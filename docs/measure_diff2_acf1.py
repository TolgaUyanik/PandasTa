# -*- coding: utf-8 -*-
"""Reproduce the numbers in docs/Diff2Acf1Measured.md.

    python docs/measure_diff2_acf1.py

Run from the repo root. Needs statsmodels (dev-only, the Gate A oracle) for
the first section; the rest uses tests/test_diff2_acf1.py's generators.
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
import tests.test_diff2_acf1 as T  # noqa: E402
from pandas_ta.momentum.a101_048 import a101_048  # noqa: E402
from pandas_ta.momentum.er import er  # noqa: E402
from pandas_ta.statistics.g191_165 import g191_165  # noqa: E402
from pandas_ta.statistics.kpss import kpss  # noqa: E402
from pandas_ta.trend.chop import chop  # noqa: E402
from pandas_ta.trend.vhf import vhf  # noqa: E402
from pandas_ta.volatility.roll_spread import roll_spread  # noqa: E402


def _unguarded():
    src = open(T._REAL.__file__, encoding="utf-8").read()
    assert src.count("NOISE_ULPS = 64") == 1
    mod = types.ModuleType("_unguarded")
    exec(compile(src.replace("NOISE_ULPS = 64", "NOISE_ULPS = 0"), T._REAL.__file__, "exec"), mod.__dict__)
    return mod


def t3(n, seed):
    """iid Student-t(3) log returns, sd 2%."""
    rng = np.random.default_rng(seed)
    return pd.Series(100 * np.exp(np.cumsum(0.02 * rng.standard_t(3, n) / np.sqrt(3))))


def ticky(n, seed):
    """Price near 5 on a 0.01 tick: many zero returns."""
    c = T._ar1(n, seed).to_numpy()
    return pd.Series(np.round((5 + (c - c[0]) * 0.01) / 0.01) * 0.01)


def flatmix(n, seed):
    c = T._ar1(n, seed).to_numpy().copy()
    c[300:450] = c[300]
    return pd.Series(c)


def tick10(n=150):
    p = [10.0]
    for _ in range(n - 1):
        p.append(round(p[-1] * 1.1, 2))
    return pd.Series(p)


def ulp_flat(n=300):
    rng = np.random.default_rng(0)
    c = np.full(n, 10.0)
    c[rng.random(n) < 0.5] = np.nextafter(10.0, 20.0)
    return pd.Series(c)


FRAMES = (("AR(1) phi 0.2, 1500", lambda: T._ar1(1500, 1, 0.2)), ("iid normal, 1500", lambda: T._ar1(1500, 2)),
          ("GARCH(.20,.75), 1500", lambda: T._garch(1500, 3)), ("tick-rounded, 1500", lambda: ticky(1500, 4)),
          ("150 flat bars, 800", lambda: flatmix(800, 5)))


def kats_diff2y_acf1(x, acfpacf_lag=6, period=7):
    """The control flow of kats/tsfeatures/tsfeatures.py (a6b7e88)
    `get_acfpacf_features` as far as `diff2y_acf1` depends on it, in Kats'
    order: the guard at L1090, L1098-1105, `pacf(x)` at L1107, the
    zero-variance guard at L1109-1116 (`_yule_walker_determinant` with one
    lag is the demeaned variance, L1156-1167), the two `pacf` calls at
    L1118-1119, and the value at L975. The `pacf` results feed other
    features and are discarded; the calls are kept because they raise on
    short inputs, which is part of what Kats does. Not reproduced: the
    `acf(x)` and `acf(diff1x)` values (L1103-1104) and the feature
    switches, which do not affect `diff2y_acf1`."""
    from statsmodels.tsa.stattools import acf, pacf
    if len(x) < 10 or len(x) < period or len(np.unique(x)) == 1:
        return np.nan
    nlag = min(acfpacf_lag, len(x) - 2)
    diff1x = [x[i] - x[i - 1] for i in range(1, len(x))]
    diff2x = [diff1x[i] - diff1x[i - 1] for i in range(1, len(diff1x))]
    diff2y_acf_list = acf(diff2x, fft=True, nlags=nlag)[1:]
    pacf(x, nlags=period)
    for d in (diff1x, diff2x):
        v = np.array(d, dtype=np.float64)
        v -= v.mean()
        if (v ** 2).mean() == 0:
            return np.nan
    pacf(diff1x, nlags=nlag)
    pacf(diff2x, nlags=nlag)
    return diff2y_acf_list[0]


def kats_minimum():
    print("== the shortest input Kats' own call returns a value on ==")
    x = np.log(T._ar1(40, 1).to_numpy())
    for n in range(9, 17):
        try:
            v = kats_diff2y_acf1(x[:n])
            out = "NaN (L1090 guard)" if np.isnan(v) else f"{v:+.4f}"
        except Exception as e:  # noqa: BLE001
            out = f"raises {type(e).__name__}"
        print(f"  {n} points: {out}")


def gate_a():
    print("== Gate A: vs Kats diff2y_acf1 (kats_diff2y_acf1 above) on log close, every window ==")
    print("   (the unguarded module, so the rounding guard does not enter; Kats differences logs,")
    print("    the module takes the log of the ratio: agreement is to rounding)")
    U = _unguarded()
    for name, mk in FRAMES:
        close = mk()
        c = close.to_numpy()
        logc = np.log(c)
        zero = np.mean(c[1:] == c[:-1])
        for L in (14, 63, 100, 252):
            ours = U.diff2_acf1(close, length=L).to_numpy()
            ref = np.full(c.size, np.nan)
            for t in range(L - 1, c.size):
                ref[t] = kats_diff2y_acf1(logc[t - L + 1:t + 1])
            m = ~np.isnan(ours) & ~np.isnan(ref)
            print(f"  {name} length {L}: zero returns {zero:.2f}; NaN {np.isnan(ours).sum()} "
                  f"(Kats {np.isnan(ref).sum()}, masks equal {np.array_equal(np.isnan(ours), np.isnan(ref))}); "
                  f"max abs diff {np.max(np.abs(ours[m] - ref[m])):.1e} over {m.sum()} bars")


def guard():
    print("== rounding guard: shipped vs unguarded ==")
    U = _unguarded()
    rows = [(f"100*(1+{g:g})^t, 300", lambda g=g: pd.Series(100 * (1 + g) ** np.arange(300.0)))
            for g in (1e-2, 1e-4, 1e-7, 1e-8, 1e-10)]
    rows.append(("exp(linspace(0, 30, 300)), 10%/bar", lambda: pd.Series(np.exp(np.linspace(0.0, 30.0, 300)))))
    rows.append(("log close = 1e-5 t^2, 300", lambda: pd.Series(100 * np.exp(1e-5 * np.arange(300.0) ** 2))))
    rows.append(("10.0 with one-ulp jitter, 300", ulp_flat))
    noise_units = []
    for name, mk in rows:
        close = mk()
        g, u = T.diff2_acf1(close), U.diff2_acf1(close)
        units = _units(close, 100)
        noise_units.append(np.nanmax(units))
        print(f"  {name}: shipped fires {g.notna().sum()}; unguarded fires {u.notna().sum()}, "
              f"median {u.median():.3f}, min {u.min():.3f}, max {u.max():.3f}; "
              f"largest sd {np.nanmax(units):.2f} eps units")
    real_units = []
    for name, mk in FRAMES + (("10%/bar on a 0.01 tick, 150", tick10),):
        close = mk()
        for L in (14, 100, 252):
            if L > close.size:
                continue
            g, u = T.diff2_acf1(close, length=L), U.diff2_acf1(close, length=L)
            same = np.array_equal(g.to_numpy(), u.to_numpy(), equal_nan=True)
            units = _units(close, L)
            fired = units[u.notna().to_numpy()]
            real_units.append(fired.min())
            print(f"  {name} length {L}: identical {same}, blanked by the guard only "
                  f"{int((g.isna() & u.notna()).sum())}; smallest sd where it fires {fired.min():.1e} eps units")
    rng = np.random.default_rng(0)
    for sd in (1e-12, 1e-9):
        close = pd.Series(100 * np.exp(np.cumsum(sd * rng.standard_normal(300))))
        units = _units(close, 100)
        real_units.append(np.nanmin(units))
        print(f"  iid log returns of sd {sd:g}, 300: shipped fires {T.diff2_acf1(close).notna().sum()} of 201; "
              f"smallest sd {np.nanmin(units):.1e} eps units")
    print(f"  headroom of the floor (NOISE_ULPS = {T._REAL.NOISE_ULPS}): rounding-only series reach at most "
          f"{max(noise_units):.2f} units; real series are at least {min(real_units):.1e} units")


def _units(close, length):
    """sd of each window's return changes, in units of eps * (1 + max |log return|)."""
    c = close.to_numpy(dtype=float)
    r = np.log(c[1:] / c[:-1])
    d2 = np.diff(r)
    out = np.full(c.size, np.nan)
    for t in range(length - 1, c.size):
        w = d2[t - length + 1:t - 1]
        rmax = np.abs(r[t - length + 1:t]).max()
        out[t] = w.std() / (np.finfo(float).eps * (1 + rmax))
    return out


