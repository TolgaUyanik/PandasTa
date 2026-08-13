# tests/test_fvg_sweep_magnet.py
"""fvg_sweep_magnet (FSME) -- displacement-validated FVG zones become
scored magnet targets after a liquidity-pivot sweep (TVPTA-6, ported from
"FVG Sweep Magnet Engine [PhenLabs]"). Self-contained on synthetic data.

Reachability tests `import pandas_ta` (`.context`), NOT `importlib.util.
spec_from_file_location` (see TODO.md TVPTA-3(c)).

All end-to-end scenarios below are built on physically valid OHLC (low <=
min(open, close) and max(open, close) <= high on every bar, not just
low <= high) -- every scenario builder asserts this full invariant at
construction time, per this project's documented history of tests
dodging bugs via impossible bars (see tests/test_sphinx_unicorn.py's and
tests/test_rejection_blocks.py's module docstrings for the precedent
incidents this guards against).

ATR strategy: `atr_len=2` throughout (not the 14 default) so ATR warms up
fast, and every scenario's exact pass/fail thresholds (gap size,
displacement body, sweep wick ratio, CE distance) are derived from the
SAME `pandas_ta.volatility.atr.atr` call the module itself uses -- NOT
hand-typed literals -- since ATR's recursive (RMA-style) warmup makes the
exact numeric value depend on the full constructed series (same
discipline `tests/test_rejection_blocks.py` established). Every scenario
below was additionally cross-checked by running `fvg_sweep_magnet` itself
and reading its actual output before being written as an assertion here,
not assumed -- one early draft of the multi-zone nearest-selection
scenario (`test_ce_dist_picks_nearer_zone_among_two_live_candidates`)
guessed a "nearby" distance from eyeballed price levels alone and was off
by nearly 40x (predicted ATR ~2, actual ATR ~38, because two large
level-jumps a few bars apart compound hard under a length-2 RMA) --
recomputing ATR directly from the constructed series, as this file now
does throughout, caught it immediately.

Most scenarios use `require_disp=False, min_gap_atr=0.0, min_score=0` (a
"trivial-qualification" mode) plus a permanent, always-in-gap FVG zone
built from a two-bar low-price (or high-price) regime followed by a
reversion to the baseline flooded range -- this decouples sweep/pivot/
magnet-window/liq_keep testing from the FVG creation-gate's own
thresholds, which get their own dedicated, non-trivial-mode scenarios.
"""
import math

import numpy as np
import pandas as pd
import pytest

from .context import pandas_ta as ta
from pandas_ta.volatility.atr import atr as _atr_fn
from pandas_ta.trend.fvg_sweep_magnet import (
    _confirm_strict_pivots, _validated_int, _validated_float, _validated_bool,
    _safe_div, _clamp, _score,
)


def _idx(n):
    return pd.date_range("2020-01-01", periods=n, freq="B")


def _valid_ohlc(O, H, L, C):
    O, H, L, C = np.asarray(O), np.asarray(H), np.asarray(L), np.asarray(C)
    assert (L <= np.minimum(O, C)).all() and (np.maximum(O, C) <= H).all(), \
        "construction check: every bar must satisfy low <= min(open,close) and max(open,close) <= high"


def _series(a, idx):
    return pd.Series(np.asarray(a, dtype=float), index=idx)


def _flooded(n, o=100.0, h=101.0, l=99.0, c=100.0):
    return (np.full(n, o), np.full(n, h), np.full(n, l), np.full(n, c))


def _run(O, H, L, C, volume=None, **kwargs):
    _valid_ohlc(O, H, L, C)
    idx = _idx(len(O))
    if volume is None:
        volume = np.full(len(O), 1e6)
    return ta.fvg_sweep_magnet(_series(O, idx), _series(H, idx), _series(L, idx), _series(C, idx),
                                _series(volume, idx), **kwargs)


# ---------------------------------------------------------------------------
# _confirm_strict_pivots -- isolated unit tests (duplicated per-file, same
# convention as liquidity_sweep.py / rejection_blocks.py / sr_force.py's
# own copies)
# ---------------------------------------------------------------------------

def test_confirm_strict_pivots_high_unique_extreme():
    vals = pd.Series([1.0, 2.0, 5.0, 2.0, 1.0])
    out = _confirm_strict_pivots(vals, 2, 2, is_high=True)
    assert out[4] == 5.0
    assert np.isnan(out[:4]).all()


def test_confirm_strict_pivots_tie_rejects():
    vals = pd.Series([1.0, 5.0, 3.0, 5.0, 1.0])
    out = _confirm_strict_pivots(vals, 2, 2, is_high=True)
    assert np.isnan(out).all()


def test_confirm_strict_pivots_low_mirror():
    vals = pd.Series([5.0, 4.0, 1.0, 4.0, 5.0])
    out = _confirm_strict_pivots(vals, 2, 2, is_high=False)
    assert out[4] == 1.0


# ---------------------------------------------------------------------------
# _validated_int / _validated_float / _validated_bool -- nan/inf/type
# discipline
# ---------------------------------------------------------------------------

def test_validated_int_none_returns_default():
    assert _validated_int(None, 7, "x") == 7


def test_validated_int_rejects_nan():
    with pytest.raises(ValueError, match="NaN"):
        _validated_int(float("nan"), 7, "x")


def test_validated_int_rejects_inf():
    with pytest.raises(ValueError, match="inf"):
        _validated_int(float("inf"), 7, "x")
    with pytest.raises(ValueError, match="inf"):
        _validated_int(float("-inf"), 7, "x")


