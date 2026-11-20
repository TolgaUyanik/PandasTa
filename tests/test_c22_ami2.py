# -*- coding: utf-8 -*-
"""C22-AMI2: `c22_ami2`, catch22's 5-bin automutual information of the last
100 daily returns at lag 2 (issue #127).

Every number here was measured by `docs/measure_c22_ami2.py` on this machine;
the receipt is `docs/C22Ami2Measured.md`. What is pinned, in order of how much
it would hurt to lose:

1. **THE TWO READINGS THAT DECIDE THE COLUMN.** The definition leaves two
   things open and both were settled by measurement:
   * **where the 0.1 buffer goes.** The bin edges are evenly spaced between
     the window's own min and max with only the two OUTER ones pushed out, so
     the buffer is there for INCLUSION and cannot move an interior edge.
     Pushing it into the interior edges too -- evenly spaced over
     `[min - 0.1, max + 0.1]`, the other reading of the same sentence, and
     this port's FIRST one -- moves 246 to 463 of 467 windows on each
     stochastic frame, by up to 0.070 nats, Spearman +0.73 to +0.88.
   * **the MILLER-MADOW bias correction.** The column is the corrected
     estimate. Dropping it moves 467 of 467 sampled windows on five frames
     and 436 of 467 on the Student-t one, by up to 0.0816 nats. The 31 it
     does not move are exact, not rounding: the correction is an integer
     multiple of 1/196 and is 0 where the table's occupied cells, rows and
     columns satisfy `cells = rows + cols - 1`.
   Of 18 candidate readings fitted to the GPL-3.0 reference as a black box
   over 2,802 windows, the shipped one reproduces it on **2,802**, the
   interior-buffer reading on 763, the uncorrected plug-in on 31, the rest on
   21 or fewer (receipt §P1c). That is the evidence the definition was read
   right, and it is the one thing in this file that cannot be re-derived from
   the module.
2. **The column IS the one the 2026-10-24 screen measured.** Over every
   window of six frames -- 8,400 -- it equals the reference to 1e-12 on
   8,400 (worst gap 2.2e-16) and bit-exactly on 2,299 of them. Unlike
   `c22_periodicity`, whose port disagrees with its own reference on 13 of
   8,400 windows beyond 1e-12, this one disagrees on none, so the screen's
   Gate E expectation transfers here.
3. **It can be NEGATIVE, and that is the estimator.** The derived bounds at
   `length` 100 are `[-0.0816, 1.6298]` -- an ENCLOSURE, neither endpoint
   claimed reachable; the measured range over five stochastic frames is
   -0.0329 to 0.2066. On 400 independent normal windows drawn through the
   shipped kernel the column reads a median of +0.0284 and is negative on
   17.3% (receipt §A10b); on §A10's separate 400, drawn through the
   plain-Python spelling so the two readings share a draw, it is +0.0282 and
   15.5% and the UNCORRECTED plug-in reads +0.086 -- its own bias,
   `(5-1)**2/(2*98)` = 0.0816 -- which is what the correction is for. ⚠ All
   of those are `length`-100 figures: the
   correction scales as `1/(2(length-2))`, so the iid median is +0.228 at
   `length` 27 and +0.008 at 250, and `MIN_LENGTH` = 27 is a floor rather
   than a recommendation.
4. **The exact oracle agrees.** The bin edges are affine in the window's own
   extremes, so the z-score's irrational `sd` cancels out of every membership
   test and the whole 5x5 count matrix is decided by exact rational
   comparisons: 90 of 90 sampled windows come out with the same matrix, value
   gap 2.2e-16. Four more spellings (plain Python with `fsum`, the entropy
   identity, `np.histogram2d`, `sklearn.metrics.mutual_info_score`) agree to
   1.6e-15 over 1,200 windows each.
5. **Two EXACT laws.** Returns alternating +-2% make `r[t+2] == r[t]`, so the
   joint table is a bijection, the MI is `ln 2` and the correction ADDS
   `(k-1)/196` over `k = 2` occupied cells: all 1,400 bars read
   0.698249221376. A period-4 cosine has `k = 3` and reads 1.049820721962.
6. **Three knobs are INERT, for one reason.** The interior edges are an
   affine function of the window's own extremes, so any positive affine map
   of the window leaves every bin assignment alone: on each of six frames, 0
   of 467 windows move under the population z-score, under NO z-score, under
   a +1 shift, or under a buffer of 0, 0.01, 1 or 1e6. ⚠ The invariance needs
   a finite `sd`, which is why the `isfinite(sd)` limb exists; two Gate B
   mutants are DEAD for the same reason (item 8); and the range being taken
   from the whole window rather than from one limb is NOT inert (5 to 9 of
   200).
7. **Scale-free, bit-identically, and not only under binary factors.** The
   price enters only as `c[t] / c[t-1]`, so x8, x64 and 2**+-40 are
   bit-identical by construction -- but so are x10, x3.7, x0.1 and
   x1.0000001, because the value is a function of a 5x5 matrix of INTEGER
   counts and the measured margin to the nearest bin edge is 1.25e-06.
8. **Causality.** 0 of 35 offsets leak on each of six frames with eight
   splices apiece, and 0 of 35 at `length` 27, 120 and 250. Twelve mutants
   are read off the module's own source, edited and exec'd in memory: the
   four look-aheads are caught at **35 of 35** offsets each -- this column
   ties on only 7.2% to 21.7% of neighbouring bar pairs (7.4% to 21.5% with
   AVX-512 / AVX2 / FMA3 off, which is why the test asserts < 40%), so there
   is almost
   nowhere for a one-bar shift to hide -- the mask mutant is caught 12 of 12
   on a dirty frame, and `chunk-wide-extremes` at 30 of 35. The three dead
   mutants are named rather than dropped: two are the affine invariance of
   item 6, and the third transposes the joint table, which a symmetric
   quantity cannot see beyond the order of its 25 logarithms (5.6e-17). The
   remaining three (`no-bias-correction`, `no-overflow-guard`, `no-floor`)
   are not look-aheads: they change VALUES, each has its own test, and a
   sweep that caught them would mean the sweep is measuring something other
   than causality.
9. **One blanking rule with an asymmetric cost.** A window is NaN unless its
   return standard deviation clears 9.09e-13. It is inert on anything with
   noise in it (0 of 1,400 bars differ from the unguarded spelling on each of
   six frames) and it empties an exactly geometric ladder, which unguarded
   fires on all 1,400 bars reading -0.0199 to 0.0932 -- inside the walk
   frame's own range -- and a 1-ulp step at 1e6, whose 100 step-holding
   windows read 0.000000 to 0.000105 (both measured on every window through
   the `no-floor` mutant, not sampled). ⚠ It does NOT empty a
   deterministically smooth path: a price rising one kurus a bar fires on all
   1,400 bars and reads 1.3432, near the top of the scale, where
   `c22_periodicity` blanks.
10. **Gate E is MEASURED and says SHIP.** Run `is127-c22_ami2-23b6686b` of
    2026-11-20: pooled max |rho| 0.0594 vs `Dist_from_High_252_pct`
    (n = 389,949), per-frame max median 0.0742 vs `natr`, 0 of 89 frames at
    0.90 -- so no column is removed and no waiver is needed. The tests pin the
    ledger row's identity and the BANDS rather than the digits, and they pin
    Gate C's real-data limb from the same run (389,949 of 398,849 pooled BIST
    bars non-NaN, 389,949 non-zero), because every OTHER count in this file is
    SYNTHETIC.

Not pinned on purpose: exact counts of distinct values, exact bars-moved
counts, and any value to 1e-15. The counts are robust to the CPU dispatch
(item 7) but the sum of 25 logarithms is not, so the tests pin bounds,
tolerances and bands and the docstrings state the local figure.
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
from pandas_ta.statistics.c22_ami2 import (
    BUFFER, CHUNK_VALUES, MAX_AMI, MIN_LENGTH, NOISE_FLOOR, NUM_BINS, TAU,
    ZSCORE_DDOF, _ami_rows, ami_bounds, c22_ami2)

ROOT = Path(__file__).resolve().parent.parent
MODULE = importlib.import_module("pandas_ta.statistics.c22_ami2")
SRC = Path(MODULE.__file__).read_text(encoding="utf-8")
LENGTH = 100
PAIRS = LENGTH - TAU

#: Strides for the oracles that are too slow for all 1,400 windows.
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


def alternating(n=1500, amp=0.02, level=100.0):
    """`r[t + 2] == r[t]` exactly, so the lag-2 table is a bijection."""
    r = amp * np.where(np.arange(n) % 2 == 0, 1.0, -1.0)
    return Series(level * np.cumprod(1.0 + r))


def ladder(n=1500, step=0.01, start=100.0):
    return Series(start * (1.0 + step) ** np.arange(n, dtype=float))


def kurus_path(n=1500, start=100.0, step=0.01):
    """A price rising by exactly one kurus a bar."""
    return Series(start + step * np.arange(n, dtype=float))


FRAMES = {
    "walk": walk(),
    "tick-rounded": tick_rounded(),
    "penny": penny(),
    "ar1": ar1(),
    "cosine": cosine_returns(),
    "student-t": student_t(),
}
#: The five frames whose returns are not deterministic. The 20-bar cosine
#: frame takes only 8 distinct values over 1,400 bars, so it is excluded from
#: the "a reading moved" assertions and named in them instead.
STOCHASTIC = [k for k in FRAMES if k != "cosine"]
_BASE = {}


def base(name):
    if name not in _BASE:
        _BASE[name] = c22_ami2(FRAMES[name])
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


def diff_bars(a, b, tol=0.0):
    x, y = np.asarray(a, float), np.asarray(b, float)
    both = ~np.isnan(x) & ~np.isnan(y)
    return (int(np.sum(np.abs(x[both] - y[both]) > tol)),
            int(np.sum(np.isnan(x) != np.isnan(y))))


def worst_gap(a, b):
    x, y = np.asarray(a, float), np.asarray(b, float)
    both = ~np.isnan(x) & ~np.isnan(y)
    return float(np.max(np.abs(x[both] - y[both]))) if both.any() else 0.0


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
def shipped_on(window):
    """One window through the shipped row kernel."""
    w = np.asarray(window, float)
    return float(_ami_rows(w.reshape(1, -1))[0])


def shipped_bins(window):
    """The bin index of every point and the six edges, as shipped."""
    w = np.asarray(window, float)
    sd = float(w.std(ddof=ZSCORE_DDOF))
    z = (w - w.mean()) / sd
    lo, hi = float(z.min()), float(z.max())
    width = (hi - lo) / NUM_BINS
    idx = np.zeros(w.size, dtype=np.int64)
    for i in range(1, NUM_BINS):
        idx += z >= lo + i * width
    edges = [lo + i * width for i in range(NUM_BINS + 1)]
    edges[0] -= BUFFER
    edges[-1] += BUFFER
    return idx, np.array(edges)


def counts_of(idx, tau=TAU, bins=NUM_BINS):
    out = np.zeros((bins, bins), dtype=np.int64)
    for a, c in zip(idx[:len(idx) - tau], idx[tau:]):
        out[a, c] += 1
    return out


def miller_madow(counts, pairs):
    c = np.asarray(counts)
    occ = float((c > 0).sum())
    occ_i = float((c.sum(axis=1) > 0).sum())
    occ_j = float((c.sum(axis=0) > 0).sum())
    return (occ - occ_i - occ_j + 1.0) / (2.0 * pairs)


def mi_from_counts(counts, pairs, how="direct", correct=True):
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
    """The definition re-spelled in plain Python, with one knob per reading
    section A of the receipt prices. `edges="outer"` and `correct=True` are
    the shipped ones; see `docs/measure_c22_ami2.py` for the full list."""
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
    else:
        b = [lo + i * (hi - lo) / bins for i in range(bins + 1)]
        b[0] -= buffer
        b[-1] += buffer

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

    idx = [which(v) for v in z]
    return mi_from_counts(counts_of(idx, tau=tau, bins=bins), n - tau,
                          how=how, correct=correct)


def exact_counts(window, ddof=ZSCORE_DDOF):
    """The 5x5 count matrix in EXACT rational arithmetic, or None.

    Every input double is a rational and the bin edges are affine in the
    window's own min and max, so the z-score's irrational `sd` cancels out of
    every membership test: `u / sd >= min(u) / sd + i (max(u) - min(u)) /
    (sd bins)` is `u >= min(u) + i (max(u) - min(u)) / bins`. Not one
    rounding happens here. `BUFFER` appears only in the two outer edges,
    which no point can be outside of.
    """
    y = [Fraction(float(v)) for v in window]
    n = len(y)
    mean = sum(y) / n
    u = [v - mean for v in y]
    if sum(v * v for v in u) == 0:
        return None
    mn, mx = min(u), max(u)
    idx = []
    for v in u:
        k = 0
        for i in range(1, NUM_BINS):
            if v >= mn + Fraction(i, NUM_BINS) * (mx - mn):
                k = i
        idx.append(k)
    return counts_of(np.asarray(idx))


def value_exact(window):
    """The value from the exact count matrix: the only roundings left are the
    logarithms, taken on exact rational ratios."""
    counts = exact_counts(window)
    if counts is None:
        return float("nan")
    pairs = int(counts.sum())
    ci, cj = counts.sum(axis=1), counts.sum(axis=0)
    out = 0.0
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


def law_value(window):
    """What the column must read when the lag-2 table is a BIJECTION: the
    marginal entropy plus `(k - 1) / (2 pairs)` over its `k` occupied cells."""
    idx, _ = shipped_bins(window)
    counts = counts_of(idx)
    k = int((counts > 0).sum())
    _, c = np.unique(idx[:len(idx) - TAU], return_counts=True)
    p = c / c.sum()
    return float(-np.sum(p * np.log(p))) + (k - 1) / (2.0 * PAIRS), k


@pytest.mark.parametrize("frame", list(FRAMES))
def test_bit_equal_to_the_exact_rational_oracle(frame):
    """Gate A's strongest limb: the count matrix with ZERO roundings.

    The value itself needs logarithms, so what is exact is the matrix that
    decides it -- and that is where a rounding could change an answer.
    Measured: 90 of 90 sampled windows across six frames agree matrix for
    matrix, and the values agree to 2.2e-16.
    """
    win, bars = windows(FRAMES[frame])
    ran = 0
    for i in range(0, win.shape[0], EXACT_STRIDE):
        idx, _ = shipped_bins(win[i])
        assert np.array_equal(exact_counts(win[i]), counts_of(idx)), \
            (frame, int(bars[i]))
        mine = float(base(frame).iloc[int(bars[i])])
        assert abs(mine - value_exact(win[i])) < 1e-14, (frame, int(bars[i]))
        ran += 1
    assert ran >= 14, ran


@pytest.mark.parametrize("how", ["plain-python", "entropy-identity",
                                 "histogram2d", "sklearn"])
@pytest.mark.parametrize("frame", list(FRAMES))
def test_the_same_quantity_spelled_four_other_ways_agrees(how, frame):
    """Four spellings that share no code with the module: plain Python with
    `math.fsum`, the algebraically identical `H(i) + H(j) - H(i, j)`,
    `np.histogram2d` for the binning and `sklearn.metrics.mutual_info_score`
    for the information. Measured over 1,200 windows each: max gap 1.1e-16,
    1.6e-15, 1.1e-16 and 1.2e-15."""
    if how == "sklearn" and importlib.util.find_spec("sklearn") is None:
        pytest.skip("sklearn is not installed")
    win, bars = windows(FRAMES[frame])
    worst = 0.0
    ran = 0
    for i in range(0, win.shape[0], WINDOW_STRIDE):
        w = win[i]
        mine = float(base(frame).iloc[int(bars[i])])
        if how == "plain-python":
            other = value_def(w)
        elif how == "entropy-identity":
            other = value_def(w, how="entropy")
        elif how == "histogram2d":
            _, e = shipped_bins(w)
            z = (w - w.mean()) / w.std(ddof=ZSCORE_DDOF)
            c, _, _ = np.histogram2d(z[:LENGTH - TAU], z[TAU:], bins=[e, e])
            other = mi_from_counts(c.astype(np.int64), PAIRS)
        else:
            from sklearn.metrics import mutual_info_score
            idx, _ = shipped_bins(w)
            other = float(mutual_info_score(idx[:LENGTH - TAU], idx[TAU:])) \
                - miller_madow(counts_of(idx), PAIRS)
        worst = max(worst, abs(mine - other))
        ran += 1
    assert ran >= 199, ran
    assert worst < 1e-13, (how, frame, worst)


def test_an_alternating_return_series_obeys_the_exact_bijection_law():
    """The first exact law. Returns alternating +-2% make `r[t+2] == r[t]`,
    so the lag-2 table is a bijection on `k = 2` occupied cells: the plug-in
    MI is the marginal entropy `ln 2` and the Miller-Madow term ADDS
    `(k-1)/196`. Measured: every one of 1,400 bars reads 0.698249221376, one
    value, and `ln 2 + 1/196` is 0.6982492213758.

    This is also the one test that would catch a sign slip in the correction:
    the uncorrected value here is `ln 2` and the shipped one is above it.
    """
    s = c22_ami2(alternating()).dropna()
    assert int(s.size) == 1400
    a = s.to_numpy()
    assert float(a.max() - a.min()) < 1e-12
    want = math.log(2.0) + 1.0 / (2.0 * PAIRS)
    assert abs(float(a[0]) - want) < 1e-12, (float(a[0]), want)
    assert float(a[0]) > math.log(2.0)
    win, bars = windows(alternating())
    for i in range(0, win.shape[0], 199):
        law, k = law_value(win[i])
        assert k == 2
        assert abs(float(s.iloc[i]) - law) < 1e-12


def test_a_period_four_cosine_obeys_the_same_law_on_three_cells():
    """The second exact law, on a different table. A period-4 cosine has
    `r[t+2] == -r[t]`, three distinct returns and `k = 3` occupied cells:
    measured 1.049820721962 on all 1,400 bars, which is the marginal entropy
    of {25, 49, 24}/98 plus 2/196."""
    s = c22_ami2(cosine_returns(period=4.0)).dropna()
    assert int(s.size) == 1400
    a = s.to_numpy()
    assert float(a.max() - a.min()) < 1e-12
    win, _ = windows(cosine_returns(period=4.0))
    for i in range(0, win.shape[0], 199):
        law, k = law_value(win[i])
        assert k == 3
        assert abs(float(s.iloc[i]) - law) < 1e-12
    assert 1.04 < float(a[0]) < 1.06


@pytest.mark.parametrize("frame", STOCHASTIC)
def test_the_edge_spelling_is_load_bearing(frame):
    """The reading a porter can get wrong, and the one this port got wrong
    first. The buffer belongs on the two OUTER edges only; pushing it into
    the interior edges as well moves 246 to 463 of 467 windows per stochastic
    frame and up to 0.070 nats. The bound here is far under the smallest of
    those because the exact count moves with the CPU dispatch.
    ⚠ The 20-bar cosine frame moves 0 and is excluded by name."""
    win, bars = windows(FRAMES[frame])
    idx = list(range(0, win.shape[0], 3))
    mine = [float(base(frame).iloc[int(bars[i])]) for i in idx]
    other = [value_def(win[i], edges="uniform") for i in idx]
    moved, mask = diff_bars(mine, other, tol=1e-12)
    assert moved >= 100, (frame, moved)
    assert mask == 0
    assert worst_gap(mine, other) > 0.01, frame


def test_the_interior_buffer_reading_is_inert_on_the_cosine_frame():
    """The other half of the measurement above, named rather than averaged
    in: on the 20-bar cosine frame the two edge spellings agree on all 467
    sampled windows, because that frame's returns are a lattice the bins
    separate the same way either way."""
    win, bars = windows(FRAMES["cosine"])
    idx = list(range(0, win.shape[0], 3))
    mine = [float(base("cosine").iloc[int(bars[i])]) for i in idx]
    other = [value_def(win[i], edges="uniform") for i in idx]
    assert diff_bars(mine, other, tol=1e-12)[0] == 0


@pytest.mark.parametrize("frame", list(FRAMES))
def test_the_bias_correction_is_load_bearing(frame):
    """Dropping the Miller-Madow term leaves the raw plug-in MI, which is a
    different column: the correction is up to 0.0816 nats (a full 5x5 table)
    and the mean over a stochastic frame is +0.055. It is measured through
    the module's own source -- a mutant with the correction removed -- so the
    claim is about the shipped code path and not about a re-spelling."""
    without = np.asarray(mutant("no-bias-correction")(FRAMES[frame]), float)
    mine = base(frame).to_numpy()
    moved, mask = diff_bars(mine, without, tol=1e-12)
    assert mask == 0
    assert moved >= 1300, (frame, moved)
    gap = worst_gap(mine, without)
    assert 0.01 < gap <= (NUM_BINS - 1) ** 2 / (2.0 * PAIRS) + 1e-12, gap
    # and the uncorrected column is always the LARGER of the two here
    assert float(np.nanmin(without - mine)) > -1e-12
    # ⚠ NOT every window: the correction is an integer multiple of
    # 1 / (2 * pairs) and is exactly 0 where the table's occupied cells, rows
    # and columns satisfy cells = rows + cols - 1. Measured at stride 3: 467
    # of 467 move on five frames and 436 of 467 on the student-t one, so the
    # bound above is 1300 of 1400 and not 1400.
    diffs = (without - mine)[~np.isnan(mine)]
    step = 1.0 / (2.0 * PAIRS)
    off_lattice = np.abs(diffs / step - np.round(diffs / step)).max()
    assert off_lattice < 1e-6, off_lattice
    if frame == "student-t":
        assert int(np.sum(np.abs(diffs) <= 1e-12)) >= 50, frame


@pytest.mark.parametrize("frame", list(FRAMES))
def test_the_z_score_and_its_divisor_are_inert(frame):
    """Three knobs that cannot matter, and the one reason they cannot: the
    interior edges are an affine function of the window's own extremes, so
    any positive affine map of the window leaves every bin assignment alone.
    Measured: 0 of 467 windows move under the population z-score (ddof 0),
    under NO z-score at all, or under a +1 shift. The reference
    implementation agrees -- it returns the same value for a window and for
    its z-score (receipt §P0)."""
    win, bars = windows(FRAMES[frame])
    idx = list(range(0, win.shape[0], 3))
    mine = [float(base(frame).iloc[int(bars[i])]) for i in idx]
    for label, other in (
            ("ddof 0", [value_def(win[i], ddof=0) for i in idx]),
            ("no z-score", [value_def(win[i], zscore=False) for i in idx]),
            ("shifted +1", [value_def(win[i] + 1.0) for i in idx])):
        assert diff_bars(mine, other, tol=1e-12) == (0, 0), (frame, label)
    assert ZSCORE_DDOF == 1


@pytest.mark.parametrize("buffer", [0.0, 0.01, 1.0, 1e6])
def test_the_buffer_cannot_bind(buffer):
    """`BUFFER` moves only the two outer edges and no point lies outside
    `[min, max]`, so any buffer gives the same bins: 0 of 467 windows move at
    0, 0.01, 1 and 1e6. It is kept because the definition has it -- and
    because the OTHER place it could have gone is `test_the_edge_spelling_is_
    load_bearing`, where the same 0.1 moves hundreds of windows."""
    win, bars = windows(FRAMES["walk"])
    idx = list(range(0, win.shape[0], 3))
    mine = [float(base("walk").iloc[int(bars[i])]) for i in idx]
    other = [value_def(win[i], buffer=buffer) for i in idx]
    assert diff_bars(mine, other, tol=1e-12) == (0, 0), buffer


@pytest.mark.parametrize("frame", STOCHASTIC)
def test_the_range_comes_from_the_whole_window_not_from_one_limb(frame):
    """The definition bins the SERIES and then forms the lagged limbs, so the
    last TAU points -- which appear in the lagged-TO limb only -- are part of
    the range. Taking it from the lagged-FROM limb instead moves 5 to 9
    windows of 200 on the stochastic frames (0 on the cosine one), so this is
    a real reading and not a cosmetic one."""
    win, bars = windows(FRAMES[frame])
    idx = list(range(0, win.shape[0], WINDOW_STRIDE))
    mine = [float(base(frame).iloc[int(bars[i])]) for i in idx]
    other = [value_def(win[i], binsource="y1") for i in idx]
    assert diff_bars(mine, other, tol=1e-12)[0] >= 1, frame


def test_the_lag_and_the_bin_count_are_not_interchangeable():
    """TAU = 2 and NUM_BINS = 5 are the feature's OWN parameters, the two
    numbers in `CO_HistogramAMI_even_2_5`. Measured on 467 windows of the
    walk: at tau 1, 3 and 5 the Spearman against the shipped column is +0.13,
    +0.06 and +0.13, and at 3 and 10 bins -0.05 and +0.44 -- so neither is a
    smooth knob whose value hardly matters."""
    win, bars = windows(FRAMES["walk"])
    idx = list(range(0, win.shape[0], 3))
    mine = [float(base("walk").iloc[int(bars[i])]) for i in idx]
    assert (TAU, NUM_BINS) == (2, 5)
    for tau in (1, 3, 5):
        other = [value_def(win[i], tau=tau) for i in idx]
        assert abs(spearman(mine, other)) < 0.5, tau
    for bins in (3, 10):
        other = [value_def(win[i], bins=bins) for i in idx]
        assert abs(spearman(mine, other)) < 0.7, bins


def test_the_column_reads_near_zero_on_independent_data():
    """What "no dependence" looks like, which a consumer cannot guess from
    the scale. On THIS section's 400 independent normal windows (receipt
    §A10, drawn through the plain-Python spelling so the corrected and
    uncorrected readings come off the same draw) the corrected column reads a
    median of +0.0282 and is negative on 15.5%; the uncorrected plug-in reads
    +0.086, which is its own first-order bias `(5-1)**2 / (2 * 98)` = 0.0816.
    ⚠ §A10b draws another 400 through the shipped kernel and gets +0.0284 and
    17.3% -- that is the pair quoted everywhere else in this port, and the
    1.8-point gap is what a 400-window sample does. The bounds here are wide
    on purpose -- both are samples -- but the ORDER of the two is the point."""
    rng = np.random.default_rng(404)
    corrected, plug = [], []
    for _ in range(400):
        w = rng.normal(0.0, 0.015, LENGTH)
        corrected.append(value_def(w))
        plug.append(value_def(w, correct=False))
    assert 0.0 < float(np.median(corrected)) < 0.05
    assert 0.05 < float(np.median(plug)) < 0.12
    assert 0.02 < float(np.mean(np.asarray(corrected) < 0.0)) < 0.40
    assert float(np.min(plug)) > 0.0          # a plug-in MI cannot be < 0
    bias = (NUM_BINS - 1) ** 2 / (2.0 * PAIRS)
    assert abs(float(np.median(plug)) - bias) < 0.02


@pytest.mark.parametrize("frame", list(FRAMES))
def test_the_output_is_inside_the_derived_bounds(frame):
    """`ami_bounds(length)` is derived, not measured: the plug-in MI is in
    `[0, log 5]` and the correction adds at most `(5-1)/(2*98)` and subtracts
    at most `(5-1)**2/(2*98)`. Measured range over the five stochastic
    frames: -0.0329 to 0.2066; the cosine frame sits at 0.727 to 0.734."""
    lo, hi = ami_bounds(LENGTH)
    a = base(frame).dropna().to_numpy()
    assert float(a.min()) >= lo, (frame, a.min(), lo)
    assert float(a.max()) <= hi, (frame, a.max(), hi)
    assert (lo, hi) == (-16 / 196, MAX_AMI + 4 / 196)
    assert ami_bounds(250)[0] > lo        # the bounds tighten with length


def test_negative_values_are_reachable_and_the_docstring_says_so():
    """A mutual information cannot be negative; this bias-CORRECTED estimate
    of one can be, and is, on four of the six frames here. That is the single
    most surprising thing about the column, so the docstring has to say it
    where a consumer will look."""
    negative = {name for name in FRAMES
                if float(base(name).dropna().to_numpy().min()) < 0.0}
    assert len(negative) >= 4, negative
    doc = c22_ami2.__doc__
    assert "NEGATIVE" in doc
    assert "Miller-Madow" in doc or "MILLER-MADOW" in doc


@pytest.mark.parametrize("frame", list(FRAMES))
def test_the_binning_never_runs_near_a_rounding_flip(frame):
    """Why this column is bit-identical under an inexact rescale (Gate D) and
    why no test here pins a value to 1e-15: the value is a function of a 5x5
    INTEGER matrix, and the only float decision is which side of an interior
    edge each point falls. The smallest margin measured is 1.25e-06, the
    median per frame 2.6e-03 to 1.9e-02, and 0 points sit within 1e-12 of an
    edge."""
    win, _ = windows(FRAMES[frame])
    worst = math.inf
    ties = 0
    for i in range(0, win.shape[0], WINDOW_STRIDE):
        w = win[i]
        z = (w - w.mean()) / w.std(ddof=ZSCORE_DDOF)
        _, e = shipped_bins(w)
        d = np.abs(z[:, None] - e[None, 1:NUM_BINS])
        worst = min(worst, float(d.min()))
        ties += int(np.sum(d < 1e-12))
    assert ties == 0, (frame, ties)
    assert worst > 1e-8, (frame, worst)


def test_the_module_docstring_attributes_the_source():
    doc = c22_ami2.__doc__
    for needle in ("Lubba", "33:1821", "CO_HistogramAMI", "GPL-3.0", "#127",
                   "Miller", "1955"):
        assert needle in doc, needle
    assert "classification" in doc.lower()
    assert "existence" in doc and "not evidence" in doc


def test_the_reference_implementation_is_not_imported_by_shipped_code():
    """The reference (pycatch22) is GPL-3.0 and this fork is MIT. The claim
    that has to hold is about the shipped CODE PATH, so this sweeps every
    `.py` file under `pandas_ta/` for an import of it -- 0 hits over more
    than 300 files. ⚠ pycatch22 IS installed in the owner's worktree, so the
    guard is not vacuous."""
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
    "chunk-wide-demean": (
        "z = (block - block.mean(axis=1, keepdims=True)) / sd[:, None]",
        "z = (block - block.mean()) / sd[:, None]"),
    "chunk-wide-sd": (
        "sd = block.std(axis=1, ddof=ZSCORE_DDOF)",
        "sd = np.full(block.shape[0], block.std(ddof=ZSCORE_DDOF))"),
    "chunk-wide-extremes": (
        "        lo = z.min(axis=1)\n        hi = z.max(axis=1)",
        "        lo = np.full(rows, z.min())\n"
        "        hi = np.full(rows, z.max())"),
    "no-bias-correction": (
        "    ami = plug - (occupied - rows_used - cols_used + 1) / (2.0 * pairs)",
        "    ami = plug"),
    "joint-transposed": (
        "    code = idx[:, :pairs] * NUM_BINS + idx[:, TAU:]",
        "    code = idx[:, TAU:] * NUM_BINS + idx[:, :pairs]"),
    "no-overflow-guard": ("bad |= ~(sd > NOISE_FLOOR) | ~np.isfinite(sd)",
                          "bad |= ~(sd > NOISE_FLOOR)"),
    "no-floor": ("bad |= ~(sd > NOISE_FLOOR) | ~np.isfinite(sd)",
                 "bad |= ~(sd > 0.0)"),
}


def mutant(name):
    """Read this module off disk, edit one write, exec it in memory."""
    old, new = MUTANTS[name]
    assert SRC.count(old) == 1, (name, SRC.count(old))
    ns = {}
    exec(compile(SRC.replace(old, new), f"<mutant {name}>", "exec"), ns)
    return ns["c22_ami2"]


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
    assert _leaks(c22_ami2, f, _offsets(len(f)), splices=8) == []


@pytest.mark.parametrize("length", [MIN_LENGTH, 120, 250])
def test_the_sweep_at_non_default_lengths(length):
    f = FRAMES["walk"]
    assert _leaks(lambda s: c22_ami2(s, length=length), f,
                  _offsets(len(f), length), splices=4) == []


@pytest.mark.parametrize("name", ["write-back-dated", "window-one-ahead",
                                  "window-ten-ahead", "returns-rolled"])
def test_each_look_ahead_mutant_is_caught(name):
    """Each look-ahead mutant must be caught by the same sweep the real
    module passes clean. Measured on the walk frame: 35 of 35 offsets for all
    four, which is the whole sweep -- this column is continuous and ties on
    under 9% of neighbouring pairs there, so a one-bar shift has nowhere to
    hide. The bound is 20 rather than 35 because the catch rate is a property
    of where the splices land."""
    f = FRAMES["walk"]
    hits = _leaks(mutant(name), f, _offsets(len(f)), splices=8)
    assert len(hits) >= 20, (name, len(hits))


def test_a_one_bar_mutant_can_only_move_bars_from_the_cut_backwards():
    """A back-dated write moves bar J-1 and bars after it, never bar J-2 or
    earlier -- which is exactly what makes it a look-ahead of ONE bar.
    Measured: 22 of 35 offsets move a pre-splice bar, and the first moved bar
    is J-1 on every one of them."""
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
    assert seen >= 10, seen


def test_the_mask_mutant_is_dead_on_a_clean_frame_and_caught_on_a_dirty_one():
    """This mutant back-dates the bad-data MASK instead of a value, so a
    clean frame cannot see it: bit-equal on all 1,500 bars of the walk. On a
    frame with one bad close it moves exactly bar J-1, caught 12 of 12."""
    fn = mutant("mask-back-dated")
    clean = FRAMES["walk"]
    assert same(c22_ami2(clean), fn(clean))
    caught = 0
    for j in _offsets(len(clean), count=12):
        dirty = clean.copy()
        dirty.iloc[j] = np.nan
        a = np.asarray(c22_ami2(dirty), float)
        b = np.asarray(fn(dirty), float)
        moved = np.where(~((a == b) | (np.isnan(a) & np.isnan(b))))[0]
        if len(moved):
            caught += 1
            assert int(moved.min()) == j - 1, (j, moved[:4])
    assert caught == 12, caught


@pytest.mark.parametrize("name", ["chunk-wide-demean", "chunk-wide-sd"])
@pytest.mark.parametrize("frame", ["walk", "tick-rounded", "penny"])
def test_two_cross_row_mutants_are_dead_by_affine_invariance(name, frame):
    """Both of these ARE reads of other rows, so the sweep should see them,
    and it cannot: they are bit-equal to the real module on all 1,500 bars of
    three frames. The reason is measured rather than excused -- the interior
    bin edges are an affine function of each row's own min and max, so
    centring or scaling a row by the whole CHUNK's mean or standard deviation
    moves the data and every edge together and no point changes bin. They are
    counted among the twelve mutants rather than quietly dropped, and the
    cross-row read that DOES bite has its own test below."""
    fn = mutant(name)
    assert same(base(frame), fn(FRAMES[frame])), (name, frame)


@pytest.mark.parametrize("frame", ["walk", "tick-rounded", "penny"])
def test_the_joint_transposed_mutant_is_dead_because_mi_is_symmetric(frame):
    """The third dead mutant, and it answers a different question: whether
    this module has the joint table's AXES the right way round. It does not
    matter -- a mutual information is symmetric, and so is the Miller-Madow
    term, which counts occupied cells, rows and columns -- so transposing the
    table can change nothing but the ORDER of the 25 logarithms. Measured:
    5.6e-17 on 568 to 618 bars of 1,400 (539 to 625 with AVX-512 / AVX2 /
    FMA3 off -- the count is itself a last-bit question, which is why only
    the GAP is asserted below), one unit in the last place, and the sweep
    catches it at 0 of 35 offsets.
    ⚠ This is NOT the "marginals transposed" candidate of receipt §P1c, which
    pairs `pi[j]` with `pj[i]`: that one is a real and wrong formula and
    matches the reference on 21 of 2,802 windows."""
    got = mutant("joint-transposed")(FRAMES[frame])
    assert diff_bars(base(frame), got, tol=1e-12) == (0, 0), frame
    assert worst_gap(base(frame), got) < 1e-15, frame


def test_the_chunk_wide_extremes_mutant_is_caught():
    """The cross-row read that does change a value: taking the bin edges from
    the whole chunk's extremes instead of each row's. Caught at 30 of 35
    offsets by the sweep, and it moves all 1,400 fired bars of three frames
    by up to 0.13 nats."""
    fn = mutant("chunk-wide-extremes")
    hits = _leaks(fn, FRAMES["walk"], _offsets(1500), splices=8)
    assert len(hits) >= 20, len(hits)
    for frame in ("walk", "tick-rounded", "penny"):
        got = fn(FRAMES[frame])
        assert diff_bars(base(frame), got, tol=1e-12)[0] >= 1300, frame
        assert worst_gap(base(frame), got) > 0.05, frame


@pytest.mark.parametrize("frame", list(FRAMES))
def test_the_column_ties_rarely_so_the_sweep_has_power(frame):
    """Why the look-ahead mutants above are caught 35 of 35, unlike the
    integer-valued catch22 siblings (8 of 35 for `c22_periodicity`'s one-bar
    mutants on its walk frame, 22 of 35 for `c22_ami_timescale`'s):
    neighbouring bars carry the same value on 7.2% to 21.7% of pairs (7.4%
    to 21.5% with AVX-512 / AVX2 / FMA3 off), and
    each stochastic frame takes 1,043 to 1,296 distinct values over 1,400
    bars -- against those siblings' 79% to 100% tie share. The 20-bar cosine
    frame takes 8 and is handled by name below."""
    a = base(frame).dropna().to_numpy()
    if frame == "cosine":
        assert len(set(a.tolist())) >= 4
        return
    assert float(np.mean(a[1:] == a[:-1])) < 0.40, frame
    assert len(set(a.tolist())) >= 700, frame


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
    """1,043 to 1,296 distinct values per frame, medians 0.023 to 0.088.
    Pinned as a band because the exact count moves with the CPU dispatch."""
    a = base(frame).dropna().to_numpy()
    assert len(set(a.tolist())) >= 700, frame
    assert float(a.max() - a.min()) > 0.1, frame


def test_the_cosine_frame_is_nearly_constant_by_construction():
    """The one frame where the column barely varies is the one whose returns
    are an exact 20-bar cosine: 8 distinct values spanning 0.0068 nats around
    0.73 -- the feature working on a perfectly repeating window, not a dead
    column."""
    a = base("cosine").dropna().to_numpy()
    assert 0.70 < float(a.min()) and float(a.max()) < 0.75
    assert float(a.max() - a.min()) < 0.05
    assert len(set(a.tolist())) >= 4


def test_a_tick_rounded_penny_frame_still_fires_everywhere():
    """The issue's own worry: shape features of returns can read BIST tick
    rounding. A 2-lira stock on a 1-kurus tick prints 21.7% of its returns as
    exactly 0.00%, which collapses 48 of 100 points into one bin, and the
    column still fires on all 1,400 bars with 1,252 distinct values. What it
    does to the READING is measured rather than waved at: the median falls
    from the walk's 0.0428 to 0.0262, so the rounding pushes this column
    DOWN, toward its no-dependence value. Whether that makes a price level or
    a candle-shape column its top real comparator is Gate E's question and is
    owed."""
    f = FRAMES["penny"]
    r = np.asarray(f, float)
    r = r[1:] / r[:-1] - 1.0
    assert float(np.mean(r == 0.0)) > 0.15
    s = base("penny")
    assert int(s.notna().sum()) == len(f) - LENGTH
    assert len(set(s.dropna().to_numpy().tolist())) >= 700
    win, _ = windows(f)
    idx, _ = shipped_bins(win[0])
    assert int(np.max(np.bincount(idx))) > 40
    assert float(s.median()) < float(base("walk").median())


def test_a_flat_run_blanks_from_the_first_all_zero_window():
    """A price that goes flat at bar 400 blanks from bar 499 -- the first bar
    whose whole window of returns is zero -- and bar 498, whose window still
    holds the one non-zero return, fires."""
    c = FRAMES["walk"].to_numpy().copy()
    c[400:] = c[399]
    s = c22_ami2(Series(c[:700]))
    assert int(s.notna().sum()) == 399
    assert not math.isnan(float(s.iloc[498]))
    assert s.iloc[499:].isna().all()


@pytest.mark.parametrize("step", [0.01, 0.001, -0.005])
def test_an_exact_geometric_ladder_never_fires_and_the_floor_is_why(step):
    """`start * (1 + step)**k` rounds every power on its own, so the window
    holds 3 or 4 distinct returns with a standard deviation of 8.9e-17 to
    1.5e-16 -- under the 9.09e-13 floor. UNGUARDED, measured on every window
    through the module's own source with the floor removed, it fires on all
    1,400 bars and reads -0.0199 to 0.0932 (median 0.0103), which is inside
    the walk frame's own range: a reader could not tell it from a real
    reading. The value bounds below are wider than that span on purpose --
    the frame IS rounding noise, so the digits move with the CPU dispatch
    (-0.0199 to 0.0417 with AVX-512 / AVX2 / FMA3 off) -- while the COUNT is
    pinned exactly, because that does not move."""
    f = ladder(step=step)
    assert int(c22_ami2(f).notna().sum()) == 0
    win, _ = windows(f)
    assert float(win.std(axis=1, ddof=ZSCORE_DDOF).max()) < NOISE_FLOOR
    assert len(set(win[0].tolist())) <= 8
    unguarded = np.asarray(mutant("no-floor")(f), float)
    live = unguarded[~np.isnan(unguarded)]
    assert live.size == 1400, live.size
    lo, hi = ami_bounds(LENGTH)
    assert lo <= float(live.min()) and float(live.max()) <= 0.2
    assert float(live.max()) > 0.0
    # and that range is not distinguishable from the walk frame's own
    real = base("walk").dropna().to_numpy()
    assert float(live.max()) < float(real.max())


@pytest.mark.parametrize("length,lo,hi", [(MIN_LENGTH, 0.15, 0.30),
                                           (LENGTH, 0.01, 0.05),
                                           (250, 0.001, 0.02)])
def test_the_no_dependence_reading_is_a_function_of_the_length(length, lo, hi):
    """"No lag-2 dependence is about +0.028" is a DEFAULT-LENGTH statement,
    and the thing that makes it one is the correction's `1 / (2 (length - 2))`
    scaling. Measured through the shipped kernel on 400 independent normal
    windows per length: iid median +0.228 at `MIN_LENGTH` = 27, +0.084 at 50,
    +0.028 at 100, +0.008 at 250, with 0.25% / 8.5% / 17.3% / 28.5% negative.

    ⚠ This is why `MIN_LENGTH` is a floor and not a recommendation: at 27 the
    window holds one lagged pair per table cell and the reading is mostly the
    estimator's own bias (the first-order plug-in term is 0.32 nats there
    against 0.0816 at the default). The bands are wide because 400 windows is
    a sample; what is pinned is that they do not overlap."""
    rng = np.random.default_rng(909)
    got = np.asarray([shipped_on(rng.normal(0.0, 0.015, length))
                      for _ in range(400)])
    assert lo < float(np.median(got)) < hi, (length, np.median(got))
    bias = (NUM_BINS - 1) ** 2 / (2.0 * (length - TAU))
    assert float(np.median(got)) < bias, (length, bias)
    assert "+0.228" in c22_ami2.__doc__ or "0.228" in c22_ami2.__doc__


def test_the_output_bounds_are_an_enclosure_not_a_measured_range():
    """`ami_bounds` is derived and is an ENCLOSURE: neither endpoint is
    claimed reachable, and the measured span is far inside it. Pinned because
    a later reader could mistake the bound for the scale -- the lower end
    would need a plug-in MI of exactly 0 on a full 5x5 table and the upper
    end a marginal entropy of exactly log 5 on a 5-cell bijection, which 98
    pairs cannot split evenly."""
    lo, hi = ami_bounds(LENGTH)
    worst_lo = min(float(base(n).dropna().to_numpy().min()) for n in FRAMES)
    worst_hi = max(float(base(n).dropna().to_numpy().max()) for n in FRAMES)
    # the highest reading measured anywhere here is the kurus path's 1.3432
    highest = float(c22_ami2(kurus_path()).dropna().to_numpy().max())
    assert lo < worst_lo - 0.04, (lo, worst_lo)
    assert worst_hi + 0.8 < hi, (hi, worst_hi)
    assert highest + 0.25 < hi, (hi, highest)
    assert "ENCLOSURE" in ami_bounds.__doc__


def test_a_single_ulp_step_never_fires_and_what_that_buys():
    """A price flat at 1e6 except for ONE 1-ulp step: the 100 windows holding
    the step have a return standard deviation of 2.2e-17, and UNGUARDED --
    measured on every window through the module's own source with the floor
    removed, not sampled -- exactly those 100 fire and read 0.000000 to
    0.000105, this column's "no dependence", which is a legal value and not a
    blank. Guarded: 0 bars fire."""
    c = np.full(1500, 1e6)
    c[700:] = np.nextafter(1e6, 2e6)
    f = Series(c)
    assert int(c22_ami2(f).notna().sum()) == 0
    unguarded = np.asarray(mutant("no-floor")(f), float)
    live = unguarded[~np.isnan(unguarded)]
    assert live.size == 100, live.size
    assert float(np.abs(live).max()) < 0.01, float(np.abs(live).max())
    win, _ = windows(f)
    assert float(win.std(axis=1, ddof=ZSCORE_DDOF).max()) < NOISE_FLOOR


def test_a_deterministically_smooth_path_fires_near_the_top_of_the_scale():
    """The floor's cost, stated in the direction it actually runs. A price
    rising by exactly one kurus a bar from 100.00 is a smooth hyperbola in
    returns whose standard deviation is 2.9e-07 -- 316,000 times the floor --
    so this column FIRES on all 1,400 bars and reads 1.3432, constant, within
    0.29 of the top of its scale, because a smooth monotone return series
    really is almost perfectly lag-2 dependent. `c22_periodicity` blanks that
    same frame on all 1,400 bars, so a companion must not assume the three
    catch22 ports blank together."""
    f = kurus_path()
    s = c22_ami2(f)
    assert int(s.notna().sum()) == 1400
    a = s.dropna().to_numpy()
    assert float(a.max() - a.min()) < 1e-9
    assert 1.3 < float(a[0]) < ami_bounds(LENGTH)[1]
    assert int(pandas_ta.c22_periodicity(f).notna().sum()) == 0
    assert int(pandas_ta.c22_ami_timescale(f).notna().sum()) == 1400


@pytest.mark.parametrize("frame", list(FRAMES))
def test_the_floor_is_inert_on_anything_price_shaped(frame):
    """The floor costs nothing on a real shape: the guarded and unguarded
    spellings are bit-equal on all 1,400 fired bars of each frame, measured
    through the module's own source rather than through a re-spelling."""
    assert same(base(frame), mutant("no-floor")(FRAMES[frame])), frame


