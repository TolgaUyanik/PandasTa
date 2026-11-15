# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.statistics.g191_044` -- Guotai Junan's (2017,
"GTJA191") alpha `#44`, per issue #60:
`TSRANK(DECAYLINEAR(CORR(LOW,MEAN(V,10),7),6),4) +
TSRANK(DECAYLINEAR(DELTA(VWAP,3),10),15)`, `VWAP -> (H+L+C)/3`, matching
the issue's own prototype (`docs/issues/screen/ind_screen.py:362-366`).
Gate A derivation is in the module docstring and `docs/G191044Measured.md`.
Gate E is pending (CLAUDE.md, "Owed, not failed").

What these pin, in order of how much it would hurt to lose:

* CAUSALITY by future-perturbation: rewrite every OHLCV bar from `j`
  onward (another synthetic frame), demand bars `[0:j]` bit-identical with
  matching NaN masks, over offsets past the 27-bar warm-up. Two mutants
  (`importlib` source read, `exec`'d in memory), each shown live (differs
  from the real module): shifting the final write index `tsrank2_length`
  bars into the future (caught at **34 of 34** offsets), and flipping the
  backward `DELTA` (`tp.shift(delta_length)`) into a FORWARD shift
  (`tp.shift(-delta_length)`) -- caught at **30 of 34** offsets. The 4
  misses are a measured, understood property of `TSRANK`, not a
  causality gap: at those offsets the leaked future segment is a genuine
  OTHER random walk (potentially far from the true series' level), so the
  corrupted `delta_tp` differs by tens of units (`python
  docs/measure_g191_044.py` prints the exact values, e.g. j=270:
  base `[-0.71, 0.40, 1.87, 3.12]` vs perturbed `[-0.71, 33.1, 34.6,
  34.2]`) -- yet `TSRANK` is an order statistic bounded to `[0, 1]`; if the
  TRUE value already sat at the window's rank ceiling (its own 15-bar
  trailing maximum), replacing it with an even larger outlier produces the
  SAME rank (both `1.0`), so the corruption is invisible to a rank-only
  comparison at exactly those bars. This is the expected behaviour of a
  percentile-rank operator, confirmed by inspecting the raw (non-ranked)
  values at the 4 missed offsets.
