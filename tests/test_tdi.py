# -*- coding: utf-8 -*-
"""TDI-20-2: `tdi`, M. H. Pee's Trend Detection Index (found in R TTR; PandasTa issue #148;
TTR is GPL-2.0 -- ported from the formula stated in the issue, never from
`TDI.R`).

    mom[T]     = price[T] - price[T - length]
    TDI_n_m[T] = (|sum_n mom| - (sum_2n |mom| - sum_n |mom|)) / price[T]

n = length (20), 2n = multiple * length (40 at the default multiple = 2).

What this file pins, in order of how much it would hurt to lose:

1. **Gate A, the issue's formula by scalar loops.** A fresh n-bar sum of
   signed momentum and fresh n-bar / 2n-bar sums of absolute momentum,
   sharing no pandas operation with the module. Unlike the issue's own
   prototype (`docs/issues/screen/ind_screen_r5.py`'s `ttr_tdi_20`, which
   computes `mom = (close - close.shift(length)).fillna(0)`), neither the
   oracle below nor the shipped module fills `mom`'s leading NaNs with 0 --
   the issue's formula has no such term. NaN masks are
   asserted IDENTICAL on every frame; values agree to 1e-9 points, not bit
   for bit -- pandas' rolling sum is an online accumulator, measured at
   most 3.109e-15 points off the loop on 376 .. 885 of 1,441 fired bars per
   1,500-bar frame (`docs/measure_tdi.py` §A1). This file's own 400-bar
   frames (same builders, same seeds) measure at most 3.553e-15
   (`docs/measure_tdi.py` §A1T) -- a different number from §A1's because a
   shorter series rounds differently, not a copy of it. ⚠ That figure
   happens to equal §D's x10-on-`jump` figure (a different comparison, the
   oracle loop vs. a price rescale, on the same frame) -- a coincidence of
   this run, not a leftover mislabel.
2. **Gate B, causality.** One shared past, two wholly different futures
   (each later bar scaled by one per-bar factor, up in one and down in
   the other): 0 of 1,499 offsets caught on each of the eight 1,500-bar
   frames (§B). FIVE look-ahead mutants are read off the shipped source,
   `exec`'d in memory, asserted LIVE first, then caught on 36 of 36 tail
   offsets of EVERY frame including `flat` -- unlike a ratio built on a
   high/low range, dividing by `close` never goes degenerate on a flat
   price, so every mutant stays visible there too.
3. **Gate D, scale.** x8, x64, 2^-20 and 2^300 are bit-identical on every
   frame; x10, x3.7 and x0.1 agree to 1e-9 points (measured at most
   4.066e-15) with identical NaN masks. ⚠ A level shift does NOT cancel,
   even loosely: `mom` and both rolling sums are shift-invariant (an
   additive constant cancels inside `price[T] - price[T - length]`), but
   the `/close` divisor is not, so the shifted column differs by up to
   2.256 (measured at +1e6) on a column whose own range is roughly
   [-2, 2]. This is NOT a bug -- it is the same reason the issue specifies
   a `/close` form rather than a `/price_at_T0` one.
4. **Gate C, reachability.** The warm-up is a CONSTANT `length + multiple
   * length - 1` = 59 bars on every frame including `flat` (1,441 of
   1,500 fire). A flat price fires every bar from the warm-up on, always
   at the constant value 0.0 (`mom` is identically 0, never NaN, so unlike
   `tao`'s high/low range this column never blanks on a flat run).
5. **Gate E, SHIP.** Run `is148-tdi-b1bb91c6` (issue-solver launcher,
   measured 2026-11-24, `module_sha1` `78fb84d9...`) measured `TDI_20_2`
   max |rho| 0.4924 vs `mad_pct_Pctl` (manifest, n = 391,017), per-frame max
   median 0.4915, 0.0% of the 89 ALTPORT-1 frames at or above 0.90, 398,849
   bars, 329 + 358 = 687 comparators -- well under the 0.76 ship line. The
   row is recorded in `docs/gate_e_ledger.csv`, so
   `test_gate_e_ledger.py::test_row_still_describes_its_module[tdi:TDI_20_2]`
   pins it. (An earlier run, `is148-tdi-c25dda7f`, was deleted from the
   ledger after a docstring fix moved the module's sha1; see
   `docs/TdiMeasured.md`.)

⚠ Counts of differing bars are NOT pinned to the digits measured: the
frames use `np.exp` / `np.cumsum`, so a different numpy kernel moves
prices in their last bits. What is pinned is structure: a bound, a NaN
mask, a first fired bar, a tolerance.

Every number quoted in this file comes from `docs/measure_tdi.py`.
"""
from pathlib import Path

