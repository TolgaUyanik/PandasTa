# -*- coding: utf-8 -*-
import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from pandas import Series

from pandas_ta.utils import get_offset, verify_series

#: The lag the automutual information is read at. The 2 is the catch22
#: operation's OWN parameter -- the `tau` of the feature catch22 1.0 calls
#: `CO_HistogramAMI_even_5bin_ami2`, which it renamed AND REDEFINED from
#: `CO_HistogramAMI_even_2_5` to match hctsa (see this module's __doc__) --
#: so it is a module constant and not a function of `length`.
TAU = 2
#: Bins per axis of the joint histogram, the `numBins` of that same name.
NUM_BINS = 5
#: How far past the window's own extremes the two OUTER bin edges reach. It is
#: the "increment buffer to ensure all points are included" of the definition,
#: and under this edge spelling it CANNOT change a value: the interior edges
#: are placed between the window's own min and max, every point lies in
#: `[min, max]` by construction, and the buffer moves only the two edges no
#: point can be outside of. It is kept because it is part of the definition and
#: because its absence would be the obvious "simplification" to make -- but it
#: is INERT, measured (`docs/measure_c22_ami2.py` section A7), not merely said
#: to be. ⚠ Pushing the buffer INTO the interior edges instead -- evenly
#: spaced over `[min - 0.1, max + 0.1]`, which is the other way to read the
#: same sentence -- is a different column: it moves 434 of 467 windows of the
#: walk frame and the reference implementation does not do it (section A5).
BUFFER = 0.1
#: Divisor convention of the z-score catch22 applies before every feature. 1
#: is MATLAB `zscore`'s default, and hctsa is MATLAB; 0 is the population one.
#: ⚠ hctsa's source was not read and the black-box fit cannot tell the two
#: apart (section P1b puts `ddof` 0 at 2,802 of 2,802 as well), which is moot
#: because the knob is INERT (section A6). Under this
#: edge spelling the whole z-score is INERT on any window whose `sd` is finite
#: and above `NOISE_FLOOR` -- the interior edges are an affine function of the
#: window's own min and max, so any positive affine map of the window leaves
#: every bin assignment alone -- and the reference agrees (it returns the same
#: value for a window and for its z-score, section P0). ⚠ The precondition is
#: not decoration: a window whose sum of squares OVERFLOWS has no z-score at
#: all (`sd` is +inf, every z is 0) and is blanked by the `isfinite(sd)` limb
#: below, which section H measures. The z-score is spelled out anyway because
#: it is what catch22 does, and because the inertness is a measured fact
#: rather than an obvious one (section A6).
ZSCORE_DDOF = 1
#: Fewest returns a window may hold: `NUM_BINS**2 + TAU`, so the window has at
#: least as many lagged PAIRS (25) as the joint histogram has cells (25). A
#: smaller or missing `length` falls back to the default.
#: ⚠ That is a FLOOR and not a recommendation, and it is the thinnest regime
#: a histogram estimator has: one pair per cell. Measured on 400 independent
#: normal windows through this kernel (section A10b), the column reads a
#: median of +0.228 at `length` 27 against +0.028 at 100 and +0.008 at 250,
#: because the first-order plug-in bias is `(NUM_BINS - 1)**2 / (2 pairs)` =
#: 0.32 nats there -- four times the default's. The guard band exists to stop
#: a caller computing something THINNER than that; it does not say 27 is a
#: good place to work.
MIN_LENGTH = NUM_BINS * NUM_BINS + TAU
#: A window of returns whose standard deviation is at most NOISE_ULPS machine
#: epsilons does not vary: what is left is the rounding of `c / c1 - 1`, and
#: this column reads the SHAPE of the window rather than its size, so it would
#: read the shape of that rounding at full strength. NaN instead. The floor is
#: an ABSOLUTE constant because what it bounds is a dimensionless RETURN, which
#: has no rolling scale of its own to keep causal; 4096 eps is this fork's
#: existing habit on such a quantity (`statistics/c22_ami_timescale.py`,
#: `statistics/c22_periodicity.py`, `statistics/tf_autocorr_1e_60.py`,
#: `statistics/ts_binent_20.py`).
NOISE_ULPS = 4096
NOISE_FLOOR = NOISE_ULPS * np.finfo(float).eps  # 9.09e-13
#: `log(NUM_BINS)`, the largest the UNCORRECTED plug-in mutual information can
#: be: it cannot exceed the entropy of either marginal, and a marginal over
#: `NUM_BINS` bins cannot exceed `log(NUM_BINS)`. The shipped column is the
#: bias-CORRECTED estimate, so its bounds are `ami_bounds()` below.
MAX_AMI = float(np.log(NUM_BINS))
#: Doubles of window to evaluate at once. Each chunk allocates a `(rows,
#: length)` z-scored slab and a `(rows, length)` integer bin slab, so this
#: budget is what keeps the peak off the product `len(close) * length`.
CHUNK_VALUES = 1 << 19


