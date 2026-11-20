# -*- coding: utf-8 -*-
"""C22-PERIODICITY (PandasTa issue #126): every number in
`docs/C22PeriodicityMeasured.md` and in the docstrings of
`pandas_ta/statistics/c22_periodicity.py` and
`tests/test_c22_periodicity.py`.

    python docs/measure_c22_periodicity.py            # sections A-H, T, Z
    python docs/measure_c22_periodicity.py A D         # just those
    python docs/measure_c22_periodicity.py P           # the GPL-3.0 black box

Section **P** is OPT-IN and is the only part of this repository that runs the
reference implementation (pycatch22, **GPL-3.0**). It is MEASUREMENT only --
the same use the owner's own screen prototype makes of it
(`docs/issues/screen/ind_screen_r3.py`) -- and no shipped module imports it. A
bare run skips P and does not import it; `importlib.util.find_spec` is used to
report whether it is installed at all, which does not execute the package.

Gate E is NOT here: it needs the private Backtesting engine and the 827 MB
BIST cache, and issue-solver runs it after the porting session.
"""
from __future__ import annotations

import importlib
import importlib.util
import math
import os
import sys
import time
import tracemalloc
from fractions import Fraction
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas_ta as ta  # noqa: E402
from pandas_ta.statistics.c22_periodicity import (  # noqa: E402
    CHUNK_VALUES, MIN_LENGTH, NOISE_FLOOR, NO_PERIOD, SPLINE_DIM, TH,
    ZSCORE_DDOF, _periodicity_rows, _spline_basis, c22_periodicity)

ROOT = Path(__file__).resolve().parent.parent
MODULE = importlib.import_module("pandas_ta.statistics.c22_periodicity")
SRC = Path(MODULE.__file__).read_text(encoding="utf-8")
LENGTH = 100
N = 1500


# --------------------------------------------------------------- frames
def walk(n=N, seed=11, sigma=0.015, level=100.0):
    rng = np.random.default_rng(seed)
    return pd.Series(level * np.exp(np.cumsum(rng.normal(0.0, sigma, n))))


def tick_rounded(n=N, seed=55):
    return pd.Series(np.round(walk(n, seed).to_numpy(), 2))


def penny(n=N, seed=23, level=2.0, sigma=0.012):
    """A 2-lira stock on a 1-kurus tick: many returns are exactly 0."""
    return pd.Series(np.round(walk(n, seed, sigma, level).to_numpy(), 2))


def ar1(n=N, seed=7, sigma=0.01, phi=0.6):
    rng = np.random.default_rng(seed)
    e = rng.normal(0.0, sigma, n)
    r = np.empty(n)
    r[0] = e[0]
    for t in range(1, n):
        r[t] = phi * r[t - 1] + e[t]
    return pd.Series(100.0 * np.cumprod(1.0 + r))


def cosine_returns(n=N, period=20.0, amp=0.01):
    t = np.arange(n, dtype=float)
    return pd.Series(100.0 * np.cumprod(1.0 + amp * np.cos(2 * np.pi * t / period)))


def student_t(n=N, seed=19, df=3, sigma=0.01):
    rng = np.random.default_rng(seed)
    r = sigma * rng.standard_t(df, n)
    return pd.Series(100.0 * np.cumprod(1.0 + np.clip(r, -0.5, 0.5)))


def ladder(n=N, step=0.01, start=100.0):
    """An exactly geometric path: constant returns up to rounding."""
    return pd.Series(start * (1.0 + step) ** np.arange(n, dtype=float))


def cubic_returns(n=N, scale=0.02):
    """Returns that ARE a cubic in the bar index, so the detrending spline
    fits them to rounding and the residual is the fit's own noise."""
    t = np.arange(n, dtype=float) / (n - 1)
    r = scale * (1.0 - 3.0 * t + 2.0 * t ** 3)
    return pd.Series(100.0 * np.cumprod(1.0 + r))


FRAMES = {
    "walk": walk(),
    "tick-rounded": tick_rounded(),
    "penny": penny(),
    "ar1": ar1(),
    "cosine": cosine_returns(),
    "student-t": student_t(),
}
STOCHASTIC = [k for k in FRAMES if k != "cosine"]
_BASE: dict[str, pd.Series] = {}


def base(name):
    if name not in _BASE:
        _BASE[name] = c22_periodicity(FRAMES[name])
    return _BASE[name]


def returns(close):
    c = np.asarray(close, float)
    return c[1:] / c[:-1] - 1.0


def windows(close, length=LENGTH):
    r = returns(close)
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
    x, y = pd.Series(np.asarray(a, float)), pd.Series(np.asarray(b, float))
    m = x.notna() & y.notna()
    if int(m.sum()) < 3:
        return float("nan")
    rx, ry = x[m].rank(), y[m].rank()
    if rx.std() == 0 or ry.std() == 0:
        return float("nan")
    return float(np.corrcoef(rx, ry)[0, 1])


def head(title):
    print()
    print("=" * 78)
    print(title)
    print("=" * 78)


def row(*cells):
    print(" | ".join(str(c) for c in cells))


