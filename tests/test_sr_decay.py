# tests/test_sr_decay.py
"""sr_decay (SRD) -- companion port to sr_force.py: the source's two OTHER
per-level scalars sr_force.py deliberately left out, `calcAttenuation` and
`calcSwirl` (TVPTA continuation, ported from "ATK/DEF Support Resistance
S/R Channel Rating Engine" -- a documented superset of sr_force.py's own
source, "ATK/DEF Support Resistance SR Force Matrix"). Self-contained on
synthetic data, same conventions as tests/test_sr_force.py: physically
valid OHLC discipline (every bar satisfies `low <= close <= high` AND
`low <= high` -- `_valid_hlc` below asserts both), reachability tested via
`import pandas_ta` (`.context`), causality via mutation + truncation.

`_attenuation` is fully hand-derivable (no ATR dependency -- just
price/close/a precomputed `time_decay` constant), so its isolated unit
tests below use plain hand math. `_swirl` depends on real ATR(14)
(Wilder/RMA) and a 14-bar SMA of `high - low`; its isolated unit tests use
small SYNTHETIC `atr_v`/`hl_sma_v` numpy arrays (not a real ATR
computation) so the swirl MATH itself is fully hand-derivable, while the
end-to-end `sr_decay()` scenarios below cross-validate the WIRING (pivot
confirmation -> per-side FIFO pool -> side-constrained nearest-level
lookup) by calling `_swirl` directly with the SAME `atr_v`/`hl_sma_v`
arrays `sr_decay()` computes internally (via the fork's own `atr()` and a
plain rolling mean) -- this is the same "cross-check via calling the
helper directly" precedent `tests/test_sr_force.py` uses for scenarios too
compound to hand-derive digit-by-digit.
"""
import math

import numpy as np
import pandas as pd
import pytest

from .context import pandas_ta as ta
from pandas_ta.trend.sr_decay import (
    _confirm_strict_pivots, _validated_int, _attenuation, _swirl,
)
from pandas_ta.volatility import atr as _atr


def _idx(n):
    return pd.date_range("2020-01-01", periods=n, freq="B")


def _valid_hlc(H, L, C):
    assert (L <= C).all() and (C <= H).all() and (L <= H).all(), \
        "construction check: every bar must satisfy low <= close <= high"


# ---------------------------------------------------------------------------
# _confirm_strict_pivots -- isolated unit tests (duplicated per-file, same
# convention as sr_force.py / liquidity_sweep.py / rejection_blocks.py)
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
# _validated_int -- isolated unit tests (nan/inf/non-integral discipline)
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


# ---------------------------------------------------------------------------
# _attenuation -- isolated unit tests, fully hand-derived (no ATR needed)
# ---------------------------------------------------------------------------

def test_attenuation_no_price_move_is_time_decay_only():
    # price == close_t -> price_decay = 0; attenuation = time_decay * 0.6
    got = _attenuation(price=100.0, close_t=100.0, time_decay=0.1)
    assert math.isclose(got, 0.06, rel_tol=1e-12)


def test_attenuation_five_pct_move():
    # priceChange = 5% -> price_decay = min(5/10, 1) = 0.5
    got = _attenuation(price=100.0, close_t=105.0, time_decay=0.1)
    expected = 0.1 * 0.6 + 0.5 * 0.4
    assert math.isclose(got, expected, rel_tol=1e-12)
    assert math.isclose(expected, 0.26, rel_tol=1e-9)


def test_attenuation_price_decay_caps_at_one():
    # 50% price move -> price_decay would be 5.0 uncapped, clipped to 1.0
    got = _attenuation(price=100.0, close_t=150.0, time_decay=0.1)
    expected = 0.1 * 0.6 + 1.0 * 0.4
    assert math.isclose(got, expected, rel_tol=1e-12)


def test_attenuation_saturates_at_one_when_both_terms_max():
    # Fletcher round 2 (MINOR): this test's comment used to claim it
    # proved the source's final `min(attenuation, 1.0)` cap was doing
    # real work, "not merely a coincidence of the two sub-term caps".
    # That was FALSE and provably so -- with time_decay and price_decay
    # each already clipped to [0,1], `td*0.6 + pd*0.4` has a maximum of
    # exactly 1.0, so the final cap can never reduce anything: it is
    # arithmetically unreachable dead code. Verified by mutation:
    # deleting the final `min(..., 1.0)` from `_attenuation` leaves the
    # ENTIRE file green. The cap is retained in the port only for source
    # fidelity (the same "translate the math as computed" discipline the
    # module docstring invokes for the /10-vs-11 swirl divisor), NOT
    # because it is load-bearing. What this test actually pins is the
    # saturation VALUE when both sub-terms are already at their caps.
    got = _attenuation(price=100.0, close_t=200.0, time_decay=1.0)
    assert got == 1.0


