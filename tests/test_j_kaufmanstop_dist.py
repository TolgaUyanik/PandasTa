# -*- coding: utf-8 -*-
"""J-KAUFMANSTOP-DIST: `j_kaufmanstop_dist`, the distance to Kaufman's long
stop (PandasTa issue #124).

    rng[T]  = high[T] - low[T]
    avg[T]  = mean(rng[T-21..T])                                  SMA 22
    stop[T] = low[T] - 2 * avg[T]
    J_KAUFMANSTOP_DIST[T] = (close[T] - stop[T]) / close[T]

WHAT THIS FILE PINS, in order of how much it would hurt to lose.

1. **Gate A against the issue's formula, spelled independently, with
   TA-Lib as the third speller.** A bar-by-bar oracle -- its own range
   loop, its own naive 22-term window sum over plain Python floats,
   sharing no code with the module -- is **bit-equal** on **1,479 of
   1,479** fired bars of each of six varying frames (8,874 pooled) with
   identical NaN masks. ⚠ The ASSERTION is 1e-12 absolute and 1e-9
   relative rather than the bit-equality: the frames are built with
   `np.exp`/`np.cumsum`, so a reduced numpy kernel can move a price in its
   last bits. The measured figure is **0.0** under both dispatches.
   `(close - (low - 2 * talib.SMA(high - low, 22))) / close` is bit-equal
   on all six frames at Spearman 1.0000, and `talib.SMA(high - low, 22)`,
   this module's `sma` and the column all first fire at bar **21** -- so
   the warm-up is run rather than recalled. That test SKIPS where talib is
   absent rather than passing silently.
   ⚠ jesse is not installed here and web access is unavailable
   (`test_the_source_library_is_not_installed_here` records it). What Gate
   A checks is the formula issue #124 quotes, and nothing in this file is a
   claim about what jesse's code computes.

2. **THE SCREEN PROTOTYPE IS THIS COLUMN'S ARITHMETIC, BIT FOR BIT**, on
   all **nine** test frames, and that is MEASURED (`test_the_screen_
   prototype_is_this_columns_arithmetic`) rather than inferred from the two
   quotes reading alike. `docs/issues/screen/ind_screen_r2.py`'s candidate
   is `(c - (l - 2 * mean(h - l, 22))) / c` and `ind_screen.py`'s
   `mean(x, n)` is `x.rolling(n).mean()`, the same call `sma` makes. ⚠ This
   is the OPPOSITE of `j_chandelier_dist`, whose prototype used an unseeded
   ATR and so described a neighbouring column. So the screen's
   DISCLOSE_GAP figures are this arithmetic's -- on 89 real frames and
   through an engine this worktree cannot read.

3. **The other readings are other columns, and one of them is a measured
   no-op.** `sma` is bit-equal to the `rolling(22, min_periods=22).mean()`
   it makes on all nine frames, so the import costs nothing. An `SMA22`
   over the TRUE range differs on 1,478 of 1,479 bars by up to 5.6e-02 at
   Spearman 0.279 .. 0.534; an `EMA22` on all 1,479 by up to 1.3e-03; the
   stop off YESTERDAY's low on 1,473 .. 1,479 by up to 3.2e-01 at Spearman
   -0.075 .. 0.020. `high - low` through `non_zero_range` is **bit-equal**
   at a price level of 100 even on the frame with 215 tied bars and the
   flat one with 1,500 -- so the plain subtraction buys nothing there --
   and at 1e-6 the variant **fails** Gate D's x8 and x64 cells on the tied
   frame while this module holds.

4. **Gate B is the sweep AND the oracle, because the sweep alone has a
   measured blind spot.** The module is caught at **0 of 36** perturbation
   offsets on each of six frames. Six look-ahead mutants are read off the
   shipped source, edited and `exec`'d in memory; every one is live and
   caught on **36 of 36** offsets of each of three frames, the first catch
   moving a bar by **1.379e-05 .. 3.023e-02** (asserted at 1e-6, which is
   still 1.9e+07× the 5.160e-14 an inexact rescale costs — seven orders,
   not the eight three files said until round 4 of the review divided it
   out).
   ⚠ **The blind spot, pinned rather than left for a reader to find.**
   Three edits LAG a leg -- the high inside the range, the average, the
   low under the stop. None reads a later bar, so the sweep catches **0 of
   36** of them; Gate A's oracle rejects all three, by **6.152e-04 ..
   3.224e-01**. The backward direction is pinned too: nothing reads before
   `T - 21`, so truncating a frame at bar 500 leaves all **979** bars from
   521 on bit-equal.

5. **Gates C and D.** Every frame fires on 1,479 of 1,500 bars; each of
   the six varying ones has 1,479 distinct values; x8/x64 is bit-identical
   on all nine at a price level of 100 and on **all nine at each of
   1e-6, 1e+6 and 1e+100** — 54 cells, which is what round 1 of the review
   asked for after finding the prose saying nine over a test that ran one;
   x10/x3.7/x0.1/x1.0000001 within **5.160e-14** relative, so the bound is
   asserted at 1e-9; `0 < fires < n` on all nine; and a level SHIFT of +10
   moves all 1,479 fired bars of the six, so the bit-identity is not
   vacuous.
   ⚠ **This column does not change sign**, which is where it parts from
   both sibling stop distances: `(close - stop)/close` is
   `(close - low)/close + 2*avg/close`, two non-negative terms on
   well-formed OHLC. Measured **0.005961 .. 0.014415** over the six,
   positive on all 8,874 bars and exactly 0.0 on none. So the signal is
   the SIZE, and `test_the_column_does_not_change_sign` pins that rather
   than a negative count.
   ⚠ A FLAT frame is the exception twice over and is pinned separately: it
   fires on all 1,479, reads exactly **0.0** on every one, and the +10
   level shift moves **0** of its bars. So "not a constant column" and
   "the shift moves everything" are both asserted on the varying frames.

6. **A bad price empties a BOUNDED window and moves nothing after it.**
   One NaN, +inf or -inf high or low blanks exactly bars
   `max(T, 21) … min(T+21, n-1)` and leaves **0** of the remaining bars
   moved; a bad close blanks exactly its own bar, or **0** bars inside the
   warm-up, and moves **0** later bars. Measured at five plant points ×
   three values = **15 cells per leg**: 22 bars blanked at 100, 700 and
   1,100, **5** at 1,495 where the frame runs out, and **6** at 5 (bars
   21 … 26, because bars 5 … 20 never fired). ⚠ Both boundaries came from
   the review: the right edge from round 1, the left from round 2, which
   found it still missing after the first fix. ⚠ The no-later-bar-moves
   half is the opposite of `j_chandelier_dist`, where a bad low blanked
   nothing and moved a bounded RUN of later bars, and the reason is
   structural: there is no recursion in this chain.

7. **Five guards, and the measurement says only two of them carry a
   load.** All five are no-ops on all nine ordinary frames. ⚠ **The three
   input finite guards are measured no-ops even on the probes built to
   reach them**: `+inf`, `-inf` and NaN planted in each leg at bar 700 of a
   `walk` leave the column BIT-EQUAL with the guard removed, in all nine
   cells. What absorbs a bad high or low is pandas' rolling window -- an
   infinite observation makes the window NaN -- pinned on its own by
   `test_a_pandas_rolling_mean_turns_an_infinite_observation_into_nan`, and
   sharpened by `test_no_rolling_aggregation_can_propagate_an_infinity`:
   `sma`, `rolling(...).apply(np.mean)` and `rolling(...).max()` all read
   NaN at a planted `+inf` while a numpy window mean reads inf, which puts
   the conversion before the aggregation. ⚠ Three aggregations measured,
   and pandas' source not read -- round 3 of the review caught a draft
   naming the internal that does it.
   ⚠ An upgrade dropping that absorption would fail **two** tests, and
   earlier drafts of this file said one in four places until round 2 of the
   review counted them: the `..._into_nan` one above, and
   `test_route_1_never_reaches_the_output`, whose 0 infinite readings are
   the same absorption --
   `test_route_1s_zero_is_the_absorption_and_would_move_without_it`
   measures route 1 shipping **99 of 120** under a propagating mean.
   ⚠ It would NOT fail the guard tests:
   `test_the_guards_stay_no_ops_even_if_the_rolling_mean_propagates`
   measures the three guards still bit-equal no-ops in all six cells, which
   is round 1's refuted inference turned into a run.
   The close-is-positive guard IS load-bearing: without it a close of -50
   fires and reads **1.924**, a sign flip in a column whose every other bar
   is 0.006 .. 0.014. And the final finite mask is the only thing between
   this column and **99 infinite readings of 120** on two of the three
   arithmetic routes an infinity can take from FINITE inputs; the third
   route ships nothing, and that asymmetry is pinned route by route.

8. **Gate E is OWED, not measured.** The screen measured the PROTOTYPE --
   which item 2 measures bit-equal to this module -- at max |rho| 0.8776
   vs the engine's `natr` (DISCLOSE_GAP, n = 396,980, per-frame max median
   0.8601). The port's own run is the launcher's, after this session;
   `test_no_gate_e_row_is_recorded_yet` and
   `test_the_receipt_says_gate_e_is_pending` are the receipt session's cue,
   and both are expected to be REPLACED then rather than to keep passing.

Every number above is printed by `python docs/measure_j_kaufmanstop_dist.py`
and by `python docs/measure_j_kaufmanstop_dist_cpu.py <section>` under
numpy's reduced CPU dispatch -- with the exceptions
`docs/JKaufmanstopDistMeasured.md` lists above its §A1, of which one matters
here: the ASSERTED bounds quoted next to a measurement (1e-12 and 1e-9 in
item 1, 1e-6 in item 4, 1e-9 in item 5 — those four, counted) are this
file's own constants rather than run output. The measured figure beside each
of them is a run.

NOT pinned here: Gate E's own arithmetic (the launcher runs it; 687
comparators over 89 real BIST frames, re-derived by
`tests/test_gate_e_ledger.py`), and Gate C's real-data limb, which comes
from the same run -- every frame in this file is synthetic. The in-fork
overlap figures of §L are SYNTHETIC and are disclosures, not gates, and here
they are **LOW rather than high**: `natr`, the one comparator with both a
synthetic and a real figure, reads 0.1092 against the screen's 0.8611, so
these six frames understate by 0.75 and cannot stand in for Gate E in
either direction. ⚠ §L is also not blind to Gate E -- `natr` is the
screen's own top comparator -- and whether the engine computes it through
this fork was not checked in this repo.
"""
import csv
import importlib.util
from pathlib import Path

