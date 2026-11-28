# -*- coding: utf-8 -*-
"""B2-VOL-ABOVE-MID-20 (issue #188): `b2_vol_above_mid_20` -- share of a
trailing 20-bar window's own volume that traded on bars closing strictly
above that window's own midpoint, `(HHV(high,20) + LLV(low,20)) / 2`. Crowd
talk (Reddit, tier 4, rd:algotrading:1whq9hv), the poster's own words quoted
in full in the module docstring. Existence, not evidence: nothing here tests
the poster's claimed use. Gate E: pending, run by issue-solver after this
session.

WHAT THIS FILE PINS, in order of how much it would hurt to lose.

1. **Gate A, by a hand-derived fixture.** 4 bars, `length=4`: `high=[10,12,9,11]`,
   `low=[8,7,8,9]`, `close=[9,11,8.5,10]`, `volume=[100,200,150,300]`. HHV=12,
   LLV=7, mid=9.5. Closes above: bars 1 (11) and 3 (10); volume 200+300=500 of
   a 750 total; ratio exactly `2/3`.
2. **Gate B, by future-perturbation sweep plus two mutants, each
   `importlib`-read and `exec`'d in memory.** The real module leaks at 0 of
   every swept offset; both mutants -- the final write shifted `length` bars
   into the future, and `mid` built from a forward-looking window -- are
   shown live (differ from the real module) and caught at every swept offset.
3. **Only one masking condition: a zero-volume window.** Unlike
   `nm_effort_result_20`'s two independent divisions, there is a single
   division here (`vol_above / vol_total`); a zero-RANGE window (every
   `high == low == close`) still produces a DEFINED ratio (0.0, since no bar
   can close strictly above a midpoint that equals its own close) -- it does
   NOT blank, which is the one place this port's masking differs from a
   naive port of `nm_effort_result_20`'s pattern.
4. **Gate C reachability** on a synthetic frame, and that `length=1` is
   informative (both 0 and 1 occur), not a forced single constant.
5. **Gate D**, on two independent axes (price, volume) and both together:
   bit-identical under a x8/x64 rescale, within a measured tolerance under
   x10/x3.7.
6. **Five-point wiring** and the dictionary row.

Every count below comes from `docs/measure_b2_vol_above_mid_20.py`,
transcribed in docs/B2VolAboveMid20Measured.md.
"""
import importlib
import types

import numpy as np
import pandas as pd
import pytest
from pandas import Series

from .context import pandas_ta as ta
from pandas_ta.volume.b2_vol_above_mid_20 import b2_vol_above_mid_20

LENGTH = 20
_REAL = importlib.import_module("pandas_ta.volume.b2_vol_above_mid_20")


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
            Series(close, index=idx), Series(volume, index=idx))


HIGH, LOW, CLOSE, VOLUME = _ohlcv()
_BASE = {}


def base(length=LENGTH):
    if length not in _BASE:
        _BASE[length] = b2_vol_above_mid_20(HIGH, LOW, CLOSE, VOLUME, length=length)
    return _BASE[length]


def same(a, b):
    x, y = np.asarray(a, float), np.asarray(b, float)
    return x.shape == y.shape and bool(
        np.all((x == y) | (np.isnan(x) & np.isnan(y))))


# ------------------------------------------------------------- Gate A
def test_hand_derived_four_bars():
    """high=[10,12,9,11], low=[8,7,8,9], close=[9,11,8.5,10],
    volume=[100,200,150,300], length=4 -- see the module docstring above."""
    high = Series([10.0, 12.0, 9.0, 11.0])
    low = Series([8.0, 7.0, 8.0, 9.0])
    close = Series([9.0, 11.0, 8.5, 10.0])
    volume = Series([100.0, 200.0, 150.0, 300.0])

    out = b2_vol_above_mid_20(high, low, close, volume, length=4)

    assert out.name == "B2_VOL_ABOVE_MID_4"
    assert out.iloc[:3].isna().all()
    assert float(out.iloc[3]) == pytest.approx(2.0 / 3.0, abs=1e-12)


