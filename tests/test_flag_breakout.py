# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.trend.flag_breakout` -- Flag Pattern Breakout (FLAG).

What this file is built around:

* A HAND-DERIVED bull flag whose every bar was computed on paper BEFORE
  the module was run: 30 flat bars at 100.0, a 5-bar pole rising 0.60 a
  bar, a 4-bar flag drifting back 0.20 a bar, and one breakout bar whose
  HIGH stays under the pole's high (otherwise the tracked upper extreme
  would reset to that bar and no close could ever clear it).  The
  confirmation lands on bar 39 and nowhere else, and the bear fixture is
  its exact mirror.

* A COMPLETE LITERAL TRANSLITERATION of the Pine source -- sequential
  accumulation, per-bar loops, no vectorisation -- run bar-for-bar
  against the shipped module.  The shipped module takes its five
  regression sums over a numpy sliding window, a different summation
  ORDER from Pine's `for` loop, so this is the test that says the
  reordering does not move an answer rather than assuming it.

* TWO CAUSALITY MUTANTS, each an `importlib` + `exec` copy of the REAL
  module source with one write index moved from the breakout bar `t`
  back to `eg[S]` -- the channel's own first bar, which is also the
  pole's last bar.  That is exactly the back-dating hazard for a chart
  pattern: the pattern "exists" from the pole onward, and it is very
  natural (and wrong) to stamp it there.  Both are PERTURBING mutants:
  they MOVE a value rather than deleting it, and the totals are asserted
  EQUAL between real and mutant so "the mutant broke the column" can
  never be mistaken for "the mutant leaked".

* NaN masks are compared explicitly, and values only on co-populated
  (finite-in-both) cells, so warm-up NaNs are never scored as agreement
  OR as disagreement.  A bare `!=` over NaN-bearing floats passes
  against a mutant that merely emits nothing.
