# -*- coding: utf-8 -*-
"""Prints the exact numbers quoted in docs/G191146Measured.md for
`pandas_ta.momentum.g191_146`. Synthetic frame only (Gate E, the real-data
measurement, is run by the launcher after this session)."""
import importlib
import types
from fractions import Fraction

import numpy as np
from pandas import Series

from pandas_ta.momentum.g191_146 import g191_146

_REAL = importlib.import_module("pandas_ta.momentum.g191_146")


def _walk(n=1500, seed=11, sigma=0.015):
    rng = np.random.default_rng(seed)
    close = 100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n)))
    return Series(close)


def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_g191_146_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


def main():
    close = _walk()
    out = g191_146(close)
    n = len(out)
    fires = int(out.notna().sum())
    nunique = int(out.dropna().nunique())
    first_valid = int(out.notna().idxmax()) if fires else None
    print(f"n={n} fires={fires} ({100 * fires / n:.2f}%) nunique={nunique} "
          f"first_valid_index={first_valid}")
    print(f"min={out.min():.6f} max={out.max():.6f} median={out.median():.6f}")

    m = out.notna()
    for k in (8.0, 64.0, 10.0, 3.7):
        scaled = g191_146(close * k)
        max_diff = float((out[m] - scaled[m]).abs().max())
        mask_match = bool((out.isna() == scaled.isna()).all())
        print(f"x{k} price max|diff|={max_diff} nan-mask-match={mask_match}")

    # Gate A: hand-derived 8-bar example at smooth1_length=3, smooth1_weight=1,
    # mean_length=2, smooth2_length=2, smooth2_weight=1 (see
    # tests/test_g191_146.py::test_hand_derived_eight_bars).
    hand_close = Series([10.0, 11.0, 9.0, 12.0, 8.0, 14.0, 7.0, 16.0])
    hand_out = g191_146(hand_close, smooth1_length=3, smooth1_weight=1,
                         mean_length=2, smooth2_length=2, smooth2_weight=1)
    print("hand-derived bars 0..7:", list(hand_out.iloc[0:8]))
    # also print the intermediate series at full precision for transcription
    r = hand_close / hand_close.shift(1) - 1.0
    s1 = r.ewm(alpha=1 / 3, adjust=False, min_periods=3).mean()
    e = r - s1
    m20 = e.rolling(2).mean()
    s2 = (e ** 2).ewm(alpha=1 / 2, adjust=False, min_periods=2).mean()
    print("r:", list(r))
    print("s1:", list(s1))
    print("e:", list(e))
    print("m20:", list(m20))
    print("s2:", list(s2))

    # Exact-rational replay of the same 8-bar hand derivation, independent
    # of float rounding and of pandas' .ewm()/.rolling(), to pin the
    # hand-derived numbers above to an exact fraction rather than to
    # whatever float64 the module itself produces.
    closes = [Fraction(10), Fraction(11), Fraction(9), Fraction(12),
              Fraction(8), Fraction(14), Fraction(7), Fraction(16)]
    rf = [None] + [closes[t] / closes[t - 1] - 1 for t in range(1, 8)]
    a1 = Fraction(1, 3)
    s1f = [None] * 8
    y = rf[1]
    s1f[1] = y
    for t in range(2, 8):
        y = a1 * rf[t] + (1 - a1) * y
        s1f[t] = y
    ef = [None if rf[t] is None or s1f[t] is None else rf[t] - s1f[t] for t in range(8)]
    m20f = [None] * 8
    for t in range(3, 8):
        if ef[t] is not None and ef[t - 1] is not None:
            m20f[t] = (ef[t] + ef[t - 1]) / 2
    a2 = Fraction(1, 2)
    s2f = [None] * 8
    z = None
    for t in range(3, 8):
        e2 = ef[t] ** 2
        z = e2 if z is None else a2 * e2 + (1 - a2) * z
        s2f[t] = z
    resultf = [None] * 8
    for t in range(4, 8):
        if m20f[t] is not None and s2f[t] is not None and s2f[t - 1] is not None:
            resultf[t] = m20f[t] * ef[t] / s2f[t]
    print("exact bars 3..7:", [None if x is None else float(x) for x in resultf[3:8]])

    # Gate B: future-perturbation leak counts, real module vs. the shipped
    # mutant (60-bar write shift) vs. a weaker centered-mean mutant.
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
    print(f"real-module leaks: {leaks(g191_146)} of {total}")
    shipped = _load_mutant(
        "result = result.where(mask)",
        "result = result.where(mask).shift(-smooth2_length)",
    )
    print(f"shipped mutant (smooth2_length-bar write shift) leaks: "
          f"{leaks(shipped.g191_146)} of {total}")
    weaker = _load_mutant(
        "m20 = e.rolling(mean_length).mean()",
        "m20 = e.rolling(mean_length, center=True).mean()",
    )
    print(f"weaker mutant (centered MEAN) leaks: {leaks(weaker.g191_146)} of {total}")


if __name__ == "__main__":
    main()
