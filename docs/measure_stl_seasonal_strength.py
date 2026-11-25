# -*- coding: utf-8 -*-
"""Reproduce the numbers in docs/StlSeasonalStrengthMeasured.md.

    python docs/measure_stl_seasonal_strength.py

Run from the repo root. Needs statsmodels (dev-only, the Gate A oracle for
STL itself -- not imported by the shipped module, see setup.py).
"""
import os
import platform
import sys
import time
import tracemalloc
import types

import numpy as np
import pandas as pd

sys.path.insert(0, os.getcwd())
import tests.test_stl_seasonal_strength as T  # noqa: E402

M = T._REAL


def gate_a_every_window():
    """statsmodels' `STL(window, period=5).fit()` -- the exact call the
    screen prototype made -- on every window of two 400-bar AR(1) frames,
    at lengths 50/100/101, plus a non-multiple-of-5 length (53) on a
    shorter frame."""
    from statsmodels.tsa.seasonal import STL
    print("== Gate A: vs statsmodels STL(window, period=5).fit(), every window ==")
    frames = [("AR(1) phi=0.2, 400 bars", T._ar1(400, 1, 0.2)),
              ("AR(1) phi=-0.4, 400 bars", T._ar1(400, 2, -0.4))]
    for name, close in frames:
        logc = np.log(close.to_numpy())
        for length in (50, 100, 101):
            out = M.stl_seasonal_strength(close, length=length).to_numpy()
            maxdiff = 0.0
            for t in range(length - 1, close.size):
                w = logc[t - length + 1:t + 1]
                r = STL(w, period=5).fit()
                e = r.resid
                ref = 1 - np.var(e) / np.var(r.seasonal + e)
                maxdiff = max(maxdiff, abs(out[t] - ref))
            n_checked = close.size - length + 1
            print(f"  {name}, length={length}: max abs diff {maxdiff:.2e} over {n_checked} fits")
    close = T._ar1(200, 3, 0.1)
    logc = np.log(close.to_numpy())
    out = M.stl_seasonal_strength(close, length=53).to_numpy()
    maxdiff = 0.0
    checked = 0
    for t in range(52, 200):
        w = logc[t - 52:t + 1]
        r = STL(w, period=5).fit()
        e = r.resid
        ref = 1 - np.var(e) / np.var(r.seasonal + e)
        maxdiff = max(maxdiff, abs(out[t] - ref))
        checked += 1
    print(f"  AR(1) phi=0.1, 200 bars, length=53 (not a multiple of 5): max abs diff {maxdiff:.2e} over {checked} fits")


def fixed_point_cross_check():
    """The module's own claim (`_build_ops`'s docstring): the closed-form
    coefficient matrices equal five hand-iterated passes of the fixed-point
    recursion, run independently of `_build_ops`'s matrix-power shortcut."""
    print("== cross-check: closed-form coefficients vs 5 hand-iterated passes ==")
    close = T._ar1(300, seed=2, phi=-0.2)
    logc = np.log(close.to_numpy())
    out = M.stl_seasonal_strength(close, length=100).to_numpy()
    maxdiff = 0.0
    for t in range(99, 300):
        w = logc[t - 99:t + 1]
        trend, seasonal = T._fixed_point_stl(w)
        resid = w - trend - seasonal
        ref = 1 - resid.var() / (seasonal + resid).var()
        maxdiff = max(maxdiff, abs(out[t] - ref))
    print(f"  max abs diff {maxdiff:.2e} over 201 windows")


