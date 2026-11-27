# -*- coding: utf-8 -*-
"""NM-PRICE-DENSITY-10 (issue #186): `nm_price_density_10`, Kaufman's price
density -- the sum of each bar's own high-low range over a trailing window,
divided by that window's own high-low span. Source: Kaufman 2013, Trading
Systems and Methods, 5th ed., ch. 1 "Other Measurements of Noise"; named,
undefined, in two Reddit threads only (tier 4), rd:algotrading:15xt5xt and
rd:algotrading:1nrkjby -- neither states a formula; this ships Kaufman's own
published chapter formula:

    NM_PRICE_DENSITY_10 = SUM(H - L, 10) / (MAX(H, 10) - MIN(L, 10))

Gate A derivation, causality and scale-free arguments are in the module
docstring. Gate E: SHIP, max |rho| 0.7289 vs `chop` (run
`is186-nm_price_density_10-dc9aa7c9`); row in `docs/gate_e_ledger.csv`.

WHAT THIS FILE PINS, in order of how much it would hurt to lose.

1. **Gate A, by a hand-derived fixture.** 4 bars, `length=2`, chosen so
   every division lands on a clean fraction: `H = [10, 12, 11, 9]`,
   `L = [8, 9, 7, 8]` (`range = [2, 3, 4, 1]`). Bar 1 (window [0,1]):
   `numerator = 2+3 = 5`, `denominator = max(10,12)-min(8,9) = 4`, ratio
   `5/4 = 1.25`. Bar 2 (window [1,2]): `numerator = 3+4 = 7`,
   `denominator = max(12,11)-min(9,7) = 5`, ratio `7/5 = 1.4`. Bar 3
   (window [2,3]): `numerator = 4+1 = 5`,
   `denominator = max(11,9)-min(7,8) = 4`, ratio `5/4 = 1.25`.
2. **Gate B, by future-perturbation sweep plus two mutants, each
   `importlib`-read and `exec`'d in memory.** The real module leaks at 0 of
   every swept offset on a 1,500-bar synthetic frame; both mutants -- the
   final write shifted `length` bars into the future, and `hh` (window
   high) built from a forward-looking window -- are shown live (differ
   from the real module) and caught at every swept offset.
3. **`MIN_LENGTH` is not 1.** At `length=1`, both the numerator and the
   denominator collapse to the identity window, forcing the ratio to a
   single constant (1.0, or NaN on an exact zero range) -- never anything
   else. The module itself REJECTS `length=1` (falls back to the default),
   so this is pinned on a standalone re-implementation of the formula, not
   through the module's own call.
4. **Gate C reachability** on a synthetic frame, and that a window whose
   high equals its low throughout (every bar a flat doji) blanks its own
   bar rather than leaving +-inf; a non-flat window is never blanked.
5. **Gate D**, bit-identical under a x8/x64 price rescale, within a
   measured tolerance under x10/x3.7.
6. **Five-point wiring** and the dictionary row.

Every count below comes from `docs/measure_nm_price_density_10.py`,
transcribed in docs/NmPriceDensity10Measured.md.
"""
import importlib
import types

import numpy as np
import pandas as pd
import pytest
from pandas import Series

from .context import pandas_ta as ta
from pandas_ta.volatility.nm_price_density_10 import MIN_LENGTH, nm_price_density_10

LENGTH = 10
_REAL = importlib.import_module("pandas_ta.volatility.nm_price_density_10")


# ------------------------------------------------------------- frames
def _ohlc(n=1500, seed=11):
    rng = np.random.default_rng(seed)
    close = 100.0 * np.exp(np.cumsum(rng.normal(0.0, 0.015, n)))
    rng2 = np.random.default_rng(seed + 1)
    spread = np.abs(rng2.normal(0.0, 0.01, n)) * close
    high = close + spread * rng2.uniform(0.2, 1.0, n)
    low = close - spread * rng2.uniform(0.2, 1.0, n)
    idx = pd.RangeIndex(n)
    return Series(high, index=idx), Series(low, index=idx)


HIGH, LOW = _ohlc()
_BASE = {}


def base(length=LENGTH):
    if length not in _BASE:
        _BASE[length] = nm_price_density_10(HIGH, LOW, length=length)
    return _BASE[length]


