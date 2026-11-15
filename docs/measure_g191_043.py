# -*- coding: utf-8 -*-
"""Prints the exact numbers quoted in docs/G191043Measured.md for
`pandas_ta.volume.g191_043`. Synthetic frame only (Gate E, the real-data
measurement, is run by the launcher after this session)."""
import importlib
import types

import numpy as np
import pandas as pd
from pandas import Series

from pandas_ta.utils import signed_series
from pandas_ta.volume.g191_043 import g191_043

_REAL = importlib.import_module("pandas_ta.volume.g191_043")


def _walk(n=1500, seed=11, sigma=0.015):
    rng = np.random.default_rng(seed)
    close = 100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n)))
    return Series(close)


def _volume(n=1500, seed=97, lo=1e4, hi=1e6):
    rng = np.random.default_rng(seed)
    return Series(rng.uniform(lo, hi, n))


def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_g191_043_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


def main():
    close = _walk()
    volume = _volume()
    out = g191_043(close, volume)
    n = len(out)
    fires = int(out.notna().sum())
    nunique = int(out.dropna().nunique())
    first_valid = int(out.notna().idxmax()) if fires else None
    print(f"n={n} fires={fires} ({100 * fires / n:.2f}%) nunique={nunique} "
          f"first_valid_index={first_valid}")
    print(f"min={out.min():.6f} max={out.max():.6f} median={out.median():.6f}")

    m = out.notna()
    for k in (8.0, 64.0, 10.0, 3.7):
        scaled = g191_043(close, volume * k)
        max_diff = float((out[m] - scaled[m]).abs().max())
        mask_match = bool((out.isna() == scaled.isna()).all())
        print(f"x{k} volume max|diff|={max_diff} nan-mask-match={mask_match}")

    for k in (8.0, 64.0, 10.0, 3.7):
        scaled = g191_043(close * k, volume)
        max_diff = float((out[m] - scaled[m]).abs().max())
        mask_match = bool((out.isna() == scaled.isna()).all())
        print(f"x{k} price max|diff|={max_diff} nan-mask-match={mask_match}")

    # Gate A: hand-derived 9-bar example at length=3 (includes a flat-day
    # boundary bar).
    hand_close = Series([100.0, 105.0, 103.0, 103.0, 108.0, 95.0, 110.0, 100.0, 120.0])
    hand_volume = Series([10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0])
    hand_out = g191_043(hand_close, hand_volume, length=3)
    print("hand-derived bars 0..8:", list(hand_out.iloc[0:9]))
    delta = hand_close.diff()
    print("delta:", list(delta))
    print("sign (signed_series):", list(signed_series(hand_close)))

    # Gate A: signed_series(close) vs an explicit np.sign(delta(c,1)) ternary
    # agree bit-for-bit, including NaN masks, on the general case.
    sv = signed_series(close)
    explicit = pd.Series(np.sign(close.diff().to_numpy()), index=close.index)
    agree = bool((sv.isna() == explicit.isna()).all()
                 and (sv.dropna() == explicit.dropna()).all())
    zero_bars = int((close.diff() == 0.0).sum())
    print(f"signed_series-vs-ternary agree={agree} zero-delta-bars={zero_bars}")

    # Independent per-bar replay using plain numpy array slicing, not
    # pandas' own .rolling()/signed_series calls, spot-checking the shipped
    # defaults (length=6).
    big_close = _walk(900, seed=5)
    big_volume = _volume(900, seed=13)
    out_defaults = g191_043(big_close, big_volume)
    c = big_close.to_numpy(dtype=float)
    v = big_volume.to_numpy(dtype=float)
    length = 6
    for t in (300, 600, 899):
        num = 0.0
        den = 0.0
        for i in range(t - length + 1, t + 1):
            sign = 1.0 if c[i] > c[i - 1] else (-1.0 if c[i] < c[i - 1] else 0.0)
            num += sign * v[i]
            den += v[i]
        expected = num / den
        print(f"independent-loop bar {t}: module={out_defaults.iloc[t]!r} "
              f"loop={expected!r}")

    # Gate B: future-perturbation leak counts, real module vs. one mutant.
    other_c = _walk(seed=41)
    other_v = _volume(seed=59)
    offsets = range(150, 1500, 40)

    def leaks(fn):
        base = fn(close, volume)
        hits = 0
        for j in offsets:
            pc, pv = close.copy(), volume.copy()
            pc.iloc[j:] = other_c.iloc[j:].values
            pv.iloc[j:] = other_v.iloc[j:].values
            o = fn(pc, pv)
            a, b = base.iloc[:j], o.iloc[:j]
            if not (a.isna() == b.isna()).all():
                hits += 1
                continue
            mm = a.notna()
            if (a[mm] != b[mm]).any():
                hits += 1
        return hits

    total = len(list(offsets))
    print(f"real-module leaks: {leaks(g191_043)} of {total}")
    write_shift = _load_mutant(
        "result = (numerator / denominator).replace([np.inf, -np.inf], np.nan)",
        "result = (numerator / denominator).replace([np.inf, -np.inf], np.nan).shift(-length)",
    )
    print(f"write-shift mutant (length-bar look-ahead) leaks: "
          f"{leaks(write_shift.g191_043)} of {total}")


if __name__ == "__main__":
    main()
