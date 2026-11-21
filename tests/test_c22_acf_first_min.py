# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.statistics.c22_acf_first_min` -- catch22's
`CO_FirstMin_ac`: the first lag where the sample autocorrelation of the
last `length` daily returns stops falling and starts rising, over a
rolling window. Measurements are in docs/C22AcfFirstMinMeasured.md.

What these pin, in order of how much it would hurt to lose:

* CORRECTNESS against the definition: the FFT-based autocorrelation
  (demeaned once, divisor `length`) against an independent double loop
  with no FFT and no vectorisation, value for value, at three lengths.
  Two closed forms: alternating returns read 1 (ACF(0)=1, ACF(1)<0,
  ACF(2)>0 is an immediate local minimum); a deterministic linear return
  RAMP has a monotonically falling autocorrelation with no interior
  minimum, so it reads the `length` sentinel.
* CAUSALITY: future-perturbation sweep at several offsets, and a mutant
  (the write index moved one bar earlier) proved live and caught at
  every offset.
* The rounding guard: a steady drift of any size and a flat price with
  one-ulp jitter are NaN; returns of standard deviation 1e-13 are kept
  (the same floor and the same relative scale as `firstzero_ac`, the
  sibling reading the same window).
* SCALE-FREE: x8/x64 bit-identical (the price enters only as a ratio);
  x10/x3.7 within tolerance; the column fires and is not constant.
* Edge cases (flat, bad closes including subnormal and infinite ones, a
  return whose square overflows, short input, length floor, chunk
  boundaries) and wiring (`Category`, the accessor, `C22ACFFIRSTMIN_100`).
