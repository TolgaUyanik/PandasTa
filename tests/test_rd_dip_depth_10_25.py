# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.momentum.rd_dip_depth_10_25` -- the gap between the
trailing 10-bar high and the close, in units of the trailing 25-bar average
high-low range (issue #181, RD-DIP-DEPTH-10-25; Reddit, tier 4, untested by
the poster). Measurements are in docs/RdDipDepth1025Measured.md.

What these pin, in order of how much it would hurt to lose:

* CORRECTNESS against an independent per-window loop built straight from the
  issue's own formula (`sliding_window_view` + plain `np.max`/mean, not
  pandas `.rolling`), plus a hand-derived fixture whose ratio is known
  before the module ever ran.
* CAUSALITY by future-splice: bars before a perturbation point J stay
  bit-identical whether or not the frame's tail is an unrelated series, at
  every swept J, and a mutant (`.shift(-1)` appended to the final ratio,
  reading one bar into the future) is proved live and caught at every J.
* SCALE-FREE: `HHV(high, length) - close` and
  `SMA(high, avg_length) - SMA(low, avg_length)` both scale exactly with an
  exactly-representable price rescale (max picks an existing, exactly
  k-scaled element; a rolling mean of k-scaled terms scales by the same
  exact factor), so their ratio is bit-identical under x8/x64 and within a
  tight tolerance under the non-power-of-two x10/x3.7 -- the same
  cancellation `rd_range_contraction` relies on.
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

_REAL = importlib.import_module("pandas_ta.momentum.rd_dip_depth_10_25")
rd_dip_depth_10_25 = _REAL.rd_dip_depth_10_25


# ---------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------
def _walk(n=1200, seed=11, start=100.0, sigma=0.012):
    rng = np.random.default_rng(seed)
    close = start * np.exp(np.cumsum(rng.normal(0.0, sigma, n)))
    spread = close * np.abs(rng.normal(0.0, 0.006, n))
    high = close + spread * rng.uniform(0.2, 1.0, n)
    low = close - spread * rng.uniform(0.2, 1.0, n)
    return Series(high), Series(low), Series(close)


# ---------------------------------------------------------------------
# Gate A -- correctness
# ---------------------------------------------------------------------
def _oracle(h, l, c, length, avg_length):
    """Independent per-window loop: plain numpy max/mean over sliding
    windows, built straight from the issue's own formula, not from the
    module's pandas `.rolling` calls."""
    hv, lv, cv = h.to_numpy(dtype=float), l.to_numpy(dtype=float), c.to_numpy(dtype=float)
    n = len(hv)
    hhv = np.full(n, np.nan)
    hw = sliding_window_view(hv, length)
    hhv[length - 1:] = hw.max(axis=1)
    avg_h = np.full(n, np.nan)
    avg_l = np.full(n, np.nan)
    hw2, lw2 = sliding_window_view(hv, avg_length), sliding_window_view(lv, avg_length)
    avg_h[avg_length - 1:] = hw2.mean(axis=1)
    avg_l[avg_length - 1:] = lw2.mean(axis=1)
    numerator = hhv - cv
    denominator = avg_h - avg_l
    out = np.full(n, np.nan)
    start = max(length, avg_length) - 1
    for t in range(start, n):
        out[t] = numerator[t] / denominator[t] if denominator[t] != 0 else np.nan
    return out


def test_matches_an_independent_loop():
    h, l, c = _walk(n=400, seed=7)
    out = rd_dip_depth_10_25(h, l, c, length=10, avg_length=25)
    ref = _oracle(h, l, c, 10, 25)
    assert (np.isnan(ref) == out.isna().values).all()
    m = ~np.isnan(ref)
    assert m.sum() > 0
    np.testing.assert_allclose(out.values[m], ref[m], rtol=1e-12, atol=1e-12)


