# tests/test_rejection_blocks.py
"""rejection_blocks (RB) -- confirmed swing pivots become "rejection
block" zones (the wick-rejection TP/entry zones the source author uses)
with a TAP/SPENT lifecycle (TVPTA-6, ported from "Kale Rejection Blocks -
John 3:16"). Self-contained on synthetic data.

Reachability tests `import pandas_ta` (`.context`), NOT `importlib.util.
spec_from_file_location` (see TODO.md TVPTA-3(c)).

All end-to-end scenarios below are built on physically valid OHLC (low <=
min(open, close) and max(open, close) <= high on every bar -- i.e. both
the open and the close sit INSIDE the [low, high] range, not just
low <= high -- each scenario builder asserts this full invariant itself
at construction time, per this project's own documented history of tests
dodging bugs via impossible bars, see tests/test_sphinx_unicorn.py's
module docstring for the precedent incident this guards against, and
Fletcher round 1 here, which caught two scenarios in this exact file that
passed a low<=high-only guard while having open/close sit outside
[low, high]).

Every scenario's expected values were hand-derived against the .pine
source's own logic (`docs/TradingView/pine/QjOFE86I-Kale-Rejection-
Blocks-John-3-16.pine`) and then independently confirmed by running the
port and reading its actual output before being written as an assertion
here -- not assumed. The two threshold tests (wick-ratio, wick-ATR) derive
their exact pass/fail wick sizes from the SAME `pandas_ta.volatility.atr`
call the module itself uses (see each test's comment), since ATR's
recursive (RMA-style) warmup makes the exact numeric threshold depend on
the full constructed series, not just a flat/asymptotic guess.
"""
import math

import numpy as np
import pandas as pd
import pytest

from .context import pandas_ta as ta
from pandas_ta.trend.rejection_blocks import (
    _confirm_strict_pivots, _validated_int, _validated_float,
)


# ---------------------------------------------------------------------------
# _confirm_strict_pivots -- isolated unit tests
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
# non-integral discipline, the explicit lesson this port applies over
# `liquidity_sweep.py`'s `_positive_int`/`_nonneg_float`, which do a bare
# `int(value)`/`float(value)` with no NaN/inf/non-integral pre-check).
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
    # 3.7 must RAISE, not silently truncate to 3 -- the exact gap in
    # liquidity_sweep.py's `_positive_int`, which does `int(3.7) == 3`
    # with no complaint.
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


def test_validated_float_none_returns_default():
    assert _validated_float(None, 0.35, "x") == 0.35


def test_validated_float_rejects_nan_and_inf():
    with pytest.raises(ValueError, match="NaN"):
        _validated_float(float("nan"), 0.35, "x")
    with pytest.raises(ValueError, match="inf"):
        _validated_float(float("inf"), 0.35, "x")
    with pytest.raises(ValueError, match="inf"):
        _validated_float(float("-inf"), 0.35, "x")


def test_validated_float_rejects_negative():
    with pytest.raises(ValueError):
        _validated_float(-0.1, 0.35, "x")


def test_validated_float_accepts_zero():
    # 0 legitimately disables the threshold (matches liquidity_sweep's
    # atr_mult=0.0 convention) -- not an error.
    assert _validated_float(0.0, 0.35, "x") == 0.0


# ---------------------------------------------------------------------------
# End-to-end rejection_blocks() scenarios
# ---------------------------------------------------------------------------

def _idx(n):
    return pd.date_range("2020-01-01", periods=n, freq="B")


def _flooded_ohlc(n, o=100.0, h=101.0, l=99.0, c=100.0):
    """A boring, constant market -- every bar identical, so any bar we
    override becomes trivially a strict-unique local extreme (no ties
    with the flood, and its own window's only competitor is the flood
    itself)."""
    O = np.full(n, o)
    H = np.full(n, h)
    L = np.full(n, l)
    C = np.full(n, c)
    return O, H, L, C


