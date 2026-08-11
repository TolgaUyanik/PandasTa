# tests/test_liquidity_sweep.py
"""liquidity_sweep (LSH) -- confirmed swing pivots become BSL/SSL resting
liquidity levels; each resolves via wick sweep or break-then-reclaim
(TVPTA-6, ported from "Liquidity Sweep Hunter | AlphaScript"). Self-
contained on synthetic data.

Reachability tests `import pandas_ta` (`.context`), NOT `importlib.util.
spec_from_file_location` (see TODO.md TVPTA-3(c)).

All end-to-end scenarios below are built on physically valid OHLC (low <=
high on every bar -- each scenario builder asserts this itself at
construction time, per this project's own documented history of tests
dodging bugs via impossible bars, see tests/test_sphinx_unicorn.py's
module docstring for the precedent incident this guards against).

Every scenario's expected values were hand-derived against the .pine
source's own logic (`docs/TradingView/pine/PqkIPsgl-Liquidity-Sweep-
Hunter-AlphaScript.pine`) and then independently confirmed by running the
port and reading its actual output before being written as an assertion
here -- not assumed.
"""
import numpy as np
import pandas as pd
import pytest

from .context import pandas_ta as ta
from pandas_ta.trend.liquidity_sweep import _confirm_strict_pivots, _process_side, _Level


# ---------------------------------------------------------------------------
# _confirm_strict_pivots -- isolated unit tests
# ---------------------------------------------------------------------------

def test_confirm_strict_pivots_high_unique_extreme():
    vals = pd.Series([1.0, 2.0, 5.0, 2.0, 1.0])
    out = _confirm_strict_pivots(vals, 2, 2, is_high=True)
    # window [0..4], bar 2 (5.0) is the strict unique max, confirms at j=4
    assert out[4] == 5.0
    assert np.isnan(out[:4]).all()


def test_confirm_strict_pivots_tie_rejects():
    vals = pd.Series([1.0, 5.0, 3.0, 5.0, 1.0])
    out = _confirm_strict_pivots(vals, 2, 2, is_high=True)
    # bar 2 (3.0) is not the max (tied 5.0s exist elsewhere) -- no confirm
    assert np.isnan(out).all()


def test_confirm_strict_pivots_low_mirror():
    vals = pd.Series([5.0, 4.0, 1.0, 4.0, 5.0])
    out = _confirm_strict_pivots(vals, 2, 2, is_high=False)
    assert out[4] == 1.0


# ---------------------------------------------------------------------------
# _process_side -- isolated unit tests
# ---------------------------------------------------------------------------

def test_process_side_bear_wick_sweep():
    levels = [_Level(price=110.0, lvl_bar=0)]
    high_v = np.array([0, 0, 0, 0, 0, 112.0])
    close_v = np.array([0, 0, 0, 0, 0, 95.0])
    atr_v = np.full(6, 1.0)
    new_levels, swept, reclaimed = _process_side(
        levels, 5, high_v, close_v, atr_v, atr_mult=0.0, max_age=300,
        mode_wick=True, mode_reclaim=True, is_bear=True)
    assert swept is True
    assert reclaimed is False
    assert new_levels == []  # resolved level leaves the pool


def test_process_side_bear_break_then_next_bar_reclaim():
    levels = [_Level(price=110.0, lvl_bar=0)]
    high_v = np.array([0, 0, 0, 0, 0, 111.0, 101.0])
    close_v = np.array([0, 0, 0, 0, 0, 111.0, 100.0])
    atr_v = np.full(7, 1.0)
    # bar 5: close breaks above -> marked broken, no event, level stays
    lvls, swept, reclaimed = _process_side(
        levels, 5, high_v, close_v, atr_v, atr_mult=0.0, max_age=300,
        mode_wick=True, mode_reclaim=True, is_bear=True)
    assert swept is False and reclaimed is False
    assert len(lvls) == 1 and lvls[0].broken is True
    # bar 6: close crosses back below -> reclaim fires, level resolves
    lvls2, swept2, reclaimed2 = _process_side(
        lvls, 6, high_v, close_v, atr_v, atr_mult=0.0, max_age=300,
        mode_wick=True, mode_reclaim=True, is_bear=True)
    assert swept2 is False and reclaimed2 is True
    assert lvls2 == []


