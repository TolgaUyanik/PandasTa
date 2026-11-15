# -*- coding: utf-8 -*-
import numpy as np
from pandas import Series

from pandas_ta.utils import get_offset, verify_series

# A deviation over a single return is just that return's own magnitude when it
# is negative and zero when it is not -- the one-bar down-move, which is a
# different feature from a window's downside deviation. Two returns is the
# smallest window over which the root-mean-square is a mean of anything.
MIN_LENGTH = 2
# `length` returns need `length + 1` closes: the oldest return in the window
# reads one bar further back than the window's first bar.
EXTRA_CLOSES = 1
# The target is the issue's parameter and is FIXED at zero rather than offered
# as an argument. A non-zero minimum acceptable return is a different feature
# and would need its own column name to carry it -- in this fork a column name
# encodes every parameter that changes its values, because the parent repo's
# mined rules match on the string.
TARGET = 0.0


def lean_tdd_20(close, length=None, offset=None, **kwargs):
    """Indicator: Target downside deviation, target 0 (LEAN_TDD)"""
    # Validate Arguments
    length = int(length) if length and int(length) >= MIN_LENGTH else 20
    close = verify_series(close, length + EXTRA_CLOSES)
    offset = get_offset(offset)

    if close is None: return

    # Calculate Result
    c = close.to_numpy(dtype=float)
    # A close that is not a finite, normal, positive float (NaN, inf, zero,
    # negative, or subnormal such as 1e-310) is bad data: it has no return, so
    # it is missing rather than a move to or from it.
    c = np.where(np.isfinite(c) & (c >= np.finfo(float).tiny), c, np.nan)
    px = Series(c, index=close.index)

    # The simple return, spelled as a price RATIO minus one: scale-free, and
    # `8a / 8b` is the same double as `a / b`, so a x2^k rescale cancels
    # exactly where a difference of two logarithms would only cancel to
    # rounding.
    r = px / px.shift(1) - 1.0
    # The UNDERPERFORMANCE against the target: a return at or above it
    # underperforms by zero, it is not dropped. `np.minimum` propagates NaN,
    # which is what keeps an unknown return unknown.
    squared = np.minimum(r - TARGET, 0.0) ** 2

    # Root MEAN square over the whole window, so the divisor is `length` and
    # not the number of returns that fell short. `min_periods=length` is what
    # makes the warm-up and any window holding an unknown return NaN instead
    # of a silently shorter window. This is the module's ONLY rolling call, so
    # it is the only window whose causality Gate B has to pin.
    mean_squared = squared.rolling(length, min_periods=length).mean()

    # No floor under the square root, which is a decision and not an
    # omission: the mean of squares cannot be negative in exact arithmetic,
    # but `rolling.mean` adds and removes terms, so a window whose squares are
    # all zero after a large one left it could in principle land a few ulps
    # BELOW zero and turn "no downside at all" into NaN. Measured instead of
    # guarded: on a frame built to force that cancellation the unguarded mean
    # is below zero on 0 of 180 complete windows, and the 160 whose squares
    # have all left the window are EXACTLY zero rather than a small residue
    # (the other 20 still hold the big square; docs/LeanTdd20Measured.md Gate
    # A6), so a clip here would be code that nothing reaches.
    # `test_a_complete_window_is_never_nan_however_the_squares_cancel` pins it
    # on the one frame where a large square actually LEAVES the window, plus a
    # rally and a flat frame where every square is zero from the start and the
    # mean has nothing to cancel -- so a pandas change that made the mean
    # negative would fail loudly rather than empty the column.
    tdd = np.sqrt(mean_squared)

    # Offset
    if offset != 0:
        tdd = tdd.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        tdd.fillna(kwargs["fillna"], inplace=True)

    # Name and Categorize it
    tdd.name = f"LEAN_TDD_{length}"
    tdd.category = "statistics"

    return tdd


