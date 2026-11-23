# -*- coding: utf-8 -*-
import numpy as np

from pandas_ta.utils import get_offset, verify_series


def wavepm(close, length=None, lookback=None, offset=None, **kwargs):
    """Indicator: Whistler Wave PM (WAVEPM)"""
    # Validate Arguments
    length = int(length) if length and length > 1 else 14
    lookback = int(lookback) if lookback and lookback > 0 else 100
    close = verify_series(close, length + lookback - 1)
    offset = get_offset(offset)

    if close is None: return

    # Calculate Result
    mu = close.rolling(length).mean()
    sigma = close.rolling(length).std(ddof=0)
    r = sigma / mu
    rms = np.sqrt((r * r).rolling(lookback).mean())
    wpm = np.tanh(r / rms)

    # Offset
    if offset != 0:
        wpm = wpm.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        wpm.fillna(kwargs["fillna"], inplace=True)

    # Name and Categorize it
    wpm.name = f"WAVEPM_{length}_{lookback}"
    wpm.category = "volatility"

    return wpm


wavepm.__doc__ = \
"""Whistler Wave PM (WAVEPM)

The 14-bar coefficient of variation of close, over its own root-mean-square
across the last 100 bars, squashed by tanh into [0, 1).

    r[T]   = std(close, length)[T] / sma(close, length)[T]     (ddof = 0)
    rms[T] = sqrt(mean(r[T-lookback+1 .. T] ** 2))
    WAVEPM = tanh(r[T] / rms[T])

Source: Mark Whistler, "Volatility Illuminated" (c. 2016), "Wave PM" (Price
Mass). No text of the book with a formula was readable; the definition is
finta's `WAVEPM` (`finta/finta.py`, LGPL-3.0) as transcribed in PandasTa
issue #261: the standard deviation is divided by the mean, and finta's
constant 3.2, which multiplies both numerator and denominator, cancels and
is left out. The math is ported, not the code. Gate A is OWED: finta's
source was not read and none of its lines are cited here. The ProRealCode port, which
does NOT divide by the mean, is the reading not taken
(`docs/WavepmMeasured.md` §A4).

ddof does not matter: a different ddof rescales every r by the same constant
sqrt(n / (n - ddof)), which cancels in r / rms (§A4 measures the residue).

Causal: bar T reads closes T-length-lookback+2 .. T. Scale-free: r is a
ratio of two price-unit quantities, so any positive rescale cancels.

0.0 exactly when the last `length` closes are one price (r = 0). Since
r <= rms * sqrt(lookback), the column never exceeds tanh(10) at the
defaults, so it stays below 1.

NaN on the first length + lookback - 2 bars; on any bar whose windows hold a
NaN or infinite close (pandas' rolling windows already return NaN there, so
an infinity needs no mask); and on a bar whose rms is 0 (a price flat for
the whole lookback). For negative prices r is negative and the column falls
in (-1, 0].

Calculation:
    Default Inputs:
        length=14, lookback=100
    r      = STDEV(close, length, ddof=0) / SMA(close, length)
    WAVEPM = TANH(r / SQRT(SMA(r * r, lookback)))

Args:
    close (pd.Series): Series of 'close's
    length (int): The coefficient-of-variation window. Default: 14
    lookback (int): The RMS window. Default: 100
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)

Returns:
    pd.Series: WAVEPM_{length}_{lookback}, dimensionless, in [0, 1) for
    positive prices
"""
