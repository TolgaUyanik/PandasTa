# -*- coding: utf-8 -*-
"""Print the environment stamp, Gate A/C/D synthetic numbers, and the live
`Category` counts for docs/TtrSnr20Measured.md and
tests/test_altport2_ports.py.

    python docs/measure_ttr_snr_20.py

Synthetic GBM walk with a fixed seed -- Gate C here is NOT Gate E, which
needs the parent repo's production column set and real BIST frames.
"""
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pandas_ta as ta
from pandas_ta.volatility.ttr_snr_20 import ttr_snr_20

LENGTH = 20


def walk(n=1200, seed=11, sigma=0.02, tick=None, wick=0.004):
    rng = np.random.default_rng(seed)
    close = 100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n)))
    if tick:
        close = np.round(close / tick) * tick
    hi_wick = np.abs(rng.normal(0.0, wick, n))
    lo_wick = np.abs(rng.normal(0.0, wick, n))
    high = close * (1.0 + hi_wick)
    low = close * (1.0 - lo_wick)
    return pd.Series(high), pd.Series(low), pd.Series(close)


def _wilder_atr_loop(high, low, close, length=LENGTH):
    """Independent scalar-loop ATR: SMA-seeded Wilder recursion, written
    from Wilder's own definition rather than imported from this package."""
    h, l, c = high.to_numpy(), low.to_numpy(), close.to_numpy()
    n = len(c)
    tr = np.full(n, np.nan)
    for i in range(1, n):
        tr[i] = max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1]))
    atr = np.full(n, np.nan)
    seed = tr[1:length + 1].mean()
    atr[length] = seed
    for i in range(length + 1, n):
        atr[i] = (atr[i - 1] * (length - 1) + tr[i]) / length
    return pd.Series(atr, index=close.index)


def main():
    print("== environment")
    print("python", sys.version.split()[0], "pandas", pd.__version__, "numpy", np.__version__)

    high, low, close = walk()

    print("== Gate A (independent scalar-loop ATR vs. shipped column)")
    loop_atr = _wilder_atr_loop(high, low, close)
    loop_snr = (close - close.shift(LENGTH)).abs() / loop_atr
    out = ttr_snr_20(high, low, close)
    m = out.notna() & loop_snr.notna()
    print("compared bars", int(m.sum()),
          "max|diff|", float((out[m] - loop_snr[m]).abs().max()))

    print("== Gate C (synthetic, 1200 bars, seed 11)")
    finite = out.dropna()
    nonzero = finite[finite != 0.0]
    print("finite", len(finite), "of", len(out),
          "nonzero", len(nonzero),
          "min", round(float(finite.min()), 6),
          "max", round(float(finite.max()), 6),
          "mean", round(float(finite.mean()), 6),
          "distinct", int(finite.nunique()))

    print("== Gate D (scale)")
    for k in (8.0, 64.0):
        base = ttr_snr_20(high, low, close)
        scaled = ttr_snr_20(high * k, low * k, close * k)
        same_mask = (base.isna() == scaled.isna()).all()
        mm = base.notna()
        bit_identical = bool((base[mm] == scaled[mm]).all())
        print(f"  x{k}: NaN masks match {same_mask}, bit-identical {bit_identical}")
    for k in (10.0, 3.7):
        base = ttr_snr_20(high, low, close)
        scaled = ttr_snr_20(high * k, low * k, close * k)
        mm = base.notna() & scaled.notna()
        diff = (base[mm] - scaled[mm]).abs()
        rel = (diff / base[mm].where(base[mm] != 0)).max()
        print(f"  x{k}: max|diff| {float(diff.max()):.3e}, "
              f"max relative {float(rel) if math.isfinite(rel) else float('nan'):.3e}")

    print("== frozen-from-bar-0 edge case (TR == 0 EVERY bar -> ATR == 0 exactly)")
    flat = pd.Series(np.full(60, 100.0))
    flat_out = ttr_snr_20(flat, flat, flat)
    print("finite", int(flat_out.notna().sum()), "all NaN" if flat_out.notna().sum() == 0
          else f"values: {sorted(flat_out.dropna().unique())[:5]}")
    from pandas_ta.volatility.atr import atr as _atr
    dbg_atr = _atr(flat, flat, flat, length=LENGTH, mamode="wrma")
    dbg_move = (flat - flat.shift(LENGTH)).abs()
    print("  debug atr[20:25]", list(dbg_atr.iloc[20:25]))
    print("  debug move[20:25]", list(dbg_move.iloc[20:25]))

    print("== frozen-AFTER-a-volatile-run edge case (TR == 0 for `length` bars, "
          "ATR decays but does not reach exactly 0 -> SNR positive, not NaN)")
    n = 60
    half_life_close = pd.Series(np.concatenate([
        100.0 * np.exp(np.cumsum(np.random.default_rng(5).normal(0.0, 0.01, 30))),
        np.full(30, 100.0),
    ]))
    decayed = ttr_snr_20(half_life_close, half_life_close, half_life_close)
    tail = decayed.iloc[-9:]
    print("tail all NaN:", bool(tail.isna().all()),
          "tail values:", [round(float(v), 6) for v in tail])

    print("== live Category counts")
    total = sum(len(v) for v in ta.Category.values())
    print("Category total", total)
    print("Category['volatility'] size", len(ta.Category["volatility"]))
    print("ttr_snr_20 in Category['volatility']:", "ttr_snr_20" in ta.Category["volatility"])


if __name__ == "__main__":
    main()
