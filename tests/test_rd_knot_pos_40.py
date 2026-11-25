# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.statistics.rd_knot_pos_40` -- the normalised age of
the lowest-MSE one-knot continuous spline break over a trailing 40-bar
window of log close (issue #166, RD-KNOT-POS-40; Reddit, tier 4, untested
by any poster). Measurements are in docs/RdKnotPos40Measured.md. Gate E is
pending, run by issue-solver after this session.

What these pin, in order of how much it would hurt to lose:

* CORRECTNESS against an independent per-window loop built straight from
  the issue's own formula (not read from the module): for every candidate
  knot, fit the continuous hinge model by `np.linalg.lstsq` and keep the
  argmin-SSE knot, plus a noiseless hand-derived fixture whose true break
  point is known before the module ever ran.
* CAUSALITY by future-splice: bars before a perturbation point J stay
  bit-identical whether or not the frame's tail is an unrelated series, at
  every swept J, and a mutant (the final `pd.Series` construction with a
  `.shift(-1)` appended, reading one bar into the future) is proved live
  and caught at a majority of the same swept J.
* SCALE-FREE: the fitted hinge model has an intercept, so in exact
  arithmetic any additive shift of `log(close)` -- i.e. any positive price
  rescale -- leaves every knot's SSE, and so the argmin knot, unchanged.
  Measured bit-identical under a power-of-two price rescale (x8, x64), and
  within a tiny tolerance under a non-power-of-two one (x10, x3.7).
* Reachability (a non-constant, in-range output on a random synthetic
  frame) and the wiring (`Category`, the accessor, warm-up, column name).
"""
import importlib
import types

import numpy as np
import pandas as pd
import pytest
from pandas import Series

from .context import pandas_ta as ta

_REAL = importlib.import_module("pandas_ta.statistics.rd_knot_pos_40")
rd_knot_pos_40 = _REAL.rd_knot_pos_40


# ---------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------
def _close(values, start="2020-01-01"):
    idx = pd.date_range(start, periods=len(values), freq="D")
    return Series(values, index=idx, dtype=float)


def _walk(n=1600, seed=11, start=100.0, mu=0.0, sigma=0.01):
    rng = np.random.default_rng(seed)
    ret = rng.normal(mu, sigma, n)
    return _close(start * np.exp(np.cumsum(ret)))


def _oracle(log_close, length, knot_margin):
    """Independent per-window loop, built straight from the issue's own
    formula (OLS fit of a continuous one-knot hinge model via
    `np.linalg.lstsq`), not read from the module."""
    n = len(log_close)
    t = np.arange(length, dtype=float)
    knots = np.arange(knot_margin, length - knot_margin)
    out = np.full(n, np.nan)
    for end in range(length - 1, n):
        window = log_close[end - length + 1: end + 1]
        if not np.all(np.isfinite(window)):
            continue
        sse = np.empty(len(knots))
        for i, k in enumerate(knots):
            X = np.column_stack([np.ones(length), t, np.maximum(t - k, 0.0)])
            coef, _, _, _ = np.linalg.lstsq(X, window, rcond=None)
            resid = window - X @ coef
            sse[i] = float(np.dot(resid, resid))
        best = knots[int(np.argmin(sse))]
        out[end] = (length - 1 - best) / (length - 1)
    return out


# ---------------------------------------------------------------------
# Gate A -- correctness
# ---------------------------------------------------------------------
def test_hand_derived_value():
    """Noiseless piecewise-linear log price: slope 1 up to t=5, slope 3
    after, an EXACT continuous hinge with knot=5 -- chosen on paper before
    the module ran. At length=10, knot_margin=2 (candidates 2..7), the
    knot=5 model reproduces the data with (near) zero residual, far below
    every other candidate's, so the argmin is unambiguous."""
    t = np.arange(10, dtype=float)
    y = np.where(t <= 5, t, 5 + 3 * (t - 5))
    close = _close(np.exp(y))
    out = rd_knot_pos_40(close, length=10, knot_margin=2)
    assert out.iloc[:9].isna().all()
    # age = (length - 1 - best) / (length - 1) = (9 - 5) / 9
    assert out.iloc[9] == pytest.approx(4 / 9, abs=1e-9)


def test_matches_an_independent_loop():
    close = _walk(n=300, seed=7)
    length, knot_margin = 40, 5
    out = rd_knot_pos_40(close, length=length, knot_margin=knot_margin)
    ref = _oracle(np.log(close.to_numpy(dtype=float)), length, knot_margin)

    assert (np.isnan(ref) == out.isna().values).all()
    m = ~np.isnan(ref)
    np.testing.assert_allclose(out.values[m], ref[m], rtol=1e-9, atol=1e-12)


def test_knot_margin_too_large_raises():
    close = _walk(n=50, seed=1)
    with pytest.raises(ValueError):
        rd_knot_pos_40(close, length=10, knot_margin=5)


def test_nonfinite_window_reads_nan():
    """A window holding a NaN close has no well-defined argmin, so the bar
    reads NaN rather than an arbitrary knot's age."""
    close = _walk(n=120, seed=3)
    close.iloc[20] = np.nan
    out = rd_knot_pos_40(close, length=40, knot_margin=5)
    # every window covering bar 20 (bars whose 40-bar trailing window
    # includes index 20, i.e. end in [20, 59]) must be NaN
    assert out.iloc[20:60].isna().all()
    # a window entirely past bar 20 (end >= 60) is defined again
    assert out.iloc[60:].notna().all()


def test_warmup_is_length_minus_one_bars():
    close = _walk(n=200, seed=2)
    out = rd_knot_pos_40(close, length=20, knot_margin=3)
    assert out.iloc[:19].isna().all()
    assert out.iloc[19:].notna().all()


