# -*- coding: utf-8 -*-
"""Outside bar: range engulfs the prior bar's range -- Reddit (tier 4,
ResearchIntel kb/reddit.db), per issue #167: r/Trading rd:Trading:1og1s0z
(2025-10-25, https://www.reddit.com/r/Trading/comments/1og1s0z/) and
r/Daytrading rd:Daytrading:1gxmcnv (2024-11-23,
https://www.reddit.com/r/Daytrading/comments/1gxmcnv/). The issue cites the
formula directly, not a script, so there is no source line number -- Gate A
reads the formula from the issue's own statement (its own instruction:
"Gate A starts from the source formula, not the prototype"), not from the
screen prototype (`docs/issues/screen/ind_screen_r6.py`'s `rd_outside_bar`,
which is mathematically the same reading but is not what Gate A cites).

POSTER'S WORDS (tier 4, untested by the poster): "Look at where it sits
relative to the prior candle." Claimed use: inside bar = compression, outside
bar = expansion; relative size shows volatility expanding/contracting -- NOT
independently tested here. This port ships existence (the pattern fires, is
causal and is scale-free), not evidence that it predicts anything.

GATE A -- the issue's formula, bar T the current bar and bar T-1 the prior
bar:
    RD_OUTSIDE_BAR = 1 IF high[T] > high[T-1] AND low[T] < low[T-1] ELSE 0
This is the mirror of the upstream `cdl_inside` (`high.diff() < 0 & low.diff()
> 0`): outside bar flips both comparisons. The issue states the scale-free
form explicitly as "1 / 0" (not signed by candle colour), so unlike
`rd_horseshoe` there is no colour/sign term to derive -- open and close play
no part in the formula and are not read.

CAUSALITY. Bar T's output reads only high/low at T and T-1 (`.shift(1)`),
nothing shifted toward the future. `tests/test_rd_outside_bar.py` proves this
with a future-perturbation probe (frames identical up to J; bars before J stay
bit-identical) and a mutant that appends a one-bar look-ahead (`.shift(-1)`)
to the final write.

SCALE-FREE. Every comparison (`>`, `<`) reads only like-for-like price terms
on the same side (a high against a prior high, a low against a prior low), so
multiplying `high`/`low` by one positive constant leaves every comparison's
truth value unchanged -- order is preserved under any positive rescale, not
merely a power of two. `tests/test_rd_outside_bar.py` checks this at k = 8,
64, 10, 3.7, all bit-identical (a discrete {0, 1} output has no rounding to
tolerate).
"""
from pandas_ta.utils import get_offset, verify_series


def rd_outside_bar(high, low, offset=None, **kwargs):
    """Candle Type: Outside Bar"""
    # Validate Arguments
    high = verify_series(high, 2)
    low = verify_series(low, 2)
    offset = get_offset(offset)

    if high is None or low is None:
        return

    # Calculate Result
    prior_high = high.shift(1)
    prior_low = low.shift(1)
    outside = (high > prior_high) & (low < prior_low)
    outside_bar = outside.astype(float).where(prior_high.notna())

    # Offset
    if offset != 0:
        outside_bar = outside_bar.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        outside_bar.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        outside_bar.fillna(method=kwargs["fill_method"], inplace=True)

    # Name & Category
    outside_bar.name = "RD_OUTSIDE_BAR"
    outside_bar.category = "candles"

    return outside_bar


rd_outside_bar.__doc__ = \
"""Candle Type: Outside Bar

An Outside Bar is a bar whose range engulfs the prior bar's range on both
sides: its high exceeds the prior high AND its low undercuts the prior low.
The mirror of the upstream `cdl_inside`. From a Reddit post (tier 4, untested
by the poster): "Look at where it sits relative to the prior candle" --
inside bar read as compression, outside bar as expansion. See the module
source above for the full source citation, Gate A derivation and the
causality/scale-free argument; docs/RdOutsideBarMeasured.md has the measured
numbers.

Sources:
    Reddit, tier 4 (ResearchIntel kb/reddit.db): rd:Trading:1og1s0z
    (2025-10-25) https://www.reddit.com/r/Trading/comments/1og1s0z/;
    rd:Daytrading:1gxmcnv (2024-11-23)
    https://www.reddit.com/r/Daytrading/comments/1gxmcnv/

Calculation:
    Default Inputs:
        (none -- fixed 2-bar comparison)
    RD_OUTSIDE_BAR = 1 IF high > high[1 bar back] AND low < low[1 bar back]
                     ELSE 0

Args:
    high (pd.Series): Series of 'high's
    low (pd.Series): Series of 'low's
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.Series: RD_OUTSIDE_BAR, a scale-free (comparison-only) column in
        {0.0, 1.0}. NaN for the first bar (no prior bar to compare against).
"""
