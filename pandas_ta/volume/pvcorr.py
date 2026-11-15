# -*- coding: utf-8 -*-
"""Price-Volume Correlation (PVCORR). RAG-scan round-2, 2026-10-22 (issue #18).

Sources: Kissell 2013 ch. 7, Kaufman 2013 ch. 12 ("Volume, Open Interest..."),
Alpha Architect, *Using Trading Volume to Optimize Portfolio Construction and
Implementation*. None of them define a single reference formula; all three
describe the same question -- do moves happen on rising or falling
participation -- not one computable function. No line-by-line source citation
is possible, unlike a Pine port.

GATE A -- THE VARIANT PICKED, AND WHY

qlib's Alpha158 ships the closest concrete oracle, `CORD`:
`Corr($close/Ref($close,1), Log($volume/Ref($volume,1)+1), d)` -- the bar
return against `log(V[t]/V[t-1] + 1)`. This port keeps the return half
exactly and changes the volume half for one reason: zero-volume bars.

`log(V[t]/V[t-1] + 1)` divides by `V[t-1]` before the `+1` ever runs, so a
halted or untraded prior bar (`V[t-1] == 0`) is a division by zero, not a
defined number -- on BIST, thin names and exchange holidays produce exactly
this. The fix keeps the same quantity (log of the volume ratio) but masks the
bar instead of dividing by zero:

    dlogv[t] = log(V[t] / V[t-1])   if V[t] > 0 and V[t-1] > 0, else NaN

A masked bar drops out of the rolling correlation's window (pandas excludes
NaN pairs), rather than injecting `inf`/`-inf` into it. This also keeps the
transform EXACTLY invariant to multiplying every `V` by a positive constant
`k`: the mask condition (`V > 0`) does not depend on `k`, and the ratio
`(kV[t])/(kV[t-1])` cancels `k` exactly in floating point when `k` is a power
of two (the same reason `pfe` and `kalman_trend` use ratios of `close`, not
differences of `log(close)`). `qlib`'s `+1` form does NOT have this property:
`log(kV[t]/(kV[t-1]) + 1)` only equals `log(V[t]/V[t-1] + 1)` when the `+1`
is negligible next to the ratio, which is not exact. See `test_scale_free`.

Decisions this port makes, each owed by the issue:
* volume transform: log RATIO of volume, masked at non-positive volume (above).
* Pearson, not Spearman: qlib's `CORR`/`CORD` family and Kissell/Kaufman's
  "correlation" are both the plain linear correlation; nothing in the sources
  asks for a rank correlation.
* window: 20 bars (one trading month), the fork's usual default for a
  rolling statistical window (`covariance` and `stdev` default to 30; this
  is a window, not a filter length, so a shorter month-scale default was
  chosen deliberately -- not measured, a Gate A judgment call).
"""
import numpy as np
from pandas import Series

from pandas_ta.utils import get_offset, verify_series
from pandas_ta.utils._pine import correlation as _rolling_pearson


def pvcorr(close, volume, length=None, offset=None, **kwargs):
    """Indicator: Price-Volume Correlation (PVCORR)"""
    # Validate Arguments
    length = int(length) if length and length > 1 else 20
    close = verify_series(close, length + 1)
    volume = verify_series(volume, length + 1)
    offset = get_offset(offset)
    if close is None or volume is None: return

    if not close.index.equals(volume.index):
        raise ValueError(
            "pvcorr: `close` and `volume` are indexed differently. A "
            "correlation read off two misaligned series is a silent "
            "nonsense number."
        )

    # Calculate Result
    ret = close.pct_change()

    vol_prev = volume.shift(1)
    valid = (volume > 0) & (vol_prev > 0)
    dlogv = Series(np.nan, index=volume.index)
    with np.errstate(divide="ignore", invalid="ignore"):
        dlogv[valid] = np.log(volume[valid] / vol_prev[valid])

    out = _rolling_pearson(ret, dlogv, length)

    # Offset
    if offset != 0:
        out = out.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        out.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        out.fillna(method=kwargs["fill_method"], inplace=True)

    # Name & Category
    out.name = f"PVCORR_{length}"
    out.category = "volume"

    return out


pvcorr.__doc__ = \
"""Price-Volume Correlation (PVCORR)

The rolling Pearson correlation between the bar return and the change in log
volume over a window: does a move happen on rising or falling participation?
Found by the ResearchIntel RAG scan of 2026-10-22, round 2 (issue #18).
Sources: Kissell (2013) ch. 7, Kaufman (2013) ch. 12, Alpha Architect's
*Using Trading Volume to Optimize Portfolio Construction and Implementation*
-- all three describe the idea, none hands over a single reference formula.

The closest concrete oracle is qlib's Alpha158 `CORD`,
`Corr(close/Ref(close,1), Log(volume/Ref(volume,1)+1), d)`. This port keeps
the return half and changes the volume half: `log(V[t]/V[t-1])`, masked to
NaN whenever `V[t]` or `V[t-1]` is not positive, instead of `log(V[t]/V[t-1]
+ 1)`. The `+1` form divides by `V[t-1]` before the `+1` ever runs, so a
halted or untraded prior bar is a division by zero rather than a defined
number. The mask also keeps the column EXACTLY invariant to a positive
rescaling of volume (the `+1` form is not): see docs/PvcorrMeasured.md.

Calculation:
    Default Inputs:
        length=20
    ret[t]   = close[t] / close[t-1] - 1
    dlogv[t] = log(volume[t] / volume[t-1])   if volume[t] > 0 and
                                                  volume[t-1] > 0, else NaN
    PVCORR   = rolling Pearson corr(ret, dlogv, length)

Args:
    close (pd.Series): Series of 'close's
    volume (pd.Series): Series of 'volume's
    length (int): The rolling window. Default: 20
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.Series: PVCORR_<length>, bounded on [-1, 1]. Scale-free by
        construction (a correlation of a return and a log-ratio), and the
        invariance is exact for both inputs -- see docs/PvcorrMeasured.md.
"""
