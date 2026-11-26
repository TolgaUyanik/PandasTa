# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.candles.clv_abs` -- mean absolute close location
(14), from issue #200 (Reddit, tier 4: rd:TradingView:1gofmli). Measurements
are in docs/ClvAbsMeasured.md (`python docs/measure_clv_abs.py`).

What these pin, in order of how much it would hurt to lose:

* CORRECTNESS against the issue's own formula (not the screen prototype):
  an independent per-bar loop reference (`_reference`, plain Python floats,
  no pandas rolling) agrees with the module on tick-rounded 2,000-bar
  frames (seeds 1-3, 38-64 zero-range bars each, lengths 5 and 14) --
  measured max abs diff <= 6.66e-16, NaN masks identical -- plus
  hand-derived fixtures (close at the high -> 1, at mid-range -> 0, a mixed
  window). The zero-range NA RULE is pinned by a fixture whose value tells
  apart the three readings (Pine `ta.sma` skipping na -> 0.875,
  propagating na -> NaN, a flat bar as 0 -> 0.625). Round 1 of the review
  replaced round 0's "a flat bar blanks `length` bars", which was a guess.
  The skip-na sentence is quoted from the Pine reference as recalled. It
  was not fetched in this session (see the module docstring).
* CAUSALITY: bars before a perturbation point J are bit-identical whether
  or not the frame's tail is replaced by an unrelated one, with and without
  2% flat bars (the dropna/reindex/ffill path), and a mutant (the `|vp|`
  write shifted one bar earlier, `.shift(-1)`) is live and caught --
  measured: real module leaked at 0 of 293 swept J in both cases, mutant at
  285 of 293.
* SCALE-FREE: x8/x64 bit-identical (0 mismatches on 1,986 cells); x10/x3.7
  within 1e-12 with identical NaN masks (measured max abs diff 1.94e-14 /
  1.79e-14 -- rolling-sum rounding, 1,978 / 1,980 cells differ in the last
  bits).
* Reachability: not constant (0 < fires < n: 1,986 settled and non-zero of
  2,000 bars, 1,928 distinct values, range 0.1224-0.6602 on the seed-4
  frame, counts pinned) and the wiring (`Category`, the accessor, warm-up,
  column name encoding the length).
