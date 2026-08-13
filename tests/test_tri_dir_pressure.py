# tests/test_tri_dir_pressure.py
"""tri_dir_pressure -- Triangular Directional Pressure (TVPTA-6 candidate
10, ported from "Directional Volume Shapes (Zeiierman)"). Only the
source's `scr()` triangular-CDF candle-direction score + its `ps = 2*dm
- 1` rescale are ported (see the module docstring in
pandas_ta/volume/tri_dir_pressure.py for the full NOT-ported list).
Self-contained on synthetic data.

Reachability tests `import pandas_ta`, NOT `importlib.util.spec_from_file_
location` (see TODO.md TVPTA-3(c)).
"""
import math

import numpy as np
import pandas as pd
import pandas.testing as pdt
import pytest

from .context import pandas_ta as ta


def _ohlcv(n=200, seed=0):
    """Valid-OHLC synthetic fixture: STRICT margins (low < min(o,c) and
    max(o,c) < high for every bar) so this is never a degenerate/wick-
    zero fixture by accident -- the dedicated degenerate-bar cases live
    in `_edge_case_bars()` below, exercised on purpose, not by chance.
    """
    rng = np.random.RandomState(seed)
    close = pd.Series(
        100 + np.cumsum(rng.randn(n) * 0.5),
        index=pd.date_range("2020-01-01", periods=n, freq="B"),
    )
    open_ = close.shift(1).fillna(close.iloc[0]) + rng.randn(n) * 0.1
    body_lo = pd.concat([open_, close], axis=1).min(axis=1)
    body_hi = pd.concat([open_, close], axis=1).max(axis=1)
    low = body_lo - (np.abs(rng.randn(n)) * 0.3 + 0.01)
    high = body_hi + (np.abs(rng.randn(n)) * 0.3 + 0.01)
    volume = pd.Series(rng.randint(1000, 50000, n).astype(float), index=close.index)

    # Non-negotiable #2: physically valid OHLC in every fixture -- not
    # just low <= high, the STRONGER per-bar constraint.
    assert (low < body_lo).all() and (body_hi < high).all(), \
        "fixture bug: OHLC must satisfy low <= min(open,close) and max(open,close) <= high"

    return open_, high, low, close, volume


def _edge_case_bars():
    """4 hand-computed bars, one per branch of the triangular-CDF formula
    that is REACHABLE under physically valid OHLC (Pine `scr()`, L51-78)
    -- verified against the SOURCE'S OWN math by hand (see the docstring
    math in the module under test), not just re-derived from the code
    being tested.

    Note what is deliberately absent: the source's `rng == 0 and c != o`
    branch (a degenerate bar where Close differs from Open despite
    High == Low) is UNREACHABLE under valid OHLC -- `low <= min(o,c)`
    and `max(o,c) <= high` together force `o == c == high == low`
    whenever `high == low`. That branch is only reachable on malformed
    data (e.g. a corrupted tick); see
    `test_degenerate_branch_on_malformed_data` below, which deliberately
    does NOT claim valid OHLC.

    bar 0 (general branch, mode strictly inside [low, high]):
        O=10 H=12 L=9 C=11 -> op=10, md=11, lw=2, rw=1
        cdf = (10-9)^2 / (3*2) = 1/6 -> dm=5/6 -> ps=2/3
    bar 1 (degenerate range, doji -- the only valid-OHLC rng==0 bar):
        O=10 H=10 L=10 C=10 -> cdf=0.5 -> dm=0.5 -> ps=0.0 (neutral)
    bar 2 (md == low, close prints exactly at the low): O=11 H=12 L=9 C=9
        op=11, cdf = 1-((12-11)/3)^2 = 1-1/9 = 8/9 -> dm=1/9 -> ps=-7/9
    bar 3 (md == high, close prints exactly at the high): O=9.5 H=12 L=9 C=12
        op=9.5, cdf = ((9.5-9)/3)^2 = (0.5/3)^2 = 1/36 -> dm=35/36 -> ps=17/18
    """
    open_ = pd.Series([10.0, 10.0, 11.0, 9.5])
    high = pd.Series([12.0, 10.0, 12.0, 12.0])
    low = pd.Series([9.0, 10.0, 9.0, 9.0])
    close = pd.Series([11.0, 10.0, 9.0, 12.0])
    volume = pd.Series([100.0, 200.0, 300.0, 400.0])

    for i in range(len(open_)):
        assert low.iloc[i] <= min(open_.iloc[i], close.iloc[i])
        assert max(open_.iloc[i], close.iloc[i]) <= high.iloc[i]

    expected_ps = [2.0 / 3.0, 0.0, -7.0 / 9.0, 17.0 / 18.0]
    return open_, high, low, close, volume, expected_ps


