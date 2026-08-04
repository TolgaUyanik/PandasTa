# -*- coding: utf-8 -*-
from pandas import DataFrame

from pandas_ta.overlap.sma import sma
from pandas_ta.volatility.atr import atr
from pandas_ta.utils import get_offset, verify_series


def atr_ma_multiple(high, low, close, atr_length=None, ma_length=None, offset=None, **kwargs):
    """Indicator: ATR% Multiple from MA (ATRMAX)"""
    atr_length = int(atr_length) if atr_length and atr_length > 0 else 14
    ma_length = int(ma_length) if ma_length and ma_length > 0 else 50
    high = verify_series(high, max(atr_length, ma_length))
    low = verify_series(low, max(atr_length, ma_length))
    close = verify_series(close, max(atr_length, ma_length))
    offset = get_offset(offset)

    if high is None or low is None or close is None: return

    # Both legs are already scale-free (a ratio of a price-scale quantity
    # to `close`/the MA), so their ratio is dimensionless -- "how many
    # ATR%-units away from its own MA is price", a volatility-adjusted
    # distance-to-MA measure, distinct from `ma_disparity` (raw % distance,
    # not normalized by the instrument's own volatility).
    atr_pct = atr(high, low, close, length=atr_length) / close * 100
    ma = sma(close, length=ma_length)
    pct_gain_ma = (close - ma) / ma * 100
    atr_multiple = pct_gain_ma / atr_pct.replace(0, float("nan"))

    # Offset
    if offset != 0:
        atr_multiple = atr_multiple.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        atr_multiple.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        atr_multiple.fillna(method=kwargs["fill_method"], inplace=True)

    atr_multiple.name = f"ATRMAX_{atr_length}_{ma_length}"
    atr_multiple.category = "volatility"

    return atr_multiple


atr_ma_multiple.__doc__ = \
"""ATR% Multiple from MA (ATRMAX)

How many ATR%-units away from its own SMA the close currently sits --
a volatility-adjusted distance-to-MA measure. `(close - MA) / MA * 100`
alone (already duplicated by the existing `ma_disparity`) says how far
price has moved from its average, but not whether that move is large or
small FOR THIS INSTRUMENT right now; dividing by `ATR / close * 100`
(the existing `atr(percent=True)` computation) rescales it into "number of
typical daily ranges" -- comparable across tickers and across the same
ticker's own calm/volatile regimes, the same normalization idea behind a
z-score but using ATR instead of a rolling standard deviation.

Source: TradingView community indicator "ATR% Multiple from 50-MA" by
GregIX (see `datastore/source/pine_triage.csv` for the exact attribution
row) (ported into AwakenAnalytics/Backtesting TVPTA-3, 2026-08-04;
MPL-2.0 per TradingView's open-source publication convention). Only the
`atrMultiple` calculation is ported -- the source's info-table UI
(`table.new`/`table.cell`, `barstate.islast`-gated) is not a per-bar
numeric series and is not replicated.

Calculation:
    Default Inputs:
        atr_length=14, ma_length=50
    atr_pct = ATR(atr_length) / close * 100
    ma = SMA(close, ma_length)
    pct_gain_ma = (close - ma) / ma * 100
    ATRMAX = pct_gain_ma / atr_pct

Args:
    high (pd.Series): Series of 'high's
    low (pd.Series): Series of 'low's
    close (pd.Series): Series of 'close's
    atr_length (int): ATR period. Default: 14
    ma_length (int): SMA period. Default: 50
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.Series: ATRMAX_{atr_length}_{ma_length}
"""
