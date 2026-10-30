# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.statistics.kpss` -- the KPSS trend-stationarity
statistic of log price over a rolling window (`regression="ct"`, one
Bartlett lag), as Kats tsfeatures computes it. PandasTa issue #157.
Measurements and the open gates are in `docs/KpssMeasured.md`.

What these tests pin, in order of how much it would hurt to lose them:

* CORRECTNESS against the source. `statsmodels.tsa.stattools.kpss(x,
  regression="ct", nlags=1)` -- the exact call Kats makes -- on every window
  of an 800-bar walk: max relative difference 2.2e-12 at length 100, 1.0e-12
  at length 30. statsmodels is not a CI dependency, so that test skips
  there; an independent `lstsq` loop written from the paper's equations 10-11
  runs everywhere, and so does a hand-computed window whose arithmetic is
  shown (`[0, 1, 0, 2]` -> 0.25).
* CAUSALITY by future-perturbation: rewrite every close from `j` onward
  (another walk, a x1000 future), demand bars `[0:j]` bit-identical with
  matching NaN masks, over 31 offsets. Two one-bar look-ahead mutants
  (`importlib` source read, `exec`'d in memory) -- the output written one bar
  early, and the window read one bar ahead -- are each proved live, then
  caught at 31 of 31.
* SCALE-FREE: on the seed-11 walk, close x8 and x64 are bit-identical, x10
  and x3.7 differ by at most 1.1e-14 and 8.6e-15 relative, NaN masks match.
  Not constant: 1,101 distinct values over the 1,101 non-warm-up bars, range
  0.0865 to 1.0744, none zero.
* WHAT IT MEASURES: over 200 synthetic 100-bar windows each, a random walk
  reads median 0.599 and exceeds the 5% critical value 0.146 in 200 of 200;
  an AR(0.5) around a linear trend reads median 0.112. That AR(0.5) still
  exceeds 0.146 in 33% of windows: one Bartlett lag under-corrects that much
  autocorrelation, a property of the source formula, not of this port.
* EDGES: a flat window and a non-positive close are NaN, never inf; a NaN
  close blanks its own bar and the next `length - 1` (100 bars at the
  default); the 99-bar warm-up; `offset`, `fillna`.
* Wiring: `Category`, the accessor, the column name `KPSS_100`.
"""
import importlib
import types

import numpy as np
import pandas as pd
import pytest
from pandas import DataFrame, Series

from .context import pandas_ta as ta
from pandas_ta.statistics.kpss import kpss


def _walk(n=1200, seed=11):
    """Tick-rounded geometric random walk around 100."""
    rng = np.random.default_rng(seed)
    return Series(np.round(100 * np.exp(np.cumsum(rng.normal(0, 0.015, n))), 2))


def _reference(close, length):
    """Kwiatkowski et al. (1992) eqs. 10-11 with one lag, by `lstsq` per window."""
    lc = np.log(np.asarray(close, dtype=float))
    out = np.full(len(lc), np.nan)
    design = np.column_stack([np.ones(length), np.arange(1, length + 1)])
    for end in range(length - 1, len(lc)):
        y = lc[end - length + 1:end + 1]
        e = y - design @ np.linalg.lstsq(design, y, rcond=None)[0]
        eta = np.sum(np.cumsum(e) ** 2) / length ** 2
        s2 = (np.sum(e ** 2) + 2 * (1 - 1 / 2) * np.dot(e[1:], e[:-1])) / length
        out[end] = eta / s2
    return out


# ------------------------------------------------------------ correctness


def test_hand_computed():
    # close = exp([0, 1, 0, 2]) -> x = [0, 1, 0, 2], t centred = [-1.5, -.5, .5, 1.5]
    # mean .75 -> xc = [-.75, .25, -.75, 1.25]; slope = sum(xc*t)/sum(t^2) = 2.5/5 = .5
    # e = xc - .5t = [0, .5, -1, .5]; cumsum = [0, .5, -.5, 0] -> eta = .5/16 = 1/32
    # s2 = (sum e^2 = 1.5  +  e1e0 + e2e1 + e3e2 = 0 - .5 - .5 = -1) / 4 = 1/8
    # KPSS = (1/32) / (1/8) = 0.25
    out = kpss(Series(np.exp([0.0, 1.0, 0.0, 2.0])), length=4)
    assert out.isna().tolist() == [True] * 3 + [False]
    assert out.iloc[3] == pytest.approx(0.25, rel=1e-12)


@pytest.mark.parametrize("length", [100, 30])
def test_matches_statsmodels_the_source_call(length):
    st = pytest.importorskip("statsmodels.tsa.stattools")
    import warnings

    rng = np.random.default_rng(3)
    close = Series(100 * np.exp(np.cumsum(rng.normal(0, 0.015, 800))))
    lc = np.log(close.values)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # p-value interpolation warnings
        ref = np.array([st.kpss(lc[i - length + 1:i + 1], regression="ct", nlags=1)[0]
                        for i in range(length - 1, len(lc))])
    out = kpss(close, length=length)
    assert out.iloc[:length - 1].isna().all()
    np.testing.assert_allclose(out.values[length - 1:], ref, rtol=1e-10)


@pytest.mark.parametrize("length", [100, 30, 3])
def test_matches_an_independent_loop(length):
    close = _walk(400)
    out = kpss(close, length=length)
    ref = _reference(close, length)
    assert (np.isnan(ref) == out.isna().values).all()
    np.testing.assert_allclose(out.values[length - 1:], ref[length - 1:], rtol=1e-9)


def test_separates_a_random_walk_from_a_trend_stationary_series():
    rng = np.random.default_rng(5)
    stationary, walk = [], []
    for _ in range(200):
        e = rng.normal(0, 0.01, 100)
        ar = np.zeros(100)
        for j in range(1, 100):
            ar[j] = 0.5 * ar[j - 1] + e[j]
        stationary.append(kpss(Series(100 * np.exp(ar + 0.001 * np.arange(100)))).iloc[-1])
        walk.append(kpss(Series(100 * np.exp(np.cumsum(rng.normal(0, 0.01, 100))))).iloc[-1])
    stationary, walk = np.array(stationary), np.array(walk)
    assert 0.112 < np.median(stationary) < 0.1123
    assert 0.599 < np.median(walk) < 0.5991
    assert (walk > 0.146).sum() == 200
    # one Bartlett lag is oversized under AR(0.5): measured 33%, not the nominal 5%
    assert (stationary > 0.146).mean() == pytest.approx(0.33)


def test_flat_or_non_positive_windows_are_nan_not_inf():
    flat = kpss(Series([50.0] * 120 + list(50.0 + np.arange(1, 21) * 0.37)))
    assert flat.iloc[99:120].isna().all()
    assert np.isfinite(flat.iloc[120:]).all()
    close = _walk(300)
    for bad in (0.0, -1.0):
        c = close.copy()
        c[150] = bad
        out = kpss(c)
        assert out[150:250].isna().all() and out[250:].notna().all()
    assert np.isinf(kpss(_walk()).values).sum() == 0


def test_edge_cases():
    close = _walk()
    base = kpss(close)
    assert int(base.isna().sum()) == 99
    cn = close.copy()
    cn[500] = np.nan
    gap = kpss(cn)
    assert gap[500:600].isna().all() and gap[600:].notna().all()
    assert int(gap.isna().sum()) == 99 + 100
    assert kpss(close, length=2).name == "KPSS_100"  # length must exceed 2
    pd.testing.assert_series_equal(kpss(close, offset=1), base.shift(1))
    assert kpss(close, fillna=0).isna().sum() == 0
    assert kpss(close.iloc[:50]) is None  # shorter than the window


# -------------------------------------------------------------- causality

_REAL = importlib.import_module("pandas_ta.statistics.kpss")


def _load_mutant(old, new, tag):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType(f"_kpss_mutant_{tag}")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


MUTANTS = {
    # the write index moved one bar earlier: bar T reports the window ending at T+1
    "write": ("values[length - 1:] = stat", "values[length - 2:-1] = stat"),
    # the window read one bar ahead
    "window": ("win = sliding_window_view(c, length)",
               "win = sliding_window_view(np.append(c[1:], np.nan), length)"),
}

OFFSETS = range(110, 1150, 34)  # 31 offsets


def _moved(a, b):
    if not (a.isna() == b.isna()).all():
        return True
    m = a.notna()
    return bool((a[m] != b[m]).any())


def _leaks(fn):
    """Count offsets `j` at which rewriting closes >= j moves any bar < j."""
    close = _walk()
    base = fn(close)
    other = _walk(seed=99)
    hits = 0
    for j in OFFSETS:
        for future in (other.iloc[j:].values, close.iloc[j:].values * 1000.0):
            pc = close.copy()
            pc.iloc[j:] = future
            if _moved(base.iloc[:j], fn(pc).iloc[:j]):
                hits += 1
                break
    return hits


def test_real_module_never_reads_the_future():
    assert _leaks(kpss) == 0


@pytest.mark.parametrize("tag", sorted(MUTANTS))
def test_mutant_is_caught(tag):
    mod = _load_mutant(*MUTANTS[tag], tag)
    close = _walk()
    assert not mod.kpss(close).equals(kpss(close))
    assert _leaks(mod.kpss) == len(OFFSETS)


# ------------------------------------------------------------ scale-free


@pytest.mark.parametrize("k", [8.0, 64.0])
def test_price_scale_is_bit_identical(k):
    close = _walk()
    base, scaled = kpss(close), kpss(close * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("k, bound", [(10.0, 1.1e-14), (3.7, 8.6e-15)])
def test_price_scale_within_tolerance(k, bound):
    close = _walk()
    base, scaled = kpss(close), kpss(close * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    # the bounds the docstring and KpssMeasured.md quote (measured 1.08e-14 / 8.54e-15)
    assert ((scaled[m] - base[m]).abs() / base[m].abs()).max() <= bound


def test_column_is_not_constant():
    out = kpss(_walk())
    m = out.notna()
    assert int(m.sum()) == 1101 and out[m].nunique() == 1101
    assert int((out[m] == 0).sum()) == 0
    assert 0.0865 < out.min() < 0.0866 and 1.0743 < out.max() < 1.0744


# ---------------------------------------------------------------- wiring


def test_name_registration_and_accessor():
    close = _walk(300)
    df = DataFrame({"open": close, "high": close, "low": close, "close": close, "volume": 1.0})
    assert "kpss" in ta.Category["statistics"]
    out = df.ta.kpss()
    assert out.name == "KPSS_100"
    pd.testing.assert_series_equal(out, kpss(close))
    assert df.ta.kpss(length=30).name == "KPSS_30"
