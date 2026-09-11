# -*- coding: utf-8 -*-
"""PINEBI-1c -- the seven TradingView `ta` alternates that earned a column,
and the two that did not.

Source for all nine: `docs/pine/RA2vGpkA-ta.pine` (untracked; see
CLAUDE.md), the TradingView/`ta` Pine v5 library, MPL-2.0, (c) TradingView.

WHAT THIS MODULE PINS, IN ORDER OF HOW MUCH IT WOULD HURT TO LOSE
-----------------------------------------------------------------

1. THE DELETION DECISION.  `stochFull` (Pine L541-544) and `stochRsi`
   (L554-558) are NOT in the package, and the reason is measured, not
   asserted: `ta.stoch(k=periodK, d=periodD, smooth_k=smoothK)` and
   `ta.stochrsi(length=periodK, rsi_length=lengthRsi, k=smoothK, d=periodD)`
   reproduce them **bit for bit** -- max|diff| == 0.0 on GRID_S, and rho ==
   1.0000 on all 40 tickers of Grid A.  The task text's hint that
   `stochFull` reaches "a separate %K smoothing" the sibling cannot express
   is WRONG; `stoch` has carried `smooth_k` separately from `d` all along,
   and `test_the_two_deleted_alternates_are_exactly_the_siblings` is what
   establishes it.  If either is ever re-added, this test fails and says
   why not to.

2. WARM-UP SAVED -- the axis that kept the other seven.  Every survivor is
   rho ~ 1.0 against its sibling, so the standing "rho >= 0.9 -> revert"
   rule would delete all seven unread; PINEBI-1c suspends it and
   substitutes warm-up and parameter reach.  Measured on GRID_S (defined
   once below) and reproduced identically on all 40 Grid A tickers:

       ema2        vs ema(10)              9 -> 0    9 bars
       rma2        vs wilder_rma(10)       9 -> 0    9 bars
       dema2       vs dema(10)             9 -> 0    9 bars
       tema2       vs tema(10)             9 -> 0    9 bars
       t3_tv       vs t3(10, 0.7)          9 -> 0    9 bars
       atr2        vs atr(14)             14 -> 0   14 bars
       supertrend2 vs supertrend(7, 3.0)   7 -> 0    7 bars

   Two things here were guessed wrong before they were measured, and the
   test exists so nobody re-guesses them:
     * Chaining EMAs does NOT multiply the warm-up.  `dema`/`tema`/`t3`
       stack 2/3/6 SMA-seeded `ema` calls, and the arithmetic guess
       (18/27/54 bars at length=10) is wrong -- the nested `ema` re-seeds
       from a window holding one finite value, so all three settle at 9.
     * Warm-up is measured as FIRST-STABLE (the index after the LAST NaN),
       not first-finite.  `pandas_ta.supertrend` pre-fills its `trend` list
       with 0 and never overwrites index 0, so first-finite scores it as 0
       and reports `supertrend2` saving nothing.  It saves 7.

3. PARAMETER REACH, established by CALLING the sibling, not by reading its
   signature.  Every sibling raises `ValueError: The truth value of a
   Series is ambiguous` on a per-bar length (they all do
   `int(length) if length and length > 0`).  Two more reach failures are
   silent wrong answers rather than errors:
     * `t3(a=1.5)` returns a column *named* `T3_10_0.7`, numerically
       identical to `a=0.7`.  The clamp `a > 0 and a < 1` swallows it.
     * `supertrend(wicks=True)` swallows `wicks` into `**kwargs` and
       returns an identical frame.

4. WHICH SIBLING `rma2` IS COMPARED AGAINST.  `pandas_ta.rma` is
   `ewm(alpha=1/length, adjust=True)` and is NOT Wilder's smoothing;
   `pandas_ta.wilder_rma` is.  Pine's `ta.rma` is Wilder's, so `wilder_rma`
   is the sibling.  Pinned so nobody "simplifies" the comparison back to
   `rma`.

5. CAUSALITY, with mutants.  The two state-carrying pieces -- the
   `dynamic_ewma` recursion six of the seven ride on, and `supertrend2`'s
   band loop -- are certified by FUTURE PERTURBATION (shift every bar from
   J onward, assert nothing before J moves), because prefix truncation
   cannot see a back-dated write.  Each mutant is shown to be caught; the
   real modules leak 0.0.

6. THE SAME STANDARD, APPLIED TO THESE SEVEN.  Round 1 indicted `t3` for
   silently clamping a parameter and naming the column for a value the call
   did not use -- and then did it six times over.  Four tests exist because
   round 1 shipped without them:
     * `test_the_two_paths_of_one_length_argument_agree` -- `ema2(close, -5)`
       returned `EMA2_10`, bit-identical to `length=10`, while
       `ema2(close, Series(-5))` clamped to 1.  One argument, two answers,
       and neither was L159's `math.max(1.0, length)`.  Both paths now run
       Pine's clamp and the name carries the EFFECTIVE value (`EMA2_1`).
     * `test_the_unclamped_parameters_are_passed_through_because_pine_does_not_clamp`
       -- L661 (`vf`) and L602 (`factor`) carry no bound, so neither does
       this port.  `T3tv_10_0.0`, `SUPERT2_7_0.0`.
     * `test_supertrend2_takes_a_per_bar_factor_because_l602_declares_one`
       -- L602 declares BOTH parameters `series float`.  Round 1 ported one
       and guarded the other with `float(multiplier) if multiplier and
       multiplier > 0`, which raises on a Series: the module reproduced in
       its own body the failure it records against the sibling.
     * `test_two_different_per_bar_lengths_do_not_share_a_column_name` --
       `_dyn` alone collided, so `append=True` silently overwrote the first
       column in the one call shape the module was kept for.  The token is
       now `dyn<min>-<max>-<8 hex blake2b>`.

7. WIRING and NAMING.  All seven reach `Category`, `df.ta.<name>()` and the
   package namespace, and no survivor column name collides with a shipped
   one.  Naming is API here: mined rules in the parent repo match on these
   strings.

WHAT THIS MODULE DOES NOT CLAIM
--------------------------------
The 9 bars of saved warm-up are real per COLUMN and buy ZERO usable ROWS in
the only consumer that exists.  Receipt:
`backtest_results/tvpta6/pine_alternates_warmup_materiality.csv`, from
`run_materiality()` in `measure_pine_alternates.py` --
`IndicatorEngine(include_advanced=False).compute_all`, DatetimeIndex left
alone, 365 numeric columns; per-column first-valid position is median 9 /
p90 88 / max 499 (`HARPARK_1_5_22_500`) on ACSEL.IS and median 13 / p90 123 /
max 2779 (`tom_pos`, a CALENDAR feature; 623 excluding the five calendar
columns) on AKBNK.IS.  A row is gated by the SLOWEST column.  Both acceptance
axes were still measured, which is what keeps the 7/9 split standing -- but
six of the seven now rest on parameter reach alone, all seven are `PX`, and
there are no call sites outside this file.  `docs/PineAlternatesMeasured.md`
says so in as many words.

The seven are price-scale overlays (six moving averages plus an ATR and a
SuperTrend line), exactly like the siblings they extend.  They do NOT clear
Gate D of the ML feature contract and are not offered as scale-free
features; they ship on the same footing as `EMA_10` and `ATRr_14`, as raw
material for ratios.  `test_the_survivors_are_price_scale_like_their_siblings`
records that rather than leaving a later reader to assume otherwise.

The full run these numbers are the synthetic slice of is
`Backtesting/scripts/analysis/measure_pine_alternates.py`; the KEEP/DELETE
table is `docs/PineAlternatesMeasured.md`.
"""
import importlib.util

