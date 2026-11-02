# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.volume.demand` -- Sibbet's Demand Index / Aspray's
Demand Oscillator, Kaufman's (2013, ch. 12) reading, volume-normalised so the
column is scale-free. Gate A risk and the three undocumented reading
decisions are in the module docstring ("WHAT IS ASSUMED") and
docs/DemandMeasured.md. Gate E is pending (CLAUDE.md, "Owed, not failed").

What these pin, in order of how much it would hurt to lose:

* CAUSALITY by future-perturbation: rewrite every bar from `j` onward, demand
  bars `[0:j]` bit-identical, over 31 offsets. A look-ahead mutant
  (`importlib` source read, `pct_chg` read one bar ahead, `exec`'d in memory)
  is proved live, then caught at 31 of 31.
* SCALE-FREE: bit-identical under x8 and x64 on BOTH the price axis (high,
  low, close together) and the volume axis independently, within 1e-9 under
  x10 and x3.7 on both, with matching NaN masks, plus `0 < fires < n`.
* The ΔC == 0 guard (the issue's own flagged risk): an unchanged close reads
  EXACTLY 0, not a division blow-up -- this is the guard, not a special case
  bolted on afterward.
* CORRECTNESS: two hand-derived bars (rising then falling, length=1,
  vol_length=1 so every rolling window is a no-op) plus an independent
  per-bar loop over a longer synthetic walk.
* Wiring: `Category`, the accessor, and the column name `DEMAND_10_10`.
"""
import importlib
import types

import numpy as np
import pandas as pd
import pytest
from pandas import Series

from .context import pandas_ta as ta
from pandas_ta.volume.demand import demand


def _walk(n=1200, seed=17, sigma=0.015, tick=0.05):
    rng = np.random.default_rng(seed)
    close = 100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n)))
    if tick:
        close = np.round(close / tick) * tick
    spread = np.abs(rng.normal(0.0, 0.01, n)) * close + (tick or 0.0)
    high = close + spread
    low = close - spread
    volume = rng.integers(1e4, 1e6, n).astype(float)
    return Series(high), Series(low), Series(close), Series(volume)


# ------------------------------------------------------------ correctness


def test_hand_derived_rising_then_falling_bar():
    """3 bars, length=1, vol_length=1 (every rolling window is a no-op
    except the 2-bar range max).

    bar0: H=10 L=9 (range 1) C=100 V=1000
    bar1: H=11 L=9 (range 2) C=110 V=2000 -- +10% from bar0
    bar2: H=10 L=8 (range 2) C=99  V=1500 -- exactly -10% from bar1

    bar1: range2=max(1,2)=2, K=3*110/2=165, pct_chg=0.10, denom=16.5
          SP=2000/16.5=4000/33, raw=2000-4000/33=62000/33, out=31/33
    bar2: range2=max(2,2)=2, K=3*99/2=148.5, pct_chg=-0.10, denom=-14.85
          BP=1500/14.85=10000/99, raw=10000/99-1500=-138500/99, out=-277/297
    Derived by hand, not by re-running the module.
    """
    high = Series([10.0, 11.0, 10.0])
    low = Series([9.0, 9.0, 8.0])
    close = Series([100.0, 110.0, 99.0])
    volume = Series([1000.0, 2000.0, 1500.0])
    out = demand(high, low, close, volume, length=1, vol_length=1)
    assert pd.isna(out.iloc[0])
    assert out.iloc[1] == pytest.approx(31.0 / 33.0, abs=1e-12)
    assert out.iloc[2] == pytest.approx(-277.0 / 297.0, abs=1e-12)


def test_unchanged_close_reads_exactly_zero():
    """The issue's flagged risk: BIST tick rounding makes ΔC = 0 common, and
    division by it must not blow up. Appending a 4th bar whose close repeats
    bar2's close (99 -> 99) must read exactly 0.0, not NaN or inf."""
    high = Series([10.0, 11.0, 10.0, 10.0])
    low = Series([9.0, 9.0, 8.0, 8.0])
    close = Series([100.0, 110.0, 99.0, 99.0])
    volume = Series([1000.0, 2000.0, 1500.0, 1700.0])
    out = demand(high, low, close, volume, length=1, vol_length=1)
    assert out.iloc[3] == 0.0


def test_flat_bar_inside_the_k_warmup_gap_is_nan_not_zero():
    """REVIEW ROUND 1 (Fletcher, CRITICAL): `avg_vol` (rolling(vol_length))
    and `k` (needs range_sma, which warms up ONE bar later than a plain
    rolling(length) because of the leading `rolling(2).max()`) do not become
    valid on the same bar. At the shipped default (length=vol_length=10),
    avg_vol is first valid at index 9 but k is first valid at index 10 --
    a 1-row gap where a flat close (the issue's own ΔC=0 failure mode) used
    to fall into the flat branch and read a fabricated 0.0 at index 9
    instead of NaN, because the guard only checked pct_chg.notna(), not
    k.notna(). Engineered here: close[9] == close[8] exactly."""
    n = 15
    close = Series([100.0 + i for i in range(n)])
    close.iloc[9] = close.iloc[8]  # force pct_chg[9] == 0.0 exactly
    high = close + 1.0
    low = close - 1.0
    volume = Series([1000.0] * n)
    out = demand(high, low, close, volume, length=10, vol_length=10)
    assert pd.isna(out.iloc[9])


def test_flat_bar_inside_an_asymmetric_k_warmup_gap_is_nan_not_zero():
    """Same bug, wider window: with vol_length << length, avg_vol is valid
    from index `vol_length - 1` while k is not valid until index `length`,
    so EVERY flat bar across that whole stretch was affected pre-fix, not
    just one row. length=50, vol_length=5: avg_vol valid from index 4, k
    not valid until index 50 -- a flat bar placed at index 20 (deep inside
    the gap) must read NaN."""
    n = 60
    close = Series([100.0 + i for i in range(n)])
    close.iloc[20] = close.iloc[19]  # force pct_chg[20] == 0.0 exactly
    high = close + 1.0
    low = close - 1.0
    volume = Series([1000.0] * n)
    out = demand(high, low, close, volume, length=50, vol_length=5)
    assert pd.isna(out.iloc[20])


def test_matches_an_independent_per_bar_loop():
    high, low, close, volume = _walk(400, seed=5)
    length, vol_length = 10, 10
    out = demand(high, low, close, volume, length=length, vol_length=vol_length)

    h, l, c, v = high.values, low.values, close.values, volume.values
    rng_ = h - l
    rng2 = np.array([max(rng_[i - 1], rng_[i]) if i >= 1 else np.nan for i in range(len(c))])

    for t in (30, 120, 250, 399):
        window = rng2[t - length + 1: t + 1]
        if np.isnan(window).any() or window.mean() <= 0:
            continue
        k = 3.0 * c[t] / window.mean()
        pct = (c[t] - c[t - 1]) / c[t - 1]
        denom = k * pct
        if pct > 0:
            bp, sp = v[t], v[t] / denom
        elif pct < 0:
            bp, sp = v[t] / abs(denom), v[t]
        else:
            bp, sp = v[t], v[t]
        avg_vol = v[t - vol_length + 1: t + 1].mean()
        expected = (bp - sp) / avg_vol
        assert out.iloc[t] == pytest.approx(expected, rel=1e-9)


def test_insufficient_history_returns_none():
    high, low, close, volume = _walk(5)
    assert demand(high, low, close, volume, length=10, vol_length=10) is None


# -------------------------------------------------------------- causality


_REAL = importlib.import_module("pandas_ta.volume.demand")


def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_demand_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


MUTANT = (
    "pct_chg = close.pct_change()",
    "pct_chg = close.pct_change().shift(-1)",
)

OFFSETS = range(40, 1100, 35)  # 31 offsets


def _leaks(fn):
    high, low, close, volume = _walk()
    base = fn(high, low, close, volume)
    oh, ol, oc, ov = _walk(seed=99)
    hits = 0
    for j in OFFSETS:
        ph, pl, pc, pv = high.copy(), low.copy(), close.copy(), volume.copy()
        ph.iloc[j:] = oh.iloc[j:].values
        pl.iloc[j:] = ol.iloc[j:].values
        pc.iloc[j:] = oc.iloc[j:].values
        pv.iloc[j:] = ov.iloc[j:].values
        out = fn(ph, pl, pc, pv)
        a, b = base.iloc[:j], out.iloc[:j]
        if not (a.isna() == b.isna()).all():
            hits += 1
            continue
        m = a.notna()
        if (a[m] != b[m]).any():
            hits += 1
    return hits


def test_real_module_never_reads_the_future():
    assert _leaks(demand) == 0


def test_mutant_is_caught():
    mod = _load_mutant(*MUTANT)
    high, low, close, volume = _walk()
    assert not mod.demand(high, low, close, volume).equals(demand(high, low, close, volume))  # live
    assert _leaks(mod.demand) == len(OFFSETS)  # caught, 31 of 31


# ------------------------------------------------------------ scale-free


@pytest.mark.parametrize("k", [8.0, 64.0])
def test_power_of_two_price_scale_is_bit_identical(k):
    high, low, close, volume = _walk()
    base = demand(high, low, close, volume)
    scaled = demand(high * k, low * k, close * k, volume)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("k", [8.0, 64.0])
def test_power_of_two_volume_scale_is_bit_identical(k):
    high, low, close, volume = _walk()
    base = demand(high, low, close, volume)
    scaled = demand(high, low, close, volume * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_other_scales_within_tolerance(k):
    high, low, close, volume = _walk()
    base = demand(high, low, close, volume)
    price_scaled = demand(high * k, low * k, close * k, volume)
    vol_scaled = demand(high, low, close, volume * k)
    for scaled in (price_scaled, vol_scaled):
        assert (base.isna() == scaled.isna()).all()
        assert (base - scaled).abs().max() < 1e-9


def test_fires_and_is_not_constant():
    high, low, close, volume = _walk()
    out = demand(high, low, close, volume)
    fires = int(out.notna().sum())
    assert 0 < fires < len(out)
    assert out.dropna().nunique() > 100


# ---------------------------------------------------------------- wiring


def test_name_registration_and_accessor():
    high, low, close, volume = _walk(200)
    df = pd.DataFrame({"open": close, "high": high, "low": low,
                       "close": close, "volume": volume})
    assert "demand" in ta.Category["volume"]
    out = df.ta.demand()
    assert out.name == "DEMAND_10_10"
    pd.testing.assert_series_equal(out, demand(high, low, close, volume))
    assert df.ta.demand(length=5, vol_length=20).name == "DEMAND_5_20"
