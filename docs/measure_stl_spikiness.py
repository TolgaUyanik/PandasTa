# -*- coding: utf-8 -*-
"""Reproduce the numbers in docs/StlSpikinessMeasured.md.

    python docs/measure_stl_spikiness.py

Run from the repo root. Needs statsmodels (dev-only, the Gate A oracle for
STL itself -- not imported by the shipped module, see setup.py).
"""
import os
import platform
import sys
import time
import tracemalloc

import numpy as np
import pandas as pd

sys.path.insert(0, os.getcwd())
import tests.test_stl_spikiness as T  # noqa: E402

M = T._REAL


def gate_a_every_window():
    """statsmodels' `STL(window, period=5).fit()` -- the exact call the
    screen prototype made -- on every window of two 400-bar AR(1) frames,
    at lengths 50/100/101, plus a non-multiple-of-5 length (53) on a
    shorter frame. The oracle is the brute-force leave-one-out loop
    (`_brute_force_spikiness`), the literal reading of the issue's own
    "var(nanvar of leave-one-out resid)"."""
    from statsmodels.tsa.seasonal import STL
    print("== Gate A: vs statsmodels STL(window, period=5).fit() + brute-force leave-one-out, every window ==")
    frames = [("AR(1) phi=0.2, 400 bars", T._ar1(400, 1, 0.2)),
              ("AR(1) phi=-0.4, 400 bars", T._ar1(400, 2, -0.4))]
    for name, close in frames:
        logc = np.log(close.to_numpy())
        for length in (50, 100, 101):
            out = M.stl_spikiness(close, length=length).to_numpy()
            maxdiff = 0.0
            for t in range(length - 1, close.size):
                w = logc[t - length + 1:t + 1]
                r = STL(w, period=5).fit()
                ref = T._brute_force_spikiness(r.resid)
                maxdiff = max(maxdiff, abs(out[t] - ref))
            n_checked = close.size - length + 1
            print(f"  {name}, length={length}: max abs diff {maxdiff:.2e} over {n_checked} fits")
    close = T._ar1(200, 3, 0.1)
    logc = np.log(close.to_numpy())
    out = M.stl_spikiness(close, length=53).to_numpy()
    maxdiff = 0.0
    checked = 0
    for t in range(52, 200):
        w = logc[t - 52:t + 1]
        r = STL(w, period=5).fit()
        ref = T._brute_force_spikiness(r.resid)
        maxdiff = max(maxdiff, abs(out[t] - ref))
        checked += 1
    print(f"  AR(1) phi=0.1, 200 bars, length=53 (not a multiple of 5): max abs diff {maxdiff:.2e} over {checked} fits")


def fixed_point_cross_check():
    """Cross-check of THIS module's closed form against a hand-run 5-pass
    iteration of the shared STL recursion plus the brute-force leave-one-out
    loop (not an independent check of the LOESS/cycle-subseries/low-pass
    math -- see stl_seasonal_strength's own oracle test for that)."""
    print("== cross-check: this module's closed form vs 5 hand-iterated passes + brute force ==")
    close = T._ar1(300, seed=2, phi=-0.2)
    logc = np.log(close.to_numpy())
    out = M.stl_spikiness(close, length=100).to_numpy()
    maxdiff = 0.0
    for t in range(99, 300):
        w = logc[t - 99:t + 1]
        trend, seasonal = T._fixed_point_stl(w)
        resid = w - trend - seasonal
        ref = T._brute_force_spikiness(resid)
        maxdiff = max(maxdiff, abs(out[t] - ref))
    print(f"  max abs diff {maxdiff:.2e} over 201 windows")


def guard():
    print("== flat/jitter guard: drift still fires (near zero), flat and jitter do not ==")
    for g in (1e-2, 1e-4, 1e-7, 1e-8, 1e-10):
        close = pd.Series(100 * (1 + g) ** np.arange(300.0))
        out = M.stl_spikiness(close)
        print(f"  drift g={g:g}: fires {out.notna().sum()} of 201; range "
              f"[{out.min():.3e}, {out.max():.3e}]")
    rng = np.random.default_rng(0)
    c = np.full(300, 10.0)
    c[rng.random(300) < 0.5] = np.nextafter(10.0, 20.0)
    print(f"  one-ulp jitter: fires {M.stl_spikiness(pd.Series(c)).notna().sum()}")
    print(f"  exactly flat: fires {M.stl_spikiness(pd.Series([10.0]*150)).notna().sum()}")
    for sd in (1e-12, 1e-9):
        close = pd.Series(100 * np.exp(np.cumsum(sd * rng.standard_normal(300))))
        print(f"  iid log returns of sd {sd:g}: fires "
              f"{M.stl_spikiness(close).iloc[99:].notna().sum()} of 201")


