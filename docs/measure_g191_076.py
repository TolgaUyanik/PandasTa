# -*- coding: utf-8 -*-
"""Prints the exact numbers quoted in docs/G191076Measured.md for
`pandas_ta.volume.g191_076`. Synthetic frame only (Gate E, the real-data
measurement, is run by the launcher after this session)."""
import importlib
import types

import numpy as np
import pandas as pd
from pandas import Series

from pandas_ta.volume.g191_076 import g191_076

_REAL = importlib.import_module("pandas_ta.volume.g191_076")


def _cv(n=1500, seed=11, sigma=0.015, vol_seed=23):
    rng = np.random.default_rng(seed)
    close = 100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n)))
    rng3 = np.random.default_rng(vol_seed)
    volume = np.abs(rng3.normal(1_000_000.0, 300_000.0, n)) + 1.0
    idx = pd.RangeIndex(n)
    return Series(close, index=idx), Series(volume, index=idx)


def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_g191_076_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


def main():
    close, volume = _cv()
    out = g191_076(close, volume)
    n = len(out)
    fires = int(out.notna().sum())
    nunique = int(out.dropna().nunique())
    first_valid = int(out.notna().idxmax()) if fires else None
    print(f"n={n} fires={fires} ({100 * fires / n:.2f}%) nunique={nunique} "
          f"first_valid_index={first_valid}")
    print(f"min={out.min():.6f} max={out.max():.6f} median={out.median():.6f}")

    m = out.notna()
    for k in (8.0, 64.0, 10.0, 3.7):
        scaled = g191_076(close * k, volume)
        max_diff = float((out[m] - scaled[m]).abs().max())
        mask_match = bool((out.isna() == scaled.isna()).all())
        print(f"x{k} PRICE max|diff|={max_diff} nan-mask-match={mask_match}")
    for k in (8.0, 64.0, 10.0, 3.7):
        scaled = g191_076(close, volume * k)
        max_diff = float((out[m] - scaled[m]).abs().max())
        mask_match = bool((out.isna() == scaled.isna()).all())
        print(f"x{k} VOLUME max|diff|={max_diff} nan-mask-match={mask_match}")

    # Gate A: hand-derived small example, length=3.
    hc = Series([10.0, 11.0, 9.0, 12.0, 8.0, 13.0])
    hv = Series([100.0, 200.0, 150.0, 300.0, 250.0, 400.0])
    hout = g191_076(hc, hv, length=3)
    ret_c = hc / hc.shift(1) - 1.0
    x = ret_c.abs() / hv
    std_x = x.rolling(3).std()
    mean_x = x.rolling(3).mean()
    print("hand ret_c:", list(ret_c))
    print("hand x:", list(x))
    print("hand std_x:", list(std_x))
    print("hand mean_x:", list(mean_x))
    print("hand result:", list(hout))

    # Gate B: future-perturbation leak counts, real module vs. two mutants.
    other_c, other_v = _cv(seed=97, vol_seed=71)
    offsets = range(150, 1500, 40)

    def leaks(fn):
        base = fn(close, volume)
        hits = 0
        for j in offsets:
            pc, pv = close.copy(), volume.copy()
            pc.iloc[j:] = other_c.iloc[j:].values
            pv.iloc[j:] = other_v.iloc[j:].values
            o = fn(pc, pv)
            a, b = base.iloc[:j], o.iloc[:j]
            if not (a.isna() == b.isna()).all():
                hits += 1
                continue
            mm = a.notna()
            if (a[mm] != b[mm]).any():
                hits += 1
        return hits

    total = len(list(offsets))
    print(f"real-module leaks: {leaks(g191_076)} of {total}")
    shipped = _load_mutant(
        "result = (std_x / mean_x).replace([np.inf, -np.inf], np.nan)",
        "result = (std_x / mean_x).replace([np.inf, -np.inf], np.nan).shift(-length)",
    )
    print(f"shipped mutant (length-bar write shift) leaks: "
          f"{leaks(shipped.g191_076)} of {total}")
    weaker = _load_mutant(
        "std_x = x.rolling(length).std()\n    mean_x = x.rolling(length).mean()",
        "std_x = x.rolling(length, center=True).std()\n    mean_x = x.rolling(length, center=True).mean()",
    )
    print(f"weaker mutant (centered STD/MEAN) leaks: {leaks(weaker.g191_076)} of {total}")


if __name__ == "__main__":
    main()
