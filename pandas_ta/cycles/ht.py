# -*- coding: utf-8 -*-
"""Hilbert Transform, the 4-tap FIR quadrature filter (HT).

PINEBI-1b port of ``ht`` from TradingView's ``ta`` library, publication
``RA2vGpkA``, lines 246-247.

    Mozilla Public License 2.0
    (c) TradingView

Gate A oracle, transcribed from the source::

    export ht(series float source) =>
        float result = 0.0962 * source + 0.5769 * nz(source[2]) - 0.5769 * nz(source[4]) - 0.0962 * nz(source[6])

NOT THE SAME THING AS THIS FORK'S `ht_*` FUNCTIONS.  TALIB-1 shipped
`ht_dcperiod`, `ht_dcphase`, `ht_phasor`, `ht_sine`, `ht_trendline` and
`ht_trendmode`, which are TA-Lib's Hilbert STATE MACHINE (`_hilbert.py`, two
warm-ups, lookback 32/63).  This is the bare quadrature FIR those read from --
one line, four taps, no state -- and it is the raw building block rather than
a read-out of it.  They coexist without a name collision because Pine's export
is the unsuffixed `ht`.

THE SCALE PROBLEM, AND WHY THE DEFAULT OUTPUT IS A RATIO
---------------------------------------------------------
The taps sum to ``0.0962 + 0.5769 - 0.5769 - 0.0962 = 0`` exactly, so the
filter has zero DC gain: a constant input gives zero out, and the output is in
price units but with the price LEVEL removed.  That makes it a price
*difference*, which still scales with price -- doubling every price doubles the
output.  A difference is not a feature for the same reason a level is not.

So the shipped column normalises by the source, giving a dimensionless
quadrature reading, and ``raw=True`` returns the unnormalised filter for
anyone building a state machine on top of it.  Same convention TALIB-1 set for
its own price-level outputs.

Pine's `nz()` maps the missing warm-up taps to 0, which would make the first
six bars a partial filter rather than no reading.  Those bars are NaN here
instead: a partially-summed FIR is not the indicator.
"""
from pandas_ta.utils import get_offset, verify_series


def ht(close, offset=None, **kwargs):
    """Indicator: Hilbert Transform 4-tap FIR (HT)"""
    # Validate Arguments
    close = verify_series(close, 7)
    offset = get_offset(offset)

    if close is None: return

    # Calculate Result -- taps in the source's order.
    quad = (0.0962 * close
            + 0.5769 * close.shift(2)
            - 0.5769 * close.shift(4)
            - 0.0962 * close.shift(6))

    raw = kwargs.pop("raw", False)
    if raw:
        ht = quad
        name = "HT"
    else:
        # Dimensionless: the filter output as a fraction of the level it was
        # measured on. `close` is never 0 on real price data; guard anyway.
        ht = 100.0 * quad / close.where(close != 0)
        name = "HT_PCT"

    # Offset
    if offset != 0:
        ht = ht.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        ht.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        ht.fillna(method=kwargs["fill_method"], inplace=True)

    # Name and Categorize it
    ht.name = name
    ht.category = "cycles"

    return ht


ht.__doc__ = """Hilbert Transform, 4-tap FIR (HT)

The quadrature filter underneath the Hilbert-transform family: a 4-tap FIR
that shifts the input by roughly 90 degrees, used to build the in-phase /
quadrature pair a cycle-period estimator needs.

⚠ This is NOT one of this fork's `ht_dcperiod` / `ht_dcphase` / `ht_phasor` /
`ht_sine` / `ht_trendline` / `ht_trendmode` columns. Those are TA-Lib's
Hilbert STATE MACHINE and its read-outs; this is the bare filter.

DEFAULT OUTPUT IS DIMENSIONLESS (percent of the source). The taps sum to zero,
so the raw filter removes the price level but still scales with price — a
difference, not a feature. Pass `raw=True` for the unnormalised filter.

Sources:
    https://www.tradingview.com/script/RA2vGpkA/ (MPL-2.0, (c) TradingView)

Calculation:
    quad   = 0.0962*src + 0.5769*src[2] - 0.5769*src[4] - 0.0962*src[6]
    HT_PCT = 100 * quad / src      # default, scale-free
    HT     = quad                  # raw=True, a price difference

Args:
    close (pd.Series): Series of 'close's
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    raw (bool): Return the unnormalised filter. Default: False
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.Series: New feature generated.
"""
