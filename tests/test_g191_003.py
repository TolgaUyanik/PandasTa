# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.momentum.g191_003` -- Guotai Junan's (2017,
"GTJA191") alpha `#3`, per issue #79:
`SUM(C=C1 ? 0 : C-(C>C1 ? MIN(L,C1) : MAX(H,C1)), 6)`, scale-free via
`/close`, matching the issue's own prototype
(`docs/issues/screen/ind_screen.py:282-287`). Gate A derivation, including
the three fixed readings of the source string, is in the module docstring
and `docs/G191003Measured.md`. Gate E is pending (CLAUDE.md, "Owed, not
failed").

What these tests pin, in order of how much it would hurt to lose:

* CAUSALITY by future-perturbation: rewrite every high/low/close bar from
  `j` onward (another synthetic walk), demand bars `[0:j]` bit-identical
  with matching NaN masks, over 37 offsets past the 7-bar warm-up. Two
  mutants (`importlib` source read, `exec`'d in memory), each shown live
  (differs from the real module) then caught at every offset: shifting the
  final write index `length=6` bars into the future, and computing the
  rolling sum with `rolling(length, center=True)` instead of the causal
  trailing window -- the same `bos` look-ahead bug class CLAUDE.md
  documents.
* THE `C=C1 ? 0` BRANCH IS LOAD-BEARING. Deleting it (a third live
  mutant) does NOT leave the column unchanged: a flat bar falls through to
  `MAX(H,C1)` and contributes `C - H <= 0`, a negative number on a bar
  whose close did not move. Pinned on a dedicated 8-bar fixture holding
  one exactly-flat close, with the two outputs' numbers written out. This
  is the opposite of `g191_129`, whose `clip` WAS a faithful restatement
  of its ternary.
* THE BAR-0 READING. `C1` is undefined at bar 0, so the formula's `C=C1`
  test is neither true nor false there; the port masks the bar to NaN by
  decision (the prototype's own `.where(c1.notna())`), not by numpy
  accident. Pinned at `length=1`, where the mask is the ONLY thing
  standing between bar 0 and a value.
* CORRECTNESS: a hand-derived 7-bar example at `length=3`, checked bar by
  bar with the arithmetic written out, plus a spot check at the shipped
  default against an independent per-bar computation using a plain Python
  loop over numpy scalars, not the module's own `.rolling()`/`.shift()`.
  And the retyped prototype expression, matched BIT-FOR-BIT on a 900-bar
  frame; the 1,500-bar run reporting `max|diff| = 0.0` against the REAL
  candidate loaded out of `docs/issues/screen/ind_screen.py` is
  `docs/measure_g191_003.py`'s, not this file's (the screen is gitignored,
  so a test may not depend on it).
* PER-BAR SIGN: every up bar contributes strictly positive and every down
  bar strictly negative (unconditionally -- `MIN(L,C1) <= C1 < C` and
  `MAX(H,C1) >= C1 > C`), so the column is a SIGNED
  accumulation/distribution tally rather than a magnitude.
* SCALE-FREE: bit-identical under price x8/x64 (power-of-two, exact in
  IEEE754), within float64 tolerance under x10/x3.7, with the exact-float
  BRANCH MASKS also unchanged (the `>` and `==` tests are the one place a
  rescale could in principle move a bar between branches). Matching NaN
  masks, plus `0 < fires < n` and `nunique > 1`.
* Wiring: `Category`, the accessor, the column name `G191_003_6`.
"""
import importlib
import types

import numpy as np
import pandas as pd
import pytest
from pandas import Series

from .context import pandas_ta as ta
from pandas_ta.momentum.g191_003 import g191_003


def _walk(n=1500, seed=11, sigma=0.015):
    """High/low/close walk with `low <= close <= high` at every bar."""
    rng = np.random.default_rng(seed)
    close = 100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n)))
    high = close * (1.0 + np.abs(rng.normal(0.0, sigma * 0.5, n)))
    low = close * (1.0 - np.abs(rng.normal(0.0, sigma * 0.5, n)))
    idx = pd.RangeIndex(n)
    return Series(high, index=idx), Series(low, index=idx), Series(close, index=idx)


# ------------------------------------------------------------ correctness


def test_hand_derived_seven_bars():
    """length=3.

    high  = [10, 13, 12, 16, 11, 21, 10]
    low   = [ 8,  9,  8, 11,  7, 15,  6]
    close = [ 9, 12,  9, 15,  8, 20,  7]
    C1    = [nan, 9, 12,  9, 15,  8, 20]

    bar 0: C1 undefined            -> NaN (masked)
    bar 1: 12 >  9 -> C - MIN(L,C1) = 12 - MIN(9, 9)  = 12 -  9 =   3
    bar 2:  9 < 12 -> C - MAX(H,C1) =  9 - MAX(12,12) =  9 - 12 =  -3
    bar 3: 15 >  9 -> C - MIN(L,C1) = 15 - MIN(11,9)  = 15 -  9 =   6
    bar 4:  8 < 15 -> C - MAX(H,C1) =  8 - MAX(11,15) =  8 - 15 =  -7
    bar 5: 20 >  8 -> C - MIN(L,C1) = 20 - MIN(15,8)  = 20 -  8 =  12
    bar 6:  7 < 20 -> C - MAX(H,C1) =  7 - MAX(10,20) =  7 - 20 = -13

    SUM(bar, 3), min_periods=3:
        t=0,1,2: NaN (window touches the masked bar 0)
        t=3: 3 - 3 + 6  =  6  -> 6 / 15   =  0.4
        t=4: -3 + 6 - 7 = -4  -> -4 / 8   = -0.5
        t=5: 6 - 7 + 12 = 11  -> 11 / 20  =  0.55
        t=6: -7 + 12 - 13 = -8 -> -8 / 7  = -1.1428571428571428
    """
    high = Series([10.0, 13.0, 12.0, 16.0, 11.0, 21.0, 10.0])
    low = Series([8.0, 9.0, 8.0, 11.0, 7.0, 15.0, 6.0])
    close = Series([9.0, 12.0, 9.0, 15.0, 8.0, 20.0, 7.0])

    out = g191_003(high, low, close, length=3)

    assert out.iloc[:3].isna().all()
    assert out.iloc[3] == pytest.approx(6.0 / 15.0, abs=1e-12)
    assert out.iloc[4] == pytest.approx(-4.0 / 8.0, abs=1e-12)
    assert out.iloc[5] == pytest.approx(11.0 / 20.0, abs=1e-12)
    assert out.iloc[6] == pytest.approx(-8.0 / 7.0, abs=1e-12)


def test_matches_an_independent_loop_at_defaults():
    """Spot-checks 3 bars of the shipped default (length=6) against an
    independent per-bar computation: a plain Python loop over numpy
    scalars, using neither `.rolling()` nor `.shift()` nor `np.where`."""
    high, low, close = _walk(900, seed=5)
    out = g191_003(high, low, close)
    hh, ll, cc = (s.to_numpy(dtype=float) for s in (high, low, close))
    length = 6

    def expected_at(t):
        total = 0.0
        for i in range(t - length + 1, t + 1):  # all >= 1 since t >= length
            c, c1 = cc[i], cc[i - 1]
            if c == c1:
                continue
            r = min(ll[i], c1) if c > c1 else max(hh[i], c1)
            total += c - r
        return total / cc[t]

    for t in (300, 600, 899):
        assert out.iloc[t] == pytest.approx(expected_at(t), rel=1e-9), f"bar {t}"


def test_matches_the_prototype_expression_bit_for_bit():
    """The issue's own prototype (`docs/issues/screen/ind_screen.py:282-287`)
    is

        c1 = delay(c, 1)
        x = np.where(c == c1, 0.0,
                     c - np.where(c > c1, np.minimum(l, c1), np.maximum(h, c1)))
        tsum(pd.Series(x, index=c.index).where(c1.notna()), 6) / c

    with `delay(x, n) = x.shift(n)` (line 45) and
    `tsum(x, n) = x.rolling(n).sum()` (line 49). The port fixes three
    READINGS of the source string (see the module docstring) but no
    arithmetic beyond the prototype, so it must agree with that expression
    EXACTLY, not within a tolerance: same NaN mask, same bits.

    The expression below is RETYPED from those lines, because
    `docs/issues/` is gitignored and a clone running this suite does not
    have it. `docs/measure_g191_003.py` closes that gap where the file IS
    present: it loads `ind_screen.py` by path, calls the registered
    `g191_003` candidate itself, and prints both the port-vs-candidate and
    the retyped-vs-candidate comparisons -- on its 1,500-bar frame all
    three are bit-identical, so the retyping is not hiding a slip."""
    high, low, close = _walk(900, seed=29)
    out = g191_003(high, low, close)

    c1 = close.shift(1)
    x = np.where(
        close == c1,
        0.0,
        close - np.where(close > c1, np.minimum(low, c1), np.maximum(high, c1)),
    )
    prototype = (
        pd.Series(x, index=close.index).where(c1.notna()).rolling(6).sum() / close
    )

    assert (out.isna() == prototype.isna()).all()
    m = out.notna()
    assert (out[m] == prototype[m]).all()


def test_up_bars_contribute_positive_and_down_bars_negative():
    """The two live branches are asymmetric by construction, with no
    OHLC-consistency assumption needed: an up bar's reference is
    `MIN(L,C1) <= C1 < C` (strictly positive contribution) and a down
    bar's is `MAX(H,C1) >= C1 > C` (strictly negative). Measured bar by
    bar on the 1,500-bar walk through `length=1`, where the window sum is
    the single bar's own contribution, which the `/close` divisor then
    scales by a positive number -- asserted below, since the sign claim is
    about the contribution and the division must not be allowed to flip
    it: 762 up bars all strictly positive, 737 down bars all strictly
    negative (`docs/measure_g191_003.py` prints the same census off the
    UNDIVIDED contribution)."""
    high, low, close = _walk()
    per_bar = g191_003(high, low, close, length=1)  # SUM over one bar
    prev = close.shift(1)
    up, down = close > prev, (close < prev) & prev.notna()

    assert (close > 0).all()  # the /close divisor cannot flip the sign
    assert int(up.sum()) == 762 and int(down.sum()) == 737  # the census itself
    assert (per_bar[up] > 0).all()
    assert (per_bar[down] < 0).all()


def test_the_flat_close_branch_is_not_redundant():
    """`C=C1 ? 0 : ...` is a real branch, not a restatement of the other
    two. Delete it and a flat bar takes the `MAX(H,C1)` route (`C > C1` is
    false when `C == C1`), contributing `C - MAX(H,C) = C - H`, which is
    NEGATIVE whenever the bar's high is above its close.

    Fixture (length=3), close flat at bar 2:
        high  = [10, 12, 14, 13, 16, 15, 18, 17]
        low   = [ 8,  9, 10,  9, 11, 10, 12, 11]
        close = [ 9, 11, 11, 12, 14, 13, 15, 14]
    bar 1: 11 >  9 -> 11 - MIN(9, 9)   =  2       (both forms)
    bar 2: 11 == 11 -> 0 shipped; 11 - MAX(14,11) = -3 without the branch
    bar 3: 12 > 11 -> 12 - MIN(9,11)   =  3       (both forms)
    bar 4: 14 > 12 -> 14 - MIN(11,12)  =  3       (both forms)
    t=3 shipped: (2 + 0 + 3)/12 = 5/12; without the branch: (2 - 3 + 3)/12 = 2/12
    t=4 shipped: (0 + 3 + 3)/14 = 6/14; without the branch: (-3 + 3 + 3)/14 = 3/14

    Three windows hold the flat bar (t=2,3,4) but t=2 is still inside the
    warm-up and NaN in both forms, so 2 outputs move, not 3.
    """
    high = Series([10.0, 12.0, 14.0, 13.0, 16.0, 15.0, 18.0, 17.0])
    low = Series([8.0, 9.0, 10.0, 9.0, 11.0, 10.0, 12.0, 11.0])
    close = Series([9.0, 11.0, 11.0, 12.0, 14.0, 13.0, 15.0, 14.0])
    assert close.iloc[2] == close.iloc[1]  # the branch is actually exercised

    out = g191_003(high, low, close, length=3)
    mutant = _load_mutant(*NO_TERNARY_MUTANT).g191_003(high, low, close, length=3)

    assert out.iloc[:3].isna().all() and mutant.iloc[:3].isna().all()
    assert out.iloc[3] == pytest.approx(5.0 / 12.0, abs=1e-12)
    assert mutant.iloc[3] == pytest.approx(2.0 / 12.0, abs=1e-12)
    assert out.iloc[4] == pytest.approx(6.0 / 14.0, abs=1e-12)
    assert mutant.iloc[4] == pytest.approx(3.0 / 14.0, abs=1e-12)
    assert not out.equals(mutant)
    # ... and identical once the flat bar leaves the window (t >= 5).
    assert (out.iloc[5:] == mutant.iloc[5:]).all()


def test_an_all_flat_window_is_exactly_zero():
    """The third value the column can take, and the one the `C=C1` branch
    exists to produce: a window whose closes are all flat sums to exactly
    `0.0`, not to a negative number. The 1,500-bar walk never reaches it
    (767 positive + 727 negative = 1,494 = every bar that fires), so it is
    pinned here or nowhere."""
    close = Series([100.0] * 7)
    high = Series([101.0, 102.0, 103.0, 101.5, 104.0, 102.5, 105.0])
    low = Series([99.0, 98.0, 97.0, 98.5, 96.0, 97.5, 95.0])
    # every bar in the window takes the `C=C1` branch -- the premise,
    # asserted rather than left to the reader eyeballing [100.0] * 7
    assert (close == close.shift(1)).iloc[1:].all()

    out = g191_003(high, low, close)

    assert out.iloc[:6].isna().all()
    assert out.iloc[6] == 0.0  # exactly, not approximately


def test_bar_zero_is_masked_by_decision_not_by_accident():
    """`C1` is undefined at bar 0, where the formula's `C=C1` test is
    neither true nor false. The port masks the bar (`.where(prev_close
    .notna())`), the prototype's own resolution. At `length=1` the mask is
    the only thing between bar 0 and a value: without it, `close == NaN`
    is False, so bar 0 would take the `MAX(H, NaN)` branch -- NaN by numpy
    accident, which is the same output for the wrong reason, and would
    become 0.0 the moment anyone 'fixed' the comparison."""
    high, low, close = _walk(50)
    out = g191_003(high, low, close, length=1)

    assert pd.isna(out.iloc[0])
    assert pd.notna(out.iloc[1])
    # The mask, not the arithmetic, is what empties bar 0: the unmasked
    # expression lands NaN there too, so the two agree -- but only the
    # masked one still holds at bar 0 if the comparison branch changes.
    prev = close.shift(1)
    unmasked = Series(
        np.where(
            close == prev,
            0.0,
            close - np.where(close > prev, np.minimum(low, prev), np.maximum(high, prev)),
        ),
        index=close.index,
    )
    assert pd.isna(unmasked.iloc[0])  # numpy's accident, documented
    forced_zero = unmasked.copy()
    forced_zero.iloc[0] = 0.0  # what a 'fix' to the comparison would give
    assert (forced_zero.rolling(1).sum() / close).iloc[0] == 0.0
    assert pd.isna(out.iloc[0])  # the shipped column does not do that


def test_misaligned_indexes_raise():
    high, low, close = _walk(100)
    shifted = close.copy()
    shifted.index = pd.RangeIndex(1, 101)
    with pytest.raises(ValueError, match="indexed differently"):
        g191_003(high, low, shifted)


def test_insufficient_history_returns_none():
    high, low, close = _walk(6)  # defaults need length + 1 = 7 bars
    assert g191_003(high, low, close) is None


def test_exact_min_length_fires_at_the_warmup_boundary():
    high, low, close = _walk(7)  # exactly length + 1 = 7 bars
    out = g191_003(high, low, close)
    assert out is not None
    assert out.iloc[:6].isna().all()
    assert pd.notna(out.iloc[6])


def test_default_name():
    high, low, close = _walk()
    assert g191_003(high, low, close).name == "G191_003_6"


def test_distinct_lengths_produce_distinct_names_and_values():
    high, low, close = _walk(400)
    out1 = g191_003(high, low, close, length=4)
    out2 = g191_003(high, low, close, length=12)
    assert out1.name == "G191_003_4"
    assert out2.name == "G191_003_12"
    m = out1.notna() & out2.notna()
    assert (out1[m] != out2[m]).any()


# -------------------------------------------------------------- causality


_REAL = importlib.import_module("pandas_ta.momentum.g191_003")


def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_g191_003_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


SHIPPED_SUM = "result = bar.rolling(length, min_periods=length).sum() / close"
WRITE_SHIFT_MUTANT = (
    SHIPPED_SUM,
    "result = (bar.rolling(length, min_periods=length).sum() / close).shift(-length)",
)
CENTERED_SUM_MUTANT = (
    SHIPPED_SUM,
    # the `bos` look-ahead bug class
    "result = bar.rolling(length, center=True, min_periods=length).sum() / close",
)
NO_TERNARY_MUTANT = (
    "np.where(close == prev_close, 0.0, close - ref)",
    "(close - ref)",  # the `C=C1 ? 0 :` branch deleted
)

OFFSETS = range(50, 1500, 40)  # past the 7-bar warm-up


def _leaks(fn):
    high, low, close = _walk(1500)
    other_h, other_l, other_c = _walk(1500, seed=97)
    base = fn(high, low, close)
    hits = 0
    for j in OFFSETS:
        ph, pl, pc = high.copy(), low.copy(), close.copy()
        ph.iloc[j:] = other_h.iloc[j:].values
        pl.iloc[j:] = other_l.iloc[j:].values
        pc.iloc[j:] = other_c.iloc[j:].values
        out = fn(ph, pl, pc)
        a, b = base.iloc[:j], out.iloc[:j]
        if not (a.isna() == b.isna()).all():
            hits += 1
            continue
        m = a.notna()
        if (a[m] != b[m]).any():
            hits += 1
    return hits


def test_real_module_never_reads_the_future():
    assert _leaks(g191_003) == 0


def test_write_shift_mutant_is_caught():
    mod = _load_mutant(*WRITE_SHIFT_MUTANT)
    high, low, close = _walk(1500)
    assert not mod.g191_003(high, low, close).equals(g191_003(high, low, close))  # live
    assert _leaks(mod.g191_003) == len(list(OFFSETS))  # caught, every offset


def test_centered_sum_mutant_is_caught():
    mod = _load_mutant(*CENTERED_SUM_MUTANT)
    high, low, close = _walk(1500)
    assert not mod.g191_003(high, low, close).equals(g191_003(high, low, close))  # live
    assert _leaks(mod.g191_003) == len(list(OFFSETS))  # caught, every offset


# ------------------------------------------------------------ reachability


def test_fires_on_a_non_trivial_fraction():
    high, low, close = _walk()  # 1500 bars, defaults
    out = g191_003(high, low, close)
    assert int(out.notna().sum()) == 1494  # exactly n - length, measured
    assert int(out.notna().idxmax()) == 6  # first fire at the warm-up bound


def test_fires_and_is_not_constant():
    high, low, close = _walk()
    out = g191_003(high, low, close)
    fires = int(out.notna().sum())
    assert 0 < fires < len(out)
    assert out.dropna().nunique() > 100


def test_the_column_takes_both_signs():
    """A signed accumulation/distribution tally, not a magnitude: on the
    1,500-bar walk 767 bars are positive and 727 negative."""
    high, low, close = _walk()
    out = g191_003(high, low, close).dropna()
    assert int((out > 0).sum()) == 767
    assert int((out < 0).sum()) == 727


# ------------------------------------------------------------ scale-free


@pytest.mark.parametrize("k", [8.0, 64.0])
def test_power_of_two_price_scale_is_bit_identical(k):
    high, low, close = _walk()
    base = g191_003(high, low, close)
    scaled = g191_003(high * k, low * k, close * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_other_price_scales_within_tolerance(k):
    high, low, close = _walk()
    base = g191_003(high, low, close)
    scaled = g191_003(high * k, low * k, close * k)
    assert (base.isna() == scaled.isna()).all()
    assert (base - scaled).abs().max() < 1e-12


@pytest.mark.parametrize("k", [8.0, 64.0, 10.0, 3.7])
def test_price_scale_moves_no_bar_between_branches(k):
    """The branch tests (`C > C1`, `C == C1`) are EXACT float comparisons,
    the one place where a rescale could in principle change the column's
    structure rather than just its rounding: `k*a == k*b` can hold for two
    distinct `a != b` that round to the same product. Measured on the
    1,500-bar walk: no bar changes branch at any of the four
    multipliers -- asserted through the MODULE at `length=1`, where the
    column is the single bar's own branch, so a module-side change of
    `>` to `>=` cannot pass this test, and then on the bare comparisons
    too."""
    high, low, close = _walk()
    base = g191_003(high, low, close, length=1)
    scaled_out = g191_003(high * k, low * k, close * k, length=1)
    assert (base.isna() == scaled_out.isna()).all()
    m = base.notna()
    assert (np.sign(base[m]) == np.sign(scaled_out[m])).all()
    assert ((base[m] == 0.0) == (scaled_out[m] == 0.0)).all()

    prev = close.shift(1)
    scaled, scaled_prev = close * k, (close * k).shift(1)
    assert ((scaled > scaled_prev) == (close > prev)).all()
    assert ((scaled == scaled_prev) == (close == prev)).all()


# ---------------------------------------------------------------- wiring


def test_name_registration_and_accessor():
    high, low, close = _walk(400)
    df = pd.DataFrame({"open": close, "high": high, "low": low, "close": close})
    assert "g191_003" in ta.Category["momentum"]
    out = df.ta.g191_003()
    assert out.name == "G191_003_6"
    pd.testing.assert_series_equal(out, g191_003(high, low, close))
    # tunable kwarg forwarded under its own name -- the "supertrend
    # failure mode" (CLAUDE.md) hasattr cannot see.
    renamed = df.ta.g191_003(length=10)
    assert renamed.name == "G191_003_10"
