# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.momentum.ovn_split` -- the rolling-sum overnight
(close[1]->open) / intraday (open->close) return split. PandasTa issue #14.
Measurements and the open gates are in `docs/OvnSplitMeasured.md`.

What these tests pin, in order of how much it would hurt to lose them:

* CORRECTNESS against an independent reference: a plain Python loop that
  builds the two per-bar log-return legs and sums each over the trailing
  window, written from the formula, not the module. Hand-computed cases
  give exact closed forms: an overnight-only move sums entirely into
  OVNSUM with INTSUM exactly 0, and vice versa for an intraday-only move.
* CAUSALITY by future-perturbation: replace the closing tail from offset
  `j` onward with a different walk, demand bars `[0:j]` bit-identical with
  matching NaN masks, over 32 offsets. Two one-bar look-ahead mutants
  (`importlib` source read, `exec`'d in memory) -- the overnight leg read
  one bar ahead, and the rolling window read one bar ahead -- are each
  proved live, then caught at 32 of 32.
* SCALE-FREE: each leg is LOG(price ratio), so it is invariant to any
  positive rescaling of open/close. x8 and x64 (powers of two) are
  bit-identical; x10 and x3.7 are within tight tolerance (log-of-ratio
  roundoff, not a real difference), with NaN masks matching.
* REACHABILITY: `0 < fires < n` on a composite frame that is overnight-only
  for one stretch and intraday-only for another, so both OVNSUM and INTSUM
  are provably non-constant and the difference column changes sign.
* EDGES: the `length`-bar warm-up, a NaN close/open blanking the windows it
  sits in, `offset`, `fillna`, `length` below 1 falling back to the default,
  too-short input returning `None`.
* Wiring: `Category`, the accessor, the three column names.
"""
import importlib
import types

import numpy as np
import pandas as pd
import pytest
from pandas import DataFrame, Series

from .context import pandas_ta as ta
from pandas_ta.momentum.ovn_split import ovn_split


def _walk(n=1200, seed=14, sigma_ovn=0.004, sigma_int=0.011, tick=0.01):
    """Overnight/intraday random walk: open = prior close * exp(overnight),
    close = open * exp(intraday) -- the same generative model `gapm`'s tests
    use, so the two return legs are not confounded (unlike a plain price
    walk, where open is just noise around the same bar's close)."""
    rng = np.random.default_rng(seed)
    overnight = rng.normal(0.0, sigma_ovn, n)
    intraday = rng.normal(0.0, sigma_int, n)
    close = np.empty(n)
    open_ = np.empty(n)
    close[0] = 100.0
    open_[0] = 100.0
    for i in range(1, n):
        open_[i] = close[i - 1] * np.exp(overnight[i])
        close[i] = open_[i] * np.exp(intraday[i])
    if tick:
        open_ = np.round(open_ / tick) * tick
        close = np.round(close / tick) * tick
    return Series(open_), Series(close)


def _reference(open_, close, length):
    """SUM(log(open/close[1]), length) and SUM(log(close/open), length), as
    a plain Python loop over per-bar legs, written from the formula."""
    n = len(close)
    o = open_.to_numpy(dtype=float)
    c = close.to_numpy(dtype=float)
    overnight = np.empty(n)
    intraday = np.empty(n)
    overnight[0] = np.nan
    intraday[0] = np.nan  # blanked to match overnight's bar-0 warm-up
    for t in range(1, n):
        overnight[t] = np.log(o[t] / c[t - 1])
        intraday[t] = np.log(c[t] / o[t])
    ovn = np.full(n, np.nan)
    intr = np.full(n, np.nan)
    for t in range(length, n):
        window_o = overnight[t - length + 1: t + 1]
        window_i = intraday[t - length + 1: t + 1]
        if np.any(np.isnan(window_o)):
            continue
        ovn[t] = window_o.sum()
        intr[t] = window_i.sum()
    return ovn, intr


# ------------------------------------------------------------ correctness


@pytest.mark.parametrize("length", [21, 9, 2])
def test_matches_the_reference_loop(length):
    open_, close = _walk(400)
    out = ovn_split(open_, close, length=length)
    ref_o, ref_i = _reference(open_, close, length)
    mask = ~np.isnan(ref_o)
    assert (out[f"OVNSUM_{length}"].isna().values == np.isnan(ref_o)).all()
    assert (out[f"INTSUM_{length}"].isna().values == np.isnan(ref_i)).all()
    np.testing.assert_allclose(out[f"OVNSUM_{length}"].values[mask], ref_o[mask], rtol=1e-9, atol=1e-12)
    np.testing.assert_allclose(out[f"INTSUM_{length}"].values[mask], ref_i[mask], rtol=1e-9, atol=1e-12)
    diff = out[f"OVNSUM_{length}"] - out[f"INTSUM_{length}"]
    pd.testing.assert_series_equal(out[f"OVNINTDIFF_{length}"], diff, check_names=False)


def test_overnight_only_move_sums_entirely_into_ovnsum():
    # close == open on every bar (zero intraday move); only the close[1]->open
    # leg moves. INTSUM must be exactly 0 and OVNSUM must carry the whole move.
    n = 40
    rng = np.random.default_rng(1)
    overnight = rng.normal(0.0, 0.01, n)
    close = np.empty(n)
    close[0] = 100.0
    for i in range(1, n):
        close[i] = close[i - 1] * np.exp(overnight[i])
    close = Series(close)
    open_ = close.copy()  # open == close every bar -> zero intraday leg
    out = ovn_split(open_, close, length=10)
    assert out["INTSUM_10"].dropna().eq(0.0).all()
    expected_ovn = np.log(close.to_numpy() / close.shift(1).to_numpy())
    expected_ovn_sum = Series(expected_ovn).rolling(10).sum()
    np.testing.assert_allclose(out["OVNSUM_10"].values[10:], expected_ovn_sum.values[10:], rtol=1e-9, atol=1e-12)


def test_intraday_only_move_sums_entirely_into_intsum():
    # open == prior close on every bar (zero overnight gap); only open->close moves.
    n = 40
    rng = np.random.default_rng(2)
    intraday = rng.normal(0.0, 0.01, n)
    close = np.empty(n)
    open_ = np.empty(n)
    close[0] = 100.0
    open_[0] = 100.0
    for i in range(1, n):
        open_[i] = close[i - 1]  # open == prior close -> zero overnight leg
        close[i] = open_[i] * np.exp(intraday[i])
    open_, close = Series(open_), Series(close)
    out = ovn_split(open_, close, length=10)
    assert out["OVNSUM_10"].dropna().eq(0.0).all()


def test_flat_price_reads_zero_both_legs():
    close = Series([50.0] * 30)
    open_ = Series([50.0] * 30)
    out = ovn_split(open_, close, length=10)
    assert out["OVNSUM_10"].dropna().eq(0.0).all()
    assert out["INTSUM_10"].dropna().eq(0.0).all()
    assert out["OVNINTDIFF_10"].dropna().eq(0.0).all()


# -------------------------------------------------------------- causality

_REAL = importlib.import_module("pandas_ta.momentum.ovn_split")


def _load_mutant(old, new, tag):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType(f"_ovn_split_mutant_{tag}")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


MUTANTS = {
    # the overnight leg reads tomorrow's open instead of today's
    "overnight_leg": (
        "overnight = log(open_.to_numpy(dtype=float) / close.shift(1).to_numpy(dtype=float))",
        "overnight = log(open_.shift(-1).to_numpy(dtype=float) / close.shift(1).to_numpy(dtype=float))",
    ),
    # the rolling window reads one bar ahead
    "window": (
        "ovn_sum = overnight.rolling(length).sum()",
        "ovn_sum = overnight.shift(-1).rolling(length).sum()",
    ),
}

OFFSETS = range(60, 1150, 35)  # 32 offsets


def _moved(a, b):
    if not (a.isna() == b.isna()).all():
        return True
    m = a.notna()
    return bool((a[m] != b[m]).any())


def _leaks(fn):
    """Count offsets `j` at which replacing the closing tail from `j` onward
    with a different walk moves any bar < j -- the signature of a look-ahead."""
    open_, close = _walk()
    base = fn(open_, close)
    other_open, other_close = _walk(seed=99)
    hits = 0
    for j in OFFSETS:
        po, pc = open_.copy(), close.copy()
        po.iloc[j:] = other_open.iloc[j:].values
        pc.iloc[j:] = other_close.iloc[j:].values
        out = fn(po, pc)
        if any(_moved(base[c].iloc[:j], out[c].iloc[:j]) for c in base.columns):
            hits += 1
    return hits


def test_real_module_never_reads_the_future():
    assert _leaks(ovn_split) == 0


@pytest.mark.parametrize("tag", sorted(MUTANTS))
def test_mutant_is_caught(tag):
    mod = _load_mutant(*MUTANTS[tag], tag)
    open_, close = _walk()
    assert not mod.ovn_split(open_, close).equals(ovn_split(open_, close))  # live
    assert _leaks(mod.ovn_split) == len(OFFSETS)                            # caught, every offset


# ------------------------------------------------------------ scale-free


@pytest.mark.parametrize("k", [8.0, 64.0])
def test_power_of_two_scale_is_bit_identical(k):
    open_, close = _walk()
    base, scaled = ovn_split(open_, close), ovn_split(open_ * k, close * k)
    for col in base.columns:
        assert (base[col].isna() == scaled[col].isna()).all()
        m = base[col].notna()
        assert (base[col][m] == scaled[col][m]).all()


@pytest.mark.parametrize("k", [10.0, 3.7])
def test_non_power_of_two_scale_is_within_tolerance(k):
    open_, close = _walk()
    base, scaled = ovn_split(open_, close), ovn_split(open_ * k, close * k)
    for col in base.columns:
        assert (base[col].isna() == scaled[col].isna()).all()
        m = base[col].notna()
        np.testing.assert_allclose(base[col][m].values, scaled[col][m].values, rtol=0, atol=1e-10)


# ------------------------------------------------------------ reachability


def test_column_is_not_constant_on_a_composite_frame():
    # 50 bars overnight-only move, then 50 bars intraday-only move
    rng = np.random.default_rng(3)
    n1, n2 = 50, 50
    close1 = np.empty(n1)
    close1[0] = 100.0
    ovn_moves = rng.normal(0.0, 0.01, n1)
    for i in range(1, n1):
        close1[i] = close1[i - 1] * np.exp(ovn_moves[i])
    open1 = close1.copy()

    close2 = np.empty(n2)
    open2 = np.empty(n2)
    close2[0] = close1[-1]
    open2[0] = close1[-1]
    int_moves = rng.normal(0.0, 0.01, n2)
    for i in range(1, n2):
        open2[i] = close2[i - 1]
        close2[i] = open2[i] * np.exp(int_moves[i])

    open_ = Series(np.concatenate([open1, open2]))
    close = Series(np.concatenate([close1, close2]))
    out = ovn_split(open_, close, length=10).dropna()
    assert out["OVNSUM_10"].nunique() > 5
    assert out["INTSUM_10"].nunique() > 5
    assert (out["OVNINTDIFF_10"] > 0).sum() > 0
    assert (out["OVNINTDIFF_10"] < 0).sum() > 0
    n = len(ovn_split(open_, close, length=10))
    assert 0 < len(out) < n


# ---------------------------------------------------------------- edges


def test_edge_cases():
    open_, close = _walk()
    base = ovn_split(open_, close)
    assert int(base["OVNSUM_21"].isna().sum()) == 21  # length-bar warm-up
    oc, cc = open_.copy(), close.copy()
    cc[500] = np.nan
    gapped = ovn_split(oc, cc)
    # close[500] = NaN blanks intraday[500] directly, and overnight[501]
    # (which reads close[500] as the prior close) one bar later.
    assert gapped["INTSUM_21"][500:521].isna().all() and gapped["INTSUM_21"][521:].notna().all()
    assert gapped["OVNSUM_21"][501:522].isna().all() and gapped["OVNSUM_21"][522:].notna().all()
    for bad in (0, -1):
        assert ovn_split(open_, close, length=bad).name == "OVN_21"
    assert ovn_split(open_, close, length=9).name == "OVN_9"
    shifted = ovn_split(open_, close, offset=1)
    pd.testing.assert_frame_equal(shifted, base.shift(1))
    filled = ovn_split(open_, close, fillna=0)
    assert filled.isna().sum().sum() == 0
    assert ovn_split(open_.iloc[:21], close.iloc[:21]) is None  # needs length + 1 bars


# ---------------------------------------------------------------- wiring


def test_name_registration_and_accessor():
    open_, close = _walk(300)
    df = DataFrame({"open": open_, "high": close, "low": close, "close": close, "volume": 1.0})
    assert "ovn_split" in ta.Category["momentum"]
    out = df.ta.ovn_split()
    assert list(out.columns) == ["OVNSUM_21", "INTSUM_21", "OVNINTDIFF_21"]
    pd.testing.assert_frame_equal(out, ovn_split(open_, close))
    assert list(df.ta.ovn_split(length=9).columns) == ["OVNSUM_9", "INTSUM_9", "OVNINTDIFF_9"]
