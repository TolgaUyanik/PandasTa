# -*- coding: utf-8 -*-
"""LEAN-TDD-20: `lean_tdd_20`, the target downside deviation at target 0
(PandasTa issue #87).

    LEAN_TDD_20 = sqrt( mean( min(r, 0)^2 ) ) over a window of 20 simple
                  returns -- the root-mean-square of the window's negative
                  returns, with the up bars counted as ZEROS.

WHAT THIS FILE PINS, in order of how much it would hurt to lose.

1. **Gate A, and that the formula under test is the issue's NAME plus the
   standard definition, not Lean's code.** QuantConnect Lean's
   `TargetDownsideDeviation` C# source is NOT in this worktree and web
   access is unavailable, so "Apache-2.0 Lean" is an attribution, not an
   oracle. What IS checkable is pinned three ways:

   * three hand-derived windows whose answers are exact doubles -- three
     returns of -0.5 give EXACTLY 0.5; a two-return window gives
     sqrt(0.125), then EXACTLY 0.0 where the window has no down bar, then
     sqrt(0.125) again; and one shortfall among three returns gives
     sqrt(0.25/3) and not sqrt(0.25/1)
     (`test_hand_derived_windows_are_exact`);
   * the screen prototype of `docs/issues/screen/ind_screen.py` (candidate
     `lean_tdd_20`), retyped here because that file is gitignored:
     **bit-equal on all 1,480 fired bars** of a 1,500-bar walk, NaN masks
     equal. The port is the column the screen measured, not a relative;
   * an independent per-window loop in plain Python scalars whose window is
     summed by `math.fsum`, which is EXACT: max |difference| 1.7e-18,
     Spearman 0.99999995, and bit-equal on 304 of 380 bars (330 of 380 on a
     0.01 grid, 380 of 380 on a rally). Those last counts are the only
     measured gap in Gate A and they are `rolling.mean`'s add-and-remove
     accumulation, not the formula's -- an exact window sum differs from
     pandas' online one in the last bits, which is also enough to break an
     exact tie. Every rank correlation NEAR 1 in this file -- the ones an
     "identical ranking" claim would rest on -- is read at eight decimals
     for that reason: 0.99999995 rounds to 1.000000 at six. The ones
     plainly below 1 are quoted at four to six.

2. **Gate B, by mutant, and why the path sweep alone is not enough here.**
   Four mutants, each `importlib`-read and `exec`'d in memory: the column
   back-dated by `length`; the return taken forward; the squared shortfall
   taken forward; and a `center=True` rolling mean. The real module leaks at
   **0/36** on every frame of both probes.
   * The usual path sweep (replace every bar from J onward with a different
     path) catches `write_shift` at 35-36/36 and `centered_mean` at
     31-36/36, but the ONE-BAR-ahead mutants at only 11-17/36 on three of
     the four frames. That is the PROBE, not a safe mutant: a replacement
     return that is POSITIVE contributes a zero square exactly as the
     positive return it replaced did, so there is nothing for the mutant to
     show.
   * So there is a **directed probe**: multiply every close from J onward by
     0.5. A power of two divides out of every later return bit-exactly, so
     exactly ONE return changes -- `r[J]`, which becomes about -0.5 and is
     therefore certainly a shortfall. Measured premise, not assumed: `r[J]`
     is a new, negative return at 36/36 J and no other return moves at all
     on any of the four frames. Every mutant is then caught at **36/36 on
     every frame**.

3. **That the divisor is the WINDOW and not the number of shortfalls**, which
   is the same decision as counting an up bar as a zero rather than dropping
   it. It is the reading a careless transcription gets wrong, it is not
   cosmetic -- max |difference| 1.2e-2 on a walk and 1.9e-2 on a 0.01 grid,
   Spearman 0.8707 and 0.8452 -- and on the hand window
   `[100, 50, 100, 100]` at length 3 it is the difference between
   sqrt(0.25/3) = 0.2887 and 0.5.

4. **Gate D: x8/x64 are bit-identical and x10/x3.7 are not, and by how
   much.** Only price RATIOS reach the result, and `8a / 8b` is the same
   double as `a / b`: 1,480 of 1,480 fired bars bit-identical at x8 and x64
   on each of a walk, a 0.01 grid and a skewed path. A non-power-of-two
   factor does not divide out, so x10/x3.7 agree to 7.2e-17 absolute and
   1.3e-14 relative with NaN masks equal -- and on the skewed frame, whose
   column takes only 37 distinct values, those last bits BREAK EXACT TIES, so
   Spearman falls to 0.9931 at x10 although no value moves by more than
   4.6e-17. That is the honest shape of the claim: bit-identical at a power
   of two, rank-stable elsewhere only where the column has no ties.

5. **What the column means, which is mostly volatility.** For iid returns
   with standard deviation s the population value is s / sqrt(2): over 2,000
   independent 20-return windows at s = 0.01 the median is 0.006683 against
   that population 0.007071 (sqrt of a mean is biased low). The level tracks
   s -- medians 0.003667 / 0.010897 / 0.028066 on three INDEPENDENT walks at
   sigma = 0.005 / 0.015 / 0.045, and 0.003442 / 0.010251 / 0.030097 on one
   seed-11 path scaled by sigma, where near-proportionality is close to an
   identity and is pinned as such -- its Spearman against the population
   standard deviation of the same 20 returns is 0.6356, and what it ADDS is
   asymmetry: two paths from the same two-point mixture with skew -2.80 and
   +2.80 (realised simple-return sd 0.014695 and 0.015324, so the
   up-skewed one is the MORE volatile) read medians 0.014444 and 0.004555, a
   ratio of 3.17. It does NOT order persistence: AR(1) medians are U-shaped
   in phi, which is the unconditional variance and not trend against
   reversion.

6. **The NaN shape and the guard bands, measured rather than asserted.** The
   warm-up is exactly `length` bars; `length` bars of history return `None`
   and `length + 1` fire exactly once, at bar `length`; `length` below 2
   falls back to 20; and a NaN, zero, negative, infinite or subnormal close
   empties exactly the 21 bars whose windows touch it -- after which two
   later bars move by at most 3.5e-18, which is `rolling.mean`'s
   accumulation restarting and is pinned rather than claimed away.

7. **That the column's ZERO is a reading and not missing data.** A rally and
   an exactly flat frame fire on all 280 of their complete windows and every
   value is exactly 0.0; on a frame built so that a huge squared shortfall
   leaves the window, no complete window comes out NaN and none of the 180
   means is below zero (which is why the module puts no floor under the
   square root), plus the five-point wiring.

Every number above comes from `docs/measure_lean_tdd_20.py`, whose run is
transcribed in `docs/LeanTdd20Measured.md`. Gate E is owed: the launcher
runs it after the porting session.
"""
import importlib
import math
import types

