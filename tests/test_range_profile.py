# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.volatility.range_profile` -- Range Profile
Oscillator (RPO), port of TradingView `atvJpWjW`.

What this file is built around:

* A HAND-DERIVED fixture at `lookback=5`, `bins=4`, `ob_os_level=50`,
  small enough that the bin counts, the modal bin, the value-area
  edges, the midline price and the oscillator value are all worked out
  on paper in the test's own docstring and asserted as literals --
  never read back out of the module and re-asserted against itself.

* THE SHARED-KERNEL CLAIM IS A TEST, NOT PROSE. The module docstring
  claims `_value_area` is the same loop as `K0SEi3Ct` source lines
  186-198. A hand-transliterated copy of THAT source's loop is run
  against `_value_area` over randomized profiles and must agree on
  every draw.

* THE TIE-INSTABILITY CLAIM IS A TEST, NOT PROSE. The docstring says
  three equally faithful transliterations of the Pine source disagree
  with each other, which is the whole justification for porting the
  exact-arithmetic form. Both halves are measured here: the three
  transliterations are run and their disagreement counted, and this
  module is pinned bar-for-bar to the integer-count one.

* TWO CAUSALITY MUTANTS, each an `importlib` + `exec` copy of the REAL
  module source with edits applied to the source text, both PERTURBING
  (the column keeps its population; it just holds wrong values).
  Detection is a REAL-vs-MUTANT table comparing each module's FULL run
  against its OWN truncated run, because a bare prefix-truncation test
  cannot see a mutant that reads the future the same way in both runs.

* NaN masks are compared explicitly and values compared only on
  co-populated (finite-in-both) cells, so warm-up NaNs are never
  counted as agreement or as disagreement.
