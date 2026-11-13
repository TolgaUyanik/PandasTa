# -*- coding: utf-8 -*-
import numpy as np
from pandas import Series

from pandas_ta.utils import get_offset, verify_series

FIRST_LAG = 2  # the source formula's k runs 2 .. max_lag
MIN_MAX_LAG = FIRST_LAG + 1  # a slope needs two (log k, log sd) points
MIN_LENGTH = MIN_MAX_LAG + 2  # lag k needs `length - k` >= 2 differences
# Lagged differences whose standard deviation is below this do not vary: they
# are a constant plus the rounding of `log`. The floor can be an absolute
# constant -- no rolling scale, so no second window to keep causal -- because
# what is floored is a DIMENSIONLESS log price ratio. It sits between the two
# bounds, with orders of room on each side: the rounding of `log(a / b)` is
# about eps * |log(a / b)|, so 4096 eps covers a move of up to 4,000 in log
# terms, while the smallest REAL variation in tick-rounded prices is one tick
# over the price, 1e-9 or more even at a price of 1e6 with a 0.001 tick.
# An eps-scaled tolerance on a float comparison that decides a branch is this
# fork's existing habit -- see `volatility/range_compress_run.py`, whose `tol`
# is 4 eps of the prices being subtracted.
NOISE_ULPS = 4096
NOISE_FLOOR = NOISE_ULPS * np.finfo(float).eps  # 9.09e-13


