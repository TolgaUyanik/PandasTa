# -*- coding: utf-8 -*-
"""J-GATOR: `j_gator`, Bill Williams' gator oscillator over close
(PandasTa issue #104).

    mid     = (high + low) / 2
    jaw     = SMMA(mid, 13) displaced 8 bars
    teeth   = SMMA(mid, 8)  displaced 5 bars
    lips    = SMMA(mid, 5)  displaced 3 bars
    J_GATOR = (|jaw - teeth| - |teeth - lips|) / close

WHAT THIS FILE PINS, in order of how much it would hurt to lose.

1. **Gate A against the issue's formula, spelled independently.** A
   hand-written recursion with hand-written lags, sharing no code with the
   module, agrees on **1,492 of 1,492** fired bars of each of seven frames
   (10,444 pooled) with identical NaN masks -- measured BIT-equal here,
   asserted as a relative bound of 1e-12 because the two spellings are not
   obliged to round the same way and a reduced-kernel run may not. The
   screen prototype, which shares pandas' `ewm`, is asserted bit-equal:
   same operations in the same order, so that one is machine-independent.
   ⚠ jesse is NOT installed here and web access is unavailable
   (`test_the_source_library_is_not_installed_here` records it, so the
   claim cannot rot into "checked against jesse"). What Gate A checks is
   the formula issue #104 quotes.

2. **THE TEETH CANCEL whenever they are the outer line, and that is the
   one structural thing to know about this column.** If the teeth sit
   above (or below) both the jaw and the lips, then
   `|jaw - teeth| - |teeth - lips|` is `±(lips - jaw)` and the teeth are
   not read at all -- the gator oscillator is the jaw-lips spread there.
   Measured on **0.0355** (trend) to **0.2815** (range-bound) of fired
   bars, bit-equal to the signed jaw-lips spread on every one of them.

3. **Gate B, and it is the teeth that make it interesting.** Five
   look-ahead mutants are read off the shipped module's source, edited,
   and `exec`'d in memory. The module itself is caught at **0 of 36**
   perturbation offsets on every frame; `jaw-lead`, `lips-lead`,
   `output-early` and `divisor-lead` at **36 of 36** on all six. The
   `teeth-lead` mutant is caught at only **5 to 30 of 36**, and that is
   item 2 and not a weakness in the mutant: a future-reading teeth is the
   OUTER line on 0.6779 to 0.9085 of bars, where it cancels. So the
   mutant is carried by its liveness (1,371 to 1,453 of ~1,487 bars moved)
   plus a mechanism-aware sweep: every offset the cancellation leaves
   exposed is caught -- 95 of 95 pooled over the six frames.

4. **Gate D.** `x8`/`x64` are bit-identical on 1,492 of 1,492 bars of each
   of seven frames and at price levels 1e-6, 1e+6 and 1e+100: every
   operation scales by an exact power of two and the final division
   cancels it. `x10`, `x3.7`, `x0.1` and `x1.0000001` are not exact and
   are asserted as a relative bound (measured max **6.480e-10**, asserted
   1e-7) with NaN masks matching -- the column is a difference of two
   small spreads, so cancellation amplifies the last bits by orders of
   magnitude more than the inputs lose.

5. **The warm-up is the LAG and nothing else.** The EWMA is seeded at bar
   0, so the column fires from bar **8** -- `JAW`'s lag, the longest --
   and on 1,492 of 1,500 bars of every frame. `MIN_BARS` = 21 is a floor
   on the INPUT, not the warm-up: a 20-bar frame returns `None` and a
   21-bar frame fires on 13 bars.

6. **WHICH SMMA, decided and priced -- and the alpha is the part that
   matters.** "SMMA" is read as Wilder's `alpha = 1/length` with
   `adjust=False`, seeded at the first value: the prototype's spelling.
   ⚠ jesse's own smoother is NOT read (see item 1), so the reading rests
   on the issue's wording and on the prototype Gate E measured. The SEED
   is a warm-up difference: against the SMA-seeded reading, max |diff|
   falls from 1.9e-3 at bar 8 to 2.0e-9 by bar 200 and 4.4e-16 by bar
   400 of a 1,500-bar frame, Spearman 0.9976 to 0.9998; against `rma`
   (pandas' default `adjust=True`), 0.9932 to 0.9991. The ALPHA is not:
   read as a plain EMA (`alpha = 2/(n+1)`) the same formula is a
   different column -- Spearman **0.5165 to 0.7075**, 0 bars in common,
   max |diff| 2.5e-2 to 7.2e-2.

7. **The guards, and the one case nothing guards.** A bad close empties
   its own bar and no other (NaN, 0.0, -1.0, ±inf, 1e-310 -- 1 bar each,
   0 other bars moved), which is what the guard buys: unguarded, a zero
   or subnormal close reads `inf` and a NEGATIVE close reads a
   plausible-looking -0.4778. An infinite high OR LOW needs no guard here
   and that is measured, not assumed: pandas turns it into a NaN before
   the `ewm` kernel, so an inf bar and a NaN bar are bit-identical columns
   with 0 non-finite readings, on both legs and both signs. A bad mid IS
   recursive: bars before it stay bit-identical and the contamination
   decays with the filter's memory (max |rel| 2.44 at the bar, 1.2e-1 by
   +50, 1.6e-3 by +100, 1.5e-10 by +300 -- the same six figures for a bad
   high and a bad low, `mid` being their mean). ⚠ NOT guarded: a frame whose high/low and close live hundreds of
   orders of magnitude apart overflows the division (52 of 60 bars
   infinite) -- bad data rather than a price, and pinned so the
   disclosure cannot rot.

8. **Gate E is OWED.** `test_the_gate_e_row_is_owed` asserts the ledger has
   NO row for this indicator, which is what
   `tests/test_gate_e_ledger.py` reports as owed and what the receipt
   session replaces with the measured row. Gate C's real-data counts come
   from the same run.

Every number above is printed by `python docs/measure_j_gator.py` on this
worktree (pandas 2.3.3, numpy 1.26.4), and
`python docs/measure_j_gator_cpu.py` re-runs this module -- and any named
section -- under numpy's `AVX512F AVX512_SKX AVX2 FMA3` dispatch disabled.
The full receipt is `docs/JGatorMeasured.md`.

NOT pinned here: Gate E itself (the launcher's run; 687 comparators over 89
real BIST frames) and Gate C's real-data limb, which comes with it. The
in-fork overlap figures of §L are SYNTHETIC and are disclosures, not gates.
"""
import csv
import importlib.util
from pathlib import Path

