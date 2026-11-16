# -*- coding: utf-8 -*-
import numpy as np
from pandas import Series

from pandas_ta.utils import get_offset, verify_series

#: Elder's three numbers, as PandasTa issue #121 states them: "(22, 2.5,
#: lookback 3)". They are module constants rather than arguments, for the
#: same reason as `pandas_ta/volatility/j_damiani.py`'s: the issue's quote
#: and the screen prototype (`docs/issues/screen/ind_screen_r2.py`,
#: candidate `j_safezone_dist`) spell exactly these three, and that one
#: triple is the whole of what the 2026-10-24 screen measured at Gate E. A
#: `period=`/`mult=`/`lookback=` surface would ship parameter combinations
#: nothing has measured, and the Gate E ledger refuses a run taken at
#: non-default parameters anyway (`docs/gate_e_ledger.py`).
PERIOD = 22
MULT = 2.5
LOOKBACK = 3

#: Bars a frame must have before the function computes at all, and it is
#: also the index of the first bar that can fire. The chain is
#: `pen` (1 bar) -> `avg` (PERIOD bars) -> `avg.shift(1)` (1 bar) ->
#: `rolling(LOOKBACK).max()` (LOOKBACK - 1 bars), so the first reading is
#: at index 25 and a frame needs 26 bars. ⚠ That is a floor on the INPUT
#: and a floor on the warm-up, not the warm-up itself: a frame with no
#: down-penetration in its first 22 bars starts later still (§C1 of
#: `docs/JSafezoneDistMeasured.md` measures 0 fired bars on a flat frame).
#: Pinned by `tests/test_j_safezone_dist.py::
#: test_a_frame_shorter_than_min_bars_is_refused`.
MIN_BARS = PERIOD + LOOKBACK + 1


def _down_penetration(low):
    """`max(low[T-1] - low[T], 0)`: how far this bar's low fell through the
    previous bar's low.

    Elder's "down-penetration", and the only place the price enters the
    stop. Bar 0 has no previous low, so its penetration is NaN -- UNDEFINED
    rather than zero, which is what keeps the first window from averaging a
    penetration that was never observed.
    """
    return (low.shift(1) - low).clip(lower=0.0)


def _mean_penetration(pen):
    """The mean down-penetration over `PERIOD` bars, averaged over the bars
    that HAD one.

    ⚠ This is the load-bearing reading of the issue's "mean(down-
    penetrations, 22)", and the alternative is a different column. Elder
    averages the penetrations themselves -- sum over the window divided by
    the NUMBER OF PENETRATIONS -- not the penetration series, which would
    divide by `PERIOD` and count the quiet bars as zeros. The issue's own
    prototype line says "mean over bars with a penetration", and
    `docs/JSafezoneDistMeasured.md` §A4 prices the divide-by-`PERIOD`
    reading instead of assuming it is close: it is a strictly smaller
    average, so a strictly higher stop and a strictly smaller distance.

    The divisor guard is not decoration. `hits` is 0 exactly when the
    window holds no penetration at all, and then `total` is 0 too, so the
    bare division is `0 / 0`. NaN is the right answer there -- "the average
    of no penetrations" has no value -- and deciding it here rather than
    inside numpy is what makes that a property of this module. §G2
    measures the guarded and the bare form bit-equal on every frame
    (`total > 0` implies `hits > 0`, because a penetration that is counted
    is positive), so what the guard buys is the decision, not a different
    number.
    """
    total = pen.rolling(PERIOD, min_periods=PERIOD).sum()
    hits = (pen > 0.0).astype(float).rolling(PERIOD, min_periods=PERIOD).sum()
    return total / hits.where(hits > 0.0)


