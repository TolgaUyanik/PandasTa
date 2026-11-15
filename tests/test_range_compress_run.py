# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.volatility.range_compress_run` -- the number of
consecutive bars whose high-low range is strictly below the prior bar's.
Source: r/Daytrading 1tv21c0 (tier 4, untested claims). Measurements and the
open gates are in `docs/RangeCompressRunMeasured.md`.

What these tests pin, in order of how much it would hurt to lose them:

* CAUSALITY by future-perturbation: rewrite every bar from `j` onward
  (another walk, a very wide future, a zero-width future), demand bars
  `[0:j]` bit-identical with matching NaN masks, over 31 offsets.  Two
  look-ahead mutants (`importlib` source read, one index shifted forward,
  `exec`'d in memory) are each proved live, then caught at 31 of 31.  The
  random rewrite alone caught the `prior` mutant at only 12 of 31.
* THE TIE TOLERANCE.  On tick prices a decimal tie can come out unequal in
  float (bars 170/171 of the seed-11 walk: both 57 ticks, 2.8500000000000085
  vs 2.8499999999999943).  With a plain `<`, 4 of the 14 exact tick ties on
  that walk read as compression, and x10 scaling moved 9 bars (x3.7 moved 0
  even without it).  `test_float_flag_matches_exact_tick_arithmetic`
  compares the module against integer tick counts.  The tolerance scales
  with PRICE, because subtraction noise does: a range-relative 1e-9 (the
  first draft) misread equal tick ranges near 1e7.
* SCALE-FREE: on the seed-11 walk, x8, x64, x10, x3.7 bit-identical with
  matching NaN masks, and `0 < fires < n` (600 of 1,200 bars non-zero, 599
  zero, 1 NaN warm-up).
* EDGES: a NaN mid-series blanks that bar and the next, then the run
  restarts at 0; zero-width and inverted-bar ties read 0; `offset`, `fillna`.
* CORRECTNESS against an independent loop written from the definition, a
  hand-computed sequence, the cap, and bar 0 being NaN (no prior range).
* Wiring: `Category`, the accessor, the column name `RCR_100`.
"""
import importlib
import types

import numpy as np
import pandas as pd
import pytest
from pandas import DataFrame, Series

from .context import pandas_ta as ta
from pandas_ta.volatility.range_compress_run import range_compress_run


TICK = 0.05


def _ticks(n=1200, seed=11):
    """Integer tick counts of high and low on a GBM walk."""
    rng = np.random.default_rng(seed)
    c = 100.0 * np.exp(np.cumsum(rng.normal(0.0, 0.02, n)))
    h = c * (1 + rng.uniform(0, 0.02, n))
    lo = c * (1 - rng.uniform(0, 0.02, n))
    return np.round(h / TICK), np.round(lo / TICK)


def _walk(n=1200, seed=11):
    ht, lt = _ticks(n, seed)
    return Series(ht * TICK), Series(lt * TICK)


# ------------------------------------------------------------ correctness


def test_hand_computed():
    rng = [5.0, 4.0, 3.0, 3.0, 2.0, 6.0, 1.0]
    low = Series([10.0] * len(rng))
    out = range_compress_run(low + Series(rng), low)
    #      bar0 no prior; 4<5; 3<4; tie resets; 2<3; 6 widens; 1<6
    assert out.isna().tolist() == [True] + [False] * 6
    assert out.iloc[1:].tolist() == [1.0, 2.0, 0.0, 1.0, 0.0, 1.0]


def test_matches_an_independent_loop():
    ht, lt = _ticks()
    r = ht - lt  # exact integer ticks, no float noise
    ref = np.full(len(r), np.nan)
    run = 0
    for t in range(1, len(r)):
        run = run + 1 if r[t] < r[t - 1] else 0
        ref[t] = min(run, 100)
    out = range_compress_run(*_walk())
    assert (np.isnan(ref) == out.isna().values).all()
    assert (out.values[1:] == ref[1:]).all()


def test_float_flag_matches_exact_tick_arithmetic():
    ht, lt = _ticks()
    h, lo = _walk()
    r_exact = Series(ht - lt)
    assert int((r_exact == r_exact.shift(1)).sum()) == 14  # decimal ties
    r_float = h - lo
    naive = r_float < r_float.shift(1)
    assert int((naive != (r_exact < r_exact.shift(1))).sum()) == 4
    out = range_compress_run(h, lo)
    assert ((out.iloc[1:] > 0) == (r_exact < r_exact.shift(1)).iloc[1:]).all()
    # the docstring's example pair: equal in ticks, unequal in float
    assert r_exact[170] == r_exact[171] == 57
    assert r_float[171] < r_float[170]
    assert out[171] == 0.0


def test_tie_tolerance_holds_at_high_prices():
    # Equal tick ranges near 1e7: a range-relative 1e-9 tolerance (the first
    # draft) read these as compression; subtraction noise scales with price.
    k = np.arange(6)
    out = range_compress_run(Series(1e7 + 0.05 * (k + 1)), Series(1e7 + 0.05 * k))
    assert out.iloc[1:].tolist() == [0.0] * 5


def test_edge_cases():
    h, lo = _walk()
    base = range_compress_run(h, lo)
    hn = h.copy()
    hn[500] = np.nan
    out = range_compress_run(hn, lo)
    # run restarts: bar 502 counts only its own comparison with bar 501
    r = h - lo
    assert out[[500, 501]].isna().all()
    assert out[502] == (1.0 if r[502] < r[501] else 0.0)
    assert out[503] in (0.0, out[502] + 1)
    assert out.drop([500, 501]).isna().sum() == 1
    # zero-width bars tie, and an inverted bar (high < low) tie does too
    assert range_compress_run(Series([5.0] * 4), Series([5.0] * 4)).iloc[1:].tolist() == [0.0] * 3
    assert range_compress_run(Series([1.0] * 3), Series([3.0] * 3)).iloc[1:].tolist() == [0.0] * 2
    pd.testing.assert_series_equal(range_compress_run(h, lo, offset=1), base.shift(1))
    assert range_compress_run(h, lo, fillna=0).isna().sum() == 0


def test_cap():
    low = Series([0.0] * 30)
    high = Series(np.linspace(30, 1, 30))  # every bar compresses
    out = range_compress_run(high, low, cap=10)
    assert out.name == "RCR_10"
    assert out.iloc[1:11].tolist() == list(map(float, range(1, 11)))
    assert (out.iloc[11:] == 10.0).all()


# -------------------------------------------------------------- causality

_REAL = importlib.import_module("pandas_ta.volatility.range_compress_run")


def _load_mutant(old, new, tag):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType(f"_rcr_mutant_{tag}")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


MUTANTS = {
    "prior": ("prior = rng.shift(1)", "prior = rng.shift(-1)"),
    "range": ("compressed = rng < prior - tol", "compressed = rng.shift(-1) < prior - tol"),
}

OFFSETS = range(40, 1100, 35)  # 31 offsets


def _moved(a, b):
    if not (a.isna() == b.isna()).all():
        return True
    m = a.notna()
    return bool((a[m] != b[m]).any())


def _leaks(fn):
    """Count offsets `j` at which rewriting bars >= j moves any bar < j.

    The output is a count driven by a binary flag, so a random rewrite of the
    future often leaves a one-bar look-ahead's flag unchanged (a random
    rewrite alone caught the `prior` mutant at 12 of 31).  A very wide and a
    zero-width future push any read of bar j to both sides of every
    comparison, so one of the three must flip it.
    """
    h, lo = _walk()
    base = fn(h, lo)
    oh, ol = _walk(seed=99)
    hits = 0
    for j in OFFSETS:
        futures = [(oh.iloc[j:].values, ol.iloc[j:].values),
                   (lo.iloc[j:].values + 1000.0, lo.iloc[j:].values),
                   (lo.iloc[j:].values, lo.iloc[j:].values)]
        for fh, fl in futures:
            ph, pl = h.copy(), lo.copy()
            ph.iloc[j:], pl.iloc[j:] = fh, fl
            if _moved(base.iloc[:j], fn(ph, pl).iloc[:j]):
                hits += 1
                break
    return hits


def test_real_module_never_reads_the_future():
    assert _leaks(range_compress_run) == 0


@pytest.mark.parametrize("tag", sorted(MUTANTS))
def test_mutant_is_caught(tag):
    mod = _load_mutant(*MUTANTS[tag], tag)
    h, lo = _walk()
    assert not mod.range_compress_run(h, lo).equals(range_compress_run(h, lo))
    assert _leaks(mod.range_compress_run) == len(OFFSETS)


# ------------------------------------------------------------ scale-free


@pytest.mark.parametrize("k", [8.0, 64.0, 10.0, 3.7])
def test_scale_is_bit_identical(k):
    h, lo = _walk()
    base, scaled = range_compress_run(h, lo), range_compress_run(h * k, lo * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] == scaled[m]).all()


def test_column_is_not_constant():
    out = range_compress_run(*_walk())
    assert int(out.isna().sum()) == 1
    assert int((out == 0).sum()) == 599 and int((out > 0).sum()) == 600
    assert out.nunique() == 5  # runs of 0..4 on this walk


# ---------------------------------------------------------------- wiring


def test_name_registration_and_accessor():
    h, lo = _walk(200)
    df = DataFrame({"open": h, "high": h, "low": lo, "close": lo, "volume": 1.0})
    assert "range_compress_run" in ta.Category["volatility"]
    out = df.ta.range_compress_run()
    assert out.name == "RCR_100"
    pd.testing.assert_series_equal(out, range_compress_run(h, lo))
    assert df.ta.range_compress_run(cap=9).name == "RCR_9"
