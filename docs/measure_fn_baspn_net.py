# -*- coding: utf-8 -*-
"""Print the environment stamp, Gate A/C/D synthetic numbers, and the live
`Category` counts for docs/FnBaspnNetMeasured.md and
tests/test_altport2_ports.py.

    python docs/measure_fn_baspn_net.py

Synthetic GBM walk with a fixed seed -- Gate C here is NOT Gate E, which
needs the parent repo's production column set and real BIST frames.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pandas_ta as ta
from pandas_ta.volume.fn_baspn_net import fn_baspn_net

SLOW, FAST = 40, 20


def walk(n=1200, seed=11, sigma=0.02, wick=0.004, tick=None):
    rng = np.random.default_rng(seed)
    close = 100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n)))
    if tick:
        close = np.round(close / tick) * tick
    hi_wick = np.abs(rng.normal(0.0, wick, n)) + 1e-6
    lo_wick = np.abs(rng.normal(0.0, wick, n)) + 1e-6
    high = close * (1.0 + hi_wick)
    low = close * (1.0 - lo_wick)
    volume = 1_000.0 * np.exp(rng.normal(0.0, 0.5, n))
    return pd.Series(high), pd.Series(low), pd.Series(close), pd.Series(volume)


def _ema_ref(x, length):
    x = np.asarray(x, dtype=float)
    n = len(x)
    out = np.full(n, np.nan)
    if n < length:
        return out
    alpha = 2.0 / (length + 1.0)
    seed_window = x[:length]
    sma = np.nan if np.isnan(seed_window).any() else seed_window.mean()
    modified = x.copy()
    modified[:length - 1] = np.nan
    modified[length - 1] = sma
    prev = None
    for i in range(n):
        v = modified[i]
        if np.isnan(v):
            continue
        out[i] = v if prev is None else alpha * v + (1.0 - alpha) * prev
        prev = out[i]
    return out


def _reference(high, low, close, volume, slow=SLOW, fast=FAST):
    h, l, c, v = (np.asarray(s, dtype=float) for s in (high, low, close, volume))
    ema_v = _ema_ref(v, slow)
    nv = np.where(ema_v == 0, np.nan, v / ema_v)
    bp, sp = c - l, h - c
    ema_bp, ema_sp = _ema_ref(bp, slow), _ema_ref(sp, slow)
    buy_ratio = np.where(ema_bp == 0, np.nan, bp / ema_bp)
    sell_ratio = np.where(ema_sp == 0, np.nan, sp / ema_sp)
    buy = _ema_ref(buy_ratio * nv, fast)
    sell = _ema_ref(sell_ratio * nv, fast)
    return buy - sell


def main():
    print("== environment")
    print("python", sys.version.split()[0], "pandas", pd.__version__, "numpy", np.__version__)

    high, low, close, volume = walk()

    print("== Gate A (independent scalar-loop EMA re-implementation vs. shipped column)")
    loop = _reference(high, low, close, volume)
    out = fn_baspn_net(high, low, close, volume)
    m = out.notna().to_numpy() & ~np.isnan(loop)
    print("compared bars", int(m.sum()),
          "max|diff|", float(np.max(np.abs(out.to_numpy()[m] - loop[m]))))
    print("NaN masks match:", bool((out.isna().to_numpy() == np.isnan(loop)).all()))
    print("first finite bar (0-indexed):", int(out.notna().to_numpy().argmax()))

    print("== Gate C (synthetic, 1200 bars, seed 11)")
    finite = out.dropna()
    nonzero = finite[finite != 0.0]
    print("finite", len(finite), "of", len(out),
          "nonzero", len(nonzero),
          "pos", int((finite > 0).sum()), "neg", int((finite < 0).sum()),
          "min", round(float(finite.min()), 6),
          "max", round(float(finite.max()), 6),
          "mean", round(float(finite.mean()), 6),
          "distinct", int(finite.nunique()))

    print("== Gate D (scale)")
    for k in (8.0, 64.0):
        base = fn_baspn_net(high, low, close, volume)
        scaled_p = fn_baspn_net(high * k, low * k, close * k, volume)
        scaled_v = fn_baspn_net(high, low, close, volume * k)
        mm = base.notna()
        print(f"  x{k} price-only: NaN masks match "
              f"{bool((base.isna() == scaled_p.isna()).all())}, bit-identical "
              f"{bool((base[mm] == scaled_p[mm]).all())}")
        print(f"  x{k} volume-only: NaN masks match "
              f"{bool((base.isna() == scaled_v.isna()).all())}, bit-identical "
              f"{bool((base[mm] == scaled_v[mm]).all())}")
    for k in (10.0, 3.7):
        base = fn_baspn_net(high, low, close, volume)
        scaled_p = fn_baspn_net(high * k, low * k, close * k, volume)
        scaled_v = fn_baspn_net(high, low, close, volume * k)
        mm = base.notna() & scaled_p.notna()
        diff_p = (base[mm] - scaled_p[mm]).abs()
        mm2 = base.notna() & scaled_v.notna()
        diff_v = (base[mm2] - scaled_v[mm2]).abs()
        print(f"  x{k} price-only: max|diff| {float(diff_p.max()):.3e}")
        print(f"  x{k} volume-only: max|diff| {float(diff_v.max()):.3e}")

    print("== live Category counts")
    total = sum(len(v) for v in ta.Category.values())
    print("Category total", total)
    print("Category['volume'] size", len(ta.Category["volume"]))
    print("fn_baspn_net in Category['volume']:", "fn_baspn_net" in ta.Category["volume"])


if __name__ == "__main__":
    main()
