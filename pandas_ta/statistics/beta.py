# -*- coding: utf-8 -*-
"""Rolling Beta of one series against another. Port of TA-Lib's `BETA`.

TA-Lib is BSD-2-Clause, (c) 1999-2007 Mario Fortier. Reference implementation:
`ta-lib/src/ta_func/ta_BETA.c`. Nothing here imports `talib`.

WHAT TA-LIB'S BETA ACTUALLY IS

The ordinary-least-squares slope of `close`'s SIMPLE RETURNS regressed on
`other`'s simple returns over a rolling window -- TA-Lib's own header calls
`inReal0` the stock and `inReal1` the index. It is NOT a correlation and not
symmetric: swapping the two arguments changes the answer.

GATE A -- PINNED, INCLUDING WHERE IT CANNOT BE PINNED

Against `talib.BETA(high, low, 5)` over 20 daily BIST frames, 29,088 pooled
comparable bars: median |diff| 4.4e-15, p99 2.8e-13, p99.8 4.9e-12. Then it
falls off a cliff -- p99.9 is 1.03 and the maximum is 3.4e+06.

That cliff is ONE population and it is identified, not waved at. 46 bars
(0.158%) disagree by more than 1e-8, and on those bars the median
denominator `n*Sxx - Sx^2` is 1.78e-14 against 7.47e-03 on the bars that
agree -- twelve orders of magnitude. Runs of identical highs (BIST prices are
tick-rounded and go flat often) make the uncentred sum-of-squares cancel to
noise, and TA-Lib's own guard is `if (denominator == 0) output 0`, which does
not fire at 1.78e-14. On those bars BOTH implementations are returning
cancellation noise; they are not disagreeing about beta.

This port keeps TA-Lib's exact algebraic form rather than a numerically better
CENTRED one, because Gate A is agreement with TA-Lib and a centred form would
be a different indicator on precisely the bars in question. The degenerate
population is reported, not hidden, and `tests/test_talib1_ports.py` asserts
its SIZE so that a real regression cannot hide inside it.

NOT REGISTERED IN `Category`, ON PURPOSE

`beta` needs a SECOND series. `df.ta.strategy()` enumerates accessors and
would have to invent one, so `beta` is absent from `Category` and present in
`AnalysisIndicators.strategy`'s default exclusion list -- the same treatment
`up_and_down_volume` and `volume_delta` get, and for the same reason.
"""
import numpy as np
from pandas import Series

from pandas_ta.utils import get_offset, verify_series


def beta(close, other=None, length=None, offset=None, **kwargs):
    """Indicator: Rolling Beta (BETA)"""
    length = int(length) if length and length > 0 else 5
    if other is None:
        raise ValueError(
            "beta: `other` is required -- a beta against nothing is not a "
            "number. Pass the benchmark series explicitly."
        )
    close = verify_series(close, length)
    other = verify_series(other, length)
    offset = get_offset(offset)
    if close is None or other is None: return

    if not close.index.equals(other.index):
        raise ValueError(
            "beta: `close` and `other` are indexed differently. A beta read "
            "off two misaligned series is a silent nonsense number."
        )

    x = close.pct_change()
    y = other.pct_change()

    n = float(length)
    sx = x.rolling(length).sum()
    sy = y.rolling(length).sum()
    sxy = (x * y).rolling(length).sum()
    sxx = (x * x).rolling(length).sum()

    denom = n * sxx - sx * sx
    with np.errstate(divide="ignore", invalid="ignore"):
        out = (n * sxy - sx * sy) / denom.where(denom != 0.0)
    # TA-Lib emits 0.0, not a NaN, when the denominator is exactly zero.
    out = out.mask(denom == 0.0, 0.0)

    if offset != 0:
        out = out.shift(offset)

    if "fillna" in kwargs:
        out.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        out.fillna(method=kwargs["fill_method"], inplace=True)

    out.name = f"BETA_{length}"
    out.category = "statistics"
    return out


beta.__doc__ = \
"""Rolling Beta (BETA)

Sources:
    TA-Lib `ta_BETA.c` (BSD-2-Clause)

Calculation:
    Default Inputs:
        length=5
    x = close.pct_change(); y = other.pct_change()
    BETA = (n*SUM(xy) - SUM(x)*SUM(y)) / (n*SUM(x*x) - SUM(x)^2)

Args:
    close (pd.Series): the series whose beta is wanted
    other (pd.Series): the benchmark. REQUIRED.
    length (int): The window. Default: 5
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.Series: BETA_length column. A ratio of returns to returns, so it is
        dimensionless and scale-free -- an ML feature as shipped, subject to
        a benchmark being chosen.
"""
