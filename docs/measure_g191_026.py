# -*- coding: utf-8 -*-
"""Prints the exact numbers quoted in docs/G191026Measured.md for
`pandas_ta.statistics.g191_026`. Synthetic frame only (Gate E, the real-data
measurement, is run by the launcher after this session)."""
import importlib
import types

import numpy as np
import pandas as pd
from pandas import Series

from pandas_ta.statistics.g191_026 import g191_026

_REAL = importlib.import_module("pandas_ta.statistics.g191_026")


def _ohlc(n=1500, seed=11, sigma=0.015):
    rng = np.random.default_rng(seed)
    close = 100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n)))
    rng2 = np.random.default_rng(seed + 1)
    spread = np.abs(rng2.normal(0.0, 0.01, n)) * close
    high = close + spread * rng2.uniform(0.2, 1.0, n)
    low = close - spread * rng2.uniform(0.2, 1.0, n)
    idx = pd.RangeIndex(n)
    return (Series(high, index=idx), Series(low, index=idx), Series(close, index=idx))


def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_g191_026_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


def main():
    high, low, close = _ohlc()
    out = g191_026(high, low, close)
    n = len(out)
    fires = int(out.notna().sum())
    nunique = int(out.dropna().nunique())
    first_valid = int(out.notna().idxmax()) if fires else None
    print(f"n={n} fires={fires} ({100 * fires / n:.2f}%) nunique={nunique} "
          f"first_valid_index={first_valid}")
    print(f"min={out.min():.6f} max={out.max():.6f} median={out.median():.6f}")

    m = out.notna()
    for k in (8.0, 64.0, 10.0, 3.7):
        scaled = g191_026(high * k, low * k, close * k)
        max_diff = float((out[m] - scaled[m]).abs().max())
        mask_match = bool((out.isna() == scaled.isna()).all())
        print(f"x{k} PRICE max|diff|={max_diff} nan-mask-match={mask_match}")

    # Gate A: hand-derived small example, mean_length=3, corr_length=2, lag=1.
    # high = close+1, low = close-1 so tp == close exactly (simplifies the
    # hand check to a close-vs-lagged-close correlation).
    hc = Series([10.0, 20.0, 30.0, 40.0, 22.0, 5.0])
    hh = hc + 1.0
    hl = hc - 1.0
    hout = g191_026(hh, hl, hc, mean_length=3, corr_length=2, lag=1)
    tp = (hh + hl + hc) / 3.0
    gap_term = (hc.rolling(3).mean() - hc) / hc
    lagged_close = hc.shift(1)
    corr_term = tp.rolling(2, min_periods=2).corr(lagged_close)
    print("hand tp:", list(tp))
    print("hand gap_term:", list(gap_term))
    print("hand lagged_close:", list(lagged_close))
    print("hand corr_term:", list(corr_term))
    print("hand result:", list(hout))

    # Gate A: spot-check the shipped default against an independent
    # per-bar computation using plain numpy, not pandas' own rolling corr.
    big_h, big_l, big_c = _ohlc(900, seed=5)
    out_big = g191_026(big_h, big_l, big_c)
    h = big_h.to_numpy(dtype=float)
    l = big_l.to_numpy(dtype=float)
    c = big_c.to_numpy(dtype=float)
    tp_arr = (h + l + c) / 3.0
    mean_length, corr_length, lag = 7, 230, 5

    def expected_at(t):
        gap = (np.mean(c[t - mean_length + 1:t + 1]) - c[t]) / c[t]
        tp_window = tp_arr[t - corr_length + 1:t + 1]
        lag_window = c[t - corr_length + 1 - lag:t + 1 - lag]
        corr = np.corrcoef(tp_window, lag_window)[0, 1]
        return gap + corr

    for t in (300, 600, 899):
        a, b = out_big.iloc[t], expected_at(t)
        rel = abs(a - b) / abs(b)
        print(f"t={t} module={a!r} independent={b!r} rel_diff={rel:.3e}")
        assert rel < 1e-9

    # Gate B: future-perturbation leak counts, real module vs. two mutants.
    high, low, close = _ohlc(1500)
    other_h, other_l, other_c = _ohlc(1500, seed=97)
    offsets = range(300, 1500, 40)

    def leaks(fn):
        base = fn(high, low, close)
        hits = 0
        for j in offsets:
            ph, pl, pc = high.copy(), low.copy(), close.copy()
            ph.iloc[j:] = other_h.iloc[j:].values
            pl.iloc[j:] = other_l.iloc[j:].values
            pc.iloc[j:] = other_c.iloc[j:].values
            o = fn(ph, pl, pc)
            a, b = base.iloc[:j], o.iloc[:j]
            if not (a.isna() == b.isna()).all():
                hits += 1
                continue
            mm = a.notna()
            if (a[mm] != b[mm]).any():
                hits += 1
        return hits

    total = len(list(offsets))
    print(f"real-module leaks: {leaks(g191_026)} of {total}")
    shipped = _load_mutant(
        "result = (gap_term + corr_term).replace([np.inf, -np.inf], np.nan)",
        "result = (gap_term + corr_term).replace([np.inf, -np.inf], np.nan).shift(-corr_length)",
    )
    print(f"shipped mutant (corr_length-bar write shift) leaks: "
          f"{leaks(shipped.g191_026)} of {total}")
    weaker = _load_mutant(
        "lagged_close = close.shift(lag)",
        "lagged_close = close.shift(-lag)",
    )
    print(f"weaker mutant (forward DELAY) leaks: {leaks(weaker.g191_026)} of {total}")


if __name__ == "__main__":
    main()
