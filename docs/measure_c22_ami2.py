# -*- coding: utf-8 -*-
"""C22-AMI2 (PandasTa issue #127): every number in `docs/C22Ami2Measured.md`
and in the docstrings of `pandas_ta/statistics/c22_ami2.py` and
`tests/test_c22_ami2.py`.

    python docs/measure_c22_ami2.py              # S, A-E, G, H, T, Z
    python docs/measure_c22_ami2.py A D          # just those
    python docs/measure_c22_ami2.py P            # the GPL-3.0 black box

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
from fractions import Fraction
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas_ta as ta  # noqa: E402
from pandas_ta.statistics.c22_ami2 import (  # noqa: E402
    BUFFER, CHUNK_VALUES, MAX_AMI, MIN_LENGTH, NOISE_FLOOR, NUM_BINS, TAU,
    ZSCORE_DDOF, _ami_rows, ami_bounds, c22_ami2)

ROOT = Path(__file__).resolve().parent.parent
MODULE = importlib.import_module("pandas_ta.statistics.c22_ami2")
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


def alternating(n=N, amp=0.02, level=100.0):
    """Returns that alternate exactly +amp / -amp, so `r[t + 2] == r[t]`:
    the lag-2 pair is the SAME value and the automutual information is the
    entropy of the marginal exactly."""
    r = amp * np.where(np.arange(n) % 2 == 0, 1.0, -1.0)
    return pd.Series(level * np.cumprod(1.0 + r))


def ladder(n=N, step=0.01, start=100.0):
    """An exactly geometric path: constant returns up to rounding."""
    return pd.Series(start * (1.0 + step) ** np.arange(n, dtype=float))


def kurus_path(n=N, start=100.0, step=0.01):
    """A price rising by exactly one kurus a bar: a smooth hyperbola in
    returns, which is what emptied `c22_periodicity`."""
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
        _BASE[name] = c22_ami2(FRAMES[name])
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


# ------------------------------------------------- independent spellings
def shipped_on(window):
    """One window through the shipped row kernel."""
    w = np.asarray(window, float)
    return float(_ami_rows(w.reshape(1, -1))[0])


def shipped_bins(window):
    """The bin index of every point, and the edges, as the shipped kernel
    assigns them: evenly spaced between the window's own extremes, with the
    two OUTER edges pushed out by BUFFER (which cannot bind)."""
    w = np.asarray(window, float)
    n = w.size
    sd = float(w.std(ddof=ZSCORE_DDOF))
    z = (w - w.mean()) / sd
    lo, hi = float(z.min()), float(z.max())
    width = (hi - lo) / NUM_BINS
    idx = np.zeros(n, dtype=np.int64)
    for i in range(1, NUM_BINS):
        idx += z >= lo + i * width
    edges = [lo + i * width for i in range(NUM_BINS + 1)]
    edges[0] -= BUFFER
    edges[-1] += BUFFER
    return idx, np.array(edges)


def uniform_bins(window):
    """The bin index under the OTHER reading of the same sentence: the buffer
    pushed into the interior edges too, so the bins are evenly spaced over
    `[min - BUFFER, max + BUFFER]`. Section A5 prices it."""
    w = np.asarray(window, float)
    sd = float(w.std(ddof=ZSCORE_DDOF))
    z = (w - w.mean()) / sd
    lo, hi = float(z.min()), float(z.max())
    step = (hi - lo + 2.0 * BUFFER) / NUM_BINS
    idx = np.zeros(w.size, dtype=np.int64)
    for i in range(1, NUM_BINS):
        idx += z >= lo - BUFFER + i * step
    return idx


def miller_madow(counts, pairs):
    """The correction the shipped column subtracts from the plug-in MI:
    `(occupied cells - occupied rows - occupied cols + 1) / (2 pairs)`, which
    is the Miller-Madow correction applied to each of the three entropies in
    `MI = H(i) + H(j) - H(i, j)`."""
    c = np.asarray(counts)
    occ = float((c > 0).sum())
    occ_i = float((c.sum(axis=1) > 0).sum())
    occ_j = float((c.sum(axis=0) > 0).sum())
    return (occ - occ_i - occ_j + 1.0) / (2.0 * pairs)


def mi_from_counts(counts, pairs, how="direct", correct=True):
    """The column's quantity in nats from an integer contingency table.

    `direct` is `sum p log(p / (pi pj))`; `entropy` is the algebraically
    identical `H(i) + H(j) - H(i, j)`, which rounds differently and is the
    second spelling section A2 compares. `correct` subtracts the Miller-Madow
    term, which is what the feature reports; `correct=False` is the raw
    plug-in MI, priced in section A12.
    """
    c = np.asarray(counts, float)
    pij = c / pairs
    pi, pj = pij.sum(axis=1), pij.sum(axis=0)
    if how == "direct":
        out = 0.0
        for i in range(pij.shape[0]):
            for j in range(pij.shape[1]):
                if pij[i, j] > 0.0:
                    out += pij[i, j] * math.log(pij[i, j] / (pi[i] * pj[j]))
    else:
        def h(p):
            return -sum(float(v) * math.log(float(v))
                        for v in np.ravel(p) if v > 0)
        out = h(pi) + h(pj) - h(pij)
    return out - miller_madow(c, pairs) if correct else out


def value_def(window, ddof=ZSCORE_DDOF, buffer=BUFFER, edges="outer",
              binsource="window", assign="edges", tau=TAU, bins=NUM_BINS,
              how="direct", zscore=True, correct=True):
    """The DEFINITION, re-spelled in plain Python with no numpy vectorisation.

    Knobs, each of them a reading section A prices rather than assumes:

    * `ddof`     -- the z-score's divisor (`ZSCORE_DDOF`).
    * `buffer`   -- how far the outer edges reach past the extremes.
    * `edges`    -- `outer` (SHIPPED): `bins + 1` evenly spaced edges from
                    `min` to `max` with only the two OUTER ones pushed out by
                    `buffer`, so the interior edges sit where an unbuffered
                    even split puts them; `uniform`: evenly spaced over
                    `[min - buffer, max + buffer]`, which moves every interior
                    edge too.
    * `binsource` -- `window`: the range comes from the whole window, which is
                    what binning the SERIES and then forming the limbs means;
                    `y1`: from the lagged-FROM limb only, which drops the
                    window's last `tau` points from the range. (The two limbs'
                    UNION is the whole window, so that is not a third
                    reading.)
    * `assign`   -- `edges`: count the interior edges the point stands at or
                    above; `floor`: `floor((y - b0) / width)`, clipped.
    * `zscore`   -- False bins the RAW returns.
    * `correct`  -- False drops the Miller-Madow correction, leaving the raw
                    plug-in mutual information.
    """
    w = [float(v) for v in window]
    n = len(w)
    if not all(math.isfinite(v) for v in w):
        return float("nan")
    mean = math.fsum(w) / n
    var = math.fsum((v - mean) ** 2 for v in w) / (n - ddof)
    sd = math.sqrt(var)
    if not (math.isfinite(sd) and sd > 0.0):
        return float("nan")
    z = [(v - mean) / sd for v in w] if zscore else list(w)
    pool = z if binsource == "window" else z[:n - tau]
    lo, hi = min(pool), max(pool)
    if edges == "uniform":
        step = (hi - lo + 2.0 * buffer) / bins
        b = [lo - buffer + i * step for i in range(bins + 1)]
    elif edges == "outer":
        b = [lo + i * (hi - lo) / bins for i in range(bins + 1)]
        b[0] -= buffer
        b[-1] += buffer
    else:
        raise ValueError(edges)

    def which(v):
        if assign == "floor":
            width = b[2] - b[1]
            k = int(math.floor((v - b[1]) / width)) + 1 if width > 0 else 0
            return min(max(k, 0), bins - 1)
        k = 0
        for i in range(1, bins):
            if v >= b[i]:
                k = i
        return k

    i1 = [which(v) for v in z[:n - tau]]
    i2 = [which(v) for v in z[tau:]]
    counts = np.zeros((bins, bins), dtype=np.int64)
    for a, c in zip(i1, i2):
        counts[a, c] += 1
    return mi_from_counts(counts, n - tau, how=how, correct=correct)


def plug_in_on(window):
    """The UNCORRECTED plug-in MI of the shipped bin assignment: the half of
    the quantity that sklearn and np.histogram2d can check independently."""
    idx, _ = shipped_bins(window)
    counts = np.zeros((NUM_BINS, NUM_BINS), dtype=np.int64)
    for a, c in zip(idx[:len(idx) - TAU], idx[TAU:]):
        counts[a, c] += 1
    return mi_from_counts(counts, len(idx) - TAU, correct=False)


def value_sklearn(window):
    """`sklearn.metrics.mutual_info_score` on the shipped bin labels: an
    independent implementation of the plug-in half of the computation, with
    this module's own Miller-Madow term subtracted."""
    from sklearn.metrics import mutual_info_score
    idx, _ = shipped_bins(window)
    counts = np.zeros((NUM_BINS, NUM_BINS), dtype=np.int64)
    for a, c in zip(idx[:len(idx) - TAU], idx[TAU:]):
        counts[a, c] += 1
    mi = float(mutual_info_score(idx[:len(idx) - TAU], idx[TAU:]))
    return mi - miller_madow(counts, len(idx) - TAU)


