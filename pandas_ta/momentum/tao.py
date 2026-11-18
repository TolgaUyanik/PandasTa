# -*- coding: utf-8 -*-
from pandas_ta.utils import get_offset, verify_series


def tao(high, low, close, length=None, ma_length=None, midpoint=None,
        offset=None, **kwargs):
    """Indicator: Trend-Adjusted Oscillator (TAO)"""
    # Validate Arguments
    length = int(length) if length and length > 0 else 10
    ma_length = int(ma_length) if ma_length and ma_length > 0 else 5
    midpoint = float(midpoint) if midpoint is not None else 50.0
    _length = length + ma_length - 1
    high = verify_series(high, _length)
    low = verify_series(low, _length)
    close = verify_series(close, _length)
    offset = get_offset(offset)

    if high is None or low is None or close is None: return

    # Calculate Result
    lowest_low = low.rolling(length).min()
    highest_high = high.rolling(length).max()
    rng = highest_high - lowest_low
    # NaN on a zero range, as the issue defines it -- NOT `non_zero_range`,
    # which `stoch` uses and which adds an epsilon and reads a flat window
    # as 0 (`docs/TaoMeasured.md` §A3).
    osc = 100 * (close - lowest_low) / rng.where(rng != 0)
    # A plain rolling mean rather than `sma`: `sma` dispatches to TA-Lib
    # when it is importable, so the column would depend on the environment.
    mao = osc.rolling(ma_length).mean()
    tao = osc - (mao - midpoint)

    # Offset
    if offset != 0:
        tao = tao.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        tao.fillna(kwargs["fillna"], inplace=True)

    # Name and Categorize it
    _mid = "" if midpoint == 50.0 else f"_{midpoint:g}"
    tao.name = f"TAO_{length}_{ma_length}{_mid}"
    tao.category = "momentum"

    return tao


tao.__doc__ = \
"""Trend-Adjusted Oscillator (TAO)

A 10-bar stochastic shifted by how far its own 5-bar mean sits from 50, so
it stops clustering in one half of the range during a trend.

    O[T]   = 100 * (close[T] - LL10[T]) / (HH10[T] - LL10[T])   (NaN if HH == LL)
    MAO[T] = mean(O[T - 4 .. T])
    TAO[T] = O[T] - (MAO[T] - 50)

Source: Perry J. Kaufman, *Trading Systems and Methods*, 5th ed. (Wiley,
2013), ch. 17, "Trend-Adjusted Oscillator", crediting E. Marshall Wall,
"Rolling with the Punches", *Futures* (July 1996). The book applies it to
"stochastics or other oscillators" with a 10-day oscillator and a 5-day
average. Its formula for the oscillator itself is garbled in the text
available, so the raw stochastic %K(10) is the owner's choice (issue #266,
2026-11-08). Gate A starts from that issue's formula, not from a prototype
and not from a reading of the book.

Algebraically `TAO = 50 + (O - MAO)`: the stochastic's deviation from its
own short mean, re-centred on 50. ⚠ It is NOT bounded to [0, 100]: `O` is
one of the five terms of `MAO`, so `O - MAO = 0.8 * O - (sum of the other
four) / 5` lies in [-80, +80] and the column in [-30, 130] at the default.
The ends are attained -- four closes at the low of the range, then one at
its high (a hand frame in the tests pins both). The measured range is in `docs/TaoMeasured.md` §C.

Causal: bar T reads `high`, `low` and `close` on bars `T - 13 .. T` and
nothing later; swept and mutant-tested in `tests/test_tao.py`.

Scale-free: every price enters as a difference over a difference, so a
positive rescale and a level shift both cancel (x8 / x64 bit-identical; see
`docs/TaoMeasured.md` §D for the inexact factors and the shift).

NaN on bars 0 .. 12 (the first `length + ma_length - 2` = 13 bars); the
first value is on bar 13. NaN also for `ma_length` bars
from any bar whose 10-bar range is exactly 0 (a flat window), since the
rolling mean then has a NaN in its window.

Calculation:
    Default Inputs:
        length=10, ma_length=5, midpoint=50
    LL  = low.rolling(length).min()
    HH  = high.rolling(length).max()
    O   = 100 * (close - LL) / (HH - LL)       (HH == LL -> NaN)
    TAO = O - (O.rolling(ma_length).mean() - midpoint)

Args:
    high (pd.Series): Series of 'high's
    low (pd.Series): Series of 'low's
    close (pd.Series): Series of 'close's
    length (int): The stochastic lookback. Default: 10
    ma_length (int): Bars in the oscillator's mean. Default: 5
    midpoint (float): The level the mean is measured from. Default: 50
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)

Returns:
    pd.Series: TAO_10_5 (a non-default midpoint is appended, e.g. TAO_10_5_40)
"""
