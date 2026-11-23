# -*- coding: utf-8 -*-
"""WAVEPM-14-100: `wavepm`, Whistler's Wave PM (PandasTa issue #261, finta
`WAVEPM` form as transcribed in the issue).

    r[T]           = std(close, 14)[T] / sma(close, 14)[T]      (ddof = 0)
    WAVEPM_14_100  = tanh(r[T] / sqrt(mean(r[T-99 .. T] ** 2)))

What this file pins, in order of how much it would hurt to lose:

⚠ **Gate A is OWED (source unread).** finta's `WAVEPM` source was not read
and none of its lines are cited, so the port is NOT cleared through Gates
A-F; issue #261 stays open for the attended reader. What follows checks
the module only against an oracle written from the same issue text.

1. **Gate A limb, the issue's finta form by explicit loops.** `_oracle` sums
   every window bar by bar -- no rolling, no code shared with the module --
   and matches it with identical NaN masks on all eight synthetic frames
   (9,716 fired bars pooled), max |diff| 3.25e-11 (`walk`), and at
   (length, lookback) (5, 20), (20, 50), (30, 200) on `walk` and `coarse`,
   max |diff| 3.15e-10. Not bit-equal: pandas' rolling sums are online, the
   oracle's are not. The test asserts 1e-9.
   ⚠ finta's source itself was not readable in this session (no network),
   so Gate A is against the issue's transcription of finta, not against
   finta's line numbers; the issue's definition is the contract here.
2. **The readings not taken.** ddof = 1 rescales every r by one constant,
   which cancels in r / rms: measured max |diff| 3.3e-16 .. 5.6e-16 between
   the ddof 0 and ddof 1 oracles on the seven moving frames. The
   ProRealCode reading (std NOT over the mean) is a different column: max
   |diff| 0.0363 .. 0.0882, Spearman 0.9777 .. 0.9982.
3. **Gate B, causality.** The module is caught on 0 of 1,499 split points
   (every bar but bar 0) on each of the eight frames in
   `docs/measure_wavepm.py` §B and 0 of 36 in the tail here. Four
   look-ahead mutants are read off the shipped source, edited and `exec`'d
   in memory; each moves 1,387 of 1,387 bars of `walk` and is caught on 36
   of 36 tail offsets on every moving frame (`mean-lead` 0 on `flat`: sigma =
   0 before the split, so r = rms = 0 and every bar before the split is NaN
   whatever mu reads).
4. **Gate D, scale.** x8 and x64 bit-identical on all eight frames and at
   price levels 1e-6, 1e+6 and 1e+100; x10 and x3.7 within 8.8e-11 with NaN
   masks equal; levels 1e-6 .. 1e+100 within 6.9e-11 of level 100.
5. **Gate C, reachability.** 1,388 of 1,500 bars fire on every moving frame
   (warm-up exactly length + lookback - 2 = 112 bars), all distinct on the
   six continuous and 0.01-tick frames, 1,286 distinct on `coarse`, where
   99 bars read exactly 0.0 (a 14-bar window of one price). Above 0.5 on
   982 .. 1,236 bars, above 0.9 on 104 .. 166. `flat` fires nowhere
   (rms = 0). Every frame's max is below tanh(10), the bound at lookback 100.
6. **Bad bars.** A NaN or +-inf close at bar 700 of `walk` moves 0 earlier
   bars, empties 113 bars (700 .. 812) and leaves the 687 after them firing;
   an infinity is bit-identical to a NaN without any mask.

Non-redundancy (synthetic, a disclosure, not Gate E): per-frame median
|rho| vs `CHOP_14_1_100` 0.7930 on these seven frames, `ER_10` 0.5462, `NATR_14`
0.3938, `J_DAMIANI_13_40` 0.3773, `BBB_5_2.0` 0.3302. Gate E is owed.

Every number above is printed by `python docs/measure_wavepm.py` on this
tree. Assertions are bounds and structural relations rather than the
digits, except where a digit IS the structure (the warm-up, the hole).
"""
from pathlib import Path

import numpy as np
import pytest
from pandas import DataFrame, Series, date_range

from .context import pandas_ta  # noqa: F401

import pandas_ta as ta
from pandas_ta.volatility.wavepm import wavepm

N = 1500
LEVEL = 100.0
LENGTH = 14
LOOKBACK = 100
WARMUP = LENGTH + LOOKBACK - 2
COLUMN = "WAVEPM_14_100"
OFFSETS = list(range(N - 36, N))
PLANT = 700


# ------------------------------------------------------------------ frames
# Same builders and seeds as `docs/measure_wavepm.py`.


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


