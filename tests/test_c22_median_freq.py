# -*- coding: utf-8 -*-
"""C22-MEDIAN-FREQ: `c22_median_freq`, hctsa's `SP_Summaries_fft_wq_50` --
the frequency below which half the power of the z-scored last 100 daily
returns' FFT spectrum lies (issue #138).

Every number here was measured by running this module and
`docs/measure_c22_median_freq.py` on this machine; the receipt is
`docs/C22MedianFreqMeasured.md`. What is pinned, in order of how much it
would hurt to lose:

1. **The definition, against an oracle that shares no code path with it.**
   `direct_dft_median_freq` re-spells the feature with an explicit O(N *
   NFFT/2) DFT (`math.cos`/`math.sin` on angles reduced modulo NFFT, all
   sums by `math.fsum`) -- no FFT. The shipped `rfft`-based column agrees
   EXACTLY (output `==`, not a tolerance) on all 1,200 windows the receipt
   samples (every 7th window of six frames). That is only meaningful
   because the output is one of 65 discrete grid values and no sampled
   window sits near a grid boundary: the smallest |running power - half|
   / total seen on any of them is 2.1e-6, nine orders above float noise.
   Designed windows with a known answer pin the grid itself: a pure
   cosine at bin k of a 128-sample window returns exactly `pi * k / 64`
   for k = 5, 20, 40, 63, and a +1/-1 alternation returns `pi`.
2. **Direction.** On AR(1) returns the column's median falls
   monotonically with phi: 2.6016 / 2.1598 / 1.5708 / 1.0308 / 0.5400 at
   phi = -0.6 / -0.3 / 0 / 0.3 / 0.6 (1,400 bars each). White noise sits
   at pi / 2, as a flat spectrum must.
3. **Causality.** A future-splice sweep on six frames (0 leaks) and mutants
   read off this module's source, including two that mix data ACROSS rows
   of one evaluation chunk (`chunk-wide-mean`, `chunk-wide-total`).
4. **Reachability on real-shaped data**, including the issue's worry: the
   tick-rounded `penny` frame, 21.68% exactly-zero returns, still fires on
   every full-window bar with 19 distinct values (1.0308 .. 1.9144).
5. **Scale-free**: bit-identical under x8 / x64 / x2^+-40 price rescales
   (price enters only as `c[t] / c[t-1]`), and measured 0 bars moved and 0
   NaN-mask differences under x10 / x3.7 price rescales and x10 / x3.7
   RETURN rescales on all six frames -- except `student-t` at returns
   x10, where one clipped return r <= -0.1 makes `1 + 10 r <= 0`, so the
   rescaled TEST price itself goes non-positive and every later bar is
   (correctly) bad data. The test below therefore rescales `walk`.

Gate E is not here and not in the ledger: it is owed (`CLAUDE.md`). The
`docs/C22PeriodicityMeasured.md` §E4 owed rule (measure against
`C22PERIODICITY_100`) is answered on synthetic frames only in the receipt:
per-frame rho -0.154 / +0.045 / +0.004 / -0.337 / nan / +0.209.

Not pinned on purpose: exact distinct-value counts and exact mutant-leak
counts. Tests pin bounds and the docstring states the local figure.
"""
import importlib
import math
from pathlib import Path

import numpy as np
import pytest
from pandas import DataFrame, Series

from .context import pandas_ta
from pandas_ta.statistics.c22_median_freq import (
    CHUNK_VALUES, MIN_LENGTH, NOISE_FLOOR, QUANTILE, ZSCORE_DDOF,
    _median_freq_rows, c22_median_freq, nfft_for)

ROOT = Path(__file__).resolve().parent.parent
MODULE = importlib.import_module("pandas_ta.statistics.c22_median_freq")
SRC = Path(MODULE.__file__).read_text(encoding="utf-8")
LENGTH = 100

ORACLE_STRIDE = 97


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
        _BASE[name] = c22_median_freq(FRAMES[name])
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


# ------------------------------------------------------------- Gate A
def shipped_on(window, nfft=None):
    w = np.asarray(window, float)
    return float(_median_freq_rows(w.reshape(1, -1), nfft or nfft_for(w.size))[0])


