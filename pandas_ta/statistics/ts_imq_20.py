# -*- coding: utf-8 -*-
import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from pandas import Series

from pandas_ta.utils import get_offset, verify_series

# A window of ONE return is identically 1.0: its single value carries all of
# the mass, so the crossing is at position 1 and `1 / 1` is the only value the
# column can take. Two returns is the smallest window on which it varies, and
# there it takes only 0.5 and 1.0.
MIN_LENGTH = 2
EXTRA_CLOSES = 1  # `length` returns need `length + 1` closes
#: The source's `q`. It is a module constant and not an argument: the issue
#: asks for one quantile, `q = 0.5`, and the column NAME carries only
#: `length`, so a second parameter could not reach the name without changing
#: it for every caller. `docs/TsImq20Measured.md` (A5) prices the other `q`.
Q = 0.5


def ts_imq_20(close, length=None, offset=None, **kwargs):
    """Indicator: index mass quantile of |returns| (TS_IMQ)"""
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
    # The source's `abs_x = np.abs(x)`. The issue already hands it
    # `|returns|`, so the source's own absolute value is a no-op on top of
    # this one (measured: bit-equal on 1,480 of 1,480 bars of each of three
    # frames); taking it HERE, once, on the `(n,)` array is what keeps
    # `sliding_window_view` below a view rather than a copy.
    a = np.abs(r)
    # Every kept `|r|` is under `max / (2 * length)`, so a window's `length`
    # of them sum to at most half the float maximum: the total is a real
    # number rather than an infinity, which would make every `acc / s` ratio
    # 0 or NaN and so report the crossing at the wrong position (or not at
    # all). A comparison against NaN is False, so this one test also drops
    # both NaN and inf. The ceiling it puts on a return is 4.494e+306 at
    # `length` 20: nothing a market can produce.
    a = np.where(a < np.finfo(float).max / (2 * length), a, np.nan)

    aw = sliding_window_view(a, length)
    rows = aw.shape[0]

    # The window's TOTAL mass, accumulated in the same left-to-right order
    # `np.cumsum` uses below, so the two agree bit-for-bit at the last
    # position -- which is what makes the crossing test below always fire on
    # a window with mass (see `found`).
    #
    # Three things this spelling is NOT, each deliberate:
    # * not `aw.sum(axis=1)`: numpy's reduction is PAIRWISE, so it would not
    #   match the sequential accumulation and the last ratio would be `1.0`
    #   only to rounding;
    # * not a difference of a GLOBAL `np.cumsum(a)`, which is both lossy and
    #   NON-LOCAL -- one enormous return sits inside every later partial sum.
    #   Measured: with a 1e+100 return planted at bar 200 of a 2,000-bar
    #   frame, that spelling returns NaN on every one of the 1,780 bars from
    #   220 on, where this one is bit-identical to the unspiked frame on all
    #   1,780 (docs/TsImq20Measured.md, Guards G4);
    # * not `np.cumsum(aw, axis=1)`, which materialises a `(rows, length)`
    #   copy of the view. The loop's peak does not grow with `length` at all:
    #   30.0 MB on 400,000 bars at each of `length` 2, 20, 60 and 250.
    s = np.zeros(rows)
    for j in range(length):
        s += aw[:, j]

    # `np.argmax(mass_centralized >= q) + 1`, written as a left-to-right
    # scan: `idx` is the 1-based position of the FIRST bar at which the
    # window's accumulated mass reaches `Q` of its total, and `found` freezes
    # it there so a later crossing cannot overwrite the first one (which is
    # what `argmax` on a boolean array means).
    acc = np.zeros(rows)
    idx = np.zeros(rows, dtype=np.int64)
    found = np.zeros(rows, dtype=bool)
    with np.errstate(invalid="ignore", divide="ignore"):
        for j in range(length):
            acc += aw[:, j]
            # `acc / s >= Q` and not `acc >= Q * s`: the source divides first
            # and compares the ratio. The two are the same comparison in
            # exact arithmetic and could disagree only where rounding
            # straddles the threshold; measured bit-equal on 1,480 of 1,480
            # bars of a walk (docs/TsImq20Measured.md, A5).
            hit = ~found & (acc / s >= Q)
            idx = np.where(hit, j + 1, idx)
            found |= hit

    # The source's own rule: `s == 0` -- every value in the window zero -- has
    # no mass to find a quantile of, and tsfresh returns NaN for it. `s` is a
    # sum of absolute values, so `s > 0` is exactly "not all zero", and it is
    # also False for the NaN a bad close or an out-of-bound return leaves
    # behind.
    #
    # `found` is a labelled BACKSTOP with no witness, kept deliberately. It
    # cannot be False where `s > 0`: `acc` after the last step is the same
    # sequence of additions as `s`, so it is the same double, `s / s` is
    # exactly 1.0, and `1.0 >= Q` for any `Q <= 1`. Counted over every window
    # of every frame in docs/measure_ts_imq_20.py (Gate A4): `found` and
    # `s > 0` disagree on 0 windows of each of nine frames. It costs one pass
    # over a `(rows,)` array and it is what stops a future `Q > 1` from
    # reporting position 0 -- which is not an argument but a mutant:
    # `tests/test_ts_imq_20.py` raises `Q` to 1.5 and shows the column goes
    # empty with this term and reports 0.0 on all 280 bars without it.
    reported = (s > 0.0) & found

    out = np.full(c.size, np.nan)
    out[length - 1:] = np.where(reported, idx / length, np.nan)
    imq = Series(out, index=close.index)

    # Offset
    if offset != 0:
        imq = imq.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        imq.fillna(kwargs["fillna"], inplace=True)

    # Name and Categorize it
    imq.name = f"TS_IMQ_{length}"
    imq.category = "statistics"

    return imq


