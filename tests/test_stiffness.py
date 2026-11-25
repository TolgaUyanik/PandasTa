# -*- coding: utf-8 -*-
"""STIFFNESS-60: `stiffness`, Katsanos' Stiffness (PandasTa issue #259).

    MA[T]    = mean(close[T-99..T])                               SMA 100
    S[T]     = std(close[T-99..T], ddof=0)
    above[T] = 1 if close[T] > MA[T] + 0.2 * S[T] else 0
    STIFF[T] = 100 * (above[T-59] + ... + above[T]) / 60

WHAT THIS FILE PINS, in order of how much it would hurt to lose.

1. **Gate A against the issue's formula, spelled independently, with
   TA-Lib as the third speller.** A bar-by-bar oracle -- its own 100-term
   mean, its own two-pass population variance and its own 60-term count over
   plain Python floats, sharing no code with the module -- is **bit-equal**
   on **1,342 of 1,342** fired bars of each of all **nine** test frames,
   NaN masks identical. `talib.SMA + 0.2 * talib.STDDEV(nbdev=1)` (TA-Lib's
   STDDEV is the population one) is bit-equal on all nine too, and first
   fires at bar **158**, the module's `MIN_BARS - 1`. That test SKIPS where
   talib is absent rather than passing silently. ⚠ Katsanos' article was
   not readable when the issue was written and was not read here; what Gate
   A checks is the issue's formula.

2. **The readings a reader might substitute are other columns -- and the
   file says WHERE they differ, because it is not everywhere.** SD with
   `ddof=1` differs on **60** bars of **two** of the six varying frames
   (`coarse`, `jump`) and on **0** of the other four; `close >= band`
   differs ONLY on the flat frame, where every close sits exactly on its
   band (SD exactly 0) and the strict module reads **0** against `>=`'s
   **100**; jesse's lower band (`SMA - 0.2*std`) differs on **943 .. 1,342**
   bars of each of the six.

3. **Gate B is the sweep AND the oracle.** The module is caught at **0 of
   36** suffix offsets on each of six frames. Five look-ahead mutants are
   read off the shipped source, edited and `exec`'d in memory; each is live
   and caught on **5 .. 36 of 36** offsets of each of three frames, and the
   first catch moves a bar by at least one step, 100/60.
   ⚠ **The sweep's factor is x10, not the x1.03 `j_kaufmanstop_dist` uses,
   and its mutants lead the band by 10 bars, not 1.** This column is a
   COUNT: a look-ahead shows only when it flips a comparison, and a one-bar
   lead of the 100-bar SD is identical to the module on two of three swept
   frames before any perturbation (`docs/StiffnessMeasured.md` §B1 prints
   both one-bar leads beside the gate's five).
   ⚠ **The blind spot, pinned.** Two edits LAG a leg -- the close, the band.
   Neither reads a later bar, so the sweep catches **0 of 36**; Gate A's
   oracle rejects both on all three frames, by **1.667 .. 5.000**. The
   backward direction: truncating at bar 500 leaves all **842** bars from
   658 on bit-equal.

4. **Gates C and D.** Every frame fires on 1,342 of 1,500 bars. Over the
   six varying frames' **8,052** fired bars: **1,244** at 0, **605** at 100,
   **6,203** strictly between, every value a multiple of 100/60. x8/x64 is
   bit-identical on all nine frames at price levels 1e-6, 100, 1e6 and
   1e100 (**36** cells); x10/x3.7/x0.1/x1.0000001 move **0** bars in all
   **36** cells, asserted at 1e-9 with NaN masks matching; `0 < fires < n`
   on all nine.
   ⚠ **The column is translation-invariant as well as scale-invariant**, so
   the template's "a +10 level shift moves every bar" check would FAIL here
   for the right reason: it moves **0** bars of all nine frames. What keeps
   the bit-identity from being vacuous is a NON-affine transform:
   `close**2` moves **180 .. 372** bars and `log(close)` **43 .. 489** of
   each of the six varying frames.
   ⚠ Three frames are constant: `flat` reads exactly **0** on all 1,342;
   `rising` and `trend` (drift 0.003/bar) read exactly **100** on all
   1,342. So "not a constant column" is asserted on the six varying frames.

5. **A bad close empties a BOUNDED run and moves nothing else.** One NaN,
   +inf or -inf close blanks **159** bars when planted at bar 700 (100 for
   the band, 59 more for the count), **101** at bar 100, **6** at bar 5 and
   **5** at bar 1,495, and moves **0** other bars -- 12 cells. ⚠ The
   module's finite guard is a **measured no-op** in all 12: pandas' rolling
   window already reads an infinite observation as NaN.

6. **Gate E is OWED, not measured.** Contributors cannot run it; the row
   goes into `docs/gate_e_ledger.csv` when the owner runs it.
   `test_the_receipt_says_gate_e_is_pending` pins that the receipt does not
   claim a verdict. The in-fork synthetic overlap is a disclosure only: the
   nearest shipped column is `MADISP_200_SMA` at a per-frame median |rho|
   of **0.8099** over the six varying frames.

Every number above is printed by `python docs/measure_stiffness.py`, with
the exceptions `docs/StiffnessMeasured.md` lists (pytest's counts, the
repo's wiring counts, and this file's ASSERTED bounds: 1e-9 for the inexact
rescale, 100/60 for a mutant's catch).

NOT pinned here: Gate E (owed), and anything on real data -- every frame in
this file is synthetic.
"""
import importlib.util
from pathlib import Path

