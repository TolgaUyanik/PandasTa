# -*- coding: utf-8 -*-
"""TS-IMQ-20 (PandasTa issue #99): every number in
`docs/TsImq20Measured.md` is printed by this script.

    python docs/measure_ts_imq_20.py            # all sections
    python docs/measure_ts_imq_20.py A C D      # selected sections

Sections: A (the source and the readings), B (the mutant sweep),
C (reachability), D (scale), G (the guards), O (what the column overlaps),
Z (cost). Gate E is run by the launcher, not here.

Nothing in this file is imported by shipped code. The oracles are
deliberately slow: tsfresh's own expression applied window by window, a
`math.fsum` scalar loop and an EXACT `fractions.Fraction` oracle, none of
which share code with the module.
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

from pandas_ta.statistics.tf_centroid_20 import tf_centroid_20
from pandas_ta.statistics.ts_above_mean_20 import ts_above_mean_20
from pandas_ta.statistics.ts_cid_ce_20 import ts_cid_ce_20
from pandas_ta.statistics.ts_medskew_20 import ts_medskew_20
from pandas_ta.statistics.ts_peaks_20 import ts_peaks_20
from pandas_ta.statistics.ts_imq_20 import Q, ts_imq_20

LENGTH = 20
_REAL = importlib.import_module("pandas_ta.statistics.ts_imq_20")


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


def _quiet(n=600, seed=31, sigma=1e-6):
    """Honest but tiny returns: 1e-6, far above the closes' own rounding."""
    rng = np.random.default_rng(seed)
    return _from_returns(rng.normal(0.0, sigma, n))


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
    if int(m.sum()) < 3:
        return float("nan")
    return float(a[m].corr(b[m], method="spearman"))


def _agree(a, b):
    """(masks equal, bit-equal count, shared count, max |difference|)."""
    masks = bool((a.isna() == b.isna()).all())
    m = a.notna() & b.notna()
    if not int(m.sum()):
        return masks, 0, 0, float("nan")
    d = (a[m] - b[m]).abs()
    return masks, int((a[m] == b[m]).sum()), int(m.sum()), float(d.max())


def _p(label, *rest):
    print(f"  {label:<58}", *rest)


# ----------------------------------------------------------------- oracles


def _tsfresh_index_mass_quantile(x, q):
    """tsfresh `feature_calculators.index_mass_quantile`, one window, as the
    published definition states it. `sum` is Python's (sequential), which is
    what makes `mass_centralized[-1]` exactly 1.0."""
    x = np.asarray(x)
    abs_x = np.abs(x)
    s = sum(abs_x)
    if s == 0:
        return float("nan")
    mass_centralized = np.cumsum(abs_x) / s
    return (np.argmax(mass_centralized >= q) + 1) / len(x)


def _source_windowed(close, length=LENGTH, q=Q, on_abs=False):
    """The source expression applied one window at a time. Shares no code
    with the module."""
    r = _returns_of(close)
    out = np.full(r.size, np.nan)
    for t in range(length - 1, r.size):
        x = r[t - length + 1:t + 1]
        if not np.isfinite(x).all():
            continue
        out[t] = _tsfresh_index_mass_quantile(np.abs(x) if on_abs else x, q)
    return Series(out, index=close.index)


def _prototype(close, length=LENGTH, q=Q):
    """`docs/issues/screen/ind_screen.py`, candidate `ts_imq_20`, retyped
    (that tree is the owner's and is gitignored, so it is copied here rather
    than imported):

        @cand("ts_imq_20", ..., "index_mass_quantile(q=0.5) on 20 |returns|")
        def _(o, h, l, c, v): return roll(ret(c), 20, w_index_mass_quantile)

        def w_index_mass_quantile(W, q=0.5):
            A = np.abs(W)
            s = A.sum(1, keepdims=True)
            cs = np.cumsum(A, 1) / np.where(s == 0, np.nan, s)
            idx = (cs >= q).argmax(1) + 1.0
            return np.where(np.isnan(cs[:, -1]), np.nan, idx / W.shape[1])

    with `roll`/`_win`/`_from_win` the screen's trailing
    `sliding_window_view`. Two things differ from the module: `A.sum(1)` is
    numpy's PAIRWISE reduction where the module accumulates the total
    sequentially, and the `(rows, length)` `np.cumsum(A, 1)` is materialised.
    """
    r = close / close.shift(1) - 1.0
    a = r.to_numpy(dtype=float)
    W = sliding_window_view(a, length)
    A = np.abs(W)
    s = A.sum(1, keepdims=True)
    with np.errstate(invalid="ignore", divide="ignore"):
        cs = np.cumsum(A, 1) / np.where(s == 0, np.nan, s)
    idx = (cs >= q).argmax(1) + 1.0
    out = np.full(close.size, np.nan)
    out[length - 1:] = np.where(np.isnan(cs[:, -1]), np.nan, idx / W.shape[1])
    return Series(out, index=close.index)


