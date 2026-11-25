# -*- coding: utf-8 -*-
import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from pandas import Series

from pandas_ta.utils import get_offset, verify_series

TILE = 20  # Kats' default `window_size`
CHUNK_CELLS = 1 << 18  # window cells per evaluation chunk
# A window whose return sd is at most NOISE_ULPS machine epsilons of its
# largest |1 + r| varies only by the rounding of `c / c1 - 1`: no variation.
NOISE_ULPS = 64


def _tiles(length):
    """(start, stop) of Kats' tiles: `np.array_split(x, len(x) // 20 + 1)`.
    For 100 returns that is 6 tiles of 17, 17, 17, 17, 16, 16 -- not 5 of 20.
    Identical tiling to `lumpiness._tiles`; stability differs only in what
    it reduces each tile to (mean, not variance)."""
    edges = np.cumsum([0] + [len(a) for a in np.array_split(np.arange(length), length // TILE + 1)])
    return list(zip(edges[:-1], edges[1:]))


def _stability_rows(r, tiles):
    """Kats `get_stability` on each row's z-scored returns: the population
    variance of the tiles' means."""
    z = r - r.mean(axis=1, keepdims=True)
    sd = np.sqrt((z * z).mean(axis=1, keepdims=True))
    # No variation, or variation at floating-point rounding level: z-scoring
    # would blow the rounding noise up to unit variance and read it as
    # structure. The rounding of `c / c1 - 1` is absolute -- about eps times
    # |1 + r| -- whatever the size of r, so the floor is too (a steady 1e-10
    # drift is as much noise as a steady 1%). NaN instead. Same guard as
    # `lumpiness`, since it guards the same z-score.
    floor = NOISE_ULPS * np.finfo(float).eps * np.abs(1.0 + r).max(axis=1, keepdims=True)
    real = sd > floor
    with np.errstate(divide="ignore", invalid="ignore"):
        z = z / np.where(real, sd, np.nan)
    m = np.stack([z[:, a:b].mean(axis=1) for a, b in tiles], axis=1)
    return m.var(axis=1)


def stability(close, length=None, offset=None, **kwargs):
    """Indicator: Stability of returns (STABILITY)"""
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
            rows[ok] = _stability_rows(chunk[ok], tiles)
        lo = length + start
        values[lo:lo + rows.size] = rows

    stab = Series(values, index=close.index)

    # Offset
    if offset != 0:
        stab = stab.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        stab.fillna(kwargs["fillna"], inplace=True)

    # Name and Categorize it
    stab.name = f"STABILITY_{length}"
    stab.category = "statistics"

    return stab


stability.__doc__ = \
"""Stability of returns (STABILITY)

How concentrated a persistent directional run is inside a rolling window of
one-bar returns: z-score the window's returns, split them into tiles, take
each tile's mean, and report the variance of those means. Near 0 when every
stretch of the window has about the same (near-zero, after z-scoring) average
return, i.e. no stretch drifts away from the rest; large when one or more
tiles' average return sits far from the others, i.e. a sustained run in one
direction inside an otherwise balanced window.

Source: Kats tsfeatures (Meta, MIT), `get_stability`:
`np.var([np.mean(x_w) for x_w in np.array_split(x, len(x) // 20 + 1)])`,
after Hyndman's tsfeatures `stability`. Kats applies it to a whole series;
the 100-bar window, one-bar returns as the input and z-scoring the window are
the choices of the 2026-10-25 screen prototype (candidate kats_stability_100,
docs/issues/screen/ind_screen_r5.py, local to the owner's machine).
PandasTa issue #158.

The tiles are Kats' `array_split`, identical to `lumpiness`'s (same source
function family, same `window_size=20`): for 100 returns, 6 tiles of 17, 17,
17, 17, 16, 16. Every variance is the population one (`np.var`, ddof 0), and
so is the z-score's standard deviation. `stability` and `lumpiness` share
the same z-scored input and the same tiling; they differ only in what each
tile is reduced to before the outer variance -- mean here, variance there.

Causal: bar T reads closes T - length .. T (`length` returns). Scale-free:
returns are price ratios, exact under a x8/x64 rescale, and z-scoring also
removes the window's overall level and volatility. A window with a NaN, zero
or negative close, or a return whose square overflows, is NaN. So is a
window whose returns do not vary beyond the rounding of `c / c1 - 1`:
standard deviation at most 64 machine epsilons times the window's largest
|1 + r| (about 1.4e-14 for ordinary returns) -- the same guard `lumpiness`
uses, since it guards the identical z-score; unguarded, a steady drift of
any size or a flat price jittering by one ulp would read as a large,
spurious STABILITY (the drift becomes, after z-scoring, exactly the kind of
one-directional run this column is meant to flag in real data). Kats does
not z-score, so it has no such case; the guard belongs to the prototype's
z-scored form. Each window is computed on its own, in chunks, so memory does
not grow with n * length.

Calculation:
    Default Inputs:
        length=100
    r = close / close.shift(1) - 1                (the window's `length` returns)
    z = (r - MEAN(r)) / STDEV(r, ddof=0)
    tiles = array_split(z, length // 20 + 1)
    STABILITY = VAR([MEAN(tile) for tile in tiles])   (ddof 0 throughout)

Args:
    close (pd.Series): Series of 'close's
    length (int): Returns per window. At least 20 (2 tiles); a smaller or
        missing value falls back to the default. Default: 100
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)

Returns:
    pd.Series: STABILITY_{length}, >= 0
"""
