# -*- coding: utf-8 -*-
"""Tests for `atr_push` (APUSH), TVPTA-6 candidate 18.

Ported from the TradingView Pine v6 source "Buy and Sell Zones"
(`LStt7FmQ-Buy-and-Sell-Zones.pine`, `wc -l` = 1513, no trailing newline
so 1514 content lines). Only the push detector (Pine L336-386) is ported;
the zone lifecycle is declined -- see the module docstring.

Three kinds of test live here:

* HAND-DERIVED unit tests on a flat-range fixture where ATR is exactly
  2.0 by construction, so the breakout leg, the impulse leg and the
  threshold comparison can each be worked out from the .pine text first
  and then checked against the port.
* TWO CAUSALITY MUTANTS, each an `importlib` + `exec` copy of the REAL
  module source with exactly one expression rewritten -- never a hand
  reimplementation. Mutant A drops the `.shift(1)` from the breakout
  reference (the `high[1]` offset). Mutant B forward-shifts the push
  window so it reads a FUTURE bar; B exists to prove the fixture has the
  POWER to detect a leak at all, which mutant A on its own does not
  establish.
* An ATR-PROVENANCE test pinning the one measured numerical deviation
  from Pine: this fork's `pandas_ta.atr` smooths with
  `ewm(alpha=1/length, adjust=True)`, while Pine's `ta.atr` is the
  recursive Wilder form (`adjust=False`). They converge; the test pins
  the convergence rather than pretending they are identical.

Every synthetic bar below is physically valid OHLC (low <= open <= high
and low <= close <= high), asserted at construction time.
"""
import importlib
import sys
import types

import numpy as np
import pandas as pd
import pytest

from .context import pandas_ta as ta
from pandas_ta.trend.atr_push import atr_push


# ---------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------
def _frame(rows):
    """rows = [(open, high, low, close), ...]; validates OHLC physically."""
    o, h, l, c = zip(*rows)
    for i, (oo, hh, ll, cc) in enumerate(rows):
        assert ll <= oo <= hh, f"bar {i}: open {oo} outside [{ll}, {hh}]"
        assert ll <= cc <= hh, f"bar {i}: close {cc} outside [{ll}, {hh}]"
        assert ll <= hh, f"bar {i}: low {ll} > high {hh}"
    return pd.DataFrame({"open": list(o), "high": list(h),
                         "low": list(l), "close": list(c)})


def _flat_then_push():
    """Ten identical bars (open=close=100, high=101, low=99) then one
    bullish push bar.

    On the flat bars True Range is exactly 2.0 every bar (h-l = 2,
    |h-prev_close| = 1, |l-prev_close| = 1), so RMA of a constant is that
    constant and ATR == 2.0 exactly -- independent of the smoothing
    convention, which is what makes this fixture hand-derivable.
    """
    rows = [(100.0, 101.0, 99.0, 100.0)] * 10
    rows.append((100.0, 104.5, 99.5, 104.0))
    return _frame(rows)


_PARAMS = dict(atr_length=2, breakout_lookback=2, push_window=2,
               min_push_atr=1.0, max_push_candles=1)


# ---------------------------------------------------------------------
# shape / registration
# ---------------------------------------------------------------------
def test_column_names_and_category():
    df = _flat_then_push()
    r = atr_push(df.open, df.high, df.low, df.close, **_PARAMS)
    assert list(r.columns) == ["APUSH_BULL_2_2_2", "APUSH_BEAR_2_2_2"]
    assert r.name == "APUSH_2_2_2"
    assert r.category == "trend"


def test_default_props_suffix():
    df = _frame([(100.0, 101.0, 99.0, 100.0)] * 40)
    r = atr_push(df.open, df.high, df.low, df.close)
    assert list(r.columns) == ["APUSH_BULL_14_5_5", "APUSH_BEAR_14_5_5"]


def test_dataframe_accessor_matches_direct_call():
    df = _flat_then_push()
    direct = atr_push(df.open, df.high, df.low, df.close, **_PARAMS)
    via = df.ta.atr_push(**_PARAMS)
    pd.testing.assert_frame_equal(direct, via)


def test_registered_in_category_dict():
    assert "atr_push" in ta.Category["trend"]


# ---------------------------------------------------------------------
# hand-derived correctness (Pine L336-386)
# ---------------------------------------------------------------------
def test_hand_derived_atr_is_exactly_two_on_flat_bars():
    """Pre-condition of every hand-derived number below."""
    from pandas_ta.volatility.atr import atr as _atr
    df = _flat_then_push()
    a = _atr(df.high, df.low, df.close, length=2)
    assert a.iloc[2:10].eq(2.0).all()


