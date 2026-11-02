# -*- coding: utf-8 -*-
"""Prints the exact numbers quoted in docs/OsapIntmomMeasured.md for
`pandas_ta.momentum.osap_intmom`. Synthetic frame only (Gate E, the
real-data measurement, is run by the launcher after this session)."""
import numpy as np
from pandas import Series

from pandas_ta.momentum.osap_intmom import osap_intmom


def _walk(n=900, seed=17, sigma=0.015):
    rng = np.random.default_rng(seed)
    close = 100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n)))
    return Series(close)


def main():
    close = _walk()
    out = osap_intmom(close)
    n = len(out)
    fires = int(out.notna().sum())
    nunique = int(out.dropna().nunique())
    print(f"n={n} fires={fires} ({100 * fires / n:.2f}%) nunique={nunique}")
    print(f"first_valid_index={out.first_valid_index()}")
    print(f"min={out.min():.6f} max={out.max():.6f} median={out.median():.6f}")

    # Gate A: hand-derived example, near_length=1, far_length=2.
    hand = Series([100.0, 110.0, 99.0, 150.0, 200.0])
    hand_out = osap_intmom(hand, near_length=1, far_length=2)
    print("hand-derived (near=1, far=2):", hand_out.tolist())

    # Gate A: independent per-bar loop at the shipped defaults.
    c = close.values
    for t in (300, 500, 700, 899):
        expected = c[t - 126] / c[t - 252] - 1
        print(f"t={t} module={out.iloc[t]:.9f} loop={expected:.9f}")

    # Gate D: scale invariance.
    m = out.notna()
    for k in (8.0, 64.0, 10.0, 3.7):
        scaled = osap_intmom(close * k)
        mask_match = bool((out.isna() == scaled.isna()).all())
        bit_identical = bool((out[m] == scaled[m]).all())
        max_diff = float((out[m] - scaled[m]).abs().max())
        print(f"x{k} close bit-identical={bit_identical} max|diff|={max_diff} "
              f"nan-mask-match={mask_match}")

    # Gate B: future-perturbation leak count, real module vs. an 8-bar
    # look-ahead mutant -- see tests/test_osap_intmom.py for the exec'd
    # mutant.
    def mutant(c_):
        return c_.shift(126 - 134) / c_.shift(252) - 1

    base_close = _walk(1600)
    other_close = _walk(1600, seed=99)
    offsets = range(400, 1225, 25)

    def leaks(fn):
        base = fn(base_close)
        hits = 0
        for j in offsets:
            pc = base_close.copy()
            pc.iloc[j:] = other_close.iloc[j:].values
            o = fn(pc)
            a, b = base.iloc[:j], o.iloc[:j]
            if not (a.isna() == b.isna()).all():
                hits += 1
                continue
            mm = a.notna()
            if (a[mm] != b[mm]).any():
                hits += 1
        return hits

    print(f"real-module leaks: {leaks(osap_intmom)} of {len(offsets)}")
    print(f"mutant leaks: {leaks(mutant)} of {len(offsets)}")


if __name__ == "__main__":
    main()
