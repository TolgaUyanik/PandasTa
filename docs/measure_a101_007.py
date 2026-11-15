# -*- coding: utf-8 -*-
"""Prints the exact numbers quoted in docs/A101007Measured.md for
`pandas_ta.momentum.a101_007`. Synthetic frame only (Gate E, the real-data
measurement, is run by the launcher after this session)."""
import importlib
import types

import numpy as np
from pandas import Series

from pandas_ta.momentum.a101_007 import a101_007

_REAL = importlib.import_module("pandas_ta.momentum.a101_007")


def _walk(n=1500, seed=11, sigma=0.015):
    rng = np.random.default_rng(seed)
    close = 100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n)))
    volume = 1000.0 * np.exp(np.cumsum(rng.normal(0.0, sigma * 1.3, n)))
    return Series(close), Series(volume)


def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_a101_007_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


def main():
    close, volume = _walk()
    out = a101_007(close, volume)
    n = len(out)
    fires = int(out.notna().sum())
    nunique = int(out.dropna().nunique())
    first_valid = int(out.notna().idxmax()) if fires else None
    print(f"n={n} fires={fires} ({100 * fires / n:.2f}%) nunique={nunique} "
          f"first_valid_index={first_valid}")
    print(f"min={out.min():.6f} max={out.max():.6f} median={out.median():.6f}")

    m = out.notna()
    for k in (8.0, 64.0, 10.0, 3.7):
        scaled = a101_007(close * k, volume)
        max_diff = float((out[m] - scaled[m]).abs().max())
        mask_match = bool((out.isna() == scaled.isna()).all())
        print(f"x{k} price max|diff|={max_diff} nan-mask-match={mask_match}")
    for k in (8.0, 64.0, 10.0, 3.7):
        scaled = a101_007(close, volume * k)
        max_diff = float((out[m] - scaled[m]).abs().max())
        mask_match = bool((out.isna() == scaled.isna()).all())
        print(f"x{k} volume max|diff|={max_diff} nan-mask-match={mask_match}")

    # Gate A: hand-derived 7-bar example (see
    # tests/test_a101_007.py::test_hand_derived_seven_bars).
    hand_close = Series([10.0, 12.0, 11.0, 15.0, 9.0, 20.0, 25.0])
    hand_volume = Series([100.0, 50.0, 80.0, 40.0, 90.0, 30.0, 60.0])
    hand_out = a101_007(hand_close, hand_volume, adv_length=2, delta_length=2,
                         ts_rank_length=2)
    print("hand-derived bars 0..6:", list(hand_out.iloc[0:7]))

    # Gate B: future-perturbation leak counts, real module vs. the shipped
    # mutant (60-bar write shift) vs. the weaker 1-bar `d7` mutant.
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

    total = len(list(offsets))
    print(f"real-module leaks: {leaks(a101_007)} of {total}")
    shipped = _load_mutant("result = result.where(mask)",
                            "result = result.where(mask).shift(-ts_rank_length)")
    print(f"shipped mutant (60-bar write shift) leaks: {leaks(shipped.a101_007)} of {total}")
    weaker = _load_mutant("d7 = close.diff(delta_length)",
                           "d7 = close.diff(delta_length).shift(-1)")
    print(f"weaker mutant (1-bar d7 shift) leaks: {leaks(weaker.a101_007)} of {total}")


if __name__ == "__main__":
    main()
