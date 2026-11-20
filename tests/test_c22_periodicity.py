# -*- coding: utf-8 -*-
"""C22-PERIODICITY: `c22_periodicity`, catch22's reading of Wang's
periodicity over the last 100 daily returns (issue #126).

Every number here was measured by `docs/measure_c22_periodicity.py` on this
machine; the receipt is `docs/C22PeriodicityMeasured.md`. What is pinned, in
order of how much it would hurt to lose:

1. **THE DETREND, AND ITS KNOT STRUCTURE.** The measure is the first
   qualifying peak of the autocorrelations of what a single-knot cubic
   REGRESSION SPLINE leaves behind, and that spline is not decoration: over
   467 windows of each STOCHASTIC frame (the constant cosine frame is immune
   to all of these and moves 0), dropping it moves 52 to 202 bars, a straight
   line 41 to 175, one cubic with no knot 19 to 105, the knot at a third
   instead of the middle 12 to 69, and three pieces 26 to 110. The shipped
   structure is also the one the GPL-3.0 reference measurably agrees with --
   99.85% of 8,400 windows, against 83.2% to 95.5% for those five on the
   2,802-window subsample both were scored on -- which is the evidence that
   `spap2(2, 4, 1:N, y)` was read correctly. Wang's three CONDITIONS are
   ablated the same way: dropping (a) "a trough before it" moves 124 to 190
   bars of 467 on four frames (and 0 on the AR(1) one, named rather than
   averaged in), allowing a negative peak -- (c) -- moves 106 to 190 on those
   same four frames and **316** on the AR(1) one, and (b)'s threshold at
   th = 0.1 moves up to 90.
1b. **THE AUTOCORRELATION'S DIVISOR, which the sources PIN.**
   `PD_PeriodicityWang` spells the line `acf(i) = mean(y(1:N-i).*y(i+1:N))`
   and catch22's C divides the same products by `size - tau`, both on a
   series catch22 z-scores BEFORE the detrend -- so the divisor is
   `(n - k) * var(window)` and condition (b)'s absolute 0.01 lives in
   pre-detrend z-scored units. ⚠ This module shipped the BIASED reading
   (the products over the RESIDUAL's own sum of squares) until 2026-11-20,
   and that deviation is priced here, not described: it moves 6 bars of
   2,802 and agrees with the reference on 2,794 of 2,802 where the shipped
   reading agrees on 2,798. The two conventions the source line does NOT fix
   -- the z-score's divisor (`ZSCORE_DDOF`) and whether the residual is
   re-centred -- move 0 of those 2,802 each.
2. **The exact rational oracle agrees.** An oracle that rounds ZERO times
   (input doubles, spline basis, least-squares coefficients,
   autocorrelations and all three Wang conditions as exact `Fraction`s --
   the z-score's square root cancels, since only `var` is needed)
   disagrees on 0 of 648 windows. Two more spellings of the same fit
   (`np.linalg.lstsq`, the normal equations) and one independent
   implementation of the same spline (`scipy.interpolate.LSQUnivariateSpline`,
   a B-spline basis) move 0 of 1,200 windows each.
3. **The cosine law is exact.** Returns that are an exact cosine of period P
   read exactly P on every fired bar at P = 8, 10, 12, 15, 20, 25 and 30 -- a
   CONSTANT column by construction, which is the feature working rather than
   a dead column. Past the lag ceiling `ceil(length / 3) - 1` = 33 the
   measure goes blind: at P = 34, 40 and 60 every fired bar reads the
   sentinel 0.
4. **0 is a SENTINEL and the FLOOR**, "no qualifying peak", not a short
   period. It is rare on the frames here (0 of 5,600 bars on the four
   stochastic non-AR frames, 10 of 1,400 on the AR(1) one), which is exactly
   why a consumer must not learn its meaning from the data.
5. **Causality.** 0 of 35 offsets leak on each of six frames with eight
   splices apiece, and 0 of 35 at `length` 30, 120 and 250. Seven mutants are
   read off this module's own source, edited and exec'd in memory.
   ⚠ A ONE-BAR look-ahead is only detectable on 8 of 35 offsets (walk) and 8
   of 35 (tick-rounded): the column is a small integer that ties on 79% to
   100% of neighbouring bar pairs, so most splices cannot witness the shift.
   The ten-bar mutant is caught 33 to 35 of 35. Prefix truncation would prove
   even less, which is why the mutants are here.
6. **Scale-free by construction, and bit-identically so.** The price enters
   only as the ratio `c[t] / c[t-1]`, so `8a / 8b` IS the double `a / b`:
   x8, x64, x2**-40 and x2**40 are bit-identical on all six frames; x8 and
   x64 at `length` 30, 120 and 250; x8 at price levels 1e-6, 1e+6 and 1e+100.
   x10, x3.7, x0.1 and x1.0000001 moved 0 bars of 8,400 here -- which the
   arithmetic does not promise for an integer decided by float comparisons;
   what makes it hold is the measured margin, the smallest deciding slope
   being 7.1e-05 and the smallest rise-above-threshold 2.6e-05.
7. **One blanking rule with a real cost.** A window is NaN unless its
   DETRENDED root mean square clears 9.09e-13. It is inert on anything with
   noise in it (0 bars differ from the unguarded spelling on each of six
   frames) and it empties a flat run, an exactly geometric ladder, a cubic
   in the returns, and -- the cost worth knowing -- a deterministically
   SMOOTH path such as a price rising one kurus a bar from 100.00, where
   `c22_ami_timescale` fires on all 1,400 bars and this column on none.
8. **Bad data.** A close that is NaN, infinite, zero, negative or subnormal
   empties exactly its own 101 windows; a close PAIR whose ratio overflows
   empties 100; and a window whose sums of squares overflow while the
   returns stay finite empties 100 -- without that last guard those bars
   read the SENTINEL 0, which is a value and not a blank.
9. **Gate E is OWED AGAIN.** It was measured on 2026-11-20 and that run is
   WITHDRAWN: the autocorrelation's divisor was corrected the same day
   (item 1b), so the run's module sha1, output fingerprint and counts belong
   to a column this tree no longer computes. The ledger row was removed,
   `test_the_gate_e_row_is_owed` asserts there is none, and
   `tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
   fails until the launcher re-runs Gate E and a receipt session records the
   new row. That failure is expected.
   ⚠ The 2026-10-24 screen's figure (max |rho| 0.0413 vs `cdl_doji`, SHIP)
   was measured on the PROTOTYPE, which is the GPL-3.0 reference's column,
   and this port is NOT bit-identical to it: 8,387 of 8,400 sampled windows
   equal, Spearman +0.9993. So that figure is an expectation, not a result.
10. **Gate C's real-data limb is owed too** -- every count in this file is
    synthetic. The receipt says so in §C4, keeps the withdrawn run's figures
    labelled as the pre-fix column's, and a test checks that it does.

Not pinned on purpose: exact counts of distinct values, exact bars-moved
counts under an inexact rescale, and any rho to 1e-6. Those move with
numpy's CPU dispatch; the tests pin bounds and bands, and the docstrings
state the local figure.
"""
import csv
import importlib
import importlib.util
import math
from fractions import Fraction
from pathlib import Path

import numpy as np
import pytest
from pandas import DataFrame, Series

from .context import pandas_ta
from pandas_ta.statistics.c22_periodicity import (
    CHUNK_VALUES, MIN_LENGTH, NOISE_FLOOR, NO_PERIOD, SPLINE_DIM, TH,
    ZSCORE_DDOF, _spline_basis, c22_periodicity)

