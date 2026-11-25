# -*- coding: utf-8 -*-
import numpy as np
from pandas_ta.overlap.ema import ema
from pandas_ta.utils import get_offset, verify_series

npNaN = np.nan


def fn_baspn_net(high, low, close, volume, slow=None, fast=None, offset=None, **kwargs):
    """Indicator: Normalised Buy/Sell Pressure, net (finta BASPN)"""
    # Validate Arguments
    slow = int(slow) if slow and slow > 0 else 40
    fast = int(fast) if fast and fast > 0 else 20
    _length = max(slow, fast) + 1
    high = verify_series(high, _length)
    low = verify_series(low, _length)
    close = verify_series(close, _length)
    volume = verify_series(volume, _length)
    offset = get_offset(offset)

    if high is None or low is None or close is None or volume is None:
        return

    # Calculate Result
    norm_volume = volume / ema(volume, length=slow).replace(0, npNaN)
    buy_pressure, sell_pressure = close - low, high - close
    buy_ratio = buy_pressure / ema(buy_pressure, length=slow).replace(0, npNaN)
    sell_ratio = sell_pressure / ema(sell_pressure, length=slow).replace(0, npNaN)
    buy = ema(buy_ratio * norm_volume, length=fast)
    sell = ema(sell_ratio * norm_volume, length=fast)
    baspn_net = buy - sell

    # Offset
    if offset != 0:
        baspn_net = baspn_net.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        baspn_net.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        baspn_net.fillna(method=kwargs["fill_method"], inplace=True)

    # Name and Categorize it
    baspn_net.name = f"FN_BASPN_NET_{slow}_{fast}"
    baspn_net.category = "volume"

    return baspn_net


fn_baspn_net.__doc__ = \
"""Normalised Buy/Sell Pressure, net (finta BASPN)

Each leg is a volume-weighted price-pressure ratio: `(C-L)/EMA40(C-L)` ("buy
pressure", how today's close-to-low range compares to its own 40-bar EMA) and
`(H-C)/EMA40(H-C)` ("sell pressure", high-to-close vs. its 40-bar EMA), both
scaled by `V/EMA40(V)` (volume vs. its own 40-bar EMA) before a final 20-bar
EMA smooths each leg. The net is buy minus sell -- positive when buying
pressure dominates. Both legs divide a price difference by an EMA of ITSELF
and a volume by an EMA of ITSELF, so every term is already dimensionless: a
constant rescale of price (high, low, close together) or of volume leaves the
column UNCHANGED, not merely proportionally rescaled, since the rescale
cancels inside each ratio -- this is "scale-free" in the strongest sense, not
just invariant up to a constant.

Source: finta (LGPL-3.0, archived) -- existence, not evidence; ported from the
formula text quoted in issue #150, never read off finta's code:

    BASPN = EMA20((C-L)/EMA40(C-L) * V/EMA40(V)) - EMA20((H-C)/EMA40(H-C) * V/EMA40(V))

Departure from the source text: the EMAs here are this fork's own `ema()`
(SMA-seeded warm-up, `adjust=False` recursion -- see `pandas_ta/overlap/ema.py`),
not a bare `Series.ewm(adjust=True)`. The formula names "EMA" without fixing
an implementation; using this package's own EMA building block, as every
other EMA-based indicator in this fork already does (e.g. `kvo`, `macd`'s
signal line), keeps behaviour consistent across the package rather than
introducing a second, bespoke EMA just for this port.

Each ratio's denominator is guarded (`.replace(0, NaN)`): a ratio's own EMA
is exactly zero only when every value feeding it over its full decay has been
zero, which does not occur on OHLCV data where `close - low >= 0` and
`high - close >= 0` are generically positive; the guard turns that
degenerate case into NaN rather than inf, matching this fork's `non_zero_range`
convention used elsewhere (e.g. `cmf`).

Calculation:
    Default Inputs:
        slow=40, fast=20
    EMA = this package's own Exponential Moving Average (SMA-seeded, adjust=False)

    norm_volume = V / EMA(V, slow)
    buy_ratio   = (C - L) / EMA(C - L, slow)
    sell_ratio  = (H - C) / EMA(H - C, slow)
    buy  = EMA(buy_ratio  * norm_volume, fast)
    sell = EMA(sell_ratio * norm_volume, fast)
    BASPN_NET = buy - sell

Args:
    high (pd.Series): Series of 'high's
    low (pd.Series): Series of 'low's
    close (pd.Series): Series of 'close's
    volume (pd.Series): Series of 'volume's
    slow (int): EMA period for each pressure ratio and for volume. Default: 40
    fast (int): EMA period for the final buy/sell smoothing. Default: 20
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.Series: FN_BASPN_NET_{slow}_{fast}, scale-free, signed (positive = net
        buying pressure).
"""
