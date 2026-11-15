# -*- coding: utf-8 -*-
"""LEAN-MOMERSION-20: `lean_momersion_20`, Gilles' Momersion index
(PandasTa issue #86).

    LEAN_MOMERSION_20 = 100 * MC / (MC + MRC) over a window of 20 pairs of
                        consecutive return SIGNS; MC = same sign, MRC =
                        opposite; a zero return is in neither.

WHAT THIS FILE PINS, in order of how much it would hurt to lose.

1. **Gate A, and that the formula under test is the ISSUE's line, not
   Lean's code.** QuantConnect Lean's `MomersionIndicator` C# source is NOT
   in this worktree and web access is unavailable, so "Apache-2.0 Lean" is an
   attribution, not an oracle. What IS checkable is pinned three ways:

   * three hand-derived windows whose answer is exact integer arithmetic --
     2/4 then 1/4 of a four-pair window; a flat-bar frame where the
     denominator shrinks to 1, 2, 2, 1; and a window whose every pair is
     flat, which is NaN (`test_hand_derived_windows_are_exact`);
   * the screen prototype of `docs/issues/screen/ind_screen.py` (candidate
     `lean_momersion_20`), retyped here because that file is gitignored:
     Spearman 1.000000, max |difference| 7.1e-15, NaN masks equal over
     1,479 fired bars of a 1,500-bar walk. The 7.1e-15 is one rounding, not
     a disagreement: the prototype spells the value `100 * (MC / (MC+MRC))`
     and the module `100 * MC / (MC + MRC)`, as the source formula writes
     it, which rounds once instead of twice -- 1,198 of 1,479 bars are
     bit-equal and the rest differ in the last bits;
   * an independent per-window loop in plain Python scalars -- no numpy, no
     pandas rolling: **bit-equal on 379 of 379 bars**, on a continuous walk
     and on a tick-rounded one.

2. **Gate B, by mutant, and the reason this column needs TWO probes.** Four
   mutants, each `importlib`-read and `exec`'d in memory: the column
   back-dated by `length`; the pair taken forward (`shift(-1)`); the return
   taken forward; and a `center=True` rolling count. The real module leaks at
   **0/36** on every frame of both probes.
   * The usual path sweep (replace every bar from J onward with a different
     path) catches the back-dating mutants at 36/36 but the ONE-BAR-ahead
     mutants at only 19/36 (walk) and 11-12/36 (price grids). That is the
     PROBE, not a safe mutant: the column reads only signs, and a fresh
     random path repeats the sign it replaced about half the time.
   * So there is a **directed probe**: multiply every close from J onward by
     0.5 or 2.0, whichever CHANGES the sign of `r[J]` -- a reversal where
     the return is nonzero, flat -> up where it is zero. A power of two
     divides out of every later return bit-exactly, so exactly ONE return
     changes. Every mutant is then caught at **36/36** on a walk, on an
     alternating path and on a 0.01 grid, and at 27-33/36 on a 0.5 grid,
     where a flat bar at J-1 absorbs the flip.

3. **That a zero return is counted in NEITHER MC nor MRC** -- the reading
   `if (p > 0) MC++ else MRC++` would put every flat bar into mean reversion.
   It is not cosmetic and it is not visible on a continuous frame: the two
   readings are bit-equal on a walk (seed 11, no exact ties), differ by max
   5.5556 (Spearman 0.9974) on a SECOND walk (seed 55) rounded to 0.01, and
   by max 55.7143 (Spearman 0.8399) on that same seed-55 walk on a 0.5 grid,
   where 14.01% of returns are zero. Real quotes are a grid, so this is the
   reading that decides the column.

4. **Gate D, that x10 is bit-identical and not merely close, AND where that
   stops.** Only the SIGN of a price ratio reaches the counts, and
   multiplying every close by a positive constant can neither reorder two
   closes (`fl(k*x)` is monotone) nor separate two equal ones: 1,479 of
   1,479 fired bars
   bit-identical at x8, x64, x10 AND x3.7, on each of a walk, a 0.01 grid
   and a 0.5 grid. The bound is pinned too, and its cause is FUSION rather
   than the division: the ratio of two distinct doubles never rounds to
   exactly 1.0, but a non-power-of-two `k` can round two closes ONE ULP
   apart to the same double, which turns a signed pair flat. On a frame of
   adjacent doubles, x8/x64 fuse 0 of 299 pairs and stay bit-identical,
   while x10 fuses 58 (19.40% zero returns) and agrees on 141 of 279 bars
   and x3.7 fuses 10 (3.34%) and agrees on 224
   (`test_the_scale_free_claim_stops_at_one_ulp_moves`). Only closes exactly
   ONE ulp apart can fuse: the scaled gap is `g * k * 2**(e - f)` ulps of
   the product's binade with the factor confined to (1/2, 2), the widest
   fusion window is 1.5 ulp (at a power of two, where half the spacing below
   and half the spacing above both round to it), and `g = 2` lands outside
   even that -- fusing at a power of two forces the factor above
   `1 - 2**-54`. No price feed comes near: one tick over the price is 1e-9
   even at a price of 1e6, seven orders above an ulp.

5. **What the column means.** Discrete: 129 reachable values at
   `length=20`, but on a tie-free frame the denominator is always 20, so the
   value is a multiple of 5 (14 distinct over the seed-11 walk; 25 and 87 on
   the seed-55 walk at 0.01 and on a 0.5 grid, which is a comparison between
   grids and not within one path). Unbiased in
   the median for iid returns (median 50.0000 over 2,000 independent
   windows, mean 50.1300, sd 11.2276, p10 35, p90 65) and wide, so one
   reading says little. It orders persistence: AR(1) medians 80 / 65 / 35 /
   20 at phi = +0.8 / +0.4 / -0.4 / -0.8 (one seed for all four, so it is a
   controlled comparison), 50 on an iid gaussian walk, and 0.0000 on every
   one of the 1,479 fired bars of a hard alternating path. NOT drift-invariant
   (Spearman 0.3829 against the same walk with drift) -- unlike most of this
   fork's window statistics, which is worth knowing before reading it as a
   regime measure.

6. **The guard bands and the NaN shape, measured rather than asserted.**
   `length` below 2 (including 0, negatives and fractions that truncate
   below 2) falls back to 20; 21 bars return `None` and 22 bars fire exactly
   once, at bar 21; a NaN, zero, negative, infinite or subnormal close
   empties exactly the 22 bars whose pairs touch it and moves **nothing
   else at all** -- the counts are integers, so there is no accumulation
   drift either side of the hole.

7. **Five-point wiring** (`Category`, the accessor, the export) and that a
   window with no signed pair is NaN rather than 50 or 0: an exactly flat
   frame fires 0/300, and so does a staircase stepping once every 10 bars,
   whose 0 of 298 known pairs are signed.

Every number above comes from `docs/measure_lean_momersion_20.py`, whose run
is transcribed in `docs/LeanMomersion20Measured.md`. Gate E is owed: the
launcher runs it after the porting session.
"""
import importlib
import math
import types

