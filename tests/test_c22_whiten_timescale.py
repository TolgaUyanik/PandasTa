# -*- coding: utf-8 -*-
"""C22-WHITEN-TIMESCALE: `c22_whiten_timescale`, catch22's
`FC_LocalSimple_mean1_tauresrat` over the last 100 daily returns (issue #139).

Every number here was measured by `docs/measure_c22_whiten_timescale.py` on
this machine; the receipt is `docs/C22WhitenTimescaleMeasured.md`. What is
pinned, in order of how much it would hurt to lose:

1. **The definition, matched exactly.** A literal re-spelling of the
   published definition -- z-scored window, FFT autocorrelation padded to
   twice the next power of two, `while acf[z] > 0 and z < maxtau: z++`, the
   mean-forecast residual by a loop -- agrees on 8,400 of 8,400 windows of six
   frames (every window) under numpy's default dispatch and on 8,399 with
   AVX2 and FMA3 disabled (`docs/measure_c22_whiten_timescale_cpu.py`). The one split
   is a cosine window whose deciding lagged sum is zero in exact arithmetic,
   and there the exact oracle sides with the module. An exact `Fraction`
   oracle that rounds zero times disagrees on 0 of 648 sampled windows, and on
   0 of all 1,400 cosine windows under both dispatches. The module never divides: the
   autocorrelation's divisor is positive, so only the sign of each lagged sum
   is needed.
2. **THE NUMERATOR IS 1 ON NOISE, SO THE COLUMN IS `1 / tau(returns)`.**
   Differencing a short-memory series puts its lag-1 autocorrelation near
   -1/2 (measured maxima -0.0812 to -0.3328 on the four noise-like frames),
   so the residual crosses at lag 1 on 1,400 of 1,400 windows of the walk,
   the tick-rounded walk, the penny frame and the Student-t path, and on
   1,397 of 1,400 of the AR(1) at phi = 0.6. Only the exact cosine frame,
   whose residual is smooth too, has it at 0 of 1,400. A consumer has to know
   the "ratio" is a reciprocal ladder 1, 1/2, 1/3, ... in practice.
3. **It is not `firstzero_ac`.** Kats' `FIRSTZEROAC_100` reports the first
   positive-then-negative sign change, so a window whose lag-1
   autocorrelation is already negative -- 368 to 821 of 1,400 windows on the
   four noise-like frames -- reads 1 here and a later lag there. Per-frame
   Spearman against it runs from -0.999 (AR(1)) to +0.634 (tick-rounded).
4. **Causality.** 0 of 35 offsets leak on each of six frames with eight
   splices apiece, and 0 of 35 at `length` 10, 30 and 250. Seven mutants are
   read off this module's source, edited and exec'd in memory. ⚠ A ONE-BAR
   look-ahead is caught at only 8 of 35 offsets on the walk (20 of 35 on the
   AR(1) frame) because the column ties on 84.8% to 93.6% of neighbouring
   pairs on the stochastic frames; the ten-bar mutant is caught 26 to 35 of
   35.
5. **Scale-free by construction.** The price enters only as `c[t] / c[t-1]`,
   so x8, x64, x2**-40 and x2**40 are bit-identical on all six frames. x10,
   x3.7, x0.1 and x1.0000001 move 0 bars on the five stochastic frames
   (smallest deciding |lagged sum| / sum of squares 1.66e-05) and ⚠ 24 to 33
   of 1,400 on the exact cosine frame, where a deciding lagged sum is zero in
   exact arithmetic and sits at 6.8e-18 -- a rounding coin flip, pinned as a
   bound with the masks equal.
6. **One blanking rule.** NaN unless both the returns and the residual have a
   root mean square of deviations above 9.09e-13. Inert on every noisy frame;
   it empties a flat run, an exactly geometric ladder (which unguarded reads
   a value on every sampled window), and returns that are an exact line in
   the bar index (window sd >= 2.89e-04, residual sd <= 2.37e-16).
7. **Bad data.** A bad close empties exactly its own 101 windows; a ratio
   that overflows empties 100; a window whose sums of squares overflow
   empties 100 -- without that guard those 100 bars read 1.0, a legal value.
8. **Gate E is OWED** (no ledger row; `GATE_E_PENDING_OK=1` on the way to
   `dev`). The 2026-10-24 screen's figure -- max |rho| 0.2521 vs `mad_pct`,
   SHIP -- was measured on the PROTOTYPE and is an expectation for this
   column, not a result for it.

Not pinned on purpose: exact counts of distinct values, exact bars-moved
counts under an inexact rescale, and any rho to 1e-6. Those move with
numpy's CPU dispatch; the tests pin bounds and bands, and the docstrings
state the local figure.
"""
import csv
import importlib
import math
from fractions import Fraction
from pathlib import Path

