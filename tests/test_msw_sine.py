# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.cycles.msw_sine` -- MESA Sine, fixed-period DFT
form (issue #146). Published source: John Ehlers, "MESA Sine Wave
Indicator" (Stocks & Commodities, Apr 1996) / Rocket Science for Traders
(Wiley, 2001) ch. 11. `docs/MswSineMeasured.md` carries the measured
numbers (Gate E pending at commit time); every number quoted here is
printed by `python docs/measure_msw_sine_proxy.py`.

This module is the sister of `tests/test_msw_lead.py` (issue #145): same
phase arithmetic, only the final output line differs (`sin(phase)` here vs
`sin(phase + pi/4)` there), so the test shape mirrors it one for one.

What these tests pin, in order of how much it would hurt to lose them:

* CAUSALITY by future-perturbation: rewrite every bar from `j` onward,
  demand bars `[0:j]` bit-identical, over 31 offsets. Two look-ahead
  mutants (`importlib` source read, `exec`'d in memory) are each proved
  live, then caught at 31 of 31: `real_lookahead` reads `close.shift(-1)`
  into the real-part rolling dot product, `write_shift` writes bar t's
  result to bar t-1. NaN masks are compared before values, because a bare
  `!=` on NaN passes a null mutant.
  ⚠ A degenerate mutant was tried and rejected, same as `msw_lead`'s:
  shifting the IMAGINARY part's rolling input the same way is invisible to
  this exact test, because Ehlers' sine weight at the window's newest
  position (Count=0) is `sin(0) = 0` -- the one bar the shift newly reads
  into that window is always multiplied by zero. It is live overall
  (measured: differs on 1,178 of 1,181 non-NaN bars -- see
  `docs/measure_msw_sine_proxy.py`'s "mutant liveness" section) but the
  single prefix index whose dependency crosses any offset `j` is always
  exactly that zero-weight bar,
  so no `j` can catch it this way. A real-part shift has no such hole
  (`cos(0) = 1`), which is why it is used instead.
* CORRECTNESS against an independent loop written from Ehlers' published
  pseudocode -- plain Python `for` loops over `Count = 0..length-1` with
  `Count=0` the current bar -- not from the module's vectorized rolling/dot
  form: NaN masks match, max|diff| measured below 1e-9 on 1,200 bars.
* SCALE-FREE: bit-identical under x8 and x64 (the guard and the dot
  products are both linear in `close`, so a power-of-two rescale is exact),
  within 1e-9 under x10 and x3.7 with matching NaN masks, and `0 < fires <
  n`.
* BOUND: a sine of an angle, so |MSW_SINE| <= 1 always; checked exactly.
* Wiring: `Category`, the accessor, and the column name `MSW_SINE_20`.
"""
import importlib
import types

import numpy as np
import pandas as pd
import pytest
from pandas import DataFrame, Series

from .context import pandas_ta as ta
from pandas_ta.cycles.msw_sine import msw_sine


def _walk(n=1200, seed=11, sigma=0.02, tick=None):
    rng = np.random.default_rng(seed)
    c = 100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n)))
    if tick:
        c = np.round(c / tick) * tick
    return Series(c)


def _loop_reference(close, length=20):
    """Ehlers' published pseudocode, as plain loops: Count=0 is the current
    bar, Count=length-1 the oldest bar in the window."""
    c = close.to_numpy(dtype=float)
    n = len(c)
    out = np.full(n, np.nan)
    for t in range(length - 1, n):
        window = c[t - length + 1: t + 1]
        real = imag = 0.0
        for count in range(length):
            price = window[length - 1 - count]
            real += price * np.cos(2 * np.pi * count / length)
            imag += price * np.sin(2 * np.pi * count / length)
        eps = 0.001 * c[t]
        if abs(real) > eps:
            phase = np.arctan(imag / real)
        else:
            phase = (np.pi / 2) * np.sign(imag)
        phase += (np.pi / 2) + (np.pi if real < 0 else 0.0)
        phase %= 2 * np.pi
        out[t] = np.sin(phase)
    return out


# ------------------------------------------------------------ correctness


def test_matches_an_independent_loop():
    close = _walk(400)
    out = msw_sine(close)
    ref = _loop_reference(close)
    assert (np.isnan(out.to_numpy()) == np.isnan(ref)).all()
    assert np.nanmax(np.abs(out.to_numpy() - ref)) < 1e-9


def test_bounded():
    out = msw_sine(_walk(tick=0.05)).dropna()
    assert (out.abs() <= 1.0 + 1e-9).all()


def test_warmup_length_minus_one():
    out = msw_sine(_walk(), length=20)
    assert out.iloc[:19].isna().all()
    assert out.iloc[19:].notna().all()


# -------------------------------------------------------------- causality


_REAL = importlib.import_module("pandas_ta.cycles.msw_sine")


def _load_mutant(old, new, tag):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType(f"_msw_sine_mutant_{tag}")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


MUTANTS = {
    "real_lookahead": ("real = close.rolling(length)", "real = close.shift(-1).rolling(length)"),
    "write_shift": ("sine = Series(np.sin(phase), index=close.index)",
                     "sine = Series(np.sin(phase), index=close.index).shift(-1)"),
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
    assert _leaks(msw_sine) == 0


@pytest.mark.parametrize("tag", sorted(MUTANTS))
def test_mutant_is_caught(tag):
    mod = _load_mutant(*MUTANTS[tag], tag)
    close = _walk()
    assert not mod.msw_sine(close).equals(msw_sine(close))  # live
    assert _leaks(mod.msw_sine) == len(OFFSETS)             # caught, 31 of 31


# ------------------------------------------------------------ scale-free


@pytest.mark.parametrize("k", [8.0, 64.0])
def test_power_of_two_scale_is_bit_identical(k):
    close = _walk(tick=0.05)
    base, scaled = msw_sine(close), msw_sine(close * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_other_scales_within_tolerance(k):
    close = _walk(tick=0.05)
    base, scaled = msw_sine(close), msw_sine(close * k)
    assert (base.isna() == scaled.isna()).all()
    assert (base - scaled).abs().max() < 1e-9


def test_column_fires_and_is_not_constant():
    out = msw_sine(_walk(tick=0.05)).dropna()
    assert 0 < len(out) < 1200
    assert out.nunique() > 100
    assert 0 < int((out > 0).sum()) < len(out)


# ---------------------------------------------------------------- wiring


def test_name_registration_and_accessor():
    close = _walk(200)
    df = DataFrame({"open": close, "high": close, "low": close,
                    "close": close, "volume": 1.0})
    assert "msw_sine" in ta.Category["cycles"]
    out = df.ta.msw_sine()
    assert out.name == "MSW_SINE_20"
    pd.testing.assert_series_equal(out, msw_sine(close))
    assert df.ta.msw_sine(length=10).name == "MSW_SINE_10"
