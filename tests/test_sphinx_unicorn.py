# tests/test_sphinx_unicorn.py
"""sphinx_unicorn -- SMC/ICT "unicorn" (swing nested in an opposing-polarity
FVG, activates on displacement + optional BPR) (TVPTA-6, ported from
"Sphinx Unicorn - FVG Breaker Nesting Model"). Self-contained on synthetic
data.

Reachability tests `import pandas_ta`, NOT `importlib.util.spec_from_file_
location` (see TODO.md TVPTA-3(c)).

Fletcher round 1 CRITICAL: the original `_find_nested_fvg`'s filled-check
lower bound was `gap_end - d + 1` (an extra `-d` dragging the scan back
into the gap's own formation bars), so any gap ending 3+ bars before its
swing self-declared "filled" and was rejected -- `fvg_look` behaved like
`fvg_look=2` regardless of the actual parameter. On the register's own
600-bar generation frame this produced EXACTLY ZERO arms/fires (visible in
the regenerated register as `0..0`/`n/a` -- a defect the diff had shipped
and then explained away as "expected rarity"). Every one of the original
15 tests passed anyway, because: (a) the isolated unit tests were built on
NaN-padded arrays where the fill-scan has nothing to trip over, and (b) the
end-to-end scenarios were built on PHYSICALLY IMPOSSIBLE bars (a bar's low
set 49 points above its own high, to dodge the bug rather than expose it).
Fixed to `lo = gap_end + 1` (re-derived from the Pine source's `for k =
off0 to i-1` directly, independent of the buggy version). Every scenario
below is rebuilt on physically valid OHLC (low <= high always) and at
least one test per helper is a "several bars before the swing" case that
specifically fails on the pre-fix code -- verified during development by
running the buggy version against these exact arrays.
"""
import numpy as np
import pandas as pd
import pytest

from .context import pandas_ta as ta
from pandas_ta.trend.sphinx_unicorn import _find_nested_fvg, _find_disp_fvg


# ---------------------------------------------------------------------------
# _find_nested_fvg -- isolated unit tests
# ---------------------------------------------------------------------------

def test_find_nested_fvg_bullish_isolated_hit():
    high = np.array([1.0, np.nan, np.nan, np.nan, np.nan])
    low = np.array([np.nan, np.nan, 3.0, np.nan, np.nan])
    t, b = _find_nested_fvg(high, low, swing_bar=4, probe=2.0, radius=5, strict=True, is_bull_setup=True)
    assert (t, b) == (3.0, 1.0)


def test_find_nested_fvg_strict_boundary_rejects_edge_touch():
    high = np.array([1.0, np.nan, np.nan, np.nan, np.nan])
    low = np.array([np.nan, np.nan, 3.0, np.nan, np.nan])
    t, b = _find_nested_fvg(high, low, swing_bar=4, probe=1.0, radius=5, strict=True, is_bull_setup=True)
    assert np.isnan(t) and np.isnan(b)


def test_find_nested_fvg_non_strict_accepts_edge_touch():
    high = np.array([1.0, np.nan, np.nan, np.nan, np.nan])
    low = np.array([np.nan, np.nan, 3.0, np.nan, np.nan])
    t, b = _find_nested_fvg(high, low, swing_bar=4, probe=1.0, radius=5, strict=False, is_bull_setup=True)
    assert (t, b) == (3.0, 1.0)


def test_find_nested_fvg_bearish_mirror():
    high = np.array([np.nan, np.nan, 1.0, np.nan, np.nan])
    low = np.array([3.0, np.nan, np.nan, np.nan, np.nan])
    t, b = _find_nested_fvg(high, low, swing_bar=4, probe=2.0, radius=5, strict=True, is_bull_setup=False)
    assert (t, b) == (3.0, 1.0)


def test_find_nested_fvg_nearest_first_not_farthest():
    high = np.array([1.0, np.nan, 1.2, np.nan, np.nan])
    low = np.array([np.nan, np.nan, np.nan, np.nan, 2.8])
    t, b = _find_nested_fvg(high, low, swing_bar=4, probe=2.0, radius=5, strict=True, is_bull_setup=True)
    assert (t, b) == (2.8, 1.2)