import numpy as np
import pytest
from pandas import DataFrame, Series

from .context import pandas_ta
from pandas_ta.statistics.c22_whiten_timescale import (
    CHUNK_VALUES, MIN_LENGTH, NOISE_FLOOR, TRAIN_LENGTH, c22_whiten_timescale)

ROOT = Path(__file__).resolve().parent.parent
MODULE = importlib.import_module("pandas_ta.statistics.c22_whiten_timescale")
SRC = Path(MODULE.__file__).read_text(encoding="utf-8")
LENGTH = 100

#: Strides for the oracles too slow for all 1,400 windows of a frame. Every
#: count asserted below is a count of what actually ran.
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


def linear_returns(n=1500, a=0.001, b=1e-5):
    r = a + b * np.arange(n, dtype=float)
    return Series(100.0 * np.cumprod(1.0 + r))


FRAMES = {
    "walk": walk(),
    "tick-rounded": tick_rounded(),
    "penny": penny(),
    "ar1": ar1(),
    "cosine": cosine_returns(),
    "student-t": student_t(),
}
#: The five frames whose returns are not deterministic.
STOCHASTIC = [k for k in FRAMES if k != "cosine"]
#: The four whose returns have short memory: the numerator is 1 on all.
NOISE_LIKE = ["walk", "tick-rounded", "penny", "student-t"]
_BASE = {}


def base(name):
    if name not in _BASE:
        _BASE[name] = c22_whiten_timescale(FRAMES[name])
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
    rx, ry = x[m].rank(), y[m].rank()
    return float(np.corrcoef(rx, ry)[0, 1])


# ------------------------------------------------------------- Gate A
def ref_acf(y):
    """catch22's `co_autocorrs` as defined: FFT of the demeaned series
    padded to twice the next power of two, inverse FFT of the power
    spectrum, divided by lag 0. Shares no code with the module."""
    y = np.asarray(y, float)
    nfft = 1 << int(math.ceil(math.log2(len(y))))
    f = np.fft.fft(y - y.mean(), 2 * nfft)
    a = np.fft.ifft(f * np.conj(f)).real
    return a / a[0]


def ref_firstzero(y):
    """catch22's `co_firstzero`, `maxtau = size`."""
    acf = ref_acf(y)
    z = 0
    while acf[z] > 0 and z < len(y):
        z += 1
    return z


def ref_value(window, train=1, zscore=True):
    y = np.asarray(window, float)
    if zscore:
        y = (y - y.mean()) / y.std(ddof=1)
    res = np.array([y[i + train] - y[i:i + train].mean()
                    for i in range(len(y) - train)])
    return ref_firstzero(res) / ref_firstzero(y)


def exact_firstzero(y):
    q = [Fraction(float(v)) for v in y]
    mu = sum(q) / len(q)
    d = [v - mu for v in q]
    for k in range(1, len(d)):
        if not sum(d[i] * d[i + k] for i in range(len(d) - k)) > 0:
            return k
    return len(d)


def exact_value(window):
    y = [float(v) for v in window]
    return exact_firstzero([y[i + 1] - y[i] for i in range(len(y) - 1)]) \
        / exact_firstzero(y)