import numpy as np
import pandas as pd
import pytest
from pandas import Series

from .context import pandas_ta as ta
from pandas_ta.momentum.lean_momersion_20 import lean_momersion_20

LENGTH = 20
WARMUP = LENGTH + 1


def _walk(n=1500, seed=11, sigma=0.015):
    rng = np.random.default_rng(seed)
    return Series(100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n))))


def _tick_rounded(n=1500, seed=55, decimals=2):
    """Prices on a 0.01 grid, as real quotes are: the frame that has exact
    ties, so zero returns, so pairs that count neither way."""
    return Series(np.round(_walk(n, seed).to_numpy(), decimals))


def _coarse_grid(n=1500, seed=55, step=0.5):
    """A coarser grid still, where flat bars are common rather than rare."""
    return Series(np.round(_walk(n, seed).to_numpy() / step) * step)


def _alternating(n=1500, seed=7, step=0.01, noise=0.001):
    rng = np.random.default_rng(seed)
    r = np.where(np.arange(n) % 2 == 0, 1.0, -1.0) * step \
        + rng.normal(0.0, noise, n)
    return Series(100.0 * np.exp(np.cumsum(r)))


def _ar1(n=1500, phi=0.0, seed=40, sigma=0.01):
    rng = np.random.default_rng(seed)
    eps = rng.normal(0.0, sigma, n)
    r = np.zeros(n)
    for i in range(1, n):
        r[i] = phi * r[i - 1] + eps[i]
    return Series(100.0 * np.exp(np.cumsum(r)))


def _zero_share(close):
    r = close / close.shift(1) - 1.0
    m = r.notna()
    return float((r[m] == 0.0).sum()) / max(int(m.sum()), 1)


# ------------------------------------------------------------- Gate A

HAND = [
    ([100.0, 101.0, 102.0, 101.0, 103.0, 104.0, 103.0], 4,
     [None, None, None, None, None, 50.0, 25.0]),
    ([10.0, 11.0, 11.0, 12.0, 13.0, 12.0, 12.0, 13.0], 3,
     [None, None, None, None, 100.0, 50.0, 50.0, 0.0]),
    ([10.0, 11.0, 11.0, 11.0, 11.0], 3,
     [None, None, None, None, None]),
]


