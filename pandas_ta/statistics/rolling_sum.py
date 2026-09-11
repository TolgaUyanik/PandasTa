# -*- coding: utf-8 -*-
from pandas_ta.utils import get_offset, verify_series


def rolling_sum(close, length=None, offset=None, **kwargs):
    """Indicator: Rolling Sum (SUM)"""
    # Validate Arguments
    length = int(length) if length and length > 0 else 10
    min_periods = int(kwargs["min_periods"]) if "min_periods" in kwargs \
        and kwargs["min_periods"] is not None else length
    close = verify_series(close, max(length, min_periods))
    offset = get_offset(offset)

    if close is None: return

    # Calculate Result
    rolling_sum = close.rolling(length, min_periods=min_periods).sum()

    # Offset
    if offset != 0:
        rolling_sum = rolling_sum.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        rolling_sum.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        rolling_sum.fillna(method=kwargs["fill_method"], inplace=True)

    # Name & Category
    rolling_sum.name = f"SUM_{length}"
    rolling_sum.category = "statistics"

    return rolling_sum


rolling_sum.__doc__ = \
"""Rolling Sum (SUM)

The sliding sum of the last `length` values.

Named `rolling_sum`, not `sum`: a module-level `sum` would shadow the Python
builtin for anything doing `from pandas_ta import *`, and this package already
carries a guard test for a related shadowing class
(`test_no_module_shadows_a_function_name_anywhere_in_the_package`). The emitted
COLUMN is `SUM_<length>`, so the name a mined rule matches on is unaffected.

⚠ **Not scale-free.** A rolling sum of prices scales with price, so it is a
`PX`-shaped column and is not usable as a model feature on its own — see
`docs/MLCompanionContract.md`. It is shipped because it is a building block
(and because Pine's `ta.sum` exists), not because it is a feature. Fed a
already-scale-free series — returns, a bounded oscillator, a binary flag — the
output is usable; a sum of a binary flag is a rolling event count, which is.

Calculation:
    Default Inputs:
        length=10
    SUM = close.rolling(length).sum()

Args:
    close (pd.Series): Series of 'close's
    length (int): It's period. Default: 10
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    min_periods (int, optional): Minimum number of observations. Default: length
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.Series: New feature generated.
"""