import numpy as np
import pytest
from pandas import DataFrame, Series

from tests.context import pandas_ta as ta

from pandas_ta.overlap.dema2 import dema2
from pandas_ta.overlap.ema2 import dynamic_ewma, ema2
from pandas_ta.overlap.rma2 import rma2
from pandas_ta.overlap.supertrend2 import supertrend2
from pandas_ta.overlap.t3_tv import t3_tv
from pandas_ta.overlap.tema2 import tema2
from pandas_ta.overlap.wilder_rma import wilder_rma
from pandas_ta.volatility.atr2 import atr2


# --------------------------------------------------------------- the fixture
N = 400
SEED = 1729


def grid_s():
    """GRID_S -- the one fixture every number in this file was measured on.

    A 400-bar seeded geometric walk with a symmetric high/low spread.  Same
    definition as `measure_pine_alternates.py`, so the figures here and the
    figures in `docs/PineAlternatesMeasured.md` are the same measurement.
    """
    rng = np.random.default_rng(SEED)
    close = Series(100 * np.exp(np.cumsum(rng.normal(0, 0.01, N))))
    spread = Series(np.abs(rng.normal(0, 0.6, N)) + 0.05)
    return close + spread, close - spread, close


def first_stable(s):
    """Index after the LAST NaN -- see point 2 of the module docstring."""
    nan_idx = np.flatnonzero(Series(np.asarray(s, dtype=float)).isna().to_numpy())
    return int(nan_idx[-1]) + 1 if nan_idx.size else 0


def spearman(a, b):
    a = Series(np.asarray(a, dtype=float))
    b = Series(np.asarray(b, dtype=float))
    m = (a.notna() & b.notna()).to_numpy()
    return float(a[m].corr(b[m], method="spearman"))


