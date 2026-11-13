# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.trend.g191_069` -- Guotai Junan's (2017, "GTJA191")
alpha `#69`, per issue #70: `SUM(DTM,20)` vs `SUM(DBM,20)` normalised by the
larger, `DTM = O<=O1 ? 0 : MAX(H-O, O-O1)`. Gate A derivation is in the
module docstring and `docs/G191069Measured.md`. Gate E is pending (CLAUDE.md,
"Owed, not failed").

What these pin, in order of how much it would hurt to lose:

* CAUSALITY by future-perturbation: rewrite every open/high/low/close bar
  from `j` onward (another synthetic frame), demand bars `[0:j]`
  bit-identical with matching NaN masks, over offsets past the 20-bar
  warm-up. One mutant (`importlib` source read, `exec`'d in memory, the
  final write index shifted `length` bars into the future) is shown live
  (differs from the real module) then caught at every offset.
* CORRECTNESS: a 7-bar hand-derived example at `length=3` (including a
  flat-open boundary bar, `open == open1`), checked against an independent
  per-bar computation. A second spot check at the shipped default
  (`length=20`) against an independent per-bar loop using plain numpy.
* SCALE-FREE: PRICE (open/high/low/close together) x8/x64 bit-identical,
  x10/x3.7 within tolerance -- plus `0 < fires < n` and `nunique > 1`.
* Wiring: `Category`, the accessor, the column name `G191_069_20`.
"""
import importlib
import types

import numpy as np
import pandas as pd
import pytest
from pandas import Series

from .context import pandas_ta as ta
from pandas_ta.trend.g191_069 import g191_069


def _ohlc(n=900, seed=23, lo=50.0, hi=150.0):
    """Synthetic OHLC frame: a close random walk, with open/high/low built
    around it so that high is always the bar's max and low its min."""
    rng = np.random.default_rng(seed)
    steps = rng.normal(0, 1.5, n)
    close = lo + np.abs(np.cumsum(steps)) % (hi - lo)
    close = Series(close)
    open_ = close.shift(1).fillna(close.iloc[0]) + rng.normal(0, 0.5, n)
    gap_up = rng.uniform(0, 1.0, n)
    gap_dn = rng.uniform(0, 1.0, n)
    high = pd.concat([open_, close], axis=1).max(axis=1) + gap_up
    low = pd.concat([open_, close], axis=1).min(axis=1) - gap_dn
    return open_, high, low, close


# ------------------------------------------------------------ correctness