@pytest.mark.parametrize("frame", list(FRAMES))
def test_bit_equal_to_the_literal_catch22_spelling(frame):
    """Every third window here; every window in the measurement script's
    section A1 (8,400 of 8,400 with numpy's default dispatch, 8,399 with
    AVX2 and FMA3 disabled -- `docs/measure_c22_whiten_timescale_cpu.py A`).

    Fixed after a run with numpy's AVX2 and FMA3 dispatch disabled failed
    it: this test used to demand 0 disagreements on the cosine frame too.
    That frame's deciding lagged sum is zero for the ideal cosine and 6.8e-18
    of the sum of squares on the rounded inputs, so its sign is a rounding
    coin flip for any float spelling. Under
    `NPY_DISABLE_CPU_FEATURES="AVX2 FMA3"` the FFT reference (window 1122)
    flips the wrong way, while the module agrees with the exact oracle on all
    1,400 cosine windows under both dispatches (section X of both scripts). So on the five stochastic
    frames the two spellings must still agree exactly. On the cosine frame a
    disagreement is allowed only where the exact rational oracle sides with
    the MODULE, and only on a handful of windows."""
    win, bars = windows(FRAMES[frame])
    mine = base(frame).to_numpy()[bars][::3]
    sub = win[::3]
    ref = [ref_value(w) for w in sub]
    assert diff_bars(mine, ref)[1] == 0
    split = [i for i in range(len(sub)) if mine[i] != ref[i]]
    if frame != "cosine":
        assert split == [], (frame, split[:4])
    assert len(split) <= 5, (frame, len(split))
    for i in split:
        assert mine[i] == exact_value(sub[i]), (frame, i)


def test_the_module_matches_the_exact_oracle_on_every_cosine_window():
    """The frame where float spellings can disagree: the module equals the
    rounding-free oracle on all 1,400 windows, under both CPU dispatches
    measured: numpy's default and AVX2/FMA3 disabled
    (`docs/measure_c22_whiten_timescale.py X` and `..._cpu.py X`, each
    printing 0 disagreements of 1400)."""
    win, bars = windows(FRAMES["cosine"])
    mine = base("cosine").to_numpy()[bars]
    assert all(mine[i] == exact_value(win[i]) for i in range(win.shape[0]))
    assert win.shape[0] == 1400


@pytest.mark.parametrize("frame", list(FRAMES))
def test_bit_equal_to_the_exact_rational_oracle(frame):
    win, bars = windows(FRAMES[frame])
    mine = base(frame).to_numpy()[bars]
    idx = range(0, win.shape[0], EXACT_STRIDE)
    for i in idx:
        assert mine[i] == exact_value(win[i]), (frame, i)
    assert len(idx) == 15


@pytest.mark.parametrize("frame", NOISE_LIKE)
def test_the_numerator_is_one_on_every_noise_like_window(frame):
    """Item 2 of this file's docstring: the column IS `1 / tau(returns)`."""
    win, bars = windows(FRAMES[frame])
    mine = base(frame).to_numpy()[bars]
    tau_r = np.array([ref_firstzero(w) for w in win])
    assert np.array_equal(mine, 1.0 / tau_r)


def test_the_numerator_leaves_one_only_on_persistent_or_smooth_returns():
    """1,397 of 1,400 on the AR(1) at phi = 0.6, 691 at 0.9; 0 of 1,400 on
    the exact cosine, whose residual is a cosine too."""
    def ones(f):
        win, _ = windows(f)
        return sum(ref_firstzero(np.diff(w)) == 1 for w in win)
    assert ones(FRAMES["ar1"]) >= 1390
    assert 500 <= ones(ar1(phi=0.9)) <= 900
    assert ones(FRAMES["cosine"]) == 0


@pytest.mark.parametrize("frame", list(FRAMES))
def test_z_scoring_the_window_changes_nothing(frame):
    win, _ = windows(FRAMES[frame])
    a = [ref_value(w, zscore=True) for w in win[::WINDOW_STRIDE]]
    b = [ref_value(w, zscore=False) for w in win[::WINDOW_STRIDE]]
    assert diff_bars(a, b)[0] == 0


def test_the_forecast_is_catch22s_mean1():
    """The `1` in `FC_LocalSimple_mean1`: the residual is `r[t] - r[t-1]`."""
    assert TRAIN_LENGTH == 1
    assert "resid = block[:, TRAIN_LENGTH:] - fc" in SRC


@pytest.mark.parametrize("frame", NOISE_LIKE)
def test_it_is_not_firstzero_ac(frame):
    """Windows whose returns' lag-1 autocorrelation is already <= 0 read 1
    here; Kats' rule cannot report lag 1 (its smallest value is 2). 368 to
    821 of 1,400 such windows on these frames."""
    s = base(frame).dropna().to_numpy()
    fz = pandas_ta.firstzero_ac(FRAMES[frame]).dropna().to_numpy()
    assert 300 <= int(np.sum(s == 1.0)) <= 900
    assert fz.min() >= 2.0
    assert abs(spearman(base(frame), pandas_ta.firstzero_ac(FRAMES[frame]))) < 0.85


