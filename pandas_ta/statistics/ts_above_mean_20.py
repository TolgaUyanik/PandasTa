# -*- coding: utf-8 -*-
import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from pandas import Series

from pandas_ta.utils import get_offset, verify_series

# A window of TWO returns is identically `1/2`: of two unequal numbers exactly
# one is above their midpoint, and two equal ones are refused by the floor
# below. Three returns is the smallest window on which the column varies, and
# there it takes only `1/3` and `2/3`.
MIN_LENGTH = 3
EXTRA_CLOSES = 1  # `length` returns need `length + 1` closes
# What this column reads is the ORDER of the window's returns against their
# own mean, so the question a floor must answer is not "is the dispersion big
# enough to divide by" (there is no division by it here) but "is the dispersion
# bigger than the error in the mean the comparisons are made against".
#
# That error scales with the window's own magnitude, so the floor is RELATIVE
# -- `NOISE_FACTOR * max |r|` -- and not the absolute `4096 eps` that
# `statistics/ts_c3_20.py`, `statistics/ts_binent_20.py` and
# `statistics/ts_cid_ce_20.py` use. The constant is the same 4096 ulps; what
# it multiplies differs because what it protects differs. An absolute floor
# would ALSO empty a quiet-but-honest window (returns of 1e-6 spread over
# 1e-13, where the mean's own error is 4.4e-21 and every comparison is clean),
# which is measured in docs/TsAboveMean20Measured.md (Guards G3).
#
# With `spread > NOISE_FACTOR * amax` the computed mean is strictly INSIDE the
# window's range, which is what keeps the count between 1 and `length - 1`:
# the exact mean is at most `hi - spread/length`, so it clears `hi` by more
# than `4096/length` = 204.8 ulps of `amax` at `length` 20. Against that, the
# error in the COMPUTED mean: naive summation of `length` terms is out by at
# most `(length - 1) * eps * sum|r| <= (length - 1) * length * eps * amax`, so
# after the division by `length` the mean is out by at most
# `(length - 1) * eps * amax` = 19 ulps, plus one more for the division
# itself. About a 10x margin, and the 1 <= count <= length - 1 it buys is
# COUNTED over every window of every frame in
# docs/measure_ts_above_mean_20.py (Gate A4).
#
# ⚠ The floor is scale-invariant and NOT shift-invariant; see the docstring.
NOISE_ULPS = 4096
NOISE_FACTOR = NOISE_ULPS * np.finfo(float).eps  # 9.09e-13, RELATIVE


