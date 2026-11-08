# -*- coding: utf-8 -*-
"""Prints the exact numbers quoted in docs/A101046Measured.md for
`pandas_ta.momentum.a101_046`. Synthetic frame only (Gate E, the real-data
measurement, is run by the launcher after this session)."""
import importlib
import types

import numpy as np
from pandas import Series

from pandas_ta.momentum.a101_046 import a101_046

_REAL = importlib.import_module("pandas_ta.momentum.a101_046")


def _walk(n=1500, seed=11, sigma=0.015):
    rng = np.random.default_rng(seed)
    close = 100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n)))
    return Series(close)


def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_a101_046_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


def main():
    close = _walk()
    out = a101_046(close)
    n = len(out)
    fires = int(out.notna().sum())
    nunique = int(out.dropna().nunique())
    first_valid = int(out.notna().idxmax()) if fires else None
    print(f"n={n} fires={fires} ({100 * fires / n:.2f}%) nunique={nunique} "
          f"first_valid_index={first_valid}")
    print(f"min={out.min():.6f} max={out.max():.6f} median={out.median():.6f}")

    m = out.notna()
    for k in (8.0, 64.0, 10.0, 3.7):
        scaled = a101_046(close * k)
        max_diff = float((out[m] - scaled[m]).abs().max())
        mask_match = bool((out.isna() == scaled.isna()).all())
        print(f"x{k} price max|diff|={max_diff} nan-mask-match={mask_match}")

    # Gate A: hand-derived 12-bar example, length=2 (see
    # tests/test_a101_046.py::test_hand_derived_twelve_bars).
    hand_close = Series([10.0, 11.0, 12.0, 10.0, 9.0, 8.0, 13.0, 14.0, 15.0,
                          16.0, 20.0, 5.0])
    hand_out = a101_046(hand_close, length=2)
    print("hand-derived bars 0..11:", list(hand_out.iloc[0:12]))

    # Gate B: future-perturbation leak counts, real module vs. the shipped
    # mutant (30-bar write shift).
    other_c = _walk(seed=97)
    offsets = range(50, 1500, 40)

    def leaks(fn):
        base = fn(close)
        hits = 0
        for j in offsets:
            pc = close.copy()
            pc.iloc[j:] = other_c.iloc[j:].values
            o = fn(pc)
            a, b = base.iloc[:j], o.iloc[:j]
            if not (a.isna() == b.isna()).all():
                hits += 1
                continue
            mm = a.notna()
            if (a[mm] != b[mm]).any():
                hits += 1
        return hits

    total = len(list(offsets))
    print(f"real-module leaks: {leaks(a101_046)} of {total}")
    shipped = _load_mutant("result = raw / close", "result = (raw / close).shift(-30)")
    print(f"shipped mutant (30-bar write shift) leaks: {leaks(shipped.a101_046)} of {total}")


if __name__ == "__main__":
    main()
