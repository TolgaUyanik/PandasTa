# -*- coding: utf-8 -*-
"""J-DAMIANI: `j_damiani`, the Damiani volatmeter's volatility line
(PandasTa issue #105).

    TR           = max(high - low, |high - close[-1]|, |low - close[-1]|)
    ATR(n)       = TR.ewm(alpha=1/n, adjust=False).mean()
    base         = ATR(13) / ATR(40)
    J_DAMIANI[T] = base[T] + 0.5 * (J_DAMIANI[T-1] - J_DAMIANI[T-3])

WHAT THIS FILE PINS, in order of how much it would hurt to lose.

1. **Gate A against the issue's formula, spelled independently.** A
   hand-written true range, a hand-written Wilder recursion and a
   hand-written feedback loop, sharing no code with the module, agree on
   **1,497 of 1,497** fired bars of each of six varying frames (8,982
   pooled) with identical NaN masks -- measured BIT-equal here, asserted
   as a 1e-12 bound (absolute AND relative) because the two spellings are
   not obliged to round the same way and a reduced-kernel run may not.
   The screen prototype, which shares pandas' `ewm` and the same loop, is
   asserted bit-equal on all EIGHT frames including the two whose `base`
   goes NaN: same operations, same order, machine-independent. That limb
   is what ties this port to the 2026-10-24 screen's Gate E figures.
   ⚠ jesse is NOT installed here and web access is unavailable
   (`test_the_source_library_is_not_installed_here` records it, so the
   claim cannot rot into "checked against jesse"). What Gate A checks is
   the formula issue #105 quotes.

2. **THE FEEDBACK LOOP IS A RESONATOR, and that is the one structural
   thing to know about this column.** `vol[T] = base[T] + 0.5*(vol[T-1] -
   vol[T-3])` is a stable IIR filter -- largest pole modulus **0.872175**
   -- whose gain is **1.000000 at DC** and peaks at **3.674235 at a
   period of 7.4705 bars**. Pinned as the filter's own numbers (roots,
   gain, impulse decay), computed from `LAG_S`/`NEAR`/`FAR` so that
   changing a constant fails here.
   ⚠ And the disclosure that goes with it: the loop does NOT re-rank the
   column. Against the bare `ATR(13)/ATR(40)` ratio it reads Spearman
   **0.8978 .. 0.9322** over the six varying frames.

3. **Gate B, five mutants, no gap.** Five look-ahead mutants are read off
   the shipped module's source, edited, and `exec`'d in memory. The
   module is caught at **0 of 36** perturbation offsets on every frame;
   each mutant is live (every shared bar moves) and caught at **36 of
   36** on every frame. Each catch is one bar moving, by 5.8e-02 ..
   1.9e-01, so none of them is caught only marginally.

4. **The column is BOUNDED at any real price scale, and the bound is the
   ratio's.** Both ATRs are weighted means of the same true ranges with
   weights summing to 1, so in exact arithmetic `base` cannot pass the
   largest ratio of those weights, `SLOW/FAST` = 40/13 = **3.076923** --
   attained to one ulp on a frame that is flat and then moves, and not
   exceeded on any of the eight frames here. Through the loop (sum of
   positive taps 2.799187, negative -1.799187) the column lies in
   **(-5.5360, 8.6129)**; the six varying frames reach 0.691678 ..
   2.858073 and `flat-start` reaches 3.628336.
   ⚠ And the exception, pinned rather than left for a reader to find:
   at SUBNORMAL scale that bound FAILS. A true range of 59 ulps smooths
   to 5 ulps and 1 ulp -- subnormal multiplication rounds absolutely --
   so `base` reads exactly 5.0, above 40/13. The same regime is where
   the divisor guard stops being a no-op: at a true range of 7 ulps the
   slow ATR rounds to 0 while the fast one does not, and the UNGUARDED
   form reads `inf`.

5. **Gates C and D.** Every varying frame fires on 1,497 of 1,500 bars
   with 1,497 distinct values; x8/x64 is bit-identical, x10/x3.7/x0.1/
   x1.0000001 within **2.098e-14** relative (asserted 1e-9), and
   `0 < fires < n`.
   ⚠ **The FLAT frame fires NOWHERE** -- `ATR(40)` is 0 when no true
   range has moved, so the ratio is `0/0` -- which is why `0 < fires < n`
   is asserted on the six varying frames and the flat one is pinned
   separately. A frame flat for its first 50 bars fires from bar **53**.

6. **The NaNs are always a leading prefix.** 3 bars on a clean frame, 53
   on the flat-start one, contiguous-from-zero on all eight. A Wilder
   EWMA of non-negative observations that is positive once stays
   positive, so there are no mid-series holes.

7. **A bad price empties NO bar**, and that is measured for NaN and
   infinite highs, lows and closes at five different bars: the three-way
   max skips a NaN leg and `ewm` skips a NaN observation. It perturbs
   the column recursively instead, decaying (worst of the six
   leg-and-value cells) 6.5e-02 at the bar -> 4.2e-03 by +50 ->
   1.5e-03 by +100 -> 1.4e-05 by +300 -- the +-inf legs, except at +100
   where the NaN close is worst by a hair (1.482e-03 / 1.475e-03).
   ⚠ An INFINITE price is NOT the same as a NaN -- `high - low` is `inf`,
   which WINS the max rather than being skipped -- but it still never
   reaches the output: pandas turns it into NaN before the `ewm` kernel.
   That pandas behaviour is pinned, so an upgrade which stops doing it
   fails here rather than shipping an infinite feature.

8. **Which ATR, priced.** Four other readings of "ATR13/ATR40" are in
   reach -- SMA-seeded (`wilder_rma`/Pine `ta.rma`), this fork's `rma`, a
   plain EMA, and this fork's `true_range` with its epsilon and its NaN
   bar 0. Each is a different column, pinned as such, with the
   convergence of the seed differences pinned as a SHAPE.

9. **Gate E is DISCLOSE, and whose measurement the ledger row is.**
   `test_the_gate_e_row_is_this_ports_own_measurement` pins the row to
   run `is105-j_damiani-fa64c9c2` (2026-11-14, on THIS module): pooled
   **0.7621** against the manifest's `ATR_Ratio_5_20` at n = 397,069,
   top-five per-frame max median **0.7639** over 89 frames, 687
   comparators, no waiver. That is the 0.76 .. 0.80 band -- a ship with
   a note, pinned as the band's two BOUNDS rather than as digits. The
   screen's PROTOTYPE read the same digits on 2026-10-24, which is why
   the row needs its identity pinned and not just its arithmetic.
   `test_the_gate_e_run_closes_gate_c_on_real_data` reads Gate C's real
   limb off the same row -- 398,570 of 398,849 bars fire, the 279 empty
   ones being `FAR * 89` plus **12** more (a leading NaN run on real
   prices, item 5's mechanism), and NO fired bar reads exactly 0.0.
   ⚠ Not pinned, because the band does not read it: `natr_percentile`
   and `natr_Pctl` each reach 0.90 on ONE of the 89 frames (0.9043 /
   0.9126) and 0.80 on 15, against per-frame medians of 0.7425 / 0.7441.

The full receipt is `docs/JDamianiMeasured.md`.

NOT pinned here: Gate E's own arithmetic (the launcher runs it; 687
comparators over 89 real BIST frames, re-derived by
`tests/test_gate_e_ledger.py`) -- item 9 pins the ROW it produced and the
real-data counts in it. The in-fork overlap figures of §L are SYNTHETIC
and are disclosures, not gates: the 687 engine comparators hold no
pandas_ta port, so the Gate E run cannot see them.
"""
import csv
import importlib.util
from pathlib import Path

import numpy as np
import pytest
from pandas import DataFrame, Series, concat, date_range

from .context import pandas_ta  # noqa: F401

