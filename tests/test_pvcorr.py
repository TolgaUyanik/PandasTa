# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.volume.pvcorr` -- rolling Pearson correlation between
the bar return and the change in log volume (issue #18). Design decisions and
their reasons are in `docs/PvcorrMeasured.md` and the module docstring.

What these tests pin, in order of how much it would hurt to lose:

* CAUSALITY by future-perturbation: rewrite both `close` and `volume` from
  bar `j` onward, demand bars `[0:j]` bit-identical, over several offsets.
  Two look-ahead mutants (`importlib` source read, one shift flipped, `exec`'d
  in memory -- never a hand-written copy) are each proved live, then the
  real module and each mutant's leak counts are measured and asserted exactly.
* SCALE-FREE: bit-identical under x8/x64 scaling of EACH input separately
  (close alone, then volume alone) -- the reason the volume transform is a
  RATIO of volume, not `log(V + k)`, which would not survive this. Within
  tolerance under x10/x3.7. `0 < fires < n` plus non-constant.
* The zero-volume bar is masked to NaN, not `inf`/`-inf` (the issue's own
  "zero-volume bars (log 0)" decision point).
* CORRECTNESS against an independent per-window loop using `np.corrcoef`
  (not pandas' rolling `.corr`), and two constructions where the true
  correlation is known exactly by how the data was built: perfectly
  correlated (+1) and perfectly anti-correlated (-1).
* Wiring: `Category`, the accessor, and the column name `PVCORR_20`.
"""
import importlib
import types

import numpy as np
import pandas as pd
import pytest
from pandas import DataFrame, Series

from .context import pandas_ta as ta
from pandas_ta.volume.pvcorr import pvcorr


def _walk(n=1200, seed=11, sigma=0.02):
    rng = np.random.default_rng(seed)
    return Series(100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n))))


def _vol(n=1200, seed=21, lo=100, hi=20000):
    rng = np.random.default_rng(seed)
    return Series(rng.integers(lo, hi, n).astype(float))


# ------------------------------------------------------------ correctness


def test_perfectly_correlated_reads_plus_one():
    close = _walk(60)
    ret = close.pct_change()
    volume = Series(np.nan, index=close.index)
    volume.iloc[0] = 1000.0
    for i in range(1, len(close)):
        volume.iloc[i] = volume.iloc[i - 1] * np.exp(2.0 * ret.iloc[i])
    out = pvcorr(close, volume, length=10).dropna()
    assert len(out) > 0
    assert (out - 1.0).abs().max() < 1e-9


def test_perfectly_anticorrelated_reads_minus_one():
    close = _walk(60)
    ret = close.pct_change()
    volume = Series(np.nan, index=close.index)
    volume.iloc[0] = 1000.0
    for i in range(1, len(close)):
        volume.iloc[i] = volume.iloc[i - 1] * np.exp(-3.0 * ret.iloc[i])
    out = pvcorr(close, volume, length=10).dropna()
    assert len(out) > 0
    assert (out + 1.0).abs().max() < 1e-9


def test_matches_an_independent_loop():
    """Re-derives the same quantity with `np.corrcoef` per window, never
    calling pandas' rolling `.corr` -- independent of the module's helper."""
    close = _walk(400)
    volume = _vol(400)  # strictly positive: no masking in play here
    n = 20
    c, v = close.values, volume.values
    ref = np.full(len(c), np.nan)
    for t in range(n, len(c)):
        rets = [c[i] / c[i - 1] - 1.0 for i in range(t - n + 1, t + 1)]
        dlogvs = [np.log(v[i] / v[i - 1]) for i in range(t - n + 1, t + 1)]
        ref[t] = np.corrcoef(rets, dlogvs)[0, 1]
    out = pvcorr(close, volume, length=n)
    assert (np.isnan(ref) == out.isna().values).all()
    assert np.nanmax(np.abs(out.values - ref)) < 1e-9


def test_zero_volume_bar_is_masked_not_inf():
    close = _walk(100)
    volume = _vol(100)
    volume.iloc[40] = 0.0  # a halted/untraded bar
    out = pvcorr(close, volume, length=10)
    assert np.isfinite(out.dropna().values).all()


def test_bounded_on_minus_one_to_one():
    out = pvcorr(_walk(500), _vol(500)).dropna()
    assert len(out) > 0
    assert (out.abs() <= 1.0 + 1e-9).all()


# -------------------------------------------------------------- causality

_REAL = importlib.import_module("pandas_ta.volume.pvcorr")


def _load_mutant(old, new, tag):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType(f"_pvcorr_mutant_{tag}")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


MUTANTS = {
    "ret": ("ret = close.pct_change()",
            "ret = close.shift(-1) / close - 1"),
    "vol_prev": ("vol_prev = volume.shift(1)",
                 "vol_prev = volume.shift(-1)"),
}

OFFSETS = range(60, 1100, 65)  # 16 offsets, all past the length=20 warm-up


def _leaks(fn):
    """Count offsets `j` at which rewriting both inputs from `j` onward
    moves any bar before `j`."""
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
    assert _leaks(pvcorr) == 0


@pytest.mark.parametrize("tag", sorted(MUTANTS))
def test_mutant_is_caught(tag):
    mod = _load_mutant(*MUTANTS[tag], tag)
    close, volume = _walk(), _vol()
    assert not mod.pvcorr(close, volume).equals(pvcorr(close, volume))  # live
    assert _leaks(mod.pvcorr) == len(OFFSETS)  # caught at every offset tried


# ------------------------------------------------------------ scale-free


@pytest.mark.parametrize("k", [8.0, 64.0])
def test_price_scale_is_bit_identical(k):
    close, volume = _walk(), _vol()
    base, scaled = pvcorr(close, volume), pvcorr(close * k, volume)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("k", [8.0, 64.0])
def test_volume_scale_is_bit_identical(k):
    close, volume = _walk(), _vol()
    base, scaled = pvcorr(close, volume), pvcorr(close, volume * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_price_scale_within_tolerance(k):
    close, volume = _walk(), _vol()
    base, scaled = pvcorr(close, volume), pvcorr(close * k, volume)
    assert (base.isna() == scaled.isna()).all()
    assert (base - scaled).abs().max() < 1e-9


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_volume_scale_within_tolerance(k):
    close, volume = _walk(), _vol()
    base, scaled = pvcorr(close, volume), pvcorr(close, volume * k)
    assert (base.isna() == scaled.isna()).all()
    assert (base - scaled).abs().max() < 1e-9


def test_column_is_not_constant():
    out = pvcorr(_walk(), _vol()).dropna()
    n_total = len(_walk())
    assert 0 < len(out) < n_total
    assert out.nunique() > 100


# ---------------------------------------------------------------- wiring


def test_name_registration_and_accessor():
    close, volume = _walk(200), _vol(200)
    df = DataFrame({"open": close, "high": close, "low": close,
                    "close": close, "volume": volume})
    assert "pvcorr" in ta.Category["volume"]
    out = df.ta.pvcorr()
    assert out.name == "PVCORR_20"
    pd.testing.assert_series_equal(out, pvcorr(close, volume))
    assert df.ta.pvcorr(length=10).name == "PVCORR_10"
