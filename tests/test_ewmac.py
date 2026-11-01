# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.momentum.ewmac` -- Carver's volatility-normalised EMA
crossover (issue #29): `(EMA_fast(close) - EMA_slow(close)) / sigma`, one
column per Carver speed pair (2:8, 4:16, 8:32, 16:64, 32:128, 64:256), with
`sigma` ONE shared EWMA standard deviation of daily price changes (not
re-derived per pair). Raw ratio only -- no forecast scalar, no cap, per the
issue's own Gate A note. Measurements and the open Gate E are in
`docs/EwmacMeasured.md`.

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
  1e-9 under x10 and x3.7 with matching NaN masks, and `0 < fires < n` per
  column (1,198 of 1,200 on the probe walk; the other 2 are the warm-up).
* CORRECTNESS: a hand-computed 3-bar EMA recursion for the 2:8 pair, and a
  400-bar random walk reassembled from the literal formula
  (`close.ewm(span=L, adjust=False).mean()`, `close.diff().ewm(span=35,
  adjust=False).std()`) independently of the module's own code path.
* Wiring: `Category`, the accessor, and all six column names.
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
    # close = [10, 11, 13, ...300 more bars]; fast=2 (alpha=2/3), slow=8
    # (alpha=2/9); no SMA seed, e0 = close[0], e_t = (1-alpha)*e_{t-1} +
    # alpha*close_t. Padded past `verify_series`'s 257-bar floor; causality
    # (proven separately below) guarantees bars >= 3 cannot move bar 2.
    close = Series([10.0, 11.0, 13.0] + [100.0] * 300)
    fast_e2 = (1 / 3) * ((1 / 3) * 10 + (2 / 3) * 11) + (2 / 3) * 13  # 12.2222...
    slow_e2 = (7 / 9) * ((7 / 9) * 10 + (2 / 9) * 11) + (2 / 9) * 13  # 10.8395...
    expected_numerator = fast_e2 - slow_e2

    out = ewmac(close)["EWMAC_2_8_35"]
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


def test_sigma_is_shared_not_per_pair():
    """The six columns must divide by the SAME sigma series, not six
    independently-derived ones (the Gate A decision in docs/EwmacMeasured.md)."""
    close = _walk(400)
    out = ewmac(close)
    sigma = close.diff().ewm(span=35, adjust=False).std()
    fast0, slow0 = PAIRS[0]
    fast1, slow1 = PAIRS[1]
    fastma0 = close.ewm(span=fast0, adjust=False).mean()
    slowma0 = close.ewm(span=slow0, adjust=False).mean()
    fastma1 = close.ewm(span=fast1, adjust=False).mean()
    slowma1 = close.ewm(span=slow1, adjust=False).mean()
    recovered0 = out["EWMAC_2_8_35"] * sigma
    recovered1 = out["EWMAC_4_16_35"] * sigma
    assert np.nanmax(np.abs((fastma0 - slowma0).values - recovered0.values)) < 1e-9
    assert np.nanmax(np.abs((fastma1 - slowma1).values - recovered1.values)) < 1e-9


def test_default_vol_length_is_35():
    close = _walk(300)
    assert "EWMAC_2_8_35" in ewmac(close).columns
    assert "EWMAC_2_8_20" in ewmac(close, vol_length=20).columns


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