def test_attenuation_returns_nan_for_non_positive_price():
    # Fletcher round 2 (MINOR): the round-1 `price <= 0 -> np.nan` guard
    # shipped with ZERO coverage -- reverting it to the pre-guard body
    # (which raised ZeroDivisionError) failed 0 of 49 tests, because every
    # other `_attenuation` call site in this file passes price=100.0.
    # A non-positive price is unreachable on real market data, but this is
    # one of TWO code paths that yield a NaN ATTEN alongside a real SWIRL
    # -- the other is a NaN Close on a level's own confirming bar with a
    # real High/Low. Fletcher round 4: that path was previously called
    # "reachable on real data" without measurement; it is NOT observed --
    # 0 of 7,038,656 bars across datastore/cache{,_hourly,_crypto} carry a
    # NaN Close at all. Both paths are defensive-contract, not observed;
    # see test_attenuation_returns_nan_for_nan_close_t below. Fletcher round 3
    # (MAJOR): this comment, §2h, and the module docstring all previously
    # claimed the price<=0 path was "the ONLY" such exception. False --
    # `_attenuation` consumes Close[t] while `ATR(14)[t]`'s true range
    # reads Close[t-1] and never Close[t], so a NaN Close nulls ATTEN and
    # leaves SWIRL real.
    assert np.isnan(_attenuation(price=0.0, close_t=100.0, time_decay=0.1))
    assert np.isnan(_attenuation(price=-5.0, close_t=100.0, time_decay=0.1))


def test_attenuation_returns_nan_for_nan_close_t():
    # Fletcher round 3 (MAJOR): the SECOND code path breaking
    # `ATTEN.isna() => SWIRL.isna()`. ⚠ Round 4: an earlier version of
    # this comment called it "the one that actually occurs on real data"
    # -- unmeasured and wrong (0 of 7,038,656 datastore bars have a NaN
    # Close). ⚠ Round 5: this comment previously said a fully missing
    # session (H/L/C all NaN) nulls ATR and SWIRL too, so the implication
    # would HOLD there -- reasoned, not run, and false. ATR(14) is
    # RMA-smoothed and steps over the NaN true range, so an all-NaN bar
    # breaks the implication on the same 17 rows (measured: ATR[22]=2.504).
    # ANY NaN Close on a confirming bar breaks it, High/Low real or not.
    # `_attenuation` consumes
    # Close[t] directly, so a NaN Close nulls it; `_swirl` does NOT,
    # because `ATR(14)[t]`'s true range reads Close[t-1], never Close[t].
    # Three documents previously called the price<=0 path "the ONLY" way
    # to break the implication -- measured counterexample below proves
    # otherwise on strictly positive prices.
    assert np.isnan(_attenuation(price=100.0, close_t=float("nan"), time_decay=0.1))


def test_nan_close_on_confirming_bar_breaks_atten_swirl_implication_end_to_end():
    # The end-to-end half: every price in this frame is >= 99.0 (strictly
    # positive, so the price<=0 guard is NOT what fires), yet a NaN Close
    # on the confirming bar produces rows where ATTEN is NaN while SWIRL
    # is real -- i.e. `(atten.notna() | swirl.isna()).all()` is False.
    # Measured: 17 such rows on this construction.
    n = 40
    H, L, C = _flooded_hlc(n)
    H[20], L[20], C[20] = 107.0, 99.0, 100.0   # swing high, confirms at 22
    C[22] = np.nan                              # halted/missing session close
    assert np.nanmin(np.concatenate([H, L, C])) > 0.0, \
        "construction check: every price must be strictly positive, so price<=0 is not the cause"
    # Deliberately bypasses `_run`/`_valid_hlc`: that guard asserts
    # `low <= close <= high`, which a NaN close can never satisfy (every
    # NaN comparison is False). A missing session close is MISSING DATA,
    # not a physically impossible bar -- the distinction the guard exists
    # to enforce. Validity is asserted below on the non-NaN bars only.
    real = ~np.isnan(C)
    assert (L[real] <= C[real]).all() and (C[real] <= H[real]).all() and (L <= H).all(), \
        "construction check: every bar with a real close must satisfy low <= close <= high"
    idx = _idx(len(H))
    out = ta.sr_decay(pd.Series(H, index=idx), pd.Series(L, index=idx),
                      pd.Series(C, index=idx), swing_len=2, max_levels=20)
    atten = out["SRD_ATTEN_RES_2"]
    swirl = out["SRD_SWIRL_RES_2"]
    asymmetric = (atten.isna() & swirl.notna())
    # Fletcher round 4 (NIT): assert the EXACT count, not just > 0 --
    # family-structure-smc.md §2h publishes "17 rows" in bold, so any
    # drift in _flooded_hlc/swing_len/the pivot rule must fail here rather
    # than silently rotting the published number behind a green suite.
    assert asymmetric.sum() == 17, \
        f"expected exactly 17 ATTEN-NaN/SWIRL-real rows (the count published in " \
        f"family-structure-smc.md §2h), got {int(asymmetric.sum())} at " \
        f"{list(np.nonzero(asymmetric.to_numpy())[0])}"
    assert not (atten.notna() | swirl.isna()).all(), \
        "this is the documented counterexample: the implication must NOT hold here"


