# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.statistics.firstzero_ac` -- Kats tsfeatures'
`firstzero_ac`: the first lag whose return autocorrelation turns negative
right after a positive one, over a rolling window of one-bar returns.
Measurements are in docs/FirstzeroAcMeasured.md.

What these pin, in order of how much it would hurt to lose:

* CORRECTNESS against the source: Kats' `get_special_ac` lines for
  `firstzero_ac` (`acf(x, fft=True, nlags=len(x))[1:]` and the `while`
  loop), on the returns of every window of an AR(1) frame at lengths 5,
  10 and 100, value for value (skipped where statsmodels is absent, i.e.
  in CI). The FFT length is statsmodels' `_next_regular`, compared over
  1..4999. An independent loop with no FFT and no module code runs
  everywhere. Closed forms: alternating returns read 3; sine returns of
  period 22 read 6; one price jump in a flat window reads `length`
  wherever the jump sits (the sign of the autocorrelation runs negative
  then positive, so there is no positive-to-negative crossing).
* SEMANTICS: it reads how long returns stay positively autocorrelated.
  AR(1) at phi = 0.9 reads later lags than at 0.6, and 0.6 later than
  iid. It is not monotone in phi below that: phi = -0.3 and iid both read
  about 3.
* The rounding guard, from both sides: a steady drift of any size, a
  steep exponential and a flat price with one-ulp jitter are NaN, not the
  sign pattern of floating-point noise; returns of standard deviation
  1e-13 are kept.
* CAUSALITY: future perturbation at 16 offsets, and a mutant (the write
  index moved one bar earlier) proved live and caught at every offset.
  The perturbation is a x1000 jump from the offset on. Swapping in
  another path from the offset on, as the other ports do, does NOT catch
  this mutant (0 of 16, measured): the column is a whole number that
  changes on about 1 bar in 9, and one changed return rarely moves it. A
  return of 999 dominates every window holding it, and moved the column
  at all 16 offsets (measured). A bad tick moves exactly the 101 bars
  whose window holds one of its two returns.
* SCALE-FREE: x8/x64 and x10/x3.7 equal value for value on this frame,
  and the column fires and is not constant.
* Edge cases (flat, bad closes including subnormal and infinite ones, a
  return whose square overflows, short input, length floor, chunk
  boundaries) and wiring (`Category`, the accessor, `FIRSTZEROAC_100`).

The semantics tests assert orderings and wide bands, not exact medians:
the medians depend on numpy's RNG stream, which NEP 19 does not freeze.
"""
import importlib
import types

import numpy as np
import pandas as pd
import pytest
from pandas import Series

from .context import pandas_ta as ta

_REAL = importlib.import_module("pandas_ta.statistics.firstzero_ac")
firstzero_ac = _REAL.firstzero_ac


def _ar1(n=600, seed=0, phi=0.0):
    """Closes whose one-bar returns are AR(1) with coefficient phi, sd 2%."""
    rng = np.random.default_rng(seed)
    e = rng.standard_normal(n) * 0.02 * np.sqrt(1 - phi * phi)
    r = np.empty(n)
    prev = 0.0
    for t in range(n):
        prev = phi * prev + e[t]
        r[t] = prev
    return Series(100 * np.cumprod(1 + r))


def _kats_loop(ac):
    """Kats' `while` loop (tsfeatures.py L1332-1338) on AC = lags 1..n-1."""
    j = 0
    while j < len(ac) - 1:
        if ac[j] > 0 and ac[j + 1] < 0:
            break
        else:
            j += 1
    return j + 2


def _loop(close, length):
    """The direct sum-of-products autocorrelation of each window's returns
    (no FFT), then Kats' loop."""
    c = close.to_numpy(dtype=float)
    r = c[1:] / c[:-1] - 1
    out = np.full(c.size, np.nan)
    for t in range(length, c.size):
        x = r[t - length:t]
        x = x - x.mean()
        a0 = np.dot(x, x)
        ac = [np.dot(x[k:], x[:-k]) / a0 for k in range(1, length)]
        out[t] = _kats_loop(ac)
    return out


# ------------------------------------------------------------ correctness


def test_fft_length_is_statsmodels_next_regular():
    sc = pytest.importorskip("statsmodels.compat.scipy")
    assert all(_REAL._next_regular(t) == sc._next_regular(t) for t in range(1, 5000))


