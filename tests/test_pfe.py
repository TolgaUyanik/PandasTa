# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.momentum.pfe` -- Hannula's Polarized Fractal
Efficiency in log-percent form (vertical leg 100 * log-return, one unit
across per bar). Measurements and the open Gate E are in
`docs/PfeMeasured.md`.

⚠ READ THIS FIRST.  This is NOT Hannula's published formula.  He measures
the vertical leg in raw price, which mixes price units with bar counts and
is not scale-free; this uses 100 * log-return.  It also replaces the task's
first candidate, `signed_er`, which was built and removed because,
unsmoothed, it equals `cmo(talib=False) / 100` (`docs/SignedErMeasured.md`).
The log-percent form keeps a VOLATILITY dependence on purpose -- on bars
that move far less than 1%, |PFE| is pushed toward 100 whatever the trend.
`test_calm_series_saturates` pins that, so the flaw cannot be forgotten.

What these tests pin, in order of how much it would hurt to lose them:

* CAUSALITY by future-perturbation: rewrite every bar from `j` onward,
  demand bars `[0:j]` bit-identical, over 31 offsets.  Two look-ahead
  mutants (`importlib` source read, one index shifted forward, `exec`'d in
  memory -- never a hand-written copy) are each proved live, then caught at
  31 of 31.  NaN masks are compared before values, because a bare `!=` on
  NaN passes a null mutant.
* SCALE-FREE: bit-identical under x8 and x64 (a price ratio is exact under a
  power of two -- the reason the step is `log(close / close[1])` and not a
  difference of logs), within 1e-12 under x10 and x3.7 with matching NaN
  masks (measured 1.7e-13 / 2.7e-13), and `0 < fires < n` (1,190 of
  1,200; the 10 that do not fire are the warm-up).
* The round-trip regression: a window that returns to its starting tick
  reads exactly 0, not +-100 (the bug the x10 test found during the port).
* CORRECTNESS against an independent loop written from the formula, not
  from the module, and two hand-computed windows: a straight line reads
  100, and steps (+1, +1, -1) read 100 * sqrt(10) / (3 * sqrt(2)).
* BOUND: |raw| <= 100 holds in exact arithmetic (triangle inequality on the
  per-bar vectors (step, 1), whose sum is (net, length)); checked to 1e-9.