def semantics():
    print("== semantics: DIFF2ACF1_100, 200 paths x 600 bars (501 values each) ==")
    rows = [(f"AR(1) phi {p:+.1f}", lambda s, p=p: T._ar1(600, s, p), -(1 - p) / 2) for p in (-0.3, -0.1, 0.0, 0.1, 0.3)]
    rows += [("iid t(3)", lambda s: t3(600, s), -0.5),
             ("GARCH(.10,.85)", lambda s: T._garch(600, s, .10, .85), -0.5),
             ("GARCH(.20,.75)", lambda s: T._garch(600, s, .20, .75), -0.5)]
    print("| log returns | population | pooled median | pooled mean | p10 | p90 |")
    for name, mk, pop in rows:
        v = np.concatenate([T.diff2_acf1(mk(2000 + s)).dropna().to_numpy() for s in range(200)])
        print(f"| {name} | {pop:+.2f} | {np.median(v):+.4f} | {v.mean():+.4f} | {np.quantile(v, .1):+.4f} | {np.quantile(v, .9):+.4f} |")


def _acs(close):
    """The column, the identity on the window's sample rho1 and rho2, and rho1."""
    c = close.to_numpy()
    r = np.log(c[1:] / c[:-1])
    g = np.full(c.size, np.nan)
    rho1 = g.copy()
    for t in range(99, c.size):
        w = r[t - 99:t]
        x = w - w.mean()
        den = np.dot(x, x)
        a1, a2 = np.dot(x[1:], x[:-1]) / den, np.dot(x[2:], x[:-2]) / den
        rho1[t] = a1
        g[t] = (2 * a1 - 1 - a2) / (2 * (1 - a1))
    return T.diff2_acf1(close).to_numpy()[99:], g[99:], rho1[99:]


