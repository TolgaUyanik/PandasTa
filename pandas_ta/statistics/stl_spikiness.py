# -*- coding: utf-8 -*-
import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from pandas import Series

from pandas_ta.statistics.stl_seasonal_strength import (
    CHUNK_CELLS, MIN_LENGTH, NOISE_ULPS, _build_ops,
)
from pandas_ta.utils import get_offset, verify_series


def stl_spikiness(close, length=None, offset=None, **kwargs):
    """Indicator: STL residual spikiness of log price (STLSPIKE)"""
    # Validate Arguments
    length = int(length) if length and int(length) >= MIN_LENGTH else 100
    close = verify_series(close, length)
    offset = get_offset(offset)

    if close is None: return

    # Calculate Result
    c = close.to_numpy(dtype=float)
    # A close that is not a finite, normal positive float is bad data: missing.
    c = np.where(np.isfinite(c) & (c >= np.finfo(float).tiny), c, np.nan)

    seasonal_op, trend_op = _build_ops(length)
    win = sliding_window_view(c, length)  # (num_windows, length), raw close
    n = length
    m = n - 1  # leave-one-out sub-array size

    step = max(1, CHUNK_CELLS // length)
    values = np.full(c.size, np.nan)
    for start in range(0, win.shape[0], step):
        raw = win[start:start + step]
        # log(close / the window's own first close), not log(close) directly:
        # see pandas_ta.statistics.stl_seasonal_strength (the same device, for
        # the same bit-identity reason -- Decision 1 in this module's own
        # Measured doc).
        with np.errstate(invalid="ignore", divide="ignore"):
            chunk = np.log(raw / raw[:, :1])
        std = chunk.std(axis=1)
        rmax = np.abs(chunk).max(axis=1)
        real = std > NOISE_ULPS * np.finfo(float).eps * (1.0 + rmax)
        s = chunk @ seasonal_op.T
        t = chunk @ trend_op.T
        r = chunk - s - t  # residual, (rows, length)

        # Leave-one-out population variance (ddof=0) of the residual, in
        # closed form rather than an O(length^2) loop per window: dropping
        # element i leaves sum = S1 - r_i and sumsq = S2 - r_i**2 over the
        # remaining (length - 1) elements, so its mean and variance follow
        # directly. Equivalent to `np.nanvar(np.delete(r, i))` for every i,
        # checked against that brute-force form in
        # tests/test_stl_spikiness.py.
        s1 = r.sum(axis=1, keepdims=True)
        s2 = (r * r).sum(axis=1, keepdims=True)
        loo_mean = (s1 - r) / m
        loo_var = (s2 - r * r) / m - loo_mean * loo_mean
        with np.errstate(invalid="ignore"):
            spike = loo_var.var(axis=1)  # variance of the leave-one-out variances
        rows = np.where(real, spike, np.nan)
        lo = length - 1 + start
        values[lo:lo + rows.size] = rows

    spikiness = Series(values, index=close.index)

    # Offset
    if offset != 0:
        spikiness = spikiness.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        spikiness.fillna(kwargs["fillna"], inplace=True)

    # Name and Categorize it
    spikiness.name = f"STLSPIKE_{length}"
    spikiness.category = "statistics"

    return spikiness


stl_spikiness.__doc__ = \
"""STL residual spikiness of log price (STLSPIKE)

The variance of the leave-one-out residual variances of a rolling window of
log close, from an STL (Seasonal-Trend decomposition using LOESS) fit of the
window with a 5-bar (trading-week) period: for each bar `i` of the window's
residual, the (population) variance of the residual with bar `i` removed,
then the variance of THAT length-`length` array of leave-one-out variances.
A single outlier residual moves many of the leave-one-out variances by a lot
when it is the one dropped, so a window with one or a few spikes in an
otherwise quiet residual reads high; a residual whose points are all of a
similar size (no single dominant spike) reads near zero regardless of its
overall level, since dropping any one point then changes every leave-one-out
variance by about the same small amount.

Source: Kats tsfeatures (Meta, MIT), `get_stl_features`:
`var(nanvar of leave-one-out resid)` (issue #162's text; Kats' own
`get_stl_features` control flow -- which STL parameters it passes, if any
beyond `period` -- is not independently re-confirmed in this session, no
network access to the Kats source). Kats applies it to a whole series; the
100-bar window, log close as the input, and period 5 are the choices of the
2026-10-25 screen prototype (candidate kats_stl_spike_100,
docs/issues/screen/ind_screen_r5.py, local to the owner's machine), which
calls `statsmodels.tsa.seasonal.STL(window, period=5).fit()` -- i.e.
`robust=False` and every other STL parameter at its statsmodels default.

STL itself (not shipped: `statsmodels` is a dev-only dependency, see
`setup.py`) is Cleveland, Cleveland, McRae & Terpenning (1990), J. Official
Statistics 6, 3-73 -- an iterated LOESS decomposition into trend, a
repeating seasonal shape and a residual. This module reuses
`pandas_ta.statistics.stl_seasonal_strength`'s from-scratch numpy
reimplementation of that decomposition (`_build_ops`, and the constants it
derives from: `PERIOD=5`, `SEASONAL=7`, `TREND=11`, `LOW_PASS=7`,
`INNER_ITER=5`) rather than duplicating it -- a second, independently
maintained copy of the same LOESS/cycle-subseries/low-pass math would be a
correctness risk of its own (the two copies drifting), not a benefit; the
fork's own `sk_fcb_pos.py` imports private helpers from `sk_fcb_width.py`
the same way. Unlike `stl_seasonal_strength`/`stl_trend_strength`, this
module needs the residual alone (`r = Y - S - T`), not a ratio against
`S` or `T`. Checked against statsmodels' own STL plus a brute-force
`np.delete`/`np.nanvar` leave-one-out loop as the oracle in
tests/test_stl_spikiness.py / docs/measure_stl_spikiness.py.

The leave-one-out variance array is computed in closed form rather than by
looping `np.delete(r, i)` for every `i` (which the oracle test does, as the
independent check): for a length-`n` residual with sum `S1` and sum of
squares `S2`, dropping element `i` leaves `n - 1` elements with sum
`S1 - r_i` and sum of squares `S2 - r_i**2`, so that sub-array's own
(population, ddof=0) mean and variance follow directly -- no need to
re-sum `n - 1` elements from scratch for every `i`. With `robust=False`,
STL's robustness weights never leave 1, so every step of the decomposition
(detrending, cycle-subseries LOESS, low-pass filtering, deseasonalising,
trend LOESS) is a LINEAR function of the window's own values, with weights
that depend only on the window length and the fixed period/seasonal/trend/
low-pass windows, never on the data -- the same fact `stl_seasonal_strength`
and `stl_trend_strength` use to collapse the 5-iteration inner loop to two
fixed `length x length` matrices (`_build_ops`), applied here to get the
residual `r` by a single matrix multiply per window.

Causal: bar T reads closes T - length + 1 .. T only -- every element of the
two fixed operators is a function of position within the window alone, so
the matrix multiply cannot read a future bar, and the leave-one-out/variance
arithmetic that follows reads only that window's own residual. Scale-free:
STL is fed `log(close / the window's own first close)`, not `log(close)`
directly (kpss.py's and stl_seasonal_strength.py's same device) --
mathematically the same input up to an additive constant per window, which
STL's trend LOESS (degree 1, so it reproduces an added constant exactly)
absorbs, leaving the residual -- and so every variance computed from it --
unchanged. Under a power-of-two price rescale the residual itself is
bit-identical (the numerator and denominator inside the log are both
multiplied by an exactly-representable factor, so the ratio's correctly-
rounded result does not move), and so is everything downstream, since the
two fixed operators and the subsequent closed-form arithmetic then see an
identical bit pattern: measured bit-identical under x8/x64, within
tolerance under x10/x3.7 (not powers of two, so not bit-exact) -- see Gate
D. A window with a close that is NaN, infinite, zero, negative or subnormal
(below 2.2e-308) is NaN (the bad value poisons every output of the matrix
multiply and the arithmetic that follows: `0 * NaN = NaN` under IEEE 754,
regardless of the multiplying weight). So is a window whose log closes do
not vary beyond the rounding of `log(close)` (a flat price, or one-ulp
float jitter around one): standard deviation at most 64 machine epsilons
times (1 + the window's largest |log close|) -- the same `NOISE_ULPS` guard
`stl_seasonal_strength` uses, imported rather than re-derived, applied here
for the same reason as its siblings: without it, a flat/jittery window's
near-zero residual would read as a near-zero (but not exactly reproducible)
spikiness rather than as missing data. Unlike diff1_pacf5/diff2_acf1's
guard on returns, this does not blank a smooth deterministic drift -- STL
reads log-close levels directly, where a drift's values genuinely vary, and
a noiseless drift's residual (and so its spikiness) is ~0 regardless
(measured in docs/measure_stl_spikiness.py).

Calculation:
    Default Inputs:
        length=100
    period=5, seasonal=7, trend=11, low_pass=7 (fixed; see above)
    Y = LN(close / close[T - length + 1])      (log closes, relative to the window's own first bar)
    T, S = STL(Y; period, seasonal, trend, low_pass, degree=1 throughout,
               inner_iter=5, outer_iter=0)      (trend, seasonal; via the two
                                                  fixed linear operators above)
    R = Y - T - S                              (residual, one value per window bar)
    V[i] = VAR(R with R[i] removed), for every i in the window   (leave-one-out variances)
    STLSPIKE = VAR(V)

Args:
    close (pd.Series): Series of 'close's
    length (int): Closes per window. At least 50 (10 full 5-bar cycles, see
        MIN_LENGTH); a smaller or missing value falls back to the default.
        Default: 100
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)

Returns:
    pd.Series: STLSPIKE_{length}
"""