# ------------------------------------------------------- 1. the two deletions
def test_the_two_deleted_alternates_are_exactly_the_siblings():
    """Why `stochFull` and `stochRsi` are not in the package.

    Both are a composition of shipped pieces, and the shipped sibling takes
    every parameter they take.  Measured below on GRID_S: max|diff| == 0.0
    at the default parameters AND at a parameter set where `smoothK` and
    `periodD` differ, which is the case the task text expected to be
    unreachable.  Grid A: rho == 1.0 on all 40 tickers.

    Zero warm-up saved and zero parameter reach -> DELETE.
    """
    high, low, close = grid_s()

    def stoch_full_pine(period_k, smooth_k, period_d):
        # Pine L541-544
        ll, hh = low.rolling(period_k).min(), high.rolling(period_k).max()
        k = ta.sma(100 * (close - ll) / (hh - ll), length=smooth_k)
        return k, ta.sma(k, length=period_d)

    def stoch_rsi_pine(length_rsi, period_k, smooth_k, period_d):
        # Pine L554-558
        r = ta.rsi(close, length=length_rsi)
        ll, hh = r.rolling(period_k).min(), r.rolling(period_k).max()
        k = ta.sma(100 * (r - ll) / (hh - ll), length=smooth_k)
        return k, ta.sma(k, length=period_d)

    # default parameters
    sib = ta.stoch(high, low, close, k=14, d=3, smooth_k=3)
    k, d = stoch_full_pine(14, 3, 3)
    assert np.nanmax(np.abs(sib["STOCHk_14_3_3"] - k)) == 0.0
    assert np.nanmax(np.abs(sib["STOCHd_14_3_3"] - d)) == 0.0

    # the case the task text expected `stoch` could not express: smoothK != periodD
    sib = ta.stoch(high, low, close, k=14, d=3, smooth_k=5)
    k, d = stoch_full_pine(14, 5, 3)
    assert np.nanmax(np.abs(sib["STOCHk_14_3_5"] - k)) == 0.0
    assert np.nanmax(np.abs(sib["STOCHd_14_3_5"] - d)) == 0.0

    # stochRsi, with an RSI length independent of the stochastic window
    sib = ta.stochrsi(close, length=21, rsi_length=14, k=5, d=3)
    k, d = stoch_rsi_pine(14, 21, 5, 3)
    assert np.nanmax(np.abs(sib["STOCHRSIk_21_14_5_3"] - k)) == 0.0
    assert np.nanmax(np.abs(sib["STOCHRSId_21_14_5_3"] - d)) == 0.0

    # and they stay deleted
    for gone in ("stoch_full", "stochfull", "stoch_rsi_tv", "stochrsi_tv"):
        assert not hasattr(ta, gone), f"{gone} was re-added without re-measuring"


# ----------------------------------------------------------- 2. warm-up saved
WARMUP = [
    # candidate, sibling first-stable, alternate first-stable
    ("ema2", 9, 0),
    ("rma2", 9, 0),
    ("dema2", 9, 0),
    ("tema2", 9, 0),
    ("t3_tv", 9, 0),
    ("atr2", 14, 0),
    ("supertrend2", 7, 0),
]


def _pairs():
    high, low, close = grid_s()
    return {
        "ema2": (ta.ema(close, length=10), ema2(close, length=10)),
        "rma2": (wilder_rma(close, length=10), rma2(close, length=10)),
        "dema2": (ta.dema(close, length=10), dema2(close, length=10)),
        "tema2": (ta.tema(close, length=10), tema2(close, length=10)),
        "t3_tv": (ta.t3(close, length=10, a=0.7), t3_tv(close, length=10, vf=0.7)),
        "atr2": (ta.atr(high, low, close, length=14),
                 atr2(high, low, close, length=14)),
        "supertrend2": (
            ta.supertrend(high, low, close, length=7, multiplier=3.0)["SUPERT_7_3.0"],
            supertrend2(high, low, close, length=7, multiplier=3.0)["SUPERT2_7_3.0"]),
    }


@pytest.mark.parametrize("name,sib_stable,alt_stable", WARMUP)
def test_warm_up_saved_is_what_kept_this_alternate(name, sib_stable, alt_stable):
    """AXIS 1: bars of warm-up the alternate saves over its sibling."""
    sib, alt = _pairs()[name]
    assert first_stable(sib) == sib_stable, f"{name}: sibling warm-up moved"
    assert first_stable(alt) == alt_stable, f"{name}: alternate warm-up moved"
    assert sib_stable - alt_stable > 0, f"{name} saves no warm-up -- delete it"


def test_chaining_emas_does_not_multiply_the_warm_up():
    """The guess that killed the first draft of the docstrings.

    `dema`/`tema`/`t3` stack 2/3/6 SMA-seeded `ema` calls.  If each stage
    added `length - 1` bars, they would settle at 18/27/54 with length=10.
    They settle at 9, because the inner `ema` re-seeds with
    `mean(ema1[0:length])` over a window holding exactly one finite value.
    """
    _, _, close = grid_s()
    assert first_stable(ta.dema(close, length=10)) == 9
    assert first_stable(ta.tema(close, length=10)) == 9
    assert first_stable(ta.t3(close, length=10)) == 9
    for guess in (18, 27, 54):
        assert first_stable(ta.t3(close, length=10)) != guess