# ------------------------------------------------------------- Gate D
@pytest.mark.parametrize("factor", [8.0, 64.0, 2.0 ** -40, 2.0 ** 40])
@pytest.mark.parametrize("frame", list(FRAMES))
def test_an_exact_binary_rescale_is_bit_identical(frame, factor):
    """By construction: the price enters only as `c[t] / c[t-1]`, and
    `8a / 8b` is the same double as `a / b`."""
    assert same(base(frame), c22_ami2(FRAMES[frame] * factor))


@pytest.mark.parametrize("factor", [8.0, 64.0])
@pytest.mark.parametrize("length", [MIN_LENGTH, 120, 250])
def test_the_scale_invariance_holds_at_non_default_lengths(length, factor):
    f = FRAMES["walk"]
    assert same(c22_ami2(f, length=length),
                c22_ami2(f * factor, length=length))


@pytest.mark.parametrize("price", [1e-6, 1e6, 1e100])
def test_the_scale_invariance_holds_at_every_price_level(price):
    f = walk(level=price)
    b = c22_ami2(f)
    assert int(b.notna().sum()) == len(f) - LENGTH
    assert same(b, c22_ami2(f * 8.0))


@pytest.mark.parametrize("factor", [10.0, 3.7, 0.1, 1.0000001])
@pytest.mark.parametrize("frame", list(FRAMES))
def test_an_inexact_rescale_is_bit_identical_too(frame, factor):
    """Not promised by the arithmetic -- x10 is not exact in binary, so the
    returns themselves move in the last bits -- but measured, and the reason
    is structural: the value is a function of a 5x5 matrix of INTEGER counts,
    so a perturbation that moves no point across a bin edge cannot move the
    output AT ALL. The measured margin to the nearest edge is 1.25e-06. This
    asserts a tolerance rather than bit-equality, because the 25 logarithms
    could in principle reassociate on another CPU dispatch."""
    got = c22_ami2(FRAMES[frame] * factor)
    moved, mask = diff_bars(base(frame), got, tol=1e-15)
    assert moved == 0, (frame, factor, moved,
                        worst_gap(base(frame), got))
    assert mask == 0, (frame, factor, mask)