import numpy as np
import pytest
from pandas import DataFrame, Series, concat, date_range

from .context import pandas_ta  # noqa: F401

import pandas_ta as ta
from pandas_ta.momentum.j_gator import JAW, LIPS, MIN_BARS, TEETH, j_gator

N = 1500
LEVEL = 100.0
COLUMN = "J_GATOR_13_8_5"
#: The column's only NaNs on a clean frame: the longest lag.
WARMUP = JAW[1]
FIRED = N - WARMUP
#: The blind causality sweep's 36 perturbation points.
OFFSETS = list(range(N - 36, N))


# ------------------------------------------------------------------ frames
# Same builders and seeds as `docs/measure_j_gator.py`, so a number in this
# file and a number in the receipt are the same measurement.


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


FRAMES = {
    "walk": _walk, "trend": _trend, "range-bound": _range_bound,
    "grid": _grid, "heavy-tailed": _heavy, "jump": _jump, "flat": _flat,
}
NAMES = list(FRAMES)
VARYING = [n for n in NAMES if n != "flat"]


def _scaled(frame, factor):
    h, l, c = frame
    return h * factor, l * factor, c * factor


def _rel(a, b):
    """Max relative difference over the bars both fire on."""
    m = a.notna() & b.notna()
    if not int(m.sum()):
        return float("nan")
    d = (a[m] - b[m]).abs()
    scale = b[m].abs().where(b[m].abs() > 0.0, np.nan)
    rel = (d / scale).max()
    return 0.0 if np.isnan(rel) else float(rel)


def _spearman(a, b):
    m = a.notna() & b.notna()
    if int(m.sum()) < 3 or a[m].nunique() < 2 or b[m].nunique() < 2:
        return float("nan")
    return float(a[m].corr(b[m], method="spearman"))


def _lines(frame, teeth_lag=TEETH[1]):
    h, l, c = frame
    mid = (h + l) / 2
    return (mid.ewm(alpha=1 / JAW[0], adjust=False).mean().shift(JAW[1]),
            mid.ewm(alpha=1 / TEETH[0], adjust=False).mean().shift(teeth_lag),
            mid.ewm(alpha=1 / LIPS[0], adjust=False).mean().shift(LIPS[1]))


# ----------------------------------------------------------------- oracles


def _smma_recursion(x, length, lag):
    a = 1.0 / length
    s = np.empty(x.size)
    s[0] = x[0]
    for i in range(1, x.size):
        s[i] = (1.0 - a) * s[i - 1] + a * x[i]
    out = np.full(x.size, np.nan)
    out[lag:] = s[: x.size - lag]
    return out


def _oracle(high, low, close):
    """The issue's formula, sharing no code with the module."""
    mid = (high.to_numpy(dtype=float) + low.to_numpy(dtype=float)) / 2
    jaw = _smma_recursion(mid, *JAW)
    teeth = _smma_recursion(mid, *TEETH)
    lips = _smma_recursion(mid, *LIPS)
    val = np.abs(jaw - teeth) - np.abs(teeth - lips)
    return Series(val / close.to_numpy(dtype=float), index=close.index)


