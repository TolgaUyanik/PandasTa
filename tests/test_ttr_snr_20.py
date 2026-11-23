# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.volatility.ttr_snr_20` -- PandasTa issue #149,
signal-to-noise ratio: |20-bar move| / ATR(20). Source: R TTR (GPL-2.0),
`SNR.R: abs(Cl - lag(Cl, n)) / ATR(n)` -- cited as existence, not run as an
oracle (`SNR.R` is not in this worktree). Measurements in
`docs/TtrSnr20Measured.md`.

What these tests pin, in order of how much it would hurt to lose:

* CORRECTNESS against an independent scalar-loop Wilder ATR, written from
  Wilder's own recursion rather than imported from this module.
* CAUSALITY by future-perturbation: rewrite every bar from `j` onward,
  demand bars `[0:j)` bit-identical with matching NaN masks, over many
  offsets. Two mutants (`importlib`-read source, `exec`'d in memory, never
  a hand copy): the final write shifted 10 bars earlier, and the close read
  into `move` taken one bar forward. Both are live (differ from the real
  module) and both are caught on every offset the sweep uses.
* SCALE-FREE: bit-identical under x8/x64 (both the numerator and the ATR
  denominator are price-scale quantities, and `k*a / k*b == a / b` exactly
  under a power-of-two `k` in IEEE float), within a measured tolerance under
  x10/x3.7, plus `0 < fires < n` and a non-constant column.
* The FROZEN-SERIES edge case: a totally flat input (no bar ever moves) is
  NOT a `0 / 0` NaN here, because `true_range`'s own `non_zero_range` helper
  already guards a degenerate zero high-low range with a float epsilon --
  existing behaviour of a dependency, not something this module adds.
* Wiring: the accessor, the column name `TTR_SNR_20`, and its
  `Category['volatility']` entry. Gate E is owed: the launcher runs it
  after this session.
"""
import importlib
import types

import numpy as np
import pandas as pd
import pytest
from pandas import DataFrame, Series

from .context import pandas_ta as ta
from pandas_ta.volatility.ttr_snr_20 import ttr_snr_20

LENGTH = 20


def _ohlc_walk(n=1200, seed=11, sigma=0.02, wick=0.004, tick=None):
    """A GBM close walk with independent high/low wicks around it, so
    high > close > low strictly (no degenerate zero-range bars by
    construction, unlike the dedicated frozen-series tests below)."""
    rng = np.random.default_rng(seed)
    close = 100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n)))
    if tick:
        close = np.round(close / tick) * tick
    hi_wick = np.abs(rng.normal(0.0, wick, n)) + 1e-6
    lo_wick = np.abs(rng.normal(0.0, wick, n)) + 1e-6
    high = close * (1.0 + hi_wick)
    low = close * (1.0 - lo_wick)
    return Series(high), Series(low), Series(close)


def _flat(n=60, level=100.0):
    c = Series(np.full(n, level))
    return c, c, c


# ------------------------------------------------------------- Gate A


def _wilder_atr_loop(high, low, close, length=LENGTH):
    """Independent scalar-loop ATR: SMA-seeded Wilder recursion, written
    from Wilder's own definition (not imported from this package)."""
    h, l, c = high.to_numpy(), low.to_numpy(), close.to_numpy()
    n = len(c)
    tr = np.full(n, np.nan)
    for i in range(1, n):
        tr[i] = max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1]))
    atr = np.full(n, np.nan)
    atr[length] = tr[1:length + 1].mean()
    for i in range(length + 1, n):
        atr[i] = (atr[i - 1] * (length - 1) + tr[i]) / length
    return Series(atr, index=close.index)


def test_matches_an_independent_scalar_loop():
    high, low, close = _ohlc_walk(400)
    base = ttr_snr_20(high, low, close)
    loop_atr = _wilder_atr_loop(high, low, close)
    loop = (close - close.shift(LENGTH)).abs() / loop_atr
    m = base.notna() & loop.notna()
    assert int(m.sum()) == 380
    assert float((base[m] - loop[m]).abs().max()) < 1e-10


