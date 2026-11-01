# -*- coding: utf-8 -*-
import numpy as np

from pandas_ta.utils import get_offset, verify_series


def ie_asym(close, length=None, mult=None, offset=None, **kwargs):
    """Indicator: Return Asymmetry (IE)"""
    # Validate Arguments
    length = int(length) if length and length > 0 else 260
    mult = float(mult) if mult and mult > 0 else 2.0
    min_periods = int(kwargs["min_periods"]) if "min_periods" in kwargs and kwargs["min_periods"] is not None else length
    close = verify_series(close, max(length, min_periods) + 1)
    offset = get_offset(offset)

    if close is None: return

    # Calculate Result: within each rolling window of `length` log-returns,
    # count returns beyond mean +- mult*std (sample std, ddof=1) and take
    # (#upper_tail - #lower_tail) / length.
    r = np.log(close / close.shift(1))

    def _asym(window):
        std = window.std(ddof=1)
        if std == 0 or np.isnan(std):
            return 0.0
        mean = window.mean()
        hi = (window > mean + mult * std).sum()
        lo = (window < mean - mult * std).sum()
        return (hi - lo) / len(window)

    ie_asym = r.rolling(length, min_periods=min_periods).apply(_asym, raw=True)

    # Offset
    if offset != 0:
        ie_asym = ie_asym.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        ie_asym.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        ie_asym.fillna(method=kwargs["fill_method"], inplace=True)

    # Name & Category
    ie_asym.name = f"IEASYM_{length}_{mult}"
    ie_asym.category = "statistics"

    return ie_asym


ie_asym.__doc__ = \
"""Return Asymmetry (IE)

The empirical form of Jiang, Wu, Zhu and Chen's distribution-based return
asymmetry measure (as described in Quantpedia strategy #0664, "Return
Asymmetry Effect in Commodity Futures", and the companion Quantpedia blog
post citing Wu, Zhu and Chen (2020) on Chinese stocks): over the trailing
`length` bar-to-bar returns, count how many sit more than `mult` sample
standard deviations above the window mean, subtract how many sit more than
`mult` standard deviations below it, and divide by `length`. A high value
means more extreme up days than down days in the window ("lottery
preference"), which the sources associate with overpricing and lower
subsequent returns.

No Pine or TA-Lib source is available for this one -- it is a published
formula, not a chart script -- so Gate A is checked against an independent
loop written from the formula (see `tests/test_ie_asym.py`), the same
pattern used for `pfe` (`docs/PfeMeasured.md`), not a line-by-line source
citation.

Returns are `log(close / close.shift(1))`, not simple percent change, so the
column is exactly scale-free under a power-of-two price rescaling (the ratio
inside the log is bit-identical) and within floating-point tolerance under
any other rescaling -- see `docs/IeAsymMeasured.md`. Standard deviation is
the sample form (`ddof=1`); the source formula does not specify biased vs.
unbiased and there is no oracle to check it against.

Calculation:
    Default Inputs:
        length=260, mult=2.0
    r = LN(close / close[1])
    For each window of the last `length` values of r:
        mean = window.mean()
        std = window.std(ddof=1)
        hi = count(window > mean + mult * std)
        lo = count(window < mean - mult * std)
        IEASYM = (hi - lo) / length

Args:
    close (pd.Series): Series of 'close's
    length (int): Rolling window, in bars of return. Default: 260
    mult (float): Standard-deviation multiplier for the tail threshold. Default: 2.0
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    min_periods (int, optional): Minimum periods to compute. Default: length
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.Series: New feature generated, scale-free, in roughly [-1, 1] but in
        practice much narrower (see docs/IeAsymMeasured.md for measured
        fire rates and value spread).
"""
