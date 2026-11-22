# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.performance.qtd_ret` -- quarter-to-date return from
the quarter's first open. Issue #205; source is tier-4 Reddit crowd talk
(module docstring), the same thread as `mtd_ret` (issue #206,
`docs/MtdRetMeasured.md`) with the anchoring period changed from calendar
month to calendar quarter. Numbers: `docs/QtdRetMeasured.md`. Gate E: pending,
run by issue-solver after this session.

What these pin, in order of how much it would hurt to lose (mirrors
`tests/test_mtd_ret.py`, with "month" replaced by "quarter" throughout; every
leak/offset count below is computed in-test from the fixture, not typed by
hand, so it cannot drift from the code it is checking; the numbers in this
docstring are `python docs/measure_qtd_ret.py`'s output on the same fixture,
quoted for a reader, not re-derived by the assertions):

* CAUSALITY: rewrite every bar from `j` onward, bars `[0:j]` bit-identical, at
  all 899 offsets. Two mutants (`exec`'d in memory), each proved live:
  anchoring on the quarter's LAST open leaks at 886 of 899 (the other 13
  offsets are quarters' first bars, where no partial quarter sits behind the
  cut), and anchoring ONE BAR LATE leaks at 14 of 899, exactly the quarters'
  second bars.
* AN UNSORTED FRAME returns None. "First row" is the earliest bar only on an
  ascending index; reversed, a bar read a later bar's open.
* A MISSING FIRST OPEN stays NaN for the quarter. `transform("first")` would
  skip it and read a later bar, which the clean-open sweep cannot see. A ZERO
  first open is NaN too, not an `inf` that `fillna` cannot clear.
* CORRECTNESS: a hand-derived frame across a quarter and year boundary, plus
  an independent per-bar loop.
