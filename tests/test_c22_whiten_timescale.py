# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.statistics.c22_whiten_timescale` -- catch22's
`FC_LocalSimple_mean1_taurat`: the ratio of two ACF timescales (hctsa's
`CO_FirstZero`, the first LINEARLY INTERPOLATED lag the autocorrelation
crosses zero) over the last `length` daily returns -- the RESIDUAL of a
trivial "forecast the previous point" predictor (the plain first
difference) over the RAW window itself. Measurements are in
`docs/C22WhitenTimescaleMeasured.md`.

What these pin, in order of how much it would hurt to lose:

* CORRECTNESS against the definition: the FFT-based "biased"
  autocorrelation (demeaned once, divisor `length`), plus the linear
  interpolation step, against an independent double loop with no FFT
  and no vectorisation, value for value, at three lengths. Two closed
  forms: alternating returns make BOTH the raw window and its first
  difference cross zero at (nearly) the same interpolated lag-1 point,
  so the ratio reads very close to 1.0 (not EXACTLY 1.0 -- the residual
  series is one point shorter than the raw window, an odd/even parity
  mismatch that the demeaning step can see even on a perfectly
  alternating input); a deterministic linear return RAMP differences to
  a CONSTANT, so its residual series is flat and the column reads NaN
  everywhere -- the opposite of `c22_acf_first_min`'s ramp behaviour
  (that column reads a single non-NaN constant on the same input),
  because that feature never differences the series at all.
* The INTERPOLATION STEP ITSELF was fit against the GPL-3.0 reference
  as a black box (`docs/measure_c22_whiten_timescale.py` section P): an
  earlier, simpler build reporting the bare INTEGER crossing lag read
  exactly 1.0 on every sampled window of a synthetic walk, while
  `pycatch22.catch22_all(...)["FC_LocalSimple_mean1_taurat"]` read a
  tight band around 0.70-0.73 on the SAME windows -- a value no integer
  scan can produce. 0 of 8,400 windows (six frames) disagree with the
  reference beyond 1e-9 after adding the interpolation.
* CAUSALITY: future-perturbation sweep at several offsets, and four
  mutants (the write index moved one bar earlier; the window read one
  or ten bars ahead; the whole return stream rolled back one bar) all
  proved live and caught at every offset tried.
* The rounding guard applies to BOTH series independently: a window
  whose RAW returns are flat is NaN (the same floor and scale as
  `c22_acf_first_min`/`firstzero_ac`), and so is a window whose raw
  returns vary but whose first DIFFERENCE happens to be flat (the ramp
  case above) -- two distinct ways to trip the same rule.
* SCALE-FREE: x8/x64 bit-identical (the price enters only as a ratio);
  x10/x3.7/x0.1/x1.0000001 agree to float noise (worst ~1e-13), even
  though the CONTINUOUS output means most individual bars move by that
  noise rather than staying bit-identical the way a discrete lag would.
* A chunk-size change moves a handful of bars by FFT batch-size float
  noise (~1e-14), not by a meaningful amount -- pinned as a tolerance,
  not exact equality, unlike this module's discrete-output siblings.
* Edge cases (flat, bad closes including subnormal and infinite ones, a
  return whose square overflows, short input, length floor) and wiring
  (`Category`, the accessor, `C22WHITENTIMESCALE_100`).
"""
import importlib
import types

import numpy as np
import pandas as pd
import pytest
from pandas import Series

from .context import pandas_ta as ta

_REAL = importlib.import_module("pandas_ta.statistics.c22_whiten_timescale")
c22_whiten_timescale = _REAL.c22_whiten_timescale


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


def _loop_first_zero(x):
    """Plain double loop, no FFT, no vectorisation: the "biased"
    autocorrelation at every lag, then the smallest k >= 1 with
    acf(k) <= 0, else len(x) -- interpolated linearly between
    (k - 1, acf(k - 1)) and (k, acf(k)), hctsa's `CO_FirstZero`."""
    x = np.asarray(x, dtype=float)
    m = len(x)
    xo = x - x.mean()
    a0 = float(np.dot(xo, xo)) / m
    acf_prev = 1.0
    for k in range(1, m):
        if a0 == 0.0:
            return float(m)
        acf_k = (float(np.dot(xo[k:], xo[:-k])) / m) / a0
        if acf_k <= 0.0:
            return (k - 1) + acf_prev / (acf_prev - acf_k)
        acf_prev = acf_k
    return float(m)