def direct_dft_median_freq(window, quantile=QUANTILE, ddof=ZSCORE_DDOF):
    """The definition with no FFT: `math.fsum` mean/sd, an explicit DFT with
    the angle reduced modulo NFFT before `cos`/`sin`, `math.fsum` running
    sums. Returns `(w, margin)`, the margin being the smallest |running sum
    - quantile * total| / total over all bins."""
    w = [float(v) for v in window]
    n = len(w)
    if not all(math.isfinite(v) for v in w):
        return float("nan"), float("nan")
    mean = math.fsum(w) / n
    sd = math.sqrt(math.fsum((v - mean) ** 2 for v in w) / (n - ddof))
    if not (math.isfinite(sd) and sd > NOISE_FLOOR):
        return float("nan"), float("nan")
    z = [(v - mean) / sd for v in w]
    nfft = nfft_for(n)
    half = nfft // 2
    power = []
    for k in range(half + 1):
        re = math.fsum(z[t] * math.cos(2 * math.pi * ((k * t) % nfft) / nfft)
                       for t in range(n))
        im = math.fsum(z[t] * math.sin(2 * math.pi * ((k * t) % nfft) / nfft)
                       for t in range(n))
        power.append(re * re + im * im)
    total = math.fsum(power)
    if not (total > 0.0):
        return float("nan"), float("nan")
    margin, j = float("inf"), None
    for k in range(half + 1):
        cum = math.fsum(power[:k + 1])
        margin = min(margin, abs(cum - quantile * total) / total)
        if j is None and cum > quantile * total:
            j = k
    return math.pi * j / half, margin


def _check_against_oracle(series, win, bars):
    ran = 0
    for i in range(0, win.shape[0], ORACLE_STRIDE):
        mine = float(series.iloc[int(bars[i])])
        other, margin = direct_dft_median_freq(win[i])
        if math.isnan(mine) or math.isnan(other):
            assert math.isnan(mine) and math.isnan(other), int(bars[i])
        else:
            # Exact, not a tolerance: the output is a grid value, and every
            # sampled window is far from a grid boundary (margin >> eps).
            assert margin > 1e-9, (int(bars[i]), margin)
            assert mine == other, (int(bars[i]), mine, other)
        ran += 1
    return ran


@pytest.mark.parametrize("frame", list(FRAMES))
def test_matches_the_direct_dft_oracle(frame):
    """Gate A's main limb: no FFT in the oracle, exact agreement."""
    win, bars = windows(FRAMES[frame])
    assert _check_against_oracle(base(frame), win, bars) >= 14


@pytest.mark.parametrize("length", [64, 120])
@pytest.mark.parametrize("frame", ["walk", "penny", "ar1"])
def test_matches_the_oracle_at_a_non_default_length(frame, length):
    """64 is its own power of two (NFFT = 64, no padding); 120 pads to 128."""
    win, bars = windows(FRAMES[frame], length=length)
    s = c22_median_freq(FRAMES[frame], length=length)
    assert _check_against_oracle(s, win, bars) >= 10


@pytest.mark.parametrize("k", [5, 20, 40, 63])
def test_a_pure_cosine_at_a_bin_returns_exactly_that_bin(k):
    t = np.arange(128, dtype=float)
    assert shipped_on(np.cos(2 * np.pi * k * t / 128)) == math.pi * k / 64


def test_an_alternating_window_returns_pi():
    alt = np.where(np.arange(100) % 2 == 0, 1.0, -1.0)
    assert shipped_on(alt) == math.pi
    assert direct_dft_median_freq(alt)[0] == math.pi


def test_the_column_falls_monotonically_with_return_autocorrelation():
    """Measured medians 2.6016 / 2.1598 / 1.5708 / 1.0308 / 0.5400."""
    medians = [float(c22_median_freq(ar1(phi=phi, seed=3)).median())
               for phi in (-0.6, -0.3, 0.0, 0.3, 0.6)]
    assert all(a > b for a, b in zip(medians, medians[1:])), medians
    assert abs(medians[2] - math.pi / 2) < 0.1, medians


def test_every_output_is_on_the_frequency_grid():
    for frame in FRAMES:
        v = base(frame).dropna().to_numpy()
        k = v * 64 / math.pi
        assert np.all(np.abs(k - np.round(k)) < 1e-9), frame
        assert np.all((v > 0.0) & (v <= math.pi)), frame


def test_nfft_is_the_next_power_of_two():
    assert [nfft_for(n) for n in (8, 9, 64, 65, 100, 128, 129, 250)] == \
        [8, 16, 64, 128, 128, 128, 256, 256]


def test_the_module_docstring_attributes_the_source():
    doc = c22_median_freq.__doc__
    for needle in ("Lubba", "33:1821", "SP_Summaries", "wq_50", "GPL-3.0",
                   "#138"):
        assert needle in doc, needle
    assert "classification" in doc.lower()
    assert "existence" in doc and "not evidence" in doc


