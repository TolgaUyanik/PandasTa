# -*- coding: utf-8 -*-
"""`dema2` -- the dynamic-length DEMA of the TradingView `ta` library.

Source: `docs/pine/RA2vGpkA-ta.pine` (untracked; see CLAUDE.md), the
TradingView/`ta` Pine v5 library, **MPL-2.0, (c) TradingView**.
`export dema2` is at L168-171:

    L168 export dema2(series float source, series float length) =>
    L169     float ema1   = ema2(source,  length)
    L170     float ema2   = ema2(ema1, length)
    L171     float result = 2 * ema1 - ema2

(The Pine source shadows the function name `ema2` with a local variable on
L170.  The non-alternate `dema()` at L147-150 is the unambiguous statement
of intent -- two chained EMAs, `2 * ema1 - ema2` -- and that is what this
port computes, with `ema2` in place of `ta.ema`.)

THE DIFFERENCES FROM `dema`, MEASURED (docs/PineAlternatesMeasured.md)

1. WARM-UP.  `dema` stacks two SMA-seeded `ema` calls.  Chaining does NOT
   double the warm-up, and the arithmetic guess that it does was measured
   and found wrong: the inner `ema`'s own SMA seed is `mean(ema1[0:length])`
   over a window holding exactly one finite value, so the second `ema` also
   settles at `length - 1`.  Measured at length=10: first-stable index 9 vs
   0, **9 bars saved**, on GRID_S and on all 40 Grid A tickers.
2. PARAMETER REACH.  `dema` does `int(length)`; `dema2` takes a per-bar
   Series length or a fractional scalar.
"""
from pandas_ta.overlap.ema2 import ema2, _length_array
from pandas_ta.utils import get_offset, verify_series


def dema2(close, length=None, offset=None, **kwargs):
    """Indicator: Dynamic-Length Double Exponential Moving Average (DEMA2)"""
    close = verify_series(close)
    offset = get_offset(offset)
    if close is None: return

    _, token = _length_array(length, close.index, 10)
    e1 = ema2(close=close, length=length)
    e2 = ema2(close=e1, length=length)
    out = 2 * e1 - e2

    if offset != 0:
        out = out.shift(offset)
    if "fillna" in kwargs:
        out.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        out.fillna(method=kwargs["fill_method"], inplace=True)

    out.name = f"DEMA2_{token}"
    out.category = "overlap"
    return out


dema2.__doc__ = \
"""Dynamic-Length Double Exponential Moving Average (DEMA2)

TradingView `ta.dema2()` -- DEMA built on the source-seeded,
per-bar-length `ema2` instead of the SMA-seeded `ema`.  Finite from bar 0
where `dema` needs `length - 1` bars (measured 9 at length=10).

Sources:
    TradingView `ta` library (RA2vGpkA), L168-171. MPL-2.0, (c) TradingView.

Calculation:
    Default Inputs:
        length=10
    ema1 = EMA2(close, length)
    ema2 = EMA2(ema1, length)
    DEMA2 = 2 * ema1 - ema2

Args:
    close (pd.Series): Series of 'close's
    length (int | float | pd.Series): It's period; a Series gives a per-bar
        length. Default: 10
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.Series: New feature generated.
"""