* CORRECTNESS: a spot check at small lengths (`mean_v_length=3,
  corr_length=3, decay1_length=2, tsrank1_length=2, delta_length=1,
  decay2_length=2, tsrank2_length=2`, 3 bars on a 60-bar frame) and at the
  shipped defaults (3 bars on a 900-bar frame), each against an
  independent per-bar computation (plain numpy `np.corrcoef`/`np.dot` over
  explicit slices, not the module's own vectorised `.rolling()` calls).
* REACHABILITY (Gate C): on a 1500-bar synthetic frame at the shipped
  default, the column fires on a non-trivial fraction of bars. Its
  cardinality is INHERENTLY small (60 distinct values observed) -- not a
  bug: `TSRANK(x, n)` with no ties is a plain integer rank out of `n`, so
  `term1` has at most 4 distinct values (`tsrank1_length=4`) and `term2`
  has at most 15 (`tsrank2_length=15`); their sum has at most `4*15=60`
  distinct combinations, matching exactly what is measured.
* SCALE-FREE: `CORR` is exactly invariant to a positive rescale of either
  input, `DECAYLINEAR` is a fixed-weight linear combination untouched by
  an already-invariant input, and `TSRANK` is an order statistic invariant
  to ANY positive rescale of its own input -- so both branches, and their
  sum, are scale-free BY CONSTRUCTION for a positive rescale of price
  (`high`/`low`/`close`) and volume INDEPENDENTLY. Bit-identical under
  both PRICE and VOLUME x8/x64/x10/x3.7 (not merely the power-of-two
  cases -- rank ordering is untouched by ANY positive rescale, so there is
  no floating-point rounding residual at all, unlike a ratio- or
  correlation-only column). Matching NaN masks, plus `0 < fires < n` and
  `nunique > 1`.
* Wiring: `Category`, the accessor, the column name
  `G191_044_10_7_6_4_3_10_15`.
"""
import importlib
import types

import numpy as np
import pandas as pd
import pytest
from pandas import Series

from .context import pandas_ta as ta
from pandas_ta.statistics.g191_044 import g191_044


def _ohlcv(n=1500, seed=11, sigma=0.015):
    rng = np.random.default_rng(seed)
    close = 100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n)))
    rng2 = np.random.default_rng(seed + 1)
    spread = np.abs(rng2.normal(0.0, 0.01, n)) * close
    high = close + spread * rng2.uniform(0.2, 1.0, n)
    low = close - spread * rng2.uniform(0.2, 1.0, n)
    rng3 = np.random.default_rng(seed + 2)
    volume = np.abs(rng3.normal(1_000_000.0, 300_000.0, n))
    idx = pd.RangeIndex(n)
    return (Series(high, index=idx), Series(low, index=idx), Series(close, index=idx),
            Series(volume, index=idx))


# ------------------------------------------------------------ correctness


def _term1_at(l, v, t, mean_v_length, corr_length, decay1_length, tsrank1_length):
    """Independent per-bar computation of the correlation-rank branch,
    using plain numpy (np.corrcoef, np.dot over explicit slices), not the
    module's own vectorised .rolling() calls."""
    w1 = np.arange(1, decay1_length + 1, dtype=float)
    w1 = w1 / w1.sum()

    def corr1_at(tt):
        mv_window = np.array([v[mt - mean_v_length + 1:mt + 1].mean()
                               for mt in range(tt - corr_length + 1, tt + 1)])
        l_window = l[tt - corr_length + 1:tt + 1]
        return np.corrcoef(l_window, mv_window)[0, 1]

    def decay1_at(tt):
        vals = [corr1_at(tt - back) for back in range(decay1_length - 1, -1, -1)]
        return float(np.dot(vals, w1))

    window = [decay1_at(t - back) for back in range(tsrank1_length - 1, -1, -1)]
    return float(pd.Series(window).rank(pct=True).iloc[-1])


def _term2_at(tp, t, delta_length, decay2_length, tsrank2_length):
    """Independent per-bar computation of the VWAP-momentum-rank branch."""
    w2 = np.arange(1, decay2_length + 1, dtype=float)
    w2 = w2 / w2.sum()

    def delta_at(tt):
        return tp[tt] - tp[tt - delta_length]

    def decay2_at(tt):
        vals = [delta_at(tt - back) for back in range(decay2_length - 1, -1, -1)]
        return float(np.dot(vals, w2))

    window = [decay2_at(t - back) for back in range(tsrank2_length - 1, -1, -1)]
    return float(pd.Series(window).rank(pct=True).iloc[-1])


def _expected_at(high, low, close, volume, t, mean_v_length, corr_length,
                  decay1_length, tsrank1_length, delta_length, decay2_length,
                  tsrank2_length):
    l_np = low.to_numpy(dtype=float)
    v_np = volume.to_numpy(dtype=float)
    tp_np = ((high + low + close) / 3.0).to_numpy(dtype=float)
    return (_term1_at(l_np, v_np, t, mean_v_length, corr_length, decay1_length, tsrank1_length)
            + _term2_at(tp_np, t, delta_length, decay2_length, tsrank2_length))


def test_matches_an_independent_loop_at_small_lengths():
    """mean_v_length=3, corr_length=3, decay1_length=2, tsrank1_length=2,
    delta_length=1, decay2_length=2, tsrank2_length=2, on a 60-bar frame."""
    high, low, close, volume = _ohlcv(60, seed=5)
    out = g191_044(high, low, close, volume, mean_v_length=3, corr_length=3,
                    decay1_length=2, tsrank1_length=2, delta_length=1,
                    decay2_length=2, tsrank2_length=2)
    for t in (20, 40, 59):
        expected = _expected_at(high, low, close, volume, t, 3, 3, 2, 2, 1, 2, 2)
        assert out.iloc[t] == pytest.approx(expected, abs=1e-9), f"bar {t}"


def test_matches_an_independent_loop_at_defaults():
    """Spot-checks 3 bars of the shipped defaults against an independent
    per-bar computation, on a 900-bar frame."""
    high, low, close, volume = _ohlcv(900, seed=5)
    out = g191_044(high, low, close, volume)
    for t in (300, 600, 899):
        expected = _expected_at(high, low, close, volume, t, 10, 7, 6, 4, 3, 10, 15)
        assert out.iloc[t] == pytest.approx(expected, rel=1e-9), f"bar {t}"


def test_insufficient_history_returns_none():
    high, low, close, volume = _ohlcv(26)  # defaults need min_length = 27
    assert g191_044(high, low, close, volume) is None


def test_exact_min_length_fires_at_the_warmup_boundary():
    high, low, close, volume = _ohlcv(27)  # exactly min_length = 27
    out = g191_044(high, low, close, volume)
    assert out is not None
    assert out.iloc[:26].isna().all()
    assert pd.notna(out.iloc[26])


def test_term1_branch_dominates_the_warmup_when_larger():
    """The two branches are computed in PARALLEL, not chained, so the true
    warm-up is the max of the two. With mean_v_length pushed far above the
    second branch's requirement, the first branch's longer warm-up must
    dominate -- a single-branch warm-up check would silently return an
    all-NaN Series instead of the documented None."""
    # branch 1 needs mean_v_length + corr_length + decay1_length + tsrank1_length - 3
    #   = 50 + 20 + 20 + 13 - 3 = 100
    # branch 2 needs delta_length + decay2_length + tsrank2_length - 1 = 1+2+2-1=4
    high, low, close, volume = _ohlcv(99)  # below max(100, 4) = 100
    assert g191_044(high, low, close, volume, mean_v_length=50, corr_length=20,
                     decay1_length=20, tsrank1_length=13, delta_length=1,
                     decay2_length=2, tsrank2_length=2) is None

    high, low, close, volume = _ohlcv(100)  # exactly max(100, 4) = 100
    out = g191_044(high, low, close, volume, mean_v_length=50, corr_length=20,
                    decay1_length=20, tsrank1_length=13, delta_length=1,
                    decay2_length=2, tsrank2_length=2)
    assert out is not None
    assert out.iloc[:99].isna().all()
    assert pd.notna(out.iloc[99])


def test_default_name():
    high, low, close, volume = _ohlcv()
    out = g191_044(high, low, close, volume)
    assert out.name == "G191_044_10_7_6_4_3_10_15"


def test_distinct_lengths_produce_distinct_names_and_values():
    high, low, close, volume = _ohlcv(400)
    out1 = g191_044(high, low, close, volume, mean_v_length=5, corr_length=5,
                     decay1_length=3, tsrank1_length=2, delta_length=2,
                     decay2_length=5, tsrank2_length=8)
    out2 = g191_044(high, low, close, volume, mean_v_length=15, corr_length=10,
                     decay1_length=8, tsrank1_length=6, delta_length=5,
                     decay2_length=12, tsrank2_length=20)
    assert out1.name != out2.name
    assert out1.name == "G191_044_5_5_3_2_2_5_8"
    assert out2.name == "G191_044_15_10_8_6_5_12_20"
    m = out1.notna() & out2.notna()
    assert (out1[m] != out2[m]).any()


def test_misaligned_index_raises():
    high, low, close, volume = _ohlcv(60)
    volume = volume.copy()
    volume.index = volume.index + 1
    with pytest.raises(ValueError):
        g191_044(high, low, close, volume)


# ------------------------------------------------------------ reachability


def test_fires_on_a_non_trivial_fraction():
    high, low, close, volume = _ohlcv()  # 1500 bars, defaults
    out = g191_044(high, low, close, volume)
    fires = int(out.notna().sum())
    assert fires > 1000  # well above a handful of coincidental fires


def test_cardinality_matches_the_discrete_tsrank_product():
    """TSRANK(x, n) with no ties is a plain integer rank out of n, so
    term1 (tsrank1_length=4) has at most 4 distinct values and term2
    (tsrank2_length=15) has at most 15 -- their sum has at most 4*15=60
    distinct combinations. Measured, not assumed: this port's own
    `docs/measure_g191_044.py` observes exactly 60 on a 1500-bar frame."""
    high, low, close, volume = _ohlcv()
    out = g191_044(high, low, close, volume)
    nunique = out.dropna().nunique()
    assert 1 < nunique <= 60


# -------------------------------------------------------------- causality


_REAL = importlib.import_module("pandas_ta.statistics.g191_044")


def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_g191_044_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


WRITE_SHIFT_MUTANT = (
    "result = term1 + term2",
    "result = (term1 + term2).shift(-tsrank2_length)",  # a tsrank2_length-bar look-ahead
)
FORWARD_DELTA_MUTANT = (
    "    delta_tp = tp - tp.shift(delta_length)",
    "    delta_tp = tp - tp.shift(-delta_length)",  # DELTA turned into a look-ahead
)

OFFSETS = range(150, 1500, 40)  # past the 27-bar warm-up
MISSED_FORWARD_DELTA_OFFSETS = 4  # measured: TSRANK ceiling ties, see module docstring


def _leaks(fn):
    high, low, close, volume = _ohlcv(1500)
    oh, ol, oc, ov = _ohlcv(1500, seed=97)
    base = fn(high, low, close, volume)
    hits = 0
    for j in OFFSETS:
        ph, pl, pc, pv = high.copy(), low.copy(), close.copy(), volume.copy()
        ph.iloc[j:] = oh.iloc[j:].values
        pl.iloc[j:] = ol.iloc[j:].values
        pc.iloc[j:] = oc.iloc[j:].values
        pv.iloc[j:] = ov.iloc[j:].values
        out = fn(ph, pl, pc, pv)
        a, b = base.iloc[:j], out.iloc[:j]
        if not (a.isna() == b.isna()).all():
            hits += 1
            continue
        m = a.notna()
        if (a[m] != b[m]).any():
            hits += 1
    return hits


def test_real_module_never_reads_the_future():
    assert _leaks(g191_044) == 0


def test_write_shift_mutant_is_caught():
    mod = _load_mutant(*WRITE_SHIFT_MUTANT)
    high, low, close, volume = _ohlcv(1500)
    assert not mod.g191_044(high, low, close, volume).equals(g191_044(high, low, close, volume))  # live
    assert _leaks(mod.g191_044) == len(list(OFFSETS))  # caught, every offset


def test_forward_delta_mutant_is_caught():
    mod = _load_mutant(*FORWARD_DELTA_MUTANT)
    high, low, close, volume = _ohlcv(1500)
    assert not mod.g191_044(high, low, close, volume).equals(g191_044(high, low, close, volume))  # live
    assert _leaks(mod.g191_044) == len(list(OFFSETS)) - MISSED_FORWARD_DELTA_OFFSETS


# ------------------------------------------------------------ scale-free


@pytest.mark.parametrize("k", [8.0, 64.0, 10.0, 3.7])
def test_price_scale_is_bit_identical(k):
    """CORR and TSRANK are both invariant to ANY positive rescale (not
    merely the power-of-two case) -- no floating-point rounding residual
    at all, unlike a ratio- or correlation-only column."""
    high, low, close, volume = _ohlcv()
    base = g191_044(high, low, close, volume)
    scaled = g191_044(high * k, low * k, close * k, volume)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("k", [8.0, 64.0, 10.0, 3.7])
def test_volume_scale_is_bit_identical(k):
    high, low, close, volume = _ohlcv()
    base = g191_044(high, low, close, volume)
    scaled = g191_044(high, low, close, volume * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] == scaled[m]).all()


def test_fires_and_is_not_constant():
    high, low, close, volume = _ohlcv()
    out = g191_044(high, low, close, volume)
    fires = int(out.notna().sum())
    assert 0 < fires < len(out)
    assert out.dropna().nunique() > 1


# ---------------------------------------------------------------- wiring


def test_name_registration_and_accessor():
    high, low, close, volume = _ohlcv(400)
    df = pd.DataFrame({"open": close, "high": high, "low": low, "close": close,
                        "volume": volume})
    assert "g191_044" in ta.Category["statistics"]
    out = df.ta.g191_044()
    assert out.name == "G191_044_10_7_6_4_3_10_15"
    pd.testing.assert_series_equal(out, g191_044(high, low, close, volume))
    # every tunable kwarg forwarded under its own name in one call -- the
    # "supertrend failure mode" (CLAUDE.md) hasattr cannot see.
    renamed = df.ta.g191_044(mean_v_length=5, corr_length=5, decay1_length=3,
                              tsrank1_length=2, delta_length=2, decay2_length=5,
                              tsrank2_length=8)
    assert renamed.name == "G191_044_5_5_3_2_2_5_8"