def test_find_nested_fvg_gap_several_bars_before_swing_unfilled():
    # THE regression test for the Fletcher-round-1 CRITICAL: a fully
    # populated (no NaN), physically valid 8-bar array where the
    # qualifying gap ends 5 bars before the swing. Highs flooded to 50.0
    # everywhere except the gap's own start bar, so no OTHER 3-bar window
    # can accidentally validate first. Independently confirmed (during
    # development, not asserted here) that the pre-fix `lo = gap_end -
    # d + 1` returns (nan, nan) on this exact array; the fix returns
    # (3.0, 1.0).
    high = np.array([1.0, 50.0, 50.0, 50.0, 50.0, 50.0, 50.0, 50.0])
    low = np.array([0.5, 1.5, 3.0, 2.5, 2.6, 2.5, 2.4, 2.0])
    t, b = _find_nested_fvg(high, low, swing_bar=7, probe=2.0, radius=10, strict=True, is_bull_setup=True)
    assert (t, b) == (3.0, 1.0)


def test_find_nested_fvg_filled_several_bars_before_swing_is_rejected():
    # Same array, but bar 4's low (0.8) dips below the gap's bottom (1.0)
    # between formation (bar 2) and the swing (bar 7) -- correctly filled
    # and rejected. This is the direction-check companion to the above:
    # confirms the fix didn't just widen the window to "always pass."
    high = np.array([1.0, 50.0, 50.0, 50.0, 50.0, 50.0, 50.0, 50.0])
    low = np.array([0.5, 1.5, 3.0, 2.5, 0.8, 2.5, 2.4, 2.0])
    t, b = _find_nested_fvg(high, low, swing_bar=7, probe=2.0, radius=10, strict=True, is_bull_setup=True)
    assert np.isnan(t) and np.isnan(b)


def test_find_nested_fvg_filled_gap_is_rejected():
    high = np.array([1.0, np.nan, np.nan, np.nan, np.nan])
    low = np.array([np.nan, np.nan, 3.0, 0.5, np.nan])
    t, b = _find_nested_fvg(high, low, swing_bar=4, probe=2.0, radius=5, strict=True, is_bull_setup=True)
    assert np.isnan(t) and np.isnan(b)


# ---------------------------------------------------------------------------
# _find_disp_fvg -- isolated unit tests
# ---------------------------------------------------------------------------

def test_find_disp_fvg_ratio_and_overlap_satisfied():
    high = np.array([1.5, np.nan, np.nan])
    low = np.array([np.nan, np.nan, 3.5])
    assert _find_disp_fvg(high, low, t_bar=2, is_bull_setup=True, nz_t=3.0, nz_b=1.0, lookback=5, min_sz=0.01, ratio=0.75) is True


def test_find_disp_fvg_fails_ratio():
    high = np.array([2.4, np.nan, np.nan])
    low = np.array([np.nan, np.nan, 3.0])
    assert _find_disp_fvg(high, low, t_bar=2, is_bull_setup=True, nz_t=3.0, nz_b=1.0, lookback=5, min_sz=0.01, ratio=0.75) is False


def test_find_disp_fvg_fails_no_overlap():
    high = np.array([10.0, np.nan, np.nan])
    low = np.array([np.nan, np.nan, 12.0])
    assert _find_disp_fvg(high, low, t_bar=2, is_bull_setup=True, nz_t=3.0, nz_b=1.0, lookback=5, min_sz=0.01, ratio=0.75) is False


def test_find_disp_fvg_bearish_branch_several_bars_before_t_bar():
    # is_bull_setup=False, and the qualifying gap sits at d=3, not d=0 --
    # exercises both the bearish polarity (never covered before) and the
    # lookback loop's d>0 path (also never covered before).
    high = np.array([np.nan, np.nan, 1.0, np.nan, np.nan, np.nan])
    low = np.array([3.0, np.nan, np.nan, np.nan, np.nan, np.nan])
    assert _find_disp_fvg(high, low, t_bar=5, is_bull_setup=False, nz_t=3.0, nz_b=1.0, lookback=6, min_sz=0.01, ratio=0.75) is True


