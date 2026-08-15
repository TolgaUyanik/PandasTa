# -*- coding: utf-8 -*-
"""Tests for `sd_zone_pro` (SDZ), TVPTA-6 candidate 19.

Ported from the TradingView Pine v6 source "SD Zone Pro"
(`gIs5tbMW.pine`, 440 lines).

Two kinds of test live here:

* HAND-DERIVED unit tests of the source's three faithfulness traps -- the
  global modular batch counter (Pine L112/L264), the source's degenerate
  shipped defaults (L9-10/L15-16), and the cross-side mass contamination
  (L199-213/L351-365). Each expected value was worked out from the .pine
  text first and then checked against the port, not read off the port.
* A CAUSALITY mutant (`_load_backdating_mutant`) that loads a MUTATED
  copy of the real module via `importlib` + `exec` into an in-memory
  module -- never a hand-reimplementation -- so it is provably the real
  algorithm plus one changed index. A bare prefix-truncation test
  (`test_truncation_matches_prefix_of_full_series`) is necessary but has
  no power to catch back-dating on its own; the mutant is what gives the
  cutoff its power.

Every synthetic bar below is physically valid OHLC (low <= close <=
high), asserted at construction time.
"""
import numpy as np
import pandas as pd
import pytest

from .context import pandas_ta as ta
from pandas_ta.trend.sd_zone_pro import sd_zone_pro, _Zone, _zone_distance


def _module():
    """The real SUBMODULE, not the re-exported function.

    `import pandas_ta.trend.sd_zone_pro as m` binds the FUNCTION here,
    because `pandas_ta/trend/__init__.py` rebinds that attribute on the
    package; `importlib.import_module` on the dotted path returns the
    module object whose globals the instrumentation below patches."""
    import importlib
    return importlib.import_module("pandas_ta.trend.sd_zone_pro")


def _record_zone_creations(**call_kwargs):
    """Run the port with `_Zone` swapped for a recording subclass and
    return the list of (side, mass, opened_at) it constructed. Every
    batch ends in exactly one `_Zone(...)` construction (both the absorb
    branch and the finalize branch), so this counts batches directly."""
    mod = _module()
    created = []
    real_zone = mod._Zone

    class _Recording(real_zone):
        __slots__ = ()

        def __init__(self, zid, side, top, bottom, opened_at, mass):
            created.append((side, mass, opened_at))
            real_zone.__init__(self, zid, side, top, bottom, opened_at, mass)

    mod._Zone = _Recording
    try:
        mod.sd_zone_pro(**call_kwargs)
    finally:
        mod._Zone = real_zone
    return created

IMB = "SDZ_MASS_IMBALANCE_5_3"
NEAR = "SDZ_NEAR_MASS_5_3"
DEFAULT_COLS = [IMB, NEAR]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _ohlcv(n=1200, seed=7, vol_seed=None):
    """A long random walk with lognormal volume. n defaults to 1200: the
    default (pivot_length=5, group=3) configuration needs 3 confirmed
    pivots per side before its FIRST zone exists, and both sides
    populated before `SDZ_MASS_IMBALANCE` can be non-NaN at all."""
    rng = np.random.default_rng(seed)
    close = pd.Series(100 * np.exp(np.cumsum(rng.normal(0.0003, 0.015, n))))
    high = close * (1 + np.abs(rng.normal(0, 0.006, n)))
    low = close * (1 - np.abs(rng.normal(0, 0.006, n)))
    vrng = np.random.default_rng(vol_seed if vol_seed is not None else seed + 100)
    volume = pd.Series(vrng.lognormal(12, 0.6, n))
    assert (low <= close).all() and (close <= high).all()
    return high, low, close, volume


def _sawtooth(cycles=40, up=6, down=6, amp=4.0, start=100.0, vol=1000.0):
    """A deterministic zig-zag: `cycles` repetitions of `up` rising bars
    then `down` falling bars, amplitude `amp`. Produces clean, evenly
    spaced pivot highs and lows so batch counting can be reasoned about
    by hand. Constant volume by default, so a batch's summed volume is
    exactly `group * vol`."""
    px = [start]
    for _ in range(cycles):
        for k in range(up):
            px.append(px[-1] + amp / up)
        for k in range(down):
            px.append(px[-1] - amp / down)
    close = pd.Series(px, dtype=float)
    high = close + 0.05
    low = close - 0.05
    volume = pd.Series(np.full(len(close), float(vol)))
    return high, low, close, volume


