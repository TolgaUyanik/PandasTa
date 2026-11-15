# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.statistics.lot_zeroret_60` -- share of zero-return
days over a trailing 60-bar window (Lesmond-Ogden-Trzcinka 1999 RFS
liquidity proxy; OSAP's `zerotrade` is the named zero-volume analogue,
substituted here with zero returns because this fork's harness drops
zero-volume bars as flat bars; issue #39). Ported from the issue's own
stated formula, `count(r == 0, 60)/60` -- unlike `osap_mrrev` #37 or
`osap_voltrend_60` #38, no plain-language-to-formula derivation was needed
here, only the warm-up masking detail covered below. Measurements and the
open gates are in `docs/LotZeroret60Measured.md`. Gate E is pending
(CLAUDE.md, "Owed, not failed").

What these pin, in order of how much it would hurt to lose:

* CAUSALITY by future-perturbation on a DENSE tie series: a plain sparse
  random walk makes zero-return events rare, so most perturbed windows
  carry the same (zero) count in both the real module and a look-ahead
  mutant by luck, not by causality -- a weak check that caught only 3 of 28
  offsets in a first attempt (see `docs/measure_lot_zeroret_60.py`). A
  series with a forced tie every 4th bar, spliced with a tie-free tail past
  each offset, makes almost every window's own zero-count change when the
  future is rewritten: real module 0 of 28 leaks, a `center=True` mutant
  caught at 28 of 28.
* CORRECTNESS against an independent per-window loop built from
  `count(r == 0, length) / length`, plus a 5-bar hand-derived example that
  exercises the undefined-return masking bar.
* SCALE-FREE: `r == 0` reduces to `close[t] == close[t-1]`, an equality
  preserved bit-for-bit under ANY uniform positive close rescale (not only
  powers of two), since IEEE-754 float multiplication is deterministic on
  equal inputs. Measured, not merely asserted, at x8/x64/x10/x3.7, plus
  `0 < fires < n` and not a constant column.
* Wiring: `Category`, the accessor, the column name `LOT_ZERORET_60`.
"""
import importlib
import types

import numpy as np
import pandas as pd
import pytest
from pandas import Series

from .context import pandas_ta as ta
from pandas_ta.statistics.lot_zeroret_60 import lot_zeroret_60


def _walk(n=1600, seed=11, zero_at=()):
    rng = np.random.default_rng(seed)
    close = Series(100 + np.cumsum(rng.normal(0, 1, n)))
    for i in zero_at:
        close.iloc[i] = close.iloc[i - 1]
    return close


def _ticky(n, seed, period=4):
    """Forces an exact tie every `period`-th bar; strictly moves elsewhere."""
    rng = np.random.default_rng(seed)
    steps = np.abs(rng.normal(0, 1, n)) + 0.01
    close = np.empty(n)
    close[0] = 100.0
    for i in range(1, n):
        close[i] = close[i - 1] if i % period == 0 else close[i - 1] + steps[i]
    return Series(close)


def _tickless(n, seed):
    """Strictly increasing -- never an exact tie."""
    rng = np.random.default_rng(seed)
    steps = np.abs(rng.normal(0, 1, n)) + 0.01
    return Series(100.0 + np.cumsum(steps))


# ------------------------------------------------------------ correctness


def test_hand_derived_value():
    """length=3. Closes [100, 100, 100, 103, 103] -> returns
    [NaN, 0, 0, 0.03, 0].

    bar2, window r[0:3] = [NaN, 0, 0]: the window's earliest return (r[0])
        is undefined, so this bar is masked to NaN -- even though a plain
        rolling sum would read 2/3 (r[0]==0 is False, not NaN; r[1] and r[2]
        are both exactly 0).
    bar3, window r[1:4] = [0, 0, 0.03]: earliest return r[1]=0 is defined,
        fires: count=2, ratio=2/3.
    bar4, window r[2:5] = [0, 0.03, 0]: earliest return r[2]=0 is defined,
        fires: count=2, ratio=2/3.
    Derived by hand, not by re-running the module.
    """
    close = Series([100.0, 100.0, 100.0, 103.0, 103.0])
    out = lot_zeroret_60(close, length=3)
    assert pd.isna(out.iloc[0])
    assert pd.isna(out.iloc[1])
    assert pd.isna(out.iloc[2])
    assert out.iloc[3] == pytest.approx(2.0 / 3.0, abs=1e-12)
    assert out.iloc[4] == pytest.approx(2.0 / 3.0, abs=1e-12)


def test_matches_an_independent_loop():
    close = _walk(zero_at=[80, 81, 200, 500, 501, 1400])
    length = 60
    out = lot_zeroret_60(close, length=length)
    r = close.pct_change(fill_method=None).to_numpy(dtype=float)

    ref = np.full(len(r), np.nan)
    for i in range(length, len(r)):
        window = r[i - length + 1:i + 1]
        if np.isnan(window[0]):
            continue
        ref[i] = np.sum(window == 0) / length

    assert (np.isnan(ref) == out.isna().values).all()
    m = ~np.isnan(ref)
    np.testing.assert_allclose(out.values[m], ref[m], rtol=1e-12)


def test_matches_a_direct_rolling_sum():
    """The module is defined to BE count(r == 0, length) / length, masked
    on the window's earliest return -- pin that equivalence directly."""
    close = _walk(zero_at=[80, 300, 900, 1200])
    length = 60
    out = lot_zeroret_60(close, length=length)
    r = close.pct_change(fill_method=None)
    expected = (r == 0).astype(float).rolling(length, min_periods=length).sum() / length
    expected = expected.where(r.shift(length - 1).notna())
    pd.testing.assert_series_equal(out, expected, check_names=False)


def test_insufficient_history_returns_none():
    close = _walk(50)  # default length=60 needs 61 bars
    assert lot_zeroret_60(close) is None


def test_default_length_is_60():
    close = _walk()
    out = lot_zeroret_60(close)
    assert out.name == "LOT_ZERORET_60"
    assert int(out.isna().sum()) == 60


def test_offset_shifts_the_series():
    close = _walk(200)
    base = lot_zeroret_60(close)
    shifted = lot_zeroret_60(close, offset=1)
    pd.testing.assert_series_equal(shifted, base.shift(1), check_names=False)


def test_fillna_fills_the_warmup_nans():
    close = _walk(200)
    out = lot_zeroret_60(close, fillna=0)
    assert not out.isna().any()
    assert (out.iloc[:60] == 0).all()


# -------------------------------------------------------------- causality


_REAL = importlib.import_module("pandas_ta.statistics.lot_zeroret_60")


def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_lot_zeroret_60_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


MUTANT = (
    "counts = zero.rolling(length, min_periods=length).sum()",
    "counts = zero.rolling(length, min_periods=length, center=True).sum()",
)

OFFSETS = range(100, 1500, 50)  # 28 offsets, all past the 60-bar warm-up

_BASE_CLOSE = _ticky(1600, seed=5)
_OTHER_CLOSE = _tickless(1600, seed=99)


def _leaks(fn):
    base = fn(_BASE_CLOSE)
    hits = 0
    for j in OFFSETS:
        pc = _BASE_CLOSE.copy()
        pc.iloc[j:] = _OTHER_CLOSE.iloc[j:].values
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
    assert _leaks(lot_zeroret_60) == 0


def test_lookahead_mutant_is_caught():
    mod = _load_mutant(*MUTANT)
    assert not mod.lot_zeroret_60(_BASE_CLOSE).equals(lot_zeroret_60(_BASE_CLOSE))  # live
    assert _leaks(mod.lot_zeroret_60) == len(OFFSETS)  # caught, 28 of 28


def test_a_sparse_random_walk_is_too_weak_a_causality_check():
    """Documents WHY the causality fixtures above use a dense tie series
    instead of a plain random walk: on a sparse walk, zero-return events are
    rare, so most perturbed windows carry the same (zero) count in both the
    real module and a look-ahead mutant by luck. This is not a property the
    module needs to satisfy; it is a property of the test data that this
    suite deliberately avoids relying on."""
    def mutant(c):
        length = 60
        r = c.pct_change(fill_method=None)
        zero = (r == 0).astype(float)
        counts = zero.rolling(length, min_periods=length, center=True).sum()
        result = counts / length
        return result.where(r.shift(length - 1).notna())

    sparse_close = _walk(1600, seed=5, zero_at=[80, 300, 900, 1200])
    sparse_other = _walk(1600, seed=99)

    def leaks(fn):
        base = fn(sparse_close)
        hits = 0
        for j in OFFSETS:
            pc = sparse_close.copy()
            pc.iloc[j:] = sparse_other.iloc[j:].values
            out = fn(pc)
            a, b = base.iloc[:j], out.iloc[:j]
            if not (a.isna() == b.isna()).all():
                hits += 1
                continue
            m = a.notna()
            if (a[m] != b[m]).any():
                hits += 1
        return hits

    assert leaks(mutant) == 3  # pins the exact count the docstring/docs quote


# ------------------------------------------------------------ scale-free


@pytest.mark.parametrize("k", [8.0, 64.0, 10.0, 3.7])
def test_any_positive_close_scale_is_bit_identical(k):
    """r == 0 reduces to close[t] == close[t-1], an equality IEEE-754
    preserves bit-for-bit under ANY uniform positive rescale (not only a
    power of two): multiplying two equal float values by the same scalar
    is the same multiplication applied to the same bits, so it produces the
    same output bits regardless of what the scalar is."""
    close = _walk(zero_at=[80, 81, 200, 500, 501, 1400])
    base = lot_zeroret_60(close)
    scaled = lot_zeroret_60(close * k)
    assert (base.isna() == scaled.isna()).all()
    m = base.notna()
    assert (base[m] == scaled[m]).all()


def test_fires_and_is_not_constant():
    close = _walk(zero_at=[80, 81, 200, 500, 501, 1400])
    out = lot_zeroret_60(close)
    fires = int(out.notna().sum())
    assert fires == 1540  # 1600 - 60
    assert 0 < fires < len(out)
    assert out.dropna().nunique() > 1


# ---------------------------------------------------------------- wiring


def test_name_registration_and_accessor():
    close = _walk(200)
    df = pd.DataFrame({"open": close, "high": close, "low": close,
                        "close": close, "volume": close})
    assert "lot_zeroret_60" in ta.Category["statistics"]
    out = df.ta.lot_zeroret_60()
    assert out.name == "LOT_ZERORET_60"
    pd.testing.assert_series_equal(out, lot_zeroret_60(close))
    assert df.ta.lot_zeroret_60(length=10).name == "LOT_ZERORET_10"
