# -*- coding: utf-8 -*-
"""12-Day Sum Of Down Moves (G191_129) -- Guotai Junan's (2017, "GTJA191",
internal quant report, read via the HKUDS/Vibe-Trading copy, MIT) alpha
`#129`, per issue #75. Source cited by the issue:

    #129: SUM(C-C1<0 ? |C-C1| : 0, 12)

**What this session could NOT do, disclosed up front:** `docs/pine/` and
web access are both unavailable in this worktree, so the issue's own named
copy -- HKUDS/Vibe-Trading (MIT) -- was never read. The formula below is
derived from the issue's own stated text (itself a quote of the GTJA191
report), per the issue's own instruction ("Gate A starts from the source
formula, not the prototype"), then cross-checked against the issue's own
prototype (`docs/issues/screen/ind_screen.py:477-478`):

    @cand("g191_129", "12-day sum of down moves", G,
          "#129: SUM(C-C1<0 ? |C-C1| : 0, 12)", "/close")
    def _(o, h, l, c, v): return tsum((-delta(c, 1)).clip(lower=0), 12) / c

No disclosed interpretation choice was needed -- the issue's own string and
the prototype agree exactly, including the window length and the issue's
own scale-free conversion ("/close").

OPERATORS, each read directly off the prototype's own (unambiguous) module
source, the same source every other `g191_*` port in this fork relies on:

* `C1` denotes `C` delayed one bar, `DELAY(C, 1) = C.shift(1)`
  (`ind_screen.py:45`), a BACKWARD shift (bar `t` reads bar `t-1`), never a
  look-ahead.
* `C-C1<0 ? |C-C1| : 0` is a per-bar ternary: on a down day (`close[t] <
  close[t-1]`) keep the MAGNITUDE of the one-bar price change, force
  exactly `0.0` otherwise (an up OR flat day). `C-C1<0` means `delta<0`, so
  `|C-C1| = |delta| = -delta` on that branch (delta itself is negative
  there); `max(-delta, 0)` is the identical function at every bar
  INCLUDING the `C==C1` boundary (`delta==0` already yields `0` under
  EITHER formulation: the ternary's condition is false there and
  `-delta==0` too), so `Series.clip(lower=0)` applied to `-delta` --
  the prototype's own spelling, `(-delta(c, 1)).clip(lower=0)` --
  reproduces the ternary exactly, with no edge-case divergence. Measured
  in two parts, since a continuous-float random walk essentially never
  lands on `delta == 0` exactly (the 1,500-bar walk below has zero such
  bars -- disclosed, not glossed over): `python docs/measure_g191_129.py`
  confirms `clip(lower=0)` of `-delta` and an explicit
  `np.where(delta < 0, -delta, 0.0)` ternary agree bit-for-bit on that
  1,500-bar synthetic walk (the general case), and
  `tests/test_g191_129.py::test_clip_matches_an_explicit_ternary_at_the_zero_boundary`
  pins the `delta == 0` boundary itself on a dedicated 5-bar frame built to
  hold one bar exactly flat.
* `SUM(X, n)` = `X.rolling(n).sum()` (`ind_screen.py:49`), a trailing
  `n`-bar sum.
* `C` = close. No other OHLCV field is read.

CALCULATION, in the order computed below (`length=12`):
    C1       = DELAY(C, 1)
    down     = MAX(-(C - C1), 0)     # NaN at bar 0, where C1 is undefined
    G191_129 = SUM(down, length) / C

CAUSALITY. `C1[t]` reads only `C[t-1]`. `down[t]` is a pointwise function of
`C[t]` and `C1[t]` -- bars no newer than `t`. `SUM(down, length)[t]` is a
trailing `length`-bar sum over the window `[t-length+1, t]`, every index
`<= t`. The final division by `C[t]` reads only bar `t`. Nothing in the
chain reads a bar newer than `t`. `tests/test_g191_129.py` proves this both
by future-perturbation (real module: 0 of N offsets leak, over a synthetic
walk rewritten from an offset onward) and by two mutants (`importlib`
source read, `exec`'d in memory, each shown live different from the real
module): shifting the final rolling-sum write index `length` bars into the
future, and computing the rolling sum with `rolling(length,
center=True)` instead of the causal trailing window -- the same `bos`
look-ahead bug class CLAUDE.md documents.

WARM-UP. `C1` is undefined at bar 0 (no prior bar), so `down` is undefined
there too (`close.diff()`'s own `NaN` at bar 0 propagates through the
negation and `.clip(lower=0)`, which preserves `NaN`). `SUM(down, length)`,
a trailing `length`-bar sum with `min_periods=length`, needs `length`
CONSECUTIVE valid `down` values ending at `t`, i.e. `t - length + 1 >= 1`,
i.e. `t >= length` -- `min_length = length + 1` bars of history (**13** at
the shipped default), enforced by `verify_series`.

SCALE-FREE. Let `k > 0` rescale price (`close -> k*close`). `C1 =
DELAY(C,1)` is linear (a shift carries no arithmetic), so it scales to
`k*C1`. `delta = C - C1` scales to `k*delta`, so `-delta` scales to
`-k*delta = k*(-delta)`. `max(k*(-delta), 0) = k*max(-delta, 0)` for any
`k > 0` (scaling a nonnegative-clip by a positive constant commutes with
the clip), so `down` scales to `k*down` at every bar. `SUM(down, length)`,
a plain linear sum, scales to `k*SUM(down, length)`. The final division by
`C -> k*C` therefore gives `(k*SUM(down,length))/(k*C) =
SUM(down,length)/C` -- the `k` cancels EXACTLY, for ANY positive `k`.
Measured on a synthetic walk: PRICE x8/x64 land bit-identical (power-of-two
multiplication is exact in IEEE754, so the cancellation is also exact in
floating point), while x10/x3.7 come out within float64 rounding tolerance
of the unscaled column (the subtraction, clip and rolling-sum arithmetic
itself rounds differently at a non-power-of-two multiplier, even though
the true mathematical ratio is identical). Measured in the test file and
`docs/measure_g191_129.py`, not merely asserted.
"""
from pandas_ta.utils import get_offset, verify_series


