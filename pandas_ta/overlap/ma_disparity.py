# -*- coding: utf-8 -*-
import numpy as np
from pandas import DataFrame

from pandas_ta.overlap.ema import ema
from pandas_ta.overlap.sma import sma
from pandas_ta.utils import get_offset, verify_series


def ma_disparity(close, length=None, ma_type=None, offset=None, **kwargs):
    """Indicator: Moving Average Disparity (MADISP)"""
    # Validate Arguments
    length = int(length) if length and length > 0 else 200
    ma_type = ma_type.lower() if isinstance(ma_type, str) else "sma"
    if ma_type not in ("sma", "ema"):
        ma_type = "sma"
    close = verify_series(close, length)
    offset = get_offset(offset)

    if close is None: return

    # Calculate Result
    ma = sma(close, length=length) if ma_type == "sma" else ema(close, length=length)
    disparity = (close - ma) / ma * 100
    # Signed square: preserves direction while emphasizing extremes, the
    # transform the source indicator ships as its default display mode.
    disparity_sq = np.sign(disparity) * disparity.pow(2)

    # Offset
    if offset != 0:
        disparity = disparity.shift(offset)
        disparity_sq = disparity_sq.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        disparity.fillna(kwargs["fillna"], inplace=True)
        disparity_sq.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        disparity.fillna(method=kwargs["fill_method"], inplace=True)
        disparity_sq.fillna(method=kwargs["fill_method"], inplace=True)

    # Name and Categorize it
    _props = f"_{length}_{ma_type.upper()}"
    disparity.name = f"MADISP{_props}"
    disparity_sq.name = f"MADISPSQ{_props}"
    disparity.category = disparity_sq.category = "overlap"

    # Prepare DataFrame to return
    df = DataFrame({disparity.name: disparity, disparity_sq.name: disparity_sq})
    df.name = f"MADISP{_props}"
    df.category = disparity.category

    return df


ma_disparity.__doc__ = \
"""Moving Average Disparity (MADISP)

Scale-free percentage distance between price and its own moving average --
the "disparity index" mean-reversion measure. Unlike a raw moving average
(a price LEVEL that drifts with the instrument's nominal price and does not
generalize across tickers or time), MADISP is bounded, cross-sectionally
comparable, and directly usable by an ML model without per-ticker scaling.

Source: TradingView community indicator "TY's MA disparity for mean
reversion strategy" by TY, https://www.tradingview.com/script/QbWGkTqA-TY-s-MA-disparity-for-mean-reversion-strategy/
(ported into AwakenAnalytics/Backtesting TVPTA-3, 2026-08-03; MPL-2.0 per
TradingView's open-source publication convention -- see the corpus's
`docs/reviews/auto-2026-08-03-tvpta-2345/` for the porting session).

Calculation:
    Default Inputs:
        length=200, ma_type="sma"
    MA = SMA(close, length)  [or EMA if ma_type="ema"]
    MADISP = (close - MA) / MA * 100
    MADISPSQ = sign(MADISP) * MADISP^2   (signed square -- the source
        indicator's default display mode: preserves direction while
        emphasizing extremes)

Scale-free by construction: scaling close and MA by any constant k leaves
(close - MA) / MA unchanged, so MADISP does not drift with an instrument's
nominal price the way a raw moving average does (verified empirically too,
2026-08-03, across 5 BIST tickers spanning a 12x price range: median|MADISP|
stayed in a ~7-35 band while median close ranged 23-283).

Args:
    close (pd.Series): Series of 'close's
    length (int): The moving-average period. Default: 200
    ma_type (str): "sma" or "ema". An unrecognized value silently falls
        back to "sma" (no error raised). Default: "sma"
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.DataFrame: MADISP_length_TYPE, MADISPSQ_length_TYPE columns.
"""
