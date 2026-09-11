# -*- coding: utf-8 -*-
"""`rma2` -- the dynamic-alpha Wilder RMA of the TradingView `ta` library.

Source: `docs/pine/RA2vGpkA-ta.pine` (untracked; see CLAUDE.md), the
TradingView/`ta` Pine v5 library, **MPL-2.0, (c) TradingView**.
`export rma2` is at L496-498, over the `ewma` helper at L75-77:

    L496 export rma2(series float source, series float length) =>
    L497     float alpha  = 1.0 / math.max(1.0, length)
    L498     float result = ewma(source, alpha)

WHICH FORK FUNCTION IS THE SIBLING -- READ THIS BEFORE COMPARING

The fork ships TWO `alpha = 1/length` averages and they are NOT the same
indicator:

  * `pandas_ta.rma`        -- `ewm(alpha=1/length, adjust=True,
    min_periods=length)`.  `adjust=True` renormalises by the truncated
    weight sum, so this is a weighted mean of the window, not Wilder's
    recursion.
  * `pandas_ta.wilder_rma` -- true Wilder, `adjust=False`, seeded with the
    SMA of the first `length` bars.

Pine's `ta.rma` (and therefore `rma2`) IS Wilder's, so the sibling to
compare against is **`wilder_rma`**, not `rma`.  Both are measured in
`docs/PineAlternatesMeasured.md`; the warm-up figure below is against
`wilder_rma`.

THE DIFFERENCES, MEASURED

1. WARM-UP.  `wilder_rma` seeds with an SMA at index `length - 1`; `rma2`
   seeds with the source at bar 0.  Measured at length=10: first-stable
   index 9 vs 0, **9 bars saved**, on GRID_S and on all 40 Grid A tickers.
2. PARAMETER REACH.  `wilder_rma` and `rma` both do `int(length)`; `rma2`
   accepts a per-bar Series length and a fractional scalar.
"""
import numpy as np
from pandas import Series

from pandas_ta.overlap.ema2 import dynamic_ewma, _length_array
from pandas_ta.utils import get_offset, verify_series


def rma2(close, length=None, offset=None, **kwargs):
    """Indicator: Dynamic-Length wildeR's Moving Average (RMA2)"""
    close = verify_series(close)
    offset = get_offset(offset)
    if close is None: return

    lengths, token = _length_array(length, close.index, 10)
    # L497 `1.0 / math.max(1.0, length)`; the max() is _length_array's floor
    alpha = 1.0 / lengths
    out = Series(dynamic_ewma(close, alpha), index=close.index)

    if offset != 0:
        out = out.shift(offset)
    if "fillna" in kwargs:
        out.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        out.fillna(method=kwargs["fill_method"], inplace=True)

    out.name = f"RMA2_{token}"
    out.category = "overlap"
    return out


rma2.__doc__ = \
"""Dynamic-Length wildeR's Moving Average (RMA2)

TradingView `ta.rma2()` -- Wilder's smoothing (`alpha = 1/length`) with a
per-bar `length` and a source seed instead of an SMA seed, so it is finite
from bar 0.  The comparable shipped indicator is `wilder_rma`, NOT `rma`
(`rma` uses `adjust=True` and is a different filter).

Sources:
    TradingView `ta` library (RA2vGpkA), L75-77 and L496-498. MPL-2.0,
    (c) TradingView.

Calculation:
    Default Inputs:
        length=10
    alpha = 1 / max(1, length)
    RMA2[0] = close[0]
    RMA2[i] = alpha * close[i] + (1 - alpha) * RMA2[i-1]

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
