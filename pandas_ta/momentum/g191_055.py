# -*- coding: utf-8 -*-
"""20-Day Wilder Swing-Index Sum (G191_055) -- Guotai Junan's (2017,
"GTJA191", internal quant report) alpha `#55`, per issue #80, which
attributes its copy of the report to HKUDS/Vibe-Trading (MIT) -- a copy
NOT read in this session, see the disclosure below. The formula string the
issue itself quotes is ELIDED:

    #55: SUM(16*(...)/R*MAX(|H-C1|,|L-C1|), 20)

**What this session could NOT do, disclosed up front.** `docs/pine/` and
web access are both unavailable in this worktree, so the issue's own named
copy -- HKUDS/Vibe-Trading (MIT) -- was never read, and the issue's own
quote of the formula hides its numerator and its `R` behind `(...)`. Two
sources were therefore available here, and they DISAGREE:

1. The issue's prototype (`docs/issues/screen/ind_screen.py:398-405`), the
   only machine-readable copy in this worktree:

       @cand("g191_055", "20-day Wilder swing-index sum", G,
             "#55: SUM(16*(...)/R*MAX(|H-C1|,|L-C1|), 20)", "/close")
       def _(o, h, l, c, v):
           c1, o1, l1 = delay(c, 1), delay(o, 1), delay(l, 1)
           a, b, d = (h - c1).abs(), (l - c1).abs(), (h - l1).abs()
           e = (c1 - o1).abs()
           r = pd.Series(np.where((a > b) & (a > d), a + b / 2 + e / 4, b + a / 2 + e / 4), index=c.index)
           si = 16 * sdiv(c - c1 + (c - o) / 2 + c1 - o1, r) * np.maximum(a, b)
           return tsum(si, 20) / c

   That `r` has TWO branches.
2. The GTJA191 report's own `#55` string as this session RECALLS it (and
   only as it recalls it -- see "The weakest link" below), whose `R` has
   THREE branches:

       R = (A>B & A>D) ? A + B/2 + E/4
         : (B>D & B>A) ? B + A/2 + E/4
         : D + E/4            with A=|H-C1|, B=|L-C1|, D=|H-L1|, E=|C1-O1|

**This port ships the THREE-branch R**, because issue #80's own Gates-owed
line says "Gate A starts from the source formula, not the prototype". TWO
pieces of evidence inside this worktree, plus ONE recalled fact about
Wilder's own construction (labelled as such, carrying exactly the weight
of (2) and no more), say the source formula has the third branch and the
prototype collapsed it:

* The prototype computes `d = |H - L1|` and then uses it in NOTHING but the
  FIRST branch's test (`(a > b) & (a > d)`). A two-branch `R` has no reason
  to know `d` at all: the only construction in which `d` belongs in a test
  is one where `d` can also be the SELECTED term. The prototype's own
  unused half of `d` is the fingerprint of a dropped third branch. Worse
  for the two-branch reading, that test can NEVER pass on OHLC-consistent
  data (proved and measured under "BRANCH 1 IS UNREACHABLE" below), so the
  prototype's `R` reduces to the single expression `B + A/2 + E/4` -- a
  "swing index" whose range denominator ignores `|H - L1|` entirely, which
  is not Wilder's construction under any reading.
* The prototype's first test is `(a > b) & (a > d)` -- a conjunction over
  three quantities -- while its second "branch" has no test at all. The
  canonical shape of that pattern is a 3-way argmax, whose middle test
  (`(b > d) & (b > a)`) the prototype dropped along with the `D + E/4`
  arm.
* The issue names the construction "**Wilder** swing-index sum" and names
  the denominator `R` -- that much is in the worktree. RECALLED, NOT IN
  THIS WORKTREE: Wilder's Swing Index defines `R` by three cases on which
  of `|H-C1|`, `|L-C1|`, `|H-L1|` is the largest, the same three
  quantities the prototype computes. Nothing available here can check
  that, so this bullet is recall dressed in the issue's own wording, not
  in-repo evidence.

**The weakest link, stated plainly.** The three-branch string in (2) is
RECALLED, not read: no copy of the GTJA191 report was readable in this
worktree. So the third branch rests on this session's recall plus the
three in-repo corroborations above, not on a transcription. If the owner's
copy turns out to carry a two-branch `R`, the fix is to replace the inner
`np.where` below with its `b + a / 2 + e / 4` arm -- one line, which is
exactly `docs/measure_g191_055.py`'s `TWO_BRANCH_R` mutant, so the size of
the decision is on the record rather than assumed. Measured on the
1,500-bar synthetic walk: the two forms differ at **1,480 of 1,480**
non-NaN bars, max |diff| **2.3181**, Spearman ρ **0.9675**, and **962 of
1,499** bars take the third branch. `docs/G191055Measured.md` carries
those numbers with the rest.

WHAT GTJA191's `#55` IS NOT: Wilder's own Swing Index, whose first two
cases SUBTRACT half the smaller term (`R = A - B/2 + E/4`) and whose
constant is `50 / T` (`T` = the limit move) rather than `16`. GTJA191's
string adds (`A + B/2 + E/4`) and uses `16`; this port follows GTJA191,
which is what the issue asks for ("Source: GTJA191"). The prototype also
adds, so the `+` is corroborated in-repo; the claim about Wilder's own
signs is RECALLED, like (2), and nothing in this worktree can check it.

OPERATORS, each read directly off the prototype's own (unambiguous) module
source, the same source every other `g191_*` port in this fork relies on:

* `C1`, `O1`, `L1` denote close/open/low delayed one bar,
  `DELAY(X, 1) = X.shift(1)` (`ind_screen.py:45`), a BACKWARD shift (bar
  `t` reads bar `t-1`), never a look-ahead.
* `SUM(X, n)` = `X.rolling(n).sum()` (`ind_screen.py:49`), a trailing
  `n`-bar sum with pandas' default `min_periods=n`, so one NaN anywhere in
  the window makes the output NaN. Written out as
  `rolling(length, min_periods=length)` here, the same explicit spelling
  `g191_003` uses, so the warm-up does not depend on a pandas default.
* `sdiv(a, b)` = `a / b` with `±inf` replaced by NaN (`ind_screen.py:37-42`),
  the prototype's safe divide. It is load-bearing here: `R` CAN be exactly
  zero (see "R == 0" below).
* `|X|` is the pointwise absolute value, `MAX(X, Y)` the pointwise
  two-argument maximum -- not the windowed `TSMAX` GTJA191 uses elsewhere
  (`ind_screen.py:50-51`). The prototype writes `np.maximum(a, b)`.
* `/2` and `/4` are true division; `16` is a float multiplier. Nothing
  here is integer arithmetic.

CALCULATION, in the order computed below (`length=20`, the issue's own
fixed "20" exposed as a tunable, this fork's convention for every other
GTJA191/Alpha101 port):
    C1, O1, L1 = DELAY(C,1), DELAY(O,1), DELAY(L,1)
    A, B, D, E = |H-C1|, |L-C1|, |H-L1|, |C1-O1|
    R        = (A>B & A>D) ? A + B/2 + E/4
             : (B>D & B>A) ? B + A/2 + E/4
             : D + E/4
    N        = C - C1 + (C - O)/2 + C1 - O1
    SI       = 16 * (N / R) * MAX(A, B)        # inf -> NaN
    G191_055 = SUM(SI, length) / C

THE NUMERATOR'S PROVENANCE, stated as precisely as `R`'s. Unlike `R`,
`N = C - C1 + (C - O)/2 + C1 - O1` is read straight off the prototype
(`ind_screen.py:404`, `c - c1 + (c - o) / 2 + c1 - o1`) -- it has an
IN-REPO source -- and the recalled report string agrees with it term for
term, so the two sources that disagree about `R` agree about `N`. Nothing
about the numerator rests on recall alone.

THE NUMERATOR IS COMPUTED IN THE SOURCE'S WRITTEN ORDER, deliberately.
`C - C1 + (C - O)/2 + C1 - O1` cancels algebraically to
`C + (C - O)/2 - O1` -- `DELAY(C,1)` drops out of the numerator entirely,
so `C1` survives only inside `A`, `B`, `E` and `R`. The source's order is
kept for FIDELITY, the same reason CLAUDE.md gives for summing TA-Lib's
Hilbert taps in TA-Lib's order, and NOT because the two spellings were
found to differ numerically: measured on the 1,500-bar synthetic walk,
they agree bit-for-bit (**max |diff| 0.0, 0 of 1,499 bars differing**),
so on that frame the choice costs nothing either way. It is reported by
`docs/measure_g191_055.py` rather than assumed in both directions.

BRANCH 1 IS UNREACHABLE on OHLC-consistent data, and that is a derivation,
not an accident of one frame. Branch 1 needs `A > B` AND `A > D`, with
`A = |H-C1|`, `B = |L-C1|`, `D = |H-L1|`. Split on `H` against `C1`:

* `H >= C1`: then `A = H - C1` and, since `L1 <= C1` (bar `t-1`'s low
  cannot exceed its close), `D = H - L1 >= H - C1 = A`. So `A > D` fails.
* `H <= C1`: then `A = C1 - H` and, since `L <= H` (bar `t`'s low cannot
  exceed its high), `B = C1 - L >= C1 - H = A`. So `A > B` fails.

The two cases cover every bar, so no OHLC-consistent bar can select branch
1. Measured on the 1,500-bar walk (**1,500 of 1,500 bars OHLC-consistent**):
branch 1 fires **0** times, branch 2 **537**, branch 3 **962**, of the
1,499 bars that have a prior bar; and the two inequalities the proof rests
on are violated **0** times each. The arm is kept anyway, because it is in
the source formula and because an inconsistent frame (bad vendor data,
`L > H`) can still reach it -- but no claim here depends on it, and
`tests/test_g191_055.py::test_branch_one_is_unreachable_on_consistent_ohlc`
pins both the census and the two inequalities.

A CONSEQUENCE WORTH SPELLING OUT: branch 1 is also the prototype's ONLY
branch test, so the prototype's `R` is `B + A/2 + E/4` on every
OHLC-consistent bar -- its first arm is dead code. The port therefore
agrees with the prototype exactly on branch-2 bars and differs on every
branch-3 bar, which on the walk is 962 of 1,499 bars (64%). Measured per
bar at `length=1`: **537 of 537** branch-2 bars bit-identical to the
prototype's SI, **0 of 962** branch-3 bars. On the column itself the two
forms differ at **1,480 of 1,480** non-NaN bars (no 20-bar window on the
walk is all-branch-2: the longest run of consecutive branch-2 bars is
**6**), max |diff| **2.3181**, Spearman ρ **0.9675**. This is NOT a corner
case, and pretending otherwise would be the "claim written before it was
measured" defect CLAUDE.md names.

`R == 0`, THE ONE DEGENERATE CASE, and it is reachable. `R` is a sum of
non-negative terms, so `R == 0` needs every term of the SELECTED branch to
vanish. Worked out branch by branch:

* Branch 1 is selected only when `A > B >= 0`, so `A > 0` and
  `R = A + B/2 + E/4 > 0`. It can never be zero.
* Branch 2 is selected only when `B > D >= 0`, so `B > 0` and likewise
  `R > 0`.
* Branch 3's value is `D + E/4`, which is zero iff `D == 0` and `E == 0`.
  And branch 3 is selected, given `D == 0`, only when `A == B`: if
  `A > B >= 0` then `A > 0 == D` and branch 1 takes it; if `B > A >= 0`
  then `B > 0 == D` and branch 2 does.

So `R == 0` iff `|H - L1| == 0`, `|C1 - O1| == 0` and `|H-C1| == |L-C1|`.
The last one has two solutions, `H == L` and `H + L == 2*C1`, and OHLC
consistency on bar `t-1` kills the second: it would need
`C1 = (H+L)/2 >= H = L1` -- but `C1 >= L1` means `(H+L)/2 >= H`, i.e.
`L >= H`, which contradicts `H > L`. What is left is one bar shape:

    bar t-1 opened and closed at the same price (`O1 == C1`), and
    bar t is ZERO-RANGE (`H == L`, hence `C == H == L`) printing exactly
    at bar t-1's low (`H == L1`).

A halt, a limit-locked print, or an untraded day carried forward, after a
doji. Note `C == C1` is NOT required: `L1 <= C1` only forces the frozen
print to sit at or below the prior close. There `N / R` is `x/0` (with
`O == C` and `O1 == C1` the numerator collapses to `C - C1`, non-zero
whenever the frozen print is below the prior close) or `0/0` (when it is
exactly at it); pandas gives `±inf` for the first and NaN for the second,
and `sdiv`'s `inf -> NaN` turns both into NaN. Because `SUM` uses
`min_periods=length`, ONE such bar NaNs the `length` outputs whose window
contains it. That is a real reachability cost on exchange data with halts,
not a theoretical one, and it is why Gate C's real-data count matters more
here than on a port with no division.
`tests/test_g191_055.py::test_zero_r_bar_nans_its_whole_window` pins the
shape and the propagation on a hand-built fixture, and
`docs/measure_g191_055.py` counts how often the synthetic walk reaches it
(**0 of 1,500 bars** -- continuous floats never print a zero-range bar, so
the fixture is the only coverage this session has).

CAUSALITY. `C1[t]`, `O1[t]`, `L1[t]` read only bar `t-1`. `A`, `B`, `D`,
`E`, `R`, `N` and `SI` are pointwise functions of bar `t` and those
delayed values -- bars no newer than `t`. `SUM(SI, length)[t]` is a
trailing `length`-bar sum over `[t-length+1, t]`, every index `<= t`. The
final division by `C[t]` reads only bar `t`. Nothing in the chain reads a
bar newer than `t`. `tests/test_g191_055.py` proves this both by
future-perturbation (real module: 0 of N offsets leak, with
open/high/low/close rewritten jointly from an offset onward) and by two
mutants (`importlib` source read, `exec`'d in memory, each shown live
different from the real module): shifting the final write index `length`
bars into the future, and computing the rolling sum with
`rolling(length, center=True)` instead of the causal trailing window --
the same `bos` look-ahead bug class CLAUDE.md documents.

WARM-UP. `C1`, `O1` and `L1` are undefined at bar 0 (no prior bar), so
`SI` is masked to NaN there. `SUM(SI, length)` with `min_periods=length`
needs `length` CONSECUTIVE valid `SI` values ending at `t`, i.e.
`t - length + 1 >= 1`, i.e. `t >= length` -- `min_length = length + 1`
bars of history (**21** at the shipped default), enforced by
`verify_series`. The mask is DECLARATIVE, and this port says so rather
than claiming it is load-bearing: at bar 0 every one of `A`, `B`, `D`, `E`
is NaN, all three branch tests are False, and the third branch's
`D + E/4` is NaN too, so the arithmetic alone already lands NaN there. The
mask makes the reading explicit and survives a later edit to the branch
tests; `tests/test_g191_055.py::test_bar_zero_is_masked` pins the outcome
at `length=1`, where nothing else can hide it. Beyond bar 0, `R == 0` is
the other NaN source (above).

SCALE-FREE. Let `k > 0` rescale price (`open, high, low, close ->
k*open, k*high, k*low, k*close`). The delays carry no arithmetic, so
`C1, O1, L1 -> k*C1, k*O1, k*L1`. Then `A, B, D, E -> k*A, k*B, k*D, k*E`
(absolute value is positively homogeneous: `|k*x| = k*|x|` for `k > 0`).
All three branch TESTS are scale-invariant, since `k*x > k*y` iff `x > y`
for `k > 0` (multiplication by a positive constant is strictly monotone on
the reals), so the SAME branch is selected and `R -> k*R`. `N` is a sum of
differences, so `N -> k*N`; `MAX(A,B) -> k*MAX(A,B)`. Hence
`SI = 16*(N/R)*MAX(A,B) -> 16*((k*N)/(k*R))*(k*MAX) = k*SI`, the `R == 0`
test included (`k*0 == 0`). `SUM(SI, length) -> k*SUM`, and the final
division by `C -> k*C` gives `(k*SUM)/(k*C) = SUM/C` -- the `k` cancels
EXACTLY, for ANY positive `k`. Measured on a synthetic walk: PRICE ×8/×64
land bit-identical (power-of-two multiplication is exact in IEEE754, so
the cancellation is exact in floating point too), while ×10/×3.7 come out
within float64 rounding tolerance of the unscaled column. One float-only
caveat, disclosed because the branch tests are exact comparisons: at a
non-power-of-two `k` the module does NOT compute `k*A` but
`fl(fl(k*H) - fl(k*C1))`, a difference of SEPARATELY rounded products,
which is not the same float as `fl(k*A)`. So for two nearly equal branch
quantities a strict `>` can in principle go either way -- tie OR invert,
not just tie; monotonicity of `x -> k*x` does not cover it, because the
compared values are not the scaled originals.
`docs/measure_g191_055.py` measures the selected-branch masks themselves
under each `k` and reports whether any bar changed branch (on the
1,500-bar walk: none, at every one of the four multipliers), and
`tests/test_g191_055.py::test_price_scale_moves_no_bar_between_branches`
asserts it through the module. Measured, not merely asserted.
"""
import numpy as np
import pandas as pd