def _run(O, H, L, C, **kwargs):
    # Fletcher MAJOR (round 1): a bare `(L <= H).all()` check does NOT
    # catch a bar whose open/close sit OUTSIDE [low, high] (e.g. both
    # below low, or both above high) -- exactly the false-confidence-guard
    # failure mode this file's own module docstring cites the
    # test_sphinx_unicorn.py incident to prevent, and it was sitting
    # undetected in two of this file's own scenarios. Full invariant:
    # low <= min(open, close) and max(open, close) <= high.
    assert (L <= np.minimum(O, C)).all() and (np.maximum(O, C) <= H).all() and (L <= H).all(), \
        "construction check: every bar must be physically valid"
    idx = _idx(len(O))
    return ta.rejection_blocks(
        pd.Series(O, index=idx), pd.Series(H, index=idx),
        pd.Series(L, index=idx), pd.Series(C, index=idx), **kwargs)


def test_bearish_tap_then_spent_lifecycle():
    # Swing high at bar 5 (H=110, unique vs flooded H=101), body_top=101
    # (O=100,C=101) -> wick=9, confirms at bar 7 (swing_len=2). Zone:
    # top=110, bot=101. min_wick_ratio/atr=0 to isolate pure lifecycle
    # logic from the qualification filters (covered separately below);
    # atr_len=2 (not the 14 default) so ATR warms up well before bar 7 --
    # the module hard-blocks zone creation on a NaN ATR regardless of
    # min_wick_atr (mirrors Pine: `wick >= minWickA * na` is always
    # `false`, even when minWickA is 0, since `0 * na` is still `na`).
    #
    # Bar 7 (the confirmation bar itself) is tested against the newly
    # created zone using bar 7's OWN (flooded) high/low/close, exactly
    # like the source's script order (lifecycle loop runs after both
    # addRB calls, same bar): high[7]=101 >= bot(101) -> TAP fires
    # immediately on the confirming bar.
    #
    # Bar 15: close breaks decisively above top (111 > 110) -> SPENT,
    # zone removed. Bar 15 also sets a new local-max high (112) but its
    # own pivot window needs index 17 (out of range for n=17) to confirm,
    # so it never interferes with this scenario.
    n = 17
    O, H, L, C = _flooded_ohlc(n)
    O[5], H[5], L[5], C[5] = 100.0, 110.0, 99.0, 101.0
    O[15], H[15], L[15], C[15] = 100.0, 112.0, 99.0, 111.0
    out = _run(O, H, L, C, swing_len=2, min_wick_ratio=0.0, min_wick_atr=0.0, atr_len=2)

    tap_bear = out["RB_TAP_BEAR_2"]
    spent_bear = out["RB_SPENT_BEAR_2"]
    dist_res = out["RB_DIST_RES_2"]

    assert tap_bear.iloc[7] == 1
    assert tap_bear.sum() == 1
    assert spent_bear.iloc[15] == 1
    assert spent_bear.sum() == 1
    assert dist_res.iloc[:7].isna().all()
    assert dist_res.iloc[7:15].eq(1.0).all()  # (101-100)/100*100 = 1.0
    assert dist_res.iloc[15:].isna().all()
    # never a bullish event anywhere in this purely-bearish scenario
    assert out["RB_TAP_BULL_2"].sum() == 0
    assert out["RB_SPENT_BULL_2"].sum() == 0
    assert out["RB_DIST_SUP_2"].isna().all()
    assert (dist_res.dropna() >= 0).all()


def test_bullish_tap_then_spent_mirrors_bearish():
    # Mirror on the support side: swing low at bar 5 (L=90, unique vs
    # flooded L=99), body_bot=99 (O=100,C=99) -> wick=9, zone: top=99,
    # bot=90. Confirms at bar 7 (swing_len=2), tested same-bar against
    # flooded low=99 <= top(99) -> TAP fires immediately. Bar 15: close
    # breaks decisively below bot (89 < 90) -> SPENT.
    n = 17
    O, H, L, C = _flooded_ohlc(n)
    O[5], H[5], L[5], C[5] = 100.0, 101.0, 90.0, 99.0
    O[15], H[15], L[15], C[15] = 100.0, 101.0, 88.0, 89.0
    out = _run(O, H, L, C, swing_len=2, min_wick_ratio=0.0, min_wick_atr=0.0, atr_len=2)

    tap_bull = out["RB_TAP_BULL_2"]
    spent_bull = out["RB_SPENT_BULL_2"]
    dist_sup = out["RB_DIST_SUP_2"]

    assert tap_bull.iloc[7] == 1
    assert tap_bull.sum() == 1
    assert spent_bull.iloc[15] == 1
    assert spent_bull.sum() == 1
    assert dist_sup.iloc[:7].isna().all()
    assert dist_sup.iloc[7:15].eq(1.0).all()  # (100-99)/100*100 = 1.0
    assert dist_sup.iloc[15:].isna().all()
    assert out["RB_TAP_BEAR_2"].sum() == 0
    assert out["RB_SPENT_BEAR_2"].sum() == 0
    assert out["RB_DIST_RES_2"].isna().all()
    assert (dist_sup.dropna() >= 0).all()


