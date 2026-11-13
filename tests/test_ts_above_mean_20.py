# -*- coding: utf-8 -*-
"""TS-ABOVE-MEAN-20: `ts_above_mean_20`, tsfresh's `count_above_mean` over
20 returns, divided by the window size (PandasTa issue #97).

    TS_ABOVE_MEAN_20 = (how many of a 20-return window's returns are
                        STRICTLY above that window's own mean) / 20

WHAT THIS FILE PINS, in order of how much it would hurt to lose.

1. **Gate A, and that the formula under test is the ISSUE's line plus the
   published `count_above_mean` definition.** tsfresh is NOT installed in
   this worktree and web access is unavailable, so "tsfresh (MIT)" is an
   attribution, not an oracle (`test_tsfresh_is_not_installed_here` records
   that, so the claim cannot rot into "checked against tsfresh"). What IS
   checkable is pinned as BIT-EQUALITY and not as a tolerance, because this
   column is a count and a count is either right or wrong:

   * the source applied window by window, sharing no code with the module --
     bit-equal on **1,480 of 1,480** fired bars of each of nine 1,500-bar
     frames;
   * a `math.fsum` scalar loop -- bit-equal on three of them;
   * an EXACT rational oracle in `fractions.Fraction`, where the window mean
     is a rational and no comparison is rounded at all -- **exact on every
     bar of every frame run**, including a path whose returns have
     `|mean| / sd` = 1e5. The float mean has not flipped one comparison;
   * hand-derived windows, including the two ends of the range.

2. **The range, which is [1/20, 19/20] and NOT [0, 1].** If no return were
   above the mean then all would be at or below it, and the sum forces them
   all EQUAL; symmetrically for all-above. So a window whose returns are not
   all identical always has between 1 and `length - 1` above the mean, and a
   reading of exactly 0.0 or 1.0 means a degenerate window got through.
   Pinned both ways: the module never leaves [0.05, 0.95] on any frame here,
   both ends are attained, and the UNGUARDED spelling does emit the
   impossible 0.0 -- on all 280 body windows of a flat frame.

3. **Gate B, by mutant, and the designed probe that the blind sweep needs.**
   Six mutants, each `importlib`-read and `exec`'d in memory, over three
   mechanisms: the write index back-dated (by 2 bars and by `length - 1`), a
   read index moved into the future (the window, the return, and the mean the
   comparisons are made against), and the FLOOR's own index. The real module
   leaks **0 of 37** offsets of a blind future-perturbation sweep on each of
   three frames and at `length` 5, 60 and 250; the first five are LIVE and
   caught **32-37 of 37**, banded rather than pinned (CI's runner has measured
   different last bits for the same seeds -- commit 22fe27b).
   ⚠ The sixth is the interesting one, and it is where the blind sweep fails.
   Rolling `hi`/`lo` by one window makes bar T's NaN mask read window T+1 --
   a real look-ahead. It IS live on all three frames, moving exactly two
   bars, **[19, 1499]** measured as a set: bar 19 from NaN to **0.0** (the
   value item 2 says this column cannot reach, because `reported` is False at
   exactly that one index), and the LAST bar from a value to NaN, which is a
   `np.roll` WRAP rather than a look-ahead. The blind sweep sees neither --
   bar 19 precedes every offset (they start at 40) and reads 0.0 either way,
   and the last bar follows every offset, while `_caught` only inspects bars
   BEFORE one. So it scores **0 of 37** and proves nothing. A DESIGNED frame
   does: a walk interrupted every 40 bars by 25 bars of exactly-zero returns
   (36 patches x 6 all-zero windows = **216 interior** empties, plus the 20
   warm-up bars). There the real module still leaks 0 of 37 and the mutant is
   caught **36 of 37**.

4. **Gate D, and that it is stronger than x8 on this column.** x8 and x64 are
   bit-identical on 1,480 of 1,480 bars of each of nine frames, which follows
   from the return being a price RATIO. x10, x3.7 and x0.1 are NOT
   bit-identical by construction, yet measured bit-equal anyway, because a
   COUNT moves only when a perturbation reorders a return and its own window
   mean. That is a measurement with a measured margin: over 199,980 windows
   of a 200,000-bar walk the smallest gap `|r - mean| / max|r|` is
   **1.6e-07** against an ulp of 2.2e-16. So the x10/x3.7/x0.1 test asserts
   the NaN masks exactly, the values with a five-bar band, and the margin
   separately -- not a bit-equality it cannot guarantee. The band has never
   been used on this machine.
   ⚠ The affine invariance of the RETURNS belongs to the COUNT and not to the
   reported MASK: the floor is scale-invariant but not shift-invariant, and
   `test_that_invariance_is_the_counts_and_not_the_reported_masks` pins the
   case where a 0.004 drift takes 580 fired bars to 0.

5. **What the column IS, which is the thing most likely to be misread.** It
   is a backwards SKEWNESS reading: a few large gains pull the mean up and
   push the column DOWN. Spearman **-0.81** against the windows' own skewness
   over 20,000 independent windows, and -0.61 / -0.86 / -0.96 against the
   SHIPPED `OSAP_RETSKEW_21` on a walk / a heavy-tailed frame / a two-point
   frame. Those three are SYNTHETIC and are the only measurement of that pair
   that exists: Gate E's 687 comparators hold no pandas_ta port -- the run
   below bears that out from its side, with no `OSAP`, `RETSKEW` or `SKEW`
   column anywhere in its four output files -- and the screen's real-frame
   fork overlap predates `osap_retskew_21` by nine days
   (docs/TsAboveMean20Measured.md §5). It is NOT volatility (-0.07 against
   the window's return sd) and NOT direction (0.07 against its mean return)
   -- except on a two-point frame, where those three are one statistic.

6. **The guards, each with what it costs.** The RELATIVE floor
   (`spread > 4096 eps * max|r|`), which is NOT the siblings' absolute one:
   on a quiet-but-honest frame -- returns of 1e-6 spread over 1e-13, every
   comparison exact -- the relative floor reports on 580 of 600 bars where an
   absolute `4096 eps` reports on none. It costs 0 body bars on each of nine
   clean frames and empties a constant-return ladder entirely, where the
   unguarded spelling reports 280 windows of pure rounding across 12 distinct
   values. The per-return magnitude bound, which keeps the window sum from
   overflowing. And the locality that separates this module from the fork's
   `ts_ac1_60` / `ts_cid_ce_20`: a planted return of 1e+2 .. 1e+300 leaves
   every bar from 220 on BIT-IDENTICAL, because no accumulator crosses a
   window boundary here.

7. **That it IS the screen prototype**, bit-equal on 1,480 of 1,480 shared
   fired bars of each of nine frames, differing only in two NaN rules that
   both go this port's way (the prototype emits the impossible 0.00 at its
   first bar, and it counts through a NaN close).

Numbers come from `docs/measure_ts_above_mean_20.py`; the receipt is
`docs/TsAboveMean20Measured.md`.
Counts that depend on the last bits of a generated frame carry a band or a
tolerance; the structural facts are pinned exactly.

Gate E is MEASURED: run `is97-ts_above_mean_20-5d78f565` (2026-11-13, default
parameters, 89 frames, 687 comparators, canary bit-equal) is **SHIP** --
pooled max |rho| **0.35937568662749647** vs `PVT_Slope_norm` at n = 396,970,
per-frame max median **0.3580864882804631** vs the same comparator over 89
frames, with 0.0% of frames at or above either the 0.90 or the 0.80 line on
any of the top five. `test_the_ledger_row_is_this_modules_gate_e_run` and
`test_the_ledger_row_carries_the_measured_gate_e_numbers` pin that row,
because `tests/test_gate_e_ledger.py` checks a row generically and cannot see
WHICH measurement it came from -- a row copied from the screen's PROTOTYPE
run would satisfy it.

⚠ Gate C in THIS FILE is SYNTHETIC. The real-data counts come from that same
run and are pinned out of the ledger: `TS_ABOVE_MEAN_20` is non-NaN on
**397,069** of 398,849 pooled bars and all 397,069 are non-zero, and the
1,780 NaN bars are exactly 20 x 89 -- the warm-up, so NEITHER the relative
floor, NOR the per-return magnitude bound, NOR the bad-close rule (item 6)
emptied a window on the 89 BIST frames.
"""
import importlib
import math
import types
from fractions import Fraction

