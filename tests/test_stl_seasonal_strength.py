# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.statistics.stl_seasonal_strength` -- Kats tsfeatures'
`get_stl_features` seasonality line, `1 - var(resid) / var(seasonal +
resid)`, from an STL decomposition (period 5) of the rolling window's log
close. Measurements are in docs/StlSeasonalStrengthMeasured.md.

What these pin, in order of how much it would hurt to lose:

* CORRECTNESS: statsmodels' own `STL(window, period=5).fit()` (the exact
  call the screen prototype made) matches this from-scratch numpy STL to
  ~1e-13, over EVERY window of two 400-bar frames at length 100, plus
  lengths 50 and 101 and a non-multiple-of-5 length (53) -- not merely
  "close", because the module exploits that `robust=False` makes every
  step of STL linear in the data and collapses the whole 5-iteration inner
  loop to two fixed matrices (`_build_ops`). This is checked two ways: the
  statsmodels run above (skipped where statsmodels is absent, CI), and,
  runnable everywhere, a direct 5-pass iteration of the recursion
  (`_fixed_point_stl`) against `_build_ops`'s closed-form matrix-power
  shortcut -- that check reuses `_seasonal_op`/`_loess_weights`, the SAME
  operator-construction code `_build_ops` calls, so it validates only the
  closed-form reduction itself, not an independently-implemented LOESS or
  cycle-subseries/low-pass filter; a bug in those would be inherited by
  both sides and would not be caught by this check alone.
* CAUSALITY by future-perturbation over 16 offsets, and a mutant (the
  chunk write index moved one bar earlier) caught at all 16.
* The flat/jitter guard: an exactly flat price and one-ulp float jitter are
  NaN (0/0), but a smooth deterministic drift of any steepness still
  fires -- STL reads log-close LEVELS directly, where a drift is real
  variation, unlike diff1_pacf5/diff2_acf1's guard on returns.
* SCALE-FREE: x8/x64 match to ~1e-13 (not bit-identical -- the matrix
  multiply visits rescaled values in a different magnitude, not an exact
  power-of-two shift), x10/x3.7 within tolerance; the column fires, is not
  constant, and a bad close nulls exactly the windows holding it.
* Edge cases (bad closes including subnormal/infinite, short input, the
  length floor, chunk boundaries, non-multiple-of-5 lengths) and wiring
  (`Category`, the accessor, `STLSEAS_100`).
