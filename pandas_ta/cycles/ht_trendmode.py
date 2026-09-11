# -*- coding: utf-8 -*-
"""Hilbert Transform - Trend vs Cycle Mode. Port of TA-Lib's `HT_TRENDMODE`.

TA-Lib is BSD-2-Clause, (c) 1999-2007 Mario Fortier; algorithm by John Ehlers
(*Rocket Science for Traders*, Wiley 2001). Reference implementation:
`ta-lib/src/ta_func/ta_HT_TRENDMODE.c`. Shared machinery, the 37-bar warm-up
and the numeric pins: `pandas_ta/cycles/_hilbert.py`. Nothing imports `talib`.

TA-Lib returns an INTEGER here (0 = cycle mode, 1 = trend mode). This port
returns float64 0.0/1.0, because a pandas integer column cannot carry the NaN
that the 63-bar lookback requires and the fork does not publish a bar TA-Lib
withholds. The values on the bars TA-Lib does publish are equal, not close:
max|diff| 0 over 27,928 bars.
"""
from pandas import Series

from pandas_ta.cycles._hilbert import LOOKBACK_63, _WARMUP_63, blank_lookback, ht_state
from pandas_ta.utils import get_offset, verify_series


def ht_trendmode(close, offset=None, **kwargs):
    """Indicator: Hilbert Transform Trend vs Cycle Mode (HT_TRENDMODE)"""
    close = verify_series(close)
    offset = get_offset(offset)
    if close is None: return

    state = ht_state(close.to_numpy(dtype=float), _WARMUP_63)
    out = Series(blank_lookback(state["trendmode"], LOOKBACK_63),
                 index=close.index, dtype=float)

    if offset != 0:
        out = out.shift(offset)

    if "fillna" in kwargs:
        out.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        out.fillna(method=kwargs["fill_method"], inplace=True)

    out.name = "HT_TRENDMODE"
    out.category = "cycles"
    return out


ht_trendmode.__doc__ = \
"""Hilbert Transform - Trend vs Cycle Mode (HT_TRENDMODE)

1 when the market is judged to be trending, 0 when it is judged to be cycling.
Four tests, in TA-Lib's order: a SineWave crossing resets the trend counter to
zero; fewer than half a dominant cycle since that reset is cycle mode; a phase
advancing at close to the dominant-cycle rate is cycle mode; and, overriding
all three, a smoothed price more than 1.5% away from the instantaneous
trendline is trend mode.

Sources:
    TA-Lib `ta_HT_TRENDMODE.c` (BSD-2-Clause)
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
    pd.Series: HT_TRENDMODE column, 0.0 or 1.0. A binary state -- scale-free,
        an ML feature as shipped.
"""