import pandas_ta as ta
from pandas_ta.volatility.j_damiani import (FAR, FAST, LAG_S, MIN_BARS, NEAR,
                                            SLOW, j_damiani)

N = 1500
LEVEL = 100.0
COLUMN = "J_DAMIANI_13_40"
#: The column's only NaNs on a frame whose `base` is defined from bar 0:
#: the feedback loop's `vol[-3]`. Both EWMAs are seeded at bar 0.
WARMUP = FAR
FIRED = N - WARMUP
#: Bars of `_flat_start` with no movement at all.
FLAT_PREFIX = 50
#: The blind causality sweep's 36 perturbation points.
OFFSETS = list(range(N - 36, N))


# ------------------------------------------------------------------ frames
# Same builders and seeds as `docs/measure_j_damiani.py`, so a number in
# this file and a number in the receipt are the same measurement.


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


def _flat_start(seed=7, n=N, level=LEVEL):
    """A walk whose first `FLAT_PREFIX` bars have `high == low == close`."""
    h, l, c = _walk(seed, n, level)
    h, l, c = h.copy(), l.copy(), c.copy()
    for s in (h, l, c):
        s.iloc[:FLAT_PREFIX] = level
    return h, l, c


FRAMES = {
    "walk": _walk, "trend": _trend, "range-bound": _range_bound,
    "grid": _grid, "heavy-tailed": _heavy, "jump": _jump, "flat": _flat,
    "flat-start": _flat_start,
}
NAMES = list(FRAMES)
#: The frames whose `base` is defined from bar 0, i.e. the ones that fire
#: on `FIRED` bars. `flat` fires nowhere and `flat-start` starts late.
VARYING = ["walk", "trend", "range-bound", "grid", "heavy-tailed", "jump"]


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


def _module_base(high, low, close):
    """`base` as the module computes it -- the bare ATR ratio."""
    prev = close.shift(1)
    tr = concat([high - low, (high - prev).abs(), (low - prev).abs()],
                axis=1).max(axis=1)
    fast = tr.ewm(alpha=1.0 / FAST, adjust=False).mean()
    slow = tr.ewm(alpha=1.0 / SLOW, adjust=False).mean()
    return fast / slow.where(slow > 0.0)


# ----------------------------------------------------------------- oracles


def _tr_oracle(high, low, close):
    """The three-way max, written out bar by bar."""
    h = high.to_numpy(dtype=float)
    l = low.to_numpy(dtype=float)
    c = close.to_numpy(dtype=float)
    out = np.empty(h.size)
    out[0] = h[0] - l[0]
    for i in range(1, h.size):
        out[i] = max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1]))
    return out


def _wilder_oracle(x, length):
    """`s[0] = x[0]; s[i] = (1 - a) * s[i-1] + a * x[i]`, written out."""
    a = 1.0 / length
    s = np.empty(x.size)
    s[0] = x[0]
    for i in range(1, x.size):
        s[i] = (1.0 - a) * s[i - 1] + a * x[i]
    return s


def _oracle(high, low, close):
    """The issue's formula, sharing no code with the module.

    No NaN handling: this is the formula as the issue writes it, so it is
    only comparable on frames whose `base` never goes NaN (`VARYING`).
    """
    tr = _tr_oracle(high, low, close)
    base = _wilder_oracle(tr, FAST) / _wilder_oracle(tr, SLOW)
    out = np.full(base.size, np.nan)
    for i in range(base.size):
        near = out[i - NEAR] if i >= NEAR else 0.0
        far = out[i - FAR] if i >= FAR else 0.0
        out[i] = base[i] + LAG_S * (near - far)
    out[:FAR] = np.nan
    return Series(out, index=close.index)


def _prototype(high, low, close):
    """`docs/issues/screen/ind_screen.py`, candidate `j_damiani`, retyped
    (that file is gitignored, so it is on the owner's machine only). Its
    `atr_wilder` and `sdiv` are inlined; the loop, the `0.0` for a missing
    predecessor and the `shift(3)` mask are the prototype's own."""
    def atr_wilder(h, l, c, n):
        tr = concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()],
                    axis=1).max(axis=1)
        return tr.ewm(alpha=1 / n, adjust=False).mean()

    base = (atr_wilder(high, low, close, 13) / atr_wilder(high, low, close, 40)
            ).replace([np.inf, -np.inf], np.nan).to_numpy()
    out = np.full(len(base), np.nan)
    for i in range(len(base)):
        if np.isnan(base[i]):
            continue
        p1 = out[i - 1] if i >= 1 and not np.isnan(out[i - 1]) else 0.0
        p3 = out[i - 3] if i >= 3 and not np.isnan(out[i - 3]) else 0.0
        out[i] = base[i] + 0.5 * (p1 - p3)
    return Series(out, index=close.index).where(
        Series(base, index=close.index).shift(3).notna())


def _loop(values):
    """The feedback loop, spelled the obvious way (a numpy array and
    `np.isnan`) rather than the module's optimised way. `docs/
    measure_j_damiani.py` §Z shows the two bit-identical."""
    out = np.full(values.size, np.nan)
    for i in range(values.size):
        if np.isnan(values[i]):
            continue
        near = out[i - NEAR] if i >= NEAR and not np.isnan(out[i - NEAR]) \
            else 0.0
        far = out[i - FAR] if i >= FAR and not np.isnan(out[i - FAR]) else 0.0
        out[i] = values[i] + LAG_S * (near - far)
    return out


def _variant(high, low, close, atr_fn):
    """The column with a different reading of ATR."""
    prev = close.shift(1)
    tr = concat([high - low, (high - prev).abs(), (low - prev).abs()],
                axis=1).max(axis=1)
    fast, slow = atr_fn(tr, FAST), atr_fn(tr, SLOW)
    base = fast / slow.where(slow > 0.0)
    out = Series(_loop(base.to_numpy(dtype=float)), index=base.index)
    return out.where(base.shift(FAR).notna())


# ----------------------------------------------------------------- mutants

SOURCE = Path(__file__).resolve().parents[1] / "pandas_ta" / "volatility" \
    / "j_damiani.py"

#: (label, old text, new text). Edits to the SHIPPED source, read off disk.
CAUSALITY_MUTANTS = [
    ("tr-lead", "prev = close.shift(1)", "prev = close.shift(-1)"),
    ("fast-atr-lead",
     "fast, slow = _atr(true_range, FAST), _atr(true_range, SLOW)",
     "fast, slow = _atr(true_range.shift(-1), FAST), _atr(true_range, SLOW)"),
    ("base-lead",
     "vol = Series(_volatmeter(base.to_numpy(dtype=float)), "
     "index=close.index)",
     "vol = Series(_volatmeter(base.shift(-1).to_numpy(dtype=float)), "
     "index=close.index)"),
    ("loop-lead",
     "near = out[i - NEAR] if i >= NEAR else np.nan",
     "near = values[i + NEAR] if i + NEAR < len(values) else np.nan"),
    ("output-early",
     "    vol = vol.where(base.shift(FAR).notna())",
     "    vol = vol.where(base.shift(FAR).notna()).shift(-1)"),
]
#: Not a causality mutant: the one guard, removed, to price what it buys.
DIVISOR_GUARD_OFF = ("slow.where(slow > 0.0)", "slow")


def _mutant(old, new):
    src = SOURCE.read_text(encoding="utf-8")
    assert src.count(old) == 1, f"{old!r} occurs {src.count(old)} times"
    ns = {}
    exec(compile(src.replace(old, new), "<mutant>", "exec"), ns)
    return ns["j_damiani"]