import numpy as np
import pytest
from pandas import DataFrame, Series, date_range

from .context import pandas_ta  # noqa: F401

import pandas_ta as ta
from pandas_ta.overlap.sma import sma
from pandas_ta.trend.j_kaufmanstop_dist import (MIN_BARS, MULT, PERIOD,
                                                j_kaufmanstop_dist)
from pandas_ta.utils import non_zero_range
from pandas_ta.volatility.true_range import true_range

ROOT = Path(__file__).resolve().parents[1]

N = 1500
LEVEL = 100.0
COLUMN = "J_KAUFMANSTOP_DIST_22_2.0"
#: The first bar that can fire on a clean frame, and so the warm-up: the
#: SMA needs PERIOD ranges and the range is defined at bar 0.
WARMUP = MIN_BARS - 1
FIRED = N - WARMUP
#: The blind causality sweep's 36 perturbation points.
OFFSETS = list(range(N - 36, N))
#: Bars a single bad HIGH or LOW removes: the range at T is in exactly the
#: PERIOD windows of `sma(high - low, PERIOD)` that end at T .. T+PERIOD-1.
EMPTIED_BY_A_BAD_RANGE_LEG = PERIOD


# ------------------------------------------------------------------ frames
# Same builders and seeds as `docs/measure_j_kaufmanstop_dist.py`, so a
# number in this file and a number in the receipt are the same measurement.


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
    idx = date_range("2020-01-01", periods=n, freq="h")
    lo = Series(level * (1.0 + step * np.arange(n)), index=idx)
    return lo * 1.004, lo, lo * 1.002


def _tied(seed=29, n=N, level=LEVEL, every=7):
    """A walk with a doji every `every` bars -- `high == low == close`, the
    bar `non_zero_range` exists for and a legitimate zero-range bar here."""
    h, l, c = _walk(seed, n, level)
    doji = np.arange(n) % every == 0
    return h.where(~doji, c), l.where(~doji, c), c


FRAMES = {
    "walk": _walk, "trend": _trend, "range-bound": _range_bound,
    "grid": _grid, "heavy-tailed": _heavy, "jump": _jump, "flat": _flat,
    "rising": _rising, "tied": _tied,
}
NAMES = list(FRAMES)
#: The six frames whose prices vary in both directions.
VARYING = ["walk", "trend", "range-bound", "grid", "heavy-tailed", "jump"]
#: Three of the six, for the sweeps: 6 mutants x 36 offsets x 2 calls each.
SWEPT = ["walk", "trend", "heavy-tailed"]


def _frame(name):
    return FRAMES[name]()


def _col(name):
    return j_kaufmanstop_dist(*_frame(name))


def _scaled(frame, factor):
    high, low, close = frame
    return high * factor, low * factor, close * factor


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


def _differing_bars(a, b):
    m = a.notna() & b.notna()
    return int((a[m].to_numpy() != b[m].to_numpy()).sum())


# ---------------------------------------------------------------- oracles


def _oracle(high, low, close):
    """The issue's formula bar by bar over plain Python floats, sharing no
    code with the module: a naive 22-term window sum rather than pandas'
    compensated running one."""
    h = high.to_numpy(dtype=float)
    l = low.to_numpy(dtype=float)
    c = close.to_numpy(dtype=float)
    n = h.size
    nan = float("nan")
    rng = [h[i] - l[i] for i in range(n)]
    out = [nan] * n
    for i in range(PERIOD - 1, n):
        window = rng[i - PERIOD + 1:i + 1]
        if any(x != x for x in window):
            continue
        stop = l[i] - MULT * (sum(window) / PERIOD)
        if c[i] == c[i]:
            out[i] = (c[i] - stop) / c[i]
    return Series(out, index=close.index)


def _prototype(high, low, close):
    """`docs/issues/screen/ind_screen_r2.py`, candidate `j_kaufmanstop_dist`,
    retyped from the read-only copy this worktree carries (that tree is
    gitignored):

        (c - (l - 2 * mean(h - l, 22))) / c

    with `ind_screen.py`'s `mean(x, n) = x.rolling(n).mean()`.
    """
    return (close - (low - 2 * (high - low).rolling(22).mean())) / close


def _alt_inline_mean(high, low, close):
    avg = (high - low).rolling(PERIOD, min_periods=PERIOD).mean()
    return (close - (low - MULT * avg)) / close


def _alt_non_zero_range(high, low, close):
    """The same column with `high - low` through `non_zero_range`, i.e. with
    its ABSOLUTE epsilon."""
    avg = sma(non_zero_range(high, low), length=PERIOD)
    return (close - (low - MULT * avg)) / close


def _alt_true_range(high, low, close):
    avg = sma(true_range(high=high, low=low, close=close), length=PERIOD)
    return (close - (low - MULT * avg)) / close


def _alt_ema(high, low, close):
    avg = (high - low).ewm(span=PERIOD, adjust=True,
                           min_periods=PERIOD).mean()
    return (close - (low - MULT * avg)) / close


def _alt_prev_low(high, low, close):
    avg = sma(high - low, length=PERIOD)
    return (close - (low.shift(1) - MULT * avg)) / close


