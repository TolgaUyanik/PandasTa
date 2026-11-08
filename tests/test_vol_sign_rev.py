# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.volume.vol_sign_rev` -- Alpha#12 of Kakushadze's "101
Formulaic Alphas" (2016, Wilmott), restated by issue #43 and
`docs/issues/screen/candidates.csv` (candidate `a101_012`) as
`sign(delta(volume,1)) * -delta(close,1)`. Gate A disclosure (the paper/vnpy
source is unreachable in this worktree; the literal operator translation and
the issue's own scale-free substitution are taken as given) is in the module
docstring and `docs/VolSignRevMeasured.md`. Gate E is pending (CLAUDE.md,
"Owed, not failed").

What these pin, in order of how much it would hurt to lose:

* CAUSALITY by future-perturbation: rewrite every bar from `j` onward, VSR
  bars `[0:j]` bit-identical, over 45 offsets past the 1-bar warm-up. A
  look-ahead mutant (`importlib` source read, the return term's
  `close.shift(1)` switched to `close.shift(-1)` -- a 1-bar read into the
  future -- `exec`'d in memory) is proved live, then caught at 45 of 45.
* CORRECTNESS: a hand-derived 5-bar example (every term a plain diff/shift)
  plus an independent per-bar loop over a longer synthetic walk.
* SCALE-FREE: bit-identical under close x8/x64 and under volume x8/x64/x10/
  x3.7 (the sign of a diff is invariant to any positive scalar); within
  1e-9 under close x10/x3.7, matching NaN masks, plus `0 < fires < n`.
* Wiring: `Category`, the accessor, and the column name `VSR`.
"""
import importlib
import types

import numpy as np
import pandas as pd
import pytest
from pandas import Series

from .context import pandas_ta as ta
from pandas_ta.volume.vol_sign_rev import vol_sign_rev


def _walk(n=900, seed=17, sigma=0.015, vol_lo=1e4, vol_hi=1e6, vol_seed=23):
    rng = np.random.default_rng(seed)
    close = 100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n)))
    vrng = np.random.default_rng(vol_seed)
    volume = vrng.uniform(vol_lo, vol_hi, n)
    return Series(close), Series(volume)


# ------------------------------------------------------------ correctness


def test_hand_derived_five_bars():
    """close = [100, 110, 99, 150, 200], volume = [1000, 1200, 1100, 1100, 1300].

    delta(volume,1): NaN, 200, -100, 0, 200 -> sign: NaN, 1, -1, 0, 1
    ret = close/close.shift(1)-1: NaN, 0.10, -0.10, 150/99-1=17/33, 200/150-1=1/3
    VSR = sign * -ret:
        idx1: 1 * -0.10 = -0.10
        idx2: -1 * -(-0.10) = -0.10
        idx3: 0 * -(17/33) = 0.0
        idx4: 1 * -(1/3) = -1/3
    Derived by hand, not by re-running the module.
    """
    close = Series([100.0, 110.0, 99.0, 150.0, 200.0])
    volume = Series([1000.0, 1200.0, 1100.0, 1100.0, 1300.0])
    out = vol_sign_rev(close, volume)
    assert pd.isna(out.iloc[0])
    assert out.iloc[1] == pytest.approx(-0.10, abs=1e-12)
    assert out.iloc[2] == pytest.approx(-0.10, abs=1e-12)
    assert out.iloc[3] == pytest.approx(0.0, abs=1e-12)
    assert out.iloc[4] == pytest.approx(-1.0 / 3.0, abs=1e-12)


def test_matches_an_independent_per_bar_loop():
    close, volume = _walk(900, seed=5, vol_seed=31)
    out = vol_sign_rev(close, volume)

    c, v = close.values, volume.values
    for t in (1, 50, 400, 899):
        expected = np.sign(v[t] - v[t - 1]) * -(c[t] / c[t - 1] - 1)
        assert out.iloc[t] == pytest.approx(expected, rel=1e-9)


def test_insufficient_history_returns_none():
    assert vol_sign_rev(Series([100.0]), Series([1000.0])) is None


# -------------------------------------------------------------- causality


_REAL = importlib.import_module("pandas_ta.volume.vol_sign_rev")


def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_vol_sign_rev_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


MUTANT = (
    "ret = close / close.shift(1) - 1",
    "ret = close / close.shift(-1) - 1",  # 1-bar look-ahead
)

OFFSETS = range(5, 895, 20)  # 45 offsets, all past the 1-bar warm-up


def _leaks(fn):
    close, volume = _walk(900)
    base = fn(close, volume)
    other_close, other_volume = _walk(900, seed=99, vol_seed=101)
    hits = 0
    for j in OFFSETS:
        pc, pv = close.copy(), volume.copy()
        pc.iloc[j:] = other_close.iloc[j:].values
        pv.iloc[j:] = other_volume.iloc[j:].values
        out = fn(pc, pv)
        a, b = base.iloc[:j], out.iloc[:j]
        if not (a.isna() == b.isna()).all():
            hits += 1
            continue
        m = a.notna()
        if (a[m] != b[m]).any():
            hits += 1
    return hits


def test_real_module_never_reads_the_future():
    assert _leaks(vol_sign_rev) == 0


def test_mutant_is_caught():
    mod = _load_mutant(*MUTANT)
    close, volume = _walk(900)
    assert not mod.vol_sign_rev(close, volume).equals(vol_sign_rev(close, volume))  # live
    assert _leaks(mod.vol_sign_rev) == len(OFFSETS)  # caught, 45 of 45


# ------------------------------------------------------------ scale-free


@pytest.mark.parametrize("k", [8.0, 64.0])
def test_power_of_two_price_scale_is_bit_identical(k):
    close, volume = _walk(900)
    base = vol_sign_rev(close, volume)
    scaled = vol_sign_rev(close * k, volume)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_other_price_scales_within_tolerance(k):
    close, volume = _walk(900)
    base = vol_sign_rev(close, volume)
    scaled = vol_sign_rev(close * k, volume)
    assert (base.isna() == scaled.isna()).all()
    assert (base - scaled).abs().max() < 1e-9


@pytest.mark.parametrize("k", [8.0, 64.0, 10.0, 3.7])
def test_any_positive_volume_scale_is_bit_identical(k):
    """sign(k * diff) == sign(diff) for any k > 0 -- exact, not just at
    powers of two, since np.sign only reads the sign bit."""
    close, volume = _walk(900)
    base = vol_sign_rev(close, volume)
    scaled = vol_sign_rev(close, volume * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] == scaled[m]).all()


def test_fires_and_is_not_constant():
    close, volume = _walk(900)
    out = vol_sign_rev(close, volume)
    fires = int(out.notna().sum())
    assert 0 < fires < len(out)
    assert out.dropna().nunique() > 100


# ---------------------------------------------------------------- wiring


def test_name_registration_and_accessor():
    close, volume = _walk(900)
    df = pd.DataFrame({"open": close, "high": close, "low": close,
                       "close": close, "volume": volume})
    assert "vol_sign_rev" in ta.Category["volume"]
    out = df.ta.vol_sign_rev()
    assert out.name == "VSR"
    pd.testing.assert_series_equal(out, vol_sign_rev(close, volume))