@pytest.mark.parametrize("closes,length,want", HAND,
                         ids=["four_pairs", "flat_bars", "all_pairs_flat"])
def test_hand_derived_windows_are_exact(closes, length, want):
    """Derived by hand, independent of any implementation.

    [100, 101, 102, 101, 103, 104, 103]: return signs + + - + + -, so pairs
    + - - + -. A 4-pair window first fills at bar 5 (pairs at bars 2..5 =
    +, -, -, +) -> MC 2, MRC 2 -> 50; at bar 6 (pairs -, -, +, -) -> 1/4 ->
    25.

    [10, 11, 11, 12, 13, 12, 12, 13]: returns + 0 + + - 0 +, so pairs
    0 0 + - 0 0. With length 3 the windows ending at bars 4..7 hold
    (0, 0, +), (0, +, -), (+, -, 0), (-, 0, 0): the zero pairs count
    NEITHER way, so the denominators are 1, 2, 2, 1 and the column is
    100, 50, 50, 0.

    [10, 11, 11, 11, 11]: every pair in the only full window is flat, so
    MC + MRC == 0 and there is no share to report: NaN."""
    out = lean_momersion_20(Series(closes), length=length)
    assert out.name == f"LEAN_MOMERSION_{length}"
    got = [None if v != v else float(v) for v in out.to_numpy()]
    assert got == want


def _prototype(close, length=LENGTH):
    """`docs/issues/screen/ind_screen.py` candidate `lean_momersion_20`,
    retyped because that tree is gitignored:

        p = ret(c) * delay(ret(c), 1)
        mc, mrc = count(p > 0, 20), count(p < 0, 20)
        return 100 * sdiv(mc, mc + mrc).where(p.shift(19).notna())
    """
    c = close.astype(float)
    r = c / c.shift(1) - 1.0
    p = r * r.shift(1)
    mc = (p > 0).astype(float).rolling(length).sum()
    mrc = (p < 0).astype(float).rolling(length).sum()
    out = (mc / (mc + mrc)).replace([np.inf, -np.inf], np.nan)
    return 100 * out.where(p.shift(length - 1).notna())


def test_matches_the_screen_prototype():
    close = _walk()
    base, proto = lean_momersion_20(close), _prototype(close)
    assert (base.isna() == proto.isna()).all()
    m = base.notna()
    assert int(m.sum()) == 1479
    assert float((base[m] - proto[m]).abs().max()) < 1e-13
    assert float(base[m].corr(proto[m], method="spearman")) >= 1.0 - 1e-12
    # the module's spelling rounds once, the prototype's twice
    assert int((base[m] == proto[m]).sum()) == 1198


def _scalar_loop(close, length=LENGTH):
    """Independent per-window implementation in plain Python scalars: no
    numpy, no pandas rolling, the counts written out."""
    c = [float(v) for v in close.to_numpy()]
    out = [float("nan")] * len(c)
    tiny = 2.2250738585072014e-308

    def sign_of(a, b):
        if not (math.isfinite(a) and a >= tiny
                and math.isfinite(b) and b >= tiny):
            return None
        d = b / a - 1.0
        return 0 if d == 0.0 else (1 if d > 0.0 else -1)

    for t in range(length + 1, len(c)):
        mc = mrc = known = 0
        for i in range(t - length + 1, t + 1):
            s1, s2 = sign_of(c[i - 2], c[i - 1]), sign_of(c[i - 1], c[i])
            if s1 is None or s2 is None:
                continue
            known += 1
            if s1 * s2 > 0:
                mc += 1
            elif s1 * s2 < 0:
                mrc += 1
        if known == length and mc + mrc > 0:
            out[t] = 100.0 * mc / (mc + mrc)
    return Series(out, index=close.index)


@pytest.mark.parametrize("frame_fn", [_walk, _tick_rounded],
                         ids=["walk", "tick_rounded"])
def test_matches_an_independent_scalar_loop(frame_fn):
    close = frame_fn(400, seed=5)
    base, loop = lean_momersion_20(close), _scalar_loop(close)
    assert (base.isna() == loop.isna()).all()
    m = base.notna()
    assert int(m.sum()) == 379
    assert (base[m] == loop[m]).all()  # bit-equal, not merely close


