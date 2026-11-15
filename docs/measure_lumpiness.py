# -*- coding: utf-8 -*-
"""Reproduce the numbers in docs/LumpinessMeasured.md.

    python docs/measure_lumpiness.py

Run from the repo root. Uses tests/test_lumpiness.py's generators and its
verbatim transcription of Kats' `get_lumpiness`.
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
import tests.test_lumpiness as T  # noqa: E402


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
          ("iid t(3), 1500", lambda: T._iid(1500, 3, "t3")), ("tick-rounded, 1500", lambda: ticky(1500, 4)),
          ("150 flat bars, 800", lambda: flatmix(800, 5)))


def gate_a():
    """The oracle is Kats verbatim on the z-scored window, with the module's
    own return form (c1 / c0 - 1), compared against the UNGUARDED module so
    the guard does not enter Gate A; the guard is measured separately."""
    print("== Gate A: vs Kats get_lumpiness (verbatim) on the z-scored window, every bar ==")
    U = _unguarded()
    for name, mk in FRAMES:
        close = mk()
        c = close.to_numpy()
        r = c[1:] / c[:-1] - 1.0
        for L in (20, 63, 100, 252):
            ours = U.lumpiness(close, length=L).to_numpy()
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
        g, u = T.lumpiness(close), U.lumpiness(close)
        print(f"  {name}: shipped fires {g.notna().sum()}; unguarded fires {u.notna().sum()}, "
              f"median {u.median():.3f}, max {u.max():.3f}")
    for name, mk in FRAMES + (("10%/bar on a 0.01 tick, 300", tick10),):
        close = mk()
        for L in (20, 100, 252):
            if L >= close.size:
                continue
            g, u = T.lumpiness(close, length=L), U.lumpiness(close, length=L)
            same = np.array_equal(g.to_numpy(), u.to_numpy(), equal_nan=True)
            print(f"  {name} length {L}: identical {same}, blanked by the guard only {int((g.isna() & u.notna()).sum())}")


def semantics():
    print("== semantics: LUMPINESS_100, 200 paths x 600 bars (500 values each) ==")
    rows = (("iid normal", lambda s: T._iid(600, s)), ("iid t(3)", lambda s: T._iid(600, s, "t3")),
            ("GARCH(.05,.90)", lambda s: T._garch(600, s, .05, .90)),
            ("GARCH(.10,.85)", lambda s: T._garch(600, s, .10, .85)),
            ("GARCH(.20,.75)", lambda s: T._garch(600, s, .20, .75)))
    print("| returns | pooled median | pooled mean | p90 |")
    for name, mk in rows:
        v = np.concatenate([T.lumpiness(mk(2000 + s)).dropna().to_numpy() for s in range(200)])
        print(f"| {name} | {np.median(v):.4f} | {v.mean():.4f} | {np.quantile(v, .9):.4f} |")


def log_vs_simple():
    src = open(T._REAL.__file__, encoding="utf-8").read()
    old = "r = c[1:] / c[:-1] - 1.0"
    assert src.count(old) == 1
    mod = types.ModuleType("_lump_log")
    exec(compile(src.replace(old, "r = np.log(c[1:] / c[:-1])"), T._REAL.__file__, "exec"), mod.__dict__)
    a, b = [], []
    for s in range(200):
        close = T._garch(600, 2000 + s, .10, .85)
        a.append(T.lumpiness(close).dropna().to_numpy())
        b.append(mod.lumpiness(close).dropna().to_numpy())
    a, b = np.concatenate(a), np.concatenate(b)
    d = np.abs(a - b)
    rho = pd.Series(a).corr(pd.Series(b), method="spearman")
    print("== log vs simple returns, LUMPINESS_100, 200 GARCH(.10,.85) paths ==")
    print(f"  max abs diff {d.max():.4f}, median abs diff {np.median(d):.5f}, median value {np.median(a):.4f}, "
          f"Spearman rho {rho:.5f}, n={a.size}")


def cost():
    print("== cost (machine-dependent; " + (platform.processor() or platform.machine()) + ") ==")
    for n in (5000, 20000, 200000):
        close = T._iid(n, 5)
        for L in (100, 252):
            runs = [_timed(close, L) for _ in range(5)]  # tracemalloc off
            tracemalloc.start()
            T.lumpiness(close, length=L)
            peak = tracemalloc.get_traced_memory()[1]
            tracemalloc.stop()
            print(f"  n={n} length={L}: 5 runs {min(runs):.3f} .. {max(runs):.3f} s; "
                  f"peak {peak / 2 ** 20:.0f} MiB (tracemalloc, separate run)")


def _timed(close, length):
    t0 = time.perf_counter()
    T.lumpiness(close, length=length)
    return time.perf_counter() - t0


if __name__ == "__main__":
    gate_a()
    guard()
    semantics()
    log_vs_simple()
    cost()
    print("python", sys.version.split()[0], "pandas", pd.__version__, "numpy", np.__version__)