def test_process_side_max_age_expires_without_event():
    levels = [_Level(price=110.0, lvl_bar=0)]
    high_v = np.array([0, 0, 0, 0, 0, 0, 112.0])
    close_v = np.array([0, 0, 0, 0, 0, 0, 95.0])
    atr_v = np.full(7, 1.0)
    lvls, swept, reclaimed = _process_side(
        levels, 6, high_v, close_v, atr_v, atr_mult=0.0, max_age=5,
        mode_wick=True, mode_reclaim=True, is_bear=True)
    # age = 6 - 0 = 6 > max_age(5) -> expires silently, even though bar 6's
    # own high/close would otherwise have triggered a sweep
    assert swept is False and reclaimed is False
    assert lvls == []


# ---------------------------------------------------------------------------
# End-to-end liquidity_sweep() scenarios
# ---------------------------------------------------------------------------

def _flooded_ohlc(n=25):
    high = np.full(n, 101.0)
    low = np.full(n, 99.0)
    close = np.full(n, 100.0)
    return high, low, close


def _idx(n):
    return pd.date_range("2020-01-01", periods=n, freq="B")


def test_pivot_confirms_and_dist_res_populates():
    # Swing high at bar 5 (110.0, strictly unique in window [3..7] since
    # every other bar's high is flooded to 101.0), confirms at bar 7
    # (swing_len=2). DIST_RES = (110-100)/100*100 = 10.0 from bar 7 on.
    n = 20
    high, low, close = _flooded_ohlc(n)
    high[5], low[5] = 110.0, 95.0
    assert (low <= high).all(), "construction check: every bar must be physically valid"
    idx = _idx(n)
    out = ta.liquidity_sweep(
        pd.Series(high, index=idx), pd.Series(low, index=idx), pd.Series(close, index=idx),
        swing_len=2, atr_mult=0.0,
    )
    assert out["LSH_DIST_RES_2"].iloc[:7].isna().all()
    assert out["LSH_DIST_RES_2"].iloc[7:].iloc[:3].eq(10.0).all()
    assert out["LSH_SWEEP_BEAR_2"].sum() == 0
    assert out["LSH_RECLAIM_BEAR_2"].sum() == 0


def test_bear_wick_sweep_fires_and_resolves_level():
    # Same swing-high setup; at bar 10, high pierces above (112 > 110) and
    # close ends back below (95 < 110) -- a wick sweep. Level resolves
    # (removed), so DIST_RES reverts to NaN immediately after (bar 10's
    # own value is also NaN -- the level that would have been measured is
    # exactly the one that just resolved this same bar).
    n = 20
    high, low, close = _flooded_ohlc(n)
    high[5], low[5] = 110.0, 95.0
    high[10], low[10], close[10] = 112.0, 94.0, 95.0
    assert (low <= high).all(), "construction check: every bar must be physically valid"
    idx = _idx(n)
    out = ta.liquidity_sweep(
        pd.Series(high, index=idx), pd.Series(low, index=idx), pd.Series(close, index=idx),
        swing_len=2, atr_mult=0.0,
    )
    assert out["LSH_SWEEP_BEAR_2"].iloc[10] == 1
    assert out["LSH_SWEEP_BEAR_2"].sum() == 1
    assert out["LSH_RECLAIM_BEAR_2"].sum() == 0
    assert pd.isna(out["LSH_DIST_RES_2"].iloc[10])
    assert out["LSH_DIST_RES_2"].iloc[9] == 10.0  # still active the bar before the sweep


