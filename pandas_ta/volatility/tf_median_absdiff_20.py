# -*- coding: utf-8 -*-
from numpy import log as nplog
from pandas_ta.utils import get_offset, verify_series


def tf_median_absdiff_20(close, length=None, offset=None, **kwargs):
    """Indicator: Median Absolute Daily Log Return (MEDABSDIFF)"""
    # Validate Arguments
    length = int(length) if length and length > 0 else 20
    close = verify_series(close, length + 1)
    offset = get_offset(offset)

    if close is None: return

    # Calculate Result
    # log(close / close.shift(1)), not log(close).diff(): the ratio is scale-
    # invariant bit-for-bit under a power-of-two rescale (it is a single
    # division of two equally-rescaled floats), so the log of it is too.
    # log(close) - log(close).shift(1) is not -- the additive log(k) term
    # from each side cancels only to within a few ulp, not bit-exactly.
    logret = nplog(close / close.shift(1))
    medabsdiff = logret.abs().rolling(length).median()

    # Offset
    if offset != 0:
        medabsdiff = medabsdiff.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        medabsdiff.fillna(kwargs["fillna"], inplace=True)

    # Name & Category
    medabsdiff.name = f"MEDABSDIFF_{length}"
    medabsdiff.category = "volatility"

    return medabsdiff


tf_median_absdiff_20.__doc__ = \
"""Median Absolute Daily Log Return (MEDABSDIFF)

The rolling median of the absolute bar-to-bar log return -- a robust (outlier-
resistant) measure of realised volatility, in the same spirit as `natr` or
`true_range` but built from the median instead of a mean/EMA, so a handful of
large moves inside the window cannot drag the whole reading up the way an
average does.

Source: TSFEL (BSD-3-Clause), `features.py median_abs_diff: median(|diff(x)|)`
-- the median absolute first difference of a generic 1-D signal `x`. TSFEL is
not a dependency of this package, dev or otherwise -- its existence and
licence are cited, per issue #118 ("Library code (TSFEL, BSD-3-Clause):
existence, not evidence"), but the library itself is neither vendored nor run
as an oracle here, so Gate A is checked against an independent loop written
from the formula text, not against TSFEL's own code. Issue #118 picks the
scale-free form: `x` = log(close), so `diff(x)` is the bar-to-bar log return,
which is a ratio and therefore invariant to a constant price rescaling.

Calculation:
    Default Inputs:
        length=20
    logret = LN(close) - LN(close)[1]     (the bar-to-bar log return)
    MEDABSDIFF = MEDIAN(ABS(logret), length)   (trailing rolling median)

Args:
    close (pd.Series): Series of 'close's
    length (int): Rolling window width in bars. Default: 20
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)

Returns:
    pd.Series: MEDABSDIFF_{length}, non-negative.
"""
