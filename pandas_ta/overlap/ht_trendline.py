# -*- coding: utf-8 -*-
"""Hilbert Transform - Instantaneous Trendline. Port of TA-Lib's `HT_TRENDLINE`.

TA-Lib is BSD-2-Clause, (c) 1999-2007 Mario Fortier; algorithm by John Ehlers
(*Rocket Science for Traders*, Wiley 2001). Reference implementation:
`ta-lib/src/ta_func/ta_HT_TRENDLINE.c`. Shared machinery, the 37-bar warm-up
and the numeric pins: `pandas_ta/cycles/_hilbert.py`. Nothing imports `talib`.

GATE D / GATE E -- THIS INDICATOR SHIPS NO FEATURE. READ THIS FIRST.

`HT_TRENDLINE` is a PRICE LEVEL: a 4-3-2-1 weighted average of the last four
dominant-cycle-length means of price. It scales one-for-one with `close`, so a
tree cannot compare it with anything, exactly as `pandas_ta/trend/pivot.py`
says of its levels. The scale-free companion `HT_TRENDLINE_DIST`
(`100 * (close/trendline - 1)`) was BUILT, WIRED, MEASURED AND DELETED:
Spearman **+0.9576 against the engine's `bias`** over 402,646 pooled daily BIST
bars, which is a revert by the Gate E rule (>= 0.90), not a disclosure.
`bias` is `close/SMA - 1` -- the same "distance from a smoothed price" shape,
computed from a different smoother -- so the duplication is structural and no
parameter change escapes it.

What is left is the RAW LEVEL, which this function now returns by default
because that is the only honest thing it has. Consequences, all deliberate:

* `ht_trendline` is NOT in `Category`, so `df.ta.strategy()` never sweeps it
  into the feature set, and it is in `AnalysisIndicators.strategy`'s default
  exclusion list so that `strategy("all")` -- which enumerates ACCESSORS --
  does not run it either.
* `df.ta.ht_trendline()` still works, and the port stays exact against
  `talib.HT_TRENDLINE` (max|diff| 0.0 over 27,928 bars), so the measurement
  stays reproducible and a future caller with a use for the level has one.
* `emit_dist=True` brings the deleted column back for re-measurement, the way
  `tvstop` keeps its deleted `TVS_DIST` reachable.
"""
import numpy as np
from pandas import DataFrame

from pandas_ta.cycles._hilbert import LOOKBACK_63, _WARMUP_63, blank_lookback, ht_state
from pandas_ta.utils import get_offset, verify_series


def ht_trendline(close, offset=None, **kwargs):
    """Indicator: Hilbert Transform Instantaneous Trendline (HT_TRENDLINE)"""
    close = verify_series(close)
    offset = get_offset(offset)
    if close is None: return
    # `raw` is accepted and ignored: the raw level is now the DEFAULT output.
    kwargs.pop("raw", None)
    emit_dist = bool(kwargs.pop("emit_dist", False))

    px = close.to_numpy(dtype=float)
    state = ht_state(px, _WARMUP_63)
    line = blank_lookback(state["trendline"], LOOKBACK_63)

    data = {"HT_TRENDLINE": line}
    if emit_dist:
        with np.errstate(divide="ignore", invalid="ignore"):
            denom = np.where(line == 0.0, np.nan, line)
            data["HT_TRENDLINE_DIST"] = 100.0 * (px / denom - 1.0)

    df = DataFrame(data, index=close.index)

    if offset != 0:
        df = df.shift(offset)

    if "fillna" in kwargs:
        df.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        df.fillna(method=kwargs["fill_method"], inplace=True)

    df.name = "HT_TRENDLINE"
    df.category = "overlap"
    return df


ht_trendline.__doc__ = \
"""Hilbert Transform - Instantaneous Trendline (HT_TRENDLINE)

Ehlers' trendline: average price over exactly one dominant cycle removes the
cycle, leaving the trend, and a 4-3-2-1 weighting of the last four such
averages removes most of the remaining ripple.

Sources:
    TA-Lib `ta_HT_TRENDLINE.c` (BSD-2-Clause)
    John Ehlers, Rocket Science for Traders (Wiley, 2001)

Calculation:
    See `pandas_ta/cycles/_hilbert.py`. Warm-up 37 bars, TA-Lib lookback 63.
    HT_TRENDLINE_DIST = 100 * (close / trendline - 1)   -- DELETED, see below

Args:
    close (pd.Series): Series of 'close's
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    emit_dist (bool): Bring back the DELETED `HT_TRENDLINE_DIST` column, for
        re-measurement only. It failed Gate E at rho +0.9576 against `bias`
        over 402,646 bars and must not be fed to a model. Default: False
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.DataFrame: HT_TRENDLINE -- a PRICE LEVEL, not an ML feature, and
        deliberately outside `Category`. Plus HT_TRENDLINE_DIST when
        emit_dist=True.
"""