def test_validated_int_rejects_non_integral_float():
    with pytest.raises(ValueError, match="non-integral"):
        _validated_int(3.7, 7, "x")


def test_validated_int_accepts_whole_float():
    assert _validated_int(4.0, 7, "x") == 4


def test_validated_int_rejects_non_positive():
    with pytest.raises(ValueError):
        _validated_int(0, 7, "x")
    with pytest.raises(ValueError):
        _validated_int(-1, 7, "x")


def test_validated_int_rejects_bool():
    with pytest.raises(ValueError):
        _validated_int(True, 7, "x")


def test_validated_int_nonpositive_allows_zero():
    # min_score uses positive=False -- 0 legitimately means "no score
    # floor, every live in-gap zone qualifies."
    assert _validated_int(0, 5, "min_score", positive=False) == 0


def test_validated_int_nonpositive_rejects_negative():
    with pytest.raises(ValueError):
        _validated_int(-1, 5, "min_score", positive=False)


def test_validated_float_none_returns_default():
    assert _validated_float(None, 1.25, "x") == 1.25


def test_validated_float_rejects_nan_and_inf():
    with pytest.raises(ValueError, match="NaN"):
        _validated_float(float("nan"), 1.25, "x")
    with pytest.raises(ValueError, match="inf"):
        _validated_float(float("inf"), 1.25, "x")
    with pytest.raises(ValueError, match="inf"):
        _validated_float(float("-inf"), 1.25, "x")


def test_validated_float_rejects_negative():
    with pytest.raises(ValueError):
        _validated_float(-0.1, 1.25, "x")


def test_validated_float_accepts_zero():
    assert _validated_float(0.0, 1.25, "x") == 0.0


def test_validated_bool_none_returns_default():
    assert _validated_bool(None, True, "require_disp") is True


def test_validated_bool_accepts_true_false():
    assert _validated_bool(True, False, "x") is True
    assert _validated_bool(False, True, "x") is False


def test_validated_bool_accepts_numpy_bool():
    assert _validated_bool(np.bool_(True), False, "x") is True


def test_validated_bool_rejects_int():
    with pytest.raises(ValueError, match="bool"):
        _validated_bool(1, True, "x")


def test_validated_bool_rejects_string():
    with pytest.raises(ValueError, match="bool"):
        _validated_bool("true", True, "x")


# ---------------------------------------------------------------------------
# _safe_div / _clamp / _score -- isolated unit tests, hand-derived against
# the source's f_safeDiv/f_clamp/f_score
# ---------------------------------------------------------------------------

def test_safe_div_zero_denominator_returns_zero():
    assert _safe_div(10.0, 0.0) == 0.0


def test_safe_div_nan_denominator_returns_zero():
    assert _safe_div(10.0, float("nan")) == 0.0


def test_safe_div_ordinary():
    assert _safe_div(10.0, 5.0) == 2.0


def test_clamp_above_hi_and_below_lo_and_inside():
    assert _clamp(5.0, 0.0, 3.0) == 3.0
    assert _clamp(-5.0, 0.0, 3.0) == 0.0
    assert _clamp(1.0, 0.0, 3.0) == 1.0


def test_score_hand_derived_normal_case():
    # gap_size=10, disp_body=atr_t=5 (a self-ratio -> dispPts fixed 2.0,
    # see module docstring's "score quirk"), age=0, vol_ratio=1.0.
    # gapPts=clamp(10/5*3.2,0,3)=clamp(6.4,0,3)=3.0
    # dispPts=clamp(5/5*2.0,0,3)=2.0
    # agePts=clamp(3-0/40,0,2)=2.0
    # volPts=clamp(1.0*1.2,0,2)=1.2
    # total=8.2 -> round-half-up -> 8
    assert _score(10.0, 5.0, 0.0, 1.0, 5.0) == 8


def test_score_zero_atr_safe_divides_to_zero_not_crash():
    # atr_t=0 -> gapPts=safeDiv(10,0)=0 -> 0; dispPts=safeDiv(0,0)=0 -> 0
    # (b==0.0 branch, not a ZeroDivisionError); agePts=2.0; volPts=1.2
    # total=3.2 -> round -> 3
    assert _score(10.0, 0.0, 0.0, 1.0, 0.0) == 3


def test_score_caps_at_ten():
    # every term saturates its own [0,3]/[0,3]/[0,2]/[0,2] cap -> sum
    # clamped to 10 before rounding.
    assert _score(1000.0, 1000.0, 0.0, 10.0, 1.0) == 10


def test_score_hand_derived_high_age_low_vol():
    # gapPts=clamp(0.5/2*3.2,0,3)=clamp(0.8,0,3)=0.8
    # dispPts=clamp(1.25/2*2.0,0,3)=clamp(1.25,0,3)=1.25
    # agePts=clamp(3-60/40,0,2)=clamp(1.5,0,2)=1.5
    # volPts=clamp(0.0*1.2,0,2)=0.0
    # total=3.55 -> round-half-up -> 4
    assert _score(0.5, 1.25, 60.0, 0.0, 2.0) == 4


# ---------------------------------------------------------------------------
# FVG creation gate -- gap size / displacement filters
# ---------------------------------------------------------------------------
# Shared displacement scenario: baseline flooded (100/101/99/100) through
# bar 23; displacement (middle) candle at bar 24 (strong bullish body,
# O=100,C=110); gap-confirming bar at bar 25 (O=112,H=115,L=112,C=114,
# gap size = low[25]-high[23] = 112-101 = 11, mid_body = |C24-O24| = 10).
# atr_len=2, pivot_len=2 throughout.

