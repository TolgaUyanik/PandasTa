# tests/test_avwap_z.py
"""avwap_z (AVWAP_Z) -- anchored VWAP z-score + %-distance, ported from
Module 1 of "MAEM - Volume Suite" (wbrAnavm.pine), TVPTA continuation.
Self-contained on synthetic data.

Reachability tests `import pandas_ta` (`.context`), NOT
`importlib.util.spec_from_file_location` (see TODO.md TVPTA-3(c)).

Every OHLC bar below uses O=H=L=C (a flat/doji bar) specifically so the
"physically valid OHLC" requirement (low <= min(open,close) and
max(open,close) <= high, not just low <= high -- this batch's own
documented history of two prior MAJOR bugs from exactly that gap) holds
trivially by construction: with all four equal, every inequality is an
equality, so there is nothing to get wrong. The hand-computed fixture
values below were derived by hand first (see comments) and only then
checked against the function's actual output.
"""
import numpy as np
import pandas as pd
import pytest

from .context import pandas_ta as ta


def _flat_bar_frame(values, volumes, dates):
    """Builds a physically-valid OHLCV frame where every bar is flat
    (O=H=L=C=values[i]) -- see module docstring for why this trivially
    satisfies the OHLC-validity requirement."""
    idx = pd.DatetimeIndex(dates)
    v = np.asarray(values, dtype=float)
    vol = np.asarray(volumes, dtype=float)
    return (
        pd.Series(v, index=idx),  # high
        pd.Series(v, index=idx),  # low
        pd.Series(v, index=idx),  # close
        pd.Series(vol, index=idx),  # volume
    )


# ---------------------------------------------------------------------------
# (a) Hand-computed fixture -- anchor="W", 4 bars in week 1 (Mon-Thu
# 2024-01-01..04, all pandas period 2024-01-01/2024-01-07) + 1 bar the
# following Monday (2024-01-08, new period 2024-01-08/2024-01-14, forces
# a reset). Values hand-derived by cumulative-sum arithmetic (see inline
# comments), independently of the implementation.
# ---------------------------------------------------------------------------

_DATES_W = ["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04", "2024-01-08"]
_VALUES_W = [100.0, 110.0, 90.0, 100.0, 120.0]
_VOLUMES_W = [100.0, 100.0, 200.0, 100.0, 50.0]


def test_hand_computed_week_anchor_fixture():
    high, low, close, volume = _flat_bar_frame(_VALUES_W, _VOLUMES_W, _DATES_W)
    out = ta.avwap_z(high, low, close, volume, anchor="W")

    z = out["AVWAP_Z_W"]
    dist = out["AVWAP_DIST_PCT_W"]

    # bar0 (2024-01-01): first bar of the period -> n=1 -> variance == 0
    # exactly (cumPV2/cumV == vwap^2 for a single sample) -> stdev == 0 ->
    # Z is this port's explicit NaN guard (source never divides by stdev
    # at all). dist_pct = (100-100)/100*100 = 0.0 (vwap == close on a
    # single-sample period trivially).
    assert pd.isna(z.iloc[0])
    assert dist.iloc[0] == pytest.approx(0.0, abs=1e-9)

    # bar1 (2024-01-02): cumPV=100*100+110*100=21000, cumV=200,
    # vwap=105.0; cumPV2=100*100^2+100*110^2=1,000,000+1,210,000=2,210,000
    # var=2,210,000/200 - 105^2 = 11050-11025=25 -> stdev=5.0
    # z=(110-105)/5=1.0; dist=(110-105)/110*100=5/110*100
    assert z.iloc[1] == pytest.approx(1.0, abs=1e-9)
    assert dist.iloc[1] == pytest.approx(5.0 / 110.0 * 100.0, abs=1e-9)

    # bar2 (2024-01-03): cumPV=21000+90*200=39000, cumV=400, vwap=97.5;
    # cumPV2=2,210,000+200*90^2=2,210,000+1,620,000=3,830,000
    # var=3,830,000/400 - 97.5^2=9575-9506.25=68.75 -> stdev=sqrt(68.75)
    # z=(90-97.5)/sqrt(68.75); dist=(90-97.5)/90*100
    stdev2 = np.sqrt(68.75)
    assert z.iloc[2] == pytest.approx(-7.5 / stdev2, abs=1e-9)
    assert dist.iloc[2] == pytest.approx(-7.5 / 90.0 * 100.0, abs=1e-9)

    # bar3 (2024-01-04): cumPV=39000+100*100=49000, cumV=500, vwap=98.0;
    # cumPV2=3,830,000+100*100^2=4,830,000
    # var=4,830,000/500 - 98^2=9660-9604=56 -> stdev=sqrt(56)
    # z=(100-98)/sqrt(56); dist=(100-98)/100*100=2.0
    stdev3 = np.sqrt(56.0)
    assert z.iloc[3] == pytest.approx(2.0 / stdev3, abs=1e-9)
    assert dist.iloc[3] == pytest.approx(2.0, abs=1e-9)

    # bar4 (2024-01-08): NEW week period -> reset -> n=1 again -> stdev==0
    # -> z NaN, dist == 0.0 (mirrors bar0's shape exactly, confirms the
    # anchor RESET actually fired at the week boundary, not just that a
    # standalone single-sample period looks like this).
    assert pd.isna(z.iloc[4])
    assert dist.iloc[4] == pytest.approx(0.0, abs=1e-9)


