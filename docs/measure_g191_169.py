# -*- coding: utf-8 -*-
"""Prints the exact numbers quoted in docs/G191169Measured.md for
`pandas_ta.momentum.g191_169`. Synthetic frame only (Gate E, the real-data
measurement, is run by the launcher after this session)."""
import importlib
import types
from fractions import Fraction

import numpy as np
import pandas as pd
from pandas import Series

from pandas_ta.momentum.g191_169 import g191_169

_REAL = importlib.import_module("pandas_ta.momentum.g191_169")


def _walk(n=1500, seed=11, sigma=0.015):
    rng = np.random.default_rng(seed)
    close = 100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n)))
    return Series(close)


def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_g191_169_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


def main():
    close = _walk()
    out = g191_169(close)
    n = len(out)
    fires = int(out.notna().sum())
    nunique = int(out.dropna().nunique())
    first_valid = int(out.notna().idxmax()) if fires else None
    print(f"n={n} fires={fires} ({100 * fires / n:.2f}%) nunique={nunique} "
          f"first_valid_index={first_valid}")
    print(f"min={out.min():.6f} max={out.max():.6f} median={out.median():.6f}")

    m = out.notna()
    for k in (8.0, 64.0, 10.0, 3.7):
        scaled = g191_169(close * k)
        max_diff = float((out[m] - scaled[m]).abs().max())
        mask_match = bool((out.isna() == scaled.isna()).all())
        print(f"x{k} price max|diff|={max_diff} nan-mask-match={mask_match}")

    # Gate A: hand-derived 10-bar example at smooth1_length=2, smooth1_weight=1,
    # fast_length=2, slow_length=3, smooth2_length=2, smooth2_weight=1
    # (alpha1=alpha2=1/2). min_length = 2+3+2 = 7, so bars 0..5 are NaN and
    # bars 6..9 are the first four valid values.
    hand_close = Series([10.0, 11.0, 9.0, 12.0, 8.0, 14.0, 7.0, 16.0, 6.0, 18.0])
    hand_out = g191_169(hand_close, smooth1_length=2, smooth1_weight=1,
                         fast_length=2, slow_length=3, smooth2_length=2,
                         smooth2_weight=1)
    print("hand-derived bars 0..9:", list(hand_out.iloc[0:10]))

    delta_c = hand_close.diff()
    s9 = delta_c.ewm(alpha=0.5, adjust=False, min_periods=2).mean()
    a = s9.shift(1)
    fast = a.rolling(2).mean()
    slow = a.rolling(3).mean()
    diff = fast - slow
    print("delta_c:", list(delta_c))
    print("s9:", list(s9))
    print("a:", list(a))
    print("fast:", list(fast))
    print("slow:", list(slow))
    print("diff:", list(diff))

    # Exact-rational replay, independent of float rounding and of pandas'
    # own .ewm()/.rolling() calls, to pin the hand-derived numbers above to
    # an exact fraction rather than to whatever float64 the module produces.
    c = [Fraction(x).limit_denominator() for x in
         [10, 11, 9, 12, 8, 14, 7, 16, 6, 18]]
    N = len(c)
    deltaf = [None] * N
    for t in range(1, N):
        deltaf[t] = c[t] - c[t - 1]
    a1 = Fraction(1, 2)
    s9f = [None] * N
    y = None
    count = 0
    for t in range(N):
        if deltaf[t] is None:
            continue
        y = deltaf[t] if y is None else a1 * deltaf[t] + (1 - a1) * y
        count += 1
        if count >= 2:
            s9f[t] = y
    af = [None] * N
    for t in range(1, N):
        af[t] = s9f[t - 1]
    fastf = [None] * N
    slowf = [None] * N
    for t in range(N):
        win2 = af[t - 1:t + 1] if t - 1 >= 0 else []
        if len(win2) == 2 and all(v is not None for v in win2):
            fastf[t] = sum(win2) / 2
        win3 = af[t - 2:t + 1] if t - 2 >= 0 else []
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
    finalf = [None if resultf[t] is None else resultf[t] / c[t] for t in range(N)]
    print("exact bars 6..9:", [None if x is None else float(x) for x in finalf[6:10]])

    # Independent per-bar replay using plain Python (looping the GTJA
    # recursion from the first valid bar), not pandas' own .ewm()/.rolling()
    # calls, spot-checking the shipped defaults.
    big_close = _walk(900, seed=3)
    out_defaults = g191_169(big_close)
    c2 = big_close.to_numpy(dtype=float)
    n2 = len(c2)
    smooth1_length, smooth1_weight = 9, 1.0
    fast_length, slow_length = 12, 26
    smooth2_length, smooth2_weight = 10, 1.0
    b1 = smooth1_weight / smooth1_length
    b2 = smooth2_weight / smooth2_length

    delta2 = [float("nan")] * n2
    for t in range(1, n2):
        delta2[t] = c2[t] - c2[t - 1]
    s9_2 = [float("nan")] * n2
    y2 = None
    cnt1 = 0
    for t in range(n2):
        if delta2[t] != delta2[t]:
            continue
        y2 = delta2[t] if y2 is None else b1 * delta2[t] + (1 - b1) * y2
        cnt1 += 1
        if cnt1 >= smooth1_length:
            s9_2[t] = y2
    a_2 = [float("nan")] * n2
    for t in range(1, n2):
        a_2[t] = s9_2[t - 1]
    fast2 = [float("nan")] * n2
    slow2 = [float("nan")] * n2
    for t in range(n2):
        wf = a_2[t - fast_length + 1:t + 1] if t - fast_length + 1 >= 0 else []
        if len(wf) == fast_length and all(v == v for v in wf):
            fast2[t] = sum(wf) / fast_length
        ws = a_2[t - slow_length + 1:t + 1] if t - slow_length + 1 >= 0 else []
        if len(ws) == slow_length and all(v == v for v in ws):
            slow2[t] = sum(ws) / slow_length
    diff2 = [float("nan")] * n2
    for t in range(n2):
        if fast2[t] == fast2[t] and slow2[t] == slow2[t]:
            diff2[t] = fast2[t] - slow2[t]
    result2 = [float("nan")] * n2
    z2 = None
    cnt2 = 0
    for t in range(n2):
        if diff2[t] != diff2[t]:
            continue
        z2 = diff2[t] if z2 is None else b2 * diff2[t] + (1 - b2) * z2
        cnt2 += 1
        if cnt2 >= smooth2_length:
            result2[t] = z2
    final2 = [float("nan") if result2[t] != result2[t] else result2[t] / c2[t]
              for t in range(n2)]

    for t in (300, 600, 899):
        print(f"independent-loop bar {t}: module={out_defaults.iloc[t]!r} "
              f"loop={final2[t]!r}")

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
            a_, b_ = base.iloc[:j], o.iloc[:j]
            if not (a_.isna() == b_.isna()).all():
                hits += 1
                continue
            mm = a_.notna()
            if (a_[mm] != b_[mm]).any():
                hits += 1
        return hits

    total = len(list(offsets))
    print(f"real-module leaks: {leaks(g191_169)} of {total}")
    write_shift = _load_mutant(
        "result = _gtja_sma(diff, smooth2_length, smooth2_weight) / close",
        "result = (_gtja_sma(diff, smooth2_length, smooth2_weight) / close).shift(-smooth2_length)",
    )
    print(f"write-shift mutant (smooth2_length-bar look-ahead) leaks: "
          f"{leaks(write_shift.g191_169)} of {total}")
    centered_fast = _load_mutant(
        "fast = a.rolling(fast_length).mean()",
        "fast = a.rolling(fast_length, center=True).mean()",
    )
    print(f"centered-fast-mean mutant leaks: {leaks(centered_fast.g191_169)} of {total}")


if __name__ == "__main__":
    main()