@pytest.mark.parametrize("factor", [0.5, 2.0, 10.0])
def test_it_is_blind_to_the_amplitude_of_the_returns(factor):
    """The bin edges are affine in the window's own extremes, so rescaling
    the RETURNS cannot move a bin: 0 of 467 windows move at x0.5, x2 and
    x10."""
    win, bars = windows(FRAMES["walk"])
    idx = list(range(0, win.shape[0], 3))
    mine = [float(base("walk").iloc[int(bars[i])]) for i in idx]
    other = [value_def(win[i] * factor) for i in idx]
    assert diff_bars(mine, other, tol=1e-12) == (0, 0), factor


def test_it_is_not_blind_to_the_order_of_the_returns():
    """So the invariance above is not vacuous: the same returns in a
    different order move 467 of 467 windows, Spearman +0.045."""
    win, bars = windows(FRAMES["walk"])
    idx = list(range(0, win.shape[0], 3))
    mine = [float(base("walk").iloc[int(bars[i])]) for i in idx]
    rng = np.random.default_rng(5)
    other = [value_def(rng.permutation(win[i])) for i in idx]
    assert diff_bars(mine, other, tol=1e-12)[0] >= 400
    assert abs(spearman(mine, other)) < 0.5


@pytest.mark.parametrize("frame", list(FRAMES))
def test_it_fires_strictly_between_zero_and_n(frame):
    s = base(frame)
    assert 0 < int(s.notna().sum()) < len(s)


