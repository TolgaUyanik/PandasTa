# -*- coding: utf-8 -*-
"""MESA Sine Wave -- Lead Sine, fixed-period DFT form.

Published source: John Ehlers, "MESA Sine Wave Indicator", Technical Analysis
of Stocks & Commodities (April 1996); reprinted as "The Sinewave Indicator",
Rocket Science for Traders (Wiley, 2001), ch. 11. Catalog attribution (issue
#145): Tulip Indicators `msw.c` (LGPL-3.0), which implements the SAME
published algorithm -- `sin(phase + pi/4)` for the lead line -- and is cited
here only as the catalog's pointer to the algorithm, never as the code this
module is written from. Nothing here is copied from `msw.c`; see the
docstring below for the published pseudocode this is ported from, line by
line against this module's code.
"""
import numpy as np
from pandas import Series
from pandas_ta.utils import get_offset, verify_series


def msw_lead(close, length=None, offset=None, **kwargs):
    """Indicator: MESA Lead Sine (MSW_LEAD)"""
    # Validate Arguments
    length = int(length) if length and length > 1 else 20
    close = verify_series(close, length)
    offset = get_offset(offset)

    if close is None: return

    # Calculate Result
    # Ehlers' `Count` runs 0 (the current/newest bar) to Period - 1 (the
    # oldest bar in the window); a rolling window's array is oldest-first,
    # so `k` is built reversed to put k=0 on the window's LAST position.
    k = np.arange(length)[::-1]
    cos_wave = np.cos(2 * np.pi * k / length)
    sin_wave = np.sin(2 * np.pi * k / length)

    real = close.rolling(length).apply(lambda y: np.dot(y, cos_wave), raw=True)
    imag = close.rolling(length).apply(lambda y: np.dot(y, sin_wave), raw=True)

    # Ehlers' guard is |RealPart| > 0.001 in raw price units, which is not
    # scale-free (it flips sign under a price rescale once |RealPart| crosses
    # the unscaled 0.001 line). This port scales the guard with price instead.
    eps = 0.001 * close
    with np.errstate(divide="ignore", invalid="ignore"):
        phase = np.where(real.abs() > eps, np.arctan(imag / real), (np.pi / 2) * np.sign(imag))
    phase = phase + np.where(real < 0, np.pi, 0.0) + np.pi / 2
    phase = np.mod(phase, 2 * np.pi)

    lead = Series(np.sin(phase + np.pi / 4), index=close.index)

    # Offset
    if offset != 0:
        lead = lead.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        lead.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        lead.fillna(method=kwargs["fill_method"], inplace=True)

    # Name and Categorize it
    lead.name = f"MSW_LEAD_{length}"
    lead.category = "cycles"

    return lead


msw_lead.__doc__ = \
"""MESA Lead Sine, fixed-period DFT form (MSW_LEAD)

The lead line of Ehlers' MESA Sine Wave indicator: the phase of the
period-`length` discrete Fourier term of `close`, read as a sine 45 degrees
(pi/4 rad) ahead of the in-phase sine. Ehlers' reading is that the lead
crosses the (unshipped here) sine line ahead of a cyclic turn.

Sources:
    John Ehlers, "MESA Sine Wave Indicator", Stocks & Commodities (Apr 1996)
    John Ehlers, Rocket Science for Traders (Wiley, 2001), ch. 11
    Catalog attribution only: Tulip Indicators `msw.c` (LGPL-3.0)

Calculation:
    Default Inputs:
        length=20

    k = length-1, length-2, ..., 0           (k = bars back; 0 = current bar)
    RealPart = Sum(close * cos(2*pi*k/length))   over the trailing window
    ImagPart = Sum(close * sin(2*pi*k/length))   over the trailing window

    Phase = atan(ImagPart / RealPart)   if |RealPart| > 0.001 * close
          = (pi/2) * sign(ImagPart)     otherwise
    Phase = Phase + pi/2 + (pi if RealPart < 0 else 0), wrapped to [0, 2*pi)

    MSW_LEAD = sin(Phase + pi/4)

The 0.001 * close guard is this port's scale-free form of Ehlers' published
`|RealPart| > 0.001` (a raw-price-unit constant): it keeps the guard's
crossing point proportional to price so a price rescale cannot flip which
branch a bar takes. See docs/MswLeadMeasured.md.

Args:
    close (pd.Series): Series of 'close's
    length (int): DFT period. Default: 20
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.Series: MSW_LEAD_<length>. A sine of an angle, so bounded in [-1, 1]
        and scale-free -- an ML feature as shipped.
"""
