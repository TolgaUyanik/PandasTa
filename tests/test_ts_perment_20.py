# -*- coding: utf-8 -*-
"""TS-PERMENT-20: `ts_perment_20`, tsfresh's permutation entropy of close
(PandasTa issue #91).

    TS_PERMENT_20_3 = -sum(p * log p), p = share of the 18 three-close
                      triples of a 20-close window falling in each of the
                      six ORDERINGS of three points

WHAT THIS FILE PINS, in order of how much it would hurt to lose.

1. **That the port is NOT the column issue #91 screened, and why.** The
   screen prototype (`docs/issues/screen/ind_screen.py`, candidate
   `ts_perment_20`) loops `for k in (0, 1, 3, 4, 6, 7)` over its own
   `4*(a<b) + 2*(b<c) + (a<c)` code. Two of those six codes, **1 and 6, are
   unrealisable** -- 6 needs `a < b < c` together with `a >= c` -- and two
   realisable ones, **2 and 5, are missing**, so the prototype is a FOUR-
   pattern sum that drops **25.90%** of a walk's triples
   (`test_the_encoding_is_exhaustive_and_the_prototype_skips_two_patterns`).
   Two measurements, kept apart because they answer different questions.
   Port against the PROTOTYPE, where the pattern set AND the tie folding both
   differ: Spearman **0.5487** on a walk, **0.4817** tick-rounded,
   **−0.0296** on a coarse grid — nothing at all. Port against the
   four-pattern VARIANT, which changes only the pattern set and holds the tie
   rule fixed: **0.5487 / 0.4811 / 0.6067**. Gate A starts from
   the source formula and not from the prototype (`CLAUDE.md`), so the port
   is the six-pattern form -- but issue #91's screen numbers (Gate E max
   |rho| 0.2046 vs `psl`) were measured on the four-pattern column and do
   NOT transfer. The retyped prototype is pinned bit-equal to the owner's
   own registry entry when that tree is present, so the comparison is
   against the screen's real code and not a paraphrase of it.

2. **Gate A, and that the formula under test is the ISSUE's line plus the
   published Bandt-Pompe definition.** tsfresh is NOT installed in this
   worktree and web access is unavailable, so "tsfresh (MIT)" is an
   attribution, not an oracle. What IS checkable is pinned four ways:

   * the 3-bit code is a BIJECTION with the ordinal pattern as tsfresh
     spells it (`argsort(argsort(x))`), checked exhaustively over all 27
     triples drawn from `{1, 2, 3}` -- which covers every weak order on
     three elements, ties included;
   * that spelling, run window by window with numpy's own `argsort` and
     `np.unique` and sharing no code with the module, is **bit-equal on
     581 of 581** bars on each of four frames. Bit-equality is not an
     accident: the six terms are accumulated in the order `np.unique`
     returns the rank vectors (codes 7, 5, 3, 4, 2, 0), which is why
     `pandas_ta/statistics/ts_perment_20.py` fixes `PATTERNS` in that order
     and `test_the_accumulation_order_is_the_sources_own` fails if it is
     reordered;
   * seven hand-derived windows with an exact closed form, including the
     ceiling: a 20-close window whose 18 triples hit each ordering exactly
     three times reads **1.7917594692280547**, which is **one ulp BELOW**
     `math.log(6)`, so `value <= log 6` is true but `value == log 6` is
     false;
   * an independent plain-Python scalar loop over `sorted()`: max
     |difference| **4.44e-16**, 0 bars over 1e-12. Spearman against it is
     0.9992 rather than 1.0 *because* the value is a coarse count statistic
     whose ties a last bit re-orders -- not a disagreement about any
     distinct value.

3. **Gate B, by mutant, on six configurations.** Five mutants, each
   `importlib`-read and `exec`'d in memory, covering TWO mechanisms: the
   write index back-dated by 1, 2, `length // 2` and `length - 1` bars (the
   one-triple roll, the two-bar back-date, the half-window roll and the full
   back-date -- rolling the code array forward by k is the same as writing
   the column k bars early, except for the k wrapped windows at the tail
   that `np.roll` fills from the head, and at `length=4` the two-bar
   and half-window mutants coincide), and the newest leg of every triple
   read one bar ahead. Over 37 offsets of a future-perturbation sweep the
   **real module leaks 0/37 in all six configurations** -- three frames at
   the defaults, plus `length` 10, 60 and 4 on the walk.
   ⚠ The mutants are not caught at 37/37: **15-32 of 37 for the three
   one- and two-bar leaks at the default length on three frames, and 7-37
   over all six configurations**, the floor at `length=4` where a window
   holds two triples. That is a property of an ORDINAL column: a
   perturbation is invisible unless it flips an order relation. The reason is
   measured exactly rather than excused -- for the one-triple leak, every
   missed offset is either an offset where the illegally read triple's CODE
   is unchanged (so the mutant's window is identical and there is nothing to
   detect) or one where the count vector moves to a PERMUTATION of itself,
   and the entropy is a symmetric function of the counts
   (`test_a_missed_mutant_offset_is_an_unchanged_code_or_a_permutation`).

4. **Gate D, and that it is stronger than x8.** The column reads only the
   ORDER of the closes, so it is bit-identical under a strictly increasing
   transform of price and not merely under a multiplication: x8, x64, x1024,
   x10, x3.7 and x0.1 are bit-identical on **1481 of 1481** fired bars on
   each of seven frames, and `log`, `sqrt`, `x**3` and `+1000` on the walk
   (one frame, which is what was run). The invariance holds up to a float64
   COLLAPSE: a transform that maps two distinct closes onto one double can
   move the column, and the tie rule makes that visible only when the
   earlier close is the larger -- on these frames none collapses. A DRIFT is
   not such a transform at all and does change the column (Spearman
   **0.2108**), which is the measurement that stops "scale-free" being read
   as "shift-invariant in time".

5. **What the column is BLIND to, which is the thing most likely to be
   misread.** It cannot see magnitude at all: a +10, +50 and +1000 sigma
   spike planted at the same bar give a **bit-identical** column (15 bars
   move in each case). And **0.0 is both the flat window and the monotone
   one** -- 20 identical closes and 20 strictly rising closes both read
   exactly 0.0, because a tie is broken by index and so reads as a rise. A
   strongly trending frame reads a median of 0.0 (1,236 of 1,481 bars
   exactly 0.0). Do NOT read this column as volatility, as trend strength,
   or as an outlier detector.

6. **The tie rule, and that it is load-bearing on coarse prices.** Ties are
   broken by INDEX (the earlier close is the smaller), which is what the
   installed numpy's `argsort(argsort(x))` does -- measured over all 27
   triples, not assumed, since `argsort`'s default `kind` is not documented
   as stable -- and therefore what tsfresh's `argsort` spelling does *if*
   that is its spelling; tsfresh is not installed here. On a frame with no ties
   that choice is free -- bit-equal to the strict-`<` folding on 1481 of
   1481 bars of a walk -- but on a coarse grid where **46.33%** of triples
   hold a tie the two readings are nearly unrelated (Spearman **0.0384**),
   and the same path rounded to a coarse grid reads differently from the
   unrounded one (Spearman **0.3796**). Price granularity is an input to
   this column.

7. **The attainable set.** The value is a function of the window's pattern
   COUNT VECTOR and nothing else. At length 6 and 7 the set of count vectors
   realisable by some ordering is exhaustively equal to the set satisfying
   the one structural constraint (consecutive triples share a comparison, so
   bit B of one code is bit A of the next): **63 of 63** and **116 of 116**.
   At the shipped length 20 that constraint admits **5,978** count vectors
   carrying **175** distinct values to 1e-12, spanning 0.0 to the ceiling;
   200,000 random orderings of 20 distinct closes reach 2,814 of them and
   every one satisfies the constraint. A rank statistic over this column
   therefore carries heavy ties by construction.

Numbers come from `docs/measure_ts_perment_20.py`; the receipt is
`docs/TsPerment20Measured.md`. Counts that depend on the last bits of a
generated frame (distinct values, Spearman to six places, how many offsets a
mutant is caught at) carry a tolerance: CI's runner has measured different
last bits for the same seeds (commit 22fe27b).
"""
import importlib
import itertools
import math
import types

