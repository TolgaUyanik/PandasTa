# tests/test_band_cross_retest.py
"""band_cross_retest -- impulse-qualified band-cross retest state machine
(TVPTA-3-composite, ported from "HTS - Wstęgi PRO 4 Alerty [v7]"). Self-
contained on synthetic data.

Reachability tests `import pandas_ta`, NOT `importlib.util.spec_from_file_
location` (see TODO.md TVPTA-3(c)).
"""
import numpy as np
import pandas as pd
import pandas.testing as pdt
import pytest

from .context import pandas_ta as ta


def _ohlc(n=400, seed=0):
    rng = np.random.RandomState(seed)
    close = pd.Series(
        100 + np.cumsum(rng.randn(n) * 0.5),
        index=pd.date_range("2020-01-01", periods=n, freq="B"),
    )
    high = close + rng.rand(n) * 0.5
    low = close - rng.rand(n) * 0.5
    return high, low, close


def test_columns_present_and_named():
    high, low, close = _ohlc()
    out = ta.band_cross_retest(high, low, close, len_fast=10, len_slow=30)
    assert list(out.columns) == [
        "BANDXR_CROSS_UP_EMA_10_30", "BANDXR_CROSS_DN_EMA_10_30",
        "BANDXR_RETEST_FAST_EMA_10_30", "BANDXR_RETEST_SLOW_EMA_10_30",
        "BANDXR_GAP_ATR_EMA_10_30",
    ]


def test_strong_uptrend_produces_a_qualifying_cross_and_retest():
    # A flat run (bands overlapping/touching), then a strong sustained
    # rally (a genuine, large, fast impulse -- comfortably clears the
    # default extension/velocity/separation minimums), then a pullback
    # that touches back into the fast band -- the textbook retest setup.
    vals = [100.0] * 20                                  # 0-19: flat (bands settle, touching)
    vals += [100.0 + i * 3.0 for i in range(1, 16)]       # 20-34: strong rally (+3/bar)
    vals += [vals[-1] - i * 0.5 for i in range(1, 11)]    # 35-44: gentle pullback toward the bands
    vals += [vals[-1]] * 10                               # 45-54: flat tail
    close = pd.Series(vals)
    high = close + 0.3
    low = close - 0.3

    out = ta.band_cross_retest(high, low, close, ma_type="ema", len_fast=5, len_slow=15,
                                atr_length=5, min_ext_atr=1.0, min_vel_atr=0.05, min_sep_atr=0.1)

    assert out["BANDXR_CROSS_UP_EMA_5_15"].sum() >= 1, "fixture must produce a qualifying cross to test the branch"
    assert out["BANDXR_RETEST_FAST_EMA_5_15"].sum() >= 1, "fixture must produce a qualifying retest to test the branch"
    # A cross up must always precede its retest.
    cross_idx = out.index[out["BANDXR_CROSS_UP_EMA_5_15"] == 1][0]
    retest_idx = out.index[out["BANDXR_RETEST_FAST_EMA_5_15"] == 1][0]
    assert retest_idx > cross_idx


def test_no_lookahead():
    high, low, close = _ohlc()
    T = 200
    out_full = ta.band_cross_retest(high, low, close, len_fast=10, len_slow=30)

    high_c, low_c, close_c = high.copy(), low.copy(), close.copy()
    high_c.iloc[T + 1:] += 1000.0
    low_c.iloc[T + 1:] += 1000.0
    close_c.iloc[T + 1:] += 1000.0
    out_corrupted = ta.band_cross_retest(high_c, low_c, close_c, len_fast=10, len_slow=30)

    pdt.assert_frame_equal(out_full.iloc[:T + 1], out_corrupted.iloc[:T + 1])


def test_reachability_via_accessor():
    high, low, close = _ohlc()
    df = pd.DataFrame({
        "open": close, "high": high, "low": low, "close": close,
        "volume": pd.Series(1000.0, index=close.index),
    })

    assert "band_cross_retest" in ta.Category["trend"]
    assert callable(getattr(df.ta, "band_cross_retest"))

    module_result = ta.band_cross_retest(high=high, low=low, close=close, len_fast=10, len_slow=30)
    accessor_result = df.ta.band_cross_retest(len_fast=10, len_slow=30)
    pdt.assert_frame_equal(module_result, accessor_result)