def test_the_reference_implementation_is_not_imported_by_shipped_code():
    """pycatch22 is GPL-3.0 and this fork is MIT."""
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
def test_the_output_is_a_ratio_of_lags_in_range(frame):
    s = base(frame).dropna().to_numpy()
    assert s.min() >= 1.0 / (LENGTH - 1) and s.max() <= LENGTH - 2
    win, _ = windows(FRAMES[frame])
    lags = [ref_firstzero(w) for w in win[::WINDOW_STRIDE]]
    assert max(lags) <= 20, "largest crossing lag measured on these frames"


def test_the_module_docstring_attributes_the_source():
    doc = c22_whiten_timescale.__doc__
    for needle in ("Lubba", "33:1821", "FC_LocalSimple_mean1_tauresrat",
                   "FC_LocalSimple", "CO_FirstZero", "GPL-3.0", "#139"):
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
    "chunk-wide-demean": ("d = x - x.mean(axis=1, keepdims=True)",
                          "d = x - x.mean()"),
    "no-overflow-guard": ("bad |= ~np.isfinite(ss_r) | ~np.isfinite(ss_e)",
                          "bad |= np.zeros_like(bad)"),
}


def mutant(name):
    """Read this module off disk, edit one line, exec it in memory."""
    old, new = MUTANTS[name]
    assert SRC.count(old) == 1, (name, SRC.count(old))
    ns = {}
    exec(compile(SRC.replace(old, new), f"<mutant {name}>", "exec"), ns)
    return ns["c22_whiten_timescale"]


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
            other = np.asarray(fn(_spliced(close, j, seed=909 + 7919 * s)), float)
            if not same(bad[:j], other[:j]):
                hits.append(j)
                break
    return hits


@pytest.mark.parametrize("frame", list(FRAMES))
def test_real_module_never_reads_the_future(frame):
    f = FRAMES[frame]
    assert _leaks(c22_whiten_timescale, f, _offsets(len(f)), splices=8) == []


@pytest.mark.parametrize("length", [MIN_LENGTH, 30, 250])
def test_the_sweep_at_non_default_lengths(length):
    f = FRAMES["walk"]
    assert _leaks(lambda s: c22_whiten_timescale(s, length=length), f,
                  _offsets(len(f), length), splices=4) == []


@pytest.mark.parametrize("name", ["write-back-dated", "window-one-ahead",
                                  "window-ten-ahead", "returns-rolled",
                                  "chunk-wide-demean"])
def test_each_mutant_is_caught(name):
    """The same sweep the real module passes clean. Measured on the walk:
    8 of 35 offsets for the three one-bar mutants, 29 for the ten-bar one and
    33 for the chunk-wide demean (which reads other rows' returns). Bounds,
    because where the splices land moves with numpy's dispatch."""
    f = FRAMES["walk"]
    hits = _leaks(mutant(name), f, _offsets(len(f)), splices=8)
    assert len(hits) >= 4, (name, len(hits))
    if name in ("window-ten-ahead", "chunk-wide-demean"):
        assert len(hits) >= 20, (name, len(hits))


def test_a_one_bar_mutant_can_only_move_bars_from_the_cut_backwards():
    """Where a back-dated write moves a pre-splice bar, the first moved bar
    is J-1 -- 4 of 35 offsets on the walk."""
    fn = mutant("write-back-dated")
    f = FRAMES["walk"]
    bad = np.asarray(fn(f), float)
    seen = 0
    for j in _offsets(len(f)):
        other = np.asarray(fn(_spliced(f, j)), float)
        moved = np.where(~((bad[:j] == other[:j])
                           | (np.isnan(bad[:j]) & np.isnan(other[:j]))))[0]
        if len(moved):
            seen += 1
            assert int(moved.min()) == j - 1, (j, moved[:4])
    assert seen >= 1, seen


def test_the_mask_mutant_is_dead_on_a_clean_frame_and_caught_on_a_dirty_one():
    """Bit-equal on the clean walk; one bad close at J moves exactly bar J-1
    first, 12 of 12."""
    fn = mutant("mask-back-dated")
    clean = FRAMES["walk"]
    assert same(c22_whiten_timescale(clean), fn(clean))
    caught = 0
    for j in _offsets(len(clean), count=12):
        dirty = clean.copy()
        dirty.iloc[j] = np.nan
        a = np.asarray(c22_whiten_timescale(dirty), float)
        b = np.asarray(fn(dirty), float)
        moved = np.where(~((a == b) | (np.isnan(a) & np.isnan(b))))[0]
        if len(moved):
            caught += 1
            assert int(moved.min()) == j - 1, (j, moved[:4])
    assert caught == 12, caught


