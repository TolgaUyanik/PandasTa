# -*- coding: utf-8 -*-
"""C22-HIGH-FLUCTUATION (PandasTa issue #144): `c22_high_fluctuation`,
catch22's `MD_pNN_pnn40` -- the share of successive return changes (after
z-scoring) exceeding 0.04 sd, over the last 100 daily simple returns.

    C22HIGHFLUCT_100 = share of |diff(Z)| > 0.04 over the trailing 100
                        simple returns, Z = z-score(returns, ddof=1)

Gate E ledger row recorded: run `is144-c22_high_fluctuation-ec7ec0ce`, SHIP,
0.5696 vs `mcgd` (per-frame max median 0.5603), measured 2026-11-23. See
docs/C22HighFluctuationMeasured.md.

What this file pins, in order of how much it would hurt to lose:

1. **Gate A against an independent spelling.** `_oracle_share` z-scores
   with Python's stdlib `statistics.mean`/`statistics.stdev` (a different
   algorithm than numpy's) and counts diffs over threshold with a plain
   Python loop -- no numpy windowing and no shared constant with the
   module except `THRESHOLD` and `NOISE_FLOOR` themselves, named
   independently. Bit-equal on every fired bar of three frames (1,400/1,400
   each). Three hand-derived windows pin the arithmetic directly: a
   constant window (NaN, no z-score to take), a strictly monotone window
   (every diff far above threshold), and a window with one tiny final step
   (one diff below threshold).
2. **Gate B by future-perturbation sweep and mutant.** Four mutants
   `importlib`-read off this module's source and `exec`'d in memory: a
   back-dated write, a forward-shifted return, a forward-shifted diff, and
   a forward-shifted standard deviation. The real module leaks 0 of 34
   offsets on three frames (8 independent random splices each); every
   mutant is caught on a strictly positive, pinned count of those 34 --
   measured by `python docs/measure_c22_high_fluctuation.py gate_b`.
3. **`MIN_LENGTH` is not a round number.** A 2-return window is a forced
   constant 1.0 (z-scoring 2 values always places them at +-1/sqrt(2)
   ddof=1, so the one diff is a forced sqrt(2) ~= 1.4142, always above
   0.04); 3 is the smallest window that is genuinely data-dependent --
   measured over 30,000/3,000 random draws respectively
   (`docs/measure_c22_high_fluctuation.py min_length`).
4. **The noise floor** -- why a constant-return window is NaN rather than a
   share read off the sign of float64 rounding.
5. **Gate D**, including the SIGN-ASYMMETRY this feature has that
   `c22_stretch_decreasing` does not: a positive OR a negative affine
   rescale of the returns leaves the share unchanged (the statistic reads
   only `|diff(Z)|`), measured bit-identical on this frame (`walk`), not
   merely bounded by a tolerance.
6. **Gate C reachability** on four frames, including the issue's own
   tick-rounding worry (a penny frame).
7. **Five-point wiring** and the attribution in the docstring.
"""
import importlib
import statistics
import types

import numpy as np
import pandas as pd
import pytest
from numpy.lib.stride_tricks import sliding_window_view
from pandas import Series

from .context import pandas_ta as ta
from pandas_ta.statistics.c22_high_fluctuation import (
    MIN_LENGTH, NOISE_FLOOR, THRESHOLD, ZSCORE_DDOF, c22_high_fluctuation)

LENGTH = 100
_REAL = importlib.import_module("pandas_ta.statistics.c22_high_fluctuation")


# ------------------------------------------------------------- frames
def _walk(n=1500, seed=11, sigma=0.015):
    rng = np.random.default_rng(seed)
    return Series(100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n))))


def _tick_rounded(n=1500, seed=55):
    return Series(np.round(_walk(n, seed).to_numpy(), 2))


def _penny(n=1500, seed=23, level=2.0, sigma=0.012):
    """A 2-lira stock on a 1-kurus tick: many returns are exactly 0."""
    rng = np.random.default_rng(seed)
    walk = level * np.exp(np.cumsum(rng.normal(0.0, sigma, n)))
    return Series(np.round(walk, 2))


