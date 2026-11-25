# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.statistics.rd_gap_fill_rate_60` -- the trailing
share of 0.3%+ overnight gaps whose same bar's high/low touches back to the
prior close (issue #165, RD-GAP-FILL-RATE-60; Reddit, tier 4, untested by
any poster). Measurements are in docs/RdGapFillRate60Measured.md. Gate E is
SHIP (0.2644 vs `ZIGZAG`), recorded in docs/gate_e_ledger.csv.

What these pin, in order of how much it would hurt to lose:

* CORRECTNESS against an independent per-bar loop built straight from the
  issue's own formula (not read from the module), plus a 4-bar hand-derived
  fixture with every input chosen on paper before the module ran.
* CAUSALITY by future-splice: bars before a perturbation point J stay
  bit-identical whether or not the frame's tail is an unrelated series, at
  every one of 28 swept J, and a mutant (the final write shifted one bar
  into the future via `.shift(-1)`) is proved live and caught at 18 of the
  same 28 swept J -- a majority, not every one (a NaN-mask coincidence at
  the splice point can let it slip through at some J), but still far more
  than a rare binary flag like `rd_horseshoe` manages (24 of 293) since this
  is a continuous ratio that changes on almost every bar.
* SCALE-FREE: bit-identical under a power-of-two price rescale (x8, x64),
  since `gap_pct` is a ratio and the comparisons are like-for-like. Under a
  non-power-of-two rescale (x10, x3.7) each operand carries its own
  last-bit rounding, so a `gap_pct` within 1e-15 relative of the 0.3%
  threshold could in principle flip sides -- measured 0 such flips on this
  module's synthetic frame, reported as a tolerance bound, not asserted as
  a mathematical guarantee (unlike the power-of-two case).
* Reachability (both NaN -- no gap in the window -- and a share strictly
  between 0 and 1 occur on a random synthetic frame) and the wiring
  (`Category`, the accessor, warm-up, column name).
