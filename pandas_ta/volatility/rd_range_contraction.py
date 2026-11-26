# -*- coding: utf-8 -*-
"""Short over long average of the 5-bar high-low spread -- issue #176
(RD-RANGE-CONTRACTION). Reddit, tier 4 (ResearchIntel kb/reddit.db):
rd:algotrading:dejh73 (2019-10-07) https://www.reddit.com/r/algotrading/comments/dejh73/.

POSTER'S WORDS (tier 4, untested by the poster): "look for a long period MA
of your spread measurement to cross over a short period MA of your spread
measurement." Claimed use: Wedge detection component (converging range) --
NOT independently tested here; this port ships existence (causal, scale-free,
reachable on real data), not evidence that it predicts anything.

GATE A -- the issue's own formula, read bar-by-bar (not the screen
prototype `docs/issues/screen/ind_screen_r6.py`'s `rd_range_contraction`; the
issue's instruction is "Gate A starts from the source formula, not the
prototype"):
    spread_t = HHV(high, n)_t - LLV(low, n)_t         -- the n-bar high-low spread
    RD_RANGE_CONTRACTION_t = MA(spread, short)_t / MA(spread, long)_t
with n=5, short=10, long=50 (the issue's own scale-free form: "as a ratio"
of the two MAs, not the poster's un-specified "cross over"). `MA` here is a
simple rolling mean, matching the screen prototype's `mean()` helper
(`x.rolling(n).mean()`) -- the poster leaves the MA type open, and the
prototype's SMA choice is adopted as stated by the issue's own "Prototype"
line. Division by zero (a flat `long` average, e.g. a constant spread of 0,
such as a dead market with zero daily range) -> NaN, not inf: `sdiv` below.

CAUSALITY. Bar T's output reads only `high[T-n-short-long+2 .. T]` and
`low[T-n-short-long+2 .. T]` -- every rolling window (max, min, mean) is
backward-looking by construction (`pandas.Series.rolling` with no `center`
argument reads only the current and PRIOR rows of its input). `n`, `short`
and `long` are all independently causal, so composing them (spread -> two
rolling means -> ratio) stays causal.
`tests/test_rd_range_contraction.py` proves this with a future-splice probe
(bars before a perturbation point J stay bit-identical whether or not the
frame's tail is replaced) and a mutant that appends `.shift(-1)` to the
`spread` write (reading one bar ahead): the real module leaks 0 bars at every
swept J; the mutant is live and leaks at every one.

SCALE-FREE. For a positive price rescale by an exactly-representable factor
`k` (a power of two): `HHV(high*k, n) = k*HHV(high, n)` and
`LLV(low*k, n) = k*LLV(low, n)` exactly (scaling every element of a window by
the same exact factor scales its max/min by that same factor, since max/min
pick an existing element rather than compute a new value), so
`spread' = k*HHV(high,n) - k*LLV(low,n) = k*spread` -- and because `k` is a
power of two, `k*a - k*b` is computed exactly as `k*(a-b)` would be (no
rounding is introduced by a power-of-two multiply, and IEEE-754 subtraction
of two exactly-k-scaled operands returns exactly k times the unscaled
subtraction's result). The same argument applies to `MA(spread, short)` and
`MA(spread, long)`: summing `k*spread_i` terms and dividing by the same
integer `short` or `long` returns exactly `k*MA(spread, short)` and
`k*MA(spread, long)`. The final ratio `(k*num)/(k*denom)` is then IEEE-754
division of two operands both scaled by the same exact `k`, which returns a
bit-identical quotient to the unscaled `num/denom` -- the same cancellation
`massi` (`pandas_ta/volatility/massi.py`, a ratio of two EMAs of the same
high-low range) relies on. Measured bit-identical under x8/x64 (max absolute
difference 0.0), and within a tight tolerance under the non-power-of-two
x10/x3.7 rescale, in `tests/test_rd_range_contraction.py` and
`docs/measure_rd_range_contraction_cpu.py` (see docs/RdRangeContractionMeasured.md
for the measured numbers).
"""
import numpy as np
import pandas as pd

from pandas_ta.utils import get_offset, verify_series


def rd_range_contraction(high, low, n=None, short=None, long=None, offset=None, **kwargs):
    """Indicator: Range Contraction, short/long MA of the n-bar spread (RD_RANGE_CONTRACTION)"""
    # Validate Arguments
    n = int(n) if n and n > 0 else 5
    short = int(short) if short and short > 0 else 10
    long = int(long) if long and long > 0 else 50
    if long < short:
        short, long = long, short
    _length = n + long - 1
    high = verify_series(high, _length)
    low = verify_series(low, _length)
    offset = get_offset(offset)

    if high is None or low is None: return

    # Calculate Result
    spread = high.rolling(n).max() - low.rolling(n).min()
    short_ma = spread.rolling(short).mean()
    long_ma = spread.rolling(long).mean()
    with np.errstate(invalid="ignore", divide="ignore"):
        result = (short_ma / long_ma).replace([np.inf, -np.inf], np.nan)

    # Offset
    if offset != 0:
        result = result.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        result.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        method = kwargs["fill_method"]
        if method in ("ffill", "pad"):
            result = result.ffill()
        elif method in ("bfill", "backfill"):
            result = result.bfill()
        else:  # a silent bfill on a typo would be a look-ahead
            raise ValueError(f"fill_method must be ffill/pad or bfill/backfill, not {method!r}")

    # Name & Category
    result.name = f"RD_RANGE_CONTRACTION_{n}_{short}_{long}"
    result.category = "volatility"

    return result


rd_range_contraction.__doc__ = \
"""Range Contraction, short/long MA of the n-bar spread (RD_RANGE_CONTRACTION)

The n-bar high-low spread (`HHV(high, n) - LLV(low, n)`), averaged over a
short and a long window and reported as their ratio: below 1 when the recent
spread is narrower than its own longer-run average (a contracting range),
above 1 when it is wider (an expanding range). A Reddit crowd-talk definition
(tier 4, untested by the poster, issue #176): "look for a long period MA of
your spread measurement to cross over a short period MA of your spread
measurement," claimed use is a Wedge-detection component (a converging
range) -- NOT independently tested here; this port ships existence (causal,
scale-free, reachable on real data), not evidence it predicts anything. See
the module source above for the full source citation, Gate A derivation and
the causality/scale-free argument; docs/RdRangeContractionMeasured.md has the
measured numbers.

Sources:
    Reddit, tier 4 (ResearchIntel kb/reddit.db): rd:algotrading:dejh73
    (2019-10-07) https://www.reddit.com/r/algotrading/comments/dejh73/

Calculation:
    Default Inputs:
        n=5, short=10, long=50
    spread = HHV(high, n) - LLV(low, n)
    RD_RANGE_CONTRACTION = MA(spread, short) / MA(spread, long)
    (+-inf from a zero `long` average -> NaN)

Args:
    high (pd.Series): Series of 'high's
    low (pd.Series): Series of 'low's
    n (int): The spread's own lookback. Default: 5
    short (int): The short MA length. Default: 10
    long (int): The long MA length. Default: 50
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): 'ffill'/'pad' or 'bfill'/'backfill'

Returns:
    pd.Series: RD_RANGE_CONTRACTION_{n}_{short}_{long}, a scale-free
        (dimensionless) ratio, NaN for the first `n + long - 2` bars (the
        combined warm-up of the spread and the long MA) and wherever the
        long-window average spread is exactly zero.
"""
