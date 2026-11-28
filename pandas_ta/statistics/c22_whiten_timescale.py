# -*- coding: utf-8 -*-
import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from pandas import Series

from pandas_ta.utils import get_offset, verify_series

#: Same floor family as this fork's other return-ACF catch22 ports
#: (`c22_acf_first_min`, `firstzero_ac`): a window whose return sd is at most
#: NOISE_ULPS machine epsilons of its largest |1 + r| varies only by the
#: rounding of `c / c1 - 1`, so neither the raw window nor its 1-bar
#: differences have a real autocorrelation to read.
NOISE_ULPS = 64
#: `TRAIN` is the feature's OWN parameter -- the `1` of
#: `FC_LocalSimple_mean1_taurat` -- a module constant, not a function of
#: `length`: the forecast at every index is always the single PREVIOUS
#: point, so the residual series is the plain first difference of the
#: window.
TRAIN = 1
#: Fewest returns a window may hold. The residual series has `length -
#: TRAIN` points; it needs at least 3 for `_first_zero_lag` to have more
#: than one interior lag to scan (`acf[:, 1:]` needs >= 2 columns). A
#: module choice, not from the source: the definition does not itself
#: state a minimum.
MIN_LENGTH = TRAIN + 3
#: Window cells per evaluation chunk -- same budget convention as this
#: fork's other catch22 ports: keeps the peak off `len(close) * length`.
CHUNK_CELLS = 1 << 18


def _first_zero_lag(x):
    """hctsa's `CO_FirstZero(y, 'ac')`: the first zero crossing of the
    sample autocorrelation of each row of `x`, as a LINEARLY INTERPOLATED
    lag rather than a bare integer one. Find the smallest integer `k >= 1`
    with `acf(k) <= 0` (the ACF crosses zero coming down from `acf(0) =
    1`), then report the fractional point between `k - 1` and `k` where
    the straight line through `(k - 1, acf(k - 1))` and `(k, acf(k))`
    itself crosses zero:

        tau = (k - 1) + acf(k - 1) / (acf(k - 1) - acf(k))

    `acf(k - 1) > 0` and `acf(k) <= 0` by construction (k is the FIRST
    such lag), so the denominator is always positive and `tau` always
    lands in `[k - 1, k]`. A row with no such lag (the ACF stays positive
    at every lag this window can see) reads back its own length `m` --
    not a short lag and not a long one, the same sentinel convention this
    fork's `c22_acf_first_min` and `firstzero_ac` use for their own "not
    found" case; a sentinel is a count, not a crossing, so it is NOT
    interpolated.

    **The interpolation step (not merely the integer-lag scan) was fit
    against the GPL-3.0 reference as a black box**
    (`docs/measure_c22_whiten_timescale.py` section P): an earlier,
    simpler build that reported the bare integer `k` read exactly 1.0 on
    every sampled `walk`-frame window (both the raw and residual series
    crossed at the very first lag), while `pycatch22.catch22_all(...)
    ["FC_LocalSimple_mean1_taurat"]` read a tight band around 0.70-0.73 on
    the SAME windows -- a fractional value no integer-lag scan can
    produce, which is what motivated re-deriving this step with linear
    interpolation.

    `x` is a `(rows, m)` slab, already known to hold no NaN. The
    autocovariance is the standard "biased" estimator read off one FFT --
    demeaned once, divided by `m` at every lag -- the same transform and
    divisor `c22_acf_first_min` and `firstzero_ac` use on the same window of
    returns.

    Returns `(tau, sd)`: `sd` is each row's own standard deviation (lag-0
    autocovariance, square-rooted), for the caller to apply its own
    no-variation floor.
    """
    rows, m = x.shape
    xo = x - x.mean(axis=1, keepdims=True)
    nfft = 1
    while nfft < 2 * m:
        nfft *= 2
    f = np.fft.fft(xo, n=nfft, axis=1)
    acov = np.fft.ifft(f * np.conjugate(f), axis=1)[:, :m].real / m
    sd = np.sqrt(np.clip(acov[:, 0], 0.0, None))

    with np.errstate(divide="ignore", invalid="ignore"):
        acf = acov / acov[:, :1]

    # Column `j` of `tail` is lag `j + 1`, j = 0 .. m - 2. A NaN comparison
    # (an all-zero `acov` divided by itself) is False everywhere, so such a
    # row falls through to the `m` sentinel and is then emptied by the
    # caller's own floor check.
    tail = acf[:, 1:]
    hit = tail <= 0.0
    found = hit.any(axis=1)
    j = hit.argmax(axis=1)  # k - 1, the column index into both acf and tail
    rix = np.arange(rows)
    acf_km1 = acf[rix, j]
    acf_k = tail[rix, j]
    denom = acf_km1 - acf_k
    with np.errstate(divide="ignore", invalid="ignore"):
        interp = j + np.where(denom > 0.0, acf_km1 / denom, 0.0)
    tau = np.where(found, interp, float(m))

    return tau, sd


