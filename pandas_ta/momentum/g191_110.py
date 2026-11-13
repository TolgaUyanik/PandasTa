# -*- coding: utf-8 -*-
"""Prior-Close Pressure Ratio (G191_110) -- Guotai Junan's (2017, "GTJA191",
internal quant report) alpha `#110`, per issue #84, which attributes its
copy of the report to HKUDS/Vibe-Trading (MIT) -- a copy NOT read in this
session, see the disclosure below. Source cited by the issue:

    #110: SUM(MAX(0,H-C1),20) / SUM(MAX(0,C1-L),20) * 100

**READ THIS FIRST -- THE COLUMN RESTATES A SHIPPED INDICATOR.** This fork
already ships this exact formula: `brar`'s `BR` column
(`pandas_ta/momentum/brar.py:23-33`). At the SAME length the two are the
same column, and that is measured rather than argued: on the 1,500-bar
walk of `docs/measure_g191_110.py` this port and
`brar(..., length=20)["BR_20"]` have Spearman **1.0**, differ by at most
**5.684341886080802e-14** (one ulp at this column's maximum), and are
bit-equal on **927 of 1,480** shared bars -- 927 of 1,480 HERE, and a
bit-equal count over float64 is last-bit dependent, so the test pins
`0 < bit_equal < 1480` rather than the integer (commit `a56d873`). The
port's own expression re-spelled `brar`'s way (`(100*num)/den` instead of
`100*(num/den)`) is bit-equal to `BR_20` on **1,480 of 1,480** bars with
`max|diff| = 0.0`, so on that frame the float gap is ENTIRELY the `100`'s
placement. `brar(..., length=20)` is reachable today through
`df.ta.brar(length=20)`, so this port adds a module, a `Category` entry
and an accessor for arithmetic the fork can already produce.

The differences from `brar`, enumerated as a measured list rather than as
a closed count. (a)-(c) are spelling and (d)-(g) are behaviour;
`docs/measure_g191_110.py` PRINTS (d), (e) and (f), while (a), (b), (c)
and (g) are READ in `brar.py:9` / `brar.py:32-33` /
`pandas_ta/utils/_core.py`'s `non_zero_range` / `brar.py:6, 10, 17` --
with (b) corroborated by the bit-equality of the re-spelled expression and
(c) by the planted-tie run:
(a) `brar`'s default `length` is 26, this alpha's is 20; (b) `brar` puts
the `100` on the numerator; (c) `brar` spells `MAX(0, .)` as
`non_zero_range` plus a negative-clip, which adds
`sys.float_info.epsilon` to the whole difference series when any element
is exactly zero; (d) `brar` does NOT replace `+-inf` with NaN -- on a
40-bar frame whose every low sits above its prior close, `BR_20` carries
**20** `inf` values where this column reports NaN, so swapping one for
the other puts `inf` into a feature matrix; (e) `brar` calls
`verify_series(.., length)` and this port `verify_series(.., length + 1)`,
so at exactly 20 bars of history `brar` returns a DataFrame whose `BR_20`
is non-NaN on **0** bars while this port returns `None`; (f) `brar.py:38`
reads `br = ar.shift(offset)`, so at any non-zero `offset` its `BR`
column is its own `AR` column shifted TWICE -- measured at `offset=2`,
`BR_20` equals `AR_20.shift(4)` on **1,477 of 1,477** shared bars, while
this port's `offset=2` output equals its own base shifted by 2 on
**1,478 of 1,478**; and (g) `brar` exposes `scalar` (default 100) and
`drift` (default 1) as parameters (`brar.py:6, 10, 17`) where this port
hardcodes `100` and `close.shift(1)`, so the equivalence holds only at
`scalar=100, drift=1` and `brar(length=20, drift=2)` has no equivalent
here at all. This list is what was measured or read in this session, not a
claim to be exhaustive.

Against the SHIPPED default `BR_26` the overlap is 0.858897 here and the
issue's own prototype measured 0.8860 pooled on real data -- under the
0.90 strike line, so the `r3-perframe-0.90` bands say DISCLOSE_GAP rather
than STRUCK. Whether a near-duplicate at a different length is worth a
column is the OWNER'S call, not Gate E's, and this session could not ask.
`docs/G191110Measured.md` carries the whole table and a ranked
recommendation, which is to SKIP it as question-redundancy.

**What this session could NOT do, disclosed up front:** `docs/pine/` and
web access are both unavailable in this worktree, so the issue's own named
copy -- HKUDS/Vibe-Trading (MIT) -- was never read. The formula below is
derived from the issue's own stated text (itself a quote of the GTJA191
report), per the issue's own instruction ("Gate A starts from the source
formula, not the prototype"), then cross-checked against the issue's own
prototype (`docs/issues/screen/ind_screen.py:459-463`):

    @cand("g191_110", "high-over-prior-close vs prior-close-over-low (20)", G,
          "#110: SUM(MAX(0,H-C1),20) / SUM(MAX(0,C1-L),20) * 100")
    def _(o, h, l, c, v):
        c1 = delay(c, 1)
        return 100 * sdiv(tsum((h - c1).clip(lower=0), 20),
                          tsum((c1 - l).clip(lower=0), 20))

The issue's string and the prototype agree on the window (20), on both
`MAX(0, .)` arms and on the `* 100`. THREE ambiguities in the string have
to be fixed and the prototype fixes all three -- but the second one has
THREE candidate parses rather than two, so there are FOUR decisions below,
numbered 1 / 2 / 2b / 3 to match the table in
`docs/G191110Measured.md`, with one test each:

1. **`MAX(0, X)` is the POINTWISE two-argument max against the scalar 0**,
   i.e. a per-bar floor, not GTJA191's windowed `TSMAX`. The screen defines
   the windowed operators separately (`tsmax`/`tsmin`,
   `ind_screen.py:50-51`) and does not use them here; the prototype writes
   `.clip(lower=0)`. The rejected windowed reading is measured rather than
   dismissed: taking `TSMAX(H-C1, 20) / TSMAX(C1-L, 20) * 100` instead
   gives a DIFFERENT column -- Spearman **0.449365**, `max|diff|`
   **160.812927**, 0 bit-equal bars of 1,480 -- so this reading is not a
   cosmetic choice, and `tests/test_g191_110.py` pins the divergence.
2. **`*100` multiplies the RATIO, it does not scale the denominator.** The
   tail `/ SUM(MAX(0,C1-L),20) * 100` admits the parse
   `/ (SUM(..) * 100)`, which is NOT what the prototype computes
   (`ind_screen.py:463` divides, then multiplies the finished ratio by
   100); standard left-to-right precedence for `/` and `*` agrees with the
   prototype. The rejected parse is this column divided by exactly 10,000
   (measured ratio **9999.999999999996** to **10000.000000000002**,
   Spearman **1.0**, 0 bit-equal bars of 1,480), so it is a pure constant
   rescale that changes no ordering of bars -- it matters only for the
   magnitude a reader sees, which is why the shipped spelling is the
   prototype's.
2b. **A THIRD parse of the same `*100`**, and it is the one the fork's own
   `brar` uses: `(100 * SUM(up)) / SUM(down)`, the scalar on the numerator
   (`brar.py:32-33`) -- algebraically identical and NOT bit-identical:
   Spearman 1.0, bit-equal on 927 of 1,480 bars (a last-bit-dependent
   count, pinned as a band), `max|diff|` 5.684341886080802e-14. All three
   parses are measured in `docs/measure_g191_110.py` and pinned in the
   test file.
3. **`C1` is yesterday's close**, `DELAY(C, 1) = C.shift(1)`
   (`ind_screen.py:45`), a BACKWARD shift (bar `t` reads bar `t-1`), never
   a look-ahead. It is undefined at bar 0, and `.clip(lower=0)` PRESERVES
   the resulting NaN rather than flooring it to `0.0`; the trailing sum's
   `min_periods` then carries that NaN through the first `length` outputs.
   The obvious alternative spelling of `MAX(0, .)`,
   `np.where(x > 0, x, 0.0)`, does NOT: a NaN fails the `> 0` test, falls
   down the else branch and fabricates a `0.0` contribution for a bar that
   has none. Measured: the `np.where` form fires on **1,481** bars against
   this port's **1,480** and starts at bar **19** instead of **20**, while
   differing on **0** of the bars where both fire -- i.e. its entire effect
   is one invented output at the warm-up edge.
   `tests/test_g191_110.py::test_the_rejected_where_spelling_invents_a_warmup_bar`
   pins it.

OPERATORS, each read directly off the prototype's own (unambiguous) module
source in this session:

* `SUM(X, n)` = `X.rolling(n).sum()` (`ind_screen.py:49`), a trailing
  `n`-bar sum at pandas' default `min_periods=n`, so one NaN anywhere in
  the window empties the output. Written out as
  `rolling(length, min_periods=length)` here, the same explicit spelling
  `g191_003` and `g191_129` use, so the warm-up does not depend on a pandas
  default.
* The prototype's own `sdiv` (`ind_screen.py:41-42`, `_fin(a / b)`)
  replaces `+-inf` with `NaN` on the division -- BEFORE the `* 100`, which
  is where this module puts the `.replace()` too, so the two agree bar for
  bar. A NaN survives the multiplication unchanged.
* `H`, `L`, `C` = high, low, close of the current bar. `OPEN` and `VOLUME`
  are not read -- which is what separates this alpha from `brar`'s OTHER
  column, `AR` (`SUM(H-O)/SUM(O-L)`, measured here at Spearman
  **0.003205** against this column).

CALCULATION, in the order computed below (`length=20`, the issue's own
fixed "20" exposed as a tunable, which is what the sibling ports that have
a surviving source constant do -- `g191_002`, `g191_003`, `g191_093`,
`g191_129`, `g191_167` among them; `g191_158` is the counterexample, since
its source's own `15`/`2` cancel and it exposes no parameter at all
(`pandas_ta/volatility/g191_158.py:63-64`)):
    C1       = DELAY(C, 1)
    up       = MAX(0, H - C1)         # NaN at bar 0, where C1 is undefined
    down     = MAX(0, C1 - L)         # ""
    G191_110 = 100 * (SUM(up, length) / SUM(down, length)), inf -> NaN

WHAT IT MEASURES. `up` is how far above yesterday's close today's high
reached, zero if it never got there; `down` is how far below yesterday's
close today's low reached, zero if it never got there. Over a trailing
window the column is the total upside excursion as a PERCENT of the total
downside excursion: `100` is balance, above `100` means buyers pushed
further past yesterday's close than sellers did, below `100` the reverse.
It is non-negative and unbounded above, so it is SKEWED by construction --
a 2x imbalance up reads 200 and a 2x imbalance down reads 50. The
rank-identical symmetric reparametrisation `100 * up / (up + down)` -- the
RSI/`BR`-to-`RSI` form of the same two sums -- measures Spearman **`1.0`
at full precision** against this column (the measure script prints the
`repr`, not a rounded `:.6f`; the test allows 1e-12 of slack, since a
Spearman is a Pearson of ranks and `sqrt(x*x) == x` is not an IEEE
guarantee) (`x/(x+y)` is strictly increasing in
`x/y` for `x, y >= 0`), so nothing that mines on RANKS can tell the two
apart; the difference is purely the scale a tree splits on. Measured, and
pinned by
`tests/test_g191_110.py::test_the_symmetric_reparametrisation_is_rank_identical`.

RELATION TO THE FORK'S OTHER COLUMNS, measured on the same 1,500-bar
synthetic walk and **NOT Gate E**: `brar:BR_26` **0.858897** (the same
formula at length 26 -- see the top of this docstring), `rsi:RSI_14`
**0.860097** and `cmo:CMO_14` **0.860097** (identical to six decimals,
which is expected since `CMO = 2*RSI - 100` is a monotone transform, and is
a pre-existing property of those two columns rather than anything this port
changes), the two GTJA cousins that take the same `MAX(0, .)` of
CLOSE-to-close changes instead -- `g191_167` (`SUM(MAX(C-C1,0),12)/C`)
**0.569560** and `g191_129` (`SUM(MAX(C1-C,0),12)/C`) **-0.621055** -- and
their own ratio, `100*g191_167/g191_129`, **0.708189**. `psl:PSL_12`
**0.648262** and `imi:IMI_14` **0.037103**. No claim is made that this is
every related column in the package: these are the momentum hits that a
grep for `clip(lower=0)` and for `close.shift` returned and that were read
in this session.

The `20` itself was varied one length at a time on the same frame, which is
what locates how much of the `BR_26` overlap is just "a 20-bar sum
resembles a 26-bar sum": length 5 **0.449792**, 10 **0.651217**, 15
**0.839252**, 19 **0.968446**, 21 **0.970599**, 26 **0.858897**, 40
**0.661417**, 60 **0.535950**. Adjacent lengths are near-duplicates of each
other and the decay is smooth, so the source's `20` is not a special point
-- it is the GTJA report's choice, and the fork's existing `BR_26` sits
four fifths of the way down that curve.

CAUSALITY. `C1[t]` reads only `C[t-1]`. `up[t]` and `down[t]` are pointwise
functions of `H[t]`, `L[t]` and `C1[t]`, all bars no newer than `t`.
`SUM(., length)[t]` is a trailing `length`-bar sum over `[t-length+1, t]`,
every index `<= t`. The final division and the `* 100` are pointwise.
Nothing in the chain reads a bar newer than `t`. `tests/test_g191_110.py`
proves this both by future-perturbation (real module: **0 of 37** offsets
leak, with high/low/close rewritten jointly from each offset onward) and by
FOUR mutants (`importlib` source read, `exec`'d in memory), each shown
live (differs from the real module) and then caught at **37 of 37**
offsets: shifting the final write index `length` bars into the future;
flipping the `DELAY` to `close.shift(-1)` so `C1` becomes TOMORROW's close
(this formula's own most plausible sign error); and computing EACH of the
two sums with `rolling(..., center=True)` instead of the causal trailing
window -- the same `bos` look-ahead bug class CLAUDE.md documents, mutated
once on the numerator's call and once on the denominator's, so neither arm
is proven by analogy from the other. `offset` is this fork's standard
parameter and a NEGATIVE offset makes THIS column read the future, so it
is pinned rather than inferred from the mutants: `offset=+2`/`-2` are
exactly the default column shifted later and earlier, and the Gate B sweep
covers the `offset=0` the registry uses. No claim is made that `offset` is
the only look-ahead reachable in this package -- it is not, and CLAUDE.md
names the counterexample: `ichimoku`'s `ICS_26` is `close.shift(-kijun)`
at DEFAULT parameters, an ACCEPTED exception by design.

WARM-UP. `C1` is undefined at bar 0, so `up` and `down` are NaN there (see
reading 3), and `SUM(., length)` at `min_periods=length` needs `length`
CONSECUTIVE valid contributions ending at `t`, i.e. `t >= length`. So
`min_length = length + 1` bars of history (**21** at the shipped default),
enforced by `verify_series`: 20 bars return `None`, 21 bars fire exactly
once, at bar 20. Measured.

THE DENOMINATOR CAN VANISH, and that is where this column hides
information. `SUM(down, length) = 0` means every one of the last
`length` bars had its LOW at or above the prior close -- an unbroken run of
gap-ups that never traded back. The division is then `x/0 = +inf`, which
the `.replace()` turns into NaN, so an extreme reading is reported as
MISSING DATA and is indistinguishable downstream from a short history.
Measured on a 40-bar frame whose every low sits above the prior close: the
raw ratio is `inf` on **20** bars and the column fires on **0 of 40**;
`brar`'s `BR_20` on the same frame leaves the **20** `inf` values in place
instead (measured -- the two modules differ here, and the port's choice is
the prototype's `sdiv`). Letting ONE bar of that frame dip below its prior
close rescues exactly the windows containing it: **10 of 40** bars fire,
the first at 30 and the last at 39. A FROZEN frame (`H == L == C`,
constant) is a different case again: numerator and denominator are both
exactly 0, so the division is `0/0` -- NaN directly, with **0** `inf`
values to replace and **40 of 40** bars NaN.

A single NaN in an input empties a whole window and displaces nothing,
unlike an `ewm`-based port, whose state outlives its window -- measured on
the sibling `g191_188`, where one NaN at index 700 displaced 167 later
bars (`docs/G191188Measured.md`): one NaN planted in `high` at index
700 of the 1,500-bar walk empties exactly **20** bars and moves **0** of
the rest (the trailing sum propagates a NaN instead of skipping it, and
carries no state past its own window); one NaN in `close` at the same index
also empties exactly **20**, since `close[700]` is read only as bar 701's
`C1`.

SCALE-FREE. Let `k > 0` rescale price (`H, L, C -> k*H, k*L, k*C`). `C1`
carries no arithmetic, so it scales to `k*C1`. The `MAX(0, .)` floor is a
comparison against zero and is scale-invariant for any `k > 0`
(`k*x > 0` iff `x > 0`, exactly, since multiplication by a positive
constant is strictly monotone), so `up -> k*up` and `down -> k*down`; the
trailing sums are linear, so both scale by `k`; and the ratio cancels it:
`(k*SUM(up))/(k*SUM(down)) = SUM(up)/SUM(down)` for ANY positive `k`, with
no extra division needed (which is why this candidate's own
`candidates.csv` row carries an EMPTY `conv` cell,
`docs/issues/screen/candidates.csv:47`). The `* 100` is a constant and
commutes with all of it. Measured on the synthetic walk: PRICE `x8`/`x64`
land bit-identical on all 1,480 fired bars (multiplication by a power of
two is exact in IEEE754 and commutes with rounding, so both sums and the
division scale exactly), while `x10`/`x3.7` come out within
**1.3073986337985843e-12** / **1.4210854715202004e-12** -- float64
rounding, not a scale dependence. Because the two floors are EXACT
comparisons, the branch masks themselves were measured under each
multiplier rather than assumed: **0** bars change branch in either the
`up` or the `down` floor at any of `x8`, `x64`, `x10`, `x3.7`.
"""
import numpy as np

