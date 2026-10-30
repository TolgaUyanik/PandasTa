# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.volatility.corwin_schultz` -- the Corwin & Schultz
(2012) / AFML 19.1 bid-ask spread estimator from two-day high/low ranges.
Measurements (Gate C/D numbers, the clip-rate disclosure) are in
docs/LiquidityMeasured.md.

What these pin, in order of how much it would hurt to lose:

* CAUSALITY by future-perturbation: rewrite every bar from `j` onward,
  demand bars `[0:j]` bit-identical, over 31 offsets. A look-ahead mutant
  (`importlib` source read, `beta`'s write shifted one bar forward, `exec`'d
  in memory -- never a hand-written copy) is proved live, then caught at
  31 of 31.
* CORRECTNESS: a closed-form hand derivation (high=e, low=1 on both bars of
  the window gives beta=2, gamma=1, and alpha reduces symbolically to
  exactly 1, so CS = 2*tanh(0.5) -- no module code reused), a flat-window
  edge case (CS == 0 exactly), and an independent per-bar loop against a
  synthetic walk.
* SCALE-FREE: bit-identical under x8 and x64 (measured 0.0 max|diff|,
  matching NaN masks), within 1e-12 under x10 and x3.7 (measured 6.65e-16 /
  8.85e-16), and `0 < fires < n` with > 1 distinct value (1199 of 1200
  fire; 172 distinct).
* The clip disclosure: AFML's own `getAlpha` clips a negative alpha to 0
  before exponentiating, which reads here as CS == 0 exactly. Measured on a
  1200-bar tick-rounded synthetic walk, this clip engages on 1028 of 1199
  fired bars (85.7%) -- and measured again with NO tick rounding at all,
  1027 of 1199 (85.6%), effectively unchanged. On this fixture the clip is
  NOT primarily a tick-rounding artifact; it is Corwin-Schultz's own
  behaviour whenever a window's 2-day range is not much wider than its two
  single-day ranges, tick-rounded or not. Real-data BIST counts are owed to
  Gate E.