import numpy as np
import pytest
from pandas import DataFrame, Series, date_range

from .context import pandas_ta  # noqa: F401

import pandas_ta as ta
from pandas_ta.overlap.sma import sma
from pandas_ta.statistics.stdev import stdev
from pandas_ta.trend.stiffness import (LENGTH, MA_LENGTH, MIN_BARS, STD_MULT,
                                       stiffness)

ROOT = Path(__file__).resolve().parents[1]

N = 1500
LEVEL = 100.0
COLUMN = "STIFF_60"
WARMUP = MIN_BARS - 1
FIRED = N - WARMUP
OFFSETS = list(range(N - 36, N))
STEP = 100.0 / LENGTH
SWEEP_FACTOR = 10.0


# ------------------------------------------------------------------ frames
# Same builders and seeds as `docs/measure_stiffness.py`, so a number in
# this file and a number in the receipt are the same measurement.


def _idx(n):
    return date_range("2020-01-01", periods=n, freq="h")


def _walk(seed=7, n=N, level=LEVEL, sigma=0.01):
    rng = np.random.default_rng(seed)
    return Series(level * np.exp(np.cumsum(rng.normal(0.0, sigma, n))),
                  index=_idx(n))


def _trend(seed=11, n=N, level=LEVEL):
    rng = np.random.default_rng(seed)
    return Series(level * np.exp(np.cumsum(rng.normal(0.003, 0.008, n))),
                  index=_idx(n))


def _range_bound(seed=13, n=N, level=LEVEL):
    rng = np.random.default_rng(seed)
    x = np.zeros(n)
    for i in range(1, n):
        x[i] = 0.9 * x[i - 1] + rng.normal(0.0, 0.02)
    return Series(level * np.exp(x), index=_idx(n))


def _grid(seed=17, n=N, level=LEVEL, tick=0.01):
    return np.round(_walk(seed, n, level) / tick) * tick


def _coarse(seed=31, n=N, level=LEVEL, tick=0.5):
    return np.round(_walk(seed, n, level) / tick) * tick


def _heavy(seed=19, n=N, level=LEVEL):
    rng = np.random.default_rng(seed)
    return Series(level * np.exp(np.cumsum(rng.standard_t(2.0, n) * 0.006)),
                  index=_idx(n))


def _jump(seed=23, n=N, level=LEVEL):
    c = _walk(seed, n, level)
    return c * Series(np.where(np.arange(n) >= 700, 1.5, 1.0), index=c.index)


