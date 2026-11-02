# -*- coding: utf-8 -*-
from pandas_ta.utils import get_offset, verify_series


def lot_zeroret_60(close, length=None, offset=None, **kwargs):
    """Indicator: Share of Zero-Return Days (LOT_ZERORET)"""
    # Validate Arguments
    length = int(length) if length and length > 0 else 60
    close = verify_series(close, length + 1)
    offset = get_offset(offset)

    if close is None: return

    # Calculate Result
    r = close.pct_change(fill_method=None)
    zero = (r == 0).astype(float)
    counts = zero.rolling(length, min_periods=length).sum()
    result = counts / length
    # `r == 0` reads False (not NaN) at a bar whose own return is undefined
    # (close[t-1] missing), so a plain rolling sum would silently count that
    # undefined bar as "not zero" instead of excluding it. Masking on the
    # window's earliest return (r shifted length-1 bars) delays the first
    # valid bar until all `length` returns inside the window are defined.
    result = result.where(r.shift(length - 1).notna())

    # Offset
    if offset != 0:
        result = result.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        result.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        result.fillna(method=kwargs["fill_method"], inplace=True)

    # Name & Category
    result.name = f"LOT_ZERORET_{length}"
    result.category = "statistics"

    return result


lot_zeroret_60.__doc__ = \
"""Share of Zero-Return Days (LOT_ZERORET)

Share of zero-return days, as asked for by issue #39: Lesmond, Ogden &
Trzcinka (1999, RFS) use the proportion of zero daily returns over a
trailing window as a liquidity proxy; the issue frames OSAP's `zerotrade`
(zero-*volume* days, US t-stat 4.40 at 12 months) as the volume-side
analogue and uses zero *returns* instead because this fork's harness drops
zero-volume bars as flat bars before an indicator ever sees them
(`docs/issues/screen/ind_screen.py` candidate `lot_zeroret_60`). The issue
states the formula itself, verbatim: `count(r == 0, 60)/60` -- there is no
separate primary-source formula to derive, unlike `osap_mrrev` #37 or
`osap_voltrend_60` #38, where the issue only gave a plain-language
restatement. Neither the Lesmond-Ogden-Trzcinka paper nor OSAP's GPL-2.0
`zerotrade` code is consulted or available in this worktree (`docs/pine/`
and web access are unavailable); this is ported from the issue's own stated
formula, not from either paper's or OSAP's code.

Calculation:
    Default Inputs:
        length=60
    r             = close.pct_change()
    LOT_ZERORET   = count(r == 0, length) / length

Args:
    close (pd.Series): Series of 'close's
    length (int): The rolling window. Default: 60
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.Series: LOT_ZERORET_{length}, a scale-free (dimensionless) share in
        [0, 1]. NaN until `length` consecutive returns are available (the
        first `length` bars, since one extra bar of history is needed to
        compute the first return).
"""
