# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.momentum.g191_129` -- Guotai Junan's (2017,
"GTJA191") alpha `#129`, per issue #75: `SUM(C-C1<0 ? |C-C1| : 0, 12)`,
scale-free via `/close`, matching the issue's own prototype
(`docs/issues/screen/ind_screen.py:477-478`). Gate A derivation is in the
module docstring and `docs/G191129Measured.md`. Gate E is pending
(CLAUDE.md, "Owed, not failed").

What these tests pin, in order of how much it would hurt to lose:

* CAUSALITY by future-perturbation: rewrite every close bar from `j`
  onward (another synthetic walk), demand bars `[0:j]` bit-identical with
  matching NaN masks, over offsets past the 13-bar warm-up. Two mutants
  (`importlib` source read, `exec`'d in memory), each shown live (differs
  from the real module) then caught at every offset: shifting the final
  write index `length=12` bars into the future, and computing the rolling
  sum with `rolling(length, center=True)` instead of the causal trailing
  window -- the same `bos` look-ahead bug class CLAUDE.md documents.
* CORRECTNESS: a hand-derived example at `length=3`, checked bar by bar,
  plus a spot check at the shipped default against an independent per-bar
  computation using plain numpy array slicing, not the module's own
  `.rolling()` calls. Also pins that `(-delta).clip(lower=0)` and an
  explicit `np.where(delta < 0, -delta, 0.0)` ternary agree bit-for-bit,
  including at the `delta == 0` boundary.
* SCALE-FREE: bit-identical under close x8/x64 (power-of-two, exact in
  IEEE754), within float64 tolerance under x10/x3.7. Matching NaN masks,
  plus `0 < fires < n` and `nunique > 1`.
* Wiring: `Category`, the accessor, the column name `G191_129_12`.
"""
import importlib
import types

import numpy as np
import pandas as pd
import pytest
from pandas import Series

from .context import pandas_ta as ta
from pandas_ta.momentum.g191_129 import g191_129


def _walk(n=1500, seed=11, sigma=0.015):
    rng = np.random.default_rng(seed)
    close = 100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n)))
    return Series(close, index=pd.RangeIndex(n))


# ------------------------------------------------------------ correctness


def test_hand_derived_six_bars():
    """length=3.

    close  = [10, 12, 9, 15, 7, 20]
    C1     = [nan, 10, 12, 9, 15, 7]
    delta  = [nan, 2, -3, 6, -8, 13]
    down   = [nan, 0, 3, 0, 8, 0]   (-delta, clip(lower=0), bar 0 NaN)
    SUM (rolling, length=3):
        t=0,1: NaN (window touches the NaN bar 0)
        t=2: sum([nan,0,3]) -> NaN (still touches bar 0)
        t=3: sum([0,3,0]) = 3
        t=4: sum([3,0,8]) = 11
        t=5: sum([0,8,0]) = 8
    result[3] = 3/15, result[4] = 11/7, result[5] = 8/20
    """
    close = Series([10.0, 12.0, 9.0, 15.0, 7.0, 20.0])

    out = g191_129(close, length=3)

    assert out.iloc[:3].isna().all()
    assert out.iloc[3] == pytest.approx(3.0 / 15.0, abs=1e-12)
    assert out.iloc[4] == pytest.approx(11.0 / 7.0, abs=1e-12)
    assert out.iloc[5] == pytest.approx(8.0 / 20.0, abs=1e-12)


def test_matches_an_independent_loop_at_defaults():
    """Spot-checks 3 bars of the shipped default (length=12) against an
    independent per-bar computation using plain numpy array slicing, not
    pandas' own `.rolling()` calls."""
    close = _walk(900, seed=5)
    out = g191_129(close)
    c = close.to_numpy(dtype=float)
    length = 12

    def expected_at(t):
        idx = np.arange(t - length + 1, t + 1)  # all >= 1 since t >= length
        delta = c[idx] - c[idx - 1]
        down = np.maximum(-delta, 0.0)
        return np.sum(down) / c[t]

    for t in (300, 600, 899):
        assert out.iloc[t] == pytest.approx(expected_at(t), rel=1e-9)


def test_clip_matches_an_explicit_ternary_at_the_zero_boundary():
    """The issue's ternary is `C-C1<0 ? |C-C1| : 0`; the module uses
    `(-delta).clip(lower=0)`. These two are mathematically identical at
    every bar, including EXACTLY where `delta == 0` (both give `0`).
    Pinned with a close series that holds flat for one bar (`delta[2] ==
    0` exactly)."""
    close = Series([10.0, 12.0, 12.0, 15.0, 9.0])
    delta = close.diff()

    via_clip = (-delta).clip(lower=0)
    via_ternary = pd.Series(
        np.where(delta < 0, -delta, 0.0), index=close.index
    ).where(delta.notna())

    assert delta.iloc[2] == 0.0  # the boundary bar actually exercised
    pd.testing.assert_series_equal(via_clip, via_ternary, check_names=False)


