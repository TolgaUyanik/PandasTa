# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.statistics.halflife` -- the Ornstein-Uhlenbeck
mean-reversion half-life over a rolling window: regress dP_t on P_{t-1},
half-life = -ln(2) / lambda, NaN outside -1 < lambda < 0. PandasTa issue #4
(HLIFE-1, HLIFE-2). Measurements and the open gates are in
`docs/HalfLifeMeasured.md`.

What these tests pin, in order of how much it would hurt to lose them:

* CORRECTNESS against a known truth (HLIFE-1 (a), the issue's oracle): for
  each theta in 0.02, 0.05, 0.1, 0.2, K = 50 independent 2,001-bar O-U
  paths `P_t = P_{t-1} - theta (P_{t-1} - 100) + e_t`, one 2,000-pair
  estimate per path. The median relative error against ln(2)/theta is
  -1.6%, +0.8%, +0.1%, +0.6%; one path's own SD is 20.3%, 13.3%, 9.0%,
  6.3%, so the standard error of the median (1.2533 SD / sqrt(K)) is 3.6%,
  2.3%, 1.6%, 1.1%. The test asserts |median error| <= 3 such SEs, with the
  SDs fixed at their measured values (not recomputed from the sample, so a
  variance blow-up cannot widen its own band), and the sample SD within
  25% of them. Against an independent `np.polyfit` loop: NaN masks
  identical, asserted rtol 1e-8 over lengths 100, 30, 3 on a walk and an
  O-U path. A hand fixture (HLIFE-1 (b)) shows
  the arithmetic: closes 10, 12, 13, 13.5 at length 3 -> lambda -0.5 ->
  2 ln 2.
* THE BIAS AT THE DEFAULT WINDOW, pinned so nobody reads it as signal: at
  100 bars the OLS AR(1) slope is biased negative (Kendall/Hurwicz; the
  Dickey-Fuller distribution at a unit root), so the same four processes
  (one 20,000-bar path each, all 100-bar windows) read medians 12.35, 8.83,
  5.58, 3.12 -- 64% to 10% short -- and 200 independent 101-bar random walks
  read median 14.87 (10th-90th percentile 6.0 to 52.5) with only 8 of 200
  NaN. A slow reverter (true 34.7) and a random walk look alike; fast
  reversion separates: 200 O-U(0.2) windows read median 3.06, all 200
  below the random-walk median.
* THE NAMED NaN BRANCH (HLIFE-1's design decision: NaN, chosen by the port
  author, pending the owner's confirmation on PR #256): lambda >= 0
  (trending, flat) and lambda <= -1 (outside monotone decay: the deviation
  vanishes in one bar at -1, oscillates while decaying for -2 < lambda < -1,
  does not decay at <= -2) are NaN, never negative or inf. A flat stretch
  followed by a move is NaN on pandas 2 and 3 alike. pandas 3 can leave a
  ~1e-12 residue in a flat window's rolling var; before review round 2 that
  yielded half-lives of 68 to 105,244 bars on 43 of 200 such series.
  Flatness is now tested exactly (rolling max == min); with that test
  removed, the pinned case still fails on 22 of 120 series on pandas 3.
* CAUSALITY by future-perturbation over 31 offsets with two futures; two
  one-bar look-ahead mutants (the output written one bar early, the change
  read one bar ahead) proved live, then caught at 31 of 31.
* NO RECURSIVE STAGE, measured on values (HLIFE-2): a +5% move of close 500
  changes all 101 bars whose window holds it (by at least 7.2%), leaves
  bars < 500 bit-identical, moves bars 601-799 by at most 6.6e-15 relative
  (the rounding residue of pandas' rolling add/remove, which IS a numerical
  dependence on departed values), and leaves bars >= 800 bit-identical: the
  sums run in independent blocks of 4 * length bars, so the residue ends at
  the next block. An EMA-smoothed mutant moves later bars by 0.25 and is
  caught.
* BOUNDED PRECISION on hostile inputs, against an independent loop: a
  level collapse from 1e5 to 1 matches to 7.8e-14 everywhere (the round-1
  code, unblocked and unanchored, was off by 5.5% there; anchored but
  unblocked, 0.38%); a single 1e7 bad tick in a walk near
  100 leaves at most 2.1e-5 inside its own block and 3.0e-14 from the next
  block on.
* SCALE-FREE (HLIFE-2 D): close x8 and x64 bit-identical; x10 and x3.7
  within 1.1e-13 and 9.5e-14 relative (asserted <= 1e-10), NaN masks match.
  Not constant: 1,095 distinct values over 1,095 non-NaN bars of the seed-11
  walk, range 3.13 to 2341 bars.
* THE FAMILY (#4's tie rule; synthetic indication, not Gate E): on 10
  tick-rounded 3,000-bar walks, Spearman rho against KPSS_100 has median
  0.240 (max 0.458), against CUSUM_100 0.224 (max 0.334), against ZSCORE_20
  -0.008.
* EDGES: a NaN close blanks its own bar and the next `length` (101 bars in
  all at the default); the 100-bar warm-up; `offset`, `fillna`; `length`
  below 3 falls back to 100; 100 closes return None.
* Wiring: `Category`, the accessor, the column name `HLIFE_100`.
"""
import importlib
import types

import numpy as np
import pandas as pd
import pytest
from pandas import DataFrame, Series

from .context import pandas_ta as ta
from pandas_ta.statistics.halflife import halflife

LN2 = np.log(2.0)


def _walk(n=1200, seed=11):
    """Tick-rounded geometric random walk around 100."""
    rng = np.random.default_rng(seed)
    return Series(np.round(100 * np.exp(np.cumsum(rng.normal(0, 0.015, n))), 2))


def _ou(theta, n, rng, mu=100.0, sigma=1.0):
    """Discrete O-U: dP_t = -theta (P_{t-1} - mu) + e_t, so lambda = -theta exactly."""
    p = np.empty(n)
    p[0] = mu
    e = rng.normal(0, sigma, n)
    for t in range(1, n):
        p[t] = p[t - 1] - theta * (p[t - 1] - mu) + e[t]
    return Series(p)


def _reference(close, length):
    """Per-window `np.polyfit` of dP_t on P_{t-1}, with the same NaN domain."""
    c = np.asarray(close, dtype=float)
    out = np.full(len(c), np.nan)
    for T in range(length, len(c)):
        x = c[T - length:T]
        lam = np.polyfit(x, c[T - length + 1:T + 1] - x, 1)[0]
        out[T] = -LN2 / lam if -1 < lam < 0 else np.nan
    return out


# ------------------------------------------------------------ correctness


def test_hand_computed():
    # pairs (P_{t-1}, dP_t): (10, 2), (12, 1), (13, .5)
    # x mean 35/3 -> xc = [-5/3, 1/3, 4/3]; y mean 7/6 -> yc = [5/6, -1/6, -2/3]
    # sum(xc*yc) = (-25 - 1 - 16) / 18 = -7/3; sum(xc^2) = 42/9 = 14/3
    # lambda = -7/3 / (14/3) = -0.5 -> half-life ln2 / 0.5 = 1.3863
    out = halflife(Series([10.0, 12.0, 13.0, 13.5]), length=3)
    assert out.isna().tolist() == [True] * 3 + [False]
    assert out.iloc[3] == pytest.approx(2 * LN2, rel=1e-12)


@pytest.mark.parametrize("theta, sd", [(0.02, 0.203), (0.05, 0.133), (0.10, 0.090), (0.20, 0.063)])
def test_recovers_a_known_half_life(theta, sd):
    K = 50
    err = np.array([
        halflife(_ou(theta, 2001, np.random.default_rng(1000 + k)), length=2000).iloc[-1]
        / (LN2 / theta) - 1
        for k in range(K)])
    assert not np.isnan(err).any()
    # the spread is what it was measured to be: a variance blow-up fails here
    assert 0.75 * sd <= err.std(ddof=1) <= 1.25 * sd
    # median of K independent estimates within 3 standard errors of the median,
    # from the fixed measured SD (1.2533 SD / sqrt(K): 3.6%, 2.3%, 1.6%, 1.1%)
    assert abs(np.median(err)) <= 3 * 1.2533 * sd / np.sqrt(K)


@pytest.mark.parametrize("theta, median", [
    (0.02, 12.347), (0.05, 8.832), (0.10, 5.579), (0.20, 3.123)])
def test_the_default_window_is_biased_short(theta, median):
    s = _ou(theta, 20000, np.random.default_rng(7))
    out = halflife(s)
    assert out.median() == pytest.approx(median, abs=1e-3)
    assert out.median() < LN2 / theta


def test_random_walks_rarely_go_nan_and_fast_reversion_separates():
    rng = np.random.default_rng(5)
    rw = np.array([halflife(Series(100 * np.exp(np.cumsum(rng.normal(0, 0.01, 101))))).iloc[-1]
                   for _ in range(200)])
    fast = np.array([halflife(_ou(0.2, 101, rng)).iloc[-1] for _ in range(200)])
    assert int(np.isnan(rw).sum()) == 8
    assert np.nanmedian(rw) == pytest.approx(14.865, abs=1e-3)
    np.testing.assert_allclose(np.nanpercentile(rw, [10, 90]), [6.0125, 52.519], atol=1e-3)
    assert int(np.isnan(fast).sum()) == 0
    assert np.median(fast) == pytest.approx(3.0625, abs=1e-3)
    assert (fast < np.nanmedian(rw)).all()


@pytest.mark.parametrize("length", [100, 30, 3])
@pytest.mark.parametrize("which", ["walk", "ou"])
def test_matches_an_independent_polyfit_loop(length, which):
    s = _walk(400) if which == "walk" else _ou(0.1, 400, np.random.default_rng(1))
    out = halflife(s, length=length)
    ref = _reference(s, length)
    assert (np.isnan(ref) == out.isna().values).all()
    m = ~np.isnan(ref)
    # blocked, anchored rolling sums vs polyfit: rounding only
    np.testing.assert_allclose(out.values[m], ref[m], rtol=1e-8)


def test_hostile_inputs_stay_precise():
    # a level collapse from 1e5 to 1: round-1 code 5.5% off, unblocked 0.38% off
    col = Series(np.r_[1e5 * np.exp(np.cumsum(np.random.default_rng(2).normal(0, .01, 300))),
                       np.exp(np.cumsum(np.random.default_rng(3).normal(0, .01, 1000)))])
    out, ref = halflife(col).values, _reference(col, 100)
    assert (np.isnan(ref) == np.isnan(out)).all()
    m = ~np.isnan(ref)
    np.testing.assert_allclose(out[m], ref[m], rtol=1e-8)  # measured 7.8e-14
    # one 1e7 bad tick at bar 1000; blocks of 400 start at 800 and 1200
    bt = _walk(1600, 4)
    bt[1000] = 1e7
    out, ref = halflife(bt).values, _reference(bt, 100)
    assert (np.isnan(ref) == np.isnan(out)).all()
    m = ~np.isnan(ref)
    m_in, m_after = m.copy(), m.copy()
    m_in[1200:] = False
    m_after[:1200] = False
    np.testing.assert_allclose(out[m_in], ref[m_in], rtol=1e-4)  # measured 2.1e-5
    np.testing.assert_allclose(out[m_after], ref[m_after], rtol=1e-8)  # measured 3.0e-14


# --------------------------------------------------------- the NaN branch


def test_no_half_life_outside_minus_one_to_zero_is_nan():
    # an accelerating trend: dP grows with P, lambda > 0
    assert halflife(Series(100 * 1.01 ** np.arange(150))).isna().all()
    assert halflife(Series([50.0] * 150)).isna().all()  # flat: no variance in P
    # alternating 10/12: lambda = -2, the deviation flips sign every bar
    assert halflife(Series([10.0, 12.0] * 4), length=3).isna().all()
    # an explosive zig-zag: lambda < -2
    assert halflife(Series([10.0, 12, 9, 14, 7, 17, 3]), length=3).isna().all()
    out = halflife(_walk())
    assert (out.dropna() > 0).all() and np.isinf(out.values).sum() == 0


def test_flat_then_move_is_nan():
    # forward-filled closes (a halted name), then trading resumes: every window
    # whose 100 previous closes are all equal has no half-life. The flat stretch
    # starts at bar 1000, in a later block whose anchor is away from its level.
    hits = 0
    for level in (1.0, 100.0, 1e4):
        for seed in range(40):
            rng = np.random.default_rng(seed)
            w = level * np.exp(np.cumsum(rng.normal(0, .01, 1000)))
            s = Series(np.r_[w, [w[-1]] * 150, w[-1] * np.exp(np.cumsum(rng.normal(0, .01, 50)))])
            hits += int(halflife(s)[1100:1151].notna().any())
    # without the exact flatness test: 22 of 120 on pandas 3.0.0, 0 on 2.3.3
    assert hits == 0


def test_edge_cases():
    close = _walk()
    base = halflife(close)
    assert int(base.isna().sum()) == 105  # 100 warm-up + 5 windows with no half-life
    cn = close.copy()
    cn[500] = np.nan
    gap = halflife(cn)
    assert gap[500:601].isna().all()
    assert (gap[601:].isna() == base[601:].isna()).all()
    assert int(gap.isna().sum() - base.isna().sum()) == 101
    for bad in (1, 2, 2.9):
        assert halflife(close, length=bad).name == "HLIFE_100"
    assert halflife(close, length=3.9).name == "HLIFE_3"
    pd.testing.assert_series_equal(halflife(close, offset=1), base.shift(1))
    assert halflife(close, fillna=0).isna().sum() == 0
    assert halflife(close.iloc[:100]) is None  # needs length + 1 closes
    assert int(halflife(close.iloc[:101]).notna().sum()) == 1


# -------------------------------------------------- no recursive stage


def _reach(fn):
    """Move close 500 by +5%; return (head bit-equal, bars changed in 500..600,
    smallest relative change there, largest relative change in 601..799,
    bars >= 800 bit-equal)."""
    close = _walk()
    p = close.copy()
    p[500] *= 1.05
    base, moved = fn(close), fn(p)
    win, after = base[500:601].notna(), base[601:800].notna()
    rel_in = ((moved[500:601] - base[500:601]).abs() / base[500:601])[win]
    rel_after = ((moved[601:800] - base[601:800]).abs() / base[601:800])[after]
    return (moved[:500].equals(base[:500]), int((rel_in > 0).sum()), rel_in.min(),
            rel_after.max(), moved[800:].equals(base[800:]))


def test_the_taint_reach_is_exactly_the_window():
    head, changed, smallest, after, next_block = _reach(halflife)
    assert head
    assert changed == 101 and smallest > 0.07  # measured 0.0719
    # same block: rolling-sum rounding residue only (measured 6.6e-15)
    assert after <= 1e-10
    # the next block (from bar 800) never saw close 500
    assert next_block


def test_a_recursive_stage_would_be_caught():
    def ema(s):
        h = halflife(s)
        return h.ewm(span=10, ignore_na=True).mean().where(h.notna())
    assert _reach(ema)[3] > 0.1  # measured 0.25


# -------------------------------------------------------------- causality

_REAL = importlib.import_module("pandas_ta.statistics.halflife")


def _load_mutant(old, new, tag):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType(f"_halflife_mutant_{tag}")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


MUTANTS = {
    # the slope written one bar early: bar T reports the window ending at T+1
    "write": ("return (sxy / sxx).where(~flat & (sxx > 0)).to_numpy()",
              "return (sxy / sxx).where(~flat & (sxx > 0)).shift(-1).to_numpy()"),
    # the one-bar change read one bar ahead
    "change": ("change = x.diff()", "change = x.diff().shift(-1)"),
}

OFFSETS = range(110, 1150, 34)  # 31 offsets


def _moved(a, b):
    if not (a.isna() == b.isna()).all():
        return True
    m = a.notna()
    return bool((a[m] != b[m]).any())


def _leaks(fn):
    """Count offsets `j` at which rewriting closes >= j moves any bar < j."""
    close = _walk()
    base = fn(close)
    other = _walk(seed=99)
    hits = 0
    for j in OFFSETS:
        for future in (other.iloc[j:].values, close.iloc[j:].values * 1000.0):
            pc = close.copy()
            pc.iloc[j:] = future
            if _moved(base.iloc[:j], fn(pc).iloc[:j]):
                hits += 1
                break
    return hits


def test_real_module_never_reads_the_future():
    assert _leaks(halflife) == 0


@pytest.mark.parametrize("tag", sorted(MUTANTS))
def test_mutant_is_caught(tag):
    mod = _load_mutant(*MUTANTS[tag], tag)
    close = _walk()
    assert not mod.halflife(close).equals(halflife(close))
    assert _leaks(mod.halflife) == len(OFFSETS)


# ------------------------------------------------------------ scale-free


@pytest.mark.parametrize("k", [8.0, 64.0])
def test_price_scale_is_bit_identical(k):
    close = _walk()
    base, scaled = halflife(close), halflife(close * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_price_scale_within_tolerance(k):
    close = _walk()
    base, scaled = halflife(close), halflife(close * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    # measured 1.1e-13 (x10) and 9.5e-14 (x3.7) relative on numpy 2.5.4. Relative
    # error in the half-life is relative error in lambda, which grows as lambda
    # nears 0 (values up to 2341 bars here); the bound leaves ~1000x headroom.
    assert ((scaled[m] - base[m]).abs() / base[m]).max() <= 1e-10


def test_column_is_not_constant():
    out = halflife(_walk())
    m = out.notna()
    assert int(m.sum()) == 1095 and out[m].nunique() == 1095
    assert 3.1276 < out.min() < 3.1277 and 2341.45 < out.max() < 2341.46


# ---------------------------------------------------------------- family


def test_family_overlap_on_synthetic_walks():
    """#4's tie rule, as an indication only: real-data rho is HLIFE-3's job."""
    rho = {"kpss": [], "cusum": [], "zscore": []}
    for seed in range(10):
        w = _walk(3000, seed)
        h = halflife(w)
        for name, s in (("kpss", ta.kpss(w)), ("cusum", ta.cusum(w)), ("zscore", ta.zscore(w, 20))):
            m = h.notna() & s.notna()
            rho[name].append(h[m].rank().corr(s[m].rank()))
    assert np.median(rho["kpss"]) == pytest.approx(0.2398, abs=1e-3)
    assert max(rho["kpss"]) == pytest.approx(0.4575, abs=1e-3)
    assert np.median(rho["cusum"]) == pytest.approx(0.2239, abs=1e-3)
    assert max(rho["cusum"]) == pytest.approx(0.3342, abs=1e-3)
    assert np.median(rho["zscore"]) == pytest.approx(-0.0082, abs=1e-3)


# ---------------------------------------------------------------- wiring


def test_name_registration_and_accessor():
    close = _walk(300)
    df = DataFrame({"open": close, "high": close, "low": close, "close": close, "volume": 1.0})
    assert "halflife" in ta.Category["statistics"]
    out = df.ta.halflife()
    assert out.name == "HLIFE_100"
    pd.testing.assert_series_equal(out, halflife(close), check_exact=True)
    assert df.ta.halflife(length=30).name == "HLIFE_30"