def value_histogram2d(window):
    """`np.histogram2d` on the shipped z-score and edges: an independent
    implementation of the BINNING, including its half-open convention."""
    w = np.asarray(window, float)
    n = w.size
    sd = float(w.std(ddof=ZSCORE_DDOF))
    z = (w - w.mean()) / sd
    _, e = shipped_bins(w)
    counts, _, _ = np.histogram2d(z[:n - TAU], z[TAU:], bins=[e, e])
    return mi_from_counts(counts.astype(np.int64), n - TAU)


# ------------------------------------------------------- exact oracle
def exact_counts(window, ddof=ZSCORE_DDOF):
    """The joint histogram in EXACT arithmetic, as integers, or None.

    Every input double is an exact rational, and the bin edges are an AFFINE
    function of the window's own minimum and maximum, so the z-score's
    irrational `sd` cancels out of every membership test entirely: writing
    `u = r - mean`, the test `u / sd >= min(u) / sd + i (max(u) - min(u)) /
    (sd * bins)` is `u >= min(u) + i (max(u) - min(u)) / bins`, a comparison
    of two rationals. Not one rounding happens here, and the two outer edges
    -- the only place `BUFFER` appears -- cannot exclude a point, because
    every `u` lies in `[min(u), max(u)]`.
    """
    y = [Fraction(float(v)) for v in window]
    n = len(y)
    mean = sum(y) / n
    u = [v - mean for v in y]
    var = sum(v * v for v in u) / (n - ddof)
    if var == 0:
        return None
    mn, mx = min(u), max(u)
    counts = np.zeros((NUM_BINS, NUM_BINS), dtype=np.int64)
    idx = []
    for v in u:
        k = 0
        for i in range(1, NUM_BINS):
            if v >= mn + Fraction(i, NUM_BINS) * (mx - mn):
                k = i
        idx.append(k)
    for a, c in zip(idx[:n - TAU], idx[TAU:]):
        counts[a, c] += 1
    return counts


def value_exact(window, ddof=ZSCORE_DDOF):
    """The column's value from the EXACT joint histogram. The counts and the
    Miller-Madow term are exact; the only roundings left are the logarithms,
    computed from exact rational ratios."""
    counts = exact_counts(window, ddof=ddof)
    if counts is None:
        return float("nan")
    pairs = int(counts.sum())
    out = 0.0
    ci = counts.sum(axis=1)
    cj = counts.sum(axis=0)
    for i in range(NUM_BINS):
        for j in range(NUM_BINS):
            if counts[i, j]:
                ratio = Fraction(int(counts[i, j]) * pairs,
                                 int(ci[i]) * int(cj[j]))
                out += float(Fraction(int(counts[i, j]), pairs)) * \
                    math.log(float(ratio))
    occ = int((counts > 0).sum())
    return out - float(Fraction(occ - int((ci > 0).sum())
                                - int((cj > 0).sum()) + 1, 2 * pairs))


def ami_candidates(idx, n, tau=TAU, bins=NUM_BINS, tag=""):
    """A battery of formulas over one window's bin assignment.

    The plug-in mutual information is the definition and is what this module
    ships; the others are the readings a measurement can tell apart -- a
    bias-corrected estimator, marginals taken over the whole window rather
    than over the lagged limb, and the two normalisation slips that make the
    marginals sum to more than one. Several of them CAN be negative, which is
    the property the reference implementation has and a mutual information
    cannot.
    """
    pairs = n - tau
    counts = np.zeros((bins, bins), dtype=np.int64)
    for a, c in zip(idx[:pairs], idx[tau:]):
        counts[a, c] += 1
    c = counts.astype(float)
    pij = c / pairs
    A, B = pij.sum(axis=1), pij.sum(axis=0)

    def mi(p, a, b):
        out = 0.0
        for i in range(bins):
            for j in range(bins):
                if p[i, j] > 0.0 and a[i] > 0.0 and b[j] > 0.0:
                    out += p[i, j] * math.log(p[i, j] / (a[i] * b[j]))
        return out

    plug = mi(pij, A, B)
    occ = float((c > 0).sum())
    occ_i = float((c.sum(axis=1) > 0).sum())
    occ_j = float((c.sum(axis=0) > 0).sum())
    # The whole window's histogram, which is what a marginal taken over `y`
    # rather than over the lagged limb would use.
    full = np.bincount(idx, minlength=bins).astype(float)
    out = {
        f"{tag}plug-in MI, no correction": plug,
        f"{tag}MI - Miller-Madow (cells)":
            plug - (occ - occ_i - occ_j + 1.0) / (2.0 * pairs),
        f"{tag}MI - (occ_i-1)(occ_j-1)/2N":
            plug - (occ_i - 1.0) * (occ_j - 1.0) / (2.0 * pairs),
        f"{tag}MI - (bins-1)**2/2N":
            plug - (bins - 1.0) ** 2 / (2.0 * pairs),
        f"{tag}marginals over the whole window, /n":
            mi(pij, full / n, full / n),
        f"{tag}marginals over the whole window, /pairs":
            mi(pij, full / pairs, full / pairs),
        f"{tag}joint /n, marginals /n":
            mi(c / n, (c / n).sum(axis=1), (c / n).sum(axis=0)),
        f"{tag}one marginal over the whole window, /pairs":
            mi(pij, full / pairs, B),
        f"{tag}marginals transposed": mi(pij, B, A),
    }
    return out


def marginal_entropy(window):
    """`H` of the lagged-FROM limb's bin marginal, in nats."""
    idx, _ = shipped_bins(window)
    i1 = idx[:len(idx) - TAU]
    _, c = np.unique(i1, return_counts=True)
    p = c / c.sum()
    return float(-np.sum(p * np.log(p)))


def law_value(window):
    """What the column must read when `bin(r[t + TAU])` is a BIJECTIVE
    function of `bin(r[t])` -- the case the exact laws of section A3 build.

    The joint histogram then has one occupied cell per occupied row and
    column, so the plug-in MI is the marginal entropy exactly and the
    Miller-Madow term is `(1 - k) / (2 pairs)` over the `k` occupied cells,
    i.e. it ADDS `(k - 1) / (2 pairs)`:

        value = H(marginal) + (k - 1) / (2 * (length - TAU))
    """
    idx, _ = shipped_bins(window)
    pairs = len(idx) - TAU
    counts = np.zeros((NUM_BINS, NUM_BINS), dtype=np.int64)
    for a, c in zip(idx[:pairs], idx[TAU:]):
        counts[a, c] += 1
    k = int((counts > 0).sum())
    return marginal_entropy(window) + (k - 1) / (2.0 * pairs), k


# ----------------------------------------------------------- the sections
def section_s():
    head("S. Setup -- what ran, and with what")
    row("numpy", np.__version__)
    row("pandas", pd.__version__)
    row("python", sys.version.split()[0])
    dispatch = getattr(np.core._multiarray_umath, "__cpu_dispatch__", [])
    enabled = [f for f in dispatch
               if np.core._multiarray_umath.__cpu_features__.get(f)]
    row("dispatchable CPU features enabled", enabled)
    for name in ("pycatch22", "scipy", "sklearn"):
        row(name, "installed" if importlib.util.find_spec(name)
            else "ABSENT")
    row("TAU / NUM_BINS / BUFFER", f"{TAU} / {NUM_BINS} / {BUFFER}")
    row("ZSCORE_DDOF / MIN_LENGTH", f"{ZSCORE_DDOF} / {MIN_LENGTH}")
    row("NOISE_FLOOR", f"{NOISE_FLOOR:.3e}")
    row("MAX_AMI = log(NUM_BINS)", f"{MAX_AMI:.6f}")
    row("frames", f"{list(FRAMES)} x {N} bars")


