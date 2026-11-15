# -*- coding: utf-8 -*-
"""Autocorrelation-scaled return -- Kakushadze's (2016, Wilmott, "101 Formulaic
Alphas") Alpha#101 `#48`, without its cross-sectional `IndNeutralize` wrapper
(this fork has no sector/industry classification to neutralise against), per
issue #41. Source cited by the issue: Kakushadze (2016); vnpy's
`vnpy/alpha101` module (MIT) carries the same published formula and is read
here only to confirm the issue's own transcription, not as the definition's
origin -- the formula itself is Kakushadze's published text, and is also the
well-known public "WorldQuant 101 Alphas" #48:

    indneutralize(
        (correlation(delta(close, 1), delta(delay(close, 1), 1), 250) * delta(close, 1)) / close,
        IndClass.subindustry
    ) / sum((delta(close, 1) / delay(close, 1)) ^ 2, 250)

With `indneutralize(x, ...)` dropped to plain `x` (no classification to
neutralise against, per the issue):

    (correlation(delta(close, 1), delta(delay(close, 1), 1), 250) * delta(close, 1)) / close
        / sum((delta(close, 1) / delay(close, 1)) ^ 2, 250)

CALCULATION. `delta(close, 1) = close - close.shift(1)` (`d` below).
`delay(close, 1) = close.shift(1)`, so `delta(delay(close, 1), 1) =
close.shift(1) - close.shift(2) = d.shift(1)`: delta-of-delay-of-close is
exactly delta-of-close shifted one bar later, i.e. the correlation term is
the rolling 250-bar lag-1 autocorrelation of the daily close-change series.
`delta(close, 1) / delay(close, 1)` is the plain simple return `r[t] =
close[t] / close[t-1] - 1`. The formula's own parentheses group
`correlation(...) * delta(close, 1)` before the `/ close`, and group the
whole left side before the trailing `/ sum(...)`:

    ((corr(d, d.shift(1), 250) * d) / close) / sum(r^2, 250)

-- exactly the order computed below. See `docs/measure_a101_048.py` for an
independent per-window loop built from this reading, matched against the
module to 1e-9.

CAUSALITY. `rolling(length).corr` and `rolling(length).sum` at bar `t` read
only `d[t-length+1 .. t]` (and `d.shift(1)`, `r`, which are themselves
backward-looking); nothing is shifted forward. `tests/test_a101_048.py`
proves this both by future-perturbation and by a mutant that reads one bar
ahead before rolling.

SCALE-FREE. Every term is a ratio or correlation of price differences and
prices (`d / close`, `r = d / close.shift(1)`, a correlation coefficient,
which is scale-invariant by definition): the whole expression is a ratio of
like-scaled quantities, so it is scale-free by construction, not by an added
normalisation step. Measured in the test file, not merely asserted.
"""
import numpy as np
from pandas_ta.utils import get_offset, verify_series


def a101_048(close, length=None, offset=None, **kwargs):
    """Indicator: Autocorrelation-Scaled Return (A101_048)"""
    # Validate Arguments
    length = int(length) if length and length > 0 else 250
    close = verify_series(close, length + 2)
    offset = get_offset(offset)

    if close is None:
        return

    # d = delta(close, 1); d.shift(1) = delta(delay(close, 1), 1) (see module
    # docstring). r = delta(close, 1) / delay(close, 1), the plain simple return.
    d = close.diff(1)
    r = close.pct_change(fill_method=None)
    autocorr = d.rolling(length).corr(d.shift(1))
    denom = (r ** 2).rolling(length).sum()
    result = (autocorr * d / close) / denom
    result = result.replace([np.inf, -np.inf], np.nan)

    # Offset
    if offset != 0:
        result = result.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        result.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        result.fillna(method=kwargs["fill_method"], inplace=True)

    # Name & Category
    result.name = f"A101_048_{length}"
    result.category = "momentum"

    return result


a101_048.__doc__ = \
"""Autocorrelation-Scaled Return (A101_048)

Kakushadze's (2016, Wilmott, "101 Formulaic Alphas") Alpha#101 `#48`, without
its cross-sectional `IndNeutralize` wrapper (this fork has no sector/industry
classification), per issue #41. The 1-day price change is scaled by its own
rolling 250-bar lag-1 autocorrelation and by the inverse of the rolling sum
of squared daily returns -- a return that is damped when the market's recent
day-to-day moves have been noisy/uncorrelated or volatile, and amplified
when they have been persistent and calm. Full Gate A derivation, causality
and scale-free arguments are in the module source above; see
docs/A101048Measured.md for the measured numbers.

Calculation:
    Default Inputs:
        length=250
    d        = DELTA(close, 1)              # close - close[1]
    r        = close / close[1] - 1         # delta(close,1)/delay(close,1)
    AC       = CORR(d, DELAY(d, 1), length) # == CORR(d, d[1], length)
    A101_048 = AC * d / close / SUM(r^2, length)

Args:
    close (pd.Series): Series of 'close's
    length (int): Rolling window for the autocorrelation and the squared-
        return sum. Default: 250
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.Series: A101_048_{length}, a scale-free (dimensionless) ratio. NaN
        for the first length+1 bars.
"""
