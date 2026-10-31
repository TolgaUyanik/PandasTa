# -*- coding: utf-8 -*-
"""Print every number in docs/CrsiMeasured.md: the hand-computed streak,
warm-up, scale tolerance, Gate C (synthetic) and proxy overlap against this
package's own [0, 100]-bounded oscillators.

    python docs/measure_crsi_proxy.py

Synthetic GBM walks with fixed seeds -- a PROXY, not Gate E, which needs the
parent repo's production column set and the 89 BIST frames.
"""
import platform
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pandas_ta as ta
from pandas_ta.momentum.crsi import _signed_streak, _percent_rank

COL = "CRSI_3_2_100"


def walk(n=3000, sigma=0.02, seed=1, tick=None):
    c = 100.0 * np.exp(np.cumsum(np.random.default_rng(seed).normal(0.0, sigma, n)))
    if tick:
        c = np.round(c / tick) * tick
    return pd.Series(c)


def rho(a, b):
    return round(a.corr(b, method="spearman"), 4)


def comparators(c):
    return {
        "RSI_3": ta.rsi(c, 3), "RSI_14": ta.rsi(c, 14),
        "CMO_14": ta.cmo(c), "STOCHRSIk_14_14_3_3": ta.stochrsi(c).iloc[:, 0],
        "WILLR_14": ta.willr(c, c, c, 14), "ROC_1": ta.roc(c, 1), "ROC_5": ta.roc(c, 5),
    }


def main():
    print("== environment", platform.python_version(), "pandas", pd.__version__, "numpy", np.__version__)

    print("== hand-computed streak: closes 10,11,12,11,10,9,10")
    closes = pd.Series([10.0, 11, 12, 11, 10, 9, 10])
    streak = _signed_streak(closes)
    print(" ", streak.tolist())

    print("== hand-computed percent rank, length=3: values 5,6,4,7")
    series = pd.Series([5.0, 6.0, 4.0, 7.0])
    pr = _percent_rank(series, 3)
    print(" ", pr.tolist())

    print("== warm-up (first non-NaN index) at defaults, 1200-bar walk")
    c = walk(1200, seed=11, tick=0.05)
    out = ta.crsi(c)
    for col in out:
        fi = out[col].first_valid_index()
        print(f"  {col}: first valid at {fi}, NaN count {out[col].isna().sum()}")

    print("== scale: max |diff| vs x1 (same walk)")
    base = ta.crsi(c)
    for k in (8.0, 64.0, 10.0, 3.7):
        scaled = ta.crsi(c * k)
        same_mask = (base.isna() == scaled.isna()).all().all()
        diff = (base - scaled).abs().max().max()
        print(f"  x{k}: mask_match={same_mask} max|diff|={diff:.3e}")

    print("== bounds [0, 100] and Gate C synthetic (1200-bar walk, tick 0.05)")
    for col in out:
        x = out[col].dropna()
        print(f"  {col}: min {x.min():.4f} max {x.max():.4f} finite {len(x)} "
              f"nonzero {int((x != 0).sum())} below50 {int((x < 50).sum())} above50 {int((x > 50).sum())} "
              f"nunique {x.nunique()}")

    print("== proxy overlap (sigma 0.02, seed 1, n=3000)")
    c = walk(3000, sigma=0.02, seed=1)
    full = ta.crsi(c)
    composite, streak_col, pct_col = full[COL], full["CRSI_STREAK_2"], full["CRSI_PCTRANK_100"]
    n = int(composite.notna().sum())
    print("  n comparable", n)
    for name, x in comparators(c).items():
        print(f"  {name:22s} composite {rho(composite, x):8.4f}   streak {rho(streak_col, x):8.4f}"
              f"   pctrank {rho(pct_col, x):8.4f}")
    print(f"  composite vs streak {rho(composite, streak_col):.4f}  composite vs pctrank {rho(composite, pct_col):.4f}"
          f"  streak vs pctrank {rho(streak_col, pct_col):.4f}")


if __name__ == "__main__":
    main()
