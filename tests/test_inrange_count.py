# -*- coding: utf-8 -*-
"""B3-INRANGE-COUNT-20: `inrange_count`, the inside-range bar counter over
its cap (PandasTa issue #203, Reddit r/TradingView 1k894ya, tier 4).

    cnt[T]   = min(cnt + 1, n) if high[T] < highest(high, n)[T-1]
                               and low[T] > lowest(low, n)[T-1]
               else max(cnt - 2, 0)
    INRC_20  = cnt / 20

What this file pins, in order of how much it would hurt to lose:

1. **Gate A, the poster's Pine by explicit loops.** `_oracle` re-scans the
   `length` bars before T on every bar -- no rolling window, no shift, no
   code shared with the module -- and is asserted BIT-equal to the module
   with identical NaN masks on all eight synthetic frames (11,840 fired
   bars as measured), and at lengths 5, 10 and 50 on `walk` and `coarse`.
   Nothing is a tolerance: the column is an integer over `length`.
   ⚠ There is only ONE limb. The screen prototype
   (`docs/issues/screen/ind_screen_r9.py`) is gitignored and not on this
   machine, so this port is not asserted equal to what the 2026-10-29
   screen measured at Gate E; the Gate E run on the port is owed.
2. **The strict comparison against a tick grid.** `<` and `>` as the poster
   wrote them, so a bar that TIES the prior range's extreme is outside and
   costs 2. The non-strict reading is bit-identical on the five continuous
   frames (0 ties), differs on 57 bars of the 0.01-tick frame (4 ties,
   Spearman 0.9984), and on the 2.0-tick frame is a different column
   (1,075 ties, 1,478 of 1,480 bars differ, Spearman 0.0944). That frame
   reads exactly 0.0 on 1,055 of 1,480 bars. The FVGDEAD lesson in
   `CLAUDE.md`, applied in advance.
3. **Gate B, causality.** The module is caught on 0 of 1,499 split points
   (every bar but bar 0) on each of the eight frames in
   `docs/measure_inrange_count.py` §B, 0 of 36 in the tail here, and 0 of
   299 on a 300-bar walk. Four look-ahead mutants are read off the shipped
   source, edited and `exec`'d in memory; each is live (moves 563 .. 1,132
   bars of `walk`) and each is caught on every frame in `MUTANT_FRAMES`.
   ⚠ Not 36 of 36: the two envelope mutants are caught on only 1 .. 16 of
   36, and `low-envelope-lead` on 0 of 36 on `trend` (an uptrend rarely
   puts a bar's low at its window's minimum), so `trend` and `flat` are
   left out of `MUTANT_FRAMES` and kept in the receipt.
4. **Gate D, scale.** x8 and x64 bit-identical on every frame and at price
   levels 1e-6, 1e+6 and 1e+100. Only comparisons touch the prices, so
   x10, x3.7 and x0.1 were ALSO bit-identical on all eight frames as
   measured; the test asserts the required tolerance (NaN masks equal,
   values within 1e-9), not the bit-equality, since an inexact rescale
   could in principle merge two neighbouring prices.
5. **Gate C, reachability.** 1,480 of 1,500 bars fire on every frame
   (warm-up exactly `length` bars), with 21 distinct values on the six
   continuous and 0.01-tick frames, 15 on `coarse` and 1 (constant 0.0) on
   `flat`, where every bar ties its own range. Both bounds, 0 and 1, are
   reached on 6 of the 8 frames.
6. **The guards.** A NaN or infinite high or low empties its own bar,
   moves 0 earlier bars, and moves 28 later bars of `walk` (the count
   resumes from where it stood); unguarded, a `+inf` high or `-inf` low
   moved 30.

Every number above is printed by `python docs/measure_inrange_count.py`
on this tree. Assertions are bounds and structural relations rather than
the digits, except where a digit IS the structure (the warm-up, the 21
values).
"""
from pathlib import Path