def _prototype(high, low, close):
    """`docs/issues/screen/ind_screen.py`, candidate `j_gator`, retyped
    (that file is gitignored, so it is on the owner's machine only)."""
    mid = (high + low) / 2
    sm = lambda n: mid.ewm(alpha=1 / n, adjust=False).mean()  # noqa: E731
    jaw, teeth, lips = sm(13).shift(8), sm(8).shift(5), sm(5).shift(3)
    return ((jaw - teeth).abs() - (teeth - lips).abs()) / close


def _sma_seeded(x, length, lag):
    """The OTHER SMMA: seeded with `SMA(x[:length])`."""
    a = 1.0 / length
    s = np.full(x.size, np.nan)
    s[length - 1] = x[:length].mean()
    for i in range(length, x.size):
        s[i] = (1.0 - a) * s[i - 1] + a * x[i]
    out = np.full(x.size, np.nan)
    out[lag:] = s[: x.size - lag]
    return out


def _sma_seeded_column(high, low, close):
    mid = (high.to_numpy(dtype=float) + low.to_numpy(dtype=float)) / 2
    val = (np.abs(_sma_seeded(mid, *JAW) - _sma_seeded(mid, *TEETH))
           - np.abs(_sma_seeded(mid, *TEETH) - _sma_seeded(mid, *LIPS)))
    return Series(val / close.to_numpy(dtype=float), index=close.index)


# ----------------------------------------------------------------- mutants

SOURCE = Path(__file__).resolve().parents[1] / "pandas_ta" / "momentum" \
    / "j_gator.py"

#: (label, old text, new text). Edits to the SHIPPED source, read off disk.
CAUSALITY_MUTANTS = [
    ("jaw-lead", "JAW = (13, 8)", "JAW = (13, -8)"),
    ("teeth-lead", "TEETH = (8, 5)", "TEETH = (8, -5)"),
    ("lips-lead", "LIPS = (5, 3)", "LIPS = (5, -3)"),
    ("output-early",
     "    gator = ((jaw - teeth).abs() - (teeth - lips).abs()) / c",
     "    gator = (((jaw - teeth).abs() - (teeth - lips).abs())"
     " / c).shift(-1)"),
    ("divisor-lead", ".abs()) / c", ".abs()) / c.shift(-1)"),
]
#: Not a causality mutant: the close guard, removed, to price what it buys.
CLOSE_GUARD_OFF = (
    "c = close.where(np.isfinite(close) & (close >= np.finfo(float).tiny))",
    "c = close")


def _mutant(old, new):
    src = SOURCE.read_text(encoding="utf-8")
    assert src.count(old) == 1, f"{old!r} occurs {src.count(old)} times"
    ns = {}
    exec(compile(src.replace(old, new), "<mutant>", "exec"), ns)
    return ns["j_gator"]


def _generator_desc():
    """`docs/gen_indicator_dictionary.py`'s own `desc`, lifted out of its
    source with `ast` and compiled alone.

    Importing that module runs its whole 345-indicator probe, which is far
    too slow for a unit test -- and re-typing the cut here would pin a COPY
    of the rule rather than the rule. This compiles the generator's actual
    function, so a change to its cut reaches this test."""
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


def _caught_at(fn, frame, j, factor=1.03):
    """Did perturbing every bar >= j move any bar < j?"""
    h, l, c = frame
    f = Series(np.where(np.arange(c.size) >= j, factor, 1.0), index=c.index)
    a = fn(h, l, c).iloc[:j]
    b = fn(h * f, l * f, c * f).iloc[:j]
    if not bool((a.isna() == b.isna()).all()):
        return True
    m = a.notna() & b.notna()
    return not bool((a[m] == b[m]).all())


def _sweep(fn, frame, offsets=None):
    return sum(_caught_at(fn, frame, j) for j in (offsets or OFFSETS))


# -------------------------------------------------- wiring and arguments


def test_name_registration_and_accessor():
    """The five wiring touch points, through the three call styles."""
    assert "j_gator" in ta.Category["momentum"]
    frame = _walk()
    col = j_gator(*frame)
    assert col.name == COLUMN
    assert col.category == "momentum"

    h, l, c = frame
    df = DataFrame({"high": h, "low": l, "close": c})
    assert hasattr(df.ta, "j_gator")
    via_accessor = df.ta.j_gator()
    assert via_accessor.name == COLUMN
    assert bool((via_accessor.dropna() == col.dropna()).all())


def test_the_source_library_is_not_installed_here():
    """Gate A is the issue's quoted formula, spelled two ways -- not a run
    of jesse. Pinned so the claim cannot rot into "checked against jesse"
    if the dependency ever appears."""
    assert importlib.util.find_spec("jesse") is None


