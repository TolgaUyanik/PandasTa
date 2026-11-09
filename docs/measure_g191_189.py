# -*- coding: utf-8 -*-
"""Prints the exact numbers quoted in docs/G191189Measured.md for
`pandas_ta.statistics.g191_189`. Synthetic frame only (Gate E, the
real-data measurement, is run by the launcher after this session)."""
import importlib
import types

import numpy as np
import pandas_ta as ta
from pandas import Series

from pandas_ta.statistics.g191_189 import g191_189
from pandas_ta.statistics.mad import mad

_REAL = importlib.import_module("pandas_ta.statistics.g191_189")


def _close(n=900, seed=11, sigma=0.015):
    rng = np.random.default_rng(seed)
    return Series(100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n))))


def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_g191_189_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


def _expected_at(c, t, mean_length, mad_length):
    devs = []
    for back in range(mad_length - 1, -1, -1):
        tt = t - back
        window = c[tt - mean_length + 1: tt + 1]
        devs.append(abs(c[tt] - sum(window) / mean_length))
    return (sum(devs) / mad_length) / c[t]


def main():
    print("wiring:")
    print("  g191_189 in Category['statistics']:", "g191_189" in ta.Category["statistics"])
    print("  Category total:", sum(len(v) for v in ta.Category.values()))
    print("  Category['statistics'] size:", len(ta.Category["statistics"]))

    close = _close()
    out = g191_189(close)
    n = len(out)
    fires = int(out.notna().sum())
    nunique = int(out.dropna().nunique())
    first_valid = int(out.notna().idxmax()) if fires else None
    print(f"n={n} fires={fires} ({100 * fires / n:.2f}%) nunique={nunique} "
          f"first_valid_index={first_valid}")
    print(f"min={out.min():.6f} max={out.max():.6f} median={out.median():.6f}")

    m = out.notna()
    for k in (8.0, 64.0, 10.0, 3.7):
        scaled = g191_189(close * k)
        max_diff = float((out[m] - scaled[m]).abs().max())
        mask_match = bool((out.isna() == scaled.isna()).all())
        print(f"x{k} PRICE max|diff|={max_diff} nan-mask-match={mask_match}")

    # Gate A: spot-check against an independent per-bar computation.
    small = _close(60, seed=5)
    c_np = small.to_numpy(dtype=float)
    out_small = g191_189(small, mean_length=3, mad_length=2)
    for t in (20, 40, 59):
        expected = _expected_at(c_np, t, 3, 2)
        actual = out_small.iloc[t]
        print(f"t={t} module={actual!r} independent={expected!r}")

    big = _close(300, seed=5)
    c_np = big.to_numpy(dtype=float)
    out_big = g191_189(big)
    for t in (100, 200, 299):
        expected = _expected_at(c_np, t, 6, 6)
        actual = out_big.iloc[t]
        print(f"t={t} module={actual!r} independent={expected!r}")

    # Non-redundancy vs. the already-shipped `mad` indicator.
    trending = _close(300, seed=3, sigma=0.02)
    g191 = g191_189(trending, mean_length=6, mad_length=6)
    shipped = mad(trending, length=6) / trending
    both = g191.notna() & shipped.notna()
    diffcount = int((g191[both] != shipped[both]).sum())
    print(f"non-redundancy vs mad: {diffcount} of {int(both.sum())} overlapping bars differ")

    # Non-redundancy, degenerate-case check: at mad_length=1 (mean_length=3
    # still >1) the two formulas must still disagree -- g191_189 reports only
    # the LAST bar's deviation, mad.py averages all 3 in-window deviations.
    from pandas import Series as _S
    degen_close = _S([1.0, 2.0, 3.0, 4.0, 5.0])
    degen_g191_pre_div = g191_189(degen_close, mean_length=3, mad_length=1) * degen_close
    degen_mad = mad(degen_close, length=3)
    for t in (2, 3, 4):
        print(f"degenerate mad_length=1: t={t} mad.py={degen_mad.iloc[t]!r} "
              f"g191_189_pre_div={degen_g191_pre_div.iloc[t]!r}")

    # Gate B: future-perturbation leak counts, real module vs. the mutant.
    close2 = _close(900)
    o_close = _close(900, seed=97)
    offsets = range(50, 900, 40)

    def leaks(fn):
        base = fn(close2)
        hits = 0
        for j in offsets:
            p_close = close2.copy()
            p_close.iloc[j:] = o_close.iloc[j:].values
            o = fn(p_close)
            a, b = base.iloc[:j], o.iloc[:j]
            if not (a.isna() == b.isna()).all():
                hits += 1
                continue
            mm = a.notna()
            if (a[mm] != b[mm]).any():
                hits += 1
        return hits

    total = len(list(offsets))
    print(f"real-module leaks: {leaks(g191_189)} of {total}")
    shift_mutant = _load_mutant(
        "mad = deviation.rolling(mad_length, min_periods=mad_length).mean()",
        "mad = deviation.rolling(mad_length, min_periods=mad_length).mean().shift(-mad_length)",
    )
    print(f"write-shift mutant leaks: {leaks(shift_mutant.g191_189)} of {total}")


if __name__ == "__main__":
    main()