# ---------------------------------------------------------------------------
# THE n=2 CASE (Fletcher round 1, MAJOR; formula CORRECTED round 2, also
# MAJOR) -- Z on a period's 2nd bar is UNBOUNDED. On a FLAT bar (close ==
# hlc3), the closed form reduces to Z = sign(p2-p1) * sqrt(v1/v2); on a
# NON-flat bar it does not (see the two-term formula in avwap_z.py's
# module docstring, and the dedicated non-flat test just below this one).
# Pinned directly, not just asserted qualitatively.
# ---------------------------------------------------------------------------

def test_second_bar_of_period_z_is_unbounded_by_volume_ratio():
    # FLAT bar (O=H=L=C=110), so close == hlc3 and the reduced formula
    # applies exactly: v1=10000, v2=100 -> Z = sign(p2-p1) * sqrt(10000/100)
    # = sign * 10.0. p2 > p1 (110 > 100) -> sign=+1 -> Z = +10.0 exactly.
    # This is the DEGENERATE special case of the general two-term formula
    # (the second term vanishes identically when c2 == p2) -- see
    # test_second_bar_z_full_formula_on_non_flat_bar below for the general
    # case, where this reduction does NOT hold and this simpler formula
    # alone would be wrong.
    dates = ["2024-01-01", "2024-01-02"]  # same week (Mon, Tue)
    values = [100.0, 110.0]
    volumes = [10000.0, 100.0]
    high, low, close, volume = _flat_bar_frame(values, volumes, dates)
    out = ta.avwap_z(high, low, close, volume, anchor="W")
    z1 = out["AVWAP_Z_W"].iloc[1]
    assert z1 == pytest.approx(10.0, abs=1e-9), (
        "closed-form n=2 case on a FLAT 2nd bar: Z(2nd bar) = "
        "sign(p2-p1) * sqrt(v1/v2) = sqrt(10000/100) = 10.0 -- if this "
        "drifts, the n=2 derivation in avwap_z.py's module docstring is "
        "now wrong and must be re-checked"
    )
    assert abs(z1) > 9, "must be genuinely large, not just nonzero -- this is the MAJOR the fix documents"


