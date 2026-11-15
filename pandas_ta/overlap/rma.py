# -*- coding: utf-8 -*-
from pandas_ta.utils import get_offset, verify_series


def rma(close, length=None, offset=None, **kwargs):
    """Indicator: wildeR's Moving Average (RMA)"""
    # Validate Arguments
    length = int(length) if length and length > 0 else 10
    alpha = (1.0 / length) if length > 0 else 0.5
    close = verify_series(close, length)
    offset = get_offset(offset)

    if close is None: return

    # Calculate Result
    rma = close.ewm(alpha=alpha, min_periods=length).mean()

    # Offset
    if offset != 0:
        rma = rma.shift(offset)

    # Name & Category
    rma.name = f"RMA_{length}"
    rma.category = "overlap"

    return rma


rma.__doc__ = \
"""wildeR's Moving Average (RMA)

The WildeR's Moving Average is simply an Exponential Moving Average (EMA) with
a modified alpha = 1 / length.

Not Wilder's smoothing: this is pandas' `ewm(alpha=1/length).mean()` with its
default `adjust=True`, not the recursive SMA-seeded form Pine's `ta.rma` uses,
so its values differ from Pine's (kept for compatibility: changing it would move
`atr` and everything built on `rma`). For true Wilder smoothing use
`wilder_rma`, or `ma("wrma", ...)`.

Sources:
    https://tlc.thinkorswim.com/center/reference/Tech-Indicators/studies-library/V-Z/WildersSmoothing
    https://www.incrediblecharts.com/indicators/wilder_moving_average.php

Calculation:
    Default Inputs:
        length=10
    EMA = Exponential Moving Average
    alpha = 1 / length
    RMA = EMA(close, alpha=alpha)

Args:
    close (pd.Series): Series of 'close's
    length (int): It's period. Default: 10
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.Series: New feature generated.
"""