"""
import importlib
import math
import types

import numpy as np
import pandas as pd
import pytest

from .context import pandas_ta as ta
from pandas_ta.volatility.range_profile import (
    range_profile, _profile_bins, _poc, _value_area,
)


OSC = "RPO_OSC_110_80"
VAW = "RPO_VA_WIDTH_PCT_110_80"
UP = "RPO_BREAK_UP_110_80"
DN = "RPO_BREAK_DN_110_80"
SHIPPED = [VAW, UP, DN]          # what the engine actually receives
COLS = [OSC] + SHIPPED           # + the deleted oscillator, test-hook only


def _rp(*args, **kwargs):
    """Every property test runs against the FULL set including the
    deleted `RPO_OSC`, because that is the quantity all three shipped
    columns are derived from. `emit_osc` is a test hook, never a
    production setting -- `test_osc_is_not_shipped_by_default` pins
    that."""
    kwargs.setdefault("emit_osc", True)
    return range_profile(*args, **kwargs)


def _noise(seed=17, n=900, sigma=0.013, flat_every=25):
    """Random-walk OHLC with a sprinkling of `high == low` (limit-lock
    shaped) bars, since those are the bars the source SKIPS."""
    rng = np.random.default_rng(seed)
    close = 100.0 * np.exp(np.cumsum(rng.normal(0, sigma, n)))
    high = close * (1 + np.abs(rng.normal(0, 0.008, n)))
    low = close * (1 - np.abs(rng.normal(0, 0.008, n)))
    if flat_every:
        flat = rng.choice(n, size=max(1, n // flat_every), replace=False)
        high[flat] = close[flat]
        low[flat] = close[flat]
    return pd.DataFrame({"open": close, "high": high, "low": low,
                         "close": close})


# ---------------------------------------------------------------------
# hand-derived fixture
# ---------------------------------------------------------------------
_HAND = pd.DataFrame({
    "low":   [10.0, 20.0, 21.0, 22.0, 23.0, 24.0, 25.0, 26.0, 27.0, 28.0],
    "high":  [12.0, 22.0, 23.0, 24.0, 25.0, 26.0, 27.0, 28.0, 29.0, 30.0],
    "close": [11.0, 21.0, 22.0, 23.0, 24.0, 25.25, 26.5, 27.0, 28.0, 29.0],
})
_HP = dict(lookback=5, bins=4, ob_os_level=50.0)
_HOSC = "RPO_OSC_5_50"
_HVAW = "RPO_VA_WIDTH_PCT_5_50"
_HUP = "RPO_BREAK_UP_5_50"
_HDN = "RPO_BREAK_DN_5_50"


def test_hand_derived_bar_5():
    """`lookback=5`, `bins=4`, `ob_os_level=50`. Bar index 5 is the
    FIRST computed bar (source line 81 gates on `bar_index >= lookback`,
    so index 4 -- which already has a full 5-bar window -- is skipped).

    Its window is bars 1..5:
        low  = 20 21 22 23 24   -> minL = 20
        high = 22 23 24 25 26   -> maxH = 26
        price_range = 6, bin_size = 6/4 = 1.5
        bins: [20,21.5) [21.5,23) [23,24.5) [24.5,26]

    Spanned bins, `floor((price-20)/1.5)` clamped to [0,3]:
        bar1 20..22 -> 0..1
        bar2 21..23 -> 0..2
        bar3 22..24 -> 1..2
        bar4 23..25 -> 2..3
        bar5 24..26 -> 2..3   (floor(6/1.5)=4, clamped to 3)
        counts = [2, 3, 4, 2], total = 11

    modal bin = 2 (count 4)
        mid_price = 20 + 1.5*(2+0.5) = 23.75

    value area, frac = 0.50:
        remaining = 11*0.5 - 4 = 1.5
        upper = w[3] = 2, lower = w[1] = 3 -> 2 >= 3 is FALSE, so the
        loop steps DOWN: lo_b = 1, remaining = 1.5 - 3 = -1.5 -> stop
        lo_b = 1, hi_b = 2
        range_low  = 20 + 1*1.5   = 21.5
        range_high = 20 + 3*1.5   = 24.5
        half_range = 1.5

        RPO_OSC          = (25.25 - 23.75)/1.5 * 50 = 50.0   (exactly)
        RPO_VA_WIDTH_PCT = (24.5 - 21.5)/23.75 * 100
                         = 12.631578947368421
    """
    r = _rp(_HAND.high, _HAND.low, _HAND.close, **_HP)
    assert r[_HOSC].iloc[:5].isna().all()
    assert r[_HOSC].iloc[5] == 50.0
    assert r[_HVAW].iloc[5] == pytest.approx(3.0 / 23.75 * 100.0, rel=0, abs=1e-12)
    # the first computed bar has no previous oscillator value, so both
    # breakout flags are NaN rather than a fabricated 0.
    assert math.isnan(r[_HUP].iloc[5]) and math.isnan(r[_HDN].iloc[5])


def test_hand_derived_bar_6_and_crossover_strictness():
    """Bar 6's window is bars 2..6, the same ramp shifted up by 1:
        minL = 21, maxH = 27, bin_size = 1.5, counts = [2, 3, 4, 2]
        modal bin 2 -> mid_price = 21 + 1.5*2.5 = 24.75
        value area lo_b=1, hi_b=2 -> range 22.5 .. 25.5, half = 1.5
        RPO_OSC = (26.5 - 24.75)/1.5*50 = 58.333...

    Bar 5's oscillator is EXACTLY 50.0 = ob_os_level. `ta.crossover` is
    `osc > level and osc[1] <= level`, both strict on the current bar
    and non-strict on the previous, so 50.0 -> 58.33 IS a crossover
    (the previous bar sitting exactly ON the level does not block it).
    """
    r = _rp(_HAND.high, _HAND.low, _HAND.close, **_HP)
    assert r[_HOSC].iloc[6] == pytest.approx(1.75 / 1.5 * 50.0, rel=0, abs=1e-12)
    assert r[_HUP].iloc[6] == 1.0
    assert r[_HDN].iloc[6] == 0.0


def test_osc_is_not_shipped_by_default():
    """`RPO_OSC` was measured at Spearman +0.858558 against the
    consuming engine's `close_vs_qtr_mean_pct` and DELETED. The default
    call must not emit it, and neither must the DataFrame accessor --
    that is the whole point of the deletion."""
    d = _noise(n=400).assign(volume=1e6)
    assert list(range_profile(d.high, d.low, d.close).columns) == SHIPPED
    assert list(d.ta.range_profile().columns) == SHIPPED
    assert OSC not in d.ta.range_profile().columns


def test_column_names_and_shape():
    d = _noise(n=400)
    r = _rp(d.high, d.low, d.close)
    assert list(r.columns) == COLS
    assert r.name == "RPO_110_80"
    assert r.category == "volatility"
    r2 = _rp(d.high, d.low, d.close, lookback=60, ob_os_level=70.5)
    assert list(r2.columns) == ["RPO_OSC_60_70.5", "RPO_VA_WIDTH_PCT_60_70.5",
                                "RPO_BREAK_UP_60_70.5", "RPO_BREAK_DN_60_70.5"]


def test_registered_and_accessor():
    assert "range_profile" in ta.Category["volatility"]
    d = _noise(n=300)
    d = d.assign(volume=1e6)
    r = d.ta.range_profile(emit_osc=True)
    assert list(r.columns) == COLS


def test_warmup_is_exactly_lookback_bars():
    """Source line 81 is `bar_index >= lookback`, so the first
    populated index is `lookback`, not `lookback - 1`."""
    d = _noise(n=400)
    r = _rp(d.high, d.low, d.close, lookback=110)
    first = int(np.argmax(r[OSC].notna().to_numpy()))
    assert first == 110
    assert r[OSC].iloc[:110].isna().all()


def test_no_volume_argument():
    """The Pine source reads no volume field anywhere (`grep -c
    '\\bvolume\\b'` on it returns 0), so `range_profile` must not take
    one. This is what makes it a volatility column rather than a
    volume-profile one."""
    import inspect
    assert "volume" not in inspect.signature(range_profile).parameters


# ---------------------------------------------------------------------
# the shared kernel
# ---------------------------------------------------------------------
def test_profile_bins_span_matches_the_sources_nested_loop():
    """`mode="span"` vs a literal transliteration of atvJpWjW lines
    98-110 (`if candle_size > 0`, clamped floor indices, inner
    `for b = b1 to b2`)."""
    rng = np.random.default_rng(4)
    for _ in range(40):
        m, bins = 30, 12
        lo_edge = float(rng.uniform(5, 500))
        bin_size = float(rng.uniform(0.01, 3.0))
        span = bins * bin_size
        low = lo_edge + rng.uniform(-0.2 * span, 0.9 * span, m)
        high = low + rng.uniform(0, 0.4 * span, m)
        high[rng.integers(0, m, 4)] = low[rng.integers(0, m, 4)]  # h == l
        ref = np.zeros(bins)
        for i in range(m):
            cs = high[i] - low[i]
            if cs > 0:
                b1 = max(0, min(bins - 1, int(math.floor((low[i] - lo_edge) / bin_size))))
                b2 = max(0, min(bins - 1, int(math.floor((high[i] - lo_edge) / bin_size))))
                for b in range(b1, b2 + 1):
                    ref[b] += 1.0
        got = _profile_bins(high, low, lo_edge, bin_size, bins, mode="span")
        np.testing.assert_array_equal(got, ref)


def test_profile_bins_span_skips_zero_range_bars():
    """`if candle_size > 0` (source line 98): a bar with high == low --
    a BIST limit-locked bar -- deposits nothing at all."""
    high = np.array([10.0, 11.0, 11.0])
    low = np.array([10.0, 10.0, 11.0])
    w = _profile_bins(high, low, 10.0, 0.5, 4, mode="span")
    assert w.sum() == 3.0   # only the middle bar, spanning bins 0,1,2
    np.testing.assert_array_equal(w, np.array([1.0, 1.0, 1.0, 0.0]))


def test_profile_bins_overlap_matches_K0SEi3Ct():
    """`mode="overlap"` vs a literal transliteration of K0SEi3Ct source
    lines 166-175 -- the fill rule the volume-profile sibling needs."""
    rng = np.random.default_rng(9)
    for _ in range(30):
        m, bins = 25, 10
        lo_edge = float(rng.uniform(1, 100))
        bin_size = float(rng.uniform(0.05, 2.0))
        span = bins * bin_size
        low = lo_edge + rng.uniform(0, 0.8 * span, m)
        high = low + rng.uniform(0, 0.3 * span, m)
        high[:3] = low[:3]
        vol = rng.uniform(1, 1e4, m)
        ref = np.zeros(bins)
        for i in range(m):
            h, l, v = high[i], low[i], vol[i]
            if h <= l:
                idx = min(bins - 1, max(0, int(math.floor((h - lo_edge) / bin_size))))
                ref[idx] += v
            else:
                for j in range(bins):
                    b_bot = lo_edge + j * bin_size
                    ov = min(h, b_bot + bin_size) - max(l, b_bot)
                    if ov > 0:
                        ref[j] += v * ov / (h - l)
        got = _profile_bins(high, low, lo_edge, bin_size, bins,
                            mode="overlap", weight=vol)
        np.testing.assert_allclose(got, ref, rtol=1e-12, atol=1e-12)


def test_profile_bins_point_mode():
    """`mode="point"` -- one deposit per bar into the bin holding
    `price` (Vrrujyso lines 126-129 use hlc3)."""
    price = np.array([10.2, 10.9, 11.6, 99.0, -5.0])
    w = _profile_bins(np.zeros(5), np.zeros(5), 10.0, 0.5, 4,
                      mode="point", price=price,
                      weight=np.array([1.0, 2.0, 3.0, 4.0, 5.0]))
    # 10.2->bin0, 10.9->bin1, 11.6->bin3, 99->clamped bin3, -5->clamped bin0
    np.testing.assert_array_equal(w, np.array([6.0, 2.0, 0.0, 7.0]))


def test_profile_bins_rejects_unknown_mode_and_bad_weight():
    with pytest.raises(ValueError):
        _profile_bins(np.ones(3), np.zeros(3), 0.0, 1.0, 4, mode="nope")
    with pytest.raises(ValueError):
        _profile_bins(np.ones(3), np.zeros(3), 0.0, 1.0, 4, weight=np.ones(2))
    with pytest.raises(ValueError):
        _profile_bins(np.ones(3), np.zeros(3), 0.0, 1.0, 4, mode="point")


def test_poc_first_index_wins_a_tie():
    """Both sources scan upward with a STRICT `>` (atvJpWjW line 117,
    K0SEi3Ct line 182), so the LOWEST index wins a tie."""
    idx, total = _poc(np.array([3.0, 5.0, 5.0, 1.0]))
    assert idx == 1 and total == 14.0
    assert _poc(np.array([])) == (0, 0.0)


def _k0sei3ct_value_area(vols, poc_idx, total, frac):
    """Hand transliteration of K0SEi3Ct source lines 186-198:

        float vaVol = pocV
        int up = pocIdx + 1
        int dn = pocIdx - 1
        while vaVol < total * vaP / 100 and (up < nB or dn >= 0)
            float vUp = up < nB  ? array.get(vols, up) : -1.0
            float vDn = dn >= 0  ? array.get(vols, dn) : -1.0
            if vUp >= vDn
                vaVol += vUp
                up += 1
            else
                vaVol += vDn
                dn -= 1
        [vols, pocIdx, dn + 1, up - 1, total]
    """
    n_b = len(vols)
    va_vol = vols[poc_idx]
    up, dn = poc_idx + 1, poc_idx - 1
    while va_vol < total * frac and (up < n_b or dn >= 0):
        v_up = vols[up] if up < n_b else -1.0
        v_dn = vols[dn] if dn >= 0 else -1.0
        if v_up >= v_dn:
            va_vol += v_up
            up += 1
        else:
            va_vol += v_dn
            dn -= 1
    return dn + 1, up - 1


def test_value_area_is_the_same_loop_as_K0SEi3Ct():
    """The module docstring's shared-kernel claim, mechanically. Run on
    INTEGER weights so that `remaining > 0` and `vaVol < target` are the
    same test rather than two float roundings of it -- which is exactly
    the population this port runs on."""
    rng = np.random.default_rng(21)
    checked = 0
    for _ in range(600):
        n_b = int(rng.integers(3, 40))
        w = rng.integers(0, 25, n_b).astype(float)
        if w.sum() == 0:
            continue
        poc, total = _poc(w)
        frac = float(rng.choice([0.5, 0.68, 0.7, 0.8, 0.9, 1.0]))
        assert _value_area(w, poc, total, frac) == \
            _k0sei3ct_value_area(w, poc, total, frac)
        checked += 1
    assert checked > 500


def test_value_area_tie_breaks_toward_the_upper_side():
    """`upper >= lower` (atvJpWjW line 137) / `vUp >= vDn` (K0SEi3Ct
    line 192): on an exact tie both sources take the UPPER neighbour."""
    w = np.array([2.0, 4.0, 10.0, 4.0, 2.0])       # total 22, symmetric
    # target 22*0.6 = 13.2, remaining after the modal bin = 3.2. The two
    # neighbours are both 4.0 -- an exact tie -- and one step settles it,
    # so the side taken is visible in the result: UP, not down.
    assert _value_area(w, 2, 22.0, 0.6) == (2, 3)
    # a second step then has to go down (2 vs 4), which is the control:
    # the loop is not simply biased upward forever.
    assert _value_area(w, 2, 22.0, 0.7) == (1, 3)


def test_value_area_degenerate_inputs():
    assert _value_area(np.zeros(5), 2, 0.0, 0.8) == (2, 2)
    assert _value_area(np.array([]), 0, 0.0, 0.8) == (0, 0)
    # frac = 1.0 must enclose the whole profile
    w = np.array([1.0, 5.0, 2.0, 3.0])
    assert _value_area(w, 1, 11.0, 1.0) == (0, 3)


# ---------------------------------------------------------------------
# correctness vs transliterations of the Pine source
# ---------------------------------------------------------------------
def _transliterate(h, l, c, mode, lookback=110, bins=50, level=80.0,
                   min_range_pct=0.001):
    """Literal, loop-for-loop transliteration of atvJpWjW lines 80-150.

    `mode` selects the per-bar deposit:
        'lit'   -> `candle_size * (bin_size / candle_size)`, verbatim
        'exact' -> `bin_size`, its algebraic value
        'count' -> `1.0`, the constant factor dropped (what this port
                   implements)
    """
    n = len(c)
    osc = [float("nan")] * n
    r_hi = r_lo = mid_price = float("nan")
    for t in range(n):
        if t >= lookback:
            min_l, max_h = l[t], h[t]
            for i in range(1, lookback):
                min_l = min(min_l, l[t - i])
                max_h = max(max_h, h[t - i])
            pr = max_h - min_l
            if pr > min_range_pct * abs(max_h + min_l) / 2.0 and pr > 0:
                bs = pr / bins
                w = [0.0] * bins
                for i in range(lookback):
                    hh, ll = h[t - i], l[t - i]
                    cs = hh - ll
                    if cs > 0:
                        add = (cs * (bs / cs) if mode == "lit"
                               else bs if mode == "exact" else 1.0)
                        b1 = max(0, min(bins - 1, int(math.floor((ll - min_l) / bs))))
                        b2 = max(0, min(bins - 1, int(math.floor((hh - min_l) / bs))))
                        for b in range(b1, b2 + 1):
                            w[b] += add
                mid_bin, mx = 0, -1e10
                for i in range(bins):
                    if w[i] > mx:
                        mx, mid_bin = w[i], i
                mid_price = min_l + bs * (mid_bin + 0.5)
                total = sum(w)
                if total > 0:
                    rem = total * (level / 100) - w[mid_bin]
                    low_b = high_b = mid_bin
                    while rem > 0 and (low_b > 0 or high_b < bins - 1):
                        up = w[high_b + 1] if high_b < bins - 1 else -1
                        dn = w[low_b - 1] if low_b > 0 else -1
                        if up >= dn and up >= 0:
                            high_b += 1
                            rem -= up
                        elif dn >= 0:
                            low_b -= 1
                            rem -= dn
                        else:
                            break
                    r_lo = min_l + low_b * bs
                    r_hi = min_l + (high_b + 1) * bs
        half = (r_hi - r_lo) / 2 if r_hi == r_hi and r_lo == r_lo else float("nan")
        if half == half and half > 0 and mid_price == mid_price:
            osc[t] = (c[t] - mid_price) / half * level
    return np.array(osc)


_XLAT_SEEDS = (17, 5, 99, 404)
_XLAT_N = 520


def _xlat_frames():
    for seed in _XLAT_SEEDS:
        d = _noise(seed=seed, n=_XLAT_N)
        yield d


def test_matches_an_integer_weight_transliteration_exactly():
    """The port's ONLY correctness anchor that can be bit-exact: the
    difference-array fill and the vectorised rolling min/max must
    reproduce the source's nested loops exactly once the deposit is the
    constant this port drops."""
    total_cells = 0
    for d in _xlat_frames():
        got = _rp(d.high, d.low, d.close)[OSC].to_numpy()
        ref = _transliterate(d.high.tolist(), d.low.tolist(),
                             d.close.tolist(), "count")
        assert np.array_equal(np.isnan(got), np.isnan(ref)), "NaN masks differ"
        both = np.isfinite(got) & np.isfinite(ref)
        assert both.sum() > 300
        np.testing.assert_array_equal(got[both], ref[both])
        total_cells += int(both.sum())
    assert total_cells > 1500


def test_transliterations_of_the_source_disagree_with_each_other():
    """The justification for substitution 2 in the module docstring:
    the source's stopping test (`remaining > 0`) and its modal-bin
    argmax are EXACT-TIE comparisons, so three equally faithful
    transliterations of the same Pine lines do not agree. There is
    therefore no bit-exact "Pine answer" to reproduce, and the
    exact-arithmetic form this module ships is the deterministic one.

    Asserted as strict inequalities on the disagreement counts (not as
    the exact numbers published in the docstring) so the test pins the
    CLAIM rather than one numpy build's rounding.
    """
    n_cells = lit_exact = lit_count = exact_count = 0
    for d in _xlat_frames():
        hh, ll, cc = d.high.tolist(), d.low.tolist(), d.close.tolist()
        a = _transliterate(hh, ll, cc, "lit")
        b = _transliterate(hh, ll, cc, "exact")
        c = _transliterate(hh, ll, cc, "count")
        m = np.isfinite(a) & np.isfinite(b) & np.isfinite(c)
        n_cells += int(m.sum())
        lit_exact += int((a[m] != b[m]).sum())
        lit_count += int((a[m] != c[m]).sum())
        exact_count += int((b[m] != c[m]).sum())
    assert n_cells > 1500
    assert lit_exact > 0, "no tie instability observed; claim is stale"
    assert lit_count > lit_exact > exact_count, (
        f"expected the literal form to be the noisiest: "
        f"lit/exact={lit_exact} lit/count={lit_count} exact/count={exact_count}")
    # and the instability is a small minority of bars, not the norm
    assert lit_count / n_cells < 0.15


# ---------------------------------------------------------------------
# scale invariance
# ---------------------------------------------------------------------
def test_scale_invariance_bit_exact_on_a_power_of_two():
    """Multiplying every price by 8 is exact in IEEE-754, and every
    operation in this indicator is either a difference of two prices or
    a ratio of two such differences, so the columns must come back
    BIT-identical -- not merely close."""
    d = _noise(n=800)
    a = _rp(d.high, d.low, d.close)
    b = _rp(d.high * 8, d.low * 8, d.close * 8)
    for col in COLS:
        x, y = a[col].to_numpy(), b[col].to_numpy()
        assert np.array_equal(np.isnan(x), np.isnan(y)), f"{col}: NaN masks differ"
        both = np.isfinite(x) & np.isfinite(y)
        assert both.sum() > 300, f"{col}: nothing co-populated"
        np.testing.assert_array_equal(x[both], y[both])
    # non-degeneracy: the flags actually fire, and not on every bar
    n_up = int(np.nansum(a[UP].to_numpy()))
    n_dn = int(np.nansum(a[DN].to_numpy()))
    pop = int(a[UP].notna().sum())
    assert 0 < n_up < pop, f"RPO_BREAK_UP degenerate: {n_up} of {pop}"
    assert 0 < n_dn < pop, f"RPO_BREAK_DN degenerate: {n_dn} of {pop}"
    assert a[OSC].std() > 1.0


def test_scale_invariance_on_a_non_power_of_two():
    """x10 is not exact in binary, so this one is a tolerance test --
    stated explicitly rather than hidden behind a default."""
    d = _noise(seed=31, n=700)
    a = _rp(d.high, d.low, d.close)
    b = _rp(d.high * 10, d.low * 10, d.close * 10)
    for col in (OSC, VAW):
        x, y = a[col].to_numpy(), b[col].to_numpy()
        assert np.array_equal(np.isnan(x), np.isnan(y)), f"{col}: NaN masks differ"
        both = np.isfinite(x) & np.isfinite(y)
        assert both.sum() > 300
        np.testing.assert_allclose(x[both], y[both], rtol=1e-9, atol=1e-9)
    for col in (UP, DN):
        x, y = a[col].to_numpy(), b[col].to_numpy()
        both = np.isfinite(x) & np.isfinite(y)
        # a x10 rescale can move a knife-edge value-area tie, so allow a
        # handful of flag disagreements but require overwhelming
        # agreement -- and require the flags to be non-degenerate.
        agree = int((x[both] == y[both]).sum())
        assert agree / both.sum() > 0.99, f"{col}: only {agree}/{both.sum()} agree"
    assert 0 < int(np.nansum(a[UP].to_numpy())) < int(a[UP].notna().sum())


def test_no_raw_price_level_is_ever_emitted():
    """Scale-free discipline: on a series living around 100, no emitted
    column may carry values of the price's own order for the whole
    column."""
    d = _noise(n=900)
    r = _rp(d.high, d.low, d.close)
    assert r[VAW].dropna().max() < 100.0     # value-area width as % of price
    assert r[VAW].dropna().min() >= 0.0


# ---------------------------------------------------------------------
# causality
# ---------------------------------------------------------------------
_REAL = importlib.import_module("pandas_ta.volatility.range_profile")
_SRC = open(_REAL.__file__, encoding="utf-8").read()


def _load_mutant(pairs, tag):
    """The REAL module source with each `(old, new)` applied exactly
    once, exec'd into a fresh in-memory module. Never a hand-written
    copy."""
    src = _SRC
    for old, new in pairs:
        assert old in src, f"mutant anchor no longer present: {old!r}"
        assert src.count(old) == 1, f"mutant anchor is not unique: {old!r}"
        src = src.replace(old, new)
    mod = types.ModuleType(f"_rpo_mutant_{tag}")
    mod.__file__ = _REAL.__file__
    exec(compile(src, _REAL.__file__, "exec"), mod.__dict__)
    return mod


# Mutant A: slide the WHOLE profile window one bar into the future --
# its extremes (the bin edges) and the bars deposited into the bins.
_MUT_A = [
    ("        min_l = roll_min[t]\n        max_h = roll_max[t]",
     "        _tf = min(t + 1, n - 1)\n"
     "        min_l = roll_min[_tf]\n        max_h = roll_max[_tf]"),
    ("                w = _profile_bins(h_v[t - lookback + 1:t + 1],\n"
     "                                  l_v[t - lookback + 1:t + 1],",
     "                _s = min(t + 1, n - 1)\n"
     "                w = _profile_bins(h_v[_s - lookback + 1:_s + 1],\n"
     "                                  l_v[_s - lookback + 1:_s + 1],"),
]

# Mutant B: leave the profile alone; price the oscillator off TOMORROW's
# close. Every populated bar keeps a value, it is just the wrong one.
_MUT_B = [
    ("                osc[t] = (c_v[t] - mid_price) / half_range * ob_os_level",
     "                osc[t] = (c_v[min(t + 1, n - 1)] - mid_price) / half_range * ob_os_level"),
]


def _finite_disagreement(full, part, k):
    """Cells where a module's FULL run and its OWN run truncated at `k`
    disagree, counted ONLY over cells finite in both, plus the count of
    NaN-mask mismatches."""
    a = full.iloc[:k].to_numpy(dtype=float)
    b = part.to_numpy(dtype=float)
    both = np.isfinite(a) & np.isfinite(b)
    mask_mismatch = int((np.isnan(a) != np.isnan(b)).sum())
    return int((a[both] != b[both]).sum()), int(both.sum()), mask_mismatch


def test_truncation_matches_prefix_of_full_series():
    """Necessary but NOT sufficient: no bar's value may depend on
    anything after it. This alone cannot see a mutant that reads the
    future the same way in the full and the truncated run -- that is
    what the mutants below are for. Run on the FULL emitted set,
    including the carried-forward `mid_price`/`range_*` state."""
    d = _noise(n=700)
    full = _rp(d.high, d.low, d.close)
    for k in (150, 301, 455, 699):
        p = d.iloc[:k]
        pd.testing.assert_frame_equal(
            range_profile(p.high, p.low, p.close, emit_osc=True), full.iloc[:k])


@pytest.mark.parametrize("pairs,tag,min_moved", [
    (_MUT_A, "a", 50),
    (_MUT_B, "b", 300),
])
def test_causality_mutants_are_caught(pairs, tag, min_moved):
    """Both mutants are PERTURBING: the column keeps its population and
    simply holds wrong values, which is asserted before any leak claim
    is made -- so "the mutant broke the column" can never be mistaken
    for "the mutant leaked".

    Detection is REAL-vs-MUTANT prefix truncation. The mutant's full run
    has already read a bar its truncated run has not, so the two
    disagree at the cut; the real module never disagrees at any k.
    """
    d = _noise(n=900)
    real_full = _rp(d.high, d.low, d.close)[OSC]
    mod = _load_mutant(pairs, tag)
    mut_full = mod.range_profile(d.high, d.low, d.close, emit_osc=True)[OSC]

    r_n, m_n = int(real_full.notna().sum()), int(mut_full.notna().sum())
    assert r_n > 500 and m_n > 500, "mutant collapsed the column; not perturbing"
    assert 0.9 < m_n / r_n < 1.1, "mutant is unsatisfiable, not perturbing"

    a = real_full.to_numpy(dtype=float)
    b = mut_full.to_numpy(dtype=float)
    both = np.isfinite(a) & np.isfinite(b)
    assert both.sum() > 500, "no co-populated bars: nothing was perturbed"
    moved = np.where(both & (a != b))[0]
    assert len(moved) >= min_moved, (
        f"mutant {tag} perturbed only {len(moved)} of {int(both.sum())} "
        f"co-populated bars")

    real_hits = mut_hits = checked = 0
    for bar in moved[:: max(1, len(moved) // 12)][:12]:
        k = int(bar) + 1
        if k < 150:
            continue
        p = d.iloc[:k]
        r_dis, r_cells, r_mm = _finite_disagreement(
            real_full, range_profile(p.high, p.low, p.close, emit_osc=True)[OSC], k)
        m_dis, m_cells, m_mm = _finite_disagreement(
            mut_full, mod.range_profile(p.high, p.low, p.close, emit_osc=True)[OSC], k)
        assert r_cells > 0 and m_cells > 0, "no co-populated cells to compare"
        assert r_dis == 0 and r_mm == 0, f"REAL module leaked at k={k}"
        real_hits += r_dis
        mut_hits += m_dis + m_mm
        checked += 1
    assert checked > 0
    assert real_hits == 0
    assert mut_hits > 0, f"the truncation table has no power against mutant {tag}"


def test_carried_forward_state_is_backward_looking_only():
    """The source's `var float` carry-forward (module docstring, STATE
    CARRIED ACROSS BARS) is the one place a lookahead could hide
    without touching the window arithmetic. A run whose tail is
    replaced by garbage must leave every earlier bar untouched."""
    d = _noise(n=600)
    full = _rp(d.high, d.low, d.close)
    e = d.copy()
    e.loc[e.index[400:], ["high", "low", "close"]] *= 3.7
    tail = _rp(e.high, e.low, e.close)
    pd.testing.assert_frame_equal(full.iloc[:400], tail.iloc[:400])


# ---------------------------------------------------------------------
# the mintick substitution and the carry-forward it gates
# ---------------------------------------------------------------------
def test_min_range_pct_gates_the_rebuild_and_carries_forward():
    """A window whose whole range is below the relative floor must not
    rebuild the profile; the previous bar's midline and value area
    persist and are priced against today's close (source lines 57-59,
    89). Verified against `min_range_pct=0.0`, which reproduces "any
    strictly positive range"."""
    n = 300
    close = np.concatenate([100 + np.arange(150) * 0.5,
                            np.full(150, 175.0) + np.arange(150) * 1e-4])
    d = pd.DataFrame({"high": close + 0.01, "low": close - 0.01,
                      "close": close})
    strict = _rp(d.high, d.low, d.close, lookback=50,
                           min_range_pct=0.05)[["RPO_OSC_50_80"]]
    loose = _rp(d.high, d.low, d.close, lookback=50,
                          min_range_pct=0.0)[["RPO_OSC_50_80"]]
    a = strict["RPO_OSC_50_80"].to_numpy()
    b = loose["RPO_OSC_50_80"].to_numpy()
    both = np.isfinite(a) & np.isfinite(b)
    assert both.sum() > 100
    assert int((a[both] != b[both]).sum()) > 0, \
        "min_range_pct made no difference on a frame built to trip it"


