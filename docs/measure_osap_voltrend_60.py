# -*- coding: utf-8 -*-
"""Prints the exact numbers quoted in docs/OsapVoltrend60Measured.md for
`pandas_ta.volume.osap_voltrend_60`. Synthetic frame only (Gate E, the
real-data measurement, is run by the launcher after this session)."""
import numpy as np
from pandas import Series

from pandas_ta.volume.osap_voltrend_60 import osap_voltrend_60


def _walk(n=1600, seed=11, lo=1e4, hi=1e6):
    rng = np.random.default_rng(seed)
    return Series(rng.uniform(lo, hi, n))


def main():
    volume = _walk()
    out = osap_voltrend_60(volume)
    n = len(out)
    fires = int(out.notna().sum())
    nunique = int(out.dropna().nunique())
    print(f"n={n} fires={fires} ({100 * fires / n:.2f}%) nunique={nunique}")
    print(f"min={out.min():.6f} max={out.max():.6f} median={out.median():.6f} "
          f"abs-median={out.abs().median():.6f}")

    m = out.notna()
    for k in (8.0, 64.0):
        scaled = osap_voltrend_60(volume * k)
        max_diff = float((out[m] - scaled[m]).abs().max())
        mask_match = bool((out.isna() == scaled.isna()).all())
        print(f"x{k} volume max|diff|={max_diff} nan-mask-match={mask_match}")

    for k in (10.0, 3.7):
        scaled = osap_voltrend_60(volume * k)
        max_diff = float((out[m] - scaled[m]).abs().max())
        mask_match = bool((out.isna() == scaled.isna()).all())
        print(f"x{k} volume max|diff|={max_diff} nan-mask-match={mask_match}")

    # Gate B: future-perturbation leak count, real module vs. a mutant whose
    # slope rolling window is centered (reads into the future) -- see
    # tests/test_osap_voltrend_60.py for the exec'd mutant.
    other = _walk(seed=99)
    offsets = range(100, 1500, 50)

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
        length = 60
        t = np.arange(length, dtype=float) - (length - 1) / 2.0
        w = t / (t * t).sum()
        slope = v.rolling(length, min_periods=length, center=True).apply(
            lambda window: np.dot(w, window), raw=True)
        vmean = v.rolling(length, min_periods=length).mean()
        return (slope / vmean).replace([np.inf, -np.inf], np.nan)

    print(f"real-module leaks: {leaks(osap_voltrend_60)} of {len(offsets)}")
    print(f"mutant leaks: {leaks(mutant)} of {len(offsets)}")


if __name__ == "__main__":
    main()
