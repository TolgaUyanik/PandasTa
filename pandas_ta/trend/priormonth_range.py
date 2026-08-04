# -*- coding: utf-8 -*-
from pandas import DataFrame, Series

from pandas_ta.utils import get_offset, verify_series


def priormonth_range(high, low, close, offset=None, **kwargs):
    """Indicator: Prior-Month Range Distance (PRIORMONTH)"""
    high = verify_series(high)
    low = verify_series(low)
    close = verify_series(close)
    offset = get_offset(offset)

    if high is None or low is None or close is None: return

    # Causal by construction: `.groupby(month).max()/.min()` aggregates
    # each calendar month using only that month's own bars, and the
    # result is used ONLY after `.shift(1)` maps it onto the FOLLOWING
    # month's bars -- so a bar in month M only ever sees month M-1's
    # fully-realized high/low, never its own still-forming month.
    month_key = close.index.to_period("M")
    monthly_high = high.groupby(month_key).max()
    monthly_low = low.groupby(month_key).min()
    prior_high_by_month = monthly_high.shift(1)
    prior_low_by_month = monthly_low.shift(1)

    prior_high = Series(month_key.map(prior_high_by_month), index=close.index, dtype=float)
    prior_low = Series(month_key.map(prior_low_by_month), index=close.index, dtype=float)
    prior_mid = (prior_high + prior_low) / 2.0

    dist_high_pct = (close - prior_high) / close * 100
    dist_mid_pct = (close - prior_mid) / close * 100
    dist_low_pct = (close - prior_low) / close * 100

    # Offset
    if offset != 0:
        dist_high_pct = dist_high_pct.shift(offset)
        dist_mid_pct = dist_mid_pct.shift(offset)
        dist_low_pct = dist_low_pct.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        dist_high_pct.fillna(kwargs["fillna"], inplace=True)
        dist_mid_pct.fillna(kwargs["fillna"], inplace=True)
        dist_low_pct.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        dist_high_pct.fillna(method=kwargs["fill_method"], inplace=True)
        dist_mid_pct.fillna(method=kwargs["fill_method"], inplace=True)
        dist_low_pct.fillna(method=kwargs["fill_method"], inplace=True)

    dist_high_pct.name = "PRIORMONTH_HIGH"
    dist_mid_pct.name = "PRIORMONTH_MID"
    dist_low_pct.name = "PRIORMONTH_LOW"

    df = DataFrame({
        dist_high_pct.name: dist_high_pct,
        dist_mid_pct.name: dist_mid_pct,
        dist_low_pct.name: dist_low_pct,
    })
    df.name = "PRIORMONTH"
    df.category = "trend"

    return df


priormonth_range.__doc__ = \
"""Prior-Month Range Distance (PRIORMONTH)

Scale-free % distance from close to the PREVIOUS completed calendar
month's high, midpoint, and low -- the monthly-periodicity sibling of
`priorday_fib`. Unlike `priorday_fib` (where one daily bar already IS one
session, so "prior session" collapses to `.shift(1)`), a calendar month
spans many daily bars, so the prior month's high/low must be aggregated
across all of that month's bars before being held constant through the
following month.

Source: TradingView community indicator "Institution Levels Gath" by
wintonbanks-adjacent authorship (see `datastore/source/pine_triage.csv`
for the exact attribution row), section "18. PREVIOUS-MONTH RELATIONSHIP"
(ported into AwakenAnalytics/Backtesting TVPTA-3, 2026-08-04; MPL-2.0 per
TradingView's open-source publication convention). Only the prior-month
high/low/midpoint distance is ported -- the source script's psychological
(round-number) price-level grid, monthly separators/shading, and
alert/table UI are NOT replicated: round-number levels are absolute price
grids (not scale-free under `close, level -> k*close, k*level`) and the
drawing/table sections carry no per-bar numeric series at all.

Calculation:
    month_key = date's calendar month
    monthly_high = high grouped by month_key, aggregated with max
    monthly_low  = low  grouped by month_key, aggregated with min
    prior_high = monthly_high shifted 1 month; prior_low likewise
    prior_mid  = (prior_high + prior_low) / 2
    PRIORMONTH_HIGH = (close - prior_high) / close * 100
    PRIORMONTH_MID  = (close - prior_mid)  / close * 100
    PRIORMONTH_LOW  = (close - prior_low)  / close * 100

Args:
    high (pd.Series): Series of 'high's
    low (pd.Series): Series of 'low's
    close (pd.Series): Series of 'close's
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.DataFrame: PRIORMONTH_HIGH, PRIORMONTH_MID, PRIORMONTH_LOW columns.
"""
