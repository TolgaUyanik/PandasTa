# -*- coding: utf-8 -*-
"""Proxy measurement for `ewmac` (issue #29): reachability, scale-free
tolerance, and a synthetic proxy overlap against a handful of guessed
comparators. NOT Gate E -- one synthetic walk, not the 89 BIST frames.
Numbers printed here are quoted verbatim into docs/EwmacMeasured.md.
"""
import numpy as np
from pandas import Series

from pandas_ta.momentum.ewmac import ewmac, PAIRS
from pandas_ta.momentum.macd import macd
from pandas_ta.volatility.natr import natr


def _walk(n=1200, seed=11, sigma=0.02, tick=None):
    rng = np.random.default_rng(seed)
    c = 100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n)))
    if tick:
        c = np.round(c / tick) * tick
    return Series(c)


def main():
    import sys
    import pandas
    print(f"pandas={pandas.__version__} numpy={np.__version__} python={sys.version.split()[0]}")
    close = _walk(tick=0.05)
    df = ewmac(close)
    print("columns:", df.columns.tolist())
    print("shape:", df.shape)

    for col in df.columns:
        s = df[col]
        fires = s.dropna()
        print(f"{col}: nonNaN={len(fires)}/{len(s)} nonzero={int((fires != 0).sum())} "
              f"nunique={s.nunique()} min={fires.min():.4f} max={fires.max():.4f}")

    for k in (8.0, 64.0):
        scaled = ewmac(close * k)
        for col, col2 in zip(df.columns, scaled.columns):
            a, b = df[col], scaled[col2]
            m = a.notna()
            identical = bool((a[m] == b[m]).all())
            print(f"x{k} bit-identical {col}: {identical}")

    for k in (10.0, 3.7):
        scaled = ewmac(close * k)
        for col, col2 in zip(df.columns, scaled.columns):
            a, b = df[col], scaled[col2]
            m = a.notna()
            diff = float((a[m] - b[m]).abs().max())
            print(f"x{k} max abs diff {col}: {diff:.3e}")

    # Proxy overlap (not Gate E): vs MACD_pct-style ratio and natr, closest
    # guesses from the issue's own overlap note, same (fast, slow) pairs
    # where they exist (12/26 is MACD's pair; EWMAC does not ship 12/26).
    high = close * 1.001
    low = close * 0.999
    natr14 = natr(high, low, close, length=14)
    macd_12_26 = macd(close, fast=12, slow=26, signal=9)["MACD_12_26_9"]
    macd_pct = macd_12_26 / close * 100

    for col in df.columns:
        s = df[col]
        common = s.to_frame("e").join(macd_pct.rename("macd_pct")).join(natr14.rename("natr")).dropna()
        if len(common) < 10:
            print(f"{col}: not enough overlap with proxy comparators")
            continue
        rho_macd = common["e"].corr(common["macd_pct"], method="spearman")
        rho_natr = common["e"].corr(common["natr"], method="spearman")
        print(f"{col} vs MACD_pct(12,26): rho={rho_macd:.4f} n={len(common)}")
        print(f"{col} vs NATR_14: rho={rho_natr:.4f} n={len(common)}")


if __name__ == "__main__":
    main()
