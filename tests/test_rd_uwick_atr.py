# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.candles.rd_uwick_atr` -- upper wick (high minus the
body top) divided by a Wilder-smoothed ATR(5) (issue #172, RD-UWICK-ATR;
Reddit, tier 4: rd:Daytrading:1rjq7kd). Measurements are in
docs/RdUwickAtrMeasured.md.

What these pin, in order of how much it would hurt to lose:

* CORRECTNESS against the issue's own formula (not the screen prototype):
  a hand-derived fixture, every input bar and the expected ratio chosen on
  paper before the module ran, plus a cross-check against an independent
  per-bar Python loop (true range + Wilder recursion, built straight from
  the formula) on a synthetic frame.
* A zero-ATR run (every bar in the smoothing window a flat doji at an
  unchanged close) reads NaN (0/0), not 0 or inf.
* CAUSALITY by future-splice: bars before a perturbation point J stay
  bit-identical, and a mutant (the final ratio with `.shift(-1)` appended,
  reading one bar ahead) is proved live and caught.
* SCALE-FREE: bit-identical under a power-of-two price rescale (x8, x64),
  since the numerator and every term feeding the ATR are each a
  like-for-like price difference. Under a non-power-of-two rescale (x10,
  x3.7) each operand carries its own last-bit rounding, bounded here as a
  measured tolerance.
* Reachability (fires on real data shape, not a constant column) and the
  wiring (`Category`, the accessor, warm-up, column name).
