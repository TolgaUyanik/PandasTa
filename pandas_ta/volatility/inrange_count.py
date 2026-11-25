# -*- coding: utf-8 -*-
import numpy as np
from pandas import Series

from pandas_ta.utils import get_offset, verify_series


def _count(h, l, hh, ll, length):
    """The poster's `var` counter over finite arrays; NaN where a bar or its
    envelope is missing, and such a bar leaves the count where it was."""
    out = np.full(h.size, np.nan)
    cnt = 0
    for t in range(h.size):
        if not (h[t] == h[t] and l[t] == l[t] and hh[t] == hh[t]
                and ll[t] == ll[t]):
            continue
        if h[t] < hh[t] and l[t] > ll[t]:
            cnt = min(cnt + 1, length)
        else:
            cnt = max(cnt - 2, 0)
        out[t] = cnt / length
    return out


def inrange_count(high, low, length=None, offset=None, **kwargs):
    """Indicator: Inside-Range Bar Counter (INRC)"""
    # Validate Arguments
    length = int(length) if length and length > 0 else 20
    high = verify_series(high, length + 1)
    low = verify_series(low, length + 1)
    offset = get_offset(offset)

    if high is None or low is None: return

    # Calculate Result
    # An infinite high would sit in the envelope for `length` bars and make
    # every bar "inside"; masked, it behaves exactly like a NaN high.
    h = high.where(np.isfinite(high))
    l = low.where(np.isfinite(low))
    # `recent_high[1]`: the envelope ends on the PREVIOUS bar. min_periods=1
    # lets a missing bar drop out of the envelope instead of emptying the
    # next `length` bars; the head is cut to the full window below.
    hh = h.rolling(length, min_periods=1).max().shift(1)
    ll = l.rolling(length, min_periods=1).min().shift(1)
    hh.iloc[:length] = np.nan
    ll.iloc[:length] = np.nan
    inrc = Series(_count(h.to_numpy(dtype=float), l.to_numpy(dtype=float),
                         hh.to_numpy(dtype=float), ll.to_numpy(dtype=float),
                         length), index=high.index)

    # Offset
    if offset != 0:
        inrc = inrc.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        inrc.fillna(kwargs["fillna"], inplace=True)

    # Name and Categorize it
    inrc.name = f"INRC_{length}"
    inrc.category = "volatility"

    return inrc


inrange_count.__doc__ = \
"""Inside-Range Bar Counter (INRC)

A counter that rises by 1 on each bar inside the prior `length`-bar high/low
range and falls by 2 on each bar outside it, over `length`.

    cnt[T] = min(cnt[T-1] + 1, length)   if high[T] < max(high[T-length .. T-1])
                                         and low[T] > min(low[T-length .. T-1])
             max(cnt[T-1] - 2, 0)        otherwise
    INRC   = cnt / length                in [0, 1], steps of 1 / length

Source: Reddit, r/TradingView post 1k894ya (2025-04-26),
https://www.reddit.com/r/TradingView/comments/1k894ya/ -- a Pine snippet,
"if high < recent_high[1] and low > recent_low[1] in_range_count :=
math.min(in_range_count + 1, range_lookback)", the else branch
`math.max(in_range_count - 2, 0)`, with `recent_high`/`recent_low` the
highest high / lowest low over `range_lookback`. Crowd talk (tier 4): the
poster's claim ("counts how long price has stayed inside the established
range") is untested here. The post does not show `range_lookback`'s value;
20 is the screen prototype's (PandasTa issue #203), and `/ length` is the
fork's scale-free form, also the prototype's.

The comparisons are STRICT, as the poster wrote them: a bar that TIES the
prior range's high or low is outside and costs 2. On continuous floats a
tie never happens; on a tick grid it does, and it moves the column
(`docs/InrangeCountMeasured.md` §A4 prices `<=`/`>=` against it).

Causal: bar T reads the highs and lows of bars T-length .. T and the
counter's own value at T-1. Scale-free: only comparisons touch the prices,
so any positive rescale that keeps the order of the prices keeps every bit.

NaN on the first `length` bars (the envelope is not full), with the count
starting from 0 on bar `length`; and on a bar whose own high or low is NaN
or infinite, which also leaves the count unchanged and drops out of later
bars' envelopes. Both choices are the fork's, not the poster's: in Pine a
comparison with `na` is false, so that bar would cost 2.

Calculation:
    Default Inputs:
        length=20
    hh  = highest(high, length)[1]
    ll  = lowest(low, length)[1]
    cnt = min(cnt + 1, length) if high < hh and low > ll
          else max(cnt - 2, 0)
    INRC = cnt / length

Args:
    high (pd.Series): Series of 'high's
    low (pd.Series): Series of 'low's
    length (int): The range lookback, and the counter's cap. Default: 20
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)

Returns:
    pd.Series: INRC_{length}, dimensionless, in [0, 1]
"""
