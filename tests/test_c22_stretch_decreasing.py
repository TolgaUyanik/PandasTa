# -*- coding: utf-8 -*-
"""C22-STRETCH-DECREASING (PandasTa issue #140): `c22_stretch_decreasing`,
catch22's `SB_BinaryStats_diff_longstretch0` -- the longest run of
successive decreases in the last 100 daily simple returns.

    C22STRETCHDEC_100 = longest run of consecutive (r[i] < r[i-1]) over the
                        trailing 100 simple returns

Gate E is owed: the launcher runs `gate_e_overlap.py` after this session and
a later session records the `docs/gate_e_ledger.csv` row, so
`tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
fails here until then (expected, per the issue-solver rules).

What this file pins, in order of how much it would hurt to lose:

1. **Gate A against an independent spelling.** `_itertools_oracle` re-counts
   the longest run of strict decreases with `itertools.groupby` over
   explicit window slices -- no numpy windowing, no vectorised run
   counting, and no shared constant with the module (not even
   `NOISE_FLOOR`) -- and agrees bit-for-bit with the shipped column on
   every fired bar of three frames. Eight HAND-derived windows pin the
   arithmetic directly: runs at either end of a window, an alternating
   window that can only score 1, and a monotone window that scores the
   maximum `length - 1`.
2. **Gate B by mutant**, five mutants `importlib`-read off this module's
   source and `exec`'d in memory: a back-dated write, a forward-shifted
   return, a forward-shifted diff sign, a forward-shifted run-length window,
   and a forward-shifted span guard. The PRIMARY proof is a single
   HAND-ENGINEERED window built for maximum sensitivity to a one-bar
   look-ahead (`test_an_engineered_window_catches_every_one_bar_mutant`):
   this column's value range is narrow and heavily tied (Gate C measures 3
   to 6 distinct values on 1,400 fired bars), so a generic future-splice
   sweep is mostly BLIND to a one-bar shift -- measured directly
   (`test_the_broad_sweep_is_mostly_blind_but_never_wrong`), the real module
   leaks 0 of 34 offsets on three frames (8 independent random splices
   each) while the four equivalent one-bar mutants are each caught on only
   1 to 2 of those 34. The engineered window sidesteps that by construction
   rather than by luck.
3. **The noise floor** -- why an exactly geometric path reads 0 rather than
   a run of float64 rounding, and what the floor costs on a monotone
   one-tick-per-bar path.
4. **Gate D, and the STRONGER-than-usual scale-free claim.** Because the
   statistic reads only the SIGN of each return-to-return diff, and a
   positive affine map cannot flip a sign, the column is bit-identical not
   just under a x8/x64 price rescale (the usual `8a/8b == a/b` argument)
   but also under a positive rescale of the RETURNS themselves -- measured
   directly, not merely bounded by a tolerance.
5. **Gate C reachability**, including the issue's own worry: a tick-rounded
   penny frame with many exactly-repeated (zero) returns still fires on
   every full-window bar.
6. **Five-point wiring** and the attribution in the docstring.
"""
import importlib
import itertools
import types

import numpy as np
import pandas as pd
import pytest
from numpy.lib.stride_tricks import sliding_window_view
from pandas import Series

from .context import pandas_ta as ta
from pandas_ta.statistics.c22_stretch_decreasing import (
    MIN_LENGTH, NOISE_FLOOR, c22_stretch_decreasing)

LENGTH = 100
_REAL = importlib.import_module("pandas_ta.statistics.c22_stretch_decreasing")


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
        _BASE[name] = c22_stretch_decreasing(FRAMES[name])
    return _BASE[name]


def same(a, b):
    x, y = np.asarray(a, float), np.asarray(b, float)
    return x.shape == y.shape and bool(
        np.all((x == y) | (np.isnan(x) & np.isnan(y))))


