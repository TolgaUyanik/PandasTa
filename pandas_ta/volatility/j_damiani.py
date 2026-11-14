# -*- coding: utf-8 -*-
import numpy as np
from pandas import Series, concat

from pandas_ta.utils import get_offset, verify_series

#: The two true-range lookbacks of the issue's quote, and nothing else is
#: configurable: issue #105 quotes jesse's `damiani_volatmeter` as
#: "vol = ATR13/ATR40 + 0.5*(vol[-1] - vol[-3])", and the screen prototype
#: (`docs/issues/screen/ind_screen.py`, candidate `j_damiani`) spells those
#: same two numbers. They are module constants rather than arguments because
#: that quote and that prototype are the whole of what the 2026-10-24 screen
#: measured at Gate E; a `fast=`/`slow=` surface would ship parameter
#: combinations nothing has measured.
FAST = 13
SLOW = 40

#: The feedback loop: `vol[T] = base[T] + LAG_S * (vol[T-NEAR] - vol[T-FAR])`.
#: `LAG_S` is the issue's 0.5, `NEAR`/`FAR` its `vol[-1]`/`vol[-3]`. All three
#: are load-bearing and none is a free parameter -- `docs/JDamianiMeasured.md`
#: §A5 measures what the loop does to the column (it is a stable resonant IIR,
#: largest pole modulus 0.872175, peak gain 3.6742 at a period of 7.47 bars)
#: and what dropping it costs (Spearman 0.8978 .. 0.9322 against the bare ATR
#: ratio over six frames, so the loop reshapes the column without
#: re-ranking it).
LAG_S = 0.5
NEAR = 1
FAR = 3

#: Bars a frame must have before the function computes at all: the longer
#: ATR's length plus the loop's reach. This is a floor on the INPUT, not the
#: warm-up -- both EWMAs are seeded at bar 0, so the column's only NaNs on a
#: clean frame are the loop's first `FAR` = 3 bars, and a 43-bar frame fires
#: on 40 of them. Pinned by
#: `tests/test_j_damiani.py::test_a_frame_shorter_than_min_bars_is_refused`.
MIN_BARS = SLOW + FAR


def _true_range(high, low, close):
    """`max(high - low, |high - prev close|, |low - prev close|)`.

    Spelled here rather than imported, and that is a decision with a
    measurement behind it: this fork's `true_range` (and therefore its
    `atr`, `natr` and `chop`) differs from the issue's `ATR` in two ways
    that both move this column. It routes `high - low` through
    `non_zero_range`, which adds an epsilon to EVERY bar of the series as
    soon as ONE bar has `high == low`, and it NaNs bar 0. The screen
    prototype spells the plain three-way max, with bar 0's range as its
    first observation, and `docs/JDamianiMeasured.md` §A4(d) prices the
    difference rather than assuming it is negligible.
    """
    prev = close.shift(1)
    ranges = concat([high - low, (high - prev).abs(), (low - prev).abs()],
                    axis=1)
    # `max(axis=1)` skips NaN, so bar 0's true range is `high - low`: the
    # two gap legs need a previous close and bar 0 has none. That is the
    # prototype's warm-up and it is why both ATRs are defined from bar 0.
    return ranges.max(axis=1)


def _atr(true_range, length):
    """Wilder's `alpha = 1 / length` EWMA, seeded at the first observation.

    `ewm(alpha=1/length, adjust=False)` -- the screen prototype's spelling
    of "ATR" and the usual reading of the issue's `ATR13`/`ATR40`.
    ⚠ jesse's own smoother is NOT read here: jesse is not installed in this
    worktree and web access is unavailable, so nothing in this module is
    evidence about what jesse's code does
    (`tests/test_j_damiani.py::test_the_source_library_is_not_installed_here`
    records that, so the claim cannot rot into "checked against jesse").
    ⚠ It is NOT this fork's `rma` (pandas' default `adjust=True` with
    `min_periods=length`), and NOT `wilder_rma`/Pine's `ta.rma` (seeded with
    `SMA(x[:length])`). Both are different columns here and both are
    measured: `docs/JDamianiMeasured.md` §A4.
    """
    return true_range.ewm(alpha=1.0 / length, adjust=False).mean()