def test_a_frame_shorter_than_min_bars_is_refused():
    """`MIN_BARS` is a floor on the INPUT (the longest length plus its
    lag), not the warm-up: one bar less and the function declines; at
    exactly `MIN_BARS` it fires on `MIN_BARS - WARMUP` = 13 bars."""
    h, l, c = _walk()
    assert MIN_BARS == JAW[0] + JAW[1] == 21
    short = MIN_BARS - 1
    assert j_gator(h.iloc[:short], l.iloc[:short], c.iloc[:short]) is None
    ok = j_gator(h.iloc[:MIN_BARS], l.iloc[:MIN_BARS], c.iloc[:MIN_BARS])
    assert int(ok.notna().sum()) == MIN_BARS - WARMUP == 13


def test_offset_and_fillna():
    frame = _walk()
    base = j_gator(*frame)
    moved = j_gator(*frame, offset=2)
    assert bool((moved.iloc[2:].dropna()
                 == base.iloc[:-2].dropna().to_numpy()).all())
    filled = j_gator(*frame, fillna=0.0)
    assert int(filled.isna().sum()) == 0
    assert int((filled.iloc[:WARMUP] == 0.0).sum()) == WARMUP


# ------------------------------------------------------------------ Gate A


@pytest.mark.parametrize("name", NAMES)
def test_gate_a_matches_the_issues_formula_spelled_independently(name):
    """A hand-written recursion with hand-written lags, against the module,
    on 1,492 of 1,492 fired bars with identical NaN masks.

    Measured BIT-equal on all seven frames here (max |diff| 0.0), asserted
    as a bound instead: the two spellings compute `(1-a)*s + a*x` through
    different code and are not obliged to round identically, so pinning
    bit-equality would pin this machine's kernels.

    ⚠ BOTH an absolute and a relative bound, because either alone has a
    hole. The relative one is vacuous on the `flat` frame, where the
    oracle is identically 0.0 and `_rel` has nothing to divide by (§A1
    prints `nan` in that cell); the absolute one is the weaker test
    elsewhere, since the column's own max |value| is 2.4e-02 to 1.2e-01.
    """
    frame = FRAMES[name]()
    col, oracle = j_gator(*frame), _oracle(*frame)
    assert bool((col.isna() == oracle.isna()).all())
    assert int(col.notna().sum()) == FIRED
    m = col.notna() & oracle.notna()
    assert int(m.sum()) == FIRED
    assert float((col[m] - oracle[m]).abs().max()) <= 1e-12
    assert _rel(col, oracle) <= 1e-12, _rel(col, oracle)


@pytest.mark.parametrize("name", NAMES)
def test_gate_a_is_bit_equal_to_the_screen_prototype(name):
    """The prototype and the module perform the SAME operations in the same
    order (pandas' `ewm`), so bit-equality here is machine-independent and
    is asserted as such. This is the limb that ties this port to the
    2026-10-24 screen's Gate E figures."""
    frame = FRAMES[name]()
    col, proto = j_gator(*frame), _prototype(*frame)
    assert bool((col.isna() == proto.isna()).all())
    m = col.notna()
    assert int(m.sum()) == FIRED
    assert bool((col[m] == proto[m]).all())


@pytest.mark.parametrize("name", VARYING)
def test_the_teeth_cancel_when_they_are_the_outer_line(name):
    """The column's one structural surprise: when the teeth sit above (or
    below) BOTH other lines, `|jaw-teeth| - |teeth-lips|` reduces to
    `±(lips - jaw)` and the teeth are not read at all.

    Measured on 0.0355 (trend) to 0.2815 (range-bound) of fired bars, and
    bit-equal to the signed jaw-lips spread on each of them. Pinned as a
    bound rather than a share per frame: the frames are built with
    `np.exp`, so which bars qualify moves in the last bits, while the
    identity itself does not. This is also why Gate B's `teeth-lead`
    mutant is caught at 5 of 36 offsets on a trending frame.
    """
    frame = FRAMES[name]()
    h, l, c = frame
    jaw, teeth, lips = _lines(frame)
    col = j_gator(*frame)
    pair = concat([jaw, lips], axis=1)
    up = teeth >= pair.max(axis=1)
    outer = (up | (teeth <= pair.min(axis=1))) & col.notna()
    share = int(outer.sum()) / int(col.notna().sum())
    assert 0.01 < share < 0.50, share
    ident = Series(np.where(up, 1.0, -1.0), index=col.index) * (lips - jaw) / c
    assert _rel(col[outer], ident[outer]) <= 1e-12


def test_the_lag_reads_backwards_and_the_warmup_is_the_longest_lag():
    """A line "displaced 8 bars forward" on a chart is, for the value at
    bar T, the smoothed value of bar T - 8. Checked against an explicit
    index walk, and the column's NaNs are exactly that longest lag."""
    frame = _walk()
    h, l, c = frame
    mid = (h + l) / 2
    for length, lag in (JAW, TEETH, LIPS):
        line = mid.ewm(alpha=1.0 / length, adjust=False).mean()
        shifted = line.shift(lag)
        assert int(shifted.isna().sum()) == lag
        assert all(shifted.iloc[t] == line.iloc[t - lag]
                   for t in range(lag, mid.size))
    col = j_gator(*frame)
    assert int(col.isna().sum()) == WARMUP == 8
    assert int(col.notna().to_numpy().argmax()) == WARMUP
    assert int(col.notna().sum()) == FIRED