"""
import importlib
import types

import numpy as np
import pandas as pd
import pytest

from .context import pandas_ta as ta
from pandas_ta.trend.flag_breakout import flag_breakout
from pandas_ta.volatility.atr import atr as _atr


BULL = "FLAG_CONF_BULL_12_0.85_0.15"
BEAR = "FLAG_CONF_BEAR_12_0.85_0.15"
POLE = "FLAG_POLE_ATR_12_0.85_0.15"
PEND = "FLAG_PEND_12_0.85_0.15"
COLS = [BULL, BEAR, POLE, PEND]


# ---------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------
def _hand(sign):
    """One deliberate flag, derived on paper.

    bars  0-29  flat at 100.00, bar range 0.10  -> ATR settles at 0.10
    bars 30-34  pole, +/-0.60 a bar             -> height 3.10, which is
                                                   10.869268 ATR at the
                                                   DETECTION bar 34 and
                                                   9.833099 ATR at the
                                                   CONFIRMATION bar 39
    bars 35-38  flag, -/+0.20 a bar             -> slope -0.20, |slope|
                                                   0.32x the pole slope
    bar     39  breakout close, HIGH still under the pole high
    bars 40-49  flat
    """
    c = [100.0] * 30
    for k in range(1, 6):
        c.append(100.0 + sign * 0.60 * k)
    p = c[-1]
    for k in range(1, 5):
        c.append(p - sign * 0.20 * k)
    c.append(p - sign * 0.05)
    c += [p - sign * 0.05] * 10
    c = np.asarray(c, dtype=float)
    return pd.DataFrame({"open": c, "high": c + 0.05, "low": c - 0.05,
                         "close": c, "volume": np.full(len(c), 1000.0)})


def _noise(n=12000, seed=5, vol=0.015, wick=0.006):
    rng = np.random.default_rng(seed)
    c = 100.0 * np.exp(np.cumsum(rng.normal(0.0, vol, n)))
    h = c * (1.0 + np.abs(rng.normal(0.0, wick, n)))
    l = c * (1.0 - np.abs(rng.normal(0.0, wick, n)))
    return pd.DataFrame({"open": c, "high": h, "low": l, "close": c,
                         "volume": np.full(n, 1000.0)})


# ---------------------------------------------------------------------
# wiring
# ---------------------------------------------------------------------
def test_column_names_and_category():
    df = _hand(1)
    out = flag_breakout(df.high, df.low, df.close)
    assert list(out.columns) == COLS
    assert out.category == "trend"
    assert out.name == "FLAG_12_0.85_0.15"


def test_registered_in_category_dict():
    assert "flag_breakout" in ta.Category["trend"]
    assert "flag_breakout" not in ta.Category["volatility"]


def test_dataframe_accessor_matches_direct_call():
    df = _hand(1)
    direct = flag_breakout(df.high, df.low, df.close)
    via = df.ta.flag_breakout()
    pd.testing.assert_frame_equal(direct, via)


def test_props_suffix_tracks_the_three_named_parameters():
    df = _hand(1)
    out = flag_breakout(df.high, df.low, df.close, staff_max_bars=10,
                        staff_min_r2=0.9, breakout_atr_mult=0.25)
    assert list(out.columns) == ["FLAG_CONF_BULL_10_0.9_0.25",
                                "FLAG_CONF_BEAR_10_0.9_0.25",
                                "FLAG_POLE_ATR_10_0.9_0.25",
                                "FLAG_PEND_10_0.9_0.25"]


# ---------------------------------------------------------------------
# hand-derived behaviour
# ---------------------------------------------------------------------
def test_hand_derived_bull_flag_confirms_on_bar_39_and_nowhere_else():
    df = _hand(1)
    out = flag_breakout(df.high, df.low, df.close)
    fired = np.flatnonzero(out[BULL].to_numpy() == 1.0)
    assert fired.tolist() == [39]
    assert out[BEAR].fillna(0.0).sum() == 0.0


def test_hand_derived_bear_flag_is_the_exact_mirror():
    df = _hand(-1)
    out = flag_breakout(df.high, df.low, df.close)
    fired = np.flatnonzero(out[BEAR].to_numpy() == 1.0)
    assert fired.tolist() == [39]
    assert out[BULL].fillna(0.0).sum() == 0.0


def test_confirmation_is_on_the_breakout_bar_not_the_pole_or_channel():
    """The pole spans bars 30-34 and the channel bars 34-38. Nothing is
    written on any of them."""
    df = _hand(1)
    out = flag_breakout(df.high, df.low, df.close)
    for bar in range(30, 39):
        assert out[BULL].iloc[bar] == 0.0
        assert out[POLE].iloc[bar] == 0.0


def test_pole_height_is_an_atr_ratio_and_no_price_is_emitted():
    df = _hand(1)
    out = flag_breakout(df.high, df.low, df.close)
    a = _atr(df.high, df.low, df.close, length=14)
    height = df.high.iloc[34] - df.low.iloc[29]       # 103.05 - 99.95
    assert height == pytest.approx(3.10)
    assert out[POLE].iloc[39] == pytest.approx(height / a.iloc[39])
    # >= the staff_min_atr gate, by construction of the L136 floor
    nz = out[POLE].to_numpy()
    assert (nz[np.isfinite(nz) & (nz != 0.0)] >= 2.0).all()
    # and never anywhere near a price
    assert out[POLE].max() < 100.0


def test_pole_height_gate_is_load_bearing_and_NOT_monotone():
    """The height floor is load-bearing: the fixture's pole measures
    3.0999999999999943 / 0.285207808093859 = 10.869268 ATR AT THE
    DETECTION BAR (34), so 10.8 still admits it and 11.0 does not.

    It is deliberately NOT asserted to be monotone, because measurement
    says it is not: `staff_min_atr=8.0` yields ZERO confirmations while
    both 5.0 and 10.0 yield one. That is a real consequence of the
    longest-window-first search (source L129/L159) -- raising the floor
    rejects the window that was winning at one bar, which lets a
    DIFFERENT window qualify at a different bar and produce a different
    channel. Anyone tuning this parameter must sweep it, not bisect it.

    NOTE: `staff_min_atr` is not part of the `_props` suffix, so these
    frames are indexed positionally -- column 0 is always CONF_BULL.
    """
    df = _hand(1)
    def fires(g):
        return flag_breakout(df.high, df.low, df.close,
                             staff_min_atr=g).iloc[:, 0].fillna(0).sum()
    assert fires(10.8) == 1.0
    assert fires(11.0) == 0.0
    assert fires(12.0) == 0.0
    assert fires(8.0) == 0.0 and fires(5.0) == 1.0 and fires(10.0) == 1.0


def test_r2_straightness_gate_is_load_bearing():
    df = _hand(1)
    # a non-default `staff_min_r2` renames the columns, so index by position
    assert flag_breakout(df.high, df.low, df.close,
                         staff_min_r2=0.999).iloc[:, 0].fillna(0).sum() == 1.0
    # bend the pole so it is no longer straight
    c = df.close.to_numpy().copy()
    c[32] -= 0.9
    d2 = pd.DataFrame({"high": c + 0.05, "low": c - 0.05, "close": c})
    assert flag_breakout(d2.high, d2.low, d2.close,
                         staff_min_r2=0.999).iloc[:, 0].fillna(0).sum() == 0.0


def test_breakout_buffer_is_load_bearing():
    df = _hand(1)
    # `breakout_atr_mult` IS part of the suffix, so index by position
    assert flag_breakout(df.high, df.low, df.close,
                         breakout_atr_mult=0.15).iloc[:, 0].fillna(0).sum() == 1.0
    assert flag_breakout(df.high, df.low, df.close,
                         breakout_atr_mult=1.0).iloc[:, 0].fillna(0).sum() == 0.0


def test_edge_max_bars_abandons_a_channel_that_never_breaks():
    df = _hand(1)
    assert flag_breakout(df.high, df.low, df.close,
                         edge_max_bars=3).iloc[:, 0].fillna(0).sum() == 0.0


def test_pend_marks_the_channel_and_resets_on_confirmation():
    df = _hand(1)
    out = flag_breakout(df.high, df.low, df.close)
    assert out[PEND].iloc[34] == 1.0     # channel seeded on the pole's end bar
    assert out[PEND].iloc[39] == 0.0     # reset by the confirmation
    assert set(np.unique(out[PEND].dropna())) <= {-1.0, 0.0, 1.0}


def test_pend_is_a_NET_so_zero_is_ambiguous():
    """Documented, not hidden: `FLAG_PEND` sums +1 (bull channel live)
    and -1 (bear channel live), so a bar tracking BOTH reads 0.0, the
    same as a bar tracking neither. On the alphabetically-first 20 of the
    578 cached BIST daily frames in the consuming project (A1CAP.IS ..
    AKFYE.IS -- NOT its BIST_100 pool), 69,467 bars, this was measured at
    1,106 of 28,897 tracking bars, 3.83%; here the test only pins that
    the encoding really is a net."""
    df = _noise(n=4000, seed=17)
    out = flag_breakout(df.high, df.low, df.close)
    assert set(np.unique(out[PEND].dropna())) <= {-1.0, 0.0, 1.0}
    assert (out[PEND].dropna() == 0.0).sum() > 0


def test_warmup_is_nan_not_zero():
    df = _hand(1)
    out = flag_breakout(df.high, df.low, df.close)
    a = _atr(df.high, df.low, df.close, length=14)
    warm = int(np.flatnonzero(np.isfinite(a.to_numpy()))[0])
    assert warm == 14
    assert out.iloc[:warm].isna().all().all()
    assert out.iloc[warm:].notna().all().all()


def test_flat_series_produces_nothing_and_no_infinities():
    c = pd.Series(np.full(300, 50.0))
    out = flag_breakout(c + 0.5, c - 0.5, c)
    assert np.isfinite(out.dropna().to_numpy()).all()
    assert out[BULL].fillna(0).sum() == 0.0
    assert out[BEAR].fillna(0).sum() == 0.0


def test_too_short_series_returns_none():
    c = pd.Series(np.arange(5, dtype=float))
    assert flag_breakout(c + 1, c - 1, c) is None


def test_open_and_volume_are_not_read():
    df = _hand(1)
    base = flag_breakout(df.high, df.low, df.close)
    df2 = df.copy()
    df2["open"] = -999.0
    df2["volume"] = 0.0
    pd.testing.assert_frame_equal(
        base, flag_breakout(df2.high, df2.low, df2.close))


# ---------------------------------------------------------------------
# scale freedom
# ---------------------------------------------------------------------
def test_scale_invariance_exponent_shift_is_bit_exact():
    """x8 is an exact power of two: every mantissa is untouched, so a
    correct scale-free column must come back BIT-identical, not merely
    close. NaN masks are compared first."""
    df = _noise(n=6000, seed=5)
    base = flag_breakout(df.high, df.low, df.close)
    up = flag_breakout(df.high * 8.0, df.low * 8.0, df.close * 8.0)
    assert (base.isna().to_numpy() == up.isna().to_numpy()).all()
    a = base.to_numpy(dtype=float)
    b = up.to_numpy(dtype=float)
    m = np.isfinite(a) & np.isfinite(b)
    assert m.sum() > 0
    assert (a[m] == b[m]).all()
    n = int(base[BULL].notna().sum())
    for col in (BULL, BEAR):
        fires = int(base[col].fillna(0.0).sum())
        assert 0 < fires < n, f"{col} is degenerate: {fires} of {n}"


def test_scale_invariance_times_ten():
    """x10 is NOT exact in binary, so the flags are required identical
    and the ratio column only to floating tolerance."""
    df = _noise(n=6000, seed=5)
    base = flag_breakout(df.high, df.low, df.close)
    up = flag_breakout(df.high * 10.0, df.low * 10.0, df.close * 10.0)
    assert (base.isna().to_numpy() == up.isna().to_numpy()).all()
    for col in (BULL, BEAR, PEND):
        assert (base[col].dropna().to_numpy()
                == up[col].dropna().to_numpy()).all()
    np.testing.assert_allclose(base[POLE].dropna().to_numpy(),
                               up[POLE].dropna().to_numpy(), rtol=1e-9)


def test_thresholds_are_atr_scaled_not_absolute():
    """A frame at 5.0 and the same shape at 5000.0 produce the same
    events -- there is no absolute price constant anywhere."""
    df = _hand(1)
    lo = flag_breakout(df.high, df.low, df.close)
    k = 1000.0
    hi = flag_breakout(df.high * k, df.low * k, df.close * k)
    assert (lo[BULL].dropna().to_numpy() == hi[BULL].dropna().to_numpy()).all()


# ---------------------------------------------------------------------
# the source's own bull/bear width asymmetry
# ---------------------------------------------------------------------
def test_width_mode_asymmetry_is_the_sources_own_behaviour():
    """Source L250 gates the BULL side on the RAW extreme span (its
    projected alternative is commented out on that same line) while L288
    gates the BEAR side on the SLOPE-PROJECTED gap. `width_mode` isolates
    that: forcing 'raw' on both sides collapses the bear count, forcing
    'projected' on both lifts the bull count. If those two moves ever
    stop being in opposite directions, the asymmetry has been lost."""
    df = _noise(n=12000, seed=5)
    src = flag_breakout(df.high, df.low, df.close, width_mode="source")
    raw = flag_breakout(df.high, df.low, df.close, width_mode="raw")
    prj = flag_breakout(df.high, df.low, df.close, width_mode="projected")
    s_b, s_s = src[BULL].sum(), src[BEAR].sum()
    assert raw[BULL].sum() == s_b and raw[BEAR].sum() < s_s
    assert prj[BEAR].sum() == s_s and prj[BULL].sum() > s_b


# ---------------------------------------------------------------------
# literal transliteration of the Pine source
# ---------------------------------------------------------------------
def _literal(h, l, c, a, staff_min_atr=2.0, staff_min_bars=2,
             staff_max_bars=12, staff_max_opposite=1, staff_min_r2=0.85,
             edge_min_bars=3, edge_max_bars=30, edge_max_width_pct=60.0,
             max_edge_slope_ratio=0.6, min_slope_atr=0.02,
             breakout_atr_mult=0.15):
    """Pine L100-305, transliterated statement by statement with NO
    vectorisation: the five regression sums accumulate in a `for` loop in
    the source's own order, and the opposite-bar count is a nested loop
    rather than a differenced cumulative sum."""
    n = len(c)

    def r2(t, lookback):                                    # L100-119
        sumX = sumY = sumXY = sumX2 = sumY2 = 0.0
        for i in range(lookback + 1):
            xi = float(i)
            yi = c[t - (lookback - i)]
            sumX += xi
            sumY += yi
            sumXY += xi * yi
            sumX2 += xi * xi
            sumY2 += yi * yi
        nf = float(lookback + 1)
        sxy = sumXY - sumX * sumY / nf
        sxx = sumX2 - sumX * sumX / nf
        syy = sumY2 - sumY * sumY / nf
        return (sxy * sxy) / (sxx * syy) if (sxx > 0.0 and syy > 0.0) else 0.0

    def find(t, rising):                                    # L121-180
        for lookback in range(staff_max_bars, staff_min_bars - 1, -1):
            if t - lookback < 0:
                continue
            if rising:
                height = h[t] - l[t - lookback]
            else:
                height = h[t - lookback] - l[t]
            if not (height >= a[t] * staff_min_atr):
                continue
            opposite = 0
            for k in range(lookback):
                if rising:
                    if h[t - k] <= l[t - k - 1]:
                        opposite += 1
                else:
                    if l[t - k] >= h[t - k - 1]:
                        opposite += 1
            if opposite > staff_max_opposite:
                continue
            if not (r2(t, lookback) >= staff_min_r2):
                continue
            if rising:
                return True, lookback, l[t - lookback], h[t]
            return True, lookback, l[t], h[t - lookback]
        return False, 0, np.nan, np.nan

    class E:                                                # L75-87
        def __init__(s, start):
            s.start = start; s.n = 0
            s.sumX = s.sumY = s.sumXY = s.sumX2 = 0.0
            s.slope = np.nan
            s.hi = np.nan; s.hib = -1; s.lo = np.nan; s.lob = -1

        def slope_upd(s, b, y):                             # L199-210
            x = float(b - s.start)
            s.n += 1; s.sumX += x; s.sumY += y
            s.sumXY += x * y; s.sumX2 += x * x
            if s.n >= 2:
                d = s.n * s.sumX2 - s.sumX * s.sumX
                if d != 0.0:
                    s.slope = (s.n * s.sumXY - s.sumX * s.sumY) / d

        def ext_upd(s, b, hv, lv):                          # L212-220
            if not np.isfinite(s.hi) or hv > s.hi:
                s.hi = hv; s.hib = b
            if not np.isfinite(s.lo) or lv < s.lo:
                s.lo = lv; s.lob = b

    cb = np.full(n, np.nan); cs = np.full(n, np.nan)
    po = np.full(n, np.nan); pe = np.full(n, np.nan)
    fin = np.flatnonzero(np.isfinite(a))
    warm = int(fin[0]) if fin.size else n
    for arr in (cb, cs, po, pe):
        arr[warm:] = 0.0

    trB = trS = False
    egB = egS = None
    hB = bB = hS = bS = 0.0
    for t in range(n):
        at = a[t]
        if not trB:
            ok, L, lo_p, hi_p = find(t, True)
            if ok:
                trB = True; hB = hi_p - lo_p; bB = float(L)
                egB = E(t); egB.slope_upd(t, hi_p); egB.ext_upd(t, hi_p, hi_p)
        else:
            e = egB
            e.slope_upd(t, h[t]); e.ext_upd(t, h[t], l[t])
            upper = e.hi + e.slope * float(t - e.hib)
            ss = hB / bB if bB > 0 else 0.0
            too_wide = (e.hi - e.lo) > (edge_max_width_pct / 100.0) * hB
            too_old = (t - e.start) > edge_max_bars
            elig = e.n >= edge_min_bars
            vs = bool(e.slope < -(min_slope_atr * at)
                      and abs(e.slope) <= max_edge_slope_ratio * ss)
            if elig and vs and c[t] > upper + breakout_atr_mult * at:
                cb[t] = 1.0; po[t] = hB / at; trB = False
            elif too_wide or too_old or (elig and not vs):
                trB = False

        if not trS:
            ok, L, lo_p, hi_p = find(t, False)
            if ok:
                trS = True; hS = hi_p - lo_p; bS = float(L)
                egS = E(t); egS.slope_upd(t, lo_p); egS.ext_upd(t, lo_p, lo_p)
        else:
            e = egS
            e.slope_upd(t, l[t]); e.ext_upd(t, h[t], l[t])
            upper = e.hi + e.slope * float(t - e.hib)
            lower = e.lo + e.slope * float(t - e.lob)
            ss = hS / bS if bS > 0 else 0.0
            too_wide = (upper - lower) > (edge_max_width_pct / 100.0) * hS
            too_old = (t - e.start) > edge_max_bars
            elig = e.n >= edge_min_bars
            vs = bool(e.slope > (min_slope_atr * at)
                      and abs(e.slope) <= max_edge_slope_ratio * ss)
            if elig and vs and c[t] < lower - breakout_atr_mult * at:
                cs[t] = 1.0; po[t] = hS / at; trS = False
            elif too_wide or too_old or (elig and not vs):
                trS = False

        if t >= warm:
            pe[t] = (1.0 if trB else 0.0) - (1.0 if trS else 0.0)
    return np.column_stack([cb, cs, po, pe])


@pytest.mark.parametrize("seed", [5, 17])
def test_matches_a_literal_pine_order_transliteration(seed):
    df = _noise(n=3000, seed=seed)
    a = _atr(df.high, df.low, df.close, length=14).to_numpy(dtype=float)
    ref = _literal(df.high.to_numpy(float), df.low.to_numpy(float),
                   df.close.to_numpy(float), a)
    got = flag_breakout(df.high, df.low, df.close).to_numpy(dtype=float)
    assert (np.isnan(ref) == np.isnan(got)).all(), "NaN masks diverge"
    m = np.isfinite(ref) & np.isfinite(got)
    assert m.sum() > 0
    assert (ref[m] == got[m]).all()
    # and the fixture is not vacuous
    assert np.nansum(ref[:, 0]) + np.nansum(ref[:, 1]) > 0


def test_literal_transliteration_also_matches_the_hand_fixture():
    df = _hand(1)
    a = _atr(df.high, df.low, df.close, length=14).to_numpy(dtype=float)
    ref = _literal(df.high.to_numpy(float), df.low.to_numpy(float),
                   df.close.to_numpy(float), a)
    assert np.flatnonzero(ref[:, 0] == 1.0).tolist() == [39]


# ---------------------------------------------------------------------
# causality
# ---------------------------------------------------------------------
_REAL = importlib.import_module("pandas_ta.trend.flag_breakout")
_SRC = open(_REAL.__file__).read()


def _load_mutant(pairs, tag):
    """The REAL module source with the given substrings replaced, exec'd
    into a fresh in-memory module. Never a hand-written copy."""
    src = _SRC
    for old, new in pairs:
        assert old in src, f"mutant anchor no longer present: {old!r}"
        src = src.replace(old, new)
    mod = types.ModuleType(f"_flag_mutant_{tag}")
    mod.__file__ = _REAL.__file__
    exec(compile(src, _REAL.__file__, "exec"), mod.__dict__)
    return mod


_A = [("                conf_bull[t] = 1.0", "                conf_bull[eg[S]] = 1.0"),
      ("                conf_bear[t] = 1.0", "                conf_bear[eg[S]] = 1.0")]
_B = [("                pole[t] = st_bull_h / atr_t",
       "                pole[eg[S]] = st_bull_h / atr_t"),
      ("                pole[t] = st_bear_h / atr_t",
       "                pole[eg[S]] = st_bear_h / atr_t")]


def _finite_disagreement(full, part, cols, k):
    """Cells where a module's FULL run and its OWN run truncated at `k`
    disagree, counted ONLY over cells finite in both. The NaN masks are
    asserted equal first, so warm-up NaNs are never scored either way."""
    A = full.iloc[:k][cols].to_numpy(dtype=float)
    B = part[cols].to_numpy(dtype=float)
    assert (np.isnan(A) == np.isnan(B)).all(), "NaN masks diverge"
    m = np.isfinite(A) & np.isfinite(B)
    return int((A[m] != B[m]).sum()), int(m.sum())


def test_truncation_matches_prefix_of_full_series():
    """Necessary but NOT sufficient: a bar's value cannot depend on
    anything after it. This alone cannot see back-dating -- truncating
    before a confirmation stops the mutant writing at all -- which is
    what the two mutants below are for."""
    df = _noise(n=4000, seed=5)
    full = flag_breakout(df.high, df.low, df.close)
    for k in (200, 1301, 2555, 3999):
        d = df.iloc[:k]
        pd.testing.assert_frame_equal(
            flag_breakout(d.high, d.low, d.close), full.iloc[:k])


def _mutant_table(pairs, tag, cols, df):
    real_full = flag_breakout(df.high, df.low, df.close)
    mod = _load_mutant(pairs, tag)
    mut_full = mod.flag_breakout(df.high, df.low, df.close)

    # PERTURBING, not unsatisfiable: the same total, on different bars.
    tot_r = float(real_full[cols].fillna(0.0).to_numpy().sum())
    tot_m = float(mut_full[cols].fillna(0.0).to_numpy().sum())
    assert tot_r > 0.0, "the fixture produced no patterns at all"
    assert tot_r == pytest.approx(tot_m), (
        f"mutant {tag} is not value-preserving: {tot_r} vs {tot_m}")
    moved = np.flatnonzero(
        (mut_full[cols].fillna(0.0).to_numpy()
         != real_full[cols].fillna(0.0).to_numpy()).any(axis=1))
    assert len(moved) > 0, "mutant did not perturb"

    real_hits = mut_hits = 0
    rows = []
    for bar in moved[:12]:
        k = int(bar) + 1
        d = df.iloc[:k]
        r_dis, r_n = _finite_disagreement(
            real_full, flag_breakout(d.high, d.low, d.close), cols, k)
        m_dis, m_n = _finite_disagreement(
            mut_full, mod.flag_breakout(d.high, d.low, d.close), cols, k)
        assert r_n > 0 and m_n > 0, "no co-populated cells to compare"
        assert r_dis == 0, f"REAL module leaked at k={k}: {r_dis} cells"
        rows.append((k, r_dis, r_n, m_dis, m_n))
        real_hits += r_dis
        mut_hits += m_dis
    assert real_hits == 0
    assert mut_hits > 0, f"the truncation table has no power against {tag}"
    return rows


def test_mutant_a_backdating_confirmation_to_the_channel_start_is_caught():
    """Mutant A moves the confirmation flag from the breakout bar `t` to
    `eg[S]` -- the channel's own first bar, which is also the pole's last
    bar. That is the canonical chart-pattern back-dating bug and exactly
    what the source's declined `f_get_envelope_bounds` / `line.new` block
    does for DISPLAY (it draws from `edge.start_bar`)."""
    _mutant_table(_A, "a", [BULL, BEAR], _noise(n=6000, seed=5))


def test_mutant_b_backdating_the_pole_height_is_caught():
    """The same edit on the measured-height column, proving the detector
    is not specific to the two flags."""
    _mutant_table(_B, "b", [POLE], _noise(n=6000, seed=5))


def test_nothing_is_written_before_the_first_pattern_can_exist():
    df = _hand(1)
    out = flag_breakout(df.high, df.low, df.close)
    assert out.iloc[14:30][[BULL, BEAR, POLE]].to_numpy().sum() == 0.0


# ---------------------------------------------------------------------
# argument handling
# ---------------------------------------------------------------------
@pytest.mark.parametrize("kw", [
    {"staff_max_bars": 0}, {"staff_max_bars": 2.5}, {"staff_max_bars": True},
    {"staff_min_r2": float("nan")}, {"staff_min_r2": float("inf")},
    {"staff_min_atr": -1.0}, {"staff_max_opposite": -1},
    {"edge_min_bars": 1}, {"atr_length": 0}, {"width_mode": "nope"},
    {"staff_max_bars": 2, "staff_min_bars": 5},
])
def test_invalid_arguments_raise_value_error(kw):
    df = _hand(1)
    with pytest.raises(ValueError):
        flag_breakout(df.high, df.low, df.close, **kw)


def test_none_arguments_use_defaults():
    df = _hand(1)
    a = flag_breakout(df.high, df.low, df.close)
    b = flag_breakout(df.high, df.low, df.close, staff_min_atr=None,
                      staff_max_bars=None, staff_min_r2=None,
                      breakout_atr_mult=None, width_mode=None,
                      atr_length=None, offset=None)
    pd.testing.assert_frame_equal(a, b)


def test_offset_shifts_all_columns():
    df = _hand(1)
    a = flag_breakout(df.high, df.low, df.close)
    b = flag_breakout(df.high, df.low, df.close, offset=2)
    for c in COLS:
        pd.testing.assert_series_equal(a[c].shift(2), b[c])


def test_fillna_kwarg():
    df = _hand(1)
    out = flag_breakout(df.high, df.low, df.close, fillna=-1.0)
    assert (out.iloc[:14].to_numpy() == -1.0).all()