def _volatmeter(base):
    """`vol[T] = base[T] + 0.5 * (vol[T-1] - vol[T-3])`, as the issue quotes.

    A Python loop over a numpy array, because the recursion reads its own
    two earlier outputs and pandas has no vectorised form of it. Linear in
    bars -- `docs/JDamianiMeasured.md` §Z times it.

    Two conventions, both the prototype's and both measured rather than
    argued (§G6):

    * a missing predecessor counts as 0.0, so the loop starts at bar 0
      instead of waiting three bars. The first `FAR` bars are computed and
      then masked out by the caller, but they are not discarded: they are
      what bar 3 recurses from.
    * a bar whose `base` is NaN emits NaN and is SKIPPED -- the loop does
      not carry a previous value across it -- so the bars after it would
      recurse from 0.0 again. ⚠ On this module's `base` that branch only
      ever runs on a LEADING run of bars: `base` is NaN while the slow
      ATR is still exactly 0, and a Wilder EWMA of non-negative
      observations that is positive once stays positive. §G6 measures
      that on all eight frames, on a 32,000-bar frame engineered so the
      smoothers underflow (they STALL above zero rather than reaching
      it, §G5(c)), and on a frame whose NaN run has to END mid-series
      (103 bars, still a prefix). A mid-series bad price does not reach
      it either: pandas' `ewm` skips a NaN observation, so the ATRs
      carry through it and `base` stays defined (§G1).
    """
    # Python floats, not a numpy array, and the NaN test is `x != x` rather
    # than `np.isnan(x)`: on a numpy scalar that call costs more than all
    # the arithmetic around it, and this loop runs once per bar. §Z times
    # both spellings at 400,000 bars and shows their outputs bit-identical;
    # the obvious one is 13 to 15 times slower over four runs (the digits
    # live there, because they move between runs).
    values = base.tolist()
    out = [np.nan] * len(values)
    for i, value in enumerate(values):
        if value != value:                                      # NaN
            continue
        near = out[i - NEAR] if i >= NEAR else np.nan
        far = out[i - FAR] if i >= FAR else np.nan
        out[i] = value + LAG_S * ((near if near == near else 0.0)
                                  - (far if far == far else 0.0))
    return np.asarray(out, dtype=float)


def j_damiani(high, low, close, offset=None, **kwargs):
    """Indicator: Damiani Volatmeter, volatility line (J_DAMIANI)"""
    # Validate Arguments
    high = verify_series(high, MIN_BARS)
    low = verify_series(low, MIN_BARS)
    close = verify_series(close, MIN_BARS)
    offset = get_offset(offset)

    if high is None or low is None or close is None: return

    # Calculate Result
    true_range = _true_range(high, low, close)
    fast, slow = _atr(true_range, FAST), _atr(true_range, SLOW)
    # ONE guard, and it is on the divisor only. `slow` is an EWMA of
    # non-negative true ranges, so it is 0 exactly when every true range so
    # far rounds to 0, and NaN is the right answer there: the ratio of two
    # zero volatilities has no value. Two things the guard buys, both
    # measured rather than argued:
    #   * on every frame with a real price scale it changes NOTHING -- it is
    #     bit-equal to the bare division, and to the prototype's
    #     `_fin(a / b)`, on all eight frames (§A2) -- and what it buys there
    #     is that the `0 / 0` is decided HERE instead of inside pandas.
    #     Measured (§G3): numpy raises `FloatingPointError` on that division
    #     under `errstate(all="raise")` and today's pandas suppresses the
    #     flag itself, so without this `where` the module's documented
    #     behaviour would rest on a pandas internal.
    #   * at SUBNORMAL scale it is the only thing between this column and an
    #     `inf`. A true range of a few ulps rounds `slow` to exactly 0 while
    #     `fast` stays at 1 ulp, and the unguarded form then reads `inf`
    #     (§G5(d), measured on 300 bars of eight such frames). That is also
    #     why nothing guards the division's RESULT: this guard has already
    #     removed the only reachable infinity, and an infinite or
    #     overflowing price cannot make another -- it makes the true range
    #     `inf`, and pandas converts that to NaN before the `ewm` kernel,
    #     which skips it (§G2).
    # ⚠ The ratio's own bound is `SLOW / FAST` = 40/13 = 3.0769..., because
    # both ATRs are weighted means of the SAME true ranges with weights
    # summing to 1. §A5(e) measures it attained to within 1 ulp and not
    # exceeded on any frame at a real price scale; §G5(d) measures the
    # subnormal regime exceeding it (`base` = 5.0 at a 59-ulp true range),
    # because subnormal multiplication rounds absolutely and the weight
    # argument has no force there.
    base = fast / slow.where(slow > 0.0)
    vol = Series(_volatmeter(base.to_numpy(dtype=float)), index=close.index)
    # The loop's own warm-up: `vol[-3]` does not exist before bar `FAR`, so
    # the first three bars are a reading of a shorter formula. They are
    # masked rather than shipped -- and the mask is on `base`, not on the
    # bar count, so a frame that starts without movement is masked until
    # three bars after its first moving one (bar 53 of a frame flat for 50,
    # measured) rather than until bar 3.
    vol = vol.where(base.shift(FAR).notna())

    # Offset
    if offset != 0:
        vol = vol.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        vol.fillna(kwargs["fillna"], inplace=True)

    # Name and Categorize it
    vol.name = f"J_DAMIANI_{FAST}_{SLOW}"
    vol.category = "volatility"

    return vol