def test_hand_derived_value():
    """A flat-then-step high with a constant low and a constant close: with
    length=2, avg_length=4, both the numerator and the denominator are
    exactly computable by hand before the module ever ran."""
    high = Series([10.0] * 3 + [20.0] * 5)
    low = Series([8.0] * 8)
    close = Series([9.0] * 8)
    out = rd_dip_depth_10_25(high, low, close, length=2, avg_length=4)
    # numerator[t] = HHV(high,2)[t] - 9; HHV(high,2) = [nan,10,10,20,20,20,20,20]
    # denominator[t] = mean(high,4)[t] - 8 (mean(low,4) is always 8)
    # bar 3 (0-indexed): HHV=20, numerator=11; mean(high,4)=mean(10,10,10,20)=12.5, denom=4.5
    assert out.iloc[3] == pytest.approx(11.0 / 4.5, abs=1e-9)
    # bar 6: HHV=20, numerator=11; mean(high,4)=mean(20,20,20,20)=20, denom=12
    assert out.iloc[6] == pytest.approx(11.0 / 12.0, abs=1e-9)
    assert out.iloc[6] == out.iloc[7]  # the window has stabilized


def test_zero_average_range_reads_nan_not_inf():
    # a perfectly flat high/low gives a zero average range everywhere, so
    # the denominator is exactly 0 and the ratio must be NaN, not +-inf
    high = Series([10.0] * 60)
    low = Series([10.0] * 60)
    close = Series([9.0] * 60)
    out = rd_dip_depth_10_25(high, low, close, length=10, avg_length=25)
    assert out.isna().all()


def test_short_input_returns_none():
    h, l, c = _walk(n=20, seed=1)
    assert rd_dip_depth_10_25(h, l, c) is None


# ---------------------------------------------------------------------
# Gate B -- causality
# ---------------------------------------------------------------------
def _load_mutant():
    old = "result = (numerator / denominator).replace([np.inf, -np.inf], np.nan)"
    new = "result = (numerator / denominator).shift(-1).replace([np.inf, -np.inf], np.nan)"
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_rd_dip_depth_10_25_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


OFFSETS = range(100, 1100, 40)  # 25 offsets, all past the 25-bar default warm-up


def _leaks(fn, base_h, base_l, base_c, other_h, other_l, other_c):
    base = fn(base_h, base_l, base_c)
    hits = 0
    for j in OFFSETS:
        sh, sl, sc = base_h.copy(), base_l.copy(), base_c.copy()
        sh.iloc[j:] = other_h.iloc[j:].to_numpy()
        sl.iloc[j:] = other_l.iloc[j:].to_numpy()
        sc.iloc[j:] = other_c.iloc[j:].to_numpy()
        out = fn(sh, sl, sc)
        a, b = base.iloc[:j], out.iloc[:j]
        if not (a.isna() == b.isna()).all():
            hits += 1
            continue
        m = a.notna()
        if (a[m] != b[m]).any():
            hits += 1
    return hits


def test_real_module_never_reads_the_future():
    ah, al, ac = _walk(1200, seed=1)
    bh, bl, bc = _walk(1200, seed=2)
    assert _leaks(rd_dip_depth_10_25, ah, al, ac, bh, bl, bc) == 0


def test_lookahead_mutant_is_caught():
    mod = _load_mutant()
    ah, al, ac = _walk(1200, seed=1)
    bh, bl, bc = _walk(1200, seed=2)
    mut = lambda h, l, c: mod.rd_dip_depth_10_25(h, l, c)  # noqa: E731
    real_out = rd_dip_depth_10_25(ah, al, ac)
    mut_out = mut(ah, al, ac)
    assert not mut_out.equals(real_out)  # live

    hits = _leaks(mut, ah, al, ac, bh, bl, bc)
    assert hits == len(OFFSETS), f"mutant caught at only {hits} of {len(OFFSETS)} J"