def _overflow_frame(route):
    """One of the three routes by which FINITE inputs can still produce an
    infinity. Same three frames and the same numbering -- the order they
    occur in the chain -- as `docs/measure_j_kaufmanstop_dist.py`'s
    `_overflow_routes`."""
    idx = date_range("2020-01-01", periods=120, freq="h")
    big = float(np.finfo(float).max)
    n = 120
    if route == "range":
        return (Series(np.full(n, big), index=idx),
                Series(np.full(n, -big), index=idx),
                Series(np.full(n, 1.0), index=idx))
    if route == "stop":
        return (Series(np.full(n, big / 2.0), index=idx),
                Series(np.full(n, -big / 2.0), index=idx),
                Series(np.full(n, 1.0), index=idx))
    if route == "division":
        rng = np.random.default_rng(5)
        return (Series(1e300 * (1.0 + 0.01 * rng.random(n)), index=idx),
                Series(-1e300 * (1.0 + 0.01 * rng.random(n)), index=idx),
                Series(np.full(n, 1e-300), index=idx))
    raise ValueError(route)


def _talib():
    if importlib.util.find_spec("talib") is None:
        pytest.skip("talib is an optional dev dependency and is not installed")
    import talib
    return talib


# ---------------------------------------------------------------- mutants

SOURCE = ROOT / "pandas_ta" / "trend" / "j_kaufmanstop_dist.py"

RNG_LINE = "    rng = hi - lo"
AVG_LINE = "    avg = sma(rng, length=PERIOD)"
STOP_LINE = "    stop = lo - MULT * avg"
DIST_LINE = "    dist = (px - stop) / px"
MASK_LINE = "    dist = dist.where(np.isfinite(dist))"

#: (label, old, new). Edits to the SHIPPED source that make the OUTPUT read
#: a bar LATER than T. ⚠ This chain holds no forward `shift` between a price
#: and the output, so a ONE-bar lead is already a look-ahead and no two-bar
#: leads are needed.
CAUSALITY_MUTANTS = [
    ("rng-high-lead", RNG_LINE, "    rng = hi.shift(-1) - lo"),
    ("rng-low-lead", RNG_LINE, "    rng = hi - lo.shift(-1)"),
    ("avg-lead", AVG_LINE, "    avg = sma(rng.shift(-1), length=PERIOD)"),
    ("stop-low-lead", STOP_LINE, "    stop = lo.shift(-1) - MULT * avg"),
    ("close-lead", DIST_LINE,
     "    dist = (px.shift(-1) - stop) / px.shift(-1)"),
    ("output-early", MASK_LINE,
     "    dist = dist.where(np.isfinite(dist)).shift(-1)"),
]

#: Edits that LAG a leg: wrong, but reading no bar later than T, so the
#: suffix sweep is blind to all three and Gate A's oracle is not.
BLIND_SPOT_MUTANTS = [
    ("rng-high-lag", RNG_LINE, "    rng = hi.shift(1) - lo"),
    ("avg-lag", AVG_LINE, "    avg = sma(rng, length=PERIOD).shift(1)"),
    ("stop-low-lag", STOP_LINE, "    stop = lo.shift(1) - MULT * avg"),
]

#: The five guards, each removable on its own, so each can be priced.
HI_GUARD_OFF = ("    hi = hi.where(np.isfinite(hi))", "    pass")
LO_GUARD_OFF = ("    lo = lo.where(np.isfinite(lo))", "    pass")
CL_GUARD_OFF = ("    cl = cl.where(np.isfinite(cl))", "    pass")
PX_GUARD_OFF = ("    px = cl.where(cl >= np.finfo(float).tiny)",
                "    px = cl")
FINITE_GUARD_OFF = (MASK_LINE, "    pass")
GUARDS = [("high is finite", HI_GUARD_OFF), ("low is finite", LO_GUARD_OFF),
          ("close is finite", CL_GUARD_OFF),
          ("close is positive+normal", PX_GUARD_OFF),
          ("output is finite", FINITE_GUARD_OFF)]


def _mutant(old, new):
    src = SOURCE.read_text(encoding="utf-8")
    assert src.count(old) == 1, f"{old!r} occurs {src.count(old)} times"
    ns = {}
    exec(compile(src.replace(old, new), "<mutant>", "exec"), ns)
    return ns["j_kaufmanstop_dist"]


def _caught_at(fn, frame, j, factor=1.03):
    """Did perturbing every bar >= j move any bar < j?

    ⚠ `factor` on all three legs is not a global rescale -- the column is
    invariant under one of those, which is Gate D -- it is a rescale of a
    SUFFIX, which moves the range and the low at bar j.
    """
    high, low, close = frame
    f = Series(np.where(np.arange(close.size) >= j, factor, 1.0),
               index=close.index)
    a = fn(high, low, close).iloc[:j]
    b = fn(high * f, low * f, close * f).iloc[:j]
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
    assert "j_kaufmanstop_dist" in ta.Category["trend"]
    assert hasattr(ta.trend, "j_kaufmanstop_dist")
    high, low, close = _frame("walk")
    col = j_kaufmanstop_dist(high, low, close)
    assert col.name == COLUMN
    assert col.category == "trend"

    df = DataFrame({"high": high.to_numpy(), "low": low.to_numpy(),
                    "close": close.to_numpy()})
    out = df.ta.j_kaufmanstop_dist()
    assert out.name == COLUMN
    assert out.equals(j_kaufmanstop_dist(high.reset_index(drop=True),
                                         low.reset_index(drop=True),
                                         close.reset_index(drop=True)))


def test_the_source_library_is_not_installed_here():
    """Gate A reads the issue's QUOTE of jesse, not its code. Recorded as a
    test so the claim cannot rot into "checked against jesse" once someone
    pip-installs it."""
    assert importlib.util.find_spec("jesse") is None


def test_the_constants_are_the_issues_numbers():
    """"long (22, mult 2)", and nothing else is configurable."""
    assert (PERIOD, MULT) == (22, 2.0)
    assert COLUMN == f"J_KAUFMANSTOP_DIST_{PERIOD}_{MULT}"
    import inspect
    params = list(inspect.signature(j_kaufmanstop_dist).parameters)
    assert params == ["high", "low", "close", "offset", "kwargs"]


def test_min_bars_is_the_sma_window_and_not_a_bar_more():
    """⚠ The one structural number that differs from `j_chandelier_dist`:
    `MIN_BARS == PERIOD`, not `PERIOD + 1`. Nothing in this chain reads a
    previous close, so the SMA's input is defined at bar 0 and the column
    fires at bar PERIOD - 1."""
    assert MIN_BARS == PERIOD
    assert WARMUP == PERIOD - 1
    high, low, close = _frame("walk")
    assert int(j_kaufmanstop_dist(high, low, close)
               .notna().to_numpy().argmax()) == WARMUP


def test_a_frame_shorter_than_min_bars_is_refused():
    """`MIN_BARS - 1` is also the index of the first firing bar, so the
    shortest frame that computes fires on exactly one."""
    high, low, close = _frame("walk")
    short = slice(None, MIN_BARS - 1)
    assert j_kaufmanstop_dist(high[short], low[short], close[short]) is None
    exact = slice(None, MIN_BARS)
    col = j_kaufmanstop_dist(high[exact], low[exact], close[exact])
    assert int(col.notna().sum()) == 1
    assert int(col.notna().to_numpy().argmax()) == MIN_BARS - 1


def test_offset_and_fillna():
    frame = _frame("walk")
    base = j_kaufmanstop_dist(*frame)
    assert _bit_equal(j_kaufmanstop_dist(*frame, offset=2), base.shift(2))
    filled = j_kaufmanstop_dist(*frame, fillna=0.0)
    assert int(filled.isna().sum()) == 0
    assert float(filled.iloc[0]) == 0.0


# -------------------------------------------------------------- Gate A


