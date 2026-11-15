# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.statistics.median_ad_hl2` -- rolling median absolute
deviation of hl2, scale-free (/close). Port of jesse (MIT)'s
`median_ad.py: scipy.stats.median_abs_deviation(hl2, window=5)`. scipy's
function defaults to `scale=1.0` (the plain statistic), not the
1.4826-scaled normal-consistent estimator of the older, deprecated
`scipy.stats.median_absolute_deviation` -- this port reproduces the
unscaled one, matching the issue's prototype (`docs/issues/screen/ind_screen_r2.py`,
candidate `j_median_ad_5`). Measurements in `docs/MedianAdHl2Measured.md`.

What these tests pin, in order of how much it would hurt to lose them:

* CAUSALITY by future-perturbation: rewrite every bar from `j` onward,
  demand bars `[0:j]` bit-identical, over a sweep of offsets. A look-ahead
  mutant (`importlib` source read, the write index of the rolling result
  shifted by the full window so output[t] is drawn entirely from bars > t,
  `exec`'d in memory -- never a hand-written copy) is proved live, then
  caught at every offset.
* CORRECTNESS against an independent loop written from the formula
  (plain median absolute deviation, scale=1), not from the module, plus a
  hand-computed window.
* SCALE-FREE: bit-identical under x8 and x64, within tolerance under x10 and
  x3.7 with matching NaN masks, and `0 < fires < n` plus not-constant.
* Wiring: `Category`, the accessor, and the column name `MEDIANAD_HL2_5`.
"""
import importlib
import types

import numpy as np
import pandas as pd
import pytest
from pandas import DataFrame, Series

from .context import pandas_ta as ta
from pandas_ta.statistics.median_ad_hl2 import median_ad_hl2


def _walk(n=600, seed=11, sigma=0.01, tick=None):
    rng = np.random.default_rng(seed)
    c = 100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n)))
    if tick:
        c = np.round(c / tick) * tick
    return Series(c)


def _hlc(close, spread=0.3):
    """Synthetic high/low straddling close by a fixed fraction, deterministic."""
    high = close * (1 + spread / 100)
    low = close * (1 - spread / 100)
    return high, low, close


# ------------------------------------------------------------ correctness


def test_matches_an_independent_loop():
    high, low, close = _hlc(_walk(300))
    n = 5
    hl2 = ((high + low) / 2).values
    c = close.values
    ref = np.full(len(c), np.nan)
    for t in range(n - 1, len(c)):
        w = hl2[t - n + 1: t + 1]
        ref[t] = np.median(np.abs(w - np.median(w))) / c[t]
    out = median_ad_hl2(high, low, close, length=n)
    assert (np.isnan(ref) == out.isna().values).all()
    assert np.nanmax(np.abs(out.values - ref)) < 1e-12


def test_hand_computed_window():
    # hl2 window [1, 2, 3, 4, 100] -> median 3, abs devs [2,1,0,1,97] -> median 1
    high = Series([2.0, 4.0, 6.0, 8.0, 200.0])
    low = Series([0.0, 0.0, 0.0, 0.0, 0.0])
    close = Series([10.0] * 5)
    out = median_ad_hl2(high, low, close, length=5)
    assert out.iloc[:4].isna().all()
    assert out.iloc[4] == pytest.approx(1.0 / 10.0, abs=1e-12)


def test_constant_hl2_reads_zero():
    high, low, close = _hlc(Series([50.0] * 20), spread=0.0)
    out = median_ad_hl2(high, low, close, length=5)
    assert (out.iloc[4:] == 0.0).all()


# -------------------------------------------------------------- causality

_REAL = importlib.import_module("pandas_ta.statistics.median_ad_hl2")


def _load_mutant(old, new, tag):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType(f"_median_ad_hl2_mutant_{tag}")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


MUTANTS = {
    "write_index": (
        "mad = hl2.rolling(length, min_periods=min_periods).apply(_mad, raw=True)",
        "mad = hl2.rolling(length, min_periods=min_periods).apply(_mad, raw=True).shift(-length)",
    ),
}

OFFSETS = range(20, 580, 25)


def _leaks(fn):
    """Count offsets `j` at which rewriting bars >= j moves any bar < j.
    A single-bar forward read is a weak probe against a median (an order
    statistic: swapping one of 5 window values for another ordinary value
    often leaves the median unchanged by chance, so a 1-bar mutant caught it
    unreliably across offsets and was dropped as a flaky guard -- not shipped
    as a `MUTANTS` entry here). `write_index`'s shift(-length) instead makes
    output[t] depend on a window drawn ENTIRELY from bars > t, so the
    boundary bar j-1 compares an all-original window against an all-replaced
    one -- detectable at every offset, not by luck."""
    high, low, close = _hlc(_walk())
    base = fn(high, low, close)
    o_high, o_low, o_close = _hlc(_walk(seed=99))
    hits = 0
    for j in OFFSETS:
        p_high, p_low, p_close = high.copy(), low.copy(), close.copy()
        p_high.iloc[j:] = o_high.iloc[j:].values
        p_low.iloc[j:] = o_low.iloc[j:].values
        p_close.iloc[j:] = o_close.iloc[j:].values
        out = fn(p_high, p_low, p_close)
        a, b = base.iloc[:j], out.iloc[:j]
        if not (a.isna() == b.isna()).all():
            hits += 1
            continue
        m = a.notna()
        if (a[m] != b[m]).any():
            hits += 1
    return hits


def test_real_module_never_reads_the_future():
    assert _leaks(median_ad_hl2) == 0


@pytest.mark.parametrize("tag", sorted(MUTANTS))
def test_mutant_is_caught(tag):
    mod = _load_mutant(*MUTANTS[tag], tag)
    high, low, close = _hlc(_walk())
    assert not mod.median_ad_hl2(high, low, close).equals(median_ad_hl2(high, low, close))  # live
    assert _leaks(mod.median_ad_hl2) == len(OFFSETS)  # caught, every offset


# ------------------------------------------------------------ scale-free


@pytest.mark.parametrize("k", [8.0, 64.0])
def test_power_of_two_scale_is_bit_identical(k):
    high, low, close = _hlc(_walk(tick=0.01))
    base = median_ad_hl2(high, low, close)
    scaled = median_ad_hl2(high * k, low * k, close * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_other_scales_within_tolerance(k):
    high, low, close = _hlc(_walk(tick=0.01))
    base = median_ad_hl2(high, low, close)
    scaled = median_ad_hl2(high * k, low * k, close * k)
    assert (base.isna() == scaled.isna()).all()
    assert (base - scaled).abs().max() < 1e-12


def test_column_is_not_constant_and_fires():
    high, low, close = _hlc(_walk(600, tick=0.01))
    out = median_ad_hl2(high, low, close)
    n = len(out)
    fires = out.notna().sum()
    assert 0 < fires < n
    assert out.dropna().nunique() > 100


# ---------------------------------------------------------------- wiring


def test_name_registration_and_accessor():
    high, low, close = _hlc(_walk(200))
    df = DataFrame({"open": close, "high": high, "low": low,
                    "close": close, "volume": 1.0})
    assert "median_ad_hl2" in ta.Category["statistics"]
    out = df.ta.median_ad_hl2()
    assert out.name == "MEDIANAD_HL2_5"
    pd.testing.assert_series_equal(out, median_ad_hl2(high, low, close))
    assert df.ta.median_ad_hl2(length=7).name == "MEDIANAD_HL2_7"
