# -*- coding: utf-8 -*-
import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from pandas import Series

from pandas_ta.utils import get_offset, verify_series

PERIOD = 5    # Kats candidate's own choice: a trading week
SEASONAL = 7  # statsmodels STL default seasonal-smoother window (odd, >= 7)
# statsmodels STL: trend window = smallest odd integer > 1.5 * PERIOD / (1 - 1.5 / SEASONAL)
# = smallest odd integer > 1.5*5 / (1 - 1.5/7) = smallest odd integer > 9.545... = 11
TREND = 11
# statsmodels STL: low-pass window = smallest odd integer > PERIOD = smallest odd integer > 5 = 7
LOW_PASS = 7
INNER_ITER = 5  # statsmodels STL fit() default inner_iter when robust=False (ours is)
# A window whose log closes do not vary beyond the rounding of log(c) is a
# flat price, not a real cycle: var(seasonal + resid) would be a rounding
# artifact and the ratio meaningless (0/0 in the exact-flat case). Unlike
# diff1_pacf5/diff2_acf1's guard on RETURNS, this does not catch a smooth
# deterministic drift -- STL reads log close levels directly, and a drift's
# log-close values genuinely vary (a straight line is not noise); measured
# in docs/measure_stl_seasonal_strength.py: every drift case still fires,
# with ordinary-looking values, while a flat price and one-ulp jitter do not.
NOISE_ULPS = 64
CHUNK_CELLS = 1 << 16  # window cells per evaluation chunk
# 10 full 5-bar cycles, so each of the 5 weekday subseries has at least 10
# points -- comfortably above the 7-point seasonal smoother this port's own
# loess needs (see _build_ops). Kats' own minimum for get_stl_features is
# not independently confirmed in this session (no network access).
MIN_LENGTH = 50

_OP_CACHE = {}  # length -> (seasonal operator, trend operator), both length x length


def _loess_weights(n, xin, xout, q, degree=1):
    """Row `i` holds the weights of a degree-`degree` local (tri-cube
    weighted) regression smoother evaluated at `xout[i]`, over data at
    integer positions `xin` (0..n-1): `smoothed[i] = weights[i] @ y`. Window
    width `q` (<= n; the caller must guarantee this -- see module docstring).
    `xout` entries may lie outside `0..n-1` (the one-point extrapolation
    STL's cycle-subseries smoothing needs); the window is still chosen from
    the n in-range points nearest the window's own clamped centre, and the
    tri-cube weights/regression use the true (possibly out-of-range) `xout`
    distance, so the fit extrapolates rather than clamping the value.
    Cleveland, Cleveland, McRae & Terpenning (1990), J. Official Statistics
    6, the LOESS step of the STL algorithm (also used, unweighted here,
    since STL's default `robust=False` keeps every robustness weight at 1)."""
    assert q <= n, (q, n)
    m = (q - 1) // 2
    out = np.zeros((len(xout), n))
    for i, x0 in enumerate(xout):
        c = int(np.clip(x0, 0, n - 1))
        nleft = max(0, min(c - m, n - q))
        idx = np.arange(nleft, nleft + q)
        d = np.abs(idx - x0)
        h = d.max()
        u = d / h
        w = np.where(u < 1, (1 - u ** 3) ** 3, 0.0)
        wsum = w.sum()
        if degree == 0 or wsum <= 0:
            out[i, idx] = w / wsum
            continue
        xbar = (w * idx).sum() / wsum
        sxx = (w * (idx - xbar) ** 2).sum()
        if sxx <= 0:
            out[i, idx] = w / wsum
        else:
            out[i, idx] = w / wsum + w * (idx - xbar) * (x0 - xbar) / sxx
    return out


def _ma_matrix(n_in, width):
    """A simple (non-weighted) moving average of `width`, as a dense
    `(n_in - width + 1) x n_in` operator."""
    n_out = n_in - width + 1
    m = np.zeros((n_out, n_in))
    for i in range(n_out):
        m[i, i:i + width] = 1.0 / width
    return m


def _cycle_subseries_op(n, p, q):
    """STL step 2 (cycle-subseries smoothing): split the `n`-point series
    into `p` subseries (positions `c, c+p, c+2p, ...`), LOESS-smooth each
    one (degree 1, window `q`) at its own points plus one before the first
    and one after the last, and interleave the results back into a single
    `(n + 2p) x n` operator. Extended position `j` (0 <= j < n+2p) belongs
    to subseries `c = j % p` at local position `j // p - 1`; summing
    `(local length + 2)` over all `p` subseries always totals `n + 2p`, so
    every extended slot is covered exactly once regardless of whether `p`
    divides `n`."""
    ext = n + 2 * p
    op = np.zeros((ext, n))
    for c in range(p):
        idx = np.arange(c, n, p)
        nc = len(idx)
        w = _loess_weights(nc, np.arange(nc), np.arange(-1, nc + 1), q, degree=1)
        rows = c + np.arange(nc + 2) * p
        op[np.ix_(rows, idx)] = w
    return op


