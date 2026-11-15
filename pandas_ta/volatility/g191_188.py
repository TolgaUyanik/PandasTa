# -*- coding: utf-8 -*-
"""Range vs its EMA -- Guotai Junan's (2017, "GTJA191", internal quant
report) alpha `#188`, per issue #83, which attributes its copy of the report
to HKUDS/Vibe-Trading (MIT) -- a copy NOT read in this session, see the
disclosure below. Source cited by the issue:

    #188: (H-L-SMA(H-L,11,2))/SMA(H-L,11,2)*100

**What this session could NOT do, disclosed up front:** `docs/pine/` and web
access are both unavailable in this worktree, so the issue's own named copy
-- HKUDS/Vibe-Trading (MIT) -- was never read. The formula below is derived
from the issue's own stated text (itself a quote of the GTJA191 report), per
the issue's own instruction ("Gate A starts from the source formula, not the
prototype"), then cross-checked against the issue's own prototype
(`docs/issues/screen/ind_screen.py:560-563`):

    @cand("g191_188", "range vs its EMA", G,
          "#188: (H-L-SMA(H-L,11,2))/SMA(H-L,11,2)*100")
    def _(o, h, l, c, v):
        e = sma(h - l, 11, 2)
        return 100 * sdiv(h - l - e, e)

The issue's string and the prototype agree on every length and weight (11,
2) and on the shape of the expression. ONE reading of the string has to be
fixed, and the prototype fixes it:

* **`*100` multiplies the RATIO, it does not scale the denominator.** The
  string's tail `/SMA(H-L,11,2)*100` admits a second parse,
  `/(SMA(H-L,11,2)*100)`, which is NOT what the prototype computes: the
  prototype divides by `e` alone and multiplies the finished ratio by 100
  (`100 * sdiv(h - l - e, e)`, `ind_screen.py:563`). Standard left-to-right
  precedence for `/` and `*` gives the same answer. The rejected reading is
  this column divided by exactly 10,000, so it is a pure constant rescale --
  Spearman 1.0, sign-identical, and no ordering of bars changes. That is
  measured rather than asserted in `docs/measure_g191_188.py` and pinned by
  `tests/test_g191_188.py::test_the_rejected_precedence_reading_is_a_constant_rescale`;
  it matters only for the magnitude a reader of the column sees, which is
  why the shipped spelling is the prototype's.

OPERATORS, each read directly off the prototype's own (unambiguous) module
source in this session -- no fork-wide claim about the other `g191_*` ports
is made here, since none was measured:

* `H`, `L` = high, low. No other OHLCV field is read.
* `SMA(A, n, m)` is GTJA's own recursive smoother, NOT this fork's
  `pandas_ta.overlap.sma` (a plain simple moving average) -- a name
  collision the prototype resolves by DEFINING its own `sma` as the GTJA
  recursion (`ind_screen.py:57-59`): `Y[t] = (m*A[t] + (n-m)*Y[t-1]) / n`,
  an exponential moving average with `alpha = m/n`. Here it is
  `SMA(.., 11, 2)`, i.e. `alpha = 2/11`, which is why the issue's own
  one-line title calls the denominator an EMA. Implemented as
  `A.ewm(alpha=m/n, adjust=False, min_periods=n).mean()`: `adjust=False`
  reproduces the recursion exactly (pandas' default `adjust=True` instead
  computes a different, non-recursive weighted average over the whole
  history), and `min_periods=n` masks the recursion until it has seen `n`
  of its own valid inputs -- the spelling the nearest sibling port in this
  same category writes for the identical operator
  (`pandas_ta/volatility/g191_109.py:101`, read in this session). The
  PROTOTYPE's own `sma` omits `min_periods` (`ind_screen.py:59`), so the
  10-bar head of this port's warm-up is this FORK's convention and not the
  source's; both spellings are measured in `docs/measure_g191_188.py`,
  pinned by
  `tests/test_g191_188.py::test_the_forks_min_periods_only_masks_bars_it_does_not_change_them`,
  and reported in `docs/G191188Measured.md` rather than argued.
  A SECOND convention rides in with `adjust=False` and is NOT stated by the
  source: the recursion `Y[t] = (m*A[t] + (n-m)*Y[t-1])/n` is undefined at
  its first bar, and `adjust=False` seeds it with `Y[first] = A[first]`.
  `min_periods` masks the output but does not remove that seed's influence
  (its weight at the first reported bar is `(9/11)**10`, about 0.15). The
  seed is inherited from the prototype and from `g191_109`, not derived:
  Gate A's independent per-bar replay is seeded the SAME way
  (`docs/measure_g191_188.py:_independent_loop`), so it validates the
  RECURSION and not the seed, and no check in this session can see a
  different initial condition.
* The prototype's own `sdiv` (`ind_screen.py:41-42`, `_fin(a / b)`)
  replaces `+-inf` with `NaN` on the division -- BEFORE the `* 100`, which
  is where this module puts the `.replace()` too, so the two agree bar for
  bar. A `NaN` survives the multiplication unchanged.

CALCULATION, in the order computed below (defaults `smooth_length=11,
smooth_weight=2`):
    r        = H - L
    e        = SMA(r, smooth_length, smooth_weight)
    G191_188 = 100 * ((r - e) / e), inf -> NaN before the 100

WHAT IT MEASURES. `e` is an EMA of the daily range at `alpha = 2/11`, i.e.
the range's own recent typical size. The column is today's range as a
PERCENT DEVIATION from that typical size: `0` when today's range is exactly
its EMA, `+100` when today's range is twice it, and bounded BELOW by `-100`
(reached only at `r = 0`, a dead bar), since `r >= 0` for valid OHLC data
and the EMA of a non-negative series is non-negative. It is a
range-expansion / range-contraction gauge, not a direction: it is blind to
where in the bar the close sat and to the sign of the move.

RELATION TO THE FORK'S OTHER RANGE COLUMNS, and this port does not hide it.
Grepping the package for `high - low` and reading the volatility hits in
this session found FOUR shipped volatility modules that divide one
smoothing of `H - L` by another: `g191_109`
(`pandas_ta/volatility/g191_109.py:157-159`, `SMA(H-L,10,2) /
SMA(SMA(H-L,10,2),10,2)` -- the ONCE-smoothed range over its TWICE-smoothed
self), `massi` (`massi.py:22-27`, `g191_109`'s ratio with arithmetic EMAs,
summed over 25 bars), `cvi` (`cvi.py:28-32`, `100 * (EMA(H-L,10) -
EMA(H-L,10)[-10]) / EMA(H-L,10)[-10]` -- this port's `100*(a-b)/b` spelling
against the EMA of TEN BARS AGO rather than against today's range), and this
one. No claim is made that those four are all of them: the grep hit 38 files
across the package and only the volatility ones were read. Also measured
because it is the nearest shape of all: `g191_158` (`(H-L)/close`).

Measured against those four on the 1,500-bar i.i.d. walk of
`docs/measure_g191_188.py` -- **NOT Gate E**: `g191_158` **0.951954**,
`g191_109` **0.641397**, `cvi` **0.266088**, `massi` **-0.066067**. The
`g191_158` number is above the 0.90 line and is the single most important
disclosure this port carries, so it is not left to the receipt alone. It is
very probably an ARTEFACT of that frame, and the artefact was measured, not
asserted: `_walk` draws each bar's spread as `close * uniform(...)`, which
makes `EMA(H-L)` nearly proportional to close (`e/close` has coefficient of
variation **0.1396** there), so `(H-L)/close` and `(H-L)/EMA(H-L)` are
near-monotone transforms of the same draw. Re-measured on a frame WITH
volatility clustering (`_walk_clustered`, the spread's log following an
AR(1); `e/close` CV **0.9382**), the `g191_158` overlap falls to
**0.451513** while `g191_109` holds at **0.729682**. Real tapes cluster.
Gate E is pending and decides. `docs/G191188Measured.md` carries the full
table (fourteen comparators), the one-variable-at-a-time variants that
locate this column's identity in its NUMERATOR rather than its denominator,
the issue's own prototype priors (0.8846 / DISCLOSE_GAP vs the engine's
`Range_ATR`; 0.3338 over 12 frames against the fork's scale-free `Category`
outputs at defaults -- a screen that predates `g191_158`'s own port), and
what does and does not follow from any of it.

CAUSALITY. `r[t] = H[t] - L[t]` is pointwise, reading no bar past `t`. The
GTJA `SMA`'s recursion reads only its own input at `t` and its own PRIOR
value at each step, so by induction `e[t]` is a function of `r[0..t]` only.
The final expression is pointwise on `r[t]` and `e[t]`. Nothing in the
chain is shifted forward anywhere. `tests/test_g191_188.py` proves this
both by future-perturbation (real module: 0 of 37 offsets leak over a
synthetic walk) and by three mutants (`importlib` source read, `exec`'d in
memory), each shown live (differs from the real module) and then caught at
every one of the 37 offsets: shifting the final write index `smooth_length`
bars into the future; building the range from `high.shift(-1) -
low.shift(-1)` (one bar of look-ahead folded in before the smoothing -- the
same `bos` look-ahead bug class CLAUDE.md documents); and reading the
smoothed range one bar ahead (`e.shift(-1)`, so BOTH the subtraction and
the division see tomorrow's EMA), which is this formula's own most
plausible off-by-one.

WARM-UP. `r` is defined on every bar (`H - L` needs no history, and an
`H == L` tie is a perfectly valid `0.0`, not a NaN). `e` carries
`min_periods=smooth_length` on its underlying `.ewm()`, so it needs
`smooth_length` valid `r` values and is defined from
`t >= smooth_length - 1`. The final expression is pointwise, so `G191_188`
is defined from `t >= smooth_length - 1` -- **10** at the shipped defaults,
i.e. `min_length = smooth_length` = **11** bars of history, enforced by
`verify_series`.

SCALE-FREE. Let `k > 0` rescale price (`H, L -> k*H, k*L`). Then
`r -> k*r` (linear in a positive scalar), and the GTJA `SMA` recursion is
linear in a positive scalar multiple of its input, so `e -> k*e`. Hence
`(r - e)/e -> (k*r - k*e)/(k*e) = (r - e)/e` -- the `k` cancels EXACTLY,
for ANY positive `k`, with no extra division needed (which is why this
candidate's own `candidates.csv` row carries an EMPTY `conv` cell,
`docs/issues/screen/candidates.csv:65`). The `* 100` is a constant and
commutes with all of it. Measured on a synthetic walk: PRICE `x8`/`x64`
land bit-identical (multiplication by a power of two is exact in IEEE754
and commutes with rounding, so the subtraction and the division scale
exactly), while `x10`/`x3.7` come out within float64 rounding tolerance
(the same arithmetic rounds differently at a non-power-of-two multiplier,
even though the true mathematical ratio is identical). Measured in the test
file and `docs/measure_g191_188.py`, not merely asserted.

A DEAD BAR (`H == L`, so `r = 0`) does NOT produce a NaN: `e > 0` as long
as any earlier bar had a positive range, so the column returns exactly
`-100.0`, its floor -- measured, one dead bar planted at index 700 of the
1,500-bar walk returns `-100.0` and the fire count does not move (1,490).
Among bars where `r` and `e` are BOTH defined (so past the warm-up head and
away from a NaN input), the division is NaN only when `e == 0`; on a frame
where EVERY bar
has `H == L` the division is `0/0`, which is NaN directly, so the
`.replace()` never has an `inf` to catch and the column fires on **0 of
1,500** bars. A NaN in `high` or `low` behaves differently again and is
measured rather than claimed: one NaN planted in `high` at index 700 empties
exactly **1** output bar (that bar's `r` is NaN), because pandas' `ewm`
SKIPS a NaN input (carrying its previous value forward) rather than emptying
its output, so `e` stays defined while its level is displaced -- **167** of
the remaining bars change value, and the first valid bar stays at 10.
`docs/measure_g191_188.py` prints all three cases.
"""
import numpy as np

