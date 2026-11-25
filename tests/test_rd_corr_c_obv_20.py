# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.volume.rd_corr_c_obv_20` -- rolling Pearson
correlation of close and OBV (issue #168, Reddit tier 4:
rd:algotrading:chnbr1). Measurements are in docs/RdCorrCObv20Measured.md.

What these pin, in order of how much it would hurt to lose:

* CORRECTNESS against the issue's own formula: a construction where close
  is forced strictly monotone with constant volume, so OBV is an exact
  affine function of bar index with close -- correlation must read +1
  (never -1: OBV's sign always matches close's own move direction, so the
  two cannot be driven anti-correlated by construction); an independent
  per-window loop using `np.corrcoef` (never calling the module's rolling
  `.corr` helper) that recomputes OBV from scratch; and the z-score
  equivalence the issue's own parenthetical claims (z-scoring either input
  first must not move the result).
* CAUSALITY by future-perturbation (rewrite close and volume from bar j
  onward, demand bars [0:j] bit-identical) and a look-ahead mutant
  (`importlib` source read, OBV series shifted one bar forward, `exec`'d in
  memory -- never a hand-written copy), proved live and then caught.
* SCALE-FREE: bit-identical under x8/x64 scaling of EACH input separately
  (close alone, then volume alone); within tolerance under x10/x3.7;
  `0 < fires < n` plus non-constant.
* Wiring: `Category`, the accessor, and the column name `RD_CORR_C_OBV_20`.
"""
import importlib
import types

import numpy as np
import pandas as pd
import pytest
from pandas import DataFrame, Series

from .context import pandas_ta as ta
from pandas_ta.volume.obv import obv
from pandas_ta.volume.rd_corr_c_obv_20 import rd_corr_c_obv_20


def _walk(n=1200, seed=11, sigma=0.02):
    rng = np.random.default_rng(seed)
    return Series(100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n))))


def _vol(n=1200, seed=21, lo=100, hi=20000):
    rng = np.random.default_rng(seed)
    return Series(rng.integers(lo, hi, n).astype(float))


# ------------------------------------------------------------ correctness


def test_monotone_close_constant_volume_reads_plus_one():
    """Strictly increasing close + constant volume: OBV's increment is a
    constant positive volume every bar, so OBV is a linear function of bar
    index -- and so, separately, is close (built as `100 + i`). Two
    perfectly linear series correlate at exactly +1."""
    n = 60
    close = Series(100.0 + np.arange(n, dtype=float))
    volume = Series(np.full(n, 500.0))
    out = rd_corr_c_obv_20(close, volume, length=10).dropna()
    assert len(out) > 0
    assert (out - 1.0).abs().max() < 1e-9


def test_matches_an_independent_loop():
    """Re-derives OBV and the rolling correlation independently (plain
    Python signed cumulative sum + `np.corrcoef` per window), never calling
    the module's own helpers."""
    close = _walk(400)
    volume = _vol(400)
    n = 20
    c, v = close.values, volume.values

    signed_vol = np.empty(len(c))
    signed_vol[0] = v[0]  # sign defaults to +1 on the first bar (initial=1)
    for i in range(1, len(c)):
        signed_vol[i] = v[i] if c[i] >= c[i - 1] else -v[i]
    obv_ref = np.cumsum(signed_vol)

    ref = np.full(len(c), np.nan)
    for t in range(n - 1, len(c)):
        window_c = c[t - n + 1:t + 1]
        window_o = obv_ref[t - n + 1:t + 1]
        ref[t] = np.corrcoef(window_c, window_o)[0, 1]

    out = rd_corr_c_obv_20(close, volume, length=n)
    assert (np.isnan(ref) == out.isna().values).all()
    assert np.nanmax(np.abs(out.values - ref)) < 1e-9


def test_zscoring_either_input_first_does_not_move_the_result():
    """The issue's own parenthetical: 'z-scoring does not change a Pearson
    correlation'. Z-score close and OBV with a GLOBAL (whole-series) mean
    and std -- an affine transform with a CONSTANT a and b across the whole
    series, which is the only kind of z-score a Pearson correlation is
    invariant to -- before correlating, and the rolling corr of the
    z-scored pair must equal the rolling corr of the raw pair. (A PER-POINT
    rolling z-score, re-centered on a different trailing window at every
    bar, is a different, non-affine transform and is deliberately NOT what
    this test uses -- it would not read the poster's claim correctly.)"""
    close = _walk(300)
    volume = _vol(300)
    n = 20
    obv_series = obv(close, volume)

    z_close = (close - close.mean()) / close.std()
    z_obv = (obv_series - obv_series.mean()) / obv_series.std()
    zscored_corr = z_close.rolling(n, min_periods=n).corr(z_obv)

    out = rd_corr_c_obv_20(close, volume, length=n)
    diff = (out - zscored_corr).dropna()
    assert len(diff) > 0
    assert diff.abs().max() < 1e-9