def test_bear_break_then_reclaim_two_step():
    # bar 10: close breaks above the 110 level (112 > 110) -- marked
    # broken, no event fires yet (mutually exclusive with sweep, whose
    # condition requires close < level). bar 11: close (a flooded 100.0,
    # already < 110) crosses back below -- reclaim fires on the very next
    # bar the close sits below the level, per the source's own "close
    # crosses back" semantics (no additional delay).
    n = 20
    high, low, close = _flooded_ohlc(n)
    high[5], low[5] = 110.0, 95.0
    high[10], low[10], close[10] = 112.5, 111.5, 112.0
    assert (low <= high).all(), "construction check: every bar must be physically valid"
    idx = _idx(n)
    out = ta.liquidity_sweep(
        pd.Series(high, index=idx), pd.Series(low, index=idx), pd.Series(close, index=idx),
        swing_len=2, atr_mult=0.0,
    )
    assert out["LSH_SWEEP_BEAR_2"].sum() == 0
    assert out["LSH_RECLAIM_BEAR_2"].iloc[11] == 1
    assert out["LSH_RECLAIM_BEAR_2"].sum() == 1
    # bar 10 itself: still broken, not yet resolved -- DIST_RES still
    # reflects the (broken but not yet removed) level
    assert out["LSH_DIST_RES_2"].iloc[10] == pytest.approx((110.0 - 112.0) / 112.0 * 100, abs=1e-9)
    assert pd.isna(out["LSH_DIST_RES_2"].iloc[11])


def test_bull_wick_sweep_mirrors_bear():
    # Mirror on the SSL side: swing low at bar 5 (90.0, unique min), wick
    # sweep at bar 10 (low pierces below 90, close ends back above).
    n = 20
    high, low, close = _flooded_ohlc(n)
    high[5], low[5] = 105.0, 90.0
    high[10], low[10], close[10] = 106.0, 88.0, 105.0
    assert (low <= high).all(), "construction check: every bar must be physically valid"
    idx = _idx(n)
    out = ta.liquidity_sweep(
        pd.Series(high, index=idx), pd.Series(low, index=idx), pd.Series(close, index=idx),
        swing_len=2, atr_mult=0.0,
    )
    assert out["LSH_DIST_SUP_2"].iloc[7:10].eq((100.0 - 90.0) / 100.0 * 100).all()
    assert out["LSH_SWEEP_BULL_2"].iloc[10] == 1
    assert out["LSH_SWEEP_BULL_2"].sum() == 1
    assert out["LSH_RECLAIM_BULL_2"].sum() == 0
    assert pd.isna(out["LSH_DIST_SUP_2"].iloc[10])


def test_bull_break_then_reclaim_mirrors_bear():
    n = 20
    high, low, close = _flooded_ohlc(n)
    high[5], low[5] = 105.0, 90.0
    high[10], low[10], close[10] = 89.0, 87.5, 88.0
    assert (low <= high).all(), "construction check: every bar must be physically valid"
    idx = _idx(n)
    out = ta.liquidity_sweep(
        pd.Series(high, index=idx), pd.Series(low, index=idx), pd.Series(close, index=idx),
        swing_len=2, atr_mult=0.0,
    )
    assert out["LSH_SWEEP_BULL_2"].sum() == 0
    # bar 10: close (88.0) < level (90.0) -> marked broken, no event
    # bar 11: close reverts to flooded 100.0 > 90.0 -> reclaim fires
    assert out["LSH_RECLAIM_BULL_2"].iloc[11] == 1
    assert out["LSH_RECLAIM_BULL_2"].sum() == 1


