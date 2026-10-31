# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.volatility.garman_klass` -- the Garman & Klass (1980)
OHLC range volatility estimator. Measurements (Gate C/D numbers) are in
docs/RangeVolMeasured.md.

What these pin, in order of how much it would hurt to lose:

* CAUSALITY by future-perturbation: rewrite OHLC from bar `j` onward with
  another walk, demand bars `[0:j]` bit-identical with matching NaN masks,
  over 31 offsets. A look-ahead mutant (`importlib` source read, the rolling
  input shifted one bar into the future, `exec`'d in memory -- never a
  hand-written copy) is proved live, then caught.
* CORRECTNESS: two hand-derived closed forms that isolate each of the
  per-bar term's two pieces (a pure-wick bar with open==close, and a
  monotonic bar with no extra wick), plus an independent per-bar loop
  against a synthetic walk.
* NON-NEGATIVITY: the per-bar term is proved (module docstring) to be
  algebraically >= 0 whenever `high >= max(open, close)` and
  `low <= min(open, close)`; a clip is present only for float safety, pinned
  to measure how often it actually engages (expected: never, on valid data).
* SCALE-FREE: bit-identical under x8/x64 (every term is a log-ratio), and
  within tolerance under x10/x3.7, plus `0 < fires < n` with > 1 distinct
  value.
* MALFORMED BAR: masked to NaN, not trusted, and recovers once the window
  clears it.
