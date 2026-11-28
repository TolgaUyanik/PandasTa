# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.candles.b3_outside_pivot3` -- the prior bar is at once
a strict 3-bar swing high and a strict 3-bar swing low, from issue #199
(Reddit, tier 4: rd:options:1k1hyso). Measurements are in
docs/B3OutsidePivot3Measured.md.

What these pin, in order of how much it would hurt to lose:

* CORRECTNESS against the issue's own formula (not the screen prototype):
  hand-derived fixtures for the fire case, each one-sided miss (swing high
  only, swing low only), a tie with the LEFT neighbour and a tie with the
  RIGHT neighbour (strict `>`/`<` -- neither fires), plus an independent
  pure-Python bar loop over tick-rounded random frames (ties included) that
  must agree on every bar (measured: 0 mismatches on 12 frames x 1,500 bars,
  646-753 equal-high/equal-low ties and 7-17 fires per frame at tick 1.0).
* CAUSALITY: bars before a perturbation point J are bit-identical whether
  or not the frame's tail is replaced by an unrelated one, at several J,
  and a mutant (the final write shifted one bar into the future via
  `.shift(-1)` -- the flag back-dated onto the middle bar, which needs the
  right neighbour it cannot yet see) proved live and caught at some swept J
  (measured: real 0 of 293 J, mutant 12 of 293).
* SCALE-FREE: bit-identical under a price rescale (x8/x64, and x10/x3.7 --
  a discrete {0, 1} output has no rounding to tolerate, so these are also
  exact), with `0 < fires < n` (measured: 69 of 1,998 settled bars on the
  2,000-bar seed-4 frame).
* Reachability (fires on a random synthetic frame, not a constant column)
  and the wiring (`Category`, the accessor, warm-up, column name).
"""
import importlib
import types

import numpy as np
import pandas as pd
import pytest
from pandas import DataFrame

from .context import pandas_ta as ta

_REAL = importlib.import_module("pandas_ta.candles.b3_outside_pivot3")
b3_outside_pivot3 = _REAL.b3_outside_pivot3


# ---------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------
def _hl(rows):
    """rows: list of (high, low) 2-tuples, oldest first."""
    h, l = zip(*rows)
    return DataFrame({"high": h, "low": l})


def _at2(rows):
    df = _hl(rows)
    return b3_outside_pivot3(df.high, df.low).iloc[2]


def test_fires_when_middle_bar_is_both_swings():
    # middle (102, 98) above both highs and below both lows -- fires at bar 2
    assert _at2([(101.0, 99.0), (102.0, 98.0), (101.5, 98.5)]) == 1.0


def test_swing_high_only_does_not_fire():
    assert _at2([(101.0, 99.0), (102.0, 98.0), (101.5, 97.0)]) == 0.0


def test_swing_low_only_does_not_fire():
    assert _at2([(101.0, 99.0), (102.0, 98.0), (103.0, 98.5)]) == 0.0


def test_tie_with_left_neighbour_does_not_fire():
    assert _at2([(102.0, 99.0), (102.0, 98.0), (101.5, 98.5)]) == 0.0
    assert _at2([(101.0, 98.0), (102.0, 98.0), (101.5, 98.5)]) == 0.0


def test_tie_with_right_neighbour_does_not_fire():
    assert _at2([(101.0, 99.0), (102.0, 98.0), (102.0, 98.5)]) == 0.0
    assert _at2([(101.0, 99.0), (102.0, 98.0), (101.5, 98.0)]) == 0.0


def test_warmup_is_exactly_two_bars():
    rows = [(101.0, 99.0), (102.0, 98.0), (101.5, 98.5), (101.0, 99.0)]
    df = _hl(rows)
    out = b3_outside_pivot3(df.high, df.low)
    assert out.iloc[:2].isna().all()
    assert out.iloc[2:].notna().all()


def _reference(high, low):
    """Independent bar loop over plain Python floats, read straight from the
    issue's formula -- no pandas shifts."""
    h, l = list(high), list(low)
    out = [np.nan, np.nan]
    for t in range(2, len(h)):
        hit = h[t - 1] > max(h[t - 2], h[t]) and l[t - 1] < min(l[t - 2], l[t])
        out.append(1.0 if hit else 0.0)
    return np.array(out)


def _ticky(n, seed, tick=1.0):
    """Tick-rounded walk with coarse ticks so equal highs/lows are common."""
    rng = np.random.default_rng(seed)
    c = 100 + np.cumsum(rng.normal(0, 1.5, n))
    h = np.round((c + np.abs(rng.normal(0, 1.0, n))) / tick) * tick
    l = np.round((c - np.abs(rng.normal(0, 1.0, n))) / tick) * tick
    return pd.Series(h), pd.Series(np.minimum(l, h))


@pytest.mark.parametrize("seed", range(12))
def test_matches_independent_loop_on_tick_rounded_frames(seed):
    h, l = _ticky(1500, seed)
    got = b3_outside_pivot3(h, l).to_numpy()
    ref = _reference(h, l)
    assert np.array_equal(got, ref, equal_nan=True)


# ---------------------------------------------------------------------
# random frames (causality, scale, reachability)
# ---------------------------------------------------------------------
def _frame(n=600, seed=1):
    rng = np.random.default_rng(seed)
    ret = rng.normal(0, 0.012, n)
    close = 100 * np.exp(np.cumsum(ret))
    spread = close * np.abs(rng.normal(0, 0.006, n))
    high = close + spread
    low = close - spread
    openp = close * (1 + rng.normal(0, 0.004, n))
    high = np.maximum.reduce([high, openp, close])
    low = np.minimum.reduce([low, openp, close])
    idx = pd.date_range("2020-01-01", periods=n, freq="D")
    return DataFrame({"open": openp, "high": high, "low": low, "close": close},
                     index=idx)


