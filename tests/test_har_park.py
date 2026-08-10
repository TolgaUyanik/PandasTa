# tests/test_har_park.py
"""har_park -- causal rolling-refit HAR regression on Parkinson volatility
(TVPTA-6, ported from "HAR-Parkinson Volume Forecast"). Self-contained on
synthetic data.

Reachability tests `import pandas_ta`, NOT `importlib.util.spec_from_file_
location` (see TODO.md TVPTA-3(c)).
"""
import numpy as np
import pandas as pd
import pytest

from .context import pandas_ta as ta


def _ohlc(n=100, seed=0):
    rng = np.random.RandomState(seed)
    close = pd.Series(
        100 + np.cumsum(rng.randn(n)),
        index=pd.date_range("2020-01-01", periods=n, freq="B"),
    )
    high = close + rng.rand(n) + 0.1
    low = close - rng.rand(n) - 0.1
    return high, low, close


def test_name_and_series():
    high, low, close = _ohlc(n=200)
    out = ta.har_park(high, low, close, fit_window=100)
    assert isinstance(out, pd.Series)
    assert out.name == "HARPARK_1_5_22"


def test_never_negative():
    # Source clips fpctRaw at 0.0 -- a negative forecasted volatility is
    # not a meaningful value, matching how natr/atr are non-negative.
    high, low, close = _ohlc(n=200, seed=1)
    out = ta.har_park(high, low, close, fit_window=100)
    assert (out.dropna() >= 0).all()


def test_nan_before_fit_ready_then_finite():
    # fit_ready requires bar_index > long_length + fit_window/2 + 60 AND a
    # solved regression -- with fit_window=100, long_length=22 that's
    # bar_index > 133. Confirms the causal gate actually gates (gate a).
    high, low, close = _ohlc(n=250, seed=2)
    out = ta.har_park(high, low, close, fit_window=100)
    assert out.iloc[:133].isna().all()
    assert out.iloc[150:].notna().any()


def test_correctness_against_independent_ols_refit():
    # Independently recompute the Parkinson series and the regression fit
    # at ONE specific bar using numpy.linalg.lstsq directly on hand-sliced
    # windows -- does not reuse the module's rolling-sum machinery, so this
    # actually validates gate (d), not just that the wiring round-trips.
    high, low, close = _ohlc(n=250, seed=3)
    fit_window = 100
    short_length, medium_length, long_length = 1, 5, 22
    out = ta.har_park(high, low, close, fit_window=fit_window)

    ln2 = np.log(2.0)
    hl_valid = (high > 0) & (low > 0) & (high >= low)
    park_pct = pd.Series(
        np.where(hl_valid, np.sqrt(np.log(high / low) ** 2 / (4 * ln2)) * 100, 0.0),
        index=close.index,
    )
    x1 = park_pct.rolling(short_length).mean()
    x2 = park_pct.rolling(medium_length).mean()
    x3 = park_pct.rolling(long_length).mean()
    y = park_pct
    p1, p2, p3 = x1.shift(1), x2.shift(1), x3.shift(1)
    valid = p1.notna() & p2.notna() & p3.notna() & y.notna()

    t = 200  # a bar comfortably inside the fit-ready region
    window_valid = valid.iloc[t - fit_window + 1: t + 1]
    X = np.column_stack([
        np.ones(window_valid.sum()),
        p1.iloc[t - fit_window + 1: t + 1][window_valid].to_numpy(),
        p2.iloc[t - fit_window + 1: t + 1][window_valid].to_numpy(),
        p3.iloc[t - fit_window + 1: t + 1][window_valid].to_numpy(),
    ])
    Y = y.iloc[t - fit_window + 1: t + 1][window_valid].to_numpy()
    coeffs, *_ = np.linalg.lstsq(X, Y, rcond=None)
    b0, b1, b2, b3 = coeffs
    expected = max(b0 + b1 * x1.iloc[t] + b2 * x2.iloc[t] + b3 * x3.iloc[t], 0.0)

    assert out.iloc[t] == pytest.approx(expected, rel=1e-6)


def test_offset():
    high, low, close = _ohlc(n=200, seed=4)
    out = ta.har_park(high, low, close, fit_window=100)
    shifted = ta.har_park(high, low, close, fit_window=100, offset=1)
    pd.testing.assert_series_equal(
        shifted.iloc[1:].reset_index(drop=True),
        out.iloc[:-1].reset_index(drop=True),
        check_names=False,
    )
