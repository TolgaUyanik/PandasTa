# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.candles.rd_wick_pressure_10` -- bear-candle lower
wicks minus bull-candle upper wicks, trailing 10 bars, divided by the
trailing sum of ranges (issue #170, RD-WICK-PRESSURE-10; Reddit, tier 4:
rd:algotrading:pneq7k). Measurements are in docs/RdWickPressure10Measured.md.

What these pin, in order of how much it would hurt to lose:

* CORRECTNESS against the issue's own formula (not the screen prototype):
  a 4-bar hand-derived fixture, every input bar and the expected ratio
  chosen on paper before the module ran, plus a cross-check against an
  independent per-bar Python loop built straight from the formula on a
  synthetic frame.
* A zero-range window (every bar in the window a doji) reads NaN (0/0),
  not 0 or inf.
* CAUSALITY by future-splice: bars before a perturbation point J stay
  bit-identical whether or not the frame's tail is an unrelated series,
  and a mutant (the final ratio with `.shift(-1)` appended, reading one
  bar ahead) is proved live and caught.
* SCALE-FREE: bit-identical under a power-of-two price rescale (x8, x64),
  since the numerator's two legs and the denominator are each a sum of
  like-for-like price differences on the same bars. Under a non-power-of-
  two rescale (x10, x3.7) each operand carries its own last-bit rounding,
  bounded here as a measured tolerance.
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

_REAL = importlib.import_module("pandas_ta.candles.rd_wick_pressure_10")
rd_wick_pressure_10 = _REAL.rd_wick_pressure_10


# ---------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------
def _ohlc(rows):
    """rows: list of (open, high, low, close) 4-tuples, oldest first."""
    o, h, l, c = zip(*rows)
    return DataFrame({"open": o, "high": h, "low": l, "close": c})


def _hand_rows():
    """length=3.
    bar0: open=100 high=102 low=98  close=99  (bear: lower_wick=99-98=1)
    bar1: open=99  high=103 low=97  close=102 (bull: upper_wick=103-102=1)
    bar2: open=102 high=105 low=100 close=101 (bear: lower_wick=101-100=1)
    bar3: open=101 high=104 low=99  close=103 (bull: upper_wick=104-103=1)
    """
    return [
        (100.0, 102.0, 98.0, 99.0),
        (99.0, 103.0, 97.0, 102.0),
        (102.0, 105.0, 100.0, 101.0),
        (101.0, 104.0, 99.0, 103.0),
    ]


def test_hand_derived_value():
    df = _ohlc(_hand_rows())
    out = rd_wick_pressure_10(df.open, df.high, df.low, df.close, length=3)
    assert out.iloc[:2].isna().all()
    # window [0,1,2]: lower_wick sum 1+0+1=2, upper_wick sum 0+1+0=1,
    # range sum 4+6+5=15 -> (2-1)/15
    assert out.iloc[2] == pytest.approx(1.0 / 15.0, abs=1e-12)
    # window [1,2,3]: lower_wick sum 0+1+0=1, upper_wick sum 1+0+1=2,
    # range sum 6+5+5=16 -> (1-2)/16
    assert out.iloc[3] == pytest.approx(-1.0 / 16.0, abs=1e-12)


def test_zero_range_window_reads_nan():
    """Every bar a doji (open == high == low == close) -- no wick, no
    range, so the window's denominator is 0 and the ratio is NaN (0/0),
    not 0."""
    rows = [(100.0, 100.0, 100.0, 100.0)] * 5
    df = _ohlc(rows)
    out = rd_wick_pressure_10(df.open, df.high, df.low, df.close, length=3)
    assert out.iloc[2:].isna().all()


def _frame(n=1600, seed=11):
    """Synthetic OHLC with real bear/bull candles and non-trivial wicks on
    both sides (spread drawn independently of direction)."""
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


def test_matches_an_independent_loop():
    df = _frame()
    length = 10
    out = rd_wick_pressure_10(df.open, df.high, df.low, df.close, length=length)

    o, h, l, c = (df[k].to_numpy(dtype=float) for k in ("open", "high", "low", "close"))
    n = len(c)
    lower_wick = np.zeros(n)
    upper_wick = np.zeros(n)
    for t in range(n):
        if c[t] < o[t]:
            lower_wick[t] = min(o[t], c[t]) - l[t]
        elif c[t] > o[t]:
            upper_wick[t] = h[t] - max(o[t], c[t])
    rng_ = h - l

    ref = np.full(n, np.nan)
    for t in range(length - 1, n):
        window = slice(t - length + 1, t + 1)
        denom = rng_[window].sum()
        if denom != 0:
            ref[t] = (lower_wick[window].sum() - upper_wick[window].sum()) / denom

    assert (np.isnan(ref) == out.isna().values).all()
    m = ~np.isnan(ref)
    np.testing.assert_allclose(out.values[m], ref[m], rtol=1e-12)


