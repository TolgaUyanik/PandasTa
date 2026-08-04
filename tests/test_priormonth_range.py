# tests/test_priormonth_range.py
"""priormonth_range -- % distance to the PREVIOUS completed calendar
month's high/mid/low, the monthly-periodicity sibling of `priorday_fib`
(TVPTA-3, ported from "Institution Levels Gath"). Self-contained on
synthetic data.

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
    high = close + rng.rand(n)
    low = close - rng.rand(n)
    return high, low, close


def test_columns_present_and_named():
    high, low, close = _ohlc()
    out = ta.priormonth_range(high, low, close)
    assert list(out.columns) == ["PRIORMONTH_HIGH", "PRIORMONTH_MID", "PRIORMONTH_LOW"]


def test_correctness_hand_computed():
    # January 2020: two bars, monthly high=110 (bar 0), monthly low=90 (bar 1).
    # February 2020: one bar -- must see January's FULLY REALIZED high/low.
    dates = pd.to_datetime(["2020-01-02", "2020-01-03", "2020-02-03"])
    high = pd.Series([105.0, 110.0, 108.0], index=dates)
    low = pd.Series([95.0, 90.0, 100.0], index=dates)
    close = pd.Series([100.0, 92.0, 105.0], index=dates)

    out = ta.priormonth_range(high, low, close)

    # January bars: no prior month at all.
    assert out["PRIORMONTH_HIGH"].iloc[0:2].isna().all()
    assert out["PRIORMONTH_LOW"].iloc[0:2].isna().all()

    # February bar: prior_high=110 (Jan's max, realized across BOTH Jan
    # bars, not just the last one), prior_low=90, prior_mid=100, close=105.
    assert out["PRIORMONTH_HIGH"].iloc[2] == pytest.approx((105.0 - 110.0) / 105.0 * 100)
    assert out["PRIORMONTH_MID"].iloc[2] == pytest.approx((105.0 - 100.0) / 105.0 * 100)
    assert out["PRIORMONTH_LOW"].iloc[2] == pytest.approx((105.0 - 90.0) / 105.0 * 100)


def test_no_lookahead():
    high, low, close = _ohlc()
    T = 60
    out_full = ta.priormonth_range(high, low, close)

    high_c, low_c, close_c = high.copy(), low.copy(), close.copy()
    high_c.iloc[T + 1:] += 1000.0
    low_c.iloc[T + 1:] += 1000.0
    close_c.iloc[T + 1:] += 1000.0
    out_corrupted = ta.priormonth_range(high_c, low_c, close_c)

    pdt.assert_frame_equal(out_full.iloc[:T + 1], out_corrupted.iloc[:T + 1])


def test_reachability_via_accessor():
    high, low, close = _ohlc()
    df = pd.DataFrame({
        "open": close, "high": high, "low": low, "close": close,
        "volume": pd.Series(1000.0, index=close.index),
    })

    assert "priormonth_range" in ta.Category["trend"]
    assert callable(getattr(df.ta, "priormonth_range"))

    module_result = ta.priormonth_range(high=high, low=low, close=close)
    accessor_result = df.ta.priormonth_range()
    pdt.assert_frame_equal(module_result, accessor_result)