import numpy as np
import pandas as pd
import pytest
from numpy.lib.stride_tricks import sliding_window_view
from pandas import Series

from .context import pandas_ta
from pandas_ta.statistics.ts_above_mean_20 import (NOISE_FACTOR,
                                                   ts_above_mean_20)

LENGTH = 20

_REAL = importlib.import_module("pandas_ta.statistics.ts_above_mean_20")


# ------------------------------------------------------------------ frames


def _walk(n=1500, seed=11, sigma=0.015, drift=0.0):
    rng = np.random.default_rng(seed)
    return Series(100.0 * np.exp(np.cumsum(rng.normal(drift, sigma, n))))


def _tick_rounded(n=1500, seed=11):
    return Series(np.round(_walk(n, seed).to_numpy(), 2))


def _from_returns(r):
    return Series(100.0 * np.cumprod(1.0 + np.asarray(r, dtype=float)))


def _window_frame(rs):
    """`len(rs) + 1` closes whose returns are `rs`."""
    body = np.cumprod(1.0 + np.asarray(rs, dtype=float))
    return Series(100.0 * np.concatenate([[1.0], body]))


def _ar1(n=1500, seed=7, sigma=0.015, phi=0.5):
    rng = np.random.default_rng(seed)
    e = rng.normal(0.0, sigma, n)
    x = np.zeros(n)
    for t in range(1, n):
        x[t] = phi * x[t - 1] + e[t]
    return _from_returns(np.clip(x, -0.5, 0.5))


def _heavy_tailed(n=1500, seed=3, df=2.0, sigma=0.01):
    rng = np.random.default_rng(seed)
    return _from_returns(np.clip(sigma * rng.standard_t(df, n), -0.5, 0.5))


def _right_skewed(n=1500, seed=5, sigma=0.01):
    rng = np.random.default_rng(seed)
    return _from_returns(np.clip(sigma * (rng.standard_exponential(n) - 1.0),
                                 -0.5, 0.5))


def _left_skewed(n=1500, seed=5, sigma=0.01):
    rng = np.random.default_rng(seed)
    return _from_returns(np.clip(sigma * (1.0 - rng.standard_exponential(n)),
                                 -0.5, 0.5))


def _two_point(n=1500, seed=4, sigma=0.01):
    rng = np.random.default_rng(seed)
    return _from_returns(np.where(rng.random(n) < 0.5, sigma, -sigma))


def _trending(n=1500, seed=9):
    return _walk(n, seed, sigma=0.004, drift=0.01)


def _flat(n=300, price=100.0):
    return Series(np.full(n, price))


def _ladder(n=300, price=100.0, rate=0.01):
    """A mathematically CONSTANT return, which float64 reproduces only to
    rounding."""
    return Series(price * (1.0 + rate) ** np.arange(n, dtype=float))


def _floored_patches(n=1500, seed=23, sigma=0.015, patch=25, every=40):
    """A walk interrupted every `every` bars by a `patch`-bar stretch of
    EXACTLY zero returns. On the nine frames above the floor is active only
    at the warm-up bar, which is why a mutant on the floor's own index moves
    nothing the sweep can inspect; here it is active on interior windows and
    the sweep bites. Built for `test_the_designed_probe_catches_the_floor_...`
    and used nowhere else."""
    rng = np.random.default_rng(seed)
    r = rng.normal(0.0, sigma, n)
    for start in range(60, n - patch, every):
        r[start:start + patch] = 0.0
    return _from_returns(r)


FRAMES = {
    "walk": _walk,
    "tick-rounded": _tick_rounded,
    "ar1+": lambda: _ar1(phi=0.5),
    "ar1-": lambda: _ar1(phi=-0.5, seed=17),
    "heavy-tailed": _heavy_tailed,
    "right-skewed": _right_skewed,
    "left-skewed": _left_skewed,
    "two-point": _two_point,
    "trending": _trending,
}
#: Every frame is 1,500 bars and the first value lands at bar `length`.
FIRED = 1500 - LENGTH


def _returns_of(close):
    return (close / close.shift(1) - 1.0).to_numpy()


def _spearman(a, b):
    m = a.notna() & b.notna()
    return float(a[m].corr(b[m], method="spearman"))


def _bit_equal(a, b):
    """Bit-equal on the shared fired bars, and the NaN masks agree."""
    if not bool((a.isna() == b.isna()).all()):
        return False, 0, 0
    m = a.notna() & b.notna()
    return bool((a[m] == b[m]).all()), int((a[m] == b[m]).sum()), int(m.sum())


def _shared_equal(a, b):
    """(equal, shared) over the bars where BOTH fire, saying nothing about
    the masks. The unguarded variants below all report at bar `length - 1`
    where this module does not, so a mask-sensitive comparison against them
    would answer the wrong question."""
    m = a.notna() & b.notna()
    return int((a[m] == b[m]).sum()), int(m.sum())


# ------------------------------------------------------------ the oracles


def _source_windowed(close, length=LENGTH):
    """tsfresh's `count_above_mean` retyped and handed one window at a time,
    then divided by the window size. Shares no code with the module: a Python
    loop, `np.mean`, and the source's own `np.where(x > m)[0].size`."""
    r = _returns_of(close)
    out = np.full(r.size, np.nan)
    for t in range(length - 1, r.size):
        x = r[t - length + 1:t + 1]
        if not np.isfinite(x).all():
            continue
        out[t] = np.where(x > np.mean(x))[0].size / length
    return Series(out, index=close.index)


def _fsum_windowed(close, length=LENGTH):
    r = [float(v) for v in _returns_of(close)]
    out = np.full(len(r), np.nan)
    for t in range(length - 1, len(r)):
        x = r[t - length + 1:t + 1]
        if not all(math.isfinite(v) for v in x):
            continue
        m = math.fsum(x) / length
        out[t] = sum(1 for v in x if v > m) / length
    return Series(out, index=close.index)