ts_imq_20.__doc__ = \
"""Index mass quantile of |returns| (TS_IMQ)

Where half the absolute-return mass of the last `length` bars sits. ⚠
Overlaps the shipped TFCENTROID_20 at 0.8466 on synthetic frames. Near 1
the big moves are the RECENT ones, near 0 they are the old ones, 0.5 is
an even spread. (The first two sentences are short on purpose:
`docs/gen_indicator_dictionary.py` keeps only the first 150 characters of
this paragraph for `docs/IndicatorDictionary.md`, which CLAUDE.md sends a
reader to first, so the overlap has to fit inside them.)

    x          = the window's `length` simple returns
    TS_IMQ     = (argmax(cumsum(|x|) / sum(|x|) >= 0.5) + 1) / length

Source: tsfresh feature_calculators (MIT), `index_mass_quantile(q=0.5)`,
as PandasTa issue #99 applies it: "on 20 |returns|". The published
function is

    abs_x = np.abs(x); s = sum(abs_x)
    if s == 0: NaN
    else: (np.argmax(np.cumsum(abs_x) / s >= q) + 1) / len(x)

and this module is that expression with `x` the window's simple returns.
The issue hands it `|returns|` and the function takes its own absolute
value, so the two readings are the same column: measured bit-equal on
1,480 of 1,480 bars of each of three frames.
⚠ tsfresh is NOT installed in this worktree and web access is
unavailable, so what Gate A checks is the published definition quoted
above plus the issue's line, not a read of tsfresh's own source. The 20
and the `q = 0.5` are the issue's own parameters.

⚠ **It is a WHERE-IS-THE-VOLATILITY reading, and this fork already ships
one.** `TFCENTROID_20` (TSFEL's temporal centroid, issue #116, merged
2026-10-30) is the energy-weighted MEAN position of the same 20 returns
where this is the absolute-mass MEDIAN position. Measured Spearman on
nine 1,500-bar frames: +0.8527 on a walk, +0.8521 tick-rounded, +0.8669
/ +0.8738 on ar1+/ar1-, **+0.8857** heavy-tailed, +0.8545 right-skewed,
+0.8545 left-skewed, +0.8042 trending, **+0.7252** two-point. Pooled
over the nine (n = 13,320): **+0.846649**; per-frame |rho| median
0.8545, max 0.8857, **0 of 9 frames at or above 0.90**.
⚠ Those are SYNTHETIC. No real-frame figure exists for this pair: the
2026-10-24 screen's fork overlap (max |rho| 0.6127 vs `cvi:CVI_10_10`,
12 frames) was taken SIX DAYS before `tf_centroid_20` entered
`Category`, so it cannot bound it, and Gate E's 687 comparators are the
engine's and hold no pandas_ta port. See docs/TsImq20Measured.md §O.
On these frames the pair sits in DISCLOSE_GAP under `r3-perframe-0.90`,
not STRUCK. Against the fork's other 20-return statistics columns it is
near zero: per-frame |rho| at most 0.1034 (`TS_CID_CE_20`), 0.0919
(`TS_PEAKS_20`), 0.0627 (`TS_MEDSKEW_20`) and 0.0543
(`TS_ABOVE_MEAN_20`).

⚠ **It is a POSITION, not a size.** The statistic is invariant to
multiplying every |return| in the window by any positive constant -- the
ratio `cumsum / sum` cancels it -- so it cannot see volatility, only
where the volatility sat. Measured on a walk: Spearman **-0.0156**
against the same window's return standard deviation, -0.0486 against its
mean return, -0.0096 against the close itself; and the column is
BIT-IDENTICAL on all 1,480 fired bars at `r x 2`, `r x 0.5` and
`r x 1e-6`.
⚠ It is NOT invariant to a SHIFT of the returns: `r + 0.004` moves 639
of 1,480 bars (Spearman 0.8534), because a shift changes which bars
carry the mass.
⚠ What it CAN see is the recency of volatility, which is what the
screen's comparators measure: against `mean|r| over 5 / mean|r| over 20`
-- a local stand-in for the `ATR_Ratio_5_20` family the 2026-10-24
screen found at the top -- it reads +0.6121 on a walk, +0.5285
heavy-tailed and +0.5582 trending.

**It takes at most `length` values, and `0` is not one of them.** The
output is `k / length` for an integer `k` in `1 .. length`, so at the
default it is one of the 20 values 0.05, 0.10, ... 1.00. How many of
them a frame reaches depends on the frame, and the spread is wide: 20 of
20 on a heavy-tailed frame (the full [0.05, 1.00]), 12 on a walk (only
[0.25, 0.80]), 8 on a trending frame, and **2 on a two-point frame**,
where every |return| is the same size and the crossing can only be at
position 10 or 11. A tree sees an ordinal with at most 20 levels, not a
continuum.
⚠ The `+ 1` is the source's and it matters: without it the column is the
0-BASED position, whose floor is 0.0 -- and 0 reads as "no mass anywhere"
to every other consumer. Measured against that variant built from
scratch: the heavy-tailed frame reaches 0.0 on 6 bars where this column
reads 0.05, and the two differ by `1 / length` to within a rounding (the
shift spans [0.049999999999999933, 0.050000000000000044], so it is
0.05 to 1.1e-16 and not exactly 0.05). A rank miner cannot see the
difference (Spearman 1.000000); a threshold rule can.

It is a state rather than an event flag: neighbouring windows share 19
of their 20 returns, so the column autocorrelates at 0.8424 at lag 1 and
0.2759 at lag 5 on a walk -- and then goes NEGATIVE, -0.3465 at lag 10
and -0.0361 at lag 20. The lag-10 sign is structural rather than noise:
a cluster of big returns sitting late in window T (a high reading) has
slid to the OLD half of window T+10 (a low one). On independent windows
of iid returns the level to expect is 0.5264 (measured mean over 20,000
gaussian windows, sd 0.0849); for student-t(2) returns the mean is
0.5251 and the sd 0.1438, and for one-signed exponential returns 0.5246
/ 0.1088 -- the CENTRE barely moves with the law's shape, which is the
other side of it being a position, while the SPREAD nearly doubles with
the tails.

**This column IS the screen prototype, bit for bit.** Issue #99's
prototype (`docs/issues/screen/ind_screen.py`, candidate `ts_imq_20`) is
`roll(ret(c), 20, w_index_mass_quantile)`, tsfresh's expression over a
trailing 20-return window. Retyped in docs/measure_ts_imq_20.py (A1c)
and measured: identical NaN masks and 1,480 of 1,480 bars BIT-EQUAL on
each of nine 1,500-bar frames, and bit-equal again on the three frames
built to break it -- 0 and 0 fired bars on 300 identical closes, 280 and
280 on a 1%-a-bar ladder, 580 and 580 on a quiet 1e-6 frame.
⚠ The two part company only on the GUARDS this module adds, which the
screen has no need of: with a close of 0, 1e-310 or inf at bar 200 of a
400-bar walk the prototype reports 360 bars to this module's 359, with a
NEGATIVE close there 380 to 359, and with a 1e+307 return planted at bar
200 of a 2,000-bar frame 1,980 to 1,960. Every one of those extra bars
is a window built on a close a market cannot print.
Because Gate E's statistic is a Spearman over the bars where both fire,
the screen's figures (max |rho| 0.5254 vs `ATR_Ratio_5_20_Pctl`,
n = 391,818) are expected to carry over; the launcher's Gate E run on
THIS module is still the number that decides ship or revert.

The arithmetic is checked independently rather than trusted, and it is
EXACT rather than approximate. tsfresh's expression applied window by
window, sharing no code with this module, is bit-equal on 1,480 of 1,480
bars of each of nine frames with identical NaN masks; a `math.fsum`
scalar loop -- every partial sum correctly rounded -- on 1,480 of 1,480
bars of each of those nine; and an EXACT rational oracle, where every float
return is a rational so the partial sums, the total and the comparison
round not at all, on **13,320 of 13,320** bars across all nine. A CLOSED
FORM pins the degenerate end: closes that DOUBLE give a return of
exactly 1.0 on every bar, so the window's values are exactly equal and
the crossing is exactly at `length / 2` -- measured 0.5 at `length` 2,
4, 20 and 60.
⚠ The one thing float arithmetic could cost here is a TIE, not
precision: where the exact cumulative mass lands within a rounding of
half the total, the crossing can be reported one position early or late,
a difference of `1 / length`, which the floats realise as
0.050000000000000044. 200 windows built to straddle the threshold
produced **0** disagreements with the exact oracle, so this is an
argument from the arithmetic and not from a witness -- but the two-point
frame under a x10 rescale (below) IS the witness that the straddle is
reachable, which is why `tests/test_ts_imq_20.py` holds that frame to
one position of tolerance against every oracle whose summation order
differs from this module's, and asserts bit-equality only against the
one whose order is the same.

Causal: bar T reads closes T - length .. T, measured by a
future-perturbation sweep (0 of 37 offsets on each of three frames and
at `length` 5, 60 and 250) and by the five mutants in
`tests/test_ts_imq_20.py`, each caught at 35 to 37 of those 37 offsets.
Scale-free: every input is a price ratio, and `8a / 8b` is the same
double as `a / b`, so the column is bit-identical under a x8/x64
rescale of price -- 1,480 of 1,480 fired bars on each of nine frames at
BOTH factors, and 1,498 / 1,495 / 1,440 / 1,250 at `length`
2 / 5 / 60 / 250, again at both.
⚠ x10, x3.7 and x0.1 are NOT bit-identical by construction, and on one
frame of nine they are not bit-identical in fact. On eight of them --
walk, tick-rounded, ar1+, ar1-, heavy-tailed, right-skewed, left-skewed
and trending -- all three rescales are bit-equal on 1,480 of 1,480 bars.
On the TWO-POINT frame, where every |return| is the same size and every
window therefore sits on the tie above, 1,029 / 1,071 / 1,038 of 1,480
bars are bit-equal and the rest move by one position
(0.050000000000000044), the largest difference the statistic can make.
The NaN masks match exactly in all 27 cases.
NaN on the first `length` bars; on any window holding a close that is
NaN, infinite, zero, negative or subnormal (such a close spoils two
returns, so it empties the `length + 1` = 21 windows it sits in --
measured at bar 200 of a 400-bar frame, with 0 earlier bars moved in all
30 (bad value, position) pairs tried, and fewer windows near either end:
1 / 2 / 20 / 21 / 2 / 1 for a bad close at bar 0 / 1 / 19 / 200 / 398 /
399); on any window holding a return whose magnitude reaches
`max / (2 * length)`, i.e. |r| >= 4.494e+306; and on any window whose
returns are ALL EXACTLY ZERO, which 21 identical closes are the only way
to reach.
⚠ **There is NO dispersion floor here, and that is a decision.** Its
siblings `statistics/ts_medskew_20.py` and
`statistics/ts_above_mean_20.py` refuse a window whose returns span 4096
ulps or less, because both read a centre estimate whose own rounding the
statistic then amplifies. This one reads an ORDER of cumulative sums and
divides by the window's own total mass, so the worst a degenerate window
can cost is ONE position. Measured on a 1%-a-bar geometric ladder, where
the return is mathematically constant and float64 reproduces it only to
rounding: this column reports 280 of 280 windows as 0.50 (178) or 0.55
(102) -- the two positions adjacent to the exact answer -- while the
same frame makes the unfloored `ts_medskew_20` statistic report 280
windows spanning [-0.3300, +0.3033], two thirds of its whole range,
which is why that module floors. The jitter is in the DATA, not here: a
DOUBLING ladder, whose returns are exactly 1.0 with no rounding at all,
reads 0.5 on all 281 windows. Adding the siblings' floor would empty
those 280 honest windows and 0 dishonest ones. On a quiet-but-honest
frame (returns 1e-6) the column fires on 580 of 600 bars over 10
distinct values and is bit-equal to the exact oracle on all 580.

**And it stays LOCAL, which a global cumulative sum would not.** Every
window is accumulated from its own `length` values, so nothing is
carried across windows. Measured on a 2,000-bar frame priced at 1e-198
with one return planted at bar 200: at x1e+02, x1e+06, x1e+08, x1e+100
and x1e+300 the 20 windows holding it all fire, and every one of the
1,780 bars from 220 on is BIT-IDENTICAL to the unspiked frame. At
x1e+307, above the per-return bound, the module empties those 20 windows
and the 1,780 later bars are bit-identical too. The O(n) spelling this
module does not use -- one global `np.cumsum` differenced per window --
survives x1e+02 and x1e+08 and then fails completely at x1e+100: the two
partial sums cancel to exactly zero, the window reads no mass, and all
1,780 later bars come back NaN -- bars on which this module spans
[0.25, 0.80] over 12 distinct values.

Cost: one reduction and one scan over a `sliding_window_view`, both
`length` passes over `(rows,)` arrays, with no allocation that grows
with `length` -- the traced peak is 30.0 MB on 400,000 bars at each of
`length` 2, 20, 60 and 250. The window-by-window oracle this was checked
against is slow enough to live in docs/measure_ts_imq_20.py rather than
here. ⚠ No wall-clock figure is quoted in this docstring on purpose:
they move between runs and between machines, and keeping one copy of
them (docs/TsImq20Measured.md, Z) is what stops the two drifting apart.
The PEAK is the claim.

Calculation:
    Default Inputs:
        length=20
    r[t]        = close[t] / close[t-1] - 1
    m[k]        = cumsum(|r|)[k] / sum(|r|) over the trailing `length`
                  returns, oldest first
    TS_IMQ[T]   = (first k with m[k] >= 0.5, counting from 1) / length,
                  NaN where those returns are all exactly zero

Args:
    close (pd.Series): Series of 'close's
    length (int): Returns per window. At least 2 -- a window of one
        return is identically 1.0 -- so a smaller or missing value falls
        back to the default. Default: 20
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)

Returns:
    pd.Series: TS_IMQ_{length}, dimensionless, one of the `length`
        values 1/length .. 1
"""
