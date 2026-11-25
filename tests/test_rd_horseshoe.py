# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.candles.rd_horseshoe` -- the horseshoe 4-bar
formation, signed, from issue #164 (a Reddit post, r/Daytrading, tier 4,
rd:Daytrading:1rwgrts). Measurements are in docs/RdHorseshoeMeasured.md.

What these pin, in order of how much it would hurt to lose:

* CORRECTNESS against the issue's own formula (not the screen prototype):
  two hand-derived fixtures (one bull, one mirrored bear) where every input
  bar and the expected output were chosen on paper before the module ran,
  plus two fixtures (one per side) showing the outer-bound check actually
  gates the pattern (breaking it blocks the fire) and one showing a doji
  breaks the red/green requirement.
* CAUSALITY: bars before a perturbation point J are bit-identical whether
  or not the frame's tail is replaced by an unrelated one, at several J,
  and a mutant (the final write shifted one bar into the future via
  `.shift(-1)`) proved live and caught at 24 of the 293 swept J (not at
  every J -- a {-1,0,1} output fires on ~8% of bars).
* SCALE-FREE: bit-identical under a price rescale (x8/x64, and x10/x3.7 --
  a discrete {-1, 0, 1} output has no rounding to tolerate, so these are
  also exact).
* Reachability (both signs fire on a random synthetic frame, not a
  constant column) and the wiring (`Category`, the accessor, warm-up,
  column name).
