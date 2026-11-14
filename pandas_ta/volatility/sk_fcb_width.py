# -*- coding: utf-8 -*-
import numpy as np

from pandas_ta.utils import get_offset, verify_series

#: Bars on each side of a candidate centre bar that a Williams fractal must
#: dominate -- Skender's `windowSpan`, used for BOTH sides. Two is the only
#: value anything here has measured: issue #107 is titled "Fractal Chaos
#: Band width (span 2)" and the screen prototype calls
#: `last_fractal(h, 2, True)`. A module constant rather than an argument so
#: that no unmeasured span can ship; `tests/test_sk_fcb_width.py` builds the
#: column's name out of it, so a change here fails the wiring test instead
#: of renaming a shipped column silently.
SPAN = 2

#: Bars a frame must have before the function will compute at all. The
#: earliest bar a fractal can be CENTRED on is `SPAN` (it needs `SPAN` bars
#: to its left) and it is only confirmed `SPAN` bars later, so `2 * SPAN` is
#: the earliest bar that can carry a band and `MIN_BARS` is the shortest
#: frame with one such bar in it.
#: ⚠ A floor on the INPUT, and NOT the warm-up. The warm-up here is
#: DATA-DEPENDENT: the column is NaN until a fractal high AND a fractal low
#: have both confirmed, which on a frame with no strict local extreme at all
#: never happens. Counted per frame in `docs/SkFcbWidthMeasured.md` §C and
#: pinned by `tests/test_sk_fcb_width.py::test_the_warmup_is_data_dependent`.
MIN_BARS = 2 * SPAN + 1


def _last_fractal(x, span, upper):
    """Level of the most recent CONFIRMED Williams fractal in `x`, held
    forward -- the band leg Skender's `Fcb` carries.

    A fractal sits on centre bar `i` when `x[i]` beats all `span` bars on
    each side STRICTLY, which is Skender's `Fractal` with
    `leftSpan = rightSpan = span` and `EndType.HighLow`: its loop sets
    `isHigh = false` on `evalHigh <= pHigh`, so a TIE on either side is not
    a fractal. `x[i] > max(both sides)` is the same predicate, and the
    rolling form below is how the screen prototype spells it.

    ⚠ The result is placed on bar `i + span`, not on bar `i`. That is the
    whole of this port's causality: the right-hand `span` bars have to exist
    before the centre can be judged, so bar `i + span` is the first bar on
    which the fractal is knowable. See the module docstring for what Skender
    does with the index instead, and `docs/SkFcbWidthMeasured.md` §A3 for
    the measured cost of the two readings differing.
    """
    ref = x.shift(span)                     # the candidate centre bar
    if upper:
        left = x.shift(span + 1).rolling(span).max()
        right = x.rolling(span).max()
        is_fractal = (ref > left) & (ref > right)
    else:
        left = x.shift(span + 1).rolling(span).min()
        right = x.rolling(span).min()
        is_fractal = (ref < left) & (ref < right)
    # `where` over a bool mask: a NaN anywhere in either window makes the
    # comparison False rather than NaN, so a bad bar declines to produce a
    # fractal instead of poisoning one. `ffill` is what makes the band a
    # step function -- and it is also why a bad bar's reach is NOT bounded
    # by a window the way a rolling mean's is: a missed fractal changes the
    # band until the NEXT fractal replaces it, which is 10 bars for one NaN
    # high at bar 700 of `walk` and could be more on another frame.
    # `docs/SkFcbWidthMeasured.md` §G2.
    return ref.where(is_fractal).ffill()


