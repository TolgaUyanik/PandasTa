# -*- coding: utf-8 -*-
import numpy as np
from pandas import DataFrame, Series

from pandas_ta.volatility.atr import atr
from pandas_ta.utils import get_offset, verify_series


def liquidity_compression_box(high, low, close, open_, window=None, atr_length=None,
                               max_atr_mult=None, min_wick_touches=None, max_body_pct=None,
                               touch_tol_pct=None, offset=None, **kwargs):
    """Indicator: Liquidity Compression Box (LCB)"""
    window = int(window) if window and window > 0 else 5
    atr_length = int(atr_length) if atr_length and atr_length > 0 else 14
    max_atr_mult = float(max_atr_mult) if max_atr_mult and max_atr_mult > 0 else 3.0
    min_wick_touches = int(min_wick_touches) if min_wick_touches and min_wick_touches > 0 else 3
    max_body_pct = float(max_body_pct) if max_body_pct and max_body_pct > 0 else 95.0
    touch_tol_pct = float(touch_tol_pct) if touch_tol_pct and touch_tol_pct > 0 else 0.03
    high = verify_series(high, window)
    low = verify_series(low, window)
    close = verify_series(close, window)
    open_ = verify_series(open_, window)
    offset = get_offset(offset)

    if high is None or low is None or close is None or open_ is None: return

    atr_val = atr(high, low, close, length=atr_length)
    if atr_val is None: return

    n = len(close)
    h = high.to_numpy(dtype=float)
    l = low.to_numpy(dtype=float)
    c = close.to_numpy(dtype=float)
    o = open_.to_numpy(dtype=float)
    a = atr_val.to_numpy(dtype=float)

    box_formed = np.zeros(n, dtype=int)
    breakout_up = np.zeros(n, dtype=int)
    breakout_dn = np.zeros(n, dtype=int)
    dist_high_pct = np.full(n, np.nan)
    dist_low_pct = np.full(n, np.nan)

    # A rolling `window`-bar range compression check: box height <=
    # ATR*max_atr_mult, average candle body-to-range ratio <=
    # max_body_pct%, and at least `min_wick_touches` bars in the window
    # touching within `touch_tol_pct` of either edge. On formation the
    # box freezes (its high/low no longer update) and the script waits
    # for a bar whose high/low AND close both clear a frozen edge --
    # this two-part state (rolling detection + frozen-box breakout wait)
    # is genuinely sequential, implemented as one bar-by-bar pass.
    waiting = False
    frozen_high = np.nan
    frozen_low = np.nan

    for t in range(n):
        # Fletcher round 1 (TVPTA-3-composite): the source gates box
        # formation on `not waiting_breakout` EVALUATED BEFORE the later
        # breakout-check block runs that same bar (Pine's top-to-bottom
        # execution order) -- so a bar that fires a breakout can never
        # ALSO form a brand-new box that same bar. `was_waiting` snapshots
        # the state as of the START of this bar (before the breakout
        # check below can clear it), so the formation gate a few lines
        # down reads the correct, source-faithful value instead of the
        # post-breakout one.
        was_waiting = waiting

        if waiting:
            if h[t] > frozen_high and c[t] > frozen_high:
                breakout_up[t] = 1
                waiting = False
            elif l[t] < frozen_low and c[t] < frozen_low:
                breakout_dn[t] = 1
                waiting = False
            else:
                dist_high_pct[t] = (c[t] - frozen_high) / c[t] * 100
                dist_low_pct[t] = (c[t] - frozen_low) / c[t] * 100
                continue

        if was_waiting or t < window - 1:
            continue

        seg_h = h[t - window + 1: t + 1]
        seg_l = l[t - window + 1: t + 1]
        seg_c = c[t - window + 1: t + 1]
        seg_o = o[t - window + 1: t + 1]
        if np.isnan(seg_h).any() or np.isnan(seg_l).any():
            continue

        cur_high = seg_h.max()
        cur_low = seg_l.min()
        box_height = cur_high - cur_low

        candle_range = seg_h - seg_l
        valid = candle_range > 0
        if valid.any():
            body_ratio = np.abs(seg_c[valid] - seg_o[valid]) / candle_range[valid]
            avg_body_ratio = body_ratio.mean()
        else:
            avg_body_ratio = 1.0  # matches source's 100% fallback

        tolerance = box_height * touch_tol_pct
        upper_touches = int(((seg_h >= cur_high - tolerance) & valid).sum())
        lower_touches = int(((seg_l <= cur_low + tolerance) & valid).sum())
        total_touches = upper_touches + lower_touches

        is_compressed = (not np.isnan(a[t])) and box_height <= a[t] * max_atr_mult
        is_body_small = avg_body_ratio <= max_body_pct / 100.0
        enough_touches = total_touches >= min_wick_touches

        if is_compressed and is_body_small and enough_touches:
            box_formed[t] = 1
            waiting = True
            frozen_high = cur_high
            frozen_low = cur_low
            dist_high_pct[t] = (c[t] - frozen_high) / c[t] * 100
            dist_low_pct[t] = (c[t] - frozen_low) / c[t] * 100

    box_formed = Series(box_formed, index=close.index)
    breakout_up = Series(breakout_up, index=close.index)
    breakout_dn = Series(breakout_dn, index=close.index)
    dist_high_pct = Series(dist_high_pct, index=close.index)
    dist_low_pct = Series(dist_low_pct, index=close.index)

    # Offset
    if offset != 0:
        box_formed = box_formed.shift(offset)
        breakout_up = breakout_up.shift(offset)
        breakout_dn = breakout_dn.shift(offset)
        dist_high_pct = dist_high_pct.shift(offset)
        dist_low_pct = dist_low_pct.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        for s in (box_formed, breakout_up, breakout_dn, dist_high_pct, dist_low_pct):
            s.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        for s in (box_formed, breakout_up, breakout_dn, dist_high_pct, dist_low_pct):
            s.fillna(method=kwargs["fill_method"], inplace=True)

    _props = f"_{window}"
    box_formed.name = f"LCB_FORMED{_props}"
    breakout_up.name = f"LCB_BREAKOUT_UP{_props}"
    breakout_dn.name = f"LCB_BREAKOUT_DN{_props}"
    dist_high_pct.name = f"LCB_HIGH_DIST{_props}"
    dist_low_pct.name = f"LCB_LOW_DIST{_props}"

    df = DataFrame({
        box_formed.name: box_formed,
        dist_high_pct.name: dist_high_pct,
        dist_low_pct.name: dist_low_pct,
        breakout_up.name: breakout_up,
        breakout_dn.name: breakout_dn,
    })
    df.name = f"LCB{_props}"
    df.category = "trend"

    return df