@pytest.mark.parametrize("length", [5, 10, 100])
def test_matches_kats_the_source_call(length):
    """kats/tsfeatures/tsfeatures.py (a6b7e88) `get_special_ac`: L1316
    `AC = acf(x, fft=True, nlags=len(x))[1:]` and L1331-1338, on the
    returns of each window. Kats' L1317 debug `print` is left out."""
    st = pytest.importorskip("statsmodels.tsa.stattools")
    close = _ar1(400, seed=1, phi=0.3)
    out = firstzero_ac(close, length=length).to_numpy()
    c = close.to_numpy()
    r = c[1:] / c[:-1] - 1
    for t in range(length, close.size):
        x = r[t - length:t]
        assert out[t] == _kats_loop(st.acf(x, fft=True, nlags=len(x))[1:]), t
    assert np.isnan(out[:length]).all()


@pytest.mark.parametrize("length", [5, 10, 100])
def test_matches_an_independent_loop(length):
    close = _ar1(400, seed=2, phi=0.6)
    out = firstzero_ac(close, length=length).to_numpy()
    ref = _loop(close, length)
    np.testing.assert_array_equal(out[length:], ref[length:])


def test_alternating_returns_read_3():
    """Returns +a, -a, ...: AC(1) < 0, AC(2) > 0, AC(3) < 0."""
    r = 0.01 * np.where(np.arange(150) % 2, -1.0, 1.0)
    out = firstzero_ac(Series(100 * np.cumprod(np.r_[1.0, 1 + r])))
    assert out.iloc[:100].isna().all()
    assert (out.iloc[100:] == 3).all()


@pytest.mark.parametrize("period, lag", [(10, 3), (22, 6)])
def test_sine_returns_read_about_a_quarter_period(period, lag):
    """Returns 0.01 sin(2 pi k / P): AC(k) follows cos(2 pi k / P), whose
    first negative lag after a positive one is the first k above P / 4.
    P = 22: AC(5) ~ +0.14, AC(6) ~ -0.14, so 6 at every bar. P = 10:
    AC(2) ~ +0.31, AC(3) ~ -0.31, so 3."""
    k = np.arange(400)
    out = firstzero_ac(Series(100 * np.cumprod(1 + 0.01 * np.sin(2 * np.pi * k / period))))
    assert (out.iloc[100:] == lag).all()


def test_one_jump_in_a_flat_window_reads_length():
    """Flat at 100, one step to 101 at bar 150, flat again. The windows
    ending at bars 150..249 hold the step at every position. Demeaned, with
    the step at position p of n returns, AC(k) = (n - k - c n) / (n (n - 1))
    where c is the number of lag-k pairs that include the step: negative
    while k <= max(p, n - 1 - p), positive beyond. The sign runs negative
    then positive, never positive then negative, so Kats' loop runs out:
    `length`. Windows of only zero returns are NaN (the guard)."""
    c = np.r_[np.full(150, 100.0), np.full(150, 101.0)]
    out = firstzero_ac(Series(c))
    assert out.iloc[:150].isna().all()
    assert (out.iloc[150:250] == 100).all()
    assert out.iloc[250:].isna().all()
    assert (firstzero_ac(Series(c), length=20).iloc[150:170] == 20).all()
    # the step mid-window (bar 199 reads the returns at bars 100..199; the
    # step, the return at bar 150, sits at position 50): lags 1..50 are
    # negative and 51..99 positive, as stated
    r = np.diff(c)[99:199] / c[99:199]
    x = r - r.mean()
    ac = np.array([np.dot(x[k:], x[:-k]) for k in range(1, 100)]) / np.dot(x, x)
    assert (ac[:50] < 0).all() and (ac[50:] > 0).all()


# --------------------------------------------------------------- semantics


def _pooled(phi, k=8, n=600):
    return np.concatenate([firstzero_ac(_ar1(n, 500 + i, phi)).dropna().to_numpy() for i in range(k)])


