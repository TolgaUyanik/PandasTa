# -*- coding: utf-8 -*-
"""J-SAFEZONE-DIST: `j_safezone_dist`, the distance to Elder's SafeZone
long stop (PandasTa issue #121).

    pen[T]  = max(low[T-1] - low[T], 0)
    avg[T]  = sum(pen, 22) / count(pen > 0, 22)
    raw[T]  = low[T-1] - 2.5 * avg[T-1]
    stop[T] = max(raw[T-2], raw[T-1], raw[T])
    J_SAFEZONE_DIST[T] = (close[T] - stop[T]) / close[T]

WHAT THIS FILE PINS, in order of how much it would hurt to lose.

1. **Gate A against the issue's formula, spelled independently.** A
   bar-by-bar oracle -- its own penetration loop, its own 22-bar window
   sums over plain Python slices, its own 3-bar max, sharing no code with
   the module -- agrees on **1,475 of 1,475** fired bars of each of six
   varying frames (8,850 pooled) with identical NaN masks. Measured
   BIT-equal here; asserted as a 1e-12 bound (absolute AND relative),
   because `rolling.sum` and `sum()` over a slice are not obliged to
   round the same way and a reduced numpy kernel may not. The screen
   prototype, which shares pandas' rolling operators, is asserted
   bit-equal on all EIGHT frames -- that limb is what ties this port to
   the 2026-10-24 screen's Gate E figures.
   ⚠ jesse is NOT installed here and web access is unavailable
   (`test_the_source_library_is_not_installed_here` records it, so the
   claim cannot rot into "checked against jesse"). What Gate A checks is
   the formula issue #121 quotes.

2. **WHICH MEAN, and the alternative pinned as a different column.**
   Elder averages the penetrations over the bars that HAD one
   (`sum / count`), not over all 22. The divide-by-22 reading gives a
   smaller mean, so a higher stop and a SMALLER distance -- on **all
   8,850** shared bars, every single one, at Spearman 0.9378 .. 0.9705.
   It also never goes NaN, which is the sharper difference: it answers
   on frames where this column correctly has no answer.

3. **THE MISSINGNESS IS INFORMATIVE**, which the nearest reference port
   (`j_damiani`) does not have: there a NaN means no movement at all,
   here it means no DOWNWARD movement. `avg` is NaN exactly when the
   last 22 bars hold
   NO down-penetration, so the column is blank precisely where a long
   has had an unusually easy ride. A `flat` frame fires on **0 of
   1,500** and a strictly-rising-lows frame on **0 of 1,500** -- the
   second is the sharp one, because every bar of it moves. `0 < fires <
   n` is therefore asserted on the six VARYING frames and those two are
   pinned separately.

4. **Gate B is the sweep AND the oracle, because the sweep alone has a
   measured blind spot.** The module is caught at **0 of 36**
   perturbation offsets on every frame. Six look-ahead mutants are read
   off the shipped source, edited and `exec`'d in memory; every one is
   live and caught on **3 to 36** of those 36 offsets on each of six
   frames, each catch moving a bar by 3.4e-04 .. 3.0e-02.
   ⚠ A count below 36 is the FORMULA's and not a gap in the mutant --
   `clip(lower=0)`, the mean over the hits and `rolling(3).max()` all
   discard information.
   ⚠ **The blind spot, pinned rather than left for a reader to find.**
   The stop carries TWO `shift(1)`s, so an edit that leads by ONE bar is
   absorbed by them: it makes the output read bar T's OWN low without
   reading any later bar. Five such edits are caught **0 of 36** by the
   sweep and all five are caught by Gate A's oracle. That is why the
   look-ahead mutants lead by two bars where the chain allows it.

5. **Gates C and D.** Every varying frame fires on 1,475 of 1,500 bars
   with 1,471 .. 1,475 distinct values; x8/x64 is bit-identical, also at
   price levels 1e-6, 1e+6 and 1e+100; x10/x3.7/x0.1/x1.0000001 within
   **4.091e-11** relative, and 6.546e-11 with AVX-512/AVX2/FMA3 off --
   the only figure outside §Z's timings that moves between numpy
   dispatches, so the bound is asserted at 1e-9; `0 < fires < n`; and a
   level
   SHIFT of +10 moves all 1,475 fired bars, so the bit-identity is not
   vacuous. The column reads -0.3262 .. 0.3375 over the six, negative on
   1,138 of 8,850 bars and exactly 0.0 on none.

6. **A bad price EMPTIES BARS here**, unlike `j_damiani`, and the count
   is exact: one NaN, +inf or -inf LOW blanks bars T+1 .. T+25, 25 of
   them, contiguous, with every bar before T bit-identical; a bad CLOSE
   blanks exactly its own bar. A plant at the last bar blanks nothing,
   because the frame ends first.

7. **Two guards, each priced, and THREE overflow routes rather than
   one.** The `hits` divisor guard is bit-equal to the bare division on
   all eight frames -- `total > 0` implies `hits > 0` -- so what it buys
   is deciding the `0/0` here rather than inside numpy. The final finite
   mask is bit-equal on all eight too, and on a frame whose lows are
   near DBL_MAX and whose closes are near DBL_MIN it is the only thing
   between this column and **95 infinite readings out of 120**.
   ⚠ That is ROUTE 3 of three arithmetic routes an infinity can take on
   FINITE inputs. Route 1 is overflow in `low.shift(1) - low` (which
   needs a negative low, and the input guard allows one) and route 2 is
   overflow in `pen.rolling(22).sum()` (eleven penetrations near DBL_MAX
   in a window). Measured: neither 1 nor 2 reaches the output with OR
   without the mask, because pandas' `rolling.sum` is COMPENSATED and an
   overflowing window reads NaN rather than `inf`. That pandas
   behaviour is pinned on its own, so an upgrade which stops doing it
   fails here instead of shipping an infinite feature.

8. **Gate E is PENDING**, run by issue-solver after this session.
   `test_the_gate_e_row_is_owed_and_not_yet_recorded` asserts the ledger
   has no row for `j_safezone_dist`, which is the receipt session's cue.
   The screen measured the PROTOTYPE at SHIP (max |rho| 0.7059 vs
   `Dist_to_hma_pct`, n = 396,606, per-frame max median 0.7249); that is
   issue #121's number and not this port's. Gate C's real-data limb is
   owed from the same run.

Every number above is printed by `python docs/measure_j_safezone_dist.py`
and by `python docs/measure_j_safezone_dist_cpu.py <section>` under
numpy's reduced CPU dispatch, EXCEPT the Gate E figures of item 8, which
are quoted from issue #121 and were measured on the PROTOTYPE.
`docs/JSafezoneDistMeasured.md` carries the tables.

NOT pinned here: Gate E's own arithmetic (the launcher runs it; 687
comparators over 89 real BIST frames, re-derived by
`tests/test_gate_e_ledger.py`). The in-fork overlap figures of §L are
SYNTHETIC and are disclosures, not gates: the 687 engine comparators
hold no pandas_ta port, so a Gate E run cannot see them.
"""
import csv
import importlib.util
from pathlib import Path