@pytest.mark.parametrize("name", VARYING)
def test_the_seed_is_the_first_value_and_the_difference_is_a_warmup(name):
    """The SMMA is seeded at the first value, not with `SMA(x[:length])`.

    The two readings are a different column early and the same column
    late: on the walk, max |diff| falls 1.9e-3 (bar 8) -> 2.0e-9 (bar 200)
    -> 4.4e-16 (bar 400), with Spearman 0.9976 .. 0.9998 per frame.
    Asserted as that shape -- different somewhere before bar 50, agreeing
    ABSOLUTELY to 1e-12 from bar 400 -- rather than as digits.

    ⚠ Absolutely, not relatively, and the difference matters: the column
    passes through zero, so a residue of 4e-16 on a bar reading 1e-5 is a
    RELATIVE 4e-11. The bound that means something here is the one against
    the column's own magnitude (max |value| ~2.4e-2 on the walk).
    """
    frame = FRAMES[name]()
    col, other = j_gator(*frame), _sma_seeded_column(*frame)
    m = col.notna() & other.notna()
    early = m & (np.arange(col.size) < 50)
    assert int((col[early] != other[early]).sum()) > 0
    late = m & (np.arange(col.size) >= 400)
    assert float((col[late] - other[late]).abs().max()) <= 1e-12
    assert _spearman(col, other) > 0.99


@pytest.mark.parametrize("name", VARYING)
def test_the_forks_rma_would_be_a_different_column(name):
    """`rma` is pandas' `ewm` at its DEFAULT `adjust=True` with
    `min_periods=length`, which is a third reading of "SMMA". It is
    nearly rank-identical (0.9932 .. 0.9991 measured) and NOT the same
    column -- asserted as "not all bars equal", never as a count, since
    how many bars coincide is a last-bits question."""
    from pandas_ta.overlap.rma import rma
    frame = FRAMES[name]()
    h, l, c = frame
    mid = (h + l) / 2
    other = ((rma(mid, JAW[0]).shift(JAW[1])
              - rma(mid, TEETH[0]).shift(TEETH[1])).abs()
             - (rma(mid, TEETH[0]).shift(TEETH[1])
                - rma(mid, LIPS[0]).shift(LIPS[1])).abs()) / c
    col = j_gator(*frame)
    m = col.notna() & other.notna()
    assert int((col[m] != other[m]).sum()) > 0
    assert _spearman(col, other) > 0.98


@pytest.mark.parametrize("name", VARYING)
def test_the_plain_ema_reading_would_be_a_different_column(name):
    """The SEED readings of "SMMA" are warm-up differences; the ALPHA is
    not. Read as a plain EMA -- `alpha = 2/(n+1)`, i.e.
    `ewm(span=n, adjust=False)`, holding `adjust` fixed so the alpha is
    the only change -- the same formula is a different column: 0.5165 ..
    0.7075 and 0 bars in common over the six varying frames, against the
    SMA-seeded variant's 0.9976 .. 0.9998.

    This is the load-bearing half of §A4, because the reading rests on the
    issue's word "SMMA" and on the prototype -- NOT on jesse's source,
    which this worktree cannot read. Asserted as bands, not as the 0:
    how many bars of two independent smoothers coincide is a last-bits
    question."""
    frame = FRAMES[name]()
    h, l, c = frame
    mid = (h + l) / 2

    def line(length, lag):
        return mid.ewm(span=length, adjust=False).mean().shift(lag)

    jaw, teeth, lips = line(*JAW), line(*TEETH), line(*LIPS)
    other = ((jaw - teeth).abs() - (teeth - lips).abs()) / c
    col = j_gator(*frame)
    m = col.notna() & other.notna()
    assert int(m.sum()) == FIRED
    assert int((col[m] == other[m]).sum()) < 0.01 * FIRED
    assert float((col[m] - other[m]).abs().max()) > 1e-3
    assert 0.40 < _spearman(col, other) < 0.80


# ------------------------------------------------------- Gate B (mutants)


@pytest.mark.parametrize("name", VARYING)
def test_the_module_is_never_caught_by_the_future_sweep(name):
    """36 offsets, every bar >= J multiplied by 1.03: no bar < J may move.
    Measured 0 of 36 on each of the six varying frames."""
    assert _sweep(j_gator, FRAMES[name]()) == 0


