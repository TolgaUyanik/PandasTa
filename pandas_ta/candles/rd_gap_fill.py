# -*- coding: utf-8 -*-
"""Same-day gap fill, signed -- issue #174 (RD-GAP-FILL). Reddit, tier 4
(ResearchIntel kb/reddit.db): rd:Daytrading:1r3r2qn (2026-02-13)
https://www.reddit.com/r/Daytrading/comments/1r3r2qn/; rd:swingtrading:1r3w6ms
(2026-02-13) https://www.reddit.com/r/swingtrading/comments/1r3w6ms/;
rd:algotrading:1mulzoh (2025-08-19)
https://www.reddit.com/r/algotrading/comments/1mulzoh/.

POSTER'S WORDS (tier 4, untested by the poster): "Gap definition: Open vs
previous Close. Minimum gap: 0.3% (filters out noise). Fill definition:
Price returns to previous Close on the same day." Claimed use: small gaps
on low volume fill often, large gaps less so, used as a fade/follow
filter -- NOT independently tested here; this port ships existence (the
flag is causal, scale-free and reachable on real data), not evidence that
it predicts anything. The twin indicator `rd_gap_fill_rate_60` (issue #165,
`pandas_ta/statistics/rd_gap_fill_rate_60.py`) shares this exact gap/fill
definition and rolls it into a trailing share; this port is the un-rolled,
per-bar signed flag the issue (#174) asks for.

GATE A -- the issue's own formula, read bar-by-bar (not the screen
prototype -- the issue's explicit instruction is "Gate A starts from the
source formula, not the prototype"):
    prev_close = close[1]
    gap_pct    = open / prev_close - 1
    gap_up     = gap_pct  >=  min_gap   (0.3% default, filters noise)
    gap_down   = gap_pct  <= -min_gap
    filled_up   = gap_up   AND low  <= prev_close   -- up-gap, same-bar low revisits close[1]
    filled_down = gap_down AND high >= prev_close   -- down-gap, same-bar high revisits close[1]
    RD_GAP_FILL = +1 IF filled_up ELSE -1 IF filled_down ELSE 0
This is the screen prototype's `rd_gap_fill` candidate
(`docs/issues/screen/ind_screen_r6.py`) read independently from the issue's
own restatement: `g, pc = o / c.shift(1) - 1, c.shift(1)`, then
`(((g >= GAP) & (l <= pc)).astype(float) - ((g <= -GAP) & (h >= pc)).astype(float))`
with `GAP = 0.003` -- the same arithmetic, confirmed by independent
derivation rather than copied. "Price returns to previous Close on the same
day" is read as the same bar's high/low touching the prior close -- the
only reading available to a module that receives one bar per trading day
(no intraday series here), matching the twin `rd_gap_fill_rate_60`'s own
decision on the identical wording.

CAUSALITY. Bar T's output reads only `open[T]`, `high[T]`, `low[T]` and
`close[T-1]`, nothing shifted toward the future. `tests/test_rd_gap_fill.py`
proves this with a future-splice probe (bars before a perturbation point J
stay bit-identical) and a mutant that appends `.shift(-1)` to the final
write (reading one bar ahead): the real module leaks 0 bars before J at
every one of 28 swept J; the mutant, a discrete {-1, 0, 1} flag that is
non-zero on only a minority of bars (an active gap-fill event), is caught
at 9 of the same 28 swept J (measured, docs/RdGapFillMeasured.md) -- not
every one, since most J land on a settled-zero stretch where a one-bar
back-date has nothing to move, the same low-power pattern `rd_horseshoe`'s
own test documents (24 of 293 there).

SCALE-FREE. `gap_pct` is a ratio (price units cancel in the division), and
both fill checks compare like-for-like price terms (`low` against
`close[1]`, `high` against `close[1]`). Multiplying `open`/`high`/`low`/
`close` by one positive constant leaves `gap_pct`'s real value and both
comparisons' truth values unchanged. Under an exact power-of-two rescale
(x8, x64) this is bit-identical, since `(open*k)/(close[1]*k)` is a
correctly-rounded division of two exactly-representable scaled operands,
equal in every bit to `open/close[1]`. Under a non-power-of-two rescale
(x10, x3.7) each scaled operand carries its own last-bit rounding, so
`gap_pct` can move by ~1e-15 relative -- far too small to flip the 0.3%
threshold on a random walk, but not proven impossible on an adversarial
input; measured 0 mismatches on `tests/test_rd_gap_fill.py`'s synthetic
frame (`docs/measure_rd_gap_fill.py`), reported as a tolerance bound, not a
mathematical guarantee the way the power-of-two case is.
"""
import numpy as np

