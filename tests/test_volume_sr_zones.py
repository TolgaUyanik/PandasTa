# tests/test_volume_sr_zones.py
"""volume_sr_zones -- volume-confirmed pivot support/resistance zones
(TVPTA-3-composite, ported from "Volume-Weighted Support & Resistance").
Self-contained on synthetic data.

Reachability tests `import pandas_ta`, NOT `importlib.util.spec_from_file_
location` (see TODO.md TVPTA-3(c)).
"""
import numpy as np
import pandas as pd
import pandas.testing as pdt
import pytest

from .context import pandas_ta as ta


def _ohlcv(n=150, seed=0):
    rng = np.random.RandomState(seed)
    close = pd.Series(
        100 + np.cumsum(rng.randn(n)),
        index=pd.date_range("2020-01-01", periods=n, freq="B"),
    )
    high = close + rng.rand(n) + 0.3
    low = close - rng.rand(n) - 0.3
    volume = pd.Series(rng.randint(1000, 2000, n).astype(float), index=close.index)
    return high, low, close, volume


def test_columns_present_and_named():
    high, low, close, volume = _ohlcv()
    out = ta.volume_sr_zones(high, low, close, volume, pivot_length=5, vol_length=10)
    assert list(out.columns) == [
        "VOLSR_RES_DIST_5_10", "VOLSR_SUP_DIST_5_10",
        "VOLSR_RES_BROKEN_5_10", "VOLSR_SUP_BROKEN_5_10",
    ]


def test_no_zone_without_volume_confirmation():
    # A textbook pivot high with FLAT (never above-average) volume must
    # never form a resistance zone -- the whole point of the volume gate.
    n = 20
    high = pd.Series([50.0] * n)
    high.iloc[10] = 60.0  # an obvious pivot high at bar10 (left=right=3)
    low = high - 5.0
    close = high - 2.0
    volume = pd.Series(1000.0, index=range(n))  # perfectly flat -> never > its own SMA*mult

    out = ta.volume_sr_zones(high, low, close, volume, pivot_length=3, vol_length=5, vol_mult=1.5)
    assert out["VOLSR_RES_DIST_3_5"].isna().all()
    assert out["VOLSR_RES_BROKEN_3_5"].sum() == 0


def test_zone_forms_with_volume_confirmation_and_breaks():
    n = 20
    high = pd.Series([50.0] * n)
    high.iloc[10] = 60.0
    low = high - 5.0
    close = high - 2.0
    volume = pd.Series(1000.0, index=range(n))
    volume.iloc[10] = 5000.0  # well above its own trailing SMA * 1.5

    out = ta.volume_sr_zones(high, low, close, volume, pivot_length=3, vol_length=5, vol_mult=1.5,
                              atr_length=3, zone_atr_mult=0.25)

    # Zone forms at the confirmation bar (pivot_bar + pivot_length = 13)
    # and holds (non-NaN distance) until price closes back above it.
    assert not np.isnan(out["VOLSR_RES_DIST_3_5"].iloc[13])

    # Force a break: close above the pivot high on a later bar.
    close_break = close.copy()
    close_break.iloc[16] = 65.0
    out2 = ta.volume_sr_zones(high, low, close_break, volume, pivot_length=3, vol_length=5,
                               vol_mult=1.5, atr_length=3, zone_atr_mult=0.25)
    assert out2["VOLSR_RES_BROKEN_3_5"].iloc[16] == 1
    assert np.isnan(out2["VOLSR_RES_DIST_3_5"].iloc[17])


def test_same_bar_formation_and_break_matches_source_order():
    # CRITICAL regression (Fletcher round 1): the source (TZLl2QBP.pine)
    # runs FORM-NEW-ZONE, THEN REMOVE-BROKEN-LEVELS, in that order within
    # one bar's top-to-bottom pass -- a zone confirming on a bar whose
    # OWN close already sits past it must be created and immediately
    # broken on that SAME bar, not survive as a permanently-unbroken
    # phantom level (which is what an earlier version of this port did
    # by checking breaks before formation).
    n = 20
    high = pd.Series([50.0] * n)
    high.iloc[10] = 60.0  # pivot high, confirms at bar 13 (pivot_length=3)
    low = high - 5.0
    close = high - 2.0
    close.iloc[13] = 65.0  # the CONFIRMATION bar's own close already clears the zone top (60)
    volume = pd.Series(1000.0, index=range(n))
    volume.iloc[10] = 5000.0

    out = ta.volume_sr_zones(high, low, close, volume, pivot_length=3, vol_length=5, vol_mult=1.5,
                              atr_length=3, zone_atr_mult=0.25)

    assert out["VOLSR_RES_BROKEN_3_5"].iloc[13] == 1
    assert np.isnan(out["VOLSR_RES_DIST_3_5"].iloc[13])


def test_no_lookahead():
    high, low, close, volume = _ohlcv()
    T = 80
    out_full = ta.volume_sr_zones(high, low, close, volume)

    high_c, low_c, close_c, volume_c = high.copy(), low.copy(), close.copy(), volume.copy()
    high_c.iloc[T + 1:] += 1000.0
    low_c.iloc[T + 1:] += 1000.0
    close_c.iloc[T + 1:] += 1000.0
    volume_c.iloc[T + 1:] *= 5
    out_corrupted = ta.volume_sr_zones(high_c, low_c, close_c, volume_c)

    pdt.assert_frame_equal(out_full.iloc[:T + 1], out_corrupted.iloc[:T + 1])


def test_reachability_via_accessor():
    high, low, close, volume = _ohlcv()
    df = pd.DataFrame({
        "open": close, "high": high, "low": low, "close": close, "volume": volume,
    })

    assert "volume_sr_zones" in ta.Category["trend"]
    assert callable(getattr(df.ta, "volume_sr_zones"))

    module_result = ta.volume_sr_zones(high=high, low=low, close=close, volume=volume)
    accessor_result = df.ta.volume_sr_zones()
    pdt.assert_frame_equal(module_result, accessor_result)
