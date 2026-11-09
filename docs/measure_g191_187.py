# -*- coding: utf-8 -*-
"""Prints the exact numbers quoted in docs/G191187Measured.md for
`pandas_ta.momentum.g191_187`. Synthetic frame only (Gate E, the real-data
measurement, is run by the launcher after this session)."""
import importlib
import types

import numpy as np
import pandas as pd
import pandas_ta as ta
from pandas import Series

from pandas_ta.momentum.g191_187 import g191_187

_REAL = importlib.import_module("pandas_ta.momentum.g191_187")


def _ohlc(n=1500, seed=11, sigma=0.015):
    rng = np.random.default_rng(seed)
    close = 100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n)))
    rng2 = np.random.default_rng(seed + 1)
    spread = np.abs(rng2.normal(0.0, 0.01, n)) * close
    high = close + spread * rng2.uniform(0.2, 1.0, n)
    low = close - spread * rng2.uniform(0.2, 1.0, n)
    open_ = low + (high - low) * rng2.uniform(0.0, 1.0, n)
    idx = pd.RangeIndex(n)
    return Series(open_, index=idx), Series(high, index=idx), Series(close, index=idx)


def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_g191_187_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


WRITE_SHIFT_MUTANT = (
    "result = dtm / close",
    "result = (dtm / close).shift(-length)",
)
FORWARD_DELAY_MUTANT = (
    "prior_open = open_.shift(1)",
    "prior_open = open_.shift(-1)",
)

OFFSETS = range(150, 1500, 40)


def _leaks(fn):
    open_, high, close = _ohlc(1500)
    o_open, o_high, o_close = _ohlc(1500, seed=97)
    base = fn(open_, high, close)
    hits = 0
    for j in OFFSETS:
        po, ph, pc = open_.copy(), high.copy(), close.copy()
        po.iloc[j:] = o_open.iloc[j:].values
        ph.iloc[j:] = o_high.iloc[j:].values
        pc.iloc[j:] = o_close.iloc[j:].values
        out = fn(po, ph, pc)
        a, b = base.iloc[:j], out.iloc[:j]
        if not (a.isna() == b.isna()).all():
            hits += 1
            continue
        m = a.notna()
        if (a[m] != b[m]).any():
            hits += 1
    return hits


def main():
    print("wiring:")
    print("  g191_187 in Category['momentum']:", "g191_187" in ta.Category["momentum"])
    print("  Category total:", sum(len(v) for v in ta.Category.values()))
    print("  Category['momentum'] size:", len(ta.Category["momentum"]))

    open_, high, close = _ohlc()
    out = g191_187(open_, high, close)
    n = len(out)
    fires = int(out.notna().sum())
    nunique = int(out.dropna().nunique())
    first_valid = int(out.notna().idxmax()) if fires else None
    print(f"n={n} fires={fires} ({100 * fires / n:.2f}%) nunique={nunique} "
          f"first_valid_index={first_valid}")
    print(f"min={out.min():.6f} max={out.max():.6f} median={out.median():.6f}")

    m = out.notna()
    for k in (8.0, 64.0, 10.0, 3.7):
        scaled = g191_187(open_ * k, high * k, close * k)
        max_diff = float((out[m] - scaled[m]).abs().max())
        mask_match = bool((out.isna() == scaled.isna()).all())
        print(f"x{k} PRICE max|diff|={max_diff} nan-mask-match={mask_match}")

    # Gate A: does MAX(H-O, O-O1) collapse to one term, as #93's MAX(O-L,O-O1)
    # does? Measure it rather than assume it does not.
    o = open_.to_numpy(dtype=float)
    h = high.to_numpy(dtype=float)
    o1 = np.roll(o, 1)
    o1[0] = np.nan
    up = o > o1
    up_move = np.maximum(h - o, o - o1)
    ho_wins = np.isclose(up_move[up], (h - o)[up])
    oo1_wins = np.isclose(up_move[up], (o - o1)[up])
    print(f"MAX(H-O,O-O1): H-O wins at {int(ho_wins.sum())}, O-O1 wins at "
          f"{int(oo1_wins.sum())}, both (tie) at {int((ho_wins & oo1_wins).sum())}, "
          f"of {int(up.sum())} up-branch bars")

    # Bar 0 of `contribution`: is the explicit `.where(o1.notna())` mask
    # load-bearing on the current arithmetic?
    masked_bar0 = np.where(np.isnan(o1), np.nan, np.where(o <= o1, 0.0, up_move))[0]
    unmasked_bar0 = np.where(o <= o1, 0.0, up_move)[0]
    print(f"bar 0: masked={masked_bar0!r} unmasked={unmasked_bar0!r} (both NaN: "
          f"{bool(np.isnan(masked_bar0) and np.isnan(unmasked_bar0))})")

    # Gate A: hand-derived seven-bar example.
    open7 = Series([10.0, 12.0, 9.0, 15.0, 11.0, 20.0, 13.0])
    high7 = Series([11.0, 13.0, 10.0, 16.0, 12.0, 30.0, 14.0])
    close7 = Series([100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0])
    out7 = g191_187(open7, high7, close7, length=3)
    print("hand-derived 7-bar example:", out7.tolist())

    # Gate A: independent per-bar spot check at the shipped default.
    open9, high9, close9 = _ohlc(900, seed=5)
    out9 = g191_187(open9, high9, close9)
    oo, hh, cc = (s.to_numpy(dtype=float) for s in (open9, high9, close9))
    length = 20

    def expected_at(t):
        idx = np.arange(t - length + 1, t + 1)
        o1i = oo[idx - 1]
        umi = np.maximum(hh[idx] - oo[idx], oo[idx] - o1i)
        contrib = np.where(oo[idx] <= o1i, 0.0, umi)
        return np.sum(contrib) / cc[t]

    for t in (300, 600, 899):
        print(f"t={t} module={out9.iloc[t]!r} independent={expected_at(t)!r}")

    # Gate B: future-perturbation leak counts, real module vs. the mutants.
    print(f"real-module leaks: {_leaks(g191_187)} of {len(list(OFFSETS))}")
    write_shift = _load_mutant(*WRITE_SHIFT_MUTANT)
    print(f"write-shift mutant leaks: {_leaks(write_shift.g191_187)} of {len(list(OFFSETS))}")
    forward_delay = _load_mutant(*FORWARD_DELAY_MUTANT)
    print(f"forward-delay mutant leaks: {_leaks(forward_delay.g191_187)} of {len(list(OFFSETS))}")


if __name__ == "__main__":
    main()
