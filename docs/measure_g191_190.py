# -*- coding: utf-8 -*-
"""Prints the exact numbers quoted in docs/G191190Measured.md for
`pandas_ta.statistics.g191_190`. Synthetic frame only (Gate E, the
real-data measurement, is run by the launcher after this session)."""
import importlib
import types

import numpy as np
import pandas as pd
from pandas import Series

from pandas_ta.statistics.g191_190 import g191_190

_REAL = importlib.import_module("pandas_ta.statistics.g191_190")


def _close(n=1500, seed=11, sigma=0.015):
    rng = np.random.default_rng(seed)
    close = 100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n)))
    return Series(close, index=pd.RangeIndex(n))


def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_g191_190_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


def _expected_at(c, t, length):
    g_lookback = length - 1
    count_up = count_dn = 0
    sum_e2_dn = sum_e2_up = 0.0
    for i in range(t - length + 1, t + 1):
        r_i = c[i] / c[i - 1] - 1.0
        g_i = (c[i] / c[i - g_lookback]) ** (1.0 / length) - 1.0
        e2_i = (r_i - g_i) ** 2
        if r_i > g_i:
            count_up += 1
            sum_e2_up += e2_i
        elif r_i < g_i:
            count_dn += 1
            sum_e2_dn += e2_i
    num = (count_up - 1) * sum_e2_dn
    den = count_dn * sum_e2_up
    if den == 0:
        return float("nan")
    ratio = num / den
    return np.log(ratio) if ratio > 0 else float("nan")


def main():
    close = _close()
    out = g191_190(close)
    n = len(out)
    fires = int(out.notna().sum())
    nunique = int(out.dropna().nunique())
    first_valid = int(out.notna().idxmax()) if fires else None
    print(f"n={n} fires={fires} ({100 * fires / n:.2f}%) nunique={nunique} "
          f"first_valid_index={first_valid}")
    print(f"min={out.min():.6f} max={out.max():.6f} median={out.median():.6f}")

    m = out.notna()
    for k in (8.0, 64.0, 10.0, 3.7):
        scaled = g191_190(close * k)
        max_diff = float((out[m] - scaled[m]).abs().max())
        mask_match = bool((out.isna() == scaled.isna()).all())
        print(f"x{k} PRICE max|diff|={max_diff} nan-mask-match={mask_match}")

    # Gate A: hand-derived small example, length=4.
    hc = Series([10.0, 10.5, 9.8, 11.0, 10.2, 12.0, 11.5, 13.0, 9.0, 10.0])
    hout = g191_190(hc, length=4)
    c = hc.to_numpy(dtype=float)
    print("hand out:", list(hout))
    for t in (6, 7, 8, 9):
        e = _expected_at(c, t, 4)
        print(f"  t={t} module={hout.iloc[t]!r} independent={e!r}")

    # Gate A: spot-check the shipped default against an independent
    # per-bar computation using plain python loops over window slices.
    big_c = _close(900, seed=5)
    out_big = g191_190(big_c)
    c = big_c.to_numpy(dtype=float)
    for t in (300, 600, 899):
        a = out_big.iloc[t]
        b = _expected_at(c, t, 20)
        if np.isnan(b):
            print(f"t={t} module={a!r} independent=nan")
            assert pd.isna(a)
        else:
            rel = abs(a - b) / abs(b)
            print(f"t={t} module={a!r} independent={b!r} rel_diff={rel:.3e}")
            assert rel < 1e-9

    # Gate B: future-perturbation leak counts, real module vs. two mutants.
    close = _close(1500)
    other_c = _close(1500, seed=97)
    offsets = range(150, 1500, 40)

    def leaks(fn):
        base = fn(close)
        hits = 0
        for j in offsets:
            pc = close.copy()
            pc.iloc[j:] = other_c.iloc[j:].values
            o = fn(pc)
            a, b = base.iloc[:j], o.iloc[:j]
            if not (a.isna() == b.isna()).all():
                hits += 1
                continue
            mm = a.notna()
            if (a[mm] != b[mm]).any():
                hits += 1
        return hits

    total = len(list(offsets))
    print(f"real-module leaks: {leaks(g191_190)} of {total}")
    shipped = _load_mutant(
        "result = pd.Series(result, index=close.index)",
        "result = pd.Series(result, index=close.index).shift(-length)",
    )
    print(f"write-shift mutant leaks: {leaks(shipped.g191_190)} of {total}")
    weaker = _load_mutant(
        "g = (close / close.shift(g_lookback)) ** (1.0 / length) - 1.0",
        "g = (close / close.shift(-g_lookback)) ** (1.0 / length) - 1.0",
    )
    print(f"forward-delay mutant leaks: {leaks(weaker.g191_190)} of {total}")


if __name__ == "__main__":
    main()