def _exact_windowed(close, length=LENGTH):
    """Every float return is a rational, so the window mean is one and every
    comparison is decided with no rounding at all."""
    r = [float(v) for v in _returns_of(close)]
    out = np.full(len(r), np.nan)
    for t in range(length - 1, len(r)):
        x = r[t - length + 1:t + 1]
        if not all(math.isfinite(v) for v in x):
            continue
        q = [Fraction(v) for v in x]
        m = sum(q) / length
        out[t] = sum(1 for v in q if v > m) / length
    return Series(out, index=close.index)


def _prototype(close, length=LENGTH):
    """`docs/issues/screen/ind_screen.py`, candidate `ts_above_mean_20`,
    retyped: `roll(ret(c), 20, w_count_above_mean)` with
    `w_count_above_mean(W) = (W > W.mean(1, keepdims=True)).mean(1)` and
    `_from_win` writing at `out[n - 1:]`. No guards of any kind."""
    r = _returns_of(close)
    W = sliding_window_view(r, length)
    out = np.full(r.size, np.nan)
    out[length - 1:] = (W > W.mean(1, keepdims=True)).mean(1)
    return Series(out, index=close.index)


def _unguarded(close, length=LENGTH):
    """This module without its floor: the same windows, the same mean."""
    r = _returns_of(close)
    W = sliding_window_view(r, length)
    out = np.full(r.size, np.nan)
    out[length - 1:] = (W > (W.sum(axis=1) / length)[:, None]).sum(axis=1) / length
    return Series(out, index=close.index)


def _absolute_floor(close, length=LENGTH):
    """The floor the sibling tsfresh ports use -- `4096 eps` ABSOLUTE on the
    window's return range -- instead of this module's relative one."""
    r = _returns_of(close)
    W = sliding_window_view(r, length)
    out = np.full(r.size, np.nan)
    out[length - 1:] = np.where(
        W.max(axis=1) - W.min(axis=1) > NOISE_FACTOR,
        (W > (W.sum(axis=1) / length)[:, None]).sum(axis=1) / length, np.nan)
    return Series(out, index=close.index)


# --------------------------------------------------- Gate A: the source


def test_tsfresh_is_not_installed_here():
    """The attribution is an attribution. If tsfresh ever IS installed, this
    fails and whoever sees it should turn the oracles below into a direct
    comparison against `feature_calculators.count_above_mean`."""
    with pytest.raises(ImportError):
        importlib.import_module("tsfresh")


@pytest.mark.parametrize("frame", sorted(FRAMES))
def test_the_module_is_bit_equal_to_the_source_applied_window_by_window(frame):
    """Gate A1: 1,480 of 1,480 on each of nine frames, masks identical."""
    close = FRAMES[frame]()
    same, eq, shared = _bit_equal(ts_above_mean_20(close),
                                  _source_windowed(close))
    assert same and eq == shared == FIRED, (frame, eq, shared)


@pytest.mark.parametrize("frame", ["walk", "heavy-tailed", "right-skewed"])
def test_the_module_is_bit_equal_to_an_fsum_scalar_loop(frame):
    """Gate A2: the mean taken by `math.fsum`, which is exact up to one
    rounding, changes no count."""
    close = FRAMES[frame]()
    same, eq, shared = _bit_equal(ts_above_mean_20(close),
                                  _fsum_windowed(close))
    assert same and eq == shared == FIRED, (frame, eq, shared)


@pytest.mark.parametrize("frame", ["walk", "tick-rounded", "two-point",
                                   "right-skewed"])
def test_the_float_mean_never_flips_a_comparison_against_an_exact_oracle(frame):
    """Gate A3. The only thing float can do to this column is decide a
    comparison the wrong way, so the oracle is EXACT rational arithmetic and
    the assertion is equality, not a tolerance."""
    close = FRAMES[frame]()
    same, eq, shared = _bit_equal(ts_above_mean_20(close),
                                  _exact_windowed(close))
    assert same and eq == shared == FIRED, (frame, eq, shared)


def test_the_exact_oracle_agrees_on_a_mean_dominated_path():
    """Where the window sum's cancellation is worst: returns of 0.5 with an
    sd of 0.5e-5, i.e. `|mean| / sd` = 1e5. 580 of 580 bars exact."""
    rng = np.random.default_rng(99)
    close = _from_returns(0.5 + 0.5e-5 * rng.standard_normal(600))
    same, eq, shared = _bit_equal(ts_above_mean_20(close),
                                  _exact_windowed(close))
    assert same and eq == shared == 600 - LENGTH, (eq, shared)


@pytest.mark.parametrize("returns,expected", [
    ([0.01, -0.01] * 10, 0.5),
    ([0.5] + [0.0] * 19, 1 / 20),
    ([-0.5] + [0.0] * 19, 19 / 20),
    ([0.001 * k for k in range(1, 21)], 10 / 20),
    ([0.0] + [0.01] * 19, 19 / 20),
    ([0.01] + [0.0] * 19, 1 / 20),
])
def test_hand_derived_windows(returns, expected):
    """Gate A6, and the two ends of the range in the same table: one big
    gain among nineteen zeros is 0.05, one big loss is 0.95."""
    assert float(ts_above_mean_20(_window_frame(returns)).iloc[-1]) == expected


def test_twenty_identical_returns_are_refused_not_read_as_zero():
    """A window of identical returns is the ONLY way to reach a count of 0,
    and it is degenerate rather than quiet -- so it is NaN here."""
    assert bool(np.isnan(ts_above_mean_20(Series(100.0 * np.ones(21)))
                         .iloc[-1]))


# -------------------------------------------------- Gate A: the readings


def _log_return_variant(close, length=LENGTH):
    r = np.log(close.to_numpy()) - np.log(close.shift(1).to_numpy())
    W = sliding_window_view(r, length)
    out = np.full(r.size, np.nan)
    out[length - 1:] = (W > (W.sum(axis=1) / length)[:, None]).sum(axis=1) / length
    return Series(out, index=close.index)


def _ge_variant(close, length=LENGTH):
    r = _returns_of(close)
    W = sliding_window_view(r, length)
    out = np.full(r.size, np.nan)
    out[length - 1:] = (W >= (W.sum(axis=1) / length)[:, None]).sum(axis=1) / length
    return Series(out, index=close.index)


def _on_closes_variant(close, length=LENGTH):
    x = close.to_numpy(dtype=float)
    W = sliding_window_view(x, length)
    out = np.full(x.size, np.nan)
    out[length - 1:] = (W > (W.sum(axis=1) / length)[:, None]).sum(axis=1) / length
    return Series(out, index=close.index)


def test_log_returns_are_a_different_column():
    """Close, but not the same: Spearman 0.9839 and bit-equal on 1,395 of
    1,480 bars (measured). The band is wide because the disagreeing bars are
    near-ties whose count a last-bit difference can move."""
    close = _walk()
    base, other = ts_above_mean_20(close), _log_return_variant(close)
    rho = _spearman(base, other)
    eq, shared = _shared_equal(base, other)
    assert 0.97 < rho < 0.999, rho
    assert shared == FIRED
    assert 1300 <= eq <= 1450, (eq, shared)


