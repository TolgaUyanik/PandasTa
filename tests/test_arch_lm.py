# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.statistics.arch_lm` -- Engle's ARCH LM statistic of
one-bar returns over a rolling window, as Kats tsfeatures' `get_het_arch`
computes it with statsmodels `het_arch`. Measurements are in
docs/ArchLmMeasured.md.

What these pin, in order of how much it would hurt to lose:

* CORRECTNESS against the source call: statsmodels
  `het_arch(window, nlags=min(10, length // 5))[0]` at every window of a
  GARCH frame, length 20 and 100, within 1e-11 absolute (at most 4.0e-13
  over four synthetic regimes in docs/measure_arch_lm.py).
  statsmodels is not a CI dependency, so that test skips there; an
  independent `np.linalg.lstsq` loop with an explicit intercept (no module
  code) runs everywhere. Plus a closed form: squared returns that follow
  e_t = 0.5 e_{t-1} + 1e-4 exactly are fitted perfectly, R^2 = 1, so the
  statistic is the row count, length - lags.
* SEMANTICS: over 10 paths, GARCH(1,1) frames read higher than iid ones,
  rising with the ARCH coefficient; fat-tailed iid returns read LOWER than
  normal ones. (How often iid returns exceed the 5% critical value is too
  noisy to pin on 10 paths -- overlapping windows -- and is measured over
  200 paths in docs/measure_arch_lm.py instead.)
