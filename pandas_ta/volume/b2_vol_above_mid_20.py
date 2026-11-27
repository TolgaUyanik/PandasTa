# -*- coding: utf-8 -*-
"""Share of window volume on closes above the range midpoint (20) -- issue #188
(B2-VOL-ABOVE-MID-20). Reddit, tier 4 (ResearchIntel kb/reddit.db):
rd:algotrading:1whq9hv (2026-09-16),
https://www.reddit.com/r/algotrading/comments/1whq9hv/ . Existence, not
evidence: nothing here tests the poster's own claimed use (supply/demand
imbalance, support/resistance via the resulting split).

GATE A. The poster's own words: "Get the highest high - lowest low divide by
half = equals equilibrium or zeroline, program any candle closing above or
below zeroline, find volume for those". The screen prototype's own
formalisation (`docs/issues/screen/ind_screen_r8.py`, candidate
`b2_vol_above_mid_20`) is read directly, scale-free form, 20-bar window, the
midpoint of the CURRENT window applied to its own 20 bars:

    mid[t]   = (HHV(high, 20)[t] + LLV(low, 20)[t]) / 2
    window   = bars [t-19, t]
    vol_above[t] = sum(volume[i] for i in window if close[i] > mid[t])
    vol_total[t] = sum(volume[i] for i in window)
    B2_VOL_ABOVE_MID_20[t] = vol_above[t] / vol_total[t]      (undefined -> NaN)

`HHV`/`LLV` are this fork's standing rolling max/min convention (trailing,
`.rolling(length, min_periods=length)`, ending at and including the current
bar -- the same convention every other `HHV`/`LLV`-based port here uses,
e.g. `rd_dip_depth_10_25`). "Closing above" is read as the strict `close[i]
> mid[t]` the prototype itself uses (`cw > mid[t]`), not `>=`: a bar closing
exactly AT the midpoint counts toward neither side's volume, matching the
poster's own binary "above or below" framing with nothing stated about ties.
A window is undefined when `mid[t]` has not yet seen a full 20-bar lookback
(the first `length - 1` bars) or when `vol_total[t] == 0` (every bar in the
window has zero volume, `0 / 0`).

READING. The poster's own claimed use (not independently tested here):
"equilibrium" splits the current 20-bar range in half; the fraction of that
window's volume that transacted on bars closing in the UPPER half reads
(per the poster) as participation weighted toward the top of the range --
claimed evidence of demand absorbing supply there, with the resulting level
read as a support/resistance line. Bounded in `[0, 1]`: 0 means every bar
closing above `mid[t]` carried no volume (none of this window's volume
traded above the midpoint), 1 means all of the window's volume traded on
bars closing above it, near 0.5 a roughly even split.

CAUSALITY. `mid[t]` reads `high`/`low` only over `[t-19, t]`
(`.rolling(20, min_periods=20)`, pandas' own causal convention, no
`center=True`); `vol_above[t]`/`vol_total[t]` read `close`/`volume` over the
SAME window `[t-19, t]`. By construction `B2_VOL_ABOVE_MID_20[t]` reads no
bar after `t` and no bar before `t-19`. `tests/test_b2_vol_above_mid_20.py`
proves this both by future-perturbation (every OHLCV bar from `J` onward
replaced by an independent synthetic path, bars `< J` required bit-identical
with matching NaN masks, swept over many `J` past the warm-up) and by two
mutants, each `importlib`-read and `exec`'d in memory, shown live (differs
from the real module) and then caught at every swept offset: the final write
shifted `length` bars into the future (`result.shift(-length)`), and `mid`
built with a FORWARD-looking rolling window (`.shift(-length)` appended
after the trailing rolling max/min, so bar `t`'s "midpoint" actually reads
`high[t+1 .. t+length]` / `low[t+1 .. t+length]`, none of which overlaps the
trailing window the real module reads).

SCALE-FREE, on two independent axes. Let `k > 0` rescale price (`high, low,
close -> k*high, k*low, k*close`) and `j > 0` rescale volume
(`volume -> j*volume`), independently or together. A positive price rescale
scales `high`, `low` AND `close` by the identical factor `k`, so `HHV`,
`LLV` and hence `mid` scale by exactly `k` too (max/min pick an existing,
exactly `k`-scaled element; `(a*k + b*k)/2` and `k*(a+b)/2` round identically
for a power-of-two `k`, which only shifts the exponent); the comparison
`close[i]*k > mid[t]*k` is then the SAME comparison the unscaled module
makes, bit-for-bit exact for a power-of-two `k` since multiplying both sides
of a comparison by the same exact power-of-two factor cannot change which
side is larger. `vol_above`/`vol_total` never read price, so they are
untouched by any price rescale at all. Symmetrically, a positive volume
rescale `j` scales `vol_above` and `vol_total` by the identical exact factor
(a sum of `j`-scaled terms scales by the same exact `j` for a power-of-two
`j`), and their ratio cancels `j` exactly (dividing two `j`-scaled floats by
each other reproduces the unscaled quotient bit-for-bit, because the shared
exponent shift cancels in IEEE754 division); price never enters the
comparison's truth value, which volume plays no part in deciding. The ratio
is therefore invariant under ANY positive price rescale, ANY positive volume
rescale, or both together -- exact in real arithmetic, and in float64
bit-identical for a power-of-two factor. A non-power-of-two factor (`x10`,
`x3.7`) rounds `high*k`/`low*k`/`close*k`/`volume*j` independently before
the rolling max/min/sums run on already-rounded inputs, so the invariance
then holds only to within float64 tolerance -- including the rare case where
independent rounding of `close[i]*k` and `mid[t]*k` moves a bar across the
strict `>` boundary it sat exactly on before scaling. Measured in
`docs/measure_b2_vol_above_mid_20.py` (see `docs/B2VolAboveMid20Measured.md`):
price-only, volume-only, and both together, at `x8`/`x64` (bit-identical,
modulo any such boundary bar) and `x10`/`x3.7` (tolerance).
"""
import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from pandas import Series

