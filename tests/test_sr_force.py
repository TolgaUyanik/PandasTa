# tests/test_sr_force.py
"""sr_force (SRF) -- confirmed swing pivots become S/R levels, each scored
once (at confirmation) by a re-test-strength score (TVPTA-6, ported from
"ATK/DEF Support Resistance SR Force Matrix"). Self-contained on
synthetic data.

Reachability tests `import pandas_ta` (`.context`), NOT `importlib.util.
spec_from_file_location` (see TODO.md TVPTA-3(c)).

This indicator only consumes high/low/close (no `open`), so the "physically
valid OHLC" discipline this project's test files document (see
`tests/test_sphinx_unicorn.py`'s module docstring for the incident that
established it, and `tests/test_rejection_blocks.py`'s for the Fletcher
round that caught two impossible bars slipping past a `low<=high`-only
guard) narrows to what actually matters here: every bar must satisfy
`low <= close <= high` AND `low <= high` -- `_valid_hlc` below asserts
both, every scenario builder calls it.

Every scenario's expected values were hand-derived against the .pine
source's own logic (`docs/TradingView/pine/1BcGW1Og.pine`,
`calculateResistanceBehavior`/`calculateSupportBehavior`) and then
independently confirmed by calling `_retest_score` directly and reading
its actual output before being written as an assertion here -- not
assumed. One hand-math attempt in developing this file assumed a single
touch at scan-offset i=1 would count on its own; running `_retest_score`
against that exact input immediately showed 0.0, not the ~0.294 hand
math predicted -- the source's `lastTouchBar` sentinel starts at 0, so
`i - lastTouchBar >= debounce_bars` requires `i >= debounce_bars` even
for the very FIRST touch, meaning i=1 can never count under the default
debounce_bars=2. `test_first_touch_at_i1_alone_never_counts_debounce_
sentinel` below pins this down explicitly since it is easy to get wrong
by hand (and was gotten wrong once, here, while writing this file).
"""
import math

import numpy as np
import pandas as pd
import pytest

from .context import pandas_ta as ta
from pandas_ta.trend.sr_force import (
    _confirm_strict_pivots, _validated_int, _validated_float, _retest_score,
)


def _idx(n):
    return pd.date_range("2020-01-01", periods=n, freq="B")


def _valid_hlc(H, L, C):
    assert (L <= C).all() and (C <= H).all() and (L <= H).all(), \
        "construction check: every bar must satisfy low <= close <= high"


# ---------------------------------------------------------------------------
# _confirm_strict_pivots -- isolated unit tests (duplicated per-file, same
# convention as liquidity_sweep.py / rejection_blocks.py's own copies)
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
# _validated_int / _validated_float -- isolated unit tests (nan/inf/
# non-integral discipline)
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
    # debounce_bars uses positive=False -- 0 legitimately means "no
    # debounce, count every touching bar."
    assert _validated_int(0, 2, "debounce_bars", positive=False) == 0


def test_validated_int_nonpositive_rejects_negative():
    with pytest.raises(ValueError):
        _validated_int(-1, 2, "debounce_bars", positive=False)


def test_validated_float_none_returns_default():
    assert _validated_float(None, 0.003, "x") == 0.003


def test_validated_float_rejects_nan_and_inf():
    with pytest.raises(ValueError, match="NaN"):
        _validated_float(float("nan"), 0.003, "x")
    with pytest.raises(ValueError, match="inf"):
        _validated_float(float("inf"), 0.003, "x")
    with pytest.raises(ValueError, match="inf"):
        _validated_float(float("-inf"), 0.003, "x")


def test_validated_float_rejects_negative():
    with pytest.raises(ValueError):
        _validated_float(-0.1, 0.003, "x")


def test_validated_float_accepts_zero():
    assert _validated_float(0.0, 0.003, "x") == 0.0


# ---------------------------------------------------------------------------
# _retest_score -- isolated unit tests. Hand-derived against the source's
# calculateResistanceBehavior/calculateSupportBehavior (byte-identical in
# the source; this port implements them once). All cases scan back from a
# late bar t=60 with retest_lookback=50, so every i in [1,50] maps to a
# valid non-negative j = t - i (no early-history truncation to reason
# about) -- boundary/truncation behavior is covered separately in the
# end-to-end scenarios below via pivot bars near the start of history.
# ---------------------------------------------------------------------------

