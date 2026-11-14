# -*- coding: utf-8 -*-
"""TS-REOCCUR-20: `ts_reoccur_20`, the share of a 20-close window's bars
whose close repeats inside that window (PandasTa issue #103).

    x            = close[T - 19 .. T]
    TS_REOCCUR   = #{ i : x[i] == x[j] for some j != i } / 20

WHAT THIS FILE PINS, in order of how much it would hurt to lose.

1. **Gate A, and it is EXACT.** The module's only arithmetic is one
   integer count divided by `length`, so there is no tolerance to argue
   about: a per-window `pandas.Series.value_counts()` oracle and the
   screen prototype's sort-and-compare agree with it on **11,848 of
   11,848** fired bars over eight frames, masks included, and at `length`
   2, 3, 5, 21, 60 and 250.
   ⚠ tsfresh is NOT installed here and web access is unavailable
   (`test_the_source_library_is_not_installed_here` records that, so the
   claim cannot rot into "checked against tsfresh"). What Gate A checks is
   the quantity the source's NAME states -- "# of data points occurring
   more than once / # of all data points" -- spelled two independent ways.
   The function name and the 20 are the issue's own.

2. **That it is a TICK-GRID feature, which is the one thing a consumer
   can get wrong.** On a continuous-float walk the column is identically
   0.0 -- 1,481 fired bars, 1 distinct value, at price 1, 100 and 1e+6 --
   and the same path on a 0.01 grid at price 1 reads mean 0.7067. The
   level is set by how many TICKS the price moves in a bar: mean 0.9124
   at 1 tick, 0.4890 at 5, 0.1682 at 20 and 0.0379 at 100 (20,000 bars per
   step). Pinned as a MONOTONE table plus bands, because the frames are
   built with `np.exp` / `np.round` and a reduced-kernel run moves their
   last bits.
   ⚠ The grid is not part of the column, so two instruments whose tick is
   a different fraction of their price are not comparable on it: the same
   path at price 5 and price 500 on a 0.01 grid reads mean 0.2254 and
   0.0037.

3. **Gate B as six mutants, five of which the blind sweep under-catches --
   and that is itself the finding.** Every look-ahead mutant is the real
   column back-dated by a DERIVED number of bars, checked bit for bit
   (1,462 .. 1,480 of 1,462 .. 1,480 bars on each of four frames). The
   prefix sweep then catches them at only 1 .. 36 of 36 offsets, because
   the column lives on a 21-point lattice and a one-bar shift often lands
   on the same value: the catch rate tracks the frame's churn (0.6466 of
   adjacent bars change on `grid-2tick`, 0.1128 on `grid-40tick`, and
   `write_index_earlier` is caught 21 and 1 times there).
   The sixth mutant shifts the bad-close mask's own index and is caught
   **0 of 36** by the sweep on every clean frame -- it changes nothing when
   no close is bad -- and 12 of 12 on a frame with a bad close at each
   offset, where it moves exactly bar `J - 1`.

4. **Gate D, where x8/x64 is exactness and x10 is a measurement.** A
   x2^k rescale is exact, so it cannot merge or split a tie: bit-identical
   on 11,848 of 11,848 bars over eight frames at both factors, at `length`
   2 / 3 / 5 / 21 / 60 / 250 and at price levels 1e-6, 1e+6 and 1e+100.
   x10 / x3.7 / x0.1 / x1.0000001 are not exact and CAN merge two closes
   that differ in their last bits -- never split a tie, since equal
   doubles scale to the same double -- and measured bit-identical on all
   11,848, with 0 merges in all 32 frame-and-factor cells counted
   separately (bit-equality does not imply it: a merge inside a window
   where both closes already had a twin changes nothing). A frame of 20 consecutive doubles starting at 1.9 does
   merge under x10 (13 of 20 distinct, column 0.00 -> 0.70) and does not
   from 1.0, which is the ulp argument measured rather than asserted.

5. **The guards.** A bad close (NaN, inf, -inf, 0.0, -100.0, 5e-324)
   empties the `length` windows that hold it and nothing earlier: 36
   (value, position) pairs, 0 earlier bars moved, 1 / 2 / 19 / 20 / 2 / 1
   windows emptied at bar 0 / 1 / 18 / 200 / 398 / 399. The chunk budget
   is invisible: `CHUNK_VALUES` 1, 20, 999 and 10**9 give an identical
   column. A flat frame reads exactly 1.0 and a one-tick-a-bar ladder
   exactly 0.0 -- readings, not missing data.

6. **The variants, priced rather than assumed.** The sibling tsfresh
   function `percentage_of_reoccurring_values_to_all_values` (distinct
   values rather than bars) is a DIFFERENT column -- 1 to 1,346 of 1,481
   bars equal -- that is nearly rank-identical, |rho| 0.9726 .. 1.0000.
   `distinct / length` is a near-mirror (|rho| 0.9268 .. 1.0000, 0 to 112
   bars equal). `has_duplicate`, the boolean, is CONSTANT on 3 of the 7
   grid frames. An equality tolerance of 1e-12 changes nothing; 1e-4
   changes only the price-100 frame, where 1e-4 relative IS one tick.
   The same statistic over 20 RETURNS is a different column, |rho|
   0.1637 .. 0.6553.

7. **What it overlaps.** It is negative volatility measured in ticks.
   Against the window's own `stdev(close, 20)`: per-frame |rho| median
   0.7974 (0.6963 .. 0.8533) over seven same-regime frames, where the
   screen's REAL figure on 89 BIST frames was 0.7222 against the engine's
   `stdev`. Against `LOT_ZERORET_20` / `LOT_ZERORET_60`, the share of
   ZERO RETURNS in the same window, the per-frame median is 0.5185 /
   0.4991. ⚠ POOLING ACROSS TICK REGIMES INFLATES the zero-return pair
   (0.7962 / 0.8427 pooled over the seven mixed frames against 0.6710 /
   0.7037 within one regime) and DEFLATES the stdev pair (0.4746 against
   0.8862), so a pooled synthetic number here is a frame-mix artefact and
   not a forecast of Gate E.

8. **Order-blindness.** The column reads the window's MULTISET: 2,000
   random permutations of one window leave it bit-identical, and a
   reversed frame gives the column reversed, bit for bit on 1,481 of
   1,481 bars. So it cannot see trend, sign, or where in the window a
   repeat sat.

9. **The lattice.** The output is `k / length`, and `k = 1` is
   unreachable: a close with a twin contributes at least two bars.
   Measured at `length` 2, 3, 20 and 60 over eight frames -- `k = 1`
   absent at every one.

10. **Gate E is OWED.** `test_the_gate_e_row_is_owed` asserts the ledger
    has NO row for this indicator, which is what
    `tests/test_gate_e_ledger.py` reports as owed and what the receipt
    session replaces with the measured row. Gate C's real-data counts come
    from the same run.

Every number above is printed by `python docs/measure_ts_reoccur_20.py`,
and `python docs/measure_ts_reoccur_20_cpu.py` re-runs this module -- and
any named section -- with `NPY_DISABLE_CPU_FEATURES="AVX512F AVX512_SKX
AVX2 FMA3"`. `docs/TsReoccur20Measured.md` carries the tables.
"""
import importlib
import importlib.util
import types

