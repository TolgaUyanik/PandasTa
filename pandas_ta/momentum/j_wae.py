# -*- coding: utf-8 -*-
import numpy as np

from pandas_ta.overlap.ema import ema
from pandas_ta.utils import get_offset, verify_series

#: Waddah Attar Explosion's five numbers, as PandasTa issue #123 quotes
#: them: "t1 = (MACD20/40 - MACD20/40[1])*150, e1 = BB20,2 upper - lower".
#: They are module constants rather than arguments, for the same reason as
#: `pandas_ta/trend/j_chandelier_dist.py`'s and
#: `pandas_ta/momentum/j_acosc.py`'s: the issue's quote and the screen
#: prototype (`docs/issues/screen/ind_screen_r2.py`, candidate `j_wae`)
#: spell exactly these five, that one combination is the whole of what the
#: 2026-10-24 screen measured at Gate E, and `docs/gate_e_ledger.py` refuses
#: a Gate E run taken at non-default parameters anyway.
SENSITIVITY = 150
FAST = 20
SLOW = 40
CHANNEL = 20
MULT = 2.0

#: Bars a frame must have before the function computes at all, and
#: `MIN_BARS - 1` is also the index of the first bar that can fire on a
#: clean frame. The binding leg is the MACD's one-bar change, not the
#: Bollinger width: the SMA-seeded EMA of SLOW bars first fires at index
#: SLOW - 1, so its one-bar difference first fires at SLOW, while the
#: CHANNEL-bar standard deviation has been ready since index CHANNEL - 1.
#: Pinned by `tests/test_j_wae.py::test_a_frame_shorter_than_min_bars_is_
#: refused`.
MIN_BARS = SLOW + 1


