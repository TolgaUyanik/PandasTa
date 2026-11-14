# -*- coding: utf-8 -*-
"""TS-Q05-60: `ts_q05_60`, the 5% quantile of 60 simple returns -- a
one-day historical VaR (PandasTa issue #101).

    r        = close / close.shift(1) - 1
    s        = the window's 60 returns, SORTED
    TS_Q05   = s[2] + (s[3] - s[2]) * 0.9500000000000002

WHAT THIS FILE PINS, in order of how much it would hurt to lose.

1. **Gate A in three steps, the first of them BIT-equality.** Neither
   tsfresh nor QuantConnect Lean is installed in this worktree and web
   access is unavailable, so both are attributions and not oracles
   (`test_neither_source_library_is_installed_here` records that, so the
   claim cannot rot into "checked against tsfresh"). What IS checkable is
   pinned:

   * pandas' own `roll_quantile` retyped from its documented behaviour --
     sort the window, take the two order statistics around `q * (n - 1)`,
     blend them `vlow + (vhigh - vlow) * frac` -- sharing no code with the
     module: bit-equal on **1,440 of 1,440** bars of each of nine
     1,500-bar frames, and at `length` 2, 5, 20, 21 and 250;
   * the SOURCE's spelling, `pandas.Series.quantile` (bit-equal to
     `np.quantile`, also pinned) applied window by window: at most **ONE
     ulp**, max relative difference 2.1e-16, Spearman 1.000000 on each of
     the nine;
   * an EXACT rational oracle -- every return is a double, so a rational;
     the sort is exact and the blend is done in `fractions.Fraction` and
     rounded once. The module is at most **1.00 ulp** and on average
     0.00 .. 0.13 ulp out; numpy's lerp branch, which the module does NOT
     use, is the more accurate one on 7 of the 9 frames and tied on 2.
     ⚠ That last oracle is the only one of the three that can witness the
     one thing this spelling can get wrong, and what it says is that the
     cost of prototype parity is one bit.

2. **That the column reads 2 of the 60 returns and NOTHING else.** `q *
   (length - 1)` is 2.95, so the value is a fixed blend of the window's
   3rd and 4th smallest returns. Shown rather than asserted: on a window of
   exact returns `2**e - 1`, moving 56 of the 60 arbitrarily far away while
   keeping each one's rank leaves the value BIT-identical and equal to the
   closed form. The consequence a consumer must know is COARSENESS: 149
   distinct values over 1,440 bars on a walk, and 5 -- spanning 2.2e-16 --
   on a two-point frame.

3. **Gate B, by mutant, and an honest account of the one the blind sweep
   cannot catch.** Five mutants are live and caught 6 to 35 of 35 offsets,
   where the real module leaks **0 of 35** on each of three frames and at
   `length` 2, 5 and 250.
   ⚠ The sixth is the one worth reading. Shifting the NaN mask's own index
   by one bar makes bar T's mask read whether bar T+1's return is finite --
   a real look-ahead -- and on a clean frame it is not merely invisible but
   **DEAD**: every return there is finite, so the shifted mask admits the
   same bars and the output is bit-identical. What it can move is DERIVED:
   a bad close at J spoils the returns at J and J+1, so the shifted mask
   drops the return at J-1, and the window ending at **J-1** is the only
   one before J that holds it without also holding J. A frame with a bad
   close at every offset catches the mutant **12 of 12** and moves exactly
   bar J-1.
   ⚠ And the blind sweep is WEAKER here than on the fork's other return
   statistics, for the reason item 2 gives: splicing a new frame in at J
   changes the quantile only if it changes the window's 3rd or 4th smallest
   return. `back_date_two` is caught 35 of 35 on a walk and **9 of 35** on
   a tick-rounded one.

4. **Gate D, which is bit-identity BY CONSTRUCTION.** Every input is a
   price ratio and `8a / 8b` is the same double as `a / b`, so a x2^k
   rescale cannot move the sort order OR the blend: 1,440 of 1,440 bars on
   each of nine frames at x8 and x64, at `length` 2 / 5 / 20 / 250, and at
   price levels 1e-6, 1e+6 and 1e+100.
   ⚠ x10 / x3.7 / x0.1 / x1.0000001 are NOT bit-identical and are held to
   masks plus a relative tolerance (measured max 1.3e-14). On the TWO-POINT
   frame their Spearman is 0.04 .. 0.34, which is rounding and not a scale
   failure -- the column there is 5 doubles spanning 2.2e-16 -- so that
   frame is asserted on the relative difference only.

5. **The guards, each with what it costs and what it buys.** A close that
   is NaN, infinite, zero, negative or subnormal empties the 61 windows it
   sits in and NOTHING earlier (30 (value, position) pairs, 0 earlier bars
   moved in all 30); an overflowing ratio empties 60. ⚠ An UNDERFLOWING
   ratio does not, and must not: 1e308 followed by 1e-300 gives exactly
   -1.0, which is the correctly rounded return and is kept -- which is why
   the bound is [-1, +inf) and not (-1, +inf), and
   `test_the_bound_is_CLOSED_because_a_price_ratio_can_underflow` pins
   both halves of that. ⚠ There is NO
   dispersion floor, unlike `ts_kurt_60` / `ts_medskew_20` /
   `ts_above_mean_20`, and that is a decision this file pins with the exact
   oracle: a flat frame reads 0.0 on 240 windows and a 1%-a-bar ladder --
   whose constant return float64 renders as FOUR distinct doubles -- reads
   one and the same value on 240, both at 0.00 ulp of error, and a quiet
   1e-6 frame fires on 540 of 600 at 1.00 ulp. The siblings' absolute
   4096-ulp floor would empty 480 of those 1,020 honest windows (flat and
   ladder) and 0 dishonest ones; the quiet frame survives it.

6. **What the column IS, which is the thing most likely to be misread.** It
   is NEGATIVE VOLATILITY: -0.5804 .. -0.7406 against `NATR_60` and
   -0.2513 .. -0.6120 against `UI_60` on six frames, so a BIG value means a
   QUIET window. It is NOT the fork's `quantile` of the price level
   (-0.0273 .. +0.2006 against `QTL_60_0.05`) and it is a slow state
   (lag-1 autocorrelation 0.9672, lag-60 -0.3241; one bar moves exactly 60
   bars).

7. **That it IS the screen prototype**: bit-equal on 1,440 of 1,440 bars of
   each of nine frames with IDENTICAL masks, parting company only where a
   guard fires.

8. **That Gate E is still owed.** `test_the_gate_e_row_is_owed` asserts
   `docs/gate_e_ledger.csv` has NO row for this indicator, which is the
   receipt session's cue: the launcher runs Gate E after this session and a
   later session records the row and replaces that test with one pinning
   the row's identity.

Numbers come from `docs/measure_ts_q05_60.py`; the receipt is
`docs/TsQ0560Measured.md`.
Counts that depend on the last bits of a generated frame carry a band or a
tolerance; the structural facts are pinned exactly.
"""
import importlib
import types
import warnings
from fractions import Fraction

import numpy as np
import pandas as pd
import pytest
from pandas import Series

from .context import pandas_ta
from pandas_ta.statistics.quantile import quantile
from pandas_ta.statistics.ts_ac1_60 import ts_ac1_60
from pandas_ta.statistics.ts_kurt_60 import ts_kurt_60
from pandas_ta.statistics.ts_q05_60 import MIN_LENGTH, Q, ts_q05_60
from pandas_ta.volatility.natr import natr
from pandas_ta.volatility.ui import ui