def test_matches_an_independent_scalar_loop():
    """Independent per-bar computation in plain Python, no pandas
    `.rolling()` or numpy `sliding_window_view` calls, no shared helper with
    the module."""
    high, low = HIGH.iloc[:400], LOW.iloc[:400]
    close, volume = CLOSE.iloc[:400], VOLUME.iloc[:400]
    length = 50
    port = b2_vol_above_mid_20(high, low, close, volume, length=length)

    h = [float(x) for x in high.to_numpy()]
    l = [float(x) for x in low.to_numpy()]
    c = [float(x) for x in close.to_numpy()]
    v = [float(x) for x in volume.to_numpy()]

    expected = [float("nan")] * len(v)
    for t in range(length - 1, len(v)):
        win_h = h[t - length + 1:t + 1]
        win_l = l[t - length + 1:t + 1]
        win_c = c[t - length + 1:t + 1]
        win_v = v[t - length + 1:t + 1]
        mid = (max(win_h) + min(win_l)) / 2.0
        tot = sum(win_v)
        if tot == 0:
            continue
        above = sum(vi for ci, vi in zip(win_c, win_v) if ci > mid)
        expected[t] = above / tot

    oracle = Series(expected, index=high.index)
    assert (port.isna() == oracle.isna()).all()
    m = port.notna()
    assert int(m.sum()) == 400 - length + 1
    assert float((port[m] - oracle[m]).abs().max()) < 1e-9


def test_the_module_docstring_attributes_the_source():
    doc = b2_vol_above_mid_20.__doc__
    for needle in ("Reddit", "rd:algotrading:1whq9hv"):
        assert needle in doc
    assert "existence" in doc.lower() and "not evidence" in doc.lower()


@pytest.mark.parametrize("length", [None, 0, -5, 0.5])
def test_a_length_at_or_below_zero_falls_back_to_the_default(length):
    out = b2_vol_above_mid_20(HIGH.iloc[:400], LOW.iloc[:400],
                              CLOSE.iloc[:400], VOLUME.iloc[:400], length=length)
    assert out.name == "B2_VOL_ABOVE_MID_20"


# ------------------------------------------------------------- min length
def test_a_one_bar_window_is_informative_not_a_forced_constant():
    """At length=1, mid[t] = (high[t] + low[t]) / 2, the bar's own midpoint;
    the ratio collapses to a plain {0.0, 1.0} flag (did this bar close in
    the top half of its own range), which still varies bar to bar -- not
    forced to one single value the way nm_effort_result_20's length=1
    collapses."""
    out = b2_vol_above_mid_20(HIGH.iloc[:400], LOW.iloc[:400],
                              CLOSE.iloc[:400], VOLUME.iloc[:400], length=1)
    vals = set(np.round(out.dropna().to_numpy(), 9))
    assert vals == {0.0, 1.0}
    assert (out == 0.0).sum() > 0
    assert (out == 1.0).sum() > 0


# ------------------------------------------------------------- Gate B
def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_b2_vol_above_mid_20_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


MUTANTS = {
    "write-shift": (
        "    result = Series(out, index=close.index)",
        "    result = Series(out, index=close.index).shift(-length)"),
    "forward-mid": (
        "    mid = (hhv + llv) / 2.0",
        "    mid = (hhv + llv) / 2.0\n    mid = mid.shift(-length)"),
}

OFFSETS = range(60, 1500, 40)  # past the 20-bar default warm-up


def _spliced(high, low, close, volume, j, seed):
    """`high`/`low`/`close`/`volume` with everything from bar `j` onward
    replaced by an independent synthetic path."""
    oh, ol, oc, ov = _ohlcv(len(high), seed=seed, vol_seed=seed + 1)
    h, l, c, v = high.copy(), low.copy(), close.copy(), volume.copy()
    h.iloc[j:] = oh.iloc[j:].to_numpy()
    l.iloc[j:] = ol.iloc[j:].to_numpy()
    c.iloc[j:] = oc.iloc[j:].to_numpy()
    v.iloc[j:] = ov.iloc[j:].to_numpy()
    return h, l, c, v