def test_all_flat_window_refreshes_the_midline_but_not_the_value_area():
    """The source's one asymmetry, preserved: `mid_price` is assigned
    BEFORE the `total > 0` check (line 121) and `range_low`/
    `range_high` AFTER it (lines 145-146). A window in which every bar
    has high == low has zero total weight, so the midline moves and the
    value area does not."""
    n = 120
    close = 100 + np.arange(n) * 0.3
    high = close.copy()
    low = close.copy()
    # give the first 60 bars real range so a value area exists at all
    high[:60] = close[:60] + 0.4
    low[:60] = close[:60] - 0.4
    d = pd.DataFrame({"high": high, "low": low, "close": close})
    r = _rp(d.high, d.low, d.close, lookback=20, bins=8,
                      min_range_pct=0.0)
    col = "RPO_OSC_20_80"
    # bars past index ~80 sit on an all-flat window: still populated,
    # because the stale value area is carried forward.
    assert r[col].iloc[100:].notna().all()


# ---------------------------------------------------------------------
# argument handling
# ---------------------------------------------------------------------
@pytest.mark.parametrize("kw", [
    dict(lookback=0), dict(lookback=-3), dict(lookback=1),
    dict(lookback=2.5), dict(lookback=True), dict(lookback=float("nan")),
    dict(lookback=float("inf")), dict(bins=1), dict(bins=0),
    dict(ob_os_level=0.0), dict(ob_os_level=-5.0),
    dict(ob_os_level=float("nan")), dict(min_range_pct=-0.1),
    dict(min_coherent_bars=-1), dict(min_coherent_bars=2.5),
    dict(min_coherent_bars=True), dict(min_coherent_bars=111),
])
def test_bad_arguments_raise(kw):
    d = _noise(n=200)
    with pytest.raises(ValueError):
        _rp(d.high, d.low, d.close, **kw)