# ------------------------------------------------------------- Gate A
HAND = [
    ([5.0, 4.0, 3.0, 2.0, 1.0], 4.0, "strictly monotone falling: every one "
     "of the 4 diffs is negative, the maximum a 5-return window can score"),
    ([1.0, 2.0, 3.0, 4.0, 5.0], 0.0, "strictly monotone rising: no diff is "
     "negative"),
    ([1.0, 1.0, 1.0, 1.0, 1.0], 0.0, "constant returns: every diff is "
     "exactly 0, which is flat, not falling"),
    ([3.0, 2.0, 1.0, 2.0, 3.0, 2.0, 1.0, 0.0], 3.0, "two falling runs (2 "
     "and 3 diffs): the LONGEST is the second, 3"),
    ([1.0, 0.0, 1.0, 0.0, 1.0, 0.0, 1.0, 0.0], 1.0, "alternating: every "
     "other diff is negative, so no run of negatives reaches 2"),
    ([5.0, 4.0, 3.0, 3.0, 2.0, 1.0], 2.0, "a flat step (3.0 to 3.0) in the "
     "middle of a fall breaks the run into 2 and 2"),
    ([0.0, 0.0, 5.0, 4.0, 3.0, 2.0, 1.0], 4.0, "a falling run at the far "
     "end of the window"),
    ([5.0, 4.0, 3.0, 2.0, 1.0, 0.0, 0.0], 5.0, "a falling run then flat: "
     "the last diff (0 - 0 = 0) is the only non-negative one, so the run "
     "is 5 of the 6 diffs, not 4"),
]


@pytest.mark.parametrize("returns,expected,why", HAND,
                         ids=[h[2].split(":")[0] for h in HAND])
def test_hand_derived_windows(returns, expected, why):
    """Each window's answer is derived by hand from the returns, with no
    implementation involved; the closes are reconstructed from them by
    `cumprod(1 + r)`, so the module's own return arithmetic is what maps
    one to the other."""
    n = len(returns)
    out = c22_stretch_decreasing(_closes_from_returns(returns), length=n)
    assert out.name == f"C22STRETCHDEC_{n}"
    assert out.iloc[:n].isna().all()
    assert float(out.iloc[n]) == expected, why


def _longest_falling_run(x):
    """`max(run lengths of True in groupby(diff(x) < 0))`, 0 when there is
    no run. An independent spelling, not a copy of any reference code,
    which this session cannot read (GPL-3.0)."""
    x = np.asarray(x, dtype=float)
    d = np.diff(x)
    runs = [len(list(g)) for v, g in itertools.groupby(d < 0.0) if v]
    return float(max(runs)) if runs else 0.0


def _itertools_oracle(close, length=LENGTH):
    """`_longest_falling_run` applied window by window in a plain Python
    loop over explicit slices: no numpy windowing, no vectorised run
    counting, and NO noise floor -- it shares nothing with the module. The
    test below asserts separately that the floor never fires on these
    frames, so bit-equality is evidence rather than a shared branch."""
    c = [float(v) for v in close.to_numpy()]
    out = [float("nan")] * len(c)
    for t in range(length, len(c)):
        r = [c[i] / c[i - 1] - 1.0 for i in range(t - length + 1, t + 1)]
        out[t] = _longest_falling_run(r)
    return Series(out, index=close.index)


@pytest.mark.parametrize("frame", ["walk", "tick-rounded", "ar1"])
def test_matches_an_independent_groupby_spelling_window_by_window(frame):
    close = FRAMES[frame]
    port, oracle = base(frame), _itertools_oracle(close)
    assert (port.isna() == oracle.isna()).all()
    m = port.notna()
    assert int(m.sum()) == 1400
    assert (port[m] == oracle[m]).all()
    # The module's one addition to the oracle is the noise floor; confirm it
    # cannot be what makes them agree here because it never fires.
    r = (close / close.shift(1) - 1.0).to_numpy()
    w = sliding_window_view(r[1:], LENGTH)
    span = w.max(axis=1) - w.min(axis=1)
    assert int((span <= NOISE_FLOOR).sum()) == 0


def test_the_module_docstring_attributes_the_source():
    doc = c22_stretch_decreasing.__doc__
    for needle in ("Lubba", "33:1821", "SB_BinaryStats_diff_longstretch0",
                   "GPL-3.0", "#140"):
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


