# -*- coding: utf-8 -*-
import numpy as np
from pandas import Series

from pandas_ta.utils import get_offset, verify_series

MIN_LAG = 1
# A window of `length` returns holds `length - 2*lag` triples, and a mean
# wants at least two of them; the standard deviation (ddof=1) wants at least
# two returns. `length=4` at `lag=1` is the smallest window giving both.
MIN_TRIPLES = 2
MIN_LENGTH = MIN_TRIPLES + 2 * MIN_LAG
EXTRA_CLOSES = 1  # `length` returns need `length + 1` closes
# A window whose returns vary only at rounding level has no volatility to
# divide by: the quotient would be the ratio of two roundings, which is
# arbitrary and large rather than small. The floor can be an absolute
# constant -- no rolling scale, so no second window to keep causal -- because
# what is floored is the standard deviation of DIMENSIONLESS price ratios.
# An eps-scaled tolerance on a float comparison that decides a branch is this
# fork's existing habit: see `statistics/lean_hurst_100.py`, whose NOISE_FLOOR
# is the same 4096 eps on a log price ratio, and
# `volatility/range_compress_run.py`, whose `tol` is 4 eps of the prices being
# subtracted.
NOISE_ULPS = 4096
NOISE_FLOOR = NOISE_ULPS * np.finfo(float).eps  # 9.09e-13


