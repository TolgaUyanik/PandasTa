# -*- coding: utf-8 -*-
"""Wick pressure: bear-candle lower wicks minus bull-candle upper wicks (10)
-- Reddit (tier 4, ResearchIntel kb/reddit.db), per issue #170: r/algotrading
rd:algotrading:pneq7k (2021-09-13,
https://www.reddit.com/r/algotrading/comments/pneq7k/). The issue cites the
formula directly, not a script, so there is no source line number -- Gate A
reads the formula from the issue's own statement (its own instruction:
"Gate A starts from the source formula, not the prototype"), not from the
screen prototype (`docs/issues/screen/ind_screen_r6.py`'s
`rd_wick_pressure_10`, which is mathematically the same reading but is not
what Gate A cites).

POSTER'S WORDS (tier 4, untested by the poster): "sum the top wicks on bull
candles on X candlestick M1 to measure 'bear defense power'". Claimed use:
wicks show who is stronger; the poster's own words say they found it mostly
useless -- NOT independently tested here either way. This port ships
existence (the column is causal, scale-free and reachable on real data), not
evidence that it measures anything the poster claims.

GATE A -- the issue's own formula:

    sum lower wick on bear candles - sum upper wick on bull candles

read per-bar as:
    bear          = close < open
    bull          = close > open
    lower_wick    = (MIN(open, close) - low)  IF bear ELSE 0
    upper_wick    = (high - MAX(open, close)) IF bull ELSE 0
    RD_WICK_PRESSURE_10 = (SUM(lower_wick, 10) - SUM(upper_wick, 10))
                          / SUM(high - low, 10)

The "(10)" in the issue's own title fixes the window, so `length` is a
parameter with that default, not a hard constant -- this fork's convention
for a fixed-suffix port (`osap_retskew_21`, `rd_gap_fill_rate_60`). The
denominator is the issue's own prototype's disclosed scale-free choice ("over
10 bars, divided by the sum of ranges") -- the poster's words give no
normalisation at all (a raw sum of wick lengths is a price-level quantity,
not an ML feature per this repo's contract), so dividing by the same window's
summed range is the prototype's own disclosed, not poster-stated, choice,
carried through unchanged here as it is what turns the column into a
feature at all.

CAUSALITY. Bar T's output reads only open/high/low/close over the window
`[T-9, T]` (`.rolling(10)`), nothing shifted toward the future.
`tests/test_rd_wick_pressure_10.py` proves this with a future-splice probe
(bars before a perturbation point J stay bit-identical) and a mutant that
appends `.shift(-1)` to the final ratio (reading one bar ahead).

SCALE-FREE. `lower_wick`, `upper_wick` and `high - low` are each a
difference of two like-for-like price terms on the SAME bar, so multiplying
`open`/`high`/`low`/`close` by one positive constant `k` scales every one of
them by exactly `k` -- the numerator and denominator of the final ratio both
scale by `k`, leaving the ratio unchanged. Under an exact power-of-two
rescale (x8, x64) this is bit-identical, since `(a*k)/(b*k)` on
exactly-representable scaled operands is a correctly-rounded division equal
in every bit to `a/b`. Under a non-power-of-two rescale (x10, x3.7) each
scaled operand carries its own last-bit rounding, so the ratio can move by a
tiny relative amount -- measured, not merely argued, in
`tests/test_rd_wick_pressure_10.py` / `docs/measure_rd_wick_pressure_10.py`.
"""
import numpy as np

from pandas_ta.utils import get_offset, verify_series


def rd_wick_pressure_10(open_, high, low, close, length=None, offset=None, **kwargs):
    """Indicator: Wick Pressure (RD_WICK_PRESSURE)"""
    # Validate Arguments
    length = int(length) if length and length > 0 else 10
    open_ = verify_series(open_, length)
    high = verify_series(high, length)
    low = verify_series(low, length)
    close = verify_series(close, length)
    offset = get_offset(offset)

    if open_ is None or high is None or low is None or close is None:
        return

    # Calculate Result
    bear = close < open_
    bull = close > open_
    lower_wick = (np.minimum(open_, close) - low).where(bear, 0.0)
    upper_wick = (high - np.maximum(open_, close)).where(bull, 0.0)
    rng = high - low

    pressure_sum = lower_wick.rolling(length).sum() - upper_wick.rolling(length).sum()
    range_sum = rng.rolling(length).sum()

    out = (pressure_sum / range_sum).replace([np.inf, -np.inf], np.nan)

    # Offset
    if offset != 0:
        out = out.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        out.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        out.fillna(method=kwargs["fill_method"], inplace=True)

    # Name & Category
    out.name = f"RD_WICK_PRESSURE_{length}"
    out.category = "candles"

    return out


rd_wick_pressure_10.__doc__ = \
"""Wick Pressure (RD_WICK_PRESSURE)

Trailing sum of lower wicks on bear (red) candles minus the trailing sum of
upper wicks on bull (green) candles, divided by the trailing sum of ranges --
a scale-free read of "who left more wick behind, buyers or sellers". A
Reddit crowd-talk definition (tier 4, untested by the poster, issue #170):
"sum the top wicks on bull candles ... to measure 'bear defense power'" --
the poster's own words say they found it mostly useless. NOT independently
tested here either way. See the module source above for the full source
citation, Gate A derivation and the causality/scale-free argument;
docs/RdWickPressure10Measured.md has the measured numbers.

Sources:
    Reddit, tier 4 (ResearchIntel kb/reddit.db): rd:algotrading:pneq7k
    (2021-09-13) https://www.reddit.com/r/algotrading/comments/pneq7k/

Calculation:
    Default Inputs:
        length=10
    bear       = close < open
    bull       = close > open
    lower_wick = (MIN(open, close) - low)  IF bear ELSE 0
    upper_wick = (high - MAX(open, close)) IF bull ELSE 0
    RD_WICK_PRESSURE = (SUM(lower_wick, length) - SUM(upper_wick, length))
                       / SUM(high - low, length)

Args:
    open_ (pd.Series): Series of 'open's
    high (pd.Series): Series of 'high's
    low (pd.Series): Series of 'low's
    close (pd.Series): Series of 'close's
    length (int): The rolling window. Default: 10
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.Series: RD_WICK_PRESSURE_<length>, a scale-free (ratio of like-for-like
        price differences) column. NaN for the first `length - 1` bars (the
        rolling window's warm-up) and wherever the window's summed range is
        exactly 0 (every bar in the window a doji with equal high/low).
"""