def _flat(n=N, level=LEVEL):
    return Series(np.full(n, level), index=_idx(n))


def _rising(n=N, level=LEVEL, step=0.001):
    return Series(level * (1.0 + step * np.arange(n)), index=_idx(n))


FRAMES = {
    "walk": _walk, "trend": _trend, "range-bound": _range_bound,
    "grid": _grid, "coarse": _coarse, "heavy-tailed": _heavy, "jump": _jump,
    "flat": _flat, "rising": _rising,
}
NAMES = list(FRAMES)
VARYING = ["walk", "range-bound", "grid", "coarse", "heavy-tailed", "jump"]
SWEPT = ["walk", "range-bound", "heavy-tailed"]


def _frame(name):
    return FRAMES[name]()


def _col(name):
    return stiffness(_frame(name))


# ---------------------------------------------------------------- helpers


def _bit_equal(a, b):
    if not bool((a.isna() == b.isna()).all()):
        return False
    m = a.notna() & b.notna()
    return bool((a[m].to_numpy() == b[m].to_numpy()).all())


def _abs(a, b):
    m = a.notna() & b.notna()
    return float((a[m] - b[m]).abs().max()) if int(m.sum()) else float("nan")


def _differing_bars(a, b):
    m = a.notna() & b.notna()
    return int((a[m].to_numpy() != b[m].to_numpy()).sum())


# ---------------------------------------------------------------- oracles


def _oracle(close):
    """The issue's formula bar by bar over plain Python floats."""
    c = close.to_numpy(dtype=float).tolist()
    n = len(c)
    nan = float("nan")
    above = [nan] * n
    for i in range(MA_LENGTH - 1, n):
        w = c[i - MA_LENGTH + 1:i + 1]
        if any(x != x for x in w):
            continue
        m = sum(w) / MA_LENGTH
        s = (sum((x - m) ** 2 for x in w) / MA_LENGTH) ** 0.5
        above[i] = 1.0 if c[i] > m + STD_MULT * s else 0.0
    out = [nan] * n
    for i in range(LENGTH - 1, n):
        w = above[i - LENGTH + 1:i + 1]
        if any(x != x for x in w):
            continue
        out[i] = 100.0 * sum(w) / LENGTH
    return Series(out, index=close.index)


def _alt(close, ddof=0, op="gt", sign=1.0):
    band = sma(close, MA_LENGTH) + sign * STD_MULT * stdev(close, MA_LENGTH,
                                                           ddof=ddof)
    hit = (close > band) if op == "gt" else (close >= band)
    above = hit.astype(float).where(band.notna())
    return 100.0 * above.rolling(LENGTH).sum() / LENGTH


def _talib():
    if importlib.util.find_spec("talib") is None:
        pytest.skip("talib is an optional dev dependency and is not installed")
    import talib
    return talib


# ---------------------------------------------------------------- mutants

SOURCE = ROOT / "pandas_ta" / "trend" / "stiffness.py"

MA_LINE = "    ma = sma(cl, length=MA_LENGTH)"
SD_LINE = "    sd = stdev(cl, length=MA_LENGTH, ddof=0)"
ABOVE_LINE = "    above = (cl > band).astype(float).where(band.notna() & cl.notna())"
COUNT_LINE = "    count = above.rolling(LENGTH, min_periods=LENGTH).sum()"
OUT_LINE = "    stiff = 100.0 * count / LENGTH"
GUARD_LINE = "    cl = cl.where(np.isfinite(cl))"

CAUSALITY_MUTANTS = [
    ("ma-lead-10", MA_LINE, "    ma = sma(cl.shift(-10), length=MA_LENGTH)"),
    ("sd-lead-10", SD_LINE,
     "    sd = stdev(cl.shift(-10), length=MA_LENGTH, ddof=0)"),
    ("close-lead", ABOVE_LINE,
     "    above = (cl.shift(-1) > band).astype(float).where(band.notna() & cl.notna())"),
    ("above-lead", COUNT_LINE,
     "    count = above.shift(-1).rolling(LENGTH, min_periods=LENGTH).sum()"),
    ("output-early", OUT_LINE,
     "    stiff = (100.0 * count / LENGTH).shift(-1)"),
]

