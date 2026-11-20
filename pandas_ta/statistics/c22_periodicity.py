# -*- coding: utf-8 -*-
import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from pandas import Series

from pandas_ta.utils import get_offset, verify_series

#: How much the autocorrelation must RISE from the trough before it for the
#: peak to count. The 0.01 is the catch22 operation's OWN parameter -- it is
#: the number in the name `PD_PeriodicityWang_th0_01` -- so it is a module
#: constant and not a function of `length`. The autocorrelation is normalised
#: by the window's own variance, so the threshold is dimensionless.
TH = 0.01
#: What a window with no qualifying peak reads. It is a SENTINEL, "no
#: periodicity found", and it is the FLOOR of the scale rather than a short
#: period: the smallest period the scan can report is 2.
NO_PERIOD = 0
#: Polynomial pieces and order of the detrending regression spline: two cubic
#: pieces joined at the middle of the window, i.e. the "single-knot cubic
#: regression spline" (three knots counting both ends) that Wang et al. use
#: and hctsa's `PD_PeriodicityWang` spells `spap2(2, 4, 1:N, y)`.
SPLINE_PIECES = 2
SPLINE_ORDER = 4
#: Free parameters of that spline: `SPLINE_PIECES + SPLINE_ORDER - 1` = 5.
SPLINE_DIM = SPLINE_PIECES + SPLINE_ORDER - 1
#: Fewest returns a window may hold. At `length` 30 the autocorrelation runs
#: to `ceil(30 / 3)` = 10 lags, so the scan has eight interior lags to test,
#: and the 5-parameter spline still leaves 25 residual degrees of freedom. A
#: smaller or missing `length` falls back to the default.
MIN_LENGTH = 30
#: A DETRENDED window whose root mean square is at most NOISE_ULPS machine
#: epsilons does not vary: what is left is the rounding of `c / c1 - 1` and of
#: the spline fit, and the period this column would report is the shape of
#: that noise. NaN instead. The floor is an ABSOLUTE constant because what it
#: bounds is a dimensionless RETURN, which has no rolling scale of its own to
#: keep causal; 4096 eps is this fork's existing habit on such a quantity
#: (`statistics/c22_ami_timescale.py`, `statistics/tf_autocorr_1e_60.py`,
#: `statistics/ts_binent_20.py`, `statistics/ts_strike_20.py`).
#:
#: It is applied to the RESIDUAL rather than to the window, and that is one
#: rule doing two jobs rather than a looser rule: the spline's own span
#: contains the constant function, so the residual's sum of squares never
#: exceeds the window's deviations from its mean, and a residual above the
#: floor therefore implies a window above it. What the residual form catches
#: in addition is a window whose returns ARE a spline in disguise -- an
#: exactly geometric price path, a polynomial drift -- where the window
#: varies but what the autocorrelations are taken on is fit rounding.
NOISE_ULPS = 4096
NOISE_FLOOR = NOISE_ULPS * np.finfo(float).eps  # 9.09e-13
#: Doubles of window to evaluate at once. Each chunk allocates a `(rows,
#: length)` residual slab plus a `(rows, ceil(length / 3))` autocorrelation
#: one, so this budget is what keeps the peak off `len(close) * length`.
CHUNK_VALUES = 1 << 19

#: Orthonormal bases of the spline space, one per window length. The basis
#: depends on `length` alone -- every window's x-grid is the same `0 .. n-1`,
#: rescaled to `[0, 1]` -- so it is built once and reused by every bar. One
#: entry is five columns of `length` doubles; a caller sweeping many lengths
#: pays that per length and nothing per bar.
_BASES = {}


def _spline_basis(n):
    """Orthonormal columns spanning the detrending spline's function space.

    The space is the piecewise cubics on `[0, 1]` with one interior break at
    `0.5` that are twice continuously differentiable there -- what a cubic
    (order 4) regression spline with two pieces fits. It has `SPLINE_DIM` = 5
    dimensions and the truncated power functions `1, t, t**2, t**3,
    (t - 0.5)**3 if t > 0.5 else 0` are a basis of it. A B-spline basis of the
    same knot vector spans the SAME space, so the least-squares fit -- and so
    the residual this module detrends with -- does not depend on which of the
    two is written down (measured against `scipy.interpolate.LSQUnivariateSpline`
    and against an exact rational solve in `docs/measure_c22_periodicity.py`).

    `np.linalg.qr` is applied once so the fit is a projection onto orthonormal
    columns, `y - Q (Q' y)`, which needs no normal equations and no inverse.
    """
    if n not in _BASES:
        t = np.arange(n, dtype=float) / (n - 1)
        cols = [t ** p for p in range(SPLINE_ORDER)]
        for piece in range(1, SPLINE_PIECES):
            knot = piece / SPLINE_PIECES
            cols.append(np.where(t > knot, (t - knot) ** (SPLINE_ORDER - 1), 0.0))
        _BASES[n] = np.linalg.qr(np.column_stack(cols))[0]
    return _BASES[n]


