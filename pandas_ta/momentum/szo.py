# -*- coding: utf-8 -*-
"""Sentiment Zone Oscillator (SZO).

PINEBI-1b port of ``szo`` from TradingView's ``ta`` library, publication
``RA2vGpkA``, lines 715-718.

    Mozilla Public License 2.0
    (c) TradingView

Gate A oracle, transcribed from the source::

    export szo(series float source, simple int length) =>
        float trend   = math.sign(ta.change(source))
        float sentPos = tema(trend, length)
        float result  = 100 * sentPos / length

    export tema(series float source, simple int length) =>
        float ema1   = ta.ema(source,  length)
        float ema2   = ta.ema(ema1, length)
        float ema3   = ta.ema(ema2, length)
        float result = 3 * (ema1 - ema2) + ema3

TWO THINGS THE TRANSCRIPTION MUST NOT "CORRECT":

* The division is by **`length`**, not by anything derived from the TEMA.
  `tema(sign(...))` is already bounded to roughly [-1, 1], so dividing by
  `length` and multiplying by 100 gives a range of about
  ``[-100/length, +100/length]`` -- NOT [-100, 100].  At the default 14 that
  is about [-7.1, 7.1].  It looks like a bug and it is what the source does;
  the scale is part of the indicator's identity and a mined rule would match
  on its thresholds, so it is reproduced exactly.
* Pine's `tema` here is applied to a SIGN series, not to price.  The triple
  EMA of a bounded series stays bounded, which is why the output is scale-free
  even though `tema` normally is not.
"""
from numpy import sign
from pandas_ta.overlap.ema import ema
from pandas_ta.utils import get_offset, verify_series


def szo(close, length=None, offset=None, **kwargs):
    """Indicator: Sentiment Zone Oscillator (SZO)"""
    # Validate Arguments
    length = int(length) if length and length > 0 else 14
    close = verify_series(close, 3 * length)
    offset = get_offset(offset)

    if close is None: return

    # Calculate Result
    trend = sign(close.diff())
    ema1 = ema(trend, length=length)
    if ema1 is None: return
    ema2 = ema(ema1, length=length)
    if ema2 is None: return
    ema3 = ema(ema2, length=length)
    if ema3 is None: return
    sent_pos = 3.0 * (ema1 - ema2) + ema3
    szo = 100.0 * sent_pos / length

    # Offset
    if offset != 0:
        szo = szo.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        szo.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        szo.fillna(method=kwargs["fill_method"], inplace=True)

    # Name and Categorize it
    szo.name = f"SZO_{length}"
    szo.category = "momentum"

    return szo


szo.__doc__ = """Sentiment Zone Oscillator (SZO)

A triple-EMA of the bar-direction sign, rescaled by `100 / length`.  It reads
persistence of direction rather than size of move: a run of up bars drives it
up regardless of how large those bars were.

Scale-free by construction -- the input is `sign(change(close))`, which is
already in {-1, 0, +1} before any smoothing, so no price unit survives into
the output.

Range is about `[-100/length, +100/length]`, NOT [-100, 100]; see the module
docstring for why that is the source's behaviour and not a transcription slip.

Sources:
    https://www.tradingview.com/script/RA2vGpkA/ (MPL-2.0, (c) TradingView)

Calculation:
    Default Inputs:
        length=14

    trend = sign(change(close))
    ema1, ema2, ema3 = ema(trend), ema(ema1), ema(ema2)   # all at `length`
    SZO = 100 * (3 * (ema1 - ema2) + ema3) / length

Args:
    close (pd.Series): Series of 'close's
    length (int): The smoothing period. Default: 14
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.Series: New feature generated.
"""
