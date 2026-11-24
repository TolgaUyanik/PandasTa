# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.statistics.stl_spikiness` -- Kats tsfeatures'
`get_stl_features` spikiness, `var(nanvar of leave-one-out resid)`, from an
STL decomposition (period 5) of the rolling window's log close.
Measurements are in docs/StlSpikinessMeasured.md.

This module reuses `pandas_ta.statistics.stl_seasonal_strength`'s
`_build_ops` (the two fixed length x length operators the STL inner loop
collapses to under `robust=False`) rather than re-deriving the
LOESS/cycle-subseries/low-pass math -- same pattern as `stl_trend_strength`.
So this file does not re-test that math from scratch; it tests that THIS
module's residual, leave-one-out closed form and final variance are correct
given those operators.

What these pin, in order of how much it would hurt to lose:

* CORRECTNESS: a brute-force `np.delete`/`np.nanvar` leave-one-out loop (the
  literal reading of "var(nanvar of leave-one-out resid)") matches this
  module's closed-form shortcut exactly (to float rounding), both against a
  hand-run fixed-point STL and against statsmodels' own
  `STL(window, period=5).fit()` -- the exact call the screen prototype made
  -- over EVERY window of two 400-bar frames at length 100, plus lengths 50
  and 101 and a non-multiple-of-5 length (53).
* CAUSALITY by future-perturbation over 16 offsets, and a mutant (the chunk
  write index moved one bar earlier) caught at all 16.
* The flat/jitter guard: an exactly flat price and one-ulp float jitter are
  NaN, but a smooth deterministic drift of any steepness still fires, near
  zero (a noiseless drift's residual is ~0, so every leave-one-out variance
  is ~0 too).
* SCALE-FREE: x8/x64 bit-identical, x10/x3.7 within tolerance; the column
  fires, is not constant, and a bad close nulls exactly the windows holding
  it.
* Edge cases (bad closes including subnormal/infinite, short input, the
  length floor, chunk boundaries, non-multiple-of-5 lengths) and wiring
  (`Category`, the accessor, `STLSPIKE_100`).
"""
import importlib
import types

import numpy as np
import pandas as pd
import pytest
from pandas import Series

from .context import pandas_ta as ta

_REAL = importlib.import_module("pandas_ta.statistics.stl_spikiness")
_SEAS = importlib.import_module("pandas_ta.statistics.stl_seasonal_strength")
stl_spikiness = _REAL.stl_spikiness


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


def _brute_force_spikiness(resid):
    """The literal "var(nanvar of leave-one-out resid)" reading: drop each
    element in turn, take the (population, ddof=0) variance of what is left,
    then the variance of that array of leave-one-out variances. Used as the
    independent oracle for the module's closed-form shortcut."""
    n = len(resid)
    v = np.empty(n)
    for i in range(n):
        v[i] = np.nanvar(np.delete(resid, i))
    return np.var(v)


def _fixed_point_stl(logc_window):
    """Direct 5-pass iteration of the STL inner loop (shares
    `_seasonal_op`/`_loess_weights` with `_build_ops` -- see that module's
    own test suite for the independent statsmodels check of THAT math).
    Used here only as a second route to (trend, seasonal) for
    `test_matches_a_hand_run_fixed_point_recursion`, which exists to catch a
    wrong closed-form/sign in THIS module, not to re-validate the
    operators."""
    n = len(logc_window)
    seasonal_op = _SEAS._seasonal_op(n)
    trend_loess_op = _SEAS._loess_weights(n, np.arange(n), np.arange(n), _SEAS.TREND, degree=1)
    t = np.zeros(n)
    s = None
    for _ in range(_SEAS.INNER_ITER):
        s = seasonal_op @ (logc_window - t)
        t = trend_loess_op @ (logc_window - s)
    return t, s


# ------------------------------------------------------------ correctness


def test_matches_a_hand_run_fixed_point_recursion():
    close = _ar1(300, seed=2, phi=-0.2)
    logc = np.log(close.to_numpy())
    out = stl_spikiness(close, length=100).to_numpy()
    ts = (99, 150, 220, 299)
    refs = np.empty(len(ts))
    for idx, t in enumerate(ts):
        w = logc[t - 99:t + 1]
        trend, seasonal = _fixed_point_stl(w)
        resid = w - trend - seasonal
        refs[idx] = _brute_force_spikiness(resid)
    # STLSPIKE_100 is ~1e-12 on these frames, so an absolute tolerance would
    # pass values wrong by orders of magnitude: relative, against the
    # ~1e-24 measured agreement (docs/StlSpikinessMeasured.md's Gate A table).
    np.testing.assert_allclose(out[list(ts)], refs, rtol=1e-6, atol=0)