def test_short_series_returns_none():
    d = _noise(n=20)
    assert _rp(d.high, d.low, d.close, lookback=110) is None


def test_offset_shifts_every_column():
    d = _noise(n=400)
    a = _rp(d.high, d.low, d.close)
    b = _rp(d.high, d.low, d.close, offset=2)
    for col in COLS:
        pd.testing.assert_series_equal(b[col], a[col].shift(2))


def test_fillna_kwarg():
    d = _noise(n=300)
    r = _rp(d.high, d.low, d.close, fillna=0.0)
    assert r.notna().all().all()


def test_nan_input_does_not_raise_and_stays_nan():
    d = _noise(n=400)
    d.loc[d.index[200:206], "high"] = np.nan
    r = _rp(d.high, d.low, d.close)
    assert r[OSC].notna().sum() > 100


# ---------------------------------------------------------------------
# the incoherent-bar guard (a deviation from the source, so it is tested
# as one: both that it fires, and that turning it off restores the
# source's behaviour)
# ---------------------------------------------------------------------
def _mgros_shaped(n=400, bad_at=159):
    """A frame carrying the exact defect measured on
    `datastore/cache/MGROS_IS_1d.parquet` index 159: High AND Low blown
    up by ~6 orders of magnitude while Open/Close stay sane, and no
    close-to-close jump anywhere, so a c2c-based cleaner cannot see it.
    """
    d = _noise(seed=77, n=n, flat_every=0)
    d = d.copy()
    d.loc[d.index[bad_at], "high"] = 12_235_458.333849315
    d.loc[d.index[bad_at], "low"] = 10_991_174.435491757
    return d