import numpy as np
import pytest
from pandas import DataFrame, Series, date_range

from .context import pandas_ta  # noqa: F401

import pandas_ta as ta
from pandas_ta.trend.j_safezone_dist import (LOOKBACK, MIN_BARS, MULT, PERIOD,
                                             j_safezone_dist)

ROOT = Path(__file__).resolve().parents[1]

N = 1500
LEVEL = 100.0
COLUMN = "J_SAFEZONE_DIST_22_2.5_3"
#: The first bar that can fire on a frame with a penetration in every
#: window, and so the warm-up.
WARMUP = MIN_BARS - 1
FIRED = N - WARMUP
#: The blind causality sweep's 36 perturbation points.
OFFSETS = list(range(N - 36, N))
#: Bars a single bad LOW removes, and the arithmetic of it: the two NaN
#: penetrations at T and T+1 spoil the PERIOD + 1 = 23 rolling-sum windows
#: ending T .. T+22; `avg.shift(1)` TRANSLATES that run to T+1 .. T+23
#: without widening it; `rolling(LOOKBACK).max()` adds LOOKBACK - 1 = 2
#: more. 23 + 0 + 2 = 25 = PERIOD + LOOKBACK, bars T+1 .. T+25.
EMPTIED_BY_A_BAD_LOW = PERIOD + LOOKBACK


# ------------------------------------------------------------------ frames
# Same builders and seeds as `docs/measure_j_safezone_dist.py`, so a number
# in this file and a number in the receipt are the same measurement.


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


def _rising(n=N, level=LEVEL, step=0.001):
    """Strictly rising lows: no down-penetration anywhere, ever."""
    idx = date_range("2020-01-01", periods=n, freq="h")
    lo = Series(level * (1.0 + step * np.arange(n)), index=idx)
    return lo * 1.004, lo, lo * 1.002


FRAMES = {
    "walk": _walk, "trend": _trend, "range-bound": _range_bound,
    "grid": _grid, "heavy-tailed": _heavy, "jump": _jump, "flat": _flat,
    "rising": _rising,
}
NAMES = list(FRAMES)
#: The frames with a down-penetration in every 22-bar window.
VARYING = ["walk", "trend", "range-bound", "grid", "heavy-tailed", "jump"]
#: The ones that fire nowhere, and for two different reasons.
DEAD = ["flat", "rising"]
#: Three of the six, for the sweeps: 6 mutants x 36 offsets x 2 calls each.
SWEPT = ["walk", "trend", "heavy-tailed"]


def _frame(name):
    _, low, close = FRAMES[name]()
    return low, close


def _col(name):
    return j_safezone_dist(*_frame(name))


def _scaled(frame, factor):
    low, close = frame
    return low * factor, close * factor


# ---------------------------------------------------------------- helpers


def _bit_equal(a, b):
    if not bool((a.isna() == b.isna()).all()):
        return False
    m = a.notna() & b.notna()
    return bool((a[m].to_numpy() == b[m].to_numpy()).all())


def _rel(a, b):
    m = a.notna() & b.notna()
    if not int(m.sum()):
        return float("nan")
    d = (a[m] - b[m]).abs()
    scale = b[m].abs().where(b[m].abs() > 0.0, np.nan)
    rel = (d / scale).max()
    return 0.0 if np.isnan(rel) else float(rel)


