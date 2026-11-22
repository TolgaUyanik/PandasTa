# -*- coding: utf-8 -*-
from pandas import DatetimeIndex
from pandas_ta.utils import get_offset, verify_series


def qtd_ret(open_, close, offset=None, **kwargs):
    """Indicator: Quarter-to-Date Return (QTD_RET)"""
    # Validate Arguments
    open_ = verify_series(open_)
    close = verify_series(close)
    offset = get_offset(offset)

    # None, not a raise: one frame without usable dates must not abort a strategy() sweep.
    if (open_ is None or close is None
            or not isinstance(open_.index, DatetimeIndex)
            or not open_.index.equals(close.index)
            # "First row of the quarter" is the earliest bar only on an ascending index; NaT fails this too.
            or not open_.index.is_monotonic_increasing):
        return

    # Calculate Result
    # Not transform("first"): it skips NaN, so a missing first open would be read from a later bar.
    quarter = open_.index.year * 4 + open_.index.quarter
    anchor = open_.groupby(quarter).transform(lambda s: s.iloc[0])
    qtd = close / anchor.where(anchor != 0) - 1

    # Offset
    if offset != 0:
        qtd = qtd.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        qtd.fillna(kwargs["fillna"], inplace=True)

    # Name and Categorize it
    qtd.name = "QTD_RET"
    qtd.category = "performance"

    return qtd


qtd_ret.__doc__ = \
"""Quarter-to-Date Return (QTD_RET)

The return from the open of the quarter's first bar to this bar's close, as a
fraction. Resets on each quarter's first bar, so on an ascending index the
anchor is known at that bar and every later bar of the quarter reads only the
past.

Source: Reddit, tier 4 (crowd talk, untested here), r/thinkorswim 1opks13
(2025-11-06), https://www.reddit.com/r/thinkorswim/comments/1opks13/, restated
by issue #205: "same, quarter: month <= 3 -> 1, <= 6 -> 2, <= 9 -> 3, else 4";
the poster's own formula is the year form, "def ytd = Round((close / yearOpen
- 1) * 100, 2)" for a watchlist column showing the gain since the period
start. Departure: a fraction, not a percent. This is `mtd_ret`
(`docs/MtdRetMeasured.md`, issue #206, same source and quote) with the
anchoring period changed from calendar month to calendar quarter; the quarter
boundary matches the issue's month-range mapping exactly (`pandas`'s
`DatetimeIndex.quarter`: month 1-3 -> 1, 4-6 -> 2, 7-9 -> 3, 10-12 -> 4).

Quarters are calendar quarters of the index as written, so a tz-aware index
resets on local time. A frame that starts mid-quarter anchors its first
partial quarter on its first bar's open, the earliest open it has. If a
quarter's first open is NaN or zero that whole quarter is NaN.

Calculation:
    QTD_RET = close / open[first bar of this calendar quarter] - 1

Args:
    open_ (pd.Series): Series of 'open's, with an ascending DatetimeIndex
    close (pd.Series): Series of 'close's, with the same index as open_
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)

Returns:
    pd.Series: QTD_RET, or None if the index is not a DatetimeIndex, is not
        ascending (NaT included), or differs between open_ and close (a shared
        subset of labels is not enough).
"""