def test_hand_derived_bull_push_bar():
    """Bar 10, worked out from the .pine text:

      previousStructureHigh = ta.highest(high[1], 2) = max(101, 101) = 101
      close 104 > 101                                 -> bullishBreakout
      close 104 > open 100                            -> bullishCandle
      recentPushLow = ta.lowest(low, 2) = min(99, 99.5) = 99
      leg = close - recentPushLow = 104 - 99 = 5
      TR   = max(104.5-99.5, |104.5-100|, |99.5-100|) = 5
      atr  = smoothed(prev 2.0, 5.0), length 2        -> 3.5014657...
      5 >= 3.5014657 * 1.0                            -> sufficientPush
      enoughHistory: bar_index 10 > max(2+1, 1+2) = 3 -> true
    """
    df = _flat_then_push()
    r = atr_push(df.open, df.high, df.low, df.close, **_PARAMS)
    assert r["APUSH_BULL_2_2_2"].iloc[10] == 1.0
    assert r["APUSH_BEAR_2_2_2"].iloc[10] == 0.0
    # And the margin is real, not marginal: leg/atr = 5 / 3.5014657 =
    # 1.42797..., comfortably clear of the 1.0 threshold. Pinned directly
    # rather than via a shipped column (the strength columns were built,
    # measured at rho 0.859 against `dist_low_5`, and removed).
    from pandas_ta.volatility.atr import atr as _atr
    a10 = _atr(df.high, df.low, df.close, length=2).iloc[10]
    assert 5.0 / a10 == pytest.approx(1.4279725, abs=1e-6)
    assert 0.5 / a10 == pytest.approx(0.1427973, abs=1e-6)


def test_flat_bars_never_fire():
    """A doji (close == open) fails `bullishCandle`/`bearishCandle`, and
    a flat close cannot exceed prior structure either."""
    df = _flat_then_push()
    r = atr_push(df.open, df.high, df.low, df.close, **_PARAMS)
    assert r["APUSH_BULL_2_2_2"].iloc[2:10].eq(0.0).all()
    assert r["APUSH_BEAR_2_2_2"].iloc[2:10].eq(0.0).all()


def test_threshold_is_load_bearing():
    """The very same bar stops firing once `min_push_atr` is raised past
    the measured leg (5 / 3.5014657 = 1.42797...), and still fires just
    below it. Proves the ATR leg is a real gate, not decoration."""
    df = _flat_then_push()
    hi = atr_push(df.open, df.high, df.low, df.close,
                  **{**_PARAMS, "min_push_atr": 1.5})
    lo = atr_push(df.open, df.high, df.low, df.close,
                  **{**_PARAMS, "min_push_atr": 1.4})
    assert hi["APUSH_BULL_2_2_2"].iloc[10] == 0.0
    assert lo["APUSH_BULL_2_2_2"].iloc[10] == 1.0


def test_breakout_is_load_bearing():
    """Widening `breakout_lookback` to reach back over a taller prior bar
    kills the same push. Prior structure, not just the impulse, gates it."""
    rows = [(100.0, 101.0, 99.0, 100.0)] * 4
    rows.append((100.0, 110.0, 99.0, 100.0))          # a tall spike bar
    rows += [(100.0, 101.0, 99.0, 100.0)] * 5
    rows.append((100.0, 104.5, 99.5, 104.0))          # the push, bar 10
    df = _frame(rows)
    near = atr_push(df.open, df.high, df.low, df.close, **_PARAMS)
    far = atr_push(df.open, df.high, df.low, df.close,
                   **{**_PARAMS, "breakout_lookback": 8})
    assert near["APUSH_BULL_2_2_2"].iloc[10] == 1.0    # window = bars 8,9
    assert far["APUSH_BULL_2_8_2"].iloc[10] == 0.0     # window reaches bar 4


def test_flag_implies_leg_at_or_above_threshold():
    """Structural invariant: on every bar the flag fires, the impulse leg
    really is >= min_push_atr x ATR. The leg is recomputed here from the
    frame (the shipped columns no longer expose it), so this is a genuine
    cross-check of the gate, not a tautology over one column."""
    from pandas_ta.volatility.atr import atr as _atr
    rng = np.random.default_rng(11)
    n = 800
    c = 100 * np.exp(np.cumsum(rng.normal(0, 0.01, n)))
    h = c * (1 + np.abs(rng.normal(0, 0.008, n)))
    l = c * (1 - np.abs(rng.normal(0, 0.008, n)))
    o = np.clip(c * (1 + rng.normal(0, 0.004, n)), l, h)
    df = _frame(list(zip(o, h, l, c)))
    for mult in (0.5, 1.0, 2.0):
        r = atr_push(df.open, df.high, df.low, df.close, min_push_atr=mult)
        fired = r["APUSH_BULL_14_5_5"] == 1.0
        assert fired.sum() > 0, f"no bull flags at min_push_atr={mult}"
        leg = df.close - df.low.rolling(5).min()
        thresh = _atr(df.high, df.low, df.close, length=14) * mult
        assert (leg[fired] >= thresh[fired] - 1e-12).all()
        # and the gate really binds: some bars fail it
        assert (~fired & (leg < thresh)).sum() > 0


