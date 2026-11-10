# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.statistics.lumpiness` -- Kats tsfeatures'
`get_lumpiness` (the variance of tile variances) on the z-scored one-bar
returns of a rolling window. Measurements are in docs/LumpinessMeasured.md.

What these pin, in order of how much it would hurt to lose:

* CORRECTNESS against the source: Kats' two lines, transcribed verbatim
  (`np.array_split(x, len(x) // 20 + 1)`, `np.var`), applied to the
  z-scored window at every bar of a GARCH frame, length 20 and 100, to
  1e-12 relative (measured: bit-identical). The tiling is Kats' own -- 6
  tiles of 17/17/17/17/16/16 for 100 returns, not 5 of 20 -- pinned
  separately. And a closed form: 10 returns of +-1% then 10 of +-3%
  z-score to tile variances 0.2 and 1.8, so LUMPINESS_20 = 0.64.
* SEMANTICS: over 10 paths, GARCH(1,1) frames read higher than iid ones,
  rising with the ARCH coefficient -- and iid fat-tailed returns read
  about as high as strong clustering. Lumpiness does not tell the two
  apart.
* The rounding guard: a steady drift of any size (1e-2 down to 1e-10 a
  bar) and a flat price with one-ulp jitter are NaN, not values made of
  floating-point noise; a real tick-rounded series is not blanked by it.
  The semantics medians are pinned within 5% only (RNG-stream dependent);
  the orderings carry the meaning.
* CAUSALITY by future-perturbation over 16 offsets, and a mutant (the write
  index moved one bar earlier) proved live and caught at every offset. A
  bad tick moves exactly the bars whose window holds one of its returns.
* SCALE-FREE: x8/x64 bit-identical, x10/x3.7 within 1e-9, and the column
  fires and is not constant.
* Edge cases (flat, bad and extreme closes, short input, length floor,
  chunk boundaries) and wiring (`Category`, the accessor,
  `LUMPINESS_100`).