def test_hand_derived_window_is_exact():
    """Five bars, every TR a hand-computable max of the three true-range
    legs (not just high-low, since the close-to-close gap exceeds the
    high/low wick here), and `move` a plain |close difference|.

    high = close + 0.5, low = close - 0.5:
    TR[1] = max(1, |101.5-100|, |100.5-100|)   = max(1, 1.5, 0.5) = 1.5
    TR[2] = max(1, |102.5-101|, |101.5-101|)   = max(1, 1.5, 0.5) = 1.5
    TR[3] = max(1, |103.5-102|, |102.5-102|)   = max(1, 1.5, 0.5) = 1.5
    TR[4] = max(1, |100.5-103|, |99.5-103|)    = max(1, 2.5, 3.5) = 3.5
    ATR[2] (seed, length=2) = mean(TR[1], TR[2]) = 1.5
    ATR[3] = (ATR[2]*1 + TR[3]) / 2 = 1.5
    ATR[4] = (ATR[3]*1 + TR[4]) / 2 = 2.5
    """
    close = Series([100.0, 101.0, 102.0, 103.0, 100.0])
    high = close + 0.5
    low = close - 0.5
    out = ttr_snr_20(high, low, close, length=2)
    assert out.iloc[2] == pytest.approx(abs(102.0 - 100.0) / 1.5)
    assert out.iloc[3] == pytest.approx(abs(103.0 - 101.0) / 1.5)
    assert out.iloc[4] == pytest.approx(abs(100.0 - 102.0) / 2.5)


# -------------------------------------------------------------- causality

_REAL = importlib.import_module("pandas_ta.volatility.ttr_snr_20")

_SRC_SNR = "    snr = move / atr_val"
_SRC_MOVE = "    move = npabs(close - close.shift(length))"

MUTANTS = {
    "write_shift": (_SRC_SNR, f"{_SRC_SNR}.shift(-10)"),
    "forward_close": (_SRC_MOVE,
                       "    move = npabs(close.shift(-1) - close.shift(length))"),
}
OFFSETS = range(40, 1100, 35)  # 31 offsets, past the 20-bar warm-up


def _load_mutant(old, new, tag):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType(f"_ttr_snr_20_mutant_{tag}")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


def _leaks(fn, high, low, close, other_high, other_low, other_close):
    """Replace every bar from `j` onward with a DIFFERENT path; count the
    `j` values at which anything strictly before `j` moves. Prefix
    truncation alone cannot see back-dating, which is why this perturbs."""
    base = fn(high, low, close)
    hits = 0
    for j in OFFSETS:
        ph, pl, pc = high.copy(), low.copy(), close.copy()
        ph.iloc[j:] = other_high.iloc[j:].to_numpy()
        pl.iloc[j:] = other_low.iloc[j:].to_numpy()
        pc.iloc[j:] = other_close.iloc[j:].to_numpy()
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
    high, low, close = _ohlc_walk()
    oh, ol, oc = _ohlc_walk(seed=99)
    assert _leaks(ttr_snr_20, high, low, close, oh, ol, oc) == 0


@pytest.mark.parametrize("tag", sorted(MUTANTS))
def test_each_mutant_is_live_and_caught_on_every_offset(tag):
    mod = _load_mutant(*MUTANTS[tag], tag)
    high, low, close = _ohlc_walk()
    oh, ol, oc = _ohlc_walk(seed=99)
    assert not mod.ttr_snr_20(high, low, close).equals(ttr_snr_20(high, low, close))
    assert _leaks(mod.ttr_snr_20, high, low, close, oh, ol, oc) == len(list(OFFSETS))


def test_a_positive_offset_only_delays_and_a_negative_one_is_the_callers_ask():
    high, low, close = _ohlc_walk(400, seed=3)
    base = ttr_snr_20(high, low, close)
    pd.testing.assert_series_equal(ttr_snr_20(high, low, close, offset=2),
                                   base.shift(2), check_names=False)
    pd.testing.assert_series_equal(ttr_snr_20(high, low, close, offset=-2),
                                   base.shift(-2), check_names=False)


# -------------------------------------------------------------- scale-free