import numpy as np
import pytest
from pandas import DataFrame, Series, date_range

from .context import pandas_ta  # noqa: F401

import pandas_ta as ta
from pandas_ta.volatility.inrange_count import inrange_count

N = 1500
LEVEL = 100.0
LENGTH = 20
COLUMN = "INRC_20"
OFFSETS = list(range(N - 36, N))
PLANT = 700


# ------------------------------------------------------------------ frames
# Same builders and seeds as `docs/measure_inrange_count.py`.


def _ohlc(close, seed):
    rng = np.random.default_rng(seed + 9_999)
    idx = date_range("2020-01-01", periods=close.size, freq="h")
    return (Series(close * (1.0 + 0.004 * rng.random(close.size)), index=idx),
            Series(close * (1.0 - 0.004 * rng.random(close.size)), index=idx),
            Series(close, index=idx))


def _walk(seed=7, n=N, level=LEVEL, sigma=0.01):
    rng = np.random.default_rng(seed)
    return _ohlc(level * np.exp(np.cumsum(rng.normal(0.0, sigma, n))), seed)


def _trend(seed=11, n=N, level=LEVEL):
    rng = np.random.default_rng(seed)
    return _ohlc(level * np.exp(np.cumsum(rng.normal(0.003, 0.008, n))), seed)


def _range_bound(seed=13, n=N, level=LEVEL):
    rng = np.random.default_rng(seed)
    x = np.zeros(n)
    for i in range(1, n):
        x[i] = 0.9 * x[i - 1] + rng.normal(0.0, 0.02)
    return _ohlc(level * np.exp(x), seed)


def _grid(seed=17, n=N, level=LEVEL, tick=0.01):
    h, l, c = _walk(seed, n, level)
    return (np.round(h / tick) * tick, np.round(l / tick) * tick,
            np.round(c / tick) * tick)


def _heavy(seed=19, n=N, level=LEVEL):
    rng = np.random.default_rng(seed)
    return _ohlc(level * np.exp(np.cumsum(rng.standard_t(2.0, n) * 0.006)),
                 seed)


def _jump(seed=23, n=N, level=LEVEL):
    h, l, c = _walk(seed, n, level)
    f = Series(np.where(np.arange(n) >= 700, 1.5, 1.0), index=c.index)
    return h * f, l * f, c * f


def _flat(n=N, level=LEVEL):
    idx = date_range("2020-01-01", periods=n, freq="h")
    one = Series(np.full(n, level), index=idx)
    return one.copy(), one.copy(), one.copy()


def _coarse(seed=7, n=N, level=LEVEL, tick=2.0):
    h, l, c = _walk(seed, n, level)
    return (np.round(h / tick) * tick, np.round(l / tick) * tick,
            np.round(c / tick) * tick)


FRAMES = {
    "walk": _walk, "trend": _trend, "range-bound": _range_bound,
    "grid": _grid, "heavy-tailed": _heavy, "jump": _jump, "flat": _flat,
    "coarse": _coarse,
}
NAMES = list(FRAMES)
MOVING = [n for n in NAMES if n != "flat"]
CONTINUOUS = ["walk", "trend", "range-bound", "heavy-tailed", "jump"]
#: Every mutant caught on each of these; `flat` never moves and `trend`
#: never exposes `low-envelope-lead` (0 of 36, receipt §B).
MUTANT_FRAMES = [n for n in NAMES if n not in ("flat", "trend")]


def _hl(frame):
    return frame[0], frame[1]


def _scaled(frame, factor):
    return tuple(s * factor for s in frame)


def _bit_equal(a, b):
    if not bool((a.isna() == b.isna()).all()):
        return False
    m = a.notna()
    return bool((a[m] == b[m]).all())


def _spearman(a, b):
    m = a.notna() & b.notna()
    return float(a[m].corr(b[m], method="spearman"))