def section_a():
    head("A. Gate A -- correctness")

    head("A1. The EXACT oracle: the joint histogram with zero roundings")
    print("Every input double is a rational, and the bin edges are AFFINE in")
    print("the window's own min and max, so the z-score's irrational sd")
    print("cancels out of every membership test: the count matrix is decided")
    print("by exact rational comparisons. The only roundings left in the value")
    print("are the logarithms themselves.")
    row("frame", "windows", "count matrices equal", "max |value gap|")
    for name in FRAMES:
        win, bars = windows(FRAMES[name])
        eq = ran = 0
        gap = 0.0
        for i in range(0, win.shape[0], 97):
            mine = shipped_on(win[i])
            got = exact_counts(win[i])
            idx, _ = shipped_bins(win[i])
            mine_counts = np.zeros((NUM_BINS, NUM_BINS), dtype=np.int64)
            for a, c in zip(idx[:LENGTH - TAU], idx[TAU:]):
                mine_counts[a, c] += 1
            eq += int(got is not None and np.array_equal(got, mine_counts))
            ran += 1
            want = value_exact(win[i])
            if math.isfinite(mine) and math.isfinite(want):
                gap = max(gap, abs(mine - want))
        row(name, ran, eq, f"{gap:.3e}")

    head("A2. Four independent spellings of the same quantity")
    print("plain-Python definition (fsum, no numpy); the entropy identity")
    print("H(i) + H(j) - H(i,j); np.histogram2d for the binning; and")
    print("sklearn.metrics.mutual_info_score for the plug-in information,")
    print("with this module's Miller-Madow term subtracted from it.")
    have_sk = importlib.util.find_spec("sklearn") is not None
    row("frame", "windows", "max |def - mine|", "max |entropy - mine|",
        "max |hist2d - mine|", "max |sklearn - mine|")
    for name in FRAMES:
        win, _ = windows(FRAMES[name])
        g = [0.0, 0.0, 0.0, 0.0]
        ran = 0
        for i in range(0, win.shape[0], 7):
            mine = shipped_on(win[i])
            if not math.isfinite(mine):
                continue
            ran += 1
            g[0] = max(g[0], abs(mine - value_def(win[i])))
            g[1] = max(g[1], abs(mine - value_def(win[i], how="entropy")))
            g[2] = max(g[2], abs(mine - value_histogram2d(win[i])))
            if have_sk:
                g[3] = max(g[3], abs(mine - value_sklearn(win[i])))
        row(name, ran, *[f"{v:.3e}" for v in g])

    head("A3. The EXACT laws: a return series whose lag-2 pair is determined")
    print("r[t+2] == r[t] (alternating +-2%) makes the lag-2 pair the SAME")
    print("value, so the joint histogram is a bijection and the value is the")
    print("marginal entropy plus the Miller-Madow term exactly; a period-4")
    print("cosine makes r[t+2] == -r[t], which the bins resolve just as well.")
    print("ln 2 = 0.6931472, and the correction over k occupied cells adds")
    print("(k - 1) / 196.")
    for label, frame in (("alternating +-2%", alternating()),
                         ("cosine period 4", cosine_returns(period=4.0)),
                         ("cosine period 2", cosine_returns(period=2.0))):
        s = c22_ami2(frame).dropna()
        win, _ = windows(frame)
        probe = list(range(0, win.shape[0], 199))
        gap = 0.0
        ks = set()
        for i in probe:
            want, k = law_value(win[i])
            ks.add(k)
            gap = max(gap, abs(float(s.iloc[i]) - want))
        vals = sorted(set(np.round(s.to_numpy(), 12).tolist()))
        row(label, f"fired {int(s.size)}",
            f"distinct (12dp) {len(vals)}", f"values {vals[:4]}",
            f"occupied cells {sorted(ks)}",
            f"max |value - (H + (k-1)/196)| {gap:.3e}")
    row("ln 2", f"{math.log(2):.7f}", "log(NUM_BINS)", f"{MAX_AMI:.7f}",
        f"bounds at length 100 {tuple(round(v, 6) for v in ami_bounds(LENGTH))}")

    head("A3b. The cosine frames, by period")
    row("period", "fired", "distinct (9dp)", "min", "median", "max")
    for p in (4, 5, 6, 8, 10, 20, 40, 97):
        s = c22_ami2(cosine_returns(period=float(p))).dropna()
        a = s.to_numpy()
        row(p, int(a.size), len(set(np.round(a, 9).tolist())),
            f"{a.min():.6f}", f"{np.median(a):.6f}", f"{a.max():.6f}")

    head("A4. The bin-assignment spelling")
    print("Counting the interior edges a point stands at or above (shipped)")
    print("against floor((y - b0) / width), clipped. Algebraically the same;")
    print("they round differently, so what matters is whether any POINT lands")
    print("in a different bin -- compared here as integer arrays, not through")
    print("the value, which also carries the summation's own rounding.")
    row("frame", "windows", "points binned differently",
        "value bars differing in any bit", "max |value gap|")
    for name in FRAMES:
        win, _ = windows(FRAMES[name])
        mine, other, flips = [], [], 0
        for i in range(0, win.shape[0], 7):
            w = win[i]
            idx_edges, _ = shipped_bins(w)
            sd = float(w.std(ddof=ZSCORE_DDOF))
            z = (w - w.mean()) / sd
            lo, hi = float(z.min()), float(z.max())
            width = (hi - lo) / NUM_BINS
            idx_floor = np.clip(np.floor((z - lo) / width), 0,
                                NUM_BINS - 1).astype(np.int64)
            flips += int(np.sum(idx_edges != idx_floor))
            mine.append(shipped_on(w))
            other.append(value_def(w, assign="floor"))
        row(name, len(mine), flips, diff_bars(mine, other)[0],
            f"{worst_gap(mine, other):.3e}")

    head("A5. THE EDGE SPELLING -- the one reading a porter can get wrong")
    print("SHIPPED: evenly spaced edges from the window's min to its max,")
    print("with only the two OUTER ones pushed out by 0.1 so the extremes are")
    print("inside -- the buffer exists for INCLUSION and does not move an")
    print("interior edge. This is the reading the reference implements (P1c).")
    print("The other reading of the same sentence pushes the buffer into the")
    print("interior edges too: evenly spaced over [min - 0.1, max + 0.1], so")
    print("every interior edge moves by up to a tenth of a standard")
    print("deviation. It was this port's FIRST reading and it is a different")
    print("column, which is why it is priced here rather than argued about.")
    row("frame", "windows", "value bars moved", "max |gap|", "Spearman")
    for name in FRAMES:
        win, _ = windows(FRAMES[name])
        mine, other = [], []
        for i in range(0, win.shape[0], 3):
            mine.append(shipped_on(win[i]))
            other.append(value_def(win[i], edges="uniform"))
        row(name, len(mine), diff_bars(mine, other, tol=1e-12)[0],
            f"{worst_gap(mine, other):.4f}",
            f"{spearman(mine, other):+.4f}")

    head("A5b. THE MILLER-MADOW CORRECTION, priced")
    print("The column is the bias-CORRECTED estimate. Dropping the correction")
    print("leaves the raw plug-in MI, which is a different column and the one")
    print("the reference does NOT compute: the correction is 0.0816 nats at a")
    print("full 5x5 table and 0 where the occupied cells, rows and columns")
    print("satisfy cells = rows + cols - 1, and it can be NEGATIVE where the")
    print("table is a bijection. `moved` is counted at 1e-12, so the windows")
    print("where it is EXACTLY zero are visible rather than rounded away.")
    row("frame", "windows", "moved", "max |gap|", "mean correction", "min",
        "max", "Spearman of corrected vs plug-in", "median of the column")
    for name in FRAMES:
        win, _ = windows(FRAMES[name])
        mine, plug, corr = [], [], []
        for i in range(0, win.shape[0], 3):
            mine.append(shipped_on(win[i]))
            plug.append(plug_in_on(win[i]))
            corr.append(plug[-1] - mine[-1])
        row(name, len(mine), diff_bars(mine, plug, tol=1e-12)[0],
            f"{worst_gap(mine, plug):.4f}",
            f"{np.mean(corr):+.6f}", f"{np.min(corr):+.6f}",
            f"{np.max(corr):+.6f}", f"{spearman(mine, plug):+.4f}",
            f"{np.median(mine):.6f}")
    print("The correction is an integer multiple of 1 / (2 * pairs) ="
          f" {1 / (2 * (LENGTH - TAU)):.6f}, so a window where it is 0 is a")
    print("window whose table satisfies that identity exactly, not one where")
    print("it rounds small.")

    head("A6. The z-score is INERT, and that is a property of the edges")
    print("The interior edges are an affine function of the window's own min")
    print("and max, so ANY positive affine map of the window -- including the")
    print("z-score, and including its divisor convention -- leaves every bin")
    print("assignment alone. Measured three ways: ddof 0 against the shipped")
    print("ddof 1, no z-score at all, and the window shifted by +1.")
    row("frame", "windows", "ddof 0 moved", "no z-score moved",
        "shifted +1 moved", "max |gap| over the three")
    for name in FRAMES:
        win, _ = windows(FRAMES[name])
        mine, pop, raw, shifted = [], [], [], []
        for i in range(0, win.shape[0], 3):
            mine.append(shipped_on(win[i]))
            pop.append(value_def(win[i], ddof=0))
            raw.append(value_def(win[i], zscore=False))
            shifted.append(value_def(win[i] + 1.0))
        row(name, len(mine), diff_bars(mine, pop, tol=1e-12)[0],
            diff_bars(mine, raw, tol=1e-12)[0],
            diff_bars(mine, shifted, tol=1e-12)[0],
            f"{max(worst_gap(mine, pop), worst_gap(mine, raw), worst_gap(mine, shifted)):.3e}")

    head("A7. The BUFFER cannot bind under this edge spelling")
    print("The buffer moves only the two outer edges, and no point lies")
    print("outside [min, max], so any buffer at all gives the same bins. It")
    print("is kept because the definition has it. ⚠ Under the OTHER edge")
    print("reading (A5) the same numbers move 246 to 463 windows, which is")
    print("what makes A5 the real decision and this one the inert knob.")
    print("All six frames, 467 windows each, so the claim's scope is the")
    print("table's.")
    row("frame", "windows", *[f"buffer {b:g}" for b in
                              (0.0, 0.01, 1.0, 1e6)], "max |gap|")
    for name in FRAMES:
        win, _ = windows(FRAMES[name])
        idx = list(range(0, win.shape[0], 3))
        mine = [shipped_on(win[i]) for i in idx]
        cells, gap = [], 0.0
        for buf in (0.0, 0.01, 1.0, 1e6):
            other = [value_def(win[i], buffer=buf) for i in idx]
            cells.append(diff_bars(mine, other, tol=1e-12)[0])
            gap = max(gap, worst_gap(mine, other))
        row(name, len(idx), *cells, f"{gap:.3e}")

    head("A8. Where the range comes from: the window, or one limb")
    print("The definition bins the SERIES and then forms the lagged limbs, so")
    print("the range is the whole window's -- including the last TAU points,")
    print("which appear in the lagged-TO limb only. Taking it from the")
    print("lagged-FROM limb instead (the two limbs' UNION is the window, so")
    print("that is not a third reading):")
    row("frame", "windows", "value bars moved", "max |gap|")
    for name in FRAMES:
        win, _ = windows(FRAMES[name])
        mine, other = [], []
        for i in range(0, win.shape[0], 7):
            mine.append(shipped_on(win[i]))
            other.append(value_def(win[i], binsource="y1"))
        row(name, len(mine), diff_bars(mine, other, tol=1e-12)[0],
            f"{worst_gap(mine, other):.4f}")

    head("A9. The lag and the bin count are the feature's own parameters")
    wk, _ = windows(FRAMES["walk"])
    wk_idx = list(range(0, wk.shape[0], 3))
    wk_mine = [shipped_on(wk[i]) for i in wk_idx]
    row("reading", "median on the walk", "Spearman vs shipped")
    for t in (1, 2, 3, 5):
        other = [value_def(wk[i], tau=t) for i in wk_idx]
        row(f"tau = {t}", f"{np.median(other):.6f}",
            f"{spearman(wk_mine, other):+.4f}")
    for b in (3, 5, 10):
        other = [value_def(wk[i], bins=b) for i in wk_idx]
        row(f"bins = {b}", f"{np.median(other):.6f}",
            f"{spearman(wk_mine, other):+.4f}")

    head("A10. What the column reads on INDEPENDENT data")
    print("A plug-in 5x5 histogram MI over 98 pairs is upward-biased even")
    print("under independence -- the first-order term is (B-1)**2/(2 pairs) =")
    print(f"{(NUM_BINS - 1) ** 2 / (2 * (LENGTH - TAU)):.6f} nats -- which is")
    print("what the Miller-Madow correction is for. So the corrected column")
    print("sits NEAR ZERO on an independent window and the uncorrected one")
    print("does not, and 'near zero' is the reading a consumer must know.")
    rng = np.random.default_rng(404)
    vals, plugs = [], []
    for _ in range(400):
        w = rng.normal(0.0, 0.015, LENGTH)
        vals.append(value_def(w))
        plugs.append(value_def(w, correct=False))
    print("⚠ These are THIS section's 400 windows, drawn through the")
    print("plain-Python spelling so the corrected and uncorrected readings")
    print("come off the same draw. A10b draws ANOTHER 400 through the shipped")
    print("kernel; the figure quoted in the module and the receipt is A10b's.")
    row("iid normal windows, CORRECTED", len(vals),
        f"mean {np.mean(vals):.6f}", f"median {np.median(vals):.6f}",
        f"min {np.min(vals):.6f}", f"max {np.max(vals):.6f}",
        f"share < 0 {float(np.mean(np.asarray(vals) < 0)):.4f}")
    row("iid normal windows, PLUG-IN", len(plugs),
        f"mean {np.mean(plugs):.6f}", f"median {np.median(plugs):.6f}",
        f"min {np.min(plugs):.6f}", f"max {np.max(plugs):.6f}")
    row("first-order plug-in bias (B-1)**2 / (2 pairs)",
        f"{(NUM_BINS - 1) ** 2 / (2 * (LENGTH - TAU)):.6f}")
    shuffled = [value_def(rng.permutation(wk[i])) for i in wk_idx]
    row("the walk's own windows, SHUFFLED", len(shuffled),
        f"mean {np.mean(shuffled):.6f}", f"median {np.median(shuffled):.6f}")
    row("the walk's own windows, in order", len(wk_mine),
        f"mean {np.mean(wk_mine):.6f}", f"median {np.median(wk_mine):.6f}")
    head("A10b. The same, at the lengths the guard band allows")
    print("Every interpretive statement about 'no dependence' is a LENGTH-100")
    print("statement, because the correction scales as 1 / (2 (length - 2)).")
    print("Measured through the shipped kernel on independent normal windows:")
    row("length", "pairs", "windows", "iid median", "share < 0",
        "first-order plug-in bias", "ami_bounds")
    rng2 = np.random.default_rng(909)
    for length in (MIN_LENGTH, 50, LENGTH, 250):
        got = []
        for _ in range(400):
            got.append(shipped_on(rng2.normal(0.0, 0.015, length)))
        got = np.asarray(got)
        lo_b, hi_b = ami_bounds(length)
        row(length, length - TAU, got.size, f"{np.median(got):+.6f}",
            f"{float(np.mean(got < 0)):.4f}",
            f"{(NUM_BINS - 1) ** 2 / (2 * (length - TAU)):.6f}",
            f"[{lo_b:.4f}, {hi_b:.4f}]")
    print("⚠ At MIN_LENGTH the window holds as many lagged PAIRS as the table")
    print("has cells, which is the thinnest the estimator is allowed to be:")
    print("the first-order plug-in bias is four times the default's and the")
    print("reading is dominated by it. The guard band exists to stop a")
    print("caller computing something thinner than that, not to suggest the")
    print("floor is a good place to work.")

    iid_median = float(np.median(vals))
    for name in FRAMES:
        a = base(name).dropna().to_numpy()
        row(f"{name}, the shipped column", f"mean {a.mean():.6f}",
            f"median {np.median(a):.6f}",
            f"share above the iid median {iid_median:.4f}: "
            f"{float(np.mean(a > iid_median)):.4f}")

    head("A11. How close the binning runs to a rounding flip")
    print("Every value is decided by which side of an edge each point falls,")
    print("so the margin that matters is min |z - edge| over the interior")
    print("edges. A margin of order 1e-3 is ten orders of magnitude above a")
    print("last-bit question; a point ON an edge would be one.")
    row("frame", "windows", "min margin", "median min margin",
        "points within 1e-12 of an edge")
    for name in FRAMES:
        win, _ = windows(FRAMES[name])
        worst = math.inf
        mins = []
        ties = 0
        for i in range(0, win.shape[0], 7):
            w = win[i]
            sd = float(w.std(ddof=ZSCORE_DDOF))
            if not sd > NOISE_FLOOR:
                continue
            z = (w - w.mean()) / sd
            _, e = shipped_bins(w)
            d = np.abs(z[:, None] - e[None, 1:NUM_BINS])
            mins.append(float(d.min()))
            worst = min(worst, float(d.min()))
            ties += int(np.sum(d < 1e-12))
        row(name, len(mins), f"{worst:.3e}", f"{np.median(mins):.3e}", ties)


