# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.statistics.level_shift_size` -- Kats tsfeatures'
`get_level_shift_features` `max` (the size of the largest jump between
consecutive sliding-window means) on a rolling window of log close.
Measurements are in docs/LevelShiftSizeMeasured.md.

What these pin, in order of how much it would hurt to lose:

* CORRECTNESS against the source: Kats' two-line formula (issue #163's
  text), transcribed independently (a plain Python loop, not the module's
  cumsum vectorisation) and matched at every bar of a GARCH frame, and a
  closed form: a single persistent level shift inside the window produces a
  known, hand-computed max diff.
* CAUSALITY: bars before a deliberate single level shift are bit-identical
  whether or not the shift ever happens, at five shift positions, and a
  mutant (the write index moved one bar earlier) proved live and caught at
  every position. A bad close moves exactly the bars whose window holds it.
* SCALE-FREE: bit-identical under a price rescale (x8/x64) because the
  window is fed `log(close / its own first close)`, whose ratio is
  bit-identical under a power-of-two rescale -- unlike the position
  companion `level_shift_idx`, this column reports a continuous value, not
  a discrete index, so it cannot rely on rounding-before-argmax for
  determinism and needs the ratio trick instead -- and within tolerance
  under x10/x3.7; the column fires and is not constant.
* Edge cases (flat price reads 0.0, not NaN; bad/short input; the length
  floor; chunk boundaries) and wiring (`Category`, the accessor,
  `LEVELSHIFTSIZE_100`).
