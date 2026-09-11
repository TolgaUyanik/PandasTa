# -*- coding: utf-8 -*-
"""Root Mean Square (RMS).

PINEBI-1b port of ``rms`` from TradingView's ``ta`` library, publication
``RA2vGpkA``, lines 505-506.

    Mozilla Public License 2.0
    (c) TradingView

Gate A oracle, transcribed from the source::

    export rms(series float source, series int length) =>
        float result = math.sqrt(math.sum(math.pow(source, 2), length) / length)

WHY THE DEFAULT OUTPUT IS A DISTANCE AND THE LEVEL IS BEHIND ``raw=True``
-------------------------------------------------------------------------
``sqrt(mean(close**2))`` is in price units: multiply every price by k and the
output multiplies by k.  That is a LEVEL, and levels are not ML features --
a tree cannot compare `RMS_14` to `close` (``PandasTa/CLAUDE.md``, the ML
feature contract).

This fork already settled how to handle exactly that, in TALIB-1: *"TA-Lib's
price-level outputs are not features. ``HT_TRENDLINE``, ``MAMA``, ``FAMA`` and
``SAREXT`` ship as percent distances; the levels are behind ``raw=True`` and
are registered nowhere."*  `rms` follows that precedent rather than inventing
a second convention: the shipped column is the percent distance from close to
the RMS, and ``raw=True`` returns the level for anyone who wants to plot it.

The distance is scale-free; the level is not, and Gate D is run on the shipped
column, which is the distance.
"""
from numpy import sqrt
from pandas_ta.utils import get_offset, verify_series


def rms(close, length=None, offset=None, **kwargs):
    """Indicator: Root Mean Square (RMS)"""
    # Validate Arguments
    length = int(length) if length and length > 0 else 14
    close = verify_series(close, length)
    offset = get_offset(offset)

    if close is None: return

    # Calculate Result
    level = sqrt((close ** 2).rolling(length).sum() / length)

    raw = kwargs.pop("raw", False)
    if raw:
        rms = level
        name = f"RMS_{length}"
    else:
        # Percent distance, the scale-free form. Positive when close sits
        # above its own root-mean-square over the window.
        rms = 100.0 * (close - level) / level
        name = f"RMS_DIST_PCT_{length}"

    # Offset
    if offset != 0:
        rms = rms.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        rms.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        rms.fillna(method=kwargs["fill_method"], inplace=True)

    # Name and Categorize it
    rms.name = name
    rms.category = "statistics"

    return rms


rms.__doc__ = """Root Mean Square (RMS)

The root mean square of the source over a rolling window.  Because it squares
before averaging, it weights large excursions more heavily than a simple mean
does, so `close` sits below it more often than it sits below an SMA -- the gap
widens with volatility rather than with drift.

DEFAULT OUTPUT IS THE PERCENT DISTANCE, not the level.  The level is in price
units and is therefore not an ML feature; pass `raw=True` to get it. This
matches how `ht_trendline`, `mama` and `sarext` ship in this fork.

Sources:
    https://www.tradingview.com/script/RA2vGpkA/ (MPL-2.0, (c) TradingView)

Calculation:
    Default Inputs:
        length=14

    level = sqrt(rolling_sum(close ** 2, length) / length)
    RMS_DIST_PCT = 100 * (close - level) / level      # default, scale-free
    RMS          = level                              # raw=True, a price level

Args:
    close (pd.Series): Series of 'close's
    length (int): The window. Default: 14
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    raw (bool): Return the price level instead of the percent distance.
        Default: False
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.Series: New feature generated.
"""
