# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.trend.rd_adx8_med20` -- rolling 20-bar median of
ADX(8) (issue #178, Reddit tier 4: rd:quant:1gc3o70). Measurements are in
docs/RdAdx8Med20Measured.md.

What these pin, in order of how much it would hurt to lose:

* CORRECTNESS against the issue's own formula: an independent recompute
  that calls this fork's own `adx()` (already ported, already tested) for
  ADX8 and then re-derives the rolling median with plain `numpy.median`
  over NumPy slices -- never calling the module's own `.rolling().median()`
  path for the outer statistic.
* CAUSALITY by future-perturbation (rewrite high/low/close from bar j
  onward, demand bars [0:j] bit-identical) and a look-ahead mutant
  (`importlib` source read, the median's input shifted one bar toward the
  future, `exec`'d in memory -- never a hand-written copy), proved live
  and then caught.
* SCALE-FREE: `ADX_8` and `RD_ADX8_MED20` both bit-identical under x8/x64
  scaling of high/low/close together; within tolerance under x10/x3.7;
  `0 < fires < n` plus non-constant.
* Wiring: `Category`, the accessor, and the column name
  `RD_ADX8_MED20_8_20`.
"""
import importlib
import types

import numpy as np
import pandas as pd
import pytest
from pandas import DataFrame, Series

from .context import pandas_ta as ta
from pandas_ta.trend.rd_adx8_med20 import rd_adx8_med20
from pandas_ta.trend.adx import adx


def _walk(n=900, seed=11, sigma=0.02):
    rng = np.random.default_rng(seed)
    close = 100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n)))
    spread = close * rng.uniform(0.001, 0.02, n)
    high = close + spread * rng.uniform(0.2, 1.0, n)
    low = close - spread * rng.uniform(0.2, 1.0, n)
    return Series(high), Series(low), Series(close)


# ------------------------------------------------------------ correctness


def test_matches_an_independent_median_of_adx8():
    """Re-derives the outer statistic independently: calls the fork's own
    (already-tested) `adx()` for ADX8, then a plain `numpy.median` over
    NumPy slices for the rolling median -- never the module's own
    `.rolling().median()` call."""
    high, low, close = _walk(900)
    length = 20
    adx8 = adx(high=high, low=low, close=close, length=8)["ADX_8"].to_numpy()

    ref = np.full(len(adx8), np.nan)
    for t in range(length - 1, len(adx8)):
        window = adx8[t - length + 1:t + 1]
        if np.isnan(window).any():
            continue
        ref[t] = np.median(window)

    out = rd_adx8_med20(high, low, close, adx_length=8, length=length)
    assert (np.isnan(ref) == out.isna().values).all()
    m = ~np.isnan(ref)
    assert np.nanmax(np.abs(out.values[m] - ref[m])) < 1e-9


def test_length_one_is_the_identity():
    """The median of a 1-bar window is that single value -- pins that
    `length=1` makes `RD_ADX8_MED20` a pass-through of ADX8 itself,
    independent of what ADX8's own values happen to be."""
    high, low, close = _walk(300)
    out = rd_adx8_med20(high, low, close, adx_length=8, length=1)
    adx8 = adx(high=high, low=low, close=close, length=8)["ADX_8"]
    m = out.notna() & adx8.notna()
    assert m.sum() > 0
    assert (out[m].to_numpy() == adx8[m].to_numpy()).all()


def test_bounded_on_zero_to_hundred():
    high, low, close = _walk(900)
    out = rd_adx8_med20(high, low, close).dropna()
    assert len(out) > 0
    assert (out >= 0.0).all()
    assert (out <= 100.0 + 1e-9).all()


# -------------------------------------------------------------- causality

_REAL = importlib.import_module("pandas_ta.trend.rd_adx8_med20")


def _load_mutant():
    old = "result = adx8.rolling(length, min_periods=min_periods).median()"
    new = "result = adx8.shift(-1).rolling(length, min_periods=min_periods).median()"
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_rd_adx8_med20_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


OFFSETS = range(400, 850, 50)  # past the adx_length + length warm-up


def _leaks(fn):
    high, low, close = _walk()
    base = fn(high, low, close)
    hits = 0
    for j in OFFSETS:
        ph, pl, pc = high.copy(), low.copy(), close.copy()
        ph.iloc[j:] = high.iloc[j:].to_numpy() * 1000.0
        pl.iloc[j:] = low.iloc[j:].to_numpy() * 1000.0
        pc.iloc[j:] = close.iloc[j:].to_numpy() * 1000.0
        out = fn(ph, pl, pc)
        a, b = base.iloc[:j], out.iloc[:j]
        if not (a.isna() == b.isna()).all():
            hits += 1
            continue
        m = a.notna()
        if (a[m] != b[m]).any():
            hits += 1
    return hits


def test_real_module_never_reads_the_future():
    assert _leaks(rd_adx8_med20) == 0


def test_mutant_is_caught():
    """A median is robust to a single extreme input -- scaling the whole
    tail from j onward by 1000x only changes ONE window position's rank
    order enough to move the median (position j-1, the sole one reading
    into the perturbed region under the mutant's one-bar shift); at a
    minority of the swept offsets the injected spike happens to land on
    the same side of the window's existing median and the mutant's output
    does not move. Measured: 5 of 9 offsets at this seed -- a majority,
    not all; pinned as such rather than claiming a perfect catch."""
    mod = _load_mutant()
    high, low, close = _walk()
    assert not mod.rd_adx8_med20(high, low, close).equals(
        rd_adx8_med20(high, low, close))  # live
    hits = _leaks(mod.rd_adx8_med20)
    assert hits > len(OFFSETS) // 2, f"mutant caught at only {hits} of {len(OFFSETS)} offsets"


# ------------------------------------------------------------ scale-free


@pytest.mark.parametrize("k", [8.0, 64.0])
def test_scale_is_bit_identical(k):
    high, low, close = _walk()
    base = rd_adx8_med20(high, low, close)
    scaled = rd_adx8_med20(high * k, low * k, close * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_scale_within_tolerance(k):
    high, low, close = _walk()
    base = rd_adx8_med20(high, low, close)
    scaled = rd_adx8_med20(high * k, low * k, close * k)
    assert (base.isna() == scaled.isna()).all()
    assert (base - scaled).abs().max() < 1e-9


def test_column_is_not_constant():
    high, low, close = _walk(900)
    out = rd_adx8_med20(high, low, close).dropna()
    assert 0 < len(out) < 900
    assert out.nunique() > 20


# ---------------------------------------------------------------- edge cases


def test_short_input_returns_none():
    high = Series([110.0] * 5)
    low = Series([100.0] * 5)
    close = Series([105.0] * 5)
    assert rd_adx8_med20(high, low, close) is None


def test_min_bars_boundary():
    """`min_bars` must reflect ADX's OWN warm-up (`2 * adx_length`, the
    convention `adxr.py` already uses for the same quantity), not
    `adx_length` alone. An earlier draft used `adx_length + length` = 28
    for the default (8, 20): `verify_series` only rejects input shorter
    than `min_bars`, so a 28..35-bar input would have passed the guard and
    then come back out as an all-NaN Series -- silently wrong rather than
    `None`. (Measured: `ADX_8`'s own first non-NaN value sits at index 15
    of a longer series, so the tightest possible bound would be 35 bars,
    one less than this port's `min_bars = 36` -- the corrected threshold
    matches `adxr.py`'s own house convention exactly rather than chasing
    the tight bound, at the cost of rejecting that one edge length as
    `None` instead of returning its single legitimate value; the same
    kind of one-bar conservative slack `adxr.py` itself carries.) This
    pins the corrected threshold, `min_bars = 36` (`2 * 8 + 20`)."""
    high, low, close = _walk(40)
    for n in (27, 35):
        out = rd_adx8_med20(high.iloc[:n], low.iloc[:n], close.iloc[:n])
        assert out is None, f"n={n} should be rejected by verify_series, not returned as all-NaN"
    out = rd_adx8_med20(high.iloc[:36], low.iloc[:36], close.iloc[:36])
    assert out is not None
    assert out.notna().any(), "n=36 (the corrected min_bars) must produce at least one finite value"


def test_offset():
    high, low, close = _walk(900)
    out0 = rd_adx8_med20(high, low, close, adx_length=8, length=20)
    out1 = rd_adx8_med20(high, low, close, adx_length=8, length=20, offset=1)
    aligned = out0.iloc[:-1]
    shifted = out1.iloc[1:]
    assert pd.isna(out1.iloc[0])
    assert (aligned.reset_index(drop=True).dropna()
            == shifted.reset_index(drop=True).dropna()).all()


# ---------------------------------------------------------------- wiring


def test_name_registration_and_accessor():
    high, low, close = _walk(900)
    df = DataFrame({"open": low, "high": high, "low": low,
                    "close": close, "volume": 1.0})
    assert "rd_adx8_med20" in ta.Category["trend"]
    out = df.ta.rd_adx8_med20()
    assert out.name == "RD_ADX8_MED20_8_20"
    pd.testing.assert_series_equal(out, rd_adx8_med20(high, low, close))
    assert df.ta.rd_adx8_med20(adx_length=5, length=10).name == "RD_ADX8_MED20_5_10"