def test_first_finite_would_have_scored_supertrend_wrong():
    """Why warm-up is measured as first-stable, not first-valid-index.

    `supertrend` pre-fills `trend = [0] * m` and its loop starts at i=1, so
    index 0 keeps a spurious finite 0.0 followed by 7 NaNs.  Under
    first-finite the sibling scores 0 and `supertrend2` appears to save
    nothing; under first-stable it saves 7.
    """
    high, low, close = grid_s()
    sib = ta.supertrend(high, low, close, length=7, multiplier=3.0)["SUPERT_7_3.0"]
    assert sib.first_valid_index() == 0
    assert sib.iloc[0] == 0.0
    assert bool(sib.iloc[1:7].isna().all())   # indices 1..6, six NaNs
    assert first_stable(sib) == 7


# --------------------------------------------------------- 3. parameter reach
SERIES_LENGTH_SIBLINGS = [
    ("ema2", lambda h, l, c, n: ta.ema(c, length=n)),
    ("rma2", lambda h, l, c, n: wilder_rma(c, length=n)),
    ("dema2", lambda h, l, c, n: ta.dema(c, length=n)),
    ("tema2", lambda h, l, c, n: ta.tema(c, length=n)),
    ("t3_tv", lambda h, l, c, n: ta.t3(c, length=n)),
    ("atr2", lambda h, l, c, n: ta.atr(h, l, c, length=n)),
    ("supertrend2", lambda h, l, c, n: ta.supertrend(h, l, c, length=n, multiplier=3.0)),
]

SERIES_LENGTH_ALTERNATES = [
    ("ema2", lambda h, l, c, n: ema2(c, length=n), "EMA2_dyn5-30-7c148edc"),
    ("rma2", lambda h, l, c, n: rma2(c, length=n), "RMA2_dyn5-30-7c148edc"),
    ("dema2", lambda h, l, c, n: dema2(c, length=n), "DEMA2_dyn5-30-7c148edc"),
    ("tema2", lambda h, l, c, n: tema2(c, length=n), "TEMA2_dyn5-30-7c148edc"),
    ("t3_tv", lambda h, l, c, n: t3_tv(c, length=n), "T3tv_dyn5-30-7c148edc_0.7"),
    ("atr2", lambda h, l, c, n: atr2(h, l, c, length=n), "ATR2_dyn5-30-7c148edc"),
]


@pytest.mark.parametrize("name,call", SERIES_LENGTH_SIBLINGS)
def test_the_sibling_cannot_take_a_per_bar_length(name, call):
    """AXIS 2, probed by calling: every sibling does `int(length)`.

    `length = int(length) if length and length > 0 else <default>` evaluates
    a Series in a boolean context, so a per-bar length is not truncated or
    ignored -- it raises.
    """
    high, low, close = grid_s()
    varying = Series(np.linspace(5, 30, N))
    with pytest.raises(ValueError, match="truth value of a Series is ambiguous"):
        call(high, low, close, varying)


@pytest.mark.parametrize("name,call,column", SERIES_LENGTH_ALTERNATES)
def test_the_alternate_honours_a_per_bar_length(name, call, column):
    """And the alternate does honour it, under a per-Series `_dyn` column name.

    The token is `dyn<min>-<max>-<8 hex>`; the digest is `blake2b` of the
    float64 buffer, so it is stable across runs and processes (Python's
    `hash()` is salted per process and would have made these names
    irreproducible). The literals below are that stable value.
    """
    high, low, close = grid_s()
    varying = Series(np.linspace(5, 30, N))
    dyn = call(high, low, close, varying)
    fixed = call(high, low, close, 10)
    assert dyn.name == column, f"{name}: per-bar column name is API -- do not rename"
    assert not np.allclose(dyn.to_numpy(float), fixed.to_numpy(float)), (
        f"{name}: the per-bar length made no difference, so it is not honoured")


def test_supertrend2_honours_a_per_bar_atr_length():
    high, low, close = grid_s()
    varying = Series(np.linspace(5, 30, N))
    dyn = supertrend2(high, low, close, length=varying, multiplier=3.0)
    fixed = supertrend2(high, low, close, length=7, multiplier=3.0)
    assert list(dyn.columns) == ["SUPERT2_dyn5-30-7c148edc_3.0",
                                 "SUPERT2d_dyn5-30-7c148edc_3.0",
                                 "SUPERT2l_dyn5-30-7c148edc_3.0",
                                 "SUPERT2s_dyn5-30-7c148edc_3.0"]
    assert not np.allclose(dyn.iloc[:, 0].to_numpy(float),
                           fixed.iloc[:, 0].to_numpy(float))