def _disp_scenario(n=30, bearish_mid=False):
    O, H, L, C = _flooded(n)
    if not bearish_mid:
        O[24], H[24], L[24], C[24] = 100.0, 110.0, 100.0, 110.0
    else:
        O[24], H[24], L[24], C[24] = 110.0, 110.0, 100.0, 100.0
    O[25], H[25], L[25], C[25] = 112.0, 115.0, 112.0, 114.0
    return O, H, L, C


def test_gap_size_gate_fails_below_min_gap_atr():
    O, H, L, C = _disp_scenario()
    out = _run(O, H, L, C, atr_len=2, pivot_len=2, min_gap_atr=3.0, require_disp=False, min_score=0)
    assert np.isnan(out["FSME_CE_DIST_BULL_2"].iloc[25])


def test_gap_size_gate_passes_default_threshold():
    O, H, L, C = _disp_scenario()
    out = _run(O, H, L, C, atr_len=2, pivot_len=2, min_gap_atr=0.25, require_disp=False, min_score=0)
    assert not np.isnan(out["FSME_CE_DIST_BULL_2"].iloc[25])


def test_displacement_gate_fails_insufficient_body():
    O, H, L, C = _disp_scenario()
    out = _run(O, H, L, C, atr_len=2, pivot_len=2, min_gap_atr=0.0, disp_atr_mult=2.0,
               require_disp=True, min_score=0)
    assert np.isnan(out["FSME_CE_DIST_BULL_2"].iloc[25])


def test_displacement_gate_passes_sufficient_body():
    O, H, L, C = _disp_scenario()
    out = _run(O, H, L, C, atr_len=2, pivot_len=2, min_gap_atr=0.0, disp_atr_mult=1.0,
               require_disp=True, min_score=0)
    assert not np.isnan(out["FSME_CE_DIST_BULL_2"].iloc[25])


def test_displacement_gate_fails_wrong_direction_candle():
    # Same gap, same body magnitude -- but the middle candle is BEARISH
    # (close < open), so midBull is false and disp_ok_bull fails
    # regardless of body size.
    O, H, L, C = _disp_scenario(bearish_mid=True)
    out = _run(O, H, L, C, atr_len=2, pivot_len=2, min_gap_atr=0.0, disp_atr_mult=1.25,
               require_disp=True, min_score=0)
    assert np.isnan(out["FSME_CE_DIST_BULL_2"].iloc[25])


def test_require_disp_false_bypasses_wrong_direction_candle():
    O, H, L, C = _disp_scenario(bearish_mid=True)
    out = _run(O, H, L, C, atr_len=2, pivot_len=2, min_gap_atr=0.0, disp_atr_mult=1.25,
               require_disp=False, min_score=0)
    assert not np.isnan(out["FSME_CE_DIST_BULL_2"].iloc[25])


def test_score_at_creation_matches_maintain_formula():
    # Independently verified: gap_size=11, atr[25] from a direct atr()
    # call, dispBody passed as atr itself (score quirk), age=0,
    # vol_ratio=1.0 (constant 1e6 volume, fully warmed 20-SMA by bar 25).
    O, H, L, C = _disp_scenario()
    idx = _idx(len(O))
    a25 = _atr_fn(_series(H, idx), _series(L, idx), _series(C, idx), length=2).iloc[25]
    expected = _score(11.0, a25, 0.0, 1.0, a25)
    out = _run(O, H, L, C, atr_len=2, pivot_len=2, min_score=0)
    assert out["FSME_CE_SCORE_BULL_2"].iloc[25] == float(expected)
    assert expected == 8  # pinned so a future ATR-implementation drift is caught


# ---------------------------------------------------------------------------
# Permanent-zone helper -- a bull (or bear) FVG that stays live and
# in-gap for the whole scenario, used to decouple sweep/pivot/window/
# liq_keep testing from the FVG creation-gate thresholds tested above.
# Bull: bars 0-1 at a LOW flat regime, bar 2+ reverts to the baseline
# flooded range -> low[2] > high[0] fires a bull gap with top=low[2]=99,
# bot=high[0]=10 -- every later baseline bar has low==99 (<=99) and
# high==101 (>=10), so in_gap stays true and close never drops below
# bot=10, so it's never filled. Bear is the mirror (bars 0-1 HIGH).
# ---------------------------------------------------------------------------

def _permanent_bull_base(n):
    O, H, L, C = _flooded(n)
    O[0], H[0], L[0], C[0] = 10.0, 10.0, 10.0, 10.0
    O[1], H[1], L[1], C[1] = 10.0, 10.0, 10.0, 10.0
    return O, H, L, C


def _permanent_bear_base(n):
    O, H, L, C = _flooded(n)
    O[0], H[0], L[0], C[0] = 200.0, 200.0, 200.0, 200.0
    O[1], H[1], L[1], C[1] = 200.0, 200.0, 200.0, 200.0
    return O, H, L, C


_TRIVIAL = dict(require_disp=False, min_gap_atr=0.0, min_score=0)


def test_permanent_bull_zone_ce_dist_populated_from_creation_bar():
    O, H, L, C = _permanent_bull_base(10)
    out = _run(O, H, L, C, atr_len=2, pivot_len=2, **_TRIVIAL)
    assert out["FSME_CE_DIST_BULL_2"].iloc[:2].isna().all()
    assert not np.isnan(out["FSME_CE_DIST_BULL_2"].iloc[2])