def ami_bounds(length):
    """The interval the column cannot leave at window `length`, derived.

    It is an ENCLOSURE: neither endpoint is claimed to be reachable, and
    neither was measured to be. The lower end would need a plug-in MI of
    exactly 0 on a fully occupied 5x5 table and the upper end a marginal
    entropy of exactly `log 5` on a 5-cell bijection, which 98 pairs cannot
    even split evenly. The measured span is in this module's __doc__.

    The plug-in mutual information is in `[0, log(NUM_BINS)]`. The
    Miller-Madow correction subtracts `(cells - rows - cols + 1) / (2 pairs)`
    over the OCCUPIED cells, rows and columns of the joint histogram, and that
    term is at most `(NUM_BINS - 1)**2 / (2 pairs)` (a full table) and at
    least `-(NUM_BINS - 1) / (2 pairs)` (a table whose occupied cells are a
    bijection, where the correction ADDS). So

        -(NUM_BINS - 1)**2 / (2 pairs)  <=  value  <=
            log(NUM_BINS) + (NUM_BINS - 1) / (2 pairs)

    which is [-0.0816, 1.6298] at the default `length` of 100.
    """
    pairs = int(length) - TAU
    return (-(NUM_BINS - 1) ** 2 / (2.0 * pairs),
            MAX_AMI + (NUM_BINS - 1) / (2.0 * pairs))


