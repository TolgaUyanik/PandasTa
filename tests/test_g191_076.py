# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.volume.g191_076` -- Guotai Junan's (2017,
"GTJA191") alpha `#76`, per issue #54: `STD(|C/C1-1|/V,20) /
MEAN(|C/C1-1|/V,20)`, the rolling coefficient of variation of the absolute
one-bar return divided by volume. Gate A derivation is in the module
docstring and `docs/G191076Measured.md`. Gate E is pending (CLAUDE.md,
"Owed, not failed").

What these pin, in order of how much it would hurt to lose:

* CAUSALITY by future-perturbation: rewrite every close/volume bar from `j`
  onward (another synthetic series), demand bars `[0:j]` bit-identical with
  matching NaN masks, over offsets past the 20-bar warm-up. Two mutants
  (`importlib` source read, `exec`'d in memory), each shown live (differs
  from the real module) then caught at every offset: shifting the final
  write index `length=20` bars into the future, and computing
  `STD`/`MEAN` with `center=True` -- the same look-ahead bug class
  CLAUDE.md documents for `bos`'s `rolling(..., center=True)`
  (`python docs/measure_g191_076.py`).
* CORRECTNESS: a 6-bar hand-derived example at `length=3`, checked against
  an independent per-bar computation built from `ret_c = c/c.shift(1)-1`,
  `x = |ret_c|/v`, `std_x`/`mean_x` as explicit rolling windows -- the exact
  values printed by `docs/measure_g191_076.py`. A second spot check at the
  shipped default (`length=20`) against an independent per-bar loop using
  plain numpy (`np.std(ddof=1)`, `np.mean`), not pandas' own `.rolling()`.
* SCALE-FREE: `ret_c` is exactly scale-free under a positive price rescale
  (the `k` cancels inside `C/C1`, so price scale never reaches `x`); `x`
  scales by `1/k` under a positive volume rescale, and `STD`/`MEAN` are
  both linear in a positive scalar multiple, so the ratio `std_x/mean_x`
  is exactly invariant under ANY `k > 0` -- bit-identical under BOTH close
  x8/x64 and volume x8/x64 (power-of-two, exact in IEEE754), and within
  float64 tolerance under x10/x3.7. Matching NaN masks, plus
  `0 < fires < n` and `nunique > 1`.
* Wiring: `Category`, the accessor, the column name `G191_076_20`.
"""
import importlib
import types

import numpy as np
import pandas as pd
import pytest
from pandas import Series

from .context import pandas_ta as ta
from pandas_ta.volume.g191_076 import g191_076


def _cv(n=1500, seed=11, sigma=0.015, vol_seed=23):
    rng = np.random.default_rng(seed)
    close = 100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n)))
    rng3 = np.random.default_rng(vol_seed)
    volume = np.abs(rng3.normal(1_000_000.0, 300_000.0, n)) + 1.0
    idx = pd.RangeIndex(n)
    return Series(close, index=idx), Series(volume, index=idx)


# ------------------------------------------------------------ correctness


def test_hand_derived_six_bars():
    """length=3: ret_c, x=|ret_c|/v, std_x/mean_x over explicit 3-bar
    windows (ddof=1). Checked to float precision against the module's
    actual output below (`python docs/measure_g191_076.py` prints the exact
    values)."""
    close = Series([10.0, 11.0, 9.0, 12.0, 8.0, 13.0])
    volume = Series([100.0, 200.0, 150.0, 300.0, 250.0, 400.0])

    out = g191_076(close, volume, length=3)

    assert out.iloc[:3].isna().all()
    expected = {
        3: 0.409433501628981,
        4: 0.09128569967877538,
        5: 0.16898413531713724,
    }
    for t, val in expected.items():
        assert out.iloc[t] == pytest.approx(val, abs=1e-9), f"bar {t}"


def test_matches_an_independent_loop_at_defaults():
    """Spot-checks 3 bars of the shipped default (length=20) against an
    independent per-bar computation using plain numpy (`np.std(ddof=1)`,
    `np.mean` over explicit slices), not pandas' `.rolling()`."""
    close, volume = _cv(900, seed=3)
    out = g191_076(close, volume)
    c = close.to_numpy(dtype=float)
    v = volume.to_numpy(dtype=float)
    length = 20
    ret_c = c[1:] / c[:-1] - 1.0
    x = np.empty_like(c)
    x[0] = np.nan
    x[1:] = np.abs(ret_c) / v[1:]

    def expected_at(t):
        window = x[t - length + 1:t + 1]
        return np.std(window, ddof=1) / np.mean(window)

    for t in (300, 600, 899):
        assert out.iloc[t] == pytest.approx(expected_at(t), rel=1e-9)


def test_insufficient_history_returns_none():
    close, volume = _cv(20)  # defaults need length + 1 = 21 bars
    assert g191_076(close, volume) is None


def test_exact_min_length_fires_at_the_warmup_boundary():
    close, volume = _cv(21)  # exactly length + 1 = 21 bars
    out = g191_076(close, volume)
    assert out is not None
    assert out.iloc[:20].isna().all()
    assert pd.notna(out.iloc[20])


def test_default_name():
    close, volume = _cv()
    out = g191_076(close, volume)
    assert out.name == "G191_076_20"


def test_distinct_lengths_produce_distinct_names_and_values():
    close, volume = _cv(300)
    out1 = g191_076(close, volume, length=10)
    out2 = g191_076(close, volume, length=15)
    assert out1.name != out2.name
    assert out1.name == "G191_076_10"
    assert out2.name == "G191_076_15"
    m = out1.notna() & out2.notna()
    assert (out1[m] != out2[m]).any()


# -------------------------------------------------------------- causality


_REAL = importlib.import_module("pandas_ta.volume.g191_076")


def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_g191_076_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


WRITE_SHIFT_MUTANT = (
    "result = (std_x / mean_x).replace([np.inf, -np.inf], np.nan)",
    "result = (std_x / mean_x).replace([np.inf, -np.inf], np.nan).shift(-length)",  # a length-bar look-ahead
)
CENTERED_WINDOW_MUTANT = (
    "std_x = x.rolling(length).std()\n    mean_x = x.rolling(length).mean()",
    "std_x = x.rolling(length, center=True).std()\n    mean_x = x.rolling(length, center=True).mean()",  # the `bos` look-ahead bug class
)

OFFSETS = range(150, 1500, 40)  # past the 20-bar warm-up


def _leaks(fn):
    close, volume = _cv(1500)
    other_c, other_v = _cv(1500, seed=97, vol_seed=71)
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
    assert _leaks(g191_076) == 0


def test_write_shift_mutant_is_caught():
    mod = _load_mutant(*WRITE_SHIFT_MUTANT)
    close, volume = _cv(1500)
    assert not mod.g191_076(close, volume).equals(g191_076(close, volume))  # live
    assert _leaks(mod.g191_076) == len(list(OFFSETS))  # caught, every offset


def test_centered_window_mutant_is_caught():
    mod = _load_mutant(*CENTERED_WINDOW_MUTANT)
    close, volume = _cv(1500)
    assert not mod.g191_076(close, volume).equals(g191_076(close, volume))  # live
    assert _leaks(mod.g191_076) == len(list(OFFSETS))  # caught, every offset


# ------------------------------------------------------------ scale-free


@pytest.mark.parametrize("k", [8.0, 64.0])
def test_power_of_two_price_scale_is_bit_identical(k):
    close, volume = _cv()
    base = g191_076(close, volume)
    scaled = g191_076(close * k, volume)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_other_price_scales_within_tolerance(k):
    close, volume = _cv()
    base = g191_076(close, volume)
    scaled = g191_076(close * k, volume)
    assert (base.isna() == scaled.isna()).all()
    assert (base - scaled).abs().max() < 1e-9


@pytest.mark.parametrize("k", [8.0, 64.0])
def test_power_of_two_volume_scale_is_bit_identical(k):
    close, volume = _cv()
    base = g191_076(close, volume)
    scaled = g191_076(close, volume * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_other_volume_scales_within_tolerance(k):
    close, volume = _cv()
    base = g191_076(close, volume)
    scaled = g191_076(close, volume * k)
    assert (base.isna() == scaled.isna()).all()
    assert (base - scaled).abs().max() < 1e-9


def test_fires_and_is_not_constant():
    close, volume = _cv()
    out = g191_076(close, volume)
    fires = int(out.notna().sum())
    assert 0 < fires < len(out)
    assert out.dropna().nunique() > 1


# ---------------------------------------------------------------- wiring


def test_name_registration_and_accessor():
    close, volume = _cv(400)
    df = pd.DataFrame({"open": close, "high": close, "low": close, "close": close,
                        "volume": volume})
    assert "g191_076" in ta.Category["volume"]
    out = df.ta.g191_076()
    assert out.name == "G191_076_20"
    pd.testing.assert_series_equal(out, g191_076(close, volume))
    renamed = df.ta.g191_076(length=10)
    assert renamed.name == "G191_076_10"
