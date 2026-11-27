# -*- coding: utf-8 -*-
"""Dip below the 10-day high in average-range units -- issue #181
(RD-DIP-DEPTH-10-25). Reddit, tier 4 (ResearchIntel kb/reddit.db):
rd:algotrading:1rjvxjy (2026-03-03) https://www.reddit.com/r/algotrading/comments/1rjvxjy/;
rd:Daytrading:1rktyiu (2026-03-04) https://www.reddit.com/r/Daytrading/comments/1rktyiu/;
rd:algotrading:1cwsco8 (2024-05-20) https://www.reddit.com/r/algotrading/comments/1cwsco8/;
rd:Trading:1rktege (2026-03-04) https://www.reddit.com/r/Trading/comments/1rktege/.

POSTER'S WORDS (tier 4, untested by the poster): "close < (10 days high -
2.5 * (25 days average high - 25 days average low)", claimed use an oversold
mean-reversion entry on SPY (enter at the ratio below > 2.5, with IBS < 0.3
-- NOT independently tested here; this port ships existence (causal,
scale-free, reachable on real data), not evidence that it predicts anything.

GATE A -- the issue's own formula, read bar-by-bar (its own instruction:
"Gate A starts from the source formula, not the prototype"
`docs/issues/screen/ind_screen_r6.py`'s `rd_dip_depth_10_25`, which reads
the same way):

    DIP_DEPTH_t = (HHV(high, 10)_t - close_t) / (SMA(high, 25)_t - SMA(low, 25)_t)

Rearranging the poster's own inequality, "close < 10-day high - 2.5 *
(25-day avg high - 25-day avg low)", onto one side gives exactly
"(10-day high - close) / (25-day avg high - 25-day avg low) > 2.5" -- the
ratio shipped here IS the poster's own left-hand quantity, and the poster's
"> 2.5" is an entry THRESHOLD on it, not part of the indicator; this fork
ships the continuous feature, not a signal (the same convention
`rd_std_ratio_20_60` and `rd_range_contraction` use for their own
posters' thresholds). `HHV` is a trailing rolling max, `SMA` a plain
rolling mean -- both match the screen prototype's own helpers
(`tsmax(x, n)` = `x.rolling(n).max()`, `mean(x, n)` = `x.rolling(n).mean()`).
Division by zero (a flat 25-bar high/low average, e.g. a dead market with
zero range for 25 consecutive bars) -> NaN, not inf: see the `replace`
below, the same guard `rd_range_contraction` and `rd_std_ratio_20_60` use
for their own zero-denominator case.

CAUSALITY. Bar T's output reads only `high[T-length+1 .. T]` for the HHV
term and `high[T-avg_length+1 .. T]` / `low[T-avg_length+1 .. T]` for the
two averages -- every rolling window (`max`, `mean`) is backward-looking by
construction (`pandas.Series.rolling` with no `center` argument reads only
the current and PRIOR rows of its input), and none of the three windows
feeds another, so composing them (two independent paths over raw
high/low/close, combined only in the final ratio) stays causal.
`tests/test_rd_dip_depth_10_25.py` proves this with a future-splice probe
(bars before a perturbation point J stay bit-identical whether or not the
frame's tail is replaced) and a mutant that appends `.shift(-1)` to the
final ratio (reading one bar ahead): the real module leaks 0 bars at every
swept J; the mutant is live and leaks at every one.

SCALE-FREE. For a positive price rescale by an exactly-representable factor
`k` (a power of two): `HHV(high*k, length) = k*HHV(high, length)` exactly
(scaling every element of a window by the same exact factor scales its max
by that same factor, since max picks an existing element rather than
computes a new value), and `close*k` scales exactly by `k` too, so
`numerator' = k*HHV(high,length) - k*close = k*numerator` exactly (IEEE-754
subtraction of two exactly-k-scaled operands, for a power-of-two `k`,
returns exactly `k` times the unscaled subtraction's result). The same
argument applies to `SMA(high*k, avg_length)` and `SMA(low*k, avg_length)`:
summing `k`-scaled terms and dividing by the same integer `avg_length`
returns exactly `k*SMA(high, avg_length)` and `k*SMA(low, avg_length)`, so
`denominator' = k*denominator` exactly too. The final ratio
`(k*numerator)/(k*denominator)` is then IEEE-754 division of two operands
both scaled by the same exact `k`, which returns a bit-identical quotient
to the unscaled `numerator/denominator` -- the same cancellation
`rd_range_contraction` (`pandas_ta/volatility/rd_range_contraction.py`)
relies on for its own ratio of range-based terms. Measured bit-identical
under x8/x64 (max absolute difference 0.0), and within a tight tolerance
under the non-power-of-two x10/x3.7 rescale, in
`tests/test_rd_dip_depth_10_25.py` and
`docs/measure_rd_dip_depth_10_25_cpu.py` (see
docs/RdDipDepth1025Measured.md for the measured numbers).

NON-REDUNDANCY. The issue's own prototype screen (`docs/issues/screen/candidates_r6.csv`)
puts this candidate's nearest comparators at `kdj_J_9_3` (0.8401) and `willr` (0.8241) --
and `willr`'s own formula, `100*(close-HHV(high,n))/(HHV(high,n)-LLV(low,n))`, shares the
same `HHV(high,n) - close` numerator shape this port uses. The two are not the same
feature: `willr` divides that gap by the SAME n-bar window's own high-low range (a
same-window normalisation), while this port divides it by a SEPARATELY-averaged 25-bar
mean-high-minus-mean-low -- a longer, smoother denominator that does not collapse to
`willr`'s own range at any parameter choice. That structural difference is why the measured
0.8401/0.8241 lands in DISCLOSE_GAP (0.80 <= rho < 0.90), not STRUCK (>= 0.90): a close
denominator, not an identical one. See docs/RdDipDepth1025Measured.md's Gate E section.
"""
import numpy as np