def test_strong_positive_autocorrelation_reads_later_lags():
    """Medians over 40 paths (docs/measure_firstzero_ac.py): 3 for iid, 6
    at phi = 0.6, 14 at phi = 0.9. Asserted: the order, and bands of
    [2, 4], [4, 9] and [9, 20] on 8 paths."""
    iid, mid, high = (np.median(_pooled(p)) for p in (0.0, 0.6, 0.9))
    assert iid < mid < high
    assert 2 <= iid <= 4 and 4 <= mid <= 9 and 9 <= high <= 20


def test_negative_autocorrelation_reads_like_iid():
    """phi = -0.3: AC(1) < 0, AC(2) > 0, AC(3) < 0 most of the time, so
    it reads 3, about as iid returns do. The column does not order
    negative against no autocorrelation. Medians over 40 paths: 3 and 3;
    on these 8 paths, 3 and 4 (docs/measure_firstzero_ac.py,
    `semantics`). Asserted: phi = -0.3 within [3, 4], iid within [2, 4]
    (the band of the test above), and the two within 1 of each other."""
    neg, iid = np.median(_pooled(-0.3)), np.median(_pooled(0.0))
    assert 3 <= neg <= 4 and 2 <= iid <= 4 and abs(neg - iid) <= 1


# ------------------------------------------------------- the rounding guard


@pytest.mark.parametrize("g", [1e-2, 1e-4, 1e-7, 1e-8, 1e-10])
def test_steady_drift_is_nan_not_rounding_noise(g):
    """100 * (1 + g)^t: the returns are equal up to rounding (at most 0.63
    epsilon units against the floor of 64, measured)."""
    assert firstzero_ac(Series(100 * (1 + g) ** np.arange(300.0))).isna().all()


def test_a_steep_exponential_is_nan():
    """exp(linspace(0, 30, 300)): 10% a bar. The largest rounding noise
    measured on a steady series, 5.69 epsilon units against 64."""
    assert firstzero_ac(Series(np.exp(np.linspace(0.0, 30.0, 300)))).isna().all()


def test_one_ulp_jitter_is_nan():
    """A flat 10.0 whose closes flip between 10.0 and the next float up."""
    rng = np.random.default_rng(0)
    c = np.full(300, 10.0)
    c[rng.random(300) < 0.5] = np.nextafter(10.0, 20.0)
    assert firstzero_ac(Series(c)).isna().all()


def test_the_guard_keeps_very_small_real_returns():
    """iid returns of standard deviation 1e-13 are real variation: at least
    393 epsilon units, six times the floor (measured). A floor of about
    400 units or more, or one scaled by price, would blank them."""
    rng = np.random.default_rng(0)
    rng.standard_normal(300)  # the stream position the measurement used
    close = Series(100 * np.cumprod(1 + 1e-13 * rng.standard_normal(300)))
    assert firstzero_ac(close).iloc[100:].notna().all()


# -------------------------------------------------------------- causality


MUTANT = ("lo = length + start", "lo = length - 1 + start")
OFFSETS = range(130, 600, 30)  # 16 offsets


def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_firstzero_ac_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


def _leaks(fn):
    close = _ar1(seed=11)
    base = fn(close)
    hits = 0
    for j in OFFSETS:
        p = close.copy()
        p.iloc[j:] *= 1e3  # one return of 999 at bar j, nothing else changes
        out = fn(p)
        a, b = base.iloc[:j], out.iloc[:j]
        if not (a.isna() == b.isna()).all() or (a[a.notna()] != b[a.notna()]).any():
            hits += 1
    return hits


def test_real_module_never_reads_the_future():
    assert _leaks(firstzero_ac) == 0


def test_mutant_is_caught():
    mod = _load_mutant(*MUTANT)
    close = _ar1(seed=11)
    assert not mod.firstzero_ac(close).equals(firstzero_ac(close))  # live
    assert _leaks(mod.firstzero_ac) == len(OFFSETS)


def test_a_bad_tick_moves_exactly_its_windows():
    """close x1000 at bar 300 changes the returns at bars 300 and 301; the
    windows holding either end at bars 300..400. Each of them moves
    (measured: 101 of 101); every other bar is bit-identical."""
    close = _ar1(seed=4)
    base = firstzero_ac(close)
    bad = close.copy()
    bad.iloc[300] *= 1e3
    out = firstzero_ac(bad)
    moved = np.flatnonzero(~((out == base) | (out.isna() & base.isna())).to_numpy())
    assert moved.tolist() == list(range(300, 401))


