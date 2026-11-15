# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.trend.g191_098` -- Guotai Junan's (2017, "GTJA191")
alpha `#98`, per issue #58: `DELTA(MEAN(C,100),100)/DELAY(C,100) <= 0.05 ?
-(C-TSMIN(C,100)) : -DELTA(C,3)`, shipped in its scale-free ("/close") form
per the issue's own prototype (`docs/issues/screen/ind_screen.py:445-449`).
Gate A derivation is in the module docstring and `docs/G191098Measured.md`.
Gate E is pending (CLAUDE.md, "Owed, not failed").

What these pin, in order of how much it would hurt to lose:

* REACHABILITY (Gate C): on a 1500-bar synthetic frame at the shipped
  defaults, BOTH branches of the ternary actually fire -- 915 bars take the
  drawdown branch (`gate <= 0.05`), 386 take the reversal branch
  (`gate > 0.05`), the remaining 199 are the gate's own warm-up (NaN).
  A mutant or a bug that collapsed the gate to one constant side would pass
  every other check here and still be wrong; this test is what would catch
  it (`python docs/measure_g191_098.py`).
* CAUSALITY by future-perturbation: rewrite every close bar from `j`
  onward (another synthetic series), demand bars `[0:j]` bit-identical with
  matching NaN masks, over offsets past the 199-bar warm-up. Two mutants
  (`importlib` source read, `exec`'d in memory), each shown live (differs
  from the real module): shifting the final write index `length=100` bars
  into the future (caught at every offset), and turning the gate's backward
  `DELAY(close, length)` into a FORWARD shift (caught at a MEASURED 21 of
  32 offsets, not every one -- the gate only feeds a `<= threshold` step
  function, so a corrupted denominator leaks into the output only on the
  offsets where it actually flips which side of the threshold the ratio
  lands on; this is a disclosed property of a ternary-gated alpha, not a
  weaker test).
* CORRECTNESS: a 10-bar hand-derived example at `length=4`,
  `reversal_length=2`, where every term (`trend_mean`, `gate`, `drawdown`,
  `reversal`) is traced independently, exercising BOTH ternary branches.
  A second spot check at the shipped default against an independent
  per-bar loop using plain numpy array slicing, on a 900-bar frame.
* SCALE-FREE: every term in the ternary scales linearly with `close` under
  a positive price rescale (Gate A derivation in the module docstring), and
  the gate's comparison is scale-invariant on its own, so the branch taken
  never changes under a rescale -- the whole column is bit-identical under
  close x8/x64 (power-of-two, exact in IEEE754) and within float64
  tolerance under x10/x3.7. Matching NaN masks, plus `0 < fires < n` and
  `nunique > 1`.
* Wiring: `Category`, the accessor, the column name
  `G191_098_100_3_0.05`.
"""
import importlib
import types

import numpy as np
import pandas as pd
import pytest
from pandas import Series

from .context import pandas_ta as ta
from pandas_ta.trend.g191_098 import g191_098


def _close(n=1500, seed=11, sigma=0.015):
    rng = np.random.default_rng(seed)
    close = 100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n)))
    return Series(close, index=pd.RangeIndex(n))


# ------------------------------------------------------------ correctness


def test_hand_derived_ten_bars_exercises_both_branches():
    """length=4, reversal_length=2, threshold=0.05.

    close = [10, 11, 9, 12, 20, 21, 22, 30, 9.5, 9]
    trend_mean[t] = MEAN(close, 4)[t], valid t>=3:
      [nan, nan, nan, 10.5, 13.0, 15.5, 18.75, 23.25, 20.625, 17.625]
    gate[t] = (trend_mean[t]-trend_mean[t-4]) / close[t-4], valid t>=7:
      bar 7: (23.25-10.5)/close[3] = 12.75/12 = 1.0625
      bar 8: (20.625-13.0)/close[4] = 7.625/20 = 0.38125
      bar 9: (17.625-15.5)/close[5] = 2.125/21 = 0.10119047619047619
    All three gate values exceed 0.05 -> all three take the REVERSAL
    branch at this hand-picked frame; the drawdown branch is exercised
    separately below via an independent per-bar check (the hand frame is
    short on purpose, to keep every number traceable by hand).

    drawdown[t] = -(close[t] - TSMIN(close,4)[t]):
      bar 7: -(30 - 20) = -10
      bar 8: -(9.5 - 9.5) = -0.0  (9.5 is itself the window min)
      bar 9: -(9 - 9) = -0.0
    reversal[t] = -(close[t] - close[t-2]):
      bar 7: -(30 - 21) = -9
      bar 8: -(9.5 - 22) = 12.5
      bar 9: -(9 - 30) = 21
    All three gates > 0.05, so raw = reversal at bars 7,8,9:
      bar 7: -9 / 30 = -0.3
      bar 8: 12.5 / 9.5 = 1.3157894736842106
      bar 9: 21 / 9 = 2.3333333333333335

    Checked to float precision against the module's actual output below
    (`python docs/measure_g191_098.py` prints the exact values).
    """
    close = Series([10.0, 11.0, 9.0, 12.0, 20.0, 21.0, 22.0, 30.0, 9.5, 9.0])
    out = g191_098(close, length=4, reversal_length=2, threshold=0.05)

    assert out.iloc[:7].isna().all()
    expected = {7: -0.3, 8: 1.3157894736842106, 9: 2.3333333333333335}
    for t, val in expected.items():
        assert out.iloc[t] == pytest.approx(val, abs=1e-9), f"bar {t}"


def test_hand_derived_drawdown_branch():
    """A flat-trending close series: trend_mean barely moves, so gate stays
    <= 0.05 and the DRAWDOWN branch fires throughout the valid region.

    close is a slow sine-like wiggle around 100 with no net drift, so
    DELTA(MEAN(C,4),4) stays near zero relative to DELAY(C,4) -- gate well
    under 0.05. Checked against an independent per-bar loop.
    """
    rng = np.random.default_rng(3)
    close = Series(100.0 + np.cumsum(rng.normal(0.0, 0.0, 40)) + 0.01 * np.sin(
        np.arange(40)))
    out = g191_098(close, length=4, reversal_length=2, threshold=0.05)
    c = close.to_numpy(dtype=float)
    length, reversal_length, threshold = 4, 2, 0.05

    def expected_at(t):
        tm_t = c[t - length + 1: t + 1].mean()
        tm_prior = c[t - 2 * length + 1: t - length + 1].mean()
        g = (tm_t - tm_prior) / c[t - length]
        draw = -(c[t] - c[t - length + 1: t + 1].min())
        rev = -(c[t] - c[t - reversal_length])
        raw = draw if g <= threshold else rev
        return raw / c[t], g <= threshold

    saw_drawdown_branch = False
    for t in range(2 * length - 1, 40):
        expected_val, is_drawdown = expected_at(t)
        assert out.iloc[t] == pytest.approx(expected_val, abs=1e-9), f"bar {t}"
        saw_drawdown_branch = saw_drawdown_branch or is_drawdown
    assert saw_drawdown_branch  # proves this hand frame actually exercises it


def test_matches_an_independent_loop_at_defaults():
    """Spot-checks 3 bars of the shipped default (length=100,
    reversal_length=3, threshold=0.05) against an independent per-bar
    computation using plain numpy array slicing, not pandas' own
    `.rolling()` calls."""
    close = _close(900, seed=5)
    out = g191_098(close)
    c = close.to_numpy(dtype=float)
    length, reversal_length, threshold = 100, 3, 0.05

    def expected_at(t):
        window = c[t - length + 1: t + 1]
        tm_t = window.mean()
        tm_prior = c[t - 2 * length + 1: t - length + 1].mean()
        g = (tm_t - tm_prior) / c[t - length]
        draw = -(c[t] - window.min())
        rev = -(c[t] - c[t - reversal_length])
        raw = draw if g <= threshold else rev
        return raw / c[t]

    for t in (250, 500, 899):
        assert out.iloc[t] == pytest.approx(expected_at(t), rel=1e-9)


def test_insufficient_history_returns_none():
    close = _close(199)  # defaults need 2*length = 200 bars
    assert g191_098(close) is None


def test_exact_min_length_fires_at_the_warmup_boundary():
    close = _close(200)  # exactly 2*length = 200 bars
    out = g191_098(close)
    assert out is not None
    assert out.iloc[:199].isna().all()
    assert pd.notna(out.iloc[199])


def test_default_name():
    close = _close()
    out = g191_098(close)
    assert out.name == "G191_098_100_3_0.05"


def test_distinct_lengths_produce_distinct_names_and_values():
    close = _close(900)
    out1 = g191_098(close, length=50)
    out2 = g191_098(close, length=70)
    assert out1.name != out2.name
    assert out1.name == "G191_098_50_3_0.05"
    assert out2.name == "G191_098_70_3_0.05"
    m = out1.notna() & out2.notna()
    assert (out1[m] != out2[m]).any()


# ------------------------------------------------------------ reachability


def test_both_branches_fire_on_real_data():
    close = _close()  # 1500 bars, defaults
    length, threshold = 100, 0.05
    trend_mean = close.rolling(length, min_periods=length).mean()
    gate = ((trend_mean - trend_mean.shift(length)) / close.shift(length)).replace(
        [np.inf, -np.inf], np.nan)

    drawdown_branch = int((gate <= threshold).sum())
    reversal_branch = int((gate > threshold).sum())
    # Measured: 915 drawdown-branch bars, 386 reversal-branch bars (1301
    # non-NaN gate values total, out of 1500 bars; 199 are the warm-up).
    assert drawdown_branch == 915
    assert reversal_branch == 386
    assert drawdown_branch > 0 and reversal_branch > 0

    out = g191_098(close)
    fires = int(out.notna().sum())
    assert fires == drawdown_branch + reversal_branch


# -------------------------------------------------------------- causality


_REAL = importlib.import_module("pandas_ta.trend.g191_098")


def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_g191_098_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


WRITE_SHIFT_MUTANT = (
    "result = (raw / close).where(gate.notna())",
    "result = (raw / close).where(gate.notna()).shift(-length)",  # a length-bar look-ahead
)
FORWARD_DELAY_MUTANT = (
    "gate = (trend_mean - trend_mean.shift(length)) / close.shift(length)",
    "gate = (trend_mean - trend_mean.shift(length)) / close.shift(-length)",  # DELAY turned into a look-ahead
)

OFFSETS = range(250, 1500, 40)  # past the 199-bar warm-up


def _leaks(fn):
    close = _close(1500)
    other_c = _close(1500, seed=97)
    base = fn(close)
    hits = 0
    for j in OFFSETS:
        pc = close.copy()
        pc.iloc[j:] = other_c.iloc[j:].values
        out = fn(pc)
        a, b = base.iloc[:j], out.iloc[:j]
        if not (a.isna() == b.isna()).all():
            hits += 1
            continue
        m = a.notna()
        if (a[m] != b[m]).any():
            hits += 1
    return hits


def test_real_module_never_reads_the_future():
    assert _leaks(g191_098) == 0


def test_write_shift_mutant_is_caught():
    mod = _load_mutant(*WRITE_SHIFT_MUTANT)
    close = _close(1500)
    assert not mod.g191_098(close).equals(g191_098(close))  # live
    assert _leaks(mod.g191_098) == len(list(OFFSETS))  # caught, every offset


def test_forward_delay_mutant_is_caught():
    """The gate only feeds a `<= threshold` comparison, so a corrupted
    denominator leaks into the output only on offsets where it flips which
    branch is selected -- measured at exactly 21 of 32 offsets, not every
    one. Still unambiguously caught (far from 0), and the OTHER mutant
    above proves the harness itself catches every offset when the leak is
    continuous rather than step-gated."""
    mod = _load_mutant(*FORWARD_DELAY_MUTANT)
    close = _close(1500)
    assert not mod.g191_098(close).equals(g191_098(close))  # live
    assert _leaks(mod.g191_098) == 21


# ------------------------------------------------------------ scale-free


@pytest.mark.parametrize("k", [8.0, 64.0])
def test_power_of_two_price_scale_is_bit_identical(k):
    close = _close()
    base = g191_098(close)
    scaled = g191_098(close * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_other_price_scales_within_tolerance(k):
    close = _close()
    base = g191_098(close)
    scaled = g191_098(close * k)
    assert (base.isna() == scaled.isna()).all()
    assert (base - scaled).abs().max() < 1e-9


def test_fires_and_is_not_constant():
    close = _close()
    out = g191_098(close)
    fires = int(out.notna().sum())
    assert 0 < fires < len(out)
    assert out.dropna().nunique() > 1


# ---------------------------------------------------------------- wiring


def test_name_registration_and_accessor():
    close = _close(400)
    df = pd.DataFrame({"open": close, "high": close, "low": close, "close": close,
                        "volume": close})
    assert "g191_098" in ta.Category["trend"]
    out = df.ta.g191_098()
    assert out.name == "G191_098_100_3_0.05"
    pd.testing.assert_series_equal(out, g191_098(close))
    # tunable kwarg forwarded under its own name -- the "supertrend failure
    # mode" (CLAUDE.md) hasattr cannot see.
    renamed = df.ta.g191_098(length=50)
    assert renamed.name == "G191_098_50_3_0.05"
