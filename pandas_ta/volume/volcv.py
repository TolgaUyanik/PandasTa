# -*- coding: utf-8 -*-
from pandas_ta.utils import get_offset, verify_series


def volcv(volume, length=None, offset=None, **kwargs):
    """Indicator: Volume Coefficient of Variation (VOLCV)"""
    length = int(length) if length and length > 0 else 20
    volume = verify_series(volume, length)
    offset = get_offset(offset)

    if volume is None: return

    mean = volume.rolling(length, min_periods=length).mean()
    std = volume.rolling(length, min_periods=length).std()
    # A zero-volume stretch has mean == std == 0: 0/0 is NaN already, but the
    # `.where` keeps the intent explicit and matches every other ratio here.
    cv = std / mean.where(mean > 0)

    # Offset
    if offset != 0:
        cv = cv.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        cv.fillna(kwargs["fillna"], inplace=True)

    cv.name = f"VOLCV_{length}"
    cv.category = "volume"

    return cv


volcv.__doc__ = \
"""Volume Coefficient of Variation (VOLCV)

How erratic trading participation is over the last `length` bars, as opposed
to how high it is: the rolling standard deviation of volume divided by its
rolling mean. A level column (`Volume_Ratio_20`, `Volume_Pctl`) asks "is
volume high right now"; this asks "does volume swing a lot, independent of
its average level". Both windows end at, and include, the current bar.

Source: Alpha Architect, "How Volatility and Turnover Affect Return
Reversals" (the volume-dispersion half of its turnover variable); Kissell,
R., *The Science of Algorithmic Trading and Portfolio Management*, 2013,
ch. 5 (volume variability as a participation-risk input). Both describe the
ratio; neither is cited here as a measured result -- see
`docs/VolcvMeasured.md` for what was actually run.

Volume only, so no price rescaling can change it. A volume rescaling by a
constant k scales both the numerator and the denominator by k and cancels:
bit-identical for power-of-two factors (x8, x64), within float rounding
otherwise (x10, x3.7 measured).

Both the mean and the std need every bar, so one NaN volume bar blanks its
own output and the next `length` - 1 bars.

Calculation:
    Default Inputs:
        length=20
    MEAN = SMA(volume, length)
    STD = STDEV(volume, length)  # ddof=1, pandas default
    VOLCV = STD / MEAN, NaN where MEAN <= 0

Args:
    volume (pd.Series): Series of 'volume's
    length (int): The rolling window. Default: 20
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)

Returns:
    pd.Series: VOLCV_{length}
"""
