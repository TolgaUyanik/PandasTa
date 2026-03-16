# -*- coding: utf-8 -*-
import numpy as np
from pandas import DataFrame
from pandas_ta.utils import get_offset, verify_series


def choch(high, low, close, swing_length=None, offset=None, **kwargs):
    """Indicator: Change of Character (CHoCH)"""
    # Validate Arguments
    swing_length = int(swing_length) if swing_length and swing_length > 0 else 5
    high = verify_series(high, swing_length)
    low = verify_series(low, swing_length)
    close = verify_series(close, swing_length)
    offset = get_offset(offset)

    if high is None or low is None or close is None: return

    # Compute swing highs/lows and BOS internally
    swing_high = (high == high.rolling(swing_length, center=True).max()).astype(int)
    swing_low = (low == low.rolling(swing_length, center=True).min()).astype(int)

    n = len(close)
    bos_bull = np.zeros(n)
    bos_bear = np.zeros(n)
    last_swing_high = np.nan
    last_swing_low = np.nan

    for i in range(n):
        if swing_high.iloc[i] == 1:
            last_swing_high = high.iloc[i]
        if swing_low.iloc[i] == 1:
            last_swing_low = low.iloc[i]
        if not np.isnan(last_swing_high) and close.iloc[i] > last_swing_high:
            bos_bull[i] = 1
        if not np.isnan(last_swing_low) and close.iloc[i] < last_swing_low:
            bos_bear[i] = 1

    # CHoCH: BOS that reverses the prevailing swing trend
    choch_bull = np.zeros(n)
    choch_bear = np.zeros(n)
    trend = 0  # 0=neutral, 1=uptrend, -1=downtrend
    last_sh = np.nan
    prev_sh = np.nan
    last_sl = np.nan
    prev_sl = np.nan

    for i in range(n):
        if swing_high.iloc[i] == 1:
            prev_sh = last_sh
            last_sh = high.iloc[i]
            if not np.isnan(prev_sh) and last_sh < prev_sh:
                trend = -1  # lower high -> downtrend

        if swing_low.iloc[i] == 1:
            prev_sl = last_sl
            last_sl = low.iloc[i]
            if not np.isnan(prev_sl) and last_sl > prev_sl:
                trend = 1   # higher low -> uptrend

        if bos_bull[i] == 1 and trend == -1:
            choch_bull[i] = 1
            trend = 0   # character changed

        if bos_bear[i] == 1 and trend == 1:
            choch_bear[i] = 1
            trend = 0

    df = DataFrame({
        "CHoCH_BULL": choch_bull,
        "CHoCH_BEAR": choch_bear,
    }, index=close.index)

    df.name = f"CHoCH_{swing_length}"
    df.category = "trend"

    if offset != 0:
        df = df.shift(offset)

    if "fillna" in kwargs:
        df.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        df.fillna(method=kwargs["fill_method"], inplace=True)

    return df


choch.__doc__ = \
"""Change of Character (choch)

A CHoCH occurs when a Break of Structure happens in the direction
opposite to the prevailing swing trend, signalling a potential reversal.

Sources:
    AwakenAnalytics custom indicator (indicator_engine.py)
    ICT / Smart Money Concept

Calculation:
    Default Inputs:
        swing_length=5
    Determine prevailing trend from sequence of swing highs/lows.
    CHoCH_BULL = 1 when BOS_BULL fires during a downtrend (lower highs)
    CHoCH_BEAR = 1 when BOS_BEAR fires during an uptrend  (higher lows)

Args:
    high (pd.Series): Series of 'high's
    low (pd.Series): Series of 'low's
    close (pd.Series): Series of 'close's
    swing_length (int): Centered rolling window for swing detection. Default: 5
    offset (int): Periods to offset. Default: 0

Returns:
    pd.DataFrame: CHoCH_BULL, CHoCH_BEAR
"""