@pytest.mark.parametrize("name", VARYING)
def test_gate_a_matches_the_issues_formula_spelled_independently(name):
    """1,479 of 1,479 bars of each frame, identical NaN masks, measured
    BIT-EQUAL. ⚠ The assertion is a tolerance, not the bit-equality: the
    frames are built with `np.exp`/`np.cumsum` and a reduced numpy kernel
    can move a price in its last bits."""
    frame = _frame(name)
    got, want = j_kaufmanstop_dist(*frame), _oracle(*frame)
    assert bool((got.isna() == want.isna()).all())
    assert int(got.notna().sum()) == FIRED == 1479
    assert _abs(got, want) < 1e-12
    assert _rel(got, want) < 1e-9


def test_the_pandas_rolling_mean_agrees_with_a_naive_window_sum():
    """Why the Gate A gap above is 0.0 rather than a few ulps: pandas'
    `rolling.mean()` is a compensated running sum and the oracle's is 22
    additions, and on this frame they agree bit for bit. ⚠ Asserted as a
    tolerance, for the dispatch reason above; the measured figure is 0.0
    and the measured differing-bar count is 0 of 1,479."""
    high, low, close = _frame("walk")
    rng = (high - low).to_numpy(dtype=float)
    pandas_avg = sma(high - low, length=PERIOD)
    naive = np.full(rng.size, np.nan)
    for i in range(PERIOD - 1, rng.size):
        naive[i] = sum(rng[i - PERIOD + 1:i + 1].tolist()) / PERIOD
    naive = Series(naive, index=close.index)
    assert bool((pandas_avg.isna() == naive.isna()).all())
    assert int(pandas_avg.notna().sum()) == FIRED
    assert _rel(pandas_avg, naive) < 1e-12


@pytest.mark.parametrize("name", VARYING)
def test_gate_a_matches_talibs_sma_spelling(name):
    """The issue's two operators as TA-Lib spells them. Measured bit-equal
    on all six frames at Spearman 1.0000; asserted as a tolerance for the
    dispatch reason, and SKIPPED where talib is absent rather than passing
    silently."""
    talib = _talib()
    high, low, close = _frame(name)
    want = (close - (low - MULT * Series(
        talib.SMA((high - low).to_numpy(dtype=float), timeperiod=PERIOD),
        index=close.index))) / close
    got = j_kaufmanstop_dist(high, low, close)
    assert bool((got.isna() == want.isna()).all())
    assert _abs(got, want) < 1e-12
    assert _spearman(got, want) > 0.9999


def test_the_warm_up_is_talibs_too_rather_than_recalled():
    """"The SMA first fires at bar 21" is run, not remembered: TA-Lib's
    `SMA`, this module's `sma` and the column all start there."""
    talib = _talib()
    high, low, close = _frame("walk")
    ts = Series(talib.SMA((high - low).to_numpy(dtype=float),
                          timeperiod=PERIOD), index=close.index)
    assert int(ts.notna().to_numpy().argmax()) == WARMUP
    assert int(sma(high - low, length=PERIOD)
               .notna().to_numpy().argmax()) == WARMUP
    assert int(j_kaufmanstop_dist(high, low, close)
               .notna().to_numpy().argmax()) == WARMUP


@pytest.mark.parametrize("name", NAMES)
def test_the_screen_prototype_is_this_columns_arithmetic(name):
    """⚠ Measured on all nine frames, not inferred from the two quotes
    reading alike -- and the OPPOSITE of `j_chandelier_dist`, whose
    prototype was a different column. This is what lets the screen's
    DISCLOSE_GAP figures be read as this arithmetic's."""
    frame = _frame(name)
    got, proto = j_kaufmanstop_dist(*frame), _prototype(*frame)
    assert bool((got.isna() == proto.isna()).all())
    assert _bit_equal(got, proto)


@pytest.mark.parametrize("name", NAMES)
def test_the_sma_import_is_the_rolling_call_it_makes(name):
    """`sma` is imported from its own module rather than retyped
    (CLAUDE.md, "Known breaks"), and this prices that: it is the
    `rolling(22, min_periods=22).mean()` the module's comment says it is."""
    frame = _frame(name)
    assert _bit_equal(j_kaufmanstop_dist(*frame), _alt_inline_mean(*frame))


@pytest.mark.parametrize("fn,floor", [(_alt_true_range, 1e-2),
                                      (_alt_ema, 1e-4),
                                      (_alt_prev_low, 1e-2)],
                         ids=["sma-over-true-range", "ema22",
                              "stop-off-yesterdays-low"])
@pytest.mark.parametrize("name", VARYING)
def test_the_other_readings_are_other_columns(fn, floor, name):
    """Three readings a reader might substitute for the issue's quote, each
    pinned as a DIFFERENT column rather than assumed close. Measured gaps:
    up to 5.6e-02 (true range), 1.3e-03 (EMA), 3.2e-01 (lagged low)."""
    frame = _frame(name)
    got, alt = j_kaufmanstop_dist(*frame), fn(*frame)
    assert not _bit_equal(got, alt)
    assert _abs(got, alt) > floor


@pytest.mark.parametrize("name", NAMES)
def test_nothing_reads_a_bar_before_the_window(name):
    """The BACKWARD limb of causality, which the forward sweep cannot see:
    the chain's only window is 22 bars wide, so truncating the frame at bar
    500 must leave every bar from 521 on untouched. Measured 979 bars,
    bit-equal."""
    high, low, close = _frame(name)
    base = j_kaufmanstop_dist(high, low, close)
    cut = j_kaufmanstop_dist(high.iloc[500:], low.iloc[500:],
                             close.iloc[500:])
    tail = base.iloc[500 + WARMUP:]
    assert int(tail.notna().sum()) == N - 500 - WARMUP == 979
    assert _bit_equal(tail, cut.iloc[WARMUP:])


# -------------------------------------------------------------- Gate B


@pytest.mark.parametrize("name", VARYING)
def test_the_module_is_never_caught_by_the_future_sweep(name):
    assert _sweep(j_kaufmanstop_dist, _frame(name)) == 0


@pytest.mark.parametrize("label,old,new", CAUSALITY_MUTANTS,
                         ids=[m[0] for m in CAUSALITY_MUTANTS])
@pytest.mark.parametrize("name", SWEPT)
def test_every_mutant_is_live_before_it_is_caught(label, old, new, name):
    """A mutant that changes nothing would be caught at 0 offsets for the
    honest reason, which would make the sweep look clean and prove nothing.
    """
    frame = _frame(name)
    a, b = j_kaufmanstop_dist(*frame), _mutant(old, new)(*frame)
    m = a.notna() & b.notna()
    assert int(m.sum()) > 0
    assert not bool((a[m].to_numpy() == b[m].to_numpy()).all())


@pytest.mark.parametrize("label,old,new", CAUSALITY_MUTANTS,
                         ids=[m[0] for m in CAUSALITY_MUTANTS])
@pytest.mark.parametrize("name", SWEPT)
def test_each_mutant_is_caught_by_the_future_sweep(label, old, new, name):
    """Measured 36 of 36 on every mutant and every frame -- unlike
    `j_chandelier_dist`, whose 22-bar MAXIMUM made some leads invisible at
    some offsets. Asserted "at least one" so a kernel that moves a last bit
    cannot turn a real catch into a failure."""
    assert _sweep(_mutant(old, new), _frame(name)) >= 1


@pytest.mark.parametrize("label,old,new", CAUSALITY_MUTANTS,
                         ids=[m[0] for m in CAUSALITY_MUTANTS])
