# -*- coding: utf-8 -*-
"""Prints the exact numbers quoted in docs/VolSignRevMeasured.md for
`pandas_ta.volume.vol_sign_rev`. Synthetic frame only (Gate E, the real-data
measurement, is run by the launcher after this session)."""
import numpy as np
from pandas import Series

from pandas_ta.volume.vol_sign_rev import vol_sign_rev


def _walk(n=900, seed=17, sigma=0.015, vol_lo=1e4, vol_hi=1e6, vol_seed=23):
    rng = np.random.default_rng(seed)
    close = 100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n)))
    vrng = np.random.default_rng(vol_seed)
    volume = vrng.uniform(vol_lo, vol_hi, n)
    return Series(close), Series(volume)


def main():
    close, volume = _walk()
    out = vol_sign_rev(close, volume)
    n = len(out)
    fires = int(out.notna().sum())
    nunique = int(out.dropna().nunique())
    print(f"n={n} fires={fires} ({100 * fires / n:.2f}%) nunique={nunique}")
    print(f"min={out.min():.6f} max={out.max():.6f} median={out.median():.6f} "
          f"abs-median={out.abs().median():.6f}")

    m = out.notna()
    for k in (8.0, 64.0):
        scaled = vol_sign_rev(close * k, volume)
        max_diff = float((out[m] - scaled[m]).abs().max())
        mask_match = bool((out.isna() == scaled.isna()).all())
        print(f"x{k} price max|diff|={max_diff} nan-mask-match={mask_match}")

    for k in (10.0, 3.7):
        scaled = vol_sign_rev(close * k, volume)
        max_diff = float((out[m] - scaled[m]).abs().max())
        mask_match = bool((out.isna() == scaled.isna()).all())
        print(f"x{k} price max|diff|={max_diff} nan-mask-match={mask_match}")

    for k in (8.0, 64.0, 10.0, 3.7):
        scaled = vol_sign_rev(close, volume * k)
        max_diff = float((out[m] - scaled[m]).abs().max())
        mask_match = bool((out.isna() == scaled.isna()).all())
        print(f"x{k} volume max|diff|={max_diff} nan-mask-match={mask_match}")

    # Gate B: future-perturbation leak count, real module vs. a 1-bar
    # look-ahead mutant (close.shift(1) -> close.shift(-1) in the return
    # term) -- see tests/test_vol_sign_rev.py for the exec'd mutant.
    other_close, other_volume = _walk(seed=99, vol_seed=101)
    offsets = range(5, 895, 20)

    def leaks(fn):
        base = fn(close, volume)
        hits = 0
        for j in offsets:
            pc, pv = close.copy(), volume.copy()
            pc.iloc[j:] = other_close.iloc[j:].values
            pv.iloc[j:] = other_volume.iloc[j:].values
            o = fn(pc, pv)
            a, b = base.iloc[:j], o.iloc[:j]
            if not (a.isna() == b.isna()).all():
                hits += 1
                continue
            mm = a.notna()
            if (a[mm] != b[mm]).any():
                hits += 1
        return hits

    def mutant(c, v):
        ret = c / c.shift(-1) - 1
        return np.sign(v.diff(1)) * -ret

    print(f"real-module leaks: {leaks(vol_sign_rev)} of {len(offsets)}")
    print(f"mutant leaks: {leaks(mutant)} of {len(offsets)}")


if __name__ == "__main__":
    main()
