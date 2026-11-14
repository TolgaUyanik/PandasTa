# -*- coding: utf-8 -*-
"""TS-ENERGY-LAST-20: `ts_energy_last_20`, the share of a 20-return
window's squared-return energy that sits in its last 5 bars (PandasTa
issue #102).

    r            = close / close.shift(1) - 1
    x            = the window's `length` simple returns
    TS_ENERGY    = sum(x[-length // 4:] ** 2) / sum(x ** 2)

WHAT THIS FILE PINS, in order of how much it would hurt to lose.

1. **Gate A, and it is BIT-equality.** tsfresh is not installed in this
   worktree and web access is unavailable, so the source is an
   attribution and not an oracle
   (`test_the_source_library_is_not_installed_here` records that, so the
   claim cannot rot into "checked against tsfresh"). What IS checkable is
   the published expression, retyped with `np.array_split` picking the
   chunk and `np.sum` doing both sums, window by window, sharing no code
   with the module: **1,480 of 1,480** bars on each of ten 1,500-bar
   frames, bit-equal, with identical NaN masks, and at `length` 4, 5, 7,
   21, 40 and 250.
   ⚠ That bit-equality is the REASON for the module's spelling.
   `sliding_window_view` gives each row a stride of one double, so a row
   is a contiguous run of `length` doubles and `ew.sum(axis=1)` is the
   same pairwise reduction `np.sum` runs on the source's own `(length,)`
   array. The left-to-right accumulation a reader reaches for first is
   3 to 4 ulps away from it and FARTHER from the correctly rounded
   answer: mean 0.77 .. 1.42 ulps against an exact rational oracle where
   this spelling is 0.66 .. 0.87, on 10 of 10 frames.

2. **That the tail is `np.array_split`'s own last chunk, at every
   length.** `length // 4` is not a simplification of the source: numpy
   hands the longer chunks out FIRST, so the last chunk is always the
   trailing `length // 4` values. Checked against `np.array_split`
   itself for every length from 4 to 240 -- both its SIZE and its
   INDICES -- rather than argued.

3. **Three closed forms and a bound.** A window whose oldest
   `length - tail` returns are exactly zero reads exactly **1.0**; one
   whose newest `tail` returns are exactly zero reads exactly **0.0**;
   and a window whose returns all have the same MAGNITUDE reads exactly
   `tail / length` -- 0.25 at the default, at `length` 4, 8, 20 and 60.
   ⚠ The bound [0, 1] is not a float theorem: `num` and `den` are reduced
   over DIFFERENT subsets, so `num <= den` holds in exact arithmetic and
   could in principle be lost to rounding. Measured: 0 of 14,800 bars
   outside it over the ten frames, 0 at `length` 4, 5, 7, 21, 40 and 250,
   and 0 of the 2,000 windows `docs/measure_ts_energy_last_20.py` §A4
   builds to straddle 1.0, whose largest reads exactly 1.0. (This file
   re-runs 200 of those 2,000, which is what a test module should cost;
   the 2,000 is the script's.)

4. **Gate B, by mutant, and the one the blind sweep cannot catch.** Five
   mutants are live and caught **36 of 36** offsets on each of four
   frames, where the real module leaks **0 of 36** and 0 at `length` 4,
   7, 60 and 250.
   ⚠ The sixth is the one worth reading. Shifting the per-return bound's
   own index by one bar makes bar T's return kept or dropped by whether
   bar T+1's return is in bound -- a real look-ahead -- and the blind
   sweep catches it **0 of 36** times, because on a frame where every
   return is in bound the only bar it changes is the LAST one, which is
   never before an offset. What it can move is DERIVED: an out-of-bound
   return at J spoils the return at J, so the shifted bound drops the
   return at J-1, and the window ending at **J-1** is the only one before
   J that holds it without also holding J. A frame with an out-of-bound
   return at each offset catches it **12 of 12** and moves exactly bar
   J-1.

5. **Gate D, which is bit-identity BY CONSTRUCTION.** Every input is a
   price ratio and `8a / 8b` is the same double as `a / b`, so a x2^k
   rescale cannot move either sum: 1,480 of 1,480 bars on each of ten
   frames at x8 and x64, at `length` 4 / 5 / 7 / 21 / 60 / 250, and at
   price levels 1e-6, 1e+6 and 1e+100.
   ⚠ x10 / x3.7 / x0.1 / x1.0000001 are NOT bit-identical and are held to
   masks plus a relative tolerance (measured max 4.6e-13, on the
   clustered frame whose smallest value is 1.1e-4). On the TWO-POINT
   frame their Spearman is 0.54 .. 0.61, which is rounding and not a
   scale failure -- the column there is 111 doubles spanning 1.2e-14
   around the exact 0.25 -- so that frame is asserted on the relative
   difference only.
   ⚠ `price ** 2` and `price ** 0.5` are NOT rescales and the column is
   NOT invariant to them, though it nearly is in RANK (Spearman 0.999583
   / 0.999885): a power map scales every LOG return by the power, so a
   ratio of squared log returns would be exactly invariant and this
   column reads simple returns.

6. **The guards, each with what it costs.** A close that is NaN,
   infinite, zero, negative or subnormal empties the `length + 1` = 21
   windows it sits in and NOTHING earlier (36 (value, position) pairs, 0
   earlier bars moved in all 36). The per-return bound is on the return
   and is taken BEFORE the square, which is why the square cannot
   overflow: a frame of nothing but out-of-bound returns raises **0**
   numpy warnings and fires 0 of 400. ⚠ There is NO dispersion floor,
   unlike `ts_binent_20` / `ts_aggac_60`, and that is a decision: a
   1%-a-bar ladder, whose constant return float64 renders only to
   rounding, reads 0.25 on all 280 of its windows at 3 ulps of the exact
   answer, and EITHER of the siblings' two 4096-ulp floors — the return
   RANGE (`ts_binent_20.py:75`) or the return SD (`ts_aggac_60.py:27`),
   both computed here — would empty all 280 of those honest windows and 0
   dishonest ones.
   ⚠ A window whose squares all UNDERFLOW to zero is empty, which is the
   source's own `full_series_energy == 0` rule reached by a second route:
   60 returns of 1e-200 fire 0 of 60, because 1e-200 squared is 0.0.

7. **What the column IS, and what it overlaps.** It is a RECENCY of
   volatility and not a level: 0.0338 .. 0.3947 against `NATR_20`,
   -0.3312 .. +0.1512 against `UI_20`, -0.2231 .. +0.0275 against the
   window's own return standard deviation and -0.0413 .. +0.0341 against
   the close itself, on ten frames.
   ⚠ It overlaps the shipped `TFCENTROID_20` -- the energy-weighted MEAN
   position of the SAME 20 returns, where this is the share in the last
   quarter -- at pooled **0.7493** over the ten frames, per-frame |rho|
   median 0.7261, max **0.9066**, 1 of 10 at or above 0.90. The one frame
   at 0.9066 is `clustered`, built HERE to make energy pile up at one end
   of a window, which is the adversarial case for the pair. Those are
   SYNTHETIC figures; Gate E's 687 comparators hold no pandas_ta port, so
   it cannot see this pair at all. It also reads 0.6093 pooled against
   `TS_IMQ_20` (max 0.8812, same frame).
   ⚠ And a 5/20 mean-|return| RATIO built from the same closes -- a local
   stand-in for the engine's `ATR_Ratio_5_20` family -- reads 0.9558 ..
   0.9986. That stand-in is not the engine's column: the screen measured
   the real `ATR_Ratio_5_20` at 0.5460 on real data, where its own
   stand-in would have said 0.96, which is why Gate E and not this file
   is what decides the band.

8. **That it is the screen prototype in RANK but NOT bit-for-bit.** The
   prototype is two `rolling().sum()` calls, which carry one running
   accumulator across windows: Spearman 1.000000 on 9 of 10 frames
   (0.998284 on the two-point one, where the column is a constant) with
   identical masks, but up to **9,170 ulps** apart on the clustered
   frame. On those 9 frames the prototype is 40 to 9,170 ulps from the
   exact oracle and the module at most 5, so the difference is the
   prototype's. ⚠ On the TWO-POINT frame it is the other way round -- 3
   ulps against the module's 4 -- because every window there holds the
   same 20 squares, so a running accumulator has nothing to drift
   against. That exception is pinned, not rounded off.
   ⚠ The same non-locality is a correctness failure rather than a
   rounding one: with a return 1e+08 times the frame's scale planted at
   bar 200 of a 2,000-bar frame, the module is bit-identical to the
   unspiked frame on all 1,778 bars the spike has left and the prototype
   on 0 of them.

Numbers come from `docs/measure_ts_energy_last_20.py`; the receipt is
`docs/TsEnergyLast20Measured.md`.
Counts that depend on the last bits of a generated frame carry a band or
a tolerance; the structural facts are pinned exactly.
"""
import importlib
import importlib.util
import types
import warnings
from fractions import Fraction

