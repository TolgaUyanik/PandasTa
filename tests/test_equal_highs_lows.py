# tests/test_equal_highs_lows.py
"""equal_highs_lows -- tolerance-clustered equal-high/equal-low liquidity
levels (TVPTA-3-composite, ported from "Equal Highs & Equal Lows"). Self-
contained on synthetic data.

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
        100 + np.cumsum(rng.randn(n)),
        index=pd.date_range("2020-01-01", periods=n, freq="B"),
    )
    high = close + rng.rand(n) + 0.5
    low = close - rng.rand(n) - 0.5
    return high, low, close


def test_columns_present_and_named():
    high, low, close = _ohlc()
    out = ta.equal_highs_lows(high, low, close, left=2, right=2)
    assert list(out.columns) == [
        "EQH_2_2", "EQL_2_2", "EQH_DIST_2_2", "EQL_DIST_2_2",
        "EQH_BROKEN_2_2", "EQL_BROKEN_2_2",
    ]


def test_correctness_hand_computed_pct_tolerance():
    # left=right=1, pct_tol so the tolerance is a known constant (avoids
    # ATR's recursive smoothing for a hand-traceable fixture).
    # Highs: [.., 10, 20, 10.4, ..] -> bar index 2 (value 10) confirms as
    # a pivot high at bar index 3 (right=1 lag) since 10 > 9 (left) and
    # 10 > 10.4? No -- need 10 STRICTLY greater than ALL window members.
    # Construct explicitly instead of reasoning abstractly:
    high = pd.Series([5.0, 9.0, 10.0, 3.0, 4.0, 10.05, 3.0])
    low = high - 5.0
    close = high - 2.0

    # Pivot highs (left=1,right=1): bar2 (10.0) vs window[bar1=9,bar3=3]
    # -> 10.0 is the strict max -> confirms at bar3 (2+right=3).
    # bar5 (10.05) vs window[bar4=4,bar6=3] -> strict max -> confirms at
    # bar6 (5+1=6).
    # Tolerance is evaluated against the CURRENT bar's own close (bar6:
    # high=3.0 -> close=1.0), not the pivot's price -- pct_tol=10.0 gives
    # tolerance = 1.0*10/100 = 0.1, comfortably >= the 0.05 gap between
    # the two pivot highs (10.0 and 10.05).
    out = ta.equal_highs_lows(high, low, close, left=1, right=1,
                               tol_mode="percent", pct_tol=10.0)

    assert out["EQH_1_1"].iloc[6] == 1
    level = max(10.05, 10.0)
    assert out["EQH_DIST_1_1"].iloc[6] == pytest.approx((close.iloc[6] - level) / close.iloc[6] * 100)


def test_same_bar_formation_and_break_matches_source_order():
    # CRITICAL regression (Fletcher round 1): the source (K3net9Kl-RLS.pine)
    # runs level FORMATION first, break-check SECOND, within one bar's
    # top-to-bottom pass -- a level that forms on a bar whose own close
    # already clears it must be created and immediately broken that SAME
    # bar, not survive as a permanently-unbroken phantom (which is what
    # an earlier version of this port did by checking breaks before
    # formation -- its docstring even falsely claimed the opposite order
    # was source-faithful).
    # Pivot highs at bar2 (10.0, confirms j=3) and bar5 (10.05, confirms
    # j=6, within tolerance of bar2's 10.0) -- level forms at j=6 as
    # max(10.05, 10.0)=10.05. close[6] is set ABOVE that level.
    high = pd.Series([5.0, 9.0, 10.0, 3.0, 4.0, 10.05, 3.0])
    low = high - 5.0
    close = pd.Series([3.0, 7.0, 8.0, 1.0, 2.0, 2.0, 11.0])  # close[6]=11.0 > level(10.05)

    out = ta.equal_highs_lows(high, low, close, left=1, right=1,
                               tol_mode="percent", pct_tol=50.0)  # loose tolerance, well past the 0.05 gap

    assert out["EQH_1_1"].iloc[6] == 1, "fixture must actually form a level to test the same-bar break"
    assert out["EQH_BROKEN_1_1"].iloc[6] == 1
    assert np.isnan(out["EQH_DIST_1_1"].iloc[6])


def test_broken_flag_and_dist_reset_after_break():
    high, low, close = _ohlc()
    out = ta.equal_highs_lows(high, low, close, left=3, right=3,
                               tol_mode="atr", atr_length=10, atr_mult=0.5)

    broken = out["EQH_BROKEN_3_3"]
    dist = out["EQH_DIST_3_3"]
    formed = out["EQH_3_3"]
    assert broken.sum() > 0, "fixture must actually produce a break to test the branch"

    for pos in np.flatnonzero(broken.to_numpy() == 1):
        # A break can only fire if a level was active going into this bar.
        if pos > 0:
            assert not np.isnan(dist.iloc[pos - 1])
        # If nothing re-forms on the SAME bar the break happened, the
        # level must be cleared (NaN) on that same bar -- not left
        # dangling at its pre-break value.
        if formed.iloc[pos] == 0:
            assert np.isnan(dist.iloc[pos])


def test_no_lookahead():
    high, low, close = _ohlc()
    T = 80
    out_full = ta.equal_highs_lows(high, low, close)

    high_c, low_c, close_c = high.copy(), low.copy(), close.copy()
    high_c.iloc[T + 1:] += 1000.0
    low_c.iloc[T + 1:] += 1000.0
    close_c.iloc[T + 1:] += 1000.0
    out_corrupted = ta.equal_highs_lows(high_c, low_c, close_c)

    pdt.assert_frame_equal(out_full.iloc[:T + 1], out_corrupted.iloc[:T + 1])


def test_reachability_via_accessor():
    high, low, close = _ohlc()
    df = pd.DataFrame({
        "open": close, "high": high, "low": low, "close": close,
        "volume": pd.Series(1000.0, index=close.index),
    })

    assert "equal_highs_lows" in ta.Category["trend"]
    assert callable(getattr(df.ta, "equal_highs_lows"))

    module_result = ta.equal_highs_lows(high=high, low=low, close=close)
    accessor_result = df.ta.equal_highs_lows()
    pdt.assert_frame_equal(module_result, accessor_result)
