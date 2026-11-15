# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.volume.g191_043` -- Guotai Junan's (2017, "GTJA191")
alpha `#43`, per issue #69: `SUM(C>C1 ? V : (C<C1 ? -V : 0), 6) / SUM(V, 6)`
(the issue's own scale-free form, "/SUM(V,6)"). Gate A derivation is in the
module docstring and `docs/G191043Measured.md`. Gate E is pending (CLAUDE.md,
"Owed, not failed").

What these pin, in order of how much it would hurt to lose:

* CAUSALITY by future-perturbation: rewrite every close/volume bar from `j`
  onward (another synthetic walk), demand bars `[0:j]` bit-identical with
  matching NaN masks, over offsets past the 6-bar warm-up. One mutant
  (`importlib` source read, `exec`'d in memory, the final write index
  shifted `length` bars into the future) is shown live (differs from the
  real module) then caught at every offset.
* CORRECTNESS: a 9-bar hand-derived example at `length=3` (including a
  flat-day boundary bar, `delta == 0`), checked against an independent
  per-bar computation. A second spot check at the shipped default
  (`length=6`) against an independent per-bar loop using plain numpy.
* SCALE-FREE: VOLUME x8/x64 bit-identical, x10/x3.7 within tolerance (the
  `k` cancels inside the ratio of two linear sums, for ANY `k > 0`); PRICE
  x8/x64/x10/x3.7 ALL bit-identical (only the SIGN of a price difference is
  read, never its magnitude) -- plus `0 < fires < n` and `nunique > 1`.
* Wiring: `Category`, the accessor, the column name `G191_043_6`.
"""
import importlib
import types

import numpy as np
import pandas as pd
import pytest
from pandas import Series

from .context import pandas_ta as ta
from pandas_ta.volume.g191_043 import g191_043
from pandas_ta.utils import signed_series


def _walk(n=900, seed=11, lo=50.0, hi=150.0):
    """Synthetic close-price random walk."""
    rng = np.random.default_rng(seed)
    steps = rng.normal(0, 1.5, n)
    close = lo + np.abs(np.cumsum(steps)) % (hi - lo)
    return Series(close)


def _volume(n=900, seed=97, lo=1e4, hi=1e6):
    rng = np.random.default_rng(seed)
    return Series(rng.uniform(lo, hi, n))


# ------------------------------------------------------------ correctness


def test_hand_derived_nine_bars():
    """length=3: G191_043 = SUM(SIGN(C-C1)*V, 3) / SUM(V, 3).

    close  = [100, 105, 103, 103, 108, 95, 110, 100, 120]
    volume = [ 10,  20,  30,  40,  50, 60,  70,  80,  90]
    diffs (bar vs prior): NaN, +5, -2, 0, +5, -13, +15, -10, +20
    signs:                 NaN, +1, -1, 0, +1,  -1,  +1,  -1,  +1
    signed_vol:            NaN, 20, -30, 0, 50, -60,  70, -80,  90

    bar3: sum(20,-30,0)/sum(20,30,40)   = -10/90  = -0.111111...
    bar4: sum(-30,0,50)/sum(30,40,50)   =  20/120 =  0.166667
    bar5: sum(0,50,-60)/sum(40,50,60)   = -10/150 = -0.066667
    bar6: sum(50,-60,70)/sum(50,60,70)  =  60/180 =  0.333333
    bar7: sum(-60,70,-80)/sum(60,70,80) = -70/210 = -0.333333
    bar8: sum(70,-80,90)/sum(70,80,90)  =  80/240 =  0.333333
    Derived by hand, not by re-running the module. Bar3 exercises the
    flat-day (delta == 0) boundary inside the summed window.
    """
    close = Series([100.0, 105.0, 103.0, 103.0, 108.0, 95.0, 110.0, 100.0, 120.0])
    volume = Series([10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0])
    out = g191_043(close, volume, length=3)

    assert out.iloc[:3].isna().all()
    expected = {
        3: -10 / 90, 4: 20 / 120, 5: -10 / 150,
        6: 60 / 180, 7: -70 / 210, 8: 80 / 240,
    }
    for t, val in expected.items():
        assert out.iloc[t] == pytest.approx(val, abs=1e-9), f"bar {t}"


def test_matches_an_independent_loop_at_defaults():
    """Spot-checks 3 bars of the shipped default (length=6) against an
    independent per-bar computation using plain numpy slicing, not the
    module's own `.rolling()`/`signed_series` calls."""
    close = _walk(900, seed=5)
    volume = _volume(900, seed=13)
    out = g191_043(close, volume)
    c = close.to_numpy(dtype=float)
    v = volume.to_numpy(dtype=float)
    length = 6

    def expected_at(t):
        num = 0.0
        den = 0.0
        for i in range(t - length + 1, t + 1):
            sign = 1.0 if c[i] > c[i - 1] else (-1.0 if c[i] < c[i - 1] else 0.0)
            num += sign * v[i]
            den += v[i]
        return num / den

    for t in (300, 600, 899):
        assert out.iloc[t] == pytest.approx(expected_at(t), rel=1e-9)


def test_signed_series_matches_an_explicit_sign_ternary_at_the_zero_boundary():
    """Pins that `pandas_ta.utils.signed_series(close)` -- used inside
    `g191_043` -- reproduces the issue's own `C>C1 ? +1 : (C<C1 ? -1 : 0)`
    ternary exactly, including the `delta == 0` flat-day boundary, on a
    dedicated 5-bar frame built to hold one bar exactly flat."""
    close = Series([100.0, 105.0, 105.0, 95.0, 95.0])  # up, flat, down, flat
    got = signed_series(close)
    delta = close.diff()
    explicit = Series(np.sign(delta.to_numpy()))
    assert got.iloc[0] is None or pd.isna(got.iloc[0])
    assert pd.isna(explicit.iloc[0])
    pd.testing.assert_series_equal(
        got.iloc[1:].astype(float), explicit.iloc[1:].astype(float),
        check_names=False, check_index_type=False,
    )


def test_insufficient_history_returns_none():
    close = _walk(6)  # defaults need length + 1 = 7 bars
    volume = _volume(6)
    assert g191_043(close, volume) is None


def test_exact_min_length_fires_at_the_warmup_boundary():
    close = _walk(7)  # exactly length + 1 = 7 bars
    volume = _volume(7)
    out = g191_043(close, volume)
    assert out is not None
    assert out.iloc[:6].isna().all()
    assert pd.notna(out.iloc[6])


def test_default_name():
    close = _walk()
    volume = _volume()
    out = g191_043(close, volume)
    assert out.name == "G191_043_6"


def test_distinct_lengths_produce_distinct_names_and_values():
    close = _walk(300)
    volume = _volume(300)
    out1 = g191_043(close, volume, length=6)
    out2 = g191_043(close, volume, length=12)
    assert out1.name != out2.name
    assert out1.name == "G191_043_6"
    assert out2.name == "G191_043_12"
    m = out1.notna() & out2.notna()
    assert (out1[m] != out2[m]).any()


def test_offset_shifts_the_series():
    close = _walk(200)
    volume = _volume(200)
    base = g191_043(close, volume)
    shifted = g191_043(close, volume, offset=1)
    pd.testing.assert_series_equal(shifted, base.shift(1), check_names=False)


def test_result_is_bounded_in_minus_one_to_one():
    """A sum of signed volume cannot exceed the sum of its own unsigned
    magnitude, so the ratio must lie in [-1, 1] wherever it fires."""
    close = _walk()
    volume = _volume()
    out = g191_043(close, volume)
    fired = out.dropna()
    assert (fired >= -1.0 - 1e-9).all()
    assert (fired <= 1.0 + 1e-9).all()


# -------------------------------------------------------------- causality


_REAL = importlib.import_module("pandas_ta.volume.g191_043")


def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_g191_043_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


WRITE_SHIFT_MUTANT = (
    "result = (numerator / denominator).replace([np.inf, -np.inf], np.nan)",
    "result = (numerator / denominator).replace([np.inf, -np.inf], np.nan).shift(-length)",  # a length-bar look-ahead
)

OFFSETS = range(50, 900, 25)  # past the 6-bar warm-up


def _leaks(fn):
    close = _walk(900)
    volume = _volume(900)
    other_close = _walk(900, seed=41)
    other_volume = _volume(900, seed=59)
    base = fn(close, volume)
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
    assert _leaks(g191_043) == 0


def test_write_shift_mutant_is_caught():
    mod = _load_mutant(*WRITE_SHIFT_MUTANT)
    close = _walk(900)
    volume = _volume(900)
    assert not mod.g191_043(close, volume).equals(g191_043(close, volume))  # live
    assert _leaks(mod.g191_043) == len(list(OFFSETS))  # caught, every offset


# ------------------------------------------------------------ scale-free


@pytest.mark.parametrize("k", [8.0, 64.0])
def test_power_of_two_volume_scale_is_bit_identical(k):
    close = _walk()
    volume = _volume()
    base = g191_043(close, volume)
    scaled = g191_043(close, volume * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_other_volume_scales_within_tolerance(k):
    close = _walk()
    volume = _volume()
    base = g191_043(close, volume)
    scaled = g191_043(close, volume * k)
    assert (base.isna() == scaled.isna()).all()
    assert (base - scaled).abs().max() < 1e-9


@pytest.mark.parametrize("k", [8.0, 64.0, 10.0, 3.7])
def test_any_price_scale_is_bit_identical(k):
    """Only the SIGN of a one-bar price difference is read, never its
    magnitude, so even a non-power-of-two price rescale is exact (unlike
    the volume case, where the arithmetic itself, not just the ratio, is
    scale-invariant only at powers of two)."""
    close = _walk()
    volume = _volume()
    base = g191_043(close, volume)
    scaled = g191_043(close * k, volume)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] == scaled[m]).all()


def test_fires_and_is_not_constant():
    close = _walk()
    volume = _volume()
    out = g191_043(close, volume)
    fires = int(out.notna().sum())
    assert fires == 894  # 900 - 6
    assert 0 < fires < len(out)
    assert out.dropna().nunique() > 1


# ---------------------------------------------------------------- wiring


def test_name_registration_and_accessor():
    close = _walk(200)
    volume = _volume(200)
    df = pd.DataFrame({"open": close, "high": close, "low": close,
                        "close": close, "volume": volume})
    assert "g191_043" in ta.Category["volume"]
    out = df.ta.g191_043()
    assert out.name == "G191_043_6"
    pd.testing.assert_series_equal(out, g191_043(close, volume))
    renamed = df.ta.g191_043(length=12)
    assert renamed.name == "G191_043_12"
