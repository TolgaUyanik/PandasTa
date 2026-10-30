# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.performance.max_return` -- the largest one-bar return
over a rolling window, the "MAX" lottery measure of Bali, Cakici and
Whitelaw (2011). PandasTa issue #12. Measurements and the open gates are in
`docs/MaxReturnMeasured.md`.

What these tests pin, in order of how much it would hurt to lose them:

* CORRECTNESS against the source definition, MAX = the maximum one-bar
  simple return in the window: a pure-Python loop of `(c_i - c_{i-1}) /
  c_{i-1}` differs by at most 1.1e-16 at lengths 21, 5 and 1, and
  `close.pct_change().rolling(length).max()` matches exactly (max |diff|
  0.0). A hand-computed window shows the arithmetic, and a single +10% step
  reads 0.10 on exactly the 21 bars whose window holds it.
* CAUSALITY by future-perturbation: rewrite every close from `j` onward
  (another walk, a x1000 future), demand bars `[0:j]` bit-identical with
  matching NaN masks, over 31 offsets. Two one-bar look-ahead mutants
  (`importlib` source read, `exec`'d in memory) -- the return series read
  one bar ahead, and the output written one bar early -- are each proved
  live, then caught at 31 of 31.
* SCALE-FREE: on the seed-11 walk, close x8 and x64 are bit-identical; x10
  and x3.7 differ by at most 2.2e-16 absolute (asserted <= 1e-14), NaN
  masks match. Not constant: 109 distinct values over the 1,179
  non-warm-up bars (a maximum holds until it leaves the window), range
  0.0090 to 0.0559.
* EDGES: a NaN, zero or negative close removes the two returns that touch
  it, so it blanks 22 bars at the default; the 21-bar warm-up; `offset`,
  `fillna`; `length` below 1 falls back to 21; 21 closes return None.
* Wiring: `Category`, the accessor, the column name `MAXRET_21`.
"""
import importlib
import types

import numpy as np
import pandas as pd
import pytest
from pandas import DataFrame, Series

from .context import pandas_ta as ta
from pandas_ta.performance.max_return import max_return


def _walk(n=1200, seed=11):
    """Tick-rounded geometric random walk around 100."""
    rng = np.random.default_rng(seed)
    return Series(np.round(100 * np.exp(np.cumsum(rng.normal(0, 0.015, n))), 2))


def _reference(close, length):
    """MAX by definition: the largest (c_i - c_{i-1}) / c_{i-1} in the window."""
    c = [float(x) for x in close]
    out = np.full(len(c), np.nan)
    for t in range(length, len(c)):
        out[t] = max((c[i] - c[i - 1]) / c[i - 1] for i in range(t - length + 1, t + 1))
    return out


# ------------------------------------------------------------ correctness


def test_hand_computed():
    # returns: 110/100 - 1 = .1, 99/110 - 1 = -.1, 99/99 - 1 = 0, 108.9/99 - 1 = .1
    # length 3: bar 3 -> max(.1, -.1, 0) = .1;  bar 4 -> max(-.1, 0, .1) = .1
    out = max_return(Series([100.0, 110.0, 99.0, 99.0, 108.9]), length=3)
    assert out.isna().tolist() == [True] * 3 + [False] * 2
    np.testing.assert_allclose(out.values[3:], [0.1, 0.1], rtol=1e-12)


@pytest.mark.parametrize("length", [21, 5, 1])
def test_matches_the_source_definition(length):
    close = _walk(400)
    out = max_return(close, length=length)
    ref = _reference(close, length)
    assert (np.isnan(ref) == out.isna().values).all()
    # measured max |diff| 1.1e-16: one rounding of (c - p) / p vs c / p - 1
    np.testing.assert_allclose(out.values[length:], ref[length:], rtol=0, atol=1e-15)
    pd.testing.assert_series_equal(
        out, close.pct_change().rolling(length).max(), check_names=False)


def test_a_step_is_held_for_exactly_length_bars():
    close = Series(np.full(80, 50.0))
    close[40:] = 55.0
    out = max_return(close)
    assert out[39] == 0.0
    np.testing.assert_allclose(out[40:61].values, np.full(21, 0.1), rtol=1e-12)
    assert (out[61:] == 0.0).all()


def test_missing_or_non_positive_closes_blank_their_windows():
    close = _walk()
    for bad in (np.nan, 0.0, -1.0):
        c = close.copy()
        c[500] = bad
        out = max_return(c)
        # returns 500 and 501 are missing; every window holding either is NaN
        assert out[500:522].isna().all() and out[522:].notna().all()
        assert int(out.isna().sum()) == 21 + 22
        assert np.isinf(out.values).sum() == 0


def test_edge_cases():
    close = _walk()
    base = max_return(close)
    assert int(base.isna().sum()) == 21
    for bad in (0, 0.5, -3):
        assert max_return(close, length=bad).name == "MAXRET_21"
    assert max_return(close, length=5.9).name == "MAXRET_5"
    pd.testing.assert_series_equal(max_return(close, offset=1), base.shift(1))
    assert max_return(close, fillna=0).isna().sum() == 0
    assert max_return(close.iloc[:21]) is None  # needs length + 1 closes
    assert int(max_return(close.iloc[:22]).notna().sum()) == 1


# -------------------------------------------------------------- causality

_REAL = importlib.import_module("pandas_ta.performance.max_return")


def _load_mutant(old, new, tag):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType(f"_max_return_mutant_{tag}")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


MUTANTS = {
    # the return series read one bar ahead: bar T sees r_{T+1}
    "returns": ("ret = np.concatenate(([np.nan], c[1:] / c[:-1] - 1.0))",
                "ret = np.concatenate((c[1:] / c[:-1] - 1.0, [np.nan]))"),
    # the output written one bar early: bar T reports the window ending at T+1
    "write": (".max().to_numpy()", ".max().shift(-1).to_numpy()"),
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
    assert _leaks(max_return) == 0


@pytest.mark.parametrize("tag", sorted(MUTANTS))
def test_mutant_is_caught(tag):
    mod = _load_mutant(*MUTANTS[tag], tag)
    close = _walk()
    assert not mod.max_return(close).equals(max_return(close))
    assert _leaks(mod.max_return) == len(OFFSETS)


# ------------------------------------------------------------ scale-free


@pytest.mark.parametrize("k", [8.0, 64.0])
def test_price_scale_is_bit_identical(k):
    close = _walk()
    base, scaled = max_return(close), max_return(close * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_price_scale_within_tolerance(k):
    close = _walk()
    base, scaled = max_return(close), max_return(close * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    # measured 2.2e-16 absolute (one ulp near 0.01-0.06) on numpy 2.5.4; the
    # bound leaves ~45x headroom for other numpy builds (CI runs 1.26.4)
    assert (scaled[m] - base[m]).abs().max() <= 1e-14


def test_column_is_not_constant():
    out = max_return(_walk())
    m = out.notna()
    assert int(m.sum()) == 1179 and out[m].nunique() == 109
    assert 0.00897 < out.min() < 0.00898 and 0.05585 < out.max() < 0.05586


# ---------------------------------------------------------------- wiring


def test_name_registration_and_accessor():
    close = _walk(300)
    df = DataFrame({"open": close, "high": close, "low": close, "close": close, "volume": 1.0})
    assert "max_return" in ta.Category["performance"]
    out = df.ta.max_return()
    assert out.name == "MAXRET_21"
    pd.testing.assert_series_equal(out, max_return(close))
    assert df.ta.max_return(length=5).name == "MAXRET_5"
