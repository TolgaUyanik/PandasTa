# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.volume.a101_026` -- Kakushadze's (2016, Wilmott)
Alpha101 `#26`, per issue #44: volume and high are each time-series ranked
within their own trailing window, the two rank series are rolling-correlated,
and the trailing peak of that correlation is negated. Gate A derivation is in
the module docstring and `docs/A101026Measured.md`. Gate E is pending
(CLAUDE.md, "Owed, not failed").

What these pin, in order of how much it would hurt to lose:

* CAUSALITY by future-perturbation: rewrite every high/volume bar from `j`
  onward (another synthetic frame), demand bars `[0:j]` bit-identical with
  matching NaN masks, over offsets past the warm-up. A `(corr_length +
  max_length)`-bar look-ahead mutant (`importlib` source read, the final
  write shifted from `result = -peak` to `result = -peak.shift(-(corr_length
  + max_length))`, `exec`'d in memory) is proved live, then caught at every
  offset. (A single-bar lookahead was tried first and rejected: the rolling
  max absorbs a 1-bar forward peek whenever the shifted value isn't the new
  window maximum, catching only 10 of 30 offsets -- re-derivable via
  `docs/measure_a101_026.py`'s `rejected 1-bar-lookahead mutant` line -- a
  smoothing artefact of the max step, not a causality gap. Shifting the
  whole write index by `corr_length + max_length` bars widens the affected
  window enough to be caught every time.)
* CORRECTNESS: a hand-derived 8-bar example at `vol_rank_length=3,
  high_rank_length=3, corr_length=3, max_length=2` (small enough windows
  that the rank/correlation/max arithmetic can be checked by hand), plus an
  independent per-bar loop at the shipped defaults (`vol_rank_length=5,
  high_rank_length=5, corr_length=5, max_length=3`) built from
  `numpy.corrcoef` and an explicit counting loop, not from pandas' own
  `.rolling().corr()` / `.rolling().max()`.
* MID-STREAM NaN: `corr(ts_rank(volume,5), ts_rank(high,5), 5)` is undefined
  (NaN) whenever a trailing 5-bar window of either rank series has zero
  variance -- a real property of correlating a quantised rank series, not a
  bug -- and `rolling(3).max()` correctly propagates that NaN forward.
  `docs/measure_a101_026.py` measures 238 such mid-stream NaNs past the
  10-bar leading warm-up on a 1,500-bar synthetic walk (see
  docs/A101026Measured.md).
  The independent-loop test's bar 899 is one of them: both the module and
  the hand-rolled reference agree it is NaN, not merely close.
* SCALE-FREE: bit-identical under high x8/x64 AND under volume x8/x64
  independently (`ts_rank` is an order statistic, invariant to monotonic
  rescale; `corr` of two already-rank series inherits it twice over),
  exactly (not merely within tolerance) under x10/x3.7, matching NaN masks,
  plus `0 < fires < n` and more than one distinct value.
* Wiring: `Category`, the accessor, the column name `A101_026_5_5_5_3`.
"""
import importlib
import types

import numpy as np
import pandas as pd
import pytest
from pandas import Series

from .context import pandas_ta as ta
from pandas_ta.volume.a101_026 import a101_026


def _frame(n=1500, seed=11, sigma=0.015):
    rng = np.random.default_rng(seed)
    close = 100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n)))
    noise = np.abs(rng.normal(0.0, 0.3, n))
    high = close + noise
    volume = 1000.0 * np.exp(np.cumsum(rng.normal(0.0, sigma * 1.3, n)))
    idx = pd.RangeIndex(n)
    return Series(high, index=idx), Series(volume, index=idx)


# ------------------------------------------------------------ correctness


def test_hand_derived_eight_bars_at_small_windows():
    """vol_rank_length=high_rank_length=corr_length=3, max_length=2.

    V = [10, 12, 9, 15, 20, 11, 25, 18]   (volume)
    H = [100, 90, 150, 60, 200, 30, 300, 400]   (high)

    ts_rank(x, 3)[t] = count(x[t-2:t+1] <= x[t]) / 3. Hand-counted:
      VR = [nan, nan, 1/3, 1.0, 1.0, 1/3, 1.0, 2/3]
      HR = [nan, nan, 1.0, 1/3, 1.0, 1/3, 1.0, 1.0]
    corr(VR, HR, 3)[t] for t=4..7, by the Pearson formula on each 3-point
    window (worked by hand with fractions, not re-run through the module):
      t=4: VR=[1/3,1,1], HR=[1,1/3,1]      -> corr = -0.5
      t=5: VR=[1,1,1/3], HR=[1/3,1,1/3]    -> corr = +0.5
      t=6: VR=[1,1/3,1], HR=[1,1/3,1] (identical) -> corr = +1.0
      t=7: VR=[1/3,1,2/3], HR=[1/3,1,1]    -> corr = sqrt(3)/2 = 0.8660254
    ts_max(corr, 2)[t] = max(corr[t-1], corr[t]):
      t=5: max(-0.5, 0.5) = 0.5   -> result = -0.5
      t=6: max(0.5, 1.0) = 1.0    -> result = -1.0
      t=7: max(1.0, 0.8660254) = 1.0 -> result = -1.0
    Derived by hand from the formula, confirmed against the module output in
    docs/measure_a101_026.py (not merely asserted).
    """
    V = Series([10.0, 12.0, 9.0, 15.0, 20.0, 11.0, 25.0, 18.0])
    H = Series([100.0, 90.0, 150.0, 60.0, 200.0, 30.0, 300.0, 400.0])
    out = a101_026(H, V, vol_rank_length=3, high_rank_length=3, corr_length=3, max_length=2)

    assert out.iloc[0:5].isna().all()
    assert out.iloc[5] == pytest.approx(-0.5, abs=1e-9)
    assert out.iloc[6] == pytest.approx(-1.0, abs=1e-9)
    assert out.iloc[7] == pytest.approx(-1.0, abs=1e-9)


def test_matches_an_independent_loop_at_defaults():
    """Spot-checks 3 bars of the shipped defaults (vol_rank_length=5,
    high_rank_length=5, corr_length=5, max_length=3) against a hand-written
    loop using an explicit counting rank and `numpy.corrcoef`, independent of
    the module's `pandas .rolling().corr()` / `.rolling().max()` calls. Bar
    899 is a mid-stream NaN (a 5-bar rank window with zero variance makes
    `corr` undefined there) -- the reference loop reproduces that NaN too,
    rather than silently dropping it the way Python's bare `max()` would."""
    high, volume = _frame(900, seed=3)
    out = a101_026(high, volume)

    h = high.to_numpy(dtype=float)
    v = volume.to_numpy(dtype=float)
    vol_rank_length = high_rank_length = corr_length = 5
    max_length = 3

    def rank_at(x, t, length):
        window = x[t - length + 1:t + 1]
        return float(np.count_nonzero(window <= window[-1])) / length

    def corr_at(t):
        a = np.array([rank_at(v, i, vol_rank_length) for i in range(t - corr_length + 1, t + 1)])
        b = np.array([rank_at(h, i, high_rank_length) for i in range(t - corr_length + 1, t + 1)])
        return np.corrcoef(a, b)[0, 1]

    def expected_at(t):
        vals = [corr_at(i) for i in range(t - max_length + 1, t + 1)]
        if any(np.isnan(x) for x in vals):
            return np.nan
        return -max(vals)

    for t in (300, 500):
        assert out.iloc[t] == pytest.approx(expected_at(t), rel=1e-9)
    assert np.isnan(expected_at(899))
    assert np.isnan(out.iloc[899])


def test_insufficient_history_returns_none():
    high, volume = _frame(10)  # defaults need max(5,5)+5+3-2 = 11 bars
    assert a101_026(high, volume) is None


def test_default_name():
    high, volume = _frame()
    out = a101_026(high, volume)
    assert out.name == "A101_026_5_5_5_3"


# -------------------------------------------------------------- causality


_REAL = importlib.import_module("pandas_ta.volume.a101_026")


def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_a101_026_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


MUTANT = (
    "result = -peak",
    "result = -peak.shift(-8)",  # an 8 = (corr_length + max_length)-bar look-ahead
)

OFFSETS = range(300, 900, 40)  # past the 10-bar warm-up


def _leaks(fn):
    high, volume = _frame(900)
    other_h, other_v = _frame(900, seed=97)
    base = fn(high, volume)
    hits = 0
    for j in OFFSETS:
        ph, pv = high.copy(), volume.copy()
        ph.iloc[j:] = other_h.iloc[j:].values
        pv.iloc[j:] = other_v.iloc[j:].values
        out = fn(ph, pv)
        a, b = base.iloc[:j], out.iloc[:j]
        if not (a.isna() == b.isna()).all():
            hits += 1
            continue
        m = a.notna()
        if (a[m] != b[m]).any():
            hits += 1
    return hits


def test_real_module_never_reads_the_future():
    assert _leaks(a101_026) == 0


def test_lookahead_mutant_is_caught():
    mod = _load_mutant(*MUTANT)
    high, volume = _frame(900)
    assert not mod.a101_026(high, volume).equals(a101_026(high, volume))  # live
    assert _leaks(mod.a101_026) == len(OFFSETS)  # caught, every offset


# ------------------------------------------------------------ scale-free


@pytest.mark.parametrize("k", [8.0, 64.0])
def test_power_of_two_high_scale_is_bit_identical(k):
    high, volume = _frame(900)
    base = a101_026(high, volume)
    scaled = a101_026(high * k, volume)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("k", [8.0, 64.0])
def test_power_of_two_volume_scale_is_bit_identical(k):
    high, volume = _frame(900)
    base = a101_026(high, volume)
    scaled = a101_026(high, volume * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_other_high_scales_within_tolerance(k):
    high, volume = _frame(900)
    base = a101_026(high, volume)
    scaled = a101_026(high * k, volume)
    assert (base.isna() == scaled.isna()).all()
    assert (base - scaled).abs().max() < 1e-9


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_other_volume_scales_within_tolerance(k):
    high, volume = _frame(900)
    base = a101_026(high, volume)
    scaled = a101_026(high, volume * k)
    assert (base.isna() == scaled.isna()).all()
    assert (base - scaled).abs().max() < 1e-9


def test_fires_and_is_not_constant():
    high, volume = _frame()
    out = a101_026(high, volume)
    fires = int(out.notna().sum())
    assert 0 < fires < len(out)
    assert out.dropna().nunique() > 1


def test_mismatched_index_raises():
    high, volume = _frame(900)
    bad_volume = volume.copy()
    bad_volume.index = bad_volume.index + 1
    with pytest.raises(ValueError):
        a101_026(high, bad_volume)


# ---------------------------------------------------------------- wiring


def test_name_registration_and_accessor():
    high, volume = _frame(900)
    df = pd.DataFrame({"open": high, "high": high, "low": high,
                        "close": high, "volume": volume})
    assert "a101_026" in ta.Category["volume"]
    out = df.ta.a101_026()
    assert out.name == "A101_026_5_5_5_3"
    pd.testing.assert_series_equal(out, a101_026(high, volume))
    renamed = df.ta.a101_026(vol_rank_length=3, high_rank_length=3, corr_length=3, max_length=2)
    assert renamed.name == "A101_026_3_3_3_2"
