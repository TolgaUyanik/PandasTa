# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.statistics.trend_scan` -- the max-|t| trailing trend
scan across a set of horizons (issue #20). Every number quoted here is
printed by `docs/measure_trend_scan_proxy.py`; the full picture, including
the deferred Gate E, is in `docs/TrendScanMeasured.md`.

⚠ READ THIS FIRST. The source (Lopez de Prado, *Machine Learning for Asset
Managers* ch05, "trend scanning") uses this statistic FORWARD-looking, as a
label. This port keeps only the trailing, feature-side half -- the task's
explicit decision -- so Gate B's mutant is not an incidental off-by-one: it
is the book's OWN forward-looking form, reconstructed by editing three
lines of the real module (the window bounds and the valid range), and
shown to leak where the real module does not.

What these tests pin, in order of how much it would hurt to lose:

* CAUSALITY by future-perturbation: the real module leaks at 0 of 8 tested
  offsets; the forward-window mutant leaks at 8 of 8.
* CORRECTNESS against TWO independent oracles, at several individual
  horizons and window positions: a plain definitional OLS (sample
  means/covariances, not the module's prefix-sum formulas), and the
  r-based identity the task itself cites (`t = r * sqrt((n-2)/(1-r**2))`,
  monotone in `r` -- the reason a SINGLE horizon would only restate
  `linreg`'s `r`; only the max-over-horizons is new).
* GATE D, the defect the task flagged directly: regressing on `log(close)`
  itself is NOT bit-identical under a power-of-two rescale (measured
  nonzero); regressing on `log(close / anchor)`, what the module actually
  ships, IS (measured exactly 0.0).
* SCALE-FREE: bit-identical under x8/x64, within 1e-6 under x10/x3.7, NaN
  masks matching, and `0 < fires < n`.
* Bad input: a NaN/zero/negative close poisons only the windows that cover
  it; horizons below 3 raise.
* Wiring: `Category`, the accessor, and the column names.
"""
import importlib
import types

import numpy as np
import pandas as pd
import pytest
from pandas import DataFrame, Series

from .context import pandas_ta as ta
from pandas_ta.statistics.trend_scan import trend_scan, DEFAULT_HORIZONS, _rolling_trend_t

TAG = "-".join(str(h) for h in DEFAULT_HORIZONS)
T_COL, L_COL = f"TSCAN_T_{TAG}", f"TSCAN_L_{TAG}"


def _walk(n=4000, seed=11, sigma=0.02, tick=None, drift=0.0):
    rng = np.random.default_rng(seed)
    c = 100.0 * np.exp(np.cumsum(rng.normal(drift, sigma, n)))
    if tick:
        c = np.round(c / tick) * tick
    return Series(c)


def _z_of(close):
    """The module's own anchor device, replicated independently for the
    oracle tests below (close/anchor ratio, so log is exact under x8/x64)."""
    vals = close.to_numpy(dtype=float)
    valid = np.isfinite(vals) & (vals > 0)
    anchor = vals[valid][0]
    with np.errstate(divide="ignore", invalid="ignore"):
        z = np.log(vals / anchor)
    z[~valid] = np.nan
    return z


def _naive_ols_t(y):
    """Plain definitional OLS t-stat -- sample means and covariances, not
    the module's prefix-sum formulas. An independent codepath."""
    n = len(y)
    x = np.arange(n, dtype=float)
    xbar, ybar = x.mean(), y.mean()
    Sxy = ((x - xbar) * (y - ybar)).sum()
    Sxx = ((x - xbar) ** 2).sum()
    Syy = ((y - ybar) ** 2).sum()
    slope = Sxy / Sxx
    SSR = Syy - slope * Sxy
    df = n - 2
    se = np.sqrt(SSR / df / Sxx)
    return slope / se


def _r_based_t(y):
    """The task's own cited identity: t = r * sqrt((n-2)/(1-r**2)), a
    genuinely different formula (correlation, not slope/SE) from both the
    module and `_naive_ols_t` above."""
    n = len(y)
    x = np.arange(n, dtype=float)
    r = np.corrcoef(x, y)[0, 1]
    return r * np.sqrt((n - 2) / (1 - r ** 2))


# ------------------------------------------------------------ correctness


@pytest.mark.parametrize("length", [3, 5, 10, 20, 60])
@pytest.mark.parametrize("t_end", [999, 2500, 3999])
def test_matches_two_independent_oracles(length, t_end):
    close = _walk(4000, seed=3)
    z = _z_of(close)
    window = z[t_end - length + 1: t_end + 1]
    out = trend_scan(close, horizons=[length])
    mine = out[f"TSCAN_T_{length}"].iloc[t_end]
    assert abs(mine - _naive_ols_t(window)) < 1e-6
    assert abs(mine - _r_based_t(window)) < 1e-6


def test_picks_the_horizon_with_the_largest_absolute_t():
    close = _walk(4000, seed=5)
    out = trend_scan(close, horizons=DEFAULT_HORIZONS)
    z = _z_of(close)
    for t_end in (500, 1500, 3000, 3999):
        best_abs, best_L = -1.0, None
        for L in DEFAULT_HORIZONS:
            window = z[t_end - L + 1: t_end + 1]
            t_val = _naive_ols_t(window)
            if abs(t_val) > best_abs:
                best_abs, best_L = abs(t_val), L
        assert out[L_COL].iloc[t_end] == best_L
        assert abs(abs(out[T_COL].iloc[t_end]) - best_abs) < 1e-6


# ------------------------------------------------------------------ Gate D


def test_ratio_anchor_is_bit_identical_but_raw_log_is_not_under_scale():
    """The defect the task flagged, measured directly: `log(close)` on its
    own is NOT guaranteed bit-identical under a power-of-two rescale, so a
    future "simplification" that drops the ratio device would silently
    break x8/x64 exactness -- pin that it is real, not a strawman."""
    close = _walk(2000, seed=9, tick=0.05)
    scaled = close * 8.0

    raw_base, raw_scaled = np.log(close.to_numpy(dtype=float)), np.log(scaled.to_numpy(dtype=float))
    raw_diff = np.nanmax(np.abs(raw_scaled - (raw_base + np.log(8.0))))
    assert raw_diff > 0.0  # the naive reading is NOT bit-identical

    ratio_base, ratio_scaled = _z_of(close), _z_of(scaled)
    assert np.array_equal(ratio_base, ratio_scaled, equal_nan=True)  # the module's device IS


# ------------------------------------------------------------- causality

_REAL = importlib.import_module("pandas_ta.statistics.trend_scan")


def _load_mutant(edits, tag):
    src = open(_REAL.__file__, encoding="utf-8").read()
    for old, new in edits:
        assert src.count(old) == 1, f"mutation target {old!r} not unique"
        src = src.replace(old, new)
    mod = types.ModuleType(f"_trend_scan_mutant_{tag}")
    mod.__file__ = _REAL.__file__
    exec(compile(src, _REAL.__file__, "exec"), mod.__dict__)
    return mod


# The book's OWN forward-looking form: the SAME trailing window and the
# SAME regression, written at the bar the window STARTS at instead of the
# bar it ENDS at -- a window [g, g+L-1] "known" at g is exactly a window
# [T-L+1, T] "known" at T-L+1 (g = T-L+1). Two edits, the complete set of
# places a result is written.
FORWARD_MUTANT = [
    ("out[length - 1] = _t(S1, S2, S3, cnt)", "out[0] = _t(S1, S2, S3, cnt)"),
    ("out[t] = _t(S1, S2, S3, cnt)", "out[t - length + 1] = _t(S1, S2, S3, cnt)"),
]

OFFSETS = list(range(500, 3700, 400))  # 8 offsets, all past the warm-up


def _leaks(fn, horizons=DEFAULT_HORIZONS):
    close = _walk(4000, seed=13)
    base = fn(close, horizons)
    other = _walk(4000, seed=99)
    hits = 0
    for j in OFFSETS:
        pert = close.copy()
        pert.iloc[j:] = other.iloc[j:].values
        out = fn(pert, horizons)
        a, b = base.iloc[:j], out.iloc[:j]
        if not (a.isna() == b.isna()).all().all():
            hits += 1
            continue
        if not a.equals(b):
            hits += 1
    return hits


def test_real_module_never_reads_the_future():
    assert _leaks(trend_scan) == 0


def test_forward_mutant_is_live_and_caught_at_every_offset():
    mod = _load_mutant(FORWARD_MUTANT, "forward")
    close = _walk(4000, seed=13)
    assert not mod.trend_scan(close, DEFAULT_HORIZONS).equals(trend_scan(close, DEFAULT_HORIZONS))  # live
    assert _leaks(mod.trend_scan) == len(OFFSETS)                                                    # caught, 8 of 8


# ------------------------------------------------------------ scale-free


@pytest.mark.parametrize("k", [8.0, 64.0])
def test_power_of_two_scale_is_bit_identical(k):
    close = _walk(3000, seed=11, tick=0.05)
    assert trend_scan(close).equals(trend_scan(close * k))


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_other_scales_within_tolerance(k):
    close = _walk(3000, seed=11, tick=0.05)
    base, scaled = trend_scan(close), trend_scan(close * k)
    assert (base.isna() == scaled.isna()).all().all()
    assert (base[T_COL] - scaled[T_COL]).abs().max() < 1e-6
    assert (base[L_COL] - scaled[L_COL]).abs().max() == 0.0


def test_fires_and_is_not_constant():
    out = trend_scan(_walk(3000, seed=11, tick=0.05, drift=0.0005))
    t_out, l_out = out[T_COL].dropna(), out[L_COL].dropna()
    assert 0 < len(t_out) < 3000
    assert t_out.nunique() > 100
    assert set(l_out.unique()) <= set(float(h) for h in DEFAULT_HORIZONS)
    assert l_out.nunique() > 1  # more than one horizon actually wins somewhere


# --------------------------------------------------------------- bad input


@pytest.mark.parametrize("bad", [np.nan, 0.0, -1.0])
def test_a_bad_close_poisons_only_the_windows_covering_it(bad):
    close = _walk(1000, seed=21)
    close.iloc[500] = bad
    vals = close.to_numpy(dtype=float)
    valid = np.isfinite(vals) & (vals > 0)
    z = _z_of(close)
    out = Series(_rolling_trend_t(z, valid, 10))
    # exactly the 10 windows of length 10 that cover bar 500 are NaN
    assert out.iloc[500:510].isna().all()
    assert out.iloc[510:].notna().all()
    assert out.iloc[9:500].notna().all()


def test_too_few_valid_closes_returns_none():
    assert trend_scan(Series([np.nan] * 100), horizons=[5]) is None
    assert trend_scan(_walk(5), horizons=[10]) is None


@pytest.mark.parametrize("bad_horizons", [[2], [1, 5], []])
def test_bad_horizons_raise(bad_horizons):
    with pytest.raises(ValueError, match="trend_scan"):
        trend_scan(_walk(500), horizons=bad_horizons)


# ---------------------------------------------------------------- wiring


def test_name_registration_and_accessor():
    close = _walk(1000, seed=31)
    df = DataFrame({"open": close, "high": close, "low": close,
                    "close": close, "volume": 1.0})
    assert "trend_scan" in ta.Category["statistics"]
    out = df.ta.trend_scan()
    assert list(out.columns) == [T_COL, L_COL]
    pd.testing.assert_frame_equal(out, trend_scan(close))
    custom = df.ta.trend_scan(horizons=[5, 10])
    assert list(custom.columns) == ["TSCAN_T_5-10", "TSCAN_L_5-10"]
