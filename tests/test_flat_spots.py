# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.statistics.flat_spots` -- Kats tsfeatures'
`get_flat_spots` (longest run of identical consecutive closes inside any
of 10 equal-size time chunks of a rolling window). Measurements are in
docs/FlatSpotsMeasured.md.

What these pin, in order of how much it would hurt to lose:

* CORRECTNESS against the source: the prototype's own `_flat_spots`
  (`docs/issues/screen/ind_screen_r5.py` L107-116), transcribed verbatim
  as a per-window oracle, compared bit-identically to the module at every
  bar on three synthetic frames (one ticky at lengths 20/30/100, plus a
  continuous and a ticky frame at length 20). A closed form: a window
  with one 10-bar chunk forced flat reads exactly that chunk's size (10),
  every other chunk strictly increasing (run 0).
* CAUSALITY by future-perturbation over 16 offsets, and a mutant (the
  write index moved one bar earlier) proved live and caught at every
  offset. A bad tick moves exactly the bars whose window holds it.
* SCALE-FREE: `==` is a deterministic function of its operands' bits, so
  it is bit-identical under ANY uniform rescale, not only a power of two
  -- measured x8/x64 AND x10/x3.7, plus the column fires and is not
  constant.
* SEMANTICS: a tick-rounded price (many repeated closes) reads a higher
  median FLATSPOTS than a continuously-varying one (almost never repeats).
* Edge cases (non-finite closes, short input, length floor not a
  multiple of 10, chunk boundaries) and wiring (`Category`, the accessor,
  `FLATSPOTS_100`).
