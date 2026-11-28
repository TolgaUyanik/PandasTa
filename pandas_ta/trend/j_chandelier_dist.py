# -*- coding: utf-8 -*-
import numpy as np
from pandas import Series, concat

from pandas_ta.overlap.wilder_rma import wilder_rma
from pandas_ta.utils import get_offset, verify_series

#: The Chandelier Exit's two numbers, as PandasTa issue #122 states them:
#: "long (22, 3)". They are module constants rather than arguments, for the
#: same reason as `pandas_ta/trend/j_safezone_dist.py`'s and
#: `pandas_ta/volatility/j_damiani.py`'s: the issue's quote
#: (`chande.py: HH22 - 3*ATR22`) and the screen prototype
#: (`docs/issues/screen/ind_screen_r2.py`, candidate `j_chandelier_dist_22`)
#: spell exactly these two, and that one pair is the whole of what the
#: 2026-10-24 screen measured at Gate E. A `period=`/`mult=` surface would
#: ship parameter combinations nothing has measured, and the Gate E ledger
#: refuses a run taken at non-default parameters anyway
#: (`docs/gate_e_ledger.py`).
PERIOD = 22
MULT = 3.0

#: Bars a frame must have before the function computes at all, and
#: `MIN_BARS - 1` is also the index of the first bar that can fire on a
#: clean frame. The binding leg is the ATR, not the highest high: the true
#: range has no bar 0 (it needs a previous close), so Wilder's seed is the
#: mean of true ranges 1 .. PERIOD and lands at index PERIOD, one bar after
#: `high.rolling(PERIOD).max()` is ready at index PERIOD - 1. Pinned by
#: `tests/test_j_chandelier_dist.py::
#: test_a_frame_shorter_than_min_bars_is_refused`.
MIN_BARS = PERIOD + 1


def _true_range(high, low, close):
    """`max(high - low, |high - prev close|, |low - prev close|)`, with bar
    0 UNDEFINED.

    Spelled here rather than imported from `pandas_ta.volatility.true_range`,
    and that is a decision with a measurement behind it -- the same decision
    `pandas_ta/volatility/j_damiani.py::_true_range` took, for the same
    reason. This fork's `true_range` routes its `high - low` leg through
    `utils.non_zero_range`, which adds `sys.float_info.epsilon` to EVERY bar
    of the series as soon as ONE bar has `high == low`. That epsilon is an
    ABSOLUTE quantity, so it does not scale with the price.

    ⚠ And §A4(e) of `docs/JChandelierDistMeasured.md` measures BOTH halves
    of that rather than asserting the obvious one. On the six varying test
    frames -- none of which has a single `high == low` bar -- a
    `true_range`-based variant is BIT-EQUAL to this module, so the copy
    buys nothing there. What it buys is Gate D on the frames where the
    epsilon survives: on a frame with a doji every seventh bar the variant
    is already not bit-identical under x8 at a price level of 100, and on
    that frame and on a flat one at a level of 1e-6 it fails x8 and x64
    both. This module holds in all eight of those cells.

    Bar 0 is NaN rather than `high[0] - low[0]`, which is TA-Lib's
    `TRANGE` (lookback 1). That is RUN rather than recalled: §A5 measures
    this function BIT-EQUAL to `talib.TRANGE` on the `walk` frame, both
    first firing at index 1. It is also what makes Wilder's seed below
    average true ranges 1 .. PERIOD rather than 0 .. PERIOD - 1, and §A5
    measures `talib.ATR(22)` first firing at index 22 and agreeing with
    `wilder_rma(tr, 22)` to 1.110e-15.
    """
    prev = close.shift(1)
    ranges = concat([high - low, (high - prev).abs(), (low - prev).abs()],
                    axis=1)
    # `max(axis=1)` skips NaN, so without this line bar 0 would read
    # `high - low` -- the screen prototype's reading, which seeds the ATR a
    # bar earlier and with one more observation (§A4(a)).
    tr = ranges.max(axis=1)
    tr.iloc[:1] = np.nan
    return tr


