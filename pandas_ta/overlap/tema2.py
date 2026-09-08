# -*- coding: utf-8 -*-
"""`tema2` -- the dynamic-length TEMA of the TradingView `ta` library.

Source: `docs/pine/RA2vGpkA-ta.pine` (untracked; see CLAUDE.md), the
TradingView/`ta` Pine v5 library, **MPL-2.0, (c) TradingView**.
`export tema2` is at L681-685:

    L681 export tema2(series float source, series float length) =>
    L682     float ema1   = ema2(source,  length)
    L683     float ema2   = ema2(ema1, length)
    L684     float ema3   = ema2(ema2, length)
    L685     float result = 3 * (ema1 - ema2) + ema3

(As in `dema2`, L683-684 shadow the function name with a local variable.
The non-alternate `tema()` at L669-673 is the unambiguous statement of
intent: three chained EMAs, `3 * (ema1 - ema2) + ema3`.)

THE DIFFERENCES FROM `tema`, MEASURED (docs/PineAlternatesMeasured.md)

1. WARM-UP.  `tema` chains three SMA-seeded `ema` calls; as in `dema`,
   chaining does not multiply the warm-up (see `dema2`'s docstring for the
   measured reason).  Measured at length=10: first-stable index 9 vs 0,
   **9 bars saved**, on GRID_S and on all 40 Grid A tickers.
2. PARAMETER REACH.  `tema` does `int(length)`; `tema2` takes a per-bar
   Series length or a fractional scalar.
"""
from pandas_ta.overlap.ema2 import ema2, _length_array
from pandas_ta.utils import get_offset, verify_series


def tema2(close, length=None, offset=None, **kwargs):
    """Indicator: Dynamic-Length Triple Exponential Moving Average (TEMA2)"""
    close = verify_series(close)
    offset = get_offset(offset)
    if close is None: return

    _, token = _length_array(length, close.index, 10)
    e1 = ema2(close=close, length=length)
    e2 = ema2(close=e1, length=length)
    e3 = ema2(close=e2, length=length)
    out = 3 * (e1 - e2) + e3

    if offset != 0:
        out = out.shift(offset)
    if "fillna" in kwargs:
        out.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        out.fillna(method=kwargs["fill_method"], inplace=True)

    out.name = f"TEMA2_{token}"
    out.category = "overlap"
    return out


tema2.__doc__ = \
"""Dynamic-Length Triple Exponential Moving Average (TEMA2)

TradingView `ta.tema2()` -- `3 * (ema1 - ema2) + ema3` over the
source-seeded, per-bar-length `ema2`.  Finite from bar 0 where `tema` needs
`length - 1` bars (measured 9 at length=10).

Sources:
    TradingView `ta` library (RA2vGpkA), L681-685. MPL-2.0, (c) TradingView.

Calculation:
    Default Inputs:
        length=10
    ema1 = EMA2(close, length)
    ema2 = EMA2(ema1, length)
    ema3 = EMA2(ema2, length)
    TEMA2 = 3 * (ema1 - ema2) + ema3

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