def test_insufficient_history_returns_none():
    close = _walk(12)  # defaults need length + 1 = 13 bars
    assert g191_129(close) is None


def test_exact_min_length_fires_at_the_warmup_boundary():
    close = _walk(13)  # exactly length + 1 = 13 bars
    out = g191_129(close)
    assert out is not None
    assert out.iloc[:12].isna().all()
    assert pd.notna(out.iloc[12])


def test_default_name():
    close = _walk()
    out = g191_129(close)
    assert out.name == "G191_129_12"


def test_distinct_lengths_produce_distinct_names_and_values():
    close = _walk(400)
    out1 = g191_129(close, length=10)
    out2 = g191_129(close, length=15)
    assert out1.name != out2.name
    assert out1.name == "G191_129_10"
    assert out2.name == "G191_129_15"
    m = out1.notna() & out2.notna()
    assert (out1[m] != out2[m]).any()


# -------------------------------------------------------------- causality


_REAL = importlib.import_module("pandas_ta.momentum.g191_129")


def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_g191_129_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


WRITE_SHIFT_MUTANT = (
    "result = down.rolling(length, min_periods=length).sum() / close",
    "result = (down.rolling(length, min_periods=length).sum() / close).shift(-length)",
)
CENTERED_SUM_MUTANT = (
    "result = down.rolling(length, min_periods=length).sum() / close",
    "result = down.rolling(length, center=True, min_periods=length).sum() / close",  # the `bos` look-ahead bug class
)

OFFSETS = range(150, 1500, 40)  # past the 13-bar warm-up


def _leaks(fn):
    close = _walk(1500)
    other_c = _walk(1500, seed=97)
    base = fn(close)
    hits = 0
    for j in OFFSETS:
        pc = close.copy()
        pc.iloc[j:] = other_c.iloc[j:].values
        out = fn(pc)
        a, b = base.iloc[:j], out.iloc[:j]
        if not (a.isna() == b.isna()).all():
            hits += 1
            continue
        m = a.notna()
        if (a[m] != b[m]).any():
            hits += 1
    return hits


def test_real_module_never_reads_the_future():
    assert _leaks(g191_129) == 0


def test_write_shift_mutant_is_caught():
    mod = _load_mutant(*WRITE_SHIFT_MUTANT)
    close = _walk(1500)
    assert not mod.g191_129(close).equals(g191_129(close))  # live
    assert _leaks(mod.g191_129) == len(list(OFFSETS))  # caught, every offset


def test_centered_sum_mutant_is_caught():
    mod = _load_mutant(*CENTERED_SUM_MUTANT)
    close = _walk(1500)
    assert not mod.g191_129(close).equals(g191_129(close))  # live
    assert _leaks(mod.g191_129) == len(list(OFFSETS))  # caught, every offset


# ------------------------------------------------------------ reachability


def test_fires_on_a_non_trivial_fraction():
    close = _walk()  # 1500 bars, defaults
    out = g191_129(close)
    fires = int(out.notna().sum())
    assert fires > 1400


def test_fires_and_is_not_constant():
    close = _walk()
    out = g191_129(close)
    fires = int(out.notna().sum())
    assert 0 < fires < len(out)
    assert out.dropna().nunique() > 100


# ------------------------------------------------------------ scale-free


@pytest.mark.parametrize("k", [8.0, 64.0])
def test_power_of_two_price_scale_is_bit_identical(k):
    close = _walk()
    base = g191_129(close)
    scaled = g191_129(close * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_other_price_scales_within_tolerance(k):
    close = _walk()
    base = g191_129(close)
    scaled = g191_129(close * k)
    assert (base.isna() == scaled.isna()).all()
    assert (base - scaled).abs().max() < 1e-9


def test_fires_and_is_not_constant_also_bounded_nonnegative():
    close = _walk()
    out = g191_129(close).dropna()
    assert (out >= 0.0).all()


# ---------------------------------------------------------------- wiring


def test_name_registration_and_accessor():
    close = _walk(400)
    df = pd.DataFrame({"open": close, "high": close, "low": close, "close": close})
    assert "g191_129" in ta.Category["momentum"]
    out = df.ta.g191_129()
    assert out.name == "G191_129_12"
    pd.testing.assert_series_equal(out, g191_129(close))
    # tunable kwarg forwarded under its own name -- the "supertrend
    # failure mode" (CLAUDE.md) hasattr cannot see.
    renamed = df.ta.g191_129(length=10)
    assert renamed.name == "G191_129_10"