from pandas_ta.utils import get_offset, verify_series


def _gtja_sma(series, n, m):
    """GTJA SMA(A,n,m): Y = (m*A + (n-m)*Y[-1]) / n, an EMA with alpha m/n."""
    return series.ewm(alpha=m / n, adjust=False, min_periods=n).mean()


def g191_188(high, low, smooth_length=None, smooth_weight=None, offset=None,
             **kwargs):
    """Indicator: Range vs Its EMA (G191_188)"""
    # Validate Arguments
    smooth_length = int(smooth_length) if smooth_length and smooth_length > 0 else 11
    smooth_weight = int(smooth_weight) if smooth_weight and smooth_weight > 0 else 2
    min_length = smooth_length
    high = verify_series(high, min_length)
    low = verify_series(low, min_length)
    offset = get_offset(offset)

    if high is None or low is None:
        return

    # Calculate Result
    r = high - low
    e = _gtja_sma(r, smooth_length, smooth_weight)
    result = 100 * ((r - e) / e).replace([np.inf, -np.inf], np.nan)

    # Offset
    if offset != 0:
        result = result.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        result.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        result.fillna(method=kwargs["fill_method"], inplace=True)

    # Name & Category
    result.name = f"G191_188_{smooth_length}_{smooth_weight}"
    result.category = "volatility"

    return result