def j_wae(close, offset=None, **kwargs):
    """Indicator: Waddah Attar Explosion power (J_WAE)"""
    # Validate Arguments
    close = verify_series(close, MIN_BARS)
    offset = get_offset(offset)

    if close is None: return

    # Calculate Result
    # One guard on the input, and §G1 prices it rather than assuming it:
    # what it buys depends on WHERE the bad close falls, and on only one
    # of the two legs.
    # An infinite close inside the first SLOW bars lands in an EMA SEED,
    # which is a mean, so without this line the seed is +/-inf; pandas then
    # SKIPS that seed as an observation and the recursion starts from a
    # raw close a bar later. Measured on a `walk` with one +inf at bar 10:
    # 649 of 1,460 bars differ by up to 1.120e+01 and one bar is lost
    # (1,459 against 1,460). At bar 39 -- the last seed bar -- 631 bars
    # differ by up to 4.569e+00 with the NaN masks equal, and at bar 700 the
    # two columns are BIT-EQUAL, because pandas' `ewm` skips an infinite
    # observation exactly as it skips a NaN and a pandas window loses only
    # the windows that CONTAIN it (§G1 probes both behaviours directly).
    # A planted NaN is unaffected either way, because the guard only maps a
    # non-finite value to the NaN it already is.
    # ⚠ So this guard is NOT what keeps an infinity out of the output: §G2
    # is.
    cl = close.astype(float)
    cl = cl.where(np.isfinite(cl))

    # "MACD20/40": the 20-bar EMA less the 40-bar EMA of the close.
    # ⚠ WHICH EMA is the load-bearing reading of this formula, and this is
    # this fork's own `ema` -- imported from its own module, the way
    # `trix`, `stc`, `pfe` and seven other momentum modules import it, and
    # the way `CLAUDE.md` requires (never from the package, which binds the
    # SUBMODULE during a partial import). At its defaults (`sma=True`,
    # `adjust=False`) it blanks the first `length - 1` bars, seeds bar
    # `length - 1` with the mean of the first `length` closes and recurses
    # at `span=length`. §A2 prints that seeding rather than trusting it.
    # The screen prototype's EMA is a bare `ewm(span=n, adjust=False)` from
    # bar 0 with NO seed, which §A4 measures as a different column to the
    # last bar of every frame; `talib.EMA` seeds the way this one does
    # (§A5). §A3 pins the whole leg BIT-EQUAL to this fork's own
    # `macd(close, fast=20, slow=40)["MACD_20_40_9"]`, so this is the
    # fork's MACD line and not a near relative of it.
    macd = ema(cl, length=FAST) - ema(cl, length=SLOW)

    # "t1 = (MACD20/40 - MACD20/40[1])*150": the MACD's ONE-BAR change,
    # times the sensitivity. `[1]` is Pine's and jesse's previous bar.
    # ⚠ This is the whole of the column's causality question, and it reads
    # BACKWARD: `shift(1)` is yesterday. `tests/test_j_wae.py` carries a
    # 36-offset future-perturbation sweep and six look-ahead mutants to say
    # so.
    t1 = SENSITIVITY * (macd - macd.shift(1))

    # "e1 = BB20,2 upper - lower": the Bollinger width at CHANNEL bars and
    # MULT population standard deviations.
    # ⚠ Spelled as the band SUBTRACTION the issue quotes, NOT as the
    # algebraic `2 * MULT * sd` -- and the two are different columns in the
    # last bits, which is why the choice is made here rather than left to a
    # reader. `(mid + dev) - (mid - dev)` rounds twice around a midpoint
    # that then cancels, so it loses the low bits of `dev` in proportion to
    # `mid / dev`. §A6 measures what that costs: the two readings of the
    # WIDTH differ by up to 1.819e-12 absolute (7.220e-15 relative) and the
    # two COLUMNS differ on 1,357 .. 1,410 of the 1,460 fired bars by up to
    # 5.329e-14, at Spearman 1.0000. §A1's oracle takes the same literal
    # route this line does. (Where the variance overflows, §G3 finds the
    # two readings AGREE: both widths are inf on the overflowing bar and
    # both NaN after it.)
    # ⚠ The three lines below are the issue's formula, not a copy of
    # `bbands`: `bbands` would compute a band-width percentage this column
    # does not use and return a four-column frame to index by name. They
    # are not a RECIPE the way `ema`'s seeding is -- there is nothing to
    # get subtly wrong in `mid +/- 2 sigma` -- and §A6 pins them BIT-EQUAL
    # to `bbands(close, 20, 2.0)`'s `BBU - BBL` on every frame, so the
    # shipped band is this fork's band.
    # `min_periods=CHANNEL` is pandas' default for this window and is
    # spelled out because it is load-bearing: one NaN close blanks CHANNEL
    # bars of this leg rather than being skipped.
    window = cl.rolling(CHANNEL, min_periods=CHANNEL)
    # `ddof=0` is the population standard deviation -- Bollinger's own, and
    # this fork's `bbands` default (`ddof=0`). `sqrt` of the variance is
    # the route `pandas_ta.statistics.stdev` takes, so §A6's bit-equality
    # against `bbands` is a check of the whole leg rather than of a bound.
    sd = np.sqrt(window.var(ddof=0))
    mid = window.mean()
    dev = MULT * sd
    e1 = (mid + dev) - (mid - dev)

    # "t1 / e1 (both price units)", the scale-free form issue #123 names.
    # ⚠ The next two lines are ONE guard in two halves, and §G2 prices them
    # TOGETHER because each alone is a measured no-op: removing `e1 > 0`
    # changes nothing (the finite mask catches the same bars) and removing
    # the finite mask changes nothing (`e1 > 0` already blanked them), on
    # all nine frames §G2 runs. Removing BOTH is what ships an infinity:
    # on a `walk` held exactly flat over bars 400..600 the width is 0.0 on
    # 182 bars while the two EMAs are still converging, so `t1` is non-zero
    # over a zero and the column reads 182 infinite values of 1,460 instead
    # of firing on 1,278.
    # That case is not exotic on real data -- a halted or illiquid name
    # printing one price for CHANNEL bars is exactly it.
    wae = t1 / e1.where(e1 > 0.0)
    # ⚠ And the finite mask is kept rather than deleted as redundant for a
    # reason that is stated rather than measured: no frame in §G3 reaches
    # an OVERFLOW of the division on finite inputs, including three built
    # to (a higher price regime feeding `t1` while the width is computed over
    # a tiny one), so this line's own load-bearing case is UNPROVEN here.
    # On the two of them whose variance overflows (at bar 19), pandas'
    # rolling variance then stays NaN for the rest of the frame -- 100 of
    # 100 later bars, unlike §G1's NaN close, whose windows recover -- so
    # those frames fire on 0 bars.
    # It costs one pass and it is the only thing standing between a future
    # pandas that returns an inf where today's returns a NaN and an
    # infinite value in an ML feature column.
    wae = wae.where(np.isfinite(wae))

    # Offset
    if offset != 0:
        wae = wae.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        wae.fillna(kwargs["fillna"], inplace=True)

    # Name and Categorize it
    wae.name = f"J_WAE_{SENSITIVITY}_{FAST}_{SLOW}_{CHANNEL}_{MULT}"
    wae.category = "momentum"

    return wae


