# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.trend.adxr` -- QuantConnect Lean's Average Directional
Movement Index Rating (Apache-2.0), `AverageDirectionalMovementIndexRating.cs`:

    adxr = (ADX + ADX[period]) / 2

also jesse (MIT) `adxr.py`, the same average. Measurements and the open
Gate E are in `docs/AdxrMeasured.md`.

ADXR is NOT re-derived from DI+/DI-/DX from scratch: it is built on this
fork's own, already-shipped `adx()` (Wilder RMA smoothing, scalar 100),
averaged against its value `length` bars back. Gate A below recomputes that
composition independently of `adxr.py` -- by calling `adx()` directly in the
test and doing the shift-and-average arithmetic itself -- so a bug in
`adxr.py` (wrong shift direction, wrong divisor, wrong column) is caught
without re-litigating `adx()`'s own correctness, which is upstream and out
of scope for this port.

What these tests pin, in order of how much it would hurt to lose them:

* CORRECTNESS against an independent recomposition of the Lean formula from
  the shipped `adx()` output, at two lengths (14 default, 7).
* CAUSALITY by future-perturbation: rewrite OHLC bars from `j` onward,
  demand bars `[0:j]` bit-identical, swept over several offsets. A
  look-ahead mutant (`importlib` source read, the backward `shift(length)`
  flipped to a forward `shift(-length)`, `exec`'d into a fresh in-memory
  module -- never a hand-written copy) is proved live, then caught at every
  offset.
* SCALE-FREE: bit-identical under x8 and x64 OHLC scaling (ADXR is an
  average of two ADX reads, and ADX is itself a ratio that cancels a price
  scale exactly), within tolerance under x10 and x3.7, and `0 < fires < n`
  on a synthetic trending/ranging frame (plus non-constancy, since a
  constant column would also pass `< n`).
* Wiring: `Category`, the `df.ta.adxr` accessor, and the column name
  `ADXR_14`.
"""
import importlib
import types

import numpy as np
import pandas as pd
import pytest
from pandas import DataFrame, Series

from .context import pandas_ta as ta
from pandas_ta.trend.adx import adx
from pandas_ta.trend.adxr import adxr


def _ohlc(n=900, seed=11, sigma=0.015, drift=0.0, start=100.0):
    rng = np.random.default_rng(seed)
    lr = rng.normal(drift, sigma, n)
    c = start * np.exp(np.cumsum(lr))
    h = c * (1.0 + np.abs(rng.normal(0, 0.006, n)))
    l = c * (1.0 - np.abs(rng.normal(0, 0.006, n)))
    return Series(h), Series(l), Series(c)


# ------------------------------------------------------------ correctness


@pytest.mark.parametrize("length", [14, 7])
def test_matches_the_lean_formula_recomposed_from_adx(length):
    h, l, c = _ohlc()
    adx_ = adx(high=h, low=l, close=c, length=length)[f"ADX_{length}"]
    expected = (adx_ + adx_.shift(length)) / 2
    out = adxr(h, l, c, length=length)
    assert (out.isna() == expected.isna()).all()
    m = out.notna()
    assert (out[m] == expected[m]).all()


def test_default_length_is_14():
    h, l, c = _ohlc()
    assert adxr(h, l, c).name == "ADXR_14"
    assert adxr(h, l, c).equals(adxr(h, l, c, length=14))


def test_bounded_zero_to_hundred():
    h, l, c = _ohlc(sigma=0.03)
    out = adxr(h, l, c).dropna()
    assert ((out >= 0.0) & (out <= 100.0 + 1e-9)).all()


# -------------------------------------------------------------- causality

_REAL = importlib.import_module("pandas_ta.trend.adxr")

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
    assert _leaks(adxr) == 0


def _load_shift_direction_mutant():
    src = open(_REAL.__file__, encoding="utf-8").read()
    old = "adxr = (adx_ + adx_.shift(length)) / 2"
    new = "adxr = (adx_ + adx_.shift(-length)) / 2"
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_adxr_mutant_shift_direction")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


def test_shift_direction_mutant_is_caught():
    mod = _load_shift_direction_mutant()
    h, l, c = _ohlc()
    assert not mod.adxr(h, l, c).equals(adxr(h, l, c))  # live: differs from the real module
    assert _leaks(mod.adxr) == len(OFFSETS)             # caught: leaks at every offset


# ------------------------------------------------------------ scale-free


@pytest.mark.parametrize("k", [8.0, 64.0])
def test_power_of_two_scale_is_bit_identical(k):
    h, l, c = _ohlc()
    base = adxr(h, l, c)
    scaled = adxr(h * k, l * k, c * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_other_scales_within_tolerance(k):
    h, l, c = _ohlc()
    base = adxr(h, l, c)
    scaled = adxr(h * k, l * k, c * k)
    assert (base.isna() == scaled.isna()).all()
    assert (base - scaled).abs().max() < 1e-9


def test_fires_on_real_shaped_data_and_is_not_constant():
    h, l, c = _ohlc(n=900, sigma=0.02)
    out = adxr(h, l, c)
    fires = out.notna().sum()
    assert 0 < fires < len(out)
    assert out.dropna().nunique() > 100


def test_too_short_a_series_returns_none():
    h, l, c = _ohlc(n=10)
    assert adxr(h, l, c) is None


# ---------------------------------------------------------------- wiring


def test_name_registration_and_accessor():
    h, l, c = _ohlc(200)
    df = DataFrame({"open": c, "high": h, "low": l, "close": c, "volume": 1.0})
    assert "adxr" in ta.Category["trend"]
    out = df.ta.adxr()
    assert out.name == "ADXR_14"
    pd.testing.assert_series_equal(out, adxr(h, l, c))
    assert df.ta.adxr(length=7).name == "ADXR_7"
