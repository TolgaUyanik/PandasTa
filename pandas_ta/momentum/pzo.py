# -*- coding: utf-8 -*-
"""Price Zone Oscillator (PZO).

PINEBI-1b port of ``pzo`` from TradingView's ``ta`` library, publication
``RA2vGpkA``, lines 322-323.

    Mozilla Public License 2.0
    (c) TradingView

Gate A oracle, transcribed from the source::

    export pzo(simple int length) =>
        float result = zone(close, length)

The whole indicator is one call into the shared ``zone()`` helper, which is
kept in ``_zone.py`` because ``vzo`` is the same recursion over volume.
"""
from pandas_ta.momentum._zone import zone
from pandas_ta.utils import get_offset, verify_series


def pzo(close, length=None, offset=None, **kwargs):
    """Indicator: Price Zone Oscillator (PZO)"""
    # Validate Arguments
    length = int(length) if length and length > 0 else 14
    close = verify_series(close, length)
    offset = get_offset(offset)

    if close is None: return

    # Calculate Result
    pzo = zone(close, close, length)
    if pzo is None: return

    # Offset
    if offset != 0:
        pzo = pzo.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        pzo.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        pzo.fillna(method=kwargs["fill_method"], inplace=True)

    # Name and Categorize it
    pzo.name = f"PZO_{length}"
    pzo.category = "momentum"

    return pzo


pzo.__doc__ = """Price Zone Oscillator (PZO)

An EMA of close signed by the bar's own direction, divided by an EMA of close.
Bounded roughly to [-100, 100]: when every bar in the window is an up bar the
numerator equals the denominator and the reading is +100.

Scale-free by construction -- both EMAs are in price units and the ratio
cancels them -- which is what makes it a feature rather than a level.

Sources:
    https://www.tradingview.com/script/RA2vGpkA/ (MPL-2.0, (c) TradingView)

Calculation:
    Default Inputs:
        length=14

    PZO = 100 * ema(sign(change(close)) * close, length) / ema(close, length)

Args:
    close (pd.Series): Series of 'close's
    length (int): The smoothing period. Default: 14
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.Series: New feature generated.
"""
