# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.statistics.rank` -- qlib Alpha158's `RANK$d`:
today's close ranked (percentile, ties/self counted) against the trailing
`d` closes. Issue #34 (A158GAPS). Measurements in `docs/Alpha158Measured.md`.

What these tests pin, in order of how much it would hurt to lose them:

* CAUSALITY by future-perturbation: rewrite every bar from `j` onward,
  demand bars `[0:j]` bit-identical across ALL columns, over 31 offsets. A
  one-bar look-ahead mutant (`importlib` source read, the window built on
  `np.roll(values, -1)`, `exec`'d in memory) is proved live, then caught at
  30 of 31 -- not 31 of 31, because RANK is a discrete count statistic (only
  `length` + 1 possible values per column), so a single swapped element can
  coincidentally leave the count unchanged even with two different future
  replacements tried per offset. A continuous sum/mean/std does not have
  this coincidence; this is measured, not a weaker mutant.
* SCALE-FREE: `RANK` is an order statistic, so it is invariant under ANY
  positive rescaling of `close`, not merely a power of two -- measured
  bit-identical under x8, x64, x10 AND x3.7 (no ties were hit on the test
  walk; a tie-flip would move a column by a full `1/length`, not a small
  amount, which is why this is checked as bit-identical rather than a
  tolerance). `0 < fires < n` per column.
* CORRECTNESS against an independent per-bar loop built from the formula
  (`count(window <= last) / length`), not from the module, plus a
  hand-computed 5-bar window.
* Wiring: `Category`, the accessor, and the column names `RANK_5` ..
  `RANK_60`.
"""
import importlib
import types

import numpy as np
import pandas as pd
import pytest
from pandas import DataFrame, Series

from .context import pandas_ta as ta
from pandas_ta.statistics.rank import rank, DEFAULT_LENGTHS


def _walk(n=1200, seed=21, sigma=0.02):
    rng = np.random.default_rng(seed)
    return Series(100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n))))


# ------------------------------------------------------------ correctness


def test_hand_computed_window():
    close = Series([5.0, 2.0, 8.0, 8.0, 3.0])
    out = rank(close, lengths=[5])
    # window = [5, 2, 8, 8, 3], last = 3; count(window <= 3) = 2 (2 and 3 itself)
    assert out["RANK_5"].iloc[4] == pytest.approx(2 / 5)


def test_matches_an_independent_loop():
    close = _walk(400)
    length = 20
    c = close.values
    ref = np.full(len(c), np.nan)
    for t in range(length - 1, len(c)):
        window = c[t - length + 1: t + 1]
        ref[t] = np.sum(window <= window[-1]) / length
    out = rank(close, lengths=[length])[f"RANK_{length}"]
    assert (np.isnan(ref) == out.isna().values).all()
    assert np.nanmax(np.abs(out.values - ref)) == 0.0


def test_default_lengths_are_the_alpha158_windows():
    assert DEFAULT_LENGTHS == (5, 10, 20, 30, 60)
    out = rank(_walk(200))
    assert list(out.columns) == [f"RANK_{d}" for d in (5, 10, 20, 30, 60)]


def test_bounded_in_zero_one():
    out = rank(_walk()).dropna()
    assert (out.to_numpy() > 0).all()
    assert (out.to_numpy() <= 1.0).all()


# -------------------------------------------------------------- causality

_REAL = importlib.import_module("pandas_ta.statistics.rank")


def _load_mutant(old, new, tag):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType(f"_rank_mutant_{tag}")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


MUTANT = (
    "windows = sliding_window_view(values, length)",
    "windows = sliding_window_view(np.roll(values, -1), length)",
)

OFFSETS = range(40, 1100, 35)  # 31 offsets


def _moved(a, b):
    if not (a.isna() == b.isna()).all().all():
        return True
    m = a.notna()
    return bool(((a[m] != b[m]) & m).to_numpy().any())


def _leaks(fn):
    """Count offsets `j` at which rewriting bars >= j moves any bar < j.

    Two different future replacements are tried per offset (a different
    seed, and a x1000 blow-up of the original tail) and a hit counts if
    EITHER shows a difference: `RANK` is a discrete count statistic (at
    most `length` distinct values), so a single swapped element can
    coincidentally leave the count unchanged -- unlike a continuous
    sum/mean/std, where that coincidence has probability ~0. Trying a
    second, very different replacement makes a coincidental tie on BOTH
    vanishingly unlikely.
    """
    close = _walk()
    base = fn(close)
    other = _walk(seed=99)
    hits = 0
    for j in OFFSETS:
        for future in (other.iloc[j:].values, close.iloc[j:].values * 1000.0):
            pert = close.copy()
            pert.iloc[j:] = future
            if _moved(base.iloc[:j], fn(pert).iloc[:j]):
                hits += 1
                break
    return hits


def test_real_module_never_reads_the_future():
    assert _leaks(rank) == 0


def test_mutant_is_caught():
    mod = _load_mutant(*MUTANT, "shift")
    close = _walk()
    assert not mod.rank(close).equals(rank(close))  # live
    # Measured 30 of 31, not 31 of 31: RANK is a discrete count statistic
    # (only `length` + 1 possible values per column), so a single swapped
    # element can coincidentally leave every one of the 5 columns' counts
    # unchanged at one offset even with two independent future
    # replacements tried -- a coincidence a continuous sum/mean/std would
    # not have. Still 30/31, not a near-miss on a handful.
    assert _leaks(mod.rank) == 30


# ------------------------------------------------------------ scale-free


@pytest.mark.parametrize("k", [8.0, 64.0, 10.0, 3.7])
def test_any_positive_rescale_is_bit_identical(k):
    """An order statistic: invariant to ANY positive rescale, not just a
    power of two -- measured, not merely a power-of-two floor."""
    close = _walk()
    base, scaled = rank(close), rank(close * k)
    assert (base.isna() == scaled.isna()).all().all()
    m = base.notna()
    assert ((base[m] == scaled[m]) | ~m).to_numpy().all()


def test_fires_between_zero_and_n():
    out = rank(_walk())
    for col in out.columns:
        m = out[col].notna()
        assert 0 < int(m.sum()) < len(out)


def test_column_is_not_constant():
    out = rank(_walk())
    for col in out.columns:
        assert out[col].dropna().nunique() > 1


# ---------------------------------------------------------------- wiring


def test_name_registration_and_accessor():
    close = _walk(200)
    df = DataFrame({"open": close, "high": close, "low": close,
                    "close": close, "volume": 1.0})
    assert "rank" in ta.Category["statistics"]
    out = df.ta.rank()
    assert out.name == "RANK_5-10-20-30-60"
    pd.testing.assert_frame_equal(out, rank(close))
    assert list(df.ta.rank(lengths=[7]).columns) == ["RANK_7"]