@pytest.mark.parametrize("frame", STOCHASTIC)
def test_the_column_ties_often_enough_to_hide_a_one_bar_shift(frame):
    """84.8% to 93.6% of neighbouring pairs equal (measured)."""
    s = base(frame).dropna().to_numpy()
    assert float(np.mean(s[1:] == s[:-1])) > 0.75


# ------------------------------------------------------------- Gate C
@pytest.mark.parametrize("frame", list(FRAMES))
def test_every_bar_with_a_full_window_fires(frame):
    """1,400 of 1,500 on every frame; the first fired bar is `length`."""
    s = base(frame)
    assert int(s.notna().sum()) == len(s) - LENGTH
    assert int(s.notna().values.argmax()) == LENGTH


@pytest.mark.parametrize("frame", STOCHASTIC)
def test_the_column_is_not_constant(frame):
    """6 to 8 distinct values on the noise-like frames, 17 on the AR(1)."""
    a = base(frame).dropna().to_numpy()
    assert len(set(a.tolist())) >= 4, frame
    assert a.max() > a.min()


def test_a_tick_rounded_penny_frame_still_fires_everywhere():
    """The issue's worry: 21.7% of the penny frame's returns are exactly 0,
    and the column fires on all 1,400 bars with the walk's median, 0.5."""
    f = FRAMES["penny"]
    r = np.asarray(f, float)
    r = r[1:] / r[:-1] - 1.0
    assert float(np.mean(r == 0.0)) > 0.15
    s = base("penny")
    assert int(s.notna().sum()) == len(f) - LENGTH
    assert float(s.median()) == float(base("walk").median()) == 0.5


def test_a_flat_run_blanks_after_the_last_window_with_a_move():
    f = FRAMES["walk"].copy()
    f.iloc[400:] = f.iloc[400]
    fired = np.where(c22_whiten_timescale(f).notna().to_numpy())[0]
    assert int(fired.max()) == 499 and fired.size == 400


@pytest.mark.parametrize("step", [0.01, 0.001, -0.005])
def test_an_exact_geometric_ladder_never_fires_and_the_floor_is_why(step):
    f = ladder(step=step)
    assert int(c22_whiten_timescale(f).notna().sum()) == 0
    win, _ = windows(f)
    assert all(not math.isnan(ref_value(w)) for w in win[::WINDOW_STRIDE])


def test_returns_on_an_exact_line_blank_although_the_window_varies():
    f = linear_returns()
    assert int(c22_whiten_timescale(f).notna().sum()) == 0
    win, _ = windows(f)
    assert min(np.std(w) for w in win) > 1e8 * NOISE_FLOOR
    assert max(np.std(np.diff(w)) for w in win) < NOISE_FLOOR


def test_a_price_rising_one_kurus_a_bar_fires_unlike_c22_periodicity():
    f = Series(100.0 + 0.01 * np.arange(1500, dtype=float))
    assert int(c22_whiten_timescale(f).notna().sum()) == 1400
    assert int(pandas_ta.c22_periodicity(f).notna().sum()) == 0


@pytest.mark.parametrize("frame", list(FRAMES))
def test_the_floor_is_inert_on_anything_price_shaped(frame):
    win, bars = windows(FRAMES[frame])
    mine = base(frame).to_numpy()[bars]
    for i in range(0, win.shape[0], 23):
        assert mine[i] == ref_value(win[i]), (frame, i)


# ------------------------------------------------------------- Gate D
@pytest.mark.parametrize("factor", [8.0, 64.0, 2.0 ** -40, 2.0 ** 40])
@pytest.mark.parametrize("frame", list(FRAMES))
def test_an_exact_binary_rescale_is_bit_identical(frame, factor):
    """scale: the price enters only as `c[t] / c[t-1]`."""
    assert same(base(frame), c22_whiten_timescale(FRAMES[frame] * factor))


@pytest.mark.parametrize("factor", [8.0, 64.0])
@pytest.mark.parametrize("length", [MIN_LENGTH, 30, 250])
def test_the_scale_invariance_holds_at_non_default_lengths(length, factor):
    f = FRAMES["walk"]
    assert same(c22_whiten_timescale(f, length=length),
                c22_whiten_timescale(f * factor, length=length))