def j_chandelier_dist(high, low, close, offset=None, **kwargs):
    """Indicator: distance to the Chandelier Exit, long (J_CHANDELIER_DIST)"""
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
    # `high`, `low` and the close INSIDE the true range only have to be
    # FINITE. They enter through differences and a maximum, which are
    # meaningful at any finite level.
    # ⚠ All three are LOAD-BEARING on an infinite input, and the measured
    # difference is in the VALUES rather than in the NaN mask -- which is
    # why §G2 prints `differ` and `max |abs|` next to its `fired` and `inf`
    # columns, and why an earlier draft of this comment was wrong. With the
    # guard the bad leg is NaN and `max(axis=1)` SKIPS it, so the true
    # range is the largest SURVIVING leg and the ATR takes it; without the
    # guard the leg is infinite, so the true range is infinite and a pandas
    # window DROPS that observation entirely (§G3 probes that behaviour
    # directly). Two different ATRs from bar T onward, with the same
    # fired-bar count either way. Measured on a `walk` with one +inf
    # planted at bar 700: removing the high guard moves 636 bars by up to
    # 3.463e-04, the low guard 664 by 1.112e-03, the close guard 663 by
    # 1.118e-03 -- and 634 / 662 / 664 bars under numpy's reduced CPU
    # dispatch, so the counts are dispatch-dependent and the test asserts
    # the shape (`> 300` bars, `> 1e-5`). A planted NaN is unaffected,
    # because the guard only maps a non-finite value to the NaN it already
    # is.
    #
    # The close as the DIVISOR must also be positive and normal, and THAT
    # guard is not decoration: §G2 measures a close of -50 shipping a
    # sign-flipped reading without it. A zero or subnormal close makes the
    # ratio overflow; a negative one silently flips the column's sign. Same
    # guard, same reasons, as the siblings that divide by a price
    # (`trend/j_safezone_dist.py`, `statistics/tf_iqr_ret_60.py`,
    # `statistics/ts_q05_60.py`).
    hi = high.astype(float)
    hi = hi.where(np.isfinite(hi))
    lo = low.astype(float)
    lo = lo.where(np.isfinite(lo))
    cl = close.astype(float)
    cl = cl.where(np.isfinite(cl))
    px = cl.where(cl >= np.finfo(float).tiny)

    # The Chandelier Exit for a LONG position, as issue #122 quotes it:
    # "chande.py: HH22 - 3*ATR22".
    #
    # ⚠ `ATR22` is read as WILDER's average true range -- seeded with the
    # mean of the first PERIOD true ranges, then recursed at
    # `alpha = 1 / PERIOD`. Two things support that reading and both are
    # checkable from here: Wilder's own 1978 specification, and TA-Lib's
    # `ATR`, which is what a bare "ATR" conventionally names and which this
    # worktree can RUN (§A2 does). It is NOT this fork's `rma` (pandas'
    # `adjust=True`) and NOT the screen prototype's bare
    # `ewm(alpha=1/22, adjust=False)` seeded at bar 0. All three are
    # different columns on the warm-up and all three are measured in
    # `docs/JChandelierDistMeasured.md` §A4. `wilder_rma` is the fork's own
    # spelling of Wilder's smoothing and is imported rather than retyped,
    # as `pandas_ta/trend/vstop.py` imports it.
    tr = _true_range(hi, lo, cl)
    atr = wilder_rma(tr, length=PERIOD)
    if atr is None:
        # `wilder_rma` refuses a series with no NaN-free window of PERIOD
        # bars -- an all-NaN frame, or one whose every window holds a hole.
        # An empty column is the right answer there, not an exception.
        atr = Series(np.nan, index=cl.index, dtype=float)

    # "HH22": the highest high of the last PERIOD bars, bar T INCLUDED.
    # ⚠ Both legs read bar T, and that is the Chandelier Exit rather than a
    # look-ahead: the stop is recomputed on every bar from the bars that
    # have closed, and a trader standing at T has T's own high, low and
    # close. Nothing here reads T + 1; `tests/test_j_chandelier_dist.py`
    # carries a 36-offset future sweep and six mutants to say so.
    # `min_periods=PERIOD` is pandas' default for this window and is spelled
    # out because it is load-bearing: one NaN high blanks PERIOD bars of
    # output rather than being skipped.
    hh = hi.rolling(PERIOD, min_periods=PERIOD).max()
    stop = hh - MULT * atr

    # The scale-free form the issue specifies: `(close - stop) / close`.
    # Not the stop level, which is a price and so not a feature (CLAUDE.md,
    # "Scale-free"). Positive while the close is above its Chandelier Exit;
    # negative once the exit has been passed.
    dist = (px - stop) / px
    # ⚠ Defence in depth, and §G3 measures that it is NOT a no-op. Finite
    # inputs leave THREE arithmetic routes to an infinity, not one, and §G3
    # runs all three with their intermediates rather than reasoning about
    # them, numbered there in the order they occur in the chain:
    # (1) overflow in the true range's `high - prev close`, which needs a
    # high near +DBL_MAX against a close near -DBL_MAX -- legal here,
    # because the finite guards do not demand an ordered bar;
    # (2) overflow in `hh - MULT * atr`, a huge ATR times three;
    # (3) overflow in THIS division, a stop near 1e300 over a close near
    # 1e-300.
    # Measured on three 120-bar frames, with this line removed: route 1
    # ships 0 infinite readings, route 2 ships 97 and route 3 ships 98
    # (§G3 prints the frame length beside the counts). Route 1 is
    # absorbed for the same reason the input guards are quiet -- a pandas
    # window operation turns the infinite true range into a NaN before
    # smoothing it -- which is a DIFFERENT absorption from the one
    # `j_safezone_dist` found in pandas' compensated `rolling.sum`, and
    # there is no rolling sum in this chain at all.
    dist = dist.where(np.isfinite(dist))

    # Offset
    if offset != 0:
        dist = dist.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        dist.fillna(kwargs["fillna"], inplace=True)

    # Name and Categorize it
    dist.name = f"J_CHANDELIER_DIST_{PERIOD}_{MULT}"
    dist.category = "trend"

    return dist


