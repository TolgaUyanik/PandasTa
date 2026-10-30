# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.volatility.tf_median_absdiff_20` -- the rolling
median absolute daily log return, ported from TSFEL (BSD-3-Clause)
`features.py median_abs_diff: median(|diff(x)|)`, issue #118. Measurements
and the open Gate E are in `docs/TfMedianAbsdiff20Measured.md`.

What these tests pin, in order of how much it would hurt to lose them:

* CAUSALITY by future-perturbation: rewrite every bar from `j` onward,
  demand bars `[0:j]` bit-identical with matching NaN masks, over 31
  offsets. A look-ahead mutant (`importlib` source read, the log-return
  series shifted 10 bars into the future, `exec`'d in memory -- never a
  hand-written copy) is proved live, then caught at 31 of 31.
  ⚠ A NAIVE one-bar-ahead shift (`.shift(-1)`) is deliberately NOT the
  catching mutant and is measured separately: median is a robust statistic,
  so replacing exactly one of the 20 values in a window changes its rank
  only part of the time -- `test_one_bar_future_read_is_only_partially_caught`
  pins this at 17 of the same 31 offsets, the CANDLE-1/smc_sweep escape
  (a test that picked one offset could read "causal" off a genuine leak).
  The 10-bar shift exposes 10 window positions per offset instead of 1,
  which is why it catches reliably.
* SCALE-FREE: bit-identical under x8 and x64 (the ratio close/close.shift(1)
  is exact under a power-of-two rescale, so its log is too), within 1e-12
  under x10 and x3.7 with matching NaN masks, and `0 < fires < n` plus a
  non-constant column so a degenerate pass cannot sneak through.
* CORRECTNESS against an independent loop written from the TSFEL formula
  text, not from the module, and a constant-log-return hand check.