def _variant(close, length=LENGTH, zeros="neither", window="pairs",
             warmup=None, spelling="ratio", pair_form="signs"):
    """The module's computation with ONE reading changed."""
    px = close.astype(float)
    if spelling == "ratio":
        r = px / px.shift(1) - 1.0
    elif spelling == "log":
        r = np.log(px / px.shift(1))
    else:
        r = px.diff()
    p = np.sign(r) * np.sign(r).shift(1) if pair_form == "signs" \
        else r * r.shift(1)
    width = length if window == "pairs" else length - 1

    def cnt(mask):
        return mask.astype(float).rolling(width, min_periods=width).sum()

    mc = cnt(p > 0)
    mrc = cnt(p < 0) if zeros == "neither" else cnt(p.notna() & ~(p > 0))
    total = mc + mrc
    # emptying the denominator first means no zero reaches the division
    out = 100.0 * mc / total.where(total > 0)
    out = out.where(cnt(p.notna()) == width)
    if warmup is not None:
        out.iloc[:int(out.notna().to_numpy().argmax())] = warmup
    return out


@pytest.mark.parametrize("frame_fn,zeros,diff,rho", [
    (_walk, 0.0, 0.0, 1.0),                    # no exact ties: bit-equal
    (_tick_rounded, 0.0027, 5.555556, 0.997355),
    (_coarse_grid, 0.1401, 55.714286, 0.839877),
], ids=["walk", "tick_rounded", "coarse_grid"])
def test_a_zero_return_counts_neither_way(frame_fn, zeros, diff, rho):
    """The reading this port rejects -- `if (p > 0) MC++ else MRC++`, which
    puts every flat bar into MEAN REVERSION. Invisible on a continuous
    frame and decisive on a price grid, which is what real quotes are."""
    close = frame_fn()
    assert _zero_share(close) == pytest.approx(zeros, abs=5e-5)
    base, other = lean_momersion_20(close), _variant(close, zeros="reversion")
    m = base.notna() & other.notna()
    assert int(m.sum()) == 1479
    assert float((base[m] - other[m]).abs().max()) == pytest.approx(diff, abs=1e-4)
    assert float(base[m].corr(other[m], method="spearman")) == \
        pytest.approx(rho, abs=1e-5)


def test_the_window_holds_pairs_not_returns():
    """`length` RETURNS is one pair fewer, so it is a different column AND it
    fires one bar earlier -- it reads one close less of history."""
    close = _walk()
    base, other = lean_momersion_20(close), _variant(close, window="returns")
    m = base.notna() & other.notna()
    assert float((base[m] - other[m]).abs().max()) == pytest.approx(4.473684,
                                                                   abs=1e-4)
    assert float(base[m].corr(other[m], method="spearman")) == \
        pytest.approx(0.968501, abs=1e-5)
    assert int(base.notna().to_numpy().argmax()) == WARMUP
    assert int(other.notna().to_numpy().argmax()) == WARMUP - 1


@pytest.mark.parametrize("kwargs", [{"spelling": "log"}, {"spelling": "diff"},
                                    {"pair_form": "product"}],
                         ids=["log_returns", "price_differences",
                              "product_of_returns"])
@pytest.mark.parametrize("frame_fn", [_walk, _tick_rounded, _coarse_grid],
                         ids=["walk", "tick_rounded", "coarse_grid"])
def test_the_spellings_of_the_pair_agree_bit_for_bit(frame_fn, kwargs):
    """Only the SIGN of the return reaches the counts, so the log return,
    the raw price difference and the product of the returns themselves (the
    prototype's spelling) are the same column -- bit-for-bit, on all three
    frames. The module takes the sign of a ratio because that is the
    issue's wording and because the ratio is what makes Gate D exact."""
    close = frame_fn()
    base, other = lean_momersion_20(close), _variant(close, **kwargs)
    assert (base.isna() == other.isna()).all()
    m = base.notna()
    assert int(m.sum()) == 1479
    assert (base[m] == other[m]).all()


def test_the_warmup_is_nan_rather_than_the_neutral_fifty():
    """Some implementations emit 50 until the window fills. That is 21 bars
    of a CONSTANT at the head of the column, which this fork's ML contract
    reads as a value; after the warm-up the two agree everywhere."""
    close = _walk()
    base, fifty = lean_momersion_20(close), _variant(close, warmup=50.0)
    assert int(base.isna().sum()) == WARMUP
    assert int((base.isna() & fifty.notna()).sum()) == WARMUP
    assert int((fifty.iloc[:WARMUP] == 50.0).sum()) == WARMUP
    m = base.notna()
    assert (base[m] == fifty[m]).all()


# ------------------------------------------------------------- Gate B

_REAL = importlib.import_module("pandas_ta.momentum.lean_momersion_20")

WRITE_SHIFT_MUTANT = (
    "    momersion = values.where(count(pair.notna()) == length)",
    "    momersion = values.where(count(pair.notna()) == length).shift(-length)")
FORWARD_PAIR_MUTANT = (
    "    pair = np.sign(r) * np.sign(r).shift(1)",
    "    pair = np.sign(r) * np.sign(r).shift(-1)")
