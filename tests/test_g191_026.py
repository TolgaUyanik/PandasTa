# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.statistics.g191_026` -- Guotai Junan's (2017,
"GTJA191") alpha `#26`, per issue #56: `(SUM(C,7)/7 - C) + CORR(VWAP,
DELAY(C,5), 230)`, converted to its scale-free form per the issue's own
parenthetical ("first term /close; VWAP -> (H+L+C)/3") and the issue's own
prototype (`docs/issues/screen/ind_screen.py:339`):
`(MEAN(C,7) - C)/C + CORR((H+L+C)/3, DELAY(C,5), 230)`. Gate A derivation is
in the module docstring and `docs/G191026Measured.md`. Gate E is pending
(CLAUDE.md, "Owed, not failed").

What these pin, in order of how much it would hurt to lose:

* CAUSALITY by future-perturbation: rewrite every OHLC bar from `j` onward
  (another synthetic frame), demand bars `[0:j]` bit-identical with
  matching NaN masks, over offsets past the 234-bar warm-up. Two mutants
  (`importlib` source read, `exec`'d in memory), each shown live (differs
  from the real module) then caught at every offset: shifting the final
  write index `corr_length=230` bars into the future, and flipping the
  backward `DELAY` (`close.shift(lag)`) into a FORWARD shift
  (`close.shift(-lag)`) -- turning the lag term itself into a look-ahead
  (`python docs/measure_g191_026.py`).
* CORRECTNESS: a 6-bar hand-derived example at `mean_length=3,
  corr_length=2, lag=1`, where high/low are built as `close +- 1` so the
  typical price collapses to `close` exactly and every rolling correlation
  is a 2-point Pearson correlation (exactly +-1 unless the two series tie),
  checked against an independent per-bar computation written directly in
  the test (not the module's own `.rolling().corr()` call). A second spot
  check at the shipped default against an independent per-bar loop using
  plain numpy (`np.mean` over explicit slices, `np.corrcoef`), on a 900-bar
  frame.
* SCALE-FREE: Pearson correlation is exactly invariant to a positive
  rescale of either input (the scale cancels between covariance and
  standard deviation), and the mean-gap term's own `/close` cancels a
  positive price rescale algebraically too -- so the whole column is
  bit-identical under close x8/x64 (power-of-two, exact in IEEE754), and
  within float64 tolerance under x10/x3.7. Matching NaN masks, plus
  `0 < fires < n` and `nunique > 1`.
* Wiring: `Category`, the accessor, the column name `G191_026_7_230_5`.
"""
import importlib
import types

import numpy as np
import pandas as pd
import pytest
from pandas import Series

from .context import pandas_ta as ta
from pandas_ta.statistics.g191_026 import g191_026


def _ohlc(n=1500, seed=11, sigma=0.015):
    rng = np.random.default_rng(seed)
    close = 100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n)))
    rng2 = np.random.default_rng(seed + 1)
    spread = np.abs(rng2.normal(0.0, 0.01, n)) * close
    high = close + spread * rng2.uniform(0.2, 1.0, n)
    low = close - spread * rng2.uniform(0.2, 1.0, n)
    idx = pd.RangeIndex(n)
    return (Series(high, index=idx), Series(low, index=idx), Series(close, index=idx))


# ------------------------------------------------------------ correctness


def test_hand_derived_six_bars():
    """mean_length=3, corr_length=2, lag=1. high = close+1, low = close-1,
    so tp = (high+low+close)/3 = close exactly, collapsing the correlation
    term to CORR(close, DELAY(close,1), 2) -- a 2-point Pearson correlation,
    exactly +-1 unless the two windows tie.

    close = [10, 20, 30, 40, 22, 5]
    gap_term[t] = (MEAN(close,3)[t]-close[t])/close[t], valid t>=2:
      gap_term[2] = (20-30)/30 = -0.333333..., gap_term[3] = (30-40)/40 = -0.25,
      gap_term[4] = (30.6667-22)/22 = 0.393939..., gap_term[5] = (22.3333-5)/5 = 3.466667...
    lagged_close[t] = close[t-1], valid t>=1: [nan,10,20,30,40,22]
    corr_term[t] = CORR(tp, lagged_close, 2), valid t>=2:
      t=2: corr([20,30],[10,20]) = +1 (both up)
      t=3: corr([30,40],[20,30]) = +1 (both up)
      t=4: corr([40,22],[30,40]) = -1 (tp down, lag up)
      t=5: corr([22,5],[40,22]) = +1 (both down)
    result[t] = corr_term[t] + gap_term[t]:
      result[2] = 1 - 0.333333... = 0.666666666666...
      result[3] = 1 - 0.25 = 0.75
      result[4] = -1 + 0.393939393939394 = -0.606060606060606
      result[5] = 1 + 3.466666666666667 = 4.466666666666667

    Checked to float precision against the module's actual output below
    (`python docs/measure_g191_026.py` prints the exact values).
    """
    close = Series([10.0, 20.0, 30.0, 40.0, 22.0, 5.0])
    high = close + 1.0
    low = close - 1.0

    out = g191_026(high, low, close, mean_length=3, corr_length=2, lag=1)

    assert out.iloc[:2].isna().all()
    expected = {
        2: 0.6666666666666667,
        3: 0.75,
        4: -0.606060606060606,
        5: 4.466666666666667,
    }
    for t, val in expected.items():
        assert out.iloc[t] == pytest.approx(val, abs=1e-9), f"bar {t}"


def test_matches_an_independent_loop_at_defaults():
    """Spot-checks 3 bars of the shipped defaults (mean_length=7,
    corr_length=230, lag=5) against an independent per-bar computation
    using plain numpy (`np.mean` over explicit slices, `np.corrcoef`), not
    pandas' `.rolling().mean()` / `.rolling().corr()`."""
    high, low, close = _ohlc(900, seed=5)
    out = g191_026(high, low, close)
    h, l, c = high.to_numpy(dtype=float), low.to_numpy(dtype=float), close.to_numpy(dtype=float)
    tp = (h + l + c) / 3.0
    mean_length, corr_length, lag = 7, 230, 5

    def expected_at(t):
        gap = (np.mean(c[t - mean_length + 1:t + 1]) - c[t]) / c[t]
        tp_window = tp[t - corr_length + 1:t + 1]
        lag_window = c[t - corr_length + 1 - lag:t + 1 - lag]
        corr = np.corrcoef(tp_window, lag_window)[0, 1]
        return gap + corr

    for t in (300, 600, 899):
        assert out.iloc[t] == pytest.approx(expected_at(t), rel=1e-9)


def test_insufficient_history_returns_none():
    high, low, close = _ohlc(234)  # defaults need lag + corr_length = 5 + 230 = 235 bars
    assert g191_026(high, low, close) is None


def test_exact_min_length_fires_at_the_warmup_boundary():
    high, low, close = _ohlc(235)  # exactly lag + corr_length = 235 bars
    out = g191_026(high, low, close)
    assert out is not None
    assert out.iloc[:234].isna().all()
    assert pd.notna(out.iloc[234])


def test_mean_length_branch_dominates_the_warmup_when_larger():
    """gap_term and corr_term are computed in PARALLEL, not chained, so the
    true warm-up is `max(mean_length, lag + corr_length)`, not just
    `lag + corr_length` -- the second branch alone would let a frame too
    short for a large `mean_length` through, silently returning an
    all-NaN Series instead of `None` (`close.rolling(mean_length).mean()`
    on a frame shorter than `mean_length` is all-NaN for every row)."""
    high, low, close = _ohlc(299)  # below max(300, 5+230=235) = 300
    assert g191_026(high, low, close, mean_length=300, corr_length=230, lag=5) is None

    high, low, close = _ohlc(300)  # exactly max(300, 235) = 300
    out = g191_026(high, low, close, mean_length=300, corr_length=230, lag=5)
    assert out is not None
    assert out.iloc[:299].isna().all()
    assert pd.notna(out.iloc[299])


def test_default_name():
    high, low, close = _ohlc()
    out = g191_026(high, low, close)
    assert out.name == "G191_026_7_230_5"


def test_distinct_lengths_produce_distinct_names_and_values():
    high, low, close = _ohlc(400)
    out1 = g191_026(high, low, close, mean_length=5, corr_length=50, lag=2)
    out2 = g191_026(high, low, close, mean_length=10, corr_length=80, lag=3)
    assert out1.name != out2.name
    assert out1.name == "G191_026_5_50_2"
    assert out2.name == "G191_026_10_80_3"
    m = out1.notna() & out2.notna()
    assert (out1[m] != out2[m]).any()


# -------------------------------------------------------------- causality


_REAL = importlib.import_module("pandas_ta.statistics.g191_026")


def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_g191_026_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


WRITE_SHIFT_MUTANT = (
    "result = (gap_term + corr_term).replace([np.inf, -np.inf], np.nan)",
    "result = (gap_term + corr_term).replace([np.inf, -np.inf], np.nan).shift(-corr_length)",  # a corr_length-bar look-ahead
)
FORWARD_DELAY_MUTANT = (
    "lagged_close = close.shift(lag)",
    "lagged_close = close.shift(-lag)",  # DELAY turned into a look-ahead
)

OFFSETS = range(300, 1500, 40)  # past the 234-bar warm-up


def _leaks(fn):
    high, low, close = _ohlc(1500)
    other_h, other_l, other_c = _ohlc(1500, seed=97)
    base = fn(high, low, close)
    hits = 0
    for j in OFFSETS:
        ph, pl, pc = high.copy(), low.copy(), close.copy()
        ph.iloc[j:] = other_h.iloc[j:].values
        pl.iloc[j:] = other_l.iloc[j:].values
        pc.iloc[j:] = other_c.iloc[j:].values
        out = fn(ph, pl, pc)
        a, b = base.iloc[:j], out.iloc[:j]
        if not (a.isna() == b.isna()).all():
            hits += 1
            continue
        m = a.notna()
        if (a[m] != b[m]).any():
            hits += 1
    return hits


def test_real_module_never_reads_the_future():
    assert _leaks(g191_026) == 0


def test_write_shift_mutant_is_caught():
    mod = _load_mutant(*WRITE_SHIFT_MUTANT)
    high, low, close = _ohlc(1500)
    assert not mod.g191_026(high, low, close).equals(g191_026(high, low, close))  # live
    assert _leaks(mod.g191_026) == len(list(OFFSETS))  # caught, every offset


def test_forward_delay_mutant_is_caught():
    mod = _load_mutant(*FORWARD_DELAY_MUTANT)
    high, low, close = _ohlc(1500)
    assert not mod.g191_026(high, low, close).equals(g191_026(high, low, close))  # live
    assert _leaks(mod.g191_026) == len(list(OFFSETS))  # caught, every offset


# ------------------------------------------------------------ scale-free


@pytest.mark.parametrize("k", [8.0, 64.0])
def test_power_of_two_price_scale_is_bit_identical(k):
    high, low, close = _ohlc()
    base = g191_026(high, low, close)
    scaled = g191_026(high * k, low * k, close * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_other_price_scales_within_tolerance(k):
    high, low, close = _ohlc()
    base = g191_026(high, low, close)
    scaled = g191_026(high * k, low * k, close * k)
    assert (base.isna() == scaled.isna()).all()
    assert (base - scaled).abs().max() < 1e-9


def test_fires_and_is_not_constant():
    high, low, close = _ohlc()
    out = g191_026(high, low, close)
    fires = int(out.notna().sum())
    assert 0 < fires < len(out)
    assert out.dropna().nunique() > 1


# ---------------------------------------------------------------- wiring


def test_name_registration_and_accessor():
    high, low, close = _ohlc(400)
    df = pd.DataFrame({"open": close, "high": high, "low": low, "close": close,
                        "volume": close})
    assert "g191_026" in ta.Category["statistics"]
    out = df.ta.g191_026()
    assert out.name == "G191_026_7_230_5"
    pd.testing.assert_series_equal(out, g191_026(high, low, close))
    # both tunable kwargs forwarded under their own names in one call --
    # the "supertrend failure mode" (CLAUDE.md) hasattr cannot see.
    renamed = df.ta.g191_026(mean_length=5, corr_length=50, lag=2)
    assert renamed.name == "G191_026_5_50_2"
