# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.momentum.a101_007` -- Kakushadze's (2016, Wilmott)
Alpha101 `#7`, per issue #51: when volume exceeds its 20-bar average, the
negated time-series rank of the 7-bar absolute price move, signed by the
direction of that move; otherwise a flat `-1`. Gate A derivation (including
the disclosed ASSUMPTIONs -- `adv(d)` read as a plain volume rolling mean,
matching `a101_021`/`a101_043`'s own resolution of the same ambiguity, and
`ts_rank` read as `count(window <= current) / d`, matching `a101_043`'s and
`a101_058`'s own `_ts_rank`) is in the module docstring and
`docs/A101007Measured.md`. Gate E is pending (CLAUDE.md, "Owed, not failed").

What these pin, in order of how much it would hurt to lose:

* CAUSALITY by future-perturbation: rewrite every close/volume bar from `j`
  onward (another synthetic walk), demand bars `[0:j]` bit-identical with
  matching NaN masks, over offsets past the 67-bar warm-up. The shipped
  mutant (`importlib` source read, `exec`'d in memory) shifts the final write
  index `ts_rank_length=60` bars into the future (`result =
  result.where(mask).shift(-ts_rank_length)`): proved live, then caught at
  every offset (`python docs/measure_a101_007.py`). A weaker mutant was tried
  first and rejected as a quantisation artefact, not a causality gap: a
  1-bar lookahead on `d7` alone is a real look-ahead (proved live) but is
  only caught 17 of 35 offsets -- `ts_rank`'s bucketed output, and the flat
  `-1` fallback branch, both sometimes absorb a 1-bar perturbation without
  changing the observed value.
* CORRECTNESS: a hand-derived 7-bar example at `adv_length=2,
  delta_length=2, ts_rank_length=2`, computed by hand from the formula text,
  not by re-running the module, exercising both the gated branch (volume
  above its average) and the flat `-1` fallback (volume at or below it). A
  second spot-check at the shipped defaults against an independent per-bar
  loop built from plain Python, not pandas' own `.rolling()`.
* SCALE-FREE: bit-identical under close x8/x64 AND under volume x8/x64
  independently (the gate `volume > adv` never reads `close`, and the
  `tsrank`/`sign` half never reads `volume`), also bit-identical (not merely
  within tolerance) under x10/x3.7 on this synthetic walk -- measured, not
  assumed. Matching NaN masks, plus `0 < fires < n` and `nunique > 1`.
* Wiring: `Category`, the accessor, the column name `A101_007_20_7_60`.
"""
import importlib
import types

import numpy as np
import pandas as pd
import pytest
from pandas import Series

from .context import pandas_ta as ta
from pandas_ta.momentum.a101_007 import a101_007


def _walk(n=1500, seed=11, sigma=0.015):
    rng = np.random.default_rng(seed)
    close = 100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n)))
    volume = 1000.0 * np.exp(np.cumsum(rng.normal(0.0, sigma * 1.3, n)))
    idx = pd.RangeIndex(n)
    return Series(close, index=idx), Series(volume, index=idx)


# ------------------------------------------------------------ correctness


def test_hand_derived_seven_bars():
    """close  = [10, 12, 11, 15, 9, 20, 25]
    volume = [100, 50, 80, 40, 90, 30, 60]
    adv_length=2, delta_length=2, ts_rank_length=2.

    adv[t] = mean(volume[t-1], volume[t]), valid t>=1:
      adv[1]=75, adv[2]=65, adv[3]=60, adv[4]=65, adv[5]=60, adv[6]=45

    d7[t] = close[t]-close[t-2], valid t>=2:
      d7[2]=1, d7[3]=3, d7[4]=-2, d7[5]=5, d7[6]=16
    |d7|: [1, 3, 2, 5, 16] at t=2..6
    sign(d7): [1, 1, -1, 1, 1] at t=2..6

    tsrank[t] = count(|d7|[t-1:t+1] <= |d7|[t]) / 2, valid t>=3:
      tsrank[3]: window=[1,3], current=3 -> count=2 -> 1.0
      tsrank[4]: window=[3,2], current=2 -> count=1 -> 0.5
      tsrank[5]: window=[2,5], current=5 -> count=2 -> 1.0
      tsrank[6]: window=[5,16],current=16 -> count=2 -> 1.0

    gated[t] = -tsrank[t]*sign(d7[t]):
      gated[3]=-1.0*1=-1.0  gated[4]=-0.5*(-1)=0.5
      gated[5]=-1.0*1=-1.0  gated[6]=-1.0*1=-1.0

    gate: volume[t] > adv[t]?
      t=3: 40>60? No  -> fallback -1.0
      t=4: 90>65? Yes -> gated[4]=0.5
      t=5: 30>60? No  -> fallback -1.0
      t=6: 60>45? Yes -> gated[6]=-1.0

    result: bars 0..2 NaN (tsrank warm-up), then
      t=3: -1.0, t=4: 0.5, t=5: -1.0, t=6: -1.0

    Derived by hand from the formula text, not by re-running the module.
    Reproduced in docs/measure_a101_007.py.
    """
    close = Series([10.0, 12.0, 11.0, 15.0, 9.0, 20.0, 25.0])
    volume = Series([100.0, 50.0, 80.0, 40.0, 90.0, 30.0, 60.0])
    out = a101_007(close, volume, adv_length=2, delta_length=2, ts_rank_length=2)

    assert out.iloc[:3].isna().all()
    expected = {3: -1.0, 4: 0.5, 5: -1.0, 6: -1.0}
    for t, val in expected.items():
        assert out.iloc[t] == pytest.approx(val, abs=1e-12), f"bar {t}"


def test_matches_an_independent_loop_at_defaults():
    """Spot-checks 3 bars of the shipped defaults (adv_length=20,
    delta_length=7, ts_rank_length=60) against a hand-written per-bar loop
    using plain Python, independent of the module's `pandas .rolling()` /
    `sliding_window_view` calls."""
    close, volume = _walk(900, seed=3)
    out = a101_007(close, volume)
    c = close.to_numpy(dtype=float)
    v = volume.to_numpy(dtype=float)
    adv_length, delta_length, ts_rank_length = 20, 7, 60

    def adv_at(t):
        return sum(v[t - adv_length + 1:t + 1]) / adv_length

    def d7_at(t):
        return c[t] - c[t - delta_length]

    def tsrank_at(t):
        window = [abs(d7_at(t - ts_rank_length + 1 + i)) for i in range(ts_rank_length)]
        current = window[-1]
        return sum(1 for x in window if x <= current) / ts_rank_length

    def expected_at(t):
        gated = -tsrank_at(t) * np.sign(d7_at(t))
        return gated if v[t] > adv_at(t) else -1.0

    for t in (100, 500, 899):
        assert out.iloc[t] == pytest.approx(expected_at(t), rel=1e-9)


def test_insufficient_history_returns_none():
    close, volume = _walk(66)  # defaults need max(20, 67) = 67 bars
    assert a101_007(close, volume) is None


def test_exact_min_length_fires_at_the_warmup_boundary():
    close, volume = _walk(67)  # exactly max(20, 67) = 67 bars
    out = a101_007(close, volume)
    assert out is not None
    assert out.iloc[:66].isna().all()
    assert pd.notna(out.iloc[66])


def test_default_name():
    close, volume = _walk()
    out = a101_007(close, volume)
    assert out.name == "A101_007_20_7_60"


def test_misaligned_index_raises():
    close, volume = _walk(80)
    volume = volume.copy()
    volume.index = volume.index + 1
    with pytest.raises(ValueError):
        a101_007(close, volume)


# -------------------------------------------------------------- causality


_REAL = importlib.import_module("pandas_ta.momentum.a101_007")


def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_a101_007_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


MUTANT = (
    "result = result.where(mask)",
    "result = result.where(mask).shift(-ts_rank_length)",  # a ts_rank_length-bar look-ahead
)

OFFSETS = range(100, 1500, 40)  # past the 67-bar warm-up


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
    assert _leaks(a101_007) == 0


def test_lookahead_mutant_is_caught():
    mod = _load_mutant(*MUTANT)
    close, volume = _walk(1500)
    assert not mod.a101_007(close, volume).equals(a101_007(close, volume))  # live
    assert _leaks(mod.a101_007) == len(list(OFFSETS))  # caught, every offset


def test_weaker_mutant_is_quantisation_limited():
    """Documents why the shipped mutant shifts the write index by the full
    `ts_rank_length` rather than by 1 bar inside `d7`: that weaker mutant is
    a real look-ahead (proved live below) but `ts_rank`'s bucketed output and
    the flat `-1` fallback branch both absorb a 1-bar perturbation often
    enough to not be caught every time -- see docs/measure_a101_007.py for
    the same count reproduced independently."""
    one_bar = _load_mutant(
        "d7 = close.diff(delta_length)",
        "d7 = close.diff(delta_length).shift(-1)",
    )
    close, volume = _walk(1500)
    assert not one_bar.a101_007(close, volume).equals(a101_007(close, volume))
    assert _leaks(one_bar.a101_007) == 17


# ------------------------------------------------------------ scale-free


@pytest.mark.parametrize("k", [8.0, 64.0])
def test_power_of_two_price_scale_is_bit_identical(k):
    close, volume = _walk()
    base = a101_007(close, volume)
    scaled = a101_007(close * k, volume)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("k", [8.0, 64.0])
def test_power_of_two_volume_scale_is_bit_identical(k):
    close, volume = _walk()
    base = a101_007(close, volume)
    scaled = a101_007(close, volume * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_other_price_scales_within_tolerance(k):
    close, volume = _walk()
    base = a101_007(close, volume)
    scaled = a101_007(close * k, volume)
    assert (base.isna() == scaled.isna()).all()
    assert (base - scaled).abs().max() < 1e-9


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_other_volume_scales_within_tolerance(k):
    close, volume = _walk()
    base = a101_007(close, volume)
    scaled = a101_007(close, volume * k)
    assert (base.isna() == scaled.isna()).all()
    assert (base - scaled).abs().max() < 1e-9


def test_fires_and_is_not_constant():
    close, volume = _walk()
    out = a101_007(close, volume)
    fires = int(out.notna().sum())
    assert 0 < fires < len(out)
    assert out.dropna().nunique() > 1


# ---------------------------------------------------------------- wiring


def test_name_registration_and_accessor():
    close, volume = _walk(400)
    df = pd.DataFrame({"open": close, "high": close, "low": close,
                        "close": close, "volume": volume})
    assert "a101_007" in ta.Category["momentum"]
    out = df.ta.a101_007()
    assert out.name == "A101_007_20_7_60"
    pd.testing.assert_series_equal(out, a101_007(close, volume))
    # all three tunable kwargs forwarded under their own names in one call --
    # the "supertrend failure mode" (CLAUDE.md) hasattr cannot see.
    renamed = df.ta.a101_007(adv_length=2, delta_length=2, ts_rank_length=2)
    assert renamed.name == "A101_007_2_2_2"
