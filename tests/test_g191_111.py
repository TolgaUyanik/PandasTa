# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.volume.g191_111` -- Guotai Junan's (2017, "GTJA191")
alpha `#111`, per issue #71: `SMA(V*CLV,11,2) - SMA(V*CLV,4,2)`, divided by
`MEAN(V,20)` (the issue's own scale-free conversion). `CLV` is the per-bar
close-location value `((C-L)-(H-C))/(H-L)`; `SMA(A,n,m)` is GTJA's own
recursive EMA (`alpha = m/n`), not this fork's plain simple-moving-average
`sma`, applied twice to the SAME series `x = V*CLV` at two different
`(n, m)` pairs, then the two smoothed series are subtracted and divided by
the trailing mean volume. Gate A derivation is in the module docstring and
`docs/G191111Measured.md`. Gate E is pending (CLAUDE.md, "Owed, not
failed").

What these pin, in order of how much it would hurt to lose:

* CAUSALITY by future-perturbation: rewrite every OHLCV bar from `j`
  onward (another synthetic walk), demand bars `[0:j]` bit-identical with
  matching NaN masks, over 37 offsets past the 19-bar warm-up. Two mutants
  (`importlib` source read, `exec`'d in memory), each shown live (differs
  from the real module) then caught at every offset: shifting the final
  write index `mean_length=20` bars into the future, and computing
  `mean_v` with `rolling(mean_length, center=True)` (the `bos` look-ahead
  bug class).
* CORRECTNESS: an 8-bar hand-derived example at `smooth1_length=3,
  smooth1_weight=1, smooth2_length=2, smooth2_weight=1, mean_length=3`,
  checked against an independent per-bar computation of `CLV`/`x`/both
  GTJA `SMA`s/`MEAN` (`python docs/measure_g191_111.py` prints the exact
  values). A second spot-check at the shipped defaults against an
  independent per-bar loop using plain numpy, not pandas' own
  `.rolling()`/`.ewm()` calls.
* SCALE-FREE: `CLV` is invariant under a positive PRICE rescale (both
  `clv`'s numerator and denominator are linear in price, the factor
  cancels), so `x = V*CLV` and everything downstream is price-rescale
  invariant; `x`, both GTJA `SMA`s and `MEAN(V,...)` are each linear in a
  positive VOLUME rescale, so the final ratio's volume factor cancels
  exactly too. Measured bit-identical under PRICE x8/x64, VOLUME x8/x64,
  and BOTH x8/x64 (power-of-two, exact in IEEE754), and within float64
  tolerance under x10/x3.7 for each. Matching NaN masks, plus
  `0 < fires < n` and `nunique > 1`.
* Wiring: `Category`, the accessor, the column name
  `G191_111_11_2_4_2_20`.
"""
import importlib
import types

import numpy as np
import pandas as pd
import pytest
from pandas import Series

from .context import pandas_ta as ta
from pandas_ta.volume.g191_111 import g191_111


def _walk(n=1500, seed=11, sigma=0.015):
    rng = np.random.default_rng(seed)
    close = 100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n)))
    rng2 = np.random.default_rng(seed + 1)
    spread = close * rng2.uniform(0.005, 0.02, n)
    high = close + spread * rng2.uniform(0.3, 1.0, n)
    low = close - spread * rng2.uniform(0.3, 1.0, n)
    volume = rng2.uniform(1000.0, 5000.0, n)
    return (Series(high), Series(low), Series(close), Series(volume))


# ------------------------------------------------------------ correctness


def test_hand_derived_bars():
    """high/low/close/volume over 8 bars (no H==L ties), smooth1_length=3,
    smooth1_weight=1 (alpha=1/3), smooth2_length=2, smooth2_weight=1
    (alpha=1/2), mean_length=3. min_length = max(3, 2, 3) = 3, so bar 0 is
    NaN (mean_v needs 3 consecutive volumes) and bars 1..7 are candidates,
    with bar 1 also NaN (mean_v still undefined there: mean_length=3 needs
    bars 0..2). Bars 2..7 are the first six valid values.

    clv = [0.0, 0.5, -0.333333, 0.0, -0.5, 0.428571, -0.5, 0.75]
    x   = [0.0, 75.0, -26.666667, 0.0, -30.0, 128.571429, -25.0, 300.0]
    sma1 (GTJA SMA(x,3,1)), valid from bar 2:
        sma1[2..7] = [7.777778, 5.185185, -6.543210, 38.495003, 17.330002,
                       111.553335]
    sma2 (GTJA SMA(x,2,1)), valid from bar 1:
        sma2[1..7] = [37.5, 5.416667, 2.708333, -13.645833, 57.462798,
                      16.231399, 158.115699]
    mean_v = MEAN(V,3), valid from bar 2:
        mean_v[2..7] = [110.0, 143.333333, 113.333333, 186.666667,
                        136.666667, 250.0]
    result[t] = (sma1[t] - sma2[t]) / mean_v[t]:
        result[2..7] = [0.02146464646464646, 0.017280361757105945,
                        0.06267020697167758, -0.10161318578357276,
                        0.008038559634934932, -0.18624945906003018]

    Independently derived and printed by docs/measure_g191_111.py, matching
    the module's float64 output exactly (same arithmetic, no float-only
    tolerance needed for this particular example).
    """
    high = Series([12.0, 14.0, 11.0, 18.0, 10.0, 22.0, 9.0, 26.0])
    low = Series([8.0, 10.0, 8.0, 12.0, 6.0, 15.0, 5.0, 18.0])
    close = Series([10.0, 13.0, 9.0, 15.0, 7.0, 20.0, 6.0, 25.0])
    volume = Series([100.0, 150.0, 80.0, 200.0, 60.0, 300.0, 50.0, 400.0])
    out = g191_111(high, low, close, volume, smooth1_length=3, smooth1_weight=1,
                    smooth2_length=2, smooth2_weight=1, mean_length=3)

    assert out.iloc[:2].isna().all()
    expected = {
        2: 0.02146464646464646,
        3: 0.017280361757105945,
        4: 0.06267020697167758,
        5: -0.10161318578357276,
        6: 0.008038559634934932,
        7: -0.18624945906003018,
    }
    for t, val in expected.items():
        assert out.iloc[t] == pytest.approx(val, abs=1e-9), f"bar {t}"


def test_matches_an_independent_loop_at_defaults():
    """Spot-checks 3 bars of the shipped defaults against a hand-written
    per-bar loop using plain numpy, independent of the module's own pandas
    `.rolling()` / `.ewm()` calls."""
    high, low, close, volume = _walk(900, seed=3)
    out = g191_111(high, low, close, volume)
    h, l, c, v = (s.to_numpy(dtype=float) for s in (high, low, close, volume))
    n = len(c)
    s1n, s1w, s2n, s2w, mn = 11, 2, 4, 2, 20
    a1, a2 = s1w / s1n, s2w / s2n

    clv_np = np.where(h != l, ((c - l) - (h - c)) / (h - l), np.nan)
    x_np = v * clv_np
    y1 = y2 = None
    count1 = count2 = 0
    sma1_np = [float("nan")] * n
    sma2_np = [float("nan")] * n
    for t in range(n):
        if x_np[t] == x_np[t]:
            y1 = x_np[t] if y1 is None else a1 * x_np[t] + (1 - a1) * y1
            count1 += 1
            if count1 >= s1n:
                sma1_np[t] = y1
            y2 = x_np[t] if y2 is None else a2 * x_np[t] + (1 - a2) * y2
            count2 += 1
            if count2 >= s2n:
                sma2_np[t] = y2
    result_np = [float("nan")] * n
    for t in range(mn - 1, n):
        mean_v_t = float(np.mean(v[t - mn + 1:t + 1]))
        if sma1_np[t] == sma1_np[t] and sma2_np[t] == sma2_np[t]:
            result_np[t] = (sma1_np[t] - sma2_np[t]) / mean_v_t

    for t in (300, 600, 899):
        assert out.iloc[t] == pytest.approx(result_np[t], rel=1e-9)


def test_insufficient_history_returns_none():
    high, low, close, volume = _walk(19)  # defaults need max(11,4,20) = 20 bars
    assert g191_111(high, low, close, volume) is None


def test_exact_min_length_fires_at_the_warmup_boundary():
    high, low, close, volume = _walk(20)  # exactly 20 bars
    out = g191_111(high, low, close, volume)
    assert out is not None
    assert out.iloc[:19].isna().all()
    assert pd.notna(out.iloc[19])


def test_default_name():
    high, low, close, volume = _walk()
    out = g191_111(high, low, close, volume)
    assert out.name == "G191_111_11_2_4_2_20"


def test_distinct_weights_produce_distinct_names_and_values():
    """Pins the regression round 1 of `g191_146` caught: two distinct
    INTEGER weights MUST produce two distinct column names (the name is
    the only thing mined strategy rules in the parent repo match on,
    CLAUDE.md "Naming is API") and, since the weight changes the GTJA
    `alpha = m/n`, two distinct Series of values."""
    high, low, close, volume = _walk(300)
    out1 = g191_111(high, low, close, volume, smooth1_length=10, smooth1_weight=1,
                     smooth2_length=5, smooth2_weight=1, mean_length=10)
    out3 = g191_111(high, low, close, volume, smooth1_length=10, smooth1_weight=3,
                     smooth2_length=5, smooth2_weight=1, mean_length=10)
    assert out1.name != out3.name
    assert out1.name == "G191_111_10_1_5_1_10"
    assert out3.name == "G191_111_10_3_5_1_10"
    m = out1.notna() & out3.notna()
    assert (out1[m] != out3[m]).any()


def test_fractional_weights_that_truncate_the_same_are_identical():
    """`smooth1_weight` is coerced to `int` at validation time, before any
    math runs, so two weights that truncate to the same integer are the
    same parameter all the way through: same name AND bit-identical
    values (the fix `g191_146`'s own regression test pins for the
    identical GTJA `SMA` operator)."""
    high, low, close, volume = _walk(300)
    out_21 = g191_111(high, low, close, volume, smooth1_length=10, smooth1_weight=2.1,
                       smooth2_length=5, smooth2_weight=1, mean_length=10)
    out_24 = g191_111(high, low, close, volume, smooth1_length=10, smooth1_weight=2.4,
                       smooth2_length=5, smooth2_weight=1, mean_length=10)
    assert out_21.name == out_24.name == "G191_111_10_2_5_1_10"
    pd.testing.assert_series_equal(out_21, out_24)


# -------------------------------------------------------------- causality


_REAL = importlib.import_module("pandas_ta.volume.g191_111")


def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_g191_111_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


WRITE_SHIFT_MUTANT = (
    "result = ((sma1 - sma2) / mean_v).replace([np.inf, -np.inf], np.nan)",
    "result = (((sma1 - sma2) / mean_v).replace([np.inf, -np.inf], np.nan)).shift(-mean_length)",
)
CENTERED_MEAN_MUTANT = (
    "mean_v = volume.rolling(mean_length).mean()",
    "mean_v = volume.rolling(mean_length, center=True).mean()",  # the `bos` look-ahead bug class
)

OFFSETS = range(50, 1500, 40)  # past the 19-bar warm-up


def _leaks(fn):
    high, low, close, volume = _walk(1500)
    other_h, other_l, other_c, other_v = _walk(1500, seed=97)
    base = fn(high, low, close, volume)
    hits = 0
    for j in OFFSETS:
        ph, pl, pc, pv = high.copy(), low.copy(), close.copy(), volume.copy()
        ph.iloc[j:] = other_h.iloc[j:].values
        pl.iloc[j:] = other_l.iloc[j:].values
        pc.iloc[j:] = other_c.iloc[j:].values
        pv.iloc[j:] = other_v.iloc[j:].values
        out = fn(ph, pl, pc, pv)
        a, b = base.iloc[:j], out.iloc[:j]
        if not (a.isna() == b.isna()).all():
            hits += 1
            continue
        m = a.notna()
        if (a[m] != b[m]).any():
            hits += 1
    return hits


def test_real_module_never_reads_the_future():
    assert _leaks(g191_111) == 0


def test_write_shift_mutant_is_caught():
    mod = _load_mutant(*WRITE_SHIFT_MUTANT)
    high, low, close, volume = _walk(1500)
    assert not mod.g191_111(high, low, close, volume).equals(
        g191_111(high, low, close, volume))  # live
    assert _leaks(mod.g191_111) == len(list(OFFSETS))  # caught, every offset


def test_centered_mean_mutant_is_caught():
    mod = _load_mutant(*CENTERED_MEAN_MUTANT)
    high, low, close, volume = _walk(1500)
    assert not mod.g191_111(high, low, close, volume).equals(
        g191_111(high, low, close, volume))  # live
    assert _leaks(mod.g191_111) == len(list(OFFSETS))  # caught, every offset


# ------------------------------------------------------------ scale-free


@pytest.mark.parametrize("k", [8.0, 64.0])
def test_power_of_two_price_scale_is_bit_identical(k):
    high, low, close, volume = _walk()
    base = g191_111(high, low, close, volume)
    scaled = g191_111(high * k, low * k, close * k, volume)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("k", [8.0, 64.0])
def test_power_of_two_volume_scale_is_bit_identical(k):
    high, low, close, volume = _walk()
    base = g191_111(high, low, close, volume)
    scaled = g191_111(high, low, close, volume * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_other_price_scales_within_tolerance(k):
    high, low, close, volume = _walk()
    base = g191_111(high, low, close, volume)
    scaled = g191_111(high * k, low * k, close * k, volume)
    assert (base.isna() == scaled.isna()).all()
    assert (base - scaled).abs().max() < 1e-9


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_other_volume_scales_within_tolerance(k):
    high, low, close, volume = _walk()
    base = g191_111(high, low, close, volume)
    scaled = g191_111(high, low, close, volume * k)
    assert (base.isna() == scaled.isna()).all()
    assert (base - scaled).abs().max() < 1e-9


def test_fires_and_is_not_constant():
    high, low, close, volume = _walk()
    out = g191_111(high, low, close, volume)
    fires = int(out.notna().sum())
    assert 0 < fires < len(out)
    assert out.dropna().nunique() > 1


# ---------------------------------------------------------------- wiring


def test_name_registration_and_accessor():
    high, low, close, volume = _walk(400)
    df = pd.DataFrame({"open": close, "high": high, "low": low,
                        "close": close, "volume": volume})
    assert "g191_111" in ta.Category["volume"]
    out = df.ta.g191_111()
    assert out.name == "G191_111_11_2_4_2_20"
    pd.testing.assert_series_equal(out, g191_111(high, low, close, volume))
    # all five tunable kwargs forwarded under their own names in one call --
    # the "supertrend failure mode" (CLAUDE.md) hasattr cannot see.
    renamed = df.ta.g191_111(smooth1_length=10, smooth1_weight=1,
                              smooth2_length=5, smooth2_weight=1, mean_length=10)
    assert renamed.name == "G191_111_10_1_5_1_10"
