# -*- coding: utf-8 -*-
import numpy as np
from pandas import DataFrame
from pandas_ta.utils import get_offset, verify_series


def wavetrend(high, low, close, n1=None, n2=None, offset=None, **kwargs):
    """Indicator: WaveTrend Oscillator"""
    # Validate Arguments
    n1 = int(n1) if n1 and n1 > 0 else 10
    n2 = int(n2) if n2 and n2 > 0 else 21
    high = verify_series(high, max(n1, n2))
    low = verify_series(low, max(n1, n2))
    close = verify_series(close, max(n1, n2))
    offset = get_offset(offset)

    if high is None or low is None or close is None: return

    # WaveTrend (legacy: n1=10, n2=21)
    ap = (high + low + close) / 3
    esa = ap.ewm(span=n1, adjust=False).mean()
    d = (ap - esa).abs().ewm(span=n1, adjust=False).mean()
    ci = (ap - esa) / (0.015 * d.replace(0, np.nan))
    wt1_legacy = ci.ewm(span=n2, adjust=False).mean()
    wt2_legacy = wt1_legacy.rolling(window=4).mean()
    wt_cross = np.where(
        (wt1_legacy > wt2_legacy) & (wt1_legacy.shift(1) <= wt2_legacy.shift(1)), 1,
        np.where(
            (wt1_legacy < wt2_legacy) & (wt1_legacy.shift(1) >= wt2_legacy.shift(1)), -1, 0
        )
    )

    # WaveTrend confirmed (SMA9 → EMA11 → EMA11 → EMA11, signal SMA4)
    ap2 = ap.rolling(9).mean()
    esa2 = ap2.ewm(span=11, adjust=False).mean()
    d2 = (ap2 - esa2).abs().ewm(span=11, adjust=False).mean()
    ci2 = (ap2 - esa2) / (0.015 * d2.replace(0, np.nan))
    wt1_conf = ci2.ewm(span=11, adjust=False).mean()
    wt2_conf = wt1_conf.rolling(4).mean()

    df = DataFrame({
        "WAVETREND":        wt1_legacy,
        "WAVETREND_SIGNAL": wt2_legacy,
        "WAVETREND_CROSS":  wt_cross,
        "WT1":              wt1_conf,
        "WT2":              wt2_conf,
    }, index=close.index)

    df.name = f"WAVETREND_{n1}_{n2}"
    df.category = "momentum"

    if offset != 0:
        df = df.shift(offset)

    if "fillna" in kwargs:
        df.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        df.fillna(method=kwargs["fill_method"], inplace=True)

    return df


wavetrend.__doc__ = \
"""WaveTrend Oscillator (wavetrend)

A momentum oscillator based on exponential smoothing of the typical price
deviation.  Returns both the legacy (n1/n2) and confirmed (fixed params)
variants, plus a crossover signal.

Sources:
    AwakenAnalytics custom indicator (indicator_engine.py)
    Original: LazyBear's WaveTrend Oscillator (TradingView)

Calculation:
    Default Inputs:
        n1=10, n2=21
    ap  = (high + low + close) / 3
    esa = EMA(ap, n1)
    d   = EMA(|ap - esa|, n1)
    ci  = (ap - esa) / (0.015 * d)
    WAVETREND        = EMA(ci, n2)
    WAVETREND_SIGNAL = SMA(WAVETREND, 4)
    WAVETREND_CROSS  = crossover/crossunder signal (+1/-1/0)
    WT1 = confirmed variant (SMA9 + EMA11 chain)
    WT2 = SMA(WT1, 4)

Args:
    high (pd.Series): Series of 'high's
    low (pd.Series): Series of 'low's
    close (pd.Series): Series of 'close's
    n1 (int): Channel length. Default: 10
    n2 (int): Average length. Default: 21
    offset (int): Periods to offset. Default: 0

Returns:
    pd.DataFrame: WAVETREND, WAVETREND_SIGNAL, WAVETREND_CROSS, WT1, WT2
"""
