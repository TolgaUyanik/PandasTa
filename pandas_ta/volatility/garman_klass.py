# -*- coding: utf-8 -*-
import numpy as np
from pandas import Series

from pandas_ta.utils import get_offset, verify_series


def _valid_ohlc(open_: Series, high: Series, low: Series, close: Series) -> Series:
    """A bar is usable if all four prices are positive and high/low actually
    bound open/close (`high >= max(open, close)`, `low <= min(open, close)`).
    Under that constraint `ln(high/low) >= |ln(close/open)|` always holds
    (equivalently `high/low >= max(close/open, open/close)`), which is what
    keeps the per-bar term below non-negative -- see module docstring."""
    return ((open_ > 0) & (high > 0) & (low > 0) & (close > 0)
            & (high >= open_) & (high >= close) & (low <= open_) & (low <= close))


def garman_klass(open_, high, low, close, length=None, offset=None, **kwargs):
    """Indicator: Garman-Klass Range Volatility (GKVOL)"""
    # Validate Arguments
    length = int(length) if length and length > 0 else 20
    open_ = verify_series(open_, length)
    high = verify_series(high, length)
    low = verify_series(low, length)
    close = verify_series(close, length)
    offset = get_offset(offset)

    if open_ is None or high is None or low is None or close is None: return

    # Per-bar variance term. `high >= max(open, close)` and `low <= min(open,
    # close)` together force `ln(high/low) >= |ln(close/open)|`, so this is
    # ALWAYS >= (0.5 - (2ln2-1)) * ln(close/open)^2 >= 0 -- no clip needed on
    # valid data (the clip below is float-safety only, see test). A malformed
    # bar (e.g. high < close from a bad tick) is masked to NaN rather than
    # trusted, matching `corwin_schultz`'s `_valid_bar` precedent.
    ln2 = np.log(2.0)
    valid = _valid_ohlc(open_, high, low, close)
    with np.errstate(divide="ignore", invalid="ignore"):
        per_bar = 0.5 * np.log(high / low) ** 2 - (2 * ln2 - 1) * np.log(close / open_) ** 2
    per_bar = Series(np.where(valid, per_bar, np.nan), index=close.index)

    variance = per_bar.rolling(length).mean().clip(lower=0.0)
    gk = np.sqrt(variance) * 100

    # Offset
    if offset != 0:
        gk = gk.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        gk.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        method = kwargs["fill_method"]
        if method in ("ffill", "pad"):
            gk = gk.ffill()
        elif method in ("bfill", "backfill"):
            gk = gk.bfill()
        else:  # a silent back-fill on a typo would be a look-ahead
            raise ValueError(f"fill_method must be ffill/pad or bfill/backfill, not {method!r}")

    # Name and Categorize it
    gk.name = f"GKVOL_{length}"
    gk.category = "volatility"

    return gk


garman_klass.__doc__ = \
"""Garman-Klass Range Volatility (GKVOL)

A range-based volatility estimator using the full OHLC bar, more statistically
efficient than a close-to-close standard deviation because it also uses the
bar's high/low extremes (the literature's efficiency claim -- Garman & Klass
report roughly 5x fewer observations needed for the same precision -- is NOT
independently re-measured in this port; see docs/RangeVolMeasured.md for what
WAS measured here). Reported as a rolling RMS volatility, in percent, over
`length` bars -- not annualised, matching `har_park`'s `park_pct` convention
rather than imposing a sqrt(252)-style trading-day assumption this repo's
single-asset frames cannot justify alone.

Sources: Aldridge, "High-Frequency Trading" (2010), ch. 8 and ch. 10
(discussed as a volatility estimator for execution/risk sizing), and the
original Garman, M. and Klass, M. (1980), "On the Estimation of Security
Price Volatilities from Historical Data", Journal of Business 53(1). Neither
source was available on this machine; the formula below is the one commonly
reproduced from Garman & Klass's own paper and is not checked against
Aldridge's chapters line by line.

Already scale-free: every term is `ln(high/low)` or `ln(close/open)`, a
ratio, so a uniform price rescaling leaves it bit-identical (x8/x64) or
changes it only by floating-point rounding (x10/x3.7). See
docs/RangeVolMeasured.md.

Calculation:
    Default Inputs:
        length=20
    valid = open>0 and high>0 and low>0 and close>0
            and high >= max(open, close) and low <= min(open, close)
    per_bar = 0.5*LN(high/low)^2 - (2*LN(2)-1)*LN(close/open)^2   (NaN if not valid)
    variance = MEAN(per_bar, length)                              (clipped >= 0, float-safety)
    GKVOL = 100 * SQRT(variance)

Args:
    open_ (pd.Series): Series of 'open's
    high (pd.Series): Series of 'high's
    low (pd.Series): Series of 'low's
    close (pd.Series): Series of 'close's
    length (int): Rolling window. Default: 20
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): 'ffill'/'pad' or 'bfill'/'backfill'

Returns:
    pd.Series: GKVOL_{length}, percent, >= 0.
"""