liquidity_compression_box.__doc__ = \
"""Liquidity Compression Box (LCB)

A rolling `window`-bar range-compression detector: a box forms when (1)
the window's high-low range is small relative to ATR, (2) candles in the
window average a small body-to-range ratio (mostly wicks/consolidation,
not directional bodies), and (3) at least `min_wick_touches` bars
touched within a tolerance of either edge (repeated rejection, not a
single spike). Once formed the box FREEZES (its edges stop updating) and
the indicator waits for a bar whose high/low AND close both clear an
edge, firing a directional breakout flag and re-arming for the next box.
Structurally different from the catalog's BB/KC-based `squeeze` (which
uses band WIDTH, not raw range/ATR + body-ratio + touch-count).

Source: TradingView community indicator "Liquidity Compression Box" (see
`datastore/source/pine_triage.csv` for the exact attribution row) (ported
into AwakenAnalytics/Backtesting TVPTA-3, 2026-08-04; MPL-2.0 per
TradingView's open-source publication convention). Only the box-
detection + frozen-breakout state machine is ported -- the source's
trailing take-profit and stop-loss trade-management overlay (a
significant fraction of the file) is out-of-scope position management
and NOT replicated.

Calculation:
    Default Inputs:
        window=5, atr_length=14, max_atr_mult=3.0, min_wick_touches=3,
        max_body_pct=95.0, touch_tol_pct=0.03
    box_height = highest(high, window) - lowest(low, window)
    avg_body_ratio = mean(|close-open|/(high-low)) over window bars with
        nonzero range (falls back to 1.0 if none, matching the source)
    tolerance = box_height * touch_tol_pct
    touches = count(high >= box_high - tolerance) + count(low <= box_low
        + tolerance), over the window
    LCB_FORMED = 1 iff box_height <= ATR*max_atr_mult AND avg_body_ratio
        <= max_body_pct/100 AND touches >= min_wick_touches
    On formation, the box high/low freeze; LCB_HIGH_DIST/LCB_LOW_DIST =
        (close - frozen edge) / close * 100, held until a breakout
    LCB_BREAKOUT_UP = 1 when high AND close both clear the frozen high
    LCB_BREAKOUT_DN = 1 when low AND close both clear the frozen low

Args:
    high (pd.Series): Series of 'high's
    low (pd.Series): Series of 'low's
    close (pd.Series): Series of 'close's
    open_ (pd.Series): Series of 'open's
    window (int): Rolling window size in bars. Default: 5
    atr_length (int): ATR period. Default: 14
    max_atr_mult (float): Max box height as an ATR multiple. Default: 3.0
    min_wick_touches (int): Minimum edge touches required. Default: 3
    max_body_pct (float): Max average body-to-range ratio, in %.
        Default: 95.0
    touch_tol_pct (float): Edge-touch tolerance as a fraction of box
        height. Default: 0.03
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.DataFrame: LCB_FORMED, LCB_HIGH_DIST, LCB_LOW_DIST,
        LCB_BREAKOUT_UP, LCB_BREAKOUT_DN columns.
"""
