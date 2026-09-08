# -*- coding: utf-8 -*-
"""`atr2` -- the dynamic-length ATR of the TradingView `ta` library.

Source: `docs/pine/RA2vGpkA-ta.pine` (untracked; see CLAUDE.md), the
TradingView/`ta` Pine v5 library, **MPL-2.0, (c) TradingView**.
`export atr2` is at L102-104, over the `ewma` helper at L75-77:

    L102 export atr2(series float length) =>
    L103     float alpha  = 1.0 / math.max(1.0, length)
    L104     float result = ewma(ta.tr(true), alpha)

WHAT `ta.tr(true)` MEANS, AND WHY IT MATTERS HERE

`ta.tr(handle_na = true)` returns `high - low` on the first bar, where the
previous close does not exist.  `pandas_ta.true_range` instead writes NaN
into `true_range.iloc[:drift]`.  That single bar is part of the warm-up
difference measured below, and it is why this module computes its own true
range rather than importing `true_range`.

THE DIFFERENCES FROM `atr`, MEASURED (docs/PineAlternatesMeasured.md)

1. WARM-UP.  `atr` runs `ma(mamode, tr, length)`; on its default
   `mamode="rma"` that is `ewm(..., min_periods=length)` over a true range
   whose bar 0 is NaN, so the first finite value is at index `length`.
   `atr2` seeds the recursion with the true range itself and has a finite
   bar 0.  Measured at length=14: first-stable index 14 vs 0, **14 bars
   saved**, on GRID_S and on all 40 Grid A tickers.
2. PARAMETER REACH.  `atr` does `length = int(length)`; `atr2` accepts a
   per-bar Series length (Pine's `series float`) and a fractional scalar.

NAMING.  `atr` builds its column name from `mamode[0]` -- `ATRr_14`,
`ATRe_14`, plus the explicit `ATRwr_14` for `wrma`.  `atr2` emits
`ATR2_14`, which collides with none of them (checked against the full
generated column list in `docs/IndicatorDictionary.md`).
"""
import numpy as np
from pandas import DataFrame, Series

from pandas_ta.overlap.ema2 import dynamic_ewma, _length_array
from pandas_ta.utils import get_drift, get_offset, verify_series


def _pine_true_range(high, low, close, drift):
    """Pine `ta.tr(handle_na = true)`: `high - low` where no previous close."""
    prev_close = close.shift(drift)
    tr = DataFrame({
        "hl": high - low,
        "hc": (high - prev_close).abs(),
        "lc": (low - prev_close).abs(),
    }).max(axis=1)
    hl = (high - low)
    tr[prev_close.isna()] = hl[prev_close.isna()]
    return tr


def atr2(high, low, close, length=None, drift=None, offset=None, **kwargs):
    """Indicator: Dynamic-Length Average True Range (ATR2)"""
    high = verify_series(high)
    low = verify_series(low)
    close = verify_series(close)
    drift = get_drift(drift)
    offset = get_offset(offset)
    if high is None or low is None or close is None: return

    lengths, token = _length_array(length, close.index, 14)
    tr = _pine_true_range(high, low, close, drift)
    # L103 `1.0 / math.max(1.0, length)`; the max() is _length_array's floor
    alpha = 1.0 / lengths
    out = Series(dynamic_ewma(tr, alpha), index=close.index)

    percentage = kwargs.pop("percent", False)
    if percentage:
        out *= 100 / close

    if offset != 0:
        out = out.shift(offset)
    if "fillna" in kwargs:
        out.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        out.fillna(method=kwargs["fill_method"], inplace=True)

    out.name = f"ATR2_{token}{'p' if percentage else ''}"
    out.category = "volatility"
    return out


atr2.__doc__ = \
"""Dynamic-Length Average True Range (ATR2)

TradingView `ta.atr2()` -- Wilder smoothing of `ta.tr(true)` with a per-bar
`length` and a source seed, so it is finite from bar 0 where `atr` needs
`length` bars (its true range NaNs bar 0 as well).

Sources:
    TradingView `ta` library (RA2vGpkA), L75-77 and L102-104. MPL-2.0,
    (c) TradingView.

Calculation:
    Default Inputs:
        length=14, drift=1, percent=False
    tr[0] = high[0] - low[0]
    tr[i] = max(high - low, |high - close[i-1]|, |low - close[i-1]|)
    alpha = 1 / max(1, length)
    ATR2[0] = tr[0]
    ATR2[i] = alpha * tr[i] + (1 - alpha) * ATR2[i-1]

    if percent:
        ATR2 *= 100 / close

Args:
    high (pd.Series): Series of 'high's
    low (pd.Series): Series of 'low's
    close (pd.Series): Series of 'close's
    length (int | float | pd.Series): It's period; a Series gives a per-bar
        length. Default: 14
    drift (int): The difference period. Default: 1
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    percent (bool, optional): Return as percentage. Default: False
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.Series: New feature generated.
"""
