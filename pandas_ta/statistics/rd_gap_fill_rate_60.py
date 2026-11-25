# -*- coding: utf-8 -*-
"""Share of 0.3%+ gaps filled the same day, trailing 60 bars -- issue #165
(RD-GAP-FILL-RATE-60). Reddit, tier 4 (ResearchIntel kb/reddit.db):
rd:Daytrading:1r3r2qn (2026-02-13) https://www.reddit.com/r/Daytrading/comments/1r3r2qn/;
rd:swingtrading:1r3w6ms (2026-02-13) https://www.reddit.com/r/swingtrading/comments/1r3w6ms/;
rd:algotrading:1mulzoh (2025-08-19) https://www.reddit.com/r/algotrading/comments/1mulzoh/.

POSTER'S WORDS (tier 4, untested by the poster): "Gap definition: Open vs
previous Close. Minimum gap: 0.3% (filters out noise). Fill definition: Price
returns to previous Close on the same day." Claimed use: small gaps on low
volume fill often, large gaps less so, used as a fade/follow filter -- NOT
independently tested here; this port ships existence (the share is causal,
scale-free and reachable on real data), not evidence that it predicts
anything.

GATE A -- the issue's own formula, read bar-by-bar (not the screen prototype;
the issue's instruction is "Gate A starts from the source formula, not the
prototype"):
    gap_pct   = open / close[1] - 1                  (today's open vs yesterday's close)
    is_gap    = |gap_pct| >= min_gap                  (0.3% default, filters noise)
    filled    = (gap_pct >=  min_gap AND low  <= close[1])    -- up-gap, same-day low revisits close[1]
             OR (gap_pct <= -min_gap AND high >= close[1])    -- down-gap, same-day high revisits close[1]
    RD_GAP_FILL_RATE_60 = SUM(filled, 60) / SUM(is_gap, 60)   (NaN with no gap in the window)
The 60-bar window is not in the poster's words -- the issue discloses it as
"this prototype's choice" (`docs/issues/screen/ind_screen_r6.py`'s
`rd_gap_fill_rate_60`), kept here as the `length` default, not hard-coded.
"Price returns to previous Close on the same day" is read as the SAME bar's
high/low touching the prior close -- the only reading of "same day" available
to a module that receives one bar per trading day (no intraday series here).

CAUSALITY. Bar T's output reads `open[T]`, `high[T]`, `low[T]` and
`close[T-1]` through `close[T]` (the rolling window), nothing shifted toward
the future. `tests/test_rd_gap_fill_rate_60.py` proves this with a
future-splice probe (bars before a perturbation point J stay bit-identical)
and a mutant that appends `.shift(-1)` to the final ratio (reading one bar
ahead): the real module leaks 0 bars before J at every swept J (28 of 28);
the mutant, being a continuous ratio that changes on almost every bar, leaks
at 18 of the same 28 swept J (measured,
docs/RdGapFillRate60Measured.md) -- a majority, not every one, since a
NaN-mask coincidence at the splice point can let it slip through at some J.

SCALE-FREE. `gap_pct` is already a percentage (price units cancel in the
division), and `filled` is two like-for-like price comparisons (`low` against
`close[1]`, `high` against `close[1]`) -- multiplying `open`/`high`/`low`/
`close` by one positive constant leaves `gap_pct`'s real value and both
comparisons' truth values unchanged. Under an exact power-of-two rescale
(x8, x64) this is bit-identical, since `(open*k)/(close[1]*k)` is a correctly
-rounded division of two exactly-representable scaled operands, equal in
every bit to `open/close[1]`. Under a non-power-of-two rescale (x10, x3.7)
each scaled operand carries its own last-bit rounding, so `gap_pct` can move
by ~1e-15 relative -- far too small to flip the 0.3% threshold on a random
walk, but not proven impossible on an adversarial input; measured 0
mismatches on `tests/test_rd_gap_fill_rate_60.py`'s synthetic frame
(`docs/measure_rd_gap_fill_rate_60.py`), not claimed as a mathematical
guarantee the way the bit-identical powers-of-two case is.
"""
import numpy as np

from pandas_ta.utils import get_offset, verify_series