import numpy as np
import pytest
from pandas import Series, date_range

from .context import pandas_ta  # noqa: F401

import pandas_ta as ta
from pandas_ta.trend.tdi import tdi

N = 400
LEVEL = 100.0
LENGTH = 20
MULTIPLE = 2
LONG_LENGTH = MULTIPLE * LENGTH
WARMUP = LENGTH + LONG_LENGTH - 1
ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "pandas_ta" / "trend" / "tdi.py"


# ------------------------------------------------------------------ frames
# Same builders and seeds as `docs/measure_tdi.py`, shortened to 400 bars.


def _index(n):
    return date_range("2020-01-01", periods=n, freq="h")


def _path(seed, n, mu=0.0, sigma=0.01, t=None):
    rng = np.random.default_rng(seed)
    r = rng.standard_t(t, n) * sigma * 0.6 if t else rng.normal(mu, sigma, n)
    return LEVEL * np.exp(np.cumsum(r))


def _series(values, tick=None):
    if tick:
        values = np.round(values / tick) * tick
    return Series(values, index=_index(len(values)))


def _walk(seed=7, n=N):
    return _series(_path(seed, n))


def _trend(seed=11, n=N):
    return _series(_path(seed, n, mu=0.003, sigma=0.008))


def _range_bound(seed=13, n=N):
    rng = np.random.default_rng(seed)
    x = np.zeros(n)
    for i in range(1, n):
        x[i] = 0.9 * x[i - 1] + rng.normal(0.0, 0.02)
    return _series(LEVEL * np.exp(x))


def _grid(seed=17, n=N):
    return _series(_path(seed, n), tick=0.01)


def _heavy(seed=19, n=N):
    return _series(_path(seed, n, t=2.0))