def test_each_mutant_is_caught_loudly_not_marginally(label, old, new):
    """A catch of one bar by 1e-16 would be a rounding accident. Measured
    1.379e-05 .. 3.023e-02 at the first caught offset; asserted at 1e-6,
    which is 1.9e+07x the 5.160e-14 an inexact rescale costs (seven orders,
    not eight)."""
    fn = _mutant(old, new)
    high, low, close = _frame("walk")
    for j in OFFSETS:
        if not _caught_at(fn, (high, low, close), j):
            continue
        f = Series(np.where(np.arange(close.size) >= j, 1.03, 1.0),
                   index=close.index)
        a = fn(high, low, close).iloc[:j]
        b = fn(high * f, low * f, close * f).iloc[:j]
        assert _abs(a, b) > 1e-6
        return
    pytest.fail(f"{label} was never caught, so its loudness is undefined")


@pytest.mark.parametrize("label,old,new", BLIND_SPOT_MUTANTS,
                         ids=[m[0] for m in BLIND_SPOT_MUTANTS])
def test_the_sweeps_blind_spot_is_pinned_and_the_oracle_covers_it(label, old,
                                                                  new):
    """Three edits that LAG a leg. None reads a later bar, so the sweep
    catches none -- pinned in BOTH directions, because a sweep that started
    catching them would mean the module's shift structure had changed. Gate
    A's oracle rejects all three, measured by 6.152e-04 .. 3.224e-01."""
    fn = _mutant(old, new)
    for name in ("walk", "heavy-tailed"):
        frame = _frame(name)
        assert _sweep(fn, frame) == 0
        assert not _bit_equal(fn(*frame), _oracle(*frame))
        assert _abs(fn(*frame), _oracle(*frame)) > 1e-4


# ---------------------------------------------------------- Gates C and D


@pytest.mark.parametrize("name", VARYING)
def test_reachability_on_the_varying_frames(name):
    col = _col(name)
    assert int(col.notna().sum()) == FIRED
    assert bool(col.iloc[:WARMUP].isna().all())
    # Not a constant, and not a handful of repeated values either. ⚠ A
    # SHAPE: the measured value is 1,479 of 1,479 distinct on every one of
    # the six (§C1), and a count pinned ten from its measurement is the
    # thing this file bans elsewhere.
    assert int(col.dropna().nunique()) > 0.9 * FIRED
    assert int((col.dropna() == 0.0).sum()) == 0


def test_the_column_does_not_change_sign():
    """⚠ Where this column parts from both sibling stop distances. The stop
    sits below bar T's OWN low, so
    `(close - stop)/close = (close - low)/close + 2*avg/close` -- two
    non-negative terms on well-formed OHLC. Measured 0.005961 .. 0.014415
    over the 8,874 fired bars of the six, positive on every one. Asserted
    as bounds rather than as the digits, which move in the last bits
    between numpy dispatches."""
    pooled = Series(np.concatenate([_col(n).dropna().to_numpy()
                                    for n in VARYING]))
    assert len(pooled) == FIRED * len(VARYING) == 8874
    assert int((pooled <= 0).sum()) == 0
    assert 0.005 < float(pooled.min()) < 0.007
    assert 0.013 < float(pooled.max()) < 0.016


@pytest.mark.parametrize("name", VARYING + ["rising", "tied"])
def test_the_two_terms_are_both_non_negative_bar_by_bar(name):
    """The identity the no-sign-change claim rests on, checked bar by bar
    rather than only through the pooled minimum: on these frames
    `close >= low` everywhere and the average range is never negative."""
    high, low, close = _frame(name)
    assert bool(((close - low) >= 0.0).all())
    avg = sma(high - low, length=PERIOD).dropna()
    assert bool((avg >= 0.0).all())


def test_a_flat_frame_reads_exactly_zero_rather_than_nothing():
    """⚠ The exception to "not a constant column", and the reason that limb
    is asserted on the varying frames only. With `high == low == close`
    every range is 0, so the average is 0, the stop IS the low, and the
    column is exactly 0.0 on all 1,479 bars it fires on."""
    col = _col("flat")
    assert int(col.notna().sum()) == FIRED
    assert int(col.dropna().nunique()) == 1
    assert float(col.dropna().iloc[0]) == 0.0


def test_a_one_way_market_still_fires_and_reads_a_narrow_band():
    """`rising` has a constant relative range, so the column fires
    everywhere and sits in a band measured 0.009898 .. 0.009946."""
    col = _col("rising")
    assert int(col.notna().sum()) == FIRED
    assert bool((col.dropna() > 0.0).all())
    assert 0.0098 < float(col.dropna().min()) < float(col.dropna().max()) \
        < 0.0100


@pytest.mark.parametrize("factor", [8.0, 64.0])
@pytest.mark.parametrize("name", NAMES)
def test_gate_d_scale_x8_x64_is_bit_identical(name, factor):
    frame = _frame(name)
    assert _bit_equal(j_kaufmanstop_dist(*frame),
                      j_kaufmanstop_dist(*_scaled(frame, factor)))


@pytest.mark.parametrize("factor", [8.0, 64.0])
def test_the_plain_subtraction_is_what_keeps_gate_d_scale_at_1e_6(factor):
    """⚠ WHY this module spells `high - low` instead of calling the fork's
    `non_zero_range`. That helper adds an ABSOLUTE epsilon to the whole leg
    as soon as one bar has `high == low`, so a variant built on it stops
    scaling with the price: at a level of 1e-6 it fails both factors on a
    frame with a doji every seventh bar, where this module holds.
    ⚠ And the honest other half, pinned next door: at a level of 100 the
    variant is BIT-EQUAL to this module on every frame, tied bars included,
    so the plain subtraction buys nothing there."""
    high, low, close = _tied()
    frame = (high / LEVEL * 1e-6, low / LEVEL * 1e-6, close / LEVEL * 1e-6)
    assert int((frame[0].to_numpy() == frame[1].to_numpy()).sum()) > 0
    assert _bit_equal(j_kaufmanstop_dist(*frame),
                      j_kaufmanstop_dist(*_scaled(frame, factor)))
    assert not _bit_equal(_alt_non_zero_range(*frame),
                          _alt_non_zero_range(*_scaled(frame, factor)))


@pytest.mark.parametrize("name", NAMES)
def test_the_non_zero_range_variant_is_bit_equal_at_an_ordinary_level(name):
    """The other half of the claim above, so the module's comment cannot
    overstate what the plain subtraction buys: at a price level of 100 the
    epsilon is below the last bit of the result and the two spellings agree
    bit for bit -- on the `tied` frame's 215 tied bars and the `flat`
    frame's 1,500 as well as on the seven frames with none."""
    frame = _frame(name)
    assert _bit_equal(j_kaufmanstop_dist(*frame), _alt_non_zero_range(*frame))


@pytest.mark.parametrize("factor", [10.0, 3.7, 0.1, 1.0000001])
@pytest.mark.parametrize("name", VARYING)
def test_gate_d_scale_tolerance_for_inexact_factors(name, factor):
    """Measured worst cell 5.160e-14 over the 24 (frame, factor) cells.
    Asserted 1e-9, which is more than four orders above it, because the
    figure moves between numpy CPU dispatches."""
    frame = _frame(name)
    base = j_kaufmanstop_dist(*frame)
    moved = j_kaufmanstop_dist(*_scaled(frame, factor))
    assert bool((base.isna() == moved.isna()).all())
    assert _rel(moved, base) < 1e-9


@pytest.mark.parametrize("factor", [8.0, 64.0])
@pytest.mark.parametrize("level", [1e-6, 1e6, 1e100])
@pytest.mark.parametrize("name", NAMES)
def test_gate_d_scale_at_extreme_price_levels(name, level, factor):
    """⚠ Every frame at every level -- 54 cells -- and not one frame, which
    is what round 1 of the review found this test running under prose that
    said nine. BOTH factors, and the headroom is MEASURED rather than
    reasoned: the largest value the chain computes at 1e100, over all nine
    frames and over all ten of the series it computes, is 9.776e+101
    against DBL_MAX 1.798e+308, a factor of 1.839e+206 (§D3)."""
    high, low, close = _frame(name)
    frame = (high / LEVEL * level, low / LEVEL * level,
             close / LEVEL * level)
    base = j_kaufmanstop_dist(*frame)
    assert int(base.notna().sum()) == FIRED
    assert _bit_equal(base, j_kaufmanstop_dist(*_scaled(frame, factor)))