# --------------------------- 3b. the same standard, applied to THIS module
#
# Round 1 indicted `t3` for "silently clamps a volume factor and the name does
# not admit it" and then committed the same fault six times over. These four
# tests are the ones that would have caught it.
NON_POSITIVE_LENGTH = [
    ("ema2", lambda c, n: ema2(c, length=n), "EMA2_1"),
    ("rma2", lambda c, n: rma2(c, length=n), "RMA2_1"),
    ("dema2", lambda c, n: dema2(c, length=n), "DEMA2_1"),
    ("tema2", lambda c, n: tema2(c, length=n), "TEMA2_1"),
    # t3_tv takes a length too and was the one survivor left unguarded in
    # round 2, while the docstring above claimed six of seven were pinned.
    ("t3_tv", lambda c, n: t3_tv(c, length=n), "T3tv_1_0.7"),
]


@pytest.mark.parametrize("name,call,expected", NON_POSITIVE_LENGTH)
def test_the_two_paths_of_one_length_argument_agree(name, call, expected):
    """A non-positive length must mean the SAME thing scalar or per-bar.

    Round 1 they did not. The scalar path sent `length <= 0` back to the
    DEFAULT -- `ema2(close, -5)` was bit-identical to `length=10` and was
    NAMED `EMA2_10` -- while the Series path clamped to 1 inside the caller's
    `np.maximum(1.0, lengths)`. One argument, two answers, and neither was the
    Pine line the module cites: L159 is `math.max(1.0, length)`, a clamp to 1.

    Now both paths run Pine's clamp, and the name carries the EFFECTIVE value,
    so a caller who passed -5 is told they got 1.
    """
    _, _, close = grid_s()
    scalar = call(close, -5)
    series = call(close, Series(np.full(N, -5.0)))
    assert np.allclose(scalar.to_numpy(float), series.to_numpy(float),
                       equal_nan=True), (
        f"{name}: the scalar and per-bar paths of length=-5 disagree")
    assert np.allclose(scalar.to_numpy(float),
                       call(close, 1).to_numpy(float), equal_nan=True), (
        f"{name}: length=-5 did not clamp to Pine's floor of 1")
    assert scalar.name == expected, (
        f"{name}: the column is named for a length the call did not use")
    assert not np.allclose(scalar.to_numpy(float),
                           call(close, 10).to_numpy(float), equal_nan=True), (
        f"{name}: length=-5 still falls back to the default")


def test_atr2_and_supertrend2_clamp_the_length_the_same_way():
    """The same rule on the two H/L/C alternates."""
    high, low, close = grid_s()
    assert atr2(high, low, close, length=-5).name == "ATR2_1"
    assert np.allclose(
        atr2(high, low, close, length=-5).to_numpy(float),
        atr2(high, low, close, length=Series(np.full(N, -5.0))).to_numpy(float),
        equal_nan=True)
    assert list(supertrend2(high, low, close, length=-5,
                            multiplier=3.0).columns)[0] == "SUPERT2_1_3.0"


def test_the_unclamped_parameters_are_passed_through_because_pine_does_not_clamp():
    """`vf` (L661) and `factor` (L602) carry no bound in Pine, so none here.

    `vf=0` collapses the generalised DEMA to a plain EMA chain -- a legal,
    meaningful configuration. Round 1 rejected it back to 0.7 and named the
    column `T3tv_10_0.7`, which is precisely the `t3(a=1.5) -> T3_10_0.7`
    defect this port exists to indict.
    """
    high, low, close = grid_s()
    zero_vf = t3_tv(close, length=10, vf=0.0)
    assert zero_vf.name == "T3tv_10_0.0"
    assert not np.allclose(zero_vf.to_numpy(float),
                           t3_tv(close, length=10, vf=0.7).to_numpy(float))
    # vf=0 IS the triple EMA chain, asserted rather than assumed
    e3 = ema2(close=ema2(close=ema2(close=close, length=10), length=10), length=10)
    assert np.allclose(zero_vf.to_numpy(float), e3.to_numpy(float))

    assert list(supertrend2(high, low, close, 7, 0.0).columns)[0] == "SUPERT2_7_0.0"


def test_supertrend2_takes_a_per_bar_factor_because_l602_declares_one():
    """L602: `supertrend2(series float factor, series float atrLength, ...)`.

    Round 1 ported one of the two and guarded the other with
    `float(multiplier) if multiplier and multiplier > 0`, which raises on a
    Series -- the identical idiom this module's own parameter-reach table
    records as the SIBLING's failure. Both are per-bar capable now.
    """
    high, low, close = grid_s()
    varying = Series(np.linspace(2, 4, N))
    dyn = supertrend2(high, low, close, length=7, multiplier=varying)
    fixed = supertrend2(high, low, close, length=7, multiplier=3.0)
    assert list(dyn.columns)[0] == "SUPERT2_7_dyn2.0-4.0-882ee074"
    assert not np.allclose(dyn.iloc[:, 0].to_numpy(float),
                           fixed.iloc[:, 0].to_numpy(float))
    # and the sibling still cannot: the failure mode is the one recorded
    with pytest.raises(ValueError, match="truth value of a Series is ambiguous"):
        ta.supertrend(high, low, close, length=7, multiplier=varying)