def test_twenty_closes_instead_of_twenty_returns_is_a_different_column():
    """The off-by-one a reader makes, priced so it is not re-argued."""
    close = _walk()
    rho = _spearman(ts_above_mean_20(close),
                    ts_above_mean_20(close, length=LENGTH - 1))
    assert 0.85 < rho < 0.93, rho


def test_the_statistic_of_the_closes_is_a_different_question_entirely():
    close = _walk()
    rho = _spearman(ts_above_mean_20(close), _on_closes_variant(close))
    assert abs(rho) < 0.3, rho


@pytest.mark.parametrize("frame", ["walk", "tick-rounded", "two-point"])
def test_strictness_is_invisible_on_generated_frames(frame):
    """The strict `>` is the source's, and no frame here can see it: a tie
    with a 20-way AVERAGE does not happen by accident. Counted -- 0 exact
    ties in 29,600 window/return pairs of each frame -- so the choice is
    pinned by the constructed window in the next test instead."""
    close = FRAMES[frame]()
    W = sliding_window_view(_returns_of(close)[1:], LENGTH)
    assert int((W == (W.sum(axis=1) / LENGTH)[:, None]).sum()) == 0
    eq, shared = _shared_equal(ts_above_mean_20(close), _ge_variant(close))
    assert eq == shared == FIRED


def test_a_constructed_exact_tie_shows_the_strict_comparison():
    """Closes [100, 50, 50, 75] have returns [-0.5, 0.0, +0.5], which sum to
    exactly 0.0 in float64, so the middle return ties the mean exactly. At
    `length` 3 the strict form reads 1/3 and `>=` reads 2/3."""
    tie = Series([100.0, 50.0, 50.0, 75.0])
    assert float(ts_above_mean_20(tie, length=3).iloc[-1]) == 1 / 3
    assert float(_ge_variant(tie, length=3).iloc[-1]) == 2 / 3


def test_the_share_is_the_raw_count_rescaled():
    """The issue asks for `count_above_mean / n`. Dividing is an exact
    rescaling, so it is the one choice a rank miner cannot see -- and the
    values are exactly `k / length`."""
    col = ts_above_mean_20(_walk()).dropna()
    counts = col * LENGTH
    assert bool((counts == counts.round()).all())
    assert set(counts.unique()) <= set(float(k) for k in range(1, LENGTH))


# --------------------------------------------------------------- the range


@pytest.mark.parametrize("frame", sorted(FRAMES))
def test_the_column_never_leaves_one_over_length_to_one_minus_that(frame):
    """Item 2. Not a measured band: if no return were above the mean, all
    would be at or below it and the sum would force them EQUAL, which the
    floor refuses. So 1 <= count <= length - 1 on every reported window."""
    col = ts_above_mean_20(FRAMES[frame]()).dropna()
    assert float(col.min()) >= 1 / LENGTH, frame
    assert float(col.max()) <= 1 - 1 / LENGTH, frame


def test_both_ends_of_the_range_are_attained_on_a_generated_frame():
    """A heavy-tailed frame reaches all 19 reachable values, 0.05 .. 0.95."""
    col = ts_above_mean_20(_heavy_tailed()).dropna()
    assert float(col.min()) == 1 / LENGTH
    assert float(col.max()) == 1 - 1 / LENGTH
    assert int(col.nunique()) >= 15


def test_the_impossible_values_are_what_an_unguarded_spelling_emits():
    """The other half of item 2: 0.0 IS reachable without the floor, on
    every body window of a flat frame, and it would read to a tree as the
    calmest possible window rather than as missing data."""
    flat = _flat()
    body = _unguarded(flat).iloc[LENGTH:].dropna()
    assert int(body.size) == 300 - LENGTH
    assert bool((body == 0.0).all())
    assert int(ts_above_mean_20(flat).notna().sum()) == 0


# ------------------------------------------------------ Gate B: the mutants


BACK_DATE_TWO = (
    "    out[length - 1:] = np.where(reported, count / length, np.nan)",
    "    out[length - 3:c.size - 2] = np.where(reported, count / length, np.nan)")
BACK_DATE_FULL = (
    "    out[length - 1:] = np.where(reported, count / length, np.nan)",
    "    out[:windows.shape[0]] = np.where(reported, count / length, np.nan)")
FORWARD_WINDOW = (
    "    windows = sliding_window_view(r, length)",
    "    windows = sliding_window_view(np.roll(r, -1), length)")
FORWARD_RETURN = (
    "        r = (px / px.shift(1) - 1.0).to_numpy()",
    "        r = (px.shift(-1) / px - 1.0).to_numpy()")
FUTURE_MEAN = (
    "        count += windows[:, j] > mean",
    "        count += windows[:, j] > np.roll(mean, -1)")
#: The floor's own index -- the one the blind sweep cannot reach on a clean
#: frame, because `reported` is True on every body window there, so the only
#: bar this mutation moves is bar `length - 1`, which precedes every offset.
#: It IS live (it turns that bar from NaN into 0.0, the arithmetically
#: impossible value) and it IS a look-ahead (bar T's mask would read window
#: T+1), so it is caught by a designed frame instead -- see
#: `test_the_designed_probe_catches_the_floor_index_mutant`.
SHIFTED_FLOOR = (
    "    hi, lo = windows.max(axis=1), windows.min(axis=1)",
    "    hi, lo = (np.roll(windows.max(axis=1), -1),\n"
    "              np.roll(windows.min(axis=1), -1))")

MUTANTS = {
    "back_date_two": BACK_DATE_TWO,
    "back_date_full": BACK_DATE_FULL,
    "forward_window": FORWARD_WINDOW,
    "forward_return": FORWARD_RETURN,
    "future_mean": FUTURE_MEAN,
}
OFFSETS = range(40, 1500, 40)  # 37 offsets
PAIRS = {
    "walk": (_walk(), _walk(seed=97)),
    "tick-rounded": (_tick_rounded(), _tick_rounded(seed=56)),
    "heavy-tailed": (_heavy_tailed(), _heavy_tailed(seed=8)),
}
#: Measured catch counts of the blind sweep, out of 37 offsets, at the
#: default `length` -- BANDS, not targets. A perturbation that moves no count
#: is invisible to the sweep, which is why the floors are below 37.
CAUGHT = {
    "back_date_two": (25, 37),
    "back_date_full": (30, 37),
    "forward_window": (20, 37),
    "forward_return": (30, 37),
    "future_mean": (30, 37),
}


def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_ts_above_mean_20_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


def _caught(fn, close, other, **kwargs):
    """Offsets J at which replacing every close from bar J on moves a bar
    BEFORE J -- which a causal column cannot do."""
    base = fn(close, **kwargs)
    hits = []
    for j in OFFSETS:
        p = close.copy()
        p.iloc[j:] = other.iloc[j:].values
        out = fn(p, **kwargs)
        a, b = base.iloc[:j], out.iloc[:j]
        if not (a.isna() == b.isna()).all():
            hits.append(j)
            continue
        m = a.notna()
        if (a[m] != b[m]).any():
            hits.append(j)
    return hits