def test_permanent_bear_zone_ce_dist_populated_from_creation_bar():
    O, H, L, C = _permanent_bear_base(10)
    out = _run(O, H, L, C, atr_len=2, pivot_len=2, **_TRIVIAL)
    assert out["FSME_CE_DIST_BEAR_2"].iloc[:2].isna().all()
    assert not np.isnan(out["FSME_CE_DIST_BEAR_2"].iloc[2])


# ---------------------------------------------------------------------------
# Filled / expired lifecycle
# ---------------------------------------------------------------------------

def test_filled_kills_zone_on_close_below_bot():
    # From the displacement scenario: zone born bar 25 (top=112,bot=101),
    # survives its own creation bar (close[25]=114 >= bot), then bar 26
    # reverts to baseline (close=100 < bot=101) -> filled, permanently.
    O, H, L, C = _disp_scenario()
    out = _run(O, H, L, C, atr_len=2, pivot_len=2, min_score=0)
    dist = out["FSME_CE_DIST_BULL_2"]
    assert not np.isnan(dist.iloc[25])
    assert dist.iloc[26:].isna().all()


def test_expired_kills_zone_after_max_fvg_age():
    # Permanent-zone construction, but max_fvg_age=5 forces expiry: born
    # bar 2, age=5 at bar 7 (5>5 false, still alive), age=6 at bar 8
    # (6>5 true, expired).
    O, H, L, C = _permanent_bull_base(12)
    out = _run(O, H, L, C, atr_len=2, pivot_len=2, max_fvg_age=5, **_TRIVIAL)
    dist = out["FSME_CE_DIST_BULL_2"]
    assert not np.isnan(dist.iloc[7])
    assert np.isnan(dist.iloc[8])
    assert dist.iloc[8:].isna().all()


# ---------------------------------------------------------------------------
# Combined FIFO pool -- dead zones linger until evicted (module docstring
# quirk): a filled zone does NOT vacate its slot; only a NEW zone's push
# trims the OLDEST slot regardless of live/dead state.
# ---------------------------------------------------------------------------

def _fifo_scenario(n=30):
    # zone1 (bull, permanent): bars 0-1 low regime -> born bar 2,
    # top=99, bot=10.
    O, H, L, C = _permanent_bull_base(n)
    # zone2 (bear, dies quickly): dip at bar 10 (high=61), gap-confirm at
    # bar 12 (high[12]=55 < low[10]=59); bar 13 reverts to baseline
    # (close=100 > top=55) -> filled immediately.
    O[10], H[10], L[10], C[10] = 60.0, 61.0, 59.0, 60.0
    O[12], H[12], L[12], C[12] = 52.0, 55.0, 50.0, 51.0
    # zone3 (bull #2): gap-confirm at bar 22 (low[22]=110 > high[20]=101
    # baseline); its own bot=101 means the very next baseline bar
    # (close=100) fills it again.
    O[22], H[22], L[22], C[22] = 108.0, 112.0, 110.0, 111.0
    return O, H, L, C


def test_dead_zone_lingers_in_pool_until_fifo_evicted():
    # fvg_lookback=2: by bar 22, pool=[zone1(alive), zone2(dead)]; pushing
    # zone3 overflows to 3>2 and evicts INDEX 0 = zone1 -- the ALIVE
    # zone, not the dead one -- because eviction is insertion-order, not
    # liveness-order. At bar 25 (baseline reverted, zone3 already
    # filled), CE_DIST_BULL must be NaN: zone1 (which would still
    # qualify -- baseline low=99<=top=99, close=100>=bot=10 -- if still
    # tracked) was evicted, and zone3 is dead.
    O, H, L, C = _fifo_scenario()
    out_capped = _run(O, H, L, C, atr_len=2, pivot_len=2, fvg_lookback=2, max_fvg_age=200, **_TRIVIAL)
    assert np.isnan(out_capped["FSME_CE_DIST_BULL_2"].iloc[25])

    # Control: with capacity for all 3 zones (fvg_lookback=10), zone1 is
    # NEVER evicted and still reports a real distance at bar 25 -- proving
    # the capped case's NaN above is specifically an eviction effect, not
    # some other coincidental zone-death.
    out_uncapped = _run(O, H, L, C, atr_len=2, pivot_len=2, fvg_lookback=10, max_fvg_age=200, **_TRIVIAL)
    assert not np.isnan(out_uncapped["FSME_CE_DIST_BULL_2"].iloc[25])


# ---------------------------------------------------------------------------
# CE_DIST/CE_SCORE inclusive-boundary tests (the source's own `inGap =
# low <= top and high >= bot` is already inclusive -- reused verbatim as
# this port's own CE candidacy filter, per this batch's gate (d)
# convention). For a BULL zone the bot-side check (high >= bot) is
# structurally guaranteed whenever the zone is live (not filled requires
# close >= bot, and high >= close always) -- so only the TOP-side
# boundary is a genuine, non-degenerate test for bull zones. The mirror
# holds for BEAR zones: the top-side check is structurally guaranteed by
# not-filled, so only the BOT-side boundary is non-degenerate there.
# ---------------------------------------------------------------------------

def test_ce_dist_bull_populated_not_nan_at_low_equals_top_boundary():
    O, H, L, C = _permanent_bull_base(10)
    # top = low[2] = 99 (baseline). Bar 5: low == 99 exactly.
    O[5], H[5], L[5], C[5] = 100.0, 101.0, 99.0, 100.0
    out = _run(O, H, L, C, atr_len=2, pivot_len=2, **_TRIVIAL)
    assert not np.isnan(out["FSME_CE_DIST_BULL_2"].iloc[5])