import numpy as np
import pandas as pd
import pytest
from numpy.lib.stride_tricks import sliding_window_view
from pandas import Series

from .context import pandas_ta
from pandas_ta.statistics.ts_perment_20 import ts_perment_20

LENGTH = 20
DIMENSION = 3
TRIPLES = LENGTH - (DIMENSION - 1)  # 18
#: The six realisable codes, in the order the module accumulates them -- the
#: order `np.unique` returns the rank vectors in, which is what makes the
#: module bit-equal to the source's own spelling.
PATTERNS = (7, 5, 3, 4, 2, 0)
UNREALISABLE = (1, 6)

_REAL = importlib.import_module("pandas_ta.statistics.ts_perment_20")


def _accumulate(counts, triples=TRIPLES):
    """The module's accumulation: one term per occupied pattern, in PATTERNS
    order."""
    h = 0.0
    for n in counts:
        if n:
            p = n / triples
            h -= p * math.log(p)
    return h


#: The ceiling: three triples in each of the six orderings. In float64 this
#: is 1.7917594692280547, ONE ULP BELOW `math.log(6)` = 1.791759469228055.
TOP = _accumulate([3] * 6)
#: A 20-close window whose 18 triples hit each ordering exactly three times,
#: found by `docs/measure_ts_perment_20.py` (12 shuffles at seed 2026).
EVEN_SPLIT = [20, 4, 8, 17, 13, 5, 2, 14, 6, 10, 11, 9, 1, 15, 7, 12, 3, 18,
              19, 16]


# ------------------------------------------------------------------ frames


def _walk(n=1500, seed=11, sigma=0.015, drift=0.0):
    rng = np.random.default_rng(seed)
    return Series(100.0 * np.exp(np.cumsum(rng.normal(drift, sigma, n))))


def _tick_rounded(n=1500, seed=55):
    return Series(np.round(_walk(n, seed).to_numpy(), 2))


def _coarse_grid(n=1500, seed=55, sigma=0.002, decimals=1):
    """A quiet path on a coarse price grid: 46% of its triples hold a tie."""
    return Series(np.round(_walk(n, seed, sigma).to_numpy(), decimals))


def _from_returns(r):
    return Series(100.0 * np.cumprod(1.0 + np.asarray(r, dtype=float)))


def _heavy_tailed(n=1500, seed=3, df=2.0, sigma=0.01):
    rng = np.random.default_rng(seed)
    return _from_returns(np.clip(sigma * rng.standard_t(df, n), -0.5, 0.5))


def _two_point(n=1500, seed=4, sigma=0.01):
    rng = np.random.default_rng(seed)
    return _from_returns(np.where(rng.random(n) < 0.5, sigma, -sigma))


def _mean_reverting(n=1500, seed=7, sigma=0.01, phi=-0.6):
    rng = np.random.default_rng(seed)
    e = rng.normal(0.0, sigma, n)
    r = np.zeros(n)
    for t in range(1, n):
        r[t] = phi * r[t - 1] + e[t]
    return _from_returns(np.clip(r, -0.5, 0.5))


def _trending(n=1500, seed=9, sigma=0.004, drift=0.01):
    return _walk(n, seed, sigma, drift)


def _flat(n=300, price=100.0):
    return Series(np.full(n, price))


def _monotone(n=300, step=0.5, price=100.0):
    return Series(price + step * np.arange(n))


def _zigzag(n=300, lo=100.0, hi=101.0):
    return Series(np.where(np.arange(n) % 2 == 0, lo, hi))


ALL_FRAMES = [_walk, _tick_rounded, _coarse_grid, _heavy_tailed, _two_point,
              _mean_reverting, _trending]


def _codes(c):
    a, b, z = c[:-2], c[1:-1], c[2:]
    return (4 * (a <= b) + 2 * (b <= z) + (a <= z)).astype(int)


# ------------------------------------------------------------- Gate A


def test_the_encoding_is_exhaustive_and_the_prototype_skips_two_patterns():
    """The module's 3-bit code against the ordinal pattern tsfresh uses.

    Exhaustive over all 27 triples of values drawn from {1, 2, 3}, which
    realises every weak order on three elements (strict orders and every tie
    pattern). Each code maps to exactly ONE `argsort(argsort(x))` rank
    vector and back, codes 1 and 6 never occur, and the screen prototype's
    loop `(0, 1, 3, 4, 6, 7)` both visits those two impossible codes and
    skips the realisable 2 and 5.
    """
    code_to_ranks = {}
    for triple in itertools.product((1.0, 2.0, 3.0), repeat=3):
        arr = np.asarray(triple)
        code = 4 * int(arr[0] <= arr[1]) + 2 * int(arr[1] <= arr[2]) \
            + int(arr[0] <= arr[2])
        ranks = tuple(int(v) for v in np.argsort(np.argsort(arr)))
        code_to_ranks.setdefault(code, set()).add(ranks)

    assert sorted(code_to_ranks) == sorted(PATTERNS)
    assert set(UNREALISABLE) & set(code_to_ranks) == set()
    # one rank vector per code, and all six rank vectors distinct
    assert all(len(v) == 1 for v in code_to_ranks.values())
    assert len({next(iter(v)) for v in code_to_ranks.values()}) == 6
    assert set(_REAL.PATTERNS) == set(PATTERNS)
    assert set(_REAL.UNREALISABLE) == set(UNREALISABLE)

    proto_loop = (0, 1, 3, 4, 6, 7)
    assert sorted(set(PATTERNS) - set(proto_loop)) == [2, 5]
    assert sorted(set(proto_loop) - set(PATTERNS)) == [1, 6]

    codes = _codes(_walk().to_numpy())
    skipped = float(np.mean((codes == 2) | (codes == 5)))
    assert skipped == pytest.approx(0.2590, abs=0.01)


def test_the_accumulation_order_is_the_sources_own():
    """`PATTERNS` is sorted by the rank vector, not by the code.

    `np.unique(..., axis=0)` returns the rank vectors sorted, so tsfresh's
    `-np.sum(probs * np.log(probs))` adds the six terms in that order. The
    module accumulates in the same order, which is why
    `test_matches_the_argsort_definition` measures 581 of 581 bars BIT-equal
    rather than merely agreeing to 1e-12; that count is pinned there with
    two bars of slack, and the order itself is pinned here. Reordering
    `PATTERNS` keeps every count and moves the last bit.
    """
    by_rank = sorted(PATTERNS,
                     key=lambda k: tuple(int(v) for v in np.argsort(
                         np.argsort(np.asarray(
                             {0: (3.0, 2.0, 1.0), 2: (3.0, 1.0, 2.0),
                              3: (2.0, 1.0, 3.0), 4: (2.0, 3.0, 1.0),
                              5: (1.0, 3.0, 2.0), 7: (1.0, 2.0, 3.0)}[k])))))
    assert tuple(by_rank) == tuple(_REAL.PATTERNS)

    close = _walk(400, seed=21)
    base = ts_perment_20(close)
    shuffled = _variant(close, patterns=(0, 2, 3, 4, 5, 7))
    m = base.notna() & shuffled.notna()
    # same counts, so the same value to 1e-12 -- and a different last bit on
    # some bars, which is exactly what the order buys.
    assert float((base[m] - shuffled[m]).abs().max()) < 1e-12
    assert 0 < int((base[m] != shuffled[m]).sum())


