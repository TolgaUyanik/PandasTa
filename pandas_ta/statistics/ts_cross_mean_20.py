# -*- coding: utf-8 -*-
import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from pandas import Series

from pandas_ta.utils import get_offset, verify_series

# A window of TWO log closes is identically 1 crossing: of two unequal
# numbers exactly one is above their midpoint, so the single adjacent pair
# always straddles the mean, and two equal ones are refused by the floor
# below. Three closes is the smallest window on which the column varies, and
# there it takes only 1 and 2.
MIN_LENGTH = 3
# What this column reads is the ORDER of the window's log closes against
# their own mean, so the question a floor must answer is not "is the
# dispersion big enough to divide by" (there is no division by it here) but
# "is the dispersion bigger than the error in the mean the comparisons are
# made against".
#
# That error scales with the window's own magnitude, so the floor is RELATIVE
# -- `NOISE_FACTOR * max |x|` -- and not the absolute `4096 eps` that
# `statistics/ts_c3_20.py`, `statistics/ts_binent_20.py` and
# `statistics/ts_cid_ce_20.py` use. It is the same choice and the same 4096
# ulps as `statistics/ts_above_mean_20.py`, and the quantity it multiplies is
# the only difference: `max |log close|` here, `max |return|` there.
#
# What an absolute floor would cost here is measured, not assumed
# (docs/TsCrossMean20Measured.md, Guards G3). On the ordinary frames the
# two are indistinguishable -- flat 0/0, walk 1,481/1,481, ladder 281/281,
# halt-patches 1,343/1,343 -- because a degenerate window's log spread is
# EXACTLY 0.0 and both thresholds refuse it. They part company where
# `|log c|` is far from 1: at a price near 1.0 the relative floor reports
# all 581 windows of a 600-bar frame and a 60-digit oracle confirms every
# one of them, where the absolute floor keeps 44.
#
# With `spread > NOISE_FACTOR * amax` the computed mean is strictly INSIDE
# the window's range, which is what keeps the count between 1 and
# `length - 1`: the exact mean is at most `hi - spread/length`, so it clears
# `hi` by more than `4096/length` = 204.8 ulps of `amax` at `length` 20.
# Against that, the error in the COMPUTED mean: summation of `length` terms
# is out by at most `(length - 1) * eps * sum|x| <= (length - 1) * length *
# eps * amax`, so after the division by `length` the mean is out by at most
# `(length - 1) * eps * amax` = 19 ulps, plus one more for the division
# itself. About a 10x margin, and the `1 <= count <= length - 1` it buys is
# COUNTED over every window of every frame in
# docs/measure_ts_cross_mean_20.py (Gate A4).
#
# ⚠ The floor is invariant under a price rescale only to the extent the LOG
# of the rescaled price is -- which is not exactly, since `log(8p)` is not
# `log(8) + log(p)` in binary floating point. See the docstring's Gate D
# paragraph: nothing here is bit-identical BY CONSTRUCTION, and the x8/x64
# bit-equality is a measurement with a measured margin.
NOISE_ULPS = 4096
NOISE_FACTOR = NOISE_ULPS * np.finfo(float).eps  # 9.09e-13, RELATIVE