import numpy as np
import pandas as pd
import pytest
from numpy.lib.stride_tricks import sliding_window_view
from pandas import Series

from .context import pandas_ta
from pandas_ta.statistics.lot_zeroret_60 import lot_zeroret_60
from pandas_ta.statistics.stdev import stdev
from pandas_ta.statistics.ts_reoccur_20 import (CHUNK_VALUES, MIN_LENGTH,
                                                ts_reoccur_20)

#: The module, not the function `pandas_ta/statistics/__init__.py` binds
#: over it in the package namespace.
MODULE = importlib.import_module("pandas_ta.statistics.ts_reoccur_20")

LENGTH = 20
N = 1500
FIRED = N - LENGTH + 1          # `length` CLOSES, so the warm-up is 19


# ----------------------------------------------------------------- frames


def _walk(n=N, seed=11, sigma=0.02, price=100.0, drift=0.0):
    rng = np.random.default_rng(seed)
    return Series(price * np.exp(np.cumsum(rng.normal(drift, sigma, n))))


def _grid(close, tick=0.01):
    return Series(np.round(close.to_numpy() / tick) * tick,
                  index=close.index)


def _level(price, seed=11, tick=0.01, sigma=0.02, n=N):
    """One 2% walk read at a BIST-like price level on a 0.01 grid. The
    price level IS the tick regime: 2% of 1.00 is two ticks, 2% of 100.00
    is two hundred."""
    return _grid(_walk(n, seed, sigma, price), tick)


def _range_bound(n=N, seed=7, price=2.0, tick=0.01, sigma=0.02, phi=0.90):
    rng = np.random.default_rng(seed)
    x = np.zeros(n)
    for t in range(1, n):
        x[t] = phi * x[t - 1] + rng.normal(0.0, sigma)
    return _grid(Series(price * np.exp(x)), tick)


def _heavy_tailed(n=N, seed=3, df=2.0, sigma=0.01, price=2.0, tick=0.01):
    rng = np.random.default_rng(seed)
    r = np.clip(sigma * rng.standard_t(df, n), -0.5, 0.5)
    return _grid(Series(price * np.cumprod(1.0 + r)), tick)


def _round_numbers(n=N, seed=9, price=1000.0, tick=1.0, sigma=0.003):
    return _grid(_walk(n, seed, sigma, price), tick)


def _continuous(n=N, seed=11, price=100.0):
    return _walk(n, seed, price=price)


def _flat(n=300, price=100.0):
    return Series(np.full(n, price))


def _ladder(n=300, price=100.0, tick=0.01):
    return Series(price + tick * np.arange(n, dtype=float))


def _two_level(n=300, seed=4, price=100.0, tick=0.01):
    rng = np.random.default_rng(seed)
    return Series(np.where(rng.random(n) < 0.5, price, price + tick))


FRAMES = {
    "grid-2tick": lambda: _level(1.0),
    "grid-10tick": lambda: _level(5.0),
    "grid-40tick": lambda: _level(20.0),
    "grid-200tick": lambda: _level(100.0),
    "range-bound": _range_bound,
    "round-1000": _round_numbers,
    "heavy-tailed": _heavy_tailed,
    #: The continuous frame belongs in Gate A / B / D: the column is a
    #: constant 0.0 there and bit-equality to the oracle still means
    #: something. It is NOT in `VARYING`.
    "continuous": _continuous,
}
NAMES = list(FRAMES)
VARYING = [n for n in NAMES if n != "continuous"]


# ---------------------------------------------------------------- helpers


TINY = np.finfo(float).tiny


def _good(w):
    return np.isfinite(w) & (w >= TINY)


def _spearman(a, b):
    m = a.notna() & b.notna()
    if int(m.sum()) < 3 or a[m].nunique() < 2 or b[m].nunique() < 2:
        return float("nan")
    return float(a[m].corr(b[m], method="spearman"))


def _agree(a, b):
    """(masks equal, shared count, bit-equal count, max |difference|)."""
    masks = bool((a.isna() == b.isna()).all())
    m = a.notna() & b.notna()
    d = float((a[m] - b[m]).abs().max()) if int(m.sum()) else float("nan")
    return masks, int(m.sum()), int((a[m] == b[m]).sum()), d


# ---------------------------------------------------------------- oracles


def _source_windowed(close, length=LENGTH):
    """The quantity the source's name states, through pandas' own counter,
    one window at a time:
    `value_counts()[value_counts() > 1].sum() / len(x)`. Shares no code
    with the module. The `_good` test is this fork's missing-data rule,
    which `test_the_missing_data_rule_is_the_forks_and_not_the_sources`
    prices separately."""
    c = close.to_numpy(dtype=float)
    out = np.full(c.size, np.nan)
    for t in range(length - 1, c.size):
        w = c[t - length + 1:t + 1]
        if not _good(w).all():
            continue
        vc = Series(w).value_counts()
        out[t] = vc[vc > 1].sum() / w.size
    return Series(out, index=close.index)


def _source_literal(close, length=LENGTH):
    """The same with NO missing-data rule, which is also what the screen
    prototype does: `value_counts()` drops a NaN and `len(x)` keeps
    counting it, so a window holding a bad close reads a DEFLATED share
    instead of nothing."""
    c = close.to_numpy(dtype=float)
    out = np.full(c.size, np.nan)
    for t in range(length - 1, c.size):
        w = Series(c[t - length + 1:t + 1])
        vc = w.value_counts()
        out[t] = vc[vc > 1].sum() / w.size
    return Series(out, index=close.index)


def _prototype(close, length=LENGTH):
    """`docs/issues/screen/ind_screen.py`, candidate `ts_reoccur_20`:
    `roll(c, 20, w_pct_reoccurring)`, retyped from that file (which is
    gitignored, so it is on the owner's machine only)."""
    a = close.to_numpy(dtype=float)
    W = sliding_window_view(a, length) if len(a) >= length \
        else np.empty((0, length))
    S = np.sort(W, 1)
    eq = S[:, 1:] == S[:, :-1]
    dup = np.zeros_like(S, dtype=bool)
    dup[:, 1:] |= eq
    dup[:, :-1] |= eq
    out = np.full(len(a), np.nan)
    out[length - 1:] = dup.mean(1)
    return Series(out, index=close.index)