HAND_CASES = [
    # (name, closes, length, counts, closed form, ulps closed form - module)
    ("20 strictly rising closes, every triple the rising ordering",
     Series(100.0 + 0.5 * np.arange(LENGTH)), LENGTH, [18], 0.0, 0),
    ("20 identical closes: a tie reads as a rise, so the same ordering",
     Series(np.full(LENGTH, 100.0)), LENGTH, [18], 0.0, 0),
    ("20 strictly falling closes, every triple the falling ordering",
     Series(100.0 - 0.5 * np.arange(LENGTH)), LENGTH, [18], 0.0, 0),
    ("zigzag 100/101: nine of each of two orderings",
     _zigzag(LENGTH), LENGTH, [9, 9], math.log(2.0), 0),
    ("the even-split witness: three of each of the six",
     Series([float(v) for v in EVEN_SPLIT]), LENGTH, [3] * 6,
     math.log(6.0), 1),
    ("length 4, closes [1,3,2,4]: one triple of each of two orderings",
     Series([1.0, 3.0, 2.0, 4.0]), 4, [1, 1], math.log(2.0), 0),
    ("length 5, closes [1,3,2,4,5]: one triple of each of three",
     Series([1.0, 3.0, 2.0, 4.0, 5.0]), 5, [1, 1, 1], math.log(3.0), 1),
]


@pytest.mark.parametrize("name,closes,length,counts,closed,ulps", HAND_CASES,
                         ids=[c[0][:40] for c in HAND_CASES])
def test_hand_derived_windows_are_exact(name, closes, length, counts, closed,
                                        ulps):
    """Seven windows whose pattern counts are known by hand, so the value has
    a closed form. The module must land 0.0 away from the accumulation of
    that closed form, and the distance between the accumulation and the
    closed form itself is pinned in ULPS -- which is how the ceiling turns
    out to be one ulp BELOW `log 6`."""
    got = ts_perment_20(closes, length=length)
    assert got.name == f"TS_PERMENT_{length}_{DIMENSION}"
    value = float(got.iloc[length - 1])
    expected = _accumulate(counts, length - 2)
    assert value == expected
    if closed:
        assert round((closed - expected) / np.spacing(closed)) == ulps
        assert value <= closed


def test_the_ceiling_is_one_ulp_below_log_six_and_is_reachable():
    """`log 6` is the mathematical bound and the module cannot reach it: the
    six terms are accumulated one at a time, so the top of the range is
    1.7917594692280547, one ulp lower. The bound has to be written with the
    ulp in it, and the witness proves the top IS attained rather than
    approached."""
    assert TOP == 1.7917594692280547
    assert TOP < math.log(6.0)
    assert round((math.log(6.0) - TOP) / np.spacing(math.log(6.0))) == 1
    window = Series([float(v) for v in EVEN_SPLIT])
    codes = _codes(window.to_numpy())
    assert [int((codes == k).sum()) for k in PATTERNS] == [3] * 6
    assert float(ts_perment_20(window).iloc[LENGTH - 1]) == TOP


def _prototype(close, length=LENGTH):
    """`docs/issues/screen/ind_screen.py` candidate `ts_perment_20`, retyped
    verbatim because that tree is gitignored:

        def perm_entropy3(x, n):
            a, b, c = x.shift(2), x.shift(1), x
            pid = (4*(a < b) + 2*(b < c) + 1*(a < c)).where(a.notna() & c.notna())
            h = pd.Series(0.0, index=x.index)
            for k in (0, 1, 3, 4, 6, 7):
                p = (pid == k).astype(float).rolling(n - 2).mean()
                h -= np.where(p > 0, p * np.log(p.where(p > 0, 1)), 0)
            return (h / np.log(6)).where(pid.rolling(n - 2).count() == n - 2)

        @cand("ts_perment_20", "permutation entropy of close (order 3, 20)",
              TS, "permutation_entropy(tau=1, dimension=3) on 20 closes")
        def _(o, h, l, c, v): return perm_entropy3(c, 20)
    """
    a, b, z = close.shift(2), close.shift(1), close
    pid = (4 * (a < b) + 2 * (b < z) + 1 * (a < z)).where(a.notna()
                                                          & z.notna())
    h = Series(0.0, index=close.index)
    for k in (0, 1, 3, 4, 6, 7):
        p = (pid == k).astype(float).rolling(length - 2).mean()
        h -= np.where(p > 0, p * np.log(p.where(p > 0, 1)), 0)
    return (h / np.log(6)).where(
        pid.rolling(length - 2).count() == length - 2)


