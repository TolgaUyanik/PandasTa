# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.volatility.rd_std_ratio_20_60` -- close's rolling
stdev over a rolling average of that same stdev series (issue #179,
RD-STD-RATIO-20-60; Reddit, tier 4, untested by the poster). Measurements
are in docs/RdStdRatio2060Measured.md.

What these pin, in order of how much it would hurt to lose:

* CORRECTNESS against an independent per-window loop built straight from
  the issue's own formula (`sliding_window_view` + plain `np.std(ddof=1)`/
  mean, not pandas `.rolling`), plus a hand-derived fixture whose ratio is
  known before the module ever ran.
* CAUSALITY by future-splice: bars before a perturbation point J stay
  bit-identical whether or not the frame's tail is an unrelated series, at
  every swept J, and a mutant (`.shift(-1)` appended to the final ratio,
  reading one bar into the future) is proved live and caught at every J.
* SCALE-FREE: a rolling stdev scales exactly with an exactly-representable
  price rescale (sum-of-squared-deviations scales by k**2, sqrt of that
  scales by exactly k for a power-of-two k), and a rolling mean of that
  stdev series scales by the same exact factor, so their ratio is
  bit-identical under x8/x64 and within a tight tolerance under the
  non-power-of-two x10/x3.7 -- the same cancellation `rd_range_contraction`
  relies on.
* Reachability (a non-constant output on a random synthetic frame) and the
  wiring (`Category`, the accessor, warm-up, column name).
"""
import importlib
import types

import numpy as np
import pandas as pd
import pytest
from numpy.lib.stride_tricks import sliding_window_view
from pandas import DataFrame, Series

from .context import pandas_ta as ta

_REAL = importlib.import_module("pandas_ta.volatility.rd_std_ratio_20_60")
rd_std_ratio_20_60 = _REAL.rd_std_ratio_20_60


# ---------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------
def _walk(n=1200, seed=11, start=100.0, sigma=0.012):
    rng = np.random.default_rng(seed)
    c = start * np.exp(np.cumsum(rng.normal(0.0, sigma, n)))
    return Series(c)


# ---------------------------------------------------------------------
# Gate A -- correctness
# ---------------------------------------------------------------------
def _oracle(close, length, avg_length):
    """Independent per-window loop: plain numpy std(ddof=1)/mean over
    sliding windows, built straight from the issue's own formula, not from
    the module's pandas `.rolling` calls."""
    cv = close.to_numpy(dtype=float)
    n = len(cv)
    std = np.full(n, np.nan)
    windows = sliding_window_view(cv, length)
    std[length - 1:] = windows.std(axis=1, ddof=1)
    out = np.full(n, np.nan)
    start = length + avg_length - 2
    for end in range(start, n):
        window = std[end - avg_length + 1: end + 1]
        denom = window.mean()
        out[end] = std[end] / denom if denom != 0 else np.nan
    return out


def test_matches_an_independent_loop():
    c = _walk(n=400, seed=7)
    out = rd_std_ratio_20_60(c, length=20, avg_length=60)
    ref = _oracle(c, 20, 60)
    assert (np.isnan(ref) == out.isna().values).all()
    m = ~np.isnan(ref)
    assert m.sum() > 0
    np.testing.assert_allclose(out.values[m], ref[m], rtol=1e-9, atol=1e-9)


def test_hand_derived_value():
    """A flat-then-step close series: with length=2, avg_length=4, the
    2-bar stdev series is zero everywhere except the single step bar, so
    the ratio at that bar is exactly computable by hand before the module
    ever ran (the lone nonzero term divided by its own 4-bar average of
    itself-and-three-zeros is exactly 4.0)."""
    close = Series([10.0] * 5 + [20.0] * 3)
    out = rd_std_ratio_20_60(close, length=2, avg_length=4)
    # std series (2-bar, ddof=1): [nan, 0, 0, 0, 0, 10/sqrt(2), 0, 0]
    # at bar 5 (0-indexed): window [std2..std5] = [0, 0, 0, 10/sqrt(2)]
    # mean = (10/sqrt(2))/4; ratio = (10/sqrt(2)) / ((10/sqrt(2))/4) = 4.0
    assert out.iloc[5] == pytest.approx(4.0, abs=1e-9)


def test_zero_average_stdev_reads_nan_not_inf():
    # a perfectly flat close gives a zero stdev everywhere, so the average
    # stdev is exactly 0 and the ratio must be NaN, not +-inf
    close = Series([10.0] * 90)
    out = rd_std_ratio_20_60(close, length=20, avg_length=60)
    assert out.isna().all()


def test_short_input_returns_none():
    c = _walk(n=20, seed=1)
    assert rd_std_ratio_20_60(c) is None


# ---------------------------------------------------------------------
# Gate B -- causality
# ---------------------------------------------------------------------
def _load_mutant():
    old = "out = (std_series / avg_std).replace([np.inf, -np.inf], np.nan)"
    new = "out = (std_series / avg_std).shift(-1).replace([np.inf, -np.inf], np.nan)"
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_rd_std_ratio_20_60_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


OFFSETS = range(200, 1200, 40)  # all past the 78-bar default warm-up (79-bar minimum input)


def _leaks(fn, base_c, other_c):
    base = fn(base_c)
    hits = 0
    for j in OFFSETS:
        sc = base_c.copy()
        sc.iloc[j:] = other_c.iloc[j:].to_numpy()
        out = fn(sc)
        a, b = base.iloc[:j], out.iloc[:j]
        if not (a.isna() == b.isna()).all():
            hits += 1
            continue
        m = a.notna()
        if (a[m] != b[m]).any():
            hits += 1
    return hits


