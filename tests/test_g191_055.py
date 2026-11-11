# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.momentum.g191_055` -- Guotai Junan's (2017,
"GTJA191") alpha `#55`, per issue #80, the 20-day sum of a Wilder swing
index, scale-free via `/close`. The issue's own quote of the formula is
ELIDED (`SUM(16*(...)/R*MAX(|H-C1|,|L-C1|), 20)`), and the two sources
available in this worktree DISAGREE about `R`: the issue's prototype
(`docs/issues/screen/ind_screen.py:398-405`) has TWO branches, the GTJA191
report's own string -- as the port session recalled it, having been unable
to read any copy -- has THREE. The port ships the three-branch form, per
issue #80's "Gate A starts from the source formula, not the prototype".
Full derivation in the module docstring; numbers in
`docs/G191055Measured.md`. Gate E is pending (CLAUDE.md, "Owed, not
failed").

What these tests pin, in order of how much it would hurt to lose:

* CAUSALITY by future-perturbation: rewrite every open/high/low/close bar
  from `j` onward (another synthetic walk), demand bars `[0:j]`
  bit-identical with matching NaN masks, over 36 offsets past the 21-bar
  warm-up. Two mutants (`importlib` source read, `exec`'d in memory), each
  shown live (differs from the real module) then caught at every offset:
  shifting the final write index `length=20` bars into the future, and
  computing the rolling sum with `rolling(length, center=True)` instead of
  the causal trailing window -- the same `bos` look-ahead bug class
  CLAUDE.md documents.
* THE THIRD BRANCH OF `R` IS THE WHOLE PORT DECISION, so it is pinned from
  both ends. A live mutant with the third branch collapsed into the
  prototype's `B + A/2 + E/4` (`TWO_BRANCH_MUTANT`) is shown to be
  bit-identical to the retyped prototype expression, to agree with the port
  on every branch-2 bar (537 of 537 on the 1,500-bar walk) and to differ on
  every branch-3 bar (962 of 962), with the arithmetic written out bar by
  bar on a 5-bar fixture. Nobody can "simplify" the inner `np.where` away
  without this failing.
* BRANCH 1 IS UNREACHABLE on OHLC-consistent data -- a derivation
  (`H >= C1` forces `D >= A`; `H <= C1` forces `B >= A`), measured here as
  a census: 0 branch-1 / 537 branch-2 / 962 branch-3 over the walk's 1,499
  bars with a prior bar, and 0 violations of either inequality. It matters
  because branch 1 is also the PROTOTYPE's only branch test, so the
  prototype's `R` is one expression with a dead arm.
* `R == 0` IS REACHABLE AND POISONS A WHOLE WINDOW. A zero-range bar
  printing at the prior bar's low, where that prior bar opened and closed
  at the same price, drives `R` to exactly `0`; `sdiv`'s `inf -> NaN` plus
  `min_periods=length` then NaNs the `length` outputs whose window holds
  it. Pinned on a 7-bar fixture at `length=2`: `R = 0` at bar 2, NaN at
  bars 0-3, valid from bar 4.
* CORRECTNESS: a hand-derived 5-bar example at `length=2` with every `A`,
  `B`, `D`, `E`, `R`, `N` and `SI` written out (branch 2, branch 3 and an
  `A == B == D` triple tie all exercised), plus a spot check at the
  shipped default against an independent per-bar computation using a plain
  Python loop over numpy scalars -- no `.rolling()`, no `.shift()`, no
  `np.where`.
* SCALE-FREE: bit-identical under price ×8/×64 (power-of-two, exact in
  IEEE754), within float64 tolerance under ×10/×3.7, with the SELECTED
  BRANCH unchanged at all four (the `>` tests are the one place a rescale
  could change the column's structure rather than its rounding). Matching
  NaN masks, plus `0 < fires < n` and `nunique > 1`.
* Wiring: `Category`, the accessor, the column name `G191_055_20`.
"""
import importlib
import types

import numpy as np
import pandas as pd
import pytest
from pandas import Series

from .context import pandas_ta as ta
from pandas_ta.momentum.g191_055 import g191_055


def _walk(n=1500, seed=11, sigma=0.015):
    """OHLC walk with `low <= open, close <= high` at every bar."""
    rng = np.random.default_rng(seed)
    close = 100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n)))
    open_ = close * (1.0 + rng.normal(0.0, sigma * 0.7, n))
    hi_body = np.maximum(open_, close)
    lo_body = np.minimum(open_, close)
    high = hi_body * (1.0 + np.abs(rng.normal(0.0, sigma * 0.5, n)))
    low = lo_body * (1.0 - np.abs(rng.normal(0.0, sigma * 0.5, n)))
    idx = pd.RangeIndex(n)
    return (Series(open_, index=idx), Series(high, index=idx),
            Series(low, index=idx), Series(close, index=idx))


def _branch_masks(open_, high, low, close):
    """The three branch masks of `R`, recomputed here rather than read out
    of the module."""
    c1, o1, l1 = close.shift(1), open_.shift(1), low.shift(1)
    a, b = (high - c1).abs(), (low - c1).abs()
    d = (high - l1).abs()
    one = (a > b) & (a > d)
    two = (~one) & (b > d) & (b > a)
    three = (~one) & (~two) & c1.notna()
    return a, b, d, one, two, three


# ------------------------------------------------------------ correctness


def test_hand_derived_five_bars():
    """length=2.

    open  = [ 99, 100,  99,  92, 92.5]
    high  = [102, 103, 100,  95, 92.5]
    low   = [ 95,  99,  90,  91, 92.5]
    close = [100, 102,  92,  94, 92.5]

    bar 0: no prior bar -> SI masked to NaN.
    bar 1: C1=100 O1=99 L1=95.  A=|103-100|=3  B=|99-100|=1
           D=|103-95|=8  E=|100-99|=1
           branch 1? 3>1 yes, 3>8 NO.  branch 2? 1>8 NO.  -> branch 3
           R = D + E/4 = 8 + 0.25 = 8.25
           N = 102-100 + (102-100)/2 + 100-99 = 2 + 1 + 1 = 4
           SI = 16 * (4/8.25) * MAX(3,1) = 16 * (4/8.25) * 3 = 23.2727...
    bar 2: C1=102 O1=100 L1=99.  A=|100-102|=2  B=|90-102|=12
           D=|100-99|=1  E=|102-100|=2
           branch 1? 2>12 NO.  branch 2? 12>1 yes, 12>2 yes -> branch 2
           R = B + A/2 + E/4 = 12 + 1 + 0.5 = 13.5
           N = 92-102 + (92-99)/2 + 102-100 = -10 - 3.5 + 2 = -11.5
           SI = 16 * (-11.5/13.5) * MAX(2,12) = ... * 12 = -163.5555...
    bar 3: C1=92 O1=99 L1=90.  A=|95-92|=3  B=|91-92|=1
           D=|95-90|=5  E=|92-99|=7
           branch 1? 3>1 yes, 3>5 NO.  branch 2? 1>5 NO.  -> branch 3
           R = 5 + 7/4 = 6.75
           N = 94-92 + (94-92)/2 + 92-99 = 2 + 1 - 7 = -4
           SI = 16 * (-4/6.75) * MAX(3,1) = ... * 3 = -28.4444...
    bar 4: C1=94 O1=92 L1=91.  zero-range bar at 92.5.
           A=|92.5-94|=1.5  B=|92.5-94|=1.5  D=|92.5-91|=1.5  E=|94-92|=2
           an A == B == D TRIPLE TIE: every strict `>` fails -> branch 3
           R = 1.5 + 0.5 = 2.0
           N = 92.5-94 + 0 + 94-92 = -1.5 + 2 = 0.5
           SI = 16 * (0.5/2.0) * 1.5 = 6.0 exactly

    SUM(SI, 2), min_periods=2:
        t=0, t=1: NaN (window touches the masked bar 0)
        t=2: ( 23.2727... - 163.5555...) / 92   = -1.5248133509003072
        t=3: (-163.5555... -  28.4444...) / 94  = -2.0425531914893615
        t=4: ( -28.4444... +   6.0      ) / 92.5 = -0.24264264264264263
    """
    open_ = Series([99.0, 100.0, 99.0, 92.0, 92.5])
    high = Series([102.0, 103.0, 100.0, 95.0, 92.5])
    low = Series([95.0, 99.0, 90.0, 91.0, 92.5])
    close = Series([100.0, 102.0, 92.0, 94.0, 92.5])
    # the fixture is OHLC-consistent -- asserted, not eyeballed
    assert ((low <= open_) & (open_ <= high) & (low <= close)
            & (close <= high)).all()

    si1 = 16 * (4.0 / 8.25) * 3.0
    si2 = 16 * (-11.5 / 13.5) * 12.0
    si3 = 16 * (-4.0 / 6.75) * 3.0
    si4 = 16 * (0.5 / 2.0) * 1.5
    assert si4 == 6.0  # exactly, the one bar whose arithmetic is binary-clean

    # SUM over one bar, times close, is the bar's own SI.
    per_bar = g191_055(open_, high, low, close, length=1) * close
    assert pd.isna(per_bar.iloc[0])
    for t, want in ((1, si1), (2, si2), (3, si3), (4, si4)):
        assert per_bar.iloc[t] == pytest.approx(want, abs=1e-12), f"SI bar {t}"

    out = g191_055(open_, high, low, close, length=2)
    assert out.iloc[:2].isna().all()
    assert out.iloc[2] == pytest.approx((si1 + si2) / 92.0, abs=1e-12)
    assert out.iloc[3] == pytest.approx((si2 + si3) / 94.0, abs=1e-12)
    assert out.iloc[4] == pytest.approx((si3 + si4) / 92.5, abs=1e-12)

    # and the branch the arithmetic above claims, bar by bar
    _, _, _, one, two, three = _branch_masks(open_, high, low, close)
    assert not one.any()
    assert three.tolist() == [False, True, False, True, True]
    assert two.tolist() == [False, False, True, False, False]


def test_matches_an_independent_loop_at_defaults():
    """Spot-checks 3 bars of the shipped default (length=20) against an
    independent per-bar computation: a plain Python loop over numpy
    scalars, using neither `.rolling()` nor `.shift()` nor `np.where`."""
    open_, high, low, close = _walk(900, seed=5)
    out = g191_055(open_, high, low, close)
    oo, hh, ll, cc = (s.to_numpy(dtype=float) for s in (open_, high, low, close))
    length = 20

    def expected_at(t):
        total = 0.0
        for i in range(t - length + 1, t + 1):  # all >= 1 since t >= length
            av, bv = abs(hh[i] - cc[i - 1]), abs(ll[i] - cc[i - 1])
            dv, ev = abs(hh[i] - ll[i - 1]), abs(cc[i - 1] - oo[i - 1])
            if av > bv and av > dv:
                rv = av + bv / 2 + ev / 4
            elif bv > dv and bv > av:
                rv = bv + av / 2 + ev / 4
            else:
                rv = dv + ev / 4
            num = cc[i] - cc[i - 1] + (cc[i] - oo[i]) / 2 + cc[i - 1] - oo[i - 1]
            total += 16 * (num / rv) * max(av, bv)
        return total / cc[t]

    for t in (300, 600, 899):
        assert out.iloc[t] == pytest.approx(expected_at(t), rel=1e-9), f"bar {t}"


def test_branch_one_is_unreachable_on_consistent_ohlc():
    """`R`'s first branch needs `A > B` AND `A > D`. On any bar with
    `L <= H` and `L1 <= C1` that is impossible:

    * `H >= C1`: `A = H - C1` and `D = H - L1 >= H - C1 = A`, so `A > D`
      fails.
    * `H <= C1`: `A = C1 - H` and `B = C1 - L >= C1 - H = A`, so `A > B`
      fails.

    Measured on the 1,500-bar walk: every bar OHLC-consistent, branch 1
    fires 0 times, branch 2 537, branch 3 962 of the 1,499 bars that have a
    prior bar, and neither inequality is violated once. The arm stays in
    the module because it is in the source formula -- but nothing here
    depends on it."""
    open_, high, low, close = _walk()
    assert int(((low <= open_) & (open_ <= high) & (low <= close)
                & (close <= high)).sum()) == 1500

    a, b, d, one, two, three = _branch_masks(open_, high, low, close)
    assert int(one.sum()) == 0
    assert int(two.sum()) == 537
    assert int(three.sum()) == 962
    assert int(two.sum()) + int(three.sum()) == 1499  # every bar with a prior

    c1 = close.shift(1)
    assert int(((high <= c1) & (b < a)).sum()) == 0   # the `H <= C1` pillar
    assert int(((high >= c1) & (d < a)).sum()) == 0   # the `H >= C1` pillar


def test_the_third_branch_mutant_reproduces_the_prototype_and_differs():
    """The port's whole Gate A decision: `R`'s third branch (`D + E/4`),
    which the issue's prototype does not have.

    Collapsing it into the prototype's `B + A/2 + E/4` (a live `exec`'d
    mutant) reproduces the retyped prototype expression BIT-FOR-BIT, so the
    mutant is a faithful stand-in for the prototype -- and it then differs
    from the shipped column at every non-NaN bar of the 1,500-bar walk,
    agreeing per bar only where branch 2 is selected:

        branch-2 bars: 537 of 537 bit-identical
        branch-3 bars:   0 of 962 bit-identical
        column:       1,480 of 1,480 non-NaN bars differ, max|diff| 2.3181

    On the 5-bar fixture of `test_hand_derived_five_bars`, bar 1 (branch 3,
    A=3 B=1 D=8 E=1, N=4):

        shipped R = D + E/4   = 8 + 0.25  = 8.25 -> SI = 16*(4/8.25)*3
        mutant  R = B + A/2 + E/4 = 1 + 1.5 + 0.25 = 2.75
                                      -> SI = 16*(4/2.75)*3

    and bar 2 (branch 2) is identical in both, since there the shipped
    branch IS `B + A/2 + E/4`."""
    mod = _load_mutant(*TWO_BRANCH_MUTANT)
    open_, high, low, close = _walk()
    out = g191_055(open_, high, low, close)
    collapsed = mod.g191_055(open_, high, low, close)
    proto = _retyped_prototype(open_, high, low, close)

    # the mutant IS the prototype, bit for bit
    assert (collapsed.isna() == proto.isna()).all()
    m = collapsed.notna()
    assert (collapsed[m] == proto[m]).all()

    # ... and the shipped column is not
    assert (out.isna() == collapsed.isna()).all()
    assert int((out[m] != collapsed[m]).sum()) == 1480 == int(m.sum())
    assert (out[m] - collapsed[m]).abs().max() == pytest.approx(2.3180569702483527,
                                                                rel=1e-9)

    # per-bar: identical on branch 2, different on branch 3
    si_out = g191_055(open_, high, low, close, length=1) * close
    si_mut = mod.g191_055(open_, high, low, close, length=1) * close
    _, _, _, one, two, three = _branch_masks(open_, high, low, close)
    assert not one.any()
    assert int((si_out[two] == si_mut[two]).sum()) == 537 == int(two.sum())
    assert int((si_out[three] == si_mut[three]).sum()) == 0
    assert int((si_out[three] != si_mut[three]).sum()) == 962 == int(three.sum())

    # the fixture's bar 1, with the arithmetic from the docstring
    o5 = Series([99.0, 100.0, 99.0, 92.0, 92.5])
    h5 = Series([102.0, 103.0, 100.0, 95.0, 92.5])
    l5 = Series([95.0, 99.0, 90.0, 91.0, 92.5])
    c5 = Series([100.0, 102.0, 92.0, 94.0, 92.5])
    ship5 = g191_055(o5, h5, l5, c5, length=1) * c5
    mut5 = mod.g191_055(o5, h5, l5, c5, length=1) * c5
    assert ship5.iloc[1] == pytest.approx(16 * (4.0 / 8.25) * 3.0, abs=1e-12)
    assert mut5.iloc[1] == pytest.approx(16 * (4.0 / 2.75) * 3.0, abs=1e-12)
    assert ship5.iloc[2] == mut5.iloc[2]  # branch 2: the same expression


def test_zero_r_bar_nans_its_whole_window():
    """`R == 0` is reachable, and one such bar NaNs the `length` outputs
    whose window contains it.

    Fixture (length=2), the degenerate bar at index 2:
        open  = [100,  99, 97, 98.0,  99, 100, 101]
        high  = [101, 100, 97, 99.0, 100, 101, 102]
        low   = [ 99,  97, 97, 97.5,  98,  99, 100]
        close = [100,  99, 97, 98.5,  99.5, 100.5, 101.5]

    bar 1 opened and closed at 99 (`E = |C1-O1| = 0` for bar 2) with a low
    of 97; bar 2 is zero-range at exactly that 97 (`D = |H-L1| = 0`), and
    `A == B == 1.5` so no strict `>` passes and branch 3 is selected. Its
    value is `D + E/4 = 0`. `N/R` is then `x/0 -> inf -> NaN` (the frozen
    print is below the prior close), so SI is NaN at bar 2, and
    `min_periods=2` carries that into t=2 and t=3. Measured `R` over the
    fixture: `[nan, 3.0, 0.0, 2.0, 2.625, 3.125, 3.125]`."""
    open_ = Series([100.0, 99.0, 97.0, 98.0, 99.0, 100.0, 101.0])
    high = Series([101.0, 100.0, 97.0, 99.0, 100.0, 101.0, 102.0])
    low = Series([99.0, 97.0, 97.0, 97.5, 98.0, 99.0, 100.0])
    close = Series([100.0, 99.0, 97.0, 98.5, 99.5, 100.5, 101.5])
    assert ((low <= open_) & (open_ <= high) & (low <= close)
            & (close <= high)).all()
    # the premise: the degenerate bar, asserted rather than eyeballed
    assert high.iloc[2] == low.iloc[2] == close.iloc[2] == low.iloc[1]
    assert open_.iloc[1] == close.iloc[1]

    out = g191_055(open_, high, low, close, length=2)
    assert out.iloc[:4].isna().all()          # warm-up 0-1, poisoned 2-3
    assert out.iloc[4:].notna().all()         # and valid again from bar 4
    assert out.iloc[4] == pytest.approx(0.44221105527638194, rel=1e-12)

    # at length=1 only the degenerate bar itself is NaN past the warm-up
    per_bar = g191_055(open_, high, low, close, length=1)
    assert [int(i) for i in per_bar.index[per_bar.isna()]] == [0, 2]


def test_bar_zero_is_masked():
    """`C1`, `O1` and `L1` are undefined at bar 0, so SI is masked there.
    The mask is DECLARATIVE and this test says so: at bar 0 every one of
    `A`, `B`, `D`, `E` is NaN, all three branch tests are False, and the
    third branch's `D + E/4` is NaN too, so the arithmetic alone already
    lands NaN. Pinned at `length=1`, where nothing else can hide it."""
    open_, high, low, close = _walk(50)
    out = g191_055(open_, high, low, close, length=1)

    assert pd.isna(out.iloc[0])
    assert pd.notna(out.iloc[1])
    # the arithmetic's own NaN at bar 0, documented rather than claimed
    c1, o1, l1 = close.shift(1), open_.shift(1), low.shift(1)
    a, b = (high - c1).abs(), (low - c1).abs()
    d, e = (high - l1).abs(), (c1 - o1).abs()
    assert pd.isna(a.iloc[0]) and pd.isna(b.iloc[0])
    assert pd.isna(d.iloc[0]) and pd.isna(e.iloc[0])
    assert not ((a > b) & (a > d)).iloc[0]   # NaN comparisons are False
    assert not ((b > d) & (b > a)).iloc[0]
    assert pd.isna((d + e / 4).iloc[0])      # the selected branch, NaN


def test_misaligned_indexes_raise():
    open_, high, low, close = _walk(100)
    shifted = close.copy()
    shifted.index = pd.RangeIndex(1, 101)
    with pytest.raises(ValueError, match="indexed differently"):
        g191_055(open_, high, low, shifted)


def test_insufficient_history_returns_none():
    open_, high, low, close = _walk(20)  # defaults need length + 1 = 21 bars
    assert g191_055(open_, high, low, close) is None


def test_exact_min_length_fires_at_the_warmup_boundary():
    open_, high, low, close = _walk(21)  # exactly length + 1 = 21 bars
    out = g191_055(open_, high, low, close)
    assert out is not None
    assert out.iloc[:20].isna().all()
    assert pd.notna(out.iloc[20])


def test_default_name():
    open_, high, low, close = _walk()
    assert g191_055(open_, high, low, close).name == "G191_055_20"


def test_distinct_lengths_produce_distinct_names_and_values():
    open_, high, low, close = _walk(400)
    out1 = g191_055(open_, high, low, close, length=5)
    out2 = g191_055(open_, high, low, close, length=40)
    assert out1.name == "G191_055_5"
    assert out2.name == "G191_055_40"
    m = out1.notna() & out2.notna()
    assert (out1[m] != out2[m]).any()


# -------------------------------------------------------------- causality


_REAL = importlib.import_module("pandas_ta.momentum.g191_055")


def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_g191_055_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


SHIPPED_SUM = "result = swing.rolling(length, min_periods=length).sum() / close"
WRITE_SHIFT_MUTANT = (
    SHIPPED_SUM,
    "result = (swing.rolling(length, min_periods=length).sum() / close).shift(-length)",
)
CENTERED_SUM_MUTANT = (
    SHIPPED_SUM,
    # the `bos` look-ahead bug class
    "result = swing.rolling(length, center=True, min_periods=length).sum() / close",
)
TWO_BRANCH_MUTANT = (
    "np.where((b > d) & (b > a), b + a / 2 + e / 4, d + e / 4)",
    "b + a / 2 + e / 4",  # the issue prototype's `R`, third branch collapsed
)

OFFSETS = range(60, 1500, 40)  # past the 21-bar warm-up


def _retyped_prototype(open_, high, low, close, length=20):
    """The issue's prototype expression, RETYPED from
    `docs/issues/screen/ind_screen.py:398-405` (with `delay`/`tsum`/`sdiv`
    from lines 45, 49 and 41), because `docs/issues/` is gitignored and a
    clone running this suite does not have it. TWO-branch `R`.

    `docs/measure_g191_055.py` closes that gap where the file IS present:
    it loads `ind_screen.py` by path, calls the registered `g191_055`
    candidate itself, and reports `max|diff| = 0.0` between this retyping
    and that candidate on the 1,500-bar walk, so the retyping is not
    hiding a slip."""
    c1, o1, l1 = close.shift(1), open_.shift(1), low.shift(1)
    a, b, d = (high - c1).abs(), (low - c1).abs(), (high - l1).abs()
    e = (c1 - o1).abs()
    r = pd.Series(
        np.where((a > b) & (a > d), a + b / 2 + e / 4, b + a / 2 + e / 4),
        index=close.index,
    )
    with np.errstate(divide="ignore", invalid="ignore"):
        si = 16 * ((close - c1 + (close - open_) / 2 + c1 - o1) / r).replace(
            [np.inf, -np.inf], np.nan) * np.maximum(a, b)
    return si.rolling(length).sum() / close


def _leaks(fn):
    open_, high, low, close = _walk(1500)
    oo, oh, ol, oc = _walk(1500, seed=97)
    base = fn(open_, high, low, close)
    hits = 0
    for j in OFFSETS:
        po, ph, pl, pc = open_.copy(), high.copy(), low.copy(), close.copy()
        po.iloc[j:] = oo.iloc[j:].values
        ph.iloc[j:] = oh.iloc[j:].values
        pl.iloc[j:] = ol.iloc[j:].values
        pc.iloc[j:] = oc.iloc[j:].values
        out = fn(po, ph, pl, pc)
        x, y = base.iloc[:j], out.iloc[:j]
        if not (x.isna() == y.isna()).all():
            hits += 1
            continue
        m = x.notna()
        if (x[m] != y[m]).any():
            hits += 1
    return hits


def test_real_module_never_reads_the_future():
    assert _leaks(g191_055) == 0


def test_write_shift_mutant_is_caught():
    mod = _load_mutant(*WRITE_SHIFT_MUTANT)
    open_, high, low, close = _walk(1500)
    assert not mod.g191_055(open_, high, low, close).equals(
        g191_055(open_, high, low, close))  # live
    assert _leaks(mod.g191_055) == len(list(OFFSETS))  # caught, every offset


def test_centered_sum_mutant_is_caught():
    mod = _load_mutant(*CENTERED_SUM_MUTANT)
    open_, high, low, close = _walk(1500)
    assert not mod.g191_055(open_, high, low, close).equals(
        g191_055(open_, high, low, close))  # live
    assert _leaks(mod.g191_055) == len(list(OFFSETS))  # caught, every offset


# ------------------------------------------------------------ reachability


def test_fires_on_a_non_trivial_fraction():
    open_, high, low, close = _walk()  # 1500 bars, defaults
    out = g191_055(open_, high, low, close)
    assert int(out.notna().sum()) == 1480  # exactly n - length, measured
    assert int(out.notna().idxmax()) == 20  # first fire at the warm-up bound


def test_fires_and_is_not_constant():
    open_, high, low, close = _walk()
    out = g191_055(open_, high, low, close)
    fires = int(out.notna().sum())
    assert 0 < fires < len(out)
    assert out.dropna().nunique() > 100


def test_the_column_takes_both_signs():
    """A signed swing tally, not a magnitude: on the 1,500-bar walk 588
    bars are positive and 892 negative, 0 exactly zero. The walk's `open`
    is the SAME bar's close times noise, so it carries no overnight gap
    structure -- the sign imbalance is the frame's, not a property of the
    formula, and nothing here claims otherwise."""
    open_, high, low, close = _walk()
    out = g191_055(open_, high, low, close).dropna()
    assert int((out > 0).sum()) == 588
    assert int((out < 0).sum()) == 892
    assert int((out == 0).sum()) == 0


# ------------------------------------------------------------ scale-free


@pytest.mark.parametrize("k", [8.0, 64.0])
def test_power_of_two_price_scale_is_bit_identical(k):
    open_, high, low, close = _walk()
    base = g191_055(open_, high, low, close)
    scaled = g191_055(open_ * k, high * k, low * k, close * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_other_price_scales_within_tolerance(k):
    """Both bounds are asserted, and which one BINDS depends on the frame,
    so neither is dressed up as the other. On this walk
    `max|column| = 4.486048`, so the relative bound `1e-12 * max|column|`
    is 4.486e-12 while the absolute bound is 1e-12: **here the absolute one
    is the tighter of the two** (48x margin over the measured residual of
    2.0872192862952943e-14 at ×10 / 2.070565940925917e-14 at ×3.7, which
    is 4.65e-15 relative). The relative form is kept because the column is
    signed and unbounded (`N/R` grows as `R` shrinks), so on a frame whose
    column is large the absolute epsilon would fail for a reason that is
    not a scale-freeness defect -- not because it binds today."""
    open_, high, low, close = _walk()
    base = g191_055(open_, high, low, close)
    scaled = g191_055(open_ * k, high * k, low * k, close * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    diff = (base[m] - scaled[m]).abs().max()
    assert diff <= 1e-12 * base[m].abs().max()   # relative: survives a big frame
    assert diff < 1e-12                          # absolute: tighter on THIS walk


@pytest.mark.parametrize("k", [8.0, 64.0, 10.0, 3.7])
def test_price_scale_moves_no_bar_between_branches(k):
    """`R`'s branch tests are exact float `>` comparisons, the one place
    where a rescale could change the column's STRUCTURE rather than just
    its rounding: two distinct products can round equal, turning a strict
    `>` into a tie and pushing a bar to a later branch. Measured on the
    1,500-bar walk: no bar changes branch at any of the four
    multipliers."""
    open_, high, low, close = _walk()
    _, _, _, one, two, three = _branch_masks(open_, high, low, close)
    _, _, _, one_k, two_k, three_k = _branch_masks(
        open_ * k, high * k, low * k, close * k)
    assert (one_k == one).all()
    assert (two_k == two).all()
    assert (three_k == three).all()

    # and through the MODULE, at length=1, where the column is the bar's
    # own SI: a module-side `>` turned into `>=` cannot pass this.
    base = g191_055(open_, high, low, close, length=1)
    scaled = g191_055(open_ * k, high * k, low * k, close * k, length=1)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (np.sign(base[m]) == np.sign(scaled[m])).all()
    # relative, like the tolerance test above: at length=1 the column is a
    # single bar's SI/close, which grows as `R` shrinks.
    assert (base[m] - scaled[m]).abs().max() <= 1e-9 * base[m].abs().max()


# ---------------------------------------------------------------- wiring


def test_name_registration_and_accessor():
    open_, high, low, close = _walk(400)
    df = pd.DataFrame({"open": open_, "high": high, "low": low, "close": close})
    assert "g191_055" in ta.Category["momentum"]
    out = df.ta.g191_055()
    assert out.name == "G191_055_20"
    pd.testing.assert_series_equal(out, g191_055(open_, high, low, close))
    # tunable kwarg forwarded under its own name -- the "supertrend
    # failure mode" (CLAUDE.md) hasattr cannot see.
    renamed = df.ta.g191_055(length=10)
    assert renamed.name == "G191_055_10"