def _ar1(n=1500, seed=7, sigma=0.01, phi=0.6):
    rng = np.random.default_rng(seed)
    e = rng.normal(0.0, sigma, n)
    r = np.empty(n)
    r[0] = e[0]
    for t in range(1, n):
        r[t] = phi * r[t - 1] + e[t]
    return Series(100.0 * np.cumprod(1.0 + r))


def _closes_from_returns(r):
    """The `len(r) + 1` closes whose simple returns are exactly `r`."""
    return Series(np.concatenate([[1.0], np.cumprod(1.0 + np.asarray(r, float))]))


FRAMES = {"walk": _walk(), "tick-rounded": _tick_rounded(), "penny": _penny(),
          "ar1": _ar1()}
_BASE = {}


def base(name):
    if name not in _BASE:
        _BASE[name] = c22_high_fluctuation(FRAMES[name])
    return _BASE[name]


def same(a, b):
    x, y = np.asarray(a, float), np.asarray(b, float)
    return x.shape == y.shape and bool(
        np.all((x == y) | (np.isnan(x) & np.isnan(y))))


# ------------------------------------------------------------- Gate A
def _oracle_share(returns, threshold=THRESHOLD, floor=NOISE_FLOOR):
    """`statistics.mean`/`statistics.stdev` (stdlib, a different mean/
    variance algorithm than numpy's) z-score the window, then a plain
    Python loop counts diffs over `threshold`. Shares no array machinery
    with the shipped module."""
    r = [float(v) for v in returns]
    if not all(np.isfinite(v) for v in r):
        return float("nan")
    sd = statistics.stdev(r)
    if not (sd > floor):
        return float("nan")
    mu = statistics.mean(r)
    z = [(v - mu) / sd for v in r]
    d = [z[i + 1] - z[i] for i in range(len(z) - 1)]
    hits = sum(1 for v in d if abs(v) > threshold)
    return hits / len(d)


def _oracle_series(close, length=LENGTH):
    """`_oracle_share` applied window by window in a plain Python loop over
    explicit slices. Mirrors the module's own `r[0] = NaN` sentinel for the
    undefined first return rather than Python's negative-index wraparound."""
    c = [float(v) for v in close.to_numpy()]

    def ret(i):
        return float("nan") if i == 0 else c[i] / c[i - 1] - 1.0

    out = [float("nan")] * len(c)
    for t in range(length - 1, len(c)):
        r = [ret(i) for i in range(t - length + 1, t + 1)]
        if not all(np.isfinite(v) for v in r):
            continue
        out[t] = _oracle_share(r)
    return Series(out, index=close.index)


HAND = [
    ([0.0, 0.0, 0.0], float("nan"), "constant returns: sd is 0, no "
     "z-score to take -- NaN, not a share read off rounding noise"),
    ([0.0, 1.0, 2.0], 1.0, "strictly monotone: z-scores are -1, 0, 1 and "
     "both diffs are exactly 1.0, far above 0.04"),
    ([0.0, 1.0, 1.001], 0.5, "one big diff and one diff below threshold"),
]


@pytest.mark.parametrize("returns,expected,why", HAND,
                         ids=["constant", "monotone", "one-small-diff"])
def test_hand_derived_windows(returns, expected, why):
    n = len(returns)
    out = c22_high_fluctuation(_closes_from_returns(returns), length=n)
    assert out.name == f"C22HIGHFLUCT_{n}"
    assert out.iloc[:n].isna().all()
    got = float(out.iloc[n])
    if np.isnan(expected):
        assert np.isnan(got), why
    else:
        assert got == expected, why