# ---------------------------------------------------------------------------
# Shape / contract
# ---------------------------------------------------------------------------

def test_default_column_names_and_shape():
    h, l, c, v = _ohlcv()
    out = sd_zone_pro(h, l, c, v)
    assert list(out.columns) == DEFAULT_COLS
    assert len(out) == len(c)
    assert out.name == "SDZ_5_3"
    assert out.category == "trend"
    assert out.index.equals(c.index)


def test_column_names_track_params():
    h, l, c, v = _ohlcv(n=600)
    out = sd_zone_pro(h, l, c, v, pivot_length=3, group=2)
    assert list(out.columns) == ["SDZ_MASS_IMBALANCE_3_2", "SDZ_NEAR_MASS_3_2"]


def test_too_short_series_returns_none():
    h, l, c, v = _ohlcv(n=1200)
    k = 2 * 5  # min_len is 2*pivot_length + 1 = 11
    assert sd_zone_pro(h.iloc[:k], l.iloc[:k], c.iloc[:k], v.iloc[:k]) is None


def test_ships_no_distance_or_broken_column():
    """SCOPE guard. This port deliberately emits neither a `*_DIST` nor a
    `*_BROKEN` column -- that lane already holds VOLSR_RES_DIST/
    VOLSR_SUP_DIST, SRF_DIST_RES/SUP, IFVG_DIST_SUP/RES, LCB_HIGH_DIST/
    LOW_DIST and the engine's own dist_to_res_level/dist_to_sup_level.
    Asserted so a later 'helpful' addition has to argue with a test."""
    h, l, c, v = _ohlcv(n=400)
    out = sd_zone_pro(h, l, c, v)
    for col in out.columns:
        assert "DIST" not in col.upper()
        assert "BROKEN" not in col.upper()


# ---------------------------------------------------------------------------
# Bounds / scale-freeness
# ---------------------------------------------------------------------------

def test_imbalance_is_bounded_and_populated():
    h, l, c, v = _ohlcv()
    out = sd_zone_pro(h, l, c, v)
    s = out[IMB].dropna()
    assert len(s) > 900, f"only {len(s)} populated bars -- fixture too short"
    assert s.min() >= -1.0 and s.max() <= 1.0
    # Both signs actually occur, so the column is not a one-sided stub.
    assert (s < 0).any() and (s > 0).any()


def test_near_mass_is_positive_and_populated():
    h, l, c, v = _ohlcv()
    s = sd_zone_pro(h, l, c, v)[NEAR].dropna()
    assert len(s) > 900
    assert (s > 0).all()


@pytest.mark.parametrize("price_mult,vol_mult", [(10.0, 1.0), (1.0, 10.0), (10.0, 10.0)])
def test_scale_invariance(price_mult, vol_mult):
    """Price x10 and volume x10, independently and together. Both output
    columns are ratios in which the respective unit cancels: the
    imbalance divides two volumes, and SDZ_NEAR_MASS divides a volume by
    a volume SMA. The zone GEOMETRY is ATR-scaled, so multiplying price
    multiplies every threshold and every level by the same factor and the
    zone population is unchanged."""
    h, l, c, v = _ohlcv()
    base = sd_zone_pro(h, l, c, v)
    scaled = sd_zone_pro(h * price_mult, l * price_mult, c * price_mult, v * vol_mult)
    for col in DEFAULT_COLS:
        a, b = base[col].to_numpy(), scaled[col].to_numpy()
        mask = np.isnan(a)
        assert (mask == np.isnan(b)).all(), f"{col}: NaN masks differ"
        assert np.nanmax(np.abs(a[~mask] - b[~mask])) < 1e-12, f"{col}: not scale-free"


# ---------------------------------------------------------------------------
# Faithfulness trap 1 -- the batch trigger is a GLOBAL MODULAR COUNTER
# ---------------------------------------------------------------------------

