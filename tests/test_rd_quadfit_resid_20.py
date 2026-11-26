# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.statistics.rd_quadfit_resid_20` -- the last bar's
residual of a trailing 20-bar quadratic (2nd-order polynomial) fit on log
close, over the window's own residual sd (issue #180, RD-QUADFIT-RESID-20;
Reddit, tier 4, untested by any poster). Measurements are in
docs/RdQuadfitResid20Measured.md. Gate E is owed (run by issue-solver after
this session).

What these pin, in order of how much it would hurt to lose:

* CORRECTNESS against a hand-derived fixture whose exact answer is known
  before the module ever ran (the quadratic design's residual-maker, for
  4 equally spaced points, is the classic orthogonal cubic contrast
  `(-1, 3, -3, 1)`; see `test_hand_derived_value`), plus an independent
  per-window loop built straight from the issue's own formula
  (`np.linalg.lstsq`, not read from the module).
* CAUSALITY by future-splice: bars before a perturbation point J stay
  bit-identical whether or not the frame's tail is an unrelated series, at
  every swept J, and a mutant (the final `pd.Series` construction with a
  `.shift(-1)` appended, reading one bar into the future) is proved live
  and caught at a majority of the same swept J.
* SCALE-FREE: the fitted quadratic has an intercept, so in exact
  (real-number) arithmetic any additive shift of `log(close)` -- i.e. any
  positive price rescale -- leaves every residual, and so the output
  ratio, unchanged. Measured NOT bit-identical under IEEE-754 float64 --
  `np.log` of a power-of-two-rescaled price is not itself bit-preserving
  the way an exact multiply is -- but within the same tiny tolerance
  (relative ~5e-9) for both a power-of-two rescale (x8, x64) and a
  non-power-of-two one (x10, x3.7).
* Reachability (a non-constant output on a random synthetic frame) and the
  wiring (`Category`, the accessor, warm-up, column name).
