# tests/test_renko_trend.py
"""renko_trend -- synthetic Renko brick tracker (TVPTA-3-composite, ported
from "Smart Renko Engine"). Self-contained on synthetic data.

Reachability tests `import pandas_ta`, NOT `importlib.util.spec_from_file_
location` (see TODO.md TVPTA-3(c)).
"""
import numpy as np
import pandas as pd
import pandas.testing as pdt
import pytest

from .context import pandas_ta as ta


def _close(n=100, seed=0):
    rng = np.random.RandomState(seed)
    return pd.Series(
        100 + np.cumsum(rng.randn(n)),
        index=pd.date_range("2020-01-01", periods=n, freq="B"),
    )


def test_columns_present_and_named():
    close = _close()
    out = ta.renko_trend(close, brick_fixed=2.0)
    assert list(out.columns) == ["RENKO_TREND_F2.0", "RENKO_DIST_F2.0"]


def test_correctness_hand_computed():
    # box=2.0 (fixed). Traced by hand against the source's while-loop:
    #   bar0: close=10, seed rClose=10, trend=1 (source's initial state)
    #   bar1: close=13, prevclose=10 -> box[8,12] broken above (13>=12)
    #         -> rClose=12, still <13 so loop again -> 12+2=14>13 stop
    #         (only ONE brick step since 13<14) -> rClose=12, trend=1
    #   bar2: close=17, prevclose=12 -> box[10,14] -> 17>=14 -> rClose=14
    #         -> loop again: 14+2=16<=17 -> rClose=16 -> loop again:
    #         16+2=18>17 stop -> rClose=16, trend=1 (TWO brick steps in
    #         one bar, exercising the multi-iteration while loop)
    #   bar3: close=13, prevclose=16 -> box[14,18] -> 13<=14 -> flip:
    #         trend=-1, rClose=14 -> loop again (trend=-1 now):
    #         13<=14-2=12? no. 13>=14+2=16? no -> stop -> rClose=14, trend=-1
    close = pd.Series([10.0, 13.0, 17.0, 13.0])
    out = ta.renko_trend(close, brick_fixed=2.0)

    assert out["RENKO_TREND_F2.0"].tolist() == [1, 1, 1, -1]
    expected_dist = [
        (10.0 - 10.0) / 10.0 * 100,
        (13.0 - 12.0) / 13.0 * 100,
        (17.0 - 16.0) / 17.0 * 100,
        (13.0 - 14.0) / 13.0 * 100,
    ]
    assert out["RENKO_DIST_F2.0"].tolist() == pytest.approx(expected_dist)


def test_no_lookahead():
    close = _close()
    T = 60
    out_full = ta.renko_trend(close, brick_pct=1.0)

    close_c = close.copy()
    close_c.iloc[T + 1:] += 1000.0
    out_corrupted = ta.renko_trend(close_c, brick_pct=1.0)

    pdt.assert_frame_equal(out_full.iloc[:T + 1], out_corrupted.iloc[:T + 1])


def test_reachability_via_accessor():
    close = _close()
    df = pd.DataFrame({
        "open": close, "high": close + 1, "low": close - 1, "close": close,
        "volume": pd.Series(1000.0, index=close.index),
    })

    assert "renko_trend" in ta.Category["trend"]
    assert callable(getattr(df.ta, "renko_trend"))

    module_result = ta.renko_trend(close=close)
    accessor_result = df.ta.renko_trend()
    pdt.assert_frame_equal(module_result, accessor_result)
