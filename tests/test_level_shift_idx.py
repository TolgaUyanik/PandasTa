# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.statistics.level_shift_idx` -- Kats tsfeatures'
`get_level_shift_features` `argmax` (the position of the largest jump
between consecutive sliding-window means) on a rolling window of log close.
Measurements are in docs/LevelShiftIdxMeasured.md.

What these pin, in order of how much it would hurt to lose:

* CORRECTNESS against the source: Kats' two-line formula (issue #159's
  text), transcribed independently (a plain Python loop, not the module's
  cumsum vectorisation) and matched at every bar of a GARCH frame, and a
  closed form: a single persistent level shift inside the window produces a
  tied plateau of WINDOW_SIZE (20) equal diffs, and `argmax`'s first-tie
  convention picks the plateau's first bar deterministically.
* CAUSALITY: bars before a deliberate single level shift are bit-identical
  whether or not the shift ever happens, at five shift positions (near the
  frame's start and end, and mid-frame), and a mutant (the write index moved
  one bar earlier) proved live and caught at every position -- a generic
  "swap the tail for an unrelated path" probe
  has low power on an argmax feature, since an older, larger shift
  elsewhere in the window can keep winning regardless of the tail (see
  `_step_series`). A bad close moves exactly the bars whose window holds it.
* SCALE-FREE: bar-for-bar invariant under a price rescale, because a diff
  between two sliding-window means of `log(close)` cancels any additive
  shift exactly -- x8/x64 bit-identical, x10/x3.7 within tolerance -- and
  the column fires and is not constant.
* Edge cases (flat price reads 0.0, not NaN; bad/short input; the length
  floor; chunk boundaries) and wiring (`Category`, the accessor,
  `LEVELSHIFTIDX_100`).
"""
import importlib
import types

import numpy as np
import pandas as pd
import pytest
from pandas import Series

from .context import pandas_ta as ta

_REAL = importlib.import_module("pandas_ta.statistics.level_shift_idx")
level_shift_idx = _REAL.level_shift_idx
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


def _oracle_idx(logw, ws=WINDOW_SIZE, decimals=_REAL.ROUND_DECIMALS):
    """Kats `get_level_shift_features`, transcribed verbatim from issue
    #159's text with a plain Python loop (not the module's cumsum
    vectorisation): a sliding `ws`-bar mean, the absolute diffs between
    consecutive means, and the argmax of those diffs."""
    means = np.array([logw[k:k + ws].mean() for k in range(len(logw) - ws + 1)])
    d = np.round(np.abs(np.diff(means)), decimals)
    return np.argmax(d) / (len(d) - 1)


def _oracle(close, length):
    c = close.to_numpy(dtype=float)
    logc = np.log(c)
    out = np.full(c.size, np.nan)
    for t in range(length - 1, c.size):
        out[t] = _oracle_idx(logc[t - length + 1:t + 1])
    return out


# ------------------------------------------------------------ correctness


@pytest.mark.parametrize("length", [MIN_LENGTH, 100])
def test_matches_kats_argmax_on_the_log_close_window(length):
    close = _garch(500, seed=1)
    out = level_shift_idx(close, length=length).to_numpy()
    ref = _oracle(close, length)
    assert np.isnan(out[:length - 1]).all()
    np.testing.assert_allclose(out[length - 1:], ref[length - 1:], rtol=1e-9, atol=0)


def test_closed_form_single_level_shift():
    """A persistent step at bar 50 inside a 100-bar window: the WINDOW_SIZE
    (20) sliding mean ramps linearly as the step enters it, producing a tied
    plateau of exactly 20 equal diffs (V/20 each) from j=30 to j=49 and 0
    everywhere else, out of 80 diffs (81 means over 100 bars, ws=20).
    `np.argmax`'s first-tie convention picks j=30, so
    LEVELSHIFTIDX_100 = 30 / (80 - 1) = 30/79 exactly."""
    step_at = 50
    close = Series(np.where(np.arange(100) < step_at, 1.0, np.exp(0.05)))
    out = level_shift_idx(close, length=100)
    assert out.iloc[:99].isna().all()
    assert out.iloc[99] == pytest.approx(30 / 79, rel=1e-9)


def test_tiles_denominator_matches_window_size():
    """For length L, there are L - WINDOW_SIZE + 1 means and L - WINDOW_SIZE
    diffs, so the idx scale's denominator is L - WINDOW_SIZE - 1."""
    for length in (MIN_LENGTH, 50, 100, 252):
        close = _garch(length + 5, seed=2)
        out = level_shift_idx(close, length=length)
        # every fired value is k / (L - WINDOW_SIZE - 1) for some integer k
        denom = length - WINDOW_SIZE - 1
        vals = out.dropna().to_numpy()
        ks = np.round(vals * denom)
        np.testing.assert_allclose(vals, ks / denom, atol=1e-12)


# -------------------------------------------------------------- causality


MUTANT = ("lo = length - 1 + start", "lo = length - 2 + start")


def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_level_shift_idx_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


def _step_series(n=600, seed=3, shift_at=400, factor=1.5):
    """Tiny iid noise with one deliberate persistent level shift at
    `shift_at`. An argmax-of-diffs feature can keep reporting the SAME
    (older) window position after the window's tail is perturbed, if an
    older feature elsewhere in the window still dominates -- so a generic
    "swap the tail for an unrelated path" leak probe has low power here.
    A single, isolated, much-larger-than-noise shift removes that
    confound: whichever side of `shift_at` a window's tail falls on is
    exactly what decides whether the window sees it."""
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
    a = level_shift_idx(close).iloc[:shift_at]
    b = level_shift_idx(shifted).iloc[:shift_at]
    pd.testing.assert_series_equal(a, b, check_exact=True)