def test_two_different_per_bar_lengths_do_not_share_a_column_name():
    """`_dyn` alone was a silent overwrite waiting to happen.

    `df.ta.ema2(length=fast, append=True)` followed by
    `df.ta.ema2(length=slow, append=True)` both wrote `EMA2_dyn`, so the
    second replaced the first -- in the exact call shape the module was kept
    for. Naming is API here.
    """
    _, _, close = grid_s()
    rising = Series(np.linspace(5, 20, N))
    falling = Series(np.linspace(20, 5, N))
    a, b = ema2(close, rising), ema2(close, falling)
    assert a.name != b.name, "two different per-bar lengths share a column name"
    # same span, so the span alone would have collided -- the digest is what
    # separates them, and it is deterministic, not Python's salted hash()
    assert a.name.startswith("EMA2_dyn5-20-") and b.name.startswith("EMA2_dyn5-20-")
    assert ema2(close, rising).name == a.name, "the token is not reproducible"
    # 4 bytes, not 2. A 16-bit digest is 65,536 codes -- a birthday bound of
    # ~300 Series in one frame for a 50% collision, and a collision here is
    # the silent `append=True` overwrite this token exists to prevent. It is
    # a bound, not a guarantee; the docstring says so too.
    assert len(a.name.rsplit("-", 1)[1]) == 8, "the digest was narrowed"


def test_a_fractional_length_is_truncated_by_the_sibling_and_kept_here():
    """`int(12.5) == 12` in the sibling; `ema2` runs the 12.5 alpha."""
    _, _, close = grid_s()
    assert np.allclose(ta.ema(close, length=12.5).to_numpy(float),
                       ta.ema(close, length=12).to_numpy(float), equal_nan=True)
    assert ema2(close, length=12.5).name == "EMA2_12.5"
    assert not np.allclose(ema2(close, length=12.5).to_numpy(float),
                           ema2(close, length=12).to_numpy(float))


def test_t3_silently_clamps_a_volume_factor_that_t3_tv_reaches():
    """`t3`'s `a > 0 and a < 1` guard is silent -- the name lies about it."""
    _, _, close = grid_s()
    clamped = ta.t3(close, length=10, a=1.5)
    assert clamped.name == "T3_10_0.7", "if this changed, re-measure the reach"
    assert np.allclose(clamped.to_numpy(float),
                       ta.t3(close, length=10, a=0.7).to_numpy(float), equal_nan=True)

    reached = t3_tv(close, length=10, vf=1.5)
    assert reached.name == "T3tv_10_1.5"
    assert np.nanmax(np.abs(reached - t3_tv(close, length=10, vf=0.7))) > 1.0


def test_supertrend_swallows_wicks_and_supertrend2_acts_on_it():
    """`wicks` falls into `**kwargs` in the sibling and changes nothing."""
    high, low, close = grid_s()
    base = ta.supertrend(high, low, close, length=7, multiplier=3.0)
    swallowed = ta.supertrend(high, low, close, length=7, multiplier=3.0, wicks=True)
    assert np.allclose(swallowed.to_numpy(float), base.to_numpy(float), equal_nan=True)

    off = supertrend2(high, low, close, length=7, multiplier=3.0)
    on = supertrend2(high, low, close, length=7, multiplier=3.0, wicks=True)
    assert list(on.columns)[0] == "SUPERT2_7_3.0w", "wicks must be visible in the name"
    assert np.nanmax(np.abs(on.iloc[:, 0].to_numpy(float)
                            - off.iloc[:, 0].to_numpy(float))) > 1.0


# ----------------------------------------------------- 4. rma2's real sibling
def test_rma2s_sibling_is_wilder_rma_and_rma_is_a_different_filter():
    """`pandas_ta.rma` is `adjust=True`; Pine's `ta.rma` is Wilder's.

    Measured on GRID_S at length=10: `rma2` sits closer to `wilder_rma`
    (max|diff| 0.0711) than to `rma` (0.4667) -- a 6.6x gap -- and the two
    fork functions differ from each other, so they are not interchangeable.
    """
    _, _, close = grid_s()
    alt = rma2(close, length=10)
    d_wilder = float(np.nanmax(np.abs(alt - wilder_rma(close, length=10))))
    d_rma = float(np.nanmax(np.abs(alt - ta.rma(close, length=10))))
    assert d_wilder == pytest.approx(0.0711, abs=5e-4)
    assert d_rma == pytest.approx(0.4667, abs=5e-4)
    assert d_wilder < d_rma
    assert not np.allclose(wilder_rma(close, length=10).to_numpy(float),
                           ta.rma(close, length=10).to_numpy(float), equal_nan=True)


# ------------------------------------------------------------- 5. rho, on the
#                                                                   record only
RHO_FLOOR = {
    "ema2": 0.9999, "rma2": 0.9999, "dema2": 0.9999,
    "tema2": 0.9999, "t3_tv": 0.9999, "atr2": 0.9700, "supertrend2": 0.9900,
}


