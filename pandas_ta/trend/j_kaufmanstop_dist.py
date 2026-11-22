# -*- coding: utf-8 -*-
import numpy as np

from pandas_ta.overlap.sma import sma
from pandas_ta.utils import get_offset, verify_series

#: Kaufman's stop's two numbers, as PandasTa issue #124 states them:
#: "long (22, mult 2)". They are module constants rather than arguments, for
#: the same reason as `pandas_ta/trend/j_chandelier_dist.py`'s and
#: `pandas_ta/trend/j_safezone_dist.py`'s: the issue's quote
#: (`kaufmanstop.py: L - 2*SMA22(H - L)`) and the screen prototype
#: (`docs/issues/screen/ind_screen_r2.py`, candidate `j_kaufmanstop_dist`)
#: spell exactly these two, and that one pair is the whole of what the
#: 2026-10-24 screen measured at Gate E. A `period=`/`mult=` surface would
#: ship parameter combinations nothing has measured, and the Gate E ledger
#: refuses a run taken at non-default parameters anyway
#: (`docs/gate_e_ledger.py`).
PERIOD = 22
MULT = 2.0

#: Bars a frame must have before the function computes at all, and
#: `MIN_BARS - 1` is also the index of the first bar that can fire on a
#: clean frame. ⚠ It is PERIOD and not PERIOD + 1, which is where this
#: module's warm-up departs from `j_chandelier_dist`'s: the only window in
#: this chain is the SMA, and its input `high - low` is defined at bar 0 --
#: no previous close is read anywhere, so nothing costs the extra bar a
#: true range costs. Pinned by `tests/test_j_kaufmanstop_dist.py::
#: test_a_frame_shorter_than_min_bars_is_refused`.
MIN_BARS = PERIOD