# ----------------------------------------------------------------- oracle


def _oracle(high, low, length=LENGTH, strict=True):
    """The poster's Pine by explicit loops: the envelope is re-scanned over
    bars T-length .. T-1 on every bar. Shares no code with the module."""
    h = high.to_numpy(dtype=float)
    l = low.to_numpy(dtype=float)
    out = np.full(h.size, np.nan)
    cnt = 0
    for t in range(length, h.size):
        hi, lo = -np.inf, np.inf
        for k in range(t - length, t):
            hi = h[k] if h[k] > hi else hi
            lo = l[k] if l[k] < lo else lo
        inside = (h[t] < hi and l[t] > lo) if strict else \
            (h[t] <= hi and l[t] >= lo)
        cnt = min(cnt + 1, length) if inside else max(cnt - 2, 0)
        out[t] = cnt / length
    return Series(out, index=high.index)


# ----------------------------------------------------------------- mutants

SOURCE = Path(__file__).resolve().parents[1] / "pandas_ta" / "volatility" \
    / "inrange_count.py"

CAUSALITY_MUTANTS = [
    ("high-envelope-lead",
     "    hh = h.rolling(length, min_periods=1).max().shift(1)",
     "    hh = h.rolling(length, min_periods=1).max().shift(-1)"),
    ("low-envelope-lead",
     "    ll = l.rolling(length, min_periods=1).min().shift(1)",
     "    ll = l.rolling(length, min_periods=1).min().shift(-1)"),
    ("high-lead",
     "    inrc = Series(_count(h.to_numpy(dtype=float),",
     "    inrc = Series(_count(h.shift(-1).to_numpy(dtype=float),"),
    ("output-early", "    # Offset\n    if offset != 0:",
     "    inrc = inrc.shift(-1)\n    # Offset\n    if offset != 0:"),
]
GUARD_OFF = ("    h = high.where(np.isfinite(high))\n"
             "    l = low.where(np.isfinite(low))",
             "    h = high\n    l = low")


def _mutant(old, new):
    src = SOURCE.read_text(encoding="utf-8")
    assert src.count(old) == 1, f"{old!r} occurs {src.count(old)} times"
    ns = {}
    exec(compile(src.replace(old, new), "<mutant>", "exec"), ns)
    return ns["inrange_count"]


def _futures(frame, j, spread=3.0):
    """The frame, and the frame with bars >= j scaled UP by [1.5, 4] or DOWN
    by its reciprocal; all three agree bit for bit on bars < j. The
    untouched tail is what catches `output-early`: an up/down pair alone
    puts bar j outside under both, and caught it on 0 of 36 of `walk`."""
    h, l, c = frame
    rng = np.random.default_rng(90_001 + j)
    f = np.ones(c.size)
    f[j:] = 1.5 + (spread - 0.5) * rng.random(c.size)[j:]
    up, dn = Series(f, index=c.index), Series(1.0 / f, index=c.index)
    return (h, l), (h * up, l * up), (h * dn, l * dn)


def _caught_at(fn, frame, j):
    base, *others = _futures(frame, j)
    a = fn(*base).iloc[:j]
    return any(not _bit_equal(a, fn(*o).iloc[:j]) for o in others)


def _sweep(fn, frame, offsets=None):
    return sum(_caught_at(fn, frame, j) for j in (offsets or OFFSETS))


def _generator_desc():
    import ast
    import re
    path = Path(__file__).resolve().parents[1] / "docs" \
        / "gen_indicator_dictionary.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    fn = next(n for n in tree.body
              if isinstance(n, ast.FunctionDef) and n.name == "desc")
    ns = {"re": re}
    exec(compile(ast.Module(body=[fn], type_ignores=[]),
                 "<gen_indicator_dictionary.desc>", "exec"), ns)
    return ns["desc"]


# -------------------------------------------------- wiring and arguments


