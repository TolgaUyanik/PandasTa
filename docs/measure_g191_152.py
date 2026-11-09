# -*- coding: utf-8 -*-
"""Prints the exact numbers quoted in docs/G191152Measured.md for
`pandas_ta.momentum.g191_152`. Synthetic frame only (Gate E, the real-data
measurement, is run by the launcher after this session)."""
import importlib
import types
from fractions import Fraction

import numpy as np
from pandas import Series

from pandas_ta.momentum.g191_152 import g191_152

_REAL = importlib.import_module("pandas_ta.momentum.g191_152")


def _walk(n=1500, seed=11, sigma=0.015):
    rng = np.random.default_rng(seed)
    close = 100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n)))
    return Series(close)


def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_g191_152_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


def main():
    close = _walk()
    out = g191_152(close)
    n = len(out)
    fires = int(out.notna().sum())
    nunique = int(out.dropna().nunique())
    first_valid = int(out.notna().idxmax()) if fires else None
    print(f"n={n} fires={fires} ({100 * fires / n:.2f}%) nunique={nunique} "
          f"first_valid_index={first_valid}")
    print(f"min={out.min():.6f} max={out.max():.6f} median={out.median():.6f}")

    m = out.notna()
    for k in (8.0, 64.0, 10.0, 3.7):
        scaled = g191_152(close * k)
        max_diff = float((out[m] - scaled[m]).abs().max())
        mask_match = bool((out.isna() == scaled.isna()).all())
        print(f"x{k} price max|diff|={max_diff} nan-mask-match={mask_match}")

    # Gate A: hand-derived 14-bar example at delay_length=3, smooth1_length=2,
    # smooth1_weight=1, fast_length=2, slow_length=3, smooth2_length=2,
    # smooth2_weight=1 (alpha1=alpha2=1/2). min_length = 3+2+3+2 = 10, so
    # bars 9..13 are valid (see tests/test_g191_152.py::test_hand_derived_bars).
    hand_close = Series([10.0, 11.0, 9.0, 12.0, 8.0, 14.0, 7.0, 16.0, 6.0, 18.0,
                         5.0, 20.0, 4.0, 22.0])
    hand_out = g191_152(hand_close, delay_length=3, smooth1_length=2,
                         smooth1_weight=1, fast_length=2, slow_length=3,
                         smooth2_length=2, smooth2_weight=1)
    print("hand-derived bars 0..13:", list(hand_out.iloc[0:14]))

    ratio = hand_close / hand_close.shift(3)
    r1 = ratio.shift(1)
    s9 = r1.ewm(alpha=0.5, adjust=False, min_periods=2).mean()
    s9_1 = s9.shift(1)
    fast = s9_1.rolling(2).mean()
    slow = s9_1.rolling(3).mean()
    diff = fast - slow
    print("ratio:", list(ratio))
    print("r1:", list(r1))
    print("s9:", list(s9))
    print("s9_1:", list(s9_1))
    print("fast:", list(fast))
    print("slow:", list(slow))
    print("diff:", list(diff))

    # Exact-rational replay, independent of float rounding and of pandas'
    # own .ewm()/.rolling() calls, to pin the hand-derived numbers above to
    # an exact fraction rather than to whatever float64 the module produces.
    c = [Fraction(x).limit_denominator() for x in
         [10, 11, 9, 12, 8, 14, 7, 16, 6, 18, 5, 20, 4, 22]]
    N = len(c)
    ratiof = [None] * N
    for t in range(3, N):
        ratiof[t] = c[t] / c[t - 3]
    r1f = [None] * N
    for t in range(4, N):
        r1f[t] = ratiof[t - 1]
    a1 = Fraction(1, 2)
    s9f = [None] * N
    y = None
    count = 0
    for t in range(N):
        if r1f[t] is None:
            continue
        y = r1f[t] if y is None else a1 * r1f[t] + (1 - a1) * y
        count += 1
        if count >= 2:
            s9f[t] = y
    s9_1f = [None] * N
    for t in range(1, N):
        s9_1f[t] = s9f[t - 1]
    fastf = [None] * N
    slowf = [None] * N
    for t in range(N):
        win2 = s9_1f[t - 1:t + 1] if t - 1 >= 0 else []
        if len(win2) == 2 and all(v is not None for v in win2):
            fastf[t] = sum(win2) / 2
        win3 = s9_1f[t - 2:t + 1] if t - 2 >= 0 else []
        if len(win3) == 3 and all(v is not None for v in win3):
            slowf[t] = sum(win3) / 3
    difff = [None if fastf[t] is None or slowf[t] is None else fastf[t] - slowf[t]
             for t in range(N)]
    a2 = Fraction(1, 2)
    resultf = [None] * N
    z = None
    count2 = 0
    for t in range(N):
        if difff[t] is None:
            continue
        z = difff[t] if z is None else a2 * difff[t] + (1 - a2) * z
        count2 += 1
        if count2 >= 2:
            resultf[t] = z
    print("exact bars 9..13:", [None if x is None else float(x) for x in resultf[9:14]])

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
    print(f"real-module leaks: {leaks(g191_152)} of {total}")
    write_shift = _load_mutant(
        "result = _gtja_sma(diff, smooth2_length, smooth2_weight)",
        "result = _gtja_sma(diff, smooth2_length, smooth2_weight).shift(-smooth2_length)",
    )
    print(f"write-shift mutant (smooth2_length-bar look-ahead) leaks: "
          f"{leaks(write_shift.g191_152)} of {total}")
    centered_fast = _load_mutant(
        "fast = s9_1.rolling(fast_length).mean()",
        "fast = s9_1.rolling(fast_length, center=True).mean()",
    )
    print(f"centered-fast-mean mutant leaks: {leaks(centered_fast.g191_152)} of {total}")


if __name__ == "__main__":
    main()
