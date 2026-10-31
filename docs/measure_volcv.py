# -*- coding: utf-8 -*-
"""Scratch measurement for Gates C and D of `volcv`. Not a test; run once to
produce the numbers quoted in `docs/VolcvMeasured.md`, which are the receipt.
"""
import numpy as np
from pandas import Series

from pandas_ta.volume.volcv import volcv


def _walk(n=1200, seed=11):
    rng = np.random.default_rng(seed)
    return Series(np.round(rng.lognormal(10.0, 0.6, n)))


def main():
    v = _walk()
    base = volcv(v)
    m = base.notna()
    print("non-nan:", int(m.sum()), "nunique:", int(base[m].nunique()))
    print("min", base.min(), "max", base.max())

    for k in (10.0, 3.7):
        scaled = volcv(v * k)
        rel = ((scaled[m] - base[m]).abs() / base[m].abs()).max()
        print("k=", k, "max rel diff:", rel)

    for k in (8.0, 64.0):
        scaled = volcv(v * k)
        eq = bool((base[m] == scaled[m]).all())
        print("k=", k, "bit identical:", eq)


if __name__ == "__main__":
    main()