def test_the_reference_implementation_is_not_imported_by_shipped_code():
    """The references (pycatch22, hctsa) are GPL-3.0 and this fork is MIT."""
    hits = []
    files = sorted((ROOT / "pandas_ta").rglob("*.py"))
    for p in files:
        for line in p.read_text(encoding="utf-8").splitlines():
            s = line.strip()
            if (s.startswith("import ") or s.startswith("from ")) \
                    and ("catch22" in s.replace("c22", "") or "hctsa" in s):
                hits.append((str(p.relative_to(ROOT)), s))
    assert hits == [], hits
    assert len(files) > 300, len(files)


# ------------------------------------------------------------- Gate B
MUTANTS = {
    "write-back-dated": (
        "out[length + a:length + b] = _median_freq_rows(win[a:b], nfft)",
        "out[length - 1 + a:length - 1 + b] = _median_freq_rows(win[a:b], nfft)"),
    "window-one-ahead": ("win = sliding_window_view(r, length)",
                         "win = sliding_window_view(r, length + 1)[:, 1:]"),
    "window-ten-ahead": ("win = sliding_window_view(r, length)",
                         "win = sliding_window_view(r, length + 10)[:, 10:]"),
    "returns-rolled": ("r = np.where(np.isfinite(r), r, np.nan)",
                       "r = np.roll(np.where(np.isfinite(r), r, np.nan), -1)"),
    "mask-back-dated": ("r = np.where(np.isfinite(r), r, np.nan)",
                        "r = np.where(np.isfinite(np.roll(r, -1)), r, np.nan)"),
    "chunk-wide-mean": (
        "z = (block - block.mean(axis=1, keepdims=True)) / sd[:, None]",
        "z = (block - block.mean()) / sd[:, None]"),
    "chunk-wide-total": ("total = cum[:, -1]",
                         "total = np.full(cum.shape[0], cum[:, -1].mean())"),
    "no-floor": ("bad |= ~(sd > NOISE_FLOOR) | ~np.isfinite(sd)",
                 "bad |= ~(sd > 0.0)"),
}


def mutant(name):
    old, new = MUTANTS[name]
    assert SRC.count(old) == 1, (name, SRC.count(old))
    ns = {}
    exec(compile(SRC.replace(old, new), f"<mutant {name}>", "exec"), ns)
    return ns["c22_median_freq"]


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
    assert _leaks(c22_median_freq, f, _offsets(len(f)), splices=8) == []


@pytest.mark.parametrize("length", [MIN_LENGTH, 120, 250])
def test_the_sweep_at_non_default_lengths(length):
    f = FRAMES["walk"]
    assert _leaks(lambda s: c22_median_freq(s, length=length), f,
                  _offsets(len(f), length), splices=4) == []


@pytest.mark.parametrize("name", ["write-back-dated", "window-one-ahead",
                                  "window-ten-ahead", "returns-rolled",
                                  "chunk-wide-mean", "chunk-wide-total"])
def test_each_look_ahead_mutant_is_caught(name):
    """The default `CHUNK_VALUES` budget holds this test's whole 1500-bar
    frame in ONE chunk, so a per-chunk (not per-row) mean or total power
    mixes every row's future into every other row's output. The output is
    a 65-level grid value, so a one-bar back-dating moves the visible
    prefix only where bar j-1's grid value changes -- hence up to 8
    independent splices per offset."""
    f = FRAMES["walk"]
    hits = _leaks(mutant(name), f, _offsets(len(f)), splices=8)
    assert len(hits) >= 10, (name, len(hits))


def test_a_one_bar_mutant_can_only_move_bars_from_the_cut_backwards():
    fn = mutant("write-back-dated")
    f = FRAMES["walk"]
    bad = np.asarray(fn(f), float)
    seen = 0
    for j in _offsets(len(f), count=35):
        for s in range(8):
            other = np.asarray(fn(_spliced(f, j, seed=909 + 7919 * s)), float)
            moved = np.where(~((bad[:j] == other[:j])
                               | (np.isnan(bad[:j]) & np.isnan(other[:j]))))[0]
            if len(moved):
                seen += 1
                assert int(moved.min()) == j - 1, (j, moved[:4])
                break
    assert seen >= 5, seen