def _loop_whiten_timescale(close, length):
    """The definition re-spelled with `_loop_first_zero`, independently of
    the shipped FFT/chunked implementation."""
    c = close.to_numpy(dtype=float)
    r = c[1:] / c[:-1] - 1
    out = np.full(c.size, np.nan)
    for t in range(length, c.size):
        x = r[t - length:t]
        d = x[1:] - x[:-1]
        sd_x = x.std()
        sd_d = d.std()
        floor = 64 * np.finfo(float).eps * np.abs(1.0 + x).max()
        if sd_x <= floor or sd_d <= floor:
            continue
        out[t] = _loop_first_zero(d) / _loop_first_zero(x)
    return out


# ------------------------------------------------------------ correctness


@pytest.mark.parametrize("length", [5, 10, 100])
def test_matches_an_independent_loop(length):
    close = _ar1(400, seed=2, phi=0.6)
    out = c22_whiten_timescale(close, length=length).to_numpy()
    ref = _loop_whiten_timescale(close, length)
    ok = ~np.isnan(ref[length:])
    assert ok.sum() > 0
    np.testing.assert_allclose(out[length:][ok], ref[length:][ok], atol=1e-9)
    assert np.array_equal(np.isnan(out[length:]), np.isnan(ref[length:]))


def test_alternating_returns_read_a_ratio_very_close_to_one():
    """Returns +a, -a, ...: acf(1) is very close to -1 for the raw window
    (an immediate, interpolated lag-1 zero crossing near 0.5), and its
    first difference crosses at nearly the same point -- so the ratio is
    very close to 1.0, but not EXACTLY 1.0: the residual series has one
    fewer point than the raw window (99 vs 100, an odd/even parity
    mismatch), so demeaning each series leaves a slightly different
    residual mean even on an otherwise perfectly alternating input."""
    r = 0.01 * np.where(np.arange(150) % 2, -1.0, 1.0)
    out = c22_whiten_timescale(Series(100 * np.cumprod(np.r_[1.0, 1 + r])))
    assert out.iloc[:100].isna().all()
    assert out.iloc[100:].notna().all()
    assert np.allclose(out.iloc[100:].to_numpy(), 1.0, atol=1e-3)
    assert not (out.iloc[100:] == 1.0).all()  # close, but not exact -- see above


def test_a_deterministic_ramp_differences_to_a_constant_and_blanks():
    """A linear return ramp's first DIFFERENCE is a constant step (every
    entry of `np.linspace` is equally spaced), so the residual series has
    no variation to read an autocorrelation from and the whole column
    blanks under the floor rule -- unlike `c22_acf_first_min`, which never
    differences the series and reads a single non-NaN constant (71) on
    the same input."""
    r = np.linspace(0.02, -0.02, 400)
    out = c22_whiten_timescale(Series(100 * np.cumprod(1 + r)), length=100)
    assert out.iloc[100:].isna().all()


# --------------------------------------------------------------- causality


MUTANTS = {
    "write-back-dated": ("out[length + a:length + b] = vals",
                         "out[length - 1 + a:length - 1 + b] = vals"),
    "window-one-ahead": ("win = sliding_window_view(r, length)",
                         "win = sliding_window_view(r, length + 1)[:, 1:]"),
    "window-ten-ahead": ("win = sliding_window_view(r, length)",
                         "win = sliding_window_view(r, length + 10)[:, 10:]"),
    "returns-rolled": ("r[~np.isfinite(r * r)] = np.nan",
                       "r[~np.isfinite(r * r)] = np.nan\n    r = np.roll(r, -1)"),
}
OFFSETS = range(130, 600, 30)


