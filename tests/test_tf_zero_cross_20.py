# -*- coding: utf-8 -*-
"""TF-ZERO-CROSS-20: `tf_zero_cross_20`, the number of sign changes among
the last 20 daily returns (PandasTa issue #113, TSFEL's `zero_cross`,
BSD-3-Clause).

    r[t]         = close[t] / close[t-1] - 1
    s[t]         = sign(r[t])                      # -1, 0 or +1
    TFZEROCROSS  = #{ j in T-18..T : s[j] != s[j-1] }

What this file pins, in order of how much it would hurt to lose:

1. **THE OVERLAP WITH `LEAN_MOMERSION_20`, which this fork already
   ships.** Momersion counts the same sign agreements over `length`
   PAIRS and reports the share that agree, so on a window with no
   flat bar it is exactly `100 * (20 - this count) / 20` at `length`
   21. `test_it_is_an_affine_restatement_of_momersion_at_length_21`
   asserts that identity on every shared bar of the seven continuous
   frames, and `test_the_default_window_still_overlaps_momersion`
   asserts |Spearman| >= 0.90 at the shipped default (measured band
   -0.9655 .. -0.9795 on those seven). Both are pinned so the
   disclosure in the docstrings cannot quietly go out of date -- it
   is the one fact that decides whether this column should be in a
   feature set at all, and the 2026-10-24 screen behind the issue
   could not see it (`lean_momersion_20` landed 2026-11-11, eighteen
   days later).
   ⚠ The call is NOT settled by Gate E, whose 687 comparators are
   the engine's and not this fork's, so
   `test_the_overlap_measurement_is_still_owed_from_the_gate_e_run`
   asserts that `docs/TfZeroCross20Measured.md` still carries the
   owed item and its revert rule. Without that, recording a green
   Gate E row would turn the disclosure into decoration.

2. **Gate A, the quantity spelled three ways -- and the ONE place
   this port is not the prototype.** The screen prototype (the
   expression Gate E's 0.3498 was measured on) is EXACTLY equal, not
   equal to a tolerance, on every bar both define: the arithmetic is
   an integer count, so a tolerance would hide a real difference. A
   window-by-window Python retype of TSFEL's own line agrees the
   same way. They part only where the prototype counts a MISSING
   return's comparisons as sign changes -- `np.sign(NaN)` is NaN and
   `NaN != 0` is True -- which this port reports as a gap.
   ⚠ The source itself is NOT readable here.
   `test_the_source_library_is_not_readable_here` asserts that, so
   the limitation fails loudly if the environment ever changes.

3. **The sign is THREE-valued, which is the whole column on a tick
   grid.** A return of exactly 0.0 is its own sign, so a lone flat
   bar between two rises counts two changes. The two-valued reading
   is a different column wherever closes repeat, and is asserted to
   be so on a coarse grid and asserted IDENTICAL on a continuous
   frame -- the pair is what stops the choice drifting.

4. **Gate B: five mutants, and the one the sweep cannot see.** All
   five are read off disk, edited and `exec`'d in memory. Four --
   tomorrow's return, a sign series rolled one bar forward, a window
   CENTRED on the current bar (the `bos` failure mode) and a value
   written one bar early -- are live and caught at every swept
   offset. The fifth back-dates the GAP MASK; a back-dated gap does
   not depend on any future value, so the sweep is blind to it by
   construction and it is caught by planting one NaN close.
   ⚠ An offset whose PREVIOUS return is flat is dropped from every
   sweep (`_offsets`), because there the two futures agree whatever
   a one-bar reader does -- with those offsets in, a mutant that
   does read ahead came back caught on only 6 of 8 of the 0.5-grid
   frame. `test_the_deterministic_futures_catch_a_wide_reader_at_a_dropped_offset`
   pins what the dropped offsets can and cannot show, so the filter
   cannot grow into a way of hiding a failure.

5. **Gate D, and the anti-vacuity check that does NOT work here.**
   An exact binary rescale is bit-identical, and so is an INEXACT
   one, because only the sign of a price ratio reaches the output.
   For the same reason a level SHIFT does not move the column
   either, so "a shift moves it" cannot stand in for "the column is
   not constant" -- that is asserted directly instead, as a distinct
   value count, and `0 < fires < n` separately.

6. **The warm-up, the bounds and the centre.** The first value is at
   bar `length`, not `length - 1`: `length` returns need `length + 1`
   closes. The value is an integer on 0 .. `length - 1`, both ends
   reached by construction, and the centre for independent
   continuous returns is `(length - 1) / 2` = 9.5 -- asserted as a
   band, because a consumer who reads 0 as neutral has it backwards.

7. **What it reads, and what it throws away.** Blind to the size and
   the sign of the returns and to a monotone map of the price; NOT
   blind to a constant drift. Blind to a time REVERSAL, which is
   asserted exactly, because a reader who assumes a window statistic
   sees direction would be wrong.

8. **Gate E is owed.**
   `test_the_gate_e_row_is_owed_and_not_yet_recorded` asserts
   `docs/gate_e_ledger.csv` carries no row for this indicator, which
   is the state this commit ships in and the receipt session's cue.

Every number quoted here is printed by
`python docs/measure_tf_zero_cross_20.py` -- EXCEPT Gate E's 0.3498,
which is the 2026-10-24 screen's, and its 687 comparators and 89
frames, which are `CLAUDE.md`'s gate table; the 2026-10-24 date,
which is the screen run id `screen_r2_20261024`'s; the 2026-11-11
date and commit `2213dc9`, read from `git log`; and the "6 of 8"
above, which is §B5's 6 usable offsets caught 6/6 plus its 2 dropped
ones caught 0/2 by a one-bar reader, not a figure the script prints
in that form.
`docs/TfZeroCross20Measured.md` carries the tables. The two CPU
dispatches print the SAME digest
(`108bc7c39deb6b45b9c9115d98df5bbf2e7716a5`, §F2), so no figure in
this file is a figure about one machine's kernels.
"""
import csv
import importlib
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from numpy.lib.stride_tricks import sliding_window_view
from pandas import DataFrame, Series, date_range

