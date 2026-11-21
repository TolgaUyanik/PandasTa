# -*- coding: utf-8 -*-
"""C22-ENTROPY-PAIRS: `c22_entropy_pairs`, catch22's Shannon entropy of
overlapping 2-letter words of a 3-quantile symbolization of the last 100
daily returns (issue #133).

Every number here was measured by running this module and
`docs/measure_c22_entropy_pairs.py` on this machine; the receipt is
`docs/C22EntropyPairsMeasured.md`. What is pinned, in order of how much it
would hurt to lose:

1. **The reading the definition leaves open.** "Quantile" names the BINNING
   rule but not the quantile ESTIMATOR at a finite sample. This port uses
   linear interpolation between bracketing order statistics (`numpy.
   quantile`'s default). It is disclosed rather than picked silently because
   a different interpolation convention is a different column at the
   margin -- see the receipt.
2. **The exact rational oracle agrees.** Linear-interpolated quantiles of a
   finite sample are a RATIONAL function of the order statistics -- no
   irrational operation is involved -- so the two cut points and every
   letter assignment can be recomputed with zero rounding and compared to
   the shipped float pipeline.
3. **Z-scoring is INERT**, for one reason: the empirical quantile of an
   increasing affine map of a sample is the same affine map of the quantile
   of the sample, so scaling and shifting a window before binning cannot
   move any letter boundary relative to the data.
4. **Two cross-row mutants are DEAD by that same invariance**, and a third
   (word order swapped) is dead because entropy is a function of the
   MULTISET of probabilities, invariant to which label is assigned to which
   category.
5. **Causality.** A future-perturbation sweep and read-off-disk mutants.
6. **Reachability on real-shaped data**, including the issue's own worry: a
   tick-rounded penny frame that collapses many returns into one letter.

Not pinned on purpose: exact counts of distinct values, exact bars-moved
counts, and any value to 1e-15. Tests pin bounds, tolerances and bands and
the docstring states the local figure.
"""
import importlib
import math
from fractions import Fraction
from pathlib import Path

import numpy as np
import pytest
from pandas import Series

from .context import pandas_ta
from pandas_ta.statistics.c22_entropy_pairs import (
    CHUNK_VALUES, MAX_ENTROPY, MIN_LENGTH, NOISE_FLOOR, NUM_LETTERS,
    NUM_WORD_TYPES, WORD_LENGTH, ZSCORE_DDOF, _entropy_pairs_rows,
    c22_entropy_pairs)

ROOT = Path(__file__).resolve().parent.parent
MODULE = importlib.import_module("pandas_ta.statistics.c22_entropy_pairs")
SRC = Path(MODULE.__file__).read_text(encoding="utf-8")
LENGTH = 100
PAIRS = LENGTH - 1

EXACT_STRIDE = 97
WINDOW_STRIDE = 7


# ------------------------------------------------------------- frames
def walk(n=1500, seed=11, sigma=0.015, level=100.0):
    rng = np.random.default_rng(seed)
    return Series(level * np.exp(np.cumsum(rng.normal(0.0, sigma, n))))


def tick_rounded(n=1500, seed=55):
    return Series(np.round(walk(n, seed).to_numpy(), 2))


def penny(n=1500, seed=23, level=2.0, sigma=0.012):
    """A 2-lira stock on a 1-kurus tick: many returns are exactly 0."""
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


FRAMES = {
    "walk": walk(),
    "tick-rounded": tick_rounded(),
    "penny": penny(),
    "ar1": ar1(),
    "cosine": cosine_returns(),
    "student-t": student_t(),
}
STOCHASTIC = [k for k in FRAMES if k != "cosine"]
_BASE = {}


def base(name):
    if name not in _BASE:
        _BASE[name] = c22_entropy_pairs(FRAMES[name])
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


# ------------------------------------------------------------- Gate A
def shipped_on(window):
    w = np.asarray(window, float)
    return float(_entropy_pairs_rows(w.reshape(1, -1))[0])


