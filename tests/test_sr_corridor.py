# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.trend.sr_corridor` -- S/R Corridor Width (SRCOR).

What this file is built around:

* A HAND-DERIVED zone fixture. The pivot bars, the zone edges and the
  corridor width are computed on paper from the price path and from an
  INDEPENDENTLY-recomputed ATR, then asserted exactly -- never read back
  out of the module and re-asserted against itself.

* THE NON-DUPLICATION CLAIMS ARE TESTS, NOT PROSE. The module docstring
  says four things that would each be a lie if untested, so each has a
  test: `volume` is not an argument (delta i); asymmetric pivots change
  the output (delta ii); the ATR invalidation buffer changes the output
  (delta iii); and the source's boolean `zonesCloseTogether` is EXACTLY
  `SRCOR_WIDTH_ATR <= minimumZoneGapATR`, which is why it is not a
  second column (delta iv). The last one is proved by exec'ing a mutant
  of the real module that emits the RAW price-unit gap, and checking the
  two booleans agree cell-for-cell.

* TWO CAUSALITY MUTANTS, each an `importlib` + `exec` copy of the REAL
  module source with one edit, both PERTURBING (they move information in
  time; they do not delete the column). Detection is a REAL-vs-MUTANT
  table comparing each module's FULL run against its OWN truncated run,
  because a bare prefix-truncation test cannot see a mutant that reads
  the future consistently in both runs.

* NaN masks are compared explicitly and values compared only on
  co-populated (finite-in-both) cells, so warm-up NaNs are never counted
  as agreement or as disagreement.