* SCALE-FREE: bit-identical under x8/x64, within 1e-9 under x10/x3.7, on a
  frame with one quarter blanked so the NaN masks have something to match,
  and `0 < fires < n` (a fire is a bar above its quarter's first open).
* A frame without dates returns None, and a real strategy sweep skips the
  column rather than crashing. Mismatched open/close indexes return None too.
* Wiring: `Category`, the accessor, and the column name `QTD_RET`.
"""
import importlib
import types

import numpy as np
import pandas as pd
import pytest

from .context import pandas_ta as ta
from pandas_ta.performance.qtd_ret import qtd_ret


def _frame(n=900, seed=17, sigma=0.015):
    rng = np.random.default_rng(seed)
    close = 100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n)))
    idx = pd.date_range("2022-01-03", periods=n, freq="B")
    open_ = pd.Series(close, index=idx).shift(1) * np.exp(rng.normal(0.0, 0.005, n))
    open_.iloc[0] = 100.0
    return open_, pd.Series(close, index=idx)


def _quarter_of(index):
    return index.year * 4 + index.quarter


# ------------------------------------------------------------ correctness


def test_hand_derived_across_a_quarter_and_year_boundary():
    """Q3 2023 anchors on 100, Q4 2023 on 200, Q1 2024 on 50. Derived by hand,
    not by re-running the module. Spans a quarter boundary that is not a year
    boundary (Sep -> Oct) and one that is both (Dec -> Jan)."""
    idx = pd.to_datetime(["2023-09-28", "2023-09-29", "2023-10-02", "2023-10-03", "2024-01-02"])
    open_ = pd.Series([100.0, 999.0, 200.0, 999.0, 50.0], index=idx)
    close = pd.Series([110.0, 90.0, 220.0, 100.0, 75.0], index=idx)
    out = qtd_ret(open_, close)
    assert out.tolist() == pytest.approx([0.10, -0.10, 0.10, -0.50, 0.50], abs=1e-12)


def test_matches_an_independent_per_bar_loop():
    open_, close = _frame()
    out = qtd_ret(open_, close)
    anchor, quarter = None, None
    for t, stamp in enumerate(close.index):
        key = (stamp.year, stamp.quarter)
        if key != quarter:
            quarter, anchor = key, open_.iloc[t]
        assert out.iloc[t] == close.iloc[t] / anchor - 1


def test_same_quarter_in_another_year_does_not_reuse_the_anchor():
    idx = pd.to_datetime(["2023-02-01", "2024-02-01"])
    out = qtd_ret(pd.Series([100.0, 50.0], index=idx), pd.Series([100.0, 50.0], index=idx))
    assert out.tolist() == [0.0, 0.0]


def test_tz_aware_index_resets_on_local_time():
    idx = pd.to_datetime(["2024-03-31 12:00", "2024-04-01 00:30"]).tz_localize("Europe/Istanbul")
    # In UTC both bars are in Q1 (31 Mar 09:00 and 21:30 UTC); locally the
    # second opens Q2 (1 Apr 00:30 Istanbul, UTC+3 year-round, no DST).
    out = qtd_ret(pd.Series([100.0, 50.0], index=idx), pd.Series([100.0, 50.0], index=idx))
    assert out.tolist() == [0.0, 0.0]


def test_missing_first_open_blanks_the_quarter_and_not_the_next():
    idx = pd.to_datetime(["2024-01-02", "2024-01-03", "2024-04-01"])
    open_ = pd.Series([np.nan, 200.0, 50.0], index=idx)
    close = pd.Series([100.0, 100.0, 100.0], index=idx)
    out = qtd_ret(open_, close)
    assert out.iloc[:2].isna().all()
    assert out.iloc[2] == 1.0


def test_zero_first_open_blanks_the_quarter_and_not_the_next():
    idx = pd.to_datetime(["2024-01-02", "2024-01-03", "2024-04-01"])
    out = qtd_ret(pd.Series([0.0, 200.0, 50.0], index=idx), pd.Series([100.0] * 3, index=idx))
    assert out.iloc[:2].isna().all()
    assert out.iloc[2] == 1.0


@pytest.mark.parametrize("order", [[1, 0, 2, 3], [3, 2, 1, 0]], ids=["swap", "reversed"])
def test_unsorted_index_returns_none(order):
    idx = pd.to_datetime(["2024-01-31", "2024-02-01", "2024-02-02", "2024-02-05"])
    s = pd.Series([100.0, 200.0, 210.0, 220.0], index=idx).iloc[order]
    assert qtd_ret(s, s) is None


def test_nat_in_index_returns_none():
    idx = pd.to_datetime(["2024-01-31", None, "2024-02-01"])
    s = pd.Series([100.0, 200.0, 210.0], index=idx)
    assert qtd_ret(s, s) is None


@pytest.mark.parametrize("break_close", [
    lambda c: c.reset_index(drop=True),
    lambda c: c.set_axis(c.index + pd.Timedelta(hours=1)),
    lambda c: c.iloc[:-1],
], ids=["range_index", "shifted_labels", "shorter"])
def test_close_index_differing_from_open_returns_none(break_close):
    open_, close = _frame(50)
    assert qtd_ret(open_, break_close(close)) is None


def test_no_datetime_index_returns_none_and_a_strategy_sweep_skips_it():
    open_, close = _frame()
    sweep = ta.Strategy(name="qtd", ta=[{"kind": "qtd_ret"}])

    dated = pd.DataFrame({"open": open_, "high": close, "low": close, "close": close, "volume": close})
    dated.ta.strategy(sweep, cores=0, verbose=False)
    assert "QTD_RET" in dated.columns

    open_, close = open_.reset_index(drop=True), close.reset_index(drop=True)
    assert qtd_ret(open_, close) is None
    undated = pd.DataFrame({"open": open_, "high": close, "low": close, "close": close, "volume": close})
    assert isinstance(undated.ta.qtd_ret(), pd.DataFrame)
    undated.ta.strategy(sweep, cores=0, verbose=False)
    assert "QTD_RET" not in undated.columns


def test_offset_shifts_the_series():
    open_, close = _frame()
    pd.testing.assert_series_equal(
        qtd_ret(open_, close, offset=1), qtd_ret(open_, close).shift(1), check_names=False)


def test_fillna_fills_a_blanked_quarter():
    idx = pd.to_datetime(["2024-01-02", "2024-04-01"])
    out = qtd_ret(pd.Series([np.nan, 50.0], index=idx), pd.Series([100.0, 100.0], index=idx), fillna=0)
    assert out.tolist() == [0.0, 1.0]


# -------------------------------------------------------------- causality


_REAL = importlib.import_module("pandas_ta.performance.qtd_ret")


LAST_OPEN = "s.iloc[-1]"
ONE_BAR_LATE = "s.iloc[min(1, len(s) - 1)]"


def _load_mutant(new=LAST_OPEN):
    src = open(_REAL.__file__, encoding="utf-8").read()
    old = "s.iloc[0]"
    assert src.count(old) == 1, "mutation target not unique"
    mod = types.ModuleType("_qtd_ret_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


OFFSETS = range(1, 900)  # every cut: a one-bar-late anchor leaks only on a quarter's second bar


def _leaks(fn):
    open_, close = _frame()
    other_open, other_close = _frame(seed=99)
    base = fn(open_, close)
    hits = 0
    for j in OFFSETS:
        po, pc = open_.copy(), close.copy()
        po.iloc[j:] = other_open.iloc[j:].values
        pc.iloc[j:] = other_close.iloc[j:].values
        a, b = base.iloc[:j], fn(po, pc).iloc[:j]
        if not (a.isna() == b.isna()).all() or (a[a.notna()] != b[a.notna()]).any():
            hits += 1
    return hits


def test_real_module_never_reads_the_future():
    assert _leaks(qtd_ret) == 0


def test_last_open_mutant_is_caught():
    mod = _load_mutant(LAST_OPEN)
    open_, close = _frame()
    assert not mod.qtd_ret(open_, close).equals(qtd_ret(open_, close))  # live
    # Offset j on a quarter's first bar has no partial quarter behind it, so it cannot leak.
    quarters = _quarter_of(close.index)
    quarter_starts = sum(quarters[j] != quarters[j - 1] for j in OFFSETS)
    assert quarter_starts > 0
    assert _leaks(mod.qtd_ret) == len(OFFSETS) - quarter_starts


def test_one_bar_late_mutant_is_caught():
    mod = _load_mutant(ONE_BAR_LATE)
    open_, close = _frame()
    assert not mod.qtd_ret(open_, close).equals(qtd_ret(open_, close))  # live
    # Only a cut on a quarter's second bar rewrites that anchor while its first bar stays behind the cut.
    quarters = _quarter_of(close.index)
    second_bars = sum(j >= 1 and quarters[j] == quarters[j - 1] and (j == 1 or quarters[j - 1] != quarters[j - 2])
                      for j in OFFSETS)
    assert second_bars > 0
    assert _leaks(mod.qtd_ret) == second_bars


# ------------------------------------------------------------ scale-free


BLANK_QUARTER_START = "2022-04-01"  # Q2 2022, inside the 900-business-day frame starting 2022-01-03


def _frame_with_a_blank_quarter():
    open_, close = _frame()
    open_.loc[open_.index[open_.index >= BLANK_QUARTER_START][0]] = np.nan
    return open_, close


@pytest.mark.parametrize("k", [8.0, 64.0])
def test_power_of_two_price_scale_is_bit_identical(k):
    open_, close = _frame_with_a_blank_quarter()
    base, scaled = qtd_ret(open_, close), qtd_ret(open_ * k, close * k)
    assert base.isna().sum() > 0
    pd.testing.assert_series_equal(base, scaled, check_exact=True)


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_other_scales_within_tolerance(k):
    open_, close = _frame_with_a_blank_quarter()
    base, scaled = qtd_ret(open_, close), qtd_ret(open_ * k, close * k)
    assert base.isna().sum() > 0
    assert (base.isna() == scaled.isna()).all()
    assert (base - scaled).abs().max() < 1e-9


def test_fires_and_is_not_constant():
    out = qtd_ret(*_frame())
    fires = int((out > 0).sum())
    assert 0 < fires < len(out)
    assert out.nunique() > 100


# ---------------------------------------------------------------- wiring


def test_name_registration_and_accessor():
    open_, close = _frame()
    df = pd.DataFrame({"open": open_, "high": close, "low": close, "close": close, "volume": close})
    assert "qtd_ret" in ta.Category["performance"]
    out = df.ta.qtd_ret()
    assert out.name == "QTD_RET"
    pd.testing.assert_series_equal(out, qtd_ret(open_, close), check_freq=False)