@pytest.mark.parametrize("price", [1e-6, 1e6, 1e100])
def test_the_scale_invariance_holds_at_every_price_level(price):
    f = walk(level=price)
    b = c22_whiten_timescale(f)
    assert int(b.notna().sum()) == len(f) - LENGTH
    assert same(b, c22_whiten_timescale(f * 8.0))


@pytest.mark.parametrize("factor", [10.0, 3.7, 0.1, 1.0000001])
@pytest.mark.parametrize("frame", list(FRAMES))
def test_an_inexact_rescale_moves_almost_nothing(frame, factor):
    """0 bars measured on every stochastic cell (bound 5); 24 to 33 of 1,400
    on the exact cosine, whose deciding lagged sum is zero in exact
    arithmetic (bound 60). NaN masks equal everywhere."""
    moved, mask = diff_bars(base(frame), c22_whiten_timescale(FRAMES[frame] * factor))
    assert moved <= (60 if frame == "cosine" else 5), (frame, factor, moved)
    assert mask == 0, (frame, factor, mask)


@pytest.mark.parametrize("frame", STOCHASTIC)
def test_the_deciding_lagged_sums_never_run_near_a_rounding_flip(frame):
    """Why the stochastic cells above come out 0: the smallest |lagged sum|
    / sum of squares at a scanned lag is 1.66e-05 (penny) or more."""
    win, _ = windows(FRAMES[frame])
    worst = math.inf
    for w in win[::WINDOW_STRIDE]:
        for y in (w, np.diff(w)):
            d = y - y.mean()
            ss = float(d @ d)
            for k in range(1, len(d)):
                p = float(np.dot(d[:-k], d[k:]))
                worst = min(worst, abs(p) / ss)
                if not p > 0:
                    break
    assert worst > 1e-7, (frame, worst)


def test_it_is_not_blind_to_the_order_of_the_returns():
    """So the bit-identity is not vacuous: 320 of 467 permuted windows move."""
    win, bars = windows(FRAMES["walk"])
    mine = base("walk").to_numpy()[bars][::3]
    rng = np.random.default_rng(5)
    other = [ref_value(rng.permutation(w)) for w in win[::3]]
    assert diff_bars(mine, other)[0] >= 200


@pytest.mark.parametrize("frame", list(FRAMES))
def test_it_fires_strictly_between_zero_and_n(frame):
    s = base(frame)
    assert 0 < int(s.notna().sum()) < len(s)


# ------------------------------------------------------------- bad data
@pytest.mark.parametrize("bad", [np.nan, np.inf, -np.inf, 0.0, -5.0, 1e-310])
def test_a_bad_close_empties_exactly_its_own_windows(bad):
    f = FRAMES["walk"].copy()
    f.iloc[700] = bad
    blank = np.where(c22_whiten_timescale(f).isna().to_numpy())[0]
    after = blank[blank >= LENGTH]
    assert after.size == 101
    assert int(after.min()) == 700 and int(after.max()) == 800


def test_a_close_pair_whose_ratio_overflows_empties_its_windows():
    f = FRAMES["walk"].copy()
    f.iloc[700] = 1e-300
    f.iloc[701] = 1e100
    blank = np.where(c22_whiten_timescale(f).isna().to_numpy())[0]
    after = blank[blank >= LENGTH]
    assert after.size == 100
    assert int(after.min()) == 701 and int(after.max()) == 800


def test_a_finite_but_enormous_return_blanks_rather_than_reading_one():
    """A return of 1e200 is finite, but its square overflows. Without the
    guard those 100 bars read 1.0 -- a legal value, not a blank."""
    f = FRAMES["walk"].copy()
    f.iloc[700] = 1e-100
    f.iloc[701] = 1e100
    s = c22_whiten_timescale(f)
    blank = np.where(s.isna().to_numpy())[0]
    assert blank[blank >= LENGTH].size == 100
    without = np.asarray(mutant("no-overflow-guard")(f), float)
    saved = np.where(np.isnan(s.to_numpy()) & ~np.isnan(without))[0]
    assert saved.size == 100
    assert set(without[saved].tolist()) == {1.0}


@pytest.mark.parametrize("frame", list(FRAMES))
def test_the_overflow_guard_is_inert_on_every_realistic_frame(frame):
    assert same(base(frame), mutant("no-overflow-guard")(FRAMES[frame]))


