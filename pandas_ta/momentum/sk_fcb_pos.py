# -*- coding: utf-8 -*-
import numpy as np

from pandas_ta.utils import get_offset, verify_series
# The band is issue #107's, already shipped and already measured, so this
# module IMPORTS it rather than retyping the fractal loop -- `CLAUDE.md`,
# "Do not add a fourth copy: import the function". `SPAN` and `MIN_BARS`
# come from there too, so the two columns cannot drift to different spans.
# ⚠ The coupling runs the other way as well: an edit to `_last_fractal`
# changes THIS column without changing this file. What catches that is the
# Gate E ledger's `output_fp`, a live fingerprint on a fixed frame rather
# than a file hash (`docs/gate_e_ledger.py:148`), plus
# `tests/test_sk_fcb_pos.py::test_the_band_helper_is_the_shipped_sibling`.
from pandas_ta.volatility.sk_fcb_width import MIN_BARS, SPAN, _last_fractal


def sk_fcb_pos(high, low, close, offset=None, **kwargs):
    """Indicator: position inside the Fractal Chaos Bands (SK_FCB_POS)"""
    # Validate Arguments
    high = verify_series(high, MIN_BARS)
    low = verify_series(low, MIN_BARS)
    close = verify_series(close, MIN_BARS)
    offset = get_offset(offset)

    if high is None or low is None or close is None: return

    # Calculate Result
    # Same guard as the sibling, and it buys the same thing: `ref > left` is
    # True for an INFINITE high, so an unguarded `+inf` high becomes a
    # fractal and `ffill` carries `inf` as the upper band until the next
    # fractal replaces it. Masked out, such a bar produces no fractal, which
    # is what a NaN high already does. Priced in `docs/SkFcbPosMeasured.md`
    # §G3.
    h = high.where(np.isfinite(high))
    l = low.where(np.isfinite(low))
    upper = _last_fractal(h, SPAN, True)
    lower = _last_fractal(l, SPAN, False)
    # ⚠ `upper - lower` IS NOT POSITIVE and is not guarded to be. The two
    # legs are read from different bars, so the band can be crossed or
    # collapsed: a zero denominator sends the bar to +-inf and the
    # `replace` below empties it, and a NEGATIVE denominator keeps the bar
    # with the scale INVERTED -- a close above both legs then reads below 0
    # instead of above 1. Both are measured per frame in
    # `docs/SkFcbPosMeasured.md` §C4, and the choice not to mask the
    # negative case is the screen prototype's, which is what Gate E's
    # 0.8348 was measured on.
    pos = (close - lower) / (upper - lower)
    # The prototype's `sdiv`: `_fin(a / b)`, i.e. `+-inf -> NaN`
    # (`docs/issues/screen/ind_screen.py:37-42`). It is the only guard this
    # column needs on `close`: a close that is NaN or infinite makes the
    # quotient NaN or infinite, so the bar empties here instead of needing
    # a mask of its own (§G1).
    pos = pos.replace([np.inf, -np.inf], np.nan)

    # Offset
    if offset != 0:
        pos = pos.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        pos.fillna(kwargs["fillna"], inplace=True)

    # Name and Categorize it
    pos.name = f"SK_FCB_POS_{SPAN}"
    pos.category = "momentum"

    return pos