_PRICE = 100.0
_TOL = 0.003
_DEBOUNCE = 2
_LOOKBACK = 50
_T = 60


def _mk(t, touches, base=50.0, price=_PRICE):
    """Build minimal high/low/close numpy arrays (length t+1) with a
    touch (high == low == close == price, a flat bar exactly at the
    level's own price -- physically valid and unambiguously "touched" by
    any of the three checks) placed at scan-offset i for every i in
    `touches` (j = t - i). Bars not listed stay at `base`, chosen far
    outside the [price*(1-tol), price*(1+tol)] band so they never
    accidentally register as a touch."""
    n = t + 1
    H = np.full(n, base)
    L = np.full(n, base)
    C = np.full(n, base)
    for i in touches:
        j = t - i
        H[j] = L[j] = C[j] = price
    assert (L <= C).all() and (C <= H).all(), "construction check"
    return H, L, C


def _w(i, lookback=_LOOKBACK):
    return 1.0 - (i / lookback) * 0.5


def test_retest_score_no_touches_is_zero():
    H, L, C = _mk(_T, [])
    assert _retest_score(H, L, C, _T, _PRICE, _LOOKBACK, _TOL, _DEBOUNCE) == 0.0


def test_first_touch_at_i1_alone_never_counts_debounce_sentinel():
    # THE hand-math trap this file's module docstring documents: i=1 can
    # never satisfy `i - lastTouchBar >= debounce_bars` when
    # lastTouchBar starts at its Pine-source initial value of 0 and
    # debounce_bars=2 (1 - 0 = 1 < 2). A touch must occur at
    # i >= debounce_bars to ever be counted, even as the very first one.
    H, L, C = _mk(_T, [1])
    assert _retest_score(H, L, C, _T, _PRICE, _LOOKBACK, _TOL, _DEBOUNCE) == 0.0


def test_retest_score_single_touch_cnt1():
    # i=2 is the minimum offset a touch can ever be counted at (see
    # above). cnt=1 -> countFactor=0.3 (the "cnt < 2" default branch).
    H, L, C = _mk(_T, [2])
    expected = 1 * _w(2) * 0.3
    got = _retest_score(H, L, C, _T, _PRICE, _LOOKBACK, _TOL, _DEBOUNCE)
    assert math.isclose(got, expected, rel_tol=1e-12)
    assert math.isclose(expected, 0.294, rel_tol=1e-9)


def test_retest_score_cnt2_count_factor_step():
    H, L, C = _mk(_T, [2, 5])
    avg = (_w(2) + _w(5)) / 2
    expected = 2 * avg * 0.6  # cnt=2 -> countFactor=0.6
    got = _retest_score(H, L, C, _T, _PRICE, _LOOKBACK, _TOL, _DEBOUNCE)
    assert math.isclose(got, expected, rel_tol=1e-12)


def test_retest_score_cnt3_count_factor_step():
    H, L, C = _mk(_T, [2, 5, 8])
    avg = (_w(2) + _w(5) + _w(8)) / 3
    expected = 3 * avg * 1.0  # cnt=3 -> countFactor=1.0
    got = _retest_score(H, L, C, _T, _PRICE, _LOOKBACK, _TOL, _DEBOUNCE)
    assert math.isclose(got, expected, rel_tol=1e-12)


def test_retest_score_cnt5_hits_final_cap():
    # 5 touches at i=2,5,8,11,14 with these early (high-weight) offsets
    # push the raw cnt*avgWeight*countFactor product (6.9) above the
    # source's own finalScore cap of 5.0 -- the cap must clip it, not
    # just report the raw product.
    H, L, C = _mk(_T, [2, 5, 8, 11, 14])
    avg = (_w(2) + _w(5) + _w(8) + _w(11) + _w(14)) / 5
    raw = 5 * avg * 1.5  # cnt=5 -> countFactor=1.5
    assert raw > 5.0, "test construction check: this case must actually hit the cap"
    got = _retest_score(H, L, C, _T, _PRICE, _LOOKBACK, _TOL, _DEBOUNCE)
    assert got == 5.0