def test_atr_penetration_filter_blocks_shallow_wick():
    # Same wick-sweep setup as test_bear_wick_sweep_fires_and_resolves_level,
    # but the wick only clears the level by 0.05 (high=110.05) while
    # atr_mult=1.0 demands a full ATR's worth of penetration -- the true
    # range on these bars is ~2.0 (flooded high 101 / low 99), so 0.05
    # cannot clear it. Must NOT fire, level must survive.
    n = 20
    high, low, close = _flooded_ohlc(n)
    high[5], low[5] = 110.0, 95.0
    high[10], low[10], close[10] = 110.05, 96.0, 95.0
    assert (low <= high).all(), "construction check: every bar must be physically valid"
    idx = _idx(n)
    out = ta.liquidity_sweep(
        pd.Series(high, index=idx), pd.Series(low, index=idx), pd.Series(close, index=idx),
        swing_len=2, atr_len=3, atr_mult=1.0,
    )
    assert out["LSH_SWEEP_BEAR_2"].sum() == 0
    assert out["LSH_DIST_RES_2"].iloc[10] == pytest.approx((110.0 - 95.0) / 95.0 * 100, abs=1e-9)


def test_max_age_expires_level_unresolved():
    n = 20
    high, low, close = _flooded_ohlc(n)
    high[5], low[5] = 110.0, 95.0
    assert (low <= high).all(), "construction check: every bar must be physically valid"
    idx = _idx(n)
    out = ta.liquidity_sweep(
        pd.Series(high, index=idx), pd.Series(low, index=idx), pd.Series(close, index=idx),
        swing_len=2, atr_mult=0.0, max_age=5,
    )
    # confirms bar 7 (lvl_bar=5); age = t-5 > 5 first true at t=11
    assert out["LSH_DIST_RES_2"].iloc[7:11].eq(10.0).all()
    assert out["LSH_DIST_RES_2"].iloc[11:].isna().all()
    assert out["LSH_SWEEP_BEAR_2"].sum() == 0
    assert out["LSH_RECLAIM_BEAR_2"].sum() == 0


def test_wick_mode_ignores_reclaim_path():
    # mode="wick" disables break-then-reclaim entirely: the break scenario
    # from test_bear_break_then_reclaim_two_step must now produce nothing.
    n = 20
    high, low, close = _flooded_ohlc(n)
    high[5], low[5] = 110.0, 95.0
    high[10], low[10], close[10] = 112.5, 111.5, 112.0
    assert (low <= high).all(), "construction check: every bar must be physically valid"
    idx = _idx(n)
    out = ta.liquidity_sweep(
        pd.Series(high, index=idx), pd.Series(low, index=idx), pd.Series(close, index=idx),
        swing_len=2, atr_mult=0.0, mode="wick",
    )
    assert out["LSH_SWEEP_BEAR_2"].sum() == 0
    assert out["LSH_RECLAIM_BEAR_2"].sum() == 0
    # level never gets marked broken in this mode, so it just keeps
    # reporting whatever the nearest bear level's distance is (still 110)
    assert out["LSH_DIST_RES_2"].iloc[10] == pytest.approx((110.0 - 112.0) / 112.0 * 100, abs=1e-9)


def test_causal_no_lookahead():
    n = 150
    rng = np.random.RandomState(7)
    close_v = 100 + np.cumsum(rng.randn(n) * 0.6)
    high_v = close_v + np.abs(rng.randn(n)) * 1.0
    low_v = close_v - np.abs(rng.randn(n)) * 1.0
    assert (low_v <= high_v).all(), "construction check: every bar must be physically valid"
    idx = _idx(n)
    high = pd.Series(high_v, index=idx)
    low = pd.Series(low_v, index=idx)
    close = pd.Series(close_v, index=idx)

    out_before = ta.liquidity_sweep(high, low, close, swing_len=3)
    assert out_before.filter(like="SWEEP").to_numpy().sum() > 0, "test data must actually produce a sweep event"
    assert out_before.filter(like="DIST").notna().to_numpy().sum() > 0, "test data must actually produce distance values"

    t = 100
    high_mut, low_mut, close_mut = high.copy(), low.copy(), close.copy()
    high_mut.iloc[t + 1:] *= 1.4
    low_mut.iloc[t + 1:] *= 0.7
    close_mut.iloc[t + 1:] *= 1.1
    out_after = ta.liquidity_sweep(high_mut, low_mut, close_mut, swing_len=3)

    pd.testing.assert_frame_equal(out_before.iloc[: t + 1], out_after.iloc[: t + 1])