def test_attenuation_symmetric_in_direction():
    # abs() in the source -- a move down must decay identically to the
    # same-magnitude move up.
    up = _attenuation(price=100.0, close_t=105.0, time_decay=0.1)
    down = _attenuation(price=100.0, close_t=95.0, time_decay=0.1)
    assert math.isclose(up, down, rel_tol=1e-12)


# ---------------------------------------------------------------------------
# _swirl -- isolated unit tests, fully hand-derived on synthetic atr_v /
# hl_sma_v arrays (a real ATR/SMA computation is not needed to pin down
# the swirl MATH itself; end-to-end wiring is covered separately below).
# ---------------------------------------------------------------------------

def test_swirl_constant_ratio_and_volatility_change():
    n = 15
    t = 14
    bars_ago = 5  # pivot_idx = 9
    atr_v = np.full(n, 2.0)
    atr_v[9] = 1.0    # atrNear
    atr_v[14] = 3.0   # atrCurrent -> volatility_change = 3.0
    high_v = np.full(n, 101.0)
    low_v = np.full(n, 100.0)   # high-low = 1.0 for every bar
    hl_sma_v = np.full(n, 1.0)  # ratio = 1.0 for every bar in the i=0..10 scan
    got = _swirl(atr_v, hl_sma_v, high_v, low_v, t, bars_ago)
    # 11 terms of ratio 1.0 -> swirl_sum=11, swirl_avg=11/10=1.1, *3.0=3.3
    assert math.isclose(got, 3.3, rel_tol=1e-12)


def test_swirl_caps_at_five():
    n = 15
    t = 14
    bars_ago = 5
    atr_v = np.full(n, 2.0)
    atr_v[9] = 1.0
    atr_v[14] = 3.0
    high_v = np.full(n, 103.0)
    low_v = np.full(n, 101.0)   # high-low = 2.0
    hl_sma_v = np.full(n, 1.0)  # ratio = 2.0 for every bar
    got = _swirl(atr_v, hl_sma_v, high_v, low_v, t, bars_ago)
    # 11 terms of ratio 2.0 -> swirl_sum=22, swirl_avg=2.2, *3.0=6.6 -> capped
    assert got == 5.0


def test_swirl_atr_near_fallback_when_nan():
    n = 15
    t = 14
    bars_ago = 5
    atr_v = np.full(n, 2.0)
    atr_v[9] = np.nan     # atrNear is NaN -> falls back to atrCurrent
    atr_v[14] = 4.0       # atrCurrent
    high_v = np.full(n, 101.0)
    low_v = np.full(n, 100.0)
    hl_sma_v = np.full(n, 1.0)
    got = _swirl(atr_v, hl_sma_v, high_v, low_v, t, bars_ago)
    # atrNear falls back to atrCurrent (4.0) -> volatility_change = 4.0/4.0 = 1.0
    assert math.isclose(got, 1.1, rel_tol=1e-12)  # swirl_avg(1.1) * 1.0


def test_swirl_atr_near_fallback_when_zero_or_negative():
    n = 15
    t = 14
    bars_ago = 5
    atr_v = np.full(n, 2.0)
    atr_v[9] = 0.0    # atrNear invalid (<=0) -> falls back to atrCurrent
    atr_v[14] = 4.0
    high_v = np.full(n, 101.0)
    low_v = np.full(n, 100.0)
    hl_sma_v = np.full(n, 1.0)
    got = _swirl(atr_v, hl_sma_v, high_v, low_v, t, bars_ago)
    assert math.isclose(got, 1.1, rel_tol=1e-12)


def test_swirl_returns_nan_when_both_atr_invalid():
    n = 15
    t = 14
    bars_ago = 5
    atr_v = np.full(n, 2.0)
    atr_v[9] = np.nan
    atr_v[14] = np.nan   # both invalid -> NaN result, no crash
    high_v = np.full(n, 101.0)
    low_v = np.full(n, 100.0)
    hl_sma_v = np.full(n, 1.0)
    got = _swirl(atr_v, hl_sma_v, high_v, low_v, t, bars_ago)
    assert np.isnan(got)