import numpy as np
import pandas as pd
import pytest
from pandas import Series

from .context import pandas_ta as ta
from pandas_ta.statistics.lean_tdd_20 import lean_tdd_20

LENGTH = 20
WARMUP = LENGTH          # bars 0 .. LENGTH-1; the first value is at bar LENGTH


def _walk(n=1500, seed=11, sigma=0.015):
    rng = np.random.default_rng(seed)
    return Series(100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n))))


def _tick_rounded(n=1500, seed=55, decimals=2):
    """Prices on a 0.01 grid, as real quotes are: the frame with exact ties,
    so returns that are exactly zero. A zero return is not a special case for
    this column -- it contributes a zero square like any up bar."""
    return Series(np.round(_walk(n, seed).to_numpy(), decimals))


def _rally(n=300, step=1.004):
    """Monotone up: every return is positive, so the column is EXACTLY zero
    on every complete window."""
    return Series(100.0 * step ** np.arange(n, dtype=float))


def _flat(n=300, level=50.0):
    return Series(np.full(n, float(level)))


def _ar1(n=1500, phi=0.0, seed=40, sigma=0.01):
    rng = np.random.default_rng(seed)
    eps = rng.normal(0.0, sigma, n)
    r = np.zeros(n)
    for i in range(1, n):
        r[i] = phi * r[i - 1] + eps[i]
    return Series(100.0 * np.exp(np.cumsum(r)))


def _skewed(n=1500, seed=23, sigma=0.015, sign=-1.0):
    """Returns from a two-point mixture, standardised to `sigma`, with the
    large moves on the down side at `sign=-1` and the up side at `+1`: the
    pair of frames that separates asymmetry from level."""
    rng = np.random.default_rng(seed)
    p = 0.1
    big = sigma * math.sqrt((1.0 - p) / p)
    small = sigma * math.sqrt(p / (1.0 - p))
    draw = rng.random(n) < p
    r = np.where(draw, sign * big, -sign * small)
    r = (r - r.mean()) / r.std(ddof=0) * sigma
    return Series(100.0 * np.exp(np.cumsum(r)))


def _cancellation(n=200, drop=0.5, step=1.001):
    """One -50% bar, then nothing but up bars: once the big square has left
    the window every square in it is exactly zero, which is where an
    add-and-remove accumulation could leave a residue either side of zero."""
    c = 100.0 * step ** np.arange(n, dtype=float)
    c[50:] = c[50:] * drop
    return Series(c)


def _zero_share(close):
    r = close / close.shift(1) - 1.0
    m = r.notna()
    return float((r[m] == 0.0).sum()) / max(int(m.sum()), 1)


# ------------------------------------------------------------- Gate A

HAND = [
    ([8.0, 4.0, 2.0, 1.0], 3, [None, None, None, 0.5]),
    ([100.0, 50.0, 100.0, 200.0, 100.0], 2,
     [None, None, math.sqrt(0.125), 0.0, math.sqrt(0.125)]),
    ([100.0, 50.0, 100.0, 100.0], 3,
     [None, None, None, math.sqrt(0.25 / 3.0)]),
]


@pytest.mark.parametrize("closes,length,want", HAND,
                         ids=["three_halvings", "one_down_one_up", "one_of_three"])
def test_hand_derived_windows_are_exact(closes, length, want):
    """Derived by hand, independent of any implementation, and compared
    BIT-for-bit rather than approximately.

    [8, 4, 2, 1] at length 3: three returns of exactly -0.5, so every square
    is 0.25, the mean is 0.25 and the root is EXACTLY 0.5.

    [100, 50, 100, 200, 100] at length 2: returns -0.5, +1, +1, -0.5, so the
    squares are 0.25, 0, 0, 0.25. The three windows are (0.25, 0) ->
    sqrt(0.125), (0, 0) -> EXACTLY 0.0 (a window with no down bar is zero,
    not missing), and (0, 0.25) -> sqrt(0.125).

    [100, 50, 100, 100] at length 3: returns -0.5, +1, 0. One shortfall in
    three returns, and the divisor is the WINDOW: sqrt(0.25/3) = 0.288675,
    where the shortfalls-only reading would say sqrt(0.25/1) = 0.5."""
    out = lean_tdd_20(Series(closes), length=length)
    assert out.name == f"LEAN_TDD_{length}"
    got = [None if v != v else float(v) for v in out.to_numpy()]
    assert got == want


