# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.momentum.a101_023` -- Kakushadze's (2016, Wilmott)
Alpha101 `#23`, per issue #47: when today's high is above its own 20-bar
trailing mean, the column reads the negated 2-bar high change divided by
close; otherwise 0. Gate A derivation is in the module docstring and
`docs/A101023Measured.md`. Gate E is pending (CLAUDE.md, "Owed, not
failed").

What these pin, in order of how much it would hurt to lose:

* CAUSALITY by future-perturbation: rewrite every high/close bar from `j`
  onward (another synthetic walk), demand bars `[0:j]` bit-identical with
  matching NaN masks, over offsets past the 19-bar warm-up. The shipped
  mutant (`importlib` source read, `exec`'d in memory) shifts the final
  write index 30 bars into the future (`result =
  result.where(mean_h.notna()).shift(-30)`): shown live (differs from the
  real module), then caught at every offset (`python
  docs/measure_a101_023.py`). A weaker mutant was tried first and rejected
  as under-sized, not wrong: shifting by only `length=20` bars is a real
  look-ahead (proved live) but is caught only 32 of 35 offsets -- the extra
  10 bars (30 vs 20) widen the affected window enough to be caught every
  time.
* CORRECTNESS: a hand-derived 8-bar example at `length=5, delta_length=2`,
  computed by hand from the formula text, not by re-running the module.
* SCALE-FREE: bit-identical under a joint high/close price rescale x8/x64
  (power-of-two, exact in IEEE754), within 1e-9 tolerance (not bit-identical
  -- measured, not assumed) under x10/x3.7. Matching NaN masks, plus
  `0 < fires < n` and `nunique > 1`.
* Wiring: `Category`, the accessor, the column name `A101_023_20_2`.
"""
import importlib
import types

import numpy as np
import pandas as pd
import pytest
from pandas import Series

from .context import pandas_ta as ta
from pandas_ta.momentum.a101_023 import a101_023


def _walk(n=1500, seed=11, sigma=0.015):
    rng = np.random.default_rng(seed)
    close = 100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n)))
    high = close * (1.0 + np.abs(rng.normal(0.0, sigma * 0.5, n)))
    idx = pd.RangeIndex(n)
    return Series(high, index=idx), Series(close, index=idx)


# ------------------------------------------------------------ correctness


def test_hand_derived_eight_bars():
    """high  = [10, 11, 12, 13, 9, 20, 8, 21]
    close = [9, 10, 11, 12, 8, 19, 7, 20]
    length=5, delta_length=2.

    mean_h[t] = mean(high[t-4:t+1]), valid t>=4:
      mean_h[4]=mean(10,11,12,13,9)=11.0
      mean_h[5]=mean(11,12,13,9,20)=13.0
      mean_h[6]=mean(12,13,9,20,8)=12.4
      mean_h[7]=mean(13,9,20,8,21)=14.2

    cond[t] = mean_h[t] < high[t]:
      t=4: 11.0<9  -> False -> 0.0
      t=5: 13.0<20 -> True  -> raw
      t=6: 12.4<8  -> False -> 0.0
      t=7: 14.2<21 -> True  -> raw

    d2[t] = high[t]-high[t-2]: d2[5]=20-13=7, d2[7]=21-20=1
    raw[t] = -d2[t]/close[t]: raw[5]=-7/19=-0.368421..., raw[7]=-1/20=-0.05

    result[4]=0.0, result[5]=-0.368421052631579, result[6]=0.0,
    result[7]=-0.05. Bars 0..3 are NaN (mean_h undefined).

    Derived by hand from the formula text, not by re-running the module.
    Reproduced in docs/measure_a101_023.py.
    """
    high = Series([10.0, 11.0, 12.0, 13.0, 9.0, 20.0, 8.0, 21.0])
    close = Series([9.0, 10.0, 11.0, 12.0, 8.0, 19.0, 7.0, 20.0])
    out = a101_023(high, close, length=5, delta_length=2)

    assert out.iloc[:4].isna().all()
    expected = {4: 0.0, 5: -0.3684210526315789, 6: 0.0, 7: -0.05}
    for t, val in expected.items():
        assert out.iloc[t] == pytest.approx(val, abs=1e-12), f"bar {t}"


def test_insufficient_history_returns_none():
    high, close = _walk(19)  # defaults need max(20, 3) = 20 bars
    assert a101_023(high, close) is None


def test_exact_min_length_fires_at_the_warmup_boundary():
    high, close = _walk(20)  # exactly max(20, 3) = 20 bars
    out = a101_023(high, close)
    assert out is not None
    assert out.iloc[:19].isna().all()
    assert pd.notna(out.iloc[19])


def test_default_name():
    high, close = _walk()
    out = a101_023(high, close)
    assert out.name == "A101_023_20_2"


def test_misaligned_index_raises():
    high, close = _walk(50)
    close = close.copy()
    close.index = close.index + 1
    with pytest.raises(ValueError):
        a101_023(high, close)


# -------------------------------------------------------------- causality


_REAL = importlib.import_module("pandas_ta.momentum.a101_023")


def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_a101_023_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


MUTANT = (
    "result = result.where(mean_h.notna())",
    "result = result.where(mean_h.notna()).shift(-30)",  # a 30-bar look-ahead
)

OFFSETS = range(100, 1500, 40)  # past the 19-bar warm-up


def _leaks(fn):
    high, close = _walk(1500)
    other_h, other_c = _walk(1500, seed=97)
    base = fn(high, close)
    hits = 0
    for j in OFFSETS:
        ph, pc = high.copy(), close.copy()
        ph.iloc[j:] = other_h.iloc[j:].values
        pc.iloc[j:] = other_c.iloc[j:].values
        out = fn(ph, pc)
        a, b = base.iloc[:j], out.iloc[:j]
        if not (a.isna() == b.isna()).all():
            hits += 1
            continue
        m = a.notna()
        if (a[m] != b[m]).any():
            hits += 1
    return hits


def test_real_module_never_reads_the_future():
    assert _leaks(a101_023) == 0


def test_lookahead_mutant_is_caught():
    mod = _load_mutant(*MUTANT)
    high, close = _walk(1500)
    assert not mod.a101_023(high, close).equals(a101_023(high, close))  # live
    assert _leaks(mod.a101_023) == len(list(OFFSETS))  # caught, every offset


def test_weaker_mutant_is_under_sized():
    """Documents why the shipped mutant shifts the write index by 30 bars
    rather than by `length=20`: that weaker mutant is a real look-ahead
    (proved live below) but is caught only 32 of 35 offsets -- see
    docs/measure_a101_023.py for the same count reproduced independently."""
    weaker = _load_mutant(
        "result = result.where(mean_h.notna())",
        "result = result.where(mean_h.notna()).shift(-length)",
    )
    high, close = _walk(1500)
    assert not weaker.a101_023(high, close).equals(a101_023(high, close))
    assert _leaks(weaker.a101_023) == 32


# ------------------------------------------------------------ scale-free


@pytest.mark.parametrize("k", [8.0, 64.0])
def test_power_of_two_price_scale_is_bit_identical(k):
    high, close = _walk()
    base = a101_023(high, close)
    scaled = a101_023(high * k, close * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_other_price_scales_within_tolerance(k):
    high, close = _walk()
    base = a101_023(high, close)
    scaled = a101_023(high * k, close * k)
    assert (base.isna() == scaled.isna()).all()
    assert (base - scaled).abs().max() < 1e-9


def test_fires_and_is_not_constant():
    high, close = _walk()
    out = a101_023(high, close)
    fires = int(out.notna().sum())
    assert 0 < fires < len(out)
    assert out.dropna().nunique() > 1


# ---------------------------------------------------------------- wiring


def test_name_registration_and_accessor():
    high, close = _walk(400)
    df = pd.DataFrame({"open": close, "high": high, "low": close,
                        "close": close, "volume": close})
    assert "a101_023" in ta.Category["momentum"]
    out = df.ta.a101_023()
    assert out.name == "A101_023_20_2"
    pd.testing.assert_series_equal(out, a101_023(high, close))
    # both tunable kwargs forwarded under their own names in one call --
    # the "supertrend failure mode" (CLAUDE.md) hasattr cannot see.
    renamed = df.ta.a101_023(length=5, delta_length=3)
    assert renamed.name == "A101_023_5_3"
