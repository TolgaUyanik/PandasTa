# -*- coding: utf-8 -*-
"""Prints the exact numbers quoted in docs/G191002Measured.md for
`pandas_ta.momentum.g191_002`. Synthetic frame only (Gate E, the real-data
measurement, is run by the launcher after this session)."""
import importlib
import types

import numpy as np
import pandas as pd
import pandas_ta as ta
from pandas import Series

from pandas_ta.momentum.g191_002 import g191_002

_REAL = importlib.import_module("pandas_ta.momentum.g191_002")


def _walk(n=1500, seed=11, sigma=0.015):
    rng = np.random.default_rng(seed)
    close = 100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n)))
    high = close * (1.0 + np.abs(rng.normal(0.0, sigma * 0.5, n)))
    low = close * (1.0 - np.abs(rng.normal(0.0, sigma * 0.5, n)))
    idx = pd.RangeIndex(n)
    return Series(high, index=idx), Series(low, index=idx), Series(close, index=idx)


def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_g191_002_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


MUTANT = (
    "result = -d1",
    "result = (-d1).shift(-30)",  # a 30-bar look-ahead
)

OFFSETS = range(50, 1500, 40)  # past the 2-bar warm-up


def _leaks(fn):
    high, low, close = _walk(1500)
    other_h, other_l, other_c = _walk(1500, seed=97)
    base = fn(high, low, close)
    hits = 0
    for j in OFFSETS:
        ph, pl, pc = high.copy(), low.copy(), close.copy()
        ph.iloc[j:] = other_h.iloc[j:].values
        pl.iloc[j:] = other_l.iloc[j:].values
        pc.iloc[j:] = other_c.iloc[j:].values
        out = fn(ph, pl, pc)
        a, b = base.iloc[:j], out.iloc[:j]
        if not (a.isna() == b.isna()).all():
            hits += 1
            continue
        m = a.notna()
        if (a[m] != b[m]).any():
            hits += 1
    return hits


def main():
    print("wiring:")
    print("  g191_002 in Category['momentum']:", "g191_002" in ta.Category["momentum"])
    print("  Category total:", sum(len(v) for v in ta.Category.values()))
    print("  Category['momentum'] size:", len(ta.Category["momentum"]))

    high, low, close = _walk()
    out = g191_002(high, low, close)
    n = len(out)
    fires = int(out.notna().sum())
    nunique = int(out.dropna().nunique())
    first_valid = int(out.notna().idxmax()) if fires else None
    print(f"n={n} fires={fires} ({100 * fires / n:.2f}%) nunique={nunique} "
          f"first_valid_index={first_valid}")
    print(f"min={out.min():.6f} max={out.max():.6f} median={out.median():.6f}")

    # Zero-range (high==low) bar count on this synthetic walk.
    zero_range = int((high == low).sum())
    print(f"zero-range (high==low) bars: {zero_range} of {n}")

    m = out.notna()
    for k in (8.0, 64.0, 10.0, 3.7):
        scaled = g191_002(high * k, low * k, close * k)
        max_diff = float((out[m] - scaled[m]).abs().max())
        mask_match = bool((out.isna() == scaled.isna()).all())
        print(f"x{k} PRICE max|diff|={max_diff} nan-mask-match={mask_match}")

    # Gate A: hand-derived eight-bar example (length=3), same OHLC numbers
    # as a101_053's own hand-derived example for cross-checking, but a
    # DIFFERENT denominator (high-low, not close-low).
    high8 = Series([10.0, 11.0, 12.0, 13.0, 9.0, 20.0, 8.0, 21.0])
    low8 = Series([8.0, 9.0, 9.0, 11.0, 7.0, 15.0, 6.0, 16.0])
    close8 = Series([9.0, 10.0, 11.0, 12.0, 8.0, 19.0, 7.0, 20.0])
    out8 = g191_002(high8, low8, close8, length=3)
    print("hand-derived 8-bar example (length=3):", out8.tolist())

    # Gate A: zero-range (high==low) denominator example.
    high5 = Series([10.0, 12.0, 13.0, 10.0, 16.0])
    low5 = Series([10.0, 8.0, 9.0, 10.0, 11.0])
    close5 = Series([10.0, 11.0, 12.0, 10.0, 15.0])
    out5 = g191_002(high5, low5, close5, length=1)
    print("zero-range-denominator example (length=1):", out5.tolist())

    # Gate A: independent per-bar spot check at the shipped default.
    high9, low9, close9 = _walk(900, seed=5)
    out9 = g191_002(high9, low9, close9)
    hh, ll, cc = (s.to_numpy(dtype=float) for s in (high9, low9, close9))
    length = 1

    def clv_at(t):
        return (2.0 * cc[t] - hh[t] - ll[t]) / (hh[t] - ll[t])

    def expected_at(t):
        return -(clv_at(t) - clv_at(t - length))

    for t in (300, 600, 899):
        print(f"t={t} module={out9.iloc[t]!r} independent={expected_at(t)!r}")

    # Gate B: future-perturbation leak counts, real module vs. the mutant.
    print(f"real-module leaks: {_leaks(g191_002)} of {len(list(OFFSETS))}")
    mutant = _load_mutant(*MUTANT)
    print(f"write-shift mutant leaks: {_leaks(mutant.g191_002)} of {len(list(OFFSETS))}")
    print("mutant live-differs-from-real:",
          not mutant.g191_002(high, low, close).equals(g191_002(high, low, close)))


if __name__ == "__main__":
    main()
