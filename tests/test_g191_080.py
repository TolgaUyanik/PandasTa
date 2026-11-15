# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.volume.g191_080` -- Guotai Junan's (2017, "GTJA191")
alpha `#80`, per issue #64: `(V-V5)/V5*100`, `V5 = DELAY(VOLUME,5)` (volume
5 bars ago, NOT a 5-bar average). Gate A derivation is in the module
docstring and `docs/G191080Measured.md`. Gate E is pending (CLAUDE.md,
"Owed, not failed").

What these pin, in order of how much it would hurt to lose:

* CAUSALITY by future-perturbation: rewrite every volume bar from `j`
  onward (another synthetic series), demand bars `[0:j]` bit-identical with
  matching NaN masks, over offsets past the 5-bar warm-up. One mutant
  (`importlib` source read, `exec`'d in memory, the final write index
  shifted `length` bars into the future) is shown live (differs from the
  real module) then caught at every offset.
* CORRECTNESS: a 7-bar hand-derived example at `length=3`, checked against
  an independent per-bar computation of `100 * (v - v.shift(3)) /
  v.shift(3)`. A second spot check at the shipped default (`length=5`)
  against an independent per-bar loop using plain numpy.
* SCALE-FREE: the column reads no price, so only a volume rescaling can
  reach it -- bit-identical under volume x8/x64 (the `k` cancels inside the
  division algebraically, for ANY `k > 0`), within tolerance under x10/x3.7,
  plus `0 < fires < n` and `nunique > 1`.
* Wiring: `Category`, the accessor, the column name `G191_080_5`.
"""
import importlib
import types

import numpy as np
import pandas as pd
import pytest
from pandas import Series

from .context import pandas_ta as ta
from pandas_ta.volume.g191_080 import g191_080


def _walk(n=900, seed=11, lo=1e4, hi=1e6):
    """Uniform positive volume stream."""
    rng = np.random.default_rng(seed)
    return Series(rng.uniform(lo, hi, n))


# ------------------------------------------------------------ correctness


def test_hand_derived_seven_bars():
    """length=3: G191_080 = 100 * (v - v.shift(3)) / v.shift(3).

    volume = [100, 200, 150, 300, 90, 600, 60]
    bar3: 100*(300-100)/100 = 200.0
    bar4: 100*(90-200)/200  = -55.0
    bar5: 100*(600-150)/150 = 300.0
    bar6: 100*(60-300)/300  = -80.0
    Derived by hand, not by re-running the module.
    """
    volume = Series([100.0, 200.0, 150.0, 300.0, 90.0, 600.0, 60.0])
    out = g191_080(volume, length=3)

    assert out.iloc[:3].isna().all()
    expected = {3: 200.0, 4: -55.0, 5: 300.0, 6: -80.0}
    for t, val in expected.items():
        assert out.iloc[t] == pytest.approx(val, abs=1e-9), f"bar {t}"


def test_matches_an_independent_loop_at_defaults():
    """Spot-checks 3 bars of the shipped default (length=5) against an
    independent per-bar computation using plain numpy slicing, not the
    module's own `.shift()` call."""
    volume = _walk(900, seed=3)
    out = g191_080(volume)
    v = volume.to_numpy(dtype=float)
    length = 5

    def expected_at(t):
        return 100.0 * (v[t] - v[t - length]) / v[t - length]

    for t in (300, 600, 899):
        assert out.iloc[t] == pytest.approx(expected_at(t), rel=1e-9)


def test_insufficient_history_returns_none():
    volume = _walk(5)  # defaults need length + 1 = 6 bars
    assert g191_080(volume) is None


def test_exact_min_length_fires_at_the_warmup_boundary():
    volume = _walk(6)  # exactly length + 1 = 6 bars
    out = g191_080(volume)
    assert out is not None
    assert out.iloc[:5].isna().all()
    assert pd.notna(out.iloc[5])


def test_default_name():
    volume = _walk()
    out = g191_080(volume)
    assert out.name == "G191_080_5"


def test_distinct_lengths_produce_distinct_names_and_values():
    volume = _walk(300)
    out1 = g191_080(volume, length=5)
    out2 = g191_080(volume, length=10)
    assert out1.name != out2.name
    assert out1.name == "G191_080_5"
    assert out2.name == "G191_080_10"
    m = out1.notna() & out2.notna()
    assert (out1[m] != out2[m]).any()


def test_offset_shifts_the_series():
    volume = _walk(200)
    base = g191_080(volume)
    shifted = g191_080(volume, offset=1)
    pd.testing.assert_series_equal(shifted, base.shift(1), check_names=False)


# -------------------------------------------------------------- causality


_REAL = importlib.import_module("pandas_ta.volume.g191_080")


def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_g191_080_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


WRITE_SHIFT_MUTANT = (
    "result = (100.0 * (volume - v5) / v5).replace([np.inf, -np.inf], np.nan)",
    "result = (100.0 * (volume - v5) / v5).replace([np.inf, -np.inf], np.nan).shift(-length)",  # a length-bar look-ahead
)

OFFSETS = range(50, 900, 25)  # past the 5-bar warm-up; a shorter, independent
# sweep from docs/measure_g191_080.py's range(50, 1500, 50) -- both land at
# 0 real leaks / all-offsets mutant leaks, but the "29 of 29" in
# docs/G191080Measured.md is the measure script's sweep, not this one's.


def _leaks(fn):
    volume = _walk(900)
    other = _walk(900, seed=97)
    base = fn(volume)
    hits = 0
    for j in OFFSETS:
        pv = volume.copy()
        pv.iloc[j:] = other.iloc[j:].values
        out = fn(pv)
        a, b = base.iloc[:j], out.iloc[:j]
        if not (a.isna() == b.isna()).all():
            hits += 1
            continue
        m = a.notna()
        if (a[m] != b[m]).any():
            hits += 1
    return hits


def test_real_module_never_reads_the_future():
    assert _leaks(g191_080) == 0


def test_write_shift_mutant_is_caught():
    mod = _load_mutant(*WRITE_SHIFT_MUTANT)
    volume = _walk(900)
    assert not mod.g191_080(volume).equals(g191_080(volume))  # live
    assert _leaks(mod.g191_080) == len(list(OFFSETS))  # caught, every offset


# ------------------------------------------------------------ scale-free


@pytest.mark.parametrize("k", [8.0, 64.0])
def test_power_of_two_volume_scale_is_bit_identical(k):
    volume = _walk()
    base = g191_080(volume)
    scaled = g191_080(volume * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_other_volume_scales_within_tolerance(k):
    volume = _walk()
    base = g191_080(volume)
    scaled = g191_080(volume * k)
    assert (base.isna() == scaled.isna()).all()
    assert (base - scaled).abs().max() < 1e-9


def test_fires_and_is_not_constant():
    volume = _walk()
    out = g191_080(volume)
    fires = int(out.notna().sum())
    assert fires == 895  # 900 - 5
    assert 0 < fires < len(out)
    assert out.dropna().nunique() > 1


# ---------------------------------------------------------------- wiring


def test_name_registration_and_accessor():
    volume = _walk(200)
    df = pd.DataFrame({"open": volume, "high": volume, "low": volume,
                        "close": volume, "volume": volume})
    assert "g191_080" in ta.Category["volume"]
    out = df.ta.g191_080()
    assert out.name == "G191_080_5"
    pd.testing.assert_series_equal(out, g191_080(volume))
    renamed = df.ta.g191_080(length=10)
    assert renamed.name == "G191_080_10"