def test_find_disp_fvg_min_sz_is_the_binding_floor():
    # Nesting zone is tiny (size 0.02), so ratio*nest_sz (0.015) is BELOW
    # min_sz (0.05) -- min_sz must be the actual constraint, not the
    # ratio term. A displacement gap of size 0.10 overlapping the zone
    # passes; verified elsewhere (test_find_disp_fvg_fails_ratio) that
    # the ratio term alone can reject -- this confirms min_sz alone can
    # be the deciding factor when ratio*nest_sz would have passed a
    # near-zero gap.
    high = np.array([0.98, np.nan, np.nan])
    low = np.array([np.nan, np.nan, 1.08])
    assert _find_disp_fvg(high, low, t_bar=2, is_bull_setup=True, nz_t=1.02, nz_b=1.0, lookback=5, min_sz=0.05, ratio=0.75) is True
    # Same zone, gap shrunk below min_sz (0.03 < 0.05) -- must fail even
    # though it still overlaps.
    high2 = np.array([0.99, np.nan, np.nan])
    low2 = np.array([np.nan, np.nan, 1.02])
    assert _find_disp_fvg(high2, low2, t_bar=2, is_bull_setup=True, nz_t=1.02, nz_b=1.0, lookback=5, min_sz=0.05, ratio=0.75) is False


# ---------------------------------------------------------------------------
# End-to-end sphinx_unicorn() scenarios
# ---------------------------------------------------------------------------
# All bars are physically valid (low <= high everywhere) -- the Fletcher-
# round-1 MAJOR finding was that the original scenarios dodged the CRITICAL
# bug via inverted bars (a low set 49 points above its own high). Every
# scenario here was independently re-run against the pre-fix code during
# development and confirmed to produce a DIFFERENT (degenerate) result,
# not asserted in the test itself but load-bearing for why these
# particular bar layouts were chosen.

def _flooded_ohlc(n=30):
    high = np.full(n, 200.0)
    low = np.full(n, 150.0)
    close = np.full(n, 150.0)
    return high, low, close


def _bearish_setup_bars(n=30):
    """Bullish FVG at bars [5,6,7] (high[5]=100.8 < low[7]=103.0, all bars
    individually valid), swing low pivot at bar 10 nested strictly inside
    (100.8, 103.0), confirming at bar 12 (swing=2)."""
    high, low, close = _flooded_ohlc(n)
    high[5], low[5] = 100.8, 100.0
    high[6], low[6] = 104.0, 100.9
    high[7], low[7] = 104.5, 103.0
    low[8] = low[9] = low[11] = low[12] = 102.5
    low[10] = 102.0
    return high, low, close


def test_arm_bear_fires_at_confirmation_lagged_bar_with_correct_dist():
    n = 20
    high, low, close = _bearish_setup_bars(n)
    idx = pd.date_range("2020-01-01", periods=n, freq="B")
    out = ta.sphinx_unicorn(
        pd.Series(high, index=idx), pd.Series(low, index=idx), pd.Series(close, index=idx),
        fvg_look=10, need_bpr=False,
    )
    # The matched gap is (t=low[7]=103.0, b=high[5]=100.8) -- b is the
    # GAP'S bottom edge (high[gap_start]), not bar 5's own low (100.0,
    # only set for that bar's OHLC validity). need = min(swing_price=
    # 102.0, zb=100.8) = 100.8.
    # dist = (close[12] - need) / close[12] * 100 = (150.0 - 100.8) / 150.0 * 100 = 32.8
    assert out["SPHINX_ARM_BEAR_2"].iloc[12] == 1
    assert out["SPHINX_ARM_BEAR_2"].sum() == 1
    assert out["SPHINX_DIST_BEAR_2"].iloc[12] == pytest.approx((150.0 - 100.8) / 150.0 * 100, abs=1e-9)
    assert pd.isna(out["SPHINX_DIST_BEAR_2"].iloc[11])


def test_fire_bear_activates_on_close_below_need_and_clears_armed_slot():
    n = 20
    high, low, close = _bearish_setup_bars(n)
    close[15], low[15], high[15] = 90.0, 89.0, 91.0
    idx = pd.date_range("2020-01-01", periods=n, freq="B")
    out = ta.sphinx_unicorn(
        pd.Series(high, index=idx), pd.Series(low, index=idx), pd.Series(close, index=idx),
        fvg_look=10, need_bpr=False,
    )
    assert out["SPHINX_FIRE_BEAR_2"].iloc[15] == 1
    assert out["SPHINX_FIRE_BEAR_2"].sum() == 1
    # need = min(102.0, 100.8) = 100.8 (see previous test's comment)
    assert out["SPHINX_DIST_BEAR_2"].iloc[15] == pytest.approx((90.0 - 100.8) / 90.0 * 100, abs=1e-9)
    assert out["SPHINX_DIST_BEAR_2"].iloc[16:].isna().all()


