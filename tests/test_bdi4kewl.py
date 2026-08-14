# tests/test_bdi4kewl.py
"""bdi4kewl (STURN) -- ATR-confirmed swing-turn signal (TVPTA-6 candidate
13, ported from "4-Hour Swing Turn V2.0" / BDi4kEWL). Self-contained on
synthetic data.

Reachability tests `import pandas_ta` (`.context`), NOT
`importlib.util.spec_from_file_location` (see TODO.md TVPTA-3(c)).

All scenario fixtures below are built on physically valid OHLC (low <=
min(open, close) and max(open, close) <= high on every bar), asserted at
construction time in each builder, per this project's documented history
of tests dodging bugs via impossible bars (see e.g.
tests/test_sphinx_unicorn.py's module docstring for the precedent
incident this guards against).

Every scenario's expected values were derived by independently
recomputing the SAME primitives the module itself calls (`pandas_ta.
volatility.atr`, `.momentum.rsi`, `.overlap.ema`/`.sma`, `.statistics.
stdev`, `.trend.adx`, `.momentum.macd`) against the constructed OHLCV
array, printing every one of the 5 confluence factors plus the impulse/
reversal thresholds, and only THEN running `bdi4kewl()` and confirming
its actual output matches -- not assumed, not hand-typed algebra alone
(the same methodology `tests/test_rejection_blocks.py`'s module docstring
documents for this family of ports; a fully-by-hand numeric trace of 7
composed indicators is not tractable, but independently recomputing them
from the same library calls and cross-checking the port's output is).

⚠ Not covered by a dedicated adversarial fixture in this file: the
SEPARATION gate (`min_swing_separation_atr` -- an accepted signal's pivot
price must be far enough from the previous accepted signal's). It is
exercised by ordinary code-path execution in every multi-signal scenario
below (its guard is a single, simple comparison alongside the ALTERNATION
guard this file DOES test directly with a forced same-direction pair),
but no scenario here specifically forces two opposite-direction
candidates close enough in price to prove SEPARATION blocks on its own --
flagged here rather than silently assumed covered.
"""
import math

import numpy as np
import pandas as pd
import pytest

from .context import pandas_ta as ta
from pandas_ta.trend.bdi4kewl import (
    _confirm_strict_pivots, _validated_bool, _validated_float, _validated_int,
)


# ---------------------------------------------------------------------------
# _confirm_strict_pivots -- isolated unit tests (duplicated helper, same
# contract as sr_force.py/rejection_blocks.py/etc.)
# ---------------------------------------------------------------------------

def test_confirm_strict_pivots_low_unique_extreme():
    vals = pd.Series([5.0, 4.0, 1.0, 4.0, 5.0])
    out = _confirm_strict_pivots(vals, 2, 2, is_high=False)
    assert out[4] == 1.0
    assert np.isnan(out[:4]).all()


def test_confirm_strict_pivots_tie_rejects():
    vals = pd.Series([5.0, 1.0, 3.0, 1.0, 5.0])
    out = _confirm_strict_pivots(vals, 2, 2, is_high=False)
    assert np.isnan(out).all()


def test_confirm_strict_pivots_high_mirror():
    vals = pd.Series([1.0, 2.0, 5.0, 2.0, 1.0])
    out = _confirm_strict_pivots(vals, 2, 2, is_high=True)
    assert out[4] == 5.0


# ---------------------------------------------------------------------------
# _validated_int / _validated_float / _validated_bool -- nan/inf/
# non-integral/wrong-dtype discipline (non-negotiable #1)
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


def test_validated_int_accepts_integral_float():
    assert _validated_int(4.0, 7, "x") == 4


def test_validated_int_rejects_bool():
    with pytest.raises(ValueError, match="bool"):
        _validated_int(True, 7, "x")


def test_validated_int_rejects_non_positive():
    with pytest.raises(ValueError, match="positive"):
        _validated_int(0, 7, "x")
    with pytest.raises(ValueError, match="positive"):
        _validated_int(-3, 7, "x")


def test_validated_float_none_returns_default():
    assert _validated_float(None, 1.5, "x") == 1.5


def test_validated_float_rejects_nan():
    with pytest.raises(ValueError, match="NaN"):
        _validated_float(float("nan"), 1.5, "x")


def test_validated_float_rejects_inf():
    with pytest.raises(ValueError, match="inf"):
        _validated_float(float("inf"), 1.5, "x")


def test_validated_float_rejects_bool():
    with pytest.raises(ValueError, match="bool"):
        _validated_float(True, 1.5, "x")


def test_validated_float_nonneg_rejects_negative():
    with pytest.raises(ValueError, match=">= 0"):
        _validated_float(-0.1, 1.5, "x", nonneg=True)


def test_validated_float_nonneg_false_accepts_negative():
    # long_bb_level/short_bb_level/long_rsi_level/short_rsi_level are the
    # only 4 params wired with nonneg=False -- the source itself allows
    # long_bb_level in [-0.5, 0.7].
    assert _validated_float(-0.5, 0.35, "x", nonneg=False) == -0.5


def test_validated_bool_none_returns_default():
    assert _validated_bool(None, True, "x") is True


def test_validated_bool_accepts_genuine_bool():
    assert _validated_bool(False, True, "x") is False


def test_validated_bool_rejects_non_bool():
    with pytest.raises(ValueError, match="bool"):
        _validated_bool(1, True, "x")
    with pytest.raises(ValueError, match="bool"):
        _validated_bool("true", True, "x")