def _generator_desc():
    """`docs/gen_indicator_dictionary.py`'s own `desc`, lifted out of its
    source with `ast` and compiled alone.

    Importing that module runs its whole indicator probe, which is far too
    slow for a unit test -- and re-typing the cut here would pin a COPY of
    the rule rather than the rule. This compiles the generator's actual
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
    """Did perturbing every bar >= j move any bar < j?

    ⚠ `factor` on high, low AND close is not a global rescale -- the
    column is invariant under one of those, which is Gate D -- it is a
    rescale of a SUFFIX, which moves the true range at bar j.
    """
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
    assert "j_damiani" in ta.Category["volatility"]
    frame = _walk()
    col = j_damiani(*frame)
    assert col.name == COLUMN
    assert col.category == "volatility"

    h, l, c = frame
    df = DataFrame({"high": h, "low": l, "close": c})
    assert hasattr(df.ta, "j_damiani")
    via_accessor = df.ta.j_damiani()
    assert via_accessor.name == COLUMN
    assert bool((via_accessor.dropna() == col.dropna()).all())


def test_the_source_library_is_not_installed_here():
    """Gate A is the issue's quoted formula, spelled two ways -- not a run
    of jesse. Pinned so the claim cannot rot into "checked against jesse"
    if the dependency ever appears."""
    assert importlib.util.find_spec("jesse") is None


def test_the_constants_are_the_issues_numbers():
    """`vol = ATR13/ATR40 + 0.5*(vol[-1] - vol[-3])`, and nothing is an
    argument: a `fast=`/`slow=` surface would ship combinations nothing
    has measured."""
    assert (FAST, SLOW, LAG_S, NEAR, FAR) == (13, 40, 0.5, 1, 3)
    assert MIN_BARS == SLOW + FAR == 43
    import inspect
    assert list(inspect.signature(j_damiani).parameters) == \
        ["high", "low", "close", "offset", "kwargs"]


def test_a_frame_shorter_than_min_bars_is_refused():
    """`MIN_BARS` is a floor on the INPUT (the longer ATR's length plus the
    loop's reach), not the warm-up: one bar less and the function declines;
    at exactly `MIN_BARS` it fires on `MIN_BARS - WARMUP` = 40 bars, with
    the same values as the first 43 bars of the whole frame -- the column
    has no look-back beyond its own recursion."""
    h, l, c = _walk()
    short = MIN_BARS - 1
    assert j_damiani(h.iloc[:short], l.iloc[:short], c.iloc[:short]) is None
    ok = j_damiani(h.iloc[:MIN_BARS], l.iloc[:MIN_BARS], c.iloc[:MIN_BARS])
    assert int(ok.notna().sum()) == MIN_BARS - WARMUP == 40
    full = j_damiani(h, l, c)
    assert bool((ok.dropna() == full.iloc[:MIN_BARS].dropna()).all())


def test_offset_and_fillna():
    frame = _walk()
    base = j_damiani(*frame)
    moved = j_damiani(*frame, offset=2)
    assert bool((moved.iloc[2:].dropna()
                 == base.iloc[:-2].dropna().to_numpy()).all())
    filled = j_damiani(*frame, fillna=0.0)
    assert int(filled.isna().sum()) == 0
    assert int((filled.iloc[:WARMUP] == 0.0).sum()) == WARMUP


# ------------------------------------------------------------------ Gate A


@pytest.mark.parametrize("name", VARYING)
def test_gate_a_matches_the_issues_formula_spelled_independently(name):
    """A hand-written true range, a hand-written Wilder recursion and a
    hand-written loop, against the module, on 1,497 of 1,497 fired bars of
    each of six frames with identical NaN masks.

    Measured BIT-equal on all six here (max |diff| 0.0), asserted as a
    bound instead: the two spellings compute `(1-a)*s + a*x` through
    different code and are not obliged to round identically, so pinning
    bit-equality would pin this machine's kernels.

    ⚠ BOTH an absolute and a relative bound. The column sits near 1, so
    the two are nearly the same test here -- unlike `j_gator`, whose
    column passes through zero -- and keeping both means neither a
    near-zero reading nor a large one can hide a divergence.
    """
    frame = FRAMES[name]()
    col, oracle = j_damiani(*frame), _oracle(*frame)
    assert bool((col.isna() == oracle.isna()).all())
    assert int(col.notna().sum()) == FIRED
    m = col.notna() & oracle.notna()
    assert int(m.sum()) == FIRED
    assert float((col[m] - oracle[m]).abs().max()) <= 1e-12
    assert _rel(col, oracle) <= 1e-12, _rel(col, oracle)


@pytest.mark.parametrize("name", NAMES)
def test_gate_a_is_bit_equal_to_the_screen_prototype(name):
    """The prototype and the module perform the SAME operations in the same
    order (pandas' `ewm`, then the same loop), so bit-equality here is
    machine-independent and is asserted as such -- on all eight frames,
    including `flat` (where both fire nowhere) and `flat-start` (where
    both start at bar 53). This is the limb that ties this port to the
    2026-10-24 screen's Gate E figures.

    It is also where the module's `slow.where(slow > 0.0)` has to agree
    with the prototype's `_fin(a / b)`: two different spellings of what
    `0 / 0` means, measured to be the same reading."""
    frame = FRAMES[name]()
    col, proto = j_damiani(*frame), _prototype(*frame)
    assert bool((col.isna() == proto.isna()).all())
    m = col.notna()
    assert int(m.sum()) == (0 if name == "flat" else
                            N - 53 if name == "flat-start" else FIRED)
    assert bool((col[m] == proto[m]).all())


@pytest.mark.parametrize("name", NAMES)
def test_the_guard_changes_no_reading(name):
    """The module's one guard, removed through the same source-edit
    machinery as the mutants: on these eight frames it must not move a
    single bar.

    ⚠ Do NOT read that as "the guard is dead code" --
    `test_the_divisor_guard_is_not_a_no_op_at_subnormal_scale` builds the
    frame where the unguarded form reads `inf`, and
    `test_what_the_divisor_guard_buys` pins what it buys at a real price
    scale."""
    frame = FRAMES[name]()
    col, unguarded = j_damiani(*frame), _mutant(*DIVISOR_GUARD_OFF)(*frame)
    assert bool((col.isna() == unguarded.isna()).all())
    m = col.notna()
    assert bool((col[m] == unguarded[m]).all())


def test_bar_zeros_ratio_is_exactly_one_and_the_warmup_is_the_loops():
    """Both EWMAs are seeded at the first true range, so `base[0]` is
    `TR[0]/TR[0]` = 1.0 exactly and the column's only NaNs are the loop's
    three. The three masked bars are COMPUTED, not skipped: bar 3 recurses
    from them, and this checks that identity bar by bar."""
    frame = _walk()
    base = _module_base(*frame)
    assert base.iloc[0] == 1.0
    assert int(base.isna().sum()) == 0

    col = j_damiani(*frame)
    assert int(col.isna().sum()) == WARMUP == 3
    assert int(col.notna().to_numpy().argmax()) == WARMUP
    assert int(col.notna().sum()) == FIRED

    raw = _loop(base.to_numpy(dtype=float))
    assert raw[0] == base.iloc[0]
    assert raw[1] == base.iloc[1] + LAG_S * raw[0]
    assert raw[2] == base.iloc[2] + LAG_S * raw[1]
    assert col.iloc[FAR] == base.iloc[FAR] + LAG_S * (raw[2] - raw[0])


@pytest.mark.parametrize("name", VARYING)
def test_the_sma_seeded_atr_would_be_a_different_column(name):
    """"ATR" seeded with `SMA(TR[:n])` -- this fork's `wilder_rma`, Pine's
    `ta.rma` -- instead of at the first observation.

    A SEED difference is a warm-up difference and has to die, but here it
    dies SLOWLY: on the walk the max |diff| falls 6.0e-01 (bar 3) ->
    4.9e-02 (bar 100) -> 2.8e-05 (bar 400) -> 1.5e-09 (bar 800) against a
    column whose own max |value| over the 1,458 bars the two share is
    1.2597, and Spearman over the whole frame is only
    0.9297 .. 0.9925 because the first few hundred bars differ. Asserted
    as that SHAPE -- different early, agreeing to 1e-6 from bar 800 -- and
    as a floor on rho, not as digits.

    ⚠ That slowness is the disclosure: the 40-bar memory and the loop's
    resonance between them make several hundred bars of this column
    seed-dependent.
    """
    from pandas_ta.overlap.wilder_rma import wilder_rma
    frame = FRAMES[name]()
    col = j_damiani(*frame)
    other = _variant(*frame, lambda x, n: wilder_rma(x, length=n))
    m = col.notna() & other.notna()
    early = m & (np.arange(col.size) < 100)
    assert int((col[early] != other[early]).sum()) > 0
    late = m & (np.arange(col.size) >= 800)
    assert float((col[late] - other[late]).abs().max()) <= 1e-6
    assert _spearman(col, other) > 0.90


@pytest.mark.parametrize("name", VARYING)
def test_the_forks_rma_would_be_a_different_column(name):
    """`rma` is pandas' `ewm` at its DEFAULT `adjust=True` with
    `min_periods=length`, which is a third reading of "ATR". Measured
    0.9382 .. 0.9838 Spearman and NOT the same column -- asserted as "not
    one bar equal", which is what `adjust=True` guarantees here: it
    re-weights every bar, so no bar can coincide by construction."""
    from pandas_ta.overlap.rma import rma
    frame = FRAMES[name]()
    col = j_damiani(*frame)
    other = _variant(*frame, lambda x, n: rma(x, length=n))
    m = col.notna() & other.notna()
    assert int(m.sum()) > 0
    assert int((col[m] == other[m]).sum()) == 0
    assert _spearman(col, other) > 0.90


@pytest.mark.parametrize("name", VARYING)
def test_the_plain_ema_reading_would_be_a_different_column(name):
    """The SEED readings are warm-up differences; the ALPHA is not. Read as
    a plain EMA -- `alpha = 2/(n+1)`, `ewm(span=n, adjust=False)`, holding
    `adjust` fixed so the alpha is the only change -- the same formula is a
    different column on every bar: 0 bars in common, max |diff| 2.5e-01 ..
    5.0e-01, Spearman 0.8278 .. 0.8885.

    This is the load-bearing half of §A4, because the reading rests on the
    issue's word "ATR" and on the prototype -- NOT on jesse's source,
    which this worktree cannot read."""
    frame = FRAMES[name]()
    col = j_damiani(*frame)
    other = _variant(*frame, lambda x, n: x.ewm(span=n, adjust=False).mean())
    m = col.notna() & other.notna()
    assert int(m.sum()) == FIRED
    assert int((col[m] == other[m]).sum()) == 0
    assert float((col[m] - other[m]).abs().max()) > 1e-1
    assert 0.70 < _spearman(col, other) < 0.95


@pytest.mark.parametrize("name", VARYING)
def test_the_forks_true_range_would_be_a_different_column(name):
    """Why the true range is spelled in the module instead of imported.

    This fork's `true_range` differs twice over: it routes `high - low`
    through `non_zero_range`, which adds an epsilon to EVERY bar of the
    series as soon as ONE bar has `high == low`, and it NaNs bar 0. On
    these six frames no bar has `high == low` (asserted), so only the
    second divergence is in play -- and one missing seed bar is enough to
    move the column for hundreds of bars (max |diff| 4.6e-01 .. 1.1e+00,
    Spearman 0.7401 .. 0.9958).

    Asserted as "a different column, with a different NaN mask", plus the
    convergence shape on the walk. The epsilon is pinned on the flat
    frame instead, where it does fire."""
    from pandas_ta.volatility.true_range import true_range
    frame = FRAMES[name]()
    h, l, c = frame
    assert int((h == l).sum()) == 0
    col = j_damiani(*frame)
    tr = true_range(h, l, c)
    assert bool(tr.isna().iloc[0])
    fast = tr.ewm(alpha=1.0 / FAST, adjust=False).mean()
    slow = tr.ewm(alpha=1.0 / SLOW, adjust=False).mean()
    base = fast / slow.where(slow > 0.0)
    other = Series(_loop(base.to_numpy(dtype=float)), index=base.index) \
        .where(base.shift(FAR).notna())
    assert not bool((col.isna() == other.isna()).all())
    m = col.notna() & other.notna()
    assert int((col[m] != other[m]).sum()) > 0


def test_the_forks_true_range_epsilon_fires_on_a_flat_frame():
    """The other half of the divergence above, where it is visible: on a
    frame with `high == low` everywhere, `non_zero_range` makes every true
    range a positive epsilon, so the fork's spelling reads a RATIO where
    the module reads nothing at all. Measured: the module fires on 0 of
    1,500 bars, the fork's true range on 1,496."""
    from pandas_ta.volatility.true_range import true_range
    h, l, c = _flat()
    assert int((h == l).sum()) == N
    assert int(j_damiani(h, l, c).notna().sum()) == 0
    tr = true_range(h, l, c)
    assert float(tr.iloc[1]) > 0.0
    fast = tr.ewm(alpha=1.0 / FAST, adjust=False).mean()
    slow = tr.ewm(alpha=1.0 / SLOW, adjust=False).mean()
    base = fast / slow.where(slow > 0.0)
    other = Series(_loop(base.to_numpy(dtype=float)), index=base.index) \
        .where(base.shift(FAR).notna())
    assert int(other.notna().sum()) == N - 4


# -------------------------------------------------- the loop as a filter


def test_the_feedback_loop_is_a_stable_resonator():
    """The column's one structural surprise, as the filter's own numbers.

    `vol[T] = base[T] + 0.5*(vol[T-1] - vol[T-3])` has transfer function
    `1 / (1 - 0.5 z^-1 + 0.5 z^-3)`. Measured: largest pole modulus
    0.872175 (stable), gain 1.000000 at DC and at Nyquist, peak 3.674235
    at a period of 7.4705 bars.

    Computed from `LAG_S`/`NEAR`/`FAR` rather than typed, so changing a
    constant fails HERE and not only in a correlation somewhere. The
    bounds are loose enough for a reduced-kernel `np.roots`, tight enough
    that nothing else passes them."""
    roots = np.roots([1.0, -LAG_S, 0.0, LAG_S])
    assert NEAR == 1 and FAR == 3, "this polynomial is NEAR=1, FAR=3"
    assert abs(max(abs(r) for r in roots) - 0.872175) < 1e-6
    assert max(abs(r) for r in roots) < 1.0, "an unstable loop would blow up"

    w = np.linspace(1e-9, np.pi, 200_001)
    z = np.exp(-1j * w)
    gain = 1.0 / np.abs(1.0 - LAG_S * z + LAG_S * z ** 3)
    assert abs(1.0 / abs(1.0 - LAG_S + LAG_S) - 1.0) < 1e-12   # DC
    k = int(np.argmax(gain))
    assert abs(gain[k] - 3.674235) < 1e-3, gain[k]
    assert abs(2 * np.pi / w[k] - 7.4705) < 1e-2


def test_the_impulse_response_decays():
    """The same stability, measured through the loop itself rather than
    through `np.roots`: 1.0 at the impulse, 1.7e-01 by +10 bars, 6.3e-04
    by +50, 1.0e-18 by +300, and sum |h| = 4.598374 -- which is what
    bounds the column in `test_the_column_is_bounded_by_the_ratios_bound`.

    ⚠ The suffix maxima are non-increasing BY CONSTRUCTION, so asserting
    that they fall proves nothing (review round 4's finding). What is
    asserted instead is their magnitude at each horizon, the STRICT drop
    between horizons, and the pole's own envelope: every tap must sit
    under `1.05 * 0.872175 ** k`, which is the stability statement and
    fails the moment `LAG_S`, `NEAR` or `FAR` moves."""
    imp = np.zeros(400)
    imp[0] = 1.0
    h = _loop(imp)
    assert h[0] == 1.0
    tops = [float(np.abs(h[k:]).max()) for k in (0, 10, 50, 100, 200, 300)]
    assert tops[1] < 0.2 and tops[2] < 1e-3 and tops[5] < 1e-15
    for a, b in zip(tops, tops[1:]):
        assert b < 0.5 * a, tops
    envelope = 1.05 * 0.872175 ** np.arange(h.size)
    assert bool((np.abs(h) <= envelope).all())
    assert abs(float(np.abs(h).sum()) - 4.598374) < 1e-5


@pytest.mark.parametrize("name", VARYING)
def test_the_loop_reshapes_the_ratio_without_re_ranking_it(name):
    """The disclosure that goes with the resonator, and it is not a
    defence: against the bare `ATR(13)/ATR(40)` the shipped column agrees
    on 0 bars and differs by up to 0.40 .. 0.94 -- but Spearman is 0.8978
    .. 0.9322. The loop changes what the column reads, not what it ranks,
    so "this is not just an ATR ratio" is NOT available as an argument at
    Gate E. Asserted as a band."""
    frame = FRAMES[name]()
    col = j_damiani(*frame)
    bare = _module_base(*frame).where(col.notna())
    m = col.notna() & bare.notna()
    assert int(m.sum()) == FIRED
    assert int((col[m] == bare[m]).sum()) == 0
    assert float((col[m] - bare[m]).abs().max()) > 0.1
    assert 0.85 < _spearman(col, bare) < 0.96


def test_the_column_is_bounded_by_the_ratios_bound():
    """`base` is a ratio of two weighted means of the SAME true ranges
    whose weights each sum to 1, so it cannot exceed the largest ratio of
    those weights -- at lag 0, `SLOW/FAST` = 40/13.

    The supremum is ATTAINED: on a frame that is flat and then moves, the
    first moving bar is the only non-zero true range, so every weight but
    lag 0 multiplies a zero. Measured 3.0769230769230766, one ulp below
    40/13 -- asserted as "within 4 ulp and never above", because the
    division's rounding is the machine's.

    Then the loop's impulse response bounds the column itself:
    `|vol| <= sup(base) * sum|h|` = 14.1489, and the tighter two-sided
    envelope using the positive and negative taps is (-5.5360, 8.6129).
    Asserted against every frame here."""
    bound = SLOW / FAST
    h, l, c = _flat_start()
    base = _module_base(h, l, c)
    hit = float(base.iloc[FLAT_PREFIX])
    assert hit <= bound
    assert abs(hit - bound) <= 4 * np.spacing(bound), (hit, bound)

    imp = np.zeros(400)
    imp[0] = 1.0
    taps = _loop(imp)
    lo = bound * float(taps[taps < 0].sum())
    hi = bound * float(taps[taps > 0].sum())
    assert -5.6 < lo < -5.5 and 8.6 < hi < 8.7, (lo, hi)
    for name in NAMES:
        col = j_damiani(*FRAMES[name]()).dropna()
        if not col.size:
            continue
        assert float(_module_base(*FRAMES[name]()).max()) <= bound
        assert lo < float(col.min()) and float(col.max()) < hi, name


def _subnormal_frame(k, n=200, move=50):
    """A frame flat for `move` bars, then one bar whose true range is `k`
    ulps. `high` only, with `low` and `close` at 0.0, so the true range
    IS that one number."""
    high = np.zeros(n)
    high[move] = k * np.nextafter(0.0, 1.0)
    idx = date_range("2020-01-01", periods=n, freq="h")
    zero = Series(np.zeros(n), index=idx)
    return Series(high, index=idx), zero, zero.copy()


def test_the_bound_is_exact_arithmetic_and_subnormals_break_it():
    """The honest limit of the bound above, and it is not where the
    receipt first guessed (an underflow stall, §G5(c)): it is SUBNORMAL
    true ranges.

    Subnormal multiplication rounds ABSOLUTELY, so `1/13` and `1/40` of
    `k` ulps both round to a whole number of ulps and the ratio is
    whatever those two integers say. At k = 59 that is 5 ulps over 1 ulp:
    `base` reads exactly 5.0 -- 1.63x the 40/13 the weight argument
    allows -- and the column reads 6.8750.

    Pinned because the alternative is a bound in a shipped docstring that
    a reader would trust further than it goes. Asserted exactly (the
    arithmetic is integer ulp counts, so it is machine-independent for
    IEEE-754 doubles), and the column's own reading is asserted to stay
    inside the published envelope, which it does here."""
    h, l, c = _subnormal_frame(59)
    base = _module_base(h, l, c)
    assert float(base.max()) == 5.0
    assert float(base.max()) > SLOW / FAST
    col = j_damiani(h, l, c)
    assert float(col.max()) == 6.875
    assert int(np.isinf(col.to_numpy()).sum()) == 0
    # ... and at a real price scale the bound holds, which is the
    # contrast that makes the exception worth stating.
    assert float(_module_base(*_walk()).max()) <= SLOW / FAST


def test_the_divisor_guard_is_not_a_no_op_at_subnormal_scale():
    """§A2 measures the guard changing no reading on all eight frames, so
    the natural conclusion is that it is dead code. It is not.

    At a true range of 7 ulps the SLOW ATR rounds to exactly 0 while the
    fast one rounds to 1 ulp, so the unguarded form divides by zero and
    reads `inf` -- on every bar from the move onward. The guard turns
    that into NaN, which is also why nothing guards the division's
    RESULT: there is no second infinity for such a guard to catch (§G2
    measures that an infinite price cannot make one).

    This is the test that would notice if someone "simplified" the
    `where` away on the strength of §A2."""
    h, l, c = _subnormal_frame(7)
    prev = c.shift(1)
    tr = concat([h - l, (h - prev).abs(), (l - prev).abs()],
                axis=1).max(axis=1)
    fast = tr.ewm(alpha=1.0 / FAST, adjust=False).mean()
    slow = tr.ewm(alpha=1.0 / SLOW, adjust=False).mean()
    assert float(fast.iloc[50]) == np.nextafter(0.0, 1.0)
    assert float(slow.iloc[50]) == 0.0

    with np.errstate(divide="ignore", invalid="ignore"):
        raw = fast.to_numpy() / slow.to_numpy()
    assert int(np.isinf(raw).sum()) > 0

    col = j_damiani(h, l, c)
    assert int(np.isinf(col.to_numpy()).sum()) == 0
    assert int(col.notna().sum()) == 0


# ------------------------------------------------------- Gate B (mutants)


@pytest.mark.parametrize("name", VARYING)
def test_the_module_is_never_caught_by_the_future_sweep(name):
    """36 offsets, every bar >= J multiplied by 1.03: no bar < J may move.
    Measured 0 of 36 on each of the six varying frames."""
    assert _sweep(j_damiani, FRAMES[name]()) == 0


@pytest.mark.parametrize("label,old,new", CAUSALITY_MUTANTS)
def test_every_mutant_is_live_before_it_is_caught(label, old, new):
    """A mutant that is not live proves nothing, so liveness comes first.
    Measured: every mutant moves EVERY shared bar on every one of the six
    varying frames (1,496 or 1,497 of them, depending on how many tail
    bars its own `shift` empties). Asserted as "more than half", the floor
    all five clear by the whole margin."""
    fn = _mutant(old, new)
    for name in VARYING:
        frame = FRAMES[name]()
        base, mut = j_damiani(*frame), fn(*frame)
        m = base.notna() & mut.notna()
        assert int(m.sum()) > 0, f"{label}/{name}: mutant fires nowhere"
        moved = int((base[m] != mut[m]).sum())
        assert moved > 0.5 * int(m.sum()), f"{label}/{name}: {moved} moved"


@pytest.mark.parametrize("label,old,new", CAUSALITY_MUTANTS)
def test_each_mutant_is_caught_by_the_future_sweep(label, old, new):
    """All five are caught at 36 of 36 offsets on every frame. Asserted as
    "every offset": each one moves a bar the perturbation definitely
    enters, and unlike `j_gator`'s teeth there is no cancellation here to
    hide a look-ahead."""
    fn = _mutant(old, new)
    for name in VARYING:
        caught = _sweep(fn, FRAMES[name]())
        assert caught == len(OFFSETS), f"{label}/{name}: {caught}"


@pytest.mark.parametrize("label,old,new", CAUSALITY_MUTANTS)
def test_each_mutant_is_caught_loudly_not_marginally(label, old, new):
    """36 of 36 could still mean "caught by one bar in the last bits", so
    this measures HOW LOUD the catch is. Each mutant moves exactly one bar
    below J, by 5.8e-02 to 1.9e-01 at the two extreme offsets -- TWELVE
    orders of magnitude above the 2.098e-14 an inexact rescale costs
    (§D2; 5.8e-02 / 2.098e-14 = 2.8e12), so no catch here is a rounding
    artefact."""
    fn = _mutant(old, new)
    frame = FRAMES["walk"]()
    h, l, c = frame
    base = fn(h, l, c)
    for j in (OFFSETS[0], OFFSETS[-1]):
        f = Series(np.where(np.arange(c.size) >= j, 1.03, 1.0), index=c.index)
        out = fn(h * f, l * f, c * f)
        a, b = base.iloc[:j], out.iloc[:j]
        m = a.notna() & b.notna()
        assert int((a[m] != b[m]).sum()) >= 1
        assert float((a[m] - b[m]).abs().max()) > 1e-3


# ------------------------------------------------------------ Gates C / D


@pytest.mark.parametrize("name", VARYING)
def test_reachability_on_the_varying_frames(name):
    """Every varying frame fires on 1,497 of 1,500 bars, with 1,497
    distinct values -- asserted as "more than half the fired bars", since
    how many values coincide is a last-bits question. The readings
    straddle 1: measured 581 .. 1,215 above and 282 .. 916 below, and
    nothing is negative."""
    col = j_damiani(*FRAMES[name]())
    fired = col.dropna()
    assert int(fired.size) == FIRED
    assert fired.nunique() > 0.5 * FIRED
    assert int((fired > 1).sum()) > 0 and int((fired < 1).sum()) > 0
    assert int((fired <= 0).sum()) == 0


def test_a_flat_frame_reads_nothing_rather_than_zero():
    """The honest answer to no volatility at all, and the reason Gate D's
    `0 < fires < n` is asserted on the varying frames: `ATR(40)` is 0
    exactly when every true range so far is 0, and then so is `ATR(13)`,
    so the ratio is `0 / 0`. Measured: 0 of 1,500 bars fire.

    ⚠ This is a DIVERGENCE from `j_gator`, whose flat frame reads exactly
    0.0 on every bar. A consumer that treats "no reading" and "zero
    volatility expansion" the same way would be wrong here."""
    h, l, c = _flat()
    assert int(np.flatnonzero(_tr_oracle(h, l, c) != 0.0).size) == 0
    base = _module_base(h, l, c)
    assert int(base.notna().sum()) == 0
    col = j_damiani(h, l, c)
    assert int(col.notna().sum()) == 0
    assert int(col.isna().sum()) == N


def test_a_flat_prefix_delays_the_first_reading():
    """The same mechanism on a frame that starts flat and then moves: the
    column fires from three bars after the first moving one -- bar 53 of a
    frame flat for 50 -- not from bar 3. Measured, and asserted as that
    arithmetic so a change in `FLAT_PREFIX` or `FAR` moves with it."""
    h, l, c = _flat_start()
    base = _module_base(h, l, c)
    assert int(base.isna().sum()) == FLAT_PREFIX
    assert int(base.notna().to_numpy().argmax()) == FLAT_PREFIX
    col = j_damiani(h, l, c)
    assert int(col.notna().to_numpy().argmax()) == FLAT_PREFIX + FAR == 53
    assert int(col.notna().sum()) == N - FLAT_PREFIX - FAR


@pytest.mark.parametrize("name", NAMES)
def test_the_nans_are_always_a_leading_prefix(name):
    """There are no mid-series holes, and that is a property of the
    smoother rather than a lucky frame: a Wilder EWMA of non-negative
    observations that is positive once stays positive, so `base` cannot go
    NaN after it is defined. Measured contiguous-from-zero on all eight
    frames -- 3 bars on the clean six, 53 on `flat-start`, all 1,500 on
    `flat`."""
    col = j_damiani(*FRAMES[name]())
    nan_bars = np.flatnonzero(col.isna().to_numpy())
    assert bool((nan_bars == np.arange(nan_bars.size)).all())


def test_the_leading_prefix_survives_a_frame_built_to_break_it():
    """The eight frames above all have their NaNs at the very start, so
    they cannot tell "always a prefix" from "these frames happen to be
    easy". This one is built so the NaN run has to END mid-frame: 7 ulps
    of movement at bar 50, which rounds the slow ATR to exactly zero
    (§G5(d)), then a real move at bar 100.

    Measured: NaN on 103 bars, still a contiguous prefix, first fired bar
    103 — three bars after the real move, which is the loop's own
    warm-up re-applied."""
    h, l, c = _subnormal_frame(7)
    h = h.copy()
    h.iloc[100] = 1.0
    col = j_damiani(h, l, c)
    nan_bars = np.flatnonzero(col.isna().to_numpy())
    assert nan_bars.size == 103
    assert bool((nan_bars == np.arange(nan_bars.size)).all())
    assert int(col.notna().to_numpy().argmax()) == 103
    assert int(np.isinf(col.to_numpy()).sum()) == 0


@pytest.mark.parametrize("name", NAMES)
@pytest.mark.parametrize("factor", [8.0, 64.0])
def test_gate_d_scale_x8_x64_is_bit_identical(name, factor):
    """A power-of-two rescale is exact in binary at every step -- the
    three-way `max`, the EWMA's `(1-a)*s + a*x`, and then the division of
    two quantities scaled by the same factor, which cancels it. So this is
    asserted bit-exactly and it is machine-independent: the same
    operations on the same doubles."""
    frame = FRAMES[name]()
    base = j_damiani(*frame)
    other = j_damiani(*_scaled(frame, factor))
    assert bool((base.isna() == other.isna()).all())
    m = base.notna()
    assert bool((base[m] == other[m]).all())


@pytest.mark.parametrize("name", VARYING)
@pytest.mark.parametrize("factor", [10.0, 3.7, 0.1, 1.0000001])
def test_gate_d_scale_tolerance_for_inexact_factors(name, factor):
    """x10, x3.7, x0.1 and x1.0000001 round, so the requirement is a
    relative bound with matching NaN masks: measured max 2.098e-14 over
    all 24 frame-and-factor cells, asserted 1e-9.

    Nearly FIVE orders of magnitude of headroom (1e-9 / 2.098e-14 =
    4.8e4), because a reduced-kernel run moves the frames themselves in
    their last bits. ⚠ The column is about four and a half orders better
    conditioned than `j_gator`'s 6.5e-10: `base` is a ratio of two
    POSITIVE nearby means, where that one was a difference of them."""
    frame = FRAMES[name]()
    base = j_damiani(*frame)
    other = j_damiani(*_scaled(frame, factor))
    assert bool((base.isna() == other.isna()).all())
    assert _rel(base, other) <= 1e-9, _rel(base, other)


@pytest.mark.parametrize("level", [1e-6, 1e+6, 1e+100])
def test_gate_d_scale_at_extreme_price_levels(level):
    """The same bit-identity at price levels 1e-6, 1e+6 and 1e+100: the
    column is a ratio of two true-range means, so the exponent cancels.

    The finiteness assertion is not decoration: an `inf` reading is
    `notna` and compares equal to `inf`, so a column that read `inf` on
    every bar at 1e+100 would satisfy the fired count and the
    bit-equality."""
    frame = _walk(level=level)
    base = j_damiani(*frame)
    assert int(base.notna().sum()) == FIRED
    assert bool(np.isfinite(base.dropna().to_numpy()).all())
    for factor in (8.0, 64.0):
        other = j_damiani(*_scaled(frame, factor))
        m = base.notna()
        assert bool((base[m] == other[m]).all())


@pytest.mark.parametrize("name", VARYING + ["flat-start"])
def test_gate_d_fires_are_strictly_between_zero_and_n(name):
    """`0 < fires < n`, so a column that is NaN everywhere -- or one that
    never warms up -- cannot pass Gate D by being invariant.

    ⚠ The `flat` frame is NOT in this list, because it fires on 0 bars by
    construction (`0 / 0`); `test_a_flat_frame_reads_nothing_rather_than_zero`
    pins that case instead of this test quietly covering it."""
    col = j_damiani(*FRAMES[name]())
    assert 0 < int(col.notna().sum()) < col.size


# ------------------------------------------------------------- the guards


@pytest.mark.parametrize("bad", [np.nan, np.inf, -np.inf])
@pytest.mark.parametrize("leg", ["high", "low", "close"])
@pytest.mark.parametrize("j", [100, 700, 1200])
def test_a_bad_price_empties_no_bar_and_decays(bad, leg, j):
    """A bad price does NOT hole this column, which is the opposite of the
    natural guess and is why it is measured at three bars on each of three
    legs with each of three values.

    Two mechanisms, both pinned: the true range is a three-way max that
    SKIPS a NaN leg, so one bad price still leaves it a value; and `ewm`
    skips a NaN observation instead of poisoning the tail. What a bad
    price does is perturb the column RECURSIVELY -- it is inside both
    EWMAs -- so the claim is two-sided: every bar before it is
    bit-identical, and the contamination decays with the slow filter's
    memory. Worst over all six (leg, value) cells and all five measured
    plants: 6.5e-02 at the bar, 4.2e-03 by +50, 1.5e-03 by +100, 1.4e-05
    by +300 -- those being the +-inf legs, EXCEPT at +100, where the NaN
    close is the worst of the six by a hair (1.482e-03 against the +-inf
    legs' 1.475e-03). The NaN legs reach 3.0e-02 (high), 5.0e-02 (low)
    and 5.2e-02 (close) at the bar itself.

    ⚠ Not every plant moves the column at all -- a NaN high on a down bar
    removes two legs the max was not using -- so the decay is asserted
    where there is something to decay, and nothing where there is not.
    ⚠ And it is asserted as RATIOS, not as "the suffix maxima fall":
    those are non-increasing by construction and prove nothing (review
    round 4's finding). Measured worst-case ratios are ~6% at +50 and
    ~2% at +100; the bounds below are 50% and 25%."""
    frame = _walk()
    h, l, c = frame
    base = j_damiani(*frame)
    h2, l2, c2 = h.copy(), l.copy(), c.copy()
    {"high": h2, "low": l2, "close": c2}[leg].iloc[j] = bad
    out = j_damiani(h2, l2, c2)

    assert bool((base.isna() == out.isna()).all())
    assert int((base.notna() & out.isna()).sum()) == 0
    assert int(out.notna().sum()) == FIRED
    assert bool(np.isfinite(out.dropna().to_numpy()).all())

    pre = base.iloc[:j].notna() & out.iloc[:j].notna()
    assert bool((base.iloc[:j][pre] == out.iloc[:j][pre]).all())

    m = base.notna() & out.notna()
    rel = ((base[m] - out[m]).abs()
           / base[m].abs().where(base[m].abs() > 0, np.nan)).to_numpy()
    bars = np.arange(base.size)[m.to_numpy()]
    tops = [float(np.nanmax(rel[bars >= j + k])) for k in (0, 50, 100)]
    assert tops[0] <= 0.1
    if tops[0] > 0.0:
        assert tops[1] <= 0.5 * tops[0], tops
        assert tops[2] <= 0.25 * tops[0], tops
    else:
        assert tops[1] == 0.0 and tops[2] == 0.0


@pytest.mark.parametrize("leg", ["high", "low", "close"])
def test_an_infinite_price_never_reaches_the_output(leg):
    """No guard against an infinity is needed, and this is what says so.

    ⚠ It is NOT the same as planting a NaN, and the natural claim that it
    is would have been WRONG: `high - low` at an infinite high is `inf`,
    which WINS the three-way max rather than being skipped by it. The
    true range at that bar is infinite -- asserted here -- and what saves
    the column is the next step: pandas converts the infinity to NaN
    before the `ewm` kernel runs, and `ewm` skips a NaN observation. So
    the ATRs carry through the bar and every reading stays finite, while
    being a different column from the NaN plant (up to 7.4e-02 apart).

    ⚠ This pins a pandas BEHAVIOUR the module relies on. If an upgrade
    stops doing it, this test fails rather than the fork silently
    shipping an infinite feature -- at which point the fix is
    `true_range.where(np.isfinite(true_range))`."""
    j = 700
    h, l, c = _walk()
    h2, l2, c2 = h.copy(), l.copy(), c.copy()
    {"high": h2, "low": l2, "close": c2}[leg].iloc[j] = np.inf

    prev = c2.shift(1)
    tr = concat([h2 - l2, (h2 - prev).abs(), (l2 - prev).abs()],
                axis=1).max(axis=1)
    assert int(np.isinf(tr.to_numpy()).sum()) == 1
    smoothed = tr.ewm(alpha=1.0 / FAST, adjust=False).mean()
    assert int(np.isinf(smoothed.to_numpy()).sum()) == 0
    assert int(smoothed.isna().sum()) == 0

    out = j_damiani(h2, l2, c2)
    assert int(out.notna().sum()) == FIRED
    assert bool(np.isfinite(out.dropna().to_numpy()).all())

    h3, l3, c3 = h.copy(), l.copy(), c.copy()
    {"high": h3, "low": l3, "close": c3}[leg].iloc[j] = np.nan
    nan_plant = j_damiani(h3, l3, c3)
    m = out.notna() & nan_plant.notna()
    assert float((out[m] - nan_plant[m]).abs().max()) > 1e-3


@pytest.mark.parametrize("value", [np.nan, 0.0, -5.0, 100.0])
def test_a_degenerate_frame_raises_nothing(value):
    """All-NaN, all-zero, all-negative and all-one-price frames: no float
    error is reachable under `errstate(all="raise")`, and every bar is
    NaN. The last of the four is the one that matters -- a frame of a
    repeated price is a halted instrument, not a pathological input."""
    idx = date_range("2020-01-01", periods=60, freq="h")
    s = Series(np.full(60, value), index=idx)
    with np.errstate(all="raise"):
        out = j_damiani(s.copy(), s.copy(), s.copy())
    assert int(out.notna().sum()) == 0


def test_what_the_divisor_guard_buys():
    """The guard changes no reading (`test_the_guard_changes_no_reading`),
    so what it buys has to be stated exactly: the `0 / 0` of a frame with
    no movement is decided HERE rather than inside pandas.

    Measured, and this is the whole justification: numpy raises
    `FloatingPointError` on that division under `errstate(all="raise")`,
    while pandas suppresses the flag itself -- so TODAY the unguarded form
    survives too. The guard is what makes the module's behaviour
    independent of that pandas internal. If this test ever fails because
    pandas stopped suppressing, the guard is already the fix."""
    frame = _flat()
    with np.errstate(all="raise"):
        assert int(j_damiani(*frame).notna().sum()) == 0

    h, l, c = frame
    prev = c.shift(1)
    tr = concat([h - l, (h - prev).abs(), (l - prev).abs()],
                axis=1).max(axis=1)
    fast = tr.ewm(alpha=1.0 / FAST, adjust=False).mean()
    slow = tr.ewm(alpha=1.0 / SLOW, adjust=False).mean()
    assert float(slow.iloc[-1]) == 0.0
    with pytest.raises(FloatingPointError):
        with np.errstate(all="raise"):
            fast.to_numpy() / slow.to_numpy()


def test_an_overflowing_range_is_skipped_rather_than_shipped():
    """The adversarial frame for the missing overflow guard: a first bar
    whose `high - low` overflows to `inf`, then a normal walk. The
    infinite true range is skipped by `ewm` (as above), so the column is
    finite on every fired bar -- measured 596 of 600, the 4 being bar 0's
    skipped observation plus the loop's three."""
    n = 600
    h, l, c = _walk(n=n)
    h2, l2 = h.copy(), l.copy()
    h2.iloc[0], l2.iloc[0] = 1e+308, -1e+308
    out = j_damiani(h2, l2, c)
    v = out.dropna().to_numpy()
    assert v.size == n - 4
    assert bool(np.isfinite(v).all())
    assert float(v.max()) < SLOW / FAST * 4.598374


def test_a_cross_scale_frame_is_finite_because_the_close_is_not_a_divisor():
    """`j_gator` discloses a cross-scale overflow here; this column has
    none, and the reason is structural rather than lucky. The close enters
    only through the true range's gap legs, never as a divisor, so a frame
    whose high/low sit at 1e+300 while the close sits at 1e-300 still
    reads a finite ratio -- measured 57 fired bars, all finite."""
    h, l, _ = _walk(n=60, level=1e+300)
    tiny = Series(np.full(60, 1e-300), index=h.index)
    out = j_damiani(h, l, tiny)
    v = out.dropna().to_numpy()
    assert v.size == 57
    assert bool(np.isfinite(v).all())


# ------------------------------------------------------- docs and the ledger


def test_the_docstrings_first_paragraph_survives_the_dictionary_cut():
    """`docs/gen_indicator_dictionary.py` shows `d[:150].rsplit(' ', 1)[0]`
    of the docstring's first paragraph, which drops the trailing word
    WHOLE. The cut only runs when the paragraph EXCEEDS 150 characters, so
    the budget is 150 and the penalty for passing it is a whole word, not
    a character. The paragraph is 141 characters, i.e. 9 to spare --
    measured by `python docs/measure_j_damiani.py W`, which calls the
    generator's own `desc()` and grows the sentence until it loses a word.
    This test runs the generator's OWN `desc`, lifted out of its source by
    `ast` so that importing it does not run the whole probe: the assertion
    then fails if the generator's cut changes, and not only if this
    sentence grows."""
    doc = j_damiani.__doc__.splitlines()
    body = []
    for line in doc[1:]:
        if line.strip():
            body.append(line.strip())
        elif body:
            break
    paragraph = " ".join(body)
    assert len(paragraph) == 141, len(paragraph)

    desc = _generator_desc()
    assert desc({"desc": paragraph}) == paragraph
    # One character past the 150 budget (ten longer than the paragraph,
    # i.e. one past §W's measured slack of 9), and the generator takes a
    # whole word.
    longer = paragraph[:-1] + "x" * 10 + paragraph[-1:]
    assert len(longer) == 151
    assert desc({"desc": longer}) != longer


def _j_damiani_ledger_row():
    ledger = Path(__file__).resolve().parents[1] / "docs" / "gate_e_ledger.csv"
    rows = list(csv.DictReader(ledger.open(encoding="utf-8")))
    assert rows, "the ledger should not be empty"
    rows = [r for r in rows if r["indicator"] == "j_damiani"]
    assert len(rows) == 1, rows
    return rows[0]


def test_the_gate_e_row_is_this_ports_own_measurement():
    """The ledger row for `j_damiani` must come from the run on THIS
    module, `is105-j_damiani-fa64c9c2` (measured 2026-11-14), and NOT from
    the screen of 2026-10-24, which measured the PROTOTYPE. The two agree
    to every printed digit -- pooled 0.7621 against the manifest's
    `ATR_Ratio_5_20` at n = 397,069, top-five per-frame max median 0.7639
    over 89 frames, runners-up `natr_percentile` 0.7302 and `natr_Pctl`
    0.7294 -- which is exactly why the row's identity needs pinning:
    `tests/test_gate_e_ledger.py` re-derives a row's `module_sha1` and
    output fingerprint from the tree and checks its verdict arithmetic,
    but it cannot see WHOSE measurement a row came from. Item 1 asserts
    this module bit-equal to the prototype on all eight frames, so the
    agreement is expected -- and an expected agreement is the easiest kind
    of row to copy over by mistake.

    The verdict is **DISCLOSE**, the 0.76 .. 0.80 band of
    `r3-perframe-0.90`: a ship with a note, not a strike. The band's two
    limbs are asserted as BOUNDS and not as digits -- pooled in
    [0.76, 0.80), top-five per-frame max median below the 0.90 strike line
    -- so a re-recorded row that moved within the band still has to stay
    in it.

    This test replaced `test_the_gate_e_row_is_owed`, which asserted the
    row was ABSENT and so failed the moment the receipt session recorded
    it. `docs/JDamianiMeasured.md` §E carries the result in full,
    including what the band does not read: `natr_percentile` and
    `natr_Pctl` each reach 0.90 on ONE of the 89 frames (0.9043 / 0.9126)
    and 0.80 on 15 of them, while their per-frame MEDIANS -- which is what
    the band reads -- are 0.7425 and 0.7441."""
    row = _j_damiani_ledger_row()
    assert row["module"] == "pandas_ta.volatility.j_damiani"
    assert row["column"] == f"J_DAMIANI_{FAST}_{SLOW}"
    assert row["run"] == "is105-j_damiani-fa64c9c2"
    assert row["verdict"] == "DISCLOSE"
    assert row["verdict_schema"] == "r3-perframe-0.90"
    assert row["waiver"] == ""
    assert row["against"] == "ATR_Ratio_5_20"
    assert row["against_set"] == "manifest"
    assert row["perframe_max_against"] == "ATR_Ratio_5_20"
    assert (int(row["n_frames"]), int(row["n_comparators"])) == (89, 687)
    # DISCLOSE is 0.76 <= pooled < 0.80, and STRUCK needs a top-5
    # comparator's per-frame median >= 0.90.
    assert 0.76 <= float(row["max_abs_rho"]) < 0.80
    assert float(row["perframe_max_median_abs_rho"]) < 0.90


def test_the_gate_e_run_closes_gate_c_on_real_data():
    """Gate C's real-data limb, read off the SAME ledger row rather than
    retyped: the column fires on 398,570 of the run's 398,849 pooled bars
    over 89 real BIST frames, so `0 < fires < n` holds there and not only
    on the synthetic frames of item 5.

    The 279 empty bars are MORE than the loop's warm-up, and that is the
    one real-data fact this run adds to the synthetic picture. A frame
    whose `base` is defined from bar 0 loses exactly `FAR` = 3 bars
    (item 6), i.e. 267 over 89 frames; the remaining **12** are a leading
    NaN run somewhere in the universe, which is the `flat`/`flat-start`
    mechanism of item 5 reaching real prices -- an opening stretch whose
    true range is 0, so `ATR(40)` is 0 and the ratio is `0/0`. WHICH
    frames carry those 12 bars is not visible from the ledger row, and
    this session did not run the harness, so the mechanism is named from
    item 6's measurement ("the NaNs are always a leading prefix") and the
    COUNT is what is pinned.

    `non_zero` equals `non_nan`, i.e. NO fired real bar reads exactly
    0.0 -- consistent with `base` being a ratio of two positive EWMAs
    wherever it is defined at all."""
    row = _j_damiani_ledger_row()
    pooled = int(row["pooled_bars"])
    fires = int(row["non_nan"])
    frames = int(row["n_frames"])
    assert 0 < fires < pooled
    assert pooled - fires == FAR * frames + 12
    assert int(row["non_zero"]) == fires