* BOUND: a median of absolute values is non-negative by construction.
* Wiring: `Category`, the accessor, and the column name `MEDABSDIFF_20`.
"""
import importlib
import types

import numpy as np
import pandas as pd
import pytest
from pandas import DataFrame, Series

from .context import pandas_ta as ta
from pandas_ta.volatility.tf_median_absdiff_20 import tf_median_absdiff_20


def _walk(n=1200, seed=11, sigma=0.02, tick=None):
    rng = np.random.default_rng(seed)
    c = 100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n)))
    if tick:
        c = np.round(c / tick) * tick
    return Series(c)


# ------------------------------------------------------------ correctness


def test_constant_log_return_reads_that_value():
    # Every bar-to-bar move is the same ratio, so every window's median of
    # |log-return| equals that one constant log-return exactly.
    r = 0.01
    close = Series(100.0 * np.exp(np.arange(25) * r))
    out = tf_median_absdiff_20(close, length=20)
    assert out.iloc[20:].apply(lambda x: x == pytest.approx(r, abs=1e-12)).all()


def test_matches_an_independent_loop():
    close = _walk(400)
    n = 20
    c = close.values
    r = np.abs(np.log(c[1:] / c[:-1]))
    ref = np.full(len(c), np.nan)
    for i in range(n, len(c)):
        w = sorted(r[i - n:i])  # n log-returns, ending at the return into bar i
        m = n // 2
        ref[i] = (w[m - 1] + w[m]) / 2.0 if n % 2 == 0 else w[m]
    out = tf_median_absdiff_20(close, length=n)
    assert (np.isnan(ref) == out.isna().values).all()
    m = ~np.isnan(ref)
    assert np.nanmax(np.abs(out.values[m] - ref[m])) < 1e-9


def test_flat_price_run_reads_zero_not_nan():
    close = Series([100.0] * 25)
    out = tf_median_absdiff_20(close, length=20)
    assert (out.iloc[20:] == 0.0).all()


def test_length_zero_and_negative_fall_back_to_default():
    close = _walk(100)
    default = tf_median_absdiff_20(close)
    for bad in (0, -5):
        out = tf_median_absdiff_20(close, length=bad)
        assert out.name == "MEDABSDIFF_20" == default.name
        pd.testing.assert_series_equal(out, default)


def test_non_negative():
    out = tf_median_absdiff_20(_walk(tick=0.05)).dropna()
    assert (out >= -1e-12).all()


# -------------------------------------------------------------- causality

_REAL = importlib.import_module("pandas_ta.volatility.tf_median_absdiff_20")


def _load_mutant(old, new, tag):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType(f"_medabsdiff_mutant_{tag}")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


_SRC_LOGRET = "logret = nplog(close / close.shift(1))"

MUTANTS = {
    "future_logret_10": (_SRC_LOGRET, f"{_SRC_LOGRET}.shift(-10)"),
}

OFFSETS = range(40, 1100, 35)  # 31 offsets


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
        if not (a.isna() == b.isna()).all():
            hits += 1
            continue
        m = a.notna()
        if (a[m] != b[m]).any():
            hits += 1
    return hits


def test_real_module_never_reads_the_future():
    assert _leaks(tf_median_absdiff_20) == 0


@pytest.mark.parametrize("tag", sorted(MUTANTS))
def test_mutant_is_caught(tag):
    mod = _load_mutant(*MUTANTS[tag], tag)
    close = _walk()
    assert not mod.tf_median_absdiff_20(close).equals(tf_median_absdiff_20(close))  # live
    assert _leaks(mod.tf_median_absdiff_20) == len(OFFSETS)                         # caught, 31 of 31


def test_one_bar_future_read_is_only_partially_caught():
    """Documents the escape, does not need to pass 31/31.

    A single-bar look-ahead (`.shift(-1)`) replaces exactly one of the 20
    values in the rolling window read at `j-1`; median only moves when that
    one replacement changes which value sits at the middle rank. Measured
    on this exact walk/offset set: live (differs from the real module) but
    caught at only 17 of 31 offsets -- a test that checked a single offset
    would have a better-than-even chance of calling this leaking mutant
    "causal". This is why `test_mutant_is_caught` uses a 10-bar shift,
    which exposes 10 window positions per offset instead of 1.
    """
    mod = _load_mutant(_SRC_LOGRET, f"{_SRC_LOGRET}.shift(-1)", "future_logret_1")
    close = _walk()
    assert not mod.tf_median_absdiff_20(close).equals(tf_median_absdiff_20(close))  # live
    assert _leaks(mod.tf_median_absdiff_20) == 17                                   # partially caught


# ------------------------------------------------------------ scale-free


@pytest.mark.parametrize("k", [8.0, 64.0])
def test_power_of_two_scale_is_bit_identical(k):
    close = _walk(tick=0.05)
    base, scaled = tf_median_absdiff_20(close), tf_median_absdiff_20(close * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_other_scales_within_tolerance(k):
    close = _walk(tick=0.05)
    base, scaled = tf_median_absdiff_20(close), tf_median_absdiff_20(close * k)
    assert (base.isna() == scaled.isna()).all()
    assert (base - scaled).abs().max() < 1e-12


def test_column_is_not_constant():
    out = tf_median_absdiff_20(_walk(tick=0.05)).dropna()
    assert 0 < len(out) < 1200
    assert out.nunique() > 100


# ---------------------------------------------------------------- wiring


def test_name_registration_and_accessor():
    close = _walk(200)
    df = DataFrame({"open": close, "high": close, "low": close,
                    "close": close, "volume": 1.0})
    assert "tf_median_absdiff_20" in ta.Category["volatility"]
    out = df.ta.tf_median_absdiff_20()
    assert out.name == "MEDABSDIFF_20"
    pd.testing.assert_series_equal(out, tf_median_absdiff_20(close))
    assert df.ta.tf_median_absdiff_20(length=10).name == "MEDABSDIFF_10"