@pytest.mark.parametrize("length", [50, 100, 101])
def test_matches_statsmodels_stl(length):
    """statsmodels' `STL(window, period=5).fit()` -- the exact call the
    screen prototype made -- checked on EVERY window of a 400-bar AR(1)
    frame (301 fits, ~0.15s), with the brute-force leave-one-out loop
    (`_brute_force_spikiness`) as the oracle for the formula itself: max
    abs diff ~1e-23 at every length tried (see docs/StlSpikinessMeasured.md's
    Gate A table for the measured per-case figures), including 101 (not a
    multiple of 5). Independent of `_build_ops`'s own operator-construction
    code -- this compares against statsmodels' `resid` directly."""
    stl = pytest.importorskip("statsmodels.tsa.seasonal").STL
    close = _ar1(400, seed=1, phi=0.2)
    out = stl_spikiness(close, length=length).to_numpy()
    logc = np.log(close.to_numpy())
    refs = np.empty(close.size - (length - 1))
    for t in range(length - 1, close.size):
        w = logc[t - length + 1:t + 1]
        r = stl(w, period=5).fit()
        refs[t - (length - 1)] = _brute_force_spikiness(r.resid)
    # Relative, not absolute: STLSPIKE_100 is ~1e-12 here (measured agreement
    # is rtol ~1e-11; 1e-6 leaves five orders of slack -- see
    # docs/StlSpikinessMeasured.md's Gate A table).
    np.testing.assert_allclose(out[length - 1:], refs, rtol=1e-6, atol=0)
    assert np.isnan(out[:length - 1]).all()


def test_a_length_not_a_multiple_of_5_still_matches():
    """length=53: subseries lengths differ by one (11,11,11,10,10),
    exercising the general (not evenly-divisible) interleaving the shared
    operators use."""
    stl = pytest.importorskip("statsmodels.tsa.seasonal").STL
    close = _ar1(200, seed=3, phi=0.1)
    out = stl_spikiness(close, length=53).to_numpy()
    logc = np.log(close.to_numpy())
    ts = list(range(52, 200, 7))
    refs = np.empty(len(ts))
    for idx, t in enumerate(ts):
        w = logc[t - 52:t + 1]
        r = stl(w, period=5).fit()
        refs[idx] = _brute_force_spikiness(r.resid)
    np.testing.assert_allclose(out[ts], refs, rtol=1e-6, atol=0)


def test_closed_form_matches_brute_force_on_an_arbitrary_array():
    """The module's own closed-form leave-one-out shortcut, exercised
    through `stl_spikiness` ITSELF (not re-derived in the test body) and
    compared against the brute-force `np.delete` loop fed the SAME
    residual, obtained independently via the hand-run fixed-point STL
    route -- at window lengths (50, 73, 101, 150) not covered by the other
    oracle tests, including one (73) not a multiple of 5."""
    cases = ((50, 11, -0.05, 60), (73, 12, 0.1, 90), (101, 13, -0.15, 140), (150, 14, 0.0, 200))
    out_vals = np.empty(len(cases))
    refs = np.empty(len(cases))
    for idx, (length, seed, phi, t) in enumerate(cases):
        close = _ar1(t + 1, seed=seed, phi=phi)
        logc = np.log(close.to_numpy())
        out_vals[idx] = stl_spikiness(close, length=length).to_numpy()[t]
        w = logc[t - length + 1:t + 1]
        trend, seasonal = _fixed_point_stl(w)
        resid = w - trend - seasonal
        refs[idx] = _brute_force_spikiness(resid)
    np.testing.assert_allclose(out_vals, refs, rtol=1e-6, atol=0)


# ------------------------------------------------------- the flat/jitter guard


def test_flat_prices_are_nan():
    assert stl_spikiness(Series([10.0] * 150)).isna().all()


def test_one_ulp_jitter_is_nan():
    rng = np.random.default_rng(0)
    c = np.full(300, 10.0)
    c[rng.random(300) < 0.5] = np.nextafter(10.0, 20.0)
    assert stl_spikiness(Series(c)).isna().all()


@pytest.mark.parametrize("g", [1e-2, 1e-4, 1e-7, 1e-8, 1e-10])
def test_a_smooth_drift_still_fires(g):
    """STL reads log-close LEVELS, where a drift's values genuinely vary:
    every drift steepness fires (measured in docs/measure_stl_spikiness.py).
    A noiseless drift's residual is ~0, so its spikiness is ~0 too --
    checked loosely here (not numerically exploded); exact ranges are in
    the Measured doc."""
    out = stl_spikiness(Series(100 * (1 + g) ** np.arange(300.0)))
    assert out.iloc[99:].notna().all()
    assert out.iloc[99:].abs().max() < 1e-4  # sanity: not numerically exploded


# -------------------------------------------------------------- causality


MUTANT = ("lo = length - 1 + start", "lo = length - 2 + start")
OFFSETS = range(130, 600, 30)  # 16 offsets


