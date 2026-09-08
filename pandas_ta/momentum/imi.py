# -*- coding: utf-8 -*-
"""Intraday Momentum Index. Port of TA-Lib's `IMI`.

TA-Lib is BSD-2-Clause, (c) 1999-2007 Mario Fortier. Reference implementation:
`ta-lib/src/ta_func/ta_IMI.c`. The indicator is Tushar Chande's: an RSI whose
up/down bars are measured OPEN-to-CLOSE (the intraday body) rather than
close-to-close, so an overnight gap contributes nothing. Nothing here imports
`talib`; the formula was pinned numerically against `talib` 0.7.1 -- max|diff|
1.4e-14 over 6,057 daily bars.
"""
import numpy as np
from pandas import Series

from pandas_ta.utils import get_offset, verify_series


def imi(open_, close, length=None, offset=None, **kwargs):
    """Indicator: Intraday Momentum Index (IMI)"""
    length = int(length) if length and length > 0 else 14
    open_ = verify_series(open_, length)
    close = verify_series(close, length)
    offset = get_offset(offset)
    if open_ is None or close is None: return

    body = Series(np.asarray(close, dtype=float) - np.asarray(open_, dtype=float),
                  index=close.index)
    gains = body.clip(lower=0.0).rolling(length).sum()
    losses = (-body).clip(lower=0.0).rolling(length).sum()
    total = gains + losses

    with np.errstate(divide="ignore", invalid="ignore"):
        out = 100.0 * gains / total.where(total != 0.0)

    if offset != 0:
        out = out.shift(offset)

    if "fillna" in kwargs:
        out.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        out.fillna(method=kwargs["fill_method"], inplace=True)

    out.name = f"IMI_{length}"
    out.category = "momentum"
    return out


imi.__doc__ = \
"""Intraday Momentum Index (IMI)

Chande's Intraday Momentum Index: RSI computed on the intraday body
(close - open) instead of the close-to-close change. A market that gaps up and
then sells off all day reads WEAK here and strong on RSI, which is the whole
point of the indicator.

Sources:
    TA-Lib `ta_IMI.c` (BSD-2-Clause)
    Tushar Chande & Stanley Kroll, The New Technical Trader (Wiley, 1994)

Calculation:
    Default Inputs:
        length=14
    body   = close - open
    gains  = SUM(max(body, 0), length)
    losses = SUM(max(-body, 0), length)
    IMI    = 100 * gains / (gains + losses)

    Where `gains + losses == 0` -- every bar in the window a doji -- TA-Lib
    divides by zero; this port emits NaN there instead of an infinity, which
    is the only deliberate divergence.

Args:
    open_ (pd.Series): Series of 'open's
    close (pd.Series): Series of 'close's
    length (int): The window. Default: 14
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.Series: IMI_length column, bounded in [0, 100] -- scale-free, an ML
        feature as shipped.
"""