def _whiten_timescale_rows(window):
    """The ratio of two ACF timescales (`_first_zero_lag`, above): the
    1-bar-forecast RESIDUAL's own timescale over the RAW window's own
    timescale.

    `window` is a `(rows, length)` slab of one-bar SIMPLE RETURNS, oldest
    first, already known to hold no NaN. The residual at index `i` (`i = 1
    .. length - 1`) is `window[i] - window[i - 1]` -- hctsa's
    `FC_LocalSimple(y, 'mean1')`: the trailing mean forecast of window
    length `TRAIN = 1` is simply the single previous point, so the residual
    is the plain first difference.

    Comes back as NaN for a row whose raw window OR whose residual series
    does not clear `NOISE_ULPS` machine epsilons of the row's own largest
    `|1 + r|` -- the same floor, the same relative scale, `c22_acf_first_min`
    and `firstzero_ac` use on this window, applied to BOTH series because
    either one going flat leaves its own ACF reading nothing but rounding
    noise.
    """
    lag_orig, sd_orig = _first_zero_lag(window)
    residual = window[:, TRAIN:] - window[:, :-TRAIN]
    lag_resid, sd_resid = _first_zero_lag(residual)

    floor = NOISE_ULPS * np.finfo(float).eps * np.abs(1.0 + window).max(axis=1)
    real = (sd_orig > floor) & (sd_resid > floor)

    ratio = lag_resid / lag_orig
    return np.where(real, ratio, np.nan)


