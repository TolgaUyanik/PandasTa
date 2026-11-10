# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.statistics.diff2_acf1` -- Kats tsfeatures'
`diff2y_acf1`, the lag-1 autocorrelation of the twice-differenced series,
on the log close of a rolling window. Measurements are in
docs/Diff2Acf1Measured.md.

What these pin, in order of how much it would hurt to lose:

* CORRECTNESS against the source: Kats' own lines (the two list
  comprehensions and `acf(diff2x, fft=True, nlags=nlag)[1:][0]`), on the
  log close of every window of an AR(1) frame, length 10 and 100, within
  1e-11 (skipped where statsmodels is absent, i.e. in CI). An independent
  loop with no statsmodels and no module code runs everywhere. And a
  closed form: alternating log returns +a, -a, ... make the return changes
  alternate too, so DIFF2ACF1_10 = -7/8.
* SEMANTICS: iid returns read about -0.5, not 0; AR(1) returns read about
  -(1 - phi) / 2, so the column orders trending above reversing returns;
  volatility clustering (GARCH) does not move it. It is close to a
  function of the window's lag-1 and lag-2 return autocorrelations.
* The rounding guard: a steady drift of any size (1e-2 down to 1e-10 a
  bar), a constant return change and a flat price with one-ulp jitter are
  NaN, not the autocorrelation of floating-point noise; real tick-level
  variation is kept.
* CAUSALITY by future-perturbation over 16 offsets, and a mutant (the write
  index moved one bar earlier) proved live and caught at every offset. A
  bad tick moves exactly the 100 bars whose window holds it.
* SCALE-FREE: x8/x64 bit-identical, x10/x3.7 within 1e-9, and the column
  fires and is not constant.
* Edge cases (flat, bad closes, a price ratio that overflows, short
  input, length floor, chunk boundaries) and wiring (`Category`, the
  accessor, `DIFF2ACF1_100`).

