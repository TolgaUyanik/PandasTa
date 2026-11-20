# -*- coding: utf-8 -*-
import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from pandas import Series

from pandas_ta.utils import get_offset, verify_series

#: The feature's own sampling lag: the window is DECIMATED by 2 before
#: anything else happens, so a window of 100 returns is analysed as 50
#: points. It is the 6th argument of the hctsa operation this feature names
#: (`SC_FluctAnal(y, 2, 'dfa', 50, 1, 2, 1)`), and it is the ONLY parameter
#: that separates the DFA member of catch22's pair from the rescaled-range
#: one, which passes no lag at all.
LAG = 2
#: Log-spaced scale steps requested before duplicates are dropped -- the
#: `tauStep` of that same operation, under `logInc = 1`.
N_TAU_STEPS = 50
#: Shortest scale analysed, in decimated points.
TAU_MIN = 5
#: Order of the polynomial removed from each box. 1 is what makes this DFA
#: rather than a higher-order DFA. ⚠ The kernel below SPELLS the order-1 fit
#: out (one slope, one intercept) instead of reading this constant, because a
#: general-order fit would be a different and slower piece of code for a
#: parameter the feature fixes; the constant is here so the parameter is
#: named, and `docs/measure_c22_dfa.py` and `tests/test_c22_dfa.py` take it
#: as a knob and price order 2 at 259 of 366 moved windows.
POLY_ORDER = 1
#: The moment the fluctuation is taken at (`q`). 2 is the root-mean-square,
#: which is what DFA means, and the kernel spells it out the same way -- the
#: mean of the SQUARED residuals. `q = 1` is priced at 95 of 366 moved
#: windows.
Q = 2
#: FLOOR on the scales either piece of the two-piece fit may be given, and
#: the one that binds at the default `length`.
#: ⚠ **8 is MEASURED, not quoted.** The definition says the fit needs enough
#: scales on each side to mean anything; it does not say how many, and no
#: copy of the operation's own source is in this worktree. What pins it is
#: the reference implementation's own output: it returns exactly the six
#: values 8/21 .. 13/21 over 8,400 windows at the default `length`, and
#: widening the search to 7 .. 15 or 6 .. 15, which is what a floor of 7 or 6
#: gives, agrees with it on 150 and 143 of 294 windows against this range's
#: 294 of 294 (`docs/measure_c22_dfa.py` section Q3).
MIN_POINTS = 8
#: ... and the SHARE of the ladder each piece must have once the ladder is
#: long enough for a quarter of it to exceed `MIN_POINTS`, which happens at
#: `scales` 34 (`length` 175). Also measured, over every ladder size the
#: feature can produce: `max(MIN_POINTS, round(scales / SCALE_SHARE))`
#: reproduces the reference's search range on all 32 of them, where a flat
#: floor of 8 fits the 18 shortest and the three neighbouring roundings miss
#: 4, 8 and 8 (section Q6b) -- and, tested by PREDICTION window by window
#: rather than by fit, it is 3,084 of 3,084 against their 3,012, 2,945 and
#: 2,945 (section Q7).
SCALE_SHARE = 4
#: Divisor convention of the z-score catch22 applies before every feature. 1
#: is MATLAB `zscore`'s default, and hctsa is MATLAB; 0 is the population one.
#: The knob is INERT here, and not by luck: the whole feature is invariant
#: under `a * r + b` for any `a != 0` (see this module's __doc__), so the
#: z-score cannot move an output -- measured at 0 of 366 windows, at either
#: `ddof` and with no z-score at all. It is spelled out because it is what
#: the definition does.
ZSCORE_DDOF = 1
#: A window of returns whose standard deviation is at most NOISE_ULPS machine
#: epsilons does not vary: what is left is the rounding of `c / c1 - 1`, and
#: this column reads the SHAPE of the fluctuation curve rather than its size,
#: so it would read the shape of that rounding at full strength. NaN instead.
#: The floor is an ABSOLUTE constant because what it bounds is a
#: dimensionless RETURN, which has no rolling scale of its own to keep
#: causal; 4096 eps is this fork's existing habit on such a quantity
#: (`statistics/c22_ami2.py`, `statistics/c22_ami_timescale.py`,
#: `statistics/c22_periodicity.py`, `statistics/tf_autocorr_1e_60.py`).
NOISE_ULPS = 4096
NOISE_FLOOR = NOISE_ULPS * np.finfo(float).eps  # 9.09e-13
#: Doubles of window to evaluate at once. Each chunk allocates a
#: `(rows, length)` z-scored slab, a `(rows, length // LAG)` profile and one
#: `(rows, boxes, tau)` view per scale, so this budget is what keeps the peak
#: off the product `len(close) * length`.
CHUNK_VALUES = 1 << 19


