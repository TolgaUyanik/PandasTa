# -*- coding: utf-8 -*-
import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from pandas import Series
from pandas_ta.utils import get_offset, verify_series


def halflife(close, length=None, offset=None, **kwargs):
    """Indicator: Ornstein-Uhlenbeck mean-reversion half-life (HLIFE)"""
    # Validate Arguments
    # Two OLS parameters: fewer than 3 pairs leave no residual degree of freedom
    length = int(length) if length and int(length) > 2 else 100
    close = verify_series(close, length + 1)
    offset = get_offset(offset)

    if close is None: return

    # Calculate Result
    c = close.to_numpy(dtype=float)
    # Bar T reads closes T - length .. T: the pairs (P_{t-1}, dP_t), t = T - length + 1 .. T
    win = sliding_window_view(c, length + 1)
    x = win[:, :-1]
    y = win[:, 1:] - x
    with np.errstate(divide="ignore", invalid="ignore"):
        # OLS slope of dP_t on [1, P_{t-1}], by centred sums
        xc = x - x.mean(axis=1, keepdims=True)
        yc = y - y.mean(axis=1, keepdims=True)
        sxx = (xc * xc).sum(axis=1)
        lam = (xc * yc).sum(axis=1) / np.where(sxx > 0, sxx, np.nan)
        # Not mean-reverting (lambda >= 0): no half-life exists; NaN, never
        # a negative or infinite one.
        hl = np.where(lam < 0, -np.log(2.0) / lam, np.nan)

    values = np.full(c.size, np.nan)
    values[length:] = hl
    halflife = Series(values, index=close.index)

    # Offset
    if offset != 0:
        halflife = halflife.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        halflife.fillna(kwargs["fillna"], inplace=True)

    # Name and Categorize it
    halflife.name = f"HLIFE_{length}"
    halflife.category = "statistics"

    return halflife


halflife.__doc__ = \
"""Ornstein-Uhlenbeck mean-reversion half-life (HLIFE)

How many bars a deviation from the window's mean level takes to halve, if
price is mean-reverting: regress the one-bar change dP_t on the previous
close P_{t-1} (with an intercept) over a rolling window; with slope lambda,
half-life = -ln(2) / lambda. Small values mean fast reversion; large values
mean slow reversion. Where lambda >= 0 the window is trending or a random
walk and no half-life exists: the column is NaN there.

Source: the discrete Ornstein-Uhlenbeck half-life of the stat-arb
literature (E. Chan's form), as specified in PandasTa issue #4 (HLIFE-1):
"Regress dP_t on P_{t-1} over a rolling window; with slope lambda,
half-life = -ln(2)/lambda in bars." -ln(2)/lambda is the continuous-time
approximation; the exact AR(1) half-life, -ln(2)/ln(1 + lambda), is
shorter by under 3% for -0.05 < lambda < 0 and is not used.

Why NaN for lambda >= 0 (the decision issue #4 asks for; taken by this
port's author, for the owner to confirm): a negative or
infinite half-life would put the trending case on the same axis as fast
reversion, and an inf poisons tree splits. NaN says "not mean-reverting in
this window" and leaves the model to treat missingness as information.

Causal: bar T reads closes T - length .. T. Scale-free: lambda is a ratio
of sums that each scale by k^2 under close * k, so it cancels; with centred
sums, bit-identical under x8 and x64. A window with a NaN close is NaN, and
so is a flat window.

Memory: every window is held at once, about 8 * n * length bytes per
intermediate array (16 MB at n = 20,000 bars, length = 100). To bound it on
a long history, call it on chunks that each start length bars early.

Calculation:
    Default Inputs:
        length=100
    x_t = close_{t-1},  y_t = close_t - close_{t-1},  t = T - length + 1 .. T
    lambda = sum((x - mean x) * (y - mean y)) / sum((x - mean x)^2)
    HLIFE = -ln(2) / lambda  if lambda < 0, else NaN

Args:
    close (pd.Series): Series of 'close's
    length (int): Regression pairs in the window, at least 3. Default: 100
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)

Returns:
    pd.Series: HLIFE_{length}
"""
