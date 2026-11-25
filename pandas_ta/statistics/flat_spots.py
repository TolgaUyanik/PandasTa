# -*- coding: utf-8 -*-
import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from pandas import Series

from pandas_ta.utils import get_offset, verify_series

CHUNKS = 10  # Kats' n // 10 chunks
# A chunk of 1 bar has no adjacent pair to compare, so every window would
# read the constant 1. Two bars per chunk (length 20) is the smallest that
# can ever read anything else.
MIN_LENGTH = 2 * CHUNKS
CHUNK_CELLS = 1 << 18  # window cells per evaluation chunk


def _flat_spots_rows(W: np.ndarray) -> np.ndarray:
    """Kats `get_flat_spots` on each row of a close window: split it into
    `CHUNKS` equal-size chunks (dropping any remainder bars -- the newest
    ones in the window, closest to bar T, since the chunks are cut from
    the window's start), and inside each chunk find the longest run of
    consecutive *identical* values. Report 1 + the longest run seen in any
    chunk -- a run of `m` equal adjacent pairs is `m + 1` identical bars."""
    k = W.shape[1] // CHUNKS
    C = W[:, :CHUNKS * k].reshape(W.shape[0], CHUNKS, k)
    eq = C[:, :, 1:] == C[:, :, :-1]
    run = np.zeros(eq.shape[:2])
    best = np.zeros(eq.shape[:2])
    for j in range(eq.shape[2]):
        run = np.where(eq[:, :, j], run + 1, 0)
        best = np.maximum(best, run)
    return best.max(axis=1) + 1.0


def flat_spots(close, length=None, offset=None, **kwargs):
    """Indicator: Flat spots of close (FLATSPOTS)"""
    # Validate Arguments
    length = int(length) if length and int(length) >= MIN_LENGTH else 100
    close = verify_series(close, length)
    offset = get_offset(offset)

    if close is None: return

    # Calculate Result
    c = close.to_numpy(dtype=float)
    # A close that is not finite (NaN or +-inf) is bad data: missing. Unlike
    # `inf == inf` (True in IEEE 754), a missing bar must never read as a
    # repeat, so it is masked out below rather than left to compare itself.
    c = np.where(np.isfinite(c), c, np.nan)

    # Bar T reads closes T - length + 1 .. T, one window at a time,
    # evaluated in chunks so memory does not grow with n * length. A window
    # holding any bad close is excluded by `ok` below -- `==` never
    # propagates NaN the way arithmetic does (NaN == NaN is False), so
    # letting one through would silently count it as "not equal to its
    # neighbour" rather than blanking the window.
    win = sliding_window_view(c, length)
    step = max(1, CHUNK_CELLS // length)
    values = np.full(c.size, np.nan)
    for start in range(0, win.shape[0], step):
        chunk = win[start:start + step]
        ok = ~np.isnan(chunk).any(axis=1)
        rows = np.full(chunk.shape[0], np.nan)
        if ok.any():
            rows[ok] = _flat_spots_rows(chunk[ok])
        lo = length - 1 + start
        values[lo:lo + rows.size] = rows

    fs = Series(values, index=close.index)

    # Offset
    if offset != 0:
        fs = fs.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        fs.fillna(kwargs["fillna"], inplace=True)

    # Name and Categorize it
    fs.name = f"FLATSPOTS_{length}"
    fs.category = "statistics"

    return fs


flat_spots.__doc__ = \
"""Flat spots of close (FLATSPOTS)

Over a rolling window of closes, split the window into 10 equal-size
chunks and, inside each chunk, find the longest run of consecutive bars
whose close did not change at all. Report 1 plus the longest such run seen
in any of the 10 chunks, so the value ranges from 1 (every bar in every
chunk differs from its neighbour) to the chunk size (one chunk is flat
start to end). A tick-rounded price that prints the same close for several
bars in a row reads high; a continuously-varying close reads 1 almost
everywhere.

Source: Kats tsfeatures (Meta, MIT), `get_flat_spots` (issue #161's text;
Kats' own line numbers are not independently re-confirmed in this session,
no network access to the Kats source): "max groupby run length per n/10
chunk" -- the series is split into `len(x) // 10` equal time chunks, and
the feature is the longest run of identical consecutive values seen in any
chunk, after Hyndman's tsfeatures `flat_spots` (R `tsfeatures`, which cuts
the series into 10 equal-width VALUE bins over its whole range rather than
equal-size TIME chunks; Kats' own description, "per n/10 chunk", is the
time-chunked form this module ports). Kats applies it to a whole series;
the 100-bar window and close itself (no returns, no log) as the input are
the choices of the 2026-10-25 screen prototype (candidate
kats_flat_spots_100, docs/issues/screen/ind_screen_r5.py, local to the
owner's machine, lines 107-116), whose own `_flat_spots` this module
reproduces: `C = W[:, :10*k].reshape(len(W), 10, k)`, `eq = C[:, :,
1:] == C[:, :, :-1]`, max running length of `eq` per chunk, `+ 1`, then the
max over chunks.

Causal: bar T reads closes T - length + 1 .. T only, each window computed
on its own. Scale-free, and more strongly than a ratio-based column: `==`
is a deterministic function of its two operands' bits, so if `a == b`
before a uniform rescale then `a * k == b * k` after it for ANY finite `k`
-- not only a power of two -- as long as neither operand under/overflows.
Measured bit-identical under x8/x64 AND x10/x3.7 (Gate D). A window with a
non-finite close (NaN or +-inf) is NaN; zero and negative closes are valid
values for equality (the column never divides).

The chunks span the window's first `CHUNKS * (length // CHUNKS)` bars; its
newest `length % CHUNKS` bars (closest to bar T) are dropped and never
checked for a flat run, when `length` is not a multiple of 10 -- for the
default length=100 there is no remainder. `length` has a floor of
2 * CHUNKS (20): a 1-bar chunk has no adjacent pair to compare, so every
window would read the constant 1 and the column would fail the "not
constant" requirement of Gate D. A smaller or missing value falls back to
100, the repo's convention (`kpss`, `stability`, `level_shift_idx`).

Calculation:
    Default Inputs:
        length=100
    k = length // 10                                (chunk size; 10 for length=100)
    chunks = split closes[T - length + 1 .. T] into 10 chunks of k bars
    FLATSPOTS = 1 + max over chunks of (longest run of adjacent closes[i] == closes[i-1] inside the chunk)

Args:
    close (pd.Series): Series of 'close's
    length (int): Closes per window. At least 2 * CHUNKS (20); a smaller
        or missing value falls back to the default. Default: 100
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)

Returns:
    pd.Series: FLATSPOTS_{length}, a whole number in [1, length // 10] or NaN
"""
