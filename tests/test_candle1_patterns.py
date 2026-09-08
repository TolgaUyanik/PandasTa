# -*- coding: utf-8 -*-
"""CANDLE-1 -- the four chart-pattern shape matchers, in order of how much it
would hurt to lose the pin.

MODULES UNDER TEST
    `pandas_ta.trend.head_shoulders`     HS_*    head & shoulders / inverse
    `pandas_ta.trend.triple_top_bottom`  TRPL_*  triple top / triple bottom
    `pandas_ta.trend.triangle_wedge`     TRIW_*  ascending / descending /
                                                 symmetrical triangle, rising /
                                                 falling wedge. NOT the
                                                 rectangle -- skipped on a
                                                 pre-registered trigger, see
                                                 `test_the_rectangle_is_skipped
                                                 _and_the_evidence_still_repro
                                                 duces` and
                                                 `CandlePatternsMeasured.md` §6
    `pandas_ta.trend.rounding_cup`       CUP_*   cup & handle / rounding bottom,
                                                 rounding top

1. THE HAND-DERIVED FIXTURES (`test_*_fixture_*`). Four price paths whose
   pivots, neckline, measured target and every emitted value were computed on
   paper BEFORE the modules were run, then asserted exactly. These are the
   tests that would catch a plausible-looking wrong shape matcher -- the single
   worst outcome available here, and one this repo has shipped before. Every
   number below is a hand derivation that the code then reproduced, not a
   number read off the code:

     head & shoulders bear   shoulders 110.5 / 109.5, head 120.5, flat
                             neckline 99.5, break bar 35 at close 99
                             HS_TGT_PCT   = |78.5 - 99| / 99   = 0.2070707
                             HS_PEND      = -1 on bars 32, 33, 34
     triple top              touches 110.5 / 111.5 / 110.0, same neckline,
                             break bar 35
                             TRPL_TGT_PCT = |87.5 - 99| / 99   = 0.1161616
                             and `head_shoulders` is SILENT on this frame --
                             asserted, because the two matchers read the same
                             five-pivot window and only the dominance test
                             separates them
     descending triangle     upper 110.5@6 -> 106.5@18 -> 102.5@26, lower flat
                             at 99.5, TWO patterns live at the break
                             TRIW_CONF_BEAR at bar 29
                             TRIW_SLOPE_UP  = -0.004695  (from pattern 2)
                             TRIW_WIDTH     =  0.033535  (from pattern 1)
                             -- two magnitudes on one bar coming from
                             DIFFERENT patterns is the documented aggregation
                             rule, pinned here so it cannot be "tidied"
                             TRIW_SLOPE_DN  =  0.0 exactly, the disclosed
                             ambiguous zero: a flat boundary and "no event"
                             are the same value
     cup / rounding top      exact parabola `88 + 0.4u^2 + 0.1u`, u = i - 5.5
                             CUP_CONF_BULL at bar 14 -- the FIRST computable
                             bar, which is why the warm-up is
                             `length + handle - 1` and not `length + handle`
                             CUP_DEPTH = 12.6 / 100.65 = 0.1251863
                             CUP_CURV > 0 for the cup, < 0 for the top

   SIX COLUMNS THAT THESE FIXTURES USED TO PIN ARE GONE. `HS_SYM`,
   `HS_HEAD_EXC`, `TRPL_SPREAD`, `TRIW_CONV`, `CUP_R2` and `CUP_SYM` were
   built, taken through a full 485-column Gate E (every one of them a clear
   SHIP against the shipped set) and then DELETED on the INTERNAL overlap --
   up to rho = 1.0000 against the sibling magnitude on the same event support.
   Each module's docstring carries the numbers and the mechanism.

2. GATE B -- FOUR CAUSALITY MUTANTS (`test_gate_b_*`). `CLAUDE.md`: prefix
   truncation cannot see back-dating, so the detector is FUTURE PERTURBATION.
   Every bar from J onward is bumped by +50 and nothing before J may move. The
   mutant is an `importlib` + `exec` copy of the real module source with the
   confirmation write index moved from `T` to `T // 2`.

   MEASURED, and the reason this test sweeps J instead of fixing it: at a
   single J the mutant is caught or not depending on whether any confirmation
   happens to land after J and whether `T // 2` collides with the perturbed
   run's own back-dated writes. On the 600-bar seed-7 frame, `T // 2` catches
   all four modules at J=150; at J=200 it misses `triangle_wedge`; at J=250
   and J=300 it misses `rounding_cup`, which fires only 6 times in 600 bars
   and never after bar 222. So the assertion is: the real module leaks 0.0 at
   EVERY J in {150, 200, 250, 300} (four independent chances to leak), and the
   mutant leaks at SOME J. Pinning one lucky J would have been a weaker claim
   dressed up as a stronger one.

3. GATE D -- SCALE INVARIANCE (`test_gate_d_*`). BIT-IDENTICAL under x8 and
   x64: `(a != b).sum() == 0` on the co-finite cells, no tolerance. A 1e-9
   `np.isclose` was caught papering over exactly this in CANDLE-0's harness
   this week. x10 and x3.7 are checked with a tolerance and matching NaN masks.
   Measured on the seed-11 500-bar frame before the six-column cut: 3,430 /
   2,940 / 3,928 / 3,262 co-finite cells per module, 0 mismatches, and the
   largest x10/x3.7 deviation anywhere is 5.4e-15. The cut removed columns,
   not behaviour, so the cell counts are now lower and the mismatch count is
   still 0 -- the test asserts the mismatch count, not the cell count.

4. GATE C -- REACHABILITY (`test_gate_c_*`). Every shipped column must fire on
   real data, with counts. Uses the parent repo's BIST daily Parquet cache and
   SKIPS when it is absent, because that cache is not part of this repo. The
   full 50-ticker / 91,197-bar counts live in
   `docs/CandlePatternsMeasured.md` §2 -- 0 of 22 columns dead, and the four
   modules reproduce CANDLE-0's prototype firing counts EXACTLY on that pool
   (H&S 180 / 180, triple top 187, triple bottom 219, cup 406). This test
   re-derives reachability on 8 tickers so a regression that silences a column
   fails here and not only in review.

5. The wiring, the validators, the offset and the column names. Cheap tests
   that catch the failure mode `CLAUDE.md` calls "computes correctly and is
   invisible".

WHAT THIS FILE DOES NOT PIN: whether any of these patterns PREDICTS anything.
Nothing here is a return study, and `docs/CandlePatternShortlist.md` §5 item 1
already records that as an open question.
"""
import importlib
import importlib.util