BLIND_SPOT_MUTANTS = [
    ("close-lag", ABOVE_LINE,
     "    above = (cl.shift(1) > band).astype(float).where(band.notna() & cl.notna())"),
    ("band-lag", ABOVE_LINE,
     "    above = (cl > band.shift(1)).astype(float).where(band.notna() & cl.notna())"),
]


def _mutant(old, new):
    src = SOURCE.read_text(encoding="utf-8")
    assert src.count(old) == 1, f"{old!r} occurs {src.count(old)} times"
    ns = {}
    exec(compile(src.replace(old, new), "<mutant>", "exec"), ns)
    return ns["stiffness"]


def _caught_at(fn, close, j, factor=SWEEP_FACTOR):
    """Did rescaling every bar >= j move any bar < j? A SUFFIX rescale, not
    a global one -- the column is invariant under that (Gate D)."""
    f = Series(np.where(np.arange(close.size) >= j, factor, 1.0),
               index=close.index)
    return not _bit_equal(fn(close).iloc[:j], fn(close * f).iloc[:j])


def _sweep(fn, close):
    return sum(_caught_at(fn, close, j) for j in OFFSETS)


def _generator_desc():
    """`docs/gen_indicator_dictionary.py`'s own `desc`, lifted out with `ast`
    rather than re-typed, so the test pins the rule and not a copy."""
    import ast
    import re
    path = ROOT / "docs" / "gen_indicator_dictionary.py"
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
    assert "stiffness" in ta.Category["trend"]
    assert hasattr(ta.trend, "stiffness")
    close = _frame("walk")
    col = stiffness(close)
    assert col.name == COLUMN
    assert col.category == "trend"
    df = DataFrame({"close": close.to_numpy()})
    out = df.ta.stiffness()
    assert out.name == COLUMN
    assert out.equals(stiffness(close.reset_index(drop=True)))


def test_the_constants_are_the_issues_numbers():
    """"ma_length = 100, std_mult = 0.2, length = 60", and nothing else is
    configurable: the Gate E ledger refuses non-default parameters."""
    assert (MA_LENGTH, STD_MULT, LENGTH) == (100, 0.2, 60)
    assert COLUMN == f"STIFF_{LENGTH}"
    import inspect
    assert list(inspect.signature(stiffness).parameters) == \
        ["close", "offset", "kwargs"]


def test_min_bars_is_the_band_then_the_count():
    """100 closes for the first band, 59 more bands for the first count."""
    assert MIN_BARS == MA_LENGTH + LENGTH - 1 == 159
    assert int(_col("walk").notna().to_numpy().argmax()) == WARMUP == 158


def test_a_frame_shorter_than_min_bars_is_refused():
    close = _frame("walk")
    assert stiffness(close.iloc[:MIN_BARS - 1]) is None
    col = stiffness(close.iloc[:MIN_BARS])
    assert int(col.notna().sum()) == 1
    assert int(col.notna().to_numpy().argmax()) == MIN_BARS - 1


def test_offset_and_fillna():
    close = _frame("walk")
    base = stiffness(close)
    assert _bit_equal(stiffness(close, offset=2), base.shift(2))
    filled = stiffness(close, fillna=0.0)
    assert int(filled.isna().sum()) == 0
    assert float(filled.iloc[0]) == 0.0


# -------------------------------------------------------------- Gate A


@pytest.mark.parametrize("name", NAMES)
def test_gate_a_matches_the_issues_formula_spelled_independently(name):
    """Measured bit-equal on 1,342 of 1,342 fired bars of every frame. The
    output is a multiple of 100/60 built from 0/1 comparisons, so there is
    no last-bit drift to tolerate: a disagreement is a flipped comparison."""
    close = _frame(name)
    got, want = stiffness(close), _oracle(close)
    assert int(got.notna().sum()) == FIRED == 1342
    assert _bit_equal(got, want)


