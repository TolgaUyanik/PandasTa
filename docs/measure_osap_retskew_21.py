# -*- coding: utf-8 -*-
"""Prints the exact numbers quoted in docs/OsapRetskew21Measured.md for
`pandas_ta.statistics.osap_retskew_21`. Synthetic frame only (Gate E, the
real-data measurement, is run by the launcher after this session)."""
import numpy as np
from pandas import Series

from pandas_ta.statistics.osap_retskew_21 import osap_retskew_21


def _walk(n=1200, seed=23, s0=100.0, sigma=0.018):
    rng = np.random.default_rng(seed)
    rets = rng.normal(0.0, sigma, n)
    px = s0 * np.cumprod(1.0 + rets)
    return Series(np.round(px, 2))


def main():
    # Gate A hand-derivation receipt: length=3, the smallest window skew is
    # defined on. Printed, not typed, so the quoted numbers in
    # docs/OsapRetskew21Measured.md are read off this output.
    example = Series([100.0, 103.0, 101.0, 108.0])
    r = example.pct_change(fill_method=None).to_numpy()[1:]
    m, s = r.mean(), r.std(ddof=1)
    n = 3
    skew3 = (n / ((n - 1) * (n - 2))) * np.sum((r - m) ** 3) / s ** 3
    print(f"3-bar example: returns={r.tolist()} mean={m:.7f} std={s:.7f} skew={skew3:.6f}")
    print(f"3-bar module output: {osap_retskew_21(example, length=3).iloc[3]:.6f}")

    close = _walk()
    out = osap_retskew_21(close)
    n = len(out)
    fires = int(out.notna().sum())
    nunique = int(out.dropna().nunique())
    print(f"n={n} fires={fires} ({100 * fires / n:.2f}%) nunique={nunique}")
    print(f"min={out.min():.6f} max={out.max():.6f} median={out.median():.6f} "
          f"abs-median={out.abs().median():.6f}")
    assert int(out.isna().sum()) == 21  # length-bar warm-up, nothing else

    for k in (8.0, 64.0):
        scaled = osap_retskew_21(close * k)
        m = out.notna()
        print(f"x{k} max|diff|={float((out[m] - scaled[m]).abs().max())}")

    for k in (10.0, 3.7):
        scaled = osap_retskew_21(close * k)
        m = out.notna()
        print(f"x{k} max|diff|={float((out[m] - scaled[m]).abs().max())}")

    # future-perturbation causality sweep, matching the test file
    other = _walk(seed=99)
    offsets = range(40, 1100, 35)
    hits = 0
    for j in offsets:
        perturbed = close.copy()
        perturbed.iloc[j:] = other.iloc[j:].values
        shifted = osap_retskew_21(perturbed)
        a, b = out.iloc[:j], shifted.iloc[:j]
        if not (a.isna() == b.isna()).all():
            hits += 1
            continue
        mm = a.notna()
        if (a[mm] != b[mm]).any():
            hits += 1
    print(f"causality: {hits} of {len(list(offsets))} offsets leaked")


if __name__ == "__main__":
    main()