@pytest.mark.parametrize("shift_at", [105, 150, 300, 450, 590])
def test_mutant_is_caught(shift_at):
    mod = _load_mutant(*MUTANT)
    close, shifted = _step_series(shift_at=shift_at)
    assert not mod.level_shift_idx(close).equals(level_shift_idx(close))  # live
    # the real module: nothing changes before the shift
    real_a = level_shift_idx(close).iloc[:shift_at]
    real_b = level_shift_idx(shifted).iloc[:shift_at]
    pd.testing.assert_series_equal(real_a, real_b, check_exact=True)
    # the mutant: the bar just before the shift already reads it (one bar early)
    mut_a = mod.level_shift_idx(close)
    mut_b = mod.level_shift_idx(shifted)
    assert mut_a.iloc[shift_at - 1] != mut_b.iloc[shift_at - 1]


def test_a_bad_tick_moves_exactly_its_windows():
    """A bad close at bar 300 (window width 100) nulls exactly bars
    300..399 -- the bars whose window holds it -- and nothing else."""
    close = _garch(seed=4)
    base = level_shift_idx(close)
    bad = close.copy()
    bad.iloc[300] = np.nan
    out = level_shift_idx(bad)
    moved = np.flatnonzero(~((out == base) | (out.isna() & base.isna())).to_numpy())
    assert moved.tolist() == list(range(300, 400))


# ------------------------------------------------------------ scale-free


@pytest.mark.parametrize("k", [8.0, 64.0])
def test_price_scale_is_bit_identical(k):
    close = _garch(seed=4)
    base, scaled = level_shift_idx(close), level_shift_idx(close * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_price_scale_within_tolerance(k):
    close = _garch(seed=4)
    base, scaled = level_shift_idx(close), level_shift_idx(close * k)
    assert (base.isna() == scaled.isna()).all()
    assert (base - scaled).abs().max() < 1e-9


def test_fires_and_is_not_constant():
    out = level_shift_idx(_garch(seed=4))
    assert out.notna().sum() == 501  # 600 bars, 99 warm-up (length - 1)
    assert out.dropna().nunique() > 1


# ------------------------------------------------------------- edge cases


def test_flat_prices_read_zero_not_nan():
    """Unlike `stability`/`lumpiness` (which z-score and so blow a flat
    window's rounding noise up to unit variance), this column never divides
    by a window statistic: a flat window's diffs are all exactly 0, tied,
    and `argmax`'s first-tie convention deterministically reads 0.0 -- a
    real answer, not a guard case."""
    out = level_shift_idx(Series([10.0] * 150))
    assert out.iloc[99:].notna().all()
    assert (out.iloc[99:] == 0.0).all()


def test_one_ulp_jitter_is_robust_not_flipping():
    """A flat 10.0 whose closes flip between 10.0 and the next float up:
    the diffs are all at the ~1e-16 scale, which the 12-decimal rounding
    collapses to an exact tie at 0, so the column still reads 0.0
    deterministically rather than a value made of floating-point noise."""
    rng = np.random.default_rng(0)
    c = np.full(150, 10.0)
    c[rng.random(150) < 0.5] = np.nextafter(10.0, 20.0)
    out = level_shift_idx(Series(c))
    assert out.iloc[99:].notna().all()
    assert (out.iloc[99:] == 0.0).all()


@pytest.mark.parametrize("bad", [np.nan, 0.0, -1.0])
def test_a_bad_close_blanks_its_windows(bad):
    close = _garch(300, seed=1)
    base = level_shift_idx(close)
    c2 = close.copy()
    c2.iloc[150] = bad
    out = level_shift_idx(c2)
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
    base = level_shift_idx(c2)
    scaled = level_shift_idx(c2 * 8.0)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] == scaled[m]).all()
    assert scaled.iloc[150:250].isna().all()


def test_short_input_and_length_floor():
    close = _garch(150, seed=1)
    assert level_shift_idx(close.iloc[:MIN_LENGTH - 1]) is None
    # below WINDOW_SIZE + 2 the idx scale would divide by zero: falls back
    # to the default, the repo's convention (kpss, arch_lm, lumpiness, stability)
    assert level_shift_idx(close, length=MIN_LENGTH - 1).name == "LEVELSHIFTIDX_100"
    assert level_shift_idx(close, length=10).name == "LEVELSHIFTIDX_100"
    assert level_shift_idx(close, length=MIN_LENGTH).notna().sum() == 150 - MIN_LENGTH + 1


def test_chunk_boundaries_do_not_change_values(monkeypatch):
    close = _garch(seed=4)
    base = level_shift_idx(close)
    monkeypatch.setattr(_REAL, "CHUNK_CELLS", 7 * 100)
    pd.testing.assert_series_equal(level_shift_idx(close), base, check_exact=True)


# ---------------------------------------------------------------- wiring


def test_name_registration_and_accessor():
    close = _garch(200, seed=1)
    df = pd.DataFrame({"open": close, "high": close, "low": close, "close": close, "volume": 1.0})
    assert "level_shift_idx" in ta.Category["statistics"]
    out = df.ta.level_shift_idx()
    assert out.name == "LEVELSHIFTIDX_100"
    pd.testing.assert_series_equal(out, level_shift_idx(close))
    assert df.ta.level_shift_idx(length=50).name == "LEVELSHIFTIDX_50"
