# -*- coding: utf-8 -*-
"""Mean absolute deviation from the 6-day mean -- Guotai Junan's (2017,
"GTJA191", internal quant report, read via the HKUDS/Vibe-Trading copy,
MIT) alpha `#189`, per issue #61. Source cited by the issue:

    #189: MEAN(|C-MEAN(C,6)|,6)

**What this session could NOT do, disclosed up front:** `docs/pine/` and
web access are both unavailable in this worktree, so the issue's own named
copy -- HKUDS/Vibe-Trading (MIT) -- was never read. The formula below is
derived from the issue's own stated text (itself a quote of the GTJA191
report), per the issue's own instruction ("Gate A starts from the source
formula, not the prototype").

GATE A -- DERIVATION. The formula reads: compute a 6-bar rolling mean of
`close`, take the absolute deviation of `close` from that mean at every
bar, then average those deviations over the trailing 6 bars -- "how far
has `close` typically sat from its own recent average, lately". This
matches the issue's own prototype (`docs/issues/screen/ind_screen.py:566-567`),
candidate `g191_189`, including the issue's own scale-free conversion
("/close"):

    @cand("g191_189", "mean absolute deviation from the 6-day mean", G,
          "#189: MEAN(|C-MEAN(C,6)|,6)", "/close")
    def _(o, h, l, c, v): return mean((c - mean(c, 6)).abs(), 6) / c

No disclosed interpretation choice was needed for the formula itself -- the
issue's own string and the prototype agree exactly, including both window
lengths and the scale-free conversion.

OPERATORS, each read directly off the prototype's own (unambiguous) module
source, the same source every other `g191_*` port in this fork relies on:

* `MEAN(X, n)` = `X.rolling(n).mean()` (`ind_screen.py:47`).
* `|X|` = `X.abs()`, elementwise absolute value.
* `C` = close. No other OHLCV field is read.

CALCULATION, in the order computed below (`mean_length=6, mad_length=6`):
    inner_mean = MEAN(C, mean_length)
    deviation  = |C - inner_mean|
    mad        = MEAN(deviation, mad_length)
    G191_189   = mad / C

This is NOT the same statistic as the already-shipped `mad` indicator
(`pandas_ta/statistics/mad.py`), despite the shared name "mean absolute
deviation": `mad(close, length)` computes ONE window mean per trailing
window and averages deviations from that SINGLE mean. `G191_189` instead
builds a full rolling-mean SERIES first (`inner_mean`, re-centered at
every bar), takes the per-bar deviation from THAT bar's own local mean,
and only then averages 6 of those per-bar deviations -- each deviation in
the final average is measured against a DIFFERENT local mean, not a
single shared one. The two formulas coincide only in the FULLY degenerate
case `mean_length=mad_length=1`, where both collapse to an identically-zero
column (`close[t] - close[t] = 0`, the only window a length-1 rolling mean
can form). At `mad_length=1` alone with `mean_length > 1` they still
disagree: `mad.py` averages all `mean_length` in-window deviations from
the window's own single mean, while `g191_189` reports only the LAST
bar's deviation from its own (different) local mean. Measured, not
asserted: `python docs/measure_g191_189.py` runs both at `mean_length=3,
mad_length=1` on `close=[1,2,3,4,5]` and prints the disagreement (`mad.py`
0.666667 vs `g191_189`'s pre-division deviation 1.0 at every bar checked).

CAUSALITY. `inner_mean[t]` is a trailing `mean_length`-bar mean, reading
only `C[t-mean_length+1..t]`. `deviation[t] = |C[t] - inner_mean[t]|`
reads only bar `t` and `inner_mean[t]`, itself already backward-looking.
`mad[t]` is a trailing `mad_length`-bar mean of `deviation`, reading only
`deviation[t-mad_length+1..t]` -- every index `<= t`. The final division
by `C[t]` reads only bar `t`. Nothing in the chain reads a bar newer than
`t`. `tests/test_g191_189.py` proves this both by future-perturbation
(real module: 0 of N offsets leak) and by a mutant (`importlib` source
read, `exec`'d in memory, shown live different from the real module):
shifting the final rolling-mean write index `mad_length` bars into the
future is caught at every offset past the warm-up.

WARM-UP. `inner_mean` is valid from `mean_length` bars of history.
`deviation` is valid wherever `inner_mean` is valid (elementwise, no
further lookback). `mad` needs `mad_length` CONSECUTIVE bars where
`deviation` is already valid (pandas' `.rolling().mean()` defaults
`min_periods` to the full window, so a window touching even one `NaN` is
itself `NaN`), valid from `mean_length + mad_length - 1` bars -- **11** at
the shipped defaults, enforced by `verify_series`.

SCALE-FREE. Let `k > 0` rescale price (`close -> k*close`). `inner_mean`
is linear (positively homogeneous of degree 1) in `close`, so it scales to
`k*inner_mean`. `deviation = |close - inner_mean|` then scales to
`k*deviation` (the absolute value of a quantity scaled by a positive `k`
scales by that same `k`). `mad`, a plain linear average of `deviation`,
scales to `k*mad`. The final division `mad / close` therefore scales to
`(k*mad) / (k*close) = mad / close` -- the `k` cancels EXACTLY. The whole
column is scale-free BY CONSTRUCTION for a positive rescale of price.
Measured on a synthetic frame: PRICE x8/x64 land bit-identical (power-of-two
multiplication is exact in IEEE754, so the scaled computation retraces the
exact same floating-point operations up to an exact exponent shift), while
x10/x3.7 come out within float64 rounding tolerance (the rolling-mean and
division arithmetic itself rounds differently at a non-power-of-two
multiplier, even though the true mathematical ratio is identical).
Measured in the test file and `docs/measure_g191_189.py`, not merely
asserted.
"""
from pandas_ta.utils import get_offset, verify_series


