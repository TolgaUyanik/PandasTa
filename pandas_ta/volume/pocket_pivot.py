# -*- coding: utf-8 -*-
from pandas import DataFrame

from pandas_ta.overlap.sma import sma
from pandas_ta.utils import get_offset, verify_series


def pocket_pivot(close, open_, high, low, volume, length=None, max_offset_pct=None,
                  lookback=None, offset=None, **kwargs):
    """Indicator: Pocket Pivot (Kacher/Morales) (PPIVOT)"""
    # Validate Arguments
    length = int(length) if length and length > 0 else 10
    max_offset_pct = float(max_offset_pct) if max_offset_pct and max_offset_pct > 0 else 4.0
    lookback = int(lookback) if lookback and lookback > 0 else 10
    close = verify_series(close, max(length, lookback) + 1)
    open_ = verify_series(open_, max(length, lookback) + 1)
    high = verify_series(high, max(length, lookback) + 1)
    low = verify_series(low, max(length, lookback) + 1)
    volume = verify_series(volume, max(length, lookback) + 1)
    offset = get_offset(offset)

    if close is None or open_ is None or volume is None: return

    # A Kacher/Morales "pocket pivot": today's up-volume exceeds the LARGEST
    # down-volume day of the prior `lookback` bars (institutional
    # accumulation reading), while price is still close to its own SMA
    # (not extended -- an early-stage signal, not a breakout chaser).
    ma = sma(close, length=length)

    buy_volume = volume.where(close > open_, 0.0)
    sell_volume = volume.where(close < open_, 0.0)
    highest_sell_volume = sell_volume.shift(1).rolling(lookback).max()

    offset_pct = (close - ma).abs() / ma * 100
    price_near_ma = offset_pct <= max_offset_pct

    volume_ratio = buy_volume / highest_sell_volume.replace(0, float("nan"))
    volume_condition = buy_volume > highest_sell_volume
    pocket_pivot_flag = (volume_condition & price_near_ma).astype(int)

    # Offset
    if offset != 0:
        pocket_pivot_flag = pocket_pivot_flag.shift(offset)
        volume_ratio = volume_ratio.shift(offset)
        offset_pct = offset_pct.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        pocket_pivot_flag.fillna(kwargs["fillna"], inplace=True)
        volume_ratio.fillna(kwargs["fillna"], inplace=True)
        offset_pct.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        pocket_pivot_flag.fillna(method=kwargs["fill_method"], inplace=True)
        volume_ratio.fillna(method=kwargs["fill_method"], inplace=True)
        offset_pct.fillna(method=kwargs["fill_method"], inplace=True)

    _props = f"_{length}_{lookback}"
    pocket_pivot_flag.name = f"PPIVOT{_props}"
    volume_ratio.name = f"PPIVOT_VOLRATIO{_props}"
    offset_pct.name = f"PPIVOT_MAOFFSET{_props}"

    df = DataFrame({
        pocket_pivot_flag.name: pocket_pivot_flag,
        volume_ratio.name: volume_ratio,
        offset_pct.name: offset_pct,
    })
    df.name = f"PPIVOT{_props}"
    df.category = "volume"

    return df


pocket_pivot.__doc__ = \
"""Pocket Pivot (Kacher/Morales) (PPIVOT)

A "pocket pivot" (from "Trade Like an O'Neil Disciple" by Kacher & Morales):
today's up-volume exceeds the largest down-volume day of the prior N bars
(an institutional-accumulation read, cheaper to compute than a true
buy/sell-volume split since Pine/here approximate it from candle direction)
while price is still close to its own moving average -- an EARLY-STAGE
accumulation signal, distinct from a breakout chase. `PPIVOT` is the
boolean 0/1 flag matching the source exactly; `PPIVOT_VOLRATIO` (today's
up-volume / the lookback's peak down-volume) and `PPIVOT_MAOFFSET`
(already scale-free, % distance from the MA) are added as continuous,
ML-usable companions to the boolean.

Source: TradingView community indicator "Pocket Pivot (Kacher/Morales) -
Custom" by an unattributed orphan-metadata slug (see
`datastore/source/pine_triage.csv`),
https://www.tradingview.com/script/fU5exdA3-Pocket-Pivot-Kacher-Morales-tez/
(ported into AwakenAnalytics/Backtesting TVPTA-3, 2026-08-04; MPL-2.0 per
TradingView's open-source publication convention).

Calculation:
    Default Inputs:
        length=10 (SMA period), max_offset_pct=4.0, lookback=10
    ma = SMA(close, length)
    buy_volume  = volume where close > open, else 0
    sell_volume = volume where close < open, else 0
    highest_sell_volume = MAX(sell_volume.shift(1), lookback)  (excludes
        the current bar, causal)
    PPIVOT = 1 where buy_volume > highest_sell_volume AND
             |close - ma| / ma * 100 <= max_offset_pct, else 0

Args:
    close (pd.Series): Series of 'close's
    open_ (pd.Series): Series of 'open's
    high (pd.Series): Series of 'high's (unused directly, accepted for a
        consistent OHLCV call signature)
    low (pd.Series): Series of 'low's (unused directly, see above)
    volume (pd.Series): Series of 'volume's
    length (int): SMA period. Default: 10
    max_offset_pct (float): Max % distance from the SMA to still count as
        "near". Default: 4.0
    lookback (int): Bars searched for the peak down-volume day. Default: 10
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.DataFrame: PPIVOT, PPIVOT_VOLRATIO, PPIVOT_MAOFFSET columns
        (all length_lookback-suffixed).
"""
