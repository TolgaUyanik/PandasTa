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
    c = T._iid(n, seed).to_numpy()
    c[300:450] = c[300]
    return pd.Series(c)


def gate_a():
    from statsmodels.stats.diagnostic import het_arch
    print("== Gate A: vs statsmodels het_arch at every window ==")
    for name, close in (("garch(.1,.85)", T._garch(1500, 1)), ("iid normal", T._iid(1500, 2)),
                        ("tick-rounded", ticky(1500, 3)), ("150 flat bars", flatmix(800, 4))):
        c = close.to_numpy()
        r = c[1:] / c[:-1] - 1
        for L in (20, 100):
            lags = min(10, L // 5)
            ours = T.arch_lm(close, length=L).to_numpy()
            ref = np.full(c.size, np.nan)
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                for t in range(L, c.size):
                    ref[t] = het_arch(r[t - L:t], nlags=lags, result_object=False)[0]
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


def cost():
    print("== cost ==")
    for n in (20000, 200000):
        close = T._iid(n, 5)
        for L in (100, 252):
            tracemalloc.start()
            t0 = time.perf_counter()
            T.arch_lm(close, length=L)
            dt = time.perf_counter() - t0
            peak = tracemalloc.get_traced_memory()[1]
            tracemalloc.stop()
            print(f"  n={n} length={L}: {dt:.2f} s, peak {peak / 2 ** 20:.0f} MiB (tracemalloc)")


if __name__ == "__main__":
    gate_a()
    semantics()
    cost()
    print("python", sys.version.split()[0], "pandas", pd.__version__, "numpy", np.__version__)
