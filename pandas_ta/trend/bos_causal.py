# -*- coding: utf-8 -*-
import numpy as np
from pandas import DataFrame
from pandas_ta.utils import get_offset, verify_series


def _confirm(vals, length, is_high):
    """Bool array: True at bar t = j + k when bar j is a swing, i.e. exactly when it becomes known.

    With k = (length - 1) // 2 and left = length - 1 - k, bar j is a swing high iff
    vals[j] == max(vals[j-left .. j+k]) and no later bar in (j, j+k] ties it (rightmost
    tie wins, the rule of `swing_equilibrium._confirm_pivots`); lows use min.
    """
    k = (length - 1) // 2
    left = length - 1 - k
    n = len(vals)
    out = np.zeros(n, dtype=bool)
    for t in range(length - 1, n):
        j = t - k
        w = vals[j - left: t + 1]
        if np.all(np.isnan(w)):
            continue
        ext = np.nanmax(w) if is_high else np.nanmin(w)
        if vals[j] == ext and not np.any(vals[j + 1: t + 1] == ext):
            out[t] = True
    return out


def bos_causal(high, low, close, swing_length=None, offset=None, **kwargs):
    """Indicator: Causal Break of Structure / Change of Character (BOSC)"""
    # Validate Arguments
    swing_length = int(swing_length) if swing_length and swing_length > 0 else 5
    high = verify_series(high, swing_length)
    low = verify_series(low, swing_length)
    close = verify_series(close, swing_length)
    offset = get_offset(offset)

    if high is None or low is None or close is None: return

    H = high.to_numpy(dtype=float)
    L = low.to_numpy(dtype=float)
    C = close.to_numpy(dtype=float)
    n = len(C)

    k = (swing_length - 1) // 2
    sh = _confirm(H, swing_length, True)
    sl = _confirm(L, swing_length, False)

    bos_bull = np.zeros(n)
    bos_bear = np.zeros(n)
    higher_high = np.zeros(n)
    lower_low = np.zeros(n)
    choch_bull = np.zeros(n)
    choch_bear = np.zeros(n)

    last_sh = last_sl = np.nan
    trend = 0  # 0 neutral, 1 up, -1 down
    for t in range(n):
        if sh[t]:
            v = H[t - k]
            if not np.isnan(last_sh):
                if v > last_sh: higher_high[t] = 1
                if v < last_sh: trend = -1
            last_sh = v
        if sl[t]:
            v = L[t - k]
            if not np.isnan(last_sl):
                if v < last_sl: lower_low[t] = 1
                if v > last_sl: trend = 1
            last_sl = v

        if not np.isnan(last_sh) and C[t] > last_sh: bos_bull[t] = 1
        if not np.isnan(last_sl) and C[t] < last_sl: bos_bear[t] = 1

        if bos_bull[t] == 1 and trend == -1:
            choch_bull[t] = 1
            trend = 0
        if bos_bear[t] == 1 and trend == 1:
            choch_bear[t] = 1
            trend = 0

    p = f"_{swing_length}"
    df = DataFrame({
        f"BOSC_BULL{p}": bos_bull,
        f"BOSC_BEAR{p}": bos_bear,
        f"BOSC_HH{p}": higher_high,
        f"BOSC_LL{p}": lower_low,
        f"BOSC_CHOCH_BULL{p}": choch_bull,
        f"BOSC_CHOCH_BEAR{p}": choch_bear,
    }, index=close.index)

    df.name = f"BOSC{p}"
    df.category = "trend"

    if offset != 0:
        df = df.shift(offset)

    if "fillna" in kwargs:
        df.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        df.fillna(method=kwargs["fill_method"], inplace=True)

    return df


bos_causal.__doc__ = \
"""Causal Break of Structure / Change of Character (bos_causal)

`bos` and `choch` with the look-ahead removed (issue #332). Both flag swings
with `rolling(swing_length, center=True)`, so a swing is used
`(swing_length - 1) // 2` bars before it can be known. Here a swing is
registered only on the bar where its right-hand bars have printed.

Sources:
    This repo: `pandas_ta/trend/bos.py`, `choch.py` (centred-window form) and
    `swing_equilibrium._confirm_pivots` (the causal confirmation rule, MIT).
    ICT / Smart Money Concept.

Calculation:
    Default Inputs:
        swing_length=5
    k = (swing_length - 1) // 2, left = swing_length - 1 - k
    swing high at j is known at t = j + k iff
        high[j] == max(high[j-left .. j+k]) and high[i] != high[j] for i in (j, j+k]
        (rightmost tie wins, so a double top confirms exactly one swing)
    swing low: same with min / low.
    HH = 1 at t = j + k when that swing high exceeds the previous one
    LL = 1 at t = j + k when that swing low is below the previous one
    BULL = 1 when close[t] > last swing high confirmed at or before t
    BEAR = 1 when close[t] < last swing low confirmed at or before t
    CHOCH_BULL = BULL while the swing trend is down (the latest trend event was a
        lower swing high); CHOCH_BEAR = BEAR while it is up (a higher swing low);
        either resets the trend to neutral.

Args:
    high, low, close (pd.Series)
    swing_length (int): Swing window. Default: 5
    offset (int): Periods to offset. Default: 0

Returns:
    pd.DataFrame: BOSC_BULL_<n>, BOSC_BEAR_<n>, BOSC_HH_<n>, BOSC_LL_<n>,
    BOSC_CHOCH_BULL_<n>, BOSC_CHOCH_BEAR_<n> (0/1 flags, scale-free)
"""
