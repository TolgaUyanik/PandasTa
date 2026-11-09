# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.statistics.g191_189` -- Guotai Junan's (2017,
"GTJA191") alpha `#189`, per issue #61: `MEAN(|C-MEAN(C,6)|,6)`,
scale-free via `/close`, matching the issue's own prototype
(`docs/issues/screen/ind_screen.py:566-567`). Gate A derivation is in the
module docstring and `docs/G191189Measured.md`. Gate E is pending
(CLAUDE.md, "Owed, not failed").

What these tests pin, in order of how much it would hurt to lose:

* CAUSALITY by future-perturbation: rewrite every bar from `j` onward
  (another synthetic frame), demand bars `[0:j]` bit-identical with
  matching NaN masks, over a sweep of offsets past the 11-bar warm-up.
  One mutant (`importlib` source read, `exec`'d in memory, shown live
  different from the real module): shifting the final rolling-mean write
  index `mad_length` bars into the future -- caught at every offset.
* CORRECTNESS against an independent per-bar computation (plain python
  loop re-deriving the nested rolling mean from scratch, not the module's
  own vectorised `.rolling()` calls), both at small lengths and at the
  shipped defaults, plus a fully hand-computed window.
* NON-REDUNDANCY with the already-shipped `mad` indicator: same name,
  different statistic (single shared window mean vs. a re-centered
  per-bar mean) -- a constructed series where the two disagree.
* SCALE-FREE: bit-identical under x8/x64, within tolerance under x10/x3.7,
  matching NaN masks, plus `0 < fires < n` and `nunique > 1`.