def test_the_shortfall_count_divisor_is_a_different_hand_answer():
    """The same hand window, priced: 0.2887 against 0.5 is not a rounding."""
    out = lean_tdd_20(Series([100.0, 50.0, 100.0, 100.0]), length=3)
    assert float(out.iloc[3]) == math.sqrt(0.25 / 3.0)
    assert abs(float(out.iloc[3]) - math.sqrt(0.25 / 1.0)) == \
        pytest.approx(0.211325, abs=1e-6)


def _prototype(close, length=LENGTH):
    """`docs/issues/screen/ind_screen.py` candidate `lean_tdd_20`, retyped
    because that tree is gitignored:

        return np.sqrt(mean(ret(c).clip(upper=0) ** 2, 20))

    with the screen's operators `ret(c) = c / c.shift(1) - 1` and
    `mean(x, n) = x.rolling(n).mean()`."""
    c = close.astype(float)
    r = c / c.shift(1) - 1.0
    return np.sqrt((r.clip(upper=0.0) ** 2).rolling(length).mean())


@pytest.mark.parametrize("frame_fn", [_walk, _tick_rounded],
                         ids=["walk", "tick_rounded"])
def test_matches_the_screen_prototype(frame_fn):
    """Bit-equal, not merely close: the port is the column the screen's Gate
    E numbers were measured on."""
    close = frame_fn()
    base, proto = lean_tdd_20(close), _prototype(close)
    assert (base.isna() == proto.isna()).all()
    m = base.notna()
    assert int(m.sum()) == 1480
    assert (base[m] == proto[m]).all()


def _scalar_loop(close, length=LENGTH):
    """Independent per-window implementation in plain Python scalars: no
    pandas rolling, and the window summed by `math.fsum`, which is exact."""
    c = [float(v) for v in close.to_numpy()]
    out = [float("nan")] * len(c)
    tiny = 2.2250738585072014e-308  # float64 smallest normal

    def ok(v):
        return math.isfinite(v) and v >= tiny

    def shortfall(a, b):
        if not (ok(a) and ok(b)):
            return None
        d = b / a - 1.0
        return (d * d) if d < 0.0 else 0.0

    for t in range(length, len(c)):
        window = [shortfall(c[i - 1], c[i])
                  for i in range(t - length + 1, t + 1)]
        if any(v is None for v in window):
            continue
        out[t] = math.sqrt(math.fsum(window) / length)
    return Series(out, index=close.index)


@pytest.mark.parametrize("frame_fn,bit,rho", [(_walk, 304, 0.99999995),
                                              (_tick_rounded, 330, 0.99999989),
                                              (_rally, 380, None)],
                         ids=["walk", "tick_rounded", "rally"])
def test_matches_an_independent_scalar_loop(frame_fn, bit, rho):
    """The remaining gap is `rolling.mean`'s add-and-remove accumulation
    against an EXACT window sum, and it is bounded at 1.7e-18 absolute. The
    bit-equal counts are pinned (pandas 2.3.3, which CI pins) so a change in
    the accumulation is visible rather than silent; on the rally, where every
    square is exactly zero, the two agree on every bar and the column is
    constant, so no rank correlation is defined.

    The Spearman is 0.99999995, not 1: a 1.7e-18 difference is enough to
    break an exact tie between two windows, and it is pinned at that
    precision rather than rounded up to "identical"."""
    close = frame_fn(400, seed=5) if frame_fn is not _rally else _rally(400)
    base, loop = lean_tdd_20(close), _scalar_loop(close)
    assert (base.isna() == loop.isna()).all()
    m = base.notna()
    assert int(m.sum()) == 380
    assert float((base[m] - loop[m]).abs().max()) < 2e-18
    assert int((base[m] == loop[m]).sum()) == bit
    if rho is None:
        assert int(base[m].nunique()) == 1
    else:
        assert float(base[m].corr(loop[m], method="spearman")) == \
            pytest.approx(rho, abs=5e-8)


def _variant(close, length=LENGTH, divisor="window", window="returns",
             warmup="nan", ddof=0, spelling="minimum"):
    """The module's computation with ONE reading changed."""
    px = close.astype(float)
    r = px / px.shift(1) - 1.0
    if spelling == "minimum":
        s = np.minimum(r - 0.0, 0.0)
    elif spelling == "clip":
        s = r.clip(upper=0.0)
    elif spelling == "where":
        s = Series(np.where(r < 0.0, r, 0.0), index=r.index).where(r.notna())
    else:
        s = -((-r).clip(lower=0.0))
    sq = s ** 2
    width = length if window == "returns" else length - 1
    mp = 1 if warmup == "partial" else width

    if divisor == "shortfalls":
        total = sq.rolling(width, min_periods=mp).sum()
        fell = (r < 0.0).astype(float).rolling(width, min_periods=mp).sum()
        out = np.sqrt(total / fell.where(fell > 0))
        return out.where(r.rolling(width, min_periods=mp).count() == width)
    return np.sqrt(sq.rolling(width, min_periods=mp).sum() / (width - ddof))


