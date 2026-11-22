# -*- coding: utf-8 -*-
import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from pandas import Series

from pandas_ta.utils import get_offset, verify_series

#: The feature's OWN parameter -- the `3` of `FC_LocalSimple_mean3_stde` --
#: so it is a module constant and not a function of `length`: at every
#: index the forecast is the mean of the PREVIOUS 3 points, never more or
#: fewer. hctsa's `FC_LocalSimple(y, 'mean3')`.
TRAIN = 3
#: Divisor convention of the z-score catch22 applies before every feature. 1
#: is MATLAB `zscore`'s default, and hctsa is MATLAB. Unlike this fork's
#: order/quantile-based catch22 ports (`c22_entropy_pairs`, `c22_dfa`), this
#: column's own residual-std OUTPUT scales with whichever `sd` the z-score
#: divided by, so the knob is NOT inert here -- it sets the output's own
#: scale, the same way it is not inert for `c22_mode_5`/`c22_mode_10`.
#: Pinned against the GPL-3.0 reference (`docs/measure_c22_forecast_error.py`
#: section P): `ddof=1` on both the input z-score AND the residual std
#: reproduces `pycatch22.catch22_all(...)["FC_LocalSimple_mean3_stde"]` on
#: 8,400 of 8,400 sampled windows (worst gap 1.1e-15); `ddof=0` on either one
#: disagrees on all 366 windows of a separate, smaller candidate-fit sample
#: (every 23rd window of six frames), by up to 6.4e-3.
ZSCORE_DDOF = 1
#: ddof of the RESIDUAL standard deviation this feature reports. Pinned
#: alongside `ZSCORE_DDOF` above by the same black-box fit.
RESID_DDOF = 1
#: Fewest returns a window may hold: `TRAIN + 2`, so the forecast-error
#: vector this feature takes a standard deviation of has at least 2 entries
#: -- the fewest `std(ddof=1)` can divide by without a zero or negative
#: denominator. A module choice, not from the source: the definition does
#: not itself state a minimum. A smaller or missing `length` falls back to
#: the default.
MIN_LENGTH = TRAIN + 2
#: A window of returns whose standard deviation is at most NOISE_ULPS
#: machine epsilons does not vary: its z-score is decided by the rounding of
#: `c / c1 - 1` rather than by shape. NaN instead. The floor is an ABSOLUTE
#: constant because what it bounds is a dimensionless RETURN, the same habit
#: this fork's other catch22-on-returns ports use (`c22_entropy_pairs`,
#: `c22_ami2`, `c22_ami_timescale`, `c22_dfa`, `c22_periodicity`,
#: `c22_mode_5`, `c22_mode_10`).
NOISE_ULPS = 4096
NOISE_FLOOR = NOISE_ULPS * np.finfo(float).eps  # 9.09e-13
#: Doubles of window to evaluate at once. Each chunk allocates a `(rows,
#: length)` z-scored slab and a same-shaped residual slab, so this budget is
#: what keeps the peak off the product `len(close) * length`.
CHUNK_VALUES = 1 << 19


def _forecast_error_rows(block):
    """The standard deviation of the forecast errors of a trailing
    3-point mean forecast, on each row's own z-scored window.

    `block` is a `(rows, length)` slab of one-bar SIMPLE RETURNS, oldest
    first. Each row is z-scored; at every index `i` from `TRAIN` to
    `length - 1` the forecast is the mean of the row's own PREVIOUS `TRAIN`
    z-scored points, the residual is `z[i] - forecast[i]`, and the column is
    the standard deviation of the `length - TRAIN` residuals so produced.

    Comes back as NaN for a row holding a non-finite return and for a row
    whose standard deviation is at most `NOISE_FLOOR` or is not finite -- a
    flat window has no z-score to take.
    """
    rows, n = block.shape

    bad = ~np.isfinite(block).all(axis=1)
    with np.errstate(invalid="ignore", over="ignore", divide="ignore"):
        sd = block.std(axis=1, ddof=ZSCORE_DDOF)
        z = (block - block.mean(axis=1, keepdims=True)) / sd[:, None]
        bad |= ~(sd > NOISE_FLOOR) | ~np.isfinite(sd)

        # The trailing TRAIN-point mean forecast, vectorised as the mean of
        # TRAIN shifted slices rather than a sliding window per row: slice
        # `k` holds `z[:, k : n - TRAIN + k]`, so summing `k = 0 .. TRAIN -
        # 1` and dividing by TRAIN gives, at output position `j`, the mean
        # of `z[:, j : j + TRAIN]` -- the forecast for target index
        # `i = j + TRAIN`, i.e. the mean of the TRAIN points immediately
        # BEFORE it.
        forecast = sum(z[:, k:n - TRAIN + k] for k in range(TRAIN)) / TRAIN
        residual = z[:, TRAIN:] - forecast
        stde = residual.std(axis=1, ddof=RESID_DDOF)

    return np.where(~bad, stde, np.nan)