def lean_hurst_100(close, length=None, max_lag=None, offset=None, **kwargs):
    """Indicator: Hurst exponent, lagged-difference form (LEAN_HURST)"""
    # Validate Arguments
    length = int(length) if length and int(length) >= MIN_LENGTH else 100
    max_lag = int(max_lag) if max_lag and int(max_lag) >= MIN_MAX_LAG else 20
    # Lag k uses the `length - k` pairs with both ends inside the window, so
    # a standard deviation of them needs k <= length - 2. `length >= 5` keeps
    # at least the two lags 2 and 3 after the clamp, so the slope is defined.
    max_lag = min(max_lag, length - 2)
    close = verify_series(close, length)
    offset = get_offset(offset)

    if close is None: return

    # Calculate Result
    c = close.to_numpy(dtype=float)
    # A close that is not a finite, normal, positive float (NaN, inf, zero,
    # negative, or subnormal such as 1e-310) is bad data: it has no price
    # ratio to take a logarithm of, so it is missing.
    c = np.where(np.isfinite(c) & (c >= np.finfo(float).tiny), c, np.nan)
    px = Series(c, index=close.index)

    lags = np.arange(FIRST_LAG, max_lag + 1)
    log_lag = np.log(lags.astype(float))
    log_lag_c = log_lag - log_lag.mean()
    denominator = (log_lag_c ** 2).sum()

    log_sd = np.empty((close.size, lags.size), dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        for j, lag in enumerate(lags):
            # x[t] - x[t - lag] for x = log close, spelled as ONE logarithm of
            # a price RATIO: a x2^k rescale then cancels exactly, where a
            # difference of two logarithms cancels only to rounding.
            diff = np.log(px / px.shift(lag))
            width = int(length - lag)  # pairs with both ends in the window
            sd = diff.rolling(width, min_periods=width).std(ddof=0)
            # A lag whose differences do not vary has log(0) = -inf, which is
            # not a point a slope can be fitted through: the window is NaN.
            # Variation at rounding level is not variation either, and it is
            # what an exactly geometric stretch leaves behind.
            log_sd[:, j] = np.log(sd.where(sd > NOISE_FLOOR).to_numpy())

    # Ordinary least squares slope of log sd on log lag, both centred. Any
    # NaN in the row (a warm-up bar, a missing close, a flat lag) makes the
    # row mean NaN and so the slope NaN.
    values = (((log_sd - log_sd.mean(axis=1, keepdims=True)) * log_lag_c)
              .sum(axis=1) / denominator)

    hurst = Series(values, index=close.index)

    # Offset
    if offset != 0:
        hurst = hurst.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        hurst.fillna(kwargs["fillna"], inplace=True)

    # Name and Categorize it
    hurst.name = f"LEAN_HURST_{length}_{max_lag}"
    hurst.category = "statistics"

    return hurst


lean_hurst_100.__doc__ = \
"""Hurst exponent, lagged-difference form (LEAN_HURST)

How fast the spread of a log-price move grows with the horizon it is
measured over. Inside a rolling window of `length` closes, take the lagged
differences of the log price at every lag k = 2 .. max_lag, take the
standard deviation of each lag's differences, and fit a straight line to
log sd against log k by least squares. The slope is the column.

For a random walk the spread grows as sqrt(k), so the population slope is
exactly 0.5; a persistent (trending) series grows faster and reads higher,
an anti-persistent (mean-reverting) one slower and reads lower. The value
is dimensionless and unbounded -- a slope, not a probability, and not
clipped to [0, 1].

⚠ The LEVEL is biased low, and the ordering is the claim. Measured on
synthetic paths only (docs/LeanHurst100Measured.md carries every number):
over 2,000 independent 100-bar windows of iid returns, whose population
slope is 0.5, the column's median is 0.4199 (mean 0.4132, sd 0.1251, p10
0.2473, p90 0.5681, above 0.5 on 25.65%) -- the window has only
`length - k` overlapping differences per lag. Do not read 0.5 as the
random-walk line on a 100-bar window. The ordering does hold: on 1,500-bar
paths of AR(1) returns the median is 0.7232 at phi = +0.8, 0.5093 at +0.4,
0.4301 for iid returns, 0.3836 at -0.4 and 0.2644 at -0.8. It is also
invariant to drift (a constant added to every log return moves each lag's
differences by k*drift and leaves their sd alone): max |difference|
2.4e-15 against the same walk given +0.004 of drift a bar.

Source: QuantConnect Lean indicators (Apache-2.0), `HurstExponent`, as the
formula is stated by PandasTa issue #85: `HurstExponent(100, maxLag 20):
slope of log std(x[t+k]-x[t]) on log k, k=2..20, x = log close`. ⚠ Lean's
own C# source is NOT in this worktree and web access is unavailable, so
this port is derived from the issue's stated formula, not read off Lean's
code; anything Lean does that the issue's line does not say (its warm-up,
its own standard-deviation convention, whether it subtracts the mean) is
unverified here. The 100-bar window and the maxLag 20 are the issue's own
parameters, and the screen prototype is `docs/issues/screen/ind_screen.py`
candidate `lean_hurst_100` (local to the owner's machine).

Five readings the formula's wording leaves open, decided and priced in
docs/LeanHurst100Measured.md rather than assumed (each number from a
1,500-bar walk, port against variant):
* `std` is the population standard deviation (`ddof=0`, numpy's default and
  the prototype's). The sample convention (`ddof=1`) changes the per-lag
  divisor, so it tilts the fit: max |difference| 5.2e-4, 0 of 1,401 bars
  bit-equal -- but Spearman 1.000000 on that frame, so the choice is
  invisible to anything ranking the column.
* The mean IS subtracted: a standard deviation, not a root mean square of
  the differences. That one is NOT cosmetic -- max |difference| 0.3010,
  Spearman 0.9318.
* k runs 2 .. max_lag, as the issue states. Including k = 1 is a different
  column: max |difference| 0.1006, Spearman 0.9896.
* Only the pairs with BOTH ends inside the window are used, so lag k
  contributes `length - k` differences (98 at k = 2, 80 at k = 20) and the
  column reads exactly `length` closes. Giving every lag `length`
  differences instead reaches `max_lag` bars further back (first value at
  bar 119 rather than 99) and is a different column: max |difference|
  0.3013, Spearman 0.8884.
* The differences are `log(close / close.shift(k))`, the same quantity as
  `log(close) - log(close).shift(k)` (max |difference| 1.8e-15, Spearman
  1.000000, NaN masks equal) but EXACTLY invariant under a x2^k price
  rescale, which a difference of two logarithms is not.

Causal: bar T reads closes T - length + 1 .. T. Scale-free: every input is
a log price ratio, bit-identical under a x8/x64 rescale. NaN on the first
`length - 1` bars, on any window holding a close that is NaN, infinite,
zero, negative or subnormal, and on any window in which some lag's
differences do not vary -- all equal (an exactly flat stretch) or varying
only at rounding level, standard deviation at most NOISE_FLOOR = 9.1e-13,
which is what an exactly geometric stretch leaves behind in float64. On a
tick-rounded walk the floor costs no bars at all.

Calculation:
    Default Inputs:
        length=100, max_lag=20
    k         = 2 .. max_lag
    d_k[t]    = log(close[t] / close[t - k])
    sd_k[t]   = population sd of d_k over the window's `length - k` values
                (NaN where sd_k <= NOISE_FLOOR, so the row is NaN)
    LEAN_HURST = slope of log(sd_k) on log(k), ordinary least squares

Args:
    close (pd.Series): Series of 'close's
    length (int): Closes per window. At least 5; a smaller or missing value
        falls back to the default. Default: 100
    max_lag (int): Largest lag k. At least 3, and clamped to `length - 2`
        (the effective value is the one in the column name). A smaller or
        missing value falls back to the default. Default: 20
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)

Returns:
    pd.Series: LEAN_HURST_{length}_{max_lag}, a dimensionless slope
"""
