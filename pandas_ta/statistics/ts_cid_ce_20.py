# -*- coding: utf-8 -*-
import numpy as np
from pandas import Series

from pandas_ta.utils import get_offset, verify_series

# A window of TWO returns is identically 2: with `x = [a, b]` the only squared
# difference is `(a-b)**2` and the population variance is `(a-b)**2/4`, so the
# quotient is 4 and the column is `sqrt(4)` for every `a != b` (and NaN when
# they are equal). Three returns is the smallest window on which the statistic
# varies.
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
# spelled on the standard deviation and squared into the variance here,
# exactly as in `statistics/ts_ac1_60.py`, because what this column divides by
# is a variance.
NOISE_ULPS = 4096
NOISE_FLOOR = NOISE_ULPS * np.finfo(float).eps  # 9.09e-13, on the sd
VAR_FLOOR = NOISE_FLOOR ** 2                    # 8.27e-25, on the variance


def ts_cid_ce_20(close, length=None, offset=None, **kwargs):
    """Indicator: CID-CE complexity estimate of returns (TS_CID_CE)"""
    # Validate Arguments
    length = int(length) if length and int(length) >= MIN_LENGTH else 20
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
    # the next line rather than carried into the accumulators.
    with np.errstate(over="ignore"):
        r = px / px.shift(1) - 1.0
    r = r.where(np.isfinite(r))
    # A return too large for its own square to be SUMMED over a window is not
    # usable data, and dropping it is not a local nicety: pandas accumulates
    # `rolling.var` and `rolling.sum` ONLINE, so an infinite accumulator never
    # leaves the window and every LATER bar comes back NaN too.
    #
    # The bound is what makes that locality structural rather than measured on
    # one shape. Every kept return has `r**2 < max/(8*length)`, so writing
    # `B**2` for that ceiling: the window mean is at most `B`, every squared
    # deviation at most `4*B**2`, so `length * var <= 4*length*B**2 < max/2`,
    # and each of the `length - 1` squared successive differences is at most
    # `4*B**2` as well, so their sum is under `max/2` too -- both accumulators
    # stay inside half the float range, the halving being headroom for the
    # accumulation's own rounding. The ceiling it puts on a return is
    # 1.06e+153 at `length` 20, which nothing a market can produce reaches. A
    # comparison against NaN or inf is False, so this test also rejects a
    # non-finite square.
    with np.errstate(over="ignore"):
        square = np.square(r.to_numpy())
    r = r.where(square < np.finfo(float).max / (8 * length))

    rolling = r.rolling(length, min_periods=length)
    # The POPULATION variance (`ddof=0`), which is what `numpy.std` computes
    # in the source's normalisation step.
    var = rolling.var(ddof=0)
    # The sum of the `length - 1` squared successive differences inside the
    # window. tsfresh z-normalises the window and then takes
    # `sqrt(dot(diff, diff))`; the normalisation's mean cancels in a
    # difference and its standard deviation factors out of the whole sum, so
    # the same number is `sqrt(sum (x[i] - x[i-1])**2 / var)`. Dividing the
    # SUM by the variance rather than normalising each return first is one
    # division instead of `length` of them and loses nothing: both spellings
    # are priced against an exact rational oracle in docs/TsCidCe20Measured.md
    # (A5).
    gap = Series(np.square(r.diff().to_numpy()), index=r.index)
    gap = gap.rolling(length - 1, min_periods=length - 1).sum()

    # A window whose two accumulators disagree with its own extrema is not
    # reported. `rolling.var` and `rolling.sum` are ONLINE -- a value is added
    # when it enters the window and subtracted when it leaves -- so a single
    # enormous return leaves a residue in both long after it has left, and
    # that residue is a plausible-looking number rather than a NaN. The two
    # tests here are exact algebra on the window's range `s = max - min`,
    # which `rolling.max`/`rolling.min` compute by a deque and therefore
    # LOCALLY: a population variance cannot exceed `(s/2)**2` (equality at
    # equal mass on the two ends, which an alternating window reaches at an
    # EVEN `length`; at an odd one it is just inside), and
    # `length - 1` squared successive differences cannot exceed
    # `(length - 1) * s**2` (equality for the same window). The slack is the
    # same 4096 eps as the floor above, relative.
    #
    # Measured (docs/TsCidCe20Measured.md, Guards): on a frame whose returns
    # run at sigma = 0.3 for 200 bars and then at sigma = 1e-9, the residue of
    # the volatile squares is larger than the frozen windows' own dispersion,
    # and the 181 bars from 219 on come out up to 6.323 away from a per-window
    # oracle whose own median there is 5.757 -- the error is the size of the
    # value. This test turns those 181 bars into NaN and costs 0 bars on each
    # of seven clean frames. It does NOT catch a single planted spike of
    # 1e+2, 1e+4 or 1e+6 (4.8e-09, 5.6e-05 and 0.786 off the oracle), because
    # there the window's own range is wide enough to allow the residue.
    #
    # ⚠ Bigger than that, the residue stops being a residue. Measured on a
    # 2,000-bar walk with one return planted at bar 200 (1,799 bars follow
    # it), and the mechanism differs by magnitude:
    #   1e+6  0 bars emptied; all 1,799 fire and are up to 0.786 wrong.
    #   1e+7  1,643 emptied -- by THIS test, not by the floor: pandas'
    #         unguarded `rolling.var` is positive on all 1,779 of bars 221..,
    #         so the residue is inside the floor and outside the window's own
    #         range. 156 bars still fire (201..1859) and are up to 3.868 from
    #         a per-window oracle.
    #   1e+8  1,779 emptied -- by the FLOOR: the unguarded variance is
    #         non-positive on all 1,779. The 20 bars that fire are exactly
    #         201..220, the windows that still hold the planted return, and
    #         nothing fires after 220.
    #   1e+10 1,780 emptied, 19 fire (201..219).
    # So this test is what rescues the 1e+7 case, and nothing rescues 1e+8:
    # that is pandas' accumulator rather than this spelling. See the
    # docstring's NaN rules.
    span = rolling.max() - rolling.min()
    bound = span * span
    trusted = (var <= 0.25 * bound * (1.0 + NOISE_FLOOR)) \
        & (gap <= (length - 1) * bound * (1.0 + NOISE_FLOOR))

    # Flooring the divisor first means no zero and no rounding-level value
    # ever reaches the division, so there is nothing for an `errstate` to
    # suppress and no infinity to clean up afterwards. The quotient is bounded
    # by `4 * length` in exact arithmetic -- its reachable maximum is
    # `4 * length * sin(pi*(length-1)/(2*length))**2`, see the docstring's
    # range -- so the square root cannot overflow either.
    #
    # Every term of `gap` is a square, so the sum is non-negative in exact
    # arithmetic, and it was counted rather than assumed: 0 negative sums over
    # 20,680 windows of the 18 frames docs/measure_ts_cid_ce_20.py builds
    # (Guard 3b), including the planted 1e+8 spike, where the VARIANCE
    # accumulator does go non-positive. If an online accumulator ever did
    # land below zero, the square root of that quotient is NaN, which is the
    # right answer for a window whose accumulator has gone backwards; the
    # `errstate` is here so numpy reports it as a NaN and not as a
    # RuntimeWarning out of library code. There is deliberately no
    # `gap >= 0` test in front of it: it would be a guard with no measurement
    # behind it, and it would not change the output.
    quotient = gap / var.where((var > VAR_FLOOR) & trusted)
    with np.errstate(invalid="ignore"):
        cidce = Series(np.sqrt(quotient.to_numpy()), index=close.index)

    # Offset
    if offset != 0:
        cidce = cidce.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        cidce.fillna(kwargs["fillna"], inplace=True)

    # Name and Categorize it
    cidce.name = f"TS_CID_CE_{length}"
    cidce.category = "statistics"

    return cidce


