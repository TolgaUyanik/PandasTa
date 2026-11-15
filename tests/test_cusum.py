# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.statistics.cusum` -- the Chu-Stinchcombe-White CUSUM
statistic on log price (Lopez de Prado, AFML ch. 17), with the supremum
taken over a rolling window of reference bars. PandasTa issue #16.
Measurements and the open gates are in `docs/CusumMeasured.md`.

What these tests pin, in order of how much it would hurt to lose them:

* CORRECTNESS against the source formula. There is no public reference
  implementation to run, so the source is AFML's formula written literally:
  `S_{n,t} = (y_t - y_n) / (sigma_t * sqrt(t - n))`, `sigma_t^2` the mean
  squared one-bar change of `y = log close`, `S_t = max_n S_{n,t}`, as nested
  Python loops on log levels, per window. Max absolute difference 4.7e-14
  at length 100, 4.8e-14 at 30, 5.5e-13 at 2. A hand-computed window
  (`exp([0, 1, 0, 2])`, length 3 -> sqrt(2)) shows the arithmetic.
* CAUSALITY by future-perturbation: rewrite every close from `j` onward
  (another walk, a x1000 future), demand bars `[0:j]` bit-identical with
  matching NaN masks, over 31 offsets. Two one-bar look-ahead mutants
  (`importlib` source read, `exec`'d in memory) -- the output written one bar
  early, and the window read one bar ahead -- are each proved live, then
  caught at 31 of 31.
* SCALE-FREE: on the seed-11 walk, close x8 and x64 are bit-identical; x10
  and x3.7 differ by at most 1.6e-14 and 1.7e-14 absolute (asserted
  <= 1e-12), NaN masks match. Not constant: 1,100 distinct values over the
  1,100 non-warm-up bars, range -0.737 to 3.771, 27 negative, none zero.
* BOUNDED: by Cauchy-Schwarz, |CUSUM| <= sqrt(length). A flat window
  followed by one move hits the bound exactly (10.0 at length 100); 80
  walks at lengths 2, 5, 30, 100 never exceed it.
* WHAT IT MEASURES: 200 pairs of 101-bar walks sharing their noise, one
  with +0.5% per bar added to its last 20 returns: medians 1.349 (no break)
  and 2.823 (break), and the break reads higher in 200 of 200 pairs.
* EDGES: a flat window and a non-positive close are NaN, never inf; a NaN
  close blanks its own bar and the next `length` (101 bars at the default);
  the 100-bar warm-up; `offset`, `fillna`; `length` below 2 falls back to
  100.
* Wiring: `Category`, the accessor, the column name `CUSUM_100`.
"""
import importlib
import types

import numpy as np
import pandas as pd
import pytest
from pandas import DataFrame, Series

from .context import pandas_ta as ta
from pandas_ta.statistics.cusum import cusum


def _walk(n=1200, seed=11):
    """Tick-rounded geometric random walk around 100."""
    rng = np.random.default_rng(seed)
    return Series(np.round(100 * np.exp(np.cumsum(rng.normal(0, 0.015, n))), 2))


def _reference(close, length):
    """AFML's S_{n,t} and its supremum, literally, on log levels, per window."""
    y = np.log(np.asarray(close, dtype=float))
    out = np.full(len(y), np.nan)
    for t in range(length, len(y)):
        dy = [y[i] - y[i - 1] for i in range(t - length + 1, t + 1)]
        sigma = np.sqrt(sum(d * d for d in dy) / length)
        out[t] = max((y[t] - y[n]) / (sigma * np.sqrt(t - n)) for n in range(t - length, t))
    return out


# ------------------------------------------------------------ correctness


def test_hand_computed():
    # close = exp([0, 1, 0, 2]) -> y = [0, 1, 0, 2], length 3 at t = 3
    # returns 1, -1, 2 -> sigma^2 = (1 + 1 + 4) / 3 = 2
    # n = 0: (2 - 0) / (sqrt2 * sqrt3) = 0.816;  n = 1: (2 - 1) / (sqrt2 * sqrt2) = 0.5
    # n = 2: (2 - 0) / (sqrt2 * 1) = sqrt2  -> max = sqrt2
    out = cusum(Series(np.exp([0.0, 1.0, 0.0, 2.0])), length=3)
    assert out.isna().tolist() == [True] * 3 + [False]
    assert out.iloc[3] == pytest.approx(np.sqrt(2), rel=1e-12)


@pytest.mark.parametrize("length", [100, 30, 2])
def test_matches_the_source_formula(length):
    close = _walk(400)
    out = cusum(close, length=length)
    ref = _reference(close, length)
    assert (np.isnan(ref) == out.isna().values).all()
    # measured max |diff| 5.5e-13 (length 2): log of a ratio vs a difference of logs
    np.testing.assert_allclose(out.values[length:], ref[length:], rtol=1e-9, atol=1e-11)


def test_bounded_by_sqrt_length():
    # |y_t - y_n| <= sqrt(t - n) * sqrt(sum r^2) = sqrt(t - n) * sqrt(length) * sigma
    for length in (2, 5, 30, 100):
        for seed in range(20):
            out = cusum(_walk(600, seed), length=length).dropna()
            assert out.abs().max() <= np.sqrt(length) * (1 + 1e-12)
    # flat, then one move r: sigma = |r| / sqrt(length), so n = T - 1 gives exactly sqrt(length)
    jump = cusum(Series([50.0] * 120 + [50.37]))
    assert jump.iloc[-1] == pytest.approx(10.0, rel=1e-12)


def test_rises_after_an_upward_break():
    rng = np.random.default_rng(5)
    pure, brk = [], []
    for _ in range(200):
        e = rng.normal(0, 0.01, 101)
        pure.append(cusum(Series(100 * np.exp(np.cumsum(e)))).iloc[-1])
        d = e.copy()
        d[-20:] += 0.005
        brk.append(cusum(Series(100 * np.exp(np.cumsum(d)))).iloc[-1])
    pure, brk = np.array(pure), np.array(brk)
    assert 1.349 < np.median(pure) < 1.3494
    assert 2.823 < np.median(brk) < 2.8235
    assert (brk > pure).sum() == 200


def test_flat_or_non_positive_windows_are_nan_not_inf():
    flat = cusum(Series([50.0] * 120 + list(50.0 + np.arange(1, 21) * 0.37)))
    assert flat.iloc[100:120].isna().all()
    assert np.isfinite(flat.iloc[120:]).all()
    close = _walk(300)
    for bad in (0.0, -1.0):
        c = close.copy()
        c[150] = bad
        out = cusum(c)
        assert out[150:251].isna().all() and out[251:].notna().all()
    assert np.isinf(cusum(_walk()).values).sum() == 0


def test_edge_cases():
    close = _walk()
    base = cusum(close)
    assert int(base.isna().sum()) == 100
    cn = close.copy()
    cn[500] = np.nan
    gap = cusum(cn)
    # the window is length + 1 closes, so one NaN blanks 101 bars
    assert gap[500:601].isna().all() and gap[601:].notna().all()
    assert int(gap.isna().sum()) == 100 + 101
    for bad in (1, 1.9):
        assert cusum(close, length=bad).name == "CUSUM_100"
    assert cusum(close, length=2.9).name == "CUSUM_2"
    pd.testing.assert_series_equal(cusum(close, offset=1), base.shift(1))
    assert cusum(close, fillna=0).isna().sum() == 0
    assert cusum(close.iloc[:100]) is None  # needs length + 1 closes


# -------------------------------------------------------------- causality

_REAL = importlib.import_module("pandas_ta.statistics.cusum")


def _load_mutant(old, new, tag):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType(f"_cusum_mutant_{tag}")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


MUTANTS = {
    # the write index moved one bar earlier: bar T reports the window ending at T+1
    "write": ("values[length:] = stat", "values[length - 1:-1] = stat"),
    # the window read one bar ahead
    "window": ("win = sliding_window_view(c, length + 1)",
               "win = sliding_window_view(np.append(c[1:], np.nan), length + 1)"),
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
    assert _leaks(cusum) == 0


@pytest.mark.parametrize("tag", sorted(MUTANTS))
def test_mutant_is_caught(tag):
    mod = _load_mutant(*MUTANTS[tag], tag)
    close = _walk()
    assert not mod.cusum(close).equals(cusum(close))
    assert _leaks(mod.cusum) == len(OFFSETS)


# ------------------------------------------------------------ scale-free


@pytest.mark.parametrize("k", [8.0, 64.0])
def test_price_scale_is_bit_identical(k):
    close = _walk()
    base, scaled = cusum(close), cusum(close * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_price_scale_within_tolerance(k):
    close = _walk()
    base, scaled = cusum(close), cusum(close * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    # measured 1.6e-14 (x10) and 1.7e-14 (x3.7) absolute on numpy 2.5.4. Absolute,
    # not relative: the column crosses zero, where a relative error is unbounded.
    # The bound leaves ~60x headroom for other numpy builds (CI runs 1.26.4).
    assert (scaled[m] - base[m]).abs().max() <= 1e-12


def test_column_is_not_constant():
    out = cusum(_walk())
    m = out.notna()
    assert int(m.sum()) == 1100 and out[m].nunique() == 1100
    assert int((out[m] == 0).sum()) == 0 and int((out[m] < 0).sum()) == 27
    assert -0.7375 < out.min() < -0.7374 and 3.7712 < out.max() < 3.7713


# ---------------------------------------------------------------- wiring


def test_name_registration_and_accessor():
    close = _walk(300)
    df = DataFrame({"open": close, "high": close, "low": close, "close": close, "volume": 1.0})
    assert "cusum" in ta.Category["statistics"]
    out = df.ta.cusum()
    assert out.name == "CUSUM_100"
    pd.testing.assert_series_equal(out, cusum(close))
    assert df.ta.cusum(length=30).name == "CUSUM_30"