import numpy as np
import pandas as pd
import pytest

from .context import pandas_ta as ta
from pandas_ta.trend.head_shoulders import head_shoulders
from pandas_ta.trend.rounding_cup import rounding_cup
from pandas_ta.trend.triangle_wedge import triangle_wedge
from pandas_ta.trend.triple_top_bottom import triple_top_bottom

MODULES = {
    "head_shoulders": ("pandas_ta.trend.head_shoulders", head_shoulders),
    "triple_top_bottom": ("pandas_ta.trend.triple_top_bottom",
                          triple_top_bottom),
    "triangle_wedge": ("pandas_ta.trend.triangle_wedge", triangle_wedge),
    "rounding_cup": ("pandas_ta.trend.rounding_cup", rounding_cup),
}

#: kwargs that make each module fire often enough on a synthetic frame to be
#: worth measuring. Not the defaults -- the defaults need real-length data.
PROBE_KW = {
    "head_shoulders": dict(left=3, right=3),
    "triple_top_bottom": dict(left=3, right=3),
    "triangle_wedge": dict(left=3, right=3),
    "rounding_cup": dict(length=30, handle=5),
}


# ---------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------
def _ohlc(closes):
    """close-driven OHLC with a symmetric 1.0-wide bar, so every high pivot is
    exactly `close + 0.5` and every low pivot `close - 0.5`. Same device as
    `tests/test_dtdb.py::_frame`, and it is what makes the neckline levels
    below hand-derivable."""
    c = [float(x) for x in closes]
    return pd.DataFrame({"open": c,
                         "high": [x + 0.5 for x in c],
                         "low": [x - 0.5 for x in c],
                         "close": c})


def _hs_bear_path():
    """One head-and-shoulders top and nothing else.

    bars  0-6   100..110   -> LEFT SHOULDER, high pivot 110.5 at bar 6
    bars  7-12  108..100   -> trough, low pivot 99.5 at bar 12   (NECKLINE)
    bars 13-18  104..120   -> HEAD, high pivot 120.5 at bar 18
    bars 19-24  116..100   -> trough, low pivot 99.5 at bar 24   (NECKLINE)
    bars 25-30  102..109   -> RIGHT SHOULDER, high pivot 109.5 at bar 30
    bars 31-40  107..89    -> the decline that breaks 99.5 at bar 35

    The shoulders are deliberately UNEQUAL (110.5 vs 109.5) so `HS_SYM` has a
    nonzero value to assert; an equal-shoulder fixture would have pinned 0.0,
    which is also what a silent bar emits.
    """
    return ([100, 102, 104, 106, 108, 109, 110]
            + [108, 106, 104, 102, 101, 100]
            + [104, 108, 112, 116, 119, 120]
            + [116, 112, 108, 104, 102, 100]
            + [102, 104, 106, 108, 108.5, 109]
            + [107, 105, 103, 101, 99, 97, 95, 93, 91, 89])


def _triple_top_path():
    """Three level tops -- 110.5, 111.5, 110.0 -- over the same flat 99.5
    neckline, breaking at bar 35.

    `max / min - 1 = 111.5 / 110.0 - 1 = 0.013636`, inside `tol = 0.03`, and
    the middle top FAILS the head-and-shoulders dominance test
    (`111.5 > 110.5 * 1.015 = 112.16` is false), which is what makes this
    frame a triple top and not an H&S. Both facts are asserted.
    """
    return ([100, 102, 104, 106, 108, 109, 110]
            + [108, 106, 104, 102, 101, 100]
            + [102, 104, 106, 108, 110, 111]
            + [109, 107, 105, 103, 101, 100]
            + [102, 104, 106, 108, 109, 109.5]
            + [107, 105, 103, 101, 99, 97, 95, 93, 91, 89])


def _descending_triangle_path():
    """A descending triangle: falling highs over a flat 99.5 floor.

    bars  0-6   -> high pivot 110.5 at bar 6
    bars  7-12  -> low  pivot  99.5 at bar 12
    bars 13-18  -> high pivot 106.5 at bar 18   (lower high)
    bars 19-24  -> low  pivot  99.5 at bar 24   (equal low)
    bars 25-30  -> high pivot 102.5 at bar 26   (lower high again)
    break below 99.5 at bar 29, close 99.4

    TWO patterns are live at the break -- (6,12,18,24) born at bar 26 and
    (12,18,24,26) born at bar 28 -- which is deliberate: it is the only way to
    pin the per-column `max |value|` aggregation, and it produces the
    documented result that `TRIW_WIDTH` comes from one pattern while
    `TRIW_CONV` and `TRIW_SLOPE_UP` come from the other.
    """
    return ([100, 102, 104, 106, 108, 109, 110]
            + [108, 106, 104, 102, 101, 100]
            + [101, 102, 103, 104, 105, 106]
            + [105, 104, 103, 102, 101, 100]
            + [101, 102, 101, 100, 99.4, 99.2])


