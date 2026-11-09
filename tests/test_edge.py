# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.volatility.edge` -- the Ardia, Guidotti & Kroencke
(2024) EDGE bid-ask spread estimator from open/high/low/close. Measurements
are in docs/EdgeMeasured.md.

What these pin, in order of how much it would hurt to lose:

* CORRECTNESS against the authors' own published number: the first 10 rows
  of eguidotti/bidask `pseudocode/ohlc.csv` (MIT, embedded below) give
  -0.016889917516422 signed in the reference's own test suite; EDGE_10 on
  them reads its magnitude to 1e-12 relative. Plus an independent
  transcription of the reference `edge()` (log differences, exact ties,
  nan-means, one window at a time -- none of the module's code) at 12 bars
  of a simulated frame, to 1e-9 relative.
* SEMANTICS: on a simulated market with a known spread (390 one-minute
  steps a day, a trade seen with probability 0.1 at the bid or the ask),
  EDGE_21 recovers a 5% spread and, over 10 paths, a 1% one. And the noise
  floor: at a ZERO spread EDGE_21 is not zero -- the unsigned form
  sqrt(|s2|) folds the estimator's noise up, and that noise is
  proportional to volatility (pinned: doubling sigma doubles it).
* CAUSALITY by future-perturbation over 16 offsets, and a mutant
  (`importlib` source read, the write index moved one bar earlier, `exec`'d
  in memory) proved live and caught. Plus two reach facts: the current
  bar's close is not read, and a bad tick moves exactly the `length` bars
  whose window holds it -- no rolling-sum residue after it leaves.
* The tie tolerance: ties moved by one ulp (adjusted-price noise) leave
  EDGE within 1e-12; the reference's exact tie test moves by 29% on the
  same input.
* SCALE-FREE: x8/x64 bit-identical with matching NaN masks, x10/x3.7
  within 1e-12, and `0 < fires < n` with every fired value distinct.
* Edge cases and wiring (`Category`, the accessor, `EDGE_21`).
"""
import importlib
import io
import types
import warnings

import numpy as np
import pandas as pd
import pytest
from pandas import Series

from .context import pandas_ta as ta

_REAL = importlib.import_module("pandas_ta.volatility.edge")
edge = _REAL.edge

# The first 10 rows of eguidotti/bidask pseudocode/ohlc.csv (commit 1caba55),
# Copyright (c) 2024 Emanuele Guidotti, MIT License. Simulated with a constant
# 1% spread. The reference's tests/test_edge.py: edge(rows 0:10, sign=True)
# == -0.016889917516422.
PUBLISHED_ROWS = """Open,High,Low,Close
1.00240075994025,1.00935878365403,0.976061138469904,0.976061138469904
0.929743096395543,0.929774737723069,0.928919694164385,0.929774737723069
0.943911414384193,0.968140794511406,0.943911414384193,0.968140794511406
0.977605378856722,0.977605378856722,0.977605378856722,0.977605378856722
0.961535370407048,0.99982474278851,0.961535370407048,0.986215329667607
0.982409003083975,0.992213437101346,0.982409003083975,0.992213437101346
1.03435413274433,1.03435413274433,1.03435413274433,1.03435413274433
1.0201424300403,1.04025465277235,1.0201424300403,1.03219266262805
1.03650094499406,1.03650094499406,1.03650094499406,1.03650094499406
1.05368509087896,1.05368509087896,1.02605242183949,1.02798086837104
"""
PUBLISHED_SIGNED = -0.016889917516422


def _published():
    df = pd.read_csv(io.StringIO(PUBLISHED_ROWS))
    return df.Open, df.High, df.Low, df.Close


def _oracle(op, hi, lo, cl):
    """eguidotti/bidask `edge()` transcribed: log differences, exact ties,
    nan-means, unsigned. One window."""
    o, h, l, c = (np.log(np.asarray(x, dtype=float)) for x in (op, hi, lo, cl))
    m = (h + l) / 2.0
    h1, l1, c1, m1 = h[:-1], l[:-1], c[:-1], m[:-1]
    o, h, l, m = o[1:], h[1:], l[1:], m[1:]
    r1, r2, r3, r4, r5 = m - o, o - m1, m - c1, c1 - m1, o - c1
    tau = ((h != l) | (l != c1)).astype(float)
    po = np.mean(tau * (o != h)) + np.mean(tau * (o != l))
    pc = np.mean(tau * (c1 != h1)) + np.mean(tau * (c1 != l1))
    pt = np.mean(tau)
    if tau.sum() < 2 or po == 0 or pc == 0:
        return np.nan
    d1 = r1 - np.mean(r1) / pt * tau
    d3 = r3 - np.mean(r3) / pt * tau
    d5 = r5 - np.mean(r5) / pt * tau
    x1 = -4.0 / po * d1 * r2 + -4.0 / pc * d3 * r4
    x2 = -4.0 / po * d1 * r5 + -4.0 / pc * d5 * r4
    e1, e2 = np.mean(x1), np.mean(x2)
    v1, v2 = np.mean(x1 ** 2) - e1 ** 2, np.mean(x2 ** 2) - e2 ** 2
    vt = v1 + v2
    s2 = (v2 * e1 + v1 * e2) / vt if vt > 0 else (e1 + e2) / 2.0
    return np.sqrt(np.abs(s2))


def _sim(n=600, spread=0.01, q=0.1, sigma=0.02, seed=0, minutes=390):
    """The paper's simulation design: the efficient log price walks per
    minute; each minute a trade is seen with probability q, at the bid or
    the ask (a fair coin); the day's OHLC are its first, highest, lowest and
    last seen trades. A day with no trade repeats the prior close."""
    rng = np.random.default_rng(seed)
    p = np.log(100.0) + np.cumsum(rng.normal(0.0, sigma / np.sqrt(minutes), n * minutes)).reshape(n, minutes)
    side = rng.choice([-1.0, 1.0], size=p.shape)
    seen = rng.random(p.shape) < q
    seen[0, 0] = True
    px = np.where(seen, np.exp(p) * (1 + side * spread / 2), np.nan)
    traded = seen.any(axis=1)
    rows = np.arange(n)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        o = px[rows, seen.argmax(axis=1)]
        c = px[rows, minutes - 1 - seen[:, ::-1].argmax(axis=1)]
        h, l = np.nanmax(px, axis=1), np.nanmin(px, axis=1)
    c = pd.Series(np.where(traded, c, np.nan)).ffill().to_numpy()
    prev = np.r_[c[0], c[:-1]]
    o, h, l = (np.where(traded, x, prev) for x in (o, h, l))
    return Series(o), Series(h), Series(l), Series(c)


# ------------------------------------------------------------ correctness


def test_reproduces_the_published_value():
    out = edge(*_published(), length=10)
    assert out.iloc[:9].isna().all()
    assert out.iloc[9] == pytest.approx(abs(PUBLISHED_SIGNED), rel=1e-12)


def test_oracle_reproduces_the_published_value():
    """The test's own oracle is checked against the authors' number too, so
    the comparison below is against a verified transcription."""
    assert _oracle(*_published()) == pytest.approx(abs(PUBLISHED_SIGNED), rel=1e-12)


@pytest.mark.parametrize("length", [3, 21, 63])
def test_matches_the_reference_window_by_window(length):
    o, h, l, c = _sim(seed=5)
    out = edge(o, h, l, c, length=length)
    for t in np.linspace(length - 1, len(o) - 1, 12).astype(int):
        w = slice(t - length + 1, t + 1)
        expected = _oracle(o[w], h[w], l[w], c[w])
        assert out.iloc[t] == pytest.approx(expected, rel=1e-9), t


# --------------------------------------------------------------- semantics


def test_recovers_a_wide_spread():
    out = edge(*_sim(n=1000, spread=0.05, seed=2))
    assert abs(out.median() / 0.05 - 1) < 0.02  # measured 0.04973


def test_recovers_a_one_percent_spread_over_paths():
    """Single 1000-day paths read medians 0.00866 to 0.01026 (measured); the
    median over 10 paths is pinned near 1%, slightly low."""
    meds = [edge(*_sim(n=1000, spread=0.01, seed=100 + k)).median() for k in range(10)]
    assert np.median(meds) == pytest.approx(0.009575, abs=1e-5)


def test_zero_spread_reads_a_volatility_floor():
    """The disclosure: at spread 0 half the windows estimate s2 < 0, and the
    unsigned form folds them up. The floor is proportional to volatility:
    the same seed at twice the sigma reads twice the median."""
    lo = edge(*_sim(n=1000, spread=0.0, sigma=0.02, seed=7)).median()
    hi = edge(*_sim(n=1000, spread=0.0, sigma=0.04, seed=7)).median()
    assert lo == pytest.approx(0.004571, abs=1e-6)
    assert hi / lo == pytest.approx(2.0, rel=1e-6)


# -------------------------------------------------------------- causality


MUTANT = (
    "values[length - 1:] = np.where(complete, _edge_rows(*windows), np.nan)",
    "values[length - 2:-1] = np.where(complete, _edge_rows(*windows), np.nan)",
)

OFFSETS = range(40, 600, 35)  # 16 offsets


def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_edge_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


def _leaks(fn):
    o, h, l, c = _sim(seed=11)
    other = _sim(seed=99)
    base = fn(o, h, l, c)
    hits = 0
    for j in OFFSETS:
        p = [x.copy() for x in (o, h, l, c)]
        for x, y in zip(p, other):
            x.iloc[j:] = y.iloc[j:].to_numpy()
        out = fn(*p)
        a, b = base.iloc[:j], out.iloc[:j]
        if not (a.isna() == b.isna()).all() or (a[a.notna()] != b[a.notna()]).any():
            hits += 1
    return hits


def test_real_module_never_reads_the_future():
    assert _leaks(edge) == 0


def test_mutant_is_caught():
    mod = _load_mutant(*MUTANT)
    sim = _sim(seed=11)
    assert not mod.edge(*sim).equals(edge(*sim))  # live
    assert _leaks(mod.edge) == len(OFFSETS)


def test_current_close_is_not_read():
    """The reference uses close only as the PRIOR close (c1): bar T's close
    first enters bar T + 1."""
    o, h, l, c = _sim(seed=4)
    base = edge(o, h, l, c)
    c2 = c.copy()
    c2.iloc[300] *= 1.3
    out = edge(o, h, l, c2)
    pd.testing.assert_series_equal(out.iloc[:301], base.iloc[:301])
    assert out.iloc[301] != base.iloc[301]


def test_a_bad_tick_moves_exactly_its_windows():
    """high x1000 at bar 300: bars 300..320 move (the 21 windows that hold
    it); every other bar is bit-identical -- no rolling-sum residue."""
    o, h, l, c = _sim(seed=4)
    base = edge(o, h, l, c)
    h2 = h.copy()
    h2.iloc[300] *= 1e3
    out = edge(o, h2, l, c)
    moved = np.flatnonzero(~((out == base) | (out.isna() & base.isna())).to_numpy())
    assert moved.tolist() == list(range(300, 321))


def test_ulp_noise_on_ties_is_ignored():
    """Move every price that ties the high or low by one ulp, as an
    adjustment factor can: EDGE stays within 1e-12 of the published value;
    the reference's exact tie test reads 29% lower (0.7069x) on the same input."""
    o, h, l, c = (x.to_numpy() for x in _published())
    o2 = np.where((o == h) | (o == l), np.nextafter(o, np.inf), o)
    c2 = np.where((c == h) | (c == l), np.nextafter(c, np.inf), c)
    ours = edge(Series(o2), Series(h), Series(l), Series(c2), length=10).iloc[9]
    exact = _oracle(o2, h, l, c2)
    assert ours == pytest.approx(abs(PUBLISHED_SIGNED), rel=1e-12)
    assert exact / abs(PUBLISHED_SIGNED) == pytest.approx(0.7069, abs=1e-4)


# ------------------------------------------------------------ scale-free


@pytest.mark.parametrize("k", [8.0, 64.0])
def test_power_of_two_scale_is_bit_identical(k):
    o, h, l, c = _sim(seed=4)
    base, scaled = edge(o, h, l, c), edge(o * k, h * k, l * k, c * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_other_scales_within_tolerance(k):
    o, h, l, c = _sim(seed=4)
    base, scaled = edge(o, h, l, c), edge(o * k, h * k, l * k, c * k)
    assert (base.isna() == scaled.isna()).all()
    assert (base - scaled).abs().max() < 1e-12


def test_fires_and_is_not_constant():
    out = edge(*_sim(seed=4))
    assert out.notna().sum() == 580  # 600 bars, 20 warm-up
    assert out.dropna().nunique() == 580


# ------------------------------------------------------------- edge cases


def test_warmup_and_short_input():
    o, h, l, c = _sim(n=30, seed=1)
    assert edge(o, h, l, c).iloc[:20].isna().all()
    assert edge(o.iloc[:20], h.iloc[:20], l.iloc[:20], c.iloc[:20]) is None


def test_flat_prices_are_nan():
    """No bar trades at two prices (tau = 0 everywhere): the reference
    returns missing."""
    flat = Series([10.0] * 30)
    assert edge(flat, flat, flat, flat).isna().all()


@pytest.mark.parametrize("bad", [np.nan, 0.0, -1.0])
def test_a_bad_price_blanks_its_windows(bad):
    o, h, l, c = _sim(n=100, seed=1)
    base = edge(o, h, l, c)
    l2 = l.copy()
    l2.iloc[50] = bad
    out = edge(o, h, l2, c)
    assert out.iloc[50:71].isna().all()
    pd.testing.assert_series_equal(out.drop(range(50, 71)), base.drop(range(50, 71)))


def test_length_below_three_falls_back_to_default():
    o, h, l, c = _sim(n=60, seed=1)
    assert edge(o, h, l, c, length=2).name == "EDGE_21"


# ---------------------------------------------------------------- wiring


def test_name_registration_and_accessor():
    o, h, l, c = _sim(n=100, seed=1)
    df = pd.DataFrame({"open": o, "high": h, "low": l, "close": c, "volume": 1.0})
    assert "edge" in ta.Category["volatility"]
    out = df.ta.edge()
    assert out.name == "EDGE_21"
    pd.testing.assert_series_equal(out, edge(o, h, l, c))
    assert df.ta.edge(length=10).name == "EDGE_10"
