# -*- coding: utf-8 -*-
import numpy as np

from pandas_ta.utils import get_offset, verify_series


def sk_rocwb_ratio(close, length=None, band_length=None, offset=None, **kwargs):
    """Indicator: ROC over its own RMS band (SK_ROCWB_RATIO)"""
    # Validate Arguments
    length = int(length) if length and length > 0 else 20
    band_length = int(band_length) if band_length and band_length > 0 else 5
    close = verify_series(close, length + band_length)
    offset = get_offset(offset)

    if close is None: return

    # Calculate Result
    # The mask is a DIVERGENCE from the screen prototype, and what it buys
    # is that an infinite close behaves EXACTLY like a NaN one: the same 10
    # bars go empty, bit for bit. Without it an infinite price empties only
    # the 5 bars around itself, and the 5 at P + 20 .. P + 24 read PLAUSIBLE
    # NUMBERS off an infinite base price (-2.2216 where the clean column
    # reads 0.4980), which is harder to notice than a gap. On finite input
    # the two columns are bit-identical -- measured on
    # every frame of `docs/measure_sk_rocwb_ratio.py` (§G2) -- so the tie to
    # the prototype's Gate E measurement survives the divergence.
    c = close.where(np.isfinite(close))
    roc = 100 * (c / c.shift(length) - 1)
    # The band is a ROOT MEAN SQUARE of the ROC, not a standard deviation:
    # nothing is subtracted, so a drifting ROC inflates it. ⚠ It is also why
    # the column is BOUNDED: `roc[T]` is one of the `band_length` terms the
    # mean averages, so |roc[T]| <= sqrt(band_length) * band[T] and the
    # quotient cannot leave +-sqrt(5) at the default (§C2).
    band = np.sqrt((roc ** 2).rolling(band_length).mean())
    ratio = roc / band
    # The prototype's `sdiv`: `_fin(a / b)`, i.e. `+-inf -> NaN`
    # (`docs/issues/screen/ind_screen.py:37-42`). ⚠ Measured to fire on 0
    # bars of every frame here, and that is structural rather than lucky:
    # `band == 0` forces `roc[T] == 0` with it, so the quotient is 0/0 = NaN
    # and never +-inf (§G3). It is kept because it is the prototype's
    # expression, which is what Gate E was measured on.
    ratio = ratio.replace([np.inf, -np.inf], np.nan)

    # Offset
    if offset != 0:
        ratio = ratio.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        ratio.fillna(kwargs["fillna"], inplace=True)

    # Name and Categorize it
    ratio.name = f"SK_ROCWB_RATIO_{length}_{band_length}"
    ratio.category = "momentum"

    return ratio