@pytest.mark.parametrize("label,old,new", CAUSALITY_MUTANTS)
def test_every_mutant_is_live_before_it_is_caught(label, old, new):
    """A mutant that is not live proves nothing, so liveness comes first.
    Measured, per mutant and over the six varying frames: 1,484 of 1,484
    (jaw-lead), 1,371 .. 1,453 of 1,487 (teeth-lead), 1,489 of 1,489
    (lips-lead), 1,491 of 1,491 (output-early) and 1,485 .. 1,491 of
    1,491 (divisor-lead) -- each mutant has its own shared count, because
    each one's `shift` NaNs a different number of tail bars. Asserted as
    "more than half the shared bars move", which is the floor all five
    clear by a wide margin."""
    fn = _mutant(old, new)
    for name in VARYING:
        frame = FRAMES[name]()
        base, mut = j_gator(*frame), fn(*frame)
        m = base.notna() & mut.notna()
        assert int(m.sum()) > 0, f"{label}/{name}: mutant fires nowhere"
        moved = int((base[m] != mut[m]).sum())
        assert moved > 0.5 * int(m.sum()), f"{label}/{name}: {moved} moved"


@pytest.mark.parametrize("label,old,new",
                         [m for m in CAUSALITY_MUTANTS
                          if m[0] != "teeth-lead"])
def test_each_mutant_is_caught_by_the_future_sweep(label, old, new):
    """Four of the five are caught at 36 of 36 offsets on every frame.
    Asserted as "every offset", because each of these four moves a bar
    whose value the perturbation definitely enters."""
    fn = _mutant(old, new)
    for name in VARYING:
        caught = _sweep(fn, FRAMES[name]())
        assert caught == len(OFFSETS), f"{label}/{name}: {caught}"


@pytest.mark.parametrize("name", VARYING)
def test_the_teeth_mutant_is_caught_wherever_the_cancellation_allows(name):
    """The `teeth-lead` mutant is the one the BLIND sweep nearly misses:
    5 of 36 offsets on the trending frame, 12 to 30 on the others, because
    a future-reading teeth is the outer line on 0.6779 to 0.9085 of bars
    and cancels there.

    What carries Gate B for it is this: at every offset where the
    UNPERTURBED mutant has an interior teeth within its 5-bar reach, the
    sweep catches it -- 24/24, 5/5, 15/15, 11/11, 20/20 and 20/20,
    i.e. 95 of 95 pooled. (It is also caught at 0 to 9 further offsets per
    frame, where the perturbation itself flips which line is outer; those
    are not asserted.) Pinned as the implication, with a floor of one
    exposed offset per frame, so neither limb can quietly become vacuous.
    """
    frame = FRAMES[name]()
    fn = _mutant("TEETH = (8, 5)", "TEETH = (8, -5)")
    jaw, teeth, lips = _lines(frame, teeth_lag=-TEETH[1])
    pair = concat([jaw, lips], axis=1)
    interior = ((teeth < pair.max(axis=1)) & (teeth > pair.min(axis=1))
                & fn(*frame).notna()).to_numpy()
    exposed = [j for j in OFFSETS
               if interior[max(0, j - TEETH[1]):j].any()]
    assert len(exposed) >= 1, "no offset exposes the mutant at all"
    assert all(_caught_at(fn, frame, j) for j in exposed)


# ------------------------------------------------------------ Gates C / D


@pytest.mark.parametrize("name", NAMES)
def test_reachability_and_the_flat_frame(name):
    """Every frame fires on 1,492 of 1,500 bars. The varying six are not
    remotely constant (1,492 distinct values each, asserted as "more than
    half the fired bars"); the flat frame is exactly 0.0 on all of them,
    which is a reading and not missing data -- all three lines coincide."""
    col = j_gator(*FRAMES[name]())
    fired = col.dropna()
    assert int(fired.size) == FIRED
    if name == "flat":
        assert bool((fired == 0.0).all())
        assert fired.nunique() == 1
    else:
        assert fired.nunique() > 0.5 * FIRED
        assert float(fired.abs().max()) > 0.0


@pytest.mark.parametrize("name", NAMES)
@pytest.mark.parametrize("factor", [8.0, 64.0])
def test_gate_d_scale_x8_x64_is_bit_identical(name, factor):
    """A power-of-two rescale is exact in binary at every step -- the
    EWMA's `(1-a)*s + a*x`, the subtractions, the `abs`, and then the
    division by a close scaled by the same factor, which cancels it. So
    this is asserted bit-exactly, on 1,492 of 1,492 bars of each of seven
    frames, and it is machine-independent: the same operations on the same
    doubles."""
    frame = FRAMES[name]()
    base = j_gator(*frame)
    other = j_gator(*_scaled(frame, factor))
    assert bool((base.isna() == other.isna()).all())
    m = base.notna()
    assert int(m.sum()) == FIRED
    assert bool((base[m] == other[m]).all())