def ts_cross_mean_20(close, length=None, offset=None, **kwargs):
    """Indicator: crossings of the window mean by log price (TS_CROSS_MEAN)"""
    # Validate Arguments
    length = int(length) if length and int(length) >= MIN_LENGTH else 20
    close = verify_series(close, length)
    offset = get_offset(offset)

    if close is None: return

    # Calculate Result
    c = close.to_numpy(dtype=float)
    # A close that is not a finite, normal, positive float (NaN, inf, zero,
    # negative, or subnormal such as 1e-310) is bad data and is dropped here
    # rather than fed to `log`. Zero and negative have no logarithm at all;
    # a SUBNORMAL has one, but it carries fewer than 53 significant bits, so
    # the error in its log is far larger than the `eps * |log c|` the floor
    # below is calibrated against -- the one quantity this column's
    # comparisons are decided within.
    c = np.where(np.isfinite(c) & (c >= np.finfo(float).tiny), c, np.nan)
    # LOG closes, the issue's own wording, and the one thing that makes this
    # module's float story different from its siblings'. The fork's
    # RETURN-based tsfresh ports (`ts_above_mean_20`, `ts_binent_20`,
    # `ts_c3_20`, `ts_cid_ce_20`, `ts_kurt_60`, `ts_ac1_60`, `ts_aggac_60`,
    # `ts_medskew_20`) read price RATIOS, where `8a / 8b` is the same double
    # as `a / b`; `ts_peaks_20` and `ts_perment_20` read raw closes and only
    # their ORDER, which a rescale cannot change either. This one takes a
    # LOGARITHM, and `log(8p)` is not `log(8) + log(p)` in binary floating
    # point -- so here the x8/x64 bit-equality is a MEASUREMENT with a
    # measured margin behind it, not a construction. `np.log` of a NaN
    # is a NaN and raises nothing (every other bad input was replaced above),
    # so no `errstate` is needed; pinned by
    # `tests/test_ts_cross_mean_20.py::test_no_warning_is_raised_on_bad_closes`.
    #
    # The sum below cannot overflow and needs no magnitude bound to say so:
    # the smallest normal double is 2.23e-308 and the largest is 1.80e+308,
    # so `|log c| <= 709.79` for every close that survived the line above,
    # and the largest `length` this function will see could not push
    # `length * 709.79` anywhere near 1.8e+308. That is a derivation, not a
    # guard -- `ts_above_mean_20` needs one because a price RATIO is
    # unbounded, and a logarithm is not.
    x = np.log(c)

    windows = sliding_window_view(x, length)
    # The window mean, from that window's own `length` values. `.sum(axis=1)`
    # on the view and not `rolling.mean()`: pandas' rolling mean is an ONLINE
    # accumulator, which is what makes a single enormous value poison every
    # later window of the frames measured in `ts_cid_ce_20`'s receipt.
    mean = windows.sum(axis=1) / length
    hi, lo = windows.max(axis=1), windows.min(axis=1)

    # tsfresh's `number_crossing_m`: `positive = x > m`, then count the
    # adjacent pairs that disagree -- `np.where(np.diff(positive))[0].size`.
    # STRICTLY above, which is the source's `>`: a close that ties the mean
    # counts as below. `>=` is a different column and is priced in
    # docs/TsCrossMean20Measured.md (Gate A5).
    #
    # Two `(rows,)` boolean columns carried forward, rather than the source's
    # own two lines spelled literally -- `above = windows > mean[:, None]`
    # then `above[:, 1:] != above[:, :-1]` -- which materialises two
    # `(rows, length)` bool arrays. The two agree on every count (measured
    # on 400,000 bars: 399,998 / 399,981 / 399,941 / 399,751 of the same
    # fired bars at `length` 3 / 20 / 60 / 250) and what
    # separates them is MEMORY: this form's traced peak is 29.2 MB on
    # 400,000 bars at every one of those lengths, where the matrix form's
    # grows 30.0 / 36.8 / 66.9 / 218.8 MB. ⚠ TIME is NOT a reason either
    # way and is deliberately not claimed: which spelling wins at a given
    # `length` CHANGED between runs of the same measurement on this
    # machine, even taking the best of three after a warm-up call: at
    # `length` 60 the winner has gone BOTH WAYS across the runs on
    # record. (Without the warm-up it is worse still: an ordered A/B
    # reads backwards, whichever spelling goes second.) The peaks are the
    # claim; the runs are tabulated in
    # docs/TsCrossMean20Measured.md (Z).
    # `tests/test_ts_cross_mean_20.py` pins the agreement and the memory
    # crossover, because the two are behaviourally identical and only the
    # cost separates them.
    count = np.zeros(windows.shape[0], dtype=np.int64)
    prev = windows[:, 0] > mean
    for j in range(1, length):
        cur = windows[:, j] > mean
        count += cur != prev
        prev = cur

    # `hi - lo` is the window's log range and `max(hi, -lo)` its largest
    # absolute log close, both from the same two reductions. A window holding
    # a NaN has NaN for both, and `NaN > anything` is False, so this one test
    # is also what empties a window with a bad close in it -- pinned by
    # `tests/test_ts_cross_mean_20.py::test_a_bad_close_empties_its_windows`
    # so the behaviour cannot drift to a silent count of 0.
    reported = (hi - lo) > NOISE_FACTOR * np.maximum(hi, -lo)

    out = np.full(c.size, np.nan)
    out[length - 1:] = np.where(reported, count, np.nan)
    crossings = Series(out, index=close.index)

    # Offset
    if offset != 0:
        crossings = crossings.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        crossings.fillna(kwargs["fillna"], inplace=True)

    # Name and Categorize it
    crossings.name = f"TS_CROSS_MEAN_{length}"
    crossings.category = "statistics"

    return crossings