def test_hand_derived_seven_bars():
    """length=3: DTM = O<=O1 ? 0 : MAX(H-O, O-O1); DBM mirrors it on L/<=.
    SD, SB = SUM(DTM,3), SUM(DBM,3); result = SD>SB ? (SD-SB)/SD :
    (SD<SB ? (SD-SB)/SB : 0).

    open  = [100, 105, 103, 103, 108,  95, 110]
    high  = [102, 108, 106, 104, 110, 100, 115]
    low   = [ 98, 102, 100, 101, 104,  92, 107]
    O1 (delay 1): NaN, 100, 105, 103, 103, 108, 95
    bar0: O1 undefined -> DTM=DBM=NaN
    bar1: O=105>O1=100 -> DTM=MAX(H-O,O-O1)=MAX(108-105,105-100)=MAX(3,5)=5; DBM=0
    bar2: O=103<O1=105 -> DTM=0; DBM=MAX(O-L,O-O1)=MAX(103-100,103-105)=MAX(3,-2)=3
    bar3: O=103<=O1=103 (flat, tie) -> DTM=0; O=103>=O1=103 (tie) -> DBM=0
    bar4: O=108>O1=103 -> DTM=MAX(110-108,108-103)=MAX(2,5)=5; DBM=0
    bar5: O=95<O1=108 -> DTM=0; DBM=MAX(95-92,95-108)=MAX(3,-13)=3
    bar6: O=110>O1=95 -> DTM=MAX(115-110,110-95)=MAX(5,15)=15; DBM=0

    DTM = [NaN, 5, 0, 0, 5, 0, 15]
    DBM = [NaN, 0, 3, 0, 0, 3, 0]
    bar3: SD=sum(5,0,0)=5   SB=sum(0,3,0)=3   SD>SB -> (5-3)/5   =  0.400000
    bar4: SD=sum(0,0,5)=5   SB=sum(3,0,0)=3   SD>SB -> (5-3)/5   =  0.400000
    bar5: SD=sum(0,5,0)=5   SB=sum(0,0,3)=3   SD>SB -> (5-3)/5   =  0.400000
    bar6: SD=sum(5,0,15)=20 SB=sum(0,3,0)=3   SD>SB -> (20-3)/20 =  0.850000
    Derived by hand, not by re-running the module. Bar3 exercises the
    flat-open (open == open1) boundary inside the summed window, where
    BOTH DTM and DBM are 0 (neither gate's `<=`/`>=` strict side fires).
    """
    open_ = Series([100.0, 105.0, 103.0, 103.0, 108.0, 95.0, 110.0])
    high = Series([102.0, 108.0, 106.0, 104.0, 110.0, 100.0, 115.0])
    low = Series([98.0, 102.0, 100.0, 101.0, 104.0, 92.0, 107.0])
    close = open_  # unused by the formula; any valid series satisfies verify_series
    out = g191_069(open_, high, low, close, length=3)

    assert out.iloc[:3].isna().all()
    expected = {3: 0.4, 4: 0.4, 5: 0.4, 6: 0.85}
    for t, val in expected.items():
        assert out.iloc[t] == pytest.approx(val, abs=1e-9), f"bar {t}"


def test_matches_an_independent_loop_at_defaults():
    """Spot-checks 3 bars of the shipped default (length=20) against an
    independent per-bar computation using plain numpy slicing, not the
    module's own `.rolling()`/`np.where` calls."""
    open_, high, low, close = _ohlc(900, seed=5)
    out = g191_069(open_, high, low, close)
    o = open_.to_numpy(dtype=float)
    h = high.to_numpy(dtype=float)
    l = low.to_numpy(dtype=float)
    length = 20

    def dtm_dbm_at(i):
        if i == 0:
            return np.nan, np.nan
        o1 = o[i - 1]
        dtm = 0.0 if o[i] <= o1 else max(h[i] - o[i], o[i] - o1)
        dbm = 0.0 if o[i] >= o1 else max(o[i] - l[i], o[i] - o1)
        return dtm, dbm

    def expected_at(t):
        sd = 0.0
        sb = 0.0
        for i in range(t - length + 1, t + 1):
            dtm, dbm = dtm_dbm_at(i)
            sd += dtm
            sb += dbm
        if sd > sb:
            return (sd - sb) / sd
        elif sd < sb:
            return (sd - sb) / sb
        return 0.0

    for t in (300, 600, 899):
        assert out.iloc[t] == pytest.approx(expected_at(t), rel=1e-9)


def test_insufficient_history_returns_none():
    open_, high, low, close = _ohlc(20)  # defaults need length + 1 = 21 bars
    assert g191_069(open_, high, low, close) is None


def test_exact_min_length_fires_at_the_warmup_boundary():
    open_, high, low, close = _ohlc(21)  # exactly length + 1 = 21 bars
    out = g191_069(open_, high, low, close)
    assert out is not None
    assert out.iloc[:20].isna().all()
    assert pd.notna(out.iloc[20])


def test_default_name():
    open_, high, low, close = _ohlc()
    out = g191_069(open_, high, low, close)
    assert out.name == "G191_069_20"


def test_distinct_lengths_produce_distinct_names_and_values():
    open_, high, low, close = _ohlc(300)
    out1 = g191_069(open_, high, low, close, length=10)
    out2 = g191_069(open_, high, low, close, length=30)
    assert out1.name != out2.name
    assert out1.name == "G191_069_10"
    assert out2.name == "G191_069_30"
    m = out1.notna() & out2.notna()
    assert (out1[m] != out2[m]).any()


