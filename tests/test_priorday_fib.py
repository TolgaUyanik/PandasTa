# tests/test_priorday_fib.py
"""priorday_fib -- % distance to the prior bar's high/mid/low, the
daily-bar reformulation of "Fib Zone Lines"' prior-session Fibonacci zone
tool (TVPTA-3). Self-contained on synthetic data.

Reachability tests `import pandas_ta`, NOT `importlib.util.spec_from_file_
location` (see TODO.md TVPTA-3(c)).
"""
import numpy as np
import pandas as pd
import pandas.testing as pdt
import pytest

from .context import pandas_ta as ta


def _ohlc(n=100, seed=0):
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
    out = ta.priorday_fib(high, low, close)
    assert list(out.columns) == ["PDFIB_HIGH", "PDFIB_MID", "PDFIB_LOW"]


def test_correctness_hand_computed():
    high = pd.Series([100.0, 110.0, 90.0, 105.0])
    low = pd.Series([95.0, 100.0, 80.0, 95.0])
    close = pd.Series([98.0, 105.0, 85.0, 100.0])

    out = ta.priorday_fib(high, low, close)

    assert out["PDFIB_HIGH"].iloc[0:1].isna().all()  # no prior bar yet

    # bar 1: prior_high=100, prior_low=95, prior_mid=97.5, close=105
    assert out["PDFIB_HIGH"].iloc[1] == pytest.approx((105.0 - 100.0) / 105.0 * 100)
    assert out["PDFIB_MID"].iloc[1] == pytest.approx((105.0 - 97.5) / 105.0 * 100)
    assert out["PDFIB_LOW"].iloc[1] == pytest.approx((105.0 - 95.0) / 105.0 * 100)

    # bar 2: prior_high=110, prior_low=100, prior_mid=105, close=85
    assert out["PDFIB_MID"].iloc[2] == pytest.approx((85.0 - 105.0) / 85.0 * 100)


def test_no_lookahead():
    high, low, close = _ohlc()
    T = 60
    out_full = ta.priorday_fib(high, low, close)

    high_c, low_c, close_c = high.copy(), low.copy(), close.copy()
    high_c.iloc[T + 1:] += 1000.0
    low_c.iloc[T + 1:] += 1000.0
    close_c.iloc[T + 1:] += 1000.0
    out_corrupted = ta.priorday_fib(high_c, low_c, close_c)

    pdt.assert_frame_equal(out_full.iloc[:T + 1], out_corrupted.iloc[:T + 1])


def test_reachability_via_accessor():
    high, low, close = _ohlc()
    df = pd.DataFrame({
        "open": close, "high": high, "low": low, "close": close,
        "volume": pd.Series(1000.0, index=close.index),
    })

    assert "priorday_fib" in ta.Category["trend"]
    assert callable(getattr(df.ta, "priorday_fib"))

    module_result = ta.priorday_fib(high=high, low=low, close=close)
    accessor_result = df.ta.priorday_fib()
    pdt.assert_frame_equal(module_result, accessor_result)
