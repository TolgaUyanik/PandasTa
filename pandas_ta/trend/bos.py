# -*- coding: utf-8 -*-
import numpy as np
from pandas import DataFrame
from pandas_ta.utils import get_offset, verify_series


def _confirmed_swings(high, low, swing_length):
    """Swing highs/lows, each written on the bar where it becomes known.

    Same window as the old centred `rolling(swing_length, center=True)`:
    with `L = swing_length`, `k = (L - 1) // 2` and `left = L - 1 - k`, bar
    `j` is a swing high when `high[j]` is the max of `high[j-left .. j+k]`
    and no bar in `(j, j+k]` ties it (the rightmost tie wins, as in
    `swing_equilibrium._confirm_pivots`). That is decided only once bar
    `j + k` has printed, so the swing is written on bar `t = j + k`, never
    on `j`. Lows mirror it with `min`.

    Returns two float Series indexed like `high`: the confirmed swing's
    high (resp. low) on its confirmation bar, NaN elsewhere.
    """
    k = (swing_length - 1) // 2

    def _side(series, is_high):
        cand = series.shift(k)                      # the bar j = t - k
        roll = series.rolling(swing_length)         # bars [t-L+1, t] = [j-left, j+k]
        extreme = roll.max() if is_high else roll.min()
        hit = cand == extreme
        if k > 0:
            later = series.rolling(k)               # bars (j, j+k] = [t-k+1, t]
            later_ext = later.max() if is_high else later.min()
            # `cand` is the extreme, so a later tie is a later bar EQUAL to it.
            hit &= (later_ext < cand) if is_high else (later_ext > cand)
        return cand.where(hit)

    return _side(high, True), _side(low, False)


def bos(high, low, close, swing_length=None, offset=None, **kwargs):
    """Indicator: Break of Structure (BOS)"""
    # Validate Arguments
    swing_length = int(swing_length) if swing_length and swing_length > 0 else 5
    high = verify_series(high, swing_length)
    low = verify_series(low, swing_length)
    close = verify_series(close, swing_length)
    offset = get_offset(offset)

    if high is None or low is None or close is None: return

    # Swings are written on the bar that confirms them (bar j + k), so no
    # column reads a bar after the one it is written on.
    sh_conf, sl_conf = _confirmed_swings(high, low, swing_length)
    sh = sh_conf.to_numpy(dtype=float)
    sl = sl_conf.to_numpy(dtype=float)
    cl = close.to_numpy(dtype=float)

    n = len(close)
    bos_bull = np.zeros(n)
    bos_bear = np.zeros(n)
    higher_high = np.zeros(n)
    lower_low = np.zeros(n)

    last_swing_high = np.nan
    last_swing_low = np.nan

    for t in range(n):
        if not np.isnan(sh[t]):
            # HIGHER_HIGH fires on the confirmation bar, against the previous
            # confirmed swing high.
            if not np.isnan(last_swing_high) and sh[t] > last_swing_high:
                higher_high[t] = 1
            last_swing_high = sh[t]

        if not np.isnan(sl[t]):
            if not np.isnan(last_swing_low) and sl[t] < last_swing_low:
                lower_low[t] = 1
            last_swing_low = sl[t]

        # BOS compares close[t] only with swings confirmed at or before t.
        if not np.isnan(last_swing_high) and cl[t] > last_swing_high:
            bos_bull[t] = 1
        if not np.isnan(last_swing_low) and cl[t] < last_swing_low:
            bos_bear[t] = 1

    df = DataFrame({
        "BOS_BULL":    bos_bull,
        "BOS_BEAR":    bos_bear,
        "HIGHER_HIGH": higher_high,
        "LOWER_LOW":   lower_low,
    }, index=close.index)

    df.name = f"BOS_{swing_length}"
    df.category = "trend"

    if offset != 0:
        df = df.shift(offset)

    if "fillna" in kwargs:
        df.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        df.fillna(method=kwargs["fill_method"], inplace=True)

    return df


bos.__doc__ = \
"""Break of Structure (bos)

Identifies when price closes above the last confirmed swing high (bullish
BOS) or below the last confirmed swing low (bearish BOS). Also returns
HIGHER_HIGH and LOWER_LOW on the bar that confirms a swing.

Causal since issue #332: a swing is written on the bar where it becomes
known, `(swing_length - 1) // 2` bars after the pivot bar. Before #332
the swings came from `rolling(swing_length, center=True)` and were written
on the pivot bar itself, so every column read that many bars ahead.

Sources:
    ICT / Smart Money Concept (break of structure).
    Swing confirmation: this repo's `pandas_ta/trend/swing_equilibrium.py`
    `_confirm_pivots` (MIT), applied to the centred window `bos` used
    before #332, with the same rightmost-tie rule.

Calculation:
    Default Inputs:
        swing_length=5
    L = swing_length, k = (L - 1) // 2, left = L - 1 - k
    swing high at bar j, confirmed on bar t = j + k, iff
        high[j] == max(high[j-left .. j+k])  and
        high[i] != high[j] for every i in (j, j+k]     (rightmost tie wins)
    swing low: the mirror, with min over low
    BOS_BULL = 1 when close[t] > the last swing high confirmed at or before t
    BOS_BEAR = 1 when close[t] < the last swing low confirmed at or before t
    HIGHER_HIGH = 1 on a confirmation bar whose swing high exceeds the
        previous confirmed swing high
    LOWER_LOW   = 1 on a confirmation bar whose swing low is below the
        previous confirmed swing low

Args:
    high (pd.Series): Series of 'high's
    low (pd.Series): Series of 'low's
    close (pd.Series): Series of 'close's
    swing_length (int): Swing window length, as the old centred window.
        Default: 5
    offset (int): Periods to offset. Default: 0

Returns:
    pd.DataFrame: BOS_BULL, BOS_BEAR, HIGHER_HIGH, LOWER_LOW
"""