from pandas_ta.utils import get_offset, verify_series


def rd_dip_depth_10_25(high, low, close, length=None, avg_length=None, offset=None, **kwargs):
    """Indicator: Dip Depth, HHV-close over average range (RD_DIP_DEPTH_10_25)"""
    # Validate Arguments
    length = int(length) if length and length > 0 else 10
    avg_length = int(avg_length) if avg_length and avg_length > 0 else 25
    _length = max(length, avg_length)
    high = verify_series(high, _length)
    low = verify_series(low, _length)
    close = verify_series(close, _length)
    offset = get_offset(offset)

    if high is None or low is None or close is None: return

    # Calculate Result
    numerator = high.rolling(length).max() - close
    denominator = high.rolling(avg_length).mean() - low.rolling(avg_length).mean()
    with np.errstate(invalid="ignore", divide="ignore"):
        result = (numerator / denominator).replace([np.inf, -np.inf], np.nan)

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
    result.name = f"RD_DIP_DEPTH_10_25_{length}_{avg_length}"
    result.category = "momentum"

    return result


rd_dip_depth_10_25.__doc__ = \
"""Dip Depth, HHV-close over average range (RD_DIP_DEPTH_10_25)

The gap between the trailing `length`-bar high and the current close,
expressed in units of the trailing `avg_length`-bar average high-low range:
`(HHV(high, length) - close) / (SMA(high, avg_length) - SMA(low, avg_length))`.
A Reddit crowd-talk definition (tier 4, untested by the poster, issue #181):
"close < (10 days high - 2.5 * (25 days average high - 25 days average
low)" -- rearranged, that is exactly "this ratio > 2.5", an entry threshold
the poster applies on top of this continuous feature, together with
IBS < 0.3 -- NOT independently tested here; this port ships existence
(causal, scale-free, reachable on real data), not evidence it predicts
anything. See the module source above for the full source citation, Gate A
derivation and the causality/scale-free argument;
docs/RdDipDepth1025Measured.md has the measured numbers.

Sources:
    Reddit, tier 4 (ResearchIntel kb/reddit.db): rd:algotrading:1rjvxjy
    (2026-03-03) https://www.reddit.com/r/algotrading/comments/1rjvxjy/;
    rd:Daytrading:1rktyiu (2026-03-04)
    https://www.reddit.com/r/Daytrading/comments/1rktyiu/;
    rd:algotrading:1cwsco8 (2024-05-20)
    https://www.reddit.com/r/algotrading/comments/1cwsco8/;
    rd:Trading:1rktege (2026-03-04)
    https://www.reddit.com/r/Trading/comments/1rktege/

Calculation:
    Default Inputs:
        length=10, avg_length=25
    numerator = HHV(high, length) - close
    denominator = SMA(high, avg_length) - SMA(low, avg_length)
    RD_DIP_DEPTH_10_25 = numerator / denominator
    (+-inf from a zero `avg_length` average range -> NaN)

Args:
    high (pd.Series): Series of 'high's
    low (pd.Series): Series of 'low's
    close (pd.Series): Series of 'close's
    length (int): The trailing high lookback. Default: 10
    avg_length (int): The average-range lookback. Default: 25
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): 'ffill'/'pad' or 'bfill'/'backfill'

Returns:
    pd.Series: RD_DIP_DEPTH_10_25_{length}_{avg_length}, a scale-free
        (dimensionless) ratio, typically >= 0 on valid OHLC data (the
        trailing high is at least the current close), NaN for the first
        `max(length, avg_length) - 1` bars and wherever the average range
        is exactly zero.
"""
