# -*- coding: utf-8 -*-
import numpy as np
from pandas import DataFrame, Series

from pandas_ta.utils import get_offset, verify_series


def _confirm_pivots(series, left, right):
    """Causal pivot confirmation, rightmost-tie-wins: a bar at position i
    confirms (becomes visible) at j=i+right iff it equals the max/min of
    the window [i-left, i+right] AND no bar strictly after it within that
    window also equals the extreme. Same validated rule as
    `pandas_ta.trend.swing_equilibrium._confirm_pivots` (see that module
    for the two failed vectorized attempts this rule replaced -- naive
    equality over-fires on plateaus, requiring uniqueness over-suppresses
    genuine ties like double-tops). Duplicated here rather than imported
    across sibling indicator modules, matching this package's convention
    of self-contained indicator files (macd.py importing ema is the
    exception, not the rule).
    """
    window = left + right + 1
    n = len(series)
    vals = series.to_numpy(dtype=float)
    out_max = np.full(n, np.nan)
    out_min = np.full(n, np.nan)
    for j in range(window - 1, n):
        i = j - right
        w = vals[j - window + 1: j + 1]
        if np.isnan(vals[i]):
            continue
        extreme_max = np.nanmax(w)
        if vals[i] == extreme_max:
            later = vals[i + 1: j + 1]
            if not (len(later) and np.any(later == extreme_max)):
                out_max[j] = vals[i]
        extreme_min = np.nanmin(w)
        if vals[i] == extreme_min:
            later = vals[i + 1: j + 1]
            if not (len(later) and np.any(later == extreme_min)):
                out_min[j] = vals[i]
    return Series(out_max, index=series.index), Series(out_min, index=series.index)


def zigzag_fib(high, low, close, length=None, offset=None, **kwargs):
    """Indicator: Zigzag Fibonacci Retracement Distance (ZZFIB)"""
    length = int(length) if length and length > 0 else 5
    high = verify_series(high, 2 * length + 1)
    low = verify_series(low, 2 * length + 1)
    close = verify_series(close, 2 * length + 1)
    offset = get_offset(offset)

    if high is None or low is None or close is None: return

    pivot_high, _ = _confirm_pivots(high, length, length)
    _, pivot_low = _confirm_pivots(low, length, length)

    # Alternating zigzag: a confirmed high pivot starts (or extends, if it
    # is even higher and no low has confirmed since) the up leg; a
    # confirmed low pivot mirrors it for the down leg. This is the ONE
    # piece swing_equilibrium's independent high/low tracking doesn't have
    # -- alternation plus replace-if-more-extreme-before-reversing -- and
    # is implemented as an explicit sequential scan, the same style already
    # used by the pre-existing `pandas_ta.trend.bos` for equivalent
    # running state. p1/p2 track the last TWO confirmed zigzag prices as of
    # each bar (all that's needed for a Fibonacci retracement of the
    # CURRENT leg); Pine's source keeps a bounded 10-point history because
    # it also draws older waves, which this port does not need.
    n = len(close)
    ph_vals = pivot_high.to_numpy()
    pl_vals = pivot_low.to_numpy()
    p1 = np.full(n, np.nan)
    p2 = np.full(n, np.nan)
    last_dir = 0
    last_price = np.nan
    prev_price = np.nan
    for j in range(n):
        if not np.isnan(ph_vals[j]):
            if last_dir <= 0:
                prev_price = last_price
                last_price = ph_vals[j]
                last_dir = 1
            elif ph_vals[j] > last_price:
                last_price = ph_vals[j]
        if not np.isnan(pl_vals[j]):
            if last_dir >= 0:
                prev_price = last_price
                last_price = pl_vals[j]
                last_dir = -1
            elif pl_vals[j] < last_price:
                last_price = pl_vals[j]
        p1[j] = prev_price
        p2[j] = last_price

    p1 = Series(p1, index=close.index)
    p2 = Series(p2, index=close.index)
    diff = p2 - p1

    # Retracement only (Pine's `is_ext=false` branch) -- the auto-detect /
    # trend-based-extension mode is NOT ported, out of scope for this pass.
    fib50 = p2 - diff * 0.5
    fib618 = p2 - diff * 0.618
    dist50_pct = (close - fib50) / close * 100
    dist618_pct = (close - fib618) / close * 100

    # Offset
    if offset != 0:
        dist50_pct = dist50_pct.shift(offset)
        dist618_pct = dist618_pct.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        dist50_pct.fillna(kwargs["fillna"], inplace=True)
        dist618_pct.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        dist50_pct.fillna(method=kwargs["fill_method"], inplace=True)
        dist618_pct.fillna(method=kwargs["fill_method"], inplace=True)

    _props = f"_{length}"
    dist50_pct.name = f"ZZFIB_50{_props}"
    dist618_pct.name = f"ZZFIB_618{_props}"

    df = DataFrame({dist50_pct.name: dist50_pct, dist618_pct.name: dist618_pct})
    df.name = f"ZZFIB{_props}"
    df.category = "trend"

    return df


zigzag_fib.__doc__ = \
"""Zigzag Fibonacci Retracement Distance (ZZFIB)

Scale-free % distance from close to the 0.5 and 0.618 (golden ratio)
Fibonacci retracement levels of the CURRENT zigzag leg -- the alternating
swing-high/swing-low sequence a chartist draws by hand. Distinct from
`swing_equilibrium` (independent, non-alternating high/low tracking): a
zigzag only advances on a REVERSAL, so its "current leg" is the most
recent confirmed swing-to-swing move, not a fixed lookback window.

Source: TradingView community indicator "GCM Fibonacci Engine for Elliott
Waves", https://www.tradingview.com/script/DxyCtMgp-GCM-Fibonacci-Engine-for-Elliott-Waves/
(ported into AwakenAnalytics/Backtesting TVPTA-3, 2026-08-04; MPL-2.0 per
TradingView's open-source publication convention). Only the alternating
zigzag + Fibonacci RETRACEMENT arithmetic is ported -- the source script's
Elliott Wave labeling/validation, its "Auto Detect" extension-vs-
retracement mode, and its full 9-level fan (0.236 .. 4.236) are NOT
replicated; scoped down to the two most commonly used levels.

Calculation:
    Default Inputs:
        length=5  (bars each side required to confirm a pivot)
    Zigzag: alternating confirmed pivot highs/lows (see `_confirm_pivots`
        docstring for the causal, rightmost-tie-wins confirmation rule).
        A pivot in the SAME direction as the current leg replaces the leg
        endpoint if more extreme; a pivot in the OPPOSITE direction starts
        a new leg.
    p1, p2 = the last two confirmed zigzag prices (the current leg)
    diff = p2 - p1
    ZZFIB_50  = (close - (p2 - diff*0.5))   / close * 100
    ZZFIB_618 = (close - (p2 - diff*0.618)) / close * 100

Args:
    high (pd.Series): Series of 'high's
    low (pd.Series): Series of 'low's
    close (pd.Series): Series of 'close's
    length (int): Bars each side required to confirm a pivot. Default: 5
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.DataFrame: ZZFIB_50_length, ZZFIB_618_length columns.
"""