def test_second_bar_z_full_formula_on_non_flat_bar():
    # Fletcher round 2, MAJOR: round 1's formula (sign(p2-p1)*sqrt(v1/v2))
    # is only correct when the 2nd bar is FLAT (close == hlc3, tested
    # above). On a NON-flat bar it is wrong, because Z divides by `close`,
    # not `typical_price`. Bar0 flat (p1=100, v1=10000). Bar1 NON-flat:
    # H=120, L=105, C=110 -> hlc3 = p2 = (120+105+110)/3 = 335/3 =
    # 111.6666...  (!= close=110), v2=100.
    #
    # Hand-derived via the corrected closed form (see avwap_z.py's module
    # docstring "THE n=2 CASE" for the full derivation):
    #   vwap  = (p1*v1 + p2*v2) / (v1+v2)
    #         = (100*10000 + (335/3)*100) / 10100
    #   stdev = |p1-p2| * sqrt(v1*v2) / (v1+v2)
    #         = |100 - 335/3| * sqrt(10000*100) / 10100
    #   Z     = (c2 - vwap) / stdev
    #         = sign(p2-p1)*sqrt(v1/v2)
    #           + (c2-p2)*(v1+v2)/(|p2-p1|*sqrt(v1*v2))
    # Computed by hand (as a calculator, independent of calling avwap_z):
    #   Z = 8.557142857142853
    # The round-1 (flat-bar-only) formula would instead predict
    # sign(p2-p1)*sqrt(v1/v2) = sign(+11.667)*sqrt(100) = +10.0 -- a
    # materially different, WRONG number for this bar.
    dates = ["2024-01-01", "2024-01-02"]
    idx = pd.DatetimeIndex(dates)
    high = pd.Series([100.0, 120.0], index=idx)
    low = pd.Series([100.0, 105.0], index=idx)
    close = pd.Series([100.0, 110.0], index=idx)
    volume = pd.Series([10000.0, 100.0], index=idx)
    out = ta.avwap_z(high, low, close, volume, anchor="W")
    z1 = out["AVWAP_Z_W"].iloc[1]
    assert z1 == pytest.approx(8.557142857142857, abs=1e-9), (
        "the corrected two-term n=2 formula must hold on a NON-flat bar, "
        "where close != hlc3 -- the round-1 flat-bar-only formula would "
        "predict 10.0 here, which is wrong"
    )
    assert z1 != pytest.approx(10.0, abs=0.1), (
        "must NOT match the round-1 (flat-bar-only, WRONG on this bar) formula"
    )


def test_second_bar_z_flips_sign_with_price_direction():
    # Same volume ratio, price direction reversed (p2 < p1) -> Z negative.
    dates = ["2024-01-01", "2024-01-02"]
    values = [110.0, 100.0]
    volumes = [10000.0, 100.0]
    high, low, close, volume = _flat_bar_frame(values, volumes, dates)
    out = ta.avwap_z(high, low, close, volume, anchor="W")
    assert out["AVWAP_Z_W"].iloc[1] == pytest.approx(-10.0, abs=1e-9)


def test_min_samples_masks_the_n2_blowup_when_opted_in():
    # Same fixture as the pin test above (Z(bar1) = +10.0 with
    # min_samples unset/None) -- with min_samples=3, bar1 has only 2
    # accumulated samples (< 3), so it must be masked to NaN too, not
    # just bar0 (which is already NaN via the stdev==0 guard regardless).
    dates = ["2024-01-01", "2024-01-02"]
    values = [100.0, 110.0]
    volumes = [10000.0, 100.0]
    high, low, close, volume = _flat_bar_frame(values, volumes, dates)
    out_default = ta.avwap_z(high, low, close, volume, anchor="W")
    out_masked = ta.avwap_z(high, low, close, volume, anchor="W", min_samples=3)
    assert out_default["AVWAP_Z_W"].iloc[1] == pytest.approx(10.0, abs=1e-9)
    assert pd.isna(out_masked["AVWAP_Z_W"].iloc[1])
    assert pd.isna(out_masked["AVWAP_Z_W"].iloc[0])
    # DIST_PCT is deliberately NEVER masked by min_samples -- no numerical
    # degeneracy at small n for a price ratio, see the docstring.
    pd.testing.assert_series_equal(
        out_default["AVWAP_DIST_PCT_W"], out_masked["AVWAP_DIST_PCT_W"], check_names=False,
    )


def test_min_samples_none_default_is_pine_parity_no_change():
    high, low, close, volume = _flat_bar_frame(_VALUES_W, _VOLUMES_W, _DATES_W)
    out_default = ta.avwap_z(high, low, close, volume, anchor="W")
    out_explicit_none = ta.avwap_z(high, low, close, volume, anchor="W", min_samples=None)
    pd.testing.assert_frame_equal(out_default, out_explicit_none)


def test_invalid_min_samples_raises():
    high, low, close, volume = _flat_bar_frame(_VALUES_W, _VOLUMES_W, _DATES_W)
    with pytest.raises(ValueError, match="min_samples"):
        ta.avwap_z(high, low, close, volume, anchor="W", min_samples=0)
    with pytest.raises(ValueError, match="min_samples"):
        ta.avwap_z(high, low, close, volume, anchor="W", min_samples=2.5)
    with pytest.raises(ValueError, match="min_samples"):
        ta.avwap_z(high, low, close, volume, anchor="W", min_samples="3")