def ts_c3_20(close, length=None, lag=None, offset=None, **kwargs):
    """Indicator: C3 nonlinearity of returns (TS_C3)"""
    # Validate Arguments
    length = int(length) if length and int(length) >= MIN_LENGTH else 20
    lag = int(lag) if lag and int(lag) >= MIN_LAG else 1
    # Keep at least `MIN_TRIPLES` triples inside the window, so the numerator
    # is a mean of something. The effective lag is the one in the column name.
    lag = min(lag, (length - MIN_TRIPLES) // 2)
    close = verify_series(close, length + EXTRA_CLOSES)
    offset = get_offset(offset)

    if close is None: return

    # Calculate Result
    c = close.to_numpy(dtype=float)
    # A close that is not a finite, normal, positive float (NaN, inf, zero,
    # negative, or subnormal such as 1e-310) is bad data: it has no return to
    # take, so it is missing.
    c = np.where(np.isfinite(c) & (c >= np.finfo(float).tiny), c, np.nan)
    px = Series(c, index=close.index)

    # The simple return, spelled as a price RATIO minus one: `8a / 8b` is the
    # same double as `a / b`, so a x2^k rescale cancels exactly rather than to
    # rounding.
    r = px / px.shift(1) - 1.0
    # c3's product, `x[t] * x[t-lag] * x[t-2*lag]`.
    triple = r * r.shift(lag) * r.shift(2 * lag)
    # `length - 2*lag` of those triples have all three ends inside a window of
    # `length` returns, so the column reads exactly `length + 1` closes: the
    # oldest factor of the oldest triple is the window's first return.
    triples = length - 2 * lag
    numerator = triple.rolling(triples, min_periods=triples).mean()
    # The scale-free divisor of the screen prototype: the SAMPLE standard
    # deviation (`ddof=1`, pandas' default and the prototype's) of the same
    # `length` returns, cubed, so the column is the third-order analogue of a
    # standardised moment and does not move with the volatility regime.
    sd = r.rolling(length, min_periods=length).std(ddof=1)
    # Emptying the divisor first means no zero and no rounding-level value
    # ever reaches the division, so there is nothing for an `errstate` to
    # suppress and no infinity to clean up afterwards.
    c3 = numerator / (sd.where(sd > NOISE_FLOOR) ** 3)

    # Offset
    if offset != 0:
        c3 = c3.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        c3.fillna(kwargs["fillna"], inplace=True)

    # Name and Categorize it
    c3.name = f"TS_C3_{length}_{lag}"
    c3.category = "statistics"

    return c3


ts_c3_20.__doc__ = \
"""C3 nonlinearity of returns (TS_C3)

Whether the recent past multiplies: the average of
`r[t] * r[t-lag] * r[t-2*lag]` over a rolling window of `length` simple
returns, divided by the cube of those returns' standard deviation.

    TS_C3 = mean(r[t] * r[t-lag] * r[t-2*lag]) / sd(r)^3

The numerator is a third-order autocorrelation: it is zero in expectation
for any series whose sign is symmetric and independent across bars, and
non-zero when the size of a move is predicted by the PRODUCT of the two
before it -- the signature of a nonlinear (in particular time-reversal
asymmetric) process, which is what tsfresh offers `c3` for. The cube of the
standard deviation makes it dimensionless in return units, like a skewness:
the numerator alone is a cube of returns and would move with the volatility
regime.

⚠ The SPREAD is wide and the column is NOT a test statistic. Measured on
synthetic paths only (docs/TsC320Measured.md carries every number): over
2,000 independent 20-return windows of iid gaussian returns, whose
population value is exactly 0, the column's median is 0.0035 (mean 0.0056,
sd 0.2185, p10 -0.2602, p90 0.2725, positive on 50.90%, finite on all
2,000) -- centred, but +-0.26 at the deciles, so one reading of 0.2 says
very little. The ordering does hold: on 1,500-bar paths whose LOG returns
are `rlog[t] = eps[t] + a * eps[t-1] * eps[t-2] / sigma`, whose population
third moment `E[rlog_t rlog_{t-1} rlog_{t-2}]` is `a * sigma^3` and whose
implied standardised value is `a / (1 + a^2)^1.5` = 0.3578 at a = +0.5
(arithmetic, not measured), the median is 0.2442 at a = +0.5, 0.0077 at
a = 0 and -0.2550 at a = -0.5. The LEVEL is shrunk toward zero by a
20-bar window and grows with it -- measured on a 20,000-bar path at
a = +0.5: median 0.2748 / 0.3390 / 0.3755 / 0.3977 at length
20 / 60 / 200 / 1000 -- so only the ORDERING is claimed; a deterministic
path
whose returns alternate between a large up and a small down move reads a
median of -0.2487. It is NOT drift-invariant -- drift moves the returns
themselves, and the numerator is not demeaned: Spearman 0.8013 and max
|difference| 0.8121 against the same walk given +0.004 of log drift a bar.

Source: tsfresh feature_calculators (MIT), `c3`, as the formula is stated
by PandasTa issue #88: `c3(x, lag=1) = mean(x[t]*x[t-1]*x[t-2]) on 20
returns`, in the scale-free form of the screen prototype
`docs/issues/screen/ind_screen.py` candidate `ts_c3_20` (local to the
owner's machine), `sdiv(mean(r * delay(r,1) * delay(r,2), 18), std(r,20)**3)`.
⚠ tsfresh is NOT installed in this worktree and web access is unavailable,
so the formula under test is the issue's line, not a read of tsfresh's own
code; anything tsfresh does that the issue's line does not say (its
behaviour when the window is shorter than `2*lag`, whether it demeans the
series first -- it does not demean in the stated form) is unverified here.
The 20 and the `lag=1` are the issue's own parameters.

Four readings the formula's wording leaves open, decided and priced in
docs/TsC320Measured.md rather than assumed (each number from the same
1,500-bar walk, port against variant):
* The divisor is the SAMPLE standard deviation (`ddof=1`), the prototype's.
  The population convention (`ddof=0`) multiplies every value by
  `((length-1)/length)^-1.5` = 1.079977 at `length=20` -- a STRICT
  rescaling (measured: `port * 1.079977` matches it to 5.6e-16), so max
  |difference| 0.0616 and 0 of 1,480 bars bit-equal, but Spearman 1.000000.
  Invisible to anything ranking the column.
* The numerator averages the `length - 2*lag` triples whose three factors
  all lie inside the window, so the column reads exactly `length + 1`
  closes. Letting every triple keep a full `length`-wide mean reaches
  `2*lag` bars further back (first value at bar 22 rather than 20) and is a
  different column: max |difference| 0.9937, Spearman 0.9201.
* The returns are simple (`close/close.shift(1) - 1`), the prototype's
  `ret`. Log returns are a different column, though a close one: max
  |difference| 0.0181, Spearman 0.999842.
* The divisor's window is the same `length` returns as the numerator's, not
  the `length - 2*lag` returns the triples span: max |difference| 0.6252,
  Spearman 0.994954.
A fifth decision, the NaN rule, is priced on 300-bar geometric ladders
rather than on that walk, because a walk never reaches it:
* A window with no volatility to divide by is NaN, not 0: there is no
  standardised value to report. The guard is `sd > 9.09e-13` rather than
  `sd != 0`, because the returns of an exactly geometric path are
  mathematically constant but vary at rounding level in float64, and an
  unguarded division then reports the ratio of two roundings. Measured: a
  1%-a-bar ladder fires 0 of 300 bars guarded and 280 unguarded, the
  unguarded values reaching 8.0e+41 (3.3e+47 on an exact x1.5 ladder) --
  wild rather than plausible, but the prototype's `sdiv` keeps them because
  they are finite. What is measured about the floor is this: on a walk and
  on a tick-rounded walk it changes neither a NaN flag nor a value (280 of
  300 bars fire on each, identical to the unguarded form), and it stops
  reading variation at about 1e-12 of relative return DISPERSION. The floor
  bounds `sd(r)`, not `|r|`, and the two are not the same comparison -- a
  tick grid quantises the return level at `tick / price` but the dispersion
  of consecutive returns at about `(tick / price)^2`. On a MONOTONE
  one-tick-per-bar path (measured): price 50 with a 0.01 tick has `|r|`
  1.9e-4 and `sd(r)` 2.1e-7, so it fires 280 of 300 bars; price 1e6 with a
  0.001 tick has `|r|` 1.0e-9 and `sd(r)` 1.1e-16, so it fires 0 -- which
  is the right answer, because a window whose returns are that nearly
  constant has no volatility to standardise by.

Causal: bar T reads closes T - length .. T, measured by a
future-perturbation sweep at `(length, lag)` = (20, 1), (20, 9) and (60, 1).
Scale-free: every input is a price ratio, and `8a / 8b` is the same double
as `a / b`, so the column is bit-identical under a x8/x64 rescale (1,480 of
1,480 fired bars on each of a walk, a tick-rounded walk and a nonlinear
path at the defaults; on the walk, 1,480 of 1,480 at `lag=9` and 1,440 of
1,440 at `length=60`) and agrees to 1.9e-14
under x10/x3.7 with identical NaN masks. The difference-of-logarithms
spelling of the return is not: at x8 it is bit-equal on 821 of 1,499 bars
where the ratio spelling is bit-equal on all 1,499. NaN on the first
`length` bars, on any window holding a close that is NaN, infinite, zero,
negative or subnormal, and on any window whose `length` returns have
`sd <= 9.09e-13` -- which happens when those returns are constant to
rounding level, either because all `length + 1` closes are identical
(measured: a flat run planted in a walk empties 0 bars at 20 identical
closes and 1 at 21) or because the path is exactly geometric, whose closes
are all distinct (measured: a 1%-a-bar ladder fires 0 of 300 bars).

Calculation:
    Default Inputs:
        length=20, lag=1
    r[t]      = close[t] / close[t-1] - 1
    p[t]      = r[t] * r[t-lag] * r[t-2*lag]
    num[t]    = mean of p over the trailing `length - 2*lag` triples
    sd[t]     = sample standard deviation of r over the trailing `length`
                returns (NaN where sd <= 9.09e-13)
    TS_C3     = num / sd^3

Args:
    close (pd.Series): Series of 'close's
    length (int): Returns per window. At least 4; a smaller or missing value
        falls back to the default. Default: 20
    lag (int): c3's lag. At least 1, and clamped to `(length - 2) // 2` so
        two triples fit (the effective value is the one in the column name).
        A smaller or missing value falls back to the default. Default: 1
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)

Returns:
    pd.Series: TS_C3_{length}_{lag}, a dimensionless third-order moment
"""