def test_guard_catches_the_mgros_shaped_print():
    d = _mgros_shaped()
    c2c = d["close"].pct_change().abs()
    assert (c2c > 0.105).sum() == 0, "fixture must be invisible to a c2c cleaner"

    off = _rp(d.high, d.low, d.close, require_coherent_bars=False)
    on = _rp(d.high, d.low, d.close, require_coherent_bars=True)

    # The defect's signature is NOT an out-of-range blow-up, which is
    # what makes it dangerous: every real bar collapses into bin 0, the
    # value area is that single bin, and the oscillator PINS at exactly
    # -ob_os_level -- a plausible-looking "permanently at the oversold
    # edge" reading, with the value-area width pinned at the collapsed
    # profile's 2 * bin_size / mid_price = 200% signature.
    o_off = off[OSC].to_numpy()
    pinned = np.isclose(o_off[159:159 + 110], -80.0, rtol=0, atol=0.05)
    assert pinned.sum() > 100, f"fixture did not pin the oscillator: {pinned.sum()}"
    w_off = off[VAW].to_numpy()[159:159 + 110]
    assert np.nanmin(w_off) > 190.0 and np.nanmax(w_off) < 210.0

    o_on = on[OSC].to_numpy()
    assert np.isclose(o_on[159:159 + 110], -80.0, rtol=0, atol=0.05).sum() <= 1
    w_on = on[VAW].to_numpy()[159:159 + 110]
    assert np.nanmax(w_on) < 60.0, f"guard left the width blown out: {np.nanmax(w_on)}"

    # bounded blast radius: the profile is a fixed rolling window, so
    # nothing before the bad bar and nothing beyond `lookback` bars
    # after it may differ.
    a = off[OSC].to_numpy()
    b = on[OSC].to_numpy()
    both = np.isfinite(a) & np.isfinite(b)
    moved = np.where(both & (a != b))[0]
    assert len(moved) > 0
    assert moved.min() >= 159
    assert moved.max() <= 159 + 110