@pytest.mark.parametrize("frame", sorted(PAIRS))
def test_the_real_module_leaks_nothing_under_the_mutant_sweep(frame):
    """Gate B's premise: replacing every close from bar J on changes no bar
    before J. 0 of 37 offsets on each of three frames."""
    close, other = PAIRS[frame]
    assert _caught(ts_above_mean_20, close, other) == []


@pytest.mark.parametrize("length", [5, 60, 250])
def test_the_real_module_leaks_nothing_at_other_lengths(length):
    close, other = PAIRS["walk"]
    assert _caught(ts_above_mean_20, close, other, length=length) == []
    assert int(ts_above_mean_20(close, length=length).notna()
               .to_numpy().argmax()) == length


@pytest.mark.parametrize("mutant", sorted(MUTANTS))
@pytest.mark.parametrize("frame", sorted(PAIRS))
def test_each_mutant_is_live_and_the_sweep_catches_it(mutant, frame):
    """Every mutant must CHANGE the column -- otherwise the test proves
    nothing -- and be caught by the blind sweep within its measured band."""
    mod = _load_mutant(*MUTANTS[mutant])
    close, other = PAIRS[frame]
    assert not mod.ts_above_mean_20(close).equals(ts_above_mean_20(close))
    hits = _caught(mod.ts_above_mean_20, close, other)
    lo, hi = CAUGHT[mutant]
    assert lo <= len(hits) <= hi, (mutant, frame, len(hits))


def test_the_floor_index_mutant_is_live_but_invisible_to_the_blind_sweep():
    """The sixth mutant, and the honest account of what Gate B's sweep cannot
    do here. Shifting `hi`/`lo` by one window makes bar T's NaN mask read
    window T+1 -- a look-ahead. On a clean frame it is LIVE and moves exactly
    TWO bars, pinned here as a set so neither can be hidden again:

    * bar `length - 1`, from NaN to **0.0** -- the value item 2 says this
      column cannot reach. That is the look-ahead, and the sweep cannot see
      it because the bar precedes every offset (those start at 40) and reads
      0.0 in the perturbed run too;
    * the LAST bar, from a value to NaN. That is a `np.roll` WRAP and not a
      look-ahead: the rolled extrema of window 0, which hold the undefined
      first return, land on the last window. The sweep cannot see that one
      either, because `_caught` only inspects bars BEFORE the offset and the
      offsets stop at 1480.

    So the sweep scores 0/37 and proves nothing. The next test is what
    catches it."""
    mod = _load_mutant(*SHIFTED_FLOOR)
    for frame, (close, other) in sorted(PAIRS.items()):
        real, mutant = ts_above_mean_20(close), mod.ts_above_mean_20(close)
        assert not mutant.equals(real), frame          # live
        moved = set(np.flatnonzero(
            (real.isna() != mutant.isna()).to_numpy()
            | (real.fillna(-1.0) != mutant.fillna(-1.0)).to_numpy()).tolist())
        assert moved == {LENGTH - 1, len(close) - 1}, (frame, sorted(moved))
        assert bool(np.isnan(real.iloc[LENGTH - 1]))
        assert float(mutant.iloc[LENGTH - 1]) == 0.0
        assert real.notna().iloc[-1] and bool(np.isnan(mutant.iloc[-1]))
        assert _caught(mod.ts_above_mean_20, close, other) == [], frame


def test_the_designed_probe_catches_the_floor_index_mutant():
    """A frame where the floor is active on INTERIOR windows -- a walk
    interrupted every 40 bars by 25 bars of exactly-zero returns, which is 36
    patches of 6 all-zero windows each, 216 interior empties measured --
    puts the shifted mask inside the sweep's reach. The real module still
    leaks 0 of 37; the mutant is caught 36 of 37, because an offset landing
    in a flat patch replaces the returns the mutant's bar J-1 illegally
    reads, flipping that bar between NaN and a value."""
    close, other = _floored_patches(), _floored_patches(seed=24)
    interior = int(ts_above_mean_20(close).iloc[LENGTH:].isna().sum())
    assert 150 <= interior <= 300, interior
    assert _caught(ts_above_mean_20, close, other) == []
    mod = _load_mutant(*SHIFTED_FLOOR)
    assert len(_caught(mod.ts_above_mean_20, close, other)) >= 20


def test_the_first_fired_bar_is_length_not_length_minus_one():
    """20 returns need 21 closes, so bar 19's window holds the undefined
    first return. The prototype reports there and this module does not --
    which is also what makes the two NaN masks differ."""
    col = ts_above_mean_20(_walk())
    assert int(col.notna().to_numpy().argmax()) == LENGTH
    assert bool(np.isnan(col.iloc[LENGTH - 1]))
    assert float(_prototype(_walk()).iloc[LENGTH - 1]) == 0.0


# ------------------------------------------------------- Gate C / Gate D


@pytest.mark.parametrize("frame", sorted(FRAMES))
def test_gate_c_the_column_fires_and_varies(frame):
    """0 < fires < n and more than one distinct value, on every frame.

    SYNTHETIC. The real-data counts come from Gate E's run and are pinned by
    `test_the_ledger_row_carries_the_measured_gate_e_numbers`."""
    close = FRAMES[frame]()
    col = ts_above_mean_20(close)
    fired = int(col.notna().sum())
    assert fired == FIRED
    assert int(col.nunique()) >= 5, frame
    assert int((col.dropna() != 0).sum()) == fired
    # Gate D3's `0 < fires < n` bites where the count is NOT pinned exactly:
    # the two degenerate frames, which the floor empties outright.
    assert int(ts_above_mean_20(_flat()).notna().sum()) == 0
    assert int(ts_above_mean_20(_ladder()).notna().sum()) == 0


@pytest.mark.parametrize("frame", sorted(FRAMES))
@pytest.mark.parametrize("k", [8.0, 64.0])
def test_scale_x8_and_x64_are_bit_identical(frame, k):
    """Gate D. `8a / 8b` is the same double as `a / b`, so the returns are
    bit-identical and so is everything downstream."""
    close = FRAMES[frame]()
    same, eq, shared = _bit_equal(ts_above_mean_20(close),
                                  ts_above_mean_20(close * k))
    assert same and eq == shared == FIRED, (frame, k, eq, shared)


@pytest.mark.parametrize("length", [3, 5, 60, 250])
def test_scale_x8_is_bit_identical_at_other_lengths(length):
    close = _walk()
    base = ts_above_mean_20(close, length=length)
    same, eq, shared = _bit_equal(base, ts_above_mean_20(close * 8.0,
                                                         length=length))
    assert same and eq == shared == 1500 - length
    assert float(base.min()) >= 1 / length
    assert float(base.max()) <= 1 - 1 / length