def g191_189(close, mean_length=None, mad_length=None, offset=None, **kwargs):
    """Indicator: Mean Absolute Deviation From The 6-Day Mean (G191_189)"""
    # Validate Arguments
    mean_length = int(mean_length) if mean_length and mean_length > 0 else 6
    mad_length = int(mad_length) if mad_length and mad_length > 0 else 6

    min_length = mean_length + mad_length - 1
    close = verify_series(close, min_length)
    offset = get_offset(offset)

    if close is None:
        return

    # Calculate Result
    inner_mean = close.rolling(mean_length, min_periods=mean_length).mean()
    deviation = (close - inner_mean).abs()
    mad = deviation.rolling(mad_length, min_periods=mad_length).mean()
    result = mad / close

    # Offset
    if offset != 0:
        result = result.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        result.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        result.fillna(method=kwargs["fill_method"], inplace=True)

    # Name & Category
    result.name = f"G191_189_{mean_length}_{mad_length}"
    result.category = "statistics"

    return result


g191_189.__doc__ = \
"""Mean Absolute Deviation From The 6-Day Mean (G191_189)

Guotai Junan's (2017, "GTJA191") alpha `#189`, per issue #61. Builds a
rolling mean of `close`, takes the per-bar absolute deviation of `close`
from THAT bar's own local mean, averages 6 of those per-bar deviations,
then divides by `close` to make the result scale-free. Full Gate A
derivation, causality and scale-free arguments are in the module source
above; see docs/G191189Measured.md for the measured numbers.

NOT the same statistic as the already-shipped `mad` indicator, which
averages deviations from a SINGLE shared window mean rather than from a
re-centered per-bar mean -- see the module docstring.

Calculation:
    Default Inputs:
        mean_length=6, mad_length=6
    inner_mean = MEAN(close, mean_length)
    deviation  = |close - inner_mean|
    mad        = MEAN(deviation, mad_length)
    G191_189   = mad / close

Args:
    close (pd.Series): Series of 'close's
    mean_length (int): Rolling window for the inner (re-centered) mean. Default: 6
    mad_length (int): Rolling window averaging the per-bar deviations. Default: 6
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.Series: G191_189_{mean_length}_{mad_length}, a scale-free
        (dimensionless) column: a mean absolute deviation divided by close,
        non-negative. NaN for the first `mean_length + mad_length - 2` bars
        (10 at the shipped defaults).
"""