# ---------------------------------------------------------------------
# Gate D -- scale-free
# ---------------------------------------------------------------------
@pytest.mark.parametrize("k", [8.0, 64.0])
def test_price_scale_is_bit_identical(k):
    """HHV of an exactly-k-scaled window picks an exactly-k-scaled element,
    and a k-scaled close subtracts exactly, so `numerator' = k*numerator`
    with no rounding for a power-of-two `k`; the two rolling means in the
    denominator scale by that same exact factor, and IEEE-754 division of
    two operands scaled by the same exact `k` returns a bit-identical
    quotient -- measured (docs/measure_rd_dip_depth_10_25_cpu.py): max
    absolute difference 0.0 on every co-finite cell, for both x8 and x64."""
    h, l, c = _walk(seed=4)
    base = rd_dip_depth_10_25(h, l, c)
    scaled = rd_dip_depth_10_25(h * k, l * k, c * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m].to_numpy() == scaled[m].to_numpy()).all()


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_scale_stays_within_a_tiny_tolerance(k):
    """At a non-power-of-two rescale the max and the division are no longer
    exact bit-for-bit, so this stays a tiny-tolerance claim rather than
    bit-identical -- measured (docs/measure_rd_dip_depth_10_25_cpu.py): max
    absolute difference far below 1e-9 for both x10 and x3.7, bounded here
    at a generous tolerance since the CPU's dispatched float kernels, not
    this module's logic, decide the last bit."""
    h, l, c = _walk(seed=4)
    base = rd_dip_depth_10_25(h, l, c)
    scaled = rd_dip_depth_10_25(h * k, l * k, c * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    np.testing.assert_allclose(base[m].to_numpy(), scaled[m].to_numpy(), rtol=1e-9, atol=1e-9)


# ---------------------------------------------------------------------
# Gate C -- reachability
# ---------------------------------------------------------------------
def test_fires_and_is_not_constant():
    h, l, c = _walk(seed=4)
    out = rd_dip_depth_10_25(h, l, c)
    fired = out.dropna()
    assert 0 < len(fired) < len(out)
    assert fired.nunique() > 1
    assert np.isfinite(fired.to_numpy()).all()
    assert (fired >= 0).all()  # trailing high >= current close on valid OHLC


# ---------------------------------------------------------------------
# wiring
# ---------------------------------------------------------------------
def test_default_params_in_name():
    h, l, c = _walk(seed=5)
    out = rd_dip_depth_10_25(h, l, c)
    assert out.name == "RD_DIP_DEPTH_10_25_10_25"


def test_custom_params_in_name():
    h, l, c = _walk(seed=5)
    out = rd_dip_depth_10_25(h, l, c, length=5, avg_length=15)
    assert out.name == "RD_DIP_DEPTH_10_25_5_15"


def test_warmup_is_max_length_avg_length_minus_1_bars():
    h, l, c = _walk(n=200, seed=2)
    out = rd_dip_depth_10_25(h, l, c, length=10, avg_length=25)
    assert out.iloc[:24].isna().all()
    assert out.iloc[24:].notna().all()


def test_offset_shifts_the_series():
    h, l, c = _walk(n=200, seed=6)
    base = rd_dip_depth_10_25(h, l, c)
    shifted = rd_dip_depth_10_25(h, l, c, offset=1)
    pd.testing.assert_series_equal(shifted, base.shift(1), check_names=False)


def test_fillna_fills_the_warmup_nans():
    h, l, c = _walk(n=200, seed=6)
    out = rd_dip_depth_10_25(h, l, c, fillna=0)
    assert not out.isna().any()
    assert (out.iloc[:24] == 0).all()


def test_fill_method_bfill_and_bad_value():
    h, l, c = _walk(n=200, seed=6)
    out = rd_dip_depth_10_25(h, l, c, fill_method="bfill")
    assert not out.isna().any()
    with pytest.raises(ValueError):
        rd_dip_depth_10_25(h, l, c, fill_method="nope")


def test_column_name_and_category():
    h, l, c = _walk(n=60, seed=1)
    out = rd_dip_depth_10_25(h, l, c, length=3, avg_length=5)
    assert out.name == "RD_DIP_DEPTH_10_25_3_5"
    assert out.category == "momentum"


def test_registered_in_category():
    assert "rd_dip_depth_10_25" in ta.Category["momentum"]


def test_accessor_matches_module_level():
    h, l, c = _walk(n=200, seed=9)
    via_module = rd_dip_depth_10_25(h, l, c)
    df = DataFrame({"high": h, "low": l, "close": c})
    via_accessor = df.ta.rd_dip_depth_10_25()
    pd.testing.assert_series_equal(via_module, via_accessor, check_exact=True)
    assert df.ta.rd_dip_depth_10_25(length=5, avg_length=15).name == "RD_DIP_DEPTH_10_25_5_15"