g191_188.__doc__ = \
"""Range vs Its EMA (G191_188)

Guotai Junan's (2017, "GTJA191") alpha `#188`, per issue #83. Today's daily
range (`high - low`) as a PERCENT DEVIATION from an EMA of that range --
GTJA's own recursive `SMA(.., 11, 2)`, i.e. `alpha = 2/11`. The column is
`0` when today's range equals its EMA, `+100` when it is twice the EMA, and
floored at `-100` on a dead bar (`high == low`). A range-expansion gauge
with no direction in it: the sign of the move and the close's position in
the bar are both invisible to it. Nearest shipped shapes, measured on one
synthetic walk and NOT Gate E: `g191_158` (`(H-L)/close`) at Spearman
0.951954 on an i.i.d.-spread frame but only 0.451513 once the frame has
volatility clustering, and `g191_109` (the ONCE-smoothed range over its
TWICE-smoothed self) at 0.641397 / 0.729682 on the same two frames. Full Gate A
derivation, causality and scale-free arguments are in the module source
above; see docs/G191188Measured.md for the measured numbers.

Calculation:
    Default Inputs:
        smooth_length=11, smooth_weight=2
    r        = high - low
    e        = SMA(r, smooth_length, smooth_weight)   # GTJA SMA, ewm(alpha=smooth_weight/smooth_length)
    G191_188 = 100 * ((r - e) / e), inf -> NaN before the 100

Args:
    high (pd.Series): Series of 'high's
    low (pd.Series): Series of 'low's
    smooth_length (int): GTJA SMA length (`n`) of the range smoother. Cast
        with `int()` like the weight, and none of its three off-nominal
        bands is guarded: `0 < n < 1` truncates to `0`, so `alpha = m/n`
        raises `ZeroDivisionError` before pandas is reached; `n < m` (e.g.
        `n = 1` at the default `m = 2`) gives `alpha > 1`, which pandas'
        `ewm` rejects with a `ValueError`; and `n == m` gives
        `alpha = 1.0` exactly, which pandas ACCEPTS -- no smoothing, so
        `e == r`, the column collapses to a constant `0.0`, and nothing
        raises. The first two are pinned by
        `tests/test_g191_188.py::test_a_length_that_breaks_the_alpha_raises`
        and the third by `::test_a_length_equal_to_the_weight_collapses_the_column_to_zero`.
        Default: 11
    smooth_weight (int): GTJA SMA weight (`m`) of the range smoother. The
        source formula and the prototype both fix `m = 2`; other values are
        untested here, and `m` is cast with `int()`, so three bands behave
        differently: `0 < m < 1` truncates to `alpha = 0` and
        `m >= smooth_length + 1` gives `alpha > 1`, both of which pandas'
        own `ewm` rejects with a ValueError; while
        `smooth_length <= m < smooth_length + 1` truncates to
        `alpha = 1.0`, which pandas ACCEPTS -- no smoothing at all, so
        `e == r` and the column collapses to a CONSTANT `0.0` wherever it
        fires, and nothing raises.
        `tests/test_g191_188.py::test_a_weight_that_leaves_alpha_outside_zero_one_raises`
        and `::test_a_weight_of_alpha_one_collapses_the_column_to_zero` pin
        the three bands. Default: 2
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.Series: G191_188_{smooth_length}_{smooth_weight}, a scale-free
        (dimensionless) percent column taking both signs, bounded below by
        -100 and unbounded above. NaN for the first smooth_length - 1 bars
        (10 at the shipped defaults).
"""