# ------------------------------------------------------------- bad data
@pytest.mark.parametrize("bad", [np.nan, np.inf, -np.inf, 0.0, -5.0, 1e-310])
def test_a_bad_close_empties_exactly_its_own_windows(bad):
    """A close that is not a finite, normal, positive float has no return to
    take, so the 101 windows that read it are blank: bars 700 .. 800 for a
    bad close at 700, and nothing else."""
    f = FRAMES["walk"].copy()
    f.iloc[700] = bad
    s = c22_ami2(f)
    blank = np.where(s.isna().to_numpy())[0]
    after = blank[blank >= LENGTH]
    assert after.size == 101
    assert int(after.min()) == 700 and int(after.max()) == 800


def test_a_close_pair_whose_ratio_overflows_empties_its_windows():
    f = FRAMES["walk"].copy()
    f.iloc[700] = 1e-300
    f.iloc[701] = 1e100
    s = c22_ami2(f)
    blank = np.where(s.isna().to_numpy())[0]
    after = blank[blank >= LENGTH]
    assert after.size == 100
    assert int(after.min()) == 701 and int(after.max()) == 800


def test_a_finite_but_enormous_return_blanks_rather_than_reading_zero():
    """`1e-100` followed by `1e100` is a FINITE return of 1e200, so the
    return filter does not catch it; what does is the `~isfinite(sd)` limb,
    because the window's sum of squares overflows. Without that limb those
    100 bars read exactly 0.0 -- the value of a window with nothing in it, a
    value and not a blank -- which is measured here by exec'ing the module
    without the guard."""
    f = FRAMES["walk"].copy()
    f.iloc[700] = 1e-100
    f.iloc[701] = 1e100
    assert math.isfinite(float(f.iloc[701] / f.iloc[700] - 1.0))
    s = c22_ami2(f)
    blank = np.where(s.isna().to_numpy())[0]
    after = blank[blank >= LENGTH]
    assert after.size == 100
    without = np.asarray(mutant("no-overflow-guard")(f), float)
    saved = np.where(np.isnan(s.to_numpy()) & ~np.isnan(without))[0]
    assert saved.size == 100
    assert set(without[saved].tolist()) == {0.0}


