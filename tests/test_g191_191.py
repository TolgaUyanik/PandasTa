# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.volume.g191_191` -- Guotai Junan's (2017,
"GTJA191") alpha `#191`, per issue #53: `(CORR(MEAN(V,20), L, 5) + (H+L)/2)
- C`, converted to its scale-free form by dividing only the price-difference
term by close (the issue's own candidate record and prototype,
`docs/issues/screen/ind_screen.py:584`, both state this conversion):
`CORR(MEAN(V,20), L, 5) + ((H+L)/2 - C)/C`. Gate A derivation is in the
module docstring and `docs/G191191Measured.md`. Gate E is pending (CLAUDE.md,
"Owed, not failed").

What these pin, in order of how much it would hurt to lose:

* CAUSALITY by future-perturbation: rewrite every OHLCV bar from `j`
  onward (another synthetic frame), demand bars `[0:j]` bit-identical with
  matching NaN masks, over offsets past the 23-bar warm-up. Two mutants
  (`importlib` source read, `exec`'d in memory), each shown live (differs
  from the real module) then caught at every offset: shifting the final
  write index `corr_length=5` bars into the future, and computing
  `MEAN(volume, mean_length)` with `center=True` -- the same look-ahead bug
  class CLAUDE.md documents for `bos`'s `rolling(..., center=True)`
  (`python docs/measure_g191_191.py`).
* CORRECTNESS: a 6-bar hand-derived example at `mean_length=3,
  corr_length=2`, where every rolling correlation is a 2-point Pearson
  correlation (exactly +-1 unless the two `x` values tie), checked against
  an independent per-bar loop written in plain Python/numpy
  (`np.corrcoef`), not pandas' own `.rolling().corr()`.
* SCALE-FREE: Pearson correlation is exactly invariant to a positive
  rescale of either input (the scale cancels between covariance and
  standard deviation), and the price-gap term's own `/close` cancels a
  positive price rescale algebraically too -- so the whole column is
  bit-identical under BOTH close x8/x64 and volume x8/x64 (power-of-two,
  exact in IEEE754), and within float64 tolerance under x10/x3.7. Matching
  NaN masks, plus `0 < fires < n` and `nunique > 1`.
* Wiring: `Category`, the accessor, the column name `G191_191_20_5`.
"""
import importlib
import types

import numpy as np
import pandas as pd
import pytest
from pandas import Series

from .context import pandas_ta as ta
from pandas_ta.volume.g191_191 import g191_191


def _ohlcv(n=1500, seed=11, sigma=0.015, vol_seed=23):
    rng = np.random.default_rng(seed)
    close = 100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n)))
    rng2 = np.random.default_rng(seed + 1)
    spread = np.abs(rng2.normal(0.0, 0.01, n)) * close
    high = close + spread * rng2.uniform(0.2, 1.0, n)
    low = close - spread * rng2.uniform(0.2, 1.0, n)
    rng3 = np.random.default_rng(vol_seed)
    volume = np.abs(rng3.normal(1_000_000.0, 300_000.0, n)) + 1.0
    idx = pd.RangeIndex(n)
    return (Series(high, index=idx), Series(low, index=idx),
            Series(close, index=idx), Series(volume, index=idx))


# ------------------------------------------------------------ correctness


def test_hand_derived_six_bars():
    """high/low/close/volume chosen so every rolling correlation window
    (corr_length=2) is a straight line -- a 2-point Pearson correlation is
    exactly +-1 unless the two MEAN(V,20)-equivalent x-values tie.

    mean_v[t] = MEAN(volume, 3): mean_v[2]=150, mean_v[3]=216.667,
      mean_v[4]=233.333, mean_v[5]=316.667 (masked before t=2).
    corr_term[t] = CORR(mean_v, low, 2), masked before t=3:
      corr_term[3] = corr([150, 216.667], [10.0, 7.5]) = -1  (mean_v up, low down)
      corr_term[4] = corr([216.667, 233.333], [7.5, 11.0]) = +1 (both up)
      corr_term[5] = corr([233.333, 316.667], [11.0, 6.5]) = -1 (mean_v up, low down)
    gap_term[t] = ((high+low)/2 - close)/close:
      [-0.025, 0.0, -0.0227273, 0.0, -0.0208333, 0.0]
    result[t] = corr_term[t] + gap_term[t], valid t>=3:
      result[3] = -1 + 0.0 = -1.0
      result[4] = +1 - 0.0208333 = 0.9791667
      result[5] = -1 + 0.0 = -1.0

    Checked to float precision against the module's actual output below
    (`python docs/measure_g191_191.py` prints the exact values).
    """
    high = Series([10.5, 9.5, 11.5, 8.5, 12.5, 7.5])
    low = Series([9.0, 8.5, 10.0, 7.5, 11.0, 6.5])
    close = Series([10.0, 9.0, 11.0, 8.0, 12.0, 7.0])
    volume = Series([100.0, 200.0, 150.0, 300.0, 250.0, 400.0])

    out = g191_191(high, low, close, volume, mean_length=3, corr_length=2)

    assert out.iloc[:3].isna().all()
    expected = {3: -1.0, 4: 0.9791666666666652, 5: -1.0}
    for t, val in expected.items():
        assert out.iloc[t] == pytest.approx(val, abs=1e-9), f"bar {t}"


def test_matches_an_independent_loop_at_defaults():
    """Spot-checks 3 bars of the shipped defaults (mean_length=20,
    corr_length=5) against an independent per-bar computation using plain
    numpy (`np.mean` over explicit slices, `np.corrcoef`), not pandas'
    `.rolling().mean()` / `.rolling().corr()`."""
    high, low, close, volume = _ohlcv(900, seed=3)
    out = g191_191(high, low, close, volume)
    v = volume.to_numpy(dtype=float)
    l = low.to_numpy(dtype=float)
    h = high.to_numpy(dtype=float)
    c = close.to_numpy(dtype=float)
    mean_length, corr_length = 20, 5

    def expected_at(t):
        mean_v_window = [np.mean(v[s - mean_length + 1:s + 1])
                          for s in range(t - corr_length + 1, t + 1)]
        low_window = l[t - corr_length + 1:t + 1]
        corr_term = np.corrcoef(mean_v_window, low_window)[0, 1]
        gap_term = ((h[t] + l[t]) / 2.0 - c[t]) / c[t]
        return corr_term + gap_term

    for t in (300, 600, 899):
        assert out.iloc[t] == pytest.approx(expected_at(t), rel=1e-9)


def test_insufficient_history_returns_none():
    high, low, close, volume = _ohlcv(23)  # defaults need 20 + 5 - 1 = 24 bars
    assert g191_191(high, low, close, volume) is None


def test_exact_min_length_fires_at_the_warmup_boundary():
    high, low, close, volume = _ohlcv(24)  # exactly 20 + 5 - 1 = 24 bars
    out = g191_191(high, low, close, volume)
    assert out is not None
    assert out.iloc[:23].isna().all()
    assert pd.notna(out.iloc[23])


def test_default_name():
    high, low, close, volume = _ohlcv()
    out = g191_191(high, low, close, volume)
    assert out.name == "G191_191_20_5"


def test_distinct_lengths_produce_distinct_names_and_values():
    high, low, close, volume = _ohlcv(300)
    out1 = g191_191(high, low, close, volume, mean_length=10, corr_length=3)
    out2 = g191_191(high, low, close, volume, mean_length=15, corr_length=4)
    assert out1.name != out2.name
    assert out1.name == "G191_191_10_3"
    assert out2.name == "G191_191_15_4"
    m = out1.notna() & out2.notna()
    assert (out1[m] != out2[m]).any()


# -------------------------------------------------------------- causality


_REAL = importlib.import_module("pandas_ta.volume.g191_191")


def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_g191_191_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


WRITE_SHIFT_MUTANT = (
    "result = result.where(mask).replace([np.inf, -np.inf], np.nan)",
    "result = result.where(mask).replace([np.inf, -np.inf], np.nan).shift(-corr_length)",  # a corr_length-bar look-ahead
)
CENTERED_MEAN_MUTANT = (
    "mean_v = volume.rolling(mean_length).mean()",
    "mean_v = volume.rolling(mean_length, center=True).mean()",  # the `bos` look-ahead bug class
)

OFFSETS = range(150, 1500, 40)  # past the 23-bar warm-up


def _leaks(fn):
    high, low, close, volume = _ohlcv(1500)
    other_h, other_l, other_c, other_v = _ohlcv(1500, seed=97, vol_seed=71)
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
    assert _leaks(g191_191) == 0


def test_write_shift_mutant_is_caught():
    mod = _load_mutant(*WRITE_SHIFT_MUTANT)
    high, low, close, volume = _ohlcv(1500)
    assert not mod.g191_191(high, low, close, volume).equals(g191_191(high, low, close, volume))  # live
    assert _leaks(mod.g191_191) == len(list(OFFSETS))  # caught, every offset


def test_centered_mean_mutant_is_caught():
    mod = _load_mutant(*CENTERED_MEAN_MUTANT)
    high, low, close, volume = _ohlcv(1500)
    assert not mod.g191_191(high, low, close, volume).equals(g191_191(high, low, close, volume))  # live
    assert _leaks(mod.g191_191) == len(list(OFFSETS))  # caught, every offset


# ------------------------------------------------------------ scale-free


@pytest.mark.parametrize("k", [8.0, 64.0])
def test_power_of_two_price_scale_is_bit_identical(k):
    high, low, close, volume = _ohlcv()
    base = g191_191(high, low, close, volume)
    scaled = g191_191(high * k, low * k, close * k, volume)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_other_price_scales_within_tolerance(k):
    high, low, close, volume = _ohlcv()
    base = g191_191(high, low, close, volume)
    scaled = g191_191(high * k, low * k, close * k, volume)
    assert (base.isna() == scaled.isna()).all()
    assert (base - scaled).abs().max() < 1e-9


@pytest.mark.parametrize("k", [8.0, 64.0])
def test_power_of_two_volume_scale_is_bit_identical(k):
    high, low, close, volume = _ohlcv()
    base = g191_191(high, low, close, volume)
    scaled = g191_191(high, low, close, volume * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_other_volume_scales_within_tolerance(k):
    high, low, close, volume = _ohlcv()
    base = g191_191(high, low, close, volume)
    scaled = g191_191(high, low, close, volume * k)
    assert (base.isna() == scaled.isna()).all()
    assert (base - scaled).abs().max() < 1e-9


def test_fires_and_is_not_constant():
    high, low, close, volume = _ohlcv()
    out = g191_191(high, low, close, volume)
    fires = int(out.notna().sum())
    assert 0 < fires < len(out)
    assert out.dropna().nunique() > 1


# ---------------------------------------------------------------- wiring


def test_name_registration_and_accessor():
    high, low, close, volume = _ohlcv(400)
    df = pd.DataFrame({"open": close, "high": high, "low": low, "close": close,
                        "volume": volume})
    assert "g191_191" in ta.Category["volume"]
    out = df.ta.g191_191()
    assert out.name == "G191_191_20_5"
    pd.testing.assert_series_equal(out, g191_191(high, low, close, volume))
    # both tunable kwargs forwarded under their own names in one call --
    # the "supertrend failure mode" (CLAUDE.md) hasattr cannot see.
    renamed = df.ta.g191_191(mean_length=10, corr_length=3)
    assert renamed.name == "G191_191_10_3"