def test_name_registration_and_accessor():
    """The five wiring touch points, through the three call styles."""
    assert "inrange_count" in ta.Category["volatility"]
    h, l, c = _walk()
    col = inrange_count(h, l)
    assert col.name == COLUMN
    assert col.category == "volatility"
    df = DataFrame({"high": h, "low": l, "close": c})
    via = df.ta.inrange_count()
    assert via.name == COLUMN
    assert _bit_equal(via, col)
    assert df.ta.inrange_count(length=10).name == "INRC_10"


def test_a_frame_shorter_than_the_window_is_refused():
    """`length + 1` bars is the shortest frame with one bar to judge."""
    h, l, _ = _walk(n=40)
    assert inrange_count(h.iloc[:LENGTH], l.iloc[:LENGTH]) is None
    out = inrange_count(h.iloc[:LENGTH + 1], l.iloc[:LENGTH + 1])
    assert int(out.notna().sum()) == 1


def test_offset_and_fillna_do_what_the_kwargs_say():
    base = inrange_count(*_hl(_walk()))
    moved = inrange_count(*_hl(_walk()), offset=2)
    m = base.shift(2).notna()
    assert bool((moved[m] == base.shift(2)[m]).all())
    assert int(inrange_count(*_hl(_walk()), fillna=0.0).isna().sum()) == 0


# ------------------------------------------------------------------ Gate A


@pytest.mark.parametrize("name", NAMES)
def test_gate_a_matches_the_poster_formula_by_explicit_loops(name):
    """Bit-equal to `_oracle`, identical NaN masks; 1,480 fired bars per
    frame as measured."""
    frame = FRAMES[name]()
    assert _bit_equal(inrange_count(*_hl(frame)), _oracle(*_hl(frame)))


@pytest.mark.parametrize("length", [5, 10, 50])
@pytest.mark.parametrize("name", ["walk", "coarse"])
def test_gate_a_holds_at_other_lengths(name, length):
    frame = FRAMES[name]()
    col = inrange_count(*_hl(frame), length=length)
    assert col.name == f"INRC_{length}"
    assert _bit_equal(col, _oracle(*_hl(frame), length=length))


def test_gate_a_hand_frame_steps_plus_one_and_minus_two():
    """A hand frame with length 3: three inside bars (+1 each, capped at 3),
    one breakout (-2), one inside (+1), two breakouts (-2 then clipped at 0)."""
    highs = [10, 11, 10, 10.5, 10.4, 10.3, 10.2, 12, 11.5, 13, 14]
    lows = [9, 8, 9, 8.5, 8.6, 8.7, 8.8, 8.9, 9.0, 9.1, 9.2]
    idx = date_range("2020-01-01", periods=len(highs), freq="h")
    col = inrange_count(Series(highs, index=idx, dtype=float),
                        Series(lows, index=idx, dtype=float), length=3)
    got = (col * 3).round().tolist()
    assert np.isnan(got[:3]).all()
    assert got[3:] == [1, 2, 3, 3, 1, 2, 0, 0]


@pytest.mark.parametrize("name", CONTINUOUS)
def test_the_strict_comparison_costs_nothing_on_continuous_prices(name):
    """0 ties on these frames, so `<` and `<=` are the same column."""
    frame = FRAMES[name]()
    assert _bit_equal(inrange_count(*_hl(frame)),
                      _oracle(*_hl(frame), strict=False))


@pytest.mark.parametrize("name,rho_max", [("grid", 0.9999), ("coarse", 0.5)])
def test_the_strict_comparison_is_the_column_on_a_tick_grid(name, rho_max):
    """Measured: 57 bars differ on the 0.01-tick frame (Spearman 0.9984),
    1,478 of 1,480 on the 2.0-tick frame (0.0944)."""
    frame = FRAMES[name]()
    col, alt = inrange_count(*_hl(frame)), _oracle(*_hl(frame), strict=False)
    m = col.notna()
    assert int((col[m] != alt[m]).sum()) > 0
    assert _spearman(col, alt) < rho_max


