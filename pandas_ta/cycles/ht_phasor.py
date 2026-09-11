# -*- coding: utf-8 -*-
"""Hilbert Transform - Phasor Components. Port of TA-Lib's `HT_PHASOR`.

TA-Lib is BSD-2-Clause, (c) 1999-2007 Mario Fortier; algorithm by John Ehlers
(*Rocket Science for Traders*, Wiley 2001). Reference implementation:
`ta-lib/src/ta_func/ta_HT_PHASOR.c`. Shared machinery and numeric pins:
`pandas_ta/cycles/_hilbert.py`. Nothing imports `talib`.

GATE D -- WHY THE SHIPPED COLUMNS ARE NOT TA-LIB'S

TA-Lib emits the in-phase and quadrature components as DETRENDED PRICE
AMPLITUDES: they carry the units of `close` and scale linearly with it. A tree
cannot compare such a column with `close`, so the raw pair is not a feature.
What ships by default is the pair divided by `close` and expressed in percent,
which is scale-free. The raw pair is still available under `raw=True`, the way
`tvstop` keeps its deleted `TVS_DIST` reachable for measurement.
"""
import numpy as np
from pandas import DataFrame

from pandas_ta.cycles._hilbert import LOOKBACK_32, _WARMUP_32, blank_lookback, ht_state
from pandas_ta.utils import get_offset, verify_series


def ht_phasor(close, offset=None, **kwargs):
    """Indicator: Hilbert Transform Phasor Components (HT_PHASOR)"""
    close = verify_series(close)
    offset = get_offset(offset)
    if close is None: return
    raw = bool(kwargs.pop("raw", False))

    px = close.to_numpy(dtype=float)
    state = ht_state(px, _WARMUP_32)
    ip = blank_lookback(state["inphase"], LOOKBACK_32)
    qd = blank_lookback(state["quadrature"], LOOKBACK_32)

    with np.errstate(divide="ignore", invalid="ignore"):
        denom = np.where(px == 0.0, np.nan, px)
        ip_pct = 100.0 * ip / denom
        qd_pct = 100.0 * qd / denom

    data = {"HT_PHASOR_IP": ip_pct, "HT_PHASOR_Q": qd_pct}
    if raw:
        data["HT_PHASOR_IP_RAW"] = ip
        data["HT_PHASOR_Q_RAW"] = qd

    df = DataFrame(data, index=close.index)

    if offset != 0:
        df = df.shift(offset)

    if "fillna" in kwargs:
        df.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        df.fillna(method=kwargs["fill_method"], inplace=True)

    df.name = "HT_PHASOR"
    df.category = "cycles"
    return df


ht_phasor.__doc__ = \
"""Hilbert Transform - Phasor Components (HT_PHASOR)

The in-phase and quadrature components of the Hilbert-transform analytic
signal built on the detrended, smoothed price. Together they are the rotating
vector whose angular rate is the dominant cycle frequency.

Sources:
    TA-Lib `ta_HT_PHASOR.c` (BSD-2-Clause)
    John Ehlers, Rocket Science for Traders (Wiley, 2001)

Calculation:
    See `pandas_ta/cycles/_hilbert.py`. Warm-up 12 bars, TA-Lib lookback 32.
    HT_PHASOR_IP = 100 * inphase / close
    HT_PHASOR_Q  = 100 * quadrature / close

Args:
    close (pd.Series): Series of 'close's
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    raw (bool): Also emit TA-Lib's unnormalised `*_RAW` columns. These carry
        price units and are NOT ML features; they exist so Gate A can be
        re-measured against `talib`. Default: False
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.DataFrame: HT_PHASOR_IP, HT_PHASOR_Q (percent of close, scale-free);
        plus HT_PHASOR_IP_RAW, HT_PHASOR_Q_RAW when raw=True.
"""