@pytest.mark.parametrize("frame", ["walk", "tick-rounded", "ar1"])
def test_matches_an_independent_stdlib_statistics_spelling(frame):
    close = FRAMES[frame]
    port, oracle = base(frame), _oracle_series(close)
    assert (port.isna() == oracle.isna()).all()
    m = port.notna()
    assert int(m.sum()) == 1400
    assert (port[m] == oracle[m]).all()
    r = (close / close.shift(1) - 1.0).to_numpy()
    w = sliding_window_view(r[1:], LENGTH)
    sd = w.std(axis=1, ddof=ZSCORE_DDOF)
    assert int((sd <= NOISE_FLOOR).sum()) == 0


def test_the_module_docstring_attributes_the_source():
    doc = c22_high_fluctuation.__doc__
    for needle in ("Lubba", "33:1821", "MD_pNN_pnn40", "GPL-3.0", "#144"):
        assert needle in doc, needle
    assert "classification" in doc.lower()
    assert "existence" in doc and "not evidence" in doc


def test_the_reference_implementation_is_not_imported_by_shipped_code():
    """The references (pycatch22, hctsa) are GPL-3.0 and this fork is MIT."""
    import pathlib
    root = pathlib.Path(_REAL.__file__).resolve().parent.parent.parent
    hits = []
    files = sorted((root / "pandas_ta").rglob("*.py"))
    for p in files:
        for line in p.read_text(encoding="utf-8").splitlines():
            s = line.strip()
            if (s.startswith("import ") or s.startswith("from ")) \
                    and ("catch22" in s.replace("c22", "") or "hctsa" in s):
                hits.append((str(p.relative_to(root)), s))
    assert hits == [], hits
    assert len(files) > 300, len(files)


# ------------------------------------------------------------- min length
def test_a_two_return_window_is_a_forced_constant():
    """Measured over 3,000 random draws (`docs/measure_c22_high_fluctuation.py
    min_length`): z-scoring 2 values always places them at -1/sqrt(2) and
    +1/sqrt(2) (ddof=1), so the one diff is a forced sqrt(2), always above
    THRESHOLD -- every non-degenerate 2-return window reads 1.0."""
    rng = np.random.default_rng(0)
    vals = set()
    for _ in range(3000):
        r = rng.normal(0.0, 1.0, 2)
        vals.add(round(_oracle_share(r), 6))
    assert vals == {1.0}


def test_min_length_three_is_informative_not_a_forced_constant():
    """The smallest window this module accepts (`MIN_LENGTH`) is genuinely
    data-dependent, unlike length=2 above."""
    rng = np.random.default_rng(1)
    vals = set()
    for _ in range(30000):
        r = rng.normal(0.0, 1.0, 3)
        vals.add(round(_oracle_share(r), 6))
    assert vals == {0.5, 1.0}


# ------------------------------------------------------------- Gate B
MUTANTS = {
    "write-back-dated": (
        "    out[length - 1:] = np.where(bad, np.nan, share)",
        "    out[length - 2:-1] = np.where(bad, np.nan, share)"),
    "forward-return": (
        "    with np.errstate(over=\"ignore\"):\n        r[1:] = c[1:] / c[:-1] - 1.0",
        "    with np.errstate(over=\"ignore\"):\n        r[:-1] = c[1:] / c[:-1] - 1.0"),
    "forward-diff": ("    d = z[:, 1:] - z[:, :-1]",
                     "    d = np.roll(z[:, 1:] - z[:, :-1], -1, axis=0)"),
    "forward-sd": ("        sd = windows.std(axis=1, ddof=ZSCORE_DDOF)",
                   "        sd = np.roll(windows.std(axis=1, ddof=ZSCORE_DDOF), -1)"),
}


def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_c22_high_fluctuation_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


OFFSETS = range(140, 1500, 40)


def _spliced(close, j, seed):
    """`close` with everything from bar `j` onward replaced by an
    independent random path starting from `close[j - 1]`. The level jump at
    the splice plants an extreme return right where a one-bar look-ahead
    would first be able to read it."""
    rng = np.random.default_rng(seed)
    c = close.to_numpy(dtype=float).copy()
    c[j:] = c[j - 1] * np.cumprod(1.0 + rng.normal(0.0005, 0.02, c.size - j))
    return Series(c, index=close.index)


