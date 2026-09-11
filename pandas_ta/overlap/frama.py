# -*- coding: utf-8 -*-
"""Fractal Adaptive Moving Average (FRAMA).

PINEBI-1b port of ``frama`` from TradingView's ``ta`` library, publication
``RA2vGpkA``, lines 205-213.

    Mozilla Public License 2.0
    (c) TradingView

Gate A oracle, transcribed from the source::

    export frama(series float source, series int length) =>
        int   len    = math.round(length / 2)
        float hh     = ta.highest(len)
        float ll     = ta.lowest(len)
        float n1     = (hh - ll) / len
        float n2     = (hh[len] - ll[len]) / len
        float n3     = (ta.highest(length) - ta.lowest(length)) / length
        float D      = math.log((n1 + n2) / n3) / math.log(2)
        float alpha  = math.exp(-4.6 * (D - 1))
        float result = ewma(source, alpha)

    ewma(series float source, series float alpha) =>
        float result = na
        result := alpha * source + (1.0 - alpha) * nz(result[1], source)

FOUR THINGS THE TRANSCRIPTION HAS TO GET RIGHT
-----------------------------------------------
* ``ta.highest(len)`` / ``ta.lowest(len)`` with no source argument default to
  **`high`** and **`low`** in Pine, not to `source`. Using `source` for both
  makes the fractal dimension a function of closes and changes `alpha`
  everywhere.
* ``n2`` reads the window `len` bars BACK (`hh[len]`), so the estimator
  compares two adjacent half-windows against the whole -- that is the fractal
  dimension. Reading the same window twice collapses `D` to a constant.
* ``ewma`` here is a **variable-alpha** recursion, so it cannot be delegated to
  `pandas.ewm`, which takes a fixed alpha. It is looped.
* Pine's `nz(result[1], source)` seeds the recursion with the CURRENT source on
  the first bar, not with 0.

Like every adaptive moving average, the raw output is a PRICE LEVEL and
therefore not an ML feature. The shipped column is the percent distance from
close; the level is behind ``raw=True``, the convention TALIB-1 set.
"""
from numpy import exp, isfinite, log, nan, zeros
from pandas_ta.utils import get_offset, verify_series


def frama(high, low, close, length=None, offset=None, **kwargs):
    """Indicator: Fractal Adaptive Moving Average (FRAMA)"""
    # Validate Arguments
    length = int(length) if length and length > 0 else 16
    half = int(round(length / 2))
    if half < 1: return
    _length = 2 * length
    high = verify_series(high, _length)
    low = verify_series(low, _length)
    close = verify_series(close, _length)
    offset = get_offset(offset)

    if high is None or low is None or close is None: return

    # Calculate Result
    hh_half = high.rolling(half).max()
    ll_half = low.rolling(half).min()
    n1 = (hh_half - ll_half) / half
    n2 = (hh_half.shift(half) - ll_half.shift(half)) / half
    n3 = (high.rolling(length).max() - low.rolling(length).min()) / length

    ratio = (n1 + n2) / n3.where(n3 != 0)
    d = log(ratio.where(ratio > 0)) / log(2.0)
    alpha = exp(-4.6 * (d - 1.0))
    # Pine does not clamp alpha; a degenerate window can push it outside
    # (0, 1], which makes the recursion diverge rather than smooth. Clamped to
    # the only range in which `ewma` is a filter, and the clamp is stated
    # rather than silent.
    alpha = alpha.clip(lower=0.01, upper=1.0)

    src = close.to_numpy(dtype=float)
    a = alpha.to_numpy(dtype=float)
    out = zeros(len(src))
    prev = nan
    for i in range(len(src)):
        ai = a[i]
        if not isfinite(ai) or not isfinite(src[i]):
            out[i] = nan
            continue
        seed = src[i] if not isfinite(prev) else prev
        prev = ai * src[i] + (1.0 - ai) * seed
        out[i] = prev
    level = close.__class__(out, index=close.index)

    raw = kwargs.pop("raw", False)
    if raw:
        frama = level
        name = f"FRAMA_{length}"
    else:
        frama = 100.0 * (close - level) / level
        name = f"FRAMA_DIST_PCT_{length}"

    # Offset
    if offset != 0:
        frama = frama.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        frama.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        frama.fillna(method=kwargs["fill_method"], inplace=True)

    # Name and Categorize it
    frama.name = name
    frama.category = "overlap"

    return frama


frama.__doc__ = """Fractal Adaptive Moving Average (FRAMA)

An EMA whose smoothing constant is driven by the fractal dimension of recent
price. When the market is trending the estimated dimension falls toward 1 and
alpha rises, so the average tracks price closely; when it is choppy the
dimension rises toward 2 and alpha collapses, so the average flattens. That is
the appeal over a fixed-alpha EMA: one parameter adapts instead of being tuned.

DEFAULT OUTPUT IS THE PERCENT DISTANCE from close, not the level — an adaptive
average is still a price level and levels are not ML features. `raw=True`
returns the level.

Sources:
    https://www.tradingview.com/script/RA2vGpkA/ (MPL-2.0, (c) TradingView)
    John Ehlers, "FRAMA - Fractal Adaptive Moving Average" (2005)

Calculation:
    Default Inputs:
        length=16

    half = round(length / 2)
    n1 = (highest(high, half) - lowest(low, half)) / half
    n2 = n1 shifted back `half` bars
    n3 = (highest(high, length) - lowest(low, length)) / length
    D     = log((n1 + n2) / n3) / log(2)
    alpha = clip(exp(-4.6 * (D - 1)), 0.01, 1.0)
    level = alpha * close + (1 - alpha) * level[1]      # variable-alpha EWMA
    FRAMA_DIST_PCT = 100 * (close - level) / level

Args:
    high (pd.Series): Series of 'high's
    low (pd.Series): Series of 'low's
    close (pd.Series): Series of 'close's
    length (int): The window. Default: 16
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    raw (bool): Return the price level instead of the percent distance.
        Default: False
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.Series: New feature generated.
"""