from .context import pandas_ta  # noqa: F401

import pandas_ta as ta
from pandas_ta.momentum.lean_momersion_20 import lean_momersion_20
from pandas_ta.statistics.tf_zero_cross_20 import MIN_LENGTH, tf_zero_cross_20

N = 400
LEVEL = 100.0
LENGTH = 20
ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "pandas_ta" / "statistics" / "tf_zero_cross_20.py"


# ------------------------------------------------------------------ frames
# The builders and seeds of `docs/measure_tf_zero_cross_20.py`, shortened
# from 1,500 bars to 400 so the module stays fast -- except `_ramp`, which is
# 200 bars in both. A count quoted from that script is therefore a count
# about 1,500-bar frames; nothing here asserts one of them.

def _series(close):
    return Series(close, index=date_range("2020-01-01", periods=close.size,
                                          freq="h"))


def _walk(seed=7, n=N, level=LEVEL, sigma=0.01):
    rng = np.random.default_rng(seed)
    return _series(level * np.exp(np.cumsum(rng.normal(0.0, sigma, n))))


def _trend(seed=11, n=N, level=LEVEL):
    rng = np.random.default_rng(seed)
    return _series(level * np.exp(np.cumsum(rng.normal(0.003, 0.008, n))))


def _range_bound(seed=13, n=N, level=LEVEL):
    rng = np.random.default_rng(seed)
    x = np.zeros(n)
    for i in range(1, n):
        x[i] = 0.9 * x[i - 1] + rng.normal(0.0, 0.02)
    return _series(level * np.exp(x))


def _grid(seed=17, n=N, level=LEVEL, tick=0.01):
    return np.round(_walk(seed, n, level) / tick) * tick


def _coarse(seed=17, n=N, level=LEVEL, tick=0.5):
    return _grid(seed, n, level, tick)


def _heavy(seed=19, n=N, level=LEVEL):
    rng = np.random.default_rng(seed)
    return _series(level * np.exp(np.cumsum(rng.standard_t(2.0, n) * 0.006)))


