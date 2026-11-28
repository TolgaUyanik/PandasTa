# -*- coding: utf-8 -*-
import numpy as np
from pandas import DataFrame
from pandas_ta.utils import get_offset, verify_series
from pandas_ta.trend.bos import _confirmed_swings


def choch(high, low, close, swing_length=None, offset=None, **kwargs):
    """Indicator: Change of Character (CHoCH)"""
    # Validate Arguments
    swing_length = int(swing_length) if swing_length and swing_length > 0 else 5
    high = verify_series(high, swing_length)
    low = verify_series(low, swing_length)
    close = verify_series(close, swing_length)
    offset = get_offset(offset)

    if high is None or low is None or close is None: return

    # Swings are written on the bar that confirms them (bar j + k), as in
    # `bos`, so no column reads a bar after the one it is written on.
    sh_conf, sl_conf = _confirmed_swings(high, low, swing_length)
    sh = sh_conf.to_numpy(dtype=float)
    sl = sl_conf.to_numpy(dtype=float)
    cl = close.to_numpy(dtype=float)

    n = len(close)
    bos_bull = np.zeros(n)
    bos_bear = np.zeros(n)
    last_swing_high = np.nan
    last_swing_low = np.nan

    for t in range(n):
        if not np.isnan(sh[t]):
            last_swing_high = sh[t]
        if not np.isnan(sl[t]):
            last_swing_low = sl[t]
        if not np.isnan(last_swing_high) and cl[t] > last_swing_high:
            bos_bull[t] = 1
        if not np.isnan(last_swing_low) and cl[t] < last_swing_low:
            bos_bear[t] = 1

    # CHoCH: BOS that reverses the prevailing swing trend
    choch_bull = np.zeros(n)
    choch_bear = np.zeros(n)
    trend = 0  # 0=neutral, 1=uptrend, -1=downtrend
    last_sh = np.nan
    prev_sh = np.nan
    last_sl = np.nan
    prev_sl = np.nan

    for t in range(n):
        if not np.isnan(sh[t]):
            prev_sh = last_sh
            last_sh = sh[t]
            if not np.isnan(prev_sh) and last_sh < prev_sh:
                trend = -1  # lower high -> downtrend

        if not np.isnan(sl[t]):
            prev_sl = last_sl
            last_sl = sl[t]
            if not np.isnan(prev_sl) and last_sl > prev_sl:
                trend = 1   # higher low -> uptrend

        if bos_bull[t] == 1 and trend == -1:
            choch_bull[t] = 1
            trend = 0   # character changed

        if bos_bear[t] == 1 and trend == 1:
            choch_bear[t] = 1
            trend = 0

    df = DataFrame({
        "CHoCH_BULL": choch_bull,
        "CHoCH_BEAR": choch_bear,
    }, index=close.index)

    df.name = f"CHoCH_{swing_length}"
    df.category = "trend"

    if offset != 0:
        df = df.shift(offset)

    if "fillna" in kwargs:
        df.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        df.fillna(method=kwargs["fill_method"], inplace=True)

    return df


choch.__doc__ = \
"""Change of Character (choch)

A CHoCH occurs when a Break of Structure happens in the direction
opposite to the prevailing swing trend, signalling a potential reversal.

Causal since issue #332: swings come from `bos`'s `_confirmed_swings` and
are written on the bar that confirms them, `(swing_length - 1) // 2` bars
after the pivot. Before #332 `choch` used the same centred
`rolling(swing_length, center=True)` swings as `bos` and read the same
number of bars ahead.

Sources:
    ICT / Smart Money Concept (change of character).
    Swing confirmation: this repo's `pandas_ta/trend/swing_equilibrium.py`
    `_confirm_pivots` (MIT), via `pandas_ta.trend.bos._confirmed_swings`.

Calculation:
    Default Inputs:
        swing_length=5
    Swings: as in `bos` (confirmed on bar j + k, rightmost tie wins).
    The prevailing trend is set on each confirmation bar: a lower swing
    high sets a downtrend, a higher swing low sets an uptrend.
    CHoCH_BULL = 1 when BOS_BULL fires during a downtrend
    CHoCH_BEAR = 1 when BOS_BEAR fires during an uptrend
    (either resets the trend to neutral)

Args:
    high (pd.Series): Series of 'high's
    low (pd.Series): Series of 'low's
    close (pd.Series): Series of 'close's
    swing_length (int): Swing window length, as in `bos`. Default: 5
    offset (int): Periods to offset. Default: 0

Returns:
    pd.DataFrame: CHoCH_BULL, CHoCH_BEAR
"""