def test_week_anchor_resets_cumulants_not_carried_across_boundary():
    # Regression-shaped check for the reset itself: if bar4's cumulants
    # were NOT reset (i.e. the bug this port must avoid: carrying week 1's
    # accumulation into week 2), vwap at bar4 would sit near 98-100 (drawn
    # toward the whole history), not exactly 120.0 (bar4's own single
    # value). Recover vwap indirectly via dist_pct==0 => vwap==close==120.
    high, low, close, volume = _flat_bar_frame(_VALUES_W, _VOLUMES_W, _DATES_W)
    out = ta.avwap_z(high, low, close, volume, anchor="W")
    assert out["AVWAP_DIST_PCT_W"].iloc[4] == pytest.approx(0.0, abs=1e-9)


# ---------------------------------------------------------------------------
# "D" anchor degenerates on one-bar-per-day data -- documented in the
# docstring as the reason the default is "W" not "D" (deviating from
# `pandas_ta.overlap.vwap`'s own "D" default). This is the direct proof.
# ---------------------------------------------------------------------------

def test_day_anchor_degenerates_to_all_nan_z_on_daily_bars():
    dates = pd.date_range("2024-01-01", periods=10, freq="B")
    values = 100 + np.cumsum(np.random.RandomState(3).randn(10))
    high, low, close, volume = _flat_bar_frame(values, np.full(10, 100.0), dates)
    out = ta.avwap_z(high, low, close, volume, anchor="D")
    assert out["AVWAP_Z_D"].isna().all()
    # dist_pct is still well-defined (vwap == close on every single-bar
    # "period") and trivially ~zero throughout -- np.isclose, not exact
    # ==0.0: vwap is recovered as ref + mean_deviation (see the
    # numerical-stability comment in avwap_z.py), so on a single-sample
    # period it is `ref + 0/vol`, which floating-point division can land
    # a few ULPs off `ref` itself (observed ~1e-14 magnitude).
    assert np.allclose(out["AVWAP_DIST_PCT_D"].to_numpy(), 0.0, atol=1e-9)


def test_default_anchor_is_week_not_day():
    dates = pd.date_range("2024-01-01", periods=10, freq="B")
    values = 100 + np.cumsum(np.random.RandomState(3).randn(10))
    high, low, close, volume = _flat_bar_frame(values, np.full(10, 100.0), dates)
    out_default = ta.avwap_z(high, low, close, volume)
    out_week = ta.avwap_z(high, low, close, volume, anchor="W")
    pd.testing.assert_frame_equal(out_default, out_week)
    # And explicitly NOT degenerate like "D" would be -- at least one
    # non-NaN Z value once a period accumulates >1 bar.
    assert out_default["AVWAP_Z_W"].notna().any()


# ---------------------------------------------------------------------------
# (b) Causality -- mutation and deletion after time t must not change
# output at/before t.
# ---------------------------------------------------------------------------

def _random_ohlcv(n=120, seed=11):
    rng = np.random.RandomState(seed)
    close_v = 100 + np.cumsum(rng.randn(n) * 0.7)
    high_v = close_v + np.abs(rng.randn(n)) * 0.5
    low_v = close_v - np.abs(rng.randn(n)) * 0.5
    open_v = close_v - rng.randn(n) * 0.2
    high_v = np.maximum.reduce([high_v, open_v, close_v])
    low_v = np.minimum.reduce([low_v, open_v, close_v])
    vol_v = np.abs(rng.randn(n)) * 100 + 10
    idx = pd.date_range("2024-01-01", periods=n, freq="B")
    assert (low_v <= np.minimum(open_v, close_v)).all(), "construction check: low must be <= min(open, close)"
    assert (np.maximum(open_v, close_v) <= high_v).all(), "construction check: max(open, close) must be <= high"
    return (
        pd.Series(high_v, index=idx), pd.Series(low_v, index=idx),
        pd.Series(close_v, index=idx), pd.Series(vol_v, index=idx),
    )


def test_causal_no_lookahead():
    high, low, close, volume = _random_ohlcv()
    out_before = ta.avwap_z(high, low, close, volume, anchor="W")
    assert out_before["AVWAP_Z_W"].notna().sum() > 0, "test data must actually produce non-NaN Z values"

    t = 80
    high_mut, low_mut, close_mut, volume_mut = high.copy(), low.copy(), close.copy(), volume.copy()
    high_mut.iloc[t + 1:] *= 1.6
    low_mut.iloc[t + 1:] *= 0.6
    close_mut.iloc[t + 1:] *= 1.3
    volume_mut.iloc[t + 1:] *= 5.0
    out_after = ta.avwap_z(high_mut, low_mut, close_mut, volume_mut, anchor="W")

    pd.testing.assert_frame_equal(out_before.iloc[: t + 1], out_after.iloc[: t + 1])