"""
import importlib
import types

import numpy as np
import pandas as pd
import pytest
from pandas import Series

from .context import pandas_ta as ta

_REAL = importlib.import_module("pandas_ta.statistics.stl_seasonal_strength")
stl_seasonal_strength = _REAL.stl_seasonal_strength


def _ar1(n=600, seed=0, phi=0.0):
    """Closes whose log returns are AR(1) with coefficient phi, sd 2%."""
    rng = np.random.default_rng(seed)
    e = rng.standard_normal(n) * 0.02 * np.sqrt(1 - phi * phi)
    r = np.empty(n)
    prev = 0.0
    for t in range(n):
        prev = phi * prev + e[t]
        r[t] = prev
    return Series(100 * np.exp(np.cumsum(r)))


def _fixed_point_stl(logc_window):
    """Cross-check of `_build_ops`'s closed-form shortcut ONLY -- not an
    independent check of the LOESS/cycle-subseries/low-pass math, since it
    calls `_seasonal_op` and `_loess_weights`, the SAME operator-
    construction code `_build_ops` itself uses to build `a`/`b`. What this
    DOES check: that the STL inner loop really is the fixed-point
    recursion `T_m = A@Y + B@T_(m-1)` `_build_ops` claims, by running it
    five times by direct iteration from T_0 = 0 rather than via the
    closed-form `coefs[-1]`/`coefs[-2]` matrix-power summation the module
    takes. A bug in `_seasonal_op`/`_loess_weights` themselves would be
    inherited by both sides and would not be caught here -- that part is
    covered only by the statsmodels oracle above (skipped in CI). Returns
    (trend, seasonal)."""
    n = len(logc_window)
    seasonal_op = _REAL._seasonal_op(n)
    trend_loess_op = _REAL._loess_weights(n, np.arange(n), np.arange(n), _REAL.TREND, degree=1)
    t = np.zeros(n)
    s = None
    for _ in range(_REAL.INNER_ITER):
        s = seasonal_op @ (logc_window - t)
        t = trend_loess_op @ (logc_window - s)
    return t, s


# ------------------------------------------------------------ correctness


def test_matches_a_hand_run_fixed_point_recursion():
    """No closed-form matrix powers, no statsmodels: runs everywhere,
    including CI. Checks `_build_ops`'s matrix-power shortcut against a
    direct 5-pass iteration of the same recursion -- see `_fixed_point_stl`
    for exactly what this does and does not cover (it shares
    `_seasonal_op`/`_loess_weights` with `_build_ops`, so it is not an
    independent check of the LOESS/cycle-subseries/low-pass math itself)."""
    close = _ar1(300, seed=2, phi=-0.2)
    logc = np.log(close.to_numpy())
    out = stl_seasonal_strength(close, length=100).to_numpy()
    for t in (99, 150, 220, 299):
        w = logc[t - 99:t + 1]
        trend, seasonal = _fixed_point_stl(w)
        resid = w - trend - seasonal
        ref = 1 - resid.var() / (seasonal + resid).var()
        assert out[t] == pytest.approx(ref, abs=1e-12)


@pytest.mark.parametrize("length", [50, 100, 101])
def test_matches_statsmodels_stl(length):
    """statsmodels' `STL(window, period=5).fit()` -- the exact call the
    screen prototype made -- checked on EVERY window of a 400-bar AR(1)
    frame (301 fits, ~0.15s): max abs diff ~1e-13 at every length tried,
    including 101 (not a multiple of 5)."""
    stl = pytest.importorskip("statsmodels.tsa.seasonal").STL
    close = _ar1(400, seed=1, phi=0.2)
    out = stl_seasonal_strength(close, length=length).to_numpy()
    logc = np.log(close.to_numpy())
    maxdiff = 0.0
    for t in range(length - 1, close.size):
        w = logc[t - length + 1:t + 1]
        r = stl(w, period=5).fit()
        e = r.resid
        ref = 1 - np.var(e) / np.var(r.seasonal + e)
        maxdiff = max(maxdiff, abs(out[t] - ref))
    assert maxdiff < 1e-9
    assert np.isnan(out[:length - 1]).all()


def test_a_length_not_a_multiple_of_5_still_matches():
    """length=53: subseries lengths differ by one (11,11,11,10,10),
    exercising the general (not evenly-divisible) interleaving in
    `_cycle_subseries_op`. Checked against statsmodels on a handful of
    windows (393 bars = CI-cheap)."""
    stl = pytest.importorskip("statsmodels.tsa.seasonal").STL
    close = _ar1(200, seed=3, phi=0.1)
    out = stl_seasonal_strength(close, length=53).to_numpy()
    logc = np.log(close.to_numpy())
    for t in range(52, 200, 7):
        w = logc[t - 52:t + 1]
        r = stl(w, period=5).fit()
        e = r.resid
        ref = 1 - np.var(e) / np.var(r.seasonal + e)
        assert out[t] == pytest.approx(ref, abs=1e-9)


# ------------------------------------------------------- the flat/jitter guard


def test_flat_prices_are_nan():
    assert stl_seasonal_strength(Series([10.0] * 150)).isna().all()


def test_one_ulp_jitter_is_nan():
    rng = np.random.default_rng(0)
    c = np.full(300, 10.0)
    c[rng.random(300) < 0.5] = np.nextafter(10.0, 20.0)
    assert stl_seasonal_strength(Series(c)).isna().all()


@pytest.mark.parametrize("g", [1e-2, 1e-4, 1e-7, 1e-8, 1e-10])
def test_a_smooth_drift_still_fires(g):
    """Unlike diff1_pacf5/diff2_acf1 (guarded on RETURNS, where a smooth
    drift is exactly constant), this reads log-close LEVELS, where a
    drift's values genuinely vary: every drift steepness fires, with
    ordinary-looking values (measured in
    docs/measure_stl_seasonal_strength.py: range ~[0.17, 0.38])."""
    out = stl_seasonal_strength(Series(100 * (1 + g) ** np.arange(300.0)))
    assert out.iloc[99:].notna().all()
    assert out.iloc[99:].between(-1, 2).all()  # sanity: not numerically exploded


# -------------------------------------------------------------- causality


MUTANT = ("lo = length - 1 + start", "lo = length - 2 + start")
OFFSETS = range(130, 600, 30)  # 16 offsets


def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_stl_seasonal_strength_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


def _leaks(fn):
    close = _ar1(seed=11)
    other = _ar1(seed=99)
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
    assert _leaks(stl_seasonal_strength) == 0


def test_mutant_is_caught():
    mod = _load_mutant(*MUTANT)
    close = _ar1(seed=11)
    assert not mod.stl_seasonal_strength(close).equals(stl_seasonal_strength(close))  # live
    assert _leaks(mod.stl_seasonal_strength) == len(OFFSETS)


def test_a_bad_close_nulls_exactly_its_windows():
    """close -> NaN at bar 300 (window width 100): every window holding it,
    bars 300..399, is NaN; every other bar is bit-identical."""
    close = _ar1(seed=4)
    base = stl_seasonal_strength(close)
    bad = close.copy()
    bad.iloc[300] = np.nan
    out = stl_seasonal_strength(bad)
    moved = np.flatnonzero(~((out == base) | (out.isna() & base.isna())).to_numpy())
    assert moved.tolist() == list(range(300, 400))


# ------------------------------------------------------------ scale-free


@pytest.mark.parametrize("k", [8.0, 64.0])
def test_price_scale_is_bit_identical(k):
    """STL reads `log(close / the window's own first close)`, not
    `log(close)` directly: under a power-of-two rescale the numerator and
    denominator are both multiplied by an exactly-representable factor, so
    the ratio -- and everything downstream, fed the identical bit pattern
    -- is bit-identical (same device as kpss.py)."""
    close = _ar1(seed=4)
    base, scaled = stl_seasonal_strength(close), stl_seasonal_strength(close * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_price_scale_within_tolerance(k):
    """Not a power of two, so not bit-exact, but within tight tolerance."""
    close = _ar1(seed=4)
    base, scaled = stl_seasonal_strength(close), stl_seasonal_strength(close * k)
    assert (base.isna() == scaled.isna()).all()
    assert (base - scaled).abs().max() < 1e-10


def test_fires_and_is_not_constant():
    out = stl_seasonal_strength(_ar1(seed=4))
    assert out.notna().sum() > 0
    assert out.notna().sum() < 600  # 0 < fires < n
    assert out.dropna().nunique() > 1


# ------------------------------------------------------------- edge cases


@pytest.mark.parametrize("bad", [np.nan, np.inf, 0.0, -1.0, 1e-310])
def test_a_bad_close_blanks_its_windows(bad):
    close = _ar1(300, seed=1)
    base = stl_seasonal_strength(close)
    c2 = close.copy()
    c2.iloc[150] = bad
    out = stl_seasonal_strength(c2)
    assert out.iloc[150:250].isna().all()
    pd.testing.assert_series_equal(out.drop(range(150, 250)), base.drop(range(150, 250)))


def test_short_input_and_length_floor():
    close = _ar1(150, seed=1)
    assert stl_seasonal_strength(close.iloc[:99]) is None  # 100 closes needed (default length)
    assert stl_seasonal_strength(close.iloc[:100]).notna().sum() == 1
    assert stl_seasonal_strength(close, length=49).name == "STLSEAS_100"  # below floor: falls back
    assert stl_seasonal_strength(close.iloc[:50], length=50).notna().sum() == 1


def test_chunk_boundaries_do_not_change_values(monkeypatch):
    """Not bit-exact (unlike diff1_pacf5's equivalent test): each chunk's
    rows go through a matrix multiply, and BLAS's summation order can
    differ by a handful of chunk-size-dependent ULPs -- measured max abs
    diff ~1e-15 in docs/measure_stl_seasonal_strength.py, nowhere near
    1e-9 (Gate D's own x10/x3.7 tolerance)."""
    close = _ar1(seed=4)
    base = stl_seasonal_strength(close)
    monkeypatch.setattr(_REAL, "CHUNK_CELLS", 7 * 100)
    out = stl_seasonal_strength(close)
    assert (out.isna() == base.isna()).all()
    assert (out - base).abs().max() < 1e-9


def test_build_ops_is_cached_per_length():
    stl_seasonal_strength(_ar1(150, seed=1), length=50)
    assert 50 in _REAL._OP_CACHE
    first = _REAL._OP_CACHE[50]
    stl_seasonal_strength(_ar1(150, seed=2), length=50)
    assert _REAL._OP_CACHE[50] is first  # same objects, not recomputed


# ---------------------------------------------------------------- wiring


def test_name_registration_and_accessor():
    close = _ar1(200, seed=1)
    df = pd.DataFrame({"open": close, "high": close, "low": close, "close": close, "volume": 1.0})
    assert "stl_seasonal_strength" in ta.Category["statistics"]
    out = df.ta.stl_seasonal_strength()
    assert out.name == "STLSEAS_100"
    pd.testing.assert_series_equal(out, stl_seasonal_strength(close))
    assert df.ta.stl_seasonal_strength(length=50).name == "STLSEAS_50"
