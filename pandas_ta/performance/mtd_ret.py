# -*- coding: utf-8 -*-
from pandas import DatetimeIndex
from pandas_ta.utils import get_offset, verify_series


def mtd_ret(open_, close, offset=None, **kwargs):
    """Indicator: Month-to-Date Return (MTD_RET)"""
    # Validate Arguments
    open_ = verify_series(open_)
    close = verify_series(close)
    offset = get_offset(offset)

    # None, not a raise: one frame without usable dates must not abort a strategy() sweep.
    if (open_ is None or close is None
            or not isinstance(open_.index, DatetimeIndex)
            or not open_.index.equals(close.index)
            # "First row of the month" is the earliest bar only on an ascending index; NaT fails this too.
            or not open_.index.is_monotonic_increasing):
        return

    # Calculate Result
    # Not transform("first"): it skips NaN, so a missing first open would be read from a later bar.
    month = open_.index.year * 12 + open_.index.month
    anchor = open_.groupby(month).transform(lambda s: s.iloc[0])
    mtd = close / anchor.where(anchor != 0) - 1

    # Offset
    if offset != 0:
        mtd = mtd.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        mtd.fillna(kwargs["fillna"], inplace=True)

    # Name and Categorize it
    mtd.name = "MTD_RET"
    mtd.category = "performance"

    return mtd


mtd_ret.__doc__ = \
"""Month-to-Date Return (MTD_RET)

The return from the open of the month's first bar to this bar's close, as a
fraction. Resets on each month's first bar, so on an ascending index the anchor
is known at that bar and every later bar of the month reads only the past.

Source: Reddit, tier 4 (crowd talk, untested here), r/thinkorswim 1opks13
(2025-11-06), https://www.reddit.com/r/thinkorswim/comments/1opks13/. Thread not
read (Reddit returned its Blocked page); formula and claimed use as restated by
issue #206: at the first bar of a new period store its open; value =
(close / period_open - 1) * 100, for a watchlist column showing the gain since
the period start. Departure: a fraction, not a percent.

Months are calendar months of the index as written, so a tz-aware index
resets on local time. A frame that starts mid-month anchors its first partial
month on its first bar's open, the earliest open it has. If a month's first
open is NaN or zero that whole month is NaN.

Calculation:
    MTD_RET = close / open[first bar of this calendar month] - 1

Args:
    open_ (pd.Series): Series of 'open's, with an ascending DatetimeIndex
    close (pd.Series): Series of 'close's, with the same index as open_
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)

Returns:
    pd.Series: MTD_RET, or None if the index is not a DatetimeIndex, is not
        ascending (NaT included), or differs between open_ and close (a shared
        subset of labels is not enough).
"""
