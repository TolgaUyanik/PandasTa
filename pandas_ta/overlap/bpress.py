# -*- coding: utf-8 -*-
import numpy as np
from pandas_ta.overlap.linreg import linreg
from pandas_ta.utils import get_offset, verify_series


def bpress(close, length=None, offset=None, **kwargs):
    """Indicator: Bubble Pressure (BPRESS)"""
    # Validate Arguments
    # Explicit ValueError on a bad `length`, not a silent fallback to the
    # default -- an earlier port in this batch quietly swallowed a NaN/inf
    # `length` into "use the default", masking a caller bug (hard-won
    # lesson, see docstring in tests/test_bpress.py).
    if length is not None:
        if not np.isfinite(length):
            raise ValueError(f"length must be finite, got {length}")
        if length <= 0:
            raise ValueError(f"length must be positive, got {length}")
        length = int(length)
    else:
        length = 500
    close = verify_series(close, length)
    offset = get_offset(offset)
    if close is None: return

    if (close <= 0).any():
        raise ValueError(
            "close must be strictly positive for a log-price indicator "
            "(math.log of a non-positive price is undefined)"
        )

    # Calculate Result
    #
    # Pine: trend = ta.linreg(math.log(close), 500, 0)
    #       bubblePressure = math.log(close) - trend
    #
    # ta.linreg(src, length, offset=0) fits an OLS line over the trailing
    # `length` bars (INCLUDING the current bar) and evaluates that line AT
    # the current bar -- i.e. the regression's fitted value at the most
    # recent (rightmost) x in the window. This is causal: the fit at bar T
    # only uses bars [T-length+1, T].
    #
    # pandas_ta's own `linreg()` parameterizes the window as x = [1..length]
    # (x=length == the current/rightmost bar) but its DEFAULT return value
    # (tsf=False) is `m * (length - 1) + b` -- the fit evaluated at
    # x = length - 1, i.e. ONE BAR BEHIND the current bar. This was verified
    # empirically against a from-scratch numpy.polyfit reference (see
    # tests/test_bpress.py::test_pandas_ta_linreg_tsf_matches_current_bar_fit):
    # the tsf=False default disagreed with the true current-bar fit by up to
    # ~0.66 on a synthetic random-walk fixture, while tsf=True matched it to
    # 1e-13. So `tsf=True` is the ONLY kwarg combination that reproduces
    # Pine's `ta.linreg(..., offset=0)` semantics -- passing no kwargs (the
    # "obvious" reading of the function name) would have silently shipped a
    # one-bar-stale trend line. Do not "simplify" this back to the default.
    log_close = np.log(close)
    trend = linreg(log_close, length=length, tsf=True)
    bpress = log_close - trend

    # Offset
    if offset != 0:
        bpress = bpress.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        bpress.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        bpress.fillna(method=kwargs["fill_method"], inplace=True)

    # Name and Categorize it
    bpress.name = f"BPRESS_{length}"
    bpress.category = "overlap"

    return bpress


bpress.__doc__ = \
"""Bubble Pressure (BPRESS)

Ports ONLY the `bubblePressure` sub-component of the TradingView community
indicator "Bitcoin Critical State Indicator (BCSI)" by BorisTheBlade687
(https://www.tradingview.com/script/RiUxCPkj/). BCSI is a 7-component
weighted composite (growthScore, accelScore, pressureScore,
compressionScore, cycleScore, entropyScore, stressScore) rescaled to a
0-100 "regime" gauge. Only `bubblePressure` (component 3 of 7, the raw
pre-normalization value feeding `pressureScore`) was ported.

Deliberately LEFT OUT, and why:
    - The final BCSI composite, its hard-coded normalize() bounds
      (e.g. growth in [-50, 500], compression in [0.5, 3.0]) and the
      0-100 rescale: every bound is a magic constant eyeballed against
      BTC's own multi-year price history, meaningless for an arbitrary
      ticker.
    - cycleScore: a wall-clock modulo against the BTC genesis timestamp
      (2009-01-03) via `cycleLength` (default 1460 days, "the Bitcoin
      halving cycle"). This is calendar-position, not price-derived, and
      is specific to BTC's own 4-year cycle narrative -- meaningless
      off-BTC.
    - growthScore / accelScore / compressionScore / entropyScore /
      stressScore: each is fed through the same BTC-tuned normalize()
      bounds above; none is a clean, scale-free, portable primitive on
      its own the way bubblePressure is.
    - The regime bucket (CAPITULATION/ACCUMULATION/EXPANSION/BUBBLE/
      CRITICAL) is a thresholding of the BTC-tuned composite and inherits
      all of the above.

Source Pine (RiUxCPkj.pine, lines 45-53):
    trend = ta.linreg(math.log(close), 500, 0)
    bubblePressure = math.log(close) - trend
    pressureScore = normalize(bubblePressure, -1.0, 1.0)   # NOT ported --
        BTC-tuned bound; bubblePressure itself is already scale-free (see
        Scale-invariance below), a hard-coded [-1, 1] clip is not needed
        for a generic ML feature.

Calculation:
    Default Inputs:
        length=500
    LOG = natural log
    LINREG = rolling causal linear-regression fit, evaluated at the
        current (rightmost) bar of the trailing window -- pandas_ta's
        own `linreg(..., tsf=True)`, NOT its bare default (see the
        in-source comment in bpress.py for why tsf=True is required to
        match Pine's ta.linreg(..., offset=0)).

    trend = LINREG(LOG(close), length)
    BPRESS = LOG(close) - trend

Scale-invariance (this is a log-space RESIDUAL, not a raw price level, so
it is scale-free by construction -- verified, not merely asserted):
    Let close' = k * close for any constant k > 0 (e.g. a different
    ticker's price magnitude, or a currency redenomination).
        log(close') = log(close) + log(k)
    A rolling OLS fit is linear in its inputs, so adding the CONSTANT
    log(k) to every value in the fitting window shifts the fitted line by
    exactly that same constant at every x, including the evaluation point:
        LINREG(log(close) + log(k), length) = LINREG(log(close), length) + log(k)
    Therefore:
        BPRESS(close') = [log(close) + log(k)] - [trend(close) + log(k)]
                        = log(close) - trend(close) = BPRESS(close)
    i.e. BPRESS is invariant under any constant multiplicative rescaling
    of price -- comparable across tickers of very different price
    magnitude without any further normalization. Tested directly (not
    just documented) in tests/test_bpress.py::test_scale_invariance.

Args:
    close (pd.Series): Series of 'close's. Must be strictly positive
        (log of a non-positive price is undefined) -- raises ValueError
        otherwise.
    length (int): Regression window length. Default: 500. Must be a
        finite positive int -- raises ValueError otherwise.
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.Series: New feature generated. Name: BPRESS_{length}
"""
