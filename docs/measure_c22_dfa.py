# -*- coding: utf-8 -*-
"""C22-DFA (PandasTa issue #128): every number in `docs/C22DfaMeasured.md`
and in the docstrings of `pandas_ta/statistics/c22_dfa.py` and
`tests/test_c22_dfa.py`.

    python docs/measure_c22_dfa.py              # S, A-E, G, H, T, Z
    python docs/measure_c22_dfa.py A D          # just those
    python docs/measure_c22_dfa.py P            # the GPL-3.0 black box

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
import sys
import time
import tracemalloc
from decimal import Decimal, localcontext
from fractions import Fraction
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas_ta as ta  # noqa: E402
from pandas_ta.statistics.c22_dfa import (  # noqa: E402
    CHUNK_VALUES, LAG, MIN_LENGTH, MIN_POINTS, NOISE_FLOOR, N_TAU_STEPS, Q,
    SCALE_SHARE, TAU_MIN, ZSCORE_DDOF, _prop_rows, c22_dfa, min_each_side,
    prop_bounds, scales)

ROOT = Path(__file__).resolve().parent.parent
MODULE = importlib.import_module("pandas_ta.statistics.c22_dfa")
SRC = Path(MODULE.__file__).read_text(encoding="utf-8")
LENGTH = 100
N = 1500
#: Significant digits the exact oracle's logarithms and straight-line fits
#: run at, about 44 beyond a double. It is applied with `localcontext` at the
#: one place that needs it and NOT at import: the decimal context is
#: process-global, and `tests/test_c22_dfa.py` imports this file by path to
#: compare the mutant tables, so a module-level `getcontext().prec = 60`
#: would leave 60 digits behind for the rest of a pytest session (the house
#: rule -- `tests/test_ts_cross_mean_20.py::_exact_windowed`).
ORACLE_PREC = 60


# --------------------------------------------------------------- frames
def walk(n=N, seed=11, sigma=0.015, level=100.0):
    rng = np.random.default_rng(seed)
    return pd.Series(level * np.exp(np.cumsum(rng.normal(0.0, sigma, n))))


def tick_rounded(n=N, seed=55):
    return pd.Series(np.round(walk(n, seed).to_numpy(), 2))


def penny(n=N, seed=55, sigma=0.015, level=2.0):
    """A 2-lira stock on a 1-kurus tick: the issue's own warning, where many
    returns are exactly zero."""
    return pd.Series(np.round(walk(n, seed, sigma, level).to_numpy(), 2))


def ar1(n=N, seed=7, sigma=0.01, phi=0.6):
    rng = np.random.default_rng(seed)
    e = rng.normal(0.0, sigma, n)
    r = np.empty(n)
    r[0] = e[0]
    for t in range(1, n):
        r[t] = phi * r[t - 1] + e[t]
    return pd.Series(100.0 * np.cumprod(1.0 + r))


def ar1_neg(n=N, seed=23, sigma=0.01, phi=-0.6):
    return ar1(n, seed, sigma, phi)


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


def kurus_path(n=N, start=100.0, step=0.01):
    """A price rising by exactly one kurus a bar: smooth, with real
    variation in the returns."""
    return pd.Series(start + step * np.arange(n, dtype=float))


FRAMES = {
    "walk": walk(),
    "tick-rounded": tick_rounded(),
    "penny": penny(),
    "ar1": ar1(),
    "cosine": cosine_returns(),
    "student-t": student_t(),
}
_BASE: dict[str, pd.Series] = {}


def base(name):
    if name not in _BASE:
        _BASE[name] = c22_dfa(FRAMES[name])
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


def diff_bars(a, b, tol=0.0):
    """(value bars differing by more than `tol`, bars whose NaN mask differs)."""
    x, y = np.asarray(a, float), np.asarray(b, float)
    both = ~np.isnan(x) & ~np.isnan(y)
    return (int(np.sum(np.abs(x[both] - y[both]) > tol)),
            int(np.sum(np.isnan(x) != np.isnan(y))))


def worst_gap(a, b):
    x, y = np.asarray(a, float), np.asarray(b, float)
    both = ~np.isnan(x) & ~np.isnan(y)
    return float(np.max(np.abs(x[both] - y[both]))) if both.any() else 0.0


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


def shipped_on(window):
    """One window through the shipped row kernel."""
    w = np.asarray(window, float)
    return float(_prop_rows(w.reshape(1, -1))[0])


# ------------------------------------------------- the definition, by hand
def scales_def(length, lag=LAG, steps=N_TAU_STEPS, tau_min=TAU_MIN,
               rounding="half-up", top="half-decimated", decimate="first"):
    """The scale ladder, re-spelled, with one knob per reading.

    * `top` -- `half-decimated` (SHIPPED): half the DECIMATED length, which
      is what `floor(N/2)` means once the lag has already been applied;
      `half-raw`: half the raw `length`, the reading that applies the lag to
      the data but not to the ladder.
    * `rounding` -- `half-up` (SHIPPED, MATLAB's and C's `round`), `even`
      (numpy's), `floor`, `ceil`.
    """
    points = -(-int(length) // lag) if decimate != "none" else int(length)
    hi = (points if top == "half-decimated" else int(length)) // 2
    if hi < tau_min:
        return []
    out = []
    for i in range(steps):
        x = math.exp(math.log(float(tau_min))
                     + i * (math.log(float(hi)) - math.log(float(tau_min)))
                     / (steps - 1))
        if rounding == "half-up":
            v = int(math.floor(x + 0.5))
        elif rounding == "even":
            v = int(np.round(x))
        elif rounding == "floor":
            v = int(math.floor(x))
        else:
            v = int(math.ceil(x))
        if v not in out:
            out.append(v)
    return sorted(out)


def _fit_resid(xs, ys):
    """Residuals of the least-squares line through `(xs, ys)`, with fsum."""
    n = len(xs)
    xm = math.fsum(xs) / n
    ym = math.fsum(ys) / n
    sxy = math.fsum((x - xm) * (y - ym) for x, y in zip(xs, ys))
    sxx = math.fsum((x - xm) ** 2 for x in xs)
    b = sxy / sxx
    return [(y - ym) - b * (x - xm) for x, y in zip(xs, ys)]


def fluctuations(window, lag=LAG, decimate="first", cumsum="after",
                 zscore=True, ddof=ZSCORE_DDOF, detrend=1, q=Q,
                 pool="all", taus=None, divisor="tau", remainder="tail",
                 **ladder_kw):
    """`F(tau)` for every scale, from the definition, in plain Python.

    Knobs, each one a reading section A prices rather than assumes:

    * `decimate` -- `first` (SHIPPED): keep points 0, lag, 2 lag, ... , which
      is `y(1:lag:end)`; `last`: keep lag-1, 2 lag-1, ..., the END-aligned
      reading; `none`: no decimation at all.
    * `cumsum`   -- `after` (SHIPPED): the profile is the cumulative sum of
      the DECIMATED series; `before`: the cumulative sum is taken first and
      decimated after, which is a different quantity.
    * `detrend`  -- the polynomial order removed from each box (`k`).
    * `pool`     -- `all` (SHIPPED): the q-th moment of every residual of
      every box; `perbox`: the q-th moment per box, then over boxes. For
      `q = 2` and equal-length boxes the two are the same number.
    """
    w = [float(v) for v in window]
    n = len(w)
    if not all(math.isfinite(v) for v in w):
        return None
    mean = math.fsum(w) / n
    var = math.fsum((v - mean) ** 2 for v in w) / (n - ddof)
    sd = math.sqrt(var)
    if not (math.isfinite(sd) and sd > 0.0):
        return None
    z = [(v - mean) / sd for v in w] if zscore else list(w)

    if cumsum == "before":
        cs = []
        acc = 0.0
        for v in z:
            acc += v
            cs.append(acc)
        if decimate == "first":
            profile = cs[::lag]
        elif decimate == "last":
            profile = cs[lag - 1::lag]
        else:
            profile = cs
    else:
        if decimate == "first":
            y = z[::lag]
        elif decimate == "last":
            y = z[lag - 1::lag]
        else:
            y = list(z)
        profile = []
        acc = 0.0
        for v in y:
            acc += v
            profile.append(acc)

    points = len(profile)
    if taus is None:
        taus = scales_def(n, lag=lag, decimate=decimate, **ladder_kw)
    out = []
    for tau in taus:
        boxes = points // tau
        if boxes < 1:
            return None
        xs = list(range(tau))
        res = []
        # Which end of the window the `points % tau` leftover comes off.
        skip = 0 if remainder == "tail" else points - boxes * tau
        for b in range(boxes):
            seg = profile[skip + b * tau:skip + (b + 1) * tau]
            if detrend == 1:
                res.append(_fit_resid(xs, seg))
            else:
                coef = np.polyfit(np.asarray(xs, float),
                                  np.asarray(seg, float), detrend)
                fit = np.polyval(coef, np.asarray(xs, float))
                res.append([float(a - b2) for a, b2 in zip(seg, fit)])
        if pool == "all":
            flat = [abs(v) ** q for seg in res for v in seg]
            # What the sum of the `q`-th powers is divided by. `tau` (times
            # the box count) is the plain mean, which is what a
            # root-mean-square fluctuation means; the others are the
            # DEGREES-OF-FREEDOM readings a variance estimator would use,
            # and each shifts `log F` by a different TAU-DEPENDENT constant,
            # so they change the shape of the curve rather than its level.
            denom = {"tau": boxes * tau,
                     "tau-1": boxes * (tau - 1),
                     "tau-2": boxes * (tau - 2),
                     "n-1": boxes * tau - 1,
                     "boxes": boxes,
                     "one": 1,
                     "one-tau": tau}[divisor]
            f = (math.fsum(flat) / denom) ** (1.0 / q)
        else:
            per = [(math.fsum(abs(v) ** q for v in seg) / tau) ** (1.0 / q)
                   for seg in res]
            f = (math.fsum(v ** q for v in per) / len(per)) ** (1.0 / q)
        out.append((tau, f))
    return out


def break_of(curve, min_points=None, score="ss", share=True,
             prop="break/ntt"):
    """The two-piece break of a `[(tau, F)]` curve, and the reading knobs.

    * `score` -- `ss` (SHIPPED): the sum of the two residual sums of
      SQUARES; `norm`: the sum of the two residual NORMS; `mean-norm`: each
      norm divided by its own point count.
    * `share` -- True (SHIPPED): the two pieces SHARE the scale at the break
      (`1:i` and `i:ntt`); False: they are disjoint (`1:i` and `i+1:ntt`).
    * `prop`  -- what is returned: `break/ntt` (SHIPPED), `(break-1)/ntt`,
      `break/(ntt-1)`.
    """
    if curve is None:
        return None
    ntt = len(curve)
    if any(not (f > 0.0) or not math.isfinite(f) for _, f in curve):
        return None
    lt = [math.log(float(tau)) for tau, _ in curve]
    lf = [math.log(f) for _, f in curve]
    mp = min_each_side(ntt) if min_points is None else min_points
    cands = list(range(mp, ntt - mp + 1))
    if not cands:
        return None
    best, best_i = None, None
    for i in cands:
        r1 = _fit_resid(lt[:i], lf[:i])
        r2 = _fit_resid(lt[i - 1:], lf[i - 1:]) if share \
            else _fit_resid(lt[i:], lf[i:])
        if score == "norm":
            s = math.sqrt(math.fsum(v * v for v in r1)) \
                + math.sqrt(math.fsum(v * v for v in r2))
        elif score == "ss":
            s = math.fsum(v * v for v in r1) + math.fsum(v * v for v in r2)
        else:
            s = math.sqrt(math.fsum(v * v for v in r1)) / len(r1) \
                + math.sqrt(math.fsum(v * v for v in r2)) / len(r2)
        if best is None or s < best:
            best, best_i = s, i
    if prop == "break/ntt":
        return best_i / ntt
    if prop == "(break-1)/ntt":
        return (best_i - 1) / ntt
    return best_i / (ntt - 1)


def value_def(window, min_points=None, score="ss", share=True,
              prop="break/ntt", **fluct_kw):
    """The whole definition re-spelled in plain Python with `math.fsum`, with
    every reading section A prices exposed as a knob."""
    curve = fluctuations(window, **fluct_kw)
    got = break_of(curve, min_points=min_points, score=score, share=share,
                   prop=prop)
    return float("nan") if got is None else got


# -------------------------------------------------- the exact-ish oracle
def value_exact(window):
    """`(break, ntt, margin)` with the profile and every residual EXACT.

    The output is an INTEGER choice -- which candidate break minimises the
    summed squared residuals -- so an oracle only has to get that integer right,
    and the margin between the winner and the runner-up says how far the
    float arithmetic would have to drift to change it.

    The window's own returns are rationals and the whole feature is invariant
    under a positive affine map of them (the z-score's `sd` scales every
    residual of every box by the same factor, which shifts `log F` by a
    constant and leaves the residuals of both straight-line fits alone), so
    the oracle works on the RAW window: the profile, the per-box
    least-squares residuals and `F(tau)**2` are exact `Fraction`s. Only the
    logarithms and the two straight-line fits are inexact, and those run in
    60-digit `Decimal`.
    """
    w = [Fraction(float(v)) for v in window]
    n = len(w)
    y = w[::LAG]
    profile, acc = [], Fraction(0)
    for v in y:
        acc += v
        profile.append(acc)
    points = len(profile)
    taus = [int(t) for t in scales(n)]
    f2 = []
    for tau in taus:
        boxes = points // tau
        xs = [Fraction(i) for i in range(tau)]
        xm = sum(xs) / tau
        sxx = sum((x - xm) ** 2 for x in xs)
        tot = Fraction(0)
        for b in range(boxes):
            seg = profile[b * tau:(b + 1) * tau]
            ym = sum(seg) / tau
            sxy = sum((x - xm) * (v - ym) for x, v in zip(xs, seg))
            slope = sxy / sxx
            tot += sum(((v - ym) - slope * (x - xm)) ** 2
                       for x, v in zip(xs, seg))
        f2.append(tot / (boxes * tau))
    if any(v <= 0 for v in f2):
        return None
    ntt = len(taus)

    def ss(xs, ys):
        m = len(xs)
        xm = sum(xs) / m
        ym = sum(ys) / m
        sxy = sum((x - xm) * (v - ym) for x, v in zip(xs, ys))
        sxx = sum((x - xm) ** 2 for x in xs)
        b = sxy / sxx
        return sum(((v - ym) - b * (x - xm)) ** 2 for x, v in zip(xs, ys))

    # `localcontext` and not `getcontext().prec = ...`: see ORACLE_PREC.
    with localcontext() as ctx:
        ctx.prec = ORACLE_PREC
        lt = [Decimal(t).ln() for t in taus]
        lf = [(Decimal(v.numerator) / Decimal(v.denominator)).ln() / Decimal(2)
              for v in f2]
        scores = []
        for i in range(min_each_side(ntt), ntt - min_each_side(ntt) + 1):
            scores.append((ss(lt[:i], lf[:i]) + ss(lt[i - 1:], lf[i - 1:]), i))
        best = min(scores)
        rest = min(s for s, i in scores if i != best[1])
        margin = float((rest - best[0]) / best[0])
    return best[1], ntt, margin


# ------------------------------------------------------------- sections
def section_s():
    head("S. The setting")
    row("numpy", np.__version__, "pandas", pd.__version__)
    row("pandas_ta", ta.version)
    row("module", MODULE.__file__)
    row("LAG", LAG, "N_TAU_STEPS", N_TAU_STEPS, "TAU_MIN", TAU_MIN,
        "Q", Q, "MIN_POINTS", MIN_POINTS)
    row("MIN_LENGTH", MIN_LENGTH, "NOISE_FLOOR", f"{NOISE_FLOOR:.3e}",
        "CHUNK_VALUES", CHUNK_VALUES)
    for name in ("pycatch22", "scipy", "sklearn"):
        row(name, "installed" if importlib.util.find_spec(name)
            else "ABSENT")
    row("frames", list(FRAMES), "bars each", N)
    # The denominator of the "no shipped module imports the GPL-3.0
    # reference" claim, counted rather than remembered.
    files = sorted((ROOT / "pandas_ta").rglob("*.py"))
    imports = [str(p.relative_to(ROOT)) for p in files
               for line in p.read_text(encoding="utf-8").splitlines()
               if (line.strip().startswith(("import ", "from ")))
               and "catch22" in line.strip().replace("c22", "")]
    row(".py files under pandas_ta/", len(files),
        "of which import the reference", len(imports), imports)


def section_a():
    head("A1. The scale ladder is a function of `length` alone")
    for length in (MIN_LENGTH, 67, 80, 100, 120, 250, 400):
        t = scales(length)
        ntt = int(t.size)
        a = min_each_side(ntt) if ntt else 0
        row(f"length {length}", f"points {-(-length // LAG)}",
            f"scales {ntt}", f"{list(t)[:6]} .. {list(t)[-3:]}",
            f"each side {a}",
            f"values {max(0, ntt - 2 * a + 1)}",
            f"bounds {prop_bounds(length)}")
    t = scales(LENGTH)
    row("default ladder", list(t))
    row("candidate breaks at the default",
        list(range(MIN_POINTS, t.size - MIN_POINTS + 1)))
    row("the values the column can take",
        [f"{i}/{t.size}={i / t.size:.6f}"
         for i in range(MIN_POINTS, t.size - MIN_POINTS + 1)])

    head("A2. The vectorised ladder and the hand-spelled one")
    for length in (67, 100, 137, 250):
        a = [int(v) for v in scales(length)]
        b = scales_def(length)
        row(f"length {length}", a == b, len(a), len(b))

    head("A3. How close any step lands to a rounding flip")
    points = -(-LENGTH // LAG)
    hi = points // 2
    worst = 1.0
    for i in range(N_TAU_STEPS):
        x = math.exp(math.log(float(TAU_MIN))
                     + i * (math.log(float(hi)) - math.log(float(TAU_MIN)))
                     / (N_TAU_STEPS - 1))
        worst = min(worst, abs(x - math.floor(x) - 0.5))
    row("closest any default step comes to a half", f"{worst:.6f}")
    row("numpy round (half to even) gives the same ladder",
        [int(v) for v in scales(LENGTH)] == scales_def(LENGTH,
                                                       rounding="even"))

    head("A4. Shipped against the hand-spelled definition, every window")
    row("frame", "windows", "bit-equal", "max |gap|")
    for name in FRAMES:
        win, bars = windows(FRAMES[name])
        n = bit = 0
        gap = 0.0
        for i in range(0, win.shape[0], 7):
            mine = shipped_on(win[i])
            theirs = value_def(win[i])
            if math.isnan(mine) and math.isnan(theirs):
                continue
            n += 1
            bit += int(mine == theirs)
            gap = max(gap, abs(mine - theirs))
        row(name, n, bit, f"{gap:.3e}")

    head("A5. The readings the definition leaves open, priced")
    print("Each column is the share of sampled windows whose value MOVES")
    print("under that reading, and the worst gap it opens.")
    readings = {
        "lag: keep the LAST point of each pair (end-aligned)":
            dict(decimate="last"),
        "lag: no decimation at all": dict(decimate="none"),
        "cumsum BEFORE the decimation": dict(cumsum="before"),
        "ladder top from the RAW length": dict(top="half-raw"),
        "ladder rounded DOWN": dict(rounding="floor"),
        "ladder rounded UP": dict(rounding="ceil"),
        "score: sum of NORMS, not of squares": dict(score="norm"),
        "score: each norm over its own point count": dict(score="mean-norm"),
        "pieces DISJOINT at the break": dict(share=False),
        "output (break - 1) / ntt": dict(prop="(break-1)/ntt"),
        "output break / (ntt - 1)": dict(prop="break/(ntt-1)"),
        "MIN_POINTS 6": dict(min_points=6),
        "MIN_POINTS 7": dict(min_points=7),
        "MIN_POINTS 9": dict(min_points=9),
        "the fluctuation divided by tau - 2 (the box's d.o.f.)":
            dict(divisor="tau-2"),
        "the leftover points off the HEAD, not the tail":
            dict(remainder="head"),
        "the population z-score (ddof 0)": dict(ddof=0),
        "NO z-score at all": dict(zscore=False),
        "q = 1 (mean absolute fluctuation)": dict(q=1),
        "per-box pooling": dict(pool="perbox"),
        "detrend order 2": dict(detrend=2),
    }
    row("reading", "windows", "moved", "max |gap|", "Spearman")
    for label, kw in readings.items():
        n = moved = 0
        gap = 0.0
        mine_v, theirs_v = [], []
        for name in FRAMES:
            win, _ = windows(FRAMES[name])
            for i in range(0, win.shape[0], 23):
                mine = shipped_on(win[i])
                theirs = value_def(win[i], **kw)
                if math.isnan(mine):
                    continue
                n += 1
                if math.isnan(theirs):
                    moved += 1
                    continue
                mine_v.append(mine)
                theirs_v.append(theirs)
                moved += int(mine != theirs)
                gap = max(gap, abs(mine - theirs))
        row(label, n, moved, f"{gap:.3e}", f"{spearman(mine_v, theirs_v):+.4f}")

    head("A6. The exact oracle: the break, and how close the race is")
    row("frame", "windows", "break agrees", "min margin", "median margin")
    for name in FRAMES:
        win, bars = windows(FRAMES[name])
        agree = n = 0
        margins = []
        for i in range(0, win.shape[0], 97):
            got = value_exact(win[i])
            mine = shipped_on(win[i])
            if got is None or math.isnan(mine):
                continue
            n += 1
            brk, ntt, margin = got
            agree += int(abs(mine - brk / ntt) < 1e-15)
            margins.append(margin)
        row(name, n, agree, f"{min(margins):.3e}" if margins else "-",
            f"{float(np.median(margins)):.3e}" if margins else "-")


def section_p():
    head("P. The reference implementation as a BLACK BOX (GPL-3.0, opt-in)")
    print("pycatch22 is GPL-3.0 and this fork is MIT. It is run here to")
    print("MEASURE only -- the same use docs/issues/screen/ind_screen_r3.py")
    print("makes of it -- and the question it answers is which reading of the")
    print("definition it implements, and whether this port is the column the")
    print("2026-10-24 screen's Gate E numbers were measured on.")
    if importlib.util.find_spec("pycatch22") is None:
        row("pycatch22", "ABSENT -- section P cannot run")
        return
    import pycatch22

    probe = pycatch22.catch22_all(
        [float(v) for v in returns(FRAMES["walk"])[:LENGTH]],
        short_names=True)
    names = probe["short_names"]
    row("catch22_all names matching 'Fluct'",
        [n for n in names if "fluct" in n.lower()])
    want = [n for n in names if "dfa" in n.lower()]
    row("the DFA one", want)
    which = names.index(want[0])
    row("its index", which)

    def ref_all(window):
        out = pycatch22.catch22_all([float(v) for v in window])
        return float(out["values"][which])

    head("P0. Entry points, and whether the reference z-scores for us")
    win, _ = windows(FRAMES["walk"])
    w = win[0]
    z = (w - w.mean()) / w.std(ddof=ZSCORE_DDOF)
    row("catch22_all on the raw window", f"{ref_all(w):.12f}")
    row("catch22_all on the z-scored window", f"{ref_all(z):.12f}")
    row("catch22_all on 8x the window", f"{ref_all(8.0 * w):.12f}")
    row("this port", f"{shipped_on(w):.12f}")
    row("the ladder this port uses", list(scales(LENGTH)))

    head("P1. Shipped against the reference, EVERY window of six frames")
    row("frame", "windows", "bit-equal", "equal to 1e-12", "max |gap|",
        "Spearman")
    tot = {"n": 0, "bit": 0, "near": 0}
    all_mine, all_ref = [], []
    every = []
    for name in FRAMES:
        win, bars = windows(FRAMES[name])
        n = bit = near = 0
        gap = 0.0
        mine_v, ref_v = [], []
        for i in range(win.shape[0]):
            mine = shipped_on(win[i])
            if math.isnan(mine):
                continue
            r = ref_all(win[i])
            n += 1
            mine_v.append(mine)
            ref_v.append(r)
            bit += int(mine == r)
            near += int(abs(mine - r) <= 1e-12)
            if abs(mine - r) > 1e-12:
                every.append((name, int(bars[i]), mine, r))
            gap = max(gap, abs(mine - r))
        row(name, n, bit, near, f"{gap:.3e}", f"{spearman(mine_v, ref_v):+.4f}")
        tot["n"] += n
        tot["bit"] += bit
        tot["near"] += near
        all_mine += mine_v
        all_ref += ref_v
    row("TOTAL", tot["n"], tot["bit"], tot["near"], "",
        f"{spearman(all_mine, all_ref):+.4f}")
    print(f"{len(every)} disagreements beyond 1e-12"
          f" (frame, bar, mine, reference); first 40:")
    for cell in every[:40]:
        print(" ", cell)
    vals = sorted(set(round(v, 12) for v in all_ref))
    row("distinct values the reference takes", len(vals), vals[:25])
    mv = sorted(set(round(v, 12) for v in all_mine))
    row("distinct values this port takes", len(mv), mv[:25])

    head("P1b. WHICH reading the reference implements")
    print("Every fifth window above, scored by this port and by the other")
    print("defensible readings of the same definition. The count is windows")
    print("where that reading equals the REFERENCE to 1e-12.")
    def even_value(w, how):
        curve = fluctuations(w)
        if curve is None:
            return float("nan")
        if any(not (f > 0.0) or not math.isfinite(f) for _, f in curve):
            return float("nan")
        got = break_of(_even_curve(curve, how))
        return float("nan") if got is None else got

    variants = {
        "shipped (decimate-first, cumsum after, SQUARES, shared break,"
        " max(8, round(ntt/4)) each side)": lambda w: shipped_on(w),
        "shipped, plain-Python spelling": lambda w: value_def(w),
        "lag: end-aligned decimation": lambda w: value_def(w, decimate="last"),
        "lag: no decimation": lambda w: value_def(w, decimate="none"),
        "cumsum before the decimation": lambda w: value_def(w, cumsum="before"),
        "ladder top from the raw length": lambda w: value_def(w, top="half-raw"),
        "ladder rounded down": lambda w: value_def(w, rounding="floor"),
        "score: sum of NORMS": lambda w: value_def(w, score="norm"),
        "score: norm per point": lambda w: value_def(w, score="mean-norm"),
        "pieces disjoint at the break": lambda w: value_def(w, share=False),
        "output (break-1)/ntt": lambda w: value_def(w, prop="(break-1)/ntt"),
        "output break/(ntt-1)": lambda w: value_def(w, prop="break/(ntt-1)"),
        "flat floor of 6 scales each side": lambda w: value_def(w,
                                                               min_points=6),
        "flat floor of 7 scales each side": lambda w: value_def(w,
                                                               min_points=7),
        "flat floor of 9 scales each side": lambda w: value_def(w,
                                                               min_points=9),
        "q = 1": lambda w: value_def(w, q=1),
        "detrend order 2": lambda w: value_def(w, detrend=2),
        "the fluctuation over the box's d.o.f. (tau - 2)":
            lambda w: value_def(w, divisor="tau-2"),
        "the leftover points off the HEAD": lambda w: value_def(
            w, remainder="head"),
        "the curve spline-resampled onto an even log grid":
            lambda w: even_value(w, "spline-even"),
        "the curve linearly resampled onto an even log grid":
            lambda w: even_value(w, "linear-even"),
        "no decimation AND cumsum before":
            lambda w: value_def(w, decimate="none", cumsum="before"),
        "end-aligned AND cumsum before":
            lambda w: value_def(w, decimate="last", cumsum="before"),
    }
    tally: dict[str, int] = {}
    n_scored = 0
    for name in FRAMES:
        win, _ = windows(FRAMES[name])
        for i in range(0, win.shape[0], 5):
            w = win[i]
            if math.isnan(shipped_on(w)):
                continue
            r = ref_all(w)
            n_scored += 1
            for key, fn in variants.items():
                val = fn(w)
                tally[key] = tally.get(key, 0) + int(
                    (math.isfinite(val) and abs(val - r) <= 1e-12)
                    or (math.isnan(val) and math.isnan(r)))
    row("windows scored", n_scored)
    for key, hit in sorted(tally.items(), key=lambda kv: -kv[1]):
        row(f"{hit} of {n_scored}", key)


def _curve_grid(window):
    """Every candidate FLUCTUATION CURVE for one window, keyed by reading.

    The expensive half of a candidate pipeline is the curve; the break search
    over it is cheap. Section Q scores the full product by computing these
    once per window and then searching each of them every way.
    """
    out = {}
    default_taus = [int(t) for t in scales(len(window))]
    raw_taus = scales_def(len(window), decimate="none")
    for data in ("first", "last", "none"):
        for cs in ("after", "before"):
            for tag, taus in (("ladder-decimated", default_taus),
                              ("ladder-raw", raw_taus)):
                key = (data, cs, tag)
                out[key] = fluctuations(window, decimate=data, cumsum=cs,
                                        taus=taus)
    return out


def _search_all(curve, score, share):
    """`(sserr, candidates)` for EVERY split of a curve, 2 .. ntt-1."""
    if curve is None:
        return None, None
    ntt = len(curve)
    if any(not (f > 0.0) or not math.isfinite(f) for _, f in curve):
        return None, None
    lt = [math.log(float(t)) for t, _ in curve]
    lf = [math.log(f) for _, f in curve]
    cands, errs = [], []
    for i in range(2, ntt):
        r1 = lt[:i], lf[:i]
        r2 = (lt[i - 1:], lf[i - 1:]) if share else (lt[i:], lf[i:])
        if len(r2[0]) < 2:
            continue
        e1 = _fit_resid(*r1)
        e2 = _fit_resid(*r2)
        if score == "norm":
            s = math.sqrt(math.fsum(v * v for v in e1)) \
                + math.sqrt(math.fsum(v * v for v in e2))
        elif score == "ss":
            s = math.fsum(v * v for v in e1) + math.fsum(v * v for v in e2)
        elif score == "rms":
            s = math.sqrt(math.fsum(v * v for v in e1) / len(e1)) \
                + math.sqrt(math.fsum(v * v for v in e2) / len(e2))
        else:
            s = math.sqrt(math.fsum(v * v for v in e1)) / len(e1) \
                + math.sqrt(math.fsum(v * v for v in e2)) / len(e2)
        cands.append(i)
        errs.append(s)
    return errs, cands


def section_q():
    head("Q. The FULL grid of readings, fitted to the reference as a black box")
    print("Each row is one pipeline: how the lag is applied, where the")
    print("cumulative sum goes, which ladder, how a split is scored, whether")
    print("the two pieces share the break scale, and how many scales the")
    print("search leaves on each side. The count is windows whose value")
    print("equals the REFERENCE to 1e-12.")
    if importlib.util.find_spec("pycatch22") is None:
        row("pycatch22", "ABSENT -- section Q cannot run")
        return
    import pycatch22
    probe = pycatch22.catch22_all([float(v) for v in
                                   returns(FRAMES["walk"])[:LENGTH]],
                                  short_names=True)
    which = probe["short_names"].index("dfa")

    def ref_all(window):
        return float(pycatch22.catch22_all(
            [float(v) for v in window])["values"][which])

    tally: dict[tuple, int] = {}
    n_scored = 0
    stride = 29
    for name in FRAMES:
        win, _ = windows(FRAMES[name])
        for i in range(0, win.shape[0], stride):
            w = win[i]
            if math.isnan(shipped_on(w)):
                continue
            r = ref_all(w)
            n_scored += 1
            grid = _curve_grid(w)
            for ckey, curve in grid.items():
                ntt = len(curve) if curve else 0
                for score in ("norm", "ss", "rms", "mean-norm"):
                    for share in (True, False):
                        errs, cands = _search_all(curve, score, share)
                        if errs is None:
                            continue
                        for mp in (4, 5, 6, 7, 8, 9):
                            # `c` scales in the first piece; the second holds
                            # `ntt - c + 1` when the two SHARE the break
                            # scale and `ntt - c` when they do not. Both
                            # pieces must clear `mp`.
                            keep = [(e, c) for e, c in zip(errs, cands)
                                    if c >= mp
                                    and ((ntt - c + 1) if share
                                         else (ntt - c)) >= mp]
                            if not keep:
                                continue
                            best = min(keep)[1]
                            for denom, dtag in ((ntt, "ntt"),
                                                (ntt - 1, "ntt-1")):
                                for off, otag in ((0, "break"),
                                                  (-1, "break-1")):
                                    val = (best + off) / denom
                                    k = (ckey, score, share, mp, dtag, otag)
                                    tally[k] = tally.get(k, 0) + int(
                                        abs(val - r) <= 1e-12)
    row("windows scored", n_scored)
    ranked = sorted(tally.items(), key=lambda kv: -kv[1])
    for k, hit in ranked[:30]:
        row(f"{hit} of {n_scored}", *k)
    row("distinct pipelines scored", len(tally))


def section_r():
    head("R. WHERE the reference's answer sits in this port's own ranking")
    print("If the only difference were the candidate RANGE, the reference's")
    print("break would be this port's argmin restricted to the interior.")
    if importlib.util.find_spec("pycatch22") is None:
        row("pycatch22", "ABSENT -- section R cannot run")
        return
    import pycatch22
    probe = pycatch22.catch22_all([float(v) for v in
                                   returns(FRAMES["walk"])[:LENGTH]],
                                  short_names=True)
    which = probe["short_names"].index("dfa")

    def ref_all(window):
        return float(pycatch22.catch22_all(
            [float(v) for v in window])["values"][which])

    for score in ("norm", "ss"):
        rank_hist: dict[int, int] = {}
        n = 0
        ref_k, mine_k = [], []
        for name in FRAMES:
            win, _ = windows(FRAMES[name])
            for i in range(0, win.shape[0], 17):
                w = win[i]
                if math.isnan(shipped_on(w)):
                    continue
                curve = fluctuations(w)
                errs, cands = _search_all(curve, score, True)
                if errs is None:
                    continue
                r = ref_all(w)
                ntt = len(curve)
                k = int(round(r * ntt))
                if abs(k / ntt - r) > 1e-9 or k not in cands:
                    rank_hist[-1] = rank_hist.get(-1, 0) + 1
                    n += 1
                    continue
                order = [c for _, c in sorted(zip(errs, cands))]
                rank_hist[order.index(k)] = rank_hist.get(order.index(k), 0) + 1
                n += 1
                ref_k.append(k)
                mine_k.append(order[0])
        row(f"score {score}: windows", n)
        row("  rank of the reference's break in this port's ordering",
            {kk: rank_hist[kk] for kk in sorted(rank_hist)})
        row("  reference break histogram",
            {kk: ref_k.count(kk) for kk in sorted(set(ref_k))})
        row("  this port's break histogram",
            {kk: mine_k.count(kk) for kk in sorted(set(mine_k))})


def _ref_fn():
    """The reference's DFA value for one window, or None if it is absent."""
    if importlib.util.find_spec("pycatch22") is None:
        return None
    import pycatch22
    probe = pycatch22.catch22_all([float(v) for v in
                                   returns(FRAMES["walk"])[:LENGTH]],
                                  short_names=True)
    which = probe["short_names"].index("dfa")

    def ref_all(window):
        return float(pycatch22.catch22_all(
            [float(v) for v in window])["values"][which])
    return ref_all


def section_q2():
    head("Q2. The grid again, with the FLUCTUATION's divisor open")
    print("Section Q pins the data pipeline -- decimate by 2 keeping the")
    print("first point, cumulative sum after, ladder from the decimated")
    print("length -- on every one of its top rows. What is left open is what")
    print("the pooled sum of squared residuals is divided by, which shifts")
    print("log F by a TAU-DEPENDENT constant and so moves the break, and")
    print("which end the leftover points come off.")
    ref_all = _ref_fn()
    if ref_all is None:
        row("pycatch22", "ABSENT -- section Q2 cannot run")
        return
    divisors = ("tau", "tau-1", "tau-2", "n-1", "boxes", "one", "one-tau")
    tally: dict[tuple, int] = {}
    n_scored = 0
    for name in FRAMES:
        win, _ = windows(FRAMES[name])
        for i in range(0, win.shape[0], 29):
            w = win[i]
            if math.isnan(shipped_on(w)):
                continue
            r = ref_all(w)
            n_scored += 1
            for divisor in divisors:
                for rem in ("tail", "head"):
                    curve = fluctuations(w, divisor=divisor, remainder=rem)
                    ntt = len(curve) if curve else 0
                    for score in ("norm", "ss", "rms", "mean-norm"):
                        for share in (True, False):
                            errs, cands = _search_all(curve, score, share)
                            if errs is None:
                                continue
                            for mp in (5, 6, 7, 8, 9):
                                keep = [(e, c) for e, c in zip(errs, cands)
                                        if c >= mp
                                        and ((ntt - c + 1) if share
                                             else (ntt - c)) >= mp]
                                if not keep:
                                    continue
                                best = min(keep)[1]
                                k = (divisor, rem, score, share, mp)
                                tally[k] = tally.get(k, 0) + int(
                                    abs(best / ntt - r) <= 1e-12)
    row("windows scored", n_scored)
    for k, hit in sorted(tally.items(), key=lambda kv: -kv[1])[:25]:
        row(f"{hit} of {n_scored}", *k)
    row("distinct pipelines scored", len(tally))


def _even_curve(curve, how):
    """The curve re-sampled onto an EVENLY spaced log-tau grid.

    hctsa's own comment on this operation says the two-piece fit is preceded
    by a spline interpolation "to get an even sampling of the interval
    (currently, in the log scale, there are relatively more at large
    scales)". That is a reading of the definition, and it changes the
    residuals of both straight-line fits, so section Q3 prices it.
    """
    lt = np.array([math.log(float(t)) for t, _ in curve])
    lf = np.array([math.log(f) for _, f in curve])
    grid = np.linspace(lt[0], lt[-1], lt.size)
    if how == "linear-even":
        vals = np.interp(grid, lt, lf)
    else:
        from scipy.interpolate import CubicSpline
        vals = CubicSpline(lt, lf, bc_type="not-a-knot")(grid)
    return [(math.exp(x), math.exp(y)) for x, y in zip(grid, vals)]


def section_q3():
    head("Q3. The grid again, with the EVEN re-sampling and the range open")
    print("Two things section Q2 could not separate: whether the two-piece")
    print("fit runs on the ladder as measured or on an EVENLY re-sampled")
    print("copy of it (hctsa's own comment says the latter), and what the")
    print("search range is -- the reference takes exactly the six values")
    print("8/21 .. 13/21 over 8,400 windows, which no (share, min-points)")
    print("pair in Q2 reproduces as a range.")
    ref_all = _ref_fn()
    if ref_all is None:
        row("pycatch22", "ABSENT -- section Q3 cannot run")
        return
    ranges = ((7, 15), (8, 14), (8, 13), (9, 13), (6, 15), (6, 16), (7, 14))
    tally: dict[tuple, int] = {}
    n_scored = 0
    for name in FRAMES:
        win, _ = windows(FRAMES[name])
        for i in range(0, win.shape[0], 29):
            w = win[i]
            if math.isnan(shipped_on(w)):
                continue
            r = ref_all(w)
            n_scored += 1
            plain = fluctuations(w)
            for tag in ("as measured", "spline-even", "linear-even"):
                curve = plain if tag == "as measured" else _even_curve(plain,
                                                                       tag)
                ntt = len(curve)
                for score in ("norm", "ss", "rms", "mean-norm"):
                    for share in (True, False):
                        errs, cands = _search_all(curve, score, share)
                        if errs is None:
                            continue
                        for lo, hi in ranges:
                            keep = [(e, c) for e, c in zip(errs, cands)
                                    if lo <= c <= hi]
                            if not keep:
                                continue
                            best = min(keep)[1]
                            k = (tag, score, share, f"{lo}..{hi}")
                            tally[k] = tally.get(k, 0) + int(
                                abs(best / ntt - r) <= 1e-12)
    row("windows scored", n_scored)
    for k, hit in sorted(tally.items(), key=lambda kv: -kv[1])[:25]:
        row(f"{hit} of {n_scored}", *k)
    row("distinct pipelines scored", len(tally))


def section_q4():
    head("Q4. The search RANGE, read off the reference at seven lengths")
    print("Q3 pins the reference's reading at the default length: the sum of")
    print("SQUARED residuals, the two pieces sharing the break scale, and a")
    print("search over the splits that leave 8 .. 13 of the 21 scales in the")
    print("first piece. 8 and 13 are two numbers, not a rule. Feeding the")
    print("reference windows of other lengths gives it other ladders, and")
    print("the smallest and largest value it then returns is the range.")
    ref_all = _ref_fn()
    if ref_all is None:
        row("pycatch22", "ABSENT -- section Q4 cannot run")
        return
    row("length", "scales", "ref lo", "ref hi", "windows", "distinct",
        "mp+2 .. ntt-mp-2")
    found = {}
    for length in (MIN_LENGTH, 80, 100, 120, 150, 250, 400):
        taus = scales(length)
        ntt = taus.size
        ks = []
        for name in ("walk", "ar1", "student-t"):
            win, _ = windows(FRAMES[name], length=length)
            for i in range(0, win.shape[0], 31):
                v = ref_all(win[i])
                k = v * ntt
                if abs(k - round(k)) > 1e-9:
                    ks.append(None)
                else:
                    ks.append(int(round(k)))
        good = [k for k in ks if k is not None]
        lo, hi = (min(good), max(good)) if good else (None, None)
        found[length] = (ntt, lo, hi)
        row(length, ntt, lo, hi, len(ks), len(set(good)),
            f"{MIN_POINTS + 2} .. {ntt - MIN_POINTS - 2}")
    head("Q4b. Which rule those seven (lo, hi) pairs obey")
    rules = {
        "mp+2 .. ntt-mp-2": lambda ntt: (MIN_POINTS + 2,
                                         ntt - MIN_POINTS - 2),
        "mp+1 .. ntt-mp": lambda ntt: (MIN_POINTS + 1, ntt - MIN_POINTS),
        "mp+2 .. ntt-mp-3": lambda ntt: (MIN_POINTS + 2,
                                         ntt - MIN_POINTS - 3),
        "8 .. ntt-8": lambda ntt: (8, ntt - 8),
        "ceil(ntt/e) .. floor(ntt(1-1/e))":
            lambda ntt: (math.ceil(ntt / math.e),
                         math.floor(ntt * (1 - 1 / math.e))),
    }
    row("rule", *[f"length {L}" for L in found])
    for label, fn in rules.items():
        cells = []
        for L, (ntt, lo, hi) in found.items():
            want = fn(ntt)
            cells.append(f"{want[0]}..{want[1]}"
                         + ("  OK" if want == (lo, hi) else "  no"))
        row(label, *cells)


def section_q5():
    head("Q5. The fitted reading, PREDICTING the reference at other lengths")
    print("Q3 fitted the reading at `length` 100 and Q4 read the range off")
    print("the same output. This section is the test that is not a fit: the")
    print("shipped module, at lengths it was never fitted on, against the")
    print("reference. `MIN_LENGTH` is the floor, and 67 and 80 are BELOW it")
    print("-- 67 is where the reference's own search runs out of candidates")
    print("and it returns 1.0 -- so they are reported through the plain")
    print("definition rather than through the module, which refuses them.")
    ref_all = _ref_fn()
    if ref_all is None:
        row("pycatch22", "ABSENT -- section Q5 cannot run")
        return
    row("length", "scales", "windows", "bit-equal", "to 1e-12", "max |gap|",
        "ref values seen")
    for length in (67, 80, 100, 120, 150, 250, 400):
        ntt = scales(length).size
        n = bit = near = 0
        gap = 0.0
        seen = set()
        for name in ("walk", "ar1", "student-t"):
            win, _ = windows(FRAMES[name], length=length)
            for i in range(0, win.shape[0], 31):
                w = win[i]
                mine = value_def(w)
                r = ref_all(w)
                seen.add(round(r * ntt, 6))
                if math.isnan(mine):
                    continue
                n += 1
                bit += int(mine == r)
                near += int(abs(mine - r) <= 1e-12)
                gap = max(gap, abs(mine - r))
        row(length, ntt, n, bit, near, f"{gap:.3e}",
            sorted(seen)[:4] + ["..."] + sorted(seen)[-2:]
            if len(seen) > 6 else sorted(seen))


#: Candidate rules for `a(ntt)`, the fewest scales the reference's break
#: search leaves on each side. Section Q6 fits them to the reference's own
#: output over every ladder size it can be handed, and section Q7 tests the
#: survivors by PREDICTION.
RANGE_RULES = {
    "8": lambda ntt: 8,
    "max(8, ceil(ntt/4))": lambda ntt: max(8, -(-ntt // 4)),
    "max(8, floor(ntt/4) + 1)": lambda ntt: max(8, ntt // 4 + 1),
    "max(8, round(ntt/4) half-up)": lambda ntt: max(
        8, int(math.floor(ntt / 4 + 0.5))),
    "ceil(ntt/4)": lambda ntt: -(-ntt // 4),
    "max(8, ceil((ntt + 1)/4))": lambda ntt: max(8, -(-(ntt + 1) // 4)),
    "max(8, ceil(ntt/4) + 1)": lambda ntt: max(8, -(-ntt // 4) + 1),
}


def _ntt_ladder(lo=70, hi=1400):
    """One `length` per distinct ladder size, the shortest of each."""
    out = {}
    for length in range(lo, hi):
        k = int(scales(length).size)
        out.setdefault(k, length)
    return out


def section_q6():
    head("Q6. `a(ntt)`, the search range, read off the reference at every"
         " ladder size")
    print("The range the reference searches is symmetric -- every ladder")
    print("size below has `lo + hi = ntt` -- so one number `a` describes it.")
    print("`a` is read as `min(lo, ntt - hi)` over the values the reference")
    print("returns, which is an UPPER bound on the true `a` only if the")
    print("optimum reaches the boundary; section Q7 is the test that does")
    print("not depend on that, by PREDICTION.")
    ref_all = _ref_fn()
    if ref_all is None:
        row("pycatch22", "ABSENT -- section Q6 cannot run")
        return
    rows = []
    row("length", "ntt", "lo", "hi", "lo+hi", "a seen", "windows")
    for ntt, length in sorted(_ntt_ladder().items()):
        if ntt < 16 or length > 1300:
            continue
        ks = []
        for name in ("walk", "ar1", "student-t", "penny"):
            win, _ = windows(FRAMES[name], length=length)
            if win.shape[0] < 3:
                continue
            for i in range(0, win.shape[0], 37):
                v = ref_all(win[i])
                k = v * ntt
                ks.append(int(round(k)) if abs(k - round(k)) < 1e-9 else None)
        good = [k for k in ks if k is not None]
        if not good:
            continue
        lo, hi = min(good), max(good)
        a = min(lo, ntt - hi)
        rows.append((ntt, a))
        row(length, ntt, lo, hi, lo + hi, a, len(good))
    head("Q6b. Which rule fits every one of those")
    row("rule", "ladder sizes fitted", "misses")
    for label, fn in RANGE_RULES.items():
        bad = [(ntt, a, fn(ntt)) for ntt, a in rows if fn(ntt) != a]
        row(label, f"{len(rows) - len(bad)} of {len(rows)}",
            bad[:8] if bad else "-")


def section_q7():
    head("Q7. The surviving range rules, tested by PREDICTION")
    print("For every ladder size, the whole pipeline is run under each rule")
    print("and compared with the reference window by window. A rule whose")
    print("range is too WIDE shows up here even where the extra candidate")
    print("never won in Q6, because it sometimes wins.")
    ref_all = _ref_fn()
    if ref_all is None:
        row("pycatch22", "ABSENT -- section Q7 cannot run")
        return
    tally = {k: [0, 0] for k in RANGE_RULES}
    per_rule_misses = {k: [] for k in RANGE_RULES}
    for ntt, length in sorted(_ntt_ladder().items()):
        if ntt < 16 or length > 1300:
            continue
        for name in ("walk", "ar1", "student-t", "penny"):
            win, _ = windows(FRAMES[name], length=length)
            if win.shape[0] < 3:
                continue
            for i in range(0, win.shape[0], 53):
                w = win[i]
                curve = fluctuations(w, taus=[int(t) for t in scales(length)])
                errs, cands = _search_all(curve, "ss", True)
                if errs is None:
                    continue
                r = ref_all(w)
                for label, fn in RANGE_RULES.items():
                    a = fn(ntt)
                    keep = [(e, c) for e, c in zip(errs, cands)
                            if a <= c <= ntt - a]
                    tally[label][1] += 1
                    if not keep:
                        per_rule_misses[label].append((ntt, "no candidate"))
                        continue
                    best = min(keep)[1]
                    if abs(best / ntt - r) <= 1e-12:
                        tally[label][0] += 1
                    elif len(per_rule_misses[label]) < 6:
                        per_rule_misses[label].append(
                            (length, ntt, best, round(r * ntt, 4)))
    row("rule", "windows agreeing", "first misses (length, ntt, mine, ref)")
    for label in RANGE_RULES:
        hit, n = tally[label]
        row(label, f"{hit} of {n}", per_rule_misses[label][:4] or "-")


# ------------------------------------------------------------- Gate B
#: The mutants `tests/test_c22_dfa.py` also builds. Kept here so the receipt
#: quotes a run of its own; the two dicts must stay identical, and
#: `test_the_measure_script_carries_the_same_mutants` imports this file by
#: path and compares them WHOLE -- edit strings included -- so a drift on
#: either side fails rather than leaving two different Gate Bs both green.
MUTANTS = {
    "write-back-dated": ("out[length + a:length + b]",
                         "out[length - 1 + a:length - 1 + b]"),
    "window-one-ahead": ("win = sliding_window_view(r, length)",
                         "win = sliding_window_view(r, length + 1)[:, 1:]"),
    "window-two-ahead": ("win = sliding_window_view(r, length)",
                         "win = sliding_window_view(r, length + 2)[:, 2:]"),
    "window-ten-ahead": ("win = sliding_window_view(r, length)",
                         "win = sliding_window_view(r, length + 10)[:, 10:]"),
    "returns-rolled": ("r = np.where(np.isfinite(r), r, np.nan)",
                       "r = np.roll(np.where(np.isfinite(r), r, np.nan), -1)"),
    "mask-back-dated": ("r = np.where(np.isfinite(r), r, np.nan)",
                        "r = np.where(np.isfinite(np.roll(r, -1)), r, np.nan)"),
    "chunk-wide-demean": (
        "z = (block - block.mean(axis=1, keepdims=True)) / sd[:, None]",
        "z = (block - block.mean()) / sd[:, None]"),
    "chunk-wide-sd": (
        "sd = block.std(axis=1, ddof=ZSCORE_DDOF)",
        "sd = np.full(block.shape[0], block.std(ddof=ZSCORE_DDOF))"),
    "profile-across-rows": (
        "        profile = np.cumsum(y, axis=1)",
        "        profile = np.cumsum(y.ravel()).reshape(y.shape)"),
    "end-aligned-decimation": ("        y = z[:, ::LAG]",
                               "        y = z[:, LAG - 1::LAG]"),
    "norms-not-squares": ("    return (resid * resid).sum(axis=1)",
                          "    return np.sqrt((resid * resid).sum(axis=1))"),
    "no-overflow-guard": ("bad |= ~(sd > NOISE_FLOOR) | ~np.isfinite(sd)",
                          "bad |= ~(sd > NOISE_FLOOR)"),
    "no-floor": ("bad |= ~(sd > NOISE_FLOOR) | ~np.isfinite(sd)",
                 "bad |= ~(sd > 0.0)"),
    "no-zero-fluctuation-guard": (
        "        bad |= ~(f2 > 0.0).all(axis=1) | ~np.isfinite(f2).all(axis=1)",
        "        bad |= ~np.isfinite(f2).all(axis=1)"),
    #: Both value guards at once, which is the only way to see what either
    #: of them buys: section H2 measures that the `isfinite(sd)` limb alone
    #: is REDUNDANT, because an overflowing window z-scores to all zeros and
    #: the zero-fluctuation guard catches it anyway.
    "no-either-guard": (
        ("bad |= ~(sd > NOISE_FLOOR) | ~np.isfinite(sd)",
         "bad |= ~(sd > NOISE_FLOOR)"),
        ("        bad |= ~(f2 > 0.0).all(axis=1) | ~np.isfinite(f2).all(axis=1)",
         "        bad |= np.zeros(rows, dtype=bool)"),
    ),
}


def mutant(name):
    """Read the module off disk, edit one write, exec it in memory."""
    edits = MUTANTS[name]
    if isinstance(edits[0], str):
        edits = (edits,)
    src = SRC
    for old, new in edits:
        assert src.count(old) == 1, (name, old, src.count(old))
        src = src.replace(old, new)
    ns = {}
    exec(compile(src, f"<mutant {name}>", "exec"), ns)
    return ns["c22_dfa"]


def _spliced(close, j, seed=909, vol=0.02, jump=1.0):
    """`close` with every bar from `j` on replaced by a fresh path.

    `vol` and `jump` are the instrument's strength. The default is an
    ordinary 2%-a-day path; `vol=0.2, jump=3.0` is the VIOLENT splice section
    B9 uses, which exists because this column takes six values and a gentle
    splice often fails to flip the one integer it reports.
    """
    rng = np.random.default_rng(seed + j)
    c = close.to_numpy(dtype=float).copy()
    c[j:] = c[j - 1] * jump * np.cumprod(
        1.0 + rng.normal(0.0005, vol, c.size - j))
    return pd.Series(c, index=close.index)


def _offsets(n, length=LENGTH, count=35):
    return [int(x) for x in np.linspace(length + 5, n - 5, count).astype(int)]


def _leaks(fn, close, offsets, splices=8, vol=0.02, jump=1.0):
    bad = np.asarray(fn(close), float)
    hits = []
    for j in offsets:
        for s in range(splices):
            other = np.asarray(fn(_spliced(close, j, seed=909 + 7919 * s,
                                           vol=vol, jump=jump)), float)
            if not same(bad[:j], other[:j]):
                hits.append(j)
                break
    return hits


def section_b():
    head("B1. The future-perturbation sweep on the REAL module")
    print("Every close from bar J on is replaced; no bar before J may move.")
    row("frame", "offsets", "leaking", "splices each")
    for name in FRAMES:
        f = FRAMES[name]
        hits = _leaks(c22_dfa, f, _offsets(len(f)), splices=8)
        row(name, 35, len(hits), 8)
    for length in (MIN_LENGTH, 120, 250):
        f = FRAMES["walk"]
        hits = _leaks(lambda s: c22_dfa(s, length=length), f,
                      _offsets(len(f), length), splices=4)
        row(f"walk at length {length}", 35, len(hits), 4)

    head("B2. The mutants, and how much of the sweep catches each")
    row("mutant", "offsets caught of 35", "bars moved on the walk",
        "max |gap|")
    for name in MUTANTS:
        fn = mutant(name)
        hits = _leaks(fn, FRAMES["walk"], _offsets(1500), splices=8)
        got = fn(FRAMES["walk"])
        moved, mask = diff_bars(base("walk"), got)
        row(name, len(hits), f"{moved} value / {mask} mask",
            f"{worst_gap(base('walk'), got):.3e}")

    head("B3. Where a back-dated write first moves a bar")
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
            first_is_j1 += int(int(moved.min()) == j - 1)
    row("offsets that move a pre-splice bar", seen,
        "of which the first moved bar is J-1", first_is_j1)

    head("B4. Why the sweep has the power it has: ties and distinct values")
    print("This column is a RATIO OF SMALL INTEGERS -- 6 possible values at")
    print("the default length -- so neighbouring bars tie often and a one-bar")
    print("shift has a great deal of room to hide. The tie share is the")
    print("ceiling on what any perturbation sweep can see.")
    row("frame", "fired bars", "distinct values", "tie share",
        "value histogram")
    for name in FRAMES:
        a = base(name).dropna().to_numpy()
        hist = {round(v, 6): int(np.sum(a == v)) for v in sorted(set(a))}
        row(name, len(a), len(set(a)),
            f"{float(np.mean(a[1:] == a[:-1])):.4f}", hist)

    head("B6. The dependency map, measured one close at a time")
    print("The sweep above is a prefix test and this column TIES on a fifth")
    print("of neighbouring bars, so it has limited power. This is the direct")
    print("question instead: for one bar T, which closes can move it? Every")
    print("close of the frame is perturbed on its own, by a factor large")
    print("enough that a dependency would show, and the bars that move are")
    print("recorded. A single FUTURE close that moved bar T would be a")
    print("causality break.")
    f = FRAMES["walk"]
    want = np.asarray(base("walk"), float)
    probes = (300, 700, 1100)
    row("bar T", "factor", "closes that move it", "earliest", "latest",
        "any close >= T", "closes at an EVEN distance")
    for factor in (1.5, 1.05):
        movers = {T: [] for T in probes}
        for j in range(len(f)):
            g = f.to_numpy(dtype=float).copy()
            g[j] *= factor
            got = np.asarray(c22_dfa(pd.Series(g, index=f.index)), float)
            for T in probes:
                if got[T] != want[T] or np.isnan(got[T]) != np.isnan(want[T]):
                    movers[T].append(j)
        for T in probes:
            m = movers[T]
            row(T, factor, len(m), min(m) if m else "-", max(m) if m else "-",
                sum(1 for j in m if j >= T),
                sum(1 for j in m if (T - j) % 2 == 0))

    head("B7. The VALUE at bar T does not read close[T] (the mask does: B7b)")
    print("That is not a bug and not a look-ahead -- it is what the lag")
    print("does. The window ending at bar T holds the returns of bars")
    print("T-99 .. T and the decimation keeps every SECOND one from the")
    print("oldest, which drops the return of bar T itself. So the value is")
    print("one bar STALE, and a consumer has to know it.")
    row("bar T", "close[T] moves bar T", "close[T] moves bar T+1")
    for T in (200, 500, 900, 1300):
        g = f.copy()
        g.iloc[T] = g.iloc[T] * 1.5
        got = np.asarray(c22_dfa(g), float)
        row(T, got[T] != want[T], got[T + 1] != want[T + 1])

    head("B7b. The MASK does read close[T], and that is the whole of it")
    print("The VALUE at bar T is a function of closes T-100 .. T-1. The NaN")
    print("MASK is not: the finiteness check and the noise floor run on the")
    print("WHOLE undecimated window, which includes the return of bar T, so")
    print("a bad close at T blanks bar T. Both halves are below. Neither is")
    print("a look-ahead -- every close read is at or before T.")
    row("case", "bar T", "bar T+1")
    for label, edit in (("close[T] x1.5 (finite)", lambda v: v * 1.5),
                        ("close[T] = NaN", lambda v: np.nan),
                        ("close[T] = 0", lambda v: 0.0)):
        moved_t = moved_next = blanked_t = 0
        for T in (200, 500, 900, 1300):
            g = f.to_numpy(dtype=float).copy()
            g[T] = edit(g[T])
            got = np.asarray(c22_dfa(pd.Series(g, index=f.index)), float)
            moved_t += int(got[T] != want[T]
                           and not (np.isnan(got[T]) and np.isnan(want[T])))
            blanked_t += int(np.isnan(got[T]) and not np.isnan(want[T]))
            moved_next += int(got[T + 1] != want[T + 1]
                              and not (np.isnan(got[T + 1])
                                       and np.isnan(want[T + 1])))
        row(label, f"moved {moved_t} of 4, blanked {blanked_t} of 4",
            f"moved or blanked {moved_next} of 4")

    head("B8. The sweep with more splices, on the mutants that DO look ahead")
    for name in ("window-two-ahead", "window-ten-ahead"):
        fn = mutant(name)
        for splices in (8, 32):
            hits = _leaks(fn, FRAMES["walk"], _offsets(1500), splices=splices)
            row(name, f"{splices} splices", f"{len(hits)} of 35 offsets")

    head("B9. The VIOLENT splice: 20% daily vol and a 3x jump at the cut")
    print("A gentle splice has to flip an integer chosen by a minimum over")
    print("six candidates, and often cannot. This instrument scrambles the")
    print("whole fluctuation curve after the cut instead. The real module")
    print("must still be clean under it; the one-bar look-ahead must not be.")
    for label, fn in (("the real module", c22_dfa),
                      ("window-two-ahead (reads close[T+1])",
                       mutant("window-two-ahead")),
                      ("window-ten-ahead", mutant("window-ten-ahead")),
                      ("write-back-dated (causal, see B2)",
                       mutant("write-back-dated")),
                      ("window-one-ahead (causal, see B2)",
                       mutant("window-one-ahead")),
                      ("returns-rolled (causal, see B2)",
                       mutant("returns-rolled")),
                      ("end-aligned-decimation (causal, see B2)",
                       mutant("end-aligned-decimation"))):
        hits = _leaks(fn, FRAMES["walk"], _offsets(1500), splices=8,
                      vol=0.2, jump=3.0)
        row(label, f"{len(hits)} of 35 offsets leak")
    for name in FRAMES:
        f = FRAMES[name]
        hits = _leaks(c22_dfa, f, _offsets(len(f)), splices=8, vol=0.2,
                      jump=3.0)
        row(f"the real module on {name}", f"{len(hits)} of 35 offsets leak")

    head("B5. The mask mutant on a clean frame and on a dirty one")
    fn = mutant("mask-back-dated")
    clean = FRAMES["walk"]
    row("bit-equal on the clean walk", same(c22_dfa(clean), fn(clean)))
    caught = first_j1 = 0
    for j in _offsets(len(clean), count=12):
        dirty = clean.copy()
        dirty.iloc[j] = np.nan
        a = np.asarray(c22_dfa(dirty), float)
        b = np.asarray(fn(dirty), float)
        moved = np.where(~((a == b) | (np.isnan(a) & np.isnan(b))))[0]
        if len(moved):
            caught += 1
            first_j1 += int(int(moved.min()) == j - 1)
    row("caught on a frame with one bad close", f"{caught} of 12",
        "first moved bar is J-1", first_j1)


# ------------------------------------------------------------- Gate C
def section_c():
    head("C1. What fires, and what the column reads")
    row("frame", "bars", "fired", "first fired bar", "min", "median", "max",
        "distinct")
    for name in FRAMES:
        s = base(name)
        a = s.dropna()
        row(name, len(s), int(s.notna().sum()),
            int(np.argmax(s.notna().to_numpy())),
            f"{a.min():.6f}", f"{a.median():.6f}", f"{a.max():.6f}",
            len(set(a.to_numpy())))

    head("C2. The issue's own warning: tick rounding")
    print("A shape feature of z-scored returns can read BIST tick rounding")
    print("rather than return dynamics. These frames are where that would")
    print("show: a 2-lira stock on a 1-kurus tick prints many returns as")
    print("exactly zero.")
    row("frame", "zero returns", "share", "fired", "median", "distinct")
    for name in ("walk", "tick-rounded", "penny"):
        r = returns(FRAMES[name])
        s = base(name)
        row(name, int(np.sum(r == 0.0)), f"{float(np.mean(r == 0.0)):.4f}",
            int(s.notna().sum()), f"{s.dropna().median():.6f}",
            len(set(s.dropna().to_numpy())))

    head("C3. What the column says about structure it was built to see")
    print("An AR(1) in returns with phi = +0.6 is persistent, phi = -0.6")
    print("alternating, and an iid walk neither. If the break means")
    print("anything, these should not read alike.")
    row("frame", "median", "mean", "histogram")
    for label, frame in (("iid walk", FRAMES["walk"]),
                         ("AR(1) phi +0.6", FRAMES["ar1"]),
                         ("AR(1) phi -0.6", ar1_neg()),
                         ("20-bar cosine returns", FRAMES["cosine"]),
                         ("Student-t(3)", FRAMES["student-t"])):
        a = c22_dfa(frame).dropna().to_numpy()
        hist = {round(v, 6): int(np.sum(a == v)) for v in sorted(set(a))}
        row(label, f"{float(np.median(a)):.6f}", f"{float(a.mean()):.6f}",
            hist)

    head("C4. The iid centre, on independent windows")
    print("400 INDEPENDENT windows of normal returns through the shipped")
    print("kernel, so the reading is not a rolling one.")
    rng = np.random.default_rng(4242)
    for length in (MIN_LENGTH, 100, 250):
        block = rng.normal(0.0, 0.01, (400, length))
        vals = _prop_rows(block)
        a = vals[~np.isnan(vals)]
        hist = {round(v, 6): int(np.sum(a == v)) for v in sorted(set(a))}
        row(f"length {length}", f"median {float(np.median(a)):.6f}",
            f"mean {float(a.mean()):.6f}", f"bounds {prop_bounds(length)}",
            hist)


# ------------------------------------------------------------- Gate D
def section_d():
    head("D1. Exact binary rescales: bit-identical or not")
    row("frame", "x8", "x64", "2**-40", "2**40")
    for name in FRAMES:
        cells = []
        for factor in (8.0, 64.0, 2.0 ** -40, 2.0 ** 40):
            cells.append("bit-equal" if same(base(name),
                                             c22_dfa(FRAMES[name] * factor))
                         else "MOVED")
        row(name, *cells)

    head("D2. Inexact rescales and other price levels")
    row("case", "moved bars", "mask differences", "max |gap|")
    for factor in (10.0, 3.7, 0.1, 1.0000001):
        got = c22_dfa(FRAMES["walk"] * factor)
        moved, mask = diff_bars(base("walk"), got)
        row(f"walk x{factor}", moved, mask,
            f"{worst_gap(base('walk'), got):.3e}")
    for level in (1e-6, 1e6, 1e100):
        f = FRAMES["walk"] / float(FRAMES["walk"].iloc[0]) * level
        got = c22_dfa(f)
        moved, mask = diff_bars(c22_dfa(FRAMES["walk"]), got)
        row(f"walk re-based at {level:.0e}", moved, mask,
            f"{worst_gap(base('walk'), got):.3e}")
    for length in (MIN_LENGTH, 120, 250):
        a = c22_dfa(FRAMES["walk"], length=length)
        b = c22_dfa(FRAMES["walk"] * 8.0, length=length)
        row(f"x8 at length {length}", *diff_bars(a, b), "bit-equal"
            if same(a, b) else "MOVED")

    head("D3. 0 < fires < n, so a constant column cannot pass")
    row("frame", "bars", "fired", "distinct values", "not constant")
    for name in FRAMES:
        s = base(name)
        a = s.dropna().to_numpy()
        row(name, len(s), int(s.notna().sum()), len(set(a)),
            len(set(a)) > 1)

    head("D4. What it is blind to, and what it is not")
    rng = np.random.default_rng(5)
    win, bars = windows(FRAMES["walk"])
    idx = list(range(0, win.shape[0], 7))
    for label, fn in (("the returns x0.5", lambda w: 0.5 * w),
                      ("the returns x2", lambda w: 2.0 * w),
                      ("the returns x10", lambda w: 10.0 * w),
                      ("the returns x-1", lambda w: -1.0 * w),
                      ("+0.001 on every return", lambda w: w + 0.001),
                      ("+1.0 on every return", lambda w: w + 1.0),
                      ("the window REVERSED", lambda w: w[::-1]),
                      ("the window SHUFFLED",
                       lambda w: rng.permutation(w))):
        moved = n = 0
        gap = 0.0
        for i in idx:
            a = shipped_on(win[i])
            b = shipped_on(fn(win[i]))
            if math.isnan(a) or math.isnan(b):
                continue
            n += 1
            moved += int(a != b)
            gap = max(gap, abs(a - b))
        row(label, f"{moved} of {n} windows move", f"max |gap| {gap:.3e}")


# ------------------------------------------------------------- Gate E'ish
def section_e():
    head("E1. Against the fork's own columns, on SYNTHETIC frames")
    print("This is NOT Gate E -- it is 1,500-bar synthetic frames, not 89")
    print("BIST ones, and the comparator set is this fork rather than the")
    print("engine's. It is here because issue #128 names #112 TF-DFA-100 as")
    print("a relative and that port SHIPPED after the 2026-10-24 screen, so")
    print("the screen's fork-overlap stage never saw it.")
    df = pd.DataFrame({"close": FRAMES["walk"],
                       "high": FRAMES["walk"] * 1.01,
                       "low": FRAMES["walk"] * 0.99,
                       "open": FRAMES["walk"].shift(1).bfill(),
                       "volume": 1e6})
    mine = base("walk")
    cols = {}
    for name, fn in (("TFDFA_100", lambda: ta.tf_dfa_100(df["close"])),
                     ("LEANHURST_100", lambda: ta.lean_hurst_100(df["close"])),
                     ("C22AMI2_100", lambda: ta.c22_ami2(df["close"])),
                     ("C22PERIOD_100",
                      lambda: ta.c22_periodicity(df["close"])),
                     ("C22AMITS_100",
                      lambda: ta.c22_ami_timescale(df["close"])),
                     ("TFSPECENT_64",
                      lambda: ta.tf_spec_entropy_64(df["close"])),
                     ("TFAC1E_60", lambda: ta.tf_autocorr_1e_60(df["close"])),
                     ("TSAC1_60", lambda: ta.ts_ac1_60(df["close"]))):
        try:
            got = fn()
        except Exception as exc:                          # noqa: BLE001
            row(name, f"not measured: {exc}")
            continue
        if isinstance(got, pd.DataFrame):
            got = got.iloc[:, 0]
        cols[name] = got
    row("column", "Spearman vs C22DFA_100", "overlapping bars")
    for name, col in sorted(cols.items(),
                            key=lambda kv: -abs(spearman(mine, kv[1]) or 0)):
        m = mine.notna() & col.notna()
        row(name, f"{spearman(mine, col):+.4f}", int(m.sum()))
    row("frames", 1, "bars", len(mine), "comparators", len(cols))

    head("E2. The same, on six frames")
    row("comparator", *[f"rho on {k}" for k in FRAMES])
    for name in sorted(cols):
        cells = []
        for frame in FRAMES:
            c = FRAMES[frame]
            try:
                other = {"TFDFA_100": ta.tf_dfa_100,
                         "LEANHURST_100": ta.lean_hurst_100,
                         "C22AMI2_100": ta.c22_ami2,
                         "C22PERIOD_100": ta.c22_periodicity,
                         "C22AMITS_100": ta.c22_ami_timescale,
                         "TFSPECENT_64": ta.tf_spec_entropy_64,
                         "TFAC1E_60": ta.tf_autocorr_1e_60,
                         "TSAC1_60": ta.ts_ac1_60}[name](c)
            except Exception:                             # noqa: BLE001
                cells.append("-")
                continue
            if isinstance(other, pd.DataFrame):
                other = other.iloc[:, 0]
            cells.append(f"{spearman(base(frame), other):+.4f}")
        row(name, *cells)


# ------------------------------------------------- degenerate frames
def section_g():
    head("G1. Frames with no fluctuation of their own")
    row("frame", "bars", "fired", "what it reads", "why")
    cases = {
        "exact geometric ladder (constant returns)": ladder(),
        "one kurus a bar": kurus_path(),
        "flat from bar 400": pd.Series(
            np.r_[walk(400).to_numpy(), np.full(N - 400, 100.0)]),
        "1-ulp step at 1e6 on bar 700": _ulp_frame(),
        "alternating +-2%": pd.Series(
            100.0 * np.cumprod(1.0 + 0.02 * np.where(
                np.arange(N) % 2 == 0, 1.0, -1.0))),
    }
    for label, frame in cases.items():
        s = c22_dfa(frame)
        a = s.dropna().to_numpy()
        row(label, len(s), int(s.notna().sum()),
            f"{sorted(set(np.round(a, 6)))[:4]}" if len(a) else "-",
            f"sd of returns {float(np.nanstd(returns(frame))):.3e}")

    head("G2. The noise floor, priced: the same frames with it removed")
    print("The `no-floor` mutant keeps the zero-standard-deviation guard")
    print("but drops the 4096-eps band, so what the floor BUYS is the")
    print("difference between these two columns.")
    fn = mutant("no-floor")
    for label, frame in cases.items():
        a = c22_dfa(frame)
        b = fn(frame)
        av = a.dropna().to_numpy()
        bv = b.dropna().to_numpy()
        row(label, f"shipped fires {len(av)}", f"no-floor fires {len(bv)}",
            f"no-floor reads {sorted(set(np.round(bv, 6)))[:5]}"
            if len(bv) else "-")
    head("G2b. ... and on the six price-shaped frames")
    for name in FRAMES:
        row(name, *diff_bars(base(name), fn(FRAMES[name])))

    head("G3. Can the fluctuation be exactly zero at a scale?")
    print("`F(tau) == 0` needs the profile exactly straight inside every box")
    print("of one scale. A window of equal returns reaches it -- and that is")
    print("already blanked by the floor -- so the question is whether")
    print("anything with real variation does. These are constructions aimed")
    print("at it: returns constant inside blocks that the boxes align with.")
    probes = {}
    for block in (5, 10, 25):
        r = np.repeat(np.linspace(0.01, 0.05, N // block + 1), block)[:N]
        probes[f"returns constant in blocks of {block}"] = pd.Series(
            100.0 * np.cumprod(1.0 + r))
    probes["returns 0 then +1% at bar 750"] = pd.Series(
        100.0 * np.cumprod(1.0 + np.where(np.arange(N) < 750, 0.0, 0.01)))
    guard = mutant("no-zero-fluctuation-guard")
    for label, frame in probes.items():
        s = c22_dfa(frame)
        g = guard(frame)
        row(label, f"shipped fires {int(s.notna().sum())}",
            f"without the guard {int(g.notna().sum())}",
            f"shipped reads {sorted(set(np.round(s.dropna().to_numpy(), 6)))[:4]}"
            if int(s.notna().sum()) else "-")
    head("G3c. The window the zero-fluctuation guard actually blanks")
    print("One frame in G3 answers the question with a YES: returns that")
    print("are exactly zero and then exactly +1% have, at ONE bar, a profile")
    print("that is straight inside every box of some scale. This locates it.")
    frame = probes["returns 0 then +1% at bar 750"]
    shipped = c22_dfa(frame)
    unguarded = guard(frame)
    hit = np.where(shipped.isna().to_numpy() & unguarded.notna().to_numpy())[0]
    hit = hit[hit >= LENGTH]
    row("bars the guard blanks and the unguarded column does not", list(hit))
    for bar in hit:
        win = returns(frame)[bar - LENGTH:bar]
        curve = fluctuations(win)
        zeros = [tau for tau, f in curve] if curve is None else \
            [tau for tau, f in curve if not (f > 0.0)]
        row(f"bar {bar}", f"scales with F = 0 exactly: {zeros}",
            f"what the unguarded column reads there:"
            f" {float(np.asarray(unguarded, float)[bar]):.6f}")

    head("G3b. The same question, asked of the kernel directly")
    print("Rows built so that every box of the smallest scale sees an")
    print("exactly straight profile: a window whose decimated returns are")
    print("constant inside blocks of 5 decimated points.")
    rows = []
    for k in range(10):
        r = np.repeat(np.arange(10, dtype=float) * (k + 1) * 1e-3, 10)[:LENGTH]
        rows.append(r)
    block = np.array(rows)
    vals = _prop_rows(block)
    row("rows", block.shape[0], "fired", int(np.sum(~np.isnan(vals))),
        "values", sorted(set(np.round(vals[~np.isnan(vals)], 6))))


# ---------------------------------------------------------- NaN rules
def section_h():
    head("H1. A bad close empties exactly its own windows")
    row("what", "fired", "blank", "first blank", "last blank")
    for label, value in (("NaN", np.nan), ("+inf", np.inf),
                         ("zero", 0.0), ("negative", -5.0),
                         ("subnormal 1e-310", 1e-310)):
        f = FRAMES["walk"].copy()
        f.iloc[700] = value
        s = c22_dfa(f)
        blank = np.where(s.isna().to_numpy())[0]
        blank = blank[blank >= LENGTH]
        row(f"close[700] = {label}", int(s.notna().sum()), len(blank),
            int(blank.min()) if len(blank) else "-",
            int(blank.max()) if len(blank) else "-")

    head("H2. A close PAIR whose ratio overflows, and one whose squares do")
    for label, pair in (("1e-300 then 1e50", (1e-300, 1e50)),
                        ("1.0 then 1e200", (1.0, 1e200)),
                        ("1.0 then 1e77", (1.0, 1e77))):
        f = FRAMES["walk"].copy()
        f.iloc[700], f.iloc[701] = pair
        s = c22_dfa(f)
        guard = np.asarray(mutant("no-overflow-guard")(f), float)
        blank = np.where(s.isna().to_numpy())[0]
        blank = blank[blank >= LENGTH]
        both = np.asarray(mutant("no-either-guard")(f), float)
        on_those = guard[blank]
        on_both = both[blank]
        row(label, f"shipped blanks {len(blank)} bars",
            f"without the isfinite(sd) limb"
            f" {int(np.sum(~np.isnan(on_those)))} of them fire",
            f"without EITHER value guard"
            f" {int(np.sum(~np.isnan(on_both)))} fire, reading"
            f" {sorted(set(np.round(on_both[~np.isnan(on_both)], 6)))}")

    head("H3. The length guard band and the warm-up")
    row("case", "result")
    for n in (LENGTH, LENGTH + 1, MIN_LENGTH, MIN_LENGTH + 1):
        s = c22_dfa(FRAMES["walk"].iloc[:n])
        row(f"{n} closes", "None" if s is None
            else f"{int(s.notna().sum())} fire")
    for length in (2, 50, MIN_LENGTH - 1, MIN_LENGTH, 120):
        s = c22_dfa(FRAMES["walk"], length=length)
        row(f"length={length}", s.name, f"{int(s.notna().sum())} fire")

    head("H4. The house offset and fill")
    s = c22_dfa(FRAMES["walk"], offset=2)
    row("offset=2 shifts by two bars",
        same(s.iloc[2:].to_numpy(), base("walk").iloc[:-2].to_numpy()))
    s = c22_dfa(FRAMES["walk"], fillna=-1)
    row("fillna=-1 fills the warm-up", int(np.sum(s.to_numpy() == -1)))


# --------------------------------------------------------- cost, chunks
def section_t():
    head("T. Cost")
    rng = np.random.default_rng(3)
    for n in (100_000, 400_000):
        close = pd.Series(100.0 * np.exp(np.cumsum(
            rng.normal(0.0, 0.01, n))))
        tracemalloc.start()
        t0 = time.perf_counter()
        out = c22_dfa(close)
        dt = time.perf_counter() - t0
        cur, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        row(f"n = {n}", f"{dt:.2f} s", f"traced peak {peak / 1e6:.1f} MB",
            f"{int(out.notna().sum())} fire")


def section_z():
    head("Z. The chunk budget cannot change a value")
    f = FRAMES["walk"]
    want = base("walk")
    for budget in (LENGTH, 4 * LENGTH, 999, CHUNK_VALUES, 10 ** 9):
        old = MODULE.CHUNK_VALUES
        MODULE.CHUNK_VALUES = budget
        try:
            got = MODULE.c22_dfa(f)
        finally:
            MODULE.CHUNK_VALUES = old
        row(f"budget {budget}", f"rows per chunk {max(1, budget // LENGTH)}",
            "bit-equal" if same(want, got) else "MOVED")


def _ulp_frame(n=N, level=1e6, at=700):
    c = np.full(n, level)
    c[at:] = np.nextafter(level, 2 * level)
    return pd.Series(c)


SECTIONS = {"S": section_s, "A": section_a, "B": section_b, "C": section_c,
            "D": section_d, "E": section_e, "G": section_g, "H": section_h,
            "P": section_p, "Q": section_q, "Q2": section_q2,
            "Q3": section_q3, "Q4": section_q4, "Q5": section_q5,
            "Q6": section_q6, "Q7": section_q7, "R": section_r,
            "T": section_t, "Z": section_z}
DEFAULT = ["S", "A", "B", "C", "D", "E", "G", "H", "T", "Z"]


if __name__ == "__main__":
    want = [a.upper() for a in sys.argv[1:]] or DEFAULT
    for key in want:
        if key not in SECTIONS:
            raise SystemExit(f"unknown section {key!r};"
                             f" pick from {list(SECTIONS)}")
        SECTIONS[key]()
