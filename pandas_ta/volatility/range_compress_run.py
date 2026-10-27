# -*- coding: utf-8 -*-
from numpy import finfo, nan

from pandas_ta.ml.companions import ml_bars_since
from pandas_ta.utils import get_offset, verify_series


def range_compress_run(high, low, cap=None, offset=None, **kwargs):
    """Indicator: Range Compression Run (RCR)"""
    cap = int(cap) if cap and cap > 0 else 100
    high = verify_series(high, 2)
    low = verify_series(low, 2)
    offset = get_offset(offset)

    if high is None or low is None: return

    rng = high - low
    prior = rng.shift(1)
    # A decimal tie on tick prices can differ by float noise, which scales with
    # the PRICE (each range carries <= ~1.5 ulp of its high), not the range.
    tol = 4 * finfo(float).eps * (high.abs() + high.shift(1).abs())
    compressed = rng < prior - tol
    # The run is "bars since the last bar that did NOT compress".
    rcr = ml_bars_since(~compressed, cap=cap)
    rcr[rng.isna() | prior.isna()] = nan  # bar 0 has no prior range to compare

    # Offset
    if offset != 0:
        rcr = rcr.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        rcr.fillna(kwargs["fillna"], inplace=True)

    rcr.name = f"RCR_{cap}"
    rcr.category = "volatility"

    return rcr


range_compress_run.__doc__ = \
"""Range Compression Run (RCR)

How many consecutive bars, ending at this one, have had a high-low range
strictly below the previous bar's range. 0 on a bar whose range is equal to
or wider than the bar before it; capped at `cap`.

Source: Reddit, r/Daytrading post 1tv21c0 (2026-06-02),
https://www.reddit.com/r/Daytrading/comments/1tv21c0/ -- a feature list
naming "count_consolidating_days (range compression)". Crowd talk (tier 4):
the poster's claims (5th most predictive feature in their XGBoost model;
"Grade A" setups need 9 consecutive compressing days) are untested here. The
post gives no formula; "compression = range below the prior bar's" is the
definition used by the 2026-10-26 screen prototype (candidate
b2_range_compress_run) and is adopted as stated.

The comparison is strict, so a tie resets the run: a tie is not a
contraction. Ties are common on tick-rounded prices, and in floating point a
decimal tie can come out unequal: 115.80000000000001 - 112.95 =
2.8500000000000085 but 117.75 - 114.9 = 2.8499999999999943 (bars 170/171 of
the test walk, both 57 ticks). So "below" means below by more than the
subtraction's rounding error, 4 * eps * (|high| + |high[1]|). That error
scales with price, not with the range, so the tolerance holds at any price
level; it is far below one tick at any realistic price.

Built on `ml_bars_since`, which already counts bars since a flag last fired;
the flag here is "this bar did not compress".

Calculation:
    Default Inputs:
        cap=100
    range = high - low
    tol = 4 * eps * (|high| + |high[1]|)
    compressed = range < range[1] - tol
    RCR = bars since the last bar where not compressed, clipped to cap
    RCR is NaN wherever range or range[1] is NaN (bar 0)

Args:
    high (pd.Series): Series of 'high's
    low (pd.Series): Series of 'low's
    cap (int): Upper clip on the run length. Default: 100
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)

Returns:
    pd.Series: RCR_{cap}
"""