def g191_129(close, length=None, offset=None, **kwargs):
    """Indicator: 12-Day Sum Of Down Moves (G191_129)"""
    # Validate Arguments
    length = int(length) if length and length > 1 else 12
    min_length = length + 1
    close = verify_series(close, min_length)
    offset = get_offset(offset)

    if close is None:
        return

    # Calculate Result
    down = (-close.diff()).clip(lower=0)
    result = down.rolling(length, min_periods=length).sum() / close

    # Offset
    if offset != 0:
        result = result.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        result.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        result.fillna(method=kwargs["fill_method"], inplace=True)

    # Name & Category
    result.name = f"G191_129_{length}"
    result.category = "momentum"

    return result


g191_129.__doc__ = \
"""12-Day Sum Of Down Moves (G191_129)

Guotai Junan's (2017, "GTJA191") alpha `#129`, per issue #75. On a down day
(close below the prior close), the bar contributes the MAGNITUDE of its own
one-bar price change; on an up or flat day, it contributes zero. Summed
over a trailing window and divided by close for a scale-free result: a
running tally of downside price movement relative to price, the
complementary half of a Wilder-RSI-style up/down split (up-move half is
`g191_167`'s sibling structure, the identical operator mirrored in sign).
Full Gate A derivation, causality and scale-free arguments are in the
module source above; see docs/G191129Measured.md for the measured numbers.

Calculation:
    Default Inputs:
        length=12
    C1       = DELAY(close, 1)
    down     = MAX(-(close - C1), 0)
    G191_129 = SUM(down, length) / close

Args:
    close (pd.Series): Series of 'close's
    length (int): Rolling window for the sum. Default: 12
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.Series: G191_129_{length}, a scale-free (dimensionless) column,
        non-negative by construction (a sum of nonnegative price-change
        magnitudes divided by a positive price). NaN for the first
        `length` bars (`min_length - 1`, 12 at the shipped default).
"""