def _leak_offsets(fn, high, low, close, volume, offsets=OFFSETS, splices=3):
    base_out = fn(high, low, close, volume)
    hit = []
    for j in offsets:
        for s in range(splices):
            h, l, c, v = _spliced(high, low, close, volume, j, seed=909 + 7919 * s)
            out = fn(h, l, c, v)
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
    assert _leak_offsets(b2_vol_above_mid_20, HIGH, LOW, CLOSE, VOLUME) == []


@pytest.mark.parametrize("name", sorted(MUTANTS))
def test_each_mutant_is_live_and_caught_at_every_swept_offset(name):
    mod = _load_mutant(*MUTANTS[name])
    assert not mod.b2_vol_above_mid_20(HIGH, LOW, CLOSE, VOLUME).equals(
        b2_vol_above_mid_20(HIGH, LOW, CLOSE, VOLUME))  # live
    hits = _leak_offsets(mod.b2_vol_above_mid_20, HIGH, LOW, CLOSE, VOLUME)
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
    assert float(fired.min()) >= 0.0
    assert float(fired.max()) <= 1.0


def test_a_zero_volume_window_blanks_its_own_bar():
    high, low, close = HIGH.iloc[:200], LOW.iloc[:200], CLOSE.iloc[:200]
    length = 20
    volume = VOLUME.iloc[:200].copy()
    volume.iloc[50:50 + length] = 0.0  # every bar in this window has 0 volume
    out = b2_vol_above_mid_20(high, low, close, volume, length=length)
    assert pd.isna(out.iloc[50 + length - 1])


def test_a_flat_price_window_computes_a_defined_zero_not_a_blank():
    """high == low == close == a CONSTANT level throughout the window: mid
    equals that same constant exactly, so no bar can close STRICTLY above
    it -- the ratio is a defined 0.0, not NaN, as long as volume is nonzero.
    This is the one place this port's masking differs from
    nm_effort_result_20's own zero-range-blanks-everything behaviour (see
    the module docstring)."""
    volume = VOLUME.iloc[:200]
    length = 20
    flat = Series(100.0, index=HIGH.iloc[:200].index)
    out = b2_vol_above_mid_20(flat, flat, flat, volume, length=length)
    assert out.iloc[length - 1:].notna().all()
    assert (out.iloc[length - 1:] == 0.0).all()


# ------------------------------------------------------------- Gate D
@pytest.mark.parametrize("k", [8.0, 64.0])
def test_power_of_two_price_scale_is_bit_identical(k):
    base_out = base()
    scaled = b2_vol_above_mid_20(HIGH * k, LOW * k, CLOSE * k, VOLUME)
    assert same(base_out, scaled)


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_other_price_scales_within_tolerance(k):
    base_out = base()
    scaled = b2_vol_above_mid_20(HIGH * k, LOW * k, CLOSE * k, VOLUME)
    assert (base_out.isna() == scaled.isna()).all()
    m = base_out.notna()
    assert float((base_out[m] - scaled[m]).abs().max()) < 1e-6


@pytest.mark.parametrize("k", [8.0, 64.0])
def test_power_of_two_volume_scale_is_bit_identical(k):
    base_out = base()
    scaled = b2_vol_above_mid_20(HIGH, LOW, CLOSE, VOLUME * k)
    assert same(base_out, scaled)


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_other_volume_scales_within_tolerance(k):
    base_out = base()
    scaled = b2_vol_above_mid_20(HIGH, LOW, CLOSE, VOLUME * k)
    assert (base_out.isna() == scaled.isna()).all()
    m = base_out.notna()
    assert float((base_out[m] - scaled[m]).abs().max()) < 1e-6


@pytest.mark.parametrize("k", [8.0, 64.0])
def test_power_of_two_combined_scale_is_bit_identical(k):
    base_out = base()
    scaled = b2_vol_above_mid_20(HIGH * k, LOW * k, CLOSE * k, VOLUME * k)
    assert same(base_out, scaled)


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_other_combined_scales_within_tolerance(k):
    base_out = base()
    scaled = b2_vol_above_mid_20(HIGH * k, LOW * k, CLOSE * k, VOLUME * k)
    assert (base_out.isna() == scaled.isna()).all()
    m = base_out.notna()
    assert float((base_out[m] - scaled[m]).abs().max()) < 1e-6