def test_batch_trigger_is_modular_not_a_sliding_window():
    """Pine L112: `totalLowPivots >= xGroupLow and (totalLowPivots %
    xGroupLow == 0)` fires on every N-th pivot EVER SEEN. So after a side
    has seen P pivots, the number of batches it has run must be exactly
    floor(P / group) -- not P - group + 1 (a sliding window) and not any
    other bucketing."""
    from pandas_ta.trend.sd_zone_pro import _confirm_strict_pivots

    h, l, c, v = _sawtooth(cycles=25)
    group = 4
    created = _record_zone_creations(high=h, low=l, close=c, volume=v,
                                     pivot_length=2, group=group)
    sides = [s for s, _, _ in created]

    n_low = int(_confirm_strict_pivots(l, 2, 2, is_high=False).notna().sum())
    n_high = int(_confirm_strict_pivots(h, 2, 2, is_high=True).notna().sum())
    assert n_low > 3 * group and n_high > 3 * group, "fixture produced too few pivots"

    assert sides.count("demand") == n_low // group
    assert sides.count("supply") == n_high // group
    # The sliding-window reading gives a different number, so the
    # assertion above actually discriminates between the two readings.
    assert n_low // group != n_low - group + 1


def test_group_one_fires_on_every_pivot():
    """`group=1` makes `total % 1 == 0` true always -- the source's own
    shipped default (L15-16), i.e. no grouping at all. One zone creation
    per confirmed pivot per side."""
    from pandas_ta.trend.sd_zone_pro import _confirm_strict_pivots

    h, l, c, v = _sawtooth(cycles=12)
    created = _record_zone_creations(high=h, low=l, close=c, volume=v,
                                     pivot_length=2, group=1)
    sides = [s for s, _, _ in created]
    n_low = int(_confirm_strict_pivots(l, 2, 2, is_high=False).notna().sum())
    n_high = int(_confirm_strict_pivots(h, 2, 2, is_high=True).notna().sum())
    assert sides.count("demand") == n_low
    assert sides.count("supply") == n_high


def test_batch_sums_the_group_most_recent_pivot_volumes():
    """The loop reads indices 0..group-1 of an unshift-to-front array
    (Pine L117-119), i.e. the `group` MOST RECENT pivots, and sums their
    OWN bars' volumes (`volume[pLowLen]`, L46). With constant volume
    `vol`, a first batch's mass is therefore exactly `group * vol`."""
    h, l, c, v = _sawtooth(cycles=12, vol=1000.0)
    created = _record_zone_creations(high=h, low=l, close=c, volume=v,
                                     pivot_length=2, group=3)
    first_demand = [m for s, m, _ in created if s == "demand"][0]
    assert first_demand == pytest.approx(3 * 1000.0)


def test_zone_creations_are_stamped_with_the_confirmation_bar():
    """Every `_Zone` must be opened at a bar >= (its pivot bar +
    pivot_length). Checked structurally here as a cheap invariant; the
    mutant test below is what actually proves the stamp is the
    confirmation bar and not the pivot bar."""
    from pandas_ta.trend.sd_zone_pro import _confirm_strict_pivots

    h, l, c, v = _ohlcv(n=600)
    created = _record_zone_creations(high=h, low=l, close=c, volume=v)
    conf_low = set(np.flatnonzero(_confirm_strict_pivots(l, 5, 5, is_high=False).notna().to_numpy()))
    conf_high = set(np.flatnonzero(_confirm_strict_pivots(h, 5, 5, is_high=True).notna().to_numpy()))
    assert created
    for side, _, opened_at in created:
        assert opened_at in (conf_low if side == "demand" else conf_high)


# ---------------------------------------------------------------------------
# Faithfulness trap 2 -- the source's shipped defaults are a no-op
# ---------------------------------------------------------------------------

def test_source_defaults_are_reachable_but_are_not_this_ports_defaults():
    """`pivot_length=1, group=1` reproduces the source's shipped
    configuration (L9-10, L15-16) exactly; this port DEVIATES to
    `pivot_length=5, group=3` and says so in its docstring. Both must
    run, and they must not be the same column."""
    h, l, c, v = _ohlcv(n=600)
    src_cfg = sd_zone_pro(h, l, c, v, pivot_length=1, group=1)
    assert list(src_cfg.columns) == ["SDZ_MASS_IMBALANCE_1_1", "SDZ_NEAR_MASS_1_1"]
    assert src_cfg["SDZ_MASS_IMBALANCE_1_1"].notna().sum() > 0

    port_cfg = sd_zone_pro(h, l, c, v)
    a = src_cfg["SDZ_MASS_IMBALANCE_1_1"].to_numpy()
    b = port_cfg[IMB].to_numpy()
    assert not np.array_equal(np.nan_to_num(a, nan=-999), np.nan_to_num(b, nan=-999))