def shipped_letters(window, ddof=ZSCORE_DDOF):
    w = np.asarray(window, float)
    sd = float(w.std(ddof=ddof))
    z = (w - w.mean()) / sd
    q1, q2 = np.quantile(z, [1.0 / 3.0, 2.0 / 3.0])
    letter = (z > q1).astype(np.int64) + (z > q2).astype(np.int64)
    return letter, (q1, q2)


def entropy_of(letter):
    code = letter[:-1] * NUM_LETTERS + letter[1:]
    counts = np.bincount(code, minlength=NUM_WORD_TYPES)
    p = counts / float(letter.size - 1)
    with np.errstate(divide="ignore", invalid="ignore"):
        return float(-np.sum(np.where(p > 0, p * np.log(p), 0.0)))


def value_def(window, ddof=ZSCORE_DDOF, zscore=True, reverse=False):
    """The definition re-spelled in plain Python with `math.fsum`, one knob
    per reading. `zscore=True` and `reverse=False` are the shipped ones."""
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

    def quantile(p):
        s = sorted(z)
        pos = p * (n - 1)
        k = int(math.floor(pos))
        frac = pos - k
        if k + 1 >= n:
            return s[-1]
        return s[k] + frac * (s[k + 1] - s[k])

    q1, q2 = quantile(1.0 / 3.0), quantile(2.0 / 3.0)
    letter = [(1 if v > q1 else 0) + (1 if v > q2 else 0) for v in z]
    pairs = list(zip(letter[1:], letter[:-1])) if reverse \
        else list(zip(letter[:-1], letter[1:]))
    counts = {}
    for pr in pairs:
        counts[pr] = counts.get(pr, 0) + 1
    p_n = n - 1
    out = 0.0
    for cnt in counts.values():
        p = cnt / p_n
        out -= p * math.log(p)
    return out


def exact_letters(window, ddof=ZSCORE_DDOF):
    """Letters recomputed with ZERO rounding: linear-interpolated quantiles
    are a RATIONAL function of the order statistics, and z-scoring is
    provably inert, so the raw returns can be used directly."""
    y = [Fraction(float(v)) for v in window]
    n = len(y)
    mean = sum(y) / n
    u = [v - mean for v in y]
    if sum(v * v for v in u) == 0:
        return None

    def quantile(p):
        s = sorted(u)
        pos = Fraction(p) * (n - 1)
        k = int(pos)
        frac = pos - k
        if k + 1 >= n:
            return s[-1]
        return s[k] + frac * (s[k + 1] - s[k])

    q1, q2 = quantile(Fraction(1, 3)), quantile(Fraction(2, 3))
    return np.array([(1 if v > q1 else 0) + (1 if v > q2 else 0)
                     for v in u], dtype=np.int64)


def value_exact(window):
    letter = exact_letters(window)
    if letter is None:
        return float("nan")
    return entropy_of(letter)


@pytest.mark.parametrize("frame", list(FRAMES))
def test_bit_equal_to_the_exact_rational_oracle(frame):
    """Gate A's strongest limb: the letter sequence with ZERO roundings
    (linear-interpolated quantiles are rational in the order statistics, and
    z-scoring is provably inert here, so the raw returns settle them)."""
    win, bars = windows(FRAMES[frame])
    ran = 0
    for i in range(0, win.shape[0], EXACT_STRIDE):
        mine_letter, _ = shipped_letters(win[i])
        exact = exact_letters(win[i])
        assert np.array_equal(mine_letter, exact), (frame, int(bars[i]))
        mine = float(base(frame).iloc[int(bars[i])])
        assert abs(mine - value_exact(win[i])) < 1e-12, (frame, int(bars[i]))
        ran += 1
    assert ran >= 14, ran


@pytest.mark.parametrize("frame", list(FRAMES))
def test_the_plain_python_respelling_agrees(frame):
    """A second spelling sharing no code with the module: `math.fsum`, a
    hand-written linear-interpolation quantile, and a dict-counted entropy."""
    win, bars = windows(FRAMES[frame])
    worst = 0.0
    ran = 0
    for i in range(0, win.shape[0], WINDOW_STRIDE):
        mine = float(base(frame).iloc[int(bars[i])])
        other = value_def(win[i])
        worst = max(worst, abs(mine - other))
        ran += 1
    assert ran >= 199, ran
    assert worst < 1e-10, (frame, worst)


