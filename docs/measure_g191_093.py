# -*- coding: utf-8 -*-
"""Prints the exact numbers quoted in docs/G191093Measured.md for
`pandas_ta.momentum.g191_093`. Synthetic frame only (Gate E, the real-data
measurement, is run by the launcher after this session)."""
import importlib
import types

import numpy as np
import pandas as pd
import pandas_ta as ta
from pandas import Series

from pandas_ta.momentum.g191_093 import g191_093

_REAL = importlib.import_module("pandas_ta.momentum.g191_093")


def _ohlc(n=1500, seed=11, sigma=0.015):
    rng = np.random.default_rng(seed)
    close = 100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n)))
    rng2 = np.random.default_rng(seed + 1)
    spread = np.abs(rng2.normal(0.0, 0.01, n)) * close
    high = close + spread * rng2.uniform(0.2, 1.0, n)
    low = close - spread * rng2.uniform(0.2, 1.0, n)
    open_ = low + (high - low) * rng2.uniform(0.0, 1.0, n)
    idx = pd.RangeIndex(n)
    return Series(open_, index=idx), Series(low, index=idx), Series(close, index=idx)


def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_g191_093_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


WRITE_SHIFT_MUTANT = (
    "result = dbm / close",
    "result = (dbm / close).shift(-length)",
)
FORWARD_DELAY_MUTANT = (
    "prior_open = open_.shift(1)",
    "prior_open = open_.shift(-1)",
)

OFFSETS = range(150, 1500, 40)


def _leaks(fn):
    open_, low, close = _ohlc(1500)
    o_open, o_low, o_close = _ohlc(1500, seed=97)
    base = fn(open_, low, close)
    hits = 0
    for j in OFFSETS:
        po, pl, pc = open_.copy(), low.copy(), close.copy()
        po.iloc[j:] = o_open.iloc[j:].values
        pl.iloc[j:] = o_low.iloc[j:].values
        pc.iloc[j:] = o_close.iloc[j:].values
        out = fn(po, pl, pc)
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
    print("  g191_093 in Category['momentum']:", "g191_093" in ta.Category["momentum"])
    print("  Category total:", sum(len(v) for v in ta.Category.values()))
    print("  Category['momentum'] size:", len(ta.Category["momentum"]))

    open_, low, close = _ohlc()
    out = g191_093(open_, low, close)
    n = len(out)
    fires = int(out.notna().sum())
    nunique = int(out.dropna().nunique())
    first_valid = int(out.notna().idxmax()) if fires else None
    print(f"n={n} fires={fires} ({100 * fires / n:.2f}%) nunique={nunique} "
          f"first_valid_index={first_valid}")
    print(f"min={out.min():.6f} max={out.max():.6f} median={out.median():.6f}")

    m = out.notna()
    for k in (8.0, 64.0, 10.0, 3.7):
        scaled = g191_093(open_ * k, low * k, close * k)
        max_diff = float((out[m] - scaled[m]).abs().max())
        mask_match = bool((out.isna() == scaled.isna()).all())
        print(f"x{k} PRICE max|diff|={max_diff} nan-mask-match={mask_match}")

    # Gate A: MAX(O-L, O-O1) collapses to O-L at every down-branch bar
    # under OHLC consistency (L <= O) -- measured, not merely argued.
    o = open_.to_numpy(dtype=float)
    l = low.to_numpy(dtype=float)
    o1 = np.roll(o, 1)
    o1[0] = np.nan
    down = o < o1
    down_move = np.maximum(o - l, o - o1)
    ol_wins = np.isclose(down_move[down], (o - l)[down])
    print(f"MAX(O-L,O-O1) selects O-L at {int(ol_wins.sum())} of {int(down.sum())} down-branch bars")

    # Bar 0 of `contribution`: the explicit `.where(o1.notna())` mask is not
    # load-bearing on the current arithmetic -- np.maximum's NaN-propagation
    # already reads NaN at bar 0 with or without it.
    masked_bar0 = np.where(np.isnan(o1), np.nan, np.where(o >= o1, 0.0, down_move))[0]
    unmasked_bar0 = np.where(o >= o1, 0.0, down_move)[0]
    print(f"bar 0: masked={masked_bar0!r} unmasked={unmasked_bar0!r} (both NaN: "
          f"{bool(np.isnan(masked_bar0) and np.isnan(unmasked_bar0))})")

    # Gate A: hand-derived six-bar example.
    open6 = Series([10.0, 8.0, 12.0, 9.0, 15.0, 7.0])
    low6 = Series([9.0, 6.0, 11.0, 5.0, 14.0, 6.0])
    close6 = Series([100.0, 101.0, 102.0, 103.0, 104.0, 105.0])
    out6 = g191_093(open6, low6, close6, length=3)
    print("hand-derived 6-bar example:", out6.tolist())

    # Gate A: independent per-bar spot check at the shipped default.
    open9, low9, close9 = _ohlc(900, seed=5)
    out9 = g191_093(open9, low9, close9)
    oo, ll, cc = (s.to_numpy(dtype=float) for s in (open9, low9, close9))
    length = 20

    def expected_at(t):
        idx = np.arange(t - length + 1, t + 1)
        o1i = oo[idx - 1]
        dmi = np.maximum(oo[idx] - ll[idx], oo[idx] - o1i)
        contrib = np.where(oo[idx] >= o1i, 0.0, dmi)
        return np.sum(contrib) / cc[t]

    for t in (300, 600, 899):
        print(f"t={t} module={out9.iloc[t]!r} independent={expected_at(t)!r}")

    # Gate B: future-perturbation leak counts, real module vs. the mutants.
    print(f"real-module leaks: {_leaks(g191_093)} of {len(list(OFFSETS))}")
    write_shift = _load_mutant(*WRITE_SHIFT_MUTANT)
    print(f"write-shift mutant leaks: {_leaks(write_shift.g191_093)} of {len(list(OFFSETS))}")
    forward_delay = _load_mutant(*FORWARD_DELAY_MUTANT)
    print(f"forward-delay mutant leaks (random sweep): "
          f"{_leaks(forward_delay.g191_093)} of {len(list(OFFSETS))} "
          f"-- coincidental gate agreement hides some, hence the dedicated test")

    # Deterministic forward-delay construction used by the actual test.
    length2 = 3
    n2 = 10
    j = 6
    open_base = Series([float(10 + i) for i in range(n2)])
    low_base = open_base - 1.0
    close_base = Series([100.0] * n2)
    open_pert = open_base.copy()
    open_pert.iloc[j:] = open_base.iloc[j - 1] - 5.0
    low_pert = low_base.copy()
    low_pert.iloc[j:] = open_pert.iloc[j:] - 1.0

    base_mut = forward_delay.g191_093(open_base, low_base, close_base, length=length2)
    pert_mut = forward_delay.g191_093(open_pert, low_pert, close_base, length=length2)
    base_real = g191_093(open_base, low_base, close_base, length=length2)
    pert_real = g191_093(open_pert, low_pert, close_base, length=length2)
    print(f"deterministic forward-delay mutant at bar {j - 1}: "
          f"base={base_mut.iloc[j - 1]!r} pert={pert_mut.iloc[j - 1]!r} (mutant leaks)")
    print(f"deterministic forward-delay, real module at bar {j - 1}: "
          f"base={base_real.iloc[j - 1]!r} pert={pert_real.iloc[j - 1]!r} (real module clean)")


if __name__ == "__main__":
    main()
