# -*- coding: utf-8 -*-
import numpy as np
from pandas import DataFrame, Series

from pandas_ta.utils import get_offset, verify_series


def swing_equilibrium(high, low, close, left=None, right=None, offset=None, **kwargs):
    """Indicator: Swing Equilibrium (SWINGEQ)"""
    # Validate Arguments
    left = int(left) if left and left > 0 else 5
    right = int(right) if right and right > 0 else 5
    high = verify_series(high, left + right + 1)
    low = verify_series(low, left + right + 1)
    close = verify_series(close, left + right + 1)
    offset = get_offset(offset)

    if high is None or low is None or close is None: return

    window = left + right + 1

    # Causal pivot confirmation: a bar at position i is a pivot high/low when
    # it is the max/min of the window [i-left, i+right]. That fact is only
    # KNOWN once bar i+right has printed -- so the confirmed value is placed
    # at i+right, not at i (this is `series.shift(right)` evaluated against
    # a trailing, non-centered rolling window ending at i+right, which is
    # exactly the window [i-left, i+right]). Do NOT use `rolling(center=True)`
    # here -- that computes the window with future bars relative to the
    # candidate bar and is not causal (see the porting-session finding below).
    # CRITICAL fix (Fletcher round 1): bare `== window max` confirms EVERY
    # bar in a flat run as its own pivot (a plateau's max is tied across
    # all of it), so `.ffill()` drags swing_high/low down to a trivial
    # decayed level and silently overwrites a real, larger prior swing --
    # verified concretely on this file's own "designed breakout" fixture:
    # a 5-bar flat run at the end of the window produced spurious pivots
    # that erased the intended 110 swing high before the real breakout bar.
    #
    # CRITICAL fix round 2 (Fletcher round 2): the first fix over-corrected
    # -- requiring the candidate be the UNIQUE extreme in its window means a
    # genuine 2-bar tie (a double-top/double-bottom, an entirely ordinary
    # pattern, not a plateau edge case) confirms NO pivot at all, silently,
    # for the rest of the series. Verified: high=[90,105,90,105,90,...],
    # left=right=2 never confirmed a single pivot under the round-1 fix.
    # Correct rule (deterministic, single-fire per tie group, and it is
    # what lets a real Pine chart show exactly one pivot per tie): a
    # candidate confirms iff it achieves the window extreme AND no LATER
    # bar within the window also achieves it -- the RIGHTMOST tied bar
    # wins. Bars BEFORE the candidate are free to tie; bars AFTER it are
    # not. Implemented as an explicit bar-by-bar scan rather than a
    # vectorized rolling comparison: after round 1's vectorized-but-wrong
    # attempt and round 2's vectorized-but-also-wrong attempt, correctness
    # by direct inspection beats a third clever alignment trick. Not a hot
    # path (computed once per backtest column, not per bar in a live loop).
    def _confirm_pivots(series, is_high):
        # MINOR, noted (Fletcher round 3): this tie-break depends on
        # `right >= 1` -- `later = vals[i+1:j+1]` is only non-empty when
        # right >= 1, and with right == 0 the tie check silently no-ops,
        # regressing exactly to round 1's plateau-over-firing bug. Currently
        # unreachable only because the wrapper's own validation
        # (`right = int(right) if right and right > 0 else 5`) forces
        # right >= 1 for any falsy/zero/negative input -- an accidental
        # side effect of that validation, not an explicit invariant of
        # THIS function. If that validation is ever loosened, this breaks
        # silently again.
        n = len(series)
        vals = series.to_numpy(dtype=float)
        out = np.full(n, np.nan)
        for j in range(window - 1, n):
            i = j - right
            w = vals[j - window + 1: j + 1]
            extreme = np.nanmax(w) if is_high else np.nanmin(w)
            if np.isnan(vals[i]) or vals[i] != extreme:
                continue
            later = vals[i + 1: j + 1]
            if len(later) and np.any(later == extreme):
                continue  # a later bar ties -- it wins instead
            out[j] = vals[i]
        return Series(out, index=series.index)

    pivot_high = _confirm_pivots(high, is_high=True)
    pivot_low = _confirm_pivots(low, is_high=False)

    # Carry the last confirmed swing high/low forward until the next one.
    swing_high = pivot_high.ffill()
    swing_low = pivot_low.ffill()

    midpoint = (swing_high + swing_low) / 2.0
    dist_pct = (close - midpoint) / close * 100

    # Break of structure: close crosses beyond the last confirmed swing.
    bull_now = close > swing_high
    bull_prev = close.shift(1) <= swing_high.shift(1)
    bos_bull = (bull_now & bull_prev).astype(int)

    bear_now = close < swing_low
    bear_prev = close.shift(1) >= swing_low.shift(1)
    bos_bear = (bear_now & bear_prev).astype(int)

    # Offset
    if offset != 0:
        dist_pct = dist_pct.shift(offset)
        bos_bull = bos_bull.shift(offset)
        bos_bear = bos_bear.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        dist_pct.fillna(kwargs["fillna"], inplace=True)
        bos_bull.fillna(kwargs["fillna"], inplace=True)
        bos_bear.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        dist_pct.fillna(method=kwargs["fill_method"], inplace=True)
        bos_bull.fillna(method=kwargs["fill_method"], inplace=True)
        bos_bear.fillna(method=kwargs["fill_method"], inplace=True)

    # Name and Categorize it
    _props = f"_{left}_{right}"
    dist_pct.name = f"SWINGEQ{_props}"
    bos_bull.name = f"SWINGEQ_BOS_BULL{_props}"
    bos_bear.name = f"SWINGEQ_BOS_BEAR{_props}"

    df = DataFrame({
        dist_pct.name: dist_pct,
        bos_bull.name: bos_bull,
        bos_bear.name: bos_bear,
    })
    df.name = f"SWINGEQ{_props}"
    df.category = "trend"

    return df