def test_swirl_skips_bars_with_invalid_normalizer():
    # avgRange <= 0 (or NaN) at a scanned bar must be SKIPPED (contributes
    # 0), not treated as a division error or forcing the whole result NaN.
    n = 15
    t = 14
    bars_ago = 5
    atr_v = np.full(n, 2.0)
    atr_v[9] = 1.0
    atr_v[14] = 3.0
    high_v = np.full(n, 101.0)
    low_v = np.full(n, 100.0)
    hl_sma_v = np.full(n, 1.0)
    hl_sma_v[10] = 0.0   # one of the 11 scanned bars (j=10, i=4) has an
                          # invalid normalizer -> skipped, only 10 terms count
    got = _swirl(atr_v, hl_sma_v, high_v, low_v, t, bars_ago)
    # 10 terms of ratio 1.0 -> swirl_sum=10, swirl_avg=10/10=1.0, *3.0=3.0
    # (the divisor is STILL 10, the source's fixed divisor, not the count
    # of valid terms -- see the module docstring's off-by-one-quirk note)
    assert math.isclose(got, 3.0, rel_tol=1e-12)


def test_swirl_early_history_truncates_scan_not_crash():
    # t smaller than the 11-bar scan reach -- j = t - i going negative
    # must be skipped, matching Pine's own start-of-history na guard.
    n = 8
    t = 7
    bars_ago = 5  # pivot_idx = 2
    atr_v = np.full(n, 2.0)
    atr_v[7] = 3.0
    high_v = np.full(n, 101.0)
    low_v = np.full(n, 100.0)
    hl_sma_v = np.full(n, 1.0)
    got = _swirl(atr_v, hl_sma_v, high_v, low_v, t, bars_ago)
    # i=0..7 valid (j=7..0), i=8..10 skipped (j<0) -> 8 terms of ratio 1.0
    # atrNear = atr_v[2] = 2.0 (untouched default) -> volatility_change = 3.0/2.0 = 1.5
    expected = (8 / 10.0) * 1.5
    assert math.isclose(got, expected, rel_tol=1e-12)


# ---------------------------------------------------------------------------
# End-to-end sr_decay() scenarios
# ---------------------------------------------------------------------------

def _flooded_hlc(n, h=101.0, l=99.0, c=100.0):
    H = np.full(n, h)
    L = np.full(n, l)
    C = np.full(n, c)
    return H, L, C


def _run(H, L, C, **kwargs):
    _valid_hlc(H, L, C)
    idx = _idx(len(H))
    return ta.sr_decay(pd.Series(H, index=idx), pd.Series(L, index=idx),
                        pd.Series(C, index=idx), **kwargs)


def _expected_swirl(H, L, C, t, swing_len):
    """Cross-check helper: builds the SAME atr_v/hl_sma_v arrays sr_decay()
    computes internally (via the fork's own atr() and a plain rolling
    mean of high-low), then calls _swirl directly. Validates the
    end-to-end WIRING (pivot confirmation -> pool -> side-constrained
    nearest lookup), not an independently re-derived RMA computation --
    the isolated _swirl unit tests above already hand-derive the swirl
    MATH itself on synthetic atr_v arrays."""
    idx = _idx(len(H))
    high = pd.Series(H, index=idx)
    low = pd.Series(L, index=idx)
    close = pd.Series(C, index=idx)
    atr_v = _atr(high, low, close, length=14).to_numpy(dtype=float)
    hl_sma_v = (high - low).rolling(14).mean().to_numpy(dtype=float)
    return _swirl(atr_v, hl_sma_v, H, L, t, swing_len)


def test_resistance_level_confirms_and_reports_atten_swirl_end_to_end():
    # Swing high at bar 20 (H=110, unique vs flooded H=101), confirms at
    # bar 22 (swing_len=2). ATR(14)/SMA(high-low,14) have long warmed up
    # to the flooded constant (TR=2.0 for 20 bars before the spike).
    n = 40
    H, L, C = _flooded_hlc(n)
    H[20], L[20], C[20] = 110.0, 99.0, 100.0
    out = _run(H, L, C, swing_len=2, max_levels=20)

    atten_res = out["SRD_ATTEN_RES_2"]
    swirl_res = out["SRD_SWIRL_RES_2"]
    assert atten_res.iloc[:22].isna().all()
    assert swirl_res.iloc[:22].isna().all()

    # ATTEN: price=110 (the pivot's own price), close_t = C[22] = 100.0
    # (flood resumed) -> price_change_pct = |100-110|/110*100
    price_change_pct = abs(100.0 - 110.0) / 110.0 * 100.0
    time_decay = min(2 / 50.0, 1.0)
    price_decay = min(price_change_pct / 10.0, 1.0)
    expected_atten = min(time_decay * 0.6 + price_decay * 0.4, 1.0)
    assert math.isclose(atten_res.iloc[22], expected_atten, rel_tol=1e-9)
    # level persists (no removal mechanism besides the FIFO cap) for every
    # subsequent bar in this scenario
    assert atten_res.iloc[22:].eq(atten_res.iloc[22]).all()

    expected_swirl = _expected_swirl(H, L, C, 22, 2)
    assert not np.isnan(expected_swirl), "test construction check: ATR/SMA must be warmed up by bar 22"
    assert math.isclose(swirl_res.iloc[22], expected_swirl, rel_tol=1e-9)
    assert swirl_res.iloc[22:].eq(swirl_res.iloc[22]).all()

    # never a support event anywhere in this purely-resistance scenario
    assert out["SRD_ATTEN_SUP_2"].isna().all()
    assert out["SRD_SWIRL_SUP_2"].isna().all()


