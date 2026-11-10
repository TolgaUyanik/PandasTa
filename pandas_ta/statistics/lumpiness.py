# -*- coding: utf-8 -*-
import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from pandas import Series

from pandas_ta.utils import get_offset, verify_series

TILE = 20  # Kats' default `window_size`
CHUNK_CELLS = 1 << 18  # window cells per evaluation chunk
FLAT_RTOL = 1e-9  # return sd at or below this times the window's RMS return is no variation


def _tiles(length):
    """(start, stop) of Kats' tiles: `np.array_split(x, len(x) // 20 + 1)`.
    For 100 returns that is 6 tiles of 17, 17, 17, 17, 16, 16 -- not 5 of 20."""
    edges = np.cumsum([0] + [len(a) for a in np.array_split(np.arange(length), length // TILE + 1)])
    return list(zip(edges[:-1], edges[1:]))


def _lumpiness_rows(r, tiles):
    """Kats `get_lumpiness` on each row's z-scored returns: the population
    variance of the tiles' population variances."""
    z = r - r.mean(axis=1, keepdims=True)
    sd = np.sqrt((z * z).mean(axis=1, keepdims=True))
    # No variation, or variation at floating-point rounding level (e.g. a
    # steady 1% a bar, whose returns differ by ~1e-14 relative): z-scoring
    # would blow the rounding noise up to unit variance and read it as
    # structure. NaN instead.
    rms = np.sqrt((r * r).mean(axis=1, keepdims=True))
    real = sd > FLAT_RTOL * rms
    with np.errstate(divide="ignore", invalid="ignore"):
        z = z / np.where(real, sd, np.nan)
    v = np.stack([z[:, a:b].var(axis=1) for a, b in tiles], axis=1)
    return v.var(axis=1)


def lumpiness(close, length=None, offset=None, **kwargs):
    """Indicator: Lumpiness of returns (LUMPINESS)"""
    # Validate Arguments
    length = int(length) if length and int(length) >= TILE else 100
    close = verify_series(close, length + 1)
    offset = get_offset(offset)

    if close is None: return

    # Calculate Result
    c = close.to_numpy(dtype=float)
    c = np.where(np.isfinite(c) & (c > 0), c, np.nan)
    with np.errstate(invalid="ignore", divide="ignore", over="ignore"):
        r = c[1:] / c[:-1] - 1.0  # one-bar return; exact under a x2^k rescale
        r[~np.isfinite(r * r)] = np.nan  # an extreme close: missing, not inf

    # Bar T reads the `length` returns ending at T (closes T - length .. T),
    # one window at a time, evaluated in chunks so memory does not grow with
    # n * length. A window holding a NaN return is NaN.
    tiles = _tiles(length)
    win = sliding_window_view(r, length)
    step = max(1, CHUNK_CELLS // length)
    values = np.full(c.size, np.nan)
    for start in range(0, win.shape[0], step):
        chunk = win[start:start + step]
        ok = ~np.isnan(chunk).any(axis=1)
        rows = np.full(chunk.shape[0], np.nan)
        if ok.any():
            rows[ok] = _lumpiness_rows(chunk[ok], tiles)
        lo = length + start
        values[lo:lo + rows.size] = rows

    lump = Series(values, index=close.index)

    # Offset
    if offset != 0:
        lump = lump.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        lump.fillna(kwargs["fillna"], inplace=True)

    # Name and Categorize it
    lump.name = f"LUMPINESS_{length}"
    lump.category = "statistics"

    return lump


lumpiness.__doc__ = \
"""Lumpiness of returns (LUMPINESS)

How unevenly variance is spread inside a rolling window of one-bar returns:
z-score the window's returns, split them into tiles, take each tile's
variance, and report the variance of those variances. Near 0 when every
stretch of the window is about as volatile as the others; large when the
window's variance is concentrated in one or two stretches (a burst of
volatility in an otherwise quiet window).

Source: Kats tsfeatures (Meta, MIT), `get_lumpiness`
(`kats/tsfeatures/tsfeatures.py` L658-673 at commit a6b7e88):
`np.var([np.var(x_w) for x_w in np.array_split(x, len(x) // 20 + 1)])`,
after Hyndman's tsfeatures `lumpiness`. Kats applies it to a whole series;
the 100-bar window, one-bar returns as the input and z-scoring the window
are the choices of the 2026-10-25 screen prototype (candidate
kats_lumpiness_100, docs/issues/screen/ind_screen_r5.py, local to the
owner's machine). PandasTa issue #156.

The tiles are Kats' `array_split`, not fixed blocks of 20: for 100 returns,
6 tiles of 17, 17, 17, 17, 16, 16. Every variance is the population one
(`np.var`, ddof 0), and so is the z-score's standard deviation.

Causal: bar T reads closes T - length .. T (`length` returns). Scale-free:
returns are price ratios, exact under a x8/x64 rescale, and z-scoring also
removes the window's overall volatility level. A window with a NaN, zero or
negative close, or a return whose square overflows, is NaN. So is a window
whose returns do not vary beyond floating-point rounding (standard
deviation at most 1e-9 times their RMS): all zero, or a steady 1% a bar,
whose returns differ by ~1e-14 relative. Without that guard the z-score
would scale rounding noise up to unit variance; measured on 100 * 1.01^t,
it read a median of 0.156 and a maximum of 0.593 out of pure rounding.
Kats does not z-score, so it has no such case; the guard belongs to the
prototype's z-scored form. Each window is computed on its own, in chunks, so memory does
not grow with n * length.

Calculation:
    Default Inputs:
        length=100
    r = close / close.shift(1) - 1                (the window's `length` returns)
    z = (r - MEAN(r)) / STDEV(r, ddof=0)
    tiles = array_split(z, length // 20 + 1)
    LUMPINESS = VAR([VAR(tile) for tile in tiles])   (ddof 0 throughout)

Args:
    close (pd.Series): Series of 'close's
    length (int): Returns per window. At least 20 (2 tiles); a smaller or
        missing value falls back to the default. Default: 100
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)

Returns:
    pd.Series: LUMPINESS_{length}, >= 0
"""