"""
import importlib
import types

import numpy as np
import pandas as pd
import pytest
from pandas import Series

from .context import pandas_ta as ta

_REAL = importlib.import_module("pandas_ta.statistics.rd_quadfit_resid_20")
rd_quadfit_resid_20 = _REAL.rd_quadfit_resid_20


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


def _oracle(log_close, length):
    """Independent per-window loop, built straight from the issue's own
    formula (OLS fit of a quadratic via `np.linalg.lstsq`), not read from
    the module."""
    n = len(log_close)
    t = np.arange(length, dtype=float)
    X = np.column_stack([np.ones(length), t, t ** 2])
    out = np.full(n, np.nan)
    for end in range(length - 1, n):
        window = log_close[end - length + 1: end + 1]
        if not np.all(np.isfinite(window)):
            continue
        coef, _, _, _ = np.linalg.lstsq(X, window, rcond=None)
        resid = window - X @ coef
        sd = float(resid.std())
        if sd == 0:
            continue
        out[end] = resid[-1] / sd
    return out


# ---------------------------------------------------------------------
# Gate A -- correctness
# ---------------------------------------------------------------------
def test_hand_derived_value():
    """length=4: for 4 equally spaced points, the quadratic design's
    residual-maker is exactly the classic orthogonal CUBIC contrast
    `v = (-1, 3, -3, 1)` (orthogonal to the constant, linear and quadratic
    columns for ANY equally spaced grid -- checked on paper, not run).
    `resid = (v.y / v.v) * v`; chosen y = (0, 1/9, 4/9, 2) gives
    `v.y = -0 + 3/9 - 12/9 + 2 = 1`, `v.v = 20`, so `resid = 0.05 * v`,
    last residual 0.05, population sd of `(-.05, .15, -.15, .05)` is
    `sqrt(0.05**2*4/4)`... -> ratio simplifies exactly to `1/sqrt(5)`,
    computed on paper before the module ever ran."""
    close = _close(np.exp([0.0, 1 / 9, 4 / 9, 2.0]))
    out = rd_quadfit_resid_20(close, length=4)
    assert out.iloc[:3].isna().all()
    assert out.iloc[3] == pytest.approx(1 / np.sqrt(5), abs=1e-9)


def test_matches_an_independent_loop():
    close = _walk(n=300, seed=7)
    length = 40
    out = rd_quadfit_resid_20(close, length=length)
    ref = _oracle(np.log(close.to_numpy(dtype=float)), length)

    assert (np.isnan(ref) == out.isna().values).all()
    m = ~np.isnan(ref)
    np.testing.assert_allclose(out.values[m], ref[m], rtol=1e-9, atol=1e-12)


def test_length_too_small_raises():
    close = _walk(n=50, seed=1)
    with pytest.raises(ValueError):
        rd_quadfit_resid_20(close, length=3)


def test_nonfinite_window_reads_nan():
    """A window holding a NaN close has no well-defined residual, so the
    bar reads NaN rather than an arbitrary fitted value."""
    close = _walk(n=120, seed=3)
    close.iloc[20] = np.nan
    out = rd_quadfit_resid_20(close, length=20)
    # every window covering bar 20 (end in [20, 39]) must be NaN
    assert out.iloc[20:40].isna().all()
    # a window entirely past bar 20 (end >= 40) is defined again
    assert out.iloc[40:].notna().all()


def test_warmup_is_length_minus_one_bars():
    close = _walk(n=200, seed=2)
    out = rd_quadfit_resid_20(close, length=20)
    assert out.iloc[:19].isna().all()
    assert out.iloc[19:].notna().all()


def test_short_input_returns_none():
    close = _walk(n=10, seed=1)
    assert rd_quadfit_resid_20(close, length=20) is None


# ---------------------------------------------------------------------
# Gate B -- causality
# ---------------------------------------------------------------------
def _load_mutant():
    old = "result = pd.Series(out, index=close.index)"
    new = "result = pd.Series(out, index=close.index).shift(-1)"
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_rd_quadfit_resid_20_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


OFFSETS = range(100, 1500, 50)  # 28 offsets, all past the 19-bar warm-up


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
    assert _leaks(rd_quadfit_resid_20, a, b) == 0


def test_lookahead_mutant_is_caught():
    mod = _load_mutant()
    a, b = _walk(1600, seed=1), _walk(1600, seed=2)
    mut = lambda c: mod.rd_quadfit_resid_20(c)  # noqa: E731
    real_out = rd_quadfit_resid_20(a)
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
def test_power_of_two_scale_stays_within_a_tiny_tolerance(k):
    """NOT bit-identical, measured (see module docstring): the fitted
    quadratic has an intercept, so in EXACT arithmetic the residual vector
    of every window is invariant to any additive shift of `log(close)` --
    i.e. any positive price rescale. But unlike a sum-of-squared-deviations
    reduction (`stdev`) or an argmin over a fixed grid (`rd_knot_pos_40`),
    this port runs `np.log` on the RESCALED price itself: `log(8*x)` is not
    bit-identical to `log(x) + log(8)` for IEEE-754 doubles even though `8`
    is an exact power of two (`log` is transcendental, not scale-preserving
    the way an exact power-of-two multiply or a correctly-rounded `sqrt` of
    an exact square is). Measured max relative diff ~5e-9 on this frame
    (docs/measure_rd_quadfit_resid_20.py) -- same order of magnitude as the
    non-power-of-two case below, not meaningfully smaller."""
    close = _walk(seed=4)
    base = rd_quadfit_resid_20(close)
    scaled = rd_quadfit_resid_20(close * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    np.testing.assert_allclose(
        base[m].to_numpy(), scaled[m].to_numpy(), rtol=1e-6, atol=1e-9)


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_other_scales_stay_within_a_tiny_tolerance(k):
    """A non-power-of-two rescale ALSO moves the last bit of `close` before
    `LN` is even called, on top of the same `log`-is-not-scale-preserving
    effect as the power-of-two case above. Measured on this frame in
    docs/measure_rd_quadfit_resid_20.py; bounded here at a generous
    relative tolerance rather than pinned exactly 0, since the CPU's
    dispatched float kernels, not this module's logic, decide the last bit
    (the issue-solver's own CPU-variant rule)."""
    close = _walk(seed=4)
    base = rd_quadfit_resid_20(close)
    scaled = rd_quadfit_resid_20(close * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    np.testing.assert_allclose(
        base[m].to_numpy(), scaled[m].to_numpy(), rtol=1e-6, atol=1e-9)


# ---------------------------------------------------------------------
# Gate C -- reachability
# ---------------------------------------------------------------------
def test_fires_and_is_not_constant():
    close = _walk(seed=4)
    out = rd_quadfit_resid_20(close)
    fired = out.dropna()
    assert 0 < len(fired) < len(out)
    assert fired.nunique() > 1
    # a z-score-like ratio, unbounded, but both signs reachable on noise
    assert fired.min() < 0.0 and fired.max() > 0.0


# ---------------------------------------------------------------------
# wiring
# ---------------------------------------------------------------------
def test_default_length_in_name():
    close = _walk(seed=5)
    out = rd_quadfit_resid_20(close)
    assert out.name == "RD_QUADFIT_RESID_20"


def test_custom_length_in_name():
    close = _walk(seed=5)
    out = rd_quadfit_resid_20(close, length=40)
    assert out.name == "RD_QUADFIT_RESID_40"


def test_offset_shifts_the_series():
    close = _walk(n=200, seed=6)
    base = rd_quadfit_resid_20(close)
    shifted = rd_quadfit_resid_20(close, offset=1)
    pd.testing.assert_series_equal(shifted, base.shift(1), check_names=False)


def test_fillna_fills_the_warmup_nans():
    close = _walk(n=200, seed=6)
    out = rd_quadfit_resid_20(close, fillna=0)
    assert not out.isna().any()
    assert (out.iloc[:19] == 0).all()


def test_column_name_and_category():
    close = _walk(n=60, seed=1)
    out = rd_quadfit_resid_20(close, length=10)
    assert out.name == "RD_QUADFIT_RESID_10"
    assert out.category == "statistics"


def test_registered_in_category():
    assert "rd_quadfit_resid_20" in ta.Category["statistics"]


def test_accessor_matches_module_level():
    close = _walk(n=200, seed=9)
    via_module = rd_quadfit_resid_20(close)
    df = pd.DataFrame({"close": close})
    via_accessor = df.ta.rd_quadfit_resid_20()
    pd.testing.assert_series_equal(via_module, via_accessor, check_exact=True)
    assert df.ta.rd_quadfit_resid_20(length=40).name == "RD_QUADFIT_RESID_40"
