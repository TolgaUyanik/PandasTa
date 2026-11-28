# -*- coding: utf-8 -*-
"""Volume Price Confirmation Indicator (VPCI), price-normalised -- Buff
Dormeier, "Volume Price Confirmation Indicator", Technical Analysis of
Stocks & Commodities, July 2007 (and his 2007 Dow Award paper), per issue
#264. Formula as the issue states it, from the CMT Association's summary
(https://cmtassociation.org/?p=74895) and jesse's `vpci` (MIT):

    VPCI = (VWMA_20 - SMA_20) / SMA_20 * (VWMA_5 / SMA_5) * (VMA_5 / VMA_20)

**What this session could NOT do, disclosed up front:** neither Dormeier's
article, his Dow Award paper (its link returned 404 to the issue's author on
2026-11-08), the CMT summary nor jesse's source was read here. Gate A starts
from the formula in the issue body, as the issue instructs. The default
lengths 5 and 20 are the owner's choice of 2026-11-08, not verified against
the original; so is the division of Dormeier's price-unit VPC by `SMA_20`,
which is what makes the column scale-free.

GATE A -- DERIVATION, factor by factor, from the issue's definition:

* `VWMA_n = sum(close * volume, n) / sum(volume, n)`, trailing, current bar
  included. Computed here as a ratio of two rolling SUMS, the issue's own
  spelling; `pandas_ta.overlap.vwma` computes the same quantity as a ratio
  of two rolling MEANS, which `tests/test_vpci.py` uses as the independent
  reference (they agree to float64 rounding, not bit-for-bit -- see the
  receipt).
* `SMA_n` = trailing `n`-bar mean of close; `VMA_n` = trailing `n`-bar mean
  of volume.
* `VPC = (VWMA_long - SMA_long) / SMA_long` -- Dormeier's VPC divided by
  `SMA_long` (the owner's normalisation). `VPR = VWMA_short / SMA_short`.
  `VM = VMA_short / VMA_long`. `VPCI = VPC * VPR * VM`, multiplied left to
  right in that order.

CAUSALITY. Every term is `rolling(n, min_periods=n)` over `[t-n+1, t]`, and
the three products are pointwise on bar `t`; there is no `center=True` and
no negative shift, so the only way this chain could look ahead is a write at
the wrong bar. `tests/test_vpci.py` pins both halves: future-perturbation on
the real module and an in-memory mutant that shifts the final write.

WARM-UP. The first defined bar is `max(short, long) - 1` (19 at the
defaults); `verify_series` needs `max(short, long)` bars of history.

SCALE-FREE. For any `k > 0`, close `x k` scales `VWMA` and `SMA` alike, so
`VPC` and `VPR` are unchanged and `VM` never reads close; volume `x k`
cancels inside each `VWMA` and inside `VM`. Bit-identical at powers of two,
within float64 rounding otherwise (measured in the receipt).

ZERO VOLUME. For a non-negative volume series, a `short`- or `long`-bar
window of all-zero volume makes that `VWMA` `0 / 0 = NaN`, which propagates
into the product -- the issue's "NaN when a volume sum is 0". `VM`'s
denominator `VMA_long` is zero only when the `long` window is all zero, in
which case `VWMA_long` is already NaN. No `inf` can arise for non-negative
volume, so there is no `inf -> NaN` guard; a SIGNED volume series (this
fork's `vol_delta`, `vsumd`) is outside the column's definition and can
yield `+-inf`.
"""
from pandas_ta.utils import get_offset, verify_series


def vpci(close, volume, short=None, long=None, offset=None, **kwargs):
    """Indicator: Volume Price Confirmation Indicator (VPCI)"""
    # Validate Arguments
    short = int(short) if short and short > 0 else 5
    long = int(long) if long and long > 0 else 20
    min_length = max(short, long)
    close = verify_series(close, min_length)
    volume = verify_series(volume, min_length)
    offset = get_offset(offset)

    if close is None or volume is None:
        return

    # Calculate Result
    pv = close * volume
    sma_long = close.rolling(long, min_periods=long).mean()
    vwma_long = pv.rolling(long, min_periods=long).sum() / volume.rolling(long, min_periods=long).sum()
    vwma_short = pv.rolling(short, min_periods=short).sum() / volume.rolling(short, min_periods=short).sum()
    vpc = (vwma_long - sma_long) / sma_long
    vpr = vwma_short / close.rolling(short, min_periods=short).mean()
    vm = volume.rolling(short, min_periods=short).mean() / volume.rolling(long, min_periods=long).mean()
    result = vpc * vpr * vm

    # Offset
    if offset != 0:
        result = result.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        result.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        result.fillna(method=kwargs["fill_method"], inplace=True)

    # Name & Category
    result.name = f"VPCI_{short}_{long}"
    result.category = "volume"

    return result


vpci.__doc__ = \
"""Volume Price Confirmation Indicator (VPCI)

Buff Dormeier (TASC, July 2007), per issue #264, with Dormeier's price-unit
VPC divided by SMA(close, long) so the column is scale-free (owner's choice).
Positive when volume-weighted price runs above plain price (volume confirms
the trend), scaled by the short-term volume-weighted price ratio and by the
short-to-long volume ratio. See docs/VpciMeasured.md for the measured numbers.

Calculation:
    Default Inputs:
        short=5, long=20
    VWMA_n = SUM(close * volume, n) / SUM(volume, n)
    VPC  = (VWMA_long - SMA(close, long)) / SMA(close, long)
    VPR  = VWMA_short / SMA(close, short)
    VM   = SMA(volume, short) / SMA(volume, long)
    VPCI = VPC * VPR * VM

Args:
    close (pd.Series): Series of 'close's
    volume (pd.Series): Series of 'volume's
    short (int): Short window. Default: 5
    long (int): Long window. Default: 20
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.Series: VPCI_{short}_{long}, scale-free, signed. NaN for the first
        max(short, long) - 1 bars and wherever a short- or long-window volume
        sum is zero.
"""