def test_causal_deletion_no_lookahead():
    high, low, close, volume = _random_ohlcv()
    t = 80
    out_full = ta.avwap_z(high, low, close, volume, anchor="W")
    out_trunc = ta.avwap_z(
        high.iloc[: t + 1], low.iloc[: t + 1], close.iloc[: t + 1], volume.iloc[: t + 1], anchor="W",
    )
    pd.testing.assert_frame_equal(out_full.iloc[: t + 1], out_trunc)


# ---------------------------------------------------------------------------
# (c) Reachability
# ---------------------------------------------------------------------------

def test_reachable_in_category_and_callable():
    assert "avwap_z" in ta.Category["volume"]
    df = pd.DataFrame({
        "high": [1.0], "low": [1.0], "close": [1.0], "volume": [1.0],
    }, index=pd.date_range("2024-01-01", periods=1))
    assert callable(getattr(df.ta, "avwap_z"))


def test_accessor_matches_direct_call():
    high, low, close, volume = _flat_bar_frame(_VALUES_W, _VOLUMES_W, _DATES_W)
    df = pd.DataFrame({"high": high, "low": low, "close": close, "volume": volume})
    via_accessor = df.ta.avwap_z(anchor="W")
    direct = ta.avwap_z(high, low, close, volume, anchor="W")
    pd.testing.assert_frame_equal(via_accessor, direct)


# ---------------------------------------------------------------------------
# (d) Scale-free
# ---------------------------------------------------------------------------

def test_scale_invariant_under_price_rescale():
    # Not byte-identical (assert_frame_equal(..., check_exact=True) would
    # be too strong a claim): both AVWAP_Z and AVWAP_DIST_PCT are exact
    # ratios ALGEBRAICALLY, but Z's denominator (`stdev`) is built from a
    # sum-of-squares subtraction that loses a few ULPs differently at
    # different absolute price scales (see the numerical-stability
    # comment in avwap_z.py). Measured directly on THIS fixture at k=1000:
    # max |Z(1x)-Z(1000x)| = 7.91e-13, max |DIST_PCT| diff = 3.48e-14
    # (Fletcher round 2 MINOR: the Z figure here previously read 2.87e-13,
    # did not reproduce on re-measurement; corrected) --
    # rtol=1e-9/atol=1e-11 below has real margin against those (not the
    # rtol/atol=1e-6 this test used before Fletcher round 1, which was ~6
    # orders of magnitude looser than the actual measured error and would
    # have passed a formula a million times worse than this one). NaN
    # positions are checked separately and exactly (`check_exact` on the
    # numeric comparison does not relax where a value is/isn't NaN, but a
    # dedicated boolean-mask assertion has more signal on failure).
    high, low, close, volume = _random_ohlcv()
    out = ta.avwap_z(high, low, close, volume, anchor="W")
    out_x1000 = ta.avwap_z(high * 1000, low * 1000, close * 1000, volume, anchor="W")
    pd.testing.assert_series_equal(out["AVWAP_Z_W"].isna(), out_x1000["AVWAP_Z_W"].isna())
    pd.testing.assert_frame_equal(out, out_x1000, check_exact=False, rtol=1e-9, atol=1e-11)


def test_scale_invariant_under_volume_rescale():
    # Measured directly on THIS fixture at m=50: max |Z| diff 1.25e-14,
    # max |DIST_PCT| diff 1.38e-14 -- same tightened tolerance as the
    # price-rescale test above, for the same reason.
    high, low, close, volume = _random_ohlcv()
    out = ta.avwap_z(high, low, close, volume, anchor="W")
    out_x50 = ta.avwap_z(high, low, close, volume * 50, anchor="W")
    pd.testing.assert_series_equal(out["AVWAP_Z_W"].isna(), out_x50["AVWAP_Z_W"].isna())
    pd.testing.assert_frame_equal(out, out_x50, check_exact=False, rtol=1e-9, atol=1e-11)


# ---------------------------------------------------------------------------
# Columns / naming
# ---------------------------------------------------------------------------

def test_columns_and_naming():
    high, low, close, volume = _flat_bar_frame(_VALUES_W, _VOLUMES_W, _DATES_W)
    out = ta.avwap_z(high, low, close, volume, anchor="M")
    assert set(out.columns) == {"AVWAP_Z_M", "AVWAP_DIST_PCT_M"}
    assert out.name == "AVWAP_Z_M"


