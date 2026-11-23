# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.statistics.diff1_pacf5` -- Kats tsfeatures'
`diff1y_pacf5`, the sum of squares of partial-autocorrelation lags 1-5 of
the window's log returns. Measurements are in docs/Diff1Pacf5Measured.md.

What these pin, in order of how much it would hurt to lose:

* CORRECTNESS: a from-scratch Durbin-Levinson recursion (no statsmodels, no
  module code) matches the module to 1e-12, and the module matches
  statsmodels' own `pacf(..., method="ywm")` -- the method that implements
  Durbin-Levinson on the UNADJUSTED sample ACF, the scale-free form the
  issue specifies -- to 1e-9 (skipped where statsmodels is absent, i.e. in
  CI).
* CAUSALITY by future-perturbation over 16 offsets, and a mutant (the write
  index moved one bar earlier) proved live and caught at every offset. A
  bad tick moves exactly the bars whose window holds it.
* The rounding guard, same rule as diff2_acf1 one differencing level
  earlier: a steady drift of any size and a flat price with one-ulp jitter
  are NaN, not the partial autocorrelation of floating-point noise; real
  variation is kept, down to returns of standard deviation 1e-12.
* SCALE-FREE: x8/x64 bit-identical, x10/x3.7 within tolerance, and the
  column fires and is not constant, always in [0, 5).
* Edge cases (flat, bad closes including subnormal and infinite ones, a
  price ratio that overflows, short input, length floor, chunk boundaries)
  and wiring (`Category`, the accessor, `DIFF1PACF5_100`).
