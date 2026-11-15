# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.momentum.a101_043` -- Kakushadze's (2016, Wilmott)
Alpha101 `#43`, per issue #46: today's volume relative to its 20-bar average,
time-series ranked over the trailing 20 bars, multiplied by the negated 7-bar
price delta, time-series ranked over the trailing 8 bars. Gate A derivation
(including the disclosed ASSUMPTIONs -- `adv(d)` read as a plain volume
rolling mean, matching `a101_021`'s own resolution of the same ambiguity, and
`ts_rank` read as `count(window <= current) / d`, matching `a101_058`'s own
`_ts_rank`) is in the module docstring and `docs/A101043Measured.md`. Gate E
is pending (CLAUDE.md, "Owed, not failed").

What these pin, in order of how much it would hurt to lose:

* CAUSALITY by future-perturbation: rewrite every close/volume bar from `j`
  onward (another synthetic walk), demand bars `[0:j]` bit-identical with
  matching NaN masks, over offsets past the 38-bar warm-up. The shipped
  mutant (`importlib` source read, `exec`'d in memory) shifts the final
  write index `rev_rank_length=8` bars into the future (`result = (vrank *
  revrank).shift(-rev_rank_length)`): proved live, then caught at every
  offset (`python docs/measure_a101_043.py`). A weaker mutant was tried
  first and rejected as a quantisation artefact, not a causality gap: a
  1-bar lookahead on `d7` alone is a real look-ahead (proved live) but is
  only caught 25 of 35 offsets -- `ts_rank`'s bucketed output sometimes
  absorbs a 1-bar perturbation without changing bucket.
* CORRECTNESS: a hand-derived 6-bar example at `adv_length=2,
  vol_rank_length=2, delta_length=2, rev_rank_length=2`, computed by hand
  from the formula text, not by re-running the module. A second spot-check
  at the shipped defaults against an independent per-bar loop built from
  plain Python, not pandas' own `.rolling()`.
* SCALE-FREE: bit-identical under close x8/x64 AND under volume x8/x64
  independently (the volume half never reads `close`, the price half never
  reads `volume`, and `ts_rank` is an order statistic), also bit-identical
  (not merely within tolerance) under x10/x3.7 on this synthetic walk --
  measured, not assumed. Matching NaN masks, plus `0 < fires < n` and
  `nunique > 1`.
* Wiring: `Category`, the accessor, the column name `A101_043_20_20_7_8`.
"""
import importlib
import types

import numpy as np
import pandas as pd
import pytest
from pandas import Series

from .context import pandas_ta as ta
from pandas_ta.momentum.a101_043 import a101_043


def _walk(n=1500, seed=11, sigma=0.015):
    rng = np.random.default_rng(seed)
    close = 100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n)))
    volume = 1000.0 * np.exp(np.cumsum(rng.normal(0.0, sigma * 1.3, n)))
    idx = pd.RangeIndex(n)
    return Series(close, index=idx), Series(volume, index=idx)


# ------------------------------------------------------------ correctness


def test_hand_derived_six_bars():
    """close  = [10, 12, 11, 15, 9, 20]
    volume = [100, 50, 80, 40, 90, 30]
    adv_length=2, vol_rank_length=2, delta_length=2, rev_rank_length=2.

    adv[t] = mean(volume[t-1], volume[t]):
      adv[1]=75, adv[2]=65, adv[3]=60, adv[4]=65, adv[5]=60
    relvol[t] = volume[t]/adv[t]:
      relvol[1]=0.666667, relvol[2]=1.230769, relvol[3]=0.666667,
      relvol[4]=1.384615, relvol[5]=0.5
    vrank[t] = count(relvol[t-1:t+1] <= relvol[t]) / 2, valid t>=2:
      vrank[2]: window=[0.6667,1.2308], current=1.2308 -> count=2 -> 1.0
      vrank[3]: window=[1.2308,0.6667], current=0.6667 -> count=1 -> 0.5
      vrank[4]: window=[0.6667,1.3846], current=1.3846 -> count=2 -> 1.0
      vrank[5]: window=[1.3846,0.5],    current=0.5    -> count=1 -> 0.5

    d7[t] = close[t]-close[t-2], valid t>=2: d7[2]=1, d7[3]=3, d7[4]=-2, d7[5]=5
    neg_d7 = -d7: [-1, -3, 2, -5] at t=2..5
    revrank[t] = count(neg_d7[t-1:t+1] <= neg_d7[t]) / 2, valid t>=3:
      revrank[3]: window=[-1,-3], current=-3 -> count=1 -> 0.5
      revrank[4]: window=[-3,2],  current=2  -> count=2 -> 1.0
      revrank[5]: window=[2,-5],  current=-5 -> count=1 -> 0.5

    result[t] = vrank[t]*revrank[t], valid from max(2,3)=3:
      result[3]=0.5*0.5=0.25, result[4]=1.0*1.0=1.0, result[5]=0.5*0.5=0.25

    Derived by hand from the formula text, not by re-running the module.
    Reproduced in docs/measure_a101_043.py.
    """
    close = Series([10.0, 12.0, 11.0, 15.0, 9.0, 20.0])
    volume = Series([100.0, 50.0, 80.0, 40.0, 90.0, 30.0])
    out = a101_043(close, volume, adv_length=2, vol_rank_length=2,
                    delta_length=2, rev_rank_length=2)

    assert out.iloc[:3].isna().all()
    expected = {3: 0.25, 4: 1.0, 5: 0.25}
    for t, val in expected.items():
        assert out.iloc[t] == pytest.approx(val, abs=1e-12), f"bar {t}"


def test_matches_an_independent_loop_at_defaults():
    """Spot-checks 3 bars of the shipped defaults (adv_length=20,
    vol_rank_length=20, delta_length=7, rev_rank_length=8) against a
    hand-written per-bar loop using plain Python, independent of the
    module's `pandas .rolling()` / `sliding_window_view` calls."""
    close, volume = _walk(900, seed=3)
    out = a101_043(close, volume)
    c = close.to_numpy(dtype=float)
    v = volume.to_numpy(dtype=float)
    adv_length, vol_rank_length, delta_length, rev_rank_length = 20, 20, 7, 8

    def relvol_at(t):
        adv = sum(v[t - adv_length + 1:t + 1]) / adv_length
        return v[t] / adv

    def vrank_at(t):
        window = [relvol_at(t - vol_rank_length + 1 + i) for i in range(vol_rank_length)]
        current = window[-1]
        return sum(1 for x in window if x <= current) / vol_rank_length

    def neg_d7_at(t):
        return -(c[t] - c[t - delta_length])

    def revrank_at(t):
        window = [neg_d7_at(t - rev_rank_length + 1 + i) for i in range(rev_rank_length)]
        current = window[-1]
        return sum(1 for x in window if x <= current) / rev_rank_length

    for t in (100, 500, 899):
        expected = vrank_at(t) * revrank_at(t)
        assert out.iloc[t] == pytest.approx(expected, rel=1e-9)


def test_insufficient_history_returns_none():
    close, volume = _walk(38)  # defaults need max(39, 15) = 39 bars
    assert a101_043(close, volume) is None


def test_exact_min_length_fires_at_the_warmup_boundary():
    close, volume = _walk(39)  # exactly max(39, 15) = 39 bars
    out = a101_043(close, volume)
    assert out is not None
    assert out.iloc[:38].isna().all()
    assert pd.notna(out.iloc[38])


def test_default_name():
    close, volume = _walk()
    out = a101_043(close, volume)
    assert out.name == "A101_043_20_20_7_8"


def test_misaligned_index_raises():
    close, volume = _walk(50)
    volume = volume.copy()
    volume.index = volume.index + 1
    with pytest.raises(ValueError):
        a101_043(close, volume)


# -------------------------------------------------------------- causality


_REAL = importlib.import_module("pandas_ta.momentum.a101_043")


def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_a101_043_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


MUTANT = (
    "result = vrank * revrank",
    "result = (vrank * revrank).shift(-rev_rank_length)",  # a rev_rank_length-bar look-ahead
)

OFFSETS = range(100, 1500, 40)  # past the 38-bar warm-up


def _leaks(fn):
    close, volume = _walk(1500)
    other_c, other_v = _walk(1500, seed=97)
    base = fn(close, volume)
    hits = 0
    for j in OFFSETS:
        pc, pv = close.copy(), volume.copy()
        pc.iloc[j:] = other_c.iloc[j:].values
        pv.iloc[j:] = other_v.iloc[j:].values
        out = fn(pc, pv)
        a, b = base.iloc[:j], out.iloc[:j]
        if not (a.isna() == b.isna()).all():
            hits += 1
            continue
        m = a.notna()
        if (a[m] != b[m]).any():
            hits += 1
    return hits


def test_real_module_never_reads_the_future():
    assert _leaks(a101_043) == 0


def test_lookahead_mutant_is_caught():
    mod = _load_mutant(*MUTANT)
    close, volume = _walk(1500)
    assert not mod.a101_043(close, volume).equals(a101_043(close, volume))  # live
    assert _leaks(mod.a101_043) == len(list(OFFSETS))  # caught, every offset


def test_weaker_mutant_is_quantisation_limited():
    """Documents why the shipped mutant shifts the write index by the full
    `rev_rank_length` rather than by 1 bar inside `d7`: that weaker mutant is
    a real look-ahead (proved live below) but `ts_rank`'s bucketed output
    absorbs a 1-bar perturbation often enough to not be caught every time --
    see docs/measure_a101_043.py for the same count (25 of 35) reproduced
    independently."""
    one_bar = _load_mutant(
        "d7 = close.diff(delta_length)",
        "d7 = close.diff(delta_length).shift(-1)",
    )
    close, volume = _walk(1500)
    assert not one_bar.a101_043(close, volume).equals(a101_043(close, volume))
    assert _leaks(one_bar.a101_043) == 25


# ------------------------------------------------------------ scale-free


@pytest.mark.parametrize("k", [8.0, 64.0])
def test_power_of_two_price_scale_is_bit_identical(k):
    close, volume = _walk()
    base = a101_043(close, volume)
    scaled = a101_043(close * k, volume)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("k", [8.0, 64.0])
def test_power_of_two_volume_scale_is_bit_identical(k):
    close, volume = _walk()
    base = a101_043(close, volume)
    scaled = a101_043(close, volume * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_other_price_scales_within_tolerance(k):
    close, volume = _walk()
    base = a101_043(close, volume)
    scaled = a101_043(close * k, volume)
    assert (base.isna() == scaled.isna()).all()
    assert (base - scaled).abs().max() < 1e-9


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_other_volume_scales_within_tolerance(k):
    close, volume = _walk()
    base = a101_043(close, volume)
    scaled = a101_043(close, volume * k)
    assert (base.isna() == scaled.isna()).all()
    assert (base - scaled).abs().max() < 1e-9


def test_fires_and_is_not_constant():
    close, volume = _walk()
    out = a101_043(close, volume)
    fires = int(out.notna().sum())
    assert 0 < fires < len(out)
    assert out.dropna().nunique() > 1


# ---------------------------------------------------------------- wiring


def test_name_registration_and_accessor():
    close, volume = _walk(400)
    df = pd.DataFrame({"open": close, "high": close, "low": close,
                        "close": close, "volume": volume})
    assert "a101_043" in ta.Category["momentum"]
    out = df.ta.a101_043()
    assert out.name == "A101_043_20_20_7_8"
    pd.testing.assert_series_equal(out, a101_043(close, volume))
    # all four tunable kwargs forwarded under their own names in one call --
    # the "supertrend failure mode" (CLAUDE.md) hasattr cannot see.
    renamed = df.ta.a101_043(adv_length=2, vol_rank_length=2, delta_length=2,
                              rev_rank_length=2)
    assert renamed.name == "A101_043_2_2_2_2"