def guard():
    print("== flat/jitter guard: drift still fires, flat and jitter do not ==")
    for g in (1e-2, 1e-4, 1e-7, 1e-8, 1e-10):
        close = pd.Series(100 * (1 + g) ** np.arange(300.0))
        out = M.stl_seasonal_strength(close)
        print(f"  drift g={g:g}: fires {out.notna().sum()} of 201; range "
              f"[{out.min():.4f}, {out.max():.4f}]")
    rng = np.random.default_rng(0)
    c = np.full(300, 10.0)
    c[rng.random(300) < 0.5] = np.nextafter(10.0, 20.0)
    print(f"  one-ulp jitter: fires {M.stl_seasonal_strength(pd.Series(c)).notna().sum()}")
    print(f"  exactly flat: fires {M.stl_seasonal_strength(pd.Series([10.0]*150)).notna().sum()}")
    for sd in (1e-12, 1e-9):
        close = pd.Series(100 * np.exp(np.cumsum(sd * rng.standard_normal(300))))
        print(f"  iid log returns of sd {sd:g}: fires "
              f"{M.stl_seasonal_strength(close).iloc[99:].notna().sum()} of 201")


def causality():
    print("== Gate B: causality ==")
    close = T._ar1(seed=11)
    print(f"  real module leaks at {T._leaks(M.stl_seasonal_strength)} of 16 offsets")
    mod = T._load_mutant(*T.MUTANT)
    print(f"  mutant differs from real: {not mod.stl_seasonal_strength(close).equals(M.stl_seasonal_strength(close))}")
    print(f"  mutant caught at {T._leaks(mod.stl_seasonal_strength)} of 16 offsets")


def reachability():
    print("== Gate C: reachability, synthetic 600 bars ==")
    out = M.stl_seasonal_strength(T._ar1(seed=4))
    print(f"  fires {out.notna().sum()} of 600 (first at bar 99); distinct "
          f"{out.dropna().nunique()}; range [{out.min():.4f}, {out.max():.4f}]")


def scale_free():
    print("== Gate D: scale-free ==")
    close = T._ar1(seed=4)
    base = M.stl_seasonal_strength(close)
    for k in (8.0, 64.0):
        scaled = M.stl_seasonal_strength(close * k)
        m = base.notna()
        same = bool((base[m] == scaled[m]).all())
        print(f"  x{k}: bit-identical {same}, NaN masks equal {(base.isna()==scaled.isna()).all()}")
    for k in (10.0, 3.7):
        scaled = M.stl_seasonal_strength(close * k)
        m = base.notna() & scaled.notna()
        print(f"  x{k}: max abs diff {np.max(np.abs(base[m]-scaled[m])):.2e}")


def chunk_boundary_noise():
    print("== chunking: BLAS summation-order noise across chunk sizes ==")
    close = T._ar1(seed=4)
    base = M.stl_seasonal_strength(close)
    orig = M.CHUNK_CELLS
    M.CHUNK_CELLS = 7 * 100
    out = M.stl_seasonal_strength(close)
    M.CHUNK_CELLS = orig
    m = base.notna()
    print(f"  max abs diff {np.max(np.abs(base[m]-out[m])):.2e} (NaN masks equal "
          f"{(base.isna()==out.isna()).all()})")


def cost():
    print("== cost (machine-dependent; " + (platform.processor() or platform.machine()) + ") ==")
    for n in (5000, 20000, 200000):
        close = T._ar1(n, 5)
        for length in (100, 252):
            runs = [_timed(close, length) for _ in range(5)]
            tracemalloc.start()
            M.stl_seasonal_strength(close, length=length)
            peak = tracemalloc.get_traced_memory()[1]
            tracemalloc.stop()
            print(f"  n={n} length={length}: 5 runs {min(runs):.3f} .. {max(runs):.3f} s; "
                  f"peak {peak / 2 ** 20:.0f} MiB (tracemalloc, separate run)")


def _timed(close, length):
    t0 = time.perf_counter()
    M.stl_seasonal_strength(close, length=length)
    return time.perf_counter() - t0


if __name__ == "__main__":
    gate_a_every_window()
    fixed_point_cross_check()
    guard()
    causality()
    reachability()
    scale_free()
    chunk_boundary_noise()
    cost()
    print("python", sys.version.split()[0], "pandas", pd.__version__, "numpy", np.__version__)
