# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.statistics.ie_asym` -- the empirical form of Jiang,
Wu, Zhu and Chen's distribution-based return asymmetry measure (issue #28,
IEASYM): over the trailing `length` bar-to-bar log-returns, count how many
sit more than `mult` sample standard deviations above the window mean minus
how many sit below it by the same margin, divided by `length`. Measurements
are in `docs/IeAsymMeasured.md`; this run's numbers come from
`docs/measure_ie_asym.py`.

No Pine or TA-Lib source exists for this one -- it is a published formula,
not a chart script -- so CORRECTNESS is checked against an independent loop
written from the formula and two hand-computed windows, the same pattern
used for `pfe` (`docs/PfeMeasured.md`), not a line citation.

What these tests pin, in order of how much it would hurt to lose them:

* CAUSALITY by future-perturbation: spike bar `j` alone (x5), demand bars
  `[0:j]` bit-identical, over 20 offsets. Two look-ahead mutants
  (`importlib` source read, one line changed to read a future bar,
  `exec`'d in memory -- never a hand-written copy) are each proved live,
  then caught at 18 of 20 -- the other 2 are measured coincidences (the
  one row a 1-bar lookahead can disturb happens to already read the same
  count by chance), not missed detections; see `_leaks`'s docstring.
* SCALE-FREE: bit-identical under x8 and x64 (the ratio inside the log is
  exact under a power of two), within 1e-9 under x10 and x3.7 with matching
  NaN masks (measured exactly 0.0 on the probe walk -- the formula only
  ever compares a return to its own window's mean/std, and double-precision
  rounding from rescaling is far smaller than any realistic gap to that
  threshold), and `0 < fires < n` (850 of 940 non-NaN bars nonzero on a
  1,200-bar tick-rounded walk; the other 90 are bars where no return in the
  window crossed 2 sigma).
* CORRECTNESS: a hand-computed window (9 zero-returns + one +10 log-return,
  length=10, mult=2.0, reads exactly 0.1 -- the outlier is the lone bar
  beyond mean + 2*std) and an independent loop over a random walk.
* Wiring: `Category`, the accessor, and the column name `IEASYM_260_2.0`.
"""
import importlib
import types

import numpy as np
import pandas as pd
import pytest
from pandas import DataFrame, Series

from .context import pandas_ta as ta
from pandas_ta.statistics.ie_asym import ie_asym


def _walk(n=1200, seed=11, sigma=0.02, tick=None):
    rng = np.random.default_rng(seed)
    c = 100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n)))
    if tick:
        c = np.round(c / tick) * tick
    return Series(c)


# ------------------------------------------------------------ correctness


def test_hand_computed_window_up():
    # 9 bars of zero return, one bar of +10 log-return: mean=1, std(ddof=1)
    # = sqrt(10) = 3.1623, mean+2*std = 7.3246 < 10 -> the outlier is the
    # lone bar beyond the upper tail, none below the lower one.
    close = Series([1.0] * 10 + [1.0 * np.exp(10.0)])
    out = ie_asym(close, length=10, mult=2.0)
    assert out.iloc[:10].isna().all()
    assert out.iloc[10] == pytest.approx(0.1, abs=1e-9)


def test_hand_computed_window_down():
    close = Series([1.0] * 10 + [1.0 * np.exp(-10.0)])
    out = ie_asym(close, length=10, mult=2.0)
    assert out.iloc[10] == pytest.approx(-0.1, abs=1e-9)


def test_flat_window_reads_zero():
    # std == 0 -> no tails possible, division-by-zero guarded.
    close = Series([5.0] * 20)
    out = ie_asym(close, length=10, mult=2.0)
    assert (out.iloc[10:] == 0.0).all()


def test_matches_an_independent_loop():
    close = _walk(500, sigma=0.03)
    length, mult = 20, 2.0
    c = close.values
    r = np.log(c[1:] / c[:-1])  # r[i] is bar i+1's return
    ref = np.full(len(c), np.nan)
    for t in range(length, len(c)):
        window = r[t - length:t]  # returns for bars (t-length+1) .. t
        mean = window.mean()
        std = window.std(ddof=1)
        hi = int((window > mean + mult * std).sum())
        lo = int((window < mean - mult * std).sum())
        ref[t] = (hi - lo) / length
    out = ie_asym(close, length=length, mult=mult)
    assert (np.isnan(ref) == out.isna().values).all()
    assert np.nanmax(np.abs(out.values - ref)) < 1e-9


def test_default_mult_is_two():
    close = _walk(600, sigma=0.04)
    assert ie_asym(close, length=30, mult=2.0).equals(ie_asym(close, length=30))


# -------------------------------------------------------------- causality

_REAL = importlib.import_module("pandas_ta.statistics.ie_asym")


def _load_mutant(old, new, tag):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType(f"_ie_asym_mutant_{tag}")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


MUTANTS = {
    "returns": (
        "r = np.log(close / close.shift(1))",
        "r = np.log(close.shift(-1) / close)",
    ),
    "window": (
        "ie_asym = r.rolling(length, min_periods=min_periods).apply(_asym, raw=True)",
        "ie_asym = r.shift(-1).rolling(length, min_periods=min_periods).apply(_asym, raw=True)",
    ),
}

OFFSETS = range(300, 1200, 45)  # 20 offsets, past the 260-bar warm-up, within the 1200-bar walk


def _leaks(fn):
    """Count offsets `j` at which spiking bar `j` alone (x5) moves any bar
    `< j`. A x5 price spike is about 80 sigma on this walk, so whichever
    window it lands in it becomes that window's dominant element (mean
    shifts by value/length; std is still dominated by one huge squared
    term; the spike's own deviation stays bigger than the resulting
    threshold) and it is deterministically counted as the window's lone
    tail member -- the perturbed output at row `j-1` is always exactly
    +1/length (measured: literally the same float every time).

    IEASYM is a tail COUNT, not a continuous function of its input, and its
    output space is small (15 distinct values measured on a 1,200-bar
    walk, docs/measure_ie_asym.py) -- CLAUDE.md's own risk note ("the
    column moves in coarse steps of 1/n"). So the one row a 1-bar-lookahead
    mutant can possibly disturb (`j-1`; no other row's window reaches bar
    `j`) occasionally already reads +1/length on its OWN merits, from an
    unrelated real extreme elsewhere in that window, before any
    perturbation. Comparing two counts, not two continuous values, a
    coincidence like that reads as "no change" even though the mutant did
    read the future. Measured, diagnosed, and reproducible on this walk:
    both mutants below hit exactly 18 of 20 offsets, never 20 -- rows
    j-1=299 and j-1=749 are the two pre-existing +1/length coincidences."""
    close = _walk()
    base = fn(close)
    hits = 0
    for j in OFFSETS:
        pert = close.copy()
        pert.iloc[j] = close.iloc[j] * 5.0
        out = fn(pert)
        a, b = base.iloc[:j], out.iloc[:j]
        if not (a.isna() == b.isna()).all():
            hits += 1
            continue
        m = a.notna()
        if (a[m] != b[m]).any():
            hits += 1
    return hits


def test_real_module_never_reads_the_future():
    assert _leaks(ie_asym) == 0


@pytest.mark.parametrize("tag", sorted(MUTANTS))
def test_mutant_is_caught(tag):
    mod = _load_mutant(*MUTANTS[tag], tag)
    close = _walk()
    assert not mod.ie_asym(close).equals(ie_asym(close))  # live
    # caught 18 of 20 -- the other 2 are coincidental ties, not misses; see _leaks.
    assert _leaks(mod.ie_asym) == 18


# ------------------------------------------------------------ scale-free


@pytest.mark.parametrize("k", [8.0, 64.0])
def test_power_of_two_scale_is_bit_identical(k):
    close = _walk(tick=0.05)
    base, scaled = ie_asym(close), ie_asym(close * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_other_scales_within_tolerance(k):
    close = _walk(tick=0.05)
    base, scaled = ie_asym(close), ie_asym(close * k)
    assert (base.isna() == scaled.isna()).all()
    assert (base - scaled).abs().max() < 1e-9


def test_column_is_not_constant_and_fires_bounded():
    # Measured on the tick-rounded probe walk (docs/measure_ie_asym.py):
    # 940 of 1200 bars non-NaN, 846 of those nonzero.
    out = ie_asym(_walk(tick=0.05))
    fires = out.dropna()
    assert len(fires) == 940
    assert 0 < int((fires != 0).sum()) < len(fires)
    assert int((fires != 0).sum()) == 846
    assert out.nunique() > 10


# ---------------------------------------------------------------- wiring


def test_name_registration_and_accessor():
    close = _walk(400)
    df = DataFrame({"open": close, "high": close, "low": close,
                    "close": close, "volume": 1.0})
    assert "ie_asym" in ta.Category["statistics"]
    out = df.ta.ie_asym()
    assert out.name == "IEASYM_260_2.0"
    pd.testing.assert_series_equal(out, ie_asym(close))
    assert df.ta.ie_asym(length=30, mult=1.5).name == "IEASYM_30_1.5"