@pytest.mark.parametrize("k", [8.0, 64.0])
def test_a_power_of_two_price_scale_is_bit_identical(k):
    high, low, close = _ohlc_walk()
    base = ttr_snr_20(high, low, close)
    scaled = ttr_snr_20(high * k, low * k, close * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert int(m.sum()) == 1180
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_a_non_power_of_two_price_scale_agrees_to_tolerance(k):
    high, low, close = _ohlc_walk()
    base = ttr_snr_20(high, low, close)
    scaled = ttr_snr_20(high * k, low * k, close * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert int(m.sum()) == 1180
    assert float((base[m] - scaled[m]).abs().max()) < 1e-10
    assert float(base[m].corr(scaled[m], method="spearman")) > 0.999


def test_fires_and_is_not_constant():
    high, low, close = _ohlc_walk()
    out = ttr_snr_20(high, low, close)
    fires = int(out.notna().sum())
    assert 0 < fires < len(close)
    assert fires == 1180
    assert int(out.nunique()) > 100


def test_non_negative():
    high, low, close = _ohlc_walk(tick=0.05)
    out = ttr_snr_20(high, low, close).dropna()
    assert (out >= 0.0).all()


# ----------------------------------------------------- frozen-series edge


def test_a_totally_flat_series_reads_zero_not_nan():
    """TR is 0 on every bar from bar 0, but `true_range`'s own
    `non_zero_range` guard already adds a float epsilon to a degenerate
    zero high-low range, so ATR settles at a tiny positive float rather
    than exact 0 -- and since `move` is exactly 0 too, the ratio is a
    clean 0.0, never a `0 / 0` NaN."""
    high, low, close = _flat()
    out = ttr_snr_20(high, low, close)
    assert int(out.notna().sum()) == 40
    assert (out.dropna() == 0.0).all()


def test_frozen_after_a_volatile_run_decays_but_does_not_reach_exactly_zero():
    """A 30-bar freeze following a volatile run: Wilder's recursion decays
    the ATR toward zero (factor ~0.95 per bar) but a 30-bar freeze is not
    enough half-lives to hit exact 0, and `move` is 0 over any 20-bar
    window fully inside the freeze -- so the ratio reads a clean 0.0, not
    NaN, on the frozen tail."""
    rng = np.random.default_rng(5)
    lead = 100.0 * np.exp(np.cumsum(rng.normal(0.0, 0.01, 30)))
    c = Series(np.concatenate([lead, np.full(30, lead[-1])]))
    out = ttr_snr_20(c, c, c)
    tail = out.iloc[-9:]
    assert tail.notna().all()
    assert (tail == 0.0).all()


# -------------------------------------------------------- edge, guards


def test_insufficient_history_returns_none():
    high, low, close = _ohlc_walk(LENGTH)
    assert ttr_snr_20(high, low, close) is None


@pytest.mark.parametrize("length", [None, 0, -5])
def test_a_length_below_the_minimum_falls_back_to_the_default(length):
    high, low, close = _ohlc_walk(400, seed=31)
    out = ttr_snr_20(high, low, close, length=length)
    assert out.name == "TTR_SNR_20"


def test_distinct_lengths_produce_distinct_names_and_values():
    high, low, close = _ohlc_walk(600, seed=31)
    a = ttr_snr_20(high, low, close, length=10)
    b = ttr_snr_20(high, low, close, length=40)
    assert (a.name, b.name) == ("TTR_SNR_10", "TTR_SNR_40")
    m = a.notna() & b.notna()
    assert int(m.sum()) > 400
    assert float(a[m].corr(b[m], method="spearman")) < 0.95


def test_fillna_applies():
    high, low, close = _ohlc_walk(200, seed=13)
    out = ttr_snr_20(high, low, close, fillna=-1.0)
    assert int((out == -1.0).sum()) == LENGTH


# ------------------------------------------------------------- wiring


def test_name_registration_and_accessor():
    high, low, close = _ohlc_walk(300, seed=17)
    df = DataFrame({"open": close, "high": high, "low": low, "close": close,
                    "volume": Series(np.full(len(close), 1000.0))})
    assert "ttr_snr_20" in ta.Category["volatility"]
    assert hasattr(df.ta, "ttr_snr_20")
    direct = ttr_snr_20(high, low, close)
    through = df.ta.ttr_snr_20()
    pd.testing.assert_series_equal(through, direct, check_names=True)
    assert through.name == "TTR_SNR_20"
    assert direct.category == "volatility"