# ------------------------------------------------------------- Gate B
MUTANTS = {
    "write-back-dated": (
        "out[length - 1:] = np.where(bad, np.nan, body)",
        "out[length - 2:-1] = np.where(bad, np.nan, body)"),
    "forward-return": ("r[1:] = c[1:] / c[:-1] - 1.0",
                       "r[:-1] = c[1:] / c[:-1] - 1.0"),
    "forward-diff-sign": ("falling = diffs < 0.0",
                          "falling = np.roll(diffs < 0.0, -1, axis=0)"),
    "forward-window": ("current = np.where(falling[:, j], current + 1.0, 0.0)",
                       "current = np.where(np.roll(falling, -1, axis=0)[:, j], "
                       "current + 1.0, 0.0)"),
    "forward-span": ("span = windows.max(axis=1) - windows.min(axis=1)",
                     "span = np.roll(windows.max(axis=1) - windows.min(axis=1), -1)"),
}


def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_c22_stretch_decreasing_mutant")
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
    back-dating, which is why this is a perturbation sweep, and several
    splices per offset are tried because this column (see Gate C) is far
    more tie-heavy than a continuous statistic, so one fixed future often
    fails to move it even under a real one-bar look-ahead."""
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
    assert _leak_offsets(c22_stretch_decreasing, FRAMES_B[frame]) == []


#: (mutant, frame) -> offsets of 34 caught, measured by
#: `python docs/measure_c22_stretch_decreasing.py gate_b`. Pinned at the
#: measured count rather than a guessed lower bound, because it IS the
#: finding: this column is so tie-heavy (Gate C: 3 to 6 distinct values on
#: 1,400 fired bars) that a generic future-splice sweep barely moves it even
#: under a genuine one-bar look-ahead. The deterministic engineered-window
#: test below is the primary Gate B proof; this sweep's job is only to show
#: the REAL module at a clean 0 and the mutants at something strictly above it.
ONE_BAR_MUTANTS = ["write-back-dated", "forward-return", "forward-diff-sign",
                   "forward-window"]
CAUGHT = {("write-back-dated", "ar1"): 1, ("write-back-dated", "tick-rounded"): 2,
          ("write-back-dated", "walk"): 1,
          ("forward-return", "ar1"): 1, ("forward-return", "tick-rounded"): 2,
          ("forward-return", "walk"): 1,
          ("forward-diff-sign", "ar1"): 1, ("forward-diff-sign", "tick-rounded"): 2,
          ("forward-diff-sign", "walk"): 1,
          ("forward-window", "ar1"): 1, ("forward-window", "tick-rounded"): 2,
          ("forward-window", "walk"): 1}


@pytest.mark.parametrize("name", ONE_BAR_MUTANTS)
@pytest.mark.parametrize("frame", sorted(FRAMES_B))
def test_the_broad_sweep_is_mostly_blind_but_never_wrong(name, frame):
    mod = _load_mutant(*MUTANTS[name])
    close = FRAMES_B[frame]
    assert not mod.c22_stretch_decreasing(close).equals(
        c22_stretch_decreasing(close))
    hits = _leak_offsets(mod.c22_stretch_decreasing, close)
    assert len(hits) == CAUGHT[(name, frame)], (name, frame, len(hits))


def test_an_engineered_window_catches_every_one_bar_mutant():
    """The PRIMARY Gate B proof, built to be maximally sensitive rather than
    to rely on the broad sweep's luck: 15 alternating returns (no run of
    negative diffs longer than 1), then a strictly decreasing tail of 5
    values (a run of 4), then one more strictly smaller value. The window
    ending just before that last value must read 4; the window ending AT it
    must read 5 -- a one-bar look-ahead reports the second number for the
    first window."""
    length = 20
    r = [0, 10] * 7 + [0] + [9, 8, 7, 6, 5] + [4]
    assert len(r) == 21
    closes = _closes_from_returns(r)
    out = c22_stretch_decreasing(closes, length=length)
    assert float(out.iloc[20]) == 4.0
    assert float(out.iloc[21]) == 5.0
    for name in ONE_BAR_MUTANTS:
        mod = _load_mutant(*MUTANTS[name])
        mutated = mod.c22_stretch_decreasing(closes, length=length)
        assert float(mutated.iloc[20]) == 5.0, name


def test_the_span_mutant_needs_a_degenerate_window_to_be_forced_live():
    """`forward-span` only moves the OUTPUT when the guard actually fires,
    which never happens on a continuous frame (0/34 above) -- so it is also
    swept on a walk carrying `length + 1` identical closes ending at each
    offset, where the real module still leaks 0 and the mutant is caught on
    1 of 34 (the same tie-heavy limitation as the one-bar mutants)."""
    c = _walk(seed=11).to_numpy().copy()
    for j in OFFSETS:
        c[j - LENGTH:j + 1] = c[j - LENGTH]
    frame = Series(c)
    assert _leak_offsets(c22_stretch_decreasing, frame) == []
    mod = _load_mutant(*MUTANTS["forward-span"])
    assert len(_leak_offsets(mod.c22_stretch_decreasing, frame)) == 1


# ------------------------------------------------------------- noise floor
def _ladder(n=300, step=0.01, start=100.0):
    return Series(start * (1.0 + step) ** np.arange(n, dtype=float))


@pytest.mark.parametrize("step", [0.01, 0.001, -0.005])
def test_an_exact_geometric_ladder_reads_zero_not_a_run_of_noise(step):
    f = _ladder(step=step)
    out = c22_stretch_decreasing(f)
    win, _ = (lambda c: (sliding_window_view(
        (c.to_numpy()[1:] / c.to_numpy()[:-1] - 1.0), LENGTH), None))(f)
    span = win.max(axis=1) - win.min(axis=1)
    assert float(span.max()) < NOISE_FLOOR
    assert int(out.notna().sum()) == 200
    assert sorted(set(out.dropna().tolist())) == [0.0]


def test_the_noise_floor_is_an_absolute_constant_and_costs_nothing_on_real_data():
    assert _REAL.NOISE_ULPS == 4096
    assert _REAL.NOISE_FLOOR == pytest.approx(9.094947017729282e-13, rel=1e-12)
    for frame in ("walk", "tick-rounded"):
        close = FRAMES[frame]
        r = (close / close.shift(1) - 1.0).to_numpy()
        w = sliding_window_view(r[1:], LENGTH)
        span = w.max(axis=1) - w.min(axis=1)
        assert int((span <= NOISE_FLOOR).sum()) == 0


def test_what_the_floor_costs_on_a_monotone_one_tick_per_bar_path():
    """The honest cost, pinned rather than argued away: at a high enough
    price the fixed tick is a shrinking fraction of the price, so the
    return span sits below the floor even though the path is genuinely
    non-constant, and the column reads 0 rather than the near-maximal run
    the (false) mathematical limit of a one-tick ladder would suggest."""
    closes = Series(1e6 + 0.001 * np.arange(300))
    r = closes / closes.shift(1) - 1.0
    span = float((r.rolling(LENGTH).max() - r.rolling(LENGTH).min()).iloc[-1])
    assert span < NOISE_FLOOR
    out = c22_stretch_decreasing(closes)
    assert sorted(set(out.dropna().tolist())) == [0.0]


# ------------------------------------------------------------- Gate C
@pytest.mark.parametrize("frame", list(FRAMES))
def test_every_bar_with_a_full_window_fires(frame):
    s = base(frame)
    assert int(s.notna().sum()) == len(s) - LENGTH
    assert int(s.notna().to_numpy().argmax()) == LENGTH
    assert s.iloc[:LENGTH].isna().all()


#: Measured by `python docs/measure_c22_stretch_decreasing.py gate_c_d`.
#: Narrow and heavily tied by construction -- see the Gate B docstring note
#: above -- so this is pinned at the measured count rather than a round
#: number.
DISTINCT = {"walk": 3, "tick-rounded": 6, "ar1": 4, "penny": 4}


@pytest.mark.parametrize("frame", list(FRAMES))
def test_the_column_is_not_constant_on_a_real_shaped_frame(frame):
    a = base(frame).dropna().to_numpy()
    assert len(set(a.tolist())) == DISTINCT[frame], frame
    assert float(a.max()) >= 2.0, frame


def test_a_tick_rounded_penny_frame_still_fires_everywhere():
    """The issue's own worry: a 2-lira stock on a 1-kurus tick fires on
    every full-window bar despite many exactly-repeated (zero) returns."""
    f = FRAMES["penny"]
    r = np.asarray(f, float)
    r = r[1:] / r[:-1] - 1.0
    assert float(np.mean(r == 0.0)) > 0.10
    s = base("penny")
    assert int(s.notna().sum()) == len(f) - LENGTH
    assert s.nunique() == DISTINCT["penny"]


def test_a_pure_uptrend_never_falls():
    out = c22_stretch_decreasing(Series(100.0 * np.exp(np.arange(300) * 0.02)))
    assert int(out.notna().sum()) == 200
    assert sorted(set(out.dropna().tolist())) == [0.0]


def test_zero_lt_fires_lt_n():
    for frame in FRAMES:
        s = base(frame)
        assert 0 < int(s.notna().sum()) < len(s)


# ------------------------------------------------------------- Gate D
@pytest.mark.parametrize("factor", [8.0, 64.0])
@pytest.mark.parametrize("frame", list(FRAMES))
def test_bit_identical_under_a_power_of_two_price_rescale(frame, factor):
    f = FRAMES[frame]
    assert same(c22_stretch_decreasing(f), c22_stretch_decreasing(f * factor))


@pytest.mark.parametrize("factor", [10.0, 3.7, 0.1])
@pytest.mark.parametrize("frame", list(FRAMES))
def test_bit_identical_under_a_price_rescale_that_is_not_a_power_of_two(
        frame, factor):
    """Not merely a tolerance claim: the price enters only as a ratio of
    consecutive closes, and `(k*a) / (k*b)` is the exact double `a / b` for
    ANY positive `k`, not just a power of two -- IEEE-754 division rounds
    the true quotient to nearest, and the true quotient is unchanged by a
    common positive factor on both operands."""
    f = FRAMES[frame]
    assert same(c22_stretch_decreasing(f), c22_stretch_decreasing(f * factor))


@pytest.mark.parametrize("factor", [10.0, 3.7, 0.1, 2.5])
def test_bit_identical_under_a_positive_affine_rescale_of_the_returns(factor):
    """The STRONGER claim this column can make that `ts_strike_20` cannot:
    the statistic reads only the SIGN of each return-to-return diff, and
    `diff(a*r) = a * diff(r)` for a constant `a`, so a positive rescale of
    the returns themselves (not just of the price) cannot flip a sign and
    is measured here to be bit-identical, not merely close."""
    close = FRAMES["walk"]
    r = (close / close.shift(1) - 1.0).to_numpy()
    r[0] = 0.0
    scaled = Series(100.0 * np.cumprod(1.0 + factor * r), index=close.index)
    base_out, out = c22_stretch_decreasing(close), c22_stretch_decreasing(scaled)
    assert same(base_out, out)


def test_an_affine_rescale_with_a_negative_slope_flips_rises_into_falls():
    """The mirror case, priced rather than left implicit: a NEGATIVE slope
    flips every sign, so it is emphatically NOT invariant under it -- this
    column answers "how long did returns fall", and negating returns asks
    "how long did they rise", a different question on the same data."""
    close = FRAMES["walk"]
    r = (close / close.shift(1) - 1.0).to_numpy()
    r[0] = 0.0
    negated = Series(100.0 * np.cumprod(1.0 - r), index=close.index)
    base_out, out = c22_stretch_decreasing(close), c22_stretch_decreasing(negated)
    m = base_out.notna() & out.notna()
    assert int(m.sum()) == 1400
    assert int((base_out[m] == out[m]).sum()) < 1400


def test_a_short_input_returns_none_until_one_window_exists():
    assert c22_stretch_decreasing(_walk(LENGTH)) is None
    out = c22_stretch_decreasing(_walk(LENGTH + 1, seed=2))
    assert int(out.notna().sum()) == 1
    assert int(out.notna().to_numpy().argmax()) == LENGTH


# ------------------------------------------------------------- guards, edge
@pytest.mark.parametrize("length", [None, 0, -5, 1, 0.5, 1.9])
def test_a_length_below_the_minimum_falls_back_to_the_default(length):
    out = c22_stretch_decreasing(_walk(400, seed=31), length=length)
    assert out.name == "C22STRETCHDEC_100"


def test_min_length_two_is_informative_not_a_forced_constant():
    """Unlike `ts_strike_20`'s length=2 (a forced constant 1), a 2-return
    window here has one diff whose sign depends on the data, so both 0 and
    1 are reachable."""
    assert float(c22_stretch_decreasing(
        _closes_from_returns([1.0, 2.0]), length=2).iloc[2]) == 0.0
    assert float(c22_stretch_decreasing(
        _closes_from_returns([2.0, 1.0]), length=2).iloc[2]) == 1.0


def test_fractional_lengths_that_truncate_the_same_are_identical():
    close = _walk(400, seed=31)
    pd.testing.assert_series_equal(c22_stretch_decreasing(close, length=50.9),
                                   c22_stretch_decreasing(close, length=50))


def test_distinct_lengths_produce_distinct_names_and_values():
    close = _walk(400, seed=31)
    a, b = (c22_stretch_decreasing(close, length=10),
            c22_stretch_decreasing(close, length=60))
    assert (a.name, b.name) == ("C22STRETCHDEC_10", "C22STRETCHDEC_60")


def test_the_offset_and_the_fill_are_the_house_ones():
    s = c22_stretch_decreasing(FRAMES["walk"], offset=2)
    assert same(s.to_numpy()[2:], base("walk").to_numpy()[:-2])
    s = c22_stretch_decreasing(FRAMES["walk"], fillna=-99)
    assert int(s.isna().sum()) == 0
    assert int((s == -99).sum()) == LENGTH


@pytest.mark.parametrize("bad", [np.nan, 0.0, -5.0, np.inf, 1e-310])
def test_a_bad_close_empties_its_own_windows_and_nothing_earlier(bad):
    close = _walk(400, seed=21)
    base_out = c22_stretch_decreasing(close)
    holed = close.copy()
    holed.iloc[200] = bad
    out = c22_stretch_decreasing(holed)
    emptied = np.flatnonzero((base_out.notna() & out.isna()).to_numpy())
    assert len(emptied) == LENGTH + 1
    assert (int(emptied.min()), int(emptied.max())) == (200, 300)
    before = base_out.notna() & out.notna() & (base_out != out)
    assert int(before.iloc[:200].sum()) == 0


def test_an_overflowing_return_pair_is_emptied():
    close = _walk(400, seed=31)
    base_out = c22_stretch_decreasing(close)
    pair = close.copy()
    pair.iloc[200] = 1e-300
    pair.iloc[201] = 1e50
    out = c22_stretch_decreasing(pair)
    emptied = np.flatnonzero((base_out.notna() & out.isna()).to_numpy())
    assert len(emptied) == LENGTH
    assert (int(emptied.min()), int(emptied.max())) == (201, 300)


# ------------------------------------------------------------- wiring
def test_name_registration_and_accessor():
    close = _walk(300, seed=17)
    df = pd.DataFrame({"open": close, "high": close * 1.01,
                       "low": close * 0.99, "close": close,
                       "volume": Series(np.full(len(close), 1000.0))})
    assert "c22_stretch_decreasing" in ta.Category["statistics"]
    assert hasattr(df.ta, "c22_stretch_decreasing")
    direct = c22_stretch_decreasing(close)
    through = df.ta.c22_stretch_decreasing()
    pd.testing.assert_series_equal(through, direct, check_names=True)
    assert through.name == "C22STRETCHDEC_100"
    assert direct.category == "statistics"


def test_the_dictionary_row_describes_this_column():
    import pathlib
    root = pathlib.Path(_REAL.__file__).resolve().parent.parent.parent
    text = (root / "docs" / "IndicatorDictionary.md").read_text(
        encoding="utf-8")
    assert "C22STRETCHDEC_100" in text
    lines = [ln for ln in text.splitlines() if "c22_stretch_decreasing" in ln]
    assert lines, "no row for c22_stretch_decreasing in the dictionary"
    assert "falling" in lines[0].lower()
