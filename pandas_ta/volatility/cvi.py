# -*- coding: utf-8 -*-
"""Chaikin's Volatility (CVI).

ALTPORT-2 port of ``pandas_ta_classic.volatility.cvi`` from
https://github.com/xgboosted/pandas-ta-classic (MIT License, Copyright (c)
pandas-ta-classic contributors).  The upstream repository is NOT vendored here;
only the algorithm is reimplemented against this fork's helpers.

Gate A oracle: ``pandas_ta_classic.cvi(high, low, length)``.
"""
from pandas_ta.overlap.ema import ema
from pandas_ta.utils import get_offset, verify_series


def cvi(high, low, length=None, roc_length=None, offset=None, **kwargs):
    """Indicator: Chaikin's Volatility (CVI)"""
    # Validate Arguments
    length = int(length) if length and length > 0 else 10
    roc_length = int(roc_length) if roc_length and roc_length > 0 else length
    _length = length + roc_length
    high = verify_series(high, _length)
    low = verify_series(low, _length)
    offset = get_offset(offset)

    if high is None or low is None: return

    # Calculate Result
    hl = high - low
    ema_hl = ema(hl, length=length, **kwargs)
    if ema_hl is None: return
    prior = ema_hl.shift(roc_length)
    cvi = 100 * (ema_hl - prior) / prior

    # Offset
    if offset != 0:
        cvi = cvi.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        cvi.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        cvi.fillna(method=kwargs["fill_method"], inplace=True)

    # Name and Categorize it
    cvi.name = f"CVI_{length}_{roc_length}"
    cvi.category = "volatility"

    return cvi


cvi.__doc__ = \
"""Chaikin's Volatility (CVI)

The rate of change of a smoothed High-Low range.  Where `natr` reports the
LEVEL of volatility and `chop` reports trending-versus-ranging, CVI reports
whether the trading range is EXPANDING or CONTRACTING, and by what percentage
over the last `roc_length` bars.  Nothing else in this package is a rate of
change of range (ALTPORT-1 verified no such column exists among the 492 the
production engine config emits).

Scale-free by construction: a ratio of two range EMAs.  Gate D measured
bit-identical (max |delta| == 0.0) under close/high/low/open x8 and x64.

Gate E (ALTPORT-1, 89 BIST daily frames, 408,253 bars): max |Spearman rho|
**0.501290** against `CHOP`, n = 405,514; per-frame median 0.499606, 0.0% of
frames >= 0.90.  SHIP.

Sources:
    Marc Chaikin.
    https://school.stockcharts.com/doku.php?id=technical_indicators:chaikins_volatility
    Ported from pandas-ta-classic (MIT), `pandas_ta_classic/volatility/cvi.py`.

Calculation:
    Default Inputs:
        length=10, roc_length=length
    EMA = Exponential Moving Average (SMA-seeded, as upstream)
    HL = high - low
    EMA_HL = EMA(HL, length)
    CVI = 100 * (EMA_HL - EMA_HL[roc_length]) / EMA_HL[roc_length]

    Upstream exposes ONE `length` used for both the EMA and the lookback.
    This port splits them, defaulting `roc_length` to `length`, so the default
    call reproduces upstream exactly (Gate A: max |diff| 0.0 over 51,866 bars).

Args:
    high (pd.Series): Series of 'high's
    low (pd.Series): Series of 'low's
    length (int): The EMA period. Default: 10
    roc_length (int): The rate-of-change lookback. Default: `length`
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.Series: New feature generated.
"""
