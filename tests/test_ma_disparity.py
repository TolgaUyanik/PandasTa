# tests/test_ma_disparity.py
"""ma_disparity -- % distance between close and its own SMA/EMA (TVPTA-3,
ported from the TradingView community indicator "TY's MA disparity for mean
reversion strategy"). Self-contained on synthetic data, no dependency on the
missing data/SPY_D.csv fixture (same reasoning as test_ichimoku_ml.py).

Reachability tests `import pandas_ta`, NOT `importlib.util.spec_from_file_
location` on the module file -- that is how test_ichimoku_ml.py does it,
which is exactly why ichimoku_ml ships green while being unreachable from
`df.ta` (TVPTA-3(c) in Backtesting/TODO.md). Do not copy that shape.
"""
import numpy as np
import pandas as pd
import pandas.testing as pdt
import pytest

from .context import pandas_ta as ta


def _close(n=300, seed=0):
    rng = np.random.RandomState(seed)
    return pd.Series(
        100 + np.cumsum(rng.randn(n)),
        index=pd.date_range("2020-01-01", periods=n, freq="B"),
    )


def test_columns_present_and_named():
    close = _close()
    out = ta.ma_disparity(close, length=20)
    assert list(out.columns) == ["MADISP_20_SMA", "MADISPSQ_20_SMA"]

    out_ema = ta.ma_disparity(close, length=20, ma_type="ema")
    assert list(out_ema.columns) == ["MADISP_20_EMA", "MADISPSQ_20_EMA"]


def test_correctness_hand_computed():
    # 6 bars, length=3 SMA. SMA at bar i (i>=2) = mean(close[i-2:i+1]).
    close = pd.Series([10.0, 12.0, 11.0, 15.0, 14.0, 20.0])
    out = ta.ma_disparity(close, length=3)

    # bar 2: sma = mean(10,12,11) = 11.0; disparity = (11-11)/11*100 = 0
    assert out["MADISP_3_SMA"].iloc[2] == pytest.approx(0.0)
    # bar 3: sma = mean(12,11,15) = 12.666...; disparity = (15-sma)/sma*100
    sma3 = (12.0 + 11.0 + 15.0) / 3
    expected3 = (15.0 - sma3) / sma3 * 100
    assert out["MADISP_3_SMA"].iloc[3] == pytest.approx(expected3)
    # bar 5: sma = mean(15,14,20) = 16.333...
    sma5 = (15.0 + 14.0 + 20.0) / 3
    expected5 = (20.0 - sma5) / sma5 * 100
    assert out["MADISP_3_SMA"].iloc[5] == pytest.approx(expected5)

    # signed square: same sign as disparity, magnitude = disparity^2
    d3 = out["MADISP_3_SMA"].iloc[3]
    assert out["MADISPSQ_3_SMA"].iloc[3] == pytest.approx(np.sign(d3) * d3 ** 2)


def test_ema_variant_differs_from_sma():
    close = _close()
    out_sma = ta.ma_disparity(close, length=20, ma_type="sma")
    out_ema = ta.ma_disparity(close, length=20, ma_type="ema")
    # EMA and SMA of a random-walk series diverge -- not bit-identical.
    assert not out_sma["MADISP_20_SMA"].iloc[100:].equals(
        out_ema["MADISP_20_EMA"].iloc[100:].rename("MADISP_20_SMA")
    )


def test_no_lookahead():
    close = _close()
    T = 220
    out_full = ta.ma_disparity(close, length=20)

    corrupted = close.copy()
    corrupted.iloc[T + 1:] = corrupted.iloc[T + 1:] + 1000.0
    out_corrupted = ta.ma_disparity(corrupted, length=20)

    pdt.assert_frame_equal(out_full.iloc[:T + 1], out_corrupted.iloc[:T + 1])


def test_reachability_via_accessor():
    close = _close()
    df = pd.DataFrame({
        "open": close, "high": close + 1, "low": close - 1,
        "close": close, "volume": pd.Series(1000.0, index=close.index),
    })

    assert "ma_disparity" in ta.Category["overlap"]
    assert callable(getattr(df.ta, "ma_disparity"))

    module_result = ta.ma_disparity(close=close, length=20)
    accessor_result = df.ta.ma_disparity(length=20)
    pdt.assert_frame_equal(module_result, accessor_result)


def test_bad_ma_type_falls_back_to_sma():
    close = _close()
    out_default = ta.ma_disparity(close, length=20)
    out_garbage = ta.ma_disparity(close, length=20, ma_type="not_a_real_type")
    pdt.assert_frame_equal(out_default, out_garbage)
