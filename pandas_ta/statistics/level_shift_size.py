# -*- coding: utf-8 -*-
import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from pandas import Series

from pandas_ta.statistics.level_shift_idx import CHUNK_CELLS, WINDOW_SIZE
from pandas_ta.utils import get_offset, verify_series

# Size needs only one diff (the `max` over however many there are), one
# fewer window bar than its companion `level_shift_idx`'s floor (22): that
# column divides by `(number of diffs) - 1` and needs at least two, this one
# divides by nothing.
MIN_LENGTH = WINDOW_SIZE + 1


def level_shift_size(close, length=None, offset=None, **kwargs):
    """Indicator: Size of the largest level shift (LEVELSHIFTSIZE)"""
    # Validate Arguments
    length = int(length) if length and int(length) >= MIN_LENGTH else 100
    close = verify_series(close, length)
    offset = get_offset(offset)

    if close is None: return

    # Calculate Result
    c = close.to_numpy(dtype=float)
    # A close that is not a finite positive float is bad data: missing.
    c = np.where(np.isfinite(c) & (c > 0), c, np.nan)

    # Bar T reads closes T - length + 1 .. T, one window at a time, chunked
    # so memory does not grow with n * length. A window holding any bad
    # close is excluded by `ok` below and written as NaN directly.
    win = sliding_window_view(c, length)  # raw close, (num_windows, length)
    step = max(1, CHUNK_CELLS // length)
    values = np.full(c.size, np.nan)
    for start in range(0, win.shape[0], step):
        chunk = win[start:start + step]
        ok = ~np.isnan(chunk).any(axis=1)
        rows = np.full(chunk.shape[0], np.nan)
        if ok.any():
            raw = chunk[ok]
            # log(close / the window's own first close), not log(close)
            # directly: under a power-of-two price rescale both the
            # numerator and the denominator are multiplied by the same
            # exactly-representable factor, so the ratio -- and hence every
            # mean, diff and this column's own max -- is bit-identical
            # (the device `stl_spikiness`/`stl_seasonal_strength` use;
            # `level_shift_idx` cannot use it since it reports an index, not
            # a value, and instead rounds before `argmax`).
            with np.errstate(invalid="ignore", divide="ignore"):
                y = np.log(raw / raw[:, :1])
            cs = np.cumsum(np.pad(y, ((0, 0), (1, 0))), axis=1)
            means = (cs[:, WINDOW_SIZE:] - cs[:, :-WINDOW_SIZE]) / WINDOW_SIZE
            d = np.abs(np.diff(means, axis=1))
            rows[ok] = d.max(axis=1)
        lo = length - 1 + start
        values[lo:lo + rows.size] = rows

    size = Series(values, index=close.index)

    # Offset
    if offset != 0:
        size = size.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        size.fillna(kwargs["fillna"], inplace=True)

    # Name and Categorize it
    size.name = f"LEVELSHIFTSIZE_{length}"
    size.category = "statistics"

    return size


level_shift_size.__doc__ = \
"""Size of the largest level shift (LEVELSHIFTSIZE)

The biggest jump between two consecutive 20-bar means inside a rolling
window of log close -- `max |mean(w) - mean(w+1)|` over sliding 20-bar
windows. A companion of `level_shift_idx` (issue #159): that column is the
jump's POSITION (scaled to [0, 1]); this one is its SIZE.

Source: Kats tsfeatures (Meta, MIT), `get_level_shift_features` (issue
#163's text; Kats' own line numbers are not independently re-confirmed in
this session, no network access to the Kats source): slide a `window_size`-
bar mean across the series, take the absolute differences between
consecutive means, and report the `max` of those differences (this column)
alongside their `argmax` (the sibling column, `level_shift_idx`). Kats
applies it to a whole series with `window_size=20` by default; the 100-bar
outer window and log close as the input are the choices of the 2026-10-25
screen prototype (candidate kats_level_shift_size_100,
docs/issues/screen/ind_screen_r5.py, local to the owner's machine).

`window_size` (20) is a fixed module constant (`WINDOW_SIZE`, imported from
`level_shift_idx` rather than redefined), not a keyword, matching the
prototype's single-candidate shape and the sibling column's own convention.

Causal: bar T reads closes T - length + 1 .. T only; the sliding means and
their diffs are built from that window alone. Scale-free: a diff between
two means of `log(close)` cancels any additive constant exactly in exact
arithmetic, so the diffs -- and this column's max of them -- are invariant
to the window's overall price level. Unlike `level_shift_idx` (whose output
is a scale-invariant INDEX, stabilised against float rounding noise by
rounding the diffs before `argmax`), this column's output is the diff VALUE
itself, so the same rounding trick would blunt genuine small shifts rather
than only absorbing noise. Instead the window is fed
`log(close / the window's own first close)`, not `log(close)` directly: the
two are the same value up to an additive constant per window (which cancels
in every diff regardless), but under a power-of-two price rescale the ratio
is bit-identical -- the numerator and denominator are both multiplied by
the same exactly-representable factor, so IEEE-754 division returns the
same bits -- and so is `np.log` of it, and everything computed from it;
measured bit-identical under x8/x64 (Gate D). A window with a NaN, zero or
negative close is NaN: the calling loop masks out any window holding one
before it ever reaches the mean/diff/max computation.

`length` has a floor of `WINDOW_SIZE + 1` (21): one diff (two means) is the
smallest window this column needs, one fewer than `level_shift_idx`'s floor
of 22 (that column additionally divides by the diff count minus one). A
smaller or missing value falls back to 100, the repo's convention (`kpss`,
`arch_lm`, `lumpiness`, `stability`, `level_shift_idx`).

Calculation:
    Default Inputs:
        length=100
    window_size=20 (fixed; see above)
    Y = LN(close / close[T - length + 1])            (log closes, relative to the window's own first bar)
    means[k] = MEAN(Y[k : k + window_size])          for k = 0 .. length - window_size
    d[k] = ABS(means[k + 1] - means[k])              for k = 0 .. length - window_size - 1
    LEVELSHIFTSIZE = MAX(d)

Args:
    close (pd.Series): Series of 'close's
    length (int): Closes per window. At least WINDOW_SIZE + 1 (21); a
        smaller or missing value falls back to the default. Default: 100
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)

Returns:
    pd.Series: LEVELSHIFTSIZE_{length}, >= 0 or NaN
"""
