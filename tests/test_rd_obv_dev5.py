# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.volume.rd_obv_dev5` -- OBV minus its 5-bar SMA, over
a 20-bar average volume (issue #177, Reddit tier 4: rd:algotrading:14rriwv).
Measurements are in docs/RdObvDev5Measured.md.

What these pin, in order of how much it would hurt to lose:

* CORRECTNESS against the issue's own formula: an independent recompute
  that calls this fork's own `obv()` (already ported, already tested) and
  then re-derives both SMAs and the division with plain NumPy over slices
  -- never calling the module's own `sma()` helper for the new arithmetic.
* CAUSALITY by future-perturbation (rewrite close/volume from bar j onward,
  demand bars [0:j] bit-identical) and a look-ahead mutant (`importlib`
  source read, OBV shifted one bar toward the future before the SMAs,
  `exec`'d in memory -- never a hand-written copy), proved live and then
  caught.
* SCALE-FREE: a price-only rescale (any positive factor, since OBV reads
  only the SIGN of close's diff) is bit-identical; a volume-only rescale is
  bit-identical at x8/x64 and within tolerance at x10/x3.7; `0 < fires < n`
  plus non-constant.
* Wiring: `Category`, the accessor, and the column name `RD_OBV_DEV5_5_20`.
"""
import importlib
import types

import numpy as np
import pandas as pd
import pytest
from pandas import DataFrame, Series

from .context import pandas_ta as ta
from pandas_ta.volume.rd_obv_dev5 import rd_obv_dev5
from pandas_ta.volume.obv import obv


def _walk(n=700, seed=11, sigma=0.02):
    rng = np.random.default_rng(seed)
    close = 100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n)))
    volume = rng.uniform(1_000.0, 10_000.0, n)
    return Series(close), Series(volume)


# ------------------------------------------------------------ correctness


def _manual_sma(arr, length):
    out = np.full(len(arr), np.nan)
    for t in range(length - 1, len(arr)):
        window = arr[t - length + 1:t + 1]
        if np.isnan(window).any():
            continue
        out[t] = window.mean()
    return out


def test_matches_an_independent_recompute():
    """Re-derives the new arithmetic independently: calls the fork's own
    (already-tested) `obv()`, then a plain NumPy loop for both SMAs and the
    division -- never the module's own `sma()` helper."""
    close, volume = _walk(700)
    length, vol_length = 5, 20
    obv_series = obv(close, volume).to_numpy()

    obv_sma = _manual_sma(obv_series, length)
    avg_volume = _manual_sma(volume.to_numpy(), vol_length)
    ref = (obv_series - obv_sma) / avg_volume

    out = rd_obv_dev5(close, volume, length=length, vol_length=vol_length)
    assert (np.isnan(ref) == out.isna().values).all()
    m = ~np.isnan(ref)
    assert m.sum() > 0
    assert np.nanmax(np.abs(out.values[m] - ref[m])) < 1e-9


def test_length_one_is_the_obv_minus_itself_over_volume_sma():
    """At `length=1` the 5-bar SMA of OBV degenerates to OBV itself, so the
    numerator is identically 0 everywhere the column fires."""
    close, volume = _walk(300)
    out = rd_obv_dev5(close, volume, length=1, vol_length=20)
    fired = out.dropna()
    assert len(fired) > 0
    assert (fired.to_numpy() == 0.0).all()


# -------------------------------------------------------------- causality

_REAL = importlib.import_module("pandas_ta.volume.rd_obv_dev5")


def _load_mutant():
    old = "obv_series = obv(close, volume)"
    new = "obv_series = obv(close, volume).shift(-1)"
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_rd_obv_dev5_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


OFFSETS = range(400, 650, 30)  # past the max(length, vol_length) warm-up


def _leaks(fn):
    close, volume = _walk()
    base = fn(close, volume)
    hits = 0
    for j in OFFSETS:
        pc, pv = close.copy(), volume.copy()
        pc.iloc[j:] = close.iloc[j:].to_numpy() * 1000.0
        pv.iloc[j:] = volume.iloc[j:].to_numpy() * 1000.0
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
    assert _leaks(rd_obv_dev5) == 0


def test_mutant_is_caught():
    mod = _load_mutant()
    close, volume = _walk()
    assert not mod.rd_obv_dev5(close, volume).equals(
        rd_obv_dev5(close, volume))  # live
    hits = _leaks(mod.rd_obv_dev5)
    assert hits == len(OFFSETS), f"mutant caught at only {hits} of {len(OFFSETS)} offsets"


# ------------------------------------------------------------ scale-free


@pytest.mark.parametrize("k", [8.0, 64.0, 10.0, 3.7])
def test_price_only_scale_is_bit_identical(k):
    """OBV reads only the SIGN of close's diff, so the numerator -- and the
    whole column, since the denominator does not read close at all -- is
    unaffected by ANY positive price rescale, not merely a power-of-two
    one."""
    close, volume = _walk()
    base = rd_obv_dev5(close, volume)
    scaled = rd_obv_dev5(close * k, volume)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("k", [8.0, 64.0])
def test_volume_only_scale_is_bit_identical(k):
    close, volume = _walk()
    base = rd_obv_dev5(close, volume)
    scaled = rd_obv_dev5(close, volume * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_volume_only_scale_within_tolerance(k):
    close, volume = _walk()
    base = rd_obv_dev5(close, volume)
    scaled = rd_obv_dev5(close, volume * k)
    assert (base.isna() == scaled.isna()).all()
    assert (base - scaled).abs().max() < 1e-9


def test_column_is_not_constant():
    close, volume = _walk(900)
    out = rd_obv_dev5(close, volume).dropna()
    assert 0 < len(out) < 900
    assert out.nunique() > 20


# ---------------------------------------------------------------- edge cases


def test_short_input_returns_none():
    close = Series([105.0] * 5)
    volume = Series([1000.0] * 5)
    assert rd_obv_dev5(close, volume) is None


def test_misaligned_index_raises():
    close = Series([100.0] * 30)
    volume = Series([1000.0] * 30, index=range(1, 31))
    with pytest.raises(ValueError):
        rd_obv_dev5(close, volume)


def test_offset():
    close, volume = _walk(700)
    out0 = rd_obv_dev5(close, volume, length=5, vol_length=20)
    out1 = rd_obv_dev5(close, volume, length=5, vol_length=20, offset=1)
    aligned = out0.iloc[:-1]
    shifted = out1.iloc[1:]
    assert pd.isna(out1.iloc[0])
    assert (aligned.reset_index(drop=True).dropna()
            == shifted.reset_index(drop=True).dropna()).all()


# ---------------------------------------------------------------- wiring


def test_name_registration_and_accessor():
    close, volume = _walk(700)
    df = DataFrame({"open": close, "high": close, "low": close,
                    "close": close, "volume": volume})
    assert "rd_obv_dev5" in ta.Category["volume"]
    out = df.ta.rd_obv_dev5()
    assert out.name == "RD_OBV_DEV5_5_20"
    pd.testing.assert_series_equal(out, rd_obv_dev5(close, volume))
    assert df.ta.rd_obv_dev5(length=10, vol_length=50).name == "RD_OBV_DEV5_10_50"