from pandas_ta.utils import get_offset, verify_series


def b2_vol_above_mid_20(high, low, close, volume, length=None, offset=None, **kwargs):
    """Indicator: Share of Window Volume on Closes Above the Range Midpoint (B2_VOL_ABOVE_MID)"""
    # Validate Arguments
    length = int(length) if length and int(length) > 0 else 20
    high = verify_series(high, length)
    low = verify_series(low, length)
    close = verify_series(close, length)
    volume = verify_series(volume, length)
    offset = get_offset(offset)

    if high is None or low is None or close is None or volume is None: return

    # Calculate Result
    hhv = high.rolling(length, min_periods=length).max()
    llv = low.rolling(length, min_periods=length).min()
    mid = (hhv + llv) / 2.0

    c = close.to_numpy(dtype=float)
    v = volume.to_numpy(dtype=float)
    mid_tail = mid.to_numpy(dtype=float)[length - 1:]

    close_windows = sliding_window_view(c, length)  # shape (n-length+1, length)
    vol_windows = sliding_window_view(v, length)
    above = close_windows > mid_tail[:, None]
    vol_above = np.where(above, vol_windows, 0.0).sum(axis=1)
    vol_total = vol_windows.sum(axis=1)

    with np.errstate(invalid="ignore", divide="ignore"):
        frac = vol_above / vol_total
    frac = np.where((vol_total > 0) & np.isfinite(mid_tail), frac, np.nan)

    out = np.full(len(c), np.nan)
    out[length - 1:] = frac
    result = Series(out, index=close.index)

    # Offset
    if offset != 0:
        result = result.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        result.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        method = kwargs["fill_method"]
        if method in ("ffill", "pad"):
            result = result.ffill()
        elif method in ("bfill", "backfill"):
            result = result.bfill()
        else:  # a silent bfill on a typo would be a look-ahead
            raise ValueError(f"fill_method must be ffill/pad or bfill/backfill, not {method!r}")

    # Name & Category
    result.name = f"B2_VOL_ABOVE_MID_{length}"
    result.category = "volume"

    return result


b2_vol_above_mid_20.__doc__ = \
"""Share of Window Volume on Closes Above the Range Midpoint (B2_VOL_ABOVE_MID)

Equilibrium/zeroline reading, crowd talk (Reddit, tier 4): split the current
20-bar window at its own midpoint, `(HHV(high,20) + LLV(low,20)) / 2`, then
report what fraction of that window's OWN volume traded on bars closing
strictly above it. Bounded in `[0, 1]`. Existence, not evidence: nothing
here tests the poster's claimed use (supply/demand imbalance, a
support/resistance line at the resulting split). See the module source above
and docs/B2VolAboveMid20Measured.md for what was actually measured.

Source:
    Reddit, tier 4 (ResearchIntel kb/reddit.db): rd:algotrading:1whq9hv
    (2026-09-16), https://www.reddit.com/r/algotrading/comments/1whq9hv/ --
    "Get the highest high - lowest low divide by half = equals equilibrium
    or zeroline, program any candle closing above or below zeroline, find
    volume for those."

Calculation:
    Default Inputs:
        length=20
    mid   = (HHV(high, length) + LLV(low, length)) / 2
    B2_VOL_ABOVE_MID = sum(volume where close > mid, over the trailing
        `length`-bar window) / sum(volume, over the same window)

Args:
    high (pd.Series): Series of 'high's
    low (pd.Series): Series of 'low's
    close (pd.Series): Series of 'close's
    volume (pd.Series): Series of 'volume's
    length (int): Rolling window for the midpoint and the volume split.
        Default: 20
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): 'ffill'/'pad' or 'bfill'/'backfill'

Returns:
    pd.Series: B2_VOL_ABOVE_MID_{length}. NaN for the first `length - 1`
        bars, and on any later bar whose trailing window has zero total
        volume -- each such bar divides by zero and is masked rather than
        left as +-inf.
"""
