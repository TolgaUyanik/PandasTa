# -*- coding: utf-8 -*-
"""Two-day high change above the 20-day mean high -- Kakushadze's (2016,
Wilmott, "101 Formulaic Alphas") Alpha101 `#23`, per issue #47. Source cited
by the issue: Kakushadze (2016); vnpy's `vnpy/alpha101` module (MIT) is named
by the issue as the copy it read, but is NOT itself consulted in this session
(`docs/pine/` and web access are unavailable in this worktree) -- the formula
used here is the issue's own restatement of Kakushadze's published text, read
as the source per the issue's own instruction ("Gate A starts from the source
formula, not the prototype").

Issue #47's stated formula:

    mean(high, 20) < high ? -delta(high, 2) : 0

scale-free form (issue's own instruction): divide the price-unit branch by
`close`.

OPERATORS, each read directly off the formula string, no ambiguity to
resolve:

* `mean(x, d)` = `x.rolling(d).mean()`, a trailing rolling mean.
* `delta(x, d)` = `x - x.shift(d)`, the plain `d`-bar difference.
* the ternary is a plain `pandas.Series.where`.

CALCULATION, in the order computed below:
    mean_h   = MEAN(high, length)              # length=20
    d2       = DELTA(high, delta_length)        # delta_length=2
    raw      = -d2 / close
    A101_023 = (mean_h < high) ? raw : 0.0, set to NaN while mean_h is NaN

The explicit NaN re-mask for the `mean_h` warm-up matches the issue's own
prototype (`docs/issues/screen/ind_screen.py`'s
`(-delta(h, 2) / c).where(mean(h, 20) < h, 0.0).where(mean(h, 20).notna())`):
without it, the first `length - 1` bars would read as the ternary's literal
`0` branch (a `NaN < x` comparison is `False` in pandas), which is a real
value, not an undefined one, and would understate the warm-up.

CAUSALITY. `mean_h` is a trailing rolling mean reading only `[t-length+1 ..
t]`; `d2 = high - high.shift(delta_length)` reads only `t` and
`t-delta_length`; the comparison, division and `.where` are all pointwise on
those same backward-looking series at `t`. Nothing is shifted forward
anywhere in the chain. `tests/test_a101_023.py` proves this both by
future-perturbation and by a mutant (`importlib` source read, `exec`'d in
memory) that shifts the final write index `length` bars into the future:
shown live (differs from the real module), then caught at every offset past
the warm-up.

SCALE-FREE. `high` and `close` are both price-unit series, so a positive
rescale of price scales both by the identical `k`. `mean_h` scales by `k`
(rolling mean is linear/positively homogeneous), so `mean_h < high` compares
two quantities both scaled by the same `k > 0` -- its truth value is
unchanged. `d2 = high - high.shift(delta_length)` scales by `k` too, so
`raw = -d2 / close` scales by `k / k = 1` -- unchanged. The whole expression
is therefore scale-free under a positive rescale applied to `high` and
`close` together. Measured in the test file, not merely asserted.
"""
from pandas_ta.utils import get_offset, verify_series


def a101_023(high, close, length=None, delta_length=None, offset=None, **kwargs):
    """Indicator: Two-Day High Change Above the 20-Day Mean High (A101_023)"""
    # Validate Arguments
    length = int(length) if length and length > 1 else 20
    delta_length = int(delta_length) if delta_length and delta_length > 0 else 2
    min_length = max(length, delta_length + 1)
    high = verify_series(high, min_length)
    close = verify_series(close, min_length)
    offset = get_offset(offset)

    if high is None or close is None:
        return

    if not high.index.equals(close.index):
        raise ValueError(
            "a101_023: `high` and `close` are indexed differently. A "
            "scale-free ratio read off misaligned series is a silent "
            "nonsense number."
        )

    # Calculate Result
    mean_h = high.rolling(length).mean()
    d2 = high.diff(delta_length)
    raw = -d2 / close

    result = raw.where(mean_h < high, 0.0)
    result = result.where(mean_h.notna())

    # Offset
    if offset != 0:
        result = result.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        result.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        result.fillna(method=kwargs["fill_method"], inplace=True)

    # Name & Category
    result.name = f"A101_023_{length}_{delta_length}"
    result.category = "momentum"

    return result


a101_023.__doc__ = \
"""Two-Day High Change Above the 20-Day Mean High (A101_023)

Kakushadze's (2016, Wilmott, "101 Formulaic Alphas") Alpha101 `#23`, per
issue #47. When today's high is above its own 20-bar trailing average, the
column reads the negated 2-bar change in the high, scaled by `close`;
otherwise it reads 0. Full Gate A derivation, causality and scale-free
arguments are in the module source above; see docs/A101023Measured.md for
the measured numbers.

Calculation:
    Default Inputs:
        length=20, delta_length=2
    mean_h   = MEAN(high, length)
    d2       = DELTA(high, delta_length)       # high - high[2]
    raw      = -d2 / close
    A101_023 = (mean_h < high) ? raw : 0.0      # NaN while mean_h is NaN

Args:
    high (pd.Series): Series of 'high's
    close (pd.Series): Series of 'close's
    length (int): Rolling window for the mean high. Default: 20
    delta_length (int): Lookback for the high delta. Default: 2
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.Series: A101_023_{length}_{delta_length}, a scale-free (dimensionless)
        column: 0.0 when today's high is at or below its own `length`-bar
        mean, else the negated `delta_length`-bar high change divided by
        `close`. NaN for the first `length - 1` bars.
"""
