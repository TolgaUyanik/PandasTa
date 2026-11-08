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
  -1.6%, +0.8%, +0.1%, +0.6%; one path's own SD is 20%, 13%, 9%, 6%. The
  test asserts |median error| <= 3 SD / sqrt(K), a tolerance derived from
  the measured spread, not picked. Against an independent `np.polyfit`
  loop: max relative difference 1.3e-10 over lengths 100, 30, 3 on a walk
  and an O-U path, NaN masks identical. A hand fixture (HLIFE-1 (b)) shows
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
  (trending, flat) and lambda <= -1 (the deviation flips sign every bar,
  or explodes) are NaN, never negative, inf or a sub-bar value.
* CAUSALITY by future-perturbation over 31 offsets with two futures; two
  one-bar look-ahead mutants (the output written one bar early, the change
  read one bar ahead) proved live, then caught at 31 of 31.
* NO RECURSIVE STAGE, measured on values (HLIFE-2): a +5% move of close 500
  changes all 101 bars whose window holds it (by at least 7.2%), leaves
  bars < 500 bit-identical, and moves bars > 600 by at most 4.3e-13
  relative -- the add/remove rounding residue of pandas' rolling sums, not
  a dependence. An EMA-smoothed mutant moves them by 0.25 and is caught.
* SCALE-FREE (HLIFE-2 D): close x8 and x64 bit-identical; x10 and x3.7
  within 1.1e-12 and 2.8e-13 relative (asserted <= 1e-10), NaN masks match.
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


@pytest.mark.parametrize("theta", [0.02, 0.05, 0.10, 0.20])
def test_recovers_a_known_half_life(theta):
    K = 50
    err = np.array([
        halflife(_ou(theta, 2001, np.random.default_rng(1000 + k)), length=2000).iloc[-1]
        / (LN2 / theta) - 1
        for k in range(K)])
    assert not np.isnan(err).any()
    # median of K independent estimates, within 3 standard errors of the
    # per-path spread (measured SD 0.20 / 0.13 / 0.09 / 0.06)
    assert abs(np.median(err)) <= 3 * err.std(ddof=1) / np.sqrt(K)


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
    # measured max relative difference 1.3e-10 (length 3, walk): rolling sums vs polyfit
    np.testing.assert_allclose(out.values[m], ref[m], rtol=1e-8)


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
    smallest relative change there, largest relative change after 600)."""
    close = _walk()
    p = close.copy()
    p[500] *= 1.05
    base, moved = fn(close), fn(p)
    win, after = base[500:601].notna(), base[601:].notna()
    rel_in = ((moved[500:601] - base[500:601]).abs() / base[500:601])[win]
    rel_after = ((moved[601:] - base[601:]).abs() / base[601:])[after]
    return moved[:500].equals(base[:500]), int((rel_in > 0).sum()), rel_in.min(), rel_after.max()


def test_the_taint_reach_is_exactly_the_window():
    head, changed, smallest, after = _reach(halflife)
    assert head
    assert changed == 101 and smallest > 0.07  # measured 0.0719
    # measured 4.3e-13: pandas' rolling add/remove rounding residue, not a dependence
    assert after <= 1e-10


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
    "write": ("lam = (sxy / sxx.where(sxx > 0)).to_numpy()",
              "lam = (sxy / sxx.where(sxx > 0)).shift(-1).to_numpy()"),
    # the one-bar change read one bar ahead
    "change": ("change = c.diff()", "change = c.diff().shift(-1)"),
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
    # measured 1.1e-12 (x10) and 2.8e-13 (x3.7) relative on numpy 2.5.4. Relative
    # error in the half-life is relative error in lambda, which grows as lambda
    # nears 0 (values up to 2341 bars here); the bound leaves ~90x headroom.
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
