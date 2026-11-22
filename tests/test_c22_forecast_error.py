# -*- coding: utf-8 -*-
"""C22-FORECAST-ERROR: `c22_forecast_error`, catch22's standard deviation of
the residuals of a trailing 3-point mean forecast on the z-scored last 100
daily returns (issue #137).

Every number here was measured by running this module and
`docs/measure_c22_forecast_error.py` on this machine; the receipt is
`docs/C22ForecastErrorMeasured.md`. What is pinned, in order of how much it
would hurt to lose:

1. **The ddof convention.** Both knobs (`ZSCORE_DDOF` on the input z-score,
   `RESID_DDOF` on the residual standard deviation) were settled by fitting
   the GPL-3.0 reference (`pycatch22`) as a BLACK BOX, not read from its
   source -- `ddof=1` on BOTH is the only one of six candidates tried that
   reproduces `pycatch22.catch22_all(...)["FC_LocalSimple_mean3_stde"]`.
   On the SHIPPED candidate's own full sweep, 8,400 of 8,400 windows (every
   window of six frames) agree (worst gap 1.1e-15); on the six-candidate fit
   itself (a smaller, separate sample, every 23rd window of six frames, 366
   windows total), every other candidate disagrees on all 366 of them.
2. **Causality.** A future-perturbation sweep and read-off-disk mutants,
   including two that mix data ACROSS rows of the same evaluation chunk --
   a leak this module's chunking could introduce if a per-row mean or sd
   were ever read from the whole chunk instead of its own row.
3. **Reachability on real-shaped data**, including the issue's own worry: a
   tick-rounded penny frame that collapses many returns into one return
   value.
4. **Scale-free**: bit-identical under a price rescale, by the same
   `close[t] / close[t-1]` construction every catch22 return-port in this
   fork uses, and the output is independent of the return window's own
   scale because z-scoring is self-cancelling in exact real arithmetic.
5. **The overflow guard is load-bearing here**, unlike `c22_mode_10`'s
   equivalent guard: this module has no separate width/range check that
   would catch an `sd = inf` window on its own, so removing
   `~np.isfinite(sd)` genuinely revives a designed adversarial window with
   a concrete (non-NaN) value instead of leaving it blanked by something
   else.

**Against the actual GPL-3.0 reference** (`pycatch22`, measured not
assumed): 0 of 8,400 windows (every window across six synthetic frames) disagree
by more than 1e-9 (worst gap 1.1e-15, machine noise) -- the cleanest
black-box fit of this fork's catch22 ports to date.

Not pinned on purpose: exact counts of distinct values and any value to
1e-15. Tests pin bounds, tolerances and bands and the docstring states the
local figure.
"""
import importlib
import math
from pathlib import Path

import numpy as np
import pytest
from pandas import DataFrame, Series

from .context import pandas_ta
from pandas_ta.statistics.c22_forecast_error import (
    CHUNK_VALUES, MIN_LENGTH, NOISE_FLOOR, RESID_DDOF, TRAIN, ZSCORE_DDOF,
    _forecast_error_rows, c22_forecast_error)

ROOT = Path(__file__).resolve().parent.parent
MODULE = importlib.import_module("pandas_ta.statistics.c22_forecast_error")
SRC = Path(MODULE.__file__).read_text(encoding="utf-8")
LENGTH = 100

EXACT_STRIDE = 23
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
        _BASE[name] = c22_forecast_error(FRAMES[name])
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
    return float(_forecast_error_rows(w.reshape(1, -1))[0])