def j_safezone_dist(low, close, offset=None, **kwargs):
    """Indicator: distance to Elder's SafeZone stop, long (J_SAFEZONE_DIST)"""
    # Validate Arguments
    low = verify_series(low, MIN_BARS)
    close = verify_series(close, MIN_BARS)
    offset = get_offset(offset)

    if low is None or close is None: return

    # Calculate Result
    # Both inputs are sanitised before any arithmetic, and the two guards
    # are deliberately different because the two series do different work.
    #
    # `low` only has to be FINITE. It enters the stop through differences
    # (`low[T-1] - low[T]`, then `low[T-1] - MULT * avg`), which are
    # meaningful at any finite level, and an infinite low would otherwise
    # survive the `clip`, the rolling sum and the rolling max and ship an
    # infinite stop. A non-positive low is left alone: it is not a divisor
    # here, and the scale-free claim rests on the CLOSE.
    #
    # `close` is the divisor, so it must also be positive and normal. A
    # zero or subnormal close makes the ratio overflow; a negative one
    # silently flips the column's sign. Same guard, same reasons, as the
    # siblings that divide by a price (`statistics/tf_iqr_ret_60.py`,
    # `statistics/ts_q05_60.py`).
    lo = low.astype(float)
    lo = lo.where(np.isfinite(lo))
    px = close.astype(float)
    px = px.where(np.isfinite(px) & (px >= np.finfo(float).tiny))

    # Elder's SafeZone stop for a LONG position, as issue #121 quotes it:
    # "L1 - 2.5*mean(down-penetrations, 22), max over 3".
    pen = _down_penetration(lo)
    avg = _mean_penetration(pen)
    # `L1` is the PREVIOUS bar's low, and `avg` is shifted with it, so the
    # stop placed for bar T is the one yesterday's data already justified.
    # ⚠ That shift is what makes this column causal in the only way a
    # trailing stop can be: bar T reads `low` up to T - 1 and `close` at T,
    # and nothing at all from bar T's own low. Dropping either `shift(1)`
    # would let today's low set today's stop -- not a look-ahead across
    # bars, but a stop the trader could not have had in the market -- and
    # `tests/test_j_safezone_dist.py` carries a mutant for each.
    raw = lo.shift(1) - MULT * avg.shift(1)
    # "max over 3": the stop TRAILS. Taking the highest of the last
    # `LOOKBACK` candidates stops a single wide bar from dropping the stop
    # back down, which is the whole point of Elder's lookback.
    # `min_periods=LOOKBACK` is pandas' default for this window and is
    # spelled out because it is load-bearing: one NaN candidate blanks
    # `LOOKBACK` bars of output rather than being skipped.
    stop = raw.rolling(LOOKBACK, min_periods=LOOKBACK).max()

    # The scale-free form the issue specifies: `(close - stop) / close`.
    # Not the stop level, which is a price and so not a feature
    # (CLAUDE.md, "Scale-free"). Positive while the close is above its
    # stop; negative once the stop has been passed.
    dist = (px - stop) / px
    # ⚠ Defence in depth, and §G3 measures that it is NOT a no-op. Finite
    # inputs leave THREE arithmetic routes to an infinity, not one, and
    # §G3 runs all three with their intermediates rather than reasoning
    # about them, numbered there in the order they occur in the chain:
    # (1) overflow in `low.shift(1) - low`, which needs a NEGATIVE low --
    # legal here; (2) overflow in `pen.rolling(22).sum()`, eleven
    # penetrations near DBL_MAX in one window; (3) overflow in THIS
    # division, a stop near 1e300 over a close near 1e-300.
    # Measured: only route 3 reaches the output. Routes 1 and 2 die in
    # the rolling sum, because pandas' `rolling.sum` is COMPENSATED and
    # an overflowing window yields NaN rather than inf -- a pandas
    # BEHAVIOUR this module relies on, measured directly in §G3 and
    # pinned by a test so that an upgrade which stops doing it fails here
    # rather than shipping an infinite feature. On route 3 this line is
    # the only thing between the column and 95 infinite readings out of
    # 120, and on all eight ordinary test frames it is bit-equal to the
    # unguarded form.
    dist = dist.where(np.isfinite(dist))

    # Offset
    if offset != 0:
        dist = dist.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        dist.fillna(kwargs["fillna"], inplace=True)

    # Name and Categorize it
    dist.name = f"J_SAFEZONE_DIST_{PERIOD}_{MULT}_{LOOKBACK}"
    dist.category = "trend"

    return dist


