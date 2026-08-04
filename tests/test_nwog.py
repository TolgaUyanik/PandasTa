# tests/test_nwog.py
"""nwog -- % distance to the New Week Opening Gap (top = max(open,
prior week's close), bottom = min(...)), held through the week (TVPTA-3,
ported from "Key Opens & Session Tracker + Highs/Lows & NWOG"). Self-
contained on synthetic data.

Reachability tests `import pandas_ta`, NOT `importlib.util.spec_from_file_
location` (see TODO.md TVPTA-3(c)).
"""
import numpy as np
import pandas as pd
import pandas.testing as pdt
import pytest

from .context import pandas_ta as ta


def _ohlc(n=150, seed=0):
    rng = np.random.RandomState(seed)
    close = pd.Series(
        100 + np.cumsum(rng.randn(n)),
        index=pd.date_range("2020-01-01", periods=n, freq="B"),
    )
    open_ = close.shift(1).fillna(close.iloc[0]) + rng.randn(n) * 0.1
    return open_, close


def test_columns_present_and_named():
    open_, close = _ohlc()
    out = ta.nwog(open_, close)
    assert list(out.columns) == ["NWOG_TOP", "NWOG_BOTTOM"]


def test_correctness_hand_computed():
    # Fri 2020-01-10 (last bar of one week) -> Mon 2020-01-13 / Tue
    # 2020-01-14 (first two bars of the next week). The gap forms on the
    # Monday bar (open vs Friday's close) and holds through Tuesday.
    dates = pd.to_datetime(["2020-01-10", "2020-01-13", "2020-01-14"])
    open_ = pd.Series([99.0, 105.0, 108.0], index=dates)
    close = pd.Series([100.0, 108.0, 110.0], index=dates)

    out = ta.nwog(open_, close)

    # First bar overall: no prior-week close to gap against.
    assert out["NWOG_TOP"].iloc[0:1].isna().all()
    assert out["NWOG_BOTTOM"].iloc[0:1].isna().all()

    # Monday: gap_top=max(105,100)=105, gap_bottom=min(105,100)=100
    assert out["NWOG_TOP"].iloc[1] == pytest.approx((108.0 - 105.0) / 108.0 * 100)
    assert out["NWOG_BOTTOM"].iloc[1] == pytest.approx((108.0 - 100.0) / 108.0 * 100)

    # Tuesday: same week -> gap held constant from Monday
    assert out["NWOG_TOP"].iloc[2] == pytest.approx((110.0 - 105.0) / 110.0 * 100)
    assert out["NWOG_BOTTOM"].iloc[2] == pytest.approx((110.0 - 100.0) / 110.0 * 100)


def test_week_anchor_is_sunday_ending():
    # MINOR regression (Fletcher round 1): the module pins `to_period(
    # "W-SUN")` explicitly rather than relying on pandas' default. This
    # locks that choice in -- a Sunday bar belongs to the week ENDING that
    # Sunday (same week as the preceding Mon-Fri), not a new week starting
    # on it. If the anchor were ever silently changed, a bar landing on
    # Sunday would flip which week it's grouped with, which a plain
    # business-day fixture (no weekend bars) can never exercise.
    dates = pd.to_datetime(["2020-01-10", "2020-01-12", "2020-01-13"])  # Fri, Sun, Mon
    open_ = pd.Series([99.0, 100.0, 105.0], index=dates)
    close = pd.Series([100.0, 100.0, 108.0], index=dates)

    out = ta.nwog(open_, close)

    # Sunday is still inside the Fri's week (W-SUN) -> no new gap forms.
    assert out["NWOG_TOP"].iloc[1:2].isna().all()
    assert out["NWOG_BOTTOM"].iloc[1:2].isna().all()

    # Monday starts a genuinely new week -> gap forms against Sunday's close.
    assert out["NWOG_TOP"].iloc[2] == pytest.approx((108.0 - 105.0) / 108.0 * 100)
    assert out["NWOG_BOTTOM"].iloc[2] == pytest.approx((108.0 - 100.0) / 108.0 * 100)


def test_no_lookahead():
    open_, close = _ohlc()
    T = 60
    out_full = ta.nwog(open_, close)

    open_c, close_c = open_.copy(), close.copy()
    open_c.iloc[T + 1:] += 1000.0
    close_c.iloc[T + 1:] += 1000.0
    out_corrupted = ta.nwog(open_c, close_c)

    pdt.assert_frame_equal(out_full.iloc[:T + 1], out_corrupted.iloc[:T + 1])


def test_reachability_via_accessor():
    open_, close = _ohlc()
    df = pd.DataFrame({
        "open": open_, "high": close + 1, "low": close - 1, "close": close,
        "volume": pd.Series(1000.0, index=close.index),
    })

    assert "nwog" in ta.Category["trend"]
    assert callable(getattr(df.ta, "nwog"))

    module_result = ta.nwog(open_=open_, close=close)
    accessor_result = df.ta.nwog()
    pdt.assert_frame_equal(module_result, accessor_result)
