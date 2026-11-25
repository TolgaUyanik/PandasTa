# -*- coding: utf-8 -*-
"""Horseshoe 4-bar formation, signed -- Reddit r/Daytrading (tier 4,
ResearchIntel kb/reddit.db, rd:Daytrading:1rwgrts, 2026-03-17,
https://www.reddit.com/r/Daytrading/comments/1rwgrts/), per issue #164. A
Reddit post, not a script, so there is no source line number to cite; the
formula below is read directly from the issue's own restatement of the
poster's words, per the issue's own instruction ("Gate A starts from the
source formula, not the prototype") -- not from the screen prototype
(`docs/issues/screen/ind_screen_r6.py`'s `rd_horseshoe`).

POSTER'S WORDS (tier 4, untested by the poster): "Bullish Horseshoe:
Composed of Red-Green-Red-Green candles in order." Claimed use: candlestick
confirmation of reversal zones at range deviations -- NOT independently
tested here; this port ships existence (the formation fires, is causal and
is scale-free), not evidence that it predicts anything.

GATE A -- the issue's formula, read bar-by-bar with bar 4 the current bar
and bar 1 three bars back:
    red   = close < open    (a down/red candle)
    green = close > open    (an up/green candle)
    BULL: bar1 red, bar2 green, bar3 red, bar4 green, AND
          high(bar2) <= max(open(bar1), close(bar4)) AND
          high(bar3) <= max(open(bar1), close(bar4))
    BEAR (issue: "bear mirrored with lows"):
          bar1 green, bar2 red, bar3 green, bar4 red, AND
          low(bar2) >= min(open(bar1), close(bar4)) AND
          low(bar3) >= min(open(bar1), close(bar4))
    RD_HORSESHOE = +1 if BULL, -1 if BEAR, 0 otherwise.
The issue's own reading of the poster's "cannot be above both" as
`<= max(open1, close4)` (mirrored to `>= min(...)` for the bear case) is
kept as given -- the Reddit post itself is not re-fetched in this session
(no web access in this worktree).

CAUSALITY. Bar T's output reads only open/high/low/close at T-3..T:
`.shift(1)`, `.shift(2)`, `.shift(3)` and the unshifted current bar, nothing
shifted toward the future. `tests/test_rd_horseshoe.py` proves this with a
future-perturbation probe (frames identical up to J; bars before J stay
bit-identical) and a mutant that appends a one-bar look-ahead (`.shift(-1)`)
to the final write: the real module leaks 0 bars before J at all 293 swept
J values; the mutant leaks at bar J-1 at 24 of them -- a binary output
cannot be expected to leak at every J (see docs/RdHorseshoeMeasured.md Gate
B).

SCALE-FREE. Every comparison (`<`, `>`, `<=`, `>=`) and every `np.maximum` /
`np.minimum` call reads only like-for-like price terms on the same bars
(an open against a close, a high against the max of an open and a close),
so multiplying `open`/`high`/`low`/`close` by one positive constant leaves
every comparison's truth value unchanged -- order is preserved under any
positive rescale, not merely a power of two. `tests/test_rd_horseshoe.py`
checks this at k = 8, 64, 10, 3.7, all bit-identical (a discrete {-1, 0, 1}
output has no rounding to tolerate).
"""
import numpy as np

from pandas_ta.utils import get_offset, verify_series


def rd_horseshoe(open_, high, low, close, offset=None, **kwargs):
    """Candle Type: Horseshoe (signed, 4-bar)"""
    # Validate Arguments
    open_ = verify_series(open_, 4)
    high = verify_series(high, 4)
    low = verify_series(low, 4)
    close = verify_series(close, 4)
    offset = get_offset(offset)

    if open_ is None or high is None or low is None or close is None:
        return

    # Calculate Result
    red = close < open_
    green = close > open_

    bar1_open = open_.shift(3)
    outer_max = np.maximum(bar1_open, close)
    outer_min = np.minimum(bar1_open, close)

    red3, grn2, red1 = (s.shift(n, fill_value=False)
                        for s, n in ((red, 3), (green, 2), (red, 1)))
    grn3, red2, grn1 = (s.shift(n, fill_value=False)
                        for s, n in ((green, 3), (red, 2), (green, 1)))

    bull = (red3 & grn2 & red1 & green
            & (high.shift(2) <= outer_max) & (high.shift(1) <= outer_max))
    bear = (grn3 & red2 & grn1 & red
            & (low.shift(2) >= outer_min) & (low.shift(1) >= outer_min))

    horseshoe = bull.astype(float) - bear.astype(float)
    horseshoe = horseshoe.where(bar1_open.notna())

    # Offset
    if offset != 0:
        horseshoe = horseshoe.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        horseshoe.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        horseshoe.fillna(method=kwargs["fill_method"], inplace=True)

    # Name & Category
    horseshoe.name = "RD_HORSESHOE"
    horseshoe.category = "candles"

    return horseshoe


rd_horseshoe.__doc__ = \
"""Candle Type: Horseshoe (signed, 4-bar)

A 4-bar signed formation from a Reddit post (r/Daytrading, tier 4, untested
by the poster): bullish is Red-Green-Red-Green with the two middle bars'
highs capped at the max of the first bar's open and the fourth (current)
bar's close; bearish is the mirror (Green-Red-Green-Red, the two middle
bars' lows floored at the min of the first bar's open and the fourth bar's
close). +1 bull / -1 bear / 0 otherwise. See the module source above for
the full source citation, Gate A derivation and the causality/scale-free
argument; docs/RdHorseshoeMeasured.md has the measured numbers.

Sources:
    Reddit, tier 4 (ResearchIntel kb/reddit.db): rd:Daytrading:1rwgrts
    (2026-03-17) https://www.reddit.com/r/Daytrading/comments/1rwgrts/

Calculation:
    Default Inputs:
        (none -- the formation is a fixed 4 bars)
    red   = close < open
    green = close > open
    outer_max = MAX(open[3 bars back], close)
    outer_min = MIN(open[3 bars back], close)

    BULL = red[3] and green[2] and red[1] and green
           and high[2] <= outer_max and high[1] <= outer_max
    BEAR = green[3] and red[2] and green[1] and red
           and low[2] >= outer_min and low[1] >= outer_min

    RD_HORSESHOE = +1 IF BULL ELSE -1 IF BEAR ELSE 0

Args:
    open_ (pd.Series): Series of 'open's
    high (pd.Series): Series of 'high's
    low (pd.Series): Series of 'low's
    close (pd.Series): Series of 'close's
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.Series: RD_HORSESHOE, a scale-free (comparison-only) signed column
        in {-1.0, 0.0, 1.0}. NaN for the first 3 bars (no full 4-bar window).
"""