def test_the_output_is_inside_the_derived_bounds():
    """`[0, log(9)]`, an ENCLOSURE -- `log(9)` is reached only by a perfectly
    uniform 9-way distribution, which 99 words cannot split exactly evenly
    (99 / 9 = 11, so it CAN in principle -- but no frame here reaches it)."""
    assert abs(MAX_ENTROPY - math.log(9.0)) < 1e-15
    for frame in FRAMES:
        a = base(frame).dropna().to_numpy()
        assert float(a.min()) >= -1e-12, frame
        assert float(a.max()) <= MAX_ENTROPY + 1e-12, frame


@pytest.mark.parametrize("frame", list(FRAMES))
def test_z_score_and_its_divisor_are_inert(frame):
    """The empirical quantile of an increasing affine map of a sample is the
    same affine map of the quantile of the sample, so no letter boundary can
    move relative to the data under a positive rescale or a shift. Measured:
    0 of 467 sampled windows move under the population z-score (`ddof` 0),
    under NO z-score at all, or under a +1 shift."""
    win, bars = windows(FRAMES[frame])
    idx = list(range(0, win.shape[0], 3))
    mine = [float(base(frame).iloc[int(bars[i])]) for i in idx]
    for label, other in (
            ("ddof 0", [value_def(win[i], ddof=0) for i in idx]),
            ("no z-score", [value_def(win[i], zscore=False) for i in idx]),
            ("shifted +1", [value_def(win[i] + 1.0) for i in idx])):
        assert diff_bars(mine, other, tol=1e-9) == (0, 0), (frame, label)
    assert ZSCORE_DDOF == 1


def test_word_order_reversed_is_dead_by_label_symmetry():
    """Entropy is a function of the MULTISET of word probabilities, so
    reading the words backwards (letter[t+1], letter[t]) instead of
    (letter[t], letter[t+1]) only PERMUTES which of the 9 categories holds
    which count -- the sum `-sum(p log p)` cannot see a permutation of its
    own terms. Measured: 0 of 467 sampled windows differ by more than
    floating-point noise on five stochastic frames."""
    for frame in STOCHASTIC:
        win, bars = windows(FRAMES[frame])
        idx = list(range(0, win.shape[0], 3))
        mine = [float(base(frame).iloc[int(bars[i])]) for i in idx]
        other = [value_def(win[i], reverse=True) for i in idx]
        assert diff_bars(mine, other, tol=1e-9) == (0, 0), frame


def test_the_module_docstring_attributes_the_source():
    doc = c22_entropy_pairs.__doc__
    for needle in ("Lubba", "33:1821", "SB_MotifThree", "GPL-3.0", "#133"):
        assert needle in doc, needle
    assert "classification" in doc.lower()
    assert "existence" in doc and "not evidence" in doc


def test_the_reference_implementation_is_not_imported_by_shipped_code():
    """The reference (pycatch22) is GPL-3.0 and this fork is MIT."""
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
    "chunk-wide-quantile": (
        "        q = np.quantile(z, [1.0 / 3.0, 2.0 / 3.0], axis=1)",
        "        qc = np.quantile(z.ravel(), [1.0 / 3.0, 2.0 / 3.0])\n"
        "        q = np.broadcast_to(qc[:, None], (2, rows))"),
    "word-order-swapped": (
        "    code = letter[:, :-1] * NUM_LETTERS + letter[:, 1:]",
        "    code = letter[:, 1:] * NUM_LETTERS + letter[:, :-1]"),
    "no-overflow-guard": ("bad |= ~(sd > NOISE_FLOOR) | ~np.isfinite(sd)",
                          "bad |= ~(sd > NOISE_FLOOR)"),
    "no-floor": ("bad |= ~(sd > NOISE_FLOOR) | ~np.isfinite(sd)",
                 "bad |= ~(sd > 0.0)"),
}