def ts_above_mean_20(close, length=None, offset=None, **kwargs):
    """Indicator: share of returns above the window mean (TS_ABOVE_MEAN)"""
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
    # an infinite return. It is silenced here and dropped by the bound below.
    with np.errstate(over="ignore"):
        r = (px / px.shift(1) - 1.0).to_numpy()
    # Every kept return satisfies `|r| < max / (2 * length)`, so the sum of a
    # window's `length` of them cannot overflow and the mean is a real number
    # rather than an infinity whose comparisons all read False -- which would
    # report a count of 0 and a share of 0.0, a value this column cannot
    # otherwise reach (see the docstring's range). A comparison against NaN or
    # inf is False, so this one test also drops both.
    #
    # The ceiling it puts on a return is 4.49e+306 at `length` 20: nothing a
    # market can produce, and far above the 1e+8 spike that defeats the ONLINE
    # accumulators of this fork's `ts_ac1_60` and `ts_cid_ce_20`. This module
    # has no such failure mode to guard -- every window is reduced from its own
    # `length` values by `sliding_window_view`, so no value leaves a residue in
    # any later window. Measured in docs/TsAboveMean20Measured.md (Guards G5),
    # on a 2,000-bar frame with one return planted at bar 200: at 1e+2, 1e+6,
    # 1e+8, 1e+100 and 1e+300 the 20 windows holding it all read 0.05 -- the
    # right answer, one return above the mean -- and every one of the 1,780
    # later bars is bit-identical to the unspiked frame. Only 1e+307, above
    # this bound, empties those 20 windows, and the 1,780 later bars are
    # bit-identical there too.
    r = np.where(np.abs(r) < np.finfo(float).max / (2 * length), r, np.nan)

    windows = sliding_window_view(r, length)
    # The window mean, from that window's own `length` values. `.sum(axis=1)`
    # on the view and not `rolling.mean()`: pandas' rolling mean is an ONLINE
    # accumulator, which is what makes a single enormous value poison every
    # later window of the frames measured in `ts_cid_ce_20`'s receipt.
    mean = windows.sum(axis=1) / length
    hi, lo = windows.max(axis=1), windows.min(axis=1)
    # STRICTLY above, which is the source's `>`: a return that ties the mean is
    # not counted. `>=` is a different column and is priced in
    # docs/TsAboveMean20Measured.md (Gate A5).
    #
    # One `(rows,)` comparison per window POSITION -- `windows[:, j]` is the
    # contiguous slice `r[j : j + rows]` -- rather than the one-liner
    # `(windows > mean[:, None]).sum(axis=1)`, which materialises a
    # `(rows, length)` bool array. The two agree on every count (measured) and
    # only the cost differs: at the default `length` 20 and n = 400,000 this
    # form is both lighter and faster (6.9 MB / 23.4 ms against 11.3 MB /
    # 27.6 ms), and its peak does not grow with `length` -- 6.9 MB at `length`
    # 250 where the matrix form reaches 103.3 MB. It is slower at a long
    # window (204.4 ms against 170.9 ms at 250), which is the whole price.
    # The milliseconds are this machine's and move between runs; the memory
    # peaks are the claim.
    # `tests/test_ts_above_mean_20.py` pins the spelling, because the two are
    # behaviourally identical and only the cost separates them.
    count = np.zeros(windows.shape[0], dtype=np.int64)
    for j in range(length):
        count += windows[:, j] > mean

    # `hi - lo` is the window's range and `max(hi, -lo)` its largest absolute
    # return, both from the same two reductions. A window holding a NaN return
    # has NaN for both, and `NaN > anything` is False, so this one test is also
    # what empties a window with a bad close in it -- pinned by
    # `tests/test_ts_above_mean_20.py::test_a_non_finite_return_empties_its_windows`
    # so the behaviour cannot drift to a silent count of 0.
    reported = (hi - lo) > NOISE_FACTOR * np.maximum(hi, -lo)

    out = np.full(c.size, np.nan)
    out[length - 1:] = np.where(reported, count / length, np.nan)
    share = Series(out, index=close.index)

    # Offset
    if offset != 0:
        share = share.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        share.fillna(kwargs["fillna"], inplace=True)

    # Name and Categorize it
    share.name = f"TS_ABOVE_MEAN_{length}"
    share.category = "statistics"

    return share


