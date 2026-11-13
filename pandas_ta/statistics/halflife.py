# -*- coding: utf-8 -*-
import numpy as np
from pandas import Series
from pandas_ta.utils import get_offset, verify_series


def _slope(c, length):
    """OLS slope of dP_t on [1, P_{t-1}] over each `length`-pair window of `c`:
    rolling cov / rolling var, O(n). Bar T reads closes T - length .. T."""
    finite = c[np.isfinite(c)]
    # Shift-invariant, so subtracting the slice's first close changes nothing
    # but the size of the sums' rounding.
    x = Series(c - (finite[0] if finite.size else 0.0))
    prev = x.shift(1)
    change = x.diff()
    sxy = change.rolling(length, min_periods=length).cov(prev)
    sxx = prev.rolling(length, min_periods=length).var()
    # pandas 3 leaves a ~1e-12 residue in the var of a flat window; test
    # flatness exactly instead of trusting sxx > 0.
    flat = prev.rolling(length, min_periods=length).max() == prev.rolling(length, min_periods=length).min()
    return (sxy / sxx).where(~flat & (sxx > 0)).to_numpy()


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
    # Rolling sums carry the rounding of every value that has left the window,
    # so they are computed in independent blocks: each block's slice starts
    # `length` closes early, and its residue ends at the next block.
    block = 4 * length
    lam = np.full(c.size, np.nan)
    for start in range(0, c.size, block):
        lo = max(0, start - length)
        lam[start:start + block] = _slope(c[lo:start + block], length)[start - lo:]
    with np.errstate(divide="ignore", invalid="ignore"):
        # -ln(2)/lambda is a monotone half-life only for -1 < lambda < 0 (AR(1)
        # coefficient in (0, 1)). lambda >= 0 is not mean-reverting; at
        # lambda = -1 the deviation vanishes in one bar; -2 < lambda < -1 is a
        # damped oscillation; lambda <= -2 does not decay. All are NaN here
        # (owner to confirm; see the docstring), never negative or inf.
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
this port's author, for the owner to confirm):
* lambda >= 0 is not mean-reverting. A negative or infinite half-life would
  put the trending case on the same axis as fast reversion, and an inf
  poisons tree splits.
* lambda <= -1 is outside the monotone-decay range. At lambda = -1 the
  deviation vanishes in one bar; for -2 < lambda < -1 it flips sign each bar
  but still decays (a damped oscillation, still mean-reverting); only
  lambda <= -2 fails to decay. Cost of the cut at -1: the very fastest
  reverters share NaN with trending windows (at the default window, an O-U
  path with theta = 1 is NaN on 56% of bars, theta = 1.2 on 98.5%). Cutting
  at -2 instead would keep them. The owner decides.

Causal: bar T reads closes T - length .. T. Scale-free: lambda is a ratio
of sums that each scale by k^2 under close * k; power-of-two scaling is
exact in floating point, so x8 and x64 are bit-identical. A window with a
NaN close is NaN, and so is a flat window (tested exactly, not by var > 0).

Rolling sums keep the rounding of values that have left the window, so they
are computed in independent blocks of 4 * length bars (each slice starting
length bars early, anchored at its first close): a residue lasts at most
to the next block, and from there the output is bit-identical to a run
that never saw the departed values.

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