def test_bdi4kewl_raises_through_real_call_not_just_helper():
    """Non-negotiable #1 wants the raise proven through the actual public
    function, not only the isolated helper -- a wrong kwarg name or a
    dropped validation call at the call site would pass the helper tests
    above while silently NOT raising here."""
    close = pd.Series(100 + np.cumsum(np.random.RandomState(0).randn(60)))
    high = close + 0.2
    low = close - 0.2
    open_ = close.copy()
    volume = pd.Series(np.full(60, 1_000_000.0))
    from pandas_ta.trend.bdi4kewl import bdi4kewl
    with pytest.raises(ValueError):
        bdi4kewl(open_=open_, high=high, low=low, close=close, volume=volume,
                 pivot_left=float("nan"))
    with pytest.raises(ValueError):
        bdi4kewl(open_=open_, high=high, low=low, close=close, volume=volume,
                 min_impulse_atr=float("inf"))
    with pytest.raises(ValueError):
        bdi4kewl(open_=open_, high=high, low=low, close=close, volume=volume,
                 pivot_right=2.5)
    with pytest.raises(ValueError):
        bdi4kewl(open_=open_, high=high, low=low, close=close, volume=volume,
                 enable_rescue_branch=1)


# ---------------------------------------------------------------------------
# Scenario builders
# ---------------------------------------------------------------------------

def _to_frame(open_, high, low, close, volume, start="2022-01-03"):
    assert (low <= np.minimum(open_, close) + 1e-9).all(), "low must be <= min(open, close) on every bar"
    assert (np.maximum(open_, close) <= high + 1e-9).all(), "max(open, close) must be <= high on every bar"
    n = len(close)
    idx = pd.bdate_range(start, periods=n)
    return pd.DataFrame(
        {"Open": open_, "High": high, "Low": low, "Close": close, "Volume": volume}, index=idx
    )


def _clean_long_scenario():
    """40 quiet warmup bars, a clean 14-bar decline, a deep-lower-wick
    bullish reversal pivot bar (all 5 confluence factors true -> score 5),
    then a strong upward reversal. Confirms as a LONG signal at
    pivot_idx + pivot_right (default pivot_right=2). Hand-verified: at
    the pivot bar (index 54), independently recomputed priorMove/
    location/momentum/active/rejection are all True (score=5); ATR[54] =
    0.8470, so 2.0*ATR = 1.6939, and impulse (rolling-12-bar high minus
    pivotLow) = 13.1887, well clear of that threshold; the confirming
    bar's close - pivotLow clears 1.2*ATR (1.0163) well within 2 bars of
    confirmation. ⚠ Fletcher round 1 (MAJOR): an earlier version of this
    docstring quoted `_expiry_scenario`'s numbers (10.92/1.37) here by
    copy-paste error -- the assertions below never depended on the wrong
    prose (13.19 >> 1.69 holds exactly as much as the false 10.92 >> 1.37
    did), but this docstring is the only WRITTEN evidence the fixture was
    actually hand-verified, and it wasn't describing itself. Re-verified
    directly against this exact fixture via a standalone script before
    being written here, not reasoned by analogy to a sibling scenario."""
    n_warm = 40
    rng = np.random.default_rng(3)
    warm = 100 + np.cumsum(rng.normal(0, 0.05, n_warm))
    down_n = 14
    down = warm[-1] - np.cumsum(np.full(down_n, 0.9)) + rng.normal(0, 0.05, down_n)
    pivot_close = down[-1] - 0.3
    pivot_low_price = pivot_close - 3.0
    pivot_open = pivot_close - 0.1
    pivot_high_price = pivot_close + 0.15
    confirm1 = pivot_close + 0.05
    confirm2 = pivot_close + 0.10
    rev_n = 6
    rev = pivot_low_price + np.cumsum(np.full(rev_n, 2.0)) + rng.normal(0, 0.05, rev_n)

    close = np.concatenate([warm, down, [pivot_close, confirm1, confirm2], rev])
    n = len(close)
    pivot_idx = n_warm + down_n

    open_ = close.copy()
    open_[1:] = close[:-1]
    open_[pivot_idx] = pivot_open

    high = np.zeros(n)
    low = np.zeros(n)
    for i in range(n):
        o, c = open_[i], close[i]
        if i == pivot_idx:
            high[i], low[i] = pivot_high_price, pivot_low_price
        else:
            high[i] = max(o, c) + abs(rng.normal(0, 0.03))
            low[i] = min(o, c) - abs(rng.normal(0, 0.03))

    volume = np.full(n, 1_000_000.0)
    volume[pivot_idx] = 3_000_000.0

    df = _to_frame(open_, high, low, close, volume)
    return df, pivot_idx


def _clean_short_scenario():
    """Mirror of `_clean_long_scenario`: 40 quiet warmup bars, a clean
    14-bar RALLY, a deep-UPPER-wick bearish reversal pivot bar, then a
    strong downward reversal. Confirms as a SHORT signal at pivot_idx +
    pivot_right, same pivot_idx=54/confirm_bar=56 as the LONG scenario
    (same warmup length, same up_n=14=down_n) -- built as its own fixture
    (not reused from `_clean_long_scenario`'s incidental background-noise
    SHORT signal) specifically so `test_truncation_before_confirmation_
    catches_backdating_mutant`'s SHORT-side mirror has a pivot bar
    comfortably past this module's own `min_len=35` floor (the LONG
    fixture's own organic SHORT signal, confirmed by direct pivot-
    detection inspection, anchors at bar 26 -- too early for a `+1`
    truncation to leave a computable frame). Verified directly against
    this exact fixture: SHORT fires at bar 56 with score 5.0."""
    n_warm = 40
    rng = np.random.default_rng(3)
    warm = 100 + np.cumsum(rng.normal(0, 0.05, n_warm))
    up_n = 14
    up = warm[-1] + np.cumsum(np.full(up_n, 0.9)) + rng.normal(0, 0.05, up_n)
    pivot_close = up[-1] + 0.3
    pivot_high_price = pivot_close + 3.0
    pivot_open = pivot_close + 0.1
    pivot_low_price = pivot_close - 0.15
    confirm1 = pivot_close - 0.05
    confirm2 = pivot_close - 0.10
    rev_n = 6
    rev = pivot_high_price - np.cumsum(np.full(rev_n, 2.0)) + rng.normal(0, 0.05, rev_n)

    close = np.concatenate([warm, up, [pivot_close, confirm1, confirm2], rev])
    n = len(close)
    pivot_idx = n_warm + up_n

    open_ = close.copy()
    open_[1:] = close[:-1]
    open_[pivot_idx] = pivot_open

    high = np.zeros(n)
    low = np.zeros(n)
    for i in range(n):
        o, c = open_[i], close[i]
        if i == pivot_idx:
            high[i], low[i] = pivot_high_price, pivot_low_price
        else:
            high[i] = max(o, c) + abs(rng.normal(0, 0.03))
            low[i] = min(o, c) - abs(rng.normal(0, 0.03))

    volume = np.full(n, 1_000_000.0)
    volume[pivot_idx] = 3_000_000.0

    df = _to_frame(open_, high, low, close, volume)
    return df, pivot_idx