def section_b():
    head("B. Gate B -- causality")

    head("B1. The real module: future-perturbation sweep")
    print("Replace every close from bar J on with a fresh path; no bar before")
    print("J may move. 35 offsets x 8 splices per frame.")
    row("frame", "offsets", "splices", "leaking offsets")
    for name in FRAMES:
        f = FRAMES[name]
        hits = _leaks(c22_ami2, f, _offsets(len(f)), splices=8)
        row(name, 35, 8, hits if hits else "none")
    for length in (MIN_LENGTH, 120, 250):
        f = FRAMES["walk"]
        hits = _leaks(lambda s: c22_ami2(s, length=length), f,
                      _offsets(len(f), length), splices=4)
        row(f"walk, length={length}", 35, 4, hits if hits else "none")

    head("B2. Mutants, read off this module's source, edited and exec'd")
    print("Each is the same sweep on the walk frame, 35 offsets x 8 splices.")
    print("Three of the twelve (`no-bias-correction`, `no-overflow-guard`,")
    print("`no-floor`) are not look-aheads and are expected to be clean:")
    print("they are here because they change VALUES, and a sweep that caught")
    print("them would mean the sweep is measuring something other than")
    print("causality.")
    row("mutant", "what it does", "offsets caught of 35")
    for name in MUTANTS:
        fn = mutant(name)
        hits = _leaks(fn, FRAMES["walk"], _offsets(N), splices=8)
        row(name, MUTANTS[name][2], len(hits))

    head("B2b. Where a one-bar mutant moves anything, it moves bar J - 1")
    fn = mutant("write-back-dated")
    bad = np.asarray(fn(FRAMES["walk"]), float)
    seen = first_is_j1 = 0
    for j in _offsets(N, count=35):
        other = np.asarray(fn(_spliced(FRAMES["walk"], j)), float)
        moved = np.where(~((bad[:j] == other[:j])
                           | (np.isnan(bad[:j]) & np.isnan(other[:j]))))[0]
        if len(moved):
            seen += 1
            first_is_j1 += int(int(moved.min()) == j - 1)
    row("offsets where a pre-splice bar moved", seen,
        "of them whose FIRST moved bar is J-1", first_is_j1)

    head("B3. The mask mutant: dead on a clean frame, alive on a dirty one")
    fn = mutant("mask-back-dated")
    row("bit-equal on the clean walk", same(base("walk"), fn(FRAMES["walk"])))
    caught = 0
    for j in _offsets(N, count=12):
        dirty = FRAMES["walk"].copy()
        dirty.iloc[j] = np.nan
        a = np.asarray(c22_ami2(dirty), float)
        b = np.asarray(fn(dirty), float)
        moved = np.where(~((a == b) | (np.isnan(a) & np.isnan(b))))[0]
        caught += int(len(moved) > 0 and int(moved.min()) == j - 1)
    row("one bad close: offsets caught, first moved bar J-1", f"{caught} / 12")

    head("B4. Three mutants are DEAD, and each reason is measured")
    print("The bin edges are an AFFINE function of each row's own min and")
    print("max, so centring or scaling a row by the whole chunk's mean or sd")
    print("moves z and every edge together and no point changes bin: those")
    print("two are inert BY CONSTRUCTION, not by luck. The third swaps which")
    print("limb indexes the rows of the joint table, and a mutual information")
    print("-- and the Miller-Madow term over its occupied cells, rows and")
    print("columns -- is SYMMETRIC, so only the order of the 25 logarithms")
    print("changes. The one cross-row read that does change a value is taking")
    print("the EXTREMES from the chunk, which is caught.")
    for mut in ("chunk-wide-demean", "chunk-wide-sd", "joint-transposed",
                "chunk-wide-extremes"):
        fn = mutant(mut)
        for name in ("walk", "tick-rounded", "penny"):
            got = fn(FRAMES[name])
            row(f"{mut}, {name}", "bit-equal" if same(base(name), got)
                else f"moved {diff_bars(base(name), got)}",
                f"max |gap| {worst_gap(base(name), got):.3e}")
    print("⚠ The chunk-wide-extremes mutant is caught by VALUES on a frame")
    print("whose chunk is the whole series only because the chunk budget is")
    print("larger than the frame; the sweep above catches it through the")
    print("splice, which is what Gate B asks.")

    head("B5. Tie density -- the sweep's POWER")
    print("A continuous column ties far less than a lag column, so a one-bar")
    print("shift is visible on most splices.")
    row("frame", "fired bars", "share of neighbouring pairs exactly equal",
        "distinct values")
    for name in FRAMES:
        a = base(name).dropna().to_numpy()
        row(name, a.size, f"{float(np.mean(a[1:] == a[:-1])):.4f}",
            len(set(a.tolist())))


