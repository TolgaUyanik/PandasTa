# -*- coding: utf-8 -*-
import numpy as np
from pandas import Series

from pandas_ta.utils import get_offset, verify_series

MIN_LAG = 1
# A window needs at least two returns beyond its longest lag. At
# `length = maxlag + 1` the longest lag contributes a single product, and the
# `maxlag = 1`, `length = 2` corner is identically -1 (`statistics/ts_ac1_60.py`
# derives that: with `x = [a, b]` the only product is `-(a-b)**2/4` and the
# population variance is `(a-b)**2/4`). One rule rules both out, and it makes
# `MIN_LENGTH` here the 3 that `ts_ac1_60` uses.
MIN_LENGTH = MIN_LAG + 2
EXTRA_CLOSES = 1  # `length` returns need `length + 1` closes
# A window whose returns vary only at rounding level has no dispersion to
# divide by: the quotient would be the ratio of two roundings. The floor can
# be an absolute constant -- no rolling scale, so no second window to keep
# causal -- because what is floored is the dispersion of DIMENSIONLESS price
# ratios. The same 4096 eps is this fork's existing habit on a dimensionless
# quantity: `statistics/ts_ac1_60.py` floors exactly this variance with it,
# `statistics/ts_c3_20.py` a return standard deviation, and
# `statistics/ts_binent_20.py` a return range. It is spelled on the standard
# deviation and squared into the variance here so the comparison is the same
# one `ts_ac1_60` makes.
NOISE_ULPS = 4096
NOISE_FLOOR = NOISE_ULPS * np.finfo(float).eps  # 9.09e-13, on the sd
VAR_FLOOR = NOISE_FLOOR ** 2                    # 8.27e-25, on the variance