def sk_fcb_width(high, low, close, offset=None, **kwargs):
    """Indicator: Fractal Chaos Band width, scale-free (SK_FCB_WIDTH)"""
    # Validate Arguments
    high = verify_series(high, MIN_BARS)
    low = verify_series(low, MIN_BARS)
    close = verify_series(close, MIN_BARS)
    offset = get_offset(offset)

    if high is None or low is None or close is None: return

    # Calculate Result
    # What this guard buys, measured rather than assumed: `ref > left` is
    # True for an INFINITE high, so an unguarded `+inf` high becomes a
    # fractal and `ffill` carries `inf` as the upper band until the next
    # fractal replaces it -- 9 infinite readings for one plant at bar 700
    # (and 5 for a `-inf` low). Masked out, that bar simply produces no
    # fractal. A NaN high already behaves that way, so the guard's whole
    # effect is to make an infinity behave like a NaN; it changes nothing
    # on a clean frame, where this module is bit-equal to the screen
    # prototype, which has no guard. `docs/SkFcbWidthMeasured.md` §G3.
    h = high.where(np.isfinite(high))
    l = low.where(np.isfinite(low))
    upper = _last_fractal(h, SPAN, True)
    lower = _last_fractal(l, SPAN, False)
    # The divisor is what makes the column scale-free, so it is also the
    # one place a bad price turns a reading into an infinity. A close that
    # is not finite, not positive, or subnormal (below `tiny`, where the
    # division overflows) empties its own bar and no other.
    c = close.where(np.isfinite(close) & (close >= np.finfo(float).tiny))
    width = (upper - lower) / c

    # Offset
    if offset != 0:
        width = width.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        width.fillna(kwargs["fillna"], inplace=True)

    # Name and Categorize it
    width.name = f"SK_FCB_WIDTH_{SPAN}"
    width.category = "volatility"

    return width