def _low_pass_op(n, p, nl):
    """STL step 3 (low-pass filtering of the extended cycle-subseries):
    three moving averages (widths p, p, 3) collapsing `n + 2p` points back
    to `n`, then a degree-1 LOESS of window `nl`. A single `n x (n + 2p)`
    operator."""
    ext = n + 2 * p
    ma = _ma_matrix(ext - 2 * p + 2, 3) @ _ma_matrix(ext - p + 1, p) @ _ma_matrix(ext, p)
    return _loess_weights(n, np.arange(n), np.arange(n), nl, degree=1) @ ma


def _seasonal_op(n):
    """Seasonal component as a linear function of the detrended input:
    `S = seasonal_op @ (Y - T)`. Step 4: the extended cycle-subseries,
    restricted to its middle `n` points (excluding the `p` extra points
    padded on each side), minus the low-pass-filtered version of the same
    extended series."""
    p = PERIOD
    cyc = _cycle_subseries_op(n, p, SEASONAL)  # (n+2p) x n
    mid = np.zeros((n, n + 2 * p))
    mid[:, p:p + n] = np.eye(n)
    return (mid - _low_pass_op(n, p, LOW_PASS)) @ cyc  # n x n


def _build_ops(length):
    """STL's inner loop (`INNER_ITER` passes, `robust=False` so every
    robustness weight is 1 throughout) reduces to two fixed `length x
    length` matrices once `period`/`seasonal`/`trend`/`low_pass` are fixed,
    because with constant weights every step -- detrend, cycle-subseries
    LOESS, low-pass filter, deseasonalise, trend LOESS -- is linear in Y,
    independent of Y's actual values. Writing `T_m = A @ Y + B @ T_(m-1)`
    for one inner pass (`A = trend_op @ (I - seasonal_op)`, `B = trend_op @
    seasonal_op`), `T_m`'s own coefficient matrix is `A + B @ (T_(m-1)'s
    coefficient matrix)`, starting from the zero matrix (`T_0 = 0`); after
    `INNER_ITER` passes that gives the final trend operator directly, and
    the final seasonal operator uses the second-to-last trend operator
    (seasonal is computed from the *previous* iteration's trend inside each
    pass). Cached per `length` since the result does not depend on the
    data, only on the window size."""
    if length in _OP_CACHE:
        return _OP_CACHE[length]
    seasonal_op = _seasonal_op(length)
    trend_loess_op = _loess_weights(length, np.arange(length), np.arange(length), TREND, degree=1)
    identity = np.eye(length)
    a = trend_loess_op @ (identity - seasonal_op)
    b = trend_loess_op @ seasonal_op
    trend_ops = []
    t = np.zeros((length, length))
    for _ in range(INNER_ITER):
        t = a + b @ t
        trend_ops.append(t)
    final_trend_op = trend_ops[-1]
    final_seasonal_op = seasonal_op @ (identity - trend_ops[-2])
    _OP_CACHE[length] = (final_seasonal_op, final_trend_op)
    return final_seasonal_op, final_trend_op