ts_above_mean_20.__doc__ = \
"""Share of returns above the window mean (TS_ABOVE_MEAN)

What fraction of the last `length` returns sat strictly above their own
window mean -- tsfresh's `count_above_mean` divided by the window size.

    x              = the window's `length` simple returns
    m              = their arithmetic mean
    TS_ABOVE_MEAN  = (how many x[i] > m) / length

⚠ **It is a SKEWNESS reading, and it reads BACKWARDS.** A few large gains
among many small losses pull the mean UP, so fewer returns clear it and the
column goes DOWN. Over 20,000 independent 20-return windows spanning
skewness -3 .. +3 the Spearman against the windows' own skewness is
**-0.8137** (that figure and the level table below are computed on the
STATISTIC rather than through this function -- 20,000 one-window calls would
say the same thing slowly -- and the bridge is the bit-equality in the
"arithmetic is checked independently" paragraph); against a rolling
`skew(r, 20)` on real-shaped frames it is
-0.6229 on a walk, -0.6211 tick-rounded, -0.6283 / -0.4884 on AR(1) paths at
phi = +-0.5, -0.8699 heavy-tailed and **-0.9899 on a two-point frame**, where
the returns take exactly two values and the column IS a relabelling of "how
many up-returns". This fork already ships a return-skewness column, and this
one lands at -0.6141 / -0.8581 / -0.9619 against `OSAP_RETSKEW_21` on those
same frames. Those figures are SYNTHETIC and they are the only measurement of
that pair that exists: Gate E's 687 comparators hold no pandas_ta port, and
the screen's real-frame fork overlap for this candidate (max |rho| 0.2405 vs
`qqe:QQEs_14_5_4.236` over 12 frames) was taken on 2026-10-24, nine days
before `osap_retskew_21` entered `Category`, so it cannot bound this pair.
What that screen DID measure on real frames is this candidate against
`ts_medskew_20`, `(mean - median)/std` on the same 20 returns, at pooled
**0.8428** -- another skewness reading, still a prototype and not shipped
(issue #98), and the most adverse figure on record for this column. See
docs/TsAboveMean20Measured.md §5.

⚠ **It cannot see volatility or direction.** The COUNT is invariant to any
affine map of the returns with a positive slope -- doubling every return,
halving it, or adding a constant drift to every one cannot change which
returns are above their own mean -- so on a walk the column reads Spearman
-0.0746 against the same window's return standard deviation and 0.0699
against the same window's mean return, and is bit-equal on 1,480 of 1,480
bars at r x 2, r x 0.5 and r + 0.004. The exception is the two-point frame
above: where the returns take two values, mean and skewness are the same
statistic and it reads 0.9899 against that mean.
⚠ That invariance is the COUNT's and not the reported MASK's. The floor
below is scale-invariant but NOT shift-invariant -- `hi - lo` is unchanged by
`r -> r + c` while `4096 eps * max|r|` grows with `c` -- so a drift can empty
a window the undrifted frame reports on. Measured: returns of about 1e-6
with a median window spread of 1.33e-15 fire on 580 of 600 bars, and the
same returns plus a 0.004 drift fire on 0, because the floor moves from
9.10e-19 to 3.64e-15 while the spread does not move at all. Only a window
that close to the floor is affected; the nine frames of Gate D5 are not.

⚠ **It is BOUNDED, and the bounds are 1/length and 1 - 1/length, not 0 and
1.** If no return is above the mean then all are at or below it and the sum
forces all of them EQUAL, and symmetrically for all-above; so a window of
returns that are not all identical always has between 1 and `length - 1` of
them above the mean. At `length` 20 that is **[0.05, 0.95]** and 19 reachable
values. Both ends are attained -- by a hand-built window (19 equal gains
after one zero reads 0.95; one gain among 19 zeros reads 0.05) and on a
heavy-tailed 1,500-bar frame, which reaches all **19 of 19** values. A
reading of exactly 0.0 or 1.0 therefore means the floor below failed, not
that the window was quiet, and no run has produced one.

⚠ **It is coarse and heavily tied.** 19 possible values at `length` 20, and
on a 1,500-bar walk only **10** of them appear, with 0.50 taking 402 of the
1,480 fired bars (0.50 is also the modal value on six of the nine frames
measured). A rank statistic over this column carries many tied ranks by
construction. It is a state, not an event flag: neighbouring windows share
19 of their 20 returns, so the column autocorrelates at 0.8323 at lag 1,
0.5937 at lag 5, 0.3495 at lag 10 and 0.1300 at lag 20 on that walk.

The level to expect: on independent windows of iid returns the column sits
at 0.5 for any SYMMETRIC distribution -- the reflection `x -> 2u - x`
preserves the law and swaps the above-mean and below-mean counts, so the
tails change the spread and not the centre: measured mean 0.4999 and sd
0.0676 over 20,000 gaussian windows, 0.4991 and sd 0.1374 for student-t(2).
It moves off 0.5 only with skew: 0.3771 for exponential returns, 0.6229 for
their mirror.

Source: tsfresh feature_calculators (MIT), `count_above_mean`, as the formula
is stated by PandasTa issue #97: `count_above_mean / n on 20 returns`.
⚠ tsfresh is NOT installed in this worktree and web access is unavailable, so
the formula under test is the issue's line plus the published definition of
`feature_calculators.count_above_mean` -- `np.where(x > np.mean(x))[0].size`
-- and not a read of tsfresh's own code; anything tsfresh does that those do
not state (how it treats NaNs) is unverified here. The 20 is the issue's own
parameter.

**This column IS the screen prototype, bit-for-bit, apart from the warm-up
bar and the guards.** Issue #97's prototype
(`docs/issues/screen/ind_screen.py`, candidate `ts_above_mean_20`, local to
the owner's machine) is `roll(ret(c), 20, w_count_above_mean)` with
`w_count_above_mean(W) = (W > W.mean(1, keepdims=True)).mean(1)` -- the same
windows, the same mean, the same strict comparison. Measured on nine
1,500-bar frames: **bit-equal on 1,480 of 1,480** shared fired bars of each,
Spearman 1.000000. The two NaN masks differ, in exactly two ways and both in
this port's favour:
* the prototype's first fired bar is 19, not 20, and that bar reads **0.00**
  -- its window holds the undefined first return, whose NaN mean makes every
  comparison False. It is the arithmetically impossible value above,
  produced on every frame;
* a non-finite close empties this port's windows and not the prototype's: one
  NaN at bar 200 of a 1,500-bar walk leaves 22 bars where one is NaN and the
  other is not, with 1,459 of 1,459 bit-equal elsewhere.
Because Gate E's statistic is a Spearman over the bars where both fire, the
screen's figures (max |rho| 0.3594 vs `PVT_Slope_norm`, n = 396,970) are
expected to carry over; the launcher's Gate E run on THIS module is still the
number that decides ship or revert.

The arithmetic is checked independently rather than trusted, and at this
column's granularity "checked" means EXACT and not a tolerance. The source
applied window by window -- every window handed to a retype of
`count_above_mean`, no shared code -- is bit-equal on 1,480 of 1,480 bars of
each of nine frames. A `math.fsum` scalar loop is bit-equal on three of them.
Against an EXACT rational oracle in `fractions.Fraction` (every float return
is a rational, so the window mean is one and every comparison is decided with
no rounding at all) the column is exact on 1,480 of 1,480 bars of a walk, a
tick-rounded frame, a two-point frame and a right-skewed frame, and on
580 of 580 bars of a path whose returns have `|mean| / sd` = 1e5, which is
where the sum's cancellation is worst. The float mean has not flipped a
single comparison in any run here.

Four readings the wording leaves open, decided and priced in
docs/TsAboveMean20Measured.md (A5) rather than assumed, each on the same
1,500-bar walk:
* The returns are SIMPLE (`close/close.shift(1) - 1`), the prototype's `ret`.
  Log returns are a different column, though a close one: Spearman 0.983938,
  bit-equal on 1,395 of 1,480 bars, max |difference| 0.1000.
* `length` is 20 RETURNS, so 21 closes, and the first value lands at bar 20.
  Rejected: 20 CLOSES, i.e. 19 returns (Spearman 0.888618, max |difference|
  0.2237) -- the off-by-one a reader makes, priced so it is not re-argued.
  Rejected too: the statistic of the 20 CLOSES rather than of the returns,
  which is a different question entirely (Spearman 0.091872).
* The comparison is STRICT, the source's `>`. This is the one choice that no
  frame here can see: a tie with a 20-way AVERAGE does not happen by
  accident, and `>=` is bit-equal on 1,480 of 1,480 bars of a walk, of a
  tick-rounded frame and of a two-point frame, with **0** exact ties in
  29,600 window/return pairs of each. It is pinned by a constructed window
  instead -- closes [100, 50, 50, 75] have returns [-0.5, 0.0, +0.5], which
  sum to exactly 0.0, so at `length` 3 the strict form reads 1/3 and `>=`
  reads 2/3.
* The output is the SHARE, the issue's `count_above_mean / n`. The raw count
  is an exact rescaling by `length` (Spearman 1.000000), so it is the one
  choice a rank miner cannot see.

Causal: bar T reads closes T - length .. T, measured by a future-perturbation
sweep and by the mutant tests in `tests/test_ts_above_mean_20.py`.
Scale-free: every input is a price ratio, and `8a / 8b` is the same double as
`a / b`, so the column is bit-identical under a x8/x64 rescale of price
(1,480 of 1,480 fired bars on each of nine frames, and 1,497 / 1,495 / 1,440
/ 1,250 at `length` 3 / 5 / 60 / 250 on the walk). x10, x3.7, x0.1 and
x1.0000001 are NOT bit-identical by construction -- they perturb the returns
in their last bits -- but they were measured bit-equal anyway, on all nine
frames and on 199,980 windows of a 200,000-bar walk. That is a measurement
with its margin measured too: a count moves only when a perturbation reorders
a return and its own window mean, the smallest gap `|r - m| / max|r|` seen in
those 199,980 windows is **1.559e-07**, and one ulp is about 2.2e-16. Nine
orders of magnitude, not a guarantee.
NaN on the first `length` bars; on any window holding a close that is NaN,
infinite, zero, negative or subnormal (such a close spoils two returns, so it
empties the `length + 1` = 21 windows it sits in -- measured at bar 200 of a
400-bar frame, with 0 earlier bars moved, and fewer near either end: 1 / 2 /
20 / 21 / 2 / 1 bars for a bad close at bar 0 / 1 / 19 / 200 / 398 / 399);
on any window holding a return whose magnitude reaches 4.49e+306; and on any
window whose `length` returns are equal to within 4096 ulps of the largest of
them, which 21 identical closes are one way to reach.
**And it stays LOCAL**, which separates this column from this fork's
`ts_ac1_60` and `ts_cid_ce_20`: every window is reduced from its own
`length` values by `sliding_window_view`, so nothing is accumulated across
windows. Measured on a 2,000-bar frame priced at 1e-198 (so that even the
largest jump leaves every close a normal float) with a single return planted
at bar 200: at x1e+02, x1e+06, x1e+08, x1e+100 and x1e+300 the 20 windows
holding it all read **0.05** -- the right answer, one return above the mean
-- and every one of the 1,780 bars from 220 on is BIT-IDENTICAL to the
unspiked frame. At x1e+307, above the per-return bound, those 20 windows are
NaN and the 1,780 later bars are still bit-identical.

Cost: three O(n * length) reductions over a `sliding_window_view` (the sum
and the two extrema) plus `length` contiguous comparisons, and no allocation
that grows with `length` -- the traced peak is 29.2 MB on 400,000 bars at
each of `length` 3, 20, 60 and 250, and the call takes roughly 48-74 ms there
at `length` 3-20 and 110-265 ms at 60-250 (this machine's milliseconds, which
move by a few per cent between runs; the peak is the claim). The
window-by-window oracle this was checked against is 0.12 s on 20,000 bars
where this module is 3.2 ms, which is why it lives in
docs/measure_ts_above_mean_20.py and not here.

Calculation:
    Default Inputs:
        length=20
    r[t]               = close[t] / close[t-1] - 1
    m                  = mean of the trailing `length` r
    TS_ABOVE_MEAN[T]   = (count of those r strictly above m) / length,
                         NaN where the window's returns span 4096 ulps or
                         less of their own largest magnitude

Args:
    close (pd.Series): Series of 'close's
    length (int): Returns per window. At least 3 -- a window of two returns
        is identically 1/2 -- so a smaller or missing value falls back to the
        default. At 3 the column takes exactly the two values 1/3 and 2/3
        (measured). Default: 20
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)

Returns:
    pd.Series: TS_ABOVE_MEAN_{length}, dimensionless, on the 19 values
        1/20 .. 19/20 at length 20
"""