def _abs(a, b):
    m = a.notna() & b.notna()
    return float((a[m] - b[m]).abs().max()) if int(m.sum()) else float("nan")


def _spearman(a, b):
    m = a.notna() & b.notna()
    if int(m.sum()) < 3 or a[m].nunique() < 2 or b[m].nunique() < 2:
        return float("nan")
    return float(a[m].corr(b[m], method="spearman"))


# ---------------------------------------------------------------- oracles


def _oracle(low, close):
    """The issue's formula, bar by bar, sharing no code with the module."""
    lo = low.to_numpy(dtype=float)
    cl = close.to_numpy(dtype=float)
    n = lo.size
    pen = np.full(n, np.nan)
    for i in range(1, n):
        pen[i] = max(lo[i - 1] - lo[i], 0.0)
    avg = np.full(n, np.nan)
    for i in range(PERIOD - 1, n):
        window = pen[i - PERIOD + 1:i + 1]
        if np.isnan(window).any():
            continue
        hits = [p for p in window if p > 0.0]
        if hits:
            avg[i] = sum(window) / len(hits)
    raw = np.full(n, np.nan)
    for i in range(1, n):
        raw[i] = lo[i - 1] - MULT * avg[i - 1]
    stop = np.full(n, np.nan)
    for i in range(LOOKBACK - 1, n):
        window = raw[i - LOOKBACK + 1:i + 1]
        if not np.isnan(window).any():
            stop[i] = max(window)
    return Series((cl - stop) / cl, index=close.index)


def _prototype(low, close):
    """`docs/issues/screen/ind_screen_r2.py`, candidate `j_safezone_dist`,
    retyped (that file is gitignored, so it is on the owner's machine
    only). `sdiv` is inlined; the rest is the prototype's own.

        pen = (l.shift() - l).clip(lower=0)
        avg = sdiv(pen.rolling(22).sum(),
                   (pen > 0).astype(float).rolling(22).sum())
        stop = (l.shift() - 2.5 * avg.shift()).rolling(3).max()
        return (c - stop) / c
    """
    pen = (low.shift() - low).clip(lower=0)
    avg = (pen.rolling(PERIOD).sum()
           / (pen > 0).astype(float).rolling(PERIOD).sum()
           ).replace([np.inf, -np.inf], np.nan)
    stop = (low.shift() - MULT * avg.shift()).rolling(LOOKBACK).max()
    return (close - stop) / close


def _overflow_frame(route):
    """One of the three routes by which FINITE inputs can still produce an
    infinity. Same three frames as `docs/measure_j_safezone_dist.py`'s
    `_OVERFLOW_ROUTES`, and the same numbering -- the order they occur in
    the chain -- so a number here and a number in §G3 are the same
    measurement."""
    idx = date_range("2020-01-01", periods=120, freq="h")
    big = np.finfo(float).max
    if route == "subtraction":          # 1. +max to -max in one bar
        return (Series(np.where(np.arange(120) % 2 == 0, big, -big),
                       index=idx),
                Series(np.full(120, 100.0), index=idx))
    if route == "sum":                  # 2. 11 near-DBL_MAX penetrations
        return (Series(np.where(np.arange(120) % 2 == 0, big, 1.0),
                       index=idx),
                Series(np.full(120, 100.0), index=idx))
    if route == "division":             # 3. a huge stop over a tiny close
        rng = np.random.default_rng(5)
        return (Series(1e300 * (1.0 + 0.01 * rng.random(120)), index=idx),
                Series(np.full(120, 1e-300), index=idx))
    raise ValueError(route)


def _mean_over_period(low, close):
    """The OTHER reading of "mean(down-penetrations, 22)": divide by 22."""
    pen = (low.shift(1) - low).clip(lower=0.0)
    avg = pen.rolling(PERIOD, min_periods=PERIOD).mean()
    stop = (low.shift(1) - MULT * avg.shift(1)
            ).rolling(LOOKBACK, min_periods=LOOKBACK).max()
    return (close - stop) / close


# ---------------------------------------------------------------- mutants

SOURCE = ROOT / "pandas_ta" / "trend" / "j_safezone_dist.py"

#: (label, old, new). Edits to the SHIPPED source that make the OUTPUT read
#: a bar later than T. ⚠ The sizes are measured, not chosen for tidiness:
#: the stop carries two `shift(1)`s, so a one-bar lead early in the chain is
#: absorbed by them and lands on bar T's own low -- see BLIND_SPOT_MUTANTS.
CAUSALITY_MUTANTS = [
    ("pen-lead-2",
     "return (low.shift(1) - low).clip(lower=0.0)",
     "return (low.shift(-2) - low).clip(lower=0.0)"),
    ("avg-lead-2",
     "    total = pen.rolling(PERIOD, min_periods=PERIOD).sum()",
     "    total = pen.shift(-2).rolling(PERIOD, min_periods=PERIOD).sum()"),
    ("raw-lead",
     "    raw = lo.shift(1) - MULT * avg.shift(1)",
     "    raw = lo.shift(-1) - MULT * avg.shift(1)"),
    ("stop-lead-2",
     "    stop = raw.rolling(LOOKBACK, min_periods=LOOKBACK).max()",
     "    stop = raw.shift(-2).rolling(LOOKBACK, min_periods=LOOKBACK).max()"),
    ("close-lead",
     "    dist = (px - stop) / px",
     "    dist = (px.shift(-1) - stop) / px.shift(-1)"),
    ("output-early",
     "    dist = dist.where(np.isfinite(dist))",
     "    dist = dist.where(np.isfinite(dist)).shift(-1)"),
]

