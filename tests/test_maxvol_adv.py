# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.volume.maxvol_adv` -- the largest volume of the last
`short` bars over the `long`-bar average volume (ADV).
Source: r/Daytrading 1tv21c0 (tier 4, untested claims). Measurements and the
open gates are in `docs/MaxvolAdvMeasured.md`.

What these tests pin, in order of how much it would hurt to lose them:

* CAUSALITY by future-perturbation: rewrite every volume bar from `j` onward
  (another walk, a x1000 future), demand bars `[0:j]` bit-identical with
  matching NaN masks, over 31 offsets.  Two one-bar look-ahead mutants
  (`importlib` source read, the peak or the ADV window shifted forward,
  `exec`'d in memory) are each proved live, then caught at 31 of 31.
* SCALE-FREE: the column reads no price, so a price rescaling cannot reach
  it; on the seed-11 walk, volume x8 and x64 are bit-identical, x10 and
  x3.7 differ by at most 2.2e-16 and 3.9e-16 relative, NaN masks match.  Not constant: 1,151
  distinct values over the 1,151 non-warm-up bars, range 1.129 to 7.358.
* ZERO OR NEGATIVE ADV reads NaN, never inf (a halted stretch, bad data).
* CORRECTNESS against an independent loop written from the definition, a
  hand-computed sequence, `short > long`, the 49-bar warm-up, a NaN bar
  blanking itself and the next max(short, long) - 1 bars (50 in all at the
  defaults, 80 at short=80), `offset`, `fillna`.
* Wiring: `Category`, the accessor, the column name `MAXVOLADV_14_50`.
"""
import importlib
import types

import numpy as np
import pandas as pd
import pytest
from pandas import DataFrame, Series

from .context import pandas_ta as ta
from pandas_ta.volume.maxvol_adv import maxvol_adv


def _walk(n=1200, seed=11):
    """Integer share counts, lognormal."""
    rng = np.random.default_rng(seed)
    return Series(np.round(rng.lognormal(10.0, 0.6, n)))


# ------------------------------------------------------------ correctness


def test_hand_computed():
    v = Series([1.0, 2.0, 6.0, 3.0, 4.0])
    out = maxvol_adv(v, short=2, long=4)
    #  bar3: max(6,3)=6 / mean(1,2,6,3)=3 ; bar4: max(3,4)=4 / mean(2,6,3,4)=3.75
    assert out.isna().tolist() == [True] * 3 + [False] * 2
    assert out.iloc[3:].tolist() == [2.0, 4.0 / 3.75]


def test_matches_an_independent_loop():
    v = _walk().values
    ref = np.full(len(v), np.nan)
    for t in range(49, len(v)):
        ref[t] = v[t - 13:t + 1].max() / (v[t - 49:t + 1].sum() / 50)
    out = maxvol_adv(Series(v))
    assert (np.isnan(ref) == out.isna().values).all()
    np.testing.assert_allclose(out.values[49:], ref[49:], rtol=1e-12)


def test_zero_adv_is_nan_not_inf():
    v = Series([0.0] * 60 + [5.0] * 5)
    out = maxvol_adv(v, short=14, long=50)
    assert out.iloc[49:60].isna().all()
    assert np.isfinite(out.iloc[60:]).all()
    # short > long: a peak can exist while ADV is zero
    w = Series([7.0] + [0.0] * 10)
    assert maxvol_adv(w, short=10, long=3).isna().all()
    # negative ADV: bar 2 mean(-5,1,1) = -1 -> NaN; bar 3 max(1,1)/mean(1,1,1) = 1
    neg = maxvol_adv(Series([-5.0, 1.0, 1.0, 1.0]), short=2, long=3)
    assert neg.iloc[:3].isna().all() and neg.iloc[3] == 1.0


def test_short_longer_than_long():
    out = maxvol_adv(Series([1.0, 2.0, 3.0, 4.0]), short=4, long=2)
    assert out.iloc[:3].isna().all() and out.iloc[3] == 4.0 / 3.5


def test_edge_cases():
    v = _walk()
    base = maxvol_adv(v)
    assert int(base.isna().sum()) == 49
    vn = v.copy()
    vn[500] = np.nan
    gap = maxvol_adv(vn)
    assert gap[500:550].isna().all() and gap[550:].notna().all()
    assert int(gap.isna().sum()) == 49 + 50
    # short > long: the peak window is the longer one, so it sets the gap.
    gap80 = maxvol_adv(vn, short=80, long=50)
    assert gap80[500:580].isna().all() and gap80[580:].notna().all()
    assert int(gap80.isna().sum()) == 79 + 80
    pd.testing.assert_series_equal(maxvol_adv(v, offset=1), base.shift(1))
    assert maxvol_adv(v, fillna=0).isna().sum() == 0


# -------------------------------------------------------------- causality

_REAL = importlib.import_module("pandas_ta.volume.maxvol_adv")


def _load_mutant(old, new, tag):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType(f"_mva_mutant_{tag}")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


MUTANTS = {
    "peak": ("peak = volume.rolling(", "peak = volume.shift(-1).rolling("),
    "adv": ("adv = volume.rolling(", "adv = volume.shift(-1).rolling("),
}

OFFSETS = range(60, 1100, 34)  # 31 offsets


def _moved(a, b):
    if not (a.isna() == b.isna()).all():
        return True
    m = a.notna()
    return bool((a[m] != b[m]).any())


def _leaks(fn):
    """Count offsets `j` at which rewriting bars >= j moves any bar < j.

    A random rewrite of bar j can stay below the window's peak, which would
    hide a one-bar look-ahead in the max; the x1000 future cannot.
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
    assert _leaks(maxvol_adv) == 0


@pytest.mark.parametrize("tag", sorted(MUTANTS))
def test_mutant_is_caught(tag):
    mod = _load_mutant(*MUTANTS[tag], tag)
    v = _walk()
    assert not mod.maxvol_adv(v).equals(maxvol_adv(v))
    assert _leaks(mod.maxvol_adv) == len(OFFSETS)


# ------------------------------------------------------------ scale-free


@pytest.mark.parametrize("k", [8.0, 64.0])
def test_volume_scale_is_bit_identical(k):
    v = _walk()
    base, scaled = maxvol_adv(v), maxvol_adv(v * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_volume_scale_within_tolerance(k):
    v = _walk()
    base, scaled = maxvol_adv(v), maxvol_adv(v * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    # the bound the docstring and MaxvolAdvMeasured.md quote (measured 2.2e-16 / 3.9e-16)
    assert ((scaled[m] - base[m]).abs() / base[m].abs()).max() <= 4e-16


def test_column_is_not_constant():
    out = maxvol_adv(_walk())
    m = out.notna()
    assert int(m.sum()) == 1151 and out[m].nunique() == 1151
    assert 1.129 < out.min() < 1.13 and 7.357 < out.max() < 7.358


# ---------------------------------------------------------------- wiring


def test_name_registration_and_accessor():
    v = _walk(200)
    df = DataFrame({"open": 1.0, "high": 1.0, "low": 1.0, "close": 1.0, "volume": v})
    assert "maxvol_adv" in ta.Category["volume"]
    out = df.ta.maxvol_adv()
    assert out.name == "MAXVOLADV_14_50"
    pd.testing.assert_series_equal(out, maxvol_adv(v))
    assert df.ta.maxvol_adv(short=5, long=20).name == "MAXVOLADV_5_20"