def _cup_path():
    """An EXACT quadratic cup, so `CUP_R2` must come back 1.0.

    `y_i = 88 + 0.4 * u^2 + 0.1 * u` for `u = i - 5.5`, i in 0..11. The `0.1u`
    tilt exists only so the two rims differ (99.55 vs 100.65) and `CUP_SYM`
    has something nonzero to pin. Then a three-bar handle below the rim and a
    close back above it at bar 14.
    """
    u = np.arange(12) - 5.5
    cup = list(88 + 0.4 * u ** 2 + 0.1 * u)
    return cup + [99.0, 100.0, 102.0, 103.0, 104.0]


def _rounding_top_path():
    """The mirror: `y_i = 112 - 0.4 * u^2 - 0.1 * u`, then a close back below
    the lower rim at bar 14."""
    u = np.arange(12) - 5.5
    top = list(112 - 0.4 * u ** 2 - 0.1 * u)
    return top + [101.0, 100.0, 98.0, 97.0, 96.0]


def _rw(n=600, seed=7):
    """Random-walk OHLC. Used by Gates B and D, where the SHAPE does not
    matter but the fire count does."""
    rng = np.random.default_rng(seed)
    c = 100 + np.cumsum(rng.normal(0, 1.2, n))
    idx = pd.date_range("2020-01-01", periods=n, freq="D")
    return (pd.Series(c + abs(rng.normal(0, 0.8, n)), index=idx),
            pd.Series(c - abs(rng.normal(0, 0.8, n)), index=idx),
            pd.Series(c, index=idx))


def _fires(series):
    """Bars where a 0/1 flag is exactly 1.0. NaN never counts.

    This helper exists because `(col != 0).sum()` counts the NaN warm-up as a
    firing -- an error that made the first smoke run of these modules look
    like a 10x over-fire until the counts were compared against CANDLE-0's
    prototype.
    """
    v = series.to_numpy(dtype=float)
    return [int(i) for i in np.flatnonzero(v == 1.0)]


# ---------------------------------------------------------------------
# 1. hand-derived fixtures
# ---------------------------------------------------------------------
def test_head_shoulders_fixture_is_exact():
    df = _ohlc(_hs_bear_path())
    out = head_shoulders(df.high, df.low, df.close, left=2, right=2)
    p = "_2_2_0.03_60"

    assert _fires(out["HS_CONF_BEAR" + p]) == [35]
    assert _fires(out["HS_CONF_BULL" + p]) == []
    assert out["HS_TGT_PCT" + p].iloc[35] == pytest.approx(20.5 / 99, abs=1e-12)
    # the pattern is born on bar 32 (the fifth pivot's confirmation bar) and
    # is pending for exactly three bars before it breaks
    pend = out["HS_PEND" + p]
    assert [int(i) for i in np.flatnonzero(pend.to_numpy() == -1.0)] == \
        [32, 33, 34]
    assert pend.iloc[35] == 0.0
    # warm-up is `left + right + 4` = 8 bars of NaN, and not one bar more
    assert out.iloc[:8].isna().all().all()
    assert not out.iloc[8].isna().any()
    # AGE is 1.0 until the first confirmation, then counts up from 0
    assert out["HS_AGE" + p].iloc[34] == 1.0
    assert out["HS_AGE" + p].iloc[35] == 0.0
    assert out["HS_AGE" + p].iloc[36] == pytest.approx(1.0 / 60)


def test_triple_top_fixture_is_exact_and_head_shoulders_stays_silent():
    """The two matchers read the SAME five-pivot window.

    Only the dominance test separates them, so a regression that loosened it
    would light both on this frame. The silence assertion is the point of the
    test, not a bonus.
    """
    df = _ohlc(_triple_top_path())
    out = triple_top_bottom(df.high, df.low, df.close, left=2, right=2)
    p = "_2_2_0.03_60"

    assert _fires(out["TRPL_CONF_BEAR" + p]) == [35]
    assert _fires(out["TRPL_CONF_BULL" + p]) == []
    assert out["TRPL_TGT_PCT" + p].iloc[35] == pytest.approx(11.5 / 99,
                                                             abs=1e-12)
    assert [int(i) for i in
            np.flatnonzero(out["TRPL_PEND" + p].to_numpy() == -1.0)] == \
        [32, 33, 34]

    hs = head_shoulders(df.high, df.low, df.close, left=2, right=2)
    assert _fires(hs["HS_CONF_BEAR_2_2_0.03_60"]) == []
    assert _fires(hs["HS_CONF_BULL_2_2_0.03_60"]) == []

    # and the converse: the H&S frame is not a triple top
    df2 = _ohlc(_hs_bear_path())
    out2 = triple_top_bottom(df2.high, df2.low, df2.close, left=2, right=2)
    assert _fires(out2["TRPL_CONF_BEAR" + p]) == []