@pytest.mark.parametrize("frame", list(FRAMES))
def test_the_overflow_guard_is_inert_on_every_realistic_frame(frame):
    assert same(base(frame), mutant("no-overflow-guard")(FRAMES[frame]))


@pytest.mark.parametrize("ratio_pair", [(1e-50, 1e27), (1e-20, 1e20)])
def test_the_overflow_guard_is_inert_where_the_sums_stay_finite(ratio_pair):
    """A close pair of ratio 1e77 or 1e40 does NOT overflow the sum of
    squares, so nothing blanks and the window is read as what it is: a window
    one astronomic return dominates."""
    lo, hi = ratio_pair
    f = FRAMES["walk"].copy()
    f.iloc[700] = lo
    f.iloc[701] = hi
    s = c22_ami2(f)
    blank = np.where(s.isna().to_numpy())[0]
    assert blank[blank >= LENGTH].size == 0
    assert same(s, mutant("no-overflow-guard")(f))


@pytest.mark.parametrize("n,fires", [(99, None), (100, None), (101, 1),
                                     (102, 2)])
def test_a_short_input_returns_none_until_one_window_exists(n, fires):
    s = c22_ami2(FRAMES["walk"].iloc[:n])
    if fires is None:
        assert s is None
    else:
        assert int(s.notna().sum()) == fires


