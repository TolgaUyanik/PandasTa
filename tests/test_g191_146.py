# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.momentum.g191_146` -- Guotai Junan's (2017,
"GTJA191") alpha `#146`, per issue #52: `MEAN(r - SMA(r,61,2), 20) * (r -
SMA(r,61,2)) / SMA((r - SMA(r,61,2))^2, 60, 2)`, where `r` is the daily
simple return and `SMA(A,n,m)` is GTJA's own recursive EMA (`alpha =
m/n`), not this fork's plain simple-moving-average `sma`. Gate A derivation
is in the module docstring and `docs/G191146Measured.md`. Gate E is pending
(CLAUDE.md, "Owed, not failed").

What these pin, in order of how much it would hurt to lose:

* CAUSALITY by future-perturbation: rewrite every close bar from `j`
  onward (another synthetic walk), demand bars `[0:j]` bit-identical with
  matching NaN masks, over offsets past the 120-bar warm-up. Two mutants
  (`importlib` source read, `exec`'d in memory), each shown live (differs
  from the real module) then caught at every offset: shifting the final
  write index `smooth2_length=60` bars into the future, and computing
  `MEAN(e, mean_length)` with `center=True` (`python docs/measure_g191_146.py`).
* CORRECTNESS: an 8-bar hand-derived example at `smooth1_length=3,
  smooth1_weight=1, mean_length=2, smooth2_length=2, smooth2_weight=1`,
  replayed independently with Python's exact `fractions.Fraction` (no
  floats, no pandas `.ewm()`/`.rolling()`) in `docs/measure_g191_146.py`,
  matching the module's float64 output to ~1e-15. A second spot-check at
  the shipped defaults against an independent per-bar loop written in
  plain Python, looping the GTJA recursion from bar 0 rather than calling
  pandas' own `.ewm()`.
* SCALE-FREE: `r = close/close.shift(1) - 1` is exactly invariant under a
  positive rescale of `close` (the scale cancels algebraically), so the
  whole column is bit-identical under close x8/x64 (power-of-two, exact in
  IEEE754), and within `~1e-14` (float64 rounding, not a scale dependency)
  under x10/x3.7. Matching NaN masks, plus `0 < fires < n` and
  `nunique > 1`.
* Wiring: `Category`, the accessor, the column name
  `G191_146_61_2_20_60_2`.
"""
import importlib
import types

import numpy as np
import pandas as pd
import pytest
from pandas import Series

from .context import pandas_ta as ta
from pandas_ta.momentum.g191_146 import g191_146


def _walk(n=1500, seed=11, sigma=0.015):
    rng = np.random.default_rng(seed)
    close = 100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n)))
    return Series(close, index=pd.RangeIndex(n))


# ------------------------------------------------------------ correctness


def test_hand_derived_eight_bars():
    """close = [10, 11, 9, 12, 8, 14, 7, 16],
    smooth1_length=3, smooth1_weight=1, mean_length=2, smooth2_length=2,
    smooth2_weight=1 (alpha1 = 1/3, alpha2 = 1/2).

    r[t] = close[t]/close[t-1] - 1, valid t>=1:
      r = [-, 0.1, -2/11, 1/3, -1/3, 0.75, -0.5, 9/7]

    s1[t] = GTJA SMA(r, 3, 1): y1=r[1]; y[t]=(1/3)*r[t]+(2/3)*y[t-1].
    Masked (min_periods=3) until t=3:
      s1[3]=0.1151515..., s1[4]=-0.0343434..., s1[5]=0.2271043...,
      s1[6]=-0.0152637..., s1[7]=0.4183955...

    e[t] = r[t] - s1[t], valid t>=3:
      e[3]=0.2181818, e[4]=-0.2989898, e[5]=0.5228956, e[6]=-0.4847362,
      e[7]=0.8673186

    m20[t] = MEAN(e, 2), valid t>=4:
      m20[4]=-0.0404040, m20[5]=0.1119528, m20[6]=0.0190796, m20[7]=0.1912912

    s2[t] = GTJA SMA(e^2, 2, 1): z=e[3]^2; z=(1/2)*e[t]^2+(1/2)*z.
    Masked (min_periods=2) until t=4:
      s2[4]=0.0684991, s2[5]=0.1709594, s2[6]=0.2029643, s2[7]=0.4776030

    result[t] = m20[t]*e[t]/s2[t], valid t>=4 (first_valid_index =
      smooth1_length + max(mean_length, smooth2_length) - 1 = 3 + 2 - 1 = 4):
      result[4]=0.176358, result[5]=0.342418, result[6]=-0.045568,
      result[7]=0.347381

    Replayed exactly with `fractions.Fraction` (no floats) in
    docs/measure_g191_146.py, matching the module's float64 output here to
    ~1e-15: exact bars 3..7 = [None, 0.17635843660629172,
    0.34241833560839685, -0.04556768211615564, 0.34738148161854115].
    """
    close = Series([10.0, 11.0, 9.0, 12.0, 8.0, 14.0, 7.0, 16.0])
    out = g191_146(close, smooth1_length=3, smooth1_weight=1, mean_length=2,
                    smooth2_length=2, smooth2_weight=1)

    assert out.iloc[:4].isna().all()
    expected = {
        4: 0.17635843660629172,
        5: 0.34241833560839685,
        6: -0.04556768211615564,
        7: 0.34738148161854115,
    }
    for t, val in expected.items():
        assert out.iloc[t] == pytest.approx(val, abs=1e-9), f"bar {t}"


def test_matches_an_independent_loop_at_defaults():
    """Spot-checks 3 bars of the shipped defaults (smooth1_length=61,
    smooth1_weight=2, mean_length=20, smooth2_length=60, smooth2_weight=2)
    against a hand-written per-bar loop using plain Python, independent of
    the module's pandas `.ewm()` / `.rolling()` calls."""
    close = _walk(900, seed=3)
    out = g191_146(close)
    c = close.to_numpy(dtype=float)
    n = len(c)
    smooth1_length, smooth1_weight = 61, 2.0
    mean_length = 20
    smooth2_length, smooth2_weight = 60, 2.0
    a1 = smooth1_weight / smooth1_length
    a2 = smooth2_weight / smooth2_length

    r = [float("nan")] + [c[t] / c[t - 1] - 1.0 for t in range(1, n)]
    s1 = [float("nan")] * n
    y = None
    count1 = 0
    for t in range(1, n):
        y = r[t] if y is None else a1 * r[t] + (1 - a1) * y
        count1 += 1
        if count1 >= smooth1_length:
            s1[t] = y
    e = [r[t] - s1[t] if t >= 1 and s1[t] == s1[t] else float("nan") for t in range(n)]
    m20 = [float("nan")] * n
    for t in range(n):
        window = e[t - mean_length + 1:t + 1] if t - mean_length + 1 >= 0 else []
        if len(window) == mean_length and all(v == v for v in window):
            m20[t] = sum(window) / mean_length
    s2 = [float("nan")] * n
    z = None
    count2 = 0
    for t in range(n):
        if e[t] != e[t]:
            continue
        e2 = e[t] ** 2
        z = e2 if z is None else a2 * e2 + (1 - a2) * z
        count2 += 1
        if count2 >= smooth2_length:
            s2[t] = z

    def expected_at(t):
        return m20[t] * e[t] / s2[t]

    for t in (300, 600, 899):
        assert out.iloc[t] == pytest.approx(expected_at(t), rel=1e-9)


def test_insufficient_history_returns_none():
    close = _walk(120)  # defaults need 61 + max(20, 60) = 121 bars
    assert g191_146(close) is None


def test_exact_min_length_fires_at_the_warmup_boundary():
    close = _walk(121)  # exactly 61 + max(20, 60) = 121 bars
    out = g191_146(close)
    assert out is not None
    assert out.iloc[:120].isna().all()
    assert pd.notna(out.iloc[120])


def test_default_name():
    close = _walk()
    out = g191_146(close)
    assert out.name == "G191_146_61_2_20_60_2"


def test_distinct_weights_produce_distinct_names_and_values():
    """Pins the fix for the review finding that `smooth1_weight`/
    `smooth2_weight` are coerced to `int`: two distinct INTEGER weights
    MUST produce two distinct column names (the name is the only thing
    mined strategy rules in the parent repo match on, CLAUDE.md "Naming is
    API") and, since the weight changes the GTJA `alpha = m/n`, two
    distinct Series of values."""
    close = _walk(300)
    out1 = g191_146(close, smooth1_length=10, smooth1_weight=1, mean_length=5,
                     smooth2_length=10, smooth2_weight=1)
    out3 = g191_146(close, smooth1_length=10, smooth1_weight=3, mean_length=5,
                     smooth2_length=10, smooth2_weight=3)
    assert out1.name != out3.name
    assert out1.name == "G191_146_10_1_5_10_1"
    assert out3.name == "G191_146_10_3_5_10_3"
    m = out1.notna() & out3.notna()
    assert (out1[m] != out3[m]).any()


def test_fractional_weights_that_truncate_the_same_are_identical():
    """The actual regression this fix closes: round 1 shipped
    `smooth1_weight`/`smooth2_weight` stored as `float` for the `ewm()`
    math but truncated to `int` only at the name f-string, so
    `smooth1_weight=2.1` and `smooth1_weight=2.4` computed DIFFERENT
    Series (`alpha=2.1/length` vs `alpha=2.4/length`) under the IDENTICAL
    name (`int(2.1) == int(2.4) == 2`). The fix truncates at validation
    time, before any math runs, so two weights that truncate to the same
    integer are now the same parameter all the way through: same name AND
    bit-identical values. This assertion FAILS against the pre-fix code
    (where the values differ despite the equal names) and PASSES against
    the current one -- the one check round 1's own regression test did
    not provide (it only compared 1 vs 3, which never collided either way)."""
    close = _walk(300)
    out_21 = g191_146(close, smooth1_length=10, smooth1_weight=2.1, mean_length=5,
                       smooth2_length=10, smooth2_weight=2.1)
    out_24 = g191_146(close, smooth1_length=10, smooth1_weight=2.4, mean_length=5,
                       smooth2_length=10, smooth2_weight=2.4)
    assert out_21.name == out_24.name == "G191_146_10_2_5_10_2"
    pd.testing.assert_series_equal(out_21, out_24)


# -------------------------------------------------------------- causality


_REAL = importlib.import_module("pandas_ta.momentum.g191_146")


def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_g191_146_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


WRITE_SHIFT_MUTANT = (
    "result = result.where(mask)",
    "result = result.where(mask).shift(-smooth2_length)",  # a smooth2_length-bar look-ahead
)
CENTERED_MEAN_MUTANT = (
    "m20 = e.rolling(mean_length).mean()",
    "m20 = e.rolling(mean_length, center=True).mean()",  # the `bos` look-ahead bug class
)

OFFSETS = range(150, 1500, 40)  # past the 120-bar warm-up


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
    assert _leaks(g191_146) == 0


def test_write_shift_mutant_is_caught():
    mod = _load_mutant(*WRITE_SHIFT_MUTANT)
    close = _walk(1500)
    assert not mod.g191_146(close).equals(g191_146(close))  # live
    assert _leaks(mod.g191_146) == len(list(OFFSETS))  # caught, every offset


def test_centered_mean_mutant_is_caught():
    mod = _load_mutant(*CENTERED_MEAN_MUTANT)
    close = _walk(1500)
    assert not mod.g191_146(close).equals(g191_146(close))  # live
    assert _leaks(mod.g191_146) == len(list(OFFSETS))  # caught, every offset


# ------------------------------------------------------------ scale-free


@pytest.mark.parametrize("k", [8.0, 64.0])
def test_power_of_two_price_scale_is_bit_identical(k):
    close = _walk()
    base = g191_146(close)
    scaled = g191_146(close * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_other_price_scales_within_tolerance(k):
    close = _walk()
    base = g191_146(close)
    scaled = g191_146(close * k)
    assert (base.isna() == scaled.isna()).all()
    assert (base - scaled).abs().max() < 1e-9


def test_fires_and_is_not_constant():
    close = _walk()
    out = g191_146(close)
    fires = int(out.notna().sum())
    assert 0 < fires < len(out)
    assert out.dropna().nunique() > 1


# ---------------------------------------------------------------- wiring


def test_name_registration_and_accessor():
    close = _walk(400)
    df = pd.DataFrame({"open": close, "high": close, "low": close, "close": close})
    assert "g191_146" in ta.Category["momentum"]
    out = df.ta.g191_146()
    assert out.name == "G191_146_61_2_20_60_2"
    pd.testing.assert_series_equal(out, g191_146(close))
    # all five tunable kwargs forwarded under their own names in one call --
    # the "supertrend failure mode" (CLAUDE.md) hasattr cannot see.
    renamed = df.ta.g191_146(smooth1_length=10, smooth1_weight=1, mean_length=5,
                              smooth2_length=10, smooth2_weight=1)
    assert renamed.name == "G191_146_10_1_5_10_1"
