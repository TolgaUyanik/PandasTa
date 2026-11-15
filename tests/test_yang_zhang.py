# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.volatility.yang_zhang` -- the Yang & Zhang (2000)
OHLC range volatility estimator, the one of the RANGEVOL trio that also reads
`open` (via the overnight close-to-open return) and so inherits issue #14's
open-quality risk. Measurements (Gate C/D numbers, the open-quality
disclosure) are in docs/RangeVolMeasured.md.

What these pin, in order of how much it would hurt to lose:

* CAUSALITY by future-perturbation: rewrite OHLC from bar `j` onward with
  another walk, demand bars `[0:j]` bit-identical with matching NaN masks,
  over 31 offsets. A look-ahead mutant (`importlib` source read, the prior
  close read one bar into the future instead of one bar into the past,
  `exec`'d in memory) is proved live, then caught.
* CORRECTNESS: a flat-market closed form (open==high==low==close on every
  bar reads exactly 0 -- every log-ratio is ln(1)==0) and an independent
  per-bar loop (manual rolling sample variance, not the module's `.rolling`
  call) against a synthetic walk.
* NON-NEGATIVITY: the combined variance is a sum of a sample variance (>=0
  by construction), k times another sample variance (k in (0, 0.15], so
  still >=0), and (1-k) times a per-bar term proved elsewhere to be >=0
  (`rogers_satchell`'s docstring) -- a clip is present only for float
  safety, pinned to measure how often it actually engages.
* OPEN-QUALITY (issue #14's risk, applied here because this estimator is the
  one that reads `open`): measured on a SYNTHETIC fixture with open forced
  to equal the prior close on a fraction `p` of bars -- YZVOL keeps firing
  (no NaN, no exception) as the overnight variance term degenerates toward
  0, it just leans on the Rogers-Satchell term instead. Real-data open
  quality is NOT measured here (owed, same as #14 itself).
* SCALE-FREE: bit-identical under x8/x64 (every term, including the
  overnight term, is a log-ratio), within tolerance under x10/x3.7, plus
  `0 < fires < n` with > 1 distinct value.
* Wiring: `Category`, the accessor, and the column name `YZVOL_20`.
"""
import importlib
import types

import numpy as np
import pandas as pd
import pytest
from pandas import Series

from .context import pandas_ta as ta
from pandas_ta.volatility.yang_zhang import yang_zhang


def _ohlc(n=1200, seed=11, sigma=0.012, overnight_sigma=0.004, spread_sigma=0.004, tick=0.01, p_flat_open=0.0):
    """Same shape as `garman_klass`/`rogers_satchell`'s fixture, extended
    with `p_flat_open`: the fraction of bars whose overnight move is forced
    to exactly 0 (open == prior close), for the open-quality disclosure."""
    rng = np.random.default_rng(seed)
    overnight = rng.normal(0.0, overnight_sigma, n)
    overnight[rng.random(n) < p_flat_open] = 0.0
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


def test_hand_derived_flat_market_reads_exactly_zero():
    """open == high == low == close == 100 on every bar: every log-ratio in
    every term is ln(1) == 0, so YZVOL == 0 exactly."""
    flat = Series([100.0] * 5)
    out = yang_zhang(flat, flat, flat, flat, length=2)
    assert (out.dropna() == 0.0).all()
    assert out.notna().sum() > 0


def test_matches_an_independent_per_bar_loop():
    """Manual rolling sample variance (ddof=1) over a plain Python window,
    not `.rolling().var()` -- an independent reimplementation of the
    formula, not a re-run of the module's own call."""
    open_, high, low, close = _ohlc(400, seed=3)
    o, h, l, c = open_.values, high.values, low.values, close.values
    length = 20
    out = yang_zhang(open_, high, low, close, length=length)
    k = 0.34 / (1.34 + (length + 1) / (length - 1))
    for t in (100, 250, 399):
        window = range(t - length + 1, t + 1)
        overnight = np.array([np.log(o[i] / c[i - 1]) for i in window])
        openclose = np.array([np.log(c[i] / o[i]) for i in window])
        rs = np.array([np.log(h[i] / c[i]) * np.log(h[i] / o[i]) + np.log(l[i] / c[i]) * np.log(l[i] / o[i])
                       for i in window])
        v_on = overnight.var(ddof=1)
        v_oc = openclose.var(ddof=1)
        variance = max(v_on + k * v_oc + (1 - k) * rs.mean(), 0.0)
        expected = 100 * np.sqrt(variance)
        assert out.iloc[t] == pytest.approx(expected, abs=1e-9)


def test_clip_never_engages_on_valid_data():
    open_, high, low, close = _ohlc()
    length = 20
    out_raw = yang_zhang(open_, high, low, close, length=length)
    # Recompute the pre-clip variance the same way the module does, and
    # confirm the clip is a no-op everywhere it fired.
    o, h, l, c = open_.values, high.values, low.values, close.values
    prev_c = np.r_[np.nan, c[:-1]]
    overnight = pd.Series(np.log(o / prev_c))
    openclose = pd.Series(np.log(c / o))
    rs = pd.Series(np.log(h / c) * np.log(h / o) + np.log(l / c) * np.log(l / o))
    k = 0.34 / (1.34 + (length + 1) / (length - 1))
    variance = overnight.rolling(length).var(ddof=1) + k * openclose.rolling(length).var(ddof=1) \
        + (1 - k) * rs.rolling(length).mean()
    pre_clip_min = variance.dropna().min()
    assert pre_clip_min >= -1e-12
    assert out_raw.notna().sum() == variance.dropna().shape[0]


def test_length_of_one_falls_back_to_default():
    """k's denominator is length-1; a caller-supplied 1 (or 0, or None)
    must not raise ZeroDivisionError -- it falls back to 20, matching
    `gapm`/`corwin_schultz`'s length guards."""
    open_, high, low, close = _ohlc(60, seed=7)
    out1 = yang_zhang(open_, high, low, close, length=1)
    out_default = yang_zhang(open_, high, low, close, length=20)
    assert out1.name == out_default.name == "YZVOL_20"
    pd.testing.assert_series_equal(out1, out_default)


# ---------------------------------------------------------- open-quality


@pytest.mark.parametrize("p", [0.0, 0.5, 0.9])
def test_open_quality_degenerate_overnight_still_fires(p):
    """Issue #14's risk, applied to this estimator: as `open == prior close`
    becomes common, the overnight variance term degenerates toward 0, but
    YZVOL keeps firing (no NaN beyond the usual warm-up, no exception) --
    it leans on the Rogers-Satchell term instead. Measured, not asserted:
    the overnight-flat fraction actually reached inside the rolling window
    tracks `p`."""
    open_, high, low, close = _ohlc(1200, seed=11, p_flat_open=p)
    out = yang_zhang(open_, high, low, close, length=20)
    assert out.iloc[20:].notna().all()
    o, c = open_.values, close.values
    prev_c = np.r_[np.nan, c[:-1]]
    flat_frac = float(np.mean(np.isclose(o[1:], prev_c[1:])))
    if p == 0.0:
        assert flat_frac < 0.01
    elif p == 0.9:
        assert flat_frac > 0.7  # tick rounding can occasionally un-flatten a forced-0 move


# -------------------------------------------------------------- causality


_REAL = importlib.import_module("pandas_ta.volatility.yang_zhang")


def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_yz_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


MUTANT = (
    "prev_close = close.shift(1)",
    "prev_close = close.shift(-1)",
)

OFFSETS = range(60, 1100, 35)  # 30 offsets, past the length=20 warm-up


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
    assert _leaks(yang_zhang) == 0


def test_mutant_is_caught():
    """Measured: caught at 30 of 30 offsets (docs/RangeVolMeasured.md)."""
    mod = _load_mutant(*MUTANT)
    open_, high, low, close = _ohlc()
    assert not mod.yang_zhang(open_, high, low, close).equals(yang_zhang(open_, high, low, close))  # live
    caught = _leaks(mod.yang_zhang)
    assert caught == 30, f"measured catch count moved: {caught} of {len(OFFSETS)} J"
    assert caught > 0, "the mutant was never caught at any J -- it is dead code, not a live bug"


# ------------------------------------------------------------ scale-free


@pytest.mark.parametrize("k", [8.0, 64.0])
def test_power_of_two_scale_is_bit_identical(k):
    open_, high, low, close = _ohlc()
    base = yang_zhang(open_, high, low, close)
    scaled = yang_zhang(open_ * k, high * k, low * k, close * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_other_scales_within_tolerance(k):
    open_, high, low, close = _ohlc()
    base = yang_zhang(open_, high, low, close)
    scaled = yang_zhang(open_ * k, high * k, low * k, close * k)
    assert (base.isna() == scaled.isna()).all()
    assert (base - scaled).abs().max() < 1e-9


def test_fires_and_is_not_constant():
    open_, high, low, close = _ohlc()
    out = yang_zhang(open_, high, low, close)
    assert 0 < out.notna().sum() < len(out)
    assert out.dropna().nunique() > 100


# ---------------------------------------------------------------- wiring


def test_name_registration_and_accessor():
    open_, high, low, close = _ohlc(200)
    df = pd.DataFrame({"open": open_, "high": high, "low": low, "close": close, "volume": 1.0})
    assert "yang_zhang" in ta.Category["volatility"]
    out = df.ta.yang_zhang()
    assert out.name == "YZVOL_20"
    pd.testing.assert_series_equal(out, yang_zhang(open_, high, low, close))
    assert df.ta.yang_zhang(length=10).name == "YZVOL_10"