def test_bounded_on_minus_one_to_one():
    out = rd_corr_c_obv_20(_walk(500), _vol(500)).dropna()
    assert len(out) > 0
    assert (out.abs() <= 1.0 + 1e-9).all()


# -------------------------------------------------------------- causality

_REAL = importlib.import_module("pandas_ta.volume.rd_corr_c_obv_20")


def _load_mutant():
    old = "out = _rolling_pearson(close, obv_series, length)"
    new = "out = _rolling_pearson(close, obv_series.shift(-1), length)"
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_rd_corr_c_obv_20_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


OFFSETS = range(60, 1100, 65)  # 16 offsets, all past the length=20 warm-up


def _leaks(fn):
    close, volume = _walk(), _vol()
    base = fn(close, volume)
    other_close, other_volume = _walk(seed=99), _vol(seed=199)
    hits = 0
    for j in OFFSETS:
        pc, pv = close.copy(), volume.copy()
        pc.iloc[j:] = other_close.iloc[j:].values
        pv.iloc[j:] = other_volume.iloc[j:].values
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
    assert _leaks(rd_corr_c_obv_20) == 0


def test_mutant_is_caught():
    mod = _load_mutant()
    close, volume = _walk(), _vol()
    assert not mod.rd_corr_c_obv_20(close, volume).equals(
        rd_corr_c_obv_20(close, volume))  # live
    assert _leaks(mod.rd_corr_c_obv_20) == len(OFFSETS)  # caught at every offset tried


# ------------------------------------------------------------ scale-free


@pytest.mark.parametrize("k", [8.0, 64.0])
def test_price_scale_is_bit_identical(k):
    close, volume = _walk(), _vol()
    base, scaled = rd_corr_c_obv_20(close, volume), rd_corr_c_obv_20(close * k, volume)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("k", [8.0, 64.0])
def test_volume_scale_is_bit_identical(k):
    close, volume = _walk(), _vol()
    base, scaled = rd_corr_c_obv_20(close, volume), rd_corr_c_obv_20(close, volume * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_price_scale_within_tolerance(k):
    close, volume = _walk(), _vol()
    base, scaled = rd_corr_c_obv_20(close, volume), rd_corr_c_obv_20(close * k, volume)
    assert (base.isna() == scaled.isna()).all()
    assert (base - scaled).abs().max() < 1e-9


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_volume_scale_within_tolerance(k):
    close, volume = _walk(), _vol()
    base, scaled = rd_corr_c_obv_20(close, volume), rd_corr_c_obv_20(close, volume * k)
    assert (base.isna() == scaled.isna()).all()
    assert (base - scaled).abs().max() < 1e-9


def test_column_is_not_constant():
    out = rd_corr_c_obv_20(_walk(), _vol()).dropna()
    n_total = len(_walk())
    assert 0 < len(out) < n_total
    assert out.nunique() > 100


# ---------------------------------------------------------------- edge cases


def test_short_input_returns_none():
    close = Series([100.0] * 5)
    volume = Series([500.0] * 5)
    assert rd_corr_c_obv_20(close, volume, length=20) is None


def test_mismatched_index_raises():
    close = _walk(50)
    volume = _vol(50)
    volume.index = volume.index + 1
    with pytest.raises(ValueError):
        rd_corr_c_obv_20(close, volume)


def test_offset():
    close, volume = _walk(60), _vol(60)
    out0 = rd_corr_c_obv_20(close, volume, length=10)
    out1 = rd_corr_c_obv_20(close, volume, length=10, offset=1)
    aligned = out0.iloc[:-1]
    shifted = out1.iloc[1:]
    assert pd.isna(out1.iloc[0])
    assert (aligned.reset_index(drop=True).dropna()
            == shifted.reset_index(drop=True).dropna()).all()


# ---------------------------------------------------------------- wiring


def test_name_registration_and_accessor():
    close, volume = _walk(200), _vol(200)
    df = DataFrame({"open": close, "high": close, "low": close,
                    "close": close, "volume": volume})
    assert "rd_corr_c_obv_20" in ta.Category["volume"]
    out = df.ta.rd_corr_c_obv_20()
    assert out.name == "RD_CORR_C_OBV_20"
    pd.testing.assert_series_equal(out, rd_corr_c_obv_20(close, volume))
    assert df.ta.rd_corr_c_obv_20(length=10).name == "RD_CORR_C_OBV_10"