def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_c22_whiten_timescale_mutant")
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
    assert _leaks(c22_whiten_timescale) == 0


@pytest.mark.parametrize("name", list(MUTANTS))
def test_each_mutant_is_caught(name):
    mod = _load_mutant(*MUTANTS[name])
    close = _ar1(seed=11)
    assert not mod.c22_whiten_timescale(close).equals(c22_whiten_timescale(close))
    assert _leaks(mod.c22_whiten_timescale) == len(OFFSETS)


def test_a_bad_tick_moves_only_the_windows_that_hold_it():
    close = _ar1(seed=4)
    base = c22_whiten_timescale(close)
    bad = close.copy()
    bad.iloc[300] *= 1e3
    out = c22_whiten_timescale(bad)
    moved = np.flatnonzero(~((out == base) | (out.isna() & base.isna())).to_numpy())
    assert moved.size > 0
    assert set(moved.tolist()) <= set(range(300, 401))
    pd.testing.assert_series_equal(out.drop(range(300, 401)), base.drop(range(300, 401)))


# ------------------------------------------------------- the rounding guard


@pytest.mark.parametrize("g", [1e-2, 1e-4, 1e-7, 1e-8, 1e-10])
def test_steady_drift_is_nan_not_rounding_noise(g):
    """A constant-return drift is flat on BOTH the raw window and its
    (zero) residual."""
    assert c22_whiten_timescale(Series(100 * (1 + g) ** np.arange(300.0))).isna().all()


def test_one_ulp_jitter_is_nan():
    rng = np.random.default_rng(0)
    c = np.full(300, 10.0)
    c[rng.random(300) < 0.5] = np.nextafter(10.0, 20.0)
    assert c22_whiten_timescale(Series(c)).isna().all()


def test_the_guard_keeps_very_small_real_returns():
    rng = np.random.default_rng(0)
    close = Series(100 * np.cumprod(1 + 1e-10 * rng.standard_normal(300)))
    assert c22_whiten_timescale(close).iloc[100:].notna().any()


# ------------------------------------------------------------ scale-free


@pytest.mark.parametrize("k", [8.0, 64.0])
def test_price_scale_is_bit_identical(k):
    close = _ar1(seed=4)
    base, scaled = c22_whiten_timescale(close), c22_whiten_timescale(close * k)
    pd.testing.assert_series_equal(base, scaled, check_exact=True)