def test_guard_off_is_a_no_op_on_a_coherent_frame():
    """Every bar of a clean frame satisfies `low <= close <= high`, so
    the guard must not change a single value there -- it is a filter on
    non-bars, not a smoother."""
    d = _noise(seed=53, n=700)
    on = _rp(d.high, d.low, d.close, require_coherent_bars=True)
    off = _rp(d.high, d.low, d.close, require_coherent_bars=False)
    pd.testing.assert_frame_equal(on, off)


def test_guard_does_not_rescue_a_coherent_but_impossible_frame():
    """The ARCLK shape: `High / Low` pinned near 3.0 with `close ==
    low` for a whole era. Coherent, so the guard passes it through
    unchanged -- asserted here so the module docstring's "what the
    guard does not catch" is a tested claim, not a hedge."""
    d = _noise(seed=61, n=500, flat_every=0)
    d = d.copy()
    sl = slice(100, 300)
    d.loc[d.index[sl], "low"] = d.loc[d.index[sl], "close"]
    d.loc[d.index[sl], "high"] = d.loc[d.index[sl], "close"] * 3.0
    coherent = (d.low <= d.close) & (d.close <= d.high)
    assert bool(coherent.all()), "fixture must stay coherent"
    on = _rp(d.high, d.low, d.close, require_coherent_bars=True)
    off = _rp(d.high, d.low, d.close, require_coherent_bars=False)
    pd.testing.assert_frame_equal(on, off)


