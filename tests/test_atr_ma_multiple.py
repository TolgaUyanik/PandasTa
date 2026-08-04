# tests/test_atr_ma_multiple.py
"""atr_ma_multiple -- volatility-adjusted distance-to-MA (TVPTA-3, ported
from "ATR% Multiple from 50-MA"). Self-contained on synthetic data.

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


def test_name_and_series():
    high, low, close = _ohlc()
    out = ta.atr_ma_multiple(high, low, close)
    assert isinstance(out, pd.Series)
    assert out.name == "ATRMAX_14_50"


def test_correctness_independent_recompute():
    # NOTE (Fletcher round 1, TVPTA-3-volatility): this recomputes via the
    # SAME ta.atr/ta.sma primitives the module itself calls -- it can only
    # catch a wiring/transcription slip, not a conceptual error (wrong
    # sign, swapped numerator/denominator). See
    # test_correctness_hand_computed below for that.
    high, low, close = _ohlc(n=80)
    out = ta.atr_ma_multiple(high, low, close, atr_length=5, ma_length=10)

    atr_series = ta.atr(high, low, close, length=5)
    ma = ta.sma(close, length=10)
    atr_pct = atr_series / close * 100
    pct_gain_ma = (close - ma) / ma * 100
    expected = pct_gain_ma / atr_pct

    pdt.assert_series_equal(out, expected, check_names=False)


def test_correctness_hand_computed():
    # atr_length=1 makes ATR degenerate to True Range itself (RMA with
    # alpha=1/1=1.0 has no memory), which IS hand-computable without
    # simulating Wilder's recursive smoothing.
    close = pd.Series([10.0, 11.0, 9.0, 12.0])
    high = close + 1.0
    low = close - 1.0

    out = ta.atr_ma_multiple(high, low, close, atr_length=1, ma_length=3)

    # bar0, bar1: SMA(3) needs 3 closes -> NaN
    assert out.iloc[0:2].isna().all()

    # bar2: TR = max(|10-8|, |10-11|, |11-8|) = max(2,1,3) = 3 -> ATR(1)=3
    #       ma = mean(10,11,9) = 10.0 -> pct_gain_ma = (9-10)/10*100 = -10.0
    #       atr_pct = 3/9*100 = 33.333... -> ATRMAX = -10.0 / (100/3) = -0.3
    assert out.iloc[2] == pytest.approx(-0.3)

    # bar3: TR = max(|13-11|, |13-9|, |9-11|) = max(2,4,2) = 4 -> ATR(1)=4
    #       ma = mean(11,9,12) = 32/3 -> pct_gain_ma = (4/3)/(32/3)*100 = 12.5
    #       atr_pct = 4/12*100 = 33.333... -> ATRMAX = 12.5 / (100/3) = 0.375
    assert out.iloc[3] == pytest.approx(0.375)


def test_no_lookahead():
    high, low, close = _ohlc()
    T = 60
    out_full = ta.atr_ma_multiple(high, low, close)

    high_c, low_c, close_c = high.copy(), low.copy(), close.copy()
    high_c.iloc[T + 1:] += 1000.0
    low_c.iloc[T + 1:] += 1000.0
    close_c.iloc[T + 1:] += 1000.0
    out_corrupted = ta.atr_ma_multiple(high_c, low_c, close_c)

    pdt.assert_series_equal(out_full.iloc[:T + 1], out_corrupted.iloc[:T + 1])


def test_reachability_via_accessor():
    high, low, close = _ohlc()
    df = pd.DataFrame({
        "open": close, "high": high, "low": low, "close": close,
        "volume": pd.Series(1000.0, index=close.index),
    })

    assert "atr_ma_multiple" in ta.Category["volatility"]
    assert callable(getattr(df.ta, "atr_ma_multiple"))

    module_result = ta.atr_ma_multiple(high=high, low=low, close=close)
    accessor_result = df.ta.atr_ma_multiple()
    pdt.assert_series_equal(module_result, accessor_result)
