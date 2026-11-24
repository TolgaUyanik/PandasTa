# -*- coding: utf-8 -*-
from pandas_ta.utils import get_offset, verify_series


def tdi(close, length=None, multiple=None, offset=None, **kwargs):
    """Indicator: Trend Detection Index (TDI)"""
    # Validate Arguments
    length = int(length) if length and length > 0 else 20
    multiple = int(multiple) if multiple and multiple > 0 else 2
    long_length = multiple * length
    _length = length + long_length
    close = verify_series(close, _length)
    offset = get_offset(offset)

    if close is None: return

    # Calculate Result
    mom = close - close.shift(length)
    abs_mom = mom.abs()
    short_sum = mom.rolling(length).sum()
    short_abs_sum = abs_mom.rolling(length).sum()
    long_abs_sum = abs_mom.rolling(long_length).sum()
    tdi = (short_sum.abs() - (long_abs_sum - short_abs_sum)) / close

    # Offset
    if offset != 0:
        tdi = tdi.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        tdi.fillna(kwargs["fillna"], inplace=True)

    # Name and Categorize it
    tdi.name = f"TDI_{length}_{multiple}"
    tdi.category = "trend"

    return tdi


tdi.__doc__ = \
"""Trend Detection Index (TDI)

M. H. Pee's Trend Detection Index: the absolute `length`-bar sum of momentum
(a directional, signed quantity) minus the excess of absolute momentum
accumulated over the longer `multiple * length` window, scaled by `close`
to make the column price-free.

    mom[T]       = price[T] - price[T - length]
    TDI_n_m[T]   = (|sum_n mom| - (sum_2n |mom| - sum_n |mom|)) / price[T]

where n = length, 2n = multiple * length, and the two rolling sums run
over the n and 2n most recent values of `mom`.

Source: R TTR (GPL-2.0), `TDI.R`: `|sum_n mom| - (sum_2n |mom| - sum_n
|mom|)`, `mom = price - price[n]`. Ported from that published formula, not
from the R source code; the scale-free `/close` form is the owner's choice
(PandasTa issue #148, 2026-10-25).

Diverges from the issue's own prototype, `docs/issues/screen/ind_screen_r5.py`'s
`ttr_tdi_20`: the prototype computes `mom = (close - close.shift(length)).fillna(0)`
before the rolling sums. That `fillna(0)` is NOT reproduced here -- it is a
screening-harness convenience absent from the issue's own distilled formula above, so
`mom` stays NaN until real history exists, same as this fork's `mom`/`roc`. This makes
the warm-up longer than the prototype's (59 bars here vs. the prototype's 39).

The first term is large when the `length`-bar move is persistently
one-directional (the signed sum does not cancel); the second term grows
when the longer window accumulates much MORE absolute movement than the
shorter one already counted, i.e. a choppy market outside the short
window. A trending market scores high; a choppy one scores low or negative.

Causal: bar T reads `close` on bars `T - (length + multiple * length - 1)
.. T` and nothing later.

Scale-free: `mom`, both rolling sums and the final numerator are all
linear in `close`, and the `/close` divisor cancels a positive rescale
exactly (x8 / x64 bit-identical).

NaN for the first `length + multiple * length - 1` bars (59 at the
defaults), the longer of the two rolling sums' warm-ups.

Calculation:
    Default Inputs:
        length=20, multiple=2
    mom          = close - close.shift(length)
    short_sum    = mom.rolling(length).sum()
    short_abs    = mom.abs().rolling(length).sum()
    long_abs     = mom.abs().rolling(multiple * length).sum()
    TDI_20_2     = (short_sum.abs() - (long_abs - short_abs)) / close

Args:
    close (pd.Series): Series of 'close's
    length (int): The short momentum window. Default: 20
    multiple (int): Multiplier on `length` for the long window. Default: 2
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)

Returns:
    pd.Series: TDI_20_2
"""