#: Edits that make the output read bar T's OWN low -- wrong, because the
#: stop a trader could have had in the market is yesterday's -- without
#: reading any LATER bar. The suffix sweep is blind to all five; the oracle
#: is not.
BLIND_SPOT_MUTANTS = [
    ("pen-lead-1", "return (low.shift(1) - low).clip(lower=0.0)",
     "return (low.shift(-1) - low).clip(lower=0.0)"),
    ("avg-lead-1", "    total = pen.rolling(PERIOD, min_periods=PERIOD).sum()",
     "    total = pen.shift(-1).rolling(PERIOD, min_periods=PERIOD).sum()"),
    ("stop-lead-1",
     "    stop = raw.rolling(LOOKBACK, min_periods=LOOKBACK).max()",
     "    stop = raw.shift(-1).rolling(LOOKBACK, min_periods=LOOKBACK).max()"),
    ("today-low", "    raw = lo.shift(1) - MULT * avg.shift(1)",
     "    raw = lo - MULT * avg.shift(1)"),
    ("today-avg", "    raw = lo.shift(1) - MULT * avg.shift(1)",
     "    raw = lo.shift(1) - MULT * avg"),
]

#: Not causality mutants: the two guards, removed, to price what they buy.
HITS_GUARD_OFF = ("return total / hits.where(hits > 0.0)",
                  "return total / hits")
FINITE_GUARD_OFF = ("    dist = dist.where(np.isfinite(dist))", "    pass")


def _mutant(old, new):
    src = SOURCE.read_text(encoding="utf-8")
    assert src.count(old) == 1, f"{old!r} occurs {src.count(old)} times"
    ns = {}
    exec(compile(src.replace(old, new), "<mutant>", "exec"), ns)
    return ns["j_safezone_dist"]


def _caught_at(fn, frame, j, factor=1.03):
    """Did perturbing every bar >= j move any bar < j?

    ⚠ `factor` on low AND close is not a global rescale -- the column is
    invariant under one of those, which is Gate D -- it is a rescale of a
    SUFFIX, which moves the penetration at bar j.
    """
    low, close = frame
    f = Series(np.where(np.arange(close.size) >= j, factor, 1.0),
               index=close.index)
    a = fn(low, close).iloc[:j]
    b = fn(low * f, close * f).iloc[:j]
    if not bool((a.isna() == b.isna()).all()):
        return True
    m = a.notna() & b.notna()
    return not bool((a[m].to_numpy() == b[m].to_numpy()).all())


def _sweep(fn, frame, offsets=None):
    return sum(_caught_at(fn, frame, j) for j in (offsets or OFFSETS))


def _generator_desc():
    """`docs/gen_indicator_dictionary.py`'s own `desc`, lifted out with
    `ast` and compiled alone. Importing that module runs its whole
    indicator probe, and re-typing the cut here would pin a COPY of the
    rule rather than the rule."""
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
    assert "j_safezone_dist" in ta.Category["trend"]
    assert hasattr(ta.trend, "j_safezone_dist")
    low, close = _frame("walk")
    col = j_safezone_dist(low, close)
    assert col.name == COLUMN
    assert col.category == "trend"

    df = DataFrame({"low": low.to_numpy(), "close": close.to_numpy()})
    out = df.ta.j_safezone_dist()
    assert out.name == COLUMN
    assert out.equals(j_safezone_dist(low.reset_index(drop=True),
                                      close.reset_index(drop=True)))


def test_the_source_library_is_not_installed_here():
    """Gate A reads the issue's QUOTE of jesse, not jesse. Recorded as a
    test so the claim cannot rot into "checked against jesse" once someone
    pip-installs it."""
    assert importlib.util.find_spec("jesse") is None


def test_the_constants_are_the_issues_numbers():
    """"(22, 2.5, lookback 3)", and nothing else is configurable."""
    assert (PERIOD, MULT, LOOKBACK) == (22, 2.5, 3)
    assert MIN_BARS == PERIOD + LOOKBACK + 1
    assert COLUMN == f"J_SAFEZONE_DIST_{PERIOD}_{MULT}_{LOOKBACK}"
    import inspect
    params = list(inspect.signature(j_safezone_dist).parameters)
    assert params == ["low", "close", "offset", "kwargs"]


def test_a_frame_shorter_than_min_bars_is_refused():
    """`MIN_BARS` is also the index of the first firing bar, so the shortest
    frame that computes fires on exactly one."""
    low, close = _frame("walk")
    assert j_safezone_dist(low.iloc[:MIN_BARS - 1],
                           close.iloc[:MIN_BARS - 1]) is None
    exact = j_safezone_dist(low.iloc[:MIN_BARS], close.iloc[:MIN_BARS])
    assert int(exact.notna().sum()) == 1
    assert int(exact.notna().to_numpy().argmax()) == MIN_BARS - 1


