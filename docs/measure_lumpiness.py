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


def gate_a():
    print("== Gate A: vs Kats get_lumpiness (verbatim) on the z-scored window, every bar ==")
    for name, close in (("GARCH(.10,.85)", T._garch(1500, 1)), ("iid normal", T._iid(1500, 2)),
                        ("iid t(3)", T._iid(1500, 3, "t3")), ("tick-rounded", ticky(1500, 4)),
                        ("150 flat bars", flatmix(800, 5))):
        r = np.diff(close.to_numpy()) / close.to_numpy()[:-1]
        for L in (20, 63, 100, 252):
            ours = T.lumpiness(close, length=L).to_numpy()
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
    print("== rounding guard ==")
    steady = pd.Series(100 * 1.01 ** np.arange(300.0))
    r = np.diff(steady.to_numpy()) / steady.to_numpy()[:-1]
    print(f"  100*1.01^t: distinct returns {np.unique(r).size}, sd/rms {r.std() / np.sqrt((r * r).mean()):.2e}, "
          f"non-NaN {T.lumpiness(steady).notna().sum()} of 200")
    src = open(T._REAL.__file__, encoding="utf-8").read()
    mod = types.ModuleType("_unguarded")
    exec(compile(src.replace("FLAT_RTOL = 1e-9", "FLAT_RTOL = 0.0"), T._REAL.__file__, "exec"), mod.__dict__)
    u = mod.lumpiness(steady)
    print(f"  unguarded on the same: non-NaN {u.notna().sum()}, median {u.median():.3f}, max {u.max():.3f}")
    for name, close in (("GARCH(.10,.85)", T._garch(1500, 1)), ("tick-rounded", ticky(1500, 4))):
        g, n = T.lumpiness(close), mod.lumpiness(close)
        same = np.array_equal(g.to_numpy(), n.to_numpy(), equal_nan=True)
        print(f"  {name}: guarded == unguarded on every bar: {same}")


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
            best = min(_timed(close, L) for _ in range(3))  # tracemalloc off
            tracemalloc.start()
            T.lumpiness(close, length=L)
            peak = tracemalloc.get_traced_memory()[1]
            tracemalloc.stop()
            print(f"  n={n} length={L}: best of 3 {best:.3f} s; peak {peak / 2 ** 20:.0f} MiB (tracemalloc, separate run)")


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
