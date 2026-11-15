# -*- coding: utf-8 -*-
"""6-Day Accumulation/Distribution Sum (G191_003) -- Guotai Junan's (2017,
"GTJA191", internal quant report) alpha `#3`, per issue #79, which
attributes its copy of the report to HKUDS/Vibe-Trading (MIT) -- a copy
NOT read in this session, see the disclosure below. Source cited by the
issue:

    #3: SUM(C=C1 ? 0 : C-(C>C1 ? MIN(L,C1) : MAX(H,C1)), 6)

**What this session could NOT do, disclosed up front:** `docs/pine/` and
web access are both unavailable in this worktree, so the issue's own named
copy -- HKUDS/Vibe-Trading (MIT) -- was never read. The formula below is
derived from the issue's own stated text (itself a quote of the GTJA191
report), per the issue's own instruction ("Gate A starts from the source
formula, not the prototype"), then cross-checked against the issue's own
prototype (`docs/issues/screen/ind_screen.py:282-287`):

    @cand("g191_003", "6-day accumulation/distribution sum", G,
          "#3: SUM(C=C1 ? 0 : C-(C>C1 ? MIN(L,C1) : MAX(H,C1)), 6)", "/close")
    def _(o, h, l, c, v):
        c1 = delay(c, 1)
        x = np.where(c == c1, 0.0, c - np.where(c > c1, np.minimum(l, c1), np.maximum(h, c1)))
        return tsum(pd.Series(x, index=c.index).where(c1.notna()), 6) / c

The issue's own string and the prototype agree, including the 6-bar window
and the issue's own scale-free conversion ("/close", the `conv` field of
that same `@cand` line). Three readings of the formula string had to be
FIXED rather than left open; all three follow the prototype, which is the
only disambiguating source available here:

1. `C=C1` is a COMPARISON (`close == close.shift(1)`), not an assignment --
   GTJA191's pseudo-code spells equality with a single `=` inside a
   ternary condition. The prototype writes `c == c1`.
2. `MIN(L,C1)` / `MAX(H,C1)` are POINTWISE two-argument min/max of two
   series, not the windowed `TSMIN`/`TSMAX` operators GTJA191 uses
   elsewhere -- the screen defines those separately as `tsmin`/`tsmax`
   (`ind_screen.py:50-51`), and `g191_098` is this fork's port of a
   formula that uses one (`pandas_ta/trend/g191_098.py:44`, `TSMIN(X, n) =
   X.rolling(n).min()`). The prototype writes `np.minimum(l, c1)` /
   `np.maximum(h, c1)`, pointwise.
3. The bar-0 boundary: `C1` is undefined at bar 0, where the ternary's
   `C=C1` test is neither true nor false. The prototype resolves it by
   masking (`.where(c1.notna())`), so bar 0 is NaN rather than 0.0, and
   the trailing sum's `min_periods` then carries that NaN forward for the
   first `length` bars. This port does the same. (NumPy alone would not:
   `c == c1` is `False` against a NaN, which would send bar 0 down the
   `MAX(H,C1)` branch, and `np.maximum(h, nan)` is NaN there, so the bar
   would be NaN by accident rather than by decision. The explicit mask
   makes it a decision, and `tests/test_g191_003.py` pins it.)

OPERATORS, each read directly off the prototype's own (unambiguous) module
source, the same source every other `g191_*` port in this fork relies on:

* `C1` denotes `C` delayed one bar, `DELAY(C, 1) = C.shift(1)`
  (`ind_screen.py:45`), a BACKWARD shift (bar `t` reads bar `t-1`), never a
  look-ahead.
* `SUM(X, n)` = `X.rolling(n).sum()` (`ind_screen.py:49`), a trailing
  `n`-bar sum with pandas' default `min_periods=n`, so one NaN anywhere in
  the window makes the output NaN. Written out as
  `rolling(length, min_periods=length)` here, the same explicit spelling
  `g191_129` uses, so the warm-up does not depend on a pandas default.
* `C`, `H`, `L` = close, high, low of the CURRENT bar. `OPEN` and `VOLUME`
  are not read.

CALCULATION, in the order computed below (`length=6`, the issue's own fixed
"6" exposed as a tunable, this fork's convention for every other
GTJA191/Alpha101 port):
    C1       = DELAY(C, 1)
    ref      = C > C1 ? MIN(L, C1) : MAX(H, C1)
    bar      = C = C1 ? 0 : C - ref      # NaN at bar 0, where C1 is undefined
    G191_003 = SUM(bar, length) / C

WHY THE `C=C1` BRANCH IS LOAD-BEARING, unlike `g191_129`'s `clip`. Drop the
ternary's zero branch and a flat bar would take the `MAX(H,C1)` route
(`C > C1` is false when `C == C1`), giving `C - MAX(H, C) = C - H <= 0` --
a NEGATIVE contribution on a bar whose close did not move at all. The zero
is therefore a real branch, not a restatement of the other two. The two
forms' per-bar CONTRIBUTIONS differ at exactly the bars where `C == C1`
and `H > C`; the COLUMN differs at every NON-NaN trailing `length`-bar
window containing such a bar, so one flat bar moves UP TO `length`
outputs -- fewer when the warm-up or the end of the series clips some of
those windows. On the fixture in `tests/test_g191_003.py`, `length=3`
with the flat bar at index 2: three windows hold it (`t=2,3,4`), `t=2` is
still inside the warm-up and NaN in both forms, so **2** outputs move
(`t=3` and `t=4`), identical again from `t=5`.
`tests/test_g191_003.py::test_the_flat_close_branch_is_not_redundant`
pins that divergence on a dedicated fixture, and
`docs/measure_g191_003.py` reports how often a continuous-float synthetic
walk reaches the branch at all (**0 of 1,500 bars** on the shipped walk --
disclosed, not glossed over: the branch is EFFECTIVELY unreachable on
continuous floats -- an exactly-zero increment has probability ~0 on a
float64 draw, not zero -- and plausibly common on tick-rounded exchange
data, by analogy only: neither this session nor CLAUDE.md measures
`C == C1` frequency, and the nearest measured number is a DIFFERENT
statistic, the `fvg`/FVGDEAD note's 21.17% of BIST daily bars closing
exactly at an extreme, i.e. `C == H` or `C == L`).

PER-BAR SIGN, a structural property of the two live branches, holding
unconditionally -- no OHLC-consistency assumption needed -- and measured on
the walk as a check rather than as the proof: on an up bar (`C > C1`) the
reference is `MIN(L, C1) <= C1 < C`, so `C - MIN(L,C1)` is strictly
POSITIVE; on a down bar (`C < C1`) the reference is `MAX(H, C1) >= C1 > C`,
so `C - MAX(H,C1)` is strictly NEGATIVE. The window sum is therefore a
signed accumulation/distribution tally, NOT a non-negative magnitude like
`g191_129`'s. Measured on the 1,500-bar walk: 0 of 762 up bars contribute
`<= 0`, 0 of 737 down bars contribute `>= 0`.

CAUSALITY. `C1[t]` reads only `C[t-1]`. `ref[t]` and `bar[t]` are pointwise
functions of `C[t]`, `H[t]`, `L[t]` and `C1[t]` -- bars no newer than `t`.
`SUM(bar, length)[t]` is a trailing `length`-bar sum over the window
`[t-length+1, t]`, every index `<= t`. The final division by `C[t]` reads
only bar `t`. Nothing in the chain reads a bar newer than `t`.
`tests/test_g191_003.py` proves this both by future-perturbation (real
module: 0 of N offsets leak, with high/low/close rewritten jointly from an
offset onward) and by two mutants (`importlib` source read, `exec`'d in
memory, each shown live different from the real module): shifting the final
write index `length` bars into the future, and computing the rolling sum
with `rolling(length, center=True)` instead of the causal trailing window
-- the same `bos` look-ahead bug class CLAUDE.md documents.

WARM-UP. `C1` is undefined at bar 0 (no prior bar), so `bar` is masked to
NaN there (see reading 3 above). `SUM(bar, length)` with
`min_periods=length` needs `length` CONSECUTIVE valid `bar` values ending
at `t`, i.e. `t - length + 1 >= 1`, i.e. `t >= length` -- `min_length =
length + 1` bars of history (**7** at the shipped default), enforced by
`verify_series`. No other NaN source exists in the chain: unlike
`g191_002`, there is no ratio whose denominator can vanish inside the
window, and the only division is by `close` itself (a zero close is not an
OHLC bar this fork models anywhere, and would make the scale-free
conversion meaningless rather than merely NaN).

SCALE-FREE. Let `k > 0` rescale price (`high, low, close -> k*high, k*low,
k*close`). `C1 = DELAY(C,1)` carries no arithmetic, so it scales to
`k*C1`. Both branch TESTS are scale-invariant: `k*C > k*C1` iff `C > C1`
and `k*C == k*C1` iff `C == C1`, for any `k > 0` (multiplication by a
positive constant is strictly monotone on the reals). `MIN`/`MAX` select an
argument rather than computing one, so `MIN(k*L, k*C1) = k*MIN(L, C1)` and
likewise for `MAX`. Hence `bar` scales to `k*bar` at every bar,
`SUM(bar, length)` to `k*SUM(bar, length)`, and the final division by
`C -> k*C` gives `(k*SUM)/(k*C) = SUM/C` -- the `k` cancels EXACTLY, for
ANY positive `k`. Measured on a synthetic walk: PRICE x8/x64 land
bit-identical (power-of-two multiplication is exact in IEEE754, so the
cancellation is also exact in floating point), while x10/x3.7 come out
within float64 rounding tolerance of the unscaled column (the subtraction
and rolling-sum arithmetic rounds differently at a non-power-of-two
multiplier, even though the true mathematical ratio is identical). One
float-only caveat, disclosed because the branch tests are exact
comparisons: `k*a == k*b` can hold in float64 for two distinct `a != b`
that round to the same product, which would move a bar from a live branch
into the zero branch. `docs/measure_g191_003.py` measures the branch masks
themselves under each `k` and reports whether any bar changed branch (on
the 1,500-bar walk: none, at every one of the four multipliers). Measured
in the test file and `docs/measure_g191_003.py`, not merely asserted.
"""
import numpy as np
from pandas import Series