def _c(frame):
    return frame[2]


def _scaled(frame, factor):
    return tuple(s * factor for s in frame)


def _bit_equal(a, b):
    if not bool((a.isna() == b.isna()).all()):
        return False
    m = a.notna()
    return bool((a[m] == b[m]).all())


def _maxdiff(a, b):
    m = a.notna() & b.notna()
    return float((a[m] - b[m]).abs().max())


def _spearman(a, b):
    m = a.notna() & b.notna()
    return float(a[m].corr(b[m], method="spearman"))


# ----------------------------------------------------------------- oracle


def _oracle(close, length=LENGTH, lookback=LOOKBACK, ddof=0, by_mean=True):
    """Issue #261's finta form by explicit loops: every window summed bar by
    bar. Shares no code with the module."""
    x = close.to_numpy(dtype=float)
    n = x.size
    r = np.full(n, np.nan)
    for t in range(length - 1, n):
        w = x[t - length + 1:t + 1]
        s = 0.0
        for v in w:
            s += v
        mu = s / length
        ss = 0.0
        for v in w:
            ss += (v - mu) * (v - mu)
        sd = (ss / (length - ddof)) ** 0.5
        r[t] = sd / mu if by_mean else sd
    out = np.full(n, np.nan)
    for t in range(length + lookback - 2, n):
        q = 0.0
        for k in range(t - lookback + 1, t + 1):
            q += r[k] * r[k]
        rms = (q / lookback) ** 0.5
        out[t] = np.tanh(r[t] / rms) if rms > 0 else np.nan
    return Series(out, index=close.index)


# ----------------------------------------------------------------- mutants

SOURCE = Path(__file__).resolve().parents[1] / "pandas_ta" / "volatility" \
    / "wavepm.py"

CAUSALITY_MUTANTS = [
    ("mean-lead", "    mu = close.rolling(length).mean()",
     "    mu = close.rolling(length).mean().shift(-1)"),
    ("std-lead", "    sigma = close.rolling(length).std(ddof=0)",
     "    sigma = close.rolling(length).std(ddof=0).shift(-1)"),
    ("rms-lead", "    rms = np.sqrt((r * r).rolling(lookback).mean())",
     "    rms = np.sqrt((r * r).rolling(lookback).mean()).shift(-1)"),
    ("output-early", "    # Offset\n    if offset != 0:",
     "    wpm = wpm.shift(-1)\n    # Offset\n    if offset != 0:"),
]


def _mutant(old, new):
    src = SOURCE.read_text(encoding="utf-8")
    assert src.count(old) == 1, f"{old!r} occurs {src.count(old)} times"
    ns = {}
    exec(compile(src.replace(old, new), "<mutant>", "exec"), ns)
    return ns["wavepm"]


def _futures(close, j, spread=3.0):
    """The close, and the close with bars >= j scaled UP by [1.5, 4] or DOWN
    by its reciprocal; all three agree bit for bit on bars < j."""
    rng = np.random.default_rng(90_001 + j)
    f = np.ones(close.size)
    f[j:] = 1.5 + (spread - 0.5) * rng.random(close.size)[j:]
    up, dn = Series(f, index=close.index), Series(1.0 / f, index=close.index)
    return close, close * up, close * dn


def _caught_at(fn, close, j):
    base, *others = _futures(close, j)
    a = fn(base).iloc[:j]
    return any(not _bit_equal(a, fn(o).iloc[:j]) for o in others)


def _sweep(fn, close, offsets=None):
    return sum(_caught_at(fn, close, j) for j in (offsets or OFFSETS))


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
    assert "wavepm" in ta.Category["volatility"]
    h, l, c = _walk()
    col = wavepm(c)
    assert col.name == COLUMN
    assert col.category == "volatility"
    df = DataFrame({"high": h, "low": l, "close": c})
    via = df.ta.wavepm()
    assert via.name == COLUMN
    assert _bit_equal(via, col)
    assert df.ta.wavepm(length=10, lookback=50).name == "WAVEPM_10_50"


def test_a_frame_shorter_than_the_window_is_refused():
    """`length + lookback - 1` = 113 bars is the shortest frame with one bar
    to judge; 112 is refused."""
    c = _c(_walk(n=200))
    assert wavepm(c.iloc[:WARMUP]) is None
    assert int(wavepm(c.iloc[:WARMUP + 1]).notna().sum()) == 1