def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_stl_spikiness_mutant")
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
    assert _leaks(stl_spikiness) == 0


def test_mutant_is_caught():
    mod = _load_mutant(*MUTANT)
    close = _ar1(seed=11)
    assert not mod.stl_spikiness(close).equals(stl_spikiness(close))  # live
    assert _leaks(mod.stl_spikiness) == len(OFFSETS)


def test_a_bad_close_nulls_exactly_its_windows():
    """close -> NaN at bar 300 (window width 100): every window holding it,
    bars 300..399, is NaN; every other bar is bit-identical."""
    close = _ar1(seed=4)
    base = stl_spikiness(close)
    bad = close.copy()
    bad.iloc[300] = np.nan
    out = stl_spikiness(bad)
    moved = np.flatnonzero(~((out == base) | (out.isna() & base.isna())).to_numpy())
    assert moved.tolist() == list(range(300, 400))


# ------------------------------------------------------------ scale-free


@pytest.mark.parametrize("k", [8.0, 64.0])
def test_price_scale_is_bit_identical(k):
    """STL reads `log(close / the window's own first close)`, not
    `log(close)` directly: under a power-of-two rescale the numerator and
    denominator are both multiplied by an exactly-representable factor, so
    the residual -- and everything downstream, fed the identical bit
    pattern -- is bit-identical (same device as kpss.py / stl_seasonal_strength.py)."""
    close = _ar1(seed=4)
    base, scaled = stl_spikiness(close), stl_spikiness(close * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_price_scale_within_tolerance(k):
    """Not a power of two, so not bit-exact, but within tight tolerance."""
    close = _ar1(seed=4)
    base, scaled = stl_spikiness(close), stl_spikiness(close * k)
    assert (base.isna() == scaled.isna()).all()
    assert (base - scaled).abs().max() < 1e-9


def test_fires_and_is_not_constant():
    out = stl_spikiness(_ar1(seed=4))
    assert out.notna().sum() > 0
    assert out.notna().sum() < 600  # 0 < fires < n
    assert out.dropna().nunique() > 1


# ------------------------------------------------------------- edge cases


@pytest.mark.parametrize("bad", [np.nan, np.inf, 0.0, -1.0, 1e-310])
def test_a_bad_close_blanks_its_windows(bad):
    close = _ar1(300, seed=1)
    base = stl_spikiness(close)
    c2 = close.copy()
    c2.iloc[150] = bad
    out = stl_spikiness(c2)
    assert out.iloc[150:250].isna().all()
    pd.testing.assert_series_equal(out.drop(range(150, 250)), base.drop(range(150, 250)))


def test_short_input_and_length_floor():
    close = _ar1(150, seed=1)
    assert stl_spikiness(close.iloc[:99]) is None  # 100 closes needed (default length)
    assert stl_spikiness(close.iloc[:100]).notna().sum() == 1
    assert stl_spikiness(close, length=49).name == "STLSPIKE_100"  # below floor: falls back
    assert stl_spikiness(close.iloc[:50], length=50).notna().sum() == 1


def test_chunk_boundaries_do_not_change_values(monkeypatch):
    """Not bit-exact (unlike the simpler elementwise ports): each chunk's
    rows go through a matrix multiply, and BLAS's summation order can
    differ by a handful of chunk-size-dependent ULPs -- measured in
    docs/measure_stl_spikiness.py, nowhere near 1e-9 (Gate D's own x10/x3.7
    tolerance)."""
    close = _ar1(seed=4)
    base = stl_spikiness(close)
    monkeypatch.setattr(_REAL, "CHUNK_CELLS", 7 * 100)
    out = stl_spikiness(close)
    assert (out.isna() == base.isna()).all()
    assert (out - base).abs().max() < 1e-9


def test_build_ops_is_shared_with_stl_seasonal_strength():
    """`_build_ops` is imported, not re-derived: the op cache is the SAME
    object `stl_seasonal_strength` fills, so a window length computed by
    either module reuses the other's cached matrices."""
    assert _REAL._build_ops is _SEAS._build_ops
    _SEAS.stl_seasonal_strength(_ar1(150, seed=1), length=51)
    assert 51 in _SEAS._OP_CACHE
    stl_spikiness(_ar1(150, seed=2), length=51)
    assert _REAL._build_ops(51) is _SEAS._OP_CACHE[51]


# ---------------------------------------------------------------- wiring


def test_name_registration_and_accessor():
    close = _ar1(200, seed=1)
    df = pd.DataFrame({"open": close, "high": close, "low": close, "close": close, "volume": 1.0})
    assert "stl_spikiness" in ta.Category["statistics"]
    out = df.ta.stl_spikiness()
    assert out.name == "STLSPIKE_100"
    pd.testing.assert_series_equal(out, stl_spikiness(close))
    assert df.ta.stl_spikiness(length=50).name == "STLSPIKE_50"
