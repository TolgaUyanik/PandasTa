# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.momentum.a101_048` -- Kakushadze's (2016, Wilmott)
Alpha101 `#48` without `IndNeutralize`, per issue #41: the 1-day price
change scaled by its own rolling 250-bar lag-1 autocorrelation and by the
inverse of the rolling sum of squared daily returns. Gate A derivation is in
the module docstring and `docs/A101048Measured.md`. Gate E is pending
(CLAUDE.md, "Owed, not failed").

What these pin, in order of how much it would hurt to lose:

* CAUSALITY by future-perturbation: rewrite every close bar from `j` onward
  (another walk), demand bars `[0:j]` bit-identical with matching NaN masks,
  over 30 offsets past the 252-bar warm-up. A one-bar look-ahead mutant
  (`importlib` source read, the autocorrelation's lag term shifted from
  `d.shift(1)` to `d.shift(-1)`, `exec`'d in memory) is proved live, then
  caught at 30 of 30.
* CORRECTNESS: a hand-derived example at `length=2` (a correlation of
  exactly two points is always +-1, so the whole chain is checkable by
  hand), plus an independent per-bar loop at the shipped default
  (`length=250`) built from `numpy.corrcoef`, not from pandas' own
  `.rolling().corr()`.
* SCALE-FREE: bit-identical under close x8/x64 (every term is a ratio of
  like-scaled prices or a correlation coefficient, scale-invariant by
  definition), within 1e-9 under x10/x3.7, matching NaN masks, plus
  `0 < fires < n` and not a constant column.
* Wiring: `Category`, the accessor, the column name `A101_048_250`.
"""
import importlib
import types

import numpy as np
import pandas as pd
import pytest
from pandas import Series

from .context import pandas_ta as ta
from pandas_ta.momentum.a101_048 import a101_048


def _walk(n=1500, seed=11, sigma=0.015):
    rng = np.random.default_rng(seed)
    close = 100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n)))
    return Series(close)


# ------------------------------------------------------------ correctness


def test_hand_derived_three_bars_at_length_2():
    """close = [100, 102, 101, 105, 103, 108], length=2.

    d = delta(close,1): [nan, 2, -1, 4, -2, 5]
    A correlation of exactly two (d, d.shift(1)) pairs is always +-1 (two
    points determine a line exactly): +1 if both pairs move the same
    direction, -1 if opposite.
      t=3: pairs (d[2],d[3])=(-1,4) vs (d[1],d[2])=(2,-1):
           d rises -1->4 while its lag falls 2->-1 -> opposite -> corr=-1
      t=4: pairs (d[3],d[4])=(4,-2) vs (d[2],d[3])=(-1,4):
           d falls 4->-2 while its lag rises -1->4 -> opposite -> corr=-1
      t=5: pairs (d[4],d[5])=(-2,5) vs (d[3],d[4])=(4,-2):
           d rises -2->5 while its lag falls 4->-2 -> opposite -> corr=-1
    r = delta(close,1)/delay(close,1): r[1]=0.02, r[2]=-1/102, r[3]=4/101,
        r[4]=-2/105, r[5]=5/103
    result(t) = corr(t) * d[t] / close[t] / (r[t-1]^2 + r[t]^2)
    """
    close = Series([100.0, 102.0, 101.0, 105.0, 103.0, 108.0])
    out = a101_048(close, length=2)

    r = {1: 0.02, 2: -1.0 / 102.0, 3: 4.0 / 101.0, 4: -2.0 / 105.0, 5: 5.0 / 103.0}
    d = {1: 2.0, 2: -1.0, 3: 4.0, 4: -2.0, 5: 5.0}
    corr = {3: -1.0, 4: -1.0, 5: -1.0}

    assert out.iloc[:3].isna().all()
    for t in (3, 4, 5):
        denom = r[t - 1] ** 2 + r[t] ** 2
        expected = corr[t] * d[t] / close.iloc[t] / denom
        assert out.iloc[t] == pytest.approx(expected, rel=1e-12)


def test_matches_an_independent_loop_at_defaults():
    """Spot-checks 3 bars of the shipped default (length=250) against a
    hand-written loop using `numpy.corrcoef`, independent of the module's
    `pandas .rolling().corr()` call."""
    close = _walk(400, seed=3)
    out = a101_048(close)
    c = close.to_numpy(dtype=float)
    length = 250

    d = np.empty(len(c))
    d[0] = np.nan
    d[1:] = c[1:] - c[:-1]
    r = np.empty(len(c))
    r[0] = np.nan
    r[1:] = c[1:] / c[:-1] - 1.0

    for t in (300, 350, 399):
        window_d = d[t - length + 1:t + 1]      # d[t-249 .. t]
        window_lag = d[t - length:t]             # d[t-250 .. t-1], i.e. d.shift(1) over the same span
        corr = np.corrcoef(window_d, window_lag)[0, 1]
        denom = np.sum(r[t - length + 1:t + 1] ** 2)
        expected = corr * d[t] / c[t] / denom
        assert out.iloc[t] == pytest.approx(expected, rel=1e-9)


def test_insufficient_history_returns_none():
    close = _walk(10)  # default length=250 needs 252 bars
    assert a101_048(close) is None


def test_default_length_and_name():
    close = _walk()
    out = a101_048(close)
    assert out.name == "A101_048_250"
    assert int(out.isna().sum()) == 251  # first_valid_index 251, measured


# -------------------------------------------------------------- causality


_REAL = importlib.import_module("pandas_ta.momentum.a101_048")


def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_a101_048_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


MUTANT = (
    "autocorr = d.rolling(length).corr(d.shift(1))",
    "autocorr = d.rolling(length).corr(d.shift(-1))",  # a 1-bar look-ahead
)

OFFSETS = range(300, 1500, 40)  # 30 offsets, past the 252-bar warm-up


def _leaks(fn):
    close = _walk()
    base = fn(close)
    other = _walk(seed=97)
    hits = 0
    for j in OFFSETS:
        perturbed = close.copy()
        perturbed.iloc[j:] = other.iloc[j:].values
        out = fn(perturbed)
        a, b = base.iloc[:j], out.iloc[:j]
        if not (a.isna() == b.isna()).all():
            hits += 1
            continue
        m = a.notna()
        if (a[m] != b[m]).any():
            hits += 1
    return hits


def test_real_module_never_reads_the_future():
    assert _leaks(a101_048) == 0


def test_lookahead_mutant_is_caught():
    mod = _load_mutant(*MUTANT)
    close = _walk()
    assert not mod.a101_048(close).equals(a101_048(close))  # live
    assert _leaks(mod.a101_048) == len(OFFSETS)  # caught, 30 of 30


# ------------------------------------------------------------ scale-free


@pytest.mark.parametrize("k", [8.0, 64.0])
def test_power_of_two_price_scale_is_bit_identical(k):
    close = _walk()
    base = a101_048(close)
    scaled = a101_048(close * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_other_scales_within_tolerance(k):
    close = _walk()
    base = a101_048(close)
    scaled = a101_048(close * k)
    assert (base.isna() == scaled.isna()).all()
    assert (base - scaled).abs().max() < 1e-9


def test_fires_and_is_not_constant():
    close = _walk()
    out = a101_048(close)
    fires = int(out.notna().sum())
    assert 0 < fires < len(out)
    assert out.dropna().nunique() > 100


# ---------------------------------------------------------------- wiring


def test_name_registration_and_accessor():
    close = _walk(400)
    df = pd.DataFrame({"open": close, "high": close, "low": close,
                        "close": close, "volume": close})
    assert "a101_048" in ta.Category["momentum"]
    out = df.ta.a101_048()
    assert out.name == "A101_048_250"
    pd.testing.assert_series_equal(out, a101_048(close))
    assert df.ta.a101_048(length=2).name == "A101_048_2"