# ------------------------------------------------------------------ Gate B


@pytest.mark.parametrize("name", NAMES)
def test_gate_b_mutant_the_module_reads_no_future_bar(name):
    """0 of 36 tail offsets; §B of the measure script runs 0 of 1,499."""
    assert _sweep(inrange_count, FRAMES[name]()) == 0


def test_gate_b_mutant_the_module_reads_no_future_bar_at_any_offset():
    """Every bar but bar 0 of a 300-bar walk as a split point: 0 of 299."""
    frame = _walk(n=300)
    assert _sweep(inrange_count, frame, list(range(1, 300))) == 0


@pytest.mark.parametrize("name", MUTANT_FRAMES)
def test_gate_b_mutant_every_lookahead_edit_is_caught(name):
    """Each of the four mutants caught somewhere in the 36 tail offsets.
    Measured counts: envelope mutants 1 .. 13, `high-lead` 23 .. 35,
    `output-early` 17 .. 31 on these six frames."""
    frame = FRAMES[name]()
    caught = {label: _sweep(_mutant(old, new), frame)
              for label, old, new in CAUSALITY_MUTANTS}
    assert all(v > 0 for v in caught.values()), caught


@pytest.mark.parametrize("label,old,new", CAUSALITY_MUTANTS,
                         ids=[m[0] for m in CAUSALITY_MUTANTS])
def test_gate_b_mutant_each_edit_is_live_against_the_module(label, old, new):
    """Each mutant moves the column on unperturbed `walk` (563 .. 1,132
    bars as measured), so a low catch count is not an inert edit."""
    frame = _walk()
    base, mut = inrange_count(*_hl(frame)), _mutant(old, new)(*_hl(frame))
    m = base.notna() & mut.notna()
    assert int((base[m] != mut[m]).sum()) > 0


# ------------------------------------------------------------------ Gate C


@pytest.mark.parametrize("name", MOVING)
def test_gate_c_the_column_fires_and_is_not_constant(name):
    """1,480 of 1,500 fired on each frame: the warm-up is exactly `length`.
    `0 < non-zero < fired` and more than one distinct value."""
    col = inrange_count(*_hl(FRAMES[name]()))
    v = col.dropna()
    assert v.size == N - LENGTH
    assert bool(col.iloc[LENGTH:].notna().all())
    assert 0 < int((v != 0).sum()) < v.size
    assert v.nunique() > 1
    assert v.min() >= 0.0 and v.max() <= 1.0


@pytest.mark.parametrize("name", ["walk", "range-bound", "grid",
                                  "heavy-tailed", "jump", "trend"])
def test_gate_c_every_step_of_the_counter_is_reached(name):
    """All 21 values 0/20 .. 20/20 on these six frames; `coarse` reaches 15."""
    v = inrange_count(*_hl(FRAMES[name]())).dropna()
    assert sorted(set((v * LENGTH).round().astype(int))) == list(range(21))


def test_a_flat_price_is_constant_zero():
    """Every bar of a flat price TIES its own prior range, so the strict
    rule calls it outside: 0.0 on all 1,480 fired bars."""
    v = inrange_count(*_hl(_flat())).dropna()
    assert v.size == N - LENGTH
    assert bool((v == 0.0).all())


# ------------------------------------------------------------------ Gate D


@pytest.mark.parametrize("name", NAMES)
@pytest.mark.parametrize("factor", [8, 64])
def test_gate_d_scale_is_bit_identical_under_exact_factors(name, factor):
    frame = FRAMES[name]()
    assert _bit_equal(inrange_count(*_hl(frame)),
                      inrange_count(*_hl(_scaled(frame, factor))))