"""
import importlib
import types

import numpy as np
import pandas as pd
import pytest
from pandas import Series

from .context import pandas_ta as ta

_REAL = importlib.import_module("pandas_ta.statistics.lumpiness")
lumpiness = _REAL.lumpiness


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


def _iid(n=600, seed=0, dist="normal"):
    rng = np.random.default_rng(seed)
    if dist == "normal":
        r = rng.normal(0.0, 0.02, n)
    else:  # Student t, 3 df, scaled to sd 2%
        r = 0.02 * rng.standard_t(3, n) / np.sqrt(3)
    return Series(100 * np.cumprod(1 + r))


def _kats(x, window_size=20):
    """kats/tsfeatures/tsfeatures.py L672-673 (a6b7e88), verbatim."""
    v = [np.var(x_w) for x_w in np.array_split(x, len(x) // window_size + 1)]
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
    out = lumpiness(close, length=length).to_numpy()
    ref = _oracle(close, length)
    assert np.isnan(out[:length]).all()
    np.testing.assert_allclose(out[length:], ref[length:], rtol=1e-12, atol=0)


def test_tiles_are_kats_array_split():
    sizes = lambda n: [b - a for a, b in _REAL._tiles(n)]  # noqa: E731
    assert sizes(100) == [17, 17, 17, 17, 16, 16]
    assert sizes(20) == [10, 10]
    assert sizes(252) == [20] * 5 + [19] * 8


def test_closed_form():
    """10 returns of +-1% then 10 of +-3%: mean 0, population variance
    (1 + 9) / 2 = 5 (in 1e-4 units), so z-scored tile variances are 1/5 and
    9/5, each tile mean 0. Their population variance is 0.8^2 = 0.64."""
    r = np.r_[0.01 * np.tile([1.0, -1.0], 5), 0.03 * np.tile([1.0, -1.0], 5)]
    close = Series(100 * np.cumprod(np.r_[1.0, 1 + r]))
    out = lumpiness(close, length=20)
    assert out.iloc[:20].isna().all()
    assert out.iloc[20] == pytest.approx(0.64, rel=1e-12)


# --------------------------------------------------------------- semantics


def _pooled(make, k=10, n=600):
    return np.concatenate([lumpiness(make(n, 500 + i)).dropna().to_numpy() for i in range(k)])


# Medians measured with numpy 2.5.4's default_rng. They depend on the RNG
# stream, which NEP 19 does not freeze across numpy releases, so they are
# pinned only within 5%; the orderings carry the meaning.
MEASURED_MEDS = (0.0822, 0.1810, 0.3024)
MEASURED_T3 = 0.2827


def test_clustered_volatility_reads_higher():
    """Medians over 10 paths x 500 bars (measured): iid normal 0.0822,
    GARCH(0.10, 0.85) 0.1810, GARCH(0.20, 0.75) 0.3024 -- ordered."""
    meds = tuple(np.median(_pooled(mk)) for mk in (
        lambda n, s: _iid(n, s),
        lambda n, s: _garch(n, s, 0.10, 0.85),
        lambda n, s: _garch(n, s, 0.20, 0.75)))
    assert meds[0] < meds[1] < meds[2]
    assert meds == pytest.approx(MEASURED_MEDS, rel=0.05)


def test_fat_tails_read_like_clustering():
    """iid Student-t(3) returns, no clustering at all, read a median of
    0.2827 -- far above iid normal and near GARCH(0.20, 0.75). One huge
    squared return makes its tile's variance dominate whatever the
    dependence. A high reading is not evidence of volatility clustering."""
    t3 = np.median(_pooled(lambda n, s: _iid(n, s, "t3")))
    normal = np.median(_pooled(lambda n, s: _iid(n, s)))
    assert t3 > 2 * normal
    assert t3 == pytest.approx(MEASURED_T3, rel=0.05)


@pytest.mark.parametrize("g", [1e-2, 1e-4, 1e-7, 1e-8, 1e-10])
def test_steady_drift_is_nan_not_rounding_noise(g):
    """100 * (1 + g)^t: the returns differ only by the rounding of
    c / c1 - 1, which is absolute (~1e-16) whatever g is. Unguarded, the
    z-score read that noise as medians of 0.156 (g = 1e-2) up to 4.34
    (g = 1e-10). A guard relative to the size of the returns (the first
    version of this module) let g <= 1e-7 through."""
    assert lumpiness(Series(100 * (1 + g) ** np.arange(300.0))).isna().all()


def test_one_ulp_jitter_is_nan():
    """A flat 10.0 whose closes flip between 10.0 and the next float up:
    unguarded it read a median of 0.036."""
    rng = np.random.default_rng(0)
    c = np.full(300, 10.0)
    c[rng.random(300) < 0.5] = np.nextafter(10.0, 20.0)
    assert lumpiness(Series(c)).isna().all()


def test_the_guard_keeps_real_tick_variation():
    """10% a bar on a 0.01 tick: the rounding to ticks is real variation
    (sd / rms 4.55e-4 in the first window), so those bars fire."""
    p = [10.0]
    for _ in range(149):
        p.append(round(p[-1] * 1.1, 2))
    assert lumpiness(Series(p)).iloc[100:].notna().all()


# -------------------------------------------------------------- causality


MUTANT = ("lo = length + start", "lo = length - 1 + start")
OFFSETS = range(130, 600, 30)  # 16 offsets


def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_lumpiness_mutant")
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
    assert _leaks(lumpiness) == 0


def test_mutant_is_caught():
    mod = _load_mutant(*MUTANT)
    close = _garch(seed=11)
    assert not mod.lumpiness(close).equals(lumpiness(close))  # live
    assert _leaks(mod.lumpiness) == len(OFFSETS)


def test_a_bad_tick_moves_exactly_its_windows():
    """close x1000 at bar 300 changes returns 300 and 301; the bars whose
    100-return window holds either are 300..400."""
    close = _garch(seed=4)
    base = lumpiness(close)
    bad = close.copy()
    bad.iloc[300] *= 1e3
    out = lumpiness(bad)
    moved = np.flatnonzero(~((out == base) | (out.isna() & base.isna())).to_numpy())
    assert moved.tolist() == list(range(300, 401))


# ------------------------------------------------------------ scale-free


@pytest.mark.parametrize("k", [8.0, 64.0])
def test_price_scale_is_bit_identical(k):
    close = _garch(seed=4)
    base, scaled = lumpiness(close), lumpiness(close * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_price_scale_within_tolerance(k):
    close = _garch(seed=4)
    base, scaled = lumpiness(close), lumpiness(close * k)
    assert (base.isna() == scaled.isna()).all()
    assert (base - scaled).abs().max() < 1e-9


def test_fires_and_is_not_constant():
    out = lumpiness(_garch(seed=4))
    assert out.notna().sum() == 500  # 600 bars, 100 warm-up
    assert out.dropna().nunique() == 500


# ------------------------------------------------------------- edge cases


def test_flat_prices_are_nan():
    assert lumpiness(Series([10.0] * 150)).isna().all()


@pytest.mark.parametrize("bad", [np.nan, 0.0, -1.0])
def test_a_bad_close_blanks_its_windows(bad):
    close = _garch(300, seed=1)
    base = lumpiness(close)
    c2 = close.copy()
    c2.iloc[150] = bad
    out = lumpiness(c2)
    assert out.iloc[150:251].isna().all()  # returns 150 and 151 are NaN
    pd.testing.assert_series_equal(out.drop(range(150, 251)), base.drop(range(150, 251)))


@pytest.mark.parametrize("extreme, blank", [(1e-300, range(151, 251)), (1e160, range(150, 250))])
def test_an_extreme_close_blanks_its_windows(extreme, blank):
    """A return whose square overflows is treated as missing: its 100
    windows are NaN, every bar outside 150..250 is unchanged."""
    close = _garch(300, seed=1)
    base = lumpiness(close)
    c2 = close.copy()
    c2.iloc[150] = extreme
    out = lumpiness(c2)
    assert out.iloc[list(blank)].isna().all()
    assert out.isna().sum() == base.isna().sum() + 100
    pd.testing.assert_series_equal(out.drop(range(150, 251)), base.drop(range(150, 251)))


def test_short_input_and_length_floor():
    close = _garch(150, seed=1)
    assert lumpiness(close.iloc[:100]) is None  # 100 returns need 101 closes
    # below 20 there is one tile (constant 0): falls back to the default,
    # the repo's convention (kpss, arch_lm), disclosed in the docstring
    assert lumpiness(close, length=19).name == "LUMPINESS_100"
    assert lumpiness(close, length=10).name == "LUMPINESS_100"
    assert lumpiness(close, length=20).notna().sum() == 130


def test_chunk_boundaries_do_not_change_values(monkeypatch):
    close = _garch(seed=4)
    base = lumpiness(close)
    monkeypatch.setattr(_REAL, "CHUNK_CELLS", 7 * 100)
    pd.testing.assert_series_equal(lumpiness(close), base, check_exact=True)


# ---------------------------------------------------------------- wiring


def test_name_registration_and_accessor():
    close = _garch(200, seed=1)
    df = pd.DataFrame({"open": close, "high": close, "low": close, "close": close, "volume": 1.0})
    assert "lumpiness" in ta.Category["statistics"]
    out = df.ta.lumpiness()
    assert out.name == "LUMPINESS_100"
    pd.testing.assert_series_equal(out, lumpiness(close))
    assert df.ta.lumpiness(length=50).name == "LUMPINESS_50"