"""
import importlib
import math
import types

import numpy as np
import pandas as pd
import pytest
from pandas import DataFrame

from .context import pandas_ta as ta

_REAL = importlib.import_module("pandas_ta.candles.clv_abs")
clv_abs = _REAL.clv_abs


# ---------------------------------------------------------------------
# Gate A: independent reference
# ---------------------------------------------------------------------
def _reference(high, low, close, length=14):
    """Per-bar loop straight from the issue's formula, no pandas rolling.

    Round 1 (review of issue #200): the round-0 reference made any NaN inside
    the window give NaN. That was the module's own unverified guess, repeated
    here, so Gate A could not test it. This loop now follows the Pine
    `ta.sma` Remarks sentence quoted in the module docstring ("`na` values in
    the `source` series are ignored; the function calculates on the `length`
    quantity of non-`na` values"): it keeps the non-NaN |vp| values seen so
    far and averages the last `length` of them, so a NaN bar leaves the
    output unchanged."""
    h, l, c = list(high), list(low), list(close)
    seen, out = [], []
    for hi, lo, cl in zip(h, l, c):
        buy, sell = cl - lo, hi - cl
        if buy + sell != 0:
            seen.append(abs((buy - sell) / (buy + sell)))
        out.append(sum(seen[-length:]) / length if len(seen) >= length else math.nan)
    return pd.Series(out, index=high.index)


def _hlc(rows):
    """rows: list of (high, low, close), oldest first."""
    h, l, c = zip(*rows)
    return DataFrame({"high": h, "low": l, "close": c})


def test_close_at_extreme_is_one():
    df = _hlc([(102.0, 98.0, 102.0), (101.0, 99.0, 99.0)] * 2)
    out = clv_abs(df.high, df.low, df.close, length=4)
    assert out.iloc[:3].isna().all()
    assert out.iloc[3] == 1.0


def test_close_at_mid_range_is_zero():
    df = _hlc([(102.0, 98.0, 100.0)] * 4)
    out = clv_abs(df.high, df.low, df.close, length=4)
    assert out.iloc[3] == 0.0


def test_mixed_window_hand_derived():
    # |vp|: close 101 in [98, 102] -> |(3 - 1) / 4| = 0.5; mid -> 0;
    # at low -> 1; close 99 in [98, 102] -> |(1 - 3) / 4| = 0.5. Mean 0.5.
    df = _hlc([(102.0, 98.0, 101.0), (102.0, 98.0, 100.0),
               (102.0, 98.0, 98.0), (102.0, 98.0, 99.0)])
    out = clv_abs(df.high, df.low, df.close, length=4)
    assert out.iloc[3] == 0.5


def test_zero_range_bar_is_skipped_not_propagated_nor_zeroed():
    """Replaces round 0's `test_zero_range_bar_blanks_exactly_length_bars`.
    That test pinned an unverified "na propagates through ta.sma" guess (see
    the module docstring). This fixture's bar 6 decides between the three
    readings: skip na (Pine's ta.sma Remarks) -> 0.875, propagate na -> NaN,
    and treat the flat bar as |vp| = 0 -> 0.625.

    |vp| per bar (length 4): 0.5, 0, 1, 0.5, 1, <flat>, 1."""
    rows = [(102.0, 98.0, 101.0), (102.0, 98.0, 100.0), (102.0, 98.0, 98.0),
            (102.0, 98.0, 99.0), (102.0, 98.0, 102.0), (100.0, 100.0, 100.0),
            (102.0, 98.0, 98.0)]
    df = _hlc(rows)
    out = clv_abs(df.high, df.low, df.close, length=4)
    assert out.iloc[:3].isna().all()
    assert out.iloc[3] == 0.5      # 0.5, 0, 1, 0.5
    assert out.iloc[4] == 0.625    # 0, 1, 0.5, 1
    assert out.iloc[5] == 0.625    # flat bar skipped: same window as bar 4
    assert out.iloc[6] == 0.875    # 1, 0.5, 1, 1 -- the window reaches past the flat bar
    ref = _reference(df.high, df.low, df.close, length=4)
    pd.testing.assert_series_equal(out, ref, check_names=False)


def test_flat_bar_inside_warmup_extends_it():
    """A flat bar during the warm-up delays the first value by one bar: the
    mean needs `length` non-NaN values."""
    rows = [(102.0, 98.0, 101.0), (100.0, 100.0, 100.0)] + [(102.0, 98.0, 101.0)] * 4
    df = _hlc(rows)
    out = clv_abs(df.high, df.low, df.close, length=4)
    assert out.iloc[:4].isna().all()
    assert out.iloc[4] == 0.5


def _frame(n=600, seed=1, tick=0.05, flat=0.02):
    rng = np.random.default_rng(seed)
    close = 50 * np.exp(np.cumsum(rng.normal(0, 0.012, n)))
    openp = close * (1 + rng.normal(0, 0.004, n))
    spread = close * np.abs(rng.normal(0, 0.006, n))
    high = np.maximum(openp, close) + spread
    low = np.minimum(openp, close) - spread
    rd = lambda x: np.round(x / tick) * tick
    openp, high, low, close = rd(openp), rd(high), rd(low), rd(close)
    is_flat = rng.random(n) < flat  # zero-range ties
    high[is_flat] = low[is_flat] = openp[is_flat] = close[is_flat]
    high = np.maximum.reduce([high, openp, close])
    low = np.minimum.reduce([low, openp, close])
    idx = pd.date_range("2020-01-01", periods=n, freq="D")
    return DataFrame({"open": openp, "high": high, "low": low, "close": close},
                     index=idx)


@pytest.mark.parametrize("seed", [1, 2, 3])
@pytest.mark.parametrize("length", [5, 14])
def test_matches_independent_reference(seed, length):
    df = _frame(n=2000, seed=seed)
    out = clv_abs(df.high, df.low, df.close, length=length)
    ref = _reference(df.high, df.low, df.close, length=length)
    assert (out.isna() == ref.isna()).all()
    m = out.notna()
    assert m.sum() > 0
    assert np.max(np.abs(out[m] - ref[m])) < 1e-12


# -------------------------------------------------------------- causality
MUTANT = ("vp_abs = vp.abs()", "vp_abs = vp.abs().shift(-1)")


def _load_mutant():
    src = open(_REAL.__file__, encoding="utf-8").read()
    old, new = MUTANT
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_clv_abs_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


def _sweep(fn, a, b, js):
    """Count J values at which fn's output on [0, J) moves when the frame's
    tail from J on is replaced by frame b's."""
    base = fn(a.high, a.low, a.close)
    leaks = 0
    for j in js:
        spliced = a.copy()
        spliced.iloc[j:] = b.iloc[j:].to_numpy()
        if not base.iloc[:j].equals(fn(spliced.high, spliced.low, spliced.close).iloc[:j]):
            leaks += 1
    return leaks


JS = list(range(10, 596, 2))


@pytest.mark.parametrize("flat", [0.0, 0.02])
def test_real_module_never_reads_the_future(flat):
    """flat=0.02 drives the na-skipping path (dropna -> rolling -> reindex
    -> ffill), which is where a reindex/ffill could leak a later value."""
    a, b = _frame(600, seed=1, flat=flat), _frame(600, seed=2, flat=flat)
    assert _sweep(clv_abs, a, b, JS) == 0


def test_mutant_is_live_and_caught():
    mod = _load_mutant()
    a, b = _frame(600, seed=1, flat=0.0), _frame(600, seed=2, flat=0.0)
    assert not mod.clv_abs(a.high, a.low, a.close).equals(clv_abs(a.high, a.low, a.close))
    leaks = _sweep(mod.clv_abs, a, b, JS)
    assert leaks > 0, f"mutant never leaked across {len(JS)} J values -- test is blind"


# ------------------------------------------------------------ scale-free
@pytest.mark.parametrize("k", [8.0, 64.0])
def test_price_scale_is_bit_identical(k):
    df = _frame(n=2000, seed=4)
    base = clv_abs(df.high, df.low, df.close)
    scaled = clv_abs(df.high * k, df.low * k, df.close * k)
    pd.testing.assert_series_equal(base, scaled, check_exact=True)


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_price_scale_within_tolerance(k):
    df = _frame(n=2000, seed=4)
    base = clv_abs(df.high, df.low, df.close)
    scaled = clv_abs(df.high * k, df.low * k, df.close * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert np.max(np.abs(base[m] - scaled[m])) < 1e-12


def test_scale_fires_and_is_not_constant():
    df = _frame(n=2000, seed=4)
    out = clv_abs(df.high, df.low, df.close).dropna()
    fires = int((out != 0).sum())
    assert 0 < fires
    assert out.nunique() > 1
    assert fires <= len(out) < len(df)


# ------------------------------------------------------------ reachability
def test_reachability_counts():
    """Gate C on the 2,000-bar seed-4 frame (42 zero-range bars): measured
    1,986 settled of 2,000 (the 13-bar warm-up plus one bar because a flat
    bar falls inside it), all 1,986 non-zero, 1,928 distinct, all in
    [0.1224, 0.6602]. Pinned exactly, so they cannot drift from
    docs/ClvAbsMeasured.md without a failure."""
    df = _frame(n=2000, seed=4)
    out = clv_abs(df.high, df.low, df.close)
    settled = out.dropna()
    assert len(settled) == 1986
    assert int((settled != 0).sum()) == 1986
    assert settled.nunique() == 1928
    assert settled.between(0.0, 1.0).all()
    assert out.iloc[:14].isna().all() and out.iloc[14:].notna().all()


# ------------------------------------------------------------- edge cases
def test_short_input_returns_none():
    df = _hlc([(102.0, 98.0, 101.0)] * 3)
    assert clv_abs(df.high, df.low, df.close, length=4) is None


def test_offset():
    df = _frame(n=40, seed=5, flat=0.0)
    out0 = clv_abs(df.high, df.low, df.close)
    out1 = clv_abs(df.high, df.low, df.close, offset=1)
    pd.testing.assert_series_equal(out0.shift(1), out1, check_exact=True)


# ---------------------------------------------------------------- wiring
def test_column_name_and_category():
    df = _frame(n=40, seed=5)
    assert clv_abs(df.high, df.low, df.close).name == "CLVABS_14"
    assert clv_abs(df.high, df.low, df.close, length=5).name == "CLVABS_5"
    assert clv_abs(df.high, df.low, df.close).category == "candles"


def test_warmup_is_length_minus_one():
    df = _frame(n=40, seed=5, flat=0.0)
    out = clv_abs(df.high, df.low, df.close)
    assert out.iloc[:13].isna().all()
    assert out.iloc[13:].notna().all()


def test_registered_in_category():
    assert "clv_abs" in ta.Category["candles"]


def test_accessor_matches_module_level():
    df = _frame(n=60, seed=9)
    via_module = clv_abs(df["high"], df["low"], df["close"], length=5)
    via_accessor = df.ta.clv_abs(length=5)
    pd.testing.assert_series_equal(via_module, via_accessor, check_exact=True)