sk_rocwb_ratio.__doc__ = \
"""ROC over its own RMS band (SK_ROCWB_RATIO)

The 20-bar Rate of Change divided by the root mean square of its own last
5 readings: today's move against how big recent moves have been.

    ROC[T]   = 100 * (close[T] / close[T - 20] - 1)
    band[T]  = sqrt( mean( ROC[T - 4 .. T]^2 ) )
    SK_ROCWB_RATIO[T] = ROC[T] / band[T]

Source: Skender Stock.Indicators (Apache-2.0), `RocWb`, as PandasTa issue
#109 names it: "RocWb.Series.cs: ROC20 vs band sqrt(mean5(ROC20^2))". The
RATIO is the fork's, from the screen prototype's scale-free form: Skender
returns the ROC and the band as two series in the same units, and a band
beside the thing it bounds is two features where this is one.
⚠ That C# file is NOT readable from this worktree: Stock.Indicators is not
installed, `docs/pine/` is absent, and a repo-wide search for
`RocWb.Series.cs` finds nothing -- pinned by
`tests/test_sk_rocwb_ratio.py::test_the_source_library_is_not_readable_here`
so the claim cannot rot into "checked against Skender" if a dependency or
a vendored corpus appears. ⚠ Web access was also unavailable in the
session that wrote this, and that one is NOT pinned by anything: a test
cannot see it.
What Gate A checks is the formula the issue names, spelled three ways, and
the attribution is to the issue's NAMING of the source rather than to a
reading of its code.

⚠ **The band is an RMS, not a standard deviation, and that is the whole
column.** Nothing is subtracted before squaring, so `roc[T]` is itself one
of the `band_length` terms the mean averages:

    band[T]^2 >= roc[T]^2 / band_length
    => |SK_ROCWB_RATIO[T]| <= sqrt(band_length) = 2.2360680 at the default

**BOUNDED, in other words, which is unusual for a momentum feature and is
the reason this form ships at all.** The bound is TIGHT: 24 flat closes
followed by one move reads 2.23606797749979, which is `sqrt(5)` to 0 ulps
(a hand frame pins it, both signs). A random walk gets close without
touching it -- the extreme over the eight synthetic frames of
`docs/measure_sk_rocwb_ratio.py` is -2.2361 .. +2.2361, and the frame that
attains it -- measured at 0 ulps from `math.sqrt(5)`, not at four decimal
places -- is the 2.0-tick one, where a flat band window is a rounding
artefact rather than a quiet market. No consumer needs to clip or
winsorise this column.
⚠ The reading NOT taken is the one the name suggests: the band as a
STANDARD DEVIATION of the ROC (ddof=0). That is a DIFFERENT COLUMN, not a
variant -- unbounded (|x| up to 138.9931 on the same frames) and Spearman
0.3251 .. 0.9163 against this one.

**Gate A is that formula, spelled three ways, and the headline is which
limb is bit-equal and which is not.** The three are: a scalar double loop
over Skender's own algebra (`100 * (c - c20) / c20`, a FRESH five-term sum
of squares, `sqrt`); the same loop respelled the way this module spells
the ROC (`100 * (c / c20 - 1)`); and the screen prototype.
  * the PROTOTYPE is bit-equal on all 10,226 bars the eight frames fire
    on, which is structural (it is this expression without the mask) and
    buys the tie to the Gate E figure the screen measured;
  * the module-spelling LOOP is NOT bit-equal on any of the seven frames
    that fire -- 102 .. 1,082 bars per frame differ by up to 2.335e-14
    relative (on `flat`, which is all-NaN, the two agree trivially) --
    because pandas' rolling mean is an online add/remove accumulator and
    a fresh five-term sum is not. Worth knowing before trusting any
    "bit-equal" claim about a rolling window;
  * Skender's SPELLING of the ROC differs by up to 4.007e-12 relative on
    575 .. 1,401 bars of each firing frame (0 on `flat`), at Spearman
    1.0000 (0.9999 on the 2.0-tick frame). An algebraic identity that is
    not a floating-point one.
⚠ **Why this module retypes two lines instead of importing `roc`, stated
as what was measured and not more.** `pandas_ta.roc` spells the ROC
Skender's way, so a ratio built on it is this column moved by that same
4.007e-12 at Spearman 1.0000 -- which CANNOT move a Gate E rho reported
to four decimals, and the claim is not that it could. The reason is
PROVENANCE: the issue's 0.8537 was measured on the prototype's
expression, and the cheapest way to keep the port and the screened
candidate the same object is to ship that expression bit for bit (§A2).
The repo's "import the helper" rule is being overridden for that, and the
cost is two lines of arithmetic that `roc` already contains.

Causal: bar T reads `close[T - 24 .. T]` and nothing later. Measured by a
sweep that splits each frame into one shared past and two WHOLLY different
futures and asks whether any earlier bar moved: 0 of 1,499 offsets on each
of the eight frames. FIVE look-ahead mutants are read off the shipped
source, edited and `exec`'d in memory, and asserted live first.
⚠ A 36-of-36 headline is NOT available for all five and is not claimed.
The three that reach into the ROC (`roc-lead`, `close-lead`,
`output-early`) are caught on 36 of 36 offsets of every frame. The two
that reach into the BAND are caught on 36 of 36 of the six other frames
and then: `band-lead` 10 of 36 on the 2.0-tick frame, `band-centred` 15
of 36, and both 0 of 36 on a FLAT price. The reason is arithmetic rather
than luck -- a shifted band multiplies a numerator that is exactly 0 on
449 bars of the tick frame and on every bar of the flat one -- so each is
given a necessary condition and swept over all 11,992 offsets of the
eight frames: `band-lead` (condition: `roc[j - 1]` is a non-zero number
whose bar exists) 9,883 exposed, `band-centred` (`roc[j - 1]` or
`roc[j - 2]`) 10,034, all of them caught, 0 caught outside the condition
and 0 exposed-but-missed.

**Scale-free, in the strict sense and not only the gate's.** The price
enters only as `close[T] / close[T - 20]`, so a positive rescale cancels
before the first arithmetic. x8, x64 and the exact binary factors 2^-20,
2^20 and 2^300 are bit-identical on every fired bar of all eight frames;
x10, x3.7, x0.1 and x1.0000001 are inexact and agree to 1.885e-11
relative with matching NaN masks (asserted at 1e-7, four orders of margin
and not a measured bound).
⚠ A LEVEL SHIFT is NOT invariant, and a reader who has met the sibling
`sk_fcb_pos` (where it is) must not assume it here: a ratio of prices is
not a ratio of prices-plus-a-constant. Measured on a walk at level 100,
adding 1 / 50 / 1e6 moves the column by 9.437e-04 / 2.325e-02 /
4.491e-02 absolute, at Spearman 1.0000 / 1.0000 / 0.9999 -- small, and
NOT zero.

**Fires from bar 24, and the warm-up is NOT data-dependent.**
`length + band_length - 1` = 24 with the defaults, and on SIX of the eight
frames every bar from 24 on fires (1,476 of 1,500); the 2.0-tick frame
fires 1,370 and a flat price 0. The exceptions are flat stretches:
`band == 0` needs five consecutive EXACTLY zero ROC readings, which needs
25 constant closes, so planted flat patches of 20 / 23 / 24 / 25 / 29 / 40
bars empty
0 / 0 / 0 / 1 / 5 / 16. On the 2.0-tick frame rounding does it without any
flat patch at all: 449 bars read a ROC of exactly 0, 106 bars are emptied,
and 343 bars read exactly 0.0.
⚠ Firing nothing on a flat price is ordinary for the bucket rather than a
defect, and that was RUN rather than assumed: of 144 columns from the 87
names in `Category["momentum"]` on a flat OHLCV frame, 42 read all-NaN
(this one among them), 77 read exactly 0.0 and 25 read something else
(`docs/SkRocwbRatioMeasured.md` §C3).
⚠ **Every count in this docstring is SYNTHETIC. Gate C's real-data limb
is OWED**, to the session that records the launcher's Gate E run, and the
number it has to fill in is this one: how often `close[T] == close[T-20]`
on the 89 ALTPORT-1 BIST frames, because that is what empties this column
and what makes it read exactly 0.0. 21.17% of real BIST daily bars close
exactly at an extreme (`CLAUDE.md`, FVGDEAD), so a 2.0-tick synthetic
frame is a stand-in and not a forecast.

NaN on the head (bars 0 .. 23) and on a flat band window, as above. A
single NaN close at bar P empties exactly 10 bars -- P .. P + 4 and
P + 20 .. P + 24 -- and moves 0 earlier bars; an INFINITE close does
exactly the same, bit for bit, which is what the `isfinite` mask buys.
Without the mask it would empty only the first 5 and leave the other 5
reading plausible numbers off an infinite base price (-2.2216 where the
clean column reads 0.4980).
⚠ A ZERO, SUBNORMAL or 1e+300 close is NOT masked -- it is a finite price
-- and empties 5 bars instead of 10; a NEGATIVE close empties none and
just moves values. None of them produces a quiet 0.0: measured 0 bars
reading exactly 0.0 that did not already, on all seven plants.
⚠ **The forward reach is not the 10 bars the formula implies.** Every
plant above moves bars out to P + 324 in their LAST BITS (230 .. 240 bars,
max 3.375e-14 absolute), because pandas' rolling mean is an online
accumulator: a bar that passes through the window changes the running
sum's rounding for every window after it. It is a last-bit effect and not
a second signal, and it is the same mechanism as the Gate A limb above.

Cost: vectorised throughout, no Python loop -- `isfinite` and `where`,
one shift, a divide, a subtract, a multiply, a square, one rolling mean,
a sqrt, a second divide and the `replace`, plus a shift only when
`offset != 0` -- so time and memory are linear in bars: a
traced peak of 5.1 MB at 100,000 bars and 20.4 MB at 400,000, identical on
two invocations. ⚠ The wall clock is disclosed and not claimed: roughly
4 ms and 17 ms for those two sizes on one machine
(`docs/SkRocwbRatioMeasured.md` §Z carries both runs).

Calculation:
    Default Inputs:
        length=20, band_length=5
    ROC   = 100 * (close / close.shift(length) - 1)
    band  = sqrt((ROC ** 2).rolling(band_length).mean())
    SK_ROCWB_RATIO = ROC / band     (+-inf -> NaN)

Args:
    close (pd.Series): Series of 'close's
    length (int): The ROC lookback. Default: 20
    band_length (int): Bars in the RMS band. Default: 5
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)

Returns:
    pd.Series: SK_ROCWB_RATIO_20_5, dimensionless, in [-sqrt(5), +sqrt(5)]
"""
