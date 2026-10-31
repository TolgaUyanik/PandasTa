# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.volatility.volvol` -- the rolling standard deviation
of a rolling volatility series (vol-of-vol), issue #15. Sources: Alpha
Architect "Volatility Anomalies: IVOL and Vol-of-Vol"; Kaufman (2013) ch. 18.
Measurements and the Gate E result are in `docs/VolvolMeasured.md` (Gate E
is run by the launcher after this session, not in this session).

What these tests pin, in order of how much it would hurt to lose them:

* CAUSALITY by future-perturbation: rewrite every bar from `j` onward, demand
  bars `[0:j]` bit-identical with matching NaN masks, over 30 offsets. A
  look-ahead mutant (`importlib` source read, the inner NATR series shifted
  10 bars into the future, `exec`'d in memory -- never a hand-written copy)
  is proved live, then caught at 30 of 30.
* SCALE-FREE: bit-identical under x8 and x64 (NATR is already a price ratio,
  exact under a power-of-two rescale, and a rolling stdev of an exactly-scaled
  series is itself exactly scaled -- sum/mean/sqrt of a power-of-two-scaled
  input stay exact in IEEE float), within 1e-12 under x10 and x3.7 with
  matching NaN masks, and `0 < fires < n` plus a non-constant column so a
  degenerate pass cannot sneak through.
* CORRECTNESS against an independent loop that recomputes NATR from the
  formula text (`100/close * ATR`, ATR an EMA of true range) and then a
  manual rolling sample stdev, not against the module's own `natr` import.
* BOUND: a standard deviation is non-negative by construction.
* Wiring: the accessor, the column name `VOLVOL_20_14`, and its
  `Category['volatility']` entry (wired per issue #15's rules; the Gate E
  ledger row is recorded by a later session once the launcher runs Gate E).
"""
import importlib
import types

import numpy as np
import pandas as pd
import pytest
from pandas import DataFrame, Series

from .context import pandas_ta as ta
from pandas_ta.volatility.volvol import volvol


def _ohlc(n=1200, seed=11, sigma=0.02, tick=None):
    rng = np.random.default_rng(seed)
    close = 100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n)))
    if tick:
        close = np.round(close / tick) * tick
    spread = np.abs(rng.normal(0.0, sigma / 4, n)) * close
    high = close + spread
    low = close - spread
    return Series(high), Series(low), Series(close)


# ------------------------------------------------------------ correctness


def _reference_natr(high, low, close, length=14):
    """Independent re-derivation of `natr`'s default (`mamode='ema'`) path:
    true range (gap-aware), then an SMA-seeded EMA (`span=length,
    adjust=False`, matching `pandas_ta.overlap.ema`'s SMA seed -- NOT Wilder's
    alpha=1/length), then the 100/close scale factor.
    """
    h, l, c = high.values, low.values, close.values
    prev_c = np.roll(c, 1)
    tr = np.maximum(h - l, np.maximum(np.abs(h - prev_c), np.abs(l - prev_c)))
    tr = pd.Series(tr)
    tr.iloc[0] = np.nan
    seeded = tr.copy()
    sma_nth = seeded[0:length].mean()  # skips the leading NaN
    seeded[:length - 1] = np.nan
    seeded.iloc[length - 1] = sma_nth
    atr = seeded.ewm(span=length, adjust=False).mean()
    return 100.0 / close * atr


def test_matches_an_independent_natr_plus_stdev_loop():
    high, low, close = _ohlc(400)
    ref_natr = _reference_natr(high, low, close, length=14)
    ref = ref_natr.rolling(20).std()
    out = volvol(high, low, close, length=20, natr_length=14)
    m = ref.notna() & out.notna()
    assert (ref.isna() == out.isna()).all()
    assert m.sum() > 300
    assert np.nanmax(np.abs(out[m].values - ref[m].values)) < 1e-9


def test_length_zero_and_negative_fall_back_to_default():
    high, low, close = _ohlc(200)
    default = volvol(high, low, close)
    for bad in (0, -5):
        out = volvol(high, low, close, length=bad)
        assert out.name == "VOLVOL_20_14" == default.name
        pd.testing.assert_series_equal(out, default)


def test_non_negative():
    high, low, close = _ohlc(tick=0.05)
    out = volvol(high, low, close).dropna()
    assert (out >= -1e-12).all()


# -------------------------------------------------------------- causality

_REAL = importlib.import_module("pandas_ta.volatility.volvol")


def _load_mutant(old, new, tag):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType(f"_volvol_mutant_{tag}")
    mod.__file__ = _REAL.__file__
    mod.__package__ = "pandas_ta.volatility"  # resolves the module's `from .natr import natr`
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


_SRC_VOL = "vol = natr(high=high, low=low, close=close, length=natr_length, mamode=mamode)"

MUTANTS = {
    "future_natr_10": (_SRC_VOL, f"{_SRC_VOL}.shift(-10)"),
}

OFFSETS = range(60, 1100, 35)  # 30 offsets


def _leaks(fn):
    """Count offsets `j` at which rewriting bars >= j moves any bar < j."""
    high, low, close = _ohlc()
    base = fn(high, low, close)
    o_high, o_low, o_close = _ohlc(seed=99)
    hits = 0
    for j in OFFSETS:
        p_high, p_low, p_close = high.copy(), low.copy(), close.copy()
        p_high.iloc[j:] = o_high.iloc[j:].values
        p_low.iloc[j:] = o_low.iloc[j:].values
        p_close.iloc[j:] = o_close.iloc[j:].values
        out = fn(p_high, p_low, p_close)
        a, b = base.iloc[:j], out.iloc[:j]
        if not (a.isna() == b.isna()).all():
            hits += 1
            continue
        m = a.notna()
        if (a[m] != b[m]).any():
            hits += 1
    return hits


def test_real_module_never_reads_the_future():
    assert _leaks(volvol) == 0


@pytest.mark.parametrize("tag", sorted(MUTANTS))
def test_mutant_is_caught(tag):
    mod = _load_mutant(*MUTANTS[tag], tag)
    high, low, close = _ohlc()
    assert not mod.volvol(high, low, close).equals(volvol(high, low, close))  # live
    assert _leaks(mod.volvol) == len(OFFSETS)                                 # caught, 30 of 30


# ------------------------------------------------------------ scale-free


@pytest.mark.parametrize("k", [8.0, 64.0])
def test_power_of_two_scale_is_bit_identical(k):
    high, low, close = _ohlc(tick=0.05)
    base = volvol(high, low, close)
    scaled = volvol(high * k, low * k, close * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_other_scales_within_tolerance(k):
    high, low, close = _ohlc(tick=0.05)
    base = volvol(high, low, close)
    scaled = volvol(high * k, low * k, close * k)
    assert (base.isna() == scaled.isna()).all()
    assert (base - scaled).abs().max() < 1e-12


def test_column_is_not_constant():
    high, low, close = _ohlc(tick=0.05)
    out = volvol(high, low, close).dropna()
    assert 0 < len(out) < 1200
    assert out.nunique() > 100


# ---------------------------------------------------------------- wiring


def test_name_registration_and_accessor():
    high, low, close = _ohlc(200)
    df = DataFrame({"open": close, "high": high, "low": low,
                    "close": close, "volume": 1.0})
    assert "volvol" in ta.Category["volatility"]
    out = df.ta.volvol()
    assert out.name == "VOLVOL_20_14"
    pd.testing.assert_series_equal(out, volvol(high, low, close))
    assert df.ta.volvol(length=10, natr_length=5).name == "VOLVOL_10_5"