def stl_seasonal_strength(close, length=None, offset=None, **kwargs):
    """Indicator: STL seasonality strength of log price (STLSEAS)"""
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

    step = max(1, CHUNK_CELLS // length)
    values = np.full(c.size, np.nan)
    for start in range(0, win.shape[0], step):
        raw = win[start:start + step]
        # log(close / the window's own first close), not log(close) directly:
        # a power-of-two price rescale multiplies numerator and denominator
        # by the same exact (no-rounding) factor, so the ratio -- and so
        # every downstream matrix multiply, fed the identical bit pattern --
        # is bit-identical to the unscaled run. Mathematically the same
        # STL input as log(close) up to an additive constant per window,
        # which STL's degree-1 trend LOESS absorbs exactly (see docstring).
        with np.errstate(invalid="ignore", divide="ignore"):
            chunk = np.log(raw / raw[:, :1])
        std = chunk.std(axis=1)
        rmax = np.abs(chunk).max(axis=1)
        real = std > NOISE_ULPS * np.finfo(float).eps * (1.0 + rmax)
        s = chunk @ seasonal_op.T
        t = chunk @ trend_op.T
        r = chunk - s - t
        with np.errstate(invalid="ignore", divide="ignore"):
            var_resid = r.var(axis=1)
            var_seas_resid = (s + r).var(axis=1)
            raw = 1 - var_resid / var_seas_resid
        rows = np.where(real & (var_seas_resid > 0), raw, np.nan)
        lo = length - 1 + start
        values[lo:lo + rows.size] = rows

    seas = Series(values, index=close.index)

    # Offset
    if offset != 0:
        seas = seas.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        seas.fillna(kwargs["fillna"], inplace=True)

    # Name and Categorize it
    seas.name = f"STLSEAS_{length}"
    seas.category = "statistics"

    return seas


stl_seasonal_strength.__doc__ = \
"""STL seasonality strength of log price (STLSEAS)

The strength of a 5-bar (trading-week) seasonal cycle in a rolling window of
log close, from an STL (Seasonal-Trend decomposition using LOESS) fit of the
window: `1 - var(resid) / var(seasonal + resid)`. Near 0 means the seasonal
component adds nothing beyond noise; near 1 means most of the window's
non-trend variation repeats on a 5-bar cycle.

Source: Kats tsfeatures (Meta, MIT), `get_stl_features`:
`1 - var(resid) / var(seasonal + resid)` (issue #155's text; Kats' own
`get_stl_features` control flow -- which STL parameters it passes, if any
beyond `period` -- is not independently re-confirmed in this session, no
network access to the Kats source). Kats applies it to a whole series; the
100-bar window, log close as the input, and period 5 are the choices of the
2026-10-25 screen prototype (candidate kats_stl_seas_100,
docs/issues/screen/ind_screen_r5.py, local to the owner's machine), which
calls `statsmodels.tsa.seasonal.STL(window, period=5).fit()` -- i.e.
`robust=False` and every other STL parameter at its statsmodels default.

STL itself (not shipped: `statsmodels` is a dev-only dependency, see
`setup.py`) is Cleveland, Cleveland, McRae & Terpenning (1990), J. Official
Statistics 6, 3-73 -- an iterated LOESS decomposition into trend, a
repeating seasonal shape and a residual. This module reimplements it in
plain numpy, matched against statsmodels' STL as an oracle in
tests/test_stl_seasonal_strength.py (and docs/measure_stl_seasonal_strength.py)
rather than imported, the same approach kpss.py and arch_lm.py take for
their own statsmodels originals.

With `robust=False`, STL's robustness weights never leave 1, so -- a fact
used directly by this implementation, not merely a performance shortcut --
every step of the decomposition (detrending, cycle-subseries LOESS,
low-pass filtering, deseasonalising, trend LOESS) is a LINEAR function of
the window's own values, with weights that depend only on the window length
and the fixed period/seasonal/trend/low-pass windows, never on the data.
The whole 5-iteration inner loop therefore collapses to two fixed `length x
length` matrices -- one for the seasonal component, one for the trend --
computed once per `length` and cached (`_build_ops`), then applied to every
rolling window by a single matrix multiply. Parameters, all statsmodels
STL defaults for `period=5`: seasonal window 7, trend window 11 (smallest
odd integer > 1.5*5/(1-1.5/7)), low-pass window 7 (smallest odd integer >
5), all LOESS degrees 1, `inner_iter=5`, `outer_iter=0` (not robust).

Causal: bar T reads closes T - length + 1 .. T only -- every element of the
two fixed operators is a function of position within the window alone, so
the matrix multiply cannot read a future bar. Scale-free: STL is fed
`log(close / the window's own first close)`, not `log(close)` directly
(kpss.py's same device) -- mathematically the same input up to an additive
constant per window, which STL's trend LOESS (degree 1, so it reproduces
an added constant exactly) absorbs, leaving the seasonal and residual
components -- and so this ratio -- unchanged. Under a power-of-two price
rescale the ratio itself is bit-identical (both the numerator and
denominator are multiplied by an exactly-representable factor, so the
division's true quotient, and its correctly-rounded result, do not move),
and so is everything downstream, since the two fixed operators then see an
identical bit pattern: measured bit-identical under x8/x64, within 1e-10
under x10/x3.7 (not powers of two, so not bit-exact) -- see Gate D. A
window with a close that is
NaN, infinite, zero, negative or subnormal (below 2.2e-308) is NaN (the bad
value poisons every output of the matrix multiply: `0 * NaN = NaN` under
IEEE 754, regardless of the multiplying weight). So is a window whose log
closes do not vary beyond the rounding of `log(close)` (a flat price, or
one-ulp float jitter around one): standard deviation at most 64 machine
epsilons times (1 + the window's largest |log close|). Unlike
diff1_pacf5/diff2_acf1's guard on returns, this does not blank a smooth
deterministic drift -- STL reads log-close levels directly, where a
drift's values genuinely vary -- so drifting series of any steepness still
fire (measured in docs/measure_stl_seasonal_strength.py).

Calculation:
    Default Inputs:
        length=100
    period=5, seasonal=7, trend=11, low_pass=7 (fixed; see above)
    Y = LN(close / close[T - length + 1])      (log closes, relative to the window's own first bar)
    T, S = STL(Y; period, seasonal, trend, low_pass, degree=1 throughout,
               inner_iter=5, outer_iter=0)      (trend, seasonal; via the two
                                                  fixed linear operators above)
    R = Y - T - S                              (residual)
    STLSEAS = 1 - VAR(R) / VAR(S + R)

Args:
    close (pd.Series): Series of 'close's
    length (int): Closes per window. At least 50 (10 full 5-bar cycles, see
        MIN_LENGTH); a smaller or missing value falls back to the default.
        Default: 100
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)

Returns:
    pd.Series: STLSEAS_{length}
"""