from pandas_ta.utils import get_offset, verify_series


def g191_055(open_, high, low, close, length=None, offset=None, **kwargs):
    """Indicator: 20-Day Wilder Swing-Index Sum (G191_055)"""
    # Validate Arguments
    length = int(length) if length and length > 0 else 20
    min_length = length + 1
    open_ = verify_series(open_, min_length)
    high = verify_series(high, min_length)
    low = verify_series(low, min_length)
    close = verify_series(close, min_length)
    offset = get_offset(offset)

    if open_ is None or high is None or low is None or close is None:
        return

    if not (
        close.index.equals(open_.index)
        and close.index.equals(high.index)
        and close.index.equals(low.index)
    ):
        raise ValueError(
            "g191_055: `open_`, `high`, `low` and `close` are indexed "
            "differently. A swing index read off misaligned series is a "
            "silent nonsense number."
        )

    # Calculate Result
    prev_close = close.shift(1)
    prev_open = open_.shift(1)
    prev_low = low.shift(1)

    a = (high - prev_close).abs()        # |H - C1|
    b = (low - prev_close).abs()         # |L - C1|
    d = (high - prev_low).abs()          # |H - L1|
    e = (prev_close - prev_open).abs()   # |C1 - O1|

    r = pd.Series(
        np.where(
            (a > b) & (a > d),
            a + b / 2 + e / 4,
            np.where((b > d) & (b > a), b + a / 2 + e / 4, d + e / 4),
        ),
        index=close.index,
    )
    # Source order kept for fidelity (CLAUDE.md's Hilbert-tap reason), not
    # for numerics: C1 cancels algebraically, and the simplified spelling
    # measures bit-identical, 0 of 1,499 bars (docs/measure_g191_055.py).
    numerator = close - prev_close + (close - open_) / 2 + prev_close - prev_open

    with np.errstate(divide="ignore", invalid="ignore"):
        swing = (numerator / r).replace([np.inf, -np.inf], np.nan)
    swing = (16 * swing * np.maximum(a, b)).where(
        prev_close.notna() & prev_open.notna() & prev_low.notna()
    )

    result = swing.rolling(length, min_periods=length).sum() / close

    # Offset
    if offset != 0:
        result = result.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        result.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        result.fillna(method=kwargs["fill_method"], inplace=True)

    # Name & Category
    result.name = f"G191_055_{length}"
    result.category = "momentum"

    return result


