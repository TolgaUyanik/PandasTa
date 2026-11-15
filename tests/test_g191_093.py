# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.momentum.g191_093` -- Guotai Junan's (2017,
"GTJA191") alpha `#93`, per issue #62: `SUM(O>=O1 ? 0 : MAX(O-L, O-O1),
20)`, scale-free via `/close`, matching the issue's own prototype
(`docs/issues/screen/ind_screen.py:438-442`). Gate A derivation is in the
module docstring and `docs/G191093Measured.md`. Gate E is pending
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
  look-ahead at the NEXT open.
* CORRECTNESS: a hand-derived example at `length=3`, checked bar by bar,
  plus a spot check at the shipped default against an independent per-bar
  computation using plain numpy array slicing, not the module's own
  `.rolling()` calls.
* WARM-UP SUBTLETY: bar 0 has no `O1`, so its down/up status is undefined,
  not merely "not a down day". The module masks it to `NaN` explicitly
  (matching the prototype's own `.where(o1.notna())`) rather than relying
  on `np.maximum`'s NaN-propagation through `down_move` to get the same
  answer by accident -- on the CURRENT arithmetic both read `NaN` at bar 0
  (measured, `python docs/measure_g191_093.py`), but the explicit mask
  survives a future rewrite of `down_move` that stops propagating `NaN`
  the same way.
* SCALE-FREE: bit-identical under OHLC x8/x64 (power-of-two, exact in
  IEEE754), within float64 tolerance under x10/x3.7. Matching NaN masks,
  plus `0 < fires < n` and `nunique > 1`.
* Wiring: `Category`, the accessor, the column name `G191_093_20`.
"""
import importlib
import types

import numpy as np
import pandas as pd
import pytest
from pandas import Series

from .context import pandas_ta as ta
from pandas_ta.momentum.g191_093 import g191_093


def _ohlc(n=1500, seed=11, sigma=0.015):
    rng = np.random.default_rng(seed)
    close = 100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n)))
    rng2 = np.random.default_rng(seed + 1)
    spread = np.abs(rng2.normal(0.0, 0.01, n)) * close
    high = close + spread * rng2.uniform(0.2, 1.0, n)
    low = close - spread * rng2.uniform(0.2, 1.0, n)
    open_ = low + (high - low) * rng2.uniform(0.0, 1.0, n)
    idx = pd.RangeIndex(n)
    return Series(open_, index=idx), Series(low, index=idx), Series(close, index=idx)


# ------------------------------------------------------------ correctness


def test_hand_derived_six_bars():
    """length=3.

    open  = [10, 8, 12, 9, 15, 7]
    low   = [ 9, 6, 11, 5, 14, 6]
    O1    = [nan, 10, 8, 12, 9, 15]
    O>=O1?  [nan, False, True, False, True, False]
    O-L   = [1, 2, 1, 4, 1, 1]
    O-O1  = [nan, -2, 4, -3, 6, -8]
    down_move = MAX(O-L, O-O1) = [nan, 2, 4, 4, 6, 1]
    contribution = O>=O1 ? 0 : down_move, bar0 masked NaN:
                  [nan, 2, 0, 4, 0, 1]
    DBM (rolling sum, length=3):
        t=0,1: NaN (window touches the masked bar 0)
        t=2: sum([nan,2,0]) -> NaN (still touches bar 0)
        t=3: sum([2,0,4]) = 6
        t=4: sum([0,4,0]) = 4
        t=5: sum([4,0,1]) = 5
    close = [100, 101, 102, 103, 104, 105] (arbitrary, close not used above)
    result[3] = 6/103, result[4] = 4/104, result[5] = 5/105
    """
    open_ = Series([10.0, 8.0, 12.0, 9.0, 15.0, 7.0])
    low = Series([9.0, 6.0, 11.0, 5.0, 14.0, 6.0])
    close = Series([100.0, 101.0, 102.0, 103.0, 104.0, 105.0])

    out = g191_093(open_, low, close, length=3)

    assert out.iloc[:3].isna().all()
    assert out.iloc[3] == pytest.approx(6.0 / 103.0, abs=1e-12)
    assert out.iloc[4] == pytest.approx(4.0 / 104.0, abs=1e-12)
    assert out.iloc[5] == pytest.approx(5.0 / 105.0, abs=1e-12)


def test_matches_an_independent_loop_at_defaults():
    """Spot-checks 3 bars of the shipped default (length=20) against an
    independent per-bar computation using plain numpy array slicing, not
    pandas' own `.rolling()` calls."""
    open_, low, close = _ohlc(900, seed=5)
    out = g191_093(open_, low, close)
    o, l, c = (s.to_numpy(dtype=float) for s in (open_, low, close))
    length = 20

    def expected_at(t):
        idx = np.arange(t - length + 1, t + 1)  # all >= 1 since t >= length
        o1 = o[idx - 1]
        down_move = np.maximum(o[idx] - l[idx], o[idx] - o1)
        contribution = np.where(o[idx] >= o1, 0.0, down_move)
        return np.sum(contribution) / c[t]

    for t in (300, 600, 899):
        assert out.iloc[t] == pytest.approx(expected_at(t), rel=1e-9)


def test_insufficient_history_returns_none():
    open_, low, close = _ohlc(20)  # defaults need length + 1 = 21 bars
    assert g191_093(open_, low, close) is None


def test_exact_min_length_fires_at_the_warmup_boundary():
    open_, low, close = _ohlc(21)  # exactly length + 1 = 21 bars
    out = g191_093(open_, low, close)
    assert out is not None
    assert out.iloc[:20].isna().all()
    assert pd.notna(out.iloc[20])


def test_default_name():
    open_, low, close = _ohlc()
    out = g191_093(open_, low, close)
    assert out.name == "G191_093_20"


def test_distinct_lengths_produce_distinct_names_and_values():
    open_, low, close = _ohlc(400)
    out1 = g191_093(open_, low, close, length=10)
    out2 = g191_093(open_, low, close, length=15)
    assert out1.name != out2.name
    assert out1.name == "G191_093_10"
    assert out2.name == "G191_093_15"
    m = out1.notna() & out2.notna()
    assert (out1[m] != out2[m]).any()


# -------------------------------------------------------------- causality


_REAL = importlib.import_module("pandas_ta.momentum.g191_093")


def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_g191_093_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


WRITE_SHIFT_MUTANT = (
    "result = dbm / close",
    "result = (dbm / close).shift(-length)",  # a length-bar look-ahead
)
FORWARD_DELAY_MUTANT = (
    "prior_open = open_.shift(1)",
    "prior_open = open_.shift(-1)",  # O1 turned into a look-ahead at the NEXT open
)

OFFSETS = range(150, 1500, 40)  # past the 21-bar warm-up


def _leaks(fn):
    open_, low, close = _ohlc(1500)
    o_open, o_low, o_close = _ohlc(1500, seed=97)
    base = fn(open_, low, close)
    hits = 0
    for j in OFFSETS:
        po, pl, pc = open_.copy(), low.copy(), close.copy()
        po.iloc[j:] = o_open.iloc[j:].values
        pl.iloc[j:] = o_low.iloc[j:].values
        pc.iloc[j:] = o_close.iloc[j:].values
        out = fn(po, pl, pc)
        a, b = base.iloc[:j], out.iloc[:j]
        if not (a.isna() == b.isna()).all():
            hits += 1
            continue
        m = a.notna()
        if (a[m] != b[m]).any():
            hits += 1
    return hits


def test_real_module_never_reads_the_future():
    assert _leaks(g191_093) == 0


def test_write_shift_mutant_is_caught():
    mod = _load_mutant(*WRITE_SHIFT_MUTANT)
    open_, low, close = _ohlc(1500)
    assert not mod.g191_093(open_, low, close).equals(g191_093(open_, low, close))  # live
    assert _leaks(mod.g191_093) == len(list(OFFSETS))  # caught, every offset


def test_forward_delay_mutant_is_caught():
    """A dedicated, deterministic construction rather than the random
    `_leaks` sweep above: `MAX(O-L, O-O1)` almost always collapses to
    `O-L` under real OHLC consistency (`low <= open`), since the `O-O1`
    term can dominate only when `O1 < low <= open`, which together with
    the branch's own `open < O1` is a contradiction. So the DELAY
    direction changes the formula's output only through which bars the
    `open >= O1` branch gate selects (0 vs. `O-L`), not through the
    magnitude of `O-O1` itself -- a random sweep would therefore miss the
    leak whenever the gate happens to agree by chance (measured: 21 of 34
    offsets, not every one). This builds a strictly increasing `open`
    series, so the forward-shifted mutant's gate is always False (always
    the nonzero branch) on the unperturbed data, then perturbs only the
    suffix so the mutant's bar `j-1` gate flips to True (0) -- a
    one-bar-wide leak the real (backward) module cannot see, since its
    bar `j-1` reads only `open[j-2]` and `open[j-1]`, both untouched."""
    mod = _load_mutant(*FORWARD_DELAY_MUTANT)
    length = 3
    n = 10
    j = 6
    open_base = Series([float(10 + i) for i in range(n)])  # strictly increasing
    low = open_base - 1.0
    close = Series([100.0] * n)

    open_pert = open_base.copy()
    # Perturb the suffix below open[j-1], flipping the mutant's bar-(j-1)
    # gate from False (nonzero) to True (0).
    open_pert.iloc[j:] = open_base.iloc[j - 1] - 5.0
    low_pert = low.copy()
    low_pert.iloc[j:] = open_pert.iloc[j:] - 1.0

    base_mut = mod.g191_093(open_base, low, close, length=length)
    pert_mut = mod.g191_093(open_pert, low_pert, close, length=length)
    assert base_mut.iloc[j - 1] != pytest.approx(pert_mut.iloc[j - 1])  # mutant leaks

    base_real = g191_093(open_base, low, close, length=length)
    pert_real = g191_093(open_pert, low_pert, close, length=length)
    assert base_real.iloc[j - 1] == pytest.approx(pert_real.iloc[j - 1])  # real module clean


# ------------------------------------------------------------ reachability


def test_fires_on_a_non_trivial_fraction():
    open_, low, close = _ohlc()  # 1500 bars, defaults
    out = g191_093(open_, low, close)
    fires = int(out.notna().sum())
    assert fires > 1400


def test_fires_and_is_not_constant():
    open_, low, close = _ohlc()
    out = g191_093(open_, low, close)
    fires = int(out.notna().sum())
    assert 0 < fires < len(out)
    assert out.dropna().nunique() > 100


# ------------------------------------------------------------ scale-free


@pytest.mark.parametrize("k", [8.0, 64.0])
def test_price_scale_is_bit_identical(k):
    open_, low, close = _ohlc()
    base = g191_093(open_, low, close)
    scaled = g191_093(open_ * k, low * k, close * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_price_scale_within_tolerance(k):
    open_, low, close = _ohlc()
    base = g191_093(open_, low, close)
    scaled = g191_093(open_ * k, low * k, close * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] - scaled[m]).abs().max() < 1e-9


# ---------------------------------------------------------------- wiring


def test_name_registration_and_accessor():
    open_, low, close = _ohlc(400)
    df = pd.DataFrame({"open": open_, "high": close, "low": low, "close": close,
                        "volume": 1.0})
    assert "g191_093" in ta.Category["momentum"]
    out = df.ta.g191_093()
    assert out.name == "G191_093_20"
    pd.testing.assert_series_equal(out, g191_093(open_, low, close))
    # tunable kwarg forwarded under its own name -- the "supertrend
    # failure mode" (CLAUDE.md) hasattr cannot see.
    renamed = df.ta.g191_093(length=10)
    assert renamed.name == "G191_093_10"
