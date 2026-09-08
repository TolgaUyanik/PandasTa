# -*- coding: utf-8 -*-
"""Hilbert Transform - Dominant Cycle Period. Port of TA-Lib's `HT_DCPERIOD`.

TA-Lib is BSD-2-Clause, (c) 1999-2007 Mario Fortier; the algorithm is John
Ehlers' (*Rocket Science for Traders*, Wiley 2001). Reference implementation:
`ta-lib/src/ta_func/ta_HT_DCPERIOD.c`. The shared state machine, the two
warm-ups and the numeric pins live in `pandas_ta/cycles/_hilbert.py` -- read
that docstring before changing anything here. Nothing imports `talib`.
"""
import numpy as np
from pandas import Series

from pandas_ta.cycles._hilbert import LOOKBACK_32, _WARMUP_32, blank_lookback, ht_state
from pandas_ta.utils import get_offset, verify_series


def ht_dcperiod(close, offset=None, **kwargs):
    """Indicator: Hilbert Transform Dominant Cycle Period (HT_DCPERIOD)"""
    close = verify_series(close)
    offset = get_offset(offset)
    if close is None: return

    state = ht_state(close.to_numpy(dtype=float), _WARMUP_32)
    out = Series(blank_lookback(state["dcperiod"], LOOKBACK_32),
                 index=close.index, dtype=float)

    if offset != 0:
        out = out.shift(offset)

    if "fillna" in kwargs:
        out.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        out.fillna(method=kwargs["fill_method"], inplace=True)

    out.name = "HT_DCPERIOD"
    out.category = "cycles"
    return out


ht_dcperiod.__doc__ = \
"""Hilbert Transform - Dominant Cycle Period (HT_DCPERIOD)

The smoothed dominant cycle period, in BARS, of the price series, measured by
a homodyne discriminator over a Hilbert-transform quadrature pair. TA-Lib
clamps the raw period to [6, 50] bars each bar, then applies a 0.2/0.8 and a
0.33/0.67 smoother, so the output is a slow-moving number of bars in [0, 50].

Sources:
    TA-Lib `ta_HT_DCPERIOD.c` (BSD-2-Clause)
    John Ehlers, Rocket Science for Traders (Wiley, 2001)

Calculation:
    See `pandas_ta/cycles/_hilbert.py`. Warm-up 12 bars, TA-Lib lookback 32.

Args:
    close (pd.Series): Series of 'close's
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.Series: HT_DCPERIOD column. A count of bars -- invariant under a
        rescaling of price, so it IS an ML feature as shipped.
"""
