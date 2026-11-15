# -*- coding: utf-8 -*-
"""Prints the exact numbers quoted in docs/G191080Measured.md for
`pandas_ta.volume.g191_080`. Synthetic frame only (Gate E, the real-data
measurement, is run by the launcher after this session)."""
import numpy as np
from pandas import Series

from pandas_ta.volume.g191_080 import g191_080


def _walk(n=1600, seed=11, lo=1e4, hi=1e6):
    rng = np.random.default_rng(seed)
    return Series(rng.uniform(lo, hi, n))


def main():
    volume = _walk()
    length = 5
    out = g191_080(volume)
    n = len(out)
    fires = int(out.notna().sum())
    nunique = int(out.dropna().nunique())
    print(f"n={n} fires={fires} ({100 * fires / n:.2f}%) nunique={nunique}")
    print(f"min={out.min():.6f} max={out.max():.6f} median={out.median():.6f} "
          f"abs-median={out.abs().median():.6f}")

    m = out.notna()
    for k in (8.0, 64.0):
        scaled = g191_080(volume * k)
        max_diff = float((out[m] - scaled[m]).abs().max())
        mask_match = bool((out.isna() == scaled.isna()).all())
        print(f"x{k} volume max|diff|={max_diff} nan-mask-match={mask_match}")

    for k in (10.0, 3.7):
        scaled = g191_080(volume * k)
        max_diff = float((out[m] - scaled[m]).abs().max())
        mask_match = bool((out.isna() == scaled.isna()).all())
        print(f"x{k} volume max|diff|={max_diff} nan-mask-match={mask_match}")

    # Gate B: future-perturbation leak count, real module vs. a mutant whose
    # write index is shifted `length` bars into the future -- see
    # tests/test_g191_080.py for the exec'd mutant.
    other = _walk(seed=99)
    offsets = range(50, 1500, 50)

    def leaks(fn):
        base = fn(volume)
        hits = 0
        for j in offsets:
            pv = volume.copy()
            pv.iloc[j:] = other.iloc[j:].values
            o = fn(pv)
            a, b = base.iloc[:j], o.iloc[:j]
            if not (a.isna() == b.isna()).all():
                hits += 1
                continue
            mm = a.notna()
            if (a[mm] != b[mm]).any():
                hits += 1
        return hits

    def mutant(v):
        v5 = v.shift(length)
        result = (100.0 * (v - v5) / v5).replace([np.inf, -np.inf], np.nan)
        return result.shift(-length)

    print(f"real-module leaks: {leaks(g191_080)} of {len(offsets)}")
    print(f"mutant leaks: {leaks(mutant)} of {len(offsets)}")


if __name__ == "__main__":
    main()
