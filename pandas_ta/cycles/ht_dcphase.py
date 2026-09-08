# -*- coding: utf-8 -*-
"""Hilbert Transform - Dominant Cycle Phase. Port of TA-Lib's `HT_DCPHASE`.

TA-Lib is BSD-2-Clause, (c) 1999-2007 Mario Fortier; algorithm by John Ehlers
(*Rocket Science for Traders*, Wiley 2001). Reference implementation:
`ta-lib/src/ta_func/ta_HT_DCPHASE.c`. Shared machinery, warm-ups and the
numeric pins: `pandas_ta/cycles/_hilbert.py`. Nothing imports `talib`.

This is one of the FOUR read-outs that need the 37-bar warm-up, not the 12-bar
one. Getting that wrong leaves the output wrong by up to 70 degrees during the
first few hundred bars and exactly right afterwards.
"""
from pandas import Series

from pandas_ta.cycles._hilbert import LOOKBACK_63, _WARMUP_63, blank_lookback, ht_state
from pandas_ta.utils import get_offset, verify_series


def ht_dcphase(close, offset=None, **kwargs):
    """Indicator: Hilbert Transform Dominant Cycle Phase (HT_DCPHASE)"""
    close = verify_series(close)
    offset = get_offset(offset)
    if close is None: return

    state = ht_state(close.to_numpy(dtype=float), _WARMUP_63)
    out = Series(blank_lookback(state["dcphase"], LOOKBACK_63),
                 index=close.index, dtype=float)

    if offset != 0:
        out = out.shift(offset)

    if "fillna" in kwargs:
        out.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        out.fillna(method=kwargs["fill_method"], inplace=True)

    out.name = "HT_DCPHASE"
    out.category = "cycles"
    return out


ht_dcphase.__doc__ = \
"""Hilbert Transform - Dominant Cycle Phase (HT_DCPHASE)

The phase, in DEGREES, of the dominant cycle: a one-bin DFT of the smoothed
price over the current dominant-cycle length, corrected for the one-bar lag of
the 4-bar weighted smoother and wrapped into (-45, 315].

Sources:
    TA-Lib `ta_HT_DCPHASE.c` (BSD-2-Clause)
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
    pd.Series: HT_DCPHASE column. An angle in degrees -- invariant under a
        rescaling of price, so it IS an ML feature as shipped.
"""
