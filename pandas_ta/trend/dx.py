# -*- coding: utf-8 -*-
from pandas_ta.trend.adx import adx
from pandas_ta.utils import get_offset, verify_series


def dx(high, low, close, length=None, scalar=None, mamode=None, drift=None, offset=None, **kwargs):
    """Indicator: Directional Movement Index (DX)"""
    # Validate Arguments
    length = int(length) if length and length > 0 else 14
    high = verify_series(high, length)
    low = verify_series(low, length)
    close = verify_series(close, length)
    offset = get_offset(offset)

    if high is None or low is None or close is None: return

    # Calculate Result
    adx_df = adx(high=high, low=low, close=close, length=length,
                 scalar=scalar, mamode=mamode, drift=drift)
    if adx_df is None: return

    scalar = float(scalar) if scalar else 100
    dmp = adx_df[f"DMP_{length}"]
    dmn = adx_df[f"DMN_{length}"]
    dx = scalar * (dmp - dmn).abs() / (dmp + dmn)

    # Offset
    if offset != 0:
        dx = dx.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        dx.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        dx.fillna(method=kwargs["fill_method"], inplace=True)

    # Name and Categorize it
    dx.name = f"DX_{length}"
    dx.category = "trend"

    return dx


dx.__doc__ = \
"""Directional Movement Index (DX)

DX is the unsmoothed directional movement index: Wilder's +DI and -DI
collapsed to a single 0-100 reading of how lopsided the two are, one bar at
a time. ADX is DX run back through another pass of the same moving average;
DX itself skips that second smoothing.

Source: jesse (MIT), `dx.py`:
    dx = 100 * |DI+ - DI-| / (DI+ + DI-)

+DI and -DI are this fork's own `adx()` (Wilder's RMA smoothing, scalar 100),
not re-derived: `adx()` already computes `DMP_<length>`/`DMN_<length>` from
the same `pos`/`neg`/`atr_` terms jesse's `dm_wilder()` calls +DI/-DI, so DX
is read off `adx()`'s own frame rather than duplicating that derivation
(same reuse this fork already uses for `adxr()`). `adx()`'s own correctness
is upstream and out of scope for this port.

Calculation:
    Default Inputs:
        length=14, mamode="rma", drift=1, scalar=100
    DMP, DMN = this fork's adx(length, mamode, drift)["DMP_<length>", "DMN_<length>"]

    DX = scalar * |DMP - DMN| / (DMP + DMN)

Args:
    high (pd.Series): Series of 'high's
    low (pd.Series): Series of 'low's
    close (pd.Series): Series of 'close's
    length (int): It's period. Default: 14
    scalar (float): How much to magnify. Default: 100
    mamode (str): adx()'s moving average mode. Default: 'rma'
    drift (int): The difference period. Default: 1
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.Series: New feature generated, in [0, 100].
"""