def family():
    sp = lambda u, v: pd.Series(u).corr(pd.Series(v), method="spearman")  # noqa: E731
    print("== family: against the window's own return autocorrelations, 100 paths x 600 bars ==")
    print("   g = (2 rho1 - 1 - rho2) / (2 (1 - rho1)) on the 99 log returns of the same window")
    for name, mk in (("iid normal", lambda s: T._ar1(600, s)), ("AR(1) phi +0.3", lambda s: T._ar1(600, s, 0.3)),
                     ("GARCH(.20,.75)", lambda s: T._garch(600, s))):
        A, G, R, pg, pr = [], [], [], [], []
        for s in range(100):
            a, g, r1 = _acs(mk(2000 + s))
            A.append(a); G.append(g); R.append(r1)
            pg.append(sp(a, g)); pr.append(sp(a, r1))
        A, G, R = map(np.concatenate, (A, G, R))
        print(f"  {name}: pooled Spearman vs g {sp(A, G):.4f} (per-path min {min(pg):.3f}, median {np.median(pg):.3f}); "
              f"vs rho1 alone {sp(A, R):.4f} (per-path p10/p50/p90 {np.quantile(pr, .1):.3f}/{np.median(pr):.3f}/{np.quantile(pr, .9):.3f}); "
              f"|column - g| median {np.median(np.abs(A - G)):.4f}, max {np.max(np.abs(A - G)):.3f}")
    print("== family: against roll_spread (in Category), 100 iid paths x 600 bars ==")
    for L in (20, 100):
        A, B = [], []
        for s in range(100):
            close = T._ar1(600, 2000 + s)
            A.append(T.diff2_acf1(close).to_numpy())
            B.append(roll_spread(close, length=L).to_numpy())
        A, B = np.concatenate(A), np.concatenate(B)
        m = ~np.isnan(A) & ~np.isnan(B)
        print(f"  ROLL_{L}: Spearman {sp(A[m], B[m]):.4f} over {m.sum()} bars where both fire "
              f"(ROLL_{L} is NaN on {np.mean(np.isnan(B[~np.isnan(A)])):.3f} of the bars where the column fires)")
    print("== family: against a101_048 (in Category; 250-bar autocorrelation times the day's change) ==")
    A, B = [], []
    for s in range(100):
        close = T._ar1(600, 2000 + s)
        A.append(T.diff2_acf1(close).to_numpy())
        B.append(a101_048(close).to_numpy())
    A, B = np.concatenate(A), np.concatenate(B)
    m = ~np.isnan(A) & ~np.isnan(B)
    print(f"  A101_048 (default): Spearman {sp(A[m], B[m]):.4f} over {m.sum()} bars where both fire")
    print("== family: against trend-vs-reversal columns in Category, 100 paths x 600 bars each ==")
    print("   (chop is given high = low = close: these frames are close-only)")
    others = (("ER_10 (default)", lambda c: er(c)), ("ER_100", lambda c: er(c, length=100)),
              ("g191_165 (default)", lambda c: g191_165(c)), ("CHOP (default)", lambda c: chop(c, c, c)),
              ("VHF (default)", lambda c: vhf(c)), ("KPSS_100 (default)", lambda c: kpss(c)))
    for frame, mk in (("iid normal", lambda s: T._ar1(600, s)), ("AR(1) phi +0.3", lambda s: T._ar1(600, s, 0.3))):
        closes = [mk(2000 + s) for s in range(100)]
        A = np.concatenate([T.diff2_acf1(c).to_numpy() for c in closes])
        for name, fn in others:
            B = np.concatenate([np.asarray(fn(c), dtype=float).reshape(len(c), -1)[:, 0] for c in closes])
            m = ~np.isnan(A) & ~np.isnan(B)
            print(f"  {frame}, {name}: Spearman {sp(A[m], B[m]):+.4f} over {m.sum()} bars where both fire")