from pandas_ta.utils import get_offset, verify_series


def g191_003(high, low, close, length=None, offset=None, **kwargs):
    """Indicator: 6-Day Accumulation/Distribution Sum (G191_003)"""
    # Validate Arguments
    length = int(length) if length and length > 0 else 6
    min_length = length + 1
    high = verify_series(high, min_length)
    low = verify_series(low, min_length)
    close = verify_series(close, min_length)
    offset = get_offset(offset)

    if high is None or low is None or close is None:
        return

    if not (high.index.equals(low.index) and high.index.equals(close.index)):
        raise ValueError(
            "g191_003: `high`, `low` and `close` are indexed differently. An "
            "accumulation/distribution sum read off misaligned series is a "
            "silent nonsense number."
        )

    # Calculate Result
    prev_close = close.shift(1)
    ref = np.where(
        close > prev_close,
        np.minimum(low, prev_close),
        np.maximum(high, prev_close),
    )
    bar = Series(
        np.where(close == prev_close, 0.0, close - ref), index=close.index
    ).where(prev_close.notna())
    result = bar.rolling(length, min_periods=length).sum() / close

    # Offset
    if offset != 0:
        result = result.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        result.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        result.fillna(method=kwargs["fill_method"], inplace=True)

    # Name & Category
    result.name = f"G191_003_{length}"
    result.category = "momentum"

    return result