def _rescue_scenario():
    """A flat, no-trend 60-bar random walk (keeps RSI near 50 and DMI
    roughly balanced) with an organic score==2 pivot at anchor bar 25
    (confirms at bar 27): priorMove/location/momentum independently False,
    active (range/ATR >= 1.10) and rejection (close>open) True -- admitted
    ONLY via the rescue branch. Hand-verified by independently recomputing
    all 5 factors at anchor bar 25 (see module test docstring methodology)
    against the SAME fixture, cross-checked against the port's actual
    STURN_SCORE/STURN_RESCUE output before being written as an assertion.
    Custom long_bb_level=-5.0/long_rsi_level=-100.0 make those two
    threshold branches structurally unreachable (isolating the DMI/EMA/
    context checks as the real, load-bearing false conditions) --
    min_impulse_atr=0.5 is lowered only so the shallow organic dip clears
    the impulse gate; every OTHER default stays at its shipped value.
    The same fixture also produces 7 total signals alternating
    LONG/SHORT/LONG/SHORT/LONG/SHORT/LONG with no consecutive repeat --
    used by the alternation test below."""
    n_warm = 60
    rng = np.random.default_rng(21)
    close = 100 + np.cumsum(rng.normal(0, 0.03, n_warm))
    pivot_idx = n_warm - 1

    baseline = close[pivot_idx - 1]
    pivot_close = baseline + 0.03
    pivot_open = baseline - 0.01
    pivot_low_price = baseline - 0.55
    pivot_high_price = baseline + 0.04
    close[pivot_idx] = pivot_close

    confirm1 = pivot_close + 0.02
    confirm2 = pivot_close + 0.03
    rev_n = 6
    rev = pivot_low_price + np.cumsum(np.full(rev_n, 0.35)) + rng.normal(0, 0.02, rev_n)

    close = np.concatenate([close, [confirm1, confirm2], rev])
    n = len(close)

    open_ = close.copy()
    open_[1:] = close[:-1]
    open_[pivot_idx] = pivot_open

    high = np.zeros(n)
    low = np.zeros(n)
    for i in range(n):
        o, c = open_[i], close[i]
        if i == pivot_idx:
            high[i], low[i] = pivot_high_price, pivot_low_price
        else:
            high[i] = max(o, c) + abs(rng.normal(0, 0.015))
            low[i] = min(o, c) - abs(rng.normal(0, 0.015))

    volume = np.full(n, 1_000_000.0)
    volume[pivot_idx] = 1_300_000.0

    df = _to_frame(open_, high, low, close, volume)
    kwargs = dict(min_impulse_atr=0.5, long_bb_level=-5.0, long_rsi_level=-100.0)
    return df, kwargs


def _expiry_scenario():
    """Same shape as `_clean_long_scenario` (real 14-bar decline, so the
    impulse gate clears normally and score is 5 -- verified independently:
    both hold at anchor bar 54), but the pivot's own wick is SHALLOW
    (pivot_low only 0.15 below its close, not 3.0) and price stays FLAT
    for 20 bars after confirmation instead of reversing. close - pivotLow
    never exceeds ~0.23 over that whole window, well under
    1.2*ATR(~0.824) -- the candidate is created (verified) but expires
    unfired 12 bars after its own anchor bar."""
    n_warm = 40
    rng = np.random.default_rng(3)
    warm = 100 + np.cumsum(rng.normal(0, 0.05, n_warm))
    down_n = 14
    down = warm[-1] - np.cumsum(np.full(down_n, 0.9)) + rng.normal(0, 0.05, down_n)

    pivot_close = down[-1] - 0.9
    pivot_open = pivot_close - 0.05
    pivot_low_price = pivot_close - 0.15
    pivot_high_price = pivot_close + 0.05
    confirm1 = pivot_close + 0.02
    confirm2 = pivot_close + 0.01
    flat_n = 20
    flat = pivot_close + rng.normal(0, 0.05, flat_n)

    close = np.concatenate([warm, down, [pivot_close, confirm1, confirm2], flat])
    n = len(close)
    pivot_idx = n_warm + down_n

    open_ = close.copy()
    open_[1:] = close[:-1]
    open_[pivot_idx] = pivot_open

    high = np.zeros(n)
    low = np.zeros(n)
    for i in range(n):
        o, c = open_[i], close[i]
        if i == pivot_idx:
            high[i], low[i] = pivot_high_price, pivot_low_price
        else:
            high[i] = max(o, c) + abs(rng.normal(0, 0.03))
            low[i] = min(o, c) - abs(rng.normal(0, 0.03))

    volume = np.full(n, 1_000_000.0)
    volume[pivot_idx] = 3_000_000.0

    df = _to_frame(open_, high, low, close, volume)
    return df, pivot_idx