@pytest.mark.parametrize("name", list(RHO_FLOOR))
def test_rho_against_the_sibling_is_recorded_not_a_veto(name):
    """Gate E, for the record.

    Every survivor is near-perfectly rank-correlated with its sibling --
    that is expected and is explicitly NOT grounds for deletion under
    PINEBI-1c, whose acceptance test is warm-up and parameter reach.  The
    floors below are the GRID_S values; they exist so a change in the
    filter shows up, not as a ship/revert gate.
    """
    sib, alt = _pairs()[name]
    assert spearman(sib, alt) >= RHO_FLOOR[name]


def test_supertrend2_direction_tracks_the_negation_of_supertrendd():
    """Pine's sign is inverted vs `pandas_ta.supertrend`, but not perfectly.

    Measured on GRID_S: `SUPERT2d == -SUPERTd` on 96.75% of 400 bars.  It is
    not 100% because the band ratchet also differs (Pine re-arms on
    `price[1]` breaking the previous band).  Anyone reading `SUPERT2d` as a
    copy of `SUPERTd` inverts their rule.
    """
    high, low, close = grid_s()
    a = ta.supertrend(high, low, close, length=7,
                      multiplier=3.0)["SUPERTd_7_3.0"].to_numpy(float)
    b = supertrend2(high, low, close, length=7,
                    multiplier=3.0)["SUPERT2d_7_3.0"].to_numpy(float)
    m = ~np.isnan(a) & ~np.isnan(b)
    agree = float((a[m] == -b[m]).mean())
    assert agree == pytest.approx(0.9675, abs=0.005)
    assert float((a[m] == b[m]).mean()) < 0.10, "the sign convention is inverted"


# ------------------------------------------------------------- 6. reachability
# distinct values each survivor emits on GRID_S. The six averages take a
# new value on every bar; `supertrend2` is a RATCHETING STOP, so it holds
# its level between re-arms and emits 86 -- asserting "> N // 2" there would
# have been a claim about a filter that is not one.
DISTINCT = {"ema2": 400, "rma2": 400, "dema2": 400, "tema2": 400,
            "t3_tv": 400, "atr2": 400, "supertrend2": 86}


@pytest.mark.parametrize("name", list(RHO_FLOOR))
def test_the_column_fires_and_is_not_constant(name):
    """Gate C: every bar is finite and the column is far from constant."""
    _, alt = _pairs()[name]
    finite = Series(np.asarray(alt, dtype=float)).dropna()
    assert len(finite) == N, f"{name} left NaNs -- it claims a bar-0 seed"
    assert 1 < finite.nunique() == DISTINCT[name]


def test_the_survivors_are_price_scale_like_their_siblings():
    """Gate D, stated rather than passed.

    These seven scale with price exactly as `EMA_10` and `ATRr_14` do; they
    are NOT scale-free features and are not offered as such.  Under a x8
    price scaling every one of them scales by 8 (bit-identical in float64
    for a dyadic factor), which is the property a tree cannot use.
    """
    high, low, close = grid_s()
    scaled = {k: v * 8 for k, v in
              dict(high=high, low=low, close=close).items()}
    checks = [
        (ema2(close, 10), ema2(scaled["close"], 10)),
        (rma2(close, 10), rma2(scaled["close"], 10)),
        (dema2(close, 10), dema2(scaled["close"], 10)),
        (tema2(close, 10), tema2(scaled["close"], 10)),
        (t3_tv(close, 10), t3_tv(scaled["close"], 10)),
        (atr2(high, low, close, 14),
         atr2(scaled["high"], scaled["low"], scaled["close"], 14)),
        (supertrend2(high, low, close, 7, 3.0)["SUPERT2_7_3.0"],
         supertrend2(scaled["high"], scaled["low"], scaled["close"],
                     7, 3.0)["SUPERT2_7_3.0"]),
    ]
    for plain, big in checks:
        assert np.array_equal(np.asarray(big, float),
                              np.asarray(plain, float) * 8, equal_nan=True), (
            f"{plain.name} did not scale by exactly 8 -- the port is not the "
            "same filter at two price levels")


# --------------------------------------------------------------- 7. causality
J = 250
BUMP = 50.0


def _leak_series(fn):
    """max |before - after| over bars < J when every bar >= J is bumped."""
    high, low, close = grid_s()
    step = BUMP * (np.arange(N) >= J)
    base = fn(high, low, close)
    moved = fn(high + step, low + step, close + step)
    a = Series(np.asarray(base, dtype=float)).iloc[:J]
    b = Series(np.asarray(moved, dtype=float)).iloc[:J]
    m = ~(a.isna() | b.isna())
    assert int(m.sum()) > J - 20, "nothing settled to compare"
    return float((a[m] - b[m]).abs().max())


CAUSAL_CASES = [
    ("ema2", lambda h, l, c: ema2(c, 10)),
    ("rma2", lambda h, l, c: rma2(c, 10)),
    ("dema2", lambda h, l, c: dema2(c, 10)),
    ("tema2", lambda h, l, c: tema2(c, 10)),
    ("t3_tv", lambda h, l, c: t3_tv(c, 10)),
    ("atr2", lambda h, l, c: atr2(h, l, c, 14)),
    ("supertrend2", lambda h, l, c: supertrend2(h, l, c, 7, 3.0)["SUPERT2_7_3.0"]),
]