import numpy as np
import pandas as pd
import pytest
from pandas import Series

from .context import pandas_ta
from pandas_ta.statistics.stdev import stdev
from pandas_ta.statistics.tf_centroid_20 import tf_centroid_20
from pandas_ta.statistics.ts_energy_last_20 import (MIN_LENGTH, SEGMENTS,
                                                    SEGMENT_FOCUS, _tail,
                                                    ts_energy_last_20)
from pandas_ta.statistics.ts_imq_20 import ts_imq_20
from pandas_ta.volatility.natr import natr
from pandas_ta.volatility.ui import ui

LENGTH = 20
TAIL = _tail(LENGTH)            # 5
N = 1500
FIRED = N - LENGTH              # `length` RETURNS need `length + 1` closes


# ----------------------------------------------------------------- frames


def _walk(n=N, seed=11, sigma=0.015, drift=0.0):
    rng = np.random.default_rng(seed)
    return Series(100.0 * np.exp(np.cumsum(rng.normal(drift, sigma, n))))


def _tick_rounded(n=N, seed=11):
    return Series(np.round(_walk(n, seed).to_numpy(), 2))


def _from_returns(r):
    return Series(100.0 * np.cumprod(1.0 + np.asarray(r, dtype=float)))


def _ar1(n=N, seed=7, sigma=0.015, phi=0.5):
    rng = np.random.default_rng(seed)
    e = rng.normal(0.0, sigma, n)
    x = np.zeros(n)
    for t in range(1, n):
        x[t] = phi * x[t - 1] + e[t]
    return _from_returns(np.clip(x, -0.5, 0.5))


def _heavy_tailed(n=N, seed=3, df=2.0, sigma=0.01):
    rng = np.random.default_rng(seed)
    return _from_returns(np.clip(sigma * rng.standard_t(df, n), -0.5, 0.5))


def _right_skewed(n=N, seed=5, sigma=0.01):
    rng = np.random.default_rng(seed)
    return _from_returns(np.clip(sigma * (rng.standard_exponential(n) - 1.0),
                                 -0.5, 0.5))


def _left_skewed(n=N, seed=5, sigma=0.01):
    rng = np.random.default_rng(seed)
    return _from_returns(np.clip(sigma * (1.0 - rng.standard_exponential(n)),
                                 -0.5, 0.5))


def _two_point(n=N, seed=4, sigma=0.01):
    rng = np.random.default_rng(seed)
    return _from_returns(np.where(rng.random(n) < 0.5, sigma, -sigma))


def _trending(n=N, seed=9):
    return _walk(n, seed, sigma=0.01, drift=0.004)


