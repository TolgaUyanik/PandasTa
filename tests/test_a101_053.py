# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.momentum.a101_053` -- Kakushadze's (2016, Wilmott)
Alpha101 `#53`, per issue #48: the negated 9-bar change of the close-location
ratio `((close-low)-(high-close))/(close-low)`. Gate A derivation is in the
module docstring and `docs/A101053Measured.md`. Gate E is pending (CLAUDE.md,
"Owed, not failed").

What these pin, in order of how much it would hurt to lose:

* CAUSALITY by future-perturbation: rewrite every high/low/close bar from
  `j` onward (another synthetic walk), demand bars `[0:j]` bit-identical with
  matching NaN masks, over offsets past the warm-up. The shipped mutant
  (`importlib` source read, `exec`'d in memory) shifts the final write index
  30 bars into the future (`result = (-d9).shift(-30)`): shown live (differs
  from the real module), then caught at every offset (`python
  docs/measure_a101_053.py`).
* CORRECTNESS: two hand-derived examples computed by hand from the formula
  text, not by re-running the module -- one with no zero denominators (shows
  the ordinary change), one that deliberately drives `close == low` on two
  bars (shows the ratio, and its downstream delta, read NaN rather than a
  signed infinity).
* SCALE-FREE: bit-identical under a joint high/low/close price rescale
  x8/x64 (power-of-two, exact in IEEE754); NOT bit-identical under x10/x3.7
  -- measured max|diff| 1.19e-7 / 6.98e-8 (`docs/measure_a101_053.py`),
  bigger than other `a101_0*` ports' 1e-9 because this ratio's own
  denominator (`close - low`) comes arbitrarily close to zero, so the
  tolerance here is loosened to 1e-6 to match what is actually measured,
  not invented. Matching NaN masks, plus `0 < fires < n` and `nunique > 1`.
* Wiring: `Category`, the accessor, the column name `A101_053_9`.
"""
import importlib
import types

import numpy as np
import pandas as pd
import pytest
from pandas import Series

from .context import pandas_ta as ta
from pandas_ta.momentum.a101_053 import a101_053


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

    clr[t] = (2*close[t]-low[t]-high[t]) / (close[t]-low[t]):
      clr[0]=(18-8-10)/1=0.0        clr[1]=(20-9-11)/1=0.0
      clr[2]=(22-9-12)/2=0.5        clr[3]=(24-11-13)/1=0.0
      clr[4]=(16-7-9)/1=0.0         clr[5]=(38-15-20)/4=0.75
      clr[6]=(14-6-8)/1=0.0         clr[7]=(40-16-21)/4=0.75

    d3[t] = clr[t]-clr[t-3], result[t] = -d3[t]:
      t=3: clr3-clr0=0.0-0.0=0.0   -> result=0.0
      t=4: clr4-clr1=0.0-0.0=0.0   -> result=0.0
      t=5: clr5-clr2=0.75-0.5=0.25 -> result=-0.25
      t=6: clr6-clr3=0.0-0.0=0.0   -> result=0.0
      t=7: clr7-clr4=0.75-0.0=0.75 -> result=-0.75

    Bars 0..2 are NaN (length=3 warm-up). Derived by hand from the formula
    text, not by re-running the module. Reproduced in docs/measure_a101_053.py.
    """
    high = Series([10.0, 11.0, 12.0, 13.0, 9.0, 20.0, 8.0, 21.0])
    low = Series([8.0, 9.0, 9.0, 11.0, 7.0, 15.0, 6.0, 16.0])
    close = Series([9.0, 10.0, 11.0, 12.0, 8.0, 19.0, 7.0, 20.0])
    out = a101_053(high, low, close, length=3)

    assert out.iloc[:3].isna().all()
    expected = {3: 0.0, 4: 0.0, 5: -0.25, 6: 0.0, 7: -0.75}
    for t, val in expected.items():
        assert out.iloc[t] == pytest.approx(val, abs=1e-12), f"bar {t}"


def test_zero_denominator_is_nan_not_inf():
    """close = [10, 10, 12, 10, 15]
    low   = [10, 8, 9, 10, 11]   -- close == low at t=0 and t=3
    high  = [12, 11, 13, 12, 16]
    length=1.

    clr[0]: denom=0            -> NaN
    clr[1]=(20-8-11)/2=0.5
    clr[2]=(24-9-13)/3=0.666666...
    clr[3]: denom=0            -> NaN
    clr[4]=(30-11-16)/4=0.75

    d1[t]=clr[t]-clr[t-1], result[t]=-d1[t]:
      t=1: clr1-clr0 = 0.5-NaN   -> NaN (clr0 undefined)
      t=2: clr2-clr1 = 0.666...-0.5=0.166666... -> result=-0.166666...
      t=3: clr3-clr2 = NaN-0.666... -> NaN (clr3 undefined)
      t=4: clr4-clr3 = 0.75-NaN  -> NaN (clr3 undefined)

    A zero denominator reads NaN, and that NaN propagates through `diff`
    exactly like any other missing value -- never a signed infinity.
    """
    close = Series([10.0, 10.0, 12.0, 10.0, 15.0])
    low = Series([10.0, 8.0, 9.0, 10.0, 11.0])
    high = Series([12.0, 11.0, 13.0, 12.0, 16.0])
    out = a101_053(high, low, close, length=1)

    assert pd.isna(out.iloc[0])
    assert pd.isna(out.iloc[1])
    assert out.iloc[2] == pytest.approx(-1.0 / 6.0, abs=1e-9)
    assert pd.isna(out.iloc[3])
    assert pd.isna(out.iloc[4])
    assert not np.isinf(out.dropna()).any()


def test_insufficient_history_returns_none():
    high, low, close = _walk(9)  # default length=9 needs min_length=10
    assert a101_053(high, low, close) is None


def test_exact_min_length_fires_at_the_warmup_boundary():
    high, low, close = _walk(10)  # exactly min_length=10
    out = a101_053(high, low, close)
    assert out is not None
    assert out.iloc[:9].isna().all()
    assert pd.notna(out.iloc[9])


def test_default_name():
    high, low, close = _walk()
    out = a101_053(high, low, close)
    assert out.name == "A101_053_9"


def test_misaligned_index_raises():
    high, low, close = _walk(50)
    close = close.copy()
    close.index = close.index + 1
    with pytest.raises(ValueError):
        a101_053(high, low, close)


# -------------------------------------------------------------- causality


_REAL = importlib.import_module("pandas_ta.momentum.a101_053")


def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_a101_053_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


MUTANT = (
    "result = -d9",
    "result = (-d9).shift(-30)",  # a 30-bar look-ahead
)

OFFSETS = range(50, 1500, 40)  # past the 9-bar warm-up


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
    assert _leaks(a101_053) == 0


def test_lookahead_mutant_is_caught():
    mod = _load_mutant(*MUTANT)
    high, low, close = _walk(1500)
    assert not mod.a101_053(high, low, close).equals(a101_053(high, low, close))  # live
    assert _leaks(mod.a101_053) == len(list(OFFSETS))  # caught, every offset


# ------------------------------------------------------------ scale-free


@pytest.mark.parametrize("k", [8.0, 64.0])
def test_power_of_two_price_scale_is_bit_identical(k):
    high, low, close = _walk()
    base = a101_053(high, low, close)
    scaled = a101_053(high * k, low * k, close * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_other_price_scales_within_tolerance(k):
    """Unlike `a101_023`'s `raw = -d2/close` (a clean quantity in the
    denominator), this formula's denominator is `close - low` itself --
    a DIFFERENCE that comes arbitrarily close to zero (measured min
    |close-low| on this walk: 7.4e-5, `docs/measure_a101_053.py`). A
    rescale-then-divide there is genuine catastrophic cancellation, not a
    scale leak in the algebra (Gate D docstring): measured max|diff| is
    1.19e-7 at x10 and 6.98e-8 at x3.7 -- both far below bit-level identity
    but real floating-point noise from a near-zero denominator, hence the
    looser (still measured, not merely loosened) 1e-6 tolerance here versus
    other ports' 1e-9."""
    high, low, close = _walk()
    base = a101_053(high, low, close)
    scaled = a101_053(high * k, low * k, close * k)
    assert (base.isna() == scaled.isna()).all()
    assert (base - scaled).abs().max() < 1e-6


def test_fires_and_is_not_constant():
    high, low, close = _walk()
    out = a101_053(high, low, close)
    fires = int(out.notna().sum())
    assert 0 < fires < len(out)
    assert out.dropna().nunique() > 1


# ---------------------------------------------------------------- wiring


def test_name_registration_and_accessor():
    high, low, close = _walk(400)
    df = pd.DataFrame({"open": close, "high": high, "low": low,
                        "close": close, "volume": close})
    assert "a101_053" in ta.Category["momentum"]
    out = df.ta.a101_053()
    assert out.name == "A101_053_9"
    pd.testing.assert_series_equal(out, a101_053(high, low, close))
    # the tunable kwarg forwarded under its own name -- the "supertrend
    # failure mode" (CLAUDE.md) hasattr cannot see.
    renamed = df.ta.a101_053(length=5)
    assert renamed.name == "A101_053_5"
