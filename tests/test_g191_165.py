# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.statistics.g191_165` -- Guotai Junan's (2017,
"GTJA191") alpha `#165`, per issue #55: `MAX(SUMAC(C-MEAN(C,48))) -
MIN(SUMAC(C-MEAN(C,48))) / STD(C,48)`, read per the issue's own
parenthetical as `(MAX-MIN)/STD`, the classical rescaled-range (R/S)
statistic over a trailing 48-bar window. Gate A derivation (including the
two disclosed interpretation choices the issue's own ambiguous formula text
requires) is in the module docstring and `docs/G191165Measured.md`. Gate E
is pending (CLAUDE.md, "Owed, not failed").

What these pin, in order of how much it would hurt to lose:

* CAUSALITY by future-perturbation: rewrite every close bar from `j`
  onward (another synthetic series), demand bars `[0:j]` bit-identical with
  matching NaN masks, over offsets past the 48-bar warm-up. Two mutants
  (`importlib` source read, `exec`'d in memory), each shown live (differs
  from the real module) then caught at every offset: shifting the whole
  write index `length=48` bars into the future, and writing each window's
  result to its CENTER bar instead of its last bar -- the same look-ahead
  bug class CLAUDE.md documents for `bos`'s `rolling(..., center=True)`,
  expressed here as a write-index shift because this module computes its
  own windows with `sliding_window_view` rather than pandas' `.rolling()`
  (`python docs/measure_g191_165.py`).
* CORRECTNESS: a 7-bar hand-derived example at `length=4`, checked against
  an independent per-bar PYTHON-LOOP computation (not the module's own
  vectorised `sliding_window_view` code) -- the exact values printed by
  `docs/measure_g191_165.py`. A second spot check at the shipped default
  (`length=48`) against the same independent loop, on a 900-bar frame.
* SCALE-FREE: every term in the ratio -- the window mean, the deviations,
  the cumulative sum, its range, and the window's own std -- scales
  EXACTLY linearly with a positive rescale of `close`, so the `k` cancels
  algebraically in the final ratio for ANY `k > 0`. Bit-identical under
  close x8/x64 (power-of-two, exact in IEEE754), within float64 tolerance
  under x10/x3.7. Matching NaN masks, plus `0 < fires < n` and
  `nunique > 1`.
* Wiring: `Category`, the accessor, the column name `G191_165_48`.
"""
import importlib
import types

import numpy as np
import pandas as pd
import pytest
from pandas import Series

from .context import pandas_ta as ta
from pandas_ta.statistics.g191_165 import g191_165


def _cv(n=1500, seed=11, sigma=0.015):
    rng = np.random.default_rng(seed)
    close = 100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n)))
    idx = pd.RangeIndex(n)
    return Series(close, index=idx)


# ------------------------------------------------------------ correctness


def test_hand_derived_seven_bars():
    """length=4: window mean, deviations, window-local cumsum, range,
    STDEV(ddof=1). Checked to float precision against an independent
    per-bar python loop below (`python docs/measure_g191_165.py` prints the
    exact values)."""
    close = Series([1.0, 2.0, 3.0, 4.0, 3.0, 2.0, 1.0])

    out = g191_165(close, length=4)

    assert out.iloc[:3].isna().all()
    expected = {
        3: 1.5491933384829668,
        4: 1.224744871391589,
        5: 1.224744871391589,
        6: 1.5491933384829668,
    }
    for t, val in expected.items():
        assert out.iloc[t] == pytest.approx(val, abs=1e-9), f"bar {t}"


def _independent_rs(x, length):
    """Plain-python per-bar loop, NOT the module's vectorised
    sliding-window code."""
    n = len(x)
    out = [float("nan")] * n
    for t in range(length - 1, n):
        w = x[t - length + 1:t + 1]
        m = sum(w) / length
        dev = [v - m for v in w]
        z, running = [], 0.0
        for d in dev:
            running += d
            z.append(running)
        rng = max(z) - min(z)
        var = sum(d * d for d in dev) / (length - 1)
        s = var ** 0.5
        out[t] = float("nan") if s == 0 else rng / s
    return out


def test_matches_an_independent_loop_at_defaults():
    """Spot-checks 3 bars of the shipped default (length=48) against an
    independent per-bar python loop over explicit window slices, not the
    module's own `sliding_window_view` vectorisation."""
    close = _cv(900, seed=5)
    out = g191_165(close)
    indep = _independent_rs(list(close), 48)

    for t in (300, 600, 899):
        assert out.iloc[t] == pytest.approx(indep[t], rel=1e-9)


def test_insufficient_history_returns_none():
    close = _cv(47)  # default length=48 needs at least 48 bars
    assert g191_165(close) is None


def test_exact_min_length_fires_at_the_warmup_boundary():
    close = _cv(48)  # exactly length=48 bars
    out = g191_165(close)
    assert out is not None
    assert out.iloc[:47].isna().all()
    assert pd.notna(out.iloc[47])


def test_default_name():
    close = _cv()
    out = g191_165(close)
    assert out.name == "G191_165_48"


def test_distinct_lengths_produce_distinct_names_and_values():
    close = _cv(300)
    out1 = g191_165(close, length=10)
    out2 = g191_165(close, length=20)
    assert out1.name != out2.name
    assert out1.name == "G191_165_10"
    assert out2.name == "G191_165_20"
    m = out1.notna() & out2.notna()
    assert (out1[m] != out2[m]).any()


# -------------------------------------------------------------- causality


_REAL = importlib.import_module("pandas_ta.statistics.g191_165")


def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_g191_165_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


WRITE_SHIFT_MUTANT = (
    "result = pd.Series(out, index=close.index)",
    "result = pd.Series(out, index=close.index).shift(-length)",  # a length-bar look-ahead
)
CENTER_WRITE_MUTANT = (
    "out[length - 1:] = rs",
    "out[(length - 1) // 2:(length - 1) // 2 + len(rs)] = rs",  # the `bos` look-ahead bug class
)

OFFSETS = range(150, 1500, 40)  # past the 48-bar warm-up


def _leaks(fn):
    close = _cv(1500)
    other_c = _cv(1500, seed=97)
    base = fn(close)
    hits = 0
    for j in OFFSETS:
        pc = close.copy()
        pc.iloc[j:] = other_c.iloc[j:].values
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
    assert _leaks(g191_165) == 0


def test_write_shift_mutant_is_caught():
    mod = _load_mutant(*WRITE_SHIFT_MUTANT)
    close = _cv(1500)
    assert not mod.g191_165(close).equals(g191_165(close))  # live
    assert _leaks(mod.g191_165) == len(list(OFFSETS))  # caught, every offset


def test_center_write_mutant_is_caught():
    mod = _load_mutant(*CENTER_WRITE_MUTANT)
    close = _cv(1500)
    assert not mod.g191_165(close).equals(g191_165(close))  # live
    assert _leaks(mod.g191_165) == len(list(OFFSETS))  # caught, every offset


# ------------------------------------------------------------ scale-free


@pytest.mark.parametrize("k", [8.0, 64.0])
def test_power_of_two_price_scale_is_bit_identical(k):
    close = _cv()
    base = g191_165(close)
    scaled = g191_165(close * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_other_price_scales_within_tolerance(k):
    close = _cv()
    base = g191_165(close)
    scaled = g191_165(close * k)
    assert (base.isna() == scaled.isna()).all()
    assert (base - scaled).abs().max() < 1e-9


def test_fires_and_is_not_constant():
    close = _cv()
    out = g191_165(close)
    fires = int(out.notna().sum())
    assert 0 < fires < len(out)
    assert out.dropna().nunique() > 1


# ---------------------------------------------------------------- wiring


def test_name_registration_and_accessor():
    close = _cv(400)
    df = pd.DataFrame({"open": close, "high": close, "low": close, "close": close,
                        "volume": close})
    assert "g191_165" in ta.Category["statistics"]
    out = df.ta.g191_165()
    assert out.name == "G191_165_48"
    pd.testing.assert_series_equal(out, g191_165(close))
    renamed = df.ta.g191_165(length=10)
    assert renamed.name == "G191_165_10"