"""
import importlib
import types

import numpy as np
import pandas as pd
import pytest
from pandas import Series

from .context import pandas_ta as ta

_REAL = importlib.import_module("pandas_ta.statistics.flat_spots")
flat_spots = _REAL.flat_spots


def _continuous(n=600, seed=0):
    """A random walk of continuous floats: adjacent closes essentially
    never tie exactly."""
    rng = np.random.default_rng(seed)
    r = rng.normal(0.0, 0.02, n)
    return Series(100 * np.cumprod(1 + r))


def _ticky(n=600, seed=0, tick=0.01, level=5.0):
    """A random walk rounded to a coarse tick: many bars print the same
    close as their neighbour."""
    c = _continuous(n, seed).to_numpy()
    c = level + (c - c[0]) * 0.01
    return Series(np.round(c / tick) * tick)


def _kats(x, chunks=10):
    """The prototype's `_flat_spots` (ind_screen_r5.py L107-116),
    transcribed for a single window: split into `chunks` equal chunks
    (dropping any remainder), longest run of identical adjacent values
    per chunk, 1 plus the max over chunks."""
    x = np.asarray(x, dtype=float)
    k = len(x) // chunks
    best = 0
    for c in range(chunks):
        seg = x[c * k:(c + 1) * k]
        run = 0
        for i in range(1, len(seg)):
            run = run + 1 if seg[i] == seg[i - 1] else 0
            best = max(best, run)
    return float(best + 1)


def _oracle(close, length):
    c = close.to_numpy(dtype=float)
    out = np.full(c.size, np.nan)
    for t in range(length - 1, c.size):
        out[t] = _kats(c[t - length + 1:t + 1])
    return out


# ------------------------------------------------------------ correctness


@pytest.mark.parametrize("length", [20, 30, 100])
def test_matches_the_prototype_oracle(length):
    close = _ticky(300, seed=1)
    out = flat_spots(close, length=length).to_numpy()
    ref = _oracle(close, length)
    assert np.isnan(out[:length - 1]).all()
    np.testing.assert_array_equal(out[length - 1:], ref[length - 1:])


@pytest.mark.parametrize("close_fn", [_continuous, _ticky])
def test_matches_the_prototype_oracle_various_frames(close_fn):
    close = close_fn(250, seed=7)
    out = flat_spots(close, length=20).to_numpy()
    ref = _oracle(close, 20)
    np.testing.assert_array_equal(out[19:], ref[19:])


def test_closed_form_one_flat_chunk():
    """100 distinct strictly-increasing closes except chunk 3 (bars 30-39
    of the window, 0-indexed) forced to a single repeated value: that
    chunk's 10 identical bars is the longest run anywhere, so the window
    reads exactly 10 -- the chunk size, the maximum possible at length 100."""
    c = np.arange(100, dtype=float)
    c[30:40] = 5.0
    close = Series(c)
    out = flat_spots(close, length=100)
    assert out.iloc[:99].isna().all()
    assert out.iloc[99] == 10.0


def test_closed_form_no_repeats_reads_one():
    close = Series(np.arange(100, dtype=float))
    out = flat_spots(close, length=100)
    assert out.iloc[99] == 1.0


# --------------------------------------------------------------- semantics


def _pooled(make, k=10, n=600, length=100):
    return np.concatenate([flat_spots(make(n, 500 + i), length=length).dropna().to_numpy()
                            for i in range(k)])


def test_tick_rounded_prices_read_higher_than_continuous():
    """A price series rounded to a coarse tick ties with its neighbour far
    more often than a continuously-varying one, so its FLATSPOTS median is
    higher -- the whole point of the column."""
    cont_med = np.median(_pooled(_continuous))
    tick_med = np.median(_pooled(_ticky))
    assert tick_med > cont_med


# -------------------------------------------------------------- causality


MUTANT = ("lo = length - 1 + start", "lo = length - 2 + start")
OFFSETS = range(130, 600, 30)  # 16 offsets


def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_flat_spots_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


def _arange_close(n=600):
    """Strictly increasing, so the only tie anywhere is the one a
    perturbation deliberately forces -- a single-bar change in a
    run-length statistic like `flat_spots` rarely moves the output
    (most single bars are not part of the longest run), so a leak probe
    needs a perturbation guaranteed to flip the result, not merely a
    changed value."""
    return Series(np.arange(n, dtype=float))


def _leaks(fn, offsets=OFFSETS):
    """At each offset j, force closes j-1 and j to tie (otherwise there
    is none, anywhere in the series) and check that no bar before j
    changed. A window ending at T = j - 1 never reads bar j, so a
    correct module is unaffected; a module that writes a window's result
    one bar too early effectively reads bar j from bar j - 1."""
    close = _arange_close()
    base = fn(close)
    hits = 0
    for j in offsets:
        p = close.copy()
        p.iloc[j] = p.iloc[j - 1]
        out = fn(p)
        a, b = base.iloc[:j], out.iloc[:j]
        if not (a.isna() == b.isna()).all() or (a[a.notna()] != b[a.notna()]).any():
            hits += 1
    return hits


def test_real_module_never_reads_the_future():
    assert _leaks(flat_spots) == 0


def test_mutant_is_caught():
    mod = _load_mutant(*MUTANT)
    close = _arange_close()
    assert not mod.flat_spots(close).equals(flat_spots(close))  # live: shifted warm-up boundary
    assert _leaks(mod.flat_spots) == len(OFFSETS)


def test_a_tie_moves_exactly_its_windows():
    """Forcing closes 299 and 300 to tie (otherwise the series is
    strictly increasing, so this is the only tie anywhere) lifts every
    100-bar window T = 300 .. 398 (T = 399's window starts at bar 300,
    so it no longer holds bar 299) from 1 to 2 -- except the 9 of them
    whose chunk boundary falls exactly between the two bars (relative
    position 399 - T a multiple of 10, i.e. T = 309, 319, .. 389), where
    the tie straddles two chunks and lifts neither."""
    close = _arange_close()
    base = flat_spots(close)
    tied = close.copy()
    tied.iloc[300] = tied.iloc[299]
    out = flat_spots(tied)
    moved = np.flatnonzero(~((out == base) | (out.isna() & base.isna())).to_numpy())
    expected = [t for t in range(300, 399) if t % 10 != 9]
    assert moved.tolist() == expected


# ------------------------------------------------------------ scale-free


@pytest.mark.parametrize("k", [8.0, 64.0])
def test_price_scale_is_bit_identical(k):
    close = _ticky(seed=4)
    base, scaled = flat_spots(close), flat_spots(close * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_price_scale_within_tolerance(k):
    """`==` is a deterministic function of its operands' bits: if two
    closes are bit-identical before a uniform rescale, the rescaled
    closes are bit-identical too, for ANY finite factor -- not only a
    power of two. Measured: exactly 0, stronger than a ratio-based
    column's rounding tolerance."""
    close = _ticky(seed=4)
    base, scaled = flat_spots(close), flat_spots(close * k)
    assert (base.isna() == scaled.isna()).all()
    assert (base - scaled).abs().max() == 0.0