sk_fcb_width.__doc__ = \
"""Fractal Chaos Band width, scale-free (SK_FCB_WIDTH)

The last confirmed fractal high minus the last confirmed fractal low,
over close: how wide the Fractal Chaos Band stands.

    upper[T]      = level of the last CONFIRMED fractal high, held forward
    lower[T]      = level of the last CONFIRMED fractal low, held forward
    SK_FCB_WIDTH  = (upper - lower) / close

A fractal high is centred on a bar whose high beats all `SPAN` = 2 highs
on each side STRICTLY, and it is confirmed `SPAN` bars later, when those
right-hand bars exist.

Source: Skender Stock.Indicators (Apache-2.0), `Fcb`, as PandasTa issue
#107 names it: "Fcb.Series.cs: upper - lower", span 2. The `/ close` is
the fork's, from the screen prototype's scale-free form.
⚠ That C# file is NOT readable from this worktree: Stock.Indicators is
not installed, `docs/pine/` is absent, and a repo-wide search for
`Fcb.Series.cs` finds nothing -- those three are pinned by
`tests/test_sk_fcb_width.py::test_the_source_library_is_not_readable_here`,
so the claim cannot rot into "checked against Skender" if a dependency
or a vendored corpus appears. ⚠ Web access was also unavailable in the
session that wrote this, and that one is NOT pinned by anything: a test
cannot see it.
What Gate A checks is the formula the issue names, spelled two ways, and
the attribution is to the issue's NAMING of the source rather than to a
reading of its code.

**Gate A is that formula, spelled two ways -- ONE of them independent.** A
transcription of Skender's `Fractal` double loop plus `Fcb`'s
roll-forward, which shares no code with this module, and the screen
prototype are BOTH bit-equal to this module on every one of the 10,330
bars the eight synthetic frames of `docs/measure_sk_fcb_width.py` fire on,
with identical NaN masks. Nothing here is a tolerance: the band is a
SELECTED price level, so the only arithmetic is one subtraction and one
division.
⚠ The second limb is NOT a second derivation and is not claimed as one:
the prototype's `last_fractal` is `_last_fractal` above, operation for
operation, so its bit-equality on a clean frame is structural. What it
buys is the TIE to the screen's Gate E figures, which were measured on
that expression, and the module's guards priced at zero.

⚠ **Skender returns a fractal ON its centre bar; this port reads it SPAN
bars later, and that is a divergence, not a transcription.** Read at the
centre, the band would be knowable before its right-hand bars existed.
The two readings are both measured: they differ on 46 .. 839 of the bars
both fire on, at Spearman 0.4638 .. 0.9643 across seven frames, so this
is a real choice and not a rounding. The confirmed reading is the one the
screen prototype measured at Gate E and the only one of the two that
survives Gate B. ⚠ What is NOT established here is what `Fcb.Series.cs`
itself does with that index, because the file cannot be read.

⚠ **The predicate is STRICT, and on a tick grid that is the whole
column.** `>` and not `>=`, so a TIE on either side destroys the fractal
-- which is invisible on synthetic continuous floats and decisive on
rounded prices, the FVGDEAD trap this repo already paid for once. The
non-strict reading is IDENTICAL on all five continuous frames (0 bars
differ, Spearman 1.0000), differs on 43 bars of a 0.01-tick frame
(0.9556) and on 1,235 bars of a 2.0-tick frame, where it reads Spearman
0.0567 -- a different column. Rounding also starves the band: the same
walk yields 216 upper fractals unrounded, 212 at a 0.01 tick, 71 at 0.5
and 15 at 2.0, and on that last frame the column takes 60 distinct values
on 1,411 fired bars and holds one band leg for up to 428 bars.
⚠ Real BIST daily bars close exactly at an extreme on 21.17% of bars
(`CLAUDE.md`, FVGDEAD), so this is the behaviour Gate E's real frames
will see, and these synthetic figures do not predict it.

Causal: bar T reads the highs and lows up to bar T -- the centre it is
judging is bar T - 2 -- and `close[T]`, nothing later. Measured by a
sweep that splits each frame into one shared past and two WHOLLY
different futures and asks whether any earlier bar moved: 0 of 1,499
offsets on each of the eight frames.
⚠ That detector is deliberately not the usual "multiply the tail by
1.03", and the reason is this column: a fractal is a COMPARISON, so a
look-ahead only shows when a decision within SPAN bars of the boundary
flips. Five look-ahead mutants are read off this file, edited and exec'd
in memory (`tests/test_sk_fcb_width.py`); each is caught on each of the
six frames other than `flat` and `coarse`, but the weakest of them --
one bar of extra right-hand window -- is caught on as few as 4 of 36
offsets, and `coarse` catches only 3 of the 5 while `flat` catches 1.
A 36-of-36 headline is not available for this indicator and is not
claimed; `docs/SkFcbWidthMeasured.md` §B has the grid. That weakest
mutant is carried by reading its edit instead: bar `j - 1` is the only
prefix bar it can reach, so its exposure condition is derivable, and
over 1,495 offsets of each of the seven firing frames it is caught 0
times outside that condition (8,743 offsets, a total the script prints)
while all 30 misses inside it fall in three named buckets -- 17, 9 and 4
-- with none left over. §B2.

Scale-free by construction: the band legs are SELECTED by comparisons,
which no positive rescale changes, and the subtraction and division then
cancel the factor. A x8/x64 rescale is bit-identical on all 10,330 fired
bars of the eight frames, and the same run REPEATED at price levels 1e-6,
1e+6 and 1e+100 is bit-identical there too.
⚠ x10, x3.7, x0.1 and x1.0000001 are inexact and agree to 1.229e-12
relative with matching NaN masks (asserted at 1e-9). The risk peculiar to
this column is NOT that last bit: a rescale that collapsed two distinct
neighbouring prices onto one double would destroy a strict inequality and
move the band by a whole price level. Measured 0 such flips over seven
frames and four factors -- a measurement, not a proof that it cannot
happen.

⚠ **The warm-up is DATA-DEPENDENT, which no other number in this
docstring can replace.** The column is NaN until a fractal high AND a
fractal low have both confirmed. The earliest that can be is bar
`2 * SPAN` = 4, which needs one bar to be both the strict high and the
strict low of its window (an outside bar; reachable, and pinned by a hand
frame). On the seven frames that fire the first fire lands on bar 7 .. 89,
and on the eighth, a FLAT price, it never comes at all -- 0 of 1,500
bars: a constant price has no strict local
extreme, so the column is all-NaN on all 1,500 bars of `flat` -- 0 fires
is a reading about the instrument, not a defect, and not a divergence
either: 13 of this category's 63 columns read all-NaN on a flat frame,
`j_damiani` among them, measured in `docs/SkFcbWidthMeasured.md` §C3.
`MIN_BARS` = 5 is a floor on the INPUT only.

⚠ **Not a non-negative width, despite the name.** `upper` and `lower` are
the last fractal high and the last fractal low, taken from DIFFERENT bars
-- often far apart, up to 428 bars on `coarse` -- so nothing makes the
difference positive. It reads NEGATIVE on 5 .. 91 bars of each of the
seven firing frames, as low as -0.1294, and exactly 0.0 on 85 bars of
`coarse`, where both legs land on the same tick -- so `<= 0` runs to
5 .. 105 bars once those zeros are counted in. A hand frame in
`docs/SkFcbWidthMeasured.md` §H shows the mechanism at -0.8868. The span
over 10,330 bars is -0.1294 .. +0.4052 and no bound is claimed.

⚠ **It is a STEP function over a moving divisor.** The band only changes
when a fractal confirms (172 .. 230 steps per leg over 1,500 bars on the
six frames other than `flat` and `coarse`, 15 and 12 on `coarse`), so
between confirmations the column moves only because `close` does -- by
construction, since the numerator is literally the same two floats on
those bars. ⚠ How much of the column's LEVEL that accounts for is
measured, and it is not what the obvious guess says: against `1/close`
the column reads Spearman -0.0330 .. 0.4571, against its own numerator
in price units 0.5357 .. 0.9973. `docs/SkFcbWidthMeasured.md` §F.

NaN on the head, as above; and on any bar whose close is NaN, infinite,
zero, negative or subnormal -- such a close empties its own bar and no
other (measured: 1 bar and 0 others for each of NaN, 0.0, -1.0, +-inf and
1e-310). What that guard buys is measured too: unguarded, a zero or
subnormal close reads `inf`, a NEGATIVE close reads a plausible-looking
-1.503724, and an infinite close reads a plausible-looking 0.000000.
⚠ A bad HIGH or LOW is absorbed instead: a comparison against a NaN is
False, so the bar makes no fractal and no reading goes missing. The cost
is that its reach is NOT bounded by a window the way a rolling mean's is
-- `ffill` carries the older level until the next fractal replaces it,
measured 10 bars for a NaN high at bar 700 and 4 for a NaN low, with 0
bars before the plant moved either way.
⚠ The high/low guard exists for infinities only: `+inf > x` is True, so
an unguarded `+inf` high becomes a fractal and the band carries `inf` --
9 infinite readings for that one plant, and 5 for a `-inf` low. With the
guard, a NaN and an infinite price give bit-identical columns.
⚠ NOT guarded, and stated rather than hidden: a frame whose high/low and
close live hundreds of orders of magnitude apart overflows the division
(51 of 51 fired bars infinite at high/low 1e+300 with close 1e-300).
That is bad data rather than a price.

Cost: four rolling passes, four shifts, two `ffill`s and one division,
no Python loop, so time and memory are linear in bars -- a traced peak of
6.6 MB at 100,000 bars and 26.4 MB at 400,000, identical on two
invocations. ⚠ The wall clock is disclosed and not claimed: roughly 14 ms
and 52 ms for those two sizes on one machine, and two invocations of the
same section already disagree in the first decimal
(`docs/SkFcbWidthMeasured.md` §Z carries both).

Calculation:
    Default Inputs:
        span=2  -- a module constant
    is_high[j]    = high[j] > high[j-2 .. j-1] and high[j] > high[j+1 .. j+2]
    is_low[j]     = low[j]  < low[j-2 .. j-1]  and low[j]  < low[j+1 .. j+2]
    upper[T]      = high[j] for the greatest j <= T - 2 with is_high[j]
    lower[T]      = low[j]  for the greatest j <= T - 2 with is_low[j]
    SK_FCB_WIDTH[T] = (upper[T] - lower[T]) / close[T]

Args:
    high (pd.Series): Series of 'high's
    low (pd.Series): Series of 'low's
    close (pd.Series): Series of 'close's, the scale-free divisor
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)

Returns:
    pd.Series: SK_FCB_WIDTH_2, dimensionless
"""