def test_retest_score_debounce_blocks_adjacent_touch():
    # i=2 and i=3 are only 1 bar apart (< debounce_bars=2) -- the second
    # must be blocked; score must equal the single-touch (i=2) case
    # exactly, not a 2-touch score.
    H, L, C = _mk(_T, [2, 3])
    single = _retest_score(*_mk(_T, [2]), _T, _PRICE, _LOOKBACK, _TOL, _DEBOUNCE)
    got = _retest_score(H, L, C, _T, _PRICE, _LOOKBACK, _TOL, _DEBOUNCE)
    assert got == single


def test_retest_score_debounce_bars_zero_counts_every_touch():
    # debounce_bars=0 disables the gap requirement entirely -- both i=2
    # and i=3 must count (2 touches), unlike the default debounce_bars=2
    # case just above where the same two offsets collapse to 1.
    H, L, C = _mk(_T, [2, 3])
    avg = (_w(2) + _w(3)) / 2
    expected = 2 * avg * 0.6
    got = _retest_score(H, L, C, _T, _PRICE, _LOOKBACK, _TOL, 0)
    assert math.isclose(got, expected, rel_tol=1e-12)


def test_retest_score_cnt_raw_above_5_inflates_avg_weight():
    # THE dedicated regression test for the module docstring's second
    # documented quirk: weightScore accumulates EVERY debounced touch
    # (cnt_raw=6 here), but avgWeight divides by the CAPPED cnt (5) --
    # so a 6-touch level's score is measurably higher than a genuine
    # 5-touch level built from this 6-touch level's 5 highest-weight
    # (lowest-offset) touches would produce. All 6 touches placed late
    # in the scan window (i=40..50) specifically so the capped score
    # does NOT ALSO hit the separate finalScore>5.0 cap -- otherwise
    # both a 5-touch and a 6+-touch level would read identically (5.0)
    # and this test would prove nothing about the inflation itself.
    H, L, C = _mk(_T, [40, 42, 44, 46, 48, 50])
    ws = [_w(i) for i in (40, 42, 44, 46, 48, 50)]
    avg_inflated = sum(ws) / 5  # divide 6 terms' sum by capped cnt=5
    expected = 5 * avg_inflated * 1.5
    assert expected < 5.0, "test construction check: must NOT hit the separate final-score cap"
    got = _retest_score(H, L, C, _T, _PRICE, _LOOKBACK, _TOL, _DEBOUNCE)
    assert math.isclose(got, expected, rel_tol=1e-12)

    # the "true" 5-touch comparison (this level's own 5 highest-weight
    # touches only, i.e. dropping the 6th/lowest-weight one) must score
    # STRICTLY LOWER -- the inflation is real and measurable, not a
    # rounding artifact.
    ws5 = [_w(i) for i in (40, 42, 44, 46, 48)]
    true5 = 5 * (sum(ws5) / 5) * 1.5
    assert got > true5


def test_retest_score_early_history_offsets_are_skipped_not_crashed():
    # j = t - i going negative (t smaller than the scan reach) must be
    # skipped exactly like Pine's `not na(high[i])` guard at the start
    # of history -- not raise, not wrap/index from the end.
    H, L, C = _mk(5, [2])  # t=5, only 6 bars of history exist at all
    got = _retest_score(H, L, C, 5, _PRICE, _LOOKBACK, _TOL, _DEBOUNCE)
    expected = 1 * _w(2) * 0.3
    assert math.isclose(got, expected, rel_tol=1e-12)


# ---------------------------------------------------------------------------
# End-to-end sr_force() scenarios
# ---------------------------------------------------------------------------

def _flooded_hlc(n, h=101.0, l=99.0, c=100.0):
    H = np.full(n, h)
    L = np.full(n, l)
    C = np.full(n, c)
    return H, L, C


def _run(H, L, C, **kwargs):
    _valid_hlc(H, L, C)
    idx = _idx(len(H))
    return ta.sr_force(pd.Series(H, index=idx), pd.Series(L, index=idx),
                        pd.Series(C, index=idx), **kwargs)