"""
import importlib
import types

import numpy as np
import pandas as pd
import pytest
from pandas import Series

from .context import pandas_ta as ta

_REAL = importlib.import_module("pandas_ta.statistics.diff1_pacf5")
diff1_pacf5 = _REAL.diff1_pacf5


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


def _loop_pacf5(rho):
    """Independent (no statsmodels, no module code) Durbin-Levinson,
    scalar, straight off the textbook recursion, on 5 unadjusted ACF
    lags."""
    phi = {(1, 1): rho[0]}
    out = [phi[1, 1]]
    for k in range(2, 6):
        num = rho[k - 1] - sum(phi[k - 1, j] * rho[k - j - 1] for j in range(1, k))
        den = 1 - sum(phi[k - 1, j] * rho[j - 1] for j in range(1, k))
        phi[k, k] = num / den
        for j in range(1, k):
            phi[k, j] = phi[k - 1, j] - phi[k, k] * phi[k - 1, k - j]
        out.append(phi[k, k])
    return np.array(out)


def _loop(close, length):
    """sum((Durbin-Levinson pacf of the demeaned window's returns)[1..5] ** 2),
    one window at a time, via the independent recursion above."""
    c = close.to_numpy(dtype=float)
    out = np.full(c.size, np.nan)
    for t in range(length - 1, c.size):
        w = c[t - length + 1:t + 1]
        r = np.log(w[1:] / w[:-1])
        x = r - r.mean()
        c0 = np.dot(x, x)
        rho = np.array([np.dot(x[:-k], x[k:]) / c0 for k in range(1, 6)])
        out[t] = (_loop_pacf5(rho) ** 2).sum()
    return out


# ------------------------------------------------------------ correctness


def test_matches_an_independent_recursion():
    """No statsmodels, no module code: runs everywhere, including CI."""
    close = _ar1(400, seed=2, phi=-0.2)
    out = diff1_pacf5(close, length=100).to_numpy()
    ref = _loop(close, 100)
    np.testing.assert_allclose(out[99:], ref[99:], rtol=0, atol=1e-12)


@pytest.mark.parametrize("length", [14, 100])
def test_matches_statsmodels_pacf_ywm(length):
    """statsmodels' `pacf(..., method="ywm")` is Yule-Walker on the
    UNADJUSTED sample ACF -- the scale-free form the issue specifies
    (docs/measure_diff1_pacf5.py: `pacf_method_probe`, max abs diff 1e-10
    against the from-scratch recursion above). Checked against the module
    on every window of an AR(1) frame."""
    st = pytest.importorskip("statsmodels.tsa.stattools")
    close = _ar1(400, seed=1, phi=0.2)
    out = diff1_pacf5(close, length=length).to_numpy()
    logc = np.log(close.to_numpy())
    for t in range(length - 1, close.size):
        x = logc[t - length + 1:t + 1]
        r = np.diff(x)
        ref = (st.pacf(r, nlags=6, method="ywm")[1:6] ** 2).sum()
        assert abs(out[t] - ref) < 1e-9, t
    assert np.isnan(out[:length - 1]).all()


def test_kats_own_call_raises_below_14_points():
    """Shared with diff2_acf1 (same Kats function, L1107): `pacf(x,
    nlags=7)` raises ValueError on 10 to 13 points. This pins statsmodels'
    behaviour, not the module's."""
    st = pytest.importorskip("statsmodels.tsa.stattools")
    x = np.log(_ar1(20, seed=1).to_numpy())
    for n in (10, 11, 12, 13):
        with pytest.raises(ValueError):
            st.pacf(x[:n], nlags=7)
    st.pacf(x[:14], nlags=7)


def test_closed_form():
    """14 log returns alternating +a, -a: for x_t = a * (-1)^t (t = 0..13,
    mean exactly 0 since the counts of +1 and -1 are equal), the unadjusted
    ACF has the closed form rho_k = (-1)^k * (14 - k) / 14. Durbin-Levinson
    on that closed form -- derived by hand, not read off the window's own
    arithmetic -- is an independent check of the ACF formula itself."""
    rho = np.array([(-1) ** k * (14 - k) / 14 for k in range(1, 6)])
    expected = (_loop_pacf5(rho) ** 2).sum()
    r = 0.01 * np.where(np.arange(14) % 2, -1.0, 1.0)
    close = Series(100 * np.exp(np.r_[0.0, np.cumsum(r)]))
    out = diff1_pacf5(close, length=15)
    assert out.iloc[14] == pytest.approx(expected, abs=1e-12)


def test_an_odd_alternation_is_computable():
    """An odd-length alternating run breaks the exact rho_1 = -1 tie (the
    last unpaired return), so the recursion does not saturate. Cross-checked
    against the independent loop."""
    r = 0.01 * np.where(np.arange(13) % 2, -1.0, 1.0)
    close = Series(100 * np.exp(np.r_[0.0, np.cumsum(r)]))
    out = diff1_pacf5(close, length=14)
    ref = _loop(close, 14)
    assert out.iloc[13] == pytest.approx(ref[13], abs=1e-12)
    assert np.isfinite(out.iloc[13])


# ------------------------------------------------------- the rounding guard


@pytest.mark.parametrize("g", [1e-2, 1e-4, 1e-7, 1e-8, 1e-10])
def test_steady_drift_is_nan_not_rounding_noise(g):
    """100 * (1 + g)^t: every log return is equal up to rounding, so the
    window's returns do not vary beyond floating-point noise (~1e-16),
    whatever g is."""
    assert diff1_pacf5(Series(100 * (1 + g) ** np.arange(300.0))).isna().all()


def test_one_ulp_jitter_is_nan():
    """A flat 10.0 whose closes flip between 10.0 and the next float up."""
    rng = np.random.default_rng(0)
    c = np.full(300, 10.0)
    c[rng.random(300) < 0.5] = np.nextafter(10.0, 20.0)
    assert diff1_pacf5(Series(c)).isna().all()


def test_a_steep_exponential_is_nan():
    """exp(linspace(0, 30, 300)): 10% a bar, constant log return up to
    rounding."""
    assert diff1_pacf5(Series(np.exp(np.linspace(0.0, 30.0, 300)))).isna().all()


def test_the_guard_keeps_real_tick_variation():
    """10% a bar on a 0.01 tick, 150 bars: the rounding to ticks is real
    variation, far above the floor, so every bar from 99 on fires."""
    p = [10.0]
    for _ in range(149):
        p.append(round(p[-1] * 1.1, 2))
    assert diff1_pacf5(Series(p)).iloc[99:].notna().all()


def test_the_guard_keeps_very_small_real_returns():
    """iid log returns of standard deviation 1e-12 are real variation, far
    above the floor."""
    rng = np.random.default_rng(0)
    close = Series(100 * np.exp(np.cumsum(1e-12 * rng.standard_normal(300))))
    assert diff1_pacf5(close).iloc[99:].notna().all()


# -------------------------------------------------------------- causality


MUTANT = ("lo = length - 1 + start", "lo = length - 2 + start")
OFFSETS = range(130, 600, 30)  # 16 offsets


def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_diff1_pacf5_mutant")
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
    assert _leaks(diff1_pacf5) == 0


def test_mutant_is_caught():
    mod = _load_mutant(*MUTANT)
    close = _ar1(seed=11)
    assert not mod.diff1_pacf5(close).equals(diff1_pacf5(close))  # live
    assert _leaks(mod.diff1_pacf5) == len(OFFSETS)


def test_a_bad_tick_moves_exactly_its_windows():
    """close x1000 at bar 300 changes log returns 299 and 300; the windows
    holding either end at bars 300..399. Every other bar is bit-identical."""
    close = _ar1(seed=4)
    base = diff1_pacf5(close)
    bad = close.copy()
    bad.iloc[300] *= 1e3
    out = diff1_pacf5(bad)
    moved = np.flatnonzero(~((out == base) | (out.isna() & base.isna())).to_numpy())
    assert moved.tolist() == list(range(300, 400))


# ------------------------------------------------------------ scale-free


@pytest.mark.parametrize("k", [8.0, 64.0])
def test_price_scale_is_bit_identical(k):
    close = _ar1(seed=4)
    base, scaled = diff1_pacf5(close), diff1_pacf5(close * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_price_scale_within_tolerance(k):
    close = _ar1(seed=4)
    base, scaled = diff1_pacf5(close), diff1_pacf5(close * k)
    assert (base.isna() == scaled.isna()).all()
    assert (base - scaled).abs().max() < 1e-9


def test_fires_and_is_not_constant():
    out = diff1_pacf5(_ar1(seed=4))
    assert out.notna().sum() > 0
    assert out.notna().sum() < 600  # 0 < fires < n
    assert out.dropna().nunique() > 1
    assert out.dropna().between(0, 5, inclusive="left").all()


# ------------------------------------------------------------- edge cases


def test_flat_prices_are_nan():
    assert diff1_pacf5(Series([10.0] * 150)).isna().all()


@pytest.mark.parametrize("bad", [np.nan, np.inf, 0.0, -1.0, 1e-310])
def test_a_bad_close_blanks_its_windows(bad):
    """NaN, infinite, zero, negative and subnormal closes are all missing
    data. A bad close at bar 150 nulls returns 149 and 150 (the window is
    99 returns wide), so every window holding either -- bars 150..249 --
    is NaN."""
    close = _ar1(300, seed=1)
    base = diff1_pacf5(close)
    c2 = close.copy()
    c2.iloc[150] = bad
    out = diff1_pacf5(c2)
    assert out.iloc[150:250].isna().all()
    pd.testing.assert_series_equal(out.drop(range(150, 250)), base.drop(range(150, 250)))


def test_a_price_ratio_that_overflows_is_missing_not_inf():
    """Closes of 1e-300 at bar 150 and 1e300 at bar 151 are both normal
    floats, but their ratio (the close150 -> close151 transition, return
    150) overflows to inf: treated as missing, not inf, so return 150 is
    NaN and windows holding it -- bars 151..249 -- are NaN. Returns 149
    (close149 -> close150) and 151 (close151 -> close152) are finite but
    altered, so bars 150 and 250 -- whose windows hold one of those but
    not return 150 -- are finite yet differ from the base value. Every
    bar outside 150..250 is bit-identical."""
    close = _ar1(300, seed=1)
    base = diff1_pacf5(close)
    c2 = close.copy()
    c2.iloc[150] = 1e-300
    c2.iloc[151] = 1e300
    out = diff1_pacf5(c2)
    assert out.iloc[151:250].isna().all()
    assert np.isfinite(out.iloc[150]) and np.isfinite(out.iloc[250])
    pd.testing.assert_series_equal(out.drop(range(150, 251)), base.drop(range(150, 251)))


def test_short_input_and_length_floor():
    close = _ar1(150, seed=1)
    assert diff1_pacf5(close.iloc[:99]) is None  # 100 closes needed
    assert diff1_pacf5(close.iloc[:100]).notna().sum() == 1
    assert diff1_pacf5(close, length=13).name == "DIFF1PACF5_100"  # below floor: falls back
    assert diff1_pacf5(close, length=14).notna().sum() == 137


def test_chunk_boundaries_do_not_change_values(monkeypatch):
    close = _ar1(seed=4)
    base = diff1_pacf5(close)
    monkeypatch.setattr(_REAL, "CHUNK_CELLS", 7 * 99)
    pd.testing.assert_series_equal(diff1_pacf5(close), base, check_exact=True)


# ---------------------------------------------------------------- wiring


def test_name_registration_and_accessor():
    close = _ar1(200, seed=1)
    df = pd.DataFrame({"open": close, "high": close, "low": close, "close": close, "volume": 1.0})
    assert "diff1_pacf5" in ta.Category["statistics"]
    out = df.ta.diff1_pacf5()
    assert out.name == "DIFF1PACF5_100"
    pd.testing.assert_series_equal(out, diff1_pacf5(close))
    assert df.ta.diff1_pacf5(length=50).name == "DIFF1PACF5_50"
