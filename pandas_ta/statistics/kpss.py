# -*- coding: utf-8 -*-
import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from pandas import Series
from pandas_ta.utils import get_offset, verify_series


def kpss(close, length=None, offset=None, **kwargs):
    """Indicator: KPSS trend-stationarity statistic (KPSS)"""
    # Validate Arguments
    length = int(length) if length and length > 2 else 100
    close = verify_series(close, length)
    offset = get_offset(offset)

    if close is None: return

    # Calculate Result
    c = close.to_numpy(dtype=float)
    win = sliding_window_view(c, length)
    t = np.arange(length) - (length - 1) / 2.0
    with np.errstate(divide="ignore", invalid="ignore"):
        # Log price relative to the window's first bar. The intercept absorbs
        # the anchor, and a ratio is exact under a power-of-two rescaling.
        x = np.log(win / win[:, :1])
        x[~np.isfinite(x)] = np.nan
        # Residuals of OLS on a constant and a linear trend (regression="ct")
        xc = x - x.mean(axis=1, keepdims=True)
        slope = (xc * t).sum(axis=1) / (t * t).sum()
        resid = xc - slope[:, None] * t
        eta = (np.cumsum(resid, axis=1) ** 2).sum(axis=1) / length ** 2
        # Newey-West long-run variance, one Bartlett lag: 2 * (1 - 1/2) = 1
        s_hat = ((resid ** 2).sum(axis=1)
                 + (resid[:, 1:] * resid[:, :-1]).sum(axis=1)) / length
        # A flat window has no residual variance; NaN, not inf.
        stat = eta / np.where(s_hat > 0, s_hat, np.nan)

    values = np.full(c.size, np.nan)
    values[length - 1:] = stat
    kpss = Series(values, index=close.index)

    # Offset
    if offset != 0:
        kpss = kpss.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        kpss.fillna(kwargs["fillna"], inplace=True)

    # Name and Categorize it
    kpss.name = f"KPSS_{length}"
    kpss.category = "statistics"

    return kpss


kpss.__doc__ = \
"""KPSS trend-stationarity statistic (KPSS)

The Kwiatkowski-Phillips-Schmidt-Shin statistic of log price over a rolling
window, under the trend-stationary null: regress log price on a constant
and a linear trend, then compare the squared partial sums of the residuals
with their long-run variance. Small values mean price wandered around a
straight line; large values mean it drifted away from one the way a random
walk does. 0.146 is the 5% critical value of the "ct" test, 0.216 the 1%.

Source: Kats tsfeatures (Meta, MIT), `get_unitroot_kpss`:
`statsmodels.tsa.stattools.kpss(x, regression="ct", nlags=1)[0]`, after
Kwiatkowski et al. (1992), J. Econometrics 54, eqs. 10-11. Kats applies it
to a whole series; the 100-bar window and log close as the input are the
choices of the 2026-10-25 screen prototype (candidate kats_kpss_100,
docs/issues/screen/ind_screen_r5.py, local to the owner's machine).
PandasTa issue #157.

Causal: bar T reads bars T - length + 1 .. T. Scale-free: log price enters
relative to the window's first bar, so a constant price factor cancels;
bit-identical under x8 and x64. A window with a NaN, zero or negative close
is NaN, and so is a flat window (zero residual variance).

Calculation:
    Default Inputs:
        length=100
    x = log(close / close[T - length + 1]) over the window
    e = residuals of OLS of x on [1, t]
    S = cumsum(e)
    eta = sum(S^2) / length^2
    s2 = (sum(e^2) + sum(e[t] * e[t-1])) / length
    KPSS = eta / s2

Args:
    close (pd.Series): Series of 'close's
    length (int): Window. Default: 100
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)

Returns:
    pd.Series: KPSS_{length}
"""