"""
import importlib
import types

import numpy as np
import pandas as pd
import pytest
from pandas import Series

from .context import pandas_ta as ta

_REAL = importlib.import_module("pandas_ta.statistics.c22_acf_first_min")
c22_acf_first_min = _REAL.c22_acf_first_min


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


def _loop_first_min(close, length):
    """The direct sum-of-products autocorrelation of each window's
    returns (no FFT, no vectorisation), then the scan this module's
    `__doc__` spells: the first k in 1 .. length - 2 with
    acf(k - 1) > acf(k) < acf(k + 1), else length."""
    c = close.to_numpy(dtype=float)
    r = c[1:] / c[:-1] - 1
    out = np.full(c.size, np.nan)
    for t in range(length, c.size):
        x = r[t - length:t]
        x = x - x.mean()
        a0 = float(np.dot(x, x))
        acf = [1.0] + [np.dot(x[k:], x[:-k]) / a0 for k in range(1, length)]
        val = float(length)
        for k in range(1, length - 1):
            if acf[k - 1] > acf[k] and acf[k] < acf[k + 1]:
                val = float(k)
                break
        out[t] = val
    return out


# ------------------------------------------------------------ correctness


@pytest.mark.parametrize("length", [5, 10, 100])
def test_matches_an_independent_loop(length):
    close = _ar1(400, seed=2, phi=0.6)
    out = c22_acf_first_min(close, length=length).to_numpy()
    ref = _loop_first_min(close, length)
    np.testing.assert_array_equal(out[length:], ref[length:])


def test_alternating_returns_read_1():
    """Returns +a, -a, ...: acf(0)=1, acf(1)<0, acf(2)>0 -- an immediate
    local minimum at the very first interior lag."""
    r = 0.01 * np.where(np.arange(150) % 2, -1.0, 1.0)
    out = c22_acf_first_min(Series(100 * np.cumprod(np.r_[1.0, 1 + r])))
    assert out.iloc[:100].isna().all()
    assert (out.iloc[100:] == 1).all()


def test_a_deterministic_ramp_reads_one_constant_lag():
    """A linear return ramp's autocorrelation has exactly one interior
    local minimum, at the same lag for every window shape (measured:
    71 at `length` 100) -- a closed deterministic law, not derived from
    the shape of the curve by hand."""
    r = np.linspace(0.02, -0.02, 400)
    out = c22_acf_first_min(Series(100 * np.cumprod(1 + r)), length=100)
    assert out.iloc[100:].notna().all()
    assert (out.iloc[100:] == 71).all()


# --------------------------------------------------------------- causality


MUTANT = ("out[length + a:length + b] = vals",
          "out[length - 1 + a:length - 1 + b] = vals")
OFFSETS = range(130, 600, 30)


def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_c22_acf_first_min_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


def _leaks(fn):
    close = _ar1(seed=11)
    base = fn(close)
    hits = 0
    for j in OFFSETS:
        p = close.copy()
        p.iloc[j:] *= 1e3
        out = fn(p)
        a, b = base.iloc[:j], out.iloc[:j]
        if not (a.isna() == b.isna()).all() or (a[a.notna()] != b[a.notna()]).any():
            hits += 1
    return hits


def test_real_module_never_reads_the_future():
    assert _leaks(c22_acf_first_min) == 0


def test_mutant_is_caught():
    mod = _load_mutant(*MUTANT)
    close = _ar1(seed=11)
    assert not mod.c22_acf_first_min(close).equals(c22_acf_first_min(close))
    assert _leaks(mod.c22_acf_first_min) == len(OFFSETS)


def test_a_bad_tick_moves_only_the_windows_that_hold_it():
    """close x1000 at bar 300 changes the returns at bars 299 and 300,
    which only the windows ending at bars 300..400 can hold -- so any
    bar this column moves must be in that range. Not every window in it
    actually changes VALUE (a big return deep in a 100-lag window often
    does not move which lag is the first local minimum, measured: on
    this frame only 2 of the 101 do), and that count is not pinned
    because it is decided by float comparisons CI's CPU dispatch can
    move."""
    close = _ar1(seed=4)
    base = c22_acf_first_min(close)
    bad = close.copy()
    bad.iloc[300] *= 1e3
    out = c22_acf_first_min(bad)
    moved = np.flatnonzero(~((out == base) | (out.isna() & base.isna())).to_numpy())
    assert moved.size > 0
    assert set(moved.tolist()) <= set(range(300, 401))
    pd.testing.assert_series_equal(out.drop(range(300, 401)), base.drop(range(300, 401)))


# ------------------------------------------------------- the rounding guard


@pytest.mark.parametrize("g", [1e-2, 1e-4, 1e-7, 1e-8, 1e-10])
def test_steady_drift_is_nan_not_rounding_noise(g):
    assert c22_acf_first_min(Series(100 * (1 + g) ** np.arange(300.0))).isna().all()


def test_one_ulp_jitter_is_nan():
    rng = np.random.default_rng(0)
    c = np.full(300, 10.0)
    c[rng.random(300) < 0.5] = np.nextafter(10.0, 20.0)
    assert c22_acf_first_min(Series(c)).isna().all()


def test_the_guard_keeps_very_small_real_returns():
    rng = np.random.default_rng(0)
    rng.standard_normal(300)
    close = Series(100 * np.cumprod(1 + 1e-13 * rng.standard_normal(300)))
    assert c22_acf_first_min(close).iloc[100:].notna().all()


# ------------------------------------------------------------ scale-free


@pytest.mark.parametrize("k", [8.0, 64.0])
def test_price_scale_is_bit_identical(k):
    close = _ar1(seed=4)
    base, scaled = c22_acf_first_min(close), c22_acf_first_min(close * k)
    pd.testing.assert_series_equal(base, scaled, check_exact=True)


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_price_scale_within_tolerance(k):
    close = _ar1(seed=4)
    base, scaled = c22_acf_first_min(close), c22_acf_first_min(close * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] != scaled[m]).mean() <= 0.01


def test_fires_and_is_not_constant():
    out = c22_acf_first_min(_ar1(seed=4))
    assert out.notna().sum() == 500  # 600 bars, first value at bar 100
    v = out.dropna()
    assert v.nunique() > 1
    assert (v == np.round(v)).all() and v.between(1, 100).all()


# ------------------------------------------------------------- edge cases


def test_flat_prices_are_nan():
    assert c22_acf_first_min(Series([10.0] * 150)).isna().all()


@pytest.mark.parametrize("bad", [np.nan, np.inf, 0.0, -1.0, 1e-310])
def test_a_bad_close_blanks_its_windows(bad):
    close = _ar1(300, seed=1)
    base = c22_acf_first_min(close)
    c2 = close.copy()
    c2.iloc[150] = bad
    out = c22_acf_first_min(c2)
    assert out.iloc[150:251].isna().all()
    pd.testing.assert_series_equal(out.drop(range(150, 251)), base.drop(range(150, 251)))


def test_a_return_whose_square_overflows_is_missing_not_inf():
    close = _ar1(300, seed=1)
    base = c22_acf_first_min(close)
    c2 = close.copy()
    c2.iloc[150] = 1e-150
    c2.iloc[151] = 1e150
    out = c22_acf_first_min(c2)
    assert out.iloc[151:251].isna().all()
    assert np.isfinite(out.iloc[150]) and np.isfinite(out.iloc[251])
    pd.testing.assert_series_equal(out.drop(range(150, 252)), base.drop(range(150, 252)))


def test_short_input_and_length_floor():
    close = _ar1(150, seed=1)
    assert c22_acf_first_min(close.iloc[:100]) is None  # 101 closes needed
    assert c22_acf_first_min(close.iloc[:101]).notna().sum() == 1
    assert c22_acf_first_min(close, length=2).name == "C22ACFFIRSTMIN_100"
    assert c22_acf_first_min(close, length=3).notna().sum() == 147


def test_chunk_boundaries_do_not_change_values(monkeypatch):
    close = _ar1(seed=4)
    base = c22_acf_first_min(close)
    monkeypatch.setattr(_REAL, "CHUNK_CELLS", 7 * 100)
    pd.testing.assert_series_equal(c22_acf_first_min(close), base, check_exact=True)


# ---------------------------------------------------------------- wiring


def test_name_registration_and_accessor():
    close = _ar1(200, seed=1)
    df = pd.DataFrame({"open": close, "high": close, "low": close, "close": close, "volume": 1.0})
    assert "c22_acf_first_min" in ta.Category["statistics"]
    out = df.ta.c22_acf_first_min()
    assert out.name == "C22ACFFIRSTMIN_100"
    pd.testing.assert_series_equal(out, c22_acf_first_min(close))
    assert df.ta.c22_acf_first_min(length=50).name == "C22ACFFIRSTMIN_50"


def test_no_shipped_module_imports_pycatch22():
    import ast
    import pathlib
    root = pathlib.Path(_REAL.__file__).resolve().parent.parent
    for path in root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module] if node.module else []
            else:
                continue
            assert not any(n and "pycatch22" in n for n in names), path
