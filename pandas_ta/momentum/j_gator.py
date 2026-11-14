# -*- coding: utf-8 -*-
import numpy as np

from pandas_ta.utils import get_offset, verify_series

#: Bill Williams' three Alligator lines, each as `(SMMA length, forward lag)`.
#: Both numbers of each pair are the source's constants, not arguments: the
#: issue's quote of jesse's `gatorosc` is "jaw = SMMA(mid,13) lag 8,
#: teeth = SMMA(mid,8) lag 5, lips = SMMA(mid,5) lag 3". The issue's quote and
#: the screen prototype define these three pairings and no other; jesse's own
#: source is not read here (see the docstring). The lag is a FORWARD
#: displacement on a chart, which for a series means reading the smoothed
#: value `lag` bars BACK -- so it costs nothing in causality and buys the
#: whole indicator its meaning. `tests/test_j_gator.py` mutates each lag's
#: sign in turn and shows the mutant caught.
JAW = (13, 8)
TEETH = (8, 5)
LIPS = (5, 3)

#: Bars a frame must have before the function will compute at all: the longest
#: line's length plus its lag. The column itself first fires at bar
#: `JAW[1]` = 8 -- the EWMA is seeded at bar 0, so the only NaNs are the lag's
#: -- and this floor is therefore a sanity bound on the input rather than the
#: warm-up. `tests/test_j_gator.py::test_a_frame_shorter_than_min_bars_is_refused`
#: pins both halves of that sentence.
MIN_BARS = JAW[0] + JAW[1]


def _smma(mid, length, lag):
    """One Alligator line: `SMMA(mid, length)` displaced `lag` bars forward.

    SMMA here is read as Wilder's `alpha = 1 / length` with
    `adjust=False`, seeded at the first observation -- the screen
    prototype's spelling (`docs/issues/screen/ind_screen.py`, candidate
    `j_gator`: `mid.ewm(alpha=1 / n, adjust=False).mean()`) and the usual
    reading of the issue's `SMMA(mid,n)`.
    ⚠ jesse's own smoother is NOT read here: jesse is not installed in
    this worktree and web access is unavailable, so nothing in this module
    is evidence about what jesse's code does. The alpha rests on the
    issue's word "SMMA" and on the prototype Gate E measured -- and it
    MATTERS, unlike the seed: `docs/JGatorMeasured.md` §A4(c) measures the
    `alpha = 2/(n+1)` reading (a plain EMA) at Spearman 0.5165 .. 0.7075
    with 0 bars in common, against §A4(a)'s SMA-seeded variant at 0.9976
    .. 0.9998.

    ⚠ It is NOT this fork's `rma`, which is `ewm(alpha=1/length,
    min_periods=length)` at pandas' default `adjust=True` -- a different
    column, measured in `docs/JGatorMeasured.md` §A4 -- and it is not the
    SMA-seeded "smoothed moving average" of TradingView's `ta.rma`, which
    §A4 also prices.

    `shift(lag)` with `lag > 0` reads BACKWARDS in time, which is what a
    line "displaced 8 bars into the future" on a chart means for the value
    at bar T.
    """
    return mid.ewm(alpha=1.0 / length, adjust=False).mean().shift(lag)


def j_gator(high, low, close, offset=None, **kwargs):
    """Indicator: Bill Williams Gator Oscillator, scale-free (J_GATOR)"""
    # Validate Arguments
    high = verify_series(high, MIN_BARS)
    low = verify_series(low, MIN_BARS)
    close = verify_series(close, MIN_BARS)
    offset = get_offset(offset)

    if high is None or low is None or close is None: return

    # Calculate Result
    mid = (high + low) / 2
    # No guard on `mid`, and that is MEASURED rather than assumed: pandas'
    # own `_prep_values` turns an infinity into a NaN before the `ewm`
    # kernel sees it, and `ewm` SKIPS a NaN observation (carrying the
    # previous smoothed value) instead of poisoning the tail. So an `inf`
    # bar and a NaN bar give bit-identical columns and an infinite high or
    # low never reaches the output -- the only non-finite reading this
    # module can produce is the cross-scale division overflow of §G5,
    # which is unguarded on purpose. `docs/JGatorMeasured.md` §G3, pinned by
    # `tests/test_j_gator.py::test_an_infinite_price_never_reaches_the_output`
    # so that a pandas upgrade which stops doing it fails loudly here
    # rather than silently shipping an infinite feature.
    jaw = _smma(mid, *JAW)
    teeth = _smma(mid, *TEETH)
    lips = _smma(mid, *LIPS)
    # The divisor is what makes the column scale-free, so it is also the one
    # place a bad price can turn a reading into an infinity. A close that is
    # not finite, not positive, or subnormal (below `tiny`, where the
    # division overflows) empties its own bar and no other.
    c = close.where(np.isfinite(close) & (close >= np.finfo(float).tiny))
    gator = ((jaw - teeth).abs() - (teeth - lips).abs()) / c

    # Offset
    if offset != 0:
        gator = gator.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        gator.fillna(kwargs["fillna"], inplace=True)

    # Name and Categorize it
    gator.name = f"J_GATOR_{JAW[0]}_{TEETH[0]}_{LIPS[0]}"
    gator.category = "momentum"

    return gator


