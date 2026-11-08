# -*- coding: utf-8 -*-
"""Prints the exact numbers quoted in docs/OsapLrrevMeasured.md for
`pandas_ta.momentum.osap_lrrev`. Synthetic frame only (Gate E, the real-data
measurement, is run by the launcher after this session)."""
import numpy as np
from pandas import Series

from pandas_ta.momentum.osap_lrrev import osap_lrrev


def _walk(n=1600, seed=17, sigma=0.015):
    rng = np.random.default_rng(seed)
    close = 100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n)))
    return Series(close)


def main():
    close = _walk()
    out = osap_lrrev(close)
    n = len(out)
    fires = int(out.notna().sum())
    nunique = int(out.dropna().nunique())
    print(f"n={n} fires={fires} ({100 * fires / n:.2f}%) nunique={nunique}")
    print(f"min={out.min():.6f} max={out.max():.6f} median={out.median():.6f} "
          f"abs-median={out.abs().median():.6f}")

    m = out.notna()
    for k in (8.0, 64.0):
        scaled = osap_lrrev(close * k)
        max_diff = float((out[m] - scaled[m]).abs().max())
        mask_match = bool((out.isna() == scaled.isna()).all())
        print(f"x{k} price max|diff|={max_diff} nan-mask-match={mask_match}")

    for k in (10.0, 3.7):
        scaled = osap_lrrev(close * k)
        max_diff = float((out[m] - scaled[m]).abs().max())
        mask_match = bool((out.isna() == scaled.isna()).all())
        print(f"x{k} price max|diff|={max_diff} nan-mask-match={mask_match}")

    # Gate B: future-perturbation leak count, real module vs. an 8-bar
    # look-ahead mutant (near-bar reference shifted from close.shift(252) to
    # close.shift(-8)) -- see tests/test_osap_lrrev.py for the exec'd mutant.
    other = _walk(seed=99)
    offsets = range(800, 1525, 25)

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
        return c.shift(-8) / c.shift(756) - 1

    print(f"real-module leaks: {leaks(osap_lrrev)} of {len(offsets)}")
    print(f"mutant leaks: {leaks(mutant)} of {len(offsets)}")


if __name__ == "__main__":
    main()
