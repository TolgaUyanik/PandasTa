# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.volume.a101_058` -- Kakushadze's (2016, Wilmott)
Alpha101 `#58` without `IndNeutralize`, per issue #42: a rolling price-volume
correlation, decay-weighted toward its most recent value, then time-series
ranked within its own trailing window, negated. `vwap` is substituted by the
issue's own scale-free proxy `(high + low + close) / 3`. Gate A derivation is
in the module docstring and `docs/A101058Measured.md`. Gate E is pending
(CLAUDE.md, "Owed, not failed").

What these pin, in order of how much it would hurt to lose:

* CAUSALITY by future-perturbation: rewrite every high/low/close/volume bar
  from `j` onward (another synthetic frame), demand bars `[0:j]`
  bit-identical with matching NaN masks, over offsets past the warm-up. A
  `rank_length`-bar look-ahead mutant (`importlib` source read, the final
  write shifted from `result = -ranked` to `result =
  -ranked.shift(-rank_length)`, `exec`'d in memory) is proved live, then
  caught at every offset. (A single-bar lookahead inside the correlation
  step was tried first and rejected: `ts_rank`'s 6-bucket output sometimes
  absorbs a 1-bar perturbation without changing bucket, catching only 11/15
  offsets -- a quantisation artefact of the final rank step, not a causality
  gap. Shifting the whole write index by `rank_length` bars widens the
  affected window enough to be caught every time.)
* CORRECTNESS: a hand-derived 8-bar example at `corr_length=2,
  decay_length=1, rank_length=2` (a 2-point Pearson correlation is always
  exactly +-1, decided by direction alone, and `decay_length=1` is the
  identity -- so the whole chain reduces to a checkable sign/rank sequence),
  plus an independent per-bar loop at the shipped defaults
  (`corr_length=4, decay_length=8, rank_length=6`) built from
  `numpy.corrcoef` and hand-coded dot products, not from pandas' own
  `.rolling().corr()` / `wma`.
* SCALE-FREE: bit-identical under high/low/close x8/x64 AND under volume
  x8/x64 independently (correlation is scale-invariant in either argument),
  within 1e-9 under x10/x3.7, matching NaN masks, plus `0 < fires < n`.
* CARDINALITY: `ts_rank(d, 6)` can only take one of 6 values
  (`1/6 .. 6/6`), so the negated column has at most 6 distinct values by
  construction -- NOT a defect, see docs/A101058Measured.md. The
  not-constant check asserts `nunique > 1`, not a three-digit floor.
* Wiring: `Category`, the accessor, the column name `A101_058_4_8_6`.
"""
import importlib
import types

import numpy as np
import pandas as pd
import pytest
from pandas import Series

from .context import pandas_ta as ta
from pandas_ta.volume.a101_058 import a101_058


def _frame(n=1500, seed=11, sigma=0.015):
    rng = np.random.default_rng(seed)
    close = 100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n)))
    noise = np.abs(rng.normal(0.0, 0.3, n))
    high = close + noise
    low = close - noise
    volume = 1000.0 * np.exp(np.cumsum(rng.normal(0.0, sigma * 1.3, n)))
    idx = pd.RangeIndex(n)
    return (Series(high, index=idx), Series(low, index=idx),
            Series(close, index=idx), Series(volume, index=idx))


# ------------------------------------------------------------ correctness


def test_hand_derived_eight_bars_at_small_windows():
    """high=low=close=T (so typical == T exactly), corr_length=2,
    decay_length=1 (identity -- no smoothing), rank_length=2.

    T = [10, 12, 9, 15, 20, 11, 25, 18]
    V = [100, 90, 150, 60, 200, 30, 300, 400]

    A 2-point Pearson correlation is always exactly +-1 (two points
    determine a line): +1 if T and V move the same direction over the pair,
    -1 if opposite.
      t=1: T 10->12 up,  V 100->90 down  -> opposite -> corr=-1
      t=2: T 12->9  down, V 90->150 up   -> opposite -> corr=-1
      t=3: T 9->15  up,  V 150->60 down  -> opposite -> corr=-1
      t=4: T 15->20 up,  V 60->200 up    -> same     -> corr=+1
      t=5: T 20->11 down, V 200->30 down -> same     -> corr=+1
      t=6: T 11->25 up,  V 30->300 up    -> same     -> corr=+1
      t=7: T 25->18 down, V 300->400 up  -> opposite -> corr=-1
    decay_length=1 is the identity, so decayed == corr_series exactly.
    rank_length=2: ranked[t] = count(decayed[t-1:t+1] <= decayed[t]) / 2.
      t=2..6: each window's current value is the window max (ties count),
              so count=2, rank=1, result=-1.
      t=7: window=(decayed[6]=+1, decayed[7]=-1), current=-1 is the window
           min only, count(<=-1)=1, rank=0.5, result=-0.5.
    Derived by hand from the formula, not by re-running the module.
    """
    T = Series([10.0, 12.0, 9.0, 15.0, 20.0, 11.0, 25.0, 18.0])
    V = Series([100.0, 90.0, 150.0, 60.0, 200.0, 30.0, 300.0, 400.0])
    out = a101_058(T, T, T, V, corr_length=2, decay_length=1, rank_length=2)

    assert out.iloc[0:2].isna().all()
    for t in (2, 3, 4, 5, 6):
        assert out.iloc[t] == pytest.approx(-1.0, abs=1e-12)
    assert out.iloc[7] == pytest.approx(-0.5, abs=1e-12)


def test_matches_an_independent_loop_at_defaults():
    """Spot-checks 3 bars of the shipped defaults (corr_length=4,
    decay_length=8, rank_length=6) against a hand-written loop using
    `numpy.corrcoef` and hand-coded dot products, independent of the
    module's `pandas .rolling().corr()` / `wma` calls."""
    high, low, close, volume = _frame(900, seed=3)
    out = a101_058(high, low, close, volume)

    typical = ((high + low + close) / 3).to_numpy(dtype=float)
    vol = volume.to_numpy(dtype=float)
    corr_length, decay_length, rank_length = 4, 8, 6
    weights = np.arange(1, decay_length + 1, dtype=float)
    total_weight = weights.sum()

    def corr_at(t):
        a = typical[t - corr_length + 1:t + 1]
        b = vol[t - corr_length + 1:t + 1]
        return np.corrcoef(a, b)[0, 1]

    def decayed_at(t):
        vals = np.array([corr_at(t - decay_length + 1 + i) for i in range(decay_length)])
        return np.dot(vals, weights) / total_weight

    def ranked_at(t):
        vals = np.array([decayed_at(t - rank_length + 1 + i) for i in range(rank_length)])
        current = vals[-1]
        return np.count_nonzero(vals <= current) / rank_length

    for t in (300, 500, 899):
        expected = -ranked_at(t)
        assert out.iloc[t] == pytest.approx(expected, rel=1e-9)


def test_insufficient_history_returns_none():
    high, low, close, volume = _frame(10)  # defaults need corr_length+decay_length+rank_length-2 = 16 bars
    assert a101_058(high, low, close, volume) is None


def test_default_name():
    high, low, close, volume = _frame()
    out = a101_058(high, low, close, volume)
    assert out.name == "A101_058_4_8_6"


# -------------------------------------------------------------- causality


_REAL = importlib.import_module("pandas_ta.volume.a101_058")


def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_a101_058_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


MUTANT = (
    "result = -ranked",
    "result = -ranked.shift(-rank_length)",  # a rank_length-bar look-ahead
)

OFFSETS = range(300, 900, 40)  # past the 16-bar warm-up


def _leaks(fn):
    high, low, close, volume = _frame(900)
    other_h, other_l, other_c, other_v = _frame(900, seed=97)
    base = fn(high, low, close, volume)
    hits = 0
    for j in OFFSETS:
        ph, pl, pc, pv = high.copy(), low.copy(), close.copy(), volume.copy()
        ph.iloc[j:] = other_h.iloc[j:].values
        pl.iloc[j:] = other_l.iloc[j:].values
        pc.iloc[j:] = other_c.iloc[j:].values
        pv.iloc[j:] = other_v.iloc[j:].values
        out = fn(ph, pl, pc, pv)
        a, b = base.iloc[:j], out.iloc[:j]
        if not (a.isna() == b.isna()).all():
            hits += 1
            continue
        m = a.notna()
        if (a[m] != b[m]).any():
            hits += 1
    return hits


def test_real_module_never_reads_the_future():
    assert _leaks(a101_058) == 0


def test_lookahead_mutant_is_caught():
    mod = _load_mutant(*MUTANT)
    high, low, close, volume = _frame(900)
    assert not mod.a101_058(high, low, close, volume).equals(a101_058(high, low, close, volume))  # live
    assert _leaks(mod.a101_058) == len(OFFSETS)  # caught, every offset


# ------------------------------------------------------------ scale-free


@pytest.mark.parametrize("k", [8.0, 64.0])
def test_power_of_two_price_scale_is_bit_identical(k):
    high, low, close, volume = _frame(900)
    base = a101_058(high, low, close, volume)
    scaled = a101_058(high * k, low * k, close * k, volume)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("k", [8.0, 64.0])
def test_power_of_two_volume_scale_is_bit_identical(k):
    high, low, close, volume = _frame(900)
    base = a101_058(high, low, close, volume)
    scaled = a101_058(high, low, close, volume * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_other_price_scales_within_tolerance(k):
    high, low, close, volume = _frame(900)
    base = a101_058(high, low, close, volume)
    scaled = a101_058(high * k, low * k, close * k, volume)
    assert (base.isna() == scaled.isna()).all()
    assert (base - scaled).abs().max() < 1e-9


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_other_volume_scales_within_tolerance(k):
    high, low, close, volume = _frame(900)
    base = a101_058(high, low, close, volume)
    scaled = a101_058(high, low, close, volume * k)
    assert (base.isna() == scaled.isna()).all()
    assert (base - scaled).abs().max() < 1e-9


def test_fires_and_is_not_constant():
    high, low, close, volume = _frame()
    out = a101_058(high, low, close, volume)
    fires = int(out.notna().sum())
    assert 0 < fires < len(out)
    # ts_rank(d, 6) can only take one of 6 values (1/6 .. 6/6), so the
    # negated column has at most 6 distinct values by construction -- see
    # docs/A101058Measured.md. "Not constant" means > 1, not a high floor.
    assert out.dropna().nunique() > 1
    assert out.dropna().nunique() <= 6


def test_mismatched_index_raises():
    high, low, close, volume = _frame(900)
    bad_volume = volume.copy()
    bad_volume.index = bad_volume.index + 1
    with pytest.raises(ValueError):
        a101_058(high, low, close, bad_volume)


# ---------------------------------------------------------------- wiring


def test_name_registration_and_accessor():
    high, low, close, volume = _frame(900)
    df = pd.DataFrame({"open": close, "high": high, "low": low,
                        "close": close, "volume": volume})
    assert "a101_058" in ta.Category["volume"]
    out = df.ta.a101_058()
    assert out.name == "A101_058_4_8_6"
    pd.testing.assert_series_equal(out, a101_058(high, low, close, volume))
    renamed = df.ta.a101_058(corr_length=2, decay_length=1, rank_length=2)
    assert renamed.name == "A101_058_2_1_2"