def test_offset_and_fillna():
    low, close = _frame("walk")
    base = j_safezone_dist(low, close)
    assert _bit_equal(j_safezone_dist(low, close, offset=2), base.shift(2))
    filled = j_safezone_dist(low, close, fillna=0.0)
    assert int(filled.isna().sum()) == 0
    assert float(filled.iloc[0]) == 0.0


# -------------------------------------------------------------- Gate A


@pytest.mark.parametrize("name", VARYING)
def test_gate_a_matches_the_issues_formula_spelled_independently(name):
    """1,475 of 1,475 bars of each frame, measured bit-equal, asserted at
    1e-12 on both scales: `rolling.sum` and a `sum()` over a slice are not
    obliged to round the same way, and a reduced numpy kernel may not."""
    low, close = _frame(name)
    got, want = j_safezone_dist(low, close), _oracle(low, close)
    assert bool((got.isna() == want.isna()).all())
    assert int(got.notna().sum()) == FIRED == 1475
    assert _abs(got, want) < 1e-12
    assert _rel(got, want) < 1e-12


@pytest.mark.parametrize("name", NAMES)
def test_gate_a_is_bit_equal_to_the_screen_prototype(name):
    """The limb that ties this port to the screen's Gate E figures. The
    module adds two guards the prototype has not; on a clean frame both are
    no-ops, which is what this asserts. Bit-equality is legitimate here
    because the operations and their order are identical."""
    low, close = _frame(name)
    assert _bit_equal(j_safezone_dist(low, close), _prototype(low, close))


def test_the_warm_up_is_the_chain_of_windows_and_shifts():
    """`pen` at 1, `avg` at PERIOD, `raw` at PERIOD + 1, `stop` and the
    column at PERIOD + LOOKBACK. Spelled as the chain rather than as the
    number 25, so a changed constant moves it."""
    low, close = _frame("walk")
    pen = (low.shift(1) - low).clip(lower=0.0)
    total = pen.rolling(PERIOD, min_periods=PERIOD).sum()
    hits = (pen > 0.0).astype(float).rolling(PERIOD, min_periods=PERIOD).sum()
    avg = total / hits.where(hits > 0.0)
    raw = low.shift(1) - MULT * avg.shift(1)
    stop = raw.rolling(LOOKBACK, min_periods=LOOKBACK).max()

    def first(s):
        return int(s.notna().to_numpy().argmax())

    assert first(pen) == 1
    assert first(avg) == PERIOD
    assert first(raw) == PERIOD + 1
    assert first(stop) == PERIOD + LOOKBACK
    assert first(j_safezone_dist(low, close)) == WARMUP == PERIOD + LOOKBACK


@pytest.mark.parametrize("name", VARYING)
def test_the_per_22_mean_would_be_a_different_column(name):
    """Dividing by 22 instead of by the number of penetrations is a smaller
    mean, so a HIGHER stop and a SMALLER distance -- on every shared bar,
    not on average."""
    low, close = _frame(name)
    ship, alt = j_safezone_dist(low, close), _mean_over_period(low, close)
    m = ship.notna() & alt.notna()
    assert int(m.sum()) == FIRED
    assert bool((ship[m] > alt[m]).all())
    assert 0.90 < _spearman(ship, alt) < 0.99
    assert _abs(ship, alt) > 1e-3


def test_the_per_22_mean_answers_where_this_column_must_not():
    """The sharper difference, and the reason the reading is load-bearing:
    on a frame with no down-penetration at all the alternative still
    returns a number."""
    low, close = _frame("rising")
    assert int(j_safezone_dist(low, close).notna().sum()) == 0
    assert int(_mean_over_period(low, close).notna().sum()) == FIRED


# -------------------------------------------------------------- Gate B


@pytest.mark.parametrize("name", VARYING)
def test_the_module_is_never_caught_by_the_future_sweep(name):
    assert _sweep(j_safezone_dist, _frame(name)) == 0


@pytest.mark.parametrize("label,old,new", CAUSALITY_MUTANTS,
                         ids=[m[0] for m in CAUSALITY_MUTANTS])
@pytest.mark.parametrize("name", SWEPT)
def test_every_mutant_is_live_before_it_is_caught(label, old, new, name):
    """A mutant that changes nothing would be caught at 0 offsets for the
    honest reason, which would make the sweep look clean and prove nothing.
    """
    frame = _frame(name)
    a, b = j_safezone_dist(*frame), _mutant(old, new)(*frame)
    m = a.notna() & b.notna()
    assert int(m.sum()) > 0
    assert not bool((a[m].to_numpy() == b[m].to_numpy()).all())


@pytest.mark.parametrize("label,old,new", CAUSALITY_MUTANTS,
                         ids=[m[0] for m in CAUSALITY_MUTANTS])
@pytest.mark.parametrize("name", SWEPT)
def test_each_mutant_is_caught_by_the_future_sweep(label, old, new, name):
    """⚠ Asserted as "at least one offset", not as 36 of 36, and that is a
    measurement rather than caution: the counts run 3 .. 36 over the six
    frames because `clip(lower=0)`, the mean over the hits and
    `rolling(3).max()` all discard information, so a 3% suffix lift moves
    the output only where the perturbed bar is one those operators select.
    """
    assert _sweep(_mutant(old, new), _frame(name)) >= 1


