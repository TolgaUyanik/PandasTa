# -*- coding: utf-8 -*-
import numpy as np
from pandas import Series

from pandas_ta.utils import get_offset, verify_series

# The lag is fixed, not a parameter: the column's NAME says lag 1, so a `lag`
# keyword would let a caller emit a `TS_AC1_*` column that is not a lag-1
# autocorrelation. See the docstring.
LAG = 1
# A window of TWO returns is identically -1: with `x = [a, b]` the mean is
# `(a+b)/2`, the only product is `-(a-b)**2/4` and the population variance is
# `(a-b)**2/4`, so the ratio is -1 for every `a != b` (and NaN when they are
# equal). Three returns is the smallest window on which the statistic varies.
MIN_LENGTH = 3
EXTRA_CLOSES = 1  # `length` returns need `length + 1` closes
# A window whose returns vary only at rounding level has no dispersion to
# divide by: the quotient would be the ratio of two roundings. The floor can
# be an absolute constant -- no rolling scale, so no second window to keep
# causal -- because what is floored is the dispersion of DIMENSIONLESS price
# ratios. The same 4096 eps is this fork's existing habit on a dimensionless
# quantity: `statistics/ts_c3_20.py` floors a return standard deviation with
# it, `statistics/ts_binent_20.py` a return range, and
# `statistics/lean_hurst_100.py` floats it against a log price ratio. It is
# spelled on the standard deviation and squared into the variance here so the
# comparison is the same one `ts_c3_20` makes.
NOISE_ULPS = 4096
NOISE_FLOOR = NOISE_ULPS * np.finfo(float).eps  # 9.09e-13, on the sd
VAR_FLOOR = NOISE_FLOOR ** 2                    # 8.27e-25, on the variance