def test_offset_shifts_the_series():
    open_, high, low, close = _ohlc(200)
    base = g191_069(open_, high, low, close)
    shifted = g191_069(open_, high, low, close, offset=1)
    pd.testing.assert_series_equal(shifted, base.shift(1), check_names=False)


def test_result_is_bounded_in_minus_one_to_one():
    """A difference of two non-negative sums normalized by the larger
    cannot leave [-1, 1]."""
    open_, high, low, close = _ohlc()
    out = g191_069(open_, high, low, close)
    fired = out.dropna()
    assert (fired >= -1.0 - 1e-9).all()
    assert (fired <= 1.0 + 1e-9).all()


# -------------------------------------------------------------- causality


_REAL = importlib.import_module("pandas_ta.trend.g191_069")


def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_g191_069_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


WRITE_SHIFT_MUTANT = (
    "    ).where(sd.notna() & sb.notna())",
    "    ).where(sd.notna() & sb.notna()).shift(-length)",  # a length-bar look-ahead
)

OFFSETS = range(50, 900, 25)  # past the 20-bar warm-up


def _leaks(fn):
    open_, high, low, close = _ohlc(900, seed=71)
    o2, h2, l2, c2 = _ohlc(900, seed=89)
    base = fn(open_, high, low, close)
    hits = 0
    for j in OFFSETS:
        po, ph, pl, pc = open_.copy(), high.copy(), low.copy(), close.copy()
        po.iloc[j:] = o2.iloc[j:].values
        ph.iloc[j:] = h2.iloc[j:].values
        pl.iloc[j:] = l2.iloc[j:].values
        pc.iloc[j:] = c2.iloc[j:].values
        out = fn(po, ph, pl, pc)
        a, b = base.iloc[:j], out.iloc[:j]
        if not (a.isna() == b.isna()).all():
            hits += 1
            continue
        m = a.notna()
        if (a[m] != b[m]).any():
            hits += 1
    return hits


def test_real_module_never_reads_the_future():
    assert _leaks(g191_069) == 0


def test_write_shift_mutant_is_caught():
    mod = _load_mutant(*WRITE_SHIFT_MUTANT)
    open_, high, low, close = _ohlc(900, seed=71)
    assert not mod.g191_069(open_, high, low, close).equals(g191_069(open_, high, low, close))  # live
    assert _leaks(mod.g191_069) == len(list(OFFSETS))  # caught, every offset


# ------------------------------------------------------------ scale-free


@pytest.mark.parametrize("k", [8.0, 64.0])
def test_power_of_two_price_scale_is_bit_identical(k):
    open_, high, low, close = _ohlc()
    base = g191_069(open_, high, low, close)
    scaled = g191_069(open_ * k, high * k, low * k, close * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_other_price_scales_within_tolerance(k):
    open_, high, low, close = _ohlc()
    base = g191_069(open_, high, low, close)
    scaled = g191_069(open_ * k, high * k, low * k, close * k)
    assert (base.isna() == scaled.isna()).all()
    assert (base - scaled).abs().max() < 1e-9


def test_fires_and_is_not_constant():
    open_, high, low, close = _ohlc()
    out = g191_069(open_, high, low, close)
    fires = int(out.notna().sum())
    assert fires == 880  # 900 - 20
    assert 0 < fires < len(out)
    assert out.dropna().nunique() > 1


# ---------------------------------------------------------------- wiring


def test_name_registration_and_accessor():
    open_, high, low, close = _ohlc(200)
    df = pd.DataFrame({"open": open_, "high": high, "low": low, "close": close})
    assert "g191_069" in ta.Category["trend"]
    out = df.ta.g191_069()
    assert out.name == "G191_069_20"
    pd.testing.assert_series_equal(out, g191_069(open_, high, low, close))
    renamed = df.ta.g191_069(length=10)
    assert renamed.name == "G191_069_10"
