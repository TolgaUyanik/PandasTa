# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.momentum.crsi` -- the streak term of Connors RSI
(Kaufman 2013 ch. 9): Wilder's RSI of the signed up/down streak. Measured
numbers (warm-up, scale tolerance, Gate C/E) are in `docs/CrsiMeasured.md`.

⚠ READ THIS FIRST. The full Connors RSI composite (`RSI(close, 3) +
RSI(streak, 2) + PercentRank(1-bar return, 100)) / 3`) was built, Gate
E-measured, and two of its three terms were REVERTED: `CRSI_3_2_100` (the
composite) and `CRSI_PCTRANK_100` both measured STRUCK (pooled |rho| 0.9265
/ 0.9717 against the engine's `log_return`, >= the 0.90 revert line on
100% of 89 frames). Only `CRSI_STREAK_2` ships, at DISCLOSE_GAP (pooled
|rho| 0.8362 vs `increasing`). See `docs/CrsiMeasured.md` for the full
Gate E table; this module and its tests now cover the streak term only.

What these tests pin, in order of how much it would hurt to lose them:

* CAUSALITY by future-perturbation: push every bar from `j` onward up (or
  down) by a huge constant, demand bars `[0:j]` bit-identical, over offsets
  past the warm-up. A look-ahead mutant (`importlib` source read, one line
  replaced, `exec`'d in memory -- never a hand-written copy) is proved live,
  then caught at every offset: the streak's direction read 10 bars ahead.
* SCALE-FREE: bit-identical under x8 and x64 (every term is a ratio or a
  sign, both exact under a power-of-two rescale), within 1e-9 under x10 and
  x3.7 with matching NaN masks, and `0 < fires < n` with > 100 distinct
  values.
* CORRECTNESS against an independent loop (Wilder RSI via plain `ewm`, the
  streak via a plain Python loop, neither calling `pandas_ta.momentum.rsi`
  or the module's own helper) over a 400-bar walk, plus a hand-computed
  example: the streak sequence for a 7-bar zigzag.
* BOUND: the column is in [0, 100], since Wilder RSI already is.
* Wiring: `Category`, the accessor, and the column name (`CRSI_STREAK_2`).
"""
import importlib
import types

import numpy as np
import pandas as pd
import pytest
from pandas import DataFrame, Series

from .context import pandas_ta as ta
from pandas_ta.momentum.crsi import crsi, _signed_streak


def _walk(n=1200, seed=11, sigma=0.02, tick=None):
    rng = np.random.default_rng(seed)
    c = 100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n)))
    if tick:
        c = np.round(c / tick) * tick
    return Series(c)


# -------------------------------------------------------------- correctness


def test_hand_computed_streak():
    closes = Series([10.0, 11, 12, 11, 10, 9, 10])
    streak = _signed_streak(closes)
    assert streak.tolist() == [0.0, 1.0, 2.0, -1.0, -2.0, -3.0, 1.0]


def _ref_rsi(x, length):
    """Independent Wilder RSI via plain `ewm` -- never calls `pandas_ta.momentum.rsi`."""
    diff = x.diff()
    gain, loss = diff.clip(lower=0.0), (-diff).clip(lower=0.0)
    avg_gain = gain.ewm(alpha=1.0 / length, min_periods=length).mean()
    avg_loss = loss.ewm(alpha=1.0 / length, min_periods=length).mean()
    return 100.0 * avg_gain / (avg_gain + avg_loss)


def _ref_streak(close):
    streak = [0.0]
    for i in range(1, len(close)):
        d, prev = close.iloc[i] - close.iloc[i - 1], streak[-1]
        if d > 0:
            streak.append(prev + 1.0 if prev > 0 else 1.0)
        elif d < 0:
            streak.append(prev - 1.0 if prev < 0 else -1.0)
        else:
            streak.append(0.0)
    return Series(streak, index=close.index)


def test_matches_an_independent_loop():
    close = _walk(400)
    streak_length = 2

    ref_streak = _ref_streak(close)
    ref_streak_rsi = _ref_rsi(ref_streak, streak_length)

    out = crsi(close)
    actual = out["CRSI_STREAK_2"]
    assert (ref_streak_rsi.isna() == actual.isna()).all()
    m = ref_streak_rsi.notna()
    assert np.nanmax(np.abs(ref_streak_rsi[m].values - actual[m].values)) < 1e-9


def test_bounded():
    out = crsi(_walk(tick=0.05)).dropna()
    assert (out.to_numpy() >= 0.0 - 1e-9).all()
    assert (out.to_numpy() <= 100.0 + 1e-9).all()


# ------------------------------------------------------------- causality


_REAL = importlib.import_module("pandas_ta.momentum.crsi")


def _load_mutant(old, new, tag):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType(f"_crsi_mutant_{tag}")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


MUTANTS = {
    "streak_future": (
        "direction = npsign(close.diff().fillna(0.0).to_numpy())",
        "direction = npsign((close.shift(-10) - close).fillna(0.0).to_numpy())",
    ),
}

OFFSETS = range(150, 1100, 35)


def _leaks(fn):
    """Count offsets `j` at which pushing bars >= j by a huge constant, up
    OR down, moves any bar < j. A huge additive shift (not a spliced-in
    unrelated walk) is deliberate: splicing in an independent random walk
    makes a future-read's sign comparison depend on the two walks' relative
    LEVEL at that specific index, which drifts unpredictably over a long
    GBM path and produces a flaky detection rate. Checking BOTH a forced-up
    and a forced-down shift closes the remaining gap: a future-sign read
    forced positive can coincide with a bar that was already trending up
    over that stretch (and so goes undetected on its own), but the
    forced-negative shift then cannot also coincide -- one of the two always
    disagrees with the un-perturbed run.

    Known blind spot: a look-ahead expressed as a difference/ratio between
    two points that BOTH fall inside the shifted region (j onward) is
    invariant to a constant additive shift and would not be caught by this
    perturbation alone -- it only stresses reads that compare a shifted
    point against an unshifted one. Copy with that in mind."""
    close = _walk()
    base = fn(close)
    hits = 0
    for j in OFFSETS:
        leaked = False
        for delta in (1.0e6, -1.0e6):
            pert = close.copy()
            pert.iloc[j:] = close.iloc[j:] + delta
            out = fn(pert)
            a, b = base.iloc[:j], out.iloc[:j]
            if not (a.isna().to_numpy() == b.isna().to_numpy()).all():
                leaked = True
                break
            m = a.notna().to_numpy().all(axis=1) if a.ndim > 1 else a.notna().to_numpy()
            av, bv = a.to_numpy()[m], b.to_numpy()[m]
            if (av != bv).any():
                leaked = True
                break
        if leaked:
            hits += 1
    return hits


def test_real_module_never_reads_the_future():
    assert _leaks(crsi) == 0


@pytest.mark.parametrize("tag", sorted(MUTANTS))
def test_mutant_is_caught(tag):
    mod = _load_mutant(*MUTANTS[tag], tag)
    close = _walk()
    assert not mod.crsi(close).equals(crsi(close))          # live
    assert _leaks(mod.crsi) == len(list(OFFSETS))            # caught, every offset


# ------------------------------------------------------------- scale-free


@pytest.mark.parametrize("k", [8.0, 64.0])
def test_power_of_two_scale_is_bit_identical(k):
    close = _walk(tick=0.05)
    base, scaled = crsi(close), crsi(close * k)
    assert (base.isna().to_numpy() == scaled.isna().to_numpy()).all()
    m = base.notna().to_numpy()
    assert (base.to_numpy()[m] == scaled.to_numpy()[m]).all()


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_other_scales_within_tolerance(k):
    close = _walk(tick=0.05)
    base, scaled = crsi(close), crsi(close * k)
    assert (base.isna().to_numpy() == scaled.isna().to_numpy()).all()
    assert (base - scaled).abs().max().max() < 1e-9  # pandas .max() skips NaN (the warm-up)


def test_columns_are_not_constant():
    # `< len(out)` alone is vacuous (warm-up NaNs); a constant column would pass it.
    out = crsi(_walk(tick=0.05)).dropna()
    for col in out:
        assert out[col].nunique() > 100, col


# --------------------------------------------------------------- wiring


def test_name_registration_and_accessor():
    close = _walk(300)
    df = DataFrame({"open": close, "high": close, "low": close,
                    "close": close, "volume": 1.0})
    assert "crsi" in ta.Category["momentum"]
    out = df.ta.crsi()
    pd.testing.assert_frame_equal(out, crsi(close))
    assert list(out.columns) == ["CRSI_STREAK_2"]
    renamed = df.ta.crsi(streak_length=3)
    assert list(renamed.columns) == ["CRSI_STREAK_3"]
