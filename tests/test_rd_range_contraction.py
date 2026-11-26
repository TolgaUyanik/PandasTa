# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.volatility.rd_range_contraction` -- the ratio of a
short over a long moving average of the n-bar high-low spread (issue #176,
RD-RANGE-CONTRACTION; Reddit, tier 4, untested by the poster). Measurements
are in docs/RdRangeContractionMeasured.md.

What these pin, in order of how much it would hurt to lose:

* CORRECTNESS against an independent per-window loop built straight from the
  issue's own formula (`sliding_window_view` + plain `np.max`/`np.min`/mean,
  not pandas `.rolling`), plus a hand-derived fixture whose ratio is known
  before the module ever ran.
* CAUSALITY by future-splice: bars before a perturbation point J stay
  bit-identical whether or not the frame's tail is an unrelated series, at
  every swept J, and a mutant (`.shift(-1)` appended to the final ratio,
  reading one bar into the future) is proved live and caught at every J.
* SCALE-FREE: `spread = HHV(high,n) - LLV(low,n)` scales exactly with an
  exactly-representable price rescale (max/min pick an existing, exactly
  k-scaled element), and both the short and long MAs of `spread` scale by the
  same exact factor, so their ratio is bit-identical under x8/x64 and within
  a tight tolerance under the non-power-of-two x10/x3.7 -- the same
  cancellation `massi` relies on.
* Reachability (a non-constant output on a random synthetic frame, bounded
  away from a degenerate 0/0) and the wiring (`Category`, the accessor,
  warm-up, column name).
"""
import importlib
import types

import numpy as np
import pandas as pd
import pytest
from numpy.lib.stride_tricks import sliding_window_view
from pandas import DataFrame, Series

from .context import pandas_ta as ta

_REAL = importlib.import_module("pandas_ta.volatility.rd_range_contraction")
rd_range_contraction = _REAL.rd_range_contraction


# ---------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------
def _walk(n=1200, seed=11, start=100.0, sigma=0.012):
    rng = np.random.default_rng(seed)
    c = start * np.exp(np.cumsum(rng.normal(0.0, sigma, n)))
    spread = c * np.abs(rng.normal(0.0, 0.006, n))
    h = c + spread
    l = c - spread
    return Series(h), Series(l)


# ---------------------------------------------------------------------
# Gate A -- correctness
# ---------------------------------------------------------------------
def _oracle(h, l, n, short, long):
    """Independent per-window loop: plain numpy max/min/mean over sliding
    windows, built straight from the issue's own formula, not from the
    module's pandas `.rolling` calls."""
    hv, lv = h.to_numpy(dtype=float), l.to_numpy(dtype=float)
    nlen = len(hv)
    spread = np.full(nlen, np.nan)
    hw, lw = sliding_window_view(hv, n), sliding_window_view(lv, n)
    spread[n - 1:] = hw.max(axis=1) - lw.min(axis=1)
    out = np.full(nlen, np.nan)
    start = n + long - 2
    for end in range(start, nlen):
        s_win = spread[end - short + 1: end + 1]
        l_win = spread[end - long + 1: end + 1]
        denom = l_win.mean()
        out[end] = s_win.mean() / denom if denom != 0 else np.nan
    return out


def test_matches_an_independent_loop():
    h, l = _walk(n=400, seed=7)
    out = rd_range_contraction(h, l, n=5, short=10, long=50)
    ref = _oracle(h, l, 5, 10, 50)
    assert (np.isnan(ref) == out.isna().values).all()
    m = ~np.isnan(ref)
    np.testing.assert_allclose(out.values[m], ref[m], rtol=1e-12, atol=1e-12)


