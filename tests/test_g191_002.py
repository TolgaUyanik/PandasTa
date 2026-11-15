# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.momentum.g191_002` -- Guotai Junan's (2017,
"GTJA191") alpha `#2`, per issue #63: the negated 1-bar change of the
close-location value `((close-low)-(high-close))/(high-low)`. Gate A
derivation is in the module docstring and `docs/G191002Measured.md`.
Gate E is pending (CLAUDE.md, "Owed, not failed").

What these pin, in order of how much it would hurt to lose:

* CAUSALITY by future-perturbation: rewrite every high/low/close bar from
  `j` onward (another synthetic walk), demand bars `[0:j]` bit-identical
  with matching NaN masks, over offsets past the 2-bar warm-up. The
  shipped mutant (`importlib` source read, `exec`'d in memory) shifts the
  final write index 30 bars into the future (`result = (-d1).shift(-30)`):
  shown live (differs from the real module), then caught at every offset
  (`python docs/measure_g191_002.py`).
* CORRECTNESS: two hand-derived examples computed by hand from the
  formula text, not by re-running the module -- one with no zero
  denominators (shows the ordinary change), one that deliberately drives
  `high == low` (a flat, zero-range bar) on two bars (shows the ratio,
  and its downstream delta, read NaN rather than a signed infinity).
* SCALE-FREE: bit-identical under a joint high/low/close price rescale
  x8/x64 (power-of-two, exact in IEEE754); within float64 tolerance under
  x10/x3.7. Matching NaN masks, plus `0 < fires < n` and `nunique > 1`.
* Wiring: `Category`, the accessor, the column name `G191_002_1`.
"""
import importlib
import types

import numpy as np
import pandas as pd
import pytest
from pandas import Series

from .context import pandas_ta as ta
from pandas_ta.momentum.g191_002 import g191_002


def _walk(n=1500, seed=11, sigma=0.015):
    rng = np.random.default_rng(seed)
    close = 100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n)))
    high = close * (1.0 + np.abs(rng.normal(0.0, sigma * 0.5, n)))
    low = close * (1.0 - np.abs(rng.normal(0.0, sigma * 0.5, n)))
    idx = pd.RangeIndex(n)
    return Series(high, index=idx), Series(low, index=idx), Series(close, index=idx)


# ------------------------------------------------------------ correctness


def test_hand_derived_eight_bars():
    """high  = [10, 11, 12, 13, 9, 20, 8, 21]
    low   = [8, 9, 9, 11, 7, 15, 6, 16]
    close = [9, 10, 11, 12, 8, 19, 7, 20]
    length=3.

    clv[t] = (2*close[t]-high[t]-low[t]) / (high[t]-low[t]):
      clv[0]=(18-10-8)/2=0.0          clv[1]=(20-11-9)/2=0.0
      clv[2]=(22-12-9)/3=0.333333...  clv[3]=(24-13-11)/2=0.0
      clv[4]=(16-9-7)/2=0.0           clv[5]=(38-20-15)/5=0.6
      clv[6]=(14-8-6)/2=0.0           clv[7]=(40-21-16)/5=0.6

    d1[t] = clv[t]-clv[t-3], result[t] = -d1[t]:
      t=3: clv3-clv0=0.0-0.0=0.0             -> result=0.0
      t=4: clv4-clv1=0.0-0.0=0.0             -> result=0.0
      t=5: clv5-clv2=0.6-0.333333...=0.2666... -> result=-0.266666...
      t=6: clv6-clv3=0.0-0.0=0.0             -> result=0.0
      t=7: clv7-clv4=0.6-0.0=0.6             -> result=-0.6

    Bars 0..2 are NaN (length=3 warm-up). Derived by hand from the formula
    text, not by re-running the module. Reproduced in
    docs/measure_g191_002.py. Same OHLC numbers as `a101_053`'s own
    hand-derived example, but a DIFFERENT denominator (high-low, not
    close-low), so the intermediate `clv` values differ from `a101_053`'s
    `clr` values at bars 2, 5 and 7.
    """
    high = Series([10.0, 11.0, 12.0, 13.0, 9.0, 20.0, 8.0, 21.0])
    low = Series([8.0, 9.0, 9.0, 11.0, 7.0, 15.0, 6.0, 16.0])
    close = Series([9.0, 10.0, 11.0, 12.0, 8.0, 19.0, 7.0, 20.0])
    out = g191_002(high, low, close, length=3)

    assert out.iloc[:3].isna().all()
    expected = {3: 0.0, 4: 0.0, 5: -0.2666666666666667, 6: 0.0, 7: -0.6}
    for t, val in expected.items():
        assert out.iloc[t] == pytest.approx(val, abs=1e-12), f"bar {t}"


def test_zero_denominator_is_nan_not_inf():
    """high  = [10, 12, 13, 10, 16]  -- high == low at t=0 and t=3
    low   = [10, 8, 9, 10, 11]
    close = [10, 11, 12, 10, 15]
    length=1.

    clv[0]: denom=0            -> NaN
    clv[1]=(22-12-8)/4=0.5
    clv[2]=(24-13-9)/4=0.5
    clv[3]: denom=0            -> NaN
    clv[4]=(30-16-11)/5=0.6

    d1[t]=clv[t]-clv[t-1], result[t]=-d1[t]:
      t=1: clv1-clv0 = 0.5-NaN   -> NaN (clv0 undefined)
      t=2: clv2-clv1 = 0.5-0.5=0.0 -> result=0.0
      t=3: clv3-clv2 = NaN-0.5  -> NaN (clv3 undefined)
      t=4: clv4-clv3 = 0.6-NaN  -> NaN (clv3 undefined)

    A zero denominator (a flat, zero-range bar) reads NaN, and that NaN
    propagates through `diff` exactly like any other missing value --
    never a signed infinity.
    """
    high = Series([10.0, 12.0, 13.0, 10.0, 16.0])
    low = Series([10.0, 8.0, 9.0, 10.0, 11.0])
    close = Series([10.0, 11.0, 12.0, 10.0, 15.0])
    out = g191_002(high, low, close, length=1)

    assert pd.isna(out.iloc[0])
    assert pd.isna(out.iloc[1])
    assert out.iloc[2] == pytest.approx(0.0, abs=1e-12)
    assert pd.isna(out.iloc[3])
    assert pd.isna(out.iloc[4])
    assert not np.isinf(out.dropna()).any()


def test_matches_an_independent_computation_at_defaults():
    """Spot-checks 3 bars of the shipped default (length=1) against an
    independent per-bar computation, not the module's own `.diff()` call."""
    high, low, close = _walk(900, seed=5)
    out = g191_002(high, low, close)
    hh, ll, cc = (s.to_numpy(dtype=float) for s in (high, low, close))

    def clv_at(t):
        return (2.0 * cc[t] - hh[t] - ll[t]) / (hh[t] - ll[t])

    def expected_at(t):
        return -(clv_at(t) - clv_at(t - 1))

    for t in (300, 600, 899):
        assert out.iloc[t] == pytest.approx(expected_at(t), rel=1e-9)


def test_insufficient_history_returns_none():
    high, low, close = _walk(1)  # default length=1 needs min_length=2
    assert g191_002(high, low, close) is None


def test_exact_min_length_fires_at_the_warmup_boundary():
    high, low, close = _walk(2)  # exactly min_length=2
    out = g191_002(high, low, close)
    assert out is not None
    assert pd.isna(out.iloc[0])
    assert pd.notna(out.iloc[1])


def test_default_name():
    high, low, close = _walk()
    out = g191_002(high, low, close)
    assert out.name == "G191_002_1"


def test_distinct_lengths_produce_distinct_names_and_values():
    high, low, close = _walk(400)
    out1 = g191_002(high, low, close, length=1)
    out2 = g191_002(high, low, close, length=5)
    assert out1.name != out2.name
    assert out1.name == "G191_002_1"
    assert out2.name == "G191_002_5"
    m = out1.notna() & out2.notna()
    assert (out1[m] != out2[m]).any()


def test_misaligned_index_raises():
    high, low, close = _walk(50)
    close = close.copy()
    close.index = close.index + 1
    with pytest.raises(ValueError):
        g191_002(high, low, close)


# -------------------------------------------------------------- causality


_REAL = importlib.import_module("pandas_ta.momentum.g191_002")


def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_g191_002_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


MUTANT = (
    "result = -d1",
    "result = (-d1).shift(-30)",  # a 30-bar look-ahead
)

OFFSETS = range(50, 1500, 40)  # past the 2-bar warm-up


def _leaks(fn):
    high, low, close = _walk(1500)
    other_h, other_l, other_c = _walk(1500, seed=97)
    base = fn(high, low, close)
    hits = 0
    for j in OFFSETS:
        ph, pl, pc = high.copy(), low.copy(), close.copy()
        ph.iloc[j:] = other_h.iloc[j:].values
        pl.iloc[j:] = other_l.iloc[j:].values
        pc.iloc[j:] = other_c.iloc[j:].values
        out = fn(ph, pl, pc)
        a, b = base.iloc[:j], out.iloc[:j]
        if not (a.isna() == b.isna()).all():
            hits += 1
            continue
        m = a.notna()
        if (a[m] != b[m]).any():
            hits += 1
    return hits


def test_real_module_never_reads_the_future():
    assert _leaks(g191_002) == 0


def test_lookahead_mutant_is_caught():
    mod = _load_mutant(*MUTANT)
    high, low, close = _walk(1500)
    assert not mod.g191_002(high, low, close).equals(g191_002(high, low, close))  # live
    assert _leaks(mod.g191_002) == len(list(OFFSETS))  # caught, every offset


# ------------------------------------------------------------ scale-free


@pytest.mark.parametrize("k", [8.0, 64.0])
def test_price_scale_is_bit_identical(k):
    high, low, close = _walk()
    base = g191_002(high, low, close)
    scaled = g191_002(high * k, low * k, close * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_price_scale_within_tolerance(k):
    high, low, close = _walk()
    base = g191_002(high, low, close)
    scaled = g191_002(high * k, low * k, close * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] - scaled[m]).abs().max() < 1e-9


def test_fires_and_is_not_constant():
    high, low, close = _walk()
    out = g191_002(high, low, close)
    fires = int(out.notna().sum())
    assert 0 < fires < len(out)
    assert out.dropna().nunique() > 1


# ---------------------------------------------------------------- wiring


def test_name_registration_and_accessor():
    high, low, close = _walk(400)
    df = pd.DataFrame({"open": close, "high": high, "low": low,
                        "close": close, "volume": close})
    assert "g191_002" in ta.Category["momentum"]
    out = df.ta.g191_002()
    assert out.name == "G191_002_1"
    pd.testing.assert_series_equal(out, g191_002(high, low, close))
    # the tunable kwarg forwarded under its own name -- the "supertrend
    # failure mode" (CLAUDE.md) hasattr cannot see.
    renamed = df.ta.g191_002(length=5)
    assert renamed.name == "G191_002_5"