def section_c():
    head("C. Gate C -- reachability")

    head("C1. Synthetic frames (1,500 bars each)")
    row("frame", "fired", "distinct", "min", "median", "max",
        "share == 0", "share > 0.5")
    for name in FRAMES:
        s = base(name)
        a = s.dropna().to_numpy()
        row(name, int(s.notna().sum()), len(set(a.tolist())),
            f"{a.min():.6f}", f"{np.median(a):.6f}", f"{a.max():.6f}",
            f"{float(np.mean(a == 0.0)):.4f}",
            f"{float(np.mean(a > 0.5)):.4f}")
    lo_b, hi_b = ami_bounds(LENGTH)
    row("the derived scale at length 100", f"[{lo_b:.6f}, {hi_b:.6f}]",
        f"(plug-in MI is in [0, log {NUM_BINS}] = [0, {MAX_AMI:.6f}];"
        f" the correction can add up to {(NUM_BINS - 1) / (2 * (LENGTH - TAU)):.6f}"
        f" and subtract up to {(NUM_BINS - 1) ** 2 / (2 * (LENGTH - TAU)):.6f})")

    head("C2. The issue's own worry: BIST tick rounding")
    print("A 2-lira stock on a 1-kurus tick prints many returns as exactly")
    print("zero, and a shape feature of z-scored returns can read that rather")
    print("than return dynamics.")
    for name in ("walk", "tick-rounded", "penny"):
        r = returns(FRAMES[name])
        a = base(name).dropna().to_numpy()
        row(name, f"zero returns {float(np.mean(r == 0.0)):.4f}",
            f"distinct returns per window "
            f"{int(np.median([len(set(w.tolist())) for w in windows(FRAMES[name])[0][::97]]))}",
            f"median value {np.median(a):.6f}",
            f"fired {a.size}")
    print("The bins the zero return lands in, penny frame (first window):")
    win, _ = windows(FRAMES["penny"])
    idx, e = shipped_bins(win[0])
    vals, cnt = np.unique(idx, return_counts=True)
    row("bin", list(vals.tolist()), "count", list(cnt.tolist()))

    head("C3. What the one blanking rule costs")
    print("`unguarded` samples the windows that actually hold the frame's")
    print("variation -- for the 1-ulp frame, the 100 windows that contain the")
    print("step, where every other window is flat and blank under any rule.")
    for label, frame, probe in (
            ("flat run from bar 400", _flat_run(), None),
            ("exact geometric ladder", ladder(), None),
            ("one kurus a bar", kurus_path(), None),
            ("1-ulp step at 1e6", _ulp_frame(), range(600, 700, 13))):
        s = c22_ami2(frame)
        win, _ = windows(frame)
        sd = win.std(axis=1, ddof=ZSCORE_DDOF)
        take = probe or range(0, win.shape[0], 199)
        unguarded = [value_def(win[i]) for i in take]
        live = [v for v in unguarded if not math.isnan(v)]
        row(label, f"fired {int(s.notna().sum())} of {len(frame)}",
            f"max window sd {np.nanmax(sd):.3e}",
            f"unguarded would read {len(live)} of {len(unguarded)} sampled",
            f"range [{min(live):.4f}, {max(live):.4f}]" if live else "")
    row("NOISE_FLOOR", f"{NOISE_FLOOR:.3e}")
    print("And the sibling catch22 ports on the same frames, for contrast:")
    for label, frame in (("exact geometric ladder", ladder()),
                         ("one kurus a bar", kurus_path())):
        row(label,
            f"c22_ami2 {int(c22_ami2(frame).notna().sum())}",
            f"c22_ami_timescale {int(ta.c22_ami_timescale(frame).notna().sum())}",
            f"c22_periodicity {int(ta.c22_periodicity(frame).notna().sum())}")

    head("C4. The floor is inert on anything price-shaped")
    row("frame", "fired bars", "bars differing from the UNGUARDED spelling")
    fn = mutant("no-floor")
    for name in FRAMES:
        got = fn(FRAMES[name])
        row(name, int(base(name).notna().sum()),
            diff_bars(base(name), got))

    head("C5. Real data -- OWED, from the launcher's Gate E run")
    print("Every count above is SYNTHETIC. The pooled BIST figures (how many")
    print("of 398,849 bars fire, and how many read the exact floor 0) come")
    print("from the Gate E run issue-solver makes after this session.")