def test_causal_deletion_no_lookahead():
    # Complementary causality check: truncating the series after t must
    # not change output at/before t either (deletion, not just mutation).
    n = 150
    rng = np.random.RandomState(7)
    close_v = 100 + np.cumsum(rng.randn(n) * 0.6)
    high_v = close_v + np.abs(rng.randn(n)) * 1.0
    low_v = close_v - np.abs(rng.randn(n)) * 1.0
    assert (low_v <= high_v).all(), "construction check: every bar must be physically valid"
    idx = _idx(n)
    high = pd.Series(high_v, index=idx)
    low = pd.Series(low_v, index=idx)
    close = pd.Series(close_v, index=idx)

    t = 100
    out_full = ta.liquidity_sweep(high, low, close, swing_len=3)
    out_trunc = ta.liquidity_sweep(high.iloc[: t + 1], low.iloc[: t + 1], close.iloc[: t + 1], swing_len=3)
    pd.testing.assert_frame_equal(out_full.iloc[: t + 1], out_trunc)


def test_accessor_matches_direct_call():
    n = 20
    high, low, close = _flooded_ohlc(n)
    high[5], low[5] = 110.0, 95.0
    idx = _idx(n)
    high_s, low_s, close_s = pd.Series(high, index=idx), pd.Series(low, index=idx), pd.Series(close, index=idx)
    df = pd.DataFrame({"high": high_s, "low": low_s, "close": close_s})
    via_accessor = df.ta.liquidity_sweep(swing_len=2, atr_mult=0.0)
    direct = ta.liquidity_sweep(high_s, low_s, close_s, swing_len=2, atr_mult=0.0)
    pd.testing.assert_frame_equal(via_accessor, direct)


def test_reachable_in_category_and_callable():
    assert "liquidity_sweep" in ta.Category["trend"]
    df = pd.DataFrame({"high": [1.0], "low": [1.0], "close": [1.0]})
    assert callable(getattr(df.ta, "liquidity_sweep"))


def test_columns_and_naming():
    n = 30  # default swing_len=10 needs verify_series min length 2*10+1=21
    high, low, close = _flooded_ohlc(n)
    idx = _idx(n)
    out = ta.liquidity_sweep(pd.Series(high, index=idx), pd.Series(low, index=idx), pd.Series(close, index=idx))
    expected = {
        "LSH_SWEEP_BULL_10", "LSH_SWEEP_BEAR_10", "LSH_RECLAIM_BULL_10",
        "LSH_RECLAIM_BEAR_10", "LSH_DIST_RES_10", "LSH_DIST_SUP_10",
    }
    assert set(out.columns) == expected
    assert out.name == "LSH_10"
    # Scale-free gate (d): the 4 flag columns are 0/1 categoricals; the 2
    # DIST columns are already `(price_diff / close) * 100` ratios, scale-
    # free by construction (same algebraic form as SPHINX_DIST_*/priorday_
    # fib's proof) -- not re-derived here, just confirmed dtype/int-ness.
    for c in ("LSH_SWEEP_BULL_10", "LSH_SWEEP_BEAR_10", "LSH_RECLAIM_BULL_10", "LSH_RECLAIM_BEAR_10"):
        assert set(out[c].unique()) <= {0, 1}


def test_invalid_mode_falls_back_to_both():
    n = 20
    high, low, close = _flooded_ohlc(n)
    high[5], low[5] = 110.0, 95.0
    idx = _idx(n)
    out = ta.liquidity_sweep(
        pd.Series(high, index=idx), pd.Series(low, index=idx), pd.Series(close, index=idx),
        swing_len=2, mode="bogus",
    )
    assert out["LSH_DIST_RES_2"].iloc[7:10].notna().all()
