# -*- coding: utf-8 -*-
"""`bos` and `choch` are causal (issue #332). Pins the fix, so the look-ahead cannot come back.

THE OLD DEFECT
--------------
Before #332 both modules flagged swings with `high == high.rolling(swing_length, center=True).max()`
(and the `low` mirror). A centred window at bar `j` includes bars after `j`, and the flag was
written on `j` itself, so every column read `(swing_length - 1) // 2` bars ahead: 1 / 2 / 3 / 4 at
`swing_length` 4 / 5 / 7 / 9 (measured for `bos` by the deleted `tests/test_bos_lookahead.py`;
`choch` used the same two lines, and the mutant test below measures the same reach for it).

THE FIX
-------
`pandas_ta.trend.bos._confirmed_swings` keeps the same window but writes each swing on the bar
that confirms it: with `L = swing_length`, `k = (L - 1) // 2`, `left = L - 1 - k`, a swing high at
`j` is confirmed on bar `t = j + k` iff `high[j] == max(high[j-left .. j+k])` and no bar in
`(j, j+k]` equals it (rightmost tie wins, as in `swing_equilibrium._confirm_pivots`). `choch`
imports the same helper.

WHAT IS PINNED, in order of how much it would hurt to lose
-----------------------------------------------------------
1. **No column reads a later bar** (Gate B). Dense sweep: every cut from bar 40 to 149 of a
   160-bar frame, bars >= cut scaled by x1.4 and, separately, by x0.6 (raising later bars cannot
   unseat a swing low, so the low side needs the downward move). Seeds 0-3, `swing_length`
   4 / 5 / 7 / 9: every bar before the cut is unchanged, on all six columns, each module alone.
2. **The probe catches the old defect** (mutant). The module source with the swing written back
   `k` bars (`.shift(-k)`: the old centred placement on tie-free frames, which the sweep's frames
   are; on a tie the old window flagged every tied bar, the mutant only the rightmost) is exec'd in memory and
   measures reach `k` on each module alone, at every length above.
3. **The formula** (Gate A). An independent per-bar loop over the issue's formula matches the
   module's swings and all six columns exactly, `swing_length` 1-9, seeds 0-4.
4. **Same swings as before, only later.** On a frame with no tied highs or lows, the confirmed
   swings are exactly the old centred swings moved `k` bars later.
5. **Ties.** A double top inside one window confirms exactly one swing high: the right-hand bar.
6. **Scale-free** (Gate D). x8 / x64 / x10 / x3.7 identical (0/1 flags of price
   comparisons), with every column firing on some bars and not on all.
"""
import inspect
import sys

import numpy as np
import pandas as pd
import pytest

from pandas_ta.trend.bos import _confirmed_swings, bos
from pandas_ta.trend.choch import choch

# `import pandas_ta.trend.bos as m` binds the FUNCTION (the package re-exports `bos` under the
# submodule's name), so read the module objects from sys.modules.
bos_mod = sys.modules["pandas_ta.trend.bos"]
choch_mod = sys.modules["pandas_ta.trend.choch"]

LENGTHS = (4, 5, 7, 9)
BOS_COLS = ["BOS_BULL", "BOS_BEAR", "HIGHER_HIGH", "LOWER_LOW"]
CHOCH_COLS = ["CHoCH_BULL", "CHoCH_BEAR"]


def _frame(n=160, seed=0):
    rng = np.random.default_rng(seed)
    close = 100 * np.exp(np.cumsum(rng.normal(0, 0.02, n)))
    spread = np.abs(rng.normal(0, 0.01, n)) * close
    high = close + spread * rng.uniform(0.2, 1.0, n)
    low = close - spread * rng.uniform(0.2, 1.0, n)
    idx = pd.RangeIndex(n)
    return pd.Series(high, idx), pd.Series(low, idx), pd.Series(close, idx)


def _both(h, l, c, L, b=bos, ch=choch):
    return pd.concat([b(h, l, c, swing_length=L), ch(h, l, c, swing_length=L)], axis=1)


def _reach(fn, L, seeds=range(4), n=160):
    """Largest number of bars before a cut whose output moves when only bars >= cut move."""
    worst = 0
    for seed in seeds:
        h, l, c = _frame(n, seed)
        base = fn(h, l, c, swing_length=L)
        for cut in range(40, n - 10):
            for f in (1.4, 0.6):
                m = np.ones(n)
                m[cut:] = f
                pert = fn(h * m, l * m, c * m, swing_length=L)
                diff = (base.iloc[:cut] != pert.iloc[:cut]).any(axis=1).to_numpy()
                if diff.any():
                    worst = max(worst, cut - int(np.argmax(diff)))
    return worst


def _mutant_pair():
    """bos/choch with each swing written back on its pivot bar: the old centred placement."""
    src = inspect.getsource(bos_mod)
    target = "        return cand.where(hit)\n"
    assert src.count(target) == 1
    src = src.replace(target, "        return cand.where(hit).shift(-k)\n")
    ns = {"__name__": "bos_mutant"}
    exec(compile(src, "bos_mutant", "exec"), ns)
    csrc = inspect.getsource(choch_mod)
    imp = "from pandas_ta.trend.bos import _confirmed_swings\n"
    assert csrc.count(imp) == 1
    cns = {"__name__": "choch_mutant", "_confirmed_swings": ns["_confirmed_swings"]}
    exec(compile(csrc.replace(imp, ""), "choch_mutant", "exec"), cns)
    return ns["bos"], cns["choch"]


