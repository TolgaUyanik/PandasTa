# -*- coding: utf-8 -*-
"""Reproduce the numbers in docs/StabilityMeasured.md.

    python docs/measure_stability.py

Run from the repo root. Uses tests/test_stability.py's generators and its
verbatim transcription of Kats' `get_stability`.
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
import tests.test_stability as T  # noqa: E402


def ticky(n, seed):
    """Price near 5 on a 0.01 tick: many zero returns."""
    c = T._iid(n, seed).to_numpy()
    c = 5 + (c - c[0]) * 0.01
    return pd.Series(np.round(c / 0.01) * 0.01)


def flatmix(n, seed):
    c = T._iid(n, seed).to_numpy().copy()
    c[300:450] = c[300]
    return pd.Series(c)


def _unguarded():
    src = open(T._REAL.__file__, encoding="utf-8").read()
    assert src.count("NOISE_ULPS = 64") == 1
    mod = types.ModuleType("_unguarded")
    exec(compile(src.replace("NOISE_ULPS = 64", "NOISE_ULPS = 0"), T._REAL.__file__, "exec"), mod.__dict__)
    return mod


def tick10(n=300):
    p = [10.0]
    for _ in range(n - 1):
        p.append(round(p[-1] * 1.1, 2))
    return pd.Series(p)


def ulp_flat(n=300):
    rng = np.random.default_rng(0)
    c = np.full(n, 10.0)
    c[rng.random(n) < 0.5] = np.nextafter(10.0, 20.0)
    return pd.Series(c)


FRAMES = (("GARCH(.10,.85), 1500", lambda: T._garch(1500, 1)), ("iid normal, 1500", lambda: T._iid(1500, 2)),
          ("block-regime, 1500", lambda: T._block_regime(1500, 3)), ("tick-rounded, 1500", lambda: ticky(1500, 4)),
          ("150 flat bars, 800", lambda: flatmix(800, 5)))


def gate_a():
    """The oracle is Kats verbatim on the z-scored window, with the module's
    own return form (c1 / c0 - 1), compared against the UNGUARDED module so
    the guard does not enter Gate A; the guard is measured separately."""
    print("== Gate A: vs Kats get_stability (verbatim) on the z-scored window, every bar ==")
    U = _unguarded()
    for name, mk in FRAMES:
        close = mk()
        c = close.to_numpy()
        r = c[1:] / c[:-1] - 1.0
        for L in (20, 63, 100, 252):
            ours = U.stability(close, length=L).to_numpy()
            ref = np.full(close.size, np.nan)
            for t in range(L, close.size):
                w = r[t - L:t]
                if w.std() > 0:
                    ref[t] = T._kats((w - w.mean()) / w.std())
            m = ~np.isnan(ours) & ~np.isnan(ref)
            print(f"  {name} length {L}: zero returns {np.mean(r == 0):.2f}; NaN {np.isnan(ours).sum()} "
                  f"(Kats {np.isnan(ref).sum()}, masks equal {np.array_equal(np.isnan(ours), np.isnan(ref))}); "
                  f"max abs diff {np.max(np.abs(ours[m] - ref[m])):.1e} over {m.sum()} bars")


def guard():
    print("== rounding guard: shipped vs unguarded ==")
    U = _unguarded()
    rows = [(f"100*(1+{g:g})^t, 300", lambda g=g: pd.Series(100 * (1 + g) ** np.arange(300.0)))
            for g in (1e-2, 1e-4, 1e-7, 1e-8, 1e-10)]
    rows.append(("10.0 with one-ulp jitter, 300", ulp_flat))
    for name, mk in rows:
        close = mk()
        g, u = T.stability(close), U.stability(close)
        print(f"  {name}: shipped fires {g.notna().sum()}; unguarded fires {u.notna().sum()}, "
              f"median {u.median():.3f}, max {u.max():.3f}")
    for name, mk in FRAMES + (("10%/bar on a 0.01 tick, 300", tick10),):
        close = mk()
        for L in (20, 100, 252):
            if L >= close.size:
                continue
            g, u = T.stability(close, length=L), U.stability(close, length=L)
            same = np.array_equal(g.to_numpy(), u.to_numpy(), equal_nan=True)
            print(f"  {name} length {L}: identical {same}, blanked by the guard only {int((g.isna() & u.notna()).sum())}")


def semantics():
    print("== semantics: STABILITY_100, 10 paths x 600 bars (500 values each) ==")
    rows = (("iid normal", lambda s: T._iid(600, s)),
            ("GARCH(.10,.85)", lambda s: T._garch(600, s, .10, .85)),
            ("block-regime drift=0.02 block=20", lambda s: T._block_regime(600, s, 0.02, 20)),
            ("block-regime drift=0.01 block=20", lambda s: T._block_regime(600, s, 0.01, 20)))
    print("| returns | pooled median | pooled mean | p90 |")
    for name, mk in rows:
        v = np.concatenate([T.stability(mk(500 + s)).dropna().to_numpy() for s in range(10)])
        print(f"| {name} | {np.median(v):.4f} | {v.mean():.4f} | {np.quantile(v, .9):.4f} |")


def scale_tolerance():
    print("== Gate D: price-scale tolerance (x10/x3.7, not powers of two) ==")
    close = T._garch(seed=4)
    for k in (10.0, 3.7):
        base, scaled = T.stability(close), T.stability(close * k)
        d = (base - scaled).abs()
        print(f"  x{k}: max abs diff {d.max():.3e}, NaN masks equal {(base.isna() == scaled.isna()).all()}")


def cost():
    print("== cost (machine-dependent; " + (platform.processor() or platform.machine()) + ") ==")
    for n in (5000, 20000, 200000):
        close = T._iid(n, 5)
        for L in (100, 252):
            runs = [_timed(close, L) for _ in range(5)]  # tracemalloc off
            tracemalloc.start()
            T.stability(close, length=L)
            peak = tracemalloc.get_traced_memory()[1]
            tracemalloc.stop()
            print(f"  n={n} length={L}: 5 runs {min(runs):.3f} .. {max(runs):.3f} s; "
                  f"peak {peak / 2 ** 20:.0f} MiB (tracemalloc, separate run)")


def _timed(close, length):
    t0 = time.perf_counter()
    T.stability(close, length=length)
    return time.perf_counter() - t0


if __name__ == "__main__":
    gate_a()
    guard()
    semantics()
    scale_tolerance()
    cost()
    print("python", sys.version.split()[0], "pandas", pd.__version__, "numpy", np.__version__)