def _jump(seed=23, n=N):
    p = _path(seed, n)
    return _series(p * np.where(np.arange(n) >= n // 2, 1.5, 1.0))


def _flat(n=N):
    return _series(np.full(n, LEVEL))


def _coarse(seed=7, n=N):
    return _series(_path(seed, n, sigma=0.002), tick=0.5)


FRAMES = {
    "walk": _walk, "trend": _trend, "range-bound": _range_bound,
    "grid": _grid, "heavy-tailed": _heavy, "jump": _jump, "flat": _flat,
    "coarse": _coarse,
}
NAMES = list(FRAMES)
FIRING = [n for n in NAMES if n != "flat"]


def _run(close, fn=None, **kw):
    return (fn or tdi)(close, **kw)


# ----------------------------------------------------------------- helpers


def _bit_equal(a, b):
    if not bool((a.isna() == b.isna()).all()):
        return False
    m = a.notna()
    return bool((a[m] == b[m]).all())


def _abs(a, b):
    m = a.notna() & b.notna()
    return float((a[m] - b[m]).abs().max()) if int(m.sum()) else 0.0


def _differs(a, b):
    one = int((a.isna() != b.isna()).sum())
    m = a.notna() & b.notna()
    return one + int((a[m] != b[m]).sum())


# ----------------------------------------------------------------- oracle


def _oracle(close, length=LENGTH, multiple=MULTIPLE):
    """The issue's formula by scalar loops, no pandas operation, no fillna:
    `mom` is NaN for the first `length` bars, exactly as `price - price[n]`
    reads on real data with no history before bar 0."""
    c = close.to_numpy(float)
    n = c.size
    long_length = multiple * length
    mom = np.full(n, np.nan)
    for i in range(length, n):
        mom[i] = c[i] - c[i - length]
    out = np.full(n, np.nan)
    for i in range(length + long_length - 1, n):
        short_w = mom[i - length + 1:i + 1]
        long_w = mom[i - long_length + 1:i + 1]
        if np.isnan(short_w).any() or np.isnan(long_w).any():
            continue
        short_sum = 0.0
        short_abs = 0.0
        for x in short_w:
            short_sum += x
            short_abs += abs(x)
        long_abs = 0.0
        for x in long_w:
            long_abs += abs(x)
        out[i] = (abs(short_sum) - (long_abs - short_abs)) / c[i]
    return Series(out, index=close.index)


# ----------------------------------------------------------------- mutants

MOM_LINE = "    mom = close - close.shift(length)"
SHORT_SUM_LINE = "    short_sum = mom.rolling(length).sum()"
SHORT_ABS_LINE = "    short_abs_sum = abs_mom.rolling(length).sum()"
LONG_ABS_LINE = "    long_abs_sum = abs_mom.rolling(long_length).sum()"
OUT_LINE = "    tdi = (short_sum.abs() - (long_abs_sum - short_abs_sum)) / close"

CAUSALITY_MUTANTS = {
    "mom-lead": (MOM_LINE, "    mom = close.shift(-length) - close"),
    "short-sum-centred": (SHORT_SUM_LINE,
                          "    short_sum = mom.rolling(length, center=True).sum()"),
    "short-abs-centred": (SHORT_ABS_LINE,
                          "    short_abs_sum = abs_mom.rolling(length, center=True).sum()"),
    "long-abs-centred": (LONG_ABS_LINE,
                         "    long_abs_sum = abs_mom.rolling(long_length, center=True).sum()"),
    "output-early": (OUT_LINE,
                     "    tdi = ((short_sum.abs() - (long_abs_sum - short_abs_sum))"
                     " / close).shift(-1)"),
}


def _mutant(old, new):
    """`tdi` with one edit applied to the SHIPPED source, read off disk and
    exec'd in memory, so no mutant drifts from the code it edits."""
    src = SOURCE.read_text(encoding="utf-8")
    assert src.count(old) == 1, f"{old!r} occurs {src.count(old)} times"
    ns = {}
    exec(compile(src.replace(old, new), "<mutant>", "exec"), ns)
    return ns["tdi"]


def _futures(close, j, spread=3.0):
    """Two series bit-equal on bars < j and wholly different from j on:
    each later bar's price scaled by one per-bar factor (up / down)."""
    n = len(close)
    rng = np.random.default_rng(90_001 + j)
    u = rng.random(n)
    up, dn = np.ones(n), np.ones(n)
    up[j:] = 1.0 + spread * u[j:]
    dn[j:] = 1.0 / (1.0 + spread * u[j:])
    return close * up, close * dn


def _caught_at(fn, close, j):
    a, b = (_run(c, fn).iloc[:j] for c in _futures(close, j))
    return not _bit_equal(a, b)


def _offsets(n=N, how_many=12):
    return list(range(n - how_many, n))


# ------------------------------------------------------------ 1. GATE A


@pytest.mark.parametrize("name", NAMES)
def test_gate_a_the_issue_formula_by_loops_agrees(name):
    """Identical NaN masks, values to 1e-9 points (measured <= 3.553e-15 on
    this test's own 400-bar frames: `python docs/measure_tdi.py A1T`)."""
    close = FRAMES[name]()
    col, orc = _run(close), _oracle(close)
    assert bool((col.isna() == orc.isna()).all())
    assert _abs(col, orc) <= 1e-9


@pytest.mark.parametrize("name", FIRING)
def test_a_flat_price_never_empties_momentum(name):
    """`mom` is a difference of two closes, never a divide-by-range: it is
    never NaN once the warm-up has passed, on any of the moving frames."""
    close = FRAMES[name]()
    col = _run(close)
    assert bool(col.iloc[WARMUP:].notna().all())


# ------------------------------------------------------------ 2. GATE B


@pytest.mark.parametrize("name", NAMES)
def test_the_module_reads_no_future_bar(name):
    close = FRAMES[name]()
    assert [j for j in _offsets() if _caught_at(tdi, close, j)] == []


@pytest.mark.parametrize("name", NAMES)
def test_prefix_truncation_leaves_the_column_unchanged(name):
    close = FRAMES[name]()
    full = _run(close)
    for k in (N // 2, N - 7):
        assert _bit_equal(_run(close.iloc[:k]), full.iloc[:k])


@pytest.mark.parametrize("label", list(CAUSALITY_MUTANTS))
def test_a_look_ahead_mutant_is_live_before_it_is_swept(label):
    fn = _mutant(*CAUSALITY_MUTANTS[label])
    close = _walk()
    assert _differs(_run(close), _run(close, fn)) > 0


@pytest.mark.parametrize("label", list(CAUSALITY_MUTANTS))
def test_a_look_ahead_mutant_is_caught_on_every_offset(label):
    """Unlike a ratio divided by a high/low range, dividing by `close`
    never goes degenerate on a flat price, so every mutant is caught on
    every frame INCLUDING `flat` -- no partial-catch exception here."""
    fn = _mutant(*CAUSALITY_MUTANTS[label])
    for name in NAMES:
        close = FRAMES[name]()
        caught = [j for j in _offsets() if _caught_at(fn, close, j)]
        assert caught == _offsets(), f"{label} on {name}: {len(caught)}"


# ------------------------------------------------------------ 3. GATE D


@pytest.mark.parametrize("name", NAMES)
@pytest.mark.parametrize("factor", [8.0, 64.0, 2.0 ** -20, 2.0 ** 300])
def test_scale_an_exact_binary_factor_is_bit_identical(name, factor):
    close = FRAMES[name]()
    assert _bit_equal(_run(close), _run(close * factor))


@pytest.mark.parametrize("name", FIRING)
@pytest.mark.parametrize("factor", [10.0, 3.7, 0.1])
def test_scale_an_inexact_factor_agrees_within_tolerance(name, factor):
    """Measured <= 4.066e-15 points; asserted at 1e-9."""
    close = FRAMES[name]()
    col, other = _run(close), _run(close * factor)
    assert bool((col.isna() == other.isna()).all())
    assert _abs(col, other) <= 1e-9


def test_scale_a_level_shift_does_not_cancel():
    """⚠ NOT a bug: `mom` and both rolling sums cancel an additive
    constant, but the `/close` divisor does not. Measured 3.801e-02 /
    9.231e-01 / 2.256 points at shift +1 / +50 / +1e6 on `walk`, whose own
    column range is roughly [-2, 2] -- this is why the issue specifies a
    `/close` form, not a shift-invariant one."""
    close = _walk()
    col, other = _run(close), _run(close + 1.0)
    assert bool((col.isna() == other.isna()).all())
    assert _abs(col, other) > 1e-6


@pytest.mark.parametrize("name", NAMES)
def test_scale_fires_strictly_between_zero_and_n(name):
    col = _run(FRAMES[name]())
    assert 0 < int(col.notna().sum()) < col.size


# ------------------------------------------------------------ 4. GATE C


@pytest.mark.parametrize("name", NAMES)
def test_the_warm_up_is_a_constant_59_bars(name):
    col = _run(FRAMES[name]())
    assert bool(col.iloc[:WARMUP].isna().all())
    assert bool(col.iloc[WARMUP:].notna().all())


def test_a_flat_price_fires_at_a_constant_zero():
    col = _run(_flat()).dropna()
    assert col.size > 0
    assert bool((col == 0.0).all())


def test_the_shortest_input_that_produces_a_value():
    """`verify_series` floors the input at `length + multiple * length` = 60."""
    close = _walk(n=WARMUP + 1)
    col = _run(close)
    assert int(col.notna().sum()) == 1
    assert _run(close.iloc[:-1]) is None


def test_the_input_is_not_mutated():
    close = _walk()
    before = close.copy()
    _run(close)
    assert close.equals(before)


# ------------------------------------------------------------ 5. WIRING


def test_the_five_wiring_touch_points():
    close = _walk()
    df = close.to_frame("close")
    assert hasattr(ta.trend, "tdi")
    assert "tdi" in ta.Category["trend"]
    assert hasattr(df.ta, "tdi")
    col = _run(close)
    assert col.name == "TDI_20_2"
    assert col.category == "trend"
    assert _bit_equal(df.ta.tdi(), col)
    assert SOURCE.exists()


def test_the_accessor_forwards_every_parameter():
    """`hasattr` cannot see a keyword forwarded under the wrong name."""
    close = _walk()
    df = close.to_frame("close")
    kw = dict(length=14, multiple=3)
    acc = df.ta.tdi(**kw)
    assert _bit_equal(acc, _run(close, **kw))
    assert acc.name == "TDI_14_3"


def test_offset_and_fillna():
    close = _walk()
    col = _run(close)
    off = _run(close, offset=2)
    assert _bit_equal(off.iloc[2:].reset_index(drop=True),
                      col.iloc[:-2].reset_index(drop=True))
    filled = _run(close, fillna=-999.0)
    assert int((filled == -999.0).sum()) == int(col.isna().sum())
