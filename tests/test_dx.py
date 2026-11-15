# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.trend.dx` -- the unsmoothed Directional Movement
Index. Port of jesse (MIT) `dx.py: 100*|DI+ - DI-|/(DI+ + DI-)`. Candidate
`j_dx_14` from the 2026-10-24 library catalog screen round 2
(`docs/issues/screen/ind_screen_r2.py`, `docs/issues/screen/candidates_r2.csv`).
Issue #120 / J-DX-14. Measurements in `docs/DxMeasured.md`.

DX is NOT re-derived from +DI/-DI from scratch: it is read off this fork's
own, already-shipped `adx()` (Wilder RMA smoothing, scalar 100) -- `adx()`
already computes `DMP_<length>`/`DMN_<length>` from the same terms jesse's
`dm_wilder()` calls +DI/-DI, so `dx()` applies the source formula to that
output rather than duplicating the derivation (the same reuse this fork
already uses for `adxr()`). Gate A below recomputes the formula
independently of `dx.py` -- by calling `adx()` directly in the test and
doing the ratio arithmetic itself -- so a bug in `dx.py` (wrong column,
wrong divisor, wrong sign) is caught without re-litigating `adx()`'s own
correctness, which is upstream and out of scope for this port.

What these tests pin, in order of how much it would hurt to lose them:

* CAUSALITY by future-perturbation: rewrite OHLC bars from `j` onward,
  demand bars `[0:j]` bit-identical, swept over several offsets. A
  look-ahead mutant (`importlib` source read, the `DMN_<length>` read
  shifted one bar into the future, `exec`'d into a fresh in-memory module
  -- never a hand-written copy) is proved live, then caught at every offset.
* CORRECTNESS against an independent recomposition of the source formula
  from the shipped `adx()` output, at two lengths (14 default, 7).
* SCALE-FREE: bit-identical under x8 and x64 OHLC scaling (DX is a ratio of
  two ADX-derived terms that cancels a price scale exactly, same as ADX
  itself), within tolerance under x10 and x3.7, and `0 < fires < n` on a
  synthetic trending/ranging frame (plus non-constancy).
* Wiring: `Category`, the `df.ta.dx` accessor, and the column name `DX_14`.
"""
import importlib
import types

import numpy as np
import pandas as pd
import pytest
from pandas import DataFrame, Series

from .context import pandas_ta as ta
from pandas_ta.trend.adx import adx
from pandas_ta.trend.dx import dx


def _ohlc(n=900, seed=11, sigma=0.015, drift=0.0, start=100.0):
    rng = np.random.default_rng(seed)
    lr = rng.normal(drift, sigma, n)
    c = start * np.exp(np.cumsum(lr))
    h = c * (1.0 + np.abs(rng.normal(0, 0.006, n)))
    l = c * (1.0 - np.abs(rng.normal(0, 0.006, n)))
    return Series(h), Series(l), Series(c)


# ------------------------------------------------------------ correctness


@pytest.mark.parametrize("length", [14, 7])
def test_matches_the_source_formula_recomposed_from_adx(length):
    h, l, c = _ohlc()
    adx_df = adx(high=h, low=l, close=c, length=length)
    dmp, dmn = adx_df[f"DMP_{length}"], adx_df[f"DMN_{length}"]
    expected = 100 * (dmp - dmn).abs() / (dmp + dmn)
    out = dx(h, l, c, length=length)
    assert (out.isna() == expected.isna()).all()
    m = out.notna()
    assert (out[m] == expected[m]).all()


def test_default_length_is_14():
    h, l, c = _ohlc()
    assert dx(h, l, c).name == "DX_14"
    assert dx(h, l, c).equals(dx(h, l, c, length=14))


def test_bounded_zero_to_hundred():
    h, l, c = _ohlc(sigma=0.03)
    out = dx(h, l, c).dropna()
    assert ((out >= 0.0) & (out <= 100.0 + 1e-9)).all()


# -------------------------------------------------------------- causality

_REAL = importlib.import_module("pandas_ta.trend.dx")

OFFSETS = range(60, 850, 55)


def _leaks(fn):
    """Count offsets `j` at which rewriting OHLC bars >= j moves any output bar < j."""
    h, l, c = _ohlc()
    base = fn(h, l, c)
    oh, ol, oc = _ohlc(seed=99)
    hits = 0
    for j in OFFSETS:
        ph, pl, pc = h.copy(), l.copy(), c.copy()
        ph.iloc[j:] = oh.iloc[j:].values
        pl.iloc[j:] = ol.iloc[j:].values
        pc.iloc[j:] = oc.iloc[j:].values
        out = fn(ph, pl, pc)
        a, b = base.iloc[:j], out.iloc[:j]
        if not (a.isna() == b.isna()).all():
            hits += 1
            continue
        m = a.notna()
        if (a[m] != b[m]).any():
            hits += 1
    return hits


def test_real_module_never_reads_the_future():
    assert _leaks(dx) == 0


def _load_future_dmn_mutant():
    src = open(_REAL.__file__, encoding="utf-8").read()
    old = 'dmn = adx_df[f"DMN_{length}"]'
    new = 'dmn = adx_df[f"DMN_{length}"].shift(-1)'
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_dx_mutant_future_dmn")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


def test_future_read_mutant_is_caught():
    mod = _load_future_dmn_mutant()
    h, l, c = _ohlc()
    assert not mod.dx(h, l, c).equals(dx(h, l, c))  # live: differs from the real module
    assert _leaks(mod.dx) == len(OFFSETS)           # caught: leaks at every offset


# ------------------------------------------------------------ scale-free


@pytest.mark.parametrize("k", [8.0, 64.0])
def test_power_of_two_scale_is_bit_identical(k):
    h, l, c = _ohlc()
    base = dx(h, l, c)
    scaled = dx(h * k, l * k, c * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_other_scales_within_tolerance(k):
    h, l, c = _ohlc()
    base = dx(h, l, c)
    scaled = dx(h * k, l * k, c * k)
    assert (base.isna() == scaled.isna()).all()
    assert (base - scaled).abs().max() < 1e-9


def test_fires_on_real_shaped_data_and_is_not_constant():
    h, l, c = _ohlc(n=900, sigma=0.02)
    out = dx(h, l, c)
    fires = out.notna().sum()
    assert 0 < fires < len(out)
    assert out.dropna().nunique() > 100


def test_too_short_a_series_returns_none():
    h, l, c = _ohlc(n=10)
    assert dx(h, l, c) is None


# ---------------------------------------------------------------- wiring


def test_name_registration_and_accessor():
    h, l, c = _ohlc(200)
    df = DataFrame({"open": c, "high": h, "low": l, "close": c, "volume": 1.0})
    assert "dx" in ta.Category["trend"]
    out = df.ta.dx()
    assert out.name == "DX_14"
    pd.testing.assert_series_equal(out, dx(h, l, c))
    assert df.ta.dx(length=7).name == "DX_7"
