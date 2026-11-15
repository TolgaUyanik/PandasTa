# -*- coding: utf-8 -*-
import numpy as np
from pandas import Series
from pandas_ta.utils import get_offset, verify_series


def max_return(close, length=None, offset=None, **kwargs):
    """Indicator: Maximum one-bar return, lottery effect (MAXRET)"""
    # Validate Arguments
    length = int(length) if length and int(length) > 0 else 21
    close = verify_series(close, length + 1)
    offset = get_offset(offset)

    if close is None: return

    # Calculate Result
    c = close.to_numpy(dtype=float)
    c = np.where(c > 0, c, np.nan)
    # One-bar simple return as a price ratio: exact under a power-of-two rescaling.
    ret = np.concatenate(([np.nan], c[1:] / c[:-1] - 1.0))
    # min_periods=length: a window with a missing return is NaN, not a partial max.
    values = Series(ret).rolling(length, min_periods=length).max().to_numpy()
    maxret = Series(values, index=close.index)

    # Offset
    if offset != 0:
        maxret = maxret.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        maxret.fillna(kwargs["fillna"], inplace=True)

    # Name and Categorize it
    maxret.name = f"MAXRET_{length}"
    maxret.category = "performance"

    return maxret


max_return.__doc__ = \
"""Maximum one-bar return, lottery effect (MAXRET)

The largest one-bar simple return over the last `length` bars, the current
bar included. Stocks with a recent extreme up-day (lottery-like payoffs)
were found to earn lower subsequent returns, the "MAX effect".

Source: Bali, Cakici and Whitelaw (2011), "Maxing out: Stocks as lotteries
and the cross-section of expected returns", J. Financial Economics 99:
MAX = the maximum daily return within the past month. Found for this repo
through Alpha Architect ("Hot off the JFE Press: Maxing Out...your
returns?") and Quantpedia ("Lottery Effect in ETFs Across Several Asset
Classes"). The paper measures a calendar month; this port uses a rolling
`length`-bar window, 21 by default (about one trading month). The paper's
MAX(k) variant, the mean of the k largest returns, is not ported.
PandasTa issue #12.

Causal: bar T reads closes T - length .. T. Scale-free: each return is a
price ratio minus one, so a constant price factor cancels; bit-identical
under x8 and x64. A NaN, zero or negative close leaves the returns into and
out of it missing, and any window holding a missing return is NaN.

Calculation:
    Default Inputs:
        length=21
    r_t = close_t / close_{t-1} - 1
    MAXRET = max(r_{T-length+1}, ..., r_T)

Args:
    close (pd.Series): Series of 'close's
    length (int): Returns in the window. Default: 21
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)

Returns:
    pd.Series: MAXRET_{length}
"""