"""
import importlib
import types

import numpy as np
import pandas as pd
import pytest
from pandas import Series

from .context import pandas_ta as ta

_REAL = importlib.import_module("pandas_ta.statistics.level_shift_size")
level_shift_size = _REAL.level_shift_size
WINDOW_SIZE = _REAL.WINDOW_SIZE
MIN_LENGTH = _REAL.MIN_LENGTH


def _garch(n=600, seed=0, a=0.1, b=0.85):
    """Closes from GARCH(1,1) returns, unconditional sd 2%."""
    rng = np.random.default_rng(seed)
    z = rng.standard_normal(n)
    omega = 4e-4 * (1 - a - b)
    r = np.empty(n)
    h = 4e-4
    for t in range(n):
        r[t] = np.sqrt(h) * z[t]
        h = omega + a * r[t] ** 2 + b * h
    return Series(100 * np.cumprod(1 + r))


def _oracle_size(logw, ws=WINDOW_SIZE):
    """Kats `get_level_shift_features`, transcribed verbatim from issue
    #163's text with a plain Python loop (not the module's cumsum
    vectorisation, and not its ratio-to-first-bar reformulation): a sliding
    `ws`-bar mean, the absolute diffs between consecutive means, and the
    max of those diffs."""
    means = np.array([logw[k:k + ws].mean() for k in range(len(logw) - ws + 1)])
    d = np.abs(np.diff(means))
    return d.max()


def _oracle(close, length):
    c = close.to_numpy(dtype=float)
    logc = np.log(c)
    out = np.full(c.size, np.nan)
    for t in range(length - 1, c.size):
        out[t] = _oracle_size(logc[t - length + 1:t + 1])
    return out


# ------------------------------------------------------------ correctness


@pytest.mark.parametrize("length", [MIN_LENGTH, 100])
def test_matches_kats_max_on_the_log_close_window(length):
    close = _garch(500, seed=1)
    out = level_shift_size(close, length=length).to_numpy()
    ref = _oracle(close, length)
    assert np.isnan(out[:length - 1]).all()
    np.testing.assert_allclose(out[length - 1:], ref[length - 1:], rtol=1e-9, atol=0)


def test_closed_form_single_level_shift():
    """A persistent step at bar 50 inside a 100-bar window: the WINDOW_SIZE
    (20) sliding mean ramps linearly from 0 to V over the 20 bars as the
    step enters it, so each of the 20 tied diffs is exactly V/20, and that
    is also the max over all 80 diffs (81 means over 100 bars, ws=20) since
    every other diff is 0. With V = 0.05 (the step's log size),
    LEVELSHIFTSIZE_100 = 0.05 / 20 exactly."""
    step_at = 50
    v = 0.05
    close = Series(np.where(np.arange(100) < step_at, 1.0, np.exp(v)))
    out = level_shift_size(close, length=100)
    assert out.iloc[:99].isna().all()
    assert out.iloc[99] == pytest.approx(v / WINDOW_SIZE, rel=1e-9)


# -------------------------------------------------------------- causality


MUTANT = ("lo = length - 1 + start", "lo = length - 2 + start")


def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_level_shift_size_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


def _step_series(n=600, seed=3, shift_at=400, factor=1.5):
    """Tiny iid noise with one deliberate persistent level shift at
    `shift_at`."""
    rng = np.random.default_rng(seed)
    base = 100 * np.cumprod(1 + rng.normal(0, 0.002, n))
    close = Series(base)
    shifted = close.copy()
    shifted.iloc[shift_at:] = shifted.iloc[shift_at:] * factor
    return close, shifted


@pytest.mark.parametrize("shift_at", [105, 150, 300, 450, 590])
def test_real_module_never_reads_the_future(shift_at):
    """Bars before `shift_at` are bit-identical whether or not the shift
    ever happens -- the real module's window for bar T < shift_at never
    reads a close at or after `shift_at`."""
    close, shifted = _step_series(shift_at=shift_at)
    a = level_shift_size(close).iloc[:shift_at]
    b = level_shift_size(shifted).iloc[:shift_at]
    pd.testing.assert_series_equal(a, b, check_exact=True)


@pytest.mark.parametrize("shift_at", [105, 150, 300, 450, 590])
def test_mutant_is_caught(shift_at):
    mod = _load_mutant(*MUTANT)
    close, shifted = _step_series(shift_at=shift_at)
    assert not mod.level_shift_size(close).equals(level_shift_size(close))  # live
    # the real module: nothing changes before the shift
    real_a = level_shift_size(close).iloc[:shift_at]
    real_b = level_shift_size(shifted).iloc[:shift_at]
    pd.testing.assert_series_equal(real_a, real_b, check_exact=True)
    # the mutant: the bar just before the shift already reads it (one bar early)
    mut_a = mod.level_shift_size(close)
    mut_b = mod.level_shift_size(shifted)
    assert mut_a.iloc[shift_at - 1] != mut_b.iloc[shift_at - 1]


def test_a_bad_tick_moves_exactly_its_windows():
    """A bad close at bar 300 (window width 100) nulls exactly bars
    300..399 -- the bars whose window holds it -- and nothing else."""
    close = _garch(seed=4)
    base = level_shift_size(close)
    bad = close.copy()
    bad.iloc[300] = np.nan
    out = level_shift_size(bad)
    moved = np.flatnonzero(~((out == base) | (out.isna() & base.isna())).to_numpy())
    assert moved.tolist() == list(range(300, 400))


# ------------------------------------------------------------ scale-free


@pytest.mark.parametrize("k", [8.0, 64.0])
def test_price_scale_is_bit_identical(k):
    close = _garch(seed=4)
    base, scaled = level_shift_size(close), level_shift_size(close * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_price_scale_within_tolerance(k):
    close = _garch(seed=4)
    base, scaled = level_shift_size(close), level_shift_size(close * k)
    assert (base.isna() == scaled.isna()).all()
    assert (base - scaled).abs().max() < 1e-9


def test_fires_and_is_not_constant():
    out = level_shift_size(_garch(seed=4))
    assert out.notna().sum() == 501  # 600 bars, 99 warm-up (length - 1)
    assert out.dropna().nunique() > 1
    assert (out.dropna() >= 0.0).all()


# ------------------------------------------------------------- edge cases


def test_flat_prices_read_zero_not_nan():
    """A flat window's diffs are all exactly 0: max(0) = 0.0, a real
    answer, not a guard case."""
    out = level_shift_size(Series([10.0] * 150))
    assert out.iloc[99:].notna().all()
    assert (out.iloc[99:] == 0.0).all()


def test_one_ulp_jitter_stays_tiny():
    """A flat 10.0 whose closes flip between 10.0 and the next float up:
    the diffs are all at the ~1e-16 scale, so the max stays at that scale
    rather than reading as a genuine level shift."""
    rng = np.random.default_rng(0)
    c = np.full(150, 10.0)
    c[rng.random(150) < 0.5] = np.nextafter(10.0, 20.0)
    out = level_shift_size(Series(c))
    assert out.iloc[99:].notna().all()
    assert (out.iloc[99:] < 1e-10).all()


@pytest.mark.parametrize("bad", [np.nan, 0.0, -1.0])
def test_a_bad_close_blanks_its_windows(bad):
    close = _garch(300, seed=1)
    base = level_shift_size(close)
    c2 = close.copy()
    c2.iloc[150] = bad
    out = level_shift_size(c2)
    assert out.iloc[150:250].isna().all()  # bars whose window holds bar 150
    pd.testing.assert_series_equal(out.drop(range(150, 250)), base.drop(range(150, 250)))


@pytest.mark.parametrize("bad", [np.nan, 0.0, -1.0])
def test_a_bad_close_blanks_the_same_windows_under_a_price_rescale(bad):
    """The NaN span a bad close blanks does not move when every close is
    also rescaled x8 -- the mask is about which closes are bad, not about
    the price level, and the fired bars stay bit-identical (Gate D)."""
    close = _garch(300, seed=1)
    c2 = close.copy()
    c2.iloc[150] = bad
    base = level_shift_size(c2)
    scaled = level_shift_size(c2 * 8.0)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] == scaled[m]).all()
    assert scaled.iloc[150:250].isna().all()


def test_short_input_and_length_floor():
    close = _garch(150, seed=1)
    assert level_shift_size(close.iloc[:MIN_LENGTH - 1]) is None
    # below WINDOW_SIZE + 1 there is no diff to take a max over: falls back
    # to the default, the repo's convention (kpss, arch_lm, lumpiness, stability)
    assert level_shift_size(close, length=MIN_LENGTH - 1).name == "LEVELSHIFTSIZE_100"
    assert level_shift_size(close, length=10).name == "LEVELSHIFTSIZE_100"
    assert level_shift_size(close, length=MIN_LENGTH).notna().sum() == 150 - MIN_LENGTH + 1


def test_chunk_boundaries_do_not_change_values(monkeypatch):
    close = _garch(seed=4)
    base = level_shift_size(close)
    monkeypatch.setattr(_REAL, "CHUNK_CELLS", 7 * 100)
    pd.testing.assert_series_equal(level_shift_size(close), base, check_exact=True)


# ---------------------------------------------------------------- wiring


def test_name_registration_and_accessor():
    close = _garch(200, seed=1)
    df = pd.DataFrame({"open": close, "high": close, "low": close, "close": close, "volume": 1.0})
    assert "level_shift_size" in ta.Category["statistics"]
    out = df.ta.level_shift_size()
    assert out.name == "LEVELSHIFTSIZE_100"
    pd.testing.assert_series_equal(out, level_shift_size(close))
    assert df.ta.level_shift_size(length=50).name == "LEVELSHIFTSIZE_50"