def test_anchor_case_insensitive():
    high, low, close, volume = _flat_bar_frame(_VALUES_W, _VOLUMES_W, _DATES_W)
    out_lower = ta.avwap_z(high, low, close, volume, anchor="w")
    out_upper = ta.avwap_z(high, low, close, volume, anchor="W")
    pd.testing.assert_frame_equal(out_lower, out_upper)


# ---------------------------------------------------------------------------
# Input validation -- explicit ValueError, not silent coercion (this
# batch's documented convention: liquidity_sweep's `mode`, bpress's
# `length`, etc.)
# ---------------------------------------------------------------------------

def test_invalid_anchor_raises():
    high, low, close, volume = _flat_bar_frame(_VALUES_W, _VOLUMES_W, _DATES_W)
    with pytest.raises(ValueError, match="anchor"):
        ta.avwap_z(high, low, close, volume, anchor="Y")


def test_non_string_anchor_raises():
    high, low, close, volume = _flat_bar_frame(_VALUES_W, _VOLUMES_W, _DATES_W)
    with pytest.raises(ValueError, match="anchor"):
        ta.avwap_z(high, low, close, volume, anchor=123)


def test_non_datetime_index_raises():
    n = 10
    values = np.full(n, 100.0)
    idx = pd.RangeIndex(n)
    high = pd.Series(values, index=idx)
    low = pd.Series(values, index=idx)
    close = pd.Series(values, index=idx)
    volume = pd.Series(np.full(n, 100.0), index=idx)
    with pytest.raises(ValueError, match="DatetimeIndex"):
        ta.avwap_z(high, low, close, volume, anchor="W")


def test_unordered_datetime_index_raises():
    # Fletcher round 1, MAJOR: a DatetimeIndex that is present but NOT
    # sorted ascending previously passed straight through (only the TYPE
    # was checked, not the ORDER) and silently produced non-causal
    # results, because groupby(periods).cumsum()/.transform("first") both
    # follow ROW order, not TIME order. `_random_ohlcv()` is already
    # sorted by construction (pd.date_range), so this shuffles it via
    # .sample(frac=1) -- same DatetimeIndex dtype, same set of
    # timestamps, just out of chronological order -- to prove the type
    # check alone (which every OTHER test in this file exercises via a
    # sorted frame, and therefore could never catch this gap) is not
    # sufficient.
    high, low, close, volume = _random_ohlcv()
    rng = np.random.RandomState(99)
    order = rng.permutation(len(close))
    high_s, low_s, close_s, volume_s = high.iloc[order], low.iloc[order], close.iloc[order], volume.iloc[order]
    assert isinstance(close_s.index, pd.DatetimeIndex)
    assert not close_s.index.is_monotonic_increasing, "construction check: must actually be unsorted"
    with pytest.raises(ValueError, match="order"):
        ta.avwap_z(high_s, low_s, close_s, volume_s, anchor="W")


def test_interior_shuffle_with_endpoints_preserved_still_raises():
    # Fletcher round 2, MAJOR: round 1's guard used `is_datetime_ordered`,
    # which is `index[0] < index[-1]` -- an ENDPOINT comparison only. A
    # shuffle that swaps two ADJACENT MIDDLE rows (leaving the first and
    # last timestamps untouched) passes that check and silently returns
    # non-causal output. This test constructs EXACTLY that case -- proof
    # the seed-99 full-permutation test above is not sufficient on its
    # own (it happens to also break the endpoint check, by luck of that
    # particular seed) and that this shuffle specifically defeats the
    # weaker check while `index.is_monotonic_increasing` (the round-2 fix)
    # still catches it.
    high, low, close, volume = _random_ohlcv()
    order = np.arange(len(close))
    order[40], order[41] = order[41], order[40]  # swap two adjacent interior rows only
    high_s, low_s, close_s, volume_s = high.iloc[order], low.iloc[order], close.iloc[order], volume.iloc[order]
    assert close_s.index[0] == close.index[0] and close_s.index[-1] == close.index[-1], (
        "construction check: endpoints must be UNCHANGED -- this is the case "
        "the endpoint-only is_datetime_ordered check cannot detect"
    )
    assert not close_s.index.is_monotonic_increasing, "construction check: must actually be unsorted"
    with pytest.raises(ValueError, match="order"):
        ta.avwap_z(high_s, low_s, close_s, volume_s, anchor="W")