def value_from_exact(window, zddof=ZSCORE_DDOF, resddof=RESID_DDOF):
    """The definition re-spelled in plain Python with `math.fsum` and no
    numpy vectorisation -- an independently re-derived oracle."""
    w = [float(v) for v in window]
    n = len(w)
    if not all(math.isfinite(v) for v in w):
        return float("nan")
    mean = math.fsum(w) / n
    var = math.fsum((v - mean) ** 2 for v in w) / (n - zddof)
    if not (var >= 0.0):
        return float("nan")
    sd = math.sqrt(var)
    if not (math.isfinite(sd) and sd > NOISE_FLOOR):
        return float("nan")
    z = [(v - mean) / sd for v in w]
    resid = []
    for i in range(TRAIN, n):
        f = math.fsum(z[i - TRAIN:i]) / TRAIN
        resid.append(z[i] - f)
    rn = len(resid)
    rmean = math.fsum(resid) / rn
    rvar = math.fsum((v - rmean) ** 2 for v in resid) / (rn - resddof)
    return math.sqrt(rvar)


@pytest.mark.parametrize("frame", list(FRAMES))
def test_matches_the_exact_fsum_oracle(frame):
    """Gate A's main limb: the definition re-derived with `math.fsum` and a
    plain Python loop, independently of the shipped chunked implementation."""
    win, bars = windows(FRAMES[frame])
    ran = 0
    for i in range(0, win.shape[0], EXACT_STRIDE):
        mine = float(base(frame).iloc[int(bars[i])])
        other = value_from_exact(win[i])
        if math.isnan(mine) or math.isnan(other):
            assert math.isnan(mine) and math.isnan(other), (frame, int(bars[i]))
        else:
            assert abs(mine - other) < 1e-9, (frame, int(bars[i]), mine, other)
        ran += 1
    assert ran >= 20, ran


@pytest.mark.parametrize("frame", list(FRAMES))
def test_matches_the_oracle_at_a_non_default_length(frame):
    length = 120
    win, bars = windows(FRAMES[frame], length=length)
    mine_series = c22_forecast_error(FRAMES[frame], length=length)
    ran = 0
    for i in range(0, win.shape[0], EXACT_STRIDE):
        mine = float(mine_series.iloc[int(bars[i])])
        other = value_from_exact(win[i])
        if math.isnan(mine) or math.isnan(other):
            assert math.isnan(mine) and math.isnan(other), (frame, int(bars[i]))
        else:
            assert abs(mine - other) < 1e-9, (frame, int(bars[i]), mine, other)
        ran += 1
    assert ran >= 10, ran


def test_the_shipped_kernel_matches_the_oracle_on_a_designed_window():
    """A hand-built window with an obvious trend plus a wobble, so the
    3-point mean forecast neither tracks it perfectly nor misses by a mile
    -- exercising ordinary interior arithmetic rather than a degenerate
    edge case."""
    window = [100.0 + i + (2.0 if i % 3 == 0 else -1.0) for i in range(20)]
    mine = shipped_on(window)
    other = value_from_exact(window)
    assert math.isfinite(mine) and math.isfinite(other)
    assert abs(mine - other) < 1e-9, (mine, other)


@pytest.mark.parametrize("ddof_pair", [(0, 1), (1, 0), (0, 0)])
def test_the_shipped_ddof_pair_is_not_interchangeable_with_the_others(ddof_pair):
    """Both ddof knobs matter to the OUTPUT, not just to the reference fit:
    on a stochastic window, any other (z-ddof, resid-ddof) pair must
    disagree with the shipped (1, 1) by more than float noise."""
    win, _ = windows(FRAMES["walk"])
    window = win[500]
    shipped = value_from_exact(window, zddof=ZSCORE_DDOF, resddof=RESID_DDOF)
    other = value_from_exact(window, zddof=ddof_pair[0], resddof=ddof_pair[1])
    assert abs(shipped - other) > 1e-4, (ddof_pair, shipped, other)