def j_kaufmanstop_dist(high, low, close, offset=None, **kwargs):
    """Indicator: distance to Kaufman's stop, long (J_KAUFMANSTOP_DIST)"""
    # Validate Arguments
    high = verify_series(high, MIN_BARS)
    low = verify_series(low, MIN_BARS)
    close = verify_series(close, MIN_BARS)
    offset = get_offset(offset)

    if high is None or low is None or close is None: return

    # Calculate Result
    # The three inputs are sanitised before any arithmetic, and the close is
    # guarded TWICE because it does two different jobs.
    #
    # `high` and `low` only have to be FINITE. They enter through a
    # difference, a mean and a subtraction, all meaningful at any finite
    # level.
    # ⚠ **The three input finite guards are measured NO-OPS here, and this
    # comment says so rather than claiming a load they do not carry.** §G2
    # plants `+inf`, `-inf` and NaN in each leg in turn, at bar 700 of a
    # `walk`, and with each guard removed in turn the column is BIT-EQUAL
    # and the fired count identical in all nine cells. What absorbs a bad
    # high or low is pandas' rolling window -- an infinite observation makes
    # the window NaN rather than propagating, pinned on its own in §G3 so an
    # upgrade that stops doing it fails there -- and what absorbs a bad
    # close is the final finite mask below.
    # ⚠ And the tempting justification for keeping them -- "pandas might
    # stop absorbing one day" -- was RUN and does not hold: §G5 rebinds
    # `sma` to a mean that PROPAGATES an infinity -- a numpy window mean,
    # because the three `rolling` aggregations §G5 measures (`sma`,
    # `apply(np.mean, raw=True)` and `rolling(...).max()`) all read NaN at
    # a planted `+inf` while the numpy mean reads `inf`, which places the
    # conversion BEFORE the window function rather than in the mean -- and
    # the three guards are still bit-equal no-ops in all six cells, because
    # the final mask converts the propagated infinity at exactly the bars
    # the guard blanks. So what keeps these three lines is
    # defence in depth and the shape the two sibling ports already have,
    # not a measured load; §G3's route 1 also shows this chain producing an
    # infinity from two FINITE legs, which no input guard would catch
    # either way. The honest reading, which the receipt states: removing
    # them would not change any of the 42 guard-off cells measured --
    # §G1's 27 (three guards x nine clean frames), §G2's 9 and §G5's 6.
    # §G4's other four plant points were not re-run with a guard removed.
    # ⚠ That is the opposite finding from `j_chandelier_dist`, where the
    # same three guards moved 634 .. 664 bars: there the bad leg was one of
    # three competing in a `max(axis=1)`, which SKIPS a NaN, so the guard
    # changed which leg won.
    #
    # The close is used ONLY as the divisor, and it is guarded TWICE
    # because `>= tiny` does not subsume `isfinite`: a NaN fails the
    # comparison, but `+inf >= tiny` is TRUE, so without the finite line a
    # `+inf` close would reach the division.
    # ⚠ The positivity guard is the ONE guard on the inputs that §G2
    # measures doing work: with it removed, a close of -50 at bar 700 FIRES
    # and reads 1.924 -- a sign-flipped number among a column whose every
    # other bar is 0.006 .. 0.014 -- instead of blanking. A zero or
    # subnormal close makes the ratio overflow. Same guards, same reasons,
    # as the siblings that divide by a price
    # (`trend/j_chandelier_dist.py`, `trend/j_safezone_dist.py`,
    # `statistics/tf_iqr_ret_60.py`, `statistics/ts_q05_60.py`).
    hi = high.astype(float)
    hi = hi.where(np.isfinite(hi))
    lo = low.astype(float)
    lo = lo.where(np.isfinite(lo))
    cl = close.astype(float)
    cl = cl.where(np.isfinite(cl))
    px = cl.where(cl >= np.finfo(float).tiny)

    # Kaufman's stop for a LONG position, as issue #124 quotes it:
    # "kaufmanstop.py: L - 2*SMA22(H - L)".
    #
    # ⚠ `H - L` is a plain subtraction and NOT this fork's
    # `utils.non_zero_range`, whose epsilon is ABSOLUTE: it adds
    # `sys.float_info.epsilon` to EVERY bar of the series as soon as ONE bar
    # has `high == low`, so a variant built on it stops scaling with the
    # price. ⚠ §A4(c) measures BOTH halves of that: the variant is
    # bit-equal to this module on all nine test frames at a price level of
    # 100, INCLUDING the one with 215 tied bars and the flat one with 1,500,
    # so the plain subtraction buys nothing there; at a level of 1e-6 the
    # variant fails Gate D's x8 and x64 cells on the tied frame and this
    # module holds. A doji is a legitimate zero-range bar here -- nothing
    # divides by the range -- so there is no reason to perturb it.
    rng = hi - lo

    # "SMA22": the fork's own simple moving average, imported from its own
    # module rather than the package (CLAUDE.md, "Known breaks"), which is
    # `rolling(22, min_periods=22).mean()`. ⚠ `min_periods == length` is
    # load-bearing and is `sma`'s own default rather than this module's
    # choice: one NaN range blanks PERIOD bars of output instead of being
    # skipped. §A4(a) measures `sma` BIT-EQUAL to an inline
    # `rolling(PERIOD, min_periods=PERIOD).mean()` on every frame, so the
    # import buys the helper's spelling and costs nothing.
    avg = sma(rng, length=PERIOD)

    # ⚠ Both legs read bar T: Kaufman's stop sits below bar T's OWN low, not
    # below yesterday's. That is the source formula (`L - 2*SMA22(H - L)`,
    # with no lag on `L`) and it is not a look-ahead -- a trader standing at
    # T has T's high, low and close. Nothing here reads T + 1;
    # `tests/test_j_kaufmanstop_dist.py` carries a 36-offset future sweep
    # and six mutants to say so.
    stop = lo - MULT * avg

    # The scale-free form the issue specifies: `(close - stop) / close`.
    # Not the stop level, which is a price and so not a feature (CLAUDE.md,
    # "Scale-free").
    # ⚠ Unlike the Chandelier and SafeZone distances, this one does NOT
    # change sign in normal markets: the stop sits below bar T's own low by
    # twice a non-negative average range, so on well-formed OHLC
    # (`close >= low`) the column is `(close - low)/close + 2*avg/close`,
    # a sum of two non-negative terms. §C1 measures the pooled range and
    # §C2 the one frame that reads exactly 0.0.
    dist = (px - stop) / px
    # ⚠ Defence in depth, and §G3 measures that it is NOT a no-op. Finite
    # inputs leave THREE arithmetic routes to an infinity, numbered there in
    # the order they occur in the chain:
    # (1) overflow in `high - low`, which needs a high near +DBL_MAX against
    # a low near -DBL_MAX -- legal here, because the finite guards do not
    # demand an ordered bar;
    # (2) overflow in `lo - MULT * avg`, twice an average range near
    # DBL_MAX;
    # (3) overflow in THIS division, a stop near -1e300 over a close near
    # 1e-300.
    # Which of the three reach the output is measured in §G3 and pinned
    # test by test, not reasoned about: `j_safezone_dist` found pandas'
    # compensated `rolling.sum` absorbing two of its three.
    dist = dist.where(np.isfinite(dist))

    # Offset
    if offset != 0:
        dist = dist.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        dist.fillna(kwargs["fillna"], inplace=True)

    # Name and Categorize it
    dist.name = f"J_KAUFMANSTOP_DIST_{PERIOD}_{MULT}"
    dist.category = "trend"

    return dist