def section_d():
    head("D. Gate D -- scale-free")

    head("D1. Exact binary rescales -- bit-identical by construction")
    row("frame", "x8", "x64", "2**-40", "2**40")
    for name in FRAMES:
        cells = []
        for f in (8.0, 64.0, 2.0 ** -40, 2.0 ** 40):
            cells.append("bit-equal" if same(base(name),
                                             c22_ami2(FRAMES[name] * f))
                         else "MOVED")
        row(name, *cells)
    row("length", "x8", "x64", "2**-40", "2**40")
    for length in (MIN_LENGTH, 120, 250):
        a = c22_ami2(FRAMES["walk"], length=length)
        cells = []
        for f in (8.0, 64.0, 2.0 ** -40, 2.0 ** 40):
            cells.append("bit-equal" if same(
                a, c22_ami2(FRAMES["walk"] * f, length=length)) else "MOVED")
        row(f"walk, length={length}", *cells)
    row("price level", "fired", "x8", "x64", "2**-40", "2**40")
    for price in (1e-6, 1e6, 1e100):
        f = walk(level=price)
        b = c22_ami2(f)
        cells = []
        for k in (8.0, 64.0, 2.0 ** -40, 2.0 ** 40):
            # 1e100 x 2**40 overflows to +inf, which is bad data and not a
            # rescale: such a cell is reported as the blank count it becomes.
            got = c22_ami2(f * k)
            cells.append("bit-equal" if same(b, got)
                         else f"MOVED (fired {int(got.notna().sum())})")
        row(f"price level {price:g}", int(b.notna().sum()), *cells)

    head("D2. Inexact rescales")
    print("x10 and x3.7 are not exact in binary, so the returns themselves")
    print("move in the last bits and a bin assignment could flip.")
    row("frame", "factor", "value bars moved", "max |gap|", "mask bars")
    for name in FRAMES:
        for f in (10.0, 3.7, 0.1, 1.0000001):
            got = c22_ami2(FRAMES[name] * f)
            moved, mask = diff_bars(base(name), got)
            row(name, f, moved, f"{worst_gap(base(name), got):.3e}", mask)

    head("D3. Blind to the AMPLITUDE of the returns, not to their ORDER")
    win, bars = windows(FRAMES["walk"])
    idx = list(range(0, win.shape[0], 3))
    mine = [shipped_on(win[i]) for i in idx]
    for f in (0.5, 2.0, 10.0):
        other = [value_def(win[i] * f) for i in idx]
        row(f"returns x{f}", f"moved {diff_bars(mine, other, tol=1e-12)[0]}"
            f" of {len(idx)}", f"max |gap| {worst_gap(mine, other):.3e}")
    rng = np.random.default_rng(5)
    other = [value_def(rng.permutation(win[i])) for i in idx]
    row("the same returns SHUFFLED",
        f"moved {diff_bars(mine, other, tol=1e-12)[0]} of {len(idx)}",
        f"Spearman {spearman(mine, other):+.4f}")

    head("D4. 0 < fires < n, and not constant")
    row("frame", "fired", "of", "distinct values", "max - min")
    for name in FRAMES:
        s = base(name)
        a = s.dropna().to_numpy()
        row(name, int(s.notna().sum()), len(s), len(set(a.tolist())),
            f"{a.max() - a.min():.6f}")


def section_e():
    head("E. Gate E -- PENDING (run by issue-solver after this session)")
    print("The harness needs the private Backtesting engine and the 827 MB")
    print("BIST cache; this session may not touch ../Backtesting at all.")
    print()
    print("The 2026-10-24 screen measured the PROTOTYPE -- the GPL-3.0")
    print("reference's column through pycatch22 -- not this port:")
    row("prototype pooled max |rho|", "0.0595 vs Dist_from_High_252_pct",
        "n = 389,949")
    row("prototype per-frame max median", "0.0742", "-> SHIP")
    row("next comparators", "drawdown_DD_PCT 0.0568, drawdown_DD_LOG 0.0568")
    row("fork overlap (stage 2, 12 frames)",
        "0.0596 vs covariance:COV_30_1", "per-frame max median 0.0854")

    head("E1. In-fork overlap, measured HERE (synthetic frames, not Gate E)")
    print("Spearman of this column against every OTHER statistics column")
    print("this fork registers that scores -- price-level ones included,")
    print("there is no tag filter here -- on the six synthetic frames. Not")
    print("Gate E -- 6 synthetic frames, not 89 BIST ones, and a fraction of")
    print("the comparators -- but it is what can be measured without the")
    print("engine, and a restatement would show up here too.")
    cols = {}
    for name in FRAMES:
        f = FRAMES[name]
        df = pd.DataFrame({"open": f, "high": f * 1.01, "low": f * 0.99,
                           "close": f, "volume": 1e6})
        mine = base(name)
        for ind in sorted(ta.Category["statistics"]):
            if ind == "c22_ami2":
                continue
            try:
                got = getattr(df.ta, ind)()
            except Exception:
                continue
            frames = got if isinstance(got, pd.DataFrame) else \
                pd.DataFrame({got.name: got})
            for c in frames.columns:
                rho = spearman(mine, frames[c])
                if math.isnan(rho):
                    continue
                cols.setdefault(c, []).append((abs(rho), name))
    pooled = sorted(((max(v)[0], float(np.median([x[0] for x in v])),
                      max(v)[1], c) for c, v in cols.items()), reverse=True)
    row("comparator columns scored", len(cols))
    row("comparator", "max |rho| over the frames", "on which frame",
        "median |rho| over the frames")
    for mx, md, fr, c in pooled[:12]:
        row(c, f"{mx:.4f}", fr, f"{md:.4f}")
    row("⚠ the per-frame MEDIAN is the quantity the r3-perframe-0.90 band"
        " uses", f"largest here {max(p[1] for p in pooled):.4f}")

    head("E2. Against the two catch22 siblings in this fork")
    for sib in ("c22_ami_timescale", "c22_periodicity"):
        rhos = []
        for name in FRAMES:
            rhos.append(abs(spearman(base(name),
                                     getattr(ta, sib)(FRAMES[name]))))
        row(sib, f"max |rho| {np.nanmax(rhos):.4f}",
            f"median {np.nanmedian(rhos):.4f}")

    head("E4. OWED RULE -- two catch22 relatives that are not in this tree")
    print("Issue #132 (`SB_MotifThree_quantile_hh`, the entropy of 2-letter")
    print("words in a 3-quantile return alphabet) and issue #129")
    print("(`SB_TransitionMatrix_quantile_3`, the same window's lag-1")
    print("transition matrix) both BIN the same 100 returns and count LAGGED")
    print("PAIRS, which is this column's construction with a different")
    print("alphabet and a different lag. Neither exists in `Category`, so")
    print("neither Gate E nor section E1 can see them.")
    print()
    print("These are PROXIES written here from the features' descriptions, to")
    print("price the overlap before those ports land -- not ports, and not")
    print("Gate E. #132's proxy is the entropy of the 9 two-letter word")
    print("frequencies of the 3-quantile alphabet at lag 1; #129's is the")
    print("trace of the covariance of that alphabet's 3x3 transition matrix's")
    print("columns.")

    def _symbols(w, q=3):
        cut = np.quantile(w, [i / q for i in range(1, q)])
        return np.searchsorted(cut, w, side="right")

    def proxy_132(w):
        s = _symbols(w)
        code = s[:-1] * 3 + s[1:]
        p = np.bincount(code, minlength=9) / float(code.size)
        p = p[p > 0]
        return float(-np.sum(p * np.log(p)))

    def proxy_129(w):
        s = _symbols(w)
        t = np.zeros((3, 3))
        for a, b in zip(s[:-1], s[1:]):
            t[a, b] += 1.0
        t /= float(s.size - 1)
        return float(np.trace(np.cov(t, rowvar=False)))

    row("relative", "frame", "|rho| vs C22AMI2_100")
    for label, fn in (("#132 proxy (word entropy)", proxy_132),
                      ("#129 proxy (transition trace)", proxy_129)):
        rhos = []
        for name in FRAMES:
            win, bars = windows(FRAMES[name])
            mine = [float(base(name).iloc[int(bars[i])])
                    for i in range(0, win.shape[0], 3)]
            other = [fn(win[i]) for i in range(0, win.shape[0], 3)]
            rho = abs(spearman(mine, other))
            rhos.append(rho)
            row(label, name, f"{rho:.4f}")
        row(label, "ALL SIX", f"max {np.nanmax(rhos):.4f}",
            f"median {np.nanmedian(rhos):.4f}")
    print()
    print("THE RULE: when issue #132 or #129 is ported, it is measured")
    print("against C22AMI2_100 before it ships -- by the stage-2 fork-overlap")
    print("screen (scale-free Category outputs at defaults) or by re-running")
    print("this section with the new column in Category. ⚠ NOT by Gate E:")
    print("its 687 comparators are the engine's compute_all and the")
    print("ml_features manifest, which do not include this fork's own")
    print("columns. The per-frame figures above are the prior, and a pooled")
    print("|rho| at or above 0.90, or a top-5 per-frame median at or above")
    print("0.90 -- the r3-perframe-0.90 line -- between either of them and")
    print("this column means one of the two is a restatement and must be")
    print("reverted or waived.")