def test_resistance_level_confirms_and_scores_end_to_end():
    # Swing high at bar 5 (H=110, unique vs flooded H=101), confirms at
    # bar 7 (swing_len=2). Its own bar is the ONLY touch found in the
    # 50-bar backward scan from bar 7 (i=2 -- the minimum offset that can
    # ever count, see the debounce-sentinel tests above): score matches
    # test_retest_score_single_touch_cnt1's hand-derived 0.294 exactly.
    n = 20
    H, L, C = _flooded_hlc(n)
    H[5], L[5], C[5] = 110.0, 99.0, 100.0
    out = _run(H, L, C, swing_len=2, retest_lookback=50, touch_tol_pct=0.003, debounce_bars=2)

    score_res = out["SRF_SCORE_RES_2"]
    dist_res = out["SRF_DIST_RES_2"]
    assert score_res.iloc[:7].isna().all()
    assert dist_res.iloc[:7].isna().all()
    assert math.isclose(score_res.iloc[7], 0.294, rel_tol=1e-9)
    assert math.isclose(dist_res.iloc[7], 10.0, rel_tol=1e-9)  # (110-100)/100*100
    # level persists (no removal mechanism besides the FIFO cap) for
    # every subsequent bar in this scenario
    assert score_res.iloc[7:].eq(score_res.iloc[7]).all()
    assert dist_res.iloc[7:].eq(10.0).all()
    # never a support event anywhere in this purely-resistance scenario
    assert out["SRF_SCORE_SUP_2"].isna().all()
    assert out["SRF_DIST_SUP_2"].isna().all()


def test_support_level_confirms_and_scores_mirrors_resistance():
    n = 20
    H, L, C = _flooded_hlc(n)
    H[5], L[5], C[5] = 101.0, 90.0, 100.0
    out = _run(H, L, C, swing_len=2, retest_lookback=50, touch_tol_pct=0.003, debounce_bars=2)

    score_sup = out["SRF_SCORE_SUP_2"]
    dist_sup = out["SRF_DIST_SUP_2"]
    assert score_sup.iloc[:7].isna().all()
    assert math.isclose(score_sup.iloc[7], 0.294, rel_tol=1e-9)
    assert math.isclose(dist_sup.iloc[7], 10.0, rel_tol=1e-9)  # (100-90)/100*100
    assert dist_sup.iloc[7:].eq(10.0).all()
    assert out["SRF_SCORE_RES_2"].isna().all()
    assert out["SRF_DIST_RES_2"].isna().all()


def test_dist_res_excludes_level_price_has_moved_below():
    # Fletcher-lesson-applied test (liquidity_sweep.py's Fletcher-MAJOR
    # precedent): a level that is still IN the pool (no break/sweep
    # removal exists for this indicator, only the FIFO cap) must still
    # be EXCLUDED from the nearest-resistance argmin the moment price
    # has moved above it -- a resistance level's price must stay
    # strictly above Close to count as a valid candidate.
    #
    # Regime 1 (bars 0-19, flood close=100): swing high at bar 5
    # (H=110) confirms at bar 7 -> level A, price=110, valid resistance
    # while close=100 (dist=10.0).
    #
    # Regime 2 (bars 20+, flood close=200, roughly a 2x rally): level A
    # (110) is now BELOW close (200) -- must be excluded. A NEW swing
    # high at bar 25 (H=210, unique vs the new flood H=201) confirms at
    # bar 27 -> level B, price=210, genuinely above the new close (200).
    n = 40
    H = np.full(n, 101.0); L = np.full(n, 99.0); C = np.full(n, 100.0)
    H[5], L[5], C[5] = 110.0, 99.0, 100.0
    H[20:], L[20:], C[20:] = 201.0, 199.0, 200.0
    H[25], L[25], C[25] = 210.0, 199.0, 200.0
    out = _run(H, L, C, swing_len=2, retest_lookback=50, touch_tol_pct=0.003, debounce_bars=2)

    dist_res = out["SRF_DIST_RES_2"]
    score_res = out["SRF_SCORE_RES_2"]
    # pre-rally: level A is the only (valid) candidate
    assert math.isclose(dist_res.iloc[7], 10.0, rel_tol=1e-9)
    assert math.isclose(dist_res.iloc[19], 10.0, rel_tol=1e-9)
    # bars 20-26: level A now below close (110 < 200) -> excluded, and
    # level B hasn't confirmed yet (confirms at 27) -> no valid candidate
    assert dist_res.iloc[20:27].isna().all(), \
        "level A must be excluded once price has moved above it, even though it is still in the pool"
    assert score_res.iloc[20:27].isna().all()
    # bar 27+: level B is the only valid candidate; its dist is
    # (210-200)/200*100 = 5.0, NOT level A's smaller (but wrong-side) gap
    assert math.isclose(dist_res.iloc[27], 5.0, rel_tol=1e-9)
    assert dist_res.iloc[27:].eq(5.0).all()


