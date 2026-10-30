# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.volume.amihud` -- Amihud (2002) illiquidity,
normalised as a ratio to its own trailing (expanding) median so the column
is scale-free. Measurements are in docs/LiquidityMeasured.md.

What these pin, in order of how much it would hurt to lose:

* CAUSALITY by future-perturbation: rewrite every bar from `j` onward,
  demand bars `[0:j]` bit-identical, over 31 offsets. A look-ahead mutant
  (`importlib` source read, the return read one bar ahead, `exec`'d in
  memory) is proved live, then caught at 31 of 31.
* SCALE-FREE (the issue's flagged risk -- raw Amihud is NOT scale-free):
  bit-identical under x8 and x64 on BOTH the price axis and the volume
  axis (measured 0.0 max|diff|), within 1e-10 under x10 and x3.7 on both
  (measured <= 7.1e-15). Raw Amihud itself would fail this; the ratio-to-
  own-median normalisation is what makes it pass, and that is the whole
  point of the normalisation decision documented in the module.
* CORRECTNESS: a hand-derived 2-bar value (close 100 -> 110 -> 99, volume
  1000/2000/1500, length=1) gives the ratio 80/67 at the third bar, by
  hand -- no module code reused -- plus an independent per-bar loop.
* The first-valid-bar boundary: the ratio of a value to a one-point
  expanding median of itself is exactly 1.0 -- not a bug, a known
  degenerate case of a history-relative ratio with no history yet.
* Gate C (synthetic): fires on 1179 of 1200 bars (98.25%).
* Wiring: `Category`, the accessor, and the column name `AMIHUD_21`.
"""
import importlib
import types

import numpy as np
import pandas as pd
import pytest
from pandas import Series

from .context import pandas_ta as ta
from pandas_ta.volume.amihud import amihud


def _walk(n=1200, seed=13, sigma=0.02, tick=0.01):
    # Draw order matches docs/measure_liq_proxy.py's `ohlcv()` exactly (close,
    # then an unused spread draw, then volume) so the RNG stream lines up and
    # the fire/distinct-value counts below match the measured numbers in
    # docs/LiquidityMeasured.md bit for bit.
    rng = np.random.default_rng(seed)
    close = 100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n)))
    _unused_spread = np.abs(rng.normal(0.0, 0.004, n))
    if tick:
        close = np.round(close / tick) * tick
    volume = rng.integers(1e5, 1e6, n).astype(float)
    return Series(close), Series(volume)


# ------------------------------------------------------------ correctness


def test_hand_derived_value():
    """close 100 -> 110 -> 99 (ret +0.10, -0.10 exactly), volume
    1000/2000/1500, length=1 (so the rolling mean is a no-op). illiq[1] =
    0.10/(110*2000), illiq[2] = 0.10/(99*1500); their ratio illiq[1]/illiq[2]
    = (99*1500)/(110*2000) = 148500/220000 = 0.675 exactly. baseline at bar
    2 is the plain mean of the two (pandas' 2-point median), so
    AMIHUD[2] = illiq[2] / ((illiq[1]+illiq[2])/2) = 2/(0.675+1) = 80/67 --
    derived by hand, not by re-running the module."""
    close = Series([100.0, 110.0, 99.0])
    volume = Series([1000.0, 2000.0, 1500.0])
    out = amihud(close, volume, length=1)
    assert pd.isna(out.iloc[0])
    assert out.iloc[1] == pytest.approx(1.0, abs=1e-12)  # first valid bar: ratio to itself
    assert out.iloc[2] == pytest.approx(80.0 / 67.0, abs=1e-9)


def test_matches_an_independent_per_bar_loop():
    close, volume = _walk(400, seed=5)
    length = 10
    out = amihud(close, volume, length=length)
    ret = close.pct_change().values
    c, v = close.values, volume.values
    illiq_all = np.abs(ret) / (c * v)
    for t in (50, 120, 250, 399):
        window = illiq_all[t - length + 1: t + 1]
        illiq_t = window.mean()
        history = np.array([np.mean(illiq_all[max(0, i - length + 1): i + 1])
                            for i in range(length, t + 1)])
        baseline = np.median(history)
        expected = illiq_t / baseline
        assert out.iloc[t] == pytest.approx(expected, rel=1e-9)


def test_zero_dollar_volume_is_nan_not_inf():
    close = Series([100.0, 101.0, 102.0, 103.0])
    volume = Series([1000.0, 0.0, 1000.0, 1000.0])
    out = amihud(close, volume, length=1)
    assert pd.isna(out.iloc[1])


# -------------------------------------------------------------- causality


_REAL = importlib.import_module("pandas_ta.volume.amihud")


def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_amihud_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


MUTANT = (
    "ret = close.pct_change()",
    "ret = close.pct_change().shift(-1)",
)

OFFSETS = range(40, 1100, 35)  # 31 offsets


def _leaks(fn):
    close, volume = _walk()
    base = fn(close, volume)
    other_c, other_v = _walk(seed=99)
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
    assert _leaks(amihud) == 0


def test_mutant_is_caught():
    mod = _load_mutant(*MUTANT)
    close, volume = _walk()
    assert not mod.amihud(close, volume).equals(amihud(close, volume))  # live
    assert _leaks(mod.amihud) == len(OFFSETS)  # caught, 31 of 31


# ------------------------------------------------------------ scale-free


@pytest.mark.parametrize("k", [8.0, 64.0])
def test_power_of_two_price_scale_is_bit_identical(k):
    close, volume = _walk()
    base, scaled = amihud(close, volume), amihud(close * k, volume)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("k", [8.0, 64.0])
def test_power_of_two_volume_scale_is_bit_identical(k):
    close, volume = _walk()
    base, scaled = amihud(close, volume), amihud(close, volume * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_other_scales_within_tolerance(k):
    close, volume = _walk()
    base = amihud(close, volume)
    price_scaled = amihud(close * k, volume)
    vol_scaled = amihud(close, volume * k)
    for scaled in (price_scaled, vol_scaled):
        assert (base.isna() == scaled.isna()).all()
        assert (base - scaled).abs().max() < 1e-10


def test_fires_and_is_not_constant():
    close, volume = _walk()
    out = amihud(close, volume)
    assert int(out.notna().sum()) == 1179
    assert out.dropna().nunique() == 1175


# ---------------------------------------------------------------- wiring


def test_name_registration_and_accessor():
    close, volume = _walk(200)
    df = pd.DataFrame({"open": close, "high": close, "low": close,
                       "close": close, "volume": volume})
    assert "amihud" in ta.Category["volume"]
    out = df.ta.amihud()
    assert out.name == "AMIHUD_21"
    pd.testing.assert_series_equal(out, amihud(close, volume))
    assert df.ta.amihud(length=10).name == "AMIHUD_10"