@pytest.mark.parametrize("name", NAMES)
@pytest.mark.parametrize("factor", [10.0, 3.7])
def test_gate_d_scale_survives_an_inexact_factor(name, factor):
    """NaN masks equal, values within 1e-9. Measured bit-identical on all
    eight frames at x10, x3.7 and x0.1."""
    frame = FRAMES[name]()
    a = inrange_count(*_hl(frame))
    b = inrange_count(*_hl(_scaled(frame, factor)))
    assert bool((a.isna() == b.isna()).all())
    m = a.notna()
    assert float((a[m] - b[m]).abs().max()) <= 1e-9


@pytest.mark.parametrize("level", [1e-6, 1e+6, 1e+100])
def test_gate_d_scale_at_extreme_price_levels(level):
    frame = _walk(level=level)
    base = inrange_count(*_hl(frame))
    assert int(base.notna().sum()) == N - LENGTH
    assert _bit_equal(base, _oracle(*_hl(_walk())))
    for factor in (8, 64):
        assert _bit_equal(base, inrange_count(*_hl(_scaled(frame, factor))))


# ------------------------------------------------------- guards and edges


@pytest.mark.parametrize("leg", ["high", "low"])
@pytest.mark.parametrize("value", [np.nan, np.inf, -np.inf])
def test_a_bad_high_or_low_empties_its_bar_and_moves_no_earlier_bar(leg,
                                                                    value):
    """Measured on `walk`: own bar NaN, 0 earlier bars moved, 28 later bars
    moved for every plant; an infinity is bit-identical to a NaN."""
    h, l = _hl(_walk())
    base = inrange_count(h, l)
    parts = {"high": h.copy(), "low": l.copy()}
    parts[leg].iloc[PLANT] = value
    out = inrange_count(parts["high"], parts["low"])
    assert np.isnan(out.iloc[PLANT])
    assert _bit_equal(base.iloc[:PLANT], out.iloc[:PLANT])
    assert bool(out.iloc[PLANT + 1:].notna().all())
    nan_parts = {"high": h.copy(), "low": l.copy()}
    nan_parts[leg].iloc[PLANT] = np.nan
    assert _bit_equal(out, inrange_count(nan_parts["high"], nan_parts["low"]))


@pytest.mark.parametrize("leg,value", [("high", np.inf), ("low", -np.inf)])
def test_the_guard_is_what_keeps_an_infinity_out_of_the_envelope(leg, value):
    """Unguarded, a `+inf` high (or `-inf` low) sits in the envelope for 20
    bars: measured 30 later bars moved against 28 with the guard."""
    h, l = _hl(_walk())
    parts = {"high": h.copy(), "low": l.copy()}
    parts[leg].iloc[PLANT] = value
    guarded = inrange_count(parts["high"], parts["low"])
    unguarded = _mutant(*GUARD_OFF)(parts["high"], parts["low"])
    assert not _bit_equal(guarded, unguarded)


@pytest.mark.parametrize("value", [np.nan, 0.0, -5.0, 100.0])
def test_a_degenerate_frame_raises_nothing(value):
    """All-NaN fires nowhere; all-one-price frames read 0.0 throughout."""
    idx = date_range("2020-01-01", periods=60, freq="h")
    s = Series(np.full(60, value), index=idx)
    with np.errstate(all="raise"):
        out = inrange_count(s.copy(), s.copy())
    v = out.dropna()
    assert v.size == (0 if np.isnan(value) else 60 - LENGTH)
    assert bool((v == 0.0).all())


# ------------------------------------------------------------- docs


def test_the_docstrings_first_paragraph_survives_the_dictionary_cut():
    """136 characters as measured (§W), under the generator's 150."""
    body = []
    for line in inrange_count.__doc__.splitlines()[1:]:
        if line.strip():
            body.append(line.strip())
        elif body:
            break
    paragraph = " ".join(body)
    assert len(paragraph) <= 150, len(paragraph)
    assert _generator_desc()({"desc": paragraph}) == paragraph
