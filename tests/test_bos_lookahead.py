# -*- coding: utf-8 -*-
"""`bos` reads the future. This pins HOW FAR, so the leak cannot grow, shrink or vanish unseen.

THE LEAK
--------
`pandas_ta/trend/bos.py` flags swings with `high == high.rolling(swing_length, center=True).max()`
(and the `low` mirror) in one batched pass before its per-bar loop runs. A centered window at bar
`i` includes bars AFTER `i`, so a pivot's flag is decided by bars that have not printed yet and is
written back to the pivot bar. The loop then carries that flag forward into all four columns:
`BOS_BULL`, `BOS_BEAR`, `HIGHER_HIGH`, `LOWER_LOW`.

It is a defect, not a design choice like `ICS_26` or `dpo(centered=True)`, and it is NOT fixed
here. `pandas_ta.trend.swing_equilibrium` re-implements the same swing tracking causally (a pivot
becomes visible only `right` bars after it printed) and is the model for a fix. Changing `bos`
changes its column values, so fixing it is the owner's call; until then this module is the guard.

Blast radius, measured 2026-10-20 by grep, not assumed: the parent repo has **zero** calls to
`ta.bos` / `df.ta.bos` and **zero** `df.ta.strategy()` sweeps, so no parent column comes from this
function. The parent's own private `BOS_BULL` / `FRACTAL_*` builders are a separate copy and a
separate question; this module says nothing about them.

WHAT IS PINNED, in order of how much it would hurt to lose
-----------------------------------------------------------
1. **The reach is exactly `(swing_length - 1) // 2` bars, on every column.** Measured with a dense
   sweep: every cut from bar 40 to 149 of a 160-bar frame, bars >= cut scaled by x1.4 AND,
   separately, by x0.6. Seeds 0-3, `swing_length` 4 / 5 / 7 / 9 -> reach 1 / 2 / 3 / 4 on all four
   columns, all 16 combinations. Equality, not `<=`: a `bos` that stopped leaking (reach 0) or
   started leaking further must both fail, and only equality catches both.
   Two ways to measure this WRONG, both hit while writing it:
   * a sparse sweep (the earlier showcase pin used `range(200, 460, 13)`) only sees the pivots its
     cuts happen to straddle, and measured 2 at `swing_length=7` against a true reach of 3;
   * scaling UP only leaves the low side under-measured: on this frame x1.4 alone gave
     `BOS_BEAR` / `LOWER_LOW` a reach of 2 at `swing_length=9`, not 4. Raising later bars cannot
     unseat a swing LOW, so the low side needs the downward perturbation.
2. **The leak comes from `center=True` and nowhere else.** The same module with only those two
   arguments flipped to `center=False`, exec'd in memory, measures reach 0 on all four columns. So
   the probe can tell a clean implementation from a leaky one, and the leak has one source.
   ⚠ A trailing window is NOT the fix - it moves every pivot to the bar that confirms it, changing
   what the columns mean. It is only the control.
3. **Even windows reach `(w - 1) // 2`, not `w // 2`.** That is pandas' centering, measured on a
   unit spike in `test_pandas_centered_window_geometry`. If pandas ever re-centers even windows,
   that test fails first and points at pandas rather than at `bos`.
"""
import importlib.util

import numpy as np
import pandas as pd
import pytest

import pandas_ta as ta

SWING_LENGTHS = [4, 5, 7, 9]
COLUMNS = ["BOS_BULL", "BOS_BEAR", "HIGHER_HIGH", "LOWER_LOW"]


def _frame(n=160, seed=0):
    rng = np.random.default_rng(seed)
    close = 100 * np.exp(np.cumsum(rng.normal(0, 0.012, n)))
    spread = np.abs(rng.normal(0, 0.006, n)) * close
    return pd.DataFrame({"high": close + spread, "low": close - spread, "close": close})


def _reach(fn, d, swing_length):
    """Per column: how many bars BEFORE a cut the earliest changed value sits.

    Every cut, both perturbation directions - see point 1 of the module docstring for why each
    of those is load-bearing.
    """
    base = fn(d["high"], d["low"], d["close"], swing_length=swing_length)
    reach = {col: 0 for col in base.columns}
    for factor in (1.4, 0.6):
        for cut in range(40, 150):
            perturbed = d.copy()
            perturbed.iloc[cut:] *= factor
            out = fn(perturbed["high"], perturbed["low"], perturbed["close"],
                     swing_length=swing_length)
            for col in base.columns:
                a = base[col].to_numpy(float)[:cut]
                b = out[col].to_numpy(float)[:cut]
                moved = np.flatnonzero(a != b)
                if len(moved):
                    reach[col] = max(reach[col], cut - int(moved.min()))
    return reach


@pytest.mark.parametrize("swing_length", SWING_LENGTHS)
def test_bos_reads_exactly_half_the_swing_window_ahead(swing_length):
    bound = (swing_length - 1) // 2
    reach = _reach(ta.bos, _frame(), swing_length)
    assert sorted(reach) == sorted(COLUMNS)
    if all(r == 0 for r in reach.values()):
        pytest.fail(f"bos(swing_length={swing_length}) no longer reads the future. If that was a "
                    "deliberate fix, delete this module and the bos entry in CLAUDE.md's causal list.")
    assert reach == {col: bound for col in COLUMNS}, (
        f"bos(swing_length={swing_length}) reach changed: measured {reach}, pinned {bound} on every "
        "column - re-measure and update the module docstring")


def test_the_trailing_window_control_is_clean():
    spec = importlib.util.find_spec("pandas_ta.trend.bos")
    src = open(spec.origin, encoding="utf8").read()
    control = src.replace("center=True", "center=False")
    assert control.count("center=False") == 2, "the control did not apply -- blind test"
    ns = {}
    exec(compile(control, "<trailing-control>", "exec"), ns)

    for swing_length in SWING_LENGTHS:
        reach = _reach(ns["bos"], _frame(), swing_length)
        assert reach == {col: 0 for col in COLUMNS}, (
            f"with center=False, swing_length={swing_length} still leaks {reach}: the probe is "
            "wrong, or bos has a second source of look-ahead")


@pytest.mark.parametrize("window", SWING_LENGTHS)
def test_pandas_centered_window_geometry(window):
    spike = pd.Series(np.zeros(60))
    spike.iloc[40] = 1.0
    seen = np.flatnonzero(spike.rolling(window, center=True).max().to_numpy() == 1)
    assert 40 - int(seen.min()) == (window - 1) // 2
