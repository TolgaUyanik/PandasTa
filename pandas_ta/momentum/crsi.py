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


def _percent_rank(series, length):
    """Pine's `ta.percentrank`: 100 * (count of the PREVIOUS `length` values
    strictly less than the current one) / length. Ties do not count, so a
    flat run of `length` + 1 equal values reads 0, not 50. Causal: the
    rolling window ends at the current bar and reads nothing past it."""
    def _rank(window):
        return 100.0 * (window[:-1] < window[-1]).sum() / length
    return series.rolling(length + 1).apply(_rank, raw=True)


def crsi(close, rsi_length=None, streak_length=None, pctrank_length=None, offset=None, **kwargs):
    """Indicator: Connors RSI (CRSI)"""
    # Validate Arguments
    rsi_length = int(rsi_length) if rsi_length and rsi_length > 0 else 3
    streak_length = int(streak_length) if streak_length and streak_length > 0 else 2
    pctrank_length = int(pctrank_length) if pctrank_length and pctrank_length > 0 else 100
    close = verify_series(close, max(rsi_length, streak_length, pctrank_length) + 1)
    offset = get_offset(offset)

    if close is None: return

    # Calculate Result
    close_rsi = rsi(close, length=rsi_length)
    streak = _signed_streak(close)
    streak_rsi = rsi(streak, length=streak_length)
    pct_rank = _percent_rank(close.pct_change(1), pctrank_length)

    composite = Series(
        (close_rsi.to_numpy() + streak_rsi.to_numpy() + pct_rank.to_numpy()) / 3.0,
        index=close.index,
    )

    _props = f"_{rsi_length}_{streak_length}_{pctrank_length}"
    df = DataFrame({
        f"CRSI{_props}": composite,
        f"CRSI_STREAK_{streak_length}": streak_rsi,
        f"CRSI_PCTRANK_{pctrank_length}": pct_rank,
    }, index=close.index)

    # Offset
    if offset != 0:
        df = df.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        df.fillna(kwargs["fillna"], inplace=True)

    # Name and Categorize it
    df.name = f"CRSI{_props}"
    df.category = "momentum"

    return df


crsi.__doc__ = \
"""Connors RSI (CRSI)

Connors Research's composite momentum oscillator (Kaufman 2013, ch. 9
"Momentum and Oscillators"): the average of three [0, 100] terms --
Wilder's RSI of the close, Wilder's RSI of the signed up/down streak, and
the percent rank of the 1-bar return over a trailing window.

    CRSI = ( RSI(close, rsi_length)
           + RSI(streak, streak_length)
           + PercentRank(close.pct_change(1), pctrank_length) ) / 3

`streak` is the signed run length of consecutive higher (or lower) closes --
+1, +2, +3, ... on a rally, -1, -2, -3, ... on a decline, 0 on an unchanged
close. `RSI(streak, streak_length)` feeds that series through the ordinary
Wilder RSI formula (`pandas_ta.momentum.rsi`), not a different smoothing.

`PercentRank(x, n)` is Pine's `ta.percentrank`: 100 * (count of the previous
`n` values strictly less than the current one) / n -- ties do not count.

`RSI(close, rsi_length)` is NOT shipped as its own column here: at the
default `rsi_length=3` it is exactly `ta.rsi(close, 3)`, already available
from the shipped `rsi` indicator, so shipping it again would be a redundant
column (CLAUDE.md's non-redundant rule). It is still computed internally
for the composite.

See docs/CrsiMeasured.md for the Gate A-F numbers, including whether the
composite and/or the streak/percent-rank components clear Gate E.

Sources:
    Kaufman, P. (2013). Trading Systems and Methods, ch. 9.

Calculation:
    Default Inputs:
        rsi_length=3, streak_length=2, pctrank_length=100

Args:
    close (pd.Series): Series of 'close's
    rsi_length (int): RSI(close) period. Default: 3
    streak_length (int): RSI(streak) period. Default: 2
    pctrank_length (int): PercentRank lookback. Default: 100
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)

Returns:
    pd.DataFrame: CRSI_3_2_100 (composite), CRSI_STREAK_2, CRSI_PCTRANK_100
"""