def test_ce_dist_bull_nan_just_outside_top_boundary():
    O, H, L, C = _permanent_bull_base(10)
    O[5], H[5], L[5], C[5] = 100.0, 101.0, 99.01, 100.0
    out = _run(O, H, L, C, atr_len=2, pivot_len=2, **_TRIVIAL)
    assert np.isnan(out["FSME_CE_DIST_BULL_2"].iloc[5])


def test_ce_dist_bear_populated_not_nan_at_high_equals_bot_boundary():
    O, H, L, C = _permanent_bear_base(10)
    # bot = high[0] = wait -- bot = high[t] at creation bar = high[2] =
    # 101 (baseline). Bar 5: high == 101 exactly, close kept well below
    # top (200) so it can never be "filled" regardless of this boundary.
    O[5], H[5], L[5], C[5] = 100.5, 101.0, 100.0, 100.5
    out = _run(O, H, L, C, atr_len=2, pivot_len=2, **_TRIVIAL)
    assert not np.isnan(out["FSME_CE_DIST_BEAR_2"].iloc[5])


def test_ce_dist_bear_nan_just_outside_bot_boundary():
    O, H, L, C = _permanent_bear_base(10)
    O[5], H[5], L[5], C[5] = 100.49, 100.99, 100.0, 100.49
    out = _run(O, H, L, C, atr_len=2, pivot_len=2, **_TRIVIAL)
    assert np.isnan(out["FSME_CE_DIST_BEAR_2"].iloc[5])


# ---------------------------------------------------------------------------
# CE_DIST/CE_SCORE nearest-zone selection among multiple live candidates
# ---------------------------------------------------------------------------

def test_ce_dist_picks_nearer_zone_among_two_live_candidates():
    # zone A (permanent, top=99,bot=10, mid=54.5) from the bars 0-1 low
    # regime. zone B (top=80,bot=20, mid=50) from a gap at bar 10
    # (high[8]=20, low[10]=80). At bar 12, both are simultaneously live
    # and in-gap (low=55<=80 and <=99; high=65>=20 and >=10; close=62 not
    # below either bot). close=62 is nearer to mid_A(54.5) than mid_B(50)
    # in ATR-normalized terms -- confirmed against a direct atr() call,
    # not assumed (see module docstring for why this exact scenario was
    # first hand-guessed wrong).
    n = 15
    O, H, L, C = _permanent_bull_base(n)
    O[8], H[8], L[8], C[8] = 20.0, 20.0, 19.0, 19.5
    O[10], H[10], L[10], C[10] = 79.0, 81.0, 80.0, 80.5
    O[12], H[12], L[12], C[12] = 60.0, 65.0, 55.0, 62.0

    idx = _idx(n)
    a12 = _atr_fn(_series(H, idx), _series(L, idx), _series(C, idx), length=2).iloc[12]
    dist_a = abs(62.0 - 54.5) / a12
    dist_b = abs(62.0 - 50.0) / a12
    assert dist_a < dist_b, "test construction check: zone A must genuinely be nearer"

    out = _run(O, H, L, C, atr_len=2, pivot_len=2, fvg_lookback=10, **_TRIVIAL)
    assert math.isclose(out["FSME_CE_DIST_BULL_2"].iloc[12], dist_a, rel_tol=1e-9)


# ---------------------------------------------------------------------------
# Liquidity pool FIFO cap (liq_keep) -- per-side, independent of the FVG
# combined pool tested above. A sweep against an EVICTED level must not
# fire; the same construction with a large liq_keep (so nothing is
# evicted) must fire.
# ---------------------------------------------------------------------------

def _liq_keep_scenario(n=30):
    O, H, L, C = _permanent_bull_base(n)
    # SSL pivot low A at bar 6 (value 90), confirms bar 8.
    O[6], H[6], L[6], C[6] = 95.0, 96.0, 90.0, 95.0
    # SSL pivot low B at bar 10 (value 92), confirms bar 12 -- with
    # liq_keep=1, pushing B's confirmation evicts A.
    O[10], H[10], L[10], C[10] = 96.0, 97.0, 92.0, 96.0
    # Bar 20: wicks to 85 and closes at 91 -- would sweep level A (90:
    # low<90, close>90) but NOT level B (92: close=91 < 92). Bullish
    # (close>open), wick ratio (min(90.5,91)-85)/(93-85)=5.5/8=0.6875.
    O[20], H[20], L[20], C[20] = 90.5, 93.0, 85.0, 91.0
    # Bar 22 (sweep_confirm=2 bars after bar 20): bullish confirming
    # candle, inside the permanent zone's gap.
    O[22], H[22], L[22], C[22] = 100.0, 102.0, 99.0, 101.0
    return O, H, L, C


def test_liq_keep_evicted_level_does_not_arm_magnet():
    O, H, L, C = _liq_keep_scenario()
    out = _run(O, H, L, C, atr_len=2, pivot_len=2, liq_keep=1, sweep_wick_mult=0.35,
               sweep_confirm=2, magnet_window=18, **_TRIVIAL)
    assert out["FSME_MAG_BULL_2"].sum() == 0


def test_liq_keep_retained_level_arms_magnet():
    O, H, L, C = _liq_keep_scenario()
    out = _run(O, H, L, C, atr_len=2, pivot_len=2, liq_keep=4, sweep_wick_mult=0.35,
               sweep_confirm=2, magnet_window=18, **_TRIVIAL)
    assert out["FSME_MAG_BULL_2"].iloc[22] == 1
    assert out["FSME_MAG_BULL_2"].sum() == 1


# ---------------------------------------------------------------------------
# Sweep wick-ratio gate
# ---------------------------------------------------------------------------