def ts_aggac_60(close, length=None, maxlag=None, offset=None, **kwargs):
    """Indicator: mean return autocorrelation over lags 1..maxlag (TS_AGGAC)"""
    # Validate Arguments
    length = int(length) if length and int(length) >= MIN_LENGTH else 60
    maxlag = int(maxlag) if maxlag and int(maxlag) >= MIN_LAG else 10
    # Keep at least two returns beyond the longest lag. The effective maxlag
    # is the one in the column name.
    maxlag = min(maxlag, length - 2)
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
    # float error the ratio can still raise -- 1e-300 followed by 1e+300 gives
    # an infinite return. Such a pair is bad data in the same way a NaN close
    # is (there is no return to take); it is silenced here and dropped by the
    # square bound below, which rejects a non-finite return along with a
    # merely enormous one. `ts_ac1_60` spells an extra
    # `r.where(np.isfinite(r))` between the two; this module does not, because
    # measuring it showed it cannot change an output -- see the Guards section
    # of docs/TsAggac60Measured.md.
    with np.errstate(over="ignore"):
        r = px / px.shift(1) - 1.0
    # A return too large for its own square to be SUMMED over a window is not
    # usable data, and dropping it is not a local nicety: pandas accumulates
    # `rolling.var` and `rolling.sum` ONLINE, so an infinite accumulator never
    # leaves the window and every LATER bar comes back NaN too.
    #
    # The bound is what makes that locality structural rather than measured on
    # one shape. Every kept return has `r**2 < max/(8*length)`, so writing
    # `B**2` for that ceiling: the window mean is at most `B`, every squared
    # deviation at most `4*B**2`, so `length * var <= 4*length*B**2 < max/2`;
    # every lag-`k` difference `r[i] - r[i-k]` is at most `2*B`, so each of the
    # `maxlag` summed squared differences is under `length * 4*B**2 < max/2`
    # as well, and so is each partial sum of squared deviations. Every
    # accumulator stays inside half the float range, the halving being headroom
    # for the accumulation's own rounding. The ceiling it puts on a return is
    # 6.12e+152 at `length` 60, which nothing a market can produce reaches. A
    # comparison against NaN or inf is False, so this test also rejects a
    # non-finite square.
    with np.errstate(over="ignore"):
        square = np.square(r.to_numpy())
    r = r.where(square < np.finfo(float).max / (8 * length))

    rolling = r.rolling(length, min_periods=length)
    mean = rolling.mean()
    # The POPULATION variance (`ddof=0`), which is what `numpy.var` computes
    # in the source formula's divisor -- ONE variance for the whole window,
    # shared by every lag, which is what makes this an autocorrelation rather
    # than ten separate correlations.
    var = rolling.var(ddof=0)
    # The window's range, computed by a deque and therefore LOCALLY. Both
    # halves of the trust test below are exact algebra on it.
    span = rolling.max() - rolling.min()
    bound = span * span
    # A population variance cannot exceed `(s/2)**2` (equality at equal mass on
    # the two ends, which an alternating window reaches).
    trusted = var <= 0.25 * bound * (1.0 + NOISE_FLOOR)

    # The numerator of lag `k`, `sum (x[i] - m) * (x[i-k] - m)` over the
    # `length - k` pairs inside the window, rewritten so that nothing in it is
    # a difference of two large numbers. From `2*u*v = u**2 + v**2 - (u - v)**2`
    # with `u = x[i] - m` and `v = x[i-k] - m`, whose difference `u - v` is
    # `x[i] - x[i-k]` and so does not contain `m` at all:
    #
    #   sum u*v = length*var - head[k]/2 - tail[k]/2 - gap[k]/2
    #
    # where `head[k]` is the squared deviations of the `k` OLDEST returns in
    # the window (the ones with no partner `k` bars EARLIER, so they are
    # absent from the later-member sum), `tail[k]` the `k` NEWEST (no partner
    # `k` bars LATER, so absent from the earlier-member sum), and `gap[k]` the
    # sum of `(x[i] - x[i-k])**2` over the `length - k` lag-`k` pairs. The
    # plain expansion `sum x[i]*x[i-k] - m*(...)` is algebraically the same and
    # loses the statistic when a window's mean dwarfs its dispersion (measured
    # against an exact rational oracle in docs/TsAggac60Measured.md, A4).
    # Nothing here is a difference of two numbers much larger than the result:
    # `r.diff(k)` subtracts two returns, whose own size is the dispersion the
    # answer is scaled by, and `head`/`tail` are partial sums of the same
    # `length` squared deviations that `length * var` totals.
    #
    # `head` and `tail` grow by one squared deviation per lag, so the loop is
    # `maxlag` passes and not `maxlag**2`. Each deviation is taken against the
    # mean of the window it belongs to -- `mean` is the rolling mean at the
    # window's LAST bar, so the return is shifted into place and the mean is
    # not, which is the opposite of squaring `r - mean` once and shifting that.
    head = tail = 0.0
    weighted = 0.0
    for k in range(1, maxlag + 1):
        # the k newest deviations, then the k oldest
        tail = tail + (r.shift(k - 1) - mean) ** 2
        head = head + (r.shift(length - k) - mean) ** 2
        gap = Series(np.square(r.diff(k).to_numpy()), index=r.index)
        gap = gap.rolling(length - k, min_periods=length - k).sum()
        # `length - k` squared lag-`k` differences cannot exceed
        # `(length - k) * span**2`.
        trusted = trusted & (gap <= (length - k) * bound * (1.0 + NOISE_FLOOR))
        # The source divides lag `k` by `(length - k) * var`, not by
        # `length * var`: each term is the biased autocorrelation scaled up by
        # `length/(length-k)`. Dividing by the shared `var` once, at the end,
        # is one rounding instead of `maxlag` of them.
        weighted = weighted \
            + (length * var - 0.5 * (head + tail + gap)) / (length - k)

    # A window whose accumulators disagree with its own extrema is not
    # reported. `rolling.var` and `rolling.sum` are ONLINE -- a value is added
    # when it enters the window and subtracted when it leaves -- so a single
    # enormous return leaves a residue in both long after it has left, and that
    # residue is a plausible-looking number rather than a NaN. The slack is the
    # same 4096 eps as the floor, relative. Measured: without this, one planted
    # return of 1e+8 (a decimal-point error in a feed, which is well inside the
    # overflow bound above) moves bars of a 400-bar frame with no NaN to mark
    # them; with it those bars are NaN (docs/TsAggac60Measured.md, Guards).
    #
    # Flooring the divisor first means no zero and no rounding-level value ever
    # reaches the division, so there is nothing for an `errstate` to suppress
    # and no infinity to clean up afterwards.
    tsaggac = weighted / (maxlag * var.where((var > VAR_FLOOR) & trusted))

    # Offset
    if offset != 0:
        tsaggac = tsaggac.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        tsaggac.fillna(kwargs["fillna"], inplace=True)

    # Name and Categorize it
    tsaggac.name = f"TS_AGGAC_{length}_{maxlag}"
    tsaggac.category = "statistics"

    return tsaggac


