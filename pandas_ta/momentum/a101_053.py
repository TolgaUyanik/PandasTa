# -*- coding: utf-8 -*-
"""9-day change of the close-location ratio -- Kakushadze's (2016, Wilmott,
"101 Formulaic Alphas") Alpha101 `#53`, per issue #48. Source cited by the
issue: Kakushadze (2016); vnpy's `vnpy/alpha101` module (MIT) is named by the
issue as the copy it read, but is NOT itself consulted in this session
(`docs/pine/` and web access are unavailable in this worktree) -- the formula
used here is the issue's own restatement of Kakushadze's published text, read
as the source per the issue's own instruction ("Gate A starts from the source
formula, not the prototype").

Issue #48's stated formula:

    -delta(((close-low)-(high-close))/(close-low), 9)

OPERATORS, read directly off the formula string, no ambiguity to resolve:

* `delta(x, d)` = `x - x.shift(d)`, the plain `d`-bar difference. The only
  operator in this formula -- unlike `a101_021`/`a101_043`, there is no
  `mean`, `std`, `adv` or `ts_rank` term, so no glossary ambiguity to
  disclose.

One modelling choice, not an ambiguity in the formula itself: `close - low`
sits in the denominator and is zero whenever the bar's close prints at its
own low (a real, non-rare event: issue #48's own sibling `fvg` note in
CLAUDE.md measures 21.17% of BIST daily bars closing exactly at an extreme).
Kakushadze's formula is silent on that case; following this fork's own
existing convention for a formula-ratio division (`a101_021`'s
`volume/adv`, `a101_043`'s `volume/adv`), `inf`/`-inf` from the zero
denominator is replaced with `NaN` rather than left as a signed infinity.

CALCULATION, in the order computed below:
    clr      = ((close - low) - (high - close)) / (close - low)
             = (2*close - low - high) / (close - low)     # algebraic simplification, same value
    d9       = DELTA(clr, length)                           # length=9
    A101_053 = -d9                                          # = clr.shift(length) - clr

CAUSALITY. `clr` is pointwise on the current bar's `close`/`low`/`high`,
reading only `t`. `d9 = clr - clr.shift(length)` reads only `t` and
`t-length`. The final negation is pointwise. Nothing is shifted forward
anywhere in the chain. `tests/test_a101_053.py` proves this both by
future-perturbation and by a mutant (`importlib` source read, `exec`'d in
memory) that shifts the final write index into the future: shown live
(differs from the real module), then caught at every offset past the
warm-up.

SCALE-FREE. `clr`'s numerator `(2*close - low - high)` and denominator
`(close - low)` are both linear in `(close, high, low)`, so a positive
rescale of the three price series by a common `k` scales numerator and
denominator identically -- `clr` itself is unchanged, not merely linearly
rescaled, by a positive price rescale (the ratio cancels `k` algebraically).
`d9 = clr - clr.shift(length)` is then a difference of two values each
individually unchanged by the rescale, so `d9`, and hence `A101_053 = -d9`,
is unchanged too. Measured in the test file, not merely asserted: x8/x64 is
bit-identical as a mathematical certainty (power-of-two multiplication is
exact in IEEE754). x10/x3.7 is NOT bit-identical -- measured max|diff| on the
test's synthetic walk is 1.19e-7 at x10 and 6.98e-8 at x3.7
(`docs/measure_a101_053.py`), bigger than the 1e-9 other ports' ratios hold
to. This is catastrophic cancellation, not a scale leak in the algebra: the
denominator `close - low` is itself a difference that comes arbitrarily
close to zero (measured min |close-low| on the same walk: 7.4e-5), so a
rescale-then-subtract-then-divide loses more bits there than a ratio whose
denominator is a clean price level (`a101_023`'s plain `close`). The test
tolerance is loosened to 1e-6 to match what is actually measured, not
invented.
"""
import numpy as np

from pandas_ta.utils import get_offset, verify_series


def a101_053(high, low, close, length=None, offset=None, **kwargs):
    """Indicator: 9-Day Change of the Close-Location Ratio (A101_053)"""
    # Validate Arguments
    length = int(length) if length and length > 0 else 9
    min_length = length + 1
    high = verify_series(high, min_length)
    low = verify_series(low, min_length)
    close = verify_series(close, min_length)
    offset = get_offset(offset)

    if high is None or low is None or close is None:
        return

    if not (high.index.equals(low.index) and high.index.equals(close.index)):
        raise ValueError(
            "a101_053: `high`, `low` and `close` are indexed differently. A "
            "close-location ratio read off misaligned series is a silent "
            "nonsense number."
        )

    # Calculate Result
    denom = close - low
    clr = ((2.0 * close - low - high) / denom).replace([np.inf, -np.inf], np.nan)
    d9 = clr.diff(length)
    result = -d9

    # Offset
    if offset != 0:
        result = result.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        result.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        result.fillna(method=kwargs["fill_method"], inplace=True)

    # Name & Category
    result.name = f"A101_053_{length}"
    result.category = "momentum"

    return result


a101_053.__doc__ = \
"""9-Day Change of the Close-Location Ratio (A101_053)

Kakushadze's (2016, Wilmott, "101 Formulaic Alphas") Alpha101 `#53`, per
issue #48. The close-location ratio `((close-low)-(high-close))/(close-low)`
reads where today's close sits within today's own close-to-low range,
relative to the close-to-high gap; the column is the negated 9-bar change of
that ratio -- positive when the close has moved toward its own low over the
window, negative when it has moved toward its own high. Full Gate A
derivation, causality and scale-free arguments are in the module source
above; see docs/A101053Measured.md for the measured numbers.

Calculation:
    Default Inputs:
        length=9
    clr      = ((close-low)-(high-close)) / (close-low)   # NaN where close==low
    A101_053 = -(clr - clr.shift(length))  # = clr.shift(length) - clr

Args:
    high (pd.Series): Series of 'high's
    low (pd.Series): Series of 'low's
    close (pd.Series): Series of 'close's
    length (int): Lookback for the ratio delta. Default: 9
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.Series: A101_053_{length}, a scale-free (dimensionless) column: the
        negated `length`-bar change of the close-location ratio. NaN for the
        first `length` bars, and additionally wherever `close == low` on the
        current or the `length`-bars-back bar (the ratio's denominator is
        zero there).
"""