def section_g():
    head("G. The floor, and what it buys")
    row("NOISE_ULPS x eps", f"{NOISE_FLOOR:.6e}")
    print("The floor bounds the window's RETURN standard deviation, the same")
    print("quantity the z-score divides by: one number doing two jobs.")
    row("frame", "min window sd", "times the floor")
    for name in FRAMES:
        win, _ = windows(FRAMES[name])
        sd = float(win.std(axis=1, ddof=ZSCORE_DDOF).min())
        row(name, f"{sd:.3e}", f"{sd / NOISE_FLOOR:.3e}")
    for label, frame in (("geometric ladder", ladder()),
                         ("one kurus a bar", kurus_path()),
                         ("1-ulp step at 1e6", _ulp_frame())):
        win, _ = windows(frame)
        sd = win.std(axis=1, ddof=ZSCORE_DDOF)
        row(label, f"max window sd {np.nanmax(sd):.3e}",
            f"times the floor {np.nanmax(sd) / NOISE_FLOOR:.3e}")
    print("What the ladder reads UNGUARDED, which is why the floor is here.")
    print("Measured on EVERY window, through the module's own source with the")
    print("floor removed (the `no-floor` mutant), not on a sample:")
    lad = ladder()
    win, _ = windows(lad)
    unguarded = np.asarray(mutant("no-floor")(lad), float)
    live = unguarded[~np.isnan(unguarded)]
    row("geometric ladder, unguarded", f"fires {live.size} of {len(lad)}",
        f"min {live.min():.4f}", f"median {np.median(live):.4f}",
        f"max {live.max():.4f}")
    row("guarded", f"fires {int(c22_ami2(lad).notna().sum())}")
    counts = [len(set(win[i].tolist())) for i in range(win.shape[0])]
    row("distinct returns per window", f"min {min(counts)}",
        f"max {max(counts)}")
    sd = win.std(axis=1, ddof=ZSCORE_DDOF)
    row("window sd", f"min {sd.min():.3e}", f"max {sd.max():.3e}",
        f"the floor is {NOISE_FLOOR:.3e}")
    vals = [value_def(win[i]) for i in range(0, win.shape[0], 199)]
    row("the same, sampled every 199 windows by the plain-Python spelling",
        f"{[round(v, 4) for v in vals]}")

    print("And the 1-ulp frame, the same way: EVERY window, through the")
    print("`no-floor` mutant. Only the 100 windows that hold the step have")
    print("any variation at all; the rest are flat and blank under any rule.")
    ulp = _ulp_frame()
    unguarded = np.asarray(mutant("no-floor")(ulp), float)
    live = unguarded[~np.isnan(unguarded)]
    row("1-ulp step at 1e6, unguarded", f"fires {live.size} of {len(ulp)}",
        f"min {live.min():.6f}", f"median {np.median(live):.6f}",
        f"max {live.max():.6f}")
    row("guarded", f"fires {int(c22_ami2(ulp).notna().sum())}")


def section_h():
    head("H. Bad data, the guard band and the wiring")
    row("bad close", "blank bars >= length", "first", "last")
    for bad in (np.nan, np.inf, -np.inf, 0.0, -5.0, 1e-310):
        f = FRAMES["walk"].copy()
        f.iloc[700] = bad
        s = c22_ami2(f)
        blank = np.where(s.isna().to_numpy())[0]
        after = blank[blank >= LENGTH]
        row(repr(bad), after.size, after.min() if after.size else "-",
            after.max() if after.size else "-")
    for label, lo, hi in (("ratio 1e400 (overflows)", 1e-300, 1e100),
                          ("ratio 1e200 (finite return)", 1e-100, 1e100),
                          ("ratio 1e77", 1e-50, 1e27)):
        f = FRAMES["walk"].copy()
        f.iloc[700] = lo
        f.iloc[701] = hi
        s = c22_ami2(f)
        blank = np.where(s.isna().to_numpy())[0]
        after = blank[blank >= LENGTH]
        without = np.asarray(mutant("no-overflow-guard")(f), float)
        saved = np.where(np.isnan(s.to_numpy()) & ~np.isnan(without))[0]
        row(label, f"return {float(f.iloc[701] / f.iloc[700] - 1.0):.3e}",
            f"blank {after.size}",
            f"without the isfinite limb those bars read "
            f"{sorted(set(np.round(without[saved], 9).tolist()))[:3]}"
            if saved.size else "the limb is inert here")

    row("n", "result")
    for n in (99, 100, 101, 102):
        s = c22_ami2(FRAMES["walk"].iloc[:n])
        row(n, "None" if s is None else f"fired {int(s.notna().sum())}")
    row("length", "name", "fired")
    for length in (None, 0, 1, MIN_LENGTH - 1, MIN_LENGTH, 250, 250.7):
        s = c22_ami2(FRAMES["walk"], length=length)
        row(repr(length), s.name, int(s.notna().sum()))
    s = c22_ami2(FRAMES["walk"], offset=2)
    row("offset=2 shifts the column",
        same(s.to_numpy()[2:], base("walk").to_numpy()[:-2]))
    s = c22_ami2(FRAMES["walk"], fillna=-1)
    row("fillna=-1", f"blanks {int(s.isna().sum())}",
        f"filled {int((s == -1).sum())}")
    row("five wiring touch points",
        Path(MODULE.__file__).exists(),
        hasattr(ta.statistics, "c22_ami2"),
        "c22_ami2" in ta.Category["statistics"],
        hasattr(ta.core.AnalysisIndicators, "c22_ami2"),
        (ROOT / "tests" / "test_c22_ami2.py").exists())
    row("Category total", sum(len(v) for v in ta.Category.values()),
        "statistics", len(ta.Category["statistics"]))
    # The size of the sweep `tests/test_c22_ami2.py::test_the_reference_
    # implementation_is_not_imported_by_shipped_code` makes, printed so the
    # receipt's figure cannot be a count taken before this module existed.
    files = sorted((ROOT / "pandas_ta").rglob("*.py"))
    hits = [p for p in files
            if any((s.strip().startswith(("import ", "from ")))
                   and "catch22" in s.replace("c22", "")
                   for s in p.read_text(encoding="utf-8").splitlines())]
    row(".py files under pandas_ta/", len(files),
        "that import the GPL-3.0 reference", len(hits))


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

    probe = pycatch22.catch22_all(
        [float(v) for v in returns(FRAMES["walk"])[:LENGTH]],
        short_names=True)
    names = [n for n in probe["short_names"] if "AMI" in n.upper()]
    row("catch22_all short names matching 'AMI'", names)
    want = [n for n in names if "ami2" in n or "even" in n]
    which = probe["short_names"].index(want[0]) if want else None
    row("the index this section reads", which, want[0] if want else None)
    direct = None
    for attr in ("CO_HistogramAMI_even_2_5", "CO_HistogramAMI_even_5bin_ami2"):
        if hasattr(pycatch22, attr):
            direct = getattr(pycatch22, attr)
            row("direct entry point", attr)
            break
    if direct is None:
        row("direct entry point", "none found; catch22_all only")

    def ref_all(window):
        out = pycatch22.catch22_all([float(v) for v in window])
        return float(out["values"][which])

    head("P0. Entry points, and whether the reference z-scores for us")
    win, _ = windows(FRAMES["walk"])
    w = win[0]
    z = (w - w.mean()) / w.std(ddof=ZSCORE_DDOF)
    row("catch22_all on the raw window", f"{ref_all(w):.12f}")
    if direct is not None:
        row("direct on the raw window", f"{float(direct(list(map(float, w)))):.12f}")
        row("direct on the z-scored window",
            f"{float(direct(list(map(float, z)))):.12f}")
    row("catch22_all on the z-scored window", f"{ref_all(z):.12f}")
    row("this port", f"{shipped_on(w):.12f}")

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
    print(f"all {len(every)} disagreements beyond 1e-12"
          f" (frame, bar, mine, reference):")
    for cell in every[:40]:
        print(" ", cell)

    head("P1b. WHICH reading the reference implements")
    print("Every third window above, scored by this port and by the other")
    print("defensible readings of the same definition. The count is windows")
    print("where that reading equals the REFERENCE to 1e-12.")
    def variants(w):
        return {
            "shipped (outer-edge buffer, Miller-Madow, ddof 1)":
                shipped_on(w),
            "shipped, plain-Python spelling": value_def(w),
            "the buffer pushed into the interior edges too":
                value_def(w, edges="uniform"),
            "no bias correction (raw plug-in MI)":
                value_def(w, correct=False),
            "no correction AND the interior buffer":
                value_def(w, edges="uniform", correct=False),
            "population z-score (ddof 0)": value_def(w, ddof=0),
            "range from the lagged-from limb, not the window":
                value_def(w, binsource="y1"),
            "floor-division bin assignment": value_def(w, assign="floor"),
            "tau = 1": value_def(w, tau=1),
            "10 bins": value_def(w, bins=10),
        }
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
            r = ref_all(w)
            n_scored += 1
            vs = variants(w)
            for key, val in vs.items():
                tally[key] = tally.get(key, 0) + int(
                    (math.isfinite(val) and abs(val - r) <= 1e-12)
                    or (math.isnan(val) and math.isnan(r)))
            if abs(mine - r) > 1e-12:
                detail.append({
                    "frame": name, "bar": int(bars[i]), "mine": mine,
                    "ref": r,
                    "readings that match the reference":
                        [k for k, v in vs.items()
                         if math.isfinite(v) and abs(v - r) <= 1e-12],
                })
    row("windows scored by both", n_scored,
        f"readings compared: {len(tally)}")
    for key, hit in sorted(tally.items(), key=lambda kv: -kv[1]):
        row(key, f"{hit} / {n_scored}")
    if detail:
        print(f"All {len(detail)} disagreements on this subsample:")
        for d in detail[:40]:
            print(" ", d)

    head("P1c. HOW the estimator was identified: a battery fitted to the"
         " reference")
    print("The reference returns NEGATIVE values, and a mutual information is")
    print("a Kullback-Leibler divergence and cannot be negative -- so the")
    print("quantity it reports is not a plug-in MI, and this port's FIRST")
    print("reading (a plug-in MI over bins evenly spaced across the padded")
    print("range) could not be right. This section is how the shipped reading")
    print("was found: a battery of candidate formulas, each DERIVED here from")
    print("named estimators and from the readings of the definition's own")
    print("sentence, fitted to the reference as a black box. The GPL-3.0")
    print("source was not read; the winner is the one that reproduces it.")
    for name in ("walk", "penny"):
        win, bars = windows(FRAMES[name])
        for i in (0, 500):
            w = win[i]
            idx, _ = shipped_bins(w)
            counts = np.zeros((NUM_BINS, NUM_BINS), dtype=np.int64)
            for a, c in zip(idx[:LENGTH - TAU], idx[TAU:]):
                counts[a, c] += 1
            print(f"{name} bar {int(bars[i])}: counts")
            for r_ in counts:
                print("   ", r_.tolist())
            row("  mine", f"{shipped_on(w):.12f}", "reference",
                f"{ref_all(w):.12f}", "difference",
                f"{shipped_on(w) - ref_all(w):.12f}")
            for key, val in sorted(ami_candidates(idx, LENGTH).items()):
                row("  " + key, f"{val:.12f}",
                    f"gap to reference {val - ref_all(w):+.3e}")

    tally: dict[str, int] = {}
    resid: dict[str, list] = {}
    n_scored = 0
    for name in FRAMES:
        win, _ = windows(FRAMES[name])
        for i in range(0, win.shape[0], 3):
            w = win[i]
            if math.isnan(shipped_on(w)):
                continue
            r = ref_all(w)
            n_scored += 1
            for key, val in ami_candidates(
                    shipped_bins(w)[0], LENGTH).items():
                tally[key] = tally.get(key, 0) + int(abs(val - r) <= 1e-12)
                resid.setdefault(key, []).append(val - r)
            for key, val in ami_candidates(
                    uniform_bins(w), LENGTH, tag="interior buffer, ").items():
                tally[key] = tally.get(key, 0) + int(abs(val - r) <= 1e-12)
                resid.setdefault(key, []).append(val - r)
    row("windows scored", n_scored, f"candidates: {len(tally)}")
    row("candidate", "equal to the reference", "mean residual",
        "max |residual|")
    for key, hit in sorted(tally.items(), key=lambda kv: -kv[1]):
        rs = np.asarray(resid[key])
        row(key, f"{hit} / {n_scored}", f"{rs.mean():+.6f}",
            f"{np.abs(rs).max():.6f}")

    head("P2. The windows this port BLANKS and the reference scores")
    for label, frame in (("geometric ladder", ladder()),
                         ("one kurus a bar", kurus_path()),
                         ("flat run from bar 400", _flat_run())):
        win, _ = windows(frame)
        blank = scored = 0
        vals = []
        for i in range(0, win.shape[0], 23):
            if math.isnan(shipped_on(win[i])):
                blank += 1
                try:
                    v = ref_all(win[i])
                except Exception:
                    continue
                if math.isfinite(v):
                    scored += 1
                    vals.append(round(v, 6))
        row(label, f"blank here {blank}", f"scored by the reference {scored}",
            f"values {sorted(set(vals))[:6]}")


