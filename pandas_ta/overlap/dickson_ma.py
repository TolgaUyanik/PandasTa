# -*- coding: utf-8 -*-
from numpy import abs as npabs, arange, argmin, ceil, flatnonzero, full, isfinite, log, nan
from pandas import Series
from pandas_ta.overlap.hma import hma
from pandas_ta.utils import get_offset, verify_series

GAIN_LIMIT = 50  # Ehlers & Way's GainLimit: gains -5.0 .. +5.0 in steps of 0.1


def _ec(x, length):
    """Ehlers & Way's error-correcting EMA of a float array. Each bar tries
    every gain and keeps the EC closest to the close; non-finite bars hold
    the state and emit NaN. EMA and EC are seeded on the first finite value."""
    alpha = 2 / (length + 1)
    gains = arange(-GAIN_LIMIT, GAIN_LIMIT + 1) / 10
    out = full(len(x), nan)
    ema = ec = nan
    for t in range(len(x)):
        if not isfinite(x[t]): continue
        if not isfinite(ec):
            ema = ec = out[t] = x[t]
            continue
        ema = alpha * x[t] + (1 - alpha) * ema
        cand = alpha * (ema + gains * (x[t] - ec)) + (1 - alpha) * ec
        ec = out[t] = cand[argmin(npabs(x[t] - cand))]  # first minimum == the paper's strict `<`
    return out


def _warmup(length):
    """Valid closes for the EMA's seed error to shrink 1e8-fold: (1 - alpha)^w <= 1e-8.
    Data-independent, so the mask cannot leak the future. 277 at length=30."""
    return int(ceil(log(1e-8) / log((length - 1) / (length + 1)))) if length > 1 else 0


def dickson_ma(close, length=None, hull_length=None, offset=None, **kwargs):
    """Indicator: Dickson Moving Average distance (DICKSON_DIST)"""
    # Validate arguments
    length = int(length) if length and int(length) > 0 else 30
    hull_length = int(hull_length) if hull_length and int(hull_length) > 1 else 7
    warmup = _warmup(length)
    close = verify_series(close, max(warmup, hull_length) + 1)
    offset = get_offset(offset)

    if close is None: return

    # Calculate Result. NaN, infinite, zero and negative closes are missing bars.
    x = close.where(isfinite(close) & (close > 0)).astype(float)
    valid = flatnonzero(x.notna().to_numpy())
    if len(valid) <= warmup: return
    dma = (Series(_ec(x.to_numpy(), length), index=x.index) + hma(x, length=hull_length)) / 2
    dist = 100 * (x / dma.where(dma > 0) - 1)

    # Count valid closes, not bars: a missing bar does not shrink the EMA's seed error.
    dist.iloc[:valid[warmup]] = nan

    # Offset
    if offset != 0:
        dist = dist.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        dist.fillna(kwargs["fillna"], inplace=True)

    # Name and Categorize it
    dist.name = f"DICKSON_DIST_{length}_{hull_length}"
    dist.category = "overlap"

    return dist


dickson_ma.__doc__ = \
"""Dickson Moving Average distance (DICKSON_DIST)

The close's percent distance from Nathan Dickson's moving average (DMA), the
mean of Ehlers & Way's error-correcting EMA (EC) and Alan Hull's moving
average (HMA).

    DMA = (EC(length) + HMA(hull_length)) / 2

Sources:
    Nathan Dickson, "Dickson Moving Average", r/algotrading (2016), as
    named by backtrader's `DicksonMovingAverage` (GPL-3.0); the library
    shows the indicator exists, the code here is written from the
    definitions below as recalled, never from backtrader. No copy of
    either publication was consulted when it was written; checking the
    EC listing against the paper is owed (docs/DicksonMaMeasured.md).
    J. F. Ehlers and R. Way, "Zero Lag (Well, Almost)", Technical Analysis
    of Stocks & Commodities, Nov 2010 (EC, EasyLanguage listing).
    A. Hull, https://alanhull.com/hull-moving-average (HMA; the fork's
    own `hma`).
    Line-by-line Gate A and every measured number: docs/DicksonMaMeasured.md.

EC, per bar (alpha = 2 / (length + 1), gains -5.0 .. +5.0 step 0.1):
    EMA = alpha * close + (1 - alpha) * EMA[1]
    EC(g) = alpha * (EMA + g * (close - EC[1])) + (1 - alpha) * EC[1]
    EC = EC(g) for the g minimising |close - EC(g)|, the lowest g on a tie

Departures from the paper's listing, both start-up or scale details:
    * EMA and EC are seeded on the first valid close (the listing starts
      both at 0); the head is then masked, see Warm-up.
    * The search starts from +inf, not the listing's LeastError = 1000000,
      a price-unit constant that would make the output depend on price
      scale once |close - EC| reaches 1e6.

Warm-up: output starts at the (w+1)-th valid close, w = the closes the EMA's
seed error needs to shrink 1e8-fold, ceil(ln 1e-8 / ln(1 - alpha)) (277 at
length=30). Valid means finite and > 0; other closes are missing bars: EC
holds its state, HMA is NaN while one is in its window, and the output is
NaN. A non-positive DMA also emits NaN; measured at the defaults, after 400
flat closes a one-bar drop held flat first gets there at 99.9%.

Calculation:
    Default Inputs:
        length=30, hull_length=7 (backtrader's defaults)
    DICKSON_DIST = 100 * (close / DMA - 1)     percent

Args:
    close (pd.Series): Series of 'close's
    length (int): EC (and its EMA) period. Default: 30
    hull_length (int): HMA period, >= 2. Default: 7
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)

Returns:
    pd.Series: New feature generated.
"""