def same(a, b):
    x, y = np.asarray(a, float), np.asarray(b, float)
    return x.shape == y.shape and bool(
        np.all((x == y) | (np.isnan(x) & np.isnan(y))))


# ------------------------------------------------------------- Gate A
def test_hand_derived_four_bars():
    """H = [10, 12, 11, 9], L = [8, 9, 7, 8], length=2. Every division
    lands on a clean fraction -- see the module docstring above."""
    high = Series([10.0, 12.0, 11.0, 9.0])
    low = Series([8.0, 9.0, 7.0, 8.0])

    out = nm_price_density_10(high, low, length=2)

    assert out.name == "NM_PRICE_DENSITY_2"
    assert pd.isna(out.iloc[0])
    assert float(out.iloc[1]) == pytest.approx(1.25, abs=1e-12)
    assert float(out.iloc[2]) == pytest.approx(1.4, abs=1e-12)
    assert float(out.iloc[3]) == pytest.approx(1.25, abs=1e-12)


def test_matches_an_independent_scalar_loop():
    """Independent per-bar computation in plain Python, no pandas
    `.rolling()` calls, no shared helper with the module."""
    high, low = HIGH.iloc[:400], LOW.iloc[:400]
    length = 50
    port = nm_price_density_10(high, low, length=length)

    h = [float(v) for v in high.to_numpy()]
    l = [float(v) for v in low.to_numpy()]

    expected = [float("nan")] * len(h)
    for t in range(length - 1, len(h)):
        win_h = h[t - length + 1:t + 1]
        win_l = l[t - length + 1:t + 1]
        numerator = sum(hi - lo for hi, lo in zip(win_h, win_l))
        denom = max(win_h) - min(win_l)
        if denom == 0:
            continue
        expected[t] = numerator / denom

    oracle = Series(expected, index=high.index)
    assert (port.isna() == oracle.isna()).all()
    m = port.notna()
    assert int(m.sum()) == 400 - length + 1
    assert float((port[m] - oracle[m]).abs().max()) < 1e-9


def test_a_window_spanning_a_gap_can_read_below_one():
    """Counterexample from the module docstring's READING section: the
    ratio is NOT bounded below by 1.0 in general."""
    high = Series([5.0, 1.0])
    low = Series([4.0, 1.0])
    out = nm_price_density_10(high, low, length=2)
    assert float(out.iloc[1]) == pytest.approx(0.25, abs=1e-12)


def test_a_malformed_bar_low_above_high_is_still_masked_not_a_silent_number():
    """The module does not validate H[t] >= L[t]. On a malformed bar where
    denominator == 0 but numerator != 0 (the OHLC-consistency precondition
    disclosed in the module docstring is violated), the ratio divides to
    -inf, which the same `.replace([inf, -inf], nan)` mask still catches
    -- found during the Fletcher review of this port."""
    high = Series([5.0, 2.0])
    low = Series([5.0, 8.0])  # bar 1: low (8) above high (2)
    out = nm_price_density_10(high, low, length=2)
    assert pd.isna(out.iloc[1])


def test_the_module_docstring_attributes_the_source():
    doc = nm_price_density_10.__doc__
    for needle in ("Kaufman", "Other Measurements of Noise",
                   "rd:algotrading:15xt5xt", "rd:algotrading:1nrkjby"):
        assert needle in doc
    assert "existence" in doc.lower() and "not evidence" in doc.lower()


# ------------------------------------------------------------- min length
def _density(h, l):
    """Plain re-implementation of the length=1/2 formula on short lists."""
    rng = [hi - lo for hi, lo in zip(h, l)]
    numerator = sum(rng)
    denom = max(h) - min(l)
    if denom == 0:
        return float("nan")
    return numerator / denom


def test_a_one_bar_window_is_forced_to_one_or_nan():
    """At length=1, numerator == range[t] and denominator == H[t]-L[t]
    exactly (a 1-bar rolling sum/max/min is the identity), so the ratio is
    forced to 1.0 (or NaN on an exact zero range) -- never anything else."""
    rng = np.random.default_rng(0)
    vals = set()
    for _ in range(3000):
        low = rng.uniform(1.0, 100.0)
        high = low + rng.uniform(0.1, 50.0)
        vals.add(round(_density([high], [low]), 9))
    assert vals == {1.0}


