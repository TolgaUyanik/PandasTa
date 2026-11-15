# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.performance.seas` -- Heston-Sadka annual-lag
seasonality: the return over the next `length` bars, measured `years`
trading years (252 bars each) ago, averaged. PandasTa issue #27.
Measurements and the open Gate E are in `docs/SeasMeasured.md`.

ASSUMPTIONS (no owner answer available; smaller-scope reading per the
issue-solver rules): `years` defaults to 1 (Quantpedia's own version, the
issue's T2 citation), not 5. The window is bar-count (252 bars), not
`DatetimeIndex`-anchored -- the issue flags BIST holidays as a risk but
calls a date-anchored version a separate design needing a `DatetimeIndex`,
which is the larger-scope option.

What these tests pin, in order of how much it would hurt to lose them:

* CAUSALITY by future-perturbation: rewrite every close from `j` onward
  (another walk, a x1000 future), demand bars `[0:j]` bit-identical with
  matching NaN masks, over 31 offsets. Two look-ahead mutants (`importlib`
  source read, one shift index pushed negative so it reads a future bar,
  `exec`'d in memory) are each proved live, then caught at 31 of 31.
* CORRECTNESS: a hand-built close series isolates the two closes a single
  bar's r_1 reads, and a second isolates y=1 and y=2 together for
  `years=2`; both check against the formula by hand. A longer walk is
  checked against an independent Python loop for `years=1` and `years=2`.
* The `length > 252` guard: at `years=1` that would read a bar after T, so
  it raises instead of silently producing a look-ahead column.
* SCALE-FREE: bit-identical under x8 and x64 (a price ratio, exact under a
  power of two), within 1e-12 under x10 and x3.7 with matching NaN masks,
  plus `0 < fires < n` so a constant column cannot pass.
* Wiring: `Category`, the accessor, the column name `SEAS_21_1`.
"""
import importlib
import types

import numpy as np
import pandas as pd
import pytest
from pandas import DataFrame, Series

from .context import pandas_ta as ta
from pandas_ta.performance.seas import seas

YEAR = 252


def _walk(n=1200, seed=11, sigma=0.015):
    """Tick-rounded geometric random walk around 100."""
    rng = np.random.default_rng(seed)
    return Series(np.round(100 * np.exp(np.cumsum(rng.normal(0, sigma, n))), 2))


# ------------------------------------------------------------ correctness


def test_hand_computed_single_year():
    # Only close[0] (T - 252) and close[21] (T - 252 + 21) matter for bar 252.
    close = Series([1.0] * 253)
    close[0] = 100.0
    close[21] = 110.0
    out = seas(close, length=21, years=1)
    assert out.iloc[:252].isna().all()
    assert out.iloc[252] == pytest.approx(0.10, abs=1e-12)


def test_hand_computed_two_years():
    close = Series([1.0] * (2 * YEAR + 1))
    T = 2 * YEAR
    close[T - YEAR] = 100.0          # y=1 denominator
    close[T - YEAR + 21] = 110.0     # y=1 numerator -> r_1 = 0.10
    close[T - 2 * YEAR] = 50.0       # y=2 denominator
    close[T - 2 * YEAR + 21] = 40.0  # y=2 numerator -> r_2 = -0.20
    out = seas(close, length=21, years=2)
    assert out.iloc[:T].isna().all()
    assert out.iloc[T] == pytest.approx((0.10 - 0.20) / 2, abs=1e-12)


@pytest.mark.parametrize("years", [1, 2])
def test_matches_an_independent_loop(years):
    close = _walk(900)
    length = 21
    c = close.values
    n = len(c)
    ref = np.full(n, np.nan)
    for t in range(years * YEAR, n):
        rs = [c[t - y * YEAR + length] / c[t - y * YEAR] - 1.0 for y in range(1, years + 1)]
        ref[t] = sum(rs) / years
    out = seas(close, length=length, years=years)
    assert (np.isnan(ref) == out.isna().values).all()
    np.testing.assert_allclose(out.values[years * YEAR:], ref[years * YEAR:], rtol=0, atol=1e-9)


def test_length_above_one_year_raises():
    close = _walk(900)
    with pytest.raises(ValueError):
        seas(close, length=253, years=1)
    seas(close, length=252, years=1)  # the boundary itself is fine


def test_edge_cases():
    close = _walk()
    base = seas(close)
    assert base.name == "SEAS_21_1"
    assert int(base.isna().sum()) == YEAR
    for bad in (0, 0.5, -3):
        assert seas(close, length=bad).name == "SEAS_21_1"
    for bad in (0, 0.5, -3):
        assert seas(close, years=bad).name == "SEAS_21_1"
    assert seas(close, length=5.9).name == "SEAS_5_1"
    assert seas(close, years=2.9).name == "SEAS_21_2"
    pd.testing.assert_series_equal(seas(close, offset=1), base.shift(1))
    assert seas(close, fillna=0).isna().sum() == 0
    assert seas(close.iloc[:YEAR]) is None  # needs years*252 + 1 closes
    assert int(seas(close.iloc[:YEAR + 1]).notna().sum()) == 1


# -------------------------------------------------------------- causality

_REAL = importlib.import_module("pandas_ta.performance.seas")


def _load_mutant(old, new, tag):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType(f"_seas_mutant_{tag}")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


MUTANTS = {
    # numerator shift pushed negative: at y=1, shift(231) -> shift(231 - 252) = shift(-21), a future bar
    "numerator": ("close.shift(lag - length)", "close.shift(lag - length - year_bars)"),
    # denominator shift pushed negative: at y=1, shift(252) -> shift(252 - 504) = shift(-252), a future bar
    "denominator": ("close.shift(lag) - 1)", "close.shift(lag - 2 * year_bars) - 1)"),
}

OFFSETS = range(260, 1150, 29)  # 31 offsets, all past the 252-bar warm-up


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
    assert _leaks(seas) == 0


@pytest.mark.parametrize("tag", sorted(MUTANTS))
def test_mutant_is_caught(tag):
    mod = _load_mutant(*MUTANTS[tag], tag)
    close = _walk()
    assert not mod.seas(close).equals(seas(close))  # live
    assert _leaks(mod.seas) == len(OFFSETS)          # caught, 31 of 31


# ------------------------------------------------------------ scale-free


@pytest.mark.parametrize("k", [8.0, 64.0])
def test_price_scale_is_bit_identical(k):
    close = _walk()
    base, scaled = seas(close), seas(close * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_price_scale_within_tolerance(k):
    close = _walk()
    base, scaled = seas(close), seas(close * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (scaled[m] - base[m]).abs().max() < 1e-12


def test_column_is_not_constant():
    out = seas(_walk())
    m = out.notna()
    assert int(m.sum()) == 1200 - YEAR
    assert out[m].nunique() > 100


# ---------------------------------------------------------------- wiring


def test_name_registration_and_accessor():
    close = _walk(600)
    df = DataFrame({"open": close, "high": close, "low": close, "close": close, "volume": 1.0})
    assert "seas" in ta.Category["performance"]
    out = df.ta.seas()
    assert out.name == "SEAS_21_1"
    pd.testing.assert_series_equal(out, seas(close))
    assert df.ta.seas(length=10, years=2).name == "SEAS_10_2"
