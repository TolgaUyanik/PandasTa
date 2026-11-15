# -*- coding: utf-8 -*-
import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from pandas import Series

from pandas_ta.utils import get_offset, verify_series

# A window of TWO returns has its mean equal to its median by construction,
# so the column is identically 0.0 there. Three returns is the smallest
# window on which it varies.
MIN_LENGTH = 3
EXTRA_CLOSES = 1  # `length` returns need `length + 1` closes
# The numerator is a DIFFERENCE of two centre readings that are usually close
# together, and the denominator is the window's own dispersion, so what a
# floor has to answer here is "is the dispersion bigger than the rounding in
# the two centres". Both roundings scale with the window's own magnitude, so
# the floor is RELATIVE -- `NOISE_FACTOR * max |r|` -- and not the absolute
# `4096 eps` of `statistics/ts_c3_20.py`, `statistics/ts_binent_20.py` and
# `statistics/ts_kurt_60.py`. `statistics/ts_above_mean_20.py` floors the same
# way for the same reason.
NOISE_ULPS = 4096
NOISE_FACTOR = NOISE_ULPS * np.finfo(float).eps  # 9.09e-13, RELATIVE


def ts_medskew_20(close, length=None, offset=None, **kwargs):
    """Indicator: mean-minus-median of returns over their sd (TS_MEDSKEW)"""
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
    # Every kept return satisfies `r**2 < max / (8 * length)`, so a window's
    # squared deviations -- each at most `(2 max|r|)**2` -- sum to at most
    # half the float maximum and the standard deviation is a real number
    # rather than an infinity, which would report 0.0 on every bar of the
    # window instead of NaN. A comparison against NaN or inf is False, so this
    # one test also drops both. The ceiling it puts on a return is 1.06e+153
    # at `length` 20: nothing a market can produce.
    with np.errstate(over="ignore"):
        square = r * r
    r = np.where(square < np.finfo(float).max / (8 * length), r, np.nan)

    windows = sliding_window_view(r, length)
    # The window mean and the window standard deviation, both from that
    # window's own `length` values, and the sd TWO-PASS (`ddof=1`, the
    # prototype's `rolling.std`). `sliding_window_view` and not
    # `rolling.mean()/.std()`: pandas' rolling moments are ONLINE
    # accumulators, which is what makes a single enormous value poison every
    # later window of the frames measured in `ts_cid_ce_20`'s receipt.
    mean = windows.sum(axis=1) / length
    # One `(rows,)` deviation per window POSITION rather than the one-liner
    # `((windows - mean[:, None])**2).sum(axis=1)`, which materialises a
    # `(rows, length)` float array. The two agree to 1.1e-16 (measured, on
    # 19,980 windows) and differ in cost: at n = 400,000 the traced peak is
    # 42.0 MB here against 76.9 MB at `length` 20 and 812.4 MB at `length`
    # 250, where this form does not grow with `length` at all.
    ssd = np.zeros(windows.shape[0])
    for j in range(length):
        d = windows[:, j] - mean
        ssd += d * d
    sd = np.sqrt(ssd / (length - 1))

    # The window MEDIAN, from pandas' rolling skip list rather than from a
    # second reduction over `windows`: `np.median(windows, axis=1)` partitions
    # a COPY of the whole view, so its peak grows with `length` exactly as the
    # matrix form above does -- 825.5 MB at `length` 250 against 42.0 MB
    # here, for a column that is BIT-EQUAL on all 19,980 windows measured
    # (it is also about three times slower there, but the PEAKS are the
    # claim: the milliseconds move between runs).
    # The skip list only ever compares and (for an even
    # `length`) averages two of the window's own values, so unlike the
    # prototype's `rolling.mean()`/`rolling.std()` it neither accumulates
    # error nor carries a value past the window that holds it
    # (docs/TsMedskew20Measured.md, Guards G7).
    median = Series(r, index=close.index) \
        .rolling(length, min_periods=length).median().to_numpy()[length - 1:]

    hi, lo = windows.max(axis=1), windows.min(axis=1)
    # `hi - lo` is the window's range and `max(hi, -lo)` its largest absolute
    # return, both from the same two reductions. A window holding a NaN return
    # has NaN for both, and `NaN > anything` is False, so this one test is
    # also what empties a window with a bad close in it.
    reported = (hi - lo) > NOISE_FACTOR * np.maximum(hi, -lo)

    with np.errstate(invalid="ignore", divide="ignore"):
        value = (mean - median) / sd
    # A labelled BACKSTOP with NO witness, kept deliberately. Over the 14
    # frames swept for docs/TsMedskew20Measured.md (Guards G4) there is not
    # one bar where the floor above reports and this value is not finite, and
    # that is arithmetic rather than luck: the smallest non-zero return a
    # close pair can produce is an ulp of 1.0 (1.110e-16 downwards), the
    # floor above only admits a window whose spread `s` clears
    # `4096 eps * max|r|`, and the two extremes of such a window straddle
    # its mean -- so one of them is at least `s/2` from it and the
    # squared-deviation SUM is at least 2.5e-57, against a smallest
    # subnormal of 4.9e-324. `sd` cannot be 0 on a window the floor
    # reports. It costs
    # one pass over a `(rows,)` array, and it is what makes the exactly-zero
    # case in that file's Gate B probe behave the way it does -- there the
    # window's sd IS 0, and this line is what empties the bar whatever the
    # floor says.
    reported &= np.isfinite(value)

    out = np.full(c.size, np.nan)
    out[length - 1:] = np.where(reported, value, np.nan)
    medskew = Series(out, index=close.index)

    # Offset
    if offset != 0:
        medskew = medskew.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        medskew.fillna(kwargs["fillna"], inplace=True)

    # Name and Categorize it
    medskew.name = f"TS_MEDSKEW_{length}"
    medskew.category = "statistics"

    return medskew


