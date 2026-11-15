# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.cycles.correlation_cycle` -- Ehlers' correlation-based
cycle/phase detector, the sibling named in issue #30 of the fork's shipped
`cti` (same author, same year): correlates price against a cosine and a sine
reference wave of one period (`length`) instead of `cti`'s straight ramp.
Measurements: `docs/CorrelationCycleMeasured.md`.

⚠ READ THIS FIRST. Gate A here is self-consistency, not a source citation:
per issue #30 no file in the owner's Pine corpus mentions Correlation Cycle,
and neither Ehlers' papers nor a library's source are reachable from this
environment (no web access, no Pine corpus access). The Pearson-correlation
arithmetic is exact and independently checkable (a closed-form identity:
correlating a window of one sinusoid against a reference sinusoid of the
same frequency, over an exact integer period, returns exactly cos/sin of
their phase difference -- `test_pure_cosine_matches_closed_form` and
`test_pure_sine_matches_closed_form` derive and check this directly, not
against the module's own code). What is NOT checked against any source is
Ehlers' own window-lag convention or his "market state" sub-output -- the
module ships Real/Angle only; market state is skipped
(`docs/EhlersDspMeasured.md`). Imag is computed internally (Angle needs it)
but is not a shipped column: Gate E struck it (max |rho| 0.9353 vs
`Squeeze_Spread_pct`), recorded in `docs/CorrelationCycleMeasured.md`.

What these tests pin, in order of how much it would hurt to lose:

* CAUSALITY by future-perturbation (same harness shape as `test_pfe.py`):
  rewrite every bar from `j` onward, demand bars `[0:j]` bit-identical, over
  31 offsets. Two look-ahead mutants (`importlib` source read, the real or
  imag rolling window shifted to see one bar into the future, `exec`'d in
  memory) are each proved live, then caught at 31 of 31.
* CORRECTNESS via a closed-form identity, derived independently of the
  module's code: correlating a pure cosine (or sine) wave at exactly
  `length` against the module's own cos/sin references must read
  `cos(2*pi*(t+1)/length)` / `-sin(2*pi*(t+1)/length)` (cosine input) or
  `sin(...)` / `cos(...)` (sine input) -- not asserted by inspecting the
  source, but by what a correlation of two same-frequency sinusoids over an
  exact integer period must equal.
* SCALE-FREE: Real is a Pearson correlation coefficient, so it is provably
  invariant to `close -> close * k` for any `k > 0` (correlation is scale-
  and location-invariant); measured bit-identical under x8 and x64, and
  within tight tolerance under x10 and x3.7, with matching NaN masks. Angle
  is a rotation angle, not a price, and inherits the same invariance through
  Real/Imag (Imag computed internally, not shipped). `0 < fires < n` so a
  constant column cannot pass.
* BOUNDS: |Real| <= 1 (Cauchy-Schwarz on the Pearson formula); Angle in
  (-180, 180].
* Degenerate window (zero variance) reads NaN, not a ZeroDivisionError or a
  spurious sign.
* Wiring: `Category`, the accessor, and the column names.
"""
import importlib
import types

import numpy as np
import pandas as pd
import pytest
from pandas import DataFrame, Series

from .context import pandas_ta as ta
from pandas_ta.cycles.correlation_cycle import correlation_cycle


def _walk(n=1200, seed=11, sigma=0.02, tick=None):
    rng = np.random.default_rng(seed)
    c = 100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n)))
    if tick:
        c = np.round(c / tick) * tick
    return Series(c)


# ------------------------------------------------------------ correctness


def test_pure_cosine_matches_closed_form():
    length, n = 20, 300
    i = np.arange(n)
    close = Series(np.cos(2 * np.pi * i / length))
    out = correlation_cycle(close, length=length)

    t = np.arange(length - 1, n)
    expected_real = np.cos(2 * np.pi * (t + 1) / length)
    expected_imag = -np.sin(2 * np.pi * (t + 1) / length)
    expected_angle = np.degrees(np.arctan2(expected_imag, expected_real))

    real = out[f"CC_REAL_{length}"].to_numpy()[length - 1:]
    angle = out[f"CC_ANGLE_{length}"].to_numpy()[length - 1:]
    assert np.allclose(real, expected_real, atol=1e-9)
    # (angle - expected) mod 360, mapped to (-180, 180]: a +-180 degree point
    # can land on either side of atan2's branch cut by float noise alone, a
    # 360-degree jump that is not a real mismatch.
    angle_diff = (angle - expected_angle + 180) % 360 - 180
    assert np.allclose(angle_diff, 0.0, atol=1e-9)
    assert out[f"CC_REAL_{length}"].iloc[:length - 1].isna().all()
    assert out[f"CC_ANGLE_{length}"].iloc[:length - 1].isna().all()


def test_pure_sine_matches_closed_form():
    length, n = 20, 300
    i = np.arange(n)
    close = Series(np.sin(2 * np.pi * i / length))
    out = correlation_cycle(close, length=length)

    t = np.arange(length - 1, n)
    expected_real = np.sin(2 * np.pi * (t + 1) / length)
    expected_imag = np.cos(2 * np.pi * (t + 1) / length)
    expected_angle = np.degrees(np.arctan2(expected_imag, expected_real))

    real = out[f"CC_REAL_{length}"].to_numpy()[length - 1:]
    angle = out[f"CC_ANGLE_{length}"].to_numpy()[length - 1:]
    assert np.allclose(real, expected_real, atol=1e-9)
    angle_diff = (angle - expected_angle + 180) % 360 - 180
    assert np.allclose(angle_diff, 0.0, atol=1e-9)
    assert out[f"CC_REAL_{length}"].iloc[:length - 1].isna().all()
    assert out[f"CC_ANGLE_{length}"].iloc[:length - 1].isna().all()


def test_flat_window_reads_nan_not_an_error():
    close = Series([5.0] * 50)
    out = correlation_cycle(close, length=10)
    assert out["CC_REAL_10"].iloc[9:].isna().all()
    assert out["CC_ANGLE_10"].iloc[9:].isna().all()


def test_bounded():
    out = correlation_cycle(_walk(tick=0.05)).dropna()
    assert (out["CC_REAL_20"].abs() <= 1 + 1e-9).all()
    assert (out["CC_ANGLE_20"] > -180 - 1e-9).all() and (out["CC_ANGLE_20"] <= 180 + 1e-9).all()


# -------------------------------------------------------------- causality

_REAL = importlib.import_module("pandas_ta.cycles.correlation_cycle")

MUTANTS = {
    "real_shift": (
        "    real = close.rolling(length).apply(\n"
        "        lambda y: _pearson_r(y, cos_wave, cos_sum, cos2_sum, length), raw=True)",
        "    real = close.shift(-1).rolling(length).apply(\n"
        "        lambda y: _pearson_r(y, cos_wave, cos_sum, cos2_sum, length), raw=True)",
    ),
    "imag_shift": (
        "    imag = close.rolling(length).apply(\n"
        "        lambda y: _pearson_r(y, sin_wave, sin_sum, sin2_sum, length), raw=True)",
        "    imag = close.shift(-1).rolling(length).apply(\n"
        "        lambda y: _pearson_r(y, sin_wave, sin_sum, sin2_sum, length), raw=True)",
    ),
}

OFFSETS = range(40, 1100, 35)  # 31 offsets


def _load_mutant(old, new, tag):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType(f"_cc_mutant_{tag}")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


def _leaks(fn):
    close = _walk()
    base = fn(close)
    other = _walk(seed=99)
    hits = 0
    for j in OFFSETS:
        pert = close.copy()
        pert.iloc[j:] = other.iloc[j:].values
        out = fn(pert)
        for col in ("CC_REAL_20", "CC_ANGLE_20"):
            a, b = base[col].iloc[:j], out[col].iloc[:j]
            if not (a.isna() == b.isna()).all():
                hits += 1
                break
            m = a.notna()
            if (a[m] != b[m]).any():
                hits += 1
                break
    return hits


def test_real_module_never_reads_the_future():
    assert _leaks(correlation_cycle) == 0


@pytest.mark.parametrize("tag", sorted(MUTANTS))
def test_mutant_is_caught(tag):
    mod = _load_mutant(*MUTANTS[tag], tag)
    close = _walk()
    assert not mod.correlation_cycle(close).equals(correlation_cycle(close))  # live
    assert _leaks(mod.correlation_cycle) == len(OFFSETS)  # caught, 31 of 31


# ------------------------------------------------------------ scale-free


@pytest.mark.parametrize("k", [8.0, 64.0])
def test_power_of_two_scale_is_bit_identical(k):
    close = _walk(tick=0.05)
    base, scaled = correlation_cycle(close), correlation_cycle(close * k)
    for col in ("CC_REAL_20", "CC_ANGLE_20"):
        assert (base[col].isna() == scaled[col].isna()).all()
        m = base[col].notna()
        assert (base[col][m] == scaled[col][m]).all()


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_other_scales_within_tolerance(k):
    close = _walk(tick=0.05)
    base, scaled = correlation_cycle(close), correlation_cycle(close * k)
    for col in ("CC_REAL_20", "CC_ANGLE_20"):
        assert (base[col].isna() == scaled[col].isna()).all()
        assert (base[col] - scaled[col]).abs().max() < 1e-9


def test_columns_are_not_constant():
    out = correlation_cycle(_walk(tick=0.05)).dropna()
    assert out["CC_REAL_20"].nunique() > 100
    assert out["CC_ANGLE_20"].nunique() > 100
    assert 0 < len(out) < len(_walk(tick=0.05))


# ---------------------------------------------------------------- wiring


def test_name_registration_and_accessor():
    close = _walk(200)
    df = DataFrame({"open": close, "high": close, "low": close,
                    "close": close, "volume": 1.0})
    assert "correlation_cycle" in ta.Category["cycles"]
    out = df.ta.correlation_cycle()
    assert list(out.columns) == ["CC_REAL_20", "CC_ANGLE_20"]
    pd.testing.assert_frame_equal(out, correlation_cycle(close))
    custom = df.ta.correlation_cycle(length=10)
    assert list(custom.columns) == ["CC_REAL_10", "CC_ANGLE_10"]