def test_the_module_docstring_attributes_the_source():
    doc = c22_forecast_error.__doc__
    for needle in ("Lubba", "33:1821", "FC_LocalSimple", "GPL-3.0", "#137"):
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
    "write-back-dated": (
        "out[length + a:length + b] = _forecast_error_rows(win[a:b])",
        "out[length - 1 + a:length - 1 + b] = _forecast_error_rows(win[a:b])"),
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
    "chunk-wide-sd": (
        "sd = block.std(axis=1, ddof=ZSCORE_DDOF)",
        "sd = np.full(block.shape[0], block.std(ddof=ZSCORE_DDOF))"),
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
    return ns["c22_forecast_error"]


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
    assert _leaks(c22_forecast_error, f, _offsets(len(f)), splices=8) == []


@pytest.mark.parametrize("length", [MIN_LENGTH, 120, 250])
def test_the_sweep_at_non_default_lengths(length):
    f = FRAMES["walk"]
    assert _leaks(lambda s: c22_forecast_error(s, length=length), f,
                  _offsets(len(f), length), splices=4) == []


@pytest.mark.parametrize("name", ["write-back-dated", "window-one-ahead",
                                  "window-ten-ahead", "returns-rolled",
                                  "chunk-wide-mean", "chunk-wide-sd"])
def test_each_look_ahead_mutant_is_caught(name):
    """Both chunk-wide mutants are look-ahead bugs, not merely wrong
    values: the default `CHUNK_VALUES` budget holds this test's whole
    1500-bar frame in ONE chunk, so a per-chunk (rather than per-row) mean
    or sd mixes every row's own future bars into every other row's output
    -- caught at every offset the sweep tries, the same as the ordinary
    look-ahead mutants above."""
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
    assert same(c22_forecast_error(clean), fn(clean))
    caught = 0
    for j in _offsets(len(clean), count=12):
        dirty = clean.copy()
        dirty.iloc[j] = np.nan
        a = np.asarray(c22_forecast_error(dirty), float)
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
    a = base(frame).dropna().to_numpy()
    assert len(set(np.round(a, 9).tolist())) >= 20, frame
    assert float(a.max() - a.min()) > 0.01, frame


def test_a_tick_rounded_penny_frame_still_fires_everywhere():
    """The issue's own worry: shape features of returns can read BIST tick
    rounding. A 2-lira stock on a 1-kurus tick collapses many returns into
    one return value, and the column still fires on every full-window bar."""
    f = FRAMES["penny"]
    r = np.asarray(f, float)
    r = r[1:] / r[:-1] - 1.0
    assert float(np.mean(r == 0.0)) > 0.15
    s = base("penny")
    assert int(s.notna().sum()) == len(f) - LENGTH


def test_a_flat_run_blanks_from_the_first_all_zero_window():
    c = FRAMES["walk"].to_numpy().copy()
    c[400:] = c[399]
    s = c22_forecast_error(Series(c[:700]))
    assert int(s.notna().sum()) == 399
    assert not math.isnan(float(s.iloc[498]))
    assert s.iloc[499:].isna().all()


@pytest.mark.parametrize("step", [0.01, 0.001, -0.005])
def test_an_exact_geometric_ladder_never_fires_and_the_floor_is_why(step):
    f = ladder(step=step)
    assert int(c22_forecast_error(f).notna().sum()) == 0
    win, _ = windows(f)
    assert float(win.std(axis=1, ddof=ZSCORE_DDOF).max()) < NOISE_FLOOR
    unguarded = np.asarray(mutant("no-floor")(f), float)
    live = unguarded[~np.isnan(unguarded)]
    assert live.size == 1400, live.size


@pytest.mark.parametrize("frame", list(FRAMES))
def test_the_overflow_guard_is_inert_on_every_realistic_frame(frame):
    """`no-overflow-guard` drops `~np.isfinite(sd)`, which only matters when
    `sd` itself overflows to infinity -- a condition none of the six
    synthetic frames reach, so the mutant must be bit-identical to the real
    module on all of them."""
    assert same(base(frame), mutant("no-overflow-guard")(FRAMES[frame]))


