# -*- coding: utf-8 -*-
"""TS-MEDSKEW-20 (PandasTa issue #98): every number in
`docs/TsMedskew20Measured.md` is printed by this script.

    python docs/measure_ts_medskew_20.py            # all sections
    python docs/measure_ts_medskew_20.py A C D      # selected sections

Sections: A (the source and the readings), B (the mutant sweep),
C (reachability), D (scale), G (the guards), O (what the column overlaps),
Z (cost). Gate E is run by the launcher, not here.

Nothing in this file is imported by shipped code. The oracles are
deliberately slow: a window-by-window Python loop, a `math.fsum` loop and an
EXACT `fractions.Fraction` oracle, none of which share code with the module.
"""
import importlib
import math
import sys
import time
import tracemalloc
from fractions import Fraction

import numpy as np
import pandas as pd
from numpy.lib.stride_tricks import sliding_window_view
from pandas import Series

from pandas_ta.statistics.ts_above_mean_20 import ts_above_mean_20
from pandas_ta.statistics.osap_retskew_21 import osap_retskew_21
from pandas_ta.statistics.ts_medskew_20 import NOISE_FACTOR, ts_medskew_20

LENGTH = 20
_REAL = importlib.import_module("pandas_ta.statistics.ts_medskew_20")


# ------------------------------------------------------------------ frames


def _walk(n=1500, seed=11, sigma=0.015, drift=0.0):
    rng = np.random.default_rng(seed)
    return Series(100.0 * np.exp(np.cumsum(rng.normal(drift, sigma, n))))


def _tick_rounded(n=1500, seed=11):
    return Series(np.round(_walk(n, seed).to_numpy(), 2))


def _from_returns(r):
    return Series(100.0 * np.cumprod(1.0 + np.asarray(r, dtype=float)))


def _window_frame(rs):
    """`len(rs) + 1` closes whose returns are `rs`."""
    body = np.cumprod(1.0 + np.asarray(rs, dtype=float))
    return Series(100.0 * np.concatenate([[1.0], body]))


def _ar1(n=1500, seed=7, sigma=0.015, phi=0.5):
    rng = np.random.default_rng(seed)
    e = rng.normal(0.0, sigma, n)
    x = np.zeros(n)
    for t in range(1, n):
        x[t] = phi * x[t - 1] + e[t]
    return _from_returns(np.clip(x, -0.5, 0.5))


def _heavy_tailed(n=1500, seed=3, df=2.0, sigma=0.01):
    rng = np.random.default_rng(seed)
    return _from_returns(np.clip(sigma * rng.standard_t(df, n), -0.5, 0.5))


def _right_skewed(n=1500, seed=5, sigma=0.01):
    rng = np.random.default_rng(seed)
    return _from_returns(np.clip(sigma * (rng.standard_exponential(n) - 1.0),
                                 -0.5, 0.5))


def _left_skewed(n=1500, seed=5, sigma=0.01):
    rng = np.random.default_rng(seed)
    return _from_returns(np.clip(sigma * (1.0 - rng.standard_exponential(n)),
                                 -0.5, 0.5))


def _two_point(n=1500, seed=4, sigma=0.01):
    rng = np.random.default_rng(seed)
    return _from_returns(np.where(rng.random(n) < 0.5, sigma, -sigma))


def _trending(n=1500, seed=9):
    return _walk(n, seed, sigma=0.004, drift=0.01)


def _flat(n=300, price=100.0):
    return Series(np.full(n, price))


def _ladder(n=300, price=100.0, rate=0.01):
    """A mathematically CONSTANT return, which float64 reproduces only to
    rounding."""
    return Series(price * (1.0 + rate) ** np.arange(n, dtype=float))


def _floored_patches(n=1500, seed=23, sigma=0.015, patch=25, every=40,
                     rate=0.01):
    """A walk interrupted every `every` bars by a `patch`-bar stretch of
    CONSTANT `rate` returns, so the floor is active on INTERIOR windows and
    the window it rejects still has a FINITE value -- which an EXACTLY zero
    patch does not (there the sd is 0 and the backstop empties the window
    whatever the floor says, so a mutation of the floor's index moves
    nothing)."""
    rng = np.random.default_rng(seed)
    r = rng.normal(0.0, sigma, n)
    for start in range(60, n - patch, every):
        r[start:start + patch] = rate
    return _from_returns(r)


def _zero_patches(n=1500, seed=23, sigma=0.015, patch=25, every=40):
    """The same shape with EXACTLY zero returns -- where the sd is 0 and the
    backstop, not the floor, is what empties the window."""
    return _floored_patches(n, seed, sigma, patch, every, rate=0.0)


FRAMES = {
    "walk": _walk,
    "tick-rounded": _tick_rounded,
    "ar1+": lambda: _ar1(phi=0.5),
    "ar1-": lambda: _ar1(phi=-0.5, seed=17),
    "heavy-tailed": _heavy_tailed,
    "right-skewed": _right_skewed,
    "left-skewed": _left_skewed,
    "two-point": _two_point,
    "trending": _trending,
}
FIRED = 1500 - LENGTH


# ----------------------------------------------------------------- helpers


def _returns_of(close):
    return (close / close.shift(1) - 1.0).to_numpy()


def _spearman(a, b):
    m = a.notna() & b.notna()
    return float(a[m].corr(b[m], method="spearman"))


def _agree(a, b):
    """(masks equal, bit-equal count, shared count, max |difference|)."""
    masks = bool((a.isna() == b.isna()).all())
    m = a.notna() & b.notna()
    if not int(m.sum()):
        return masks, 0, 0, float("nan")
    d = (a[m] - b[m]).abs()
    return masks, int((a[m] == b[m]).sum()), int(m.sum()), float(d.max())


def _shared(a, b):
    m = a.notna() & b.notna()
    if not int(m.sum()):
        return 0, 0, float("nan")
    d = (a[m] - b[m]).abs()
    return int((a[m] == b[m]).sum()), int(m.sum()), float(d.max())