@pytest.mark.parametrize("name", NAMES)
def test_gate_a_matches_talibs_sma_and_population_stddev(name):
    """`talib.STDDEV` with `nbdev=1` is the population SD the issue names
    (ddof = 0). Measured bit-equal on all nine frames, first fired bar 158."""
    talib = _talib()
    close = _frame(name)
    x = close.to_numpy(dtype=float)
    band = Series(talib.SMA(x, timeperiod=MA_LENGTH)
                  + STD_MULT * talib.STDDEV(x, timeperiod=MA_LENGTH, nbdev=1),
                  index=close.index)
    above = (close > band).astype(float).where(band.notna())
    want = 100.0 * above.rolling(LENGTH).sum() / LENGTH
    assert int(want.notna().to_numpy().argmax()) == WARMUP
    assert _bit_equal(stiffness(close), want)


@pytest.mark.parametrize("name", VARYING)
def test_ddof_1_is_a_different_column_on_exactly_two_frames(name):
    """⚠ The issue's ddof = 0 is NOT `stdev`'s default. The ddof = 1 reading
    differs on 60 bars of `coarse` and of `jump` and on 0 of the other four
    -- so this pins where it bites rather than claiming it always does."""
    close = _frame(name)
    want = 60 if name in ("coarse", "jump") else 0
    assert _differing_bars(stiffness(close), _alt(close, ddof=1)) == want


@pytest.mark.parametrize("name", NAMES)
def test_the_strict_comparison_matters_only_on_an_exact_tie(name):
    """`close >= band` is a different column only where a close sits exactly
    on its band: the flat frame, where SD is exactly 0 and the band is the
    close. There the module reads 0 and `>=` reads 100; on the other eight
    frames the two are bit-equal."""
    close = _frame(name)
    got, ge = stiffness(close), _alt(close, op="ge")
    if name == "flat":
        assert set(got.dropna().unique()) == {0.0}
        assert set(ge.dropna().unique()) == {100.0}
    else:
        assert _bit_equal(got, ge)


@pytest.mark.parametrize("name", VARYING)
def test_jesses_lower_band_is_a_different_column(name):
    """jesse counts closes above `SMA - 0.2*std`; the owner chose the upper
    band. Measured 943 .. 1,342 bars differing on each of the six."""
    close = _frame(name)
    assert _differing_bars(stiffness(close), _alt(close, sign=-1.0)) >= 900


@pytest.mark.parametrize("name", NAMES)
def test_nothing_reads_a_bar_before_the_window(name):
    """The BACKWARD limb of causality: truncating at bar 500 leaves all 842
    bars from 658 on bit-equal."""
    close = _frame(name)
    tail = stiffness(close).iloc[500 + WARMUP:]
    cut = stiffness(close.iloc[500:]).iloc[WARMUP:]
    assert int(tail.notna().sum()) == N - 500 - WARMUP == 842
    assert _bit_equal(tail, cut)


# -------------------------------------------------------------- Gate B


@pytest.mark.parametrize("name", VARYING)
def test_the_module_is_never_caught_by_the_future_sweep(name):
    assert _sweep(stiffness, _frame(name)) == 0


@pytest.mark.parametrize("label,old,new", CAUSALITY_MUTANTS,
                         ids=[m[0] for m in CAUSALITY_MUTANTS])
@pytest.mark.parametrize("name", SWEPT)
def test_every_mutant_is_live_before_it_is_caught(label, old, new, name):
    """A mutant identical to the module would be caught at 0 offsets for the
    honest reason. Measured live on 92 .. 1,094 bars of each frame."""
    close = _frame(name)
    assert _differing_bars(stiffness(close), _mutant(old, new)(close)) > 0


@pytest.mark.parametrize("label,old,new", CAUSALITY_MUTANTS,
                         ids=[m[0] for m in CAUSALITY_MUTANTS])
