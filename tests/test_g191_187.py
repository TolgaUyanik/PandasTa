# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.momentum.g191_187` -- Guotai Junan's (2017,
"GTJA191") alpha `#187`, per issue #65: `SUM(O<=O1 ? 0 : MAX(H-O, O-O1),
20)`, scale-free via `/close`, matching the issue's own prototype
(`docs/issues/screen/ind_screen.py:554-557`). Gate A derivation is in the
module docstring and `docs/G191187Measured.md`. Gate E is pending
(CLAUDE.md, "Owed, not failed").

What these tests pin, in order of how much it would hurt to lose:

* CAUSALITY by future-perturbation: rewrite every OHLC bar from `j`
  onward (another synthetic frame), demand bars `[0:j]` bit-identical with
  matching NaN masks, over offsets past the 21-bar warm-up. Two mutants
  (`importlib` source read, `exec`'d in memory), each shown live (differs
  from the real module) then caught at every offset: shifting the final
  write index `length=20` bars into the future, and flipping the backward
  `DELAY` (`open_.shift(1)`, i.e. `O1`) into a FORWARD shift
  (`open_.shift(-1)`) -- turning the previous-open reference into a
  look-ahead at the NEXT open. Unlike the mirror alpha `#93`
  (`g191_093`), `MAX(H-O, O-O1)` here does NOT collapse to one term
  (measured: `H-O` wins 149, `O-O1` wins 604, of 753 up-branch bars on a
  1,500-bar frame -- `docs/measure_g191_187.py`), so the ordinary random
  future-perturbation sweep catches the forward-delay mutant directly, at
  every one of its 34 offsets -- no dedicated deterministic construction
  needed (measured, not assumed).
* CORRECTNESS: a hand-derived example at `length=3`, checked bar by bar,
  plus a spot check at the shipped default against an independent per-bar
  computation using plain numpy array slicing, not the module's own
  `.rolling()` calls.