@pytest.mark.parametrize("name", NAMES)
def test_gate_d_fires_are_strictly_between_zero_and_n(name):
    col = _col(name)
    assert 0 < int(col.notna().sum()) < len(col)


@pytest.mark.parametrize("name", VARYING)
def test_a_level_shift_moves_every_fired_bar(name):
    """The check that keeps the x8 bit-identity from being vacuous: the
    column is invariant under a RESCALE and not under a SHIFT, so it reads
    a ratio rather than nothing at all. ⚠ Asserted on the VARYING frames:
    the flat frame's 1,479 bars read exactly 0.0 either way, and the next
    test pins that."""
    high, low, close = _frame(name)
    base = j_kaufmanstop_dist(high, low, close)
    moved = j_kaufmanstop_dist(high + 10.0, low + 10.0, close + 10.0)
    m = base.notna() & moved.notna()
    assert int(m.sum()) == FIRED
    assert int((base[m] != moved[m]).sum()) == FIRED


def test_a_level_shift_moves_nothing_on_the_flat_frame():
    """The exception to the test above, measured rather than left as a
    surprise: with a zero range the column is exactly 0.0 at any level, so
    0 of its 1,479 bars move."""
    high, low, close = _frame("flat")
    base = j_kaufmanstop_dist(high, low, close)
    moved = j_kaufmanstop_dist(high + 10.0, low + 10.0, close + 10.0)
    m = base.notna() & moved.notna()
    assert int(m.sum()) == FIRED
    assert int((base[m] != moved[m]).sum()) == 0


# --------------------------------------------------- guards and bad data


@pytest.mark.parametrize("value", [np.nan, np.inf, -np.inf])
@pytest.mark.parametrize("leg", ["high", "low"])
@pytest.mark.parametrize("j", [5, 100, 700, 1100, 1495])
def test_a_bad_range_leg_empties_exactly_its_own_windows(value, leg, j):
    """`max(T, 21) .. min(T+21, n-1)`: the range at T reaches the output
    through `sma(high - low, 22)`, and a NaN is in exactly the windows that
    hold it -- of which only the ones past the warm-up were ever firing.
    ⚠ BOTH boundaries are plant points, and both came from the review:
    round 1 asked for the right edge (**5** bars at 1,495, where the frame
    ends at 1,499) and round 2 for the left (**6** bars at 5, bars 21 … 26,
    because bars 5 … 20 were never fired). 22 bars at 100, 700 and 1,100.
    ⚠ Everything else is bit-identical -- the prefix AND the suffix. There
    is no recursion in this chain, so unlike `j_chandelier_dist` a bad leg
    moves no later bar at all."""
    high, low, close = _frame("walk")
    base = j_kaufmanstop_dist(high, low, close)
    h, l = high.copy(), low.copy()
    {"high": h, "low": l}[leg].iloc[j] = value
    with np.errstate(all="ignore"):
        col = j_kaufmanstop_dist(h, l, close)
    gone = np.flatnonzero((base.notna() & col.isna()).to_numpy())
    want = list(range(max(j, WARMUP),
                      min(j + EMPTIED_BY_A_BAD_RANGE_LEG, N)))
    assert gone.tolist() == want
    assert len(want) == min(j + EMPTIED_BY_A_BAD_RANGE_LEG, N) \
        - max(j, WARMUP)
    assert _bit_equal(base.iloc[:j], col.iloc[:j])
    assert _differing_bars(base.iloc[j + 1:], col.iloc[j + 1:]) == 0


@pytest.mark.parametrize("value", [np.nan, np.inf, -np.inf])
@pytest.mark.parametrize("j", [5, 100, 700, 1100, 1495])
def test_a_bad_close_empties_its_own_bar_and_moves_no_other(value, j):
    """The close is only the divisor, so a bad one costs exactly its own
    bar and nothing else moves -- and **0** bars when the bad bar is inside
    the warm-up, where nothing was firing to lose. Measured at 5, 100, 700,
    1,100 and 1,495 (§G4)."""
    high, low, close = _frame("walk")
    base = j_kaufmanstop_dist(high, low, close)
    cl = close.copy()
    cl.iloc[j] = value
    with np.errstate(all="ignore"):
        col = j_kaufmanstop_dist(high, low, cl)
    gone = np.flatnonzero((base.notna() & col.isna()).to_numpy())
    assert gone.tolist() == ([j] if j >= WARMUP else [])
    assert _bit_equal(base.iloc[:j], col.iloc[:j])
    assert _differing_bars(base.iloc[j + 1:], col.iloc[j + 1:]) == 0


@pytest.mark.parametrize("label,edit", GUARDS, ids=[g[0] for g in GUARDS])
@pytest.mark.parametrize("name", NAMES)
def test_every_guard_is_a_no_op_on_an_ordinary_frame(label, edit, name):
    frame = _frame(name)
    assert _bit_equal(j_kaufmanstop_dist(*frame), _mutant(*edit)(*frame))


@pytest.mark.parametrize("value", [np.inf, -np.inf, np.nan])
@pytest.mark.parametrize("leg,label,edit",
                         [("high", "high is finite", HI_GUARD_OFF),
                          ("low", "low is finite", LO_GUARD_OFF),
                          ("close", "close is finite", CL_GUARD_OFF)],
                         ids=["high", "low", "close"])
def test_the_three_input_finite_guards_are_measured_no_ops(leg, label, edit,
                                                           value):
    """⚠ The finding this test exists to RECORD rather than to celebrate.
    §G2 plants each of `+inf`, `-inf` and NaN in each leg at bar 700 of a
    `walk` and removes the matching guard: the column is BIT-EQUAL in all
    nine cells, with identical fired counts and no infinite reading either
    way. So these three lines carry no measured load here, and the module's
    comment says so.

    What does the work is pinned elsewhere: pandas' rolling window turns an
    infinite observation into a NaN
    (`test_a_pandas_rolling_mean_turns_an_infinite_observation_into_nan`),
    and the final finite mask catches the two overflow routes that reach
    the output.
    ⚠ **This test does NOT pin pandas' absorption**, and an earlier draft
    of this docstring claimed it did -- "a pandas upgrade that changed the
    absorption would fail here as well as there", which round 1 of the
    review refuted and §G5 then measured. With `sma` rebound to a mean that
    PROPAGATES an infinity, these guards are STILL no-ops, because the final
    mask converts the propagated infinity to a NaN at exactly the bars the
    guard already blanks:
    `test_the_guards_stay_no_ops_even_if_the_rolling_mean_propagates` is
    that measurement.
    ⚠ **TWO** tests would fail on such an upgrade, not one -- round 2 of the
    review caught a draft that said one. They are
    `test_a_pandas_rolling_mean_turns_an_infinite_observation_into_nan` and
    `test_route_1_never_reaches_the_output`, whose zero infinite readings
    are the same absorption;
    `test_route_1s_zero_is_the_absorption_and_would_move_without_it`
    measures route 1 shipping 99 of 120 instead.
    """
    high, low, close = _frame("walk")
    bare = _mutant(*edit)
    h, l, c = high.copy(), low.copy(), close.copy()
    {"high": h, "low": l, "close": c}[leg].iloc[700] = value
    with np.errstate(all="ignore"):
        ship, naked = j_kaufmanstop_dist(h, l, c), bare(h, l, c)
    assert int(np.isinf(ship).sum()) == int(np.isinf(naked).sum()) == 0
    assert _bit_equal(ship, naked)