def test_the_mask_mutant_is_dead_on_a_clean_frame_and_caught_on_a_dirty_one():
    fn = mutant("mask-back-dated")
    clean = FRAMES["walk"]
    assert same(c22_median_freq(clean), fn(clean))
    caught = 0
    for j in _offsets(len(clean), count=12):
        dirty = clean.copy()
        dirty.iloc[j] = np.nan
        a = np.asarray(c22_median_freq(dirty), float)
        b = np.asarray(fn(dirty), float)
        moved = np.where(~((a == b) | (np.isnan(a) & np.isnan(b))))[0]
        if len(moved):
            caught += 1
            assert int(moved.min()) == j - 1, (j, moved[:4])
    assert caught == 12, caught


# ------------------------------------------------------------- Gate C
@pytest.mark.parametrize("frame", list(FRAMES))
def test_every_bar_with_a_full_window_fires(frame):
    s = base(frame)
    assert int(s.notna().sum()) == len(s) - LENGTH
    assert int(s.notna().values.argmax()) == LENGTH
    assert s.iloc[:LENGTH].isna().all()


@pytest.mark.parametrize("frame", STOCHASTIC)
def test_the_column_is_not_constant_on_a_stochastic_frame(frame):
    """Measured distinct values: 19 / 24 / 19 / 15 / 18 (walk, tick-rounded,
    penny, ar1, student-t)."""
    a = base(frame).dropna().to_numpy()
    assert len(set(a.tolist())) >= 10, frame
    assert float(a.max() - a.min()) > 0.5, frame


def test_a_tick_rounded_penny_frame_still_fires_everywhere():
    """The issue's own worry: a 2-lira stock on a 1-kurus tick (21.68% zero
    returns) still fires on every full-window bar."""
    f = FRAMES["penny"]
    r = np.asarray(f, float)
    r = r[1:] / r[:-1] - 1.0
    assert float(np.mean(r == 0.0)) > 0.15
    s = base("penny")
    assert int(s.notna().sum()) == len(f) - LENGTH
    assert s.nunique() >= 10


def test_a_period_20_cosine_reads_near_its_own_frequency():
    """Constant 0.2945 = pi * 6 / 64, the grid bin nearest 2 pi / 20."""
    v = base("cosine").dropna()
    assert v.nunique() == 1
    assert float(v.iloc[0]) == math.pi * 6 / 64


def test_a_flat_run_blanks_from_the_first_all_zero_window():
    c = FRAMES["walk"].to_numpy().copy()
    c[400:] = c[399]
    s = c22_median_freq(Series(c[:700]))
    assert int(s.notna().sum()) == 399
    assert not math.isnan(float(s.iloc[498]))
    assert s.iloc[499:].isna().all()


@pytest.mark.parametrize("step", [0.01, 0.001, -0.005])
def test_an_exact_geometric_ladder_never_fires_and_the_floor_is_why(step):
    f = ladder(step=step)
    assert int(c22_median_freq(f).notna().sum()) == 0
    win, _ = windows(f)
    assert float(win.std(axis=1, ddof=ZSCORE_DDOF).max()) < NOISE_FLOOR
    unguarded = np.asarray(mutant("no-floor")(f), float)
    assert int((~np.isnan(unguarded)).sum()) > 0


# ------------------------------------------------------------- Gate D
@pytest.mark.parametrize("factor", [8.0, 64.0, 2.0 ** -40, 2.0 ** 40])
@pytest.mark.parametrize("frame", list(FRAMES))
def test_bit_identical_under_a_power_of_two_price_rescale(frame, factor):
    """The price enters only as `c[t] / c[t-1]`, so a power-of-two rescale
    multiplies and divides out exactly in floating point."""
    f = FRAMES[frame]
    assert same(c22_median_freq(f), c22_median_freq(f * factor)), (frame, factor)


@pytest.mark.parametrize("factor", [10.0, 3.7])
@pytest.mark.parametrize("frame", list(FRAMES))
def test_an_inexact_price_rescale_moves_nothing_and_keeps_the_nan_mask(frame, factor):
    """Measured 0 bars moved on all six frames; the bound is a tolerance
    because an inexact rescale is not exact in float division."""
    moved, mask = diff_bars(base(frame), c22_median_freq(FRAMES[frame] * factor),
                            tol=1e-12)
    assert mask == 0
    assert moved == 0, (frame, factor, moved)


