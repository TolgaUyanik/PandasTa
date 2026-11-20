# -*- coding: utf-8 -*-
import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from pandas import Series

from pandas_ta.utils import get_offset, verify_series

#: Points in the local forecast: catch22's `FC_LocalSimple_mean1` predicts
#: each return by the mean of the ONE return before it, i.e. by that return,
#: so the forecast residual is the first difference of the window. It is the
#: `1` in the feature's name, so it is a module constant and not a parameter.
TRAIN_LENGTH = 1
#: Fewest returns a window may hold: the residual then has 9 points and the
#: autocorrelation 8 lags. A smaller or missing `length` falls back to the
#: default.
MIN_LENGTH = 10
#: A window (or its residual) whose root mean square of deviations is at most
#: NOISE_ULPS machine epsilons does not vary: what is left is the rounding of
#: `c / c1 - 1`, and the sign of its autocorrelation is the sign of that
#: noise. NaN instead. The floor is ABSOLUTE because what it bounds is a
#: dimensionless RETURN; 4096 eps is this fork's existing habit on such a
#: quantity (`statistics/c22_periodicity.py`, `statistics/c22_ami_timescale.py`).
NOISE_ULPS = 4096
NOISE_FLOOR = NOISE_ULPS * np.finfo(float).eps  # 9.09e-13
#: Doubles of window to evaluate at once, so the peak memory is set by this
#: budget and not by `len(close) * length`.
CHUNK_VALUES = 1 << 19


def _first_zero_rows(x):
    """catch22's `CO_FirstZero` on each row of `x`: the first lag whose
    autocorrelation is NOT positive (`<= 0`), counting from lag 0.

    The autocorrelation at lag k is the lagged products of the demeaned row
    over its sum of squares -- a positive divisor -- so its sign is the sign
    of the products' sum alone and no division is taken. A row that never
    crosses would read its own length, as catch22's `maxtau = size` does;
    that cannot happen, because the biased autocovariances of a demeaned
    series over lags 1 .. m-1 sum to minus half the lag-0 one, so at least
    one of them is negative.

    Returns `(lag, ss)`: the lag as a float and the row's sum of squared
    deviations, which the caller uses for the noise floor and overflow guard.
    """
    rows, m = x.shape
    with np.errstate(invalid="ignore", over="ignore"):
        d = x - x.mean(axis=1, keepdims=True)
        ss = (d * d).sum(axis=1)
    out = np.full(rows, float(m))
    live = np.arange(rows)
    for k in range(1, m):
        if live.size == 0:
            break
        dl = d[live]
        with np.errstate(invalid="ignore", over="ignore"):
            p = (dl[:, :m - k] * dl[:, k:]).sum(axis=1)
        # catch22 walks `while (acf[k] > 0)`: an exact 0 IS the crossing, and
        # so is NaN, which the caller blanks anyway.
        hit = ~(p > 0.0)
        out[live[hit]] = k
        live = live[~hit]
    return out, ss


def _whiten_rows(block):
    """`FC_LocalSimple_mean1_tauresrat` on each row of `block`, a `(rows,
    length)` slab of one-bar SIMPLE RETURNS, oldest first: the first zero
    crossing of the autocorrelation of the 1-step mean-forecast residual,
    over that of the returns themselves.

    NaN for a row holding a non-finite return, for a row whose returns or
    whose residual have a root mean square of deviations at most
    `NOISE_FLOOR`, and for a row whose sums of squares overflow.
    """
    n = block.shape[1]
    bad = ~np.isfinite(block).all(axis=1)
    # Residual of the local mean forecast: return t minus the mean of the
    # TRAIN_LENGTH returns before it, for t = TRAIN_LENGTH .. n - 1. At the
    # catch22 setting that is `r[t] - r[t-1]`.
    fc = sliding_window_view(block, TRAIN_LENGTH, axis=1)[:, :-1].mean(axis=2)
    with np.errstate(invalid="ignore", over="ignore"):
        resid = block[:, TRAIN_LENGTH:] - fc
    tau_r, ss_r = _first_zero_rows(block)
    tau_e, ss_e = _first_zero_rows(resid)
    with np.errstate(invalid="ignore"):
        rms_r = np.sqrt(ss_r / n)
        rms_e = np.sqrt(ss_e / (n - TRAIN_LENGTH))
    # `~(x > FLOOR)` is True for 0.0 and for NaN; `~isfinite` catches the
    # sums of squares that overflow although every return is finite.
    bad |= ~(rms_r > NOISE_FLOOR) | ~(rms_e > NOISE_FLOOR)
    bad |= ~np.isfinite(ss_r) | ~np.isfinite(ss_e)
    return np.where(~bad, tau_e / tau_r, np.nan)