def test_support_level_confirms_and_reports_atten_swirl_mirrors_resistance():
    n = 40
    H, L, C = _flooded_hlc(n)
    H[20], L[20], C[20] = 101.0, 90.0, 100.0
    out = _run(H, L, C, swing_len=2, max_levels=20)

    atten_sup = out["SRD_ATTEN_SUP_2"]
    swirl_sup = out["SRD_SWIRL_SUP_2"]
    assert atten_sup.iloc[:22].isna().all()

    price_change_pct = abs(100.0 - 90.0) / 90.0 * 100.0
    time_decay = min(2 / 50.0, 1.0)
    price_decay = min(price_change_pct / 10.0, 1.0)
    expected_atten = min(time_decay * 0.6 + price_decay * 0.4, 1.0)
    assert math.isclose(atten_sup.iloc[22], expected_atten, rel_tol=1e-9)
    assert atten_sup.iloc[22:].eq(atten_sup.iloc[22]).all()

    expected_swirl = _expected_swirl(H, L, C, 22, 2)
    assert not np.isnan(expected_swirl)
    assert math.isclose(swirl_sup.iloc[22], expected_swirl, rel_tol=1e-9)

    assert out["SRD_ATTEN_RES_2"].isna().all()
    assert out["SRD_SWIRL_RES_2"].isna().all()


def test_atten_res_excludes_level_price_has_moved_below():
    # Fletcher-lesson-applied test (sr_force.py's own Fletcher-MAJOR
    # precedent, itself citing liquidity_sweep.py's original finding): a
    # level still IN the pool (no break/sweep removal exists here, only
    # the FIFO cap) must still be EXCLUDED from the nearest-resistance
    # query the moment price has moved above it.
    #
    # Regime 1 (bars 0-19, flood close=100): swing high at bar 5 (H=110)
    # confirms at bar 7 -> level A, price=110, active while close=100.
    # Regime 2 (bars 20+, flood close=200, roughly a 2x rally): level A is
    # now BELOW close -- must be excluded. A NEW swing high at bar 25
    # (H=210) confirms at bar 27 -> level B, genuinely above the new
    # close (200).
    n = 40
    H = np.full(n, 101.0); L = np.full(n, 99.0); C = np.full(n, 100.0)
    H[5], L[5], C[5] = 110.0, 99.0, 100.0
    H[20:], L[20:], C[20:] = 201.0, 199.0, 200.0
    H[25], L[25], C[25] = 210.0, 199.0, 200.0
    out = _run(H, L, C, swing_len=2, max_levels=20)

    atten_res = out["SRD_ATTEN_RES_2"]
    swirl_res = out["SRD_SWIRL_RES_2"]
    assert not atten_res.iloc[7:20].isna().any(), "level A must be active pre-rally"
    assert atten_res.iloc[20:27].isna().all(), \
        "level A must be excluded once price has moved above it, even though it is still in the pool"
    assert swirl_res.iloc[20:27].isna().all()
    assert not atten_res.iloc[27:].isna().any(), "level B must be active post-confirmation"
    # level A and level B have different prices/close_t at confirmation ->
    # different attenuation, proving this is really level B, not a stale
    # level A value slipping through
    assert not math.isclose(atten_res.iloc[27], atten_res.iloc[19], rel_tol=1e-9)


def test_atten_sup_excludes_level_price_has_moved_above():
    # Mirror of the above on the support side: a crash leaves a former
    # support level ABOVE the new, lower close.
    n = 40
    H = np.full(n, 101.0); L = np.full(n, 99.0); C = np.full(n, 100.0)
    H[5], L[5], C[5] = 101.0, 90.0, 100.0
    H[20:], L[20:], C[20:] = 51.0, 49.0, 50.0
    L[25], H[25], C[25] = 40.0, 51.0, 50.0
    out = _run(H, L, C, swing_len=2, max_levels=20)

    atten_sup = out["SRD_ATTEN_SUP_2"]
    assert not atten_sup.iloc[7:20].isna().any()
    assert atten_sup.iloc[20:27].isna().all(), \
        "level A (support=90) must be excluded once price has fallen below it"
    assert not atten_sup.iloc[27:].isna().any()


