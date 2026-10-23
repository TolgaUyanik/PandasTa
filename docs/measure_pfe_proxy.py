# -*- coding: utf-8 -*-
"""Print the proxy-overlap and Gate C numbers in docs/PfeMeasured.md and docs/SignedErMeasured.md.

    python docs/measure_pfe_proxy.py

Synthetic GBM walks with fixed seeds -- a PROXY, not Gate E, which needs the
parent repo's production column set. `signed_er` was removed, so its raw form
is rebuilt here as er * sign(close.diff(length)), the identity it was built on.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pandas_ta as ta


def walk(n=3000, sigma=0.02, seed=1, tick=None):
    c = 100.0 * np.exp(np.cumsum(np.random.default_rng(seed).normal(0.0, sigma, n)))
    if tick:
        c = np.round(c / tick) * tick
    return pd.Series(c)


def rho(a, b):
    return round(a.corr(b, method="spearman"), 4)


def comparators(c):
    return {
        "CMO_10 (talib=False)": ta.cmo(c, 10, talib=False), "ROC_10": ta.roc(c, 10),
        "SLOPE_10": ta.slope(c, 10), "CMO_14 (default)": ta.cmo(c), "RSI_14": ta.rsi(c),
        "ER_10": ta.er(c),
    }


def main():
    c = walk()
    print("== signed ER (removed)")
    raw = ta.er(c, 10) * np.sign(c.diff(10))
    cmo_sum = ta.cmo(c, 10, talib=False) / 100
    print("raw vs cmo(talib=False)/100: max|diff|", (raw - cmo_sum).abs().max(),
          "rho", rho(raw, cmo_sum), "n", int((raw.notna() & cmo_sum.notna()).sum()))
    cmo_rma = ta.cmo(c, 10) / 100
    print("raw vs cmo(talib=True)/100: max|diff|", round((raw - cmo_rma).abs().max(), 4),
          "rho", rho(raw, cmo_rma))
    ser = raw.ewm(span=5, adjust=False).mean()
    for name, x in comparators(c).items():
        print(f"  SER_10_5 vs {name}: {rho(ser, x)}")

    print("== pfe")
    p = ta.pfe(c)
    print("n comparable", int(p.notna().sum()))
    for name, x in comparators(c).items():
        print(f"  PFE_10_5 vs {name}: {rho(p, x)}")
    print("volatility sweep: sigma, median |raw PFE|, rho vs CMO_10 sum, rho vs ROC_10")
    for s in (0.001, 0.005, 0.01, 0.02, 0.05):
        c = walk(sigma=s)
        sm = ta.pfe(c)
        print(" ", s, round(ta.pfe(c, smooth=1).abs().median(), 2),
              rho(sm, ta.cmo(c, 10, talib=False)), rho(sm, ta.roc(c, 10)))
    c = walk(1200, seed=11, tick=0.05)
    p = ta.pfe(c).dropna()
    print("Gate C synthetic (1200 bars, seed 11, tick 0.05): finite", len(p),
          "nonzero", int((p != 0).sum()), "pos", int((p > 0).sum()), "neg", int((p < 0).sum()))


if __name__ == "__main__":
    main()