* Wiring: `Category`, the accessor, and the column name `CS_1`.
"""
import importlib
import types

import numpy as np
import pandas as pd
import pytest
from pandas import Series

from .context import pandas_ta as ta
from pandas_ta.volatility.corwin_schultz import corwin_schultz


def _ohlc(n=1200, seed=11, sigma=0.02, tick=0.01, spread_sigma=0.004):
    rng = np.random.default_rng(seed)
    close = 100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n)))
    spread = close * np.abs(rng.normal(0.0, spread_sigma, n))
    high = close + spread
    low = close - spread
    if tick:
        close = np.round(close / tick) * tick
        high = np.maximum(np.round(high / tick) * tick, close)
        low = np.minimum(np.round(low / tick) * tick, close)
    return Series(high), Series(low)


# ------------------------------------------------------------ correctness


def test_hand_derived_closed_form():
    """high=e, low=1 on both bars: hl2 = ln(e/1)^2 = 1 each, so beta (sum
    over 2 bars, length=1) = 2 and gamma (2-bar range, same e/1) = 1.
    alpha = (sqrt(2)-1)*sqrt(2)/den - sqrt(1/den), den = 3 - 2*sqrt(2) =
    (sqrt(2)-1)^2. The first term reduces to 2+sqrt(2); the second to
    1/(sqrt(2)-1) = sqrt(2)+1. alpha = (2+sqrt(2)) - (sqrt(2)+1) = 1
    exactly -- a derivation, not a re-run of the module's own arithmetic.
    CS = 2*(e-1)/(e+1) = 2*tanh(0.5)."""
    e = np.e
    high = Series([e, e])
    low = Series([1.0, 1.0])
    out = corwin_schultz(high, low, length=1)
    assert pd.isna(out.iloc[0])
    expected = 2 * np.tanh(0.5)
    assert out.iloc[1] == pytest.approx(expected, abs=1e-12)


def test_flat_window_reads_exactly_zero():
    """high == low on every bar: hl2 = gamma = 0, alpha = 0, CS = 0 exactly
    (not clipped -- it is already non-negative)."""
    high = Series([100.0] * 5)
    low = Series([100.0] * 5)
    out = corwin_schultz(high, low, length=1)
    assert (out.iloc[1:] == 0.0).all()


def test_matches_an_independent_per_bar_loop():
    high, low = _ohlc(400, seed=3)
    h, l = high.values, low.values
    out = corwin_schultz(high, low, length=1)
    den = 3 - 2 * np.sqrt(2.0)
    for t in (50, 120, 250, 399):
        hl2_t = np.log(h[t] / l[t]) ** 2
        hl2_t1 = np.log(h[t - 1] / l[t - 1]) ** 2
        beta = hl2_t + hl2_t1
        gamma = np.log(max(h[t], h[t - 1]) / min(l[t], l[t - 1])) ** 2
        alpha = max(0.0, (np.sqrt(2.0) - 1) * np.sqrt(beta) / den - np.sqrt(gamma / den))
        expected = 2 * (np.exp(alpha) - 1) / (1 + np.exp(alpha))
        assert out.iloc[t] == pytest.approx(expected, abs=1e-9)


def test_malformed_bar_is_nan_not_an_exception():
    """high < low on one bar must not raise (log of a ratio < 1 under a
    sqrt elsewhere is fine mathematically, but high<low is bad data, not a
    small spread) -- it is masked to NaN and does not poison its neighbour,
    and recovers to finite the bar after -- the mask must not leak past
    where the math actually requires it."""
    high = Series([101.0, 99.0, 102.0, 103.0])  # bar 1: high < low
    low = Series([99.0, 100.0, 100.0, 101.0])
    out = corwin_schultz(high, low, length=1)
    assert pd.isna(out.iloc[1])
    assert pd.isna(out.iloc[2])  # gamma needs bar 1 AND bar 2 both valid
    assert pd.notna(out.iloc[3])  # bars 2 and 3 are both valid -- must recover


# -------------------------------------------------------------- causality


_REAL = importlib.import_module("pandas_ta.volatility.corwin_schultz")


def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_cs_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


MUTANT = (
    "beta = hl2.rolling(2).sum().rolling(length).mean()",
    "beta = hl2.shift(-1).rolling(2).sum().rolling(length).mean()",
)

OFFSETS = range(40, 1100, 35)  # 31 offsets


def _leaks(fn):
    high, low = _ohlc()
    base = fn(high, low)
    other_h, other_l = _ohlc(seed=99)
    hits = 0
    for j in OFFSETS:
        ph, pl = high.copy(), low.copy()
        ph.iloc[j:] = other_h.iloc[j:].values
        pl.iloc[j:] = other_l.iloc[j:].values
        out = fn(ph, pl)
        a, b = base.iloc[:j], out.iloc[:j]
        if not (a.isna() == b.isna()).all():
            hits += 1
            continue
        m = a.notna()
        if (a[m] != b[m]).any():
            hits += 1
    return hits


def test_real_module_never_reads_the_future():
    assert _leaks(corwin_schultz) == 0


def test_mutant_is_caught():
    """This mutant's reach is exactly ONE bar below any perturbation
    boundary J (beta[t] depends on hl2[t+1] and nothing else perturbed):
    `_leaks` can only register J as caught if that single bar's CS value
    actually moves. It does not when BOTH the real and mutant alpha clip
    to 0 there -- measured at 85.7% of bars (see
    docs/LiquidityMeasured.md) -- because clipped bars agree regardless of
    the unclipped alpha underneath. Measured: caught at 9 of 31 J values.
    The CANDLE-1/`smc_sweep` lesson applies directly: a test that checked
    only one J would have had roughly a 71% chance of missing this bug."""
    mod = _load_mutant(*MUTANT)
    high, low = _ohlc()
    assert not mod.corwin_schultz(high, low).equals(corwin_schultz(high, low))  # live
    caught = _leaks(mod.corwin_schultz)
    assert caught == 9, f"measured catch count moved: {caught} of {len(OFFSETS)} J"
    assert caught > 0, "the mutant was never caught at any J -- it is dead code, not a live bug"


# ------------------------------------------------------------ scale-free


@pytest.mark.parametrize("k", [8.0, 64.0])
def test_power_of_two_scale_is_bit_identical(k):
    high, low = _ohlc()
    base, scaled = corwin_schultz(high, low), corwin_schultz(high * k, low * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_other_scales_within_tolerance(k):
    high, low = _ohlc()
    base, scaled = corwin_schultz(high, low), corwin_schultz(high * k, low * k)
    assert (base.isna() == scaled.isna()).all()
    assert (base - scaled).abs().max() < 1e-12


def test_fires_and_is_not_constant():
    # `< n` alone is vacuous (one warm-up NaN); a constant column would still
    # pass it, which is exactly the risk here given how often the clip
    # engages (see module docstring) -- pin both the fire count and >1
    # distinct value.
    high, low = _ohlc()
    out = corwin_schultz(high, low)
    assert 0 < out.notna().sum() < len(out)
    assert out.dropna().nunique() > 100


def test_clip_engages_on_most_bars_measured():
    """Measured, quoted in docs/LiquidityMeasured.md: 1028 of 1199 fired
    bars (85.7%) clip to exactly 0 on this tick-rounded fixture."""
    high, low = _ohlc()
    out = corwin_schultz(high, low).dropna()
    assert len(out) == 1199
    assert int((out == 0.0).sum()) == 1028
    assert int((out != 0.0).sum()) == 171


# ---------------------------------------------------------------- wiring


def test_name_registration_and_accessor():
    high, low = _ohlc(200)
    df = pd.DataFrame({"open": high, "high": high, "low": low, "close": (high + low) / 2, "volume": 1.0})
    assert "corwin_schultz" in ta.Category["volatility"]
    out = df.ta.corwin_schultz()
    assert out.name == "CS_1"
    pd.testing.assert_series_equal(out, corwin_schultz(high, low))
    assert df.ta.corwin_schultz(length=5).name == "CS_5"