def test_descending_triangle_fixture_pins_the_aggregation_rule():
    df = _ohlc(_descending_triangle_path())
    out = triangle_wedge(df.high, df.low, df.close, left=2, right=2)
    p = "_2_2_60"

    assert _fires(out["TRIW_CONF_BEAR" + p]) == [29]
    assert _fires(out["TRIW_CONF_BULL" + p]) == []
    # two patterns pending on bar 28, one on bars 26-27
    assert list(out["TRIW_PEND" + p].iloc[26:29]) == [1.0, 1.0, 2.0]

    # pattern 1 = pivots at bars 6/12/18/24, pattern 2 = 12/18/24/26.
    # upper slope, pattern 2: (102.5 - 106.5) / (26 - 18) / 106.5
    s2 = (102.5 - 106.5) / (26 - 18) / 106.5
    assert out["TRIW_SLOPE_UP" + p].iloc[29] == pytest.approx(s2, abs=1e-12)
    # width, pattern 1: upper line 110.5 -> 106.5 evaluated at bar 29, less
    # the flat 99.5 floor, over the break close 99.4
    up29 = 110.5 + (106.5 - 110.5) * (29 - 6) / (18 - 6)
    assert out["TRIW_WIDTH" + p].iloc[29] == pytest.approx(
        (up29 - 99.5) / 99.4, abs=1e-12)
    # the disclosed ambiguous zero: the lower boundary is exactly flat
    assert out["TRIW_SLOPE_DN" + p].iloc[29] == 0.0
    # warm-up is `left + right + 3` = 7
    assert out.iloc[:7].isna().all().all()
    assert not out.iloc[7].isna().any()


def test_cup_and_rounding_top_fixtures_are_exact():
    kw = dict(length=12, handle=3, curv_min=0.6, sym_tol=0.10, min_depth=0.05)
    p = "_12_3_0.6_0.1_0.05"

    cup = pd.Series(_cup_path(), dtype=float)
    out = rounding_cup(cup, **kw)
    assert _fires(out["CUP_CONF_BULL" + p]) == [14]
    assert _fires(out["CUP_CONF_BEAR" + p]) == []
    assert out["CUP_DEPTH" + p].iloc[14] == pytest.approx(12.6 / 100.65,
                                                          abs=1e-12)
    assert out["CUP_CURV" + p].iloc[14] > 0
    # bar 14 is the FIRST computable bar. This is the assertion that caught an
    # off-by-one warm-up of `length + handle`, which discarded it.
    assert out.iloc[:14].isna().all().all()
    assert not out.iloc[14].isna().any()

    top = pd.Series(_rounding_top_path(), dtype=float)
    out2 = rounding_cup(top, **kw)
    assert _fires(out2["CUP_CONF_BEAR" + p]) == [14]
    assert _fires(out2["CUP_CONF_BULL" + p]) == []
    assert out2["CUP_CURV" + p].iloc[14] < 0
    assert out2["CUP_DEPTH" + p].iloc[14] == pytest.approx(
        (111.95 - 99.35) / 111.95, abs=1e-9)


# ---------------------------------------------------------------------
# 2. Gate B -- future-perturbation mutants
# ---------------------------------------------------------------------
def _mutate(modname, fnname):
    """`importlib`-read the real source, back-date the confirmation write from
    `T` to `T // 2`, `exec` the result in memory. Returns the mutant function.

    This is a PERTURBING mutation, not an unsatisfiable one: the same number
    of writes happen, they simply land earlier. A mutation that stopped the
    column firing would be caught by a reachability test and would prove
    nothing about causality.
    """
    spec = importlib.util.find_spec(modname)
    src = open(spec.origin, encoding="utf8").read()
    m = src.replace("conf_bear[T] = 1.0", "conf_bear[T // 2] = 1.0") \
           .replace("conf_bull[T] = 1.0", "conf_bull[T // 2] = 1.0")
    assert m != src, f"the mutation did not apply to {modname} -- test blind"
    ns = {}
    exec(compile(m, "<mutant>", "exec"), ns)
    return ns[fnname]


def _leak(fn, name, J):
    """Perturb every bar from J onward by +50; return the largest movement on
    any co-finite cell BEFORE J, and how many cells were compared."""
    high, low, close = _rw()
    n = len(close)
    bump = 50.0 * (np.arange(n) >= J)
    kw = PROBE_KW[name]
    if name == "rounding_cup":
        a, b = fn(close=close, **kw), fn(close=close + bump, **kw)
    else:
        a = fn(high=high, low=low, close=close, **kw)
        b = fn(high=high + bump, low=low + bump, close=close + bump, **kw)
    A, B = a.iloc[:J], b.iloc[:J]
    mask = (~(A.isna() | B.isna())).to_numpy()
    return float((A[mask] - B[mask]).abs().max().max()), int(mask.sum())


@pytest.mark.parametrize("name", sorted(MODULES))
def test_gate_b_causality_with_a_back_dating_mutant(name):
    """Nothing before J may move when every bar from J onward is bumped.

    Sweeping J is deliberate -- see this file's docstring, item 2. The real
    module must be clean at EVERY J; the mutant only has to be caught at one,
    because whether a back-dated write is visible at a given J depends on
    where the confirmations happen to fall.
    """
    modname, real = MODULES[name]
    mutant = _mutate(modname, name)
    Js = (150, 200, 250, 300)

    real_leaks, mutant_leaks, cells = [], [], []
    for J in Js:
        lr, nc = _leak(real, name, J)
        lm, _ = _leak(mutant, name, J)
        real_leaks.append(lr)
        mutant_leaks.append(lm)
        cells.append(nc)

    assert min(cells) > 500, f"nothing settled to compare: {cells}"
    assert real_leaks == [0.0] * len(Js), (
        f"{name} leaks the future: {dict(zip(Js, real_leaks))}")
    assert max(mutant_leaks) > 0.0, (
        f"the back-dated mutant of {name} was NOT caught at any J "
        f"({dict(zip(Js, mutant_leaks))}) -- this test cannot certify "
        f"causality as written")


