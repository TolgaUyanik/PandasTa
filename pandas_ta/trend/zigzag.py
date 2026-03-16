# -*- coding: utf-8 -*-
import numpy as np
from pandas import Series
from pandas_ta.utils import get_offset, verify_series


def zigzag(close, pct_threshold=None, offset=None, **kwargs):
    """Indicator: ZigZag"""
    # Validate Arguments
    pct_threshold = float(pct_threshold) if pct_threshold and pct_threshold > 0 else 0.05
    close = verify_series(close, 2)
    offset = get_offset(offset)

    if close is None: return

    # Calculate Result
    n = len(close)
    zigzag_arr = np.full(n, np.nan)
    direction = 0  # 1=up, -1=down
    last_pivot = close.iloc[0]
    last_pivot_idx = 0

    for i in range(1, n):
        price = close.iloc[i]
        change = (price - last_pivot) / last_pivot if last_pivot != 0 else 0

        if direction >= 0 and change < -pct_threshold:
            zigzag_arr[last_pivot_idx] = last_pivot
            direction = -1
            last_pivot = price
            last_pivot_idx = i
        elif direction <= 0 and change > pct_threshold:
            zigzag_arr[last_pivot_idx] = last_pivot
            direction = 1
            last_pivot = price
            last_pivot_idx = i
        elif direction == 1 and price > last_pivot:
            last_pivot = price
            last_pivot_idx = i
        elif direction == -1 and price < last_pivot:
            last_pivot = price
            last_pivot_idx = i

    result = Series(zigzag_arr, index=close.index)

    if offset != 0:
        result = result.shift(offset)

    if "fillna" in kwargs:
        result.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        result.fillna(method=kwargs["fill_method"], inplace=True)

    result.name = f"ZIGZAG_{int(pct_threshold * 100)}"
    result.category = "trend"

    return result


zigzag.__doc__ = \
"""ZigZag (zigzag)

Marks pivot highs and lows where the price has reversed by at least
`pct_threshold` from the last pivot.  Non-pivot bars are NaN.

Sources:
    AwakenAnalytics custom indicator (indicator_engine.py)

Calculation:
    Default Inputs:
        pct_threshold=0.05 (5%)
    Track last pivot price and direction.
    Flip direction when abs(change from last pivot) > pct_threshold.

Args:
    close (pd.Series): Series of 'close's
    pct_threshold (float): Minimum reversal size. Default: 0.05 (5%)
    offset (int): Periods to offset. Default: 0

Returns:
    pd.Series: Pivot price at reversal bars, NaN elsewhere
"""