def test_max_levels_fifo_cap_resistance_side():
    # max_levels=1: level 1 (price=105, confirms bar 7) must be EVICTED
    # the instant level 2 (price=120, confirms bar 22) is pushed -- ATTEN
    # must jump straight to level 2's value, never level 1's.
    n = 30
    H = np.full(n, 101.0); L = np.full(n, 99.0); C = np.full(n, 100.0)
    H[5], L[5], C[5] = 105.0, 99.0, 100.0
    H[20], L[20], C[20] = 120.0, 99.0, 100.0
    out = _run(H, L, C, swing_len=2, max_levels=1)

    atten_res = out["SRD_ATTEN_RES_2"]
    assert not atten_res.iloc[7:22].isna().any()
    level1_atten = atten_res.iloc[7]
    assert atten_res.iloc[7:22].eq(level1_atten).all()
    level2_atten = atten_res.iloc[22]
    assert not math.isclose(level2_atten, level1_atten, rel_tol=1e-9), \
        "level 1 must be evicted, not still reported, once level 2 confirms under max_levels=1"
    assert atten_res.iloc[22:].eq(level2_atten).all()


def test_max_levels_fifo_cap_support_side():
    # Fletcher NIT: the resistance-side test above was misleadingly named
    # "_per_side" while only ever exercising the resistance pool -- a
    # copy-paste inversion in sr_decay.py's support-side eviction branch
    # (`sup_levels.pop(0)`) would have gone uncaught. Mirror on the
    # support side: level 1 (price=95, confirms bar 7) must be EVICTED the
    # instant level 2 (price=80, confirms bar 22) is pushed under
    # max_levels=1.
    n = 30
    H = np.full(n, 101.0); L = np.full(n, 99.0); C = np.full(n, 100.0)
    H[5], L[5], C[5] = 101.0, 95.0, 100.0
    H[20], L[20], C[20] = 101.0, 80.0, 100.0
    out = _run(H, L, C, swing_len=2, max_levels=1)

    atten_sup = out["SRD_ATTEN_SUP_2"]
    assert not atten_sup.iloc[7:22].isna().any()
    level1_atten = atten_sup.iloc[7]
    assert atten_sup.iloc[7:22].eq(level1_atten).all()
    level2_atten = atten_sup.iloc[22]
    assert not math.isclose(level2_atten, level1_atten, rel_tol=1e-9), \
        "level 1 must be evicted, not still reported, once level 2 confirms under max_levels=1"
    assert atten_sup.iloc[22:].eq(level2_atten).all()


def test_atten_and_swirl_report_real_values_not_nan_when_close_equals_level_price():
    # THE dedicated regression test for the Fletcher-MAJOR fix
    # sr_force.py's DIST/SCORE columns already established: before that
    # fix, side-constraint filters used strict >/<, so Close landing
    # EXACTLY on a level's price reported NaN instead of the level's real
    # (frozen-at-creation) value. Applied here from the start.
    #
    # Resistance: swing high at bar 20 (H=107, unique vs flooded H=101),
    # confirms at bar 22 -> level A, price=107. Placed at bar 20 (not
    # earlier) so ATR(14)/SMA(high-low,14) are already warmed up by the
    # confirming bar -- this test's SWIRL assertion needs a REAL (not
    # early-history-NaN) swirl value to be meaningful; see
    # test_atten_real_swirl_permanently_nan_for_early_history_level for
    # the (expected, documented) early-history NaN-swirl case this
    # deliberately avoids. At bar 30, Close is set to EXACTLY 107 (H/L
    # widened just enough to keep the bar physically valid; this
    # incidentally also creates a brand new candidate resistance pivot at
    # bar 30, but it would not confirm until bar 32 -- irrelevant to this
    # test, which only asserts bar 30 itself).
    n = 40
    H, L, C = _flooded_hlc(n)
    H[20], L[20], C[20] = 107.0, 99.0, 100.0
    H[30], L[30], C[30] = 107.5, 106.5, 107.0
    out = _run(H, L, C, swing_len=2, max_levels=20)

    atten_res = out["SRD_ATTEN_RES_2"]
    swirl_res = out["SRD_SWIRL_RES_2"]
    assert not np.isnan(atten_res.iloc[22])
    assert not np.isnan(swirl_res.iloc[22]), "test construction check: ATR/SMA must be warmed up by bar 22"
    assert atten_res.iloc[30] == atten_res.iloc[22], \
        "must report level A's real (frozen-at-creation) attenuation, never NaN, at the exact equality boundary"
    assert swirl_res.iloc[30] == swirl_res.iloc[22], \
        "must report level A's real (frozen-at-creation) swirl, never NaN, at the exact equality boundary"