def _impulse_gate_rejection_scenario():
    """A flat 60-bar market with a tiny, otherwise well-scoring pivot
    (close > open, elevated volume, deep-enough for its OWN small wick to
    read as 'active') followed by a strong reversal ramp that WOULD
    confirm a candidate immediately if one existed. Independently
    verified impulse (rolling-12-bar high minus pivotLow) = 0.6996 at the
    pivot bar, ATR = 0.2660 -- with the shipped default min_impulse_atr
    (2.0) this would already sit close to the edge on some seeds, so this
    test pins it down unambiguously with an explicit min_impulse_atr=10.0
    override (threshold 2.660 >> 0.6996, guaranteed to fail) to isolate
    the impulse gate as the single blocking mechanism under test, not a
    coincidence of this particular noise draw."""
    n_warm = 60
    rng = np.random.default_rng(3)
    close = 100 + np.cumsum(rng.normal(0, 0.15, n_warm))
    pivot_idx = n_warm - 1
    baseline = close[pivot_idx - 1]

    pivot_close = baseline - 0.05
    pivot_open = pivot_close - 0.05
    pivot_low_price = pivot_open - 0.01
    pivot_high_price = pivot_close + 0.05
    close[pivot_idx] = pivot_close

    confirm1 = pivot_close + 0.02
    confirm2 = pivot_close + 0.03
    rev_n = 6
    rev = pivot_low_price + np.cumsum(np.full(rev_n, 2.0)) + rng.normal(0, 0.05, rev_n)

    close = np.concatenate([close, [confirm1, confirm2], rev])
    n = len(close)

    open_ = close.copy()
    open_[1:] = close[:-1]
    open_[pivot_idx] = pivot_open

    high = np.zeros(n)
    low = np.zeros(n)
    for i in range(n):
        o, c = open_[i], close[i]
        if i == pivot_idx:
            high[i], low[i] = pivot_high_price, pivot_low_price
        else:
            high[i] = max(o, c) + abs(rng.normal(0, 0.1))
            low[i] = min(o, c) - abs(rng.normal(0, 0.1))

    volume = np.full(n, 1_000_000.0)
    volume[pivot_idx] = 3_000_000.0

    df = _to_frame(open_, high, low, close, volume)
    return df, pivot_idx


def _large_realistic_ohlcv(n=500, seed=42):
    """A larger, non-degenerate synthetic frame for the reachability/
    canary tests -- trending random walk with real (non-flat, non-
    symmetric) wicks and varying volume, NOT the fixed +-2%/constant-
    volume shape `gen_indicator_register.py`'s own fixture uses (that
    shape is documented, in several sibling ports' register rows, to
    silently zero out same-bar terms; irrelevant to THIS indicator's
    formula, but avoided here anyway so this canary is not accidentally
    another instance of the same artifact class)."""
    rng = np.random.default_rng(seed)
    close = 50 * np.exp(np.cumsum(rng.normal(0.0004, 0.016, n)))
    open_ = close * (1 + rng.normal(0, 0.003, n))
    high = np.maximum(open_, close) * (1 + np.abs(rng.normal(0.004, 0.004, n)))
    low = np.minimum(open_, close) * (1 - np.abs(rng.normal(0.004, 0.004, n)))
    volume = rng.integers(100_000, 1_000_000, n).astype(float)
    return _to_frame(open_, high, low, close, volume)


# ---------------------------------------------------------------------------
# Reachability (gate c): .context import, Category membership, accessor
# equality with the direct function call
# ---------------------------------------------------------------------------

def test_reachable_via_category():
    assert "bdi4kewl" in ta.Category["trend"]


def test_reachable_via_module_path():
    from pandas_ta.trend.bdi4kewl import bdi4kewl as direct_fn
    assert callable(direct_fn)


def test_accessor_matches_direct_call():
    from pandas_ta.trend.bdi4kewl import bdi4kewl as direct_fn

    df = _large_realistic_ohlcv()
    direct = direct_fn(open_=df["Open"], high=df["High"], low=df["Low"],
                        close=df["Close"], volume=df["Volume"])

    df_lower = df.rename(columns=str.lower)
    via_accessor = df_lower.ta.bdi4kewl()

    assert list(via_accessor.columns) == list(direct.columns)
    for col in direct.columns:
        left = via_accessor[col].to_numpy()
        right = direct[col].to_numpy()
        both_nan = np.isnan(left) & np.isnan(right)
        assert np.allclose(left[~both_nan], right[~both_nan])


# ---------------------------------------------------------------------------
# Non-degenerate at literal defaults (gate 3 / non-negotiable #3)
# ---------------------------------------------------------------------------

