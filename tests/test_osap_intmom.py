# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.momentum.osap_intmom` -- intermediate momentum,
catalogued in the Open Source Asset Pricing (OSAP) SignalDoc as `IntMom`
(Novy-Marx 2012, OSAP t 5.79). Issue #40. Gate A disclosure (the
telescoping-return identity already used by `osap_mrrev` #37, and the
issue's own 126/252-bar conversion taken as given) is in the module
docstring and `docs/OsapIntmomMeasured.md`. Gate E is pending (CLAUDE.md,
"Owed, not failed").

What these pin, in order of how much it would hurt to lose:

* CAUSALITY by future-perturbation: rewrite every bar from `j` onward,
  INTMOM bars `[0:j]` bit-identical, over offsets past the 252-bar warm-up.
  A look-ahead mutant (`importlib` source read, the near-bar reference
  shifted from `close.shift(near_length)` to a shift that reads ahead of
  `t` -- `exec`'d in memory) is proved live, then caught at every offset.
* CORRECTNESS: a hand-derived 5-bar example (near_length=1, far_length=2, so
  every term is a plain shift, no rolling window) plus an independent
  per-bar loop over a longer synthetic walk at the shipped defaults.
* SCALE-FREE: bit-identical under close x8 and x64 (a ratio of two
  identically-scaled prices), within 1e-9 under x10 and x3.7, matching NaN
  masks, plus `0 < fires < n`.
* Wiring: `Category`, the accessor, and the column name `INTMOM_126_252`.
"""
import importlib
import types

import numpy as np
import pandas as pd
import pytest
from pandas import Series

from .context import pandas_ta as ta
from pandas_ta.momentum.osap_intmom import osap_intmom


def _walk(n=900, seed=17, sigma=0.015):
    rng = np.random.default_rng(seed)
    close = 100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n)))
    return Series(close)


# ------------------------------------------------------------ correctness


def test_hand_derived_five_bars():
    """near_length=1, far_length=2 -- every term is a plain shift, no rolling
    window, so the ratio is checked by hand.

    close = [100, 110, 99, 150, 200]
    idx2: close[1]/close[0]-1 = 110/100-1 = 0.10
    idx3: close[2]/close[1]-1 = 99/110-1  = -0.10
    idx4: close[3]/close[2]-1 = 150/99-1  = 51/99 = 17/33
    Derived by hand, not by re-running the module.
    """
    close = Series([100.0, 110.0, 99.0, 150.0, 200.0])
    out = osap_intmom(close, near_length=1, far_length=2)
    assert pd.isna(out.iloc[0])
    assert pd.isna(out.iloc[1])
    assert out.iloc[2] == pytest.approx(0.10, abs=1e-12)
    assert out.iloc[3] == pytest.approx(-0.10, abs=1e-12)
    assert out.iloc[4] == pytest.approx(17.0 / 33.0, abs=1e-12)


def test_matches_an_independent_per_bar_loop_at_defaults():
    close = _walk(900, seed=5)
    near_length, far_length = 126, 252
    out = osap_intmom(close, near_length=near_length, far_length=far_length)

    c = close.values
    for t in (300, 500, 700, 899):
        expected = c[t - near_length] / c[t - far_length] - 1
        assert out.iloc[t] == pytest.approx(expected, rel=1e-9)


def test_insufficient_history_returns_none():
    close = _walk(200)  # far_length default 252 needs 253 bars
    assert osap_intmom(close) is None


def test_near_length_not_less_than_far_length_returns_none():
    close = _walk(900)
    assert osap_intmom(close, near_length=252, far_length=126) is None


def test_offset_shifts_the_series():
    close = _walk(900)
    base = osap_intmom(close)
    shifted = osap_intmom(close, offset=1)
    pd.testing.assert_series_equal(shifted, base.shift(1), check_names=False)


def test_fillna_fills_the_warmup_nans():
    close = _walk(900)
    out = osap_intmom(close, fillna=0)
    assert not out.isna().any()
    assert (out.iloc[:252] == 0).all()


# -------------------------------------------------------------- causality


_REAL = importlib.import_module("pandas_ta.momentum.osap_intmom")


def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_osap_intmom_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


MUTANT = (
    "intmom = close.shift(near_length) / close.shift(far_length) - 1",
    "intmom = close.shift(near_length - 134) / close.shift(far_length) - 1",  # near_length=126 -> shift(-8): an 8-bar look-ahead
)

OFFSETS = range(400, 1225, 25)  # 33 offsets, all past the 252-bar warm-up


def _leaks(fn):
    close = _walk(1600)
    base = fn(close)
    other = _walk(1600, seed=99)
    hits = 0
    for j in OFFSETS:
        pc = close.copy()
        pc.iloc[j:] = other.iloc[j:].values
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
    assert _leaks(osap_intmom) == 0


def test_mutant_is_caught():
    mod = _load_mutant(*MUTANT)
    close = _walk(1600)
    assert not mod.osap_intmom(close).equals(osap_intmom(close))  # live
    assert _leaks(mod.osap_intmom) == len(OFFSETS)  # caught, every offset


# ------------------------------------------------------------ scale-free


@pytest.mark.parametrize("k", [8.0, 64.0])
def test_power_of_two_price_scale_is_bit_identical(k):
    close = _walk(900)
    base = osap_intmom(close)
    scaled = osap_intmom(close * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_other_scales_within_tolerance(k):
    close = _walk(900)
    base = osap_intmom(close)
    scaled = osap_intmom(close * k)
    assert (base.isna() == scaled.isna()).all()
    assert (base - scaled).abs().max() < 1e-9


def test_fires_and_is_not_constant():
    close = _walk(900)
    out = osap_intmom(close)
    fires = int(out.notna().sum())
    assert 0 < fires < len(out)
    assert out.dropna().nunique() > 100


# ---------------------------------------------------------------- wiring


def test_name_registration_and_accessor():
    close = _walk(900)
    df = pd.DataFrame({"open": close, "high": close, "low": close,
                       "close": close, "volume": close})
    assert "osap_intmom" in ta.Category["momentum"]
    out = df.ta.osap_intmom()
    assert out.name == "INTMOM_126_252"
    pd.testing.assert_series_equal(out, osap_intmom(close))
    assert df.ta.osap_intmom(near_length=1, far_length=2).name == "INTMOM_1_2"
