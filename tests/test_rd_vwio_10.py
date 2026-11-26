# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.volume.rd_vwio_10` -- volume-weighted imbalance
oscillator (issue #173, Reddit tier 4: rd:algotrading:1c261v8).
Measurements are in docs/RdVwio10Measured.md.

What these pin, in order of how much it would hurt to lose:

* CORRECTNESS against the issue's own formula: a construction where every
  bar closes above its open (all-buy) and one where every bar closes below
  its open (all-sell), so the imbalance is +volume / -volume every bar and
  the ratio must read +1 / -1 exactly; an independent per-bar loop (plain
  Python, never calling the module's own `ema` import) that rebuilds
  buys/sells/imbalance and the two EMAs from scratch; and the module's own
  `pandas_ta.overlap.ema` reading of "EMA" checked against the screen
  prototype's plain `Series.ewm(adjust=False)` reading -- identical after
  the warm-up, to float tolerance.
* CAUSALITY by future-perturbation (rewrite open/close/volume from bar j
  onward, demand bars [0:j] bit-identical) and a look-ahead mutant
  (`importlib` source read, final ratio `.shift(-1)`'d, `exec`'d in memory
  -- never a hand-written copy), proved live and then caught.
* SCALE-FREE: bit-identical under x8/x64/x10/x3.7 price rescale (open and
  close together -- the comparison `close > open` is invariant to ANY
  positive rescale, not just a power-of-two one); bit-identical under
  x8/x64 volume rescale, within tolerance under x10/x3.7; `0 < fires < n`
  plus non-constant.
* Wiring: `Category`, the accessor, and the column name `RD_VWIO_10`.
"""
import importlib
import types

import numpy as np
import pandas as pd
import pytest
from pandas import DataFrame, Series

from .context import pandas_ta as ta
from pandas_ta.volume.rd_vwio_10 import rd_vwio_10


def _close(n=1200, seed=11, sigma=0.02):
    rng = np.random.default_rng(seed)
    return Series(100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n))))


def _open(close, seed=31, jitter=0.01):
    rng = np.random.default_rng(seed)
    prior = close.shift(1)
    prior.iloc[0] = close.iloc[0]
    return (prior * (1.0 + rng.normal(0.0, jitter, len(close)))).rename(None)


def _vol(n=1200, seed=21, lo=100, hi=20000):
    rng = np.random.default_rng(seed)
    return Series(rng.integers(lo, hi, n).astype(float))


def _frame(n=1200, cseed=11, oseed=31, vseed=21):
    close = _close(n, cseed)
    open_ = _open(close, oseed)
    volume = _vol(n, vseed)
    return open_, close, volume


# ------------------------------------------------------------ correctness


def test_all_buy_bars_reads_plus_one():
    """Every bar closes strictly above its own open: imbalance == volume
    every bar, so EMA(imbalance) == EMA(volume) and the ratio is +1."""
    n = 60
    close = Series(100.0 + np.arange(n, dtype=float))
    open_ = close - 1.0
    volume = Series(np.full(n, 500.0))
    out = rd_vwio_10(open_, close, volume, length=10).dropna()
    assert len(out) > 0
    assert (out - 1.0).abs().max() < 1e-9


def test_all_sell_bars_reads_minus_one():
    """Every bar closes strictly below its own open: imbalance == -volume
    every bar, so the ratio is -1."""
    n = 60
    close = Series(100.0 + np.arange(n, dtype=float))
    open_ = close + 1.0
    volume = Series(np.full(n, 500.0))
    out = rd_vwio_10(open_, close, volume, length=10).dropna()
    assert len(out) > 0
    assert (out + 1.0).abs().max() < 1e-9


def test_matches_an_independent_loop():
    """Re-derives buys/sells/imbalance and both EMAs independently (plain
    Python, SMA-seeded recursion matching `pandas_ta.overlap.ema`'s own
    reading), never importing the module's `ema` helper."""
    open_, close, volume = _frame(400)
    n = 10
    o, c, v = open_.values, close.values, volume.values

    def ema_ref(x, length):
        out = np.full(len(x), np.nan)
        seed = np.mean(x[:length])
        out[length - 1] = seed
        alpha = 2.0 / (length + 1.0)
        for i in range(length, len(x)):
            out[i] = alpha * x[i] + (1 - alpha) * out[i - 1]
        return out

    imbalance = np.where(c > o, v, np.where(c < o, -v, 0.0))
    num_ref = ema_ref(imbalance, n)
    den_ref = ema_ref(v, n)
    ref = num_ref / den_ref

    out = rd_vwio_10(open_, close, volume, length=n)
    assert (np.isnan(ref) == out.isna().values).all()
    assert np.nanmax(np.abs(out.values - ref)) < 1e-9


def test_matches_the_screen_prototypes_plain_ewm_reading_after_warmup():
    """The screen prototype (`docs/issues/screen/ind_screen_r6.py`) reads
    "EMA" as a plain `Series.ewm(span=10, adjust=False).mean()` with no SMA
    seed. This module instead reuses `pandas_ta.overlap.ema` (SMA-seeded) so
    Gate D's `0 < fires < n` can see a real warm-up. The two readings differ
    from a different seed (bar 9's SMA seed vs. bar 0's single-bar seed) by
    a transient that decays geometrically at rate `(1 - 2/(n+1))` per bar --
    `docs/measure_rd_vwio_10.py` measures the decay directly. By bar 100
    (`(9/11)**91` ~ 1.2e-8, seed at bar 9 to bar 100 is 91 steps) the two
    readings must agree to float tolerance."""
    open_, close, volume = _frame(500)
    n = 10
    buys = volume.where(close > open_, 0.0)
    sells = volume.where(close < open_, 0.0)
    imbalance = buys - sells
    prototype = (imbalance.ewm(span=n, adjust=False).mean()
                 / volume.ewm(span=n, adjust=False).mean())

    out = rd_vwio_10(open_, close, volume, length=n)
    tail = out.index >= 100
    both_settled = tail & out.notna() & prototype.notna()
    assert both_settled.sum() > 350
    diff = (out[both_settled] - prototype[both_settled]).abs()
    assert diff.max() < 1e-6


def test_bounded_near_minus_one_to_one():
    out = rd_vwio_10(*_frame(600)).dropna()
    assert len(out) > 0
    assert (out.abs() <= 1.0 + 1e-9).all()


# -------------------------------------------------------------- causality

_REAL = importlib.import_module("pandas_ta.volume.rd_vwio_10")


def _load_mutant():
    old = "out = (num / den).replace([np.inf, -np.inf], np.nan)"
    new = "out = (num / den).shift(-1).replace([np.inf, -np.inf], np.nan)"
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_rd_vwio_10_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


OFFSETS = range(60, 1100, 65)  # 16 offsets, all past the length=10 warm-up


def _leaks(fn):
    open_, close, volume = _frame()
    base = fn(open_, close, volume)
    other_open, other_close, other_volume = _frame(cseed=99, oseed=131, vseed=199)
    hits = 0
    for j in OFFSETS:
        po, pc, pv = open_.copy(), close.copy(), volume.copy()
        po.iloc[j:] = other_open.iloc[j:].values
        pc.iloc[j:] = other_close.iloc[j:].values
        pv.iloc[j:] = other_volume.iloc[j:].values
        out = fn(po, pc, pv)
        a, b = base.iloc[:j], out.iloc[:j]
        if not (a.isna() == b.isna()).all():
            hits += 1
            continue
        m = a.notna()
        if (a[m] != b[m]).any():
            hits += 1
    return hits


def test_real_module_never_reads_the_future():
    assert _leaks(rd_vwio_10) == 0


def test_mutant_is_caught():
    mod = _load_mutant()
    open_, close, volume = _frame()
    assert not mod.rd_vwio_10(open_, close, volume).equals(
        rd_vwio_10(open_, close, volume))  # live
    assert _leaks(mod.rd_vwio_10) == len(OFFSETS)  # caught at every offset tried


# ------------------------------------------------------------ scale-free


@pytest.mark.parametrize("k", [8.0, 64.0, 10.0, 3.7])
def test_price_scale_is_bit_identical(k):
    """`close > open` is invariant to ANY positive rescale of both together
    -- not just a power of two -- since no price magnitude enters the
    arithmetic, only the sign of the comparison."""
    open_, close, volume = _frame()
    base = rd_vwio_10(open_, close, volume)
    scaled = rd_vwio_10(open_ * k, close * k, volume)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("k", [8.0, 64.0])
def test_volume_scale_is_bit_identical(k):
    open_, close, volume = _frame()
    base = rd_vwio_10(open_, close, volume)
    scaled = rd_vwio_10(open_, close, volume * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_volume_scale_within_tolerance(k):
    open_, close, volume = _frame()
    base = rd_vwio_10(open_, close, volume)
    scaled = rd_vwio_10(open_, close, volume * k)
    assert (base.isna() == scaled.isna()).all()
    assert (base - scaled).abs().max() < 1e-9


def test_column_is_not_constant():
    out = rd_vwio_10(*_frame()).dropna()
    n_total = len(_frame()[1])
    assert 0 < len(out) < n_total
    assert out.nunique() > 100


# ---------------------------------------------------------------- edge cases


def test_short_input_returns_none():
    open_ = Series([100.0] * 5)
    close = Series([100.0] * 5)
    volume = Series([500.0] * 5)
    assert rd_vwio_10(open_, close, volume, length=20) is None


def test_doji_bars_contribute_zero_imbalance():
    """`close == open`: the issue's own `(close > open)`/`(close < open)`
    both evaluate False, so a run of exact dojis with non-zero volume must
    contribute 0 to the numerator on every one of those bars, moving only
    the volume denominator."""
    n = 40
    close = Series(100.0 + np.arange(n, dtype=float) * 0.0)
    open_ = close.copy()
    volume = Series(np.full(n, 500.0))
    out = rd_vwio_10(open_, close, volume, length=10).dropna()
    assert len(out) > 0
    assert (out.abs() < 1e-9).all()


def test_doji_contributes_zero_among_directional_neighbours():
    """A doji bar sitting among ordinary directional bars must contribute
    exactly 0 to `imbalance` while its non-tied neighbours still contribute
    their own +-volume sign -- unlike the all-equal frame above, where a bug
    that only zeroes EVERY bar uniformly would still pass. This runs the
    REAL module (not a hand re-derivation) on a frame with forced ties
    mixed among ordinary bars, against an independent per-bar reference
    that has the same ties forced into it, so a module bug in how it
    combines tied and untied bars would show up as a mismatch."""
    open_, close, volume = _frame(200)
    close = close.copy()
    tie_positions = [20, 75, 130]
    for i in tie_positions:
        close.iloc[i] = open_.iloc[i]  # force an exact tie at these bars

    n = 10
    o, c, v = open_.values, close.values, volume.values
    for i in tie_positions:
        assert c[i] == o[i]  # the forced tie actually landed

    def ema_ref(x, length):
        out = np.full(len(x), np.nan)
        out[length - 1] = np.mean(x[:length])
        alpha = 2.0 / (length + 1.0)
        for i in range(length, len(x)):
            out[i] = alpha * x[i] + (1 - alpha) * out[i - 1]
        return out

    imbalance_ref = np.where(c > o, v, np.where(c < o, -v, 0.0))
    for i in tie_positions:
        assert imbalance_ref[i] == 0.0  # the reference itself zeroes the tie
    ref = ema_ref(imbalance_ref, n) / ema_ref(v, n)

    out = rd_vwio_10(open_, close, volume, length=n)
    assert (np.isnan(ref) == out.isna().values).all()
    assert np.nanmax(np.abs(out.values - ref)) < 1e-9


def test_offset():
    open_, close, volume = _frame(300)
    out0 = rd_vwio_10(open_, close, volume, length=10)
    out1 = rd_vwio_10(open_, close, volume, length=10, offset=1)
    aligned = out0.iloc[:-1]
    shifted = out1.iloc[1:]
    assert pd.isna(out1.iloc[0])
    assert (aligned.reset_index(drop=True).dropna()
            == shifted.reset_index(drop=True).dropna()).all()


# ---------------------------------------------------------------- wiring


def test_name_registration_and_accessor():
    open_, close, volume = _frame(500)
    df = DataFrame({"open": open_, "high": np.maximum(open_, close) + 1.0,
                    "low": np.minimum(open_, close) - 1.0, "close": close,
                    "volume": volume})
    assert "rd_vwio_10" in ta.Category["volume"]
    out = df.ta.rd_vwio_10()
    assert out.name == "RD_VWIO_10"
    pd.testing.assert_series_equal(out, rd_vwio_10(open_, close, volume))
    assert df.ta.rd_vwio_10(length=20).name == "RD_VWIO_20"
