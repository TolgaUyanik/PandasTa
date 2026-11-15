# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.volume.g191_144` -- Guotai Junan's (2017,
"GTJA191") alpha `#144`, per issue #57: `SUMIF(|C/C1-1|/AMOUNT, C<C1, 20) /
COUNT(C<C1, 20)`, converted to its scale-free form per the issue's own
parenthetical ("divided by the all-day mean of |r|/AMOUNT over 20 bars;
AMOUNT -> TP*V") and the issue's own prototype
(`docs/issues/screen/ind_screen.py:485`):
`[SUMIF(x, C<C1, 20) / COUNT(C<C1, 20)] / MEAN(x, 20)`, `x = |C/C1-1| /
(TP*V)`. Gate A derivation is in the module docstring and
`docs/G191144Measured.md`. Gate E is pending (CLAUDE.md, "Owed, not
failed").

What these pin, in order of how much it would hurt to lose:

* CAUSALITY by future-perturbation: rewrite every OHLCV bar from `j`
  onward (another synthetic frame), demand bars `[0:j]` bit-identical with
  matching NaN masks, over offsets past the 21-bar warm-up. Two mutants
  (`importlib` source read, `exec`'d in memory), each shown live (differs
  from the real module) then caught at every offset: shifting the final
  write index `length=20` bars into the future, and flipping the backward
  `DELAY` (`close.shift(1)`, i.e. `C1`) into a FORWARD shift
  (`close.shift(-1)`) -- turning the previous-close reference into a
  look-ahead at the NEXT close (`python docs/measure_g191_144.py`).
* CORRECTNESS: a 6-bar hand-derived example at `length=3`, where high/low
  are built as `close +- 1` so the typical price collapses to `close`
  exactly, checked against an independent per-bar computation written
  directly in the test (not the module's own `.rolling()` calls). A second
  spot check at the shipped default against an independent per-bar loop
  using plain numpy, on a 900-bar frame.
* WARM-UP SUBTLETY: bar 0 has no `C1`, so its down/up status is undefined,
  not merely false. The module masks it out rather than letting a naive
  `close < close.shift(1)` (which reads `False`, not `NaN`, at bar 0) leak
  an arbitrary 0-contribution into the first rolling window. Pinned by
  comparing against an independent per-bar loop that applies the same
  mask.
* SCALE-FREE: `|C/C1-1|` is exactly invariant to a positive price rescale,
  and `AMOUNT = TP*V` scales by the SAME factor as any price-rescale times
  any volume-rescale, so `x`'s scale cancels identically between the
  down-day average and the all-day average -- the whole column is
  bit-identical under close x8/x64, volume x8/x64, AND both together
  (power-of-two, exact in IEEE754), and within float64 tolerance under
  x10/x3.7. Matching NaN masks, plus `0 < fires < n` and `nunique > 1`.
* Wiring: `Category`, the accessor, the column name `G191_144_20`.
"""
import importlib
import types

import numpy as np
import pandas as pd
import pytest
from pandas import Series

from .context import pandas_ta as ta
from pandas_ta.volume.g191_144 import g191_144


def _ohlcv(n=1500, seed=11, sigma=0.015, vol_seed=23):
    rng = np.random.default_rng(seed)
    close = 100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n)))
    rng2 = np.random.default_rng(seed + 1)
    spread = np.abs(rng2.normal(0.0, 0.01, n)) * close
    high = close + spread * rng2.uniform(0.2, 1.0, n)
    low = close - spread * rng2.uniform(0.2, 1.0, n)
    rng3 = np.random.default_rng(vol_seed)
    volume = np.abs(rng3.normal(1_000_000.0, 300_000.0, n)) + 1.0
    idx = pd.RangeIndex(n)
    return (Series(high, index=idx), Series(low, index=idx),
            Series(close, index=idx), Series(volume, index=idx))


# ------------------------------------------------------------ correctness


def test_hand_derived_six_bars():
    """length=3. high = close+1, low = close-1, so tp = close exactly,
    collapsing amount to close*volume.

    close = [10, 20, 30, 40, 22, 5], volume = [100, 200, 150, 300, 250, 400]
    amount[t] = close[t]*volume[t] = [1000, 4000, 4500, 12000, 5500, 2000]
    prior_close = [nan, 10, 20, 30, 40, 22]
    ret_abs[t] = |close[t]/prior_close[t] - 1|, valid t>=1:
      [nan, 1.0, 0.5, 0.333333..., 0.45, 0.772727...]
    x[t] = ret_abs[t]/amount[t], valid t>=1:
      [nan, 0.00025, 0.000111111..., 0.0000277778, 0.0000818182, 0.00038636...]
    down[t] = close[t] < prior_close[t], valid t>=1:
      [nan->masked, False, False, False, True, True]

    Bar 0's down-status is undefined (no C1), masked out of both SUMIF and
    COUNT -- not merely treated as "not a down day". Rolling window of 3
    over this masked series requires 3 DEFINED (non-masked) points, so the
    earliest the window [1,2,3] can be fully defined is t=3; at t=3 that
    window has ZERO down days (0/0 in down_avg -- still NaN). At t=4 the
    window [2,3,4] has one down day (t=4 itself): down_avg[4] = x[4]/1 =
    0.0000818182; all_avg[4] = mean(x[2],x[3],x[4]) = 0.0000735690.
    result[4] = 0.0000818182 / 0.0000735690 = 1.112128... At t=5 the window
    [3,4,5] has two down days: down_avg[5] = (x[4]+x[5])/2 = 0.0002340909;
    all_avg[5] = mean(x[3],x[4],x[5]) = 0.0001653199.
    result[5] = 0.0002340909 / 0.0001653199 = 1.415988...

    Checked to float precision against the module's actual output below
    (`python docs/measure_g191_144.py` prints the exact values).
    """
    close = Series([10.0, 20.0, 30.0, 40.0, 22.0, 5.0])
    high = close + 1.0
    low = close - 1.0
    volume = Series([100.0, 200.0, 150.0, 300.0, 250.0, 400.0])

    out = g191_144(high, low, close, volume, length=3)

    assert out.iloc[:4].isna().all()  # includes the zero-down-days bar at t=3
    expected = {4: 1.1121281464530892, 5: 1.4159877800407332}
    for t, val in expected.items():
        assert out.iloc[t] == pytest.approx(val, abs=1e-9), f"bar {t}"


def test_matches_an_independent_loop_at_defaults():
    """Spot-checks 3 bars of the shipped default (length=20) against an
    independent per-bar computation using plain numpy array slicing, not
    pandas' own `.rolling()` calls."""
    high, low, close, volume = _ohlcv(900, seed=5, vol_seed=71)
    out = g191_144(high, low, close, volume)
    h, l, c, v = (s.to_numpy(dtype=float) for s in (high, low, close, volume))
    tp = (h + l + c) / 3.0
    amount = tp * v
    length = 20

    def expected_at(t):
        idx = np.arange(t - length + 1, t + 1)  # all >= 1 since t >= length
        xi = np.abs(c[idx] / c[idx - 1] - 1.0) / amount[idx]
        downi = c[idx] < c[idx - 1]
        sumif = np.sum(np.where(downi, xi, 0.0))
        count = np.sum(downi.astype(float))
        return (sumif / count) / np.mean(xi)

    for t in (300, 600, 899):
        assert out.iloc[t] == pytest.approx(expected_at(t), rel=1e-9)


def test_insufficient_history_returns_none():
    high, low, close, volume = _ohlcv(20)  # defaults need length + 1 = 21 bars
    assert g191_144(high, low, close, volume) is None


def test_exact_min_length_fires_at_the_warmup_boundary():
    high, low, close, volume = _ohlcv(21)  # exactly length + 1 = 21 bars
    out = g191_144(high, low, close, volume)
    assert out is not None
    assert out.iloc[:20].isna().all()
    assert pd.notna(out.iloc[20])  # this seed has >= 1 down day among bars 1..20


def test_default_name():
    high, low, close, volume = _ohlcv()
    out = g191_144(high, low, close, volume)
    assert out.name == "G191_144_20"


def test_distinct_lengths_produce_distinct_names_and_values():
    high, low, close, volume = _ohlcv(400)
    out1 = g191_144(high, low, close, volume, length=10)
    out2 = g191_144(high, low, close, volume, length=15)
    assert out1.name != out2.name
    assert out1.name == "G191_144_10"
    assert out2.name == "G191_144_15"
    m = out1.notna() & out2.notna()
    assert (out1[m] != out2[m]).any()


# -------------------------------------------------------------- causality


_REAL = importlib.import_module("pandas_ta.volume.g191_144")


def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_g191_144_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


WRITE_SHIFT_MUTANT = (
    "result = (down_avg / all_avg).replace([np.inf, -np.inf], np.nan)",
    "result = (down_avg / all_avg).replace([np.inf, -np.inf], np.nan).shift(-length)",  # a length-bar look-ahead
)
FORWARD_DELAY_MUTANT = (
    "prior_close = close.shift(1)",
    "prior_close = close.shift(-1)",  # C1 turned into a look-ahead at the NEXT close
)

OFFSETS = range(150, 1500, 40)  # past the 21-bar warm-up


def _leaks(fn):
    high, low, close, volume = _ohlcv(1500)
    other_h, other_l, other_c, other_v = _ohlcv(1500, seed=97, vol_seed=71)
    base = fn(high, low, close, volume)
    hits = 0
    for j in OFFSETS:
        ph, pl, pc, pv = high.copy(), low.copy(), close.copy(), volume.copy()
        ph.iloc[j:] = other_h.iloc[j:].values
        pl.iloc[j:] = other_l.iloc[j:].values
        pc.iloc[j:] = other_c.iloc[j:].values
        pv.iloc[j:] = other_v.iloc[j:].values
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
    assert _leaks(g191_144) == 0


def test_write_shift_mutant_is_caught():
    mod = _load_mutant(*WRITE_SHIFT_MUTANT)
    high, low, close, volume = _ohlcv(1500)
    assert not mod.g191_144(high, low, close, volume).equals(g191_144(high, low, close, volume))  # live
    assert _leaks(mod.g191_144) == len(list(OFFSETS))  # caught, every offset


def test_forward_delay_mutant_is_caught():
    mod = _load_mutant(*FORWARD_DELAY_MUTANT)
    high, low, close, volume = _ohlcv(1500)
    assert not mod.g191_144(high, low, close, volume).equals(g191_144(high, low, close, volume))  # live
    assert _leaks(mod.g191_144) == len(list(OFFSETS))  # caught, every offset


# ------------------------------------------------------------ scale-free


@pytest.mark.parametrize("k", [8.0, 64.0])
def test_power_of_two_price_scale_is_bit_identical(k):
    high, low, close, volume = _ohlcv()
    base = g191_144(high, low, close, volume)
    scaled = g191_144(high * k, low * k, close * k, volume)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_other_price_scales_within_tolerance(k):
    high, low, close, volume = _ohlcv()
    base = g191_144(high, low, close, volume)
    scaled = g191_144(high * k, low * k, close * k, volume)
    assert (base.isna() == scaled.isna()).all()
    assert (base - scaled).abs().max() < 1e-9


@pytest.mark.parametrize("k", [8.0, 64.0])
def test_power_of_two_volume_scale_is_bit_identical(k):
    high, low, close, volume = _ohlcv()
    base = g191_144(high, low, close, volume)
    scaled = g191_144(high, low, close, volume * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_other_volume_scales_within_tolerance(k):
    high, low, close, volume = _ohlcv()
    base = g191_144(high, low, close, volume)
    scaled = g191_144(high, low, close, volume * k)
    assert (base.isna() == scaled.isna()).all()
    assert (base - scaled).abs().max() < 1e-9


@pytest.mark.parametrize("k", [8.0, 64.0])
def test_power_of_two_combined_scale_is_bit_identical(k):
    high, low, close, volume = _ohlcv()
    base = g191_144(high, low, close, volume)
    scaled = g191_144(high * k, low * k, close * k, volume * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_other_combined_scales_within_tolerance(k):
    high, low, close, volume = _ohlcv()
    base = g191_144(high, low, close, volume)
    scaled = g191_144(high * k, low * k, close * k, volume * k)
    assert (base.isna() == scaled.isna()).all()
    assert (base - scaled).abs().max() < 1e-9


def test_fires_and_is_not_constant():
    high, low, close, volume = _ohlcv()
    out = g191_144(high, low, close, volume)
    fires = int(out.notna().sum())
    assert 0 < fires < len(out)
    assert out.dropna().nunique() > 1


# ---------------------------------------------------------------- wiring


def test_name_registration_and_accessor():
    high, low, close, volume = _ohlcv(400)
    df = pd.DataFrame({"open": close, "high": high, "low": low, "close": close,
                        "volume": volume})
    assert "g191_144" in ta.Category["volume"]
    out = df.ta.g191_144()
    assert out.name == "G191_144_20"
    pd.testing.assert_series_equal(out, g191_144(high, low, close, volume))
    # tunable kwarg forwarded under its own name -- the "supertrend failure
    # mode" (CLAUDE.md) hasattr cannot see.
    renamed = df.ta.g191_144(length=10)
    assert renamed.name == "G191_144_10"