def test_enough_history_gate_boundary():
    """`bar_index > math.max(breakoutLookback + 1, maximumPushCandles + 2)`.

    The gate is moved across ONE fixed push bar (index 4) by varying
    `max_push_candles`, rather than moving the bar -- moving the bar
    would also move the breakout window and confound the two.

    breakout_lookback = 2 throughout, so `breakoutLookback + 1` = 3.
      max_push_candles=1 -> bound = max(3, 3) = 3, and 4 > 3  -> fires
      max_push_candles=2 -> bound = max(3, 4) = 4, and 4 > 4  -> suppressed
    That second case pins the comparison as strict `>`, not `>=`.
    """
    base = (100.0, 101.0, 99.0, 100.0)
    push = (100.0, 104.5, 99.5, 104.0)
    df = _frame([base] * 4 + [push] + [base] * 4)
    fires = atr_push(df.open, df.high, df.low, df.close, **_PARAMS)
    assert fires["APUSH_BULL_2_2_2"].iloc[4] == 1.0
    for mpc, bound in ((2, 4), (3, 5)):
        r = atr_push(df.open, df.high, df.low, df.close,
                     **{**_PARAMS, "max_push_candles": mpc})
        assert r["APUSH_BULL_2_2_2"].iloc[4] == 0.0, f"mpc={mpc} bound={bound}"


def test_warmup_is_nan_not_zero():
    df = _flat_then_push()
    r = atr_push(df.open, df.high, df.low, df.close, **_PARAMS)
    assert r.iloc[0].isna().all() and r.iloc[1].isna().all()
    assert r.iloc[2].notna().all()


def test_flat_frame_atr_is_float_residue_not_zero():
    """The reason the degenerate-ATR guard is RELATIVE, pinned as a fact
    about this fork rather than an assumption: on a perfectly flat frame
    `pandas_ta.atr` returns 2.22e-16, NOT 0.0, so a bare `atr > 0` mask
    would not fire."""
    from pandas_ta.volatility.atr import atr as _atr
    df = _frame([(100.0, 100.0, 100.0, 100.0)] * 12)
    a = _atr(df.high, df.low, df.close, length=2)
    assert (a.iloc[2:] > 0).all()
    assert a.iloc[-1] < 1e-15


def test_degenerate_atr_would_blow_up_a_division_flags_are_immune():
    """The reason any FUTURE continuous form must carry a RELATIVE ATR
    guard, kept as an executable record after the strength columns were
    removed. On this frame the ATR window is flat while the push window
    reaches outside it, so `leg / atr` evaluates to 4.50e+16. The shipped
    FLAG columns are structurally immune -- Pine compares against ATR and
    never divides by it -- which this asserts rather than assumes."""
    from pandas_ta.volatility.atr import atr as _atr
    rows = [(100.0, 100.0, 90.0, 100.0)] + [(100.0, 100.0, 100.0, 100.0)] * 8
    df = _frame(rows)
    a = _atr(df.high, df.low, df.close, length=2)
    leg = df.close - df.low.rolling(9).min()
    assert a.iloc[-1] > 0                       # a bare `> 0` guard passes
    assert (leg.iloc[-1] / a.iloc[-1]) > 1e15   # ...and it does not protect
    r = atr_push(df.open, df.high, df.low, df.close,
                 **{**_PARAMS, "push_window": 9})
    assert not np.isinf(r.to_numpy(dtype=float)).any()
    assert set(r["APUSH_BULL_2_2_9"].dropna().unique()) <= {0.0, 1.0}


def test_flat_frame_produces_no_infinities():
    df = _frame([(100.0, 100.0, 100.0, 100.0)] * 12)
    r = atr_push(df.open, df.high, df.low, df.close, **_PARAMS)
    assert not np.isinf(r.to_numpy(dtype=float)).any()
    assert r["APUSH_BULL_2_2_2"].iloc[2:].eq(0.0).all()


