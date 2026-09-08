# -*- coding: utf-8 -*-
"""`supertrend2` -- the TradingView `ta` library's alternate SuperTrend.

Source: `docs/pine/RA2vGpkA-ta.pine` (untracked; see CLAUDE.md), the
TradingView/`ta` Pine v5 library, **MPL-2.0, (c) TradingView**.
`export supertrend2` is at L602-625; it is `supertrend()` (L570-593) with
`ta.atr()` swapped for `atr2()`.  The band and direction block, verbatim:

    L613 lowerBand := lowerBand > prevLowerBand or  lowPrice[1] < prevLowerBand ? lowerBand : prevLowerBand
    L614 upperBand := upperBand < prevUpperBand or highPrice[1] > prevUpperBand ? upperBand : prevUpperBand
    L616 if na(atr[1])
    L617     direction := 1
    L618 else if prevSuperTrend == prevUpperBand
    L619     direction := highPrice > upperBand ? -1 : 1
    L620 else
    L621     direction := lowPrice < lowerBand ? 1 : -1
    L622 superTrend := direction == -1 ? lowerBand : upperBand

DIRECTION SIGN IS OPPOSITE TO `supertrend` -- DO NOT ASSUME

Pine's convention here is `-1 = uptrend` (the stop is the LOWER band) and
`+1 = downtrend`.  `pandas_ta.supertrend` uses the opposite: `dir_ = 1`
when `close` breaks the upper band.  So `SUPERT2d_*` tracks the NEGATION of
`SUPERTd_*` -- measured agreement 96.75% of 400 bars on GRID_S; it is not
100% because the two also disagree on the band ratchet (Pine re-arms a band
on `price[1]` breaking the PREVIOUS band, `supertrend` on `close[i]`
breaking `band[i-1]`).  Treating `SUPERT2d` as a copy of `SUPERTd` would
invert every rule that reads it.

THE DIFFERENCES FROM `supertrend`, MEASURED (docs/PineAlternatesMeasured.md)

1. WARM-UP.  `supertrend` calls `atr(...)` (default `mamode="rma"`,
   `min_periods=length` over a true range that NaNs bar 0), so its bands --
   and its trend line -- are NaN until index `length`.  `atr2` is finite
   from bar 0, so `supertrend2` emits a line from bar 0.  Measured at
   length=7: first-stable index 7 vs 0, **7 bars saved**, on GRID_S and on
   all 40 Grid A tickers.  Note `SUPERT_*` reports a FINITE bar 0 -- the
   loop pre-fills `trend` with 0 and never overwrites index 0 -- so the
   honest measure is the index after the LAST NaN, not the first finite
   one.
2. PARAMETER REACH -- THREE (round 1 claimed two and shipped one of them):
   a. `supertrend` does `length = int(length)`; `atrLength` here may be a
      per-bar Series.
   b. `wicks`.  Pine's L607-608 pick `high`/`low` instead of `close` on
      both sides of the reversal test.  `pandas_ta.supertrend` has no such
      argument and tests `close` only; there is no keyword that reaches the
      wick behaviour.
   c. THE FACTOR, per bar.  L602 declares BOTH `factor` and `atrLength`
      `series float`.  Round 1 ported only `atrLength` and left the factor
      guarded by `float(multiplier) if multiplier and multiplier > 0`, which
      raises `ValueError: The truth value of a Series is ambiguous` on a
      Series -- reproducing in this module's own body the failure it records
      against the sibling.  Both are now per-bar capable, and the factor
      carries NO floor because Pine puts none on it.
"""
import numpy as np
from pandas import DataFrame

from pandas_ta.overlap.ema2 import _param_array
from pandas_ta.overlap.hl2 import hl2
from pandas_ta.utils import get_offset, verify_series
from pandas_ta.volatility.atr2 import atr2


