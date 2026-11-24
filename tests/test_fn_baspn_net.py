# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.volume.fn_baspn_net` -- PandasTa issue #150,
normalised buying minus selling pressure (40, 20). Source: finta (LGPL-3.0,
archived) -- existence, not evidence; `fn_baspn_net`'s own source is NOT in
this worktree, and the formula below is recalled from the issue text, never
read off finta's code:

    BASPN = EMA20((C-L)/EMA40(C-L) * V/EMA40(V)) - EMA20((H-C)/EMA40(H-C) * V/EMA40(V))

Measurements in `docs/FnBaspnNetMeasured.md`.

What these tests pin, in order of how much it would hurt to lose:

* CORRECTNESS against an independent scalar-loop re-implementation of this
  fork's own EMA algorithm (SMA-seeded warm-up, leading-NaN skip, recursive
  from there) -- written from the formula and the EMA definition, never by
  importing `pandas_ta.overlap.ema`.
* CAUSALITY by future-perturbation: rewrite every bar from `j` onward with
  an UNRELATED walk, demand bars `[0:j)` bit-identical with matching NaN
  masks, over 32 offsets past the warm-up. Two mutants (`importlib`-read
  source, `exec`'d in memory, never a hand copy): the close read into the
  buy/sell pressure legs taken one bar forward, and the volume read into the
  normalising ratio taken one bar forward. Both are live (differ from the
  real module) and both are caught on every offset.
* SCALE-FREE in the STRONG sense: every term is a ratio of a quantity to an
  EMA of itself, so a price rescale (high, low, close together) or an
  independent volume rescale leaves the column UNCHANGED, not merely
  proportionally rescaled -- checked bit-identical for x8/x64 price-only,
  volume-only, and combined (both at once), plus tolerance for x10/x3.7. Plus
  `0 < fires < n` and a non-constant column.
* Wiring: the accessor, the column name `FN_BASPN_NET_40_20`, and its
  `Category['volume']` entry.
* Gate E: pending, run by issue-solver after this session; see
  docs/FnBaspnNetMeasured.md.
"""
import importlib
import types

import numpy as np
import pandas as pd
import pytest
from pandas import DataFrame, Series

from .context import pandas_ta as ta
from pandas_ta.volume.fn_baspn_net import fn_baspn_net

SLOW, FAST = 40, 20


def _ohlcv_walk(n=1200, seed=11, sigma=0.02, wick=0.004, tick=None):
    """A GBM close walk with independent high/low wicks (high > close > low
    strictly) and a positive, independently-varying volume series."""
    rng = np.random.default_rng(seed)
    close = 100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n)))
    if tick:
        close = np.round(close / tick) * tick
    hi_wick = np.abs(rng.normal(0.0, wick, n)) + 1e-6
    lo_wick = np.abs(rng.normal(0.0, wick, n)) + 1e-6
    high = close * (1.0 + hi_wick)
    low = close * (1.0 - lo_wick)
    volume = 1_000.0 * np.exp(rng.normal(0.0, 0.5, n))
    return Series(high), Series(low), Series(close), Series(volume)


# ------------------------------------------------------------- Gate A


def _ema_ref(x, length):
    """Independent re-implementation of this fork's own EMA (SMA-seeded
    warm-up, then a recursive EMA that skips a leading NaN block and seeds
    on the first valid value) -- written from `pandas_ta/overlap/ema.py`'s
    documented algorithm, not by calling it."""
    x = np.asarray(x, dtype=float)
    n = len(x)
    out = np.full(n, np.nan)
    if n < length:
        return out
    alpha = 2.0 / (length + 1.0)
    seed_window = x[:length]
    sma = np.nan if np.isnan(seed_window).any() else seed_window.mean()
    modified = x.copy()
    modified[:length - 1] = np.nan
    modified[length - 1] = sma
    prev = None
    for i in range(n):
        v = modified[i]
        if np.isnan(v):
            continue
        out[i] = v if prev is None else alpha * v + (1.0 - alpha) * prev
        prev = out[i]
    return out


def _reference(high, low, close, volume, slow=SLOW, fast=FAST):
    h, l, c, v = (np.asarray(s, dtype=float) for s in (high, low, close, volume))
    ema_v = _ema_ref(v, slow)
    nv = np.where(ema_v == 0, np.nan, v / ema_v)
    bp, sp = c - l, h - c
    ema_bp, ema_sp = _ema_ref(bp, slow), _ema_ref(sp, slow)
    buy_ratio = np.where(ema_bp == 0, np.nan, bp / ema_bp)
    sell_ratio = np.where(ema_sp == 0, np.nan, sp / ema_sp)
    buy = _ema_ref(buy_ratio * nv, fast)
    sell = _ema_ref(sell_ratio * nv, fast)
    return buy - sell


def test_matches_an_independent_scalar_loop():
    high, low, close, volume = _ohlcv_walk(400)
    base = fn_baspn_net(high, low, close, volume)
    loop = _reference(high, low, close, volume)
    m = base.notna() & ~np.isnan(loop)
    assert int(m.sum()) > 300
    assert float(np.nanmax(np.abs(base[m].to_numpy() - loop[m.to_numpy()]))) < 1e-9
    assert (base.isna().to_numpy() == np.isnan(loop)).all()


def test_hand_derived_literal_at_the_warmup_boundary():
    """Three bars, `slow=2` and `fast=1` (so the outer EMA is a pure
    pass-through: alpha = 2/(1+1) = 1, i.e. `ema(x, 1) == x` exactly), worked
    out BY HAND, not by re-running `_reference`:

        bp = close - low = [1, 2, 2];  sp = high - close = [1, 1, 1]
        ema_bp[1] = mean(bp[0:2]) = mean(1, 2)     = 1.5
        ema_sp[1] = mean(sp[0:2]) = mean(1, 1)     = 1.0
        ema_v[1]  = mean(volume[0:2]) = mean(100, 200) = 150.0

        norm_volume[1] = volume[1] / ema_v[1]  = 200 / 150   = 4/3
        buy_ratio[1]   = bp[1] / ema_bp[1]      = 2 / 1.5     = 4/3
        sell_ratio[1]  = sp[1] / ema_sp[1]      = 1 / 1.0     = 1

        buy[1]  = buy_ratio[1]  * norm_volume[1] = (4/3) * (4/3) = 16/9
        sell[1] = sell_ratio[1] * norm_volume[1] = 1    * (4/3) = 4/3 = 12/9
        BASPN_NET[1] = buy[1] - sell[1] = 16/9 - 12/9 = 4/9

    Bar 2's inputs are irrelevant to this value by construction (causal), and
    are filled with arbitrary-but-valid numbers only so `verify_series`'s
    3-bar minimum (`max(slow, fast) + 1`) is met.
    """
    high = Series([11.0, 13.0, 12.0])
    low = Series([9.0, 10.0, 9.0])
    close = Series([10.0, 12.0, 11.0])
    volume = Series([100.0, 200.0, 160.0])
    out = fn_baspn_net(high, low, close, volume, slow=2, fast=1)
    assert np.isnan(out.iloc[0])
    assert out.iloc[1] == pytest.approx(4.0 / 9.0, abs=1e-12)


# -------------------------------------------------------------- causality

_REAL = importlib.import_module("pandas_ta.volume.fn_baspn_net")

_SRC_PRESSURE = "    buy_pressure, sell_pressure = close - low, high - close"
_SRC_VOLUME = "    norm_volume = volume / ema(volume, length=slow).replace(0, npNaN)"

MUTANTS = {
    "forward_close": (_SRC_PRESSURE,
                       "    buy_pressure, sell_pressure = close.shift(-1) - low, high - close"),
    "forward_volume": (_SRC_VOLUME,
                        "    norm_volume = volume.shift(-1) / ema(volume, length=slow).replace(0, npNaN)"),
}
OFFSETS = range(60, 1150, 35)  # 32 offsets, past the ~39-bar warm-up


def _load_mutant(old, new, tag):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType(f"_fn_baspn_net_mutant_{tag}")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


def _leaks(fn, high, low, close, volume, other_high, other_low, other_close, other_volume):
    base = fn(high, low, close, volume)
    hits = 0
    for j in OFFSETS:
        ph, pl, pc, pv = high.copy(), low.copy(), close.copy(), volume.copy()
        ph.iloc[j:] = other_high.iloc[j:].to_numpy()
        pl.iloc[j:] = other_low.iloc[j:].to_numpy()
        pc.iloc[j:] = other_close.iloc[j:].to_numpy()
        pv.iloc[j:] = other_volume.iloc[j:].to_numpy()
        out = fn(ph, pl, pc, pv)
        a, b = base.iloc[:j], out.iloc[:j]
        if not (a.isna() == b.isna()).all():
            hits += 1
            continue
        m = a.notna()
        if (a[m] != b[m]).any():
            hits += 1
    return hits


def test_real_module_never_reads_the_future():
    high, low, close, volume = _ohlcv_walk()
    oh, ol, oc, ov = _ohlcv_walk(seed=99)
    assert _leaks(fn_baspn_net, high, low, close, volume, oh, ol, oc, ov) == 0


@pytest.mark.parametrize("tag", sorted(MUTANTS))
def test_each_mutant_is_live_and_caught_on_every_offset(tag):
    mod = _load_mutant(*MUTANTS[tag], tag)
    high, low, close, volume = _ohlcv_walk()
    oh, ol, oc, ov = _ohlcv_walk(seed=99)
    assert not mod.fn_baspn_net(high, low, close, volume).equals(
        fn_baspn_net(high, low, close, volume))
    assert _leaks(mod.fn_baspn_net, high, low, close, volume, oh, ol, oc, ov) == len(list(OFFSETS))


def test_a_positive_offset_only_delays_and_a_negative_one_is_the_callers_ask():
    high, low, close, volume = _ohlcv_walk(400, seed=3)
    base = fn_baspn_net(high, low, close, volume)
    pd.testing.assert_series_equal(fn_baspn_net(high, low, close, volume, offset=2),
                                   base.shift(2), check_names=False)
    pd.testing.assert_series_equal(fn_baspn_net(high, low, close, volume, offset=-2),
                                   base.shift(-2), check_names=False)


# -------------------------------------------------------------- scale-free


@pytest.mark.parametrize("k", [8.0, 64.0])
def test_a_power_of_two_price_scale_is_bit_identical(k):
    high, low, close, volume = _ohlcv_walk()
    base = fn_baspn_net(high, low, close, volume)
    scaled = fn_baspn_net(high * k, low * k, close * k, volume)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert int(m.sum()) > 0
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("k", [8.0, 64.0])
def test_a_power_of_two_volume_scale_is_bit_identical(k):
    high, low, close, volume = _ohlcv_walk()
    base = fn_baspn_net(high, low, close, volume)
    scaled = fn_baspn_net(high, low, close, volume * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("k", [8.0, 64.0])
def test_a_power_of_two_combined_price_and_volume_scale_is_bit_identical(k):
    """Price and volume rescaled AT ONCE, with DIFFERENT factors -- the
    strongest form of the scale-free claim, since price and volume cancel
    independently inside different ratios and a bug coupling them would only
    show up when both move together."""
    high, low, close, volume = _ohlcv_walk()
    base = fn_baspn_net(high, low, close, volume)
    scaled = fn_baspn_net(high * k, low * k, close * k, volume * (k / 2.0))
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_a_non_power_of_two_price_scale_agrees_to_tolerance(k):
    high, low, close, volume = _ohlcv_walk()
    base = fn_baspn_net(high, low, close, volume)
    scaled = fn_baspn_net(high * k, low * k, close * k, volume)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert float((base[m] - scaled[m]).abs().max()) < 1e-9


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_a_non_power_of_two_volume_scale_agrees_to_tolerance(k):
    high, low, close, volume = _ohlcv_walk()
    base = fn_baspn_net(high, low, close, volume)
    scaled = fn_baspn_net(high, low, close, volume * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert float((base[m] - scaled[m]).abs().max()) < 1e-9


def test_fires_and_is_not_constant():
    high, low, close, volume = _ohlcv_walk()
    out = fn_baspn_net(high, low, close, volume)
    fires = int(out.notna().sum())
    assert 0 < fires < len(close)
    assert int(out.nunique()) > 100


def test_no_inf_on_a_realistic_walk():
    high, low, close, volume = _ohlcv_walk(tick=0.05)
    out = fn_baspn_net(high, low, close, volume).dropna()
    assert np.isfinite(out.to_numpy()).all()


# ------------------------------------------------------------- edge, guards


def test_insufficient_history_returns_none():
    high, low, close, volume = _ohlcv_walk(SLOW)
    assert fn_baspn_net(high, low, close, volume) is None


@pytest.mark.parametrize("slow,fast", [(None, None), (0, 0), (-5, -5)])
def test_non_positive_periods_fall_back_to_the_default(slow, fast):
    high, low, close, volume = _ohlcv_walk(400, seed=31)
    out = fn_baspn_net(high, low, close, volume, slow=slow, fast=fast)
    assert out.name == "FN_BASPN_NET_40_20"


def test_distinct_periods_produce_distinct_names_and_values():
    high, low, close, volume = _ohlcv_walk(600, seed=31)
    a = fn_baspn_net(high, low, close, volume, slow=20, fast=10)
    b = fn_baspn_net(high, low, close, volume, slow=60, fast=30)
    assert (a.name, b.name) == ("FN_BASPN_NET_20_10", "FN_BASPN_NET_60_30")
    m = a.notna() & b.notna()
    assert int(m.sum()) > 300
    assert float(a[m].corr(b[m], method="spearman")) < 0.999


def test_fillna_applies():
    high, low, close, volume = _ohlcv_walk(200, seed=13)
    out = fn_baspn_net(high, low, close, volume, fillna=-999.0)
    assert int((out == -999.0).sum()) > 0


# ------------------------------------------------------------- wiring


def test_name_registration_and_accessor():
    high, low, close, volume = _ohlcv_walk(300, seed=17)
    df = DataFrame({"open": close, "high": high, "low": low, "close": close,
                    "volume": volume})
    assert "fn_baspn_net" in ta.Category["volume"]
    assert hasattr(df.ta, "fn_baspn_net")
    direct = fn_baspn_net(high, low, close, volume)
    through = df.ta.fn_baspn_net()
    pd.testing.assert_series_equal(through, direct, check_names=True)
