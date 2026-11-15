# -*- coding: utf-8 -*-
import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from pandas import Series

from pandas_ta.utils import get_offset, verify_series

#: Two closes are the fewest that can repeat at all. At `length` 1 the single
#: datapoint in a window has nothing to reoccur with, so the column would be
#: identically 0.0 rather than a share, and `np.sort`'s adjacent comparison
#: would run over an empty axis.
MIN_LENGTH = 2
#: Doubles to hold in the sorted copy at once. The sort HAS to materialise a
#: copy -- the statistic reads the window's multiset, so there is nothing a
#: window can inherit from its neighbour -- and this budget is what keeps
#: that copy off both `len(close)` AND `length`: the rows per chunk are
#: `CHUNK_VALUES // length`, so the peak is ~16 MB of window either way. It
#: cannot change a value, because every chunk is an independent run of rows:
#: `tests/test_ts_reoccur_20.py::test_the_chunk_budget_cannot_change_a_value`
#: runs the default against budgets of 1, 20, 999 and 10**9.
CHUNK_VALUES = 1 << 21


def _reoccurring(window):
    """How many of a window's datapoints occur in it more than once.

    One row per window, `length` columns, oldest close first. Sorting the
    row puts every run of equal closes together, so a datapoint reoccurs
    exactly when it equals its left or its right neighbour in the sorted
    row -- which is `value_counts()[value_counts() > 1].sum()` reached
    without building a counter per window. This is the screen prototype's
    own spelling (`docs/issues/screen/ind_screen.py`,
    `w_pct_reoccurring`), and `docs/TsReoccur20Measured.md` A1/A2 measures
    it bit-equal to both that and a per-window `value_counts()` oracle.

    ⚠ Equality here is EXACT float equality, with no tick grid and no
    tolerance. That is the source's own test and it is the whole feature:
    on a continuous-float frame nothing ever repeats and the column is
    identically 0.0 (measured, A5). What makes it informative is that real
    prices live on a tick grid.

    A row holding a NaN is counted and then DISCARDED by the caller's mask,
    so where `np.sort` puts a NaN -- numpy documents the end -- cannot
    reach the output.
    """
    s = np.sort(window, axis=1)
    eq = s[:, 1:] == s[:, :-1]
    dup = np.zeros(s.shape, dtype=bool)
    dup[:, 1:] |= eq
    dup[:, :-1] |= eq
    return dup.sum(axis=1)


