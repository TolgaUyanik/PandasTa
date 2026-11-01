# -*- coding: utf-8 -*-
import numpy as np
from pandas import DataFrame
from pandas_ta.utils import get_offset, verify_series


def _pearson_r(y, wave, wave_sum, wave2_sum, length):
    """Pearson correlation of window `y` against the fixed `wave`, same
    closed-form sums as `pandas_ta.overlap.linreg`'s `r=True` branch (there
    against a ramp; here against a sinusoid). NaN on a degenerate window
    (zero variance in `y`) rather than a division by zero."""
    y_sum = y.sum()
    y2_sum = (y * y).sum()
    wy_sum = (wave * y).sum()
    rn = length * wy_sum - wave_sum * y_sum
    rd_sq = (length * wave2_sum - wave_sum * wave_sum) * (length * y2_sum - y_sum * y_sum)
    if rd_sq <= 0:
        return np.nan
    return rn / np.sqrt(rd_sq)


def correlation_cycle(close, length=None, offset=None, **kwargs):
    """Indicator: Correlation Cycle (Real, Imag, Angle)"""
    # Validate arguments
    length = int(length) if length and length > 1 else 20
    close = verify_series(close, length)
    offset = get_offset(offset)

    if close is None: return

    # Reference waves: position k=0 is the OLDEST bar in the rolling window
    # and k=length-1 the newest -- the same oldest-first convention this
    # fork's own `linreg(r=True)` uses for its ramp (x = range(1, length+1),
    # multiplied positionally against a raw=False window). One full period
    # per window, so Sum(wave) ~ 0 up to float rounding.
    k = np.arange(length)
    cos_wave = np.cos(2 * np.pi * k / length)
    sin_wave = np.sin(2 * np.pi * k / length)
    cos_sum, cos2_sum = float(cos_wave.sum()), float((cos_wave * cos_wave).sum())
    sin_sum, sin2_sum = float(sin_wave.sum()), float((sin_wave * sin_wave).sum())

    real = close.rolling(length).apply(
        lambda y: _pearson_r(y, cos_wave, cos_sum, cos2_sum, length), raw=True)
    imag = close.rolling(length).apply(
        lambda y: _pearson_r(y, sin_wave, sin_sum, sin2_sum, length), raw=True)
    angle = np.degrees(np.arctan2(imag, real))

    # CC_IMAG_<length> is computed above (needed for Angle) but not shipped as
    # a column: Gate E (docs/CorrelationCycleMeasured.md) struck it, max |rho|
    # 0.9353 vs Squeeze_Spread_pct on the 89-frame BIST universe.
    df = DataFrame({
        f"CC_REAL_{length}": real,
        f"CC_ANGLE_{length}": angle,
    }, index=close.index)

    # Offset
    if offset != 0:
        df = df.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        df.fillna(kwargs["fillna"], inplace=True)

    # Name and Categorize it
    df.name = f"CC_{length}"
    df.category = "cycles"

    return df


correlation_cycle.__doc__ = \
"""Correlation Cycle (CC)

John Ehlers' correlation-based cycle/phase detector (the sibling named in
issue #30 of the fork's already-shipped `cti`, Correlation Trend Indicator,
same author, same year, 2020): instead of correlating price against a
straight ramp (what `cti` does, via `linreg(r=True)`), this correlates price
against a cosine and a sine reference wave of one fixed period (`length`),
giving a Real and an Imaginary part, and an Angle from their arctangent.

⚠ Gate A is self-consistency, not a line-by-line source citation. Per issue
#30, no file in the owner's local Pine corpus mentions Correlation Cycle, so
its only possible Gate A references are Ehlers' own papers or a library's
source -- and neither is reachable from this environment (no web access, no
Pine corpus access). The Pearson-correlation arithmetic itself is exact and
unambiguous (it is the same closed-form sums already shipped and tested in
`linreg`'s `r=True` branch, here applied to a sinusoid instead of a ramp);
what is NOT verified against any source is Ehlers' own convention for which
end of the window is lag zero, the sign of the sine reference, and the
"market state" sub-indicator his published version also carries. Those three
would be invented, not ported; market state is skipped (see
`docs/EhlersDspMeasured.md`). Imag is also not shipped, but for a measured
reason, not an invented one: Gate E struck it (max |rho| 0.9353 vs
`Squeeze_Spread_pct`), so only Real / Angle ship.

Calculation:
    Default Inputs:
        length=20
    k = 0, 1, ..., length-1   (0 = oldest bar in the window)
    Real  = PearsonR(close, cos(2*pi*k/length))   over the trailing window
    Imag  = PearsonR(close, sin(2*pi*k/length))   over the trailing window
    Angle = degrees(atan2(Imag, Real))             in (-180, 180]

Real is a Pearson correlation coefficient: unit-free by construction
(invariant to `close -> close * k` for any k > 0, since a correlation
coefficient is scale- and location-invariant), bounded in [-1, 1]. Angle is
a rotation angle, not a price, bounded in (-180, 180]. Imag is computed
internally (Angle needs it) but is NOT shipped as a column: measured Gate E
max |rho| 0.9353 vs `Squeeze_Spread_pct` on the 89-frame BIST universe, over
CLAUDE.md's 0.90 STRUCK line. See docs/CorrelationCycleMeasured.md.

Args:
    close (pd.Series): Series of 'close's
    length (int): Number of bars in one reference-wave period. Default: 20
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)

Returns:
    pd.DataFrame: CC_REAL_<length>, CC_ANGLE_<length>
"""
