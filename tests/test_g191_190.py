# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.statistics.g191_190` -- Guotai Junan's (2017,
"GTJA191") alpha `#190`, per issue #59:
`LOG((COUNT(r>g,20)-1)*SUMIF((r-g)^2,r<g,20) / (COUNT(r<g,20)*SUMIF((r-g)^2,
r>g,20)))`, `g = (C/C19)^(1/20)-1`, matching the issue's own prototype
(`docs/issues/screen/ind_screen.py:570-579`). Gate A derivation is in the
module docstring and `docs/G191190Measured.md`. Gate E is pending
(CLAUDE.md, "Owed, not failed").

What these pin, in order of how much it would hurt to lose:

* CAUSALITY by future-perturbation: rewrite every close bar from `j`
  onward (another synthetic series), demand bars `[0:j]` bit-identical with
  matching NaN masks, over offsets past the 39-bar warm-up. Two mutants
  (`importlib` source read, `exec`'d in memory), each shown live (differs
  from the real module) then caught at every offset: shifting the final
  write index `length=20` bars into the future, and turning `g`'s backward
  `DELAY(close, length-1)` into a FORWARD shift.
* CORRECTNESS: a hand-derived example at `length=4` (geometric-mean
  lookback 3), where every term (`r`, `g`, `up`, `dn`, `e2`, `num`, `den`)
  is traced independently. A second spot check at the shipped default
  against an independent per-bar loop using plain numpy array slicing, on
  a 900-bar frame.
* REACHABILITY (Gate C): on a 1500-bar synthetic frame at the shipped
  default, the column fires on a non-trivial fraction of bars and is not
  constant -- the quantity is defined only where the ratio inside `LOG` is
  strictly positive, so a mutant that collapsed the denominator to zero
  everywhere would pass every other check and still be wrong.
* SCALE-FREE: `r` and `g` are both return RATIOS, exactly invariant under
  any positive price rescale (the `k` cancels before any other arithmetic
  runs), so the whole column -- built entirely from `r` and `g` -- is
  scale-free by construction. Bit-identical under close x8/x64
  (power-of-two, exact in IEEE754), within float64 tolerance under
  x10/x3.7. Matching NaN masks, plus `0 < fires < n` and `nunique > 1`.