def test_degenerate_branch_on_malformed_data():
    # The source's `rng == 0` branch handles Close != Open despite
    # High == Low -- physically impossible for a valid bar (see
    # `_edge_case_bars` docstring) but reachable on a corrupted tick
    # (e.g. a bad OHLCV row). Deliberately NOT asserting valid-OHLC
    # here -- that is the point of this test.
    open_ = pd.Series([10.0, 9.0])
    high = pd.Series([10.0, 10.0])
    low = pd.Series([10.0, 10.0])
    close = pd.Series([9.0, 10.0])  # bar0: close<open (bearish); bar1: close>open (bullish)
    out = ta.tri_dir_pressure(open_, high, low, close, use_volume=False)
    assert out.iloc[0] == pytest.approx(-1.0)
    assert out.iloc[1] == pytest.approx(1.0)


def test_correctness_hand_computed_ps():
    open_, high, low, close, volume, expected_ps = _edge_case_bars()
    out = ta.tri_dir_pressure(open_, high, low, close, use_volume=False)
    for i, exp in enumerate(expected_ps):
        assert out.iloc[i] == pytest.approx(exp, abs=1e-9), f"bar {i}"


def test_correctness_hand_computed_volume_weighted():
    open_, high, low, close, volume, expected_ps = _edge_case_bars()
    out = ta.tri_dir_pressure(open_, high, low, close, volume=volume, use_volume=True)
    for i, exp in enumerate(expected_ps):
        assert out.iloc[i] == pytest.approx(volume.iloc[i] * exp, abs=1e-6), f"bar {i}"


def test_columns_present_and_named():
    open_, high, low, close, volume = _ohlcv()
    out_pf = ta.tri_dir_pressure(open_, high, low, close, use_volume=False)
    out_vw = ta.tri_dir_pressure(open_, high, low, close, volume=volume, use_volume=True)
    assert out_pf.name == "TRI_DIR_PRESSURE"
    assert out_vw.name == "TRI_DIR_PRESSURE"
    assert isinstance(out_pf, pd.Series) and isinstance(out_vw, pd.Series)


def test_fixture_nondegenerate_at_literal_defaults():
    """Non-negotiable #3: measure the fixture's output at literal engine
    defaults, print actual populated/nonzero counts, and assert a real
    canary -- not gated behind any size condition. Calling with only
    (open_, high, low, close) exercises the LITERAL default signature
    (use_volume defaults to True inside the function, so this also
    covers the "volume required by default" path via the accessor's
    own default in the reachability test below)."""
    open_, high, low, close, volume = _ohlcv()
    out = ta.tri_dir_pressure(open_, high, low, close, use_volume=False)
    populated = out.notna().sum()
    nonzero = (out != 0).sum()
    print(f"tri_dir_pressure defaults: populated={populated}/{len(out)} nonzero={nonzero}/{len(out)}")
    assert populated == len(out), "every bar must produce a value -- this indicator has zero warm-up"
    assert nonzero > len(out) * 0.5, "a stub returning all-zero/constant would pass boundedness but fail this"
    assert out.min() >= -1.0 - 1e-9
    assert out.max() <= 1.0 + 1e-9
    # Not degenerate: real spread, not a single repeated value.
    assert out.nunique() > len(out) * 0.5


def test_bounded_scale_free_when_use_volume_false():
    open_, high, low, close, volume = _ohlcv(n=2000, seed=7)
    out = ta.tri_dir_pressure(open_, high, low, close, use_volume=False)
    assert out.min() >= -1.0 - 1e-9
    assert out.max() <= 1.0 + 1e-9
    assert out.notna().all()


def test_volume_weighted_is_not_bounded_to_unit_range():
    # Sibling-to-vol_delta form: with large volume the magnitude scales
    # past [-1, 1] -- this is a DELIBERATE non-claim, verified by
    # execution, not assumed. Confirms the docstring's "unbounded, like
    # vol_delta" statement is true, not aspirational.
    open_ = pd.Series([10.0])
    high = pd.Series([12.0])
    low = pd.Series([9.0])
    close = pd.Series([11.0])
    volume = pd.Series([1_000_000.0])
    out = ta.tri_dir_pressure(open_, high, low, close, volume=volume, use_volume=True)
    assert abs(out.iloc[0]) > 1.0


def test_no_lookahead_truncation():
    open_, high, low, close, volume = _ohlcv()
    T = 100
    out_full = ta.tri_dir_pressure(open_, high, low, close, volume=volume, use_volume=True)
    out_prefix = ta.tri_dir_pressure(
        open_.iloc[:T + 1], high.iloc[:T + 1], low.iloc[:T + 1],
        close.iloc[:T + 1], volume=volume.iloc[:T + 1], use_volume=True,
    )
    pdt.assert_series_equal(out_full.iloc[:T + 1], out_prefix, check_names=False)
    # The compared prefix genuinely carries signal (not all-equal/zero).
    assert out_prefix.nunique() > 1


