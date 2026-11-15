# -*- coding: utf-8 -*-
import numpy as np

from pandas_ta.utils import get_offset, verify_series

#: The Awesome Oscillator's two window lengths and the signal length the
#: acceleration oscillator subtracts, in bars. All three are the source's
#: constants rather than arguments: the issue's quote of jesse's `acosc` is
#: "AO - SMA(AO,5), AO = SMA(mid,5)-SMA(mid,34)", which names 5, 34 and 5
#: and no other pairing. `tests/test_j_acosc.py` builds the column's name
#: out of them, so a change here fails the wiring test rather than renaming
#: a shipped column silently.
FAST = 5
SLOW = 34
SIGNAL = 5

#: Bars the column is NaN on at the head of a clean frame: `SLOW - 1` for
#: the slow SMA plus `SIGNAL - 1` for the signal SMA that averages it. The
#: two warm-ups ADD rather than overlapping, because the signal is a mean of
#: `AO` and not of the price -- the trap this constant exists to name.
#: Measured, not inferred: `tests/test_j_acosc.py::test_the_warmup_is_the_two_windows_added`
#: counts the NaNs on seven frames.
WARMUP = SLOW + SIGNAL - 2

#: Bars a frame must have before the function will compute at all: one more
#: than the warm-up, so the shortest accepted frame fires on exactly one bar.
#: `tests/test_j_acosc.py::test_a_frame_shorter_than_min_bars_is_refused`
#: pins both halves of that sentence.
MIN_BARS = WARMUP + 1


def _sma(x, length):
    """`SMA(x, length)` as the screen prototype spells it.

    `docs/issues/screen/ind_screen.py`'s helper is
    `def mean(x, n): return x.rolling(n).mean()` -- pandas' default
    `min_periods=n`, so the window must be FULL and a NaN inside it
    propagates. The signal leg relies on exactly that: `AO`'s own warm-up
    NaNs are what push the column's first fire out to `WARMUP`.

    ⚠ Spelled here rather than imported from `pandas_ta.overlap.sma`, which
    computes the same `rolling(length, min_periods=length).mean()` but also
    renames the series and re-validates it on every call. The two are
    asserted BIT-equal in `tests/test_j_acosc.py`, so this is a cost choice
    and not a divergence; `pandas_ta.momentum.ao` is checked the same way,
    since `AO` here is that shipped indicator's formula.
    """
    return x.rolling(length).mean()


def j_acosc(high, low, close, offset=None, **kwargs):
    """Indicator: Bill Williams Acceleration Oscillator, scale-free (J_ACOSC)"""
    # Validate Arguments
    high = verify_series(high, MIN_BARS)
    low = verify_series(low, MIN_BARS)
    close = verify_series(close, MIN_BARS)
    offset = get_offset(offset)

    if high is None or low is None or close is None: return

    # Calculate Result
    mid = (high + low) / 2
    # No guard on `mid`, and that is MEASURED rather than assumed: a
    # `rolling(...).mean()` window holding a NaN OR an infinity reads NaN,
    # so a bad high or low empties the 38 bars its windows reach and no
    # reading is non-finite. An infinite price and a NaN one give
    # bit-identical columns here -- unlike `j_gator`, whose `ewm` SKIPS the
    # observation and carries on. `docs/JAcoscMeasured.md` §G3, pinned by
    # `tests/test_j_acosc.py::test_an_infinite_price_empties_bars_like_a_nan`
    # so that a pandas upgrade which stops doing it fails loudly here
    # rather than silently shipping an infinite feature.
    ao = _sma(mid, FAST) - _sma(mid, SLOW)
    # The divisor is what makes the column scale-free, so it is also the one
    # place a bad price can turn a reading into an infinity. A close that is
    # not finite, not positive, or subnormal (below `tiny`, where the
    # division overflows) empties its own bar and no other.
    c = close.where(np.isfinite(close) & (close >= np.finfo(float).tiny))
    acosc = (ao - _sma(ao, SIGNAL)) / c

    # Offset
    if offset != 0:
        acosc = acosc.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        acosc.fillna(kwargs["fillna"], inplace=True)

    # Name and Categorize it
    acosc.name = f"J_ACOSC_{FAST}_{SLOW}_{SIGNAL}"
    acosc.category = "momentum"

    return acosc


