# -*- coding: utf-8 -*-
from pandas_ta.overlap import sma
from pandas_ta.utils import get_offset, verify_series


def dpo(close, length=None, centered=False, offset=None, **kwargs):
    """Indicator: Detrend Price Oscillator (DPO)"""
    # Validate Arguments
    length = int(length) if length and length > 0 else 20
    close = verify_series(close, length)
    offset = get_offset(offset)

    if close is None: return

    # Calculate Result
    t = int(0.5 * length) + 1
    ma = sma(close, length)

    dpo = close - ma.shift(t)
    if centered:
        dpo = (close.shift(t) - ma).shift(-t)

    # Offset
    if offset != 0:
        dpo = dpo.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        dpo.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        dpo.fillna(method=kwargs["fill_method"], inplace=True)

    # Name and Categorize it
    dpo.name = f"DPO_{length}"
    dpo.category = "trend"

    return dpo


dpo.__doc__ = \
"""Detrend Price Oscillator (DPO)

Is an indicator designed to remove trend from price and make it easier to
identify cycles.

Sources:
    https://www.tradingview.com/scripts/detrendedpriceoscillator/
    https://www.fidelity.com/learning-center/trading-investing/technical-analysis/technical-indicator-guide/dpo
    http://stockcharts.com/school/doku.php?id=chart_school:technical_indicators:detrended_price_osci

Calculation:
    Default Inputs:
        length=20, centered=False
    SMA = Simple Moving Average
    t = int(0.5 * length) + 1

    DPO = close - SMA(close, length).shift(t)
    if centered:
        DPO = (close.shift(t) - SMA(close, length)).shift(-t)

Causality:
    centered=False (the default) is causal: bar T reads only bars <= T.
    centered=True compares close[T] with the SMA ending at T + t, so it
    reads t bars of the FUTURE and its last t values are NaN. It is the
    classic chart form; never feed it to a model. Upstream pandas-ta
    defaults to centered=True -- this fork flipped it (PandasTa issue #5).

Args:
    close (pd.Series): Series of 'close's
    length (int): It's period. Default: 1
    centered (bool): Shift the dpo back by int(0.5 * length) + 1. Reads
        the future. Default: False
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.Series: New feature generated.
"""
