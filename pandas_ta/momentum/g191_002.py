# -*- coding: utf-8 -*-
"""One-Day Change Of Close Location -- Guotai Junan's (2017, "GTJA191",
internal quant report, read via the HKUDS/Vibe-Trading copy, MIT) alpha
`#2`, per issue #63. Source cited by the issue:

    #2: -DELTA(((C-L)-(H-C))/(H-L),1)

**What this session could NOT do, disclosed up front:** `docs/pine/` and
web access are both unavailable in this worktree, so the issue's own named
copy -- HKUDS/Vibe-Trading (MIT) -- was never read. The formula below is
derived from the issue's own stated text (itself a quote of the GTJA191
report), per the issue's own instruction ("Gate A starts from the source
formula, not the prototype").

GATE A -- DERIVATION. The issue's own prototype
(`docs/issues/screen/ind_screen.py:278-279`, candidate `g191_002`) spells
out the identical formula directly:

    @cand("g191_002", "one-day change of close location", G,
          "#2: -DELTA(((C-L)-(H-C))/(H-L),1)")
    def _(o, h, l, c, v): return -delta(clv(h, l, c), 1)

with `clv` and `delta` defined in the same module (`ind_screen.py:110`,
`:46`):

    def clv(h, l, c): return sdiv((c - l) - (h - c), h - l)
    def delta(x, n): return x - x.shift(n)

and `sdiv`/`_fin` (`:41-42`, `:37-38`):

    def sdiv(a, b): return _fin(a / b)
    def _fin(x): return x.replace([np.inf, -np.inf], np.nan)

No disclosed interpretation choice was needed for the formula itself --
the issue's own string and the prototype agree exactly. `clv` is the
"close location value": `(C-L)-(H-C) = 2*C-H-L`, so
`clv = (2*C-H-L)/(H-L)` -- the same algebraic simplification
`pandas_ta.momentum.a101_053` already uses for its own close-location
ratio, which has a DIFFERENT denominator (`close-low`, not `high-low`)
and a different source formula (Alpha101 `#53`, not GTJA191 `#2`); the two
are not a restatement of each other on the numerator alone, since the
denominators diverge whenever `close != high`.

OPERATORS, each read directly off the prototype's own (unambiguous)
module source, the same source every other `g191_*`/`a101_*` port in this
fork relies on:

* `DELTA(X, n)` = `X - X.shift(n)` (`ind_screen.py:46`), a plain backward
  `n`-bar difference -- never a look-ahead.
* `CLV(H, L, C)` = `sdiv((C-L)-(H-C), H-L)` (`:110`), a pointwise ratio on
  the CURRENT bar's own high/low/close, reading no other bar.
* `sdiv(a, b)` = `a / b` with `+-inf` mapped to `NaN` (`:41-42`, `:37-38`)
  -- the fork's own existing convention for a formula-ratio division
  (`a101_053`'s `(close-low)` denominator, `a101_021`/`a101_043`'s
  `volume/adv`).

CALCULATION, in the order computed below (`length=1`, the issue's own
fixed "1" exposed as a tunable, matching this fork's convention for every
other DELTA-based GTJA191/Alpha101 port -- `a101_053`'s own `length=9`
default):
    clv       = (2*close - high - low) / (high - low)   # NaN where high==low
    d1        = DELTA(clv, length)
    G191_002  = -d1 = clv.shift(length) - clv

CAUSALITY. `clv[t]` is a pointwise function of `high[t]`, `low[t]` and
`close[t]` only -- it reads no other bar. `d1[t] = clv[t] - clv[t-length]`
reads only `clv[t]` and `clv[t-length]`, both indices `<= t`. The final
negation is pointwise. Nothing in the chain reads a bar newer than `t`.
`tests/test_g191_002.py` proves this both by future-perturbation (real
module: 0 of N offsets leak, across high/low/close rewritten jointly from
an offset onward) and by a mutant (`importlib` source read, `exec`'d in
memory, shown live different from the real module): shifting the final
write index `30` bars into the future, caught at every offset past the
2-bar warm-up.

WARM-UP. `clv[t]` needs `high[t] != low[t]` to be non-NaN (otherwise the
ratio's denominator is zero and `sdiv` maps it to `NaN`); `d1[t]` needs
BOTH `clv[t]` and `clv[t-length]` to be non-NaN. Structurally, the first
bar has no prior bar to diff against, so `min_length = length + 1` -- **2**
bars of history at the shipped default (`length=1`), enforced by
`verify_series`. A zero-range bar (`high==low`) inside the window still
produces `NaN` at that bar and propagates through `d1` like any other
missing value, exactly as `a101_053`'s own `close==low` case does.

A disclosed structural fact, not a modelling choice: under ordinary OHLC
consistency (`low <= open, close <= high` at every bar), `high == low`
forces `open == close == high == low` too -- a fully flat, zero-range
bar. This is a much rarer degenerate case than `a101_053`'s own
`close == low` zero-denominator ("close prints at its own low", measured
21.17% of BIST daily bars per the `fvg`/FVGDEAD note in `CLAUDE.md`), since
it additionally requires the HIGH to coincide with the low on the same
bar. Measured on a 1,500-bar synthetic continuous-float walk
(`python docs/measure_g191_002.py`): 0 zero-range bars, so the `sdiv`
NaN-branch never fires there; real tick-rounded exchange data can still
hit it, so the mask stays in the formula regardless, matching the
prototype's own unconditional use of `sdiv`.

SCALE-FREE. Let `k > 0` rescale price (`high, low, close -> k*high,
k*low, k*close`). The numerator `2*close-high-low` and the denominator
`high-low` are both linear in `(high, low, close)`, so they each scale to
`k*(2*close-high-low)` and `k*(high-low)` -- `clv` itself therefore scales
to `(k*num)/(k*den) = num/den`, UNCHANGED by a positive rescale (the `k`
cancels exactly, the same algebraic cancellation `a101_053`'s own
close-location ratio relies on). `d1 = clv - clv.shift(length)` is a
difference of two values each individually unchanged by the rescale, so
`d1`, and hence `G191_002 = -d1`, is unchanged too. Measured on a
synthetic frame: PRICE x8/x64 land bit-identical (power-of-two
multiplication is exact in IEEE754, so the scaled computation retraces
the exact same floating-point operations up to an exact exponent shift),
while x10/x3.7 come out within float64 rounding tolerance (the ratio's
own arithmetic rounds differently at a non-power-of-two multiplier, even
though the true mathematical ratio is identical). Measured in the test
file and `docs/measure_g191_002.py`, not merely asserted.
"""
import numpy as np