# ---------------------------------------------------------------------
# the coherence FLOOR (`min_coherent_bars`) -- the second half of the
# incoherent-bar deviation, added 2026-08-26 after review
# ---------------------------------------------------------------------
def _mostly_incoherent_prefix(n=400, bad_until=162):
    """The MGROS shape at the START of a frame: indices 0..bad_until-1
    are all incoherent, so the first bars past `bar_index >= lookback`
    have a window holding only a handful of real bars.

    Reproduces `datastore/cache/MGROS_IS_1d.parquet`, whose indices
    0-161 are all incoherent and whose bar 162 emitted a full 50-bin
    profile built from EXACTLY ONE coherent bar.
    """
    d = _noise(seed=91, n=n, flat_every=0).copy()
    # blow the High/Low apart from Open/Close, the real defect's shape:
    # `low <= close <= high` fails, no close-to-close jump anywhere.
    d.loc[d.index[:bad_until], "high"] = 12_235_458.333849315
    d.loc[d.index[:bad_until], "low"] = 10_991_174.435491757
    return d


def test_min_coherent_bars_floors_the_profile_support():
    """Without a floor, one surviving bar is enough to rebuild a full
    50-bin profile. With the shipped floor it is not.

    This is the MINOR-1 finding of the 2026-08-25 review, pinned:
    MGROS.IS bar 162 emitted `RPO_VA_WIDTH_PCT = 7.849436` from a
    110-bar window containing one coherent bar.
    """
    d = _mostly_incoherent_prefix()
    coherent = (d.low <= d.close) & (d.close <= d.high)
    assert int(coherent[:162].sum()) == 0, "fixture prefix must be all-bad"
    c2c = d["close"].pct_change().abs()
    assert int((c2c > 0.105).sum()) == 0, "fixture must be invisible to DI-1"

    unfloored = _rp(d.high, d.low, d.close, min_coherent_bars=0)
    floored = _rp(d.high, d.low, d.close)          # default = bins = 50

    # the one-bar profile exists without the floor ...
    assert np.isfinite(unfloored[VAW].to_numpy(float)[162])
    assert np.isfinite(unfloored[OSC].to_numpy(float)[162])
    # ... and is gone with it, along with every window below 50 bars.
    assert not np.isfinite(floored[VAW].to_numpy(float)[162])

    # the first bar the floored run populates has >= 50 coherent bars
    # behind it -- computed from the fixture, not read back out.
    support = pd.Series(coherent.to_numpy().astype(float)) \
        .rolling(110, min_periods=1).sum().to_numpy()
    first = int(np.flatnonzero(np.isfinite(floored[VAW].to_numpy(float)))[0])
    assert support[first] >= 50
    assert support[first - 1] < 50

    # WITHDRAWAL-ONLY: the floor may remove cells; it may never change a
    # surviving value and may never create one.
    for col in COLS:
        a = unfloored[col].to_numpy(float)
        b = floored[col].to_numpy(float)
        na_a, na_b = np.isnan(a), np.isnan(b)
        assert not (na_a & ~na_b).any(), f"{col}: floor CREATED a cell"
        both = ~na_a & ~na_b
        assert np.array_equal(a[both], b[both]), f"{col}: floor MOVED a value"
        assert (~na_a & na_b).sum() > 0, f"{col}: floor withdrew nothing"