def causality():
    print("== Gate B: causality ==")
    close = T._ar1(seed=11)
    print(f"  real module leaks at {T._leaks(M.stl_spikiness)} of 16 offsets")
    mod = T._load_mutant(*T.MUTANT)
    print(f"  mutant differs from real: {not mod.stl_spikiness(close).equals(M.stl_spikiness(close))}")
    print(f"  mutant caught at {T._leaks(mod.stl_spikiness)} of 16 offsets")


def reachability():
    print("== Gate C: reachability ==")
    out = M.stl_spikiness(T._ar1(seed=4))
    print(f"  quiet AR(1), 600 bars: fires {out.notna().sum()} of 600 (first at bar 99); "
          f"distinct {out.dropna().nunique()}; range [{out.min():.3e}, {out.max():.3e}]")

    # A frame with occasional large jumps gives the leave-one-out variance
    # array real dispersion (one dominant spike moves many of the
    # leave-one-out variances by a lot when IT is the one dropped), unlike
    # the quiet AR(1) frame above, whose residual points are all about the
    # same size.
    rng = np.random.default_rng(6)
    n = 600
    e = rng.standard_normal(n) * 0.012
    jump_idx = rng.choice(np.arange(20, n), size=n // 50, replace=False)
    e[jump_idx] += rng.choice([-1, 1], size=len(jump_idx)) * rng.uniform(0.08, 0.2, len(jump_idx))
    close = pd.Series(100 * np.exp(np.cumsum(e)))
    out2 = M.stl_spikiness(close)
    print(f"  spiky frame (occasional 8-20% jumps), 600 bars: fires {out2.notna().sum()} of 600; "
          f"distinct {out2.dropna().nunique()}; range [{out2.min():.3e}, {out2.max():.3e}]")
    print(f"  spiky frame max / quiet frame max: {out2.max() / out.max():.1f}x")

    # The literal fixture docs/gen_indicator_dictionary.py probes (same N,
    # seed and close construction as its own `make_df(100.0)`, copied here
    # rather than imported so this script does not also trigger that
    # module's full indicator probe on import) -- the exact frame the
    # dictionary's CONST tag on STLSPIKE_100 is measured against.
    dict_rng = np.random.default_rng(7)
    dict_ret = dict_rng.normal(0, 0.012, 600)
    dict_close = pd.Series(100.0 * np.exp(np.cumsum(dict_ret)))
    dict_out = M.stl_spikiness(dict_close).dropna()
    print(f"  docs/gen_indicator_dictionary.py's literal probe frame: fires {len(dict_out)}; "
          f"distinct {dict_out.nunique()}; range [{dict_out.min():.3e}, {dict_out.max():.3e}] "
          f"(rounds to 0.000000000 at the dictionary's 9-decimal CONST threshold)")


def scale_free():
    print("== Gate D: scale-free ==")
    close = T._ar1(seed=4)
    base = M.stl_spikiness(close)
    for k in (8.0, 64.0):
        scaled = M.stl_spikiness(close * k)
        m = base.notna()
        same = bool((base[m] == scaled[m]).all())
        print(f"  x{k}: bit-identical {same}, NaN masks equal {(base.isna()==scaled.isna()).all()}")
    for k in (10.0, 3.7):
        scaled = M.stl_spikiness(close * k)
        m = base.notna() & scaled.notna()
        print(f"  x{k}: max abs diff {np.max(np.abs(base[m]-scaled[m])):.2e}")


def chunk_boundary_noise():
    print("== chunking: BLAS summation-order noise across chunk sizes ==")
    close = T._ar1(seed=4)
    base = M.stl_spikiness(close)
    orig = M.CHUNK_CELLS
    M.CHUNK_CELLS = 7 * 100
    out = M.stl_spikiness(close)
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
            M.stl_spikiness(close, length=length)
            peak = tracemalloc.get_traced_memory()[1]
            tracemalloc.stop()
            print(f"  n={n} length={length}: 5 runs {min(runs):.3f} .. {max(runs):.3f} s; "
                  f"peak {peak / 2 ** 20:.0f} MiB (tracemalloc, separate run)")


def _timed(close, length):
    t0 = time.perf_counter()
    M.stl_spikiness(close, length=length)
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