# ---------------------------------------------------------------------
# 3. Gate D -- scale invariance
# ---------------------------------------------------------------------
#: Gate D's frame. 2,000 bars, not the 500 an earlier revision used. The
#: reason is MINOR 5 of the round-2 review and it is worth stating: an
#: aggregate "0 mismatches over 3,430 co-finite cells" was dominated by the
#: flags, `*_PEND` and `*_AGE`, whose scale invariance is trivial. On 500 bars
#: the columns that could ACTUALLY break -- the magnitudes -- carried
#: HS_TGT_PCT 2 nonzero cells, CUP_DEPTH 7, CUP_CURV 7 and the three TRIW
#: magnitudes 31 each. Not vacuous, but nowhere near what the headline
#: implied. The frame is longer and the per-column floor below makes the
#: shortfall a FAILURE rather than a footnote.
GATE_D_BARS = 2000

#: Minimum NONZERO co-finite cells a column must contribute before its
#: bit-identity claim means anything. A magnitude that never fires is
#: trivially scale-invariant.
GATE_D_MIN_NONZERO = 20


def _scaled(name, fn, k, n=GATE_D_BARS):
    high, low, close = _rw(n=n, seed=11)
    kw = PROBE_KW[name]
    if name == "rounding_cup":
        return fn(close=close * k, **kw)
    return fn(high=high * k, low=low * k, close=close * k, **kw)


#: Seeds pooled for the per-column count. One 2,000-bar walk still leaves
#: `HS_CONF_BEAR` at 9 nonzero cells and `HS_CONF_BULL` at 11 -- a head and
#: shoulders is a rare shape and no single frame fixes that. Four walks is the
#: same device `test_gate_d_no_column_is_constant` already uses, for the same
#: reason: the shortfall is a property of the SAMPLE, so the honest fix is a
#: bigger sample rather than a smaller floor.
GATE_D_SEEDS = (11, 12, 13, 14)


def gate_d_cells(name, fn, k=8.0, seeds=GATE_D_SEEDS):
    """Per column: (co-finite cells, nonzero co-finite cells, mismatches),
    summed over `seeds` independent walks.

    Returned rather than asserted so the same numbers can be printed into
    `docs/CandlePatternsMeasured.md` §3 instead of being summarised away.
    """
    rows = {}
    for seed in seeds:
        high, low, close = _rw(n=GATE_D_BARS, seed=seed)
        kw = PROBE_KW[name]
        if name == "rounding_cup":
            a, b = fn(close=close, **kw), fn(close=close * k, **kw)
        else:
            a = fn(high=high, low=low, close=close, **kw)
            b = fn(high=high * k, low=low * k, close=close * k, **kw)
        for col in a.columns:
            x, y = a[col].to_numpy(float), b[col].to_numpy(float)
            m = ~np.isnan(x) & ~np.isnan(y)
            prev = rows.get(col, (0, 0, 0))
            rows[col] = (prev[0] + int(m.sum()),
                         prev[1] + int((m & (x != 0)).sum()),
                         prev[2] + int((x[m] != y[m]).sum()))
    return rows


@pytest.mark.parametrize("name", sorted(MODULES))
def test_gate_d_is_bit_identical_under_x8_and_x64(name):
    """`==`, not `np.isclose`. Powers of two rescale exactly in IEEE-754, so
    every ratio these modules emit must come back with the identical bit
    pattern; a tolerance here would hide a column that is only APPROXIMATELY
    scale-free, which is the defect Gate D exists to catch."""
    _, fn = MODULES[name]
    base = _scaled(name, fn, 1.0).to_numpy()
    for k in (8.0, 64.0):
        other = _scaled(name, fn, k).to_numpy()
        assert (np.isnan(base) != np.isnan(other)).sum() == 0, \
            f"{name} x{k}: NaN masks differ"
        m = ~np.isnan(base) & ~np.isnan(other)
        assert int((base[m] != other[m]).sum()) == 0, \
            f"{name} x{k} is not bit-identical"


@pytest.mark.parametrize("name", sorted(MODULES))
def test_gate_d_is_not_vacuous_column_by_column(name):
    """Every column must ACTUALLY EXERCISE the gate, not ride the aggregate.

    Bit-identity over a column that is 0.0 everywhere is free. The aggregate
    cell count in an earlier revision of `docs/CandlePatternsMeasured.md` §3
    was 3,430 / 2,940 / 3,928 / 3,262 -- but on that 500-bar frame the
    MAGNITUDES, the only columns whose arithmetic could break, contributed
    HS_TGT_PCT 2 nonzero cells, CUP_DEPTH 7, CUP_CURV 7 and the three TRIW
    magnitudes 31 each. This test makes that shortfall fail rather than be
    discovered in review, so a matcher that tightens until a magnitude stops
    firing cannot silently take Gate D down with it.
    """
    _, fn = MODULES[name]
    rows = gate_d_cells(name, fn)
    thin = {c: nz for c, (_, nz, _) in rows.items()
            if nz < GATE_D_MIN_NONZERO}
    assert not thin, (
        f"{name}: columns with under {GATE_D_MIN_NONZERO} nonzero co-finite "
        f"cells over {len(GATE_D_SEEDS)} x {GATE_D_BARS} bars -- Gate D is "
        f"near-vacuous for "
        f"them: {thin}")
    assert all(mm == 0 for _, _, mm in rows.values())


@pytest.mark.parametrize("name", sorted(MODULES))
def test_gate_d_survives_non_power_of_two_rescales(name):
    _, fn = MODULES[name]
    base = _scaled(name, fn, 1.0).to_numpy()
    for k in (10.0, 3.7):
        other = _scaled(name, fn, k).to_numpy()
        assert (np.isnan(base) != np.isnan(other)).sum() == 0
        m = ~np.isnan(base) & ~np.isnan(other)
        assert float(np.abs(base[m] - other[m]).max()) < 1e-12