ROOT = Path(__file__).resolve().parent.parent
MODULE = importlib.import_module("pandas_ta.statistics.c22_periodicity")
SRC = Path(MODULE.__file__).read_text(encoding="utf-8")
LENGTH = 100
ACMAX = -(-LENGTH // 3)

#: Strides for the oracles that are too slow for all 1,400 windows of a
#: frame. Every count asserted below is a count of what actually ran.
EXACT_STRIDE = 97
WINDOW_STRIDE = 7


# ------------------------------------------------------------- frames
def walk(n=1500, seed=11, sigma=0.015, level=100.0):
    rng = np.random.default_rng(seed)
    return Series(level * np.exp(np.cumsum(rng.normal(0.0, sigma, n))))


def tick_rounded(n=1500, seed=55):
    return Series(np.round(walk(n, seed).to_numpy(), 2))


def penny(n=1500, seed=23, level=2.0, sigma=0.012):
    """A 2-lira stock on a 1-kurus tick: 21.7% of returns are exactly 0."""
    return Series(np.round(walk(n, seed, sigma, level).to_numpy(), 2))


def ar1(n=1500, seed=7, sigma=0.01, phi=0.6):
    rng = np.random.default_rng(seed)
    e = rng.normal(0.0, sigma, n)
    r = np.empty(n)
    r[0] = e[0]
    for t in range(1, n):
        r[t] = phi * r[t - 1] + e[t]
    return Series(100.0 * np.cumprod(1.0 + r))


def cosine_returns(n=1500, period=20.0, amp=0.01):
    t = np.arange(n, dtype=float)
    return Series(100.0 * np.cumprod(1.0 + amp * np.cos(2 * np.pi * t / period)))


def student_t(n=1500, seed=19, df=3, sigma=0.01):
    rng = np.random.default_rng(seed)
    r = sigma * rng.standard_t(df, n)
    return Series(100.0 * np.cumprod(1.0 + np.clip(r, -0.5, 0.5)))


def ladder(n=1500, step=0.01, start=100.0):
    return Series(start * (1.0 + step) ** np.arange(n, dtype=float))


def cubic_returns(n=1500, scale=0.02):
    """Returns that ARE a cubic in the bar index: the detrending spline fits
    them to rounding, so what is left is the FIT's own noise."""
    t = np.arange(n, dtype=float) / (n - 1)
    r = scale * (1.0 - 3.0 * t + 2.0 * t ** 3)
    return Series(100.0 * np.cumprod(1.0 + r))


FRAMES = {
    "walk": walk(),
    "tick-rounded": tick_rounded(),
    "penny": penny(),
    "ar1": ar1(),
    "cosine": cosine_returns(),
    "student-t": student_t(),
}
#: The five frames whose returns are not deterministic. The cosine frame is
#: CONSTANT by construction (section 3 of this file's docstring), so it is
#: excluded from "not constant" assertions and named in them instead.
STOCHASTIC = [k for k in FRAMES if k != "cosine"]
_BASE = {}


def base(name):
    if name not in _BASE:
        _BASE[name] = c22_periodicity(FRAMES[name])
    return _BASE[name]


def windows(close, length=LENGTH):
    c = np.asarray(close, float)
    r = c[1:] / c[:-1] - 1.0
    win = np.lib.stride_tricks.sliding_window_view(r, length)
    return win, np.arange(length, length + win.shape[0])


def same(a, b):
    x, y = np.asarray(a, float), np.asarray(b, float)
    return x.shape == y.shape and bool(
        np.all((x == y) | (np.isnan(x) & np.isnan(y))))


def diff_bars(a, b):
    x, y = np.asarray(a, float), np.asarray(b, float)
    both = ~np.isnan(x) & ~np.isnan(y)
    return (int(np.sum(x[both] != y[both])),
            int(np.sum(np.isnan(x) != np.isnan(y))))


def spearman(a, b):
    x, y = Series(np.asarray(a, float)), Series(np.asarray(b, float))
    m = x.notna() & y.notna()
    if int(m.sum()) < 3:
        return float("nan")
    rx, ry = x[m].rank(), y[m].rank()
    if rx.std() == 0 or ry.std() == 0:
        return float("nan")
    return float(np.corrcoef(rx, ry)[0, 1])


# ------------------------------------------------------------- Gate A
def _scan(acf, th=TH, strict=True, need_trough=True, need_positive=True):
    """The Wang scan over a list of autocorrelations; index i is lag i + 1.

    `need_trough` and `need_positive` ablate Wang's conditions (a) and (c),
    which `test_wangs_other_two_conditions_are_load_bearing` prices.
    """
    trough = None
    for i in range(1, len(acf) - 1):
        cur = acf[i]
        slope_in, slope_out = cur - acf[i - 1], acf[i + 1] - cur
        if strict:
            is_peak = slope_in > 0 and slope_out < 0
            is_trough = slope_in < 0 and slope_out > 0
        else:
            is_peak = slope_in >= 0 and slope_out <= 0
            is_trough = slope_in <= 0 and slope_out >= 0
        if is_peak and (trough is not None or not need_trough):
            tall = trough is None or cur - trough >= th
            if tall and (cur >= 0 or not need_positive):
                return i + 1
        if is_trough:
            trough = cur
    return NO_PERIOD


def _basis(n, knots=(0.5,), degree=3):
    t = np.arange(n, dtype=float) / (n - 1)
    cols = [t ** p for p in range(degree + 1)]
    cols += [np.where(t > k, (t - k) ** degree, 0.0) for k in knots]
    return np.column_stack(cols)


def resid_qr(window, **kw):
    w = np.asarray(window, float)
    q = np.linalg.qr(_basis(w.size, **kw))[0]
    return w - q @ (q.T @ w)


def resid_lstsq(window):
    w = np.asarray(window, float)
    x = _basis(w.size)
    return w - x @ np.linalg.lstsq(x, w, rcond=None)[0]


def resid_normal(window):
    w = np.asarray(window, float)
    x = _basis(w.size)
    return w - x @ np.linalg.solve(x.T @ x, x.T @ w)


def resid_scipy(window):
    from scipy.interpolate import LSQUnivariateSpline
    w = np.asarray(window, float)
    x = np.arange(w.size, dtype=float)
    return w - LSQUnivariateSpline(x, w, t=[(w.size - 1) / 2.0], k=3)(x)


def value_src(window, th=TH, ddof=ZSCORE_DDOF, fit=None, demean=True,
              strict=True, acmax=None, need_trough=True, need_positive=True):
    """The SOURCE spelling of the quantity, written without the module.

    catch22 z-scores the series BEFORE the detrend, and both
    `PD_PeriodicityWang` (`acf(i) = mean(y(1:N-i).*y(i+1:N))`) and catch22's
    C reference (`acf[tau-1] /= size - tau`) average each lag's products over
    the `n - k` pairs that exist. So: z-score, detrend, average, scan. The
    module divides one sum by `(n - k) * var` instead of dividing the series
    by `sd` first, which is the same quantity rounded differently.

    `fit` takes the z-scored window and returns its residual.
    """
    w = np.asarray(window, float)
    n = w.size
    sd = float(w.std(ddof=ddof))
    if not (np.isfinite(sd) and sd > 0.0):
        return float("nan")
    z = (w - w.mean()) / sd
    r = (fit or resid_qr)(z)
    d = r - r.mean() if demean else r
    m = acmax or -(-n // 3)
    acf = [float((d[:n - k] * d[k:]).sum()) / (n - k) for k in range(1, m + 1)]
    if not np.isfinite(acf).all():
        return float("nan")
    return float(_scan(acf, th=th, strict=strict, need_trough=need_trough,
                       need_positive=need_positive))


def value_biased(resid, th=TH):
    """The reading this module shipped until 2026-11-20 and no longer does:
    the lagged products over the RESIDUAL's own sum of squares. Kept so the
    deviation from the source line can be priced rather than asserted."""
    r = np.asarray(resid, float)
    n = r.size
    d = r - r.mean()
    ss = float((d * d).sum())
    if not ss > 0.0:
        return float("nan")
    acf = [float((d[:n - k] * d[k:]).sum()) / ss
           for k in range(1, -(-n // 3) + 1)]
    return float(_scan(acf, th=th))


def src_acf(window):
    """The autocorrelations the shipped scan reads, spelled as the module
    spells them: products of the spline residual over `(n - k) * var`, `var`
    taken on the window BEFORE the detrend."""
    w = np.asarray(window, float)
    n = w.size
    d = resid_qr(w)
    d = d - d.mean()
    var = float(w.var(ddof=ZSCORE_DDOF))
    return np.array([float((d[:n - k] * d[k:]).sum()) / ((n - k) * var)
                     for k in range(1, -(-n // 3) + 1)])


def value_exact(window):
    """The definition in exact rational arithmetic -- zero roundings.

    The z-score's `sd` is irrational and never needed: the quantity divides
    by `(n - k) * var`, and `var` is rational."""
    y = [Fraction(float(v)) for v in window]
    n = len(y)
    t = [Fraction(i, n - 1) for i in range(n)]
    half = Fraction(1, 2)
    cols = [[Fraction(1)] * n, t, [v * v for v in t], [v ** 3 for v in t],
            [(v - half) ** 3 if v > half else Fraction(0) for v in t]]
    assert len(cols) == SPLINE_DIM
    g = [[sum(a[k] * b[k] for k in range(n)) for b in cols] for a in cols]
    rhs = [sum(a[k] * y[k] for k in range(n)) for a in cols]
    # Exact Gaussian elimination with partial pivoting.
    m = len(rhs)
    aug = [list(g[i]) + [rhs[i]] for i in range(m)]
    for col in range(m):
        piv = max(range(col, m), key=lambda r: abs(aug[r][col]))
        assert aug[piv][col] != 0
        aug[col], aug[piv] = aug[piv], aug[col]
        inv = Fraction(1, 1) / aug[col][col]
        aug[col] = [v * inv for v in aug[col]]
        for r in range(m):
            if r != col and aug[r][col] != 0:
                f = aug[r][col]
                aug[r] = [v - f * w for v, w in zip(aug[r], aug[col])]
    coef = [aug[i][m] for i in range(m)]
    fit = [sum(coef[j] * cols[j][k] for j in range(m)) for k in range(n)]
    resid = [y[k] - fit[k] for k in range(n)]
    mean = sum(resid, Fraction(0)) / n
    d = [v - mean for v in resid]
    ss = sum(v * v for v in d)
    wmean = sum(y, Fraction(0)) / n
    var = sum((v - wmean) ** 2 for v in y) / (n - ZSCORE_DDOF)
    if ss == 0 or var == 0:
        return float("nan")
    acf = [sum(d[i] * d[i + k] for i in range(n - k)) / ((n - k) * var)
           for k in range(1, -(-n // 3) + 1)]
    return float(_scan(acf, th=Fraction(1, 100)))


@pytest.mark.parametrize("frame", ["walk", "penny", "ar1", "cosine"])
def test_bit_equal_to_the_exact_rational_oracle(frame):
    """Gate A's strongest limb: an oracle that rounds ZERO times.

    Every input double is an exact rational, so the spline's normal
    equations, its coefficients, the residual, the autocorrelations and all
    three of Wang's conditions can be decided exactly. Measured: 0
    disagreements on all six frames at stride 13 (648 windows); four frames
    at stride 97 here, for runtime.
    """
    win, bars = windows(FRAMES[frame])
    ran = 0
    for i in range(0, win.shape[0], EXACT_STRIDE):
        mine = float(base(frame).iloc[int(bars[i])])
        want = value_exact(win[i])
        assert mine == want or (math.isnan(mine) and math.isnan(want)), \
            (frame, int(bars[i]), mine, want)
        ran += 1
    assert ran >= 14, ran


@pytest.mark.parametrize("how", ["lstsq", "normal", "scipy"])
@pytest.mark.parametrize("frame", list(FRAMES))
def test_the_same_spline_space_fitted_another_way_agrees(how, frame):
    """The shipped fit is a projection onto the QR factor of the truncated
    power basis. `np.linalg.lstsq` and the normal equations are two other
    spellings of it; `scipy.interpolate.LSQUnivariateSpline` is an
    independent implementation of the same least-squares cubic spline in a
    B-SPLINE basis -- which is the basis hctsa's `spap2(2, 4, 1:N, y)` uses.
    Measured: 0 of 1,200 windows move for each, residuals agreeing to
    8.8e-15 .. 1.3e-12 of their own size.
    """
    if how == "scipy" and importlib.util.find_spec("scipy") is None:
        pytest.skip("scipy is not installed")
    fit = {"lstsq": resid_lstsq, "normal": resid_normal,
           "scipy": resid_scipy}[how]
    win, bars = windows(FRAMES[frame])
    moved = ran = 0
    for i in range(0, win.shape[0], WINDOW_STRIDE):
        mine = float(base(frame).iloc[int(bars[i])])
        other = value_src(win[i], fit=fit)
        moved += int(not (mine == other
                          or (math.isnan(mine) and math.isnan(other))))
        ran += 1
    assert ran >= 199, ran
    assert moved == 0, (how, frame, moved)


@pytest.mark.parametrize("period", [8, 10, 12, 15, 20, 25, 30])
def test_a_cosine_in_returns_reads_its_own_period(period):
    """The deterministic scale: a return series that is an exact cosine of
    period P reads exactly P, on every fired bar. This is the law that says
    the column measures a PERIOD and not an index into something."""
    s = c22_periodicity(cosine_returns(period=float(period))).dropna()
    assert int(s.size) == 1400, int(s.size)
    assert set(s.to_numpy().tolist()) == {float(period)}


def test_the_lag_ceiling_is_a_ceil_and_its_top_lag_is_reachable():
    """`acmax = ceil(length / 3)` = 34 at the default, so the largest period
    the scan can report is 33 and the documented range is `{0} ∪ {2 .. 33}`.
    Change that `ceil` to a `floor` and the range silently becomes
    `{2 .. 32}` while every other test here still passes -- the range test
    asserts an upper bound, the exact oracle computes its own ceiling, and
    the cosine law is otherwise only exercised at P <= 25. So: an exact
    cosine of period 33 must still read 33, which it does on the median bar
    (values {32, 33}) under both CPU dispatches -- and at `length` 50, where
    `ceil` gives 17 lags and `floor` gives 16, a 16-bar cosine must still
    read 16, which the `floor` spelling cannot do (its scan would stop at
    lag 15)."""
    s = c22_periodicity(cosine_returns(period=33.0)).dropna()
    assert float(s.max()) == float(ACMAX - 1) == 33.0
    assert float(s.median()) == float(ACMAX - 1)
    short = c22_periodicity(cosine_returns(period=16.0), length=50).dropna()
    assert float(short.median()) == 16.0


@pytest.mark.parametrize("period", [34, 40, 60])
def test_a_period_past_the_lag_ceiling_reads_the_sentinel(period):
    """The autocorrelations stop at `ceil(length / 3)` and a peak needs a
    neighbour on each side, so no period above 33 can be reported at
    `length` 100. Measured: every fired bar reads the sentinel at P = 34, 40
    and 60. Only the median is pinned at P = 34, the first period over the
    ceiling, where a peak can still sit on the ceiling itself and the exact
    set is a rounding question."""
    s = c22_periodicity(cosine_returns(period=float(period))).dropna()
    assert float(s.median()) == float(NO_PERIOD)
    if period >= 40:
        assert set(s.to_numpy().tolist()) == {float(NO_PERIOD)}


@pytest.mark.parametrize("knots,degree,floor_moved", [
    ((), 1, 30),       # a straight line
    ((), 3, 12),       # one cubic, no knot
    ((1 / 3,), 3, 8),  # the knot a third of the way in
    ((1 / 3, 2 / 3), 3, 20),  # three pieces
])
@pytest.mark.parametrize("frame", STOCHASTIC)
def test_the_detrend_structure_is_load_bearing(knots, degree, floor_moved,
                                               frame):
    """A later "simplification" of the spline would change shipped values.
    Measured over 467 windows of each stochastic frame: a straight line moves
    41 to 175 bars, one cubic 19 to 105, the knot at a third 12 to 69, three
    pieces 26 to 110. The bounds here are well under the smallest of those,
    because the exact count moves with numpy's CPU dispatch."""
    win, bars = windows(FRAMES[frame])
    idx = list(range(0, win.shape[0], 3))
    mine = [float(base(frame).iloc[int(bars[i])]) for i in idx]
    other = [value_src(win[i],
                       fit=lambda z: resid_qr(z, knots=knots, degree=degree))
             for i in idx]
    moved = diff_bars(mine, other)[0]
    assert moved >= floor_moved, (frame, knots, degree, moved)


@pytest.mark.parametrize("frame", STOCHASTIC)
def test_dropping_the_detrend_is_the_biggest_change_of_all(frame):
    """Not detrending at all moves 52 to 202 bars of 467 and drops the rank
    correlation to +0.49 .. +0.85 -- so the spline is the step that makes
    this column what it is."""
    win, bars = windows(FRAMES[frame])
    idx = list(range(0, win.shape[0], 3))
    mine = [float(base(frame).iloc[int(bars[i])]) for i in idx]
    other = [value_src(win[i], fit=lambda z: z) for i in idx]
    assert diff_bars(mine, other)[0] >= 30, frame
    assert spearman(mine, other) < 0.95


def test_the_shipped_autocorrelation_is_the_source_line_not_the_biased_one():
    """The divisor is PINNED by the sources, and it is not the biased one.

    `PD_PeriodicityWang` does not call `CO_AutoCorr`: it spells the line
    `acf(i) = mean(y(1:N-i).*y(i+1:N))`, and catch22's C reference divides
    the same products by `size - tau` -- the ADJUSTED divisor, on a series
    catch22 z-scores BEFORE the detrend, which is what makes condition (b)'s
    absolute 0.01 dimensionless. This module shipped the BIASED reading (the
    products over the residual's own sum of squares) until 2026-11-20 and
    attributed it to `CO_AutoCorr(.., 'Fourier')`; that was wrong, and the
    deviation is priced here rather than described.

    Measured: the biased reading moves 6 bars of 2,802 windows of six frames
    (1 tick-rounded, 4 AR(1), 1 Student-t; 0 on the walk, the penny and the
    cosine) and it agrees with the GPL-3.0 reference on 2,794 of 2,802 where
    the shipped reading agrees on 2,798 (receipt §P1b). The count is POOLED
    over the three frames that move (measured 6, bound 3) because two of
    them move a single bar and one bar of CPU-dispatch drift must not turn a
    true statement red.
    """
    moved = 0
    for frame in ("tick-rounded", "ar1", "student-t"):
        win, bars = windows(FRAMES[frame])
        idx = list(range(0, win.shape[0], 3))
        mine = [float(base(frame).iloc[int(bars[i])]) for i in idx]
        other = [value_biased(resid_qr(win[i])) for i in idx]
        moved += diff_bars(mine, other)[0]
    assert moved >= 3, moved
    # and the module says so where a reader will look
    doc = c22_periodicity.__doc__
    assert "mean(y(1:N-i).*y(i+1:N))" in doc
    assert "size - tau" in doc


@pytest.mark.parametrize("frame", list(FRAMES))
def test_the_two_conventions_the_source_line_leaves_open_move_nothing(frame):
    """The source line fixes neither the z-score's divisor nor whether the
    spline residual is re-centred before the products, so both are measured
    rather than argued: 0 bars of 467 on each of six frames for each, and
    both readings agree with the reference on the same 2,798 of 2,802
    windows (receipt §P1b). `ZSCORE_DDOF` is 1 because that is MATLAB
    `zscore`'s divisor and so hctsa's."""
    win, bars = windows(FRAMES[frame])
    idx = list(range(0, win.shape[0], 3))
    mine = [float(base(frame).iloc[int(bars[i])]) for i in idx]
    pop = [value_src(win[i], ddof=0) for i in idx]
    raw = [value_src(win[i], demean=False) for i in idx]
    assert diff_bars(mine, pop)[0] == 0, frame
    assert diff_bars(mine, raw)[0] == 0, frame
    assert ZSCORE_DDOF == 1


@pytest.mark.parametrize("frame", list(FRAMES))
def test_demeaning_the_residual_moves_nothing(frame):
    """The spline's span contains the constant function, so its residual
    already sums to zero: the demean inside the autocorrelation is there
    because that is what an autocorrelation IS, not because it moves a
    value. Measured: 0 bars of 467 on each frame, spelled here through the
    module's own normalisation rather than through `value_src`'s."""
    win, bars = windows(FRAMES[frame])
    idx = list(range(0, win.shape[0], 3))
    mine = [float(base(frame).iloc[int(bars[i])]) for i in idx]
    other = []
    for i in idx:
        w = win[i]
        r = resid_qr(w)
        var = float(w.var(ddof=ZSCORE_DDOF))
        n = w.size
        acf = [float((r[:n - k] * r[k:]).sum()) / ((n - k) * var)
               for k in range(1, ACMAX + 1)]
        other.append(float(_scan(acf)) if var > 0 else float("nan"))
    assert diff_bars(mine, other)[0] == 0, frame


@pytest.mark.parametrize("frame", STOCHASTIC)
def test_the_threshold_is_load_bearing(frame):
    """Wang's third condition -- the peak must stand `th` above the trough
    before it -- is the 0.01 in the feature's own name. At th = 0.1 between
    38 and 90 bars of 467 move on the stochastic frames; at th = 0 between 0
    and 15 do."""
    win, bars = windows(FRAMES[frame])
    idx = list(range(0, win.shape[0], 3))
    mine = [float(base(frame).iloc[int(bars[i])]) for i in idx]
    ten = [value_src(win[i], th=0.1) for i in idx]
    assert diff_bars(mine, ten)[0] >= 20, frame


@pytest.mark.parametrize("frame", ["walk", "tick-rounded", "penny",
                                   "student-t"])
def test_wangs_other_two_conditions_are_load_bearing(frame):
    """Conditions (a) "a trough before it" and (c) "a non-negative peak" are
    the two the scan's bookkeeping could most easily get wrong, so they are
    ablated rather than trusted. Over 467 windows per frame, dropping (a)
    moves 124 to 190 bars on these four frames and allowing a negative peak
    moves 106 to 190 on them -- and 316 on the AR(1) frame, which the next
    test covers for (a) and §A6b tabulates for both.
    ⚠ Two frames are excluded BY NAME rather than averaged in: on the AR(1)
    frame dropping (a) moves 0 (its autocorrelation always dips before the
    reported peak) and the constant cosine frame moves 0 under both."""
    win, bars = windows(FRAMES[frame])
    idx = list(range(0, win.shape[0], 3))
    mine = [float(base(frame).iloc[int(bars[i])]) for i in idx]
    no_trough = [value_src(win[i], need_trough=False) for i in idx]
    any_sign = [value_src(win[i], need_positive=False) for i in idx]
    assert diff_bars(mine, no_trough)[0] >= 50, frame
    assert diff_bars(mine, any_sign)[0] >= 50, frame


def test_dropping_the_trough_condition_is_inert_on_the_ar1_frame():
    """The other half of the measurement above, named rather than hidden: on
    the AR(1) frame condition (a) costs nothing, because that frame's
    autocorrelation always has a strict local minimum before the lag the
    column reports. Measured: 0 bars of 467."""
    win, bars = windows(FRAMES["ar1"])
    idx = list(range(0, win.shape[0], 3))
    mine = [float(base("ar1").iloc[int(bars[i])]) for i in idx]
    other = [value_src(win[i], need_trough=False) for i in idx]
    assert diff_bars(mine, other)[0] == 0


@pytest.mark.parametrize("frame", list(FRAMES))
def test_the_strictness_of_the_extremum_test_is_unreached_on_every_frame_measured(
        frame):
    """`<` against `<=` in the slope tests picks the same lag on every window
    sampled (0 of 467 on all six frames), because no sampled slope is exactly
    flat: 0 of 15,411 lag pairs per frame. ⚠ Six SYNTHETIC frames; real BIST
    windows are unmeasured here (receipt §C4), so this is a result about this
    sample and not a property of the column. The strictness is kept because
    that is what a local extremum means."""
    win, bars = windows(FRAMES[frame])
    idx = list(range(0, win.shape[0], 3))
    mine = [float(base(frame).iloc[int(bars[i])]) for i in idx]
    other = [value_src(win[i], strict=False) for i in idx]
    assert diff_bars(mine, other)[0] == 0, frame
    flat = 0
    for i in idx[::7]:
        flat += int(np.sum(np.diff(src_acf(win[i])) == 0.0))
    assert flat == 0, (frame, flat)


@pytest.mark.parametrize("frame", list(FRAMES))
def test_z_scoring_the_window_changes_nothing(frame):
    """The module z-scores the window itself, as catch22 does, so z-scoring
    the INPUT must be inert: the spline fit is equivariant and the z-score of
    a z-score is itself up to rounding. Measured on 200 windows per frame: 0
    moved -- which also means a caller handing this column pre-normalised
    returns gets the same values. It is true of the reference too (61 of 61
    windows, receipt §P2)."""
    win, bars = windows(FRAMES[frame])
    for i in range(0, win.shape[0], WINDOW_STRIDE):
        w = win[i]
        z = (w - w.mean()) / w.std()
        a = float(base(frame).iloc[int(bars[i])])
        b = value_src(z)
        assert a == b or (math.isnan(a) and math.isnan(b)), (frame, i, a, b)


def test_the_reference_implementation_is_not_imported_by_shipped_code():
    """The reference (pycatch22) is GPL-3.0 and this fork is MIT. The claim
    that has to hold is about the shipped CODE PATH, so this sweeps every
    `.py` file under `pandas_ta/` for an import of it -- 397 files on this
    tree, 0 hits. ⚠ pycatch22 IS installed in the owner's worktree, so the
    guard is not vacuous; `importlib.util.find_spec` reports that without
    executing the package."""
    hits = []
    files = sorted((ROOT / "pandas_ta").rglob("*.py"))
    for p in files:
        for line in p.read_text(encoding="utf-8").splitlines():
            s = line.strip()
            if (s.startswith("import ") or s.startswith("from ")) \
                    and "catch22" in s.replace("c22", ""):
                hits.append((str(p.relative_to(ROOT)), s))
    assert hits == [], hits
    assert len(files) > 300, len(files)


@pytest.mark.parametrize("frame", list(FRAMES))
def test_the_output_is_a_whole_number_in_the_documented_range(frame):
    s = base(frame).dropna().to_numpy()
    assert np.all(s == np.floor(s))
    assert s.min() >= 0.0
    assert s.max() <= ACMAX - 1
    assert not np.any((s > 0.0) & (s < 2.0)), "lag 1 cannot be a peak"


def test_the_module_docstring_attributes_the_source():
    doc = c22_periodicity.__doc__
    for needle in ("Lubba", "33:1821", "PD_PeriodicityWang", "Wang",
                   "2007", "GPL-3.0", "#126"):
        assert needle in doc, needle
    assert "classification" in doc.lower()
    assert "existence" in doc and "not evidence" in doc


# ------------------------------------------------------------- Gate B
MUTANTS = {
    "write-back-dated": ("out[length + a:length + b]",
                         "out[length - 1 + a:length - 1 + b]"),
    "window-one-ahead": ("win = sliding_window_view(r, length)",
                         "win = sliding_window_view(r, length + 1)[:, 1:]"),
    "window-ten-ahead": ("win = sliding_window_view(r, length)",
                         "win = sliding_window_view(r, length + 10)[:, 10:]"),
    "returns-rolled": ("r = np.where(np.isfinite(r), r, np.nan)",
                       "r = np.roll(np.where(np.isfinite(r), r, np.nan), -1)"),
    "mask-back-dated": ("r = np.where(np.isfinite(r), r, np.nan)",
                        "r = np.where(np.isfinite(np.roll(r, -1)), r, np.nan)"),
    "chunk-wide-demean": ("d = resid - resid.mean(axis=1, keepdims=True)",
                          "d = resid - resid.mean()"),
    "no-overflow-guard": ("bad |= ~np.isfinite(ss) | ~np.isfinite(var)",
                          "bad |= np.zeros_like(bad)"),
}


def mutant(name):
    """Read this module off disk, edit one write, exec it in memory."""
    old, new = MUTANTS[name]
    assert SRC.count(old) == 1, (name, SRC.count(old))
    ns = {}
    exec(compile(SRC.replace(old, new), f"<mutant {name}>", "exec"), ns)
    return ns["c22_periodicity"]


def _spliced(close, j, seed=909):
    rng = np.random.default_rng(seed + j)
    c = close.to_numpy(dtype=float).copy()
    c[j:] = c[j - 1] * np.cumprod(1.0 + rng.normal(0.0005, 0.02, c.size - j))
    return Series(c, index=close.index)


def _offsets(n, length=LENGTH, count=35):
    return [int(x) for x in np.linspace(length + 5, n - 5, count).astype(int)]


def _leaks(fn, close, offsets, splices=8):
    bad = np.asarray(fn(close), float)
    hits = []
    for j in offsets:
        for s in range(splices):
            other = np.asarray(fn(_spliced(close, j, seed=909 + 7919 * s)),
                               float)
            if not same(bad[:j], other[:j]):
                hits.append(j)
                break
    return hits


@pytest.mark.parametrize("frame", list(FRAMES))
def test_real_module_never_reads_the_future(frame):
    """Future-perturbation sweep: replace every close from J on and no bar
    before J may move. 0 of 35 offsets leak on each frame, eight splices
    apiece."""
    f = FRAMES[frame]
    assert _leaks(c22_periodicity, f, _offsets(len(f)), splices=8) == []


@pytest.mark.parametrize("length", [MIN_LENGTH, 120, 250])
def test_the_sweep_at_non_default_lengths(length):
    f = FRAMES["walk"]
    assert _leaks(lambda s: c22_periodicity(s, length=length), f,
                  _offsets(len(f), length), splices=4) == []


@pytest.mark.parametrize("name", ["write-back-dated", "window-one-ahead",
                                  "window-ten-ahead", "returns-rolled"])
def test_each_mutant_is_caught(name):
    """Each look-ahead mutant must be caught by the same sweep the real
    module passes clean. Measured on the walk frame: 8 of 35 offsets for the
    three one-bar mutants and 33 of 35 for the ten-bar one. The bound is 4
    rather than 8 because the catch rate is a property of where the splices
    land, which moves with numpy's dispatch."""
    f = FRAMES["walk"]
    hits = _leaks(mutant(name), f, _offsets(len(f)), splices=8)
    assert len(hits) >= 4, (name, len(hits))
    if name == "window-ten-ahead":
        assert len(hits) >= 25, len(hits)


def test_a_one_bar_mutant_can_only_move_bars_from_the_cut_backwards():
    """A back-dated write moves bar J-1 and bars after it, never bar J-2 or
    earlier for a splice at J -- which is exactly what makes it a look-ahead
    of ONE bar. Measured: where anything pre-splice moves, the first moved
    bar is J-1 every time -- 2 of 35 offsets on the walk, which is low
    because the column ties on 88.8% of neighbouring pairs there."""
    fn = mutant("write-back-dated")
    f = FRAMES["walk"]
    bad = np.asarray(fn(f), float)
    seen = 0
    for j in _offsets(len(f), count=35):
        other = np.asarray(fn(_spliced(f, j)), float)
        moved = np.where(~((bad[:j] == other[:j])
                           | (np.isnan(bad[:j]) & np.isnan(other[:j]))))[0]
        if len(moved):
            seen += 1
            assert int(moved.min()) == j - 1, (j, moved[:4])
    assert seen >= 1, seen


def test_the_mask_mutant_is_dead_on_a_clean_frame_and_caught_on_a_dirty_one():
    """The fifth mutant back-dates the bad-data mask instead of a value, so a
    clean frame cannot see it: bit-equal on all 1,500 bars of the walk. On a
    frame with one bad close it moves exactly bar J-1, caught 12 of 12."""
    fn = mutant("mask-back-dated")
    clean = FRAMES["walk"]
    assert same(c22_periodicity(clean), fn(clean))
    caught = 0
    for j in _offsets(len(clean), count=12):
        dirty = clean.copy()
        dirty.iloc[j] = np.nan
        a = np.asarray(c22_periodicity(dirty), float)
        b = np.asarray(fn(dirty), float)
        moved = np.where(~((a == b) | (np.isnan(a) & np.isnan(b))))[0]
        if len(moved):
            caught += 1
            assert int(moved.min()) == j - 1, (j, moved[:4])
    assert caught == 12, caught


def test_the_chunk_wide_demean_mutant_is_near_dead_and_that_is_measured():
    """The sixth mutant replaces each row's own residual mean with the whole
    chunk's -- which IS a read of other rows, so the sweep should see it, and
    it does not: 0 of 35 offsets, and the mutant is bit-equal to the real
    module on all 1,500 bars of three frames. The reason is measured rather
    than excused: the residual of a least-squares fit whose span contains the
    constant function sums to zero, so both means are ~1e-18 and subtracting
    the wrong one changes nothing. It is counted among the six mutants rather
    than quietly dropped."""
    fn = mutant("chunk-wide-demean")
    for frame in ("walk", "tick-rounded", "cosine"):
        assert same(base(frame), fn(FRAMES[frame])), frame
    f = FRAMES["walk"]
    assert _leaks(fn, f, _offsets(len(f), count=12), splices=4) == []


@pytest.mark.parametrize("frame", list(FRAMES))
def test_the_column_ties_often_enough_to_hide_a_one_bar_shift(frame):
    """Why the mutant counts above are not 35 of 35, and why prefix
    truncation would prove nothing here: neighbouring bars carry the same
    small integer 79.3% to 100% of the time (measured)."""
    s = base(frame).dropna().to_numpy()
    assert float(np.mean(s[1:] == s[:-1])) > 0.70


# ------------------------------------------------------------- Gate C
@pytest.mark.parametrize("frame", list(FRAMES))
def test_every_bar_with_a_full_window_fires(frame):
    """1,400 of 1,500 on every frame, and the first fired bar is `length`:
    the window ending at bar T holds the returns of bars T-99 .. T, which
    read closes T-100 .. T."""
    s = base(frame)
    assert int(s.notna().sum()) == len(s) - LENGTH
    assert int(s.notna().values.argmax()) == LENGTH
    assert s.iloc[:LENGTH].isna().all()


@pytest.mark.parametrize("frame", STOCHASTIC)
def test_the_column_is_not_constant_on_a_stochastic_frame(frame):
    """11 to 30 distinct values per frame, median 5 (14 on the AR(1) path).
    Pinned as a band because the exact count moves with the CPU dispatch."""
    a = base(frame).dropna().to_numpy()
    assert len(set(a.tolist())) >= 8, frame
    assert a.max() > a.min()


def test_the_cosine_frame_is_constant_by_construction_not_by_death():
    """The one frame where the column is a single value is the one whose
    returns are an exact 20-bar cosine, and the value is 20 -- the feature
    working, not a dead column."""
    a = base("cosine").dropna().to_numpy()
    assert set(a.tolist()) == {20.0}


def test_a_tick_rounded_penny_frame_still_fires_everywhere():
    """The issue's own worry: shape features of returns can read BIST tick
    rounding. A 2-lira stock on a 1-kurus tick prints 21.7% of its returns as
    exactly 0.00% and the column still fires on all 1,400 bars with the same
    shape as the unrounded walk (median 5 on both). Gate E answered the other
    half: the port's top real comparators ARE the rounding tells the issue
    named -- `cdl_doji` 0.0415 and `BODY_PCT` 0.0392 pooled, price levels
    leading the per-frame medians at 0.0950 -- at a tenth of the strike
    line (receipt §E1)."""
    f = FRAMES["penny"]
    r = np.asarray(f, float)
    r = r[1:] / r[:-1] - 1.0
    assert float(np.mean(r == 0.0)) > 0.15
    s = base("penny")
    assert int(s.notna().sum()) == len(f) - LENGTH
    assert float(s.median()) == float(base("walk").median())


def test_the_sentinel_is_reachable_but_rare():
    """0 is "no qualifying peak". It is reached on 10 of 1,400 bars of the
    AR(1) frame and on 0 of the 5,600 bars of the other four stochastic
    frames -- so a consumer cannot learn what it means from the data, which
    is why the docstring and the receipt lead with it."""
    ar = base("ar1").dropna().to_numpy()
    assert int(np.sum(ar == 0.0)) >= 1
    assert float(np.mean(ar == 0.0)) < 0.05
    for frame in ("walk", "tick-rounded", "penny", "student-t"):
        a = base(frame).dropna().to_numpy()
        assert int(np.sum(a == 0.0)) == 0, frame


def test_a_flat_run_blanks_from_the_first_all_zero_window():
    """A price that goes flat at bar 400 blanks from bar 499 -- the first bar
    whose whole window of returns is zero -- and bar 498, whose window still
    holds the one non-zero return, fires. Nothing blanks earlier, which is
    the difference from `c22_ami_timescale`'s constant-limb rule."""
    c = FRAMES["walk"].to_numpy().copy()
    c[400:] = c[399]
    s = c22_periodicity(Series(c[:700]))
    assert int(s.notna().sum()) == 399
    assert not math.isnan(float(s.iloc[498]))
    assert s.iloc[499:].isna().all()


@pytest.mark.parametrize("step", [0.01, 0.001, -0.005])
def test_an_exact_geometric_ladder_never_fires_and_the_floor_is_why(step):
    """`start * (1 + step)**k` rounds every power on its own, so the window
    holds 3 to 5 distinct returns with a standard deviation of about 1.2e-16
    -- under the 9.09e-13 floor. Unguarded it fires all 1,400 bars and reads
    inside [3, 11], values a reader could not tell from a real frame's. The
    bound below is wider than that on purpose: the frame IS rounding noise,
    so the exact set moves with the CPU dispatch ({3 .. 10} by default,
    {3 .. 11} with AVX-512 / AVX2 / FMA3 off)."""
    f = ladder(step=step)
    assert int(c22_periodicity(f).notna().sum()) == 0
    win, _ = windows(f)
    assert float(win.std(axis=1).max()) < NOISE_FLOOR
    assert len(set(win[0].tolist())) <= 6
    unguarded = [value_src(win[i]) for i in range(0, 1400, 199)]
    assert all(2.0 <= v <= ACMAX - 1 for v in unguarded), unguarded


def test_a_cubic_in_the_returns_never_fires_and_the_window_is_not_flat():
    """The case the floor is applied to the RESIDUAL for: returns that are a
    cubic in the bar index vary (window sd 2.81e-05 .. 1.15e-03, at least
    30 million times the floor) but the spline fits them to 1.4e-16, so the
    autocorrelations would be the shape of the fit's rounding. Unguarded:
    1,400 bars, every one reading the SENTINEL 0 -- a legal value of this
    column, and a claim about a window there is nothing to read in."""
    f = cubic_returns()
    assert int(c22_periodicity(f).notna().sum()) == 0
    win, _ = windows(f)
    assert float(win.std(axis=1).min()) > 1e-5
    rms = []
    for i in range(0, 1400, 199):
        d = resid_qr(win[i])
        d = d - d.mean()
        rms.append(math.sqrt(float((d * d).sum()) / d.size))
    assert max(rms) < NOISE_FLOOR, max(rms)


@pytest.mark.parametrize("frame", list(FRAMES))
def test_the_residual_floor_implies_a_window_floor(frame):
    """One rule doing two jobs: the spline's span contains the constant
    function, so the residual's sum of squares never exceeds the window's
    deviations from its mean, and a residual above the floor therefore
    implies a window above it. Measured on 9,800 rows (six frames and the
    cubic one): 0 break it."""
    win, _ = windows(FRAMES[frame])
    q = _spline_basis(LENGTH)
    resid = win - (win @ q) @ q.T
    d = resid - resid.mean(axis=1, keepdims=True)
    dw = win - win.mean(axis=1, keepdims=True)
    assert int(np.sum((d * d).sum(axis=1) > (dw * dw).sum(axis=1))) == 0


# ------------------------------------------------------------- Gate D
@pytest.mark.parametrize("factor", [8.0, 64.0, 2.0 ** -40, 2.0 ** 40])
@pytest.mark.parametrize("frame", list(FRAMES))
def test_an_exact_binary_rescale_is_bit_identical(frame, factor):
    """By construction: the price enters only as `c[t] / c[t-1]`, and
    `8a / 8b` is the same double as `a / b`."""
    assert same(base(frame), c22_periodicity(FRAMES[frame] * factor))


@pytest.mark.parametrize("factor", [8.0, 64.0])
@pytest.mark.parametrize("length", [MIN_LENGTH, 120, 250])
def test_the_scale_invariance_holds_at_non_default_lengths(length, factor):
    f = FRAMES["walk"]
    assert same(c22_periodicity(f, length=length),
                c22_periodicity(f * factor, length=length))


@pytest.mark.parametrize("price", [1e-6, 1e6, 1e100])
def test_the_scale_invariance_holds_at_every_price_level(price):
    f = walk(level=price)
    b = c22_periodicity(f)
    assert int(b.notna().sum()) == len(f) - LENGTH
    assert same(b, c22_periodicity(f * 8.0))


@pytest.mark.parametrize("factor", [10.0, 3.7, 0.1, 1.0000001])
@pytest.mark.parametrize("frame", list(FRAMES))
def test_an_inexact_rescale_moves_almost_nothing(frame, factor):
    """Not promised by the arithmetic -- the output is an integer decided by
    float comparisons -- so this is a bound (5 bars of 1,400) and not the 0
    that was measured on every one of these 24 cells."""
    moved, mask = diff_bars(base(frame), c22_periodicity(FRAMES[frame] * factor))
    assert moved <= 5, (frame, factor, moved)
    assert mask == 0, (frame, factor, mask)


@pytest.mark.parametrize("frame", list(FRAMES))
def test_the_deciding_comparisons_never_run_near_a_rounding_flip(frame):
    """Why the cell above comes out 0, and why no test here pins a rho to
    1e-6: the smallest slope at the reported peak is 7.1e-05 and the
    smallest rise above the trough-plus-threshold is 2.6e-05 -- still ten
    orders of magnitude above a last-bit question."""
    win, bars = windows(FRAMES[frame])
    worst = math.inf
    worst_th = math.inf
    for i in range(0, win.shape[0], 11):
        v = float(base(frame).iloc[int(bars[i])])
        if not v > 0:
            continue
        acf = src_acf(win[i])
        p = int(v) - 1
        worst = min(worst, abs(acf[p] - acf[p - 1]), abs(acf[p + 1] - acf[p]))
        slopes = np.diff(acf)
        tr = np.where((slopes[:-1] < 0) & (slopes[1:] > 0))[0] + 1
        before = tr[tr < p]
        if before.size:
            worst_th = min(worst_th, abs(acf[p] - acf[before[-1]] - TH))
    assert worst > 1e-7, (frame, worst)
    assert worst_th > 1e-6, (frame, worst_th)


@pytest.mark.parametrize("factor", [0.5, 2.0, 10.0])
def test_it_is_blind_to_the_amplitude_of_the_returns(factor):
    """A correlation cannot see a rescale of both limbs, and a least-squares
    fit is equivariant under one: 0 of 467 windows move."""
    win, bars = windows(FRAMES["walk"])
    idx = list(range(0, win.shape[0], 3))
    mine = [float(base("walk").iloc[int(bars[i])]) for i in idx]
    other = [value_src(win[i] * factor) for i in idx]
    assert diff_bars(mine, other)[0] == 0, factor


def test_it_is_not_blind_to_the_order_of_the_returns():
    """So the bit-identity above is not vacuous: the same returns in a
    different order move 401 of 467 windows."""
    win, bars = windows(FRAMES["walk"])
    idx = list(range(0, win.shape[0], 3))
    mine = [float(base("walk").iloc[int(bars[i])]) for i in idx]
    rng = np.random.default_rng(5)
    other = [value_src(rng.permutation(win[i])) for i in idx]
    assert diff_bars(mine, other)[0] >= 200


@pytest.mark.parametrize("frame", list(FRAMES))
def test_it_fires_strictly_between_zero_and_n(frame):
    s = base(frame)
    assert 0 < int(s.notna().sum()) < len(s)


# ------------------------------------------------------- the noise floor
@pytest.mark.parametrize("frame", list(FRAMES))
def test_the_floor_is_inert_on_anything_price_shaped(frame):
    """The floor costs nothing on a real shape: the guarded and unguarded
    spellings are bit-equal on all 1,400 fired bars of each frame."""
    win, _ = windows(FRAMES[frame])
    mine = base(frame).dropna().to_numpy()
    for i in range(0, win.shape[0], 23):
        assert mine[i] == value_src(win[i]), (frame, i)


def test_what_the_floor_buys_on_a_single_ulp_step():
    """A price flat at 1e6 except for ONE 1-ulp step reads values inside the
    scale unguarded -- 100 bars, reading 0 and values from 16 to 33 here --
    which a reader could not tell from a real reading. The exact set is
    rounding noise and moves with numpy's CPU dispatch, so only "some window
    reads a value" is pinned. Guarded: 0 bars fire."""
    c = np.full(1500, 1e6)
    c[700:] = np.nextafter(1e6, 2e6)
    f = Series(c)
    assert int(c22_periodicity(f).notna().sum()) == 0
    win, _ = windows(f)
    live = [value_src(win[i]) for i in range(600, 700, 7)]
    assert sum(not math.isnan(v) for v in live) > 0


def test_a_deterministically_smooth_path_blanks_where_the_sibling_fires():
    """The cost of the floor, stated rather than hidden. A price rising by
    exactly one kurus a bar from 100.00 is a smooth hyperbola in returns: the
    spline fits it below the floor and this column is NaN on all 1,400 bars,
    while `c22_ami_timescale` -- the sibling catch22 port on the same window
    -- fires on all 1,400. A series with any noise in it is nowhere near
    this; the walk, the tick-rounded walk and the penny frame all fire fully.
    """
    f = Series(100.0 + 0.01 * np.arange(1500, dtype=float))
    assert int(c22_periodicity(f).notna().sum()) == 0
    sibling = pandas_ta.c22_ami_timescale(f)
    assert int(sibling.notna().sum()) == 1400


# ------------------------------------------------------------- bad data
@pytest.mark.parametrize("bad", [np.nan, np.inf, -np.inf, 0.0, -5.0, 1e-310])
def test_a_bad_close_empties_exactly_its_own_windows(bad):
    """A close that is not a finite, normal, positive float has no return to
    take, so the 101 windows that read it are blank: bars 700 .. 800 for a
    bad close at 700, and nothing else."""
    f = FRAMES["walk"].copy()
    f.iloc[700] = bad
    s = c22_periodicity(f)
    blank = np.where(s.isna().to_numpy())[0]
    after = blank[blank >= LENGTH]
    assert after.size == 101
    assert int(after.min()) == 700 and int(after.max()) == 800


def test_a_close_pair_whose_ratio_overflows_empties_its_windows():
    f = FRAMES["walk"].copy()
    f.iloc[700] = 1e-300
    f.iloc[701] = 1e100
    s = c22_periodicity(f)
    blank = np.where(s.isna().to_numpy())[0]
    after = blank[blank >= LENGTH]
    assert after.size == 100
    assert int(after.min()) == 701 and int(after.max()) == 800


def test_a_finite_but_enormous_return_blanks_rather_than_reading_the_sentinel():
    """`1e-100` followed by `1e100` is a FINITE return of 1e200, so the
    return filter does not catch it; what does is the `~isfinite` limb,
    because both the residual's sum of squares and the window's variance
    overflow. Without that limb those 100 bars read the SENTINEL 0 -- "no
    periodicity", a value and not a blank -- which is measured here by
    exec'ing the module without the guard."""
    f = FRAMES["walk"].copy()
    f.iloc[700] = 1e-100
    f.iloc[701] = 1e100
    r = float(f.iloc[701] / f.iloc[700] - 1.0)
    assert math.isfinite(r)
    s = c22_periodicity(f)
    blank = np.where(s.isna().to_numpy())[0]
    after = blank[blank >= LENGTH]
    assert after.size == 100
    without = np.asarray(mutant("no-overflow-guard")(f), float)
    saved = np.where(np.isnan(s.to_numpy()) & ~np.isnan(without))[0]
    assert saved.size == 100
    assert set(without[saved].tolist()) == {float(NO_PERIOD)}


@pytest.mark.parametrize("frame", list(FRAMES))
def test_the_overflow_guard_is_inert_on_every_realistic_frame(frame):
    assert same(base(frame), mutant("no-overflow-guard")(FRAMES[frame]))


@pytest.mark.parametrize("ratio_pair", [(1e-50, 1e27), (1e-20, 1e20)])
def test_the_overflow_guard_is_inert_where_the_sums_stay_finite(ratio_pair):
    """A close pair of ratio 1e77 or 1e40 does NOT overflow the sums of
    squares, so nothing blanks and the window is read as what it is: a
    window one astronomic return dominates."""
    lo, hi = ratio_pair
    f = FRAMES["walk"].copy()
    f.iloc[700] = lo
    f.iloc[701] = hi
    s = c22_periodicity(f)
    blank = np.where(s.isna().to_numpy())[0]
    assert blank[blank >= LENGTH].size == 0
    assert same(s, mutant("no-overflow-guard")(f))


@pytest.mark.parametrize("n,fires", [(99, None), (100, None), (101, 1),
                                     (102, 2)])
def test_a_short_input_returns_none_until_one_window_exists(n, fires):
    s = c22_periodicity(FRAMES["walk"].iloc[:n])
    if fires is None:
        assert s is None
    else:
        assert int(s.notna().sum()) == fires


@pytest.mark.parametrize("length,name,fires", [
    (None, "C22PERIODICITY_100", 1400),
    (0, "C22PERIODICITY_100", 1400),
    (1, "C22PERIODICITY_100", 1400),
    (MIN_LENGTH - 1, "C22PERIODICITY_100", 1400),
    (MIN_LENGTH, f"C22PERIODICITY_{MIN_LENGTH}", 1500 - MIN_LENGTH),
    (250, "C22PERIODICITY_250", 1250),
    (250.7, "C22PERIODICITY_250", 1250),
])
def test_the_length_guard_band(length, name, fires):
    """Below `MIN_LENGTH` = 30 -- where the lag scan would have fewer than
    eight interior lags -- a length falls back to 100 rather than computing
    something thin."""
    s = c22_periodicity(FRAMES["walk"], length=length)
    assert s.name == name
    assert int(s.notna().sum()) == fires


def test_the_offset_and_the_fill_are_the_house_ones():
    s = c22_periodicity(FRAMES["walk"], offset=2)
    assert same(s.to_numpy()[2:], base("walk").to_numpy()[:-2])
    s = c22_periodicity(FRAMES["walk"], fillna=-1)
    assert int(s.isna().sum()) == 0
    assert int((s == -1).sum()) == LENGTH


@pytest.mark.parametrize("budget", [100, 400, 1024])
def test_the_chunk_budget_cannot_change_a_value(budget):
    """Each row's spline fit and demean are per-row, so the chunk boundary is
    invisible: budgets of 100, 400, 1,024 and the default are bit-equal."""
    want = base("walk")
    MODULE.CHUNK_VALUES = budget
    try:
        got = c22_periodicity(FRAMES["walk"])
    finally:
        MODULE.CHUNK_VALUES = CHUNK_VALUES
    assert same(want, got)


# ------------------------------------------------------------- wiring
def test_the_five_wiring_touch_points():
    assert Path(MODULE.__file__).exists()
    assert hasattr(pandas_ta.statistics, "c22_periodicity")
    assert "c22_periodicity" in pandas_ta.Category["statistics"]
    assert hasattr(pandas_ta.core.AnalysisIndicators, "c22_periodicity")
    assert (ROOT / "tests" / "test_c22_periodicity.py").exists()


def test_the_accessor_forwards_its_parameters():
    df = DataFrame({"close": FRAMES["walk"].to_numpy()})
    acc = df.ta.c22_periodicity()
    assert acc.name == "C22PERIODICITY_100"
    assert same(acc, base("walk"))
    acc = df.ta.c22_periodicity(length=250, offset=1)
    assert acc.name == "C22PERIODICITY_250"
    assert same(acc, c22_periodicity(FRAMES["walk"], length=250, offset=1))


def test_the_dictionary_row_describes_this_column():
    text = (ROOT / "docs" / "IndicatorDictionary.md").read_text(
        encoding="utf-8")
    assert "C22PERIODICITY_100" in text
    assert "c22_periodicity" in text


# ------------------------------------------------------- Gate E, owed again
RECEIPT = ROOT / "docs" / "C22PeriodicityMeasured.md"


def test_the_receipt_says_gate_e_is_pending():
    """Gate E was measured on 2026-11-20 and that measurement is WITHDRAWN:
    the autocorrelation's divisor was corrected the same day (review round 1
    -- it divided by the residual's own sum of squares, which is not the line
    either source spells), so the run's module sha1, output fingerprint and
    counts belong to a column this tree no longer computes. The receipt must
    say PENDING and keep the withdrawn digits labelled as the pre-fix
    column's, rather than carry a number measured on something else."""
    text = RECEIPT.read_text(encoding="utf-8")
    assert "Gate E: pending, run by issue-solver after this session" in text
    assert "withdrawn" in text.lower()
    assert "0.0413" in text and "cdl_doji" in text  # the PROTOTYPE figure
    assert "prototype" in text.lower()


def test_the_gate_e_row_is_owed():
    """The ledger has no row for this column, and
    `tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
    fails until the receipt session records one. That failure is expected and
    this test is its mirror: if a row appears, this test fails and the two
    pending-Gate-E tests here must be swapped for ones that pin the row.

    The 2026-11-20 row was recorded and then REMOVED: its run measured the
    pre-fix autocorrelation (see the test above), and a row whose module sha1
    has moved is a measurement that is owed, not a measurement."""
    path = ROOT / "docs" / "gate_e_ledger.csv"
    with path.open(newline="", encoding="utf-8") as fh:
        rows = [r for r in csv.DictReader(fh)
                if r.get("indicator") == "c22_periodicity"]
    assert rows == [], rows


def test_the_receipt_discloses_the_gap_to_the_reference():
    """The screen's Gate E figure was measured on the GPL-3.0 reference's
    column and this port is not bit-identical to it (8,387 of 8,400 windows
    equal, Spearman +0.9993). The receipt has to say so, because otherwise
    the prototype's number reads as a result for this column."""
    text = RECEIPT.read_text(encoding="utf-8")
    assert "8,387" in text and "8,400" in text
    assert "0.9993" in text


def test_gate_cs_real_data_limb_is_owed_in_the_receipt():
    """Every count in this file is synthetic. The receipt says the real-data
    limb comes from the launcher's Gate E run, and names the two counts it
    owes. The 2026-11-20 figures (389,949 non-NaN, 389,928 non-zero of
    398,849) are kept as the PRE-FIX column's and marked as such."""
    text = RECEIPT.read_text(encoding="utf-8")
    assert "owed" in text.lower()
    assert "398,849" in text


def test_the_owed_rule_for_the_nearest_catch22_relatives():
    """`CO_FirstMin_ac` (issue #130) and `SP_Summaries_fft_wq_50` (issue
    #137) read the same return window's autocorrelation and spectrum, and
    neither exists in this tree, so no run has priced the pair. The receipt
    carries the rule for when they land and this test fails if it is
    dropped."""
    text = RECEIPT.read_text(encoding="utf-8")
    assert "#130" in text and "#137" in text
    assert "OWED RULE" in text
