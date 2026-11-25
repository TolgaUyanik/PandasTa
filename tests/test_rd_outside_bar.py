# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.candles.rd_outside_bar` -- outside bar: range engulfs
the prior bar's range, from issue #167 (Reddit, tier 4: rd:Trading:1og1s0z,
rd:Daytrading:1gxmcnv). Measurements are in docs/RdOutsideBarMeasured.md.

What these pin, in order of how much it would hurt to lose:

* CORRECTNESS against the issue's own formula (not the screen prototype):
  hand-derived fixtures for the fire case and each of the two ways it can
  fail to fire (high side only, low side only), plus the exact-equal
  boundary (neither `>` nor `<` is satisfied on a tie).
* CAUSALITY: bars before a perturbation point J are bit-identical whether
  or not the frame's tail is replaced by an unrelated one, at several J,
  and a mutant (the final write shifted one bar into the future via
  `.shift(-1)`) proved live and caught at some swept J (not necessarily
  every J -- a {0, 1} output fires on a minority of bars).
* SCALE-FREE: bit-identical under a price rescale (x8/x64, and x10/x3.7 --
  a discrete {0, 1} output has no rounding to tolerate, so these are also
  exact).
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

_REAL = importlib.import_module("pandas_ta.candles.rd_outside_bar")
rd_outside_bar = _REAL.rd_outside_bar


# ---------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------
def _hl(rows):
    """rows: list of (high, low) 2-tuples, oldest first."""
    h, l = zip(*rows)
    return DataFrame({"high": h, "low": l})


def test_fires_when_both_sides_engulf():
    rows = [
        (101.0, 99.0),   # prior bar
        (102.0, 98.0),   # current: high > 101, low < 99 -- fires
    ]
    df = _hl(rows)
    out = rd_outside_bar(df.high, df.low)
    assert pd.isna(out.iloc[0])
    assert out.iloc[1] == 1.0


def test_high_side_only_does_not_fire():
    rows = [
        (101.0, 99.0),
        (102.0, 99.5),   # high > 101, but low 99.5 is NOT < 99
    ]
    df = _hl(rows)
    out = rd_outside_bar(df.high, df.low)
    assert out.iloc[1] == 0.0


def test_low_side_only_does_not_fire():
    rows = [
        (101.0, 99.0),
        (100.5, 98.0),   # low < 99, but high 100.5 is NOT > 101
    ]
    df = _hl(rows)
    out = rd_outside_bar(df.high, df.low)
    assert out.iloc[1] == 0.0


def test_exact_tie_does_not_fire():
    """high == prior high and low == prior low -- neither `>` nor `<` holds."""
    rows = [
        (101.0, 99.0),
        (101.0, 99.0),
    ]
    df = _hl(rows)
    out = rd_outside_bar(df.high, df.low)
    assert out.iloc[1] == 0.0


def test_warmup_is_exactly_one_bar():
    rows = [(101.0, 99.0), (102.0, 98.0), (103.0, 97.0)]
    df = _hl(rows)
    out = rd_outside_bar(df.high, df.low)
    assert pd.isna(out.iloc[0])
    assert out.iloc[1:].notna().all()


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
    "outside_bar = outside.astype(float).where(prior_high.notna())",
    "outside_bar = outside.astype(float).where(prior_high.notna()).shift(-1)",
)


def _load_mutant():
    src = open(_REAL.__file__, encoding="utf-8").read()
    old, new = MUTANT
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_rd_outside_bar_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


@pytest.mark.parametrize("j", [10, 50, 300, 590])
def test_real_module_never_reads_the_future(j):
    a, spliced = _spliced(600, j, seed_a=1, seed_b=2)
    base = rd_outside_bar(a.high, a.low).iloc[:j]
    perturbed = rd_outside_bar(spliced.high, spliced.low).iloc[:j]
    pd.testing.assert_series_equal(base, perturbed, check_exact=True)


def test_mutant_is_caught_across_a_sweep_of_perturbation_points():
    """A single fixed J is a weak test here -- the pattern fires on a
    minority of bars (below), so a one-bar back-date only shows up when a
    bar adjacent to J happens to be an event, the same low-power problem
    `tests/test_altport2_ports.py` documents for `smc_sweep`. The assertion
    is therefore: the real module leaks 0 bars before J at EVERY swept J,
    and the mutant leaks at SOME J, not any particular one."""
    mod = _load_mutant()
    a = _frame(600, seed=1)
    b = _frame(600, seed=2)
    mut_a_full = mod.rd_outside_bar(a.high, a.low)
    real_a_full = rd_outside_bar(a.high, a.low)

    # live: the mutant differs from the real module on the unperturbed frame
    assert not mut_a_full.equals(real_a_full)

    js = list(range(10, 596, 2))
    real_leaks, mutant_leaks = 0, 0
    for j in js:
        spliced = a.copy()
        spliced.iloc[j:] = b.iloc[j:].to_numpy()
        real_b = rd_outside_bar(spliced.high, spliced.low)
        if not real_a_full.iloc[:j].equals(real_b.iloc[:j]):
            real_leaks += 1

        mut_b = mod.rd_outside_bar(spliced.high, spliced.low)
        av, bv = mut_a_full.iloc[j - 1], mut_b.iloc[j - 1]
        both_nan = pd.isna(av) and pd.isna(bv)
        if not (av == bv or both_nan):
            mutant_leaks += 1

    assert real_leaks == 0, f"real module leaked before J at {real_leaks} of {len(js)} J values"
    assert mutant_leaks > 0, f"mutant never leaked across {len(js)} J values -- test is blind"


# ------------------------------------------------------------ scale-free
@pytest.mark.parametrize("k", [8.0, 64.0, 10.0, 3.7])
def test_price_scale_is_bit_identical(k):
    df = _frame(seed=4)
    base = rd_outside_bar(df.high, df.low)
    scaled = rd_outside_bar(df.high * k, df.low * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] == scaled[m]).all()


# ------------------------------------------------------------ reachability
def test_fires_and_is_not_constant():
    df = _frame(n=2000, seed=4)
    out = rd_outside_bar(df.high, df.low)
    fired = out.dropna()
    assert (fired != 0.0).sum() > 0
    assert (fired != 0.0).sum() < len(fired)
    assert 1.0 in fired.values
    assert 0.0 in fired.values


# ------------------------------------------------------------- edge cases
def test_short_input_returns_none():
    df = _hl([(101.0, 99.0)])
    assert rd_outside_bar(df.high, df.low) is None


def test_offset():
    rows = [(101.0, 99.0), (102.0, 98.0), (103.0, 97.0)]
    df = _hl(rows)
    out0 = rd_outside_bar(df.high, df.low)
    out1 = rd_outside_bar(df.high, df.low, offset=1)
    assert out0.iloc[1] == 1.0
    assert pd.isna(out1.iloc[1])
    assert out1.iloc[2] == 1.0


# ---------------------------------------------------------------- wiring
def test_column_name_and_category():
    df = _hl([(101.0, 99.0), (102.0, 98.0)])
    out = rd_outside_bar(df.high, df.low)
    assert out.name == "RD_OUTSIDE_BAR"
    assert out.category == "candles"


def test_registered_in_category():
    assert "rd_outside_bar" in ta.Category["candles"]


def test_accessor_matches_module_level():
    df = _frame(n=20, seed=9)
    via_module = rd_outside_bar(df["high"], df["low"])
    via_accessor = df.ta.rd_outside_bar()
    pd.testing.assert_series_equal(via_module, via_accessor, check_exact=True)