def test_offset_and_fillna_do_what_the_kwargs_say():
    c = _c(_walk())
    base = wavepm(c)
    moved = wavepm(c, offset=2)
    m = base.shift(2).notna()
    assert bool((moved[m] == base.shift(2)[m]).all())
    assert int(wavepm(c, fillna=0.0).isna().sum()) == 0


# ------------------------------------------------------------------ Gate A


@pytest.mark.parametrize("name", NAMES)
def test_gate_a_matches_the_issue_formula_by_explicit_loops(name):
    """Identical NaN masks, values within 1e-9 (measured max 3.25e-11)."""
    c = _c(FRAMES[name]())
    col, orc = wavepm(c), _oracle(c)
    assert bool((col.isna() == orc.isna()).all())
    if col.notna().any():
        assert _maxdiff(col, orc) <= 1e-9


@pytest.mark.parametrize("length,lookback", [(5, 20), (20, 50), (30, 200)])
@pytest.mark.parametrize("name", ["walk", "coarse"])
def test_gate_a_holds_at_other_windows(name, length, lookback):
    """Measured max 3.15e-10, at (5, 20) on `walk`."""
    c = _c(FRAMES[name]())
    col = wavepm(c, length=length, lookback=lookback)
    orc = _oracle(c, length, lookback)
    assert col.name == f"WAVEPM_{length}_{lookback}"
    assert bool((col.isna() == orc.isna()).all())
    assert _maxdiff(col, orc) <= 1e-9


def test_gate_a_hand_frame():
    """length 2, lookback 2: r = |a - b| / (a + b), by hand."""
    idx = date_range("2020-01-01", periods=4, freq="h")
    col = wavepm(Series([1.0, 3.0, 3.0, 1.0], index=idx), length=2,
                 lookback=2)
    # r = [nan, 0.5, 0.0, 0.5]; rms at bar 2 = sqrt(0.125), bar 3 the same
    assert np.isnan(col.iloc[:2]).all()
    assert col.iloc[2] == 0.0
    assert abs(col.iloc[3] - np.tanh(0.5 / np.sqrt(0.125))) <= 1e-15


@pytest.mark.parametrize("name", MOVING)
def test_ddof_cancels_in_the_ratio(name):
    """Measured max |diff| 3.3e-16 .. 5.6e-16, ddof 0 vs ddof 1."""
    c = _c(FRAMES[name]())
    assert _maxdiff(_oracle(c), _oracle(c, ddof=1)) <= 1e-14


@pytest.mark.parametrize("name", MOVING)
def test_the_prorealcode_reading_is_a_different_column(name):
    """Without the division by the mean: max |diff| 0.0363 .. 0.0882,
    Spearman 0.9777 .. 0.9982 as measured."""
    c = _c(FRAMES[name]())
    col, alt = wavepm(c), _oracle(c, by_mean=False)
    assert _maxdiff(col, alt) > 0.01
    assert _spearman(col, alt) < 0.999


# ------------------------------------------------------------------ Gate B


@pytest.mark.parametrize("name", NAMES)
def test_gate_b_mutant_the_module_reads_no_future_bar(name):
    """0 of 36 tail offsets; §B of the measure script runs 0 of 1,499."""
    assert _sweep(wavepm, _c(FRAMES[name]())) == 0


def test_gate_b_mutant_the_module_reads_no_future_bar_at_any_offset():
    """Every bar but bar 0 of a 300-bar walk as a split point."""
    c = _c(_walk(n=300))
    assert _sweep(wavepm, c, list(range(1, 300))) == 0


@pytest.mark.parametrize("name", MOVING)
def test_gate_b_mutant_every_lookahead_edit_is_caught(name):
    """Measured 36 of 36 for every mutant on every moving frame."""
    c = _c(FRAMES[name]())
    caught = {label: _sweep(_mutant(old, new), c)
              for label, old, new in CAUSALITY_MUTANTS}
    assert all(v > 0 for v in caught.values()), caught


@pytest.mark.parametrize("label,old,new", CAUSALITY_MUTANTS,
                         ids=[m[0] for m in CAUSALITY_MUTANTS])
def test_gate_b_mutant_each_edit_is_live_against_the_module(label, old, new):
    """Each mutant moves 1,387 of 1,387 bars of unperturbed `walk`."""
    c = _c(_walk())
    base, mut = wavepm(c), _mutant(old, new)(c)
    m = base.notna() & mut.notna()
    assert int((base[m] != mut[m]).sum()) > 0


# ------------------------------------------------------------------ Gate C