# ---------------------------------------------------------------------------
# Faithfulness trap 3 -- cross-side mass contamination
# ---------------------------------------------------------------------------

def test_cross_side_merge_is_on_by_default_and_can_be_switched_off():
    """The source's `mergeCrossSide` default is TRUE (L21), so a demand
    cluster's volume can land in a SUPPLY zone's `Vols` entry. The port
    keeps that default and gates it, so the correlation check can be run
    with the contamination off. On a fixture where cross-side merges
    actually happen the two columns must differ."""
    h, l, c, v = _ohlcv()
    on = sd_zone_pro(h, l, c, v)
    off = sd_zone_pro(h, l, c, v, merge_cross_side=False)
    a, b = on[IMB].to_numpy(), off[IMB].to_numpy()
    differing = np.nansum(np.abs(np.nan_to_num(a) - np.nan_to_num(b)) > 1e-12)
    assert differing > 0, "fixture never triggers a cross-side merge -- test has no power"


def test_cross_side_merge_adds_mass_to_the_other_sides_zone():
    """Directly instrumented: `_Zone.add_mass` is the ONLY place a
    merge deposits volume into an existing zone, so counting its calls
    with `merge_cross_side` on vs off isolates the cross-side path."""
    h, l, c, v = _ohlcv()

    def _n_merges(flag):
        mod = _module()
        calls = []
        real_add = mod._Zone.add_mass

        def _patched(self, at, delta):
            calls.append((self.side, at, delta))
            return real_add(self, at, delta)

        mod._Zone.add_mass = _patched
        try:
            mod.sd_zone_pro(high=h, low=l, close=c, volume=v, merge_cross_side=flag)
        finally:
            mod._Zone.add_mass = real_add
        return calls

    with_cross = _n_merges(True)
    without = _n_merges(False)
    assert len(without) > 0, "fixture triggers no SAME-side merge either -- no power"
    assert len(with_cross) > len(without), (
        f"cross-side merges add no extra mass events "
        f"({len(with_cross)} vs {len(without)}) -- fixture has no power"
    )


# ---------------------------------------------------------------------------
# Zone geometry / helpers
# ---------------------------------------------------------------------------

def test_zone_distance_is_zero_inside_and_symmetric_outside():
    z = _Zone(0, "demand", top=105.0, bottom=100.0, opened_at=0, mass=1.0)
    assert _zone_distance(100.0, z) == 0.0
    assert _zone_distance(102.5, z) == 0.0
    assert _zone_distance(105.0, z) == 0.0
    assert _zone_distance(98.0, z) == pytest.approx(2.0)
    assert _zone_distance(107.0, z) == pytest.approx(2.0)


def test_zone_mass_timeline_is_append_only():
    z = _Zone(0, "supply", top=10.0, bottom=9.0, opened_at=3, mass=100.0)
    z.add_mass(9, 50.0)
    z.add_mass(20, 25.0)
    assert z.mass_events == [(3, 100.0), (9, 150.0), (20, 175.0)]
    assert z.mass == 175.0


def test_max_boxes_zero_means_unlimited():
    """Pine's own tooltip on `maxBoxCount` says "0 = Unlimited" (L28), so
    0 is a legal value and must not be rejected as non-positive."""
    h, l, c, v = _ohlcv(n=600)
    out = sd_zone_pro(h, l, c, v, max_boxes=0)
    assert out[IMB].notna().sum() > 0


def test_smaller_max_boxes_changes_the_column():
    h, l, c, v = _ohlcv()
    wide = sd_zone_pro(h, l, c, v, max_boxes=15)[IMB].to_numpy()
    tight = sd_zone_pro(h, l, c, v, max_boxes=2)[IMB].to_numpy()
    assert not np.array_equal(np.nan_to_num(wide, nan=-9), np.nan_to_num(tight, nan=-9))


# ---------------------------------------------------------------------------
# Causality
# ---------------------------------------------------------------------------

def test_truncation_matches_prefix_of_full_series():
    """Prefix stability -- necessary for causality, but NOT sufficient on
    its own to catch back-dating (see
    `test_truncation_before_confirmation_catches_backdating_mutant` for
    the test that actually has that power)."""
    h, l, c, v = _ohlcv()
    full = sd_zone_pro(h, l, c, v)
    for k in (200, 400, 777, 1000):
        part = sd_zone_pro(h.iloc[:k], l.iloc[:k], c.iloc[:k], v.iloc[:k])
        pd.testing.assert_frame_equal(part, full.iloc[:k], check_exact=False)