def section_t():
    head("T. Chunking and cost")
    want = base("walk")
    for budget in (100, 400, 1024):
        MODULE.CHUNK_VALUES = budget
        try:
            got = c22_ami2(FRAMES["walk"])
        finally:
            MODULE.CHUNK_VALUES = CHUNK_VALUES
        row(f"CHUNK_VALUES = {budget}", "bit-equal" if same(want, got)
            else "MOVED")
    big = walk(n=400_000, seed=3)
    tracemalloc.start()
    t0 = time.perf_counter()
    s = c22_ami2(big)
    dt = time.perf_counter() - t0
    peak = tracemalloc.get_traced_memory()[1]
    tracemalloc.stop()
    row("n = 400,000", f"{dt:.1f} s", f"traced peak {peak / 1e6:.1f} MB",
        f"fired {int(s.notna().sum())}")


def section_z():
    head("Z. Summary")
    row("column", f"C22AMI2_{LENGTH}")
    row("derived bounds at length 100",
        f"[{ami_bounds(LENGTH)[0]:.6f}, {ami_bounds(LENGTH)[1]:.6f}] nats")
    for name in FRAMES:
        a = base(name).dropna().to_numpy()
        row(name, f"fired {a.size}", f"median {np.median(a):.6f}",
            f"min {a.min():.6f}", f"max {a.max():.6f}")
    row("Gate E", "PENDING -- run by issue-solver after this session")


# --------------------------------------------------------------- Gate B tools
MUTANTS = {
    "write-back-dated": (
        "out[length + a:length + b]",
        "out[length - 1 + a:length - 1 + b]",
        "writes each chunk one bar early"),
    "window-one-ahead": (
        "win = sliding_window_view(r, length)",
        "win = sliding_window_view(r, length + 1)[:, 1:]",
        "each window reads one return from the future"),
    "window-ten-ahead": (
        "win = sliding_window_view(r, length)",
        "win = sliding_window_view(r, length + 10)[:, 10:]",
        "each window reads ten returns from the future"),
    "returns-rolled": (
        "r = np.where(np.isfinite(r), r, np.nan)",
        "r = np.roll(np.where(np.isfinite(r), r, np.nan), -1)",
        "the whole return series is shifted one bar earlier"),
    "mask-back-dated": (
        "r = np.where(np.isfinite(r), r, np.nan)",
        "r = np.where(np.isfinite(np.roll(r, -1)), r, np.nan)",
        "the bad-data MASK reads the next bar"),
    "chunk-wide-demean": (
        "z = (block - block.mean(axis=1, keepdims=True)) / sd[:, None]",
        "z = (block - block.mean()) / sd[:, None]",
        "each row is centred on the whole CHUNK's mean"),
    "chunk-wide-sd": (
        "sd = block.std(axis=1, ddof=ZSCORE_DDOF)",
        "sd = np.full(block.shape[0], block.std(ddof=ZSCORE_DDOF))",
        "each row is scaled by the whole CHUNK's sd"),
    "chunk-wide-extremes": (
        "        lo = z.min(axis=1)\n        hi = z.max(axis=1)",
        "        lo = np.full(rows, z.min())\n"
        "        hi = np.full(rows, z.max())",
        "the bin edges come from the whole CHUNK's extremes"),
    "no-bias-correction": (
        "    ami = plug - (occupied - rows_used - cols_used + 1) / (2.0 * pairs)",
        "    ami = plug",
        "drops the Miller-Madow correction"),
    "joint-transposed": (
        "    code = idx[:, :pairs] * NUM_BINS + idx[:, TAU:]",
        "    code = idx[:, TAU:] * NUM_BINS + idx[:, :pairs]",
        "swaps which limb indexes the rows of the joint table"),
    "no-overflow-guard": (
        "bad |= ~(sd > NOISE_FLOOR) | ~np.isfinite(sd)",
        "bad |= ~(sd > NOISE_FLOOR)",
        "drops the `isfinite(sd)` limb"),
    "no-floor": (
        "bad |= ~(sd > NOISE_FLOOR) | ~np.isfinite(sd)",
        "bad |= ~(sd > 0.0)",
        "drops the noise floor, keeping only sd > 0"),
}


def mutant(name):
    """Read this module off disk, edit one write, exec it in memory."""
    old, new = MUTANTS[name][0], MUTANTS[name][1]
    assert SRC.count(old) == 1, (name, SRC.count(old))
    ns: dict = {}
    exec(compile(SRC.replace(old, new), f"<mutant {name}>", "exec"), ns)
    return ns["c22_ami2"]


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


def _flat_run(n=700, at=400):
    c = FRAMES["walk"].to_numpy().copy()
    c[at:] = c[at - 1]
    return pd.Series(c[:n])


def _ulp_frame(n=N, level=1e6, at=700):
    c = np.full(n, level)
    c[at:] = np.nextafter(level, 2 * level)
    return pd.Series(c)


SECTIONS = {
    "S": section_s, "A": section_a, "B": section_b, "C": section_c,
    "D": section_d, "E": section_e, "G": section_g, "H": section_h,
    "P": section_p, "T": section_t, "Z": section_z,
}
DEFAULT = ["S", "A", "B", "C", "D", "E", "G", "H", "T", "Z"]


if __name__ == "__main__":
    want = [a.upper() for a in sys.argv[1:]] or DEFAULT
    for key in want:
        if key not in SECTIONS:
            raise SystemExit(f"unknown section {key!r};"
                             f" pick from {list(SECTIONS)}")
        SECTIONS[key]()