def supertrend2(high, low, close, length=None, multiplier=None, wicks=None,
                offset=None, **kwargs):
    """Indicator: TradingView Alternate SuperTrend (SUPERT2)"""
    high = verify_series(high)
    low = verify_series(low)
    close = verify_series(close)
    offset = get_offset(offset)
    if high is None or low is None or close is None: return

    wicks = bool(wicks)
    if length is None:
        length = 7

    _atr = atr2(high, low, close, length=length)
    ltoken = _atr.name.split("_", 1)[1]

    # L602 declares BOTH parameters `series float`: `supertrend2(series float
    # factor, series float atrLength, ...)`. Round 1 ported only `atrLength`
    # and validated the factor with `float(multiplier) if multiplier and
    # multiplier > 0` -- which raises `ValueError: The truth value of a Series
    # is ambiguous` on a per-bar factor, the very failure this module's own
    # parameter-reach measurement records against `supertrend`. It is now the
    # same normalisation as the length, with NO floor, because Pine puts none
    # on the factor.
    mult, mtoken = _param_array(multiplier, close.index, 3.0, as_float=True)
    matr = mult * _atr.to_numpy(dtype=float)

    src = hl2(high, low).to_numpy(dtype=float)
    ub = src + matr
    lb = src - matr
    hp = (high if wicks else close).to_numpy(dtype=float)
    lp = (low if wicks else close).to_numpy(dtype=float)
    atr_v = _atr.to_numpy(dtype=float)

    m = close.size
    direction = np.full(m, np.nan)
    trend = np.full(m, np.nan)
    long_ = np.full(m, np.nan)
    short_ = np.full(m, np.nan)

    for i in range(m):
        # nz(lowerBand[1]) / nz(upperBand[1]) -- Pine's nz() of a na history
        # is 0.0, and on bar 0 that is exactly what L613/L614 see.
        prev_lb = 0.0 if i == 0 or np.isnan(lb[i - 1]) else lb[i - 1]
        prev_ub = 0.0 if i == 0 or np.isnan(ub[i - 1]) else ub[i - 1]
        prev_hp = np.nan if i == 0 else hp[i - 1]
        prev_lp = np.nan if i == 0 else lp[i - 1]

        if not (lb[i] > prev_lb or (not np.isnan(prev_lp) and prev_lp < prev_lb)):
            lb[i] = prev_lb
        if not (ub[i] < prev_ub or (not np.isnan(prev_hp) and prev_hp > prev_ub)):
            ub[i] = prev_ub

        prev_st = np.nan if i == 0 else trend[i - 1]
        prev_atr = np.nan if i == 0 else atr_v[i - 1]

        if np.isnan(prev_atr):
            d = 1.0
        elif prev_st == prev_ub:
            d = -1.0 if hp[i] > ub[i] else 1.0
        else:
            d = 1.0 if lp[i] < lb[i] else -1.0

        direction[i] = d
        trend[i] = lb[i] if d == -1 else ub[i]
        if d == -1:
            long_[i] = lb[i]
        else:
            short_[i] = ub[i]

    _props = f"_{ltoken}_{mtoken}{'w' if wicks else ''}"
    df = DataFrame({
        f"SUPERT2{_props}": trend,
        f"SUPERT2d{_props}": direction,
        f"SUPERT2l{_props}": long_,
        f"SUPERT2s{_props}": short_,
    }, index=close.index)
    df.name = f"SUPERT2{_props}"
    df.category = "overlap"

    if offset != 0:
        df = df.shift(offset)
    if "fillna" in kwargs:
        df.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        df.fillna(method=kwargs["fill_method"], inplace=True)

    return df


supertrend2.__doc__ = \
"""TradingView Alternate SuperTrend (SUPERT2)

SUPERT2d is -1 in an UPTREND and +1 in a downtrend -- the NEGATION of
`SUPERTd`, whose sign is the opposite. TradingView `ta.supertrend2()`:
SuperTrend over `atr2`, so the ATR length and the factor may both vary bar by
bar and the line is finite from bar 0. Adds `wicks`, which tests `high`/`low`
instead of `close` for the reversal; `pandas_ta.supertrend` has no equivalent.

The polarity sentence is FIRST on purpose: `docs/IndicatorDictionary.md`
truncates this description at 150 characters, and CLAUDE.md tells a reader to
consult that file before judging a column. A sign note that only exists below
the fold does not reach the person who needs it. `halftrend` does the same.

Sources:
    TradingView `ta` library (RA2vGpkA), L602-625. MPL-2.0, (c) TradingView.

Calculation:
    Default Inputs:
        length=7, multiplier=3.0, wicks=False
    atr        = ATR2(high, low, close, length) * multiplier   (both per-bar capable)
    upperBand  = hl2 + atr, ratcheted down while price has not broken it
    lowerBand  = hl2 - atr, ratcheted up while price has not broken it
    SUPERT2    = direction == -1 ? lowerBand : upperBand

Args:
    high (pd.Series): Series of 'high's
    low (pd.Series): Series of 'low's
    close (pd.Series): Series of 'close's
    length (int | float | pd.Series): ATR period; a Series gives a per-bar
        length. Default: 7
    multiplier (float | pd.Series): ATR multiplier; a Series gives Pine's
        per-bar `factor` (L602). No floor -- Pine puts none on it, so 0 and
        negatives pass through. Default: 3.0
    wicks (bool): Test high/low rather than close on reversal. Default: False
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.DataFrame: SUPERT2 (line), SUPERT2d (direction), SUPERT2l (long),
    SUPERT2s (short) columns.
"""
