# -*- coding: utf-8 -*-
"""Print the environment stamp and Gate C/D synthetic numbers for
docs/TfMedianAbsdiff20Measured.md.

    python docs/measure_tf_median_absdiff_20.py

Synthetic GBM walk with a fixed seed -- Gate C here is NOT Gate E, which needs
the parent repo's production column set and real BIST frames.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pandas_ta as ta


def walk(n=1200, seed=11, sigma=0.02, tick=None):
    c = 100.0 * np.exp(np.cumsum(np.random.default_rng(seed).normal(0.0, sigma, n)))
    if tick:
        c = np.round(c / tick) * tick
    return pd.Series(c)


def main():
    print("== environment")
    print("python", sys.version.split()[0], "pandas", pd.__version__, "numpy", np.__version__)

    print("== Gate C (synthetic, 1200 bars, seed 11, tick 0.05)")
    c = walk(tick=0.05)
    out = ta.tf_median_absdiff_20(c)
    finite = out.dropna()
    nonzero = finite[finite != 0.0]
    print("finite", len(finite), "of", len(out),
          "nonzero", len(nonzero),
          "min", finite.min(), "max", round(finite.max(), 6),
          "mean", round(finite.mean(), 6))

    print("== Gate D (scale)")
    for k in (8.0, 64.0):
        base, scaled = ta.tf_median_absdiff_20(c), ta.tf_median_absdiff_20(c * k)
        same_mask = (base.isna() == scaled.isna()).all()
        m = base.notna()
        bit_identical = bool((base[m] == scaled[m]).all())
        print(f"  x{k}: NaN masks match {same_mask}, bit-identical {bit_identical}")
    for k in (10.0, 3.7):
        base, scaled = ta.tf_median_absdiff_20(c), ta.tf_median_absdiff_20(c * k)
        print(f"  x{k}: max|diff| {(base - scaled).abs().max():.3e}")

    print("== Gate D, rejected form (NOT shipped): log(close).diff() instead of log(close/close.shift(1))")
    length = 20

    def rejected_form(close, length=length):
        logret = np.log(close).diff()
        return logret.abs().rolling(length).median()

    for k in (8.0, 64.0):
        base, scaled = rejected_form(c), rejected_form(c * k)
        m = base.notna()
        print(f"  x{k}: max|diff| {(base[m] - scaled[m]).abs().max():.3e}")


if __name__ == "__main__":
    main()
