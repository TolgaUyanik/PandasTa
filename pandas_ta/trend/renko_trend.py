# -*- coding: utf-8 -*-
import numpy as np
from pandas import DataFrame, Series

from pandas_ta.utils import get_offset, verify_series


def renko_trend(close, brick_pct=None, brick_fixed=None, max_iterations=None,
                 offset=None, **kwargs):
    """Indicator: Synthetic Renko Trend (RENKO)"""
    brick_pct = float(brick_pct) if brick_pct and brick_pct > 0 else 1.0
    max_iterations = int(max_iterations) if max_iterations and max_iterations > 0 else 100
    close = verify_series(close)
    offset = get_offset(offset)

    if close is None: return

    # Box size: a fixed price-unit value if `brick_fixed` is given,
    # otherwise a percentage of the CURRENT bar's close (auto-scales with
    # price -- the source's default and recommended mode).
    if brick_fixed and brick_fixed > 0:
        box = np.full(len(close), float(brick_fixed))
    else:
        box = (close.to_numpy(dtype=float) * brick_pct) / 100.0

    vals = close.to_numpy(dtype=float)
    n = len(vals)
    r_close = np.full(n, np.nan)
    trend = np.zeros(n, dtype=int)

    # Sequential Renko-close construction: the synthetic level only ever
    # moves in fixed `box` increments, one brick at a time, and can step
    # MULTIPLE bricks within a single native bar if the move is large
    # enough (the inner while loop, capped at max_iterations matching the
    # source) -- direction flips only when price breaks a full brick
    # against the current trend. Initial state seeds `r_close` at the
    # first bar's own close (the source's `if na(rClose): rClose := close`),
    # not 0, so the very first bar never spuriously "breaks" a brick.
    prev_close = np.nan
    prev_trend = 1
    for idx in range(n):
        if np.isnan(vals[idx]) or np.isnan(box[idx]):
            r_close[idx] = prev_close
            trend[idx] = prev_trend
            continue
        if np.isnan(prev_close):
            prev_close = vals[idx]
            prev_trend = 1
            r_close[idx] = prev_close
            trend[idx] = prev_trend
            continue

        cur_close = prev_close
        cur_trend = prev_trend
        c = vals[idx]
        b = box[idx]
        for _ in range(max_iterations):
            if cur_trend == 1:
                if c >= cur_close + b:
                    cur_close = cur_close + b
                elif c <= cur_close - b:
                    cur_trend = -1
                    cur_close = cur_close - b
                else:
                    break
            else:
                if c <= cur_close - b:
                    cur_close = cur_close - b
                elif c >= cur_close + b:
                    cur_trend = 1
                    cur_close = cur_close + b
                else:
                    break

        r_close[idx] = cur_close
        trend[idx] = cur_trend
        prev_close = cur_close
        prev_trend = cur_trend

    r_close = Series(r_close, index=close.index)
    trend = Series(trend, index=close.index)
    dist_pct = (close - r_close) / close * 100

    # Offset
    if offset != 0:
        trend = trend.shift(offset)
        dist_pct = dist_pct.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        trend.fillna(kwargs["fillna"], inplace=True)
        dist_pct.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        trend.fillna(method=kwargs["fill_method"], inplace=True)
        dist_pct.fillna(method=kwargs["fill_method"], inplace=True)

    _props = f"_{brick_pct}" if not (brick_fixed and brick_fixed > 0) else f"_F{brick_fixed}"
    trend.name = f"RENKO_TREND{_props}"
    dist_pct.name = f"RENKO_DIST{_props}"

    df = DataFrame({trend.name: trend, dist_pct.name: dist_pct})
    df.name = f"RENKO{_props}"
    df.category = "trend"

    return df


renko_trend.__doc__ = \
"""Synthetic Renko Trend (RENKO)

A synthetic Renko brick tracker built directly from close, independent of
the chart's native bar size: a running level (`r_close`) only moves in
fixed `box`-sized increments, and flips direction only when price breaks
a full brick against the current trend -- exactly the classic Renko
construction rule, computed causally bar-by-bar (a single native bar can
advance the synthetic level by more than one brick, handled by the inner
iteration loop, capped at `max_iterations` matching the source). Not a
duplicate of anything in the catalog (no Renko/box-tracker exists).
`RENKO_TREND` is the categorical +1/-1 state; `RENKO_DIST` is the
scale-free % distance from close to the current brick level.

Source: TradingView community indicator "Smart Renko Engine" (see
`datastore/source/pine_triage.csv` for the exact attribution row) (ported
into AwakenAnalytics/Backtesting TVPTA-3, 2026-08-04; MPL-2.0 per
TradingView's open-source publication convention). Only the core Renko
engine (source lines ~181-218) is ported -- the source's asset-detection
auto-brick-sizing preset table, MA ribbon overlay, and dashboard are all
decorative/config and NOT replicated; `brick_pct`/`brick_fixed` expose the
same two sizing MODES (percentage-of-price vs. fixed point value) without
the asset-name lookup table.

Calculation:
    Default Inputs:
        brick_pct=1.0 (percent-of-close box sizing), max_iterations=100
    box = brick_fixed if brick_fixed else close * brick_pct / 100
    Sequential per bar: while price breaks r_close +/- box (trend-
        dependent), step r_close by one box increment (up to
        max_iterations steps per bar); a break AGAINST the current trend
        flips trend and steps the level in the new direction.
    RENKO_TREND = +1 / -1 (current brick direction)
    RENKO_DIST  = (close - r_close) / close * 100

Args:
    close (pd.Series): Series of 'close's
    brick_pct (float): Box size as % of close (used unless brick_fixed is
        given). Default: 1.0
    brick_fixed (float): Box size as a fixed price-unit value. Overrides
        brick_pct when given. Default: None
    max_iterations (int): Cap on bricks advanced within a single bar.
        Default: 100
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.DataFrame: RENKO_TREND, RENKO_DIST columns.
"""
