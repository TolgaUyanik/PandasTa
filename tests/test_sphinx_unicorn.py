# tests/test_sphinx_unicorn.py
"""sphinx_unicorn -- SMC/ICT "unicorn" (swing nested in an opposing-polarity
FVG, activates on displacement + optional BPR) (TVPTA-6, ported from
"Sphinx Unicorn - FVG Breaker Nesting Model"). Self-contained on synthetic
data.

Reachability tests `import pandas_ta`, NOT `importlib.util.spec_from_file_
location` (see TODO.md TVPTA-3(c)).

Test strategy (Fletcher lesson from the WnzgKfOS/har_park port, applied
proactively here): the helper functions (`_find_nested_fvg`,
`_find_disp_fvg`) are tested in FULL ISOLATION first, against hand-picked
arrays with every other bar set far enough away (NaN or flooded) that no
accidental gap can confound the result -- each isolated case's expected
output is computed by hand in the test comment, not re-derived from the
implementation. The end-to-end `sphinx_unicorn()` scenarios below were
built and their expected values confirmed by direct execution during
development (documented per scenario), then hand-verified against the
`need`/`dist` formula independently -- not just asserted because "that's
what the function returned."
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
    # Bars 0,1,2 form the ONLY possible gap: high[0]=1.0 < low[2]=3.0.
    # Every other array position is NaN, so no other candidate can match.
    # probe=2.0 sits strictly inside (1.0, 3.0).
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


def test_find_nested_fvg_filled_gap_is_rejected():
    # Same gap as above, but bar 3's low (0.5) dips below the gap's bottom
    # (1.0) between formation (bar 2) and the swing bar (4) -- the gap is
    # "filled" and must not match even though probe still nests inside it.
    high = np.array([1.0, np.nan, np.nan, np.nan, np.nan])
    low = np.array([np.nan, np.nan, 3.0, 0.5, np.nan])
    t, b = _find_nested_fvg(high, low, swing_bar=4, probe=2.0, radius=5, strict=True, is_bull_setup=True)
    assert np.isnan(t) and np.isnan(b)


def test_find_nested_fvg_bearish_mirror():
    # Bearish FVG: low[0]=3.0 > high[2]=1.0, range (bot=1.0, top=3.0).
    high = np.array([np.nan, np.nan, 1.0, np.nan, np.nan])
    low = np.array([3.0, np.nan, np.nan, np.nan, np.nan])
    t, b = _find_nested_fvg(high, low, swing_bar=4, probe=2.0, radius=5, strict=True, is_bull_setup=False)
    assert (t, b) == (3.0, 1.0)


def test_find_nested_fvg_nearest_first_not_farthest():
    # Two valid candidate gaps: a nearer one (bars 2,3,4: high[2]=1.2 <
    # low[4]=2.8) and a farther one (bars 0,1,2: high[0]=1.0 < low[2]=3.0).
    # probe=2.0 nests inside BOTH. The search must return the NEARER one
    # (radius counts outward from the swing bar).
    high = np.array([1.0, np.nan, 1.2, np.nan, np.nan])
    low = np.array([np.nan, np.nan, np.nan, np.nan, 2.8])
    t, b = _find_nested_fvg(high, low, swing_bar=4, probe=2.0, radius=5, strict=True, is_bull_setup=True)
    assert (t, b) == (2.8, 1.2)


# ---------------------------------------------------------------------------
# _find_disp_fvg -- isolated unit tests
# ---------------------------------------------------------------------------

def test_find_disp_fvg_ratio_and_overlap_satisfied():
    # Nesting zone [1.0, 3.0] (size 2.0). Displacement gap at bars 0,1,2:
    # high[0]=1.5 < low[2]=3.5 -> range (1.5, 3.5), size 2.0, overlaps
    # [1.0,3.0] by [1.5,3.0]=1.5 > 0. need_sz = max(0.01, 0.75*2.0) = 1.5;
    # gap size 2.0 >= 1.5 -> passes.
    high = np.array([1.5, np.nan, np.nan])
    low = np.array([np.nan, np.nan, 3.5])
    assert _find_disp_fvg(high, low, t_bar=2, is_bull_setup=True, nz_t=3.0, nz_b=1.0, lookback=5, min_sz=0.01, ratio=0.75) is True


def test_find_disp_fvg_fails_ratio():
    # Same nesting zone, but the displacement gap is only 0.6 wide
    # (high=2.4, low=3.0) -- below need_sz=1.5.
    high = np.array([2.4, np.nan, np.nan])
    low = np.array([np.nan, np.nan, 3.0])
    assert _find_disp_fvg(high, low, t_bar=2, is_bull_setup=True, nz_t=3.0, nz_b=1.0, lookback=5, min_sz=0.01, ratio=0.75) is False


def test_find_disp_fvg_fails_no_overlap():
    # Displacement gap (10.0, 12.0) does not overlap nesting zone (1.0, 3.0) at all.
    high = np.array([10.0, np.nan, np.nan])
    low = np.array([np.nan, np.nan, 12.0])
    assert _find_disp_fvg(high, low, t_bar=2, is_bull_setup=True, nz_t=3.0, nz_b=1.0, lookback=5, min_sz=0.01, ratio=0.75) is False


# ---------------------------------------------------------------------------
# End-to-end sphinx_unicorn() scenarios
# ---------------------------------------------------------------------------
# Construction technique: highs flooded to 200.0 and baseline low/close set
# far above any gap zone (150.0) everywhere except deliberately engineered
# bars, so no accidental gap or fill can form -- verified by direct
# execution during development that these scenarios produce exactly one
# gap and one swing, not an incidental extra match.

def _flooded_ohlc(n=30):
    high = np.full(n, 200.0)
    low = np.full(n, 150.0)
    close = np.full(n, 150.0)
    return high, low, close


def test_arm_bear_fires_at_confirmation_lagged_bar_with_correct_dist():
    # Bullish FVG at bars [5,6,7]: high[5]=100.8 < low[7]=103.0.
    # Swing low pivot at bar 10 (low=102.0, strict unique min of the
    # 5-bar window [8..12], all neighbors raised to 102.5) nests strictly
    # inside (100.8, 103.0). Pivot (swing=2) confirms at bar 10+2=12.
    n = 20
    high, low, close = _flooded_ohlc(n)
    high[5] = 100.8
    low[7] = 103.0
    low[8] = low[9] = low[11] = low[12] = 102.5
    low[10] = 102.0
    idx = pd.date_range("2020-01-01", periods=n, freq="B")
    out = ta.sphinx_unicorn(
        pd.Series(high, index=idx), pd.Series(low, index=idx), pd.Series(close, index=idx),
        fvg_look=10, need_bpr=False,
    )
    # need_disp=True (default): need = min(swing_price=102.0, zb=100.8) = 100.8
    # dist = (close[12] - need) / close[12] * 100 = (150.0 - 100.8) / 150.0 * 100 = 32.8
    assert out["SPHINX_ARM_BEAR_2"].iloc[12] == 1
    assert out["SPHINX_ARM_BEAR_2"].sum() == 1
    assert out["SPHINX_DIST_BEAR_2"].iloc[12] == pytest.approx(32.8, abs=1e-9)
    assert out["SPHINX_DIST_BEAR_2"].iloc[11] != out["SPHINX_DIST_BEAR_2"].iloc[11]  # NaN before arming


def test_fire_bear_activates_on_close_below_need_and_clears_armed_slot():
    n = 20
    high, low, close = _flooded_ohlc(n)
    high[5] = 100.8
    low[7] = 103.0
    low[8] = low[9] = low[11] = low[12] = 102.5
    low[10] = 102.0
    # Push close below need=100.8 at bar 15.
    close[15] = 90.0
    low[15] = 90.0
    high[15] = 91.0
    idx = pd.date_range("2020-01-01", periods=n, freq="B")
    out = ta.sphinx_unicorn(
        pd.Series(high, index=idx), pd.Series(low, index=idx), pd.Series(close, index=idx),
        fvg_look=10, need_bpr=False,
    )
    assert out["SPHINX_FIRE_BEAR_2"].iloc[15] == 1
    assert out["SPHINX_FIRE_BEAR_2"].sum() == 1
    # dist = (90.0 - 100.8) / 90.0 * 100 = -12.0
    assert out["SPHINX_DIST_BEAR_2"].iloc[15] == pytest.approx(-12.0, abs=1e-9)
    # armed slot cleared after firing -- no zone watched afterward.
    assert out["SPHINX_DIST_BEAR_2"].iloc[16:].isna().all()


def test_clustering_merges_overlapping_zone_updates_span_no_second_arm():
    # Second bullish FVG (bars 20,21,22: high[20]=99.0 < low[22]=104.0,
    # span 5.0) OVERLAPS the first armed zone's range (100.8, 103.0) --
    # must merge into the existing cluster (span grows, watched swing
    # updates), NOT create a second arm event.
    n = 40
    high, low, close = _flooded_ohlc(n)
    high[5] = 100.8
    low[7] = 103.0
    low[8] = low[9] = low[11] = low[12] = 102.5
    low[10] = 102.0
    high[20] = 99.0
    low[22] = 104.0
    low[23] = low[24] = low[26] = low[27] = 103.5
    low[25] = 103.0
    idx = pd.date_range("2020-01-01", periods=n, freq="B")
    out = ta.sphinx_unicorn(
        pd.Series(high, index=idx), pd.Series(low, index=idx), pd.Series(close, index=idx),
        fvg_look=25, need_bpr=False,
    )
    assert out["SPHINX_ARM_BEAR_2"].sum() == 1  # only the first swing armed a NEW zone
    assert out["SPHINX_ARM_BEAR_2"].iloc[12] == 1
    assert out["SPHINX_DIST_BEAR_2"].iloc[12] == pytest.approx(32.8, abs=1e-9)
    # After the second swing confirms (bar 25+2=27), the span/watched swing
    # updated: need = min(103.0, 99.0) = 99.0, dist = (150-99)/150*100 = 34.0
    assert out["SPHINX_DIST_BEAR_2"].iloc[27] == pytest.approx(34.0, abs=1e-9)


def test_causal_no_lookahead():
    # Mutate every bar strictly after t and confirm output at/before t is
    # unchanged -- catches a look-ahead bug in the pivot confirmation lag,
    # the FVG search, or the activation check, without sharing any
    # implementation logic with sphinx_unicorn() itself.
    n = 60
    rng = np.random.RandomState(11)
    close_v = 100 + np.cumsum(rng.randn(n) * 0.6)
    high_v = close_v + np.abs(rng.randn(n)) * 1.0
    low_v = close_v - np.abs(rng.randn(n)) * 1.0
    idx = pd.date_range("2020-01-01", periods=n, freq="B")
    high = pd.Series(high_v, index=idx)
    low = pd.Series(low_v, index=idx)
    close = pd.Series(close_v, index=idx)

    out_before = ta.sphinx_unicorn(high, low, close)

    t = 40
    high_mut, low_mut, close_mut = high.copy(), low.copy(), close.copy()
    high_mut.iloc[t + 1:] *= 1.4
    low_mut.iloc[t + 1:] *= 0.7
    close_mut.iloc[t + 1:] *= 1.1
    out_after = ta.sphinx_unicorn(high_mut, low_mut, close_mut)

    pd.testing.assert_frame_equal(out_before.iloc[: t + 1], out_after.iloc[: t + 1])


def test_accessor_matches_direct_call():
    n = 40
    high, low, close = _flooded_ohlc(n)
    high[5] = 100.8
    low[7] = 103.0
    low[8] = low[9] = low[11] = low[12] = 102.5
    low[10] = 102.0
    idx = pd.date_range("2020-01-01", periods=n, freq="B")
    high_s, low_s, close_s = pd.Series(high, index=idx), pd.Series(low, index=idx), pd.Series(close, index=idx)
    df = pd.DataFrame({"high": high_s, "low": low_s, "close": close_s})
    via_accessor = df.ta.sphinx_unicorn(fvg_look=10, need_bpr=False)
    direct = ta.sphinx_unicorn(high_s, low_s, close_s, fvg_look=10, need_bpr=False)
    pd.testing.assert_frame_equal(via_accessor, direct)


def test_columns_and_naming():
    # min_len = 2*swing + fvg_look + 5 = 29 at defaults -- needs enough
    # history for verify_series not to reject it.
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