from pandas_ta.utils import get_offset, verify_series


def g191_002(high, low, close, length=None, offset=None, **kwargs):
    """Indicator: One-Day Change Of Close Location (G191_002)"""
    # Validate Arguments
    length = int(length) if length and length > 0 else 1
    min_length = length + 1
    high = verify_series(high, min_length)
    low = verify_series(low, min_length)
    close = verify_series(close, min_length)
    offset = get_offset(offset)

    if high is None or low is None or close is None:
        return

    if not (high.index.equals(low.index) and high.index.equals(close.index)):
        raise ValueError(
            "g191_002: `high`, `low` and `close` are indexed differently. A "
            "close-location ratio read off misaligned series is a silent "
            "nonsense number."
        )

    # Calculate Result
    denom = high - low
    clv = ((2.0 * close - high - low) / denom).replace([np.inf, -np.inf], np.nan)
    d1 = clv.diff(length)
    result = -d1

    # Offset
    if offset != 0:
        result = result.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        result.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        result.fillna(method=kwargs["fill_method"], inplace=True)

    # Name & Category
    result.name = f"G191_002_{length}"
    result.category = "momentum"

    return result


g191_002.__doc__ = \
"""One-Day Change Of Close Location (G191_002)

Guotai Junan's (2017, "GTJA191") alpha `#2`, per issue #63. The
close-location value `((close-low)-(high-close))/(high-low)` reads where
today's close sits within today's own high-low range; the column is the
negated `length`-bar change of that value -- positive when the close has
moved toward its own low over the window, negative when it has moved
toward its own high. Full Gate A derivation, causality and scale-free
arguments are in the module source above; see docs/G191002Measured.md for
the measured numbers.

Calculation:
    Default Inputs:
        length=1
    clv      = ((close-low)-(high-close)) / (high-low)   # NaN where high==low
    G191_002 = -(clv - clv.shift(length))  # = clv.shift(length) - clv

Args:
    high (pd.Series): Series of 'high's
    low (pd.Series): Series of 'low's
    close (pd.Series): Series of 'close's
    length (int): Lookback for the close-location delta. Default: 1
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.Series: G191_002_{length}, a scale-free (dimensionless) column: the
        negated `length`-bar change of the close-location value. NaN for
        the first `length` bars, and additionally wherever `high == low`
        on the current or the `length`-bars-back bar (the ratio's
        denominator is zero there).
"""