# ---------------------------------------------------- reference spellings
def acmax_of(n):
    return -(-n // 3)


def scan_acf(acf, th=TH, strict=True, need_trough=True, need_positive=True):
    """The Wang scan, over a plain list of autocorrelations (index i = lag
    i + 1). Returns the lag, or NO_PERIOD."""
    m = len(acf)
    trough = None
    for i in range(1, m - 1):
        cur, prev, nxt = acf[i], acf[i - 1], acf[i + 1]
        if strict:
            is_peak = (cur - prev > 0) and (nxt - cur < 0)
            is_trough = (cur - prev < 0) and (nxt - cur > 0)
        else:
            is_peak = (cur - prev >= 0) and (nxt - cur <= 0)
            is_trough = (cur - prev <= 0) and (nxt - cur >= 0)
        if is_peak and (trough is not None or not need_trough):
            ok = True
            if trough is not None and not (cur - trough >= th):
                ok = False
            if need_positive and not (cur >= 0):
                ok = False
            if ok:
                return i + 1
        if is_trough:
            trough = cur
    return NO_PERIOD


def fit_resid_lstsq(window):
    """The same spline space, fitted by `np.linalg.lstsq` on the truncated
    power basis instead of by projection onto its QR factor."""
    w = np.asarray(window, float)
    n = w.size
    t = np.arange(n, dtype=float) / (n - 1)
    x = np.column_stack([np.ones(n), t, t ** 2, t ** 3,
                         np.where(t > 0.5, (t - 0.5) ** 3, 0.0)])
    coef = np.linalg.lstsq(x, w, rcond=None)[0]
    return w - x @ coef


def fit_resid_normal(window):
    """The same fit again, through the normal equations."""
    w = np.asarray(window, float)
    n = w.size
    t = np.arange(n, dtype=float) / (n - 1)
    x = np.column_stack([np.ones(n), t, t ** 2, t ** 3,
                         np.where(t > 0.5, (t - 0.5) ** 3, 0.0)])
    coef = np.linalg.solve(x.T @ x, x.T @ w)
    return w - x @ coef


def fit_resid_knots(window, knots=(0.5,), degree=3):
    """The least-squares regression spline of the same degree with ANY
    interior knot set, so the shipped knot structure (one knot, at the middle
    of the window) can be measured against its neighbours rather than
    assumed."""
    w = np.asarray(window, float)
    n = w.size
    t = np.arange(n, dtype=float) / (n - 1)
    cols = [t ** p for p in range(degree + 1)]
    cols += [np.where(t > k, (t - k) ** degree, 0.0) for k in knots]
    x = np.column_stack(cols)
    q = np.linalg.qr(x)[0]
    return w - q @ (q.T @ w)


def fit_resid_scipy(window):
    """`scipy.interpolate.LSQUnivariateSpline`: a least-squares cubic
    B-spline with one interior knot at the middle of the window -- an
    independent implementation of what hctsa's `spap2(2, 4, 1:N, y)` means."""
    from scipy.interpolate import LSQUnivariateSpline
    w = np.asarray(window, float)
    n = w.size
    x = np.arange(n, dtype=float)
    spl = LSQUnivariateSpline(x, w, t=[(n - 1) / 2.0], k=3)
    return w - spl(x)


def acf_of(resid, demean=True, kind="biased", acmax=None):
    """The autocorrelations of one detrended window, four ways -- every one
    of them a DEVIATION from the source line, which `value_source` spells.

    `biased` is the reading this module shipped until 2026-11-20: the `n - k`
    products that exist over the sum of squares of all `n` deviations of the
    RESIDUAL. It was attributed to hctsa's `CO_AutoCorr(y, k, 'Fourier')`,
    which `PD_PeriodicityWang` does not call. `adjusted` averages those
    products over the `n - k` pairs but still normalises on the residual, so
    it is not the source reading either. `pearson` demeans and normalises
    each LIMB by its own mean and sum of squares. `halfmean` keeps one mean
    but normalises by the two limbs' sums of squares.
    """
    r = np.asarray(resid, float)
    n = r.size
    d = r - r.mean() if demean else r
    ss = float((d * d).sum())
    m = acmax if acmax is not None else acmax_of(n)
    out = []
    for k in range(1, m + 1):
        a, b = d[:n - k], d[k:]
        if kind == "pearson":
            da, db = a - a.mean(), b - b.mean()
            den = math.sqrt(float((da * da).sum()) * float((db * db).sum()))
            out.append(float((da * db).sum()) / den if den > 0 else float("nan"))
            continue
        if kind == "halfmean":
            den = math.sqrt(float((a * a).sum()) * float((b * b).sum()))
            out.append(float((a * b).sum()) / den if den > 0 else float("nan"))
            continue
        if not ss > 0.0:
            return None
        num = float((a * b).sum())
        out.append(num / (ss * (n - k) / n) if kind == "adjusted"
                   else num / ss)
    return out


def value_from_resid(resid, th=TH, demean=True, adjusted=False,
                     acmax=None, strict=True, kind=None, need_trough=True,
                     need_positive=True):
    acf = acf_of(resid, demean=demean,
                 kind=kind or ("adjusted" if adjusted else "biased"),
                 acmax=acmax)
    if acf is None or not np.isfinite(acf).all():
        return float("nan")
    return float(scan_acf(acf, th=th, strict=strict, need_trough=need_trough,
                          need_positive=need_positive))


def value_source(window, th=TH, ddof=ZSCORE_DDOF, demean=False, fit=None,
                 acmax=None, strict=True, need_trough=True,
                 need_positive=True):
    """The SOURCE spelling of the whole quantity, z-score included.

    hctsa's `PD_PeriodicityWang` does not call `CO_AutoCorr`: it spells the
    autocorrelations inline as `acf(i) = mean(y(1:N-i).*y(i+1:N))`, and
    catch22's C reference divides the same products by `size - tau`. That is
    the ADJUSTED divisor, and what makes those averages dimensionless is that
    catch22 Z-SCORES THE SERIES BEFORE the detrend -- so condition (b)'s
    absolute 0.01 lives in PRE-DETREND z-scored units, not in units of the
    residual's own variance. This function is that reading end to end:
    z-score the window, detrend it with the same spline, average the lagged
    products over the `n - k` pairs that exist, scan.

    This is the reading the module SHIPS since 2026-11-20, spelled
    independently of it: the module divides one sum by `(n - k) * var` where
    this divides the series by `sd` first, and the module re-centres the
    residual where the source line does not. Both are the same quantity
    rounded differently (measured in A5: 0 of 2,802 windows move under
    either). The pre-2026-11-20 reading divided by the RESIDUAL's own sum of
    squares instead, which differs from this quantity by the lag-dependent
    factor `(n - 1) / (n - k)` and by `resid_ss / window_ss` -- two
    deviations, both of which condition (b)'s absolute 0.01 can see. It is
    kept in the tables below as a deviation.

    `ddof` is the z-score's divisor convention -- 1 is MATLAB `zscore`'s, 0
    the population one -- and `ddof = 0` multiplies every autocorrelation by
    `n / (n - 1)`, which condition (b) can see in principle and does not
    here. `demean` re-centres the residual before the products, which the
    source line does not do (the residual of a fit whose span holds the
    constant function already sums to zero). `fit` is applied to the Z-SCORED
    window and returns its residual.
    """
    w = np.asarray(window, float)
    n = w.size
    sd = float(w.std(ddof=ddof))
    if not (np.isfinite(sd) and sd > 0.0):
        return float("nan")
    z = (w - w.mean()) / sd
    if fit is not None:
        resid = fit(z)
    else:
        q = _spline_basis(n)
        resid = z - (z @ q) @ q.T
    d = resid - resid.mean() if demean else resid
    m = acmax if acmax is not None else acmax_of(n)
    acf = [float((d[:n - k] * d[k:]).sum()) / (n - k) for k in range(1, m + 1)]
    if not np.isfinite(acf).all():
        return float("nan")
    return float(scan_acf(acf, th=th, strict=strict, need_trough=need_trough,
                          need_positive=need_positive))


def shipped_on(window):
    """The shipped kernel on a single window, as a float."""
    return float(_periodicity_rows(np.asarray(window, float)[None, :])[0])


def shipped_acf(window):
    """The autocorrelations the SHIPPED kernel scans, spelled its way: the
    lagged products of the spline residual, over `(n - k) * var` where `var`
    is the window's PRE-DETREND variance at `ZSCORE_DDOF`. Used wherever a
    section has to read the quantity a decision turned on."""
    w = np.asarray(window, float)
    n = w.size
    q = _spline_basis(n)
    r = w - (w @ q) @ q.T
    d = r - r.mean()
    var = float(w.var(ddof=ZSCORE_DDOF))
    return np.array([float((d[:n - k] * d[k:]).sum()) / ((n - k) * var)
                     for k in range(1, acmax_of(n) + 1)])


# ------------------------------------------------------- exact oracle
def _frac_solve(a, b):
    """Exact Gaussian elimination with partial pivoting over Fractions."""
    m = len(b)
    aug = [list(a[i]) + [b[i]] for i in range(m)]
    for col in range(m):
        piv = max(range(col, m), key=lambda r: abs(aug[r][col]))
        if aug[piv][col] == 0:
            raise ZeroDivisionError("singular")
        aug[col], aug[piv] = aug[piv], aug[col]
        inv = Fraction(1, 1) / aug[col][col]
        aug[col] = [v * inv for v in aug[col]]
        for r in range(m):
            if r != col and aug[r][col] != 0:
                f = aug[r][col]
                aug[r] = [v - f * w for v, w in zip(aug[r], aug[col])]
    return [aug[i][m] for i in range(m)]


def value_exact(window, th=Fraction(1, 100)):
    """The definition in exact rational arithmetic -- zero roundings.

    Every input double is an exact rational, the basis functions of the
    spline space are exact rationals on the window's x-grid, the
    least-squares coefficients are the exact solution of the (exact) normal
    equations, and both the autocorrelations and the three Wang conditions
    are compared as exact rationals. Nothing in this function rounds.

    The z-score's `sd` is irrational, but the quantity never needs it: the
    autocorrelation of the z-scored window's residual is
    `sum(d_i d_{i+k}) / ((n - k) * var)`, and `var` -- a sum of squares over
    `n - ZSCORE_DDOF` -- is rational. The square root cancels.
    """
    y = [Fraction(float(v)) for v in window]
    n = len(y)
    t = [Fraction(i, n - 1) for i in range(n)]
    half = Fraction(1, 2)
    cols = [[Fraction(1)] * n,
            t,
            [v * v for v in t],
            [v * v * v for v in t],
            [(v - half) ** 3 if v > half else Fraction(0) for v in t]]
    g = [[sum(ci[k] * cj[k] for k in range(n)) for cj in cols] for ci in cols]
    rhs = [sum(ci[k] * y[k] for k in range(n)) for ci in cols]
    coef = _frac_solve(g, rhs)
    fit = [sum(coef[j] * cols[j][k] for j in range(len(cols))) for k in range(n)]
    resid = [y[k] - fit[k] for k in range(n)]
    mean = sum(resid, Fraction(0)) / n
    d = [v - mean for v in resid]
    ss = sum(v * v for v in d)
    if ss == 0:
        return float("nan")
    wmean = sum(y, Fraction(0)) / n
    var = sum((v - wmean) ** 2 for v in y) / (n - ZSCORE_DDOF)
    if var == 0:
        return float("nan")
    acf = [sum(d[i] * d[i + k] for i in range(n - k)) / ((n - k) * var)
           for k in range(1, acmax_of(n) + 1)]
    return float(scan_acf(acf, th=th))


# ===================================================================== S
def section_s():
    head("S. Environment")
    row("python", sys.version.split()[0])
    row("numpy", np.__version__)
    row("pandas", pd.__version__)
    for name in ("scipy", "statsmodels", "pycatch22"):
        spec = importlib.util.find_spec(name)
        row(name, "installed" if spec is not None else "ABSENT")
    row("length", LENGTH, "acmax", acmax_of(LENGTH),
        "lags scanned", f"2 .. {acmax_of(LENGTH) - 1}")
    row("NOISE_FLOOR", f"{NOISE_FLOOR:.4e}",
        "TH", TH, "SPLINE_DIM", SPLINE_DIM)
    q = _spline_basis(LENGTH)
    row("basis shape", q.shape,
        "max |Q'Q - I|", f"{np.abs(q.T @ q - np.eye(q.shape[1])).max():.3e}")


# ===================================================================== A
def section_a():
    head("A1. The spline basis is a choice of SPANNING SET, not of model")
    print("Shipped: projection onto the QR factor of the truncated power")
    print("basis. Three other spellings of the SAME function space:")
    have_scipy = importlib.util.find_spec("scipy") is not None
    for name in FRAMES:
        win, bars = windows(FRAMES[name])
        idx = range(0, win.shape[0], 7)
        worst = {"lstsq": 0.0, "normal": 0.0, "scipy": 0.0}
        moved = {"lstsq": 0, "normal": 0, "scipy": 0}
        ran = 0
        for i in idx:
            w = win[i]
            mine = shipped_on(w)
            q = _spline_basis(w.size)
            rmine = w - (w @ q) @ q.T
            for key, fn in (("lstsq", fit_resid_lstsq),
                            ("normal", fit_resid_normal),
                            ("scipy", fit_resid_scipy)):
                if key == "scipy" and not have_scipy:
                    continue
                r2 = fn(w)
                worst[key] = max(worst[key],
                                 float(np.abs(r2 - rmine).max()
                                       / max(np.abs(rmine).max(), 1e-300)))
                if value_source(w, fit=fn) != mine:
                    moved[key] += 1
            ran += 1
        row(name, f"windows {ran}",
            *[f"{k}: {moved[k]} moved, rel {worst[k]:.2e}" for k in worst])

    head("A2. The exact rational oracle -- zero roundings")
    stride = int(os.environ.get("C22P_EXACT_STRIDE", 13))
    t0 = time.perf_counter()
    for name in FRAMES:
        win, bars = windows(FRAMES[name])
        agree = dis = 0
        bad = []
        for i in range(0, win.shape[0], stride):
            mine = shipped_on(win[i])
            want = value_exact(win[i])
            if (mine == want) or (math.isnan(mine) and math.isnan(want)):
                agree += 1
            else:
                dis += 1
                bad.append((int(bars[i]), mine, want))
        row(name, f"agree {agree}", f"disagree {dis}", bad[:3])
    row("stride", stride, f"{time.perf_counter() - t0:.1f}s")

    head("A3. The cosine law: an exact cosine of period P reads P")
    for period in (8, 10, 12, 15, 20, 25, 30, 33, 34, 40, 60):
        s = c22_periodicity(cosine_returns(period=float(period)))
        v = s.dropna()
        vals = sorted(set(v.to_numpy().tolist()))
        row(f"P = {period}", f"fired {int(v.size)}",
            f"values {vals[:6]}{' ...' if len(vals) > 6 else ''}",
            f"median {float(v.median())}")

    head("A4. Z-scoring the window changes nothing (catch22's own convention)")
    for name in FRAMES:
        win, _ = windows(FRAMES[name])
        idx = range(0, win.shape[0], 7)
        moved = ran = 0
        for i in idx:
            w = win[i]
            z = (w - w.mean()) / w.std()
            a, b = shipped_on(w), shipped_on(z)
            if not (a == b or (math.isnan(a) and math.isnan(b))):
                moved += 1
            ran += 1
        row(name, f"windows {ran}", f"moved {moved}")

    head("A5. The ACF spelling: the SOURCE one is what ships, and what the"
         " deviations from it cost")
    print("The source line is `acf(i) = mean(y(1:N-i).*y(i+1:N))`"
          " (PD_PeriodicityWang,")
    print("which does NOT call CO_AutoCorr) and `acf[tau-1] /= size - tau`")
    print("(catch22's C), on a series catch22 z-scores BEFORE the detrend.")
    print("Shipped: that quantity, with the z-score spelled as one division")
    print("by `var` at the end. Column 1 is the LITERAL spelling (divide the")
    print("series by `sd` first, project again); column 2 the population")
    print("z-score; column 3 re-centring the residual, which the source line")
    print("does not do; columns 4-5 the pre-2026-11-20 reading, which")
    print("normalised by the RESIDUAL's own sum of squares.")
    row("frame", "windows", "literal z-score first", "z-score ddof 0",
        "residual re-demeaned", "biased (resid sum of squares)",
        "n - k but normalised on the residual")
    for name in FRAMES:
        win, _ = windows(FRAMES[name])
        idx = list(range(0, win.shape[0], 3))
        mine, src, src0, srcd, biased, adj = [], [], [], [], [], []
        for i in idx:
            q = _spline_basis(win[i].size)
            r = win[i] - (win[i] @ q) @ q.T
            mine.append(shipped_on(win[i]))
            src.append(value_source(win[i]))
            src0.append(value_source(win[i], ddof=0))
            srcd.append(value_source(win[i], demean=True))
            biased.append(value_from_resid(r))
            adj.append(value_from_resid(r, adjusted=True))
        row(name, len(idx),
            f"{diff_bars(mine, src)[0]} moved, rho {spearman(mine, src):+.4f}",
            f"{diff_bars(mine, src0)[0]} moved",
            f"{diff_bars(mine, srcd)[0]} moved",
            f"{diff_bars(mine, biased)[0]} moved,"
            f" rho {spearman(mine, biased):+.4f}",
            f"{diff_bars(mine, adj)[0]} moved")

    head("A5b. The DETREND is load-bearing: four other knot structures")
    row("frame", "no detrend", "straight line", "one cubic (no knot)",
        "knot at 1/3", "three pieces")
    for name in FRAMES:
        win, _ = windows(FRAMES[name])
        idx = list(range(0, win.shape[0], 3))
        mine = [shipped_on(win[i]) for i in idx]
        cells = []
        for label, kw in (("raw", None), ("line", dict(knots=(), degree=1)),
                          ("cubic", dict(knots=())),
                          ("1/3", dict(knots=(1 / 3,))),
                          ("three", dict(knots=(1 / 3, 2 / 3)))):
            if kw is None:
                other = [value_source(win[i], fit=lambda z: z) for i in idx]
            else:
                other = [value_source(
                    win[i], fit=lambda z, kw=kw: fit_resid_knots(z, **kw))
                    for i in idx]
            cells.append(f"{diff_bars(mine, other)[0]} moved,"
                         f" rho {spearman(mine, other):+.3f}")
        row(name, f"windows {len(idx)}", *cells)

    head("A6. The threshold is load-bearing (th = 0.01 vs 0 vs 0.1)")
    for name in FRAMES:
        win, _ = windows(FRAMES[name])
        idx = list(range(0, win.shape[0], 3))
        mine, zero, ten = [], [], []
        for i in idx:
            mine.append(shipped_on(win[i]))
            zero.append(value_source(win[i], th=0.0))
            ten.append(value_source(win[i], th=0.1))
        row(name, f"windows {len(idx)}",
            f"th=0: {diff_bars(mine, zero)[0]} moved",
            f"th=0.1: {diff_bars(mine, ten)[0]} moved")

    head("A6b. Wang's other two conditions, (a) a trough before it and"
         " (c) a non-negative peak")
    for name in FRAMES:
        win, _ = windows(FRAMES[name])
        idx = list(range(0, win.shape[0], 3))
        mine, no_trough, any_sign = [], [], []
        for i in idx:
            mine.append(shipped_on(win[i]))
            no_trough.append(value_source(win[i], need_trough=False))
            any_sign.append(value_source(win[i], need_positive=False))
        row(name, f"windows {len(idx)}",
            f"no trough required: {diff_bars(mine, no_trough)[0]} moved",
            f"a negative peak allowed: {diff_bars(mine, any_sign)[0]} moved")

    head("A7. Strictness, and the lag ceiling")
    for name in FRAMES:
        win, _ = windows(FRAMES[name])
        idx = list(range(0, win.shape[0], 3))
        mine, loose, floor3 = [], [], []
        for i in idx:
            mine.append(shipped_on(win[i]))
            loose.append(value_source(win[i], strict=False))
            floor3.append(value_source(win[i], acmax=win[i].size // 3))
        row(name, f"windows {len(idx)}",
            f"non-strict: {diff_bars(mine, loose)[0]} moved",
            f"floor(n/3): {diff_bars(mine, floor3)[0]} moved")

    head("A8. Exact ties in the comparisons the scan makes")
    for name in FRAMES:
        win, _ = windows(FRAMES[name])
        flat_slope = flat_th = 0
        cells = 0
        for i in range(0, win.shape[0], 3):
            acf = shipped_acf(win[i])
            n = win[i].size
            slopes = np.diff(acf)
            flat_slope += int(np.sum(slopes == 0.0))
            cells += slopes.size
            peaks = np.where((slopes[:-1] > 0) & (slopes[1:] < 0))[0] + 1
            troughs = np.where((slopes[:-1] < 0) & (slopes[1:] > 0))[0] + 1
            for p in peaks:
                before = troughs[troughs < p]
                if before.size:
                    if acf[p] - acf[before[-1]] == TH:
                        flat_th += 1
        row(name, f"slope cells {cells}", f"exactly flat {flat_slope}",
            f"peak-trough exactly TH {flat_th}")


# ===================================================================== B
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
}


def mutant(name):
    old, new = MUTANTS[name]
    assert SRC.count(old) == 1, (name, SRC.count(old))
    ns: dict = {}
    exec(compile(SRC.replace(old, new), f"<mutant {name}>", "exec"), ns)
    return ns["c22_periodicity"]


def _spliced(close, j, seed=909):
    rng = np.random.default_rng(seed + j)
    c = close.to_numpy(dtype=float).copy()
    c[j:] = c[j - 1] * np.cumprod(1.0 + rng.normal(0.0005, 0.02, c.size - j))
    return pd.Series(c, index=close.index)


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


def section_b():
    head("B1. Future-perturbation sweep, 35 offsets x 8 splices")
    for name in FRAMES:
        f = FRAMES[name]
        hits = _leaks(c22_periodicity, f, _offsets(len(f)), splices=8)
        row(name, f"leaking offsets {len(hits)} / 35", hits[:4])
    for length in (MIN_LENGTH, 120, 250):
        f = FRAMES["walk"]
        hits = _leaks(lambda s: c22_periodicity(s, length=length), f,
                      _offsets(len(f), length), splices=4)
        row(f"walk, length {length}", f"leaking offsets {len(hits)} / 35")

    head("B2. Mutants, read off the module source and exec'd in memory")
    for name in MUTANTS:
        cells = []
        for frame in ("walk", "tick-rounded", "cosine"):
            f = FRAMES[frame]
            fn = mutant(name)
            hits = _leaks(fn, f, _offsets(len(f)), splices=8)
            moved = diff_bars(base(frame), fn(f))
            cells.append(f"{frame}: {len(hits)}/35 (differs on {moved[0]}"
                         f" bars, {moved[1]} mask)")
        row(name, *cells)

    head("B2b. Where a one-bar mutant moves anything, it moves bar J-1")
    fn = mutant("write-back-dated")
    f = FRAMES["walk"]
    bad = np.asarray(fn(f), float)
    seen = first_is_j1 = 0
    for j in _offsets(len(f), count=35):
        other = np.asarray(fn(_spliced(f, j)), float)
        moved = np.where(~((bad[:j] == other[:j])
                           | (np.isnan(bad[:j]) & np.isnan(other[:j]))))[0]
        if len(moved):
            seen += 1
            first_is_j1 += int(moved.min() == j - 1)
    row("offsets that move a pre-splice bar", seen,
        "first moved bar is J-1", first_is_j1)

    head("B3. The mask mutant: dead on a clean frame, caught on a dirty one")
    fn = mutant("mask-back-dated")
    clean = FRAMES["walk"]
    row("bit-equal on the clean walk", same(c22_periodicity(clean), fn(clean)))
    caught = at_j1 = 0
    for j in _offsets(len(clean), count=12):
        dirty = clean.copy()
        dirty.iloc[j] = np.nan
        a = np.asarray(c22_periodicity(dirty), float)
        b = np.asarray(fn(dirty), float)
        moved = np.where(~((a == b) | (np.isnan(a) & np.isnan(b))))[0]
        if len(moved):
            caught += 1
            at_j1 += int(moved.min() == j - 1)
    row("caught", f"{caught} / 12", "first moved bar is J-1", at_j1)

    head("B4. Tie density -- why the counts above are not 35 of 35")
    for name in FRAMES:
        s = base(name).dropna().to_numpy()
        row(name, f"neighbouring pairs equal {float(np.mean(s[1:] == s[:-1])):.3f}")


# ===================================================================== C
def section_c():
    head("C1. Reachability on six synthetic frames (1,500 bars each)")
    row("frame", "fired", "distinct", "range", "median", "zeros", "first bar")
    for name in FRAMES:
        s = base(name)
        v = s.dropna()
        a = v.to_numpy()
        row(name, f"{int(v.size)} / {len(s)}", len(set(a.tolist())),
            f"{a.min():g} .. {a.max():g}", f"{float(v.median()):g}",
            f"{int(np.sum(a == 0))} ({100 * np.mean(a == 0):.1f}%)",
            int(s.notna().values.argmax()))
    s = base("walk").dropna().to_numpy()
    vals, counts = np.unique(s, return_counts=True)
    print("walk distribution:",
          {int(v): int(c) for v, c in zip(vals, counts)})

    head("C2. The issue's worry: BIST tick rounding")
    paths = {
        "2 lira, 1 kurus tick (penny)": FRAMES["penny"],
        "100 lira rounded to the kurus": FRAMES["tick-rounded"],
        "100 lira unrounded (walk)": FRAMES["walk"],
    }
    for label, f in paths.items():
        r = returns(f)
        s = c22_periodicity(f).dropna()
        a = s.to_numpy()
        row(label, f"zero returns {100 * np.mean(r == 0.0):.1f}%",
            f"fired {int(s.size)}", f"distinct {len(set(a.tolist()))}",
            f"median {float(s.median()):g}",
            f"zeros {100 * np.mean(a == 0):.1f}%")

    head("C3. What the one blanking rule costs")
    flat = FRAMES["walk"].to_numpy().copy()
    flat[400:] = flat[399]
    s = c22_periodicity(pd.Series(flat[:700]))
    live = np.where(s.notna().to_numpy())[0]
    row("400-bar walk then 300 flat closes",
        f"fired {int(s.notna().sum())} / 700",
        f"last live bar {int(live.max()) if live.size else None}")
    for step in (0.01, 0.001, -0.005):
        f = ladder(step=step)
        s = c22_periodicity(f)
        guarded = int(s.notna().sum())
        win, _ = windows(f)
        sd = win.std(axis=1)
        un = [value_source(win[i]) for i in range(0, win.shape[0], 29)]
        un = np.asarray(un, float)
        row(f"geometric ladder, step {step:+g}", f"fired {guarded}",
            f"distinct returns per window {len(set(win[0].tolist()))}",
            f"window sd {sd.max():.2e} vs floor {NOISE_FLOOR:.2e}",
            f"unguarded would read {np.nanmin(un):g} .. {np.nanmax(un):g}")
    f = cubic_returns()
    s = c22_periodicity(f)
    win, _ = windows(f)
    q = _spline_basis(LENGTH)
    un = np.asarray([value_source(win[i])
                     for i in range(0, win.shape[0], 29)], float)
    resid = win - (win @ q) @ q.T
    dd = resid - resid.mean(axis=1, keepdims=True)
    rms = np.sqrt((dd * dd).sum(axis=1) / win.shape[1])
    row("returns that ARE a cubic", f"fired {int(s.notna().sum())}",
        f"window sd {win.std(axis=1).min():.2e} .. {win.std(axis=1).max():.2e}"
        f" (clears a window-level floor)",
        f"residual rms {rms.min():.2e} .. {rms.max():.2e}"
        f" vs floor {NOISE_FLOOR:.2e}",
        f"unguarded would read {np.nanmin(un):g} .. {np.nanmax(un):g}")
    broke = tested = 0
    for name in list(FRAMES) + ["cubic"]:
        w = win if name == "cubic" else windows(FRAMES[name])[0]
        dd2 = w - (w @ q) @ q.T
        dd2 = dd2 - dd2.mean(axis=1, keepdims=True)
        dw = w - w.mean(axis=1, keepdims=True)
        broke += int(np.sum((dd2 * dd2).sum(axis=1) > (dw * dw).sum(axis=1)))
        tested += w.shape[0]
    row("the residual floor implies a window floor",
        f"rows with residual ss > window ss: {broke} of {tested}")


# ===================================================================== D
def section_d():
    head("D1. Exact binary rescales -- bit-identical")
    for name in FRAMES:
        cells = []
        for factor in (8.0, 64.0, 2.0 ** -40, 2.0 ** 40):
            cells.append(same(base(name), c22_periodicity(FRAMES[name] * factor)))
        row(name, f"x8 {cells[0]}", f"x64 {cells[1]}",
            f"2**-40 {cells[2]}", f"2**40 {cells[3]}")
    for length in (MIN_LENGTH, 120, 250):
        f = FRAMES["walk"]
        b = c22_periodicity(f, length=length)
        row(f"walk, length {length}",
            *[f"x{x:g} {same(b, c22_periodicity(f * x, length=length))}"
              for x in (8.0, 64.0)])
    for price in (1e-6, 1e6, 1e100):
        f = walk(level=price)
        b = c22_periodicity(f)
        row(f"price level {price:g}", f"x8 {same(b, c22_periodicity(f * 8.0))}",
            f"fired {int(b.notna().sum())}")

    head("D2. Inexact rescales")
    for name in FRAMES:
        cells = []
        for factor in (10.0, 3.7, 0.1, 1.0000001):
            moved, mask = diff_bars(base(name),
                                    c22_periodicity(FRAMES[name] * factor))
            cells.append(f"x{factor:g}: {moved} bars, {mask} mask")
        row(name, *cells)

    head("D3. Blind to the amplitude of the returns, not to their order")
    q = _spline_basis(LENGTH)
    for name in ("walk", "ar1"):
        win, _ = windows(FRAMES[name])
        idx = list(range(0, win.shape[0], 3))
        mine = [shipped_on(win[i]) for i in idx]
        for factor in (0.5, 2.0, 10.0):
            other = [shipped_on(win[i] * factor) for i in idx]
            row(f"{name}, returns x{factor:g}",
                f"{diff_bars(mine, other)[0]} of {len(idx)} moved")
        rng = np.random.default_rng(5)
        other = [shipped_on(rng.permutation(win[i])) for i in idx]
        row(f"{name}, returns reshuffled",
            f"{diff_bars(mine, other)[0]} of {len(idx)} moved")

    head("D4. 0 < fires < n, and not constant")
    for name in FRAMES:
        s = base(name)
        a = s.dropna().to_numpy()
        row(name, f"0 < {int(s.notna().sum())} < {len(s)}",
            f"distinct {len(set(a.tolist()))}")

    head("D5. How close the deciding comparisons run to a rounding flip")
    for name in FRAMES:
        win, _ = windows(FRAMES[name])
        margins = []
        th_margins = []
        for i in range(0, win.shape[0], 3):
            acf = shipped_acf(win[i])
            v = shipped_on(win[i])
            if not (v > 0):
                continue
            i_pk = int(v) - 1
            slopes = np.diff(acf)
            troughs = np.where((slopes[:-1] < 0) & (slopes[1:] > 0))[0] + 1
            before = troughs[troughs < i_pk]
            margins.append(min(abs(acf[i_pk] - acf[i_pk - 1]),
                               abs(acf[i_pk + 1] - acf[i_pk])))
            if before.size:
                th_margins.append(abs(acf[i_pk] - acf[before[-1]] - TH))
        row(name, f"windows {len(margins)}",
            f"min slope margin {min(margins):.2e}" if margins else "-",
            f"min |peak-trough-TH| {min(th_margins):.2e}" if th_margins else "-")


# ===================================================================== E
def section_e():
    head("E3. In-fork overlap on the six synthetic frames (not Gate E)")
    print("Gate E's 687 comparators are the engine's; these are this fork's")
    print("own shape/cycle columns, which Gate E cannot see.")
    cands = [
        ("C22AMITIMESCALE_100", lambda f: ta.c22_ami_timescale(f)),
        ("FIRSTZEROAC_100", lambda f: ta.firstzero_ac(f)),
        ("DIFF2ACF1_100", lambda f: ta.diff2_acf1(f)),
        ("TS_AC1_60", lambda f: ta.ts_ac1_60(f)),
        ("TFAUTOCORR1E_60", lambda f: ta.tf_autocorr_1e_60(f)),
        ("TFCENTROID_20", lambda f: ta.tf_centroid_20(f)),
        ("TFSPECENT_64", lambda f: ta.tf_spec_entropy_64(f)),
        ("TFDFA_100", lambda f: ta.tf_dfa_100(f)),
        ("TS_CID_CE_20", lambda f: ta.ts_cid_ce_20(f)),
        ("TS_PERMENT_20_3", lambda f: ta.ts_perment_20(f)),
        ("TS_BINENT_20_5", lambda f: ta.ts_binent_20(f)),
        ("TS_AGGAC_60_10", lambda f: ta.ts_aggac_60(f)),
        ("TS_C3_20_1", lambda f: ta.ts_c3_20(f)),
        ("HLIFE_100", lambda f: ta.halflife(f)),
        ("LEAN_HURST_100_20", lambda f: ta.lean_hurst_100(f)),
        ("ENTLZ_20", lambda f: ta.entlz(f)),
        ("HT_DCPERIOD", lambda f: ta.ht_dcperiod(f)),
        ("SEAS", lambda f: ta.seas(f)),
    ]
    pooled_mine = np.concatenate([base(k).to_numpy() for k in FRAMES])
    rows = []
    for label, fn in cands:
        try:
            series = []
            for k in FRAMES:
                out = fn(FRAMES[k])
                if isinstance(out, pd.DataFrame):
                    out = out.iloc[:, 0]
                series.append(np.asarray(out, float))
        except Exception as exc:  # pragma: no cover - reported, not raised
            row(label, f"SKIPPED: {type(exc).__name__}: {exc}")
            continue
        pooled_other = np.concatenate(series)
        per = [abs(spearman(base(k), s)) for k, s in zip(FRAMES, series)]
        both = (~np.isnan(pooled_mine)) & (~np.isnan(pooled_other))
        rows.append((label, spearman(pooled_mine, pooled_other),
                     int(both.sum()), float(np.nanmedian(per)),
                     float(np.nanmax(per)), per))
    rows.sort(key=lambda t: -abs(t[1]) if not math.isnan(t[1]) else 0)
    row("comparator", "pooled rho", "n", "per-frame median |rho|",
        "per-frame max |rho|")
    for label, rho, n, med, mx, per in rows:
        row(label, f"{rho:+.4f}", n, f"{med:.4f}", f"{mx:.4f}",
            "[" + ", ".join("nan" if math.isnan(p) else f"{p:.3f}"
                            for p in per) + "]")

    head("E4. The OWED RULE: two catch22 relatives that are not in the tree")
    print("Issues #130 (CO_FirstMin_ac, the first minimum of the return")
    print("ACF) and #137 (SP_Summaries_fft_wq_50, the median frequency of")
    print("the return spectrum) read the SAME window. Neither is ported, so")
    print("Gate E cannot see them. The two columns below are PROXIES written")
    print("here -- a plausible spelling of each, not its port -- so the")
    print("figures are an advance warning and not a measurement of #130 or")
    print("#137.")

    def proxy_first_min_ac(close):
        win, _ = windows(close)
        out = np.full(len(close), np.nan)
        d = win - win.mean(axis=1, keepdims=True)
        ss = (d * d).sum(axis=1)
        m = acmax_of(LENGTH)
        acf = np.empty((win.shape[0], m))
        for k in range(1, m + 1):
            acf[:, k - 1] = (d[:, :LENGTH - k] * d[:, k:]).sum(axis=1) / ss
        for r in range(win.shape[0]):
            v = 0.0
            for i in range(1, m - 1):
                if acf[r, i] < acf[r, i - 1] and acf[r, i] < acf[r, i + 1]:
                    v = i + 1
                    break
            out[LENGTH + r] = v
        return out

    def proxy_median_freq(close):
        win, _ = windows(close)
        out = np.full(len(close), np.nan)
        d = win - win.mean(axis=1, keepdims=True)
        power = np.abs(np.fft.rfft(d, axis=1)) ** 2
        power = power[:, 1:]
        cum = np.cumsum(power, axis=1)
        half = cum[:, -1:] / 2.0
        idx = np.argmax(cum >= half, axis=1)
        out[LENGTH:] = idx + 1
        return out

    row("proxy", *list(FRAMES), "pooled")
    for label, fn in (("#130 first minimum of the return ACF",
                       proxy_first_min_ac),
                      ("#137 median frequency of the return spectrum",
                       proxy_median_freq)):
        per, pooled_other = [], []
        for k in FRAMES:
            s = fn(FRAMES[k])
            per.append(abs(spearman(base(k), s)))
            pooled_other.append(s)
        row(label, *[f"{p:.3f}" if not math.isnan(p) else "nan" for p in per],
            f"{abs(spearman(pooled_mine, np.concatenate(pooled_other))):.3f}")


# ===================================================================== G
def section_g():
    head("G. The floor, and what it buys")
    q = _spline_basis(LENGTH)

    def unguarded(close):
        win, _ = windows(close)
        return np.asarray([value_source(win[i])
                           for i in range(win.shape[0])], float)

    for name in FRAMES:
        g = base(name).dropna().to_numpy()
        u = unguarded(FRAMES[name])
        row(name, f"guarded fires {g.size}",
            f"unguarded fires {int(np.sum(~np.isnan(u)))}",
            f"bars differing {diff_bars(base(name).to_numpy()[LENGTH:], u)}")

    cases = {}
    c = np.full(N, 1e6)
    c[700:] = np.nextafter(1e6, 2e6)
    cases["flat at 1e6 except one 1-ulp step"] = pd.Series(c)
    cases["one 1-kurus tick per bar at 1e6"] = pd.Series(
        1e6 + 0.01 * np.arange(N, dtype=float))
    cases["one 1-kurus tick per bar at 1e9"] = pd.Series(
        1e9 + 0.01 * np.arange(N, dtype=float))
    cases["one 1-kurus tick per bar at 100"] = pd.Series(
        100.0 + 0.01 * np.arange(N, dtype=float))
    cases["400 identical closes"] = pd.Series(np.full(400, 7.0))
    cases["returns that ARE a cubic"] = cubic_returns()
    cases["exact geometric ladder"] = ladder()
    for label, f in cases.items():
        s = c22_periodicity(f)
        u = unguarded(f) if len(f) > LENGTH else np.array([])
        live = int(s.notna().sum())
        ulive = int(np.sum(~np.isnan(u))) if u.size else 0
        # The WHOLE set, not its first few: a truncated list here was read as
        # a range in the receipt once (review round 2).
        vals = sorted(set(u[~np.isnan(u)].tolist())) if u.size else []
        sib = ta.c22_ami_timescale(f)
        row(label, f"guarded fires {live}", f"unguarded fires {ulive}",
            f"unguarded values {vals}",
            f"c22_ami_timescale fires"
            f" {0 if sib is None else int(sib.notna().sum())}")


# ===================================================================== H
def section_h():
    head("H1. Bad data")
    for bad in (np.nan, np.inf, -np.inf, 0.0, -5.0, 1e-310):
        f = FRAMES["walk"].copy()
        f.iloc[700] = bad
        s = c22_periodicity(f)
        blank = np.where(s.isna().to_numpy())[0]
        after = blank[blank >= LENGTH]
        row(f"close[700] = {bad!r}", f"blank bars {int(s.isna().sum())}",
            f"blank beyond the warm-up {after.size}",
            f"range {after.min() if after.size else None}"
            f" .. {after.max() if after.size else None}")
    for lo, hi in ((1e-300, 1e100), (1e-100, 1e100), (1e-50, 1e27),
                   (1e-20, 1e20)):
        f = FRAMES["walk"].copy()
        f.iloc[700] = lo
        f.iloc[701] = hi
        s = c22_periodicity(f)
        blank = np.where(s.isna().to_numpy())[0]
        after = blank[blank >= LENGTH]
        r = hi / lo - 1.0
        row(f"close pair {lo:g} -> {hi:g} (return {r:g})",
            f"blank beyond the warm-up {after.size}",
            f"range {after.min() if after.size else None}"
            f" .. {after.max() if after.size else None}")

    head("H1b. What the overflow limb of the mask buys")
    old = "bad |= ~np.isfinite(ss) | ~np.isfinite(var)"
    assert SRC.count(old) == 1
    ns: dict = {}
    exec(compile(SRC.replace(old, "bad |= np.zeros_like(bad)"),
                 "<no-overflow-guard>", "exec"), ns)
    unguarded = ns["c22_periodicity"]
    for lo, hi in ((1e-100, 1e100), (1e-50, 1e27)):
        f = FRAMES["walk"].copy()
        f.iloc[700] = lo
        f.iloc[701] = hi
        a, b = c22_periodicity(f), unguarded(f)
        blank_a = int(a.isna().sum())
        blank_b = int(b.isna().sum())
        bars = np.where(np.isnan(a.to_numpy()) & ~np.isnan(b.to_numpy()))[0]
        vals = sorted(set(b.to_numpy()[bars].tolist())) if bars.size else []
        row(f"close pair {lo:g} -> {hi:g}", f"guarded blanks {blank_a}",
            f"unguarded blanks {blank_b}",
            f"the {bars.size} bars it saves would read {vals[:5]}")
    row("inert on the clean walk",
        same(c22_periodicity(FRAMES['walk']), unguarded(FRAMES['walk'])))

    head("H2. Short inputs, the length guard, offset and fillna")
    for n in (99, 100, 101, 102):
        s = c22_periodicity(FRAMES["walk"].iloc[:n])
        row(f"n = {n}", "None" if s is None else f"fired {int(s.notna().sum())}")
    for length in (None, 0, 1, MIN_LENGTH - 1, MIN_LENGTH, 250, 250.7):
        s = c22_periodicity(FRAMES["walk"], length=length)
        row(f"length = {length!r}", s.name, f"fired {int(s.notna().sum())}")
    s = c22_periodicity(FRAMES["walk"], offset=2)
    row("offset=2 is the unshifted column shifted by 2",
        same(s.to_numpy()[2:], base("walk").to_numpy()[:-2]))
    s = c22_periodicity(FRAMES["walk"], fillna=-1)
    row("fillna=-1", f"NaNs left {int(s.isna().sum())}",
        f"-1 on {int((s == -1).sum())} bars")

    head("H3. The five wiring touch points, live")
    import pandas_ta
    row("1 module", Path(MODULE.__file__).relative_to(ROOT))
    row("2 package export", hasattr(pandas_ta.statistics, "c22_periodicity"))
    row("3 Category", "c22_periodicity" in pandas_ta.Category["statistics"])
    df = pd.DataFrame({"close": FRAMES["walk"].to_numpy()})
    acc = df.ta.c22_periodicity()
    row("4 accessor", acc.name, same(acc, base("walk")))
    acc2 = df.ta.c22_periodicity(length=250, offset=1)
    row("4 accessor forwards", acc2.name,
        same(acc2, c22_periodicity(FRAMES["walk"], length=250, offset=1)))
    row("5 tests", (ROOT / "tests" / "test_c22_periodicity.py").exists())
    row("Category total", sum(len(v) for v in pandas_ta.Category.values()))

    head("H4. No shipped module imports the reference")
    hits = []
    for p in sorted((ROOT / "pandas_ta").rglob("*.py")):
        text = p.read_text(encoding="utf-8")
        for line in text.splitlines():
            s = line.strip()
            if (s.startswith("import ") or s.startswith("from ")) and \
                    ("pycatch22" in s or "catch22" in s.replace("c22", "")):
                hits.append((str(p.relative_to(ROOT)), s))
    row("python files scanned",
        len(list((ROOT / "pandas_ta").rglob("*.py"))), "import hits", hits)
    row("pycatch22 installed in this worktree",
        importlib.util.find_spec("pycatch22") is not None)


# ===================================================================== P
def section_p():
    head("P. The reference implementation as a BLACK BOX (GPL-3.0, opt-in)")
    print("pycatch22 is GPL-3.0 and this fork is MIT. It is run here to")
    print("MEASURE only -- the same use docs/issues/screen/ind_screen_r3.py")
    print("makes of it -- and the question it answers is whether this port is")
    print("the column the 2026-10-24 screen's Gate E numbers were measured on.")
    if importlib.util.find_spec("pycatch22") is None:
        row("pycatch22", "ABSENT -- section P cannot run")
        return
    import pycatch22

    def ref(window):
        return float(pycatch22.PD_PeriodicityWang_th0_01(
            [float(v) for v in window]))

    probe = pycatch22.catch22_all([float(v) for v in returns(FRAMES["walk"])
                                   [:LENGTH]], short_names=True)
    names = [n for n in probe["short_names"] if "eriodicity" in n]
    row("catch22_all names matching 'eriodicity'", names)
    which = probe["short_names"].index(names[0]) if names else None

    def ref_all(window):
        out = pycatch22.catch22_all([float(v) for v in window],
                                    short_names=True)
        return float(out["values"][which])

    head("P1. Shipped vs reference, EVERY window of the six frames")
    row("frame", "windows", "equal", "mine < ref", "mine > ref",
        "Spearman", "worst gap")
    tot = {"eq": 0, "lo": 0, "hi": 0, "n": 0}
    all_mine, all_ref = [], []
    every = []
    for name in FRAMES:
        win, bars = windows(FRAMES[name])
        eq = lo = hi = n = 0
        mine_v, ref_v = [], []
        worst = 0
        for i in range(win.shape[0]):
            mine = shipped_on(win[i])
            if math.isnan(mine):
                continue
            r = ref(win[i])
            n += 1
            mine_v.append(mine)
            ref_v.append(r)
            if mine == r:
                eq += 1
            else:
                lo += int(mine < r)
                hi += int(mine > r)
                # EVERY disagreement, not a sample of them: this is the one
                # fact the port's whole disclosure rests on.
                every.append((name, int(bars[i]), mine, r))
            worst = max(worst, abs(mine - r))
        row(name, n, eq, lo, hi, f"{spearman(mine_v, ref_v):+.4f}", worst)
        all_mine += mine_v
        all_ref += ref_v
        for k, v in (("eq", eq), ("lo", lo), ("hi", hi), ("n", n)):
            tot[k] += v
    row("TOTAL", tot["n"], tot["eq"], tot["lo"], tot["hi"],
        f"{spearman(all_mine, all_ref):+.4f}", "")
    row("equal share", f"{100 * tot['eq'] / tot['n']:.2f}%")
    print(f"all {len(every)} disagreements (frame, bar, mine, reference):")
    for cell in every:
        print(" ", cell)

    head("P1b. WHICH reading the reference agrees with, on the same windows")
    print("Every third window above, scored by this port and by the other")
    print("defensible readings of the same definition (the count of readings")
    print("is printed with the table). The count is windows where that")
    print("reading equals the REFERENCE.")
    q = _spline_basis(LENGTH)

    def variants(w):
        r_qr = w - (w @ q) @ q.T
        out = {
            # SHIPPED since 2026-11-20: the source spelling -- z-score the
            # window, detrend it, average each lag's products over the n - k
            # pairs that exist (`mean(y(1:N-i).*y(i+1:N))`, `acf[tau-1] /=
            # size - tau`). The next three are the same quantity with the one
            # convention the source line does not fix, or spelled the literal
            # way; the three after them are the pre-2026-11-20 reading, which
            # normalised by the RESIDUAL's own sum of squares and so carried
            # the taper n / (n - k) and the ratio resid_var / window_var.
            "shipped (z-score, n - k divisor, QR spline)": shipped_on(w),
            "shipped, spelled z-score-first": value_source(w),
            "shipped, population z-score (ddof 0)": value_source(w, ddof=0),
            "shipped, residual re-demeaned": value_source(w, demean=True),
            "biased acf (divisor = the RESIDUAL's sum of squares)":
                value_from_resid(r_qr),
            "biased acf, no demean":
                value_from_resid(r_qr, demean=False),
            "n - k divisor but normalised on the residual":
                value_from_resid(r_qr, adjusted=True),
            "acmax = floor(n / 3)": value_source(w, acmax=w.size // 3),
            "non-strict extrema": value_source(w, strict=False),
            "th = 0 (no rise required)": value_source(w, th=0.0),
            "scipy B-spline detrend": value_source(w, fit=fit_resid_scipy),
            "lagged-pair Pearson acf":
                value_from_resid(r_qr, kind="pearson"),
            "two-limb normalisation, one mean":
                value_from_resid(r_qr, kind="halfmean"),
            "no detrend at all (raw returns)":
                value_source(w, fit=lambda z: z),
            "detrend by one cubic polynomial (no knot)":
                value_source(w, fit=lambda z: fit_resid_knots(z, knots=())),
            "detrend with the knot at 1/3":
                value_source(w, fit=lambda z: fit_resid_knots(z, knots=(1 / 3,))),
            "detrend with three pieces":
                value_source(w, fit=lambda z: fit_resid_knots(
                    z, knots=(1 / 3, 2 / 3))),
            "detrend by a straight line":
                value_source(w, fit=lambda z: fit_resid_knots(
                    z, knots=(), degree=1)),
        }
        return out

    tally: dict[str, int] = {}
    n_scored = 0
    detail = []
    for name in FRAMES:
        win, bars = windows(FRAMES[name])
        for i in range(0, win.shape[0], 3):
            w = win[i]
            mine = shipped_on(w)
            if math.isnan(mine):
                continue
            r = ref(w)
            n_scored += 1
            vs = variants(w)
            for key, val in vs.items():
                tally[key] = tally.get(key, 0) + int(
                    val == r or (math.isnan(val) and math.isnan(r)))
            if mine != r:
                acf = shipped_acf(w)
                i_pk = int(mine) - 1
                slopes = np.diff(acf)
                tr = np.where((slopes[:-1] < 0) & (slopes[1:] > 0))[0] + 1
                before = tr[tr < i_pk]
                detail.append({
                    "frame": name, "bar": int(bars[i]), "mine": mine,
                    "ref": r,
                    "acf at mine-1, mine, mine+1":
                        [round(float(acf[i_pk - 1]), 6),
                         round(float(acf[i_pk]), 6),
                         round(float(acf[i_pk + 1]), 6)],
                    "peak - trough - TH":
                        float(acf[i_pk] - acf[before[-1]] - TH)
                        if before.size else None,
                    "variants that match the reference":
                        [k for k, v in vs.items() if v == r],
                })
    row("windows scored by both", n_scored,
        f"readings compared: {len(tally)} (the shipped one and"
        f" {len(tally) - 1} others)")
    for key, hit in sorted(tally.items(), key=lambda kv: -kv[1]):
        row(key, f"{hit} / {n_scored}")
    print()
    print(f"All {len(detail)} disagreements on this subsample, with the"
          f" readings that match the reference on each:")
    for d in detail:
        print(" ", d)
    print()
    print("How many of those each reading explains:")
    explains: dict[str, int] = {}
    for d in detail:
        for key in d["variants that match the reference"]:
            explains[key] = explains.get(key, 0) + 1
    for key, hit in sorted(explains.items(), key=lambda kv: -kv[1]):
        row(key, f"{hit} / {len(detail)}")
    row("explained by NO reading tried",
        f"{sum(1 for d in detail if not d['variants that match the reference'])}"
        f" / {len(detail)}")

    head("P2. The same through catch22_all, and the z-score question")
    win, _ = windows(FRAMES["walk"])
    agree = n = 0
    for i in range(0, win.shape[0], 23):
        n += 1
        agree += int(ref(win[i]) == ref_all(win[i]))
    row("single-feature vs catch22_all", f"{agree} / {n} equal")
    zeq = zn = 0
    for i in range(0, win.shape[0], 23):
        z = (win[i] - win[i].mean()) / win[i].std()
        zn += 1
        zeq += int(ref(win[i]) == ref(z))
    row("reference on raw vs z-scored returns", f"{zeq} / {zn} equal")

    head("P3. The windows this port BLANKS and the reference scores")
    cases = {
        "walk": FRAMES["walk"],
        "penny": FRAMES["penny"],
        "400-bar walk + 300 flat closes": None,
        "exact geometric ladder": ladder(),
        "returns that ARE a cubic": cubic_returns(),
    }
    flat = FRAMES["walk"].to_numpy().copy()
    flat[400:] = flat[399]
    cases["400-bar walk + 300 flat closes"] = pd.Series(flat[:700])
    for label, f in cases.items():
        s = c22_periodicity(f)
        win, bars = windows(f)
        blank = [i for i in range(win.shape[0])
                 if math.isnan(float(s.iloc[LENGTH + i]))]
        scored = []
        for i in blank[::3]:
            try:
                scored.append(ref(win[i]))
            except Exception as exc:
                scored.append(f"raised {type(exc).__name__}")
        vals = sorted({v for v in scored if isinstance(v, float)})
        row(label, f"blank windows {len(blank)}",
            f"sampled {len(scored)}",
            f"the reference scores {sum(isinstance(v, float) for v in scored)}",
            f"values {vals}")


# ===================================================================== T
def section_t():
    head("T. Cost")
    rng = np.random.default_rng(3)
    big = pd.Series(100.0 * np.exp(np.cumsum(rng.normal(0, 0.01, 400_000))))
    tracemalloc.start()
    t0 = time.perf_counter()
    s = c22_periodicity(big)
    dt = time.perf_counter() - t0
    cur, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    row(f"n = {len(big):,}", f"fired {int(s.notna().sum()):,}",
        f"{dt:.1f}s", f"traced peak {peak / 1e6:.1f} MB")
    row("chunk rows at length 100", CHUNK_VALUES // LENGTH)


# ===================================================================== Z
def section_z():
    head("Z. The chunk boundary is invisible")
    f = FRAMES["walk"]
    want = base("walk")
    for budget in (100, 400, 1024, CHUNK_VALUES):
        MODULE.CHUNK_VALUES = budget
        try:
            got = c22_periodicity(f)
        finally:
            MODULE.CHUNK_VALUES = CHUNK_VALUES
        row(f"CHUNK_VALUES = {budget}", f"bit-equal {same(want, got)}")


SECTIONS = {
    "S": section_s, "A": section_a, "B": section_b, "C": section_c,
    "D": section_d, "E": section_e, "G": section_g, "H": section_h,
    "P": section_p, "T": section_t, "Z": section_z,
}
DEFAULT = ["S", "A", "B", "C", "D", "E", "G", "H", "T", "Z"]


def main(argv):
    want = [a.upper() for a in argv] or DEFAULT
    for key in want:
        if key not in SECTIONS:
            raise SystemExit(f"unknown section {key!r}; pick from {list(SECTIONS)}")
    for key in want:
        SECTIONS[key]()


if __name__ == "__main__":
    main(sys.argv[1:])