@pytest.mark.parametrize("name", VARYING)
@pytest.mark.parametrize("factor", [10.0, 3.7, 0.1, 1.0000001])
def test_gate_d_scale_tolerance_for_inexact_factors(name, factor):
    """x10, x3.7, x0.1 and x1.0000001 round, so the requirement is a
    relative bound with matching NaN masks: measured max 6.480e-10 over
    all 24 frame-and-factor cells, asserted 1e-7.

    ⚠ That is six orders of magnitude worse than the inputs' own 1e-16,
    and it is the column's shape rather than a defect: `|jaw - teeth|` and
    `|teeth - lips|` are differences of nearby EWMAs, so the result is a
    small number carrying the absolute error of a price."""
    frame = FRAMES[name]()
    base = j_gator(*frame)
    other = j_gator(*_scaled(frame, factor))
    assert bool((base.isna() == other.isna()).all())
    assert _rel(base, other) <= 1e-7, _rel(base, other)


@pytest.mark.parametrize("level", [1e-6, 1e+6, 1e+100])
def test_gate_d_scale_at_extreme_price_levels(level):
    """The same bit-identity at price levels 1e-6, 1e+6 and 1e+100: the
    column is a ratio, so the exponent cancels.

    The finiteness assertion is not decoration: an `inf` reading is
    `notna` and compares equal to `inf`, so a column that read `inf` on
    every bar at 1e+100 would satisfy the fired count and the
    bit-equality. It is also what
    `test_the_cross_scale_overflow_is_disclosed_and_unguarded` leans on
    when it says one scale is fine (§D(c)'s `finite` column)."""
    frame = _walk(level=level)
    base = j_gator(*frame)
    assert int(base.notna().sum()) == FIRED
    assert bool(np.isfinite(base.dropna().to_numpy()).all())
    for factor in (8.0, 64.0):
        other = j_gator(*_scaled(frame, factor))
        m = base.notna()
        assert bool((base[m] == other[m]).all())


@pytest.mark.parametrize("name", NAMES)
def test_gate_d_fires_are_strictly_between_zero_and_n(name):
    """`0 < fires < n`, so a column that is NaN everywhere -- or one that
    never warms up -- cannot pass Gate D by being invariant."""
    col = j_gator(*FRAMES[name]())
    assert 0 < int(col.notna().sum()) < col.size


# ------------------------------------------------------------- the guards


@pytest.mark.parametrize("bad", [np.nan, 0.0, -1.0, np.inf, -np.inf, 1e-310])
def test_a_bad_close_empties_its_own_bar_and_no_other(bad):
    """The close is only the divisor, so a bad one is not recursive:
    measured, each of these six empties exactly bar J and moves 0 other
    bars."""
    j = 700
    frame = _walk()
    h, l, c = frame
    base = j_gator(*frame)
    c2 = c.copy()
    c2.iloc[j] = bad
    out = j_gator(h, l, c2)
    assert bool(out.isna().iloc[j])
    assert int((base.notna() & out.isna()).sum()) == 1
    m = base.notna() & out.notna()
    assert bool((base[m] == out[m]).all())


def test_what_the_close_guard_buys():
    """Without it, a zero or subnormal close reads `inf` and a NEGATIVE
    close reads a plausible-looking finite number of the wrong sign
    (-0.4778 measured). Pinned through the same source-edit machinery as
    the mutants, so the justification is a run and not an argument."""
    j = 700
    h, l, c = _walk()
    unguarded = _mutant(*CLOSE_GUARD_OFF)
    for bad in (0.0, 1e-310):
        c2 = c.copy()
        c2.iloc[j] = bad
        assert np.isinf(unguarded(h, l, c2).iloc[j])
    c2 = c.copy()
    c2.iloc[j] = -1.0
    raw = unguarded(h, l, c2).iloc[j]
    assert np.isfinite(raw) and raw < 0.0
    assert bool(j_gator(h, l, c2).isna().iloc[j])


@pytest.mark.parametrize("leg", ["high", "low"])
@pytest.mark.parametrize("bad", [np.inf, -np.inf])
def test_an_infinite_price_never_reaches_the_output(bad, leg):
    """No guard on `mid` is needed, and this is what says so: pandas turns
    an infinity into a NaN before the `ewm` kernel runs, and `ewm` SKIPS a
    NaN observation. So an infinite high gives bit-identically the column
    a NaN high gives, with 0 non-finite readings.

    Run on BOTH legs: `mid` is `(high + low) / 2`, so a bad low has to
    behave like a bad high, and §G2/§G3 measure that rather than arguing
    it from the symmetry.

    ⚠ This pins a pandas BEHAVIOUR the module relies on. If an upgrade
    stops doing it, this test fails rather than the fork silently
    shipping an infinite feature -- at which point the guard
    `mid.where(np.isfinite(mid))` is the fix."""
    j = 700
    h, l, c = _walk()

    def planted(value):
        if leg == "high":
            x = h.copy()
            x.iloc[j] = value
            return x, l
        x = l.copy()
        x.iloc[j] = value
        return h, x

    out, ref = j_gator(*planted(bad), close=c), j_gator(*planted(np.nan),
                                                        close=c)
    assert bool((out.isna() == ref.isna()).all())
    m = out.notna()
    assert int(m.sum()) == FIRED
    assert bool((out[m] == ref[m]).all())
    assert bool(np.isfinite(out[m].to_numpy()).all())