@pytest.mark.parametrize("frame_fn,zeros,diff,rho", [
    (_walk, 0.0, 1.180243e-02, 0.870677),
    (_tick_rounded, 0.0027, 1.937484e-02, 0.845209),
], ids=["walk", "tick_rounded"])
def test_the_divisor_is_the_window_not_the_shortfall_count(frame_fn, zeros,
                                                           diff, rho):
    """The reading this port rejects: averaging only over the bars that fell
    short, which is the same thing as DROPPING the up bars instead of
    counting them as zeros. It is the one decision that changes the column's
    shape rather than its last bits."""
    close = frame_fn()
    assert _zero_share(close) == pytest.approx(zeros, abs=5e-5)
    base, other = lean_tdd_20(close), _variant(close, divisor="shortfalls")
    m = base.notna() & other.notna()
    assert int(m.sum()) == 1480
    assert float((base[m] - other[m]).abs().max()) == pytest.approx(diff,
                                                                    rel=1e-4)
    assert float(base[m].corr(other[m], method="spearman")) == \
        pytest.approx(rho, abs=1e-5)


@pytest.mark.parametrize("frame_fn,diff,rho", [
    (_walk, 5.969723e-03, 0.967733),
    (_tick_rounded, 4.461599e-03, 0.962543),
], ids=["walk", "tick_rounded"])
def test_the_window_holds_returns_not_closes(frame_fn, diff, rho):
    """`length` CLOSES is one return fewer, so it is a different column AND
    it fires one bar earlier -- it reads one close less of history."""
    close = frame_fn()
    base, other = lean_tdd_20(close), _variant(close, window="closes")
    m = base.notna() & other.notna()
    assert float((base[m] - other[m]).abs().max()) == pytest.approx(diff,
                                                                    rel=1e-4)
    assert float(base[m].corr(other[m], method="spearman")) == \
        pytest.approx(rho, abs=1e-5)
    assert int(base.notna().to_numpy().argmax()) == WARMUP
    assert int(other.notna().to_numpy().argmax()) == WARMUP - 1


def test_the_sample_divisor_is_a_different_value_and_the_same_ranking():
    """`length - 1` multiplies the whole column by sqrt(20/19), so no bar is
    bit-equal and the ranking is all but untouched: the choice is nearly
    invisible to anything that ranks the column and plainly visible to
    anything that reads its level. 0.99999999 rather than exactly 1, because
    the common factor is applied in floating point and that breaks exact
    ties."""
    close = _walk()
    base, other = lean_tdd_20(close), _variant(close, ddof=1)
    m = base.notna() & other.notna()
    assert int(m.sum()) == 1480
    assert float((base[m] - other[m]).abs().max()) == \
        pytest.approx(4.664010e-04, rel=1e-4)
    assert int((base[m] == other[m]).sum()) == 0
    assert float(base[m].corr(other[m], method="spearman")) > 0.9999999
    ratio = (other[m] / base[m].where(base[m] > 0)).dropna()
    assert float(ratio.max() - ratio.min()) < 1e-12
    assert float(ratio.median()) == pytest.approx(math.sqrt(20.0 / 19.0),
                                                  abs=1e-12)


def test_the_warmup_is_nan_rather_than_a_partial_window():
    """The rejected reading divides by the window's CURRENT count, so an
    unready indicator reads as a shorter window -- one plausible reading of
    an indicator before it is ready, and NOT a claim about Lean's code,
    which is not in this worktree and was not read. It would put 19 bars of
    a differently scaled statistic at the head of the column, which this
    fork's ML contract reads as data; after the warm-up the two agree
    bit-for-bit."""
    close = _walk()
    base, part = lean_tdd_20(close), _variant(close, warmup="partial")
    assert int(base.isna().sum()) == WARMUP
    assert int((base.isna() & part.notna()).sum()) == WARMUP - 1
    m = base.notna()
    assert int(m.sum()) == 1480
    assert (base[m] == part[m]).all()


@pytest.mark.parametrize("spelling", ["clip", "where", "negated"])
@pytest.mark.parametrize("frame_fn", [_walk, _tick_rounded, _rally],
                         ids=["walk", "tick_rounded", "rally"])
def test_the_spellings_of_the_shortfall_agree_bit_for_bit(frame_fn, spelling):
    """`np.minimum(r, 0)`, `r.clip(upper=0)`, `where(r < 0, r, 0)` and the
    negated upside are the same column on every frame, including the gridded
    one where returns are exactly zero -- so none of them is a reading."""
    close = frame_fn(1500) if frame_fn is _rally else frame_fn()
    base, other = lean_tdd_20(close), _variant(close, spelling=spelling)
    assert (base.isna() == other.isna()).all()
    m = base.notna()
    assert int(m.sum()) == 1480
    assert (base[m] == other[m]).all()