swing_equilibrium.__doc__ = \
"""Swing Equilibrium (SWINGEQ)

Scale-free % distance between close and the midpoint ("50% equilibrium",
a standard SMC/ICT concept) of the last confirmed swing high and swing
low, plus break-of-structure (BOS) flags for when close crosses beyond
that swing. A raw swing-high/low LEVEL drifts with an instrument's
nominal price the same way a raw moving average does (INDOC law); this
reformulates it as the scale-free DISTANCE form, the same shape as the
already-validated `dist_to_res_level`.

Source: TradingView community indicator "Market Structure & 50%
Retracement" by Gringa507, https://www.tradingview.com/script/pBEGoW2X-Market-Structure-50-Retracement/
(ported into AwakenAnalytics/Backtesting TVPTA-3, 2026-08-04; MPL-2.0 per
TradingView's open-source publication convention).

⚠ Overlaps existing `pandas_ta.trend.bos` (swing-high/low + BOS booleans)
by design/concept, not by copy -- `bos()` does not expose the underlying
swing price VALUES (only BOS_BULL/BOS_BEAR/HIGHER_HIGH/LOWER_LOW), so the
50%-equilibrium distance this indicator adds could not be derived from
`bos()`'s output alone; the swing tracking is reimplemented here,
CAUSALLY (see the code comment on why `rolling(center=True)` is wrong for
this). ⚠ **Found while porting, out of scope to fix here**: `bos()`'s own
swing-high/low detection uses `rolling(..., center=True)` in a single
batched pass before its per-bar loop runs -- that window includes bars
AFTER the candidate bar, so `bos()` has a look-ahead bug on its own swing
flags. `bos` has zero call sites in `backtesting_engine/` as of this
finding (registered, never wired in), so this is dormant, not live -- but
it means `bos()` is not a safe precedent to copy causality style from,
only registration/DataFrame-shape style.

Calculation:
    Default Inputs:
        left=5, right=5
    swing_high = last HIGH that was the max of [bar-left, bar+right],
        confirmed (visible) only `right` bars after it printed
    swing_low  = mirror, over LOW
    SWINGEQ = (close - (swing_high + swing_low)/2) / close * 100
    SWINGEQ_BOS_BULL = 1 on the bar close first closes above swing_high
    SWINGEQ_BOS_BEAR = 1 on the bar close first closes below swing_low

Args:
    high (pd.Series): Series of 'high's
    low (pd.Series): Series of 'low's
    close (pd.Series): Series of 'close's
    left (int): Bars before the candidate pivot. Default: 5
    right (int): Bars after the candidate pivot required to confirm it
        (also the causal confirmation lag). Default: 5
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.DataFrame: SWINGEQ_left_right, SWINGEQ_BOS_BULL_left_right,
        SWINGEQ_BOS_BEAR_left_right columns.
"""