def test_sweep_wick_ratio_gate_fails_above_actual_ratio():
    # Bar 20's actual wick ratio is 5.5/8 = 0.6875 (see
    # _liq_keep_scenario's comment). sweep_wick_mult=0.70 > 0.6875 must
    # block the sweep entirely -- no magnet ever fires.
    O, H, L, C = _liq_keep_scenario()
    out = _run(O, H, L, C, atr_len=2, pivot_len=2, liq_keep=4, sweep_wick_mult=0.70,
               sweep_confirm=2, magnet_window=18, **_TRIVIAL)
    assert out["FSME_MAG_BULL_2"].sum() == 0


def test_sweep_wick_ratio_gate_passes_below_actual_ratio():
    O, H, L, C = _liq_keep_scenario()
    out = _run(O, H, L, C, atr_len=2, pivot_len=2, liq_keep=4, sweep_wick_mult=0.68,
               sweep_confirm=2, magnet_window=18, **_TRIVIAL)
    assert out["FSME_MAG_BULL_2"].iloc[22] == 1


# ---------------------------------------------------------------------------
# sweep_confirm / magnet_window boundaries (both inclusive, matching the
# source's `sweepConfirm <= bar-lastSweepBar <= magnetWindow`)
# ---------------------------------------------------------------------------

def test_sweep_confirm_lower_boundary_inclusive():
    O, H, L, C = _liq_keep_scenario()  # sweep at bar 20, bullish confirm at bar 22 (=20+2)
    out = _run(O, H, L, C, atr_len=2, pivot_len=2, liq_keep=4, sweep_wick_mult=0.35,
               sweep_confirm=2, magnet_window=18, **_TRIVIAL)
    assert out["FSME_MAG_BULL_2"].iloc[22] == 1


def test_sweep_confirm_below_minimum_blocks_fire():
    O, H, L, C = _permanent_bull_base(30)
    O[6], H[6], L[6], C[6] = 95.0, 96.0, 90.0, 95.0
    O[20], H[20], L[20], C[20] = 90.5, 93.0, 85.0, 91.0
    # bar 21 = sweep bar + 1, BELOW sweep_confirm=2.
    O[21], H[21], L[21], C[21] = 100.0, 102.0, 99.0, 101.0
    out = _run(O, H, L, C, atr_len=2, pivot_len=2, liq_keep=4, sweep_wick_mult=0.35,
               sweep_confirm=2, magnet_window=18, **_TRIVIAL)
    assert out["FSME_MAG_BULL_2"].sum() == 0


def test_magnet_window_upper_boundary_inclusive():
    O, H, L, C = _permanent_bull_base(45)
    O[6], H[6], L[6], C[6] = 95.0, 96.0, 90.0, 95.0
    O[20], H[20], L[20], C[20] = 90.5, 93.0, 85.0, 91.0
    O[38], H[38], L[38], C[38] = 100.0, 102.0, 99.0, 101.0  # =20+18, inclusive boundary
    out = _run(O, H, L, C, atr_len=2, pivot_len=2, liq_keep=4, sweep_wick_mult=0.35,
               sweep_confirm=2, magnet_window=18, **_TRIVIAL)
    assert out["FSME_MAG_BULL_2"].iloc[38] == 1


def test_magnet_window_past_upper_boundary_blocks_fire():
    O, H, L, C = _permanent_bull_base(45)
    O[6], H[6], L[6], C[6] = 95.0, 96.0, 90.0, 95.0
    O[20], H[20], L[20], C[20] = 90.5, 93.0, 85.0, 91.0
    O[39], H[39], L[39], C[39] = 100.0, 102.0, 99.0, 101.0  # =20+19, one past the window
    out = _run(O, H, L, C, atr_len=2, pivot_len=2, liq_keep=4, sweep_wick_mult=0.35,
               sweep_confirm=2, magnet_window=18, **_TRIVIAL)
    assert out["FSME_MAG_BULL_2"].sum() == 0


# ---------------------------------------------------------------------------
# min_score gate
# ---------------------------------------------------------------------------

def test_min_score_gate_fails_above_actual_score():
    # Bar 22's actual score in the liq_keep scenario is 8.0 (independently
    # confirmed against _score() via the creation-scenario score test
    # above's same formula -- verified 8.0 directly against the real
    # output at construction time).
    O, H, L, C = _liq_keep_scenario()
    out = _run(O, H, L, C, atr_len=2, pivot_len=2, liq_keep=4, sweep_wick_mult=0.35,
               sweep_confirm=2, magnet_window=18, require_disp=False, min_gap_atr=0.0, min_score=9)
    assert out["FSME_MAG_BULL_2"].sum() == 0


def test_min_score_gate_passes_at_actual_score():
    O, H, L, C = _liq_keep_scenario()
    out = _run(O, H, L, C, atr_len=2, pivot_len=2, liq_keep=4, sweep_wick_mult=0.35,
               sweep_confirm=2, magnet_window=18, require_disp=False, min_gap_atr=0.0, min_score=8)
    assert out["FSME_MAG_BULL_2"].iloc[22] == 1


# ---------------------------------------------------------------------------
# Candle-direction gate (strict, matching the source's Close > Open /
# Close < Open, not inclusive)
# ---------------------------------------------------------------------------

def test_candle_direction_gate_blocks_doji():
    O, H, L, C = _permanent_bull_base(30)
    O[6], H[6], L[6], C[6] = 95.0, 96.0, 90.0, 95.0
    O[20], H[20], L[20], C[20] = 90.5, 93.0, 85.0, 91.0
    # bar 22 left at the baseline doji (close == open == 100.0)
    out = _run(O, H, L, C, atr_len=2, pivot_len=2, liq_keep=4, sweep_wick_mult=0.35,
               sweep_confirm=2, magnet_window=18, **_TRIVIAL)
    assert out["FSME_MAG_BULL_2"].sum() == 0