from pandas_ta.utils import get_offset, verify_series


def g191_110(high, low, close, length=None, offset=None, **kwargs):
    """Indicator: Prior-Close Pressure Ratio (G191_110)"""
    # Validate Arguments
    length = int(length) if length and length > 0 else 20
    min_length = length + 1
    high = verify_series(high, min_length)
    low = verify_series(low, min_length)
    close = verify_series(close, min_length)
    offset = get_offset(offset)

    if high is None or low is None or close is None:
        return

    if not (high.index.equals(low.index) and high.index.equals(close.index)):
        raise ValueError(
            "g191_110: `high`, `low` and `close` are indexed differently. A "
            "pressure ratio read off misaligned series is a silent nonsense "
            "number."
        )

    # Calculate Result
    prev_close = close.shift(1)
    up = (high - prev_close).clip(lower=0)
    down = (prev_close - low).clip(lower=0)
    up_sum = up.rolling(length, min_periods=length).sum()
    down_sum = down.rolling(length, min_periods=length).sum()
    result = 100 * (up_sum / down_sum).replace([np.inf, -np.inf], np.nan)

    # Offset
    if offset != 0:
        result = result.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        result.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        result.fillna(method=kwargs["fill_method"], inplace=True)

    # Name & Category
    result.name = f"G191_110_{length}"
    result.category = "momentum"

    return result