ts_cross_mean_20.__doc__ = \
"""Crossings of the window mean by log price (TS_CROSS_MEAN)

How CHOPPY the last `length` closes were. ⚠ A CHOPPINESS reading, not a
volatility or a direction one. How many times the log price crossed its own
window mean -- tsfresh's `number_crossing_m` with `m` the window's mean.

    x              = the window's `length` log closes
    m              = their arithmetic mean (so `exp(m)` is the window's
                     GEOMETRIC mean close)
    TS_CROSS_MEAN  = how many adjacent pairs of x sit on opposite sides of m

A monotone window reads **1** whatever its slope, and a window that
alternates above and below reads **19** at `length` 20; both ends are
reached by construction. So the column is a count of mean reversions inside
the window, and it is NOT a count of sign changes in the returns: against
`number_crossing_m(log returns, m=0)`, the other way this source function is
usually called, it reads Spearman 0.176569 on a walk.

⚠ **What it overlaps.** It is the fork's `chop` family seen from another
angle: on six synthetic frames it reads Spearman +0.5289 to +0.6296 against
`chop`, -0.4813 to -0.5607 against `vhf`, -0.1694 to -0.2895 against
`LEAN_MOMERSION_20`, +0.2171 to +0.4812 against `TS_PERMENT_20_3` and
+0.2145 to +0.3540 against `TS_PEAKS_20_2` (the last two over the SAME 20
closes). Those are SYNTHETIC. The real-frame figures that exist are the
2026-10-24 screen's, taken on its prototype and not on this module: Gate E
max |rho| **0.5500** vs `BB_BWidth_Pctl` over n = 391,907, then `BB_BWidth`
0.5095 and `chop` 0.4925, with a per-frame max median of 0.5495 -- SHIP on
every band -- and a stage-2 fork overlap of 0.5684 vs
`squeeze_pro:SQZPRO_ON_WIDE` over 12 frames. The screen's own candidate-pair
list, which records every pair at |rho| >= 0.8019, does not contain this
candidate at all. The launcher's Gate E run on THIS module is the number
that decides ship or revert.

⚠ **It is a DISPERSION reading upside down, and that is the one thing to
know before using it as a regime flag.** A window whose log closes spread
out is a window that trended, and a trending window crosses its mean once:
on a walk the Spearman against the window's own log-close standard deviation
is **-0.6827**, against |log close[T] - log close[T-19]| -0.3906 and against
that drift divided by the window's realised volatility -0.4053. Against the
realised volatility ALONE it is only +0.1045, and against the close itself
-0.1178, so it is the SHAPE of the window and not its size that moves this
column. The level to expect, over 20,000 independent windows: **3.6674**
(sd 2.2007) for a driftless gaussian walk, **1.1946** (sd 0.6461) once a
1-sd-per-bar drift is added, and **9.8399** (sd 2.1603) for log closes that
are white noise rather than a walk.

⚠ **It is BOUNDED, and the bounds are 1 and `length - 1`, not 0 and
`length - 1`.** The window mean lies strictly between the window's own
extremes unless every value is equal, so at least one close is above it and
at least one is not, and the sequence has to switch at least once. A reading
of exactly **0 is arithmetically impossible** and means the floor below
failed; no run here has produced one from this function, and the UNGUARDED
spelling produces 281 of them on a 300-bar flat frame. 19 at `length` 20
needs a perfectly alternating window and is reached by construction; the
largest any of nine 1,500-bar frames reaches is 16, on a two-point frame.

⚠ **It is coarse and heavily tied.** 19 possible values at `length` 20, of
which a 1,500-bar walk shows 13, with the value 1 taking 339 of 1,481 fired
bars. A rank statistic over this column carries many tied ranks by
construction. It is a state, not an event flag: neighbouring windows share
19 of their 20 closes, so the column autocorrelates at 0.8519 at lag 1,
0.3000 at lag 5, -0.0481 at lag 10 and -0.0172 at lag 20 on that walk.

Source: tsfresh feature_calculators (MIT), `number_crossing_m`, as the
formula is stated by PandasTa issue #100: `number_crossing_m(x, m=mean) on
20 log closes`.
⚠ tsfresh is NOT installed in this worktree and web access is unavailable,
so the formula under test is the issue's line plus the published definition
of `feature_calculators.number_crossing_m` -- `positive = x > m` then
`np.where(np.diff(positive))[0].size` -- and not a read of tsfresh's own
code; anything tsfresh does that those do not state (how it treats NaNs) is
unverified here. The 20 is the issue's own parameter, and so is `m = mean`:
the source function takes any level.

**This column IS the screen prototype, bit-for-bit, apart from the guards.**
Issue #100's prototype (`docs/issues/screen/ind_screen.py`, candidate
`ts_cross_mean_20`, local to the owner's machine) is
`roll(np.log(c), 20, w_crossings_mean)` with
`w_crossings_mean(W) = (s[:, 1:] != s[:, :-1]).sum(1)` over
`s = W > W.mean(1, keepdims=True)` -- the same windows, the same mean, the
same strict comparison, the same first fired bar. Measured on nine
1,500-bar frames: **bit-equal on 1,481 of 1,481** bars of each, with
IDENTICAL NaN masks, Spearman 1.000000. They part company only where a
guard fires: on a 300-bar flat frame the prototype reports 281 windows of
the impossible 0 and this port reports none, and one NaN close at bar 200 of
a 1,500-bar walk empties 20 windows here that the prototype reads 0 on.
Because Gate E's statistic is a Spearman over the bars where both fire, the
screen's figures are expected to carry over; the launcher's run on THIS
module is still the number that decides.

The arithmetic is checked independently rather than trusted, and at this
column's granularity "checked" means BIT-EQUAL and not a tolerance. The
source applied window by window -- every window handed to a retype of
`number_crossing_m`, no shared code -- is bit-equal on 1,481 of 1,481 bars
of each of nine frames. A `math.fsum` scalar loop over the C library's
`math.log` is bit-equal on three of them. And against an oracle that decides
every comparison at **60 significant digits** (`decimal.Decimal.ln`, about
44 digits beyond a double) the column is bit-equal on 1,481 of 1,481 bars of
a walk, a tick-rounded frame, a two-point frame and a trending frame, and on
581 of 581 bars of quiet frames priced at 1e+6 and 1e-6, where the
cancellation between a log close and its window mean is worst.
Only that last check can witness the one thing this column's arithmetic
can get wrong. The first two compare a double pipeline against another
double pipeline: if the double logarithm of a close sits on the wrong
side of the double mean, the module and both of them put it there
together. So the count of windows on which float is known to have decided
every comparison correctly is the 60-digit oracle's **5,924 + 1,743**,
and not A1's 13,329 or A2's 4,443; five of the nine frames have never
been put to an exact oracle at all.
⚠ That is a scope and NOT a guarantee. The floor refuses the regime where
float is badly wrong -- bucketed by each window's own
`(hi - lo) / (eps * max|x|)`, the unguarded count agrees with the 60-digit
oracle on only 0.5678 of the windows below 16 ulps -- but it does not make
the arithmetic exact: on the ramped-volatility frame built for that
measurement, **one ADMITTED window in 351**, in the bucket just above the
floor, is miscounted. See docs/TsCrossMean20Measured.md (Guards G3b),
which also records how far the ordinary frames sit from that edge: the
worst window of the nine is at 1.27e+13 ulps, nine orders above the floor.

Four readings the one-line formula leaves open, decided and priced in
docs/TsCrossMean20Measured.md (A5) rather than assumed, each on the same
1,500-bar walk:
* The window holds LOG closes, the issue's own wording, so the threshold is
  the window's GEOMETRIC mean close. On the raw closes the threshold is the
  arithmetic mean instead, which is a different and slightly higher line:
  Spearman 0.990557, bit-equal on 1,443 of 1,481 bars, max difference 2.
* `length` is 20 CLOSES, not 20 returns, so the first value lands at bar 19
  and not bar 20. On 20 returns the column is a different question
  altogether -- Spearman 0.147259, bit-equal on 35 of 1,481 bars.
* The comparison is STRICT, the source's `>`. This is the one choice no
  frame here can see: a tie with a 20-way average does not happen by
  accident (0 exact ties in 88,860 window/close pairs of three frames), and
  at `length` 3 a tie cannot separate the two spellings at all -- a tied
  value is not above the mean, and its two neighbours cannot both be: with
  `x1 = m` the three values sum to `3m`, so `x0 + x2` is exactly `2m`, and
  two values both strictly above `m` would sum to MORE than that. It is
  pinned at `length` 4 by a constructed window instead: the closes
  **[12, 6, 18, 1]** multiply to 6**4, so the exact mean of their logs is
  log(6) and the second close ties it bit-for-bit -- the strict form reads
  3 and `>=` reads 1.
* The output is the RAW COUNT, the source function's own return value.
  Dividing by `length - 1` is an exact rescaling (Spearman 1.000000), so it
  is the one choice a rank miner cannot see.

Causal: bar T reads closes T - length + 1 .. T, measured by a
future-perturbation sweep and by the mutant tests in
`tests/test_ts_cross_mean_20.py`.
Scale-free, and ⚠ **nothing here is bit-identical BY CONSTRUCTION**, which
is where this column's float story parts from its siblings'. The fork's
RETURN-based tsfresh ports (`ts_above_mean_20`, `ts_binent_20`,
`ts_c3_20`, `ts_cid_ce_20`, `ts_kurt_60`, `ts_ac1_60`, `ts_aggac_60`,
`ts_medskew_20`) read price RATIOS, where `8a / 8b` is the same double as
`a / b`; `ts_peaks_20` and `ts_perment_20` read raw closes and only their
ORDER, which a rescale cannot change either. This one takes a LOGARITHM,
and `log(8p)` is not `log(8) + log(p)` in binary floating point. Every
rescale perturbs the log closes in their last bits, and what holds the
COUNT still is a margin, measured: the smallest `|x - mean| / max|x|` over
the 199,981 windows of a 200,000-bar walk is **6.927e-10** against an ulp
of 2.2e-16, six orders of magnitude. With that margin the column is
bit-equal on 1,481 of 1,481 bars of each of nine frames at x8 and x64, and
on 1,498 / 1,496 / 1,441 / 1,251 fired bars at `length` 3 / 5 / 60 / 250 on
the walk; also at x10, x3.7, x0.1 and x1.0000001 on all nine frames, and on
all 199,981 windows of that 200,000-bar walk and of a 200,000-bar
tick-rounded copy of it.
Stronger than a rescale, and under exactly the same caveat: the count
reads only the ORDER of the log closes against their own mean, so any
strictly monotone power map of the price leaves the EXACT count alone --
`x -> a*x` preserves that order for `a > 0` and reverses all of it for
`a < 0`, which leaves the number of SWITCHES untouched. In doubles it is a
measurement and not a construction, because `log(p**a)` is no more exactly
`a * log(p)` than `log(8p)` is `log(8) + log(p)`: three maps were measured,
`price ** 2`, `price ** 0.5` and `1 / price`, bit-equal on 1,481 of 1,481
bars of the walk.
NaN on the first `length - 1` bars; on any window holding a close that is
NaN, infinite, zero, negative or subnormal (such a close empties the
`length` = 20 windows it sits in -- measured at bar 200 of a 400-bar frame,
with 0 earlier bars moved, and fewer near either end: 1 / 2 / 19 / 20 / 2 /
1 bars for a bad close at bar 0 / 1 / 18 / 200 / 398 / 399); and on any
window whose log closes span 4096 ulps or less of the largest of them,
which 20 identical closes are one way to reach.
**And it stays LOCAL**: every window is reduced from its own `length`
values by `sliding_window_view`, so nothing is accumulated across windows.
Measured on a 2,000-bar frame with one close multiplied at bar 200: at
x1e+02, x1e+06, x1e+08, x1e+100 and x1e+300 every one of the 1,780 bars
from 220 on is BIT-IDENTICAL to the unspiked frame, and the 20 windows
holding the spike read 1 or 2. The prototype is local here too.

Cost: three O(n * length) reductions over a `sliding_window_view` (the sum
and the two extrema) plus `length` contiguous comparisons, and no allocation
that grows with `length` -- the traced peak is 29.2 MB on 400,000 bars at
each of `length` 3, 20, 60 and 250, where the matrix spelling of the same
count reaches 218.8 MB at 250. Across the runs on record the call
takes 33.5-102.3 ms there at `length` 3-60 and 269.7-312.9 ms at 250
(this machine's milliseconds, best of three after a warm-up call; the
250-bar figure moved by 16% between runs, so the peak is the claim and
the time is not). The
window-by-window oracle this was checked against is about TWO ORDERS
slower on 20,000 bars -- 159.8 to 174.8 ms against this module's 2.8 to
3.5, from cold single calls that the script does not warm up, so the gap
is the claim and the endpoints are observations -- which is why it lives
in
docs/measure_ts_cross_mean_20.py and not here.

Calculation:
    Default Inputs:
        length=20
    x[t]               = log(close[t])
    m                  = mean of the trailing `length` x
    TS_CROSS_MEAN[T]   = how many of the 19 adjacent pairs of that window
                         straddle m, i.e. tsfresh's
                         np.where(np.diff(x > m))[0].size,
                         NaN where the window's log closes span 4096 ulps
                         or less of their own largest magnitude

Args:
    close (pd.Series): Series of 'close's
    length (int): Closes per window. At least 3 -- a window of two closes
        is identically 1 crossing -- so a smaller or missing value falls
        back to the default. At 3 the column takes exactly the two values
        1 and 2 (measured). Default: 20
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)

Returns:
    pd.Series: TS_CROSS_MEAN_{length}, a dimensionless integer count on
        1 .. length - 1, i.e. 1 .. 19 at length 20
"""