@pytest.mark.parametrize("frame_fn,complete,zeros", [
    (_cancellation, 180, 160), (_rally, 280, 280), (_flat, 280, 280),
], ids=["cancellation", "rally", "flat"])
def test_a_complete_window_is_never_nan_however_the_squares_cancel(
        frame_fn, complete, zeros):
    """Why the module puts NO floor under the square root. The squares are
    non-negative, so the mean cannot be negative in exact arithmetic, but
    `rolling.mean` adds and removes terms -- and a mean a few ulps BELOW zero
    would make `sqrt` NaN, turning "no downside at all" into missing data.
    Measured here instead of guarded. Only the `_cancellation` frame
    exercises the dangerous path -- a large square entering the window and
    then leaving it; on the rally and the flat frame every square is zero
    from the start, so the mean has nothing to cancel and those 560 windows
    are a floor rather than evidence. Across all three: 0 of the complete
    windows come out negative, the emptied ones (160 of 180 on
    `_cancellation`, 280 of 280 on each of the others) are EXACTLY zero
    rather than merely small, and no complete window is NaN. If a future
    pandas changed that, this test fails loudly rather than the column
    emptying in silence."""
    close = frame_fn()
    r = close / close.shift(1) - 1.0
    mean_sq = (np.minimum(r, 0.0) ** 2).rolling(LENGTH,
                                                min_periods=LENGTH).mean()
    done = mean_sq.notna()
    assert int(done.sum()) == complete
    assert int((mean_sq[done] < 0.0).sum()) == 0
    assert int((mean_sq[done] == 0.0).sum()) == zeros
    out = lean_tdd_20(close)
    assert int((done & out.isna()).sum()) == 0
    assert int((out.dropna() == 0.0).sum()) == zeros


# ------------------------------------------------------------- Gate B

_REAL = importlib.import_module("pandas_ta.statistics.lean_tdd_20")

MUTANTS = {
    "write_shift": (
        "    tdd = np.sqrt(mean_squared)",
        "    tdd = np.sqrt(mean_squared).shift(-length)"),
    "forward_return": (
        "    r = px / px.shift(1) - 1.0",
        "    r = px.shift(-1) / px - 1.0"),
    "forward_square": (
        "    squared = np.minimum(r - TARGET, 0.0) ** 2",
        "    squared = (np.minimum(r - TARGET, 0.0) ** 2).shift(-1)"),
    "centered_mean": (
        "    mean_squared = squared.rolling(length, min_periods=length).mean()",
        "    mean_squared = squared.rolling(length, min_periods=length, "
        "center=True).mean()"),
}
OFFSETS = range(60, 1500, 40)  # past the 20-bar warm-up
TOTAL = len(list(OFFSETS))
assert TOTAL == 36  # every count pinned below is out of this many J values

PAIRS = {
    "walk": (_walk(), _walk(seed=97)),
    "walk_vs_rally": (_walk(), _rally(1500)),
    "tick_rounded": (_tick_rounded(), _tick_rounded(seed=56)),
    "skewed_down": (_skewed(), _skewed(seed=24)),
}
FLIP_FRAMES = {
    "walk": _walk(),
    "rally": _rally(1500),
    "tick_rounded": _tick_rounded(),
    "skewed_down": _skewed(),
}

#: Measured catch counts of the PATH sweep, out of 36. The one-bar-ahead
#: mutants are missed wherever the replacement return is positive, because a
#: positive return contributes the same zero square as the positive return it
#: replaced -- a property of this probe on a one-sided column, which is why
#: the directed probe below exists. Pinned so a change in either direction is
#: visible.
PATH_SWEEP = {
    "write_shift": {"walk": 36, "walk_vs_rally": 36, "tick_rounded": 36,
                    "skewed_down": 35},
    "forward_return": {"walk": 36, "walk_vs_rally": 17, "tick_rounded": 14,
                       "skewed_down": 11},
    "forward_square": {"walk": 36, "walk_vs_rally": 17, "tick_rounded": 14,
                       "skewed_down": 11},
    "centered_mean": {"walk": 36, "walk_vs_rally": 36, "tick_rounded": 36,
                      "skewed_down": 31},
}


def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_lean_tdd_20_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


def _moved_before(base, out, j):
    a, b = base.iloc[:j], out.iloc[:j]
    if not (a.isna() == b.isna()).all():
        return True
    m = a.notna()
    return bool((a[m] != b[m]).any())


def _path_leaks(fn, close, other):
    """Replace every bar from J onward with a different path; count the J
    values at which anything strictly before J moves. Prefix truncation
    cannot see back-dating, which is why this is a perturbation sweep."""
    base = fn(close)
    hits = 0
    for j in OFFSETS:
        p = close.copy()
        p.iloc[j:] = other.iloc[j:].values
        if _moved_before(base, fn(p), j):
            hits += 1
    return hits


def _halve_tail(close, j):
    """Every close from `j` onward times 0.5. A power of two divides out of
    every later return bit-exactly, so exactly ONE return changes -- `r[j]`,
    which becomes about -0.5 and so is certainly a shortfall."""
    p = close.copy()
    p.iloc[j:] = close.iloc[j:].to_numpy() * 0.5
    return p


def _flip_leaks(fn, close):
    base = fn(close)
    hits = 0
    for j in OFFSETS:
        if _moved_before(base, fn(_halve_tail(close, j)), j):
            hits += 1
    return hits