def test_wick_ratio_threshold_blocks_and_admits():
    # rng = H-L = 110-100 = 10; min_wick_ratio default 0.35 -> threshold
    # wick 3.5. min_wick_atr=0.0 isolates this filter alone.
    n = 15
    # FAIL: body_top=107 -> wick = 110-107 = 3.0 < 3.5
    O, H, L, C = _flooded_ohlc(n)
    O[5], H[5], L[5], C[5] = 105.0, 110.0, 100.0, 107.0
    out_fail = _run(O, H, L, C, swing_len=2, min_wick_ratio=0.35, min_wick_atr=0.0, atr_len=2)
    assert out_fail["RB_DIST_RES_2"].isna().all()
    assert out_fail["RB_TAP_BEAR_2"].sum() == 0

    # PASS: body_top=106 -> wick = 110-106 = 4.0 >= 3.5
    O2, H2, L2, C2 = _flooded_ohlc(n)
    O2[5], H2[5], L2[5], C2[5] = 104.0, 110.0, 100.0, 106.0
    out_pass = _run(O2, H2, L2, C2, swing_len=2, min_wick_ratio=0.35, min_wick_atr=0.0, atr_len=2)
    dist_res = out_pass["RB_DIST_RES_2"]
    assert dist_res.iloc[7:].eq(6.0).all()  # (106-100)/100*100 = 6.0


def test_wick_atr_threshold_blocks_and_admits():
    # ATR(2) at the confirmation bar (index 7) for this exact H/L/C
    # construction (verified independently via pandas_ta.volatility.atr
    # on the same series) is 3.1338582677165356 -> min_wick_atr default
    # 0.30 -> threshold wick 0.9401574803149606. Varying ONLY `open`
    # (never `close`) keeps the pivot bar's true range/ATR trajectory
    # identical between the fail/pass cases, since TR is computed from
    # high/low/close alone -- open plays no role in ATR, only in
    # body_top = max(open, close). min_wick_ratio=0.0 isolates this
    # filter alone.
    from pandas_ta.volatility.atr import atr as _atr_fn

    n = 20
    O, H, L, C = _flooded_ohlc(n)
    O[5], H[5], L[5], C[5] = 100.0, 110.0, 99.0, 100.0
    idx = _idx(n)
    atr_check = _atr_fn(pd.Series(H, index=idx), pd.Series(L, index=idx),
                         pd.Series(C, index=idx), length=2)
    threshold = 0.30 * atr_check.iloc[7]
    assert math.isclose(threshold, 0.9401574803149606, rel_tol=1e-9)

    # FAIL: open=109.2 -> body_top=109.2 -> wick=0.8 < threshold
    Of, Hf, Lf, Cf = _flooded_ohlc(n)
    Of[5], Hf[5], Lf[5], Cf[5] = 109.2, 110.0, 99.0, 100.0
    out_fail = _run(Of, Hf, Lf, Cf, swing_len=2, min_wick_ratio=0.0, min_wick_atr=0.30, atr_len=2)
    assert out_fail["RB_DIST_RES_2"].isna().all()

    # PASS: open=109.0 -> body_top=109.0 -> wick=1.0 >= threshold
    Op, Hp, Lp, Cp = _flooded_ohlc(n)
    Op[5], Hp[5], Lp[5], Cp[5] = 109.0, 110.0, 99.0, 100.0
    out_pass = _run(Op, Hp, Lp, Cp, swing_len=2, min_wick_ratio=0.0, min_wick_atr=0.30, atr_len=2)
    dist_res = out_pass["RB_DIST_RES_2"]
    assert dist_res.iloc[7:].eq(9.0).all()  # (109-100)/100*100 = 9.0


