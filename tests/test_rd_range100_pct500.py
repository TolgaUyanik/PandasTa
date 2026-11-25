# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.volatility.rd_range100_pct500` -- percentile rank
of the 100-bar high-low range among the last 500 (issue #169, Reddit tier
4: rd:algotrading:1nrkjby). Measurements are in
docs/RdRange100Pct500Measured.md.

What these pin, in order of how much it would hurt to lose:

* CORRECTNESS against the issue's own formula: an independent per-window
  loop (plain Python, `np.argmax`/`np.argmin`/a manual rank count, never
  calling the module's own rolling helpers) that recomputes `R =
  (HHV(high,100) - LLV(low,100)) / LLV(low,100)` and its 500-bar percentile
  rank from scratch; a hand-derived constant-range frame where every `R`
  reading is identical, so every percentile rank must read exactly 1.0
  (the `method="max"` tie rule).
* CAUSALITY by future-perturbation (rewrite high/low from bar j onward,
  demand bars [0:j] bit-identical) and a look-ahead mutant (`importlib`
  source read, the percentile-rank input shifted one bar toward the
  future, `exec`'d in memory -- never a hand-written copy), proved live
  and then caught.
* SCALE-FREE: bit-identical under x8/x64 scaling of high AND low together;
  within tolerance under x10/x3.7; `0 < fires < n` plus non-constant.
* Wiring: `Category`, the accessor, and the column name
  `RD_RANGE100_PCT500_100_500`.
"""
import importlib
import types

import numpy as np
import pandas as pd
import pytest
from pandas import DataFrame, Series

from .context import pandas_ta as ta
from pandas_ta.volatility.rd_range100_pct500 import rd_range100_pct500


def _walk(n=1200, seed=11, sigma=0.02):
    rng = np.random.default_rng(seed)
    close = 100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n)))
    spread = close * rng.uniform(0.001, 0.02, n)
    high = close + spread * rng.uniform(0.2, 1.0, n)
    low = close - spread * rng.uniform(0.2, 1.0, n)
    return Series(high), Series(low)


# ------------------------------------------------------------ correctness


def test_matches_an_independent_loop():
    """Re-derives R and its rolling percentile rank independently (plain
    Python rolling max/min + a manual rank-among-the-window count), never
    calling the module's own rolling helpers."""
    high, low = _walk(700)
    length, pctlen = 100, 500
    h, l = high.values, low.values

    r_ref = np.full(len(h), np.nan)
    for t in range(length - 1, len(h)):
        hh = h[t - length + 1:t + 1].max()
        ll = l[t - length + 1:t + 1].min()
        r_ref[t] = (hh - ll) / ll

    rank_ref = np.full(len(h), np.nan)
    for t in range(pctlen - 1, len(h)):
        window = r_ref[t - pctlen + 1:t + 1]
        if np.isnan(window).any():
            continue
        cur = window[-1]
        rank_ref[t] = (window <= cur).sum() / pctlen  # method="max" tie rule

    out = rd_range100_pct500(high, low, length=length, pctlen=pctlen)
    assert (np.isnan(rank_ref) == out.isna().values).all()
    m = ~np.isnan(rank_ref)
    assert np.nanmax(np.abs(out.values[m] - rank_ref[m])) < 1e-9


def test_constant_range_reads_exactly_one():
    """Every `R` reading identical (a perfectly periodic high/low pair) --
    the `method="max"` tie rule means every bar in a tied window reads the
    highest rank, i.e. the percentile rank must be exactly 1.0 everywhere
    it fires."""
    n = 650
    low = Series(np.full(n, 100.0))
    high = Series(np.full(n, 110.0))
    out = rd_range100_pct500(high, low, length=100, pctlen=500).dropna()
    assert len(out) > 0
    assert (out == 1.0).all()


def test_bounded_on_zero_to_one():
    high, low = _walk(900)
    out = rd_range100_pct500(high, low).dropna()
    assert len(out) > 0
    assert (out >= 0.0).all()
    assert (out <= 1.0 + 1e-9).all()


# -------------------------------------------------------------- causality

_REAL = importlib.import_module("pandas_ta.volatility.rd_range100_pct500")


def _load_mutant():
    old = 'out = r.rolling(pctlen).rank(pct=True, method="max")'
    new = 'out = r.shift(-1).rolling(pctlen).rank(pct=True, method="max")'
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_rd_range100_pct500_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


OFFSETS = range(650, 1150, 70)  # past the 100+500-1 = 599-bar warm-up; none
# of these 8 positions sits at the base series' own rank ceiling (1.0) --
# verified once against this fixed seed, since a rank already pinned at
# 1.0 cannot visibly rise further under either perturbation below (see
# `_leaks`'s docstring)


def _leaks(fn):
    """A rank is quantized to 1/pctlen (0.002 at the default 500) and a
    single perturbed bar only ever touches ONE position's window (see the
    module docstring's causality argument) -- swapping in another smooth
    random walk, as the fork's other causality probes do, lands in the
    SAME percentile bucket by coincidence often enough to make a single
    offset an unreliable witness. A deterministic 1000x SPIKE of `high` at
    bar j (forcing `R[j]` to a new window maximum regardless of the other
    99 bars already in its 100-bar lookback, which a single lower value
    could not do -- `rolling(100).max()` is insensitive to one interior
    bar unless that bar WAS the argmax) is reliable in one direction only;
    `OFFSETS` is curated (see above) to avoid the one case the spike
    cannot show -- `R[j]`'s rank already pinned at the 500-bar ceiling
    before the spike, which cannot rise further."""
    high, low = _walk()
    base = fn(high, low)
    hits = 0
    for j in OFFSETS:
        ph = high.copy()
        ph.iloc[j:] = high.iloc[j:].to_numpy() * 1000.0
        out = fn(ph, low)
        a, b = base.iloc[:j], out.iloc[:j]
        if not (a.isna() == b.isna()).all():
            hits += 1
            continue
        m = a.notna()
        if (a[m] != b[m]).any():
            hits += 1
    return hits


def test_real_module_never_reads_the_future():
    assert _leaks(rd_range100_pct500) == 0


def test_mutant_is_caught():
    mod = _load_mutant()
    high, low = _walk()
    assert not mod.rd_range100_pct500(high, low).equals(
        rd_range100_pct500(high, low))  # live
    assert _leaks(mod.rd_range100_pct500) == len(OFFSETS)  # caught at every offset tried


# ------------------------------------------------------------ scale-free


@pytest.mark.parametrize("k", [8.0, 64.0])
def test_scale_is_bit_identical(k):
    high, low = _walk()
    base = rd_range100_pct500(high, low)
    scaled = rd_range100_pct500(high * k, low * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_scale_within_tolerance(k):
    high, low = _walk()
    base = rd_range100_pct500(high, low)
    scaled = rd_range100_pct500(high * k, low * k)
    assert (base.isna() == scaled.isna()).all()
    assert (base - scaled).abs().max() < 1e-9


def test_column_is_not_constant():
    high, low = _walk(1200)
    out = rd_range100_pct500(high, low).dropna()
    assert 0 < len(out) < 1200
    assert out.nunique() > 50


# ---------------------------------------------------------------- edge cases


def test_short_input_returns_none():
    high = Series([110.0] * 5)
    low = Series([100.0] * 5)
    assert rd_range100_pct500(high, low) is None


def test_mismatched_index_raises():
    high, low = _walk(700)
    low.index = low.index + 1
    with pytest.raises(ValueError):
        rd_range100_pct500(high, low)


def test_zero_low_divides_to_nan_not_inf():
    """`LLV(low, 100)` hitting exactly 0.0 would divide-by-zero; the
    prototype's own `sdiv` turns that into NaN, and this module matches."""
    n = 650
    high, low = _walk(n)
    low = low.copy()
    low.iloc[200] = 0.0
    out = rd_range100_pct500(high, low, length=100, pctlen=500)
    assert not np.isinf(out.to_numpy(dtype=float)).any()


def test_offset():
    high, low = _walk(700)
    out0 = rd_range100_pct500(high, low, length=100, pctlen=500)
    out1 = rd_range100_pct500(high, low, length=100, pctlen=500, offset=1)
    aligned = out0.iloc[:-1]
    shifted = out1.iloc[1:]
    assert pd.isna(out1.iloc[0])
    assert (aligned.reset_index(drop=True).dropna()
            == shifted.reset_index(drop=True).dropna()).all()


# ---------------------------------------------------------------- wiring


def test_name_registration_and_accessor():
    high, low = _walk(700)
    df = DataFrame({"open": low, "high": high, "low": low,
                    "close": (high + low) / 2.0, "volume": 1.0})
    assert "rd_range100_pct500" in ta.Category["volatility"]
    out = df.ta.rd_range100_pct500()
    assert out.name == "RD_RANGE100_PCT500_100_500"
    pd.testing.assert_series_equal(out, rd_range100_pct500(high, low))
    assert df.ta.rd_range100_pct500(length=50, pctlen=200).name == "RD_RANGE100_PCT500_50_200"
