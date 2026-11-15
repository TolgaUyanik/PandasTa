# -*- coding: utf-8 -*-
"""Prints the exact numbers quoted in docs/A101023Measured.md for
`pandas_ta.momentum.a101_023`. Synthetic frame only (Gate E, the real-data
measurement, is run by the launcher after this session)."""
import importlib
import types

import numpy as np
from pandas import Series

from pandas_ta.momentum.a101_023 import a101_023

_REAL = importlib.import_module("pandas_ta.momentum.a101_023")


def _walk(n=1500, seed=11, sigma=0.015):
    rng = np.random.default_rng(seed)
    close = 100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n)))
    high = close * (1.0 + np.abs(rng.normal(0.0, sigma * 0.5, n)))
    return Series(high), Series(close)


def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_a101_023_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


def main():
    high, close = _walk()
    out = a101_023(high, close)
    n = len(out)
    fires = int(out.notna().sum())
    nunique = int(out.dropna().nunique())
    first_valid = int(out.notna().idxmax()) if fires else None
    print(f"n={n} fires={fires} ({100 * fires / n:.2f}%) nunique={nunique} "
          f"first_valid_index={first_valid}")
    print(f"min={out.min():.6f} max={out.max():.6f} median={out.median():.6f}")
    zero_bars = int((out == 0.0).sum())
    print(f"literal-zero bars={zero_bars} ({100 * zero_bars / n:.2f}%)")

    m = out.notna()
    for k in (8.0, 64.0, 10.0, 3.7):
        scaled = a101_023(high * k, close * k)
        max_diff = float((out[m] - scaled[m]).abs().max())
        mask_match = bool((out.isna() == scaled.isna()).all())
        print(f"x{k} price max|diff|={max_diff} nan-mask-match={mask_match}")

    # Gate A: hand-derived 8-bar example, length=5, delta_length=2 (see
    # tests/test_a101_023.py::test_hand_derived_eight_bars).
    hand_high = Series([10.0, 11.0, 12.0, 13.0, 9.0, 20.0, 8.0, 21.0])
    hand_close = Series([9.0, 10.0, 11.0, 12.0, 8.0, 19.0, 7.0, 20.0])
    hand_out = a101_023(hand_high, hand_close, length=5, delta_length=2)
    print("hand-derived bars 0..7:", list(hand_out.iloc[0:8]))

    # Gate B: future-perturbation leak counts, real module vs. the shipped
    # mutant (length-bar write shift).
    other_h, other_c = _walk(seed=97)
    offsets = range(100, 1500, 40)

    def leaks(fn):
        base = fn(high, close)
        hits = 0
        for j in offsets:
            ph, pc = high.copy(), close.copy()
            ph.iloc[j:] = other_h.iloc[j:].values
            pc.iloc[j:] = other_c.iloc[j:].values
            o = fn(ph, pc)
            a, b = base.iloc[:j], o.iloc[:j]
            if not (a.isna() == b.isna()).all():
                hits += 1
                continue
            mm = a.notna()
            if (a[mm] != b[mm]).any():
                hits += 1
        return hits

    total = len(list(offsets))
    print(f"real-module leaks: {leaks(a101_023)} of {total}")
    weaker = _load_mutant(
        "result = result.where(mean_h.notna())",
        "result = result.where(mean_h.notna()).shift(-length)",  # length=20
    )
    shipped = _load_mutant(
        "result = result.where(mean_h.notna())",
        "result = result.where(mean_h.notna()).shift(-30)",
    )
    print(f"rejected mutant (length=20-bar write shift) leaks: {leaks(weaker.a101_023)} of {total}")
    print(f"shipped mutant (30-bar write shift) leaks: {leaks(shipped.a101_023)} of {total}")


if __name__ == "__main__":
    main()
