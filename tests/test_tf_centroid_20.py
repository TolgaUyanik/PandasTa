# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.statistics.tf_centroid_20` -- the energy-weighted
mean position (0..1) of the last `length` bars' squared simple returns.
Source: TSFEL `calc_centroid` (BSD-3-Clause). Measurements and the open
gates are in `docs/TfCentroid20Measured.md`.

What these tests pin, in order of how much it would hurt to lose them:

* CAUSALITY by future-perturbation: rewrite every close bar from `j`
  onward (another walk, a x1000 future), demand bars `[0:j]` bit-identical
  with matching NaN masks, over 31 offsets. A one-bar look-ahead mutant
  (`importlib` source read, `close` shifted forward before `pct_change`,
  `exec`'d in memory) is proved live, then caught at 31 of 31.
* SCALE-FREE: the signal is `close.pct_change(fill_method=None)`, a
  ratio, so a uniform
  price rescaling cancels before squaring; on the seed-11 walk, price x8
  and x64 are bit-identical, x10 and x3.7 agree within tolerance, NaN
  masks matching. Not constant: 1,180 distinct values over the 1,180
  non-warm-up bars (min/max/mean/median pinned too).
* ZERO-ENERGY window (all-zero returns) reads NaN, never 0 (TSFEL's own
  zero-division fallback is not carried: this fork never emits a magic 0
  for an undefined ratio).
* CORRECTNESS against an independent loop written from the TSFEL formula,
  a hand-computed sequence, the `length`-bar warm-up, a NaN close bar
  blanking itself and the next `length` bars, `offset`, `fillna`.
* Wiring: `Category`, the accessor, the column name `TFCENTROID_20`.
"""
import importlib
import types

import numpy as np
import pandas as pd
import pytest
from pandas import DataFrame, Series

from .context import pandas_ta as ta
from pandas_ta.statistics.tf_centroid_20 import tf_centroid_20


def _walk(n=1200, seed=11, s0=100.0, sigma=0.02):
    """Synthetic GBM-like close series, tick-rounded to 2dp like a real price."""
    rng = np.random.default_rng(seed)
    rets = rng.normal(0.0, sigma, n)
    px = s0 * np.cumprod(1.0 + rets)
    return Series(np.round(px, 2))


# ------------------------------------------------------------ correctness


def test_hand_computed():
    # length=4: t = [0, 1/3, 2/3, 1]
    c = Series([10.0, 11.0, 9.0, 9.9, 11.0])
    out = tf_centroid_20(c, length=4)
    r = c.pct_change(fill_method=None).to_numpy()
    t = np.array([0.0, 1 / 3, 2 / 3, 1.0])
    sq = r[1:5] ** 2
    expected = (sq * t).sum() / sq.sum()
    assert out.isna().tolist() == [True] * 4 + [False]
    assert out.iloc[4] == pytest.approx(expected)


def test_matches_an_independent_loop():
    c = _walk()
    v = c.to_numpy(dtype=float)
    r = c.pct_change(fill_method=None).to_numpy(dtype=float)
    length = 20
    ref = np.full(len(v), np.nan)
    for i in range(length, len(v)):
        window = r[i - length + 1:i + 1]
        t = np.arange(length, dtype=float) / (length - 1)
        energy = (window ** 2).sum()
        if energy > 0:
            ref[i] = (t * window ** 2).sum() / energy
    out = tf_centroid_20(c)
    assert (np.isnan(ref) == out.isna().values).all()
    np.testing.assert_allclose(out.values[length:], ref[length:], rtol=1e-12)


def test_zero_energy_window_is_nan_not_zero():
    # length consecutive identical closes -> all-zero returns -> zero energy
    c = Series([5.0] * 10 + [5.5, 5.4, 5.6, 5.3])
    out = tf_centroid_20(c, length=5)
    # bars 5..9 (0-indexed) are windows entirely inside the flat run
    assert out.iloc[5:10].isna().all()
    # once a non-flat return enters the window, energy > 0
    assert np.isfinite(out.iloc[10:]).all()


def test_warmup_and_nan_propagation():
    c = _walk()
    base = tf_centroid_20(c)
    assert int(base.isna().sum()) == 20
    cn = c.copy()
    cn[500] = np.nan
    gap = tf_centroid_20(cn)
    # one NaN close blanks its own return and the next `length` returns,
    # i.e. `length + 1` tainted centroid windows (the window at the gap's
    # own bar, plus `length - 1` windows still containing it, plus the one
    # extra from the NaN return at 501).
    assert gap.iloc[500:521].isna().all()
    assert gap.iloc[521:].notna().all()


def test_offset_and_fillna():
    c = _walk(300)
    base = tf_centroid_20(c)
    pd.testing.assert_series_equal(tf_centroid_20(c, offset=1), base.shift(1))
    assert tf_centroid_20(c, fillna=0).isna().sum() == 0


def test_bounded_0_1():
    out = tf_centroid_20(_walk())
    m = out.notna()
    assert (out[m] >= 0.0).all() and (out[m] <= 1.0).all()


# -------------------------------------------------------------- causality

_REAL = importlib.import_module("pandas_ta.statistics.tf_centroid_20")


def _load_mutant(old, new, tag):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType(f"_tfc_mutant_{tag}")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


MUTANTS = {
    "lookahead": (
        "r = close.pct_change(fill_method=None).to_numpy(dtype=float)",
        "r = close.shift(-1).pct_change(fill_method=None).to_numpy(dtype=float)",
    ),
}

OFFSETS = range(60, 1100, 34)  # 31 offsets


def _moved(a, b):
    if not (a.isna() == b.isna()).all():
        return True
    m = a.notna()
    return bool((a[m] != b[m]).any())


def _leaks(fn):
    """Count offsets `j` at which rewriting bars >= j moves any bar < j."""
    c = _walk()
    base = fn(c)
    other = _walk(seed=99)
    hits = 0
    for j in OFFSETS:
        for future in (other.iloc[j:].values, c.iloc[j:].values * 1000.0):
            pc = c.copy()
            pc.iloc[j:] = future
            if _moved(base.iloc[:j], fn(pc).iloc[:j]):
                hits += 1
                break
    return hits


def test_real_module_never_reads_the_future():
    assert _leaks(tf_centroid_20) == 0


@pytest.mark.parametrize("tag", sorted(MUTANTS))
def test_mutant_is_caught(tag):
    mod = _load_mutant(*MUTANTS[tag], tag)
    c = _walk()
    assert not mod.tf_centroid_20(c).equals(tf_centroid_20(c))
    assert _leaks(mod.tf_centroid_20) == len(OFFSETS)


# ------------------------------------------------------------ scale-free


@pytest.mark.parametrize("k", [8.0, 64.0])
def test_price_scale_is_bit_identical(k):
    c = _walk()
    base, scaled = tf_centroid_20(c), tf_centroid_20(c * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_price_scale_within_tolerance(k):
    c = _walk()
    base, scaled = tf_centroid_20(c), tf_centroid_20(c * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna() & (base.abs() > 0)
    # measured 6.633e-15 (x10) / 6.076e-15 (x3.7) on this walk
    assert ((scaled[m] - base[m]).abs() / base[m].abs()).max() <= 1e-13


def test_column_is_not_constant():
    out = tf_centroid_20(_walk())
    m = out.notna()
    assert int(m.sum()) == 1180
    # pins the exact figures quoted in docs/TfCentroid20Measured.md's Gate C row
    assert int(out[m].nunique()) == 1180
    assert out[m].min() == pytest.approx(0.22703367476493705)
    assert out[m].max() == pytest.approx(0.7639855682057195)
    assert out[m].mean() == pytest.approx(0.5007277309366513)
    assert out[m].median() == pytest.approx(0.5015225423847335)


# ---------------------------------------------------------------- wiring


def test_name_registration_and_accessor():
    c = _walk(200)
    df = DataFrame({"open": 1.0, "high": 1.0, "low": 1.0, "close": c, "volume": 1.0})
    assert "tf_centroid_20" in ta.Category["statistics"]
    out = df.ta.tf_centroid_20()
    assert out.name == "TFCENTROID_20"
    pd.testing.assert_series_equal(out, tf_centroid_20(c))
    assert df.ta.tf_centroid_20(length=10).name == "TFCENTROID_10"