def ts_ac1_60(close, length=None, offset=None, **kwargs):
    """Indicator: lag-1 return autocorrelation (TS_AC1)"""
    # Validate Arguments
    length = int(length) if length and int(length) >= MIN_LENGTH else 60
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
    #
    # Both ends are finite, positive and normal by now, so OVERFLOW is the one
    # float error the ratio can still raise -- 1e-300 followed by 1e50 gives
    # an infinite return. Such a pair is bad data in the same way a NaN close
    # is (there is no return to take), so it is silenced here and dropped on
    # the next line rather than carried into the moments.
    with np.errstate(over="ignore"):
        r = px / px.shift(1) - 1.0
    r = r.where(np.isfinite(r))
    # A return too large for its own square to be SUMMED over a window is not
    # usable data, and dropping it is not a local nicety: pandas accumulates
    # `rolling.var` and `rolling.sum` ONLINE, so an infinite accumulator never
    # leaves the window and every LATER bar comes back NaN too. Measured on a
    # 400-bar walk with one close of 1e-300 at bar 200, whose next return is
    # about 1e+302 and whose square overflows: without this line 199 bars go
    # (201..399, the rest of the frame), with it 60 (201..260) -- see
    # docs/TsAc160Measured.md, Guards.
    #
    # The bound is what makes that locality structural rather than measured on
    # one shape. Every kept return has `r**2 < max/(8*length)`, so writing
    # `B**2` for that ceiling: the window mean is at most `B`, every squared
    # deviation at most `4*B**2`, so `length * var <= 4*length*B**2 < max/2`
    # and the summed squared differences are under `max/2` as well -- each of
    # the three accumulators stays inside half the float range, the halving
    # being headroom for the accumulation's own rounding. The ceiling it puts
    # on a return is 6.12e+152, which nothing a market can produce reaches. A
    # comparison against NaN or inf is False, so this test also rejects a
    # non-finite square.
    with np.errstate(over="ignore"):
        square = np.square(r.to_numpy())
    r = r.where(square < np.finfo(float).max / (8 * length))

    rolling = r.rolling(length, min_periods=length)
    mean = rolling.mean()
    # The POPULATION variance (`ddof=0`), which is what `numpy.var` computes
    # in the source formula's divisor.
    var = rolling.var(ddof=0)
    # The numerator, `sum (x[i] - m) * (x[i-1] - m)` over the `length - 1`
    # pairs inside the window, rewritten so that nothing in it is a difference
    # of two large numbers. From `2*u*v = u**2 + v**2 - (u - v)**2` with
    # `u = x[i] - m` and `v = x[i-1] - m`, whose difference `u - v` is
    # `x[i] - x[i-1]` and so does not contain `m` at all:
    #
    #   sum u*v = length*var - (oldest - m)**2 / 2 - (newest - m)**2 / 2
    #                        - sum (x[i] - x[i-1])**2 / 2
    #
    # because the first sum of squares counts every deviation twice except the
    # window's two end ones. The plain expansion
    # `sum x[i]*x[i-1] - m*((length+1)*m - oldest - newest)` is algebraically
    # the same and loses the statistic when a window's mean dwarfs its
    # dispersion: measured against an exact rational oracle on a path with
    # `|mean| / sd = 1e5`, this spelling is 2.1e-10 out and that one 4.1e-06
    # (docs/TsAc160Measured.md, A4). Nothing here is a difference of two
    # numbers much larger than the result: `r.diff()` subtracts two returns,
    # whose own size is the dispersion the answer is scaled by, and the two
    # end deviations are single terms of a sum of `length` of them.
    gap = Series(np.square(r.diff().to_numpy()), index=r.index)
    gap = gap.rolling(length - LAG, min_periods=length - LAG).sum()
    oldest = r.shift(length - 1)
    numerator = length * var \
        - 0.5 * ((oldest - mean) ** 2 + (r - mean) ** 2 + gap)

    # A window whose two accumulators disagree with its own extrema is not
    # reported. `rolling.var` and `rolling.sum` are ONLINE -- a value is added
    # when it enters the window and subtracted when it leaves -- so a single
    # enormous return leaves a residue in both long after it has left, and
    # that residue is a plausible-looking number rather than a NaN. The two
    # tests here are exact algebra on the window's range `s = max - min`,
    # which `rolling.max`/`rolling.min` compute by a deque and therefore
    # LOCALLY: a population variance cannot exceed `(s/2)**2` (equality at
    # equal mass on the two ends, which an alternating window reaches), and
    # `length - 1` squared successive differences cannot exceed
    # `(length - 1) * s**2`. The slack is the same 4096 eps as the floor
    # below, relative. Measured: without this, one planted return of 1e+8
    # (a decimal-point error in a feed, which is well inside the overflow
    # bound above) moves 139 bars of a 400-bar frame by up to 1.28 with no
    # NaN to mark them; with it those bars are NaN
    # (docs/TsAc160Measured.md, Guards).
    span = rolling.max() - rolling.min()
    bound = span * span
    trusted = (var <= 0.25 * bound * (1.0 + NOISE_FLOOR)) \
        & (gap <= (length - LAG) * bound * (1.0 + NOISE_FLOOR))

    # The source divides by `(length - lag) * var`, not by `length * var`: the
    # column is the biased autocorrelation scaled up by `length/(length-lag)`,
    # which is 1.016949 at the default (see the docstring).
    #
    # Flooring the divisor first means no zero and no rounding-level value
    # ever reaches the division, so there is nothing for an `errstate` to
    # suppress and no infinity to clean up afterwards: the quotient is bounded
    # by `length/(length - lag)` in exact arithmetic, and by `length` under
    # any rounding of the numerator, because a single squared deviation is at
    # most `length * var`.
    tsac1 = numerator / ((length - LAG)
                         * var.where((var > VAR_FLOOR) & trusted))

    # Offset
    if offset != 0:
        tsac1 = tsac1.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        tsac1.fillna(kwargs["fillna"], inplace=True)

    # Name and Categorize it
    tsac1.name = f"TS_AC1_{length}"
    tsac1.category = "statistics"

    return tsac1