"""
import importlib
import types

import numpy as np
import pandas as pd
import pytest
from pandas import DataFrame

from .context import pandas_ta as ta

_REAL = importlib.import_module("pandas_ta.statistics.rd_gap_fill_rate_60")
rd_gap_fill_rate_60 = _REAL.rd_gap_fill_rate_60


# ---------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------
def _ohlc(rows):
    """rows: list of (open, high, low, close) 4-tuples, oldest first."""
    o, h, l, c = zip(*rows)
    return DataFrame({"open": o, "high": h, "low": l, "close": c})


def _hand_rows():
    """length=3, min_gap=0.003.
    bar0: no prior close -> is_gap/filled both False by construction.
    bar1: prev_close=100 (bar0's close); open=100.5 -> gap_pct=+0.005 (gap);
          low=99.8 <= 100 -> filled.
    bar2: prev_close=100.6 (bar1's close); open=99.0 -> gap_pct=-0.0159 (gap);
          high=100.5 < 100.6 -> NOT filled (down-gap needs high >= prev_close).
    bar3: prev_close=99.5 (bar2's close); open=99.6 -> gap_pct=+0.001005,
          |gap_pct| < 0.003 -> not a gap at all.
    """
    return [
        (100.0, 101.0, 99.0, 100.0),   # bar0
        (100.5, 100.9, 99.8, 100.6),   # bar1: gap, filled
        (99.0, 100.5, 98.5, 99.5),     # bar2: gap, not filled
        (99.6, 100.0, 99.0, 99.8),     # bar3: no gap
    ]


def test_hand_derived_value():
    df = _ohlc(_hand_rows())
    out = rd_gap_fill_rate_60(df.open, df.high, df.low, df.close, length=3)
    assert out.iloc[:2].isna().all()
    # window [0,1,2]: is_gap count 2 (bar1, bar2), filled count 1 (bar1 only)
    assert out.iloc[2] == pytest.approx(0.5, abs=1e-12)
    # window [1,2,3]: is_gap count 2 (bar1, bar2), filled count 1 (bar1 only)
    assert out.iloc[3] == pytest.approx(0.5, abs=1e-12)


def test_no_gap_in_window_reads_nan():
    """Every bar's open equals the prior close exactly -- no gap ever, so
    the window holds 0 gaps and the ratio is NaN (0/0), not 0."""
    close = [100.0, 100.0, 100.0, 100.0, 100.0]
    rows = [(c, c + 1.0, c - 1.0, c) for c in close]
    df = _ohlc(rows)
    out = rd_gap_fill_rate_60(df.open, df.high, df.low, df.close, length=3)
    assert out.iloc[2:].isna().all()


def _frame(n=1600, seed=11):
    """Synthetic OHLC with explicit overnight gaps (std ~0.6%, so many
    cross the 0.3% threshold and many do not) and an intraday range wide
    enough that some gaps fill and some do not."""
    rng = np.random.default_rng(seed)
    ret = rng.normal(0.0, 0.01, n)
    close = 100.0 * np.exp(np.cumsum(ret))
    gap = rng.normal(0.0, 0.006, n)
    openp = np.empty(n)
    openp[0] = close[0]
    openp[1:] = close[:-1] * (1.0 + gap[1:])
    spread = np.abs(rng.normal(0.0, 0.004, n)) * close
    high = np.maximum(openp, close) + spread
    low = np.minimum(openp, close) - spread
    idx = pd.date_range("2020-01-01", periods=n, freq="D")
    return DataFrame({"open": openp, "high": high, "low": low, "close": close},
                      index=idx)


def test_matches_an_independent_loop():
    df = _frame()
    length, min_gap = 60, 0.003
    out = rd_gap_fill_rate_60(df.open, df.high, df.low, df.close, length=length)

    o, h, l, c = (df[k].to_numpy(dtype=float) for k in ("open", "high", "low", "close"))
    n = len(c)
    is_gap = np.zeros(n, dtype=bool)
    filled = np.zeros(n, dtype=bool)
    for t in range(1, n):
        gap_pct = o[t] / c[t - 1] - 1.0
        is_gap[t] = abs(gap_pct) >= min_gap
        if gap_pct >= min_gap:
            filled[t] = l[t] <= c[t - 1]
        elif gap_pct <= -min_gap:
            filled[t] = h[t] >= c[t - 1]

    ref = np.full(n, np.nan)
    for t in range(length - 1, n):
        window = slice(t - length + 1, t + 1)
        gaps = int(is_gap[window].sum())
        if gaps > 0:
            ref[t] = filled[window].sum() / gaps

    assert (np.isnan(ref) == out.isna().values).all()
    m = ~np.isnan(ref)
    np.testing.assert_allclose(out.values[m], ref[m], rtol=1e-12)


def test_warmup_is_length_minus_one_bars():
    df = _frame(200)
    out = rd_gap_fill_rate_60(df.open, df.high, df.low, df.close, length=10)
    assert out.iloc[:9].isna().all()


def test_default_length_and_min_gap_in_name():
    df = _frame()
    out = rd_gap_fill_rate_60(df.open, df.high, df.low, df.close)
    assert out.name == "RD_GAP_FILL_RATE_60_0.3"


def test_custom_length_and_min_gap_in_name():
    df = _frame()
    out = rd_gap_fill_rate_60(df.open, df.high, df.low, df.close, length=20, min_gap=0.01)
    assert out.name == "RD_GAP_FILL_RATE_20_1"


def test_offset_shifts_the_series():
    df = _frame(200)
    base = rd_gap_fill_rate_60(df.open, df.high, df.low, df.close)
    shifted = rd_gap_fill_rate_60(df.open, df.high, df.low, df.close, offset=1)
    pd.testing.assert_series_equal(shifted, base.shift(1), check_names=False)


def test_fillna_fills_the_warmup_nans():
    df = _frame(200)
    out = rd_gap_fill_rate_60(df.open, df.high, df.low, df.close, fillna=0)
    assert not out.isna().any()
    assert (out.iloc[:59] == 0).all()


def test_short_input_returns_none():
    df = _ohlc(_hand_rows()[:2])
    assert rd_gap_fill_rate_60(df.open, df.high, df.low, df.close, length=60) is None


# -------------------------------------------------------------- causality
def _load_mutant():
    old = "rate = rate.where(gap_count > 0)"
    new = "rate = rate.where(gap_count > 0).shift(-1)"
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_rd_gap_fill_rate_60_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


OFFSETS = range(100, 1500, 50)  # 28 offsets, all past the 59-bar warm-up


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
    assert _leaks(rd_gap_fill_rate_60, a, b) == 0


def test_lookahead_mutant_is_caught():
    mod = _load_mutant()
    a, b = _frame(1600, seed=1), _frame(1600, seed=2)
    mut = lambda o, h, l, c: mod.rd_gap_fill_rate_60(o, h, l, c)  # noqa: E731
    real_out = rd_gap_fill_rate_60(a.open, a.high, a.low, a.close)
    mut_out = mut(a.open, a.high, a.low, a.close)
    assert not mut_out.equals(real_out)  # live

    hits = _leaks(mut, a, b)
    # measured 18 of 28 (docs/measure_rd_gap_fill_rate_60.py) -- pinned as a
    # bound (>half), not a bit-level count: a NaN-mask equality lucky escape
    # at the remaining J is CPU-independent (it depends on this frame's
    # structure, not on float rounding), so the exact count is stable, but
    # the structural claim ("caught at most of the swept J") is what matters.
    assert hits >= len(OFFSETS) // 2, f"mutant caught at only {hits} of {len(OFFSETS)} J"


# ------------------------------------------------------------ scale-free
@pytest.mark.parametrize("k", [8.0, 64.0])
def test_power_of_two_scale_is_bit_identical(k):
    """gap_pct is a ratio, and the comparisons are like-for-like price
    terms, so a power-of-two rescale is an exact exponent shift on every
    operand -- the correctly-rounded division and every comparison's truth
    value cannot move."""
    df = _frame(seed=4)
    base = rd_gap_fill_rate_60(df.open, df.high, df.low, df.close)
    scaled = rd_gap_fill_rate_60(df.open * k, df.high * k, df.low * k, df.close * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_other_scales_stay_within_a_tiny_tolerance(k):
    """Not provably bit-exact (see module docstring): each scaled operand
    carries its own last-bit rounding, so an isolated gap_pct within 1e-15
    relative of the 0.3% threshold could flip sides. Measured 0 such flips
    on this frame (docs/measure_rd_gap_fill_rate_60.py); bounded here at a
    generous 1% of valid bars rather than pinned at exactly 0, since the
    CPU's dispatched float kernels (not this module's logic) decide the
    last bit, and the issue-solver's own rules forbid pinning an exact
    bit-level count across CPU variants."""
    df = _frame(seed=4)
    base = rd_gap_fill_rate_60(df.open, df.high, df.low, df.close)
    scaled = rd_gap_fill_rate_60(df.open * k, df.high * k, df.low * k, df.close * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    mismatches = int((base[m] != scaled[m]).sum())
    assert mismatches <= max(1, int(0.01 * int(m.sum())))


# ------------------------------------------------------------ reachability
def test_fires_and_is_not_constant():
    df = _frame(seed=4)
    out = rd_gap_fill_rate_60(df.open, df.high, df.low, df.close)
    fired = out.dropna()
    assert 0 < len(fired) < len(out)
    assert fired.nunique() > 1
    assert ((fired >= 0.0) & (fired <= 1.0)).all()
    assert fired.min() < 1.0 and fired.max() > 0.0


# ---------------------------------------------------------------- wiring
def test_column_name_and_category():
    df = _ohlc(_hand_rows())
    out = rd_gap_fill_rate_60(df.open, df.high, df.low, df.close, length=3)
    assert out.name == "RD_GAP_FILL_RATE_3_0.3"
    assert out.category == "statistics"


def test_registered_in_category():
    assert "rd_gap_fill_rate_60" in ta.Category["statistics"]


def test_accessor_matches_module_level():
    df = _frame(n=200, seed=9)
    via_module = rd_gap_fill_rate_60(df["open"], df["high"], df["low"], df["close"])
    via_accessor = df.ta.rd_gap_fill_rate_60()
    pd.testing.assert_series_equal(via_module, via_accessor, check_exact=True)
    assert df.ta.rd_gap_fill_rate_60(length=20, min_gap=0.01).name == "RD_GAP_FILL_RATE_20_1"
