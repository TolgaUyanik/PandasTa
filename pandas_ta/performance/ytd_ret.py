# -*- coding: utf-8 -*-
from pandas import DatetimeIndex
from pandas_ta.utils import get_offset, verify_series


def ytd_ret(open_, close, offset=None, **kwargs):
    """Indicator: Year-to-Date Return (YTD_RET)"""
    # Validate Arguments
    open_ = verify_series(open_)
    close = verify_series(close)
    offset = get_offset(offset)

    # None, not a raise: one frame without usable dates must not abort a strategy() sweep.
    if (open_ is None or close is None
            or not isinstance(open_.index, DatetimeIndex)
            or not open_.index.equals(close.index)
            # "First row of the year" is the earliest bar only on an ascending index; NaT fails this too.
            or not open_.index.is_monotonic_increasing):
        return

    # Calculate Result
    # Not transform("first"): it skips NaN, so a missing first open would be read from a later bar.
    anchor = open_.groupby(open_.index.year).transform(lambda s: s.iloc[0])
    ytd = close / anchor.where(anchor != 0) - 1

    # Offset
    if offset != 0:
        ytd = ytd.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        ytd.fillna(kwargs["fillna"], inplace=True)

    # Name and Categorize it
    ytd.name = "YTD_RET"
    ytd.category = "performance"

    return ytd


ytd_ret.__doc__ = \
"""Year-to-Date Return (YTD_RET)

The return from the open of the year's first bar to this bar's close, as a
fraction. Resets on each calendar year's first bar, so on an ascending index the
anchor is known at that bar and every later bar of the year reads only the past.

Source: Reddit, tier 4 (crowd talk, untested here), r/thinkorswim 1opks13
(2025-11-06), https://www.reddit.com/r/thinkorswim/comments/1opks13/. Formula
and claimed use as restated by issue #204 (thread not read here): "def ytd =
Round((close / yearOpen - 1) * 100, 2);", a watchlist column showing the gain
since the period start. Departures: a fraction, not a percent, and not rounded.

Years are calendar years of the index as written, so a tz-aware index resets
on local time. A frame that starts mid-year anchors its first partial year on
its first bar's open, the earliest open it has. If a year's first open is NaN
or zero that whole year is NaN.

Calculation:
    YTD_RET = close / open[first bar of this calendar year] - 1

Args:
    open_ (pd.Series): Series of 'open's, with an ascending DatetimeIndex
    close (pd.Series): Series of 'close's, with the same index as open_
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)

Returns:
    pd.Series: YTD_RET, or None if the index is not a DatetimeIndex, is not
        ascending (NaT included), or differs between open_ and close (a shared
        subset of labels is not enough).
"""