g191_055.__doc__ = \
"""20-Day Wilder Swing-Index Sum (G191_055)

Guotai Junan's (2017, "GTJA191") alpha `#55`, per issue #80. Each bar gets
a Swing Index: the bar's directional move (close against the prior close,
plus half its own open-to-close body, plus the prior bar's body) divided by
a range reference `R` -- whichever of `|H-C1|`, `|L-C1|`, `|H-L1|` is the
largest, blended with half the runner-up and a quarter of the prior body --
then scaled by the larger of the two close-to-extreme gaps. Summed over a
trailing window and divided by close for a scale-free result, which is
GTJA191's variant of Wilder's Accumulated Swing Index: a 20-bar tally of
how much of the recent range the tape actually travelled, signed by
direction.

This fork ships no other Swing Index / ASI construction (measured: one
case-insensitive content search for `swing[ _-]?index|accum\\w* swing|\\bASI\\b`
over `pandas_ta/**/*.py` matches THIS FILE AND NOTHING ELSE. A looser
search for bare `swing` matches 31 files, one of which is this one. The
count quoted here is deliberately the one over the OTHER 30, because a
total would include this docstring and would move every time anyone edits
it: ripgrep's count mode (`rg -ic swing` over `pandas_ta/**/*.py`), summed
over all files except this one, gives **349 matching LINES across the
other 30**. No whole-tree total is quoted anywhere here, deliberately: one
was, it counted this docstring, and editing the docstring moved it. (Lines
are not occurrences, either -- several of the 349 carry the word twice.)
The evidence that none of those 30 is
a Swing Index is the index-pattern search above matching none of them --
not a reading of all 349 lines, which this session did not do. Those 30
are the
SMC / pivot-structure detectors (`trend/swing_equilibrium.py`,
`trend/bos.py`, `trend/choch.py`, `trend/sr_decay.py`,
`trend/zigzag_fib.py` and so on), their package and accessor plumbing
(`pandas_ta/__init__.py:85`, `trend/__init__.py:50`, `core.py`'s
`swing_*` keyword arguments) and bare uses of the word for a price swing
in modules that are something else entirely -- `momentum/tsi.py:53`,
`overlap/kama.py:58`, `volatility/wvma.py:65`, `volume/volcv.py:39`).
Full Gate A derivation -- including the two-branch versus
THREE-branch `R` disagreement between the issue's prototype and the
report's own string, which this port resolves in favour of the three-branch
form and measures -- plus the causality and scale-free arguments are in the
module source above; see docs/G191055Measured.md for the measured numbers.

Calculation:
    Default Inputs:
        length=20
    C1, O1, L1 = DELAY(close,1), DELAY(open,1), DELAY(low,1)
    A, B, D, E = |high-C1|, |low-C1|, |high-L1|, |C1-O1|
    R        = (A>B & A>D) ? A + B/2 + E/4
             : (B>D & B>A) ? B + A/2 + E/4
             : D + E/4
    N        = close - C1 + (close - open)/2 + C1 - O1
    SI       = 16 * (N / R) * MAX(A, B)        # inf -> NaN
    G191_055 = SUM(SI, length) / close

Args:
    open_ (pd.Series): Series of 'open's
    high (pd.Series): Series of 'high's
    low (pd.Series): Series of 'low's
    close (pd.Series): Series of 'close's
    length (int): Rolling window for the sum. Default: 20
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.Series: G191_055_{length}, a scale-free (dimensionless) column,
        SIGNED and UNBOUNDED: positive when the window's up-swings
        outweigh its down-swings, negative otherwise. NaN for the first
        `length` bars (`min_length - 1`, 20 at the shipped default), and
        NaN for the `length` windows containing any bar whose `R` is
        exactly zero -- a zero-range bar printing at the prior bar's low,
        where that prior bar opened and closed at the same price (see the
        module source's "R == 0" section for the derivation).
"""