@pytest.mark.parametrize("name,fn", CAUSAL_CASES)
def test_each_survivor_leaks_no_future(name, fn):
    """Future perturbation: bump every bar from J on, nothing before J moves."""
    assert _leak_series(fn) == 0.0, f"{name} reads the future"


def test_dynamic_ewma_is_causal_with_a_mutant():
    """The detector, not just the claim.

    `dynamic_ewma` carries state, so a one-bar back-dated write survives
    prefix truncation untouched -- truncating at J and re-running gives the
    same answer whether or not the write index is shifted, because the
    recursion is deterministic in its own prefix.  Future perturbation is
    the method that sees it.

    Measured: the real module leaks 0.0; a mutant that writes `out[i - 5]`
    leaks a non-zero amount, so the test is not blind.
    """
    spec = importlib.util.find_spec("pandas_ta.overlap.ema2")
    source = open(spec.origin, encoding="utf8").read()
    mutated = source.replace("        out[i] = prev\n",
                             "        out[max(i - 5, 0)] = prev\n")
    assert mutated != source, "the mutation did not apply -- the test is blind"

    namespace = {}
    exec(compile(mutated, "<mutant>", "exec"), namespace)
    mutant_ema2 = namespace["ema2"]

    assert _leak_series(lambda h, l, c: ema2(c, 10)) == 0.0
    assert _leak_series(lambda h, l, c: mutant_ema2(c, 10)) > 1.0, (
        "the back-dated mutant was NOT caught, so this cannot certify causality")


def test_supertrend2_loop_is_causal_with_a_mutant():
    """Same detector on the band loop, which also carries state.

    The loop reads `trend[i - 1]`, so back-dating the write both leaks and
    perturbs the recursion; either way the leak must be non-zero for the
    test to be a detector at all.  Measured: real 0.0, mutant > 1.0.
    """
    spec = importlib.util.find_spec("pandas_ta.overlap.supertrend2")
    source = open(spec.origin, encoding="utf8").read()
    mutated = source.replace(
        "        trend[i] = lb[i] if d == -1 else ub[i]\n",
        "        trend[max(i - 5, 0)] = lb[i] if d == -1 else ub[i]\n")
    assert mutated != source, "the mutation did not apply -- the test is blind"

    namespace = {}
    exec(compile(mutated, "<mutant>", "exec"), namespace)
    mutant = namespace["supertrend2"]

    assert _leak_series(
        lambda h, l, c: supertrend2(h, l, c, 7, 3.0)["SUPERT2_7_3.0"]) == 0.0
    assert _leak_series(
        lambda h, l, c: mutant(h, l, c, 7, 3.0)["SUPERT2_7_3.0"]) > 1.0, (
        "the back-dated mutant was NOT caught, so this cannot certify causality")


# ------------------------------------------------------------------ 8. wiring
SURVIVORS = {
    "ema2": "overlap", "rma2": "overlap", "dema2": "overlap",
    "tema2": "overlap", "t3_tv": "overlap", "supertrend2": "overlap",
    "atr2": "volatility",
}


@pytest.mark.parametrize("name,category", sorted(SURVIVORS.items()))
def test_all_five_wiring_touch_points(name, category):
    """Module, package export, `Category`, `df.ta` accessor, and this file."""
    assert hasattr(ta, name), f"{name} is not exported from the package"
    assert name in ta.Category[category], f"{name} is not in Category[{category}]"
    high, low, close = grid_s()
    df = DataFrame({"open": close, "high": high, "low": low, "close": close,
                    "volume": Series(np.full(N, 1000.0))})
    result = getattr(df.ta, name)()
    assert result is not None, f"df.ta.{name}() returned None"


def test_the_survivor_column_names_collide_with_nothing_shipped():
    """Naming is API: a survivor must not overwrite a shipped column."""
    high, low, close = grid_s()
    new = {
        ema2(close, 10).name, rma2(close, 10).name, dema2(close, 10).name,
        tema2(close, 10).name, t3_tv(close, 10).name,
        atr2(high, low, close, 14).name,
        *supertrend2(high, low, close, 7, 3.0).columns,
    }
    shipped = {
        ta.ema(close, 10).name, ta.rma(close, 10).name,
        wilder_rma(close, 10).name, ta.dema(close, 10).name,
        ta.tema(close, 10).name, ta.t3(close, 10).name,
        *[ta.atr(high, low, close, 14, mamode=m).name
          for m in ("rma", "ema", "sma", "wma", "wrma", "t3")],
        *ta.supertrend(high, low, close, length=7, multiplier=3.0).columns,
    }
    assert not (new & shipped), f"column name collision: {sorted(new & shipped)}"
    assert len(new) == 10, "one of the survivors stopped emitting its column"