j_damiani.__doc__ = \
"""Damiani Volatmeter, volatility line (J_DAMIANI)

Short-term true range over long-term true range, run through a three-bar
feedback loop: how far volatility stands above its own slower level.

    TR       = max(high - low, |high - close[-1]|, |low - close[-1]|)
    ATR(n)   = TR.ewm(alpha=1/n, adjust=False).mean()
    base     = ATR(13) / ATR(40)
    J_DAMIANI[T] = base[T] + 0.5 * (J_DAMIANI[T-1] - J_DAMIANI[T-3])

Source: jesse indicators (MIT), `damiani_volatmeter`, as PandasTa issue
#105 quotes it: "vol = ATR13/ATR40 + 0.5*(vol[-1] - vol[-3])".
⚠ jesse is NOT installed in this worktree and web access is unavailable,
so Gate A does not read jesse's own source
(`tests/test_j_damiani.py::test_the_source_library_is_not_installed_here`
records that). What Gate A checks is the formula the issue quotes,
spelled two independent ways, and the attribution is to the issue's QUOTE
rather than to jesse's code.
⚠ One column, not two. The issue's title and its quote name the
VOLATILITY line, which is what ships. Whether jesse's own
`damiani_volatmeter` also returns a threshold line is not something this
worktree can see, and no threshold line was screened at Gate E.

**Gate A is the formula, spelled two ways.** A hand-written true range, a
hand-written Wilder recursion and a hand-written feedback loop -- sharing
no code with this module -- agree with it on 1,497 of 1,497 fired bars of
each of six varying synthetic frames, measured BIT-equal; the test asserts
a 1e-12 bound instead, because pandas' `ewm` divides by `(1 - a) + a` and
an independent spelling is not obliged to round the same way. The screen
prototype, which shares pandas' `ewm`, is asserted bit-equal on all eight
frames -- the same operations in the same order, so that limb is
machine-independent, and it is what ties this port to the 2026-10-24
screen's Gate E figures.

⚠ **Gate E on the PROTOTYPE was DISCLOSE, not SHIP** -- max |rho| 0.7621
vs the engine's `ATR_Ratio_5_20` over 89 BIST frames (n = 397,069),
top-five per-frame max median 0.7639, in the 0.76 .. 0.80 band. The next
comparators were `natr_percentile` 0.7302 and `natr_Pctl` 0.7294. This
column answers a question the shipped set already answers at roughly
three quarters of the way: it is a fast-over-slow volatility ratio, and
so is `ATR_Ratio_5_20`. The port's own Gate E run is what decides its
band (§E of `docs/JDamianiMeasured.md`).
⚠ **What it is nearest to inside this fork, measured on synthetic
frames:** `natr` at |rho| <= 0.8362, then `chop` 0.3120, `volvol` 0.2614,
`massi` 0.2297, `atr_ma_multiple` 0.2186 and `rvi` 0.1871. The first of
those is above the 0.80 DISCLOSE_GAP line -- on SIX synthetic frames,
which is a disclosure and not a gate -- and `natr` is a volatility LEVEL
(ATR over close) where this is a ratio of two horizons. Note the screen's
own fork-overlap stage put `massi` nearest instead, at 0.7023 on 12 real
frames; the two universes disagree and neither is Gate E (§L).

⚠ **THE FEEDBACK LOOP IS A RESONATOR, and that is the one structural
thing to know about this column.** `vol[T] = base[T] + 0.5*(vol[T-1] -
vol[T-3])` is an IIR filter. It is stable -- the largest pole modulus is
0.872175, measured, so an impulse decays (1.0 at the impulse, 1.7e-01 by
+10 bars, 6.3e-04 by +50) -- but its gain is not flat: 1.000000 at DC and
at Nyquist, with a peak of 3.674235 at a period of 7.4705 bars. So the
column is NOT "the ATR ratio, smoothed": it leaves the mean level of the
ratio alone and amplifies roughly weekly volatility cycles by three and a
half times.
⚠ **What that does NOT do is re-rank the column**, and that is the
disclosure rather than the defence: against the bare `ATR(13)/ATR(40)`
ratio the shipped column reads Spearman 0.8978 .. 0.9322 over six frames
(no bar in common, max |diff| 0.40 .. 0.94). The loop reshapes; it does
not make this a different question from "fast volatility over slow".

**Bounded at any real price scale, and the bound is the ratio's.** Both
ATRs are weighted means of the SAME true ranges with weights summing to
1, so in exact arithmetic `base` cannot exceed the largest ratio of those
weights, which is at lag 0: `SLOW / FAST` = 40/13 = 3.076923. That
supremum is ATTAINED -- on a frame that is flat and then moves, the first
moving bar is the only non-zero true range, measured
3.0769230769230766, one ulp below 40/13 -- and it is the measured max
over all eight test frames. Through the loop's impulse response (sum of
positive taps 2.799187, of negative taps -1.799187) the column then lies
in (-5.5360, 8.6129). What the frames actually reach is narrower: over
8,982 bars of the six varying frames, 0.691678 .. 2.858073 with 8,977 of
them inside 0.25 .. 2.5 and 0 negative; `flat-start` reaches 3.628336.
⚠ **That is an EXACT-ARITHMETIC bound, and §G5(d) measures floating
point breaking it** -- at SUBNORMAL scale, not in the underflow stall
§G5(c) explores. A true range of 59 ulps smooths to 5 ulps and 1 ulp,
because subnormal multiplication rounds absolutely, so `base` reads
exactly 5.0 and the column 6.8750. The weight argument has no force
there. It is still nowhere near an overflow, and the divisor guard
removes the one `inf` that regime can produce (§G5(d)), which is why
nothing guards the division's result.

Causal: bar T reads `high`/`low` up to T, `close` up to T - 1, and its
own two earlier outputs. Nothing later. Measured by a 36-offset
future-perturbation sweep (0 of 36 on each of six frames) and by five
look-ahead mutants read off this file, edited and `exec`'d in memory,
each caught at 36 of 36 offsets on every frame.

Scale-free by construction: every step up to `base` is homogeneous of
degree 1 in the price, and the ratio cancels the factor, so a x8/x64
rescale is bit-identical on 1,497 of 1,497 bars of each of six frames,
on 1,447 of 1,447 of a frame that starts flat, and at price levels 1e-6,
1e+6 and 1e+100. x10/x3.7/x0.1/x1.0000001 round: measured max 2.098e-14
relative, asserted 1e-9.

⚠ **A frame with no movement at all reads NaN, not 0.0, and that is the
honest answer**: `ATR(40)` is 0 exactly when every true range so far is
0, and so is `ATR(13)`, so the ratio is `0 / 0` -- undefined rather than
zero. A flat frame therefore fires on 0 of its 1,500 bars (measured),
which is why Gate D's `0 < fires < n` is asserted on the six VARYING
frames and the flat one is pinned separately. The same mechanism makes a
flat PREFIX a leading NaN run: a frame flat for its first 50 bars fires
from bar 53, not bar 3 (measured).

**The NaNs are always a leading prefix** -- 3 bars on a clean frame, 53
on that flat-start one, measured contiguous-from-zero on all eight frames
and on a 32,000-bar adversarial one. A Wilder EWMA of non-negative
observations that is positive once stays positive, so `base` cannot go
NaN again after it is defined, and there are no mid-series holes.

⚠ **A bad price does NOT empty a bar here** -- measured 0 emptied, for
NaN and infinite highs, lows and closes planted at five different bars.
Two reasons, both measured rather than argued: the true range is a
three-way max that SKIPS a NaN leg, so one bad price still leaves it a
value; and `ewm` skips a NaN observation rather than poisoning the tail.
What a bad price does instead is perturb the column recursively -- it is
inside the two EWMAs -- so the claim is two-sided: bars BEFORE it stay
bit-identical, and the contamination decays with the slow filter's
memory. Worst over all six (leg, value) cells and all five plants:
6.5e-02 at the bar, 4.2e-03 by +50, 1.5e-03 by +100, 1.4e-05 by +300 --
the +-inf legs, except at +100 where the NaN close is worst by a hair
(1.482e-03 against 1.475e-03). The NaN legs are smaller elsewhere
(3.0e-02 high, 5.0e-02 low, 5.2e-02 close, at the bar).
⚠ An INFINITE price is not the same as a NaN, and the natural claim that
it is would have been wrong: `high - low` at an infinite high IS `inf`,
so it WINS the three-way max instead of being skipped by it. It still
never reaches the output -- pandas converts the infinity to NaN before
the `ewm` kernel, which then skips it, leaving 1,497 of 1,497 readings
finite -- but it is a different column from the NaN plant (up to 7.4e-02
apart, measured). The skip is a pandas BEHAVIOUR this module relies on,
pinned by a test so that an upgrade which stops doing it fails loudly
here rather than shipping an infinite feature.

⚠ **The warm-up is LONG, and that is a disclosure for the consumer.** The
column fires from bar 3, but what it reads for the first few hundred bars
still depends on where the ATR recursion was seeded. Against the
SMA-seeded reading of "ATR" (this fork's `wilder_rma`, Pine's `ta.rma`)
the max |diff| falls 6.0e-01 at bar 3 to 4.9e-02 by bar 100, 2.8e-05 by
bar 400 and 1.5e-09 by bar 800 on a walk whose own max |value| over the
1,458 bars the two share is 1.2597. Both the 40-bar memory and the loop's
resonance stretch that out.

Cost: two `ewm` passes, one three-way `max`, and one Python loop over the
bars. Linear in bars, with about half the time in the loop, and the loop
is written for speed rather than for looks -- Python floats and `x != x`
instead of a numpy array and `np.isnan`, which §Z measures as a factor of
13 to 15 over four runs, with bit-identical output. ⚠ The
millisecond and microsecond figures live in `docs/JDamianiMeasured.md` §Z
and nowhere else, including here: they are one machine's and one run's,
and so is anything divided by them.

Calculation:
    Default Inputs:
        fast=13, slow=40, lag_s=0.5, near=1, far=3  -- module constants
    TR           = max(high - low, |high - close[-1]|, |low - close[-1]|)
    ATR(n)       = TR.ewm(alpha=1/n, adjust=False).mean()
    base         = ATR(fast) / ATR(slow)
    J_DAMIANI[T] = base[T] + 0.5 * (J_DAMIANI[T-1] - J_DAMIANI[T-3])
                   with a missing earlier output counted as 0.0, and the
                   first 3 bars masked out.

Args:
    high (pd.Series): Series of 'high's
    low (pd.Series): Series of 'low's
    close (pd.Series): Series of 'close's
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)

Returns:
    pd.Series: J_DAMIANI_13_40, dimensionless
"""
