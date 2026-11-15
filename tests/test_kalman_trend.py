# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.overlap.kalman_trend` -- a two-state (level,
velocity) local-linear-trend Kalman filter on ln(close / first positive
close).  Measurements and the deferred Gate E are in
`docs/KalmanTrendMeasured.md`; every number quoted here is printed by
`docs/measure_kalman_trend_proxy.py`.

⚠ READ THIS FIRST.  The noise variances are FIXED parameters.  Fitting them
by maximum likelihood on the whole series would be a look-ahead, and with
fixed variances the gain converges to a data-independent constant, so after
the warm-up this is a fixed linear filter on log price (Holt-like).  That is
why the proxy overlap is high (VEL vs PPO_12_26_9 rho 0.8992) and why Gate E
decides whether either column survives.

What these tests pin, in order of how much it would hurt to lose them:

* CAUSALITY by future-perturbation: rewrite every bar from `j` onward,
  demand bars `[0:j]` bit-identical, over 32 offsets past the warm-up.
  Four look-ahead mutants (`importlib` source read, `exec`'d in memory) are
  each proved live, then caught at 32 of 32: the observation read one bar
  ahead, the DIST and VEL writes back-dated one bar, and -- the failure the
  task flagged 🔴 -- the slope noise "fitted" on the whole series' variance.
  NaN masks are compared before values, because a bare `!=` on NaN passes
  a null mutant.
* The HEAD, not only the tail (the Hilbert lesson in CLAUDE.md): starting
  the filter at bar s instead of bar 0 must agree with the full run to
  1e-6 from the FIRST emitted bar on (measured worst 4.0e-7 / 2.5e-7 /
  1.5e-7), over 90 runs, at three parameter pairs, not just the defaults
  (warm-ups 213 / 147 / 174).  And the warm-up is not padding: emitting
  from half of it leaves a start-dependent error above 1e-3 (measured
  1.6e-3).  A q_slope too small for the Riccati recursion to converge
  raises rather than silently under-masking the head.
* The warm-up counts UPDATES, not bars: NaNs inside the head push the
  first emitted bar later by exactly their number.
* SCALE-FREE: bit-identical under x8 and x64 (y is the log of a ratio,
  exact under a power of two), within 1e-9 (measured 2.8e-14) under x10 and x3.7 with matching
  NaN masks, and `0 < fires < n` per column.
* CORRECTNESS against an independent matrix-form filter (F, H, Q, R, P
  written from the textbook equations, not from the module), including a
  NaN close and a zero close (predict-only bars), and a log-linear series
  reads DIST -> 0 and VEL -> the per-bar log-percent step.
* Bad input: a zero close does not poison the series, leading NaNs only
  shift the output, an all-NaN series returns None, and negative or
  non-finite q_* raise instead of falling back to default-named columns.
* Wiring: `Category`, the accessor, and the column names (`.12g`, so
  parameters differing past 6 digits do not collide).
"""
import importlib
import types

import numpy as np
import pandas as pd
import pytest
from pandas import DataFrame, Series

from .context import pandas_ta as ta
from pandas_ta.overlap.kalman_trend import kalman_trend, _steady_warmup

W = 213  # warm-up at the defaults, printed by docs/measure_kalman_trend_proxy.py


def _walk(n=1200, seed=11, sigma=0.02, tick=None):
    rng = np.random.default_rng(seed)
    c = 100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n)))
    if tick:
        c = np.round(c / tick) * tick
    return Series(c)


def _matrix_filter(close, q_level=0.01, q_slope=0.0001):
    """Textbook predict/update in matrix form; non-finite y is predict-only."""
    c = close.values
    with np.errstate(divide="ignore", invalid="ignore"):
        y = np.log(c / c[np.isfinite(c) & (c > 0)][0])
    F = np.array([[1.0, 1.0], [0.0, 1.0]])
    H = np.array([[1.0, 0.0]])
    Q, R = np.diag([q_level, q_slope]), 1.0
    x, P = np.zeros(2), np.eye(2) * 1e4
    dist, vel = np.full(len(y), np.nan), np.full(len(y), np.nan)
    started = False
    for t in range(len(y)):
        if started:
            x, P = F @ x, F @ P @ F.T + Q
        if not np.isfinite(y[t]):
            continue
        started = True
        K = (P @ H.T / (H @ P @ H.T + R)).ravel()
        x = x + K * (y[t] - x[0])
        P = (np.eye(2) - np.outer(K, H)) @ P
        dist[t] = 100 * np.expm1(y[t] - x[0])
        vel[t] = 100 * x[1]
    return dist, vel


# ------------------------------------------------------------ correctness


def test_warmup_at_defaults():
    assert _steady_warmup(0.01, 0.0001) == W
    out = kalman_trend(_walk())
    assert out.iloc[:W].isna().all().all()
    assert out.iloc[W:].notna().all().all()


def test_matches_an_independent_matrix_filter_including_bad_bars():
    close = _walk(900)
    close.iloc[600] = np.nan
    close.iloc[700] = 0.0
    dist, vel = _matrix_filter(close)
    out = kalman_trend(close)
    for got, ref in ((out.iloc[:, 0].values, dist), (out.iloc[:, 1].values, vel)):
        ref = ref.copy()
        ref[:W] = np.nan
        assert (np.isnan(got) == np.isnan(ref)).all()
        assert np.nanmax(np.abs(got - ref)) < 1e-9


def test_log_linear_series_reads_its_step():
    close = Series(100.0 * np.exp(0.003 * np.arange(500)))
    out = kalman_trend(close).dropna()
    assert out.iloc[:, 0].abs().max() < 1e-6
    assert (out.iloc[:, 1] - 0.3).abs().max() < 1e-6


# ------------------------------------------------------------- bad input


@pytest.mark.parametrize("bad", [np.nan, 0.0, -1.0])
def test_a_bad_close_is_skipped_not_propagated(bad):
    close = _walk()
    close.iloc[600] = bad
    out = kalman_trend(close)
    assert out.iloc[600].isna().all()
    assert np.isfinite(out.iloc[601:].values).all()


def test_leading_nans_only_shift_the_output():
    close = _walk()
    padded = pd.concat([Series([np.nan] * 50), close], ignore_index=True)
    out = kalman_trend(padded)
    assert out.first_valid_index() == 50 + W
    assert out.iloc[50:].reset_index(drop=True).equals(kalman_trend(close))


def test_warmup_counts_valid_bars_not_bars():
    close = _walk()
    close.iloc[50:70] = np.nan
    assert kalman_trend(close).first_valid_index() == W + 20


def test_all_nan_or_too_few_valid_returns_none():
    assert kalman_trend(Series([np.nan] * 500)) is None
    close = _walk(500)
    close.iloc[:300] = np.nan
    assert kalman_trend(close) is None  # 200 valid closes <= W
    assert kalman_trend(_walk(W)) is None


@pytest.mark.parametrize("kw", [{"q_level": -1}, {"q_level": np.nan}, {"q_level": np.inf},
                                {"q_slope": -1e-4}, {"q_slope": np.nan},
                                # Riccati needs > 5000 steps: tiny q_slope, or large q_level
                                {"q_slope": 1e-12}, {"q_slope": 1e-8}, {"q_level": 30}])
def test_bad_parameters_raise(kw):
    with pytest.raises(ValueError, match="kalman_trend"):
        kalman_trend(_walk(), **kw)


# -------------------------------------------------------------- causality

_REAL = importlib.import_module("pandas_ta.overlap.kalman_trend")


def _load_mutant(edits, tag):
    src = open(_REAL.__file__, encoding="utf-8").read()
    for old, new in edits:
        assert src.count(old) == 1, f"mutation target {old!r} not unique"
        src = src.replace(old, new)
    mod = types.ModuleType(f"_kft_mutant_{tag}")
    mod.__file__ = _REAL.__file__
    exec(compile(src, _REAL.__file__, "exec"), mod.__dict__)
    return mod


MUTANTS = {
    "observation": [("e = y[t] - level", "e = y[min(t + 1, n - 1)] - level")],
    "dist_write": [("dist[t] = 100", "dist[t - 1] = 100")],
    "vel_write": [("vel[t] = 100", "vel[t - 1] = 100")],
    # the 🔴 failure: noise "fitted" on the whole series (column names unchanged)
    "full_series_fit": [
        ("    started = False\n",
         "    started = False\n    _fit = float(__import__('numpy').var(__import__('numpy').diff(y))) * 1e4\n"),
        ("p11 + q_slope\n", "p11 + q_slope * _fit\n"),
    ],
}

OFFSETS = range(240, 1200, 30)  # 32 offsets, all past the warm-up


def _leaks(fn):
    """Count offsets `j` at which rewriting bars >= j moves any bar < j."""
    close = _walk()
    base = fn(close)
    other = _walk(seed=99)
    hits = 0
    for j in OFFSETS:
        pert = close.copy()
        pert.iloc[j:] = other.iloc[j:].values
        out = fn(pert)
        a, b = base.iloc[:j], out.iloc[:j]
        if not (a.isna() == b.isna()).all().all():
            hits += 1
            continue
        if not a.equals(b):
            hits += 1
    return hits


def test_real_module_never_reads_the_future():
    assert _leaks(kalman_trend) == 0


@pytest.mark.parametrize("tag", sorted(MUTANTS))
def test_mutant_is_caught(tag):
    mod = _load_mutant(MUTANTS[tag], tag)
    close = _walk()
    assert not mod.kalman_trend(close).equals(kalman_trend(close))  # live
    assert _leaks(mod.kalman_trend) == len(OFFSETS)                 # caught, 32 of 32


# ------------------------------------------------------- head transient

PARAMS = [(0.01, 0.0001), (0.0, 0.001), (0.1, 0.001)]  # warm-ups 213 / 147 / 174


@pytest.mark.parametrize("q_level,q_slope", PARAMS)
def test_head_agrees_with_a_longer_run_from_the_first_emitted_bar(q_level, q_slope):
    w = _steady_warmup(q_level, q_slope)
    worst = 0.0
    for seed in range(10):
        for sigma in (0.005, 0.02, 0.05):
            close = _walk(1500, seed=seed, sigma=sigma)
            full = kalman_trend(close, q_level, q_slope)
            for s in (100, 500, 900):
                part = kalman_trend(close.iloc[s:], q_level, q_slope)
                i = part.first_valid_index()
                assert i == s + w
                worst = max(worst, (part.loc[i:] - full.loc[i:]).abs().max().max())
    assert worst < 1e-6


def test_the_warmup_is_not_padding():
    """Emitting from W // 2 would carry a visible transient: a warm-up
    chosen to pass a tail check would not catch this."""
    close = _walk(1500, seed=3)
    full = kalman_trend(close)
    mod = _load_mutant([("isfinite(y))[warmup]", "isfinite(y))[warmup // 2]")], "half")
    early = mod.kalman_trend(close.iloc[500:])
    i = 500 + W // 2
    assert early.first_valid_index() == i
    assert abs(early.loc[i].iloc[0] - full.loc[i].iloc[0]) > 1e-3


# ------------------------------------------------------------ scale-free


@pytest.mark.parametrize("k", [8.0, 64.0])
def test_power_of_two_scale_is_bit_identical(k):
    close = _walk(tick=0.05)
    assert kalman_trend(close).equals(kalman_trend(close * k))


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_other_scales_within_tolerance(k):
    close = _walk(tick=0.05)
    base, scaled = kalman_trend(close), kalman_trend(close * k)
    assert (base.isna() == scaled.isna()).all().all()
    assert (base - scaled).abs().max().max() < 1e-9


def test_columns_fire_and_are_not_constant():
    out = kalman_trend(_walk(tick=0.05)).dropna()
    for col in out:
        x = out[col]
        assert 0 < int((x > 0).sum()) < len(x)
        assert x.nunique() > 100


# ---------------------------------------------------------------- wiring


def test_name_registration_and_accessor():
    close = _walk(700)  # q_slope=1e-5 needs a 549-bar warm-up
    df = DataFrame({"open": close, "high": close, "low": close,
                    "close": close, "volume": 1.0})
    assert "kalman_trend" in ta.Category["overlap"]
    out = df.ta.kalman_trend()
    assert list(out.columns) == ["KFT_DIST_0.01_0.0001", "KFT_VEL_0.01_0.0001"]
    pd.testing.assert_frame_equal(out, kalman_trend(close))
    assert list(df.ta.kalman_trend(q_level=0, q_slope=0.001).columns) \
        == ["KFT_DIST_0_0.001", "KFT_VEL_0_0.001"]
    assert list(df.ta.kalman_trend(q_slope=1e-5).columns) \
        == ["KFT_DIST_0.01_1e-05", "KFT_VEL_0.01_1e-05"]
    assert df.ta.kalman_trend(q_level=0.01000001).columns[0] == "KFT_DIST_0.01000001_0.0001"