def _windowed(close, length, f):
    c = close.to_numpy(dtype=float)
    out = np.full(c.size, np.nan)
    for t in range(length - 1, c.size):
        w = c[t - length + 1:t + 1]
        if not _good(w).all():
            continue
        out[t] = f(w)
    return Series(out, index=close.index)


def _values_variant(close, length=LENGTH):
    """tsfresh's sibling `percentage_of_reoccurring_values_to_all_values`:
    repeated DISTINCT values over distinct values."""
    def f(w):
        _, counts = np.unique(w, return_counts=True)
        return np.sum(counts > 1) / float(counts.size)
    return _windowed(close, length, f)


def _distinct_variant(close, length=LENGTH):
    """tsfresh's `ratio_value_number_to_time_series_length`."""
    return _windowed(close, length,
                     lambda w: np.unique(w).size / float(w.size))


def _tolerant(close, length=LENGTH, rel=1e-12):
    def f(w):
        s = np.sort(w)
        eq = np.isclose(s[1:], s[:-1], rtol=rel, atol=0.0)
        dup = np.zeros(s.size, dtype=bool)
        dup[1:] |= eq
        dup[:-1] |= eq
        return dup.sum() / float(s.size)
    return _windowed(close, length, f)


def _on_returns(close, length=LENGTH):
    """The same statistic over `length` RETURNS. A return can be negative,
    so `_good` does not apply; and `length` returns need `length + 1`
    closes, so this variant fires one bar later than the module."""
    r = (close / close.shift(1) - 1.0).to_numpy()
    out = np.full(r.size, np.nan)
    for t in range(length, r.size):
        w = r[t - length + 1:t + 1]
        if not np.isfinite(w).all():
            continue
        s = np.sort(w)
        eq = s[1:] == s[:-1]
        dup = np.zeros(s.size, dtype=bool)
        dup[1:] |= eq
        dup[:-1] |= eq
        out[t] = dup.sum() / float(s.size)
    return Series(out, index=close.index)


# ======================================================== Gate A, the source


def test_the_source_library_is_not_installed_here():
    """What Gate A checks is the quantity the source's NAME states, spelled
    two ways, not a run of tsfresh. Pinned so the claim cannot rot into
    "checked against tsfresh" if the dependency ever appears."""
    assert importlib.util.find_spec("tsfresh") is None


@pytest.mark.parametrize("name", NAMES)
def test_gate_a_is_bit_equal_to_the_sources_own_quantity(name):
    """A per-window `value_counts()` oracle and the screen prototype, on
    every frame. 1,481 of 1,481 bars each, 11,848 pooled over the eight.

    This is bit-equality rather than a tolerance because the module's only
    arithmetic is `count / length` -- two exact integers, one correctly
    rounded division -- and both oracles divide the same two."""
    close = FRAMES[name]()
    col = ts_reoccur_20(close)
    masks, shared, same, d = _agree(col, _source_windowed(close))
    assert masks
    assert shared == FIRED
    assert same == shared, f"{shared - same} bars differ, max |diff| {d}"
    masks, shared, same, d = _agree(col, _prototype(close))
    assert masks and shared == FIRED
    assert same == shared, f"prototype: {shared - same} differ, max {d}"


@pytest.mark.parametrize("length", [MIN_LENGTH, 3, 5, 21, 60, 250])
def test_gate_a_is_bit_equal_to_the_source_at_other_lengths(length):
    close = _level(1.0)
    for oracle in (_source_windowed, _prototype):
        masks, shared, same, d = _agree(ts_reoccur_20(close, length=length),
                                        oracle(close, length=length))
        assert masks
        assert shared == N - length + 1
        assert same == shared, f"{shared - same} differ, max |diff| {d}"


@pytest.mark.parametrize("length", [MIN_LENGTH, 3, LENGTH, 60])
def test_the_output_lives_on_the_k_over_length_lattice_and_skips_one(length):
    """`k = 1` is unreachable: a close with a twin contributes at least two
    bars to the count. Measured over eight frames at four lengths.

    ⚠ The lattice is exact as a RATIONAL, not as a round trip: `count /
    length` is a correctly rounded double, and multiplying it back by
    `length` is a second rounding, which at `length` 60 lands up to
    3.6e-15 off an integer (0.0e+00 at `length` 2, 3 and 20). So `k` is
    recovered with a tolerance -- the claim is about the value, not about
    float multiplication."""
    ks = set()
    for name in NAMES:
        col = ts_reoccur_20(FRAMES[name](), length=length).dropna()
        k = col.to_numpy() * length
        assert float(np.abs(k - np.round(k)).max()) < 1e-9, "off-lattice"
        assert float(col.min()) >= 0.0 and float(col.max()) <= 1.0
        ks |= set(np.round(k).astype(int).tolist())
    assert 1 not in ks, f"length {length}: k = 1 is reachable after all"
    assert 0 in ks or length in ks


@pytest.mark.parametrize("length", [MIN_LENGTH, 3, LENGTH, 60])
def test_the_closed_forms_are_exact(length):
    """A flat frame reads exactly 1.0 and a one-tick-a-bar ladder exactly
    0.0 -- no tolerance, at any length.

    A frame drawn from TWO grid points is the interesting one, and it is
    not simply 1.0: the only way a value fails to have a twin there is to
    appear exactly once, so the reachable set is `{1.0, (length - 1) /
    length}` -- and at `length` 2, where "appears once" means both closes
    differ, `{1.0, 0.0}`. Measured 1.0 on all 281 bars at `length` 20,
    where a run of 20 coin flips hitting one side exactly once is rare."""
    flat = ts_reoccur_20(_flat(300), length=length).dropna()
    lad = ts_reoccur_20(_ladder(300), length=length).dropna()
    assert flat.size == lad.size == 300 - length + 1
    assert (flat == 1.0).all()
    assert (lad == 0.0).all()
    two = ts_reoccur_20(_two_level(300), length=length).dropna()
    allowed = {1.0, 0.0} if length == 2 else {1.0, (length - 1) / length}
    assert set(two.unique().tolist()) <= allowed, two.unique()
    if length == LENGTH:
        assert (two == 1.0).all()