# ------------------------------------------------------------ scale-free


@pytest.mark.parametrize("k", [8.0, 64.0])
def test_price_scale_is_bit_identical(k):
    close = _ar1(seed=4)
    base, scaled = firstzero_ac(close), firstzero_ac(close * k)
    pd.testing.assert_series_equal(base, scaled, check_exact=True)


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_price_scale_within_tolerance(k):
    """Returns move by rounding under x10 and x3.7, so an autocorrelation
    within rounding of 0 could change sign. None does on this frame (0
    bars differ, measured); the NaN masks must match and at most 1% of
    bars may differ."""
    close = _ar1(seed=4)
    base, scaled = firstzero_ac(close), firstzero_ac(close * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] != scaled[m]).mean() <= 0.01


def test_fires_and_is_not_constant():
    out = firstzero_ac(_ar1(seed=4))
    assert out.notna().sum() == 500  # 600 bars, the first value at bar 100
    v = out.dropna()
    assert v.nunique() > 1
    assert (v == np.round(v)).all() and v.between(2, 100).all()


# ------------------------------------------------------------- edge cases


def test_flat_prices_are_nan():
    assert firstzero_ac(Series([10.0] * 150)).isna().all()


@pytest.mark.parametrize("bad", [np.nan, np.inf, 0.0, -1.0, 1e-310])
def test_a_bad_close_blanks_its_windows(bad):
    """NaN, infinite, zero, negative and subnormal closes are all missing
    data: returns 150 and 151 are NaN, so the windows ending at bars
    150..250 are NaN."""
    close = _ar1(300, seed=1)
    base = firstzero_ac(close)
    c2 = close.copy()
    c2.iloc[150] = bad
    out = firstzero_ac(c2)
    assert out.iloc[150:251].isna().all()
    pd.testing.assert_series_equal(out.drop(range(150, 251)), base.drop(range(150, 251)))


def test_a_return_whose_square_overflows_is_missing_not_inf():
    """Closes of 1e-150 then 1e150: the return between them (bar 151) is
    about 1e300, finite, but its square overflows. It is missing: the
    windows holding it end at bars 151..250 and are NaN, and nothing
    raises. Bars 150 and 251 read only the finite returns into and out of
    the pair (about -1 each), so they still fire. With the mask on `r`
    alone instead of `r * r`, this test fails (checked)."""
    close = _ar1(300, seed=1)
    base = firstzero_ac(close)
    c2 = close.copy()
    c2.iloc[150] = 1e-150
    c2.iloc[151] = 1e150
    out = firstzero_ac(c2)
    assert out.iloc[151:251].isna().all()
    assert np.isfinite(out.iloc[150]) and np.isfinite(out.iloc[251])
    pd.testing.assert_series_equal(out.drop(range(150, 252)), base.drop(range(150, 252)))


def test_short_input_and_length_floor():
    close = _ar1(150, seed=1)
    assert firstzero_ac(close.iloc[:100]) is None  # 101 closes needed
    assert firstzero_ac(close.iloc[:101]).notna().sum() == 1
    # below 5, the shortest series Kats' `transform` accepts: falls back to
    # the default, the repo's convention (kpss, arch_lm), disclosed in the
    # docstring
    assert firstzero_ac(close, length=4).name == "FIRSTZEROAC_100"
    assert firstzero_ac(close, length=5).notna().sum() == 145


def test_chunk_boundaries_do_not_change_values(monkeypatch):
    close = _ar1(seed=4)
    base = firstzero_ac(close)
    monkeypatch.setattr(_REAL, "CHUNK_CELLS", 7 * 100)
    pd.testing.assert_series_equal(firstzero_ac(close), base, check_exact=True)


# ---------------------------------------------------------------- wiring


def test_name_registration_and_accessor():
    close = _ar1(200, seed=1)
    df = pd.DataFrame({"open": close, "high": close, "low": close, "close": close, "volume": 1.0})
    assert "firstzero_ac" in ta.Category["statistics"]
    out = df.ta.firstzero_ac()
    assert out.name == "FIRSTZEROAC_100"
    pd.testing.assert_series_equal(out, firstzero_ac(close))
    assert df.ta.firstzero_ac(length=50).name == "FIRSTZEROAC_50"