"""
import importlib
import types

import numpy as np
import pandas as pd
import pytest
from pandas import DataFrame

from .context import pandas_ta as ta

_REAL = importlib.import_module("pandas_ta.candles.rd_uwick_atr")
rd_uwick_atr = _REAL.rd_uwick_atr


# ---------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------
def _ohlc(rows):
    """rows: list of (open, high, low, close) 4-tuples, oldest first."""
    o, h, l, c = zip(*rows)
    return DataFrame({"open": o, "high": h, "low": l, "close": c})


def _hand_rows():
    """length=2 (short window to keep the hand-derivation small).
    bar0: open=100 high=104 low=98  close=101 (upper_wick=104-101=3)
    bar1: open=101 high=103 low=97  close=99  (upper_wick=103-101=2, since
          MAX(open,close)=101)
    bar2: open=99  high=106 low=96  close=102 (upper_wick=106-102=4)
    True range: bar0 = high-low = 6 (no prior close); bar1 = max(103-97,
          |103-101|, |97-101|) = max(6,2,4) = 6; bar2 = max(106-96,
          |106-99|, |96-99|) = max(10,7,3) = 10.
    Wilder ATR(2), SMA-seeded: seed at bar1 = mean(TR[0], TR[1]) = 6.0;
          bar2 = TR[1] seed recursion: ATR[2] = ATR[1] + (TR[2]-ATR[1])/2
          = 6 + (10-6)/2 = 8.0.
    """
    rows = [
        (100.0, 104.0, 98.0, 101.0),
        (101.0, 103.0, 97.0, 99.0),
        (99.0, 106.0, 96.0, 102.0),
    ]
    return rows


def test_hand_derived_value():
    """`true_range` forces its own first bar to NaN (`drift`-bar warm-up,
    independent of this port), so Wilder's SMA seed needs the FIRST two
    non-NaN true ranges -- bar1 (TR=6) and bar2 (TR=10) -- landing the first
    valid ATR at bar2, not bar1."""
    df = _ohlc(_hand_rows())
    out = rd_uwick_atr(df.open, df.high, df.low, df.close, length=2)
    assert out.iloc[:2].isna().all()
    # bar2: upper_wick = 106 - max(99, 102) = 4; ATR[2] seed = mean(TR1=6, TR2=10) = 8
    assert out.iloc[2] == pytest.approx(4.0 / 8.0, abs=1e-9)


def test_flat_run_reads_zero_not_nan():
    """A run of flat dojis (open == high == low == close, unchanged) has
    zero true range throughout -- but `true_range` reads it via
    `non_zero_range`, which floors any exactly-equal high/low pair at
    machine epsilon rather than leaving it 0 (this fork's own defence
    against crypto data where `high == low`), so ATR here is a tiny
    epsilon, never exactly 0. The ratio is therefore 0/eps = 0.0, not NaN
    -- the inf-guard in the module exists for the in-principle exact-zero-
    ATR case this epsilon floor otherwise forecloses."""
    rows = [(100.0, 100.0, 100.0, 100.0)] * 8
    df = _ohlc(rows)
    out = rd_uwick_atr(df.open, df.high, df.low, df.close, length=3)
    assert out.iloc[:3].isna().all()
    assert (out.iloc[3:] == 0.0).all()


def _frame(n=1600, seed=11):
    """Synthetic OHLC with non-trivial upper/lower wicks drawn independently
    of body direction."""
    rng = np.random.default_rng(seed)
    ret = rng.normal(0.0, 0.01, n)
    close = 100.0 * np.exp(np.cumsum(ret))
    openp = np.empty(n)
    openp[0] = close[0]
    openp[1:] = close[:-1] * (1.0 + rng.normal(0.0, 0.004, n - 1))
    body_hi = np.maximum(openp, close)
    body_lo = np.minimum(openp, close)
    wick_up = np.abs(rng.normal(0.0, 0.003, n)) * close
    wick_dn = np.abs(rng.normal(0.0, 0.003, n)) * close
    high = body_hi + wick_up
    low = body_lo - wick_dn
    idx = pd.date_range("2020-01-01", periods=n, freq="D")
    return DataFrame({"open": openp, "high": high, "low": low, "close": close},
                      index=idx)


def _independent_atr5(h, l, c, length=5):
    """Wilder ATR, SMA-seeded, built straight from the formula -- not read
    from `wilder_rma` or `true_range`. `true_range`'s own bar-0 is forced to
    NaN by its `drift`-bar warm-up (independent of this port), so the SMA
    seed needs the first `length` non-NaN true ranges -- bars 1..length --
    landing the first valid ATR at bar `length`, not `length - 1`."""
    n = len(c)
    tr = np.full(n, np.nan)
    for t in range(1, n):
        tr[t] = max(h[t] - l[t], abs(h[t] - c[t - 1]), abs(l[t] - c[t - 1]))
    out = np.full(n, np.nan)
    if n <= length:
        return out
    out[length] = np.nanmean(tr[1:length + 1])
    for t in range(length + 1, n):
        out[t] = out[t - 1] + (tr[t] - out[t - 1]) / length
    return out


def test_matches_an_independent_loop():
    df = _frame()
    length = 5
    out = rd_uwick_atr(df.open, df.high, df.low, df.close, length=length)

    o, h, l, c = (df[k].to_numpy(dtype=float) for k in ("open", "high", "low", "close"))
    n = len(c)
    upper_wick = h - np.maximum(o, c)
    atr_ref = _independent_atr5(h, l, c, length=length)
    ref = np.full(n, np.nan)
    m = ~np.isnan(atr_ref) & (atr_ref != 0)
    ref[m] = upper_wick[m] / atr_ref[m]

    assert (np.isnan(ref) == out.isna().values).all()
    mm = ~np.isnan(ref)
    np.testing.assert_allclose(out.values[mm], ref[mm], rtol=1e-9)


def test_warmup_matches_atr_warmup():
    df = _frame(200)
    out = rd_uwick_atr(df.open, df.high, df.low, df.close, length=5)
    first_valid = out.notna().idxmax()
    assert out.loc[:first_valid].iloc[:-1].isna().all()
    assert out.loc[first_valid:].notna().all()


def test_default_length_in_name():
    df = _frame()
    out = rd_uwick_atr(df.open, df.high, df.low, df.close)
    assert out.name == "RD_UWICK_ATR"


def test_custom_length_runs():
    df = _frame()
    out = rd_uwick_atr(df.open, df.high, df.low, df.close, length=20)
    assert out.name == "RD_UWICK_ATR"
    assert out.notna().any()


def test_offset_shifts_the_series():
    df = _frame(200)
    base = rd_uwick_atr(df.open, df.high, df.low, df.close)
    shifted = rd_uwick_atr(df.open, df.high, df.low, df.close, offset=1)
    pd.testing.assert_series_equal(shifted, base.shift(1), check_names=False)


def test_fillna_fills_the_warmup_nans():
    df = _frame(200)
    out = rd_uwick_atr(df.open, df.high, df.low, df.close, fillna=0)
    assert not out.isna().any()


def test_short_input_returns_none():
    df = _ohlc(_hand_rows()[:1])
    assert rd_uwick_atr(df.open, df.high, df.low, df.close, length=5) is None


# -------------------------------------------------------------- causality
def _load_mutant():
    old = 'out = (upper_wick / atr5).replace([np.inf, -np.inf], np.nan)'
    new = 'out = (upper_wick / atr5).replace([np.inf, -np.inf], np.nan).shift(-1)'
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_rd_uwick_atr_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


OFFSETS = range(100, 1500, 50)  # 28 offsets, all past warm-up


def _leaks(fn, base_frame, other_frame):
    base = fn(base_frame.open, base_frame.high, base_frame.low, base_frame.close)
    hits = 0
    for j in OFFSETS:
        spliced = base_frame.copy()
        spliced.iloc[j:] = other_frame.iloc[j:].to_numpy()
        out = fn(spliced.open, spliced.high, spliced.low, spliced.close)
        a, b = base.iloc[:j], out.iloc[:j]
        if not (a.isna() == b.isna()).all():
            hits += 1
            continue
        m = a.notna()
        if (a[m] != b[m]).any():
            hits += 1
    return hits


def test_real_module_never_reads_the_future():
    a, b = _frame(1600, seed=1), _frame(1600, seed=2)
    assert _leaks(rd_uwick_atr, a, b) == 0


def test_lookahead_mutant_is_caught():
    mod = _load_mutant()
    a, b = _frame(1600, seed=1), _frame(1600, seed=2)
    mut = lambda o, h, l, c: mod.rd_uwick_atr(o, h, l, c)  # noqa: E731
    real_out = rd_uwick_atr(a.open, a.high, a.low, a.close)
    mut_out = mut(a.open, a.high, a.low, a.close)
    assert not mut_out.equals(real_out)  # live

    hits = _leaks(mut, a, b)
    assert hits > 0, f"mutant never leaked across {len(OFFSETS)} J values -- test is blind"


# ------------------------------------------------------------ scale-free
@pytest.mark.parametrize("k", [8.0, 64.0])
def test_power_of_two_scale_is_bit_identical(k):
    """upper_wick and every term feeding Wilder's ATR are each a difference
    of like-for-like price terms, so a power-of-two rescale is an exact
    exponent shift on every operand -- the correctly-rounded ratio cannot
    move."""
    df = _frame(seed=4)
    base = rd_uwick_atr(df.open, df.high, df.low, df.close)
    scaled = rd_uwick_atr(df.open * k, df.high * k, df.low * k, df.close * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_other_scales_stay_within_a_tiny_tolerance(k):
    """Not provably bit-exact: each scaled operand carries its own last-bit
    rounding. Bounded here as a measured tolerance, not a mathematical
    guarantee the way the power-of-two case is."""
    df = _frame(seed=4)
    base = rd_uwick_atr(df.open, df.high, df.low, df.close)
    scaled = rd_uwick_atr(df.open * k, df.high * k, df.low * k, df.close * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    max_diff = (base[m] - scaled[m]).abs().max()
    assert max_diff < 1e-6


# ------------------------------------------------------------ reachability
def test_fires_and_is_not_constant():
    df = _frame(seed=4)
    out = rd_uwick_atr(df.open, df.high, df.low, df.close)
    fired = out.dropna()
    assert 0 < len(fired) < len(out)
    assert fired.nunique() > 1
    assert fired.min() >= 0.0
    assert fired.max() > 0.0


# ---------------------------------------------------------------- wiring
def test_column_name_and_category():
    df = _ohlc(_hand_rows())
    out = rd_uwick_atr(df.open, df.high, df.low, df.close, length=2)
    assert out.name == "RD_UWICK_ATR"
    assert out.category == "candles"


def test_registered_in_category():
    assert "rd_uwick_atr" in ta.Category["candles"]


def test_accessor_matches_module_level():
    df = _frame(n=200, seed=9)
    via_module = rd_uwick_atr(df["open"], df["high"], df["low"], df["close"])
    via_accessor = df.ta.rd_uwick_atr()
    pd.testing.assert_series_equal(via_module, via_accessor, check_exact=True)
    assert df.ta.rd_uwick_atr(length=20).name == "RD_UWICK_ATR"
