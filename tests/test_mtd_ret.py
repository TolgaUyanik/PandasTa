# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.performance.mtd_ret` -- month-to-date return from the
month's first open. Issue #206; source is tier-4 Reddit crowd talk (module
docstring). Numbers: `docs/MtdRetMeasured.md`. Gate E is owed (CLAUDE.md, "Owed,
not failed").

What these pin, in order of how much it would hurt to lose:

* CAUSALITY: rewrite every bar from `j` onward, bars `[0:j]` bit-identical, at
  30 offsets. The mutant anchors each month on its LAST open instead of its first
  (`exec`'d in memory), the look-ahead this column is one index away from. It is
  proved live, then caught at 26 of 30; the other 4 offsets are months' first
  bars, where no partial month sits behind the cut, so nothing can leak.
* A MISSING FIRST OPEN stays NaN for the month. `transform("first")` would skip
  it and read a later bar, which the clean-open sweep cannot see.
* CORRECTNESS: a hand-derived frame across a month and year boundary, plus an
  independent per-bar loop.
* SCALE-FREE: bit-identical under x8/x64, within 1e-9 under x10/x3.7, matching
  NaN masks, `0 < fires < n` (a fire is a bar above its month's first open).
* A frame without dates returns None rather than crashing a strategy sweep.
* Wiring: `Category`, the accessor, and the column name `MTD_RET`.
"""
import importlib
import types

import numpy as np
import pandas as pd
import pytest

from .context import pandas_ta as ta
from pandas_ta.performance.mtd_ret import mtd_ret


def _frame(n=900, seed=17, sigma=0.015):
    rng = np.random.default_rng(seed)
    close = 100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n)))
    idx = pd.date_range("2022-01-03", periods=n, freq="B")
    open_ = pd.Series(close, index=idx).shift(1) * np.exp(rng.normal(0.0, 0.005, n))
    open_.iloc[0] = 100.0
    return open_, pd.Series(close, index=idx)


# ------------------------------------------------------------ correctness


def test_hand_derived_across_a_month_and_year_boundary():
    """Dec anchors on 100 and Jan on 200, a different year's January on 50.
    Derived by hand, not by re-running the module."""
    idx = pd.to_datetime(["2023-12-28", "2023-12-29", "2024-01-02", "2024-01-03", "2025-01-02"])
    open_ = pd.Series([100.0, 999.0, 200.0, 999.0, 50.0], index=idx)
    close = pd.Series([110.0, 90.0, 220.0, 100.0, 75.0], index=idx)
    out = mtd_ret(open_, close)
    assert out.tolist() == pytest.approx([0.10, -0.10, 0.10, -0.50, 0.50], abs=1e-12)


def test_matches_an_independent_per_bar_loop():
    open_, close = _frame()
    out = mtd_ret(open_, close)
    anchor, month = None, None
    for t, stamp in enumerate(close.index):
        if (stamp.year, stamp.month) != month:
            month, anchor = (stamp.year, stamp.month), open_.iloc[t]
        assert out.iloc[t] == close.iloc[t] / anchor - 1


def test_same_month_in_another_year_does_not_reuse_the_anchor():
    idx = pd.to_datetime(["2023-03-01", "2024-03-01"])
    out = mtd_ret(pd.Series([100.0, 50.0], index=idx), pd.Series([100.0, 50.0], index=idx))
    assert out.tolist() == [0.0, 0.0]


def test_tz_aware_index_resets_on_local_time():
    idx = pd.to_datetime(["2024-01-31 12:00", "2024-02-01 00:30"]).tz_localize("Europe/Istanbul")
    # In UTC both bars are in January; locally the second opens February.
    out = mtd_ret(pd.Series([100.0, 50.0], index=idx), pd.Series([100.0, 50.0], index=idx))
    assert out.tolist() == [0.0, 0.0]


def test_missing_first_open_blanks_the_month_and_not_the_next():
    idx = pd.to_datetime(["2024-01-02", "2024-01-03", "2024-02-01"])
    open_ = pd.Series([np.nan, 200.0, 50.0], index=idx)
    close = pd.Series([100.0, 100.0, 100.0], index=idx)
    out = mtd_ret(open_, close)
    assert out.iloc[:2].isna().all()
    assert out.iloc[2] == 1.0


def test_no_datetime_index_returns_none_and_accessor_leaves_frame_alone():
    open_, close = _frame()
    open_, close = open_.reset_index(drop=True), close.reset_index(drop=True)
    assert mtd_ret(open_, close) is None
    df = pd.DataFrame({"open": open_, "close": close})
    assert isinstance(df.ta.mtd_ret(), pd.DataFrame)
    assert list(df.columns) == ["open", "close"]


def test_offset_shifts_the_series():
    open_, close = _frame()
    pd.testing.assert_series_equal(
        mtd_ret(open_, close, offset=1), mtd_ret(open_, close).shift(1), check_names=False)


def test_fillna_fills_a_blanked_month():
    idx = pd.to_datetime(["2024-01-02", "2024-02-01"])
    out = mtd_ret(pd.Series([np.nan, 50.0], index=idx), pd.Series([100.0, 100.0], index=idx), fillna=0)
    assert out.tolist() == [0.0, 1.0]


# -------------------------------------------------------------- causality


_REAL = importlib.import_module("pandas_ta.performance.mtd_ret")


def _load_mutant():
    src = open(_REAL.__file__, encoding="utf-8").read()
    old = "s.iloc[0]"
    assert src.count(old) == 1, "mutation target not unique"
    mod = types.ModuleType("_mtd_ret_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, "s.iloc[-1]"), _REAL.__file__, "exec"), mod.__dict__)
    return mod


OFFSETS = range(100, 850, 25)  # 30 offsets; 4 of them fall on a month's first bar


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
    assert _leaks(mtd_ret) == 0


def test_mutant_is_caught():
    mod = _load_mutant()
    open_, close = _frame()
    assert not mod.mtd_ret(open_, close).equals(mtd_ret(open_, close))  # live
    # Offset j on a month's first bar has no partial month behind it, so it cannot leak.
    month_starts = {j for j in OFFSETS if close.index[j].month != close.index[j - 1].month}
    assert _leaks(mod.mtd_ret) == len(OFFSETS) - len(month_starts)
    assert _leaks(mod.mtd_ret) > 0


# ------------------------------------------------------------ scale-free


@pytest.mark.parametrize("k", [8.0, 64.0])
def test_power_of_two_price_scale_is_bit_identical(k):
    open_, close = _frame()
    base, scaled = mtd_ret(open_, close), mtd_ret(open_ * k, close * k)
    assert (base.isna() == scaled.isna()).all()
    assert (base == scaled).all()


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_other_scales_within_tolerance(k):
    open_, close = _frame()
    base, scaled = mtd_ret(open_, close), mtd_ret(open_ * k, close * k)
    assert (base.isna() == scaled.isna()).all()
    assert (base - scaled).abs().max() < 1e-9


def test_fires_and_is_not_constant():
    out = mtd_ret(*_frame())
    fires = int((out > 0).sum())
    assert 0 < fires < len(out)
    assert out.nunique() > 100


# ---------------------------------------------------------------- wiring


def test_name_registration_and_accessor():
    open_, close = _frame()
    df = pd.DataFrame({"open": open_, "high": close, "low": close, "close": close, "volume": close})
    assert "mtd_ret" in ta.Category["performance"]
    out = df.ta.mtd_ret()
    assert out.name == "MTD_RET"
    pd.testing.assert_series_equal(out, mtd_ret(open_, close), check_freq=False)