def _jump(seed=23, n=N, level=LEVEL):
    c = _walk(seed, n, level)
    return c * Series(np.where(np.arange(n) >= n // 2, 1.5, 1.0), index=c.index)


def _from_returns(r, level=LEVEL):
    return _series(level * np.cumprod(1.0 + np.asarray(r, dtype=float)))


def _persistent(seed=29, n=N, level=LEVEL, phi=0.6, sigma=0.01):
    rng = np.random.default_rng(seed)
    r = np.zeros(n)
    for i in range(1, n):
        r[i] = phi * r[i - 1] + rng.normal(0.0, sigma)
    return _from_returns(r, level)


def _mean_reverting(seed=31, n=N, level=LEVEL, phi=-0.6, sigma=0.01):
    return _persistent(seed, n, level, phi, sigma)


def _flat(n=N, level=LEVEL):
    return _series(np.full(n, level))


def _ramp(n=200, level=LEVEL, step=2.0):
    return _series(level * step ** np.arange(n))


def _alternating(n=N, level=LEVEL, size=0.01):
    return _from_returns(size * (-1.0) ** np.arange(n), level)


FRAMES = {
    "walk": _walk, "trend": _trend, "range-bound": _range_bound,
    "grid": _grid, "coarse-grid": _coarse, "heavy-tailed": _heavy,
    "jump": _jump, "persistent": _persistent,
    "mean-reverting": _mean_reverting, "flat": _flat, "ramp": _ramp,
    "alternating": _alternating,
}
#: The frames whose column is not a constant: a mutant or a perturbation
#: cannot be caught on a frame whose every window reads the same number.
VARIED = [k for k in FRAMES if k not in ("flat", "ramp", "alternating")]
#: The frames with no exactly-equal pair of consecutive closes, where the
#: sign of every return is +1 or -1.
CONTINUOUS = ["walk", "trend", "range-bound", "heavy-tailed", "jump",
              "persistent", "mean-reverting"]


# ----------------------------------------------------------------- helpers

def _bit_equal(a, b):
    if not bool((a.isna() == b.isna()).all()):
        return False
    m = a.notna()
    return bool((a[m] == b[m]).all())


def _differs(a, b):
    one = int((a.isna() != b.isna()).sum())
    m = a.notna() & b.notna()
    return one + int((a[m] != b[m]).sum())


def _both(a, b):
    return int((a.notna() & b.notna()).sum())


def _spearman(a, b):
    m = a.notna() & b.notna()
    return float(a[m].corr(b[m], method="spearman"))


def _returns(close):
    """The prototype's `ret(c) = c / c.shift(1) - 1`."""
    return (close / close.shift(1) - 1.0).to_numpy(dtype=float)


def _place(close, length, vals):
    out = np.full(close.size, np.nan)
    out[length - 1:] = vals
    return Series(out, index=close.index)


# ----------------------------------------------------------------- oracles

def _prototype(close, length=LENGTH):
    """`docs/issues/screen/ind_screen_r2.py:216-217`, retyped:

        roll(ret(c), 20,
             lambda W: (np.diff(np.sign(W), axis=1) != 0)
             .sum(1).astype(float))
    """
    r = _returns(close)
    W = sliding_window_view(r, length)
    vals = (np.diff(np.sign(W), axis=1) != 0).sum(1).astype(float)
    return _place(close, length, vals)


def _window_oracle(close, length=LENGTH):
    """TSFEL's line applied to one window at a time, in a Python loop that
    shares no code with the module, with this port's gap rule."""
    r = _returns(close)
    out = np.full(close.size, np.nan)
    for t in range(length, r.size):
        w = r[t - length + 1:t + 1]
        if np.isfinite(w).all():
            out[t] = len(np.where(np.diff(np.sign(w)))[0])
    return Series(out, index=close.index)


def _two_valued(close, length=LENGTH):
    """The reading NOT taken: a flat return counts as positive."""
    r = _returns(close)
    out = np.full(close.size, np.nan)
    W = sliding_window_view(r, length)
    S = np.where(W < 0.0, -1.0, 1.0)
    fin = np.isfinite(W).all(axis=1)
    out[length - 1:] = np.where(fin, (np.diff(S, axis=1) != 0).sum(1), np.nan)
    out[length - 1] = np.nan
    return Series(out, index=close.index)


# ----------------------------------------------------------------- mutants

RETURN_LINE = \
    "    r = close.pct_change(fill_method=None).to_numpy(dtype=float)"
SIGN_LINE = "    sign = np.sign(np.where(finite, r, 0.0))"
WRITE_LINE = \
    "    out[length:] = np.where(n_finite == length, count, np.nan)"

LOOKAHEAD_MUTANTS = {
    "tomorrow": (RETURN_LINE, RETURN_LINE.replace(
        "    r = ", "    r = np.roll(").replace(
        "(dtype=float)", "(dtype=float), -1)")),
    "sign rolled": (SIGN_LINE,
                    "    sign = np.roll(np.sign(np.where(finite, r, 0.0)), -1)"),
    "centred": (SIGN_LINE,
                "    sign = np.roll(np.sign(np.where(finite, r, 0.0)),"
                " -(length // 2))"),
    "early write": (WRITE_LINE, WRITE_LINE.replace("out[length:]",
                                                   "out[length - 1:-1]")),
}
MASK_MUTANT = (WRITE_LINE, WRITE_LINE.replace(
    "n_finite == length", "np.roll(n_finite == length, -1)"))


def _mutant(old, new):
    src = SOURCE.read_text(encoding="utf-8")
    assert src.count(old) == 1, \
        f"{old!r} occurs {src.count(old)} times in {SOURCE.name}"
    ns = {}
    exec(compile(src.replace(old, new), "<mutant>", "exec"), ns)
    return ns["tf_zero_cross_20"]


def _futures(close, j, size=0.03):
    """Two closes that agree BIT FOR BIT below bar `j` and whose return AT
    `j` has the OPPOSITE SIGN: A rises every bar, B alternates starting down.
    (Only the return at `j` is guaranteed opposite; from `j + 1` on A is
    always up and B alternates, so some later bars share a sign.)

    That one guaranteed flip makes the pair `(r[j-1], r[j])` a change in
    exactly one of the two futures, so a reader of bar `j` must separate
    them -- unless `r[j-1]` is itself FLAT, in which case the pair is a
    change in BOTH and the offset proves nothing. `_offsets` drops those: on
    the 400-bar 0.5-grid frame two of the eight are flat, and with them in
    the sweep a mutant that does read ahead came back caught on only 6 of 8.
    §B5 of `docs/measure_tf_zero_cross_20.py` measures both halves of that
    -- at a usable offset the fork's usual random futures catch exactly what
    these do, and at a dropped one neither catches a one-bar reader."""
    a = close.to_numpy(dtype=float).copy()
    b = a.copy()
    base = a[j - 1]
    steps = np.arange(1, a.size - j + 1, dtype=float)
    a[j:] = base * (1.0 + size) ** steps
    b[j:] = base * (1.0 + size * (-1.0) ** steps)
    return Series(a, index=close.index), Series(b, index=close.index)


def _caught_at(fn, close, j):
    a, b = (fn(f).iloc[:j] for f in _futures(close, j))
    return not _bit_equal(a, b)


OFFSETS = [int(round(x)) for x in np.linspace(LENGTH + 5, N - 5, 8)]


def _offsets(close):
    """The swept offsets whose previous return is signed; see `_futures`."""
    r = _returns(close)
    return [j for j in OFFSETS if np.isfinite(r[j - 1]) and r[j - 1] != 0.0]


# ----------------------------- 1. the overlap with an already-shipped column

@pytest.mark.parametrize("name", CONTINUOUS)
def test_it_is_an_affine_restatement_of_momersion_at_length_21(name):
    """With no flat bar in the window every pair is signed, so momersion's
    `100 * MC / (MC + MRC)` is `100 * (20 - MRC) / 20` and MRC is this column
    at `length` 21. This is the disclosure that decides whether the column
    belongs in a feature set at all; if it ever stops holding, the docstrings
    are wrong."""
    c = FRAMES[name]()
    assert not (np.diff(c.to_numpy()) == 0.0).any(), "frame is not continuous"
    count21 = tf_zero_cross_20(c, length=LENGTH + 1)
    momersion = lean_momersion_20(c)
    implied = 100.0 * (LENGTH - count21) / LENGTH
    shared = implied.notna() & momersion.notna()
    assert int(shared.sum()) > 300
    assert np.allclose(implied[shared], momersion[shared], rtol=0, atol=1e-9)
    assert _spearman(count21, momersion) == pytest.approx(-1.0, abs=1e-12)


@pytest.mark.parametrize("name", CONTINUOUS)
def test_the_default_window_still_overlaps_momersion(name):
    """One pair fewer than momersion's window, and still a restatement: the
    measured band over the seven continuous 1,500-bar frames is
    -0.9655 .. -0.9795, so 0.90 is a floor with room, not the measurement.
    (The 0.01-tick `grid` frame, which is not in this list, reads -0.9622.)
    """
    c = FRAMES[name]()
    assert _spearman(tf_zero_cross_20(c), lean_momersion_20(c)) <= -0.90


def test_flat_bars_are_what_separate_it_from_momersion():
    """The overlap decays with the share of exactly-zero returns, which is a
    property of the PRICE GRID. Pinned as an ordering, not as the measured
    -0.9622 / -0.7586, because the ordering is the claim."""
    fine, coarse = _grid(), _coarse()
    fine_zero = float((_returns(fine)[1:] == 0.0).mean())
    coarse_zero = float((_returns(coarse)[1:] == 0.0).mean())
    assert 0.0 < fine_zero < coarse_zero
    fine_rho = _spearman(tf_zero_cross_20(fine), lean_momersion_20(fine))
    coarse_rho = _spearman(tf_zero_cross_20(coarse), lean_momersion_20(coarse))
    assert fine_rho < coarse_rho < 0.0, (fine_rho, coarse_rho)


# ------------------------------------------------------------------ 2. Gate A

@pytest.mark.parametrize("name", list(FRAMES))
def test_gate_a_the_module_equals_the_screen_prototype_exactly(name):
    c = FRAMES[name]()
    mod, pro = tf_zero_cross_20(c), _prototype(c)
    shared = mod.notna() & pro.notna()
    assert int(shared.sum()) == int(mod.notna().sum()) > 0
    # EXACT equality: the arithmetic is an integer count, so a tolerance
    # would hide a real difference rather than absorb a rounding one.
    assert bool((mod[shared] == pro[shared]).all())


@pytest.mark.parametrize("name", list(FRAMES))
def test_gate_a_the_only_divergence_is_the_window_holding_a_bad_return(name):
    """The prototype reads every window this module reads, and exactly one
    more per frame here: the window at `length - 1`, which holds `r[0]`."""
    c = FRAMES[name]()
    mod, pro = tf_zero_cross_20(c), _prototype(c)
    only_module = int((mod.notna() & pro.isna()).sum())
    only_proto = [int(i) for i in
                  np.flatnonzero((pro.notna() & mod.isna()).to_numpy())]
    assert only_module == 0
    assert only_proto == [LENGTH - 1]


@pytest.mark.parametrize("length", [MIN_LENGTH, 5, LENGTH, 60, 250])
def test_gate_a_the_prototype_agreement_holds_at_every_length(length):
    for name in ("walk", "grid", "heavy-tailed"):
        c = FRAMES[name]()
        mod, pro = (tf_zero_cross_20(c, length=length),
                    _prototype(c, length=length))
        shared = mod.notna() & pro.notna()
        assert int(shared.sum()) == len(c) - length
        assert bool((mod[shared] == pro[shared]).all())


@pytest.mark.parametrize("name", list(FRAMES))
def test_gate_a_the_source_line_window_by_window_agrees(name):
    """TSFEL's `len(np.where(np.diff(np.sign(w)))[0])`, one window at a time
    in a Python loop sharing no code with the module."""
    c = FRAMES[name]()
    mod, orc = tf_zero_cross_20(c), _window_oracle(c)
    assert _bit_equal(mod, orc)


def test_gate_a_the_window_is_the_last_length_returns_and_no_other():
    """Spelled out once at a size small enough to read: the value at bar T is
    a function of exactly the returns T - length + 1 .. T."""
    c = _walk()
    r = _returns(c)
    v = tf_zero_cross_20(c, length=4)
    for t in (10, 11, 250, 399):
        w = r[t - 3:t + 1]
        assert v.iloc[t] == float((np.diff(np.sign(w)) != 0).sum())


def test_the_source_library_is_not_readable_here():
    """Gate A reads the issue's one line, not TSFEL. If that ever stops being
    true, this test fails and the caveat in the docstrings must come out."""
    with pytest.raises(ImportError):
        importlib.import_module("tsfel")
    assert not list((ROOT / "docs").glob("*tsfel*"))


# --------------------------------------------------- 3. the three-valued sign

def test_a_flat_bar_is_its_own_sign_and_costs_two_changes():
    """Closes 100, 101, 101, 102 ...: the pairs (+, 0) and (0, +) are each a
    change, so one unchanged close adds two."""
    c = _series(np.array([100.0, 101.0, 101.0] + list(102.0 + np.arange(5))))
    v = tf_zero_cross_20(c, length=MIN_LENGTH)
    assert list(v.to_numpy()[2:4]) == [1.0, 1.0]
    assert list(v.to_numpy()[4:]) == [0.0, 0.0, 0.0, 0.0]


@pytest.mark.parametrize("name", CONTINUOUS)
def test_the_two_valued_reading_is_invisible_on_a_continuous_frame(name):
    c = FRAMES[name]()
    assert not (_returns(c)[1:] == 0.0).any()
    assert _bit_equal(tf_zero_cross_20(c), _two_valued(c))


def test_the_two_valued_reading_is_a_different_column_on_a_grid():
    """Which is why the choice is stated rather than assumed."""
    c = _coarse()
    assert (_returns(c)[1:] == 0.0).mean() > 0.10
    mod, two = tf_zero_cross_20(c), _two_valued(c)
    shared = mod.notna() & two.notna()
    assert int((mod[shared] != two[shared]).sum()) > 0.5 * int(shared.sum())
    assert float((mod[shared] - two[shared]).abs().max()) >= 2.0


# ------------------------------------------------------------------ 4. Gate B

@pytest.mark.parametrize("name", VARIED)
def test_the_module_reads_no_future_bar(name):
    c = FRAMES[name]()
    assert sum(_caught_at(tf_zero_cross_20, c, j) for j in _offsets(c)) == 0


@pytest.mark.parametrize("name", list(FRAMES))
def test_prefix_truncation_leaves_the_column_unchanged(name):
    c = FRAMES[name]()
    full = tf_zero_cross_20(c)
    for j in [j for j in OFFSETS if j < c.size]:
        assert _bit_equal(full.iloc[:j], tf_zero_cross_20(c.iloc[:j]))


@pytest.mark.parametrize("label", list(LOOKAHEAD_MUTANTS))
@pytest.mark.parametrize("name", VARIED)
def test_a_look_ahead_mutant_is_live_and_caught_at_every_offset(label, name):
    fn = _mutant(*LOOKAHEAD_MUTANTS[label])
    c = FRAMES[name]()
    offsets = _offsets(c)
    assert len(offsets) >= 6
    assert not _bit_equal(fn(c), tf_zero_cross_20(c)), "mutant is not live"
    assert sum(_caught_at(fn, c, j) for j in offsets) == len(offsets)


@pytest.mark.parametrize("name", VARIED[:3])
def test_the_mask_mutant_is_live_nowhere_and_the_blind_sweep_misses_it(name):
    """A back-dated GAP MASK depends on no future VALUE, so on a frame with
    no gap it is not even live. This is the limit of the sweep, asserted so
    the next reader does not take 0-of-8 for proof."""
    fn = _mutant(*MASK_MUTANT)
    c = FRAMES[name]()
    assert _bit_equal(fn(c), tf_zero_cross_20(c))
    assert sum(_caught_at(fn, c, j) for j in _offsets(c)) == 0


def test_the_deterministic_futures_catch_a_wide_reader_at_a_dropped_offset():
    """The offsets `_offsets` drops are dropped because a ONE-bar reader is
    invisible there: with `r[j-1]` flat the pair is a change in both futures
    whatever `r[j]` does. A mutant that reads `length // 2` bars ahead is
    not, and the deterministic futures catch it there where the fork's
    seeded random pair does not (§B5). Swept here so that difference is
    exercised by the suite and not only by the measure script."""
    c = _coarse()
    r = _returns(c)
    dropped = [j for j in OFFSETS if np.isfinite(r[j - 1]) and r[j - 1] == 0.0]
    assert dropped, "the coarse grid no longer has a flat offset to sweep"
    centred = _mutant(*LOOKAHEAD_MUTANTS["centred"])
    one_bar = _mutant(*LOOKAHEAD_MUTANTS["tomorrow"])
    assert all(_caught_at(centred, c, j) for j in dropped)
    assert not any(_caught_at(one_bar, c, j) for j in dropped)
    assert sum(_caught_at(tf_zero_cross_20, c, j) for j in dropped) == 0


@pytest.mark.parametrize("at", [100, 200, 300])
def test_a_mutant_that_back_dates_the_gap_mask_is_caught_by_a_planted_nan(at):
    fn = _mutant(*MASK_MUTANT)
    c = _walk()
    c.iloc[at] = np.nan
    real = tf_zero_cross_20(c).isna().to_numpy()
    mutated = fn(c).isna().to_numpy()
    first_real = min(i for i in np.flatnonzero(real) if i >= LENGTH)
    first_mut = min(i for i in np.flatnonzero(mutated) if i >= LENGTH)
    assert first_real == at
    assert first_mut == at - 1


@pytest.mark.parametrize("at", [100, 300])
@pytest.mark.parametrize("factor", [1.5, 1.0 / 1.5])
def test_one_changed_close_moves_only_the_windows_that_hold_it(at, factor):
    """A close enters the returns at `at` and `at + 1`, so nothing outside
    `at .. at + length` may move -- the check a prefix sum has to pass, since
    its totals run the length of the frame."""
    c = _walk()
    base = tf_zero_cross_20(c)
    d = c.copy()
    d.iloc[at] = d.iloc[at] * factor
    moved = np.flatnonzero((base != tf_zero_cross_20(d)).to_numpy()
                           & base.notna().to_numpy())
    assert all(at <= int(i) <= at + LENGTH for i in moved), moved


# ------------------------------------------------------------------ 5. Gate D

@pytest.mark.parametrize("name", list(FRAMES))
@pytest.mark.parametrize("factor", [8.0, 64.0, 2.0 ** -40, 2.0 ** 40,
                                    2.0 ** 100])
def test_scale_an_exact_binary_factor_is_bit_identical(name, factor):
    c = FRAMES[name]()
    assert _bit_equal(tf_zero_cross_20(c), tf_zero_cross_20(c * factor))


@pytest.mark.parametrize("length", [MIN_LENGTH, 5, LENGTH, 60, 250])
def test_scale_by_eight_is_bit_identical_at_every_length(length):
    c = _walk()
    assert _bit_equal(tf_zero_cross_20(c, length=length),
                      tf_zero_cross_20(c * 8.0, length=length))


@pytest.mark.parametrize("name", list(FRAMES))
@pytest.mark.parametrize("factor", [10.0, 3.7, 0.1, 1.0000001])
def test_scale_an_inexact_factor_is_bit_identical_too(name, factor):
    """Stronger than the gate asks for, and it holds because only the SIGN of
    a price ratio reaches the output. A sign could still flip for a return
    within an ulp of zero, which is why this is a measurement."""
    c = FRAMES[name]()
    assert _bit_equal(tf_zero_cross_20(c), tf_zero_cross_20(c * factor))


@pytest.mark.parametrize("name", ["walk", "grid", "heavy-tailed"])
@pytest.mark.parametrize("power", [2.0, 0.5, -1.0])
def test_scale_a_monotone_power_map_of_the_price_changes_nothing(name, power):
    """`p ** a` keeps the order of two closes for a > 0 and reverses all of
    it for a < 0, and reversing every sign leaves every DISAGREEMENT a
    disagreement."""
    c = FRAMES[name]()
    assert _bit_equal(tf_zero_cross_20(c), tf_zero_cross_20(c ** power))


@pytest.mark.parametrize("shift", [10.0, 100.0])
def test_scale_a_level_shift_does_not_move_it_either(shift):
    """⚠ The usual anti-vacuity check does NOT work on this column, and that
    is a property: `c + k > c' + k` exactly when `c > c'`. Asserted so a
    reader does not add the usual 'a shift must move it' test and call the
    column broken when it fails."""
    c = _walk()
    assert _bit_equal(tf_zero_cross_20(c), tf_zero_cross_20(c + shift))


def test_a_shift_that_straddles_zero_does_move_it():
    """The one shift that can: with the two closes of a pair on opposite
    sides of zero the ratio's order flips. Taking EVERY close negative does
    not, because then every sign flips at once."""
    c = _walk()
    straddling = c - (float(c.min()) + 1.0)
    all_negative = c - (float(c.max()) + 1.0)
    assert float(straddling.min()) < 0.0 < float(straddling.max())
    assert float(all_negative.max()) < 0.0
    assert _differs(tf_zero_cross_20(c), tf_zero_cross_20(straddling)) > 0
    assert _bit_equal(tf_zero_cross_20(c), tf_zero_cross_20(all_negative))


@pytest.mark.parametrize("name", list(FRAMES))
def test_scale_fires_strictly_between_zero_and_n(name):
    c = FRAMES[name]()
    v = tf_zero_cross_20(c)
    assert 0 < int(v.notna().sum()) < len(v)


@pytest.mark.parametrize("name", VARIED)
def test_the_column_is_not_constant(name):
    """What makes the bit-identity above non-vacuous, since a level shift
    cannot be used for it here. The measured span on the 1,500-bar frames is
    13 to 15 distinct values; 5 is a floor with room."""
    assert int(tf_zero_cross_20(FRAMES[name]()).dropna().nunique()) >= 5


# -------------------------------------- 6. the warm-up, the bounds, the centre

@pytest.mark.parametrize("name", list(FRAMES))
def test_the_warm_up_is_length_bars_and_the_value_is_a_count(name):
    c = FRAMES[name]()
    v = tf_zero_cross_20(c)
    assert int(np.flatnonzero(v.notna().to_numpy())[0]) == LENGTH
    assert bool(v.iloc[:LENGTH].isna().all())
    fired = v.dropna().to_numpy()
    assert bool((fired == np.round(fired)).all())
    assert 0 <= fired.min() and fired.max() <= LENGTH - 1


def test_both_ends_of_the_range_are_reached_by_construction():
    assert tf_zero_cross_20(_alternating()).dropna().eq(LENGTH - 1).all()
    assert tf_zero_cross_20(_ramp()).dropna().eq(0.0).all()
    assert tf_zero_cross_20(_flat()).dropna().eq(0.0).all()


def test_the_centre_for_independent_returns_is_half_the_pairs():
    """A sign change between two independent continuous returns has
    probability 1/2, so 19 pairs centre on 9.5 -- NOT on 0.

    §A5 measures 4,000 disjoint windows at mean 9.5077, sd 2.1991. This
    redraws 2,000 of its own and asserts only the centre, to +-0.15, and
    that the draw spans both sides of it: the sd is a property of the draw
    and pinning it here would pin the RNG rather than the column."""
    rng = np.random.default_rng(4242)
    draws = 2000
    W = rng.normal(0.0, 0.01, draws * LENGTH).reshape(draws, LENGTH)
    counts = (np.diff(np.sign(W), axis=1) != 0).sum(1)
    assert counts.mean() == pytest.approx((LENGTH - 1) / 2, abs=0.15)
    assert counts.min() < 6 and counts.max() > 13


def test_the_count_orders_persistence():
    """The ordering the column exists for: alternating returns read above a
    walk, which reads above trending ones."""
    median = {name: float(tf_zero_cross_20(FRAMES[name]()).median())
              for name in ("mean-reverting", "walk", "persistent")}
    assert median["mean-reverting"] > median["walk"] > median["persistent"]


# --------------------------------------------- 7. what it reads and discards

@pytest.mark.parametrize("factor", [0.5, 2.0, -1.0, 1e-6])
def test_it_is_blind_to_the_size_and_the_sign_of_the_returns(factor):
    r = _returns(_walk())[1:]
    assert _bit_equal(tf_zero_cross_20(_from_returns(r)),
                      tf_zero_cross_20(_from_returns(r * factor)))


def test_it_is_not_blind_to_a_constant_drift():
    """Drift makes one sign likelier, so it removes changes."""
    r = _returns(_walk())[1:]
    base = tf_zero_cross_20(_from_returns(r)).mean()
    drifted = tf_zero_cross_20(_from_returns(r + 0.01)).mean()
    assert drifted < base - 1.0


def test_it_is_blind_to_a_time_reversal_and_not_to_a_permutation():
    """Reversing a window keeps every adjacency, so the count cannot move --
    exactly, on every sampled window. A permutation does not."""
    rng = np.random.default_rng(5150)
    r = _returns(_walk())[1:]
    same_rev = same_perm = 0
    trials = 200
    for _ in range(trials):
        j = int(rng.integers(0, r.size - LENGTH))
        w = r[j:j + LENGTH]
        n_w = int((np.diff(np.sign(w)) != 0).sum())
        same_rev += n_w == int((np.diff(np.sign(w[::-1])) != 0).sum())
        same_perm += n_w == int((np.diff(np.sign(rng.permutation(w))) != 0).sum())
    assert same_rev == trials
    assert same_perm < trials // 2


def test_it_is_a_state_and_not_an_event():
    """Neighbouring windows share 19 of their 20 returns."""
    v = tf_zero_cross_20(_walk()).dropna()
    assert v.autocorr(1) > 0.85
    assert abs(v.autocorr(LENGTH)) < 0.5


# ------------------------------------------------- guards, warm-up, wiring

@pytest.mark.parametrize("value", [np.nan, np.inf, -np.inf, 0.0, 1e-310])
def test_a_bad_close_empties_its_windows_and_moves_nothing_earlier(value):
    at = 200
    c = _walk()
    base = tf_zero_cross_20(c)
    c.iloc[at] = value
    v = tf_zero_cross_20(c)
    gaps = np.flatnonzero(v.isna().to_numpy() & base.notna().to_numpy())
    assert 20 <= len(gaps) <= 21
    assert all(at <= int(i) <= at + LENGTH for i in gaps)
    earlier = (base != v) & base.notna() & v.notna() & (np.arange(len(v)) < at)
    assert int(earlier.sum()) == 0


def test_a_negative_close_is_a_price_and_not_a_gap():
    """Nothing here takes a logarithm, so a negative close has a return and
    is read rather than dropped."""
    c = _walk()
    base = tf_zero_cross_20(c)
    c.iloc[200] = -100.0
    v = tf_zero_cross_20(c)
    assert int(v.notna().sum()) == int(base.notna().sum())
    assert _differs(base, v) > 0


@pytest.mark.parametrize("name", list(FRAMES))
def test_no_floating_point_error_is_reachable(name):
    with np.errstate(all="raise"):
        tf_zero_cross_20(FRAMES[name]())


def test_no_floating_point_error_is_reachable_on_a_broken_frame():
    c = _walk()
    c.iloc[100] = 0.0
    c.iloc[200] = np.nan
    c.iloc[300] = np.inf
    with np.errstate(all="raise"):
        assert int(tf_zero_cross_20(c).notna().sum()) > 0


def test_the_shortest_input_that_produces_a_value():
    assert tf_zero_cross_20(_walk(n=LENGTH)) is None
    assert int(tf_zero_cross_20(_walk(n=LENGTH + 1)).notna().sum()) == 1


def test_the_input_series_is_not_mutated():
    c = _walk()
    before = c.to_numpy().copy()
    tf_zero_cross_20(c)
    assert np.array_equal(before, c.to_numpy())


@pytest.mark.parametrize("length", [None, 0, 1, -5, 1.0])
def test_a_length_below_the_minimum_falls_back_to_the_default(length):
    assert tf_zero_cross_20(_walk(), length=length).name == f"TFZEROCROSS_{LENGTH}"


def test_the_minimum_length_is_honoured():
    v = tf_zero_cross_20(_walk(), length=MIN_LENGTH)
    assert v.name == f"TFZEROCROSS_{MIN_LENGTH}"
    assert set(v.dropna().unique()) <= {0.0, 1.0}


def test_offset_and_fillna():
    c = _walk()
    base = tf_zero_cross_20(c)
    pd.testing.assert_series_equal(tf_zero_cross_20(c, offset=1),
                                   base.shift(1), check_names=False)
    filled = tf_zero_cross_20(c, fillna=-1.0)
    assert int(filled.isna().sum()) == 0
    assert bool((filled.iloc[:LENGTH] == -1.0).all())


def test_a_degenerate_frame_neither_raises_nor_invents_a_value():
    for arr in (np.full(60, np.nan), np.zeros(60), np.full(60, np.inf)):
        v = tf_zero_cross_20(_series(arr))
        assert v is not None
        assert int(v.notna().sum()) == 0


def test_the_five_wiring_touch_points():
    assert ta.tf_zero_cross_20 is tf_zero_cross_20
    assert "tf_zero_cross_20" in ta.Category["statistics"]
    assert hasattr(DataFrame().ta, "tf_zero_cross_20")
    c = _walk()
    df = DataFrame({"close": c.to_numpy()}, index=c.index)
    out = df.ta.tf_zero_cross_20()
    assert out.name == f"TFZEROCROSS_{LENGTH}"
    assert _bit_equal(out, tf_zero_cross_20(c))
    assert df.ta.tf_zero_cross_20(length=5).name == "TFZEROCROSS_5"


def test_the_overlap_warning_survives_the_dictionary_cut():
    """`docs/gen_indicator_dictionary.py` shows the first paragraph after the
    title, squeezed and truncated to 150 characters. The overlap with
    `LEAN_MOMERSION_20` is the one thing a reader of the dictionary must
    see, so it has to fit inside that -- which is a real constraint and not
    a formality: the paragraph has room for one sentence and the warning."""
    import re
    # The limit is read out of the generator, not retyped: if it ever
    # dropped below the paragraph's length the dictionary row would lose
    # the warning silently, which is the one failure this test exists for.
    gen = (ROOT / "docs" / "gen_indicator_dictionary.py").read_text(
        encoding="utf-8")
    limit = int(re.search(r"def desc\(rec, limit=(\d+)\)", gen).group(1))
    first = tf_zero_cross_20.__doc__.split("\n\n")[1].strip()
    cut = re.sub(r"\s+", " ", first).strip()
    if len(cut) > limit:
        cut = cut[:limit].rsplit(" ", 1)[0] + "…"
    assert "LEAN_MOMERSION_20" in cut, cut
    assert "0 .. `length - 1`" in cut, cut


def test_the_gate_e_row_is_owed_and_not_yet_recorded():
    """Gate E is run by issue-solver after this session; the receipt session
    records the row and replaces this test."""
    path = ROOT / "docs" / "gate_e_ledger.csv"
    rows = list(csv.DictReader(path.read_text(encoding="utf-8").splitlines()))
    assert not [r for r in rows if r["indicator"] == "tf_zero_cross_20"]


def test_the_overlap_measurement_is_still_owed_from_the_gate_e_run():
    """The momersion overlap is the one thing Gate E's comparator set cannot
    see, so "the owner's call" needs a trigger or it is never made: the
    receipt session has to measure ρ against `LEAN_MOMERSION_20` on the same
    89 frames and apply the same band. This asserts the owed item and its
    revert rule are still in the receipt, so a green Gate E row cannot be
    recorded without meeting them."""
    doc = (ROOT / "docs" / "TfZeroCross20Measured.md").read_text(
        encoding="utf-8")
    # Each string is unique to the OWED block. "LEAN_MOMERSION_20" and
    # "revert" on their own are not: §L1's table header and its "ship or
    # revert" sentence satisfy both with the block deleted.
    assert "OWED from the Gate E run" in doc
    assert "revert `tf_zero_cross_20` if it is" in doc
    assert "r3-perframe-0.90" in doc
