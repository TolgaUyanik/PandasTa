# -*- coding: utf-8 -*-
import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from pandas import Series

from pandas_ta.utils import get_offset, verify_series

#: tsfresh's `num_segments`. A module constant and not an argument: the
#: source's `segment_focus` means "the LAST chunk" only because it is
#: `num_segments - 1`, so the two cannot move independently without changing
#: which chunk the column reads. `docs/TsEnergyLast20Measured.md` (A5) prices
#: the other segment counts.
SEGMENTS = 4
#: tsfresh's `segment_focus` -- the last of the `SEGMENTS` chunks.
SEGMENT_FOCUS = SEGMENTS - 1
#: Fewer returns than chunks makes `np.array_split` hand the focused chunk
#: nothing, and `np.sum([])` is 0.0, so the column would be identically zero
#: rather than a share. At `length` 4 the tail is one return.
MIN_LENGTH = SEGMENTS
EXTRA_CLOSES = 1  # `length` returns need `length + 1` closes


def _tail(length):
    """The length of `np.array_split(x, SEGMENTS)[SEGMENT_FOCUS]`.

    `np.array_split` gives `length % SEGMENTS` chunks of `length // SEGMENTS
    + 1` and the rest `length // SEGMENTS`, the longer ones FIRST, so the
    last chunk is always the trailing `length // SEGMENTS` values -- 5 at the
    default. Pinned against `np.array_split` itself for every `length` from
    `MIN_LENGTH` to 240 by
    `tests/test_ts_energy_last_20.py::test_the_tail_is_numpys_own_last_chunk`.
    """
    return length // SEGMENTS


def ts_energy_last_20(close, length=None, offset=None, **kwargs):
    """Indicator: share of the window's squared-return energy in its last
    quarter (TS_ENERGY_LAST)"""
    # Validate Arguments
    length = int(length) if length and int(length) >= MIN_LENGTH else 20
    close = verify_series(close, length + EXTRA_CLOSES)
    offset = get_offset(offset)

    if close is None: return

    tail = _tail(length)

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

    # The bound is on the return and it is taken BEFORE the square, so the
    # square cannot overflow: `length` values of at most `bound ** 2` sum to
    # at most half the float maximum, which is a real number rather than an
    # infinity. An infinite total would make every ratio 0 or NaN instead of
    # a share. A comparison against NaN is False, so this one test also drops
    # both NaN and inf. The ceiling it puts on a return is 2.120e+153 at
    # `length` 20: nothing a market can produce.
    bound = np.sqrt(np.finfo(float).max / (2 * length))
    r = np.where(np.abs(r) < bound, r, np.nan)
    e = r * r

    ew = sliding_window_view(e, length)

    # The window's TOTAL energy and its TAIL energy. `sliding_window_view`
    # gives each row a stride of one double, so a row IS a contiguous run of
    # `length` doubles and `axis=1` reduces it through the same pairwise
    # summation `np.sum` uses on the source's own `(length,)` array. That is
    # why this spelling is BIT-EQUAL to tsfresh's rather than close to it:
    # 1,480 of 1,480 bars on each of ten frames and at `length` 4, 5, 7, 21,
    # 40 and 250 (docs/TsEnergyLast20Measured.md, A1). The tail slice is basic
    # slicing, so it is a view too and nothing `(rows, length)` is
    # materialised.
    #
    # Two things this is NOT, each deliberate:
    # * not a left-to-right accumulation over the same view, which is a
    #   different summation order and is FARTHER from the correctly rounded
    #   answer -- mean 0.77 .. 1.42 ulps against an exact rational oracle
    #   where this spelling is 0.66 .. 0.87 (§A3);
    # * not a rolling sum, which is what the screen prototype uses and what
    #   is NON-LOCAL -- `rolling(length).sum()` carries one running
    #   accumulator across windows, so a single enormous return leaves a
    #   residue in every later window (measured in §G4).
    den = ew.sum(axis=1)
    num = ew[:, length - tail:].sum(axis=1)

    # The source's own rule: `full_series_energy == 0` -- every value in the
    # window exactly zero -- has no energy to take a share of, and tsfresh
    # returns NaN for it. `den > 0.0` is exactly that test (a sum of squares
    # is never negative) and it is also False for the NaN a bad close or an
    # out-of-bound return leaves behind.
    with np.errstate(invalid="ignore"):
        val = np.where(den > 0.0, num / den, np.nan)

    out = np.full(c.size, np.nan)
    out[length - 1:] = val
    energy = Series(out, index=close.index)

    # Offset
    if offset != 0:
        energy = energy.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        energy.fillna(kwargs["fillna"], inplace=True)

    # Name and Categorize it
    energy.name = f"TS_ENERGY_LAST_{length}_{SEGMENTS}"
    energy.category = "statistics"

    return energy


