# tests/test_rsi_divergence.py
"""rsi_divergence -- classic price/RSI pivot divergence detector
(TVPTA-3-composite, ported from "RSI Divergence Engine v3 [30-40 Bar
Window]"). Self-contained on synthetic data.

Reachability tests `import pandas_ta`, NOT `importlib.util.spec_from_file_
location` (see TODO.md TVPTA-3(c)).
"""
import numpy as np
import pandas as pd
import pandas.testing as pdt
import pytest

from .context import pandas_ta as ta


def _ohlc(n=200, seed=0):
    rng = np.random.RandomState(seed)
    close = pd.Series(
        100 + np.cumsum(rng.randn(n)),
        index=pd.date_range("2020-01-01", periods=n, freq="B"),
    )
    high = close + rng.rand(n) + 0.2
    low = close - rng.rand(n) - 0.2
    return high, low, close


def test_columns_present_and_named():
    high, low, close = _ohlc()
    out = ta.rsi_divergence(high, low, close, rsi_length=14, pivot_left=4, pivot_right=4)
    assert list(out.columns) == ["RSIDIV_BULL_14_4_4", "RSIDIV_BEAR_14_4_4"]


def test_correctness_hand_computed_bullish():
    # Two pivot lows (left=right=1): bar3 (price 93, pure decline into it
    # -> RSI(3)=0.0 exactly, no gains anywhere in its lookback) and bar9
    # (price 91, a LOWER low than bar3's 93) -- but bar9's RSI lookback
    # contains an up-spike at bar7 (100->102), so RSI at bar9 reads > 0
    # despite the lower price. Lower low + higher RSI = bullish
    # divergence, confirmed at bar10 (pivot_right=1 lag). The up-spike is
    # placed 2 bars before the low specifically so it does NOT itself
    # become a spurious pivot (it sits ABOVE its neighbors, not below).
    close = pd.Series([
        100.0, 100.0, 100.0,   # 0,1,2
        93.0,                   # 3: pivot A (confirms at bar4)
        100.0, 100.0, 100.0,    # 4,5,6
        102.0,                  # 7: up-spike, feeds a gain into pivot B's RSI window
        98.0,                   # 8
        91.0,                   # 9: pivot B, lower low than A (confirms at bar10)
        100.0, 100.0,           # 10,11
    ])
    high = close + 0.1
    low = close - 0.1

    out = ta.rsi_divergence(high, low, close, rsi_length=3, pivot_left=1, pivot_right=1,
                             min_lookback=2, max_lookback=20, rsi_oversold=90.0)

    # Independently confirm the RSI condition this fixture relies on,
    # using the package's own (separately-tested) `rsi()`, not a
    # hardcoded number -- pivot A's RSI must be exactly 0 (a pure
    # decline has zero gains) and pivot B's must be strictly higher.
    rsi_val = ta.rsi(close, length=3)
    assert rsi_val.iloc[3] == pytest.approx(0.0)
    assert rsi_val.iloc[9] > rsi_val.iloc[3]
    assert close.iloc[9] < close.iloc[3]

    assert out["RSIDIV_BULL_3_1_1"].tolist() == [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0]
    assert out["RSIDIV_BEAR_3_1_1"].sum() == 0


def test_no_lookahead():
    high, low, close = _ohlc()
    T = 120
    out_full = ta.rsi_divergence(high, low, close)

    high_c, low_c, close_c = high.copy(), low.copy(), close.copy()
    high_c.iloc[T + 1:] += 1000.0
    low_c.iloc[T + 1:] += 1000.0
    close_c.iloc[T + 1:] += 1000.0
    out_corrupted = ta.rsi_divergence(high_c, low_c, close_c)

    pdt.assert_frame_equal(out_full.iloc[:T + 1], out_corrupted.iloc[:T + 1])


def test_reachability_via_accessor():
    high, low, close = _ohlc()
    df = pd.DataFrame({
        "open": close, "high": high, "low": low, "close": close,
        "volume": pd.Series(1000.0, index=close.index),
    })

    assert "rsi_divergence" in ta.Category["momentum"]
    assert callable(getattr(df.ta, "rsi_divergence"))

    module_result = ta.rsi_divergence(high=high, low=low, close=close)
    accessor_result = df.ta.rsi_divergence()
    pdt.assert_frame_equal(module_result, accessor_result)