lean_tdd_20.__doc__ = \
"""Target downside deviation, target 0 (LEAN_TDD)

How large the recent shortfalls below a target return were, in return units.
Inside a rolling window of `length` simple returns, replace every return at
or above the target by zero, square what is left and take the square root of
the MEAN over the whole window:

    LEAN_TDD = sqrt( mean( min(r - target, 0)^2 ) )

The target is FIXED at zero, which is the issue's parameter, so the column is
the root-mean-square of the window's negative returns with the up bars
counted as zeros rather than dropped. It is the denominator of the Sortino
ratio, and it differs from a standard deviation in two ways that matter: the
up side is discarded instead of averaged, and nothing is centred -- the
target, not the window's own mean, is what deviations are taken from.

The column is dimensionless (a function of price RATIOS), non-negative, and
EXACTLY zero on any window with no negative return -- a rally, or a flat
stretch. That zero is a reading and not missing data.

⚠ It is largely a VOLATILITY measure, which is the thing to know before
reading it as a downside-risk feature. For iid returns with standard
deviation s the population value is s / sqrt(2); measured over 2,000
independent 20-return windows at s = 0.01 the median is 0.006683 against
that population 0.007071 (mean 0.006772, sd 0.001752, p10 0.004564, p90
0.009094), and on a 1,500-bar gaussian walk the column's Spearman against
the population standard deviation of the same 20 returns is 0.6356 and
against the shipped `ui` 0.6798 on one synthetic OHLC frame. On real data
the screen found the same thing more strongly: the prototype's Gate E max
|rho| was 0.8123 against `ui`, the DISCLOSE_GAP band.

What it adds over a standard deviation is ASYMMETRY. Measured on two paths
built from the same two-point return mixture with opposite skew (skew -2.80
and +2.80, realised simple-return sd 0.014695 and 0.015324 -- the up-skewed
path is the slightly MORE volatile of the two): the column's median is
0.014444 on the down-skewed path and 0.004555 on the up-skewed one, a ratio
of 3.17. It also does NOT order persistence: AR(1) returns driven by one set
of innovations read medians 0.009389 / 0.007593 / 0.007902 / 0.011441 at
phi = +0.8 / +0.4 / -0.4 / -0.8, which is the U shape of the unconditional
variance and not a trend/reversion scale. docs/LeanTdd20Measured.md carries
every number.

Source: QuantConnect Lean indicators (Apache-2.0),
`TargetDownsideDeviation`, as the formula is named by PandasTa issue #87:
`TargetDownsideDeviation(20, 0)`.
⚠ Lean's own C# source is NOT in this worktree and web access is
unavailable, so this port is derived from the standard definition of the
target downside deviation and from the screen prototype's one line, not read
off Lean's code; anything Lean does that neither says (what it emits before
its window fills, whether its divisor is the window count or the number of
shortfalls, what series it is fed) is unverified here. The 20 and the target
0 are the issue's own parameters, and the screen prototype is
`docs/issues/screen/ind_screen.py` candidate `lean_tdd_20`, local to the
owner's machine, which spells it
`np.sqrt(mean(ret(c).clip(upper=0) ** 2, 20))`.

Four readings the wording leaves open, decided and priced in
docs/LeanTdd20Measured.md rather than assumed (numbers from a 1,500-bar
walk, port against variant over 1,480 fired bars):
* the divisor is the WINDOW, not the number of shortfalls -- which is the
  same decision as counting a return above the target as a ZERO rather than
  dropping it, seen from the other side. Dividing by the count of returns
  that fell short instead is a different column: max |difference| 1.2e-2 on
  a walk and 1.9e-2 on a 0.01 price grid, Spearman 0.8707 and 0.8452. It is
  also the reading that can make the column RISE when up bars replace down
  bars, because they leave the average rather than enter it as zeros.
* the window holds `length` RETURNS, so it reads `length + 1` closes and the
  warm-up is `length` bars. Holding `length` CLOSES instead is one return
  fewer: max |difference| 6.0e-3, Spearman 0.9678, and it fires one bar
  earlier.
* the warm-up is NaN. Emitting a PARTIAL window instead -- dividing by the
  window's current count, which is one plausible reading of an indicator
  that is not yet ready, and NOT a statement about Lean's code, which was
  not read in this session -- changes only the first `length - 1` bars and
  agrees bit-for-bit on all 1,480 afterwards; it would put 19 bars of a
  differently-scaled statistic at the head of the column, which this fork's
  ML contract reads as data.
* the mean of squares is divided by `length` (population). The sample
  divisor `length - 1` multiplies the whole column by sqrt(20/19) = 1.0260,
  so it is a different value (max |difference| 4.7e-4, 0 of 1,480 bars
  bit-equal) and all but the same ranking (Spearman 0.99999999, not 1: a
  common factor applied in floating point still breaks exact ties).

Causal: bar T reads closes T - length .. T. Scale-free: the only inputs are
price ratios, so the column is bit-identical under x8/x64 (1,480 of 1,480
fired bars on each of three frames) and equal to within 7.2e-17 absolute /
1.3e-14 relative under x10/x3.7, where the ratio no longer divides out
exactly. NaN on the first `length` bars and on any window holding a close
that is NaN, infinite, zero, negative or subnormal -- at the default
`offset=0`, nowhere else (a non-zero `offset` shifts the NaN block with the
column): unlike a share or a ratio this column has no undefined case,
because a window with no shortfall is zero.

Calculation:
    Default Inputs:
        length=20   (target fixed at 0.0)
    r[t]     = close[t] / close[t-1] - 1
    s[t]     = min(r[t] - 0, 0)                 # 0 on an up or flat bar
    LEAN_TDD = sqrt( mean of s^2 over the trailing `length` returns )

Args:
    close (pd.Series): Series of 'close's
    length (int): Returns per window. At least 2; a smaller or missing value
        falls back to the default. Default: 20
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)

Returns:
    pd.Series: LEAN_TDD_{length}, a non-negative dimensionless deviation
"""