"""
import importlib
import types

import numpy as np
import pandas as pd
import pytest
from pandas import DataFrame

from .context import pandas_ta as ta

_REAL = importlib.import_module("pandas_ta.candles.rd_horseshoe")
rd_horseshoe = _REAL.rd_horseshoe


# ---------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------
def _ohlc(rows):
    """rows: list of (open, high, low, close) 4-tuples, oldest first."""
    o, h, l, c = zip(*rows)
    return DataFrame({"open": o, "high": h, "low": l, "close": c})


def _bull_rows():
    """bar1 red, bar2 green, bar3 red, bar4 (current) green; outer bound
    max(open1=100, close4=101) = 101; high(bar2)=100.7 and high(bar3)=100.9
    both <= 101 -- the pattern fires."""
    return [
        (100.0, 101.0, 97.0, 98.0),    # bar1: red
        (98.0, 100.7, 97.8, 100.5),    # bar2: green, high 100.7 <= 101
        (100.5, 100.9, 98.5, 99.0),    # bar3: red, high 100.9 <= 101
        (99.0, 101.6, 98.7, 101.0),    # bar4 (current): green
    ]


def _bear_rows():
    """Mirror: bar1 green, bar2 red, bar3 green, bar4 (current) red; outer
    bound min(open1=100, close4=99) = 99; low(bar2)=99.3 and low(bar3)=99.8
    both >= 99 -- the pattern fires."""
    return [
        (100.0, 103.0, 99.5, 102.0),   # bar1: green
        (102.0, 102.3, 99.3, 100.0),   # bar2: red, low 99.3 >= 99
        (100.0, 101.8, 99.8, 101.5),   # bar3: green, low 99.8 >= 99
        (101.5, 101.7, 98.5, 99.0),    # bar4 (current): red
    ]


def test_bull_fixture_is_exact():
    df = _ohlc(_bull_rows())
    out = rd_horseshoe(df.open, df.high, df.low, df.close)
    assert out.iloc[:3].isna().all()
    assert out.iloc[3] == 1.0


def test_bear_fixture_is_exact():
    df = _ohlc(_bear_rows())
    out = rd_horseshoe(df.open, df.high, df.low, df.close)
    assert out.iloc[:3].isna().all()
    assert out.iloc[3] == -1.0


def test_outer_bound_violation_blocks_the_bull_pattern():
    """Same colours as the bull fixture, but bar2's high (101.2) now pokes
    above max(open1, close4) = 101 -- the formation must NOT fire."""
    rows = _bull_rows()
    rows[1] = (98.0, 101.2, 97.8, 100.5)
    df = _ohlc(rows)
    out = rd_horseshoe(df.open, df.high, df.low, df.close)
    assert out.iloc[3] == 0.0


def test_outer_bound_violation_blocks_the_bear_pattern():
    rows = _bear_rows()
    rows[1] = (102.0, 102.3, 98.7, 100.0)  # low 98.7 < min(open1, close4)=99
    df = _ohlc(rows)
    out = rd_horseshoe(df.open, df.high, df.low, df.close)
    assert out.iloc[3] == 0.0


def test_a_doji_breaks_the_colour_requirement():
    """bar3 closes exactly at its open (neither red nor green) -- the bull
    pattern must not fire even though the outer-bound check would pass."""
    rows = _bull_rows()
    o3, h3, l3, _ = rows[2]
    rows[2] = (o3, h3, l3, o3)  # close == open
    df = _ohlc(rows)
    out = rd_horseshoe(df.open, df.high, df.low, df.close)
    assert out.iloc[3] == 0.0


def test_warmup_is_exactly_three_bars():
    df = _ohlc(_bull_rows())
    out = rd_horseshoe(df.open, df.high, df.low, df.close)
    assert out.iloc[:3].isna().all()
    assert out.iloc[3:].notna().all()


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
    "horseshoe = horseshoe.where(bar1_open.notna())",
    "horseshoe = horseshoe.where(bar1_open.notna()).shift(-1)",
)


def _load_mutant():
    src = open(_REAL.__file__, encoding="utf-8").read()
    old, new = MUTANT
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_rd_horseshoe_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


@pytest.mark.parametrize("j", [10, 50, 300, 590])
def test_real_module_never_reads_the_future(j):
    a, spliced = _spliced(600, j, seed_a=1, seed_b=2)
    base = rd_horseshoe(a.open, a.high, a.low, a.close).iloc[:j]
    perturbed = rd_horseshoe(spliced.open, spliced.high, spliced.low,
                             spliced.close).iloc[:j]
    pd.testing.assert_series_equal(base, perturbed, check_exact=True)


def test_mutant_is_caught_across_a_sweep_of_perturbation_points():
    """A single fixed J is a weak test here: the pattern fires on roughly 8%
    of bars (measured: 163 of 1,997 settled bars on a 2,000-bar synthetic
    frame, `docs/measure_rd_horseshoe.py`), so a one-bar back-date only
    shows up when a bar adjacent to J happens to be an event -- the same
    low-power problem
    `tests/test_altport2_ports.py` documents for `smc_sweep` (87 of 775 J
    caught the mutant, not 775). The assertion is therefore: the real
    module leaks 0 bars before J at EVERY swept J, and the mutant leaks at
    SOME J, not any particular one."""
    mod = _load_mutant()
    a = _frame(600, seed=1)
    b = _frame(600, seed=2)
    mut_a_full = mod.rd_horseshoe(a.open, a.high, a.low, a.close)
    real_a_full = rd_horseshoe(a.open, a.high, a.low, a.close)

    # live: the mutant differs from the real module on the unperturbed frame
    assert not mut_a_full.equals(real_a_full)

    js = list(range(10, 596, 2))
    real_leaks, mutant_leaks = 0, 0
    for j in js:
        spliced = a.copy()
        spliced.iloc[j:] = b.iloc[j:].to_numpy()
        real_b = rd_horseshoe(spliced.open, spliced.high, spliced.low,
                              spliced.close)
        if not real_a_full.iloc[:j].equals(real_b.iloc[:j]):
            real_leaks += 1

        mut_b = mod.rd_horseshoe(spliced.open, spliced.high, spliced.low,
                                 spliced.close)
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
    base = rd_horseshoe(df.open, df.high, df.low, df.close)
    scaled = rd_horseshoe(df.open * k, df.high * k, df.low * k, df.close * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] == scaled[m]).all()


# ------------------------------------------------------------ reachability
def test_fires_both_signs_and_is_not_constant():
    df = _frame(n=2000, seed=4)
    out = rd_horseshoe(df.open, df.high, df.low, df.close)
    fired = out.dropna()
    assert (fired != 0.0).sum() > 0
    assert (fired != 0.0).sum() < len(fired)
    assert 1.0 in fired.values
    assert -1.0 in fired.values


# ------------------------------------------------------------- edge cases
def test_short_input_returns_none():
    df = _ohlc(_bull_rows()[:3])
    assert rd_horseshoe(df.open, df.high, df.low, df.close) is None


def test_offset():
    rows = _bull_rows() + [(101.0, 102.0, 100.0, 101.5)]
    df = _ohlc(rows)
    out0 = rd_horseshoe(df.open, df.high, df.low, df.close)
    out1 = rd_horseshoe(df.open, df.high, df.low, df.close, offset=1)
    assert out0.iloc[3] == 1.0
    assert pd.isna(out1.iloc[3])
    assert out1.iloc[4] == 1.0


# ---------------------------------------------------------------- wiring
def test_column_name_and_category():
    df = _ohlc(_bull_rows())
    out = rd_horseshoe(df.open, df.high, df.low, df.close)
    assert out.name == "RD_HORSESHOE"
    assert out.category == "candles"


def test_registered_in_category():
    assert "rd_horseshoe" in ta.Category["candles"]


def test_accessor_matches_module_level():
    df = _frame(n=20, seed=9)
    via_module = rd_horseshoe(df["open"], df["high"], df["low"], df["close"])
    via_accessor = df.ta.rd_horseshoe()
    pd.testing.assert_series_equal(via_module, via_accessor, check_exact=True)
