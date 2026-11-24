# -*- coding: utf-8 -*-
"""C22-OUTLIER-TIMING-POS: `c22_outlier_timing_pos`, catch22's
`DN_OutlierInclude_p_001_mdrmd` -- the timing of positive outliers in the
z-scored last 100 daily returns (issue #143).

⚠ **Round 4 (owner, attended).** The kernel now follows catch22's
`DN_OutlierInclude_p_001_mdrmd` step for step; measured 2026-11-24 against
pycatch22 0.4.5 run as a black box outside this package: 26,118 of 26,118
windows agree to 1e-12. Earlier rounds did not -- see the module
docstring.

Every number here was measured by running this module and
`docs/measure_c22_outlier_timing_pos.py` on this machine; the receipt is
`docs/C22OutlierTimingPosMeasured.md`. What is pinned, in order of how much
it would hurt to lose:

1. **The definition, against an independent SECOND SPELLING.**
   `direct_threshold_sweep` re-spells the feature with plain Python
   (`statistics.median`, `math.fsum`, no numpy) and no shared code with the
   vectorised kernel. The GPL-3.0 reference itself is not a dependency, so
   its agreement (above) is a recorded measurement, not a test here.
2. **Causality.** A future-splice sweep on six frames (0 leaks) and
   mutants read off this module's source. The REAL module leaks on 0 of
   10 probed offsets on every frame.
3. **Reachability on real-shaped data**, including the issue's worry: the
   tick-rounded `penny` frame still fires on every full-window bar with a
   wide, non-degenerate range.
4. **Scale-free**: bit-identical under x8 / x64 price rescales (price enters
   only as `c[t] / c[t-1]`), and measured 0 bars moved under x10 / x3.7
   price rescales and return rescales on all six frames.

Gate E: see the receipt's Gate E section; this module does not restate it.

Not pinned on purpose: exact distinct-value counts and exact mutant-leak
counts. Tests pin bounds and the docstring states the local figure.
"""
import importlib
import math
import statistics
from pathlib import Path

import numpy as np
import pytest
from pandas import DataFrame, Series

from .context import pandas_ta
from pandas_ta.statistics.c22_outlier_timing_pos import (
    CHUNK_VALUES, INC, MIN_LENGTH, NOISE_FLOOR, TRIM_PCT, ZSCORE_DDOF,
    _outlier_timing_pos_rows, c22_outlier_timing_pos)

ROOT = Path(__file__).resolve().parent.parent
MODULE = importlib.import_module("pandas_ta.statistics.c22_outlier_timing_pos")
SRC = Path(MODULE.__file__).read_text(encoding="utf-8")
LENGTH = 100


# ------------------------------------------------------------- frames
def walk(n=550, seed=11, sigma=0.015, level=100.0):
    rng = np.random.default_rng(seed)
    return Series(level * np.exp(np.cumsum(rng.normal(0.0, sigma, n))))


def tick_rounded(n=550, seed=55):
    return Series(np.round(walk(n, seed).to_numpy(), 2))


def penny(n=550, seed=23, level=2.0, sigma=0.012):
    """A 2-lira stock on a 1-kurus tick: many returns are exactly 0."""
    return Series(np.round(walk(n, seed, sigma, level).to_numpy(), 2))


def ar1(n=550, seed=7, sigma=0.01, phi=0.6):
    rng = np.random.default_rng(seed)
    e = rng.normal(0.0, sigma, n)
    r = np.empty(n)
    r[0] = e[0]
    for t in range(1, n):
        r[t] = phi * r[t - 1] + e[t]
    return Series(100.0 * np.cumprod(1.0 + r))


def jump_cluster(n=550, seed=31, sigma=0.008):
    """Positive jumps clustered early in each 100-bar window: a frame built
    so the column's TIMING semantics have something real to read."""
    rng = np.random.default_rng(seed)
    r = rng.normal(0.0, sigma, n)
    r[::17] += 0.03
    return Series(100.0 * np.cumprod(1.0 + r))


def student_t(n=550, seed=19, df=3, sigma=0.01):
    rng = np.random.default_rng(seed)
    r = sigma * rng.standard_t(df, n)
    return Series(100.0 * np.cumprod(1.0 + np.clip(r, -0.5, 0.5)))


def ladder(n=550, step=0.01, start=100.0):
    return Series(start * (1.0 + step) ** np.arange(n, dtype=float))