def test_atten_and_swirl_report_real_values_not_nan_when_close_equals_level_price_support_mirror():
    n = 40
    H, L, C = _flooded_hlc(n)
    H[20], L[20], C[20] = 101.0, 93.0, 100.0
    H[30], L[30], C[30] = 93.5, 92.5, 93.0
    out = _run(H, L, C, swing_len=2, max_levels=20)

    atten_sup = out["SRD_ATTEN_SUP_2"]
    swirl_sup = out["SRD_SWIRL_SUP_2"]
    assert not np.isnan(atten_sup.iloc[22])
    assert not np.isnan(swirl_sup.iloc[22]), "test construction check: ATR/SMA must be warmed up by bar 22"
    assert atten_sup.iloc[30] == atten_sup.iloc[22], \
        "must report the level's real attenuation, never NaN, at the exact equality boundary"
    assert swirl_sup.iloc[30] == swirl_sup.iloc[22], \
        "must report the level's real swirl, never NaN, at the exact equality boundary"


def test_atten_swirl_bounded_and_atten_isna_implies_swirl_isna():
    # Fletcher MAJOR (round 1): the expression previously shipped here was
    # `(atten.isna() | swirl.notna()).all()`, which is
    # `atten.notna() => swirl.notna()` -- the LOGICAL INVERSE of the
    # documented invariant, and it happened to pass only because seed=11/
    # n=250 has no pivot confirming before ATR(14) warms up on this
    # particular fixture (no statistical power to catch the bug it
    # claimed to guard). The correct proposition, matching this test's own
    # (unchanged) failure message and the module docstring's account of
    # why the ATTEN/SWIRL relationship is one-directional (NOT
    # sr_force.py's fully two-way SCORE/DIST pairing), is
    # `atten.isna() => swirl.isna()`, i.e. `atten.notna() | swirl.isna()`.
    # The POSITIVE case this bound alone cannot exercise -- a level that
    # actually HAS real ATTEN alongside permanently-NaN SWIRL -- is
    # covered end-to-end by
    # test_atten_real_swirl_permanently_nan_for_early_history_level below.
    #
    # Fletcher round 2 (NIT) -- the honest limit of THIS test: on
    # seed=11/n=250 the atten/swirl NaN masks are IDENTICAL (37/37 RES,
    # 19/19 SUP), i.e. zero asymmetric rows in EITHER direction, so the
    # implication cannot be "demonstrated" here -- reverting it to the
    # round-0 buggy polarity leaves this file green. It earns its place as
    # a REGRESSION GUARD, not a demonstration: it does bite an
    # `_attenuation`-returns-NaN mutation, including the newly reachable
    # `price <= 0` path. The bound half is likewise slack on this fixture
    # (measured ATTEN 0.101..0.170 / 0.076..0.217 against a 1.0 cap; SWIRL
    # 0.803..1.322 / 0.602..1.602 against a 5.0 cap). The DEMONSTRATED
    # asymmetric case lives in the early-history test below; the caps live
    # in the isolated `_attenuation`/`_swirl` unit tests above.
    open_, high, low, close = _random_walk_ohlc(n=250, seed=11)
    out = ta.sr_decay(high, low, close)
    for atten_col, swirl_col in (("SRD_ATTEN_RES_5", "SRD_SWIRL_RES_5"),
                                  ("SRD_ATTEN_SUP_5", "SRD_SWIRL_SUP_5")):
        atten = out[atten_col]
        swirl = out[swirl_col]
        assert (atten.notna() | swirl.isna()).all(), \
            f"{atten_col}.isna() must imply {swirl_col}.isna() (no side-valid level -> both NaN)"
        pop_atten = atten.dropna()
        pop_swirl = swirl.dropna()
        assert len(pop_atten) > 0, "test construction check: must actually produce populated levels"
        assert (pop_atten >= 0.0).all() and (pop_atten <= 1.0).all()
        # Fletcher round 2 (MINOR): this was `if len(pop_swirl):`, so
        # stubbing _swirl to return NaN unconditionally left the test
        # GREEN (bound branch skipped; the implication above is trivially
        # all-True when swirl is entirely NaN). Mirrors the atten branch's
        # hard construction check now.
        assert len(pop_swirl) > 0, "test construction check: must actually produce populated swirl values"
        assert (pop_swirl >= 0.0).all() and (pop_swirl <= 5.0).all()