@pytest.mark.parametrize("name", sorted(MODULES))
def test_gate_d_no_column_is_constant(name):
    """`0 < fires < n` -- a constant column cannot pass Gate D even if it is
    perfectly scale-invariant, which a constant trivially is.

    FOUR random-walk seeds are pooled, not one, and the reason is a measured
    one: on the single seed-11 500-bar frame used by the scale tests above,
    `HS_CONF_BULL_3_3_0.03_60` never fires -- an inverse head and shoulders
    simply does not occur in those 500 bars. That is a property of the SAMPLE,
    not of the column, and the honest fix is a bigger sample rather than a
    weaker assertion. Real-data reachability is a separate test.
    """
    _, fn = MODULES[name]
    kw = PROBE_KW[name]
    frames = []
    for seed in (11, 12, 13, 14):
        high, low, close = _rw(n=500, seed=seed)
        frames.append(fn(close=close, **kw) if name == "rounding_cup"
                      else fn(high=high, low=low, close=close, **kw))
    out = pd.concat(frames, axis=0, ignore_index=True)
    for col in out.columns:
        v = out[col].to_numpy(dtype=float)
        v = v[np.isfinite(v)]
        assert len(v) > 0, f"{col} is entirely NaN"
        assert v.min() != v.max(),             f"{col} is constant over 4 x 500 random-walk bars"


# ---------------------------------------------------------------------
# 4. Gate C -- reachability on real data
# ---------------------------------------------------------------------
def _real_frames(limit=8):
    import glob
    import os
    cache = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "..", "Backtesting", "datastore", "cache")
    out = []
    for path in sorted(glob.glob(os.path.join(cache, "*_1d.parquet"))):
        df = pd.read_parquet(path)
        df.columns = [str(c).lower() for c in df.columns]
        if not {"high", "low", "close"} <= set(df.columns):
            continue
        df = df.dropna()
        if len(df) < 400:
            continue
        out.append(df)
        if len(out) >= limit:
            break
    return out


@pytest.mark.parametrize("name", sorted(MODULES))
def test_gate_c_every_column_fires_on_real_data(name):
    """Every shipped column must be reachable, at the DEFAULT parameters.

    The counts recorded in `docs/CandlePatternsMeasured.md` come from the full
    50-ticker sweep; this is the 8-ticker re-derivation that keeps the claim
    testable inside this repo. It SKIPS rather than fails when the parent
    repo's cache is absent, in the same style as
    `tests/test_candle_patterns_reachable.py`.
    """
    frames = _real_frames()
    if not frames:
        pytest.skip("Backtesting/datastore/cache is not present")
    _, fn = MODULES[name]
    nonzero = None
    bars = 0
    for df in frames:
        out = fn(close=df.close) if name == "rounding_cup" else \
            fn(high=df.high, low=df.low, close=df.close)
        bars += len(df)
        v = (out.to_numpy(dtype=float) != 0) & np.isfinite(
            out.to_numpy(dtype=float))
        counts = v.sum(axis=0)
        nonzero = counts if nonzero is None else nonzero + counts
    dead = [c for c, k in zip(out.columns, nonzero) if k == 0]
    assert not dead, f"{name}: dead columns over {bars} real bars: {dead}"


# ---------------------------------------------------------------------
# 5. wiring, validation, naming
# ---------------------------------------------------------------------
@pytest.mark.parametrize("name", sorted(MODULES))
def test_registered_and_reachable_through_the_accessor(name):
    """`Category` membership and a `df.ta.<name>()` accessor. Touch points 3
    and 4 of `CLAUDE.md`'s five -- the pair that drifted apart once and made
    eleven indicators raise `AttributeError` from `df.ta.strategy()`."""
    assert name in ta.Category["trend"]
    df = _ohlc(_hs_bear_path() * 3)
    got = getattr(df.ta, name)(**PROBE_KW[name])
    assert isinstance(got, pd.DataFrame) and not got.empty


@pytest.mark.parametrize("name", sorted(MODULES))
def test_offset_shifts_every_column(name):
    _, fn = MODULES[name]
    # n=500 explicitly: `_scaled` defaults to GATE_D_BARS, which round 2 raised
    # 500 -> 2,000 so the magnitude columns would carry enough nonzero cells.
    # That silently made `a` four times longer than `b` here, and the boolean
    # mask stopped matching the array it indexed.
    a = _scaled(name, fn, 1.0, n=500)
    high, low, close = _rw(n=500, seed=11)
    kw = dict(PROBE_KW[name], offset=2)
    b = fn(close=close, **kw) if name == "rounding_cup" else \
        fn(high=high, low=low, close=close, **kw)
    assert list(a.columns) == list(b.columns)
    shifted = a.shift(2)
    m = (~a.shift(2).isna() & ~b.isna()).to_numpy()
    assert m.sum() > 1000
    assert float(np.abs(shifted.to_numpy()[m] - b.to_numpy()[m]).max()) == 0.0


@pytest.mark.parametrize("name", sorted(MODULES))
def test_bad_parameters_raise_rather_than_silently_defaulting(name):
    _, fn = MODULES[name]
    high, low, close = _rw(n=120)
    call = (lambda **k: fn(close=close, **k)) if name == "rounding_cup" else \
        (lambda **k: fn(high=high, low=low, close=close, **k))
    key = "length" if name == "rounding_cup" else "left"
    for bad in (0, -1, 2.5, float("nan"), float("inf"), True, "five"):
        with pytest.raises(ValueError):
            call(**{key: bad})


