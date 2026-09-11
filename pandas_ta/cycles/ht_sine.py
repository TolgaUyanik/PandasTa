# -*- coding: utf-8 -*-
"""Hilbert Transform - SineWave. Port of TA-Lib's `HT_SINE`.

TA-Lib is BSD-2-Clause, (c) 1999-2007 Mario Fortier; algorithm by John Ehlers
(*Rocket Science for Traders*, Wiley 2001). Reference implementation:
`ta-lib/src/ta_func/ta_HT_SINE.c`. Shared machinery, the 37-bar warm-up this
read-out needs, and the numeric pins: `pandas_ta/cycles/_hilbert.py`. Nothing
imports `talib`.
"""
from pandas import DataFrame

from pandas_ta.cycles._hilbert import LOOKBACK_63, _WARMUP_63, blank_lookback, ht_state
from pandas_ta.utils import get_offset, verify_series


def ht_sine(close, offset=None, **kwargs):
    """Indicator: Hilbert Transform SineWave (HT_SINE)"""
    close = verify_series(close)
    offset = get_offset(offset)
    if close is None: return

    state = ht_state(close.to_numpy(dtype=float), _WARMUP_63)
    df = DataFrame({
        "HT_SINE": blank_lookback(state["sine"], LOOKBACK_63),
        "HT_LEADSINE": blank_lookback(state["leadsine"], LOOKBACK_63),
    }, index=close.index)

    if offset != 0:
        df = df.shift(offset)

    if "fillna" in kwargs:
        df.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        df.fillna(method=kwargs["fill_method"], inplace=True)

    df.name = "HT_SINE"
    df.category = "cycles"
    return df


ht_sine.__doc__ = \
"""Hilbert Transform - SineWave (HT_SINE)

`sin(DCPhase)` and `sin(DCPhase + 45 degrees)`. Ehlers' reading is that the
two lines cross ahead of a cyclic turn and wander without crossing while the
market trends, which is what `ht_trendmode` formalises.

Sources:
    TA-Lib `ta_HT_SINE.c` (BSD-2-Clause)
    John Ehlers, Rocket Science for Traders (Wiley, 2001)

Calculation:
    See `pandas_ta/cycles/_hilbert.py`. Warm-up 37 bars, TA-Lib lookback 63.

Args:
    close (pd.Series): Series of 'close's
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.DataFrame: HT_SINE, HT_LEADSINE. Both are sines of an angle, so both
        are bounded in [-1, 1] and scale-free -- ML features as shipped.
"""
