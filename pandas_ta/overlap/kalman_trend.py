# -*- coding: utf-8 -*-
from functools import lru_cache

from numpy import abs as npabs, array, ceil, errstate, expm1, eye, flatnonzero, full, isfinite, log, nan, outer
from numpy.linalg import eigvals
from pandas import DataFrame
from pandas_ta.utils import get_offset, verify_series


@lru_cache(maxsize=None)
def _steady_state(q_level, q_slope):
    """Steady-state gain (level, slope) and closed-loop spectral radius, by
    iterating the Riccati recursion. Data-independent, so it cannot leak the future."""
    F, P = array([[1.0, 1.0], [0.0, 1.0]]), eye(2) * 1e4
    for _ in range(5000):
        prev = P
        P = F @ P @ F.T + array([[q_level, 0.0], [0.0, q_slope]])
        K = P[:, 0] / (P[0, 0] + 1.0)
        P = P - outer(K, P[0])
        if npabs(P - prev).max() <= 1e-15 * npabs(P).max(): break
    else:  # an unconverged rho is too small, so the warm-up would be too short
        raise ValueError(f"kalman_trend: Riccati did not converge for q_level={q_level}, q_slope={q_slope}")
    rho = float(max(abs(eigvals((eye(2) - outer(K, [1.0, 0.0])) @ F))))
    return (float(K[0]), float(K[1])), rho


def _steady_warmup(q_level, q_slope):
    """Valid bars for the start-up transient to shrink 1e8-fold at the steady-state
    spectral radius. The transient starts at about 16 (percent, measured); the head
    worst left is 4.0e-7 measured (decay runs slower than rho predicts: 120 vs 112
    bars to 1e-3), under the 1e-6 the head test asserts."""
    rho = _steady_state(q_level, q_slope)[1]
    if rho >= 1.0:
        raise ValueError(f"kalman_trend: q_level={q_level}, q_slope={q_slope} never settle (rho={rho})")
    return int(ceil(log(1e-8) / log(rho)))


def kalman_trend(close, q_level=None, q_slope=None, offset=None, **kwargs):
    """Indicator: Kalman Local-Linear-Trend filter on log price (KFT)"""
    # Validate arguments
    q_level = 0.01 if q_level is None else float(q_level)
    q_slope = (0.0 if q_slope is None else float(q_slope)) or 0.0001
    if not (isfinite(q_level) and isfinite(q_slope) and q_level >= 0 and q_slope > 0):
        raise ValueError(f"kalman_trend: need finite q_level >= 0, q_slope > 0; got {q_level}, {q_slope}")
    warmup = _steady_warmup(q_level, q_slope)
    close = verify_series(close, warmup + 1)
    offset = get_offset(offset)

    if close is None: return

    # Calculate Result. Log of a ratio to the first usable close, so x8 rescaling is bit-identical.
    vals = close.to_numpy(dtype=float)
    usable = vals[isfinite(vals) & (vals > 0)]
    if len(usable) <= warmup: return
    with errstate(divide="ignore", invalid="ignore"):  # 0 -> -inf, < 0 -> nan; both skipped below
        y = log(vals / usable[0])
    n = len(y)
    dist, vel = full(n, nan), full(n, nan)
    level = slope = 0.0
    p00, p01, p11 = 1e4, 0.0, 1e4  # diffuse prior; measurement noise is 1, q_* are ratios to it
    started = False
    for t in range(n):
        if started:  # predict: level += slope
            level += slope
            p00, p01, p11 = p00 + 2 * p01 + p11 + q_level, p01 + p11, p11 + q_slope
        if not isfinite(y[t]): continue
        started = True
        s = p00 + 1.0
        k0, k1 = p00 / s, p01 / s
        e = y[t] - level
        level += k0 * e
        slope += k1 * e
        p00, p01, p11 = (1 - k0) * p00, (1 - k0) * p01, p11 - k1 * p01
        dist[t] = 100 * expm1(y[t] - level)
        vel[t] = 100 * slope

    # Count updates, not bars: a predict-only bar does not shrink the transient.
    cut = flatnonzero(isfinite(y))[warmup]
    dist[:cut] = vel[:cut] = nan

    _props = f"_{q_level:.12g}_{q_slope:.12g}"
    df = DataFrame({f"KFT_DIST{_props}": dist, f"KFT_VEL{_props}": vel}, index=close.index)

    # Offset
    if offset != 0:
        df = df.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        df.fillna(kwargs["fillna"], inplace=True)

    # Name and Categorize it
    df.name = f"KFT{_props}"
    df.category = "overlap"

    return df


kalman_trend.__doc__ = \
"""Kalman Local-Linear-Trend filter (KFT)

A two-state (level, velocity) Kalman filter on log price, emitting the close's
percent distance from the filtered level and the filtered velocity per bar.
The model, on y = ln(close / first positive close):

    level[t] = level[t-1] + slope[t-1] + w_level,   w_level ~ N(0, q_level)
    slope[t] = slope[t-1] + w_slope,                w_slope ~ N(0, q_slope)
    y[t]     = level[t] + v,                        v ~ N(0, 1)

Sources: Alpha Architect, Trend-Following Filters Parts 4-5; Chan (2013) ch. 3.
Neither is cited line by line; the recursion is the textbook predict/update.

The noise variances are FIXED parameters, never fitted: maximum-likelihood
fitting on the whole series would be a look-ahead. Only their ratio to the
measurement noise matters, so the measurement noise is 1.

Warm-up: output starts at the (w+1)-th valid close, where `w` is the number of
updates the start-up transient takes to shrink 1e8-fold at the steady-state
closed-loop spectral radius (213 at the defaults). Valid means finite and > 0;
other closes are predict-only bars that emit NaN. See docs/KalmanTrendMeasured.md.

Column names format q_level and q_slope with `.12g` (0.0001 -> "0.0001",
1e-05 -> "1e-05", 0.0 -> "0", 0.01000001 -> "0.01000001"). Pass Python floats:
a numpy float32 carries its rounding into the name (1e-4 -> "9.99999974738e-05").

Calculation:
    Default Inputs:
        q_level=0.01, q_slope=0.0001 (steady-state level gain printed by
        docs/measure_kalman_trend_proxy.py)

    KFT_DIST = 100 * (close / exp(filtered level) - 1)     percent
    KFT_VEL  = 100 * filtered slope                         log-percent per bar

Args:
    close (pd.Series): Series of 'close's
    q_level (float): level noise / measurement noise; finite, >= 0. Default: 0.01
    q_slope (float): slope noise / measurement noise; finite, > 0, and 0 or
        None falls back to the default. Default: 0.0001
    Negative or non-finite q_level / q_slope raise ValueError, and so does any
    pair whose Riccati recursion needs more than 5000 steps: q_slope small
    relative to q_level, roughly a warm-up beyond ~5000 updates, e.g.
    (0.01, 1e-8), (2, 1e-5), (30, 1e-4).
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)

Returns:
    pd.DataFrame: KFT_DIST, KFT_VEL columns.
"""