def rd_gap_fill_rate_60(open_, high, low, close, length=None, min_gap=None, offset=None, **kwargs):
    """Indicator: Share of 0.3%+ Gaps Filled the Same Day (RD_GAP_FILL_RATE)"""
    # Validate Arguments
    length = int(length) if length and length > 0 else 60
    min_gap = float(min_gap) if min_gap is not None and min_gap > 0 else 0.003
    open_ = verify_series(open_, length + 1)
    high = verify_series(high, length + 1)
    low = verify_series(low, length + 1)
    close = verify_series(close, length + 1)
    offset = get_offset(offset)

    if open_ is None or high is None or low is None or close is None:
        return

    # Calculate Result
    prev_close = close.shift(1)
    gap_pct = open_ / prev_close - 1

    is_gap = gap_pct.abs() >= min_gap
    filled = ((gap_pct >= min_gap) & (low <= prev_close)) \
        | ((gap_pct <= -min_gap) & (high >= prev_close))

    gap_count = is_gap.astype(float).rolling(length).sum()
    filled_count = filled.astype(float).rolling(length).sum()

    rate = (filled_count / gap_count).replace([np.inf, -np.inf], np.nan)
    # A window with no gap divides 0 by 0, already NaN in IEEE float; the
    # explicit mask below is for an inf that cannot occur mathematically
    # here (filled_count <= gap_count always) but is kept for the same
    # reason `sdiv` keeps it in the screen prototype: defensive, not reached.
    rate = rate.where(gap_count > 0)

    # Offset
    if offset != 0:
        rate = rate.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        rate.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        method = kwargs["fill_method"]
        if method in ("ffill", "pad"):
            rate = rate.ffill()
        elif method in ("bfill", "backfill"):
            rate = rate.bfill()
        else:  # a silent bfill on a typo would be a look-ahead
            raise ValueError(f"fill_method must be ffill/pad or bfill/backfill, not {method!r}")

    # Name & Category
    rate.name = f"RD_GAP_FILL_RATE_{length}_{min_gap * 100:g}"
    rate.category = "statistics"

    return rate


rd_gap_fill_rate_60.__doc__ = \
"""Share of 0.3%+ Gaps Filled the Same Day (RD_GAP_FILL_RATE)

Trailing share of gaps -- `open` vs the prior `close`, at least `min_gap`
in magnitude -- whose same bar's high/low touches back to the prior close.
A Reddit crowd-talk definition (tier 4, untested by the poster, issue #165):
small gaps on low volume are claimed to fill often, large gaps less so,
proposed as a fade/follow filter. That use is NOT independently tested here;
this port ships existence (causal, scale-free, reachable on real data), not
evidence it predicts anything. See the module source above for the full
source citation, Gate A derivation and the causality/scale-free argument;
docs/RdGapFillRate60Measured.md has the measured numbers.

Sources:
    Reddit, tier 4 (ResearchIntel kb/reddit.db): rd:Daytrading:1r3r2qn
    (2026-02-13) https://www.reddit.com/r/Daytrading/comments/1r3r2qn/;
    rd:swingtrading:1r3w6ms (2026-02-13)
    https://www.reddit.com/r/swingtrading/comments/1r3w6ms/;
    rd:algotrading:1mulzoh (2025-08-19)
    https://www.reddit.com/r/algotrading/comments/1mulzoh/

Calculation:
    Default Inputs:
        length=60, min_gap=0.003
    prev_close = close[1]
    gap_pct    = open / prev_close - 1
    is_gap     = ABS(gap_pct) >= min_gap
    filled     = (gap_pct >= min_gap AND low <= prev_close)
              OR (gap_pct <= -min_gap AND high >= prev_close)
    RD_GAP_FILL_RATE = SUM(filled, length) / SUM(is_gap, length)
                       (NaN wherever the window holds no gap)

Args:
    open_ (pd.Series): Series of 'open's
    high (pd.Series): Series of 'high's
    low (pd.Series): Series of 'low's
    close (pd.Series): Series of 'close's
    length (int): The rolling window. Default: 60
    min_gap (float): Minimum |gap| as a fraction of the prior close, e.g.
        0.003 for 0.3%. Default: 0.003
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): 'ffill'/'pad' or 'bfill'/'backfill'

Returns:
    pd.Series: RD_GAP_FILL_RATE_{length}_{min_gap*100}, a scale-free
        (dimensionless) share in [0, 1]. NaN for the first `length - 1` bars
        (the rolling window's warm-up) and for any window holding no gap at
        all.
"""
