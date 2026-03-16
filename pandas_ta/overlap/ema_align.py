# -*- coding: utf-8 -*-
from pandas import DataFrame
from pandas_ta.utils import get_offset, verify_series


def ema_align(close, offset=None, **kwargs):
    """Indicator: EMA Stack Alignment"""
    # Validate Arguments
    close = verify_series(close, 200)
    offset = get_offset(offset)

    if close is None: return

    # Calculate Result — EMA stack (9, 21, 50, 100, 200)
    periods = [9, 21, 50, 100, 200]
    emas = {p: close.ewm(span=p, adjust=False).mean() for p in periods}

    bull = (
        (emas[9]   > emas[21] ).astype(int) +
        (emas[21]  > emas[50] ).astype(int) +
        (emas[50]  > emas[100]).astype(int) +
        (emas[100] > emas[200]).astype(int)
    )
    bear = (
        (emas[9]   < emas[21] ).astype(int) +
        (emas[21]  < emas[50] ).astype(int) +
        (emas[50]  < emas[100]).astype(int) +
        (emas[100] < emas[200]).astype(int)
    )

    df = DataFrame({
        "EMA_ALIGN_BULL": bull,
        "EMA_ALIGN_BEAR": bear,
    }, index=close.index)

    df.name = "EMA_ALIGN"
    df.category = "overlap"

    if offset != 0:
        df = df.shift(offset)

    if "fillna" in kwargs:
        df.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        df.fillna(method=kwargs["fill_method"], inplace=True)

    return df


ema_align.__doc__ = \
"""EMA Stack Alignment (ema_align)

Counts how many of the EMA(9), EMA(21), EMA(50), EMA(100), EMA(200)
relationships are aligned bullishly or bearishly.  The result is an
integer 0-4 for each direction.

Sources:
    AwakenAnalytics custom indicator (indicator_engine.py)

Calculation:
    EMA_ALIGN_BULL = (EMA9 > EMA21) + (EMA21 > EMA50)
                   + (EMA50 > EMA100) + (EMA100 > EMA200)
    EMA_ALIGN_BEAR = (EMA9 < EMA21) + (EMA21 < EMA50)
                   + (EMA50 < EMA100) + (EMA100 < EMA200)

Args:
    close (pd.Series): Series of 'close's
    offset (int): Periods to offset the result. Default: 0

Returns:
    pd.DataFrame: EMA_ALIGN_BULL (0-4), EMA_ALIGN_BEAR (0-4)
"""
