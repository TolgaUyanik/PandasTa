# -*- coding: utf-8 -*-
from pandas_ta.utils import get_offset, verify_series


def maxvol_adv(volume, short=None, long=None, offset=None, **kwargs):
    """Indicator: Peak Volume over ADV (MAXVOLADV)"""
    short = int(short) if short and short > 0 else 14
    long = int(long) if long and long > 0 else 50
    volume = verify_series(volume, max(short, long))
    offset = get_offset(offset)

    if volume is None: return

    peak = volume.rolling(short, min_periods=short).max()
    adv = volume.rolling(long, min_periods=long).mean()
    # A zero ADV (a halted stretch) has no ratio; NaN, not inf.
    mva = peak / adv.where(adv > 0)

    # Offset
    if offset != 0:
        mva = mva.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        mva.fillna(kwargs["fillna"], inplace=True)

    mva.name = f"MAXVOLADV_{short}_{long}"
    mva.category = "volume"

    return mva


maxvol_adv.__doc__ = \
"""Peak Volume over ADV (MAXVOLADV)

The largest single-bar volume of the last `short` bars, divided by the
average volume of the last `long` bars (ADV). 1 means the peak bar was an
ordinary bar; 5 means one bar in the window traded five times the average.
Both windows end at, and include, the current bar.

Source: Reddit, r/Daytrading post 1tv21c0 (2026-06-02),
https://www.reddit.com/r/Daytrading/comments/1tv21c0/ -- a feature list
naming "max_volume_vs_adv (peak volume day)". Crowd talk (tier 4): the
poster's claim (a top-3 feature of an XGBoost classifier, AUC 0.723, for
100-200% five-day moves in low-float stocks) is untested here. The post
gives only the feature name: it fixes neither the peak window nor what ADV
is. The 14-bar peak and ADV = SMA(volume, 50) over a window that excludes
nothing are the choices of the 2026-10-26 screen prototype (candidate
b2_maxvol14_adv50, docs/issues/screen/ind_screen_r8.py:116-118, local to
the owner's machine). It computes the same ratio; the one difference is a
negative ADV, finite there and NaN here, which real volume cannot reach.
Same post as `range_compress_run`.

Volume only, so no price rescaling can change it. A volume rescaling
cancels up to float rounding: bit-identical for power-of-two factors (x8,
x64), within 4e-16 relative otherwise (x10, x3.7 measured).

Both windows need every bar, so one NaN volume bar blanks its own output
and the next max(short, long) - 1 bars (50 bars in all at the defaults).

Calculation:
    Default Inputs:
        short=14, long=50
    PEAK = rolling max(volume, short)
    ADV = SMA(volume, long)
    MAXVOLADV = PEAK / ADV, NaN where ADV <= 0

Args:
    volume (pd.Series): Series of 'volume's
    short (int): Window of the peak. Default: 14
    long (int): Window of the average. Default: 50
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)

Returns:
    pd.Series: MAXVOLADV_{short}_{long}
"""