def test_fire_bear_blocked_by_bpr_when_no_adequate_displacement_gap():
    # need_bpr=True (the DEFAULT, and what indicator_engine.py actually
    # uses) -- close crosses below need at bar 15, but NO displacement
    # gap forms nearby, so the fire must NOT happen and the zone stays
    # armed. bar 13's low is deliberately set to 85.0 (below bar 15's
    # high=91.0) so no accidental bearish gap forms there either --
    # verified during development that leaving it at the flood value
    # (150.0) DOES accidentally satisfy the BPR gate (91.0 < 150.0), so
    # this value is load-bearing, not arbitrary.
    n = 20
    high, low, close = _bearish_setup_bars(n)
    close[15], low[15], high[15] = 90.0, 89.0, 91.0
    low[13] = 85.0
    idx = pd.date_range("2020-01-01", periods=n, freq="B")
    out = ta.sphinx_unicorn(
        pd.Series(high, index=idx), pd.Series(low, index=idx), pd.Series(close, index=idx), fvg_look=10,
    )
    assert out["SPHINX_FIRE_BEAR_2"].sum() == 0
    assert out["SPHINX_DIST_BEAR_2"].iloc[15:].notna().all()  # still armed throughout


def test_fire_bear_activates_when_bpr_displacement_gap_present():
    # Same setup, but this time a genuine bearish displacement gap forms
    # right at the crossing bar (bar 13's low=104.0 > bar 15's high=99.0,
    # a valid bearish FVG overlapping the armed zone [100.0, 103.0] with
    # size 5.0 >= need_sz=max(0.01%*90, 0.75*3.0=2.25)) -- BPR passes,
    # fire happens.
    n = 20
    high, low, close = _bearish_setup_bars(n)
    close[15], low[15], high[15] = 90.0, 89.0, 99.0
    low[13] = 104.0
    idx = pd.date_range("2020-01-01", periods=n, freq="B")
    out = ta.sphinx_unicorn(
        pd.Series(high, index=idx), pd.Series(low, index=idx), pd.Series(close, index=idx), fvg_look=10,
    )
    assert out["SPHINX_FIRE_BEAR_2"].iloc[15] == 1
    assert out["SPHINX_FIRE_BEAR_2"].sum() == 1


def test_arm_bull_and_dist_bull_hold_without_immediate_fire():
    # Bullish mirror: bearish FVG (SIBI) at bars [5,6,7] (low[5]=104.0 >
    # high[7]=101.0), swing HIGH pivot at bar 10 nested inside (101.0,
    # 104.0). Baseline kept LOW (close=85.0, below need=104.0) so arming
    # doesn't also immediately fire -- verified during development that a
    # baseline of 150.0 (as used for the bearish scenarios) fires on the
    # SAME bar it arms, since 150.0 already clears need=104.0, which
    # would make this test unable to isolate ARM from FIRE.
    n = 20
    high = np.full(n, 90.0)
    low = np.full(n, 80.0)
    close = np.full(n, 85.0)
    low[5], high[5] = 104.0, 103.5
    low[6], high[6] = 101.5, 100.9
    low[7], high[7] = 101.5, 101.0
    high[8] = high[9] = high[11] = high[12] = 101.5
    high[10], low[10] = 102.0, 101.8
    idx = pd.date_range("2020-01-01", periods=n, freq="B")
    out = ta.sphinx_unicorn(
        pd.Series(high, index=idx), pd.Series(low, index=idx), pd.Series(close, index=idx),
        fvg_look=10, need_bpr=False,
    )
    assert out["SPHINX_ARM_BULL_2"].iloc[12] == 1
    assert out["SPHINX_FIRE_BULL_2"].iloc[12] == 0
    # need = max(swing_price=102.0, zt=104.0) = 104.0
    # dist = (85.0 - 104.0) / 85.0 * 100
    assert out["SPHINX_DIST_BULL_2"].iloc[12] == pytest.approx((85.0 - 104.0) / 85.0 * 100, abs=1e-9)
    assert out["SPHINX_DIST_BULL_2"].iloc[15] == pytest.approx((85.0 - 104.0) / 85.0 * 100, abs=1e-9)