def _fsum_windowed(close, length=LENGTH, q=Q):
    """The same statistic in scalar Python, with `math.fsum` -- which is
    EXACTLY rounded -- for every partial sum and for the total."""
    r = [float(v) for v in _returns_of(close)]
    out = np.full(len(r), np.nan)
    for t in range(length - 1, len(r)):
        x = [abs(v) for v in r[t - length + 1:t + 1]]
        if not all(math.isfinite(v) for v in x):
            continue
        s = math.fsum(x)
        if s == 0.0:
            continue
        for k in range(length):
            if math.fsum(x[:k + 1]) / s >= q:
                out[t] = (k + 1) / length
                break
    return Series(out, index=close.index)


def _exact_windowed(close, length=LENGTH, q=Q):
    """An EXACT oracle. Every float is a rational, so the partial sums, the
    total and the comparison are computed with NO rounding at all."""
    r = _returns_of(close)
    qf = Fraction(q)
    out = np.full(r.size, np.nan)
    for t in range(length - 1, r.size):
        x = r[t - length + 1:t + 1]
        if not np.isfinite(x).all():
            continue
        xs = [Fraction(abs(float(v))) for v in x]
        s = sum(xs)
        if s == 0:
            continue
        cum = Fraction(0)
        for k, v in enumerate(xs):
            cum += v
            if cum / s >= qf:
                out[t] = (k + 1) / length
                break
    return Series(out, index=close.index)


def _global_cumsum_variant(close, length=LENGTH, q=Q):
    """The O(n) spelling this module does NOT use: ONE global cumulative sum,
    differenced per window. Algebraically the same statistic, and neither
    local nor well conditioned -- every window's partial sums are differences
    of two numbers that have accumulated the whole frame before them. The NaN
    bookkeeping is kept separate so the comparison is about the accumulator
    and not about mask handling."""
    r = _returns_of(close)
    a = np.abs(r)
    bad = ~np.isfinite(a)
    c = np.concatenate([[0.0], np.cumsum(np.where(bad, 0.0, a))])
    badc = np.concatenate([[0], np.cumsum(bad.astype(np.int64))])
    out = np.full(r.size, np.nan)
    for t in range(length - 1, r.size):
        lo = t - length + 1
        if badc[t + 1] - badc[lo]:
            continue
        s = c[t + 1] - c[lo]
        if not np.isfinite(s) or s <= 0:
            continue
        for k in range(length):
            if (c[lo + k + 1] - c[lo]) / s >= q:
                out[t] = (k + 1) / length
                break
    return Series(out, index=close.index)


# --------------------------------------------------- A: source and readings


