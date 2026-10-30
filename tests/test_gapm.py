# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.momentum.gapm` -- Gap Momentum: the sum of up gaps
(open - prior close) over the sum of down gaps across `length` bars, smoothed
by an EMA of span `signal`. Sources: Kaufman, TASC Jan 2024 (cited from
recollection, unverified) and r/algotrading 1brndbe (tier 4, untested claims).
Measurements and the open gates are in `docs/GapmMeasured.md`.

What these tests pin, in order of how much it would hurt to lose them:

* CAUSALITY by future-perturbation: rewrite open and close from bar `j`
  onward with another walk, demand bars `[0:j]` bit-identical with matching
  NaN masks, over 31 offsets.  Three look-ahead mutants (`importlib` source
  read, one index shifted forward, `exec`'d in memory): the gap reading
  `close.shift(-1)`, the up-gap sum reading one bar ahead, and the output
  written one bar early (`gapm.shift(-1)`).  Each is
  proved live, then caught at 31 of 31.  The real module leaks at 0.  With
  the random rewrite alone the `window` mutant was caught at only 28 of 31,
  which is why a second, all-up-gap future exists.
* THE ZERO-DENOMINATOR RULE.  A window with no down gap gives NaN, never
  inf, and that NaN reaches the output (the EMA skips it and does not carry
  its last value over it).  The rate depends on how often open == prior
  close.  On the 2,000-bar seed-11 walk with that forced on a fraction
  p of bars: p = 0.5 / 0.7 / 0.8 / 0.9 give 0 / 2 / 50 / 399 of the 1,960
  full windows with no down gap (0 / 0.10% / 2.55% / 20.36%).  p = 0.8 is
  pinned: 50 such windows, 109 NaN in the output (59 warm-up + 50).
* THE TAIL IS LOPSIDED, not pinned as a bound: the ratio is unbounded above
  and floored at 0.  GAPM min / median / max on that walk: 0.447 / 1.042 /
  2.447 at p = 0, 0.176 / 1.254 / 26.385 at p = 0.8, 0.003 / 1.396 / 30.643
  at p = 0.9.  Pinned at p = 0.8 so a change to the tail is seen.
* SCALE-FREE: on the 1,200-bar seed-11 walk, x8 and x64 are bit-identical,
  and x10 and x3.7 are equal within a relative 1.8e-14 (measured max
  1.73e-14 / 1.36e-14, the same on pandas 2.3.3 and 3.0.6), all with
  matching NaN masks.  It is not constant:
  706 bars above 1, 435 below, 59 NaN warm-up.
* CORRECTNESS against an independent loop written from the definition
  (sums, ratio, and the EMA recursion with NaNs skipped and `signal` valid
  ratios before the first value), and a hand-computed sequence.
* EDGES: a NaN input mid-series; `offset`; `fillna`; `fill_method`, where
  an unknown value raises (it used to back-fill: a silent look-ahead).
* Wiring: `Category`, the accessor (parameters forwarded under the right
  names), the column name `GAPM_40_20`.
"""
import importlib
import types

import numpy as np
import pandas as pd
import pytest
from pandas import DataFrame, Series

from .context import pandas_ta as ta
from pandas_ta.momentum.gapm import gapm


TICK = 0.01


def _walk(n=1200, seed=11, p_flat=0.0, level=50.0):
    """Tick-rounded walk whose open is the prior close moved overnight and
    whose close is the open moved intraday; `p_flat` of the overnight moves
    are forced to 0 (open == prior close)."""
    rng = np.random.default_rng(seed)
    on, intra = rng.normal(0, 0.004, n), rng.normal(0, 0.011, n)
    on[rng.random(n) < p_flat] = 0.0
    lc = np.log(level) + np.cumsum(on + intra)
    c = np.round(np.exp(lc) / TICK) * TICK
    prev = np.r_[c[0], c[:-1]]
    o = np.round(prev * np.exp(on) / TICK) * TICK
    return Series(o), Series(c)


def _reference(o, c, length=40, signal=20):
    o, c = np.asarray(o, float), np.asarray(c, float)
    n = len(o)
    up, dn = np.full(n, np.nan), np.full(n, np.nan)
    for t in range(1, n):
        g = o[t] - c[t - 1]
        up[t], dn[t] = max(g, 0.0), max(-g, 0.0)
    ratio = np.full(n, np.nan)
    for t in range(length, n):
        u, d = up[t - length + 1:t + 1], dn[t - length + 1:t + 1]
        if np.isnan(u).any() or np.isnan(d).any():
            continue
        if d.sum() > 0:
            ratio[t] = u.sum() / d.sum()
    a = 2.0 / (signal + 1)
    out = np.full(n, np.nan)
    y, seen = None, 0
    for t in range(n):
        if np.isnan(ratio[t]):
            continue
        y = ratio[t] if y is None else (1 - a) * y + a * ratio[t]
        seen += 1
        if seen >= signal:
            out[t] = y
    return out


# ------------------------------------------------------------ correctness


def test_hand_computed():
    close = Series([10.0] * 6)
    open_ = Series([10.0, 11.0, 9.0, 10.5, 8.0, 12.0])
    # gaps (bar 1..5): +1, -1, +0.5, -2, +2
    out = gapm(open_, close, length=3, signal=1)  # span 1: GAPM == ratio
    assert out.name == "GAPM_3_1"
    assert out.iloc[:3].isna().all()
    assert out.iloc[3:].tolist() == pytest.approx([1.5 / 1.0, 0.5 / 3.0, 2.5 / 2.0])


def test_matches_an_independent_loop():
    for p in (0.0, 0.8):
        o, c = _walk(n=2000, p_flat=p)
        out = gapm(o, c)
        ref = _reference(o, c)
        assert (np.isnan(ref) == out.isna().values).all()
        np.testing.assert_allclose(out.values[~np.isnan(ref)], ref[~np.isnan(ref)], rtol=1e-12)


def test_no_down_gap_is_nan_never_inf():
    close = Series([10.0] * 8)
    open_ = Series([10.0, 9.0, 10.0, 10.5, 10.0, 11.0, 10.0, 9.5])
    out = gapm(open_, close, length=3, signal=1)
    # gaps (bar 1..7): -1, 0, +0.5, 0, +1, 0, -0.5; down gaps only at bars 1, 7,
    # so the windows ending at bars 4, 5, 6 hold none
    assert out.isna().tolist() == [True] * 3 + [False, True, True, True, False]
    assert np.isfinite(out.dropna()).all()


def test_nan_rate_under_frequent_flat_opens():
    o, c = _walk(n=2000, p_flat=0.8)
    dn = (c.shift(1) - o).clip(lower=0)
    no_down = ((dn > 0).rolling(40).sum() == 0).iloc[40:]  # full windows only (bar 0 has no gap)
    assert len(no_down) == 1960 and int(no_down.sum()) == 50
    out = gapm(o, c)
    assert int(out.isna().sum()) == 109
    assert not np.isinf(out).any()
    assert (round(out.min(), 3), round(out.median(), 3), round(out.max(), 3)) == (0.176, 1.254, 26.385)


def test_edge_cases():
    o, c = _walk()
    base = gapm(o, c)
    on = o.copy()
    on[600] = np.nan
    out = gapm(on, c)
    # the NaN gap sits in 40 windows: those ratios and outputs are NaN
    assert out.iloc[600:640].isna().all() and out.iloc[640:].notna().all()
    pd.testing.assert_series_equal(out.iloc[:600], base.iloc[:600])
    pd.testing.assert_series_equal(gapm(o, c, offset=1), base.shift(1))
    assert gapm(o, c, fillna=0).isna().sum() == 0
    assert gapm(on, c, fill_method="ffill").iloc[600:].isna().sum() == 0
    with pytest.raises(ValueError):
        gapm(on, c, fill_method="ffil")  # used to bfill silently: bar 600 read bar 640


# -------------------------------------------------------------- causality

_REAL = importlib.import_module("pandas_ta.momentum.gapm")


def _load_mutant(old, new, tag):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType(f"_gapm_mutant_{tag}")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


MUTANTS = {
    "gap": ("gap = open_ - close.shift(1)", "gap = open_ - close.shift(-1)"),
    "window": ("ratio = up.rolling(length).sum()", "ratio = up.shift(-1).rolling(length).sum()"),
    "write": ('gapm.name = f"GAPM', 'gapm = gapm.shift(-1); gapm.name = f"GAPM'),
}

OFFSETS = range(70, 1150, 35)  # 31 offsets


def _moved(a, b):
    if not (a.isna() == b.isna()).all():
        return True
    m = a.notna()
    return bool((a[m] != b[m]).any())


def _leaks(fn):
    """Count offsets `j` at which rewriting bars >= j moves any bar < j.

    A random rewrite alone caught the `window` mutant at only 28 of 31: when
    bar j gaps down in both walks, its up gap is 0 either way.  The second
    future opens every bar 1000 above the prior close, so bar j's up gap
    must change.
    """
    o, c = _walk()
    base = fn(o, c)
    fo, fc = _walk(seed=99)
    hits = 0
    up_o = c.shift(1) + 1000.0
    for j in OFFSETS:
        for fut_o, fut_c in ((fo, fc), (up_o, c)):
            po, pc = o.copy(), c.copy()
            po.iloc[j:], pc.iloc[j:] = fut_o.iloc[j:].values, fut_c.iloc[j:].values
            if _moved(base.iloc[:j], fn(po, pc).iloc[:j]):
                hits += 1
                break
    return hits


def test_real_module_never_reads_the_future():
    assert _leaks(gapm) == 0


@pytest.mark.parametrize("tag", sorted(MUTANTS))
def test_mutant_is_caught(tag):
    mod = _load_mutant(*MUTANTS[tag], tag)
    o, c = _walk()
    assert not mod.gapm(o, c).equals(gapm(o, c))
    assert _leaks(mod.gapm) == len(OFFSETS)


# ------------------------------------------------------------ scale-free


@pytest.mark.parametrize("k", [8.0, 64.0])
def test_scale_is_bit_identical(k):
    o, c = _walk()
    base, scaled = gapm(o, c), gapm(o * k, c * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_scale_within_tolerance(k):
    o, c = _walk()
    base, scaled = gapm(o, c), gapm(o * k, c * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    np.testing.assert_allclose(scaled[m], base[m], rtol=1.8e-14)


def test_column_is_not_constant():
    out = gapm(*_walk())
    assert int(out.isna().sum()) == 59 and out.first_valid_index() == 59
    assert int((out > 1).sum()) == 706 and int((out < 1).sum()) == 435
    assert 0 < int((out > 1).sum()) < len(out)


# ---------------------------------------------------------------- wiring


def test_name_registration_and_accessor():
    o, c = _walk(300)
    df = DataFrame({"open": o, "high": np.maximum(o, c), "low": np.minimum(o, c),
                    "close": c, "volume": 1.0})
    assert "gapm" in ta.Category["momentum"]
    out = df.ta.gapm()
    assert out.name == "GAPM_40_20"
    pd.testing.assert_series_equal(out, gapm(o, c))
    custom = df.ta.gapm(length=10, signal=5)
    assert custom.name == "GAPM_10_5"
    pd.testing.assert_series_equal(custom, gapm(o, c, length=10, signal=5))