j_acosc.__doc__ = \
"""Bill Williams Acceleration Oscillator, scale-free (J_ACOSC)

The Awesome Oscillator minus its own 5-bar mean, over close: how fast the
AO is moving rather than where it stands.

    mid      = (high + low) / 2
    AO       = SMA(mid, 5) - SMA(mid, 34)
    J_ACOSC  = (AO - SMA(AO, 5)) / close

Source: jesse indicators (MIT), `acosc`, as PandasTa issue #106 quotes it:
"acosc: AO - SMA(AO,5), AO = SMA(mid,5)-SMA(mid,34)". The `/ close` is the
fork's, from the screen prototype's scale-free form.
⚠ jesse is NOT installed in this worktree and web access is unavailable,
so Gate A does not read jesse's own source
(`tests/test_j_acosc.py::test_the_source_library_is_not_installed_here`
records that, so the claim cannot rot into "checked against jesse").
What Gate A checks is the formula the issue quotes, spelled three
independent ways, and the attribution is to the issue's QUOTE rather than
to jesse's code.

**Gate A is the formula, spelled three ways.** An oracle that re-sums
every window with `math.fsum` and shares no code with the module, the
screen prototype, and this fork's own shipped `ao` + `sma` all agree with
this module on 1,463 of 1,463 fired bars of each of seven synthetic frames
(10,241 pooled), with identical NaN masks. The prototype and the
`ao`/`sma` route are asserted BIT-equal -- same operations, same order --
while the `fsum` oracle is asserted as a bound, and the bound that matters
is the ABSOLUTE one: measured max |diff| 4.536e-16 against max |rel|
8.784e-11, because the column is a cancelling difference and its own
values run down to 1e-16 (the same two figures read 4.569e-16 and
3.336e-11 under reduced CPU dispatch). `tests/test_j_acosc.py` asserts
1e-14 absolute and 1e-9 relative.

⚠ **THE SUBTRACTION IS A HIGH-PASS FILTER, and that is the one structural
thing to know.** `AO - SMA(AO, 5)` is a linear FIR filter of `mid` with 38
taps whose |H(w)| is 0.000000 at DC, peaks at 0.673744 at a period of
11.4939 bars and falls to 0.160000 at Nyquist, so it is blind to the price
LEVEL and loudest on roughly fortnightly swings. ⚠ What that does NOT make
it is independent of `AO`: against `AO`'s own 1-bar change over close it
reads Spearman 0.8638 .. 0.9016 over six synthetic frames (against the
`AO / close` LEVEL, only 0.1187 .. 0.3026 -- the differencing is the whole
column). The screen measured the prototype at DISCLOSE_GAP anyway -- max
|rho| 0.8381 vs `FWMA_Slope_pct_Pctl`, n = 391,996, top-5 per-frame max
median 0.8431. Gate E on this port is what decides the band.

Causal: bar T reads `(high + low) / 2` up to bar T and `close[T]`, nothing
later. Measured by a 36-offset future-perturbation sweep (0 of 36 on each
of six varying frames) and by five look-ahead mutants in
`tests/test_j_acosc.py`, read off this file, edited and `exec`'d in memory;
every one is caught at 36 of 36 on each of those same six.
⚠ Six and not seven, and the reason is measured rather than argued: the
sweep multiplies bars >= J by 1.03, so a perturbed `flat` frame is a
two-level STEP and not a constant, and four of the five mutants ARE
caught on it at 36 of 36. The one that is not is `divisor-lead`, at 0 of
36 -- a constant price makes `AO` exactly 0.0 on every bar before the
perturbation, so mutating the DIVISOR alone moves nothing there. `flat`
is therefore excluded so that the gate is asserted at full strength
(5 of 5 mutants, 36 of 36) on six frames rather than at four-of-five on
seven. `docs/JAcoscMeasured.md` §B5.
Nothing cancels in this formula, so unlike `j_gator`'s teeth there is no
blind spot to work around.

Scale-free by construction: every step is linear in the price and the
final division cancels the factor, so a x8/x64 rescale is bit-identical on
1,463 of 1,463 bars of each of seven frames -- and the same x8/x64 run
REPEATED at price levels 1e-6, 1e+6 and 1e+100 is bit-identical on 1,463
of 1,463 there too. Across those three levels the column's max |value|
agrees to 3.9e-15 relative (4.4e-15 under reduced CPU dispatch) but is NOT
bit-equal, because 1e-6, 1e+6 and 1e+100 are not exact binary multiples
and the frame builder's `level * exp(...)` already differs in its last
bits.
⚠ x10, x3.7, x0.1 and x1.0000001 are not exact, and this column AMPLIFIES
the last bits: it is a difference of differences of nearby rolling means,
so a 1e-16 move in a price shows up as up to 1.812e-10 relative in the
column (1.886e-10 under numpy's AVX-512/AVX2/FMA3 dispatch disabled). The
tests pin 1e-7 and keep bit-equality only where the operation sequence is
identical by construction.

⚠ **The warm-up is the two windows ADDED, not the longer of them.** The
signal leg averages `AO`, not the price, so `AO`'s own 33 leading NaNs
push the column's first fire to bar 37 = `SLOW + SIGNAL - 2`. `MIN_BARS`
= 38 is a floor on the INPUT: a 37-bar frame returns `None` and a 38-bar
frame fires on exactly 1 bar.

⚠ **Not bounded.** It is a filtered price over a price, and no bound is
claimed: over 10,241 bars of seven frames it spans -0.1101 .. +0.1198,
with |value| <= 0.02 on 9,874 of them. A FLAT price reads exactly 0.0 on
all 1,463 of its fired bars -- both means of a constant are that constant,
so `AO` is exactly 0.0 -- which is a reading and not missing data.

NaN on the first 37 bars; and on any bar whose close is NaN, infinite,
zero, negative or subnormal -- such a close empties its own bar and no
other (measured: 1 bar each for NaN, 0.0, -1.0, +-inf and 1e-310, with 0
other bars moved). That guard is on the DIVISOR only, and what it buys is
measured: unguarded, a zero or subnormal close reads `inf` and a NEGATIVE
close reads a plausible-looking -0.771217.
⚠ A bad HIGH or LOW is different, and unlike `j_gator` it is NOT absorbed:
`mid` enters through `rolling(...).mean()`, which EMPTIES a window holding
a bad value instead of skipping the observation, so one bad bar empties
exactly the 38 bars its windows reach (measured: bars 700..737 for a plant
at 700) and no bar before it moves. An INFINITE high or low gives a
bit-identical column to a NaN one, on both legs and both signs, with 0
non-finite readings -- measured, not assumed.
⚠ And the part that is NOT bit-identical, disclosed rather than hidden:
bars AFTER the emptied run move too, by up to 9.486e-12 relative (662 of
them for that plant). That is pandas' rolling accumulator re-summing the
window from scratch once a NaN has passed through it, not contamination
from the bad bar.
⚠ NOT guarded, and stated rather than hidden: a frame whose high/low and
close live hundreds of orders of magnitude apart overflows the division
(23 of 23 fired bars infinite at high/low 1e+300 with close 1e-300). That
is bad data rather than a price.

Cost: three rolling passes, two divisions (`/ 2` for `mid` and `/ close`)
and one `where`, no Python loop, so time and memory are linear in bars --
a traced peak of 4.8 MB at 100,000 bars and 19.2 MB at 400,000, i.e. 4.0x
the memory for 4x the bars, both figures identical on all eight runs
`docs/JAcoscMeasured.md` §Z tabulates. ⚠ No wall-clock figure is quoted
here at all: those same eight runs put the TIME ratio for the same two
sizes anywhere between 3.66x and 4.54x, so §Z carries the milliseconds as
a disclosure and claims no digit of them.

Calculation:
    Default Inputs:
        fast=5, slow=34, signal=5  -- module constants
    SMA(x, n)  = x.rolling(n).mean()
    mid        = (high + low) / 2
    AO         = SMA(mid, 5) - SMA(mid, 34)
    J_ACOSC[T] = (AO[T] - SMA(AO, 5)[T]) / close[T]

Args:
    high (pd.Series): Series of 'high's
    low (pd.Series): Series of 'low's
    close (pd.Series): Series of 'close's, the scale-free divisor
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)

Returns:
    pd.Series: J_ACOSC_5_34_5, dimensionless
"""