* Wiring: `Category`, the accessor, and the column name `GKVOL_20`.
"""
import importlib
import types

import numpy as np
import pandas as pd
import pytest
from pandas import Series

from .context import pandas_ta as ta
from pandas_ta.volatility.garman_klass import garman_klass


def _ohlc(n=1200, seed=11, sigma=0.012, overnight_sigma=0.004, spread_sigma=0.004, tick=0.01):
    """A tick-rounded walk: open = prior close moved overnight, close = open
    moved intraday, high/low widened by an independent wick -- same shape as
    `gapm`'s `_walk` and `corwin_schultz`'s `_ohlc` fixtures, extended with a
    wick so high/low genuinely bound open/close."""
    rng = np.random.default_rng(seed)
    overnight = rng.normal(0.0, overnight_sigma, n)
    intraday = rng.normal(0.0, sigma, n)
    open_ = np.empty(n)
    close = np.empty(n)
    cur = 100.0
    for t in range(n):
        o = cur * np.exp(overnight[t])
        c = o * np.exp(intraday[t])
        open_[t], close[t] = o, c
        cur = c
    wick = np.maximum(open_, close) * np.abs(rng.normal(0.0, spread_sigma, n))
    high = np.maximum(open_, close) + wick
    low = np.minimum(open_, close) - wick
    if tick:
        open_ = np.round(open_ / tick) * tick
        close = np.round(close / tick) * tick
        high = np.maximum(np.round(high / tick) * tick, np.maximum(open_, close))
        low = np.minimum(np.round(low / tick) * tick, np.minimum(open_, close))
    return Series(open_), Series(high), Series(low), Series(close)


# ------------------------------------------------------------ correctness


def test_hand_derived_pure_wick_isolates_hl_term():
    """open == close == 1, a pure wick to e / 1/e: the open-close term is
    exactly 0, so GKVOL^2/10000 reduces to 0.5*ln(e/(1/e))^2 = 0.5*2^2 = 2."""
    e = np.e
    out = garman_klass(Series([1.0]), Series([e]), Series([1 / e]), Series([1.0]), length=1)
    assert out.iloc[0] == pytest.approx(100 * np.sqrt(2.0), abs=1e-9)


def test_hand_derived_monotonic_bar_isolates_oc_term():
    """open=1, close=e, high=e, low=1 (no extra wick -- high/low exactly
    equal the bar's own open/close extremes): ln(H/L) = ln(C/O) = 1, so
    GKVOL^2/10000 = 0.5*1 - (2ln2-1)*1 = 1.5 - 2*ln(2)."""
    e = np.e
    out = garman_klass(Series([1.0]), Series([e]), Series([1.0]), Series([e]), length=1)
    expected = 100 * np.sqrt(1.5 - 2 * np.log(2.0))
    assert out.iloc[0] == pytest.approx(expected, abs=1e-9)


def test_matches_an_independent_per_bar_loop():
    open_, high, low, close = _ohlc(400, seed=3)
    o, h, l, c = open_.values, high.values, low.values, close.values
    out = garman_klass(open_, high, low, close, length=5)
    ln2 = np.log(2.0)
    for t in (50, 120, 250, 399):
        window = range(t - 4, t + 1)
        terms = [0.5 * np.log(h[i] / l[i]) ** 2 - (2 * ln2 - 1) * np.log(c[i] / o[i]) ** 2 for i in window]
        expected = 100 * np.sqrt(max(np.mean(terms), 0.0))
        assert out.iloc[t] == pytest.approx(expected, abs=1e-9)


def test_malformed_bar_is_nan_and_recovers():
    """A bad tick (high < close) at one bar masks that bar to NaN; every
    window containing it is NaN, and the column recovers once length=3's
    window has moved entirely past it."""
    open_, high, low, close = _ohlc(60, seed=5)
    high = high.copy()
    high.iloc[30] = low.iloc[30] - 1.0  # high < low < close: malformed
    out = garman_klass(open_, high, low, close, length=3)
    assert pd.isna(out.iloc[30])
    assert pd.isna(out.iloc[31])
    assert pd.isna(out.iloc[32])
    assert pd.notna(out.iloc[33])  # window [31,32,33] no longer touches bar 30


def test_clip_never_engages_on_valid_data():
    """The clip in the module is float-safety only -- on valid OHLC the
    per-bar term is algebraically >= 0 (module docstring). Measured here by
    recomputing the pre-clip variance directly and checking it never went
    negative on this fixture."""
    open_, high, low, close = _ohlc()
    o, h, l, c = open_.values, high.values, low.values, close.values
    ln2 = np.log(2.0)
    per_bar = 0.5 * np.log(h / l) ** 2 - (2 * ln2 - 1) * np.log(c / o) ** 2
    assert (per_bar >= -1e-15).all()


# -------------------------------------------------------------- causality


_REAL = importlib.import_module("pandas_ta.volatility.garman_klass")


def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_gk_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


MUTANT = (
    "variance = per_bar.rolling(length).mean().clip(lower=0.0)",
    "variance = per_bar.shift(-1).rolling(length).mean().clip(lower=0.0)",
)

OFFSETS = range(40, 1100, 35)  # 31 offsets


def _leaks(fn):
    open_, high, low, close = _ohlc()
    base = fn(open_, high, low, close)
    o2, h2, l2, c2 = _ohlc(seed=99)
    hits = 0
    for j in OFFSETS:
        po, ph, pl, pc = open_.copy(), high.copy(), low.copy(), close.copy()
        po.iloc[j:] = o2.iloc[j:].values
        ph.iloc[j:] = h2.iloc[j:].values
        pl.iloc[j:] = l2.iloc[j:].values
        pc.iloc[j:] = c2.iloc[j:].values
        out = fn(po, ph, pl, pc)
        a, b = base.iloc[:j], out.iloc[:j]
        if not (a.isna() == b.isna()).all():
            hits += 1
            continue
        m = a.notna()
        if (a[m] != b[m]).any():
            hits += 1
    return hits


def test_real_module_never_reads_the_future():
    assert _leaks(garman_klass) == 0


def test_mutant_is_caught():
    """Measured: caught at 31 of 31 offsets (docs/RangeVolMeasured.md)."""
    mod = _load_mutant(*MUTANT)
    open_, high, low, close = _ohlc()
    assert not mod.garman_klass(open_, high, low, close).equals(garman_klass(open_, high, low, close))  # live
    caught = _leaks(mod.garman_klass)
    assert caught == 31, f"measured catch count moved: {caught} of {len(OFFSETS)} J"
    assert caught > 0, "the mutant was never caught at any J -- it is dead code, not a live bug"


# ------------------------------------------------------------ scale-free


@pytest.mark.parametrize("k", [8.0, 64.0])
def test_power_of_two_scale_is_bit_identical(k):
    open_, high, low, close = _ohlc()
    base = garman_klass(open_, high, low, close)
    scaled = garman_klass(open_ * k, high * k, low * k, close * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_other_scales_within_tolerance(k):
    open_, high, low, close = _ohlc()
    base = garman_klass(open_, high, low, close)
    scaled = garman_klass(open_ * k, high * k, low * k, close * k)
    assert (base.isna() == scaled.isna()).all()
    assert (base - scaled).abs().max() < 1e-9


def test_fires_and_is_not_constant():
    open_, high, low, close = _ohlc()
    out = garman_klass(open_, high, low, close)
    assert 0 < out.notna().sum() < len(out)
    assert out.dropna().nunique() > 100


# ---------------------------------------------------------------- wiring


def test_name_registration_and_accessor():
    open_, high, low, close = _ohlc(200)
    df = pd.DataFrame({"open": open_, "high": high, "low": low, "close": close, "volume": 1.0})
    assert "garman_klass" in ta.Category["volatility"]
    out = df.ta.garman_klass()
    assert out.name == "GKVOL_20"
    pd.testing.assert_series_equal(out, garman_klass(open_, high, low, close))
    assert df.ta.garman_klass(length=5).name == "GKVOL_5"