def _p(label, *rest):
    print(f"  {label:<58}", *rest)


# ----------------------------------------------------------------- oracles


def _source_windowed(close, length=LENGTH):
    """The issue's formula applied one window at a time. Shares no code with
    the module: a Python loop, `np.mean`, `np.median` and `np.std(ddof=1)`."""
    r = _returns_of(close)
    out = np.full(r.size, np.nan)
    for t in range(length - 1, r.size):
        x = r[t - length + 1:t + 1]
        if not np.isfinite(x).all():
            continue
        s = np.std(x, ddof=1)
        if s == 0.0:
            continue
        out[t] = (np.mean(x) - np.median(x)) / s
    return Series(out, index=close.index)


def _fsum_windowed(close, length=LENGTH):
    """The same statistic in scalar Python, with `math.fsum` for both sums
    and `statistics.median`'s rule (the mean of the two central values) spelt
    out on a sorted copy."""
    r = [float(v) for v in _returns_of(close)]
    out = np.full(len(r), np.nan)
    for t in range(length - 1, len(r)):
        x = r[t - length + 1:t + 1]
        if not all(math.isfinite(v) for v in x):
            continue
        m = math.fsum(x) / length
        s = math.sqrt(math.fsum((v - m) ** 2 for v in x) / (length - 1))
        if s == 0.0:
            continue
        y = sorted(x)
        med = (y[length // 2] if length % 2
               else 0.5 * (y[length // 2 - 1] + y[length // 2]))
        out[t] = (m - med) / s
    return Series(out, index=close.index)


def _exact_windowed(close, length=LENGTH):
    """Every float return is a rational, so the mean, the median and the
    VARIANCE are rationals computed with no rounding at all. Only the final
    square root and the division are float, and both are correctly rounded,
    so this is the true value of the window's own returns to within one ulp
    of each."""
    r = [float(v) for v in _returns_of(close)]
    out = np.full(len(r), np.nan)
    for t in range(length - 1, len(r)):
        x = r[t - length + 1:t + 1]
        if not all(math.isfinite(v) for v in x):
            continue
        q = [Fraction(v) for v in x]
        m = sum(q) / length
        var = sum((v - m) ** 2 for v in q) / (length - 1)
        if var == 0:
            continue
        y = sorted(q)
        med = (y[length // 2] if length % 2
               else (y[length // 2 - 1] + y[length // 2]) / 2)
        num = m - med
        # float(num) / sqrt(float(var)) would round twice over; this rounds
        # the ratio of two exact rationals once, through the square root.
        out[t] = float(num) / math.sqrt(float(var))
    return Series(out, index=close.index)


def _prototype(close, length=LENGTH):
    """`docs/issues/screen/ind_screen.py`, candidate `ts_medskew_20`,
    retyped:

        r = ret(c)
        sdiv(mean(r, 20) - r.rolling(20).median(), std(r, 20))

    with `mean`/`std` = `rolling.mean()`/`rolling.std()` (ddof=1, ONLINE
    accumulators) and `sdiv = _fin(a / b)`, which masks non-finite values.
    No guards of any kind."""
    r = close / close.shift(1) - 1.0
    num = r.rolling(length).mean() - r.rolling(length).median()
    den = r.rolling(length).std()
    with np.errstate(invalid="ignore", divide="ignore"):
        out = num / den
    return out.where(np.isfinite(out))


def _unguarded(close, length=LENGTH):
    """This module without its floor and without its backstop."""
    r = _returns_of(close)
    W = sliding_window_view(r, length)
    mean = W.sum(axis=1) / length
    sd = np.sqrt(((W - mean[:, None]) ** 2).sum(axis=1) / (length - 1))
    med = np.median(W, axis=1)
    out = np.full(r.size, np.nan)
    with np.errstate(invalid="ignore", divide="ignore"):
        out[length - 1:] = (mean - med) / sd
    return Series(out, index=close.index)


def _absolute_floor(close, length=LENGTH):
    """The floor the sibling tsfresh ports use -- `4096 eps` ABSOLUTE on the
    window's return range -- instead of this module's relative one."""
    r = _returns_of(close)
    W = sliding_window_view(r, length)
    mean = W.sum(axis=1) / length
    sd = np.sqrt(((W - mean[:, None]) ** 2).sum(axis=1) / (length - 1))
    med = np.median(W, axis=1)
    out = np.full(r.size, np.nan)
    with np.errstate(invalid="ignore", divide="ignore"):
        out[length - 1:] = np.where(W.max(axis=1) - W.min(axis=1)
                                    > NOISE_FACTOR, (mean - med) / sd, np.nan)
    return Series(out, index=close.index)


def _matrix_variant(close, length=LENGTH):
    """The module with its deviation loop written as one `(rows, length)`
    expression -- the spelling the comment in the module rejects on cost."""
    r = _returns_of(close)
    sq = r * r
    r = np.where(sq < np.finfo(float).max / (8 * length), r, np.nan)
    W = sliding_window_view(r, length)
    mean = W.sum(axis=1) / length
    sd = np.sqrt(((W - mean[:, None]) ** 2).sum(axis=1) / (length - 1))
    med = Series(r, index=close.index).rolling(
        length, min_periods=length).median().to_numpy()[length - 1:]
    hi, lo = W.max(axis=1), W.min(axis=1)
    rep = (hi - lo) > NOISE_FACTOR * np.maximum(hi, -lo)
    with np.errstate(invalid="ignore", divide="ignore"):
        v = (mean - med) / sd
    out = np.full(r.size, np.nan)
    out[length - 1:] = np.where(rep & np.isfinite(v), v, np.nan)
    return Series(out, index=close.index)


def _np_median_variant(close, length=LENGTH):
    """The module with `np.median(windows, axis=1)` instead of pandas'
    rolling skip list -- the other spelling of the same median."""
    r = _returns_of(close)
    sq = r * r
    r = np.where(sq < np.finfo(float).max / (8 * length), r, np.nan)
    W = sliding_window_view(r, length)
    mean = W.sum(axis=1) / length
    ssd = np.zeros(W.shape[0])
    for j in range(length):
        d = W[:, j] - mean
        ssd += d * d
    sd = np.sqrt(ssd / (length - 1))
    med = np.median(W, axis=1)
    hi, lo = W.max(axis=1), W.min(axis=1)
    rep = (hi - lo) > NOISE_FACTOR * np.maximum(hi, -lo)
    with np.errstate(invalid="ignore", divide="ignore"):
        v = (mean - med) / sd
    out = np.full(r.size, np.nan)
    out[length - 1:] = np.where(rep & np.isfinite(v), v, np.nan)
    return Series(out, index=close.index)


# ---------------------------------------------------------------- readings


def _log_return_variant(close, length=LENGTH):
    r = np.log(close.to_numpy()) - np.log(close.shift(1).to_numpy())
    W = sliding_window_view(r, length)
    mean = W.sum(axis=1) / length
    sd = np.sqrt(((W - mean[:, None]) ** 2).sum(axis=1) / (length - 1))
    out = np.full(r.size, np.nan)
    with np.errstate(invalid="ignore", divide="ignore"):
        out[length - 1:] = (mean - np.median(W, axis=1)) / sd
    return Series(out, index=close.index)


def _ddof0_variant(close, length=LENGTH):
    r = _returns_of(close)
    W = sliding_window_view(r, length)
    mean = W.sum(axis=1) / length
    sd = np.sqrt(((W - mean[:, None]) ** 2).sum(axis=1) / length)
    out = np.full(r.size, np.nan)
    with np.errstate(invalid="ignore", divide="ignore"):
        out[length - 1:] = (mean - np.median(W, axis=1)) / sd
    return Series(out, index=close.index)


def _abs_numerator_variant(close, length=LENGTH):
    """The numerator made ABSOLUTE, as the named tsfresh function has it,
    but still over the standard deviation -- i.e. only the sign thrown
    away, with the denominator left alone. This is the reading the issue's
    line leaves open; `_range_variant` below changes the denominator too."""
    return ts_medskew_20(close, length=length).abs()


def _on_closes_variant(close, length=LENGTH):
    """The statistic of the `length` CLOSES rather than of the returns."""
    c = close.to_numpy(dtype=float)
    W = sliding_window_view(c, length)
    mean = W.sum(axis=1) / length
    sd = np.sqrt(((W - mean[:, None]) ** 2).sum(axis=1) / (length - 1))
    out = np.full(c.size, np.nan)
    with np.errstate(invalid="ignore", divide="ignore"):
        out[length - 1:] = (mean - np.median(W, axis=1)) / sd
    return Series(out, index=close.index)


def _nineteen_returns_variant(close, length=LENGTH):
    """`length` CLOSES, so `length - 1` returns -- the off-by-one."""
    return ts_medskew_20(close, length=length - 1)


def _range_variant(close, length=LENGTH):
    """tsfresh's LITERAL `symmetry_looking` quantity: `|mean - median|`
    divided by `max - min` rather than by the standard deviation. The issue
    asks for the continuous `(mean - median)/std` form; this is what the
    named source function compares against `r * (max - min)`."""
    r = _returns_of(close)
    W = sliding_window_view(r, length)
    mean = W.sum(axis=1) / length
    out = np.full(r.size, np.nan)
    with np.errstate(invalid="ignore", divide="ignore"):
        out[length - 1:] = (np.abs(mean - np.median(W, axis=1))
                            / (W.max(axis=1) - W.min(axis=1)))
    return Series(out, index=close.index)


# ------------------------------------------------------------------ Gate A


def section_A():
    print("\n=== Gate A: the source ===")
    print("\nA1 module vs the source applied window by window "
          "(masks, bit-equal/shared, max |diff|)")
    for name in sorted(FRAMES):
        close = FRAMES[name]()
        _p(name, _agree(ts_medskew_20(close), _source_windowed(close)))

    print("\nA2 module vs a math.fsum scalar loop")
    for name in ["walk", "heavy-tailed", "right-skewed"]:
        close = FRAMES[name]()
        _p(name, _agree(ts_medskew_20(close), _fsum_windowed(close)))

    print("\nA3 module vs an EXACT rational oracle "
          "(mean, median and variance exact)")
    for name in ["walk", "tick-rounded", "two-point", "right-skewed"]:
        close = FRAMES[name]()
        a, b = ts_medskew_20(close), _exact_windowed(close)
        masks, eq, shared, mx = _agree(a, b)
        m = a.notna() & b.notna()
        rel = float(((a[m] - b[m]).abs()
                     / b[m].abs().clip(lower=1e-300)).max())
        _p(name, (masks, eq, shared, mx, f"max rel {rel:.3e}"))

    print("\nA3b the exact oracle on a mean-dominated path "
          "(|mean|/sd = 1e5, worst cancellation)")
    rng = np.random.default_rng(99)
    close = _from_returns(0.5 + 0.5e-5 * rng.standard_normal(600))
    a, b = ts_medskew_20(close), _exact_windowed(close)
    masks, eq, shared, mx = _agree(a, b)
    m = a.notna() & b.notna()
    rel = float(((a[m] - b[m]).abs() / b[m].abs().clip(lower=1e-300)).max())
    _p("mean-dominated", (masks, eq, shared, mx, f"max rel {rel:.3e}"))

    print("\nA4 hand-derived windows")
    print("  one return of `a` among `n - 1` equal ones is 1/sqrt(n) for "
          "ANY a and n (mean a/n, median 0, sd a/sqrt(n)):")
    for n in (3, 4, 20, 60):
        for a in (0.5, 0.001, -0.5):
            got = float(ts_medskew_20(_window_frame([0.0] * (n - 1) + [a]),
                                      length=n).iloc[-1])
            want = math.copysign(1.0 / math.sqrt(n), a)
            _p(f"n={n}, a={a:+}", f"{got:+.15f}", f"expected {want:+.15f}",
               f"|diff| {abs(got - want):.2e}")
    print("  windows whose mean and median agree read ~0:")
    for rs in ([0.01, -0.01] * 10, [0.0] * 10 + [0.01] * 10,
               [0.001 * k for k in range(1, 21)]):
        got = float(ts_medskew_20(_window_frame(rs)).iloc[-1])
        _p(f"{rs[:3]}... n={len(rs)}", f"{got:+.3e}")

    print("\nA5 the readings the wording leaves open (Spearman, max |diff|)")
    walk = _walk()
    base = ts_medskew_20(walk)
    for label, variant in [
        ("log returns", _log_return_variant(walk)),
        ("ddof=0 (population sd)", _ddof0_variant(walk)),
        ("|mean-median|/sd, the sign thrown away",
         _abs_numerator_variant(walk)),
        ("20 closes, i.e. 19 returns", _nineteen_returns_variant(walk)),
        ("the statistic OF the 20 closes", _on_closes_variant(walk)),
        ("|mean-median|/(max-min), tsfresh's literal form",
         _range_variant(walk)),
        ("Pearson 2 (x3)", base * 3.0),
    ]:
        eq, shared, mx = _shared(base, variant)
        _p(label, f"rho {_spearman(base, variant):.6f}",
           f"bit-equal {eq}/{shared}", f"max |diff| {mx:.4f}")

    print("\nA5b the ddof=0 rescaling is EXACT in rank, and the ratio is "
          "constant")
    v = _ddof0_variant(walk)
    m = base.notna() & v.notna()
    ratio = (v[m] / base[m])
    _p("ratio v/base", f"min {float(ratio.min()):.12f}",
       f"max {float(ratio.max()):.12f}",
       f"sqrt(20/19) {math.sqrt(LENGTH / (LENGTH - 1)):.12f}")

    print("\nA6 the range: |value| <= sqrt((n-1)/n) = "
          f"{math.sqrt((LENGTH - 1) / LENGTH):.6f}")
    for name in sorted(FRAMES):
        col = ts_medskew_20(FRAMES[name]())
        _p(name, f"min {float(col.min()):+.6f}", f"max {float(col.max()):+.6f}",
           f"max |v| {float(col.abs().max()):.6f}")
    print("  constructed extremes:")
    for k in range(1, LENGTH):
        rs = [0.0] * k + [0.01] * (LENGTH - k)
        got = float(ts_medskew_20(_window_frame(rs)).iloc[-1])
        if k in (10, 11, 12, 13):
            _p(f"{k} zeros + {LENGTH - k} gains", f"{got:+.6f}")
    best, best_k = 0.0, None
    for k in range(1, LENGTH):
        rs = [0.0] * k + [0.01] * (LENGTH - k)
        got = abs(float(ts_medskew_20(_window_frame(rs)).iloc[-1]))
        if got > best:
            best, best_k = got, k
    _p("largest two-point |value| over k", f"{best:.6f}", f"at k={best_k}")
    print("  search for the sample maximum, 200,000 windows per family:")
    rng = np.random.default_rng(5)
    families = {
        "gaussian": lambda k: rng.standard_normal((k, LENGTH)),
        "exponential": lambda k: rng.standard_exponential((k, LENGTH)),
        "lognormal": lambda k: rng.lognormal(0.0, 2.0, (k, LENGTH)),
        "student-t(1)": lambda k: rng.standard_t(1.0, (k, LENGTH)),
        "two-point, random split": lambda k: (
            rng.random((k, LENGTH)) < rng.random((k, 1))).astype(float),
        "sorted uniform, random levels": lambda k: np.sort(
            rng.random((k, LENGTH)) ** rng.integers(1, 9, (k, 1)), axis=1),
    }
    for label, draw in families.items():
        X = draw(200000)
        s = X.std(axis=1, ddof=1)
        v = np.where(s > 0, (X.mean(axis=1) - np.median(X, axis=1))
                     / np.where(s > 0, s, 1.0), 0.0)
        _p(label, f"max |value| {float(np.abs(v).max()):.6f}")
    print("  and the parametric family `k` equal lows + `n - k` equal highs:")
    best = max(((abs((20 - k) / 20.0
                     / math.sqrt((k * (20 - k) ** 2 + (20 - k) * k ** 2)
                                 / 400.0 / 19.0)), k)
                for k in range(11, 20)))
    _p("largest over k", f"{best[0]:.6f}", f"at k={best[1]}")

    print("\nA7 module vs the screen prototype")
    for name in sorted(FRAMES):
        close = FRAMES[name]()
        a, b = ts_medskew_20(close), _prototype(close)
        _p(name, (_shared(a, b), f"rho {_spearman(a, b):.6f}",
                  f"proto fires {int(b.notna().sum())}",
                  f"module fires {int(a.notna().sum())}"))
    print("  where the two masks differ, on the walk:")
    close = _walk()
    a, b = ts_medskew_20(close), _prototype(close)
    only_proto = np.flatnonzero((a.isna() & b.notna()).to_numpy())
    only_mod = np.flatnonzero((b.isna() & a.notna()).to_numpy())
    _p("bars only the prototype reports", only_proto.tolist()[:10],
       f"n={only_proto.size}")
    _p("bars only the module reports", only_mod.tolist()[:10],
       f"n={only_mod.size}")
    print("  the prototype on a flat frame and on a constant-return ladder:")
    for label, frame in [("flat", _flat()), ("ladder", _ladder())]:
        _p(label, f"proto fires {int(_prototype(frame).notna().sum())}",
           f"module fires {int(ts_medskew_20(frame).notna().sum())}",
           f"unguarded fires {int(_unguarded(frame).notna().sum())}")
    print("  the prototype through a bad close (NaN at bar 200 of 1,500):")
    bad = _walk().copy()
    bad.iloc[200] = np.nan
    _p("prototype fires", int(_prototype(bad).notna().sum()),
       "module fires", int(ts_medskew_20(bad).notna().sum()))


# ------------------------------------------------------------------ Gate B


BACK_DATE_TWO = (
    "    out[length - 1:] = np.where(reported, value, np.nan)",
    "    out[length - 3:c.size - 2] = np.where(reported, value, np.nan)")
BACK_DATE_FULL = (
    "    out[length - 1:] = np.where(reported, value, np.nan)",
    "    out[:windows.shape[0]] = np.where(reported, value, np.nan)")
FORWARD_WINDOW = (
    "    windows = sliding_window_view(r, length)",
    "    windows = sliding_window_view(np.roll(r, -1), length)")
FORWARD_RETURN = (
    "        r = (px / px.shift(1) - 1.0).to_numpy()",
    "        r = (px.shift(-1) / px - 1.0).to_numpy()")
FUTURE_MEDIAN = (
    "        .rolling(length, min_periods=length).median().to_numpy()[length - 1:]",
    "        .rolling(length, min_periods=length).median()"
    ".to_numpy()[length - 1:]\n    median = np.roll(median, -1)")
SHIFTED_FLOOR = (
    "    hi, lo = windows.max(axis=1), windows.min(axis=1)",
    "    hi, lo = (np.roll(windows.max(axis=1), -1),\n"
    "              np.roll(windows.min(axis=1), -1))")

MUTANTS = {
    "back_date_two": BACK_DATE_TWO,
    "back_date_full": BACK_DATE_FULL,
    "forward_window": FORWARD_WINDOW,
    "forward_return": FORWARD_RETURN,
    "future_median": FUTURE_MEDIAN,
}
OFFSETS = range(40, 1500, 40)


def _load_mutant(old, new):
    import types
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_ts_medskew_20_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


def _caught(fn, close, other, **kwargs):
    base = fn(close, **kwargs)
    hits = []
    for j in OFFSETS:
        p = close.copy()
        p.iloc[j:] = other.iloc[j:].values
        out = fn(p, **kwargs)
        a, b = base.iloc[:j], out.iloc[:j]
        if not (a.isna() == b.isna()).all():
            hits.append(j)
            continue
        m = a.notna()
        if (a[m] != b[m]).any():
            hits.append(j)
    return hits


def section_B():
    print("\n=== Gate B: causality ===")
    pairs = {
        "walk": (_walk(), _walk(seed=97)),
        "tick-rounded": (_tick_rounded(), _tick_rounded(seed=56)),
        "heavy-tailed": (_heavy_tailed(), _heavy_tailed(seed=8)),
    }
    print(f"\nB1 the real module under the blind sweep "
          f"({len(list(OFFSETS))} offsets)")
    for name, (close, other) in sorted(pairs.items()):
        _p(name, f"caught {len(_caught(ts_medskew_20, close, other))}")
    for length in [5, 60, 250]:
        close, other = pairs["walk"]
        _p(f"walk, length={length}",
           f"caught {len(_caught(ts_medskew_20, close, other, length=length))}",
           "first fired bar",
           int(ts_medskew_20(close, length=length).notna()
               .to_numpy().argmax()))

    print("\nB2 each mutant: live? and how many offsets catch it")
    for mutant in sorted(MUTANTS):
        mod = _load_mutant(*MUTANTS[mutant])
        for name, (close, other) in sorted(pairs.items()):
            live = not mod.ts_medskew_20(close).equals(ts_medskew_20(close))
            _p(f"{mutant} / {name}", f"live {live}",
               f"caught {len(_caught(mod.ts_medskew_20, close, other))}")

    print("\nB3 the floor-index mutant: live, but what does it move?")
    mod = _load_mutant(*SHIFTED_FLOOR)
    for name, (close, other) in sorted(pairs.items()):
        real, mut = ts_medskew_20(close), mod.ts_medskew_20(close)
        moved = np.flatnonzero(
            (real.isna() != mut.isna()).to_numpy()
            | (real.fillna(-99.0) != mut.fillna(-99.0)).to_numpy())
        _p(f"{name}", f"live {not mut.equals(real)}",
           f"moved bars {moved.tolist()}",
           f"caught {len(_caught(mod.ts_medskew_20, close, other))}")
    print("\nB4 the designed probe for that mutant")
    for label, make in [("constant-rate patches", _floored_patches),
                        ("exactly-zero patches", _zero_patches)]:
        close, other = make(), make(seed=24)
        col = ts_medskew_20(close)
        interior = int(col.iloc[LENGTH:].isna().sum())
        un = _unguarded(close)
        finite = int(un.iloc[LENGTH:][col.iloc[LENGTH:].isna()].notna().sum())
        _p(f"{label}: interior bars emptied", interior,
           f"of which the unguarded spelling reports a finite value on {finite}")
        _p(f"{label}: real module caught",
           len(_caught(ts_medskew_20, close, other)))
        _p(f"{label}: floor mutant caught",
           len(_caught(mod.ts_medskew_20, close, other)))


# ------------------------------------------------------------- Gates C / D


def section_C():
    print("\n=== Gate C: reachability (SYNTHETIC; real data comes from "
          "Gate E's run) ===")
    for name in sorted(FRAMES):
        col = ts_medskew_20(FRAMES[name]())
        v = col.dropna()
        _p(name, f"fires {int(col.notna().sum())}/{len(col)}",
           f"non-zero {int((v != 0).sum())}",
           f"distinct {int(v.nunique())}",
           f"[{float(v.min()):+.4f}, {float(v.max()):+.4f}]")
    for label, frame in [("flat", _flat()), ("ladder", _ladder())]:
        col = ts_medskew_20(frame)
        _p(label, f"fires {int(col.notna().sum())}/{len(col)}")
    print("\nC2 where an exact 0.0 comes from")
    col = ts_medskew_20(_window_frame([0.01, -0.01] * 10))
    _p("a symmetric hand window", f"{float(col.iloc[-1]):.3e}")
    walk = ts_medskew_20(_walk()).dropna()
    _p("exact zeros on the walk", int((walk == 0.0).sum()), f"of {walk.size}")
    tp = ts_medskew_20(_two_point()).dropna()
    _p("exact zeros on the two-point frame", int((tp == 0.0).sum()),
       f"of {tp.size}", "bars",
       np.flatnonzero((tp == 0.0).to_numpy()).tolist()[:5])


def section_D():
    print("\n=== Gate D: scale ===")
    print("\nD1 x8 / x64 (bit-identical expected)")
    for name in sorted(FRAMES):
        close = FRAMES[name]()
        base = ts_medskew_20(close)
        for k in (8.0, 64.0):
            masks, eq, shared, mx = _agree(base, ts_medskew_20(close * k))
            if not (masks and eq == shared):
                _p(f"{name} x{k:g}", "NOT bit-identical", (masks, eq, shared, mx))
        _p(name, f"bit-identical x8 and x64 on {int(base.notna().sum())} bars")
    print("\nD1b x8 at other lengths, on the walk")
    close = _walk()
    for length in (3, 5, 60, 250):
        base = ts_medskew_20(close, length=length)
        masks, eq, shared, mx = _agree(base, ts_medskew_20(close * 8.0,
                                                           length=length))
        _p(f"length={length}", (masks, eq, shared, mx))
    print("\nD2 x10 / x3.7 / x0.1 (NOT bit-identical by construction)")
    for name in sorted(FRAMES):
        close = FRAMES[name]()
        base = ts_medskew_20(close)
        for k in (10.0, 3.7, 0.1):
            masks, eq, shared, mx = _agree(base, ts_medskew_20(close * k))
            _p(f"{name} x{k:g}", f"masks {masks}", f"bit-equal {eq}/{shared}",
               f"max |diff| {mx:.3e}",
               f"rho {_spearman(base, ts_medskew_20(close * k)):.6f}")
    print("\nD3 an affine map of the RETURNS (the statistic's own "
          "invariance)")
    rng = np.random.default_rng(11)
    r = rng.normal(0.0, 0.015, 1500)
    base = ts_medskew_20(_from_returns(r))
    for label, rr in [("r x 2", 2 * r), ("r x 0.5", 0.5 * r),
                      ("r + 0.004", r + 0.004)]:
        col = ts_medskew_20(_from_returns(rr))
        masks, eq, shared, mx = _agree(base, col)
        _p(label, f"masks {masks}", f"bit-equal {eq}/{shared}",
           f"max |diff| {mx:.3e}", f"rho {_spearman(base, col):.6f}")
    print("\nD4 the floor is scale-invariant but NOT shift-invariant "
          "(spreads measured on the returns the module actually sees)")
    rng = np.random.default_rng(3)
    # The intended noise is far below what a close pair can represent, so
    # what the module sees is the closes' OWN rounding, about 1e-16 -- above
    # the floor at returns of 1e-6 and below it at returns of 0.004.
    tiny = 1e-6 + 1e-21 * rng.standard_normal(600)
    for label, rr in [("returns ~1e-6", tiny), ("the same + 0.004",
                                                tiny + 0.004)]:
        close = _from_returns(rr)
        col = ts_medskew_20(close)
        r = _returns_of(close)[1:]
        W = sliding_window_view(r, LENGTH)
        spread = float(np.median(W.max(axis=1) - W.min(axis=1)))
        amax = float(np.median(np.abs(W).max(axis=1)))
        _p(label, f"fires {int(col.notna().sum())}/{len(col)}",
           f"median spread {spread:.3e}", f"floor {NOISE_FACTOR * amax:.3e}")


# ------------------------------------------------------------------ guards


def section_G():
    print("\n=== Guards ===")
    print("\nG1 what the floor costs on a clean frame "
          "(module vs the unguarded spelling)")
    for name in sorted(FRAMES):
        close = FRAMES[name]()
        a, b = ts_medskew_20(close), _unguarded(close)
        body = int((a.isna() & b.notna()).iloc[LENGTH:].sum())
        _p(name, f"module {int(a.notna().sum())}",
           f"unguarded {int(b.notna().sum())}", f"body bars lost {body}")
    print("\nG2 the ladder: a mathematically constant return")
    lad = _ladder()
    u = _unguarded(lad).dropna()
    _p("module fires", int(ts_medskew_20(lad).notna().sum()))
    _p("unguarded fires", int(u.size), f"distinct {int(u.nunique())}",
       f"range [{float(u.min()):+.4f}, {float(u.max()):+.4f}]")
    print("\nG3 relative vs absolute floor on a quiet-but-honest frame")
    rng = np.random.default_rng(3)
    quiet = _from_returns(1e-6 + 1e-13 * rng.standard_normal(600))
    _p("returns 1e-6 spread 1e-13: module",
       int(ts_medskew_20(quiet).notna().sum()),
       "absolute floor", int(_absolute_floor(quiet).notna().sum()))
    a, b = ts_medskew_20(quiet), _exact_windowed(quiet)
    _p("  module vs the exact oracle there", _agree(a, b))
    # What makes this frame HONEST rather than rounding, in the same terms
    # D4 uses: the spread the module actually sees against the spread the
    # closes' own rounding produces at this return level (D4's 4.441e-16).
    W = sliding_window_view(_returns_of(quiet)[1:], LENGTH)
    spread = float(np.median(W.max(axis=1) - W.min(axis=1)))
    amax = float(np.median(np.abs(W).max(axis=1)))
    _p("  returns 1e-6: median window spread", f"{spread:.3e}",
       f"relative floor {NOISE_FACTOR * amax:.3e}",
       f"absolute floor {NOISE_FACTOR:.3e}",
       f"spread / D4's rounding spread {spread / 4.441e-16:.3e}")
    loud = _from_returns(0.5 + 1e-14 * rng.standard_normal(600))
    _p("returns 0.5 spread 1e-14: module",
       int(ts_medskew_20(loud).notna().sum()),
       "absolute floor", int(_absolute_floor(loud).notna().sum()))
    W = sliding_window_view(_returns_of(loud)[1:], LENGTH)
    spread = float(np.median(W.max(axis=1) - W.min(axis=1)))
    amax = float(np.median(np.abs(W).max(axis=1)))
    _p("  returns 0.5: median window spread", f"{spread:.3e}",
       f"relative floor {NOISE_FACTOR * amax:.3e}",
       f"absolute floor {NOISE_FACTOR:.3e}")
    print("\nG4 the `isfinite` backstop: is there an input that reaches it?")
    print("  a) returns so small that a squared deviation would underflow "
          "cannot be built from closes at all --")
    for mag in (1e-100, 1e-150, 1e-180):
        rng = np.random.default_rng(13)
        rr = mag * (1.0 + 0.5 * rng.standard_normal(300))
        close = _from_returns(rr)
        r = _returns_of(close)[1:]
        _p(f"intended returns ~{mag:.0e}",
           f"returns the module sees: max |r| {np.abs(r).max():.3e}",
           f"distinct {len(set(r.tolist()))}",
           f"module fires {int(ts_medskew_20(close).notna().sum())}")
    up = float(np.nextafter(1.0, 2.0) - 1.0)
    down = float(np.nextafter(1.0, 0.0) - 1.0)
    rmin = min(abs(up), abs(down))
    _p("the smallest non-zero return a close pair can produce",
       f"up {up:.3e}", f"down {down:.3e}", f"smaller magnitude {rmin:.3e}")
    # With `max - min = s` the two extremes straddle the mean, so one of
    # them is at least `s/2` away from it and the SUM of squared deviations
    # is at least `(s/2)**2`. The floor admits a window only when
    # `s > NOISE_FACTOR * max|r|`, and `max|r| >= rmin` there.
    _p("  the smallest squared-deviation SUM the floor can admit",
       f">= {((NOISE_FACTOR * rmin) / 2) ** 2:.3e}",
       f"against the smallest subnormal {float(np.nextafter(0.0, 1.0)):.3e}")
    print("  b) over every frame in this file, bars where the floor reports "
          "but the value is not finite:")
    probes = {k: v() for k, v in FRAMES.items()}
    probes["flat"] = _flat()
    probes["ladder"] = _ladder()
    probes["patches"] = _floored_patches()
    probes["zero-patches"] = _zero_patches()
    probes["quiet"] = _from_returns(
        1e-6 + 1e-13 * np.random.default_rng(3).standard_normal(600))
    total = 0
    for name, close in sorted(probes.items()):
        r = _returns_of(close)
        W = sliding_window_view(r, LENGTH)
        mean = W.sum(axis=1) / LENGTH
        sd = np.sqrt(((W - mean[:, None]) ** 2).sum(axis=1) / (LENGTH - 1))
        med = np.median(W, axis=1)
        hi, lo = W.max(axis=1), W.min(axis=1)
        rep = (hi - lo) > NOISE_FACTOR * np.maximum(hi, -lo)
        with np.errstate(invalid="ignore", divide="ignore"):
            v = (mean - med) / sd
        total += int((rep & ~np.isfinite(v)).sum())
    _p("over " + str(len(probes)) + " frames", f"{total} bars")
    print("\nG5 a bad close empties the windows that hold it "
          "(400-bar frame)")
    for bar in (0, 1, 19, 200, 398, 399):
        close = _walk(400).copy()
        base = ts_medskew_20(close)
        close.iloc[bar] = np.nan
        col = ts_medskew_20(close)
        moved = np.flatnonzero((base.isna() != col.isna()).to_numpy())
        earlier = int((moved < bar).sum())
        _p(f"NaN at bar {bar}", f"emptied {moved.size}",
           f"earlier bars moved {earlier}")
    print("\nG6 a close that is not a normal positive float")
    for value in (np.nan, np.inf, 0.0, -1.0, 1e-310):
        close = _walk(400).copy()
        close.iloc[200] = value
        col = ts_medskew_20(close)
        _p(f"close[200] = {value}", f"fires {int(col.notna().sum())}/400")
    print("\nG7 one enormous return stays LOCAL (2,000-bar frame priced at "
          "1e-198, spike at bar 200)")
    rng = np.random.default_rng(21)
    r = rng.normal(0.0, 0.015, 2000)
    base_close = Series(1e-198 * np.cumprod(1.0 + r))
    base = ts_medskew_20(base_close)
    print("  (the tail is NOT bit-identical by construction: a spike "
          "rescales every later close by a non-power-of-two factor, so "
          "`c[t]/c[t-1]` is rebuilt from different bits)")
    print("  (the 20 holding windows are summarised by their MEDIAN and "
          "their spread -- they are 20 different windows, not 20 copies)")
    for mag in (1e2, 1e6, 1e8, 1e100, 1e300, 1e154):
        rr = r.copy()
        rr[200] = mag
        close = Series(1e-198 * np.cumprod(1.0 + rr))
        col = ts_medskew_20(close)
        tail = slice(220, None)
        eq, shared, mx = _shared(col.iloc[tail], base.iloc[tail])
        hold = col.iloc[200:220]
        _p(f"spike x{mag:.0e}", f"tail bit-equal {eq}/{shared}",
           f"max |diff| {mx:.3e}",
           f"holding windows fire {int(hold.notna().sum())}/20",
           f"median there "
           f"{float(hold.median()) if hold.notna().any() else float('nan'):+.6f}",
           f"spread there "
           f"{float(hold.max() - hold.min()) if hold.notna().any() else float('nan'):.3e}")
    print("\nG7b the same spike through the PROTOTYPE's online accumulators "
          "-- the comparison the tolerance above has to be read against")
    for mag in (1e2, 1e6, 1e8, 1e100):
        rr = r.copy()
        rr[200] = mag
        close = Series(1e-198 * np.cumprod(1.0 + rr))
        proto, proto_base = _prototype(close), _prototype(base_close)
        tail = slice(220, None)
        same = bool((proto.iloc[tail].fillna(-99.0)
                     == proto_base.iloc[tail].fillna(-99.0)).all())
        eq, shared, mx = _shared(proto.iloc[tail], proto_base.iloc[tail])
        _p(f"prototype, spike x{mag:.0e}", f"tail bit-identical {same}",
           f"bit-equal {eq}/{shared}", f"max |diff| {mx:.3e}")


# ---------------------------------------------------------------- overlaps


def section_O():
    print("\n=== What the column overlaps ===")
    print("\nO1 against the window's OWN textbook skewness, over 20,000 "
          "independent windows")
    rng = np.random.default_rng(31)
    med, skw = [], []
    for _ in range(20000):
        t = rng.integers(0, 3)
        if t == 0:
            x = rng.standard_normal(LENGTH)
        elif t == 1:
            x = rng.standard_exponential(LENGTH)
        else:
            x = -rng.standard_exponential(LENGTH)
        s = np.std(x, ddof=1)
        if s == 0:
            continue
        med.append((np.mean(x) - np.median(x)) / s)
        skw.append(float(pd.Series(x).skew()))
    a, b = pd.Series(med), pd.Series(skw)
    _p("Spearman vs sample skewness", f"{_spearman(a, b):.4f}")
    _p("Pearson", f"{float(a.corr(b)):.4f}")
    print("\nO2 against a rolling skew(20) of the same returns, by frame")
    for name in sorted(FRAMES):
        close = FRAMES[name]()
        r = close / close.shift(1) - 1.0
        _p(name, f"{_spearman(ts_medskew_20(close), r.rolling(LENGTH).skew()):+.4f}")
    print("\nO3 against the SHIPPED OSAP_RETSKEW_21 and TS_ABOVE_MEAN_20")
    for name in sorted(FRAMES):
        close = FRAMES[name]()
        col = ts_medskew_20(close)
        _p(name, f"OSAP_RETSKEW_21 {_spearman(col, osap_retskew_21(close)):+.4f}",
           f"TS_ABOVE_MEAN_20 {_spearman(col, ts_above_mean_20(close)):+.4f}")
    print("\nO3b OSAP_RETSKEW at length 20 (the same window, so the "
          "closest thing the fork has)")
    for name in sorted(FRAMES):
        close = FRAMES[name]()
        _p(name, f"{_spearman(ts_medskew_20(close), osap_retskew_21(close, length=LENGTH)):+.4f}")
    print("\nO4 volatility and direction")
    close = _walk()
    r = close / close.shift(1) - 1.0
    col = ts_medskew_20(close)
    _p("vs the window's return sd",
       f"{_spearman(col, r.rolling(LENGTH).std()):+.4f}")
    _p("vs the window's mean return",
       f"{_spearman(col, r.rolling(LENGTH).mean()):+.4f}")
    _p("vs the close itself", f"{_spearman(col, close):+.4f}")
    print("\nO5 autocorrelation of the column (a state, not an event)")
    for lag in (1, 5, 10, 20):
        _p(f"lag {lag}", f"{float(col.autocorr(lag)):+.4f}")
    print("\nO6 the level on iid returns (independent windows)")
    rng = np.random.default_rng(41)
    for label, draw in [
        ("gaussian", lambda: rng.standard_normal(LENGTH)),
        ("student-t(2)", lambda: rng.standard_t(2, LENGTH)),
        ("exponential", lambda: rng.standard_exponential(LENGTH)),
        ("-exponential", lambda: -rng.standard_exponential(LENGTH)),
    ]:
        vals = []
        for _ in range(20000):
            x = draw()
            s = np.std(x, ddof=1)
            if s:
                vals.append((np.mean(x) - np.median(x)) / s)
        v = np.asarray(vals)
        _p(label, f"mean {v.mean():+.4f}", f"sd {v.std():.4f}",
           f"max |v| {np.abs(v).max():.4f}")


# -------------------------------------------------------------------- cost


def section_Z():
    print("\n=== Cost ===")
    n = 400000
    close = _walk(n, seed=2)
    for length in (3, 20, 60, 250):
        tracemalloc.start()
        t0 = time.perf_counter()
        ts_medskew_20(close, length=length)
        dt = time.perf_counter() - t0
        peak = tracemalloc.get_traced_memory()[1]
        tracemalloc.stop()
        _p(f"module, length={length}", f"{dt * 1000:.0f} ms",
           f"peak {peak / 1e6:.1f} MB")
    for label, fn in [("matrix deviations", _matrix_variant),
                      ("np.median(windows)", _np_median_variant)]:
        for length in (20, 250):
            tracemalloc.start()
            t0 = time.perf_counter()
            fn(close, length=length)
            dt = time.perf_counter() - t0
            peak = tracemalloc.get_traced_memory()[1]
            tracemalloc.stop()
            _p(f"{label}, length={length}", f"{dt * 1000:.0f} ms",
               f"peak {peak / 1e6:.1f} MB")
    print("\n  the two median spellings agree:")
    small = _walk(20000, seed=2)
    _p("module vs np.median(windows)",
       _agree(ts_medskew_20(small), _np_median_variant(small)))
    _p("module vs the matrix deviations",
       _agree(ts_medskew_20(small), _matrix_variant(small)))
    t0 = time.perf_counter()
    _source_windowed(small)
    _p("the window-by-window oracle on 20,000 bars",
       f"{time.perf_counter() - t0:.2f} s")


SECTIONS = {"A": section_A, "B": section_B, "C": section_C, "D": section_D,
            "G": section_G, "O": section_O, "Z": section_Z}


if __name__ == "__main__":
    wanted = [a.upper() for a in sys.argv[1:]] or list(SECTIONS)
    for key in wanted:
        SECTIONS[key]()