"""
import importlib
import types

import numpy as np
import pandas as pd
import pytest

from .context import pandas_ta as ta
from pandas_ta.trend.sr_corridor import sr_corridor
from pandas_ta.volatility.atr import atr as _atr


COL = "SRCOR_WIDTH_ATR_8_5_0.6"
P21 = dict(pivot_left=2, pivot_right=1)
COL21 = "SRCOR_WIDTH_ATR_2_1_0.6"
MIN_GAP_ATR = 0.25          # the Pine source's `minimumZoneGapATR` default


def _frame(closes):
    """close-driven OHLC with a symmetric 1.0-wide bar, so `high` and
    `low` pivots are exactly `close +- 0.5` and hand-derivable."""
    c = [float(x) for x in closes]
    return pd.DataFrame({"open": c,
                         "high": [x + 0.5 for x in c],
                         "low": [x - 0.5 for x in c],
                         "close": c})


def _noise(seed=11, n=1200, drift=0.0):
    rng = np.random.default_rng(seed)
    c = 100 * np.exp(np.cumsum(rng.normal(drift, 0.011, n)))
    h = c * (1 + abs(rng.normal(0, 0.005, n)))
    l = c * (1 - abs(rng.normal(0, 0.005, n)))
    return pd.DataFrame({"open": c, "high": h, "low": l, "close": c})


# bars 0-19 are a flat 100 run whose only job is to warm the 14-bar ATR
# up out of NaN: the source refuses to form a zone while `atr[pivotRight]`
# is `na` (source line 343/363), so a fixture that peaks inside the
# warm-up produces no zones at all and proves nothing. A flat run also
# yields NO pivots (a plateau has no unique extreme), so it adds no
# zones of its own.
_CORRIDOR_PATH = [100.0] * 20 + [101, 102, 101, 100, 99, 98, 99, 100] \
                 + [100.0] * 17
PEAK_BAR, PEAK_CONF = 21, 22       # high 102.5, confirms pivot_right=1 later
TROUGH_BAR, TROUGH_CONF = 25, 26   # low   97.5, confirms pivot_right=1 later
RES_TOP, SUP_BOTTOM = 102.5, 97.5


def _corridor():
    """One clean inverted-V then one clean V, at pivot_left=2/right=1.

    bar 21  close 102 -> unique pivot HIGH (high 102.5), confirms bar 22
    bar 25  close  98 -> unique pivot LOW  (low  97.5), confirms bar 26
    bars 27-44 flat at 100 -> price parked between the two zones, and no
        further pivot forms (every later window ties).

    Verified against the module before any assertion was written: the
    column's first populated bar is 26 and no zone is invalidated
    anywhere in the path.
    """
    return _frame(_CORRIDOR_PATH)


# ---------------------------------------------------------------------
# shape / registration -- the 5 touch points
# ---------------------------------------------------------------------
def test_column_names_and_category():
    d = _noise(n=400)
    r = sr_corridor(d.high, d.low, d.close)
    assert list(r.columns) == [COL]
    assert r.name == "SRCOR_8_5_0.6"
    assert r.category == "trend"


def test_registered_in_category_dict():
    assert "sr_corridor" in ta.Category["trend"]


def test_dataframe_accessor_matches_direct_call():
    d = _noise(n=400)
    direct = sr_corridor(d.high, d.low, d.close)
    frame = d.copy()
    frame.columns = [c.lower() for c in frame.columns]
    pd.testing.assert_frame_equal(direct, frame.ta.sr_corridor())


def test_only_one_column_is_emitted():
    """The port is deliberately ONE column. If a second one ever
    appears, the docstring's non-duplication argument has to be
    re-argued and re-measured, so this is pinned."""
    d = _noise(n=400)
    assert sr_corridor(d.high, d.low, d.close).shape[1] == 1


# ---------------------------------------------------------------------
# correctness vs the Pine source, hand-derived
# ---------------------------------------------------------------------
def test_hand_derived_zone_edges_and_corridor_width():
    """Both zones and the corridor width are derived on paper here, from
    the price path plus an INDEPENDENTLY recomputed ATR:

        resistance top    = 102.5   (pivot high, bar 2, confirms bar 3)
        resistance bottom = 102.5 - ATR[2] * 0.60
        support    bottom =  97.5   (pivot low,  bar 6, confirms bar 7)
        support    top    =  97.5 + ATR[6] * 0.60
        width             = (res_bottom - sup_top) / ATR[j]

    Note the two zone depths use the ATR of the PIVOT's own bar (source
    lines 349/369), not of the confirmation bar, and the divisor uses
    the ATR of the bar being reported.
    """
    d = _corridor()
    a = _atr(d.high, d.low, d.close, length=14).to_numpy()
    r = sr_corridor(d.high, d.low, d.close, **P21)[COL21]

    res_bottom = RES_TOP - a[PEAK_BAR] * 0.60
    sup_top = SUP_BOTTOM + a[TROUGH_BAR] * 0.60
    assert res_bottom == pytest.approx(101.8476268192461, abs=1e-12)
    assert sup_top == pytest.approx(98.22771193271060, abs=1e-12)
    # nothing to pair with before the support confirms at bar 26
    assert r.iloc[:TROUGH_CONF].isna().all()
    for j in (26, 30, 40, 44):
        assert r.iloc[j] == pytest.approx((res_bottom - sup_top) / a[j], abs=1e-12)
    assert r.iloc[26] == pytest.approx(2.9266990438560225, abs=1e-12)


def test_pivot_confirms_pivot_right_bars_after_the_extreme():
    """The corridor cannot open until the SECOND of the two pivots has
    CONFIRMED, which is `pivot_right` bars after its extreme. The trough
    sits at bar 25 in this fixture, so the first populated bar must be
    26 at `pivot_right = 1` and 28 at `pivot_right = 3` -- a 2-bar shift
    that only a right-side confirmation lag can produce."""
    d = _corridor()
    r1 = sr_corridor(d.high, d.low, d.close, pivot_left=2, pivot_right=1)
    r3 = sr_corridor(d.high, d.low, d.close, pivot_left=2, pivot_right=3)
    assert r1["SRCOR_WIDTH_ATR_2_1_0.6"].first_valid_index() == TROUGH_BAR + 1
    assert r3["SRCOR_WIDTH_ATR_2_3_0.6"].first_valid_index() == TROUGH_BAR + 3


def test_price_closing_beyond_the_buffer_kills_the_zone():
    """A close above `res_top + ATR * invalidation_atr` removes the
    resistance zone, and with it the corridor. The flip bar is computed
    from an independently recomputed ATR, not read from the module."""
    d = _frame(_CORRIDOR_PATH + [101, 103, 106, 110, 115, 120])
    a = _atr(d.high, d.low, d.close, length=14).to_numpy()
    r = sr_corridor(d.high, d.low, d.close, **P21)[COL21]
    kill = np.where(d.close.to_numpy() > RES_TOP + a * 0.10)[0]
    kill = kill[kill >= TROUGH_CONF]
    assert len(kill) > 0
    first = int(kill[0])
    assert first == 46
    assert r.notna().iloc[first - 1]
    assert r.isna().iloc[first:].all()


def test_corridor_is_nan_when_only_one_side_exists():
    """A monotone decline builds support zones and no resistance zone;
    a one-sided book has no corridor."""
    d = _frame([100.0] * 20 + list(range(100, 60, -1)))
    r = sr_corridor(d.high, d.low, d.close, **P21)[COL21]
    assert r.isna().all()


def test_corridor_can_go_negative_when_zones_overlap():
    """`distanceBetweenZones` is SIGNED (source lines 580-584). A deep
    `zone_atr` makes the two bands overlap, and the module must publish
    the negative gap rather than clamping it."""
    d = _corridor()
    r = sr_corridor(d.high, d.low, d.close, zone_atr=6.0,
                    **P21)["SRCOR_WIDTH_ATR_2_1_6.0"]
    v = r.dropna()
    assert len(v) > 0
    assert v.min() == pytest.approx(-8.25615587115965, abs=1e-12)


# ---------------------------------------------------------------------
# the four non-duplication deltas vs `volume_sr_zones` (VOLSR)
# ---------------------------------------------------------------------
def test_delta_i_volume_is_not_read():
    """VOLSR forms a zone only on above-average volume at the pivot bar.
    This source has no such filter, so `volume` must not even be an
    argument -- otherwise the difference is not real."""
    import inspect
    assert "volume" not in inspect.signature(sr_corridor).parameters


def test_delta_ii_asymmetric_pivots_change_the_output():
    """VOLSR takes a single `pivot_length` and cannot express the
    source's 8/5. If 8/5 and 8/8 gave the same column the asymmetry
    would be decorative."""
    d = _noise(n=1200)
    asym = sr_corridor(d.high, d.low, d.close, pivot_left=8, pivot_right=5)
    sym = sr_corridor(d.high, d.low, d.close, pivot_left=8, pivot_right=8)
    a = asym["SRCOR_WIDTH_ATR_8_5_0.6"].to_numpy()
    b = sym["SRCOR_WIDTH_ATR_8_8_0.6"].to_numpy()
    m = np.isfinite(a) & np.isfinite(b)
    assert m.sum() > 100
    assert (a[m] != b[m]).sum() > 0


def test_delta_iii_invalidation_buffer_changes_the_output():
    """VOLSR breaks a zone on a bare close through the level. Setting
    `invalidation_atr = 0` reproduces that, and it must not give the
    same column as the source's 0.10."""
    d = _noise(n=1200)
    buffered = sr_corridor(d.high, d.low, d.close)
    bare = sr_corridor(d.high, d.low, d.close, invalidation_atr=0.0)
    a = buffered[COL].to_numpy()
    b = bare[COL].to_numpy()
    m = np.isfinite(a) & np.isfinite(b)
    assert m.sum() > 100
    assert (a[m] != b[m]).sum() > 0
    # the buffer can only make zones live LONGER, so it can only add
    # populated bars, never remove them
    assert np.isfinite(a).sum() >= np.isfinite(b).sum()


