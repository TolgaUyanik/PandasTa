# -*- coding: utf-8 -*-
"""Temporal Centroid of Squared Returns (TFCENTROID) -- port of TSFEL's
`calc_centroid` (BSD-3-Clause), https://github.com/fraunhoferportugal/tsfel,
`tsfel/feature_extraction/features.py`:

    time = np.arange(0, len(signal))
    energy = np.sum(np.power(signal, 2))
    t_energy = np.dot(time, np.power(signal, 2))
    return t_energy / energy if energy != 0 else 0

TSFEL's `signal` is a generic 1-D array passed in by the caller; here the
signal is `length`-bar simple returns, and `time` is rescaled from
`0..length-1` to `0..1` so the column does not grow with `length` -- the
scale-free form prototyped at `docs/issues/screen/ind_screen_r2.py:209-213`
(candidate `tf_centroid_20`, local to the owner's machine, `docs/issues/`
is gitignored):

    t = np.arange(20) / 19
    roll(ret(c), 20, lambda W: (W ** 2 @ t) / sum(W ** 2))

CALCULATION.  Over the `length`-bar window ending at, and including, the
current bar: `t[k] = k / (length - 1)` for `k = 0..length-1` (oldest bar
first, so the current bar carries weight 1.0 and the oldest carries 0.0);
`x[k]` is the simple return `close[k] / close[k-1] - 1`. The result is
`sum(t * x^2) / sum(x^2)`, the energy-weighted mean position in the window:
near 1.0 when the largest squared returns sit at the recent end, near 0.0
when they sit at the old end, 0.5 for a flat or symmetric energy profile.

TSFEL returns 0 for a zero-energy window (silence); this port returns NaN
instead, matching the prototype's `sum(..) / np.where(s == 0, np.nan, s)`
and this fork's `sdiv`-style convention (`maxvol_adv`, `entropy`) of never
emitting a magic 0 for an undefined ratio. `length` consecutive identical
closes (all-zero returns) is the only way to reach it.

CAUSALITY.  The window is a plain trailing `sliding_window_view` ending at
bar `t`; nothing is shifted forward. `tests/test_tf_centroid_20.py` proves
this both by future-perturbation (31 offsets) and by a mutant that reads
`close` one bar ahead.

SCALE-FREE.  The signal is `close.pct_change(fill_method=None)`, a ratio, so a uniform
price rescaling cancels in the division before squaring: bit-identical
under a power-of-two price scale (x8, x64), and within float-rounding
tolerance under an arbitrary one (x10, x3.7) -- measured in the test file,
not assumed.
"""
import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from pandas import Series

from pandas_ta.utils import get_offset, verify_series


def tf_centroid_20(close, length=None, offset=None, **kwargs):
    """Indicator: Temporal Centroid of Squared Returns (TFCENTROID)"""
    # length=1 is rejected, not just length<=0: t = arange(length)/(length-1)
    # is undefined (0/0) at length=1.
    length = int(length) if length and length > 1 else 20
    close = verify_series(close, length + 1)
    offset = get_offset(offset)

    if close is None: return

    # fill_method=None: a gap must propagate as NaN, never get padded over.
    r = close.pct_change(fill_method=None).to_numpy(dtype=float)
    n = r.shape[0]
    out = np.full(n, np.nan)

    if n >= length:
        win = sliding_window_view(r, length)            # (n-length+1, length), oldest first
        sq = win ** 2
        t = np.arange(length, dtype=float) / (length - 1)
        num = sq @ t
        den = sq.sum(axis=1)
        with np.errstate(invalid="ignore", divide="ignore"):
            centroid = np.where(den > 0.0, num / den, np.nan)
        centroid = np.where(np.isfinite(win).all(axis=1), centroid, np.nan)
        out[length - 1:] = centroid

    result = Series(out, index=close.index)

    # Offset
    if offset != 0:
        result = result.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        result.fillna(kwargs["fillna"], inplace=True)

    result.name = f"TFCENTROID_{length}"
    result.category = "statistics"

    return result


tf_centroid_20.__doc__ = \
"""Temporal Centroid of Squared Returns (TFCENTROID)

The energy-weighted mean position of the last `length` bars' simple
returns, on a 0..1 time axis where 0 is the oldest bar in the window and 1
is the current bar. A value near 1 means the largest moves (up or down)
happened recently; near 0 means they happened early in the window; 0.5 is
a flat or time-symmetric energy profile. The window needs every bar, so
one gap blanks its own output and the next `length` bars.

Source: TSFEL (Fraunhofer Portugal AICOS, BSD-3-Clause),
https://github.com/fraunhoferportugal/tsfel,
`tsfel/feature_extraction/features.py` `calc_centroid`:
`sum(t * x^2) / sum(x^2)`. TSFEL's `t` runs `0..length-1`; this port
rescales it to `0..1` so the column does not grow with `length`, following
the scale-free form prototyped at `docs/issues/screen/ind_screen_r2.py`
(candidate `tf_centroid_20`, local to the owner's machine).

Calculation:
    Default Inputs:
        length=20
    RET = close / close[1] - 1
    T = 0..(length-1) / (length-1)          # 0..1, oldest first
    TFCENTROID = SUM(T * RET^2, length) / SUM(RET^2, length)
    NaN where the window's return energy is 0 (all-zero returns)

Args:
    close (pd.Series): Series of 'close's
    length (int): Rolling window. Default: 20
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)

Returns:
    pd.Series: TFCENTROID_{length}
"""