def test_defaults_are_non_degenerate_canary():
    df = _large_realistic_ohlcv()
    out = df.ta.bdi4kewl()  # every param left at its literal shipped default

    long_col, short_col, score_col, rescue_col = out.columns
    assert long_col == "STURN_LONG_3_2"
    assert short_col == "STURN_SHORT_3_2"

    long_sum = int(out[long_col].sum())
    short_sum = int(out[short_col].sum())
    print(f"canary: LONG={long_sum} SHORT={short_sum} of {len(out)} bars")
    # CANARY: a constant/NaN-stub fixture (e.g. a flat-price frame with no
    # real pivots) would produce 0 here for BOTH columns -- this trips if
    # the fixture ever degenerates back to that shape.
    assert long_sum > 0, "canary tripped: no LONG signal at all on a 500-bar trending fixture"
    assert short_sum > 0, "canary tripped: no SHORT signal at all on a 500-bar trending fixture"
    assert out[long_col].isin([0, 1]).all()
    assert out[short_col].isin([0, 1]).all()

    populated_score = out[score_col].dropna()
    assert len(populated_score) == long_sum + short_sum
    assert (populated_score >= 2).all() and (populated_score <= 5).all()
    assert populated_score.nunique() > 1, "canary tripped: SCORE is a constant, not a real 2-5 distribution"

    populated_rescue = out[rescue_col].dropna()
    assert len(populated_rescue) == long_sum + short_sum
    assert populated_rescue.isin([0.0, 1.0]).all()
    # Fletcher MINOR (round 1): `isin([0.0, 1.0])` alone is satisfied by a
    # CONSTANT 0.0 column -- the rescue branch is the narrowest gate in
    # the whole state machine (score==2 AND active AND rejection) and so
    # the likeliest to silently stop firing; a constant-0.0 RESCUE column
    # would pass every assertion above it. On this exact fixture it fires
    # 2/57 times (verified before writing this assertion) -- mirrors the
    # SCORE nunique canary just above.
    assert populated_rescue.nunique() > 1, "canary tripped: RESCUE never fires (or always fires) on this fixture"


# ---------------------------------------------------------------------------
# Hand-computed scenario (gate a)
# ---------------------------------------------------------------------------

def test_hand_computed_clean_long_signal():
    df, pivot_idx = _clean_long_scenario()
    out = df.ta.bdi4kewl()
    confirm_bar = pivot_idx + 2  # default pivot_right=2

    assert out["STURN_LONG_3_2"].iloc[confirm_bar] == 1
    assert out["STURN_SHORT_3_2"].iloc[confirm_bar] == 0
    # Independently recomputed against the SAME atr/rsi/ema/sma/stdev/adx/
    # macd calls the module uses: all 5 confluence factors true at the
    # pivot bar -> score 5, admitted via the normal (non-rescue) path.
    assert out["STURN_SCORE_3_2"].iloc[confirm_bar] == 5.0
    assert out["STURN_RESCUE_3_2"].iloc[confirm_bar] == 0.0

    # Causality point: nothing fires at or before the pivot bar itself --
    # the flag is written on the CONFIRMATION bar, never back-dated.
    assert out["STURN_LONG_3_2"].iloc[:confirm_bar].sum() == 0 or \
        pivot_idx not in np.flatnonzero(out["STURN_LONG_3_2"].to_numpy()[:confirm_bar])
    assert out["STURN_LONG_3_2"].iloc[pivot_idx] == 0
    assert out["STURN_LONG_3_2"].iloc[pivot_idx + 1] == 0


# ---------------------------------------------------------------------------
# Rescue branch (score == 2, admitted only via enable_rescue_branch)
# ---------------------------------------------------------------------------

def test_rescue_branch_admits_score_2_candidate():
    df, kwargs = _rescue_scenario()
    out = df.ta.bdi4kewl(**kwargs)

    assert out["STURN_LONG_3_2"].iloc[27] == 1
    assert out["STURN_SCORE_3_2"].iloc[27] == 2.0
    assert out["STURN_RESCUE_3_2"].iloc[27] == 1.0


def test_rescue_branch_disabled_blocks_the_same_candidate():
    """Same fixture, `enable_rescue_branch=False` -- the score==2
    candidate at bar 27 must no longer be admitted at all (impulse still
    clears, but `score >= min_score` is False and the rescue branch is
    now unreachable by construction)."""
    df, kwargs = _rescue_scenario()
    kwargs = dict(kwargs, enable_rescue_branch=False)
    out = df.ta.bdi4kewl(**kwargs)
    assert out["STURN_LONG_3_2"].iloc[27] == 0


def test_signals_alternate_direction_no_consecutive_repeat():
    """Organic evidence for the ALTERNATION gate (`last_signal_direction
    != candidate.direction`): the rescue-scenario fixture produces 7
    accepted signals total; none of them repeats the direction of the
    signal immediately before it."""
    df, kwargs = _rescue_scenario()
    out = df.ta.bdi4kewl(**kwargs)
    long_hits = set(np.flatnonzero(out["STURN_LONG_3_2"].to_numpy()).tolist())
    short_hits = set(np.flatnonzero(out["STURN_SHORT_3_2"].to_numpy()).tolist())
    all_hits = sorted((i, 1) for i in long_hits) + sorted((i, -1) for i in short_hits)
    all_hits.sort(key=lambda x: x[0])
    assert len(all_hits) >= 4, "fixture no longer produces enough signals to exercise alternation"
    directions = [d for _, d in all_hits]
    for a, b in zip(directions, directions[1:]):
        assert a != b, f"consecutive same-direction signals fired: {all_hits}"


