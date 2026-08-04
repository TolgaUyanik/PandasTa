# tests/test_weis_wave.py
"""weis_wave -- Renko-gated volume/effort wave oscillator (David Weis),
TVPTA-3, ported from "Weis Wave Renko - Effort vs Result" (source has
exactly one plot() call in 947 lines; everything else is label/table UI).
Self-contained on synthetic data.

Reachability tests `import pandas_ta`, NOT `importlib.util.spec_from_file_
location` (see TODO.md TVPTA-3(c)).
"""
import numpy as np
import pandas as pd
import pandas.testing as pdt
import pytest

from .context import pandas_ta as ta


def _ohlcv(n=100, seed=0):
    rng = np.random.RandomState(seed)
    close = pd.Series(
        100 + np.cumsum(rng.randn(n)),
        index=pd.date_range("2020-01-01", periods=n, freq="B"),
    )
    open_ = close.shift(1).fillna(close.iloc[0])
    high = pd.concat([close, open_], axis=1).max(axis=1) + rng.rand(n)
    low = pd.concat([close, open_], axis=1).min(axis=1) - rng.rand(n)
    volume = pd.Series(rng.randint(100, 500, n).astype(float), index=close.index)
    return open_, high, low, close, volume


def test_name_and_series():
    open_, high, low, close, volume = _ohlcv()
    out = ta.weis_wave(high, low, close, open_, volume)
    assert isinstance(out, pd.Series)
    assert out.name == "WEISWAVE_TRAD_3.0"


def test_correctness_hand_computed():
    # price_source="close" -> the Renko box tracks close alone (hi_src ==
    # lo_src == close). box=2.0. Traced by hand bar-by-bar against the
    # source's currclose/direction/vol recursion:
    #   bar0: close=10, prevclose=0 -> box [-2,2] broken above -> cur=10,
    #         dir=1 (new wave) -> wave_effort=vol[0]=100
    #   bar1: close=13, prevclose=10 -> box [8,12] broken above -> cur=13,
    #         dir=1 (unchanged) -> wave_effort=100+200=300
    #   bar2: close=12, prevclose=13 -> box [11,15] NOT broken (12 inside)
    #         -> cur stays 13, dir unchanged -> wave_effort=300+150=450
    #   bar3: close=16, prevclose=13 -> box [11,15] broken above -> cur=16,
    #         dir=1 (unchanged) -> wave_effort=450+300=750
    #   bar4: close=14, prevclose=16 -> box [14,18] NOT broken (14 is not
    #         strictly < 14) -> cur stays 16, dir unchanged
    #         -> wave_effort=750+250=1000
    # normalize=False throughout -> barcount stays 1 -> WEISWAVE=wave_effort.
    close = pd.Series([10.0, 13.0, 12.0, 16.0, 14.0])
    open_ = close.shift(1).fillna(10.0)
    high = close + 1
    low = close - 1
    volume = pd.Series([100.0, 200.0, 150.0, 300.0, 250.0])

    out = ta.weis_wave(high, low, close, open_, volume,
                        method="traditional", value=2.0, price_source="close")

    expected = pd.Series([100.0, 300.0, 450.0, 750.0, 1000.0])
    pdt.assert_series_equal(out.reset_index(drop=True), expected, check_names=False)


def test_no_lookahead():
    open_, high, low, close, volume = _ohlcv()
    T = 60
    out_full = ta.weis_wave(high, low, close, open_, volume)

    open_c, high_c, low_c, close_c, volume_c = (
        open_.copy(), high.copy(), low.copy(), close.copy(), volume.copy(),
    )
    close_c.iloc[T + 1:] += 1000.0
    high_c.iloc[T + 1:] += 1000.0
    low_c.iloc[T + 1:] += 1000.0
    open_c.iloc[T + 1:] += 1000.0
    volume_c.iloc[T + 1:] *= 5

    out_corrupted = ta.weis_wave(high_c, low_c, close_c, open_c, volume_c)

    pdt.assert_series_equal(out_full.iloc[:T + 1], out_corrupted.iloc[:T + 1])


def test_reachability_via_accessor():
    open_, high, low, close, volume = _ohlcv()
    df = pd.DataFrame({
        "open": open_, "high": high, "low": low, "close": close, "volume": volume,
    })

    assert "weis_wave" in ta.Category["volume"]
    assert callable(getattr(df.ta, "weis_wave"))

    module_result = ta.weis_wave(high=high, low=low, close=close, open_=open_, volume=volume)
    accessor_result = df.ta.weis_wave()
    pdt.assert_series_equal(module_result, accessor_result)