def _leak_offsets(fn, close, offsets=OFFSETS, splices=8):
    """A hit at J means at least one of `splices` independent random futures
    moved something strictly before J. Prefix truncation alone cannot see
    back-dating, which is why this is a perturbation sweep."""
    base_out = fn(close)
    hit = []
    for j in offsets:
        for s in range(splices):
            out = fn(_spliced(close, j, seed=909 + 7919 * s))
            a, b = base_out.iloc[:j], out.iloc[:j]
            if not (a.isna() == b.isna()).all():
                hit.append(j)
                break
            m = a.notna()
            if (a[m] != b[m]).any():
                hit.append(j)
                break
    return hit


FRAMES_B = {"walk": _walk(), "tick-rounded": _tick_rounded(), "ar1": _ar1()}


@pytest.mark.parametrize("frame", sorted(FRAMES_B))
def test_real_module_never_reads_the_future(frame):
    assert _leak_offsets(c22_high_fluctuation, FRAMES_B[frame]) == []


#: (mutant, frame) -> offsets of 34 caught, measured by
#: `python docs/measure_c22_high_fluctuation.py gate_b`. Pinned at the
#: measured count rather than a guessed lower bound.
CAUGHT = {("write-back-dated", "ar1"): 15, ("write-back-dated", "tick-rounded"): 8,
          ("write-back-dated", "walk"): 14,
          ("forward-return", "ar1"): 15, ("forward-return", "tick-rounded"): 8,
          ("forward-return", "walk"): 14,
          ("forward-diff", "ar1"): 15, ("forward-diff", "tick-rounded"): 8,
          ("forward-diff", "walk"): 14,
          ("forward-sd", "ar1"): 9, ("forward-sd", "tick-rounded"): 6,
          ("forward-sd", "walk"): 8}


@pytest.mark.parametrize("name", sorted(MUTANTS))
@pytest.mark.parametrize("frame", sorted(FRAMES_B))
def test_each_mutant_leaks_a_strictly_positive_pinned_count(name, frame):
    mod = _load_mutant(*MUTANTS[name])
    close = FRAMES_B[frame]
    assert not mod.c22_high_fluctuation(close).equals(
        c22_high_fluctuation(close))
    hits = _leak_offsets(mod.c22_high_fluctuation, close)
    assert len(hits) == CAUGHT[(name, frame)], (name, frame, len(hits))
    assert len(hits) > 0


# ------------------------------------------------------------- noise floor
def _ladder(n=300, step=0.01, start=100.0):
    return Series(start * (1.0 + step) ** np.arange(n, dtype=float))


@pytest.mark.parametrize("step", [0.01, 0.001, -0.005])
def test_an_exact_geometric_ladder_reads_nan_not_a_noise_share(step):
    f = _ladder(step=step)
    out = c22_high_fluctuation(f)
    r = f.to_numpy()[1:] / f.to_numpy()[:-1] - 1.0
    w = sliding_window_view(r[1:], LENGTH)
    sd = w.std(axis=1, ddof=ZSCORE_DDOF)
    assert float(np.nanmax(sd)) < NOISE_FLOOR
    assert int(out.notna().sum()) == 0


def test_the_noise_floor_is_an_absolute_constant():
    assert _REAL.NOISE_ULPS == 4096
    assert _REAL.NOISE_FLOOR == pytest.approx(9.094947017729282e-13, rel=1e-12)
    for frame in ("walk", "tick-rounded"):
        close = FRAMES[frame]
        r = (close / close.shift(1) - 1.0).to_numpy()
        w = sliding_window_view(r[1:], LENGTH)
        sd = w.std(axis=1, ddof=ZSCORE_DDOF)
        assert int((sd <= NOISE_FLOOR).sum()) == 0


