# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.volume.osap_voltrend_60` -- volume trend, catalogued
in the Open Source Asset Pricing (OSAP) SignalDoc as `VolumeTrend`
(Haugen-Baker 1996, t-stat 3.0, "monthly 60 -> daily 60"). Issue #38. Gate A
disclosure (the OLS-slope-is-origin-invariant identity, and the issue's own
direct 60-bar window -- no trading-days-per-month conversion needed, unlike
`osap_mrrev` #37) is in the module docstring and `docs/OsapVoltrend60Measured.md`.
Gate E is pending (CLAUDE.md, "Owed, not failed").

What these pin, in order of how much it would hurt to lose:

* CAUSALITY by future-perturbation: rewrite every volume bar from `j`
  onward, VOLTREND bars `[0:j]` bit-identical, over offsets past the 60-bar
  warm-up. A look-ahead mutant (`importlib` source read, the slope's rolling
  window switched to `center=True`, `exec`'d in memory) is proved live, then
  caught.
* CORRECTNESS: a hand-derived value at `length=3` (every sum done by hand,
  no module code reused) plus an independent per-bar loop at the shipped
  default (`length=60`).
* SCALE-FREE: the column reads no price, so only a volume rescaling can
  reach it -- bit-identical under volume x8/x64, within tolerance under
  x10/x3.7, plus `0 < fires < n`.
* Wiring: `Category`, the accessor, and the column name `VOLTREND_60`.
"""
import importlib
import types

import numpy as np
import pandas as pd
import pytest
from pandas import Series

from .context import pandas_ta as ta
from pandas_ta.volume.osap_voltrend_60 import osap_voltrend_60


def _walk(n=900, seed=11, lo=1e4, hi=1e6):
    """Lognormal-ish positive volume stream."""
    rng = np.random.default_rng(seed)
    return Series(rng.uniform(lo, hi, n))


# ------------------------------------------------------------ correctness


def test_hand_derived_value():
    """length=3, volume = [100, 150, 170, 300].

    t = [-1, 0, 1], w = t / sum(t**2) = [-0.5, 0, 0.5].

    bar2, window [100, 150, 170]:
        slope = -0.5*100 + 0*150 + 0.5*170 = -50 + 85 = 35
        mean  = (100 + 150 + 170) / 3 = 140
        ratio = 35 / 140 = 0.25
    bar3, window [150, 170, 300]:
        slope = -0.5*150 + 0*170 + 0.5*300 = -75 + 150 = 75
        mean  = (150 + 170 + 300) / 3 = 620 / 3
        ratio = 75 * 3 / 620 = 225 / 620 = 45 / 124
    Derived by hand, not by re-running the module.
    """
    volume = Series([100.0, 150.0, 170.0, 300.0])
    out = osap_voltrend_60(volume, length=3)
    assert pd.isna(out.iloc[0])
    assert pd.isna(out.iloc[1])
    assert out.iloc[2] == pytest.approx(0.25, abs=1e-12)
    assert out.iloc[3] == pytest.approx(45.0 / 124.0, abs=1e-12)


def test_matches_an_independent_per_bar_loop_at_defaults():
    volume = _walk(900, seed=5)
    length = 60
    out = osap_voltrend_60(volume)

    v = volume.values
    t = np.arange(length, dtype=float) - (length - 1) / 2.0
    denom = (t * t).sum()
    for bar in (100, 300, 500, 899):
        window = v[bar - length + 1: bar + 1]
        slope = np.dot(t, window) / denom
        expected = slope / window.mean()
        assert out.iloc[bar] == pytest.approx(expected, rel=1e-9)


def test_insufficient_history_returns_none():
    volume = _walk(50)  # default length=60 needs 60 bars
    assert osap_voltrend_60(volume) is None


def test_offset_shifts_the_series():
    volume = _walk(200)
    base = osap_voltrend_60(volume)
    shifted = osap_voltrend_60(volume, offset=1)
    pd.testing.assert_series_equal(shifted, base.shift(1), check_names=False)


def test_fillna_fills_the_warmup_nans():
    volume = _walk(200)
    out = osap_voltrend_60(volume, fillna=0)
    assert not out.isna().any()
    assert (out.iloc[:59] == 0).all()


# -------------------------------------------------------------- causality


_REAL = importlib.import_module("pandas_ta.volume.osap_voltrend_60")


def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_osap_voltrend_60_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


MUTANT = (
    "slope = volume.rolling(length, min_periods=length).apply(_slope, raw=True)",
    "slope = volume.rolling(length, min_periods=length, center=True).apply(_slope, raw=True)",
)

OFFSETS = range(100, 880, 30)  # 26 offsets, all past the 60-bar warm-up


def _leaks(fn):
    volume = _walk(900)
    base = fn(volume)
    other = _walk(900, seed=99)
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
    assert _leaks(osap_voltrend_60) == 0


def test_mutant_is_caught():
    mod = _load_mutant(*MUTANT)
    volume = _walk(900)
    assert not mod.osap_voltrend_60(volume).equals(osap_voltrend_60(volume))  # live
    assert _leaks(mod.osap_voltrend_60) == len(OFFSETS)  # caught


# ------------------------------------------------------------ scale-free


@pytest.mark.parametrize("k", [8.0, 64.0])
def test_power_of_two_volume_scale_is_bit_identical(k):
    volume = _walk(900)
    base, scaled = osap_voltrend_60(volume), osap_voltrend_60(volume * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_other_scales_within_tolerance(k):
    volume = _walk(900)
    base = osap_voltrend_60(volume)
    scaled = osap_voltrend_60(volume * k)
    assert (base.isna() == scaled.isna()).all()
    assert (base - scaled).abs().max() < 1e-9


def test_fires_and_is_not_constant():
    volume = _walk(900)
    out = osap_voltrend_60(volume)
    fires = int(out.notna().sum())
    assert fires == 841  # 900 - 59
    assert 0 < fires < len(out)
    assert out.dropna().nunique() > 100


# ---------------------------------------------------------------- wiring


def test_name_registration_and_accessor():
    volume = _walk(200)
    df = pd.DataFrame({"open": volume, "high": volume, "low": volume,
                       "close": volume, "volume": volume})
    assert "osap_voltrend_60" in ta.Category["volume"]
    out = df.ta.osap_voltrend_60()
    assert out.name == "VOLTREND_60"
    pd.testing.assert_series_equal(out, osap_voltrend_60(volume))
    assert df.ta.osap_voltrend_60(length=10).name == "VOLTREND_10"