j_gator.__doc__ = \
"""Bill Williams Gator Oscillator, scale-free (J_GATOR)

Alligator jaw-teeth spread minus teeth-lips spread, over close: how much
more the SLOW pair of Bill Williams' lines has opened than the fast pair.

    mid     = (high + low) / 2
    jaw     = SMMA(mid, 13) displaced 8 bars
    teeth   = SMMA(mid, 8)  displaced 5 bars
    lips    = SMMA(mid, 5)  displaced 3 bars
    J_GATOR = (|jaw - teeth| - |teeth - lips|) / close

Source: jesse indicators (MIT), `gatorosc`, as PandasTa issue #104 quotes
it: "|jaw-teeth| - |teeth-lips|; jaw = SMMA(mid,13) lag 8, teeth =
SMMA(mid,8) lag 5, lips = SMMA(mid,5) lag 3". The `/ close` is the
fork's, from the screen prototype's scale-free form.
⚠ jesse is NOT installed in this worktree and web access is unavailable,
so Gate A does not read jesse's own source
(`tests/test_j_gator.py::test_the_source_library_is_not_installed_here`
records that, so the claim cannot rot into "checked against jesse").
What Gate A checks is the formula the issue quotes, spelled two
independent ways, and the attribution is to the issue's QUOTE rather
than to jesse's code.
⚠ One column, not two. The issue quotes a single DIFFERENCE, and that
is what ships; whether jesse's own `gatorosc` also returns the two
spreads apart is not something this worktree can see. The two spreads
the formula is built from were measured separately anyway, because
shipping them would have been the wider scope: over six synthetic
frames the difference reads 0.5398 .. 0.6468 against a scale-free
`|jaw - teeth|` and -0.0910 .. -0.5644 against `|teeth - lips|`, which
are themselves 0.3189 .. 0.7534 correlated -- two columns restating
each other more than either restates the difference
(`docs/JGatorMeasured.md` §L2).

**Gate A is the formula, spelled two ways.** A hand-written recursion
with hand-written lags agrees with this module on 1,492 of 1,492 fired
bars of each of seven frames -- measured BIT-equal, but
`tests/test_j_gator.py` asserts a relative bound of 1e-12, because
pandas' `ewm` divides by `(1 - alpha) + alpha` and an independent
spelling is not obliged to round the same way. The screen prototype,
which shares pandas' `ewm`, is asserted bit-equal: the same operations
in the same order.

**⚠ THE TEETH CANCEL whenever they are the outer line, and that is the
one structural thing to know.** If the teeth sit above both the jaw and
the lips, `|jaw-teeth| - |teeth-lips|` is `(teeth-jaw) - (teeth-lips)` =
`lips - jaw`; below both, `jaw - lips`. The oscillator is then the
JAW-LIPS spread and does not read the middle line at all -- measured on
0.0355 (a trending frame) to 0.2815 (a mean-reverting one) of fired
bars, bit-equal to that signed spread on every one of them. It is also
why the teeth look-ahead mutant is caught at only 5 of 36 perturbation
offsets on the trending frame: a future-reading teeth is outer on
0.9085 of bars there (§B1).

Causal: bar T reads `(high + low) / 2` up to bar T and `close[T]`,
nothing later. Measured by a 36-offset future-perturbation sweep (0 of
36 on each of six frames) and by five mutants in
`tests/test_j_gator.py`, read off this file, edited and exec'd. Four are
caught at 36 of 36 on every frame; the teeth one is carried by its
liveness (1,371 .. 1,453 of ~1,487 bars moved) and by a
mechanism-aware sweep that catches it at every offset the cancellation
leaves exposed -- 95 of 95 pooled (§B2).

Scale-free by construction: every step is linear in the price and the
final division cancels the factor, so a x8/x64 rescale is
bit-identical on 1,492 of 1,492 bars of each of seven frames and at
price levels 1e-6, 1e+6 and 1e+100.
⚠ x10, x3.7, x0.1 and x1.0000001 are not exact, and this column
AMPLIFIES the last bits: it is a difference of two differences of
nearby EWMAs, so a 1e-16 move in a price shows up as up to 6.5e-10 in
the column (9.2e-10 under numpy's AVX-512/AVX2/FMA3 dispatch
disabled). The tests pin 1e-7 and keep bit-equality only where the
operation sequence is identical by construction.

⚠ **The warm-up is the longest LAG and nothing else.** The EWMA is
seeded at its first observation, so the column fires from bar 8 -- bar
8's jaw is `SMMA(13)` of ONE bar. That transient is the source's and
the prototype's, and it is kept rather than NaN'd: against the
SMA-seeded reading of "SMMA" the max |diff| falls from 1.9e-3 at bar 8
to 2.0e-9 by bar 200 and 4.4e-16 by bar 400 of a 1,500-bar frame
(Spearman 0.9976 .. 0.9998 per frame; this fork's `rma`, pandas'
`adjust=True`, is a third reading at 0.9932 .. 0.9991). `MIN_BARS` = 21
is a floor on the INPUT, not the warm-up.
⚠ Those two are WARM-UP readings. The ALPHA is not: read as a plain EMA
(`alpha = 2/(n+1)`) the same formula is a different column -- Spearman
0.5165 .. 0.7075, 0 bars in common, max |diff| 2.5e-2 .. 7.2e-2 -- so
"SMMA" meaning Wilder's `1/n` is the load-bearing reading here, and it
rests on the issue's wording and on the prototype Gate E measured, not
on any reading of jesse's source (§A4(c)).

⚠ **What it is nearest to, in this fork, measured on synthetic frames:**
`ichimoku_ml`'s `ICHI_TK_CROSS_AGE` at |rho| <= 0.4910, then
`qqe:QQEs` 0.4291, `ichimoku_ml`'s `ICHI_TK_DIST` 0.4151, `chop`
0.3594, `natr` 0.2420 and `ao` 0.1942 -- `ao` being the other Bill
Williams oscillator over the same `(high + low) / 2`. The first of those is the fork's copy of the
screen's runner-up REAL-data comparator (0.3635 on 89 BIST frames
against this column's prototype), and all of them are far under the
0.76 ship line. Gate E on 687 engine comparators is what decides the
band (§L1, §E).

⚠ **Not bounded.** It is a spread difference over a price, and no bound
is claimed: over 10,444 bars of seven frames it spans -0.1240 ..
+0.0446, with |value| <= 0.1 on 10,443 of them. A FLAT price reads
exactly 0.0 on every bar -- all three lines coincide -- which is a
reading and not missing data.

NaN on the first 8 bars; and on any bar whose close is NaN, infinite,
zero, negative or subnormal -- such a close empties its own bar and no
other (measured: 1 bar each for NaN, 0.0, -1.0, +-inf and 1e-310, with
0 other bars moved). That guard is on the DIVISOR only, and what it
buys is measured: unguarded, a zero or subnormal close reads `inf` and
a NEGATIVE close reads a plausible-looking -0.4778.
⚠ A bad HIGH or LOW is different, because it is inside the filter: bars
before it stay bit-identical and the contamination decays with the
filter's memory (max |rel| 2.44 at the bar, 1.2e-1 by +50, 1.6e-3 by
+100, 1.5e-10 by +300). An INFINITE one needs no guard here and that is
measured rather than assumed -- pandas turns it into a NaN before the
`ewm` kernel, and `ewm` skips a NaN observation, so an inf bar and a
NaN bar give bit-identical columns with 0 non-finite readings. Both
legs are run, on both signs: `mid` is `(high + low) / 2`, so a bad low
has to behave like a bad high, and §G2/§G3 measure it rather than
inferring it.
⚠ NOT guarded, and stated rather than hidden: a frame whose high/low
and close live hundreds of orders of magnitude apart overflows the
division (52 of 60 bars infinite at high/low 1e+300 with close 1e-300).
That is bad data rather than a price.

Cost: three `ewm` passes and three `shift`s, no window and no Python
loop, so time and memory are linear in bars -- 4.1 .. 6.3 ms and a
traced peak of 6.4 MB at 100,000 bars, 20.4 .. 22.9 ms and 25.6 MB at
400,000. ⚠ No wall-clock figure is a claim outside
`docs/JGatorMeasured.md` §Z, and there only as a best-of-5 range over
two runs: they move between runs and machines.

Calculation:
    Default Inputs:
        jaw=(13, 8), teeth=(8, 5), lips=(5, 3)  -- module constants
    SMMA(x, n) = x.ewm(alpha=1/n, adjust=False).mean()
    mid        = (high + low) / 2
    J_GATOR[T] = (|SMMA(mid,13)[T-8] - SMMA(mid,8)[T-5]|
                  - |SMMA(mid,8)[T-5] - SMMA(mid,5)[T-3]|) / close[T]

Args:
    high (pd.Series): Series of 'high's
    low (pd.Series): Series of 'low's
    close (pd.Series): Series of 'close's, the scale-free divisor
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)

Returns:
    pd.Series: J_GATOR_13_8_5, dimensionless
"""