def test_real_module_never_reads_the_future():
    ac = _walk(1200, seed=1)
    bc = _walk(1200, seed=2)
    assert _leaks(rd_std_ratio_20_60, ac, bc) == 0


def test_lookahead_mutant_is_caught():
    mod = _load_mutant()
    ac = _walk(1200, seed=1)
    bc = _walk(1200, seed=2)
    mut = lambda c: mod.rd_std_ratio_20_60(c)  # noqa: E731
    real_out = rd_std_ratio_20_60(ac)
    mut_out = mut(ac)
    assert not mut_out.equals(real_out)  # live

    hits = _leaks(mut, ac, bc)
    assert hits == len(OFFSETS), f"mutant caught at only {hits} of {len(OFFSETS)} J"


# ---------------------------------------------------------------------
# Gate D -- scale-free
# ---------------------------------------------------------------------
@pytest.mark.parametrize("k", [8.0, 64.0])
def test_price_scale_is_bit_identical(k):
    """A rolling stdev of an exactly-k-scaled window scales by exactly k
    (sum of squared deviations scales by k**2, sqrt of that by exactly k
    for a power-of-two k); a rolling mean of that stdev series then scales
    by the same exact factor, and IEEE-754 division of two operands scaled
    by the same exact k returns a bit-identical quotient -- measured
    (docs/measure_rd_std_ratio_20_60_cpu.py): max absolute difference 0.0
    on every co-finite cell, for both x8 and x64."""
    c = _walk(seed=4)
    base = rd_std_ratio_20_60(c)
    scaled = rd_std_ratio_20_60(c * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m].to_numpy() == scaled[m].to_numpy()).all()


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_scale_stays_within_a_tiny_tolerance(k):
    """At a non-power-of-two rescale the stdev and the division are no
    longer exact bit-for-bit, so this stays a tiny-tolerance claim rather
    than bit-identical -- measured (docs/measure_rd_std_ratio_20_60_cpu.py):
    max absolute difference far below 1e-9 for both x10 and x3.7, bounded
    here at a generous tolerance since the CPU's dispatched float kernels,
    not this module's logic, decide the last bit."""
    c = _walk(seed=4)
    base = rd_std_ratio_20_60(c)
    scaled = rd_std_ratio_20_60(c * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    np.testing.assert_allclose(base[m].to_numpy(), scaled[m].to_numpy(), rtol=1e-9, atol=1e-9)


# ---------------------------------------------------------------------
# Gate C -- reachability
# ---------------------------------------------------------------------
def test_fires_and_is_not_constant():
    c = _walk(seed=4)
    out = rd_std_ratio_20_60(c)
    fired = out.dropna()
    assert 0 < len(fired) < len(out)
    assert fired.nunique() > 1
    assert np.isfinite(fired.to_numpy()).all()
    assert (fired >= 0).all()  # a ratio of two non-negative stdevs


# ---------------------------------------------------------------------
# wiring
# ---------------------------------------------------------------------
def test_default_params_in_name():
    c = _walk(seed=5)
    out = rd_std_ratio_20_60(c)
    assert out.name == "RD_STD_RATIO_20_60_20_60"


def test_custom_params_in_name():
    c = _walk(seed=5)
    out = rd_std_ratio_20_60(c, length=10, avg_length=30)
    assert out.name == "RD_STD_RATIO_20_60_10_30"


def test_warmup_is_length_plus_avg_length_minus_2_bars():
    c = _walk(n=200, seed=2)
    out = rd_std_ratio_20_60(c, length=20, avg_length=60)
    assert out.iloc[:78].isna().all()
    assert out.iloc[78:].notna().all()


def test_offset_shifts_the_series():
    c = _walk(n=200, seed=6)
    base = rd_std_ratio_20_60(c)
    shifted = rd_std_ratio_20_60(c, offset=1)
    pd.testing.assert_series_equal(shifted, base.shift(1), check_names=False)


def test_fillna_fills_the_warmup_nans():
    c = _walk(n=200, seed=6)
    out = rd_std_ratio_20_60(c, fillna=0)
    assert not out.isna().any()
    assert (out.iloc[:78] == 0).all()


def test_fill_method_bfill_and_bad_value():
    c = _walk(n=200, seed=6)
    out = rd_std_ratio_20_60(c, fill_method="bfill")
    assert not out.isna().any()
    with pytest.raises(ValueError):
        rd_std_ratio_20_60(c, fill_method="nope")


def test_column_name_and_category():
    c = _walk(n=100, seed=1)
    out = rd_std_ratio_20_60(c, length=5, avg_length=15)
    assert out.name == "RD_STD_RATIO_20_60_5_15"
    assert out.category == "volatility"


def test_registered_in_category():
    assert "rd_std_ratio_20_60" in ta.Category["volatility"]


def test_accessor_matches_module_level():
    c = _walk(n=200, seed=9)
    via_module = rd_std_ratio_20_60(c)
    df = DataFrame({"close": c})
    via_accessor = df.ta.rd_std_ratio_20_60()
    pd.testing.assert_series_equal(via_module, via_accessor, check_exact=True)
    assert df.ta.rd_std_ratio_20_60(length=10, avg_length=30).name == "RD_STD_RATIO_20_60_10_30"