ts_ac1_60.__doc__ = \
"""Lag-1 return autocorrelation (TS_AC1)

Whether the last `length` returns came in runs or in alternations: the lag-1
autocorrelation of the trailing `length` simple returns, in tsfresh's
normalisation.

    x       = the window's `length` simple returns
    m, v    = their mean and their POPULATION variance (`ddof=0`)
    TS_AC1  = sum over the length-1 pairs of (x[i] - m)*(x[i-1] - m)
              / ((length - 1) * v)

⚠ **It is NOT volatility, and not the direction either.** It is invariant to
any AFFINE map of the returns, which is the strongest of its properties and
the one a consumer should read first: doubling every return, halving it, or
adding a constant drift to every one leaves the column where it was
(Spearman 1.000000 and max |difference| 4.0e-15 at returns x2, 9.6e-15 at
x0.5 and 2.7e-14 at +0.004 of log drift a bar, measured on a 1,500-bar walk,
with identical NaN masks). Against the SAME window's statistics on that
walk: Spearman -0.0965 against the window's standard deviation, 0.0560
against its mean return and -0.0073 against the absolute mean return. Read
it as "did these moves alternate or continue", nothing else.

⚠ **It is BOUNDED, and both ends are reachable.** The normalisation is
`length / (length - 1)` times the usual biased estimator, which is itself in
[-1, 1], so the column lives inside +-1.016949 at `length` 60 -- and the
reachable ends are slightly tighter than that, because the window is demeaned
first. At `length` 60 they are **[-1.015601, +1.011559]**, derived as the
extreme eigenvalues of the lag-1 product form restricted to the demeaned
subspace and attained by the module on the matching eigenvector window to
6.7e-16 and 8.9e-16. At `length` 4 the range is [-1.078689, +0.412023] and at
`length` 10 [-1.066103, +0.934726]: the window is too short for a +1 to be
reachable. One window has an EXACT value: any window whose returns alternate
between two values in equal counts reads exactly **-1.0** for every `length`
(derived: every one of the `length - 1` products is `-d**2` and the variance
is `d**2`; measured bit-exactly on `close = [1, 2, 1, 2, 1]` at `length` 4,
and to 5.4e-15 on a 1,500-bar alternating frame at the default, where the
closes are built by a product and the returns are no longer exactly +-d).

⚠ **A reading near zero is the usual case, and the spread is wide.** For iid
returns the population value is 0, and over 2,000 independent 60-return
windows the column has median -0.0106, mean -0.0134, sd 0.1222, p10 -0.1797,
p90 0.1418 and is positive on 45.70% (finite on 2,000 of 2,000). The small
negative centre is this estimator's own small-sample bias, about
`-1/(length - 1)` = -0.0169, and the spread is about `1/sqrt(length)` =
0.1291 (both arithmetic, not measured). So a single reading of +-0.1 says
almost nothing; what the column orders is the regime. On paths whose LOG
returns are an AR(1) with coefficient `phi`, whose population lag-1
autocorrelation is exactly `phi`, the medians are 0.5030 / 0.2699 / 0.0283 /
-0.2180 / -0.4683 at `phi` = +0.50 / +0.25 / 0 / -0.25 / -0.50. The LEVEL is
shrunk by a 60-bar window and grows with it (measured on a 20,000-bar
`phi` = +0.5 path: median 0.3797 / 0.4655 / 0.4871 / 0.4975 at `length`
20 / 60 / 200 / 1000).

⚠ **It needs 61 closes and it is a slow state.** Two consecutive windows
share 59 of their 60 returns, so the column autocorrelates at 0.9760 at lag
1, 0.2813 at lag 30 and -0.2129 at lag 60 (measured on a walk). It is not an
event flag.

Source: tsfresh feature_calculators (MIT), `autocorrelation`, as the formula
is stated by PandasTa issue #94: `autocorrelation(x, lag=1) on 60 returns`.
⚠ tsfresh is NOT installed in this worktree and web access is unavailable, so
the formula under test is the issue's line plus the published definition of
`feature_calculators.autocorrelation` -- the window's single mean, the
population variance, and the `(len(x) - lag)` denominator -- and not a read
of tsfresh's own code; anything tsfresh does that those do not state (how it
treats NaNs, what it returns for a series shorter than `lag`) is unverified
here. The 60 and the `lag = 1` are the issue's own parameters.

⚠ **This column is NOT the screen prototype**, and the difference is
visible. Issue #94's prototype
(`docs/issues/screen/ind_screen.py` candidate `ts_ac1_60`, local to the
owner's machine) is `corr(r, delay(r, 1), 60)` -- a PEARSON correlation of
two 60-pair slices, with two means and two standard deviations, reading 61
returns and so 62 closes. The issue's own "Gates owed" says Gate A starts
from the source formula and not from the prototype, so the source formula is
what ships here. Measured against the prototype on a 1,500-bar walk:
Spearman 0.988839, max |difference| 0.1013, bit-equal on 0 of 1,439 bars,
and the first fired bar is 60 here against the prototype's 61. The screen's
Gate E figures (max |rho| 0.2534 vs `mad_pct`, n = 393,420) were therefore
measured on a DIFFERENT column, and the launcher's Gate E run on this module
is the number that decides ship or revert. The prototype was read, retyped
and imported: the retype and the owner's own registry entry agree bit-for-bit
on 1,439 of 1,439 bars.

The arithmetic is checked independently rather than trusted. The source
formula applied window by window with `sliding_window_view` -- no pandas
rolling anywhere, so no shared window machinery -- agrees with this column to
4.9e-15 on a walk, 2.8e-15 tick-rounded and 2.1e-15 on an AR(1) path, at
Spearman 1.000000 with identical NaN masks. Against an EXACT rational oracle
in `fractions.Fraction` (every close is a rational, so the whole statistic is
one) the module is 3.1e-15 out on a walk and 1.0e-15 tick-rounded, where a
`math.fsum` scalar loop is 1.0e-15 and 1.6e-15: the same order, with no
spelling systematically better.

Four readings the wording leaves open, decided and priced in
docs/TsAc160Measured.md (A6) rather than assumed, each on the same walk:
* The returns are SIMPLE (`close/close.shift(1) - 1`), the prototype's `ret`.
  Log returns are a different column, though a close one: Spearman 0.999883,
  max |difference| 5.5e-03.
* `length` is 60 RETURNS, so 61 closes, and the first value lands at bar 60.
  Rejected: 60 CLOSES, i.e. 59 returns (Spearman 0.989106, max |difference|
  0.1111) -- the off-by-one a reader makes, priced so it is not re-argued.
* The `(length - lag)` denominator and the POPULATION variance, both the
  source's. The two alternatives collapse into one column: dividing by
  `length * v` instead, or keeping `length - lag` but using the SAMPLE
  variance, both multiply this column by exactly `59/60` (measured:
  `port * 0.983333` reproduces each to 4.8e-15, and the two agree with each
  other to 5.6e-17 at 1,351 of 1,440 bars bit-equal). Spearman 1.000000, so
  a rank miner cannot see the choice; a rule with a threshold can, by up to
  4.7e-03.
* The window's SINGLE mean and variance, the source's, rather than a Pearson
  correlation of the two lagged slices over the same 60 returns
  (`pandas.Series.autocorr`): Spearman 0.999901, max |difference| 1.4e-02.
  That variant is the prototype's normalisation on this port's window, and it
  is the closer half of the gap to the prototype.

`lag` is deliberately NOT a parameter. The issue fixes it at 1 and the
column's NAME says so, so a `lag` keyword would let a caller emit a
`TS_AC1_*` column that is not a lag-1 autocorrelation.

A window with no dispersion to divide by is NaN, not a number, and the floor
is this fork's `4096 eps` rather than the source's. tsfresh's own guard is
`np.isclose(var, 0)`, which with numpy's default `atol` empties every window
whose return variance is below 1e-8 -- i.e. whose return sd is below 1e-4.
Measured on 300-bar frames: that guard reports on 0 of 240 windows of a
walk with sigma = 1e-6 (variance 6.0e-13) and 0 of 240 at sigma = 1e-9, where
this column reports on all 240 and reads a perfectly ordinary +-0.27. Both
guards agree on the two degenerate frames -- a flat frame and a 1%-a-bar
geometric ladder (whose returns are mathematically constant but vary at
rounding level in float64) report on 0 of 240 windows under either, while an
UNGUARDED spelling reports on 240 of the ladder's, up to 0.8328, out of
nothing but rounding.

Causal: bar T reads closes T - length .. T, measured by a
future-perturbation sweep -- 0 of 35 offsets on each of a walk, a
tick-rounded walk and an AR(1) path.
Scale-free: every input is a price ratio, and `8a / 8b` is the same double as
`a / b`, so the column is bit-identical under a x8/x64 rescale of price
(1,440 of 1,440 fired bars on each of those three frames, and 1,497 / 1,480 /
1,250 at `length` 3 / 20 / 250 on the walk). x10 and x3.7 are not
bit-identical -- they perturb the returns in their last bits -- but the NaN
masks match exactly and the values agree to 8.8e-15 at Spearman 1.000000,
which is the Gate D tolerance reading. The difference-of-logarithms spelling
of the return would not be: at x8 it is bit-equal on 821 of 1,499 bars where
the ratio spelling is bit-equal on all 1,499.
NaN on the first `length` bars; on any window holding a close that is NaN,
infinite, zero, negative or subnormal (a bad close empties the
`length + 1` = 61 windows it sits in, because it spoils two returns --
measured, with 0 earlier bars moved); on any window holding a close pair
whose ratio OVERFLOWS or whose return's SQUARE does; on any window whose
`length` returns have a population variance of 8.27e-25 or less (an sd of
9.09e-13 or less); and on any window whose variance or summed squared
differences exceed what its own range allows, which is the accumulator test
below.

⚠ **Two numerical limits, measured rather than assumed.**
* `rolling.var` and `rolling.sum` are ONLINE in pandas, so a single enormous
  return leaves a residue in both long after it has left the window. The
  trust test above (an exact bound from the window's own range, computed by
  a deque and therefore local) turns the gross case into NaN: with one
  planted return of 1e+8 in a 400-bar walk, the 139 bars after it has left
  every window are NaN here and sit up to **1.280** away from a per-window
  oracle without the test. It is not a cure for the whole range: the same
  bars are 1.3e-09 out for a planted return of 1e+2, 3.3e-06 at 1e+4 and
  8.5e-03 at 1e+6, none of which the test catches, because the variance
  stays inside its bound. On seven clean frames -- walk, tick-rounded,
  AR(1) at +-0.5, an alternating frame (which attains the bound EXACTLY, at a
  measured ratio of 1.000000000000), a sigma = 1e-6 walk and a fine-tick
  ladder -- it costs 0 bars.
* The numerator is spelled to avoid subtracting the window mean from a raw
  product sum. On a path whose returns have `|mean| / sd` = 1e5 the module is
  2.1e-10 from the exact rational value, where the `math.fsum` loop and the
  window-by-window oracle are 1.7e-10 and the plain raw-sum expansion is
  **4.1e-06**, about 2.3e+04 times worse. That is the spelling's whole
  justification, and it is a measurement on one shape rather than a bound.

Cost: five O(n) passes (mean, variance, the squared-difference sum and the
two extrema) and no allocation that grows with `length` -- the traced peak is
38.8 MB on 400,000 bars at each of `length` 3, 20, 60 and 250, in each of
three runs, and the call takes roughly 70-90 ms there (the three runs gave
71/73/73/72, 73/80/88/90 and 71/72/72/73 ms, so the times are a band and not
four numbers). The trust test's two extrema cost about 7 ms of that in two
paired runs (73 against 66 ms, then 71 against 64 ms, same code path, flag
flipped). The window-by-window oracle this was checked against is 292-300 ms
and peaks at 406.4 MB on the same input -- that peak reproduced exactly --
which is why it lives in docs/measure_ts_ac1_60.py and not here.

Calculation:
    Default Inputs:
        length=60
    r[t]       = close[t] / close[t-1] - 1
    m, v       = mean and population variance of the trailing `length` r
    TS_AC1[T]  = sum((r[i] - m) * (r[i-1] - m)) / ((length - 1) * v)
                 over the `length - 1` pairs inside the window, NaN where
                 v <= 8.27e-25 or the accumulator test fails

Args:
    close (pd.Series): Series of 'close's
    length (int): Returns per window. At least 3 -- a window of two returns
        is identically -1 -- so a smaller or missing value falls back to the
        default. Default: 60
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)

Returns:
    pd.Series: TS_AC1_{length}, dimensionless, in [-1.015601, 1.011559] at
        length 60
"""