def _ami_rows(block):
    """The 5-bin histogram automutual information at lag 2, per row of `block`.

    `block` is a `(rows, length)` slab of one-bar SIMPLE RETURNS, oldest
    first. Each row is z-scored; the range between its own extremes is cut
    into `NUM_BINS` even bins (the two outer edges pushed out by `BUFFER`, so
    the extremes are inside); every point is assigned to the bin whose
    half-open interval holds it; and the MILLER-MADOW bias-corrected mutual
    information of the joint histogram of `(bin[t], bin[t + TAU])` is returned
    in NATS.

    Comes back as NaN for a row holding a non-finite return and for a row
    whose standard deviation is at most `NOISE_FLOOR` or is not finite -- a
    flat window has no z-score, and a window whose squares overflow has none
    either.
    """
    rows, n = block.shape
    pairs = n - TAU

    # `~isfinite` carries the rows holding a bad return; without it one NaN
    # would spread across the row's mean, sd and every bin edge.
    bad = ~np.isfinite(block).all(axis=1)
    with np.errstate(invalid="ignore", over="ignore", divide="ignore"):
        # catch22 z-scores the series before every feature. Under the edge
        # spelling below this is INERT (`ZSCORE_DDOF`), and it is written out
        # because it is what the definition does.
        sd = block.std(axis=1, ddof=ZSCORE_DDOF)
        z = (block - block.mean(axis=1, keepdims=True)) / sd[:, None]
        # `~(sd > NOISE_FLOOR)` is True for 0.0 and for NaN. The `isfinite`
        # limb is load-bearing on its own: a window of enormous (but finite)
        # returns overflows the sum of squares, `sd` is then +inf -- which
        # CLEARS the floor -- and every z is 0, so without it such a row would
        # read exactly 0.0, the value of a window with nothing in it, instead
        # of blanking.
        bad |= ~(sd > NOISE_FLOOR) | ~np.isfinite(sd)

        lo = z.min(axis=1)
        hi = z.max(axis=1)
        # The `NUM_BINS + 1` bin edges are evenly spaced from the window's own
        # minimum to its own maximum, with the first pushed down and the last
        # pushed up by BUFFER so that both extremes fall inside a bin. Only
        # the INTERIOR edges can decide anything (nothing lies outside
        # `[min, max]`), so only they are formed here: `lo + i * (hi - lo) /
        # NUM_BINS` for `i` in `1 .. NUM_BINS - 1`.
        width = (hi - lo) / NUM_BINS
        # The bin index is the number of interior edges the point stands at or
        # above, which is exactly the membership rule `b[i] <= y < b[i+1]`
        # over bins `0 .. NUM_BINS - 1`.
        idx = np.zeros(z.shape, dtype=np.int64)
        for i in range(1, NUM_BINS):
            idx += z >= (lo + i * width)[:, None]

    # The joint histogram of the two limbs, counted in one pass: each row gets
    # its own block of `NUM_BINS**2` codes.
    code = idx[:, :pairs] * NUM_BINS + idx[:, TAU:]
    code = code + (np.arange(rows) * (NUM_BINS * NUM_BINS))[:, None]
    counts = np.bincount(code.ravel(),
                         minlength=rows * NUM_BINS * NUM_BINS)
    counts = counts.reshape(rows, NUM_BINS, NUM_BINS)
    pij = counts / float(pairs)
    # Marginals: `pi` over the lagged-FROM limb (the row index), `pj` over the
    # lagged-TO one.
    pi = pij.sum(axis=2)
    pj = pij.sum(axis=1)

    with np.errstate(divide="ignore", invalid="ignore"):
        # `pij > 0` implies both of its marginals are positive, so every term
        # that survives the mask is finite; the empty cells are dropped rather
        # than evaluated to `0 * -inf`.
        term = pij * np.log(pij / (pi[:, :, None] * pj[:, None, :]))
    plug = np.where(pij > 0.0, term, 0.0).sum(axis=(1, 2))

    # THE MILLER-MADOW BIAS CORRECTION, and it is the estimator this feature
    # reports rather than a refinement of it. `MI = H(i) + H(j) - H(i, j)`,
    # and the Miller-Madow correction of a plug-in entropy over `m` OCCUPIED
    # bins is `+(m - 1) / (2 N)`; applying it to all three entropies leaves
    #
    #     MI_MM = MI - (cells - rows - cols + 1) / (2 pairs)
    #
    # over the occupied cells, rows and columns. Without it the column is
    # dominated by its own bias on a near-independent window -- the
    # first-order term is `(NUM_BINS - 1)**2 / (2 pairs)` = 0.0816 nats, which
    # is larger than the MEDIAN reading of four of the five stochastic frames
    # measured (walk 0.0428, tick-rounded 0.0270, penny 0.0262, student-t
    # 0.0234, section C1) though not of the AR(1) one (0.0883) -- and with
    # it the column can go slightly NEGATIVE, which an information cannot;
    # that is a property of a bias-corrected ESTIMATE and is disclosed in this
    # module's __doc__. The reference implementation computes this quantity:
    # 2,802 of 2,802 windows of six frames agree to 1e-12, where the
    # uncorrected plug-in agrees on 31 and the uncorrected plug-in over
    # interior-buffered bins on 15 (`docs/measure_c22_ami2.py` section P1c).
    occupied = (counts > 0).sum(axis=(1, 2))
    rows_used = (counts.sum(axis=2) > 0).sum(axis=1)
    cols_used = (counts.sum(axis=1) > 0).sum(axis=1)
    ami = plug - (occupied - rows_used - cols_used + 1) / (2.0 * pairs)

    return np.where(~bad, ami, np.nan)