FRAMES = {
    "walk": walk(),
    "tick-rounded": tick_rounded(),
    "penny": penny(),
    "ar1": ar1(),
    "jump-cluster": jump_cluster(),
    "student-t": student_t(),
}
STOCHASTIC = list(FRAMES)
_BASE = {}


def base(name):
    if name not in _BASE:
        _BASE[name] = c22_outlier_timing_pos(FRAMES[name])
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
def shipped_on(window):
    w = np.asarray(window, float)
    return float(_outlier_timing_pos_rows(w.reshape(1, -1))[0])


def direct_threshold_sweep(window, inc=INC, ddof=ZSCORE_DDOF):
    """The definition re-spelled with no numpy: `math.fsum` mean/sd, a plain
    Python threshold sweep, `statistics.median` for both the per-step
    median position and the outer median. Positions are 1-indexed (the
    MATLAB/hctsa `find()` convention)."""
    w = [float(v) for v in window]
    n = len(w)
    if not all(math.isfinite(v) for v in w):
        return float("nan")
    mean = math.fsum(w) / n
    var = math.fsum((v - mean) ** 2 for v in w) / (n - ddof)
    sd = math.sqrt(var) if var > 0.0 else 0.0
    if not (math.isfinite(sd) and sd > NOISE_FLOOR):
        return float("nan")
    y = [((v - mean) / sd) for v in w]
    max_y = max(y)
    if not (max_y > 0.0):
        return float("nan")
    tot = sum(1 for v in y if v >= 0.0)
    nth = int(max_y / inc) + 1
    half = n / 2.0
    gap_nan, share, ranks = [], [], []
    for k in range(nth):
        thr = k * inc
        idx = [i + 1 for i in range(n) if y[i] >= thr]
        gap_nan.append(len(idx) < 2)
        share.append((len(idx) - 1) * 100.0 / tot)
        ranks.append(statistics.median(idx) / half - 1.0 if idx else float("nan"))
    # The reference's cut: the last step still including more than
    # TRIM_PCT percent, or the first step with fewer than two points.
    mj = max([k for k in range(nth) if share[k] > TRIM_PCT], default=0)
    fbi = min([k for k in range(nth) if gap_nan[k]], default=nth - 1)
    return statistics.median(ranks[:min(mj, fbi) + 1])


def _check_against_oracle(series, win, bars, stride=61):
    ran = 0
    for i in range(0, win.shape[0], stride):
        mine = float(series.iloc[int(bars[i])])
        other = direct_threshold_sweep(win[i])
        if math.isnan(mine) or math.isnan(other):
            assert math.isnan(mine) and math.isnan(other), int(bars[i])
        else:
            assert mine == pytest.approx(other, rel=1e-9, abs=1e-9), \
                (int(bars[i]), mine, other)
        ran += 1
    return ran


@pytest.mark.parametrize("frame", list(FRAMES))
def test_matches_the_direct_sweep_oracle(frame):
    """Gate A's main limb: an independent plain-Python spelling agrees. 450
    fired windows at the default length and stride 23 gives 20 samples;
    measured 20 of 20 agree on every one of the six frames."""
    win, bars = windows(FRAMES[frame])
    assert _check_against_oracle(base(frame), win, bars, stride=23) >= 15


@pytest.mark.parametrize("length", [20, 150])
@pytest.mark.parametrize("frame", ["walk", "penny", "ar1"])
def test_matches_the_oracle_at_a_non_default_length(frame, length):
    win, bars = windows(FRAMES[frame], length=length)
    s = c22_outlier_timing_pos(FRAMES[frame], length=length)
    assert _check_against_oracle(s, win, bars, stride=25) >= 12


def test_the_module_docstring_attributes_the_source():
    doc = c22_outlier_timing_pos.__doc__
    for needle in ("Lubba", "33:1821", "DN_OutlierInclude", "mdrmd",
                   "GPL-3.0", "#143"):
        assert needle in doc, needle
    assert "classification" in doc.lower()
    assert "existence" in doc and "not evidence" in doc
    assert "Checked against the reference's OUTPUT" in doc


def test_the_reference_implementation_is_not_imported_by_shipped_code():
    """The reference (pycatch22) is GPL-3.0 and this fork is MIT."""
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


