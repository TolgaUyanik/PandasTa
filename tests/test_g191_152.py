# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.momentum.g191_152` -- Guotai Junan's (2017,
"GTJA191") alpha `#152`, per issue #66: `SMA(MEAN(DELAY(SMA(DELAY(C/C9,1),
9,1),1),12) - MEAN(same,26), 9, 1)`, a MACD-style fast-minus-slow spread of
a once-lagged, GTJA-recursively-smoothed 9-day close ratio. `SMA(A,n,m)` is
GTJA's own recursive EMA (`alpha = m/n`), not this fork's plain simple-
moving-average `sma`. Gate A derivation is in the module docstring and
`docs/G191152Measured.md`. Gate E is pending (CLAUDE.md, "Owed, not
failed").

What these pin, in order of how much it would hurt to lose:

* CAUSALITY by future-perturbation: rewrite every close bar from `j`
  onward (another synthetic walk), demand bars `[0:j]` bit-identical with
  matching NaN masks, over 34 offsets past the 52-bar warm-up. Two mutants
  (`importlib` source read, `exec`'d in memory), each shown live (differs
  from the real module) then caught at every offset: shifting the final
  write index `smooth2_length=9` bars into the future, and computing
  `fast` with `rolling(fast_length, center=True)` (the `bos` look-ahead
  bug class). A third construction (`r1 = ratio.shift(-1)`, a genuine
  one-bar look-ahead) is live-different but NOT caught by this sweep --
  the pipeline's own further `DELAY`s push its first visible effect one
  bar past the checked window (`python docs/measure_g191_152.py`); kept
  disclosed in the module docstring, not used as a Gate B pin.
* CORRECTNESS: a 14-bar hand-derived example at `delay_length=3,
  smooth1_length=2, smooth1_weight=1, fast_length=2, slow_length=3,
  smooth2_length=2, smooth2_weight=1`, replayed independently with
  Python's exact `fractions.Fraction` (no floats, no pandas
  `.ewm()`/`.rolling()`) in `docs/measure_g191_152.py`, matching the
  module's float64 output to ~1e-13. A second spot-check at the shipped
  defaults against an independent per-bar loop written in plain Python,
  looping the GTJA recursion from the first valid bar rather than calling
  pandas' own `.ewm()`.
* SCALE-FREE: `ratio = close / close.shift(delay_length)` is exactly
  invariant under a positive rescale of `close` (the scale cancels
  algebraically before anything downstream runs), so the whole column is
  bit-identical under close x8/x64 (power-of-two, exact in IEEE754), and
  within `~1e-15` (float64 rounding, not a scale dependency) under
  x10/x3.7. Matching NaN masks, plus `0 < fires < n` and `nunique > 1`.
* Wiring: `Category`, the accessor, the column name
  `G191_152_9_9_1_12_26_9_1`.
"""
import importlib
import types

import numpy as np
import pandas as pd
import pytest
from pandas import Series

from .context import pandas_ta as ta
from pandas_ta.momentum.g191_152 import g191_152


def _walk(n=1500, seed=11, sigma=0.015):
    rng = np.random.default_rng(seed)
    close = 100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n)))
    return Series(close, index=pd.RangeIndex(n))


# ------------------------------------------------------------ correctness


def test_hand_derived_bars():
    """close = [10, 11, 9, 12, 8, 14, 7, 16, 6, 18, 5, 20, 4, 22],
    delay_length=3, smooth1_length=2, smooth1_weight=1, fast_length=2,
    slow_length=3, smooth2_length=2, smooth2_weight=1 (alpha1 = alpha2 =
    1/2). min_length = delay_length + smooth1_length +
    max(fast_length, slow_length) + smooth2_length = 3+2+3+2 = 10, so bars
    0..8 are NaN and bars 9..13 are the first five valid values.

    ratio[t] = close[t]/close[t-3], valid t>=3:
      ratio = [-,-,-, 1.2, 0.727273, 1.555556, 0.583333, 2.0, 0.428571,
               2.571429, 0.3125, 3.333333, 0.222222, 4.4]
    r1[t] = ratio[t-1], valid t>=4.
    s9[t] = GTJA SMA(r1, 2, 1): y=r1[4]; y[t]=0.5*r1[t]+0.5*y[t-1].
    Masked (min_periods=2) until t=5:
      s9[5..13] = [0.963636, 1.259596, 0.921465, 1.460732, 0.944652,
                   1.758040, 1.035270, 2.184302, 1.203262]
    s9_1[t] = s9[t-1], valid t>=6.
    fast[t] = MEAN(s9_1, 2), valid t>=7. slow[t] = MEAN(s9_1, 3), valid t>=8.
    diff[t] = fast[t]-slow[t], valid t>=8:
      diff[8..13] = [0.042298, -0.022832, 0.093742, -0.036462, 0.150668,
                     -0.049418]
    result[t] = GTJA SMA(diff, 2, 1), masked (min_periods=2) until t=9:
      result[9..13] = [0.009732744107744109, 0.051737614237614235,
                        0.007637761544011544, 0.07915276274651274,
                        0.014867330297017797]

    Replayed exactly with `fractions.Fraction` (no floats) in
    docs/measure_g191_152.py, matching the module's float64 output here to
    ~1e-13.
    """
    close = Series([10.0, 11.0, 9.0, 12.0, 8.0, 14.0, 7.0, 16.0, 6.0, 18.0,
                     5.0, 20.0, 4.0, 22.0])
    out = g191_152(close, delay_length=3, smooth1_length=2, smooth1_weight=1,
                    fast_length=2, slow_length=3, smooth2_length=2,
                    smooth2_weight=1)

    assert out.iloc[:9].isna().all()
    expected = {
        9: 0.009732744107744109,
        10: 0.051737614237614235,
        11: 0.007637761544011544,
        12: 0.07915276274651274,
        13: 0.014867330297017797,
    }
    for t, val in expected.items():
        assert out.iloc[t] == pytest.approx(val, abs=1e-9), f"bar {t}"


def test_matches_an_independent_loop_at_defaults():
    """Spot-checks 3 bars of the shipped defaults (delay_length=9,
    smooth1_length=9, smooth1_weight=1, fast_length=12, slow_length=26,
    smooth2_length=9, smooth2_weight=1) against a hand-written per-bar
    loop using plain Python, independent of the module's pandas
    `.ewm()` / `.rolling()` calls."""
    close = _walk(900, seed=3)
    out = g191_152(close)
    c = close.to_numpy(dtype=float)
    n = len(c)
    delay_length = 9
    smooth1_length, smooth1_weight = 9, 1.0
    fast_length, slow_length = 12, 26
    smooth2_length, smooth2_weight = 9, 1.0
    a1 = smooth1_weight / smooth1_length
    a2 = smooth2_weight / smooth2_length

    ratio = [float("nan")] * n
    for t in range(delay_length, n):
        ratio[t] = c[t] / c[t - delay_length]
    r1 = [float("nan")] * n
    for t in range(1, n):
        r1[t] = ratio[t - 1]
    s9 = [float("nan")] * n
    y = None
    count1 = 0
    for t in range(n):
        if r1[t] != r1[t]:
            continue
        y = r1[t] if y is None else a1 * r1[t] + (1 - a1) * y
        count1 += 1
        if count1 >= smooth1_length:
            s9[t] = y
    s9_1 = [float("nan")] * n
    for t in range(1, n):
        s9_1[t] = s9[t - 1]
    fast = [float("nan")] * n
    slow = [float("nan")] * n
    for t in range(n):
        wf = s9_1[t - fast_length + 1:t + 1] if t - fast_length + 1 >= 0 else []
        if len(wf) == fast_length and all(v == v for v in wf):
            fast[t] = sum(wf) / fast_length
        ws = s9_1[t - slow_length + 1:t + 1] if t - slow_length + 1 >= 0 else []
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
        z = diff[t] if z is None else a2 * diff[t] + (1 - a2) * z
        count2 += 1
        if count2 >= smooth2_length:
            result[t] = z

    for t in (300, 600, 899):
        assert out.iloc[t] == pytest.approx(result[t], rel=1e-9)


def test_insufficient_history_returns_none():
    close = _walk(52)  # defaults need 9 + 9 + max(12, 26) + 9 = 53 bars
    assert g191_152(close) is None


def test_exact_min_length_fires_at_the_warmup_boundary():
    close = _walk(53)  # exactly 9 + 9 + 26 + 9 = 53 bars
    out = g191_152(close)
    assert out is not None
    assert out.iloc[:52].isna().all()
    assert pd.notna(out.iloc[52])


def test_default_name():
    close = _walk()
    out = g191_152(close)
    assert out.name == "G191_152_9_9_1_12_26_9_1"


def test_distinct_weights_produce_distinct_names_and_values():
    """Pins the regression round 1 of `g191_146` caught: two distinct
    INTEGER weights MUST produce two distinct column names (the name is
    the only thing mined strategy rules in the parent repo match on,
    CLAUDE.md "Naming is API") and, since the weight changes the GTJA
    `alpha = m/n`, two distinct Series of values."""
    close = _walk(300)
    out1 = g191_152(close, delay_length=5, smooth1_length=5, smooth1_weight=1,
                     fast_length=5, slow_length=10, smooth2_length=5,
                     smooth2_weight=1)
    out3 = g191_152(close, delay_length=5, smooth1_length=5, smooth1_weight=3,
                     fast_length=5, slow_length=10, smooth2_length=5,
                     smooth2_weight=3)
    assert out1.name != out3.name
    assert out1.name == "G191_152_5_5_1_5_10_5_1"
    assert out3.name == "G191_152_5_5_3_5_10_5_3"
    m = out1.notna() & out3.notna()
    assert (out1[m] != out3[m]).any()


def test_fractional_weights_that_truncate_the_same_are_identical():
    """`smooth1_weight`/`smooth2_weight` are coerced to `int` at
    validation time, before any math runs, so two weights that truncate to
    the same integer are the same parameter all the way through: same name
    AND bit-identical values (the fix `g191_146`'s own regression test
    pins for the identical GTJA `SMA` operator)."""
    close = _walk(300)
    out_21 = g191_152(close, delay_length=5, smooth1_length=10, smooth1_weight=2.1,
                       fast_length=5, slow_length=10, smooth2_length=10,
                       smooth2_weight=2.1)
    out_24 = g191_152(close, delay_length=5, smooth1_length=10, smooth1_weight=2.4,
                       fast_length=5, slow_length=10, smooth2_length=10,
                       smooth2_weight=2.4)
    assert out_21.name == out_24.name == "G191_152_5_10_2_5_10_10_2"
    pd.testing.assert_series_equal(out_21, out_24)


# -------------------------------------------------------------- causality


_REAL = importlib.import_module("pandas_ta.momentum.g191_152")


def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_g191_152_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


WRITE_SHIFT_MUTANT = (
    "result = _gtja_sma(diff, smooth2_length, smooth2_weight)",
    "result = _gtja_sma(diff, smooth2_length, smooth2_weight).shift(-smooth2_length)",
)
CENTERED_FAST_MUTANT = (
    "fast = s9_1.rolling(fast_length).mean()",
    "fast = s9_1.rolling(fast_length, center=True).mean()",  # the `bos` look-ahead bug class
)

OFFSETS = range(150, 1500, 40)  # past the 52-bar warm-up


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
    assert _leaks(g191_152) == 0


def test_write_shift_mutant_is_caught():
    mod = _load_mutant(*WRITE_SHIFT_MUTANT)
    close = _walk(1500)
    assert not mod.g191_152(close).equals(g191_152(close))  # live
    assert _leaks(mod.g191_152) == len(list(OFFSETS))  # caught, every offset


def test_centered_fast_mutant_is_caught():
    mod = _load_mutant(*CENTERED_FAST_MUTANT)
    close = _walk(1500)
    assert not mod.g191_152(close).equals(g191_152(close))  # live
    assert _leaks(mod.g191_152) == len(list(OFFSETS))  # caught, every offset


def test_forward_inner_delay_mutant_is_live_but_not_caught_by_this_sweep():
    """Disclosed in the module docstring: `r1 = ratio.shift(-1)` IS a
    genuine one-bar look-ahead and differs live from the real module, but
    the pipeline's own further `DELAY`s (`s9_1 = DELAY(s9,1)`, then the
    rolling means) push its first visible OUTPUT effect to index `j`, one
    bar past the last index (`j-1`) this sweep's `[:j]` window checks.
    Pinned here as a NEGATIVE result -- NOT a Gate B pin -- so nobody reads
    the module docstring's disclosure as untested."""
    mod = _load_mutant("r1 = ratio.shift(1)", "r1 = ratio.shift(-1)")
    close = _walk(1500)
    assert not mod.g191_152(close).equals(g191_152(close))  # live
    assert _leaks(mod.g191_152) == 0  # NOT caught by this sweep


# ------------------------------------------------------------ scale-free


@pytest.mark.parametrize("k", [8.0, 64.0])
def test_power_of_two_price_scale_is_bit_identical(k):
    close = _walk()
    base = g191_152(close)
    scaled = g191_152(close * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_other_price_scales_within_tolerance(k):
    close = _walk()
    base = g191_152(close)
    scaled = g191_152(close * k)
    assert (base.isna() == scaled.isna()).all()
    assert (base - scaled).abs().max() < 1e-9


def test_fires_and_is_not_constant():
    close = _walk()
    out = g191_152(close)
    fires = int(out.notna().sum())
    assert 0 < fires < len(out)
    assert out.dropna().nunique() > 1


# ---------------------------------------------------------------- wiring


def test_name_registration_and_accessor():
    close = _walk(400)
    df = pd.DataFrame({"open": close, "high": close, "low": close, "close": close})
    assert "g191_152" in ta.Category["momentum"]
    out = df.ta.g191_152()
    assert out.name == "G191_152_9_9_1_12_26_9_1"
    pd.testing.assert_series_equal(out, g191_152(close))
    # all seven tunable kwargs forwarded under their own names in one call --
    # the "supertrend failure mode" (CLAUDE.md) hasattr cannot see.
    renamed = df.ta.g191_152(delay_length=5, smooth1_length=5, smooth1_weight=1,
                              fast_length=5, slow_length=10, smooth2_length=5,
                              smooth2_weight=1)
    assert renamed.name == "G191_152_5_5_1_5_10_5_1"
