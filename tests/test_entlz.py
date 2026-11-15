# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.statistics.entlz` -- the plug-in Shannon entropy of
sign-encoded returns (AFML ch. 18 "Entropy Features"). PandasTa issue #11.
Measurements and the open gates are in `docs/EntlzMeasured.md`.

What these tests pin, in order of how much it would hurt to lose them:

* CORRECTNESS against an independent reference: a nested-loop frequency
  count of the sign alphabet {-1, 0, +1} per window, written from the
  plug-in-entropy formula, not from the module. Three hand-computed cases
  give exact closed forms: a pure trend reads exactly 0, a perfect
  alternation reads exactly 1 bit, and a three-way-equal split reads
  exactly log2(3).
* CAUSALITY by future-perturbation: flip the sign of return `j` alone
  (deterministic reflection around bar `j-1`, not a random future -- a
  3-symbol sign alphabet can tie on a random future by chance), demand
  bars `[0:j]` bit-identical with matching NaN masks, over 32 offsets. Two
  one-bar look-ahead mutants (`importlib` source read, `exec`'d in
  memory) -- the return series read one bar ahead, and the rolling
  frequency window read one bar ahead -- are each proved live, then
  caught at 32 of 32. `test_the_random_future_convention_ties_on_this_alphabet`
  pins WHY the deterministic flip is used instead of the whole-tail-
  replacement convention `pfe`/`cusum` use: on this alphabet that
  convention only catches both mutants at 29 of 32 offsets.
* SCALE-FREE, more strongly than the usual x8/x64 bit-identical check:
  because `sign(k * x) == sign(x)` for any `k > 0`, the column is
  bit-identical under x8, x64, x10 AND x3.7 (measured, not merely within
  tolerance) -- the only property a sign encoding needs to guarantee this,
  and the reason the issue calls it "scale-free by construction".
* BOUNDED: 0 <= ENTLZ <= log(3, base), the entropy of a uniform 3-symbol
  alphabet; a flat window (single symbol) hits the lower bound exactly.
* REACHABILITY: `0 < fires < n` is replaced by "not constant" (the column
  is continuous). On a 50-bar trend + 200-bar chop frame (length 20): 230
  non-NaN bars, 11 distinct values, 31 reading exactly 0 (the trend) and
  127 reading >= 0.99 bit, near the 2-symbol bound (the chop).
* EDGES: a flat window (constant sign) reads 0, not NaN; a NaN close
  blanks its own bar and the next `length`; the `length`-bar warm-up;
  `offset`, `fillna`; `length` below 2 falls back to 20.
