# -*- coding: utf-8 -*-
from pandas_ta.utils import get_offset, verify_series


def expand3_3pct(high, low, pct=None, offset=None, **kwargs):
    """Indicator: Three Bars of Expanding Highs / Lows (EXPAND3)"""
    # Validate Arguments
    pct = float(pct) if pct and pct > 0 else 3.0
    high = verify_series(high, 3)
    low = verify_series(low, 3)
    offset = get_offset(offset)

    if high is None or low is None: return

    # Calculate Result
    up_k = 1.0 + pct / 100.0
    dn_k = 1.0 - pct / 100.0
    h1 = high.shift(1)
    h2 = high.shift(2)
    l1 = low.shift(1)
    l2 = low.shift(2)
    up = (h2 * up_k <= h1) & (h1 * up_k <= high)
    dn = (l2 * dn_k >= l1) & (l1 * dn_k >= low)
    valid = high.notna() & h1.notna() & h2.notna() & low.notna() & l1.notna() & l2.notna()
    expand = (up.astype(float) - dn.astype(float)).where(valid)

    # Offset
    if offset != 0:
        expand = expand.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        expand.fillna(kwargs["fillna"], inplace=True)

    # Name and Categorize it
    expand.name = f"EXPAND3_{pct}"
    expand.category = "trend"

    return expand


expand3_3pct.__doc__ = \
"""Three Bars of Expanding Highs / Lows (EXPAND3)

+1 on a bar whose high closes a run of three highs, each at least `pct`
percent above the one before; -1 on a bar whose low closes a run of three
lows, each at least `pct` percent below the one before; 0 otherwise. Both
legs can fire on one wide bar sequence, and then they net to 0.

    up[T]   = high[T-2] * (1 + pct/100) <= high[T-1]
              and high[T-1] * (1 + pct/100) <= high[T]
    dn[T]   = low[T-2] * (1 - pct/100) >= low[T-1]
              and low[T-1] * (1 - pct/100) >= low[T]
    EXPAND3_pct[T] = up[T] - dn[T]

Source: Reddit r/TradingView, post 1jlvqer (2025-03-28),
https://www.reddit.com/r/TradingView/comments/1jlvqer/ -- crowd talk (tier
4), untested by its poster: `highSignal = high[2]*1.03 <= high[1] and
high[1]*1.03 <= high`, "same for the lows the other way around". PandasTa
issue #201. The low leg is read as the mirror on the multiplier side,
`low[1] <= 0.97 * low[2]` (lows 3% LOWER), not `low[1] * 1.03 <= low[2]`;
the two differ only on steps between 2.913% and 3%.

Ties fire: both comparisons are non-strict, as in the source. At the
default the multipliers are exactly the float literals 1.03 and 0.97
(`1 + 3/100 == 1.03`), so a tick-rounded step that lands exactly on 3%
fires or not by the float product, the same as the Pine expression.

Causal: bar T reads `high` and `low` on bars T-2, T-1, T and nothing later.

Scale-free: the output is a comparison of `price * k` against `price`, so a
positive power-of-two rescale (x8, x64) is bit-identical; any other
positive factor can only flip a comparison sitting within one ulp of the
3% step.

NaN on the first 2 bars, and on any bar whose 3-bar window holds a NaN high
or low; otherwise -1, 0 or +1.

Calculation:
    Default Inputs:
        pct=3
    up         = (high[2] * 1.03 <= high[1]) & (high[1] * 1.03 <= high)
    dn         = (low[2] * 0.97 >= low[1]) & (low[1] * 0.97 >= low)
    EXPAND3_3.0 = up - dn

Args:
    high (pd.Series): Series of 'high's
    low (pd.Series): Series of 'low's
    pct (float): The minimum step between consecutive highs (lows), in
        percent. Default: 3
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)

Returns:
    pd.Series: EXPAND3_3.0
"""
