# -*- coding: utf-8 -*-
import numpy as np
from pandas import DataFrame, Series

from pandas_ta.utils import get_offset, verify_series


def nwog(open_, close, offset=None, **kwargs):
    """Indicator: New Week Opening Gap Distance (NWOG)"""
    open_ = verify_series(open_)
    close = verify_series(close)
    offset = get_offset(offset)

    if open_ is None or close is None: return

    # A new week's opening gap forms once: at the first bar of each week,
    # bracketed by that bar's own open and the PRIOR bar's close (which is
    # chronologically the last trading day of the PRIOR week -- no
    # look-ahead, `close.shift(1)` is data from before the current bar).
    # The zone then holds constant (ffill) through the rest of the week,
    # matching the source Pine script's ray-extends-right-until-mitigated
    # behavior, simplified the same way `priorday_fib` holds its prior-bar
    # zone for a fixed period rather than tracking live mitigation.
    # Anchor pinned explicitly (weeks end Sunday) rather than relying on
    # pandas' default -- self-documenting instead of an implicit choice a
    # future pandas version or refactor could silently shift.
    week_key = Series(close.index.to_period("W-SUN"), index=close.index)
    is_new_week = week_key.ne(week_key.shift(1))

    prev_close = close.shift(1)
    raw_top = np.where(is_new_week, np.maximum(open_, prev_close), np.nan)
    raw_bottom = np.where(is_new_week, np.minimum(open_, prev_close), np.nan)

    gap_top = Series(raw_top, index=close.index).ffill()
    gap_bottom = Series(raw_bottom, index=close.index).ffill()

    dist_top_pct = (close - gap_top) / close * 100
    dist_bottom_pct = (close - gap_bottom) / close * 100

    # Offset
    if offset != 0:
        dist_top_pct = dist_top_pct.shift(offset)
        dist_bottom_pct = dist_bottom_pct.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        dist_top_pct.fillna(kwargs["fillna"], inplace=True)
        dist_bottom_pct.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        dist_top_pct.fillna(method=kwargs["fill_method"], inplace=True)
        dist_bottom_pct.fillna(method=kwargs["fill_method"], inplace=True)

    dist_top_pct.name = "NWOG_TOP"
    dist_bottom_pct.name = "NWOG_BOTTOM"

    df = DataFrame({
        dist_top_pct.name: dist_top_pct,
        dist_bottom_pct.name: dist_bottom_pct,
    })
    df.name = "NWOG"
    df.category = "trend"

    return df


nwog.__doc__ = \
"""New Week Opening Gap Distance (NWOG)

Scale-free % distance from close to the top/bottom of the New Week
Opening Gap -- the zone bracketed by the prior week's final close and the
current week's first open. A genuinely distinct concept from
`priorday_fib`/`priormonth_range` (which measure distance to a PRIOR
PERIOD's realized range): NWOG measures the GAP itself, i.e. how far price
has moved between the last print of one week and the first print of the
next, not the range traded during either week.

Source: TradingView community indicator "Key Opens & Session Tracker +
Highs/Lows & NWOG" by LuxAlgo (see `datastore/source/pine_triage.csv` for
the exact attribution row), the "New Week Opening Gap (NWOG)" section
(ported into AwakenAnalytics/Backtesting TVPTA-3, 2026-08-04; MPL-2.0 per
TradingView's open-source publication convention). Only the NWOG
computation is ported -- the source script's Key Open (midnight/10AM) ray
tracking and its Asian/London intraday session high/low tracker are
intraday-timezone-dependent (session windows narrower than one daily bar)
and are NOT replicated; see the DEFER note on this candidate in
`datastore/source/pine_candidates_families.csv`.

Calculation:
    week_key = date's ISO week
    is_new_week = week_key differs from the prior bar's week_key
    On is_new_week bars: gap_top = max(open, close.shift(1))
                         gap_bottom = min(open, close.shift(1))
    Both held constant (forward-filled) through the rest of the week.
    NWOG_TOP    = (close - gap_top)    / close * 100
    NWOG_BOTTOM = (close - gap_bottom) / close * 100

Args:
    open_ (pd.Series): Series of 'open's
    close (pd.Series): Series of 'close's
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.DataFrame: NWOG_TOP, NWOG_BOTTOM columns.
"""
