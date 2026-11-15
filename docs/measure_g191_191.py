# -*- coding: utf-8 -*-
"""Prints the exact numbers quoted in docs/G191191Measured.md for
`pandas_ta.volume.g191_191`. Synthetic frame only (Gate E, the real-data
measurement, is run by the launcher after this session)."""
import importlib
import types

import numpy as np
import pandas as pd
from pandas import Series

from pandas_ta.volume.g191_191 import g191_191

_REAL = importlib.import_module("pandas_ta.volume.g191_191")


def _ohlcv(n=1500, seed=11, sigma=0.015, vol_seed=23):
    rng = np.random.default_rng(seed)
    close = 100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n)))
    rng2 = np.random.default_rng(seed + 1)
    spread = np.abs(rng2.normal(0.0, 0.01, n)) * close
    high = close + spread * rng2.uniform(0.2, 1.0, n)
    low = close - spread * rng2.uniform(0.2, 1.0, n)
    rng3 = np.random.default_rng(vol_seed)
    volume = np.abs(rng3.normal(1_000_000.0, 300_000.0, n)) + 1.0
    idx = pd.RangeIndex(n)
    return (Series(high, index=idx), Series(low, index=idx),
            Series(close, index=idx), Series(volume, index=idx))


def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_g191_191_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


def main():
    high, low, close, volume = _ohlcv()
    out = g191_191(high, low, close, volume)
    n = len(out)
    fires = int(out.notna().sum())
    nunique = int(out.dropna().nunique())
    first_valid = int(out.notna().idxmax()) if fires else None
    print(f"n={n} fires={fires} ({100 * fires / n:.2f}%) nunique={nunique} "
          f"first_valid_index={first_valid}")
    print(f"min={out.min():.6f} max={out.max():.6f} median={out.median():.6f}")

    m = out.notna()
    for k in (8.0, 64.0, 10.0, 3.7):
        scaled = g191_191(high * k, low * k, close * k, volume)
        max_diff = float((out[m] - scaled[m]).abs().max())
        mask_match = bool((out.isna() == scaled.isna()).all())
        print(f"x{k} PRICE max|diff|={max_diff} nan-mask-match={mask_match}")
    for k in (8.0, 64.0, 10.0, 3.7):
        scaled = g191_191(high, low, close, volume * k)
        max_diff = float((out[m] - scaled[m]).abs().max())
        mask_match = bool((out.isna() == scaled.isna()).all())
        print(f"x{k} VOLUME max|diff|={max_diff} nan-mask-match={mask_match}")

    # Gate A: hand-derived small example, mean_length=3, corr_length=2.
    hc = Series([10.0, 9.0, 11.0, 8.0, 12.0, 7.0])
    hl = Series([9.0, 8.5, 10.0, 7.5, 11.0, 6.5])
    hh = Series([10.5, 9.5, 11.5, 8.5, 12.5, 7.5])
    hv = Series([100.0, 200.0, 150.0, 300.0, 250.0, 400.0])
    hout = g191_191(hh, hl, hc, hv, mean_length=3, corr_length=2)
    mean_v = hv.rolling(3).mean()
    corr_term = mean_v.rolling(2, min_periods=2).corr(hl)
    gap_term = ((hh + hl) / 2.0 - hc) / hc
    print("hand mean_v:", list(mean_v))
    print("hand corr_term:", list(corr_term))
    print("hand gap_term:", list(gap_term))
    print("hand result:", list(hout))

    # Gate B: future-perturbation leak counts, real module vs. two mutants.
    other_c, other_l, other_h, other_v = None, None, None, None
    other_h2, other_l2, other_c2, other_v2 = _ohlcv(seed=97, vol_seed=71)
    offsets = range(150, 1500, 40)

    def leaks(fn):
        base = fn(high, low, close, volume)
        hits = 0
        for j in offsets:
            ph, pl, pc, pv = high.copy(), low.copy(), close.copy(), volume.copy()
            ph.iloc[j:] = other_h2.iloc[j:].values
            pl.iloc[j:] = other_l2.iloc[j:].values
            pc.iloc[j:] = other_c2.iloc[j:].values
            pv.iloc[j:] = other_v2.iloc[j:].values
            o = fn(ph, pl, pc, pv)
            a, b = base.iloc[:j], o.iloc[:j]
            if not (a.isna() == b.isna()).all():
                hits += 1
                continue
            mm = a.notna()
            if (a[mm] != b[mm]).any():
                hits += 1
        return hits

    total = len(list(offsets))
    print(f"real-module leaks: {leaks(g191_191)} of {total}")
    shipped = _load_mutant(
        "result = result.where(mask).replace([np.inf, -np.inf], np.nan)",
        "result = result.where(mask).replace([np.inf, -np.inf], np.nan).shift(-corr_length)",
    )
    print(f"shipped mutant (corr_length-bar write shift) leaks: "
          f"{leaks(shipped.g191_191)} of {total}")
    weaker = _load_mutant(
        "mean_v = volume.rolling(mean_length).mean()",
        "mean_v = volume.rolling(mean_length, center=True).mean()",
    )
    print(f"weaker mutant (centered MEAN) leaks: {leaks(weaker.g191_191)} of {total}")


if __name__ == "__main__":
    main()
