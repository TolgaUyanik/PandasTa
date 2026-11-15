# -*- coding: utf-8 -*-
"""Prints the exact numbers quoted in docs/DemandMeasured.md for
`pandas_ta.volume.demand`. Synthetic frame only (Gate E, the real-data
measurement, is run by the launcher after this session)."""
import numpy as np
from pandas import Series

from pandas_ta.volume.demand import demand


def _walk(n=1200, seed=17, sigma=0.015, tick=0.05):
    rng = np.random.default_rng(seed)
    close = 100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n)))
    if tick:
        close = np.round(close / tick) * tick
    spread = np.abs(rng.normal(0.0, 0.01, n)) * close + (tick or 0.0)
    high = close + spread
    low = close - spread
    volume = rng.integers(1e4, 1e6, n).astype(float)
    return Series(high), Series(low), Series(close), Series(volume)


def main():
    high, low, close, volume = _walk()
    out = demand(high, low, close, volume)
    n = len(out)
    fires = int(out.notna().sum())
    nunique = int(out.dropna().nunique())
    print(f"n={n} fires={fires} ({100 * fires / n:.2f}%) nunique={nunique}")
    print(f"min={out.min():.6f} max={out.max():.6f} median={out.median():.6f} "
          f"abs-median={out.abs().median():.6f}")

    flat = int((close.diff() == 0).sum())
    print(f"exact-flat (close[t]==close[t-1]) bars: {flat}")

    for k in (8.0, 64.0):
        price_scaled = demand(high * k, low * k, close * k, volume)
        vol_scaled = demand(high, low, close, volume * k)
        m = out.notna()
        print(f"x{k} price max|diff|={float((out[m] - price_scaled[m]).abs().max())} "
              f"volume max|diff|={float((out[m] - vol_scaled[m]).abs().max())}")

    for k in (10.0, 3.7):
        price_scaled = demand(high * k, low * k, close * k, volume)
        vol_scaled = demand(high, low, close, volume * k)
        m = out.notna()
        print(f"x{k} price max|diff|={float((out[m] - price_scaled[m]).abs().max())} "
              f"volume max|diff|={float((out[m] - vol_scaled[m]).abs().max())}")


if __name__ == "__main__":
    main()
