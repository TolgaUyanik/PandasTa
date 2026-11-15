# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.volatility.g191_160` -- Guotai Junan's (2017,
"GTJA191") alpha `#160`, per issue #67: `SMA(C<=C1 ? STD(C,20) : 0, 20, 1)`,
divided by close (`/close`, the issue's own scale-free conversion). On a
down-or-flat day the bar contributes its trailing rolling std of close, on
an up day it contributes zero; GTJA's own recursive `SMA` smooths that
series, and the result is divided by close. `SMA(A,n,m)` is GTJA's own
recursive EMA (`alpha = m/n`), not this fork's plain simple-moving-average
`sma`. Gate A derivation is in the module docstring and
`docs/G191160Measured.md`. Gate E is pending (CLAUDE.md, "Owed, not
failed").

What these pin, in order of how much it would hurt to lose:

* CAUSALITY by future-perturbation: rewrite every close bar from `j`
  onward (another synthetic walk), demand bars `[0:j]` bit-identical with
  matching NaN masks, over 34 offsets past the 38-bar warm-up. Two mutants
  (`importlib` source read, `exec`'d in memory), each shown live (differs
  from the real module) then caught at every offset: shifting the final
  write index `smooth_length=20` bars into the future, and computing
  `std_c` with `rolling(std_length, center=True)` (the `bos` look-ahead
  bug class).
* CORRECTNESS: an 8-bar hand-derived example at `std_length=3,
  smooth_length=3, smooth_weight=1`, checked against an independent
  per-bar computation of `STD`/the ternary/GTJA `SMA` (`python
  docs/measure_g191_160.py` prints the exact values). A second spot-check
  at the shipped defaults against an independent per-bar loop using plain
  numpy (`np.std(ddof=1)`), not pandas' own `.rolling()`/`.ewm()`.
* SCALE-FREE: the down/up-day branch choice (`C <= C1`) is invariant under
  a positive price rescale, and `STD`/GTJA `SMA` are both linear in a
  positive scalar multiple of their input, so the whole column is
  bit-identical under close x8/x64 (power-of-two, exact in IEEE754), and
  within float64 tolerance under x10/x3.7. Matching NaN masks, plus
  `0 < fires < n` and `nunique > 1`.
* Wiring: `Category`, the accessor, the column name
  `G191_160_20_20_1`.
"""
import importlib
import types

import numpy as np
import pandas as pd
import pytest
from pandas import Series

from .context import pandas_ta as ta
from pandas_ta.volatility.g191_160 import g191_160


def _walk(n=1500, seed=11, sigma=0.015):
    rng = np.random.default_rng(seed)
    close = 100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n)))
    return Series(close, index=pd.RangeIndex(n))


# ------------------------------------------------------------ correctness


def test_hand_derived_bars():
    """close = [10, 12, 9, 15, 7, 20, 5, 25], std_length=3, smooth_length=3,
    smooth_weight=1 (alpha = 1/3). min_length = std_length + smooth_length -
    1 = 5, so bars 0..3 are NaN and bars 4..7 are the first four valid
    values.

    C1[t] = close[t-1]. down-day iff close[t] <= C1[t]: bars 1,3,5,7 are
    up days (C1 < close), bars 2,4,6 are down days.
    std_c[t] = STDEV(close[t-2:t+1], ddof=1), valid t>=2:
      std_c[2..7] = [1.527525, 3.0, 4.163332, 6.557439, 8.144528, 10.408330]
    down_vol[t] = std_c[t] on a down day, else 0.0, masked to NaN where
    std_c is NaN:
      down_vol[2..7] = [1.527525, 0.0, 4.163332, 0.0, 8.144528, 0.0]
    GTJA SMA(down_vol, 3, 1): y = down_vol[2]; y[t] = (1/3)*down_vol[t] +
    (2/3)*y[t-1]. Masked (min_periods=3) until t=4:
      sma[4..7] = [2.066677, 1.377785, 3.633366, 2.422244]
    result[t] = sma[t] / close[t]:
      result[4..7] = [0.2952396337048347, 0.06888924786446143,
                      0.7266731819883688, 0.09688975759844919]

    Independently derived and printed by docs/measure_g191_160.py, matching
    the module's float64 output exactly (same arithmetic, no float-only
    tolerance needed for this particular example).
    """
    close = Series([10.0, 12.0, 9.0, 15.0, 7.0, 20.0, 5.0, 25.0])
    out = g191_160(close, std_length=3, smooth_length=3, smooth_weight=1)

    assert out.iloc[:4].isna().all()
    expected = {
        4: 0.2952396337048347,
        5: 0.06888924786446143,
        6: 0.7266731819883688,
        7: 0.09688975759844919,
    }
    for t, val in expected.items():
        assert out.iloc[t] == pytest.approx(val, abs=1e-9), f"bar {t}"


def test_matches_an_independent_loop_at_defaults():
    """Spot-checks 3 bars of the shipped defaults (std_length=20,
    smooth_length=20, smooth_weight=1) against a hand-written per-bar
    loop using plain numpy (`np.std(ddof=1)`), independent of the module's
    own pandas `.rolling()` / `.ewm()` calls."""
    close = _walk(900, seed=3)
    out = g191_160(close)
    c = close.to_numpy(dtype=float)
    n = len(c)
    std_length, smooth_length, smooth_weight = 20, 20, 1.0
    alpha = smooth_weight / smooth_length

    std_c = [float("nan")] * n
    for t in range(std_length - 1, n):
        std_c[t] = float(np.std(c[t - std_length + 1:t + 1], ddof=1))
    down_vol = [float("nan")] * n
    for t in range(n):
        if std_c[t] != std_c[t]:
            continue
        down_vol[t] = std_c[t] if c[t] <= c[t - 1] else 0.0
    y = None
    count = 0
    result = [float("nan")] * n
    for t in range(n):
        if down_vol[t] != down_vol[t]:
            continue
        y = down_vol[t] if y is None else alpha * down_vol[t] + (1 - alpha) * y
        count += 1
        if count >= smooth_length:
            result[t] = y / c[t]

    for t in (300, 600, 899):
        assert out.iloc[t] == pytest.approx(result[t], rel=1e-9)


def test_insufficient_history_returns_none():
    close = _walk(38)  # defaults need 20 + 20 - 1 = 39 bars
    assert g191_160(close) is None


def test_exact_min_length_fires_at_the_warmup_boundary():
    close = _walk(39)  # exactly 20 + 20 - 1 = 39 bars
    out = g191_160(close)
    assert out is not None
    assert out.iloc[:38].isna().all()
    assert pd.notna(out.iloc[38])


def test_default_name():
    close = _walk()
    out = g191_160(close)
    assert out.name == "G191_160_20_20_1"


def test_distinct_weights_produce_distinct_names_and_values():
    """Pins the regression round 1 of `g191_146` caught: two distinct
    INTEGER weights MUST produce two distinct column names (the name is
    the only thing mined strategy rules in the parent repo match on,
    CLAUDE.md "Naming is API") and, since the weight changes the GTJA
    `alpha = m/n`, two distinct Series of values."""
    close = _walk(300)
    out1 = g191_160(close, std_length=10, smooth_length=10, smooth_weight=1)
    out3 = g191_160(close, std_length=10, smooth_length=10, smooth_weight=3)
    assert out1.name != out3.name
    assert out1.name == "G191_160_10_10_1"
    assert out3.name == "G191_160_10_10_3"
    m = out1.notna() & out3.notna()
    assert (out1[m] != out3[m]).any()


def test_fractional_weights_that_truncate_the_same_are_identical():
    """`smooth_weight` is coerced to `int` at validation time, before any
    math runs, so two weights that truncate to the same integer are the
    same parameter all the way through: same name AND bit-identical
    values (the fix `g191_146`'s own regression test pins for the
    identical GTJA `SMA` operator)."""
    close = _walk(300)
    out_21 = g191_160(close, std_length=10, smooth_length=10, smooth_weight=2.1)
    out_24 = g191_160(close, std_length=10, smooth_length=10, smooth_weight=2.4)
    assert out_21.name == out_24.name == "G191_160_10_10_2"
    pd.testing.assert_series_equal(out_21, out_24)


# -------------------------------------------------------------- causality


_REAL = importlib.import_module("pandas_ta.volatility.g191_160")


def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_g191_160_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


WRITE_SHIFT_MUTANT = (
    "result = _gtja_sma(down_vol, smooth_length, smooth_weight) / close",
    "result = (_gtja_sma(down_vol, smooth_length, smooth_weight) / close).shift(-smooth_length)",
)
CENTERED_STD_MUTANT = (
    "std_c = close.rolling(std_length).std()",
    "std_c = close.rolling(std_length, center=True).std()",  # the `bos` look-ahead bug class
)

OFFSETS = range(150, 1500, 40)  # past the 38-bar warm-up


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
    assert _leaks(g191_160) == 0


def test_write_shift_mutant_is_caught():
    mod = _load_mutant(*WRITE_SHIFT_MUTANT)
    close = _walk(1500)
    assert not mod.g191_160(close).equals(g191_160(close))  # live
    assert _leaks(mod.g191_160) == len(list(OFFSETS))  # caught, every offset


def test_centered_std_mutant_is_caught():
    mod = _load_mutant(*CENTERED_STD_MUTANT)
    close = _walk(1500)
    assert not mod.g191_160(close).equals(g191_160(close))  # live
    assert _leaks(mod.g191_160) == len(list(OFFSETS))  # caught, every offset


# ------------------------------------------------------------ scale-free


@pytest.mark.parametrize("k", [8.0, 64.0])
def test_power_of_two_price_scale_is_bit_identical(k):
    close = _walk()
    base = g191_160(close)
    scaled = g191_160(close * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_other_price_scales_within_tolerance(k):
    close = _walk()
    base = g191_160(close)
    scaled = g191_160(close * k)
    assert (base.isna() == scaled.isna()).all()
    assert (base - scaled).abs().max() < 1e-9


def test_fires_and_is_not_constant():
    close = _walk()
    out = g191_160(close)
    fires = int(out.notna().sum())
    assert 0 < fires < len(out)
    assert out.dropna().nunique() > 1


# ---------------------------------------------------------------- wiring


def test_name_registration_and_accessor():
    close = _walk(400)
    df = pd.DataFrame({"open": close, "high": close, "low": close, "close": close})
    assert "g191_160" in ta.Category["volatility"]
    out = df.ta.g191_160()
    assert out.name == "G191_160_20_20_1"
    pd.testing.assert_series_equal(out, g191_160(close))
    # all three tunable kwargs forwarded under their own names in one call --
    # the "supertrend failure mode" (CLAUDE.md) hasattr cannot see.
    renamed = df.ta.g191_160(std_length=10, smooth_length=10, smooth_weight=1)
    assert renamed.name == "G191_160_10_10_1"
