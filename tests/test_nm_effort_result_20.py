# -*- coding: utf-8 -*-
"""NM-EFFORT-RESULT-20 (issue #185): `nm_effort_result_20`, Wyckoff's
"effort vs result" (volume vs price response) read as relative volume over
relative range -- named in two Reddit threads only (tier 4), neither of
which states a formula; this ships the issue's own stated formalisation
(identical to the screen prototype's):

    NM_EFFORT_RESULT_20 = [V / SMA20(V)] / [(H - L) / SMA20(H - L)]

Gate A derivation (there is no second, independent published formula to
derive this from -- the issue discloses that itself), causality and
scale-free arguments are in the module docstring. Gate E: pending, run by
issue-solver after this session.

WHAT THIS FILE PINS, in order of how much it would hurt to lose.

1. **Gate A, by a hand-derived fixture.** 4 bars, `length=2`, chosen so
   every division lands on a clean fraction: `V = [100, 200, 150, 300]`,
   `range = H - L = [2, 4, 1, 5]`. Bar 1: `rel_volume = 200/150 = 4/3`,
   `rel_range = 4/3`, ratio exactly `1.0`. Bar 2: `rel_volume = 150/175 =
   6/7`, `rel_range = 1/2.5 = 2/5`, ratio `15/7 = 2.142857142857143`. Bar 3:
   `rel_volume = 300/225 = 4/3`, `rel_range = 5/3`, ratio `4/5 = 0.8`.
2. **Gate B, by future-perturbation sweep plus two mutants, each
   `importlib`-read and `exec`'d in memory.** The real module leaks at 0 of
   every swept offset on a 1,500-bar synthetic frame; both mutants --
   the final write shifted `length` bars into the future, and
   `mean_volume` built from a forward-looking window -- are shown live
   (differ from the real module) and caught at every swept offset.
3. **`MIN_LENGTH` is not 1.** At `length=1` both `mean_volume` and
   `mean_range` collapse to the identity window, forcing the whole ratio to
   a single constant (1.0, or NaN on an exact zero) -- never anything else.
4. **Gate C reachability** on a synthetic frame, and that a flat (zero
   range or zero volume) trailing window blanks its own bar rather than
   leaving +-inf.
5. **Gate D**, on two independent axes (price, volume) and both together:
   bit-identical under a x8/x64 rescale, within a measured tolerance under
   x10/x3.7.
6. **Five-point wiring** and the dictionary row.

Every count below comes from `docs/measure_nm_effort_result_20.py`,
transcribed in docs/NmEffortResult20Measured.md.
"""
import importlib
import types

import numpy as np
import pandas as pd
import pytest
from pandas import Series

from .context import pandas_ta as ta
from pandas_ta.volume.nm_effort_result_20 import MIN_LENGTH, nm_effort_result_20

LENGTH = 20
_REAL = importlib.import_module("pandas_ta.volume.nm_effort_result_20")


# ------------------------------------------------------------- frames
def _ohlcv(n=1500, seed=11, vol_seed=23):
    rng = np.random.default_rng(seed)
    close = 100.0 * np.exp(np.cumsum(rng.normal(0.0, 0.015, n)))
    rng2 = np.random.default_rng(seed + 1)
    spread = np.abs(rng2.normal(0.0, 0.01, n)) * close
    high = close + spread * rng2.uniform(0.2, 1.0, n)
    low = close - spread * rng2.uniform(0.2, 1.0, n)
    rng3 = np.random.default_rng(vol_seed)
    volume = np.abs(rng3.normal(1_000_000.0, 300_000.0, n)) + 1.0
    idx = pd.RangeIndex(n)
    return (Series(high, index=idx), Series(low, index=idx),
            Series(volume, index=idx))


HIGH, LOW, VOLUME = _ohlcv()
_BASE = {}


def base(length=LENGTH):
    if length not in _BASE:
        _BASE[length] = nm_effort_result_20(HIGH, LOW, VOLUME, length=length)
    return _BASE[length]


def same(a, b):
    x, y = np.asarray(a, float), np.asarray(b, float)
    return x.shape == y.shape and bool(
        np.all((x == y) | (np.isnan(x) & np.isnan(y))))


