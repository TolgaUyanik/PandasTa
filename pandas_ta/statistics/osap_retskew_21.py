# -*- coding: utf-8 -*-
"""Skewness of daily returns (21) -- Open Source Asset Pricing (Chen &
Zimmermann) SignalDoc's `ReturnSkew` (Bali-Engle-Murray 2016, OSAP t 4.01):
the sample skewness of a stock's daily simple returns, measured over a
trailing window. OSAP's own signal is monthly-updated on a monthly lookback;
this port, like GTJA191 Alpha #166 (the same statistic over 20 days), works
on the daily bars this fork has and fixes the window at 21 trading days
(~1 month), per issue #36. OSAP's reference code is GPL-2.0 and is
DELIBERATELY NOT consulted -- this is ported from the statistic's textbook
definition (the Fisher-Pearson adjusted/"sample" skewness coefficient, the
same bias-corrected `g1` formula already shipped by this repo's own
`statistics.skew` for price, applied here to returns instead of price), not
from OSAP's R/SAS implementation.

CALCULATION.  `r[t] = close[t] / close[t-1] - 1` (plain simple return, a
ratio, dimensionless). Over a trailing `length`-bar window ending at, and
including, bar `t`:

    skew(r) = n/((n-1)(n-2)) * sum((r_i - mean(r))^3) / s^3,  n = length,
              s = sample std of the window (ddof=1)

which is exactly `pandas.Series.rolling(length).skew()` -- see
`docs/measure_osap_retskew_21.py` for an independent per-window loop built
from this formula, matched against the module to 1e-9.

CAUSALITY.  The rolling window only ever looks at `r[t-length+1 .. t]`;
nothing is shifted forward. `tests/test_osap_retskew_21.py` proves this both
by future-perturbation (31 offsets) and by a mutant that reads the return
series one bar ahead before rolling.

SCALE-FREE.  `r[t]` is a ratio of two closes, so cancels exactly (bit-for-bit
in binary floating point) under a power-of-two close rescale, and within
float tolerance under an arbitrary one -- the skewness of a rescaled series
built from ratios is therefore scale-free by construction, not by an added
normalisation step. Measured in the test file, not merely asserted.
"""
from pandas_ta.utils import get_offset, verify_series


def osap_retskew_21(close, length=None, offset=None, **kwargs):
    """Indicator: Skewness of Daily Returns (OSAP_RETSKEW)"""
    # Validate Arguments
    length = int(length) if length and length > 2 else 21
    close = verify_series(close, length + 1)
    offset = get_offset(offset)

    if close is None: return

    # Calculate Result
    ret = close.pct_change(fill_method=None)
    result = ret.rolling(length, min_periods=length).skew()

    # Offset
    if offset != 0:
        result = result.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        result.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        result.fillna(method=kwargs["fill_method"], inplace=True)

    # Name & Category
    result.name = f"OSAP_RETSKEW_{length}"
    result.category = "statistics"

    return result


osap_retskew_21.__doc__ = \
"""Skewness of Daily Returns (OSAP_RETSKEW)

Open Source Asset Pricing (Chen & Zimmermann) SignalDoc's `ReturnSkew`
(Bali-Engle-Murray 2016, OSAP t 4.01): the sample skewness of a stock's daily
simple returns over a trailing window, fixed at 21 trading days (~1 month)
per issue #36 -- the same statistic GTJA191 Alpha #166 takes over 20 days.
Ported from the statistic's textbook definition (the Fisher-Pearson
bias-corrected skewness coefficient, the same formula this repo's own
`statistics.skew` already ships for price), never from OSAP's GPL-2.0
reference code.

Calculation:
    Default Inputs:
        length=21
    RET = close.pct_change()
    OSAP_RETSKEW = RET.rolling(length).skew()

Args:
    close (pd.Series): Series of 'close's
    length (int): Rolling window, in trading days. Default: 21
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.Series: OSAP_RETSKEW_{length}, a scale-free (ratio-based) skewness
        column. NaN until `length` consecutive returns are available.
"""