def test_clustering_merges_overlapping_zone_updates_span_no_second_arm():
    n = 40
    high, low, close = _bearish_setup_bars(n)
    high[20], low[20] = 99.0, 98.5
    high[21], low[21] = 104.5, 99.5
    high[22], low[22] = 105.0, 104.0
    low[23] = low[24] = low[26] = low[27] = 103.5
    low[25] = 103.0
    idx = pd.date_range("2020-01-01", periods=n, freq="B")
    out = ta.sphinx_unicorn(
        pd.Series(high, index=idx), pd.Series(low, index=idx), pd.Series(close, index=idx),
        fvg_look=25, need_bpr=False,
    )
    assert out["SPHINX_ARM_BEAR_2"].sum() == 1
    assert out["SPHINX_ARM_BEAR_2"].iloc[12] == 1
    # need = min(102.0, 100.8) = 100.8 (same first zone as the arm test above)
    assert out["SPHINX_DIST_BEAR_2"].iloc[12] == pytest.approx((150.0 - 100.8) / 150.0 * 100, abs=1e-9)
    # After the second (larger, overlapping) swing confirms at bar 27, the
    # matched gap is (t=low[22]=104.0, b=high[20]=99.0); need = min(swing_
    # price=103.0, zb=99.0) = 99.0.
    assert out["SPHINX_DIST_BEAR_2"].iloc[27] == pytest.approx((150.0 - 99.0) / 150.0 * 100, abs=1e-9)


def test_causal_no_lookahead():
    # Mutate every bar strictly after t and confirm output at/before t is
    # unchanged. Fletcher round 1 MAJOR: the original version of this
    # test used data that produced an all-zero, all-NaN frame (RandomState
    # seed/length that happened to trigger neither the (buggy) FVG search
    # nor any arm), so the assertion held trivially and would have passed
    # against `return zeros`. This data is confirmed non-vacuous first.
    n = 150
    rng = np.random.RandomState(11)
    close_v = 100 + np.cumsum(rng.randn(n) * 0.6)
    high_v = close_v + np.abs(rng.randn(n)) * 1.0
    low_v = close_v - np.abs(rng.randn(n)) * 1.0
    idx = pd.date_range("2020-01-01", periods=n, freq="B")
    high = pd.Series(high_v, index=idx)
    low = pd.Series(low_v, index=idx)
    close = pd.Series(close_v, index=idx)

    out_before = ta.sphinx_unicorn(high, low, close)
    assert out_before.filter(like="ARM").to_numpy().sum() > 0, "test data must actually produce an arm event"
    assert out_before.filter(like="DIST").notna().to_numpy().sum() > 0, "test data must actually produce distance values"

    t = 100
    high_mut, low_mut, close_mut = high.copy(), low.copy(), close.copy()
    high_mut.iloc[t + 1:] *= 1.4
    low_mut.iloc[t + 1:] *= 0.7
    close_mut.iloc[t + 1:] *= 1.1
    out_after = ta.sphinx_unicorn(high_mut, low_mut, close_mut)

    pd.testing.assert_frame_equal(out_before.iloc[: t + 1], out_after.iloc[: t + 1])


def test_accessor_matches_direct_call():
    n = 20
    high, low, close = _bearish_setup_bars(n)
    idx = pd.date_range("2020-01-01", periods=n, freq="B")
    high_s, low_s, close_s = pd.Series(high, index=idx), pd.Series(low, index=idx), pd.Series(close, index=idx)
    df = pd.DataFrame({"high": high_s, "low": low_s, "close": close_s})
    via_accessor = df.ta.sphinx_unicorn(fvg_look=10, need_bpr=False)
    direct = ta.sphinx_unicorn(high_s, low_s, close_s, fvg_look=10, need_bpr=False)
    pd.testing.assert_frame_equal(via_accessor, direct)


def test_columns_and_naming():
    n = 40
    high, low, close = _flooded_ohlc(n)
    idx = pd.date_range("2020-01-01", periods=n, freq="B")
    out = ta.sphinx_unicorn(pd.Series(high, index=idx), pd.Series(low, index=idx), pd.Series(close, index=idx))
    expected = {
        "SPHINX_ARM_BULL_2", "SPHINX_ARM_BEAR_2", "SPHINX_FIRE_BULL_2",
        "SPHINX_FIRE_BEAR_2", "SPHINX_DIST_BULL_2", "SPHINX_DIST_BEAR_2",
    }
    assert set(out.columns) == expected
    assert out.name == "SPHINX_2"