def test_dist_sup_excludes_level_price_has_moved_above():
    # Mirror of the above on the support side: a crash (instead of a
    # rally) leaves a former support level ABOVE the new, lower close.
    n = 40
    H = np.full(n, 101.0); L = np.full(n, 99.0); C = np.full(n, 100.0)
    H[5], L[5], C[5] = 101.0, 90.0, 100.0
    H[20:], L[20:], C[20:] = 51.0, 49.0, 50.0
    L[25], H[25], C[25] = 40.0, 51.0, 50.0
    out = _run(H, L, C, swing_len=2, retest_lookback=50, touch_tol_pct=0.003, debounce_bars=2)

    dist_sup = out["SRF_DIST_SUP_2"]
    assert math.isclose(dist_sup.iloc[7], 10.0, rel_tol=1e-9)
    assert math.isclose(dist_sup.iloc[19], 10.0, rel_tol=1e-9)
    assert dist_sup.iloc[20:27].isna().all(), \
        "level A (support=90) must be excluded once price has fallen below it"
    assert math.isclose(dist_sup.iloc[27], 20.0, rel_tol=1e-9)  # (50-40)/50*100
    assert dist_sup.iloc[27:].eq(20.0).all()


def test_max_levels_fifo_cap_per_side():
    # max_levels=1: level 1 (price=105, nearer, confirms bar 7) must be
    # EVICTED the instant level 2 (price=120, farther, confirms bar 22)
    # is pushed -- DIST_RES must jump straight from level 1's smaller
    # distance to level 2's larger one, never averaging or preferring
    # the nearer (evicted) level.
    n = 30
    H = np.full(n, 101.0); L = np.full(n, 99.0); C = np.full(n, 100.0)
    H[5], L[5], C[5] = 105.0, 99.0, 100.0
    H[20], L[20], C[20] = 120.0, 99.0, 100.0
    out = _run(H, L, C, swing_len=2, retest_lookback=50, touch_tol_pct=0.003,
               debounce_bars=2, max_levels=1)

    dist_res = out["SRF_DIST_RES_2"]
    assert math.isclose(dist_res.iloc[7], 5.0, rel_tol=1e-9)   # (105-100)/100*100
    assert dist_res.iloc[7:22].eq(5.0).all()
    assert math.isclose(dist_res.iloc[22], 20.0, rel_tol=1e-9)  # (120-100)/100*100, level 1 evicted
    assert dist_res.iloc[22:].eq(20.0).all()


def test_dist_and_score_report_zero_not_nan_when_close_equals_level_price():
    # THE dedicated regression test for the Fletcher MAJOR fix (round 1
    # on this port): before the fix, the side-constraint filters used
    # strict >/< , so Close landing EXACTLY on a level's price -- the
    # single most informative bar, price sitting exactly on a heavily
    # re-tested level -- reported NaN on BOTH SCORE and DIST instead of
    # the obvious answer: you are AT that level right now, distance 0.
    # Mirrors rejection_blocks.py's own "zero not nan while price inside
    # zone" regression test for the same class of gap.
    #
    # Resistance: swing high at bar 5 (H=107, unique vs flooded H=101),
    # confirms at bar 7 -> level A, price=107, score=0.294 (single
    # self-touch, same as the other single-touch scenarios in this
    # file). At bar 15, Close is set to EXACTLY 107 (H/L widened just
    # enough to keep the bar physically valid; this incidentally also
    # creates a brand new candidate resistance pivot at bar 15, but it
    # would not confirm until bar 17 -- irrelevant to this test, which
    # only asserts bar 15 itself, before that second pivot ever enters
    # the pool).
    n = 20
    H, L, C = _flooded_hlc(n)
    H[5], L[5], C[5] = 107.0, 99.0, 100.0
    H[15], L[15], C[15] = 107.5, 106.5, 107.0
    out = _run(H, L, C, swing_len=2, retest_lookback=50, touch_tol_pct=0.003, debounce_bars=2)

    assert math.isclose(out["SRF_SCORE_RES_2"].iloc[7], 0.294, rel_tol=1e-9)
    assert out["SRF_DIST_RES_2"].iloc[15] == 0.0, "must be 0.0 (Close == level price), never NaN"
    assert math.isclose(out["SRF_SCORE_RES_2"].iloc[15], 0.294, rel_tol=1e-9), \
        "must report the level's real score, never NaN, at the exact equality boundary"