def test_single_row_frame_does_not_raise():
    # Fletcher round 2, MINOR: the round-1 endpoint-only guard
    # (`index[0] < index[-1]`) rejected a valid 1-row frame, since
    # index[0] == index[-1] trivially fails a strict `<` comparison --
    # silently dropping the AVWAP columns downstream (indicator_engine.py
    # wraps every call in a bare try/except). `is_monotonic_increasing`
    # is True for a length-1 index by definition, so this must NOT raise
    # and must return the documented degenerate row (Z NaN via the
    # stdev==0 guard, DIST_PCT ~= 0.0).
    idx = pd.DatetimeIndex(["2024-01-01"])
    high = pd.Series([100.0], index=idx)
    low = pd.Series([100.0], index=idx)
    close = pd.Series([100.0], index=idx)
    volume = pd.Series([1000.0], index=idx)
    out = ta.avwap_z(high, low, close, volume, anchor="W")
    assert list(out.columns) == ["AVWAP_Z_W", "AVWAP_DIST_PCT_W"]
    assert pd.isna(out["AVWAP_Z_W"].iloc[0])
    assert out["AVWAP_DIST_PCT_W"].iloc[0] == pytest.approx(0.0, abs=1e-9)


def test_negative_cumulative_volume_maps_to_nan_not_finite_garbage():
    # NIT: Pine's guard is `cumV > 0 ? ... : na`, which also treats a
    # NEGATIVE cumV as na, not just a zero one. Not reachable with a real
    # OHLCV feed (volume is never negative in practice), but cheap to
    # honor exactly rather than let `.replace(0.0, nan)` leave a negative
    # cumV to produce finite (garbage) output instead.
    dates = ["2024-01-01", "2024-01-02", "2024-01-03"]
    values = [100.0, 100.0, 105.0]
    volumes = [-50.0, 40.0, 100.0]  # cumV: -50, -10, 90 -- first two bars negative
    high, low, close, volume = _flat_bar_frame(values, volumes, dates)
    out = ta.avwap_z(high, low, close, volume, anchor="W")
    assert pd.isna(out["AVWAP_Z_W"].iloc[0])
    assert pd.isna(out["AVWAP_DIST_PCT_W"].iloc[0])
    assert pd.isna(out["AVWAP_Z_W"].iloc[1])
    assert pd.isna(out["AVWAP_DIST_PCT_W"].iloc[1])


def test_none_anchor_uses_documented_default():
    high, low, close, volume = _flat_bar_frame(_VALUES_W, _VOLUMES_W, _DATES_W)
    out_none = ta.avwap_z(high, low, close, volume, anchor=None)
    out_omitted = ta.avwap_z(high, low, close, volume)
    out_explicit_w = ta.avwap_z(high, low, close, volume, anchor="W")
    pd.testing.assert_frame_equal(out_none, out_omitted)
    pd.testing.assert_frame_equal(out_none, out_explicit_w)


# ---------------------------------------------------------------------------
# Zero-volume handling -- cumV == 0 must propagate to NaN, not raise or
# divide-by-zero-warn.
# ---------------------------------------------------------------------------

def test_zero_volume_bar_propagates_nan_not_error():
    dates = ["2024-01-01", "2024-01-02", "2024-01-03"]
    values = [100.0, 100.0, 105.0]
    volumes = [0.0, 0.0, 100.0]
    high, low, close, volume = _flat_bar_frame(values, volumes, dates)
    out = ta.avwap_z(high, low, close, volume, anchor="W")
    # first two bars: cumV == 0 throughout -> vwap/variance/stdev all NaN
    # by the `cumV > 0 ? ... : na` guard -> Z and DIST_PCT both NaN.
    assert pd.isna(out["AVWAP_Z_W"].iloc[0])
    assert pd.isna(out["AVWAP_DIST_PCT_W"].iloc[0])
    assert pd.isna(out["AVWAP_Z_W"].iloc[1])
    assert pd.isna(out["AVWAP_DIST_PCT_W"].iloc[1])
    # third bar: cumV becomes 100 for the first time (n=1 sample) -> same
    # single-sample degenerate shape as bar0 in the main fixture.
    assert pd.isna(out["AVWAP_Z_W"].iloc[2])
    assert out["AVWAP_DIST_PCT_W"].iloc[2] == pytest.approx(0.0, abs=1e-9)