def test_combined_pool_shared_fifo_cap_across_directions():
    # The source's `bxs` array holds BOTH directions together and caps
    # the TOTAL at `keepN` (max_zones), evicting the OLDEST regardless of
    # direction -- NOT a per-side cap. max_zones=1 with a bearish zone
    # then a bullish zone born later must evict the bearish one, even
    # though they're on opposite sides.
    n = 25
    O, H, L, C = _flooded_ohlc(n)
    # bearish zone at bar 3 (confirms bar 5, swing_len=2)
    O[3], H[3], L[3], C[3] = 100.0, 110.0, 99.0, 101.0
    # bullish zone at bar 13 (confirms bar 15) -- born AFTER, should
    # evict the bearish one from the size-1 combined pool
    O[13], H[13], L[13], C[13] = 100.0, 101.0, 90.0, 99.0
    out = _run(O, H, L, C, swing_len=2, min_wick_ratio=0.0, min_wick_atr=0.0,
               atr_len=2, max_zones=1)
    # after bar 15, only the bullish zone should remain active
    assert out["RB_DIST_RES_2"].iloc[16:].isna().all(), "bearish zone must have been evicted"
    assert out["RB_DIST_SUP_2"].iloc[16:].notna().all(), "bullish zone must still be active"


def test_dist_res_prefers_zone_containing_price_over_farther_zone():
    # Fletcher round 1 renamed/re-derived this test (was
    # `..._ignores_stale_zone_below_price`, asserting the FARTHER zone B's
    # distance won). That assertion was measured against pre-MINOR-fix
    # code; it is no longer correct, for a structural reason worth stating
    # explicitly: a bearish zone's SPENT check (`close > zone.top`) fires
    # every bar, so an ACTIVE bearish zone can NEVER have `top < close` --
    # if it did, it would already have been spent and removed before this
    # bar's DIST computation runs. So "zone A, bot below close, still
    # active" can only ever mean `bot <= close <= top` -- CONTAINING
    # price, i.e. exactly the TAP-moment scenario the MINOR fix (see
    # rejection_blocks.py's `_new_zone`-adjacent dist_res/dist_sup block
    # comment) targets, not a genuinely wrong-side/stale zone (which is
    # structurally impossible here, unlike liquidity_sweep.py's point
    # levels with a separate broken-but-unresolved state).
    #
    # So this test's real, still-valuable job post-fix: prove a zone
    # CONTAINING price (distance 0, "you're already there") correctly
    # wins the argmin over a farther zone that's merely AHEAD (a smaller
    # positive distance) -- i.e. the raw (unclamped) `bot - c` key must
    # keep favoring the more-negative (contained) zone over the
    # less-negative-but-still-smaller positive value of an ahead-only
    # zone, not fall back to reporting the ahead zone once one candidate
    # is a match. An implementation that reverted to the pre-fix
    # `bot > c` filter would instead report zone B's (125-105)/105*100 =
    # 19.05 here -- this test fails loudly against that regression.
    #
    # Zone A (contains price): swing high at bar 5, top=200 (never spent
    # -- close never approaches 200), bot=101 (O=100,C=101) -- BELOW the
    # flood close of 105, so [101, 200] CONTAINS close=105.
    #
    # Zone B (genuine, farther): swing high at bar 15, top=140, bot=125
    # (O=124,C=125) -- entirely ABOVE the flood close of 105, genuine
    # overhead resistance at +19.05%.
    n = 25
    O, H, L, C = _flooded_ohlc(n, o=105.0, h=106.0, l=104.0, c=105.0)
    # L[5]=99.0 (not the flooded 104.0): required so open(100)/close(101)
    # both sit inside [low, high] (Fletcher MAJOR round 1 fix -- the
    # original 104.0 put both open and close BELOW low, an impossible
    # bar). Side effect: low=99.0 is now also a strict-unique local min
    # vs the flooded low=104.0, so this bar ALSO confirms a bullish zone
    # at bar 7 -- harmless here, this test asserts nothing about
    # RB_DIST_SUP/RB_TAP_BULL/RB_SPENT_BULL.
    O[5], H[5], L[5], C[5] = 100.0, 200.0, 99.0, 101.0
    O[15], H[15], L[15], C[15] = 124.0, 140.0, 104.0, 125.0
    out = _run(O, H, L, C, swing_len=2, min_wick_ratio=0.0, min_wick_atr=0.0, atr_len=2)

    assert out["RB_SPENT_BEAR_2"].sum() == 0, "zone A must never spend in this scenario -- both zones stay simultaneously active"
    dist_res = out["RB_DIST_RES_2"]
    post_b = dist_res.iloc[17:]
    assert post_b.notna().all(), "must be 0.0 (zone A contains price), never NaN"
    assert np.allclose(post_b.to_numpy(), 0.0, atol=1e-9), \
        "must pick zone A (contains price, distance 0), never fall back to zone B's farther 19.05%"