@pytest.mark.parametrize("label,old,new", CAUSALITY_MUTANTS,
                         ids=[m[0] for m in CAUSALITY_MUTANTS])
def test_each_mutant_is_caught_loudly_not_marginally(label, old, new):
    """A catch of one bar by 1e-16 would be a rounding accident. Measured
    3.4e-04 .. 3.0e-02 at the first caught offset; asserted at 1e-5, which
    is still five orders above the 4.091e-11 an inexact rescale costs
    (§D2)."""
    fn = _mutant(old, new)
    low, close = _frame("walk")
    for j in OFFSETS:
        f = Series(np.where(np.arange(close.size) >= j, 1.03, 1.0),
                   index=close.index)
        a, b = fn(low, close).iloc[:j], fn(low * f, close * f).iloc[:j]
        if _caught_at(fn, (low, close), j):
            assert _abs(a, b) > 1e-5
            return
    pytest.fail(f"{label} was never caught, so its loudness is undefined")


@pytest.mark.parametrize("label,old,new", BLIND_SPOT_MUTANTS,
                         ids=[m[0] for m in BLIND_SPOT_MUTANTS])
def test_the_sweeps_blind_spot_is_pinned_and_the_oracle_covers_it(label, old,
                                                                  new):
    """Five edits that make the output read bar T's OWN low. None reads a
    later bar, so the sweep catches none of them -- pinned in BOTH
    directions, because a sweep that started catching them would mean the
    module's shift structure had changed. Gate A's oracle rejects all
    five."""
    fn = _mutant(old, new)
    for name in ("walk", "heavy-tailed"):
        frame = _frame(name)
        assert _sweep(fn, frame) == 0
        assert not _bit_equal(fn(*frame), _oracle(*frame))
        assert _abs(fn(*frame), _oracle(*frame)) > 1e-3


# ---------------------------------------------------------- Gates C and D


@pytest.mark.parametrize("name", VARYING)
def test_reachability_on_the_varying_frames(name):
    col = _col(name)
    assert int(col.notna().sum()) == FIRED
    assert bool(col.iloc[:WARMUP].isna().all())
    # Not a constant, and not a handful of repeated values either.
    assert int(col.dropna().nunique()) > FIRED - 10
    assert int((col.dropna() == 0.0).sum()) == 0
    assert int((col.dropna() < 0.0).sum()) > 0


@pytest.mark.parametrize("name", DEAD)
def test_a_frame_with_no_down_penetration_reads_nothing(name):
    """`flat` and `rising` fire NOWHERE, for two different reasons, and
    that is the column's shape rather than a defect: `avg` is the mean over
    the bars that HAD a penetration. ⚠ `rising` is the sharp one -- every
    bar of it moves."""
    col = _col(name)
    assert int(col.notna().sum()) == 0
    assert len(col) == N


def test_the_missingness_is_not_missing_at_random():
    """The consumer-facing form of the same fact, measured rather than
    argued: blank the drawdowns out of a walk and the column goes with
    them."""
    low, close = _frame("walk")
    assert int(j_safezone_dist(low, close).notna().sum()) == FIRED
    monotone = Series(np.maximum.accumulate(low.to_numpy()), index=low.index)
    assert int(j_safezone_dist(monotone, close).notna().sum()) == 0


@pytest.mark.parametrize("factor", [8.0, 64.0])
@pytest.mark.parametrize("name", VARYING)
def test_gate_d_scale_x8_x64_is_bit_identical(name, factor):
    frame = _frame(name)
    assert _bit_equal(j_safezone_dist(*frame),
                      j_safezone_dist(*_scaled(frame, factor)))


@pytest.mark.parametrize("factor", [10.0, 3.7, 0.1, 1.0000001])
@pytest.mark.parametrize("name", VARYING)
def test_gate_d_scale_tolerance_for_inexact_factors(name, factor):
    """Measured worst cell 4.091e-11 over the 24 (frame, factor) cells, and
    6.546e-11 over the same 24 under reduced CPU dispatch -- the one figure
    outside the receipt's wall-clock section that moves that way. Asserted
    1e-9, which is more than an order above both."""
    frame = _frame(name)
    base = j_safezone_dist(*frame)
    moved = j_safezone_dist(*_scaled(frame, factor))
    assert bool((base.isna() == moved.isna()).all())
    assert _rel(moved, base) < 1e-9


@pytest.mark.parametrize("factor", [8.0, 64.0])
@pytest.mark.parametrize("level", [1e-6, 1e6, 1e100])
def test_gate_d_scale_at_extreme_price_levels(level, factor):
    """⚠ BOTH factors, not just x8. An earlier draft asserted x64 at these
    levels on four prose surfaces while only x8 had been run. The headroom
    is MEASURED, not reasoned, and over all six cells rather than three:
    the largest intermediate anywhere in the chain is 6.419e+101 against
    DBL_MAX 1.798e+308, a factor of 2.800e+206 (§D3). An earlier draft of
    that sentence said "four orders"; the one after it quoted the figure
    over six cells when three had been walked."""
    low, close = _frame("walk")
    frame = (low / LEVEL * level, close / LEVEL * level)
    base = j_safezone_dist(*frame)
    assert int(base.notna().sum()) == FIRED
    assert _bit_equal(base, j_safezone_dist(*_scaled(frame, factor)))