# NOTE: the delta-(v) test lives BELOW `_load_mutant`, because the
# cleanest proof that the zero-clamp is load-bearing is a mutant that
# removes it. See `test_delta_v_distance_is_zero_clamped_inside_the_zone`.


# ---------------------------------------------------------------------
# delta (iv): why the compressed-area FLAG is not a second column
# ---------------------------------------------------------------------
_REAL = importlib.import_module("pandas_ta.trend.sr_corridor")
_SRC = open(_REAL.__file__).read()


def _load_mutant(old, new, tag):
    """The REAL module source with exactly one substring replaced,
    exec'd into a fresh in-memory module. Never a hand-written copy."""
    assert old in _SRC, f"mutant anchor no longer present: {old!r}"
    assert _SRC.count(old) == 1, f"mutant anchor is not unique: {old!r}"
    mod = types.ModuleType(f"_srcor_mutant_{tag}")
    mod.__file__ = _REAL.__file__
    exec(compile(_SRC.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


_RAW_OLD = "            width_atr[j] = (res_bottom - sup_top) / a"
_RAW_NEW = "            width_atr[j] = (res_bottom - sup_top)"


def test_compressed_flag_is_exactly_a_threshold_on_the_shipped_column():
    """The source's `zonesCloseTogether` (lines 588-590) is
    `distanceBetweenZones <= atr * minimumZoneGapATR`.

    Proved here, not asserted: a mutant of the real module emits the RAW
    price-unit gap, ATR is recomputed independently, and the two
    booleans are compared cell-for-cell on co-populated bars. Both
    outcomes must occur, so the agreement is not vacuous.
    """
    d = _noise(n=1500)
    real = sr_corridor(d.high, d.low, d.close)[COL].to_numpy()
    mod = _load_mutant(_RAW_OLD, _RAW_NEW, "raw")
    raw = mod.sr_corridor(d.high, d.low, d.close)[COL].to_numpy()
    a = _atr(d.high, d.low, d.close, length=14).to_numpy()

    m = np.isfinite(real) & np.isfinite(raw) & np.isfinite(a)
    assert m.sum() > 500
    assert (np.isnan(real) == np.isnan(raw)).all()

    # The identity holds for ANY threshold, so it is checked at the
    # source's own default AND at a threshold taken from the column's own
    # median, which guarantees a non-vacuous split (both outcomes occur).
    for thr in (MIN_GAP_ATR, float(np.median(real[m]))):
        pine_flag = raw[m] <= a[m] * thr
        from_column = real[m] <= thr
        assert np.array_equal(pine_flag, from_column), f"thr={thr}"
    split = raw[m] <= a[m] * float(np.median(real[m]))
    assert 0 < int(split.sum()) < int(m.sum())

    # Reported, not asserted as a property of the market: on this
    # synthetic path the source's DEFAULT compression threshold never
    # fires -- 0 of the populated bars sit at or below 0.25 ATR, because
    # two 0.60-ATR-deep zones that overlapped that closely would already
    # have invalidated each other. A second column that is constant-0 on
    # a 1,500-bar fixture is a further reason not to ship the flag.
    assert int((real[m] <= MIN_GAP_ATR).sum()) == 0


def test_raw_gap_is_not_scale_free_but_the_shipped_column_is():
    """The reason the raw gap is not the shipped form: it is a price
    LEVEL difference and moves with the price scale. The mutant makes
    that concrete instead of leaving it as an assertion in prose."""
    d = _noise(n=900)
    mod = _load_mutant(_RAW_OLD, _RAW_NEW, "raw2")
    raw1 = mod.sr_corridor(d.high, d.low, d.close)[COL].to_numpy()
    raw8 = mod.sr_corridor(d.high * 8, d.low * 8, d.close * 8)[COL].to_numpy()
    m = np.isfinite(raw1) & np.isfinite(raw8)
    assert m.sum() > 100
    assert (raw1[m] != raw8[m]).sum() > 0
    np.testing.assert_allclose(raw8[m], raw1[m] * 8.0, rtol=1e-12)


_CLAMP_OLD = "                d = c - t if c > t else 0.0"
_CLAMP_NEW = "                d = c - t"


def test_delta_v_distance_is_zero_clamped_inside_the_zone():
    """Nearest-zone SELECTION clamps the distance at 0 once price is
    inside the band (source lines 475-479 / 487-491). VOLSR has no such
    clamp -- it ranks by a signed percent distance.

    Proved with a mutant that deletes the clamp from the support branch
    only, so an inside-the-band zone scores NEGATIVE and outranks a
    zone the source would have tied at 0. `zone_atr = 3.0` is used so
    that containment is common enough for the difference to be
    frequent rather than a handful of bars.
    """
    d = _noise(n=1500)
    col = "SRCOR_WIDTH_ATR_8_5_3.0"
    real = sr_corridor(d.high, d.low, d.close, zone_atr=3.0)[col].to_numpy()
    mod = _load_mutant(_CLAMP_OLD, _CLAMP_NEW, "clamp")
    mut = mod.sr_corridor(d.high, d.low, d.close, zone_atr=3.0)[col].to_numpy()
    both = np.isfinite(real) & np.isfinite(mut)
    assert both.sum() > 300
    assert (real[both] != mut[both]).sum() > 0, "the clamp is not load-bearing"


# ---------------------------------------------------------------------
# warm-up / degenerate input
# ---------------------------------------------------------------------
def test_warmup_is_nan():
    d = _noise(n=600)
    r = sr_corridor(d.high, d.low, d.close)[COL]
    assert r.iloc[:14].isna().all()


def test_flat_series_produces_no_values_and_no_infinities():
    """A flat series has no strict pivots at all and, separately, a zero
    ATR; the column must be all-NaN rather than inf."""
    d = _frame([100.0] * 300)
    r = sr_corridor(d.high, d.low, d.close)[COL]
    assert r.isna().all()
    assert not np.isinf(r.to_numpy(dtype=float)).any()


def test_too_short_series_returns_none():
    d = _frame([100.0, 101.0, 102.0])
    assert sr_corridor(d.high, d.low, d.close) is None


def test_max_zones_cap_is_load_bearing():
    """`max_zones` is a SHARED oldest-first FIFO across both zone types
    (source line 383). A cap of 1 can hold only one zone, so no bar can
    ever have both a support and a resistance, and the column is empty."""
    d = _noise(n=900)
    assert sr_corridor(d.high, d.low, d.close)[COL].notna().sum() > 100
    tight = sr_corridor(d.high, d.low, d.close, max_zones=1)[COL]
    assert tight.notna().sum() == 0


# ---------------------------------------------------------------------
# scale-free
# ---------------------------------------------------------------------
@pytest.mark.parametrize("k,exact", [(8.0, True), (0.125, True),
                                     (10.0, False), (1234.5, False)])
def test_scale_free_under_price_rescale(k, exact):
    """Multiplying every price by k must not change the column.

    k=8 and k=0.125 are exact powers of two, so for those the check is
    BIT-EXACT (`assert_array_equal`): rescaling only shifts the float
    exponent. Non-power-of-two factors are checked at rtol=1e-9.

    NaN masks must match exactly, and the column must be non-degenerate
    -- a constant or empty column is invariant to everything, which
    would make the whole test vacuous.
    """
    d = _noise(n=1200)
    base = sr_corridor(d.high, d.low, d.close)[COL]
    scaled = sr_corridor(d.high * k, d.low * k, d.close * k)[COL]
    assert (base.isna().to_numpy() == scaled.isna().to_numpy()).all()
    b = base.dropna()
    s = scaled.dropna()
    n = len(b)
    assert n > 300, "too few populated bars for the check to mean anything"
    nz = int((b != 0).sum())
    assert 0 < nz <= n
    assert b.nunique() > 100, "column is near-constant; invariance is vacuous"
    assert float(b.std()) > 0.0
    if exact:
        np.testing.assert_array_equal(s.to_numpy(), b.to_numpy())
    else:
        np.testing.assert_allclose(s.to_numpy(), b.to_numpy(),
                                   rtol=1e-9, atol=1e-12)


def test_no_price_level_is_ever_emitted():
    """Scale-free discipline: on a series that lives around 100, an
    ATR-normalised corridor must not come back carrying values of the
    same order as the price itself for the whole column."""
    d = _noise(n=1200)
    v = sr_corridor(d.high, d.low, d.close)[COL].dropna()
    assert v.abs().max() < 60.0
    assert v.median() < 30.0


# ---------------------------------------------------------------------
# causality
# ---------------------------------------------------------------------
_MUT_A_OLD = ("        if not np.isnan(ph_vals[j]) and not np.isnan(a_pivot):\n"
              "            top = ph_vals[j]")
_MUT_A_NEW = ("        _jf = min(j + pivot_right, n - 1)\n"
              "        if not np.isnan(ph_vals[_jf]) and not np.isnan(a_pivot):\n"
              "            top = ph_vals[_jf]")

_MUT_B_OLD = "        a = atr_vals[j]"
_MUT_B_NEW = "        a = atr_vals[min(j + 1, n - 1)]"


def _finite_disagreement(full, part, k):
    """Cells where a module's FULL run and its OWN run truncated at `k`
    disagree, counted ONLY over cells finite in both."""
    A = full.iloc[:k].to_numpy(dtype=float)
    B = part.to_numpy(dtype=float)
    both = np.isfinite(A) & np.isfinite(B)
    mask_mismatch = int((np.isnan(A) != np.isnan(B)).sum())
    return (int((A[both] != B[both]).sum()), int(both.sum()), mask_mismatch)


def test_truncation_matches_prefix_of_full_series():
    """Necessary but NOT sufficient: a bar's value cannot depend on
    anything after it. This alone cannot see a mutant that reads the
    future the same way in both runs -- that is what the mutants are
    for."""
    d = _noise(n=700)
    full = sr_corridor(d.high, d.low, d.close)
    for k in (120, 301, 455, 699):
        p = d.iloc[:k]
        pd.testing.assert_frame_equal(
            sr_corridor(p.high, p.low, p.close), full.iloc[:k])


def test_mutant_a_forming_the_zone_at_the_pivots_own_bar_is_caught():
    """Mutant A creates the resistance zone `pivot_right` bars EARLY --
    at the pivot's own bar rather than at its confirmation bar. That is
    the canonical pivot-indicator look-ahead, and exactly what the Pine
    source does for DISPLAY (`bar_index - pivotRight`, source line 357).

    It is a PERTURBING mutant: the zone still forms, it just forms
    earlier, so the column keeps roughly the same population rather than
    collapsing -- asserted below, so "the mutant broke the column" can
    never be mistaken for "the mutant leaked".

    Detection is REAL-vs-MUTANT prefix truncation. The mutant's full run
    has already read the pivot that confirms after the cut; its
    truncated run has not, so the two disagree. The real module never
    disagrees at any k.
    """
    d = _noise(n=900)
    real_full = sr_corridor(d.high, d.low, d.close)[COL]
    mod = _load_mutant(_MUT_A_OLD, _MUT_A_NEW, "a")
    mut_full = mod.sr_corridor(d.high, d.low, d.close)[COL]

    rn, mn = int(real_full.notna().sum()), int(mut_full.notna().sum())
    assert rn > 300 and mn > 300, "mutant collapsed the column; not perturbing"
    assert 0.5 < mn / rn < 2.0, "mutant is unsatisfiable, not perturbing"
    a = real_full.to_numpy(dtype=float)
    b = mut_full.to_numpy(dtype=float)
    both = np.isfinite(a) & np.isfinite(b)
    assert both.sum() > 300, "no co-populated bars: nothing was perturbed"
    moved = np.where(both & (a != b))[0]
    assert len(moved) > 0, "mutant did not perturb on co-populated bars"

    real_hits = mut_hits = 0
    checked = 0
    for bar in moved[:: max(1, len(moved) // 12)][:12]:
        k = int(bar) + 1
        if k < 60:
            continue
        p = d.iloc[:k]
        r_dis, r_n, r_mm = _finite_disagreement(
            real_full, sr_corridor(p.high, p.low, p.close)[COL], k)
        m_dis, m_n, m_mm = _finite_disagreement(
            mut_full, mod.sr_corridor(p.high, p.low, p.close)[COL], k)
        assert r_n > 0 and m_n > 0, "no co-populated cells to compare"
        assert r_dis == 0 and r_mm == 0, f"REAL module leaked at k={k}"
        real_hits += r_dis
        mut_hits += m_dis + m_mm
        checked += 1
    assert checked > 0
    assert real_hits == 0
    assert mut_hits > 0, "the truncation table has no power against mutant A"


def test_mutant_b_using_tomorrows_atr_is_caught():
    """Mutant B leaves the zone engine alone and only swaps the ATR used
    for the buffer and the divisor to the NEXT bar's. Perturbing (every
    populated bar keeps a value, it is just the wrong one), and it
    proves the detector is not specific to the pivot path."""
    d = _noise(n=900)
    real_full = sr_corridor(d.high, d.low, d.close)[COL]
    mod = _load_mutant(_MUT_B_OLD, _MUT_B_NEW, "b")
    mut_full = mod.sr_corridor(d.high, d.low, d.close)[COL]

    a = real_full.to_numpy(dtype=float)
    b = mut_full.to_numpy(dtype=float)
    both = np.isfinite(a) & np.isfinite(b)
    assert both.sum() > 300
    assert int(mut_full.notna().sum()) > 300
    moved = np.where(both & (a != b))[0]
    assert len(moved) > 100, "mutant did not perturb on co-populated bars"

    mut_hits = 0
    checked = 0
    for bar in moved[:: max(1, len(moved) // 12)][:12]:
        k = int(bar) + 1
        if k < 60:
            continue
        p = d.iloc[:k]
        r_dis, r_n, r_mm = _finite_disagreement(
            real_full, sr_corridor(p.high, p.low, p.close)[COL], k)
        m_dis, m_n, m_mm = _finite_disagreement(
            mut_full, mod.sr_corridor(p.high, p.low, p.close)[COL], k)
        assert r_n > 0 and m_n > 0
        assert r_dis == 0 and r_mm == 0, f"REAL module leaked at k={k}"
        mut_hits += m_dis + m_mm
        checked += 1
    assert checked > 0
    assert mut_hits > 0, "no power against mutant B"


# ---------------------------------------------------------------------
# argument handling
# ---------------------------------------------------------------------
@pytest.mark.parametrize("kw", [
    dict(pivot_left=0), dict(pivot_left=-1), dict(pivot_left=2.5),
    dict(pivot_left=float("nan")), dict(pivot_left=True),
    dict(pivot_right=0), dict(pivot_right=float("inf")),
    dict(atr_length=0), dict(max_zones=0),
    dict(zone_atr=0.0), dict(zone_atr=-1.0), dict(zone_atr=float("nan")),
    dict(zone_atr=float("inf")), dict(zone_atr=True),
    dict(invalidation_atr=-0.1), dict(invalidation_atr=float("inf")),
])
def test_invalid_arguments_raise_value_error(kw):
    d = _noise(n=300)
    with pytest.raises(ValueError):
        sr_corridor(d.high, d.low, d.close, **kw)


def test_invalidation_atr_zero_is_allowed():
    """0 is a legitimate value -- it reproduces a bare break -- so it
    must NOT be rejected the way `zone_atr=0` is."""
    d = _noise(n=400)
    assert sr_corridor(d.high, d.low, d.close, invalidation_atr=0.0) is not None


def test_none_arguments_use_defaults():
    d = _noise(n=500)
    a = sr_corridor(d.high, d.low, d.close)
    b = sr_corridor(d.high, d.low, d.close, pivot_left=None, pivot_right=None,
                    atr_length=None, zone_atr=None, invalidation_atr=None,
                    max_zones=None)
    pd.testing.assert_frame_equal(a, b)


def test_offset_shifts_the_column():
    d = _noise(n=500)
    base = sr_corridor(d.high, d.low, d.close)
    off = sr_corridor(d.high, d.low, d.close, offset=2)
    pd.testing.assert_series_equal(off[COL], base[COL].shift(2),
                                   check_names=False)


def test_fillna_kwarg():
    d = _noise(n=400)
    r = sr_corridor(d.high, d.low, d.close, fillna=0.0)
    assert r.notna().all().all()