ts_energy_last_20.__doc__ = \
"""Recency of the window's squared-return energy (TS_ENERGY_LAST)

The share of a `length`-bar window's squared-return energy in its
newest quarter. ⚠ Overlaps the shipped TFCENTROID_20 at 0.7493 on
synthetic frames. 0.25 is an even spread, near 1 every big move was
recent, near 0 they were all old. (The first two sentences are short on
purpose: `docs/gen_indicator_dictionary.py` keeps only the first 150
characters of this paragraph for `docs/IndicatorDictionary.md`, which
CLAUDE.md sends a reader to first, so the overlap has to fit inside
them.)

    x            = the window's `length` simple returns
    tail         = length // 4, the last chunk numpy's own split gives
    TS_ENERGY    = sum(x[-tail:] ** 2) / sum(x ** 2)

Source: tsfresh feature_calculators (MIT),
`energy_ratio_by_chunks(num_segments=4, segment_focus=3)`, as PandasTa
issue #102 applies it: "on 20 returns". The published function is

    full = np.sum(x ** 2)
    NaN if full == 0 else
        np.sum(np.array_split(x, num_segments)[segment_focus] ** 2.0)
        / full

and this module is that expression with `x` the window's `length`
simple returns. `segment_focus = num_segments - 1` is the LAST chunk,
and `np.array_split` hands the longer chunks out first, so that chunk
is always the trailing `length // num_segments` values -- 5 of 20 at
the default. That is checked against `np.array_split` itself, size and
indices, for every `length` from 4 to 240, rather than argued.
⚠ tsfresh is NOT installed in this worktree and web access is
unavailable, so what Gate A checks is the published definition quoted
above plus the issue's line, not a read of tsfresh's own source. The
20, the 4 and the 3 are the issue's own parameters.

**Gate A is BIT-equality, and that is why the spelling is what it is.**
The source's expression, retyped with `np.array_split` picking the
chunk and `np.sum` doing both sums, window by window and sharing no
code with this module: 1,480 of 1,480 bars on each of ten 1,500-bar
frames with identical NaN masks, and at `length` 4, 5, 7, 21, 40 and
250. `sliding_window_view` gives each row a stride of one double, so a
row is a contiguous run of `length` doubles and `ew.sum(axis=1)` is the
same pairwise reduction `np.sum` runs on the source's own `(length,)`
array -- equality by construction rather than by luck, and it survives
`NPY_DISABLE_CPU_FEATURES="AVX512F AVX512_SKX AVX2 FMA3"`.
⚠ The left-to-right accumulation a reader reaches for first is 3 to 4
ulps away from this one and FARTHER from the correctly rounded answer:
measured against an exact rational oracle, mean 0.77 .. 1.42 ulps
against this spelling's 0.66 .. 0.87, worse on 10 of 10 frames.

**⚠ It is a RECENCY of volatility, not a level, and this fork already
ships two neighbours.** A share cancels the window's overall size, so
the column cannot see how volatile the window was: Spearman 0.0338 ..
0.3947 against `NATR_20`, -0.3312 .. +0.1512 against `UI_20`, -0.2231
.. +0.0275 against the window's own return standard deviation and
-0.0413 .. +0.0341 against the close itself, over ten synthetic frames.
What it CAN see is where in the window the volatility sat, which is
`TFCENTROID_20`'s question (TSFEL's temporal centroid, issue #116,
merged 2026-10-30, the energy-weighted MEAN position of the SAME 20
returns) and `TS_IMQ_20`'s (issue #99, the absolute-mass MEDIAN
position). Measured over the same ten frames: pooled **0.7493** against
`TFCENTROID_20` (n = 14,800), per-frame |rho| median 0.7261, max
**0.9066**, 1 of 10 at or above 0.90; and pooled 0.6093 against
`TS_IMQ_20`, median 0.5465, max 0.8812, 0 of 10 at or above 0.90. The
frame that reaches 0.9066 is `clustered`, built for this receipt to
pile energy up at one end of a window, which is the adversarial case
for the pair. Both of those figures sit in the SHIP band under
`r3-perframe-0.90` -- below the 0.76 line, not in DISCLOSE_GAP's
0.80 .. 0.90 -- and they are reported anyway because the per-frame MAX
reaches 0.9066, which no band reads. Not STRUCK: that needs pooled
>= 0.90 or a per-frame MEDIAN >= 0.90, and neither limb is close.
⚠ Those are SYNTHETIC and no real-frame figure for either pair exists:
Gate E's 687 comparators are the engine's and hold no pandas_ta port,
and the 2026-10-24 screen's fork overlap (max |rho| 0.5795 vs
`bbands:BBB_5_2.0`, 12 frames) was taken six days before
`tf_centroid_20` entered `Category` and three weeks before
`ts_imq_20`, so it cannot bound them. See
`docs/TsEnergyLast20Measured.md` §O.
⚠ The nearest thing of all is a 5/20 mean-|return| RATIO built from the
same closes -- a local stand-in for the engine's `ATR_Ratio_5_20`
family -- at 0.9558 .. 0.9986. That stand-in is NOT the engine's
column, and the gap matters: the screen measured the real
`ATR_Ratio_5_20` at 0.5460 and `natr_Chg_5d` at 0.7020 on 89 real
frames where the close-based stand-ins here read 0.96 and 0.90. Gate E
is what decides the band.

**0.25 is the neutral reading, and it is 0.25 for any return law.** On
20,000 INDEPENDENT windows the mean is 0.2488 for gaussian returns,
0.2474 for student-t(2) and 0.2503 for one-sided exponential ones --
`tail / length`, because a share of an evenly spread total does not
care about the shape. What the tails change is the SPREAD: sd 0.1298 /
0.2309 / 0.1773.
Three closed forms pin the ends. A window whose oldest `length - tail`
returns are exactly zero reads exactly **1.0**; one whose newest `tail`
returns are exactly zero reads exactly **0.0**; and one whose returns
all have the same MAGNITUDE reads exactly `tail / length` -- measured
at `length` 4, 8, 20 and 60 for all three.
⚠ The bound [0, 1] is not a float theorem: `num` and `den` are reduced
over DIFFERENT subsets of the window, so `num <= den` is exact
arithmetic and could in principle be lost to rounding. Measured: 0 of
14,800 bars outside it over the ten frames, 0 at `length` 4, 5, 7, 21,
40 and 250, and 0 of 2,000 windows built to straddle 1.0, whose largest
reads exactly 1.0.

**It is a state for `tail` bars and then forgets.** Windows one bar
apart share `length - 1` returns, so the column autocorrelates at
0.7859 at lag 1 on a walk -- and then goes to nothing, -0.0278 at lag 5
and 0.0006 at lag 20. On the clustered frame, where volatility itself
persists, lag 5 is 0.4227 and lag 20 **-0.3804**: a cluster that was in
the tail of window T sits in the body of window T+20. One bar moves
exactly `length` bars and the SIGN says which sum it is in -- a -50%
bar at 700 moves bars 700..719, up on the first 5 and down on the
other 15.

**It is blind to the SIGN of every return**, because it reads `r * r`:
the right- and left-skewed frames of the receipt, whose returns are
exact negatives of each other, agree to 1.8e-14 with Spearman
1.000000. ⚠ That is ranks and a tolerance rather than bit-equality, and
the reason is the frame and not the column -- a sign-flipped frame has
to be rebuilt from closes, which re-rounds every return.

**This column is the screen prototype in RANK, not bit for bit.** Issue
#102's prototype (`docs/issues/screen/ind_screen.py`, candidate
`ts_energy_last_20`) is `sdiv(tsum(r2, 5), tsum(r2, 20))`: two
`rolling().sum()` calls, which carry one running accumulator across
windows. Identical NaN masks and Spearman 1.000000 on nine of the ten
frames (0.998284 on the two-point one, where this column is a
constant), but up to 9,170 ulps apart on the clustered frame -- and on
those nine it is the PROTOTYPE that is out, 40 to 9,170 ulps from the
exact oracle where this module is at most 5. (On the two-point frame it
is the other way round, 3 against 4: every window there holds the same
20 squares, so a running accumulator has nothing to drift against.)
⚠ The same non-locality is a correctness failure and not a rounding
one. With one return 1e+08 times the frame's scale planted at bar 200
of a 2,000-bar frame, this module is bit-identical to the unspiked
frame on all 1,778 bars the spike has LEFT, and so it is at x1e+02,
x1e+06, x1e+100 and x1e+300; the prototype is bit-identical on 41, 41,
0, 0 and 0 of them. HOW MANY it loses is kernel-dependent and is not a
claim: running the same section under
`docs/measure_ts_energy_last_20_cpu.py G` moves three of those five to
1,690, because whether a compensated running sum clears its residue
depends on the frame's last bits. That it loses SOME is the claim.
Because Gate E's statistic is a Spearman, the screen's figures for the
prototype (max |rho| 0.7020 vs `natr_Chg_5d`, n = 397,069, SHIP) are
expected to carry over; the launcher's Gate E run on THIS module is
still the number that decides ship or revert.

Causal: bar T reads closes T - length .. T, measured by a
future-perturbation sweep (0 of 36 offsets on each of four frames and
at `length` 4, 7, 60 and 250) and by the six mutants in
`tests/test_ts_energy_last_20.py`. Five are caught at 36 of 36 offsets
on every frame; the sixth, which shifts the per-return bound's own
index, is caught 0 of 36 by the blind sweep and 12 of 12 by a frame
built to give it something to mis-read.
Scale-free: every input is a price ratio, and `8a / 8b` is the same
double as `a / b`, so the column is bit-identical under a x8/x64
rescale of price -- 1,480 of 1,480 fired bars on each of ten frames at
BOTH factors, at `length` 4 / 5 / 7 / 21 / 60 / 250, and at price
levels 1e-6, 1e+6 and 1e+100.
⚠ x10, x3.7, x0.1 and x1.0000001 are NOT bit-identical by construction
and are not bit-identical in fact; they keep the NaN masks exactly and
agree to a max relative difference of 4.6e-13, on the clustered frame
whose smallest value is 1.1e-04. On the TWO-POINT frame their Spearman
is 0.54 .. 0.61, which is rounding and not a scale failure -- the
column there is 111 doubles spanning 1.2e-14 around the exact 0.25 --
so that frame is read on the relative difference only.
⚠ `price ** 2` and `price ** 0.5` are not rescales and the column is
not invariant to them (0 of 1,480 bars bit-equal, values up to 0.0139
apart), though it nearly is in RANK, 0.999583 and 0.999885: a power map
scales every LOG return by the power, so a ratio of squared LOG returns
would be exactly invariant, and simple returns approximate log returns.

NaN on the first `length` bars; on any window holding a close that is
NaN, infinite, zero, negative or subnormal (such a close spoils two
returns, so it empties the `length + 1` = 21 windows it sits in --
measured at bar 200 of a 400-bar frame, with 0 earlier bars moved in
all 36 (bad value, position) pairs tried, and fewer windows near either
end: 1 / 2 / 20 / 21 / 2 / 1 for a bad close at bar 0 / 1 / 19 / 200 /
398 / 399); on any window holding a return whose magnitude reaches
`sqrt(max / (2 * length))`, i.e. |r| >= 2.120e+153; and on any window
whose squared returns are ALL EXACTLY ZERO.
⚠ That last rule is the source's own `full_series_energy == 0`, and it
has two routes to it. `length + 1` identical closes is one. The other
is UNDERFLOW: a return below `sqrt(tiny)` = 1.49e-154 squares to zero,
so 60 returns of 1e-200 fire 0 of 60. Honest data cannot reach either.
⚠ The per-return bound is taken BEFORE the square, which is the whole
point of it: `length` squares of the bound sum to half the float
maximum, so a window's total is a number rather than an infinity, and
the square itself cannot overflow -- a frame of nothing but
out-of-bound returns raises 0 numpy warnings.
⚠ **There is NO dispersion floor here, and that is a decision.** Its
siblings `statistics/ts_binent_20.py` and `statistics/ts_aggac_60.py`
refuse a degenerate window at 4096 ulps, on the return RANGE and on the
return SD respectively, because both read a spread whose own rounding
the statistic then amplifies -- and both floors are priced here, since
the decision names both modules. This
one divides a window's energy by that window's own total, so a
degenerate window gives the right answer instead of a loud one: a
1%-a-bar geometric ladder, whose return is only MATHEMATICALLY constant
and which float64 renders only to rounding, reads 0.25 on all 280 of
its windows, within 1e-14 of the exact answer and at 3 ulps of it.
Adding EITHER floor would empty all 280 of those honest windows and 0
dishonest ones; a quiet-but-honest frame (returns 1e-6) fires on 580 of
600 over more than 500 distinct values and survives both untouched.

Cost: two reductions over a `sliding_window_view`, with no allocation
that grows with `length` -- the traced peak is 22.8 MB on 400,000 bars
at each of `length` 4, 20, 60 and 250. The TIME does grow with
`length`, because each window is reduced in full rather than being
updated from its neighbour: the BEST OF 5 runs is monotone in `length`
and `length` 250 costs between 2.59x and 2.74x `length` 4 (seven such
runs, measured). The window-by-window
oracles this was checked against are slow enough to live in
`docs/measure_ts_energy_last_20.py` rather than here.
⚠ No wall-clock figure is quoted anywhere but in one place
(`docs/TsEnergyLast20Measured.md` §Z) on purpose, and even there only as
a best-of-5: they move between runs and between machines by up to 40% on
the same worktree, and timing each length ONCE was enough to print a
non-monotone table (measured, review round 3). The peak, the ordering
and the ratio are the claims.

Calculation:
    Default Inputs:
        length=20
    r[t]        = close[t] / close[t-1] - 1
    tail        = length // 4
    TS_ENERGY[T] = sum(r[T-tail+1 .. T] ** 2)
                   / sum(r[T-length+1 .. T] ** 2),
                   NaN where those squared returns are all exactly zero

Args:
    close (pd.Series): Series of 'close's
    length (int): Returns per window. At least 4 -- fewer returns than
        chunks leaves the focused chunk empty -- so a smaller or missing
        value falls back to the default. Default: 20
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)

Returns:
    pd.Series: TS_ENERGY_LAST_{length}_4, dimensionless, in [0, 1]
"""
