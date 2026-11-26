# -*- coding: utf-8 -*-
"""Outside pivot (3-bar): the prior bar is at once a 3-bar swing high and a
3-bar swing low -- Reddit (tier 4, ResearchIntel kb/reddit.db), per issue
#199: r/options rd:options:1k1hyso (2025-04-17,
https://www.reddit.com/r/options/comments/1k1hyso/). The issue cites the
formula directly, not a script, so there is no source line number -- Gate A
reads the formula from the issue's own statement (its own instruction:
"Gate A starts from the source formula, not the prototype"), not from the
screen prototype (`docs/issues/screen/ind_screen_r9.py`'s
`b3_outside_pivot3`).

POSTER'S WORDS (tier 4, untested by the poster): "when a middle candle's high
is higher than the highs of 2 candles surrounding it, and also when the middle
candle's low is lower than the lows of 2 candles surrounding it". Claimed use:
exclude double-sided swings as unreliable swing signals -- NOT independently
tested here. This port ships existence (the pattern fires, is causal and is
scale-free), not evidence that it predicts anything.

GATE A -- the issue's formula, bar T the current bar and bar T-1 the middle
("prior") bar:
    B3_OUTSIDE_PIVOT3 = 1 IF high[T-1] > max(high[T-2], high[T])
                          AND low[T-1] < min(low[T-2], low[T])
                        ELSE 0
Strict on both sides, so a tie with either neighbour does not fire. Open and
close play no part in the formula and are not read. The flag is written on
bar T, the first bar at which the right-hand neighbour exists -- not
back-dated onto the middle bar T-1, which would read one bar of future.

CAUSALITY. Bar T's output reads only high/low at T, T-1 and T-2 (`.shift(1)`,
`.shift(2)`), nothing shifted toward the future. `tests/test_b3_outside_pivot3.py`
proves this with a future-perturbation sweep (frames identical up to J; bars
before J stay bit-identical) and a mutant that back-dates the final write by
one bar (`.shift(-1)`, i.e. the flag placed on the middle bar).

SCALE-FREE. Every comparison reads only like-for-like price terms (highs
against highs, lows against lows), so multiplying `high`/`low` by one positive
constant leaves every truth value unchanged. `tests/test_b3_outside_pivot3.py`
checks k = 8, 64, 10, 3.7, all bit-identical.
"""
from pandas_ta.utils import get_offset, verify_series


def b3_outside_pivot3(high, low, offset=None, **kwargs):
    """Candle Type: 3-bar Outside Pivot"""
    # Validate Arguments
    high = verify_series(high, 3)
    low = verify_series(low, 3)
    offset = get_offset(offset)

    if high is None or low is None:
        return

    # Calculate Result
    mid_high, mid_low = high.shift(1), low.shift(1)
    left_high, left_low = high.shift(2), low.shift(2)
    swing_high = (mid_high > left_high) & (mid_high > high)
    swing_low = (mid_low < left_low) & (mid_low < low)
    pivot = (swing_high & swing_low).astype(float).where(left_high.notna())

    # Offset
    if offset != 0:
        pivot = pivot.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        pivot.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        pivot.fillna(method=kwargs["fill_method"], inplace=True)

    # Name & Category
    pivot.name = "B3_OUTSIDE_PIVOT3"
    pivot.category = "candles"

    return pivot


b3_outside_pivot3.__doc__ = \
"""Candle Type: 3-bar Outside Pivot

Fires on bar T when the prior bar (T-1) is simultaneously a strict 3-bar swing
high (its high above the highs of T-2 and T) and a strict 3-bar swing low (its
low below the lows of T-2 and T). Equivalently, an outside bar at T-1
(`rd_outside_bar`) followed by an inside bar at T
(`cdl_inside(..., asbool=True)`). From a
Reddit comment (tier 4, untested by the poster), whose claimed use is to
exclude such double-sided swings as unreliable swing signals. See the module
source above for the full source citation, Gate A derivation and the
causality/scale-free argument; docs/B3OutsidePivot3Measured.md has the
measured numbers.

Sources:
    Reddit, tier 4 (ResearchIntel kb/reddit.db): rd:options:1k1hyso
    (2025-04-17) https://www.reddit.com/r/options/comments/1k1hyso/

Calculation:
    Default Inputs:
        (none -- fixed 3-bar comparison)
    B3_OUTSIDE_PIVOT3 = 1 IF high[1 back] > max(high[2 back], high)
                          AND low[1 back] < min(low[2 back], low)
                        ELSE 0

Args:
    high (pd.Series): Series of 'high's
    low (pd.Series): Series of 'low's
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.Series: B3_OUTSIDE_PIVOT3, a scale-free (comparison-only) column in
        {0.0, 1.0}. NaN for the first two bars (no left neighbour yet).
"""
