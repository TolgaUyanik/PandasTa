# -*- coding: utf-8 -*-
import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from pandas import Series

from pandas_ta.utils import get_offset, verify_series

#: A window whose return standard deviation is at most NOISE_ULPS machine
#: epsilons of its largest |1 + r| varies only by the rounding of
#: `c / c1 - 1`: no variation, so no autocorrelation to read. Same constant
#: and the same relative-to-`|1 + r|` form as this module's closest sibling,
#: `firstzero_ac` -- the same input window read by a different scan.
NOISE_ULPS = 64
#: Fewest returns a window may hold. The scan needs at least one interior
#: lag to test -- `k = 1` reads `acf(0)`, `acf(1)`, `acf(2)` -- so three
#: returns is the absolute floor; a smaller or missing `length` falls back
#: to the default.
MIN_LENGTH = 3
#: Window cells per evaluation chunk, the same budget convention as
#: `firstzero_ac` and the other catch22 ports: this is what keeps the peak
#: off `len(close) * length` rather than `len(close) * length` itself.
CHUNK_CELLS = 1 << 18


def _acf_first_min_rows(r):
    """The first local minimum of the sample autocorrelation, per row of `r`.

    `r` is a `(rows, length)` slab of one-bar SIMPLE RETURNS, oldest first,
    already known to hold no NaN. Each row's autocovariance at every lag
    `0 .. length - 1` is read off one FFT (demeaned once, divisor `length`
    -- the standard "biased" estimator, the same transform and divisor
    `firstzero_ac` uses), normalised by lag 0 into `acf`, and the row
    reports the smallest lag `k >= 1` with `acf(k - 1) > acf(k) < acf(k +
    1)` -- a STRICT local minimum. A row with no such lag reads `length`,
    the window's own size: not a short lag and not a long one, a sentinel
    that means "no interior minimum found in the range this scan can see",
    the same convention `firstzero_ac` uses for its own "no crossing" case.

    Comes back as NaN for a row whose return standard deviation is at most
    `NOISE_ULPS` machine epsilons of its largest `|1 + r|` -- a flat
    window has no autocorrelation to read, only the rounding of `c / c1 -
    1` at full strength.
    """
    rows, m = r.shape
    xo = r - r.mean(axis=1, keepdims=True)
    nfft = 1
    while nfft < 2 * m:
        nfft *= 2
    f = np.fft.fft(xo, n=nfft, axis=1)
    acov = np.fft.ifft(f * np.conjugate(f), axis=1)[:, :m].real / m

    # A window with no variation (or variation at rounding level) has no
    # autocorrelation to read: `sd` would be at or near zero, and every
    # `acf` value the shape of `c / c1 - 1`'s own rounding. The floor is
    # relative to `|1 + r|` because that is the scale the return's rounding
    # itself is relative to.
    sd = np.sqrt(np.clip(acov[:, 0], 0.0, None))
    floor = NOISE_ULPS * np.finfo(float).eps * np.abs(1.0 + r).max(axis=1)
    real = sd > floor

    with np.errstate(divide="ignore", invalid="ignore"):
        acf = acov / acov[:, :1]

    # Column `c` of this comparison is lag `c + 1`: `left` is `acf(k - 1)`
    # for `k = 1 .. m - 2`, `mid` is `acf(k)` and `right` is `acf(k + 1)`.
    # Every comparison against a NaN (an all-zero `acov` divided by itself)
    # is False, so such a row falls through to the `m` sentinel and is then
    # emptied by `real` below.
    left = acf[:, :m - 2]
    mid = acf[:, 1:m - 1]
    right = acf[:, 2:m]
    hit = (left > mid) & (mid < right)
    found = hit.any(axis=1)
    lag = np.where(found, hit.argmax(axis=1) + 1.0, float(m))

    return np.where(real, lag, np.nan)