def _screen_candidate():
    """The screen's own registry entry, when `docs/issues/` is present (it is
    gitignored, so a clone does not have it).

    The path is anchored on this file, not on the working directory: a
    CWD-relative path would turn the only guard that the retyped prototype is
    the screen's real code into a silent skip when pytest runs from anywhere
    but the repository root.
    """
    import importlib.util
    import sys
    from pathlib import Path

    path = Path(__file__).resolve().parents[1] / "docs" / "issues" / \
        "screen" / "ind_screen.py"
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location("_ind_screen_perment", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_ind_screen_perment"] = mod
    spec.loader.exec_module(mod)
    return mod.REG["ts_perment_20"]["fn"]


@pytest.mark.parametrize("frame_fn,rho", [(_walk, 0.5487),
                                          (_tick_rounded, 0.4817),
                                          (_coarse_grid, -0.0296)])
def test_the_port_is_not_the_column_the_screen_measured(frame_fn, rho):
    """The headline difference, measured on three frames.

    The prototype drops two of the six realisable orderings, so it is a
    different statistic -- not a rescaling of this one. Issue #91's Gate E
    numbers were taken on the prototype and do not carry over to the port,
    which is why the launcher re-runs Gate E on the shipped module.

    On the coarse grid the two differ for BOTH reasons at once -- the missing
    patterns and the opposite tie folding -- and the correlation is
    -0.0296, i.e. nothing at all.
    """
    close = frame_fn()
    port, proto = ts_perment_20(close), _prototype(close)
    m = port.notna() & proto.notna()
    assert int(m.sum()) == 1481
    assert bool((port.isna() == proto.isna()).all())  # same warm-up
    assert float(port[m].corr(proto[m], method="spearman")) == pytest.approx(
        rho, abs=0.02)
    # and not a rescaling: dividing by log 6 does not reconcile them either
    scaled = port / math.log(6.0)
    assert int((scaled[m] == proto[m]).sum()) < 10
    assert float((port[m] - proto[m]).abs().max()) > 0.4


def test_the_retyped_prototype_is_the_screens_own_code():
    """When the owner's gitignored `docs/issues/` tree is in this worktree,
    the retyped prototype above must be bit-equal to the registry entry the
    screen actually ran. Skipped on a clone, where that tree is absent."""
    fn = _screen_candidate()
    if fn is None:
        pytest.skip("docs/issues/screen/ind_screen.py is not in this tree")
    close = _walk()
    imported = Series(np.asarray(fn(close, close, close, close, close),
                                 dtype=float), index=close.index)
    mine = _prototype(close)
    m = mine.notna() & imported.notna()
    assert int(m.sum()) == 1481
    assert bool((mine.isna() == imported.isna()).all())
    assert int((mine[m] == imported[m]).sum()) == 1481


def _argsort_definition(close, length=LENGTH):
    """tsfresh's `permutation_entropy` spelled with numpy's own `argsort` and
    `np.unique`, window by window, sharing no code with the module:

        X = the `length - dimension + 1` subchunks of `dimension`
            consecutive closes (tau = 1)
        permutations = argsort(argsort(X))
        _, counts = unique(permutations, axis=0, return_counts=True)
        probs = counts / len(permutations)
        return -sum(probs * log(probs))
    """
    c = close.to_numpy(dtype=float)
    out = np.full(c.size, np.nan)
    for t in range(length - 1, c.size):
        w = c[t - length + 1:t + 1]
        if not np.isfinite(w).all():
            continue
        x = sliding_window_view(w, DIMENSION)
        perms = np.argsort(np.argsort(x, axis=1), axis=1)
        _, counts = np.unique(perms, axis=0, return_counts=True)
        probs = counts / len(perms)
        out[t] = float(-np.sum(probs * np.log(probs)))
    return Series(out, index=close.index)


@pytest.mark.parametrize("frame_fn", [_walk, _tick_rounded, _coarse_grid,
                                      _two_point])
def test_matches_the_argsort_definition(frame_fn):
    """The strongest Gate A check available without tsfresh installed: the
    source's own spelling, bit for bit on 581 of 581 bars -- including two
    frames where closes TIE, so the tie rule is checked against `argsort`
    rather than assumed to agree with it.

    ⚠ The bit-equal COUNT is an equality of two float pipelines (six
    `h -= p*log(p)` subtractions over an `(n,)` array against `-np.sum(...)`
    over a `(<=6,)` one), so it is a measurement on this machine rather than
    something the arithmetic promises: `docs/measure_ts_perment_20.py`'s
    `gate_a` measures that reordering the same six terms and changing nothing
    else costs 4.44e-16 and moves 249-274 of the 581 bars on four frames.
    The portable half of the claim is pinned exactly -- 0 bars differ by more
    than 1e-12 (about three orders of margin over that 4.44e-16) and max
    |diff| under 1e-14 (about 20x it). The count is pinned at `>= 579`: two
    bars of slack, worth a one- or two-bar drift and nothing more -- a libm
    that really disagreed about `log` across call shapes would move hundreds
    of bars and SHOULD fail here.
    """
    close = frame_fn(n=600)
    port, definition = ts_perment_20(close), _argsort_definition(close)
    m = port.notna() & definition.notna()
    assert int(m.sum()) == 581
    assert bool((port.isna() == definition.isna()).all())
    diff = (port[m] - definition[m]).abs()
    assert int((diff > 1e-12).sum()) == 0
    assert float(diff.max()) <= 1e-14
    assert int((port[m] == definition[m]).sum()) >= 579  # 581/581 measured


def _scalar_loop(close, length=LENGTH):
    """An independent per-window loop in plain Python scalars: the pattern is
    the tuple of positions sorted by `(value, position)`, which is the same
    index tie-break spelled a third way."""
    c = [float(v) for v in close.to_numpy(dtype=float)]
    out = [float("nan")] * len(c)
    for t in range(length - 1, len(c)):
        w = c[t - length + 1:t + 1]
        if any(math.isnan(v) or math.isinf(v) for v in w):
            continue
        counts = {}
        for i in range(len(w) - 2):
            tri = w[i:i + 3]
            order = tuple(p for _, p in sorted((v, p)
                                               for p, v in enumerate(tri)))
            counts[order] = counts.get(order, 0) + 1
        n = len(w) - 2
        h = 0.0
        for v in counts.values():
            p = v / n
            h -= p * math.log(p)
        out[t] = h
    return Series(out, index=close.index)


@pytest.mark.parametrize("frame_fn", [_walk, _tick_rounded, _coarse_grid])
def test_matches_an_independent_scalar_loop(frame_fn):
    """A third implementation, accumulating in FIRST-OCCURRENCE order rather
    than the source's. It agrees to 4.44e-16 and 0 bars over 1e-12 -- and is
    NOT bit-equal, which is the measurement behind item 2's claim that the
    accumulation order is a last bit of the result."""
    close = frame_fn(n=600)
    port, loop = ts_perment_20(close), _scalar_loop(close)
    m = port.notna() & loop.notna()
    assert int(m.sum()) == 581
    diff = (port[m] - loop[m]).abs()
    # 4.44e-16 measured on all three frames; the bound is loose because the
    # size of a last-bit disagreement is a libm detail (commit 22fe27b),
    # while "no bar disagrees by more than 1e-12" is the real claim.
    assert float(diff.max()) <= 1e-14
    assert int((diff > 1e-12).sum()) == 0
    assert int((port[m] == loop[m]).sum()) < 581
    assert float(port[m].corr(loop[m], method="spearman")) > 0.99


def _variant(close, length=LENGTH, patterns=PATTERNS, normalise=False,
             strict=False, on_returns=False, triples_window=False):
    """The module's arithmetic with one reading changed, so each decision is
    priced rather than argued."""
    c = close.to_numpy(dtype=float)
    if on_returns:
        r = np.full(c.size, np.nan)
        r[1:] = c[1:] / c[:-1] - 1.0
        c = r
    ok = np.isfinite(c)
    a, b, z = c[:-2], c[1:-1], c[2:]
    with np.errstate(invalid="ignore"):
        if strict:
            code = (4 * (a < b) + 2 * (b < z) + (a < z)).astype(np.int8)
        else:
            code = (4 * (a <= b) + 2 * (b <= z) + (a <= z)).astype(np.int8)
    codes = np.where(ok[:-2] & ok[1:-1] & ok[2:], code, -1)
    triples = length if triples_window else length - 2
    windows = sliding_window_view(codes, triples)
    h = np.zeros(windows.shape[0])
    for k in patterns:
        p = (windows == k).sum(axis=1) / triples
        h -= np.where(p > 0, p * np.log(np.where(p > 0, p, 1.0)), 0.0)
    if normalise:
        h = h / math.log(len(patterns))
    bad = (windows < 0).any(axis=1)
    out = np.full(c.size, np.nan)
    out[triples + 1:] = np.where(bad, np.nan, h)
    return Series(out, index=close.index)


def test_normalising_by_log_six_is_a_strict_rescaling():
    """The prototype divides by `log 6`; tsfresh's `permutation_entropy`
    does not. The choice changes no ranking at all -- Spearman exactly
    1.000000 -- so it is the only one of the five open readings that a rank
    miner cannot see."""
    close = _walk()
    base, other = ts_perment_20(close), _variant(close, normalise=True)
    m = base.notna() & other.notna()
    assert int(m.sum()) == 1481
    assert float(base[m].corr(other[m], method="spearman")) == 1.0
    assert float((base[m] - other[m]).abs().max()) == pytest.approx(
        0.7834, abs=1e-3)
    assert float((base[m] / math.log(6.0) - other[m]).abs().max()) == 0.0


@pytest.mark.parametrize("frame_fn,tied,bit_equal,rho", [
    (_walk, 0.0, 1481, 1.0),
    (_tick_rounded, 0.0067, 1377, 0.9795),
    (_coarse_grid, 0.4633, 19, 0.0384),
])
def test_the_tie_rule_is_free_on_fine_prices_and_decides_the_column_on_coarse(
        frame_fn, tied, bit_equal, rho):
    """Ties are broken by INDEX (`<=`), which is what the installed numpy's
    `argsort(argsort(x))` does -- measured over all 27 triples in
    `test_the_encoding_is_exhaustive_and_the_prototype_skips_two_patterns`,
    not assumed -- and therefore what tsfresh's `argsort` spelling does *if*
    that is its spelling; tsfresh is not installed here. The prototype folds
    them the other way with a strict `<`.

    On a continuous path the two readings are bit-equal on every bar, so the
    choice looks cosmetic. It is not: on a coarse grid where 46% of triples
    hold a tie they are nearly unrelated (Spearman 0.0384). The tie rate is
    measured here too, so the claim and its cause stay together.
    """
    close = frame_fn()
    c = close.to_numpy()
    a, b, z = c[:-2], c[1:-1], c[2:]
    rate = float(((a == b) | (b == z) | (a == z)).mean())
    assert rate == pytest.approx(tied, abs=0.02)

    base, other = ts_perment_20(close), _variant(close, strict=True)
    m = base.notna() & other.notna()
    assert int(m.sum()) == 1481
    equal = int((base[m] == other[m]).sum())
    if bit_equal == 1481:
        assert equal == 1481
    else:
        assert abs(equal - bit_equal) <= max(10, bit_equal // 10)
    assert float(base[m].corr(other[m], method="spearman")) == pytest.approx(
        rho, abs=0.03)


@pytest.mark.parametrize("frame_fn,rho", [(_walk, 0.8895),
                                          (_tick_rounded, 0.9063),
                                          (_coarse_grid, 0.9287)])
def test_the_window_is_twenty_closes_not_twenty_triples(frame_fn, rho):
    """"on 20 closes" is the issue's wording, so a window holds 18 triples
    and the first value lands at bar 19. Reading it as 20 TRIPLES would need
    22 closes and is a different, more smoothed column (Spearman 0.89-0.93),
    which is why the reading is recorded rather than assumed."""
    close = frame_fn()
    base, other = ts_perment_20(close), _variant(close, triples_window=True)
    assert int(base.notna().to_numpy().argmax()) == LENGTH - 1
    assert int(other.notna().to_numpy().argmax()) == LENGTH + 1
    m = base.notna() & other.notna()
    assert float(base[m].corr(other[m], method="spearman")) == pytest.approx(
        rho, abs=0.02)


@pytest.mark.parametrize("frame_fn,rho", [(_walk, 0.1311),
                                          (_tick_rounded, -0.0538),
                                          (_coarse_grid, 0.0600)])
def test_the_input_is_closes_not_returns(frame_fn, rho):
    """The issue says "on 20 closes", and `ts_binent_20` / `ts_c3_20` are the
    fork's return-based tsfresh ports. Permutation entropy of the RETURNS is
    an almost unrelated column (|Spearman| <= 0.14 on three frames), so the
    two are not interchangeable and this port is the close-based one."""
    close = frame_fn()
    base, other = ts_perment_20(close), _variant(close, on_returns=True)
    m = base.notna() & other.notna()
    assert float(base[m].corr(other[m], method="spearman")) == pytest.approx(
        rho, abs=0.05)
    assert abs(float(base[m].corr(other[m], method="spearman"))) < 0.2


def test_the_degenerate_window_is_zero_and_so_is_the_monotone_one():
    """A window with nothing to order reads 0.0, not NaN -- the source's
    reading, since one ordering holds all the mass.

    The cost is stated rather than hidden: 20 identical closes and 20
    strictly rising closes are the SAME value, exactly 0.0, because a tie is
    broken by index and therefore reads as a rise. A consumer cannot use
    this column to tell a dead stock from a trending one.
    """
    for frame in (_flat(), _monotone()):
        out = ts_perment_20(frame)
        assert int(out.notna().sum()) == 281
        assert int((out.dropna() == 0.0).sum()) == 281
    assert float(ts_perment_20(_flat()).iloc[LENGTH - 1]) == 0.0
    assert float(ts_perment_20(_monotone()).iloc[LENGTH - 1]) == 0.0
    # and on a real-shaped path the value is never 0
    assert int((ts_perment_20(_walk()).dropna() == 0.0).sum()) == 0


# ------------------------------------------------------------- Gate B

BACK_DATE_TWO = (
    "    out[length - 1:] = np.where(bad, np.nan, h)",
    "    out[length - 3:c.size - 2] = np.where(bad, np.nan, h)")
BACK_DATE_FULL = (
    "    out[length - 1:] = np.where(bad, np.nan, h)",
    "    out[:windows.shape[0]] = np.where(bad, np.nan, h)")
FORWARD_LEG = (
    "    a, b, z = c[:-LEGS], c[TAU:c.size - TAU], c[LEGS:]",
    "    a, b, z = c[:-LEGS], c[TAU:c.size - TAU], np.roll(c, -1)[LEGS:]")
ROLLED_WINDOW = (
    "    windows = sliding_window_view(codes, triples)",
    "    windows = sliding_window_view(np.roll(codes, -(length // 2)), "
    "triples)")
FORWARD_TRIPLE = (
    "    windows = sliding_window_view(codes, triples)",
    "    windows = sliding_window_view(np.roll(codes, -1), triples)")

MUTANTS = [BACK_DATE_TWO, BACK_DATE_FULL, FORWARD_LEG, ROLLED_WINDOW,
           FORWARD_TRIPLE]
MUTANT_IDS = ["back_date_two", "back_date_full", "forward_leg",
              "rolled_window", "forward_triple"]
OFFSETS = range(40, 1500, 40)  # 37 offsets, past the 20-bar warm-up
FRAMES = {
    "walk": (_walk(), _walk(seed=97)),
    "tick-rounded": (_tick_rounded(), _tick_rounded(seed=56)),
    "heavy-tailed": (_heavy_tailed(), _heavy_tailed(seed=8)),
}


def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_ts_perment_20_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


def _caught(fn, close, other):
    """Replace every bar from J onward with a different path; return the J
    values at which anything strictly before J moves. Prefix truncation
    cannot see back-dating, which is why this is a perturbation sweep."""
    base = fn(close)
    hits = []
    for j in OFFSETS:
        p = close.copy()
        p.iloc[j:] = other.iloc[j:].values
        out = fn(p)
        a, b = base.iloc[:j], out.iloc[:j]
        if not (a.isna() == b.isna()).all():
            hits.append(j)
            continue
        m = a.notna()
        if (a[m] != b[m]).any():
            hits.append(j)
    return hits


@pytest.mark.parametrize("frame", sorted(FRAMES))
def test_real_module_never_reads_the_future(frame):
    close, other = FRAMES[frame]
    assert _caught(ts_perment_20, close, other) == []


@pytest.mark.parametrize("length", [10, 60, 4])
def test_real_module_never_reads_the_future_at_other_lengths(length):
    """`length` is the one user-reachable parameter, and the sweep above runs
    the default only."""
    close, other = FRAMES["walk"]

    def real(c):
        return ts_perment_20(c, length=length)

    assert int(real(close).notna().to_numpy().argmax()) == length - 1
    assert _caught(real, close, other) == []


#: (mutant index, frame, caught offsets of 37). Measured locally; a
#: tolerance of 4 absorbs a runner whose frame differs in the last bits.
MUTANT_CELLS = [
    (0, "walk", 31), (0, "tick-rounded", 32), (0, "heavy-tailed", 23),
    (1, "walk", 37), (1, "tick-rounded", 37), (1, "heavy-tailed", 37),
    (2, "walk", 18), (2, "tick-rounded", 17), (2, "heavy-tailed", 19),
    (3, "walk", 37), (3, "tick-rounded", 37), (3, "heavy-tailed", 37),
    (4, "walk", 20), (4, "tick-rounded", 21), (4, "heavy-tailed", 15),
]


@pytest.mark.parametrize("index,frame,caught", MUTANT_CELLS,
                         ids=[f"{MUTANT_IDS[i]}-{f}"
                              for i, f, _ in MUTANT_CELLS])
def test_each_mutant_is_caught_on_each_frame(index, frame, caught):
    """Every mutant changes the column live and is caught by the sweep.

    ⚠ The two whole-window leaks are caught 37/37; the three that move the
    column or the window by ONE or TWO bars are caught at 15-32 of 37. That
    is the ordinal column, not a hole in the sweep: a perturbation is
    invisible unless it flips an order relation.
    `test_a_missed_mutant_offset_is_an_unchanged_code_or_a_permutation`
    measures the mechanism for the one-triple leak, and the real module's
    0/37 is asserted on three frames and three further lengths rather than
    on one.
    """
    mod = _load_mutant(*MUTANTS[index])
    close, other = FRAMES[frame]
    assert not mod.ts_perment_20(close).equals(ts_perment_20(close))  # live
    hits = _caught(mod.ts_perment_20, close, other)
    assert len(hits) > 0
    if caught == 37:
        assert len(hits) == 37
    else:
        assert abs(len(hits) - caught) <= 4


@pytest.mark.parametrize("index,length,caught", [
    (0, 10, 29), (1, 10, 37), (2, 10, 15), (3, 10, 37), (4, 10, 20),
    (0, 60, 30), (1, 60, 37), (2, 60, 21), (3, 60, 36), (4, 60, 20),
    (0, 4, 22), (1, 4, 25), (2, 4, 7), (3, 4, 22), (4, 4, 11),
], ids=[f"{MUTANT_IDS[i]}-{n}" for i, n, _ in [
    (0, 10, 0), (1, 10, 0), (2, 10, 0), (3, 10, 0), (4, 10, 0),
    (0, 60, 0), (1, 60, 0), (2, 60, 0), (3, 60, 0), (4, 60, 0),
    (0, 4, 0), (1, 4, 0), (2, 4, 0), (3, 4, 0), (4, 4, 0)]])
def test_the_mutants_at_non_default_lengths(index, length, caught):
    """The same five mutants on the walk at `length` 10, 60 and 4. The real
    module leaks 0/37 at each (asserted in
    `test_real_module_never_reads_the_future_at_other_lengths`); every
    mutant is still caught, and the catch rate FALLS with the window --
    at `length=4` a window holds two triples, so there is very little for a
    perturbation to disturb."""
    close, other = FRAMES["walk"]
    mod = _load_mutant(*MUTANTS[index])

    def mutated(c):
        return mod.ts_perment_20(c, length=length)

    def real(c):
        return ts_perment_20(c, length=length)

    assert not mutated(close).equals(real(close))
    hits = _caught(mutated, close, other)
    assert len(hits) > 0
    if caught == 37:
        assert len(hits) == 37
    else:
        assert abs(len(hits) - caught) <= 5


@pytest.mark.parametrize("frame", sorted(FRAMES))
def test_a_missed_mutant_offset_is_an_unchanged_code_or_a_permutation(frame):
    """WHY the one-triple leak is missed at an offset, measured rather than
    excused.

    The `forward_triple` mutant writes bar T from a window that ends one
    triple late, so at offset J the only prefix bar that can move is J-1,
    and only if the perturbation changes the CODE of the triple ending at
    bar J. Every missed offset is therefore one of exactly two things:

    * the code is unchanged -- the mutant's window is identical bar for bar,
      so there is nothing to detect. Every such offset is missed, which this
      test asserts as a set inclusion rather than a count;
    * the code changed and the window's count vector moved to a PERMUTATION
      of itself. The entropy is a symmetric function of the counts, so the
      value cannot see it.
    """
    close, other = FRAMES[frame]
    mod = _load_mutant(*FORWARD_TRIPLE)
    hits = set(_caught(mod.ts_perment_20, close, other))
    miss = [j for j in OFFSETS if j not in hits]
    assert miss, "the sweep is supposed to be insensitive at some offsets"

    base_codes = _codes(close.to_numpy())
    same_code, absorbed = [], []
    for j in OFFSETS:
        p = close.copy()
        p.iloc[j:] = other.iloc[j:].values
        pc = _codes(p.to_numpy())
        if base_codes[j - 2] == pc[j - 2]:
            same_code.append(j)
            continue
        if j in hits:
            continue
        lo = j - 1 - TRIPLES  # the mutant's window at bar J-1
        cb = sorted(int((base_codes[lo:j - 1] == k).sum()) for k in PATTERNS)
        cp = sorted(int((pc[lo:j - 1] == k).sum()) for k in PATTERNS)
        absorbed.append((j, cb == cp))

    assert set(same_code) <= set(miss)
    assert sorted(set(same_code) | {j for j, _ in absorbed}) == miss
    assert absorbed, "no offset exercised the permutation case"
    assert all(perm for _, perm in absorbed)


def test_a_positive_offset_only_delays_and_a_negative_one_is_the_callers_ask():
    """`offset` is this fork's standard parameter and a negative one is a
    user-reachable look-ahead -- the caller's explicit request, not a
    property of the formula, whose default `offset=0` the sweep covers."""
    close = _walk(400, seed=3)
    base = ts_perment_20(close)
    pd.testing.assert_series_equal(ts_perment_20(close, offset=2),
                                   base.shift(2), check_names=False)
    pd.testing.assert_series_equal(ts_perment_20(close, offset=-2),
                                   base.shift(-2), check_names=False)


# ------------------------------------------------------------- Gate C/D


@pytest.mark.parametrize("frame_fn", ALL_FRAMES)
@pytest.mark.parametrize("k", [8.0, 64.0, 1024.0])
def test_a_power_of_two_price_scale_is_bit_identical(frame_fn, k):
    """x8 and x64 are Gate D's requirement, and here they are trivial rather
    than lucky: the column reads only comparisons, and `8a < 8b` is `a < b`
    exactly. Asserted on seven frames, including two with ties."""
    close = frame_fn()
    base, scaled = ts_perment_20(close), ts_perment_20(close * k)
    assert bool((base.isna() == scaled.isna()).all())
    m = base.notna()
    assert int(m.sum()) == 1481
    assert int((base[m] == scaled[m]).sum()) == 1481


@pytest.mark.parametrize("frame_fn", ALL_FRAMES)
@pytest.mark.parametrize("k", [10.0, 3.7, 0.1])
def test_other_price_scales_are_bit_identical_too(frame_fn, k):
    """x10 and x3.7 round each close, and rounding is monotone, so the order
    survives -- a scale can only destroy information by COLLAPSING two
    closes onto one double, and then only when the earlier close is the
    larger (the tie rule makes a collapse invisible in the other
    direction). On these seven frames none collapses: 1481 of 1481 bars
    bit-identical."""
    close = frame_fn()
    base, scaled = ts_perment_20(close), ts_perment_20(close * k)
    m = base.notna()
    assert int((base[m] == scaled[m]).sum()) == 1481


@pytest.mark.parametrize("length", [4, 10, 60, 250])
def test_a_price_scale_is_bit_identical_at_non_default_lengths(length):
    close = _walk()
    base = ts_perment_20(close, length=length)
    scaled = ts_perment_20(close * 8.0, length=length)
    m = base.notna()
    assert int(m.sum()) == 1500 - length + 1
    assert int((base[m] == scaled[m]).sum()) == int(m.sum())


@pytest.mark.parametrize("name,fn", [
    ("log", np.log), ("sqrt", np.sqrt), ("cube", lambda x: x ** 3),
    ("shift", lambda x: x + 1000.0),
])
def test_any_strictly_increasing_transform_of_price_is_bit_identical(name, fn):
    """Scale-free understates it: the column is INVARIANT TO THE PRICE AXIS.
    Taking logs, square roots, cubes or adding a constant leaves it
    bit-identical on 1481 of 1481 bars, because every one of those maps the
    order relations onto themselves."""
    close = _walk()
    base = ts_perment_20(close)
    other = ts_perment_20(Series(fn(close.to_numpy()), index=close.index))
    m = base.notna()
    assert int((base[m] == other[m]).sum()) == 1481


def test_a_drift_is_not_such_a_transform():
    """The invariance above is per-value, so it says nothing about adding
    drift -- which re-orders closes against each other and really does move
    the column (Spearman 0.21). Pinned so "invariant to the price axis" can
    never be read as "invariant to the path"."""
    close = _walk()
    drifted = Series(close.to_numpy() * np.exp(0.004 * np.arange(len(close))),
                     index=close.index)
    base, other = ts_perment_20(close), ts_perment_20(drifted)
    m = base.notna() & other.notna()
    rho = float(base[m].corr(other[m], method="spearman"))
    assert rho == pytest.approx(0.2108, abs=0.05)
    assert int((base[m] == other[m]).sum()) < 100


@pytest.mark.parametrize("frame_fn,lo,hi,median,zeros", [
    (_walk, 0.5566, 1.7729, 1.6188, 0),
    (_tick_rounded, 0.7608, TOP, 1.6188, 0),
    (_coarse_grid, 0.6837, TOP, 1.5654, 0),
    (_heavy_tailed, 0.7608, TOP, 1.6425, 0),
    (_two_point, 0.8676, 1.3801, 1.3220, 0),
    (_mean_reverting, 0.9580, TOP, 1.6731, 0),
    (_trending, 0.0, 0.6837, 0.0, 1236),
])
def test_fires_and_is_not_constant(frame_fn, lo, hi, median, zeros):
    """Gate D's `0 < fires < n`, and the shape of the range on seven frames.

    The `trending` row is the one worth reading twice: a path with a 2.5
    sigma-a-bar drift is nearly monotone, so the column sits at exactly 0.0
    on 1,236 of its 1,481 bars. A column that is 0 for a whole regime is
    still informative, but it is NOT a volatility reading.
    """
    close = frame_fn()
    out = ts_perment_20(close)
    fires = int(out.notna().sum())
    assert 0 < fires < len(close)
    assert fires == 1481
    x = out.dropna()
    assert float(x.min()) == pytest.approx(lo, abs=1e-2)
    assert float(x.max()) == pytest.approx(hi, abs=1e-2)
    assert float(x.median()) == pytest.approx(median, abs=1e-2)
    assert abs(int((x == 0.0).sum()) - zeros) <= max(5, zeros // 10)
    assert float(x.max()) <= TOP
    assert float(x.min()) >= 0.0
    assert int(x.nunique()) > 1


def test_the_column_cannot_see_magnitude():
    """The property a consumer is most likely to get wrong, measured three
    ways: planting a +10, a +50 and a +1000 sigma return at the same bar
    gives a BIT-IDENTICAL column, because all three put that close above
    everything around it and the ordering is all the column reads."""
    close = _walk()
    base = ts_perment_20(close)
    outs = []
    for size in (10.0, 50.0, 1000.0):
        c = close.to_numpy().copy()
        c[700] = c[700] * (1.0 + size * 0.015)
        outs.append(ts_perment_20(Series(c, index=close.index)))
    assert outs[0].equals(outs[1])
    assert outs[0].equals(outs[2])
    # How MANY bars move depends on the last bits of the generated frame, so
    # it carries a tolerance (15 locally); what is pinned exactly is the
    # structural bound -- a spike at one bar can only reach the `length`
    # windows that hold it.
    moved = int((outs[0].dropna() != base.dropna()).sum())
    assert 0 < moved <= LENGTH  # 15 locally, 10 on a CI runner


def test_price_granularity_is_an_input():
    """The same path on a coarser grid is a different column (Spearman
    0.3796 at 46% tied triples; 0.9912 at 0.7%). Stated in the test because
    a consumer reading "invariant to the price axis" would otherwise expect
    rounding to be free."""
    fine = ts_perment_20(_walk(sigma=0.002, seed=55))
    coarse = ts_perment_20(_coarse_grid())
    m = fine.notna() & coarse.notna()
    assert float(fine[m].corr(coarse[m], method="spearman")) == pytest.approx(
        0.3796, abs=0.05)

    walk = ts_perment_20(_walk())
    ticked = ts_perment_20(_tick_rounded(seed=11))
    m = walk.notna() & ticked.notna()
    assert float(walk[m].corr(ticked[m], method="spearman")) > 0.95


# ------------------------------------------------- the attainable values


def _satisfying_count_vectors(triples):
    """Count vectors reachable under the one structural constraint:
    consecutive triples share a comparison, so bit B of one code is bit A of
    the next."""
    states = {((k >> 1) & 1,
               tuple(1 if p == k else 0 for p in PATTERNS)): True
              for k in PATTERNS}
    for _ in range(triples - 1):
        nxt = {}
        for bit, counts in states:
            for k in PATTERNS:
                if ((k >> 2) & 1) != bit:
                    continue
                c = list(counts)
                c[PATTERNS.index(k)] += 1
                nxt[(((k >> 1) & 1), tuple(c))] = True
        states = nxt
    return {counts for _, counts in states}


def _realised_count_vectors(length):
    out = set()
    for perm in itertools.permutations(range(1, length + 1)):
        codes = _codes(np.asarray(perm, dtype=float))
        out.add(tuple(int((codes == k).sum()) for k in PATTERNS))
    return out


@pytest.mark.parametrize("length,count", [(6, 63), (7, 116)])
def test_the_structural_constraint_is_exactly_attainability_at_small_lengths(
        length, count):
    """Exhaustive over all orderings of 6 and 7 distinct closes: the count
    vectors a permutation can realise are EXACTLY those satisfying the
    shared-comparison constraint, 63 of 63 and 116 of 116. That is the
    evidence behind using the constraint as the attainable set at length 20,
    where exhaustion is not possible -- it is evidence at two lengths, not a
    proof at twenty."""
    realised = _realised_count_vectors(length)
    satisfying = _satisfying_count_vectors(length - 2)
    assert len(realised) == count
    assert realised == satisfying


def test_the_attainable_set_at_the_shipped_length():
    """5,978 count vectors, 175 distinct values to 1e-12, spanning exactly
    0.0 to the ceiling. Every value the module emits on four frames is in
    that set at 1e-12 and the raw float64 values are NOT, which is the
    accumulation detail of item 2 showing up as data."""
    satisfying = _satisfying_count_vectors(TRIPLES)
    assert len(satisfying) == 5978
    values = {round(_accumulate(c), 12) for c in satisfying}
    assert len(values) == 175
    assert min(values) == 0.0
    assert max(values) == pytest.approx(TOP, abs=1e-12)

    for frame_fn in (_walk, _tick_rounded, _coarse_grid, _heavy_tailed):
        out = ts_perment_20(frame_fn()).dropna()
        observed = {round(float(v), 12) for v in out}
        assert observed <= values
        assert int(out.nunique()) > len(observed) > 1


def test_random_orderings_reach_a_fraction_of_the_set_including_the_ceiling():
    """200,000 random orderings of 20 distinct closes reach 2,814 of the
    5,978 count vectors -- random orderings concentrate on the high-entropy
    ones -- and every vector they reach satisfies the constraint. The even
    split is among them, which is the second proof that the ceiling is
    attained."""
    rng = np.random.default_rng(5)
    base = np.arange(1.0, LENGTH + 1.0)
    satisfying = _satisfying_count_vectors(TRIPLES)
    seen = set()
    for _ in range(200000):
        codes = _codes(rng.permutation(base))
        seen.add(tuple(int((codes == k).sum()) for k in PATTERNS))
    assert seen <= satisfying
    assert abs(len(seen) - 2814) <= 100
    assert tuple([3] * 6) in seen


# -------------------------------------------------------- edges, guards


def test_insufficient_history_returns_none():
    close = _walk(400, seed=3)
    assert ts_perment_20(close.iloc[:LENGTH - 1]) is None
    assert ts_perment_20(close.iloc[:3], length=4) is None


def test_exact_min_history_fires_at_the_warmup_boundary():
    """Exactly `length` closes produce exactly one value, at bar
    `length - 1`: the window is 20 closes and 18 triples, so no bar is
    wasted and none is borrowed."""
    close = _walk(400, seed=3)
    out = ts_perment_20(close.iloc[:LENGTH])
    assert int(out.notna().sum()) == 1
    assert int(out.notna().to_numpy().argmax()) == LENGTH - 1
    assert 0.0 <= float(out.iloc[-1]) <= TOP
    assert int(ts_perment_20(close).notna().to_numpy().argmax()) == LENGTH - 1


@pytest.mark.parametrize("length", [None, 0, 1, 2, 3, -5, 3.9])
def test_a_length_below_the_minimum_falls_back_to_the_default(length):
    """`MIN_LENGTH` is 4 because a three-close window holds ONE triple, whose
    histogram has one bin and whose entropy is the constant 0."""
    close = _walk(400, seed=3)
    assert ts_perment_20(close, length=length).name == "TS_PERMENT_20_3"
    assert _REAL.MIN_LENGTH == 4


def test_the_smallest_window_takes_exactly_two_values():
    """At `length=4` a window holds two triples, so the column is
    `0` (both the same ordering) or `log 2` (two different ones) and nothing
    else -- the floor of usefulness, which is why 4 is the minimum rather
    than 3."""
    out = ts_perment_20(_walk(400, seed=3), length=4).dropna()
    assert int(out.notna().sum()) == 397
    assert sorted(out.round(12).unique()) == [0.0,
                                              round(math.log(2.0), 12)]


@pytest.mark.parametrize("bad", [np.nan, np.inf, -np.inf])
def test_a_close_that_is_not_finite_empties_exactly_its_own_windows(bad):
    """A non-finite close has no place in an ordering (every comparison
    against a NaN is False, which would read as "greater than everything"),
    so it is masked. It sits in 3 triples and therefore in exactly `length`
    windows -- bars 200 to 219 for a bad close at 200 -- and nothing
    earlier moves."""
    close = _walk(400, seed=3)
    base = ts_perment_20(close)
    c = close.to_numpy().copy()
    c[200] = bad
    out = ts_perment_20(Series(c, index=close.index))
    emptied = [int(i) for i in np.flatnonzero(out.isna() & base.notna())]
    assert emptied == list(range(200, 200 + LENGTH))
    # nothing before the bad close moves, and nothing after bar 219 either
    head = base.iloc[:200].notna()
    assert bool((base.iloc[:200][head] == out.iloc[:200][head]).all())
    tail = base.iloc[220:].notna()
    assert bool((base.iloc[220:][tail] == out.iloc[220:][tail]).all())


@pytest.mark.parametrize("bad", [0.0, -5.0, 1e-310])
def test_a_non_positive_or_subnormal_close_is_not_rejected(bad):
    """Deliberately unlike `ts_binent_20` and `ts_c3_20`, which need a return
    and so need positivity. This column takes no ratio and no logarithm, so
    a zero, a negative or a subnormal close still has a well-defined place
    in the ordering -- and all three are BELOW every neighbour, so all three
    give the same value."""
    close = _walk(400, seed=3)
    c = close.to_numpy().copy()
    c[200] = bad
    out = ts_perment_20(Series(c, index=close.index))
    assert int(out.notna().sum()) == 400 - LENGTH + 1
    assert float(out.iloc[200]) == pytest.approx(1.706057115643, abs=1e-12)


def test_fractional_lengths_that_truncate_the_same_are_identical():
    close = _walk(400, seed=3)
    assert ts_perment_20(close, length=4.9).equals(
        ts_perment_20(close, length=4))


def test_distinct_lengths_produce_distinct_names_and_values():
    close = _walk(400, seed=3)
    a, b = ts_perment_20(close, length=20), ts_perment_20(close, length=40)
    assert (a.name, b.name) == ("TS_PERMENT_20_3", "TS_PERMENT_40_3")
    m = a.notna() & b.notna()
    assert int((a[m] != b[m]).sum()) > 0


def test_fillna_applies():
    close = _walk(400, seed=3)
    assert int(ts_perment_20(close, fillna=0).isna().sum()) == 0


def test_the_dimension_and_tau_are_fixed_and_named_in_the_column():
    """The issue fixes order 3 and tau 1, so neither is a parameter; the 3 is
    in the column name so a later order cannot silently reuse it."""
    assert (_REAL.DIMENSION, _REAL.TAU, _REAL.LEGS) == (3, 1, 2)
    assert ts_perment_20(_walk(400, seed=3)).name.endswith("_3")


# ------------------------------------------------------------- wiring


def test_name_registration_and_accessor():
    """Touch points 2, 3 and 4: the export, `Category`, and `df.ta`."""
    close = _walk(400, seed=3)
    assert "ts_perment_20" in pandas_ta.Category["statistics"]
    assert callable(getattr(pandas_ta, "ts_perment_20", None))
    df = pd.DataFrame({"close": close.to_numpy()})
    out = df.ta.ts_perment_20()
    assert out.name == "TS_PERMENT_20_3"
    assert out.equals(ts_perment_20(df["close"]))
    assert getattr(out, "category", None) == "statistics"


def test_the_accessor_forwards_length_under_the_right_name():
    """The `supertrend` failure mode: a keyword forwarded under the wrong
    name computes the default and nobody notices."""
    close = _walk(400, seed=3)
    df = pd.DataFrame({"close": close.to_numpy()})
    assert df.ta.ts_perment_20(length=40).name == "TS_PERMENT_40_3"
    assert df.ta.ts_perment_20(length=40).equals(
        ts_perment_20(df["close"], length=40))
