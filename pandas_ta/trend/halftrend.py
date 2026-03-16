# -*- coding: utf-8 -*-
import numpy as np
from pandas import DataFrame
from pandas_ta.utils import get_offset, verify_series


def halftrend(high, low, close, atr_period=None, amplitude=None, offset=None, **kwargs):
    """Indicator: HalfTrend"""
    # Validate Arguments
    atr_period = int(atr_period) if atr_period and atr_period > 0 else 14
    amplitude = float(amplitude) if amplitude and amplitude > 0 else 2.0
    high = verify_series(high, atr_period)
    low = verify_series(low, atr_period)
    close = verify_series(close, atr_period)
    offset = get_offset(offset)

    if high is None or low is None or close is None: return

    # Calculate Result
    atr = high.rolling(atr_period).max() - low.rolling(atr_period).min()
    dev = amplitude * atr / 2

    high_ma = high.rolling(2).max()
    low_ma = low.rolling(2).min()

    n = len(close)
    halftrend_arr = np.full(n, np.nan)
    halftrend_dir = np.zeros(n)
    up = np.full(n, np.nan)
    down = np.full(n, np.nan)
    trend = 0  # 0=up, 1=down

    for i in range(atr_period, n):
        if i == atr_period:
            up[i] = low_ma.iloc[i]
            down[i] = high_ma.iloc[i]
            halftrend_arr[i] = up[i]
            halftrend_dir[i] = 1
            continue

        prev_up = up[i - 1] if not np.isnan(up[i - 1]) else low_ma.iloc[i]
        prev_down = down[i - 1] if not np.isnan(down[i - 1]) else high_ma.iloc[i]

        if trend == 0:
            up[i] = max(prev_up, low_ma.iloc[i])
            if close.iloc[i] < up[i] - dev.iloc[i]:
                trend = 1
                down[i] = high_ma.iloc[i]
                halftrend_arr[i] = down[i]
                halftrend_dir[i] = -1
            else:
                halftrend_arr[i] = up[i]
                halftrend_dir[i] = 1
        else:
            down[i] = min(prev_down, high_ma.iloc[i])
            if close.iloc[i] > down[i] + dev.iloc[i]:
                trend = 0
                up[i] = low_ma.iloc[i]
                halftrend_arr[i] = up[i]
                halftrend_dir[i] = 1
            else:
                halftrend_arr[i] = down[i]
                halftrend_dir[i] = -1

    df = DataFrame({
        "HALFTREND":     halftrend_arr,
        "HALFTREND_DIR": halftrend_dir,
    }, index=close.index)

    df.name = f"HALFTREND_{atr_period}_{amplitude}"
    df.category = "trend"

    if offset != 0:
        df = df.shift(offset)

    if "fillna" in kwargs:
        df.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        df.fillna(method=kwargs["fill_method"], inplace=True)

    return df


halftrend.__doc__ = \
"""HalfTrend (halftrend)

An ATR-based trend-following indicator that alternates between an
uptrend line (support) and a downtrend line (resistance).
HALFTREND_DIR is +1 in uptrend and -1 in downtrend.

Sources:
    AwakenAnalytics custom indicator (indicator_engine.py)
    Original concept: halftrend by Alex Orekhov (everget) on TradingView

Calculation:
    Default Inputs:
        atr_period=14, amplitude=2
    dev = amplitude * (rolling_high(2) - rolling_low(2)) / 2
    Switches from uptrend to downtrend when close < up_line - dev
    Switches from downtrend to uptrend when close > down_line + dev

Args:
    high (pd.Series): Series of 'high's
    low (pd.Series): Series of 'low's
    close (pd.Series): Series of 'close's
    atr_period (int): ATR window. Default: 14
    amplitude (float): Deviation multiplier. Default: 2.0
    offset (int): Periods to offset. Default: 0

Returns:
    pd.DataFrame: HALFTREND (price level), HALFTREND_DIR (+1/-1)
"""