def test_atten_real_swirl_permanently_nan_for_early_history_level():
    # THE positive, end-to-end regression test the module docstring's
    # "one-directional NaN relationship" paragraph (and family-structure-
    # smc.md §2h, and the register's srd_swirl_ `why` string) all rest on
    # -- Fletcher MAJOR (round 1): nothing in the suite previously
    # exercised this end-to-end (test_swirl_returns_nan_when_both_atr_
    # invalid only forces NaN into a synthetic atr_v array and never calls
    # sr_decay() itself).
    #
    # Swing high at bar 3 (H=110, unique vs flooded H=101), confirms at
    # bar 5 (swing_len=2) -- deliberately BEFORE ATR(14) has any valid
    # history (needs ~14 bars), so this level's SWIRL is computed from
    # `atr_near`/`atr_current` that are both still NaN at confirmation.
    # ATTEN has no ATR dependency and is real regardless.
    n = 40
    H, L, C = _flooded_hlc(n)
    H[3], L[3], C[3] = 110.0, 99.0, 100.0
    out = _run(H, L, C, swing_len=2, max_levels=20)

    atten_res = out["SRD_ATTEN_RES_2"]
    swirl_res = out["SRD_SWIRL_RES_2"]
    assert atten_res.iloc[:5].isna().all()

    price_change_pct = abs(100.0 - 110.0) / 110.0 * 100.0
    time_decay = min(2 / 50.0, 1.0)
    price_decay = min(price_change_pct / 10.0, 1.0)
    expected_atten = min(time_decay * 0.6 + price_decay * 0.4, 1.0)
    assert math.isclose(atten_res.iloc[5], expected_atten, rel_tol=1e-9)
    assert not np.isnan(atten_res.iloc[5]), "ATTEN must be real -- no ATR dependency"
    assert np.isnan(swirl_res.iloc[5]), \
        "SWIRL must be NaN -- ATR(14) has no valid history yet at this early confirming bar"

    # the NaN is frozen at creation (like every other per-level scalar
    # here) and never heals even once ATR(14) has long warmed up by later
    # bars -- ATTEN stays real and constant for the same reason.
    assert atten_res.iloc[5:].eq(atten_res.iloc[5]).all()
    assert swirl_res.iloc[5:].isna().all(), \
        "the NaN SWIRL must never heal, even after ATR(14) warms up at later bars"


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
    out_full = ta.sr_decay(high, low, close)
    t = 120

    rng = np.random.RandomState(99)
    high2, low2, close2 = high.copy(), low.copy(), close.copy()
    n = len(close)
    shock = rng.randn(n - t - 1) * 5
    close2.iloc[t + 1:] = close2.iloc[t + 1:] + shock
    high2.iloc[t + 1:] = np.maximum(high2.iloc[t + 1:], close2.iloc[t + 1:]) + 1.0
    low2.iloc[t + 1:] = np.minimum(low2.iloc[t + 1:], close2.iloc[t + 1:]) - 1.0
    assert (low2 <= close2).all() and (close2 <= high2).all(), "construction check"

    out_mut = ta.sr_decay(high2, low2, close2)
    pd.testing.assert_frame_equal(out_full.iloc[:t + 1], out_mut.iloc[:t + 1])


def test_causal_deletion_no_lookahead():
    open_, high, low, close = _random_walk_ohlc()
    out_full = ta.sr_decay(high, low, close)
    t = 120
    out_trunc = ta.sr_decay(high.iloc[:t + 1], low.iloc[:t + 1], close.iloc[:t + 1])
    pd.testing.assert_frame_equal(out_full.iloc[:t + 1], out_trunc)


# ---------------------------------------------------------------------------
# Reachability
# ---------------------------------------------------------------------------

def test_reachable_via_category_and_accessor():
    assert "sr_decay" in ta.Category["trend"]
    open_, high, low, close = _random_walk_ohlc(n=60)
    df = pd.DataFrame({"open": open_, "high": high, "low": low, "close": close})
    assert callable(getattr(df.ta, "sr_decay"))
    direct = ta.sr_decay(high, low, close)
    via_accessor = df.ta.sr_decay()
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
    dict(swing_len=True),
    dict(max_levels=float("nan")),
    dict(max_levels=float("-inf")),
    dict(max_levels=1.5),
    dict(max_levels=0),
    dict(max_levels=-2),
])
def test_invalid_params_raise_value_error(kwargs):
    high, low, close = _bars()
    with pytest.raises(ValueError):
        ta.sr_decay(high, low, close, **kwargs)


def test_none_params_use_documented_defaults():
    high, low, close = _bars()
    out = ta.sr_decay(high, low, close, swing_len=None, max_levels=None)
    assert list(out.columns) == [
        "SRD_ATTEN_RES_5", "SRD_ATTEN_SUP_5", "SRD_SWIRL_RES_5", "SRD_SWIRL_SUP_5",
    ]


# ---------------------------------------------------------------------------
# Attribution
# ---------------------------------------------------------------------------

def test_docstring_names_source_and_author():
    doc = ta.sr_decay.__doc__
    normalized = " ".join(doc.split())
    assert "https://www.tradingview.com/script/2wGxbRZP/" in normalized
    assert "ATTDEFS" in doc
    assert "S/R Channel Rating Engine" in normalized


def test_docstring_notes_what_was_not_ported():
    doc = ta.sr_decay.__doc__
    # calcHistoricalPower (still deferred), the channel-line drawing, and
    # sr_force.py's own touch-behavior base must all be named explicitly
    # as NOT re-ported here.
    assert "calcHistoricalPower" in doc
    assert "sr_force" in doc
    assert "NOT ported" in doc