@pytest.mark.parametrize("name", SWEPT)
def test_each_mutant_is_caught_by_the_future_sweep(label, old, new, name):
    """Measured 5 .. 36 of 36. Asserted "at least one"."""
    assert _sweep(_mutant(old, new), _frame(name)) >= 1


@pytest.mark.parametrize("label,old,new", CAUSALITY_MUTANTS,
                         ids=[m[0] for m in CAUSALITY_MUTANTS])
def test_each_mutant_is_caught_by_at_least_one_step(label, old, new):
    """A count column cannot move by a rounding accident: a catch is a whole
    flipped comparison, at least 100/60. Measured 1.6667 at the first caught
    offset on `walk` for all five."""
    fn = _mutant(old, new)
    close = _frame("walk")
    for j in OFFSETS:
        if _caught_at(fn, close, j):
            f = Series(np.where(np.arange(N) >= j, SWEEP_FACTOR, 1.0),
                       index=close.index)
            gap = _abs(fn(close).iloc[:j], fn(close * f).iloc[:j])
            assert gap >= STEP - 1e-9
            return
    pytest.fail(f"{label} was never caught")


@pytest.mark.parametrize("label,old,new", BLIND_SPOT_MUTANTS,
                         ids=[m[0] for m in BLIND_SPOT_MUTANTS])
@pytest.mark.parametrize("name", SWEPT)
def test_the_sweeps_blind_spot_is_pinned_and_the_oracle_covers_it(label, old,
                                                                  new, name):
    """Two edits that LAG a leg. Neither reads a later bar, so the sweep
    catches 0 of 36; the oracle rejects both on all three frames, by
    1.667 .. 5.000."""
    fn = _mutant(old, new)
    close = _frame(name)
    assert _sweep(fn, close) == 0
    assert _abs(fn(close), _oracle(close)) >= STEP - 1e-9


# ---------------------------------------------------------- Gates C and D


@pytest.mark.parametrize("name", VARYING)
def test_reachability_on_the_varying_frames(name):
    """Fires on 1,342 of 1,500; 52 .. 61 distinct values; every one a
    multiple of 100/60 inside [0, 100]."""
    col = _col(name)
    assert int(col.notna().sum()) == FIRED
    assert bool(col.iloc[:WARMUP].isna().all())
    v = col.dropna()
    assert int(v.nunique()) >= 50
    assert bool(((v >= 0.0) & (v <= 100.0)).all())
    assert np.allclose(v / STEP, np.round(v / STEP))


def test_reachability_counts_pooled_over_the_varying_frames():
    """Both bounds are reached, and most bars are strictly between."""
    pooled = Series(np.concatenate([_col(n).dropna().to_numpy()
                                    for n in VARYING]))
    assert len(pooled) == 8052
    assert int((pooled == 0.0).sum()) == 1244
    assert int((pooled == 100.0).sum()) == 605
    assert int(((pooled > 0.0) & (pooled < 100.0)).sum()) == 6203


@pytest.mark.parametrize("name,value", [("flat", 0.0), ("rising", 100.0),
                                        ("trend", 100.0)])
def test_the_three_constant_frames(name, value):
    """⚠ The exceptions to "not a constant column": a flat close sits ON its
    band and the comparison is strict, so 0; a rising frame and a 0.003/bar
    drift stay above the padded mean, so 100."""
    col = _col(name)
    assert int(col.notna().sum()) == FIRED
    assert set(col.dropna().unique()) == {value}


@pytest.mark.parametrize("factor", [8.0, 64.0])
@pytest.mark.parametrize("level", [LEVEL, 1e-6, 1e6, 1e100])
@pytest.mark.parametrize("name", NAMES)
def test_gate_d_scale_x8_x64_is_bit_identical(name, level, factor):
    """All nine frames at all four price levels, both factors: 36 cells."""
    close = _frame(name) / LEVEL * level
    base = stiffness(close)
    assert int(base.notna().sum()) == FIRED
    assert _bit_equal(base, stiffness(close * factor))