def test_mutation_after_cutoff_does_not_change_earlier_output():
    h, l, c, v = _ohlcv()
    base = sd_zone_pro(h, l, c, v)
    k = 700
    h2, l2, c2, v2 = h.copy(), l.copy(), c.copy(), v.copy()
    for s in (h2, l2, c2):
        s.iloc[k:] = s.iloc[k:] * 3.0
    v2.iloc[k:] = v2.iloc[k:] * 7.0
    mutated = sd_zone_pro(h2, l2, c2, v2)
    pd.testing.assert_frame_equal(mutated.iloc[:k], base.iloc[:k], check_exact=False)


def _load_backdating_mutant():
    """Load a MUTATED copy of the real module in which the single
    zone-state write-site is back-dated to the pivot's own bar.

    The real module stamps every zone-state change (open, close, mass
    merge) with `zone_state_idx`, assigned once at the top of PASS 1's
    bar loop as the CONFIRMATION bar `j`. The mutant rewrites that one
    assignment to `j - pivot_length`, i.e. the bar the pivot actually
    printed on -- exactly the mistranslation the source invites, since
    the source DOES draw its box `left = minBarIdx`, anchored back at the
    pivot (Pine L242-250 / L394-402).

    Source is read from the real module's `__file__` via `importlib` and
    exec'd into an in-memory `types.ModuleType` (no filesystem
    footprint), never hand-reimplemented -- so the mutant is provably the
    real algorithm plus one changed index.
    """
    import importlib
    import types

    # The dotted `import_module` path gets the actual SUBMODULE (which
    # has a real `__file__`); the same name as an attribute of
    # `pandas_ta.trend` resolves to the re-exported FUNCTION.
    real_module = importlib.import_module("pandas_ta.trend.sd_zone_pro")
    with open(real_module.__file__, "r", encoding="utf-8") as fh:
        src = fh.read()

    marker = "zone_state_idx = j"
    assert src.count(marker) == 1, \
        "write-site marker moved or duplicated -- update this mutant loader"
    mutated = src.replace(marker, "zone_state_idx = j - pivot_length", 1)
    assert mutated != src

    mod = types.ModuleType("sd_zone_pro_backdating_mutant")
    exec(compile(mutated, "<sd_zone_pro_backdating_mutant>", "exec"), mod.__dict__)
    return mod.sd_zone_pro


# (cut, pivot_bar) pairs found by an exhaustive scan of every cutoff in
# [60, 400) on the `_ohlcv(n=400, seed=7)` fixture, keeping only cutoffs
# where the REAL port agrees with itself under truncation AND the MUTANT
# disagrees with itself, on BOTH output columns simultaneously. 10 of the
# 340 scanned cutoffs qualify for both columns; the first 5 are used
# here. (Many more qualify for SDZ_MASS_IMBALANCE alone -- the pair
# requirement is the strict one, because SDZ_NEAR_MASS only moves when
# the back-dated zone is the NEAREST one on either side.)
BACKDATE_CASES = [(92, 87), (138, 133), (180, 175), (245, 240), (288, 283)]


@pytest.mark.parametrize("col", DEFAULT_COLS)
@pytest.mark.parametrize("cut,pivot_bar", BACKDATE_CASES)
def test_truncation_before_confirmation_catches_backdating_mutant(col, cut, pivot_bar):
    """Truncate the series to `[:cut]`, so the batch confirming at bar
    `cut` is never reached by the truncated run. Proven two ways on the
    same fixture and cutoff:

    1. The REAL port produces the SAME value at `pivot_bar` in both runs
       -- no divergence, matching the module docstring's CAUSALITY claim.
    2. The MUTANT produces DIFFERENT values at `pivot_bar` between its
       full and truncated runs: in the full run it has already back-dated
       the bar-`cut` zone onto bar `cut - pivot_length`, in the truncated
       run that zone does not exist. A genuine, detected divergence --
       which is what gives this cutoff its power. A cutoff placed after
       the confirmation bar (as in
       `test_truncation_matches_prefix_of_full_series`) would let both
       runs reach the same event and back-date identically, detecting
       nothing at all.
    """
    h, l, c, v = _ohlcv(n=400, seed=7)
    assert pivot_bar == cut - 5

    real_full = sd_zone_pro(h, l, c, v)
    real_trunc = sd_zone_pro(h.iloc[:cut], l.iloc[:cut], c.iloc[:cut], v.iloc[:cut])
    a, b = real_full[col].iloc[pivot_bar], real_trunc[col].iloc[pivot_bar]
    assert (np.isnan(a) and np.isnan(b)) or a == b, \
        f"REAL port is not causal at bar {pivot_bar}: {a} vs {b}"

    mutant = _load_backdating_mutant()
    mut_full = mutant(h, l, c, v)
    mut_trunc = mutant(h.iloc[:cut], l.iloc[:cut], c.iloc[:cut], v.iloc[:cut])
    x, y = mut_full[col].iloc[pivot_bar], mut_trunc[col].iloc[pivot_bar]
    same = (np.isnan(x) and np.isnan(y)) or x == y
    assert not same, \
        f"mutant is a no-op at bar {pivot_bar} for {col} -- test has no power"