@pytest.mark.parametrize("name", NAMES)
def test_the_values_to_all_values_sibling_is_a_different_column(name):
    """tsfresh ships both functions and the issue names ONE of them. The
    sibling reads DISTINCT values rather than bars: 1 to 1,346 of 1,481
    bars equal across the frames, |rho| 0.9726 .. 1.0000. Nearly
    rank-identical, so the choice barely moves a tree -- but it is not the
    same column, which is why the docstring names which one this is."""
    close = FRAMES[name]()
    base = ts_reoccur_20(close)
    other = _values_variant(close)
    masks, shared, same, d = _agree(base, other)
    assert masks and shared == FIRED
    if name == "continuous":            # both are identically 0.0 there
        assert same == shared
        return
    assert same < shared, "the two functions agreed on every bar"
    assert 0.90 < abs(_spearman(base, other)) <= 1.0


@pytest.mark.parametrize("name", VARYING)
def test_the_distinct_count_variant_is_a_near_mirror(name):
    """`ratio_value_number_to_time_series_length` is NOT the complement of
    this column -- 0 to 112 of 1,481 bars equal, max |difference| up to
    1.0 -- but it is nearly rank-inverse, |rho| 0.9268 .. 1.0000."""
    close = FRAMES[name]()
    base, other = ts_reoccur_20(close), _distinct_variant(close)
    masks, shared, same, _ = _agree(base, other)
    assert masks and shared == FIRED
    rho = _spearman(base, other)
    assert rho < -0.90, rho


@pytest.mark.parametrize("rel,moves", [(1e-12, False), (1e-4, True)])
def test_an_equality_tolerance_would_be_a_different_column(rel, moves):
    """Equality here is EXACT, and that is a decision. A 1e-12 relative
    tolerance changes nothing on any frame. A 1e-4 one changes exactly the
    price-100 frame, because 1e-4 of 100 IS one tick -- so a tolerance at
    the tick scale turns the column into a dispersion measure (|rho|
    0.4339 there)."""
    hit = []
    for name in VARYING:
        close = FRAMES[name]()
        base = ts_reoccur_20(close)
        masks, shared, same, _ = _agree(base, _tolerant(close, rel=rel))
        assert masks and shared == FIRED
        if same != shared:
            hit.append(name)
    assert bool(hit) is moves, hit
    if moves:
        assert hit == ["grid-200tick"], hit


@pytest.mark.parametrize("name", VARYING)
def test_the_same_statistic_on_returns_is_a_different_column(name):
    """The issue says "on 20 closes". On 20 RETURNS instead it is a
    different column -- |rho| 0.1637 .. 0.6553 -- and it fires one bar
    later, because `length` returns need `length + 1` closes."""
    close = FRAMES[name]()
    base, other = ts_reoccur_20(close), _on_returns(close)
    masks, shared, _, _ = _agree(base, other)
    assert not masks and shared == FIRED - 1
    rho = _spearman(base, other)
    assert np.isnan(rho) or abs(rho) < 0.80, rho


def test_the_missing_data_rule_is_the_forks_and_not_the_sources():
    """The one rule the module does not share with the source or the
    prototype. `value_counts()` drops a NaN and keeps `len(x)` in the
    denominator, so a window holding a bad close reports a DEFLATED share;
    this fork empties it. Measured with a bad close at bar 200 of a
    400-bar frame: 361 fired bars here, 381 there, and the 20 bars they
    disagree on read 0.50 .. 0.80."""
    base = _level(1.0, n=400)
    for value in (np.nan, np.inf, 0.0, -100.0, 5e-324):
        c = base.copy()
        c.iloc[200] = value
        mine, lit = ts_reoccur_20(c), _source_literal(c)
        assert int(mine.notna().sum()) == 400 - LENGTH + 1 - LENGTH
        assert int(lit.notna().sum()) == 400 - LENGTH + 1
        only_there = mine.isna() & lit.notna()
        assert int(only_there.sum()) == LENGTH
        assert float(lit[only_there].min()) > 0.0


def test_it_is_order_blind_because_it_reads_the_multiset():
    """2,000 random permutations of one window, bit-identical. The
    frame-level consequence: a reversed frame gives the column reversed,
    bit for bit -- so the column cannot tell a window from its reverse,
    and cannot see trend or sign."""
    rng = np.random.default_rng(5)
    close = _level(1.0)
    w = close.iloc[:LENGTH].to_numpy()
    base = float(ts_reoccur_20(Series(w)).iloc[-1])
    assert 0.0 < base <= 1.0
    for _ in range(2000):
        assert float(ts_reoccur_20(Series(rng.permutation(w)))
                     .iloc[-1]) == base
    for name in NAMES:
        c = FRAMES[name]()
        a = ts_reoccur_20(c).dropna().to_numpy()
        b = ts_reoccur_20(Series(c.to_numpy()[::-1])).dropna().to_numpy()
        assert a.size == b.size == FIRED
        assert np.array_equal(b, a[::-1]), name


# ========================================================= Gate B, by mutant


OFFSETS = range(60, N, 40)              # 36 offsets, past the 19-bar warm-up
BAD_OFFSETS = range(60, N, 120)         # 12 offsets, >= length apart
PAIRS = {
    "grid-2tick": (_level(1.0), _level(1.0, seed=97)),
    "grid-10tick": (_level(5.0), _level(5.0, seed=97)),
    "grid-40tick": (_level(20.0), _level(20.0, seed=97)),
    "range-bound": (_range_bound(), _range_bound(seed=44)),
}

BACK_DATE_TWO = (
    "    share = Series(out, index=close.index)",
    "    share = Series(out, index=close.index).shift(-2)")
BACK_DATE_FULL = (
    "    share = Series(out, index=close.index)",
    "    share = Series(out, index=close.index).shift(-(length - 1))")
WRITE_INDEX_EARLIER = (
    "    out[length - 1:] = val",
    "    out[length - 2:-1] = val")
FORWARD_WINDOW = (
    "    w = sliding_window_view(c, length)",
    "    w = sliding_window_view(np.roll(c, -1), length)")
CENTRED_WINDOW = (
    "    w = sliding_window_view(c, length)",
    "    w = sliding_window_view(np.roll(c, -(length // 2)), length)")
#: The bad-close mask's own index. A real look-ahead, and INVISIBLE to the
#: blind sweep: see `test_gate_b_mutant_the_blind_sweep_cannot_catch`.
SHIFTED_BAD_MASK = (
    "    holds_bad = (nbad[length:] - nbad[:rows]) > 0",
    "    holds_bad = np.roll((nbad[length:] - nbad[:rows]) > 0, -1)")