# ------------------------------------------------------------- Gate A
def test_hand_derived_four_bars():
    """V = [100, 200, 150, 300], range = [2, 4, 1, 5], length=2. Every
    division lands on a clean fraction -- see the module docstring above."""
    volume = Series([100.0, 200.0, 150.0, 300.0])
    rng = Series([2.0, 4.0, 1.0, 5.0])
    high = rng  # low = 0 everywhere, so high - low == rng exactly
    low = Series([0.0, 0.0, 0.0, 0.0])

    out = nm_effort_result_20(high, low, volume, length=2)

    assert out.name == "NM_EFFORT_RESULT_2"
    assert pd.isna(out.iloc[0])
    assert float(out.iloc[1]) == pytest.approx(1.0, abs=1e-12)
    assert float(out.iloc[2]) == pytest.approx(15.0 / 7.0, abs=1e-12)
    assert float(out.iloc[3]) == pytest.approx(0.8, abs=1e-12)


def test_matches_an_independent_scalar_loop():
    """Independent per-bar computation in plain Python, no pandas
    `.rolling()` calls, no shared helper with the module."""
    high, low, volume = HIGH.iloc[:400], LOW.iloc[:400], VOLUME.iloc[:400]
    length = 50
    port = nm_effort_result_20(high, low, volume, length=length)

    h = [float(v) for v in high.to_numpy()]
    l = [float(v) for v in low.to_numpy()]
    v = [float(v) for v in volume.to_numpy()]
    r = [hi - lo for hi, lo in zip(h, l)]

    expected = [float("nan")] * len(v)
    for t in range(length - 1, len(v)):
        win_v = v[t - length + 1:t + 1]
        win_r = r[t - length + 1:t + 1]
        mean_v = sum(win_v) / length
        mean_r = sum(win_r) / length
        if mean_v == 0 or mean_r == 0:
            continue
        rel_v = v[t] / mean_v
        rel_r = r[t] / mean_r
        if rel_r == 0:
            continue
        expected[t] = rel_v / rel_r

    oracle = Series(expected, index=high.index)
    assert (port.isna() == oracle.isna()).all()
    m = port.notna()
    assert int(m.sum()) == 400 - length + 1
    assert float((port[m] - oracle[m]).abs().max()) < 1e-9


def test_the_module_docstring_attributes_the_source():
    doc = nm_effort_result_20.__doc__
    for needle in ("Wyckoff", "Volume Range Events", "rd:Daytrading:1k9oyhh"):
        assert needle in doc
    assert "existence" in doc.lower() and "not evidence" in doc.lower()


# ------------------------------------------------------------- min length
def _ratio(v, r):
    """Plain re-implementation of the length=1/2 formula on short lists."""
    n = len(v)
    length = n
    mean_v = sum(v) / length
    mean_r = sum(r) / length
    if mean_v == 0 or mean_r == 0:
        return float("nan")
    rel_v = v[-1] / mean_v
    rel_r = r[-1] / mean_r
    if rel_r == 0:
        return float("nan")
    return rel_v / rel_r


def test_a_one_bar_window_is_forced_to_one_or_nan():
    """At length=1, mean_volume == volume and mean_range == range exactly
    (the rolling mean of a 1-bar window is the identity), so both ratios
    are forced to 1.0 (or NaN on an exact zero) -- never anything else."""
    rng = np.random.default_rng(0)
    vals = set()
    for _ in range(3000):
        v, r = rng.uniform(1.0, 100.0, 1), rng.uniform(1.0, 100.0, 1)
        vals.add(round(_ratio(list(v), list(r)), 9))
    assert vals == {1.0}


def test_length_two_is_informative_not_a_single_forced_constant():
    rng = np.random.default_rng(1)
    vals = set()
    for _ in range(3000):
        v = rng.uniform(1.0, 100.0, 2)
        r = rng.uniform(1.0, 100.0, 2)
        val = _ratio(list(v), list(r))
        if np.isfinite(val):
            vals.add(round(val, 6))
    assert len(vals) > 50  # a forced constant would collapse to {x}


@pytest.mark.parametrize("length", [None, 0, -5, 1, 0.5, 1.9])
def test_a_length_below_the_minimum_falls_back_to_the_default(length):
    out = nm_effort_result_20(HIGH.iloc[:400], LOW.iloc[:400],
                              VOLUME.iloc[:400], length=length)
    assert out.name == "NM_EFFORT_RESULT_20"