def test_dist_sup_prefers_zone_containing_price_over_farther_zone():
    # Mirror of the above on the support side. Same structural argument:
    # an active bullish zone's SPENT check (`close < zone.bot`) fires
    # every bar, so an active bullish zone can never have `bot > close`
    # -- "zone A, top above close, still active" can only mean
    # `bot <= close <= top`, containing price.
    #
    # Zone A (contains price): swing low at bar 5, bot=10 (never spent --
    # close never drops near 10), top=109 (O=110,C=109 -> body_bot=109) --
    # ABOVE the flood close of 105, so [10, 109] CONTAINS close=105.
    #
    # Zone B (genuine, farther): swing low at bar 15, top=85, bot=70
    # (O=86,C=85) -- entirely BELOW the flood close of 105, genuine
    # support at -19.05%.
    n = 25
    O, H, L, C = _flooded_ohlc(n, o=105.0, h=106.0, l=104.0, c=105.0)
    # H[5]=110.0 (not the flooded 106.0): required so open(110)/close(109)
    # both sit inside [low, high] (Fletcher MAJOR round 1 fix -- the
    # original 106.0 put both open and close ABOVE high, an impossible
    # bar). Side effect: high=110.0 is now also a strict-unique local max
    # vs the flooded high=106.0, so this bar ALSO confirms a bearish zone
    # at bar 7 -- harmless here, this test asserts nothing about
    # RB_DIST_RES/RB_TAP_BEAR/RB_SPENT_BEAR.
    O[5], H[5], L[5], C[5] = 110.0, 110.0, 10.0, 109.0
    O[15], H[15], L[15], C[15] = 86.0, 106.0, 70.0, 85.0
    out = _run(O, H, L, C, swing_len=2, min_wick_ratio=0.0, min_wick_atr=0.0, atr_len=2)

    assert out["RB_SPENT_BULL_2"].sum() == 0, "zone A must never spend -- both zones stay simultaneously active"
    dist_sup = out["RB_DIST_SUP_2"]
    post_b = dist_sup.iloc[17:]
    assert post_b.notna().all(), "must be 0.0 (zone A contains price), never NaN"
    assert np.allclose(post_b.to_numpy(), 0.0, atol=1e-9), \
        "must pick zone A (contains price, distance 0), never fall back to zone B's farther 19.05%"


def test_dist_res_zero_not_nan_while_price_inside_zone():
    # THE direct regression test for the Fletcher MINOR fix itself:
    # before the fix, DIST_RES went NaN exactly when price was AT or
    # INSIDE an active zone -- the precise moment RB_TAP_BEAR fires and an
    # ML consumer most needs a real number, not a missing one. This test
    # isolates a SINGLE zone (no second zone competing in the argmin) and
    # walks close from outside, to the exact near-edge boundary, to
    # strictly inside, checking DIST_RES is 0.0 (not NaN) throughout.
    n = 20
    O, H, L, C = _flooded_ohlc(n)
    # Bearish zone at bar 5 (as in test_bearish_tap_then_spent_lifecycle):
    # top=110, bot=101, confirms at bar 7.
    O[5], H[5], L[5], C[5] = 100.0, 110.0, 99.0, 101.0
    # Bar 10: close=105 -- strictly INSIDE [101, 110], not the boundary.
    O[10], H[10], L[10], C[10] = 104.0, 106.0, 103.0, 105.0
    # Bar 11: close=101 -- exactly AT the near edge (z.bot).
    O[11], H[11], L[11], C[11] = 101.0, 102.0, 100.0, 101.0
    out = _run(O, H, L, C, swing_len=2, min_wick_ratio=0.0, min_wick_atr=0.0, atr_len=2)

    assert out["RB_SPENT_BEAR_2"].sum() == 0, "zone must stay active (close never exceeds top=110) throughout"
    dist_res = out["RB_DIST_RES_2"]
    assert dist_res.iloc[10] == 0.0, "close=105 strictly inside [101,110] must report 0.0, not NaN"
    assert dist_res.iloc[11] == 0.0, "close=101 == z.bot (exact boundary) must report 0.0, not NaN"
    # bars outside the zone (flooded close=100 < bot=101) still report the
    # genuine positive distance, unaffected by the fix.
    assert dist_res.iloc[7] == 1.0
    assert dist_res.iloc[9] == 1.0