* Wiring: `Category`, the accessor, and the column name `PFE_10_5`.
"""
import importlib
import types

import numpy as np
import pandas as pd
import pytest
from pandas import DataFrame, Series

from .context import pandas_ta as ta
from pandas_ta.momentum.pfe import pfe


def _walk(n=1200, seed=11, sigma=0.02, tick=None):
    rng = np.random.default_rng(seed)
    c = 100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n)))
    if tick:
        c = np.round(c / tick) * tick  # tick rounding produces flat bars
    return Series(c)


def _from_steps(steps):
    """Closes whose 100*log-returns are exactly `steps` (up to rounding)."""
    return Series(100.0 * np.exp(np.cumsum([0.0] + list(steps)) / 100.0))


# ------------------------------------------------------------ correctness


def test_straight_line_reads_100():
    raw = pfe(_from_steps([2.0, 2.0, 2.0]), length=3, smooth=1)
    assert raw.iloc[:3].isna().all()
    assert raw.iloc[3] == pytest.approx(100.0, abs=1e-9)
    assert pfe(_from_steps([-2.0] * 3), length=3, smooth=1).iloc[3] \
        == pytest.approx(-100.0, abs=1e-9)


def test_hand_computed_zigzag():
    raw = pfe(_from_steps([1.0, 1.0, -1.0]), length=3, smooth=1)
    expected = 100 * np.sqrt(1 + 9) / (3 * np.sqrt(2))  # 74.5356
    assert raw.iloc[3] == pytest.approx(expected, abs=1e-9)


def test_matches_an_independent_loop():
    close = _walk(400)
    n = 10
    c = close.values
    ref = np.full(len(c), np.nan)
    for t in range(n, len(c)):
        steps = [100 * np.log(c[i] / c[i - 1]) for i in range(t - n + 1, t + 1)]
        net = sum(steps)
        path = sum(np.sqrt(s * s + 1) for s in steps)
        ref[t] = 100 * np.sign(net) * np.sqrt(net * net + n * n) / path
    raw = pfe(close, length=n, smooth=1)
    assert (np.isnan(ref) == raw.isna().values).all()
    assert np.nanmax(np.abs(raw.values - ref)) < 1e-9


def test_smoothing_is_a_plain_ewm_of_the_raw():
    close = _walk()
    raw = pfe(close, smooth=1)
    expected = raw.ewm(span=5, adjust=False).mean()
    assert (pfe(close) - expected).abs().max() == 0.0


def test_bounded():
    for sigma in (0.001, 0.02, 0.1):
        raw = pfe(_walk(sigma=sigma, tick=0.05), smooth=1).dropna()
        assert (raw.abs() <= 100 + 1e-9).all()


def test_flat_window_reads_zero():
    close = Series([5.0] * 30 + list(np.linspace(5, 8, 30)))
    raw = pfe(close, length=10, smooth=1)
    assert (raw.iloc[11:30] == 0.0).all()


def test_round_trip_window_reads_exactly_zero():
    """Regression: with net summed from per-bar log-returns, a window that
    returns to its starting tick summed to +-1e-16 and sign() made it
    +-100. Found by the x10 tolerance test (max diff 47.8 on a tick-rounded
    walk). On tick-rounded data every bar whose close equals the close
    `length` bars back must read exactly 0."""
    close = _walk(3000, tick=0.05)
    raw = pfe(close, smooth=1)
    same = close == close.shift(10)
    assert same.sum() == 6  # quoted in docs/PfeMeasured.md
    assert (raw[same] == 0.0).all()


def test_calm_series_saturates():
    """The disclosed flaw, measured: median |raw| is 99.6 on a 0.1%-per-bar
    walk and 36.7 on a 5% walk (3,000 bars, seed 1)."""
    calm = pfe(_walk(3000, seed=1, sigma=0.001), smooth=1).abs().median()
    wild = pfe(_walk(3000, seed=1, sigma=0.05), smooth=1).abs().median()
    assert calm > 99 and wild < 40


# -------------------------------------------------------------- causality

_REAL = importlib.import_module("pandas_ta.momentum.pfe")


def _load_mutant(old, new, tag):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType(f"_pfe_mutant_{tag}")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


MUTANTS = {
    "net": ("net = 100 * log(close / close.shift(length))",
            "net = 100 * log(close.shift(-1) / close.shift(length - 1))"),
    "path": ("path = sqrt(step * step + 1).rolling(length).sum()",
             "path = sqrt(step * step + 1).shift(-1).rolling(length).sum()"),
}

OFFSETS = range(40, 1100, 35)  # 31 offsets


def _leaks(fn):
    """Count offsets `j` at which rewriting bars >= j moves any bar < j."""
    close = _walk()
    base = fn(close)
    other = _walk(seed=99)
    hits = 0
    for j in OFFSETS:
        pert = close.copy()
        pert.iloc[j:] = other.iloc[j:].values
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
    assert _leaks(pfe) == 0


@pytest.mark.parametrize("tag", sorted(MUTANTS))
def test_mutant_is_caught(tag):
    mod = _load_mutant(*MUTANTS[tag], tag)
    close = _walk()
    assert not mod.pfe(close).equals(pfe(close))  # live
    assert _leaks(mod.pfe) == len(OFFSETS)        # caught, 31 of 31


# ------------------------------------------------------------ scale-free


@pytest.mark.parametrize("k", [8.0, 64.0])
def test_power_of_two_scale_is_bit_identical(k):
    close = _walk(tick=0.05)
    base, scaled = pfe(close), pfe(close * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_other_scales_within_tolerance(k):
    close = _walk(tick=0.05)
    base, scaled = pfe(close), pfe(close * k)
    assert (base.isna() == scaled.isna()).all()
    assert (base - scaled).abs().max() < 1e-12


def test_column_is_not_constant():
    # `< len(out)` alone is vacuous (warm-up NaNs); a constant ±100 column would pass it.
    out = pfe(_walk(tick=0.05)).dropna()
    assert out.nunique() > 100
    assert int((out > 0).sum()) == 612 and int((out < 0).sum()) == 578


# ---------------------------------------------------------------- wiring


def test_name_registration_and_accessor():
    close = _walk(200)
    df = DataFrame({"open": close, "high": close, "low": close,
                    "close": close, "volume": 1.0})
    assert "pfe" in ta.Category["momentum"]
    out = df.ta.pfe()
    assert out.name == "PFE_10_5"
    pd.testing.assert_series_equal(out, pfe(close))
    assert df.ta.pfe(length=7, smooth=3).name == "PFE_7_3"