#: §G5's edit: the shipped `sma` import replaced by a mean that PROPAGATES
#: an infinity instead of letting pandas' window turn it into a NaN.
#: ⚠ It leaves `rolling` out, and that is measured rather than stylistic:
#: the three `rolling` aggregations measured all turn an infinite
#: observation into a NaN, so `rolling(...).apply(np.mean, raw=True)` --
#: which round 2 of the review proposed and an earlier draft of this
#: constant used -- does not propagate either.
#: `test_no_rolling_aggregation_can_propagate_an_infinity` is that
#: measurement, and §G5 prints the four means side by side.
PROPAGATING_MEAN = (
    "from pandas_ta.overlap.sma import sma",
    "def sma(close, length=None, **kwargs):\n"
    "    import numpy as _np\n"
    "    from pandas import Series as _S\n"
    "    _a = close.to_numpy(dtype=float)\n"
    "    _o = _np.full(_a.size, _np.nan)\n"
    "    for _i in range(length - 1, _a.size):\n"
    "        _o[_i] = _a[_i - length + 1:_i + 1].mean()\n"
    "    return _S(_o, index=close.index)")


def _propagating():
    """The shipped module with `sma` rebound to the propagating mean."""
    src = SOURCE.read_text(encoding="utf-8")
    assert src.count(PROPAGATING_MEAN[0]) == 1
    return src.replace(*PROPAGATING_MEAN)


def test_no_rolling_aggregation_can_propagate_an_infinity():
    """⚠ Round 2 of the review proposed
    `rolling(...).apply(np.mean, raw=True)` as a mean that propagates an
    infinity, and the measurement refutes it. Measured on the `walk` with a
    `+inf` high at bar 700 (§G5): `sma`,
    `rolling(...).apply(np.mean, raw=True)` and `rolling(...).max()` all
    read **NaN** there with 0 infinite bars, and a numpy window mean with no
    `rolling` in it reads **inf** with 22. So the conversion happens before
    the window function rather than inside the aggregation.

    ⚠ **THREE aggregations is the scope of this test**, which is a sample
    and not a proof of the name's universal: pandas' source is outside this
    worktree and is not read, so where exactly the conversion sits is not
    claimed here. Round 3 of the review caught an earlier draft naming
    `_prep_values` and crediting §G5 with printing it. What is measured is
    the behaviour of the three.

    This is why `PROPAGATING_MEAN` leaves `rolling` out, and it is the
    sharper form of what
    `test_a_pandas_rolling_mean_turns_an_infinite_observation_into_nan`
    pins.
    """
    high, low, close = _frame("walk")
    h = high.copy()
    h.iloc[700] = np.inf
    rng = h - low
    with np.errstate(all="ignore"):
        shipped = sma(rng, length=PERIOD)
        applied = rng.rolling(PERIOD, min_periods=PERIOD).apply(np.mean,
                                                                raw=True)
        maxed = rng.rolling(PERIOD, min_periods=PERIOD).max()
    for name, col in (("sma", shipped), ("apply(np.mean)", applied),
                      ("max", maxed)):
        assert int(np.isinf(col).sum()) == 0, name
        assert bool(col.isna().iloc[700]), name

    ns = {}
    exec(compile(_propagating().split("def j_kaufmanstop_dist")[0],
                 "<means>", "exec"), ns)
    with np.errstate(all="ignore"):
        propagated = ns["sma"](rng, PERIOD)
    assert int(np.isinf(propagated).sum()) == PERIOD
    assert bool(np.isinf(propagated.iloc[700]))


def test_route_1s_zero_is_the_absorption_and_would_move_without_it():
    """⚠ Round 2 of the review's MAJOR, measured. An earlier draft said in
    four places that
    `test_a_pandas_rolling_mean_turns_an_infinite_observation_into_nan` is
    the ONLY test a pandas that stopped absorbing would fail. It is not:
    `test_route_1_never_reaches_the_output` asserts 0 infinite readings
    WITHOUT the final mask on the route-1 frame, and that zero exists only
    because the window absorbs the infinite range.

    Measured under the propagating mean (§G5): route 1 ships **99** of 120
    infinite readings without the mask, exactly like routes 2 and 3, so
    §G3's route-1 row would move from 0 to 99 and that test would fail.
    ⚠ What does NOT change is the shipped column: with the mask in place
    all three routes ship 0 infinite readings even then, which is the limb
    that matters for a feature.
    """
    on = _propagating()
    off = on.replace(*FINITE_GUARD_OFF)
    assert off != on
    ns_on, ns_off = {}, {}
    exec(compile(on, "<prop>", "exec"), ns_on)
    exec(compile(off, "<prop-nomask>", "exec"), ns_off)
    for route in ("range", "stop", "division"):
        frame = _overflow_frame(route)
        with np.errstate(all="ignore"):
            ship = ns_on["j_kaufmanstop_dist"](*frame)
            bare = ns_off["j_kaufmanstop_dist"](*frame)
        assert int(np.isinf(ship).sum()) == 0, route
        assert int(np.isinf(bare).sum()) > 50, route


@pytest.mark.parametrize("value", [np.inf, -np.inf])
@pytest.mark.parametrize("leg,edit",
                         [("high", HI_GUARD_OFF), ("low", LO_GUARD_OFF),
                          ("close", CL_GUARD_OFF)],
                         ids=["high", "low", "close"])
def test_the_guards_stay_no_ops_even_if_the_rolling_mean_propagates(leg, edit,
                                                                    value):
    """⚠ The measurement that replaced an inference round 1 of the review
    refuted. The tempting justification for keeping three dead guards is
    "pandas might stop absorbing infinities one day" -- so this test makes
    pandas stop, by rebinding `sma` to `PROPAGATING_MEAN`: a numpy window
    mean with no `rolling` in it, which reads **inf** at a planted bar where
    every `rolling` aggregation measured reads NaN
    (`test_no_rolling_aggregation_can_propagate_an_infinity`). The guard is
    then removed on top of that.
    ⚠ An earlier draft of this docstring named
    `rolling(...).apply(np.mean, raw=True)` here -- round 2 of the review's
    proposal, which round 2's own fix then measured as NOT propagating. The
    vehicle is the numpy window mean and nothing else; round 3 caught the
    stale sentence surviving twelve lines above the one that refutes it.

    Measured (§G5): the column is STILL bit-equal with and without each
    guard, in all six cells, because the final `isfinite` mask converts the
    propagated infinity to a NaN at exactly the bars the guard already
    blanks. So the upgrade story does not justify the three lines, and the
    receipt says so instead of implying otherwise.

    The rebinding is also measured not to change the clean column: the
    propagating mean is bit-equal to `sma` on a clean `walk`, which is what
    makes the comparison above about the guard rather than about the mean.
    ⚠ Without the cross-referenced test above, these six cells would prove
    nothing: they read identically whether the rebound mean propagates or
    absorbs, which is round 2 of the review's MINOR.
    """
    high, low, close = _frame("walk")
    on = _propagating()
    off = on.replace(*edit)
    assert off != on
    ns_on, ns_off = {}, {}
    exec(compile(on, "<prop>", "exec"), ns_on)
    exec(compile(off, "<prop+guard-off>", "exec"), ns_off)

    with np.errstate(all="ignore"):
        clean = ns_on["j_kaufmanstop_dist"](high, low, close)
    assert _bit_equal(clean, j_kaufmanstop_dist(high, low, close))

    h, l, c = high.copy(), low.copy(), close.copy()
    {"high": h, "low": l, "close": c}[leg].iloc[700] = value
    with np.errstate(all="ignore"):
        a = ns_on["j_kaufmanstop_dist"](h, l, c)
        b = ns_off["j_kaufmanstop_dist"](h, l, c)
    assert int(np.isinf(a).sum()) == int(np.isinf(b).sum()) == 0
    assert _bit_equal(a, b)