def test_dist_sup_zero_not_nan_while_price_inside_zone():
    # Mirror of the above on the support side.
    n = 20
    O, H, L, C = _flooded_ohlc(n)
    # Bullish zone at bar 5: top=99, bot=90, confirms at bar 7.
    O[5], H[5], L[5], C[5] = 100.0, 101.0, 90.0, 99.0
    # Bar 10: close=95 -- strictly INSIDE [90, 99].
    O[10], H[10], L[10], C[10] = 96.0, 97.0, 94.0, 95.0
    # Bar 11: close=99 -- exactly AT the near edge (z.top).
    O[11], H[11], L[11], C[11] = 99.0, 100.0, 98.0, 99.0
    out = _run(O, H, L, C, swing_len=2, min_wick_ratio=0.0, min_wick_atr=0.0, atr_len=2)

    assert out["RB_SPENT_BULL_2"].sum() == 0, "zone must stay active (close never drops below bot=90) throughout"
    dist_sup = out["RB_DIST_SUP_2"]
    assert dist_sup.iloc[10] == 0.0, "close=95 strictly inside [90,99] must report 0.0, not NaN"
    assert dist_sup.iloc[11] == 0.0, "close=99 == z.top (exact boundary) must report 0.0, not NaN"
    assert dist_sup.iloc[7] == 1.0
    assert dist_sup.iloc[9] == 1.0


# ---------------------------------------------------------------------------
# Causality -- mutation and truncation, matching liquidity_sweep.py's two
# independent checks.
# ---------------------------------------------------------------------------

def _random_walk_ohlc(n=200, seed=3):
    rng = np.random.RandomState(seed)
    idx = _idx(n)
    close = pd.Series(100 + np.cumsum(rng.randn(n) * 0.5), index=idx)
    high = close + np.abs(rng.randn(n)) * 0.6 + 0.05
    low = close - np.abs(rng.randn(n)) * 0.6 - 0.05
    open_ = close.shift(1).fillna(close.iloc[0])
    open_ = open_.clip(lower=low, upper=high)
    assert (low <= high).all(), "construction check: every bar must be physically valid"
    return open_, high, low, close


def test_causal_no_lookahead():
    open_, high, low, close = _random_walk_ohlc()
    out_full = ta.rejection_blocks(open_, high, low, close)
    t = 120

    rng = np.random.RandomState(99)
    open2, high2, low2, close2 = open_.copy(), high.copy(), low.copy(), close.copy()
    n = len(close)
    shock = rng.randn(n - t - 1) * 5
    close2.iloc[t + 1:] = close2.iloc[t + 1:] + shock
    high2.iloc[t + 1:] = np.maximum(high2.iloc[t + 1:], close2.iloc[t + 1:]) + 1.0
    low2.iloc[t + 1:] = np.minimum(low2.iloc[t + 1:], close2.iloc[t + 1:]) - 1.0
    open2.iloc[t + 1:] = close2.shift(1).iloc[t + 1:]
    open2.iloc[t + 1:] = open2.iloc[t + 1:].clip(lower=low2.iloc[t + 1:], upper=high2.iloc[t + 1:])
    assert (low2 <= high2).all(), "construction check: every bar must be physically valid"

    out_mut = ta.rejection_blocks(open2, high2, low2, close2)
    pd.testing.assert_frame_equal(out_full.iloc[:t + 1], out_mut.iloc[:t + 1])


def test_causal_deletion_no_lookahead():
    open_, high, low, close = _random_walk_ohlc()
    out_full = ta.rejection_blocks(open_, high, low, close)
    t = 120
    out_trunc = ta.rejection_blocks(open_.iloc[:t + 1], high.iloc[:t + 1],
                                     low.iloc[:t + 1], close.iloc[:t + 1])
    pd.testing.assert_frame_equal(out_full.iloc[:t + 1], out_trunc)


