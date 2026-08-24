# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.trend.dtdb` -- Double Top / Double Bottom (DTDB).

What this file is built around:

* A HAND-DERIVED double-top fixture whose neckline (99.5), apex (107.5),
  measured target (91.5) and every event bar were computed on paper from
  the price path BEFORE the module was run, then asserted exactly.

* TWO CAUSALITY MUTANTS, each an `importlib` + `exec` copy of the REAL
  module source with one write site moved from the event bar `j` to the
  pattern's own `apex_bar` -- i.e. exactly the back-dating hazard for a
  chart pattern. Both are PERTURBING mutants, not unsatisfiable ones:
  they move a value rather than deleting it, and the total fire count is
  asserted EQUAL between real and mutant so that "the mutant broke the
  column" can never be mistaken for "the mutant leaked". A bare
  prefix-truncation test cannot detect back-dating -- truncating before
  the confirmation stops the mutant writing at all -- so the detector is
  a REAL-vs-MUTANT table comparing each module's FULL run against its
  OWN truncated run.

* NaN masks are compared explicitly and values are compared only on
  co-populated (finite-in-both) cells, so warm-up NaNs can never be
  counted as agreement or as disagreement.
"""
import importlib
import types

import numpy as np
import pandas as pd
import pytest

from .context import pandas_ta as ta
from pandas_ta.trend.dtdb import dtdb
from pandas_ta.volatility.atr import atr as _atr


# ---------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------
def _frame(closes):
    """close-driven OHLC with a symmetric 1.0-wide bar, so `high` and
    `low` pivots are exactly `close +- 0.5` and hand-derivable."""
    c = [float(x) for x in closes]
    return pd.DataFrame({"open": c,
                         "high": [x + 0.5 for x in c],
                         "low": [x - 0.5 for x in c],
                         "close": c})


def _double_top():
    """A single, deliberate double top with NOTHING before it.

    Bars 0-4   flat at 107  -> rightmost-tie pivot HIGH at bar 4 (107.5)
    Bars 5-11  106..100     -> pivot LOW at bar 11 (99.5)   = the NECKLINE
    Bars 12-18 101..107     -> pivot HIGH at bar 18 (107.5) = the APEX bar
    Bars 19-37 106..88      -> breaks the neckline, then runs to target
    Bars 38-45 flat at 88

    The series opens on a HIGH pivot on purpose. An earlier draft opened
    flat at 100 and rose first, which made the first three pivots
    LOW-HIGH-LOW: a DOUBLE BOTTOM matched first and then blocked the
    double top via `f_regionTaken`. That is correct ported behaviour, not
    a bug, but it makes a useless double-top fixture.

    Hand-derived, all BEFORE running the module:
        neck   = 99.5           (the pivot low)
        apex   = (107.5 + 107.5) / 2 = 107.5
        height = apex - neck = 8.0
        target = neck - height = 91.5
    """
    c = [107.0] * 5 + [106, 105, 104, 103, 102, 101, 100] \
        + [101, 102, 103, 104, 105, 106, 107] \
        + [107 - i for i in range(1, 20)] + [88.0] * 8
    return _frame(c)


NECK, APEX, TARGET = 99.5, 107.5, 91.5
BORN_BAR, CONF_BAR, RESOLVE_BAR = 21, 26, 33
P3 = dict(pivots=3)
_S = "_3_0.5_0.15"
BEAR, BULL = f"DTDB_CONF_BEAR{_S}", f"DTDB_CONF_BULL{_S}"
TGT, PEND, RES = f"DTDB_TGT_PCT{_S}", f"DTDB_PEND{_S}", f"DTDB_RES{_S}"


def _noise(seed=11, n=900, drift=0.0):
    rng = np.random.default_rng(seed)
    c = 100 * np.exp(np.cumsum(rng.normal(drift, 0.011, n)))
    h = c * (1 + abs(rng.normal(0, 0.005, n)))
    l = c * (1 - abs(rng.normal(0, 0.005, n)))
    return pd.DataFrame({"open": c, "high": h, "low": l, "close": c})


# ---------------------------------------------------------------------
# shape / registration -- the 5 touch points
# ---------------------------------------------------------------------
def test_column_names_and_category():
    r = dtdb(_double_top().high, _double_top().low, _double_top().close, **P3)
    assert list(r.columns) == [BEAR, BULL, TGT, PEND, RES]
    assert r.name == f"DTDB{_S}"
    assert r.category == "trend"


def test_default_props_suffix():
    df = _noise(n=400)
    r = dtdb(df.high, df.low, df.close)
    assert r.name == "DTDB_8_0.5_0.15"
    assert "DTDB_CONF_BEAR_8_0.5_0.15" in r.columns


def test_registered_in_category_dict():
    assert "dtdb" in ta.Category["trend"]


def test_dataframe_accessor_matches_direct_call():
    df = _double_top()
    direct = dtdb(df.high, df.low, df.close, **P3)
    d = df.copy()
    d.columns = [c.lower() for c in d.columns]
    via = d.ta.dtdb(**P3)
    pd.testing.assert_frame_equal(direct, via)


# ---------------------------------------------------------------------
# correctness vs the Pine source, hand-derived
# ---------------------------------------------------------------------
def test_hand_derived_double_top_confirms_on_the_neckline_break_bar():
    """The confirmation bar is NOT chosen by the module here: it is the
    first bar whose close falls below `neck - atr * buf_atr`, computed
    independently from the same fixture."""
    df = _double_top()
    r = dtdb(df.high, df.low, df.close, **P3)
    a = _atr(df.high, df.low, df.close, length=14)
    buf = a * 0.15
    breaks = np.where(df.close.to_numpy() < (NECK - buf).to_numpy())[0]
    assert breaks[0] == CONF_BAR
    assert r[BEAR].iloc[CONF_BAR] == 1.0
    assert r[BEAR].sum() == 1.0
    assert r[BULL].sum() == 0.0


def test_pattern_is_pending_between_birth_and_confirmation():
    """`PEND` is -1 (one live double top) from the bar the third pivot
    confirms until the bar the neckline breaks, and 0 outside."""
    df = _double_top()
    r = dtdb(df.high, df.low, df.close, **P3)
    p = r[PEND]
    assert (p.iloc[BORN_BAR:CONF_BAR] == -1.0).all()
    assert p.iloc[BORN_BAR - 1] == 0.0
    assert p.iloc[CONF_BAR] == 0.0
    assert (p.iloc[CONF_BAR:] == 0.0).all()


def test_measured_target_is_the_projected_height_as_a_ratio():
    """target = neck - (apex - neck); the column publishes it as
    |target - close| / close on the break bar. Hand value, not read back
    from the module."""
    df = _double_top()
    r = dtdb(df.high, df.low, df.close, **P3)
    close_at_break = df.close.iloc[CONF_BAR]
    expected = abs(TARGET - close_at_break) / close_at_break
    assert expected == pytest.approx(0.07575757575757576, abs=1e-15)
    assert r[TGT].iloc[CONF_BAR] == pytest.approx(expected, abs=1e-15)
    assert (r[TGT].drop(index=CONF_BAR).fillna(0) == 0.0).all()


def test_outcome_fires_on_the_first_bar_the_low_reaches_the_target():
    df = _double_top()
    r = dtdb(df.high, df.low, df.close, **P3)
    lows = df.low.to_numpy()
    first = np.where(lows[CONF_BAR + 1:] <= TARGET)[0][0] + CONF_BAR + 1
    assert first == RESOLVE_BAR
    assert r[RES].iloc[RESOLVE_BAR] == 1.0
    assert r[RES].sum() == 1.0


def test_target_price_is_never_emitted():
    """Scale-free discipline: no column may carry the 91.5 target level
    (nor the 99.5 neckline nor the 107.5 apex)."""
    df = _double_top()
    r = dtdb(df.high, df.low, df.close, **P3)
    v = r.to_numpy(dtype=float)
    v = v[np.isfinite(v)]
    for level in (TARGET, NECK, APEX):
        assert not np.any(np.isclose(v, level))


def test_equal_tops_tolerance_is_load_bearing():
    """Raise the second peak well past `tol = atr * 0.5` and the shape
    test must reject it -- no pattern, therefore no confirmation."""
    c = [107.0] * 5 + [106, 105, 104, 103, 102, 101, 100] \
        + [102, 104, 106, 108, 110, 112, 114] \
        + [114 - 2 * i for i in range(1, 20)] + [76.0] * 8
    d = _frame(c)
    r = dtdb(d.high, d.low, d.close, **P3)
    assert r[BEAR].sum() == 0.0
    assert (r[PEND].fillna(0) == 0.0).all()


def test_minimum_depth_is_load_bearing():
    """`min(h1, h2) - l1 > 1.5 * tol` (Pine L209, the DT shape test): a double top whose
    trough is a scratch rather than a real retracement is rejected.

    The gate is isolated by moving `tol_atr`, not the price path, so that
    ONLY this inequality changes: the equal-tops test `|h1 - h2| <= tol`
    passes trivially either way (the two peaks are exactly equal here),
    the break buffer is a separate parameter, and the void tolerance
    stays far above the path's high.

    Hand-derived flip point: depth = apex - neck = 107.5 - 99.5 = 8.0,
    and ATR at the match bar (21) is 1.45388365538473, so the gate turns
    over at tol_atr = 8.0 / (1.5 * 1.45388365538473) = 3.6683357...
    tol_atr = 3.0 must still fire; tol_atr = 4.0 must not.
    """
    df = _double_top()
    a = _atr(df.high, df.low, df.close, length=14)
    flip = 8.0 / (1.5 * a.iloc[BORN_BAR])
    assert flip == pytest.approx(3.6683357114445405, abs=1e-12)
    below = dtdb(df.high, df.low, df.close, tol_atr=3.0, **P3)
    above = dtdb(df.high, df.low, df.close, tol_atr=4.0, **P3)
    assert below["DTDB_CONF_BEAR_3_3.0_0.15"].sum() == 1.0
    assert above["DTDB_CONF_BEAR_3_4.0_0.15"].sum() == 0.0


def test_weaker_mode_rejects_a_higher_second_peak():
    """`dbl_mode="weaker"` adds `h2 <= h1 + tol * 0.25` (Pine L209, the DT shape test)."""
    c = [107.0] * 5 + [106, 105, 104, 103, 102, 101, 100] \
        + [101, 102, 103, 104, 105, 106, 107.6] \
        + [107.6 - i for i in range(1, 20)] + [88.0] * 8
    d = _frame(c)
    assert dtdb(d.high, d.low, d.close, dbl_mode="any", **P3)[BEAR].sum() == 1.0
    assert dtdb(d.high, d.low, d.close, dbl_mode="weaker", **P3)[BEAR].sum() == 0.0


def test_max_wait_voids_a_pattern_that_never_breaks():
    """A pattern whose neckline is never broken is dropped after
    `max_wait` bars -- PEND must return to 0 and stay there."""
    c = [107.0] * 5 + [106, 105, 104, 103, 102, 101, 100] \
        + [101, 102, 103, 104, 105, 106, 107] + [104.0] * 60
    d = _frame(c)
    r = dtdb(d.high, d.low, d.close, max_wait=10, **P3)
    p = r[PEND].fillna(0).to_numpy()
    assert p[BORN_BAR] == -1.0
    assert p[BORN_BAR + 10] == -1.0
    assert p[BORN_BAR + 11] == 0.0
    assert r[BEAR].sum() == 0.0


def test_void_past_the_extreme_discards_the_pattern():
    """Price running above `ext + vtol` kills a forming double top
    (Pine L345), and does so long before `max_wait` would.

    The spike is deliberately delayed to bars 22+: an earlier draft
    spiked from bar 19, which voided the pattern on the very bar it was
    born, so `PEND` never showed -1 and the test proved nothing about
    the void branch as opposed to the birth branch.
    """
    c = [107.0] * 5 + [106, 105, 104, 103, 102, 101, 100] \
        + [101, 102, 103, 104, 105, 106, 107] + [106, 105, 104] \
        + [110, 115, 120, 125, 130] + [130.0] * 10
    d = _frame(c)
    r = dtdb(d.high, d.low, d.close, max_wait=200, **P3)
    p = r[PEND].fillna(0).to_numpy()
    assert p[BORN_BAR] == -1.0        # born and still pending
    assert p[BORN_BAR + 1] == 0.0     # first bar above ext + vtol: voided
    assert (p[BORN_BAR + 1:] == 0.0).all()
    assert r[BEAR].sum() == 0.0


def test_wick_mode_confirms_where_close_mode_does_not():
    """`mode="wick"` tests the bar's LOW against the neckline instead of
    its close (Pine L347 bear / L352 bull) -- a spike through that closes back must
    confirm in wick mode and not in close mode."""
    c = [107.0] * 5 + [106, 105, 104, 103, 102, 101, 100] \
        + [101, 102, 103, 104, 105, 106, 107] + [105.0, 103.0, 101.0] \
        + [100.5] * 30
    d = _frame(c)
    # widen only the spike bar's low, deep through the neckline
    d.loc[24, "low"] = 96.0
    assert dtdb(d.high, d.low, d.close, **P3)[BEAR].sum() == 0.0
    assert dtdb(d.high, d.low, d.close, mode="wick", **P3)[BEAR].sum() == 1.0


def test_double_bottom_is_the_mirror():
    """The same path inverted around 100 must produce exactly one
    DOUBLE BOTTOM and no double top."""
    c = [107.0] * 5 + [106, 105, 104, 103, 102, 101, 100] \
        + [101, 102, 103, 104, 105, 106, 107] \
        + [107 - i for i in range(1, 20)] + [88.0] * 8
    inv = [200.0 - x for x in c]
    d = _frame(inv)
    r = dtdb(d.high, d.low, d.close, **P3)
    assert r[BULL].sum() == 1.0
    assert r[BEAR].sum() == 0.0
    assert r[BULL].iloc[CONF_BAR] == 1.0


def test_region_taken_blocks_an_overlapping_second_pattern():
    """`f_regionTaken` (Pine L139-153) admits ONE pattern per region.
    A path whose first three pivots are LOW-HIGH-LOW matches a double
    BOTTOM, which then blocks the double TOP its next pivot would form.
    This is the exact mechanism whose H&S half was deliberately NOT
    ported -- pinned here so the divergence stays visible."""
    c = [100.0] * 5 + [101, 102, 103, 104, 105, 106, 107] \
        + [106, 105, 104, 103, 102, 101, 100] \
        + [101, 102, 103, 104, 105, 106, 107] \
        + [107 - i for i in range(1, 20)] + [88.0] * 8
    d = _frame(c)
    r = dtdb(d.high, d.low, d.close, **P3)
    # the double bottom claims the region first; the later double top
    # over the SAME pivots never becomes a pattern
    assert r[PEND].fillna(0).min() >= 0.0, "a double top was admitted"
    assert r[BEAR].sum() == 0.0


# ---------------------------------------------------------------------
# warm-up / degenerate input
# ---------------------------------------------------------------------
def test_warmup_is_nan_not_zero():
    """No pivot can confirm before bar `2 * pivots`, so those bars are
    NaN rather than a fabricated 0."""
    df = _noise(n=400)
    r = dtdb(df.high, df.low, df.close, pivots=5)
    for col in r.columns:
        assert r[col].iloc[:10].isna().all()
        assert r[col].iloc[10:].notna().all()


def test_flat_series_produces_nothing_and_no_infinities():
    d = _frame([100.0] * 300)
    r = dtdb(d.high, d.low, d.close, **P3)
    v = r.to_numpy(dtype=float)
    assert not np.isinf(v).any()
    assert np.nansum(np.abs(v)) == 0.0


def test_too_short_series_returns_none():
    d = _frame([100.0, 101.0, 102.0])
    assert dtdb(d.high, d.low, d.close, pivots=8) is None


def test_volume_is_not_read():
    import inspect
    assert "volume" not in inspect.signature(dtdb).parameters


# ---------------------------------------------------------------------
# scale-free
# ---------------------------------------------------------------------
@pytest.mark.parametrize("k", [8.0, 10.0, 0.125, 1234.5])
def test_scale_free_under_price_rescale(k):
    """Multiplying every price by k must not change any column.

    k=8 and k=0.125 are exact powers of two, so for those the check is
    BIT-EXACT (`rtol=0`): rescaling only shifts the float exponent. The
    non-power-of-two factors are checked at rtol=1e-9.

    NaN masks must match exactly, and the columns must be non-degenerate
    (`0 < fires < n`) -- a column that never fires is invariant to
    everything, which would make the whole test vacuous.
    """
    df = _noise(n=1200)
    base = dtdb(df.high, df.low, df.close, **P3)
    scaled = dtdb(df.high * k, df.low * k, df.close * k, **P3)
    assert (base.isna().to_numpy() == scaled.isna().to_numpy()).all()
    exact = float(k).is_integer() and (int(k) & (int(k) - 1)) == 0 or k == 0.125
    fired = 0
    for col in base.columns:
        b, s = base[col].dropna(), scaled[col].dropna()
        assert len(b) > 100
        nz = int((b != 0).sum())
        fired += nz
        assert 0 <= nz < len(b)
        if exact:
            np.testing.assert_array_equal(s.to_numpy(), b.to_numpy())
        else:
            np.testing.assert_allclose(s.to_numpy(), b.to_numpy(),
                                       rtol=1e-9, atol=1e-12)
    assert fired > 0, "every column is constant; invariance is vacuous"


def test_thresholds_are_atr_scaled_not_absolute():
    """The whole matcher is ATR-scaled, so a 10x price series must yield
    the SAME pattern count -- an absolute (price-level) threshold
    anywhere inside would break this."""
    df = _noise(n=1500)
    a = dtdb(df.high, df.low, df.close, **P3)
    b = dtdb(df.high * 10, df.low * 10, df.close * 10, **P3)
    assert a[BEAR].sum() == b[BEAR].sum() > 0
    assert a[BULL].sum() == b[BULL].sum()


# ---------------------------------------------------------------------
# causality
# ---------------------------------------------------------------------
_REAL = importlib.import_module("pandas_ta.trend.dtdb")
_SRC = open(_REAL.__file__).read()


def _load_mutant(old, new, tag):
    """The REAL module source with exactly one substring replaced,
    exec'd into a fresh in-memory module. Never a hand-written copy."""
    assert old in _SRC, f"mutant anchor no longer present: {old!r}"
    mod = types.ModuleType(f"_dtdb_mutant_{tag}")
    mod.__file__ = _REAL.__file__
    exec(compile(_SRC.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


_MUTANT_A_OLD = ('                    if p["dir"] == -1:\n'
                 '                        conf_bear[j] = 1.0\n'
                 '                    else:\n'
                 '                        conf_bull[j] = 1.0')
_MUTANT_A_NEW = ('                    _bd = p["apex_bar"]\n'
                 '                    if p["dir"] == -1:\n'
                 '                        conf_bear[_bd] = 1.0\n'
                 '                    else:\n'
                 '                        conf_bull[_bd] = 1.0')

_MUTANT_B_OLD = '                        if _d > tgt[j]:\n                            tgt[j] = _d'
_MUTANT_B_NEW = ('                        if _d > tgt[p["apex_bar"]]:\n'
                 '                            tgt[p["apex_bar"]] = _d')


def _finite_disagreement(full, part, cols, k):
    """Cells where a module's FULL run and its OWN run truncated at `k`
    disagree, counted ONLY over cells finite in both. NaN masks are
    asserted equal first, so warm-up NaNs are never scored either way."""
    A = full.iloc[:k][cols].to_numpy(dtype=float)
    B = part[cols].to_numpy(dtype=float)
    assert (np.isnan(A) == np.isnan(B)).all(), "NaN masks diverge"
    m = np.isfinite(A) & np.isfinite(B)
    return int((A[m] != B[m]).sum()), int(m.sum())


def test_truncation_matches_prefix_of_full_series():
    """Necessary but NOT sufficient: a bar's value cannot depend on
    anything after it. This alone cannot see back-dating -- that is what
    the mutants below are for."""
    df = _noise(n=700)
    full = dtdb(df.high, df.low, df.close, **P3)
    for k in (120, 301, 455, 699):
        d = df.iloc[:k]
        pd.testing.assert_frame_equal(dtdb(d.high, d.low, d.close, **P3),
                                      full.iloc[:k])


def test_mutant_a_backdating_confirmation_to_the_apex_bar_is_caught():
    """Mutant A moves the confirmation write from the break bar `j` to
    the pattern's own `apex_bar` -- the canonical chart-pattern
    back-dating bug, and exactly what the Pine source's `label.new(
    p.apexBar, ...)` does for DISPLAY.

    It is a PERTURBING mutant: the total fire count is unchanged (the
    flag moves, it is not deleted), asserted below, so this cannot be
    confused with a mutant that merely kills the column.

    Detection is REAL-vs-MUTANT prefix truncation at `k = apex_bar + 1`,
    i.e. AFTER the apex but BEFORE the neckline break: the mutant's full
    run has already written back at the apex, its truncated run has not
    reached the break at all, so they disagree. The real module never
    disagrees at any `k`.
    """
    df = _noise(n=900)
    cols = [BEAR, BULL]
    real_full = dtdb(df.high, df.low, df.close, **P3)
    mod = _load_mutant(_MUTANT_A_OLD, _MUTANT_A_NEW, "a")
    mut_full = mod.dtdb(df.high, df.low, df.close, **P3)

    # perturbing, not unsatisfiable
    assert real_full[BEAR].sum() > 0 and real_full[BULL].sum() > 0
    assert real_full[BEAR].sum() == mut_full[BEAR].sum()
    assert real_full[BULL].sum() == mut_full[BULL].sum()
    # ...but the flags sit on DIFFERENT bars
    moved = np.where((mut_full[cols].fillna(0).to_numpy()
                      != real_full[cols].fillna(0).to_numpy()).any(axis=1))[0]
    assert len(moved) > 0, "mutant did not perturb; the fixture has no patterns"

    real_hits = mut_hits = 0
    for bar in moved[:10]:
        k = int(bar) + 1
        d = df.iloc[:k]
        r_dis, r_n = _finite_disagreement(real_full,
                                          dtdb(d.high, d.low, d.close, **P3),
                                          cols, k)
        m_dis, m_n = _finite_disagreement(mut_full,
                                          mod.dtdb(d.high, d.low, d.close, **P3),
                                          cols, k)
        assert r_n > 0 and m_n > 0, "no co-populated cells to compare"
        assert r_dis == 0, f"REAL module leaked at k={k}: {r_dis} cells"
        real_hits += r_dis
        mut_hits += m_dis
    assert real_hits == 0
    assert mut_hits > 0, "the truncation table has no power against mutant A"


def test_mutant_b_backdating_the_target_to_the_apex_bar_is_caught():
    """Mutant B is the same edit applied to the measured-target column,
    proving the detector is not specific to the flags."""
    df = _noise(n=900)
    cols = [TGT]
    real_full = dtdb(df.high, df.low, df.close, **P3)
    mod = _load_mutant(_MUTANT_B_OLD, _MUTANT_B_NEW, "b")
    mut_full = mod.dtdb(df.high, df.low, df.close, **P3)
    assert (real_full[TGT].fillna(0) > 0).sum() > 0
    assert (mut_full[TGT].fillna(0) > 0).sum() == \
           (real_full[TGT].fillna(0) > 0).sum()
    moved = np.where(mut_full[TGT].fillna(0).to_numpy()
                     != real_full[TGT].fillna(0).to_numpy())[0]
    assert len(moved) > 0

    mut_hits = 0
    for bar in moved[:10]:
        k = int(bar) + 1
        d = df.iloc[:k]
        r_dis, r_n = _finite_disagreement(real_full,
                                          dtdb(d.high, d.low, d.close, **P3),
                                          cols, k)
        m_dis, _ = _finite_disagreement(mut_full,
                                        mod.dtdb(d.high, d.low, d.close, **P3),
                                        cols, k)
        assert r_n > 0
        assert r_dis == 0, f"REAL module leaked at k={k}"
        mut_hits += m_dis
    assert mut_hits > 0, "no power against mutant B"


def test_nothing_is_written_before_the_pattern_is_born():
    """Direct statement of the same property on the hand fixture: the
    apex bar (18) and both pivot bars (4, 11) carry a hard zero."""
    df = _double_top()
    r = dtdb(df.high, df.low, df.close, **P3)
    # bar 4 is the first pivot but sits inside the 2*pivots warm-up, so
    # it is NaN rather than 0 -- asserted as NaN, not quietly skipped.
    assert r[BEAR].iloc[4] != r[BEAR].iloc[4]
    for bar in (11, 18):              # neckline pivot, apex pivot
        assert r[BEAR].iloc[bar] == 0.0
        assert r[TGT].iloc[bar] == 0.0
        assert r[RES].iloc[bar] == 0.0


# ---------------------------------------------------------------------
# argument handling
# ---------------------------------------------------------------------
@pytest.mark.parametrize("kw", [
    dict(pivots=0), dict(pivots=2), dict(pivots=2.5), dict(pivots=float("nan")),
    dict(pivots=True), dict(atr_length=-1), dict(max_wait=0), dict(track_bars=0),
    dict(max_keep=0), dict(tol_atr=0.0), dict(tol_atr=float("inf")),
    dict(buf_atr=-0.1), dict(void_atr=-1.0), dict(mode="wik"),
    dict(dbl_mode="strong"), dict(mode=3),
])
def test_invalid_arguments_raise_value_error(kw):
    df = _noise(n=200)
    with pytest.raises(ValueError):
        dtdb(df.high, df.low, df.close, **kw)


def test_none_arguments_use_defaults():
    df = _noise(n=400)
    a = dtdb(df.high, df.low, df.close)
    b = dtdb(df.high, df.low, df.close, pivots=None, tol_atr=None,
             buf_atr=None, void_atr=None, max_wait=None, track_bars=None,
             max_keep=None, atr_length=None, mode=None, dbl_mode=None)
    pd.testing.assert_frame_equal(a, b)


def test_mode_and_dbl_mode_are_case_insensitive():
    df = _noise(n=400)
    pd.testing.assert_frame_equal(
        dtdb(df.high, df.low, df.close, mode="close", dbl_mode="any"),
        dtdb(df.high, df.low, df.close, mode="CLOSE", dbl_mode=" Any "))


def test_offset_shifts_all_columns():
    df = _double_top()
    base = dtdb(df.high, df.low, df.close, **P3)
    off = dtdb(df.high, df.low, df.close, offset=2, **P3)
    for col in base.columns:
        pd.testing.assert_series_equal(off[col], base[col].shift(2),
                                       check_names=False)


def test_fillna_kwarg():
    df = _noise(n=300)
    r = dtdb(df.high, df.low, df.close, pivots=5, fillna=0.0)
    assert r.notna().all().all()


def test_max_keep_evicts_the_oldest_confirmed_pattern():
    """`max_keep` is engine state, not display: evicting a confirmed
    pattern frees its region and lets later patterns be admitted, so a
    small cap must produce at least as many confirmations as a large
    one on the same series."""
    df = _noise(n=1500)
    tight = dtdb(df.high, df.low, df.close, max_keep=1, **P3)
    loose = dtdb(df.high, df.low, df.close, max_keep=30, **P3)
    n_tight = tight[BEAR].sum() + tight[BULL].sum()
    n_loose = loose[BEAR].sum() + loose[BULL].sum()
    assert n_loose > 0
    assert n_tight >= n_loose