ts_aggac_60.__doc__ = \
"""Mean return autocorrelation over lags 1..maxlag (TS_AGGAC)

How much the last `length` returns repeat themselves over a RANGE of
horizons rather than at one: the lag-1..lag-`maxlag` autocorrelations of the
trailing `length` simple returns, in tsfresh's normalisation, averaged.

    x        = the window's `length` simple returns
    m, v     = their mean and their POPULATION variance (`ddof=0`)
    AC[k]    = sum over the length-k pairs of (x[i] - m)*(x[i-k] - m)
               / ((length - k) * v)
    TS_AGGAC = (AC[1] + ... + AC[maxlag]) / maxlag

⚠ **It is NOT volatility, and not the direction either.** It is invariant to
any AFFINE map of the returns, which is the strongest of its properties and
the one a consumer should read first: doubling every return, halving it, or
adding a constant drift to every one leaves the column where it was
(Spearman 1.000000 and max |difference| 4.9e-15 at returns x2, 5.0e-15 at
x0.5 and 1.3e-14 at +0.004 of log drift a bar, measured on a 1,500-bar walk,
with identical NaN masks). Against the SAME window's statistics on that
walk: Spearman -0.0069 against the window's standard deviation, 0.1132
against its mean return and -0.1357 against the absolute mean return.

⚠ **It is BOUNDED, and the two ends are NOT symmetric.** At `length` 60 and
`maxlag` 10 the reachable range is **[-0.310043, +0.915798]** -- the column
is `length` times a Rayleigh quotient of the lag-weighted product form
restricted to the demeaned subspace, so its extremes are that form's extreme
eigenvalues, and the module attains both on the matching eigenvector window
to 6.7e-16. A window cannot be strongly negative at ten lags at once (a path
that alternates is negative at the odd lags and POSITIVE at the even ones),
which is why the floor is three times nearer zero than the ceiling. At
`length` 20 the range is [-0.292703, +0.259700] and at `length` 12
[-0.483955, +0.185127]; at `maxlag` 1 it is `ts_ac1_60`'s own
[-1.015601, +1.011559]. The looser Cauchy-Schwarz ceiling, `(length/maxlag) *
sum 1/(length-k)`, is 1.103990 at the default and is not attained.
One family of windows has an EXACT value: any window whose returns alternate
between two values in equal counts has `AC[k] = (-1)**k`, so it reads
exactly **0** for every EVEN `maxlag` and `-1/maxlag` for every odd one
(measured bit-exactly on `close = [1, 2, 1, 2, ...]` at `length` 60, 20 of 20
fired bars at `maxlag` 2 and 10; and to 3.7e-16 on a 1,500-bar alternating
frame built by a product, where the returns are no longer exactly +-d).

⚠ **A reading near zero is the usual case, and the spread is NARROW.** For
iid returns the population value is 0, and over 2,000 independent 60-return
windows the column has median -0.0227, mean -0.0182, sd 0.0351, p10 -0.0577,
p90 0.0299 and is positive on 25.50% (finite on 2,000 of 2,000). On the SAME
2,000 paths `ts_ac1_60` reads median -0.0106, sd 0.1222 and positive 45.70%:
averaging ten lags shrinks the spread to 0.287 of the lag-1 column's and
roughly DOUBLES the negative centre (2.14 times its median), because each lag
carries its own small-sample bias of about `-1/(length - 1)` and they do not
cancel. A reading of 0 is therefore mildly POSITIVE evidence of
autocorrelation, not neutral. On paths whose LOG
returns are an AR(1) with coefficient `phi`, whose population lag-`k`
autocorrelation is exactly `phi**k`, the medians are 0.0448 / 0.0044 /
-0.0161 / -0.0286 / -0.0362 at `phi` = +0.50 / +0.25 / 0 / -0.25 / -0.50,
against a population mean over the ten lags of +0.0999 / +0.0333 / 0 /
-0.0200 / -0.0333.

⚠ **At a short `length` the bias swamps the signal, and it can flip the
SIGN.** The high lags are estimated from few pairs, so the bias grows as
`length` approaches `2*maxlag`: on iid windows the median is -0.0061 at
`length` 200, -0.0220 at 60, -0.0424 at 30, -0.0537 at 20 and -0.0772 at 12.
On a 20,000-bar AR(1) path with `phi` = +0.50, whose population value is
+0.0999, the median reads 0.1054 / 0.0871 / 0.0431 at `length`
1000 / 200 / 60 and **-0.0514** at `length` 20 -- negative, for a positively
autocorrelated path. Do not compare readings across lengths, and do not run
this column at a `length` near `2*maxlag`.

⚠ **It is BLIND to a seasonality whose period divides `maxlag`.** The lag-`k`
autocorrelations of an exactly periodic window sum to zero over any whole
cycle of rotations, so averaging lags 1..10 cancels a period of 2, 5 or 10
almost exactly: on 1,500-bar paths whose returns repeat with those periods
the median is +0.000000 / +0.000008 / +0.000067, where the lag-1 column alone
reads -1.0000 / -0.5872 / -0.5674. A period that does NOT divide 10 survives,
but barely: -0.050649 at period 3 and -0.050173 at period 7. This is a
property of the `f_agg='mean'` aggregation the issue specifies, not a defect
of the port.

⚠ **It needs 61 closes and it is a slow state.** Two consecutive windows
share 59 of their 60 returns, so the column autocorrelates at 0.9665 at lag
1, 0.3686 at lag 30 and 0.0683 at lag 60 (measured on a walk). It is not an
event flag.

Source: tsfresh feature_calculators (MIT), `agg_autocorrelation`, as the
formula is stated by PandasTa issue #96:
`agg_autocorrelation(f_agg='mean', maxlag=10) on 60 returns`.
⚠ tsfresh is NOT installed in this worktree and web access is unavailable, so
the formula under test is the issue's line plus the published definitions of
`feature_calculators.agg_autocorrelation` and the
`statsmodels.tsa.stattools.acf(x, adjusted=True)` it calls -- and not a read
of tsfresh's own code; anything tsfresh does that those do not state (how it
treats NaNs, which `fft` branch it takes above 1,250 points) is unverified
here. The 60 and the `maxlag = 10` are the issue's own parameters.
That `acf` detour is the one place the two published definitions could have
disagreed, so it is MEASURED and not assumed: `acovf(adjusted=True)[k]`
divides by `length - k` and `acovf[0]` by `length`, so the quotient
`acovf[k]/acovf[0]` is `sum / ((length-k) * v)` -- which is what
`feature_calculators.autocorrelation(x, lag=k)` spells directly. Over 200
random 60-point windows the mean of the ten `autocorrelation(x, k)` and
`agg_autocorrelation` agree to 3.5e-17. statsmodels IS installed in this
worktree, and the retyped adjusted `acf` used above reproduces
`statsmodels.tsa.stattools.acf(x, adjusted=True, fft=False)` BIT-EXACTLY on
that window; the module is 5.7e-15 from the adjusted-acf path applied window
by window on a walk, 2.5e-15 tick-rounded and 3.4e-15 on an AR(1) path.

⚠ **This column is NOT the screen prototype**, and the difference is
visible. Issue #96's prototype (`docs/issues/screen/ind_screen.py` candidate
`ts_aggac_60`, local to the owner's machine) is
`sum(corr(r, delay(r, k), 60) for k in range(1, 11)) / 10` -- ten PEARSON
correlations of two 60-pair slices, each with two means and two standard
deviations, the lag-10 term reading 70 returns and so 71 closes. The issue's
own "Gates owed" says Gate A starts from the source formula and not from the
prototype, so the source formula is what ships here. Measured against the
prototype on a 1,500-bar walk: Spearman 0.902932, max |difference| 4.7e-02,
bit-equal on 0 of 1,430 bars, and the first fired bar is 60 here against the
prototype's 70. The screen's Gate E figures (max |rho| 0.2815 vs `mad_pct`,
n = 392,619) were therefore measured on a DIFFERENT column, and the
launcher's Gate E run on this module is the number that decides ship or
revert. The prototype was read, retyped and imported: the retype and the
owner's own registry entry agree bit-for-bit on 1,430 of 1,430 bars.

⚠ **Disclosed because Gate E cannot see it: this fork already ships the
lag-1 term alone.** Gate E's 687 comparators hold no pandas_ta port, so the
in-fork overlap is measured here instead, against the seven `Category`
modules whose value is a function of the same series at a fixed offset --
enumerated by hand from `pandas_ta/__init__.py`, not by grepping for `.corr(`
against a `shift(`, because that grep misses `lean_momersion_20` (a product of
two signs) and `ts_cid_ce_20` (a sum of squared successive differences). The
four frames are a walk, a tick-rounded walk, an AR(1) path and a seasonal
one; 26 of the 28 pairs produce a usable number and the largest |Spearman| of
those 26 is **0.5335**:

    ts_ac1_60 TS_AC1_60          +0.3739 / +0.0008 / +0.3787 / -0.2027
    ts_c3_20 TS_C3_20_1          +0.0984 / -0.0142 / +0.0315 / -0.5335
    g191_026                     -0.2839 / -0.0357 / +0.0980 / +0.0882
    ts_cid_ce_20 TS_CID_CE_20    +0.0377 / -0.0496 / +0.0555 / +0.2680
    lean_momersion_20            -0.0161 / -0.0479 / +0.0408 / (constant)
    a101_048                     +0.0284 / +0.0283 / +0.0063 / -0.0419
    roll_spread ROLL_20          +0.0245 / -0.0484 / (n = 26)  / +0.0897

The two excluded pairs are excluded for a stated reason, not dropped:
`lean_momersion_20` is constant on the seasonal frame, and `ROLL_20` -- which
is NaN wherever a window's lag-1 autocovariance is non-negative -- overlaps
this column on only 26 of the AR(1) frame's 1,440 bars, where a Spearman
carries a standard error of about 0.2.

Averaging ten lags is not a restatement of the first one. Run at `maxlag` 1
this module IS `ts_ac1_60` to 5.6e-17, bit-equal on 936 of 1,440 bars -- the
gap is the division order, one `/(maxlag*v)` here against one
`/((length-lag)*v)` there.

The arithmetic is checked independently rather than trusted. The source
formula applied window by window with `sliding_window_view` -- no pandas
rolling anywhere, so no shared window machinery -- agrees with this column to
5.7e-15 on a walk, 2.4e-15 tick-rounded, 3.4e-15 on an AR(1) path and
3.2e-15 on a seasonal one, with identical NaN masks throughout. Spearman is
1.000000 on the first three; on the seasonal frame it is 0.990891, because
returns that repeat exactly every 10 bars leave the column full of NEAR-TIES
that a 3e-15 disagreement reorders -- the absolute agreement there is 6e-12
of that frame's own range.
Against an EXACT rational oracle in `fractions.Fraction` (every close is a
rational, so the whole statistic is one) the module is 2.4e-15 out on a walk
and 1.2e-15 tick-rounded, where a `math.fsum` scalar loop is 3.3e-16 and
4.1e-16: this spelling is about seven times the error of an exact summation
on an ordinary frame, and 6.8e+03 times BETTER than the plain raw-sum
expansion on the shape that matters (below).

Five readings the wording leaves open, decided and priced in
docs/TsAggac60Measured.md (A6) rather than assumed, each on the same walk:
* The returns are SIMPLE (`close/close.shift(1) - 1`), the prototype's `ret`.
  Log returns are a different column, though a close one: Spearman 0.999781,
  max |difference| 2.2e-03.
* `length` is 60 RETURNS, so 61 closes, and the first value lands at bar 60.
  Rejected: 60 CLOSES, i.e. 59 returns (Spearman 0.979126, max |difference|
  4.0e-02) -- the off-by-one a reader makes, priced so it is not re-argued.
* The `(length - k)` denominator and the POPULATION variance, both the
  source's. Dividing by `length * v` instead (the biased estimator) gives
  Spearman 0.995068 and max |difference| 1.2e-02 -- unlike the lag-1 case,
  where that choice is one constant factor, the per-lag weights differ and a
  RANK miner can see it. Keeping `length - k` with the SAMPLE variance is one
  constant factor, `59/60`: Spearman 1.000000, max |difference| 2.1e-03.
* The lags are 1..`maxlag`, the source's `a[:maxlag]` AFTER `acf[1:]`.
  Including lag 0, which is identically 1, is the off-by-one this expression
  invites: it maps the column to `1/11 + (10/11)*TS_AGGAC`, so Spearman is
  exactly 1.000000 and max |difference| 9.7e-02. A rank miner cannot see it;
  a rule with a threshold can.
* The window's SINGLE mean and variance, the source's, rather than a Pearson
  correlation per lag over the same 60 returns (`pandas.Series.autocorr`):
  Spearman 0.996854, max |difference| 1.1e-02. That variant is the
  prototype's normalisation on this port's window, and it is the closer half
  of the gap to the prototype.

`maxlag` IS a parameter, unlike `ts_ac1_60`'s `lag`, because the column name
carries it: `TS_AGGAC_60_10` says which lags were averaged, so a caller
cannot emit a mislabelled column. It is clamped to `length - 2` and the
EFFECTIVE value is the one in the name (`maxlag=1000` at `length` 60 gives
`TS_AGGAC_60_58`), which is `ts_c3_20`'s habit with its own `lag`.

A window with no dispersion to divide by is NaN, not a number, and the floor
is this fork's `4096 eps` rather than either of the source's two. tsfresh's
`agg_autocorrelation` does not skip such a window: it takes the
`np.abs(var) < 1e-10` branch and returns the MEAN OF ZEROS, i.e. exactly
0.0 -- a value this column reaches all the time (25.50% of iid windows are
above it), so the fabrication is invisible downstream. That threshold is on
the variance of RETURNS, so it fires at a return sd below 1e-5: measured on
300-bar frames, it fabricates 240 exact zeros on each of a flat frame, a
1%-a-bar geometric ladder, a walk at sigma = 1e-6 and a walk at sigma = 1e-9
-- on the last two of which this column reports on all 240 windows and reads
a perfectly ordinary +-0.066. tsfresh's OTHER guard, the
`np.isclose(var, 0)` of `feature_calculators.autocorrelation`, empties all
240 of those four instead. This module reports on 240 of the two low-vol
walks and on 0 of the two degenerate frames, where an UNGUARDED spelling
reports on 240 of the ladder's windows, up to 0.0603, out of nothing but
rounding.

Causal: bar T reads closes T - length .. T, measured by a
future-perturbation sweep -- 0 of 35 offsets on each of a walk, a
tick-rounded walk and an AR(1) path.
Scale-free: every input is a price ratio, and `8a / 8b` is the same double as
`a / b`, so the column is bit-identical under a x8/x64 rescale of price
(1,440 of 1,440 fired bars on each of those three frames, and 1,488 / 1,480 /
1,250 at `length` 12 / 20 / 250 on the walk). x10 and x3.7 are not
bit-identical -- they perturb the returns in their last bits -- but the NaN
masks match exactly and the values agree to 9.5e-15 at Spearman 1.000000,
which is the Gate D tolerance reading. The difference-of-logarithms spelling
of the return would not be: at x8 it is bit-equal on 821 of 1,499 bars where
the ratio spelling is bit-equal on all 1,499.
NaN on the first `length` bars; on any window holding a close that is NaN,
infinite, zero, negative or subnormal (a bad close empties the
`length + 1` = 61 windows it sits in, because it spoils two returns --
measured, with 0 earlier bars moved); on any window holding a close pair
whose ratio OVERFLOWS or whose return's SQUARE does; on any window whose
`length` returns have a population variance of 8.27e-25 or less (an sd of
9.09e-13 or less); and on any window whose variance or any of its `maxlag`
summed squared differences exceed what its own range allows, which is the
accumulator test below.

⚠ **Two numerical limits, measured rather than assumed.**
* `rolling.var` and `rolling.sum` are ONLINE in pandas, so a single enormous
  return leaves a residue in both long after it has left the window. The
  trust test above (an exact bound from the window's own range, computed by
  a deque and therefore local) turns the gross case into NaN: with one
  planted return of 1e+8 in a 400-bar walk, the 139 bars after it has left
  every window are NaN here and sit up to **1.149** away from a per-window
  oracle without the test. It is not a cure for the whole range: the same
  bars are 1.4e-09 out for a planted return of 1e+2, 3.5e-06 at 1e+4 and
  9.1e-03 at 1e+6, none of which the test catches, because the variance
  stays inside its bound. On nine clean frames -- walk, tick-rounded,
  AR(1) at +-0.5, a seasonal path, an alternating frame (which attains the
  bound EXACTLY, at a measured ratio of 1.000000000000), a volatility
  COLLAPSE from sigma 0.3 to 1e-9, a sigma = 1e-6 walk and a fine-tick ladder
  -- it costs 0 bars. The collapse is the shape `ts_cid_ce_20` found the
  accumulator loses; here the VARIANCE FLOOR gets there first (pandas' online
  variance comes back at or below 8.27e-25 on 141 of the 200 post-collapse
  bars), and the 59 bars that still report are 3.6e-14 from the per-window
  oracle with the trust test or without it.
* The numerator is spelled to avoid subtracting the window mean from a raw
  product sum. On a path whose returns have `|mean| / sd` = 1e5 the module is
  2.0e-10 from the exact rational value, where the `math.fsum` loop and the
  window-by-window oracle are 8.0e-11 and the plain raw-sum expansion is
  **1.3e-06**, about 6.8e+03 times worse. That is the spelling's whole
  justification, and it is a measurement on one shape rather than a bound.
  The 2.0e-10 is NOT the divisor's rounding: feeding the module's numerator
  to the EXACT rational variance instead of pandas' leaves it at 1.9e-10.
  That floor is the cancellation in `x[i] - m` itself, which every spelling
  pays -- the `math.fsum` loop's own 8.0e-11 is the same effect.

Cost: four O(n) passes shared by every lag (mean, variance and the two
extrema) plus four per lag (two shifts, a lagged difference and its rolling
sum), and no allocation that grows with `length` -- the traced peak is
45.2 MB on 400,000 bars, reproduced exactly across runs. The TIMES are
individual runs on one machine and not bounds: two runs of the shipped module
gave 246 and 237 ms at the default, ~75 ms at `maxlag` 1 and 235-240 ms at
`length` 12 and 250, so the cost tracks `maxlag` and not `length`. The trust
test's `maxlag` comparisons cost roughly 30 ms of that (238 against 209, then
235 against 208 ms, same code path, flag flipped). The window-by-window
oracle this was checked against is ~1.24 s and peaks at 403.2 MB on the same
input, which is why it lives in docs/measure_ts_aggac_60.py and not here.

Calculation:
    Default Inputs:
        length=60, maxlag=10
    r[t]         = close[t] / close[t-1] - 1
    m, v         = mean and population variance of the trailing `length` r
    AC[k]        = sum((r[i] - m) * (r[i-k] - m)) / ((length - k) * v)
                   over the `length - k` pairs inside the window
    TS_AGGAC[T]  = mean of AC[1..maxlag], NaN where v <= 8.27e-25 or the
                   accumulator test fails

Args:
    close (pd.Series): Series of 'close's
    length (int): Returns per window. At least 3 -- a window of two returns
        is identically -1 -- so a smaller or missing value falls back to the
        default. `maxlag` is clamped to it, not the other way round.
        Default: 60
    maxlag (int): The longest lag averaged; the lags are 1..maxlag. At least
        1, clamped to `length - 2`, and the effective value is the one in the
        column name. Default: 10
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)

Returns:
    pd.Series: TS_AGGAC_{length}_{maxlag}, dimensionless, in
        [-0.310043, 0.915798] at length 60 and maxlag 10
"""