# ---------------------------------------------------------------------------
# Repeat-fire cooldown (> magnet_window since the same direction's last
# fire; a fresh sweep within the window is necessary but not sufficient)
# ---------------------------------------------------------------------------

def test_cooldown_blocks_repeat_fire_then_clears():
    O, H, L, C = _permanent_bull_base(55)
    O[6], H[6], L[6], C[6] = 95.0, 96.0, 90.0, 95.0
    O[20], H[20], L[20], C[20] = 90.5, 93.0, 85.0, 91.0
    O[22], H[22], L[22], C[22] = 100.0, 102.0, 99.0, 101.0   # fires (first)
    O[26], H[26], L[26], C[26] = 95.0, 96.0, 90.0, 95.0      # fresh SSL pivot
    O[32], H[32], L[32], C[32] = 90.5, 93.0, 85.0, 91.0      # fresh sweep
    O[34], H[34], L[34], C[34] = 100.0, 102.0, 99.0, 101.0   # sweep-fresh + eligible, but cooldown-blocked (34-22=12<=18)
    O[41], H[41], L[41], C[41] = 100.0, 102.0, 99.0, 101.0   # still sweep-fresh from bar 32, cooldown cleared (41-22=19>18)
    out = _run(O, H, L, C, atr_len=2, pivot_len=2, liq_keep=4, sweep_wick_mult=0.35,
               sweep_confirm=2, magnet_window=18, **_TRIVIAL)
    fired = np.nonzero(out["FSME_MAG_BULL_2"].values)[0]
    assert list(fired) == [22, 41]


# ---------------------------------------------------------------------------
# Bear mirror -- one full end-to-end sweep+magnet-fire scenario
# ---------------------------------------------------------------------------

def test_bear_sweep_and_magnet_fire_end_to_end():
    O, H, L, C = _permanent_bear_base(30)
    # BSL pivot high at bar 6 (value 110), confirms bar 8.
    O[6], H[6], L[6], C[6] = 105.0, 110.0, 104.0, 105.0
    # bear sweep at bar 20: high>110, close<110, close<open.
    O[20], H[20], L[20], C[20] = 109.5, 115.0, 107.0, 109.0
    # bearish confirming candle at bar 22 (=20+2).
    O[22], H[22], L[22], C[22] = 100.0, 101.0, 98.0, 99.0
    out = _run(O, H, L, C, atr_len=2, pivot_len=2, liq_keep=4, sweep_wick_mult=0.35,
               sweep_confirm=2, magnet_window=18, **_TRIVIAL)
    assert out["FSME_MAG_BEAR_2"].iloc[22] == 1
    assert out["FSME_MAG_BULL_2"].sum() == 0


# ---------------------------------------------------------------------------
# NaN pairing + boundedness on random data
# ---------------------------------------------------------------------------

def _random_walk_ohlcv(n=250, seed=11):
    rng = np.random.RandomState(seed)
    idx = _idx(n)
    close = pd.Series(100 + np.cumsum(rng.randn(n) * 0.6), index=idx)
    high = close + np.abs(rng.randn(n)) * 0.7 + 0.05
    low = close - np.abs(rng.randn(n)) * 0.7 - 0.05
    open_ = close.shift(1).fillna(close.iloc[0]).clip(lower=low, upper=high)
    volume = pd.Series(1e6 + np.abs(rng.randn(n)) * 2e5, index=idx)
    assert (low <= close).all() and (close <= high).all()
    assert (low <= open_).all() and (open_ <= high).all()
    return open_, high, low, close, volume


def test_ce_score_nan_exactly_when_ce_dist_nan_and_bounded_when_populated():
    open_, high, low, close, volume = _random_walk_ohlcv()
    out = ta.fvg_sweep_magnet(open_, high, low, close, volume)
    for dist_col, score_col in (("FSME_CE_DIST_BULL_5", "FSME_CE_SCORE_BULL_5"),
                                 ("FSME_CE_DIST_BEAR_5", "FSME_CE_SCORE_BEAR_5")):
        dist = out[dist_col]
        score = out[score_col]
        assert (dist.isna() == score.isna()).all(), \
            f"{score_col} must be NaN exactly when {dist_col} is NaN"
        pop_dist = dist.dropna()
        pop_score = score.dropna()
        if len(pop_dist):
            assert (pop_dist >= 0.0).all()
        if len(pop_score):
            assert (pop_score >= 0.0).all() and (pop_score <= 10.0).all()
    for mag_col in ("FSME_MAG_BULL_5", "FSME_MAG_BEAR_5"):
        assert out[mag_col].isin([0, 1]).all()


# ---------------------------------------------------------------------------
# Causality -- mutation and truncation
# ---------------------------------------------------------------------------