def mutant(name):
    old, new = MUTANTS[name]
    assert SRC.count(old) == 1, (name, SRC.count(old))
    ns = {}
    exec(compile(SRC.replace(old, new), f"<mutant {name}>", "exec"), ns)
    return ns["c22_entropy_pairs"]


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
    f = FRAMES[frame]
    assert _leaks(c22_entropy_pairs, f, _offsets(len(f)), splices=8) == []


@pytest.mark.parametrize("length", [MIN_LENGTH, 120, 250])
def test_the_sweep_at_non_default_lengths(length):
    f = FRAMES["walk"]
    assert _leaks(lambda s: c22_entropy_pairs(s, length=length), f,
                  _offsets(len(f), length), splices=4) == []


@pytest.mark.parametrize("name", ["write-back-dated", "window-one-ahead",
                                  "window-ten-ahead", "returns-rolled"])
def test_each_look_ahead_mutant_is_caught(name):
    f = FRAMES["walk"]
    hits = _leaks(mutant(name), f, _offsets(len(f)), splices=8)
    assert len(hits) >= 10, (name, len(hits))


def test_a_one_bar_mutant_can_only_move_bars_from_the_cut_backwards():
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
    assert seen >= 5, seen


def test_the_mask_mutant_is_dead_on_a_clean_frame_and_caught_on_a_dirty_one():
    fn = mutant("mask-back-dated")
    clean = FRAMES["walk"]
    assert same(c22_entropy_pairs(clean), fn(clean))
    caught = 0
    for j in _offsets(len(clean), count=12):
        dirty = clean.copy()
        dirty.iloc[j] = np.nan
        a = np.asarray(c22_entropy_pairs(dirty), float)
        b = np.asarray(fn(dirty), float)
        moved = np.where(~((a == b) | (np.isnan(a) & np.isnan(b))))[0]
        if len(moved):
            caught += 1
            assert int(moved.min()) == j - 1, (j, moved[:4])
    assert caught == 12, caught


@pytest.mark.parametrize("name", ["chunk-wide-demean", "chunk-wide-sd"])
@pytest.mark.parametrize("frame", ["walk", "tick-rounded", "penny"])
def test_two_mutants_are_dead_by_affine_invariance(name, frame):
    """`chunk-wide-demean` and `chunk-wide-sd` replace each row's own mean or
    standard deviation with the whole CHUNK's, which is the SAME affine
    invariance as `test_z_score_and_its_divisor_are_inert` applied cross-row
    instead of cross-reading: the comparisons that decide each letter are
    unchanged, so the letter sequence -- and hence every downstream float
    operation on it -- is bit-identical to the real module."""
    fn = mutant(name)
    assert same(base(frame), fn(FRAMES[frame])), (name, frame)


@pytest.mark.parametrize("frame", ["walk", "tick-rounded", "penny"])
def test_the_word_order_swapped_mutant_is_dead_up_to_summation_order(frame):
    """Entropy is a function of the MULTISET of word probabilities: swapping
    (letter[t], letter[t+1]) for (letter[t+1], letter[t]) transposes the 3x3
    count table, which permutes which of the 9 cells holds which count but
    changes no count's VALUE. The two sums `-sum(p log p)` therefore add the
    same nine terms in a different order -- mathematically identical, and
    floating-point addition is not associative, so this is NOT asserted
    bit-equal: measured gap is under 1e-9 on every fired bar of three
    frames, not `== 0.0`."""
    fn = mutant("word-order-swapped")
    moved, mask = diff_bars(base(frame), fn(FRAMES[frame]), tol=1e-9)
    assert mask == 0
    assert moved == 0, (frame, moved)


def test_the_chunk_wide_quantile_mutant_is_caught():
    """The cross-row read that DOES bite: taking the quantile cut points
    from the whole chunk's flattened returns instead of each row's own."""
    fn = mutant("chunk-wide-quantile")
    hits = _leaks(fn, FRAMES["walk"], _offsets(1500), splices=8)
    assert len(hits) >= 10, len(hits)
    for frame in ("walk", "tick-rounded", "penny"):
        got = fn(FRAMES[frame])
        assert diff_bars(base(frame), got, tol=1e-9)[0] >= 500, frame