def test_the_directed_probe_changes_exactly_one_return_into_a_shortfall():
    """The probe's own premise, measured: `r[J]` becomes a new NEGATIVE
    return at every J, and no other return changes at all -- on a walk, a
    rally with no down bar anywhere, a price grid and a skewed path."""
    for label, close in FLIP_FRAMES.items():
        r = close / close.shift(1) - 1.0
        for j in OFFSETS:
            p = _halve_tail(close, j)
            pr = p / p.shift(1) - 1.0
            assert float(pr.iloc[j]) < 0.0, f"{label} J={j}: not a shortfall"
            assert float(pr.iloc[j]) != float(r.iloc[j]), \
                f"{label} J={j}: the return did not change"
            rest = r.drop(index=r.index[j])
            prest = pr.drop(index=pr.index[j])
            m = rest.notna()
            assert (rest[m] == prest[m]).all(), \
                f"{label} J={j}: another return moved"


@pytest.mark.parametrize("frame", sorted(PAIRS))
def test_real_module_never_reads_the_future_under_the_path_sweep(frame):
    close, other = PAIRS[frame]
    assert _path_leaks(lean_tdd_20, close, other) == 0


@pytest.mark.parametrize("frame", sorted(FLIP_FRAMES))
def test_real_module_never_reads_the_future_under_the_directed_probe(frame):
    assert _flip_leaks(lean_tdd_20, FLIP_FRAMES[frame]) == 0


@pytest.mark.parametrize("frame", sorted(PAIRS))
@pytest.mark.parametrize("mutant", sorted(MUTANTS))
def test_each_mutant_is_caught_by_the_path_sweep(mutant, frame):
    """Live on every frame, and caught as often as it was measured to be.
    The one-bar-ahead mutants sit well below 36 on three frames because the
    probe can replace a positive return with another positive one;
    `test_each_mutant_is_caught_by_the_directed_probe` removes that."""
    mod = _load_mutant(*MUTANTS[mutant])
    close, other = PAIRS[frame]
    assert not mod.lean_tdd_20(close).equals(lean_tdd_20(close))
    assert _path_leaks(mod.lean_tdd_20, close, other) == \
        PATH_SWEEP[mutant][frame]


@pytest.mark.parametrize("frame", sorted(FLIP_FRAMES))
@pytest.mark.parametrize("mutant", sorted(MUTANTS))
def test_each_mutant_is_caught_by_the_directed_probe(mutant, frame):
    """36/36 on every frame for every mutant: a forced shortfall at J cannot
    be absorbed the way a random replacement can."""
    mod = _load_mutant(*MUTANTS[mutant])
    close = FLIP_FRAMES[frame]
    assert not mod.lean_tdd_20(close).equals(lean_tdd_20(close))
    assert _flip_leaks(mod.lean_tdd_20, close) == TOTAL


def test_a_positive_offset_only_delays_and_a_negative_one_is_the_callers_ask():
    """`offset` is this fork's standard parameter and a negative one is a
    user-reachable look-ahead -- the caller's explicit request, not a
    property of the formula, whose default `offset=0` the sweeps cover."""
    close = _walk(400, seed=3)
    base = lean_tdd_20(close)
    pd.testing.assert_series_equal(lean_tdd_20(close, offset=2),
                                   base.shift(2), check_names=False)
    pd.testing.assert_series_equal(lean_tdd_20(close, offset=-2),
                                   base.shift(-2), check_names=False)


# ------------------------------------------------------------- Gate D


@pytest.mark.parametrize("k", [8.0, 64.0])
@pytest.mark.parametrize("frame_fn", [_walk, _tick_rounded, _skewed],
                         ids=["walk", "tick_rounded", "skewed_down"])
