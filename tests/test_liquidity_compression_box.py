# tests/test_liquidity_compression_box.py
"""liquidity_compression_box -- rolling range-compression + frozen-box
breakout detector (TVPTA-3-composite, ported from "Liquidity Compression
Box"). Self-contained on synthetic data.

Reachability tests `import pandas_ta`, NOT `importlib.util.spec_from_file_
location` (see TODO.md TVPTA-3(c)).
"""
import numpy as np
import pandas as pd
import pandas.testing as pdt
import pytest

from .context import pandas_ta as ta


def _ohlc(n=150, seed=0):
    rng = np.random.RandomState(seed)
    close = pd.Series(
        100 + np.cumsum(rng.randn(n) * 0.3),
        index=pd.date_range("2020-01-01", periods=n, freq="B"),
    )
    open_ = close.shift(1).fillna(close.iloc[0])
    high = pd.concat([close, open_], axis=1).max(axis=1) + rng.rand(n) * 0.2
    low = pd.concat([close, open_], axis=1).min(axis=1) - rng.rand(n) * 0.2
    return open_, high, low, close


def test_columns_present_and_named():
    open_, high, low, close = _ohlc()
    out = ta.liquidity_compression_box(high, low, close, open_, window=5)
    assert list(out.columns) == [
        "LCB_FORMED_5", "LCB_HIGH_DIST_5", "LCB_LOW_DIST_5",
        "LCB_BREAKOUT_UP_5", "LCB_BREAKOUT_DN_5",
    ]


def test_flat_tight_range_forms_a_box():
    # A perfectly flat, tiny-range, small-body window must satisfy all
    # three formation gates: compressed (tiny range vs ATR), small bodies
    # (all dojis), and enough wick touches (every bar touches both edges
    # in a flat run).
    n = 30
    close = pd.Series([100.0] * n)
    open_ = pd.Series([100.0] * n)
    high = pd.Series([100.5] * n)
    low = pd.Series([99.5] * n)

    out = ta.liquidity_compression_box(high, low, close, open_, window=5,
                                        max_atr_mult=10.0, min_wick_touches=3, max_body_pct=95.0)
    assert out["LCB_FORMED_5"].sum() > 0, "fixture must actually form a box to test the branch"


def test_breakout_up_requires_high_and_close_beyond_frozen_edge():
    n = 15
    close = pd.Series([100.0] * n)
    open_ = pd.Series([100.0] * n)
    high = pd.Series([100.5] * n)
    low = pd.Series([99.5] * n)
    # A clean breakout bar: both high and close clear the frozen high.
    close.iloc[10] = 105.0
    high.iloc[10] = 106.0

    # atr_length small enough that ATR (RMA-based, needs a warmup) is
    # already available well before bar10 -- otherwise no box can form
    # in time to test the breakout at all (caught by running this).
    out = ta.liquidity_compression_box(high, low, close, open_, window=5, atr_length=3,
                                        max_atr_mult=10.0, min_wick_touches=3, max_body_pct=95.0)
    assert out["LCB_FORMED_5"].iloc[:10].sum() > 0, "fixture must form a box before bar10 to test the breakout"
    assert out["LCB_BREAKOUT_UP_5"].iloc[10] == 1
    assert out["LCB_BREAKOUT_DN_5"].sum() == 0


def test_breakout_bar_never_also_forms_a_new_box():
    # MAJOR regression (Fletcher round 1): the source gates box formation
    # on `not waiting_breakout` EVALUATED BEFORE that same bar's later
    # breakout-check block runs -- so a bar that fires a breakout can
    # never ALSO form a fresh box that same bar. An earlier version of
    # this port checked `waiting` AFTER the breakout branch had already
    # cleared it, making a same-bar "breakout, then immediately re-arm"
    # structurally reachable. General invariant, not a single hand-picked
    # fixture: across many formations/breakouts, LCB_BREAKOUT_UP/DN and
    # LCB_FORMED must never both be 1 on the same bar.
    open_, high, low, close = _ohlc(n=400, seed=3)
    out = ta.liquidity_compression_box(high, low, close, open_, window=4, atr_length=5,
                                        max_atr_mult=2.0, min_wick_touches=2, max_body_pct=90.0)

    any_breakout = (out["LCB_BREAKOUT_UP_4"] == 1) | (out["LCB_BREAKOUT_DN_4"] == 1)
    assert any_breakout.sum() > 0, "fixture must actually produce breakouts to test the branch"
    assert not ((any_breakout) & (out["LCB_FORMED_4"] == 1)).any()


def test_no_lookahead():
    open_, high, low, close = _ohlc()
    T = 100
    out_full = ta.liquidity_compression_box(high, low, close, open_)

    open_c, high_c, low_c, close_c = open_.copy(), high.copy(), low.copy(), close.copy()
    high_c.iloc[T + 1:] += 1000.0
    low_c.iloc[T + 1:] += 1000.0
    close_c.iloc[T + 1:] += 1000.0
    open_c.iloc[T + 1:] += 1000.0
    out_corrupted = ta.liquidity_compression_box(high_c, low_c, close_c, open_c)

    pdt.assert_frame_equal(out_full.iloc[:T + 1], out_corrupted.iloc[:T + 1])


def test_reachability_via_accessor():
    open_, high, low, close = _ohlc()
    df = pd.DataFrame({
        "open": open_, "high": high, "low": low, "close": close,
        "volume": pd.Series(1000.0, index=close.index),
    })

    assert "liquidity_compression_box" in ta.Category["trend"]
    assert callable(getattr(df.ta, "liquidity_compression_box"))

    module_result = ta.liquidity_compression_box(high=high, low=low, close=close, open_=open_)
    accessor_result = df.ta.liquidity_compression_box()
    pdt.assert_frame_equal(module_result, accessor_result)