def c22_forecast_error(close, length=None, offset=None, **kwargs):
    """Indicator: catch22 error of a 3-bar mean forecast of returns
    (C22FORECASTERROR)"""
    # Validate Arguments
    length = int(length) if length and int(length) >= MIN_LENGTH else 100
    close = verify_series(close, length + 1)
    offset = get_offset(offset)

    if close is None: return

    # Calculate Result
    c = close.to_numpy(dtype=float)
    # A close that is not a finite, normal, positive float (NaN, inf, zero,
    # negative, or subnormal such as 1e-310) is bad data: it has no return to
    # take, so it is missing.
    c = np.where(np.isfinite(c) & (c >= np.finfo(float).tiny), c, np.nan)

    # The one-bar simple return, spelled as a price RATIO minus one: `8a / 8b`
    # is the same double as `a / b`, so a x2**k rescale of the price cancels
    # EXACTLY here and nothing downstream can see it.
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        r = c[1:] / c[:-1] - 1.0
    r = np.where(np.isfinite(r), r, np.nan)

    n = c.size
    out = np.full(n, np.nan)
    if n >= length + 1:
        # The window ending at bar T holds the `length` returns of bars
        # T - length + 1 .. T, which read closes T - length .. T: bar `length`
        # is the first that fires.
        win = sliding_window_view(r, length)
        rows = win.shape[0]
        step = max(1, CHUNK_VALUES // length)
        for a in range(0, rows, step):
            b = min(a + step, rows)
            out[length + a:length + b] = _forecast_error_rows(win[a:b])

    result = Series(out, index=close.index)

    # Offset
    if offset != 0:
        result = result.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        result.fillna(kwargs["fillna"], inplace=True)

    # Name and Categorize it
    result.name = f"C22FORECASTERROR_{length}"
    result.category = "statistics"

    return result


c22_forecast_error.__doc__ = \
"""catch22 error of a 3-bar mean forecast of returns (C22FORECASTERROR)

Z-score the last `length` daily returns. At every index from the 4th
point on, forecast it as the mean of the PREVIOUS 3 z-scored points,
take the residual (actual minus forecast), and report the standard
deviation of the `length - 3` residuals so produced.

    Z   = (X - mean(X)) / sd(X, ddof=1)
    f[i]   = mean(Z[i-3], Z[i-2], Z[i-1]),           i = 3 .. length-1
    e[i]   = Z[i] - f[i]
    C22FORECASTERROR = sd(e, ddof=1)

**This is the irreducible noise of the naivest local forecaster this
fork's catch22 family has**: a flat 3-point moving average, applied to
the OWN past of a z-scored return window rather than to price. A series
whose returns are close to a pure random walk (no exploitable short-run
structure for a 3-point average to catch) reads CLOSE TO the overall
z-scored standard deviation, i.e. close to 1 -- after z-scoring removes
the window's own scale, "the 3-bar mean forecast cannot do much better
than guessing the window's own mean" is the "nothing to see here"
reading. A series with strong local smoothness (a 3-point average
genuinely tracks it) reads BELOW 1; one with anti-persistent local
noise (overshooting the 3-point average systematically) can read
ABOVE 1.

**Source: catch22 (Lubba, Sethi, Knaute, Schultz, Fulcher, Jones 2019,
*Data Mining and Knowledge Discovery* 33:1821, "catch22: CAnonical
Time-series CHaracteristics"), feature `FC_LocalSimple_mean3_stde` of
catch22 1.0 -- hctsa's `FC_LocalSimple(y, 'mean3')`, the standard
deviation of its residuals -- applied by PandasTa issue #137 to the
last 100 daily simple returns.** ⚠ catch22 is a subset selected for
TIME-SERIES CLASSIFICATION performance on 93 reference problems. That
is not return prediction, and nothing here tests it on BIST: its
presence in this fork is existence, not evidence.

The reference implementation (pycatch22 1.0.2) is **GPL-3.0** and this
fork is MIT: this module was written from the DEFINITION -- hctsa's own
`FC_LocalSimple` family (a local forecaster's residual statistics) and
the name `mean3_stde` itself, which states the forecast (a trailing
3-point mean) and the reported statistic (the residual standard
deviation) -- and from catch22's standard z-score preprocessing, never
from the reference's source. No shipped module imports it (a test
asserts that over the whole package); the one place it is run at all is
`docs/measure_c22_forecast_error.py` section P, opt-in, measurement
only, the same use the owner's own screen prototype makes of it.

**Both `ddof` knobs were settled by fitting the GPL-3.0 reference as a
BLACK BOX, not read from its source** (`docs/measure_c22_forecast_error.py`
section P): of six candidate (z-score ddof, residual ddof) pairs tried --
(1, 1), (1, 0), (0, 1), (0, 0), no-z-score, and dividing the shipped
(1, 1) reading by `sqrt(length - 3)` (a literal reading of "std ERROR") --
only `ddof=1` on BOTH reproduces `pycatch22.catch22_all(...)
["FC_LocalSimple_mean3_stde"]` **on 8,400 of 8,400 sampled windows** across
six synthetic frames (worst gap 1.1e-15, machine noise) -- the full P2
sweep, run on the shipped candidate only. The SIX-candidate fit itself
(§P1) runs on a smaller sample, every 23rd window of the same six frames,
366 windows total: every other candidate disagrees on all 366 of them, by
1.9e-4 to 1.2 depending on the candidate, nowhere near the 1e-6 band the
shipped candidate clears. This is the cleanest black-box fit of this fork's catch22
ports to date -- no residual gap, no root-caused divergence, unlike
`c22_mode_10`/`c22_mode_5` (a float32-vs-float64 boundary flip on a
repeated-value frame) or `c22_periodicity` (an unresolved biased-divisor
gap).

Calculation:
    Default Inputs:
        length=100, TRAIN=3, ZSCORE_DDOF=1, RESID_DDOF=1
    r[t]   = close[t] / close[t-1] - 1
    X      = r[T-length+1 .. T]                 (the window)
    Z      = (X - mean(X)) / sd(X, ddof=1)
    f[i]   = mean(Z[i-3:i]),                     i = 3 .. length-1
    e[i]   = Z[i] - f[i]
    C22FORECASTERROR = sd(e, ddof=1)

**ONE blanking rule.** The window is NaN unless its return standard
deviation clears 9.09e-13 (4096 eps) -- the same floor this fork's other
catch22 ports on returns use -- so that this column reads SHAPE and not
the rounding of a flat window.

Causal: bar T reads closes T - length .. T. Measured by future-perturbation
sweep and by mutants read off this module's source, edited and exec'd in
memory (`docs/measure_c22_forecast_error.py` section B, `tests/
test_c22_forecast_error.py`).

Scale-free: z-scoring removes any affine dependence on the RAW return
scale -- `Z' = (kX + d - mean(kX + d)) / sd(kX + d, ddof=1) = Z` for any
`k > 0` and any shift `d`, exactly, in real arithmetic, and every later
step (the trailing-mean forecast, the residual, its own standard
deviation) is a further linear/affine function of `Z` -- so the shipped
column is dimensionless by construction. In floating point this is
bit-identical under a x8/x64 price rescale (the price enters only as
`c[t] / c[t-1]`, and `8a / 8b` is the double `a / b`) and measured within
a small tolerance under an inexact return rescale (x10, x3.7) -- see
`docs/measure_c22_forecast_error.py` section D and `tests/
test_c22_forecast_error.py`.

NaN on the first `length` bars; on every window holding a close that is
NaN, infinite, zero, negative or subnormal; on a window holding a close
PAIR whose ratio overflows to an infinite return; and under the
blanking rule above.

Args:
    close (pd.Series): Series of 'close's
    length (int): RETURNS per window, so `length + 1` closes. At least
        `TRAIN + 2` = 5 -- so the residual vector has at least 2 entries
        for its own `std(ddof=1)` to be defined -- and a smaller or
        missing value falls back to the default. Default: 100
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)

Returns:
    pd.Series: C22FORECASTERROR_{length}, a dimensionless (z-score-unit)
        standard deviation, typically near 1 on a return series close to
        a random walk
"""
