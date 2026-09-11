# -*- coding: utf-8 -*-
"""Random Walk Index (RWI).

PINEBI-1b port of ``rwi`` from TradingView's ``ta`` library, publication
``RA2vGpkA``, lines 512-516.

    Mozilla Public License 2.0
    (c) TradingView

Gate A oracle, transcribed line by line from the source::

    export rwi(simple int length) =>
        float divisor = ta.atr(length) * math.sqrt(length)
        float rwiHigh = (high - nz(low[length])) / divisor
        float rwiLow  = (nz(high[length]) - low) / divisor
        [rwiHigh, rwiLow]

Two things in that transcription are easy to get wrong and are pinned by the
test module:

* ``ta.atr`` in Pine is RMA-smoothed True Range -- Wilder's smoothing, NOT an
  EMA and NOT a simple mean.  This fork's ``rma`` is ``adjust=True`` and is a
  DIFFERENT filter (PINEBI-1c measured it); the Wilder filter is
  ``wilder_rma``.  Using ``rma`` here reproduces Pine on no bar but the first.
* ``nz(low[length])`` is the low ``length`` bars back with NaN mapped to 0, not
  dropped.  On the warm-up window that makes ``rwiHigh`` equal ``high /
  divisor`` rather than NaN, which is a real (and large) value, so the warm-up
  must be masked explicitly rather than left to propagate.
"""
from numpy import sqrt
from pandas import DataFrame
from pandas_ta.volatility.true_range import true_range
from pandas_ta.overlap.wilder_rma import wilder_rma
from pandas_ta.utils import get_offset, verify_series


def rwi(high, low, close, length=None, offset=None, **kwargs):
    """Indicator: Random Walk Index (RWI)"""
    # Validate Arguments
    length = int(length) if length and length > 0 else 14
    _length = 2 * length
    high = verify_series(high, _length)
    low = verify_series(low, _length)
    close = verify_series(close, _length)
    offset = get_offset(offset)

    if high is None or low is None or close is None: return

    # Calculate Result
    tr = true_range(high=high, low=low, close=close)
    atr = wilder_rma(tr, length=length)
    if atr is None: return
    divisor = atr * sqrt(length)

    # Pine's nz() maps na to 0.  Reproduced explicitly, then the warm-up is
    # masked: a value computed against a zeroed prior bar is an artifact of
    # nz(), not a reading, and shipping it would plant a large synthetic
    # number on the first `length` bars.
    prior_low = low.shift(length)
    prior_high = high.shift(length)
    warm = prior_low.isna() | prior_high.isna()

    rwi_high = (high - prior_low.fillna(0)) / divisor
    rwi_low = (prior_high.fillna(0) - low) / divisor
    rwi_high[warm] = float("nan")
    rwi_low[warm] = float("nan")

    # Offset
    if offset != 0:
        rwi_high = rwi_high.shift(offset)
        rwi_low = rwi_low.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        rwi_high.fillna(kwargs["fillna"], inplace=True)
        rwi_low.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        rwi_high.fillna(method=kwargs["fill_method"], inplace=True)
        rwi_low.fillna(method=kwargs["fill_method"], inplace=True)

    # Name and Categorize it
    rwi_high.name = f"RWIh_{length}"
    rwi_low.name = f"RWIl_{length}"
    rwi_high.category = rwi_low.category = "momentum"

    data = {rwi_high.name: rwi_high, rwi_low.name: rwi_low}
    df = DataFrame(data)
    df.name = f"RWI_{length}"
    df.category = "momentum"

    return df


rwi.__doc__ = """Random Walk Index (RWI)

Compares the actual move over `length` bars against the move a random walk of
the same volatility would be expected to produce.  The denominator is
`ATR * sqrt(length)` -- the random-walk scaling -- so a reading above 1 says
the range travelled is larger than diffusion alone explains.

Both columns are scale-free: numerator and denominator are both prices, so
multiplying every input by k leaves the ratio unchanged.

Sources:
    https://www.tradingview.com/script/RA2vGpkA/ (MPL-2.0, (c) TradingView)

Calculation:
    Default Inputs:
        length=14

    divisor = wilder_rma(true_range, length) * sqrt(length)
    RWIh = (high - low[length]) / divisor
    RWIl = (high[length] - low) / divisor

Args:
    high (pd.Series): Series of 'high's
    low (pd.Series): Series of 'low's
    close (pd.Series): Series of 'close's
    length (int): The lookback and ATR smoothing period. Default: 14
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.DataFrame: RWIh_{length}, RWIl_{length} columns.
"""
