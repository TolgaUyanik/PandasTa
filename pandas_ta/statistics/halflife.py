# -*- coding: utf-8 -*-
import numpy as np
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
    c = close.astype(float)
    # Bar T reads closes T - length .. T: the pairs (P_{t-1}, dP_t), t = T - length + 1 .. T
    prev = c.shift(1)
    change = c.diff()
    # OLS slope of dP_t on [1, P_{t-1}] from rolling sums: cov / var, O(n)
    sxy = change.rolling(length, min_periods=length).cov(prev)
    sxx = prev.rolling(length, min_periods=length).var()
    lam = (sxy / sxx.where(sxx > 0)).to_numpy()
    with np.errstate(divide="ignore", invalid="ignore"):
        # A half-life exists only for -1 < lambda < 0 (AR(1) coefficient in
        # (0, 1)). lambda >= 0 is not mean-reverting; lambda <= -1 flips sign
        # every bar or explodes. Both are NaN, never a negative, inf or
        # sub-bar "half-life".
        values = np.where((lam < 0) & (lam > -1), -np.log(2.0) / lam, np.nan)
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
mean slow reversion. A half-life exists only for -1 < lambda < 0; outside
it (trending, random-walk-like, or oscillating windows) the column is NaN.

Source: the discrete Ornstein-Uhlenbeck half-life of the stat-arb
literature (E. Chan's form), as specified in PandasTa issue #4 (HLIFE-1):
"Regress dP_t on P_{t-1} over a rolling window; with slope lambda,
half-life = -ln(2)/lambda in bars." That is the continuous-time
approximation, kept deliberately; the exact AR(1) half-life,
-ln(2)/ln(1 + lambda), is shorter: by 2.5% at lambda = -0.05, 10.4% at
-0.2 (3.5 bars) and 27.9% at -0.5.

Why NaN outside -1 < lambda < 0 (the decision issue #4 asks for; taken by
this port's author, for the owner to confirm): a negative or infinite
half-life would put the trending case on the same axis as fast reversion,
an inf poisons tree splits, and for lambda <= -1 the deviation changes sign
every bar (or grows), so -ln(2)/lambda is not a half-life. NaN says "no
half-life in this window" and leaves the model to treat missingness as
information.

Causal: bar T reads closes T - length .. T. Scale-free: lambda is a ratio
of sums that each scale by k^2 under close * k; power-of-two scaling is
exact in floating point, so x8 and x64 are bit-identical. A window with a
NaN close is NaN, and so is a flat window.

Calculation:
    Default Inputs:
        length=100
    x_t = close_{t-1},  y_t = close_t - close_{t-1},  t = T - length + 1 .. T
    lambda = rolling cov(y, x) / rolling var(x)
    HLIFE = -ln(2) / lambda  if -1 < lambda < 0, else NaN

Args:
    close (pd.Series): Series of 'close's
    length (int): Regression pairs in the window, at least 3. Default: 100
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)

Returns:
    pd.Series: HLIFE_{length}
"""
