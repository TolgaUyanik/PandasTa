# -*- coding: utf-8 -*-
"""10-day price acceleration -- Kakushadze's (2016, Wilmott, "101 Formulaic
Alphas") Alpha101 `#46`, per issue #49. Source cited by the issue:
Kakushadze (2016); vnpy's `vnpy/alpha101` module (MIT) is named by the issue
as the copy it read, but is NOT itself consulted in this session
(`docs/pine/` and web access are unavailable in this worktree) -- the
formula used here is the issue's own restatement of Kakushadze's published
text, read as the source per the issue's own instruction ("Gate A starts
from the source formula, not the prototype").

Issue #49's stated formula -- the "core" shared, per the issue, by
Kakushadze's Alpha101 `#46`/`#49`/`#51`:

    (delay(close, 20) - delay(close, 10)) / 10 - (delay(close, 10) - close) / 10

Kakushadze's full `#46` wraps this core in a ternary on fixed price-unit
thresholds (0.25, 0, -0.1, -0.05, read off the published text, NOT
transcribed by the issue) before branching to `-1`, `+1` or a plain 1-bar
price change. The issue's own instruction drops that ternary and its
thresholds entirely and ships the bare core in scale-free form (divide by
`close`) -- the same move already made for `a101_023` (issue #47): "scale-
free form (issue's own instruction): divide the price-unit branch by
`close`."

OPERATORS, read directly off the formula string, no ambiguity to resolve:

* `delay(x, d)` = `x.shift(d)`, already established by `a101_021` /
  `a101_023` / `a101_043` / `a101_048` / `a101_053` for `delay`/`delta`.

CALCULATION, in the order computed below:
    far      = DELAY(close, 2 * length)        # length=10, far delay=20
    near     = DELAY(close, length)             # length=10
    raw      = (far - near) / length - (near - close) / length
             = (far - 2*near + close) / length  # algebraic simplification, same value
    A101_046 = raw / close                       # scale-free (issue's instruction)

`raw` is literally the discrete second difference of `close` sampled every
`length` bars, divided by `length` -- an acceleration: the change between
the two `length`-bar price moves `(far -> near)` and `(near -> close)`.

CAUSALITY. `far = close.shift(2*length)` and `near = close.shift(length)`
each read only a single bar at or before `t - length`; `raw` and the final
`/ close` are pointwise combinations of `far`, `near` and the current bar's
`close`. Nothing is shifted forward anywhere in the chain.
`tests/test_a101_046.py` proves this both by future-perturbation and by a
mutant (`importlib` source read, `exec`'d in memory) that shifts the final
write index into the future: shown live (differs from the real module),
then caught at every offset past the warm-up.

SCALE-FREE. `far`, `near` and `close` are all price-unit series, so a
positive rescale of `close` by a common `k` scales `far`, `near` and `close`
identically, and hence scales `raw = (far - 2*near + close) / length` by the
same `k` (linear in three identically-scaled terms). `A101_046 = raw /
close` then scales by `k / k = 1` -- unchanged by a positive price rescale,
exactly `a101_023`'s `-d2 / close` pattern (both numerator and denominator
linear-in-price, cancel exactly). Measured in the test file, not merely
asserted: x8/x64 is bit-identical as a mathematical certainty (power-of-two
multiplication is exact in IEEE754); x10/x3.7 is held to a measured, not
invented, floating-point-rounding tolerance.
"""
from pandas_ta.utils import get_offset, verify_series


def a101_046(close, length=None, offset=None, **kwargs):
    """Indicator: 10-Day Price Acceleration (A101_046)"""
    # Validate Arguments
    length = int(length) if length and length > 0 else 10
    min_length = 2 * length + 1
    close = verify_series(close, min_length)
    offset = get_offset(offset)

    if close is None:
        return

    # Calculate Result
    far = close.shift(2 * length)
    near = close.shift(length)
    raw = (far - near) / length - (near - close) / length
    result = raw / close

    # Offset
    if offset != 0:
        result = result.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        result.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        result.fillna(method=kwargs["fill_method"], inplace=True)

    # Name & Category
    result.name = f"A101_046_{length}"
    result.category = "momentum"

    return result


a101_046.__doc__ = \
"""10-Day Price Acceleration (A101_046)

Kakushadze's (2016, Wilmott, "101 Formulaic Alphas") Alpha101 `#46`, per
issue #49, as the "core" sub-expression it shares with `#49`/`#51`: the
ternary and its fixed price-unit thresholds (0.25, 0, -0.1, -0.05) are
dropped per the issue's own instruction, and the bare core ships in scale-
free form (divided by `close`). The column reads the discrete second
difference of `close` sampled every `length` bars -- the change between the
earlier `length`-bar price move and the more recent one -- divided by
`length` and by `close`: positive when the price has been accelerating
upward, negative when decelerating or accelerating downward. Full Gate A
derivation, causality and scale-free arguments are in the module source
above; see docs/A101046Measured.md for the measured numbers.

Calculation:
    Default Inputs:
        length=10
    far      = DELAY(close, 2*length)           # close.shift(20)
    near     = DELAY(close, length)              # close.shift(10)
    raw      = (far - near) / length - (near - close) / length
    A101_046 = raw / close

Args:
    close (pd.Series): Series of 'close's
    length (int): Lookback step for the two price deltas; the far delay is
        `2 * length`. Default: 10
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.Series: A101_046_{length}, a scale-free (dimensionless) column: the
        `length`-bar second difference of `close`, scaled by `length` and by
        `close`. NaN for the first `2 * length` bars.
"""
