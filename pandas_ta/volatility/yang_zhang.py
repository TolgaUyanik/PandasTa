# -*- coding: utf-8 -*-
import numpy as np
from pandas import Series

from pandas_ta.utils import get_offset, verify_series


def _valid_ohlc(open_: Series, high: Series, low: Series, close: Series) -> Series:
    """A bar is usable if all four prices are positive and high/low actually
    bound open/close. See `rogers_satchell`'s docstring for why that keeps
    the per-bar Rogers-Satchell term below non-negative."""
    return ((open_ > 0) & (high > 0) & (low > 0) & (close > 0)
            & (high >= open_) & (high >= close) & (low <= open_) & (low <= close))


def yang_zhang(open_, high, low, close, length=None, offset=None, **kwargs):
    """Indicator: Yang-Zhang Range Volatility (YZVOL)"""
    # Validate Arguments. k below needs length > 1 (division by length-1);
    # a caller-supplied 1 or 0 falls back to the default rather than raising,
    # matching this repo's other length guards (e.g. `gapm`, `corwin_schultz`).
    length = int(length) if length and length > 1 else 20
    open_ = verify_series(open_, length + 1)
    high = verify_series(high, length + 1)
    low = verify_series(low, length + 1)
    close = verify_series(close, length + 1)
    offset = get_offset(offset)

    if open_ is None or high is None or low is None or close is None: return

    valid = _valid_ohlc(open_, high, low, close)

    # Overnight (close-to-open) and open-to-close log returns. The overnight
    # term is why #14's open-quality risk applies here (Quantpedia: a free
    # data feed's `open` is often unreliable) -- see docs/RangeVolMeasured.md
    # for what was measured about it on synthetic data; real-data quality is
    # owed, same as #14 itself.
    prev_close = close.shift(1)
    overnight_valid = valid & prev_close.notna() & (prev_close > 0)
    with np.errstate(divide="ignore", invalid="ignore"):
        overnight = Series(np.where(overnight_valid, np.log(open_ / prev_close), np.nan), index=close.index)
        openclose = Series(np.where(valid, np.log(close / open_), np.nan), index=close.index)
        rs_per_bar = Series(np.where(
            valid, np.log(high / close) * np.log(high / open_) + np.log(low / close) * np.log(low / open_),
            np.nan), index=close.index)

    v_overnight = overnight.rolling(length).var(ddof=1)
    v_openclose = openclose.rolling(length).var(ddof=1)
    v_rs = rs_per_bar.rolling(length).mean()

    # Yang & Zhang's own bias-correction weight, balancing the (unbiased but
    # noisier) open-to-close term against the (biased but less noisy)
    # Rogers-Satchell term. Needs length > 1, guarded above.
    k = 0.34 / (1.34 + (length + 1) / (length - 1))
    variance = (v_overnight + k * v_openclose + (1 - k) * v_rs).clip(lower=0.0)
    yz = np.sqrt(variance) * 100

    # Offset
    if offset != 0:
        yz = yz.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        yz.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        method = kwargs["fill_method"]
        if method in ("ffill", "pad"):
            yz = yz.ffill()
        elif method in ("bfill", "backfill"):
            yz = yz.bfill()
        else:  # a silent back-fill on a typo would be a look-ahead
            raise ValueError(f"fill_method must be ffill/pad or bfill/backfill, not {method!r}")

    # Name and Categorize it
    yz.name = f"YZVOL_{length}"
    yz.category = "volatility"

    return yz


yang_zhang.__doc__ = \
"""Yang-Zhang Range Volatility (YZVOL)

A range-based volatility estimator that adds the OVERNIGHT (close-to-open)
jump to Rogers-Satchell, so it uses the full OHLC bar AND the gap at the
open -- the issue's "adds the overnight jump" framing. Combines three
variance terms over a rolling window of `length` bars: the sample variance
of the overnight log return, the sample variance of the open-to-close log
return, and the mean Rogers-Satchell per-bar term, weighted by Yang & Zhang's
own bias-correction `k`. Reported as a rolling RMS volatility, in percent,
matching `har_park`'s `park_pct` convention (not annualised).

Sources: Kissell, "The Science of Algorithmic Trading and Portfolio
Management" (2013), ch. 13, Isichenko, "Quantitative Portfolio Management"
(2021), ch. 2, and the original Yang, D. and Zhang, Q. (2000), "Drift
Independent Volatility Estimation Based on High, Low, Open, and Close
Prices", Journal of Business 73(3). None of the three were available on
this machine; the formula below is the one commonly reproduced from Yang &
Zhang's own paper and is not checked against Kissell's or Isichenko's
chapters line by line.

Because this estimator reads `open`, Quantpedia's open-quality warning from
issue #14 applies: a free OHLC feed's `open` is often unreliable (e.g.
`open == prior close` on many bars, which this port measures on SYNTHETIC
data only -- docs/RangeVolMeasured.md; real-data quality is owed, same as #14).

Already scale-free: every term is a log-ratio of prices (including the
overnight term, `open / prior close`), so a uniform price rescaling leaves
it bit-identical (x8/x64) or changes it only by floating-point rounding
(x10/x3.7). See docs/RangeVolMeasured.md.

Calculation:
    Default Inputs:
        length=20
    valid = open>0 and high>0 and low>0 and close>0
            and high >= max(open, close) and low <= min(open, close)
    overnight  = LN(open / close[1])                  (NaN if close[1] invalid)
    openclose  = LN(close / open)
    rs_per_bar = LN(high/close)*LN(high/open) + LN(low/close)*LN(low/open)
    k = 0.34 / (1.34 + (length+1)/(length-1))
    variance = VAR(overnight, length) + k*VAR(openclose, length) + (1-k)*MEAN(rs_per_bar, length)
               (sample variance, ddof=1; clipped >= 0, float-safety)
    YZVOL = 100 * SQRT(variance)

Args:
    open_ (pd.Series): Series of 'open's
    high (pd.Series): Series of 'high's
    low (pd.Series): Series of 'low's
    close (pd.Series): Series of 'close's
    length (int): Rolling window; must be > 1 (a caller-supplied 0 or 1
        falls back to the default). Default: 20
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): 'ffill'/'pad' or 'bfill'/'backfill'

Returns:
    pd.Series: YZVOL_{length}, percent, >= 0.
"""