def test_a_short_input_returns_none_until_one_window_exists():
    assert b2_vol_above_mid_20(HIGH.iloc[:LENGTH - 1], LOW.iloc[:LENGTH - 1],
                               CLOSE.iloc[:LENGTH - 1], VOLUME.iloc[:LENGTH - 1]) is None
    out = b2_vol_above_mid_20(HIGH.iloc[:LENGTH], LOW.iloc[:LENGTH],
                              CLOSE.iloc[:LENGTH], VOLUME.iloc[:LENGTH])
    assert int(out.notna().sum()) == 1
    assert pd.notna(out.iloc[-1])


# ------------------------------------------------------------- edge, guards
def test_fractional_lengths_that_truncate_the_same_are_identical():
    pd.testing.assert_series_equal(
        b2_vol_above_mid_20(HIGH.iloc[:400], LOW.iloc[:400], CLOSE.iloc[:400],
                            VOLUME.iloc[:400], length=50.9),
        b2_vol_above_mid_20(HIGH.iloc[:400], LOW.iloc[:400], CLOSE.iloc[:400],
                            VOLUME.iloc[:400], length=50))


def test_distinct_lengths_produce_distinct_names_and_values():
    a = b2_vol_above_mid_20(HIGH.iloc[:600], LOW.iloc[:600], CLOSE.iloc[:600],
                            VOLUME.iloc[:600], length=20)
    b = b2_vol_above_mid_20(HIGH.iloc[:600], LOW.iloc[:600], CLOSE.iloc[:600],
                            VOLUME.iloc[:600], length=50)
    assert (a.name, b.name) == ("B2_VOL_ABOVE_MID_20", "B2_VOL_ABOVE_MID_50")
    m = a.notna() & b.notna()
    assert int(m.sum()) > 100
    assert (a[m] != b[m]).any()


def test_the_offset_and_the_fill_are_the_house_ones():
    s = b2_vol_above_mid_20(HIGH, LOW, CLOSE, VOLUME, offset=2)
    assert same(s.to_numpy()[2:], base().to_numpy()[:-2])
    s = b2_vol_above_mid_20(HIGH, LOW, CLOSE, VOLUME, fillna=-99)
    assert int(s.isna().sum()) == 0
    assert int((s == -99).sum()) == LENGTH - 1


def test_fill_method_rejects_a_typo():
    with pytest.raises(ValueError):
        b2_vol_above_mid_20(HIGH.iloc[:400], LOW.iloc[:400], CLOSE.iloc[:400],
                            VOLUME.iloc[:400], length=50, fill_method="bogus")


# ------------------------------------------------------------- wiring
def test_name_registration_and_accessor():
    df = pd.DataFrame({"open": HIGH, "high": HIGH, "low": LOW, "close": CLOSE,
                       "volume": VOLUME})
    assert "b2_vol_above_mid_20" in ta.Category["volume"]
    assert hasattr(df.ta, "b2_vol_above_mid_20")
    length = 50
    direct = b2_vol_above_mid_20(HIGH, LOW, CLOSE, VOLUME, length=length)
    through = df.ta.b2_vol_above_mid_20(length=length)
    pd.testing.assert_series_equal(through, direct, check_names=True)
    assert through.name == "B2_VOL_ABOVE_MID_50"
    assert direct.category == "volume"


def test_the_dictionary_row_describes_this_column():
    import pathlib
    root = pathlib.Path(_REAL.__file__).resolve().parent.parent.parent
    text = (root / "docs" / "IndicatorDictionary.md").read_text(encoding="utf-8")
    assert "B2_VOL_ABOVE_MID_20" in text
    lines = [ln for ln in text.splitlines() if "b2_vol_above_mid_20" in ln]
    assert lines, "no row for b2_vol_above_mid_20 in the dictionary"
