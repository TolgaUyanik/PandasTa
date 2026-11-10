# -*- coding: utf-8 -*-
"""Prints the exact numbers quoted in docs/G191129Measured.md for
`pandas_ta.momentum.g191_129`. Synthetic frame only (Gate E, the real-data
measurement, is run by the launcher after this session)."""
import importlib
import types

import numpy as np
import pandas as pd
from pandas import Series

from pandas_ta.momentum.g191_129 import g191_129

_REAL = importlib.import_module("pandas_ta.momentum.g191_129")


def _walk(n=1500, seed=11, sigma=0.015):
    rng = np.random.default_rng(seed)
    close = 100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n)))
    return Series(close)


def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_g191_129_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


def main():
    close = _walk()
    out = g191_129(close)
    n = len(out)
    fires = int(out.notna().sum())
    nunique = int(out.dropna().nunique())
    first_valid = int(out.notna().idxmax()) if fires else None
    print(f"n={n} fires={fires} ({100 * fires / n:.2f}%) nunique={nunique} "
          f"first_valid_index={first_valid}")
    print(f"min={out.min():.6f} max={out.max():.6f} median={out.median():.6f}")

    m = out.notna()
    for k in (8.0, 64.0, 10.0, 3.7):
        scaled = g191_129(close * k)
        max_diff = float((out[m] - scaled[m]).abs().max())
        mask_match = bool((out.isna() == scaled.isna()).all())
        print(f"x{k} price max|diff|={max_diff} nan-mask-match={mask_match}")

    # Gate A: hand-derived 6-bar example at length=3.
    hand_close = Series([10.0, 12.0, 9.0, 15.0, 7.0, 20.0])
    hand_out = g191_129(hand_close, length=3)
    print("hand-derived bars 0..5:", list(hand_out.iloc[0:6]))
    delta = hand_close.diff()
    print("delta:", list(delta))
    print("down ((-delta).clip):", list((-delta).clip(lower=0)))

    # Gate A: (-delta).clip(lower=0) vs explicit ternary agree bit-for-bit on
    # the general case (the 1,500-bar synthetic walk below has zero
    # exactly-flat bars, printed as zero-delta-bars; the delta == 0 boundary
    # itself is pinned separately by
    # tests/test_g191_129.py::test_clip_matches_an_explicit_ternary_at_the_zero_boundary's
    # dedicated 5-bar frame, not by this walk).
    delta_big = close.diff()
    via_clip = (-delta_big).clip(lower=0)
    via_ternary = pd.Series(
        np.where(delta_big < 0, -delta_big, 0.0), index=close.index
    ).where(delta_big.notna())
    zero_bars = int((delta_big == 0.0).sum())
    agree = bool(via_clip.equals(via_ternary))
    print(f"clip-vs-ternary agree={agree} zero-delta-bars={zero_bars}")

    # Independent per-bar replay using plain numpy array slicing, not
    # pandas' own .rolling() calls, spot-checking the shipped defaults.
    big_close = _walk(900, seed=5)
    out_defaults = g191_129(big_close)
    c = big_close.to_numpy(dtype=float)
    length = 12
    for t in (300, 600, 899):
        idx = np.arange(t - length + 1, t + 1)
        d = c[idx] - c[idx - 1]
        down = np.maximum(-d, 0.0)
        expected = float(np.sum(down) / c[t])
        print(f"independent-loop bar {t}: module={out_defaults.iloc[t]!r} "
              f"loop={expected!r}")

    # Gate B: future-perturbation leak counts, real module vs. two mutants.
    other_c = _walk(seed=97)
    offsets = range(150, 1500, 40)

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
    print(f"real-module leaks: {leaks(g191_129)} of {total}")
    write_shift = _load_mutant(
        "result = down.rolling(length, min_periods=length).sum() / close",
        "result = (down.rolling(length, min_periods=length).sum() / close).shift(-length)",
    )
    print(f"write-shift mutant (length-bar look-ahead) leaks: "
          f"{leaks(write_shift.g191_129)} of {total}")
    centered_sum = _load_mutant(
        "result = down.rolling(length, min_periods=length).sum() / close",
        "result = down.rolling(length, center=True, min_periods=length).sum() / close",
    )
    print(f"centered-sum mutant leaks: "
          f"{leaks(centered_sum.g191_129)} of {total}")


if __name__ == "__main__":
    main()