def test_the_overflow_guard_is_load_bearing_on_a_designed_adversarial_window():
    """A close pair of ratio 1e200 makes one one-bar return ~1e200: its
    SQUARE overflows `float64` (max ~1.8e308) inside `block.std`, so `sd`
    itself comes back `inf` rather than NaN, and the real module blanks the
    window via the `~np.isfinite(sd)` limb `no-overflow-guard` removes.
    UNLIKE `c22_mode_10`'s equivalent guard, this module has no separate
    width/range check to fall back on: with `sd = inf`, every element's
    `z = (v - mean) / sd` collapses to `0.0` (a finite numerator over an
    infinite denominator), the 3-point forecast of three zeros is `0.0`,
    every residual is `0.0`, and `std([0, 0, ..., 0], ddof=1) = 0.0` --
    a concrete, non-NaN value. So removing the guard genuinely REVIVES the
    window instead of leaving it caught by something else."""
    f = FRAMES["walk"].copy()
    f.iloc[700] = 1e-100
    f.iloc[701] = 1e100
    assert math.isfinite(float(f.iloc[701] / f.iloc[700] - 1.0))
    s = c22_forecast_error(f)
    blank = np.where(s.isna().to_numpy())[0]
    after = blank[blank >= LENGTH]
    assert after.size == 100

    without = np.asarray(mutant("no-overflow-guard")(f), float)
    revived = np.where(np.isnan(s.to_numpy()) & ~np.isnan(without))[0]
    assert revived.size == 100, revived.size
    assert np.allclose(without[revived], 0.0, atol=1e-9), without[revived][:5]


# ------------------------------------------------------------- Gate D
@pytest.mark.parametrize("factor", [8.0, 64.0, 2.0 ** -40, 2.0 ** 40])
@pytest.mark.parametrize("frame", list(FRAMES))
def test_bit_identical_under_a_power_of_two_price_rescale(frame, factor):
    """The price enters only as `c[t] / c[t-1]`, so a power-of-two rescale
    multiplies and divides out exactly in floating point."""
    f = FRAMES[frame]
    a = c22_forecast_error(f)
    b = c22_forecast_error(f * factor)
    assert same(a, b), (frame, factor)


@pytest.mark.parametrize("factor", [10.0, 3.7, 0.1, 1.0000001])
def test_the_column_is_blind_to_an_inexact_return_rescale(factor):
    """Not bit-identical by CONSTRUCTION like the power-of-two case above --
    this scales the RETURNS stream itself, which an inexact rescale does
    not cancel out of a float division the same way. The output is a
    function of a z-score of an affine-rescaled window, which in EXACT real
    arithmetic is unchanged for any positive factor (z-scoring cancels the
    rescale), so the bound is a tolerance rather than `== 0`."""
    base_f = FRAMES["walk"]
    r = base_f.to_numpy()[1:] / base_f.to_numpy()[:-1] - 1.0
    scaled = np.empty(len(base_f))
    scaled[0] = 100.0
    scaled[1:] = scaled[0] * np.cumprod(1.0 + factor * r)
    a = base("walk").to_numpy()
    b = c22_forecast_error(Series(scaled)).to_numpy()
    moved, mask = diff_bars(a, b, tol=1e-6)
    assert mask == 0
    assert moved == 0, (factor, moved)


def test_zero_lt_fires_lt_n_at_the_default_length():
    s = base("walk")
    assert 0 < int(s.notna().sum()) < len(s)


@pytest.mark.parametrize("n,fires", [(99, None), (100, None), (101, 1),
                                     (102, 2)])
def test_a_short_input_returns_none_until_one_window_exists(n, fires):
    s = c22_forecast_error(FRAMES["walk"].iloc[:n])
    if fires is None:
        assert s is None
    else:
        assert int(s.notna().sum()) == fires


