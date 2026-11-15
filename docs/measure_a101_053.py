# -*- coding: utf-8 -*-
"""Prints the exact numbers quoted in docs/A101053Measured.md for
`pandas_ta.momentum.a101_053`. Synthetic frame only (Gate E, the real-data
measurement, is run by the launcher after this session)."""
import importlib
import types

import numpy as np
from pandas import Series

from pandas_ta.momentum.a101_053 import a101_053

_REAL = importlib.import_module("pandas_ta.momentum.a101_053")


def _walk(n=1500, seed=11, sigma=0.015):
    rng = np.random.default_rng(seed)
    close = 100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n)))
    high = close * (1.0 + np.abs(rng.normal(0.0, sigma * 0.5, n)))
    low = close * (1.0 - np.abs(rng.normal(0.0, sigma * 0.5, n)))
    return Series(high), Series(low), Series(close)


def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_a101_053_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


def main():
    high, low, close = _walk()
    out = a101_053(high, low, close)
    n = len(out)
    fires = int(out.notna().sum())
    nunique = int(out.dropna().nunique())
    first_valid = int(out.notna().idxmax()) if fires else None
    print(f"n={n} fires={fires} ({100 * fires / n:.2f}%) nunique={nunique} "
          f"first_valid_index={first_valid}")
    print(f"min={out.min():.6f} max={out.max():.6f} median={out.median():.6f}")

    min_denom = (close - low).abs().min()
    print(f"min |close-low| on this walk={min_denom:.6e}")

    m = out.notna()
    for k in (8.0, 64.0, 10.0, 3.7):
        scaled = a101_053(high * k, low * k, close * k)
        max_diff = float((out[m] - scaled[m]).abs().max())
        mask_match = bool((out.isna() == scaled.isna()).all())
        print(f"x{k} price max|diff|={max_diff} nan-mask-match={mask_match}")

    # Gate A: hand-derived 8-bar example, length=3 (see
    # tests/test_a101_053.py::test_hand_derived_eight_bars).
    hand_high = Series([10.0, 11.0, 12.0, 13.0, 9.0, 20.0, 8.0, 21.0])
    hand_low = Series([8.0, 9.0, 9.0, 11.0, 7.0, 15.0, 6.0, 16.0])
    hand_close = Series([9.0, 10.0, 11.0, 12.0, 8.0, 19.0, 7.0, 20.0])
    hand_out = a101_053(hand_high, hand_low, hand_close, length=3)
    print("hand-derived bars 0..7:", list(hand_out.iloc[0:8]))

    # Gate A: the zero-denominator example (see
    # tests/test_a101_053.py::test_zero_denominator_is_nan_not_inf).
    zd_close = Series([10.0, 10.0, 12.0, 10.0, 15.0])
    zd_low = Series([10.0, 8.0, 9.0, 10.0, 11.0])
    zd_high = Series([12.0, 11.0, 13.0, 12.0, 16.0])
    zd_out = a101_053(zd_high, zd_low, zd_close, length=1)
    print("zero-denominator bars 0..4:", list(zd_out.iloc[0:5]))

    # Gate B: future-perturbation leak counts, real module vs. the shipped
    # mutant (30-bar write shift).
    other_h, other_l, other_c = _walk(seed=97)
    offsets = range(50, 1500, 40)

    def leaks(fn):
        base = fn(high, low, close)
        hits = 0
        for j in offsets:
            ph, pl, pc = high.copy(), low.copy(), close.copy()
            ph.iloc[j:] = other_h.iloc[j:].values
            pl.iloc[j:] = other_l.iloc[j:].values
            pc.iloc[j:] = other_c.iloc[j:].values
            o = fn(ph, pl, pc)
            a, b = base.iloc[:j], o.iloc[:j]
            if not (a.isna() == b.isna()).all():
                hits += 1
                continue
            mm = a.notna()
            if (a[mm] != b[mm]).any():
                hits += 1
        return hits

    total = len(list(offsets))
    print(f"real-module leaks: {leaks(a101_053)} of {total}")
    shipped = _load_mutant("result = -d9", "result = (-d9).shift(-30)")
    print(f"shipped mutant (30-bar write shift) leaks: {leaks(shipped.a101_053)} of {total}")


if __name__ == "__main__":
    main()
