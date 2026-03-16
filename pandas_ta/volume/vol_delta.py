# -*- coding: utf-8 -*-
import numpy as np
from pandas import Series
from pandas_ta.utils import get_offset, verify_series


def vol_delta(open_, high, low, close, volume, offset=None, **kwargs):
    """Indicator: Volume Delta (Approximated)"""
    # Validate Arguments
    open_ = verify_series(open_, 1)
    high = verify_series(high, 1)
    low = verify_series(low, 1)
    close = verify_series(close, 1)
    volume = verify_series(volume, 1)
    offset = get_offset(offset)

    if any(s is None for s in [open_, high, low, close, volume]): return

    # Calculate Result — proxy for buy/sell pressure without tick data
    total_range = high - low
    result = volume * (close - open_) / total_range.replace(0, np.nan)

    if offset != 0:
        result = result.shift(offset)

    if "fillna" in kwargs:
        result.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        result.fillna(method=kwargs["fill_method"], inplace=True)

    result.name = "VOL_DELTA_APPROX"
    result.category = "volume"

    return result


vol_delta.__doc__ = \
"""Volume Delta Approximation (vol_delta)

Approximates buy/sell volume pressure using OHLCV data without tick data.
Positive values indicate net buying pressure; negative values indicate
net selling pressure.

Sources:
    AwakenAnalytics custom indicator (indicator_engine.py)

Calculation:
    VOL_DELTA_APPROX = Volume * (Close - Open) / (High - Low)

    Positive when close > open (bullish bar = buying pressure)
    Negative when close < open (bearish bar = selling pressure)
    Magnitude scaled by how much of the bar range was used.

Args:
    open_ (pd.Series): Series of 'open's
    high (pd.Series): Series of 'high's
    low (pd.Series): Series of 'low's
    close (pd.Series): Series of 'close's
    volume (pd.Series): Series of 'volume's
    offset (int): Periods to offset. Default: 0

Returns:
    pd.Series: VOL_DELTA_APPROX
"""