def _section_a():
    print("\nA. THE SOURCE AND THE READINGS")

    print("\nA1. tsfresh's expression, window by window (bit-equal / shared,"
          " masks)")
    for name in FRAMES:
        close = FRAMES[name]()
        masks, eq, shared, mx = _agree(ts_imq_20(close),
                                       _source_windowed(close))
        _p(name, f"bit-equal {eq}/{shared}  masks-equal {masks}  max|d| {mx}")

    print("\nA1b. the issue's `on |returns|` against the raw returns "
          "(the source abs's either way)")
    for name in ["walk", "heavy-tailed", "two-point"]:
        close = FRAMES[name]()
        masks, eq, shared, mx = _agree(_source_windowed(close),
                                       _source_windowed(close, on_abs=True))
        _p(name, f"bit-equal {eq}/{shared}  masks-equal {masks}  max|d| {mx}")

    print("\nA1c. the SCREEN PROTOTYPE, retyped from "
          "docs/issues/screen/ind_screen.py")
    for name in FRAMES:
        close = FRAMES[name]()
        masks, eq, shared, mx = _agree(ts_imq_20(close), _prototype(close))
        _p(name, f"bit-equal {eq}/{shared}  masks-equal {masks}  max|d| {mx}")
    for label, frame in (("flat (300 identical closes)", _flat()),
                         ("1%/bar ladder", _ladder()),
                         ("quiet (returns 1e-6)", _quiet())):
        mine, proto = ts_imq_20(frame), _prototype(frame)
        masks, eq, shared, mx = _agree(mine, proto)
        _p(label, f"module non-NaN {int(mine.notna().sum())}  prototype "
                  f"non-NaN {int(proto.notna().sum())}  bit-equal "
                  f"{eq}/{shared}  masks-equal {masks}")
    print("    where the two DO part company -- the guards the screen has "
          "no need of:")
    for bad in (0.0, -1.0, 1e-310, np.inf):
        close = _walk(400, seed=3)
        close.iloc[200] = bad
        mine, proto = ts_imq_20(close), _prototype(close)
        masks, eq, shared, mx = _agree(mine, proto)
        _p(f"close[200] = {bad}",
           f"module non-NaN {int(mine.notna().sum())}  prototype non-NaN "
           f"{int(proto.notna().sum())}  masks-equal {masks}")
    for k in (1e100, 1e307):
        mine, proto = ts_imq_20(_spiked(k)), _prototype(_spiked(k))
        masks, eq, shared, mx = _agree(mine, proto)
        _p(f"a {k:g} return planted at bar 200",
           f"module non-NaN {int(mine.notna().sum())}  prototype non-NaN "
           f"{int(proto.notna().sum())}  masks-equal {masks}")

    print("\nA2. a math.fsum scalar loop (exactly rounded partial sums)")
    for name in FRAMES:
        close = FRAMES[name]()
        masks, eq, shared, mx = _agree(ts_imq_20(close), _fsum_windowed(close))
        _p(name, f"bit-equal {eq}/{shared}  masks-equal {masks}  max|d| {mx}")

    print("\nA3. the EXACT rational oracle")
    tot_eq = tot = 0
    for name in FRAMES:
        close = FRAMES[name]()
        masks, eq, shared, mx = _agree(ts_imq_20(close), _exact_windowed(close))
        tot_eq += eq
        tot += shared
        _p(name, f"bit-equal {eq}/{shared}  masks-equal {masks}  max|d| {mx}")
    _p("pooled", f"bit-equal {tot_eq}/{tot}")

    print("\nA3b. the closed form, and a hunt for a float-vs-exact "
          "disagreement")
    # Closes that DOUBLE give a return of exactly 1.0 on every bar, so the
    # window's `length` values are exactly equal, `s` is exact and the
    # crossing is exactly at position `length / 2`.
    for n in (2, 4, 20, 60):
        doubling = Series(2.0 ** np.arange(n + 1, dtype=float))
        got = float(ts_imq_20(doubling, length=n).iloc[-1])
        _p(f"{n} returns of EXACTLY 1.0 (a doubling ladder)",
           f"value {got}  expected {np.ceil(n * Q) / n}")
    rng = np.random.default_rng(5)
    disagree = tried = 0
    for _ in range(200):
        # Near-tie windows on purpose: the first half carries almost exactly
        # half the mass, so the comparison runs against the threshold.
        half = np.abs(rng.normal(0.0, 0.01, LENGTH // 2))
        x = np.concatenate([half, half * (1.0 + rng.normal(0.0, 1e-13,
                                                           LENGTH // 2))])
        close = _window_frame(x * rng.choice([-1.0, 1.0], LENGTH))
        a = float(ts_imq_20(close).iloc[-1])
        b = float(_exact_windowed(close).iloc[-1])
        tried += 1
        disagree += a != b
    _p(f"{tried} windows built to straddle the threshold",
       f"float-vs-exact disagreements {disagree}")

    print("\nA4. the `found` backstop has no witness, and the value set")
    for name in FRAMES:
        close = FRAMES[name]()
        col = ts_imq_20(close)
        vals = np.unique(col.dropna().to_numpy())
        ok = np.all(np.isin(np.round(vals * LENGTH, 9),
                            np.arange(1, LENGTH + 1)))
        _p(name, f"distinct {vals.size}  all k/length {bool(ok)}  "
                 f"min {vals.min():.2f}  max {vals.max():.2f}")
    print("    (`found` != `s > 0` is counted inside the module's own run "
          "below)")
    for name in FRAMES:
        close = FRAMES[name]()
        _p(name, f"found-vs-mass disagreements {_found_vs_mass(close)}")
    print("    the backstop's only WITNESS, by mutant (a 300-bar walk):")
    walk300 = _walk(300)
    hi_q = _load_mutant("Q = 0.5", "Q = 1.5")
    no_backstop = _load_patched([
        ("Q = 0.5", "Q = 1.5"),
        ("    reported = (s > 0.0) & found", "    reported = (s > 0.0)")])
    _p("the real module", f"non-NaN {int(ts_imq_20(walk300).notna().sum())}"
                          f"/{300 - LENGTH}")
    _p("Q = 1.5, backstop KEPT",
       f"non-NaN {int(hi_q.ts_imq_20(walk300).notna().sum())}")
    col = no_backstop.ts_imq_20(walk300).dropna()
    _p("Q = 1.5, backstop DROPPED",
       f"non-NaN {int(col.size)}  max value {float(col.max())}")

    print("\nA5. the readings the wording leaves open, on a walk")
    walk = _walk()
    base = ts_imq_20(walk)

    log_close = Series(np.exp(np.cumsum(np.concatenate(
        [[0.0], np.log(walk.to_numpy()[1:] / walk.to_numpy()[:-1])]))),
        index=walk.index)
    logr = np.concatenate([[np.nan], np.log(walk.to_numpy()[1:]
                                            / walk.to_numpy()[:-1])])
    other = _from_r_series(logr, walk)
    masks, eq, shared, mx = _agree(base, other)
    _p("simple vs LOG returns",
       f"rho {_spearman(base, other):.6f}  bit-equal {eq}/{shared}  "
       f"max|d| {mx:.17g} ({mx / (1.0 / LENGTH):.2f} positions)")

    on_closes = _on_closes_variant(walk)
    _p("of the 20 |returns| vs of the 20 CLOSES",
       f"rho {_spearman(base, on_closes):.6f}")

    short = ts_imq_20(walk, length=LENGTH - 1)
    _p("20 returns (21 closes) vs 20 CLOSES (19 returns)",
       f"rho {_spearman(base, short):.6f}  "
       f"max|d| {_agree(base, short)[3]:.4f}")

    # Built as its own oracle -- `np.argmax(...)` WITHOUT the source's `+ 1`
    # -- and not as `base - 1/length`, which would be the conclusion
    # subtracted from itself.
    for name in ("walk", "heavy-tailed"):
        close = FRAMES[name]()
        mine, no1 = ts_imq_20(close), _no_plus_one_variant(close)
        d = (mine - no1).dropna()
        _p(f"the source's `+ 1` dropped ({name})",
           f"rho {_spearman(mine, no1):.6f}  shift [{float(d.min()):.17g}, "
           f"{float(d.max()):.17g}]  variant min {float(no1.min()):.2f} vs "
           f"module min {float(mine.min()):.2f}  variant bars at 0.0 "
           f"{int((no1 == 0.0).sum())}")

    strict = _strict_variant(walk)
    _p("`>= q` vs `> q`",
       f"bit-equal {_agree(base, strict)[1]}/{FIRED}  "
       f"rho {_spearman(base, strict):.6f}")

    cross = _crossmul_variant(walk)
    _p("`acc / s >= q` vs `acc >= q * s`",
       f"bit-equal {_agree(base, cross)[1]}/{FIRED}  "
       f"rho {_spearman(base, cross):.6f}")

    for q in (0.25, 0.75):
        other = _source_windowed(walk, q=q)
        _p(f"q = {q} instead of 0.5", f"rho {_spearman(base, other):.6f}  "
                                      f"mean {float(other.mean()):.4f}")

    print("\nA6. the distribution on a walk and on iid windows")
    col = base.dropna()
    counts = col.value_counts().sort_index()
    _p("fired / distinct / min / max",
       f"{col.size} / {col.unique().size} / {col.min():.2f} / {col.max():.2f}")
    _p("median / mean / sd",
       f"{col.median():.4f} / {col.mean():.4f} / {col.std():.4f}")
    _p("mode (value, count)",
       f"({counts.idxmax():.2f}, {int(counts.max())})  "
       f"rarest ({counts.idxmin():.2f}, {int(counts.min())})")
    for lag in (1, 5, 10, 20):
        _p(f"autocorrelation at lag {lag}", f"{col.autocorr(lag):.4f}")
    for law, draw in (("gaussian", lambda g, n: g.normal(0.0, 0.01, n)),
                      ("student-t(2)",
                       lambda g, n: 0.01 * g.standard_t(2.0, n)),
                      ("exponential",
                       lambda g, n: 0.01 * g.standard_exponential(n))):
        vals = _iid_windows(draw, 20000)
        _p(f"20,000 independent {law} windows",
           f"mean {vals.mean():.4f}  sd {vals.std():.4f}  "
           f"min {vals.min():.2f}  max {vals.max():.2f}")


def _from_r_series(r, close):
    """The module's statistic computed on a GIVEN return array (used for the
    log-return reading), via the source expression."""
    out = np.full(r.size, np.nan)
    for t in range(LENGTH - 1, r.size):
        x = r[t - LENGTH + 1:t + 1]
        if not np.isfinite(x).all():
            continue
        out[t] = _tsfresh_index_mass_quantile(x, Q)
    return Series(out, index=close.index)


def _on_closes_variant(close, length=LENGTH, q=Q):
    """The statistic OF the closes rather than of their returns."""
    c = close.to_numpy(dtype=float)
    out = np.full(c.size, np.nan)
    for t in range(length - 1, c.size):
        out[t] = _tsfresh_index_mass_quantile(c[t - length + 1:t + 1], q)
    return Series(out, index=close.index)


def _no_plus_one_variant(close, length=LENGTH, q=Q):
    """The source expression WITHOUT its `+ 1`: `argmax(...) / len(x)`, a
    0-based position. Built from scratch rather than derived from the
    module's output, so what it measures is the reading and not a
    subtraction."""
    r = _returns_of(close)
    out = np.full(r.size, np.nan)
    for t in range(length - 1, r.size):
        x = np.abs(r[t - length + 1:t + 1])
        if not np.isfinite(x).all():
            continue
        s = sum(x)
        if s == 0:
            continue
        out[t] = np.argmax(np.cumsum(x) / s >= q) / length
    return Series(out, index=close.index)


def _strict_variant(close, length=LENGTH, q=Q):
    r = _returns_of(close)
    out = np.full(r.size, np.nan)
    for t in range(length - 1, r.size):
        x = np.abs(r[t - length + 1:t + 1])
        if not np.isfinite(x).all():
            continue
        s = sum(x)
        if s == 0:
            continue
        mass = np.cumsum(x) / s
        hit = np.flatnonzero(mass > q)
        if hit.size:
            out[t] = (hit[0] + 1) / length
    return Series(out, index=close.index)


def _crossmul_variant(close, length=LENGTH, q=Q):
    r = _returns_of(close)
    out = np.full(r.size, np.nan)
    for t in range(length - 1, r.size):
        x = np.abs(r[t - length + 1:t + 1])
        if not np.isfinite(x).all():
            continue
        s = sum(x)
        if s == 0:
            continue
        cum = np.cumsum(x)
        hit = np.flatnonzero(cum >= q * s)
        if hit.size:
            out[t] = (hit[0] + 1) / length
    return Series(out, index=close.index)


def _found_vs_mass(close, length=LENGTH):
    """Re-runs the module's own two loops and counts the windows where the
    `found` backstop and `s > 0` disagree."""
    r = _returns_of(close)
    a = np.abs(r)
    a = np.where(a < np.finfo(float).max / (2 * length), a, np.nan)
    aw = sliding_window_view(a, length)
    s = np.zeros(aw.shape[0])
    for j in range(length):
        s += aw[:, j]
    acc = np.zeros(aw.shape[0])
    found = np.zeros(aw.shape[0], dtype=bool)
    with np.errstate(invalid="ignore", divide="ignore"):
        for j in range(length):
            acc += aw[:, j]
            found |= acc / s >= Q
    return int((found != (s > 0.0)).sum())


def _iid_windows(draw, count, length=LENGTH, seed=19):
    rng = np.random.default_rng(seed)
    out = np.empty(count)
    for i in range(count):
        x = np.abs(draw(rng, length))
        s = sum(x)
        out[i] = ((np.argmax(np.cumsum(x) / s >= Q) + 1) / length
                  if s > 0 else np.nan)
    return out


# ------------------------------------------------------------ B: the mutants


MUTANTS = {
    "back_date_two": (
        "    out[length - 1:] = np.where(reported, idx / length, np.nan)",
        "    out[length - 3:c.size - 2] = np.where(reported, idx / length,"
        " np.nan)"),
    "back_date_full": (
        "    out[length - 1:] = np.where(reported, idx / length, np.nan)",
        "    out[:rows] = np.where(reported, idx / length, np.nan)"),
    "forward_window": (
        "    aw = sliding_window_view(a, length)",
        "    aw = sliding_window_view(np.roll(a, -1), length)"),
    "forward_return": (
        "        r = (px / px.shift(1) - 1.0).to_numpy()",
        "        r = (px.shift(-1) / px - 1.0).to_numpy()"),
    "future_total": (
        "    acc = np.zeros(rows)",
        "    s = np.roll(s, -1)\n    acc = np.zeros(rows)"),
}
OFFSETS = range(40, 1500, 40)  # 37 offsets
PAIRS = {
    "walk": (_walk(), _walk(seed=97)),
    "tick-rounded": (_tick_rounded(), _tick_rounded(seed=56)),
    "heavy-tailed": (_heavy_tailed(), _heavy_tailed(seed=8)),
}


def _load_patched(pairs):
    import types
    src = open(_REAL.__file__, encoding="utf-8").read()
    for old, new in pairs:
        assert src.count(old) == 1, f"mutation target {old!r} not unique"
        src = src.replace(old, new)
    mod = types.ModuleType("_ts_imq_20_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src, _REAL.__file__, "exec"), mod.__dict__)
    return mod


def _load_mutant(old, new):
    return _load_patched([(old, new)])


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


def _section_b():
    print("\nB. GATE B -- THE MUTANT SWEEP (37 offsets, J = 40..1480)")
    print("\nB1. the real module leaks nothing")
    for name, (close, other) in PAIRS.items():
        _p(name, f"leaks at {len(_caught(ts_imq_20, close, other))}/37")
    for length in (5, 60, 250):
        close, other = PAIRS["walk"]
        hits = _caught(ts_imq_20, close, other, length=length)
        first = int(ts_imq_20(close, length=length).notna().to_numpy().argmax())
        _p(f"walk at length {length}",
           f"leaks at {len(hits)}/37  first fired bar {first}")

    print("\nB2. every mutant is live and caught")
    for mutant, (old, new) in MUTANTS.items():
        mod = _load_mutant(old, new)
        for name, (close, other) in PAIRS.items():
            live = not mod.ts_imq_20(close).equals(ts_imq_20(close))
            hits = _caught(mod.ts_imq_20, close, other)
            _p(f"{mutant} / {name}", f"live {live}  caught {len(hits)}/37")


# ------------------------------------------------------- C: reachability


def _section_c():
    print("\nC. REACHABILITY (synthetic; the real-data counts are the "
          "launcher's Gate E run)")
    for name in FRAMES:
        close = FRAMES[name]()
        col = ts_imq_20(close)
        first = int(col.notna().to_numpy().argmax())
        _p(name, f"non-NaN {int(col.notna().sum())}/{close.size}  "
                 f"distinct {int(col.dropna().unique().size)}  "
                 f"first fired bar {first}  "
                 f"non-zero {int((col.dropna() != 0).sum())}")
    _p("flat (300 identical closes)",
       f"non-NaN {int(ts_imq_20(_flat()).notna().sum())}")
    _p("ladder (1%/bar, 300 bars)",
       f"non-NaN {int(ts_imq_20(_ladder()).notna().sum())}  "
       f"distinct {int(ts_imq_20(_ladder()).dropna().unique().size)}  "
       f"value {float(ts_imq_20(_ladder()).dropna().iloc[0])}")
    _p("quiet (returns 1e-6, 600 bars)",
       f"non-NaN {int(ts_imq_20(_quiet()).notna().sum())}  "
       f"distinct {int(ts_imq_20(_quiet()).dropna().unique().size)}")


# -------------------------------------------------------------- D: scale


def _section_d():
    print("\nD. GATE D -- SCALE")
    print("\nD1. x8 and x64 on price, bit-identical")
    for name in FRAMES:
        close = FRAMES[name]()
        row = []
        for k in (8.0, 64.0):
            masks, eq, shared, mx = _agree(ts_imq_20(close),
                                           ts_imq_20(close * k))
            row.append(f"x{int(k)} {eq}/{shared} masks {masks}")
        _p(name, "  ".join(row))
    for length in (2, 5, 60, 250):
        close = _walk()
        row = []
        for k in (8.0, 64.0):
            masks, eq, shared, mx = _agree(
                ts_imq_20(close, length=length),
                ts_imq_20(close * k, length=length))
            row.append(f"x{int(k)} {eq}/{shared} masks {masks}")
        _p(f"walk at length {length}", "  ".join(row))

    print("\nD2. x10, x3.7, x0.1 -- not powers of two, so NOT bit-identical "
          "by construction")
    for name in FRAMES:
        close = FRAMES[name]()
        row = []
        for k in (10.0, 3.7, 0.1):
            masks, eq, shared, mx = _agree(ts_imq_20(close),
                                           ts_imq_20(close * k))
            row.append(f"x{k} {eq}/{shared} masks {masks} max|d| {mx}")
        _p(name, "  ".join(row))

    print("\nD3. invariance to a positive rescale of the RETURNS themselves")
    rng = np.random.default_rng(11)
    r = rng.normal(0.0, 0.015, 1500)
    base = ts_imq_20(_from_returns(r))
    for k in (2.0, 0.5, 1e-6):
        masks, eq, shared, mx = _agree(base, ts_imq_20(_from_returns(r * k)))
        _p(f"returns x{k}", f"bit-equal {eq}/{shared}  masks {masks}")
    other = ts_imq_20(_from_returns(r + 0.004))
    moved = int((base.dropna() != other.dropna()).sum())
    _p("returns + 0.004 (a SHIFT, not a rescale)",
       f"moved {moved}/{FIRED}  rho {_spearman(base, other):.4f}")

    print("\nD4. what the column does NOT see")
    walk = _walk()
    r = _returns_of(walk)
    sd = Series(r, index=walk.index).rolling(LENGTH).std()
    mean = Series(r, index=walk.index).rolling(LENGTH).mean()
    _p("vs the window's return sd", f"rho {_spearman(ts_imq_20(walk), sd):.4f}")
    _p("vs the window's mean return",
       f"rho {_spearman(ts_imq_20(walk), mean):.4f}")
    _p("vs the close itself", f"rho {_spearman(ts_imq_20(walk), walk):.4f}")


# ------------------------------------------------------------- G: guards


def _section_g():
    print("\nG. THE GUARDS")

    print("\nG1. a bad close empties the windows that hold it, and no more")
    combos = moved_anywhere = 0
    for bad in (np.nan, np.inf, 0.0, -1.0, 1e-310):
        for at in (0, 1, 19, 200, 398, 399):
            close = _walk(400, seed=3)
            base = ts_imq_20(close)
            spoilt = close.copy()
            spoilt.iloc[at] = bad
            got = ts_imq_20(spoilt)
            newly = int((base.notna() & got.isna()).sum())
            earlier = int((base.iloc[:at].fillna(-9)
                           != got.iloc[:at].fillna(-9)).sum())
            combos += 1
            moved_anywhere += earlier > 0
            if at == 200 or np.isnan(bad):
                _p(f"close[{at}] = {bad}",
                   f"newly NaN {newly}  bars before it moved {earlier}")
    _p(f"over all {combos} (bad value, position) pairs",
       f"pairs with a bar before the bad close moved {moved_anywhere}")

    print("\nG2. all-zero returns: the source's own `s == 0` rule")
    _p("21 identical closes", f"value {ts_imq_20(_flat(21)).iloc[-1]}")
    _p("300 identical closes",
       f"non-NaN {int(ts_imq_20(_flat()).notna().sum())}")
    mixed = _window_frame([0.0] * 19 + [0.01])
    _p("19 zero returns then one 1%", f"value {float(ts_imq_20(mixed).iloc[-1])}")
    mixed = _window_frame([0.01] + [0.0] * 19)
    _p("one 1% then 19 zero returns", f"value {float(ts_imq_20(mixed).iloc[-1])}")

    print("\nG3. NO dispersion floor -- what one would cost")
    lad = _ladder()
    col = ts_imq_20(lad)
    counts = col.dropna().value_counts().sort_index()
    _p("1%/bar ladder: this module",
       f"non-NaN {int(col.notna().sum())}  "
       f"values {dict((float(k), int(v)) for k, v in counts.items())}")
    doubling = Series(2.0 ** np.arange(301, dtype=float))
    dcol = ts_imq_20(doubling)
    _p("a DOUBLING ladder (returns exactly 1.0, no rounding)",
       f"non-NaN {int(dcol.notna().sum())}  "
       f"distinct {int(dcol.dropna().unique().size)}  "
       f"value {float(dcol.dropna().iloc[0])}")
    _p("1%/bar ladder: ts_medskew_20 (which HAS the floor)",
       f"non-NaN {int(ts_medskew_20(lad).notna().sum())}")
    un = _unfloored_medskew(lad)
    _p("1%/bar ladder: the same statistic WITHOUT its floor",
       f"non-NaN {int(un.notna().sum())}  "
       f"range [{float(un.min()):.4f}, {float(un.max()):.4f}]")
    quiet = _quiet()
    qcol = ts_imq_20(quiet)
    _p("quiet frame (returns 1e-6): this module",
       f"non-NaN {int(qcol.notna().sum())}/{quiet.size}  "
       f"distinct {int(qcol.dropna().unique().size)}")
    _p("quiet frame: the sibling's RELATIVE floor would report",
       f"non-NaN {int(ts_medskew_20(quiet).notna().sum())}")
    exact = _exact_windowed(quiet)
    masks, eq, shared, mx = _agree(qcol, exact)
    _p("quiet frame vs the EXACT oracle",
       f"bit-equal {eq}/{shared}  masks {masks}")

    print("\nG4. locality: a planted spike")
    print("    (the frame is priced at 1e-198 so even a 1e+300 return cannot "
          "overflow the close path)")
    for k in (1e2, 1e6, 1e8, 1e100, 1e300, 1e307):
        a, b = (ts_imq_20(_spiked(None)), ts_imq_20(_spiked(k)))
        window = b.iloc[200:220]
        later_eq = int((a.iloc[220:].fillna(-9)
                        == b.iloc[220:].fillna(-9)).sum())
        _p(f"spike x{k:g}",
           f"its 20 windows non-NaN {int(window.notna().sum())}  "
           f"bars 220.. bit-identical {later_eq}/{a.size - 220}")
    print("    the GLOBAL-cumsum spelling, same frames:")
    base = _global_cumsum_variant(_spiked(None))
    for k in (1e2, 1e8, 1e100):
        b = _global_cumsum_variant(_spiked(k))
        later_eq = int((base.iloc[220:].fillna(-9)
                        == b.iloc[220:].fillna(-9)).sum())
        tail = b.iloc[220:].dropna()
        _p(f"spike x{k:g}", f"bars 220.. bit-identical "
                            f"{later_eq}/{base.size - 220}  tail range "
                            f"[{float(tail.min()):.2f}, "
                            f"{float(tail.max()):.2f}]  "
                            f"distinct {int(tail.unique().size)}")
    tail = ts_imq_20(_spiked(1e100)).iloc[220:].dropna()
    _p("this module's own tail at x1e+100",
       f"range [{float(tail.min()):.2f}, {float(tail.max()):.2f}]  "
       f"distinct {int(tail.unique().size)}")

    print("\nG5. the per-return bound")
    _p("max |r| admitted at length 20",
       f"{np.finfo(float).max / (2 * LENGTH):.3e}")


def _spiked(k, n=2000, seed=13, sigma=0.01, price=1e-198):
    """A 2,000-bar frame priced at 1e-198, optionally with one enormous
    return planted at bar 200. The low base price is what keeps the close
    path finite for a spike up to 1e+307."""
    rng = np.random.default_rng(seed)
    r = rng.normal(0.0, sigma, n)
    if k is not None:
        r[200] = k
    return Series(price * np.cumprod(1.0 + r))


def _unfloored_medskew(close, length=LENGTH):
    """`ts_medskew_20` with its relative floor removed -- used only to show
    what the floor is FOR in that module and why this one does not need it."""
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


# ---------------------------------------------------------- O: the overlap


def _section_o():
    print("\nO. WHAT THE COLUMN OVERLAPS")
    print("\nO1. against the fork's own statistics columns, per frame")
    others = {
        "TFCENTROID_20": tf_centroid_20,
        "TS_ABOVE_MEAN_20": ts_above_mean_20,
        "TS_MEDSKEW_20": ts_medskew_20,
        "TS_CID_CE_20": ts_cid_ce_20,
        "TS_PEAKS_20": ts_peaks_20,
    }
    pooled = {k: ([], []) for k in others}
    per_frame = {k: [] for k in others}
    for name in FRAMES:
        close = FRAMES[name]()
        base = ts_imq_20(close)
        row = []
        for label, fn in others.items():
            col = fn(close)
            if isinstance(col, pd.DataFrame):
                col = col.iloc[:, 0]
            rho = _spearman(base, col)
            per_frame[label].append(rho)
            row.append(f"{label} {rho:+.4f}")
            m = base.notna() & col.notna()
            pooled[label][0].extend(base[m].tolist())
            pooled[label][1].extend(col[m].tolist())
        _p(name, "  ".join(row))
    print("    pooled over the nine frames, and the per-frame |rho| summary"
          " (the shape Gate E's bands read):")
    for label, (xs, ys) in pooled.items():
        rho = float(Series(xs).corr(Series(ys), method="spearman"))
        mags = np.abs(np.array(per_frame[label]))
        _p(label, f"pooled {rho:+.6f}  n {len(xs)}  per-frame |rho| "
                  f"max {mags.max():.4f} median {np.median(mags):.4f} "
                  f"min {mags.min():.4f}  frames >= 0.90: "
                  f"{int((mags >= 0.90).sum())}/{mags.size}")

    print("\nO2. against a local ATR-ratio proxy (the screen's top "
          "comparator family)")
    for name in ["walk", "heavy-tailed", "trending"]:
        close = FRAMES[name]()
        r = Series(np.abs(_returns_of(close)), index=close.index)
        ratio = r.rolling(5).mean() / r.rolling(LENGTH).mean()
        _p(name, f"mean|r|_5 / mean|r|_20  "
                 f"rho {_spearman(ts_imq_20(close), ratio):+.4f}")


# ------------------------------------------------------------- Z: the cost


def _section_z():
    print("\nZ. COST (this machine; the PEAKS are the claim)")
    rng = np.random.default_rng(2)
    close = _from_returns(rng.normal(0.0, 0.01, 400000))
    # THREE runs per length, reported as a range: a single observation of a
    # wall clock is the fastest of the ones nobody printed.
    for length in (2, 20, 60, 250):
        times, peak = [], 0.0
        for _ in range(3):
            tracemalloc.start()
            t0 = time.perf_counter()
            ts_imq_20(close, length=length)
            times.append((time.perf_counter() - t0) * 1000.0)
            peak = max(peak, tracemalloc.get_traced_memory()[1] / 1e6)
            tracemalloc.stop()
        _p(f"length {length} on 400,000 bars",
           f"{min(times):6.1f}-{max(times):6.1f} ms over 3 runs  "
           f"peak {peak:.1f} MB")
    small = _from_returns(rng.normal(0.0, 0.01, 20000))
    t0 = time.perf_counter()
    _source_windowed(small)
    _p("the window-by-window oracle on 20,000 bars",
       f"{time.perf_counter() - t0:.2f} s")


SECTIONS = {"A": _section_a, "B": _section_b, "C": _section_c,
            "D": _section_d, "G": _section_g, "O": _section_o, "Z": _section_z}


if __name__ == "__main__":
    wanted = [s.upper() for s in sys.argv[1:]] or list(SECTIONS)
    print(f"numpy {np.__version__}  pandas {pd.__version__}")
    for key in wanted:
        SECTIONS[key]()
