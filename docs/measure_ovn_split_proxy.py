# -*- coding: utf-8 -*-
"""Print the Gate A/C/D numbers and a pre-screen (NOT Gate E) in docs/OvnSplitMeasured.md.

    python docs/measure_ovn_split_proxy.py

A PROXY screen only -- Gate E needs the parent repo's production column set
and the 89-frame BIST universe and is run by the launcher. The issue's own
"Risk, check first" (how often yfinance BIST `open` equals the prior `close`)
is NOT measured here either: this headless worktree has no network access
and no BIST OHLC fixture, so there is nothing real to check it against. See
docs/OvnSplitMeasured.md for that gap.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pandas_ta as ta
from pandas_ta.momentum.ovn_split import ovn_split


def walk(n=1200, seed=14, sigma_ovn=0.004, sigma_int=0.011, tick=0.01, tie_p=0.0):
    """Overnight/intraday random walk: open = prior close * exp(overnight),
    close = open * exp(intraday). `tie_p` forces that fraction of bars to
    open exactly at the prior close (overnight = 0), to probe the issue's
    "open is often wrong / stale" risk on a synthetic stand-in."""
    rng = np.random.default_rng(seed)
    overnight = rng.normal(0.0, sigma_ovn, n)
    intraday = rng.normal(0.0, sigma_int, n)
    if tie_p:
        ties = rng.random(n) < tie_p
        overnight = np.where(ties, 0.0, overnight)
    close = np.empty(n)
    open_ = np.empty(n)
    close[0] = 100.0
    open_[0] = 100.0
    for i in range(1, n):
        open_[i] = close[i - 1] * np.exp(overnight[i])
        close[i] = open_[i] * np.exp(intraday[i])
    if tick:
        open_ = np.round(open_ / tick) * tick
        close = np.round(close / tick) * tick
    return pd.Series(open_), pd.Series(close)


def reference(open_, close, length):
    """SUM(log(open/close[1]), length) and SUM(log(close/open), length), as
    a plain Python loop, written from the formula, not the module."""
    n = len(close)
    ovn = np.full(n, np.nan)
    intr = np.full(n, np.nan)
    o = open_.to_numpy(dtype=float)
    c = close.to_numpy(dtype=float)
    overnight = np.empty(n)
    intraday = np.empty(n)
    overnight[0] = np.nan
    intraday[0] = np.nan  # blanked to match overnight's bar-0 warm-up
    for t in range(1, n):
        overnight[t] = np.log(o[t] / c[t - 1])
        intraday[t] = np.log(c[t] / o[t])
    for t in range(length, n):
        window_o = overnight[t - length + 1: t + 1]
        window_i = intraday[t - length + 1: t + 1]
        if np.any(np.isnan(window_o)):
            continue
        ovn[t] = window_o.sum()
        intr[t] = window_i.sum()
    return ovn, intr


def rho(a, b):
    return round(a.corr(b, method="spearman"), 4)


def main():
    open_, close = walk()

    print("== Gate A: against the independent reference loop (length 21, 9, 2)")
    for length in (21, 9, 2):
        out = ovn_split(open_, close, length=length)
        ref_o, ref_i = reference(open_, close, length)
        mask = ~np.isnan(ref_o)
        diff_o = np.abs(out[f"OVNSUM_{length}"].values[mask] - ref_o[mask])
        diff_i = np.abs(out[f"INTSUM_{length}"].values[mask] - ref_i[mask])
        print(f"  length={length}: max|diff| OVNSUM {diff_o.max():.3e}, "
              f"INTSUM {diff_i.max():.3e}  n {int(mask.sum())}")

    print("== Gate D: scale invariance (log(k*a/k*b) == log(a/b))")
    base = ovn_split(open_, close)
    for k in (8.0, 64.0, 10.0, 3.7):
        scaled = ovn_split(open_ * k, close * k)
        for col in base.columns:
            same_nan = (base[col].isna() == scaled[col].isna()).all()
            m = base[col].notna()
            bit_identical = bool((base[col][m] == scaled[col][m]).all())
            max_abs_diff = float((base[col][m] - scaled[col][m]).abs().max()) if not bit_identical else 0.0
            print(f"  k={k} {col}: NaN masks match {same_nan}  bit-identical {bit_identical}"
                  + (f"  max|diff| {max_abs_diff:.3e}" if not bit_identical else ""))

    print("== Gate C: synthetic reachability (1200 bars, seed 14, length 21)")
    out = ovn_split(open_, close).dropna()
    for col in out.columns:
        s = out[col]
        print(f"  {col}: non-NaN {len(s)}  distinct {s.nunique()}  "
              f"min {s.min():.6f}  max {s.max():.6f}")

    print("== Risk probe (NOT the real yfinance/BIST check, synthetic only): "
          "fraction of bars with open == prior close")
    for tie_p in (0.0, 0.3, 0.7, 0.9):
        o2, c2 = walk(tie_p=tie_p, seed=23)
        ties = int((o2.round(2) == c2.shift(1).round(2)).sum())
        print(f"  tie_p={tie_p}: measured tie fraction {ties / len(o2):.4f}")

    print("== Pre-screen (NOT Gate E): Spearman rho vs in-package candidates, same walk")
    ovn = ovn_split(open_, close)
    comparators = {
        "GAPM_40_20": ta.gapm(open_, close),
        "TRIX_30_9": ta.trix(close)["TRIX_30_9"],
        "ROC_10": ta.roc(close),
        "MOM_10": ta.mom(close),
        "LOGRET_1": ta.log_return(close),
        "PCTRET_1": ta.percent_return(close),
        "CUSUM_100": ta.cusum(close),
        "PFE_10_5": ta.pfe(close),
    }
    for out_col in ("OVNSUM_21", "INTSUM_21", "OVNINTDIFF_21"):
        for name, x in comparators.items():
            print(f"  {out_col} vs {name}: {rho(ovn[out_col], x)}")


if __name__ == "__main__":
    main()
