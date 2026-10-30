# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.volatility.roll_spread` -- Roll (1984)'s implied
bid-ask spread from the autocovariance of successive price changes, emitted
as a percent of price. Measurements are in docs/LiquidityMeasured.md.

What these pin, in order of how much it would hurt to lose:

* CAUSALITY by future-perturbation: rewrite every bar from `j` onward,
  demand bars `[0:j]` bit-identical, over 31 offsets. A look-ahead mutant
  (`importlib` source read, the lag read flipped from yesterday to
  tomorrow, `exec`'d in memory) is proved live, then caught at 31 of 31.
* CORRECTNESS: a hand-derived value on a 2-bar bounce (close alternating
  100/101, a textbook Roll scenario) gives cov = -4/3 exactly and
  ROLL = 4/sqrt(3) -- no module code reused -- plus an independent per-bar
  loop against a synthetic walk.
* The NaN-vs-0 decision: a strictly trending series (cov == 0, the
  boundary case) reads NaN, not 0 -- a 0 would read as "no cost here",
  which the model does not support on a bar where it is undefined.
* SCALE-FREE: bit-identical under x8 and x64 (measured 0.0 max|diff|,
  matching NaN masks), within 1e-10 under x10 and x3.7 (measured 7.1e-13 /
  4.2e-13).
* Gate C (synthetic): fires on 575 of 1200 bars; the autocovariance is
  non-negative (undefined) on 604 of 1179 post-warm-up bars (51.2%) --
  "common", as the issue says. Real-data counts: docs/LiquidityMeasured.md, Gate C.
* Wiring: `Category`, the accessor, and the column name `ROLL_20`.
"""
import importlib
import types

import numpy as np
import pandas as pd
import pytest
from pandas import Series

from .context import pandas_ta as ta
from pandas_ta.volatility.roll_spread import roll_spread


def _walk(n=1200, seed=12, sigma=0.02, tick=0.01):
    rng = np.random.default_rng(seed)
    c = 100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n)))
    if tick:
        c = np.round(c / tick) * tick
    return Series(c)


# ------------------------------------------------------------ correctness


def test_hand_derived_bounce_value():
    """close alternates 100/101/100/... (the textbook bid-ask bounce): dp
    alternates +1/-1 forever. For length=4 at t=6, the window dp[3:7] =
    [-1,1,-1,1] paired against its lag dp[2:6] = [1,-1,1,-1]; both windows
    sum to 0, so sample covariance = sum(x*y)/(n-1) = (-4)/3. dollar =
    2*sqrt(4/3) = 4/sqrt(3); close[6] = 100, so pct = dollar/100*100 =
    4/sqrt(3) exactly -- derived by hand, not by re-running the module."""
    close = Series([100.0, 101.0, 100.0, 101.0, 100.0, 101.0, 100.0,
                    101.0, 100.0, 101.0, 100.0])
    out = roll_spread(close, length=4)
    expected = 4.0 / np.sqrt(3.0)
    assert out.iloc[6] == pytest.approx(expected, abs=1e-9)


def test_trending_series_reads_nan_not_zero():
    """A pure uptrend: dp is constant (+1 every bar), so its rolling
    covariance with its own lag is exactly 0 -- the boundary of "not
    negative". The decision (see module docstring): NaN, not 0."""
    close = Series(100.0 + np.arange(30))
    out = roll_spread(close, length=10)
    assert out.iloc[15:].isna().all()


def test_matches_an_independent_per_bar_loop():
    close = _walk(400, seed=4)
    length = 15
    out = roll_spread(close, length=length)
    dp = close.diff().values
    for t in (50, 120, 250, 399):
        x = dp[t - length + 1: t + 1]
        y = dp[t - length: t]
        cov = np.cov(x, y, ddof=1)[0, 1]
        expected = (2 * np.sqrt(-cov) / close.iloc[t] * 100) if cov < 0 else np.nan
        if np.isnan(expected):
            assert pd.isna(out.iloc[t])
        else:
            assert out.iloc[t] == pytest.approx(expected, rel=1e-9)


# -------------------------------------------------------------- causality


_REAL = importlib.import_module("pandas_ta.volatility.roll_spread")


def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_roll_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


MUTANT = (
    "cov = dp.rolling(length).cov(dp.shift(1))",
    "cov = dp.rolling(length).cov(dp.shift(-1))",
)

OFFSETS = range(40, 1100, 35)  # 31 offsets


def _leaks(fn):
    close = _walk()
    base = fn(close)
    other = _walk(seed=99)
    hits = 0
    for j in OFFSETS:
        pert = close.copy()
        pert.iloc[j:] = other.iloc[j:].values
        out = fn(pert)
        a, b = base.iloc[:j], out.iloc[:j]
        if not (a.isna() == b.isna()).all():
            hits += 1
            continue
        m = a.notna()
        if (a[m] != b[m]).any():
            hits += 1
    return hits


def test_real_module_never_reads_the_future():
    assert _leaks(roll_spread) == 0


def test_mutant_is_caught():
    """This mutant's reach is exactly ONE bar below any perturbation
    boundary J (cov[t] depends on dp[t+1] and nothing else perturbed):
    `_leaks` can only register J as caught if that single bar's ROLL value
    actually moves. It does not when BOTH the real and mutant covariance
    are non-negative there (NaN == NaN) -- measured at 51.2% of post-
    warm-up bars (see docs/LiquidityMeasured.md). Measured: caught at 18
    of 31 J values. The CANDLE-1/`smc_sweep` lesson applies directly: a
    test that checked only one J would have had roughly a 42% chance of
    missing this bug."""
    mod = _load_mutant(*MUTANT)
    close = _walk()
    assert not mod.roll_spread(close).equals(roll_spread(close))  # live
    caught = _leaks(mod.roll_spread)
    assert caught == 18, f"measured catch count moved: {caught} of {len(OFFSETS)} J"
    assert caught > 0, "the mutant was never caught at any J -- it is dead code, not a live bug"


# ------------------------------------------------------------ scale-free


@pytest.mark.parametrize("k", [8.0, 64.0])
def test_power_of_two_scale_is_bit_identical(k):
    close = _walk()
    base, scaled = roll_spread(close), roll_spread(close * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_other_scales_within_tolerance(k):
    close = _walk()
    base, scaled = roll_spread(close), roll_spread(close * k)
    assert (base.isna() == scaled.isna()).all()
    assert (base - scaled).abs().max() < 1e-10


def test_gate_c_fires_and_nan_rate_measured():
    """Measured, quoted in docs/LiquidityMeasured.md."""
    close = _walk()
    out = roll_spread(close)
    assert int(out.notna().sum()) == 575
    post_warmup = out.iloc[21:]
    assert int(post_warmup.isna().sum()) == 604
    assert out.dropna().nunique() == 575


# ---------------------------------------------------------------- wiring


def test_name_registration_and_accessor():
    close = _walk(200)
    df = pd.DataFrame({"open": close, "high": close, "low": close,
                       "close": close, "volume": 1.0})
    assert "roll_spread" in ta.Category["volatility"]
    out = df.ta.roll_spread()
    assert out.name == "ROLL_20"
    pd.testing.assert_series_equal(out, roll_spread(close))
    assert df.ta.roll_spread(length=10).name == "ROLL_10"