# ------------------------------------------------------------- Gate C
@pytest.mark.parametrize("frame", list(FRAMES))
def test_every_bar_with_a_full_window_fires(frame):
    s = base(frame)
    assert int(s.notna().sum()) == len(s) - LENGTH
    assert int(s.notna().values.argmax()) == LENGTH
    assert s.iloc[:LENGTH].isna().all()


@pytest.mark.parametrize("frame", STOCHASTIC)
def test_the_column_is_not_constant_on_a_stochastic_frame(frame):
    a = base(frame).dropna().to_numpy()
    assert len(set(a.tolist())) >= 20, frame
    assert float(a.max() - a.min()) > 0.05, frame


def test_a_tick_rounded_penny_frame_still_fires_everywhere():
    """The issue's own worry: shape features of returns can read BIST tick
    rounding. A 2-lira stock on a 1-kurus tick collapses many returns into
    one letter, and the column still fires on every full-window bar."""
    f = FRAMES["penny"]
    r = np.asarray(f, float)
    r = r[1:] / r[:-1] - 1.0
    assert float(np.mean(r == 0.0)) > 0.15
    s = base("penny")
    assert int(s.notna().sum()) == len(f) - LENGTH


def test_a_flat_run_blanks_from_the_first_all_zero_window():
    c = FRAMES["walk"].to_numpy().copy()
    c[400:] = c[399]
    s = c22_entropy_pairs(Series(c[:700]))
    assert int(s.notna().sum()) == 399
    assert not math.isnan(float(s.iloc[498]))
    assert s.iloc[499:].isna().all()


@pytest.mark.parametrize("step", [0.01, 0.001, -0.005])
def test_an_exact_geometric_ladder_never_fires_and_the_floor_is_why(step):
    f = ladder(step=step)
    assert int(c22_entropy_pairs(f).notna().sum()) == 0
    win, _ = windows(f)
    assert float(win.std(axis=1, ddof=ZSCORE_DDOF).max()) < NOISE_FLOOR
    unguarded = np.asarray(mutant("no-floor")(f), float)
    live = unguarded[~np.isnan(unguarded)]
    assert live.size == 1400, live.size
    assert float(live.min()) >= -1e-9
    assert float(live.max()) <= MAX_ENTROPY + 1e-9


# ------------------------------------------------------------- Gate D
@pytest.mark.parametrize("factor", [8.0, 64.0, 2.0 ** -40, 2.0 ** 40])
@pytest.mark.parametrize("frame", list(FRAMES))
def test_bit_identical_under_a_power_of_two_price_rescale(frame, factor):
    """The price enters only as `c[t] / c[t-1]`, so a power-of-two rescale
    multiplies and divides out exactly in floating point."""
    f = FRAMES[frame]
    a = c22_entropy_pairs(f)
    b = c22_entropy_pairs(f * factor)
    assert same(a, b), (frame, factor)


@pytest.mark.parametrize("factor", [10.0, 3.7, 0.1, 1.0000001])
def test_the_column_is_blind_to_an_inexact_return_rescale(factor):
    """Not bit-identical by CONSTRUCTION like the power-of-two case above --
    this scales the RETURNS stream itself (a synthetic price built to
    realise `r' = factor * r`), which an inexact rescale does not cancel
    out of a float division the same way. Whether every bar still agrees is
    therefore a measured fact and not an identity, so the bound is a
    tolerance rather than `== 0`."""
    base_f = FRAMES["walk"]
    r = base_f.to_numpy()[1:] / base_f.to_numpy()[:-1] - 1.0
    scaled = np.empty(len(base_f))
    scaled[0] = 100.0
    scaled[1:] = scaled[0] * np.cumprod(1.0 + factor * r)
    a = base("walk").to_numpy()
    b = c22_entropy_pairs(Series(scaled)).to_numpy()
    moved, mask = diff_bars(a, b, tol=1e-9)
    assert mask == 0
    assert moved <= len(a) // 20, (factor, moved)


def test_zero_lt_fires_lt_n_at_the_default_length():
    s = base("walk")
    assert 0 < int(s.notna().sum()) < len(s)