@pytest.mark.parametrize("name", MOVING)
def test_gate_c_the_column_fires_and_is_not_constant(name):
    """1,388 of 1,500 fired: the warm-up is exactly length + lookback - 2.
    In [0, tanh(10)], above 0.5 and above 0.9 somewhere."""
    col = wavepm(_c(FRAMES[name]()))
    v = col.dropna()
    assert v.size == N - WARMUP
    assert bool(col.iloc[WARMUP:].notna().all())
    assert v.nunique() > 1000
    assert v.min() >= 0.0 and v.max() < np.tanh(10.0)
    assert 0 < int((v > 0.5).sum()) < v.size
    assert 0 < int((v > 0.9).sum()) < v.size


def test_a_window_of_one_price_reads_exactly_zero():
    """`coarse` (2.0 tick): 99 bars of 0.0, measured."""
    v = wavepm(_c(_coarse())).dropna()
    assert 0 < int((v == 0.0).sum()) < v.size


def test_a_flat_price_fires_nowhere():
    """rms = 0 on every bar of a flat price: NaN, not a division error."""
    assert int(wavepm(_c(_flat())).notna().sum()) == 0


def test_a_negative_price_mirrors_into_minus_one_zero():
    """Measured on the negated `walk`: [-0.9794, -0.2658], the exact
    negative of the positive column."""
    c = _c(_walk())
    assert _bit_equal(wavepm(-c), -wavepm(c))


# ------------------------------------------------------------------ Gate D


@pytest.mark.parametrize("name", NAMES)
@pytest.mark.parametrize("factor", [8, 64])
def test_gate_d_scale_is_bit_identical_under_exact_factors(name, factor):
    frame = FRAMES[name]()
    assert _bit_equal(wavepm(_c(frame)), wavepm(_c(_scaled(frame, factor))))


@pytest.mark.parametrize("name", NAMES)
@pytest.mark.parametrize("factor", [10.0, 3.7])
def test_gate_d_scale_survives_an_inexact_factor(name, factor):
    """NaN masks equal, values within 1e-9 (measured max 8.75e-11)."""
    frame = FRAMES[name]()
    a = wavepm(_c(frame))
    b = wavepm(_c(_scaled(frame, factor)))
    assert bool((a.isna() == b.isna()).all())
    fires = int(a.notna().sum())
    if name != "flat":
        assert 0 < fires < N
        assert _maxdiff(a, b) <= 1e-9


@pytest.mark.parametrize("level", [1e-6, 1e+6, 1e+100])
def test_gate_d_scale_at_extreme_price_levels(level):
    """Within 6.9e-11 of level 100, as measured; x8/x64 bit-identical."""
    frame = _walk(level=level)
    base = wavepm(_c(frame))
    assert int(base.notna().sum()) == N - WARMUP
    assert _maxdiff(base, wavepm(_c(_walk()))) <= 1e-9
    for factor in (8, 64):
        assert _bit_equal(base, wavepm(_c(_scaled(frame, factor))))


# ------------------------------------------------------- bad bars and edges


@pytest.mark.parametrize("value", [np.nan, np.inf, -np.inf])
def test_a_bad_close_moves_no_earlier_bar_and_leaves_a_fixed_hole(value):
    """Measured on `walk`: 0 earlier bars moved, 113 bars (700 .. 812)
    empty, the 687 after them fire; an infinity is bit-identical to a
    NaN."""
    c = _c(_walk())
    base = wavepm(c)
    x = c.copy()
    x.iloc[PLANT] = value
    out = wavepm(x)
    assert _bit_equal(base.iloc[:PLANT], out.iloc[:PLANT])
    hole = PLANT + LENGTH + LOOKBACK - 1
    assert bool(out.iloc[PLANT:hole].isna().all())
    assert bool(out.iloc[hole:].notna().all())
    y = c.copy()
    y.iloc[PLANT] = np.nan
    assert _bit_equal(out, wavepm(y))


@pytest.mark.parametrize("value", [np.nan, 0.0, -5.0, 100.0])
def test_a_degenerate_frame_raises_nothing_and_fires_nowhere(value):
    idx = date_range("2020-01-01", periods=300, freq="h")
    s = Series(np.full(300, value), index=idx)
    assert int(wavepm(s).notna().sum()) == 0


# ------------------------------------------------------------- docs


def test_the_docstrings_first_paragraph_survives_the_dictionary_cut():
    """131 characters as measured (§W), under the generator's 150."""
    body = []
    for line in wavepm.__doc__.splitlines()[1:]:
        if line.strip():
            body.append(line.strip())
        elif body:
            break
    paragraph = " ".join(body)
    assert len(paragraph) <= 150, len(paragraph)
    assert _generator_desc()({"desc": paragraph}) == paragraph