@pytest.mark.parametrize("factor", [10.0, 3.7, 0.1, 1.0000001])
@pytest.mark.parametrize("name", NAMES)
def test_gate_d_scale_tolerance_for_inexact_factors(name, factor):
    """Measured 0 bars differing in all 36 cells; asserted as a tolerance
    with matching NaN masks, because an inexact rescale could in principle
    flip a comparison that sits within an ulp of its band."""
    close = _frame(name)
    base, moved = stiffness(close), stiffness(close * factor)
    assert bool((base.isna() == moved.isna()).all())
    assert _abs(base, moved) < 1e-9


@pytest.mark.parametrize("name", NAMES)
def test_gate_d_scale_fires_are_strictly_between_zero_and_n(name):
    col = _col(name)
    assert 0 < int(col.notna().sum()) < len(col)


@pytest.mark.parametrize("name", NAMES)
def test_gate_d_scale_a_level_shift_moves_nothing(name):
    """⚠ Unlike `j_kaufmanstop_dist`, this column is translation-invariant
    too: close, MA and 0.2*S all move together under `close + b`. Measured
    0 bars moved by +10 on all nine frames."""
    close = _frame(name)
    assert _bit_equal(stiffness(close), stiffness(close + 10.0))


@pytest.mark.parametrize("name", VARYING)
def test_gate_d_scale_identity_is_not_vacuous(name):
    """What DOES move the column is a non-affine transform: `close**2`
    moves 180 .. 372 bars and `log(close)` 43 .. 489 of each of the six."""
    close = _frame(name)
    base = stiffness(close)
    assert _differing_bars(base, stiffness(close ** 2)) >= 100
    assert _differing_bars(base, stiffness(np.log(close))) >= 40


# ---------------------------------------------------------------- guards


@pytest.mark.parametrize("j,blanked", [(5, 6), (100, 101), (700, 159),
                                       (1495, 5)])
@pytest.mark.parametrize("value", [np.nan, np.inf, -np.inf])
def test_a_bad_close_empties_a_bounded_run_and_moves_nothing(value, j,
                                                             blanked):
    close = _frame("walk")
    bad = close.copy()
    bad.iloc[j] = value
    base, out = stiffness(close), stiffness(bad)
    assert int((base.notna() & out.isna()).sum()) == blanked
    assert _differing_bars(base, out) == 0
    assert int(np.isinf(out).sum()) == 0


@pytest.mark.parametrize("j", [5, 100, 700, 1495])
@pytest.mark.parametrize("value", [np.nan, np.inf, -np.inf])
def test_the_finite_guard_is_a_measured_no_op(value, j):
    """⚠ The module's comment says so; this keeps it honest. Pandas' rolling
    window already reads an infinite close as NaN."""
    bad = _frame("walk").copy()
    bad.iloc[j] = value
    assert _bit_equal(stiffness(bad), _mutant(GUARD_LINE, "    pass")(bad))


def test_an_all_nan_frame_is_empty_rather_than_an_error():
    s = Series(np.full(200, np.nan), index=_idx(200))
    col = stiffness(s)
    assert col is not None
    assert int(col.notna().sum()) == 0
    assert col.name == COLUMN


# -------------------------------------------------- documentation surface


def test_the_docstrings_first_paragraph_survives_the_dictionary_cut():
    doc = stiffness.__doc__.splitlines()
    body = []
    for line in doc[1:]:
        s = line.strip()
        if s:
            body.append(s)
        elif body:
            break
    full = " ".join(body)
    cut = _generator_desc()({"desc": full})
    assert "…" not in cut
    assert cut == full
    assert "100-bar SMA" in cut


def test_the_receipt_says_gate_e_is_pending():
    """Gate E is owed: the receipt must say so and must not claim a band."""
    doc = (ROOT / "docs" / "StiffnessMeasured.md").read_text(encoding="utf-8")
    assert "Gate E: pending, run by issue-solver after this session" in doc
    assert "0.8099" in doc            # the synthetic disclosure, §L
    assert "MADISP_200_SMA" in doc
