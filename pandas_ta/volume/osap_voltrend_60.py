# -*- coding: utf-8 -*-
import numpy as np

from pandas_ta.utils import get_offset, verify_series


def osap_voltrend_60(volume, length=None, offset=None, **kwargs):
    """Indicator: OSAP Volume Trend (VOLTREND)"""
    # Validate Arguments
    length = int(length) if length and length > 0 else 60
    volume = verify_series(volume, length)
    offset = get_offset(offset)

    if volume is None: return

    # VOLTREND = OLS slope of volume on a centered time index 0..length-1,
    # over its own trailing mean. The slope of y on x does not depend on
    # where x's origin sits (shifting x by a constant leaves cov(x, y) and
    # var(x) unchanged) -- an identity, not an assumption -- so centering t
    # on zero only removes a float-precision wobble; it does not change the
    # slope value. `w` folds the whole OLS-slope formula into one fixed
    # weight vector (the issue's "slope of volume on time"): for centered
    # `t`, slope = sum(t_i * y_i) / sum(t_i^2), i.e. a plain dot product.
    t = np.arange(length, dtype=float) - (length - 1) / 2.0
    w = t / (t * t).sum()

    def _slope(window):
        return np.dot(w, window)

    slope = volume.rolling(length, min_periods=length).apply(_slope, raw=True)
    vol_mean = volume.rolling(length, min_periods=length).mean()
    with np.errstate(divide="ignore", invalid="ignore"):
        voltrend = (slope / vol_mean).replace([np.inf, -np.inf], np.nan)

    # Offset
    if offset != 0:
        voltrend = voltrend.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        voltrend.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        voltrend.fillna(method=kwargs["fill_method"], inplace=True)

    # Name and Categorize it
    voltrend.name = f"VOLTREND_{length}"
    voltrend.category = "volume"

    return voltrend


osap_voltrend_60.__doc__ = \
"""OSAP Volume Trend (VOLTREND)

Volume trend, as asked for by issue #38: the Open Source Asset Pricing
(OSAP) SignalDoc (Chen & Zimmermann) catalogues it as `VolumeTrend`
(Haugen-Baker 1996, OSAP t-stat 3.0), "monthly 60 -> daily 60" -- the
issue's own stated window conversion (no trading-days-per-month arithmetic
needed here, unlike `osap_mrrev` #37: the issue gives the daily window
number directly).

Gate A. The primary OSAP SignalDoc text and the OSAP replication code
(GPL-2.0) are NOT consulted or available in this worktree (`docs/pine/` and
web access are unavailable); per the issue, this is ported from the
catalogue's own description -- "slope of volume on time over its mean (60)"
-- not from OSAP's code. That description is implemented literally:

    1. "slope of volume on time" = the ordinary-least-squares slope of the
       trailing `length` volume bars regressed against a time index. The
       slope of y on x is invariant to x's origin (an identity: shifting x
       by a constant leaves cov(x, y) and var(x) unchanged), so a centered
       index `t = 0..length-1` minus its own mean is used -- this gives the
       same slope as any other linear time index, it only keeps the
       intermediate sums near zero.
    2. "over its mean" = divided by the trailing `length`-bar mean of the
       same volume series -- the scale-free form the issue states explicitly
       (`docs/issues/screen/candidates.csv`, candidate `osap_voltrend_60`:
       "slope / mean(V,60)"), confirmed against the prototype
       (`docs/issues/screen/ind_screen.py:800-802`,
       `sdiv(regbeta_seq(v, 60), mean(v, 60))`) for the conversion only --
       the prototype's `regbeta_seq` uses the identical centered-time OLS
       slope (`t = arange(n) - (n-1)/2`, weight `t / sum(t**2)`), read for
       the window-centering convention, not as the source of the formula
       itself (per the issue's own instruction, "Gate A starts from the
       source formula, not the prototype"). This remains unconfirmed
       against the primary SignalDoc text itself, which this worktree
       cannot reach.

Calculation:
    Default Inputs:
        length=60
    t        = arange(length) - (length - 1) / 2     (centered time index)
    w        = t / sum(t ** 2)
    slope[t] = dot(w, volume[t-length+1 : t+1])        (rolling OLS slope)
    VOLTREND = slope / rolling_mean(volume, length)

Args:
    volume (pd.Series): Series of 'volume's
    length (int): The rolling window. Default: 60
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.Series: VOLTREND_{length}, a scale-free (dimensionless) ratio of a
        volume slope to its own trailing mean -- invariant to a positive
        rescaling of volume by construction (both terms scale by the same
        factor). NaN for the first `length - 1` bars, and wherever the
        trailing mean is exactly zero.
"""
