# tests/test_cdvo.py
"""cdvo -- ATR-Adjusted Varadi Oscillator (TVPTA-3, ported from "Custom
DVO (ATR-Adjusted Varadi Oscillator)"). Self-contained on synthetic data.

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
    high = close + rng.rand(n)
    low = close - rng.rand(n)
    return high, low, close


def test_bounded_0_100():
    high, low, close = _ohlc()
    out = ta.cdvo(high, low, close, atr_length=10, smooth=2, rank_length=50)
    valid = out.dropna()
    assert (valid >= 0).all() and (valid <= 100).all()


def test_correctness_independent_recompute():
    # Independent reimplementation of every step -- NOT calling the
    # module's private _percentrank -- against small parameters so the
    # rolling window is exercised well before the series ends.
    high, low, close = _ohlc(n=120)
    atr_length, smooth, rank_length = 5, 3, 20

    out = ta.cdvo(high, low, close, atr_length=atr_length, smooth=smooth, rank_length=rank_length)

    median_price = (high + low) / 2.0
    atr_series = ta.atr(high, low, close, length=atr_length)
    # Matches the source's `atrVal != 0 ? ... : 0.0` ternary (Fletcher
    # round 1: a bare division diverges from Pine on a zero-ATR bar).
    stretch = np.where(atr_series != 0, (close - median_price) / atr_series.replace(0, np.nan), 0.0)
    stretch = pd.Series(stretch, index=close.index)
    smoothed = ta.sma(stretch, length=smooth)

    # pandas' `.rolling(window).apply(...)` defaults to `min_periods=window`
    # -- the ENTIRE window (current + rank_length priors) must be non-NaN
    # before it fires at all, not merely the current value. Matching that
    # exactly (rather than the more permissive "skip only NaN priors")
    # is what this test caught on the first attempt: a `len(valid) == 0`
    # gate let the manual loop fire several bars before the module's
    # actual rolling window had fully cleared the atr/sma NaN warmup.
    expected = pd.Series(np.nan, index=close.index)
    vals = smoothed.to_numpy()
    for i in range(rank_length, len(vals)):
        cur = vals[i]
        window = vals[i - rank_length:i]
        if np.isnan(cur) or np.isnan(window).any():
            continue
        expected.iloc[i] = (window < cur).sum() / rank_length * 100.0

    pdt.assert_series_equal(out, expected, check_names=False)


def test_zero_atr_gives_zero_stretch_not_nan():
    # MAJOR regression (Fletcher round 1): a BIST name frozen at its price
    # limit for atr_length+ consecutive sessions has True Range 0 every
    # bar. The source Pine defines stretch=0.0 on a zero-ATR bar (`atrVal
    # != 0 ? ... : 0.0`); a bare `.replace(0, nan)` would instead poison
    # the trailing SMA/percent-rank windows with an avoidable NaN the
    # source never has.
    #
    # This is tested in ISOLATION on the exact 2-line pattern used in
    # cdvo.py, not end-to-end through the real `ta.atr()`: empirically,
    # pandas_ta's `atr()` (RMA via `.ewm().mean()`) on a genuinely flat
    # 6,000-bar series asymptotes to ~2.22e-16 (machine epsilon) and never
    # reaches bit-exact 0.0, so the branch is effectively unreachable
    # through that specific smoothing implementation on realistic data --
    # confirmed by direct experiment, not assumed. The defensive code is
    # still correct and cheap to keep (Pine's own smoothing may behave
    # differently), so it's verified directly here instead of chasing an
    # unreachable end-to-end fixture.
    atr_val = pd.Series([2.0, 0.0, 0.0, 3.0])
    close_minus_median = pd.Series([1.0, 5.0, -5.0, 6.0])

    stretch = close_minus_median / atr_val.replace(0, float("nan"))
    stretch = stretch.where(atr_val != 0, 0.0)

    assert stretch.iloc[0] == pytest.approx(0.5)
    assert stretch.iloc[1] == 0.0
    assert stretch.iloc[2] == 0.0
    assert stretch.iloc[3] == pytest.approx(2.0)
    assert not stretch.isna().any()


def test_no_lookahead():
    high, low, close = _ohlc()
    T = 100
    out_full = ta.cdvo(high, low, close, atr_length=10, smooth=2, rank_length=50)

    high_c, low_c, close_c = high.copy(), low.copy(), close.copy()
    high_c.iloc[T + 1:] += 1000.0
    low_c.iloc[T + 1:] += 1000.0
    close_c.iloc[T + 1:] += 1000.0
    out_corrupted = ta.cdvo(high_c, low_c, close_c, atr_length=10, smooth=2, rank_length=50)

    pdt.assert_series_equal(out_full.iloc[:T + 1], out_corrupted.iloc[:T + 1])


def test_reachability_via_accessor():
    high, low, close = _ohlc()
    df = pd.DataFrame({
        "open": close, "high": high, "low": low, "close": close,
        "volume": pd.Series(1000.0, index=close.index),
    })

    assert "cdvo" in ta.Category["momentum"]
    assert callable(getattr(df.ta, "cdvo"))

    module_result = ta.cdvo(high=high, low=low, close=close)
    accessor_result = df.ta.cdvo()
    pdt.assert_series_equal(module_result, accessor_result)
