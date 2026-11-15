# -*- coding: utf-8 -*-
"""Reproduce the numbers in docs/ArchLmMeasured.md.

    python docs/measure_arch_lm.py

Run from the repo root. Needs statsmodels (dev-only, the Gate A oracle) for
the first section; the rest uses tests/test_arch_lm.py's own generators.
"""
import os
import sys
import time
import tracemalloc
import warnings

import numpy as np
import pandas as pd

sys.path.insert(0, os.getcwd())
import tests.test_arch_lm as T  # noqa: E402


def ticky(n, seed):
    """Price near 5 on a 0.01 tick: many zero returns."""
    c = T._iid(n, seed).to_numpy() * 0.05
    c = 1 + (c - c[0]) * 0.2 + 4  # damp the walk to about 0.4% a bar near 5
    return pd.Series(np.round(c / 0.01) * 0.01)


def flatmix(n, seed):
    c = T._iid(n, seed).to_numpy().copy()
    c[300:450] = c[300]
    return pd.Series(c)


def near_singular(n, seed):
    """Squared returns periodic with period 3 plus 1e-10 relative noise: the
    lag matrix is close to rank-deficient, where the port's cutoff (on the
    centred lags) and statsmodels' (on [1, lags]) can decide differently."""
    rng = np.random.default_rng(seed)
    base = np.array([0.01, 0.02, 0.03])[np.arange(n) % 3]
    r = base * (1 + 1e-10 * rng.standard_normal(n)) * np.where(rng.random(n) < 0.5, -1.0, 1.0)
    return pd.Series(100 * np.cumprod(1 + np.r_[0.0, r[1:]]))


def gate_a():
    from statsmodels.stats.diagnostic import het_arch
    print("== Gate A: vs statsmodels het_arch at every window ==")
    for name, close in (("garch(.1,.85)", T._garch(1500, 1)), ("iid normal", T._iid(1500, 2)),
                        ("tick-rounded", ticky(1500, 3)), ("150 flat bars", flatmix(800, 4)),
                        ("near-singular", near_singular(800, 5))):
        c = close.to_numpy()
        r = c[1:] / c[:-1] - 1
        for L in (20, 100):
            lags = min(10, L // 5)
            ours = T.arch_lm(close, length=L).to_numpy()
            ref = np.full(c.size, np.nan)
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                for t in range(L, c.size):
                    ref[t] = het_arch(r[t - L:t], nlags=lags)[0]
            m = ~np.isnan(ours) & ~np.isnan(ref)
            print(f"  {name} length {L}: zero returns {np.mean(r == 0):.2f}; NaN {np.isnan(ours).sum()} "
                  f"(statsmodels {np.isnan(ref).sum()}, masks equal {np.array_equal(np.isnan(ours), np.isnan(ref))}); "
                  f"max abs diff {np.max(np.abs(ours[m] - ref[m])):.1e} over {m.sum()} bars")


def semantics():
    print("== semantics: ARCHLM_100, 200 paths x 600 bars (500 values each) ==")
    rows = (("iid normal", lambda s: T._iid(600, s)), ("iid t(3)", lambda s: T._iid(600, s, "t3")),
            ("GARCH(.05,.90)", lambda s: T._garch(600, s, .05, .90)),
            ("GARCH(.10,.85)", lambda s: T._garch(600, s, .10, .85)),
            ("GARCH(.20,.75)", lambda s: T._garch(600, s, .20, .75)))
    print("| returns | pooled median | pooled mean | share > 18.307 | per-path share p10 / p50 / p90 |")
    for name, mk in rows:
        vals = [T.arch_lm(mk(2000 + s)).dropna().to_numpy() for s in range(200)]
        pooled = np.concatenate(vals)
        per = np.array([np.mean(v > T.CRIT_5PCT_10DF) for v in vals])
        print(f"| {name} | {np.median(pooled):.3f} | {pooled.mean():.3f} | {np.mean(pooled > T.CRIT_5PCT_10DF):.4f} | "
              f"{np.quantile(per, .1):.3f} / {np.median(per):.3f} / {np.quantile(per, .9):.3f} |")


def log_vs_simple():
    """ARCHLM_100 on log returns (the module with r = log(c / c1)) against the
    shipped simple returns, over 200 GARCH(0.10, 0.85) paths."""
    import types
    src = open(T._REAL.__file__, encoding="utf-8").read()
    old = "r = c[1:] / c[:-1] - 1.0"
    assert src.count(old) == 1
    mod = types.ModuleType("_arch_lm_log")
    exec(compile(src.replace(old, "r = np.log(c[1:] / c[:-1])"), T._REAL.__file__, "exec"), mod.__dict__)
    a, b = [], []
    for s in range(200):
        close = T._garch(600, 2000 + s, .10, .85)
        a.append(T.arch_lm(close).dropna().to_numpy())
        b.append(mod.arch_lm(close).dropna().to_numpy())
    a, b = np.concatenate(a), np.concatenate(b)
    d = np.abs(a - b)
    rho = pd.Series(a).corr(pd.Series(b), method="spearman")
    print("== log vs simple returns, ARCHLM_100, 200 GARCH(.10,.85) paths ==")
    print(f"  max abs diff {d.max():.3f}, median abs diff {np.median(d):.4f}, Spearman rho {rho:.5f}, n={a.size}")


def cost():
    import platform
    print("== cost (machine-dependent; " + (platform.processor() or platform.machine()) + ") ==")
    for n in (5000, 20000, 200000):
        close = T._iid(n, 5)
        for L in (100, 252):
            best = min(_timed(close, L) for _ in range(3))  # tracemalloc off
            tracemalloc.start()
            T.arch_lm(close, length=L)
            peak = tracemalloc.get_traced_memory()[1]
            tracemalloc.stop()
            print(f"  n={n} length={L}: best of 3 {best:.2f} s; peak {peak / 2 ** 20:.0f} MiB (tracemalloc, separate run)")


def _timed(close, length):
    t0 = time.perf_counter()
    T.arch_lm(close, length=length)
    return time.perf_counter() - t0


if __name__ == "__main__":
    gate_a()
    semantics()
    log_vs_simple()
    cost()
    print("python", sys.version.split()[0], "pandas", pd.__version__, "numpy", np.__version__)
