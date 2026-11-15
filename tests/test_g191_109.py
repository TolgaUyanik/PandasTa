# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.volatility.g191_109` -- Guotai Junan's (2017,
"GTJA191") alpha `#109`, per issue #76: `SMA(H-L,10,2) /
SMA(SMA(H-L,10,2),10,2)`. `SMA(A,n,m)` is GTJA's own recursive EMA
(`alpha = m/n`), not this fork's plain simple-moving-average `sma`, applied
TWICE here in a CHAIN (the second application smooths the OUTPUT of the
first, unlike `g191_111`'s two `SMA`s applied in parallel to the same
input). No `conv` field in the issue's own `candidates.csv` row -- the
ratio of a quantity to its own further smoothing is scale-free with no
extra division needed. Gate A derivation is in the module docstring and
`docs/G191109Measured.md`. Gate E is pending (CLAUDE.md, "Owed, not
failed").

What these pin, in order of how much it would hurt to lose:

* CAUSALITY by future-perturbation: rewrite every high/low bar from `j`
  onward (another synthetic walk), demand bars `[0:j]` bit-identical with
  matching NaN masks, over 37 offsets past the 19-bar warm-up. Two mutants
  (`importlib` source read, `exec`'d in memory), each shown live (differs
  from the real module) then caught at every offset: shifting the final
  write index `smooth2_length=10` bars into the future, and computing the
  first `SMA`'s input from `high.shift(-1) - low.shift(-1)` (one bar of
  look-ahead folded into the range before smoothing -- the `bos`
  look-ahead bug class).
* CORRECTNESS: an 8-bar hand-derived example at `smooth1_length=3,
  smooth1_weight=1, smooth2_length=2, smooth2_weight=1`, checked against
  an independent per-bar computation of the chained GTJA `SMA`
  (`python docs/measure_g191_109.py` prints the exact values). A second
  spot-check at the shipped defaults against an independent per-bar loop
  using plain numpy, not pandas' own `.rolling()`/`.ewm()` calls.
* SCALE-FREE: `H - L` is linear in a positive price rescale, and GTJA
  `SMA` is a linear recursion in a positive scalar multiple of its input,
  so BOTH stages of the chain scale by the SAME factor -- the ratio
  cancels it exactly, with no extra division needed (unlike every other
  ratio-form `g191_*` port, this one's own `candidates.csv` row carries no
  `conv` field). Measured bit-identical under PRICE x8/x64 (power-of-two,
  exact in IEEE754), and within float64 tolerance under x10/x3.7. Matching
  NaN masks, plus `0 < fires < n`, `nunique > 1`, and non-negativity.
* Wiring: `Category`, the accessor, the column name `G191_109_10_2_10_2`.
"""
import importlib
import types

import numpy as np
import pandas as pd
import pytest
from pandas import Series

from .context import pandas_ta as ta
from pandas_ta.volatility.g191_109 import g191_109


def _walk(n=1500, seed=11, sigma=0.015):
    rng = np.random.default_rng(seed)
    close = 100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n)))
    rng2 = np.random.default_rng(seed + 1)
    spread = close * rng2.uniform(0.005, 0.02, n)
    high = close + spread * rng2.uniform(0.3, 1.0, n)
    low = close - spread * rng2.uniform(0.3, 1.0, n)
    return (Series(high), Series(low))


# ------------------------------------------------------------ correctness


def test_hand_derived_bars():
    """high/low over 8 bars (no H==L ties), smooth1_length=3,
    smooth1_weight=1 (alpha=1/3), smooth2_length=2, smooth2_weight=1
    (alpha=1/2). min_length = smooth1_length + smooth2_length - 1 = 4, so
    bars 0..2 are NaN and bars 3..7 are the first five valid values.

    r = H - L = [4.0, 4.0, 3.0, 6.0, 4.0, 7.0, 4.0, 8.0]
    GTJA SMA(r, 3, 1), masked to NaN until bar 2 (min_periods=3):
        e[2..7] = [3.666666666666667, 4.444444444444445, 4.296296296296296,
                   5.19753086419753, 4.79835390946502, 5.86556927297668]
    GTJA SMA(e, 2, 1) applied to THAT series (e's own leading NaNs at bars
    0,1 are skipped, not treated as zero), masked to NaN until the second
    valid e value (bar 3, min_periods=2):
        s[3..7] = [4.055555555555555, 4.175925925925926, 4.686728395061728,
                   4.7425411522633745, 5.304055212620027]
    result[t] = e[t] / s[t]:
        result[3..7] = [1.0958904109589043, 1.0288248337028825,
                        1.1089891340138294, 1.0117685340853624,
                        1.1058650481278236]

    Independently derived and printed by docs/measure_g191_109.py, matching
    the module's float64 output exactly (same arithmetic, no float-only
    tolerance needed for this particular example).
    """
    high = Series([12.0, 14.0, 11.0, 18.0, 10.0, 22.0, 9.0, 26.0])
    low = Series([8.0, 10.0, 8.0, 12.0, 6.0, 15.0, 5.0, 18.0])
    out = g191_109(high, low, smooth1_length=3, smooth1_weight=1,
                    smooth2_length=2, smooth2_weight=1)

    assert out.iloc[:3].isna().all()
    expected = {
        3: 1.0958904109589043,
        4: 1.0288248337028825,
        5: 1.1089891340138294,
        6: 1.0117685340853624,
        7: 1.1058650481278236,
    }
    for t, val in expected.items():
        assert out.iloc[t] == pytest.approx(val, abs=1e-9), f"bar {t}"


def test_matches_an_independent_loop_at_defaults():
    """Spot-checks 3 bars of the shipped defaults (smooth1_length=10,
    smooth1_weight=2, smooth2_length=10, smooth2_weight=2) against a
    hand-written per-bar loop using plain numpy, independent of the
    module's own pandas `.rolling()` / `.ewm()` calls."""
    high, low = _walk(900, seed=3)
    out = g191_109(high, low)
    h, l = high.to_numpy(dtype=float), low.to_numpy(dtype=float)
    n = len(h)
    s1n, s1w, s2n, s2w = 10, 2, 10, 2
    a1, a2 = s1w / s1n, s2w / s2n
    r_np = h - l

    def _sma_loop(x, alpha, min_periods):
        y = None
        count = 0
        out_ = [float("nan")] * n
        for t in range(n):
            if x[t] != x[t]:
                continue
            y = x[t] if y is None else alpha * x[t] + (1 - alpha) * y
            count += 1
            if count >= min_periods:
                out_[t] = y
        return out_

    e_np = _sma_loop(r_np, a1, s1n)
    s_np = _sma_loop(np.array(e_np, dtype=float), a2, s2n)
    result_np = [float("nan")] * n
    for t in range(n):
        if s_np[t] == s_np[t] and e_np[t] == e_np[t]:
            result_np[t] = e_np[t] / s_np[t]

    for t in (300, 600, 899):
        assert out.iloc[t] == pytest.approx(result_np[t], rel=1e-9)


def test_insufficient_history_returns_none():
    high, low = _walk(18)  # defaults need 10 + 10 - 1 = 19 bars
    assert g191_109(high, low) is None


def test_exact_min_length_fires_at_the_warmup_boundary():
    high, low = _walk(19)  # exactly 10 + 10 - 1 = 19 bars
    out = g191_109(high, low)
    assert out is not None
    assert out.iloc[:18].isna().all()
    assert pd.notna(out.iloc[18])


def test_default_name():
    high, low = _walk()
    out = g191_109(high, low)
    assert out.name == "G191_109_10_2_10_2"


def test_distinct_weights_produce_distinct_names_and_values():
    """Pins the regression round 1 of `g191_146` caught: two distinct
    INTEGER weights MUST produce two distinct column names (the name is
    the only thing mined strategy rules in the parent repo match on,
    CLAUDE.md "Naming is API") and, since the weight changes the GTJA
    `alpha = m/n`, two distinct Series of values."""
    high, low = _walk(300)
    out1 = g191_109(high, low, smooth1_length=10, smooth1_weight=1,
                     smooth2_length=5, smooth2_weight=1)
    out3 = g191_109(high, low, smooth1_length=10, smooth1_weight=3,
                     smooth2_length=5, smooth2_weight=1)
    assert out1.name != out3.name
    assert out1.name == "G191_109_10_1_5_1"
    assert out3.name == "G191_109_10_3_5_1"
    m = out1.notna() & out3.notna()
    assert (out1[m] != out3[m]).any()


def test_fractional_weights_that_truncate_the_same_are_identical():
    """`smooth1_weight`/`smooth2_weight` are coerced to `int` at validation
    time, before any math runs, so two weights that truncate to the same
    integer are the same parameter all the way through: same name AND
    bit-identical values (the fix `g191_146`'s own regression test pins
    for the identical GTJA `SMA` operator)."""
    high, low = _walk(300)
    out_21 = g191_109(high, low, smooth1_length=10, smooth1_weight=2.1,
                       smooth2_length=5, smooth2_weight=1)
    out_24 = g191_109(high, low, smooth1_length=10, smooth1_weight=2.4,
                       smooth2_length=5, smooth2_weight=1)
    assert out_21.name == out_24.name == "G191_109_10_2_5_1"
    pd.testing.assert_series_equal(out_21, out_24)


# -------------------------------------------------------------- causality


_REAL = importlib.import_module("pandas_ta.volatility.g191_109")


def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_g191_109_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


WRITE_SHIFT_MUTANT = (
    "    result = (e / s).replace([np.inf, -np.inf], np.nan)",
    "    result = ((e / s).replace([np.inf, -np.inf], np.nan)).shift(-smooth2_length)",
)
LOOKAHEAD_RANGE_MUTANT = (
    "    e = _gtja_sma(high - low, smooth1_length, smooth1_weight)",
    "    e = _gtja_sma(high.shift(-1) - low.shift(-1), smooth1_length, smooth1_weight)",  # the `bos` look-ahead bug class
)

OFFSETS = range(50, 1500, 40)  # past the 19-bar warm-up


def _leaks(fn):
    high, low = _walk(1500)
    other_h, other_l = _walk(1500, seed=97)
    base = fn(high, low)
    hits = 0
    for j in OFFSETS:
        ph, pl = high.copy(), low.copy()
        ph.iloc[j:] = other_h.iloc[j:].values
        pl.iloc[j:] = other_l.iloc[j:].values
        out = fn(ph, pl)
        a, b = base.iloc[:j], out.iloc[:j]
        if not (a.isna() == b.isna()).all():
            hits += 1
            continue
        m = a.notna()
        if (a[m] != b[m]).any():
            hits += 1
    return hits


def test_real_module_never_reads_the_future():
    assert _leaks(g191_109) == 0


def test_write_shift_mutant_is_caught():
    mod = _load_mutant(*WRITE_SHIFT_MUTANT)
    high, low = _walk(1500)
    assert not mod.g191_109(high, low).equals(g191_109(high, low))  # live
    assert _leaks(mod.g191_109) == len(list(OFFSETS))  # caught, every offset


def test_lookahead_range_mutant_is_caught():
    mod = _load_mutant(*LOOKAHEAD_RANGE_MUTANT)
    high, low = _walk(1500)
    assert not mod.g191_109(high, low).equals(g191_109(high, low))  # live
    assert _leaks(mod.g191_109) == len(list(OFFSETS))  # caught, every offset


# ------------------------------------------------------------ scale-free


@pytest.mark.parametrize("k", [8.0, 64.0])
def test_power_of_two_price_scale_is_bit_identical(k):
    high, low = _walk()
    base = g191_109(high, low)
    scaled = g191_109(high * k, low * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_other_price_scales_within_tolerance(k):
    high, low = _walk()
    base = g191_109(high, low)
    scaled = g191_109(high * k, low * k)
    assert (base.isna() == scaled.isna()).all()
    assert (base - scaled).abs().max() < 1e-9


def test_fires_and_is_not_constant():
    high, low = _walk()
    out = g191_109(high, low)
    fires = int(out.notna().sum())
    assert 0 < fires < len(out)
    assert out.dropna().nunique() > 1


def test_non_negative():
    """The column is a ratio of two GTJA SMAs of a nonnegative quantity
    (the daily range `high - low`, which cannot be negative for valid
    OHLC data), so both the numerator and denominator are non-negative
    wherever they fire, and so is their ratio."""
    high, low = _walk()
    out = g191_109(high, low).dropna()
    assert (out >= 0.0).all()


# ---------------------------------------------------------------- wiring


def test_name_registration_and_accessor():
    high, low = _walk(400)
    df = pd.DataFrame({"open": high, "high": high, "low": low, "close": high})
    assert "g191_109" in ta.Category["volatility"]
    out = df.ta.g191_109()
    assert out.name == "G191_109_10_2_10_2"
    pd.testing.assert_series_equal(out, g191_109(high, low))
    # all four tunable kwargs forwarded under their own names in one call --
    # the "supertrend failure mode" (CLAUDE.md) hasattr cannot see.
    renamed = df.ta.g191_109(smooth1_length=5, smooth1_weight=1,
                              smooth2_length=5, smooth2_weight=1)
    assert renamed.name == "G191_109_5_1_5_1"