@pytest.mark.parametrize("k", [10.0, 3.7, 0.1])
def test_scale_x10_and_x3_7_agree_though_they_need_not(k):
    """These rescales DO perturb the returns' last bits, so bit-equality is
    a measurement rather than a guarantee -- the margin behind it is the next
    test. So the assertion is BANDED: the values must agree on all but a
    handful of bars (measured here: 1,480 of 1,480, so the band has never
    been used -- it is there because a runner with different SIMD kernels
    could land one near-tie the other way). The NaN masks are asserted
    exactly, and that too is a margin and not an exactness: the floor is
    scale-invariant in REAL arithmetic only, and x10 moves `hi`, `lo` and
    `max|r|` in their last bits -- but a mask bit can only move for a window
    whose spread sits within a factor of about 1 of `4096 eps * max|r|`, and
    on these frames that ratio is ten orders of magnitude clear."""
    close = _walk()
    base, other = ts_above_mean_20(close), ts_above_mean_20(close * k)
    assert bool((base.isna() == other.isna()).all()), k
    eq, shared = _shared_equal(base, other)
    assert shared == FIRED and eq >= FIRED - 5, (k, eq)
    assert _spearman(base, other) > 0.999, k


def test_the_margin_behind_that_agreement_is_nine_orders_of_magnitude():
    """A count moves only when a perturbation reorders a return and its own
    window mean. Over 199,980 windows of a 200,000-bar walk the smallest gap
    `|r - mean| / max|r|` measured is 1.6e-07, against an ulp of 2.2e-16.
    The assertion is the margin, loosely banded, not that exact number."""
    r = _returns_of(_walk(200000, seed=4))[1:]
    W = sliding_window_view(r, LENGTH)
    gap = np.abs(W - (W.sum(axis=1) / LENGTH)[:, None]).min(axis=1)
    ratio = float((gap / np.abs(W).max(axis=1)).min())
    # The claim is about `ratio / eps` -- how many ulps of its own scale the
    # closest return stands off its window mean. Measured 7.0e+08.
    assert ratio / np.finfo(float).eps > 1e7, ratio


@pytest.mark.parametrize("label,make", [
    ("r x 2", lambda r: 2.0 * r),
    ("r x 0.5", lambda r: 0.5 * r),
    ("r + 0.004", lambda r: r + 0.004),
])
def test_scale_an_affine_map_of_the_returns_leaves_it_where_it_was(label, make):
    """Stronger than a price rescale, and the reason this is neither a
    volatility nor a direction column: the COUNT is invariant to any affine
    map of the returns with a positive slope. The frame is rebuilt from the
    mapped returns by `cumprod`, so the returns that come back out differ in
    their last bits and this is a banded measurement, not the exact identity
    -- 1,480 of 1,480 here, and the band has never been used."""
    rng = np.random.default_rng(11)
    r = 0.015 * rng.standard_normal(1500)
    base = ts_above_mean_20(_from_returns(r))
    other = ts_above_mean_20(_from_returns(make(r)))
    assert bool((base.isna() == other.isna()).all()), label
    eq, shared = _shared_equal(base, other)
    assert shared == FIRED and eq >= FIRED - 5, (label, eq, shared)


def test_that_invariance_is_the_counts_and_not_the_reported_masks():
    """The limit of the test above, measured rather than left implicit: the
    floor `(hi - lo) > 4096 eps * max|r|` is scale-invariant but NOT
    shift-invariant, because a drift grows `max|r|` and leaves `hi - lo`
    alone. Returns of about 1e-6 whose window spread sits just under the
    threshold a 0.004 drift would impose fire on 580 of 600 bars undrifted
    and on 0 drifted."""
    rng = np.random.default_rng(13)
    noise = 3e-16 * rng.standard_normal(600)
    assert int(ts_above_mean_20(_from_returns(1e-6 + noise))
               .notna().sum()) == 600 - LENGTH
    assert int(ts_above_mean_20(_from_returns(1e-6 + 0.004 + noise))
               .notna().sum()) == 0


# ------------------------------------------------------------- the guards


@pytest.mark.parametrize("frame", sorted(FRAMES))
def test_the_floor_costs_no_body_bar_on_a_clean_frame(frame):
    """It empties bar `length - 1` on every frame -- the window holding the
    undefined first return -- and nothing else."""
    close = FRAMES[frame]()
    lost = ts_above_mean_20(close).isna() & _unguarded(close).notna()
    assert int(lost.iloc[LENGTH:].sum()) == 0, frame
    assert int(lost.sum()) == 1, frame


def test_the_floor_empties_a_constant_return_ladder_the_unguarded_one_does_not():
    """A 1%-a-bar geometric ladder has a mathematically CONSTANT return that
    float64 reproduces only to rounding, so an unguarded count is decided by
    that rounding: 280 body windows reported, across many distinct values,
    none of them meaningful."""
    lad = _ladder()
    body = _unguarded(lad).iloc[LENGTH:].dropna()
    assert int(body.size) == 300 - LENGTH
    assert int(body.nunique()) >= 5
    assert int(ts_above_mean_20(lad).notna().sum()) == 0


def test_the_floor_is_relative_and_an_absolute_one_would_be_wrong_here():
    """Why this module does NOT copy the siblings' absolute `4096 eps`: on a
    quiet-but-honest frame -- returns of about 1e-6 with a 1e-13 spread --
    every comparison is exact (checked against the rational oracle) and an
    absolute floor would throw all of it away."""
    rng = np.random.default_rng(5)
    close = _from_returns(1e-6 + 1e-13 * rng.standard_normal(600))
    shipped = ts_above_mean_20(close)
    assert int(shipped.notna().sum()) == 600 - LENGTH
    assert int(_absolute_floor(close).notna().sum()) == 0
    same, eq, shared = _bit_equal(shipped, _exact_windowed(close))
    assert same and eq == shared == 600 - LENGTH


def test_the_relative_floor_still_refuses_the_mirror_case():
    """Returns of about 0.5 with a 1e-14 spread: here the count IS rounding,
    and both floors must refuse."""
    rng = np.random.default_rng(5)
    close = _from_returns(0.5 + 1e-14 * rng.standard_normal(600))
    assert int(ts_above_mean_20(close).notna().sum()) == 0
    assert int(_absolute_floor(close).notna().sum()) == 0


@pytest.mark.parametrize("bar,emptied", [(0, 1), (1, 2), (19, 20), (200, 21),
                                         (398, 2), (399, 1)])
def test_a_non_finite_return_empties_its_windows(bar, emptied):
    """A bad close spoils TWO returns, so it empties the `length + 1` = 21
    windows it sits in -- fewer near either end, where the warm-up or the end
    of the frame swallows part of the span. 0 earlier bars move, which is the
    other half of the claim."""
    close = _walk(400)
    base = ts_above_mean_20(close)
    holed = close.copy()
    holed.iloc[bar] = np.nan
    out = ts_above_mean_20(holed)
    assert int((out.isna() & base.notna()).sum()) == emptied
    before = slice(0, bar - LENGTH) if bar > LENGTH else slice(0, 0)
    assert bool((out.iloc[before].fillna(-1.0)
                 == base.iloc[before].fillna(-1.0)).all())