def _clustered(n=N, seed=21, quiet=0.002, loud=0.03, run=25):
    """GARCH-like, by hand: alternating runs of quiet and loud bars, so the
    energy really does pile up at one end of a window."""
    rng = np.random.default_rng(seed)
    sig = np.where((np.arange(n) // run) % 2 == 0, quiet, loud)
    return _from_returns(np.clip(sig * rng.standard_normal(n), -0.5, 0.5))


def _flat(n=300, price=100.0):
    return Series(np.full(n, price))


def _ladder(n=300, price=100.0, rate=0.01):
    return Series(price * (1.0 + rate) ** np.arange(n, dtype=float))


def _quiet(n=600, price=100.0, step=1e-6, seed=13):
    rng = np.random.default_rng(seed)
    return _from_returns(step * rng.standard_normal(n)) * (price / 100.0)


FRAMES = {
    "walk": _walk,
    "tick-rounded": _tick_rounded,
    "ar1+": lambda: _ar1(phi=0.5),
    "ar1-": lambda: _ar1(phi=-0.5),
    "heavy-tailed": _heavy_tailed,
    "right-skewed": _right_skewed,
    "left-skewed": _left_skewed,
    "two-point": _two_point,
    "trending": _trending,
    "clustered": _clustered,
}
NAMES = list(FRAMES)
#: Every frame but the two-point one, whose column is a constant 0.25 up to
#: rounding, so a rank correlation on it reads the rounding.
VARYING = [n for n in NAMES if n != "two-point"]


# ---------------------------------------------------------------- helpers


def _ret(close):
    return close / close.shift(1) - 1.0


def _ohlc(close, band=0.004):
    return close * (1.0 + band), close * (1.0 - band)


def _spearman(a, b):
    m = a.notna() & b.notna()
    return float(a[m].corr(b[m], method="spearman"))


def _agree(a, b):
    """(masks equal, shared count, bit-equal count, max |difference|)."""
    masks = bool((a.isna() == b.isna()).all())
    m = a.notna() & b.notna()
    d = float((a[m] - b[m]).abs().max()) if int(m.sum()) else float("nan")
    return masks, int(m.sum()), int((a[m] == b[m]).sum()), d


def _ulps(a, b):
    m = a.notna() & b.notna()
    x, y = a[m].to_numpy(), b[m].to_numpy()
    ulp = np.abs(np.nextafter(y, np.inf) - y)
    return np.abs(x - y) / ulp


# ---------------------------------------------------------------- oracles


def _source_windowed(close, length=LENGTH):
    """tsfresh's `energy_ratio_by_chunks(num_segments=4, segment_focus=3)`
    as published, over the trailing `length` returns, one window at a time.
    Shares no code with the module."""
    r = _ret(close).to_numpy()
    out = np.full(r.size, np.nan)
    for t in range(length, r.size):
        w = r[t - length + 1:t + 1]
        if not np.isfinite(w).all():
            continue
        full = np.sum(w ** 2)
        if full == 0:
            continue
        chunk = np.array_split(w, SEGMENTS)[SEGMENT_FOCUS]
        out[t] = np.sum(chunk ** 2.0) / full
    return Series(out, index=close.index)


def _sequential_view(close, length=LENGTH):
    """The same windows, accumulated LEFT TO RIGHT -- the spelling the
    module does not use."""
    from numpy.lib.stride_tricks import sliding_window_view
    r = _ret(close).to_numpy()
    ew = sliding_window_view(r * r, length)
    tail = _tail(length)
    den = np.zeros(ew.shape[0])
    for j in range(length):
        den += ew[:, j]
    num = np.zeros(ew.shape[0])
    for j in range(length - tail, length):
        num += ew[:, j]
    with np.errstate(invalid="ignore"):
        val = np.where(den > 0.0, num / den, np.nan)
    out = np.full(r.size, np.nan)
    out[length - 1:] = val
    return Series(out, index=close.index)


def _exact(close, length=LENGTH):
    """The correctly rounded answer: every return is a double, so a
    rational; the squares and both sums are exact and the ratio is rounded
    exactly once."""
    r = _ret(close).to_numpy()
    tail = _tail(length)
    out = np.full(r.size, np.nan)
    for t in range(length, r.size):
        w = r[t - length + 1:t + 1]
        if not np.isfinite(w).all():
            continue
        sq = [Fraction(float(v)) ** 2 for v in w]
        den = sum(sq)
        if den == 0:
            continue
        out[t] = float(sum(sq[length - tail:]) / den)
    return Series(out, index=close.index)


def _prototype(close, length=LENGTH):
    """`docs/issues/screen/ind_screen.py`, candidate `ts_energy_last_20`:
    `sdiv(tsum(ret(c) ** 2, 5), tsum(ret(c) ** 2, 20))`."""
    r2 = _ret(close) ** 2
    out = r2.rolling(_tail(length)).sum() / r2.rolling(length).sum()
    return out.replace([np.inf, -np.inf], np.nan)


# ======================================================== Gate A, the source


def test_the_source_library_is_not_installed_here():
    """What Gate A checks is the PUBLISHED expression, retyped, not a run
    of tsfresh. Pinned so the claim cannot rot into "checked against
    tsfresh" if the dependency ever appears."""
    assert importlib.util.find_spec("tsfresh") is None


@pytest.mark.parametrize("name", NAMES)
def test_gate_a_is_bit_equal_to_the_sources_own_spelling(name):
    """`np.array_split` picks the chunk and `np.sum` does both sums, window
    by window. 1,480 of 1,480 bars, masks included, on every frame.

    This is bit-equality and not a tolerance because
    `sliding_window_view`'s rows are contiguous runs of `length` doubles,
    so `ew.sum(axis=1)` is the same pairwise reduction `np.sum` runs on the
    source's `(length,)` array."""
    close = FRAMES[name]()
    masks, shared, same, d = _agree(ts_energy_last_20(close),
                                    _source_windowed(close))
    assert masks
    assert shared == FIRED
    assert same == shared, f"{shared - same} bars differ, max |diff| {d}"


@pytest.mark.parametrize("length", [MIN_LENGTH, 5, 7, 21, 40, 250])
def test_gate_a_is_bit_equal_to_the_source_at_other_lengths(length):
    close = _walk()
    masks, shared, same, d = _agree(
        ts_energy_last_20(close, length=length),
        _source_windowed(close, length=length))
    assert masks
    assert shared == N - length
    assert same == shared, f"{shared - same} bars differ, max |diff| {d}"


def test_the_tail_is_numpys_own_last_chunk():
    """`length // SEGMENTS` is not a simplification of `np.array_split`: it
    is what that function returns, because the LONGER chunks go first. Both
    the size and the indices, for every length from `MIN_LENGTH` to 240."""
    for length in range(MIN_LENGTH, 241):
        chunk = np.array_split(np.arange(length), SEGMENTS)[SEGMENT_FOCUS]
        assert len(chunk) == _tail(length), length
        assert list(chunk) == list(range(length - _tail(length), length)), \
            length


@pytest.mark.parametrize("length", [MIN_LENGTH, 8, LENGTH, 60])
def test_a_window_whose_old_returns_are_zero_reads_exactly_one(length):
    """Closed form, and the ceiling: if the oldest `length - tail` returns
    are exactly zero, the window's whole energy is its tail's."""
    tail = _tail(length)
    c = np.concatenate([np.full(length - tail + 1, 100.0),
                        100.0 * np.cumprod(np.full(tail, 1.01))])
    assert ts_energy_last_20(Series(c), length=length).iloc[-1] == 1.0


@pytest.mark.parametrize("length", [MIN_LENGTH, 8, LENGTH, 60])
def test_a_window_whose_new_returns_are_zero_reads_exactly_zero(length):
    """The other closed form, and the floor."""
    tail = _tail(length)
    rise = 100.0 * np.cumprod(np.full(length - tail + 1, 1.01))
    c = np.concatenate([rise, np.full(tail, rise[-1])])
    assert ts_energy_last_20(Series(c), length=length).iloc[-1] == 0.0


@pytest.mark.parametrize("length", [MIN_LENGTH, 8, LENGTH, 60])
def test_a_two_point_window_reads_exactly_tail_over_length(length):
    """The third closed form, and the one that says what the column
    measures: when every return has the same MAGNITUDE the energy is spread
    evenly, so the share is exactly the tail's share of the bars."""
    rng = np.random.default_rng(7)
    s = np.where(rng.random(length) < 0.5, 1.0, -1.0)
    c = _from_returns(np.concatenate([[0.0], s * 0.5]))
    got = ts_energy_last_20(Series(c), length=length).iloc[-1]
    assert got == _tail(length) / length


@pytest.mark.parametrize("name", NAMES)
def test_the_output_never_leaves_the_unit_interval(name):
    """`num <= den` is exact arithmetic, not a float theorem: the two sums
    are reduced over different subsets and rounded independently."""
    v = ts_energy_last_20(FRAMES[name]()).dropna().to_numpy()
    assert v.size == FIRED
    assert float(v.min()) >= 0.0 and float(v.max()) <= 1.0


def test_the_unit_interval_holds_at_other_lengths_and_under_a_straddle():
    close = _walk()
    for length in (MIN_LENGTH, 5, 7, 21, 40, 250):
        v = ts_energy_last_20(close, length=length).dropna().to_numpy()
        assert float(v.min()) >= 0.0 and float(v.max()) <= 1.0, length
    rng = np.random.default_rng(3)
    worst = 0.0
    for _ in range(200):
        body = 10.0 ** rng.uniform(-30, -8, LENGTH - TAIL)
        tail = 1.0 + rng.uniform(-0.3, 0.3, TAIL)
        c = _from_returns(np.concatenate([[0.0], body, tail * 0.1]))
        v = float(ts_energy_last_20(Series(c)).iloc[-1])
        assert 0.0 <= v <= 1.0
        worst = max(worst, v)
    assert worst == 1.0, "the straddle should reach the ceiling"


@pytest.mark.parametrize("name", NAMES)
def test_the_exact_rational_oracle_agrees_to_a_few_ulps(name):
    """The correctly rounded answer, in `Fraction`. Measured max 3 to 5
    ulps and mean 0.66 to 0.87; the pins are bands, because the last bit
    of a generated frame moves with the CPU."""
    close = FRAMES[name]()
    u = _ulps(ts_energy_last_20(close), _exact(close))
    assert u.size == FIRED
    assert float(u.max()) <= 8.0
    assert float(u.mean()) <= 1.5


def test_the_module_is_closer_to_the_exact_answer_than_a_left_to_right_sum():
    """Why the module reduces with `sum(axis=1)` rather than accumulating.
    Measured: the pairwise spelling is the more accurate one on 10 of 10
    frames. The pin is `<=` per frame plus a strict majority, so a CPU that
    ties on one frame does not fail it."""
    better = 0
    for name in NAMES:
        close = FRAMES[name]()
        ex = _exact(close)
        mine = float(_ulps(ts_energy_last_20(close), ex).mean())
        theirs = float(_ulps(_sequential_view(close), ex).mean())
        assert mine <= theirs + 1e-12, name
        better += int(mine < theirs)
    assert better >= 8


@pytest.mark.parametrize("name", NAMES)
def test_a_left_to_right_sum_is_a_few_ulps_away_and_rank_identical(name):
    """The spelling not used is not WRONG, it is less accurate: 3 to 4 ulps
    away, and the same ranks everywhere but on the two-point frame, whose
    column is a constant."""
    close = FRAMES[name]()
    col, seq = ts_energy_last_20(close), _sequential_view(close)
    assert float(_ulps(col, seq).max()) <= 8.0
    if name in VARYING:
        assert _spearman(col, seq) > 0.9999


def test_reading_log_returns_would_move_the_values_but_not_the_ranks():
    """The issue says "returns" and the module reads SIMPLE returns, which
    is the prototype's reading. The log reading differs by up to 1.4e-02
    with Spearman 0.999572 -- priced rather than assumed.

    The bit-equal count is 0 here and is asserted as a BAND, not as that
    0: whether a bar's two readings happen to round together is a float
    coincidence and the frame is generated by dispatched kernels."""
    close = _walk()
    lr = np.log(close / close.shift(1))
    e = lr ** 2
    alt = e.rolling(TAIL).sum() / e.rolling(LENGTH).sum()
    col = ts_energy_last_20(close)
    masks, shared, same, d = _agree(col, alt)
    assert masks and shared == FIRED
    assert same <= FIRED // 100
    assert 5e-03 < d < 5e-02
    assert _spearman(col, alt) > 0.999


def test_the_energy_is_the_SQUARE_and_the_absolute_value_is_a_near_miss():
    """The same expression over |r| instead of r**2 reads 0.9638 -- close
    enough to be mistaken for this column and not the same column."""
    close = _walk()
    a = _ret(close).abs()
    alt = a.rolling(TAIL).sum() / a.rolling(LENGTH).sum()
    rho = _spearman(ts_energy_last_20(close), alt)
    assert 0.93 < rho < 0.99


def test_the_other_three_chunks_of_the_split_are_other_columns():
    """`segment_focus` 3 is the issue's, and the other three chunks of the
    same split read -0.36 / -0.36 / -0.24 against it: the shares sum to 1,
    so they are NEGATIVELY related, not restatements."""
    close = _walk()
    col = ts_energy_last_20(close)
    e = _ret(close) ** 2
    den = e.rolling(LENGTH).sum()
    for focus in range(SEGMENTS - 1):
        lo = LENGTH - (SEGMENTS - focus) * TAIL
        num = e.shift(LENGTH - TAIL - lo).rolling(TAIL).sum()
        assert -0.60 < _spearman(col, num / den) < -0.10, focus


def test_other_segment_counts_are_other_columns():
    """2 / 5 / 10 / 20 segments read 0.6061 / 0.8705 / 0.5665 / 0.3643
    against the issue's 4, and their means are the tail's share of the
    bars. `SEGMENTS` is a constant for this reason: it changes the
    column."""
    close = _walk()
    col = ts_energy_last_20(close)
    e = _ret(close) ** 2
    bands = {2: (0.50, 0.70), 5: (0.80, 0.93), 10: (0.45, 0.68),
             20: (0.25, 0.48)}
    for segments, (lo, hi) in bands.items():
        tail = LENGTH // segments
        alt = e.rolling(tail).sum() / e.rolling(LENGTH).sum()
        rho = _spearman(col, alt)
        assert lo < rho < hi, (segments, rho)
        assert abs(float(alt.mean()) - tail / LENGTH) < 0.02


def test_the_sign_of_a_return_cannot_reach_the_output():
    """`e = r * r`, so the column reads magnitudes only. ⚠ This is pinned
    on RANKS and a 2e-14 tolerance rather than bit-equality, and the reason
    is the frame: a sign-flipped frame has to be rebuilt from closes, which
    re-rounds every return. The right- and left-skewed frames, whose
    returns are exact negatives of each other, agree to 1.8e-14."""
    rs, ls = _right_skewed(), _left_skewed()
    a, b = ts_energy_last_20(rs), ts_energy_last_20(ls)
    masks, shared, same, d = _agree(a, b)
    assert masks and shared == FIRED
    assert d < 1e-13
    assert _spearman(a, b) > 0.99999


# ========================================================= Gate B, by mutant


OFFSETS = range(60, N, 40)      # 36 offsets, past the 20-bar warm-up
PAIRS = {
    "walk": (_walk(), _walk(seed=97)),
    "tick-rounded": (_tick_rounded(), _tick_rounded(seed=56)),
    "heavy-tailed": (_heavy_tailed(), _heavy_tailed(seed=8)),
    "clustered": (_clustered(), _clustered(seed=44)),
}
BAD_OFFSETS = range(60, N, 120)         # 12 offsets, >= length + 1 apart

BACK_DATE_TWO = (
    "    energy = Series(out, index=close.index)",
    "    energy = Series(out, index=close.index).shift(-2)")
BACK_DATE_FULL = (
    "    energy = Series(out, index=close.index)",
    "    energy = Series(out, index=close.index).shift(-(length - 1))")
FORWARD_RETURN = (
    "        r = (px / px.shift(1) - 1.0).to_numpy()",
    "        r = (px.shift(-1) / px - 1.0).to_numpy()")
WRITE_INDEX_EARLIER = (
    "    out[length - 1:] = val",
    "    out[length - 2:-1] = val")
ROLLED_WINDOW = (
    "    e = r * r",
    "    e = np.roll(r * r, -(length // 2))")
#: The per-return bound's own index. A real look-ahead, and INVISIBLE to the
#: blind sweep: see `test_the_mutant_the_blind_sweep_cannot_catch`.
FORWARD_BOUND = (
    "    r = np.where(np.abs(r) < bound, r, np.nan)",
    "    r = np.where(np.abs(np.roll(r, -1)) < bound, r, np.nan)")

MUTANTS = {
    "back_date_two": BACK_DATE_TWO,
    "back_date_full": BACK_DATE_FULL,
    "forward_return": FORWARD_RETURN,
    "write_index_earlier": WRITE_INDEX_EARLIER,
    "rolled_window": ROLLED_WINDOW,
}


def _load_mutant(old, new):
    real = importlib.import_module("pandas_ta.statistics.ts_energy_last_20")
    with open(real.__file__, encoding="utf-8") as fh:
        src = fh.read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_ts_energy_last_20_mutant")
    mod.__file__ = real.__file__
    exec(compile(src.replace(old, new), real.__file__, "exec"), mod.__dict__)
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


@pytest.mark.parametrize("name", list(PAIRS))
def test_the_real_module_leaks_nothing_to_the_future(name):
    close, other = PAIRS[name]
    assert _caught(ts_energy_last_20, close, other) == []


@pytest.mark.parametrize("length", [MIN_LENGTH, 7, 60, 250])
def test_the_real_module_leaks_nothing_at_other_lengths(length):
    close, other = PAIRS["walk"]
    assert _caught(ts_energy_last_20, close, other, length=length) == []
    first = int(ts_energy_last_20(close, length=length)
                .notna().to_numpy().argmax())
    assert first == length


@pytest.mark.parametrize("mutant", list(MUTANTS))
@pytest.mark.parametrize("frame", list(PAIRS))
def test_gate_b_mutant_is_live_and_caught(mutant, frame):
    """Each mutant is read out of the real module's source, edited in
    memory and `exec`'d, so it is the shipped code with one write index or
    one read moved. All five are live on every frame and caught at all 36
    offsets."""
    mod = _load_mutant(*MUTANTS[mutant])
    close, other = PAIRS[frame]
    assert not mod.ts_energy_last_20(close).equals(ts_energy_last_20(close))
    assert len(_caught(mod.ts_energy_last_20, close, other)) == \
        len(list(OFFSETS))


def _out_of_bound_frame(seed=23):
    """A walk whose return at every designed offset is above the module's
    own bound, which is what the forward-bound mutant needs in order to
    mis-read anything."""
    c = _walk(N, seed).to_numpy().copy()
    for j in BAD_OFFSETS:
        c[j] = c[j - 1] * 1e200
        c[j + 1] = c[j] / 1e200
    return Series(c)


def test_gate_b_the_mutant_the_blind_sweep_cannot_catch():
    """The sixth mutant, and the reason prefix truncation is not a Gate B.
    Shifting the bound's own index by one bar makes bar T's return kept or
    dropped by whether bar T+1's is in bound. On a frame where every return
    is in bound the only bar that changes is the LAST one -- never before
    an offset -- so the blind sweep catches it 0 of 36 times on each of
    four frames.

    What it CAN move is derived, not searched: an out-of-bound return at J
    spoils the return at J, so the shifted bound drops the return at J-1,
    and the window ending at J-1 is the only one before J that holds that
    return without also holding J's. A frame with an out-of-bound return at
    each offset catches it 12 of 12 and moves exactly bar J-1."""
    mod = _load_mutant(*FORWARD_BOUND)
    for frame, (close, other) in PAIRS.items():
        assert _caught(mod.ts_energy_last_20, close, other) == [], frame

    close, other = _out_of_bound_frame(), _walk(N, 97)
    assert _caught(ts_energy_last_20, close, other, BAD_OFFSETS) == []
    # The mutant keeps an out-of-bound return, so ITS square overflows --
    # the module's own cannot, which is what
    # `test_the_bound_is_on_the_return_so_the_square_cannot_overflow` pins.
    with np.errstate(over="ignore"):
        hits = _caught(mod.ts_energy_last_20, close, other, BAD_OFFSETS)
        assert len(hits) == len(list(BAD_OFFSETS))
        for j in BAD_OFFSETS:
            p = close.copy()
            p.iloc[j:] = other.iloc[j:].values
            a, b = mod.ts_energy_last_20(close), mod.ts_energy_last_20(p)
            a, b = a.iloc[:j], b.iloc[:j]
            # The union of mask flips and value changes, so `moved` is the
            # set the assertion claims: a bar that kept its mask and moved
            # its double counts too.
            m = a.notna() & b.notna()
            changed = (a.isna() != b.isna()).to_numpy()
            changed[m.to_numpy()] |= (a[m] != b[m]).to_numpy()
            moved = np.flatnonzero(changed).tolist()
            assert moved == [j - 1], (j, moved)


# ============================================================ Gate C and D


@pytest.mark.parametrize("name", NAMES)
def test_gate_c_fires_on_every_bar_past_the_warm_up(name):
    col = ts_energy_last_20(FRAMES[name]())
    assert int(col.notna().sum()) == FIRED
    assert int(col.notna().to_numpy().argmax()) == LENGTH
    assert bool(col.iloc[:LENGTH].isna().all())


@pytest.mark.parametrize("name", VARYING)
def test_gate_c_is_not_a_constant_and_spans_a_real_range(name):
    """Bands, not counts: the distinct-value count depends on the last bits
    of a generated frame. Measured 1,480 of 1,480 distinct on each of these
    nine frames."""
    v = ts_energy_last_20(FRAMES[name]()).dropna()
    assert v.unique().size > FIRED // 2
    assert float(v.min()) < 0.05 < 0.60 < float(v.max())
    assert 0.15 < float(v.median()) < 0.26


def test_the_two_point_frame_is_a_constant_up_to_rounding():
    """Where Gate C's and Gate D's readings have to change. Every |return|
    is the same size, so the exact answer is `tail / length` on every
    window; what is left is rounding -- 111 doubles spanning 1.2e-14."""
    v = ts_energy_last_20(_two_point()).dropna().to_numpy()
    assert v.size == FIRED
    assert v.max() - v.min() < 1e-12
    assert float(np.abs(v - TAIL / LENGTH).max()) < 1e-13


@pytest.mark.parametrize("name", NAMES)
def test_gate_d_scale_x8_and_x64_are_bit_identical(name):
    """`8a / 8b` is the same double as `a / b`, so neither sum can move."""
    close = FRAMES[name]()
    base = ts_energy_last_20(close)
    for k in (8.0, 64.0):
        masks, shared, same, d = _agree(base, ts_energy_last_20(close * k))
        assert masks and shared == FIRED
        assert same == shared, (k, d)


@pytest.mark.parametrize("length", [MIN_LENGTH, 5, 7, 21, 60, 250])
def test_gate_d_scale_x8_at_other_lengths(length):
    close = _walk()
    masks, shared, same, _ = _agree(
        ts_energy_last_20(close, length=length),
        ts_energy_last_20(close * 8.0, length=length))
    assert masks and shared == N - length and same == shared


@pytest.mark.parametrize("price", [1e-6, 1e6, 1e100])
def test_gate_d_scale_x8_at_extreme_price_levels(price):
    c = _walk() * (price / 100.0)
    masks, shared, same, _ = _agree(ts_energy_last_20(c),
                                    ts_energy_last_20(c * 8.0))
    assert masks and shared == FIRED and same == shared


@pytest.mark.parametrize("k", [10.0, 3.7, 0.1, 1.0000001])
@pytest.mark.parametrize("name", NAMES)
def test_gate_d_scale_by_a_non_power_of_two_keeps_masks_and_values(name, k):
    """NOT bit-identical by construction, so this is a tolerance: measured
    max relative difference 4.6e-13, on the clustered frame whose smallest
    value is 1.1e-04."""
    close = FRAMES[name]()
    base, other = ts_energy_last_20(close), ts_energy_last_20(close * k)
    masks, shared, same, d = _agree(base, other)
    assert masks and shared == FIRED
    m = base.notna() & other.notna()
    rel = float(((base[m] - other[m]).abs()
                 / base[m].abs().clip(lower=1e-300)).max())
    assert rel < 1e-11, rel
    if name in VARYING:
        assert _spearman(base, other) > 0.9999


def test_gate_d_scale_on_the_two_point_frame_reads_rounding_not_scale():
    """⚠ The two-point frame's Spearman under x10 is 0.54, and that is NOT
    a scale failure: the column there is a constant 0.25 plus 1.2e-14 of
    rounding, so the rank correlation ranks the rounding. The relative
    difference, which is the reading that survives, stays at 3e-14.

    So the relative difference is what is PINNED. The Spearman is checked
    only as "either the two agree bit for bit or the rank correlation is
    reading rounding": a kernel on which the rescale happened to come out
    bit-equal would be an improvement, not a regression, and must not
    turn this test red."""
    close = _two_point()
    base = ts_energy_last_20(close)
    for k in (10.0, 3.7, 0.1, 1.0000001):
        other = ts_energy_last_20(close * k)
        assert float((base - other).abs().max()) < 1e-13
        bit_equal = bool((base.dropna() == other.dropna()).all())
        assert bit_equal or abs(_spearman(base, other)) < 0.95


def test_gate_d_a_power_of_the_price_is_not_a_rescale():
    """`price ** 2` is not a rescale and the column is not invariant to it
    -- 0 bars bit-equal, values up to 0.0139 apart. It nearly is in RANK
    (0.999583 / 0.999885), and the reason is worth knowing: a power map
    scales every LOG return by the power, so a ratio of squared LOG returns
    would be exactly invariant, and simple returns approximate log
    returns.

    The bit-equal count is 0 here and is asserted as a BAND, for the same
    reason as in `test_reading_log_returns_would_move_the_values_but_not_
    the_ranks`: a bar on which the two readings round together is a float
    coincidence, not a property."""
    close = _walk()
    base = ts_energy_last_20(close)
    for power, bound in ((2.0, 0.05), (0.5, 0.05)):
        other = ts_energy_last_20(close ** power)
        masks, shared, same, d = _agree(base, other)
        assert masks and shared == FIRED
        assert same <= FIRED // 100
        assert 1e-03 < d < bound
        assert _spearman(base, other) > 0.999


# ================================================================== guards


@pytest.mark.parametrize("value", [np.nan, np.inf, -np.inf, 0.0, -100.0,
                                   1e-310])
def test_a_bad_close_empties_its_windows_and_nothing_earlier(value):
    """A close that is not a finite, normal, positive float spoils the
    returns at its own bar and the next, so it empties the `length + 1`
    windows that hold either -- and no bar before them moves.

    "Before them" is every bar up to and NOT including `j`. Bar T reads
    closes T - length .. T, so the earliest window that can see close `j`
    is the one ending at bar `j`; the window ending at `j - 1` cannot, and
    it is the single bar an off-by-one in the window-to-bar mapping would
    move first. An earlier draft of this test sliced `:max(j - 1, 0)` and
    so excluded exactly that bar, which bought nothing -- review round 3
    caught it."""
    base_close = _walk(400)
    base = ts_energy_last_20(base_close)
    for j, emptied in ((0, 1), (1, 2), (19, 20), (200, LENGTH + 1),
                       (398, 2), (399, 1)):
        c = base_close.copy()
        c.iloc[j] = value
        col = ts_energy_last_20(c)
        assert int(base.notna().sum()) - int(col.notna().sum()) == emptied, j
        a, b = base.iloc[:j], col.iloc[:j]
        assert bool((a.isna() == b.isna()).all()), j
        m = a.notna()
        assert bool((a[m] == b[m]).all()), j


def test_the_bound_is_on_the_return_so_the_square_cannot_overflow():
    """The ceiling is `sqrt(max / (2 * length))` = 2.120e+153 at the
    default: `length` squares of it sum to half the float maximum, so the
    total is a number and not an infinity. Because the test is taken BEFORE
    the square, a frame of nothing but out-of-bound returns raises no numpy
    warning at all."""
    bound = float(np.sqrt(np.finfo(float).max / (2 * LENGTH)))
    assert 2.11e153 < bound < 2.13e153

    base_close = _walk(400)
    base = ts_energy_last_20(base_close)
    c = base_close.to_numpy().copy()
    c[200] = c[199] * (bound * 2)
    out = ts_energy_last_20(Series(c))
    assert int(base.notna().sum()) - int(out.notna().sum()) == LENGTH

    c = base_close.to_numpy().copy()
    c[200] = c[199] * (bound * 0.5)
    out = ts_energy_last_20(Series(c))
    assert int(out.notna().sum()) == int(base.notna().sum())
    assert float(out.iloc[200]) == 1.0

    c = base_close.to_numpy().copy()
    for j in range(1, 399, 2):
        c[j] = c[j - 1] * 1e200
        c[j + 1] = c[j] / 1e200
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        out = ts_energy_last_20(Series(c))
    assert [str(w.message) for w in caught] == []
    assert int(out.notna().sum()) == 0


def test_a_flat_frame_is_EMPTY_and_not_zero():
    """The source's own rule: a window with no energy has no share of it.
    `den > 0.0` is exactly `full_series_energy != 0`, and 21 identical
    closes are the only way to reach it with honest data."""
    assert int(ts_energy_last_20(_flat()).notna().sum()) == 0
    c = _flat().to_numpy().copy()
    c[:100] = 100.0 * np.cumprod(np.full(100, 1.01))
    col = ts_energy_last_20(Series(c))
    assert 0 < int(col.notna().sum()) < 280


def test_there_is_no_dispersion_floor_and_this_is_what_that_buys():
    """⚠ A decision, not an omission. `ts_binent_20` and `ts_aggac_60`
    refuse a degenerate window at the same 4096 ulps but on DIFFERENT
    statistics of it -- the return RANGE (`ts_binent_20.py:75`) and the
    return SD (`ts_aggac_60.py:27`) -- because both read a SPREAD whose
    own rounding the statistic then amplifies. This one divides a window's
    energy by its own total, so a degenerate window gives the right answer
    rather than a loud one: a 1%-a-bar ladder, whose return is only
    MATHEMATICALLY constant, reads 0.25 on all 280 of its windows at 3
    ulps of the exact answer.

    Both floors are priced below rather than one standing in for the
    other: either would empty all 280 of the ladder's honest windows and 0
    of the quiet frame's 580."""
    floor = 4096 * np.finfo(float).eps

    def _killed(close, col):
        r = _ret(close)
        rng = r.rolling(LENGTH).max() - r.rolling(LENGTH).min()
        sd = r.rolling(LENGTH).std(ddof=0)
        return (int((col.notna() & (rng <= floor)).sum()),
                int((col.notna() & (sd <= floor)).sum()))

    ladder = _ladder()
    col = ts_energy_last_20(ladder)
    assert int(col.notna().sum()) == 280
    v = col.dropna().to_numpy()
    assert float(np.abs(v - TAIL / LENGTH).max()) < 1e-14
    assert float(_ulps(col, _exact(ladder)).max()) <= 8.0
    assert _killed(ladder, col) == (280, 280)

    quiet = _quiet()
    col = ts_energy_last_20(quiet)
    assert int(col.notna().sum()) == 580
    assert col.dropna().unique().size > 500
    assert float(_ulps(col, _exact(quiet)).max()) <= 8.0
    assert _killed(quiet, col) == (0, 0)


def test_a_window_whose_squares_all_underflow_is_empty():
    """The source's `full_series_energy == 0` has a second route to it that
    honest data cannot take: a return below sqrt(tiny) = 1.49e-154 squares
    to zero. 60 returns of 1e-200 leave the window with no energy at all;
    mixing in 20 honest ones puts every scrap of it in the tail."""
    assert (1e-200) ** 2 == 0.0
    assert int(ts_energy_last_20(_from_returns(np.full(60, 1e-200)))
               .notna().sum()) == 0
    c = _from_returns(np.concatenate([np.full(40, 1e-200),
                                      np.full(20, 1e-3)]))
    col = ts_energy_last_20(c)
    assert int(col.notna().sum()) == LENGTH
    assert float(col.dropna().max()) == 1.0


def test_the_window_is_LOCAL_where_a_rolling_sum_is_not():
    """The screen prototype's two `rolling().sum()` calls carry one running
    accumulator across windows, so one enormous return leaves a residue in
    every later window. This spelling reduces each window on its own.

    Measured on a 2,000-bar frame priced at 1e-198 with one return planted
    at bar 200: at x1e+08, x1e+100 and x1e+300 the module is bit-identical
    to the unspiked frame on all 1,778 bars the spike has LEFT, and the
    prototype on 0 of them.

    ⚠ What is PINNED of the prototype is "not all of them", not the 0: its
    recovery is frame-dependent and the frames are built with `np.exp` and
    `np.cumsum`, which are dispatched. `python
    docs/measure_ts_energy_last_20_cpu.py G` runs the same section with
    AVX-512/AVX2/FMA3 off and the prototype's counts MOVE -- 1,690 of
    1,778 at x1e+300 where the default run reads 0, and 1,690 at x1e+02
    and x1e+06 where it reads 41. Every cell is still short of 1,778.
    The module's side is the structural one and is pinned exactly, in both
    runs: it reduces each window on its own, so there is nothing to
    carry."""
    close = _walk(2000, seed=31) * 1e-198
    later = slice(202 + LENGTH, None)
    for mag in (1e8, 1e100, 1e300):
        c = close.to_numpy().copy()
        c[200] = c[199] * mag
        c[201] = c[200] / mag
        spiked = Series(c)
        mine_b, mine_s = ts_energy_last_20(close), ts_energy_last_20(spiked)
        pro_b, pro_s = _prototype(close), _prototype(spiked)
        n = int(mine_b.iloc[later].notna().sum())
        assert n > 1700
        assert int((mine_b.iloc[later] == mine_s.iloc[later]).sum()) == n
        kept = int((pro_b.iloc[later] == pro_s.iloc[later]).sum())
        assert kept < n, (mag, kept, n)


# ========================================================= what it overlaps


def test_it_overlaps_the_shipped_tf_centroid_20_and_this_is_the_disclosure():
    """⚠ `TFCENTROID_20` (TSFEL's temporal centroid, issue #116, merged
    2026-10-30) is the energy-weighted MEAN position of the same 20
    returns, where this column is their share in the last quarter. Pooled
    Spearman over ten frames **0.7493** (n = 14,800), per-frame |rho|
    median 0.7261, max **0.9066**, 1 of 10 at or above 0.90 -- and the one
    frame that reaches it is `clustered`, built here to pile energy up at
    one end of a window, which is the adversarial case for the pair.
    Both of those figures are in the SHIP band under `r3-perframe-0.90`
    -- below the 0.76 line, not in DISCLOSE_GAP's 0.80 .. 0.90 -- and are
    reported anyway because the per-frame MAX reaches 0.9066, which no
    band reads. Not STRUCK either, which the assertions below pin
    directly.
    ⚠ These are SYNTHETIC. Gate E's 687 comparators are the engine's and
    hold no pandas_ta port, so no real-frame figure for this pair exists --
    the same hole `docs/TsImq20Measured.md` §O records for `TS_IMQ_20`,
    which this column reads 0.6093 against."""
    per_tf, per_imq, pool = [], [], []
    for name in NAMES:
        close = FRAMES[name]()
        col, tf, imq = (ts_energy_last_20(close), tf_centroid_20(close),
                        ts_imq_20(close))
        per_tf.append(abs(_spearman(col, tf)))
        per_imq.append(abs(_spearman(col, imq)))
        m = col.notna() & tf.notna()
        pool.append(pd.DataFrame({"a": col[m], "b": tf[m]}))
    both = pd.concat(pool, ignore_index=True)
    pooled = float(both["a"].corr(both["b"], method="spearman"))
    assert 0.70 < pooled < 0.80
    assert 0.65 < float(np.median(per_tf)) < 0.80
    assert max(per_tf) < 0.95
    assert sum(1 for p in per_tf if p >= 0.90) <= 2
    assert float(np.median(per_imq)) < 0.70
    assert max(per_imq) < 0.95


@pytest.mark.parametrize("name", NAMES)
def test_it_is_a_recency_of_volatility_and_not_a_level(name):
    """A share cancels the window's overall size, so the column cannot see
    how volatile the window was -- only where in it the volatility sat.
    Measured bands over ten frames: 0.0338 .. 0.3947 against `NATR_20`,
    -0.3312 .. +0.1512 against `UI_20`, -0.2231 .. +0.0275 against the
    window's own return standard deviation, -0.0413 .. +0.0341 against the
    close."""
    close = FRAMES[name]()
    col = ts_energy_last_20(close)
    high, low = _ohlc(close)
    r = _ret(close)
    assert abs(_spearman(col, natr(high=high, low=low, close=close,
                                   length=LENGTH))) < 0.45
    assert abs(_spearman(col, ui(close=close, length=LENGTH))) < 0.40
    assert abs(_spearman(col, stdev(close=r, length=LENGTH))) < 0.30
    assert abs(_spearman(col, close)) < 0.10


def test_what_it_IS_near_is_a_five_over_twenty_volatility_ratio():
    """⚠ The warning a consumer needs. A 5/20 mean-|return| ratio built
    from the same closes -- a local stand-in for the engine's
    `ATR_Ratio_5_20` family, which the 2026-10-24 screen found third
    against the prototype -- reads 0.9558 .. 0.9986 on these frames.
    That stand-in is NOT the engine's column: the screen measured the real
    `ATR_Ratio_5_20` at 0.5460 and `natr_Chg_5d` at 0.7020 on 89 real
    frames, where the close-based stand-ins here say 0.96 and 0.90. Which
    is the whole reason Gate E, and not this file, decides the band."""
    for name in NAMES:
        close = FRAMES[name]()
        a = _ret(close).abs()
        ratio = a.rolling(TAIL).mean() / a.rolling(LENGTH).mean()
        assert _spearman(ts_energy_last_20(close), ratio) > 0.95, name


def test_the_level_to_expect_on_independent_windows():
    """20,000 INDEPENDENT windows, so the relation is not an artefact of
    overlap. The mean is `tail / length` = 0.25 whatever the law -- a share
    of an evenly-spread total -- and what the tails change is the SPREAD:
    sd 0.1298 gaussian, 0.2309 student-t(2), 0.1773 one-sided exponential.

    ⚠ This pins the STATISTIC, not the shipped function; what transfers it
    is Gate A's bit-equality against the source's own spelling."""
    rng = np.random.default_rng(2026)
    for draw, lo, hi in ((lambda n: rng.standard_normal(n), 0.11, 0.15),
                         (lambda n: rng.standard_t(2.0, n), 0.20, 0.27),
                         (lambda n: rng.standard_exponential(n) - 1.0,
                          0.15, 0.20)):
        W = draw((20000, LENGTH)) ** 2
        v = W[:, LENGTH - TAIL:].sum(axis=1) / W.sum(axis=1)
        assert abs(float(v.mean()) - TAIL / LENGTH) < 0.01
        assert lo < float(v.std()) < hi


def test_one_bar_moves_exactly_length_bars_and_the_sign_turns_at_tail():
    """A -50% bar enters the window at bar 700 and leaves it at bar 720, so
    it moves exactly `length` bars -- and the SIGN of the move says which
    sum it is in: the spike is in the numerator for the first `tail` of
    them (all 5 positive) and only in the denominator afterwards (all 15
    negative).

    x0.5 and not x0.8: a power of two leaves every later ratio the same
    double, so the count is exact instead of a threshold."""
    close = _walk()
    base = ts_energy_last_20(close)
    spiked = close.copy()
    spiked.iloc[700:] = spiked.iloc[700:] * 0.5
    out = ts_energy_last_20(spiked)
    moved = np.flatnonzero((base != out).to_numpy()
                           & base.notna().to_numpy()).tolist()
    assert moved == list(range(700, 700 + LENGTH))
    d = out - base
    assert bool((d.iloc[700:700 + TAIL] > 0).all())
    assert bool((d.iloc[700 + TAIL:700 + LENGTH] < 0).all())


def test_it_is_a_state_for_tail_bars_and_then_forgets():
    """Windows one bar apart share 19 of their 20 returns, so the column
    autocorrelates at 0.7859 at lag 1 on a walk -- and then goes to
    NOTHING: -0.0278 at lag 5 and 0.0006 at lag 20, where the windows no
    longer overlap. On the clustered frame, where volatility itself
    persists, lag 5 is 0.4227 and lag 20 is -0.3804."""
    col = ts_energy_last_20(_walk())
    assert 0.70 < float(col.autocorr(1)) < 0.85
    assert abs(float(col.autocorr(TAIL))) < 0.15
    assert abs(float(col.autocorr(LENGTH))) < 0.10
    col = ts_energy_last_20(_clustered())
    assert float(col.autocorr(1)) > 0.85
    assert float(col.autocorr(TAIL)) > 0.30
    assert float(col.autocorr(LENGTH)) < -0.25


# ============================================= the prototype and the ledger


@pytest.mark.parametrize("name", NAMES)
def test_it_is_the_screen_prototype_in_RANK_but_not_bit_for_bit(name):
    """Issue #102's prototype is `sdiv(tsum(r2, 5), tsum(r2, 20))`, two
    `rolling().sum()` calls. Identical NaN masks and Spearman 1.000000 on
    the nine varying frames, but up to 9,170 ulps apart on the clustered
    one -- and on the nine it is the PROTOTYPE that is out: against the
    exact oracle it is 40 to 9,170 ulps away where the module is at most 5.
    So Gate E's figures for the prototype carry over in rank, which is what
    a Spearman reads.
    ⚠ The TWO-POINT frame is the exception and it is pinned as one: there
    every window holds the same 20 squares, so the running accumulator has
    nothing to drift against and the prototype is the closer of the two (3
    ulps against the module's 4, mean 0.434 against 0.868)."""
    close = FRAMES[name]()
    col, pro = ts_energy_last_20(close), _prototype(close)
    masks, shared, same, d = _agree(col, pro)
    assert masks and shared == FIRED
    assert d < 1e-12
    ex = _exact(close)
    mine, theirs = float(_ulps(col, ex).max()), float(_ulps(pro, ex).max())
    if name in VARYING:
        assert _spearman(col, pro) > 0.99999
        assert mine <= theirs
        assert theirs > 8.0, "the prototype should be the loose one here"
    else:
        assert mine <= 8.0 and theirs <= mine


def test_the_prototype_parts_company_only_on_the_guards():
    """With a close of inf, 0 or 1e-310 at bar 200 of a 400-bar walk the
    prototype reports 360 bars to this module's 359, and with a NEGATIVE
    close there 380 to 359. With a NaN close the two agree, because pandas
    propagates it. Every extra bar is a window built on a close a market
    cannot print."""
    base = _walk(400)
    for value, pro_fires in ((np.inf, 360), (0.0, 360), (1e-310, 360),
                             (-100.0, 380), (np.nan, 359)):
        c = base.copy()
        c.iloc[200] = value
        assert int(ts_energy_last_20(c).notna().sum()) == 359, value
        assert int(_prototype(c).notna().sum()) == pro_fires, value


def test_the_gate_e_row_is_owed():
    """Gate E is run by issue-solver AFTER this session, so there is no
    ledger row yet and `tests/test_gate_e_ledger.py::
    test_every_indicator_that_needs_a_row_has_one` reports this indicator
    as owed. This test is the receipt session's cue: when the row is
    recorded it fails, and is replaced by one pinning the row's identity --
    the module, the column, the run id and the verdict -- the way
    `tests/test_ts_q05_60.py` does for issue #101.

    ⚠ The 2026-10-24 screen measured the PROTOTYPE at max |rho| 0.7020 vs
    `natr_Chg_5d` over n = 397,069 (SHIP), per-frame max median 0.7036. The
    module is rank-identical to that prototype on the nine varying frames
    (Spearman 1.000000), so the figure is expected to carry over -- but the
    launcher's run on THIS module is the number that decides ship or
    revert."""
    import csv
    from pathlib import Path
    ledger = Path(__file__).resolve().parents[1] / "docs" / "gate_e_ledger.csv"
    rows = list(csv.DictReader(ledger.open(encoding="utf-8")))
    assert rows, "the ledger should not be empty"
    assert [r for r in rows if r["indicator"] == "ts_energy_last_20"] == []


# ====================================================== wiring and arguments


def test_name_registration_and_accessor():
    close = _walk(400)
    out = ts_energy_last_20(close)
    assert out.name == f"TS_ENERGY_LAST_{LENGTH}_{SEGMENTS}"
    assert out.category == "statistics"
    assert "ts_energy_last_20" in pandas_ta.Category["statistics"]
    df = pd.DataFrame({"close": close})
    df.index = pd.date_range("2020-01-01", periods=len(close), freq="D")
    got = df.ta.ts_energy_last_20()
    assert got.name == f"TS_ENERGY_LAST_{LENGTH}_{SEGMENTS}"
    pd.testing.assert_series_equal(got.reset_index(drop=True),
                                   out.reset_index(drop=True))


@pytest.mark.parametrize("length,named", [(None, LENGTH), (0, LENGTH),
                                          (1, LENGTH), (3, LENGTH),
                                          (-5, LENGTH), (4, 4), (60, 60)])
def test_a_length_below_the_minimum_falls_back_to_the_default(length, named):
    assert ts_energy_last_20(_walk(400), length=length).name == \
        f"TS_ENERGY_LAST_{named}_{SEGMENTS}"


def test_why_the_minimum_is_the_segment_count():
    """Shown rather than asserted: with fewer returns than chunks
    `np.array_split` hands the focused chunk nothing, `np.sum([])` is 0.0,
    and the column would be identically zero instead of a share."""
    for length in range(1, SEGMENTS):
        chunk = np.array_split(np.arange(length), SEGMENTS)[SEGMENT_FOCUS]
        assert chunk.size == 0
        assert np.sum(chunk ** 2.0) == 0.0
    assert np.array_split(np.arange(MIN_LENGTH),
                          SEGMENTS)[SEGMENT_FOCUS].size == 1


def test_too_short_an_input_returns_none():
    """`length` RETURNS, so `length + 1` closes are the fewest that give
    one value."""
    assert ts_energy_last_20(_walk(LENGTH)) is None
    assert int(ts_energy_last_20(_walk(LENGTH + 1)).notna().sum()) == 1


def test_offset_and_fillna():
    close = _walk(400)
    base = ts_energy_last_20(close)
    pd.testing.assert_series_equal(ts_energy_last_20(close, offset=2),
                                   base.shift(2), check_names=False)
    filled = ts_energy_last_20(close, fillna=-1.0)
    assert int((filled == -1.0).sum()) == LENGTH
    assert bool(filled.notna().all())
