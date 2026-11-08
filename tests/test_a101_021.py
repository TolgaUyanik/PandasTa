# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.momentum.a101_021` -- Kakushadze's (2016, Wilmott)
Alpha101 `#21`, per issue #45: a short mean tested against a band built from
a longer mean +- its standard deviation, falling back to a volume-vs-its-
20-bar-average tiebreak inside the band. Gate A derivation (including the
two disclosed ASSUMPTIONs -- `std` at pandas' default `ddof=1`, and `adv(d)`
read as a plain volume rolling mean rather than Kakushadze's literal
dollar-volume definition, both argued from the issue's own prototype and its
own disclosed "unchanged under price x8" invariant) is in the module
docstring and `docs/A101021Measured.md`. Gate E is pending (CLAUDE.md, "Owed,
not failed").

What these pin, in order of how much it would hurt to lose:

* CAUSALITY by future-perturbation: rewrite every close/volume bar from `j`
  onward (another synthetic walk), demand bars `[0:j]` bit-identical with
  matching NaN masks, over offsets past the 20-bar warm-up. The shipped
  mutant (`importlib` source read, `exec`'d in memory) shifts the whole
  write index `adv_length=20` bars into the future: proved live, then
  caught at every offset. Two weaker mutants were tried first and rejected
  as quantisation artefacts of the discretised `{-1, 1}` output (see the
  module docstring and `docs/measure_a101_021.py`): a 1-bar look-ahead on
  `s8` alone caught only 8 of 35 offsets, and a `length=8`-bar write shift
  caught 32 of 35.
* CORRECTNESS: a 9-bar hand-derived example at `length=3, fast_length=1,
  adv_length=2` that hits all three branches of the formula (the
  mean8+std8 branch, the mean2 branch, and both outcomes of the volume
  tiebreak), computed by hand from the formula text, not by re-running the
  module. A second spot-check at the shipped defaults against an
  independent bar-by-bar loop built from plain Python (not pandas'
  `.rolling()`).
* SCALE-FREE: bit-identical under close x8/x64 AND under volume x8/x64
  independently (both branches of the formula compare same-scaled terms;
  power-of-two scaling is exact in IEEE754, so this is a mathematical
  certainty, not just a measurement). Within 1e-9 under x10/x3.7, which on
  this synthetic walk also comes out bit-identical -- measured, not
  assumed, but an empirical, seed-dependent result rather than a general
  guarantee. Matching NaN masks, plus `0 < fires < n` and both regime
  values (-1, 1) present.
* Wiring: `Category`, the accessor, the column name `A101_021_8_2_20`.
"""
import importlib
import types

import numpy as np
import pandas as pd
import pytest
from pandas import Series

from .context import pandas_ta as ta
from pandas_ta.momentum.a101_021 import a101_021


def _walk(n=1500, seed=11, sigma=0.015):
    rng = np.random.default_rng(seed)
    close = 100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n)))
    volume = 1000.0 * np.exp(np.cumsum(rng.normal(0.0, sigma * 1.3, n)))
    idx = pd.RangeIndex(n)
    return Series(close, index=idx), Series(volume, index=idx)


# ------------------------------------------------------------ correctness


def test_hand_derived_nine_bars_all_three_branches():
    """close  = [10, 10, 10, 10, 10, 100, 10, 10, 1]
    volume = [100, 50, 70, 80, 90, 40, 30, 20, 25]
    length=3, fast_length=1, adv_length=2 -> m2 = close[t] (mean of a
    single-bar window is the bar itself).

    t=2,3,4: window=[10,10,10], m8=10, s8=0 (ddof=1 of 3 equal values).
      m8+s8=10 < m2=10? no (equal). m2=10 < m8-s8=10? no (equal). -> tiebreak.
      t=2: adv=mean(v[1],v[2])=mean(50,70)=60, r=70/60=7/6>=1 -> +1
      t=3: adv=mean(v[2],v[3])=mean(70,80)=75, r=80/75=16/15>=1 -> +1
      t=4: adv=mean(v[3],v[4])=mean(80,90)=85, r=90/85=18/17>=1 -> +1
    t=5: window=close[3,4,5]=[10,10,100], m8=40,
      s8=sqrt(((10-40)^2*2+(100-40)^2)/2)=sqrt(5400/2)=sqrt(2700)=51.9615...
      m2=close[5]=100. m8+s8=91.9615 < 100 -> branch1, result=-1.
    t=6: window=close[4,5,6]=[10,100,10], same {10,10,100} set -> m8=40,
      s8=sqrt(2700)=51.9615. m2=close[6]=10. m8+s8=91.9615<10? no.
      m2=10 < m8-s8=-11.9615? no. -> tiebreak.
      adv=mean(v[5],v[6])=mean(40,30)=35, r=30/35=6/7<1 -> -1
    t=7: window=close[5,6,7]=[100,10,10], same set -> m8=40, s8=51.9615.
      m2=close[7]=10. Same as t=6 -> tiebreak.
      adv=mean(v[6],v[7])=mean(30,20)=25, r=20/25=0.8<1 -> -1
    t=8: window=close[6,7,8]=[10,10,1], m8=7,
      s8=sqrt(((10-7)^2*2+(1-7)^2)/2)=sqrt(54/2)=sqrt(27)=5.19615...
      m2=close[8]=1. m8+s8=12.19615<1? no.
      m2=1 < m8-s8=7-5.19615=1.80385? YES -> branch2, result=+1.

    Derived by hand from the formula text, not by re-running the module.
    """
    close = Series([10.0, 10.0, 10.0, 10.0, 10.0, 100.0, 10.0, 10.0, 1.0])
    volume = Series([100.0, 50.0, 70.0, 80.0, 90.0, 40.0, 30.0, 20.0, 25.0])
    out = a101_021(close, volume, length=3, fast_length=1, adv_length=2)

    assert out.iloc[:2].isna().all()
    expected = {2: 1.0, 3: 1.0, 4: 1.0, 5: -1.0, 6: -1.0, 7: -1.0, 8: 1.0}
    for t, val in expected.items():
        assert out.iloc[t] == pytest.approx(val, abs=1e-12), f"bar {t}"


def test_matches_an_independent_loop_at_defaults():
    """Spot-checks 3 bars of the shipped defaults (length=8, fast_length=2,
    adv_length=20) against a hand-written per-bar loop using plain Python
    statistics, independent of the module's `pandas .rolling()` calls."""
    import statistics
    close, volume = _walk(400, seed=3)
    out = a101_021(close, volume)
    c = close.to_numpy(dtype=float)
    v = volume.to_numpy(dtype=float)
    length, fast_length, adv_length = 8, 2, 20

    def expected_at(t):
        w8 = c[t - length + 1:t + 1]
        m8 = statistics.mean(w8)
        s8 = statistics.stdev(w8)  # ddof=1
        m2 = statistics.mean(c[t - fast_length + 1:t + 1])
        adv = statistics.mean(v[t - adv_length + 1:t + 1])
        r = v[t] / adv
        if m8 + s8 < m2:
            return -1.0
        if m2 < m8 - s8:
            return 1.0
        return 1.0 if r >= 1.0 else -1.0

    for t in (100, 250, 399):
        assert out.iloc[t] == pytest.approx(expected_at(t), abs=1e-12)


def test_insufficient_history_returns_none():
    close, volume = _walk(10)  # defaults need max(8,2,20)=20 bars
    assert a101_021(close, volume) is None


def test_default_name():
    close, volume = _walk()
    out = a101_021(close, volume)
    assert out.name == "A101_021_8_2_20"


def test_misaligned_index_raises():
    close, volume = _walk(50)
    volume = volume.copy()
    volume.index = volume.index + 1
    with pytest.raises(ValueError):
        a101_021(close, volume)


# -------------------------------------------------------------- causality


_REAL = importlib.import_module("pandas_ta.momentum.a101_021")


def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_a101_021_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


MUTANT = (
    "result = result.where(mask)",
    "result = result.where(mask).shift(-adv_length)",  # an adv_length-bar look-ahead
)

OFFSETS = range(100, 1500, 40)  # past the 20-bar warm-up


def _leaks(fn):
    close, volume = _walk(1500)
    other_c, other_v = _walk(1500, seed=97)
    base = fn(close, volume)
    hits = 0
    for j in OFFSETS:
        pc, pv = close.copy(), volume.copy()
        pc.iloc[j:] = other_c.iloc[j:].values
        pv.iloc[j:] = other_v.iloc[j:].values
        out = fn(pc, pv)
        a, b = base.iloc[:j], out.iloc[:j]
        if not (a.isna() == b.isna()).all():
            hits += 1
            continue
        m = a.notna()
        if (a[m] != b[m]).any():
            hits += 1
    return hits


def test_real_module_never_reads_the_future():
    assert _leaks(a101_021) == 0


def test_lookahead_mutant_is_caught():
    mod = _load_mutant(*MUTANT)
    close, volume = _walk(1500)
    assert not mod.a101_021(close, volume).equals(a101_021(close, volume))  # live
    assert _leaks(mod.a101_021) == len(list(OFFSETS))  # caught, every offset


def test_weaker_mutants_are_quantisation_limited():
    """Documents why the shipped mutant shifts by the full `adv_length`
    rather than by 1 bar: both weaker mutants are real look-aheads (proved
    live below) but the discretised {-1, 1} output absorbs a small
    perturbation at most offsets, so neither is caught at every offset --
    see `docs/measure_a101_021.py` for the same counts reproduced
    independently."""
    one_bar = _load_mutant(
        "s8 = close.rolling(length).std()",
        "s8 = close.rolling(length).std().shift(-1)",
    )
    length_shift = _load_mutant(
        "result = result.where(mask)",
        "result = result.where(mask).shift(-length)",
    )
    close, volume = _walk(1500)
    assert not one_bar.a101_021(close, volume).equals(a101_021(close, volume))
    assert not length_shift.a101_021(close, volume).equals(a101_021(close, volume))
    assert _leaks(one_bar.a101_021) == 8
    assert _leaks(length_shift.a101_021) == 32


# ------------------------------------------------------------ scale-free


@pytest.mark.parametrize("k", [8.0, 64.0])
def test_power_of_two_price_scale_is_bit_identical(k):
    close, volume = _walk()
    base = a101_021(close, volume)
    scaled = a101_021(close * k, volume)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("k", [8.0, 64.0])
def test_power_of_two_volume_scale_is_bit_identical(k):
    close, volume = _walk()
    base = a101_021(close, volume)
    scaled = a101_021(close, volume * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_other_price_scales_within_tolerance(k):
    close, volume = _walk()
    base = a101_021(close, volume)
    scaled = a101_021(close * k, volume)
    assert (base.isna() == scaled.isna()).all()
    assert (base - scaled).abs().max() < 1e-9


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_other_volume_scales_within_tolerance(k):
    close, volume = _walk()
    base = a101_021(close, volume)
    scaled = a101_021(close, volume * k)
    assert (base.isna() == scaled.isna()).all()
    assert (base - scaled).abs().max() < 1e-9


def test_fires_and_has_both_regimes():
    close, volume = _walk()
    out = a101_021(close, volume)
    fires = int(out.notna().sum())
    assert 0 < fires < len(out)
    assert set(out.dropna().unique()) == {-1.0, 1.0}


# ---------------------------------------------------------------- wiring


def test_name_registration_and_accessor():
    close, volume = _walk(400)
    df = pd.DataFrame({"open": close, "high": close, "low": close,
                        "close": close, "volume": volume})
    assert "a101_021" in ta.Category["momentum"]
    out = df.ta.a101_021()
    assert out.name == "A101_021_8_2_20"
    pd.testing.assert_series_equal(out, a101_021(close, volume))
    assert df.ta.a101_021(length=10).name == "A101_021_10_2_20"
    # all three tunable kwargs forwarded under their own names in one call --
    # the "supertrend failure mode" (CLAUDE.md) hasattr cannot see.
    assert (df.ta.a101_021(length=3, fast_length=1, adv_length=2).name
            == "A101_021_3_1_2")