@pytest.mark.parametrize("value", [0.0, -100.0, 1e-310, np.inf])
def test_a_close_that_has_no_return_is_treated_as_missing(value):
    """Zero, negative, subnormal and infinite closes all have no usable
    return, so they empty their windows exactly as a NaN does."""
    close = _walk(400)
    base = ts_above_mean_20(close)
    holed = close.copy()
    holed.iloc[200] = value
    out = ts_above_mean_20(holed)
    assert int((out.isna() & base.notna()).sum()) == LENGTH + 1


@pytest.mark.parametrize("mag", [1e2, 1e6, 1e8, 1e100, 1e300])
def test_one_enormous_return_stays_local(mag):
    """What separates this module from the fork's `ts_ac1_60` and
    `ts_cid_ce_20`, whose ONLINE accumulators carry a residue forward: every
    window here is reduced from its own `length` values, so a planted return
    moves exactly the 20 windows holding it -- and moves them to the RIGHT
    answer, one return above the mean. The frame is priced at 1e-198 so even
    the largest jump leaves every close a normal float."""
    close = _walk(2000, seed=21) * 1e-200
    base = ts_above_mean_20(close)
    spiked = close.copy()
    spiked.iloc[200:] = spiked.iloc[200:] * mag
    out = ts_above_mean_20(spiked)
    assert bool((out.iloc[200:220] == 1 / LENGTH).all()), mag
    tail = slice(220, None)
    assert bool((out.iloc[tail].isna() == base.iloc[tail].isna()).all())
    assert bool((out.iloc[tail].dropna() == base.iloc[tail].dropna()).all())


def test_a_return_above_the_bound_is_dropped_and_still_local():
    """Above `max / (2 * length)` = 4.49e+306 the window sum could overflow,
    so the return is refused -- and the 1,780 bars after it are still
    bit-identical to the unspiked frame."""
    close = _walk(2000, seed=21) * 1e-200
    base = ts_above_mean_20(close)
    spiked = close.copy()
    spiked.iloc[200:] = spiked.iloc[200:] * 1e307
    out = ts_above_mean_20(spiked)
    assert bool(out.iloc[200:220].isna().all())
    tail = slice(220, None)
    assert bool((out.iloc[tail].isna() == base.iloc[tail].isna()).all())
    assert bool((out.iloc[tail].dropna() == base.iloc[tail].dropna()).all())


# ------------------------------------------------- the prototype and Gate E


@pytest.mark.parametrize("frame", sorted(FRAMES))
def test_the_port_is_bit_equal_to_the_screen_prototype(frame):
    """Item 7. The prototype shares the statistic exactly; the masks differ
    only at bar `length - 1`, where it emits the impossible 0.00."""
    close = FRAMES[frame]()
    base, proto = ts_above_mean_20(close), _prototype(close)
    m = base.notna() & proto.notna()
    assert int(m.sum()) == FIRED
    assert bool((base[m] == proto[m]).all()), frame
    differ = base.isna() != proto.isna()
    assert int(differ.sum()) == 1 and bool(differ.iloc[LENGTH - 1])


def test_the_prototype_counts_through_a_bad_close_and_this_port_does_not():
    """The second mask difference, and the reason the screen's Gate E figure
    is an expectation and not a receipt: on a frame carrying a NaN close the
    two part company, agreeing bit-for-bit everywhere else."""
    holed = _walk()
    holed.iloc[200] = np.nan
    base, proto = ts_above_mean_20(holed), _prototype(holed)
    differ = base.isna() != proto.isna()
    assert int(differ.sum()) == LENGTH + 2  # the 21 windows, plus bar 19
    m = base.notna() & proto.notna()
    assert bool((base[m] == proto[m]).all())


def _ledger_rows():
    import csv
    from pathlib import Path
    ledger = Path(__file__).resolve().parents[1] / "docs" / "gate_e_ledger.csv"
    rows = list(csv.DictReader(ledger.open(encoding="utf-8")))
    assert rows, "the ledger should not be empty"
    assert [r for r in rows if r["column"].startswith("TS_AC1")], \
        "sanity: the ledger should carry the neighbouring ts_ac1_60 row"
    return rows


def test_the_ledger_row_is_this_modules_gate_e_run():
    """Gate E on this column is the launcher's run on THIS module,
    `is97-ts_above_mean_20-5d78f565` (measured 2026-11-13), and NOT issue
    #97's screen, which measured the prototype -- a column this file's item 7
    separates from the port by two NaN rules. The two agree to the four
    decimals the screen published (0.3594 vs `PVT_Slope_norm` at the same
    n = 396,970), which is exactly why the identity of the row needs pinning:
    `tests/test_gate_e_ledger.py` re-derives a row's `module_sha1` and output
    fingerprint from the tree and checks its verdict arithmetic, but it cannot
    see WHOSE measurement a row came from.
    """
    rows = [r for r in _ledger_rows() if r["indicator"] == "ts_above_mean_20"]
    assert len(rows) == 1
    row = rows[0]
    assert row["module"] == "pandas_ta.statistics.ts_above_mean_20"
    assert row["column"] == "TS_ABOVE_MEAN_20"
    assert row["run"] == "is97-ts_above_mean_20-5d78f565"
    assert row["verdict"] == "SHIP"
    assert row["verdict_schema"] == "r3-perframe-0.90"
    assert row["waiver"] == ""
    assert (int(row["n_frames"]), int(row["n_comparators"])) == (89, 687)
    assert float(row["max_abs_rho"]) < 0.76
    assert float(row["perframe_max_median_abs_rho"]) < 0.90


def test_the_ledger_row_carries_the_measured_gate_e_numbers():
    """The figures `docs/TsAboveMean20Measured.md` reports in its Gate E and
    Gate C sections, read back out of the ledger so that an edit to either one
    has to move both: 0.35937568662749647 vs `PVT_Slope_norm` over the
    manifest set at n = 396,970, per-frame max median 0.3580864882804631
    against the same comparator over 89 frames, and the run's real-data
    reachability counts -- 397,069 non-NaN and 397,069 non-zero of 398,849
    pooled bars.

    Two load-bearing ones. The NaN bars are exactly 20 x 89, the warm-up, so
    none of this module's guards emptied a window on the 89 BIST frames -- any
    window they emptied would be a NaN bar past bar 19 of its frame. And
    non-zero == non-NaN is item 2's range bound seen on real data: a reading
    of exactly 0.0 needs all twenty returns equal, which the floor refuses
    rather than reports.
    """
    rows = [r for r in _ledger_rows() if r["column"] == "TS_ABOVE_MEAN_20"]
    assert len(rows) == 1
    row = rows[0]
    assert float(row["max_abs_rho"]) == 0.35937568662749647
    assert row["against"] == "PVT_Slope_norm"
    assert row["against_set"] == "manifest"
    assert int(row["n"]) == 396970
    assert float(row["perframe_max_median_abs_rho"]) == 0.3580864882804631
    assert row["perframe_max_against"] == "PVT_Slope_norm"
    assert (int(row["non_nan"]), int(row["non_zero"])) == (397069, 397069)
    assert int(row["pooled_bars"]) == 398849
    # The NaN bars are exactly the warm-up: 20 per frame, 89 frames.
    assert int(row["pooled_bars"]) - int(row["non_nan"]) == LENGTH * 89


# ------------------------------------------- what the column actually is