def test_length_two_is_informative_not_a_single_forced_constant():
    rng = np.random.default_rng(1)
    vals = set()
    for _ in range(3000):
        lows = rng.uniform(1.0, 100.0, 2)
        highs = lows + rng.uniform(0.1, 50.0, 2)
        val = _density(list(highs), list(lows))
        if np.isfinite(val):
            vals.add(round(val, 6))
    assert len(vals) > 50  # a forced constant would collapse to {x}


@pytest.mark.parametrize("length", [None, 0, -5, 1, 0.5, 1.9])
def test_a_length_below_the_minimum_falls_back_to_the_default(length):
    out = nm_price_density_10(HIGH.iloc[:400], LOW.iloc[:400], length=length)
    assert out.name == "NM_PRICE_DENSITY_10"


# ------------------------------------------------------------- Gate B
def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_nm_price_density_10_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


MUTANTS = {
    "write-shift": (
        "    result = (numerator / denominator).replace([np.inf, -np.inf], np.nan)",
        "    result = (numerator / denominator).replace([np.inf, -np.inf], np.nan).shift(-length)"),
    "forward-hh": (
        "    hh = high.rolling(length, min_periods=length).max()",
        "    hh = high.rolling(length, min_periods=length).max().shift(-length)"),
}

OFFSETS = range(60, 1500, 40)  # past the 10-bar default warm-up


def _spliced(high, low, j, seed):
    """`high`/`low` with everything from bar `j` onward replaced by an
    independent synthetic path."""
    oh, ol = _ohlc(len(high), seed=seed)
    h, l = high.copy(), low.copy()
    h.iloc[j:] = oh.iloc[j:].to_numpy()
    l.iloc[j:] = ol.iloc[j:].to_numpy()
    return h, l


def _leak_offsets(fn, high, low, offsets=OFFSETS, splices=3):
    base_out = fn(high, low)
    hit = []
    for j in offsets:
        for s in range(splices):
            h, l = _spliced(high, low, j, seed=909 + 7919 * s)
            out = fn(h, l)
            a, b = base_out.iloc[:j], out.iloc[:j]
            if not (a.isna() == b.isna()).all():
                hit.append(j)
                break
            m = a.notna()
            if (a[m] != b[m]).any():
                hit.append(j)
                break
    return hit


def test_real_module_never_reads_the_future():
    assert _leak_offsets(nm_price_density_10, HIGH, LOW) == []


@pytest.mark.parametrize("name", sorted(MUTANTS))
def test_each_mutant_is_live_and_caught_at_every_swept_offset(name):
    mod = _load_mutant(*MUTANTS[name])
    assert not mod.nm_price_density_10(HIGH, LOW).equals(
        nm_price_density_10(HIGH, LOW))  # live
    hits = _leak_offsets(mod.nm_price_density_10, HIGH, LOW)
    assert len(hits) == len(list(OFFSETS)), (name, len(hits))


# ------------------------------------------------------------- Gate C
def test_every_bar_with_a_full_window_fires_on_the_default():
    s = base()
    assert int(s.notna().sum()) == len(s) - LENGTH + 1
    assert s.iloc[:LENGTH - 1].isna().all()
    assert pd.notna(s.iloc[LENGTH - 1])


def test_zero_lt_fires_lt_n_and_the_column_is_not_constant():
    s = base()
    fired = s.dropna()
    assert 0 < int(s.notna().sum()) < len(s)
    assert fired.nunique() > 1


def test_a_flat_window_blanks_its_own_bar():
    """Only the bar whose OWN trailing window is entirely flat is blanked --
    once the window slides past the flat run it picks up a non-flat bar
    again and the ratio is defined."""
    length = 10
    high = HIGH.iloc[:200].copy()
    low = LOW.iloc[:200].copy()
    high.iloc[50:50 + length] = 100.0
    low.iloc[50:50 + length] = 100.0  # every bar in the window a flat doji
    out = nm_price_density_10(high, low, length=length)
    assert pd.isna(out.iloc[50 + length - 1])
    assert pd.notna(out.iloc[50 + length])