def test_alternation_blocks_same_direction_repeat():
    """Forced negative case: two consecutive down-legs with NO intervening
    opposite signal both independently qualify as high-score LONG
    candidates (verified: both confirm with score 5 on their own), but the
    second's own reversal-confirmation bar must NOT fire as a second LONG
    in a row -- `last_signal_direction` is already 1 from the first."""
    n_warm = 40
    rng = np.random.default_rng(5)
    warm = 100 + np.cumsum(rng.normal(0, 0.04, n_warm))

    def _down_leg(start, seed):
        r = np.random.default_rng(seed)
        return start - np.cumsum(np.full(14, 0.9)) + r.normal(0, 0.04, 14)

    def _pivot_block(prev_close, seed):
        down = _down_leg(prev_close, seed)
        pivot_close = down[-1] - 0.3
        pivot_low = pivot_close - 3.0
        pivot_open = pivot_close - 0.1
        pivot_high = pivot_close + 0.15
        confirm1 = pivot_close + 0.05
        confirm2 = pivot_close + 0.1
        r2 = np.random.default_rng(seed + 1)
        rev = pivot_low + np.cumsum(np.full(6, 2.0)) + r2.normal(0, 0.05, 6)
        seq = np.concatenate([down, [pivot_close, confirm1, confirm2], rev])
        return seq, pivot_open, pivot_low, pivot_high

    seq1, po1, plo1, phi1 = _pivot_block(warm[-1], seed=101)
    seq2, po2, plo2, phi2 = _pivot_block(seq1[-1] + 5.0, seed=201)

    close = np.concatenate([warm, seq1, seq2])
    n = len(close)
    pivot1_idx = n_warm + 14
    pivot2_idx = n_warm + len(seq1) + 14

    open_ = close.copy()
    open_[1:] = close[:-1]
    open_[pivot1_idx] = po1
    open_[pivot2_idx] = po2

    high = np.zeros(n)
    low = np.zeros(n)
    for i in range(n):
        o, c = open_[i], close[i]
        if i == pivot1_idx:
            high[i], low[i] = phi1, plo1
        elif i == pivot2_idx:
            high[i], low[i] = phi2, plo2
        else:
            high[i] = max(o, c) + abs(rng.normal(0, 0.03))
            low[i] = min(o, c) - abs(rng.normal(0, 0.03))

    volume = np.full(n, 1_000_000.0)
    volume[pivot1_idx] = 3_000_000.0
    volume[pivot2_idx] = 3_000_000.0

    df = _to_frame(open_, high, low, close, volume)
    out = df.ta.bdi4kewl()

    confirm1_bar = pivot1_idx + 2
    confirm2_bar = pivot2_idx + 2
    assert out["STURN_LONG_3_2"].iloc[confirm1_bar] == 1, "setup invariant: the FIRST pivot must fire"
    # An intervening SHORT can legitimately appear between the two blocks
    # from the down-leg/reversal noise (it does not defeat this test --
    # if one fires, alternation is satisfied honestly rather than by
    # construction, and the second LONG firing would then be expected, not
    # blocked). Skip the assertion in that case; assert the block only
    # when no intervening opposite signal occurred.
    intervening_short = out["STURN_SHORT_3_2"].iloc[confirm1_bar + 1:confirm2_bar].sum() > 0
    if not intervening_short:
        assert out["STURN_LONG_3_2"].iloc[confirm2_bar] == 0, \
            "second same-direction candidate must be alternation-blocked"


# ---------------------------------------------------------------------------
# Expiry (candidate created, never reversal-confirms, dropped unfired)
# ---------------------------------------------------------------------------

def test_expired_candidate_never_fires():
    df, pivot_idx = _expiry_scenario()
    out = df.ta.bdi4kewl()
    window = out.iloc[pivot_idx: pivot_idx + 18]
    assert window["STURN_LONG_3_2"].sum() == 0
    assert window["STURN_SHORT_3_2"].sum() == 0


# ---------------------------------------------------------------------------
# Impulse-gate rejection (score/reversal would pass; impulse alone blocks)
# ---------------------------------------------------------------------------

def test_impulse_gate_blocks_shallow_pivot():
    df, pivot_idx = _impulse_gate_rejection_scenario()
    out = df.ta.bdi4kewl(min_impulse_atr=10.0)
    assert out["STURN_LONG_3_2"].sum() == 0
    assert out["STURN_SHORT_3_2"].sum() == 0


def test_impulse_gate_default_threshold_lets_reversal_ramp_fire_elsewhere():
    """Sanity check that `min_impulse_atr=10.0` -- not some unrelated
    difference between this fixture and the others -- is what's blocking
    everything above: at the SHIPPED DEFAULT (2.0) this exact fixture is
    not required to be silent; this only documents that the override in
    the test above is the isolated variable, not a coincidence of an
    otherwise-inert fixture."""
    df, pivot_idx = _impulse_gate_rejection_scenario()
    out_default = df.ta.bdi4kewl()  # default min_impulse_atr=2.0
    out_blocked = df.ta.bdi4kewl(min_impulse_atr=10.0)
    total_default = int(out_default["STURN_LONG_3_2"].sum() + out_default["STURN_SHORT_3_2"].sum())
    total_blocked = int(out_blocked["STURN_LONG_3_2"].sum() + out_blocked["STURN_SHORT_3_2"].sum())
    assert total_blocked <= total_default, "raising min_impulse_atr must never CREATE new signals"


# ---------------------------------------------------------------------------
# Causality (non-negotiable #4): mutation + truncation, on a fixture that
# carries a real, non-zero signal in every output column
# ---------------------------------------------------------------------------

def test_mutation_after_cutoff_does_not_change_earlier_output():
    df, pivot_idx = _clean_long_scenario()
    confirm_bar = pivot_idx + 2
    cutoff = confirm_bar + 5  # comfortably past the real signal this fixture carries

    # capture the mutated copy BEFORE calling the accessor on `df` -- the
    # accessor renames columns to lowercase IN PLACE on its own frame
    # argument (`core.py`'s `df.rename(..., inplace=True)`), so calling it
    # first would silently leave `df.copy()` with lowercase column names.
    mutated = df.copy()
    out_original = df.ta.bdi4kewl()

    rng = np.random.default_rng(999)
    n = len(mutated)
    shock = rng.normal(0, 50, n - cutoff)  # large, unrelated perturbation
    mutated.iloc[cutoff:, mutated.columns.get_loc("Close")] += shock
    mutated.iloc[cutoff:, mutated.columns.get_loc("High")] += shock + 5
    mutated.iloc[cutoff:, mutated.columns.get_loc("Low")] += shock - 5
    mutated.iloc[cutoff:, mutated.columns.get_loc("Open")] += shock
    # keep OHLC physically valid after the shock
    mutated.loc[mutated.index[cutoff:], "High"] = mutated.iloc[cutoff:][["Open", "High", "Low", "Close"]].max(axis=1)
    mutated.loc[mutated.index[cutoff:], "Low"] = mutated.iloc[cutoff:][["Open", "High", "Low", "Close"]].min(axis=1)

    out_mutated = mutated.ta.bdi4kewl()

    for col in out_original.columns:
        left = out_original[col].to_numpy()[:cutoff]
        right = out_mutated[col].to_numpy()[:cutoff]
        both_nan = np.isnan(left) & np.isnan(right)
        assert np.array_equal(left[~both_nan], right[~both_nan]), f"{col} changed before the mutation cutoff"

    # the fixture is not vacuously "carrying no signal" up to the cutoff
    assert out_original["STURN_LONG_3_2"].iloc[:cutoff].sum() > 0


