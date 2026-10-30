# -*- coding: utf-8 -*-
import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from pandas import Series
from pandas_ta.utils import get_offset, verify_series


def cusum(close, length=None, offset=None, **kwargs):
    """Indicator: Chu-Stinchcombe-White CUSUM statistic (CUSUM)"""
    # Validate Arguments
    length = int(length) if length and int(length) > 1 else 100
    close = verify_series(close, length + 1)
    offset = get_offset(offset)

    if close is None: return

    # Calculate Result
    c = close.to_numpy(dtype=float)
    # Bar T reads closes T - length .. T: the reference points n = T - length
    # .. T - 1 and the length one-bar log returns between them.
    win = sliding_window_view(c, length + 1)
    k = np.sqrt(np.arange(length, 0, -1, dtype=float))  # sqrt(t - n)
    with np.errstate(divide="ignore", invalid="ignore"):
        # Log differences as log of a ratio: exact under a power-of-two rescaling.
        r = np.log(win[:, 1:] / win[:, :-1])
        r[~np.isfinite(r)] = np.nan
        dep = np.log(win[:, -1:] / win[:, :-1])  # y_t - y_n
        dep[~np.isfinite(dep)] = np.nan
        sigma = np.sqrt((r * r).mean(axis=1))
        # A flat window has no volatility; NaN, not inf.
        sigma = np.where(sigma > 0, sigma, np.nan)
        stat = (dep / (sigma[:, None] * k)).max(axis=1)

    values = np.full(c.size, np.nan)
    values[length:] = stat
    cusum = Series(values, index=close.index)

    # Offset
    if offset != 0:
        cusum = cusum.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        cusum.fillna(kwargs["fillna"], inplace=True)

    # Name and Categorize it
    cusum.name = f"CUSUM_{length}"
    cusum.category = "statistics"

    return cusum


cusum.__doc__ = \
"""Chu-Stinchcombe-White CUSUM statistic (CUSUM)

The largest standardised rise of log price over any earlier reference bar
in a rolling window: for each reference bar n, the log change from n to the
current bar divided by the window's one-bar volatility times sqrt(bars
elapsed). Near zero or negative means price is at or below every recent
level after scaling; large positive means it has broken upward from some
recent level faster than its volatility explains.

Source: the Chu-Stinchcombe-White CUSUM test on levels, as given in Lopez de
Prado, Advances in Financial Machine Learning (2018), ch. 17 "Structural
Breaks": S_{n,t} = (y_t - y_n) / (sigma_t * sqrt(t - n)), with sigma_t^2 the
mean squared one-bar change of y up to t, and S_t = sup over n of S_{n,t},
y = log price. The book takes the supremum over every earlier bar (O(n^2)
over a series); this port takes it over the last `length` bars and
estimates sigma_t over the same window. One-sided (upward), as in the book.
PandasTa issue #16.

Causal: bar T reads closes T - length .. T. Scale-free: every change enters
as the log of a price ratio, so a constant price factor cancels;
bit-identical under x8 and x64. A window with a NaN, zero or negative close
is NaN, and so is a flat window (zero volatility).

Memory: every window is held at once, about 8 * n * length bytes per
intermediate array (80 MB at n = 10,000 bars, length = 1,000). To bound it
on a long history, call it on chunks that each start length bars early.

Calculation:
    Default Inputs:
        length=100
    r_i = log(close_i / close_{i-1}),  i = T - length + 1 .. T
    sigma = sqrt(mean(r_i^2))
    S_n = log(close_T / close_n) / (sigma * sqrt(T - n)),  n = T - length .. T - 1
    CUSUM = max(S_n)

Args:
    close (pd.Series): Series of 'close's
    length (int): Reference bars in the window, at least 2. Default: 100
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)

Returns:
    pd.Series: CUSUM_{length}
"""