# ------------------------------------------------------------- Gate B
def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_nm_effort_result_20_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


MUTANTS = {
    "write-shift": (
        "    result = (rel_volume / rel_range).replace([np.inf, -np.inf], np.nan)",
        "    result = (rel_volume / rel_range).replace([np.inf, -np.inf], np.nan).shift(-length)"),
    "forward-mean-volume": (
        "    mean_volume = volume.rolling(length, min_periods=length).mean()",
        "    mean_volume = volume.rolling(length, min_periods=length).mean().shift(-length)"),
}

OFFSETS = range(60, 1500, 40)  # past the 20-bar default warm-up


def _spliced(high, low, volume, j, seed):
    """`high`/`low`/`volume` with everything from bar `j` onward replaced
    by an independent synthetic path."""
    oh, ol, ov = _ohlcv(len(high), seed=seed, vol_seed=seed + 1)
    h, l, v = high.copy(), low.copy(), volume.copy()
    h.iloc[j:] = oh.iloc[j:].to_numpy()
    l.iloc[j:] = ol.iloc[j:].to_numpy()
    v.iloc[j:] = ov.iloc[j:].to_numpy()
    return h, l, v


def _leak_offsets(fn, high, low, volume, offsets=OFFSETS, splices=3):
    base_out = fn(high, low, volume)
    hit = []
    for j in offsets:
        for s in range(splices):
            h, l, v = _spliced(high, low, volume, j, seed=909 + 7919 * s)
            out = fn(h, l, v)
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
    assert _leak_offsets(nm_effort_result_20, HIGH, LOW, VOLUME) == []


@pytest.mark.parametrize("name", sorted(MUTANTS))
def test_each_mutant_is_live_and_caught_at_every_swept_offset(name):
    mod = _load_mutant(*MUTANTS[name])
    assert not mod.nm_effort_result_20(HIGH, LOW, VOLUME).equals(
        nm_effort_result_20(HIGH, LOW, VOLUME))  # live
    hits = _leak_offsets(mod.nm_effort_result_20, HIGH, LOW, VOLUME)
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


def test_a_flat_volume_window_blanks_its_own_bar():
    high, low = HIGH.iloc[:200], LOW.iloc[:200]
    volume = VOLUME.iloc[:200].copy()
    length = 20
    volume.iloc[50:50 + length] = 1000.0  # perfectly flat trailing window
    out = nm_effort_result_20(high, low, volume, length=length)
    # at bar 50+length-1 the window is [50, 50+length-1], all equal -> mean
    # equals every element, rel_volume == 1.0 (not blanked -- flat but
    # nonzero volume divides cleanly); only an ALL-ZERO window blanks.
    assert pd.notna(out.iloc[50 + length - 1])

    zero_volume = VOLUME.iloc[:200].copy()
    zero_volume.iloc[50:50 + length] = 0.0
    out_zero = nm_effort_result_20(high, low, zero_volume, length=length)
    assert pd.isna(out_zero.iloc[50 + length - 1])


def test_a_flat_range_window_blanks_its_own_bar():
    volume = VOLUME.iloc[:200]
    length = 20
    high = HIGH.iloc[:200].copy()
    low = high.copy()  # range == 0 everywhere -> mean_range == 0 in-window
    out = nm_effort_result_20(high, low, volume, length=length)
    assert out.iloc[length - 1:].isna().all()


# ------------------------------------------------------------- Gate D
@pytest.mark.parametrize("k", [8.0, 64.0])
def test_power_of_two_price_scale_is_bit_identical(k):
    base_out = base()
    scaled = nm_effort_result_20(HIGH * k, LOW * k, VOLUME)
    assert same(base_out, scaled)


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_other_price_scales_within_tolerance(k):
    base_out = base()
    scaled = nm_effort_result_20(HIGH * k, LOW * k, VOLUME)
    assert (base_out.isna() == scaled.isna()).all()
    m = base_out.notna()
    assert float((base_out[m] - scaled[m]).abs().max()) < 1e-6