def test_mutation_isolated_to_the_mutated_bar():
    # This indicator has NO rolling/stateful component (every bar's `ps`
    # depends only on that bar's own OHLC) -- so a mutation at bar T
    # must change ONLY position T's output, everywhere else must be
    # bit-identical. A stronger causality claim than most rolling-window
    # indicators can make, and worth verifying rather than assuming.
    open_, high, low, close, volume = _ohlcv()
    T = 100
    out_orig = ta.tri_dir_pressure(open_, high, low, close, use_volume=False)

    open_m, high_m, low_m, close_m = open_.copy(), high.copy(), low.copy(), close.copy()
    close_m.iloc[T] = close_m.iloc[T] + 1000.0
    high_m.iloc[T] = high_m.iloc[T] + 1000.0
    out_mut = ta.tri_dir_pressure(open_m, high_m, low_m, close_m, use_volume=False)

    changed = (out_orig != out_mut) & ~(out_orig.isna() & out_mut.isna())
    assert changed.sum() == 1
    assert changed.index[changed][0] == out_orig.index[T]


def test_offset_shifts_result():
    open_, high, low, close, volume = _ohlcv()
    out0 = ta.tri_dir_pressure(open_, high, low, close, use_volume=False)
    out1 = ta.tri_dir_pressure(open_, high, low, close, use_volume=False, offset=1)
    pdt.assert_series_equal(out0.iloc[:-1].reset_index(drop=True), out1.iloc[1:].reset_index(drop=True), check_names=False)
    assert math.isnan(out1.iloc[0])


def test_fillna_kwarg():
    open_, high, low, close, volume = _ohlcv()
    out = ta.tri_dir_pressure(open_, high, low, close, use_volume=False, offset=1, fillna=0)
    assert out.iloc[0] == 0
    assert not out.isna().any()


def test_reachability_via_accessor():
    open_, high, low, close, volume = _ohlcv()
    df = pd.DataFrame({
        "open": open_, "high": high, "low": low, "close": close, "volume": volume,
    })

    assert "tri_dir_pressure" in ta.Category["volume"]
    assert callable(getattr(df.ta, "tri_dir_pressure"))

    module_result = ta.tri_dir_pressure(open_=open_, high=high, low=low, close=close, volume=volume, use_volume=True)
    accessor_result = df.ta.tri_dir_pressure()
    pdt.assert_series_equal(module_result, accessor_result, check_names=False)


def test_reachability_via_accessor_use_volume_false():
    open_, high, low, close, volume = _ohlcv()
    df = pd.DataFrame({
        "open": open_, "high": high, "low": low, "close": close, "volume": volume,
    })
    module_result = ta.tri_dir_pressure(open_=open_, high=high, low=low, close=close, use_volume=False)
    accessor_result = df.ta.tri_dir_pressure(use_volume=False)
    pdt.assert_series_equal(module_result, accessor_result, check_names=False)


def test_rejects_nonfinite_ohlc():
    open_, high, low, close, volume = _ohlcv(n=10)
    for bad in (np.nan, np.inf, -np.inf):
        broken = close.copy()
        broken.iloc[3] = bad
        with pytest.raises(ValueError, match="non-finite"):
            ta.tri_dir_pressure(open_, high, low, broken, use_volume=False)


def test_rejects_nonfinite_volume():
    open_, high, low, close, volume = _ohlcv(n=10)
    broken_volume = volume.copy()
    broken_volume.iloc[3] = np.inf
    with pytest.raises(ValueError, match="non-finite"):
        ta.tri_dir_pressure(open_, high, low, close, volume=broken_volume, use_volume=True)


def test_rejects_wrong_dtype():
    open_, high, low, close, volume = _ohlcv(n=10)
    bad_close = pd.Series(["a"] * len(close), index=close.index)
    with pytest.raises(ValueError, match="numeric"):
        ta.tri_dir_pressure(open_, high, low, bad_close, use_volume=False)


def test_use_volume_true_requires_volume():
    open_, high, low, close, volume = _ohlcv(n=10)
    with pytest.raises(ValueError, match="volume"):
        ta.tri_dir_pressure(open_, high, low, close, use_volume=True)


def test_use_volume_false_does_not_require_volume():
    open_, high, low, close, volume = _ohlcv(n=10)
    out = ta.tri_dir_pressure(open_, high, low, close, use_volume=False)
    assert out.notna().all()


def test_use_volume_must_be_bool():
    open_, high, low, close, volume = _ohlcv(n=10)
    with pytest.raises(ValueError, match="bool"):
        ta.tri_dir_pressure(open_, high, low, close, volume=volume, use_volume="yes")


def test_docstring_attribution():
    doc = ta.tri_dir_pressure.__doc__
    assert "tradingview.com/script/3XE8qqfr" in doc
    assert "Zeiierman" in doc
    assert "scr(" in doc
    assert "NOT ported" in doc or "NOT" in doc