def _spliced(n, j, seed_a, seed_b):
    """Frame A for its full length; frame B's tail (from `j` on) grafted on
    top of frame A's prefix -- an unrelated, independently drawn future."""
    a = _frame(n, seed_a)
    b = _frame(n, seed_b)
    spliced = a.copy()
    spliced.iloc[j:] = b.iloc[j:].to_numpy()
    return a, spliced


# -------------------------------------------------------------- causality
MUTANT = (
    "pivot = (swing_high & swing_low).astype(float).where(left_high.notna())",
    "pivot = (swing_high & swing_low).astype(float).where(left_high.notna()).shift(-1)",
)


def _load_mutant():
    src = open(_REAL.__file__, encoding="utf-8").read()
    old, new = MUTANT
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_b3_outside_pivot3_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


@pytest.mark.parametrize("j", [10, 50, 300, 590])
def test_real_module_never_reads_the_future(j):
    a, spliced = _spliced(600, j, seed_a=1, seed_b=2)
    base = b3_outside_pivot3(a.high, a.low).iloc[:j]
    perturbed = b3_outside_pivot3(spliced.high, spliced.low).iloc[:j]
    pd.testing.assert_series_equal(base, perturbed, check_exact=True)


def test_mutant_is_caught_across_a_sweep_of_perturbation_points():
    """A single fixed J is a weak test here -- the pattern fires on a few
    percent of bars, so a one-bar back-date only shows up when a bar adjacent
    to J happens to be an event (the same low-power problem
    `tests/test_rd_outside_bar.py` documents). The assertion is therefore:
    the real module leaks 0 bars before J at EVERY swept J, and the mutant
    leaks at SOME J, not any particular one."""
    mod = _load_mutant()
    a = _frame(600, seed=1)
    b = _frame(600, seed=2)
    mut_a_full = mod.b3_outside_pivot3(a.high, a.low)
    real_a_full = b3_outside_pivot3(a.high, a.low)

    # live: the mutant differs from the real module on the unperturbed frame
    assert not mut_a_full.equals(real_a_full)

    js = list(range(10, 596, 2))
    real_leaks, mutant_leaks = 0, 0
    for j in js:
        spliced = a.copy()
        spliced.iloc[j:] = b.iloc[j:].to_numpy()
        real_b = b3_outside_pivot3(spliced.high, spliced.low)
        if not real_a_full.iloc[:j].equals(real_b.iloc[:j]):
            real_leaks += 1

        mut_b = mod.b3_outside_pivot3(spliced.high, spliced.low)
        av, bv = mut_a_full.iloc[j - 1], mut_b.iloc[j - 1]
        both_nan = pd.isna(av) and pd.isna(bv)
        if not (av == bv or both_nan):
            mutant_leaks += 1

    assert real_leaks == 0, f"real module leaked before J at {real_leaks} of {len(js)} J values"
    assert mutant_leaks > 0, f"mutant never leaked across {len(js)} J values -- test is blind"


# ------------------------------------------------------------ scale-free
@pytest.mark.parametrize("k", [8.0, 64.0, 10.0, 3.7])
def test_price_scale_is_bit_identical(k):
    df = _frame(n=2000, seed=4)
    base = b3_outside_pivot3(df.high, df.low)
    scaled = b3_outside_pivot3(df.high * k, df.low * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] == scaled[m]).all()
    fires = int((base[m] == 1.0).sum())
    assert 0 < fires < int(m.sum())


# ------------------------------------------------------------ reachability
def test_fires_and_is_not_constant():
    df = _frame(n=2000, seed=4)
    out = b3_outside_pivot3(df.high, df.low)
    fired = out.dropna()
    assert 0 < (fired != 0.0).sum() < len(fired)
    assert set(fired.unique()) == {0.0, 1.0}


# ------------------------------------------------------------- edge cases
def test_short_input_returns_none():
    df = _hl([(101.0, 99.0), (102.0, 98.0)])
    assert b3_outside_pivot3(df.high, df.low) is None


def test_offset():
    rows = [(101.0, 99.0), (102.0, 98.0), (101.5, 98.5), (101.0, 99.0)]
    df = _hl(rows)
    out0 = b3_outside_pivot3(df.high, df.low)
    out1 = b3_outside_pivot3(df.high, df.low, offset=1)
    assert out0.iloc[2] == 1.0
    assert out1.iloc[3] == 1.0


# ---------------------------------------------------------------- wiring
def test_column_name_and_category():
    df = _hl([(101.0, 99.0), (102.0, 98.0), (101.5, 98.5)])
    out = b3_outside_pivot3(df.high, df.low)
    assert out.name == "B3_OUTSIDE_PIVOT3"
    assert out.category == "candles"


def test_registered_in_category():
    assert "b3_outside_pivot3" in ta.Category["candles"]


def test_accessor_matches_module_level():
    df = _frame(n=20, seed=9)
    via_module = b3_outside_pivot3(df["high"], df["low"])
    via_accessor = df.ta.b3_outside_pivot3()
    pd.testing.assert_series_equal(via_module, via_accessor, check_exact=True)
