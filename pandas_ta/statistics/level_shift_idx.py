# -*- coding: utf-8 -*-
import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from pandas import Series

from pandas_ta.utils import get_offset, verify_series

WINDOW_SIZE = 20  # Kats' default `window_size` for the sliding means
# WINDOW_SIZE + 2 closes give exactly 3 sliding means, hence 2 diffs between
# them, so `d.shape[1] - 1` (the idx scale's denominator) is >= 1: no 0/0.
MIN_LENGTH = WINDOW_SIZE + 2
# Diffs are rounded before argmax so a tied maximum (two windows whose
# WINDOW_SIZE-bar means move by the same tick-rounded amount, common in real
# price data) picks the same index under a price rescale instead of flipping
# on the last-bit rounding noise `np.log` introduces at a different scale.
ROUND_DECIMALS = 12
CHUNK_CELLS = 1 << 18  # window cells per evaluation chunk


def _level_shift_idx_rows(chunk):
    """Kats `get_level_shift_features`'s `argmax` on each row: slide a
    WINDOW_SIZE-wide mean across the row, take the absolute diffs between
    consecutive means, and return the (rounded-tiebreak) argmax scaled to
    [0, 1] by the number of diffs minus one (1 = the last diff, i.e. the
    most recent window boundary)."""
    cs = np.cumsum(np.pad(chunk, ((0, 0), (1, 0))), axis=1)
    means = (cs[:, WINDOW_SIZE:] - cs[:, :-WINDOW_SIZE]) / WINDOW_SIZE
    d = np.round(np.abs(np.diff(means, axis=1)), ROUND_DECIMALS)
    return np.argmax(d, axis=1) / (d.shape[1] - 1)


def level_shift_idx(close, length=None, offset=None, **kwargs):
    """Indicator: Position of the largest level shift (LEVELSHIFTIDX)"""
    # Validate Arguments
    length = int(length) if length and int(length) >= MIN_LENGTH else 100
    close = verify_series(close, length)
    offset = get_offset(offset)

    if close is None: return

    # Calculate Result
    c = close.to_numpy(dtype=float)
    # A close that is not a finite positive float is bad data: missing.
    c = np.where(np.isfinite(c) & (c > 0), c, np.nan)
    with np.errstate(invalid="ignore", divide="ignore"):
        logc = np.log(c)

    # Bar T reads closes T - length + 1 .. T, one window at a time,
    # evaluated in chunks so memory does not grow with n * length. A window
    # holding any bad close is excluded by `ok` below -- never fed to
    # `_level_shift_idx_rows` -- and written as NaN directly: `np.argmax`
    # returns the INDEX of a NaN, not a NaN, so letting one through would
    # silently produce a bogus non-NaN idx rather than blanking the window.
    win = sliding_window_view(logc, length)
    step = max(1, CHUNK_CELLS // length)
    values = np.full(c.size, np.nan)
    for start in range(0, win.shape[0], step):
        chunk = win[start:start + step]
        ok = ~np.isnan(chunk).any(axis=1)
        rows = np.full(chunk.shape[0], np.nan)
        if ok.any():
            rows[ok] = _level_shift_idx_rows(chunk[ok])
        lo = length - 1 + start
        values[lo:lo + rows.size] = rows

    idx = Series(values, index=close.index)

    # Offset
    if offset != 0:
        idx = idx.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        idx.fillna(kwargs["fillna"], inplace=True)

    # Name and Categorize it
    idx.name = f"LEVELSHIFTIDX_{length}"
    idx.category = "statistics"

    return idx


level_shift_idx.__doc__ = \
"""Position of the largest level shift (LEVELSHIFTIDX)

Where, inside a rolling window of log close, the biggest jump between two
consecutive 20-bar means sits -- scaled to [0, 1], with 1 meaning the jump is
at the most recent window boundary (closest to bar T) and 0 meaning it is at
the oldest one. A companion of `kats_level_shift_size_100` (issue #162, not
this port): that column is the jump's SIZE; this one is its POSITION.

Source: Kats tsfeatures (Meta, MIT), `get_level_shift_features` (issue #159's
text; Kats' own line numbers are not independently re-confirmed in this
session, no network access to the Kats source): slide a `window_size`-bar
mean across the series, take the absolute differences between consecutive
means, and report `argmax` of those differences (this column) alongside
their `max` (the sibling column, not shipped here). Kats applies it to a
whole series with `window_size=20` by default; the 100-bar outer window and
log close as the input are the choices of the 2026-10-25 screen prototype
(candidate kats_level_shift_idx_100, docs/issues/screen/ind_screen_r5.py,
local to the owner's machine), which also rounds the diffs to 12 decimals
before `argmax` -- kept here, see below.

`window_size` (20) is a fixed module constant (`WINDOW_SIZE`), not a keyword,
matching the prototype's single-candidate shape (only the outer window is
exposed, as `length`, the same convention `stability`/`lumpiness` use for
their own fixed `window_size=20` tiling).

Causal: bar T reads closes T - length + 1 .. T only; the sliding means and
their diffs are built from that window alone. Scale-free: under a price
rescale, `log(close * k) = log(close) + log(k)`, and a diff between two
means cancels any additive constant exactly in exact arithmetic -- so the
diffs, and hence which index is the argmax, are invariant to the window's
overall price level. In finite-precision floats `np.log` does not add that
constant bit-for-bit, so two diffs that are mathematically tied (e.g. two
windows of tick-rounded prices whose 20-bar means step by the same amount)
can differ by rounding noise at the ~1e-15 scale and pick a different
`argmax` at a different price scale. Rounding the diffs to 12 decimals
before `argmax` (the prototype's own device, kept verbatim) absorbs that
noise while leaving genuine level shifts -- orders of magnitude larger in
real log-price data -- untouched; measured bit-identical under x8/x64 (Gate
D). A window with a NaN, zero or negative close is NaN: the calling loop
masks out any window holding one before it ever reaches `argmax`, rather
than relying on NaN to propagate through the reduction (it would not --
`np.argmax` returns the INDEX of a NaN entry, a plain int, not a NaN).

The idx scale's denominator is the number of diffs minus one, so `length`
has a floor of `WINDOW_SIZE + 2` (22): three means, hence two diffs, is the
smallest window that does not divide by zero. A smaller or missing value
falls back to 100, the repo's convention (`kpss`, `arch_lm`, `lumpiness`,
`stability`).

Calculation:
    Default Inputs:
        length=100
    window_size=20 (fixed; see above)
    Y = LN(close)                                   (log closes, the window's own length)
    means[k] = MEAN(Y[k : k + window_size])          for k = 0 .. length - window_size
    d[k] = ROUND(ABS(means[k + 1] - means[k]), 12)   for k = 0 .. length - window_size - 1
    LEVELSHIFTIDX = ARGMAX(d) / (length - window_size - 1)

Args:
    close (pd.Series): Series of 'close's
    length (int): Closes per window. At least WINDOW_SIZE + 2 (22); a
        smaller or missing value falls back to the default. Default: 100
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)

Returns:
    pd.Series: LEVELSHIFTIDX_{length}, in [0, 1] or NaN
"""