def test_hand_derived_value():
    """Constant spread before and after a step: with n=2, short=2, long=4,
    HHV-LLV of a flat-then-doubled high/low series is a known constant per
    regime, so the short/long ratio at the step is exactly computable by
    hand before the module ever ran."""
    # bars 0..4: high=11, low=9 (spread 2); bars 5..7: high=21, low=9 (first
    # widening bar has a 12-wide 2-bar spread, then steady spread 12)
    high = Series([11.0] * 5 + [21.0] * 3)
    low = Series([9.0] * 5 + [9.0] * 3)
    out = rd_range_contraction(high, low, n=2, short=2, long=4)
    # bar 7 (0-indexed): spread series = [nan,2,2,2,2,12,12,12]
    # short MA(2) at 7 = mean(12,12)=12; long MA(4) at 7 = mean(2,12,12,12)=9.5
    assert out.iloc[7] == pytest.approx(12.0 / 9.5, abs=1e-9)


def test_short_and_long_are_swapped_if_given_backwards():
    h, l = _walk(n=200, seed=3)
    a = rd_range_contraction(h, l, n=5, short=10, long=50)
    b = rd_range_contraction(h, l, n=5, short=50, long=10)
    pd.testing.assert_series_equal(a, b, check_names=False)
    assert b.name == "RD_RANGE_CONTRACTION_5_10_50"


def test_zero_long_average_reads_nan_not_inf():
    # a perfectly flat high/low gives a zero spread everywhere, so the long
    # average is exactly 0 and the ratio must be NaN, not +-inf
    high = Series([10.0] * 60)
    low = Series([10.0] * 60)
    out = rd_range_contraction(high, low, n=5, short=10, long=50)
    assert out.isna().all()


def test_short_input_returns_none():
    h, l = _walk(n=20, seed=1)
    assert rd_range_contraction(h, l) is None


# ---------------------------------------------------------------------
# Gate B -- causality
# ---------------------------------------------------------------------
def _load_mutant():
    old = "result = (short_ma / long_ma).replace([np.inf, -np.inf], np.nan)"
    new = "result = (short_ma / long_ma).shift(-1).replace([np.inf, -np.inf], np.nan)"
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_rd_range_contraction_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


OFFSETS = range(100, 1100, 40)  # 25 offsets, all past the 58-bar default warm-up


def _leaks(fn, base_h, base_l, other_h, other_l):
    base = fn(base_h, base_l)
    hits = 0
    for j in OFFSETS:
        sh, sl = base_h.copy(), base_l.copy()
        sh.iloc[j:] = other_h.iloc[j:].to_numpy()
        sl.iloc[j:] = other_l.iloc[j:].to_numpy()
        out = fn(sh, sl)
        a, b = base.iloc[:j], out.iloc[:j]
        if not (a.isna() == b.isna()).all():
            hits += 1
            continue
        m = a.notna()
        if (a[m] != b[m]).any():
            hits += 1
    return hits


def test_real_module_never_reads_the_future():
    ah, al = _walk(1200, seed=1)
    bh, bl = _walk(1200, seed=2)
    assert _leaks(rd_range_contraction, ah, al, bh, bl) == 0


def test_lookahead_mutant_is_caught():
    mod = _load_mutant()
    ah, al = _walk(1200, seed=1)
    bh, bl = _walk(1200, seed=2)
    mut = lambda h, l: mod.rd_range_contraction(h, l)  # noqa: E731
    real_out = rd_range_contraction(ah, al)
    mut_out = mut(ah, al)
    assert not mut_out.equals(real_out)  # live

    hits = _leaks(mut, ah, al, bh, bl)
    assert hits == len(OFFSETS), f"mutant caught at only {hits} of {len(OFFSETS)} J"


