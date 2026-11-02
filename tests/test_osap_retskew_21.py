# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.statistics.osap_retskew_21` -- skewness of daily
simple returns over a trailing 21-bar window (OSAP `ReturnSkew`,
Bali-Engle-Murray 2016, ported from the textbook formula, never from OSAP's
GPL-2.0 code; issue #36). Measurements and the open gates are in
`docs/OsapRetskew21Measured.md`. Gate E is pending (CLAUDE.md, "Owed, not
failed").

What these pin, in order of how much it would hurt to lose:

* CAUSALITY by future-perturbation: rewrite every close bar from `j`
  onward (another walk), demand bars `[0:j]` bit-identical with matching
  NaN masks, over 31 offsets. A one-bar look-ahead mutant (`importlib`
  source read, the return series shifted forward before `.rolling().skew()`,
  `exec`'d in memory) is proved live, then caught at 31 of 31.
* SCALE-FREE: the return series is a ratio of two closes, so a uniform
  price rescale cancels before the skewness is computed -- bit-identical
  under x8/x64, within 1e-9 under x10/x3.7, matching NaN masks, plus
  `0 < fires < n` and not a constant column.
* CORRECTNESS against an independent per-window loop built from the
  Fisher-Pearson bias-corrected skewness formula (the same one this repo's
  `statistics.skew` already ships for price), plus a 3-bar hand-derived
  example.
* Wiring: `Category`, the accessor, the column name `OSAP_RETSKEW_21`.
"""
import importlib
import types

import numpy as np
import pandas as pd
import pytest
from pandas import Series

from .context import pandas_ta as ta
from pandas_ta.statistics.osap_retskew_21 import osap_retskew_21


def _walk(n=1200, seed=23, s0=100.0, sigma=0.018):
    rng = np.random.default_rng(seed)
    rets = rng.normal(0.0, sigma, n)
    px = s0 * np.cumprod(1.0 + rets)
    return Series(np.round(px, 2))


# ------------------------------------------------------------ correctness


def test_hand_derived_three_returns():
    """length=3 (the smallest window skew is defined on): 4 closes ->
    3 returns -> one skew value, derived by the bias-corrected formula
    n/((n-1)(n-2)) * sum((r-mean)^3) / s^3, s = sample std (ddof=1)."""
    close = Series([100.0, 103.0, 101.0, 108.0])
    out = osap_retskew_21(close, length=3)
    r = close.pct_change(fill_method=None).to_numpy()[1:]  # 3 returns
    n = 3
    m = r.mean()
    s = r.std(ddof=1)
    expected = (n / ((n - 1) * (n - 2))) * np.sum((r - m) ** 3) / s ** 3
    assert out.iloc[:3].isna().all()
    assert out.iloc[3] == pytest.approx(expected, abs=1e-12)


def test_matches_an_independent_loop():
    close = _walk()
    length = 21
    out = osap_retskew_21(close, length=length)
    r = close.pct_change(fill_method=None).to_numpy(dtype=float)

    ref = np.full(len(r), np.nan)
    for i in range(length, len(r)):
        window = r[i - length + 1:i + 1]
        n = length
        m = window.mean()
        s = window.std(ddof=1)
        ref[i] = (n / ((n - 1) * (n - 2))) * np.sum((window - m) ** 3) / s ** 3

    assert (np.isnan(ref) == out.isna().values).all()
    np.testing.assert_allclose(out.values[length:], ref[length:], rtol=1e-9)


def test_matches_pandas_rolling_skew_directly():
    """The module is defined to BE close.pct_change().rolling(length).skew() --
    pin that equivalence directly, independent of the hand-written loop above."""
    close = _walk(seed=7)
    out = osap_retskew_21(close, length=21)
    expected = close.pct_change(fill_method=None).rolling(21, min_periods=21).skew()
    pd.testing.assert_series_equal(out, expected, check_names=False)


def test_insufficient_history_returns_none():
    close = _walk(5)
    assert osap_retskew_21(close, length=21) is None


def test_default_length_is_21():
    close = _walk()
    out = osap_retskew_21(close)
    assert out.name == "OSAP_RETSKEW_21"
    assert int(out.isna().sum()) == 21


# -------------------------------------------------------------- causality


_REAL = importlib.import_module("pandas_ta.statistics.osap_retskew_21")


def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_osap_retskew_21_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


MUTANT = (
    "ret = close.pct_change(fill_method=None)",
    "ret = close.pct_change(fill_method=None).shift(-1)",
)

OFFSETS = range(40, 1100, 35)  # 31 offsets


def _leaks(fn):
    close = _walk()
    base = fn(close)
    other = _walk(seed=99)
    hits = 0
    for j in OFFSETS:
        perturbed = close.copy()
        perturbed.iloc[j:] = other.iloc[j:].values
        out = fn(perturbed)
        a, b = base.iloc[:j], out.iloc[:j]
        if not (a.isna() == b.isna()).all():
            hits += 1
            continue
        m = a.notna()
        if (a[m] != b[m]).any():
            hits += 1
    return hits


def test_real_module_never_reads_the_future():
    assert _leaks(osap_retskew_21) == 0


def test_lookahead_mutant_is_caught():
    mod = _load_mutant(*MUTANT)
    close = _walk()
    assert not mod.osap_retskew_21(close).equals(osap_retskew_21(close))  # live
    assert _leaks(mod.osap_retskew_21) == len(OFFSETS)  # caught, 31 of 31


# ------------------------------------------------------------ scale-free


@pytest.mark.parametrize("k", [8.0, 64.0])
def test_power_of_two_price_scale_is_bit_identical(k):
    close = _walk()
    base = osap_retskew_21(close)
    scaled = osap_retskew_21(close * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_other_scales_within_tolerance(k):
    close = _walk()
    base = osap_retskew_21(close)
    scaled = osap_retskew_21(close * k)
    assert (base.isna() == scaled.isna()).all()
    assert (base - scaled).abs().max() < 1e-9


def test_fires_and_is_not_constant():
    close = _walk()
    out = osap_retskew_21(close)
    fires = int(out.notna().sum())
    assert 0 < fires < len(out)
    assert out.dropna().nunique() > 100


# ---------------------------------------------------------------- wiring


def test_name_registration_and_accessor():
    close = _walk(200)
    df = pd.DataFrame({"open": close, "high": close, "low": close,
                        "close": close, "volume": close})
    assert "osap_retskew_21" in ta.Category["statistics"]
    out = df.ta.osap_retskew_21()
    assert out.name == "OSAP_RETSKEW_21"
    pd.testing.assert_series_equal(out, osap_retskew_21(close))
    assert df.ta.osap_retskew_21(length=10).name == "OSAP_RETSKEW_10"