The semantics tests assert bands and orderings, not exact medians: the
medians depend on numpy's RNG stream, which NEP 19 does not freeze.
"""
import importlib
import types

import numpy as np
import pandas as pd
import pytest
from pandas import Series

from .context import pandas_ta as ta

_REAL = importlib.import_module("pandas_ta.statistics.diff2_acf1")
diff2_acf1 = _REAL.diff2_acf1


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


def _garch(n=600, seed=0, a=0.2, b=0.75):
    """Closes whose log returns are GARCH(1,1), unconditional sd 2%: no
    return autocorrelation, strong volatility clustering."""
    rng = np.random.default_rng(seed)
    z = rng.standard_normal(n)
    omega = 4e-4 * (1 - a - b)
    r = np.empty(n)
    h = 4e-4
    for t in range(n):
        r[t] = np.sqrt(h) * z[t]
        h = omega + a * r[t] ** 2 + b * h
    return Series(100 * np.exp(np.cumsum(r)))


def _loop(close, length):
    """sum(x[t] * x[t-1]) / sum(x^2) of the demeaned return changes, one
    window at a time."""
    c = close.to_numpy(dtype=float)
    out = np.full(c.size, np.nan)
    for t in range(length - 1, c.size):
        w = c[t - length + 1:t + 1]
        r = np.log(w[1:] / w[:-1])
        d = np.diff(r)
        x = d - d.mean()
        out[t] = np.dot(x[1:], x[:-1]) / np.dot(x, x)
    return out


# ------------------------------------------------------------ correctness


@pytest.mark.parametrize("length", [10, 100])
def test_matches_kats_the_source_call(length):
    """kats/tsfeatures/tsfeatures.py (a6b7e88) L1098-1105 and L975, on the
    log close of each window. Kats differences the logs; the module takes
    the log of the ratio, so they agree to rounding, not bit for bit."""
    st = pytest.importorskip("statsmodels.tsa.stattools")
    close = _ar1(400, seed=1, phi=0.2)
    out = diff2_acf1(close, length=length).to_numpy()
    logc = np.log(close.to_numpy())
    for t in range(length - 1, close.size):
        x = logc[t - length + 1:t + 1]
        nlag = min(6, len(x) - 2)
        diff1x = [x[i] - x[i - 1] for i in range(1, len(x))]
        diff2x = [diff1x[i] - diff1x[i - 1] for i in range(1, len(diff1x))]
        ref = st.acf(diff2x, fft=True, nlags=nlag)[1:][0]
        assert abs(out[t] - ref) < 1e-11, t
    assert np.isnan(out[:length - 1]).all()


@pytest.mark.parametrize("length", [10, 100])
def test_matches_an_independent_loop(length):
    close = _ar1(400, seed=2, phi=-0.2)
    out = diff2_acf1(close, length=length).to_numpy()
    ref = _loop(close, length)
    np.testing.assert_allclose(out[length - 1:], ref[length - 1:], rtol=0, atol=1e-12)


def test_closed_form():
    """9 log returns +a, -a, ..., +a give 8 return changes -2a, +2a, ...:
    mean 0, sum of squares 8 * 4a^2, sum of lagged products -7 * 4a^2.
    DIFF2ACF1_10 = -7/8."""
    r = 0.01 * np.where(np.arange(9) % 2, -1.0, 1.0)
    close = Series(100 * np.exp(np.r_[0.0, np.cumsum(r)]))
    out = diff2_acf1(close, length=10)
    assert out.iloc[:9].isna().all()
    assert out.iloc[9] == pytest.approx(-0.875, abs=1e-12)


# --------------------------------------------------------------- semantics


def _pooled(make, k=10, n=600):
    return np.concatenate([diff2_acf1(make(n, 500 + i)).dropna().to_numpy() for i in range(k)])


def test_reads_the_return_autocorrelation():
    """AR(1) returns have a population value of -(1 - phi) / 2: -0.65,
    -0.50, -0.35 at phi = -0.3, 0, +0.3. Medians over 10 paths x 501 bars
    sit within 0.03 of those (over 200 paths: -0.639, -0.492, -0.345), in
    order. No memory reads -0.5, not 0."""
    meds = [np.median(_pooled(lambda n, s, p=p: _ar1(n, s, p))) for p in (-0.3, 0.0, 0.3)]
    assert meds[0] < meds[1] < meds[2]
    for med, pop in zip(meds, (-0.65, -0.50, -0.35)):
        assert abs(med - pop) < 0.03


def test_volatility_clustering_does_not_move_it():
    """GARCH(0.20, 0.75) returns -- no autocorrelation, strong clustering --
    read the same as iid returns: medians within 0.03 (over 200 paths:
    -0.489 vs -0.492)."""
    garch = np.median(_pooled(lambda n, s: _garch(n, s)))
    iid = np.median(_pooled(lambda n, s: _ar1(n, s)))
    assert abs(garch - iid) < 0.03
    assert abs(garch + 0.5) < 0.03


def test_it_tracks_the_lag_1_and_lag_2_return_autocorrelations():
    """The population identity (2 rho1 - 1 - rho2) / (2 (1 - rho1)),
    evaluated on each window's own sample autocorrelations of its 99 log
    returns, ranks the bars almost as the column does: Spearman 0.989
    pooled over these 10 iid paths (0.992 over 100 paths in
    docs/measure_diff2_acf1.py). The lag-1 autocorrelation alone ranks
    them less well (0.657 here, 0.71 over 100 paths, and from
    0.38 to 0.89 by path, p10 to p90), so only the ordering is asserted."""
    cols, gs, rho1s = [], [], []
    for i in range(10):
        close = _ar1(600, seed=500 + i)
        c = close.to_numpy()
        r = np.log(c[1:] / c[:-1])
        g = np.full(c.size, np.nan)
        rho1 = np.full(c.size, np.nan)
        for t in range(99, c.size):
            w = r[t - 99:t]
            x = w - w.mean()
            a1 = np.dot(x[1:], x[:-1]) / np.dot(x, x)
            a2 = np.dot(x[2:], x[:-2]) / np.dot(x, x)
            rho1[t] = a1
            g[t] = (2 * a1 - 1 - a2) / (2 * (1 - a1))
        cols.append(diff2_acf1(close).to_numpy()[99:])
        gs.append(g[99:])
        rho1s.append(rho1[99:])
    col = Series(np.concatenate(cols))
    rho_g = col.corr(Series(np.concatenate(gs)), method="spearman")
    rho_1 = col.corr(Series(np.concatenate(rho1s)), method="spearman")
    assert rho_g > 0.97
    assert rho_1 < rho_g


# ------------------------------------------------------- the rounding guard


@pytest.mark.parametrize("g", [1e-2, 1e-4, 1e-7, 1e-8, 1e-10])
def test_steady_drift_is_nan_not_rounding_noise(g):
    """100 * (1 + g)^t: the log returns are equal up to rounding, so the
    return changes are rounding noise (~1e-16) whatever g is."""
    assert diff2_acf1(Series(100 * (1 + g) ** np.arange(300.0))).isna().all()


def test_constant_return_change_is_nan():
    """log close = 1e-5 * t^2: the return grows by exactly 2e-5 a bar, so
    the return changes do not vary."""
    close = Series(100 * np.exp(1e-5 * np.arange(300.0) ** 2))
    assert diff2_acf1(close).isna().all()


def test_one_ulp_jitter_is_nan():
    """A flat 10.0 whose closes flip between 10.0 and the next float up."""
    rng = np.random.default_rng(0)
    c = np.full(300, 10.0)
    c[rng.random(300) < 0.5] = np.nextafter(10.0, 20.0)
    assert diff2_acf1(Series(c)).isna().all()


def test_the_guard_keeps_real_tick_variation():
    """10% a bar on a 0.01 tick, 150 bars: the rounding to ticks is real
    variation, far above the floor, so every bar from 99 on fires."""
    p = [10.0]
    for _ in range(149):
        p.append(round(p[-1] * 1.1, 2))
    assert diff2_acf1(Series(p)).iloc[99:].notna().all()


# -------------------------------------------------------------- causality


MUTANT = ("lo = length - 1 + start", "lo = length - 2 + start")
OFFSETS = range(130, 600, 30)  # 16 offsets


def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_diff2_acf1_mutant")
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
    assert _leaks(diff2_acf1) == 0


def test_mutant_is_caught():
    mod = _load_mutant(*MUTANT)
    close = _ar1(seed=11)
    assert not mod.diff2_acf1(close).equals(diff2_acf1(close))  # live
    assert _leaks(mod.diff2_acf1) == len(OFFSETS)


def test_a_bad_tick_moves_exactly_its_windows():
    """close x1000 at bar 300 changes log returns 299 and 300, so return
    changes 298..300; the windows holding any of them end at bars 300..399.
    Every other bar is bit-identical."""
    close = _ar1(seed=4)
    base = diff2_acf1(close)
    bad = close.copy()
    bad.iloc[300] *= 1e3
    out = diff2_acf1(bad)
    moved = np.flatnonzero(~((out == base) | (out.isna() & base.isna())).to_numpy())
    assert moved.tolist() == list(range(300, 400))


# ------------------------------------------------------------ scale-free


@pytest.mark.parametrize("k", [8.0, 64.0])
def test_price_scale_is_bit_identical(k):
    close = _ar1(seed=4)
    base, scaled = diff2_acf1(close), diff2_acf1(close * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_price_scale_within_tolerance(k):
    close = _ar1(seed=4)
    base, scaled = diff2_acf1(close), diff2_acf1(close * k)
    assert (base.isna() == scaled.isna()).all()
    assert (base - scaled).abs().max() < 1e-9


def test_fires_and_is_not_constant():
    out = diff2_acf1(_ar1(seed=4))
    assert out.notna().sum() == 501  # 600 bars, the first value at bar 99
    assert out.dropna().nunique() == 501
    assert out.dropna().between(-1, 1).all()


# ------------------------------------------------------------- edge cases


def test_flat_prices_are_nan():
    assert diff2_acf1(Series([10.0] * 150)).isna().all()


@pytest.mark.parametrize("bad", [np.nan, 0.0, -1.0])
def test_a_bad_close_blanks_its_windows(bad):
    close = _ar1(300, seed=1)
    base = diff2_acf1(close)
    c2 = close.copy()
    c2.iloc[150] = bad
    out = diff2_acf1(c2)
    assert out.iloc[150:250].isna().all()  # log returns 149 and 150 are NaN
    pd.testing.assert_series_equal(out.drop(range(150, 250)), base.drop(range(150, 250)))


def test_a_price_ratio_that_overflows_is_missing_not_inf():
    """A close of 1e-310 makes the next ratio overflow to inf. That return
    is treated as missing: the windows holding it (bars 151..249) are NaN,
    nothing raises, and every bar outside 150..249 is unchanged. Bar 150
    still fires, on the (finite, absurd) return into the tiny close."""
    close = _ar1(300, seed=1)
    base = diff2_acf1(close)
    c2 = close.copy()
    c2.iloc[150] = 1e-310
    out = diff2_acf1(c2)
    assert out.iloc[151:250].isna().all()
    assert np.isfinite(out.iloc[150])
    pd.testing.assert_series_equal(out.drop(range(150, 250)), base.drop(range(150, 250)))


def test_short_input_and_length_floor():
    close = _ar1(150, seed=1)
    assert diff2_acf1(close.iloc[:99]) is None  # 100 closes needed
    assert diff2_acf1(close.iloc[:100]).notna().sum() == 1
    # below Kats' own minimum of 10 points: falls back to the default, the
    # repo's convention (kpss, arch_lm), disclosed in the docstring
    assert diff2_acf1(close, length=9).name == "DIFF2ACF1_100"
    assert diff2_acf1(close, length=10).notna().sum() == 141


def test_chunk_boundaries_do_not_change_values(monkeypatch):
    close = _ar1(seed=4)
    base = diff2_acf1(close)
    monkeypatch.setattr(_REAL, "CHUNK_CELLS", 7 * 98)
    pd.testing.assert_series_equal(diff2_acf1(close), base, check_exact=True)


# ---------------------------------------------------------------- wiring


def test_name_registration_and_accessor():
    close = _ar1(200, seed=1)
    df = pd.DataFrame({"open": close, "high": close, "low": close, "close": close, "volume": 1.0})
    assert "diff2_acf1" in ta.Category["statistics"]
    out = df.ta.diff2_acf1()
    assert out.name == "DIFF2ACF1_100"
    pd.testing.assert_series_equal(out, diff2_acf1(close))
    assert df.ta.diff2_acf1(length=50).name == "DIFF2ACF1_50"