g191_110.__doc__ = \
"""Prior-Close Pressure Ratio (G191_110)

Guotai Junan's (2017, "GTJA191") alpha `#110`, per issue #84. Over a
trailing window, the total distance highs reached ABOVE the prior close
divided by the total distance lows reached BELOW it, in percent: `100` is
balance, above `100` means buyers pushed further past yesterday's close
than sellers did, below `100` the reverse. Non-negative and unbounded
above.

**This restates a shipped column.** `brar`'s `BR` is the same formula
(`pandas_ta/momentum/brar.py:23-33`). At the same length the two agree to
Spearman 1.0 and `max|diff|` 5.68e-14 on a 1,500-bar synthetic walk, and
the port's own expression re-spelled `brar`'s way is bit-identical to
`BR_20` there; against the shipped default `BR_26` the overlap is 0.858897
on that frame, and the issue's own prototype measured 0.8860 pooled on real
data (DISCLOSE_GAP, under the 0.90 strike line).
`df.ta.brar(length=20)` already produces this arithmetic -- but the two are
NOT interchangeable, and the difference that bites is measured: `brar` does
not replace `+-inf` with NaN, so on a frame of unbroken gap-ups its `BR_20`
carries 20 `inf` values where this column reports NaN. The other measured
differences (the `100`'s placement, `non_zero_range`'s epsilon, a
`length`-vs-`length+1` history guard, `brar.py:38`'s double-shifted
`offset`, and `brar`'s `scalar`/`drift` parameters, which this port
hardcodes at `100` and `shift(1)` -- so the equivalence holds only at
`scalar=100, drift=1`) are enumerated in the module source above. Whether the column is
worth keeping is the owner's call; the ranked recommendation in
`docs/G191110Measured.md` is to SKIP it as question-redundancy. Also
rank-identical (Spearman `1.0` at full precision) to
its own symmetric reparametrisation `100 * up / (up + down)`, so no
rank-based miner can distinguish the two scalings.

Full Gate A derivation (three fixed readings of the source string, three
parses of the `*100`), causality, warm-up, the vanishing-denominator case
and the scale-free argument are in the module source above; the measured
numbers are in docs/G191110Measured.md.

Calculation:
    Default Inputs:
        length=20
    C1       = DELAY(close, 1)
    up       = MAX(0, high - C1)
    down     = MAX(0, C1 - low)
    G191_110 = 100 * (SUM(up, length) / SUM(down, length)), inf -> NaN

Args:
    high (pd.Series): Series of 'high's
    low (pd.Series): Series of 'low's
    close (pd.Series): Series of 'close's
    length (int): Rolling window for both sums, guarded by
        `int(length) if length and length > 0 else 20`. Two greps over the
        fork's `g191_*` modules, counting the assignment form only (not
        docstring mentions): `…length > 0 else` appears **31** times in
        **16** other modules and `…length > 1 else` **24** times in **18**,
        with **5** modules using BOTH (`g191_023`, `g191_044`, `g191_160`,
        `g191_174`, `g191_191`) and `g191_098` using a third spelling
        (`>= 1`). So `> 0` is the fork's commonest window guard, not a
        departure from it -- though narrowing to the parameter spelled
        exactly `length`, the split reverses: **3** of the 15 others use
        `> 0` (`g191_002`, `g191_003`, `g191_080`) and **12** use `> 1`.
        `> 0` is kept because `length=1` is legal and defined for this
        formula (a one-bar window is a ratio of one bar's two excursions,
        pinned below), whereas a `> 1` guard would silently substitute the
        default 20 for a caller who asked for 1; the cost is that `> 0`
        leaves the `0 < length < 1` band open, and the `> 1` spelling
        would close it by falling back to 20. Three
        off-nominal bands follow, all measured rather than assumed.
        `0` and any negative value fall back to the default 20
        (bit-identical to the default call). `0 < length < 1` does NOT:
        the guard passes (the value is truthy and positive), `int()` then
        truncates it to `0`, and nothing raises -- a zero-width
        `rolling(0, min_periods=0).sum()` is not NaN but `0.0` (measured:
        `0.0` on all 1,500 bars, 0 NaN), so the ratio is `0/0` and the
        column ships as ALL NaN under the name `G191_110_0`.
        `length=1` is legal and degenerate rather than empty: the window is
        a single bar, so the column fires only where that bar's low broke
        its prior close (measured: 1,045 of 1,500 bars on the walk, 616
        distinct values). Pinned by
        `tests/test_g191_110.py::test_the_length_guards_three_bands`.
        Default: 20
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.Series: G191_110_{length}, a scale-free (dimensionless) percent
        column: non-negative, unbounded above, `100` at balance, and
        exactly `0.0` for a window in which no high ever cleared its prior
        close while some low broke it -- measured on a 40-bar all-gap-down
        frame, where all 20 fired bars are exactly `0.0` (and the column is
        therefore CONSTANT on such a frame, which the ML contract says is
        not a feature; the 1,500-bar walk has 0 such bars). NaN for the
        first `length` bars
        (`min_length - 1`, 20 at the shipped default) and ALSO wherever the
        trailing `length`-bar downside sum is exactly zero -- an unbroken
        run of gap-ups, where the ratio is `+inf` and is reported as
        missing rather than as an extreme.
"""