def test_dist_and_score_report_zero_not_nan_when_close_equals_level_price_support_mirror():
    # Mirror of the above on the support side.
    n = 20
    H, L, C = _flooded_hlc(n)
    H[5], L[5], C[5] = 101.0, 93.0, 100.0
    H[15], L[15], C[15] = 93.5, 92.5, 93.0
    out = _run(H, L, C, swing_len=2, retest_lookback=50, touch_tol_pct=0.003, debounce_bars=2)

    assert math.isclose(out["SRF_SCORE_SUP_2"].iloc[7], 0.294, rel_tol=1e-9)
    assert out["SRF_DIST_SUP_2"].iloc[15] == 0.0, "must be 0.0 (Close == level price), never NaN"
    assert math.isclose(out["SRF_SCORE_SUP_2"].iloc[15], 0.294, rel_tol=1e-9), \
        "must report the level's real score, never NaN, at the exact equality boundary"


def test_retest_score_nan_close_does_not_block_touch_via_high_or_low():
    # THE dedicated regression test for the Fletcher MINOR fix: the
    # source's touch-scan guard is `not na(high[i]) and not na(low[i])`
    # -- close is NOT part of it. A NaN close on an otherwise-valid bar
    # must not block a touch registered via that bar's high or low; it
    # must simply fail its OWN band comparison (NaN comparisons are
    # always False), leaving the high/low disjuncts free to still fire.
    # An earlier version of this port guarded on high/low/close
    # together, which silently dropped this touch.
    H, L, C = _mk(_T, [])
    j = _T - 2  # the same minimum-countable offset (i=2) used throughout this file
    H[j] = _PRICE  # touch registers via high
    C[j] = np.nan  # close is NaN on this same bar -- must not block it
    got_with_nan_close = _retest_score(H, L, C, _T, _PRICE, _LOOKBACK, _TOL, _DEBOUNCE)

    H2, L2, C2 = _mk(_T, [2])  # equivalent bar, ordinary (non-NaN) close touch
    got_ordinary = _retest_score(H2, L2, C2, _T, _PRICE, _LOOKBACK, _TOL, _DEBOUNCE)

    assert got_with_nan_close == got_ordinary
    assert got_with_nan_close > 0.0, "test construction check: the touch must actually register"


def test_score_nan_exactly_when_dist_nan_and_bounded_when_populated():
    open_, high, low, close = _random_walk_ohlc(n=250, seed=11)
    out = ta.sr_force(high, low, close)
    for score_col, dist_col in (("SRF_SCORE_RES_5", "SRF_DIST_RES_5"),
                                 ("SRF_SCORE_SUP_5", "SRF_DIST_SUP_5")):
        score = out[score_col]
        dist = out[dist_col]
        assert (score.isna() == dist.isna()).all(), \
            f"{score_col} must be NaN exactly when {dist_col} is NaN"
        pop_score = score.dropna()
        pop_dist = dist.dropna()
        if len(pop_score):
            assert (pop_score >= 0.0).all() and (pop_score <= 5.0).all()
        if len(pop_dist):
            assert (pop_dist >= 0.0).all()
            # a %-of-close distance on this random-walk scale should
            # never run away to an absurd magnitude
            assert (pop_dist < 100).all()


# ---------------------------------------------------------------------------
# Causality -- mutation and truncation
# ---------------------------------------------------------------------------