* Wiring: `Category`, the accessor, the column name `ENTLZ_20`.
"""
import importlib
import types

import numpy as np
import pandas as pd
import pytest
from pandas import DataFrame, Series

from .context import pandas_ta as ta
from pandas_ta.statistics.entlz import entlz

LOG2_3 = np.log2(3.0)


def _walk(n=1200, seed=11):
    """Tick-rounded geometric random walk around 100 (produces flat bars)."""
    rng = np.random.default_rng(seed)
    return Series(np.round(100 * np.exp(np.cumsum(rng.normal(0, 0.015, n))), 2))


def _reference(close, length, base=2.0):
    """Plug-in entropy of the sign alphabet, as nested Python loops."""
    r = np.diff(np.asarray(close, dtype=float))
    sign = np.sign(r)
    out = np.full(len(close), np.nan)
    for t in range(length, len(close)):
        window = sign[t - length:t]  # returns (t-length+1)..t, i.e. r[t-length..t-1]
        counts = {s: 0 for s in (-1.0, 0.0, 1.0)}
        for v in window:
            counts[v] += 1
        h = 0.0
        for v in counts.values():
            if v == 0:
                continue
            p = v / length
            h -= p * np.log(p) / np.log(base)
        out[t] = h
    return out


# ------------------------------------------------------------ correctness


def test_pure_trend_reads_zero():
    close = Series(np.arange(1.0, 31.0))  # strictly increasing, every return +1
    out = entlz(close, length=10)
    assert out.iloc[10:].eq(0.0).all()


def test_pure_decline_reads_zero():
    close = Series(np.arange(30.0, 0.0, -1.0))
    out = entlz(close, length=10)
    assert out.iloc[10:].eq(0.0).all()


def test_perfect_alternation_reads_one_bit():
    # returns alternate +1, -1, +1, -1, ... -> freq(+1) = freq(-1) = 0.5, freq(0) = 0
    steps = np.array([1.0, -1.0] * 15)
    close = Series(np.cumsum(np.concatenate([[0.0], steps])))
    out = entlz(close, length=10)
    assert out.iloc[10:] .apply(lambda v: v == pytest.approx(1.0, abs=1e-12)).all()


def test_three_way_equal_split_reads_log2_3():
    # length 9: 3 up, 3 down, 3 flat returns, in some fixed order
    steps = np.array([1.0, -1.0, 0.0] * 3)
    close = Series(np.cumsum(np.concatenate([[0.0], steps])))
    out = entlz(close, length=9)
    assert out.iloc[9] == pytest.approx(LOG2_3, abs=1e-12)


@pytest.mark.parametrize("length", [20, 9, 2])
def test_matches_the_reference_loop(length):
    close = _walk(400)
    out = entlz(close, length=length)
    ref = _reference(close, length)
    assert (np.isnan(ref) == out.isna().values).all()
    np.testing.assert_allclose(out.values[length:], ref[length:], rtol=1e-9, atol=1e-12)


def test_matches_the_reference_loop_at_a_non_default_base():
    close = _walk(400)
    out = entlz(close, length=20, base=10.0)
    ref = _reference(close, length=20, base=10.0)
    assert (np.isnan(ref) == out.isna().values).all()
    np.testing.assert_allclose(out.values[20:], ref[20:], rtol=1e-9, atol=1e-12)


def test_flat_window_reads_zero_not_nan():
    close = Series([50.0] * 40)  # every return is exactly 0 (flat)
    out = entlz(close, length=10)
    assert out.iloc[10:].eq(0.0).all()


# -------------------------------------------------------------- causality

_REAL = importlib.import_module("pandas_ta.statistics.entlz")


def _load_mutant(old, new, tag):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType(f"_entlz_mutant_{tag}")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


MUTANTS = {
    # returns read one bar ahead: the symbol at T is sign(close[T+1] - close[T])
    "returns": ("returns = close.diff()", "returns = close.diff().shift(-1)"),
    # the rolling frequency window reads one bar ahead
    "window": ("freq = indicator.rolling(length).mean().to_numpy()",
               "freq = indicator.shift(-1).rolling(length).mean().to_numpy()"),
}

OFFSETS = range(60, 1150, 35)  # 32 offsets


def _moved(a, b):
    if not (a.isna() == b.isna()).all():
        return True
    m = a.notna()
    return bool((a[m] != b[m]).any())


def _flip_at(close, j, eps=1.0):
    """`close` with bar `j` reflected around bar `j-1`, so the return at `j`
    has the opposite sign of the base return at `j` -- deterministic, not
    luck-of-the-draw like a random future, which a 3-symbol sign alphabet
    can tie on by chance. A tied (zero) base return is nudged instead of
    reflected, since reflecting a zero displacement is still zero."""
    pc = close.copy()
    d = close.iloc[j] - close.iloc[j - 1]
    pc.iloc[j] = close.iloc[j - 1] + eps if d == 0 else close.iloc[j - 1] - d
    return pc


def _leaks(fn):
    """Count offsets `j` at which flipping the sign of return `j` alone
    moves any bar < j -- the exact signature of a one-bar look-ahead."""
    close = _walk()
    base = fn(close)
    hits = 0
    for j in OFFSETS:
        pc = _flip_at(close, j)
        if _moved(base.iloc[:j], fn(pc).iloc[:j]):
            hits += 1
    return hits


def test_real_module_never_reads_the_future():
    assert _leaks(entlz) == 0


@pytest.mark.parametrize("tag", sorted(MUTANTS))
def test_mutant_is_caught(tag):
    mod = _load_mutant(*MUTANTS[tag], tag)
    close = _walk()
    assert not mod.entlz(close).equals(entlz(close))  # live
    assert _leaks(mod.entlz) == len(OFFSETS)          # caught, every offset


def _leaks_random_future(fn):
    """The whole-tail-replacement convention `pfe`/`cusum` use: at each
    offset `j`, overwrite closes `j:` with another walk or the same walk
    x1000, and see if bars `< j` move. Kept ONLY to pin why it is NOT used
    above: the perturbed and base returns can tie in SIGN by chance on a
    3-symbol alphabet, unlike a continuous statistic."""
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


@pytest.mark.parametrize("tag", sorted(MUTANTS))
def test_the_random_future_convention_ties_on_this_alphabet(tag):
    """Measured, pinning the reason `_leaks` above flips a single bar
    deterministically instead: both look-ahead mutants are caught at only
    29 of 32 offsets by the random-future convention, 3 short of the 32/32
    the deterministic flip gets. Re-run this to reproduce the count."""
    mod = _load_mutant(*MUTANTS[tag], tag)
    assert _leaks_random_future(mod.entlz) == 29


# ------------------------------------------------------------ scale-free


@pytest.mark.parametrize("k", [8.0, 64.0, 10.0, 3.7])
def test_any_positive_scale_is_bit_identical(k):
    """sign(k * x) == sign(x) for k > 0, so unlike most rolling statistics
    this column needs no tolerance band at all: every scale tested,
    including the non-power-of-two ones, is bit-identical."""
    close = _walk()
    base, scaled = entlz(close), entlz(close * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] == scaled[m]).all()


def test_column_is_not_constant():
    # a strict trend (zero entropy) followed by a choppy walk (higher entropy)
    trend = np.arange(1.0, 51.0)
    chop = _walk(200, seed=3).to_numpy() + trend[-1]
    close = Series(np.concatenate([trend, chop]))
    out = entlz(close, length=20).dropna()
    assert out.nunique() > 10
    assert (out == 0.0).sum() > 0          # the trending windows
    assert (out >= 0.99).sum() > 0         # the choppy windows, near the 2-symbol bound of 1 bit
    assert ((out >= 0.0) & (out <= LOG2_3 + 1e-9)).all()


def test_bounded():
    for seed in range(10):
        out = entlz(_walk(600, seed)).dropna()
        assert (out >= -1e-12).all() and (out <= LOG2_3 + 1e-9).all()


# ---------------------------------------------------------------- edges


def test_edge_cases():
    close = _walk()
    base = entlz(close)
    assert int(base.isna().sum()) == 20  # length-bar warm-up
    cn = close.copy()
    cn[500] = np.nan
    gap = entlz(cn)
    # one NaN close blanks its own return and the next `length` windows
    assert gap[500:521].isna().all() and gap[521:].notna().all()
    for bad in (1, 1.9):
        assert entlz(close, length=bad).name == "ENTLZ_20"
    assert entlz(close, length=9.9).name == "ENTLZ_9"
    pd.testing.assert_series_equal(entlz(close, offset=1), base.shift(1))
    assert entlz(close, fillna=0).isna().sum() == 0
    assert entlz(close.iloc[:20]) is None  # needs length + 1 closes


# ---------------------------------------------------------------- wiring


def test_name_registration_and_accessor():
    close = _walk(300)
    df = DataFrame({"open": close, "high": close, "low": close, "close": close, "volume": 1.0})
    assert "entlz" in ta.Category["statistics"]
    out = df.ta.entlz()
    assert out.name == "ENTLZ_20"
    pd.testing.assert_series_equal(out, entlz(close))
    assert df.ta.entlz(length=9).name == "ENTLZ_9"