j_chandelier_dist.__doc__ = \
"""Distance to the Chandelier Exit, long (J_CHANDELIER_DIST)

How far the close stands above the long Chandelier Exit, in fractions of
the close. The exit trails the 22-bar highest high by three Wilder ATRs.

    tr[T]   = max(high - low, |high - close[T-1]|, |low - close[T-1]|)
    atr[T]  = Wilder(tr, 22)                       SMA-seeded at tr[1..22]
    stop[T] = max(high[T-21..T]) - 3 * atr[T]
    J_CHANDELIER_DIST[T] = (close[T] - stop[T]) / close[T]

Source: jesse indicators (MIT), `chande.py`, as PandasTa issue #122 quotes
it: "chande.py: HH22 - 3*ATR22"; the issue also names Skender
Stock.Indicators' `Chandelier` for the same formula. The underlying rule is
Chuck LeBeau's Chandelier Exit.
⚠ Neither jesse nor Skender is installed in this worktree and web access is
unavailable, so Gate A does not read either library's source
(`tests/test_j_chandelier_dist.py::test_the_source_libraries_are_not_
installed_here` records that, so the claim cannot rot into "checked against
jesse"). What Gate A checks is the formula issue #122 quotes, spelled three
independent ways, and the attribution is to the issue's QUOTE rather than to
jesse's code. The issue itself says of the library: "existence, not
evidence".
⚠ **And nothing below is a statement about what jesse's or Skender's code
says.** Which smoother each library calls, and which series it takes the
highest high over, is not checkable here, so those are not claimed: the
reading of `ATR22` as Wilder's rests on Wilder's 1978 specification and on
TA-Lib's `ATR`, the conventional meaning of a bare "ATR", which this
worktree can RUN. An earlier draft of this docstring quoted jesse's array
indexing from memory four lines after pinning a test to stop exactly that.
⚠ The LONG exit only: issue #122 names the long side and the screen
measured only the long candidate, so no short-side column has a Gate E
figure. Whether either library's function also takes a short direction is
not checkable here and is not claimed.

**Gate A is the issue's formula, spelled independently, and TA-Lib is the
third speller.** A bar-by-bar oracle -- its own true-range loop, its own
SMA seed, its own Wilder recursion over plain Python floats, its own
22-bar running maximum, sharing no code with the module -- agrees with this
module on 1,478 of 1,478 fired bars of each of six varying frames, with
identical NaN masks, to 2.5e-16 absolute and 4.3e-12 relative. NOT
bit-equal, and the reason is named in §A1: pandas' `ewm(adjust=False)`
re-associates Wilder's step, and re-associating it by hand in the oracle
moves it by the same 2.5e-16. The assertions are 1e-12 absolute and 1e-9
relative, both of which a reduced numpy kernel also clears.
`talib.MAX(high, 22) - 3 * talib.ATR(high, low, close, 22)` -- the quote's
two operators as TA-Lib spells them -- is the same column to 2.4e-16
absolute on all six frames at Spearman 1.0000 (talib 0.7.1); the test skips
rather than passing silently where talib is absent.

⚠ **WHICH ATR is the load-bearing reading of this formula, and the
alternatives are different columns on the warm-up.** This module reads
`ATR22` as Wilder's, SEEDED with the mean of the first 22 true ranges --
Wilder's 1978 specification, and what TA-Lib's `ATR` computes -- and uses
`wilder_rma`, the fork's own spelling of that. Measured (§A4), over the six
varying frames:
    * the SCREEN PROTOTYPE's `ewm(alpha=1/22, adjust=False)` from bar 0
      disagrees on 655 .. 722 of the 1,478 shared bars, by up to 2.0e-02,
      and the last bar it disagrees on is 732 .. 808 (717 .. 873 under
      numpy's reduced CPU dispatch) -- the seeds differ and the recursion
      forgets at `(21/22)^k`. It also fires one bar
      earlier, because it needs no seed window. Spearman 0.9989 .. 1.0000;
    * this fork's `rma` (`adjust=True`) disagrees on 779 .. 961 bars by up
      to 5.9e-03, and a plain `SMA(tr, 22)` on 1,477 of 1,478 by up to
      2.8e-02 at Spearman 0.9662 .. 0.9974;
    * `HH22` taken over the CLOSE rather than the high disagrees on
      1,474 .. 1,478 of the shared bars (and on 1,294 of 1,478 of the
      doji frame §A4 adds to the six) by up to 4.5e-03.
⚠ That is also the one caveat on the screen's Gate E figures below: they
were measured on the prototype's ATR, not on this one.

Causal: bar T reads `high` and `low` up to T and `close` up to T. Nothing
later. Measured by a 36-offset future-perturbation sweep (0 of 36 on each
of six frames) and by six look-ahead mutants read off this file, edited and
`exec`'d in memory, each live and caught on 11 to 36 of those 36 offsets of
each of three frames, the first catch moving a bar by 6.3e-04 .. 3.3e-02.
⚠ A count below 36 is the FORMULA's, not a gap in the mutant: `hh` is a
22-bar MAXIMUM, so leading it by a bar changes nothing at the offsets
where the perturbed bar is not the one it selects.
⚠ **And the sweep has a blind spot this module states rather than leaves
for a reader to find.** An edit that drops the `shift(1)` in the true
range makes bar T's range read bar T's OWN close instead of yesterday's --
wrong, but not a look-ahead, because it reads no later bar. Three such
edits are measured in §B2, all three caught 0 of 36 by the sweep and all
three caught by Gate A's oracle, which they miss by 2.0e-02 .. 3.1e-01.
That is why Gate B here is the sweep AND the oracle.

Scale-free by construction: every step up to `stop` is homogeneous of
degree 1 in the price, and the final division cancels the factor, so a
x8/x64 rescale is bit-identical on 1,478 of 1,478 bars of each of six
frames and at price levels 1e-6, 1e+6 and 1e+100. x10/x3.7/x0.1/
x1.0000001 round: the measured worst of 24 cells is 2.467e-11 and the test
asserts 1e-9 rather than the digits, because that figure moves between
numpy CPU dispatches. A level SHIFT of +10 moves all 1,478 fired bars of
every one of the six, so the bit-identity is a real check and not a vacuous
one.

⚠ **Bounded ABOVE, unbounded below, and the sign is the signal.** On
well-formed OHLC (`close <= high`, which this module does not enforce) the
close is at most the 22-bar high, so the column is at most
`3 * atr / close` and cannot run away upward; it goes NEGATIVE exactly when
the close has fallen
more than three ATRs below that high, which is what the Chandelier Exit is
for, and a collapse can take it arbitrarily far. Measured over the 8,868
fired bars of the six frames: -0.3163 .. 0.0639, negative on 3,759 of them
and exactly 0.0 on none (§C1). ⚠ A flat frame reads exactly 0.0 on all
1,478 of its fired bars, so this column is CONSTANT there rather than
blank (§C2) -- the stop is the high and the high is the close.

⚠ **Gate E on the PROTOTYPE was DISCLOSE_GAP** -- max |rho| 0.8606 vs the
manifest's `Range_Pos_20` over 89 BIST frames (n = 396,980), top-five
per-frame max median 0.8759, inside the 0.80 .. 0.90 band. The next
comparators were `ICHI_PRICE_VS_KIJUN` 0.8485 and `bias` 0.8438. The port's
own Gate E run is what decides its band, and it is PENDING: the launcher
runs it after this session (§E of `docs/JChandelierDistMeasured.md`).
⚠ **What it is nearest to in the fork is `cksp`, and the figure is above
the 0.90 line.** The Chande Kroll Stop's long leg is `HH(10) - 3*ATR(10)`
run through a second 20-bar maximum -- the same family -- and the distance
from the close to it reaches a per-frame median |rho| of 0.9320 over the
six varying frames, ahead of a retyped `Range_Pos_20` at 0.9181, `bias`'s
`BIAS_SMA_26` at 0.9150 and `ichimoku_ml`'s `ICHI_PRICE_VS_KIJUN` at
0.9115 -- the whole top four, in order (§L). Two things keep that
from being a verdict: `cksp` ships the price LEVEL, which the ML contract
does not treat as a feature, so the column measured against does not exist
in the fork; and six synthetic frames read HIGH -- on the one comparator
with both a synthetic and a real figure, the synthetic median is 0.0575
above the screen's real 0.8606. §L is a disclosure, not a gate.

Cost: one `concat` of three legs, one `rolling` max, one Wilder EWMA, two
shifts and one division. Linear in bars. ⚠ The wall-clock figures live in
`docs/JChandelierDistMeasured.md` §Z and nowhere else, including here:
they are one machine's and one run's.

Calculation:
    Default Inputs:
        period=22, mult=3.0  -- module constants
    tr      = max(high - low, |high - close[1]|, |low - close[1]|), tr[0] NaN
    atr     = wilder_rma(tr, 22)
    stop    = high.rolling(22).max() - 3.0 * atr
    J_CHANDELIER_DIST = (close - stop) / close

Args:
    high (pd.Series): Series of 'high's
    low (pd.Series): Series of 'low's
    close (pd.Series): Series of 'close's
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)

Returns:
    pd.Series: J_CHANDELIER_DIST_22_3.0, a fraction of the close
"""