#: One perturbed value per numeric parameter of each matcher. Chosen to be
#: legal (they must pass the validators) and to have a real chance of moving
#: the output on the probe frame.
PARAM_PERTURBATIONS = {
    "head_shoulders": {"left": 4, "right": 4, "tol": 0.08, "max_wait": 25},
    "triple_top_bottom": {"left": 4, "right": 4, "tol": 0.08, "max_wait": 25},
    "triangle_wedge": {"left": 4, "right": 4, "max_wait": 25},
    "rounding_cup": {"length": 34, "handle": 7, "curv_min": 0.4,
                     "sym_tol": 0.04, "min_depth": 0.30},
}


def _named_run(name, fn, **over):
    high, low, close = _rw(n=800, seed=11)
    kw = dict(PROBE_KW[name], **over)
    out = fn(close=close, **kw) if name == "rounding_cup" else \
        fn(high=high, low=low, close=close, **kw)
    return list(out.columns), out.to_numpy()


def _name_property_violations(name, fn):
    """Every numeric parameter, perturbed one at a time. Returns the list of
    violations of:

        output changed   =>  name changed      (no silent collision)
        output unchanged =>  name unchanged    (no false promise)

    Factored out of the test so the MUTANT below can run the identical check
    against deliberately broken modules and show it fires.
    """
    base_cols, base_vals = _named_run(name, fn)
    bad = []
    for param, value in PARAM_PERTURBATIONS[name].items():
        cols, vals = _named_run(name, fn, **{param: value})
        same_name = cols == base_cols
        same_vals = vals.shape == base_vals.shape and bool(
            ((np.isnan(base_vals) == np.isnan(vals)) &
             ((base_vals == vals) | np.isnan(base_vals))).all())
        if not same_vals and same_name:
            bad.append(f"{name}.{param}: CHANGES the output but not the name "
                       f"({base_cols[0]}) -- a silent collision")
        if same_vals and not same_name:
            bad.append(f"{name}.{param}: is in the name but did NOT change "
                       f"the output ({base_cols[0]} -> {cols[0]}) -- either "
                       f"dead, or this frame cannot reach it; check by hand")
    return bad


@pytest.mark.parametrize("name", sorted(MODULES))
def test_a_parameter_that_changes_the_output_changes_the_name(name):
    """Naming is API -- `CLAUDE.md`. The parent repo matches mined-strategy
    rules on these strings, so two DIFFERENT features must never share a name,
    and one feature must never wear two.

    This replaced four literal-string assertions that could not see either of
    the two real defects sitting next to them, both since fixed:

      * `rounding_cup` computed with `min_depth` and left it OUT of the
        suffix. Measured on this exact frame: `min_depth=0.05` fires
        `CUP_CONF_BULL` 4 times, `min_depth=0.30` fires it 0 times, and both
        emitted `CUP_CONF_BULL_30_5_0.6_0.1`.
      * `triangle_wedge` put `tol` IN the suffix and never read it:
        `tol=0.03` and `tol=0.99` gave bit-identical output under
        `TRIW_CONF_BEAR_3_3_0.03_60` and `TRIW_CONF_BEAR_3_3_0.99_60`.

    The second direction of the property is the weaker one and is kept
    deliberately: a parameter that cannot move the output on an 800-bar walk
    is not PROOF that it is dead, so a failure there is a prompt to check by
    hand, and the message says so rather than pretending to a verdict.
    """
    _, fn = MODULES[name]
    bad = _name_property_violations(name, fn)
    assert bad == [], "\n".join(bad)


def test_the_naming_property_catches_both_defects_it_was_written_for():
    """The detector, pinned. A property test that cannot fail is decoration.

    Two `importlib` + `exec` mutants of the REAL module source, one per
    defect direction, each checked with `_name_property_violations` -- the
    same function the test above uses, so this certifies that function and
    not a paraphrase of it.
    """
    import importlib.util

    def _mutate(modname, fnname, pairs):
        src = open(importlib.util.find_spec(modname).origin,
                   encoding="utf8").read()
        m = src
        for a, b in pairs:
            assert m.count(a) == 1, f"mutation anchor missing: {a[:60]}"
            m = m.replace(a, b)
        assert m != src, "the mutation did not apply -- this test is blind"
        ns = {}
        exec(compile(m, "<mutant>", "exec"), ns)
        return ns[fnname]

    # (1) a LIVE parameter dropped from the name -> silent collision
    cup = _mutate(
        "pandas_ta.trend.rounding_cup", "rounding_cup",
        [('_props = f"_{length}_{handle}_{curv_min}_{sym_tol}_{min_depth}"',
          '_props = f"_{length}_{handle}_{curv_min}_{sym_tol}"')])
    bad = _name_property_violations("rounding_cup", cup)
    assert any("min_depth" in b and "silent collision" in b for b in bad), bad

    # (2) a DEAD parameter advertised in the name -> false promise
    triw = _mutate(
        "pandas_ta.trend.triangle_wedge", "triangle_wedge",
        [# `_validated_float` is no longer imported by the real module -- it
         # became unused when `tol` was deleted -- so the mutant has to put
         # the import back before it can call it. Without this pair the
         # mutant dies on NameError and the test silently stops testing.
         ("from pandas_ta.trend._patternlib import (\n"
          "    _line_at, _pivot_stream, _validated_int,\n)",
          "from pandas_ta.trend._patternlib import (\n"
          "    _line_at, _pivot_stream, _validated_float, _validated_int,\n)"),
         ("def triangle_wedge(high, low, close, left=None, right=None, "
          "max_wait=None,\n                   offset=None, **kwargs):",
          "def triangle_wedge(high, low, close, left=None, right=None, "
          "max_wait=None,\n                   tol=None, offset=None, **kwargs):"),
         ('    max_wait = _validated_int(max_wait, 60, "max_wait")\n'
          "    offset = get_offset(offset)",
          '    max_wait = _validated_int(max_wait, 60, "max_wait")\n'
          '    tol = _validated_float(tol, 0.03, "tol")\n'
          "    offset = get_offset(offset)"),
         ('_props = f"_{left}_{right}_{max_wait}"',
          '_props = f"_{left}_{right}_{tol}_{max_wait}"')])
    saved = PARAM_PERTURBATIONS["triangle_wedge"]
    try:
        PARAM_PERTURBATIONS["triangle_wedge"] = dict(saved, tol=0.99)
        bad = _name_property_violations("triangle_wedge", triw)
    finally:
        PARAM_PERTURBATIONS["triangle_wedge"] = saved
    assert any("tol" in b and "did NOT change" in b for b in bad), bad

    # and the real modules are clean under the same check
    for nm, (_, fn) in sorted(MODULES.items()):
        assert _name_property_violations(nm, fn) == []