def c22_ami2(close, length=None, offset=None, **kwargs):
    """Indicator: catch22 automutual information of returns at lag 2 (C22AMI2)"""
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
    # to zero -- 1e-300 followed by 1e50, say -- and such a pair is bad data in
    # the same way a NaN close is.
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        r = c[1:] / c[:-1] - 1.0
    r = np.where(np.isfinite(r), r, np.nan)

    n = c.size
    out = np.full(n, np.nan)
    if n >= length + 1:
        # The window ending at bar T holds the `length` returns of bars
        # T - length + 1 .. T, which read closes T - length .. T: bar `length`
        # is the first that fires.
        win = sliding_window_view(r, length)
        rows = win.shape[0]
        step = max(1, CHUNK_VALUES // length)
        for a in range(0, rows, step):
            b = min(a + step, rows)
            out[length + a:length + b] = _ami_rows(win[a:b])

    result = Series(out, index=close.index)

    # Offset
    if offset != 0:
        result = result.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        result.fillna(kwargs["fillna"], inplace=True)

    # Name and Categorize it
    result.name = f"C22AMI2_{length}"
    result.category = "statistics"

    return result


c22_ami2.__doc__ = \
"""catch22 automutual information of returns at lag 2 (C22AMI2)

How much the bin a return falls into tells you about the bin the
return TWO bars later falls into: cut the last `length` daily returns
into 5 even bins spanning their own range, count the 98 lagged pairs
into a 5x5 table, and report the mutual information of that table in
NATS, bias-corrected.

    C22AMI2 = MI(bin(r[t]), bin(r[t+2])) - Miller-Madow correction

**The output can be slightly NEGATIVE, and that is the estimator and
not a bug.** A mutual information cannot be, but this is the
MILLER-MADOW BIAS-CORRECTED estimate of one, and a corrected estimate
of a quantity that is near zero lands on both sides of it. The
derived bounds at `length` 100 are `[-0.0816, 1.6298]` --
`-(5-1)**2 / (2 * 98)` to `log 5 + (5-1) / (2 * 98)` -- and on five
stochastic 1,500-bar frames (an iid walk, a tick-rounded walk, a
2-lira stock on a 1-kurus tick, an AR(1)-in-returns path, a
Student-t(3) path) the measured range is -0.0329 to 0.2066 with
medians 0.023 to 0.088. On 400 independent normal windows the column
reads a median of **+0.028** and is negative on **17.3%** of them
(section A10b, drawn through this kernel; section A10's separate
400-window sample gives +0.0282 and 15.5%), so
"near zero, either sign" is the reading for "no lag-2 dependence this
binning can see" **at the default `length`** -- the correction scales
as `1 / (2 (length - 2))`, so that figure moves with it (+0.228 at
`length` 27, +0.008 at 250; see the `length` note below). The
UNCORRECTED plug-in MI reads +0.086 on section A10's windows -- its
own first-order bias, `(5-1)**2 / (2 * 98)` = 0.0816 nats, which is
larger than the MEDIAN reading of four of the five stochastic frames
here and not of the fifth -- all five from the same 1,400-bar run
(walk 0.0428, tick-rounded 0.0270, penny 0.0262, student-t 0.0234,
AR(1) **0.0883**) -- and 11% of the 20-bar cosine frame's 0.7295,
which is what the correction is for.

**THE TWO READINGS THAT DECIDE THE COLUMN, AND HOW THEY WERE PINNED.**
The definition leaves two things open, and both were settled by
measurement rather than by taste (`docs/measure_c22_ami2.py` §P1c):
* **where the buffer goes.** The bin edges are evenly spaced between
  the window's own minimum and maximum, with only the two OUTER edges
  pushed out by 0.1 so that both extremes fall inside a bin -- the
  buffer is there for INCLUSION. Pushing it into the interior edges
  too (evenly spaced over `[min - 0.1, max + 0.1]`, the other way to
  read the same sentence, and this port's first reading) is a
  different column: it moves 246 to 463 of 467 sampled windows on
  each of the five stochastic frames, by up to 0.070 nats, Spearman
  +0.73 to +0.88 (and 0 windows on the 20-bar cosine frame, where
  this column takes 8 values over 1,400 bars).
* **the bias correction.** Dropping it moves 467 of 467 sampled
  windows on five of the six frames and 436 of 467 on the Student-t
  one, by up to 0.0816 nats, Spearman +0.74 to +0.99 against the
  shipped column. The 31 windows it does NOT move are not a rounding
  artefact: the correction is an integer multiple of `1 / (2 * 98)`
  and it is exactly 0 where the table's occupied cells, rows and
  columns satisfy `cells = rows + cols - 1`.
Of the 18 candidate readings fitted to the reference implementation as
a BLACK BOX over 2,802 windows, the shipped one reproduces it on
**2,802**, the interior-buffer reading on 763, the uncorrected plug-in
on 31 and the rest on 21 or fewer.

**This port IS the column the 2026-10-24 screen measured.** Over
EVERY window of six frames -- 8,400 of them -- it equals the GPL-3.0
reference to within 1e-12 on 8,400 (worst gap 2.2e-16, Spearman
+1.0000 per frame on the five non-degenerate ones) and is BIT-equal on
2,299. So the screen's Gate E figure (max |rho| 0.0595 vs
`Dist_from_High_252_pct`, SHIP) is an expectation that transfers,
unlike `c22_periodicity`'s -- though it is still a figure measured on
the prototype, and Gate E is re-run on this port.

Source: catch22 (Lubba, Sethi, Knaute, Schultz, Fulcher, Jones 2019,
*Data Mining and Knowledge Discovery* 33:1821, "catch22: CAnonical
Time-series CHaracteristics"), feature `ami2` /
`CO_HistogramAMI_even_5bin_ami2` of catch22 1.0 -- the hctsa operation
`CO_HistogramAMI(y, 2, 'even', 5)` -- applied by PandasTa issue #127
to the last 100 daily simple returns. The bias correction is Miller
and Madow's (1955), applied to each of the three entropies in
`MI = H(i) + H(j) - H(i, j)`.
⚠ **Which catch22 this is.** catch22 1.0 renamed AND REDEFINED this
feature from `CO_HistogramAMI_even_2_5` "to match hctsa" -- that is
the reference's own deprecation notice, quoted in
`docs/C22Ami2Measured.md` section P. Every figure here is measured
against **pycatch22 1.0.2**, the post-change definition, which is
also the one the 2026-10-24 screen read. The PRE-1.0 definition was
never run and nothing here claims to be it.
The reference implementation (pycatch22 1.0.2) is **GPL-3.0** and this
fork is MIT: this module was written from the DEFINITIONS and from a
named estimator, no shipped module imports the reference (a test
asserts that over the whole package), and the one place it is run at
all is `docs/measure_c22_ami2.py` section P -- opt-in, measurement
only, the same use the owner's own screen prototype makes of it. ⚠
hctsa's own source is not in this tree and was not read: what section
P knows about it is what the reference's OUTPUT shows, and the two
structural readings above are identified by fitting candidates to that
output.

⚠ catch22 is a subset selected for TIME-SERIES CLASSIFICATION
performance on 93 reference problems. That is not return prediction,
and nothing here tests it on BIST: its presence in this fork is
existence, not evidence.

Gate A also checks the quantity five ways that share no code with
this module:
* an EXACT oracle that rounds zero times in the part that can move a
  value. The bin edges are affine in the window's own min and max, so
  the z-score's irrational `sd` cancels out of every membership test
  and the whole 5x5 count matrix is decided by exact rational
  comparisons: 90 of 90 sampled windows across six frames come out
  with the same count matrix, and the value agrees to 2.2e-16;
* the definition re-spelled in plain Python with `math.fsum` and no
  numpy vectorisation (max gap 1.1e-16 over 1,200 windows);
* the entropy identity `H(i) + H(j) - H(i, j)`, which is
  algebraically the same and rounds differently (1.6e-15);
* `np.histogram2d` for the binning, half-open convention included
  (1.1e-16), and `sklearn.metrics.mutual_info_score` for the
  information (1.2e-15);
* two EXACT laws. Returns that alternate exactly +2% / -2% have
  `r[t+2] == r[t]`, so the table is a bijection, the MI is the
  marginal entropy `ln 2` and the correction ADDS `(k-1)/196` over the
  `k = 2` occupied cells: every one of 1,400 bars reads
  0.698249221376, one distinct value. A period-4 cosine has
  `r[t+2] == -r[t]`, `k = 3`, and reads 1.049820721962 on all 1,400.

**What is INERT here, measured rather than assumed.** Three knobs a
reader might expect to matter do not, and for one reason: the interior
edges are an affine function of the window's own extremes, so any
positive affine map of the window leaves every bin assignment alone.
Over 467 windows of each of six frames, 0 move under the population
z-score (`ddof` 0), 0 under NO z-score at all, 0 under a +1 shift, and
0 under a buffer of 0, 0.01, 1 or 1e6. The reference agrees: it
returns the same value for a window and for its z-score. ⚠ The
invariance needs a finite `sd`, which is why the `isfinite(sd)` limb
exists -- see the NaN paragraph below. Taking the
range from the lagged-FROM limb instead of from the whole window is
NOT inert -- 5 to 9 windows of 200 on the five stochastic frames, 0
on the cosine one -- and neither are the
feature's own parameters: at `tau` 1, 3 or 5 the Spearman against the
shipped column is +0.13, +0.06 and +0.13, and at 3 or 10 bins -0.05
and +0.44.

Calculation:
    Default Inputs:
        length=100, TAU=2, NUM_BINS=5, BUFFER=0.1, ZSCORE_DDOF=1
    r[t]   = close[t] / close[t-1] - 1
    X      = r[T-length+1 .. T]                 (the window)
    Z      = (X - mean(X)) / sd(X, ddof=1)      (inert, see above)
    b[i]   = min(Z) + i * (max(Z) - min(Z)) / 5,   i = 1 .. 4
             (b[0] = min(Z) - 0.1, b[5] = max(Z) + 0.1, neither of
              which can bind)
    k[t]   = how many of b[1..4] that Z[t] stands at or above
    N[a,c] = #{t : k[t] = a and k[t+2] = c},    98 pairs
    p      = N / 98,  pi = rowsums(p),  pj = colsums(p)
    MI     = sum over N[a,c] > 0 of p log(p / (pi pj))
    C22AMI2 = MI - (occupied cells - occupied rows - occupied columns
                    + 1) / (2 * 98)

**ONE blanking rule.** The window is NaN unless its return standard
deviation clears 9.09e-13 (4096 eps). It is inert on anything with
noise in it -- 0 of 1,400 bars differ from the unguarded spelling on
each of the six frames -- and what it buys is that this column reads
SHAPE and not size, so rounding noise would be read at full strength:
* an exactly geometric price path holds 3 or 4 distinct returns per
  window with a standard deviation of 8.9e-17 to 1.5e-16, and
  unguarded -- measured on every window, through this module's source
  with the floor removed -- it fires on all 1,400 bars reading -0.0199
  to 0.0932, median 0.0103: squarely inside the walk frame's own
  range, and a reader could not tell the difference. The frame IS
  rounding noise, so those three digits move with the CPU dispatch
  (-0.0199 to 0.0417 with AVX-512 / AVX2 / FMA3 off) while the count
  does not;
* a price flat at 1e6 except for ONE 1-ulp step: of its 1,500 bars
  only the 100 whose window holds the step have any variation at all,
  and unguarded those 100 read 0.000000 to 0.000105 (median
  0.000105) -- this column's "no dependence", measured on every one
  of them rather than sampled;
* a price that goes flat at bar 400 blanks from bar 499, the first bar
  whose whole window of returns is zero. Nothing blanks earlier.
⚠ **It does NOT empty a deterministically smooth path**, and that is
worth knowing in the other direction: a price rising by exactly one
kurus a bar has a return standard deviation of 2.9e-07, 316,000 times
the floor, so it fires on all 1,400 bars -- and it reads **1.3432**,
constant, near the top of the scale, because a smooth monotone return
series really is almost perfectly lag-2 dependent. `c22_periodicity`
blanks that same frame; this column does not.

Causal: bar T reads closes T - length .. T. Measured by
future-perturbation sweep -- 0 of 35 offsets leak on each of six
frames with eight splices apiece, and 0 of 35 at `length` 27, 120 and
250 -- and by twelve mutants read off this file, edited and exec'd in
memory. The four look-ahead mutants are caught at 35 of 35 offsets
each, which is the whole sweep: this column ties on 7.2% to 21.7%
of neighbouring bar pairs -- 7.4% to 21.5% with AVX-512 / AVX2 / FMA3
off, the tie share being a count of exact float equalities -- and
takes 1,043 to 1,296 distinct values on the five
stochastic frames, 8 on the 20-bar cosine one, so unlike the
integer-valued catch22 siblings there is almost nowhere
for a one-bar shift to hide. Where a back-dated write moves any
pre-splice bar, the first bar it moves is J-1 (22 of 22 offsets). The
mask mutant is bit-equal on a clean frame and caught 12 of 12 on a
frame with one bad close. ⚠ THREE mutants are DEAD, each for a
measured reason: centring or scaling each row by the whole CHUNK's
mean or standard deviation is the affine invariance above and is
bit-equal on three frames, and swapping which limb indexes the rows of
the joint table changes nothing but the order of the 25 logarithms --
5.6e-17, on 568 to 618 bars of 1,400 under this machine's dispatch and
539 to 625 with AVX-512 / AVX2 / FMA3 off, which is how little that
count means beside the gap -- because a mutual information and
its Miller-Madow term are symmetric. The cross-row read
that does bite is taking the EXTREMES from the chunk, and that mutant
is caught at 30 of 35 offsets. The remaining three of the twelve
(`no-bias-correction`, `no-overflow-guard`, `no-floor`) are not
look-aheads and are expected clean on the sweep: they are there
because they change VALUES, each has its own test, and a sweep that
caught them would mean the sweep is measuring something other than
causality.
Scale-free: bit-identical under x8, x64, 2**-40 and 2**40 on all six
frames, at `length` 27 / 120 / 250, and at price levels 1e-6, 1e+6 and
1e+100 -- BY CONSTRUCTION, since the price enters only as
`c[t] / c[t-1]`, and `8a / 8b` is the double `a / b`. x10, x3.7, x0.1
and x1.0000001 are bit-identical too, and here that is not luck: the
value is a function of a 5x5 matrix of INTEGER counts, so a
perturbation that moves no point across a bin edge cannot move the
output at all, and the measured margin to the nearest edge is 1.25e-06
(median 2.6e-03 to 1.9e-02). Blind to a rescale of the returns
themselves (0 of 467 windows at x0.5, x2 and x10) and moved by their
ORDER (467 of 467, Spearman +0.045).
NaN on the first `length` bars; on every window holding a close that
is NaN, infinite, zero, negative or subnormal (101 bars at the
default); on a window holding a close PAIR whose ratio overflows to an
infinite return (100 bars); on a window whose SUM OF SQUARES overflows
although the returns themselves are finite, which a close pair of
ratio 1e200 reaches and one of ratio 1e77 does not (100 bars --
without that guard those bars read exactly 0.0, measured, which is a
value and not a blank); and under the blanking rule above.

Cost: the windows are walked in chunks, so the peak is set by
`CHUNK_VALUES` and not by `len(close) * length`: at n = 400,000 the
traced peak is 27.1 MB (tracemalloc) and the run takes about 1.4 s.
Budgets of 100, 400, 1,024 and the default are bit-equal, so the chunk
boundary is invisible. Wall clock is not quoted as a band because it
does not reproduce.

Args:
    close (pd.Series): Series of 'close's
    length (int): RETURNS per window, so `length + 1` closes. At least
        `NUM_BINS**2 + TAU` = 27 -- so a window has at least as many
        lagged pairs as the joint histogram has cells -- and a smaller
        or missing value falls back to the default.
        ⚠ **The SCALE is a function of it**, because the bias
        correction scales as `1 / (2 * (length - TAU))`. On 400
        independent normal windows the column reads a median of
        +0.228 at 27, +0.084 at 50, +0.028 at 100 and +0.008 at 250,
        and is negative on 0.25% / 8.5% / 17.3% / 28.5% of them; the
        bounds go `[-0.3200, 1.6894]` at 27 to `[-0.0323, 1.6175]` at
        250. So "no lag-2 dependence is about +0.028, either sign" is
        a DEFAULT-LENGTH statement, and at 27 the reading is mostly
        the estimator's own bias. Default: 100
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)

Returns:
    pd.Series: C22AMI2_{length}, nats, inside `ami_bounds(length)` =
        [-0.0816, 1.6298] at the default
"""