@pytest.mark.parametrize("factor", [10.0, 3.7, 0.1])
def test_the_column_is_blind_to_an_inexact_return_rescale(factor):
    """In exact arithmetic a positive return rescale multiplies every bin's
    power alike. Measured 0 bars moved at x10 / x3.7 on all six frames
    (student-t at x10 aside: its rescaled test price goes non-positive)."""
    f = FRAMES["walk"]
    r = f.to_numpy()[1:] / f.to_numpy()[:-1] - 1.0
    scaled = np.empty(len(f))
    scaled[0] = 100.0
    scaled[1:] = scaled[0] * np.cumprod(1.0 + factor * r)
    moved, mask = diff_bars(base("walk"), c22_median_freq(Series(scaled)), tol=1e-12)
    assert mask == 0
    assert moved == 0, (factor, moved)


def test_zero_lt_fires_lt_n_at_the_default_length():
    for frame in STOCHASTIC:
        s = base(frame)
        assert 0 < int(s.notna().sum()) < len(s)


@pytest.mark.parametrize("n,fires", [(99, None), (100, None), (101, 1),
                                     (102, 2)])
def test_a_short_input_returns_none_until_one_window_exists(n, fires):
    s = c22_median_freq(FRAMES["walk"].iloc[:n])
    if fires is None:
        assert s is None
    else:
        assert int(s.notna().sum()) == fires


@pytest.mark.parametrize("length,name,fires", [
    (None, "C22MEDFREQ_100", 1400),
    (0, "C22MEDFREQ_100", 1400),
    (1, "C22MEDFREQ_100", 1400),
    (MIN_LENGTH - 1, "C22MEDFREQ_100", 1400),
    (MIN_LENGTH, f"C22MEDFREQ_{MIN_LENGTH}", 1500 - MIN_LENGTH),
    (250, "C22MEDFREQ_250", 1250),
    (250.7, "C22MEDFREQ_250", 1250),
])
def test_the_length_guard_band(length, name, fires):
    """Below `MIN_LENGTH` = 8 -- a module choice, not from the source -- a
    length falls back to 100, AND the column is named after the length
    actually used (`CLAUDE.md`: naming is API)."""
    s = c22_median_freq(FRAMES["walk"], length=length)
    assert s.name == name
    assert int(s.notna().sum()) == fires


def test_the_offset_and_the_fill_are_the_house_ones():
    s = c22_median_freq(FRAMES["walk"], offset=2)
    assert same(s.to_numpy()[2:], base("walk").to_numpy()[:-2])
    s = c22_median_freq(FRAMES["walk"], fillna=-99)
    assert int(s.isna().sum()) == 0
    assert int((s == -99).sum()) == LENGTH


@pytest.mark.parametrize("budget", [100, 400, 1024])
def test_the_chunk_budget_cannot_change_a_value(budget):
    """Every quantity is per-row, so the chunk boundary is invisible."""
    want = base("walk")
    MODULE.CHUNK_VALUES = budget
    try:
        got = c22_median_freq(FRAMES["walk"])
    finally:
        MODULE.CHUNK_VALUES = CHUNK_VALUES
    assert same(want, got)


# ------------------------------------------------------------- wiring
def test_the_five_wiring_touch_points():
    assert Path(MODULE.__file__).exists()
    assert hasattr(pandas_ta.statistics, "c22_median_freq")
    assert "c22_median_freq" in pandas_ta.Category["statistics"]
    assert hasattr(pandas_ta.core.AnalysisIndicators, "c22_median_freq")
    assert (ROOT / "tests" / "test_c22_median_freq.py").exists()


def test_the_accessor_forwards_its_parameters():
    df = DataFrame({"close": FRAMES["walk"].to_numpy()})
    acc = df.ta.c22_median_freq()
    assert acc.name == "C22MEDFREQ_100"
    assert same(acc, base("walk"))
    acc = df.ta.c22_median_freq(length=250, offset=1)
    assert acc.name == "C22MEDFREQ_250"
    assert same(acc, c22_median_freq(FRAMES["walk"], length=250, offset=1))


def test_the_dictionary_row_describes_this_column():
    """The generator takes the docstring's first line as the title, so a
    wrapped title would leak its parenthetical short name into the body."""
    text = (ROOT / "docs" / "IndicatorDictionary.md").read_text(
        encoding="utf-8")
    assert "C22MEDFREQ_100" in text
    lines = [ln for ln in text.splitlines() if "c22_median_freq" in ln]
    assert lines, "no row for c22_median_freq in the dictionary"
    assert "power spectrum" in lines[0].lower()
    assert "(C22MEDFREQ)" not in lines[0]