def window_definition():
    print("== window definition: 100 closes (shipped) vs 102 closes (= 100 return changes), same bars ==")
    A, B = [], []
    for s in range(100):
        close = T._ar1(600, 2000 + s)
        A.append(T.diff2_acf1(close, length=100).to_numpy()[101:])
        B.append(T.diff2_acf1(close, length=102).to_numpy()[101:])
    A, B = np.concatenate(A), np.concatenate(B)
    d = np.abs(A - B)
    print(f"  max abs diff {d.max():.4f}, median abs diff {np.median(d):.5f}, "
          f"Spearman {pd.Series(A).corr(pd.Series(B), method='spearman'):.5f}, n={A.size}")


def cost():
    print("== cost (machine-dependent; " + (platform.processor() or platform.machine()) + ") ==")
    for n in (5000, 20000, 200000):
        close = T._ar1(n, 5)
        for L in (100, 252):
            runs = [_timed(close, L) for _ in range(5)]  # tracemalloc off
            tracemalloc.start()
            T.diff2_acf1(close, length=L)
            peak = tracemalloc.get_traced_memory()[1]
            tracemalloc.stop()
            print(f"  n={n} length={L}: 5 runs {min(runs):.3f} .. {max(runs):.3f} s; "
                  f"peak {peak / 2 ** 20:.0f} MiB (tracemalloc, separate run)")


def _timed(close, length):
    t0 = time.perf_counter()
    T.diff2_acf1(close, length=length)
    return time.perf_counter() - t0


if __name__ == "__main__":
    kats_minimum()
    gate_a()
    guard()
    semantics()
    family()
    window_definition()
    cost()
    print("python", sys.version.split()[0], "pandas", pd.__version__, "numpy", np.__version__)