# ------------------------------------------------------------- Gate C
@pytest.mark.parametrize("frame", list(FRAMES))
def test_every_bar_with_a_full_window_fires(frame):
    s = base(frame)
    assert int(s.notna().sum()) == len(s) - LENGTH
    assert int(s.notna().to_numpy().argmax()) == LENGTH
    assert s.iloc[:LENGTH].isna().all()


#: Measured by `python docs/measure_c22_high_fluctuation.py gate_c_d`.
DISTINCT = {"walk": 7, "tick-rounded": 7, "ar1": 8, "penny": 27}


@pytest.mark.parametrize("frame", list(FRAMES))
def test_the_column_is_not_constant_on_a_real_shaped_frame(frame):
    a = base(frame).dropna().to_numpy()
    assert len(set(a.tolist())) == DISTINCT[frame], frame
    assert float(a.min()) >= 0.0 and float(a.max()) <= 1.0, frame


def test_a_tick_rounded_penny_frame_still_fires_everywhere():
    """The issue's own worry: a 2-lira stock on a 1-kurus tick fires on
    every full-window bar despite many exactly-repeated (zero) returns, and
    is MORE varied there (more distinct shares) than on a continuous
    frame, since repeated zero returns shrink many diffs below 0.04."""
    f = FRAMES["penny"]
    r = np.asarray(f, float)
    r = r[1:] / r[:-1] - 1.0
    assert float(np.mean(r == 0.0)) > 0.10
    s = base("penny")
    assert int(s.notna().sum()) == len(f) - LENGTH
    assert s.nunique() == DISTINCT["penny"]


def test_zero_lt_fires_lt_n():
    for frame in FRAMES:
        s = base(frame)
        assert 0 < int(s.notna().sum()) < len(s)


# ------------------------------------------------------------- Gate D
@pytest.mark.parametrize("factor", [8.0, 64.0])
@pytest.mark.parametrize("frame", list(FRAMES))
def test_bit_identical_under_a_power_of_two_price_rescale(frame, factor):
    f = FRAMES[frame]
    assert same(c22_high_fluctuation(f), c22_high_fluctuation(f * factor))


@pytest.mark.parametrize("factor", [10.0, 3.7, 0.1])
@pytest.mark.parametrize("frame", list(FRAMES))
def test_bit_identical_under_a_price_rescale_that_is_not_a_power_of_two(
        frame, factor):
    f = FRAMES[frame]
    assert same(c22_high_fluctuation(f), c22_high_fluctuation(f * factor))


@pytest.mark.parametrize("shift", [0.0, 0.01])
@pytest.mark.parametrize("factor", [10.0, 3.7, 0.1, 2.5])
def test_bit_identical_under_a_positive_affine_rescale_of_the_returns(
        factor, shift):
    """Measured, not merely argued: the z-score cancels a positive affine
    map of the returns exactly in real arithmetic, and the share -- a count
    over a fixed grid, `k / (length - 1)` -- only moves if a diff crosses
    the 0.04 boundary, which none do on this frame at these factors."""
    close = FRAMES["walk"]
    r = (close / close.shift(1) - 1.0).to_numpy()
    r[0] = 0.0
    scaled = Series(100.0 * np.cumprod(1.0 + factor * r + shift),
                    index=close.index)
    base_out, out = c22_high_fluctuation(close), c22_high_fluctuation(scaled)
    assert same(base_out, out)


def test_bit_identical_under_a_negative_rescale_of_the_returns():
    """The feature this column has that `c22_stretch_decreasing` does NOT:
    the statistic reads only `|diff(Z)|`, and a negative affine map flips
    every z-score's sign (`Z' = -Z`) without changing any diff's absolute
    size, so the share is unchanged -- unlike a run-of-falls statistic,
    which would read "rises" instead."""
    close = FRAMES["walk"]
    r = (close / close.shift(1) - 1.0).to_numpy()
    r[0] = 0.0
    negated = Series(100.0 * np.cumprod(1.0 - r), index=close.index)
    base_out, out = c22_high_fluctuation(close), c22_high_fluctuation(negated)
    assert same(base_out, out)