g191_003.__doc__ = \
"""6-Day Accumulation/Distribution Sum (G191_003)

Guotai Junan's (2017, "GTJA191") alpha `#3`, per issue #79. Each bar
contributes the distance from its close to a DIRECTIONAL reference price:
on an up bar (close above the prior close) the lower of today's low and the
prior close, giving a positive contribution; on a down bar the higher of
today's high and the prior close, giving a negative one; on a flat bar
(close exactly equal to the prior close) exactly zero. Summed over a
trailing window and divided by close for a scale-free result -- the
windowed form of Williams' cumulative Accumulation/Distribution, which this
fork does not otherwise ship (the volume-weighted `ad` is a different
construction). Full Gate A derivation, the three fixed readings of the
source string, causality and scale-free arguments are in the module source
above; see docs/G191003Measured.md for the measured numbers.

Calculation:
    Default Inputs:
        length=6
    C1       = DELAY(close, 1)
    ref      = close > C1 ? MIN(low, C1) : MAX(high, C1)
    bar      = close == C1 ? 0 : close - ref
    G191_003 = SUM(bar, length) / close

Args:
    high (pd.Series): Series of 'high's
    low (pd.Series): Series of 'low's
    close (pd.Series): Series of 'close's
    length (int): Rolling window for the sum. Default: 6
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.Series: G191_003_{length}, a scale-free (dimensionless) column,
        SIGNED: positive when the window's up-bar contributions outweigh
        its down-bar contributions in MAGNITUDE (not in count -- one large
        up bar outweighs three small down bars), negative when the
        down-bar contributions outweigh them, and ZERO when they balance
        -- exactly `0.0` for a window whose closes are all flat, where
        every bar takes the `C=C1` zero branch and the sum is bit-exact
        (`tests/test_g191_003.py::test_an_all_flat_window_is_exactly_zero`);
        a MIXED window that cancels only in real arithmetic can land
        within float64 rounding of zero rather than on it -- not measured,
        since the 1,500-bar walk produces no zeros of either kind. NaN for
        the first `length` bars (`min_length - 1`, 6 at the shipped
        default).
"""