@pytest.mark.parametrize("length,name,fires", [
    (None, "C22AMI2_100", 1400),
    (0, "C22AMI2_100", 1400),
    (1, "C22AMI2_100", 1400),
    (MIN_LENGTH - 1, "C22AMI2_100", 1400),
    (MIN_LENGTH, f"C22AMI2_{MIN_LENGTH}", 1500 - MIN_LENGTH),
    (250, "C22AMI2_250", 1250),
    (250.7, "C22AMI2_250", 1250),
])
def test_the_length_guard_band(length, name, fires):
    """Below `MIN_LENGTH` = `NUM_BINS**2 + TAU` = 27 -- where a window would
    hold fewer lagged pairs than the joint histogram has cells -- a length
    falls back to 100 rather than computing something thin."""
    s = c22_ami2(FRAMES["walk"], length=length)
    assert s.name == name
    assert int(s.notna().sum()) == fires
    assert MIN_LENGTH == NUM_BINS * NUM_BINS + TAU


def test_the_offset_and_the_fill_are_the_house_ones():
    s = c22_ami2(FRAMES["walk"], offset=2)
    assert same(s.to_numpy()[2:], base("walk").to_numpy()[:-2])
    s = c22_ami2(FRAMES["walk"], fillna=-1)
    assert int(s.isna().sum()) == 0
    assert int((s == -1).sum()) == LENGTH


