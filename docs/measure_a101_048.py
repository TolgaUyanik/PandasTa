# -*- coding: utf-8 -*-
"""Prints the exact numbers quoted in docs/A101048Measured.md for
`pandas_ta.momentum.a101_048`. Synthetic frame only (Gate E, the real-data
measurement, is run by the launcher after this session)."""
import numpy as np
from pandas import Series

from pandas_ta.momentum.a101_048 import a101_048


def _walk(n=1500, seed=11, sigma=0.015):
    rng = np.random.default_rng(seed)
    close = 100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n)))
    return Series(close)


def main():
    close = _walk()
    out = a101_048(close)
    n = len(out)
    fires = int(out.notna().sum())
    nunique = int(out.dropna().nunique())
    first_valid = int(out.notna().idxmax()) if fires else None
    print(f"n={n} fires={fires} ({100 * fires / n:.2f}%) nunique={nunique} first_valid_index={first_valid}")
    print(f"min={out.min():.6f} max={out.max():.6f} median={out.median():.6f} "
          f"abs-median={out.abs().median():.6f}")

    m = out.notna()
    for k in (8.0, 64.0):
        scaled = a101_048(close * k)
        max_diff = float((out[m] - scaled[m]).abs().max())
        mask_match = bool((out.isna() == scaled.isna()).all())
        print(f"x{k} price max|diff|={max_diff} nan-mask-match={mask_match}")

    for k in (10.0, 3.7):
        scaled = a101_048(close * k)
        max_diff = float((out[m] - scaled[m]).abs().max())
        mask_match = bool((out.isna() == scaled.isna()).all())
        print(f"x{k} price max|diff|={max_diff} nan-mask-match={mask_match}")

    # Gate A: hand-derived example at length=2, bars 3/4/5 (see
    # tests/test_a101_048.py::test_hand_derived_three_bars_at_length_2).
    hand_close = Series([100.0, 102.0, 101.0, 105.0, 103.0, 108.0])
    hand_out = a101_048(hand_close, length=2)
    print("hand-derived length=2 bars 3/4/5:", hand_out.iloc[3], hand_out.iloc[4], hand_out.iloc[5])

    # Gate B: future-perturbation leak count, real module vs. a 1-bar
    # look-ahead mutant (the autocorrelation's lag term shifted from
    # d.shift(1) to d.shift(-1)) -- see tests/test_a101_048.py for the
    # exec'd mutant.
    other = _walk(seed=97)
    offsets = range(300, 1500, 40)

    def leaks(fn):
        base = fn(close)
        hits = 0
        for j in offsets:
            pc = close.copy()
            pc.iloc[j:] = other.iloc[j:].values
            o = fn(pc)
            a, b = base.iloc[:j], o.iloc[:j]
            if not (a.isna() == b.isna()).all():
                hits += 1
                continue
            mm = a.notna()
            if (a[mm] != b[mm]).any():
                hits += 1
        return hits

    def mutant(c):
        d = c.diff(1)
        r = c.pct_change(fill_method=None)
        autocorr = d.rolling(250).corr(d.shift(-1))
        denom = (r ** 2).rolling(250).sum()
        result = (autocorr * d / c) / denom
        return result.replace([np.inf, -np.inf], np.nan)

    print(f"real-module leaks: {leaks(a101_048)} of {len(list(offsets))}")
    print(f"mutant leaks: {leaks(mutant)} of {len(list(offsets))}")


if __name__ == "__main__":
    main()
