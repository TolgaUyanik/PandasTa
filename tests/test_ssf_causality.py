# -*- coding: utf-8 -*-
"""`ssf` read the future. This pins the fix, and the way it was found.

THE BUG
-------
`pandas_ta/overlap/ssf.py` ran its recursion as `for i in range(0, m)`. At
`i = 0` the body evaluates `ssf.iloc[i - 1]` -> `ssf.iloc[-1]`, which is
Python negative indexing: **the last bar of the series**. The 3-pole branch
reaches `iloc[-3]`. Since `ssf` is seeded as a copy of `close`, the first
two or three output bars were computed from the last two or three CLOSES, and
because the filter is recursive that contamination then propagated forward
through every subsequent bar.

Measured before the fix, on a 400-bar frame: altering only bars from index
300 onward moved the output at **bar 0** by **31.4**. The first differing bar
was 0, not 297 — this was never an edge effect.

WHY IT MATTERS BEYOND ONE INDICATOR
------------------------------------
`PandasTa/CLAUDE.md`'s ML feature contract says value at bar T reads only bars
<= T, and that *"the complete exception list is two upstream columns"*
(`ichimoku`'s `ICS_26`, and `dpo` at `centered=True`). `ssf` was a third, and
it was undocumented — so the exception list was not complete and anything
relying on it was relying on a list, not a measurement.

HOW IT WAS FOUND, which is the part worth keeping
--------------------------------------------------
Not by reading the source. MLCOL-1's companion screen added a per-parent
causality probe — perturb the tail, require the prefix to be bit-identical —
specifically because a hand-maintained exception list only contains the cases
someone already thought of. It caught `dpo` and `ICS_26`, which were known,
and `ssf`, which was not.

The same run also showed why causality must gate the INCREMENTAL axis rather
than sit beside it: the leaking `dpo` companion was ranked FIRST by axis 3a
at dAUC +0.0473 and permutation importance +0.35693, beating its own shuffled
null 15/15, in a field where every honest candidate scored ~0.01. Leakage is
the strongest signal a model can be handed, so the axis promotes it rather
than rejecting it, with every control behaving exactly as designed.

BLAST RADIUS, measured rather than assumed
-------------------------------------------
`ssf` IS emitted by the engine, is NOT admitted to the mining tree
(`MiningConfig` bars it), and IS consumed by `strategy_factory.py:299` as a
named crossover strategy. `StrategyMaster.csv` contains **zero** rows
mentioning it and **zero** `status=paper` rows mentioning it, so no mined or
deployed strategy was affected. Backtests that enumerated the generated `ssf`
crossover family before 2026-09-11 are contaminated.
"""
import numpy as np
import pytest
from pandas import Series

import pandas_ta as ta


def _frame(n=400, seed=0):
    rng = np.random.default_rng(seed)
    return Series(100 * np.exp(np.cumsum(rng.normal(0, 0.012, n))))


@pytest.mark.parametrize("poles", [2, 3])
@pytest.mark.parametrize("cut", [150, 300, 380])
def test_ssf_does_not_read_the_future(poles, cut):
    """Alter only bars >= cut; every earlier bar must be bit-identical."""
    close = _frame()
    perturbed = close.copy()
    perturbed.iloc[cut:] *= 1.5

    a = np.asarray(ta.ssf(close, poles=poles), dtype=float)[:cut]
    b = np.asarray(ta.ssf(perturbed, poles=poles), dtype=float)[:cut]
    m = np.isfinite(a) & np.isfinite(b)
    assert m.any()
    assert float(np.abs(a[m] - b[m]).max()) == 0.0, (
        f"ssf(poles={poles}) leaks the future: perturbing bars >= {cut} moved "
        f"an earlier bar")


@pytest.mark.parametrize("poles", [2, 3])
def test_the_negative_index_mutant_is_caught(poles):
    """The exact bug, re-introduced, must fail the probe above.

    Without this the causality test could pass on an implementation that
    never reads anything at all, and it would not prove the probe can see the
    defect it was written for.
    """
    import importlib.util
    spec = importlib.util.find_spec("pandas_ta.overlap.ssf")
    src = open(spec.origin, encoding="utf8").read()
    # put the loop bounds back the way they were
    mutated = src.replace("for i in range(3, m):", "for i in range(0, m):") \
                 .replace("for i in range(2, m):", "for i in range(0, m):")
    assert mutated != src, "the mutation did not apply -- blind test"
    ns = {}
    exec(compile(mutated, "<mutant>", "exec"), ns)
    mut = ns["ssf"]

    close = _frame()
    perturbed = close.copy()
    perturbed.iloc[300:] *= 1.5
    a = np.asarray(mut(close, poles=poles), dtype=float)[:300]
    b = np.asarray(mut(perturbed, poles=poles), dtype=float)[:300]
    m = np.isfinite(a) & np.isfinite(b)
    assert float(np.abs(a[m] - b[m]).max()) > 0.0, (
        "the pre-fix implementation did NOT leak, so either the bug was "
        "somewhere else or this mutant no longer reproduces it")


@pytest.mark.parametrize("poles", [2, 3])
def test_the_warmup_is_seeded_with_close_not_zero(poles):
    """The first `poles` bars are the recursion's seed, not a reading.

    They are `close`, which is the conventional warm-up and what Ehlers'
    formulation assumes. Zeroing them would plant a synthetic value on real
    bars -- the defect PINEBI-1e removed from `normalize`.
    """
    close = _frame()
    out = ta.ssf(close, poles=poles)
    assert np.allclose(out.iloc[:poles].to_numpy(),
                       close.iloc[:poles].to_numpy())


def test_ssf_still_smooths():
    """A causality fix that broke the filter would pass every test above."""
    close = _frame()
    out = ta.ssf(close, length=10, poles=2).dropna()
    assert out.diff().abs().mean() < close.diff().abs().mean(), \
        "ssf is no longer smoother than its input"
    assert out.nunique() > 100