@pytest.mark.parametrize("budget", [100, 400, 1024])
def test_the_chunk_budget_cannot_change_a_value(budget):
    """Every quantity is per-row, so the chunk boundary is invisible: budgets
    of 100, 400, 1,024 and the default are bit-equal. The `chunk-wide-*`
    mutants are the same claim from the other side."""
    want = base("walk")
    MODULE.CHUNK_VALUES = budget
    try:
        got = c22_ami2(FRAMES["walk"])
    finally:
        MODULE.CHUNK_VALUES = CHUNK_VALUES
    assert same(want, got)


# ------------------------------------------------------------- wiring
def test_the_five_wiring_touch_points():
    assert Path(MODULE.__file__).exists()
    assert hasattr(pandas_ta.statistics, "c22_ami2")
    assert "c22_ami2" in pandas_ta.Category["statistics"]
    assert hasattr(pandas_ta.core.AnalysisIndicators, "c22_ami2")
    assert (ROOT / "tests" / "test_c22_ami2.py").exists()


def test_the_accessor_forwards_its_parameters():
    df = DataFrame({"close": FRAMES["walk"].to_numpy()})
    acc = df.ta.c22_ami2()
    assert acc.name == "C22AMI2_100"
    assert same(acc, base("walk"))
    acc = df.ta.c22_ami2(length=250, offset=1)
    assert acc.name == "C22AMI2_250"
    assert same(acc, c22_ami2(FRAMES["walk"], length=250, offset=1))