# ---------------------------------------------------------------------
# scale-freedom
# ---------------------------------------------------------------------
def _noise_frame(seed=3, n=600):
    rng = np.random.default_rng(seed)
    c = 100 * np.exp(np.cumsum(rng.normal(0, 0.012, n)))
    h = c * (1 + np.abs(rng.normal(0, 0.009, n)))
    l = c * (1 - np.abs(rng.normal(0, 0.009, n)))
    o = np.clip(c * (1 + rng.normal(0, 0.005, n)), l, h)
    return _frame(list(zip(o, h, l, c)))


@pytest.mark.parametrize("k", [10.0, 0.1, 1234.5])
def test_scale_free_under_price_rescale(k):
    """Both columns are invariant to multiplying every price by k.

    NaN masks must match exactly too -- an invariance claim that quietly
    changed which bars are populated would be worthless. And the columns
    must not be trivially invariant by being constant: a column that
    never fires is invariant to everything, so the fire count is asserted
    non-degenerate before the comparison is allowed to mean anything."""
    df = _noise_frame()
    base = atr_push(df.open, df.high, df.low, df.close)
    scaled = atr_push(df.open * k, df.high * k, df.low * k, df.close * k)
    assert (base.isna().to_numpy() == scaled.isna().to_numpy()).all()
    for col in base.columns:
        b, s = base[col].dropna(), scaled[col].dropna()
        assert len(b) > 100
        assert 0 < b.sum() < len(b), f"{col} is constant; invariance is vacuous"
        np.testing.assert_allclose(s.to_numpy(), b.to_numpy(),
                                   rtol=1e-9, atol=1e-12)


def test_volume_is_not_read():
    """`atr_push` takes no volume argument at all -- the strongest form
    of volume-invariance. Pinned so a future edit cannot add one silently."""
    import inspect
    assert "volume" not in inspect.signature(atr_push).parameters


