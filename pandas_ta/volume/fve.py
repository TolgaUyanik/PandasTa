# -*- coding: utf-8 -*-
"""Finite Volume Elements (FVE) -- Markos Katsanos, "Finite Volume
Elements", Technical Analysis of Stocks & Commodities, April 2003, per issue
#260. Formula as the issue states it, from Linnsoft's reference
(https://www.linnsoft.com/techind/finite-volume-elements) and finta's
`FVE` (LGPL-3.0; its code is not used here):

    FVE = 100 * sum_22(VE) / (SMA(volume, 22) * 22)

**What this session could NOT do, disclosed up front:** neither Katsanos's
April 2003 article, his volatility-adjusted September 2003 version,
Linnsoft's page nor finta's source was read here. Gate A starts from the
definition in the issue body, as the issue instructs. The fixed 0.3% cutoff
is the owner's choice of 2026-11-08; whether Katsanos also caps volume or
uses a cumulative sum is unverified and not part of this port.

GATE A -- DERIVATION, term by term, from the issue's definition:

* `TP_t = (high_t + low_t + close_t) / 3`.
* `MF_t = (close_t - (high_t + low_t) / 2) + (TP_t - TP_{t-1})` -- the
  close's position against the bar's midpoint plus the typical-price change.
  `TP_{t-1}` is undefined at bar 0, so `MF_0` is NaN.
* `VE_t = volume_t` if `MF_t > cutoff * close_t`, `-volume_t` if
  `MF_t < -cutoff * close_t`, else 0. Both comparisons are STRICT: a bar
  whose `|MF|` equals the band exactly is a 0, as the issue's "else 0"
  reads. `VE` is NaN wherever `MF` is NaN.
* `FVE_t = 100 * sum(VE, t-length+1..t) / sum(volume, t-length+1..t)`.
  `SMA(volume, n) * n` is written as the rolling SUM it equals. NaN when
  that volume sum is 0.

CAUSALITY. `TP_{t-1}` is a backward difference, the band reads bar `t`'s own
close, and both sums are `rolling(length, min_periods=length)` over
`[t-length+1, t]`; there is no `center=True` and no negative shift.
`tests/test_fve.py` pins both halves: future-perturbation on the real module
and an in-memory mutant that shifts the final write one bar into the future.

WARM-UP. `VE_0` is NaN, so the first full window of `VE` ends at bar
`length` (22 at the defaults); `verify_series` needs `length + 1` bars.

SCALE-FREE. Prices `x k` scale `MF` and the band alike, so every `VE` sign
is unchanged; volume `x k` scales numerator and denominator alike.
Bit-identical at powers of two; at other factors a bar whose `MF` sits
within float64 rounding of the band could flip -- measured in the receipt.

ZERO VOLUME. A window of all-zero volume makes both sums 0, and the
denominator is masked to NaN, so the result is NaN, never `inf`.
"""
from pandas_ta.utils import get_offset, verify_series


def fve(high, low, close, volume, length=None, cutoff=None, offset=None, **kwargs):
    """Indicator: Finite Volume Elements (FVE)"""
    # Validate Arguments
    length = int(length) if length and length > 0 else 22
    cutoff = float(cutoff) if cutoff is not None and cutoff >= 0 else 0.003
    min_length = length + 1
    high = verify_series(high, min_length)
    low = verify_series(low, min_length)
    close = verify_series(close, min_length)
    volume = verify_series(volume, min_length)
    offset = get_offset(offset)

    if high is None or low is None or close is None or volume is None:
        return

    # Calculate Result
    tp = (high + low + close) / 3
    mf = (close - (high + low) / 2) + (tp - tp.shift(1))
    band = cutoff * close
    ve = (volume.where(mf > band, 0.0) - volume.where(mf < -band, 0.0)).where(mf.notna())
    vsum = volume.rolling(length, min_periods=length).sum()
    vesum = ve.rolling(length, min_periods=length).sum()
    result = 100 * vesum / vsum.where(vsum != 0)

    # Offset
    if offset != 0:
        result = result.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        result.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        result.fillna(method=kwargs["fill_method"], inplace=True)

    # Name & Category
    # The issue fixes the default name FVE_22; a non-default cutoff is appended so two cutoffs never share a column.
    result.name = f"FVE_{length}" if cutoff == 0.003 else f"FVE_{length}_{cutoff}"
    result.category = "volume"

    return result


fve.__doc__ = \
"""Finite Volume Elements (FVE)

Markos Katsanos (TASC, April 2003), per issue #260, with the owner's fixed
cutoff. Net volume of the bars whose money flow moved more than `cutoff` of
the close, as a percent of all volume traded over `length` bars. Bounded in
[-100, 100] for non-negative volume. See docs/FveMeasured.md for the measured numbers.

Sources:
    Markos Katsanos, "Finite Volume Elements", TASC, April 2003
    https://www.linnsoft.com/techind/finite-volume-elements

Calculation:
    Default Inputs:
        length=22, cutoff=0.003
    TP  = (high + low + close) / 3
    MF  = (close - (high + low) / 2) + (TP - TP.shift(1))
    VE  = volume if MF > cutoff * close, -volume if MF < -cutoff * close, else 0
    FVE = 100 * SUM(VE, length) / SUM(volume, length)

Args:
    high (pd.Series): Series of 'high's
    low (pd.Series): Series of 'low's
    close (pd.Series): Series of 'close's
    volume (pd.Series): Series of 'volume's
    length (int): The window. Default: 22
    cutoff (float): Money-flow cutoff as a fraction of close; 0 drops the
        dead zone, a negative value falls back to the default. Default: 0.003
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.Series: FVE_{length} (FVE_{length}_{cutoff} at a non-default
        cutoff), scale-free, in [-100, 100] for non-negative volume. NaN for the first
        `length` bars and wherever the `length`-bar volume sum is zero.
"""
