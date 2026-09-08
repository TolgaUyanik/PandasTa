# -*- coding: utf-8 -*-
from pandas_ta.utils import get_offset, verify_series


def covariance(close, other=None, length=None, ddof=None, offset=None,
               **kwargs):
    """Indicator: Rolling Covariance (COV)"""
    # Validate Arguments
    length = int(length) if length and length > 1 else 30
    ddof = int(ddof) if ddof is not None and ddof >= 0 else 1
    if other is None:
        raise ValueError(
            "covariance: `other` is required. Returning None silently was the "
            "same class of quiet nonsense this function's alignment guard "
            "exists to prevent."
        )
    close = verify_series(close, length)
    other = verify_series(other, length)
    offset = get_offset(offset)

    if close is None or other is None: return

    # A covariance of two series read off different indices is a silent
    # nonsense number, not an error. Align first and say so.
    if not close.index.equals(other.index):
        # ... but ONLY when both indices are unique. `align(join="inner")` on a
        # duplicated index is a cartesian product: 100 rows against 97 returned
        # 194 -- longer than either input -- and the rolling covariance was
        # then computed over fabricated pairs. Measured, not hypothetical.
        if not close.index.is_unique or not other.index.is_unique:
            raise ValueError(
                "covariance: cannot align a duplicated index -- the inner join "
                "would multiply rows instead of matching them (100 x 97 -> 194 "
                "on a repeated DatetimeIndex). De-duplicate first."
            )
        close, other = close.align(other, join="inner")
        if close.size < length: return

    # Calculate Result
    covariance = close.rolling(length, min_periods=length).cov(other, ddof=ddof)

    # Offset
    if offset != 0:
        covariance = covariance.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        covariance.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        covariance.fillna(method=kwargs["fill_method"], inplace=True)

    # Name & Category
    covariance.name = f"COV_{length}_{ddof}"
    covariance.category = "statistics"

    return covariance


covariance.__doc__ = \
"""Rolling Covariance (COV)

The trailing covariance of two series over `length` bars. The two-series
counterpart of `variance`, and the unnormalised counterpart of `correlation`.

⚠ **Not scale-free, and the failure is worse than for a single-series column.**
Covariance carries the units of BOTH inputs, so on two price series it scales
with price *squared* — a covariance of 41.7 means nothing without knowing what
the two series cost. For a model feature use **`correlation`** (already shipped
in `pandas_ta.utils._pine`), which is this quantity divided by both standard
deviations and is bounded on [-1, 1]. `covariance` is shipped as a building
block and for the cases where the unnormalised magnitude is the point.

Feeding it two RETURN series rather than two price series gives a scale-free
result, and that is the intended use.

⚠ Mismatched indices are **inner-joined**, not broadcast positionally. Two
series read off different indices produce a plausible-looking number rather
than an error, which is the kind of silent defect this package's review rounds
keep finding.

Calculation:
    Default Inputs:
        length=30, ddof=1
    COV = close.rolling(length).cov(other, ddof=ddof)

Args:
    close (pd.Series): Series of 'close's
    other (pd.Series): The second series. Required.
    length (int): It's period. Default: 30
    ddof (int): Delta Degrees of Freedom. 1 is the sample covariance,
        0 the population covariance. Default: 1
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.Series: New feature generated.
"""