@pytest.mark.parametrize("k", [8.0, 64.0])
def test_power_of_two_volume_scale_is_bit_identical(k):
    base_out = base()
    scaled = nm_effort_result_20(HIGH, LOW, VOLUME * k)
    assert same(base_out, scaled)


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_other_volume_scales_within_tolerance(k):
    base_out = base()
    scaled = nm_effort_result_20(HIGH, LOW, VOLUME * k)
    assert (base_out.isna() == scaled.isna()).all()
    m = base_out.notna()
    assert float((base_out[m] - scaled[m]).abs().max()) < 1e-6


@pytest.mark.parametrize("k", [8.0, 64.0])
def test_power_of_two_combined_scale_is_bit_identical(k):
    base_out = base()
    scaled = nm_effort_result_20(HIGH * k, LOW * k, VOLUME * k)
    assert same(base_out, scaled)


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_other_combined_scales_within_tolerance(k):
    base_out = base()
    scaled = nm_effort_result_20(HIGH * k, LOW * k, VOLUME * k)
    assert (base_out.isna() == scaled.isna()).all()
    m = base_out.notna()
    assert float((base_out[m] - scaled[m]).abs().max()) < 1e-6


def test_a_short_input_returns_none_until_one_window_exists():
    assert nm_effort_result_20(HIGH.iloc[:LENGTH - 1], LOW.iloc[:LENGTH - 1],
                               VOLUME.iloc[:LENGTH - 1]) is None
    out = nm_effort_result_20(HIGH.iloc[:LENGTH], LOW.iloc[:LENGTH],
                              VOLUME.iloc[:LENGTH])
    assert int(out.notna().sum()) == 1
    assert pd.notna(out.iloc[-1])


# ------------------------------------------------------------- edge, guards
def test_fractional_lengths_that_truncate_the_same_are_identical():
    pd.testing.assert_series_equal(
        nm_effort_result_20(HIGH.iloc[:400], LOW.iloc[:400], VOLUME.iloc[:400], length=50.9),
        nm_effort_result_20(HIGH.iloc[:400], LOW.iloc[:400], VOLUME.iloc[:400], length=50))


def test_distinct_lengths_produce_distinct_names_and_values():
    a = nm_effort_result_20(HIGH.iloc[:600], LOW.iloc[:600], VOLUME.iloc[:600], length=20)
    b = nm_effort_result_20(HIGH.iloc[:600], LOW.iloc[:600], VOLUME.iloc[:600], length=50)
    assert (a.name, b.name) == ("NM_EFFORT_RESULT_20", "NM_EFFORT_RESULT_50")
    m = a.notna() & b.notna()
    assert int(m.sum()) > 100
    assert (a[m] != b[m]).any()


def test_the_offset_and_the_fill_are_the_house_ones():
    s = nm_effort_result_20(HIGH, LOW, VOLUME, offset=2)
    assert same(s.to_numpy()[2:], base().to_numpy()[:-2])
    s = nm_effort_result_20(HIGH, LOW, VOLUME, fillna=-99)
    assert int(s.isna().sum()) == 0
    assert int((s == -99).sum()) == LENGTH - 1


def test_fill_method_rejects_a_typo():
    with pytest.raises(ValueError):
        nm_effort_result_20(HIGH.iloc[:400], LOW.iloc[:400], VOLUME.iloc[:400],
                            length=50, fill_method="bogus")


# ------------------------------------------------------------- wiring
def test_name_registration_and_accessor():
    df = pd.DataFrame({"open": HIGH, "high": HIGH, "low": LOW,
                       "close": (HIGH + LOW) / 2.0, "volume": VOLUME})
    assert "nm_effort_result_20" in ta.Category["volume"]
    assert hasattr(df.ta, "nm_effort_result_20")
    length = 50
    direct = nm_effort_result_20(HIGH, LOW, VOLUME, length=length)
    through = df.ta.nm_effort_result_20(length=length)
    pd.testing.assert_series_equal(through, direct, check_names=True)
    assert through.name == "NM_EFFORT_RESULT_50"
    assert direct.category == "volume"


def test_the_dictionary_row_describes_this_column():
    import pathlib
    root = pathlib.Path(_REAL.__file__).resolve().parent.parent.parent
    text = (root / "docs" / "IndicatorDictionary.md").read_text(encoding="utf-8")
    assert "NM_EFFORT_RESULT_20" in text
    lines = [ln for ln in text.splitlines() if "nm_effort_result_20" in ln]
    assert lines, "no row for nm_effort_result_20 in the dictionary"
