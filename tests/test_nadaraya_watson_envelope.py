# tests/test_nadaraya_watson_envelope.py
"""nadaraya_watson_envelope -- non-repainting rational-quadratic kernel
regression envelope (TVPTA-3-composite, ported from "ConfluX"). Self-
contained on synthetic data.

Reachability tests `import pandas_ta`, NOT `importlib.util.spec_from_file_
location` (see TODO.md TVPTA-3(c)).
"""
import numpy as np
import pandas as pd
import pandas.testing as pdt
import pytest

from .context import pandas_ta as ta


def _ohlc(n=260, seed=0):
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
    out = ta.nadaraya_watson_envelope(high, low, close, lookback=50)
    assert list(out.columns) == [
        "NWE_MID_50_8.0_8.0", "NWE_UPPER_50_8.0_8.0",
        "NWE_LOWER_50_8.0_8.0", "NWE_SLOPE_50_8.0_8.0",
    ]


def test_correctness_hand_computed():
    # Constant close -> the weighted average of a constant series is that
    # same constant, regardless of the kernel weights -- a case any
    # correct kernel-weighted average must get exactly right.
    n = 20
    close = pd.Series([50.0] * n)
    high = close + 1.0
    low = close - 1.0

    out = ta.nadaraya_watson_envelope(high, low, close, lookback=10, h=8.0, r=8.0)

    valid = out["NWE_MID_10_8.0_8.0"].dropna()
    assert len(valid) > 0
    assert valid.to_numpy() == pytest.approx(0.0, abs=1e-9)


def test_correctness_independent_recompute():
    high, low, close = _ohlc(n=80)
    lookback, h, r = 30, 6.0, 4.0

    out = ta.nadaraya_watson_envelope(high, low, close, lookback=lookback, h=h, r=r)

    i = np.arange(lookback + 1, dtype=float)
    weights = (1.0 + (i ** 2) / (2.0 * h * h * r)) ** (-r)
    weights_chrono = weights[::-1]
    weight_sum = weights.sum()

    vals = close.to_numpy(dtype=float)
    n = len(vals)
    window = lookback + 1
    expected_mid = np.full(n, np.nan)
    for end in range(window - 1, n):
        segment = vals[end - window + 1: end + 1]
        expected_mid[end] = np.dot(segment, weights_chrono) / weight_sum

    expected_dist = (close.to_numpy() - expected_mid) / close.to_numpy() * 100
    pdt.assert_series_equal(
        out[f"NWE_MID_{lookback}_{h}_{r}"],
        pd.Series(expected_dist, index=close.index, name=f"NWE_MID_{lookback}_{h}_{r}"),
    )


def test_no_lookahead():
    high, low, close = _ohlc()
    T = 220
    out_full = ta.nadaraya_watson_envelope(high, low, close, lookback=50)

    high_c, low_c, close_c = high.copy(), low.copy(), close.copy()
    high_c.iloc[T + 1:] += 1000.0
    low_c.iloc[T + 1:] += 1000.0
    close_c.iloc[T + 1:] += 1000.0
    out_corrupted = ta.nadaraya_watson_envelope(high_c, low_c, close_c, lookback=50)

    pdt.assert_frame_equal(out_full.iloc[:T + 1], out_corrupted.iloc[:T + 1])


def test_reachability_via_accessor():
    high, low, close = _ohlc()
    df = pd.DataFrame({
        "open": close, "high": high, "low": low, "close": close,
        "volume": pd.Series(1000.0, index=close.index),
    })

    assert "nadaraya_watson_envelope" in ta.Category["overlap"]
    assert callable(getattr(df.ta, "nadaraya_watson_envelope"))

    module_result = ta.nadaraya_watson_envelope(high=high, low=low, close=close, lookback=50)
    accessor_result = df.ta.nadaraya_watson_envelope(lookback=50)
    pdt.assert_frame_equal(module_result, accessor_result)
