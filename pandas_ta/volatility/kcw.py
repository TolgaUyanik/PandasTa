# -*- coding: utf-8 -*-
"""Keltner Channel Width (KCW).

PINEBI-1b port of Pine v6's core built-in ``ta.kcw``.  A CORE BUILT-IN, not a
library export, so it carries no MPL attribution -- unlike the 14 library
functions in this batch.

Gate A oracle: Pine's documented definition of ``ta.kcw``,
``(upper - lower) / basis`` over the same Keltner construction ``ta.kc`` uses.

WHY THIS IS A PORT AND NOT A `have`
-----------------------------------
PINEBI-0 first classified `kcw` as `have` on the strength of the fork already
shipping `kc`.  Review (round 4) caught it: ``pandas_ta.kc`` returns
``KCLe_``/``KCBe_``/``KCUe_`` -- three PRICE LEVELS and no width column.  The
width is the only scale-free thing in that construction, and it was the one
piece missing.  Levels are not features (``PandasTa/CLAUDE.md``, the ML feature
contract); a width ratio is.
"""
from pandas_ta.volatility.kc import kc
from pandas_ta.utils import get_offset, verify_series


def kcw(high, low, close, length=None, scalar=None, mamode=None, offset=None,
        **kwargs):
    """Indicator: Keltner Channel Width (KCW)"""
    # Validate Arguments
    length = int(length) if length and length > 0 else 20
    scalar = float(scalar) if scalar and scalar > 0 else 2.0
    mamode = mamode if isinstance(mamode, str) else "ema"
    high = verify_series(high, length)
    low = verify_series(low, length)
    close = verify_series(close, length)
    offset = get_offset(offset)

    if high is None or low is None or close is None: return

    # Calculate Result -- delegate the channel itself rather than reimplement
    # it, so `kcw` cannot drift away from `kc` (the FVGENG lesson: do not add
    # a second copy of a loop, import the function).
    bands = kc(high=high, low=low, close=close, length=length, scalar=scalar,
               mamode=mamode, **kwargs)
    if bands is None: return

    lower, basis, upper = (bands.iloc[:, 0], bands.iloc[:, 1],
                           bands.iloc[:, 2])
    kcw = (upper - lower) / basis

    # Offset
    if offset != 0:
        kcw = kcw.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        kcw.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        kcw.fillna(method=kwargs["fill_method"], inplace=True)

    # Name and Categorize it
    # Mirrors `kc`'s own suffix so the parameter set is readable off the name;
    # naming is API (CLAUDE.md) and a mined rule matches on this string.
    kcw.name = f"KCW{mamode[0]}_{length}_{scalar}"
    kcw.category = "volatility"

    return kcw


kcw.__doc__ = """Keltner Channel Width (KCW)

The Keltner channel's width as a fraction of its own basis --
`(upper - lower) / basis`.  Pine ships this as a core built-in, `ta.kcw`,
alongside `ta.kc`; this fork shipped the channel and not the width.

Unlike the three `kc` columns, which are price levels and therefore unusable
as ML features, the width is scale-free: multiply every price by k and the
ratio is unchanged.  It measures the same thing Bollinger bandwidth does but
off an ATR envelope rather than a standard deviation, so it does not collapse
in the same places.

Sources:
    Pine Script v6 built-in `ta.kcw`

Calculation:
    Default Inputs:
        length=20, scalar=2.0, mamode="ema"

    KC = kc(high, low, close, length, scalar, mamode)
    KCW = (KC.upper - KC.lower) / KC.basis

Args:
    high (pd.Series): Series of 'high's
    low (pd.Series): Series of 'low's
    close (pd.Series): Series of 'close's
    length (int): The channel period. Default: 20
    scalar (float): ATR multiplier. Default: 2.0
    mamode (str): See ```help(ta.ma)```. Default: 'ema'
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.Series: New feature generated.
"""