def test_the_rectangle_is_skipped_and_the_evidence_still_reproduces():
    """The pre-registered trigger fired, so `triangle_wedge` emits NO rectangle.

    `docs/CandlePatternShortlist.md` §5 item 5 set the trigger before this
    module existed: SKIP at +/-3-bar recall >= ~0.69 against `LCB_BREAKOUT_*`.
    Measured on 250 BIST tickers / 343,638 bars with the population read out of
    `_scan` itself: RECT_UP 811 events, recall 0.7102 +/- 0.0159; RECT_DN 756
    events, recall 0.6958 +/- 0.0167. Above 0.69 on the point estimate and with
    0.69 below the 1-SE band, so it fires on the literal AND the noise-aware
    reading.

    Two things are pinned here, and the second is the one that rots:

    1. the shipped scan emits no rectangle confirmation at all;
    2. `include_rect=True` STILL DOES, so the measurement that justified the
       skip can be re-run. A decision whose evidence has been deleted along
       with the thing it decided about cannot be reviewed, and this repo has
       an explicit rule against claims with no run behind them.
    """
    from pandas_ta.trend.triangle_wedge import _scan

    high, low, close = _rw(n=4000, seed=3)
    shipped = _scan(high, low, close, 3, 3, 60)
    evidence = _scan(high, low, close, 3, 3, 60, include_rect=True)

    assert shipped["rect_up"].sum() == 0.0
    assert shipped["rect_dn"].sum() == 0.0
    n_rect = int(evidence["rect_up"].sum() + evidence["rect_dn"].sum())
    assert n_rect > 0, (
        "include_rect=True produced no rectangles either, so this test cannot "
        "tell a working skip from a matcher that stopped finding them")

    # and the skip REMOVES confirmations rather than relabelling them
    s_conf = int(np.nansum(shipped["conf_bull"] == 1) +
                 np.nansum(shipped["conf_bear"] == 1))
    e_conf = int(np.nansum(evidence["conf_bull"] == 1) +
                 np.nansum(evidence["conf_bear"] == 1))
    assert e_conf - s_conf > 0
    assert e_conf - s_conf <= n_rect, (
        "the skip removed more confirmations than there were rectangles")

    # the public function never exposes a rectangle either
    df = _ohlc(_hs_bear_path() * 6)
    out = triangle_wedge(df.high, df.low, df.close)
    flat = ((out["TRIW_SLOPE_UP_5_5_60"].abs() < 0.0015) &
            (out["TRIW_SLOPE_DN_5_5_60"].abs() < 0.0015) &
            ((out["TRIW_CONF_BULL_5_5_60"] == 1.0) |
             (out["TRIW_CONF_BEAR_5_5_60"] == 1.0)))
    assert not flat.any(), (
        "a confirmation with two flat published slopes survived the skip; note "
        "this proxy has false positives, so a failure here needs _scan to "
        "confirm before it is called a rectangle")


def test_the_shipped_suffixes_are_the_documented_ones():
    """The exact default names, so a rename is a deliberate act.

    Two recorded deviations from `docs/CandlePatternShortlist.md` §4:

      * it wrote the cup default as `..._0.10`; Python renders the float
        `0.10` as `0.1`, so `CUP_CONF_BULL_40_10_0.6_0.10` is not a name this
        package can produce. The shipped suffix also carries `min_depth`,
        which §4 did not propose and which the test above proves is live.
      * `triangle_wedge` has NO `tol`, so its suffix is
        `_{left}_{right}_{max_wait}`, breaking the four-module parity §4
        assumed. Parity with a dead parameter is not parity.
    """
    df = _ohlc(_hs_bear_path() * 6)
    assert "HS_CONF_BEAR_5_5_0.03_60" in head_shoulders(
        df.high, df.low, df.close).columns
    assert "TRPL_CONF_BEAR_5_5_0.03_60" in triple_top_bottom(
        df.high, df.low, df.close).columns
    assert "TRIW_CONF_BULL_5_5_60" in triangle_wedge(
        df.high, df.low, df.close).columns
    assert "CUP_CONF_BULL_40_10_0.6_0.1_0.05" in rounding_cup(
        df.close).columns


def test_no_column_is_a_raw_price_level():
    """The forbidden-column list from `docs/CandlePatternShortlist.md` §4:
    no neckline / boundary / rim price, no width in points, no bar index.

    Enforced by CONSEQUENCE rather than by name: run the same frame at x1 and
    x1000 and assert nothing changed. A raw price level cannot survive that,
    and neither can a point width or a bar count that has been divided by
    nothing.
    """
    for name, (_, fn) in sorted(MODULES.items()):
        a = _scaled(name, fn, 1.0).to_numpy()
        b = _scaled(name, fn, 1000.0).to_numpy()
        m = ~np.isnan(a) & ~np.isnan(b)
        assert float(np.abs(a[m] - b[m]).max()) < 1e-9, \
            f"{name} carries a price-scaled column"