from pandas_ta.utils import get_offset, verify_series


def rd_gap_fill(open_, high, low, close, min_gap=None, offset=None, **kwargs):
    """Candle Type: Same-Day Gap Fill, Signed (RD_GAP_FILL)"""
    # Validate Arguments
    min_gap = float(min_gap) if min_gap is not None and min_gap > 0 else 0.003
    open_ = verify_series(open_, 2)
    high = verify_series(high, 2)
    low = verify_series(low, 2)
    close = verify_series(close, 2)
    offset = get_offset(offset)

    if open_ is None or high is None or low is None or close is None:
        return

    # Calculate Result
    prev_close = close.shift(1)
    gap_pct = open_ / prev_close - 1

    filled_up = (gap_pct >= min_gap) & (low <= prev_close)
    filled_down = (gap_pct <= -min_gap) & (high >= prev_close)

    gap_fill = filled_up.astype(float) - filled_down.astype(float)
    gap_fill = gap_fill.where(prev_close.notna())

    # Offset
    if offset != 0:
        gap_fill = gap_fill.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        gap_fill.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        method = kwargs["fill_method"]
        if method in ("ffill", "pad"):
            gap_fill = gap_fill.ffill()
        elif method in ("bfill", "backfill"):
            gap_fill = gap_fill.bfill()
        else:  # a silent bfill on a typo would be a look-ahead
            raise ValueError(f"fill_method must be ffill/pad or bfill/backfill, not {method!r}")

    # Name & Category
    gap_fill.name = f"RD_GAP_FILL_{min_gap * 100:g}"
    gap_fill.category = "candles"

    return gap_fill


rd_gap_fill.__doc__ = \
"""Candle Type: Same-Day Gap Fill, Signed (RD_GAP_FILL)

Per-bar signed flag for an overnight gap -- `open` vs the prior `close`, at
least `min_gap` in magnitude -- whose own bar's high/low touches back to
the prior close. A Reddit crowd-talk definition (tier 4, untested by the
poster, issue #174): small gaps on low volume are claimed to fill often,
large gaps less so, proposed as a fade/follow filter. That use is NOT
independently tested here; this port ships existence (causal, scale-free,
reachable on real data), not evidence it predicts anything. See the module
source above for the full source citation, Gate A derivation and the
causality/scale-free argument; docs/RdGapFillMeasured.md has the measured
numbers.

Sources:
    Reddit, tier 4 (ResearchIntel kb/reddit.db): rd:Daytrading:1r3r2qn
    (2026-02-13) https://www.reddit.com/r/Daytrading/comments/1r3r2qn/;
    rd:swingtrading:1r3w6ms (2026-02-13)
    https://www.reddit.com/r/swingtrading/comments/1r3w6ms/;
    rd:algotrading:1mulzoh (2025-08-19)
    https://www.reddit.com/r/algotrading/comments/1mulzoh/

Calculation:
    Default Inputs:
        min_gap=0.003
    prev_close  = close[1]
    gap_pct     = open / prev_close - 1
    filled_up   = (gap_pct >=  min_gap) AND low  <= prev_close
    filled_down = (gap_pct <= -min_gap) AND high >= prev_close
    RD_GAP_FILL = +1 IF filled_up ELSE -1 IF filled_down ELSE 0

Args:
    open_ (pd.Series): Series of 'open's
    high (pd.Series): Series of 'high's
    low (pd.Series): Series of 'low's
    close (pd.Series): Series of 'close's
    min_gap (float): Minimum |gap| as a fraction of the prior close, e.g.
        0.003 for 0.3%. Default: 0.003
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): 'ffill'/'pad' or 'bfill'/'backfill'

Returns:
    pd.Series: RD_GAP_FILL_{min_gap*100}, a scale-free signed column in
        {-1.0, 0.0, 1.0}. NaN for the first bar (no prior close).
"""
