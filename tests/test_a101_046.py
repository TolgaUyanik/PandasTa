# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.momentum.a101_046` -- Kakushadze's (2016, Wilmott)
Alpha101 `#46`, per issue #49: the "core" shared with `#49`/`#51`,
`(delay(close,20)-delay(close,10))/10 - (delay(close,10)-close)/10`, ternary
and price-unit thresholds dropped, shipped scale-free (divided by `close`).
Gate A derivation is in the module docstring and `docs/A101046Measured.md`.
Gate E is pending (CLAUDE.md, "Owed, not failed").

What these pin, in order of how much it would hurt to lose:

* CAUSALITY by future-perturbation: rewrite every close bar from `j` onward
  (another synthetic walk), demand bars `[0:j]` bit-identical with matching
  NaN masks, over offsets past the 20-bar warm-up. The shipped mutant
  (`importlib` source read, `exec`'d in memory) shifts the final write
  index 30 bars into the future: shown live (differs from the real module),
  then caught at every offset (`python docs/measure_a101_046.py`).
* CORRECTNESS: a hand-derived example computed by hand from the formula
  text, not by re-running the module.
* SCALE-FREE: bit-identical under a close price rescale x8/x64
  (power-of-two, exact in IEEE754); measured tolerance at x10/x3.7
  (`docs/measure_a101_046.py`). Matching NaN masks, plus `0 < fires < n`
  and `nunique > 1`.
* Wiring: `Category`, the accessor, the column name `A101_046_10`.
"""
import importlib
import types

import numpy as np
import pandas as pd
import pytest
from pandas import Series

from .context import pandas_ta as ta
from pandas_ta.momentum.a101_046 import a101_046


def _walk(n=1500, seed=11, sigma=0.015):
    rng = np.random.default_rng(seed)
    close = 100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n)))
    idx = pd.RangeIndex(n)
    return Series(close, index=idx)


# ------------------------------------------------------------ correctness


def test_hand_derived_twelve_bars():
    """close = [10, 11, 12, 10, 9, 8, 13, 14, 15, 16, 20, 5], length=2.

    far[t]  = close[t-4]  (delay 2*length=4)
    near[t] = close[t-2]  (delay length=2)
    raw[t]  = (far-near)/2 - (near-close)/2 = (far - 2*near + close)/2
    result[t] = raw[t] / close[t]

    t=4: far=close[0]=10, near=close[2]=12, c=9
         raw=(10-24+9)/2=-2.5          result=-2.5/9=-0.2777777777777778
    t=5: far=close[1]=11, near=close[3]=10, c=8
         raw=(11-20+8)/2=-0.5          result=-0.5/8=-0.0625
    t=6: far=close[2]=12, near=close[4]=9,  c=13
         raw=(12-18+13)/2=3.5          result=3.5/13=0.2692307692307692
    t=7: far=close[3]=10, near=close[5]=8,  c=14
         raw=(10-16+14)/2=4.0          result=4.0/14=0.2857142857142857
    t=8: far=close[4]=9,  near=close[6]=13, c=15
         raw=(9-26+15)/2=-1.0          result=-1.0/15=-0.06666666666666667
    t=9: far=close[5]=8,  near=close[7]=14, c=16
         raw=(8-28+16)/2=-2.0          result=-2.0/16=-0.125
    t=10: far=close[6]=13, near=close[8]=15, c=20
         raw=(13-30+20)/2=1.5          result=1.5/20=0.075
    t=11: far=close[7]=14, near=close[9]=16, c=5
         raw=(14-32+5)/2=-6.5          result=-6.5/5=-1.3

    Bars 0..3 are NaN (2*length=4 warm-up). Derived by hand from the
    formula text, not by re-running the module. Reproduced in
    docs/measure_a101_046.py.
    """
    close = Series([10.0, 11.0, 12.0, 10.0, 9.0, 8.0, 13.0, 14.0, 15.0, 16.0,
                     20.0, 5.0])
    out = a101_046(close, length=2)

    assert out.iloc[:4].isna().all()
    expected = {
        4: -0.2777777777777778, 5: -0.0625, 6: 0.2692307692307692,
        7: 0.2857142857142857, 8: -0.06666666666666667, 9: -0.125,
        10: 0.075, 11: -1.3,
    }
    for t, val in expected.items():
        assert out.iloc[t] == pytest.approx(val, abs=1e-12), f"bar {t}"


def test_insufficient_history_returns_none():
    close = _walk(20)  # default length=10 needs min_length=21
    assert a101_046(close) is None


def test_exact_min_length_fires_at_the_warmup_boundary():
    close = _walk(21)  # exactly min_length=21
    out = a101_046(close)
    assert out is not None
    assert out.iloc[:20].isna().all()
    assert pd.notna(out.iloc[20])


def test_default_name():
    close = _walk()
    out = a101_046(close)
    assert out.name == "A101_046_10"


# -------------------------------------------------------------- causality


_REAL = importlib.import_module("pandas_ta.momentum.a101_046")


def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_a101_046_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


MUTANT = (
    "result = raw / close",
    "result = (raw / close).shift(-30)",  # a 30-bar look-ahead
)

OFFSETS = range(50, 1500, 40)  # past the 20-bar warm-up


def _leaks(fn):
    close = _walk(1500)
    other_c = _walk(1500, seed=97)
    base = fn(close)
    hits = 0
    for j in OFFSETS:
        pc = close.copy()
        pc.iloc[j:] = other_c.iloc[j:].values
        out = fn(pc)
        a, b = base.iloc[:j], out.iloc[:j]
        if not (a.isna() == b.isna()).all():
            hits += 1
            continue
        m = a.notna()
        if (a[m] != b[m]).any():
            hits += 1
    return hits


def test_real_module_never_reads_the_future():
    assert _leaks(a101_046) == 0


def test_lookahead_mutant_is_caught():
    mod = _load_mutant(*MUTANT)
    close = _walk(1500)
    assert not mod.a101_046(close).equals(a101_046(close))  # live
    assert _leaks(mod.a101_046) == len(list(OFFSETS))  # caught, every offset


# ------------------------------------------------------------ scale-free


@pytest.mark.parametrize("k", [8.0, 64.0])
def test_power_of_two_price_scale_is_bit_identical(k):
    close = _walk()
    base = a101_046(close)
    scaled = a101_046(close * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_other_price_scales_within_tolerance(k):
    close = _walk()
    base = a101_046(close)
    scaled = a101_046(close * k)
    assert (base.isna() == scaled.isna()).all()
    assert (base - scaled).abs().max() < 1e-9


def test_fires_and_is_not_constant():
    close = _walk()
    out = a101_046(close)
    fires = int(out.notna().sum())
    assert 0 < fires < len(out)
    assert out.dropna().nunique() > 1


# ---------------------------------------------------------------- wiring


def test_name_registration_and_accessor():
    close = _walk(400)
    df = pd.DataFrame({"open": close, "high": close, "low": close,
                        "close": close, "volume": close})
    assert "a101_046" in ta.Category["momentum"]
    out = df.ta.a101_046()
    assert out.name == "A101_046_10"
    pd.testing.assert_series_equal(out, a101_046(close))
    # the tunable kwarg forwarded under its own name -- the "supertrend
    # failure mode" (CLAUDE.md) hasattr cannot see.
    renamed = df.ta.a101_046(length=5)
    assert renamed.name == "A101_046_5"