def test_it_is_a_backwards_skewness_reading():
    """Item 5, on 20,000 INDEPENDENT windows spanning skewness -3 .. +3, so
    the relation is not an artefact of overlapping windows. Negative: a few
    large gains pull the mean up and push the column down.

    ⚠ This pins the STATISTIC, not the shipped function: 20,000 one-window
    calls would be a slow way to say the same thing, so the count is
    recomputed here. What transfers it to the column is Gate A1's
    bit-equality -- 1,480 of 1,480 on each of nine frames against the source
    applied window by window."""
    rng = np.random.default_rng(2026)
    W = (rng.standard_normal((20000, LENGTH))
         + np.linspace(-3.0, 3.0, 20000)[:, None]
         * (rng.standard_exponential((20000, LENGTH)) - 1.0))
    v = (W > W.mean(1, keepdims=True)).sum(1) / LENGTH
    z = (W - W.mean(1, keepdims=True)) / W.std(1, keepdims=True)
    rho = float(pd.Series(v).corr(pd.Series((z ** 3).mean(1)),
                                  method="spearman"))
    assert -0.95 < rho < -0.6, rho


@pytest.mark.parametrize("frame,lo,hi", [("walk", -0.75, -0.50),
                                         ("heavy-tailed", -0.95, -0.75),
                                         ("two-point", -1.00, -0.90)])
def test_the_in_fork_overlap_with_the_shipped_return_skewness(frame, lo, hi):
    """Disclosed because Gate E cannot see it: its 687 comparators hold no
    pandas_ta port. `OSAP_RETSKEW_21` is this fork's return-skewness column,
    and on a TWO-POINT frame -- returns taking exactly two values -- the two
    are one statistic. The bands are wide on purpose; what is pinned is that
    the overlap exists and grows with the tails."""
    close = FRAMES[frame]()
    rho = _spearman(ts_above_mean_20(close), pandas_ta.osap_retskew_21(close))
    assert lo <= rho <= hi, (frame, rho)


def test_it_is_neither_volatility_nor_direction_on_a_walk():
    """The flip side of the affine invariance above."""
    close = _walk()
    r = Series(_returns_of(close), index=close.index)
    base = ts_above_mean_20(close)
    assert abs(_spearman(base, r.rolling(LENGTH).std())) < 0.25
    assert abs(_spearman(base, r.rolling(LENGTH).mean())) < 0.25


def test_it_is_coarse_and_heavily_tied():
    """19 values EXIST at length 20; a 1,500-bar walk shows about ten of
    them, with one value taking a quarter of the bars. A rank statistic over
    this column carries many tied ranks by construction."""
    col = ts_above_mean_20(_walk()).dropna()
    assert 5 <= int(col.nunique()) <= 15
    assert int(col.value_counts().max()) > 0.2 * col.size


def test_it_is_a_state_not_an_event_flag():
    """Neighbouring windows share 19 of their 20 returns."""
    col = ts_above_mean_20(_walk()).dropna()
    assert float(col.autocorr(1)) > 0.7
    assert float(col.autocorr(20)) < 0.4


def test_the_level_is_one_half_for_any_symmetric_distribution():
    """Not measured per frame but derived and then measured. The derivation
    is a REFLECTION and not "mean = median" (a skewed law can have those
    equal and not read 0.5): if the returns are iid and symmetric about `u`,
    then `x -> 2u - x` preserves the law, maps the window mean to its own
    reflection, and swaps the above-mean and below-mean counts. Ties have
    probability 0, so E[count above] = length / 2 and the column sits at 0.5
    whatever the tails do. 20,000 independent windows.

    ⚠ Like the test above, this pins the STATISTIC; Gate A1's bit-equality is
    what carries it to the shipped column."""
    rng = np.random.default_rng(2026)
    for draw in (rng.standard_normal, lambda s: rng.standard_t(2.0, s)):
        W = draw((20000, LENGTH))
        v = (W > W.mean(1, keepdims=True)).sum(1) / LENGTH
        assert abs(float(v.mean()) - 0.5) < 0.01


# ---------------------------------------------------- wiring and arguments


def test_name_registration_and_accessor():
    close = _walk(400)
    out = ts_above_mean_20(close)
    assert out.name == f"TS_ABOVE_MEAN_{LENGTH}"
    assert out.category == "statistics"
    assert "ts_above_mean_20" in pandas_ta.Category["statistics"]
    df = pd.DataFrame({"close": close})
    df.index = pd.date_range("2020-01-01", periods=len(close), freq="D")
    got = df.ta.ts_above_mean_20()
    assert got.name == f"TS_ABOVE_MEAN_{LENGTH}"
    pd.testing.assert_series_equal(got.reset_index(drop=True),
                                   out.reset_index(drop=True))


@pytest.mark.parametrize("length,name", [(None, 20), (0, 20), (2, 20),
                                         (-5, 20), (60, 60)])
def test_a_length_below_the_minimum_falls_back_to_the_default(length, name):
    """A window of two returns is identically 1/2, so `length` 2 is not a
    column; three is the smallest that varies."""
    assert ts_above_mean_20(_walk(400), length=length).name \
        == f"TS_ABOVE_MEAN_{name}"


def test_length_three_takes_exactly_two_values():
    col = ts_above_mean_20(_walk(400), length=3).dropna()
    assert set(col.unique()) == {1 / 3, 2 / 3}


def test_too_short_an_input_returns_none():
    """`length` returns need `length + 1` closes."""
    assert ts_above_mean_20(_walk(LENGTH)) is None
    assert int(ts_above_mean_20(_walk(LENGTH + 1)).notna().sum()) == 1


def test_offset_and_fillna():
    close = _walk(400)
    base = ts_above_mean_20(close)
    pd.testing.assert_series_equal(ts_above_mean_20(close, offset=2),
                                   base.shift(2), check_names=False)
    pd.testing.assert_series_equal(ts_above_mean_20(close, offset=-2),
                                   base.shift(-2), check_names=False)
    filled = ts_above_mean_20(close, fillna=0.0)
    assert int(filled.isna().sum()) == 0
    assert bool((filled.iloc[:LENGTH] == 0.0).all())


def test_the_module_does_not_import_the_package_root():
    """The `TypeError: 'module' object is not callable` trap in CLAUDE.md:
    a helper is imported from its own module, never from the package."""
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert "from pandas_ta.statistics import" not in src
    assert "from pandas_ta.overlap import" not in src


def test_the_count_is_spelled_column_by_column_not_as_a_matrix():
    """A cost choice, pinned because the two spellings are behaviourally
    identical and only the memory and the timing separate them: the
    `(rows, length)` bool matrix peaks at 103.3 MB at `length` 250 where this
    form stays at 6.9 MB (docs/TsAboveMean20Measured.md, Cost). If the
    one-liner is ever restored, re-measure before accepting it."""
    code = [ln for ln in open(_REAL.__file__, encoding="utf-8").read()
            .splitlines() if not ln.lstrip().startswith("#")]
    assert any("count += windows[:, j] > mean" in ln for ln in code)
    assert not any("windows > mean[:, None]" in ln for ln in code)