LENGTH = 60
N = 1500
FIRED = N - LENGTH          # `length` RETURNS, so `length + 1` closes
ONE_ULP = 1.0

_REAL = importlib.import_module("pandas_ta.statistics.ts_q05_60")


# ------------------------------------------------------------------ frames


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
    """Every return is +-1%, so the window has 2 distinct values and the
    column is numerically a constant. The Gate D tie frame."""
    rng = np.random.default_rng(seed)
    return _from_returns(np.where(rng.random(n) < 0.5, sigma, -sigma))


def _trending(n=N, seed=9):
    return _walk(n, seed, sigma=0.01, drift=0.004)


def _flat(n=300, price=100.0):
    return Series(np.full(n, price))


def _ladder(n=300, price=100.0, rate=0.01):
    """A constant-rate rise. Its return is mathematically constant and
    float64 reproduces it as FOUR distinct doubles (measured), the smallest
    0.009999999999999565 -- so this frame is the one that would make a
    centre-and-spread statistic such as `ts_medskew_20` need a floor."""
    return Series(price * (1.0 + rate) ** np.arange(n, dtype=float))


def _quiet(n=600, price=100.0, step=1e-6, seed=13):
    """Honest but tiny returns: 1e-6 a bar."""
    rng = np.random.default_rng(seed)
    return _from_returns(step * rng.standard_normal(n)) * (price / 100.0)