def test_a_non_flat_window_is_never_blanked():
    high = HIGH.iloc[:200].copy()
    low = LOW.iloc[:200].copy()
    length = 10
    high.iloc[50:50 + length - 1] = 100.0
    low.iloc[50:50 + length - 1] = 100.0  # flat except the LAST bar of the window
    high.iloc[50 + length - 1] = 101.0
    low.iloc[50 + length - 1] = 100.0
    out = nm_price_density_10(high, low, length=length)
    assert pd.notna(out.iloc[50 + length - 1])


# ------------------------------------------------------------- Gate D
@pytest.mark.parametrize("k", [8.0, 64.0])
def test_power_of_two_scale_is_bit_identical(k):
    base_out = base()
    scaled = nm_price_density_10(HIGH * k, LOW * k)
    assert same(base_out, scaled)


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_other_scales_within_tolerance(k):
    base_out = base()
    scaled = nm_price_density_10(HIGH * k, LOW * k)
    assert (base_out.isna() == scaled.isna()).all()
    m = base_out.notna()
    assert float((base_out[m] - scaled[m]).abs().max()) < 1e-6


def test_a_short_input_returns_none_until_one_window_exists():
    assert nm_price_density_10(HIGH.iloc[:LENGTH - 1], LOW.iloc[:LENGTH - 1]) is None
    out = nm_price_density_10(HIGH.iloc[:LENGTH], LOW.iloc[:LENGTH])
    assert int(out.notna().sum()) == 1
    assert pd.notna(out.iloc[-1])


# ------------------------------------------------------------- edge, guards
def test_fractional_lengths_that_truncate_the_same_are_identical():
    pd.testing.assert_series_equal(
        nm_price_density_10(HIGH.iloc[:400], LOW.iloc[:400], length=50.9),
        nm_price_density_10(HIGH.iloc[:400], LOW.iloc[:400], length=50))


def test_distinct_lengths_produce_distinct_names_and_values():
    a = nm_price_density_10(HIGH.iloc[:600], LOW.iloc[:600], length=10)
    b = nm_price_density_10(HIGH.iloc[:600], LOW.iloc[:600], length=50)
    assert (a.name, b.name) == ("NM_PRICE_DENSITY_10", "NM_PRICE_DENSITY_50")
    m = a.notna() & b.notna()
    assert int(m.sum()) > 100
    assert (a[m] != b[m]).any()


def test_the_offset_and_the_fill_are_the_house_ones():
    s = nm_price_density_10(HIGH, LOW, offset=2)
    assert same(s.to_numpy()[2:], base().to_numpy()[:-2])
    s = nm_price_density_10(HIGH, LOW, fillna=-99)
    assert int(s.isna().sum()) == 0
    assert int((s == -99).sum()) == LENGTH - 1


def test_fill_method_rejects_a_typo():
    with pytest.raises(ValueError):
        nm_price_density_10(HIGH.iloc[:400], LOW.iloc[:400],
                            length=50, fill_method="bogus")


# ------------------------------------------------------------- wiring
def test_name_registration_and_accessor():
    df = pd.DataFrame({"open": HIGH, "high": HIGH, "low": LOW,
                       "close": (HIGH + LOW) / 2.0, "volume": 1.0})
    assert "nm_price_density_10" in ta.Category["volatility"]
    assert hasattr(df.ta, "nm_price_density_10")
    length = 50
    direct = nm_price_density_10(HIGH, LOW, length=length)
    through = df.ta.nm_price_density_10(length=length)
    pd.testing.assert_series_equal(through, direct, check_names=True)
    assert through.name == "NM_PRICE_DENSITY_50"
    assert direct.category == "volatility"


def test_the_dictionary_row_describes_this_column():
    import pathlib
    root = pathlib.Path(_REAL.__file__).resolve().parent.parent.parent
    text = (root / "docs" / "IndicatorDictionary.md").read_text(encoding="utf-8")
    assert "NM_PRICE_DENSITY_10" in text
    lines = [ln for ln in text.splitlines() if "nm_price_density_10" in ln]
    assert lines, "no row for nm_price_density_10 in the dictionary"