# ---------------------------------------------------------------------
# Gate D -- scale-free
# ---------------------------------------------------------------------
@pytest.mark.parametrize("k", [8.0, 64.0])
def test_price_scale_is_bit_identical(k):
    """HHV/LLV of an exactly-k-scaled window pick exactly-k-scaled elements,
    so `spread' = k*spread` with no rounding for a power-of-two `k`; the
    short and long MAs of `spread` then both scale by that same exact
    factor, and IEEE-754 division of two operands scaled by the same exact
    `k` returns a bit-identical quotient -- measured
    (docs/measure_rd_range_contraction_cpu.py): max absolute difference 0.0
    on every co-finite cell, for both x8 and x64."""
    h, l = _walk(seed=4)
    base = rd_range_contraction(h, l)
    scaled = rd_range_contraction(h * k, l * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m].to_numpy() == scaled[m].to_numpy()).all()


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_scale_stays_within_a_tiny_tolerance(k):
    """At a non-power-of-two rescale the max/min and the division are no
    longer exact bit-for-bit, so this stays a tiny-tolerance claim rather
    than bit-identical -- measured (docs/measure_rd_range_contraction_cpu.py):
    max absolute difference far below 1e-9 for both x10 and x3.7, bounded
    here at a generous tolerance since the CPU's dispatched float kernels,
    not this module's logic, decide the last bit."""
    h, l = _walk(seed=4)
    base = rd_range_contraction(h, l)
    scaled = rd_range_contraction(h * k, l * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    np.testing.assert_allclose(base[m].to_numpy(), scaled[m].to_numpy(), rtol=1e-9, atol=1e-9)


# ---------------------------------------------------------------------
# Gate C -- reachability
# ---------------------------------------------------------------------
def test_fires_and_is_not_constant():
    h, l = _walk(seed=4)
    out = rd_range_contraction(h, l)
    fired = out.dropna()
    assert 0 < len(fired) < len(out)
    assert fired.nunique() > 1
    assert np.isfinite(fired.to_numpy()).all()
    assert (fired > 0).all()  # a ratio of two positive averages (spread >= 0)


# ---------------------------------------------------------------------
# wiring
# ---------------------------------------------------------------------
def test_default_params_in_name():
    h, l = _walk(seed=5)
    out = rd_range_contraction(h, l)
    assert out.name == "RD_RANGE_CONTRACTION_5_10_50"


def test_custom_params_in_name():
    h, l = _walk(seed=5)
    out = rd_range_contraction(h, l, n=3, short=5, long=20)
    assert out.name == "RD_RANGE_CONTRACTION_3_5_20"


def test_warmup_is_n_plus_long_minus_2_bars():
    h, l = _walk(n=200, seed=2)
    out = rd_range_contraction(h, l, n=5, short=10, long=50)
    assert out.iloc[:53].isna().all()
    assert out.iloc[53:].notna().all()


def test_offset_shifts_the_series():
    h, l = _walk(n=200, seed=6)
    base = rd_range_contraction(h, l)
    shifted = rd_range_contraction(h, l, offset=1)
    pd.testing.assert_series_equal(shifted, base.shift(1), check_names=False)


def test_fillna_fills_the_warmup_nans():
    h, l = _walk(n=200, seed=6)
    out = rd_range_contraction(h, l, fillna=0)
    assert not out.isna().any()
    assert (out.iloc[:53] == 0).all()


def test_fill_method_bfill_and_bad_value():
    h, l = _walk(n=200, seed=6)
    out = rd_range_contraction(h, l, fill_method="bfill")
    assert not out.isna().any()
    with pytest.raises(ValueError):
        rd_range_contraction(h, l, fill_method="nope")


def test_column_name_and_category():
    h, l = _walk(n=60, seed=1)
    out = rd_range_contraction(h, l, n=2, short=3, long=5)
    assert out.name == "RD_RANGE_CONTRACTION_2_3_5"
    assert out.category == "volatility"


def test_registered_in_category():
    assert "rd_range_contraction" in ta.Category["volatility"]


def test_accessor_matches_module_level():
    h, l = _walk(n=200, seed=9)
    via_module = rd_range_contraction(h, l)
    df = DataFrame({"high": h, "low": l})
    via_accessor = df.ta.rd_range_contraction()
    pd.testing.assert_series_equal(via_module, via_accessor, check_exact=True)
    assert df.ta.rd_range_contraction(n=3, short=5, long=20).name == "RD_RANGE_CONTRACTION_3_5_20"
