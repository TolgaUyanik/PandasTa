# -*- coding: utf-8 -*-
from pandas_ta.utils import get_offset, verify_series


def normalize(close, length=None, offset=None, **kwargs):
    """Indicator: Rolling Min-Max Normalisation (NORM)"""
    # Validate Arguments
    if length is not None and int(length) < 2:
        raise ValueError(
            f"normalize: length must be >= 2, got {length}. A 1-bar window has "
            f"no range, so every output would be NaN -- silently promoting it "
            f"to 14 hides a caller's mistake."
        )
    length = int(length) if length and length > 1 else 14
    close = verify_series(close, length)
    offset = get_offset(offset)

    if close is None: return

    # Calculate Result -- TRAILING window. A whole-series min/max would leak
    # the future into every bar, which is the single defect this package's
    # causality gate exists to catch.
    window = close.rolling(length, min_periods=length)
    lowest, highest = window.min(), window.max()
    spread = highest - lowest

    # A flat window has NO position within a range, so it emits NaN. 0.5 was
    # tried and rejected on measurement, not taste: on a tick-rounded 2,000-bar
    # walk (0.1 tick, sigma=0.02) it planted a synthetic value on 17.7% of
    # settled bars, sitting at the exact centre of the feature's distribution
    # and indistinguishable from a genuine mid-range reading. A gap is
    # information a model can handle; a fabricated observation is not.
    normalize = (close - lowest) / spread.where(spread != 0)
    normalize[lowest.isna()] = float("nan")

    # Offset
    if offset != 0:
        normalize = normalize.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        normalize.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        normalize.fillna(method=kwargs["fill_method"], inplace=True)

    # Name & Category
    normalize.name = f"NORM_{length}"
    normalize.category = "statistics"

    return normalize


normalize.__doc__ = \
"""Rolling Min-Max Normalisation (NORM)

Where the current value sits inside its own trailing range, on [0, 1]. 0 is the
window low, 1 the window high.

**Causal by construction.** The window is trailing (`rolling`), never
whole-series. A whole-series min-max is the classic look-ahead leak: it tells
bar 5 what the maximum of bar 900 was. This package's Gate B exists for exactly
that class of defect and `tests/test_pinebi_1e_utilities.py::test_normalize_is_causal_with_a_mutant`
pins it with a mutant.

**Scale-free by construction**, which is what makes this useful: it converts a
`PX`-shaped column (a price, a moving average) into a bounded feature a tree
can compare across tickers and across eras. That is the same job
`ml_dist_pct` does by a different route — see `docs/MLCompanionContract.md`.

A flat window (`high == low`) returns **NaN**, not 0 and not 0.5. With no range
there is no position within it. 0.5 was implemented first and removed on
measurement: on a tick-rounded 2,000-bar walk (0.1 tick, sigma=0.02) it planted
a synthetic reading on **17.7%** of settled bars, at the exact centre of the
feature's distribution and indistinguishable from a real mid-range value. On
the illiquid BIST names that already show tick-degenerate behaviour it would be
worse. A gap a model can handle; a fabricated observation it cannot.

Calculation:
    Default Inputs:
        length=14
    lowest  = close.rolling(length).min()
    highest = close.rolling(length).max()
    NORM    = (close - lowest) / (highest - lowest)

Args:
    close (pd.Series): Series of 'close's
    length (int): It's period. Default: 14
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.Series: New feature generated.
"""