ts_cid_ce_20.__doc__ = \
"""CID-CE complexity estimate of returns (TS_CID_CE)

How JAGGED the last `length` returns were: the length of the z-normalised
return path, which tsfresh offers as a complexity estimate.

    x          = the window's `length` simple returns
    v          = their POPULATION variance (`ddof=0`)
    TS_CID_CE  = sqrt(sum over the length-1 pairs of (x[i] - x[i-1])**2 / v)

⚠ **It is NOT volatility.** It is invariant to any AFFINE map of the
returns, which is the property to read first: doubling every return, halving
it, or adding a constant drift to every one leaves the column where it was
(Spearman 1.000000 and max |difference| 9.7e-14 at returns x2, 8.4e-14 at
x0.5 and 1.1e-13 at +0.004 of log drift a bar, measured on a 1,500-bar walk,
with identical NaN masks). Against the SAME window's statistics on that
walk: Spearman **0.0072** against the window's standard deviation, -0.0733
against its mean return, -0.0097 against the absolute mean return and
-0.0731 against the 20-bar price change. tsfresh's OTHER mode,
`normalize=False`, is the volatility reading -- it is 0.8243 against that
same standard deviation where this column is 0.0072 -- and it is not what
the issue asks for.

⚠ **It is a monotone restatement of the lag-1 return autocorrelation AT THE
SAME WINDOW.** Exactly, with `y` the demeaned window:

    TS_CID_CE**2 = 2*length - (y[oldest]**2 + y[newest]**2) / v
                   - 2*(length - 1) * TS_AC1(length)

which the module reproduces to 2.1e-14 over 1,480 bars. So against this
fork's `ts_ac1_60` run at `length` 20 the Spearman is **-0.977743**; against
the SHIPPED `TS_AC1_60`, whose window is 60 returns and not 20, it is
**-0.4218** on a walk, -0.5342 tick-rounded and -0.4339 on an AR(1) path.
Gate E's comparator set is the engine's 687 columns and cannot see a
pandas_ta port, so this overlap is disclosed here rather than measured
there: the two columns ship at different lengths, and a consumer putting
both at the same `length` would be double-weighting one signal.

⚠ **It is BOUNDED and both ends are reachable.** The squared column is
`length` times the Rayleigh quotient of the free-end path Laplacian on the
subspace orthogonal to the all-ones vector, whose eigenvalues are
`4*sin(pi*k/(2*length))**2` for k = 1..length-1 (the k = 0 eigenvector IS
that vector), so

    min = sqrt(4*length) * sin(pi/(2*length))
    max = sqrt(4*length) * sin(pi*(length-1)/(2*length))

which is **[0.701759, 8.916700]** at `length` 20 -- [1.732051, 3.000000] at
3, [1.530734, 3.695518] at 4, [0.989378, 6.246690] at 10 and
[0.405532, 15.486625] at 60. Both ends are attained by the module on the
matching cosine window, to 1.8e-15. One family of windows has an EXACT
value: returns alternating between two values read `2*sqrt(length-1)` at an
even `length` (**8.717798** at 20) and `2*length/sqrt(length+1)` at an odd
one, derived and measured bit-exactly on `close = [1, 2, 1, 2, ...]` at
`length` 3, 4, 20 and 21 (at 5 the two spellings of the same number differ
by one ulp).

⚠ **The usual case is near sqrt(2*length) and the spread is narrow.** For
iid returns of finite variance the RATIO OF EXPECTATIONS is exactly
`2*length`: `E[gap] = 2*(length-1)*sigma**2` and
`E[var] = (length-1)*sigma**2/length` (arithmetic, not measured, and
distribution-free). The expectation of a ratio is not the ratio of the
expectations, so the column need NOT sit at `sqrt(2*length)` = 6.3246 at
`length` 20, and which side it lands on is MEASURED rather than derived
(`sqrt` pulls a mean down, `1/var` pulls it up, and the two are dependent).
It lands just below: over 2,000 independent 20-return windows
the column has median 6.2848, mean 6.2599, sd 0.6723, p10 5.4033, p90
7.1126, min 3.4785 and max 8.0608 (finite on 2,000 of 2,000). The LEVEL
therefore grows with the window, roughly as `sqrt(2*length)`: on a
20,000-bar AR(1) path at `phi` = +0.5 the median is 4.8186 / 7.9344 /
14.2868 / 31.6863 at `length` 20 / 60 / 200 / 1000, i.e. 0.76 / 0.72 / 0.71
/ 0.71 of `sqrt(2*length)`. Two columns at different `length` are NOT on one
scale.

⚠ **What it orders is the persistence of the returns, downward.** On paths
whose LOG returns are an AR(1) with coefficient `phi`, the medians are
4.6865 / 5.5166 / 6.2276 / 6.8905 / 7.5389 at `phi` = +0.50 / +0.25 / 0 /
-0.25 / -0.50: trending (positively autocorrelated) returns read LOW,
alternating ones read HIGH. Two consecutive windows share 19 of their 20
returns, so the column autocorrelates at 0.8876 at lag 1, 0.3662 at lag 10
and -0.1284 at lag 20 (measured on a walk) -- it is a state, not an event
flag.

Source: tsfresh feature_calculators (MIT), `cid_ce(x, normalize=True)`, as
the formula is stated by PandasTa issue #95: `cid_ce(x, normalize=True) on
20 returns`.
⚠ tsfresh is NOT installed in this worktree and web access is unavailable,
so the formula under test is the issue's line plus the published definition
of `feature_calculators.cid_ce` -- z-normalise by the POPULATION standard
deviation, take `numpy.diff`, return `sqrt(dot(d, d))` -- and not a read of
tsfresh's own code; anything tsfresh does that those do not state (how it
treats NaNs) is unverified here. The 20 is the issue's own parameter.

**This column IS the screen prototype, up to one positive constant.** Issue
#95's prototype (`docs/issues/screen/ind_screen.py` candidate
`ts_cid_ce_20`, local to the owner's machine) divides by pandas' default
SAMPLE standard deviation (`ddof=1`) where the source divides by the
population one, so the prototype is exactly this column divided by
`sqrt(20/19)` = 1.025978352085. Measured on a 1,500-bar walk: the ratio is
that constant to twelve decimals at both its minimum and its maximum
(max |port - sqrt(20/19) * prototype| = 2.7e-15, the factor at full float
precision), Spearman **1.000000**,
NaN masks identical, same first fired bar 20 -- and the owner's own registry
entry agrees with the retype bit-for-bit on 1,480 of 1,480 bars. Because
Gate E's statistic is a Spearman, which no positive rescaling moves, the
screen's figures (max |rho| 0.2641 vs `chop`, n = 396,927) are expected to
carry over to this column wherever both fire; the launcher's Gate E run on
this module is still the number that decides ship or revert, since this
port's guards empty windows the prototype would report on.

The arithmetic is checked independently rather than trusted. The source
function applied window by window -- every window handed to a retype of
`cid_ce` itself, so the z-normalisation happens per return as tsfresh does
it and no pandas rolling is involved -- agrees with this column to 3.5e-14
on a walk, 2.2e-14 tick-rounded, 4.1e-14 on an AR(1) path and 2.9e-10 on a
path whose returns have `|mean| / sd` = 1e5, at Spearman 1.000000 with
identical NaN masks. Against an EXACT rational oracle in
`fractions.Fraction` (every close is a rational, so the whole squared
statistic is one) the module is 4.4e-15 out on a walk, 8.0e-15 tick-rounded
and 1.1e-09 on that mean-dominated path, where a `math.fsum` scalar loop is
4.4e-15, 8.9e-15 and 1.1e-09: the same order everywhere, with no spelling
systematically better. The mean-dominated error belongs to the variance
accumulator, which every spelling shares; the numerator holds no mean at
all, because a difference of two returns does not contain one.

Three readings the wording leaves open, decided and priced in
docs/TsCidCe20Measured.md (A6) rather than assumed, each on the same walk:
* The returns are SIMPLE (`close/close.shift(1) - 1`), the prototype's
  `ret`. Log returns are a different column, though a close one: Spearman
  0.999909, max |difference| 4.8e-02.
* `length` is 20 RETURNS, so 21 closes, and the first value lands at bar 20.
  Rejected: 20 CLOSES, i.e. 19 returns (Spearman 0.949216, max |difference|
  1.4179) -- the off-by-one a reader makes, priced so it is not re-argued.
* The POPULATION standard deviation, the source's `numpy.std`, rather than
  the prototype's sample one: Spearman 1.000000 and a level difference of up
  to 0.1988, i.e. the constant 1.025978352085 above. A rank miner cannot see
  the choice; a rule with a threshold can.

A window with no dispersion to divide by is NaN, not a number, and NOT
tsfresh's **0.0**: that branch (`if s == 0: return 0.0`) returns a value
below the reachable minimum of 0.701759, which a tree would read as the
calmest possible window rather than as missing data. Measured on 300-bar
frames: on a flat frame tsfresh's branch reports 0.0 on all 280 windows
where this column reports on none; on a 1%-a-bar geometric ladder, whose
returns are mathematically constant but vary at rounding level in float64,
an UNGUARDED spelling reports on all 280 windows and reaches 8.6372 -- a
plausible-looking number inside the reachable range, out of nothing but
rounding. The floor is this fork's `4096 eps`, spelled on the standard
deviation and squared into the variance. It bounds the DISPERSION of the
returns, not their size: a one-tick-a-bar ladder at price 50 with a 0.01
tick has window variance 4.3e-14 and reports on 280 of 300 bars, while at
price 1e6 with a 0.001 tick it is 1.2e-32 and reports on none.

Causal: bar T reads closes T - length .. T, measured by a
future-perturbation sweep -- 0 of 35 offsets on each of a walk, a
tick-rounded walk and an AR(1) path.
Scale-free: every input is a price ratio, and `8a / 8b` is the same double as
`a / b`, so the column is bit-identical under a x8/x64 rescale of price
(1,480 of 1,480 fired bars on each of those three frames, and 1,497 / 1,440
/ 1,250 at `length` 3 / 60 / 250 on the walk). x10 and x3.7 are not
bit-identical -- they perturb the returns in their last bits -- but the NaN
masks match exactly and the values agree to 7.4e-14 at Spearman 1.000000,
which is the Gate D tolerance reading. The difference-of-logarithms spelling
of the return would not be: at x8 it is bit-equal on 821 of 1,499 bars where
the ratio spelling is bit-equal on all 1,499.
NaN on the first `length` bars; on any window holding a close that is NaN,
infinite, zero, negative or subnormal (a bad close empties the
`length + 1` = 21 windows it sits in, because it spoils two returns --
measured, with 0 earlier bars moved); on any window holding a close pair
whose ratio OVERFLOWS or whose return's SQUARE does; on any window whose
`length` returns have a population variance of 8.27e-25 or less (an sd of
9.09e-13 or less), which 21 identical closes are one way to reach; and on
any window whose variance or summed squared differences exceed what its own
range allows, which is the accumulator test below.
⚠ **And NOT locally, when one return is enormous.** Measured on a 2,000-bar
walk with a single return planted at bar 200, so 1,799 bars follow it, and
the answer depends on the magnitude -- the sentence to read is the row, not a
threshold:

    1e+6   0 of the 1,799 later bars go NaN. They fire and are up to 0.786
           from a per-window oracle: WRONG, not missing.
    1e+7   1,643 go NaN -- the accumulator trust test's doing, since pandas'
           unguarded variance is still positive on all of bars 221.. -- and
           156 bars still fire (the last at bar 1859), up to 3.868 out.
    1e+8   1,779 go NaN, because the unguarded variance comes back
           NON-POSITIVE on every one of them and the floor empties them. The
           20 bars that fire are exactly 201..220, the windows that still
           hold the planted return; **nothing fires after bar 220** for the
           remaining 1,779 bars of the frame.
    1e+10  1,780 go NaN, 19 fire (201..219).

The per-return square bound below is no help: it drops a return whose SQUARE
is unrepresentable (above 1.06e+153), and 1e+8 is representable. The cause is
pandas' ONLINE `rolling.var`, not this spelling -- the same frames through
`ts_ac1_60`, which shares the accumulator and this port's floor and trust
test, empty exactly the same bars, which is expected rather than independent
evidence; the evidence is the unguarded variance count above. The only
structurally local spelling is a per-window pass, which costs 35.7 s against
this module's 55-59 ms on 400,000 bars. It is recorded rather than fixed.

⚠ **Two numerical limits, measured rather than assumed.**
* `rolling.var` and `rolling.sum` are ONLINE in pandas, so a volatile
  stretch leaves a residue in both long after it has left the window. The
  trust test above (exact bounds from the window's own range, computed by a
  deque and therefore local) turns the gross case into NaN: on a frame whose
  returns run at sigma = 0.3 for 200 bars and then at sigma = 1e-9, the 181
  bars from 219 on are NaN here and sit up to **6.323** from a per-window
  oracle whose median there is 5.757 without the test -- an error the size of
  the value. The sigma gap matters: at sigma = 1e-7 instead of 1e-9 the test
  rejects 0 bars and the untested spelling is only 1.3e-02 out, and at
  sigma = 0.05 then 1e-9 both spellings are empty anyway. It is not a cure
  for the whole range either: a single planted return of 1e+2, 1e+4 or 1e+6
  leaves the bars after it 4.8e-09, 5.6e-05 and **0.786** out and passes the
  test, because a window that still remembers a wide range allows the
  residue. It IS what empties the 1,643 bars of the 1e+7 case above, and at
  1e+8 the accumulator is destroyed outright and no test can help. On
  seven clean frames -- walk,
  tick-rounded, AR(1) at +-0.5, an alternating frame (which attains BOTH
  bounds EXACTLY, at measured ratios of 1.000000000000), a sigma = 1e-6 walk
  and a fine-tick ladder -- the test costs 0 bars.
* The column is a ratio of two accumulators, so a window whose returns have
  a huge mean and a tiny dispersion is as accurate as the variance is: on a
  path with `|mean| / sd` = 1e5 the module is 1.1e-09 from the exact rational
  value, and so are the `math.fsum` loop and the window-by-window oracle.
  There is no better spelling of this column to reach for; it is a limit of
  the statistic, not of this port.

Cost: four O(n) rolling passes (the variance, the squared-difference sum and
the two extrema) and no allocation that grows with `length` -- the traced peak is
29.2 MB on 400,000 bars at each of `length` 3, 20, 60 and 250, in each of
three runs, and the call takes 55-59 ms there (a band across those 12 calls,
flat in `length`, not four numbers). The trust test's two extrema are about
half of that in four paired runs (54-55 ms against 26-27 ms, same code path,
flag flipped): the price of not reporting a plausible number on a
volatile-then-frozen frame. The window-by-window oracle this was checked
against is 35.7 s and peaks at 80.1 MB on the same input, which is why it
lives in docs/measure_ts_cid_ce_20.py and not here.

Calculation:
    Default Inputs:
        length=20
    r[t]          = close[t] / close[t-1] - 1
    v             = population variance of the trailing `length` r
    g             = sum of (r[i] - r[i-1])**2 over the length-1 pairs
    TS_CID_CE[T]  = sqrt(g / v), NaN where v <= 8.27e-25 or the accumulator
                    test fails

Args:
    close (pd.Series): Series of 'close's
    length (int): Returns per window. At least 3 -- a window of two returns
        is identically 2 -- so a smaller or missing value falls back to the
        default. Default: 20
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)

Returns:
    pd.Series: TS_CID_CE_{length}, dimensionless, in [0.701759, 8.916700] at
        length 20
"""
