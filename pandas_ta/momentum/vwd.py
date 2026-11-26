# -*- coding: utf-8 -*-
import numpy as np

from pandas_ta.overlap.ema import ema
from pandas_ta.overlap.sma import sma
from pandas_ta.utils import get_offset, verify_series

#: The poster's two windows, "sma14" and "ema7". They are module constants
#: rather than arguments for the same reason as `j_wae`'s: the issue's
#: quote and the screen prototype (`docs/issues/screen/ind_screen_r9.py`,
#: candidate `b3_vwd_14`) spell exactly these two, that one combination is
#: the whole of what the 2026-10-29 screen measured at Gate E, and
#: `docs/gate_e_ledger.py` refuses a Gate E run taken at non-default
#: parameters anyway.
FAST = 7
SLOW = 14

#: The poster's two multipliers, "* 100" on the MA difference and "* 10" on
#: the product. Neither changes a rank, so neither changes Gate E; they are
#: kept so the column reads in the poster's units.
PERCENT = 100.0
GAIN = 10.0

#: Bars a frame must have before the function computes at all, and
#: `MIN_BARS - 1` is the index of the first bar that can fire on a clean
#: frame: SMA14 of the close and SMA14 of |vp| both first fire at index
#: SLOW - 1, and the SMA-seeded EMA7 has been ready since FAST - 1.
MIN_BARS = SLOW


def vwd(high, low, close, offset=None, **kwargs):
    """Indicator: Volume-Weighted MA-Difference oscillator (VWD)"""
    # Validate Arguments
    high = verify_series(high, MIN_BARS)
    low = verify_series(low, MIN_BARS)
    close = verify_series(close, MIN_BARS)
    offset = get_offset(offset)

    if high is None or low is None or close is None: return

    # Calculate Result
    # A non-finite price becomes the NaN it already is, so an infinity is
    # skipped by the EMA and blanks only the windows that contain it.
    h = high.astype(float)
    l = low.astype(float)
    c = close.astype(float)
    h, l, c = h.where(np.isfinite(h)), l.where(np.isfinite(l)), c.where(np.isfinite(c))

    # "madif = ((sma14 - ema7) / ema7) * 100". This fork's `ema`, imported
    # from its own module: SMA-seeded at bar FAST - 1, `adjust=False` --
    # the same seeding as `talib.EMA`. A bare `ewm(span=7)` from bar 0 is a
    # different column; `tests/test_vwd.py` prices it.
    e = ema(c, length=FAST)
    madif = (sma(c, length=SLOW) - e) / e * PERCENT

    # "vp = (buy - sell) / (buy + sell), buy = V*(C-L)/(H-L),
    # sell = V*(H-C)/(H-L)". V and (H-L) cancel from the numerator and the
    # denominator, so vp is the close location value and volume is not
    # read: buy + sell = V. The literal form differs only where V == 0
    # (0/0) or V is NaN, and in the last bits; Gate A measures both.
    # A bar with H == L is 0/0 in the source too, so it is blank here, and
    # it blanks SLOW bars of `vs` below -- the source's behaviour, kept.
    # A bar with H < L (corrupt data; finite in the source) is blanked too.
    rng = h - l
    vp = ((c - l) - (h - c)) / rng.where(rng > 0.0)

    # "vs = SMA14(|vp|)": the mean pressure magnitude over SLOW bars.
    vs = sma(vp.abs(), length=SLOW)

    # "vwd = madif * vp * vs * 10".
    vwd = madif * vp * vs * GAIN
    vwd = vwd.where(np.isfinite(vwd))

    # Offset
    if offset != 0:
        vwd = vwd.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        vwd.fillna(kwargs["fillna"], inplace=True)

    # Name and Categorize it
    vwd.name = f"VWD_{FAST}_{SLOW}"
    vwd.category = "momentum"

    return vwd


vwd.__doc__ = \
"""Volume-Weighted MA-Difference oscillator (VWD)

The percent gap of the 14-bar SMA over the 7-bar EMA, times the bar's close location and its 14-bar mean absolute value.

    madif[T] = (SMA(close, 14)[T] - EMA(close, 7)[T]) / EMA(close, 7)[T] * 100
    vp[T]    = (buy - sell) / (buy + sell),  buy = V*(C-L)/(H-L),
               sell = V*(H-C)/(H-L)   ==  ((C-L) - (H-C)) / (H-L)
    vs[T]    = SMA(|vp|, 14)[T]
    VWD[T]   = madif[T] * vp[T] * vs[T] * 10

Source: Reddit, tier 4 -- r/TradingView post 1gofmli (2024-11-11),
https://www.reddit.com/r/TradingView/comments/1gofmli/, as PandasTa issue
#202 quotes it: "madif = ((sma14 - ema7) / ema7) * 100; vp = (buy - sell) /
(buy + sell), buy = V*(C-L)/(H-L), sell = V*(H-C)/(H-L); vs = SMA14(|vp|);
vwd = madif * vp * vs * 10". The poster reads 3-minute bars and fires on a
2-sigma band with an RSI filter; neither the band nor the filter ships, and
nothing here tests what the poster says the oscillator does. Existence, not
evidence.

⚠ **"Volume-weighted" in name only.** V multiplies both `buy` and `sell`,
so it cancels from `vp`, and this module does not read volume. The literal
form with V agrees to rounding wherever V > 0 (`tests/test_vwd.py`, Gate
A); where V == 0 the literal form is 0/0, and where V is NaN it is NaN.

⚠ **A bar with H == L blanks SLOW bars.** `vp` is 0/0 there in the source,
and SMA14 of |vp| needs 14 valid bars, so one such bar blanks the column at
that bar and the next 13. An H < L bar (corrupt data) is blanked the same
way, although the source would compute it. Kept as the source computes it; the cost on real
data is what the Gate E run's sample size reports.

Causal: bar T reads high, low and close up to T. Measured by a 36-offset
future-perturbation sweep and by look-ahead mutants read off this file,
edited and `exec`'d in memory (`tests/test_vwd.py`, Gate B).

Scale-free: `madif` is a ratio of prices and `vp` a ratio of price
differences, so a common rescale of H, L and C cancels; x8 and x64 are
bit-identical (Gate D). Figures in `docs/VwdMeasured.md`.

Calculation:
    Default Inputs:
        fast=7, slow=14 -- module constants
    e     = ema(close, 7)                       SMA-seeded
    madif = (sma(close, 14) - e) / e * 100
    vp    = ((close - low) - (high - close)) / (high - low)   blank if H <= L
    vs    = sma(|vp|, 14)
    VWD   = madif * vp * vs * 10

Args:
    high (pd.Series): Series of 'high's
    low (pd.Series): Series of 'low's
    close (pd.Series): Series of 'close's
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)

Returns:
    pd.Series: VWD_7_14, a dimensionless oscillator
"""
