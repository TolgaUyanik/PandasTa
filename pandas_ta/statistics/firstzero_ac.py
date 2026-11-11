# -*- coding: utf-8 -*-
import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from pandas import Series

from pandas_ta.utils import get_offset, verify_series

# A window whose return sd is at most NOISE_ULPS machine epsilons of its
# largest |1 + r| varies only by the rounding of `c / c1 - 1`: no variation.
NOISE_ULPS = 64
CHUNK_CELLS = 1 << 18  # window cells per evaluation chunk
MIN_LENGTH = 5  # Kats' `transform` refuses fewer points (tsfeatures.py L502)


def _next_regular(target):
    """statsmodels' `_next_regular` (compat/scipy.py L17): the smallest
    5-smooth number >= target, the FFT length `acovf` pads to."""
    if target <= 6 or not (target & (target - 1)):
        return target
    best = float("inf")
    p5 = 1
    while p5 < target:
        p35 = p5
        while p35 < target:
            quotient = -(-target // p35)
            p2 = 2 ** ((quotient - 1).bit_length())
            n = p2 * p35
            if n == target:
                return n
            best = min(best, n)
            p35 *= 3
            if p35 == target:
                return p35
        best = min(best, p35)
        p5 *= 5
        if p5 == target:
            return p5
    return min(best, p5)


def _firstzero_rows(r):
    """Kats `get_special_ac` -> `firstzero_ac` on each row of returns `r`:
    `AC = acf(x, fft=True, nlags=len(x))[1:]`, then the first j with
    AC[j] > 0 and AC[j + 1] < 0, reported as j + 2 (the lag of that first
    negative autocorrelation), or len(x) when there is none."""
    m = r.shape[1]
    # statsmodels acovf, fft=True, demean, not adjusted: the same padding,
    # transform and divisor, so the signs are Kats' own.
    xo = r - r.mean(axis=1, keepdims=True)
    f = np.fft.fft(xo, n=_next_regular(2 * m + 1), axis=1)
    acov = np.fft.ifft(f * np.conjugate(f), axis=1)[:, :m].real / m
    # No variation, or variation at floating-point rounding level: every
    # autocorrelation would be that of rounding noise, and its sign is
    # arbitrary. The rounding of `c / c1 - 1` is absolute -- about eps times
    # |1 + r| -- whatever the size of r, so the floor is too. NaN instead.
    sd = np.sqrt(acov[:, 0])
    floor = NOISE_ULPS * np.finfo(float).eps * np.abs(1.0 + r).max(axis=1)
    real = sd > floor
    with np.errstate(divide="ignore", invalid="ignore"):
        ac = acov[:, 1:] / acov[:, :1]  # acf(...)[1:]: lags 1 .. m - 1
    hit = (ac[:, :-1] > 0) & (ac[:, 1:] < 0)
    j = np.where(hit.any(axis=1), hit.argmax(axis=1), m - 2)
    return np.where(real, j + 2.0, np.nan)


def firstzero_ac(close, length=None, offset=None, **kwargs):
    """Indicator: First zero crossing of the return autocorrelation (FIRSTZEROAC)"""
    # Validate Arguments
    length = int(length) if length and int(length) >= MIN_LENGTH else 100
    close = verify_series(close, length + 1)
    offset = get_offset(offset)

    if close is None: return

    # Calculate Result
    c = close.to_numpy(dtype=float)
    # A close that is not a finite, normal positive float (NaN, inf, zero,
    # negative, or subnormal such as 1e-310) is bad data: missing.
    c = np.where(np.isfinite(c) & (c >= np.finfo(float).tiny), c, np.nan)
    with np.errstate(invalid="ignore", divide="ignore", over="ignore"):
        r = c[1:] / c[:-1] - 1.0  # one-bar return; exact under a x2^k rescale
        r[~np.isfinite(r * r)] = np.nan  # an extreme close: missing, not inf

    # Bar T reads the `length` returns ending at T (closes T - length .. T),
    # one window at a time, evaluated in chunks so memory does not grow with
    # n * length. A window holding a NaN return is NaN.
    win = sliding_window_view(r, length)
    step = max(1, CHUNK_CELLS // length)
    values = np.full(c.size, np.nan)
    for start in range(0, win.shape[0], step):
        chunk = win[start:start + step]
        ok = ~np.isnan(chunk).any(axis=1)
        rows = np.full(chunk.shape[0], np.nan)
        if ok.any():
            rows[ok] = _firstzero_rows(chunk[ok])
        lo = length + start
        values[lo:lo + rows.size] = rows

    fz = Series(values, index=close.index)

    # Offset
    if offset != 0:
        fz = fz.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        fz.fillna(kwargs["fillna"], inplace=True)

    # Name and Categorize it
    fz.name = f"FIRSTZEROAC_{length}"
    fz.category = "statistics"

    return fz


firstzero_ac.__doc__ = \
"""First zero crossing of the return autocorrelation (FIRSTZEROAC)

Over a rolling window of one-bar returns, take the sample autocorrelation
at every lag 1 .. length - 1 and report the first lag whose autocorrelation
is negative right after a positive one: the lag k with AC(k - 1) > 0 and
AC(k) < 0, the smallest such k. A window with no such pair reads `length`.
The value is a whole number from 2 to length.

Measured on synthetic paths only (docs/FirstzeroAcMeasured.md): it reads
how long returns stay positively autocorrelated. Sine returns of period P
read about the first lag above P / 4 (P = 22 reads 6). AR(1) returns read a
median of 14 at phi = 0.9 and 6 at phi = 0.6, but 3 at phi = 0.3, 0 and
-0.3: below strong persistence it does not order the autocorrelation, and its
Spearman with the window's lag-1 return autocorrelation is 0.02. For iid
returns its p10 to p90 is 2 to 7, and it changes on about 1 bar in 9.

A window whose returns are zero except for one move has no crossing (every
autocorrelation is negative), so it reads `length`. On returns that move
on only 2% of bars, 36% of the bars that fire read `length`; at 5%, 3%.

Source: Kats tsfeatures (Meta, MIT), `get_special_ac` -> `firstzero_ac`
(`kats/tsfeatures/tsfeatures.py` L1293-1340, L1316 and L1331-1338 at commit
a6b7e88): `AC = acf(x, fft=True, nlags=len(x))[1:]`, then
`while j < len(AC) - 1: if AC[j] > 0 and AC[j + 1] < 0: break`, returning
`j + 2`. statsmodels 0.15.0 `tsa/stattools/_stattools.py`: `acf` L847
(`avf[: nlags + 1] / avf[0]`, L1013; `nlags = len(x)` is truncated to the
len(x) - 1 lags `acovf` returns), `acovf` L488 (demeaned once, divisor n,
FFT padded to `_next_regular(2n + 1)`, L609-613). The module repeats that
FFT, so its autocorrelations are statsmodels' to rounding and the signs
Kats compares are the same. Kats applies it to a whole series; the 100-bar
window and one-bar returns as the input are the choices of the 2026-10-25
screen prototype (candidate kats_firstzero_ac_100,
docs/issues/screen/ind_screen_r5.py, local to the owner's machine).
PandasTa issue #152.

Not Hyndman's `firstzero_ac`, which is the first lag whose autocorrelation
is negative at all: Kats needs a positive lag in front of it, so a window
whose lag-1 autocorrelation is already negative reads a later lag.

Causal: bar T reads closes T - length .. T (`length` returns). Scale-free:
returns are price ratios, exact under a x8/x64 rescale. A window with a
close that is NaN, infinite, zero, negative or subnormal (below 2.2e-308),
or a return whose square overflows, is NaN. So is a window whose returns
do not vary beyond the rounding of `c / c1 - 1`: standard deviation at most
64 machine epsilons times the window's largest |1 + r| (about 1.4e-14 for
ordinary returns) -- all-zero returns, a steady drift of any size, or a
flat price jittering by one ulp. Kats returns `length` on a constant
series (every autocorrelation is NaN, so no lag passes the test) and
otherwise reports the sign pattern of the rounding noise. Each window is
computed on its own, in chunks, so memory does not grow with n * length.

Calculation:
    Default Inputs:
        length=100
    r = close / close.shift(1) - 1                (the window's `length` returns)
    AC(k) = acovf(r)[k] / acovf(r)[0],  k = 1 .. length - 1  (demeaned, divisor n)
    FIRSTZEROAC = min{k >= 2 : AC(k - 1) > 0 and AC(k) < 0}, else length

Args:
    close (pd.Series): Series of 'close's
    length (int): Returns per window. At least 5 (Kats' `transform` refuses
        a shorter series); a smaller or missing value falls back to the
        default. Default: 100
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)

Returns:
    pd.Series: FIRSTZEROAC_{length}, a whole number in [2, length]
"""
