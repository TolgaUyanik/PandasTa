# -*- coding: utf-8 -*-
"""Reproduce the numbers in docs/Diff1Pacf5Measured.md.

    python docs/measure_diff1_pacf5.py

Run from the repo root. Needs statsmodels (dev-only, the Gate A oracle).
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
import tests.test_diff1_pacf5 as T  # noqa: E402


def _unguarded():
    src = open(T._REAL.__file__, encoding="utf-8").read()
    assert src.count("NOISE_ULPS = 64") == 1
    mod = types.ModuleType("_unguarded")
    exec(compile(src.replace("NOISE_ULPS = 64", "NOISE_ULPS = 0"), T._REAL.__file__, "exec"), mod.__dict__)
    return mod


def ticky(n, seed):
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
          ("tick-rounded, 1500", lambda: ticky(1500, 4)), ("150 flat bars, 800", lambda: flatmix(800, 5)))


def pacf_method_probe():
    """Which statsmodels pacf method matches Durbin-Levinson on the
    UNADJUSTED sample ACF (the issue's stated scale-free form)? Checked
    against an independent, from-scratch recursion (no statsmodels, no
    module code) on one window."""
    from statsmodels.tsa.stattools import pacf
    rng = np.random.default_rng(0)
    x = rng.standard_normal(99)
    x = x - x.mean()
    c0 = (x * x).sum()
    rho = np.array([(x[:-k] * x[k:]).sum() / c0 for k in range(1, 6)])
    ref = _loop_pacf5(rho)
    print("== which statsmodels pacf method matches Durbin-Levinson on the unadjusted ACF ==")
    for method in ("ywm", "ywmle", "ywadjusted", "yw", "ols"):
        try:
            v = pacf(x, nlags=6, method=method)[1:6]
            print(f"  method={method!r}: pacf={np.round(v, 10).tolist()} max|diff vs from-scratch|={np.max(np.abs(v - ref)):.2e}")
        except Exception as e:  # noqa: BLE001
            print(f"  method={method!r}: raises {type(e).__name__}: {e}")
    print(f"  from-scratch recursion: {np.round(ref, 10).tolist()}")


def _loop_pacf5(rho):
    """Independent (no statsmodels, no module code) Durbin-Levinson,
    scalar, straight off the textbook recursion."""
    phi = {(1, 1): rho[0]}
    out = [phi[1, 1]]
    for k in range(2, 6):
        num = rho[k - 1] - sum(phi[k - 1, j] * rho[k - j - 1] for j in range(1, k))
        den = 1 - sum(phi[k - 1, j] * rho[j - 1] for j in range(1, k))
        phi[k, k] = num / den
        for j in range(1, k):
            phi[k, j] = phi[k - 1, j] - phi[k, k] * phi[k - 1, k - j]
        out.append(phi[k, k])
    return np.array(out)


def kats_diff1y_pacf5(x, acfpacf_lag=6, period=7, method="ywm"):
    """The control flow of kats/tsfeatures/tsfeatures.py `get_acfpacf_features`
    as far as `diff1y_pacf5` depends on it, in Kats' order (shared with
    `diff2y_acf1`, see docs/Diff2Acf1Measured.md's citation): the guard at
    L1090, L1098-1100 (nlag, diff1x), `pacf(x)` at L1107, the zero-variance
    guard on diff1x at L1109-1116, `pacf(diff1x, nlags=nlag)` at L1118 (whose
    [1:6] ** 2 sum is diff1y_pacf5 itself here, not merely run and discarded
    as it is for diff2y_acf1), and `pacf(diff2x, nlags=nlag)` at L1119 (run,
    discarded: it feeds diff2y_pacf5, not this feature). `method` selects the
    statsmodels pacf method; Kats' own call does not pin one, so this script
    checks `ywm` (what the ported, unadjusted-ACF form matches) against the
    historical default `ywadjusted`."""
    from statsmodels.tsa.stattools import pacf
    if len(x) < 10 or len(x) < period or len(np.unique(x)) == 1:
        return np.nan
    nlag = min(acfpacf_lag, len(x) - 2)
    diff1x = [x[i] - x[i - 1] for i in range(1, len(x))]
    diff2x = [diff1x[i] - diff1x[i - 1] for i in range(1, len(diff1x))]
    pacf(x, nlags=period)
    for d in (diff1x, diff2x):
        v = np.array(d, dtype=np.float64)
        v -= v.mean()
        if (v ** 2).mean() == 0:
            return np.nan
    p1 = pacf(diff1x, nlags=nlag, method=method)[1:6]
    pacf(diff2x, nlags=nlag, method=method)
    return (p1 ** 2).sum()


def gate_a():
    print("== Gate A: vs kats_diff1y_pacf5 (method=ywm) on log close, every window ==")
    print("   (the unguarded module, so the rounding guard does not enter)")
    U = _unguarded()
    for name, mk in FRAMES:
        close = mk()
        c = close.to_numpy()
        logc = np.log(c)
        zero = np.mean(c[1:] == c[:-1])
        for L in (14, 63, 100, 252):
            ours = U.diff1_pacf5(close, length=L).to_numpy()
            ref = np.full(c.size, np.nan)
            for t in range(L - 1, c.size):
                ref[t] = kats_diff1y_pacf5(logc[t - L + 1:t + 1])
            m = ~np.isnan(ours) & ~np.isnan(ref)
            print(f"  {name} length {L}: zero returns {zero:.2f}; NaN {np.isnan(ours).sum()} "
                  f"(Kats {np.isnan(ref).sum()}, masks equal {np.array_equal(np.isnan(ours), np.isnan(ref))}); "
                  f"max abs diff {np.max(np.abs(ours[m] - ref[m])):.1e} over {m.sum()} bars")
    print("== same, method=ywadjusted (Kats' own default), to show the documented divergence ==")
    for name, mk in FRAMES[:2]:
        close = mk()
        c = close.to_numpy()
        logc = np.log(c)
        L = 100
        ours = U.diff1_pacf5(close, length=L).to_numpy()
        ref = np.full(c.size, np.nan)
        for t in range(L - 1, c.size):
            ref[t] = kats_diff1y_pacf5(logc[t - L + 1:t + 1], method="ywadjusted")
        m = ~np.isnan(ours) & ~np.isnan(ref)
        print(f"  {name} length {L}: max abs diff {np.max(np.abs(ours[m] - ref[m])):.3f}, "
              f"median {np.median(np.abs(ours[m] - ref[m])):.3f} over {m.sum()} bars")


def kats_minimum():
    print("== the shortest input Kats' own call returns a value on ==")
    x = np.log(T._ar1(40, 1).to_numpy())
    for n in range(9, 17):
        try:
            v = kats_diff1y_pacf5(x[:n])
            out = "NaN (L1090 guard)" if np.isnan(v) else f"{v:.4f}"
        except Exception as e:  # noqa: BLE001
            out = f"raises {type(e).__name__}"
        print(f"  {n} points: {out}")


def guard():
    print("== rounding guard: shipped vs unguarded ==")
    U = _unguarded()
    rows = [(f"100*(1+{g:g})^t, 300", lambda g=g: pd.Series(100 * (1 + g) ** np.arange(300.0)))
            for g in (1e-2, 1e-4, 1e-7, 1e-8, 1e-10)]
    rows.append(("exp(linspace(0, 30, 300)), 10%/bar", lambda: pd.Series(np.exp(np.linspace(0.0, 30.0, 300)))))
    rows.append(("10.0 with one-ulp jitter, 300", ulp_flat))
    noise_units = []
    for name, mk in rows:
        close = mk()
        g, u = T.diff1_pacf5(close), U.diff1_pacf5(close)
        units = _units(close, 100)
        noise_units.append(np.nanmax(units))
        print(f"  {name}: shipped fires {g.notna().sum()}; unguarded fires {u.notna().sum()}, "
              f"median {u.median():.3f}, max {u.max():.3f}; largest sd {np.nanmax(units):.2f} eps units")
    real_units = []
    for name, mk in FRAMES + (("10%/bar on a 0.01 tick, 150", tick10),):
        close = mk()
        for L in (14, 100, 252):
            if L > close.size:
                continue
            g, u = T.diff1_pacf5(close, length=L), U.diff1_pacf5(close, length=L)
            same = np.array_equal(g.to_numpy(), u.to_numpy(), equal_nan=True)
            units = _units(close, L)
            fired = units[u.notna().to_numpy()]
            if fired.size:
                real_units.append(fired.min())
            print(f"  {name} length {L}: identical {same}, blanked by the guard only "
                  f"{int((g.isna() & u.notna()).sum())}")
    rng = np.random.default_rng(0)
    for sd in (1e-12, 1e-9):
        close = pd.Series(100 * np.exp(np.cumsum(sd * rng.standard_normal(300))))
        units = _units(close, 100)
        real_units.append(np.nanmin(units))
        print(f"  iid log returns of sd {sd:g}, 300: shipped fires {T.diff1_pacf5(close).notna().sum()} of 201; "
              f"smallest sd {np.nanmin(units):.1e} eps units")
    print(f"  headroom of the floor (NOISE_ULPS = {T._REAL.NOISE_ULPS}): rounding-only series reach at most "
          f"{max(noise_units):.2f} units; real series are at least {min(real_units):.1e} units")


def _units(close, length):
    """sd of each window's returns, in units of eps * (1 + max |log return|)."""
    c = close.to_numpy(dtype=float)
    r = np.log(c[1:] / c[:-1])
    out = np.full(c.size, np.nan)
    for t in range(length - 1, c.size):
        w = r[t - length + 1:t]
        out[t] = w.std() / (np.finfo(float).eps * (1 + np.abs(w).max()))
    return out


def reachability():
    print("== Gate C: reachability, synthetic 600 bars ==")
    out = T.diff1_pacf5(T._ar1(seed=4))
    print(f"  fires {out.notna().sum()} of 600 (first at bar 99); distinct {out.dropna().nunique()}; "
          f"range [{out.min():.4f}, {out.max():.4f}]")


def cost():
    print("== cost (machine-dependent; " + (platform.processor() or platform.machine()) + ") ==")
    for n in (5000, 20000, 200000):
        close = T._ar1(n, 5)
        for L in (100, 252):
            runs = [_timed(close, L) for _ in range(5)]
            tracemalloc.start()
            T.diff1_pacf5(close, length=L)
            peak = tracemalloc.get_traced_memory()[1]
            tracemalloc.stop()
            print(f"  n={n} length={L}: 5 runs {min(runs):.3f} .. {max(runs):.3f} s; "
                  f"peak {peak / 2 ** 20:.0f} MiB (tracemalloc, separate run)")


def _timed(close, length):
    t0 = time.perf_counter()
    T.diff1_pacf5(close, length=length)
    return time.perf_counter() - t0


if __name__ == "__main__":
    pacf_method_probe()
    kats_minimum()
    gate_a()
    guard()
    reachability()
    cost()
    print("python", sys.version.split()[0], "pandas", pd.__version__, "numpy", np.__version__)