def test_the_dictionary_row_describes_this_column():
    text = (ROOT / "docs" / "IndicatorDictionary.md").read_text(
        encoding="utf-8")
    assert "C22AMI2_100" in text
    assert "c22_ami2" in text


# ------------------------------------------------------- Gate E, measured
RECEIPT = ROOT / "docs" / "C22Ami2Measured.md"


def test_the_receipt_carries_the_measured_gate_e_numbers():
    """The receipt is the deliverable the issue asks for, so the launcher's
    run of 2026-11-20 has to live in it and not only in the ledger: the pooled
    max with its comparator, the sample size, the per-frame max median with
    ITS comparator, and the run id.

    The 2026-10-24 screen's PROTOTYPE figure (0.0595, the same comparator)
    stays in §E0, labelled as the prototype's, because the agreement is what
    §P1 predicted -- but the pending line must be gone, since that line is how
    this document said "nobody has measured this"."""
    text = RECEIPT.read_text(encoding="utf-8")
    assert "Gate E: measured 2026-11-20 by issue-solver" in text
    assert "0.05943562162216838" in text          # the PORT's pooled max
    assert "0.07418786831507361" in text          # its per-frame max median
    assert "Dist_from_High_252_pct" in text and "natr" in text
    assert "389,949" in text
    assert "is127-c22_ami2-23b6686b" in text
    assert "r3-perframe-0.90" in text
    assert "0.0595" in text and "prototype" in text.lower()
    assert "Gate E: pending, run by issue-solver" not in text


def test_the_gate_e_row_is_recorded_and_says_ship():
    """The ledger carries exactly one row, for the one shipped column, and the
    `r3-perframe-0.90` bands put it at SHIP: nothing is removed, no waiver is
    needed. The bands are asserted as bands (pooled < 0.76, per-frame max
    median < 0.90) rather than as digits, which is what the CPU-dispatch rule
    asks for; the run id is pinned beside them, because this port's figure
    agrees with the 2026-10-24 screen's prototype to three decimals and an
    expected agreement is the easiest kind of row to copy in from the wrong
    run."""
    path = ROOT / "docs" / "gate_e_ledger.csv"
    with path.open(newline="", encoding="utf-8") as fh:
        rows = [r for r in csv.DictReader(fh)
                if r["indicator"] == "c22_ami2"]
    assert len(rows) == 1, rows
    row = rows[0]
    assert row["column"] == f"C22AMI2_{LENGTH}"
    assert row["module"] == "pandas_ta.statistics.c22_ami2"
    assert row["verdict"] == "SHIP"
    assert float(row["max_abs_rho"]) < 0.76
    assert float(row["perframe_max_median_abs_rho"]) < 0.90
    assert row["against"] == "Dist_from_High_252_pct"
    assert row["run"] == "is127-c22_ami2-23b6686b"
    assert row["measured"] == "2026-11-20"
    assert row["waiver"] == ""                  # only STRUCK needs one


def test_the_gate_e_row_has_no_sentinel_gap():
    """0.0 is a legal reading of this column, not only a blank (§C1), and on
    the 89 BIST frames it was never read: the row's non-NaN and non-zero
    counts are EQUAL. The sibling `c22_periodicity`, whose scale reaches 0 by
    way of a flat window, has them differing -- so this is a measured fact
    about BIST returns and not a property of the field."""
    path = ROOT / "docs" / "gate_e_ledger.csv"
    with path.open(newline="", encoding="utf-8") as fh:
        rows = {r["indicator"]: r for r in csv.DictReader(fh)}
    row = rows["c22_ami2"]
    non_nan, non_zero = int(row["non_nan"]), int(row["non_zero"])
    assert non_nan == 389949
    assert non_zero == non_nan
    sibling = rows["c22_periodicity"]
    assert int(sibling["non_zero"]) < int(sibling["non_nan"])


def test_the_receipt_states_the_agreement_with_the_reference():
    """The screen's Gate E figure was measured on the GPL-3.0 reference's
    column, so whether this port IS that column decides whether the figure
    transfers. It does -- 8,400 of 8,400 windows equal to 1e-12 -- and the
    receipt has to carry the number, because it is the one fact that makes
    the prototype's 0.0595 an expectation rather than a coincidence."""
    text = RECEIPT.read_text(encoding="utf-8")
    assert "8,400 of 8,400" in text
    assert "2,802" in text and "763" in text
    assert "Miller" in text


def test_the_owed_rule_for_the_nearest_catch22_relatives():
    """`SB_MotifThree_quantile_hh` (issue #132) and
    `SB_TransitionMatrix_quantile_3` (issue #129) bin the SAME 100 returns and
    count lagged pairs -- #132 is literally one of the three entropies in this
    column's formula over a 3-symbol alphabet -- and neither exists in this
    tree, so no run has priced the pair. The receipt carries proxies (max
    |rho| 0.53 and 0.49, both on the AR(1) frame, median 0.13 and 0.12) and
    the rule for when they land; this test fails if the section is dropped."""
    text = RECEIPT.read_text(encoding="utf-8")
    assert "#132" in text and "#129" in text
    assert "OWED RULE" in text
    assert "SB_MotifThree_quantile_hh" in text
    assert "SB_TransitionMatrix_quantile_3" in text


def test_the_receipt_scopes_its_interpretive_figures_to_the_length():
    """The one figure a consumer will carry away -- "no dependence is about
    +0.028" -- is a length-100 figure, and the receipt has to say so where it
    says the figure. §A10b is the measurement that makes it a scope and not a
    hedge."""
    text = RECEIPT.read_text(encoding="utf-8")
    assert "A10b" in text
    assert "+0.227979" in text or "+0.228" in text
    assert "is a floor, not a recommendation" in text


def test_gate_cs_real_data_limb_is_in_the_receipt():
    """Every count measured in THIS file is synthetic, which is the defect
    `CLAUDE.md` names, so Gate C's real-data limb has to be stated in the
    receipt: 389,949 of 398,849 pooled BIST bars non-NaN, which is `89 x 100`
    bars short of the pool -- the warm-up exactly, so the §C3 floor and the
    §P2 gap to the reference blanked nothing on real data."""
    text = RECEIPT.read_text(encoding="utf-8")
    assert "398,849" in text
    assert "389,949" in text
    assert "0 further bars blanked" in text