def test_the_close_positivity_guard_is_the_one_that_bites():
    """The guard on the inputs that IS load-bearing. Measured: with it
    removed, a close of -50 at bar 700 fires and reads 1.924 -- a sign flip
    in a column whose every other bar is 0.006 .. 0.014. A zero and a
    subnormal close read NaN without it instead of blanking, which is the
    same bar lost by a different route.

    ⚠ And the bar it blanks is the only bar it touches: the close reaches
    the output only as the divisor, so the prefix AND the suffix are
    bit-identical."""
    high, low, close = _frame("walk")
    base = j_kaufmanstop_dist(high, low, close)
    for bad in (0.0, -50.0, 5e-310):
        cl = close.copy()
        cl.iloc[700] = bad
        with np.errstate(all="ignore"):
            col = j_kaufmanstop_dist(high, low, cl)
        gone = np.flatnonzero((base.notna() & col.isna()).to_numpy())
        assert gone.tolist() == [700]
        assert _bit_equal(base.iloc[:700], col.iloc[:700])
        assert _differing_bars(base.iloc[701:], col.iloc[701:]) == 0

    cl = close.copy()
    cl.iloc[700] = -50.0
    with np.errstate(all="ignore"):
        bare = _mutant(*PX_GUARD_OFF)(high, low, cl)
    assert bool(bare.notna().iloc[700])
    # The sign flip itself: every other fired bar of this frame is
    # 0.006 .. 0.014, and this one is the stop over a negative close.
    assert float(bare.iloc[700]) > 1.0


def test_the_finite_mask_is_not_a_no_op_where_the_division_overflows():
    """The frame where the final mask earns its line: a stop near -1e300
    over a close near 1e-300. Measured 99 infinite readings of 120 without
    it, 0 with it. This is route 3 of §G3's three."""
    frame = _overflow_frame("division")
    with np.errstate(all="ignore"):
        guarded = j_kaufmanstop_dist(*frame)
        bare = _mutant(*FINITE_GUARD_OFF)(*frame)
    assert int(np.isinf(guarded).sum()) == 0
    assert int(np.isinf(bare).sum()) > 50


def test_route_2_also_reaches_the_output_without_the_mask():
    """⚠ Three routes, not one, and TWO of them reach the output. Route 2
    is the stop's own subtraction, `lo - 2 * avg` with an average range
    near DBL_MAX / 2. Measured 99 of 120 infinite readings without the
    mask."""
    frame = _overflow_frame("stop")
    with np.errstate(all="ignore"):
        guarded = j_kaufmanstop_dist(*frame)
        bare = _mutant(*FINITE_GUARD_OFF)(*frame)
    assert int(np.isinf(guarded).sum()) == 0
    assert int(np.isinf(bare).sum()) > 50


def test_route_1_never_reaches_the_output():
    """And the one that does not: an infinite RANGE from two finite legs.
    It ships nothing, because the rolling mean turns the infinite
    observation into a NaN -- the behaviour the next test pins."""
    frame = _overflow_frame("range")
    with np.errstate(all="ignore"):
        guarded = j_kaufmanstop_dist(*frame)
        bare = _mutant(*FINITE_GUARD_OFF)(*frame)
    assert int(np.isinf(guarded).sum()) == 0
    assert int(np.isinf(bare).sum()) == 0
    assert int(guarded.notna().sum()) == 0


def test_a_pandas_rolling_mean_turns_an_infinite_observation_into_nan():
    """The pandas BEHAVIOUR two of the tests above rest on, pinned
    separately so an upgrade that stops doing it fails HERE rather than
    shipping an infinite feature.

    Measured, and the contrast is the point, on 81 bars of 1.0 with one bad
    value at bar 40:

    * one `+inf` -> every window holding bar 40 reads NaN, so 38 of the 60
      possible windows fire and none is infinite;
    * one DBL_MAX -> bar 40 reads 8.171e+306, so a merely huge observation
      flows straight through and 60 windows fire.

    ⚠ `rolling.mean()` is NOT `ewm`: `j_chandelier_dist` measured the EWM
    SKIPPING an infinite observation and carrying on, which is why a bad
    low there moved values instead of blanking bars.
    """
    big = float(np.finfo(float).max)
    with np.errstate(all="ignore"):
        infinite = sma(Series([1.0] * 40 + [np.inf] + [1.0] * 40),
                       length=PERIOD)
        huge = sma(Series([1.0] * 40 + [big] + [1.0] * 40), length=PERIOD)
    assert int(np.isinf(infinite).sum()) == 0
    assert int(infinite.notna().sum()) == 81 - PERIOD + 1 - PERIOD == 38
    assert bool(infinite.iloc[40:40 + PERIOD].isna().all())
    assert int(np.isinf(huge).sum()) == 0
    assert int(huge.notna().sum()) == 81 - PERIOD + 1 == 60
    assert float(huge.iloc[40]) > 1e306


@pytest.mark.parametrize("value", [0.0, -100.0, 5e-310, 1e308])
def test_a_degenerate_frame_raises_nothing_and_ships_nothing_infinite(value):
    """A constant frame of any of these four raises nothing. The first
    three read NOTHING -- the close guard drops a zero, a negative and a
    subnormal -- and 1e308 reads exactly 0.0 on the 39 bars a 60-bar frame
    leaves after the warm-up."""
    idx = date_range("2020-01-01", periods=60, freq="h")
    s = Series(np.full(60, value), index=idx)
    with np.errstate(all="ignore"):
        col = j_kaufmanstop_dist(s, s, s)
    assert int(np.isinf(col).sum()) == 0
    if value == 1e308:
        assert int(col.notna().sum()) == 60 - WARMUP
        assert int(col.dropna().nunique()) == 1
        assert float(col.dropna().iloc[0]) == 0.0
    else:
        assert int(col.notna().sum()) == 0


@pytest.mark.parametrize("n", [0, 1, 5, MIN_BARS - 1])
def test_a_frame_below_min_bars_is_refused_at_every_length(n):
    s = Series(np.full(n, 100.0),
               index=date_range("2020-01-01", periods=n, freq="h"))
    assert j_kaufmanstop_dist(s, s, s) is None


def test_an_all_nan_frame_is_empty_rather_than_an_error():
    """`sma` returns a NaN column rather than None for a long enough
    all-NaN series, so there is no None to escape -- unlike
    `j_chandelier_dist`, where `wilder_rma` returns None and the module has
    to catch it."""
    s = Series(np.full(100, np.nan),
               index=date_range("2020-01-01", periods=100, freq="h"))
    col = j_kaufmanstop_dist(s, s, s)
    assert col is not None
    assert int(col.notna().sum()) == 0
    assert col.name == COLUMN


# -------------------------------------------------- documentation surface


def test_the_docstrings_first_paragraph_survives_the_dictionary_cut():
    """`docs/IndicatorDictionary.md` is what CLAUDE.md tells a reader to
    consult before judging a column, and it prints the first paragraph cut
    at 150 characters. A cut sentence there is how a column gets
    misunderstood."""
    doc = j_kaufmanstop_dist.__doc__.splitlines()
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
    assert "Kaufman" in cut and "range" in cut


def test_the_receipt_says_gate_e_is_pending():
    """⚠ Expected to be REPLACED by the receipt session, not to keep
    passing: the launcher runs Gate E after this session and a later
    session writes the measured numbers in."""
    doc = (ROOT / "docs" / "JKaufmanstopDistMeasured.md").read_text(
        encoding="utf-8")
    assert "Gate E: pending, run by issue-solver after this session" in doc
    assert "0.8776182137043917" in doc   # the SCREEN's figure, on the prototype
    assert "natr" in doc
    assert "DISCLOSE_GAP" in doc


def test_no_gate_e_row_is_recorded_yet():
    """The receipt session's cue. `tests/test_gate_e_ledger.py` fails on a
    local run until the row exists -- that is the owed-measurement state
    CLAUDE.md describes, not a defect in this port."""
    path = ROOT / "docs" / "gate_e_ledger.csv"
    with path.open(newline="", encoding="utf-8") as handle:
        rows = [r for r in csv.DictReader(handle)
                if r["indicator"] == "j_kaufmanstop_dist"]
    assert rows == []