# ---------------------------------------------------------------------------
# Reachability
# ---------------------------------------------------------------------------

def test_reachable_via_category_and_accessor():
    assert "rejection_blocks" in ta.Category["trend"]
    open_, high, low, close = _random_walk_ohlc(n=60)
    df = pd.DataFrame({"open": open_, "high": high, "low": low, "close": close})
    assert callable(getattr(df.ta, "rejection_blocks"))
    direct = ta.rejection_blocks(open_, high, low, close)
    via_accessor = df.ta.rejection_blocks()
    pd.testing.assert_frame_equal(direct, via_accessor)


# ---------------------------------------------------------------------------
# Invalid-input validation (nan/inf/non-integral -- gate over
# liquidity_sweep.py's bare int()/float() coercions)
# ---------------------------------------------------------------------------

def _bars(n=50, seed=1):
    rng = np.random.RandomState(seed)
    idx = _idx(n)
    close = pd.Series(100 + np.cumsum(rng.randn(n)), index=idx)
    high = close + 1
    low = close - 1
    open_ = close
    return open_, high, low, close


@pytest.mark.parametrize("kwargs", [
    dict(swing_len=float("nan")),
    dict(swing_len=float("inf")),
    dict(swing_len=3.7),
    dict(swing_len=0),
    dict(swing_len=-1),
    dict(min_wick_ratio=float("nan")),
    dict(min_wick_ratio=float("inf")),
    dict(min_wick_ratio=-0.1),
    dict(min_wick_atr=float("-inf")),
    dict(min_wick_atr=-0.5),
    dict(atr_len=float("-inf")),
    dict(atr_len=0),
    dict(max_zones=0),
    dict(max_zones=-2),
])
def test_invalid_params_raise_value_error(kwargs):
    open_, high, low, close = _bars()
    with pytest.raises(ValueError):
        ta.rejection_blocks(open_, high, low, close, **kwargs)


def test_none_params_use_documented_defaults():
    open_, high, low, close = _bars()
    out = ta.rejection_blocks(open_, high, low, close, swing_len=None,
                               min_wick_ratio=None, min_wick_atr=None,
                               atr_len=None, max_zones=None)
    assert list(out.columns) == [
        "RB_TAP_BULL_3", "RB_TAP_BEAR_3", "RB_SPENT_BULL_3",
        "RB_SPENT_BEAR_3", "RB_DIST_RES_3", "RB_DIST_SUP_3",
    ]


# ---------------------------------------------------------------------------
# Attribution (gate e)
# ---------------------------------------------------------------------------

def test_docstring_names_source_and_author():
    # URL is line-wrapped in the docstring for readability (same as
    # liquidity_sweep.py/sphinx_unicorn.py's docstrings), so check the
    # normalized (whitespace-collapsed) text for the full URL rather than
    # an exact substring match that would break on the wrap point.
    doc = ta.rejection_blocks.__doc__
    normalized = " ".join(doc.split())
    assert "https://www.tradingview.com/script/ QjOFE86I-Kale-Rejection-Blocks-John-3-16/" in normalized \
        or "https://www.tradingview.com/script/QjOFE86I-Kale-Rejection-Blocks-John-3-16/" in normalized
    assert "lezama03" in doc
    assert "Kale Rejection Blocks" in doc


# ---------------------------------------------------------------------------
# Column naming / dtype sanity
# ---------------------------------------------------------------------------

def test_flag_columns_are_binary_and_dist_columns_are_percent_scale():
    open_, high, low, close = _random_walk_ohlc(n=300, seed=7)
    out = ta.rejection_blocks(open_, high, low, close)
    for col in ("RB_TAP_BULL_3", "RB_TAP_BEAR_3", "RB_SPENT_BULL_3", "RB_SPENT_BEAR_3"):
        assert set(out[col].unique()).issubset({0, 1})
    for col in ("RB_DIST_RES_3", "RB_DIST_SUP_3"):
        vals = out[col].dropna()
        if len(vals):
            assert (vals >= 0).all()
            # a %-of-close distance on this random-walk scale should never
            # run away to an absurd magnitude
            assert (vals < 100).all()