@pytest.mark.parametrize("name", VARYING)
def test_gate_d_fires_are_strictly_between_zero_and_n(name):
    col = _col(name)
    assert 0 < int(col.notna().sum()) < len(col)


@pytest.mark.parametrize("name", VARYING)
def test_a_level_shift_moves_every_fired_bar(name):
    """The check that keeps the x8 bit-identity from being vacuous: the
    column is invariant under a RESCALE and not under a SHIFT, so it reads
    a ratio rather than nothing at all."""
    low, close = _frame(name)
    base = j_safezone_dist(low, close)
    moved = j_safezone_dist(low + 10.0, close + 10.0)
    m = base.notna() & moved.notna()
    assert int(m.sum()) == FIRED
    assert int((base[m] != moved[m]).sum()) == FIRED


# --------------------------------------------------- guards and bad data


@pytest.mark.parametrize("value", [np.nan, np.inf, -np.inf])
@pytest.mark.parametrize("leg", ["low", "close"])
@pytest.mark.parametrize("j", [100, 400, 700, 1100])
def test_a_bad_price_empties_an_exact_window_of_bars(leg, value, j):
    """⚠ Unlike `j_damiani`, a bad price here DOES empty bars, and the count
    is exact and the same for NaN, +inf and -inf. A bad LOW takes bars
    T+1 .. T+25; a bad CLOSE takes its own bar and no other. Everything
    before the first emptied bar is bit-identical, which is the other half
    of the claim."""
    low, close = _frame("walk")
    base = j_safezone_dist(low, close)
    lo, cl = low.copy(), close.copy()
    (lo if leg == "low" else cl).iloc[j] = value
    col = j_safezone_dist(lo, cl)

    gone = np.flatnonzero((base.notna() & col.isna()).to_numpy())
    if leg == "close":
        assert gone.tolist() == [j]
    else:
        assert gone.tolist() == list(range(j + 1,
                                           j + 1 + EMPTIED_BY_A_BAD_LOW))
    assert _bit_equal(base.iloc[:j], col.iloc[:j])


@pytest.mark.parametrize("value", [np.nan, np.inf, -np.inf])
def test_a_bad_low_at_the_last_bar_empties_nothing(value):
    """The frame ends before the 25 bars do."""
    low, close = _frame("walk")
    lo = low.copy()
    lo.iloc[-1] = value
    assert _bit_equal(j_safezone_dist(low, close), j_safezone_dist(lo, close))


@pytest.mark.parametrize("name", NAMES)
def test_the_hits_guard_changes_no_reading(name):
    """`total > 0` implies `hits > 0`, because a counted penetration is
    positive, so the bare form's only division by zero is `0/0` -- NaN
    either way. What the guard buys is that the decision is this module's
    rather than numpy's."""
    frame = _frame(name)
    assert _bit_equal(j_safezone_dist(*frame), _mutant(*HITS_GUARD_OFF)(*frame))


@pytest.mark.parametrize("name", NAMES)
def test_the_finite_guard_changes_no_reading_on_a_real_price_scale(name):
    frame = _frame(name)
    assert _bit_equal(j_safezone_dist(*frame),
                      _mutant(*FINITE_GUARD_OFF)(*frame))


def test_the_finite_guard_is_not_a_no_op_where_the_division_overflows():
    """And the frame where it earns its line: lows near DBL_MAX over closes
    near DBL_MIN. Measured 95 infinite readings of 120 without it, 0 with
    it. This is route 3 of §G3's three, the only one that reaches the
    output."""
    lo, cl = _overflow_frame("division")
    with np.errstate(over="ignore", invalid="ignore"):
        guarded = j_safezone_dist(lo, cl)
        bare = _mutant(*FINITE_GUARD_OFF)(lo, cl)
    assert int(np.isinf(guarded).sum()) == 0
    assert int(np.isinf(bare).sum()) > 0


@pytest.mark.parametrize("route", ["subtraction", "sum"])
def test_routes_1_and_2_never_reach_the_output(route):
    """⚠ Finite inputs leave THREE arithmetic routes to an infinity, not
    one, and an earlier draft of the module docstring said the division was
    the only one. They are numbered in §G3 in the order they occur in the
    chain: route 1 is `low.shift(1) - low` (which needs a NEGATIVE low, and
    the input guard allows one), route 2 is `pen.rolling(22).sum()` with
    eleven penetrations near DBL_MAX in a window, route 3 is the final
    division. Measured: neither 1 nor 2 reaches the output, with OR without
    the final mask, because they die in the rolling sum (next test)."""
    lo, cl = _overflow_frame(route)
    with np.errstate(over="ignore", invalid="ignore"):
        guarded = j_safezone_dist(lo, cl)
        bare = _mutant(*FINITE_GUARD_OFF)(lo, cl)
    assert int(np.isinf(guarded).sum()) == 0
    assert int(np.isinf(bare).sum()) == 0
    assert int(guarded.notna().sum()) == 0