FORWARD_RETURN_MUTANT = (
    "    r = px / px.shift(1) - 1.0",
    "    r = px.shift(-1) / px - 1.0")
CENTERED_COUNT_MUTANT = (
    "        return mask.astype(float).rolling(length, min_periods=length).sum()",
    "        return mask.astype(float).rolling(length, min_periods=length, "
    "center=True).sum()")

MUTANTS = {
    "write_shift": WRITE_SHIFT_MUTANT,
    "forward_pair": FORWARD_PAIR_MUTANT,
    "forward_return": FORWARD_RETURN_MUTANT,
    "centered_count": CENTERED_COUNT_MUTANT,
}
OFFSETS = range(60, 1500, 40)  # past the 21-bar warm-up
TOTAL = len(list(OFFSETS))
assert TOTAL == 36  # every count pinned below is out of this many J values

PAIRS = {
    "walk": (_walk(), _walk(seed=97)),
    "walk_vs_alternating": (_walk(), _alternating()),
    "tick_rounded": (_tick_rounded(), _tick_rounded(seed=56)),
    "coarse_grid": (_coarse_grid(), _coarse_grid(seed=56)),
}
FLIP_FRAMES = {
    "walk": _walk(),
    "alternating": _alternating(),
    "tick_rounded": _tick_rounded(),
    "coarse_grid": _coarse_grid(),
}

#: Measured catch counts of the PATH sweep, out of 36. The one-bar-ahead
#: mutants are caught about half the time because a fresh random path
#: repeats the sign it replaced about half the time -- a property of this
#: probe on a sign-driven column, which is why the directed probe below
#: exists. Pinned so a change in either direction is visible.
PATH_SWEEP = {
    "write_shift": {"walk": 36, "walk_vs_alternating": 36,
                    "tick_rounded": 36, "coarse_grid": 36},
    "forward_pair": {"walk": 19, "walk_vs_alternating": 19,
                     "tick_rounded": 12, "coarse_grid": 11},
    "forward_return": {"walk": 19, "walk_vs_alternating": 19,
                       "tick_rounded": 12, "coarse_grid": 11},
    "centered_count": {"walk": 36, "walk_vs_alternating": 36,
                       "tick_rounded": 35, "coarse_grid": 36},
}
#: Measured catch counts of the DIRECTED probe, out of 36. Only the 0.5
#: grid misses any J, and there the reason is known: a flat bar at J - 1
#: makes the pair zero whichever way r[J] points, so the flip is absorbed.
DIRECTED = {
    "write_shift": {"walk": 36, "alternating": 36, "tick_rounded": 36,
                    "coarse_grid": 33},
    "forward_pair": {"walk": 36, "alternating": 36, "tick_rounded": 36,
                     "coarse_grid": 27},
    "forward_return": {"walk": 36, "alternating": 36, "tick_rounded": 36,
                       "coarse_grid": 27},
    "centered_count": {"walk": 36, "alternating": 36, "tick_rounded": 36,
                       "coarse_grid": 33},
}


def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_lean_momersion_20_mutant")
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


def _flip_tail(close, j):
    """Every close from `j` onward times 0.5 or 2.0, whichever CHANGES the
    sign of `r[j]` -- a reversal where `r[j] != 0`, and flat → up where it
    is zero. A power of two divides out of every later return bit-exactly,
    so this changes EXACTLY ONE return."""
    k = 0.5 if float(close.iloc[j]) > float(close.iloc[j - 1]) else 2.0
    p = close.copy()
    p.iloc[j:] = close.iloc[j:].to_numpy() * k
    return p


def _flip_leaks(fn, close):
    base = fn(close)
    hits = 0
    for j in OFFSETS:
        if _moved_before(base, fn(_flip_tail(close, j)), j):
            hits += 1
    return hits


def test_the_directed_probe_really_flips_exactly_one_return():
    """The probe's own premise, measured: the sign of `r[J]` changes at
    every J, and no other return changes at all. On the grid frames a zero
    `r[J]` becomes positive rather than reversing, which is a change of
    sign all the same -- and part of why the 0.5 grid catches fewer J."""
    for label, close in FLIP_FRAMES.items():
        r = close / close.shift(1) - 1.0
        for j in OFFSETS:
            p = _flip_tail(close, j)
            pr = p / p.shift(1) - 1.0
            assert np.sign(float(pr.iloc[j])) != np.sign(float(r.iloc[j])), \
                f"{label} J={j}: the sign did not reverse"
            rest = r.drop(index=r.index[j])
            prest = pr.drop(index=pr.index[j])
            m = rest.notna()
            assert (rest[m] == prest[m]).all(), \
                f"{label} J={j}: another return moved"


