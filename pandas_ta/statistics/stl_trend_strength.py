# -*- coding: utf-8 -*-
import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from pandas import Series

from pandas_ta.statistics.stl_seasonal_strength import (
    CHUNK_CELLS, MIN_LENGTH, NOISE_ULPS, _build_ops,
)
from pandas_ta.utils import get_offset, verify_series


def stl_trend_strength(close, length=None, offset=None, **kwargs):
    """Indicator: STL trend strength of log price (STLTREND)"""
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
        r = chunk - s - t
        with np.errstate(invalid="ignore", divide="ignore"):
            var_resid = r.var(axis=1)
            var_trend_resid = (t + r).var(axis=1)
            raw = 1 - var_resid / var_trend_resid
        rows = np.where(real & (var_trend_resid > 0), raw, np.nan)
        lo = length - 1 + start
        values[lo:lo + rows.size] = rows

    trend = Series(values, index=close.index)

    # Offset
    if offset != 0:
        trend = trend.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        trend.fillna(kwargs["fillna"], inplace=True)

    # Name and Categorize it
    trend.name = f"STLTREND_{length}"
    trend.category = "statistics"

    return trend


stl_trend_strength.__doc__ = \
"""STL trend strength of log price (STLTREND)

The strength of the trend component in a rolling window of log close, from
an STL (Seasonal-Trend decomposition using LOESS) fit of the window with a
5-bar (trading-week) period: `1 - var(resid) / var(trend + resid)`. Near 0
means the window's variation is dominated by residual noise (and the 5-bar
seasonal component); near 1 means most of the window's variation is carried
by the smooth trend line.

Source: Kats tsfeatures (Meta, MIT), `get_stl_features`:
`1 - var(resid) / var(trend + resid)` (issue #160's text; Kats' own
`get_stl_features` control flow -- which STL parameters it passes, if any
beyond `period` -- is not independently re-confirmed in this session, no
network access to the Kats source). Kats applies it to a whole series; the
100-bar window, log close as the input, and period 5 are the choices of the
2026-10-25 screen prototype (candidate kats_stl_trend_100,
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
the same way. Only the final ratio differs: `stl_seasonal_strength` divides
by `var(seasonal + resid)`, this module by `var(trend + resid)`. Checked
against statsmodels' own STL as an oracle in
tests/test_stl_trend_strength.py / docs/measure_stl_trend_strength.py.

With `robust=False`, STL's robustness weights never leave 1, so every step
of the decomposition (detrending, cycle-subseries LOESS, low-pass
filtering, deseasonalising, trend LOESS) is a LINEAR function of the
window's own values, with weights that depend only on the window length and
the fixed period/seasonal/trend/low-pass windows, never on the data. The
whole 5-iteration inner loop therefore collapses to two fixed `length x
length` matrices -- one for the seasonal component, one for the trend --
computed once per `length` and cached by `_build_ops`, then applied to
every rolling window by a single matrix multiply. Parameters, all
statsmodels STL defaults for `period=5`: seasonal window 7, trend window 11
(smallest odd integer > 1.5*5/(1-1.5/7)), low-pass window 7 (smallest odd
integer > 5), all LOESS degrees 1, `inner_iter=5`, `outer_iter=0` (not
robust).

Causal: bar T reads closes T - length + 1 .. T only -- every element of the
two fixed operators is a function of position within the window alone, so
the matrix multiply cannot read a future bar. Scale-free: STL is fed
`log(close / the window's own first close)`, not `log(close)` directly
(kpss.py's and stl_seasonal_strength.py's same device) -- mathematically
the same input up to an additive constant per window, which STL's trend
LOESS (degree 1, so it reproduces an added constant exactly) absorbs,
leaving the trend and residual components -- and so this ratio --
unchanged. Under a power-of-two price rescale the ratio itself is
bit-identical (both the numerator and denominator are multiplied by an
exactly-representable factor, so the division's true quotient, and its
correctly-rounded result, do not move), and so is everything downstream,
since the two fixed operators then see an identical bit pattern: measured
bit-identical under x8/x64, within tolerance under x10/x3.7 (not powers of
two, so not bit-exact) -- see Gate D. A window with a close that is NaN,
infinite, zero, negative or subnormal (below 2.2e-308) is NaN (the bad
value poisons every output of the matrix multiply: `0 * NaN = NaN` under
IEEE 754, regardless of the multiplying weight). So is a window whose log
closes do not vary beyond the rounding of `log(close)` (a flat price, or
one-ulp float jitter around one): standard deviation at most 64 machine
epsilons times (1 + the window's largest |log close|) -- the same
`NOISE_ULPS` guard `stl_seasonal_strength` uses, imported rather than
re-derived. Unlike diff1_pacf5/diff2_acf1's guard on returns, this does not
blank a smooth deterministic drift -- STL reads log-close levels directly,
where a drift's values genuinely vary -- so drifting series of any
steepness still fire (measured in docs/measure_stl_trend_strength.py).

Calculation:
    Default Inputs:
        length=100
    period=5, seasonal=7, trend=11, low_pass=7 (fixed; see above)
    Y = LN(close / close[T - length + 1])      (log closes, relative to the window's own first bar)
    T, S = STL(Y; period, seasonal, trend, low_pass, degree=1 throughout,
               inner_iter=5, outer_iter=0)      (trend, seasonal; via the two
                                                  fixed linear operators above)
    R = Y - T - S                              (residual)
    STLTREND = 1 - VAR(R) / VAR(T + R)

Args:
    close (pd.Series): Series of 'close's
    length (int): Closes per window. At least 50 (10 full 5-bar cycles, see
        MIN_LENGTH); a smaller or missing value falls back to the default.
        Default: 100
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)

Returns:
    pd.Series: STLTREND_{length}
"""