def _periodicity_rows(block):
    """Wang's periodicity, for each row of `block`.

    `block` is a `(rows, length)` slab of one-bar SIMPLE RETURNS, oldest
    first. Each row is detrended by a two-piece cubic regression spline, the
    autocorrelations of the residual are taken out to `ceil(length / 3)` lags,
    and the first lag that is a strict local MAXIMUM of them, stands at least
    `TH` above the last strict local minimum before it, and is itself
    non-negative, is the period. A row with no such lag reads `NO_PERIOD`.

    Comes back as NaN for a row holding a non-finite return and for a row
    whose DETRENDED root mean square is at most `NOISE_FLOOR` -- a flat
    window, a window whose returns are a spline in disguise, and a window
    whose sums of squares overflow.
    """
    rows, n = block.shape
    q = _spline_basis(n)

    # `~isfinite` carries the rows holding a bad return; without it the matrix
    # product below would spread one NaN across the whole residual row.
    bad = ~np.isfinite(block).all(axis=1)
    with np.errstate(invalid="ignore", over="ignore"):
        # Detrend: subtract the least-squares spline, spelled as a projection
        # onto the orthonormal basis of its own function space.
        resid = block - (block @ q) @ q.T
        # The residual of a fit whose span contains the constant function sums
        # to zero in exact arithmetic, so this demean is worth about 1e-18 of
        # the residual -- it is here because the autocorrelation of a series
        # is DEFINED on its deviations from its mean, not because it moves a
        # value (measured: 0 bars differ on each of the six frames).
        d = resid - resid.mean(axis=1, keepdims=True)
        ss = (d * d).sum(axis=1)
        rms = np.sqrt(ss / n)
    # `~(rms > NOISE_FLOOR)` is True for 0.0 and for NaN; `~isfinite(ss)` is
    # the limb that catches the +inf a window of enormous (but finite)
    # returns produces, which would otherwise CLEAR the floor.
    bad |= ~np.isfinite(ss) | ~(rms > NOISE_FLOOR)

    # Lags, out to a third of the window: beyond that the autocorrelation is
    # taken over fewer than two thirds of the pairs and Wang's measure stops
    # looking. `-(-n // 3)` is `ceil(n / 3)` in integers.
    acmax = -(-n // 3)
    acf = np.empty((rows, acmax))
    with np.errstate(invalid="ignore", divide="ignore", over="ignore"):
        den = np.where(ss > 0.0, ss, 1.0)
        for k in range(1, acmax + 1):
            # The BIASED autocorrelation: the `n - k` products that exist,
            # over the sum of squares of all `n` deviations. That is what
            # hctsa's `CO_AutoCorr(y, k, 'Fourier')` computes, and the
            # alternative (dividing by `n - k` instead) is a different column
            # -- see this module's __doc__.
            acf[:, k - 1] = (d[:, :n - k] * d[:, k:]).sum(axis=1) / den

    out = np.full(rows, float(NO_PERIOD))
    done = np.zeros(rows, dtype=bool)
    # The last strict local minimum seen at a lower lag than the lag being
    # tested, which is Wang's condition (a): a peak with no trough before it
    # is not a period however tall it is.
    have_trough = np.zeros(rows, dtype=bool)
    trough = np.zeros(rows)
    # Column `i` of `acf` is lag `i + 1`, so this walks lags 2 .. acmax - 1 in
    # order -- a local extremum needs a neighbour on each side -- and keeps
    # the FIRST qualifying peak. Every comparison against a NaN is False, so
    # such a row falls through to NO_PERIOD and is then emptied by `bad`.
    for i in range(1, acmax - 1):
        cur = acf[:, i]
        slope_in = cur - acf[:, i - 1]
        slope_out = acf[:, i + 1] - cur
        is_peak = (slope_in > 0.0) & (slope_out < 0.0)
        is_trough = (slope_in < 0.0) & (slope_out > 0.0)
        # (a) a trough before it, (b) at least TH above that trough, and
        # (c) a non-negative correlation.
        hit = (is_peak & have_trough & ~done
               & (cur - trough >= TH) & (cur >= 0.0))
        out[hit] = i + 1
        done |= hit
        # A lag is a peak, a trough, or neither, so the order of these two
        # within one iteration cannot matter.
        fresh = is_trough & ~done
        trough = np.where(fresh, cur, trough)
        have_trough |= fresh

    return np.where(~bad, out, np.nan)


def c22_periodicity(close, length=None, offset=None, **kwargs):
    """Indicator: catch22 Wang's periodicity of returns (C22PERIODICITY)"""
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
    # EXACTLY here and nothing downstream can see it. Both ends are finite,
    # positive and normal by now, so the ratio can still overflow or underflow
    # to zero -- 1e-300 followed by 1e50, say -- and such a pair is bad data in
    # the same way a NaN close is.
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
            out[length + a:length + b] = _periodicity_rows(win[a:b])

    result = Series(out, index=close.index)

    # Offset
    if offset != 0:
        result = result.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        result.fillna(kwargs["fillna"], inplace=True)

    # Name and Categorize it
    result.name = f"C22PERIODICITY_{length}"
    result.category = "statistics"

    return result


c22_periodicity.__doc__ = \
"""catch22 Wang's periodicity of returns (C22PERIODICITY)

The period of the last `length` daily returns, read the way Wang, Wirth
and Wang (2007) read one: detrend the window with a single-knot cubic
regression spline, take the autocorrelations of what is left out to a
third of the window, and report the FIRST lag that is a strict local
maximum of them, stands at least 0.01 above the last strict local
minimum before it, and is itself a non-negative correlation. A window
with no such lag reads 0.

    C22PERIODICITY = the first lag tau in 2 .. ceil(length/3) - 1 with
                     acf(tau) a strict local max, acf(tau) - acf(last
                     trough before tau) >= 0.01 and acf(tau) >= 0;
                     else 0

The output is a small INTEGER in `{0} union {2 .. 33}` at the default
`length`, and **0 is a SENTINEL, not a short period**: it means no peak
in the window's autocorrelation passed the three conditions. It is also
the FLOOR of the scale, so a consumer cannot read the column as a
magnitude without knowing that -- it is tagged `ORD` for that reason.
Over four stochastic 1,500-bar frames (an iid walk, a second walk
rounded to the kurus, a 2-lira stock on a 1-kurus tick, a Student-t(3)
path) it takes 11 to 15 distinct values, runs 3 .. 20, has median 5 and
reads the sentinel on **0** of those 5,600 bars; on an AR(1)-in-returns
path, 30 values, 0 .. 33, median 14, sentinel on 10 of 1,400. It TIES
on 79.3% to 100% of neighbouring bar pairs.

**The deterministic scale is a cosine, and the law is exact**: returns
that are an exact cosine of period P read exactly P on every fired bar
at P = 8, 10, 12, 15, 20 and 25. It degrades where the ceiling bites --
29 or 30 at P = 30, 32 or 33 at P = 33, and 0 or 33 at P = 34, the
first period past `ceil(length / 3) - 1` = 33, where the sentinel is the
median reading. At P = 40 and 60 EVERY fired bar reads the sentinel.
**A period much longer than a third of the window is invisible to this
measure, by construction.**

**THE DETREND IS LOAD-BEARING AND ITS KNOT STRUCTURE IS NOT A TASTE
CHOICE.** Over 467 windows of each STOCHASTIC frame (the cosine frame
moves 0 under every one of these, a constant column being immune),
dropping it entirely moves 50 to 202 bars (Spearman +0.47 to +0.86),
detrending by a straight line 37 to 177, by one cubic with no knot 18 to
107, with the knot at a third instead of the middle 12 to 70, and with
three pieces 26 to 119. The
shipped structure -- two cubic pieces, one knot, at the middle, by least
squares -- is also the one the reference implementation measurably
agrees with: on every window of six frames it reads the same value as
this module on **8,376 of 8,400** (99.71%, Spearman +0.9980). On the
stride-3 subsample of 2,802 of those windows the shipped reading agrees
on 99.71% and the five other structures on 83.2% (no detrend), 85.9%
(a line), 92.9% (one cubic), 95.5% (knot at a third) and 91.8% (three
pieces) -- `docs/measure_c22_periodicity.py` section P.
⚠ Those 24 windows are a REAL difference and the cause is not
identified. Each of the 8 that fall in the stride-3 subsample IS matched
by at least one of fourteen alternative readings, but no alternative is
better overall: the one that matches the most of them (the knot at a
third, 6 of 8) disagrees with the reference on 126 of those 2,802
windows, 124 of them windows where this reading agrees. Six of the
eight are decided by a quantity
sitting within 6e-03 of a boundary -- a plateau 3e-04 wide, a peak
1.8e-04 above zero, a rise 3.3e-04 above the threshold -- and two are
not, so part of the difference is structural rather than marginal. What
it is NOT is this module's own conditioning: four spellings of the same
fit sit 2.5e-14 (the independent B-spline) to 1.3e-12 (the
worst-conditioned, the normal equations) apart and move 0 of 1,200
windows, where the deciding quantities above need 1e-04 to 2e-01.
This column is therefore NOT bit-identical to the catch22
reference, unlike `c22_ami_timescale` -- so the 2026-10-24 screen's
Gate E figure (max |rho| 0.0413 vs `cdl_doji`, SHIP) was measured on
the REFERENCE's column and is an EXPECTATION for this one, not a
result for it.

Source: catch22 (Lubba, Sethi, Knaute, Schultz, Fulcher, Jones 2019,
*Data Mining and Knowledge Discovery* 33:1821, "catch22: CAnonical
Time-series CHaracteristics"), feature `PD_PeriodicityWang_th0_01` --
the hctsa operation `PD_PeriodicityWang`, whose own source is Wang,
Wirth and Wang, "Structure-based statistical features and multivariate
time series clustering", *Seventh IEEE International Conference on Data
Mining* 351-360 (2007), at threshold 0.01 -- applied by PandasTa issue
#126 to the last 100 daily simple returns. The reference implementation
(pycatch22 1.x) is **GPL-3.0** and this fork is MIT: this module was
written from the DEFINITIONS, no shipped module imports the reference (a
test asserts that over the whole package), and the one place it is run
at all is `docs/measure_c22_periodicity.py` section P -- opt-in,
measurement only, the same use the owner's own screen prototype makes of
it -- to answer whether this port is the column the 2026-10-24 screen
measured.

⚠ catch22 is a subset selected for TIME-SERIES CLASSIFICATION
performance on 93 reference problems. That is not return prediction, and
nothing here tests it on BIST: its presence in this fork is existence,
not evidence.

Gate A also checks the quantity three ways that share no code with this
module: an exact `fractions.Fraction` oracle that rounds ZERO times --
the input doubles, the spline basis on the window's grid, the
least-squares coefficients, the autocorrelations and all three Wang
conditions as exact rationals (0 disagreements on 648 windows); the same
spline space fitted by `np.linalg.lstsq` and by the normal equations
instead of by projection onto a QR factor (0 of 1,200 windows moved);
and `scipy.interpolate.LSQUnivariateSpline`, a least-squares cubic
B-SPLINE with one interior knot, which is an independent implementation
of what hctsa's `spap2(2, 4, 1:N, y)` means (0 of 1,200 moved, residuals
agreeing to 8.8e-15 .. 2.5e-14 of the residual's own size).

**The autocorrelation is the BIASED one** -- the `length - k` products
that exist over the sum of squares of all `length` deviations -- because
that is what the hctsa operation's own `CO_AutoCorr(y, k, 'Fourier')`
computes. The ADJUSTED spelling (the same products averaged over the
`length - k` pairs) is a different column, but only just: 2, 5 and 1 bars
of 467 move on the three frames where anything moves (tick-rounded,
AR(1), Student-t) and 0 on the walk, the penny and the cosine frame, and it is one
of the readings that match the reference where this one does not (4 of
the 8 sampled disagreements). Whether the mean is subtracted from the spline residual
before the products are taken moves **0** bars of 467 on each of the six
frames -- the residual of a fit whose span contains the constant
function already sums to zero.

⚠ **All three of Wang's conditions decide real values**, measured by
ablation over 467 windows per frame: dropping (a) "a trough before it"
moves up to 190 bars, allowing a negative peak -- condition (c) -- up to
319, and the 0.01 of condition (b) moves up to 15 bars at th = 0 and up
to 91 at th = 0.1. The STRICTNESS of the local-extremum test does not
(0 of 467 on all six frames, and 0 exactly flat slopes in 15,411 sampled
lag pairs). `ceil` against `floor` in the lag ceiling moves almost
nothing on a realistic frame -- 1 bar of 467, on the AR(1) one -- but it
sets the TOP of the scale: under `floor` the largest reportable period
at `length` 100 would be 32 rather than 33, and an exact 33-bar cosine
could not be read at all.

Calculation:
    Default Inputs:
        length=100, TH=0.01
    r[t]   = close[t] / close[t-1] - 1
    X      = r[T-length+1 .. T]                 (the window)
    S      = the least-squares cubic spline on two pieces (one interior
             knot, at the middle of the window) through X
    Y      = X - S                              (the detrended window)
    D      = Y - mean(Y)
    acf(k) = sum(D[:-k] * D[k:]) / sum(D * D),  k = 1 .. ceil(length/3)
    C22PERIODICITY = the first lag that is a strict local maximum of
                     acf, at least 0.01 above the last strict local
                     minimum before it, and non-negative; else 0

**ONE blanking rule, and it empties more than a reader expects.** The
window is NaN unless the DETRENDED root mean square clears 9.09e-13
(4096 eps). It is inert on anything with noise in it -- 0 bars differ
from the unguarded spelling on each of the six frames -- and it is one
rule doing two jobs, because the spline's span contains the constant
function, so the residual's sum of squares never exceeds the window's
own (measured: 0 rows of 1,400 break that on the frame built to break
it). What it empties:
* a window with no variation at all: a price that goes flat at bar 400
  blanks from bar 499, the first bar whose whole window of returns is
  zero -- unlike `c22_ami_timescale`, nothing blanks earlier;
* an exactly geometric price path, whose returns are constant up to
  rounding (3 to 5 distinct doubles per window, window sd ~1.2e-16).
  Unguarded it fires on all 1,400 bars of a 1,500-bar frame and reads
  inside [3, 11] -- values a reader could not tell from a real frame's;
* returns that ARE a cubic in the bar index, where the window varies
  (sd 2.81e-05 .. 1.15e-03, at least 30 million times the floor) but
  the spline fits it to 1.4e-16 and the autocorrelations would be the
  shape of the FIT's rounding. Unguarded: 1,400 bars reading inside
  [3, 13]. Both frames are rounding noise, so the exact SETS move with
  numpy's CPU dispatch; the spans hold under both measured here;
* ⚠ **a deterministically smooth price path**, which is the cost worth
  knowing: a price rising by exactly one kurus a bar from 100.00 is a
  smooth hyperbola in returns, the spline fits it to below the floor,
  and this column is NaN on all 1,400 bars where
  `c22_ami_timescale` fires. A real series with any noise in it is
  nowhere near this.

Causal: bar T reads closes T - length .. T. Measured by
future-perturbation sweep -- 0 of 35 offsets leak on each of six frames
with eight splices apiece, and 0 of 35 at `length` 30, 120 and 250 --
and by six mutants read off this file, edited and exec'd in memory.
⚠ The sweep's POWER is limited by the ties: a one-bar look-ahead mutant
is caught at 8 of 35 offsets (walk), 9 of 35 (tick-rounded) and 2 of 35
on a frame where the column is constant, while a ten-bar one is caught
33 to 35 of 35. Where a one-bar mutant moves a pre-splice bar it moves
exactly bar J - 1.
Scale-free: bit-identical under x8, x64, 2**-40 and 2**40 on all six
frames; under x8 and x64 at `length` 30 / 120 / 250; and under x8 at
price levels 1e-6, 1e+6 and 1e+100 -- BY CONSTRUCTION, since
the price enters only as `c[t] / c[t-1]`, and
`8a / 8b` is the double `a / b`. x10, x3.7, x0.1 and x1.0000001 come out
bit-identical too, which the arithmetic does not promise for an integer
decided by float comparisons; what makes it hold is measured, the
smallest margin in the deciding comparisons being 2.0e-05 (the slope at
the reported peak) and 3.3e-04 (the peak's rise above its trough,
against the 0.01 threshold).
NaN on the first `length` bars; on every window holding a close that is
NaN, infinite, zero, negative or subnormal (101 bars at the default);
on a window holding a close PAIR whose ratio overflows (100 bars); on a
window whose residual sum of squares OVERFLOWS although the returns
themselves are finite, which a close pair of ratio 1e200 reaches and
one of ratio 1e77 does not (100 bars -- without that guard those bars
read the SENTINEL 0, "no periodicity", measured); and under the
blanking rule above.

Cost: the windows are walked in chunks, so the peak is set by
`CHUNK_VALUES` and not by `len(close) * length`: at n = 400,000 the
traced peak is 23.8 MB (tracemalloc) and the run takes about 6 s.
Budgets of 100, 400, 1,024 and the default are bit-equal, so the chunk
boundary is invisible. Wall clock is not quoted as a band because it
does not reproduce.

Args:
    close (pd.Series): Series of 'close's
    length (int): RETURNS per window, so `length + 1` closes. At least
        30, and a smaller or missing value falls back to the default.
        ⚠ The lag ceiling DOES scale with it, `ceil(length / 3)`, so the
        column's range is a function of `length`. Default: 100
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)

Returns:
    pd.Series: C22PERIODICITY_{length}, a whole number in {0} union
        {2 .. ceil(length/3) - 1}
"""