def ts_reoccur_20(close, length=None, offset=None, **kwargs):
    """Indicator: share of a window's closes that repeat in it
    (TS_REOCCUR)"""
    # Validate Arguments
    length = int(length) if length and int(length) >= MIN_LENGTH else 20
    close = verify_series(close, length)
    offset = get_offset(offset)

    if close is None: return

    # Calculate Result
    c = close.to_numpy(dtype=float)
    # A close that is not a finite, normal, positive float (NaN, inf, zero,
    # negative, or subnormal such as 1e-310) is bad data: it is a missing
    # price rather than a price that happens to repeat.
    c = np.where(np.isfinite(c) & (c >= np.finfo(float).tiny), c, np.nan)

    rows = c.size - length + 1
    counts = np.empty(rows, dtype=np.int64)
    w = sliding_window_view(c, length)
    step = max(1, CHUNK_VALUES // length)
    for a in range(0, rows, step):
        b = min(a + step, rows)
        counts[a:b] = _reoccurring(w[a:b])

    # Whether a window holds a bad close, from a prefix sum over the 1-D
    # mask rather than a second pass over the windows: window `i` covers
    # `c[i : i + length]`, so its bad count is `nbad[i + length] - nbad[i]`.
    nbad = np.concatenate(([0], np.cumsum(np.isnan(c))))
    holds_bad = (nbad[length:] - nbad[:rows]) > 0

    # The share. Both sides are exact integers, so this is the correctly
    # rounded value of `count / length` and it is the module's ONLY float
    # arithmetic -- which is why Gate A is bit-equality rather than a
    # tolerance.
    val = np.where(holds_bad, np.nan, counts / float(length))

    out = np.full(c.size, np.nan)
    out[length - 1:] = val
    share = Series(out, index=close.index)

    # Offset
    if offset != 0:
        share = share.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        share.fillna(kwargs["fillna"], inplace=True)

    # Name and Categorize it
    share.name = f"TS_REOCCUR_{length}"
    share.category = "statistics"

    return share


ts_reoccur_20.__doc__ = \
"""Share of a window's closes that repeat in it (TS_REOCCUR)

Share of the last `length` closes that repeat inside the window. ⚠ EXACT
price equality: a tick-grid feature, identically 0.0 on continuous
prices. (Those two sentences are 147 characters, and they have to
survive the cut `docs/gen_indicator_dictionary.py` makes for
`docs/IndicatorDictionary.md`, which CLAUDE.md sends a reader to first.
That cut is NOT 150 characters: it is `d[:150].rsplit(" ", 1)[0]`, which
drops the trailing word whole, so the usable length is 149 and the slack
is TWO -- measured by `python docs/measure_ts_reoccur_20.py W`, which
calls the generator's own `desc()` and grows this sentence until it
breaks. Re-run it, and then the generator, before lengthening them.)

    x           = the window's `length` closes
    TS_REOCCUR  = #{ i : x[i] == x[j] for some j != i } / length

Source: tsfresh feature_calculators (MIT),
`percentage_of_reoccurring_datapoints_to_all_datapoints`, as PandasTa
issue #103 applies it: "on 20 closes". The quantity the name states is
"# of data points occurring more than once / # of all data points",
which is `value_counts()[value_counts() > 1].sum() / len(x)` -- the
share of the window's BARS whose close has a twin, not the share of its
distinct VALUES that are repeated (that is the sibling function
`percentage_of_reoccurring_values_to_all_values`, a different column --
1 to 1,346 of 1,481 bars equal per frame -- though a nearly
rank-identical one, |rho| 0.9726 .. 1.0000 over seven tick-grid
frames).
⚠ tsfresh is NOT installed in this worktree and web access is
unavailable, so Gate A does not read tsfresh's own source. What it
checks is that quantity, spelled two independent ways -- a per-window
`pandas.Series.value_counts()` counter and the screen prototype's
sort-and-compare -- against the module, bit for bit. The function name
and the 20 are the issue's own. Nothing here is evidence about
tsfresh's handling of an edge the issue does not name.

**Gate A is exact, not a tolerance.** The only arithmetic is one
integer count divided by `length`, so the module, a per-window
`value_counts()` oracle and the screen prototype
(`docs/issues/screen/ind_screen.py`, candidate `ts_reoccur_20`:
`roll(c, 20, w_pct_reoccurring)`) agree on 11,848 of 11,848 fired bars
over eight frames, and at `length` 2, 3, 5, 21, 60 and 250 -- bit for
bit, masks included, on frames with no bad close. The output lives on
the lattice `k / length`, and `k = 1` is UNREACHABLE: a value with a
twin contributes at least two bars. Measured at `length` 2, 3, 20 and
60 over all eight frames, `k = 1` occurs nowhere, and the reachable set
at `length` 20 is 0.0 and 0.10 .. 1.00.

**⚠ It is volatility measured in TICKS, and that is the one thing to
know before using it.** A repeat needs two closes to land on the same
grid point, so the column reads how far the price moves per bar
relative to the tick -- downward. On a 0.01 grid at price 100 the mean
share runs 0.9124 at a 1-tick daily move, 0.6519 at 3 ticks, 0.2937 at
10 ticks and 0.0379 at 100 ticks (20,000 bars per step, measured, and
strictly decreasing). Against the window's own `stdev(close, 20)` the
per-frame |rho| median is 0.7974 (0.6963 .. 0.8533) over seven frames
of ONE tick regime, which is the nearest thing to it; against
`stdev(returns, 20)` only 0.0428 .. 0.3210, because a share cancels the
window's overall size and what is left is the move against the GRID.
Against `LOT_ZERORET_20`, the share of ZERO RETURNS over the same 20
BARS -- 21 closes, so NOT the same window; the window-identical
comparison is `LOT_ZERORET` at length 19 -- the per-frame median is
0.5185. Adjacent repeats are much of what this counts but not all: at
length 19 the count provably covers every zero return (a run of k of
them is k+1 equal closes) and on one frame 574 of the 1,218 bars with
no zero return at all still fire, the price having come BACK to a level
it left.
⚠ All of those are SYNTHETIC, and a POOLED synthetic figure here reads
the frame mix rather than the column: pooling seven frames of different
tick regimes takes the `LOT_ZERORET_60` pair from 0.7037 to 0.8427 and
the `stdev(close, 20)` pair from 0.8862 down to 0.4746. On the 89 real
BIST frames the 2026-10-24 screen measured the prototype's top
comparator at |rho| 0.7222 (`stdev`, n = 397,158, top-5 per-frame max
median 0.7700) and bounded its whole fork sweep at 0.4851 -- a sweep
whose comparator pool holds `lot_zeroret_60` if that column cleared its
scale-free and non-constant filters, which is not recorded. Gate E on
this module is what decides the band.
⚠ The tick grid is NOT part of the column, so two instruments whose
tick is a different FRACTION of their price are not comparable on it:
the same return path quantised at price 5 and at price 500 on a 0.01
grid reads mean 0.2254 and 0.0037. Rescaling a frame rescales its grid
with it, which is why Gate D passes; a cross-sectional comparison does
not.
⚠ In a coarse regime it is nearly a BINARY flag: at 200 ticks a bar it
reads 0.00 on 90.9% of bars and 0.10 on 8.8%, over 3 distinct values.
⚠ `docs/IndicatorDictionary.md` therefore tags this column **CONST** and
lists it under "Never fires on the probe", next to `lot_zeroret_60`:
that probe is one continuous-float frame, so the tag is a FIXTURE
artifact in the same sense as `cdl_pattern`'s. The screen's Gate E on
the prototype returned a finite Spearman over n = 397,158 real BIST
bars, which a constant column cannot do; the pooled real-data counts
are owed with the Gate E run.

**It is blind to the ORDER of the window's closes**, because it reads
their multiset: every one of 2,000 random permutations of a window
leaves the value bit-identical, and a REVERSED frame gives the column
reversed, bit for bit on 1,481 of 1,481 bars of each of seven frames.
So it cannot see trend, sign or where in the window a repeat sat --
only how many bars had a twin.

Causal: bar T reads closes T - length + 1 .. T, measured by a
future-perturbation sweep (0 of 36 offsets on each of four frames and
at `length` 2, 7, 60 and 250) and by the six mutants in
`tests/test_ts_reoccur_20.py`. Each of the five live ones IS this
column back-dated by a DERIVED number of bars, bit for bit on every
bar the mutation's wrap leaves alone (1,462 .. 1,480 per frame).
⚠ The blind sweep catches those five at only 1 .. 36 of 36 offsets, and
that is a fact about the COLUMN: it lives on a 21-point lattice, so a
one-bar shift often lands on the value it replaced, and the catch rate
tracks how often the column changes at all (churn 0.6466 on the finest
frame against 0.1128 on the sparsest). The derived displacement, not
the sweep, is what carries Gate B here. The sixth mutant shifts the
bad-close mask's own index: it is not even live on a clean frame, so
the sweep catches it 0 of 36 times, and on a frame with a bad close at
each of 12 offsets it is caught 12 of 12, moving exactly bar J-1.
Scale-free: a share of a count, and every comparison is an equality, so
a x2^k rescale of price is EXACT and cannot merge or split a tie --
bit-identical under x8/x64 on 11,848 of 11,848 fired bars over eight
frames, at `length` 2 / 3 / 5 / 21 / 60 / 250 and at price levels
1e-6, 1e+6 and 1e+100.
⚠ x10, x3.7, x0.1 and x1.0000001 are not exact and could in principle
MERGE two closes that differ in their last bits (they can never split a
tie, since equal doubles scale to the same double). Measured, as two
separate things because bit-equality does not imply the second:
bit-identical on all 11,848 bars at all four factors, and 0 merges in
all 32 frame-and-factor cells. A frame built
to force one -- 20 consecutive doubles from 1.9 -- does merge under x10
(13 of 20 distinct, the column 0.00 -> 0.70) and does not from 1.0, so
this is a measurement and not a theorem.
⚠ `price ** 2` and `price ** 0.5` are not rescales. They are monotone
and so preserve every tie exactly in exact arithmetic, but they round:
measured bit-identical on 10,367 of 10,367 bars of the seven grid
frames anyway, with 0 merges.

NaN on the first `length - 1` bars; and on any window holding a close
that is NaN, infinite, zero, negative or subnormal -- such a close
empties the (at most `length` = 20) windows it sits in and nothing
earlier: measured over 36 (bad value, position) pairs, 1 / 2 / 19 / 20
/ 2 / 1 windows emptied at bar 0 / 1 / 18 / 200 / 398 / 399 of a
400-bar frame -- fewer near either end -- with 0 earlier bars moved in
any of the 36.
⚠ There is NO undefined case beyond that, and no dispersion floor. A
window with no repeat reads exactly 0.0 and a window of `length`
identical closes reads exactly 1.0; both are readings, not missing
data. The source's own `len(x) == 0` NaN is unreachable here, because
`verify_series` refuses an input shorter than `length`.
⚠ The source, the prototype and this module part company on ONE rule,
and it is this fork's: a window holding a bad close is NaN here, where
`value_counts()` drops the NaN and keeps `len(x) = length` in the
denominator, which silently reports a DEFLATED share -- and a bad close
that is not NaN (0.0, a negative, an infinity, a subnormal) it treats as
a perfectly good price that happens to be unique. Measured: with one bad
close planted at bar 200 of a 400-bar frame, this module fires on 361
bars and the source-literal reading on 381, for each of five bad
values, and the 20 bars they disagree on read 0.50 .. 0.80 there.

Cost: one sort per window and nothing carried between them -- the
statistic reads a multiset, so a window inherits nothing from its
neighbour -- which is why the time grows faster than `length`: at
`length` 250 the best of 3 runs costs ABOUT 20x `length` 2, monotone in
`length`. Not two significant figures: five invocations of that section
on 100,000 bars on one worktree printed fifteen ratios spanning 20.58 ..
21.52, and a 20..21 bracket written after the first three failed on the
fourth (docs/TsReoccur20Measured.md §Z). The memory does
not grow with `length`, because the sorted copy is taken
`CHUNK_VALUES // length` rows at a time: traced peak 17.3 MB at
`length` 2 and 27.6 .. 28.2 MB at `length` 20, 60 and 250, on 400,000
bars.
⚠ No wall-clock figure is quoted outside `docs/TsReoccur20Measured.md`
§Z, and there only as a best-of-3: they move between runs and between
machines. The peak, the ordering and the ratio are the claims.

Calculation:
    Default Inputs:
        length=20
    x            = close[T - length + 1 .. T]
    TS_REOCCUR[T] = (number of i with x[i] == x[j] for some j != i)
                    / length

Args:
    close (pd.Series): Series of 'close's
    length (int): Closes per window. At least 2 -- one datapoint has
        nothing to repeat with -- so a smaller or missing value falls
        back to the default. Default: 20
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)

Returns:
    pd.Series: TS_REOCCUR_{length}, dimensionless, on the lattice
        {0, 2/length, 3/length, ..., 1}
"""
