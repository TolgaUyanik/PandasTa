# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.statistics.stability` -- Kats tsfeatures'
`get_stability` (the variance of tile means) on the z-scored one-bar
returns of a rolling window. Measurements are in docs/StabilityMeasured.md.

What these pin, in order of how much it would hurt to lose:

* CORRECTNESS against the source: Kats' two lines, transcribed verbatim
  (`np.array_split(x, len(x) // 20 + 1)`, `np.mean` per tile then `np.var`
  across tiles), applied to the z-scored window at every bar of a GARCH
  frame, length 20 and 100, to 1e-12 relative (measured: bit-identical).
  The tiling is Kats' own -- 6 tiles of 17/17/17/17/16/16 for 100 returns,
  not 5 of 20, identical to `lumpiness`'s tiling -- pinned separately. And a
  closed form: 10 returns of +1% then 10 of -1% z-score to tile means +1
  and -1, so STABILITY_20 = 1.0 exactly.
* SEMANTICS: a return path whose mean steps between +drift and -drift every
  `TILE` (20) bars reads a higher median than an iid path with the same
  unconditional sd -- the whole point of the column (a localised run, not
  overall volatility, raises it).
* The rounding guard: a steady drift of any size (1e-2 down to 1e-10 a bar)
  and a flat price with one-ulp jitter are NaN, not values made of
  floating-point noise; a real tick-rounded series is not blanked by it.
* CAUSALITY by future-perturbation over 16 offsets, and a mutant (the write
  index moved one bar earlier) proved live and caught at every offset. A
  bad tick moves exactly the bars whose window holds one of its returns.
* SCALE-FREE: x8/x64 bit-identical, x10/x3.7 within 1e-9, and the column
  fires and is not constant.
* Edge cases (flat, bad and extreme closes, short input, length floor,
  chunk boundaries) and wiring (`Category`, the accessor, `STABILITY_100`).