def c22_whiten_timescale(close, length=None, offset=None, **kwargs):
    """Indicator: catch22 whitening timescale ratio of returns (C22WHITEN)"""
    # Validate Arguments
    length = int(length) if length and int(length) >= MIN_LENGTH else 100
    close = verify_series(close, length + 1)
    offset = get_offset(offset)

    if close is None: return

    # Calculate Result
    c = close.to_numpy(dtype=float)
    # A close that is not a finite, normal, positive float (NaN, inf, zero,
    # negative, or subnormal such as 1e-310) is bad data: missing.
    c = np.where(np.isfinite(c) & (c >= np.finfo(float).tiny), c, np.nan)

    # The one-bar simple return as a price RATIO minus one: `8a / 8b` is the
    # same double as `a / b`, so a x2**k rescale cancels exactly here. A ratio
    # that overflows or underflows is bad data like a NaN close.
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        r = c[1:] / c[:-1] - 1.0
    r = np.where(np.isfinite(r), r, np.nan)

    n = c.size
    out = np.full(n, np.nan)
    if n >= length + 1:
        # The window ending at bar T holds the `length` returns of bars
        # T - length + 1 .. T, which read closes T - length .. T.
        win = sliding_window_view(r, length)
        rows = win.shape[0]
        step = max(1, CHUNK_VALUES // length)
        for a in range(0, rows, step):
            b = min(a + step, rows)
            out[length + a:length + b] = _whiten_rows(win[a:b])

    result = Series(out, index=close.index)

    # Offset
    if offset != 0:
        result = result.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        result.fillna(kwargs["fillna"], inplace=True)

    # Name and Categorize it
    result.name = f"C22WHITEN_{length}"
    result.category = "statistics"

    return result


c22_whiten_timescale.__doc__ = \
"""catch22 whitening timescale ratio of returns (C22WHITEN)

How much a one-step forecast shortens the memory of the last `length`
daily returns: predict each return by the one before it, and divide the
first zero crossing of the autocorrelation of what that forecast leaves
behind by the first zero crossing of the autocorrelation of the returns
themselves.

    C22WHITEN = tau(r[t] - r[t-1]) / tau(r),   tau(x) = the first lag
                whose autocorrelation of x is <= 0

**On anything noise-like THE NUMERATOR IS 1 AND THE COLUMN IS
`1 / tau(r)`.** Differencing a short-memory series makes its lag-1
autocorrelation about -1/2 (exactly -1/2 for white noise, -(1 - phi)/2 for
an AR(1) in population), so the residual crosses zero at lag 1 and only
the denominator moves. Measured on every window of six 1,500-bar frames:
the numerator is 1 on all 1,400 of the walk, the 1-kurus tick-rounded
walk, the 2-lira penny frame and the Student-t(3) path; on 1,397 of 1,400
of an AR(1) at phi = 0.6 (and on 1,400 at 0.3, 1,095 at 0.8, 691 at 0.9,
557 at 0.95, where sampling noise can flip a lag-1 autocorrelation near
zero); and on 0 of 1,400 only on an exact 20-bar cosine in returns, whose
residual is smooth too. So the column is a COARSE reciprocal ladder --
1, 1/2, 1/3, ... -- with 6 to 8 distinct values on the four noise-like
frames (17 on the AR(1) one), and it ties on 84.8% to 93.6% of
neighbouring bar pairs on the five stochastic frames. 1 means the returns'
own lag-1 autocorrelation is already <= 0; 0.5 that lag 1 was positive and
lag 2 not; and so on.

**Not `firstzero_ac`.** `FIRSTZEROAC_100` (Kats) reports the first lag where
a POSITIVE autocorrelation is followed by a negative one, so a window whose
lag-1 autocorrelation is already negative -- 368 to 821 of the 1,400
windows of the four noise-like frames -- reads 1 here and a later lag
there. Spearman against it per frame: +0.306, +0.634, -0.098, -0.999,
-0.962, +0.528 (walk, tick-rounded, penny, AR(1), cosine, Student-t).

Source: catch22 (Lubba, Sethi, Knaute, Schultz, Fulcher, Jones 2019,
*Data Mining and Knowledge Discovery* 33:1821, "catch22: CAnonical
Time-series CHaracteristics"), feature `FC_LocalSimple_mean1_tauresrat` --
the hctsa operation `FC_LocalSimple(y, 'mean', 1)`, output `taures` over
the input's own `CO_FirstZero(y, 'ac')` -- applied by PandasTa issue #139
to the last 100 daily simple returns. The reference implementation
(pycatch22) is **GPL-3.0** and this fork is MIT: this module was written
from the DEFINITIONS, no shipped module imports the reference (a test
asserts that over the whole package), and the reference was not run here
at all -- it is not installed on the machine this port was written on.

⚠ catch22 is a subset selected for TIME-SERIES CLASSIFICATION
performance on 93 reference problems. That is not return prediction, and
nothing here tests it on BIST: its presence in this fork is existence,
not evidence.

Gate A: a literal re-spelling of the published definition (z-score the
window, FFT autocorrelation padded to twice the next power of two,
`while acf[z] > 0 and z < maxtau: z++`, the mean-forecast residual by a
loop) agrees on **8,400 of 8,400** windows of six frames under numpy's
default dispatch and on 8,399 with its AVX2 and FMA3 dispatch disabled
(`docs/measure_c22_whiten_timescale_cpu.py A`). The one split is on the
exact cosine frame, where a deciding lagged sum is zero for the ideal cosine
and 6.8e-18 of the sum of squares on the rounded inputs. There the FFT
spelling rounds the wrong way, and this module agrees with an exact
`fractions.Fraction` oracle on all 1,400 cosine windows under both
dispatches. That oracle rounds zero times and disagrees on 0 of 648
windows sampled across the six frames.
This module never divides: the autocorrelation's divisor (the sum of
squares) is positive, so only the SIGN of each lagged sum is needed.
Z-scoring the window moves 0 of 1,200 sampled windows, and no exact-zero
lagged sum was met in any scan on the six frames, so catch22's `> 0`
against `>= 0` decided nothing there. `maxtau = size` is unreachable: the
biased autocovariances of a demeaned series over lags 1 .. m-1 sum to
minus half the lag-0 one, so some lag is negative.

Calculation:
    Default Inputs:
        length=100, TRAIN_LENGTH=1
    r[t]  = close[t] / close[t-1] - 1
    X     = r[T-length+1 .. T]                    (the window)
    E     = X[1:] - X[:-1]                        (1-step mean forecast)
    tau(x) = min k >= 1 with sum((x - mean x)[:-k] * (x - mean x)[k:]) <= 0
    C22WHITEN = tau(E) / tau(X)

**ONE blanking rule.** A window is NaN unless both the returns and the
residual have a root mean square of deviations above 9.09e-13 (4096 eps).
It is inert on anything with noise in it (0 of the sampled bars differ
from the unguarded reference on each of six frames). What it empties:
* a window with no variation: a price flat from bar 400 fires through
  bar 499 and blanks after;
* an exactly geometric price path (window sd at most 1.44e-16), which
  unguarded reads a value on every sampled window -- the sign pattern of
  rounding noise;
* returns that are an exact LINE in the bar index: the window varies (sd
  at least 2.89e-04) but the residual is a constant up to 2.37e-16.
Unlike `c22_periodicity`, a price rising one kurus a bar is NOT blanked:
its returns are a hyperbola, not a line, and this column fires on all
1,400 bars where `c22_periodicity` fires on none.

Causal: bar T reads closes T - length .. T. Measured by
future-perturbation sweep -- 0 of 35 offsets leak on each of six frames
with eight splices apiece, and 0 of 35 at `length` 10, 30 and 250 -- and
by seven mutants read off this file, edited and exec'd in memory. ⚠ The
sweep's power is limited by the ties: a one-bar look-ahead is caught at 8
of 35 offsets on the walk and the tick-rounded walk, 20 of 35 on the
AR(1) frame; a ten-bar one at 26 to 35 of 35.
Scale-free: bit-identical under x8, x64, 2**-40 and 2**40 on all six
frames, under x8 and x64 at `length` 10 / 30 / 250, and under x8 at price
levels 1e-6, 1e+6 and 1e+100 -- by construction, since the price enters
only as `c[t] / c[t-1]` and `8a / 8b` is the double `a / b`. x10, x3.7,
x0.1 and x1.0000001 move 0 bars on the five stochastic frames, whose
smallest deciding |lagged sum| / sum of squares is 1.66e-05; ⚠ on the
exact cosine frame they move 24 to 33 bars of 1,400, because there a
deciding lagged sum is ZERO in exact arithmetic (cos(pi/2)) and sits at
6.8e-18 of the sum of squares -- a rounding coin flip.
NaN on the first `length` bars; on every window holding a close that is
NaN, infinite, zero, negative or subnormal (101 bars at the default); on
a window holding a close pair whose ratio overflows (100 bars); on a
window whose sums of squares overflow although the returns are finite,
which a close pair of ratio 1e200 reaches and one of ratio 1e77 does not
(100 bars -- without that guard those bars read 1.0, a legal value,
measured); and under the blanking rule above.

Cost: the windows are walked in chunks and the lag scan stops for a row
once it crosses (the largest crossing lag on any window of the six
frames is 20, on the AR(1) one; 6 to 9 on the others): at n = 400,000 the traced peak
is 30.7 MB and the run took 1.9 s here. Budgets of 100, 400, 1,024 and
the default are bit-equal.

Args:
    close (pd.Series): Series of 'close's
    length (int): RETURNS per window, so `length + 1` closes. At least
        10, and a smaller or missing value falls back to the default.
        Default: 100
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)

Returns:
    pd.Series: C22WHITEN_{length}, a ratio of two whole numbers in
        1 .. length - 1; in practice 1 / tau(returns)
"""
