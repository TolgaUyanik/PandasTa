# -*- coding: utf-8 -*-
import numpy as np
from pandas import DataFrame
from pandas_ta.utils import get_offset, verify_series


def ob(open_, high, low, close, max_zones=None, offset=None, **kwargs):
    """Indicator: Order Blocks (OB)"""
    # Validate Arguments
    max_zones = int(max_zones) if max_zones and max_zones > 0 else 20
    open_ = verify_series(open_, 2)
    high = verify_series(high, 2)
    low = verify_series(low, 2)
    close = verify_series(close, 2)
    offset = get_offset(offset)

    if open_ is None or high is None or low is None or close is None: return

    n = len(close)
    ob_bull = np.zeros(n)
    ob_bear = np.zeros(n)
    bull_zones = []  # (zone_low, zone_high)
    bear_zones = []

    for i in range(1, n):
        # Bullish OB: prior bar bearish AND current bar impulse-closes above prior high
        if (close.iloc[i - 1] < open_.iloc[i - 1]
                and close.iloc[i] > high.iloc[i - 1]):
            bull_zones.append((low.iloc[i - 1], high.iloc[i - 1]))

        # Bearish OB: prior bar bullish AND current bar impulse-closes below prior low
        if (close.iloc[i - 1] > open_.iloc[i - 1]
                and close.iloc[i] < low.iloc[i - 1]):
            bear_zones.append((low.iloc[i - 1], high.iloc[i - 1]))

        c = close.iloc[i]

        active_bull = []
        for (zl, zh) in bull_zones:
            if zl <= c <= zh:
                ob_bull[i] = 1
            if c >= zl:  # zone not yet mitigated (close above OB low)
                active_bull.append((zl, zh))
        bull_zones = active_bull[-max_zones:]

        active_bear = []
        for (zl, zh) in bear_zones:
            if zl <= c <= zh:
                ob_bear[i] = 1
            if c <= zh:  # zone not yet mitigated (close below OB high)
                active_bear.append((zl, zh))
        bear_zones = active_bear[-max_zones:]

    df = DataFrame({
        "OB_BULL": ob_bull,
        "OB_BEAR": ob_bear,
    }, index=close.index)

    df.name = "OB"
    df.category = "trend"

    if offset != 0:
        df = df.shift(offset)

    if "fillna" in kwargs:
        df.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        df.fillna(method=kwargs["fill_method"], inplace=True)

    return df


ob.__doc__ = \
"""Order Blocks (ob)

Identifies institutional order block zones and flags when the current
bar's close is inside an active (unmitigated) order block zone.

Sources:
    AwakenAnalytics custom indicator (indicator_engine.py)
    ICT (Inner Circle Trader) concept

Calculation:
    Bullish OB formed when: prior bar is bearish AND close[i] > high[i-1]
    Bearish OB formed when: prior bar is bullish AND close[i] < low[i-1]
    OB_BULL = 1 when close is inside an active bullish OB zone
    OB_BEAR = 1 when close is inside an active bearish OB zone
    Zones expire when price closes beyond the far side of the zone.

Args:
    open_ (pd.Series): Series of 'open's
    high (pd.Series): Series of 'high's
    low (pd.Series): Series of 'low's
    close (pd.Series): Series of 'close's
    max_zones (int): Maximum active zones to track. Default: 20
    offset (int): Periods to offset. Default: 0

Returns:
    pd.DataFrame: OB_BULL, OB_BEAR
"""