* Wiring: `Category`, the accessor, the column name `G191_190_20`.
"""
import importlib
import types

import numpy as np
import pandas as pd
import pytest
from pandas import Series

from .context import pandas_ta as ta
from pandas_ta.statistics.g191_190 import g191_190


def _close(n=1500, seed=11, sigma=0.015):
    rng = np.random.default_rng(seed)
    close = 100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n)))
    return Series(close, index=pd.RangeIndex(n))


# ------------------------------------------------------------ correctness


def _expected_at(c, t, length):
    """Independent per-bar computation using plain numpy array slicing and
    explicit python loops over the trailing window, not the module's own
    vectorised `.rolling()` calls."""
    g_lookback = length - 1
    r_t = c[t] / c[t - 1] - 1.0
    g_t = (c[t] / c[t - g_lookback]) ** (1.0 / length) - 1.0

    count_up = count_dn = 0
    sum_e2_dn = sum_e2_up = 0.0
    for i in range(t - length + 1, t + 1):
        r_i = c[i] / c[i - 1] - 1.0
        g_i = (c[i] / c[i - g_lookback]) ** (1.0 / length) - 1.0
        e2_i = (r_i - g_i) ** 2
        if r_i > g_i:
            count_up += 1
            sum_e2_up += e2_i
        elif r_i < g_i:
            count_dn += 1
            sum_e2_dn += e2_i

    num = (count_up - 1) * sum_e2_dn
    den = count_dn * sum_e2_up
    if den == 0:
        return float("nan")
    ratio = num / den
    return np.log(ratio) if ratio > 0 else float("nan")


def test_hand_derived_small_example():
    """length=4 (geometric-mean lookback 3). close chosen so every bar in
    the last window is traceable by hand; checked against `_expected_at`,
    an independent per-bar loop, and the exact values are printed by
    `python docs/measure_g191_190.py`."""
    close = Series([10.0, 10.5, 9.8, 11.0, 10.2, 12.0, 11.5, 13.0, 9.0, 10.0])
    out = g191_190(close, length=4)

    assert out.iloc[:6].isna().all()  # 2*4-2 = 6 bars of warm-up
    c = close.to_numpy(dtype=float)
    for t in (6, 7, 8, 9):
        expected = _expected_at(c, t, 4)
        if np.isnan(expected):
            assert pd.isna(out.iloc[t]), f"bar {t}"
        else:
            assert out.iloc[t] == pytest.approx(expected, abs=1e-9), f"bar {t}"


def test_matches_an_independent_loop_at_defaults():
    """Spot-checks 3 bars of the shipped default (length=20) against an
    independent per-bar computation."""
    close = _close(900, seed=5)
    out = g191_190(close)
    c = close.to_numpy(dtype=float)

    checked_any = False
    for t in (300, 600, 899):
        expected = _expected_at(c, t, 20)
        if np.isnan(expected):
            assert pd.isna(out.iloc[t]), f"bar {t}"
            continue
        checked_any = True
        assert out.iloc[t] == pytest.approx(expected, rel=1e-9), f"bar {t}"
    assert checked_any  # at least one of the three spot-checks is defined


def test_insufficient_history_returns_none():
    close = _close(38)  # defaults need 2*length-1 = 39 bars
    assert g191_190(close) is None


def test_exact_min_length_bars_before_warmup_are_nan():
    close = _close(39)  # exactly 2*length-1 = 39 bars
    out = g191_190(close)
    assert out is not None
    assert out.iloc[:38].isna().all()  # 2*length-2 = 38 NaN bars


def test_default_name():
    close = _close()
    out = g191_190(close)
    assert out.name == "G191_190_20"


def test_distinct_lengths_produce_distinct_names_and_values():
    close = _close(900)
    out1 = g191_190(close, length=10)
    out2 = g191_190(close, length=30)
    assert out1.name != out2.name
    assert out1.name == "G191_190_10"
    assert out2.name == "G191_190_30"
    m = out1.notna() & out2.notna()
    assert (out1[m] != out2[m]).any()


# ------------------------------------------------------------ reachability


def test_fires_on_a_non_trivial_fraction_and_is_not_constant():
    close = _close()  # 1500 bars, defaults
    out = g191_190(close)
    fires = int(out.notna().sum())
    assert fires > 100  # well above a handful of coincidental positive ratios
    assert out.dropna().nunique() > 1


# -------------------------------------------------------------- causality


_REAL = importlib.import_module("pandas_ta.statistics.g191_190")


def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_g191_190_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


WRITE_SHIFT_MUTANT = (
    "result = pd.Series(result, index=close.index)",
    "result = pd.Series(result, index=close.index).shift(-length)",  # a length-bar look-ahead
)
FORWARD_DELAY_MUTANT = (
    "g = (close / close.shift(g_lookback)) ** (1.0 / length) - 1.0",
    "g = (close / close.shift(-g_lookback)) ** (1.0 / length) - 1.0",  # DELAY turned into a look-ahead
)

OFFSETS = range(150, 1500, 40)  # past the 39-bar warm-up


def _leaks(fn):
    close = _close(1500)
    other_c = _close(1500, seed=97)
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
    assert _leaks(g191_190) == 0


def test_write_shift_mutant_is_caught():
    mod = _load_mutant(*WRITE_SHIFT_MUTANT)
    close = _close(1500)
    assert not mod.g191_190(close).equals(g191_190(close))  # live
    assert _leaks(mod.g191_190) == len(list(OFFSETS))  # caught, every offset


def test_forward_delay_mutant_is_caught():
    mod = _load_mutant(*FORWARD_DELAY_MUTANT)
    close = _close(1500)
    assert not mod.g191_190(close).equals(g191_190(close))  # live
    assert _leaks(mod.g191_190) == len(list(OFFSETS))  # caught, every offset


# ------------------------------------------------------------ scale-free


@pytest.mark.parametrize("k", [8.0, 64.0])
def test_power_of_two_price_scale_is_bit_identical(k):
    close = _close()
    base = g191_190(close)
    scaled = g191_190(close * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_other_price_scales_within_tolerance(k):
    close = _close()
    base = g191_190(close)
    scaled = g191_190(close * k)
    assert (base.isna() == scaled.isna()).all()
    assert (base - scaled).abs().max() < 1e-9


def test_fires_and_is_not_constant():
    close = _close()
    out = g191_190(close)
    fires = int(out.notna().sum())
    assert 0 < fires < len(out)
    assert out.dropna().nunique() > 1


# ---------------------------------------------------------------- wiring


def test_name_registration_and_accessor():
    close = _close(400)
    df = pd.DataFrame({"open": close, "high": close, "low": close, "close": close,
                        "volume": close})
    assert "g191_190" in ta.Category["statistics"]
    out = df.ta.g191_190()
    assert out.name == "G191_190_20"
    pd.testing.assert_series_equal(out, g191_190(close))
    renamed = df.ta.g191_190(length=10)
    assert renamed.name == "G191_190_10"
