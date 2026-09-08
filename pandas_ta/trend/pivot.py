# -*- coding: utf-8 -*-
from pandas import DataFrame

from pandas_ta.utils import get_offset, verify_series
from pandas_ta.utils._pine import pivot_point_levels


def pivot(high, low, close, anchor=None, kind="Traditional", offset=None,
          **kwargs):
    """Indicator: Pivot Point Distances (PIVOT)"""
    # Validate Arguments
    high = verify_series(high)
    low = verify_series(low)
    close = verify_series(close)
    offset = get_offset(offset)

    if high is None or low is None or close is None: return

    levels = pivot_point_levels(high=high, low=low, close=close, anchor=anchor,
                                kind=kind)
    if levels is None or levels.empty: return

    # Calculate Result -- DISTANCES, never the levels themselves. An `R2` of
    # 41.72 is unusable as a feature: a tree cannot compare it to a close that
    # was 12 two years ago. `(close - level) / close` is the same information
    # in a form that survives a split, a re-listing and a change of ticker.
    data = {}
    for name in levels.columns:
        data[f"PIVOT_{name}_DIST_PCT"] = (close - levels[name]) / close

    pivot = DataFrame(data, index=close.index)

    # Offset
    if offset != 0:
        pivot = pivot.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        pivot.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        pivot.fillna(method=kwargs["fill_method"], inplace=True)

    # Name & Category
    pivot.name = "PIVOT"
    pivot.category = "trend"

    return pivot


pivot.__doc__ = \
"""Pivot Point Distances (PIVOT)

Where price sits relative to each of the eleven Traditional pivot levels, as a
signed fraction of price: `(close - level) / close`. Positive means price is
ABOVE that level.

**This is the scale-free companion to `pivot_point_levels`, not a duplicate of
it.** That function returns the eleven levels as raw prices — `PP`, `R1`-`R5`,
`S1`-`S5` — which are `PX`-shaped and therefore dead as model features: a tree
cannot compare `R2 = 41.72` to a close that was 12 two years ago, and the
comparison it needs (`close > R2`) is a relation trees cannot read off two
separate columns. Emitting the distance pre-computes that relation and makes
its SIGN the feature. This is the `ichimoku_ml` precedent, which turned five
price lines into eight scale-free causal columns.

Eleven columns: `PIVOT_PP_DIST_PCT`, `PIVOT_R1_DIST_PCT` … `PIVOT_S5_DIST_PCT`.

**Causal**, inherited from `pivot_point_levels`: levels for the period starting
at an anchor bar are priced from the COMPLETED previous period, so nothing
reads forward. `tests/test_pinebi_1e_utilities.py::test_pivot_is_causal_with_a_mutant` pins
that rather than trusting the inheritance — by perturbing every bar from J
onward and asserting nothing before J moves. Note what that test also
established: for anchor-sparse output like this, prefix truncation and
endpoint rescanning BOTH score 0.0 against a real back-dating mutant and
certify nothing.

⚠ Only `kind="Traditional"` exists, because that is all `pivot_point_levels`
implements; the others raise rather than silently substituting.

⚠ `anchor` defaults to a change of calendar month on a DatetimeIndex and
RAISES on any other index rather than guessing a period.

No TradingView provenance and no MPL attribution: Pine's `ta.pivot_point_levels`
is a built-in with no published source, and the distance form is this fork's
own choice, not a port of anything.

Calculation:
    levels = pivot_point_levels(high, low, close, anchor, kind)
    PIVOT_<level>_DIST_PCT = (close - levels[<level>]) / close

Args:
    high (pd.Series): Series of 'high's
    low (pd.Series): Series of 'low's
    close (pd.Series): Series of 'close's
    anchor (pd.Series): Boolean Series marking the first bar of each period.
        Default: a change of calendar month on a DatetimeIndex.
    kind (str): Pivot type. Only "Traditional". Default: "Traditional"
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.DataFrame: 11 columns, one signed distance per pivot level.
"""
