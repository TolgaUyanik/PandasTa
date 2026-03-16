# -*- coding: utf-8 -*-
import numpy as np
from pandas import DataFrame
from pandas_ta.utils import get_offset, verify_series


def fvg(high, low, close, max_zones=None, offset=None, **kwargs):
    """Indicator: Fair Value Gap (FVG)"""
    # Validate Arguments
    max_zones = int(max_zones) if max_zones and max_zones > 0 else 10
    high = verify_series(high, 3)
    low = verify_series(low, 3)
    close = verify_series(close, 3)
    offset = get_offset(offset)

    if high is None or low is None or close is None: return

    n = len(close)
    fvg_bull_flag = np.zeros(n)
    fvg_bear_flag = np.zeros(n)
    in_fvg_bull = np.zeros(n)
    in_fvg_bear = np.zeros(n)

    # Spot FVG formations (3-bar pattern)
    for i in range(2, n):
        if low.iloc[i] > high.iloc[i - 2]:
            fvg_bull_flag[i] = 1
        if high.iloc[i] < low.iloc[i - 2]:
            fvg_bear_flag[i] = 1

    bull_zones = []  # (zone_low, zone_high)
    bear_zones = []  # (zone_high, zone_low)

    for i in range(2, n):
        if fvg_bull_flag[i]:
            bull_zones.append((high.iloc[i - 2], low.iloc[i]))
        if fvg_bear_flag[i]:
            bear_zones.append((high.iloc[i], low.iloc[i - 2]))

        c = close.iloc[i]

        active_bull = []
        for (zl, zh) in bull_zones:
            if zl <= c <= zh:
                in_fvg_bull[i] = 1
            if c <= zh:  # zone still open (not fully filled from above)
                active_bull.append((zl, zh))
        bull_zones = active_bull[-max_zones:]

        active_bear = []
        for (zh, zl) in bear_zones:
            if zh <= c <= zl:
                in_fvg_bear[i] = 1
            if c >= zh:  # zone still open (not fully filled from below)
                active_bear.append((zh, zl))
        bear_zones = active_bear[-max_zones:]

    df = DataFrame({
        "FVG_BULL":    fvg_bull_flag,
        "FVG_BEAR":    fvg_bear_flag,
        "IN_FVG_BULL": in_fvg_bull,
        "IN_FVG_BEAR": in_fvg_bear,
    }, index=close.index)

    df.name = "FVG"
    df.category = "trend"

    if offset != 0:
        df = df.shift(offset)

    if "fillna" in kwargs:
        df.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        df.fillna(method=kwargs["fill_method"], inplace=True)

    return df


fvg.__doc__ = \
"""Fair Value Gap (fvg)

Detects 3-bar Fair Value Gaps (imbalances) and tracks whether the
current bar is inside an active (unfilled) FVG zone.

Sources:
    AwakenAnalytics custom indicator (indicator_engine.py)
    ICT (Inner Circle Trader) concept

Calculation:
    FVG_BULL = 1 when low[i] > high[i-2]  (gap up, bullish imbalance)
    FVG_BEAR = 1 when high[i] < low[i-2]  (gap down, bearish imbalance)
    IN_FVG_BULL = 1 when close is inside an active bullish FVG zone
    IN_FVG_BEAR = 1 when close is inside an active bearish FVG zone
    Zones expire when price fully closes through them.

Args:
    high (pd.Series): Series of 'high's
    low (pd.Series): Series of 'low's
    close (pd.Series): Series of 'close's
    max_zones (int): Maximum number of active zones to track. Default: 10
    offset (int): Periods to offset. Default: 0

Returns:
    pd.DataFrame: FVG_BULL, FVG_BEAR, IN_FVG_BULL, IN_FVG_BEAR
"""
