# -*- coding: utf-8 -*-
"""Gate B/C/D numbers for `adxr`, quoted in docs/AdxrMeasured.md.

Synthetic only -- no Backtesting engine access in this worktree. Run:
    python docs/measure_adxr_proxy.py
"""
import numpy as np
from pandas import Series

from pandas_ta.trend.adx import adx
from pandas_ta.trend.adxr import adxr


def _ohlc(n=900, seed=11, sigma=0.015, drift=0.0, start=100.0):
    rng = np.random.default_rng(seed)
    lr = rng.normal(drift, sigma, n)
    c = start * np.exp(np.cumsum(lr))
    h = c * (1.0 + np.abs(rng.normal(0, 0.006, n)))
    l = c * (1.0 - np.abs(rng.normal(0, 0.006, n)))
    return Series(h), Series(l), Series(c)


def main():
    h, l, c = _ohlc(n=900, sigma=0.02)
    out = adxr(h, l, c)
    fires = int(out.notna().sum())
    print(f"Gate C/D fires: {fires} of {len(out)} bars, "
          f"{out.dropna().nunique()} distinct values, "
          f"range [{out.min():.6f}, {out.max():.6f}]")

    OFFSETS = list(range(60, 850, 55))
    print(f"Gate B offsets swept: {len(OFFSETS)} ({OFFSETS[0]}..{OFFSETS[-1]} step 55)")

    h8, l8, c8 = h * 8.0, l * 8.0, c * 8.0
    base, scaled8 = adxr(h, l, c), adxr(h8, l8, c8)
    m = base.notna()
    max_diff_x8 = (base[m] - scaled8[m]).abs().max()
    print(f"x8 max |diff|: {max_diff_x8}")

    h10, l10, c10 = h * 10.0, l * 10.0, c * 10.0
    scaled10 = adxr(h10, l10, c10)
    max_diff_x10 = (base[m] - scaled10[m]).abs().max()
    print(f"x10 max |diff|: {max_diff_x10}")


if __name__ == "__main__":
    main()