def test_causal_no_lookahead():
    open_, high, low, close, volume = _random_walk_ohlcv()
    out_full = ta.fvg_sweep_magnet(open_, high, low, close, volume)
    t = 150

    rng = np.random.RandomState(99)
    open2, high2, low2, close2, volume2 = open_.copy(), high.copy(), low.copy(), close.copy(), volume.copy()
    n = len(close)
    shock = rng.randn(n - t - 1) * 5
    close2.iloc[t + 1:] = close2.iloc[t + 1:] + shock
    high2.iloc[t + 1:] = np.maximum(high2.iloc[t + 1:], close2.iloc[t + 1:]) + 1.0
    low2.iloc[t + 1:] = np.minimum(low2.iloc[t + 1:], close2.iloc[t + 1:]) - 1.0
    open2.iloc[t + 1:] = open2.iloc[t + 1:].clip(lower=low2.iloc[t + 1:], upper=high2.iloc[t + 1:])
    volume2.iloc[t + 1:] = volume2.iloc[t + 1:] + np.abs(rng.randn(n - t - 1)) * 1e5
    assert (low2 <= close2).all() and (close2 <= high2).all()
    assert (low2 <= open2).all() and (open2 <= high2).all()

    out_mut = ta.fvg_sweep_magnet(open2, high2, low2, close2, volume2)
    pd.testing.assert_frame_equal(out_full.iloc[:t + 1], out_mut.iloc[:t + 1])


def test_causal_deletion_no_lookahead():
    open_, high, low, close, volume = _random_walk_ohlcv()
    out_full = ta.fvg_sweep_magnet(open_, high, low, close, volume)
    t = 150
    out_trunc = ta.fvg_sweep_magnet(open_.iloc[:t + 1], high.iloc[:t + 1], low.iloc[:t + 1],
                                     close.iloc[:t + 1], volume.iloc[:t + 1])
    pd.testing.assert_frame_equal(out_full.iloc[:t + 1], out_trunc)


# ---------------------------------------------------------------------------
# Reachability
# ---------------------------------------------------------------------------

def test_reachable_via_category_and_accessor():
    assert "fvg_sweep_magnet" in ta.Category["trend"]
    open_, high, low, close, volume = _random_walk_ohlcv(n=60)
    df = pd.DataFrame({"open": open_, "high": high, "low": low, "close": close, "volume": volume})
    assert callable(getattr(df.ta, "fvg_sweep_magnet"))
    direct = ta.fvg_sweep_magnet(open_, high, low, close, volume)
    via_accessor = df.ta.fvg_sweep_magnet()
    pd.testing.assert_frame_equal(direct, via_accessor)


# ---------------------------------------------------------------------------
# Invalid-input validation
# ---------------------------------------------------------------------------

def _bars(n=60, seed=1):
    rng = np.random.RandomState(seed)
    idx = _idx(n)
    close = pd.Series(100 + np.cumsum(rng.randn(n)), index=idx)
    high = close + 1
    low = close - 1
    open_ = close.shift(1).fillna(close.iloc[0]).clip(lower=low, upper=high)
    volume = pd.Series(1e6, index=idx)
    return open_, high, low, close, volume


@pytest.mark.parametrize("kwargs", [
    dict(fvg_lookback=float("nan")),
    dict(fvg_lookback=float("inf")),
    dict(fvg_lookback=3.7),
    dict(fvg_lookback=0),
    dict(fvg_lookback=-1),
    dict(disp_atr_mult=float("nan")),
    dict(disp_atr_mult=float("inf")),
    dict(disp_atr_mult=-0.1),
    dict(atr_len=0),
    dict(atr_len=-5),
    dict(min_gap_atr=float("nan")),
    dict(min_gap_atr=float("-inf")),
    dict(min_gap_atr=-0.1),
    dict(require_disp=1),
    dict(require_disp="true"),
    dict(max_fvg_age=0),
    dict(max_fvg_age=1.5),
    dict(pivot_len=0),
    dict(pivot_len=-2),
    dict(liq_keep=0),
    dict(sweep_wick_mult=float("nan")),
    dict(sweep_wick_mult=-0.1),
    dict(sweep_confirm=0),
    dict(sweep_confirm=float("inf")),
    dict(magnet_window=0),
    dict(magnet_window=-1),
    dict(min_score=float("nan")),
    dict(min_score=-1),
    dict(min_score=1.5),
])
def test_invalid_params_raise_value_error(kwargs):
    open_, high, low, close, volume = _bars()
    with pytest.raises(ValueError):
        ta.fvg_sweep_magnet(open_, high, low, close, volume, **kwargs)


def test_none_params_use_documented_defaults():
    open_, high, low, close, volume = _bars()
    out = ta.fvg_sweep_magnet(open_, high, low, close, volume, fvg_lookback=None, disp_atr_mult=None,
                               atr_len=None, min_gap_atr=None, require_disp=None, max_fvg_age=None,
                               pivot_len=None, liq_keep=None, sweep_wick_mult=None, sweep_confirm=None,
                               magnet_window=None, min_score=None)
    assert list(out.columns) == [
        "FSME_MAG_BULL_5", "FSME_MAG_BEAR_5", "FSME_CE_DIST_BULL_5", "FSME_CE_DIST_BEAR_5",
        "FSME_CE_SCORE_BULL_5", "FSME_CE_SCORE_BEAR_5",
    ]


def test_min_score_zero_allowed():
    open_, high, low, close, volume = _bars()
    out = ta.fvg_sweep_magnet(open_, high, low, close, volume, min_score=0)
    assert "FSME_MAG_BULL_5" in out.columns


# ---------------------------------------------------------------------------
# Attribution
# ---------------------------------------------------------------------------

def test_docstring_names_source_and_author():
    doc = ta.fvg_sweep_magnet.__doc__
    normalized = " ".join(doc.split())
    assert "https://www.tradingview.com/script/1FFYDfSr-FVG-Sweep-Magnet-Engine-PhenLabs/" in normalized
    assert "PhenLabs" in doc


def test_docstring_differentiates_from_fvg_and_liquidity_sweep():
    doc = ta.fvg_sweep_magnet.__doc__
    assert "fvg.py" in doc
    assert "liquidity_sweep.py" in doc