j_safezone_dist.__doc__ = \
"""Distance to Elder's SafeZone stop, long (J_SAFEZONE_DIST)

How far the close stands above Elder's SafeZone long stop, in fractions of
the close. The stop trails yesterday's low by 2.5 mean down-penetrations.

    pen[T]  = max(low[T-1] - low[T], 0)            a down-penetration
    avg[T]  = sum(pen, 22) / count(pen > 0, 22)    mean over bars that HAD one
    raw[T]  = low[T-1] - 2.5 * avg[T-1]
    stop[T] = max(raw[T-2], raw[T-1], raw[T])
    J_SAFEZONE_DIST[T] = (close[T] - stop[T]) / close[T]

Source: jesse indicators (MIT), `safezonestop.py`, as PandasTa issue #121
quotes it: "safezonestop.py (Rust core; Elder's definition used): L1 -
2.5*mean(down-penetrations, 22), max over 3". The underlying rule is
Alexander Elder's SafeZone stop.
⚠ jesse is NOT installed in this worktree and web access is unavailable,
so Gate A does not read jesse's own source
(`tests/test_j_safezone_dist.py::test_the_source_library_is_not_installed
_here` records that, so the claim cannot rot into "checked against
jesse"). What Gate A checks is the formula the issue quotes, spelled two
independent ways, and the attribution is to the issue's QUOTE rather than
to jesse's code. The issue itself says of the library: "existence, not
evidence".
⚠ The LONG stop only. jesse's function takes a direction and issue #121
names the long side; no short-side column was screened at Gate E.

**Gate A is the issue's formula, spelled independently.** A bar-by-bar
oracle -- its own penetration loop, its own 22-bar window sums over plain
Python slices, its own 3-bar max -- agrees with this module on 1,475 of
1,475 fired bars of each of six varying frames, measured BIT-equal and
asserted at 1e-12 (absolute and relative), because a `rolling.sum` and a
`sum()` over a slice are not obliged to round the same way and a reduced
numpy kernel may not. The screen prototype, which shares pandas' rolling
operators, is asserted bit-equal on all eight frames; that limb is what
ties this port to the 2026-10-24 screen's Gate E figures.

⚠ **WHICH MEAN is the load-bearing reading of this formula, and the
alternative is a different column.** Elder averages over the bars that HAD a
penetration (`sum / count`), not over all 22 (`sum / 22`). The issue's
prototype says "mean over bars with a penetration" and this module
follows it. Measured (§A4): the divide-by-22 reading is a smaller
average on any window with a quiet bar, so a HIGHER stop and a SMALLER
distance -- on all 8,850 shared bars of six frames, every one of them,
and Spearman 0.9378 .. 0.9705 with max |diff| 2.09e-02 .. 1.09e-01. It
also never goes NaN, so it is a different column rather than a rounding
of this one.

⚠ **THE MISSINGNESS IS INFORMATIVE, and it is the one structural thing a
consumer must know.** `avg` is NaN exactly when the last 22 bars hold NO
down-penetration at all -- a perfectly smooth advance, or no movement at
all -- so the column is blank precisely where the market has been
unusually kind to a long. It is not missing at random. A flat frame fires
on 0 of its 1,500 bars (measured) and a strictly-rising-lows frame on 0
of 1,500; `0 < fires < n` is therefore asserted on the six VARYING frames
and those two are pinned separately.
⚠ And unlike `j_damiani`, a single bad price here EMPTIES BARS: one NaN
or infinite low blanks exactly 25 bars of output, bars T+1 .. T+25
(measured for NaN, +inf and -inf at four interior plant points; a plant
at the last bar empties nothing, because the frame ends first), while a
bad CLOSE empties exactly that one bar. The NaNs are a leading prefix on
a clean frame and are NOT in general -- §G1 measures the mid-series hole
and that every bar before it is bit-identical.

⚠ **Gate E on the PROTOTYPE was SHIP** -- max |rho| 0.7059 vs the
manifest's `Dist_to_hma_pct` over 89 BIST frames (n = 396,606), top-five
per-frame max median 0.7249, under the 0.76 ship line. The next
comparators were `Dist_to_hma_pct_Pctl` 0.6979 and `cfo` 0.6857. The
port's own Gate E run is what decides its band, and it is PENDING: the
launcher runs it after this session (§E of
`docs/JSafezoneDistMeasured.md`).
⚠ **What it is nearest to among SEVEN chosen neighbours** -- not a sweep
of the fork -- is the same column the screen found:
`linreg_channel`'s `LINREG_LOWER_2_DIST_PCT`, at |rho| 0.6371 .. 0.7040
over the six varying frames, then `RVI_14` at 0.5174, and nothing else
among those seven reaches 0.21 (§L). Both of the top two are distances
to a lower band, so the agreement is not a coincidence. That is SIX
SYNTHETIC frames and a disclosure, not a gate; the one fork-wide
measurement is the screen's own stage-2 sweep, which put the same
column nearest at 0.7578 on 12 REAL frames.

Causal: bar T reads `low` up to T - 1 and `close` at T. Nothing later,
and nothing from bar T's own low. Measured by a 36-offset
future-perturbation sweep (0 of 36 on each of six frames) and by six
look-ahead mutants read off this file, edited and `exec`'d in memory,
each live and caught on 3 to 36 of those 36 offsets of each of the six.
⚠ A count below 36 is the FORMULA's, not a gap in the mutant: the
`clip(lower=0)`, the mean over the hits and the `rolling(3).max()` all
discard information, so raising a suffix by 3% moves the output only at
the offsets where the perturbed bar is one those operators select.
⚠ **And the sweep has a blind spot this module states rather than
leaves for a reader to find.** The stop carries TWO `shift(1)`s between
a penetration and the output, so an edit that leads by ONE bar is
absorbed by them: it makes the output read bar T's own low -- wrong,
because the stop a trader could have had in the market is yesterday's --
without reading any LATER bar. Five such edits are measured in §B2, all
five caught 0 of 36 by the sweep and all five caught by Gate A's oracle.
That is why Gate B here is the sweep AND the oracle, and why the
look-ahead mutants lead by two bars where the chain allows it.

Scale-free by construction: every step up to `stop` is homogeneous of
degree 1 in the price, and the final division cancels the factor, so a
x8/x64 rescale is bit-identical on 1,475 of 1,475 bars of each of six
frames and at price levels 1e-6, 1e+6 and 1e+100. x10/x3.7/x0.1/
x1.0000001 round: measured max 4.091e-11 relative over 24 cells, and
6.546e-11 over the same 24 with AVX-512/AVX2/FMA3 disabled -- the only
figure outside the receipt's wall-clock section that moves between numpy
dispatches, which is why the test asserts 1e-9 rather than the digits.
A level SHIFT of +10
moves all 1,475 fired bars of every one of the six, so the
bit-identity is a real check and not a vacuous one.

⚠ **Unbounded in both directions, and the sign is the signal.** In
normal conditions the close sits a few percent above its stop; over the
8,850 fired bars of the six varying frames the column reads -0.3262 ..
0.3375, negative on 1,138 of them and exactly 0.0 on none (§C1).
Nothing bounds it: a long stop can be arbitrarily far below a close
that has run away from it, and a close that has collapsed through the
stop reads arbitrarily negative.

Cost: two `rolling` sums, one `rolling` max, three shifts
(`low.shift(1)` in the penetration, `lo.shift(1)` and `avg.shift(1)` in
the raw stop) and two divisions (the mean over the hits, and the final
`/ close`). Linear in bars. ⚠ The wall-clock figures live in
`docs/JSafezoneDistMeasured.md` §Z and nowhere else, including here: they
are one machine's and one run's.

Calculation:
    Default Inputs:
        period=22, mult=2.5, lookback=3  -- module constants
    pen     = (low.shift(1) - low).clip(lower=0)
    avg     = pen.rolling(22).sum() / (pen > 0).rolling(22).sum()
    raw     = low.shift(1) - 2.5 * avg.shift(1)
    stop    = raw.rolling(3).max()
    J_SAFEZONE_DIST = (close - stop) / close

Args:
    low (pd.Series): Series of 'low's
    close (pd.Series): Series of 'close's
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)

Returns:
    pd.Series: J_SAFEZONE_DIST_22_2.5_3, a fraction of the close
"""
