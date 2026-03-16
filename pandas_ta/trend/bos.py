# -*- coding: utf-8 -*-
import numpy as np
from pandas import DataFrame
from pandas_ta.utils import get_offset, verify_series


def bos(high, low, close, swing_length=None, offset=None, **kwargs):
    """Indicator: Break of Structure (BOS)"""
    # Validate Arguments
    swing_length = int(swing_length) if swing_length and swing_length > 0 else 5
    high = verify_series(high, swing_length)
    low = verify_series(low, swing_length)
    close = verify_series(close, swing_length)
    offset = get_offset(offset)

    if high is None or low is None or close is None: return

    # Compute swing highs/lows (local extremes over centered window)
    swing_high = (high == high.rolling(swing_length, center=True).max()).astype(int)
    swing_low = (low == low.rolling(swing_length, center=True).min()).astype(int)

    n = len(close)
    bos_bull = np.zeros(n)
    bos_bear = np.zeros(n)
    higher_high = np.zeros(n)
    lower_low = np.zeros(n)

    last_swing_high = np.nan
    last_swing_low = np.nan

    for i in range(n):
        if swing_high.iloc[i] == 1:
            if not np.isnan(last_swing_high) and high.iloc[i] > last_swing_high:
                higher_high[i] = 1
            last_swing_high = high.iloc[i]

        if swing_low.iloc[i] == 1:
            if not np.isnan(last_swing_low) and low.iloc[i] < last_swing_low:
                lower_low[i] = 1
            last_swing_low = low.iloc[i]

        if not np.isnan(last_swing_high) and close.iloc[i] > last_swing_high:
            bos_bull[i] = 1
        if not np.isnan(last_swing_low) and close.iloc[i] < last_swing_low:
            bos_bear[i] = 1

    df = DataFrame({
        "BOS_BULL":    bos_bull,
        "BOS_BEAR":    bos_bear,
        "HIGHER_HIGH": higher_high,
        "LOWER_LOW":   lower_low,
    }, index=close.index)

    df.name = f"BOS_{swing_length}"
    df.category = "trend"

    if offset != 0:
        df = df.shift(offset)

    if "fillna" in kwargs:
        df.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        df.fillna(method=kwargs["fill_method"], inplace=True)

    return df


bos.__doc__ = \
"""Break of Structure (bos)

Identifies when price breaks above the last swing high (bullish BOS) or
below the last swing low (bearish BOS).  Also returns HIGHER_HIGH and
LOWER_LOW signals at swing pivot bars.

Sources:
    AwakenAnalytics custom indicator (indicator_engine.py)
    ICT / Smart Money Concept

Calculation:
    Default Inputs:
        swing_length=5
    swing_high = local high over centered rolling(swing_length)
    swing_low  = local low  over centered rolling(swing_length)
    BOS_BULL = 1 when close > last swing high
    BOS_BEAR = 1 when close < last swing low
    HIGHER_HIGH = 1 at a swing high that exceeds the previous swing high
    LOWER_LOW   = 1 at a swing low  that is below the previous swing low

Args:
    high (pd.Series): Series of 'high's
    low (pd.Series): Series of 'low's
    close (pd.Series): Series of 'close's
    swing_length (int): Centered rolling window for swing detection. Default: 5
    offset (int): Periods to offset. Default: 0

Returns:
    pd.DataFrame: BOS_BULL, BOS_BEAR, HIGHER_HIGH, LOWER_LOW
"""