def test_min_coherent_bars_is_monotone_in_the_floor():
    """Raising the floor may only ever remove more cells. A floor that
    let a bar back in would mean the support count is not the thing
    being thresholded."""
    d = _mostly_incoherent_prefix()
    prev = None
    for floor in (0, 5, 20, 50, 110):
        pop = _rp(d.high, d.low, d.close,
                  min_coherent_bars=floor)[VAW].notna().to_numpy()
        if prev is not None:
            assert not (pop & ~prev).any(), f"floor={floor} re-populated a bar"
        prev = pop


def test_min_coherent_bars_is_not_applied_with_the_guard_off():
    """`require_coherent_bars=False` reproduces the Pine source exactly,
    so the floor -- which is not in the source -- must not act there.
    That branch's own `min_periods=lookback` already forces full
    support, so this costs nothing."""
    d = _mostly_incoherent_prefix()
    a = _rp(d.high, d.low, d.close, require_coherent_bars=False,
            min_coherent_bars=0)
    b = _rp(d.high, d.low, d.close, require_coherent_bars=False,
            min_coherent_bars=110)
    pd.testing.assert_frame_equal(a, b)


def test_min_coherent_bars_default_is_bins_clamped_to_lookback():
    """The default is `bins`, so it moves when `bins` does -- and a
    `bins > lookback` configuration is clamped rather than flooring
    every bar out of existence."""
    d = _noise(seed=93, n=400, flat_every=0).copy()
    d.loc[d.index[:80], "high"] = 12_235_458.333849315
    d.loc[d.index[:80], "low"] = 10_991_174.435491757

    lo = _rp(d.high, d.low, d.close, lookback=110, bins=10)
    hi = _rp(d.high, d.low, d.close, lookback=110, bins=90)
    n_lo = int(lo["RPO_VA_WIDTH_PCT_110_80"].notna().sum())
    n_hi = int(hi["RPO_VA_WIDTH_PCT_110_80"].notna().sum())
    assert n_lo > n_hi, (n_lo, n_hi)

    # bins > lookback: clamped to lookback, so bars with a fully
    # coherent window still populate.
    clamped = _rp(d.high, d.low, d.close, lookback=60, bins=200)
    assert int(clamped["RPO_VA_WIDTH_PCT_60_80"].notna().sum()) > 0