* Wiring: `Category`, the accessor, the column name `G191_189_6_6`.
"""
import importlib
import types

import numpy as np
import pandas as pd
import pytest
from pandas import DataFrame, Series

from .context import pandas_ta as ta
from pandas_ta.statistics.g191_189 import g191_189
from pandas_ta.statistics.mad import mad


def _close(n=900, seed=11, sigma=0.015):
    rng = np.random.default_rng(seed)
    return Series(100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n))))


# ------------------------------------------------------------ correctness


def _expected_at(c, t, mean_length, mad_length):
    """Independent per-bar computation: re-derive the nested rolling mean
    from scratch with explicit python slicing, not the module's own
    vectorised .rolling() calls."""
    devs = []
    for back in range(mad_length - 1, -1, -1):
        tt = t - back
        window = c[tt - mean_length + 1: tt + 1]
        devs.append(abs(c[tt] - sum(window) / mean_length))
    return (sum(devs) / mad_length) / c[t]


def test_matches_an_independent_loop_at_small_lengths():
    close = _close(60, seed=5)
    c = close.to_numpy(dtype=float)
    out = g191_189(close, mean_length=3, mad_length=2)
    for t in (20, 40, 59):
        expected = _expected_at(c, t, 3, 2)
        assert out.iloc[t] == pytest.approx(expected, rel=1e-9), f"bar {t}"


def test_matches_an_independent_loop_at_defaults():
    close = _close(300, seed=5)
    c = close.to_numpy(dtype=float)
    out = g191_189(close)
    for t in (100, 200, 299):
        expected = _expected_at(c, t, 6, 6)
        assert out.iloc[t] == pytest.approx(expected, rel=1e-9), f"bar {t}"


def test_hand_computed_window():
    # close = [1,2,3,4,5,6,7,8,9,10,11], mean_length=3, mad_length=2
    # inner_mean[t] = mean(close[t-2:t+1])
    # at t=10 (close=11): inner_mean windows t=9 (close=10) -> mean(8,9,10)=9, dev=|10-9|=1
    #                                       t=10(close=11) -> mean(9,10,11)=10, dev=|11-10|=1
    # mad = mean(1,1) = 1; result = 1 / 11
    close = Series([float(x) for x in range(1, 12)])
    out = g191_189(close, mean_length=3, mad_length=2)
    assert out.iloc[:3].isna().all()  # min_length = 3+2-1 = 4, NaN through index 2
    assert pd.notna(out.iloc[3])
    assert out.iloc[10] == pytest.approx(1.0 / 11.0, abs=1e-12)


def test_insufficient_history_returns_none():
    close = _close(10)  # defaults need min_length = 11
    assert g191_189(close) is None


def test_exact_min_length_fires_at_the_warmup_boundary():
    close = _close(11)  # exactly min_length = 11
    out = g191_189(close)
    assert out is not None
    assert out.iloc[:10].isna().all()
    assert pd.notna(out.iloc[10])


def test_default_name():
    close = _close()
    out = g191_189(close)
    assert out.name == "G191_189_6_6"


def test_distinct_lengths_produce_distinct_names_and_values():
    close = _close(200)
    out1 = g191_189(close, mean_length=3, mad_length=4)
    out2 = g191_189(close, mean_length=10, mad_length=12)
    assert out1.name != out2.name
    assert out1.name == "G191_189_3_4"
    assert out2.name == "G191_189_10_12"
    m = out1.notna() & out2.notna()
    assert (out1[m] != out2[m]).any()


def test_constant_close_reads_zero():
    close = Series([50.0] * 20)
    out = g191_189(close)
    assert (out.iloc[10:] == 0.0).all()


# ----------------------------------------------------------- non-redundancy


def test_still_differs_from_mad_at_mad_length_one():
    """The two formulas coincide only in the FULLY degenerate case
    mean_length=mad_length=1 (both collapse to an identically-zero
    column). At mad_length=1 alone with mean_length>1, mad.py still
    averages all mean_length in-window deviations from the window's own
    single mean, while g191_189 reports only the LAST bar's deviation
    from its own (different) local mean -- these must still disagree."""
    close = Series([1.0, 2.0, 3.0, 4.0, 5.0])
    pre_div = g191_189(close, mean_length=3, mad_length=1) * close
    shipped = mad(close, length=3)
    for t in (2, 3, 4):
        assert pre_div.iloc[t] != pytest.approx(shipped.iloc[t])


def test_length_one_is_honoured_not_silently_defaulted():
    """mean_length=1 / mad_length=1 are legitimate (if degenerate) window
    sizes -- a validation bug that silently falls back to the default
    would make this test's companion (test_still_differs_from_mad_at_mad_length_one)
    pass for the wrong reason."""
    close = _close(30)
    out1 = g191_189(close, mean_length=1, mad_length=1)
    assert out1.name == "G191_189_1_1"
    assert (out1.dropna() == 0.0).all()  # close[t] - close[t] = 0, every bar
    out2 = g191_189(close, mean_length=3, mad_length=1)
    assert out2.name == "G191_189_3_1"
    assert out2.dropna().nunique() > 1  # not silently defaulted to length 6


def test_differs_from_the_shipped_mad_indicator():
    """Same informal name ('mean absolute deviation'), different statistic:
    `mad(close, length)` shares ONE window mean across every deviation in
    the window; `g191_189` re-centers at every bar before averaging. On a
    trending series (not flat, not i.i.d. noise) the two must disagree."""
    close = _close(300, seed=3, sigma=0.02)
    g191 = g191_189(close, mean_length=6, mad_length=6)
    shipped_mad = mad(close, length=6)  # single shared window mean, same length
    both = g191.notna() & shipped_mad.notna()
    assert both.sum() > 100
    # shipped_mad is NOT divided by close -- compare on the same (scale-free)
    # footing by dividing it too, so the test isolates the statistic, not units.
    shipped_scaled = shipped_mad / close
    assert (g191[both] != shipped_scaled[both]).any()


# -------------------------------------------------------------- causality

_REAL = importlib.import_module("pandas_ta.statistics.g191_189")


def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_g191_189_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


WRITE_SHIFT_MUTANT = (
    "mad = deviation.rolling(mad_length, min_periods=mad_length).mean()",
    "mad = deviation.rolling(mad_length, min_periods=mad_length).mean().shift(-mad_length)",
)

OFFSETS = range(50, 900, 40)  # past the 11-bar warm-up


def _leaks(fn):
    close = _close(900)
    o_close = _close(900, seed=97)
    base = fn(close)
    hits = 0
    for j in OFFSETS:
        p_close = close.copy()
        p_close.iloc[j:] = o_close.iloc[j:].values
        out = fn(p_close)
        a, b = base.iloc[:j], out.iloc[:j]
        if not (a.isna() == b.isna()).all():
            hits += 1
            continue
        m = a.notna()
        if (a[m] != b[m]).any():
            hits += 1
    return hits


def test_real_module_never_reads_the_future():
    assert _leaks(g191_189) == 0


def test_write_shift_mutant_is_caught():
    mod = _load_mutant(*WRITE_SHIFT_MUTANT)
    close = _close(900)
    assert not mod.g191_189(close).equals(g191_189(close))  # live
    assert _leaks(mod.g191_189) == len(list(OFFSETS))  # caught, every offset


# ------------------------------------------------------------ reachability


def test_fires_on_a_non_trivial_fraction():
    close = _close()  # 900 bars, defaults
    out = g191_189(close)
    fires = int(out.notna().sum())
    assert fires > 800


def test_fires_and_is_not_constant():
    close = _close()
    out = g191_189(close)
    fires = int(out.notna().sum())
    assert 0 < fires < len(out)
    assert out.dropna().nunique() > 100


# ------------------------------------------------------------ scale-free


@pytest.mark.parametrize("k", [8.0, 64.0])
def test_price_scale_is_bit_identical(k):
    close = _close()
    base = g191_189(close)
    scaled = g191_189(close * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] == scaled[m]).all()


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_price_scale_within_tolerance(k):
    close = _close()
    base = g191_189(close)
    scaled = g191_189(close * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] - scaled[m]).abs().max() < 1e-9


# ---------------------------------------------------------------- wiring


def test_name_registration_and_accessor():
    close = _close(400)
    df = DataFrame({"open": close, "high": close, "low": close, "close": close,
                     "volume": 1.0})
    assert "g191_189" in ta.Category["statistics"]
    out = df.ta.g191_189()
    assert out.name == "G191_189_6_6"
    pd.testing.assert_series_equal(out, g191_189(close))
    # every tunable kwarg forwarded under its own name -- the "supertrend
    # failure mode" (CLAUDE.md) hasattr cannot see.
    renamed = df.ta.g191_189(mean_length=3, mad_length=4)
    assert renamed.name == "G191_189_3_4"
