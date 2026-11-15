# -*- coding: utf-8 -*-
"""Prints the exact numbers quoted in docs/A101021Measured.md for
`pandas_ta.momentum.a101_021`. Synthetic frame only (Gate E, the real-data
measurement, is run by the launcher after this session)."""
import importlib
import types

import numpy as np
from pandas import Series

from pandas_ta.momentum.a101_021 import a101_021

_REAL = importlib.import_module("pandas_ta.momentum.a101_021")


def _walk(n=1500, seed=11, sigma=0.015):
    rng = np.random.default_rng(seed)
    close = 100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n)))
    volume = 1000.0 * np.exp(np.cumsum(rng.normal(0.0, sigma * 1.3, n)))
    return Series(close), Series(volume)


def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_a101_021_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


def main():
    close, volume = _walk()
    out = a101_021(close, volume)
    n = len(out)
    fires = int(out.notna().sum())
    nunique = int(out.dropna().nunique())
    first_valid = int(out.notna().idxmax()) if fires else None
    print(f"n={n} fires={fires} ({100 * fires / n:.2f}%) nunique={nunique} "
          f"first_valid_index={first_valid} values={sorted(out.dropna().unique())}")
    print(out.dropna().value_counts().to_dict())

    m = out.notna()
    for k in (8.0, 64.0, 10.0, 3.7):
        scaled = a101_021(close * k, volume)
        max_diff = float((out[m] - scaled[m]).abs().max())
        mask_match = bool((out.isna() == scaled.isna()).all())
        print(f"x{k} price max|diff|={max_diff} nan-mask-match={mask_match}")
    for k in (8.0, 64.0, 10.0, 3.7):
        scaled = a101_021(close, volume * k)
        max_diff = float((out[m] - scaled[m]).abs().max())
        mask_match = bool((out.isna() == scaled.isna()).all())
        print(f"x{k} volume max|diff|={max_diff} nan-mask-match={mask_match}")

    # Gate A: hand-derived example, length=3/fast_length=1/adv_length=2
    # (see tests/test_a101_021.py::test_hand_derived_nine_bars_all_three_branches).
    hand_close = Series([10.0, 10.0, 10.0, 10.0, 10.0, 100.0, 10.0, 10.0, 1.0])
    hand_volume = Series([100.0, 50.0, 70.0, 80.0, 90.0, 40.0, 30.0, 20.0, 25.0])
    hand_out = a101_021(hand_close, hand_volume, length=3, fast_length=1, adv_length=2)
    print("hand-derived bars 2..8:", list(hand_out.iloc[2:9]))

    # Gate B: future-perturbation leak counts, real module vs. three
    # mutants -- the shipped one (adv_length-bar write shift) and two
    # weaker ones tried first and rejected as quantisation artefacts.
    other_c, other_v = _walk(seed=97)
    offsets = range(100, 1500, 40)

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

    one_bar = _load_mutant(
        "s8 = close.rolling(length).std()",
        "s8 = close.rolling(length).std().shift(-1)",
    )
    length_shift = _load_mutant(
        "result = result.where(mask)",
        "result = result.where(mask).shift(-length)",
    )
    adv_shift = _load_mutant(
        "result = result.where(mask)",
        "result = result.where(mask).shift(-adv_length)",
    )

    total = len(list(offsets))
    print(f"real-module leaks: {leaks(a101_021)} of {total}")
    print(f"rejected mutant (1-bar s8 lookahead) leaks: {leaks(one_bar.a101_021)} of {total}")
    print(f"rejected mutant (length-bar write shift) leaks: {leaks(length_shift.a101_021)} of {total}")
    print(f"shipped mutant (adv_length-bar write shift) leaks: {leaks(adv_shift.a101_021)} of {total}")


if __name__ == "__main__":
    main()