def test_warmup_is_length_minus_one_bars():
    df = _frame(200)
    out = rd_wick_pressure_10(df.open, df.high, df.low, df.close, length=10)
    assert out.iloc[:9].isna().all()
    assert out.iloc[9:].notna().all()


def test_default_length_in_name():
    df = _frame()
    out = rd_wick_pressure_10(df.open, df.high, df.low, df.close)
    assert out.name == "RD_WICK_PRESSURE_10"


def test_custom_length_in_name():
    df = _frame()
    out = rd_wick_pressure_10(df.open, df.high, df.low, df.close, length=20)
    assert out.name == "RD_WICK_PRESSURE_20"


def test_offset_shifts_the_series():
    df = _frame(200)
    base = rd_wick_pressure_10(df.open, df.high, df.low, df.close)
    shifted = rd_wick_pressure_10(df.open, df.high, df.low, df.close, offset=1)
    pd.testing.assert_series_equal(shifted, base.shift(1), check_names=False)


def test_fillna_fills_the_warmup_nans():
    df = _frame(200)
    out = rd_wick_pressure_10(df.open, df.high, df.low, df.close, fillna=0)
    assert not out.isna().any()
    assert (out.iloc[:9] == 0).all()


def test_short_input_returns_none():
    df = _ohlc(_hand_rows()[:2])
    assert rd_wick_pressure_10(df.open, df.high, df.low, df.close, length=10) is None


# -------------------------------------------------------------- causality
def _load_mutant():
    old = "out = (pressure_sum / range_sum).replace([np.inf, -np.inf], np.nan)"
    new = "out = (pressure_sum / range_sum).replace([np.inf, -np.inf], np.nan).shift(-1)"
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_rd_wick_pressure_10_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


OFFSETS = range(100, 1500, 50)  # 28 offsets, all past the 9-bar warm-up


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
    assert _leaks(rd_wick_pressure_10, a, b) == 0


def test_lookahead_mutant_is_caught():
    mod = _load_mutant()
    a, b = _frame(1600, seed=1), _frame(1600, seed=2)
    mut = lambda o, h, l, c: mod.rd_wick_pressure_10(o, h, l, c)  # noqa: E731
    real_out = rd_wick_pressure_10(a.open, a.high, a.low, a.close)
    mut_out = mut(a.open, a.high, a.low, a.close)
    assert not mut_out.equals(real_out)  # live

    hits = _leaks(mut, a, b)
    assert hits > 0, f"mutant never leaked across {len(OFFSETS)} J values -- test is blind"


# ------------------------------------------------------------ scale-free
@pytest.mark.parametrize("k", [8.0, 64.0])
def test_power_of_two_scale_is_bit_identical(k):
    """lower_wick, upper_wick and the range are each a difference of two
    like-for-like price terms on the same bar, so a power-of-two rescale is
    an exact exponent shift on every operand -- the correctly-rounded ratio
    cannot move."""
    df = _frame(seed=4)
    base = rd_wick_pressure_10(df.open, df.high, df.low, df.close)
    scaled = rd_wick_pressure_10(df.open * k, df.high * k, df.low * k, df.close * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_other_scales_stay_within_a_tiny_tolerance(k):
    """Not provably bit-exact: each scaled operand carries its own last-bit
    rounding. Bounded here as a measured tolerance, not a mathematical
    guarantee the way the power-of-two case is."""
    df = _frame(seed=4)
    base = rd_wick_pressure_10(df.open, df.high, df.low, df.close)
    scaled = rd_wick_pressure_10(df.open * k, df.high * k, df.low * k, df.close * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    max_diff = (base[m] - scaled[m]).abs().max()
    assert max_diff < 1e-9


# ------------------------------------------------------------ reachability
def test_fires_and_is_not_constant():
    df = _frame(seed=4)
    out = rd_wick_pressure_10(df.open, df.high, df.low, df.close)
    fired = out.dropna()
    assert 0 < len(fired) < len(out)
    assert fired.nunique() > 1
    assert fired.min() < 0.0 and fired.max() > 0.0


# ---------------------------------------------------------------- wiring
def test_column_name_and_category():
    df = _ohlc(_hand_rows())
    out = rd_wick_pressure_10(df.open, df.high, df.low, df.close, length=3)
    assert out.name == "RD_WICK_PRESSURE_3"
    assert out.category == "candles"


def test_registered_in_category():
    assert "rd_wick_pressure_10" in ta.Category["candles"]


def test_accessor_matches_module_level():
    df = _frame(n=200, seed=9)
    via_module = rd_wick_pressure_10(df["open"], df["high"], df["low"], df["close"])
    via_accessor = df.ta.rd_wick_pressure_10()
    pd.testing.assert_series_equal(via_module, via_accessor, check_exact=True)
    assert df.ta.rd_wick_pressure_10(length=20).name == "RD_WICK_PRESSURE_20"