* WARM-UP SUBTLETY: bar 0 has no `O1`, so its up/down status is undefined,
  not merely "not an up day". The module masks it to `NaN` explicitly
  (matching the prototype's own `.where(o1.notna())`) rather than relying
  on `np.maximum`'s NaN-propagation through `up_move` to get the same
  answer by accident -- on the CURRENT arithmetic both read `NaN` at bar 0
  (measured, `python docs/measure_g191_187.py`), but the explicit mask
  survives a future rewrite of `up_move` that stops propagating `NaN` the
  same way.
* SCALE-FREE: bit-identical under OHLC x8/x64 (power-of-two, exact in
  IEEE754), within float64 tolerance under x10/x3.7. Matching NaN masks,
  plus `0 < fires < n` and `nunique > 1`.
* Wiring: `Category`, the accessor, the column name `G191_187_20`.
"""
import importlib
import types

import numpy as np
import pandas as pd
import pytest
from pandas import Series

from .context import pandas_ta as ta
from pandas_ta.momentum.g191_187 import g191_187


def _ohlc(n=1500, seed=11, sigma=0.015):
    rng = np.random.default_rng(seed)
    close = 100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n)))
    rng2 = np.random.default_rng(seed + 1)
    spread = np.abs(rng2.normal(0.0, 0.01, n)) * close
    high = close + spread * rng2.uniform(0.2, 1.0, n)
    low = close - spread * rng2.uniform(0.2, 1.0, n)
    open_ = low + (high - low) * rng2.uniform(0.0, 1.0, n)
    idx = pd.RangeIndex(n)
    return Series(open_, index=idx), Series(high, index=idx), Series(close, index=idx)


# ------------------------------------------------------------ correctness


def test_hand_derived_seven_bars():
    """length=3.

    open  = [10, 12,  9, 15, 11, 20, 13]
    high  = [11, 13, 10, 16, 12, 30, 14]
    O1    = [nan, 10, 12,  9, 15, 11, 20]
    O<=O1?  [nan, False, True, False, True, False, True]
    H-O   = [ 1,  1,  1,  1,  1, 10,  1]
    O-O1  = [nan,  2, -3,  6, -4,  9, -7]
    up_move = MAX(H-O, O-O1) = [nan, 2, 1, 6, 1, 10, 1]
    contribution = O<=O1 ? 0 : up_move, bar0 masked NaN:
                  [nan, 2, 0, 6, 0, 10, 0]
    DTM (rolling sum, length=3):
        t=0,1: NaN (window touches the masked bar 0)
        t=2: sum([nan,2,0]) -> NaN (still touches bar 0)
        t=3: sum([2,0,6]) = 8
        t=4: sum([0,6,0]) = 6
        t=5: sum([6,0,10]) = 16
        t=6: sum([0,10,0]) = 10
    close = [100, 101, 102, 103, 104, 105, 106] (arbitrary, close not used above)
    result[3] = 8/103, result[4] = 6/104, result[5] = 16/105, result[6] = 10/106
    """
    open_ = Series([10.0, 12.0, 9.0, 15.0, 11.0, 20.0, 13.0])
    high = Series([11.0, 13.0, 10.0, 16.0, 12.0, 30.0, 14.0])
    close = Series([100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0])

    out = g191_187(open_, high, close, length=3)

    assert out.iloc[:3].isna().all()
    assert out.iloc[3] == pytest.approx(8.0 / 103.0, abs=1e-12)
    assert out.iloc[4] == pytest.approx(6.0 / 104.0, abs=1e-12)
    assert out.iloc[5] == pytest.approx(16.0 / 105.0, abs=1e-12)
    assert out.iloc[6] == pytest.approx(10.0 / 106.0, abs=1e-12)


def test_matches_an_independent_loop_at_defaults():
    """Spot-checks 3 bars of the shipped default (length=20) against an
    independent per-bar computation using plain numpy array slicing, not
    pandas' own `.rolling()` calls."""
    open_, high, close = _ohlc(900, seed=5)
    out = g191_187(open_, high, close)
    o, h, c = (s.to_numpy(dtype=float) for s in (open_, high, close))
    length = 20

    def expected_at(t):
        idx = np.arange(t - length + 1, t + 1)  # all >= 1 since t >= length
        o1 = o[idx - 1]
        up_move = np.maximum(h[idx] - o[idx], o[idx] - o1)
        contribution = np.where(o[idx] <= o1, 0.0, up_move)
        return np.sum(contribution) / c[t]

    for t in (300, 600, 899):
        assert out.iloc[t] == pytest.approx(expected_at(t), rel=1e-9)


def test_insufficient_history_returns_none():
    open_, high, close = _ohlc(20)  # defaults need length + 1 = 21 bars
    assert g191_187(open_, high, close) is None


def test_exact_min_length_fires_at_the_warmup_boundary():
    open_, high, close = _ohlc(21)  # exactly length + 1 = 21 bars
    out = g191_187(open_, high, close)
    assert out is not None
    assert out.iloc[:20].isna().all()
    assert pd.notna(out.iloc[20])


def test_default_name():
    open_, high, close = _ohlc()
    out = g191_187(open_, high, close)
    assert out.name == "G191_187_20"


def test_distinct_lengths_produce_distinct_names_and_values():
    open_, high, close = _ohlc(400)
    out1 = g191_187(open_, high, close, length=10)
    out2 = g191_187(open_, high, close, length=15)
    assert out1.name != out2.name
    assert out1.name == "G191_187_10"
    assert out2.name == "G191_187_15"
    m = out1.notna() & out2.notna()
    assert (out1[m] != out2[m]).any()


# -------------------------------------------------------------- causality


_REAL = importlib.import_module("pandas_ta.momentum.g191_187")


def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_g191_187_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


WRITE_SHIFT_MUTANT = (
    "result = dtm / close",
    "result = (dtm / close).shift(-length)",  # a length-bar look-ahead
)
FORWARD_DELAY_MUTANT = (
    "prior_open = open_.shift(1)",
    "prior_open = open_.shift(-1)",  # O1 turned into a look-ahead at the NEXT open
)

OFFSETS = range(150, 1500, 40)  # past the 21-bar warm-up


def _leaks(fn):
    open_, high, close = _ohlc(1500)
    o_open, o_high, o_close = _ohlc(1500, seed=97)
    base = fn(open_, high, close)
    hits = 0
    for j in OFFSETS:
        po, ph, pc = open_.copy(), high.copy(), close.copy()
        po.iloc[j:] = o_open.iloc[j:].values
        ph.iloc[j:] = o_high.iloc[j:].values
        pc.iloc[j:] = o_close.iloc[j:].values
        out = fn(po, ph, pc)
        a, b = base.iloc[:j], out.iloc[:j]
        if not (a.isna() == b.isna()).all():
            hits += 1
            continue
        m = a.notna()
        if (a[m] != b[m]).any():
            hits += 1
    return hits


def test_real_module_never_reads_the_future():
    assert _leaks(g191_187) == 0


def test_write_shift_mutant_is_caught():
    mod = _load_mutant(*WRITE_SHIFT_MUTANT)
    open_, high, close = _ohlc(1500)
    assert not mod.g191_187(open_, high, close).equals(g191_187(open_, high, close))  # live
    assert _leaks(mod.g191_187) == len(list(OFFSETS))  # caught, every offset


def test_forward_delay_mutant_is_caught():
    """Unlike `g191_093`'s mirrored mutant, `MAX(H-O, O-O1)` here never
    collapses to a single term (measured: `docs/measure_g191_187.py`
    reports `H-O` winning 149 and `O-O1` winning 604 of 753 up-branch
    bars on a 1,500-bar frame, zero ties) -- the DELAY direction changes
    the `O-O1` term's own magnitude directly, so the ordinary random
    future-perturbation sweep catches the leak without a dedicated
    deterministic construction."""
    mod = _load_mutant(*FORWARD_DELAY_MUTANT)
    open_, high, close = _ohlc(1500)
    assert not mod.g191_187(open_, high, close).equals(g191_187(open_, high, close))  # live
    assert _leaks(mod.g191_187) == len(list(OFFSETS))  # caught, every offset


# ------------------------------------------------------------ reachability


def test_fires_on_a_non_trivial_fraction():
    open_, high, close = _ohlc()  # 1500 bars, defaults
    out = g191_187(open_, high, close)
    fires = int(out.notna().sum())
    assert fires > 1400


def test_fires_and_is_not_constant():
    open_, high, close = _ohlc()
    out = g191_187(open_, high, close)
    fires = int(out.notna().sum())
    assert 0 < fires < len(out)
    assert out.dropna().nunique() > 100


# ------------------------------------------------------------ scale-free


@pytest.mark.parametrize("k", [8.0, 64.0])
def test_price_scale_is_bit_identical(k):
    open_, high, close = _ohlc()
    base = g191_187(open_, high, close)
    scaled = g191_187(open_ * k, high * k, close * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_price_scale_within_tolerance(k):
    open_, high, close = _ohlc()
    base = g191_187(open_, high, close)
    scaled = g191_187(open_ * k, high * k, close * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] - scaled[m]).abs().max() < 1e-9


# ---------------------------------------------------------------- wiring


def test_name_registration_and_accessor():
    open_, high, close = _ohlc(400)
    df = pd.DataFrame({"open": open_, "high": high, "low": close, "close": close,
                        "volume": 1.0})
    assert "g191_187" in ta.Category["momentum"]
    out = df.ta.g191_187()
    assert out.name == "G191_187_20"
    pd.testing.assert_series_equal(out, g191_187(open_, high, close))
    # tunable kwarg forwarded under its own name -- the "supertrend
    # failure mode" (CLAUDE.md) hasattr cannot see.
    renamed = df.ta.g191_187(length=10)
    assert renamed.name == "G191_187_10"