@pytest.mark.parametrize("which", [0, 1], ids=["bos", "choch"])
@pytest.mark.parametrize("L", LENGTHS)
def test_no_column_reads_a_later_bar(L, which):
    assert _reach((bos, choch)[which], L) == 0


@pytest.mark.parametrize("which", [0, 1], ids=["bos", "choch"])
@pytest.mark.parametrize("L", LENGTHS)
def test_mutant_with_the_old_centred_placement_is_caught(L, which):
    assert _reach(_mutant_pair()[which], L) == (L - 1) // 2


def _oracle(h, l, c, L):
    """The issue's formula as a plain per-bar loop, sharing no code with the module."""
    hi, lo, cl = h.to_numpy(), l.to_numpy(), c.to_numpy()
    n = len(cl)
    k = (L - 1) // 2
    left = L - 1 - k
    sh = np.full(n, np.nan)
    sl = np.full(n, np.nan)
    for t in range(n):
        j = t - k
        if j - left < 0:
            continue
        win_h = hi[j - left: t + 1]
        win_l = lo[j - left: t + 1]
        if hi[j] == max(win_h) and all(hi[i] != hi[j] for i in range(j + 1, t + 1)):
            sh[t] = hi[j]
        if lo[j] == min(win_l) and all(lo[i] != lo[j] for i in range(j + 1, t + 1)):
            sl[t] = lo[j]
    out = {name: np.zeros(n) for name in BOS_COLS + CHOCH_COLS}
    last_h = last_l = np.nan
    trend = 0
    for t in range(n):
        if not np.isnan(sh[t]):
            if not np.isnan(last_h) and sh[t] > last_h:
                out["HIGHER_HIGH"][t] = 1
            if not np.isnan(last_h) and sh[t] < last_h:
                trend = -1
            last_h = sh[t]
        if not np.isnan(sl[t]):
            if not np.isnan(last_l) and sl[t] < last_l:
                out["LOWER_LOW"][t] = 1
            if not np.isnan(last_l) and sl[t] > last_l:
                trend = 1
            last_l = sl[t]
        bull = not np.isnan(last_h) and cl[t] > last_h
        bear = not np.isnan(last_l) and cl[t] < last_l
        out["BOS_BULL"][t] = bull
        out["BOS_BEAR"][t] = bear
        if bull and trend == -1:
            out["CHoCH_BULL"][t] = 1
            trend = 0
        if bear and trend == 1:
            out["CHoCH_BEAR"][t] = 1
            trend = 0
    return sh, sl, pd.DataFrame(out, index=c.index)


@pytest.mark.parametrize("L", range(1, 10))
@pytest.mark.parametrize("seed", range(5))
def test_matches_an_independent_loop_over_the_formula(L, seed):
    h, l, c = _frame(400, seed)
    # Round to a tick so ties occur and the tie rule is exercised, not just the plain case.
    h, l, c = h.round(0), l.round(0), c.round(0)
    sh, sl, ref = _oracle(h, l, c, L)
    got_h, got_l = _confirmed_swings(h, l, L)
    np.testing.assert_array_equal(got_h.to_numpy(), sh)
    np.testing.assert_array_equal(got_l.to_numpy(), sl)
    got = _both(h, l, c, L)
    pd.testing.assert_frame_equal(got[ref.columns], ref, check_dtype=False)


@pytest.mark.parametrize("L", LENGTHS)
def test_same_swings_as_the_old_centred_window_only_k_bars_later(L):
    h, l, c = _frame(400, 7)
    assert h.duplicated().sum() == 0 and l.duplicated().sum() == 0
    k = (L - 1) // 2
    old_h = (h == h.rolling(L, center=True).max())
    old_l = (l == l.rolling(L, center=True).min())
    new_h, new_l = _confirmed_swings(h, l, L)
    assert old_h.sum() > 10 and old_l.sum() > 10
    pd.testing.assert_series_equal(new_h.notna(), old_h.shift(k, fill_value=False), check_names=False)
    pd.testing.assert_series_equal(new_l.notna(), old_l.shift(k, fill_value=False), check_names=False)


def test_a_double_top_confirms_one_swing_on_the_right_hand_bar():
    #            0    1    2    3    4    5    6    7    8    9
    high = pd.Series([10, 11, 12, 15, 13, 15, 12, 11, 10, 9], dtype=float)
    low = high - 1
    sh, _ = _confirmed_swings(high, low, 5)          # k = 2
    confirmed = sh.dropna()
    assert list(confirmed.index) == [7]             # pivot bar 5 (the right-hand top) + k
    assert confirmed.iloc[0] == 15
    # The old centred window flagged BOTH tops.
    assert (high == high.rolling(5, center=True).max()).sum() == 2


@pytest.mark.parametrize("fn,cols", [(bos, BOS_COLS), (choch, CHOCH_COLS)])
def test_scale_free(fn, cols):
    h, l, c = _frame(1200, 3)
    base = fn(h, l, c)
    n = len(c)
    for col in cols:
        fires = int(base[col].sum())
        assert 0 < fires < n, (col, fires)
    for f in (8.0, 64.0):
        pd.testing.assert_frame_equal(fn(h * f, l * f, c * f), base)
    for f in (10.0, 3.7):
        pd.testing.assert_frame_equal(fn(h * f, l * f, c * f), base)


def test_column_names_unchanged():
    h, l, c = _frame()
    assert list(bos(h, l, c).columns) == BOS_COLS and bos(h, l, c).name == "BOS_5"
    assert list(choch(h, l, c).columns) == CHOCH_COLS and choch(h, l, c).name == "CHoCH_5"