def test_backdating_mutant_is_globally_live():
    """Belt-and-braces: the mutant must differ from the real port on the
    FULL series too, so a future refactor that quietly neutered the
    marker (e.g. moved the stamp elsewhere) fails loudly here as well as
    in the per-cutoff test above."""
    h, l, c, v = _ohlcv(n=400, seed=7)
    real = sd_zone_pro(h, l, c, v)
    mut = _load_backdating_mutant()(h, l, c, v)
    for col in DEFAULT_COLS:
        a, b = real[col].to_numpy(), mut[col].to_numpy()
        assert not np.array_equal(np.nan_to_num(a, nan=-9e9), np.nan_to_num(b, nan=-9e9)), \
            f"{col}: mutant equals the real port -- no back-dating signal at all"


# ---------------------------------------------------------------------------
# Argument validation
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("kwargs", [
    {"pivot_length": 0}, {"pivot_length": -3}, {"pivot_length": 2.5},
    {"pivot_length": float("nan")}, {"pivot_length": float("inf")},
    {"pivot_length": True}, {"pivot_length": "abc"},
    {"group": 0}, {"group": -1}, {"group": 1.5}, {"group": "x"},
    {"max_bar_dist": 0}, {"max_bar_dist": -2}, {"max_bar_dist": 3.5},
    {"atr_length": 0}, {"atr_length": -1}, {"vol_length": 0}, {"vol_length": -4},
    {"merge_tol_mult": float("nan")}, {"merge_tol_mult": float("inf")},
    {"merge_tol_mult": -0.5}, {"merge_tol_mult": True}, {"merge_tol_mult": "x"},
    {"box_atr_mult": float("nan")}, {"box_atr_mult": -1.0},
    {"max_boxes": -1}, {"max_boxes": 2.5}, {"max_boxes": float("nan")},
    {"merge_cross_side": "yes"}, {"merge_cross_side": 1},
])
def test_bad_kwargs_raise(kwargs):
    h, l, c, v = _ohlcv(n=300)
    with pytest.raises(ValueError):
        sd_zone_pro(h, l, c, v, **kwargs)


@pytest.mark.parametrize("kwargs", [
    {"merge_tol_mult": 0.0}, {"box_atr_mult": 0.0}, {"max_boxes": 0},
    {"merge_cross_side": False}, {"merge_cross_side": np.bool_(True)},
])
def test_legal_edge_kwargs_do_not_raise(kwargs):
    h, l, c, v = _ohlcv(n=400)
    assert sd_zone_pro(h, l, c, v, **kwargs) is not None


def test_offset_shifts_every_column():
    h, l, c, v = _ohlcv()
    base = sd_zone_pro(h, l, c, v)
    shifted = sd_zone_pro(h, l, c, v, offset=2)
    for col in DEFAULT_COLS:
        pd.testing.assert_series_equal(
            shifted[col].iloc[2:].reset_index(drop=True),
            base[col].iloc[:-2].reset_index(drop=True),
            check_names=False, check_dtype=False,
        )


def test_dataframe_accessor_matches_direct_call():
    h, l, c, v = _ohlcv()
    df = pd.DataFrame({"open": c, "high": h, "low": l, "close": c, "volume": v})
    direct = sd_zone_pro(h, l, c, v)
    via = df.ta.sd_zone_pro()
    pd.testing.assert_frame_equal(direct, via, check_exact=False)


def test_registered_in_category():
    assert "sd_zone_pro" in ta.Category["trend"]
