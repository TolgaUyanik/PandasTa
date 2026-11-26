# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.candles.rd_gap_fill` -- the same-day gap fill,
signed, from issue #174 (RD-GAP-FILL; Reddit, tier 4, untested by any
poster). Measurements are in docs/RdGapFillMeasured.md.

What these pin, in order of how much it would hurt to lose:

* CORRECTNESS against an independent per-bar reading of the issue's own
  formula (not read from the module), on a 5-bar hand-derived fixture
  chosen on paper before the module ran -- one filled up-gap, one unfilled
  down-gap, one bar below the 0.3% threshold (no gap at all) and one filled
  down-gap, so every branch of the three-way sign fires at least once --
  plus a boundary fixture (`gap_pct` exactly `== min_gap`, proving the
  issue's inclusive `>=` is read that way) and a same-bar check that
  `min_gap` actually gates the comparisons, not merely the column name.
* CAUSALITY by future-splice: bars before a perturbation point J stay
  bit-identical whether or not the frame's tail is an unrelated series, at
  every one of 28 swept J, and a mutant (the final write shifted one bar
  into the future via `.shift(-1)`) is proved live and caught at 9 of the
  same 28 swept J -- a discrete {-1, 0, 1} flag that is non-zero on a
  minority of bars (so most J fall on a settled-zero stretch where the
  mutant's one-bar back-date has nothing to move), not every J, the same
  low-power pattern `rd_horseshoe`'s own test documents (caught at 24 of
  293 there).
* SCALE-FREE: bit-identical under a power-of-two price rescale (x8, x64),
  since `gap_pct` is a ratio and the fill comparisons are like-for-like.
  Under a non-power-of-two rescale (x10, x3.7) each operand carries its own
  last-bit rounding, so a `gap_pct` within ~1e-15 relative of the 0.3%
  threshold could in principle flip sides -- measured 0 such flips on this
  module's synthetic frame, reported as a tolerance bound, not asserted as
  a mathematical guarantee the way the power-of-two case is.
* Reachability (both +1 and -1 fire on a random synthetic frame, not a
  constant column) and the wiring (`Category`, the accessor, warm-up,
  column name).
"""
import importlib
import types

import numpy as np
import pandas as pd
import pytest
from pandas import DataFrame

from .context import pandas_ta as ta

_REAL = importlib.import_module("pandas_ta.candles.rd_gap_fill")
rd_gap_fill = _REAL.rd_gap_fill


# ---------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------
def _ohlc(rows):
    """rows: list of (open, high, low, close) 4-tuples, oldest first."""
    o, h, l, c = zip(*rows)
    return DataFrame({"open": o, "high": h, "low": l, "close": c})


def _hand_rows():
    """min_gap=0.003 (default).
    bar0: no prior close -> output NaN by construction.
    bar1: prev_close=100 (bar0's close); open=100.5 -> gap_pct=+0.005 (gap
          up); low=99.8 <= 100 -> filled -> +1.
    bar2: prev_close=100.6 (bar1's close); open=99.0 -> gap_pct=-0.0159
          (gap down); high=100.5 < 100.6 -> NOT filled (down-gap needs
          high >= prev_close) -> 0.
    bar3: prev_close=99.5 (bar2's close); open=99.6 -> gap_pct=+0.001005,
          |gap_pct| < 0.003 -> not a gap at all -> 0.
    bar4: prev_close=99.8 (bar3's close); open=98.5 -> gap_pct=-0.01303
          (gap down); high=99.9 >= 99.8 -> filled -> -1.
    """
    return [
        (100.0, 101.0, 99.0, 100.0),   # bar0
        (100.5, 100.9, 99.8, 100.6),   # bar1: gap up, filled -> +1
        (99.0, 100.5, 98.5, 99.5),     # bar2: gap down, not filled -> 0
        (99.6, 100.0, 99.0, 99.8),     # bar3: no gap -> 0
        (98.5, 99.9, 98.0, 98.7),      # bar4: gap down, filled -> -1
    ]


def test_hand_derived_values():
    df = _ohlc(_hand_rows())
    out = rd_gap_fill(df.open, df.high, df.low, df.close)
    assert pd.isna(out.iloc[0])
    expected = [1.0, 0.0, 0.0, -1.0]
    assert out.iloc[1:].tolist() == expected


def test_no_gap_ever_reads_zero_not_nan():
    """Every bar's open equals the prior close exactly -- no gap ever, so
    every settled bar reads 0.0 (no gap => not filled up, not filled
    down), never NaN beyond the first bar."""
    close = [100.0, 100.0, 100.0, 100.0, 100.0]
    rows = [(c, c + 1.0, c - 1.0, c) for c in close]
    df = _ohlc(rows)
    out = rd_gap_fill(df.open, df.high, df.low, df.close)
    assert pd.isna(out.iloc[0])
    assert (out.iloc[1:] == 0.0).all()


def test_warmup_is_exactly_one_bar():
    df = _ohlc(_hand_rows())
    out = rd_gap_fill(df.open, df.high, df.low, df.close)
    assert pd.isna(out.iloc[0])
    assert out.iloc[1:].notna().all()


def test_gap_exactly_at_threshold_counts_as_a_gap():
    """gap_pct == min_gap exactly must fire: the issue's own '|gap| >=
    0.3%' is inclusive, and the code's `>=`/`<=` comparisons must actually
    be read that way, not `>`/`<`. Uses min_gap=0.25 and open/prev_close =
    125.0/100.0 = 1.25 -- both binary-exact fractions (2^-2, 5/4) -- so
    `gap_pct` lands on `min_gap` bit-for-bit, not merely close to it; a
    decimal threshold like the issue's native 0.3% cannot be hit exactly
    in binary floating point, so this isolates the inclusive-comparison
    claim from any float-rounding question."""
    rows = [
        (100.0, 101.0, 99.0, 100.0),     # bar0
        (125.0, 130.0, 99.0, 126.0),     # bar1: gap_pct = 125.0/100.0-1 = 0.25 exactly, filled (low 99.0 <= 100.0)
    ]
    df = _ohlc(rows)
    out = rd_gap_fill(df.open, df.high, df.low, df.close, min_gap=0.25)
    assert out.iloc[1] == 1.0


def test_min_gap_parameter_actually_changes_firing():
    """A 0.5% gap must fire at the default min_gap (0.3%) but read 0 at a
    stricter min_gap (1%) -- proves `min_gap` gates the comparisons, not
    merely the column name."""
    rows = [
        (100.0, 101.0, 99.0, 100.0),    # bar0
        (100.5, 100.9, 99.8, 100.6),    # bar1: gap_pct = +0.5%, filled
    ]
    df = _ohlc(rows)
    loose = rd_gap_fill(df.open, df.high, df.low, df.close, min_gap=0.003)
    strict = rd_gap_fill(df.open, df.high, df.low, df.close, min_gap=0.01)
    assert loose.iloc[1] == 1.0
    assert strict.iloc[1] == 0.0


def test_default_min_gap_in_name():
    df = _ohlc(_hand_rows())
    out = rd_gap_fill(df.open, df.high, df.low, df.close)
    assert out.name == "RD_GAP_FILL_0.3"


def test_custom_min_gap_in_name():
    df = _ohlc(_hand_rows())
    out = rd_gap_fill(df.open, df.high, df.low, df.close, min_gap=0.01)
    assert out.name == "RD_GAP_FILL_1"


def test_offset_shifts_the_series():
    df = _ohlc(_hand_rows())
    base = rd_gap_fill(df.open, df.high, df.low, df.close)
    shifted = rd_gap_fill(df.open, df.high, df.low, df.close, offset=1)
    pd.testing.assert_series_equal(shifted, base.shift(1), check_names=False)


def test_fillna_fills_the_warmup_nan():
    df = _ohlc(_hand_rows())
    out = rd_gap_fill(df.open, df.high, df.low, df.close, fillna=0)
    assert not out.isna().any()
    assert out.iloc[0] == 0


def test_short_input_returns_none():
    df = _ohlc(_hand_rows()[:1])
    assert rd_gap_fill(df.open, df.high, df.low, df.close) is None


# ---------------------------------------------------------------------
# random frames (causality, scale, reachability)
# ---------------------------------------------------------------------
def _frame(n=1600, seed=11):
    """Synthetic OHLC with explicit overnight gaps (std ~0.6%, so many
    cross the 0.3% threshold and many do not, in both directions) and an
    intraday range wide enough that some gaps fill and some do not."""
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


# -------------------------------------------------------------- causality
def _load_mutant():
    old = "gap_fill = gap_fill.where(prev_close.notna())"
    new = "gap_fill = gap_fill.where(prev_close.notna()).shift(-1)"
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_rd_gap_fill_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


OFFSETS = range(100, 1500, 50)  # 28 offsets, all past the 1-bar warm-up


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
    assert _leaks(rd_gap_fill, a, b) == 0


def test_lookahead_mutant_is_caught():
    mod = _load_mutant()
    a, b = _frame(1600, seed=1), _frame(1600, seed=2)
    mut = lambda o, h, l, c: mod.rd_gap_fill(o, h, l, c)  # noqa: E731
    real_out = rd_gap_fill(a.open, a.high, a.low, a.close)
    mut_out = mut(a.open, a.high, a.low, a.close)
    assert not mut_out.equals(real_out)  # live

    hits = _leaks(mut, a, b)
    # measured 9 of 28 on this frame pair (docs/measure_rd_gap_fill.py,
    # docs/RdGapFillMeasured.md) -- pinned as "some, not none" rather than
    # an exact count, since a sparse {-1,0,1} flag can coincide with the
    # unperturbed frame at a varying number of J depending on the seed; the
    # structural claim is that the real module never leaks (above) while
    # the live mutant does leak at a non-trivial share of J.
    assert hits > 0, "mutant never leaked across any swept J -- test is blind"
    assert hits >= 5, f"mutant caught at only {hits} of {len(OFFSETS)} J, weaker than measured"


# ------------------------------------------------------------ scale-free
@pytest.mark.parametrize("k", [8.0, 64.0])
def test_power_of_two_scale_is_bit_identical(k):
    """gap_pct is a ratio, and both fill comparisons are like-for-like
    price terms, so a power-of-two rescale is an exact exponent shift on
    every operand -- the correctly-rounded division and every comparison's
    truth value cannot move."""
    df = _frame(seed=4)
    base = rd_gap_fill(df.open, df.high, df.low, df.close)
    scaled = rd_gap_fill(df.open * k, df.high * k, df.low * k, df.close * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_other_scales_stay_within_a_tiny_tolerance(k):
    """Not provably bit-exact (see module docstring): each scaled operand
    carries its own last-bit rounding, so an isolated gap_pct within 1e-15
    relative of the 0.3% threshold could flip sides. Measured 0 such flips
    on this frame (docs/measure_rd_gap_fill.py); bounded here at a generous
    1% of valid bars rather than pinned at exactly 0, since the CPU's
    dispatched float kernels, not this module's logic, decide the last bit
    (the issue-solver's own CPU-variant rule forbids pinning an exact
    bit-level count across CPU variants)."""
    df = _frame(seed=4)
    base = rd_gap_fill(df.open, df.high, df.low, df.close)
    scaled = rd_gap_fill(df.open * k, df.high * k, df.low * k, df.close * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    mismatches = int((base[m] != scaled[m]).sum())
    assert mismatches <= max(1, int(0.01 * int(m.sum())))


# ------------------------------------------------------------ reachability
def test_fires_both_signs_and_is_not_constant():
    df = _frame(seed=4)
    out = rd_gap_fill(df.open, df.high, df.low, df.close)
    fired = out.dropna()
    assert len(fired) == len(out) - 1  # settled on every bar but bar 0
    assert (fired != 0.0).sum() > 0
    assert (fired != 0.0).sum() < len(fired)
    assert 1.0 in fired.values
    assert -1.0 in fired.values


# ---------------------------------------------------------------- wiring
def test_column_name_and_category():
    df = _ohlc(_hand_rows())
    out = rd_gap_fill(df.open, df.high, df.low, df.close)
    assert out.name == "RD_GAP_FILL_0.3"
    assert out.category == "candles"


def test_registered_in_category():
    assert "rd_gap_fill" in ta.Category["candles"]


def test_accessor_matches_module_level():
    df = _frame(n=200, seed=9)
    via_module = rd_gap_fill(df["open"], df["high"], df["low"], df["close"])
    via_accessor = df.ta.rd_gap_fill()
    pd.testing.assert_series_equal(via_module, via_accessor, check_exact=True)
    assert df.ta.rd_gap_fill(min_gap=0.01).name == "RD_GAP_FILL_1"