* CAUSALITY by future-perturbation over 16 offsets, and a mutant (the write
  index moved one bar earlier, `importlib` source read, `exec`'d in memory)
  proved live and caught at every offset. A bad tick moves exactly the
  bars whose window holds one of its two returns.
* SCALE-FREE: x8/x64 bit-identical, x10/x3.7 within 1e-9, and the column
  fires and is not constant.
* Edge cases (flat, bad prices, short input, length floor, chunk
  boundaries) and wiring (`Category`, the accessor, `ARCHLM_100`).
"""
import importlib
import types

import numpy as np
import pandas as pd
import pytest
from pandas import Series

from .context import pandas_ta as ta

_REAL = importlib.import_module("pandas_ta.statistics.arch_lm")
arch_lm = _REAL.arch_lm

CRIT_5PCT_10DF = 18.307  # chi-squared(10) 95th percentile


def _garch(n=600, seed=0, a=0.1, b=0.85):
    """Closes from GARCH(1,1) returns, unconditional sd 2%."""
    rng = np.random.default_rng(seed)
    z = rng.standard_normal(n)
    omega = 4e-4 * (1 - a - b)
    r = np.empty(n)
    h = 4e-4
    for t in range(n):
        r[t] = np.sqrt(h) * z[t]
        h = omega + a * r[t] ** 2 + b * h
    return Series(100 * np.cumprod(1 + r))


def _iid(n=600, seed=0, dist="normal"):
    rng = np.random.default_rng(seed)
    if dist == "normal":
        r = rng.normal(0.0, 0.02, n)
    else:  # Student t, 3 df, scaled to sd 2%
        r = 0.02 * rng.standard_t(3, n) / np.sqrt(3)
    return Series(100 * np.cumprod(1 + r))


def _loop(close, length):
    """OLS with an explicit intercept by `lstsq`, one window at a time."""
    lags = min(10, length // 5)
    c = close.to_numpy(dtype=float)
    r = c[1:] / c[:-1] - 1
    out = np.full(c.size, np.nan)
    for t in range(length, c.size):
        e = r[t - length:t] ** 2
        y = e[lags:]
        x = np.column_stack([np.ones(y.size)] + [e[lags - j:length - j] for j in range(1, lags + 1)])
        beta = np.linalg.lstsq(x, y, rcond=None)[0]
        resid = y - x @ beta
        out[t] = y.size * (1 - (resid @ resid) / ((y - y.mean()) @ (y - y.mean())))
    return out


# ------------------------------------------------------------ correctness


@pytest.mark.parametrize("length", [20, 100])
def test_matches_statsmodels_the_source_call(length):
    diag = pytest.importorskip("statsmodels.stats.diagnostic")
    close = _garch(500, seed=1)
    out = arch_lm(close, length=length).to_numpy()
    c = close.to_numpy()
    r = c[1:] / c[:-1] - 1
    lags = min(10, length // 5)
    for t in range(length, c.size):
        ref = diag.het_arch(r[t - length:t], nlags=lags, result_object=False)[0]
        assert abs(out[t] - ref) < 1e-11, t
    assert np.isnan(out[:length]).all()


@pytest.mark.parametrize("length", [20, 100])
def test_matches_an_independent_loop(length):
    close = _garch(400, seed=2)
    out = arch_lm(close, length=length).to_numpy()
    ref = _loop(close, length)
    np.testing.assert_allclose(out[length:], ref[length:], rtol=1e-9, atol=1e-10)


def test_a_perfect_fit_reads_the_row_count():
    """e_t = 0.5 e_{t-1} + 1e-4 exactly: the lag-1 regressor fits e_t with
    R^2 = 1, so ARCHLM = (length - lags) * 1. length 20 -> lags 4 -> 16."""
    e = [1e-3]
    for _ in range(40):
        e.append(0.5 * e[-1] + 1e-4)
    r = np.sqrt(e) * np.where(np.arange(len(e)) % 2, 1.0, -1.0)
    close = Series(100 * np.cumprod(1 + np.r_[0.0, r]))
    out = arch_lm(close, length=20).dropna()
    assert len(out) > 0
    np.testing.assert_allclose(out.to_numpy(), 16.0, rtol=1e-9)


# --------------------------------------------------------------- semantics


def _pooled(make, k=10, n=600):
    return np.concatenate([arch_lm(make(n, 500 + i)).dropna().to_numpy() for i in range(k)])


def test_clustered_volatility_reads_higher():
    """Medians over 10 paths x 500 bars (measured): iid normal 8.947,
    GARCH(0.10, 0.85) 12.728, GARCH(0.20, 0.75) 17.985 -- ordered.
    Share above the 5% critical value: 4.2% / 23.6% / 49.1%."""
    normal = _pooled(lambda n, s: _iid(n, s))
    mid = _pooled(lambda n, s: _garch(n, s, 0.10, 0.85))
    high = _pooled(lambda n, s: _garch(n, s, 0.20, 0.75))
    meds = tuple(np.median(v) for v in (normal, mid, high))
    assert meds[0] < meds[1] < meds[2]
    assert meds == pytest.approx((8.9469, 12.7281, 17.9848), abs=1e-3)
    shares = tuple(np.mean(v > CRIT_5PCT_10DF) for v in (normal, mid, high))
    assert shares == pytest.approx((0.0424, 0.2360, 0.4908), abs=1e-4)


def test_fat_tails_read_lower_than_normal():
    """iid Student-t(3) returns read a LOWER median than iid normal ones
    (measured 5.292 vs 8.947 here; pooled 5.182 vs 8.365 over 200 paths in
    docs/measure_arch_lm.py): rare huge squares dominate the window's
    variance of e but do not predict each other. A low reading is not
    evidence of calm."""
    t3 = np.median(_pooled(lambda n, s: _iid(n, s, "t3")))
    normal = np.median(_pooled(lambda n, s: _iid(n, s)))
    assert t3 < normal
    assert t3 == pytest.approx(5.2922, abs=1e-3)


# -------------------------------------------------------------- causality


MUTANT = ("lo = length + start", "lo = length - 1 + start")
OFFSETS = range(130, 600, 30)  # 16 offsets


def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_arch_lm_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


def _leaks(fn):
    close = _garch(seed=11)
    other = _garch(seed=99)
    base = fn(close)
    hits = 0
    for j in OFFSETS:
        p = close.copy()
        p.iloc[j:] = other.iloc[j:].to_numpy() * (close.iloc[j - 1] / other.iloc[j - 1])
        out = fn(p)
        a, b = base.iloc[:j], out.iloc[:j]
        if not (a.isna() == b.isna()).all() or (a[a.notna()] != b[a.notna()]).any():
            hits += 1
    return hits


def test_real_module_never_reads_the_future():
    assert _leaks(arch_lm) == 0


def test_mutant_is_caught():
    mod = _load_mutant(*MUTANT)
    close = _garch(seed=11)
    assert not mod.arch_lm(close).equals(arch_lm(close))  # live
    assert _leaks(mod.arch_lm) == len(OFFSETS)


def test_a_bad_tick_moves_exactly_its_windows():
    """close x1000 at bar 300 changes returns 300 and 301; the bars whose
    100-return window holds either are 300..400. Every other bar is
    bit-identical."""
    close = _garch(seed=4)
    base = arch_lm(close)
    bad = close.copy()
    bad.iloc[300] *= 1e3
    out = arch_lm(bad)
    moved = np.flatnonzero(~((out == base) | (out.isna() & base.isna())).to_numpy())
    assert moved.tolist() == list(range(300, 401))


# ------------------------------------------------------------ scale-free


@pytest.mark.parametrize("k", [8.0, 64.0])
def test_price_scale_is_bit_identical(k):
    close = _garch(seed=4)
    base, scaled = arch_lm(close), arch_lm(close * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_price_scale_within_tolerance(k):
    close = _garch(seed=4)
    base, scaled = arch_lm(close), arch_lm(close * k)
    assert (base.isna() == scaled.isna()).all()
    assert (base - scaled).abs().max() < 1e-9


def test_fires_and_is_not_constant():
    out = arch_lm(_garch(seed=4))
    assert out.notna().sum() == 500  # 600 bars, 100 warm-up
    assert out.dropna().nunique() == 500


# ------------------------------------------------------------- edge cases


def test_flat_prices_are_nan():
    """No price change: every squared return is 0, R^2 is undefined."""
    assert arch_lm(Series([10.0] * 150)).isna().all()


@pytest.mark.parametrize("bad", [np.nan, 0.0, -1.0])
def test_a_bad_close_blanks_its_windows(bad):
    close = _garch(300, seed=1)
    base = arch_lm(close)
    c2 = close.copy()
    c2.iloc[150] = bad
    out = arch_lm(c2)
    assert out.iloc[150:251].isna().all()  # returns 150 and 151 are NaN
    pd.testing.assert_series_equal(out.drop(range(150, 251)), base.drop(range(150, 251)))


def test_short_input_and_length_floor():
    close = _garch(150, seed=1)
    assert arch_lm(close.iloc[:100]) is None  # 100 returns need 101 closes
    assert arch_lm(close, length=9).name == "ARCHLM_100"
    assert arch_lm(close, length=10).notna().sum() == 140


def test_chunk_boundaries_do_not_change_values(monkeypatch):
    close = _garch(seed=4)
    base = arch_lm(close)
    monkeypatch.setattr(_REAL, "CHUNK_CELLS", 7 * 100)
    pd.testing.assert_series_equal(arch_lm(close), base, check_exact=True)


# ---------------------------------------------------------------- wiring


def test_name_registration_and_accessor():
    close = _garch(200, seed=1)
    df = pd.DataFrame({"open": close, "high": close, "low": close, "close": close, "volume": 1.0})
    assert "arch_lm" in ta.Category["statistics"]
    out = df.ta.arch_lm()
    assert out.name == "ARCHLM_100"
    pd.testing.assert_series_equal(out, arch_lm(close))
    assert df.ta.arch_lm(length=50).name == "ARCHLM_50"
