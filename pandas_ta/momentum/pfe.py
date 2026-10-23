# -*- coding: utf-8 -*-
from numpy import log, sign, sqrt
from pandas_ta.overlap.ema import ema
from pandas_ta.utils import get_offset, verify_series


def pfe(close, length=None, smooth=None, offset=None, **kwargs):
    """Indicator: Polarized Fractal Efficiency (PFE), log-percent form"""
    # Validate arguments
    length = int(length) if length and length > 0 else 10
    smooth = int(smooth) if smooth and smooth > 0 else 5
    close = verify_series(close, max(length, smooth) + 1)
    offset = get_offset(offset)

    if close is None: return

    # Calculate Result: each bar is one unit across and 100*log-return up/down.
    # A ratio, not a difference, so x8 rescaling is bit-identical.
    step = 100 * log(close / close.shift(1))
    # Not step.rolling().sum(): on tick-rounded prices an exactly-flat net sums to +-1e-16 and sign() flips it to +-100.
    net = 100 * log(close / close.shift(length))
    path = sqrt(step * step + 1).rolling(length).sum()
    pfe = 100 * sign(net) * sqrt(net * net + length * length) / path

    if smooth > 1:
        pfe = ema(pfe, length=smooth, sma=False)

    # Offset
    if offset != 0:
        pfe = pfe.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        pfe.fillna(kwargs["fillna"], inplace=True)

    # Name and Categorize it
    pfe.name = f"PFE_{length}_{smooth}"
    pfe.category = "momentum"

    return pfe


pfe.__doc__ = \
"""Polarized Fractal Efficiency (PFE)

Hans Hannula's PFE (Technical Analysis of Stocks & Commodities, Jan 1994):
the straight-line distance between the first and last bar of a window over
the length of the bar-to-bar path, both measured on a chart where one bar is
one unit across, signed by the net move, then EMA-smoothed. +100 is a
straight rally, -100 a straight decline.

Departure from Hannula: he measures the vertical leg in raw price, which
adds price units to bar counts, so the value changes when prices are
rescaled. Here the vertical leg is 100 * log-return (about one unit per 1%
move), which is scale-free. Unlike the raw form it is still volatility-
dependent by design: on bars that move far less than 1%, sqrt(net^2 + n^2)
and the path both approach n, so |PFE| approaches 100 whatever the trend.
See docs/PfeMeasured.md.

Hannula's published code is recalled, not cited, as ten bars, nine segments
and a horizontal leg of 10 (sqrt(dC^2 + 100)); this uses `length` segments and a horizontal leg of
`length`, so a straight line reads exactly 100.

Calculation:
    Default Inputs:
        length=10, smooth=5
    EMA = Exponential Moving Average (no SMA seed)

    step = 100 * LN(close / close[1])
    net = 100 * LN(close / close[length])     (== SUM(step, length) exactly in exact arithmetic)
    path = SUM(SQRT(step^2 + 1), length)
    raw = 100 * SIGN(net) * SQRT(net^2 + length^2) / path
    PFE = EMA(raw, smooth) if smooth > 1 else raw

Args:
    close (pd.Series): Series of 'close's
    length (int): Number of bar-to-bar segments. Default: 10
    smooth (int): EMA period; 1 disables smoothing. Default: 5
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)

Returns:
    pd.Series: New feature generated, in [-100, 100] up to rounding.
"""