j_wae.__doc__ = \
"""Waddah Attar Explosion power (J_WAE)

The one-bar change of the 20/40 MACD line, times 150, over the width of
the 20-bar 2-sigma Bollinger band: signed acceleration per unit of
volatility.

    macd[T] = EMA(close, 20)[T] - EMA(close, 40)[T]     both SMA-seeded
    t1[T]   = (macd[T] - macd[T-1]) * 150
    e1[T]   = BBupper(close, 20, 2)[T] - BBlower(close, 20, 2)[T]
    J_WAE[T] = t1[T] / e1[T]

Source: jesse indicators (MIT), `waddah_attar_explosion.py`, as PandasTa
issue #123 quotes it: "t1 = (MACD20/40 - MACD20/40[1])*150, e1 = BB20,2
upper - lower". The underlying rule is Waddah Attar's "Explosion"
histogram, which the TradingView community knows through LazyBear's
transcription.
⚠ jesse is NOT installed in this worktree and web access is unavailable,
so Gate A does not read jesse's source
(`tests/test_j_wae.py::test_the_source_library_is_not_installed_here`
records that, so the claim cannot rot into "checked against jesse"). What
Gate A checks is the formula issue #123 quotes, spelled three independent
ways, and the attribution is to the issue's QUOTE rather than to jesse's
code. The issue itself says of the library: "existence, not evidence".
⚠ **Nothing below is a statement about what jesse's code says.** Which EMA
seeding it uses, which standard deviation its Bollinger bands take, and
whether it ships the ratio at all (jesse's own output is the pair
`t1`/`e1` with a dead zone, not their quotient) is not checkable here and
is not claimed. The RATIO is issue #123's scale-free conversion --
"t1 / e1 (both price units)" -- and it is the thing the 2026-10-24 screen
measured.
⚠ The POWER only. jesse's indicator also carries an explosion line and a
dead zone, neither of which the issue quotes, neither of which the screen
measured, and so neither of which ships here.

**Gate A is the issue's formula spelled independently, and this fork's own
`macd` and `bbands` are the second and third spellers.** A bar-by-bar
oracle -- its own `math.fsum` SMA seed, its own EMA recursion over plain
Python floats, its own windowed mean and population variance, sharing no
code with the module -- agrees with this module on 1,460 of 1,460 fired
bars of each of six varying frames, with identical NaN masks, to
1.692e-10 absolute and 4.302e-11 relative at Spearman 1.0000 (§A1). NOT
bit-equal, and §A1b attributes the gap leg by leg rather than guessing:
it is `e1`, where pandas' `rolling.var` is an online update and the
oracle's is a two-pass `fsum` (up to 4.302e-11 relative, and the
column's relative gap matches `e1`'s to three significant digits on every
frame). The EMA legs are the quiet ones -- both are bit-equal to the
oracle's hand-rolled recursion on two of the six frames (`grid`,
`heavy-tailed`), and on the other four one leg differs by at most
2.842e-14, each time the leg whose `Series.mean()` seed is not equal to
the oracle's `math.fsum` seed; under numpy's reduced CPU dispatch the
seeds are equal and both legs are bit-equal on all six -- and `t1` is
bit-equal on five of the six, its one exception 2.132e-12. The
assertions are 1e-7 absolute and 1e-7 relative, both of which a reduced
numpy kernel also clears.
`macd(close, fast=20, slow=40)["MACD_20_40_9"]` is BIT-EQUAL to this
module's MACD leg on all six (§A3) and `bbands(close, 20, 2.0)`'s upper
minus lower is BIT-EQUAL to its `e1` on all six (§A6), so both halves are
this fork's own columns rather than a retyping of them.
`talib.EMA(close, 20) - talib.EMA(close, 40)` is the same leg to 1.273e-11
absolute, first firing at the same bar 39 (talib 0.7.1, §A5); that test
skips rather than passing silently where talib is absent.

⚠ **WHICH EMA is the load-bearing reading, and the screen prototype's is
not this one.** This module reads `EMA` as SMA-seeded -- this fork's
`ema`, and `talib.EMA` -- while the prototype recurses from bar 0 with no
seed. Measured (§A4) over the six varying frames: the prototype's column
disagrees with the shipped one on 1,399 .. 1,435 of the 1,460 shared bars
by up to 2.664e+00, the last disagreement falling at bar 1,499 of 1,500
on all six (1,496 on `range-bound` under numpy's reduced CPU dispatch)
rather than washing out, and it fires 21 bars earlier (from index 19
rather than 40). Spearman 0.9983 .. 1.0000. So the screen's DISCLOSE_GAP
figures describe a NEIGHBOURING column, and the port's own Gate E run
decides its band. Two further readings are priced rather than assumed
close: pandas' `adjust=True` EMA (1,065 .. 1,113 bars differ, by up to
4.495e+00) and a SAMPLE standard deviation in the width (`ddof=1`: all
1,460 bars differ, by up to 3.105e-01 -- a WIDER band, so a column
smaller in magnitude: the median |alt| / |this| is 0.9747 on every
frame).

Causal: bar T reads `close` up to T. Nothing later. Measured by a
36-offset future-perturbation sweep (0 of 36 on each of six frames) and by
six look-ahead mutants read off this file, edited and `exec`'d in memory,
each live and caught on 36 of 36 offsets of each of three frames, the
first catch moving a bar by 2.539e-02 .. 1.937e+00 (§B1).
⚠ **And the sweep has a blind spot this module states rather than leaves
for a reader to find.** An edit that makes `t1` read `macd - macd.shift(2)`
-- the change over TWO bars -- or that lags `e1` by a bar is wrong without
reading any later bar, so the suffix sweep catches it 0 of 36 times. Three
such edits are measured in §B2, all three caught 0 of 36 by the sweep and
all three caught by Gate A's oracle, which they miss by 2.929e-01 ..
1.220e+01. That is why Gate B here is the sweep AND the oracle.

Scale-free by construction: `t1` and `e1` are both homogeneous of degree 1
in the price, so the ratio cancels the factor. Measured bit-identical
under x8 and x64 on 1,460 of 1,460 bars of each of six frames and at price
levels 1e-6, 1e+6 and 1e+100 (§D1, §D3), and within 5.267e-10 absolute
under x10/x3.7/x0.1/x1.0000001 over 24 cells with every NaN mask matching,
asserted 1e-7 (§D2).
⚠ **This column is AFFINE-invariant, not merely scale-free, and that
breaks the usual non-vacuity check.** Every EMA of `close + k` is that EMA
plus `k`, so the MACD cancels the shift, and a standard deviation ignores
it: a +10 level shift moves the column by at most 3.564e-11 (§D4), where
other ports use exactly that shift to show their x8 bit-identity is not
vacuous. §D5 does that job here instead -- a +1 % nudge at ONE bar moves
594 .. 800 of the 1,460 fired bars, by up to 1.040e+00, starting at the
nudged bar.

⚠ **Unbounded in both directions, centred on zero, and the sign is the
signal.** `t1` is a difference of a difference, so it changes sign with
every wobble of the MACD; `e1` is a width and cannot be negative. Measured
over the 8,760 fired bars of the six varying frames: -8.7671e+00 ..
1.2263e+01, negative on 4,297 of them, |value| <= 10 on 8,751, and exactly
0.0 on NONE, with 1,460 distinct values on each frame (§C1).
⚠ Two degenerate frames are pinned separately (§C2), and they are the
shapes where this column says nothing. A CONSTANT close fires on 0 of
1,500 bars -- the width is exactly 0.0 on all 1,481 full windows and the
`e1 > 0` guard blanks every one. A straight arithmetic RAMP fires on all
1,460 but reads |value| <= 1.845e-12 on every one: the MACD of a ramp is
constant, so `t1` is zero up to the last bits. "Not a constant column" is
therefore asserted on the varying frames, not on every frame.

⚠ **Gate E on the PROTOTYPE was DISCLOSE_GAP** -- max |rho| 0.8698 vs the
manifest's `BB_PctB_Pctl` over 89 BIST frames (n = 391,907), top-five
per-frame max median 0.8715, inside the 0.80 .. 0.90 band. The next
comparators were `MACD_Hist_ATR` 0.8565 and `MACD_Hist_ATR_Pctl` 0.8536.
The port's own Gate E run is what decides its band, and it is PENDING: the
launcher runs it after this session (§E of `docs/JWaeMeasured.md`).
⚠ **What it is nearest to in the fork is `pgo`, and the figure sits in the
same DISCLOSE_GAP band rather than above the 0.90 line**: `PGO_14` reads a
per-frame median |rho| of 0.8580 over the six varying frames (0.8311 ..
0.9519), then a retyped `MACD_Hist_ATR` at 0.8531, `MACDh_12_26_9 / close`
at 0.8522, `bbands` %B at 0.8473 and `ROC_10` at 0.7555; `squeeze`'s
`SQZ_20_2.0_20_1.5` is far behind at 0.3885 (§L).
⚠ Six SYNTHETIC frames are not 89 real ones, and here they read HIGH by a
hair rather than low: on the one comparator with both figures, `PGO_14`,
the synthetic median is 0.8580 against the screen's real 0.8562 (+0.0018).
A single frame does cross 0.90 on `PGO_14` and on %B. §L is a disclosure,
not a gate.

Cost: two `ewm` recursions, one rolling mean, one rolling variance, one
shift and one division. Linear in bars. ⚠ The wall-clock figures live in
`docs/JWaeMeasured.md` §Z and nowhere else, including here: they are one
machine's and one run's.

Calculation:
    Default Inputs:
        sensitivity=150, fast=20, slow=40, channel=20, mult=2.0
        -- module constants
    macd = ema(close, 20) - ema(close, 40)        both SMA-seeded
    t1   = 150 * (macd - macd.shift(1))
    sd   = sqrt(close.rolling(20).var(ddof=0))
    mid  = close.rolling(20).mean()
    e1   = (mid + 2.0 * sd) - (mid - 2.0 * sd)
    J_WAE = t1 / e1                               blank where e1 <= 0

Args:
    close (pd.Series): Series of 'close's
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)

Returns:
    pd.Series: J_WAE_150_20_40_20_2.0, a dimensionless ratio
"""