"""
import importlib
import types

import numpy as np
import pandas as pd
import pytest
from pandas import Series

from .context import pandas_ta as ta

_REAL = importlib.import_module("pandas_ta.statistics.stability")
stability = _REAL.stability


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


def _iid(n=600, seed=0):
    rng = np.random.default_rng(seed)
    r = rng.normal(0.0, 0.02, n)
    return Series(100 * np.cumprod(1 + r))


def _block_regime(n=600, seed=0, drift=0.02, block=20):
    """iid normal returns (sd 2%) plus a block-wise mean that flips sign
    every `block` bars -- a localised run inside any window that spans more
    than one block, which is what `stability` is built to flag."""
    rng = np.random.default_rng(seed)
    r = rng.normal(0.0, 0.02, n)
    sign = np.where((np.arange(n) // block) % 2 == 0, 1.0, -1.0)
    r = r + sign * drift
    return Series(100 * np.cumprod(1 + r))


def _kats(x, window_size=20):
    """Kats `get_stability`, transcribed verbatim from issue #158's text."""
    v = [np.mean(x_w) for x_w in np.array_split(x, len(x) // window_size + 1)]
    return np.var(v)


def _oracle(close, length):
    c = close.to_numpy(dtype=float)
    r = c[1:] / c[:-1] - 1
    out = np.full(c.size, np.nan)
    for t in range(length, c.size):
        w = r[t - length:t]
        out[t] = _kats((w - w.mean()) / w.std())
    return out


# ------------------------------------------------------------ correctness


@pytest.mark.parametrize("length", [20, 100])
def test_matches_kats_on_the_z_scored_window(length):
    close = _garch(500, seed=1)
    out = stability(close, length=length).to_numpy()
    ref = _oracle(close, length)
    assert np.isnan(out[:length]).all()
    np.testing.assert_allclose(out[length:], ref[length:], rtol=1e-12, atol=0)


def test_tiles_are_kats_array_split():
    sizes = lambda n: [b - a for a, b in _REAL._tiles(n)]  # noqa: E731
    assert sizes(100) == [17, 17, 17, 17, 16, 16]
    assert sizes(20) == [10, 10]
    assert sizes(252) == [20] * 5 + [19] * 8


def test_closed_form():
    """10 returns of +1% then 10 of -1%: population mean 0, population sd
    1% (equal +-1% split), so z-scored returns are exactly +1 (first tile)
    and -1 (second tile) -- each tile's own mean, since the tiles (10/10)
    align exactly with the two blocks. Population variance of [1, -1] is 1."""
    r = np.r_[np.full(10, 0.01), np.full(10, -0.01)]
    close = Series(100 * np.cumprod(np.r_[1.0, 1 + r]))
    out = stability(close, length=20)
    assert out.iloc[:20].isna().all()
    assert out.iloc[20] == pytest.approx(1.0, rel=1e-12)


# --------------------------------------------------------------- semantics


def _pooled(make, k=10, n=600):
    return np.concatenate([stability(make(n, 500 + i)).dropna().to_numpy() for i in range(k)])


def test_a_block_regime_reads_higher_than_iid():
    """A return path whose mean flips sign every 20 bars (close to the
    tile width) reads a higher median STABILITY than an iid path of the
    same unconditional sd -- a localised directional run inside the window
    is exactly what this column is built to flag."""
    iid_med = np.median(_pooled(lambda n, s: _iid(n, s)))
    regime_med = np.median(_pooled(lambda n, s: _block_regime(n, s)))
    assert regime_med > 3 * iid_med


@pytest.mark.parametrize("g", [1e-2, 1e-4, 1e-7, 1e-8, 1e-10])
def test_steady_drift_is_nan_not_rounding_noise(g):
    """100 * (1 + g)^t: the returns differ only by the rounding of
    c / c1 - 1, which is absolute (~1e-16) whatever g is. Unguarded, the
    z-score would read that noise as a large, spurious STABILITY (a smooth
    drift z-scores to exactly the kind of one-directional run this column
    is meant to flag in real data)."""
    assert stability(Series(100 * (1 + g) ** np.arange(300.0))).isna().all()


def test_one_ulp_jitter_is_nan():
    """A flat 10.0 whose closes flip between 10.0 and the next float up."""
    rng = np.random.default_rng(0)
    c = np.full(300, 10.0)
    c[rng.random(300) < 0.5] = np.nextafter(10.0, 20.0)
    assert stability(Series(c)).isna().all()


def test_the_guard_keeps_real_tick_variation():
    """10% a bar on a 0.01 tick: the rounding to ticks is real variation
    (sd / rms 4.55e-4 in the first window, same frame `lumpiness` uses for
    this check), so those bars fire."""
    p = [10.0]
    for _ in range(149):
        p.append(round(p[-1] * 1.1, 2))
    assert stability(Series(p)).iloc[100:].notna().all()


# -------------------------------------------------------------- causality


MUTANT = ("lo = length + start", "lo = length - 1 + start")
OFFSETS = range(130, 600, 30)  # 16 offsets


def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_stability_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


def _leaks(fn):
    close = _garch(seed=11)
    other = _garch(seed=99)
    base = fn(close)
    hits = 0
    for j in OFFSETS:
        p = close.copy()
        p.iloc[j:] = other.iloc[j:].to_numpy() * (close.iloc[j - 1] / other.iloc[j - 1])
        out = fn(p)
        a, b = base.iloc[:j], out.iloc[:j]
        if not (a.isna() == b.isna()).all() or (a[a.notna()] != b[a.notna()]).any():
            hits += 1
    return hits


def test_real_module_never_reads_the_future():
    assert _leaks(stability) == 0


def test_mutant_is_caught():
    mod = _load_mutant(*MUTANT)
    close = _garch(seed=11)
    assert not mod.stability(close).equals(stability(close))  # live
    assert _leaks(mod.stability) == len(OFFSETS)


def test_a_bad_tick_moves_exactly_its_windows():
    """close x1000 at bar 300 changes returns 300 and 301; the bars whose
    100-return window holds either are 300..400."""
    close = _garch(seed=4)
    base = stability(close)
    bad = close.copy()
    bad.iloc[300] *= 1e3
    out = stability(bad)
    moved = np.flatnonzero(~((out == base) | (out.isna() & base.isna())).to_numpy())
    assert moved.tolist() == list(range(300, 401))


# ------------------------------------------------------------ scale-free


@pytest.mark.parametrize("k", [8.0, 64.0])
def test_price_scale_is_bit_identical(k):
    close = _garch(seed=4)
    base, scaled = stability(close), stability(close * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_price_scale_within_tolerance(k):
    close = _garch(seed=4)
    base, scaled = stability(close), stability(close * k)
    assert (base.isna() == scaled.isna()).all()
    assert (base - scaled).abs().max() < 1e-9


def test_fires_and_is_not_constant():
    out = stability(_garch(seed=4))
    assert out.notna().sum() == 500  # 600 bars, 100 warm-up
    assert out.dropna().nunique() == 500


# ------------------------------------------------------------- edge cases


def test_flat_prices_are_nan():
    assert stability(Series([10.0] * 150)).isna().all()


@pytest.mark.parametrize("bad", [np.nan, 0.0, -1.0])
def test_a_bad_close_blanks_its_windows(bad):
    close = _garch(300, seed=1)
    base = stability(close)
    c2 = close.copy()
    c2.iloc[150] = bad
    out = stability(c2)
    assert out.iloc[150:251].isna().all()  # returns 150 and 151 are NaN
    pd.testing.assert_series_equal(out.drop(range(150, 251)), base.drop(range(150, 251)))


@pytest.mark.parametrize("extreme, blank", [(1e-300, range(151, 251)), (1e160, range(150, 250))])
def test_an_extreme_close_blanks_its_windows(extreme, blank):
    """A return whose square overflows is treated as missing: its 100
    windows are NaN, every bar outside 150..250 is unchanged."""
    close = _garch(300, seed=1)
    base = stability(close)
    c2 = close.copy()
    c2.iloc[150] = extreme
    out = stability(c2)
    assert out.iloc[list(blank)].isna().all()
    assert out.isna().sum() == base.isna().sum() + 100
    pd.testing.assert_series_equal(out.drop(range(150, 251)), base.drop(range(150, 251)))


def test_short_input_and_length_floor():
    close = _garch(150, seed=1)
    assert stability(close.iloc[:100]) is None  # 100 returns need 101 closes
    # below 20 there is one tile (constant 0): falls back to the default,
    # the repo's convention (kpss, arch_lm, lumpiness), disclosed in the docstring
    assert stability(close, length=19).name == "STABILITY_100"
    assert stability(close, length=10).name == "STABILITY_100"
    assert stability(close, length=20).notna().sum() == 130


def test_chunk_boundaries_do_not_change_values(monkeypatch):
    close = _garch(seed=4)
    base = stability(close)
    monkeypatch.setattr(_REAL, "CHUNK_CELLS", 7 * 100)
    pd.testing.assert_series_equal(stability(close), base, check_exact=True)


# ---------------------------------------------------------------- wiring


def test_name_registration_and_accessor():
    close = _garch(200, seed=1)
    df = pd.DataFrame({"open": close, "high": close, "low": close, "close": close, "volume": 1.0})
    assert "stability" in ta.Category["statistics"]
    out = df.ta.stability()
    assert out.name == "STABILITY_100"
    pd.testing.assert_series_equal(out, stability(close))
    assert df.ta.stability(length=50).name == "STABILITY_50"