def test_the_rolling_sums_overflow_behaviour_is_not_uniform():
    """The pandas BEHAVIOUR the previous test rests on, pinned separately
    AND pinned as the non-rule it is.

    ⚠ Both probes are 81 bars with the bad value in the MIDDLE, because
    `min_periods` blanks `PERIOD - 1` = 21 windows of ANY frame and a
    31-bar probe with the bad value at bar 0 cannot tell those 21 from
    the contamination. An earlier draft of this test used such a frame
    and read its 22 NaNs as 22 contaminated windows.

    Measured, and the second row is the finding:

    * one `+inf` at bar 40 -> 0 infinite readings, and all 22 windows
      that hold it (bars 40 .. 61) are NaN;
    * two DBL_MAX at bars 40 and 41 -> **1 infinite reading**, the window
      in which the overflow first happens, with only the 21 after it
      (bars 42 .. 62) NaN.

    So "the compensated sum absorbs an overflow" is true of §G3's routes
    1 and 2 and is NOT a rule. That is why the module keeps its final
    finite mask, and why `test_routes_1_and_2_never_reach_the_output`
    asserts the MODULE's output rather than this internal.
    """
    big = np.finfo(float).max
    with np.errstate(over="ignore", invalid="ignore"):
        one_inf = Series([1.0] * 40 + [np.inf] + [1.0] * 40).rolling(
            PERIOD, min_periods=PERIOD).sum()
        two_big = Series([1.0] * 40 + [big] * 2 + [1.0] * 39).rolling(
            PERIOD, min_periods=PERIOD).sum()

    def _blanked(s):
        idx = np.flatnonzero(s.isna().to_numpy())
        return [int(i) for i in idx if i >= PERIOD - 1]

    assert int(np.isinf(one_inf).sum()) == 0
    assert _blanked(one_inf) == list(range(40, 40 + PERIOD))
    assert int(np.isinf(two_big).sum()) == 1
    assert _blanked(two_big) == list(range(42, 42 + PERIOD - 1))


@pytest.mark.parametrize("value", [0.0, -100.0, 5e-310, 1e308])
def test_a_degenerate_frame_raises_nothing_and_ships_nothing_infinite(value):
    """A constant frame of any of these four reads NaN everywhere -- there
    is no penetration in a constant series -- and raises nothing on the
    way."""
    idx = date_range("2020-01-01", periods=60, freq="h")
    s = Series(np.full(60, value), index=idx)
    with np.errstate(all="ignore"):
        col = j_safezone_dist(s, s)
    assert int(col.notna().sum()) == 0
    assert int(np.isinf(col).sum()) == 0


@pytest.mark.parametrize("n", [0, 1, 5, MIN_BARS - 1])
def test_a_frame_below_min_bars_is_refused_at_every_length(n):
    """Including the empty and one-bar indexes, which §G5 prints."""
    s = Series(np.full(n, 100.0),
               index=date_range("2020-01-01", periods=n, freq="h"))
    assert j_safezone_dist(s, s) is None


def test_an_all_nan_frame_is_empty_rather_than_an_error():
    s = Series(np.full(100, np.nan),
               index=date_range("2020-01-01", periods=100, freq="h"))
    col = j_safezone_dist(s, s)
    assert int(col.notna().sum()) == 0


def test_a_non_positive_close_is_dropped_rather_than_sign_flipped():
    """The close is a DIVISOR, so a zero flips the column to an infinity
    and a negative one flips its sign. Both are dropped, and the bars
    around them are untouched."""
    low, close = _frame("walk")
    base = j_safezone_dist(low, close)
    for bad in (0.0, -50.0):
        cl = close.copy()
        cl.iloc[700] = bad
        col = j_safezone_dist(low, cl)
        assert bool(col.isna().iloc[700])
        assert _bit_equal(base.drop(base.index[700]),
                          col.drop(col.index[700]))


# -------------------------------------------------- documentation surface


def test_the_docstrings_first_paragraph_survives_the_dictionary_cut():
    """`docs/IndicatorDictionary.md` is what CLAUDE.md tells a reader to
    consult before judging a column, and it prints the first paragraph cut
    at 150 characters. A cut sentence there is how a column gets
    misunderstood."""
    doc = j_safezone_dist.__doc__.splitlines()
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
    assert "Elder" in cut and "stop" in cut


def test_the_receipt_states_that_gate_e_is_pending():
    """The receipt is the deliverable issue #121 asks for, and a pending
    Gate E has to say so in it rather than only in a commit message."""
    doc = (ROOT / "docs" / "JSafezoneDistMeasured.md").read_text(
        encoding="utf-8")
    assert "Gate E: pending, run by issue-solver after this session" in doc
    assert "0.7059" in doc          # the screen's PROTOTYPE figure
    assert "r3-perframe-0.90" in doc


def test_the_gate_e_row_is_owed_and_not_yet_recorded():
    """Gate E is run by issue-solver after this session; the receipt
    session records the row and replaces this test."""
    path = ROOT / "docs" / "gate_e_ledger.csv"
    with path.open(newline="", encoding="utf-8") as handle:
        rows = [r for r in csv.DictReader(handle)
                if r["indicator"] == "j_safezone_dist"]
    assert rows == []