# ---------------------------------------------------------------------
# causality
# ---------------------------------------------------------------------
def _load_mutant(old, new, tag):
    """Load a copy of the REAL module source with exactly one substring
    replaced, exec'd into a fresh in-memory module. Never a hand-written
    reimplementation -- it is provably this algorithm plus one edit."""
    real = importlib.import_module("pandas_ta.trend.atr_push")
    src = open(real.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType(f"_atr_push_mutant_{tag}")
    mod.__file__ = real.__file__
    exec(compile(src.replace(old, new), real.__file__, "exec"), mod.__dict__)
    return mod


def test_mutant_a_dropping_the_shift_kills_every_flag():
    """Mutant A: `high.shift(1).rolling(...)` -> `high.rolling(...)`,
    i.e. `ta.highest(high, N)` instead of `ta.highest(high[1], N)`.

    Including the current bar makes the breakout test `close > max(high
    over a window CONTAINING high[t])`, which subsumes `close > high[t]`
    and is therefore unsatisfiable for valid OHLC. The mutant does not
    leak -- it produces a silently DEAD column, which is exactly why an
    assertion could not have caught this and a mutant can."""
    mod = _load_mutant(
        "prev_structure_high = high.shift(1).rolling(breakout_lookback).max()",
        "prev_structure_high = high.rolling(breakout_lookback).max()",
        "a",
    )
    df = _noise_frame()
    real = atr_push(df.open, df.high, df.low, df.close)
    mut = mod.atr_push(df.open, df.high, df.low, df.close)
    assert real["APUSH_BULL_14_5_5"].sum() > 0
    assert mut["APUSH_BULL_14_5_5"].sum() == 0
    # the bear side is untouched by this edit -- it reads prev_structure_LOW
    pd.testing.assert_series_equal(real["APUSH_BEAR_14_5_5"],
                                   mut["APUSH_BEAR_14_5_5"])


def test_mutant_b_forward_shifted_push_window_changes_output():
    """Mutant B: the push window reads one bar into the FUTURE
    (`low.shift(-1).rolling(...)`). This is the leak the fixture must be
    able to see; if this passed unchanged, the causality suite would have
    no power and mutant A would prove nothing about leakage."""
    mod = _load_mutant(
        "recent_push_low = low.rolling(push_window).min()",
        "recent_push_low = low.shift(-1).rolling(push_window).min()",
        "b",
    )
    df = _noise_frame()
    real = atr_push(df.open, df.high, df.low, df.close)
    mut = mod.atr_push(df.open, df.high, df.low, df.close)
    disagree = (real["APUSH_BULL_14_5_5"] != mut["APUSH_BULL_14_5_5"]).sum()
    assert disagree > 0, "fixture cannot detect a one-bar future leak"


def test_truncation_matches_prefix_of_full_series():
    """Necessary (not sufficient) causality check: computing on the first
    `k` bars must reproduce the first `k` values of the full run exactly.
    A bar's value therefore cannot depend on anything after it."""
    df = _noise_frame()
    full = atr_push(df.open, df.high, df.low, df.close)
    for k in (120, 300, 455):
        d = df.iloc[:k]
        part = atr_push(d.open, d.high, d.low, d.close)
        pd.testing.assert_frame_equal(part, full.iloc[:k])


# ---------------------------------------------------------------------
# ATR provenance: this fork's atr vs Pine's ta.atr
# ---------------------------------------------------------------------
def test_atr_smoothing_deviates_from_pine_only_during_warmup():
    """This fork's `pandas_ta.atr` uses `ewm(alpha=1/length, adjust=True)`
    (upstream pandas_ta's `rma`), while Pine's `ta.atr` is the recursive
    Wilder form. They are NOT identical early on and DO converge.

    Following the fork convention is deliberate: every sibling module in
    this package that reads ATR (`sd_zone_pro`, `rejection_blocks`,
    `band_cross_retest`, `bdi4kewl`, `inverse_fvg`, ...) reads the same
    `atr`, so deviating here would make APUSH's ATR inconsistent with
    every other ATR in the same engine frame.

    This test PINS the measured behaviour instead of claiming equality:
    the relative gap is material in the first ~50 bars and negligible
    thereafter. The bounds below were measured, then written down.
    """
    from pandas_ta.volatility.atr import atr as _atr
    from pandas_ta.volatility.true_range import true_range

    df = _noise_frame(seed=7, n=1200)
    shipped = _atr(df.high, df.low, df.close, length=14)

    L, n = 14, len(df)
    tr = true_range(df.high, df.low, df.close).to_numpy(dtype=float).copy()
    tr[0] = df.high.iloc[0] - df.low.iloc[0]      # Pine's ta.tr(true) bar 0
    wilder = np.full(n, np.nan)
    wilder[L - 1] = np.nanmean(tr[:L])            # Pine seeds ta.rma with SMA
    for i in range(L, n):
        wilder[i] = (wilder[i - 1] * (L - 1) + tr[i]) / L

    rel = (shipped.to_numpy() - wilder) / wilder
    assert abs(rel[20]) > 1e-3                    # measured 1.17e-2
    assert abs(rel[50]) > 1e-3                    # measured 5.72e-3
    assert np.nanmax(np.abs(rel[200:])) < 1e-6    # measured 5.87e-8
    assert np.nanmax(np.abs(rel[500:])) < 1e-12   # measured ~1e-16


# ---------------------------------------------------------------------
# argument validation
# ---------------------------------------------------------------------
@pytest.mark.parametrize("kw", [
    {"atr_length": 0}, {"atr_length": -1}, {"atr_length": 3.5},
    {"atr_length": float("nan")}, {"atr_length": float("inf")},
    {"atr_length": True}, {"atr_length": "x"},
    {"breakout_lookback": 0}, {"push_window": -2}, {"max_push_candles": 0},
    {"min_push_atr": 0}, {"min_push_atr": -1.0},
    {"min_push_atr": float("nan")}, {"min_push_atr": float("inf")},
])
def test_invalid_arguments_raise_value_error(kw):
    df = _flat_then_push()
    with pytest.raises(ValueError):
        atr_push(df.open, df.high, df.low, df.close, **kw)


def test_none_arguments_use_defaults():
    df = _noise_frame()
    a = atr_push(df.open, df.high, df.low, df.close)
    b = atr_push(df.open, df.high, df.low, df.close, atr_length=None,
                 breakout_lookback=None, push_window=None,
                 min_push_atr=None, max_push_candles=None)
    pd.testing.assert_frame_equal(a, b)


def test_too_short_series_returns_none():
    df = _frame([(100.0, 101.0, 99.0, 100.0)] * 3)
    assert atr_push(df.open, df.high, df.low, df.close) is None


def test_offset_shifts_all_columns():
    df = _noise_frame()
    base = atr_push(df.open, df.high, df.low, df.close)
    off = atr_push(df.open, df.high, df.low, df.close, offset=2)
    for col in base.columns:
        pd.testing.assert_series_equal(off[col], base[col].shift(2))


def test_fillna_kwarg():
    df = _flat_then_push()
    r = atr_push(df.open, df.high, df.low, df.close, fillna=-1.0, **_PARAMS)
    assert r.notna().all().all()
    assert (r.iloc[0] == -1.0).all()