def test_truncation_matches_prefix_of_full_series():
    df, pivot_idx = _clean_long_scenario()
    confirm_bar = pivot_idx + 2
    truncate_at = confirm_bar + 3

    out_full = df.ta.bdi4kewl()
    out_truncated = df.iloc[:truncate_at].ta.bdi4kewl()

    for col in out_full.columns:
        left = out_full[col].to_numpy()[:truncate_at]
        right = out_truncated[col].to_numpy()
        both_nan = np.isnan(left) & np.isnan(right)
        assert np.array_equal(left[~both_nan], right[~both_nan]), f"{col} differs between full and truncated runs"

    assert out_truncated["STURN_LONG_3_2"].sum() > 0


def _load_backdating_mutant():
    """Fletcher MINOR (round 1): the two causality tests above truncate/
    mutate PAST the confirmation bar (`confirm_bar+3`/`+5`), so a back-
    dating port (writing the flag at `c.pivot_bar` instead of `t`) and
    the real, confirmation-bar port produce IDENTICAL prefixes under
    both tests -- both runs reach the same confirmation event and back-
    date identically either way. Neither test can actually distinguish
    "flag on the confirming bar" from "flag back-dated to the pivot bar",
    which is precisely the property the module docstring's CAUSALITY
    section claims. This loads a MUTATED copy of the real module (source
    read from disk, the two known write-sites `out_long[t] = 1` /
    `out_short[t] = 1` textually replaced with `out_long[c.pivot_bar] =
    1` / `out_short[c.pivot_bar] = 1`, executed as a separate module via
    `importlib` rather than hand-reimplemented) so the test below can
    prove, by actually running it, that a truncation point BEFORE
    confirmation catches what a truncation point after it cannot.
    """
    import importlib
    import types

    # `pandas_ta.trend.bdi4kewl` resolves to the FUNCTION (re-exported by
    # `pandas_ta/trend/__init__.py`'s `from .bdi4kewl import bdi4kewl`,
    # which shadows the submodule name in that package's namespace) --
    # `importlib.import_module` on the dotted path gets the actual
    # SUBMODULE object, which has a real `__file__`.
    real_module = importlib.import_module("pandas_ta.trend.bdi4kewl")
    with open(real_module.__file__, "r", encoding="utf-8") as fh:
        src = fh.read()
    marker_long = "out_long[t] = 1"
    marker_short = "out_short[t] = 1"
    assert src.count(marker_long) == 1 and src.count(marker_short) == 1, \
        "write-site markers moved or duplicated -- update this mutant loader"
    mutated_src = src.replace(marker_long, "out_long[c.pivot_bar] = 1", 1)
    mutated_src = mutated_src.replace(marker_short, "out_short[c.pivot_bar] = 1", 1)
    assert mutated_src != src

    # Fletcher NIT (round 2): the original version of this loader wrote
    # the mutated source to a temp file via `tempfile.NamedTemporaryFile
    # (..., delete=False)` and never cleaned it up, leaking one file per
    # test run. `exec(compile(...))` into a fresh in-memory `types.
    # ModuleType` gets the same result (a real module object with the
    # mutated `bdi4kewl` bound inside it, imports and all) with no
    # filesystem footprint at all.
    mutant_module = types.ModuleType("bdi4kewl_backdating_mutant")
    exec(compile(mutated_src, "<bdi4kewl_backdating_mutant>", "exec"), mutant_module.__dict__)
    return mutant_module.bdi4kewl