def _random_walk_ohlc(n=200, seed=3):
    rng = np.random.RandomState(seed)
    idx = _idx(n)
    close = pd.Series(100 + np.cumsum(rng.randn(n) * 0.5), index=idx)
    high = close + np.abs(rng.randn(n)) * 0.6 + 0.05
    low = close - np.abs(rng.randn(n)) * 0.6 - 0.05
    open_ = close.shift(1).fillna(close.iloc[0])
    open_ = open_.clip(lower=low, upper=high)
    assert (low <= close).all() and (close <= high).all(), "construction check"
    return open_, high, low, close


def test_causal_no_lookahead():
    open_, high, low, close = _random_walk_ohlc()
    out_full = ta.sr_force(high, low, close)
    t = 120

    rng = np.random.RandomState(99)
    high2, low2, close2 = high.copy(), low.copy(), close.copy()
    n = len(close)
    shock = rng.randn(n - t - 1) * 5
    close2.iloc[t + 1:] = close2.iloc[t + 1:] + shock
    high2.iloc[t + 1:] = np.maximum(high2.iloc[t + 1:], close2.iloc[t + 1:]) + 1.0
    low2.iloc[t + 1:] = np.minimum(low2.iloc[t + 1:], close2.iloc[t + 1:]) - 1.0
    assert (low2 <= close2).all() and (close2 <= high2).all(), "construction check"

    out_mut = ta.sr_force(high2, low2, close2)
    pd.testing.assert_frame_equal(out_full.iloc[:t + 1], out_mut.iloc[:t + 1])


def test_causal_deletion_no_lookahead():
    open_, high, low, close = _random_walk_ohlc()
    out_full = ta.sr_force(high, low, close)
    t = 120
    out_trunc = ta.sr_force(high.iloc[:t + 1], low.iloc[:t + 1], close.iloc[:t + 1])
    pd.testing.assert_frame_equal(out_full.iloc[:t + 1], out_trunc)


# ---------------------------------------------------------------------------
# Reachability
# ---------------------------------------------------------------------------

def test_reachable_via_category_and_accessor():
    assert "sr_force" in ta.Category["trend"]
    open_, high, low, close = _random_walk_ohlc(n=60)
    df = pd.DataFrame({"open": open_, "high": high, "low": low, "close": close})
    assert callable(getattr(df.ta, "sr_force"))
    direct = ta.sr_force(high, low, close)
    via_accessor = df.ta.sr_force()
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
    return high, low, close


@pytest.mark.parametrize("kwargs", [
    dict(swing_len=float("nan")),
    dict(swing_len=float("inf")),
    dict(swing_len=3.7),
    dict(swing_len=0),
    dict(swing_len=-1),
    dict(retest_lookback=float("nan")),
    dict(retest_lookback=float("inf")),
    dict(retest_lookback=0),
    dict(retest_lookback=-5),
    dict(touch_tol_pct=float("nan")),
    dict(touch_tol_pct=float("inf")),
    dict(touch_tol_pct=-0.1),
    dict(debounce_bars=float("nan")),
    dict(debounce_bars=float("-inf")),
    dict(debounce_bars=1.5),
    dict(debounce_bars=-1),
    dict(max_levels=0),
    dict(max_levels=-2),
])
def test_invalid_params_raise_value_error(kwargs):
    high, low, close = _bars()
    with pytest.raises(ValueError):
        ta.sr_force(high, low, close, **kwargs)


def test_none_params_use_documented_defaults():
    high, low, close = _bars()
    out = ta.sr_force(high, low, close, swing_len=None, retest_lookback=None,
                       touch_tol_pct=None, debounce_bars=None, max_levels=None)
    assert list(out.columns) == [
        "SRF_SCORE_RES_5", "SRF_SCORE_SUP_5", "SRF_DIST_RES_5", "SRF_DIST_SUP_5",
    ]


# ---------------------------------------------------------------------------
# Attribution
# ---------------------------------------------------------------------------

def test_docstring_names_source_and_author():
    doc = ta.sr_force.__doc__
    normalized = " ".join(doc.split())
    assert "https://www.tradingview.com/script/1BcGW1Og/" in normalized
    assert "ATTDEFS" in doc
    assert "S/R Force Matrix" in doc