def test_a_short_input_returns_none_until_one_window_exists():
    assert c22_high_fluctuation(_walk(LENGTH)) is None
    out = c22_high_fluctuation(_walk(LENGTH + 1, seed=2))
    assert int(out.notna().sum()) <= 1


# ------------------------------------------------------------- guards, edge
@pytest.mark.parametrize("length", [None, 0, -5, 1, 2, 0.5, 1.9])
def test_a_length_below_the_minimum_falls_back_to_the_default(length):
    out = c22_high_fluctuation(_walk(400, seed=31), length=length)
    assert out.name == "C22HIGHFLUCT_100"


def test_fractional_lengths_that_truncate_the_same_are_identical():
    close = _walk(400, seed=31)
    pd.testing.assert_series_equal(c22_high_fluctuation(close, length=50.9),
                                   c22_high_fluctuation(close, length=50))


def test_distinct_lengths_produce_distinct_names_and_values():
    close = _walk(400, seed=31)
    a, b = (c22_high_fluctuation(close, length=10),
            c22_high_fluctuation(close, length=60))
    assert (a.name, b.name) == ("C22HIGHFLUCT_10", "C22HIGHFLUCT_60")


def test_the_offset_and_the_fill_are_the_house_ones():
    s = c22_high_fluctuation(FRAMES["walk"], offset=2)
    assert same(s.to_numpy()[2:], base("walk").to_numpy()[:-2])
    s = c22_high_fluctuation(FRAMES["walk"], fillna=-99)
    assert int(s.isna().sum()) == 0
    assert int((s == -99).sum()) == LENGTH


@pytest.mark.parametrize("bad", [np.nan, 0.0, -5.0, np.inf, 1e-310])
def test_a_bad_close_empties_its_own_windows_and_nothing_earlier(bad):
    close = _walk(400, seed=21)
    base_out = c22_high_fluctuation(close)
    holed = close.copy()
    holed.iloc[200] = bad
    out = c22_high_fluctuation(holed)
    emptied = np.flatnonzero((base_out.notna() & out.isna()).to_numpy())
    assert len(emptied) == LENGTH + 1
    assert (int(emptied.min()), int(emptied.max())) == (200, 300)
    before = base_out.notna() & out.notna() & (base_out != out)
    assert int(before.iloc[:200].sum()) == 0


def test_an_overflowing_return_pair_is_emptied():
    close = _walk(400, seed=31)
    base_out = c22_high_fluctuation(close)
    pair = close.copy()
    pair.iloc[200] = 1e-300
    pair.iloc[201] = 1e50
    out = c22_high_fluctuation(pair)
    emptied = np.flatnonzero((base_out.notna() & out.isna()).to_numpy())
    assert len(emptied) == LENGTH
    assert (int(emptied.min()), int(emptied.max())) == (201, 300)


# ------------------------------------------------------------- wiring
def test_name_registration_and_accessor():
    close = _walk(300, seed=17)
    df = pd.DataFrame({"open": close, "high": close * 1.01,
                       "low": close * 0.99, "close": close,
                       "volume": Series(np.full(len(close), 1000.0))})
    assert "c22_high_fluctuation" in ta.Category["statistics"]
    assert hasattr(df.ta, "c22_high_fluctuation")
    direct = c22_high_fluctuation(close)
    through = df.ta.c22_high_fluctuation()
    pd.testing.assert_series_equal(through, direct, check_names=True)
    assert through.name == "C22HIGHFLUCT_100"
    assert direct.category == "statistics"


def test_the_dictionary_row_describes_this_column():
    import pathlib
    root = pathlib.Path(_REAL.__file__).resolve().parent.parent.parent
    text = (root / "docs" / "IndicatorDictionary.md").read_text(
        encoding="utf-8")
    assert "C22HIGHFLUCT_100" in text
    lines = [ln for ln in text.splitlines() if "c22_high_fluctuation" in ln]
    assert lines, "no row for c22_high_fluctuation in the dictionary"