def test_the_overflow_guard_is_inert_where_the_sums_stay_finite():
    f = FRAMES["walk"].copy()
    f.iloc[700] = 1e-50
    f.iloc[701] = 1e27
    blank = np.where(c22_whiten_timescale(f).isna().to_numpy())[0]
    assert blank[blank >= LENGTH].size == 0


@pytest.mark.parametrize("n,fires", [(99, None), (100, None), (101, 1),
                                     (102, 2)])
def test_a_short_input_returns_none_until_one_window_exists(n, fires):
    s = c22_whiten_timescale(FRAMES["walk"].iloc[:n])
    if fires is None:
        assert s is None
    else:
        assert int(s.notna().sum()) == fires


@pytest.mark.parametrize("length,name,fires", [
    (None, "C22WHITEN_100", 1400),
    (0, "C22WHITEN_100", 1400),
    (MIN_LENGTH - 1, "C22WHITEN_100", 1400),
    (MIN_LENGTH, f"C22WHITEN_{MIN_LENGTH}", 1500 - MIN_LENGTH),
    (250, "C22WHITEN_250", 1250),
    (250.7, "C22WHITEN_250", 1250),
])
def test_the_length_guard_band(length, name, fires):
    s = c22_whiten_timescale(FRAMES["walk"], length=length)
    assert s.name == name
    assert int(s.notna().sum()) == fires


def test_the_offset_and_the_fill_are_the_house_ones():
    s = c22_whiten_timescale(FRAMES["walk"], offset=2)
    assert same(s.to_numpy()[2:], base("walk").to_numpy()[:-2])
    s = c22_whiten_timescale(FRAMES["walk"], fillna=-1)
    assert int(s.isna().sum()) == 0
    assert int((s == -1).sum()) == LENGTH


@pytest.mark.parametrize("budget", [100, 400, 1024])
def test_the_chunk_budget_cannot_change_a_value(budget):
    want = base("walk")
    MODULE.CHUNK_VALUES = budget
    try:
        got = c22_whiten_timescale(FRAMES["walk"])
    finally:
        MODULE.CHUNK_VALUES = CHUNK_VALUES
    assert same(want, got)


# ------------------------------------------------------------- wiring
def test_the_five_wiring_touch_points():
    assert Path(MODULE.__file__).exists()
    assert hasattr(pandas_ta.statistics, "c22_whiten_timescale")
    assert "c22_whiten_timescale" in pandas_ta.Category["statistics"]
    assert hasattr(pandas_ta.core.AnalysisIndicators, "c22_whiten_timescale")
    assert (ROOT / "tests" / "test_c22_whiten_timescale.py").exists()


def test_the_accessor_forwards_its_parameters():
    df = DataFrame({"close": FRAMES["walk"].to_numpy()})
    acc = df.ta.c22_whiten_timescale()
    assert acc.name == "C22WHITEN_100"
    assert same(acc, base("walk"))
    acc = df.ta.c22_whiten_timescale(length=250, offset=1)
    assert acc.name == "C22WHITEN_250"
    assert same(acc, c22_whiten_timescale(FRAMES["walk"], length=250, offset=1))


def test_the_dictionary_row_describes_this_column():
    text = (ROOT / "docs" / "IndicatorDictionary.md").read_text(encoding="utf-8")
    assert "C22WHITEN_100" in text
    assert "c22_whiten_timescale" in text


# -------------------------------------------------------- Gate E, owed
RECEIPT = ROOT / "docs" / "C22WhitenTimescaleMeasured.md"


def test_the_gate_e_row_is_owed():
    """No ledger row yet: Gate E needs the private engine and the BIST cache,
    and the owner records the row before the release. When it lands, swap
    this test for one that pins the row, as `test_c22_periodicity.py` did."""
    with (ROOT / "docs" / "gate_e_ledger.csv").open(newline="", encoding="utf-8") as fh:
        rows = [r for r in csv.DictReader(fh)
                if r["indicator"] == "c22_whiten_timescale"]
    assert rows == []
    text = RECEIPT.read_text(encoding="utf-8")
    assert "Gate E: pending, run by issue-solver" in text
    assert "0.2521" in text and "prototype" in text.lower()


def test_the_receipt_states_the_reciprocal_ladder():
    text = RECEIPT.read_text(encoding="utf-8")
    assert "1 / tau" in text
    assert "8,400 of 8,400" in text