j_kaufmanstop_dist.__doc__ = \
"""Distance to Kaufman's stop, long (J_KAUFMANSTOP_DIST)

How far the close stands above Kaufman's long stop, as a fraction of the
close. The stop sits twice the 22-bar average range below the bar's low.

    rng[T]  = high[T] - low[T]
    avg[T]  = mean(rng[T-21..T])                                  SMA 22
    stop[T] = low[T] - 2 * avg[T]
    J_KAUFMANSTOP_DIST[T] = (close[T] - stop[T]) / close[T]

Source: jesse indicators (MIT), `kaufmanstop.py`, as PandasTa issue #124
quotes it: "kaufmanstop.py: L - 2*SMA22(H - L)". Issue #124 names the rule
Kaufman's stop; that attribution is the issue's and is not checked here.
⚠ jesse is not installed in this worktree and web access is unavailable, so
Gate A does not read its source
(`tests/test_j_kaufmanstop_dist.py::test_the_source_library_is_not_
installed_here` records that, so the claim cannot rot into "checked against
jesse"). What Gate A checks is the formula issue #124 quotes, spelled three
independent ways, and the attribution is to the issue's QUOTE rather than to
jesse's code. The issue itself says of the library: "existence, not
evidence".
⚠ **Nothing below is a statement about what jesse's code says.** Whether its
`SMA22` is taken over `H - L` bar by bar, or over something else, and
whether `L` is lagged, is not checkable here, so neither is claimed. The
reading taken is the issue's quote read literally, and the screen prototype
spells the same one.
⚠ The LONG stop only: issue #124 names the long side and the screen measured
only the long candidate, so no short-side column has a Gate E figure.
Whether jesse's function also takes a short direction is not checkable here
and is not claimed.

**Gate A is the issue's formula, spelled independently, and TA-Lib is the
third speller.** A bar-by-bar oracle -- its own range loop, its own naive
22-term window sum over plain Python floats, sharing no code with the
module -- is BIT-EQUAL to this module on 1,479 of 1,479 fired bars of each
of six varying frames, with identical NaN masks (§A1, which also measures
pandas' compensated `rolling.mean()` bit-equal to that naive sum on the
`walk` frame rather than assuming the two agree). ⚠ The test asserts 1e-12
absolute and 1e-9 relative rather than the bit-equality, because the frames
are built with `np.exp`/`np.cumsum` and a reduced numpy kernel can move a
price in its last bits; the measured figure under both dispatches is 0.0.
`(close - (low - 2 * talib.SMA(high - low, 22))) / close` -- the quote's
operators as TA-Lib spells them -- is bit-equal on all six frames at
Spearman 1.0000 and first fires at the same bar 21 (talib 0.7.1); the test
skips rather than passing silently where talib is absent.

⚠ **THE SCREEN PROTOTYPE IS THIS COLUMN'S ARITHMETIC, BIT FOR BIT**, and
that is measured (§A3) rather than assumed from a quote that reads the same:
`(c - (l - 2 * mean(h - l, 22))) / c` with `ind_screen.py`'s
`mean(x, n) = x.rolling(n).mean()` is bit-equal to this module on all nine
test frames. This is the opposite of `j_chandelier_dist`, where the
prototype's unseeded ATR made the screen's figures describe a neighbouring
column. So the screen's DISCLOSE_GAP figures below are about THIS
arithmetic -- on 89 real frames this worktree cannot read, through an engine
whose guards are not these. The port's own Gate E run is still what decides
its band.

Causal: bar T reads `high`, `low` and `close` at T and the 21 bars before
it. Nothing later, and nothing before `T - 21` -- measured as well as
stated: truncating a 1,500-bar frame at bar 500 leaves all 979 bars from
521 on bit-equal (§A5). The forward direction is a 36-offset
future-perturbation sweep (0 of 36 on each of six frames) and six
look-ahead mutants read off this file, edited and `exec`'d in memory, each
live and caught on all 36 of those offsets of each of three frames, the
first catch moving a bar by 1.379e-05 .. 3.023e-02.
⚠ **And the sweep has a blind spot this module states rather than leaves for
a reader to find.** An edit that LAGS a leg -- `low.shift(1)`, the average
by a bar, or the high inside the range -- is wrong without reading any later
bar, so the sweep catches 0 of 36 of all three such edits; Gate A's oracle
rejects all three, by 6.152e-04 .. 3.224e-01. That is why Gate B here is the
sweep AND the oracle.

Scale-free by construction: every step up to `stop` is homogeneous of
degree 1 in the price, and the final division cancels the factor, so a
x8/x64 rescale is bit-identical on 1,479 of 1,479 bars of each of all nine
test frames, and on each of those nine at price levels 1e-6, 1e+6 and
1e+100 as well -- 54 cells, measured rather than extrapolated from one
frame. The largest value the chain computes at 1e100 -- over the three
inputs, `rng`, `avg`, `2*avg`, `stop`, `px`, `px - stop` and `dist`, all
ten -- is 9.776e+101 over all nine frames, leaving 1.839e+206 of DBL_MAX
headroom (§D3).
x10/x3.7/x0.1/x1.0000001 round: the
measured worst of 24 cells is 5.160e-14 and the test asserts 1e-9 rather
than the digits, because that figure moves between numpy CPU dispatches. A
level SHIFT of +10 moves all 1,479 fired bars of every one of the six
varying frames, so the bit-identity is a real check and not a vacuous one.
⚠ The shift moves 0 bars of the FLAT frame, where the column is exactly 0.0
either way, so that limb is asserted on the varying frames (§D4).

⚠ **Bounded BELOW by zero on well-formed OHLC, and it does not change
sign.** `(close - stop)/close = (close - low)/close + 2*avg/close`, a sum of
two non-negative terms when `close >= low` (which this module does not
enforce), so unlike the Chandelier and SafeZone distances there is no
sign to read: the signal is the SIZE. Measured over the 8,874 fired bars of
the six varying frames: 0.005961 .. 0.014415, positive on all 8,874 and
exactly 0.0 on none, with 1,479 of 1,479 distinct values per frame (§C1).
⚠ A flat frame reads exactly 0.0 on all 1,479 of its fired bars, so this
column is CONSTANT there rather than blank (§C2) -- the range is 0, so the
stop IS the low and the low is the close.
⚠ **A bad price empties a BOUNDED window and moves nothing after it.** One
NaN, +inf or -inf high or low blanks exactly bars
`max(T, 21) .. min(T+21, n-1)` -- measured 22 bars at plant points 100, 700
and 1,100 of a 1,500-bar frame, 5 at 1,495 where the frame runs out, and 6
at bar 5, where the first 16 of the window's bars had never fired -- and
leaves every one of the remaining bars bit-identical; a bad close blanks
exactly its own bar, or none at all inside the warm-up (§G4, 15 cells per
leg: five plant points x three values). There is no recursion in this
chain, which is what makes that true here and false in
`j_chandelier_dist`.

⚠ **Gate E on the PROTOTYPE was DISCLOSE_GAP** -- max |rho| 0.8776 vs the
engine's `natr` over 89 BIST frames (n = 396,980), top-five per-frame max
median 0.8601, inside the 0.80 .. 0.90 band. The next comparators were
`Stop_2ATR_pct` 0.8776 and `Swing_Range_pct` 0.7305. Because §A3 measures
the prototype bit-equal to this module, those figures are this arithmetic's
rather than a neighbour's -- but they were taken on data and through an
engine this worktree cannot read, and the port's own Gate E run is what
decides its band. It is PENDING: the launcher runs it after this session
(§E of `docs/JKaufmanstopDistMeasured.md`).
⚠ **The in-fork overlap this session CAN measure is LOW, and that is a
warning about the measurement rather than about the column.** Over the six
varying frames the nearest neighbour is a retyped `lean_avgrange_14`
(`SMA(high - low, 14)/close`) at a per-frame median |rho| of 0.5506, then
`j_chandelier_dist` at 0.1436, a retyped `Stop_2ATR_pct` at 0.1366, a
retyped `true_range/close` at 0.1096 and `natr`'s `NATR_14` at 0.1092 --
five of §L's seven rows, in order. ⚠ `natr` is the one comparator with both
a synthetic and a real figure, and the synthetic number is 0.75 BELOW the
screen's 0.8611 -- the reverse of `j_chandelier_dist`, where synthetic read
0.0575 high. What §L measures about why is on the synthetic side only: the
column is a wick term plus a range term, and on these frames the wick term
carries more of it (|rho| 0.857 .. 0.884 against 0.574 .. 0.620 over the
six; 0.920 against 0.572 on the `tied` frame §L adds to them), because
`_ohlc` draws the relative range i.i.d. per bar so its 22-bar mean is
smoother than real volatility. So §L is a disclosure that cannot stand in
for Gate E in EITHER direction -- not a gate, and not a floor.

Cost: one subtraction, one `rolling` mean, one multiply-subtract and one
division. Linear in bars. ⚠ The wall-clock figures live in
`docs/JKaufmanstopDistMeasured.md` §Z and nowhere else, including here:
they are one machine's and one run's.

Calculation:
    Default Inputs:
        period=22, mult=2.0  -- module constants
    rng     = high - low
    avg     = sma(rng, 22)
    stop    = low - 2.0 * avg
    J_KAUFMANSTOP_DIST = (close - stop) / close

Args:
    high (pd.Series): Series of 'high's
    low (pd.Series): Series of 'low's
    close (pd.Series): Series of 'close's
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)

Returns:
    pd.Series: J_KAUFMANSTOP_DIST_22_2.0, a fraction of the close
"""