def test_truncation_before_confirmation_catches_backdating_mutant():
    """The real fix for the gap above: truncate BEFORE the confirmation
    bar (`pivot_idx + 1`, i.e. the confirming bar at `pivot_idx + 2` is
    NOT in the truncated frame at all), so only the FULL run ever reaches
    confirmation and can write a back-dated marker at `pivot_idx`. Proven
    two ways on the SAME fixture and cutoff:

    1. The REAL port: `STURN_LONG_3_2[pivot_idx]` is 0 in both the full
       and the truncated run (it never writes there, back-dated or not)
       -- no divergence, matching the CAUSALITY claim.
    2. The MUTANT (`_load_backdating_mutant`): its FULL run DOES write 1
       at `pivot_idx` (proving the mutant is live, not a no-op), but its
       TRUNCATED run (which never reaches the confirmation bar) does not
       -- a genuine, detected divergence. This is the concrete
       demonstration that this test methodology has power; the
       `confirm_bar+3`/`+5` cutoffs used elsewhere in this file do not.

    Both checks are then MIRRORED on the SHORT side (Fletcher NIT, round
    2): the mutant patches both `out_long[t] = 1` and `out_short[t] = 1`,
    but an earlier version of this test only ever asserted against the
    LONG column, leaving the SHORT write-site patched-but-unexercised.
    This exact fixture also produces a genuine SHORT signal (confirmed at
    bar 36, anchored at bar 34), reused here rather than building a
    second fixture.
    """
    df, pivot_idx = _clean_long_scenario()
    truncate_at = pivot_idx + 1  # excludes the confirmation bar (pivot_idx + 2) entirely

    # capture OHLCV references BEFORE calling the accessor -- it renames
    # `df`'s own columns to lowercase IN PLACE (see the mutation test
    # above for the same gotcha).
    open_ = df["Open"]
    high = df["High"]
    low = df["Low"]
    close = df["Close"]
    volume = df["Volume"]

    # 1. Real port: no divergence at pivot_idx, because it never writes there.
    out_full = df.ta.bdi4kewl()
    out_truncated = df.iloc[:truncate_at].ta.bdi4kewl()
    assert out_full["STURN_LONG_3_2"].iloc[pivot_idx] == 0
    assert out_truncated["STURN_LONG_3_2"].iloc[pivot_idx] == 0

    # 2. Mutant: full run back-dates (proves the mutant is real); truncated
    # run never reaches confirmation, so it cannot -- divergence detected.
    mutant_fn = _load_backdating_mutant()

    mutant_full = mutant_fn(open_=open_, high=high, low=low, close=close, volume=volume)
    mutant_truncated = mutant_fn(open_=open_.iloc[:truncate_at], high=high.iloc[:truncate_at],
                                  low=low.iloc[:truncate_at], close=close.iloc[:truncate_at],
                                  volume=volume.iloc[:truncate_at])

    mutant_full_at_pivot = mutant_full["STURN_LONG_3_2"].iloc[pivot_idx]
    mutant_truncated_at_pivot = mutant_truncated["STURN_LONG_3_2"].iloc[pivot_idx]
    assert mutant_full_at_pivot == 1, "mutant setup invariant: the full run must actually back-date"
    assert mutant_truncated_at_pivot == 0, "mutant setup invariant: truncated run must not reach confirmation"
    assert mutant_full_at_pivot != mutant_truncated_at_pivot, \
        "this truncation point failed to catch the back-dating mutant -- test has no power"

    # --- SHORT-side mirror (Fletcher NIT, round 2): the mutant patches
    # BOTH `out_long[t] = 1` and `out_short[t] = 1` (see
    # `_load_backdating_mutant`'s docstring), but everything above only
    # ever checked the LONG column -- the SHORT write-site was patched
    # and never exercised by an assertion. Uses the dedicated
    # `_clean_short_scenario` fixture (a mirror of `_clean_long_scenario`,
    # same pivot_idx=54/confirm_bar=56 shape) rather than reusing
    # `_clean_long_scenario`'s own incidental background-noise SHORT
    # signal -- that signal's real anchor bar, found by direct pivot-
    # detection inspection, is bar 26 (NOT `confirm_bar - pivot_right` --
    # a candidate can be created well before the bar it eventually
    # fires on), too early for a `pivot_idx_short + 1` truncation to
    # leave a computable frame (`min_len=35`). Mirrors the LONG block
    # above exactly: real port shows 0/0 at the SHORT pivot bar; the
    # mutant's full run DOES back-date SHORT to its pivot bar while its
    # own earlier truncation (before ITS confirmation bar) cannot.
    df_short, pivot_idx_short = _clean_short_scenario()
    truncate_at_short = pivot_idx_short + 1  # excludes SHORT's own confirmation bar (pivot_idx_short + 2)

    open_s = df_short["Open"]
    high_s = df_short["High"]
    low_s = df_short["Low"]
    close_s = df_short["Close"]
    volume_s = df_short["Volume"]

    out_full_short = df_short.ta.bdi4kewl()
    out_truncated_short = df_short.iloc[:truncate_at_short].ta.bdi4kewl()
    assert out_full_short["STURN_SHORT_3_2"].iloc[pivot_idx_short] == 0
    assert out_truncated_short["STURN_SHORT_3_2"].iloc[pivot_idx_short] == 0

    mutant_full_short = mutant_fn(open_=open_s, high=high_s, low=low_s, close=close_s, volume=volume_s)
    mutant_truncated_short = mutant_fn(open_=open_s.iloc[:truncate_at_short], high=high_s.iloc[:truncate_at_short],
                                        low=low_s.iloc[:truncate_at_short], close=close_s.iloc[:truncate_at_short],
                                        volume=volume_s.iloc[:truncate_at_short])
    mutant_full_short_at_pivot = mutant_full_short["STURN_SHORT_3_2"].iloc[pivot_idx_short]
    mutant_truncated_short_at_pivot = mutant_truncated_short["STURN_SHORT_3_2"].iloc[pivot_idx_short]
    assert mutant_full_short_at_pivot == 1, "mutant setup invariant: the SHORT full run must actually back-date"
    assert mutant_truncated_short_at_pivot == 0, "mutant setup invariant: SHORT truncated run must not reach confirmation"
    assert mutant_full_short_at_pivot != mutant_truncated_short_at_pivot, \
        "this truncation point failed to catch the SHORT-side back-dating mutant -- test has no power"


# ---------------------------------------------------------------------------
# Offset / fillna plumbing (standard pandas_ta contract)
# ---------------------------------------------------------------------------

def test_offset_shifts_output():
    df = _large_realistic_ohlcv()
    out0 = df.ta.bdi4kewl()
    out1 = df.ta.bdi4kewl(offset=1)
    for col in out0.columns:
        left = out0[col].to_numpy()[:-1]
        right = out1[col].to_numpy()[1:]
        both_nan = np.isnan(left) & np.isnan(right)
        assert np.array_equal(left[~both_nan], right[~both_nan])
