# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.momentum.g191_169` -- Guotai Junan's (2017,
"GTJA191") alpha `#169`, per issue #72: `SMA(MEAN(DELAY(SMA(C-C1,9,1),1),
12) - MEAN(same,26), 10, 1) / close`, a MACD-style fast-minus-slow spread
of a once-lagged, GTJA-recursively-smoothed one-day price change, divided
by close for a scale-free result. `SMA(A,n,m)` is GTJA's own recursive EMA
(`alpha = m/n`), not this fork's plain simple-moving-average `sma`. Gate A
derivation is in the module docstring and `docs/G191169Measured.md`. Gate
E is pending (CLAUDE.md, "Owed, not failed").

What these pin, in order of how much it would hurt to lose:

* CAUSALITY by future-perturbation: rewrite every close bar from `j`
  onward (another synthetic walk), demand bars `[0:j]` bit-identical with
  matching NaN masks, over 34 offsets past the 44-bar warm-up. Two mutants
  (`importlib` source read, `exec`'d in memory), each shown live (differs
  from the real module) then caught at every offset: shifting the final
  write index `smooth2_length=10` bars into the future, and computing
  `fast` with `rolling(fast_length, center=True)` (the `bos` look-ahead
  bug class).
* CORRECTNESS: a 10-bar hand-derived example at `smooth1_length=2,
  smooth1_weight=1, fast_length=2, slow_length=3, smooth2_length=2,
  smooth2_weight=1`, replayed independently with Python's exact
  `fractions.Fraction` (no floats, no pandas `.ewm()`/`.rolling()`) in
  `docs/measure_g191_169.py`, matching the module's float64 output to
  ~1e-13. A second spot-check at the shipped defaults against an
  independent per-bar loop written in plain Python, looping the GTJA
  recursion from the first valid bar rather than calling pandas' own
  `.ewm()`.
* SCALE-FREE: `delta_c = close - close.shift(1)` and every downstream term
  built only from it (`s9`, `a`, `fast`, `slow`, `diff`, the final `SMA`)
  are linear in `close`, scaling exactly by the same factor as `close`
  under a positive rescale and cancelling against the final division by
  `close`: bit-identical under close x8/x64 (power-of-two, exact in
  IEEE754), and within `~1e-15` (float64 rounding, not a scale dependency)
  under x10/x3.7. Matching NaN masks, plus `0 < fires < n` and
  `nunique > 1`.
* Wiring: `Category`, the accessor, the column name
  `G191_169_9_1_12_26_10_1`.
"""
import importlib
import types

import numpy as np
import pandas as pd
import pytest
from pandas import Series

from .context import pandas_ta as ta
from pandas_ta.momentum.g191_169 import g191_169


def _walk(n=1500, seed=11, sigma=0.015):
    rng = np.random.default_rng(seed)
    close = 100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n)))
    return Series(close, index=pd.RangeIndex(n))


# ------------------------------------------------------------ correctness


def test_hand_derived_bars():
    """close = [10, 11, 9, 12, 8, 14, 7, 16, 6, 18], smooth1_length=2,
    smooth1_weight=1, fast_length=2, slow_length=3, smooth2_length=2,
    smooth2_weight=1 (alpha1 = alpha2 = 1/2). min_length = smooth1_length +
    max(fast_length, slow_length) + smooth2_length = 2+3+2 = 7, so bars
    0..5 are NaN and bars 6..9 are the first four valid values.

    delta_c[t] = close[t]-close[t-1], valid t>=1:
      delta_c = [-, 1, -2, 3, -4, 6, -7, 9, -10, 12]
    s9[t] = GTJA SMA(delta_c, 2, 1): y=delta_c[1]; y[t]=0.5*delta_c[t]+0.5*y[t-1].
    Masked (min_periods=2) until t=2:
      s9[2..9] = [-0.5, 1.25, -1.375, 2.3125, -2.34375, 3.328125, -3.3359375,
                  4.33203125]
    a[t] = s9[t-1], valid t>=3.
    fast[t] = MEAN(a, 2), valid t>=4. slow[t] = MEAN(a, 3), valid t>=5.
    diff[t] = fast[t]-slow[t], valid t>=5:
      diff[5..9] = [0.145833, -0.260417, 0.453125, -0.606771, 0.779948]
    result[t] = GTJA SMA(diff, 2, 1), masked (min_periods=2) until t=6.
    G191_169[t] = result[t] / close[t].

    Replayed exactly with `fractions.Fraction` (no floats) in
    docs/measure_g191_169.py, matching the module's float64 output here to
    ~1e-13.
    """
    close = Series([10.0, 11.0, 9.0, 12.0, 8.0, 14.0, 7.0, 16.0, 6.0, 18.0])
    out = g191_169(close, smooth1_length=2, smooth1_weight=1, fast_length=2,
                    slow_length=3, smooth2_length=2, smooth2_weight=1)

    assert out.iloc[:6].isna().all()
    expected = {
        6: -0.008184523809523806,
        7: 0.012369791666666668,
        8: -0.034071180555555546,
        9: 0.015986689814814815,
    }
    for t, val in expected.items():
        assert out.iloc[t] == pytest.approx(val, abs=1e-9), f"bar {t}"


def test_matches_an_independent_loop_at_defaults():
    """Spot-checks 3 bars of the shipped defaults (smooth1_length=9,
    smooth1_weight=1, fast_length=12, slow_length=26, smooth2_length=10,
    smooth2_weight=1) against a hand-written per-bar loop using plain
    Python, independent of the module's pandas `.ewm()` / `.rolling()`
    calls."""
    close = _walk(900, seed=3)
    out = g191_169(close)
    c = close.to_numpy(dtype=float)
    n = len(c)
    smooth1_length, smooth1_weight = 9, 1.0
    fast_length, slow_length = 12, 26
    smooth2_length, smooth2_weight = 10, 1.0
    b1 = smooth1_weight / smooth1_length
    b2 = smooth2_weight / smooth2_length

    delta = [float("nan")] * n
    for t in range(1, n):
        delta[t] = c[t] - c[t - 1]
    s9 = [float("nan")] * n
    y = None
    count1 = 0
    for t in range(n):
        if delta[t] != delta[t]:
            continue
        y = delta[t] if y is None else b1 * delta[t] + (1 - b1) * y
        count1 += 1
        if count1 >= smooth1_length:
            s9[t] = y
    a = [float("nan")] * n
    for t in range(1, n):
        a[t] = s9[t - 1]
    fast = [float("nan")] * n
    slow = [float("nan")] * n
    for t in range(n):
        wf = a[t - fast_length + 1:t + 1] if t - fast_length + 1 >= 0 else []
        if len(wf) == fast_length and all(v == v for v in wf):
            fast[t] = sum(wf) / fast_length
        ws = a[t - slow_length + 1:t + 1] if t - slow_length + 1 >= 0 else []
        if len(ws) == slow_length and all(v == v for v in ws):
            slow[t] = sum(ws) / slow_length
    diff = [float("nan")] * n
    for t in range(n):
        if fast[t] == fast[t] and slow[t] == slow[t]:
            diff[t] = fast[t] - slow[t]
    result = [float("nan")] * n
    z = None
    count2 = 0
    for t in range(n):
        if diff[t] != diff[t]:
            continue
        z = diff[t] if z is None else b2 * diff[t] + (1 - b2) * z
        count2 += 1
        if count2 >= smooth2_length:
            result[t] = z
    final = [float("nan") if result[t] != result[t] else result[t] / c[t]
             for t in range(n)]

    for t in (300, 600, 899):
        assert out.iloc[t] == pytest.approx(final[t], rel=1e-9)


def test_insufficient_history_returns_none():
    close = _walk(44)  # defaults need 9 + max(12, 26) + 10 = 45 bars
    assert g191_169(close) is None


def test_exact_min_length_fires_at_the_warmup_boundary():
    close = _walk(45)  # exactly 9 + 26 + 10 = 45 bars
    out = g191_169(close)
    assert out is not None
    assert out.iloc[:44].isna().all()
    assert pd.notna(out.iloc[44])


def test_default_name():
    close = _walk()
    out = g191_169(close)
    assert out.name == "G191_169_9_1_12_26_10_1"


def test_distinct_weights_produce_distinct_names_and_values():
    """Pins the regression round 1 of `g191_146` caught: two distinct
    INTEGER weights MUST produce two distinct column names (the name is
    the only thing mined strategy rules in the parent repo match on,
    CLAUDE.md "Naming is API") and, since the weight changes the GTJA
    `alpha = m/n`, two distinct Series of values."""
    close = _walk(300)
    out1 = g191_169(close, smooth1_length=5, smooth1_weight=1, fast_length=5,
                     slow_length=10, smooth2_length=5, smooth2_weight=1)
    out3 = g191_169(close, smooth1_length=5, smooth1_weight=3, fast_length=5,
                     slow_length=10, smooth2_length=5, smooth2_weight=3)
    assert out1.name != out3.name
    assert out1.name == "G191_169_5_1_5_10_5_1"
    assert out3.name == "G191_169_5_3_5_10_5_3"
    m = out1.notna() & out3.notna()
    assert (out1[m] != out3[m]).any()


def test_fractional_weights_that_truncate_the_same_are_identical():
    """`smooth1_weight`/`smooth2_weight` are coerced to `int` at
    validation time, before any math runs, so two weights that truncate to
    the same integer are the same parameter all the way through: same name
    AND bit-identical values (the fix `g191_146`'s own regression test
    pins for the identical GTJA `SMA` operator)."""
    close = _walk(300)
    out_21 = g191_169(close, smooth1_length=10, smooth1_weight=2.1,
                       fast_length=5, slow_length=10, smooth2_length=10,
                       smooth2_weight=2.1)
    out_24 = g191_169(close, smooth1_length=10, smooth1_weight=2.4,
                       fast_length=5, slow_length=10, smooth2_length=10,
                       smooth2_weight=2.4)
    assert out_21.name == out_24.name == "G191_169_10_2_5_10_10_2"
    pd.testing.assert_series_equal(out_21, out_24)


# -------------------------------------------------------------- causality


_REAL = importlib.import_module("pandas_ta.momentum.g191_169")


def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_g191_169_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


WRITE_SHIFT_MUTANT = (
    "result = _gtja_sma(diff, smooth2_length, smooth2_weight) / close",
    "result = (_gtja_sma(diff, smooth2_length, smooth2_weight) / close).shift(-smooth2_length)",
)
CENTERED_FAST_MUTANT = (
    "fast = a.rolling(fast_length).mean()",
    "fast = a.rolling(fast_length, center=True).mean()",  # the `bos` look-ahead bug class
)

OFFSETS = range(150, 1500, 40)  # past the 44-bar warm-up


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
    assert _leaks(g191_169) == 0


def test_write_shift_mutant_is_caught():
    mod = _load_mutant(*WRITE_SHIFT_MUTANT)
    close = _walk(1500)
    assert not mod.g191_169(close).equals(g191_169(close))  # live
    assert _leaks(mod.g191_169) == len(list(OFFSETS))  # caught, every offset


def test_centered_fast_mutant_is_caught():
    mod = _load_mutant(*CENTERED_FAST_MUTANT)
    close = _walk(1500)
    assert not mod.g191_169(close).equals(g191_169(close))  # live
    assert _leaks(mod.g191_169) == len(list(OFFSETS))  # caught, every offset


# ------------------------------------------------------------ scale-free


@pytest.mark.parametrize("k", [8.0, 64.0])
def test_power_of_two_price_scale_is_bit_identical(k):
    close = _walk()
    base = g191_169(close)
    scaled = g191_169(close * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_other_price_scales_within_tolerance(k):
    close = _walk()
    base = g191_169(close)
    scaled = g191_169(close * k)
    assert (base.isna() == scaled.isna()).all()
    assert (base - scaled).abs().max() < 1e-9


def test_fires_and_is_not_constant():
    close = _walk()
    out = g191_169(close)
    fires = int(out.notna().sum())
    assert 0 < fires < len(out)
    assert out.dropna().nunique() > 1


# ---------------------------------------------------------------- wiring


def test_name_registration_and_accessor():
    close = _walk(400)
    df = pd.DataFrame({"open": close, "high": close, "low": close, "close": close})
    assert "g191_169" in ta.Category["momentum"]
    out = df.ta.g191_169()
    assert out.name == "G191_169_9_1_12_26_10_1"
    pd.testing.assert_series_equal(out, g191_169(close))
    # all six tunable kwargs forwarded under their own names in one call --
    # the "supertrend failure mode" (CLAUDE.md) hasattr cannot see.
    renamed = df.ta.g191_169(smooth1_length=5, smooth1_weight=1, fast_length=5,
                              slow_length=10, smooth2_length=5, smooth2_weight=1)
    assert renamed.name == "G191_169_5_1_5_10_5_1"