def _crash(n=160, drop=-0.5):
    """`n / 2` bars of exactly -50% then `n / 2` of +1%. `1 + drop` is a
    power of two, so the returns are EXACTLY `drop` and the column's floor
    is reached bit-exactly."""
    return _from_returns(np.r_[np.full(n // 2, drop),
                               np.full(n - n // 2, 0.01)])


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
}
#: The frames the EXACT oracle is run on. It is a Python loop over
#: `Fraction`, so it is slow; `docs/measure_ts_q05_60.py` (A3) runs all
#: nine.
EXACT_FRAMES = ["walk", "tick-rounded", "heavy-tailed", "two-point"]
TIE_FRAME = "two-point"


# ----------------------------------------------------------------- helpers


def _ret(close):
    return close / close.shift(1) - 1.0


def _ohlc(close, band=0.004):
    """Deterministic SYNTHETIC high/low for the neighbours that need them."""
    return close * (1.0 + band), close * (1.0 - band)


def _spearman(a, b):
    m = a.notna() & b.notna()
    return float(a[m].corr(b[m], method="spearman"))


def _agree(a, b):
    """(masks equal, shared count, bit-equal count, max |difference|)."""
    masks = bool((a.isna() == b.isna()).all())
    m = a.notna() & b.notna()
    d = float((a[m] - b[m]).abs().max()) if int(m.sum()) else 0.0
    return masks, int(m.sum()), int((a[m] == b[m]).sum()), d


def _max_rel(a, b):
    m = a.notna() & b.notna()
    return float(((a[m] - b[m]).abs() / b[m].abs()).max())


def _max_ulps(a, b):
    """max |a - b| in units of the last place of `b`."""
    m = a.notna() & b.notna()
    y = b[m].to_numpy()
    ulp = np.abs(np.nextafter(y, np.inf) - y)
    return float((np.abs(a[m].to_numpy() - y) / ulp).max())


def _mean_ulps(a, b):
    m = a.notna() & b.notna()
    y = b[m].to_numpy()
    ulp = np.abs(np.nextafter(y, np.inf) - y)
    return float((np.abs(a[m].to_numpy() - y) / ulp).mean())


# -------------------------------------------------------------- the oracles


def _pandas_spelling(close, length=LENGTH, q=Q):
    """pandas' `roll_quantile` with `interpolation='linear'`, retyped from
    its documented behaviour and sharing no code with the module."""
    r = _ret(close).to_numpy()
    out = np.full(r.size, np.nan)
    i = q * (length - 1)
    lo, frac = int(i), i % 1
    for t in range(length, r.size):
        w = r[t - length + 1:t + 1]
        if not np.isfinite(w).all():
            continue
        s = np.sort(w)
        vlow, vhigh = s[lo], s[lo + 1]
        out[t] = vlow + (vhigh - vlow) * frac
    return Series(out, index=close.index)


def _source_windowed(close, length=LENGTH, q=Q):
    """tsfresh's `quantile(x, q)` -- `pandas.Series(x).quantile(q)` -- over
    the trailing `length` returns, one window at a time."""
    r = _ret(close)
    out = np.full(len(close), np.nan)
    for t in range(length, len(close)):
        w = r.iloc[t - length + 1:t + 1]
        if not np.isfinite(w.to_numpy()).all():
            continue
        out[t] = w.quantile(q)
    return Series(out, index=close.index)


def _numpy_spelling(close, length=LENGTH, q=Q):
    """numpy's `_lerp`, which for `t >= 0.5` evaluates
    `b - (b - a) * (1 - t)` rather than `a + (b - a) * t`."""
    r = _ret(close).to_numpy()
    out = np.full(r.size, np.nan)
    i = q * (length - 1)
    lo, frac = int(i), i % 1
    for t in range(length, r.size):
        w = r[t - length + 1:t + 1]
        if not np.isfinite(w).all():
            continue
        s = np.sort(w)
        a, b = s[lo], s[lo + 1]
        out[t] = b - (b - a) * (1.0 - frac)
    return Series(out, index=close.index)


def _exact(close, length=LENGTH, q=None):
    """The correctly rounded answer: every return is a double, so a
    rational, the sort is exact, and the blend is rounded exactly once.

    `q` defaults to `Fraction(Q)`, the EXACT value of the double 0.05 that
    the source is handed, and not to 1/20."""
    qf = Fraction(Q) if q is None else q
    r = _ret(close).to_numpy()
    out = np.full(r.size, np.nan)
    i = qf * (length - 1)
    lo = int(i)
    frac = i - lo
    for t in range(length, r.size):
        w = r[t - length + 1:t + 1]
        if not np.isfinite(w).all():
            continue
        s = sorted(Fraction(float(v)) for v in w)
        out[t] = float(s[lo] + (s[lo + 1] - s[lo]) * frac)
    return Series(out, index=close.index)


def _prototype(close, length=LENGTH, q=Q):
    """`docs/issues/screen/ind_screen.py`, candidate `ts_q05_60`, retyped
    (that tree is the owner's and gitignored, so it is copied rather than
    imported): `ret(c).rolling(60).quantile(0.05)` with
    `ret(c) = c / c.shift(1) - 1`. No guards of any kind."""
    return (close / close.shift(1) - 1.0).rolling(length).quantile(q)


# --------------------------------------------------- Gate A: the attribution


def test_neither_source_library_is_installed_here():
    """"tsfresh feature_calculators (MIT)" and "Lean ValueAtRisk" are
    ATTRIBUTIONS. Neither package is importable in this worktree and web
    access is unavailable, so no test in this file compares against either
    one; what Gate A checks is the published definition of
    `feature_calculators.quantile` (`pandas.Series.quantile`) plus the
    issue's own line. This test exists so that the distinction cannot
    quietly rot."""
    for name in ("tsfresh", "QuantConnect", "clr"):
        with pytest.raises(ImportError):
            importlib.import_module(name)


# ------------------------------------------------------- Gate A1: the bits


@pytest.mark.parametrize("frame", sorted(FRAMES))
def test_gate_a1_bit_equal_to_pandas_own_spelling_retyped(frame):
    """The strongest form Gate A can take on a column with no closed form:
    an independent reimplementation of the arithmetic pandas documents,
    agreeing on every bit. 1,440 of 1,440 bars, masks identical."""
    close = FRAMES[frame]()
    masks, shared, same, d = _agree(ts_q05_60(close), _pandas_spelling(close))
    assert masks
    assert same == shared == FIRED, (same, shared)
    assert d == 0.0


@pytest.mark.parametrize("length", [MIN_LENGTH, 5, 20, 21, 250])
def test_gate_a1_bit_equal_at_other_lengths(length):
    close = _walk()
    masks, shared, same, d = _agree(ts_q05_60(close, length=length),
                                    _pandas_spelling(close, length=length))
    assert masks
    assert same == shared == N - length
    assert d == 0.0


# --------------------------------------- Gate A2: the source's own spelling


@pytest.mark.parametrize("frame", sorted(FRAMES))
def test_gate_a2_the_source_spelling_agrees_to_one_ulp(frame):
    """tsfresh's `quantile` IS `pandas.Series.quantile`, which blends the
    two order statistics the other way round from pandas' ROLLING kernel.
    The two are the same number to within one ulp -- max relative
    difference 2.1e-16 measured, and the same ranks exactly."""
    close = FRAMES[frame]()
    col, src = ts_q05_60(close), _source_windowed(close)
    masks, shared, same, _ = _agree(col, src)
    assert masks
    assert shared == FIRED
    assert _max_ulps(col, src) <= ONE_ULP
    assert _max_rel(col, src) < 1e-15
    assert _spearman(col, src) > 1.0 - 1e-12


def test_gate_a2_series_quantile_is_numpys_quantile():
    """Which is why there are two oracles here and not three: the source's
    spelling and numpy's lerp branch are the same double."""
    close = _walk()
    masks, shared, same, d = _agree(_source_windowed(close),
                                    _numpy_spelling(close))
    assert masks and same == shared == FIRED and d == 0.0


# ---------------------------------------------- Gate A3: the exact oracle


@pytest.mark.parametrize("frame", EXACT_FRAMES)
def test_gate_a3_the_module_is_within_one_ulp_of_the_exact_answer(frame):
    """The only one of the three oracles that can witness what this
    spelling gets wrong. Measured: at most 1.00 ulp, and on average 0.0000
    (two-point, right-skewed) to 0.1340 (tick-rounded)."""
    close = FRAMES[frame]()
    col, ex = ts_q05_60(close), _exact(close)
    masks, shared, _, _ = _agree(col, ex)
    assert masks and shared == FIRED
    assert _max_ulps(col, ex) <= ONE_ULP
    assert _mean_ulps(col, ex) < 0.25


@pytest.mark.parametrize("frame", EXACT_FRAMES)
def test_gate_a3_numpys_branch_is_the_more_accurate_one(frame):
    """And the module does not use it, on purpose: prototype parity. What
    is asserted is the ORDERING -- numpy's branch is never further from the
    exact answer than pandas' -- and not the counts, which move with the
    last bits of a generated frame. Measured bit-equal counts against the
    EXACT oracle, module / numpy, on these four frames: 1,364 / 1,440,
    1,247 / 1,423, 1,262 / 1,406 and 1,440 / 1,440. (The module-against-
    SOURCE counts are a different table, §A2, and read 1,364 / 1,230 /
    1,228 / 1,440.)"""
    close = FRAMES[frame]()
    ex = _exact(close)
    mine = _mean_ulps(ts_q05_60(close), ex)
    theirs = _mean_ulps(_numpy_spelling(close), ex)
    assert _max_ulps(_numpy_spelling(close), ex) <= ONE_ULP
    assert theirs <= mine + 1e-12, (theirs, mine)


def test_gate_a3_the_double_005_is_not_one_twentieth():
    """The other float detail the formula hides. `q` is the double 0.05,
    whose exact value is 3602879701896397/72057594037927936; the two exact
    answers differ on 92 of 1,440 bars of a walk, by at most one ulp. The
    COUNT is not asserted -- it moves with the frame's last bits -- but the
    bound and the fact that they differ at all are."""
    close = _walk()
    a, b = _exact(close), _exact(close, q=Fraction(1, 20))
    masks, shared, same, _ = _agree(a, b)
    assert masks and shared == FIRED
    assert same < shared, "0.05 and 1/20 should not be the same oracle"
    assert _max_ulps(a, b) <= ONE_ULP
    assert Fraction(Q) != Fraction(1, 20)


# ------------------------------- Gate A4: which returns the column reads


def _pow2_window(exponents, price=100.0):
    """A `len(exponents) + 1`-close frame whose returns are exactly
    `2**e - 1`. Every step is a multiplication by a power of two, so the
    closes -- and the returns recovered from them -- are EXACT, which is
    what lets two such frames be compared bit for bit."""
    c = [float(price)]
    for e in exponents:
        c.append(c[-1] * 2.0 ** e)
    return Series(np.array(c))


def test_a4_only_the_third_and_fourth_smallest_returns_are_read():
    """Item 2, as a bit-equality. Two windows share their 3rd and 4th
    smallest returns (2**-3 - 1 and 2**-2 - 1) and agree on nothing else:
    the 56 above the pair move from +1.0 to +3.0, the two below it from
    -0.96875 / -0.9375 to -0.999999 / -0.999998, and the order inside the
    window is shuffled differently. Same double."""
    rng = np.random.default_rng(3)
    pair = [-3, -2]
    ea = np.array([-5, -4] + pair + [1] * 56, dtype=int)
    eb = np.array([-20, -19] + pair + [2] * 56, dtype=int)
    rng.shuffle(ea)
    rng.shuffle(eb)
    a = float(ts_q05_60(_pow2_window(ea)).iloc[-1])
    b = float(ts_q05_60(_pow2_window(eb)).iloc[-1])
    assert a == b

    i = Q * (LENGTH - 1)
    lo, frac = int(i), i % 1
    s2, s3 = 2.0 ** -3 - 1.0, 2.0 ** -2 - 1.0
    assert (lo, i) == (2, 2.95)
    assert a == s2 + (s3 - s2) * frac
    assert a == -0.75625


@pytest.mark.parametrize("length,lo,frac", [
    (MIN_LENGTH, 0, 0.05), (5, 0, 0.2), (20, 0, 0.9500000000000001),
    (21, 1, 0.0), (LENGTH, 2, 0.9500000000000002),
    (250, 12, 0.45000000000000107)])
def test_a4_which_order_statistics_each_length_reads(length, lo, frac):
    """`length` changes the column's MEANING and not only its smoothness.
    Below 21 it reads the smallest and the second smallest return; at
    exactly 21 the second smallest alone, because the fraction is 0.0.
    These are exact doubles, so they are pinned exactly."""
    i = Q * (length - 1)
    assert int(i) == lo
    assert i % 1 == frac


def test_a4_the_coarseness_that_follows():
    """Reading 2 of 60 returns makes the column a step function. BANDS,
    because a generated frame's last bits move the counts: measured 149
    distinct values on a walk and on a tick-rounded walk, 139 to 170 on
    eight of nine frames, and 5 on the two-point one."""
    for frame in ("walk", "tick-rounded"):
        col = ts_q05_60(FRAMES[frame]()).dropna()
        assert 100 <= col.unique().size <= 260, (frame, col.unique().size)
    col = ts_q05_60(_two_point()).dropna()
    assert col.unique().size <= 12
    assert float(col.max() - col.min()) < 1e-14
    assert int(col.value_counts().max()) > 1000


# ----------------------------------- Gate A5: the readings that were open


def test_a5_log_returns_keep_the_ranks_and_move_the_values():
    """A quantile commutes with an increasing transform, so the log-return
    reading has the SAME ranks (Spearman 1.000000) -- a rank miner cannot
    see the choice -- and values up to 5.4e-04 away, which a threshold rule
    can. The module takes the prototype's SIMPLE returns."""
    close = _walk()
    base = ts_q05_60(close)
    alt = np.log(close / close.shift(1)).rolling(
        LENGTH, min_periods=LENGTH).quantile(Q)
    assert _spearman(base, alt) > 1.0 - 1e-9
    d = float((base - alt).abs().max())
    assert 1e-5 < d < 1e-2


@pytest.mark.parametrize("how,lo,hi", [
    ("lower", 0.80, 0.95), ("higher", 0.99, 0.9999),
    ("nearest", 0.99, 0.9999), ("midpoint", 0.93, 0.99)])
def test_a5_the_interpolation_alternatives_are_different_columns(how, lo, hi):
    """`linear` is pandas' and numpy's default and so the source's. The
    others are not rescalings of it: measured Spearman 0.891866 (`lower`),
    0.998307 (`higher` and `nearest`, both `s[3]` at this length) and
    0.965027 (`midpoint`)."""
    close = _walk()
    base = ts_q05_60(close)
    alt = _ret(close).rolling(LENGTH, min_periods=LENGTH).quantile(
        Q, interpolation=how)
    assert lo < _spearman(base, alt) < hi
    assert float((base - alt).abs().max()) > 1e-4


def test_the_default_interpolation_is_linear():
    """The module does not spell `interpolation="linear"` out, because the
    keyword has moved between pandas versions while the default has not.
    This is what makes that silence safe: on THIS pandas the default is
    bit-equal to `linear` and distinguishable from every other option."""
    close = _walk()
    r = _ret(close)
    base = r.rolling(LENGTH, min_periods=LENGTH).quantile(Q)
    assert base.equals(r.rolling(LENGTH, min_periods=LENGTH).quantile(
        Q, interpolation="linear"))
    for how in ("lower", "higher", "nearest", "midpoint"):
        assert not base.equals(r.rolling(LENGTH, min_periods=LENGTH).quantile(
            Q, interpolation=how))


def test_a5_sixty_returns_and_not_sixty_closes():
    """The off-by-one a reader makes: 60 CLOSES is 59 returns, a near-copy
    (Spearman 0.983016, max |difference| 9.4e-03) whose first value lands
    one bar earlier. Priced so it is not re-argued."""
    close = _walk()
    base = ts_q05_60(close)
    alt = _ret(close).rolling(LENGTH - 1, min_periods=LENGTH - 1).quantile(Q)
    assert 0.95 < _spearman(base, alt) < 0.999
    assert float((base - alt).abs().max()) > 1e-3
    assert int(base.notna().to_numpy().argmax()) == LENGTH
    assert int(alt.notna().to_numpy().argmax()) == LENGTH - 1


def test_a5_the_sign_is_the_quantiles_own_and_not_vars():
    """VaR is usually quoted as a positive loss, `-quantile`. This column
    keeps the quantile's sign, so a WORSE tail is a SMALLER number. A rank
    miner sees a pure sign flip; a threshold rule does not."""
    close = _walk()
    base = ts_q05_60(close)
    assert _spearman(base, -base) < -1.0 + 1e-12
    assert bool((base.dropna() < 0).all())


@pytest.mark.parametrize("q,lo,hi", [(0.01, 0.55, 0.75), (0.10, 0.55, 0.78),
                                     (0.25, 0.35, 0.55), (0.50, 0.20, 0.40)])
def test_a5_the_neighbouring_quantiles_are_different_columns(q, lo, hi):
    """`q = 0.05` is the issue's. Its neighbours read different order
    statistics and are genuinely different columns rather than rescalings:
    measured Spearman 0.662418 / 0.673904 / 0.442682 / 0.291534."""
    close = _walk()
    base = ts_q05_60(close)
    alt = _ret(close).rolling(LENGTH, min_periods=LENGTH).quantile(q)
    assert lo < _spearman(base, alt) < hi


# --------------------------------------------- Gate A6: the prototype


@pytest.mark.parametrize("frame", sorted(FRAMES))
def test_a6_the_column_is_the_screen_prototype_bit_for_bit(frame):
    """What makes the 2026-10-24 screen's figures relevant to this port:
    identical masks and every one of 1,440 fired bars bit-equal, on each of
    nine frames."""
    close = FRAMES[frame]()
    masks, shared, same, d = _agree(ts_q05_60(close), _prototype(close))
    assert masks and same == shared == FIRED and d == 0.0


@pytest.mark.parametrize("label,bad,protofires", [
    ("inf", np.inf, 280), ("zero", 0.0, 280), ("subnormal", 1e-310, 280),
    ("negative", -100.0, 340)])
def test_a6_the_two_part_company_only_on_the_guards(label, bad, protofires):
    """A close a market cannot print is where the module and the prototype
    differ -- and the prototype's extra bars are windows built on that
    close. A NEGATIVE close is the worst of them: the prototype reports all
    340 bars, computing returns across a sign change."""
    close = _walk(400)
    close.iloc[200] = bad
    assert int(ts_q05_60(close).notna().sum()) == 340 - (LENGTH + 1)
    assert int(_prototype(close).notna().sum()) == protofires


def test_a6_a_nan_close_needs_no_guard_and_a_flat_frame_needs_no_floor():
    """The two places the prototype is already right: pandas propagates a
    NaN, so both empty the same 61 windows; and a flat frame has a
    well-defined 5% quantile, so both report 0.0 on all 240 of its
    windows."""
    close = _walk(400)
    close.iloc[200] = np.nan
    assert int(ts_q05_60(close).notna().sum()) \
        == int(_prototype(close).notna().sum()) == 340 - (LENGTH + 1)

    flat = _flat()
    masks, shared, same, d = _agree(ts_q05_60(flat), _prototype(flat))
    assert masks and same == shared == 300 - LENGTH and d == 0.0
    assert sorted(set(ts_q05_60(flat).dropna())) == [0.0]


# ------------------------------------------------------ Gate B: the mutants


BACK_DATE_TWO = (
    "    q05 = r.rolling(length, min_periods=length).quantile(Q)",
    "    q05 = r.rolling(length, min_periods=length).quantile(Q).shift(-2)")
BACK_DATE_FULL = (
    "    q05 = r.rolling(length, min_periods=length).quantile(Q)",
    "    q05 = r.rolling(length, min_periods=length).quantile(Q)"
    ".shift(-(length - 1))")
FORWARD_RETURN = (
    "        r = px / px.shift(1) - 1.0",
    "        r = px.shift(-1) / px - 1.0")
CENTERED_WINDOW = (
    "    q05 = r.rolling(length, min_periods=length).quantile(Q)",
    "    q05 = r.rolling(length, min_periods=length, center=True)"
    ".quantile(Q)")
ROLLED_WINDOW = (
    "    q05 = r.rolling(length, min_periods=length).quantile(Q)",
    "    q05 = r.shift(-(length // 2)).rolling(length, min_periods=length)"
    ".quantile(Q)")
#: The NaN mask's own index. A real look-ahead -- bar T's mask would read
#: whether bar T+1's return is finite -- and DEAD on a clean frame, where
#: every return but the first is finite. Caught by a designed frame below.
FORWARD_MASK = (
    "    r = r.where(np.isfinite(r))",
    "    r = r.where(np.isfinite(r).shift(-1, fill_value=True))")

MUTANTS = {
    "back_date_two": BACK_DATE_TWO,
    "back_date_full": BACK_DATE_FULL,
    "forward_return": FORWARD_RETURN,
    "centered_window": CENTERED_WINDOW,
    "rolled_window": ROLLED_WINDOW,
}
OFFSETS = range(120, N, 40)     # 35 offsets, past the 60-bar warm-up
PAIRS = {
    "walk": (_walk(), _walk(seed=97)),
    "tick-rounded": (_tick_rounded(), _tick_rounded(seed=56)),
    "heavy-tailed": (_heavy_tailed(), _heavy_tailed(seed=8)),
}
#: Measured catch counts of the blind sweep, out of 35 offsets, as BANDS.
#: ⚠ The low ones are the finding, not a defect in the mutant: splicing a
#: different frame in at J moves bar J-2 or J-1 only if it changes the
#: window's 3rd or 4th SMALLEST return, and on a tick-rounded frame it
#: often does not. `back_date_full` shifts by 59 bars and so always lands
#: on a different window; `centered_window` and `rolled_window` move the
#: whole window by 30.
CAUGHT = {
    "back_date_two": {"walk": (28, 35), "tick-rounded": (4, 20),
                      "heavy-tailed": (28, 35)},
    "back_date_full": {"walk": (30, 35), "tick-rounded": (30, 35),
                       "heavy-tailed": (30, 35)},
    "forward_return": {"walk": (28, 35), "tick-rounded": (3, 20),
                       "heavy-tailed": (28, 35)},
    "centered_window": {"walk": (30, 35), "tick-rounded": (30, 35),
                        "heavy-tailed": (30, 35)},
    "rolled_window": {"walk": (30, 35), "tick-rounded": (30, 35),
                      "heavy-tailed": (30, 35)},
}
BAD_OFFSETS = range(120, N, 120)        # 12 offsets, >= length + 1 apart


def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_ts_q05_60_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


def _caught(fn, close, other, offsets=OFFSETS, **kwargs):
    """Offsets J at which replacing every close from bar J on moves a bar
    BEFORE J -- which a causal column cannot do."""
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


@pytest.mark.parametrize("frame", sorted(PAIRS))
def test_the_real_module_leaks_nothing_under_the_mutant_sweep(frame):
    """Gate B's premise: replacing every close from bar J on changes no bar
    before J. 0 of 35 offsets on each of three frames."""
    close, other = PAIRS[frame]
    assert _caught(ts_q05_60, close, other) == []


@pytest.mark.parametrize("length", [MIN_LENGTH, 5, 250])
def test_the_real_module_leaks_nothing_at_other_lengths(length):
    close, other = PAIRS["walk"]
    assert _caught(ts_q05_60, close, other, length=length) == []
    assert int(ts_q05_60(close, length=length).notna()
               .to_numpy().argmax()) == length


@pytest.mark.parametrize("mutant", sorted(MUTANTS))
@pytest.mark.parametrize("frame", sorted(PAIRS))
def test_each_mutant_is_live_and_the_sweep_catches_it(mutant, frame):
    """Every mutant must CHANGE the column -- otherwise the test proves
    nothing -- and be caught within its measured band."""
    mod = _load_mutant(*MUTANTS[mutant])
    close, other = PAIRS[frame]
    assert not mod.ts_q05_60(close).equals(ts_q05_60(close))
    hits = _caught(mod.ts_q05_60, close, other)
    lo, hi = CAUGHT[mutant][frame]
    assert lo <= len(hits) <= hi, (mutant, frame, len(hits))


def test_the_mask_index_mutant_is_dead_on_a_clean_frame():
    """The sixth mutant, and the honest account of what Gate B's sweep
    cannot do here. Shifting the NaN mask by one bar makes bar T's mask
    read bar T+1's return -- a look-ahead. On a clean frame every return
    but the first is finite, so the shifted mask admits the same bars and
    the mutant produces a BIT-IDENTICAL column: not merely invisible to the
    sweep but dead. The test after this one is what gives it something to
    change."""
    mod = _load_mutant(*FORWARD_MASK)
    for frame, (close, other) in sorted(PAIRS.items()):
        assert mod.ts_q05_60(close).equals(ts_q05_60(close)), frame
        assert _caught(mod.ts_q05_60, close, other) == [], frame


def _bad_close_frame(seed=23):
    """The DESIGNED probe: a walk with a NaN close at every offset the
    sweep splices at, 120 bars apart so each one empties its 61 windows and
    the frame still fires in between."""
    c = _walk(N, seed).to_numpy().copy()
    for j in BAD_OFFSETS:
        c[j] = np.nan
    return Series(c)


def test_the_designed_probe_catches_the_mask_index_mutant():
    """What the shifted mask can move is DERIVED and then counted. A bad
    close at J spoils the returns at J and J+1, so the shifted mask drops
    the return at J-1; the window ending at J-1 is the only one before J
    that holds that return without also holding J, so bar J-1 is the only
    bar before J that can move. On a frame with a bad close at every
    offset: the real module still leaks 0 of 12, the mutant is caught 12 of
    12, and the bar it moves is J-1 and nothing else -- checked at ALL
    twelve offsets, and counting a changed VALUE as a move and not only a
    changed NaN mask."""
    close, other = _bad_close_frame(), _walk(N, 97)
    assert 600 < int(ts_q05_60(close).notna().sum()) < 800
    assert _caught(ts_q05_60, close, other, BAD_OFFSETS) == []

    mod = _load_mutant(*FORWARD_MASK)
    hits = _caught(mod.ts_q05_60, close, other, BAD_OFFSETS)
    assert len(hits) == len(list(BAD_OFFSETS))

    base = mod.ts_q05_60(close)
    for j in BAD_OFFSETS:
        p = close.copy()
        p.iloc[j:] = other.iloc[j:].values
        a, b = base.iloc[:j], mod.ts_q05_60(p).iloc[:j]
        changed = (a.isna() != b.isna()) | ((a - b).abs().fillna(0.0) > 0.0)
        assert np.flatnonzero(changed.to_numpy()).tolist() == [j - 1], j


def test_the_first_fired_bar_is_length():
    """`length` RETURNS, so `length + 1` closes -- bar 60 and not bar 59.
    The prototype agrees, because it reads the same 60 returns."""
    col = ts_q05_60(_walk())
    assert int(col.notna().to_numpy().argmax()) == LENGTH
    assert bool(np.isnan(col.iloc[LENGTH - 1]))
    assert int(_prototype(_walk()).notna().to_numpy().argmax()) == LENGTH


# ------------------------------------------------------- Gate C and Gate D


@pytest.mark.parametrize("frame", sorted(FRAMES))
def test_gate_c_the_column_fires_and_varies(frame):
    """0 < fires < n, and not all the same value, on each of nine frames.
    ⚠ The two-point frame passes "not all the same value" only
    numerically: its 5 distinct doubles span 2.2e-16. That is the honest
    reading of an order statistic on a two-valued return series, and it is
    why the band below is on the COUNT and not on the spread."""
    col = ts_q05_60(FRAMES[frame]())
    assert int(col.notna().sum()) == FIRED
    assert 0 < int(col.notna().sum()) < N
    assert col.dropna().unique().size >= 2
    assert bool(np.isfinite(col.dropna()).all())


def test_gate_c_the_sign_is_negative_on_every_ordinary_frame():
    """All 1,440 fired bars of each of the nine frames, including the
    strongly trending one, whose maximum is -0.005264."""
    for frame in FRAMES:
        col = ts_q05_60(FRAMES[frame]()).dropna()
        assert bool((col < 0.0).all()), frame
    assert float(ts_q05_60(_trending()).max()) < -1e-4


def test_the_column_is_bounded_below_by_minus_one_and_the_bound_is_tight():
    """Every close is finite, positive and normal by the time the ratio is
    taken, so every return is at least -1 and so is any blend of two of
    them. On every ordinary frame the inequality is STRICT; -0.5 is reached
    bit-exactly on a frame of -50% bars, where `1 + r` is a power of two."""
    for frame in FRAMES:
        assert float(ts_q05_60(FRAMES[frame]()).min()) > -1.0, frame
    assert float(ts_q05_60(_crash()).min()) == -0.5


def test_the_bound_is_CLOSED_because_a_price_ratio_can_underflow():
    """The mirror of the overflow guard, and the reason the docstring says
    [-1, +inf) and not (-1, +inf). `close[t-1] = 1e308` and
    `close[t] = 1e-300` are both finite, positive and normal, but their
    ratio 1e-608 flushes to 0.0, so the return is exactly -1.0. That is
    FINITE and it is KEPT -- it is the correctly rounded value of
    -1 + 1e-608, not a failure -- which is why `r.where(np.isfinite(r))`
    does not and should not drop it.

    Reaching -1.0 in the COLUMN takes four such returns in one window,
    because `q = 0.05` reads the 3rd and 4th smallest: ONE of them is the
    window's own minimum `s[0]`, so it never reaches `s[2]`/`s[3]` and the
    column's floor is untouched. It does MOVE 60 bars -- a -1.0 at `s[0]`
    demotes every ordinary return by one rank -- which is asserted here
    because it is the same mechanism read the other way round.

    ⚠ This frame perturbs TWO returns: `close[200] = 1e308` also makes the
    return at bar 200 about +9.5e+305, finite and kept, the window MAXIMUM
    of the windows ending at 200..259. The moved range's UPPER end is
    structural (`201 + length - 1`); its LOWER end is measured on this
    frame -- bar 200 holds the huge positive return but not the -1.0, and
    it does not move only because this walk's own return at bar 200 is not
    among its window's four smallest.

    The three-bar cycle below is what gets to the bound while keeping every
    close normal and every other ratio finite: 1e308 -> 1e-300 underflows,
    1e-300 -> 1e8 is 1e+308 and 1e8 -> 1e308 is 1e+300."""
    base = ts_q05_60(_walk(400))
    c = _walk(400).to_numpy().copy()
    c[200], c[201] = 1e308, 1e-300
    r = Series(c) / Series(c).shift(1) - 1.0
    assert float(r.iloc[201]) == -1.0
    assert bool(np.isfinite(r.iloc[201]))
    one = ts_q05_60(Series(c))
    assert int(one.notna().sum()) == 340
    assert float(one.min()) > -1.0          # one of them cannot reach q=0.05
    assert int((one == -1.0).sum()) == 0
    changed = (base.isna() != one.isna()) | ((base - one).abs().fillna(0.0)
                                             > 0.0)
    assert np.flatnonzero(changed.to_numpy()).tolist() \
        == list(range(201, 261))

    many = ts_q05_60(Series(np.tile([1e308, 1e-300, 1e8], 30)))
    assert int((_ret(Series(np.tile([1e308, 1e-300, 1e8], 30)))
                == -1.0).sum()) == 30
    assert int(many.notna().sum()) == 30
    assert float(many.min()) == -1.0
    assert bool((many.dropna() == -1.0).all())


def test_a_flat_frame_reads_zero_and_a_ladder_reads_its_own_return():
    """Both are legitimate readings and not degenerate ones: 95% of a flat
    window's bars were not down, and 95% of a 1%-a-bar rise's bars were up
    by 1%. ⚠ The ladder is the witness that this column is NOT bounded
    above by zero.

    ⚠ And it is the witness for the no-floor decision. The ladder's return
    is mathematically constant but float64 gives it FOUR distinct values;
    an order statistic simply PICKS one of them, so all 240 windows read
    the same double -- 0.009999999999999787 here, 2.1e-16 under 0.01 --
    rather than amplifying the jitter the way a standardised moment does.
    Neither the exact value nor the exact count of distinct values is
    pinned: `_ladder` builds its closes with `np.power`, which numpy
    DISPATCHES, so a kernel with a different last bit could redistribute
    the four returns. Measured here and again under
    `docs/measure_ts_q05_60_cpu.py`: one single value, 0.009999999999999787.
    What is asserted is the band and the tolerance, which is what carries
    the no-floor argument."""
    flat, ladder = ts_q05_60(_flat()), ts_q05_60(_ladder())
    assert int(flat.notna().sum()) == int(ladder.notna().sum()) == 300 - LENGTH
    assert sorted(set(flat.dropna())) == [0.0]
    values = ladder.dropna().unique()
    assert 1 <= values.size <= 4
    assert float(np.abs(values - 0.01).max()) < 1e-15
    assert float(ladder.min()) > 0.0
    assert np.unique(_ret(_ladder()).dropna().to_numpy()).size > 1


@pytest.mark.parametrize("k", [8.0, 64.0])
@pytest.mark.parametrize("frame", sorted(FRAMES))
def test_gate_d_scale_x8_and_x64_are_bit_identical(frame, k):
    """BY CONSTRUCTION: `8a / 8b` is the same double as `a / b`, so the
    window's values -- and so their sort order and the blend -- cannot move
    at all. 1,440 of 1,440 fired bars on each of nine frames at both
    factors."""
    close = FRAMES[frame]()
    masks, shared, same, d = _agree(ts_q05_60(close), ts_q05_60(close * k))
    assert masks and same == shared == FIRED and d == 0.0


@pytest.mark.parametrize("length", [MIN_LENGTH, 5, 20, 250])
def test_gate_d_scale_x8_at_other_lengths(length):
    close = _walk()
    masks, shared, same, d = _agree(ts_q05_60(close, length=length),
                                    ts_q05_60(close * 8.0, length=length))
    assert masks and same == shared == N - length and d == 0.0


@pytest.mark.parametrize("price", [1e-6, 1e6, 1e100])
def test_gate_d_scale_x8_at_extreme_price_levels(price):
    close = _walk() * (price / 100.0)
    masks, shared, same, d = _agree(ts_q05_60(close), ts_q05_60(close * 8.0))
    assert masks and same == shared == FIRED and d == 0.0


@pytest.mark.parametrize("k", [10.0, 3.7, 0.1, 1.0000001])
@pytest.mark.parametrize("frame", ["walk", "tick-rounded", "heavy-tailed"])
def test_gate_d_scale_x10_and_x37_hold_masks_and_a_tolerance(frame, k):
    """A factor that is not a power of two perturbs the returns in their
    last bits, which can swap two nearly equal order statistics. Masks must
    still match exactly; measured max relative difference 1.3e-14 and
    Spearman 1.000000."""
    close = FRAMES[frame]()
    base, other = ts_q05_60(close), ts_q05_60(close * k)
    masks, shared, _, _ = _agree(base, other)
    assert masks and shared == FIRED
    assert _max_rel(base, other) < 1e-12
    assert _spearman(base, other) > 0.9999


@pytest.mark.parametrize("k", [10.0, 3.7, 0.1, 1.0000001])
def test_gate_d_scale_on_the_tie_frame_reads_rounding_and_not_a_failure(k):
    """The one frame where Gate D's Spearman is NOT the reading. The
    two-point frame's column is 5 doubles spanning 2.2e-16, so a rank
    correlation on it is reading rounding: measured 0.0401 .. 0.3352. What
    is asserted is what a last-bit change cannot break -- the masks and the
    relative difference."""
    close = _two_point()
    base, other = ts_q05_60(close), ts_q05_60(close * k)
    masks, shared, _, _ = _agree(base, other)
    assert masks and shared == FIRED
    assert _max_rel(base, other) < 1e-12
    assert float(base.dropna().max() - base.dropna().min()) < 1e-14


@pytest.mark.parametrize("power", [2.0, 0.5])
def test_gate_d_a_monotone_transform_of_price_keeps_the_ranks(power):
    """Stronger than a rescale, and a different statement: `price ** 2` is
    not a rescale at all -- it doubles every log return -- but a quantile
    is equivariant under any INCREASING transform of the return, so the
    ranks survive while the values move by up to 0.0316."""
    close = _walk()
    base, other = ts_q05_60(close), ts_q05_60(close ** power)
    assert _spearman(base, other) > 1.0 - 1e-9
    assert float((base - other).abs().max()) > 1e-3


# ---------------------------------------------------------------- the guards


@pytest.mark.parametrize("bad", [np.nan, np.inf, -np.inf, 0.0, -100.0, 1e-310])
@pytest.mark.parametrize("pos", [0, 1, LENGTH, 200, 399])
def test_a_bad_close_empties_its_windows_and_nothing_earlier(bad, pos):
    """A close that is not a finite, normal, positive float has no return,
    and it spoils TWO of them -- its own and the next bar's -- so it empties
    the `length + 1` = 61 windows it sits in. 30 (value, position) pairs,
    and in all 30 the number of bars moved BEFORE the bad bar is 0."""
    base = ts_q05_60(_walk(400))
    close = _walk(400)
    close.iloc[pos] = bad
    col = ts_q05_60(close)
    emptied = [i for i in range(400)
               if col.isna().iloc[i] and not base.isna().iloc[i]]
    assert [i for i in emptied if i < pos] == []
    expected = {0: 1, 1: 2, LENGTH: LENGTH + 1, 200: LENGTH + 1, 399: 1}[pos]
    assert len(emptied) == expected
    if pos == 200:
        assert emptied == list(range(200, 261))


def test_an_overflowing_ratio_empties_sixty_windows():
    """1e-300 followed by 1e50 is a ratio of 1e+350, so an infinite return.
    Both closes are themselves normal and positive, so only ONE return is
    spoiled and only 60 windows go -- one fewer than for a bad close."""
    base = ts_q05_60(_walk(400))
    c = _walk(400).to_numpy().copy()
    c[200], c[201] = 1e-300, 1e50
    col = ts_q05_60(Series(c))
    emptied = [i for i in range(400)
               if col.isna().iloc[i] and not base.isna().iloc[i]]
    assert emptied == list(range(201, 261))


@pytest.mark.parametrize("mag", [1e10, 1e100, 1e200, 1e300])
def test_one_huge_return_stays_local(mag):
    """There is no sum and no accumulator here, which is what separates this
    module from `ts_kurt_60`: a return of 1e+300 is just the window's
    largest order statistic, so nothing is emptied and every later bar is
    bit-identical to the unspiked frame. `ts_kurt_60` without its
    fourth-power guard empties the whole remainder of the frame.

    The spike changes TWO returns, at bars 200 and 201, so the windows
    HOLDING a spiked return are the 61 ending at bars 200..260. The slice
    asserted below is wider on purpose -- bars 141..262, 122 bars -- so
    that it brackets those 61 on both sides."""
    close = _walk(400)
    spiked = close.copy()
    spiked.iloc[200] = spiked.iloc[200] * mag
    base, col = ts_q05_60(close), ts_q05_60(spiked)
    assert int(col.iloc[141:263].notna().sum()) == 122      # bars, not windows
    assert int(col.iloc[200:261].notna().sum()) == LENGTH + 1
    assert bool((base.iloc[263:] == col.iloc[263:]).all())


@pytest.mark.parametrize("frame,fires,worst", [
    ("flat", 240, 0.0), ("ladder", 240, ONE_ULP), ("quiet", 540, ONE_ULP)])
def test_there_is_no_dispersion_floor_and_the_exact_oracle_says_so(frame,
                                                                   fires,
                                                                   worst):
    """The decision this module takes and its siblings do not. A window with
    no dispersion has a well-defined 5% quantile -- its own constant return
    -- and nothing here divides by a spread, so there is nothing for a floor
    to protect. Against the exact rational oracle: a flat frame and a
    1%-a-bar ladder are CORRECTLY ROUNDED on all 240 of their windows, and a
    quiet 1e-6 frame is within one ulp on all 540 of its.

    ⚠ The ladder is asserted at ONE ulp and not at zero, although zero is
    what it measures on both dispatch paths. `_ladder` builds its closes
    with `np.power`, which numpy DISPATCHES; a kernel that moves their last
    bits redistributes the four return doubles, and a window where
    `s[2] != s[3]` blends them and can round. The flat frame has no such
    exposure -- its returns are exactly 0.0 by construction -- so there the
    0.00 is a theorem and is asserted as one.

    The second half is what the floor would COST, since the first half
    alone would not settle it: the 4096-ulp floor `ts_kurt_60` puts on the
    window's return RANGE empties the flat and ladder windows (range 0.0 and
    4.441e-16) and leaves the quiet frame alone (3.751e-06), so it would
    throw away 480 correctly rounded windows to buy nothing."""
    close = {"flat": _flat, "ladder": _ladder, "quiet": _quiet}[frame]()
    col, ex = ts_q05_60(close), _exact(close)
    masks, shared, _, _ = _agree(col, ex)
    assert masks and shared == fires
    assert _max_ulps(col, ex) <= worst

    r = _ret(close)
    rolling = r.rolling(LENGTH, min_periods=LENGTH)
    floored = col.notna() & ((rolling.max() - rolling.min())
                             <= 4096 * np.finfo(float).eps)
    assert int(floored.sum()) == (0 if frame == "quiet" else fires)


def test_no_warning_is_raised_on_bad_closes():
    """The `errstate` is what keeps a RuntimeWarning out of the caller's
    log: an overflowing ratio is expected input here, not a surprise."""
    c = _walk(400).to_numpy().copy()
    c[100], c[101] = 1e-300, 1e50
    c[200], c[201], c[202] = 0.0, -5.0, np.inf
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        out = ts_q05_60(Series(c))
    assert int(out.notna().sum()) > 0


# ----------------------------------------- what the column actually is


@pytest.mark.parametrize("frame", ["walk", "tick-rounded", "heavy-tailed",
                                   "trending", "ar1+", "ar1-"])
def test_it_is_negative_volatility(frame):
    """Item 6, the single most important number for a consumer, on
    SYNTHETIC frames with SYNTHETIC high/low (close x 1.004 and x 0.996)
    because `natr` needs a range and these frames have only closes.
    Measured -0.5804 .. -0.7406 against `NATR_60` (the shallow end is
    `ar1-`, the deep end `ar1+`), -0.2513 .. -0.6120 against `UI_60`, and
    -0.2974 .. -0.6907 against the window's own return standard
    deviation."""
    close = FRAMES[frame]()
    high, low = _ohlc(close)
    col = ts_q05_60(close)
    sd = _ret(close).rolling(LENGTH, min_periods=LENGTH).std()
    assert -0.85 < _spearman(col, natr(high, low, close, length=LENGTH)) < -0.45
    assert -0.75 < _spearman(col, ui(close, length=LENGTH)) < -0.15
    assert -0.80 < _spearman(col, sd) < -0.20


@pytest.mark.parametrize("frame", ["walk", "tick-rounded", "heavy-tailed",
                                   "trending", "ar1+", "ar1-"])
def test_it_does_not_restate_the_forks_quantile_of_the_price_level(frame):
    """`QTL_60_0.05` is the SAME pandas machinery on the price LEVEL, which
    is the column most likely to be mistaken for this one. It is not:
    -0.0273 .. +0.2006 on six frames. Nor are the other 60-return
    statistics columns: -0.1803 .. +0.1094 (`TS_KURT_60`) and -0.2787 ..
    +0.4315 (`TS_AC1_60`)."""
    close = FRAMES[frame]()
    col = ts_q05_60(close)
    assert abs(_spearman(col, quantile(close, length=LENGTH, q=Q))) < 0.45
    assert abs(_spearman(col, ts_kurt_60(close))) < 0.45
    assert abs(_spearman(col, ts_ac1_60(close))) < 0.60


def test_the_level_to_expect_on_independent_windows():
    """20,000 INDEPENDENT windows, so the relation is not an artefact of
    overlap. A gaussian window reads a mean of -1.5664 sigma -- NOT the
    -1.6449 of the distribution's own 5% point, because the estimator reads
    the 3rd and 4th of 60 draws -- a student-t(2) one -2.8003 and a
    one-sided exponential one -0.9329. What the law's tails change is
    mostly the SPREAD: sd 0.2555 / 0.9387 / 0.0336.

    ⚠ This pins the STATISTIC, not the shipped function: 20,000 one-window
    calls would be a slow way to say the same thing. What transfers it is
    Gate A1's bit-equality against pandas' own spelling."""
    rng = np.random.default_rng(2026)
    i = Q * (LENGTH - 1)
    lo, frac = int(i), i % 1

    def _level(W):
        W = np.sort(W, axis=1)
        v = W[:, lo] + (W[:, lo + 1] - W[:, lo]) * frac
        return float(v.mean()), float(v.std())

    mean, sd = _level(rng.standard_normal((20000, LENGTH)))
    assert -1.62 < mean < -1.51 and 0.22 < sd < 0.29
    mean, sd = _level(rng.standard_t(2.0, (20000, LENGTH)))
    assert -3.2 < mean < -2.4 and 0.7 < sd < 1.2
    mean, sd = _level(rng.standard_exponential((20000, LENGTH)) - 1.0)
    assert -0.95 < mean < -0.91 and 0.02 < sd < 0.05


def test_it_is_a_slow_state_and_not_an_event_flag():
    """Two consecutive windows share 59 of their 60 returns, so the column
    autocorrelates at 0.9672 at lag 1 and 0.3287 at lag 30, and then goes
    NEGATIVE: -0.3241 at lag 60, because the window has moved past the bars
    that set the old reading."""
    col = ts_q05_60(_walk())
    assert float(col.autocorr(1)) > 0.90
    assert 0.15 < float(col.autocorr(30)) < 0.50
    assert float(col.autocorr(LENGTH)) < -0.10


def test_one_bar_moves_exactly_length_bars():
    """A -20% bar enters the window at bar 700 and leaves it at bar 760, so
    it moves exactly `length` = 60 bars and nothing else."""
    close = _walk()
    base = ts_q05_60(close)
    spiked = close.copy()
    spiked.iloc[700:] = spiked.iloc[700:] * 0.80
    moved = np.flatnonzero(((base - ts_q05_60(spiked)).abs() > 1e-12)
                           .to_numpy()).tolist()
    assert moved == list(range(700, 700 + LENGTH))


# ----------------------------------------------------------- the Gate E row


def test_the_gate_e_row_is_owed():
    """Gate E is run by the issue-solver launcher AFTER this session, so
    `docs/gate_e_ledger.csv` must have NO row for this indicator yet. That
    makes `tests/test_gate_e_ledger.py::
    test_every_indicator_that_needs_a_row_has_one` fail locally, which is
    expected and is what CI's `GATE_E_PENDING_OK=1` turns into a skip.

    ⚠ This test is the receipt session's CUE: it fails the moment the row
    is recorded, and must then be replaced by one pinning the row's
    IDENTITY (its `run`, module and column), the way `ts_imq_20` and
    `ts_cross_mean_20` did. `docs/TsQ0560Measured.md` §E carries the
    pending note."""
    import csv
    from pathlib import Path
    ledger = Path(__file__).resolve().parents[1] / "docs" / "gate_e_ledger.csv"
    rows = list(csv.DictReader(ledger.open(encoding="utf-8")))
    assert rows, "the ledger should not be empty"
    assert [r for r in rows if r["indicator"] == "ts_q05_60"] == []


# ------------------------------------------------------ wiring and arguments


def test_name_registration_and_accessor():
    close = _walk(400)
    out = ts_q05_60(close)
    assert out.name == f"TS_Q05_{LENGTH}"
    assert out.category == "statistics"
    assert "ts_q05_60" in pandas_ta.Category["statistics"]
    df = pd.DataFrame({"close": close})
    df.index = pd.date_range("2020-01-01", periods=len(close), freq="D")
    got = df.ta.ts_q05_60()
    assert got.name == f"TS_Q05_{LENGTH}"
    pd.testing.assert_series_equal(got.reset_index(drop=True),
                                   out.reset_index(drop=True))


@pytest.mark.parametrize("length,name", [(None, 60), (0, 60), (1, 60),
                                         (-5, 60), (20, 20)])
def test_a_length_below_the_minimum_falls_back_to_the_default(length, name):
    assert ts_q05_60(_walk(400), length=length).name == f"TS_Q05_{name}"


def test_length_one_would_be_the_return_itself_which_is_why_it_is_refused():
    """The reason for `MIN_LENGTH`, shown rather than asserted: the
    quantile of a single value is that value for every `q`, so `length` 1
    would be `percent_return` under another name rather than a quantile."""
    close = _walk(400)
    r = _ret(close)
    one = r.rolling(1, min_periods=1).quantile(Q)
    assert bool((one.dropna() == r.dropna()).all())
    assert ts_q05_60(close, length=1).name == f"TS_Q05_{LENGTH}"


def test_too_short_an_input_returns_none():
    """`length` RETURNS, so `length + 1` closes are the fewest that give
    one value."""
    assert ts_q05_60(_walk(LENGTH)) is None
    assert int(ts_q05_60(_walk(LENGTH + 1)).notna().sum()) == 1


def test_offset_and_fillna():
    close = _walk(400)
    base = ts_q05_60(close)
    pd.testing.assert_series_equal(ts_q05_60(close, offset=2),
                                   base.shift(2), check_names=False)
    pd.testing.assert_series_equal(ts_q05_60(close, offset=-2),
                                   base.shift(-2), check_names=False)
    filled = ts_q05_60(close, fillna=0.0)
    assert int(filled.isna().sum()) == 0
    assert bool((filled.iloc[:LENGTH] == 0.0).all())


def test_the_module_does_not_import_the_package_root():
    """The `TypeError: 'module' object is not callable` trap in CLAUDE.md:
    a helper is imported from its own module, never from the package."""
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert "from pandas_ta.statistics import" not in src
    assert "from pandas_ta.overlap import" not in src