@pytest.mark.parametrize("k", [10.0, 3.7, 0.1, 1.0000001])
def test_price_scale_within_tolerance(k):
    """Not bit-identical by construction -- the output is a CONTINUOUS
    interpolated ratio, so an inexact rescale moves most individual bars
    by float noise even though the value is unchanged in exact real
    arithmetic (each series' own ACF already normalises by its own
    variance). The bound is a magnitude tolerance, not a moved-fraction
    one."""
    close = _ar1(seed=4)
    base, scaled = c22_whiten_timescale(close), c22_whiten_timescale(close * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert float(np.max(np.abs(base[m].to_numpy() - scaled[m].to_numpy()))) < 1e-6


def test_fires_and_is_not_constant():
    out = c22_whiten_timescale(_ar1(seed=4))
    assert int(out.notna().sum()) == 500  # 600 bars, first value at bar 100
    v = out.dropna()
    assert v.nunique() > 1


# ------------------------------------------------------------- edge cases


def test_flat_prices_are_nan():
    assert c22_whiten_timescale(Series([10.0] * 150)).isna().all()


@pytest.mark.parametrize("bad", [np.nan, np.inf, 0.0, -1.0, 1e-310])
def test_a_bad_close_blanks_its_windows(bad):
    close = _ar1(300, seed=1)
    base = c22_whiten_timescale(close)
    c2 = close.copy()
    c2.iloc[150] = bad
    out = c22_whiten_timescale(c2)
    assert out.iloc[150:251].isna().all()
    pd.testing.assert_series_equal(out.drop(range(150, 251)), base.drop(range(150, 251)))


def test_a_return_whose_square_overflows_is_missing_not_inf():
    close = _ar1(300, seed=1)
    base = c22_whiten_timescale(close)
    c2 = close.copy()
    c2.iloc[150] = 1e-150
    c2.iloc[151] = 1e150
    out = c22_whiten_timescale(c2)
    assert out.iloc[151:251].isna().all()
    assert np.isfinite(out.iloc[150]) and np.isfinite(out.iloc[251])
    pd.testing.assert_series_equal(out.drop(range(150, 252)), base.drop(range(150, 252)))


def test_short_input_and_length_floor():
    close = _ar1(150, seed=1)
    assert c22_whiten_timescale(close.iloc[:100]) is None  # 101 closes needed
    assert c22_whiten_timescale(close.iloc[:101]).notna().sum() <= 1
    assert c22_whiten_timescale(close, length=2).name == "C22WHITENTIMESCALE_100"
    assert c22_whiten_timescale(close, length=3).name == "C22WHITENTIMESCALE_100"
    assert c22_whiten_timescale(close, length=_REAL.MIN_LENGTH).name == \
        f"C22WHITENTIMESCALE_{_REAL.MIN_LENGTH}"


def test_chunk_boundaries_move_values_by_float_noise_only(monkeypatch):
    """Unlike this module's discrete-lag siblings (`c22_acf_first_min`,
    `firstzero_ac`), the output here is a CONTINUOUS interpolated ratio,
    so the FFT's own batch-size-dependent rounding can move a handful of
    bars by machine noise when the chunk boundary moves (measured:
    `docs/measure_c22_whiten_timescale.py` section Y, worst |diff|
    5.6e-17 on that frame) -- a tolerance, not exact equality."""
    close = _ar1(seed=4)
    base = c22_whiten_timescale(close)
    monkeypatch.setattr(_REAL, "CHUNK_CELLS", 7 * 100)
    got = c22_whiten_timescale(close)
    assert (base.isna() == got.isna()).all()
    m = base.notna()
    assert float(np.max(np.abs(base[m].to_numpy() - got[m].to_numpy()))) < 1e-9


def test_the_offset_and_the_fill_are_the_house_ones():
    close = _ar1(seed=4)
    base = c22_whiten_timescale(close)
    shifted = c22_whiten_timescale(close, offset=2)
    pd.testing.assert_series_equal(shifted.iloc[2:].reset_index(drop=True),
                                   base.iloc[:-2].reset_index(drop=True),
                                   check_exact=True)
    filled = c22_whiten_timescale(close, fillna=-99)
    assert int(filled.isna().sum()) == 0
    assert int((base.isna() & (filled == -99)).sum()) == int(base.isna().sum())


# ---------------------------------------------------------------- wiring


def test_name_registration_and_accessor():
    close = _ar1(200, seed=1)
    df = pd.DataFrame({"open": close, "high": close, "low": close, "close": close, "volume": 1.0})
    assert "c22_whiten_timescale" in ta.Category["statistics"]
    out = df.ta.c22_whiten_timescale()
    assert out.name == "C22WHITENTIMESCALE_100"
    pd.testing.assert_series_equal(out, c22_whiten_timescale(close))
    assert df.ta.c22_whiten_timescale(length=50).name == "C22WHITENTIMESCALE_50"


def test_the_module_docstring_attributes_the_source():
    doc = c22_whiten_timescale.__doc__
    for needle in ("Lubba", "33:1821", "FC_LocalSimple", "GPL-3.0", "#139"):
        assert needle in doc, needle
    assert "classification" in doc.lower()
    assert "existence" in doc and "not evidence" in doc


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