@pytest.mark.parametrize("frame", sorted(PAIRS))
def test_real_module_never_reads_the_future_under_the_path_sweep(frame):
    close, other = PAIRS[frame]
    assert _path_leaks(lean_momersion_20, close, other) == 0


@pytest.mark.parametrize("frame", sorted(FLIP_FRAMES))
def test_real_module_never_reads_the_future_under_the_directed_probe(frame):
    assert _flip_leaks(lean_momersion_20, FLIP_FRAMES[frame]) == 0


@pytest.mark.parametrize("frame", sorted(PAIRS))
@pytest.mark.parametrize("mutant", sorted(MUTANTS))
def test_each_mutant_is_caught_by_the_path_sweep(mutant, frame):
    """Live on every frame, and caught as often as it was measured to be.
    The one-bar-ahead mutants sit near half the J values because the probe
    replaces a sign with a random one; `test_each_mutant_is_caught_by_the_
    directed_probe` is the one that removes that coin flip."""
    mod = _load_mutant(*MUTANTS[mutant])
    close, other = PAIRS[frame]
    assert not mod.lean_momersion_20(close).equals(lean_momersion_20(close))
    assert _path_leaks(mod.lean_momersion_20, close, other) == \
        PATH_SWEEP[mutant][frame]


@pytest.mark.parametrize("frame", sorted(FLIP_FRAMES))
@pytest.mark.parametrize("mutant", sorted(MUTANTS))
def test_each_mutant_is_caught_by_the_directed_probe(mutant, frame):
    mod = _load_mutant(*MUTANTS[mutant])
    close = FLIP_FRAMES[frame]
    assert not mod.lean_momersion_20(close).equals(lean_momersion_20(close))
    assert _flip_leaks(mod.lean_momersion_20, close) == DIRECTED[mutant][frame]


def test_a_positive_offset_only_delays_and_a_negative_one_is_the_callers_ask():
    """`offset` is this fork's standard parameter and a negative one is a
    user-reachable look-ahead -- the caller's explicit request, not a
    property of the formula, whose default `offset=0` the sweeps cover."""
    close = _walk(400, seed=3)
    base = lean_momersion_20(close)
    pd.testing.assert_series_equal(lean_momersion_20(close, offset=2),
                                   base.shift(2), check_names=False)
    pd.testing.assert_series_equal(lean_momersion_20(close, offset=-2),
                                   base.shift(-2), check_names=False)


# ------------------------------------------------------------- Gate D


@pytest.mark.parametrize("k", [8.0, 64.0, 10.0, 3.7])
@pytest.mark.parametrize("frame_fn", [_walk, _tick_rounded, _coarse_grid],
                         ids=["walk", "tick_rounded", "coarse_grid"])