def c22_acf_first_min(close, length=None, offset=None, **kwargs):
    """Indicator: catch22 first minimum of the return autocorrelation (C22ACFFIRSTMIN)"""
    # Validate Arguments
    length = int(length) if length and int(length) >= MIN_LENGTH else 100
    close = verify_series(close, length + 1)
    offset = get_offset(offset)

    if close is None: return

    # Calculate Result
    c = close.to_numpy(dtype=float)
    # A close that is not a finite, normal positive float (NaN, inf, zero,
    # negative, or subnormal such as 1e-310) is bad data: it has no return
    # to take, so it is missing.
    c = np.where(np.isfinite(c) & (c >= np.finfo(float).tiny), c, np.nan)

    # The one-bar simple return, spelled as a price RATIO minus one: `8a /
    # 8b` is the same double as `a / b`, so a x2**k rescale of the price
    # cancels EXACTLY here and nothing downstream can see it. Both ends are
    # finite, positive and normal by now, so the ratio can still overflow
    # or underflow to zero, which is bad data in the same way a NaN close
    # is.
    with np.errstate(invalid="ignore", divide="ignore", over="ignore"):
        r = c[1:] / c[:-1] - 1.0
        r[~np.isfinite(r * r)] = np.nan

    n = c.size
    out = np.full(n, np.nan)
    if n >= length + 1:
        # The window ending at bar T holds the `length` returns of bars
        # T - length + 1 .. T, which read closes T - length .. T: bar
        # `length` is the first that fires. Evaluated in chunks so memory
        # does not grow with `len(close) * length`.
        win = sliding_window_view(r, length)
        rows = win.shape[0]
        step = max(1, CHUNK_CELLS // length)
        for a in range(0, rows, step):
            b = min(a + step, rows)
            chunk = win[a:b]
            ok = ~np.isnan(chunk).any(axis=1)
            vals = np.full(chunk.shape[0], np.nan)
            if ok.any():
                vals[ok] = _acf_first_min_rows(chunk[ok])
            out[length + a:length + b] = vals

    result = Series(out, index=close.index)

    # Offset
    if offset != 0:
        result = result.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        result.fillna(kwargs["fillna"], inplace=True)

    # Name and Categorize it
    result.name = f"C22ACFFIRSTMIN_{length}"
    result.category = "statistics"

    return result


c22_acf_first_min.__doc__ = \
"""catch22 first minimum of the return autocorrelation (C22ACFFIRSTMIN)

Over the last `length` daily simple returns, read the sample
autocorrelation at every lag `0 .. length - 1` and report the SMALLEST
lag `k >= 1` where it is a strict local minimum -- the first point the
autocorrelation stops falling and starts rising. A window whose
autocorrelation never turns, scanning the whole range this feature can
see, reads `length` itself: not a short lag and not a long one, a
SENTINEL for "no interior minimum found", the same convention this
fork's sibling `firstzero_ac` uses for its own "no crossing" case.

    C22ACFFIRSTMIN = the first lag k in 1 .. length - 2 with
                     acf(k - 1) > acf(k) and acf(k) < acf(k + 1);
                     else length

The output is a whole number in `[1, length]`. **`length` is a
SENTINEL and also the CEILING of the scale** -- a consumer cannot read
it as "a long lag" without knowing that it may instead mean "no minimum
in range".

Source: catch22 (Lubba, Sethi, Knaute, Schultz, Fulcher, Jones 2019,
*Data Mining and Knowledge Discovery* 33:1821, "catch22: CAnonical
Time-series CHaracteristics"), feature `CO_FirstMin_ac` -- the hctsa
operation `CO_FirstMin(y, 'ac')`: the first local minimum of the
series' own autocorrelation function -- applied by PandasTa issue #131
to the last 100 daily simple returns. The reference implementation
(pycatch22 1.x) is **GPL-3.0** and this fork is MIT: this module was
written from the DEFINITION -- "the first minimum of the
autocorrelation function" is public-domain mathematics, not reference
code -- and no shipped module imports the reference (a test asserts
that over the whole package). The one place it is run at all is
`docs/measure_c22_acf_first_min.py` section P -- opt-in, measurement
only, the same use the owner's own screen prototype makes of it -- to
check this port's reading against a black box.

⚠ catch22 is a subset selected for TIME-SERIES CLASSIFICATION
performance on 93 reference problems. That is not return prediction,
and nothing here tests it on BIST: its presence in this fork is
existence, not evidence.

**The autocorrelation is the standard "biased" estimator, read off one
FFT per window** -- demeaned once, divided by `length` at every lag
(not `length - k`), the same transform and divisor this fork's
`firstzero_ac` already uses for the SAME window of returns. catch22
z-scores its series before every feature; doing so here is INERT by
construction, because the autocorrelation already divides by the
window's own `acov(0)` -- any affine map of the window cancels in both
the numerator and the denominator. Gate A checks the FFT spelling
against a brute-force double loop over lags with no FFT and no
vectorisation at all (`docs/measure_c22_acf_first_min.py` section A).

Calculation:
    Default Inputs:
        length=100
    r[t]    = close[t] / close[t-1] - 1
    X       = r[T-length+1 .. T]                (the window)
    d       = X - mean(X)
    acov(k) = sum(d[:length-k] * d[k:]) / length,  k = 0 .. length - 1
    acf(k)  = acov(k) / acov(0)
    C22ACFFIRSTMIN = min{k in 1 .. length - 2 :
                          acf(k - 1) > acf(k) and acf(k) < acf(k + 1)},
                     else length

**ONE blanking rule.** The window is NaN unless its return standard
deviation clears `64 * eps * max(|1 + r|)` over the window -- the same
floor, the same relative scale, as `firstzero_ac`. It is inert on
anything with noise in it and catches a flat window (all-zero returns
or a price gone flat), a steady drift of any size (constant returns up
to the rounding of `c / c1 - 1`), and a price jittering by one ulp.
Measured in `docs/measure_c22_acf_first_min.py` section G.

**The OWED comparison.** `docs/C22PeriodicityMeasured.md` section E4
flagged this exact pair in advance: `C22PERIODICITY_100` reads the
SAME 100 returns' autocorrelation (through a detrending spline this
feature does not apply) and its own harness's PROXY for this feature
scored a pooled Spearman around +0.8 against it on six synthetic
frames. That receipt's own rule applies: this port's column is
measured against `C22PERIODICITY_100` in
`docs/measure_c22_acf_first_min.py` section E, and if Gate E's real
run (the launcher's, on BIST) strikes that pair, one of the two is
reverted or waived rather than both shipping unexamined.

Causal: bar T reads closes T - length .. T. Measured by
future-perturbation sweep and by mutants read off this module's source,
edited and exec'd in memory (`docs/measure_c22_acf_first_min.py`
section B).
Scale-free: the price enters only as `close[t] / close[t-1]`, and
`8a / 8b` is the same double as `a / b` -- BY CONSTRUCTION, bit-identical
under x8 and x64 (section D).
NaN on the first `length` bars; on every window holding a close that is
NaN, infinite, zero, negative or subnormal; on a window holding a close
PAIR whose ratio overflows; and under the blanking rule above.

Cost: the windows are walked in chunks, so the peak is set by
`CHUNK_CELLS` and not by `len(close) * length`.

Args:
    close (pd.Series): Series of 'close's
    length (int): RETURNS per window, so `length + 1` closes. At least 3;
        a smaller or missing value falls back to the default. Default: 100
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)

Returns:
    pd.Series: C22ACFFIRSTMIN_{length}, a whole number in [1, length]
"""
