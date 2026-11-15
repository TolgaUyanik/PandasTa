# -*- coding: utf-8 -*-
"""Print every number in docs/TrendScanMeasured.md: the rolling-sum
precision defect (global-index vs local/window-scale sums), the Gate D
ratio-vs-raw-log defect, the anchor-choice equivalence, Gate C synthetic
counts, scale tolerance, and the proxy overlap against existing columns.

    python docs/measure_trend_scan_proxy.py

Synthetic GBM walks with fixed seeds -- a PROXY, not Gate E, which needs the
parent repo's production column set and real BIST frames (run by the
issue-solver launcher outside this worktree).
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pandas_ta as ta
from pandas_ta.statistics.trend_scan import DEFAULT_HORIZONS, _rolling_trend_t


def walk(n=3000, sigma=0.02, seed=1, tick=None):
    c = 100.0 * np.exp(np.cumsum(np.random.default_rng(seed).normal(0.0, sigma, n)))
    if tick:
        c = np.round(c / tick) * tick
    return pd.Series(c)


def rho(a, b):
    return round(a.corr(b, method="spearman"), 4)


def _z_ratio(close):
    """The module's own device: log(close / anchor), anchor = first finite
    positive close -- a ratio, exact under a power-of-two rescale."""
    vals = close.to_numpy(dtype=float)
    valid = np.isfinite(vals) & (vals > 0)
    anchor = vals[valid][0]
    with np.errstate(divide="ignore", invalid="ignore"):
        z = np.log(vals / anchor)
    z[~valid] = np.nan
    return z, valid


def _rolling_trend_t_global_index(z, valid, length):
    """The FIRST version of this port: O(1)-per-window via prefix sums
    weighted by the bar's GLOBAL index, not the local/window-scale
    incremental recurrence the module ships. Kept here only to measure the
    precision this port moved away from (see the "rolling-sum precision"
    block below) -- not used by the shipped module."""
    n = len(z)
    out = np.full(n, np.nan)
    if length > n:
        return out
    zf = np.where(valid, z, 0.0)
    g = np.arange(n, dtype=float)
    cz = np.concatenate(([0.0], np.cumsum(zf)))
    czg = np.concatenate(([0.0], np.cumsum(g * zf)))
    cz2 = np.concatenate(([0.0], np.cumsum(zf * zf)))
    cnt = np.concatenate(([0], np.cumsum(valid.astype(np.int64))))
    t_idx = np.arange(length - 1, n)
    start, end_excl = t_idx - length + 1, t_idx + 1
    Sz = cz[end_excl] - cz[start]
    Sgz = czg[end_excl] - czg[start]
    Sz2 = cz2[end_excl] - cz2[start]
    cntw = cnt[end_excl] - cnt[start]
    Sg = length * (start + end_excl - 1) / 2.0
    Sxx = length * (length * length - 1) / 12.0
    Sxy = Sgz - Sg * Sz / length
    Syy = Sz2 - Sz * Sz / length
    slope = Sxy / Sxx
    SSR = Syy - slope * Sxy
    df = length - 2
    with np.errstate(divide="ignore", invalid="ignore"):
        t_stat = slope * np.sqrt(Sxx * df / SSR)
    t_stat[(cntw != length) | ~(SSR > 0)] = np.nan
    out[t_idx] = t_stat
    return out


def _naive_ols_t(y):
    n = len(y)
    x = np.arange(n, dtype=float)
    xbar, ybar = x.mean(), y.mean()
    Sxy = ((x - xbar) * (y - ybar)).sum()
    Sxx = ((x - xbar) ** 2).sum()
    Syy = ((y - ybar) ** 2).sum()
    slope = Sxy / Sxx
    SSR = Syy - slope * Sxy
    se = np.sqrt(SSR / (n - 2) / Sxx)
    return slope / se


def comparators(c):
    out = {f"close/EMA_{n} - 1": 100 * (c / ta.ema(c, n) - 1) for n in (5, 10, 20)}
    out.update({
        "BIAS_SMA_26": ta.bias(c), "ROC_5": ta.roc(c, 5), "ROC_10": ta.roc(c, 10),
        "ROC_20": ta.roc(c, 20), "SLOPE_10": ta.slope(c, 10), "SLOPE_40": ta.slope(c, 40),
        "ADX_14": ta.adx(c, c, c).iloc[:, 0], "CMO_14": ta.cmo(c), "RSI_14": ta.rsi(c),
        "TRIX_30_9": ta.trix(c).iloc[:, 0], "CUSUM_100": ta.cusum(c), "KPSS_100": ta.kpss(c),
    })
    return out


def main():
    print("== rolling-sum precision: local-recurrence (shipped) vs global-index prefix sums,")
    print("   vs a plain definitional OLS oracle -- 4000-bar walk, seed 3, length 3 and 20")
    close = walk(4000, seed=3)
    z, valid = _z_ratio(close)
    for length in (3, 20):
        local = _rolling_trend_t(z, valid, length)
        glob = _rolling_trend_t_global_index(z, valid, length)
        for t_end in (999, 2500, 3999):
            window = z[t_end - length + 1: t_end + 1]
            oracle = _naive_ols_t(window)
            print(f"  length={length} t_end={t_end}: oracle {oracle:.10f}"
                  f"  local-recurrence |diff| {abs(local[t_end] - oracle):.3e}"
                  f"  global-index |diff| {abs(glob[t_end] - oracle):.3e}")

    print("== Gate D defect: regressing on log(close) directly vs log(close / anchor),")
    print("   max |diff| in the single-horizon t-stat under x8 (3000 bars, seed 11, tick 0.05)")
    close = walk(3000, seed=11, tick=0.05)
    length = 20
    vals = close.to_numpy(dtype=float)
    valid = np.isfinite(vals) & (vals > 0)
    raw_z = np.log(vals)
    raw_z[~valid] = np.nan
    ratio_z, _ = _z_ratio(close)
    t_raw = _rolling_trend_t(raw_z, valid, length)
    t_ratio = _rolling_trend_t(ratio_z, valid, length)
    for k in (8.0, 64.0):
        scaled = close * k
        svals = scaled.to_numpy(dtype=float)
        svalid = np.isfinite(svals) & (svals > 0)
        s_raw_z = np.log(svals)
        s_raw_z[~svalid] = np.nan
        s_ratio_z, _ = _z_ratio(scaled)
        t_raw_scaled = _rolling_trend_t(s_raw_z, svalid, length)
        t_ratio_scaled = _rolling_trend_t(s_ratio_z, svalid, length)
        raw_diff = np.nanmax(np.abs(t_raw_scaled - t_raw))
        ratio_diff = np.nanmax(np.abs(t_ratio_scaled - t_ratio))
        print(f"  x{k}: raw-log max|diff| {raw_diff:.3e}  ratio-anchor max|diff| {ratio_diff:.3e}")

    print("== anchor choice: window-local P_ref (a FRESH ratio of raw prices, re-anchored")
    print("   per window) vs this module's series-wide anchor -- same (slope, t) in exact")
    print("   arithmetic -- measured max|diff| over 3 window positions")
    close = walk(4000, seed=7)
    z, valid = _z_ratio(close)
    raw = close.to_numpy(dtype=float)
    length = 20
    for t_end in (500, 1500, 3999):
        window = z[t_end - length + 1: t_end + 1]
        series_wide = _naive_ols_t(window)
        raw_window = raw[t_end - length + 1: t_end + 1]
        with np.errstate(divide="ignore", invalid="ignore"):
            local_ref = np.log(raw_window / raw_window[0])  # genuine per-window ratio, not log(a)-log(b)
        window_local = _naive_ols_t(local_ref)
        print(f"  t_end={t_end}: series-wide {series_wide:.10f}  window-local {window_local:.10f}"
              f"  |diff| {abs(series_wide - window_local):.3e}")

    print("== scale: max |diff| in TSCAN_T vs x1 (3000 bars, seed 11, tick 0.05), default horizons")
    c = walk(3000, seed=11, tick=0.05)
    base = ta.trend_scan(c)
    t_col, l_col = base.columns
    for k in (8.0, 64.0, 10.0, 3.7):
        scaled = ta.trend_scan(c * k)
        nan_match = (base.isna() == scaled.isna()).all().all()
        print(f"  x{k}: T max|diff| {(base[t_col] - scaled[t_col]).abs().max():.3e}"
              f"  L max|diff| {(base[l_col] - scaled[l_col]).abs().max():.3e}"
              f"  nan-masks-match {nan_match}  T bit-identical {base[t_col].equals(scaled[t_col])}")

    print("== Gate C synthetic (3000 bars, seed 11, tick 0.05, drift 0.0005), default horizons")
    out = ta.trend_scan(walk(3000, seed=11, tick=0.05) + 0)  # drift applied below
    c = pd.Series(100.0 * np.exp(np.cumsum(np.random.default_rng(11).normal(0.0005, 0.02, 3000))))
    c = pd.Series(np.round(c / 0.05) * 0.05)
    out = ta.trend_scan(c)
    t_out, l_out = out[t_col].dropna(), out[l_col].dropna()
    print(f"  finite {len(t_out)} / {len(c)}  distinct T {t_out.nunique()}"
          f"  horizons used {sorted(l_out.unique())}  counts {l_out.value_counts().sort_index().to_dict()}")

    print("== proxy overlap (sigma 0.02, seed 1, drift 0.0003), default horizons")
    c = pd.Series(100.0 * np.exp(np.cumsum(np.random.default_rng(1).normal(0.0003, 0.02, 5000))))
    out = ta.trend_scan(c)
    tcol = out.columns[0]
    n_comp = int(out[tcol].notna().sum())
    print("  n comparable", n_comp)
    for name, x in comparators(c).items():
        print(f"  {name:22s} rho {rho(out[tcol], x):8.4f}")

    print("volatility sweep: sigma, max|rho| (comparator)")
    for s in (0.005, 0.01, 0.02, 0.05):
        c = pd.Series(100.0 * np.exp(np.cumsum(np.random.default_rng(1).normal(0.0003, s, 5000))))
        out = ta.trend_scan(c)
        r = {name: rho(out[tcol], x) for name, x in comparators(c).items()}
        best = max(r, key=lambda name: abs(r[name]))
        print(" ", s, r[best], best)


if __name__ == "__main__":
    main()