def test_a_bad_mid_leaves_earlier_bars_alone_and_decays():
    """A bad high IS recursive -- it is inside the filter -- so the claim
    is two-sided: every bar before it is bit-identical, and the
    contamination decays with the filter's own memory (max |rel| 2.44 at
    the bar, 1.2e-1 by +50, 1.6e-3 by +100, 1.5e-10 by +300 measured).

    Asserted as the decay's SHAPE: strictly falling across those
    checkpoints and under 1e-6 by +300. Not as the digits, which the
    frame's `np.exp` can move."""
    j = 700
    frame = _walk()
    h, l, c = frame
    base = j_gator(*frame)
    h2 = h.copy()
    h2.iloc[j] = np.nan
    out = j_gator(h2, l, c)
    pre = base.iloc[:j].notna() & out.iloc[:j].notna()
    assert bool((base.iloc[:j][pre] == out.iloc[:j][pre]).all())
    m = base.notna() & out.notna()
    rel = ((base[m] - out[m]).abs()
           / base[m].abs().where(base[m].abs() > 0, np.nan)).to_numpy()
    bars = np.arange(base.size)[m.to_numpy()]
    tops = [float(np.nanmax(rel[bars >= j + k])) for k in (0, 50, 100, 300)]
    assert tops[0] > tops[1] > tops[2] > tops[3]
    assert tops[3] < 1e-6, tops


@pytest.mark.parametrize("value", [np.nan, 0.0, -5.0])
def test_a_degenerate_frame_raises_nothing(value):
    """All-NaN, all-zero and all-negative frames: no float error is
    reachable under `errstate(all="raise")`, and every bar is NaN."""
    idx = date_range("2020-01-01", periods=60, freq="h")
    s = Series(np.full(60, value), index=idx)
    with np.errstate(all="raise"):
        out = j_gator(s.copy(), s.copy(), s.copy())
    assert int(out.notna().sum()) == 0


def test_the_cross_scale_overflow_is_disclosed_and_unguarded():
    """The one case nothing here guards, pinned so the disclosure cannot
    rot into silence: a frame whose high/low sit at 1e+300 while the close
    sits at 1e-300 overflows the division and reads `inf` (52 of 60 bars
    measured). That is bad data rather than a price -- the same walk at
    ONE scale fires 1,492 finite bars at 1e-6, 1e+6 and 1e+100, which is
    `test_gate_d_scale_at_extreme_price_levels`'s `np.isfinite` assertion
    and §D(c)'s `finite` column -- and the module reports it instead of
    hiding it."""
    h, l, _ = _walk(n=60, level=1e+300)
    tiny = Series(np.full(60, 1e-300), index=h.index)
    out = j_gator(h, l, tiny)
    assert int(np.isinf(out.to_numpy()).sum()) > 0


# ------------------------------------------------------- docs and the ledger


def test_the_docstrings_first_paragraph_survives_the_dictionary_cut():
    """`docs/gen_indicator_dictionary.py` shows `d[:150].rsplit(' ', 1)[0]`
    of the docstring's first paragraph, which drops the trailing word
    WHOLE. The cut only runs when the paragraph EXCEEDS 150 characters, so
    the budget is 150 and the penalty for passing it is a whole word, not
    a character. The paragraph is 146 characters, i.e. 4 to spare --
    measured by `python docs/measure_j_gator.py W`, which calls the
    generator's own `desc()` and grows the sentence until it loses a word.
    This test runs the generator's OWN `desc`, lifted out of its source by
    `ast` so that importing it does not run the 345-indicator probe: the
    assertion then fails if the generator's cut changes, and not only if
    this sentence grows."""
    doc = j_gator.__doc__.splitlines()
    body = []
    for line in doc[1:]:
        if line.strip():
            body.append(line.strip())
        elif body:
            break
    paragraph = " ".join(body)
    assert len(paragraph) == 146, len(paragraph)

    desc = _generator_desc()
    assert desc({"desc": paragraph}) == paragraph
    # One character past the 150 budget (five longer than the paragraph,
    # i.e. one past §W's measured slack of 4), and the generator takes a
    # whole word.
    longer = paragraph[:-1] + "x" * 5 + paragraph[-1:]
    assert len(longer) == 151
    assert desc({"desc": longer}) != longer


def test_the_gate_e_row_is_owed():
    """Gate E is run by issue-solver after this session, so the ledger has
    NO row for this indicator yet -- which is what
    `tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
    reports as owed, and what the receipt session replaces with the
    measured row (and this test with one pinning its identity).
    `docs/JGatorMeasured.md` §E says so too."""
    ledger = Path(__file__).resolve().parents[1] / "docs" / "gate_e_ledger.csv"
    rows = list(csv.DictReader(ledger.open(encoding="utf-8")))
    assert rows, "the ledger should not be empty"
    assert [r for r in rows if r["indicator"] == "j_gator"] == []