def c22_whiten_timescale(close, length=None, offset=None, **kwargs):
    """Indicator: catch22 ACF timescale of 1-bar forecast residuals vs returns (C22WHITENTIMESCALE)"""
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
        r[~np.isfinite(r * r)] = np.nan

    n = c.size
    out = np.full(n, np.nan)
    if n >= length + 1:
        # The window ending at bar T holds the `length` returns of bars
        # T - length + 1 .. T, which read closes T - length .. T: bar `length`
        # is the first that fires. Evaluated in chunks so memory does not
        # grow with `len(close) * length`.
        win = sliding_window_view(r, length)
        rows = win.shape[0]
        step = max(1, CHUNK_CELLS // length)
        for a in range(0, rows, step):
            b = min(a + step, rows)
            chunk = win[a:b]
            ok = ~np.isnan(chunk).any(axis=1)
            vals = np.full(chunk.shape[0], np.nan)
            if ok.any():
                vals[ok] = _whiten_timescale_rows(chunk[ok])
            out[length + a:length + b] = vals

    result = Series(out, index=close.index)

    # Offset
    if offset != 0:
        result = result.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        result.fillna(kwargs["fillna"], inplace=True)

    # Name and Categorize it
    result.name = f"C22WHITENTIMESCALE_{length}"
    result.category = "statistics"

    return result


c22_whiten_timescale.__doc__ = \
"""catch22 ACF timescale of 1-bar forecast residuals vs returns (C22WHITENTIMESCALE)

Over the last `length` daily simple returns, take the first difference
(the residual of a trivial "forecast the previous value" predictor) and
report the ratio of two autocorrelation timescales: the first zero
crossing of the RESIDUAL's own autocorrelation function, over the first
zero crossing of the RAW window's. "Zero crossing" is hctsa's
`CO_FirstZero`: find the smallest lag `k >= 1` where the ACF is zero or
negative, then report the LINEARLY INTERPOLATED fractional point
between `k - 1` and `k` where the straight line through those two ACF
values itself crosses zero -- a continuous lag estimate, not a bare
integer one. A series whose ACF never turns non-positive, over every
lag this window can see, reads back its own length -- not a short lag
and not a long one, a SENTINEL for "no crossing found", the same
convention this fork's `c22_acf_first_min` and `firstzero_ac` use for
their own integer-lag case (a sentinel is a count, not a crossing, so
it is never itself interpolated).

    C22WHITENTIMESCALE = CO_FirstZero(diff(X)) / CO_FirstZero(X)

A value near 1 means differencing the window does not change how long
its autocorrelation takes to turn negative; well below 1 means
differencing shortens that timescale a lot (the raw series carries slow
structure the 1-bar forecast's residual does not); above 1 is possible
too, when differencing lengthens it (e.g. it introduces a negative lag-1
autocorrelation that a short raw-series timescale did not have).

Source: catch22 (Lubba, Sethi, Knaute, Schultz, Fulcher, Jones 2019,
*Data Mining and Knowledge Discovery* 33:1821, "catch22: CAnonical
Time-series CHaracteristics"), feature `FC_LocalSimple_mean1_taurat` --
the hctsa operation `FC_LocalSimple(y, 'mean1')`'s `tauresrat` /
`taurat` statistic: the ratio of the residual series' own
autocorrelation timescale (`CO_FirstZero`) to the raw series' --
applied by PandasTa issue #139 to the last 100 daily simple returns.
The reference implementation (pycatch22 1.0.2) is **GPL-3.0** and this
fork is MIT: this module was written from the DEFINITION -- "the
trailing mean forecast with a training window of 1 point is simply the
previous point" and "the first zero crossing of the autocorrelation
function" are both public-domain mathematics, not reference code -- and
no shipped module imports the reference (a test asserts that over the
whole package). The one place it is run at all is
`docs/measure_c22_whiten_timescale.py` section P -- opt-in, measurement
only, the same use the owner's own screen prototype makes of it.

**The linear-interpolation step was settled by fitting the GPL-3.0
reference as a BLACK BOX, not read from its source.** An earlier,
simpler build that scanned only the bare INTEGER crossing lag read
exactly 1.0 on every sampled window of a synthetic random-walk frame
(both the raw window and its residual crossed at the very first
integer lag), while `pycatch22.catch22_all(...)
["FC_LocalSimple_mean1_taurat"]` read a tight band around 0.70-0.73 on
the SAME windows -- a fractional value no integer scan can produce.
Adding the interpolation above closed the gap: **0 of 8,400 windows
(every window of six synthetic frames) disagree with the reference
beyond 1e-9**, worst absolute difference 1.6e-12 (`docs/
measure_c22_whiten_timescale.py` section P).

⚠ catch22 is a subset selected for TIME-SERIES CLASSIFICATION
performance on 93 reference problems. That is not return prediction,
and nothing here tests it on BIST: its presence in this fork is
existence, not evidence.

**The autocorrelation is the standard "biased" estimator, read off one
FFT per window** -- demeaned once, divided by the series' own length at
every lag, the same transform and divisor this fork's `c22_acf_first_min`
and `firstzero_ac` already use on the SAME window of returns. catch22
z-scores its series before every feature; doing so here is INERT by
construction, because the autocorrelation already divides by the
series' own `acov(0)` -- any affine map of either series cancels in
both the numerator and the denominator of its own ACF, so it cancels in
the ratio too.

Calculation:
    Default Inputs:
        length=100, TRAIN=1
    r[t]      = close[t] / close[t-1] - 1
    X         = r[T-length+1 .. T]                      (the window)
    D         = X[1:] - X[:-1]                           (the residual)
    k(y)      = min{k in 1 .. len(y) - 1 : acf_y(k) <= 0}, else len(y)
    tau(y)    = len(y)                                    if k(y) == len(y)
              = (k(y) - 1) + acf_y(k(y) - 1) / (acf_y(k(y) - 1) - acf_y(k(y)))
                                                           otherwise
    C22WHITENTIMESCALE = tau(D) / tau(X)

**ONE blanking rule, applied to BOTH series.** The window is NaN unless
BOTH the raw window's own return standard deviation AND the residual
series' own standard deviation clear `64 * eps * max(|1 + r|)` -- the
same floor, the same relative scale, `c22_acf_first_min` and
`firstzero_ac` use on this window -- so that this column reads ACF
structure and not the rounding of a flat window on either side of the
ratio.

Causal: bar T reads closes T - length .. T. Measured by future-perturbation
sweep and by mutants read off this module's source, edited and exec'd in
memory (`docs/measure_c22_whiten_timescale.py` section B, `tests/
test_c22_whiten_timescale.py`).

Scale-free: the price enters only as `close[t] / close[t-1]`, and `8a /
8b` is the same double as `a / b` -- bit-identical under a x8/x64 price
rescale (section D), and the ratio is unchanged in exact real
arithmetic under any positive affine rescale of the returns because
both `tau(X)` and `tau(D)` are themselves scale-free (each one's own
ACF already normalises by its own variance). Because `tau` is now a
CONTINUOUS interpolated value rather than a bare integer lag, an
INEXACT rescale (x10, x3.7, x0.1, x1.0000001) moves most individual
bars by float noise (worst measured 3.7e-13) rather than leaving them
bit-identical -- unlike this fork's discrete-lag catch22 siblings.

NaN on the first `length` bars; on every window holding a close that is
NaN, infinite, zero, negative or subnormal; on a window holding a close
PAIR whose ratio overflows to an infinite return; and under the
blanking rule above.

Args:
    close (pd.Series): Series of 'close's
    length (int): RETURNS per window, so `length + 1` closes. At least
        `TRAIN + 3` = 4 -- so the residual series has at least 3 points,
        giving `_first_zero_lag` more than one interior lag to scan --
        and a smaller or missing value falls back to the default.
        Default: 100
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)

Returns:
    pd.Series: C22WHITENTIMESCALE_{length}, a ratio of two continuous,
        linearly interpolated lag counts, typically positive and most
        often read well under 10
"""
