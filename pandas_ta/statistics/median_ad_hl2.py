# -*- coding: utf-8 -*-
from numpy import abs as npabs, median as npmedian
from pandas_ta.utils import get_offset, verify_series


def _mad(window):
    """Median absolute deviation of one rolling window, scipy's scale=1.0 (unscaled)."""
    return npmedian(npabs(window - npmedian(window)))


def median_ad_hl2(high, low, close, length=None, offset=None, **kwargs):
    """Indicator: Median Absolute Deviation of HL2, scale-free (MEDIANAD_HL2)"""
    # Validate Arguments
    length = int(length) if length and length > 0 else 5
    min_periods = int(kwargs["min_periods"]) if "min_periods" in kwargs and kwargs["min_periods"] is not None else length
    high = verify_series(high, max(length, min_periods))
    low = verify_series(low, max(length, min_periods))
    close = verify_series(close, max(length, min_periods))
    offset = get_offset(offset)

    if high is None or low is None or close is None: return

    # Calculate Result
    hl2 = (high + low) / 2
    mad = hl2.rolling(length, min_periods=min_periods).apply(_mad, raw=True)
    median_ad_hl2 = mad / close

    # Offset
    if offset != 0:
        median_ad_hl2 = median_ad_hl2.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        median_ad_hl2.fillna(kwargs["fillna"], inplace=True)

    # Name and Categorize it
    median_ad_hl2.name = f"MEDIANAD_HL2_{length}"
    median_ad_hl2.category = "statistics"

    return median_ad_hl2


median_ad_hl2.__doc__ = \
"""Median Absolute Deviation of HL2 (MEDIANAD_HL2)

Source: jesse (MIT), `median_ad.py`: `scipy.stats.median_abs_deviation(hl2, window)`.
scipy's function with its default `scale=1.0` is the plain, unscaled statistic --
`median(|x - median(x)|)` -- not the 1.4826-scaled, normal-consistent estimator
of `scipy.stats.median_absolute_deviation` (a different, older, deprecated
function in the same package). This port computes that same unscaled statistic
on a rolling window and divides by `close` to make it scale-free, per the issue's
"scale-free form: /close".

Calculation:
    Default Inputs:
        length=5
    HL2 = (high + low) / 2
    MAD[t] = median(|HL2[t-length+1 .. t] - median(HL2[t-length+1 .. t])|)
    MEDIANAD_HL2 = MAD / close

Args:
    high (pd.Series): Series of 'high's
    low (pd.Series): Series of 'low's
    close (pd.Series): Series of 'close's
    length (int): Rolling window. Default: 5
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    min_periods (int, optional): Minimum bars for a rolling window. Default: length
    fillna (value, optional): pd.DataFrame.fillna(value)

Returns:
    pd.Series: New feature, scale-free (a ratio to close).
"""