def scales(length):
    """The scales the fluctuation is measured over, in DECIMATED points.

    `N_TAU_STEPS` points spaced evenly in the LOG, from `TAU_MIN` to half the
    decimated window, rounded to integers with the duplicates dropped. It is
    a function of `length` alone -- no data enters it -- so the whole scale
    ladder of a given `length` is a constant: at the default 100 it is the 21
    integers 5 .. 25.
    """
    points = -(-int(length) // LAG)
    top = points // 2
    if top < TAU_MIN:
        return np.empty(0, dtype=np.int64)
    steps = np.exp(np.linspace(np.log(float(TAU_MIN)), np.log(float(top)),
                               N_TAU_STEPS))
    # `floor(x + 0.5)` and not `np.round`: MATLAB's and C's `round` take a
    # half away from zero, numpy's takes it to the nearest EVEN integer.
    # Whether any step of the default ladder lands near a half is measured
    # (`docs/measure_c22_dfa.py` section A3), not assumed.
    return np.unique(np.floor(steps + 0.5).astype(np.int64))


def min_each_side(ntt):
    """Fewest scales the break search leaves on each side of a `ntt`-scale
    ladder: a quarter of the ladder, never below `MIN_POINTS`.

    So the break runs over `min_each_side(ntt) .. ntt - min_each_side(ntt)`,
    which is 8 .. 13 of the 21 scales at the default `length`. The rounding
    is `floor(x + 0.5)`, the same half-away-from-zero one `scales()` uses,
    and it is load-bearing: a ladder of 34 scales wants 9 and `ceil` would
    give 9 as well, while a ladder of 33 wants 8 and `ceil` gives 9
    (`docs/measure_c22_dfa.py` section Q6).
    """
    # `int(x + 0.5)` is `floor(x + 0.5)` here: `ntt` is positive, so `int`
    # truncates downwards.
    return max(MIN_POINTS, int(int(ntt) / SCALE_SHARE + 0.5))


def _first_length_with_a_choice():
    """The shortest `length` whose ladder gives the break search more than one
    candidate. Walked rather than written down, so it cannot drift from
    `scales()`, from `MIN_POINTS` or from `min_each_side()`."""
    for length in range(LAG, 4096):
        ntt = int(scales(length).size)
        if ntt and ntt - 2 * min_each_side(ntt) + 1 >= 2:
            return length
    raise RuntimeError("no length under 4096 gives the break search a choice")


#: Fewest returns a window may hold. At `MIN_LENGTH` the ladder holds 17
#: scales, so the break search chooses between TWO candidates and the column
#: takes two values -- a floor, emphatically not a recommendation;
#: `prop_bounds()` says how coarse it is. A smaller or missing `length` falls
#: back to the default. ⚠ The reference implementation has no such floor and,
#: fed a window whose ladder leaves its search no candidate at all, returns
#: 1.0 -- a number outside the range the quantity can otherwise take
#: (measured at `length` 67, section Q4). This port blanks that regime by
#: construction instead.
MIN_LENGTH = _first_length_with_a_choice()


def prop_bounds(length):
    """The interval the column cannot leave at window `length`, derived.

    The output is `break / scales`, where `break` is the number of scales in
    the first piece of the two-piece fit and the search leaves at least
    `min_each_side(scales)` of them on each side. So it is one of the
    `scales - 2 min_each_side + 1` ratios

        min_each_side / scales  ..  (scales - min_each_side) / scales

    which is [0.3810, 0.6190] over 6 values at the default `length` of 100,
    and the two values 8/17 and 9/17 at `MIN_LENGTH`.
    """
    ntt = int(scales(length).size)
    if not ntt:
        return (float("nan"), float("nan"))
    a = min_each_side(ntt)
    if ntt - 2 * a + 1 < 1:
        return (float("nan"), float("nan"))
    return (a / ntt, (ntt - a) / ntt)


def _residual_ss(x, y):
    """Sum of SQUARED residuals of the least-squares line through `(x, y)`,
    per row of `y`.

    `x` is one scale axis shared by every row, `y` a `(rows, points)` block.
    The residuals are formed EXPLICITLY -- centre, slope, subtract -- rather
    than as `Syy - Sxy**2 / Sxx`, which is the same algebra and cancels
    catastrophically where the fit is nearly exact, exactly the regime a
    fluctuation curve sits in.
    """
    xc = x - x.mean()
    sxx = float((xc * xc).sum())
    yc = y - y.mean(axis=1, keepdims=True)
    slope = (yc * xc).sum(axis=1) / sxx
    resid = yc - slope[:, None] * xc
    return (resid * resid).sum(axis=1)


def _prop_rows(block):
    """The DFA fluctuation scaling break of each row of `block`.

    `block` is a `(rows, length)` slab of one-bar SIMPLE RETURNS, oldest
    first. Each row is z-scored (inert, see `ZSCORE_DDOF`), decimated by
    `LAG`, cumulatively summed into a profile, and the root-mean-square
    linearly-detrended fluctuation `F(tau)` is taken over every scale of
    `scales(length)`. The break is the two-piece straight-line fit of
    `log F` on `log tau` that minimises the sum of the two sums of SQUARED
    residuals -- not of the two residual NORMS, which is a different column
    and the reading this port first got wrong (section Q3: 294 of 294
    against 202 of 294) -- and the row's value is the SHARE of scales in the
    first piece.

    Comes back as NaN for a row holding a non-finite return, for a row whose
    standard deviation is at most `NOISE_FLOOR` or is not finite, and for a
    row whose fluctuation is exactly zero (or not finite) at any one scale --
    a profile that is exactly straight inside every box of that size, which
    has no `log F` to fit.
    """
    rows, n = block.shape
    taus = scales(n)
    ntt = taus.size

    # `~isfinite` carries the rows holding a bad return; without it one NaN
    # would spread across the row's mean, sd and every scale.
    bad = ~np.isfinite(block).all(axis=1)
    with np.errstate(invalid="ignore", over="ignore", divide="ignore"):
        sd = block.std(axis=1, ddof=ZSCORE_DDOF)
        # `~(sd > NOISE_FLOOR)` is True for 0.0 and for NaN. The `isfinite`
        # limb catches the row whose sum of squares OVERFLOWS although its
        # returns are finite -- `sd` is then +inf, which CLEARS the floor,
        # and every z is 0. ⚠ On its own that limb is REDUNDANT, measured
        # rather than assumed: such a row z-scores to all zeros, so its
        # profile is flat, so the zero-fluctuation guard below blanks it
        # anyway (section H2 -- 0 of the 100 bars a close pair of ratio
        # 1e200 blanks fire without this limb, and all 100 read 0.380952
        # with BOTH value guards removed). It is kept because it says what
        # it means at the place the overflow happens.
        bad |= ~(sd > NOISE_FLOOR) | ~np.isfinite(sd)
        z = (block - block.mean(axis=1, keepdims=True)) / sd[:, None]

        # The lag: the window is DECIMATED, keeping its first point and every
        # LAG-th after it, which is `y(1:lag:end)` of the operation this
        # feature names. At the default that drops the 50 returns of odd
        # offset INCLUDING THE MOST RECENT ONE -- see this module's __doc__,
        # where the consequence is measured rather than mentioned.
        y = z[:, ::LAG]
        # The profile. DFA fluctuates the CUMULATIVE SUM of the series, and
        # the decimation happens first: `cumsum(y[::LAG])` and not
        # `cumsum(y)[::LAG]`, which is a different quantity (section A5).
        profile = np.cumsum(y, axis=1)
        points = profile.shape[1]

        f2 = np.empty((rows, ntt), dtype=float)
        for j in range(ntt):
            tau = int(taus[j])
            boxes = points // tau
            # The last `points % tau` of the profile are dropped, which is
            # the forward-only pass the definition spells (`reshape` of the
            # first `boxes * tau` points).
            blk = profile[:, :boxes * tau].reshape(rows, boxes, tau)
            # A centred regressor, so the slope is one division and the
            # intercept is the box mean.
            t = np.arange(tau, dtype=float) - (tau - 1) / 2.0
            slope = (blk * t).sum(axis=2, keepdims=True) / float((t * t).sum())
            resid = blk - blk.mean(axis=2, keepdims=True) - slope * t
            # `q = 2`: the mean of the SQUARED residuals pooled over every
            # box of this scale. Pooling and averaging the per-box mean
            # squares are the same number here, because every box of a scale
            # holds the same `tau` points.
            f2[:, j] = (resid * resid).sum(axis=2).sum(axis=1) / float(
                boxes * tau)

        # `F(tau) == 0` has no logarithm. It needs the profile to be exactly
        # straight inside EVERY box of one scale, and it is REACHED on data
        # that is not flat: on a frame whose returns are exactly 0 and then
        # exactly +1%, bar 754 has `F = 0` at 17 of its 21 scales, and
        # without this guard it reads 0.380952 instead of blanking (section
        # G3c). It also blanks the overflowing window of section H2.
        bad |= ~(f2 > 0.0).all(axis=1) | ~np.isfinite(f2).all(axis=1)
        # `0.5 log(F^2)` rather than `log(sqrt(F^2))`: one rounding instead
        # of two. The substituted 1.0 never reaches an output -- its row is
        # already `bad` -- it is there so the logarithm cannot warn.
        log_f = 0.5 * np.log(np.where(f2 > 0.0, f2, 1.0))

    log_tau = np.log(taus.astype(float))
    # The break search. Candidate `i` splits the ladder into the first `i`
    # scales and the last `ntt - i + 1` -- the two pieces SHARE the scale at
    # the break -- and is scored by the sum of the two sums of SQUARED
    # residuals. Both readings are load-bearing and both are pinned by the
    # reference's own output rather than by taste: scoring the two residual
    # NORMS instead disagrees with it on 92 of 294 windows and splitting the
    # ladder DISJOINTLY on 123 of 294 (`docs/measure_c22_dfa.py` section Q3).
    # `i` runs over the splits that leave `min_each_side(ntt)` scales on each
    # side.
    first = min_each_side(ntt)
    last = ntt - first
    sserr = np.empty((rows, last - first + 1), dtype=float)
    for c, i in enumerate(range(first, last + 1)):
        sserr[:, c] = (_residual_ss(log_tau[:i], log_f[:, :i])
                       + _residual_ss(log_tau[i - 1:], log_f[:, i - 1:]))
    # `argmin` takes the FIRST minimum, which is the tie rule of the
    # definition's own `min`.
    break_at = np.argmin(sserr, axis=1) + first
    return np.where(~bad, break_at / float(ntt), np.nan)


def c22_dfa(close, length=None, offset=None, **kwargs):
    """Indicator: catch22 DFA fluctuation scaling break (C22DFA)"""
    # Validate Arguments
    length = int(length) if length and int(length) >= MIN_LENGTH else 100
    close = verify_series(close, length + 1)
    offset = get_offset(offset)

    if close is None: return

    # Calculate Result
    c = close.to_numpy(dtype=float)
    # A close that is not a finite, normal, positive float (NaN, inf, zero,
    # negative, or subnormal such as 1e-310) is bad data: it has no return to
    # take, so it is missing.
    c = np.where(np.isfinite(c) & (c >= np.finfo(float).tiny), c, np.nan)

    # The one-bar simple return, spelled as a price RATIO minus one: `8a / 8b`
    # is the same double as `a / b`, so a x2**k rescale of the price cancels
    # EXACTLY here and nothing downstream can see it. Both ends are finite,
    # positive and normal by now, so the ratio can still overflow or underflow
    # to zero -- 1e-300 followed by 1e50, say -- and such a pair is bad data
    # in the same way a NaN close is.
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        r = c[1:] / c[:-1] - 1.0
    r = np.where(np.isfinite(r), r, np.nan)

    n = c.size
    out = np.full(n, np.nan)
    if n >= length + 1:
        # The window ending at bar T holds the `length` returns of bars
        # T - length + 1 .. T, which read closes T - length .. T: bar
        # `length` is the first that fires.
        win = sliding_window_view(r, length)
        rows = win.shape[0]
        step = max(1, CHUNK_VALUES // length)
        for a in range(0, rows, step):
            b = min(a + step, rows)
            out[length + a:length + b] = _prop_rows(win[a:b])

    result = Series(out, index=close.index)

    # Offset
    if offset != 0:
        result = result.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        result.fillna(kwargs["fillna"], inplace=True)

    # Name and Categorize it
    result.name = f"C22DFA_{length}"
    result.category = "statistics"

    return result


c22_dfa.__doc__ = \
"""catch22 DFA fluctuation scaling break (C22DFA)

WHERE the detrended fluctuation of the last `length` returns stops
following one power law and starts following another: measure
`F(tau)`, the root-mean-square linearly-detrended fluctuation of the
return profile, over 21 box sizes; fit TWO straight lines to
`log F` against `log tau`; and report the SHARE of the box sizes
that fall in the first of the two pieces.

    C22DFA = (box sizes in the first piece) / (box sizes)

**It is a RATIO OF SMALL INTEGERS, and that is the first thing to
know about it.** At the default `length` it takes six values and
nothing between them -- 8/21, 9/21, 10/21, 11/21, 12/21, 13/21, so
0.380952 to 0.619048 -- because the break is one of six candidate
positions on a 21-rung ladder. `prop_bounds(length)` derives the set
for any `length`. Neighbouring bars carry the SAME value on 20.3% to
35.3% of pairs on five stochastic 1,500-bar frames, and on 100% of
the 20-bar cosine one, which reads 0.380952 on all 1,400 of its
fired bars. A consumer that wants a continuous DFA statistic wants
`tf_dfa_100` (the exponent itself, issue #112), not this.

⚠ **The value at bar T does not read close[T].** The lag decimates
the window keeping every SECOND return starting from the OLDEST, so
the return of bar T itself -- the one that needs close[T] -- is
dropped: the VALUE at bar T is a function of closes T-100 .. T-1.
That is the feature's own parameter and not a defect, and it is
measured rather than reasoned: perturbing close[T] by a finite
factor moves bar T on 0 of 4 sampled bars and bar T+1 on 3 of them
(`docs/measure_c22_dfa.py` section B7), and perturbing EVERY close of
a frame one at a time moves bar T only from closes in
`[T-100, T-1]`, never from a close at or after T (section B6). So the
column is causal AND one bar stale, and a companion that expects
today's return in it will be wrong.
⚠ The NaN **MASK** is the exception, and it is still causal: the
finiteness check and the noise floor run on the WHOLE undecimated
window, which does include the return of bar T, so a close at T that
is NaN or zero blanks bar T -- 4 of 4 sampled bars, where the finite
perturbation moves 0 of 4 (section B7b). That is why a single bad
close blanks 101 bars starting AT its own bar and not 100 starting
after it. A consumer recomputing this column on data truncated at
T-1 gets the same values and a different mask.

⚠ **Its "no break" reading is not the middle of the range.** On 400
INDEPENDENT windows of normal returns the median is 0.571429 and the
single commonest value is the TOP candidate 0.619048 (147 of 400) --
the fluctuation curve of iid returns is close to one straight line,
and a two-piece fit of a straight line puts its break wherever the
residuals happen to be smallest, which is biased towards the end of
the ladder. The same measurement reads a median of 0.529412 at
`length` 83 and 0.605263 at 250 (section C4). Read it against its
own measured centre, never against 0.5.

**This port IS the column the 2026-10-24 screen measured.** Over
EVERY window of six frames -- 8,400 of them -- it is BIT-EQUAL to
the GPL-3.0 reference implementation, on all six frames, with 0
disagreements (section P1). Fed windows of other lengths, which give
it ladders of 16 to 47 rungs, the same reading predicts the
reference on 3,084 of 3,084 windows across all 32 ladder sizes
(section Q7). So the screen's Gate E figure (max |rho| 0.0707 vs
`mad_pct_Pctl`, SHIP) is an expectation that transfers -- though it
is still a figure measured on the prototype, and Gate E is re-run on
this port.

**THE THREE READINGS THAT DECIDE THE COLUMN, AND HOW THEY WERE
PINNED.** The definition names a two-piece fit of a fluctuation
curve; it does not say how a split is scored, whether the two pieces
share the scale at the break, or how many scales each piece needs.
A grid of 2,304 candidate pipelines was fitted to the reference as a
BLACK BOX (section Q), then 560 more with the fluctuation's divisor
open (Q2) and 168 more with the even re-sampling and the search range
open (Q3), and exactly one survives:
* **the sum of SQUARED residuals**, not of the two residual norms.
  Scoring norms moves 100 of 366 sampled windows and agrees with the
  reference on 202 of 294 (sections A5, Q3).
* **the two pieces SHARE the scale at the break** -- the first piece
  is scales `1 .. i`, the second `i .. 21`. Splitting them disjointly
  moves 167 of 366 windows and agrees on 171 of 294.
* **each piece gets at least `max(8, round(scales / 4))` scales.**
  The reference returns exactly six values at the default `length`
  and the range is symmetric at every ladder size, so one number
  describes it; `max(8, round(ntt/4))` reproduces it on 32 of 32
  ladder sizes where a flat floor of 8 fits 18 of 32 and the three
  neighbouring roundings 28, 24 and 24 (section Q6b), and it
  predicts the reference window by window on 3,084 of 3,084
  (section Q7).
Three more readings are fixed the same way and are not close calls:
the lag DECIMATES the window keeping its first point (the
end-aligned reading agrees on 611 of 1,680 windows, no decimation at
all on 21), the cumulative sum is taken AFTER the decimation (802 of
1,680), and the ladder's top comes from the DECIMATED length (34 of
1,680). ⚠ The ladder size is itself the evidence that the lag is
real: the reference's values are 21sts over a 100-return window, and
a 21-rung ladder needs a top scale of 25, which needs a series of 50
or 51 points -- not 100.

**What is INERT here, measured rather than assumed.** The whole
feature is invariant under `a * r + b` for any `a != 0`: a constant
`b` in the returns is a straight LINE in the profile and every box's
own detrend removes it, and `a` scales every residual of every box
alike, which shifts `log F` by a constant and leaves the residuals
of both straight-line fits untouched. So, over 200 windows of the
walk frame, 0 move under the returns x0.5, x2, x10 or x-1, and 0
under +0.001 or +1.0 on every return (section D4) -- and the
z-score, which is one such map, moves 0 of 366 windows at either
`ddof` (section A5). What it is NOT blind to is the ORDER of the
returns: a reversal moves 155 of 200 windows and a shuffle 144.

Source: catch22 (Lubba, Sethi, Knaute, Schultz, Fulcher, Jones 2019,
*Data Mining and Knowledge Discovery* 33:1821, "catch22: CAnonical
Time-series CHaracteristics"), feature `dfa` /
`SC_FluctAnal_2_dfa_50_1_2_logi_prop_r1` -- the hctsa operation
`SC_FluctAnal(y, 2, 'dfa', 50, 1, 2, 1)`, whose `prop_r1` output is
the share of scales in the first scaling regime -- applied by
PandasTa issue #128 to the last 100 daily simple returns. The
paper's own description of the feature is "proportion of slower
timescale fluctuations that scale with DFA (50% sampling)", and the
50% sampling is the lag of 2.
The reference implementation (pycatch22 1.0.2) is **GPL-3.0** and
this fork is MIT: this module was written from the DEFINITION, no
shipped module imports the reference (a test asserts that over the
whole package), and the one place it is run at all is
`docs/measure_c22_dfa.py` sections P and Q -- opt-in, measurement
only, the same use the owner's own screen prototype makes of it. ⚠
hctsa's own source is not in this tree and was not read: what those
sections know about it is what the reference's OUTPUT shows, and the
readings above are identified by fitting candidates to that output.

⚠ catch22 is a subset selected for TIME-SERIES CLASSIFICATION
performance on 93 reference problems. That is not return
prediction, and nothing here tests it on BIST: its presence in this
fork is existence, not evidence.

Gate A also checks the quantity three ways that share no code with
this module:
* the definition re-spelled in plain Python with `math.fsum` and no
  numpy vectorisation: bit-equal on 1,200 windows of six frames,
  max gap 0.0 (section A4);
* an EXACT oracle. The profile, every per-box least-squares residual
  and `F(tau)**2` are `Fraction`s -- no rounding at all -- and only
  the logarithms and the two straight-line fits are inexact, in
  60-digit `Decimal`. It agrees on the break on 90 of 90 sampled
  windows, and it reports the MARGIN: the runner-up split's score
  exceeds the winner's by at least 3.598e-04 relative (median 2.8%
  to 17.6% per frame), which is the slack a reassociated numpy
  reduction would have to close to move an output (section A6);
* the ladder, which is a function of `length` alone, spelled twice:
  21 scales 5 .. 25 at the default, and no step of it lands closer
  than 0.0026 to a rounding half, so `floor(x + 0.5)` and numpy's
  round-half-to-even give the same ladder (section A3).

Calculation:
    Default Inputs:
        length=100, LAG=2, N_TAU_STEPS=50, TAU_MIN=5, Q=2,
        POLY_ORDER=1, MIN_POINTS=8, SCALE_SHARE=4
    r[t]  = close[t] / close[t-1] - 1
    X     = r[T-length+1 .. T]                  (the window)
    Z     = (X - mean(X)) / sd(X, ddof=1)       (inert, see above)
    Y     = Z[0], Z[2], Z[4], ...               (the lag: 50 points)
    P     = CUMSUM(Y)                           (the profile)
    tau   = round(exp(linspace(log 5, log 25, 50))), deduplicated
            = 5, 6, ..., 25                     (21 scales)
    for each tau:
        k      = 50 // tau                      boxes, the tail dropped
        F(tau) = sqrt(mean over all k * tau residuals of
                      (P - the box's own OLS line)^2)
    for each split i in 8 .. 13:
        e(i) = SS(log F[1..i]   on log tau[1..i])
             + SS(log F[i..21]  on log tau[i..21])
    C22DFA = argmin(e) / 21
    NaN while the window is incomplete; when it holds a non-finite
    return; when the return standard deviation is at most 9.09e-13
    or is not finite; and when F(tau) is 0 at ANY scale, which is
    reachable on data that is not flat (see below)

**TWO blanking rules beyond the bad-data one.**
* the window is NaN unless its return standard deviation clears
  9.09e-13 (4096 eps). It is inert on anything with noise in it --
  0 of 1,400 bars differ from the unguarded spelling on each of six
  price-shaped frames -- and what it buys is that this column reads
  the SHAPE of a fluctuation curve, so rounding noise would be read
  at full strength: an exactly geometric price path (constant
  returns, sd 1.2e-16) fires on all 1,400 bars unguarded, reading
  five of the six values, and a price flat at 1e6 except for ONE
  1-ulp step fires on the 100 bars whose window holds the step,
  reading five of the six (section G2);
* the window is NaN if `F(tau)` is exactly 0 at any scale, which has
  no logarithm. ⚠ This is REACHED on data with real variation, not
  only on a flat window: on a frame whose returns are exactly 0 and
  then exactly +1%, bar 754 has `F = 0` at 17 of its 21 scales and
  unguarded reads 0.380952 (section G3c). It also blanks the window
  whose sum of squares overflows, which is why the `isfinite(sd)`
  limb above is redundant -- measured, section H2.
⚠ **It does NOT empty a deterministically smooth path**: a price
rising by exactly one kurus a bar has a return standard deviation of
3.8e-06, four million times the floor, so it fires on all 1,400 bars
-- reading 0.380952, constant. A companion must not assume the four
catch22 ports blank together.

Causal: the VALUE at bar T reads closes T - length .. T - 1 and its
NaN mask also reads close[T] (see the staleness note above); nothing
reads a close after T. Measured by future-perturbation sweep -- 0 of 35
offsets leak on each of six frames with eight splices apiece, 0 of
35 at `length` 83, 120 and 250, and 0 of 35 under a VIOLENT splice
(20% daily volatility and a 3x jump at the cut) on all six frames --
by the one-close-at-a-time dependency map above, and by fifteen
mutants read off this file, edited and exec'd in memory.
⚠ **Four mutants that look like look-aheads are not**, and the
reason is the lag: a window shifted one bar forward still ends on
the return the decimation THROWS AWAY. Its kept set ends on the
return of bar T instead of bar T-1, so it reads close[T] -- causal,
merely no longer stale. Back-dating the write, shifting the window
one bar ahead, rolling the returns, and decimating from the newest
end each move 1,098 to 1,099 of the 1,400 fired bars of the walk
frame -- so the edit lands -- and each leaks on 0 of 35 offsets,
because each is still causal. The mutant that IS a one-bar
look-ahead shifts the window TWO bars, so its kept set ends on the
return of bar T+1: the gentle sweep catches it on 5 of 35 offsets,
7 with 32 splices, and the violent one on 28 of 35. A ten-bar shift
is caught 35 of 35 by both.
⚠ **Four more are DEAD, each for a measured reason.** Centring or
scaling each row by the whole CHUNK's mean or standard deviation,
and cumulatively summing the profile ACROSS rows, are all the affine
invariance above: bit-equal on 1,500 bars. Dropping the
`isfinite(sd)` limb is bit-equal because the zero-fluctuation guard
blanks the same rows.
Scale-free: bit-identical under x8, x64, 2**-40 and 2**40 on all six
frames, and at `length` 83 / 120 / 250 -- BY CONSTRUCTION, since the
price enters only as `c[t] / c[t-1]`, and `8a / 8b` is the double
`a / b`. x10, x3.7, x0.1 and x1.0000001 are bit-identical too, and
at price levels 1e-6, 1e+6 and 1e+100, and here that is not luck:
the output is an INTEGER choice whose runner-up is at least
3.598e-04 away in relative score, so a perturbation that does not
close that gap cannot move it at all.
NaN on the first `length` bars; on every window holding a close that
is NaN, infinite, zero, negative or subnormal (101 bars at the
default); on a window holding a close PAIR whose ratio overflows to
an infinite return (100 bars); and under the two blanking rules
above.

Cost: the windows are walked in chunks, so the peak is set by
`CHUNK_VALUES` and not by `len(close) * length`: at n = 400,000 the
traced peak is 23.4 MB (tracemalloc) and the run takes about 6.8 s.
Budgets of 100, 400, 999 and 10**9 are bit-equal to the default, so
the chunk boundary is invisible. Wall clock is not quoted as a band
because it does not reproduce.

Every figure in this docstring that comes from sections A, B, C, D,
E, G, H or Z of `docs/measure_c22_dfa.py` reproduces with `AVX512F`,
`AVX512_SKX`, `AVX2` and `FMA3` disabled, which is what CI runs on:
those eight were re-run under that dispatch and ONE digit in the
whole receipt moves -- the geometric ladder's return standard
deviation, 1.175e-16 against 1.119e-16, which is quoted above only
as 1.2e-16 because it is rounding noise either way. That is the
integer-choice structure again. ⚠ The exclusions are deliberate and
they are exactly two: the wall clock and traced peak in the
paragraph above come from section T and do not reproduce on EITHER
dispatch, and the counts against the REFERENCE (8,400 of 8,400,
3,084 of 3,084, and the 294 and 1,680 tallies) come from the
GPL-3.0 sections P and Q, which were not re-run under it. The
366-window tallies are NOT among them: they are section A5, this
module against its own plain-Python spelling with no reference in
the loop, and they are in the eight that were re-run. See
`docs/C22DfaMeasured.md` section F1.

Args:
    close (pd.Series): Series of 'close's
    length (int): RETURNS per window, so `length + 1` closes. At
        least 83 -- the shortest window whose ladder gives the break
        search more than one candidate -- and a smaller or missing
        value falls back to the default.
        ⚠ **The set of values it can take is a function of it**, and
        so is the centre: `prop_bounds` is [0.4706, 0.5294] over 2
        values at 83, [0.3810, 0.6190] over 6 at the default,
        [0.3077, 0.6923] over 11 at 120 and [0.2632, 0.7368] over 19
        at 250, and the iid median moves 0.5294 / 0.5714 / 0.6053
        over 83 / 100 / 250 (section C4). A companion that passes a
        non-default `length` must re-derive its own centre.
        ⚠ There is no ceiling, but the EVIDENCE has one: the
        search-range rule is checked against the reference over
        ladders of 16 to 47 scales, which is `length` 79 to 1,187
        (sections Q6, Q7). Above that
        `max(MIN_POINTS, round(scales / SCALE_SHARE))` is an
        extrapolation.
        Default: 100
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)

Returns:
    pd.Series: C22DFA_{length}, dimensionless, one of the
        `scales - 2 * min_each_side + 1` ratios in
        `prop_bounds(length)` = [0.380952, 0.619048] at the default
"""
