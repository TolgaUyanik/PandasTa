# -*- coding: utf-8 -*-
"""Print the environment stamp and Gate C/D synthetic numbers for
docs/VolvolMeasured.md.

    python docs/measure_volvol.py

Synthetic GBM walk with a fixed seed -- Gate C here is NOT Gate E, which needs
the parent repo's production column set and real BIST frames.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pandas_ta as ta


def ohlc(n=1200, seed=11, sigma=0.02, tick=None):
    rng = np.random.default_rng(seed)
    close = 100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n)))
    if tick:
        close = np.round(close / tick) * tick
    spread = np.abs(rng.normal(0.0, sigma / 4, n)) * close
    high = pd.Series(close + spread)
    low = pd.Series(close - spread)
    return high, low, pd.Series(close)


def main():
    print("== environment")
    print("python", sys.version.split()[0], "pandas", pd.__version__, "numpy", np.__version__)

    print("== Gate C (synthetic, 1200 bars, seed 11, tick 0.05)")
    high, low, close = ohlc(tick=0.05)
    out = ta.volvol(high, low, close)
    finite = out.dropna()
    nonzero = finite[finite != 0.0]
    print("finite", len(finite), "of", len(out),
          "nonzero", len(nonzero),
          "min", round(finite.min(), 6), "max", round(finite.max(), 6),
          "mean", round(finite.mean(), 6))

    print("== Gate D (scale)")
    for k in (8.0, 64.0):
        base = ta.volvol(high, low, close)
        scaled = ta.volvol(high * k, low * k, close * k)
        same_mask = (base.isna() == scaled.isna()).all()
        m = base.notna()
        bit_identical = bool((base[m] == scaled[m]).all())
        print(f"  x{k}: NaN masks match {same_mask}, bit-identical {bit_identical}")
    for k in (10.0, 3.7):
        base = ta.volvol(high, low, close)
        scaled = ta.volvol(high * k, low * k, close * k)
        print(f"  x{k}: max|diff| {(base - scaled).abs().max():.3e}")


if __name__ == "__main__":
    main()