def test_a_power_of_two_price_scale_is_bit_identical(frame_fn, k):
    """`8a / 8b` is the same double as `a / b`, so every square, every window
    mean and every root is the same bit pattern: 1,480 of 1,480 fired bars on
    each frame."""
    close = frame_fn()
    base, scaled = lean_tdd_20(close), lean_tdd_20(close * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert int(m.sum()) == 1480
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("k", [10.0, 3.7])
@pytest.mark.parametrize("frame_fn,rho_floor", [(_walk, 0.9999999),
                                                (_tick_rounded, 0.9999999),
                                                (_skewed, 0.99)],
                         ids=["walk", "tick_rounded", "skewed_down"])
def test_a_non_power_of_two_price_scale_agrees_to_rounding(frame_fn, rho_floor,
                                                           k):
    """Where the Gate D claim stops, and it is not hand-waved. A factor that
    is not a power of two does not divide out of `fl(k*a) / fl(k*b)`, so the
    column moves in its last bits: at most 7.2e-17 absolute and 1.3e-14
    relative (the measured worst cell is 1.218341e-14, the 0.01 grid at
    x3.7), NaN masks equal, Spearman 0.99999999 on the walk and the grid.
    On the skewed frame the column takes only 37 distinct values, so those
    last bits BREAK EXACT TIES and the rank correlation falls to 0.9931 at
    x10 and 0.9944 at x3.7 although no value moves by more than 4.6e-17 --
    which is why the rank floor is a parameter of this test rather than a
    constant."""
    close = frame_fn()
    base, scaled = lean_tdd_20(close), lean_tdd_20(close * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert int(m.sum()) == 1480
    # both bounds are the ones the docs state, not slack ones an order up
    assert float((base[m] - scaled[m]).abs().max()) < 7.2e-17
    rel = ((base[m] - scaled[m]).abs() / base[m].where(base[m] > 0)).max()
    assert float(rel) < 1.3e-14   # the bound stated in the docs, not a slack one
    assert float(base[m].corr(scaled[m], method="spearman")) >= rho_floor


def test_fires_and_is_not_constant():
    close = _walk()
    out = lean_tdd_20(close)
    fires = int(out.notna().sum())
    assert 0 < fires < len(close)
    assert fires == 1480
    assert int(out.nunique()) == 1094


# ------------------------------------------------- what the column means


def test_the_level_tracks_the_return_standard_deviation():
    """Two readings of the same claim, kept apart on purpose.

    The first three walks share seed 11, so they are ONE set of standard
    normals scaled by sigma -- common random numbers, which makes
    near-proportionality close to an identity (the only departure from
    1 : 3 : 9 is `exp`'s convexity on simple returns). Pinned anyway,
    because those are the medians the receipt transcribes.

    The second three are INDEPENDENT draws (seeds 101/102/103), which is the
    part that is evidence rather than algebra: 0.003667 / 0.010897 /
    0.028066, so the ratios are 2.97 and 2.58 -- the level tracks sigma
    without being pinned to it."""
    shared = [float(lean_tdd_20(_walk(sigma=s)).median())
              for s in (0.005, 0.015, 0.045)]
    assert shared == [pytest.approx(0.003442, abs=1e-6),
                      pytest.approx(0.010251, abs=1e-6),
                      pytest.approx(0.030097, abs=1e-6)]
    assert 2.8 < shared[1] / shared[0] < 3.2
    assert 2.8 < shared[2] / shared[1] < 3.2

    free = [float(lean_tdd_20(_walk(seed=101 + i, sigma=s)).median())
            for i, s in enumerate((0.005, 0.015, 0.045))]
    assert free == [pytest.approx(0.003667, abs=1e-6),
                    pytest.approx(0.010897, abs=1e-6),
                    pytest.approx(0.028066, abs=1e-6)]
    assert 2.0 < free[1] / free[0] < 4.0
    assert 2.0 < free[2] / free[1] < 4.0


def test_the_iid_level_is_sigma_over_root_two_and_biased_low():
    """For iid returns with standard deviation s the population value is
    s / sqrt(2) = 0.007071 at s = 0.01. The sqrt of a mean is biased low on a
    20-return window: median 0.006683 over 2,000 independent windows, above
    the population value on 40.75% of them. Pinned loosely -- the seed is
    fixed, the bounds are not tight."""
    rng = np.random.default_rng(123)
    sigma = 0.01
    paths = 100.0 * np.exp(np.cumsum(
        rng.normal(0.0, sigma, (2000, LENGTH + 1)), axis=1))
    est = np.array([float(lean_tdd_20(Series(p)).iloc[-1]) for p in paths])
    assert np.isfinite(est).all()
    assert (est >= 0.0).all()
    population = sigma / math.sqrt(2.0)
    assert float(np.median(est)) == pytest.approx(0.006683, abs=5e-6)
    assert float(np.median(est)) < population
    assert 0.35 < float((est > population).mean()) < 0.45


def test_the_skew_is_what_it_adds_over_volatility():
    """Two paths from the same two-point mixture with opposite skew. The
    up-skewed one is the slightly MORE volatile of the two by realised
    simple-return standard deviation, and the column still reads 3.17 times
    lower on it -- so what the column carries over a standard deviation is
    asymmetry, not level."""
    down, up = _skewed(sign=-1.0), _skewed(sign=+1.0)
    sd_down = float((down / down.shift(1) - 1.0).dropna().std(ddof=0))
    sd_up = float((up / up.shift(1) - 1.0).dropna().std(ddof=0))
    assert sd_down == pytest.approx(0.01469475, abs=1e-7)
    assert sd_up == pytest.approx(0.01532414, abs=1e-7)
    assert sd_up > sd_down
    a = float(lean_tdd_20(down).median())
    b = float(lean_tdd_20(up).median())
    assert a == pytest.approx(0.014444, abs=1e-6)
    assert b == pytest.approx(0.004555, abs=1e-6)
    assert a / b == pytest.approx(3.1712, abs=1e-3)


def test_it_does_not_order_persistence():
    """Unlike `lean_hurst_100` or `lean_momersion_20`, this column says
    nothing about trend against reversion: AR(1) returns driven by ONE set of
    innovations read U-shaped in phi, because +-0.8 both inflate the
    unconditional variance. Pinned so nobody reads it as a persistence
    feature."""
    medians = [float(lean_tdd_20(_ar1(phi=phi, seed=40)).median())
               for phi in (0.8, 0.4, -0.4, -0.8)]
    assert medians == [pytest.approx(0.009389, abs=1e-6),
                       pytest.approx(0.007593, abs=1e-6),
                       pytest.approx(0.007902, abs=1e-6),
                       pytest.approx(0.011441, abs=1e-6)]
    assert medians[0] > medians[1] and medians[3] > medians[2]


def test_drift_moves_the_level_but_barely_the_ranks():
    """Drift makes down bars rarer and smaller, so the level falls: max
    |difference| 3.1e-3 against the same walk at +0.004 of log drift a bar.
    The ranking is nearly untouched (Spearman 0.9914), which is the honest
    statement -- the column is not drift-invariant, and it is not re-ordered
    by this much drift either."""
    close = _walk()
    drifted = Series(close.to_numpy() * np.exp(0.004 * np.arange(len(close))))
    base, out = lean_tdd_20(close), lean_tdd_20(drifted)
    assert (base.isna() == out.isna()).all()
    m = base.notna()
    assert float((base[m] - out[m]).abs().max()) == \
        pytest.approx(3.121724e-03, rel=1e-4)
    assert float(base[m].corr(out[m], method="spearman")) == \
        pytest.approx(0.991447, abs=1e-5)
    assert float(out[m].median()) < float(base[m].median())


# -------------------------------------------------------- edge, guards


@pytest.mark.parametrize("frame_fn", [_rally, _flat], ids=["rally", "flat"])
def test_a_frame_with_no_down_bar_is_exactly_zero_and_not_nan(frame_fn):
    """The zero is a reading: no downside in the window means a deviation of
    zero, where a share or a ratio would have to be NaN."""
    out = lean_tdd_20(frame_fn())
    assert int(out.notna().sum()) == 280
    assert (out.dropna() == 0.0).all()


def test_insufficient_history_returns_none():
    assert lean_tdd_20(_walk(LENGTH)) is None


def test_exact_min_length_fires_once_at_the_warmup_boundary():
    out = lean_tdd_20(_walk(LENGTH + 1, seed=2))
    assert int(out.notna().sum()) == 1
    assert int(out.notna().to_numpy().argmax()) == WARMUP


@pytest.mark.parametrize("bad", [np.nan, 0.0, -5.0, np.inf, 1e-310])
def test_a_bad_close_empties_its_own_windows_and_leaves_a_tiny_residue(bad):
    """NaN, zero, negative, infinite and subnormal closes are all missing
    data. A bad close at bar 200 kills the return into it and the return out
    of it, so it empties the 21 windows 200..220. Two LATER bars then move,
    by at most 3.5e-18 (measured 3.469e-18; 2.449e-16 relative, which the
    assert below rounds up to 2.5e-16): that is `rolling.mean`'s
    accumulation restarting after the hole, and it is pinned rather than
    described as "nothing else moves", which would be false."""
    close = _walk(400, seed=21)
    base = lean_tdd_20(close)
    holed = close.copy()
    holed.iloc[200] = bad
    out = lean_tdd_20(holed)
    emptied = np.flatnonzero((base.notna() & out.isna()).to_numpy())
    assert len(emptied) == LENGTH + 1
    assert (int(emptied.min()), int(emptied.max())) == (200, 220)
    shared = base.notna() & out.notna()
    moved = shared & (base != out)
    assert int(moved.sum()) == 2
    assert int(np.flatnonzero(moved.to_numpy()).min()) > 220
    # both residues pinned at the measured size, not an order up
    assert float((base[moved] - out[moved]).abs().max()) < 3.5e-18
    rel = ((base[moved] - out[moved]).abs() / base[moved]).max()
    assert float(rel) < 2.5e-16


@pytest.mark.parametrize("length", [None, 0, -5, 1, 0.5, 1.9])
def test_a_length_below_the_minimum_falls_back_to_the_default(length):
    out = lean_tdd_20(_walk(400, seed=31), length=length)
    assert out.name == "LEAN_TDD_20"
    assert int(out.notna().sum()) == 380


@pytest.mark.parametrize("length", [2, 2.9])
def test_the_smallest_accepted_length_is_two(length):
    """`int()` truncation is the rule, so 2.9 is accepted AS 2 rather than
    falling back to the default -- the complement of the row above, which is
    only about fractions that truncate BELOW 2."""
    out = lean_tdd_20(_walk(400, seed=31), length=length)
    assert out.name == "LEAN_TDD_2"
    assert int(out.notna().sum()) == 398


def test_fractional_lengths_that_truncate_the_same_are_identical():
    close = _walk(400, seed=31)
    pd.testing.assert_series_equal(lean_tdd_20(close, length=50.9),
                                   lean_tdd_20(close, length=50))


def test_distinct_lengths_produce_distinct_names_and_values():
    close = _walk(1500, seed=31)
    a, b = lean_tdd_20(close, length=10), lean_tdd_20(close, length=60)
    assert (a.name, b.name) == ("LEAN_TDD_10", "LEAN_TDD_60")
    m = a.notna() & b.notna()
    assert int(m.sum()) > 1000
    assert float(a[m].corr(b[m], method="spearman")) < 0.9


def test_a_length_that_needs_more_closes_than_the_frame_has_returns_none():
    close = _walk(400, seed=31)
    longest = lean_tdd_20(close, length=399)
    assert longest.name == "LEAN_TDD_399"
    assert int(longest.notna().sum()) == 1
    assert lean_tdd_20(close, length=400) is None


def test_fillna_applies():
    out = lean_tdd_20(_walk(200, seed=13), fillna=-1.0)
    assert int((out == -1.0).sum()) == WARMUP


# ------------------------------------------------------------- wiring


def test_name_registration_and_accessor():
    close = _walk(300, seed=17)
    df = pd.DataFrame({"open": close, "high": close * 1.01,
                       "low": close * 0.99, "close": close,
                       "volume": Series(np.full(len(close), 1000.0))})
    assert "lean_tdd_20" in ta.Category["statistics"]
    assert hasattr(df.ta, "lean_tdd_20")
    direct = lean_tdd_20(close)
    through = df.ta.lean_tdd_20()
    pd.testing.assert_series_equal(through, direct, check_names=True)
    assert through.name == "LEAN_TDD_20"
    assert direct.category == "statistics"