def test_fires_and_is_not_constant():
    out = flat_spots(_ticky(seed=4))
    assert out.notna().sum() == 501  # 600 bars, 99 warm-up (length - 1)
    assert out.dropna().nunique() > 1


# ------------------------------------------------------------- edge cases


@pytest.mark.parametrize("bad", [np.nan, np.inf, -np.inf])
def test_a_non_finite_close_blanks_its_windows(bad):
    close = _ticky(300, seed=1)
    base = flat_spots(close)
    c2 = close.copy()
    c2.iloc[150] = bad
    out = flat_spots(c2)
    assert out.iloc[150:250].isna().all()  # 100-bar windows holding bar 150
    pd.testing.assert_series_equal(out.drop(range(150, 250)), base.drop(range(150, 250)))


def test_zero_and_negative_closes_are_valid():
    """Unlike the return-based kats_* siblings, flat_spots never divides,
    so zero and negative closes are ordinary values, not missing data."""
    c = np.arange(100, dtype=float) - 50.0  # crosses zero and negative
    c[30:40] = 0.0
    out = flat_spots(Series(c), length=100)
    assert out.iloc[99] == 10.0


def test_short_input_and_length_floor():
    close = _ticky(150, seed=1)
    assert flat_spots(close.iloc[:19]) is None  # fewer than the length-100 default needs
    # below 2 * CHUNKS (20) a chunk has no adjacent pair (always reads the
    # constant 1): falls back to the default, the repo's convention
    # (kpss, stability, level_shift_idx), disclosed in the docstring
    assert flat_spots(close, length=19).name == "FLATSPOTS_100"
    assert flat_spots(close, length=10).name == "FLATSPOTS_100"
    assert flat_spots(close, length=20).notna().sum() == 131


def test_length_not_a_multiple_of_ten():
    """length=25: 10 chunks of 2 (20 bars used, the window's newest 5
    bars dropped). Matches the oracle, which uses the same truncation."""
    close = _ticky(200, seed=2)
    out = flat_spots(close, length=25).to_numpy()
    ref = _oracle(close, 25)
    np.testing.assert_array_equal(out[24:], ref[24:])


def test_chunk_boundaries_do_not_change_values(monkeypatch):
    close = _ticky(seed=4)
    base = flat_spots(close)
    monkeypatch.setattr(_REAL, "CHUNK_CELLS", 7 * 100)
    pd.testing.assert_series_equal(flat_spots(close), base, check_exact=True)


# ---------------------------------------------------------------- wiring


def test_name_registration_and_accessor():
    close = _ticky(200, seed=1)
    df = pd.DataFrame({"open": close, "high": close, "low": close, "close": close, "volume": 1.0})
    assert "flat_spots" in ta.Category["statistics"]
    out = df.ta.flat_spots()
    assert out.name == "FLATSPOTS_100"
    pd.testing.assert_series_equal(out, flat_spots(close))
    assert df.ta.flat_spots(length=50).name == "FLATSPOTS_50"
