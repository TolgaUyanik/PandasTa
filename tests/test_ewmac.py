# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.momentum.ewmac` -- Carver's volatility-normalised EMA
crossover (issue #29): `(EMA_fast(close) - EMA_slow(close)) / sigma`. Carver
gives six speed pairs; Gate E (measured 2026-11-01, `docs/EwmacMeasured.md`)
STRUCK five of them against existing engine columns (pooled |rho|
0.9175-0.9945 vs `pgo`, `smi_SMI_5_20_5`, `tsi`, `ICHI_CHIKOU_VS_CLOUD`,
`Dist_to_SMA_200_pct`) and they were removed. Only **64:256** ships now, at
DISCLOSE_GAP (0.8744 vs `SMA_200_Slope_pct`). Raw ratio only -- no forecast
scalar, no cap, per the issue's own Gate A note.

Carver's book gives the family and the pairs, not a line-numbered source
file, so CORRECTNESS is checked by reassembling the formula from literal
`pandas` primitives in this test (not by importing the module's internals)
and by a hand-computed 3-bar EMA recursion -- the same "no oracle, so check
the formula" pattern used for `pfe` and `ie_asym`.

What these tests pin, in order of how much it would hurt to lose them:

* CAUSALITY by future-rewrite: rewrite every bar from `j` onward with a
  second, unrelated walk; demand bars `[0:j]` bit-identical, over 31
  offsets. Two look-ahead mutants (`importlib` source read, one line
  changed to read a future bar, `exec`'d in memory -- never a hand-written
  copy) are each proved live, then caught at 31 of 31.
* SCALE-FREE: bit-identical under x8 and x64 (EMA and EWMA-std are both
  linear/homogeneous in `close` under exact power-of-two scaling), within
  1e-9 under x10 and x3.7 with matching NaN masks, and `0 < fires < n`.
* CORRECTNESS: a hand-computed 3-bar EMA recursion for the surviving 64:256
  pair, and a 400-bar random walk reassembled from the literal formula
  (`close.ewm(span=L, adjust=False).mean()`, `close.diff().ewm(span=35,
  adjust=False).std()`) independently of the module's own code path.
* Wiring: `Category`, the accessor, and the one column name.
"""
import importlib
import types

import numpy as np
import pandas as pd
import pytest
from pandas import DataFrame, Series

from .context import pandas_ta as ta
from pandas_ta.momentum.ewmac import ewmac, PAIRS


def _walk(n=1200, seed=11, sigma=0.02, tick=None):
    rng = np.random.default_rng(seed)
    c = 100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n)))
    if tick:
        c = np.round(c / tick) * tick
    return Series(c)


# ------------------------------------------------------------ correctness


def test_hand_computed_three_bar_recursion():
    # close = [10, 11, 13, ...300 more bars]; fast=64 (alpha=2/65), slow=256
    # (alpha=2/257); no SMA seed, e0 = close[0], e_t = (1-alpha)*e_{t-1} +
    # alpha*close_t. causality (proven separately below) guarantees bars
    # >= 3 cannot move bar 2.
    close = Series([10.0, 11.0, 13.0] + [100.0] * 300)
    fast, slow = 64, 256
    af, as_ = 2 / (fast + 1), 2 / (slow + 1)
    fast_e2 = (1 - af) * ((1 - af) * 10 + af * 11) + af * 13
    slow_e2 = (1 - as_) * ((1 - as_) * 10 + as_ * 11) + as_ * 13
    expected_numerator = fast_e2 - slow_e2

    out = ewmac(close)["EWMAC_64_256_35"]
    sigma = close.diff().ewm(span=35, adjust=False).std()
    numerator = out * sigma
    assert numerator.iloc[2] == pytest.approx(expected_numerator, abs=1e-9)


def test_matches_a_formula_reassembled_independently():
    close = _walk(400)
    vol_length = 35
    sigma = close.diff().ewm(span=vol_length, adjust=False).std()
    out = ewmac(close)
    for fast, slow in PAIRS:
        fastma = close.ewm(span=fast, adjust=False).mean()
        slowma = close.ewm(span=slow, adjust=False).mean()
        expected = (fastma - slowma) / sigma
        col = f"EWMAC_{fast}_{slow}_{vol_length}"
        actual = out[col]
        assert (expected.isna() == actual.isna()).all()
        m = expected.notna()
        assert np.nanmax(np.abs(expected[m].values - actual[m].values)) < 1e-9


def test_default_vol_length_is_35():
    close = _walk(300)
    assert "EWMAC_64_256_35" in ewmac(close).columns
    assert "EWMAC_64_256_20" in ewmac(close, vol_length=20).columns


# -------------------------------------------------------------- causality

_REAL = importlib.import_module("pandas_ta.momentum.ewmac")


def _load_mutant(old, new, tag):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType(f"_ewmac_mutant_{tag}")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


MUTANTS = {
    "sigma": (
        "sigma = close.diff().ewm(span=vol_length, adjust=False).std()",
        "sigma = close.diff().shift(-1).ewm(span=vol_length, adjust=False).std()",
    ),
    "fastma": (
        "col = (fastma - slowma) / sigma",
        "col = (fastma.shift(-1) - slowma) / sigma",
    ),
}

OFFSETS = range(40, 1100, 35)  # 31 offsets


def _leaks(fn):
    """Count offsets `j` at which rewriting bars >= j moves any bar < j."""
    close = _walk()
    base = fn(close)
    other = _walk(seed=99)
    hits = 0
    for j in OFFSETS:
        pert = close.copy()
        pert.iloc[j:] = other.iloc[j:].values
        out = fn(pert)
        a, b = base.iloc[:j], out.iloc[:j]
        if not (a.isna().to_numpy() == b.isna().to_numpy()).all():
            hits += 1
            continue
        m = a.notna().to_numpy()
        if (a.to_numpy()[m] != b.to_numpy()[m]).any():
            hits += 1
    return hits


def test_real_module_never_reads_the_future():
    assert _leaks(ewmac) == 0


@pytest.mark.parametrize("tag", sorted(MUTANTS))
def test_mutant_is_caught(tag):
    mod = _load_mutant(*MUTANTS[tag], tag)
    close = _walk()
    assert not mod.ewmac(close).equals(ewmac(close))  # live
    assert _leaks(mod.ewmac) == len(OFFSETS)           # caught, 31 of 31


# ------------------------------------------------------------ scale-free


@pytest.mark.parametrize("k", [8.0, 64.0])
def test_power_of_two_scale_is_bit_identical(k):
    close = _walk(tick=0.05)
    base, scaled = ewmac(close), ewmac(close * k)
    assert (base.isna().to_numpy() == scaled.isna().to_numpy()).all()
    m = base.notna().to_numpy()
    assert (base.to_numpy()[m] == scaled.to_numpy()[m]).all()


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_other_scales_within_tolerance(k):
    close = _walk(tick=0.05)
    base, scaled = ewmac(close), ewmac(close * k)
    assert (base.isna().to_numpy() == scaled.isna().to_numpy()).all()
    assert np.nanmax(np.abs(base.to_numpy() - scaled.to_numpy())) < 1e-9


def test_every_column_fires_and_is_not_constant():
    # Measured on the tick-rounded probe walk (docs/measure_ewmac.py):
    # 1,198 of 1,200 bars non-NaN per column, all 1,198 nonzero.
    out = ewmac(_walk(tick=0.05))
    assert list(out.columns) == [f"EWMAC_{f}_{s}_35" for f, s in PAIRS]
    for col in out.columns:
        fires = out[col].dropna()
        assert len(fires) == 1198
        assert 0 < int((fires != 0).sum()) < len(out)
        assert out[col].nunique() > 100


# ---------------------------------------------------------------- wiring


def test_name_registration_and_accessor():
    close = _walk(400)
    df = DataFrame({"open": close, "high": close, "low": close,
                    "close": close, "volume": 1.0})
    assert "ewmac" in ta.Category["momentum"]
    out = df.ta.ewmac()
    expected_cols = [f"EWMAC_{f}_{s}_35" for f, s in PAIRS]
    assert list(out.columns) == expected_cols
    pd.testing.assert_frame_equal(out, ewmac(close))
    assert list(df.ta.ewmac(vol_length=20).columns) == \
        [f"EWMAC_{f}_{s}_20" for f, s in PAIRS]