def test_the_zscore_divisor_is_not_inert_but_moves_little():
    """`ddof` rescales every `y[i]` by the same positive factor, which
    preserves RANKING but not which positions clear a fixed ABSOLUTE
    threshold -- so this is NOT an invariance, unlike several sibling
    catch22 ports' z-score divisor. Measured small: at most a minority of
    sampled windows move."""
    f = FRAMES["ar1"]
    win, bars = windows(f)
    moved = checked = 0
    for i in range(0, win.shape[0], 53):
        a = direct_threshold_sweep(win[i], ddof=1)
        b = direct_threshold_sweep(win[i], ddof=0)
        if math.isnan(a) or math.isnan(b):
            assert math.isnan(a) and math.isnan(b)
            continue
        checked += 1
        if a != b:
            moved += 1
    assert checked >= 5, checked
    assert moved <= max(1, checked // 2), (moved, checked)


# ------------------------------------------------------------- Gate B
MUTANTS = {
    "write-back-dated": (
        "out[length + a:length + b] = _outlier_timing_pos_rows(win[a:b])",
        "out[length - 1 + a:length - 1 + b] = _outlier_timing_pos_rows(win[a:b])"),
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
    "no-floor": ("bad |= ~(sd > NOISE_FLOOR) | ~np.isfinite(sd)",
                 "bad |= ~(sd > 0.0)"),
}


def mutant(name):
    old, new = MUTANTS[name]
    assert SRC.count(old) == 1, (name, SRC.count(old))
    ns = {}
    exec(compile(SRC.replace(old, new), f"<mutant {name}>", "exec"), ns)
    return ns["c22_outlier_timing_pos"]


def _spliced(close, j, seed=909):
    rng = np.random.default_rng(seed + j)
    c = close.to_numpy(dtype=float).copy()
    c[j:] = c[j - 1] * np.cumprod(1.0 + rng.normal(0.0005, 0.02, c.size - j))
    return Series(c, index=close.index)


def _offsets(n, length=LENGTH, count=10):
    return [int(x) for x in np.linspace(length + 5, n - 5, count).astype(int)]


def _leaks(fn, close, offsets, splices=2):
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
    assert _leaks(c22_outlier_timing_pos, f, _offsets(len(f))) == []


@pytest.mark.parametrize("length", [MIN_LENGTH, 150, 250])
def test_the_sweep_at_non_default_lengths(length):
    f = FRAMES["walk"]
    assert _leaks(lambda s: c22_outlier_timing_pos(s, length=length), f,
                  _offsets(len(f), length)) == []


#: How many of the 10 offsets each mutant must leak on. A ONE-BAR
#: perturbation (`write-back-dated`, `window-one-ahead`, `returns-rolled`)
#: moves the column only when the shifted return changes which positions
#: clear a threshold step, so it is caught on about half the offsets.
#: Measured on this frame: write-back-dated 5/10, window-one-ahead 5/10,
#: returns-rolled 5/10, window-ten-ahead 10/10, chunk-wide-mean 10/10.
#: Floors are set a couple of hits below each measured count, to leave room for the last-bit float
#: differences CI's AVX-512-less CPUs can introduce without masking a
#: genuine regression.
MUTANT_MIN_HITS = {
    "write-back-dated": 3, "window-one-ahead": 3, "returns-rolled": 3,
    "window-ten-ahead": 8, "chunk-wide-mean": 8,
}


@pytest.mark.parametrize("name", list(MUTANT_MIN_HITS))
def test_each_look_ahead_mutant_is_caught(name):
    f = FRAMES["walk"]
    hits = _leaks(mutant(name), f, _offsets(len(f)))
    assert len(hits) >= MUTANT_MIN_HITS[name], (name, len(hits))


def test_a_one_bar_mutant_can_only_move_bars_from_the_cut_backwards():
    """Measured 2 of 8 offsets show any movement at all (floor set one
    below, for CPU-variant float noise); every one that DOES move still
    moves from exactly bar `j - 1`, never earlier."""
    fn = mutant("write-back-dated")
    f = FRAMES["walk"]
    bad = np.asarray(fn(f), float)
    seen = 0
    for j in _offsets(len(f), count=8):
        other = np.asarray(fn(_spliced(f, j, seed=909 + 7919)), float)
        moved = np.where(~((bad[:j] == other[:j])
                           | (np.isnan(bad[:j]) & np.isnan(other[:j]))))[0]
        if len(moved):
            seen += 1
            assert int(moved.min()) == j - 1, (j, moved[:4])
    assert seen >= 1, seen


def test_the_mask_mutant_is_dead_on_a_clean_frame_and_caught_on_a_dirty_one():
    fn = mutant("mask-back-dated")
    clean = FRAMES["walk"]
    assert same(c22_outlier_timing_pos(clean), fn(clean))
    caught = 0
    for j in _offsets(len(clean), count=8):
        dirty = clean.copy()
        dirty.iloc[j] = np.nan
        a = np.asarray(c22_outlier_timing_pos(dirty), float)
        b = np.asarray(fn(dirty), float)
        moved = np.where(~((a == b) | (np.isnan(a) & np.isnan(b))))[0]
        if len(moved):
            caught += 1
            assert int(moved.min()) == j - 1, (j, moved[:4])
    assert caught == 8, caught


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
    assert len(set(a.tolist())) >= 10, frame
    assert float(a.max() - a.min()) > 0.0, frame


def test_a_tick_rounded_penny_frame_still_fires_everywhere():
    """The issue's own worry: a 2-lira stock on a 1-kurus tick (many zero
    returns) still fires on every full-window bar."""
    f = FRAMES["penny"]
    r = np.asarray(f, float)
    r = r[1:] / r[:-1] - 1.0
    assert float(np.mean(r == 0.0)) > 0.15
    s = base("penny")
    assert int(s.notna().sum()) == len(f) - LENGTH
    assert s.nunique() >= 10


def test_a_flat_run_blanks_from_the_first_all_zero_window():
    c = FRAMES["walk"].to_numpy().copy()
    c[400:] = c[399]
    s = c22_outlier_timing_pos(Series(c[:700]))
    assert int(s.notna().sum()) == 399
    assert not math.isnan(float(s.iloc[498]))
    assert s.iloc[499:].isna().all()


@pytest.mark.parametrize("step", [0.01, 0.001, -0.005])
def test_an_exact_geometric_ladder_never_fires_and_the_floor_is_why(step):
    f = ladder(step=step)
    assert int(c22_outlier_timing_pos(f).notna().sum()) == 0
    win, _ = windows(f)
    assert float(win.std(axis=1, ddof=ZSCORE_DDOF).max()) < NOISE_FLOOR
    unguarded = np.asarray(mutant("no-floor")(f), float)
    assert int((~np.isnan(unguarded)).sum()) > 0


def test_every_output_is_a_normalised_median_position():
    """`median(idx)/(length/2) - 1` with `idx` 1-indexed and `idx <= length`
    bounds the output in `[2/length - 1, 1]`, never below -1 and never above
    +1."""
    for frame in FRAMES:
        v = base(frame).dropna().to_numpy()
        assert np.all(v >= -1.0), frame
        assert np.all(v <= 1.0 + 1e-12), frame


# ------------------------------------------------------------- Gate D
@pytest.mark.parametrize("factor", [8.0, 64.0, 2.0 ** -40, 2.0 ** 40])
@pytest.mark.parametrize("frame", list(FRAMES))
def test_bit_identical_under_a_power_of_two_price_rescale(frame, factor):
    """The price enters only as `c[t] / c[t-1]`, so a power-of-two rescale
    multiplies and divides out exactly in floating point."""
    f = FRAMES[frame]
    assert same(c22_outlier_timing_pos(f),
               c22_outlier_timing_pos(f * factor)), (frame, factor)


@pytest.mark.parametrize("factor", [10.0, 3.7])
@pytest.mark.parametrize("frame", list(FRAMES))
def test_an_inexact_price_rescale_moves_nothing_and_keeps_the_nan_mask(frame, factor):
    moved, mask = diff_bars(base(frame),
                            c22_outlier_timing_pos(FRAMES[frame] * factor))
    assert mask == 0
    assert moved == 0, (frame, factor, moved)


@pytest.mark.parametrize("factor", [10.0, 3.7, 0.1])
def test_the_column_is_blind_to_an_inexact_positive_return_rescale(factor):
    """A positive rescale of the returns is an affine map on `r` with
    `a = factor > 0`, `b = 0`, which the z-score cancels entirely."""
    f = FRAMES["walk"]
    r = f.to_numpy()[1:] / f.to_numpy()[:-1] - 1.0
    scaled = np.empty(len(f))
    scaled[0] = 100.0
    scaled[1:] = scaled[0] * np.cumprod(1.0 + factor * r)
    moved, mask = diff_bars(base("walk"), c22_outlier_timing_pos(Series(scaled)))
    assert mask == 0
    assert moved == 0, (factor, moved)


def test_a_negative_return_rescale_flips_which_tail_is_read():
    """`a < 0` is NOT in the invariance class: it swaps which outliers are
    "positive", so the column need not (and measurably does not) agree with
    the unscaled one."""
    f = FRAMES["ar1"]
    r = f.to_numpy()[1:] / f.to_numpy()[:-1] - 1.0
    scaled = np.empty(len(f))
    scaled[0] = 100.0
    scaled[1:] = scaled[0] * np.cumprod(1.0 - r)
    moved, _ = diff_bars(base("ar1"), c22_outlier_timing_pos(Series(scaled)))
    assert moved > 0


def test_zero_lt_fires_lt_n_at_the_default_length():
    for frame in STOCHASTIC:
        s = base(frame)
        assert 0 < int(s.notna().sum()) < len(s)


@pytest.mark.parametrize("n,fires", [(99, None), (100, None), (101, 1),
                                     (102, 2)])
def test_a_short_input_returns_none_until_one_window_exists(n, fires):
    s = c22_outlier_timing_pos(FRAMES["walk"].iloc[:n])
    if fires is None:
        assert s is None
    else:
        assert int(s.notna().sum()) == fires


@pytest.mark.parametrize("length,name,fires", [
    (None, "C22OUTLIERTIMINGPOS_100", 450),
    (0, "C22OUTLIERTIMINGPOS_100", 450),
    (1, "C22OUTLIERTIMINGPOS_100", 450),
    (MIN_LENGTH - 1, "C22OUTLIERTIMINGPOS_100", 450),
    (MIN_LENGTH, f"C22OUTLIERTIMINGPOS_{MIN_LENGTH}", 550 - MIN_LENGTH),
    (250, "C22OUTLIERTIMINGPOS_250", 300),
    (250.7, "C22OUTLIERTIMINGPOS_250", 300),
])
def test_the_length_guard_band(length, name, fires):
    """Below `MIN_LENGTH` = 10 -- a module choice, not from the source -- a
    length falls back to 100, AND the column is named after the length
    actually used (`CLAUDE.md`: naming is API)."""
    s = c22_outlier_timing_pos(FRAMES["walk"], length=length)
    assert s.name == name
    assert int(s.notna().sum()) == fires


def test_the_offset_and_the_fill_are_the_house_ones():
    s = c22_outlier_timing_pos(FRAMES["walk"], offset=2)
    assert same(s.to_numpy()[2:], base("walk").to_numpy()[:-2])
    s = c22_outlier_timing_pos(FRAMES["walk"], fillna=-99)
    assert int(s.isna().sum()) == 0
    assert int((s == -99).sum()) == LENGTH


@pytest.mark.parametrize("budget", [1000, 5000, 1 << 20])
def test_the_chunk_budget_cannot_change_a_value(budget):
    """Every quantity is per-row, so the chunk boundary is invisible."""
    want = base("walk")
    MODULE.CHUNK_VALUES = budget
    try:
        got = c22_outlier_timing_pos(FRAMES["walk"])
    finally:
        MODULE.CHUNK_VALUES = CHUNK_VALUES
    assert same(want, got)


# ------------------------------------------------------------- wiring
def test_the_five_wiring_touch_points():
    assert Path(MODULE.__file__).exists()
    assert hasattr(pandas_ta.statistics, "c22_outlier_timing_pos")
    assert "c22_outlier_timing_pos" in pandas_ta.Category["statistics"]
    assert hasattr(pandas_ta.core.AnalysisIndicators, "c22_outlier_timing_pos")
    assert (ROOT / "tests" / "test_c22_outlier_timing_pos.py").exists()


def test_the_accessor_forwards_its_parameters():
    df = DataFrame({"close": FRAMES["walk"].to_numpy()})
    acc = df.ta.c22_outlier_timing_pos()
    assert acc.name == "C22OUTLIERTIMINGPOS_100"
    assert same(acc, base("walk"))
    acc = df.ta.c22_outlier_timing_pos(length=250, offset=1)
    assert acc.name == "C22OUTLIERTIMINGPOS_250"
    assert same(acc, c22_outlier_timing_pos(FRAMES["walk"], length=250, offset=1))


def test_the_dictionary_row_describes_this_column():
    """The generator takes the docstring's first line as the title, so a
    wrapped title would leak its parenthetical short name into the body."""
    text = (ROOT / "docs" / "IndicatorDictionary.md").read_text(
        encoding="utf-8")
    assert "C22OUTLIERTIMINGPOS_100" in text
    lines = [ln for ln in text.splitlines() if "c22_outlier_timing_pos" in ln]
    assert lines, "no row for c22_outlier_timing_pos in the dictionary"
    assert "outlier" in lines[0].lower()
    assert "(C22OUTLIERTIMINGPOS)" not in lines[0]
