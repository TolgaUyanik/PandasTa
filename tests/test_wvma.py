# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.volatility.wvma` -- qlib Alpha158's `WVMA$d`: the
coefficient of variation of the volume-weighted absolute return. Issue #34
(A158GAPS). Measurements in `docs/Alpha158Measured.md`.

What these tests pin, in order of how much it would hurt to lose them:

* CAUSALITY by future-perturbation: rewrite every bar from `j` onward,
  demand bars `[0:j]` bit-identical across ALL columns, over 31 offsets.
  Two one-bar look-ahead mutants (`importlib` source read, the std or the
  mean window shifted forward, `exec`'d in memory) are each proved live,
  then caught at 31 of 31.
* SCALE-FREE: the `close/close.shift(1)` return ratio cancels any common
  price-axis factor exactly, so `WVMA` is bit-identical under x8 AND x64
  price rescales (measured 0.0 max diff), and within 1e-9 under x10 and
  x3.7 price rescales. The volume axis is NOT bit-identical even at x8/x64
  -- measured max|diff| 6.66e-16 / 4.44e-16 -- because the `+1e-12` floor
  does not commute exactly with a volume rescale (`k*mean + 1e-12` vs
  `k*(mean + 1e-12/k)`); still comfortably inside the 1e-9 tolerance used
  for all four volume-axis factors. `0 < fires < n` per column.
* CORRECTNESS against an independent per-bar loop built from the formula,
  not from the module, plus a hand-computed 4-bar window.
* Wiring: `Category`, the accessor, and the column names `WVMA_5` ..
  `WVMA_60`.
"""
import importlib
import types

import numpy as np
import pandas as pd
import pytest
from pandas import DataFrame, Series

from .context import pandas_ta as ta
from pandas_ta.volatility.wvma import wvma, DEFAULT_LENGTHS


def _ohlcv(n=1200, seed=31, sigma=0.02, tick=0.01):
    rng = np.random.default_rng(seed)
    close = 100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n)))
    if tick:
        close = np.round(close / tick) * tick
    volume = rng.integers(1e5, 1e6, n).astype(float)
    return Series(close), Series(volume)


# ------------------------------------------------------------ correctness


def test_hand_computed_window():
    close = Series([100.0, 110.0, 99.0, 105.0, 101.0])
    volume = Series([1000.0, 2000.0, 1500.0, 1800.0, 1200.0])
    out = wvma(close, volume, lengths=[4])
    ret = (close / close.shift(1) - 1).abs()
    vwret = (ret * volume).iloc[1:5].to_numpy()  # bars 1..4, the length=4 window
    expected = np.std(vwret, ddof=1) / (np.mean(vwret) + 1e-12)
    assert out["WVMA_4"].iloc[4] == pytest.approx(expected, rel=1e-12)


def test_matches_an_independent_loop():
    close, volume = _ohlcv(400, seed=5)
    length = 20
    c, v = close.values, volume.values
    ret_all = np.abs(c[1:] / c[:-1] - 1)
    vwret_all = np.concatenate([[np.nan], ret_all * v[1:]])
    ref = np.full(len(c), np.nan)
    for t in range(length, len(c)):
        window = vwret_all[t - length + 1: t + 1]
        ref[t] = np.std(window, ddof=1) / (np.mean(window) + 1e-12)
    out = wvma(close, volume, lengths=[length])[f"WVMA_{length}"]
    assert (np.isnan(ref) == out.isna().values).all()
    np.testing.assert_allclose(out.values[length:], ref[length:], rtol=1e-9)


def test_default_lengths_are_the_alpha158_windows():
    assert DEFAULT_LENGTHS == (5, 10, 20, 30, 60)
    close, volume = _ohlcv(200)
    out = wvma(close, volume)
    assert list(out.columns) == [f"WVMA_{d}" for d in (5, 10, 20, 30, 60)]


def test_non_negative():
    close, volume = _ohlcv()
    out = wvma(close, volume).dropna()
    assert (out.to_numpy() >= 0).all()


# -------------------------------------------------------------- causality

_REAL = importlib.import_module("pandas_ta.volatility.wvma")


def _load_mutant(old, new, tag):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType(f"_wvma_mutant_{tag}")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


MUTANTS = {
    "std": ("std = vwret.rolling(length).std()", "std = vwret.shift(-1).rolling(length).std()"),
    "mean": ("mean = vwret.rolling(length).mean()", "mean = vwret.shift(-1).rolling(length).mean()"),
}

OFFSETS = range(40, 1100, 35)  # 31 offsets


def _moved(a, b):
    if not (a.isna() == b.isna()).all().all():
        return True
    m = a.notna()
    return bool(((a[m] != b[m]) & m).to_numpy().any())


def _leaks(fn):
    close, volume = _ohlcv()
    base = fn(close, volume)
    other_c, other_v = _ohlcv(seed=99)
    hits = 0
    for j in OFFSETS:
        for fc, fv in ((other_c.iloc[j:].values, other_v.iloc[j:].values),
                       (close.iloc[j:].values * 1000.0, volume.iloc[j:].values * 1000.0)):
            pc, pv = close.copy(), volume.copy()
            pc.iloc[j:] = fc
            pv.iloc[j:] = fv
            if _moved(base.iloc[:j], fn(pc, pv).iloc[:j]):
                hits += 1
                break
    return hits


def test_real_module_never_reads_the_future():
    assert _leaks(wvma) == 0


@pytest.mark.parametrize("tag", sorted(MUTANTS))
def test_mutant_is_caught(tag):
    mod = _load_mutant(*MUTANTS[tag], tag)
    close, volume = _ohlcv()
    assert not mod.wvma(close, volume).equals(wvma(close, volume))  # live
    assert _leaks(mod.wvma) == len(OFFSETS)  # caught, 31 of 31


# ------------------------------------------------------------ scale-free


@pytest.mark.parametrize("k", [8.0, 64.0])
def test_power_of_two_price_scale_is_bit_identical(k):
    close, volume = _ohlcv()
    base, scaled = wvma(close, volume), wvma(close * k, volume)
    assert (base.isna() == scaled.isna()).all().all()
    m = base.notna()
    assert ((base[m] == scaled[m]) | ~m).to_numpy().all()


@pytest.mark.parametrize("k", [8.0, 64.0, 10.0, 3.7])
def test_volume_scale_within_tolerance(k):
    """NOT bit-identical, unlike the price axis: measured max|diff| 6.66e-16
    at x8 / 4.44e-16 at x64 (floating-point noise from the `+1e-12` floor,
    which does not commute exactly with a volume rescale: `k*mean + 1e-12`
    vs `k*(mean + 1e-12/k)`), well under this 1e-9 bound."""
    close, volume = _ohlcv()
    base, scaled = wvma(close, volume), wvma(close, volume * k)
    assert (base.isna() == scaled.isna()).all().all()
    m = base.notna()
    assert ((base[m] - scaled[m]).abs() < 1e-9).to_numpy()[m.to_numpy()].all()


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_other_price_scales_within_tolerance(k):
    close, volume = _ohlcv()
    base, scaled = wvma(close, volume), wvma(close * k, volume)
    assert (base.isna() == scaled.isna()).all().all()
    m = base.notna()
    assert ((base[m] - scaled[m]).abs() < 1e-9).to_numpy()[m.to_numpy()].all()


def test_fires_between_zero_and_n():
    close, volume = _ohlcv()
    out = wvma(close, volume)
    for col in out.columns:
        m = out[col].notna()
        assert 0 < int(m.sum()) < len(out)


def test_column_is_not_constant():
    close, volume = _ohlcv()
    out = wvma(close, volume)
    for col in out.columns:
        assert out[col].dropna().nunique() > 100


# ---------------------------------------------------------------- wiring


def test_name_registration_and_accessor():
    close, volume = _ohlcv(200)
    df = DataFrame({"open": close, "high": close, "low": close,
                    "close": close, "volume": volume})
    assert "wvma" in ta.Category["volatility"]
    out = df.ta.wvma()
    assert out.name == "WVMA_5-10-20-30-60"
    pd.testing.assert_frame_equal(out, wvma(close, volume))
    assert list(df.ta.wvma(lengths=[7]).columns) == ["WVMA_7"]
