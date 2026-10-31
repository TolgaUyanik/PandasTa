# -*- coding: utf-8 -*-
from numpy import sign as npsign
from pandas import DataFrame, Series
from pandas_ta.momentum.rsi import rsi
from pandas_ta.utils import get_offset, verify_series


def _signed_streak(close):
    """Signed count of consecutive up (or down) closes: +1, +2, +3, ... on a
    run of higher closes, -1, -2, -3, ... on a run of lower closes, 0 on an
    unchanged close (or the series' first bar, which has no prior close to
    compare against). Causal: bar t only reads close[t] and streak[t-1]."""
    direction = npsign(close.diff().fillna(0.0).to_numpy())
    streak = [0.0] * len(direction)
    for i in range(1, len(direction)):
        d, prev = direction[i], streak[i - 1]
        if d > 0:
            streak[i] = prev + 1.0 if prev > 0 else 1.0
        elif d < 0:
            streak[i] = prev - 1.0 if prev < 0 else -1.0
        # d == 0: stays 0.0, the close round-tripped
    return Series(streak, index=close.index)


def crsi(close, streak_length=None, offset=None, **kwargs):
    """Indicator: Connors RSI streak term (CRSI)"""
    # Validate Arguments
    streak_length = int(streak_length) if streak_length and streak_length > 0 else 2
    close = verify_series(close, streak_length + 1)
    offset = get_offset(offset)

    if close is None: return

    # Calculate Result
    streak = _signed_streak(close)
    streak_rsi = rsi(streak, length=streak_length)

    _props = f"_{streak_length}"
    df = DataFrame({
        f"CRSI_STREAK{_props}": streak_rsi,
    }, index=close.index)

    # Offset
    if offset != 0:
        df = df.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        df.fillna(kwargs["fillna"], inplace=True)

    # Name and Categorize it
    df.name = f"CRSI_STREAK{_props}"
    df.category = "momentum"

    return df


crsi.__doc__ = \
"""Connors RSI streak term (CRSI)

Connors Research's composite momentum oscillator (Kaufman 2013, ch. 9
"Momentum and Oscillators") is the average of three [0, 100] terms --
Wilder's RSI of the close, Wilder's RSI of the signed up/down streak, and
the percent rank of the 1-bar return over a trailing window:

    CRSI = ( RSI(close, 3) + RSI(streak, 2) + PercentRank(close.pct_change(1), 100) ) / 3

Gate E (`docs/CrsiMeasured.md`) measured the full composite's `CRSI_3_2_100`
and `PercentRank`'s `CRSI_PCTRANK_100` STRUCK against the engine's own
`log_return` (pooled |rho| 0.9265 / 0.9717, both >= the 0.90 revert line on
100% of 89 frames) -- both are reverted. Only the streak term ships, at
DISCLOSE_GAP (pooled |rho| 0.8362 vs `increasing`).

`streak` is the signed run length of consecutive higher (or lower) closes --
+1, +2, +3, ... on a rally, -1, -2, -3, ... on a decline, 0 on an unchanged
close. `RSI(streak, streak_length)` feeds that series through the ordinary
Wilder RSI formula (`pandas_ta.momentum.rsi`), not a different smoothing.

See docs/CrsiMeasured.md for the Gate A-F numbers.

Sources:
    Kaufman, P. (2013). Trading Systems and Methods, ch. 9.

Calculation:
    Default Inputs:
        streak_length=2

Args:
    close (pd.Series): Series of 'close's
    streak_length (int): RSI(streak) period. Default: 2
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)

Returns:
    pd.DataFrame: CRSI_STREAK_2
"""