def test_every_price_scale_is_bit_identical(frame_fn, k):
    """x8 and x64 are bit-identical because `8a / 8b` is the same double as
    `a / b`. x10 and x3.7 are too, which a continuous column would not be:
    only the SIGN of the ratio reaches the counts, and a positive constant
    can neither reorder two closes nor separate two equal ones."""
    close = frame_fn()
    base, scaled = lean_momersion_20(close), lean_momersion_20(close * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert int(m.sum()) == 1479
    assert (base[m] == scaled[m]).all()


def _ulp_walk(n=300, seed=3, start=1.0):
    """Consecutive closes that are ADJACENT doubles: every move is one ulp.
    No price feed produces this -- one tick over the price is 1e-9 even at a
    price of 1e6 with a 0.001 tick, seven orders above an ulp."""
    rng = np.random.default_rng(seed)
    steps = rng.choice([-1.0, 1.0], size=n)
    out = np.empty(n)
    v = float(start)
    for i in range(n):
        v = float(np.nextafter(v, np.inf if steps[i] > 0 else -np.inf))
        out[i] = v
    return Series(out)


def test_the_scale_free_claim_stops_at_one_ulp_moves():
    """Where Gate D's x10/x3.7 bit-identity ends, and WHY -- measured, not
    hand-waved. A rescale cannot reorder two closes, and the ratio of two
    distinct doubles never rounds to exactly 1.0 (pinned here: 0 of this
    frame's returns read as zero although every close differs from the
    last). What a non-power-of-two k CAN do is round two closes one ulp
    apart to the SAME double, which turns a signed pair flat. x8/x64 fuse
    nothing and stay bit-identical; x10 fuses 58 of 299 pairs and x3.7 ten,
    and the column moves with them. Only one-ulp neighbours can fuse -- the
    widest fusion window is the 1.5 ulp at a power of two, and 2 ulps of
    separation land outside it for every k -- and every real frame is orders
    above that."""
    close = _ulp_walk()
    base = lean_momersion_20(close)
    assert int(base.notna().sum()) == 279
    assert int(((close / close.shift(1) - 1.0).dropna() == 0.0).sum()) == 0
    for k, fused, bit, diff in ((8.0, 0, 279, 0.0), (64.0, 0, 279, 0.0),
                                (10.0, 58, 141, 60.0),
                                (3.7, 10, 224, 16.538462)):
        scaled_close = close * k
        a = scaled_close.to_numpy()
        assert int((a[1:] == a[:-1]).sum()) == fused
        s = lean_momersion_20(scaled_close)
        assert (base.isna() == s.isna()).all()
        m = base.notna()
        assert int((base[m] == s[m]).sum()) == bit
        assert float((base[m] - s[m]).abs().max()) == pytest.approx(diff,
                                                                   abs=1e-4)


def test_fires_and_is_not_constant():
    close = _walk()
    out = lean_momersion_20(close)
    fires = int(out.notna().sum())
    assert 0 < fires < len(close)
    assert fires == 1479
    assert int(out.nunique()) == 14


def test_the_value_set_is_discrete_and_the_denominator_explains_it():
    """100 * MC / (MC + MRC) with MC + MRC <= 20 has 129 reachable values,
    but a frame without exact ties signs every pair, so the denominator is
    always 20 and the value is a multiple of 5. Grids, which have flat
    bars, shrink the denominator and show more."""
    reachable = {round(100.0 * mc / t, 12)
                 for t in range(1, LENGTH + 1) for mc in range(t + 1)}
    assert len(reachable) == 129
    walk = lean_momersion_20(_walk()).dropna()
    assert ((walk % 5.0) == 0.0).all()
    assert int(walk.nunique()) == 14
    assert int(lean_momersion_20(_tick_rounded()).nunique()) == 25
    assert int(lean_momersion_20(_coarse_grid()).nunique()) == 87


# ------------------------------------------------- what the column means


def test_it_orders_persistence():
    """AR(1) returns: phi = +0.8 keeps going, -0.8 reverses. The medians
    must come out in that order, which is the column's actual claim. ONE
    seed for every phi (common random numbers), so this is the phi effect
    and not four unrelated draws."""
    medians = [float(lean_momersion_20(_ar1(phi=phi, seed=40)).median())
               for phi in (0.8, 0.4, -0.4, -0.8)]
    assert medians == [80.0, 65.0, 35.0, 20.0]
    assert float(lean_momersion_20(_walk()).median()) == 50.0


def test_a_hard_alternating_path_reads_zero_everywhere():
    out = lean_momersion_20(_alternating())
    assert int(out.notna().sum()) == 1479
    assert (out.dropna() == 0.0).all()


def test_the_iid_median_is_fifty_and_the_spread_is_wide():
    """For iid returns the population value is exactly 50 (consecutive
    return signs are independent). The column is unbiased in the median and
    +-15 points at the deciles, which is the number a reader needs before
    treating one reading as a regime call. Pinned loosely -- the seed is
    fixed, the bounds are not tight."""
    rng = np.random.default_rng(123)
    paths = 100.0 * np.exp(np.cumsum(
        rng.normal(0.0, 0.01, (300, LENGTH + 2)), axis=1))
    est = np.array([float(lean_momersion_20(Series(p)).iloc[-1])
                    for p in paths])
    assert np.isfinite(est).all()
    assert float(np.median(est)) == 50.0
    assert 46.0 < float(est.mean()) < 54.0
    assert 8.0 < float(est.std(ddof=0)) < 14.0


def test_it_is_not_drift_invariant_and_that_is_pinned_on_purpose():
    """Unlike most of this fork's window statistics, drift moves this
    column: it makes up-moves likelier, so it changes the signs. Measured
    rather than hoped for, so a future 'fix' that makes it invariant is
    visible as a changed test."""
    close = _walk()
    drifted = Series(close.to_numpy() * np.exp(0.004 * np.arange(len(close))))
    base, out = lean_momersion_20(close), lean_momersion_20(drifted)
    assert (base.isna() == out.isna()).all()
    m = base.notna()
    assert float(base[m].corr(out[m], method="spearman")) < 0.5


# -------------------------------------------------------- edge, guards


def test_a_flat_frame_is_nan():
    assert int(lean_momersion_20(Series(np.full(300, 50.0))).notna().sum()) == 0


def test_a_staircase_with_no_adjacent_steps_is_nan():
    """Every pair is flat, so MC + MRC == 0 on every window: NaN, not a
    fake 50. The frame real data comes closest to is a thinly traded name
    that moves once a week."""
    stair = Series(np.repeat(np.arange(1, 31, dtype=float) + 100.0, 10))
    r = stair / stair.shift(1) - 1.0
    p = np.sign(r) * np.sign(r).shift(1)
    assert int((p.notna() & (p != 0)).sum()) == 0
    assert int(lean_momersion_20(stair).notna().sum()) == 0


def test_a_one_tick_alternation_reads_zero():
    frame = Series(np.where(np.arange(300) % 2 == 0, 100.00, 100.01))
    out = lean_momersion_20(frame)
    assert int(out.notna().sum()) == 279
    assert (out.dropna() == 0.0).all()


def test_insufficient_history_returns_none():
    assert lean_momersion_20(_walk(WARMUP)) is None


def test_exact_min_length_fires_once_at_the_warmup_boundary():
    out = lean_momersion_20(_walk(LENGTH + 2, seed=2))
    assert int(out.notna().sum()) == 1
    assert int(out.notna().to_numpy().argmax()) == WARMUP


@pytest.mark.parametrize("bad", [np.nan, 0.0, -5.0, np.inf, 1e-310])
def test_a_bad_close_empties_its_own_windows_and_moves_nothing_else(bad):
    """NaN, zero, negative, infinite and subnormal closes are all missing
    data. A bad close at bar 200 kills the pair that ends on it and the
    pair that starts from it, so it empties the 22 windows 200..221 -- and
    because the counts are integers, NOTHING else moves, on either side."""
    close = _walk(400, seed=21)
    base = lean_momersion_20(close)
    holed = close.copy()
    holed.iloc[200] = bad
    out = lean_momersion_20(holed)
    emptied = np.flatnonzero((base.notna() & out.isna()).to_numpy())
    assert len(emptied) == LENGTH + 2
    assert (int(emptied.min()), int(emptied.max())) == (200, 221)
    shared = base.notna() & out.notna()
    assert int((shared & (base != out)).sum()) == 0


@pytest.mark.parametrize("length", [None, 0, -5, 1, 0.5, 1.9])
def test_a_length_below_the_minimum_falls_back_to_the_default(length):
    out = lean_momersion_20(_walk(400, seed=31), length=length)
    assert out.name == "LEAN_MOMERSION_20"
    assert int(out.notna().sum()) == 379


@pytest.mark.parametrize("length", [2, 2.9])
def test_the_smallest_accepted_length_is_two(length):
    """`int()` truncation is the rule, so 2.9 is accepted AS 2 rather than
    falling back to the default -- the complement of the row above, which
    is only about fractions that truncate BELOW 2."""
    out = lean_momersion_20(_walk(400, seed=31), length=length)
    assert out.name == "LEAN_MOMERSION_2"
    assert int(out.notna().sum()) == 397


def test_fractional_lengths_that_truncate_the_same_are_identical():
    close = _walk(400, seed=31)
    pd.testing.assert_series_equal(lean_momersion_20(close, length=50.9),
                                   lean_momersion_20(close, length=50))


def test_distinct_lengths_produce_distinct_names_and_values():
    close = _walk(1500, seed=31)
    a, b = lean_momersion_20(close, length=10), lean_momersion_20(close,
                                                                  length=60)
    assert (a.name, b.name) == ("LEAN_MOMERSION_10", "LEAN_MOMERSION_60")
    m = a.notna() & b.notna()
    assert int(m.sum()) > 1000
    assert float(a[m].corr(b[m], method="spearman")) < 0.9


def test_a_length_that_needs_more_closes_than_the_frame_has_returns_none():
    close = _walk(400, seed=31)
    longest = lean_momersion_20(close, length=398)
    assert longest.name == "LEAN_MOMERSION_398"
    assert int(longest.notna().sum()) == 1
    assert lean_momersion_20(close, length=399) is None


def test_fillna_applies():
    out = lean_momersion_20(_walk(200, seed=13), fillna=-1.0)
    assert int((out == -1.0).sum()) == WARMUP


# ------------------------------------------------------------- wiring


def test_name_registration_and_accessor():
    close = _walk(300, seed=17)
    df = pd.DataFrame({"open": close, "high": close * 1.01,
                       "low": close * 0.99, "close": close,
                       "volume": Series(np.full(len(close), 1000.0))})
    assert "lean_momersion_20" in ta.Category["momentum"]
    assert hasattr(df.ta, "lean_momersion_20")
    direct = lean_momersion_20(close)
    through = df.ta.lean_momersion_20()
    pd.testing.assert_series_equal(through, direct, check_names=True)
    assert through.name == "LEAN_MOMERSION_20"
    assert lean_momersion_20(close).category == "momentum"