#: mutant -> (edit, bars it back-dates the column by). The displacement is
#: DERIVED from the edit and then checked bit for bit, which is what makes
#: this Gate B independent of whether the column happens to change at a
#: sweep offset.
MUTANTS = {
    "back_date_two": (BACK_DATE_TWO, 2),
    "back_date_full": (BACK_DATE_FULL, LENGTH - 1),
    "write_index_earlier": (WRITE_INDEX_EARLIER, 1),
    "forward_window": (FORWARD_WINDOW, 1),
    "centred_window": (CENTRED_WINDOW, LENGTH // 2),
}


def _load_mutant(old, new):
    with open(MODULE.__file__, encoding="utf-8") as fh:
        src = fh.read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_ts_reoccur_20_mutant")
    mod.__file__ = MODULE.__file__
    exec(compile(src.replace(old, new), mod.__file__, "exec"), mod.__dict__)
    return mod


def _caught(fn, close, other, offsets=OFFSETS, **kwargs):
    base = fn(close, **kwargs)
    hits = []
    for j in offsets:
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


def _back_dated_by(mutant, real, k, length=LENGTH):
    """(bars compared, bars where the mutant IS the real column read `k`
    bars later). The tail is excluded because `np.roll` wraps."""
    hi = real.size - 1 - k
    a = mutant.iloc[length - 1:hi + 1].to_numpy()
    b = real.iloc[length - 1 + k:hi + 1 + k].to_numpy()
    return a.size, int(((a == b) | (np.isnan(a) & np.isnan(b))).sum())


def _changes(col):
    d = col.dropna().to_numpy()
    return float((d[1:] != d[:-1]).mean())


@pytest.mark.parametrize("name", list(PAIRS))
def test_the_real_module_leaks_nothing_to_the_future(name):
    close, other = PAIRS[name]
    assert _caught(ts_reoccur_20, close, other) == []


@pytest.mark.parametrize("length", [MIN_LENGTH, 7, 60, 250])
def test_the_real_module_leaks_nothing_at_other_lengths(length):
    close, other = PAIRS["grid-2tick"]
    assert _caught(ts_reoccur_20, close, other, length=length) == []
    first = int(ts_reoccur_20(close, length=length)
                .notna().to_numpy().argmax())
    assert first == length - 1


@pytest.mark.parametrize("mutant", list(MUTANTS))
@pytest.mark.parametrize("frame", list(PAIRS))
def test_gate_b_mutant_is_live_and_is_the_column_back_dated(mutant, frame):
    """Each mutant is read out of the real module's source, edited in
    memory and `exec`'d, so it is the shipped code with one write index or
    one read moved. Two things are pinned, and the SECOND is the strong
    one:

    * the blind prefix sweep catches it, but only sometimes -- 1 to 36 of
      36 offsets, because the column lives on a 21-point lattice and a
      shifted value often equals the one it replaced, so the floor
      asserted here is 5 and only on the two high-churn frames;
    * the mutant IS the real column back-dated by the derived number of
      bars, on every bar `np.roll`'s wrap leaves alone. That holds whether
      or not the sweep notices, which is why it is the assertion that
      carries Gate B here."""
    (old, new), k = MUTANTS[mutant]
    mod = _load_mutant(old, new)
    close, other = PAIRS[frame]
    real, got = ts_reoccur_20(close), mod.ts_reoccur_20(close)
    assert not got.equals(real)
    n, same = _back_dated_by(got, real, k)
    assert n > N - LENGTH - k, n
    assert same == n, f"{n - same} of {n} bars are not real(+{k})"
    # ⚠ The sweep's floor is only asserted on the two HIGH-CHURN frames,
    # where the lowest measured count is 21 of 36. On `grid-40tick`
    # `write_index_earlier` is caught exactly ONCE, and the frames are
    # generated with dispatched kernels, so a floor of 1 there would be a
    # test that a different CPU could redden for a reason that has
    # nothing to do with the port.
    caught = len(_caught(mod.ts_reoccur_20, close, other))
    assert caught >= (5 if frame in ("grid-2tick", "range-bound") else 0)


@pytest.mark.parametrize("frame", list(PAIRS))
def test_the_sweeps_catch_rate_is_bounded_by_the_columns_churn(frame):
    """Why the counts above are not 36 of 36. The sweep can only see a
    back-date where the column CHANGES from one bar to the next, and on
    this lattice it often does not: churn 0.6466 / 0.3236 / 0.1128 /
    0.6155 on the four frames, against 27 / 14 / 4 / 31 catches for the
    two-bar back-date. Pinned as an ORDERING plus bands, since the frames
    are generated with dispatched kernels."""
    close, other = PAIRS[frame]
    churn = _changes(ts_reoccur_20(close))
    assert 0.05 < churn < 0.95
    (old, new), _ = MUTANTS["back_date_two"]
    caught = len(_caught(_load_mutant(old, new).ts_reoccur_20, close, other))
    assert 1 <= caught <= len(list(OFFSETS))
    if frame == "grid-40tick":          # the lowest-churn frame of the four
        assert churn < 0.25 and caught < 18
    if frame == "grid-2tick":
        assert churn > 0.45 and caught > 15


def _bad_close_frame(seed=23, value=np.nan):
    """A grid walk with a BAD close at every designed offset -- what the
    shifted-mask mutant needs in order to mis-read anything."""
    c = _level(1.0, seed=seed).to_numpy().copy()
    for j in BAD_OFFSETS:
        c[j] = value
    return Series(c)


def test_gate_b_mutant_the_blind_sweep_cannot_catch():
    """The sixth mutant, and the reason prefix truncation is not a Gate B.
    Shifting the bad-close mask's own index makes bar T empty or not
    according to whether the window ending at T+1 holds a bad close. On a
    frame where no close is bad the mask is all False and the mutant is
    not even LIVE, so the blind sweep catches it 0 of 36 times on each of
    four frames.

    What it CAN move is derived, not searched: a bad close at J spoils the
    windows ending at J .. J+19, so the shifted mask empties the bars
    J-1 .. J+18, and bar J-1 is the only one before J. A frame with a bad
    close at each of 12 offsets catches it 12 of 12 and moves exactly bar
    J-1 at all twelve, under a moved-set definition that is mask flips
    UNION value changes."""
    mod = _load_mutant(*SHIFTED_BAD_MASK)
    for frame, (close, other) in PAIRS.items():
        assert mod.ts_reoccur_20(close).equals(ts_reoccur_20(close)), frame
        assert _caught(mod.ts_reoccur_20, close, other) == [], frame

    close, other = _bad_close_frame(), _level(1.0, seed=97)
    assert _caught(ts_reoccur_20, close, other, BAD_OFFSETS) == []
    hits = _caught(mod.ts_reoccur_20, close, other, BAD_OFFSETS)
    assert len(hits) == len(list(BAD_OFFSETS))
    for j in BAD_OFFSETS:
        p = close.copy()
        p.iloc[j:] = other.iloc[j:].values
        a = mod.ts_reoccur_20(close).iloc[:j]
        b = mod.ts_reoccur_20(p).iloc[:j]
        m = (a.notna() & b.notna())
        changed = (a.isna() != b.isna()).to_numpy()
        changed[m.to_numpy()] |= (a[m] != b[m]).to_numpy()
        assert np.flatnonzero(changed).tolist() == [j - 1], j


# ============================================================ Gate C and D


@pytest.mark.parametrize("name", NAMES)
def test_gate_c_fires_on_every_bar_past_the_warm_up(name):
    col = ts_reoccur_20(FRAMES[name]())
    assert int(col.notna().sum()) == FIRED
    assert int(col.notna().to_numpy().argmax()) == LENGTH - 1
    assert bool(col.iloc[:LENGTH - 1].isna().all())
    assert 0 < int(col.notna().sum()) < col.size


@pytest.mark.parametrize("name", VARYING)
def test_gate_c_is_not_a_constant_and_spans_a_real_range(name):
    """Bands, not counts: which grid point a generated close lands on
    depends on the last bits of `np.exp`. Measured per frame, distinct
    values and span: `grid-2tick` 18 / 0.85, `grid-10tick` 13 / 0.65,
    `grid-40tick` 7 / 0.50, `grid-200tick` **3 / 0.20**, `range-bound`
    18 / 0.85, `round-1000` 16 / 0.75, `heavy-tailed` 19 / 0.95.

    ⚠ `grid-200tick` gets its own floor, and the reason is margin: its
    third value (0.20) is carried by 4 bars of 1,481 -- the raw count
    `section_C` prints beside the histogram share, not a share read
    backwards -- so a floor of 3 there would sit exactly on the
    measurement, on a
    frame built with `np.exp` / `np.cumsum` / `np.round`. Two distinct
    values and one lattice step is all that "not a constant" needs."""
    col = ts_reoccur_20(FRAMES[name]()).dropna()
    if name == "grid-200tick":
        least, span = 2, 0.10
    else:
        least, span = 6, 0.35
    assert col.nunique() >= least, col.nunique()
    assert float(col.max()) - float(col.min()) >= span
    assert 0.0 <= float(col.min()) and float(col.max()) <= 1.0


@pytest.mark.parametrize("price", [1.0, 100.0, 1e6])
def test_a_continuous_float_frame_is_identically_zero(price):
    """The disclosure, pinned. Nothing repeats in a continuous float walk,
    so the column is a constant 0.0 -- a reading, not a failure, and the
    reason the feature only exists on a tick grid. Measured: 0 duplicated
    closes in the raw walk itself."""
    close = _continuous(price=price)
    col = ts_reoccur_20(close)
    assert int(close.duplicated().sum()) == 0
    assert int(col.notna().sum()) == FIRED
    assert col.dropna().nunique() == 1
    assert float(col.max()) == 0.0
    on_grid = ts_reoccur_20(_grid(close / price))
    assert float(on_grid.mean()) > 0.3


def test_the_level_is_set_by_the_move_in_TICKS():
    """The column's real argument is `price * sigma / tick`. Pinned as a
    strictly DECREASING table plus end bands -- measured mean 0.9124 at
    one tick a bar down to 0.0379 at a hundred, over 20,000 bars a
    step."""
    means = []
    for ticks in (1, 2, 3, 5, 10, 20, 50, 100):
        sigma = ticks * 0.01 / 100.0            # price 100, tick 0.01
        col = ts_reoccur_20(_grid(_walk(20000, 31, sigma, 100.0))).dropna()
        means.append(float(col.mean()))
    assert all(a > b for a, b in zip(means, means[1:])), means
    assert means[0] > 0.85 and means[-1] < 0.10


def test_the_tick_grid_is_not_part_of_the_column():
    """⚠ The cross-sectional limit. The same return path quantised at
    price 5 and at price 500 on a 0.01 grid is two different columns
    (mean 0.2254 and 0.0037), because the tick is a different fraction of
    the price. Rescaling a FRAME rescales its grid with it, which is why
    Gate D passes; comparing two instruments does not."""
    path = _walk(seed=11)
    low = ts_reoccur_20(_grid(path * 0.05))
    high = ts_reoccur_20(_grid(path * 5.0))
    assert float(low.mean()) > 10.0 * float(high.mean())
    assert low.dropna().nunique() > high.dropna().nunique()


@pytest.mark.parametrize("name", NAMES)
def test_gate_d_scale_x8_and_x64_are_bit_identical(name):
    """A x2^k rescale is EXACT, so it can neither merge nor split a tie:
    `8a == 8b` exactly when `a == b`. 1,481 of 1,481 fired bars on every
    frame at both factors."""
    close = FRAMES[name]()
    base = ts_reoccur_20(close)
    for k in (8.0, 64.0):
        masks, shared, same, d = _agree(base, ts_reoccur_20(close * k))
        assert masks and shared == FIRED
        assert same == shared, f"x{k}: {shared - same} differ, max {d}"


@pytest.mark.parametrize("length", [MIN_LENGTH, 3, 5, 21, 60, 250])
def test_gate_d_scale_x8_at_other_lengths(length):
    close = _level(1.0)
    masks, shared, same, _ = _agree(
        ts_reoccur_20(close, length=length),
        ts_reoccur_20(close * 8.0, length=length))
    assert masks and shared == N - length + 1 and same == shared


@pytest.mark.parametrize("price", [1e-6, 1e6, 1e100])
def test_gate_d_scale_x8_at_extreme_price_levels(price):
    close = Series(_level(1.0).to_numpy() * price)
    masks, shared, same, _ = _agree(ts_reoccur_20(close),
                                    ts_reoccur_20(close * 8.0))
    assert masks and shared == FIRED and same == shared


@pytest.mark.parametrize("k", [10.0, 3.7, 0.1, 1.0000001])
@pytest.mark.parametrize("name", NAMES)
def test_gate_d_scale_by_a_non_power_of_two_merges_nothing_here(name, k):
    """These factors are NOT exact, so they can merge two closes that
    differ in their last bits -- never split a tie, since equal doubles
    scale to the same double. Measured: bit-identical on 1,481 of 1,481
    bars, AND 0 merges, on every frame and at all four factors. That is
    a measurement, not a theorem:
    `test_gate_d_a_forced_merge_shows_what_the_measurement_rules_out`
    builds the frame where it does happen.

    ⚠ The two assertions are not the same one. A merge inside a window
    where both closes already had a twin leaves the duplicate count --
    and the column -- untouched, which is why the distinct-close count
    is checked on its own rather than inferred from bit-equality."""
    close = FRAMES[name]()
    masks, shared, same, d = _agree(ts_reoccur_20(close),
                                    ts_reoccur_20(close * k))
    assert masks and shared == FIRED
    assert same == shared, f"x{k}: {shared - same} differ, max |d| {d}"
    lost = (np.unique(close.to_numpy()).size
            - np.unique((close * k).to_numpy()).size)
    assert lost == 0, f"x{k}: the rescale merged {lost} distinct closes"


def test_gate_d_a_forced_merge_shows_what_the_measurement_rules_out():
    """20 CONSECUTIVE doubles -- neighbours one ulp apart -- is the frame a
    non-exact rescale can collapse. From 1.9, x10 leaves 13 of 20 distinct
    and the column goes from 0.00 to 0.70; from 1.0 nothing merges at any
    factor. That is the ulp argument measured: a x10 product's ulp is 8 or
    16 times the input's, so a collision needs the larger binade."""
    def run(p):
        vals = [p]
        for _ in range(LENGTH - 1):
            vals.append(float(np.nextafter(vals[-1], np.inf)))
        return Series(vals)

    hot = run(1.9)
    assert float(ts_reoccur_20(hot).iloc[-1]) == 0.0
    assert np.unique((hot * 10.0).to_numpy()).size < LENGTH
    assert float(ts_reoccur_20(hot * 10.0).iloc[-1]) > 0.5
    for k in (8.0, 64.0):               # exact, so still 20 distinct
        assert float(ts_reoccur_20(hot * k).iloc[-1]) == 0.0

    cold = run(1.0)
    for k in (1.0, 8.0, 64.0, 10.0, 3.7, 0.1):
        assert np.unique((cold * k).to_numpy()).size == LENGTH
        assert float(ts_reoccur_20(cold * k).iloc[-1]) == 0.0


@pytest.mark.parametrize("power", [2.0, 0.5])
@pytest.mark.parametrize("name", VARYING)
def test_gate_d_scale_a_power_of_the_price_keeps_every_tie(name, power):
    """`price ** 2` and `price ** 0.5` are not rescales, but they are
    MONOTONE, so in exact arithmetic they preserve every tie and every
    distinction. They round, so a merge is possible -- and measured
    bit-identical on 1,481 of 1,481 bars anyway."""
    close = FRAMES[name]()
    masks, shared, same, d = _agree(ts_reoccur_20(close),
                                    ts_reoccur_20(close ** power))
    assert masks and shared == FIRED
    assert same == shared, f"** {power}: {shared - same} differ, max {d}"


# ===================================================== guards and locality


@pytest.mark.parametrize("value", [np.nan, np.inf, -np.inf, 0.0, -100.0,
                                   5e-324])
@pytest.mark.parametrize("pos,emptied", [(0, 1), (1, 2), (18, 19),
                                         (200, LENGTH), (398, 2), (399, 1)])
def test_a_bad_close_empties_its_windows_and_nothing_earlier(value, pos,
                                                             emptied):
    """A bad close sits in `length` windows and spoils exactly those --
    fewer near either end. 36 (value, position) pairs, 0 earlier bars
    moved in any of them. The counts are window geometry, not floats, so
    they are exact."""
    base = _level(1.0, n=400)
    clean = ts_reoccur_20(base)
    c = base.copy()
    c.iloc[pos] = value
    col = ts_reoccur_20(c)
    assert int(clean.notna().sum()) - int(col.notna().sum()) == emptied
    if pos:
        a, b = clean.iloc[:pos], col.iloc[:pos]
        m = a.notna() & b.notna()
        assert bool((a.isna() == b.isna()).all())
        assert int((a[m] != b[m]).sum()) == 0


def test_a_frame_of_nothing_but_bad_closes_is_empty_and_quiet():
    """No float error anywhere: the module's only arithmetic is an integer
    division. `np.errstate(all="raise")` would turn one into an
    exception."""
    with np.errstate(all="raise"):
        assert int(ts_reoccur_20(Series(np.full(400, np.nan)))
                   .notna().sum()) == 0
        assert int(ts_reoccur_20(Series(np.zeros(400)))
                   .notna().sum()) == 0
        assert int(ts_reoccur_20(Series(np.full(400, -1.0)))
                   .notna().sum()) == 0


@pytest.mark.parametrize("budget", [1, 20, 999, 10 ** 9])
def test_the_chunk_budget_cannot_change_a_value(budget):
    """`CHUNK_VALUES` bounds the sorted copy; it is not a parameter of the
    statistic. Every chunk is an independent run of rows, so 1 row at a
    time and 50,000,000 at a time give the same column, bit for bit."""
    close = _level(1.0, n=600)
    want = ts_reoccur_20(close)
    try:
        MODULE.CHUNK_VALUES = budget
        got = ts_reoccur_20(close)
    finally:
        MODULE.CHUNK_VALUES = CHUNK_VALUES
    assert got.equals(want)
    assert ts_reoccur_20(close).equals(want)        # restored


def test_one_close_can_move_only_the_next_length_bars():
    """Bar T's close sits in the windows ending at T .. T+19 and nowhere
    else, so that is the whole reach. How MANY of those 20 actually move
    is not fixed -- 4 to 20, measured -- because the duplicate count need
    not change; the SPAN is."""
    close = _level(1.0, n=600)
    base = ts_reoccur_20(close)
    seen = []
    for j in (100, 300, 500):
        for bump in (0.01, 0.50):
            c = close.copy()
            c.iloc[j] = c.iloc[j] + bump
            got = ts_reoccur_20(c)
            m = (base.notna() & got.notna()).to_numpy()
            changed = (base.isna() != got.isna()).to_numpy()
            changed[m] |= (base[base.notna() & got.notna()]
                           != got[base.notna() & got.notna()]).to_numpy()
            moved = np.flatnonzero(changed)
            assert moved.size >= 1
            assert int(moved.min()) >= j
            assert int(moved.max()) <= j + LENGTH - 1
            seen.append(moved.size)
    assert max(seen) <= LENGTH


def test_how_long_it_remembers():
    """Windows one bar apart share 19 of 20 closes, so the column
    autocorrelates hard at lag 1 -- 0.8974 .. 0.9549 over the seven grid
    frames -- and then lets go: |lag 20| at most 0.2992, and the frame
    where it stays highest is the heavy-tailed one, where the quiet
    stretches themselves persist."""
    lag1, lag20 = [], []
    for name in VARYING:
        col = ts_reoccur_20(FRAMES[name]())
        lag1.append(_spearman(col, col.shift(1)))
        lag20.append(abs(_spearman(col, col.shift(LENGTH))))
    assert min(lag1) > 0.80, lag1
    assert max(lag20) < 0.45, lag20


def test_it_is_negative_volatility_measured_in_ticks():
    """What it overlaps, and the number that matters most for Gate E. On
    seven frames of ONE tick regime the per-frame |rho| against
    `stdev(close, 20)` has median 0.7974 (0.6963 .. 0.8533) -- against the
    screen's 0.7222 for the PROTOTYPE on 89 real BIST frames, where
    `stdev` was the top of 687 comparators. Bands, because the figure is
    synthetic and the frames are generated."""
    per = []
    for seed in (11, 97, 5, 23, 44, 56, 8):
        close = _level(1.0, seed=seed)
        per.append(abs(_spearman(ts_reoccur_20(close),
                                 stdev(close, length=LENGTH))))
    assert 0.55 < float(np.median(per)) < 0.95, per
    assert min(per) > 0.50, per


def test_it_is_not_the_share_of_zero_returns_though_it_is_close():
    """`LOT_ZERORET_20` counts ADJACENT repeats (a zero return); this
    column counts a repeat anywhere in the window, so it is the larger
    quantity and they are not the same feature: per-frame |rho| median
    0.5185 (0.3178 .. 0.6507) within one tick regime.

    ⚠ The pooled figure across tick REGIMES is higher, 0.7962 over the
    seven mixed frames, because both columns are high on a fine grid and
    low on a coarse one -- so a pooled synthetic number here reads the
    frame mix. The screen's real 12-frame fork sweep, whose comparator
    set is every `Category` indicator at defaults that is scale-free AND
    non-constant on its first frame (`fork_overlap.py:85-93` — four
    tests, not one, so `LOT_ZERORET_60` is in that pool only if it
    cleared the non-constant one, which the CSV does not record), put
    the prototype's max at 0.4851."""
    per = []
    for seed in (11, 97, 5, 23, 44, 56, 8):
        close = _level(1.0, seed=seed)
        per.append(abs(_spearman(ts_reoccur_20(close),
                                 lot_zeroret_60(close, length=LENGTH))))
    assert 0.30 < float(np.median(per)) < 0.80, per


def test_every_zero_return_in_the_window_is_counted_and_then_some():
    """The exact relation between the two, which is what makes "not the
    same feature" a derivation rather than a correlation.

    `LOT_ZERORET` at length 19 reads the same 20 closes this column does
    (19 returns need 20 closes). A run of `k` zero returns there is `k+1`
    EQUAL closes, all of which have a twin, so with `m` such runs the
    count is at least `sum(k) + m >= sum(k) + 1`. Measured on seven
    frames: the bound holds on every bar, and the column is non-zero on
    bars where there is no zero return at all -- the repeats that are not
    adjacent, which is the whole difference.

    ⚠ At length 20 the two read DIFFERENT windows -- `LOT_ZERORET_20`
    needs 21 closes -- so the bound does NOT hold there: a zero return
    between bars T-20 and T-19 is counted by it and is invisible here.
    That edge is why this test uses 19 and the correlation test uses 20
    (which is the comparator a default sweep would reach for)."""
    strictly_more = 0
    for seed in (11, 97, 5, 23, 44, 56, 8):
        close = _level(1.0, seed=seed)
        a = ts_reoccur_20(close)
        b = lot_zeroret_60(close, length=LENGTH - 1)
        m = a.notna() & b.notna()
        assert int(m.sum()) == FIRED
        zeros = np.round(b[m].to_numpy() * (LENGTH - 1)).astype(int)
        count = np.round(a[m].to_numpy() * LENGTH).astype(int)
        hit = zeros > 0
        assert bool((count[hit] >= zeros[hit] + 1).all())
        assert bool((count[~hit] >= 0).all())
        strictly_more += int((count[~hit] > 0).sum())
    assert strictly_more > 0, "no window repeated a close non-adjacently"


def test_the_gate_e_row_is_owed():
    """Gate E is run by issue-solver after this session, so the ledger has
    NO row for this indicator yet -- which is what
    `tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
    reports as owed, and what the receipt session replaces with the
    measured row (and this test with one pinning its identity).
    `docs/TsReoccur20Measured.md` §E says so too."""
    import csv
    from pathlib import Path
    ledger = Path(__file__).resolve().parents[1] / "docs" / "gate_e_ledger.csv"
    rows = list(csv.DictReader(ledger.open(encoding="utf-8")))
    assert rows, "the ledger should not be empty"
    assert [r for r in rows if r["indicator"] == "ts_reoccur_20"] == []


# ====================================================== wiring and arguments


def test_name_registration_and_accessor():
    close = _level(1.0, n=400)
    out = ts_reoccur_20(close)
    assert out.name == f"TS_REOCCUR_{LENGTH}"
    assert out.category == "statistics"
    assert "ts_reoccur_20" in pandas_ta.Category["statistics"]
    df = pd.DataFrame({"close": close})
    df.index = pd.date_range("2020-01-01", periods=len(close), freq="D")
    got = df.ta.ts_reoccur_20()
    assert got.name == f"TS_REOCCUR_{LENGTH}"
    pd.testing.assert_series_equal(got.reset_index(drop=True),
                                   out.reset_index(drop=True))


@pytest.mark.parametrize("length,named", [(None, LENGTH), (0, LENGTH),
                                          (1, LENGTH), (-5, LENGTH),
                                          (2, 2), (60, 60)])
def test_a_length_below_the_minimum_falls_back_to_the_default(length, named):
    assert ts_reoccur_20(_level(1.0, n=400), length=length).name == \
        f"TS_REOCCUR_{named}"


def test_why_the_minimum_is_two():
    """Shown rather than asserted: at `length` 1 the single datapoint in a
    window has nothing to reoccur with, so the column would be identically
    0.0 -- and the sorted row's adjacent comparison would run over an
    empty axis."""
    assert MIN_LENGTH == 2
    one = sliding_window_view(_level(1.0, n=50).to_numpy(), 1)
    assert one.shape[1] == 1
    assert (one[:, 1:] == one[:, :-1]).shape == (one.shape[0], 0)
    two = ts_reoccur_20(_flat(50), length=2).dropna()
    assert (two == 1.0).all() and two.size == 49


def test_too_short_an_input_returns_none():
    """`length` CLOSES, so `length` of them are the fewest that give one
    value."""
    assert ts_reoccur_20(_level(1.0, n=LENGTH - 1)) is None
    assert int(ts_reoccur_20(_level(1.0, n=LENGTH)).notna().sum()) == 1


def test_offset_and_fillna():
    close = _level(1.0, n=400)
    base = ts_reoccur_20(close)
    pd.testing.assert_series_equal(ts_reoccur_20(close, offset=2),
                                   base.shift(2), check_names=False)
    filled = ts_reoccur_20(close, fillna=-1.0)
    assert int((filled == -1.0).sum()) == LENGTH - 1
    assert bool(filled.iloc[LENGTH - 1:].eq(base.iloc[LENGTH - 1:]).all())
