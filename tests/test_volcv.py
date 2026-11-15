# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.volume.volcv` -- the coefficient of variation of
volume, `std(volume, length) / mean(volume, length)`: how erratic
participation is, as opposed to how high it is.
Source: Alpha Architect "How Volatility and Turnover Affect Return
Reversals"; Kissell 2013 ch. 5 (both describe the ratio; neither is a
measured claim). Measurements and the open gates are in
`docs/VolcvMeasured.md`.

What these tests pin, in order of how much it would hurt to lose them:

* CAUSALITY by future-perturbation: rewrite every volume bar from `j` onward
  (another walk, a x1000 future), demand bars `[0:j]` bit-identical with
  matching NaN masks, over 31 offsets. Two one-bar look-ahead mutants
  (`importlib` source read, the mean or the std window shifted forward,
  `exec`'d in memory) are each proved live, then caught at 31 of 31.
* SCALE-FREE: the column reads no price, so a price rescaling cannot reach
  it. `std(kv)/mean(kv) = std(v)/mean(v)` algebraically for any k > 0; on the
  seed-11 walk, volume x8 and x64 are bit-identical, x10 and x3.7 differ by a
  measured bound, NaN masks match. Not constant.
* ZERO MEAN reads NaN, never inf (an all-zero-volume stretch).
* CORRECTNESS against an independent loop written from the definition, a
  hand-computed sequence, the `length`-1-bar warm-up, a NaN bar blanking
  itself and the next `length` - 1 bars, `offset`, `fillna`.
* Wiring: `Category`, the accessor, the column name `VOLCV_20`.
"""
import importlib
import types

import numpy as np
import pandas as pd
import pytest
from pandas import DataFrame, Series

from .context import pandas_ta as ta
from pandas_ta.volume.volcv import volcv


def _walk(n=1200, seed=11):
    """Integer share counts, lognormal."""
    rng = np.random.default_rng(seed)
    return Series(np.round(rng.lognormal(10.0, 0.6, n)))


# ------------------------------------------------------------ correctness


def test_hand_computed():
    v = Series([1.0, 2.0, 6.0, 3.0, 4.0])
    out = volcv(v, length=3)
    #  bar2: mean(1,2,6)=3, std(1,2,6, ddof=1) -> cv
    #  bar3: mean(2,6,3)=11/3, std(2,6,3, ddof=1)
    #  bar4: mean(6,3,4)=13/3, std(6,3,4, ddof=1)
    window = [[1.0, 2.0, 6.0], [2.0, 6.0, 3.0], [6.0, 3.0, 4.0]]
    expected = [np.std(w, ddof=1) / np.mean(w) for w in window]
    assert out.isna().tolist() == [True, True, False, False, False]
    np.testing.assert_allclose(out.iloc[2:].tolist(), expected, rtol=1e-12)


def test_matches_an_independent_loop():
    v = _walk().values
    length = 20
    ref = np.full(len(v), np.nan)
    for t in range(length - 1, len(v)):
        window = v[t - length + 1:t + 1]
        m = window.mean()
        ref[t] = window.std(ddof=1) / m if m > 0 else np.nan
    out = volcv(Series(v))
    assert (np.isnan(ref) == out.isna().values).all()
    np.testing.assert_allclose(out.values[length - 1:], ref[length - 1:], rtol=1e-12)


def test_zero_mean_is_nan_not_inf():
    v = Series([0.0] * 25 + [5.0] * 5)
    out = volcv(v, length=20)
    assert out.iloc[19:25].isna().all()
    assert np.isfinite(out.iloc[25:]).all()


def test_edge_cases():
    v = _walk()
    base = volcv(v, length=20)
    assert int(base.isna().sum()) == 19
    vn = v.copy()
    vn[500] = np.nan
    gap = volcv(vn, length=20)
    assert gap[500:520].isna().all() and gap[520:].notna().all()
    assert int(gap.isna().sum()) == 19 + 20
    pd.testing.assert_series_equal(volcv(v, offset=1), base.shift(1))
    assert volcv(v, fillna=0).isna().sum() == 0


# -------------------------------------------------------------- causality

_REAL = importlib.import_module("pandas_ta.volume.volcv")


def _load_mutant(old, new, tag):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType(f"_volcv_mutant_{tag}")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


MUTANTS = {
    "mean": ("mean = volume.rolling(", "mean = volume.shift(-1).rolling("),
    "std": ("std = volume.rolling(", "std = volume.shift(-1).rolling("),
}

OFFSETS = range(60, 1100, 34)  # 31 offsets


def _moved(a, b):
    if not (a.isna() == b.isna()).all():
        return True
    m = a.notna()
    return bool((a[m] != b[m]).any())


def _leaks(fn):
    """Count offsets `j` at which rewriting bars >= j moves any bar < j.

    A random rewrite of bar j can leave the window's mean/std unchanged by
    coincidence; the x1000 future makes that vanishingly unlikely.
    """
    v = _walk()
    base = fn(v)
    other = _walk(seed=99)
    hits = 0
    for j in OFFSETS:
        for future in (other.iloc[j:].values, v.iloc[j:].values * 1000.0):
            pv = v.copy()
            pv.iloc[j:] = future
            if _moved(base.iloc[:j], fn(pv).iloc[:j]):
                hits += 1
                break
    return hits


def test_real_module_never_reads_the_future():
    assert _leaks(volcv) == 0


@pytest.mark.parametrize("tag", sorted(MUTANTS))
def test_mutant_is_caught(tag):
    mod = _load_mutant(*MUTANTS[tag], tag)
    v = _walk()
    assert not mod.volcv(v).equals(volcv(v))
    assert _leaks(mod.volcv) == len(OFFSETS)


# ------------------------------------------------------------ scale-free


@pytest.mark.parametrize("k", [8.0, 64.0])
def test_volume_scale_is_bit_identical(k):
    v = _walk()
    base, scaled = volcv(v), volcv(v * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_volume_scale_within_tolerance(k):
    v = _walk()
    base, scaled = volcv(v), volcv(v * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    # the bound VolcvMeasured.md quotes (measured 7.3e-15 / 1.9e-14)
    assert ((scaled[m] - base[m]).abs() / base[m].abs()).max() <= 1e-13


def test_column_is_not_constant():
    out = volcv(_walk())
    m = out.notna()
    assert int(m.sum()) == 1181 and out[m].nunique() == 1181
    assert 0.2867 < out.min() < 0.2868 and 1.4415 < out.max() < 1.4416


def test_fires_between_zero_and_n():
    out = volcv(_walk())
    m = out.notna()
    assert 0 < int(m.sum()) < len(out)


# ---------------------------------------------------------------- wiring


def test_name_registration_and_accessor():
    v = _walk(200)
    df = DataFrame({"open": 1.0, "high": 1.0, "low": 1.0, "close": 1.0, "volume": v})
    assert "volcv" in ta.Category["volume"]
    out = df.ta.volcv()
    assert out.name == "VOLCV_20"
    pd.testing.assert_series_equal(out, volcv(v))
    assert df.ta.volcv(length=10).name == "VOLCV_10"
