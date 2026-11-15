# -*- coding: utf-8 -*-
from pandas_ta.trend.adx import adx
from pandas_ta.utils import get_offset, verify_series


def adxr(high, low, close, length=None, scalar=None, mamode=None, drift=None, offset=None, **kwargs):
    """Indicator: Average Directional Movement Index Rating (ADXR)"""
    # Validate Arguments
    length = int(length) if length and length > 0 else 14
    high = verify_series(high, 2 * length)
    low = verify_series(low, 2 * length)
    close = verify_series(close, 2 * length)
    offset = get_offset(offset)

    if high is None or low is None or close is None: return

    # Calculate Result
    adx_df = adx(high=high, low=low, close=close, length=length,
                 scalar=scalar, mamode=mamode, drift=drift)
    if adx_df is None: return

    adx_ = adx_df[f"ADX_{length}"]
    adxr = (adx_ + adx_.shift(length)) / 2

    # Offset
    if offset != 0:
        adxr = adxr.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        adxr.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        adxr.fillna(method=kwargs["fill_method"], inplace=True)

    # Name and Categorize it
    adxr.name = f"ADXR_{length}"
    adxr.category = "trend"

    return adxr


adxr.__doc__ = \
"""Average Directional Movement Index Rating (ADXR)

ADXR rates the trend strength ADX reports by averaging it against its own
value `length` bars back, damping ADX's bar-to-bar noise at the cost of a
further `length`-bar lag.

Source: QuantConnect Lean (Apache-2.0), `AverageDirectionalMovementIndexRating.cs`:
    adxr = (ADX + ADX[period]) / 2
Also jesse (MIT) `adxr.py`, the same average.

ADX itself is this fork's own `adx()` (Wilder's RMA smoothing, scalar 100),
not re-derived, so ADXR inherits ADX's warm-up and its 0-100 range.

Calculation:
    Default Inputs:
        length=14
    ADX = Average Directional Movement Index (this fork's adx(), length)

    ADXR = (ADX + ADX[length bars ago]) / 2

Args:
    high (pd.Series): Series of 'high's
    low (pd.Series): Series of 'low's
    close (pd.Series): Series of 'close's
    length (int): It's period. Default: 14
    scalar (float): How much to magnify. Default: 100
    mamode (str): ADX's moving average mode. Default: 'rma'
    drift (int): The difference period. Default: 1
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.Series: New feature generated, in [0, 100].
"""
