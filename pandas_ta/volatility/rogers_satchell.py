# -*- coding: utf-8 -*-
import numpy as np
from pandas import Series

from pandas_ta.utils import get_offset, verify_series


def _valid_ohlc(open_: Series, high: Series, low: Series, close: Series) -> Series:
    """A bar is usable if all four prices are positive and high/low actually
    bound open/close. Under that constraint `ln(high/close)`, `ln(high/open)`
    are both >= 0 and `ln(low/close)`, `ln(low/open)` are both <= 0, so each
    product term below is non-negative -- see module docstring."""
    return ((open_ > 0) & (high > 0) & (low > 0) & (close > 0)
            & (high >= open_) & (high >= close) & (low <= open_) & (low <= close))


def rogers_satchell(open_, high, low, close, length=None, offset=None, **kwargs):
    """Indicator: Rogers-Satchell Range Volatility (RSVOL)"""
    # Validate Arguments
    length = int(length) if length and length > 0 else 20
    open_ = verify_series(open_, length)
    high = verify_series(high, length)
    low = verify_series(low, length)
    close = verify_series(close, length)
    offset = get_offset(offset)

    if open_ is None or high is None or low is None or close is None: return

    # Per-bar variance term, drift-independent by construction (Rogers &
    # Satchell 1991): unlike Garman-Klass, it does not assume the bar's drift
    # (open-to-close move) is zero-mean, which is what "drift-independent"
    # means here. `high >= max(open, close)` and `low <= min(open, close)`
    # make `ln(high/close)*ln(high/open) >= 0` and
    # `ln(low/close)*ln(low/open) >= 0` individually, so the sum is ALWAYS
    # >= 0 on valid data -- no clip needed (the clip below is float-safety
    # only, see test). A malformed bar is masked to NaN, not trusted.
    valid = _valid_ohlc(open_, high, low, close)
    with np.errstate(divide="ignore", invalid="ignore"):
        per_bar = np.log(high / close) * np.log(high / open_) + np.log(low / close) * np.log(low / open_)
    per_bar = Series(np.where(valid, per_bar, np.nan), index=close.index)

    variance = per_bar.rolling(length).mean().clip(lower=0.0)
    rs = np.sqrt(variance) * 100

    # Offset
    if offset != 0:
        rs = rs.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        rs.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        method = kwargs["fill_method"]
        if method in ("ffill", "pad"):
            rs = rs.ffill()
        elif method in ("bfill", "backfill"):
            rs = rs.bfill()
        else:  # a silent back-fill on a typo would be a look-ahead
            raise ValueError(f"fill_method must be ffill/pad or bfill/backfill, not {method!r}")

    # Name and Categorize it
    rs.name = f"RSVOL_{length}"
    rs.category = "volatility"

    return rs


rogers_satchell.__doc__ = \
"""Rogers-Satchell Range Volatility (RSVOL)

A range-based volatility estimator using the full OHLC bar, DRIFT-INDEPENDENT
by construction (unlike Garman-Klass, it does not assume the bar's own
open-to-close move has zero mean) -- the issue's own framing for why this one
is included alongside Garman-Klass. Reported as a rolling RMS volatility, in
percent, over `length` bars, matching `har_park`'s `park_pct` convention
(not annualised).

Sources: Aldridge, "High-Frequency Trading" (2010), ch. 8 and ch. 10, and
the original Rogers, L.C.G. and Satchell, S.E. (1991), "Estimating Variance
From High, Low and Closing Prices", Annals of Applied Probability 1(4).
Neither source was available on this machine; the formula below is the one
commonly reproduced from Rogers & Satchell's own paper and is not checked
against Aldridge's chapters line by line.

Already scale-free: every term is a log-ratio of two of the bar's own
prices, so a uniform price rescaling leaves it bit-identical (x8/x64) or
changes it only by floating-point rounding (x10/x3.7). See
docs/RangeVolMeasured.md.

Calculation:
    Default Inputs:
        length=20
    valid = open>0 and high>0 and low>0 and close>0
            and high >= max(open, close) and low <= min(open, close)
    per_bar = LN(high/close)*LN(high/open) + LN(low/close)*LN(low/open)  (NaN if not valid)
    variance = MEAN(per_bar, length)                                     (clipped >= 0, float-safety)
    RSVOL = 100 * SQRT(variance)

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
    pd.Series: RSVOL_{length}, percent, >= 0.
"""
