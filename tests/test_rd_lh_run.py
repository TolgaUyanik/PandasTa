# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.trend.rd_lh_run` -- the run length of consecutive
lower highs (issue #182, RD-LH-RUN; Reddit, tier 4, untested by the poster).
Measurements are in docs/RdLhRunMeasured.md.

What these pin, in order of how much it would hurt to lose:

* CORRECTNESS against an independent Python loop built straight from the
  issue's own recursion (`n[t] = n[t-1] + 1 if high[t] < high[t-1] else 0`),
  plus a hand-computed sequence.
* CAUSALITY by future-splice: bars before a perturbation point J stay
  bit-identical whether or not the frame's tail is replaced by an unrelated
  series, at every swept J, and a mutant (`high.shift(-1)` in place of
  `high.shift(1)`, comparing to the NEXT bar instead of the prior one) is
  proved live and caught at every J.
* SCALE-FREE: `high < high.shift(1)` is a direct comparison of two raw
  values (not a subtraction compared to zero), so it is bit-identical under
  any positive rescale unless the rescale's own rounding creates or removes
  an exact tie -- measured 0 such ties on the synthetic walk, so x8/x64/x10/
  x3.7 are all bit-identical here.
* Reachability (`0 < fires < n`, not constant, bounded by `cap`) and the
  wiring (`Category`, the accessor, the column name).
"""
import importlib
import types

import numpy as np
import pandas as pd
import pytest
from pandas import DataFrame, Series

from .context import pandas_ta as ta
from pandas_ta.trend.rd_lh_run import rd_lh_run


def _walk(n=1200, seed=11, start=100.0, sigma=0.012):
    rng = np.random.default_rng(seed)
    close = start * np.exp(np.cumsum(rng.normal(0.0, sigma, n)))
    spread = close * np.abs(rng.normal(0.0, 0.006, n))
    high = close + spread * rng.uniform(0.2, 1.0, n)
    return Series(high)


# ---------------------------------------------------------------------
# Gate A -- correctness
# ---------------------------------------------------------------------
def test_hand_computed():
    # bar0: no prior -> 0 (else branch); 9<10 -> 1; 8<9 -> 2; tie(8==8) -> 0;
    # 11>8 -> 0; 10<11 -> 1; 10==10 -> 0
    high = Series([10.0, 9.0, 8.0, 8.0, 11.0, 10.0, 10.0])
    out = rd_lh_run(high)
    assert out.tolist() == [0.0, 1.0, 2.0, 0.0, 0.0, 1.0, 0.0]


def test_matches_an_independent_loop():
    high = _walk(n=800, seed=7)
    hv = high.to_numpy(dtype=float)
    ref = np.zeros(len(hv))
    for t in range(1, len(hv)):
        ref[t] = ref[t - 1] + 1 if hv[t] < hv[t - 1] else 0.0
    out = rd_lh_run(high)
    assert not out.isna().any()
    assert (out.to_numpy() == ref).all()


def test_short_input_returns_none():
    assert rd_lh_run(Series([1.0])) is None


# ---------------------------------------------------------------------
# Gate B -- causality
# ---------------------------------------------------------------------
def _load_mutant():
    old = "lower_high = high < high.shift(1)\n    result = ml_bars_since(~lower_high, cap=cap)"
    new = "lower_high = high < high.shift(-1)\n    result = ml_bars_since(~lower_high, cap=cap)"
    mod_file = importlib.import_module("pandas_ta.trend.rd_lh_run").__file__
    src = open(mod_file, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_rd_lh_run_mutant")
    mod.__file__ = mod_file
    exec(compile(src.replace(old, new), mod_file, "exec"), mod.__dict__)
    return mod


OFFSETS = range(40, 1100, 35)  # 31 offsets


def _moved(a, b):
    if not (a.isna() == b.isna()).all():
        return True
    m = a.notna()
    return bool((a[m] != b[m]).any())


def _leaks(fn, base_h, other_h):
    """Count offsets `j` at which rewriting bars >= j moves any bar < j.

    A single random-walk replacement at the tail flips a ONE-BAR-AHEAD
    mutant's flag at bar j-1 only about half the time (a boolean is either
    already True or already False before the rewrite), so a lone random
    future caught this mutant at only 16 of 31 J. Pairing a future pinned
    HIGH (forces the next-bar read True) with one pinned LOW (forces it
    False) covers both cases: whichever of the two differs from the base's
    actual (unknown) value is guaranteed to flip it.
    """
    base = fn(base_h)
    hits = 0
    for j in OFFSETS:
        futures = [
            other_h.iloc[j:].to_numpy(),               # independent random walk
            np.full(len(base_h) - j, 1.0e6),            # pinned far above
            np.full(len(base_h) - j, 1.0e-6),            # pinned far below
        ]
        for fut in futures:
            sh = base_h.copy()
            sh.iloc[j:] = fut
            if _moved(base.iloc[:j], fn(sh).iloc[:j]):
                hits += 1
                break
    return hits


def test_real_module_never_reads_the_future():
    ah, bh = _walk(1200, seed=1), _walk(1200, seed=2)
    assert _leaks(rd_lh_run, ah, bh) == 0


def test_lookahead_mutant_is_caught():
    mod = _load_mutant()
    ah, bh = _walk(1200, seed=1), _walk(1200, seed=2)
    mut = lambda h: mod.rd_lh_run(h)  # noqa: E731
    assert not mut(ah).equals(rd_lh_run(ah))  # live
    hits = _leaks(mut, ah, bh)
    assert hits == len(OFFSETS), f"mutant caught at only {hits} of {len(OFFSETS)} J"


# ---------------------------------------------------------------------
# Gate D -- scale-free
# ---------------------------------------------------------------------
@pytest.mark.parametrize("k", [8.0, 64.0, 10.0, 3.7])
def test_scale_is_bit_identical(k):
    """`high < high.shift(1)` compares two raw values directly, so a
    positive rescale only disagrees with the unscaled comparison if it
    creates/removes an exact tie through independent rounding of the two
    scaled operands -- measured (docs/measure_rd_lh_run.py): 0 consecutive
    exact ties in `high` on this walk, so 0 mismatches at any of these k."""
    high = _walk(seed=4)
    base = rd_lh_run(high)
    scaled = rd_lh_run(high * k)
    assert (base.isna() == scaled.isna()).all()
    assert (base.to_numpy() == scaled.to_numpy()).all()


# ---------------------------------------------------------------------
# Gate C -- reachability
# ---------------------------------------------------------------------
def test_fires_and_is_not_constant():
    high = _walk(seed=4)
    out = rd_lh_run(high)
    assert not out.isna().any()
    assert 0 < int((out > 0).sum()) < len(out)
    assert out.nunique() > 1
    assert (out >= 0).all()
    assert (out <= 100).all()


def test_cap():
    high = Series(np.linspace(30, 1, 30))  # every bar after bar 0 is a lower high
    out = rd_lh_run(high, cap=10)
    assert out.name == "RD_LH_RUN_10"
    assert out.iloc[:11].tolist() == list(map(float, range(0, 11)))
    assert (out.iloc[11:] == 10.0).all()


# ---------------------------------------------------------------------
# edges / wiring
# ---------------------------------------------------------------------
def test_edge_cases():
    high = _walk(n=200, seed=6)
    base = rd_lh_run(high)
    pd.testing.assert_series_equal(rd_lh_run(high, offset=1), base.shift(1))
    assert rd_lh_run(high, fillna=0).isna().sum() == 0
    with pytest.raises(ValueError):
        rd_lh_run(high, fill_method="nope")


def test_nan_mid_series_resets_the_run():
    high = _walk(n=200, seed=6).copy()
    high[100] = np.nan
    out = rd_lh_run(high)
    # a NaN high can never be strictly less than anything, nor can the next
    # bar be strictly less than NaN, so both bar 100 and 101 read 0
    assert out[100] == 0.0
    assert out[101] == 0.0


def test_default_params_in_name():
    out = rd_lh_run(_walk(seed=5))
    assert out.name == "RD_LH_RUN_100"


def test_column_name_and_category():
    out = rd_lh_run(_walk(n=60, seed=1), cap=5)
    assert out.name == "RD_LH_RUN_5"
    assert out.category == "trend"


def test_registered_in_category():
    assert "rd_lh_run" in ta.Category["trend"]


def test_accessor_matches_module_level():
    high = _walk(n=200, seed=9)
    via_module = rd_lh_run(high)
    df = DataFrame({"high": high})
    via_accessor = df.ta.rd_lh_run()
    pd.testing.assert_series_equal(via_module, via_accessor, check_exact=True)
    assert df.ta.rd_lh_run(cap=7).name == "RD_LH_RUN_7"