ts_medskew_20.__doc__ = \
"""Mean-minus-median of returns over their sd (TS_MEDSKEW)

The NONPARAMETRIC skewness of the last `length` returns. ⚠ Overlaps the
shipped TS_ABOVE_MEAN_20 at 0.8428 on real frames. How far those returns'
mean sits above or below their median, in units of their own standard
deviation -- Pearson's second coefficient without its factor 3. (The first
two sentences are short on purpose: `docs/gen_indicator_dictionary.py`
keeps only the first 150 characters of this paragraph for
`docs/IndicatorDictionary.md`, which CLAUDE.md sends a reader to first, so
the overlap has to fit inside them.)

    x            = the window's `length` simple returns
    TS_MEDSKEW   = (mean(x) - median(x)) / sd(x),  sd with ddof=1

⚠ **It is a SKEWNESS reading, and this fork already ships two.** Against
the windows' own textbook sample skewness, over 20,000 independent
20-return windows drawn from a symmetric, a right-skewed and a left-skewed
law, the Spearman is **+0.8803**.
* Against the shipped `TS_ABOVE_MEAN_20` (issue #97, merged 2026-11-13,
  the share of a window's returns above its own mean -- a BACKWARDS
  skewness reading, hence the sign): **-0.8885** on a walk, **-0.9025**
  heavy-tailed, -0.8854 / -0.8824 / -0.8894 / -0.8920 on ar1+ / ar1- /
  tick-rounded / trending, -0.7288 two-point, -0.3941 on the two
  exponential frames.
  ⚠ Those are SYNTHETIC. The REAL-frame figure for this pair is the
  screen's pooled **0.8428** (2026-10-24, over the 89 ALTPORT-1 frames),
  which is DISCLOSE_GAP and not STRUCK under `r3-perframe-0.90` -- and it
  is the most adverse number on record for either column. Gate E cannot
  re-measure it: its 687 comparators are the engine's and hold no
  pandas_ta port. See docs/TsMedskew20Measured.md §O.
* Against the shipped `OSAP_RETSKEW_21`, the bias-corrected moment
  skewness, at its shipped `length` 21: +0.6485 on a walk, +0.8028
  heavy-tailed, +0.4933 / +0.6520 on ar1-/ar1+, +0.2000 on the exponential
  frames. At `length` 20 that column IS `r.rolling(20).skew()`, and
  docs/TsMedskew20Measured.md's §O3b re-run at 20 reproduces its §O1
  rolling-skew row exactly (+0.6647 on a walk, +0.8220 heavy-tailed) --
  which is the cross-check, and also 0.0162 above the shipped column's
  figure on the walk.

⚠ **It cannot see volatility, direction or the price level.** The
statistic is invariant to any affine map of the returns with a positive
slope: both the numerator and the sd scale with the returns, and a shift
cancels in `mean - median`. Measured on a walk: Spearman **+0.0800**
against the same window's return standard deviation, **-0.1129** against
its mean return, +0.0737 against the close itself; and the column agrees
with itself to 4.0e-14 at `r x 2`, `r x 0.5` and `r + 0.004`.

⚠ **It is BOUNDED, and the bound is not 1.** `|mean - median| <= sd_pop`
is a theorem -- the median minimises `E|x - a|`, so
`|mean - median| <= E|x - median| <= E|x - mean| <= sd_pop` by Jensen --
and this column divides by the ddof=1 sd, so
`|TS_MEDSKEW| <= sqrt((length-1)/length)`, which is **0.974679** at
`length` 20. The largest value any window built for
docs/TsMedskew20Measured.md reaches is **0.881631**, by 11 equal low
returns and 9 equal high ones; 1.2 million random windows from six
families did not beat it, and the gap to the bound is not closed
analytically. A 1,500-bar walk spans [-0.4210, +0.4013] and a two-point
frame reaches the 0.881631 at both signs.
⚠ Its NEIGHBOUR is the surprise: an 11/9 split reads 0.8816 and a 10/10
split reads **0**, because the median then sits between the two levels.
One return of `a` among `length - 1` equal ones is exactly
`sign(a)/sqrt(length)` -- 0.2236 at 20 -- whatever `a` is.

It is a state rather than an event flag: neighbouring windows share 19 of
their 20 returns, so the column autocorrelates at 0.8963 at lag 1, 0.6345
at lag 5, 0.3773 at lag 10 and 0.1360 at lag 20 on a walk. The level to
expect on independent windows of iid returns is 0 for any SYMMETRIC law
(measured mean -0.0006, sd 0.1532 over 20,000 gaussian windows; -0.0002
and sd 0.1659 for student-t(2)) and moves off it only with skew: +0.2832
for exponential returns, -0.2831 for their mirror.

Source: tsfresh feature_calculators (MIT), `symmetry_looking`, as the
formula is stated by PandasTa issue #98: `symmetry_looking, continuous
form: (mean-median)/std on 20 returns`.
⚠ **The named function does not contain this expression.** Published
`feature_calculators.symmetry_looking` compares `|mean - median|` against
`r * (max - min)` and returns a BOOLEAN; the continuous
`(mean - median)/std` form is the ISSUE's own wording, and the two are
different columns -- dividing by the RANGE and taking the absolute value
as that function does reads Spearman **-0.1942** against this one on a
walk. So the attribution is to the idea (mean-against-median as a symmetry
test), not to a line of code.
⚠ tsfresh is NOT installed in this worktree and web access is
unavailable, so the formula under test is the issue's line plus the
published definition of that function, not a read of tsfresh's own code.
The 20 is the issue's own parameter.

**This column is the screen prototype to 5.2e-15, with the same NaN
mask.** Issue #98's prototype (`docs/issues/screen/ind_screen.py`,
candidate `ts_medskew_20`) is
`sdiv(mean(r, 20) - r.rolling(20).median(), std(r, 20))`. Measured on nine
1,500-bar frames: identical masks, 1,480 of 1,480 bars within 5.2e-15,
Spearman 1.000000 on eight of them and 0.999696 on the two-point frame,
where the column is heavily tied and the last bits reorder ties. The two
part company only on the guards -- a constant-return ladder, which the
prototype reads 280 windows of and this module reports none of -- and on
locality (below). Because Gate E's statistic is a Spearman over the bars
where both fire, the screen's figures (max |rho| 0.3727 vs
`PVT_Slope_norm`, n = 396,970) are expected to carry over; the launcher's
Gate E run on THIS module is still the number that decides ship or revert.

The arithmetic is checked independently rather than trusted. The issue's
formula applied window by window, sharing no code with this module, agrees
to **2.2e-16** over 1,480 bars of each of nine frames with identical NaN
masks; a `math.fsum` scalar loop to 1.7e-16 on three of them; and an EXACT
rational oracle -- every float return is a rational, so the mean, the
median and the variance are computed with no rounding at all -- to
3.3e-16 absolute and 8.5e-14 relative. ⚠ The one place the arithmetic is
visibly lossy is a path whose returns have `|mean| / sd` = 1e5, where
`mean - median` cancels five digits: there the agreement is **4.3e-11**
absolute, 1.3e-08 relative. A CLOSED FORM pins the rest: one return of `a`
among `length - 1` equal ones is `sign(a)/sqrt(length)` exactly, measured
to 2.8e-16 at `length` 3, 4, 20 and 60.

Six readings the wording leaves open, decided and priced in
docs/TsMedskew20Measured.md (A5) rather than assumed, each on the same
1,500-bar walk:
* The returns are SIMPLE (`close/close.shift(1) - 1`), the prototype's
  `ret`. Log returns are a near-copy: Spearman 0.999961, max |difference|
  0.0109.
* The sd is the SAMPLE one, `ddof=1` -- the prototype's `rolling.std()`.
  The population sd is `sqrt(length/(length-1))` = 1.025978 times it, a
  CONSTANT at a fixed `length`, so the choice is invisible to a rank miner
  (Spearman 1.000000, ratio constant to 1e-12) and worth 0.0109 to a rule
  with a threshold.
* The numerator is NOT absolute, so the column keeps its sign and reads
  right-skew as positive. Throwing the sign away and keeping the sd
  (`|mean - median| / sd`) is a different column: Spearman **-0.206800**,
  bit-equal on the 642 of 1,480 bars where this one is non-negative.
  Throwing the denominator away as well is the tsfresh form above.
* No factor 3. Pearson's second coefficient is three times this; an exact
  rescaling, so again only a threshold sees it.
* `length` is 20 RETURNS, so 21 closes, and the first value lands at bar
  20. Rejected: 20 CLOSES, i.e. 19 returns (Spearman 0.918816, max
  |difference| 0.3371) -- the off-by-one a reader makes.
* Rejected too: the statistic OF the 20 closes rather than of the returns,
  which is a different question (Spearman 0.123198).

Causal: bar T reads closes T - length .. T, measured by a
future-perturbation sweep (0 of 37 offsets on each of three frames and at
`length` 5, 60 and 250) and by the six mutants in
`tests/test_ts_medskew_20.py`.
Scale-free: every input is a price ratio, and `8a / 8b` is the same double
as `a / b`, so the column is bit-identical under a x8/x64 rescale of price
(1,480 of 1,480 fired bars on each of nine frames, and 1,497 / 1,495 /
1,440 / 1,250 at `length` 3 / 5 / 60 / 250). x10, x3.7 and x0.1 are NOT
bit-identical by construction and agree to 1.2e-13 with exactly matching
NaN masks.
NaN on the first `length` bars; on any window holding a close that is NaN,
infinite, zero, negative or subnormal (such a close spoils two returns, so
it empties the `length + 1` = 21 windows it sits in -- measured at bar 200
of a 400-bar frame, with 0 earlier bars moved, and fewer near either end:
1 / 2 / 20 / 21 / 2 / 1 bars for a bad close at bar 0 / 1 / 19 / 200 / 398
/ 399); on any window holding a return whose square reaches
`max / (8 * length)`, i.e. |r| >= 1.06e+153; and on any window whose
`length` returns span 4096 ulps or less of the largest of them, which 21
identical closes are one way to reach.
⚠ That floor is RELATIVE and deliberately not the absolute `4096 eps` of
`statistics/ts_kurt_60.py` and `statistics/ts_binent_20.py`: what it
protects is a difference of two centre readings against the rounding in
those centres, and that rounding scales with the window's own magnitude.
On a quiet-but-honest frame -- returns of 1e-6 spread over 1e-13, where
the column agrees with the exact oracle to 1.3e-09 -- the relative floor
reports on all 580 body bars and an absolute one reports on none; on the
mirror case, returns of 0.5 spread over 1e-14, both refuse. It costs 0
body bars on each of nine clean frames and empties a 1%-a-bar geometric
ladder entirely, where the unguarded spelling reports 280 windows of pure
rounding spanning [-0.3300, +0.3033].
⚠ The floor is scale-invariant but NOT shift-invariant: a frame whose
returns span only the closes' own rounding (4.4e-16) fires on 576 of 600
bars at returns of 1e-6, where the floor is 9.1e-19, and on NONE after a
0.004 drift, where it is 3.6e-15.

**And it stays LOCAL, which the prototype does not.** Every window is
reduced from its own `length` values by `sliding_window_view` and a skip
list, so nothing is accumulated across windows. Measured on a 2,000-bar
frame priced at 1e-198 with one return planted at bar 200: the 20 windows
holding it all fire, with a MEDIAN of 0.223491 at x1e+02 and 0.223607 at
x1e+06, x1e+08 and x1e+100 -- the closed form above, one odd return among
nineteen -- and they are 20 different windows rather than 20 copies, so
what collapses with the spike is their spread (2.96e-04, 2.96e-08,
2.96e-10, 1.39e-16). At x1e+154 and x1e+300, both above the per-return
bound, the module empties those 20 windows. In ALL SIX cases every one of
the 1,780 bars
from 220 on agrees with the unspiked frame to **3.4e-14** (not
bit-identically: a spike rescales every later close by a non-power-of-two
factor). Through the prototype's ONLINE `rolling.mean()`/`rolling.std()`
the same later bars move by 5.97e-10, 1.33e-02, **0.403** and 0.418 at
x1e+02, x1e+06, x1e+08 and x1e+100 -- a third of this column's whole
range, on bars whose windows no longer hold the spike.

Cost: three O(n * length) reductions over a `sliding_window_view` (the
sum and the two extrema), `length` contiguous deviations, and one pandas
rolling median, with no allocation that grows with `length` -- the traced
peak is 42.0 MB on 400,000 bars at each of `length` 3, 20, 60 and 250, and
the call takes roughly 104 / 195 / 266 / 536 ms there. The
window-by-window oracle this was checked against takes about 0.8 s on
20,000 bars, which is why it lives in docs/measure_ts_medskew_20.py and
not here. ⚠ Every wall-clock figure in this paragraph is this machine's
and moves between runs -- the same oracle timed 0.81 s and 0.73 s in two
runs of the same script. The PEAKS are the claim.

Calculation:
    Default Inputs:
        length=20
    r[t]            = close[t] / close[t-1] - 1
    TS_MEDSKEW[T]   = (mean(r) - median(r)) / sd(r) over the trailing
                      `length` returns, sd with ddof=1, NaN where those
                      returns span 4096 ulps or less of their own largest
                      magnitude

Args:
    close (pd.Series): Series of 'close's
    length (int): Returns per window. At least 3 -- a window of two
        returns has its mean equal to its median, so the column is
        identically 0 there -- so a smaller or missing value falls back to
        the default. At 3 the bound is sqrt(2/3) = 0.8165. Default: 20
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)

Returns:
    pd.Series: TS_MEDSKEW_{length}, dimensionless, inside
        [-0.974679, +0.974679] at length 20
"""
