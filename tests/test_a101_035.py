# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.volume.a101_035` -- Kakushadze's (2016, Wilmott)
Alpha101 `#35`, per issue #50: `ts_rank(volume, 32) * (1 - ts_rank(close +
high - low, 16)) * (1 - ts_rank(returns, 32))`. Gate A derivation is in the
module docstring and `docs/A101035Measured.md`. Gate E is pending (CLAUDE.md,
"Owed, not failed").

What these pin, in order of how much it would hurt to lose:

* CAUSALITY by future-perturbation: rewrite every high/low/close/volume bar
  from `j` onward (another synthetic frame), demand bars `[0:j]`
  bit-identical with matching NaN masks, over offsets past the warm-up. A
  32-bar look-ahead mutant (`importlib` source read, the final write
  `result = vol_rank * (1 - pr_rank) * (1 - ret_rank)` wrapped in
  `.shift(-vol_length)`, `exec`'d in memory) is proved live, then caught at
  every offset. (A 1-bar look-ahead was tried first and rejected: caught
  only 29 of 30 offsets -- `ts_rank`'s integer-count quantisation sometimes
  absorbs a 1-bar perturbation without changing bucket -- re-derivable via
  `docs/measure_a101_035.py`'s "rejected single-bar-shift mutant" line, a
  quantisation artefact of the rank steps, not a causality gap. Widening the
  shift to a full window (32 bars, `vol_length`) is caught every time.)
* CORRECTNESS: a hand-derived 8-bar example at `vol_length=3, price_length=2,
  return_length=3`, plus a spot-check against an independent per-bar Python
  loop at the shipped defaults (32, 16, 32), built with plain `sum`/`count`,
  not `numpy.lib.stride_tricks`.
* SCALE-FREE: measured bit-identical under high/low/close x8/x64 AND under
  volume x8/x64 independently, AND -- measured, not merely asserted --
  bit-identical under x10/x3.7 too (see docs/A101035Measured.md for why
  that is an empirical finding on this frame, not a universal guarantee),
  matching NaN masks, plus `0 < fires < n`.
* Wiring: `Category`, the accessor, the column name `A101_035_32_16_32`.
"""
import importlib
import types

import numpy as np
import pandas as pd
import pytest
from pandas import Series

from .context import pandas_ta as ta
from pandas_ta.volume.a101_035 import a101_035


def _frame(n=1500, seed=11, sigma=0.015):
    rng = np.random.default_rng(seed)
    close = 100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n)))
    noise = np.abs(rng.normal(0.0, 0.3, n))
    high = close + noise
    low = close - noise
    volume = 1000.0 * np.exp(np.cumsum(rng.normal(0.0, sigma * 1.3, n)))
    idx = pd.RangeIndex(n)
    return (Series(high, index=idx), Series(low, index=idx),
            Series(close, index=idx), Series(volume, index=idx))


# ------------------------------------------------------------ correctness


def test_hand_derived_eight_bars_at_small_windows():
    """high - low is a constant 1.0, so price_term = close + high - low =
    close + 1 -- a monotonic shift of close, same rank order.

    close  = [10, 11, 9, 12, 8, 14, 13, 16]
    volume = [100, 200, 150, 300, 50, 400, 250, 500]
    vol_length=3, price_length=2, return_length=3. Combined warm-up:
    max(3-1, 2-1, 3) = 3, so bars 0-2 are NaN and bar 3 is the first valid
    one. Derived by hand from the formula (count(window <= current) /
    length for each rank, then vol_rank * (1-pr_rank) * (1-ret_rank)), not
    by re-running the module:
      t=3: vol_rank=3/3=1,   pr_rank=2/2=1,   ret_rank=3/3=1   -> 1*0*0 = 0
      t=4: vol_rank=1/3,     pr_rank=1/2,     ret_rank=1/3     -> (1/3)(1/2)(2/3) = 1/9
      t=5: vol_rank=3/3=1,   pr_rank=2/2=1,   ret_rank=3/3=1   -> 1*0*0 = 0
      t=6: vol_rank=2/3,     pr_rank=1/2,     ret_rank=2/3     -> (2/3)(1/2)(1/3) = 1/9
      t=7: vol_rank=3/3=1,   pr_rank=2/2=1,   ret_rank=2/3     -> 1*0*(1/3) = 0
    """
    close = Series([10.0, 11.0, 9.0, 12.0, 8.0, 14.0, 13.0, 16.0])
    high = close + 0.5
    low = close - 0.5
    volume = Series([100.0, 200.0, 150.0, 300.0, 50.0, 400.0, 250.0, 500.0])
    out = a101_035(high, low, close, volume, vol_length=3, price_length=2, return_length=3)

    assert out.iloc[0:3].isna().all()
    expected = {3: 0.0, 4: 1 / 9, 5: 0.0, 6: 1 / 9, 7: 0.0}
    for t, val in expected.items():
        assert out.iloc[t] == pytest.approx(val, abs=1e-12)


def test_matches_an_independent_loop_at_defaults():
    """Spot-checks 3 bars of the shipped defaults (vol_length=32,
    price_length=16, return_length=32) against a hand-written loop built
    from plain Python `sum`/comparisons, independent of the module's
    `numpy.lib.stride_tricks.sliding_window_view`."""
    high, low, close, volume = _frame(900, seed=3)
    out = a101_035(high, low, close, volume)

    c = close.to_numpy(dtype=float)
    h = high.to_numpy(dtype=float)
    l = low.to_numpy(dtype=float)
    v = volume.to_numpy(dtype=float)
    price_term = c + h - l
    returns = np.empty(len(c))
    returns[0] = np.nan
    returns[1:] = c[1:] / c[:-1] - 1.0

    def ts_rank_at(values, t, length):
        window = [values[t - length + 1 + i] for i in range(length)]
        current = window[-1]
        return sum(1 for x in window if x <= current) / length

    def expected_at(t):
        vr = ts_rank_at(v, t, 32)
        pr = ts_rank_at(price_term, t, 16)
        rr = ts_rank_at(returns, t, 32)
        return vr * (1 - pr) * (1 - rr)

    for t in (300, 500, 899):
        assert out.iloc[t] == pytest.approx(expected_at(t), rel=1e-9)


def test_insufficient_history_returns_none():
    high, low, close, volume = _frame(10)  # defaults need 33 bars
    assert a101_035(high, low, close, volume) is None


def test_default_name():
    high, low, close, volume = _frame()
    out = a101_035(high, low, close, volume)
    assert out.name == "A101_035_32_16_32"


# -------------------------------------------------------------- causality


_REAL = importlib.import_module("pandas_ta.volume.a101_035")


def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_a101_035_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


MUTANT = (
    "result = vol_rank * (1 - pr_rank) * (1 - ret_rank)",
    "result = (vol_rank * (1 - pr_rank) * (1 - ret_rank)).shift(-vol_length)",  # full-window look-ahead
)

OFFSETS = range(300, 900, 40)  # past the 32-bar warm-up


def _leaks(fn):
    high, low, close, volume = _frame(900)
    other_h, other_l, other_c, other_v = _frame(900, seed=97)
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
    assert _leaks(a101_035) == 0


def test_lookahead_mutant_is_caught():
    mod = _load_mutant(*MUTANT)
    high, low, close, volume = _frame(900)
    assert not mod.a101_035(high, low, close, volume).equals(a101_035(high, low, close, volume))  # live
    assert _leaks(mod.a101_035) == len(OFFSETS)  # caught, every offset


# ------------------------------------------------------------ scale-free


@pytest.mark.parametrize("k", [8.0, 64.0])
def test_power_of_two_price_scale_is_bit_identical(k):
    high, low, close, volume = _frame(900)
    base = a101_035(high, low, close, volume)
    scaled = a101_035(high * k, low * k, close * k, volume)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("k", [8.0, 64.0])
def test_power_of_two_volume_scale_is_bit_identical(k):
    high, low, close, volume = _frame(900)
    base = a101_035(high, low, close, volume)
    scaled = a101_035(high, low, close, volume * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_other_price_scales_measured_bit_identical(k):
    """Not a power of two, so exact IEEE754 cancellation in `returns`'
    division is not guaranteed -- measured bit-identical on this frame
    anyway (see module docstring's SCALE-FREE paragraph), not merely held
    to a tolerance."""
    high, low, close, volume = _frame(900)
    base = a101_035(high, low, close, volume)
    scaled = a101_035(high * k, low * k, close * k, volume)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_other_volume_scales_measured_bit_identical(k):
    high, low, close, volume = _frame(900)
    base = a101_035(high, low, close, volume)
    scaled = a101_035(high, low, close, volume * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] == scaled[m]).all()


def test_fires_and_is_not_constant():
    high, low, close, volume = _frame()
    out = a101_035(high, low, close, volume)
    fires = int(out.notna().sum())
    assert 0 < fires < len(out)
    assert out.dropna().nunique() > 1


def test_mismatched_index_raises():
    high, low, close, volume = _frame(900)
    bad_volume = volume.copy()
    bad_volume.index = bad_volume.index + 1
    with pytest.raises(ValueError):
        a101_035(high, low, close, bad_volume)


# ---------------------------------------------------------------- wiring


def test_name_registration_and_accessor():
    high, low, close, volume = _frame(900)
    df = pd.DataFrame({"open": close, "high": high, "low": low,
                        "close": close, "volume": volume})
    assert "a101_035" in ta.Category["volume"]
    out = df.ta.a101_035()
    assert out.name == "A101_035_32_16_32"
    pd.testing.assert_series_equal(out, a101_035(high, low, close, volume))
    renamed = df.ta.a101_035(vol_length=3, price_length=2, return_length=3)
    assert renamed.name == "A101_035_3_2_3"