sk_fcb_pos.__doc__ = \
"""Position inside the Fractal Chaos Bands (SK_FCB_POS)

Where close sits between the last confirmed fractal low and the last
confirmed fractal high: 0 at the lower band, 1 at the upper band.

    upper[T]    = level of the last CONFIRMED fractal high, held forward
    lower[T]    = level of the last CONFIRMED fractal low, held forward
    SK_FCB_POS  = (close - lower) / (upper - lower)

A fractal high is centred on a bar whose high beats all `SPAN` = 2 highs
on each side STRICTLY, and it is confirmed `SPAN` bars later, when those
right-hand bars exist.

Source: Skender Stock.Indicators (Apache-2.0), `Fcb`, as PandasTa issue
#108 names it: "Fcb.Series.cs: bands = last fractal high / low", span 2.
The `(close - lower) / (upper - lower)` is the fork's, from the screen
prototype's scale-free form.
⚠ That C# file is NOT readable from this worktree: Stock.Indicators is
not installed, `docs/pine/` is absent, and a repo-wide search for
`Fcb.Series.cs` finds nothing -- those three are pinned by
`tests/test_sk_fcb_pos.py::test_the_source_library_is_not_readable_here`,
so the claim cannot rot into "checked against Skender" if a dependency
or a vendored corpus appears. ⚠ Web access was also unavailable in the
session that wrote this, and that one is NOT pinned by anything: a test
cannot see it.
What Gate A checks is the formula the issue names, spelled two ways, and
the attribution is to the issue's NAMING of the source rather than to a
reading of its code.

⚠ **THE DENOMINATOR IS NOT POSITIVE, and that is the one thing to know.**
`upper` and `lower` are the last fractal HIGH and the last fractal LOW,
read from DIFFERENT bars, so nothing makes the band well-ordered. Three
regimes, all measured in `docs/SkFcbPosMeasured.md` §C4:
  * `upper > lower` -- 1,306 .. 1,486 of the 1,500 bars of each of the
    seven firing synthetic frames. The column means what its name says.
  * `upper == lower` -- the quotient is +-inf and the bar is EMPTIED. 0
    bars on six frames and 85 on a 2.0-tick frame, where it is the whole
    of the gap between 1,411 bars with a band and 1,326 fired bars. The
    sibling `sk_fcb_width` reads exactly 0.0 on those same bars; this
    column reads nothing.
  * `upper < lower` -- 5 .. 91 bars of each firing frame, in 1 .. 17 runs
    of up to 20 bars. The bar is KEPT with the position scale INVERTED:
    a close above both legs reads BELOW 0 instead of above 1.
Masking the inverted band instead was measured, not waved away: it
differs from this column on exactly those 5 .. 91 bars per frame and
nowhere else (Spearman 1.0000 and 0.0 max difference on the bars both
fire). Keeping them is the screen prototype's reading, and the prototype
is what Gate E's 0.8348 was measured on.

⚠ **Not bounded to [0, 1], and not nearly.** Only 593 .. 944 of each
frame's fired bars land inside the band; 142 .. 400 read below 0 and
37 .. 744 above 1. The span over the seven frames is -182.0 .. +187.0,
reached on a 0.01-tick frame where the two legs sat one tick apart. No
bound is claimed, and a consumer clipping or rank-transforming this
column should know the tail comes from a SMALL DENOMINATOR rather than
from an extreme close.

**Gate A is that formula, spelled two ways -- ONE of them independent.** A
transcription of Skender's `Fractal` double loop plus `Fcb`'s
roll-forward, which shares no code with this module, and the screen
prototype are BOTH bit-equal to this module on every one of the 10,245
bars the eight synthetic frames of `docs/measure_sk_fcb_pos.py` fire on,
with identical NaN masks. Nothing here is a tolerance: the legs are
SELECTED price levels, so the arithmetic is two subtractions and one
division on the same doubles.
⚠ The second limb is NOT a second derivation and is not claimed as one:
the prototype's `last_fractal` is the imported `_last_fractal` operation
for operation and its `sdiv` is the `replace` above. What it buys is the
TIE to the screen's Gate E figures, which were measured on that
expression.

⚠ **Skender returns a fractal ON its centre bar; this port reads it SPAN
bars later, and that is a divergence, not a transcription.** Read at the
centre, the band would be knowable before its right-hand bars existed.
The two readings are both measured: they differ on 42 .. 841 of the bars
both fire on, at Spearman 0.7765 .. 0.9845 across seven frames. The
confirmed reading is the one the screen prototype measured at Gate E and
the only one of the two that survives Gate B. ⚠ What is NOT established
here is what `Fcb.Series.cs` itself does with that index, because the
file cannot be read.

⚠ **The predicate is STRICT, and on a tick grid that is the whole
column.** `>` and not `>=`, so a TIE on either side destroys the fractal
-- invisible on synthetic continuous floats and decisive on rounded
prices, the FVGDEAD trap this repo already paid for once. The non-strict
reading is IDENTICAL on all five continuous frames (0 bars differ,
Spearman 1.0000), differs on 43 bars of a 0.01-tick frame (0.9957) and on
1,256 bars of a 2.0-tick frame, where it reads Spearman 0.3417 -- a
different column. Rounding also starves the band: the same walk yields
216 upper fractals unrounded, 212 at a 0.01 tick, 71 at 0.5 and 15 at
2.0, and on that last frame the column takes 27 distinct values on 1,326
fired bars and holds one band leg for up to 429 bars.
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
flips. Six look-ahead mutants are read off the shipped source, edited
and exec'd in memory (`tests/test_sk_fcb_pos.py`) -- THREE of them in the
`_last_fractal` this module imports, which is the only way to test the
causality of code this file does not contain. Four are caught on 28 .. 36
of 36 offsets; the two that look ahead through something discrete are
caught on as few as 4 of 36, so each of those is given a NECESSARY
condition for being catchable and swept densely: over 10,465 offsets of
seven frames they are caught 1,685 of 1,696 and 1,664 of 1,676 exposed
offsets and 0 of the ~8,780 unexposed ones, with every one of the 23
misses classified (10 where the band only moved on bars that read NaN
anyway, 13 where two different bands gave the same quotient) and none
left over. `docs/SkFcbPosMeasured.md` §B .. §B2.

**Scale-free, and more: invariant under any increasing AFFINE map of
price.** The legs are SELECTED by comparisons, which no positive rescale
or level shift changes, and the factor then cancels between numerator and
denominator -- which is also why this column needs no `/ close`. A x8/x64
rescale is bit-identical on all 10,245 fired bars of the eight frames,
and the same run REPEATED at price levels 1e-6, 1e+6 and 1e+100 is
bit-identical there too.
⚠ x10, x3.7, x0.1 and x1.0000001 are inexact and agree to 9.633e-11
relative with matching NaN masks (asserted at 1e-7, which is three
orders of margin and not a measured bound). A LEVEL SHIFT is invariant
too but not bit-identical, because adding a constant re-rounds every
price: Spearman 1.0000 with matching masks at +1, +50 and +1e6, within
4.260e-14, 9.854e-12 and 1.307e-07 relative.
⚠ The risk peculiar to a comparison-selected band is NOT that last bit: a
rescale that collapsed two distinct neighbouring prices onto one double
would destroy a strict inequality and move a leg by a whole price level.
Measured 0 such flips over seven frames and four factors -- a
measurement, not a proof that it cannot happen.

⚠ **The warm-up is DATA-DEPENDENT, which no other number in this
docstring can replace.** The column is NaN until a fractal high AND a
fractal low have both confirmed. The earliest that can be is bar
`2 * SPAN` = 4, which needs one bar to be both the strict high and the
strict low of its window (an outside bar; reachable, and pinned by a hand
frame). On the seven frames that fire the first fire lands on bar 7 .. 89,
and on the eighth, a FLAT price, it never comes at all -- 0 of 1,500
bars, because a constant price has no strict local extreme. That last
part is NOT a divergence from the bucket and it was RUN rather than
assumed: of 139 columns from the 86 names in `Category["momentum"]` on a
flat OHLCV frame, 41 read all-NaN -- `willr`, `rsi`, `cci` and
`stochrsi` among them -- 78 read exactly 0.0 and 20 read something else
(`docs/SkFcbPosMeasured.md` §C3). `MIN_BARS` = 5 is a floor on the INPUT
only.

⚠ **It is a STEP function's quotient.** Both legs change only when a
fractal confirms (15 .. 230 steps per leg over 1,500 bars, one leg held
for up to 429 bars on a 2.0-tick frame), so between confirmations the
column moves only because `close` does, AFFINELY, with the slope's SIGN
set by the denominator. Measured on the longest constant-leg stretch of
each frame, its rank correlation against close is exactly +1 where
`upper > lower` and exactly -1 where `upper < lower`. ⚠ POOLED over a
whole frame it is NOT a close proxy, and the guess that it would be is
refuted: Spearman against close reads -0.0112 .. 0.5049. Against its own
numerator `close - lower`, in price units, it reads 0.3669 .. 0.8919,
which is the highest row of `docs/SkFcbPosMeasured.md` §F -- most of what
this column RANKS is already in the numerator.

NaN on the head, as above; on any bar whose band is collapsed
(`upper == lower`); and on any bar whose close is NaN or infinite -- such
a close empties its own bar and no other (measured: 1 bar and 0 others).
⚠ A ZERO, NEGATIVE or subnormal close is NOT emptied, and that is a
DIVERGENCE from the sibling, which masks them because there close is the
divisor. Here close is in the numerator, so such a bar reads a large
finite number instead (measured -29.1085 for a 0.0 close, -29.7735 for
-1.0, -29.1085 for 1e-310 and 6.65015e+299 for 1e+300, on a walk at
level 100). That is arithmetically what "position relative to a band"
means for such a close and it is not a defect, but a consumer that feeds
a bad tick through as a price gets a number rather than a gap.
⚠ A bad HIGH or LOW is absorbed instead: a comparison against a NaN is
False, so the bar makes no fractal and no reading goes missing. The cost
is that its reach is NOT bounded by a window the way a rolling mean's is
-- `ffill` carries the older level until the next fractal replaces it,
measured 10 bars for a NaN high at bar 700 and 4 for a NaN low, with 0
bars before the plant moved either way.
⚠ The high/low mask exists for infinities, and here the unguarded failure
is QUIETER than the sibling's: `+inf > x` is True, so an unguarded `+inf`
high becomes a fractal and lands in the DENOMINATOR, where the quotient
reads a plausible 0.0 rather than an `inf` -- 9 bars for one plant, and 5
bars turned NaN for a `-inf` low. With the mask, a NaN and an infinite
price give bit-identical columns.
⚠ What the sibling has and this column does NOT: a cross-scale overflow.
High/low at 1e+300 with close at 1e-300 leaves the sibling width infinite
on every fired bar and leaves this column finite on all 52 of them
(-90.2228 .. -50.3638), because the factor cancels.

Cost: four rolling passes, four shifts, two `ffill`s, two subtractions,
one division and one `replace`, no Python loop, so time and memory are
linear in bars -- a traced peak of 6.6 MB at 100,000 bars and 26.4 MB at
400,000, identical on two invocations. ⚠ The wall clock is disclosed and
not claimed: roughly 15 ms and 57 ms for those two sizes on one machine,
and two invocations of the same section already disagree in the first
decimal (`docs/SkFcbPosMeasured.md` §Z carries both).

Calculation:
    Default Inputs:
        span=2  -- a module constant, imported from `sk_fcb_width`
    is_high[j]  = high[j] > high[j-2 .. j-1] and high[j] > high[j+1 .. j+2]
    is_low[j]   = low[j]  < low[j-2 .. j-1]  and low[j]  < low[j+1 .. j+2]
    upper[T]    = high[j] for the greatest j <= T - 2 with is_high[j]
    lower[T]    = low[j]  for the greatest j <= T - 2 with is_low[j]
    SK_FCB_POS[T] = (close[T] - lower[T]) / (upper[T] - lower[T])

Args:
    high (pd.Series): Series of 'high's
    low (pd.Series): Series of 'low's
    close (pd.Series): Series of 'close's
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)

Returns:
    pd.Series: SK_FCB_POS_2, dimensionless
"""