def test_short_input_returns_none():
    close = _walk(n=30, seed=1)
    assert rd_knot_pos_40(close, length=40) is None


# ---------------------------------------------------------------------
# Gate B -- causality
# ---------------------------------------------------------------------
def _load_mutant():
    old = "result = pd.Series(out, index=close.index)"
    new = "result = pd.Series(out, index=close.index).shift(-1)"
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_rd_knot_pos_40_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


OFFSETS = range(100, 1500, 50)  # 28 offsets, all past the 39-bar warm-up


def _leaks(fn, base_series, other_series):
    base = fn(base_series)
    hits = 0
    for j in OFFSETS:
        spliced = base_series.copy()
        spliced.iloc[j:] = other_series.iloc[j:].to_numpy()
        out = fn(spliced)
        a, b = base.iloc[:j], out.iloc[:j]
        if not (a.isna() == b.isna()).all():
            hits += 1
            continue
        m = a.notna()
        if (a[m] != b[m]).any():
            hits += 1
    return hits


def test_real_module_never_reads_the_future():
    a, b = _walk(1600, seed=1), _walk(1600, seed=2)
    assert _leaks(rd_knot_pos_40, a, b) == 0


def test_lookahead_mutant_is_caught():
    mod = _load_mutant()
    a, b = _walk(1600, seed=1), _walk(1600, seed=2)
    mut = lambda c: mod.rd_knot_pos_40(c)  # noqa: E731
    real_out = rd_knot_pos_40(a)
    mut_out = mut(a)
    assert not mut_out.equals(real_out)  # live

    hits = _leaks(mut, a, b)
    # A continuous value that changes on almost every bar, so the mutant is
    # caught at a majority of swept J, not merely "some" -- pinned as a
    # bound, not a bit-level count the CPU's dispatched kernels could move.
    assert hits >= len(OFFSETS) // 2, f"mutant caught at only {hits} of {len(OFFSETS)} J"


# ---------------------------------------------------------------------
# Gate D -- scale-free
# ---------------------------------------------------------------------
@pytest.mark.parametrize("k", [8.0, 64.0])
def test_power_of_two_scale_is_bit_identical(k):
    """The fitted model has an intercept, so in exact arithmetic the SSE of
    every knot is invariant to any additive shift of log(close) -- i.e. any
    positive price rescale. Measured bit-identical under a power-of-two
    rescale (see module docstring for the float-precision argument)."""
    close = _walk(seed=4)
    base = rd_knot_pos_40(close)
    scaled = rd_knot_pos_40(close * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_other_scales_stay_within_a_tiny_tolerance(k):
    """Not provably bit-exact (see module docstring): a non-power-of-two
    rescale moves the LAST BIT of `close` before LN is even called, which
    can in principle flip an already-close argmin between two knots.
    Measured 0 such flips on this frame (docs/measure_rd_knot_pos_40.py);
    bounded here at a generous 1% of valid bars rather than pinned exactly
    0, since the CPU's dispatched float kernels, not this module's logic,
    decide the last bit (the issue-solver's own CPU-variant rule)."""
    close = _walk(seed=4)
    base = rd_knot_pos_40(close)
    scaled = rd_knot_pos_40(close * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    mismatches = int((base[m] != scaled[m]).sum())
    assert mismatches <= max(1, int(0.01 * int(m.sum())))


# ---------------------------------------------------------------------
# Gate C -- reachability
# ---------------------------------------------------------------------
def test_fires_and_is_not_constant():
    close = _walk(seed=4)
    out = rd_knot_pos_40(close)
    fired = out.dropna()
    assert 0 < len(fired) < len(out)
    assert fired.nunique() > 1
    assert ((fired >= 0.0) & (fired <= 1.0)).all()
    assert fired.min() < 1.0 and fired.max() > 0.0


# ---------------------------------------------------------------------
# wiring
# ---------------------------------------------------------------------
def test_default_length_and_knot_margin_in_name():
    close = _walk(seed=5)
    out = rd_knot_pos_40(close)
    assert out.name == "RD_KNOT_POS_40_5"


def test_custom_length_and_knot_margin_in_name():
    close = _walk(seed=5)
    out = rd_knot_pos_40(close, length=20, knot_margin=3)
    assert out.name == "RD_KNOT_POS_20_3"


def test_offset_shifts_the_series():
    close = _walk(n=200, seed=6)
    base = rd_knot_pos_40(close)
    shifted = rd_knot_pos_40(close, offset=1)
    pd.testing.assert_series_equal(shifted, base.shift(1), check_names=False)


def test_fillna_fills_the_warmup_nans():
    close = _walk(n=200, seed=6)
    out = rd_knot_pos_40(close, fillna=0)
    assert not out.isna().any()
    assert (out.iloc[:39] == 0).all()


def test_column_name_and_category():
    close = _walk(n=60, seed=1)
    out = rd_knot_pos_40(close, length=10, knot_margin=2)
    assert out.name == "RD_KNOT_POS_10_2"
    assert out.category == "statistics"


def test_registered_in_category():
    assert "rd_knot_pos_40" in ta.Category["statistics"]


def test_accessor_matches_module_level():
    close = _walk(n=200, seed=9)
    via_module = rd_knot_pos_40(close)
    df = pd.DataFrame({"close": close})
    via_accessor = df.ta.rd_knot_pos_40()
    pd.testing.assert_series_equal(via_module, via_accessor, check_exact=True)
    assert df.ta.rd_knot_pos_40(length=20, knot_margin=3).name == "RD_KNOT_POS_20_3"