@pytest.mark.parametrize("length,name,fires", [
    (None, "C22FORECASTERROR_100", 1400),
    (0, "C22FORECASTERROR_100", 1400),
    (1, "C22FORECASTERROR_100", 1400),
    (MIN_LENGTH - 1, "C22FORECASTERROR_100", 1400),
    (MIN_LENGTH, f"C22FORECASTERROR_{MIN_LENGTH}", 1500 - MIN_LENGTH),
    (250, "C22FORECASTERROR_250", 1250),
    (250.7, "C22FORECASTERROR_250", 1250),
])
def test_the_length_guard_band(length, name, fires):
    """Below `MIN_LENGTH` = `TRAIN + 2` = 5 -- a module choice, not from the
    source -- a length falls back to 100, AND the column is named after
    the length actually used, not the one asked for. The exact branch
    `CLAUDE.md`'s "naming is API" warns about: an untested fallback here
    would silently rename the column a caller thinks it is reading."""
    s = c22_forecast_error(FRAMES["walk"], length=length)
    assert s.name == name
    assert int(s.notna().sum()) == fires
    assert MIN_LENGTH == TRAIN + 2


def test_the_offset_and_the_fill_are_the_house_ones():
    s = c22_forecast_error(FRAMES["walk"], offset=2)
    assert same(s.to_numpy()[2:], base("walk").to_numpy()[:-2])
    s = c22_forecast_error(FRAMES["walk"], fillna=-99)
    assert int(s.isna().sum()) == 0
    assert int((s == -99).sum()) == LENGTH


@pytest.mark.parametrize("budget", [100, 400, 1024])
def test_the_chunk_budget_cannot_change_a_value(budget):
    """Every quantity is per-row, so the chunk boundary is invisible."""
    want = base("walk")
    MODULE.CHUNK_VALUES = budget
    try:
        got = c22_forecast_error(FRAMES["walk"])
    finally:
        MODULE.CHUNK_VALUES = CHUNK_VALUES
    assert same(want, got)


# ------------------------------------------------------------- wiring
def test_the_five_wiring_touch_points():
    assert Path(MODULE.__file__).exists()
    assert hasattr(pandas_ta.statistics, "c22_forecast_error")
    assert "c22_forecast_error" in pandas_ta.Category["statistics"]
    assert hasattr(pandas_ta.core.AnalysisIndicators, "c22_forecast_error")
    assert (ROOT / "tests" / "test_c22_forecast_error.py").exists()


def test_the_accessor_forwards_its_parameters():
    df = DataFrame({"close": FRAMES["walk"].to_numpy()})
    acc = df.ta.c22_forecast_error()
    assert acc.name == "C22FORECASTERROR_100"
    assert same(acc, base("walk"))
    acc = df.ta.c22_forecast_error(length=250, offset=1)
    assert acc.name == "C22FORECASTERROR_250"
    assert same(acc, c22_forecast_error(FRAMES["walk"], length=250, offset=1))


def test_the_dictionary_row_describes_this_column():
    """Not just a substring check: the generator (`docs/gen_indicator_
    dictionary.py`) takes the docstring's first line as the title and the
    next contiguous run of non-blank lines as the body, so a title that
    wraps onto a second physical line swallows that line as the whole body
    and leaves the real description unreached (`tests/
    test_c22_entropy_pairs.py` found this bug the first time)."""
    text = (ROOT / "docs" / "IndicatorDictionary.md").read_text(
        encoding="utf-8")
    assert "C22FORECASTERROR_100" in text
    assert "c22_forecast_error" in text
    lines = [ln for ln in text.splitlines() if "c22_forecast_error" in ln]
    assert lines, "no row for c22_forecast_error in the dictionary"
    row_text = lines[0]
    assert "forecast" in row_text.lower()
    assert "(C22FORECASTERROR)" not in row_text, (
        "the docstring title leaked its own parenthetical short name into "
        "the dictionary body instead of a real description -- the title "
        "line wrapped and broke the generator's parser")
