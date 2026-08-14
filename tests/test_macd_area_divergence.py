# -*- coding: utf-8 -*-
"""Tests for `macd_area_divergence` (MADIV), TVPTA-6 candidate 15.

Ported from the TradingView Pine v6 source "趋势结构系统均线共振版"
(iOd2A4mw.pine, 172 lines).

Fixtures use SHORT MA/MACD lengths (3/5/8 and 3/6/3) rather than the
20/60/120 + 12/26/9 defaults: the alignment gate flips only a handful of
times per 400 bars at the defaults, so a default-parameter fixture that
reliably fires both a TOP and a BOTTOM divergence would have to be
thousands of bars long. The DEFAULT parameters are still exercised
throughout: every test taking `_realistic()` runs at 20/60/120 + 12/26/9
on a 2,500-bar walk. Reachability at the defaults on real data is
measured separately -- see
`backtest_results/tvpta6/macd_area_divergence_overlap_20260814.md`.

The back-dating mutant (`_load_backdating_mutant`) deliberately loads a
MUTATED copy of the real module via `importlib` + `exec` into an
in-memory module -- never a hand-reimplementation -- so it is provably
the real algorithm plus one changed index.
"""
import numpy as np
import pandas as pd
import pytest

from pandas_ta.momentum import macd_area_divergence

# Short-parameter set used by the structural fixtures.
P = dict(fast_len=3, mid_len=5, slow_len=8, macd_fast=3, macd_slow=6, macd_signal=3)
TOP = "MADIV_TOP_3_5_8"
BOT = "MADIV_BOT_3_5_8"
BULL_AREA = "MADIV_BULL_AREA_R_3_5_8"
BEAR_AREA = "MADIV_BEAR_AREA_R_3_5_8"
BULL_PX = "MADIV_BULL_PX_R_3_5_8"
BEAR_PX = "MADIV_BEAR_PX_R_3_5_8"

DEFAULT_COLS = [
    "MADIV_TOP_20_60_120", "MADIV_BOT_20_60_120",
    "MADIV_BULL_AREA_R_20_60_120", "MADIV_BEAR_AREA_R_20_60_120",
    "MADIV_BULL_PX_R_20_60_120", "MADIV_BEAR_PX_R_20_60_120",
]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _from_segments(segments, start=100.0, wick=0.002):
    """Build (high, low, close) from a list of (n_bars, per-bar drift)."""
    px = [start]
    for n, d in segments:
        for _ in range(n):
            px.append(px[-1] * (1 + d))
    close = pd.Series(px, dtype=float)
    return close * (1 + wick), close * (1 - wick), close


def _top_scenario():
    """A STRUCTURAL top divergence, hand-shaped rather than sampled.

    Bull segment 1 is a short violent impulse (large histogram area) to a
    high; a shallow pullback flips the gate to bear; bull segment 2 is a
    long slow grind that takes price to a HIGHER high on a SMALLER
    accumulated histogram area, then a flat plateau, then a drop that
    flips the gate back to bear and confirms the divergence.

    The 13-bar plateau exists to separate the segment's price EXTREME
    from the CONFIRMATION bar, which is what gives the back-dating mutant
    test its resolution. Its drift is SLIGHTLY NEGATIVE (-0.0003), not
    flat: on a perfectly flat plateau the source's own L67 (`if high ==
    bullHigh`) re-latches `bullHighBar` on every tying bar, so the
    extreme walks forward to the last plateau bar and the gap collapses
    to 1. That is faithful Pine behaviour, and it is why this fixture
    decays instead of flatlining.

    Returns (high, low, close); n=76, the confirmation bar is 62 and the
    segment extreme is bar 50 (a 12-bar gap) -- both asserted, not
    assumed, in `test_top_scenario_fires_where_expected` and in the
    mutant test's own parametrisation.
    """
    return _from_segments([(10, 0.06), (8, -0.015), (32, 0.004), (13, -0.0003), (12, -0.03)])


def _bot_scenario():
    """A BOTTOM divergence found by an exhaustive seeded random-walk
    search: seed 2121 of 0..2999 maximised the extreme->confirmation gap
    (13 bars) among seeds producing exactly one BOT event. Hand-shaping a
    bottom the way `_top_scenario` shapes a top does not work -- under
    geometric drift the mirrored construction produced no qualifying pair
    anywhere in a 5-factor grid search -- so a sampled fixture is used
    instead. n=160, confirmation bar 139, segment extreme bar 126."""
    rng = np.random.default_rng(2121)
    close = pd.Series(100 * np.exp(np.cumsum(rng.normal(0, 0.02, 160))))
    return close * 1.003, close * 0.997, close


def _realistic(n=2500, seed=11):
    """A long random walk. n defaults to 2500 because the DEFAULT
    20/60/120 gate flips only a handful of times per thousand bars: at
    n=600 not one of the four ratio columns is ever populated, so a
    shorter fixture would make several assertions below vacuous."""
    rng = np.random.default_rng(seed)
    close = pd.Series(100 * np.exp(np.cumsum(rng.normal(0.0004, 0.015, n))))
    high = close * (1 + np.abs(rng.normal(0, 0.005, n)))
    low = close * (1 - np.abs(rng.normal(0, 0.005, n)))
    return high, low, close


# ---------------------------------------------------------------------------
# Shape / contract
# ---------------------------------------------------------------------------

def test_default_column_names_and_shape():
    h, l, c = _realistic()
    out = macd_area_divergence(h, l, c)
    assert list(out.columns) == DEFAULT_COLS
    assert len(out) == len(c)
    assert out.name == "MADIV_20_60_120"
    assert out.category == "momentum"
    assert out.index.equals(c.index)


def test_props_track_the_ma_lengths_not_the_macd_lengths():
    h, l, c = _realistic()
    out = macd_area_divergence(h, l, c, fast_len=10, mid_len=30, slow_len=90)
    assert list(out.columns) == [
        "MADIV_TOP_10_30_90", "MADIV_BOT_10_30_90",
        "MADIV_BULL_AREA_R_10_30_90", "MADIV_BEAR_AREA_R_10_30_90",
        "MADIV_BULL_PX_R_10_30_90", "MADIV_BEAR_PX_R_10_30_90",
    ]


def test_flags_are_zero_one_only():
    h, l, c = _realistic()
    out = macd_area_divergence(h, l, c)
    for col in (DEFAULT_COLS[0], DEFAULT_COLS[1]):
        assert out[col].notna().all(), "flags are dense, never NaN"
        assert set(np.unique(out[col].to_numpy())) <= {0, 1}


def test_too_short_returns_none():
    """`verify_series(close, min_len)` refuses a frame shorter than the
    longest length in play; min_len is max(20,60,120,12,26,9) == 120."""
    h, l, c = _realistic(n=119)
    assert macd_area_divergence(h, l, c) is None
    h, l, c = _realistic(n=120)
    assert macd_area_divergence(h, l, c) is not None


def test_min_len_tracks_the_macd_lengths_too():
    """A frame long enough for the MAs but not for the MACD slow EMA is
    still refused -- min_len is the max over BOTH families, not just the
    MA gate."""
    h, l, c = _realistic(n=60)
    assert macd_area_divergence(h, l, c, fast_len=3, mid_len=5, slow_len=8,
                                macd_fast=3, macd_slow=90, macd_signal=3) is None


# ---------------------------------------------------------------------------
# Source semantics
# ---------------------------------------------------------------------------

def test_top_scenario_fires_where_expected():
    """Both legs of the source's L111 condition hold at the confirmation
    bar: price made a higher segment high (PX ratio > 1) AND the segment
    area shrank below `shrink` (AREA ratio < 0.95)."""
    h, l, c = _top_scenario()
    out = macd_area_divergence(h, l, c, **P)
    fired = np.flatnonzero(out[TOP].to_numpy())
    assert list(fired) == [62]
    assert out[BULL_PX].iloc[62] > 1.0
    assert out[BULL_AREA].iloc[62] < 0.95
    # The segment's price extreme is 12 bars earlier -- the gap the
    # back-dating mutant exploits.
    assert int(h.iloc[18:62].idxmax()) == 50


def test_bot_scenario_fires_with_both_legs():
    h, l, c = _bot_scenario()
    out = macd_area_divergence(h, l, c, **P)
    fired = np.flatnonzero(out[BOT].to_numpy())
    assert list(fired) == [139]
    assert out[BEAR_PX].iloc[139] < 1.0, "price made a LOWER segment low"
    assert out[BEAR_AREA].iloc[139] < 0.95, "bear momentum area shrank"


def test_shrink_gate_is_live():
    """Raising `shrink` above 1 removes the momentum leg entirely, so the
    flag degenerates to the price leg alone and fires strictly more
    often; dropping it to a very small value fires strictly less."""
    h, l, c = _bot_scenario()
    base = macd_area_divergence(h, l, c, **P)[BOT].sum()
    loose = macd_area_divergence(h, l, c, shrink=10.0, **P)[BOT].sum()
    tight = macd_area_divergence(h, l, c, shrink=1e-9, **P)[BOT].sum()
    assert loose > base > tight
    assert tight == 0


def test_prev_state_updates_even_when_no_divergence_fires():
    """Source L116-117 / L136-137 update `prevBull*`/`prevBear*` on EVERY
    structure point, fired or not. Consequence: the ratio columns are
    populated at structure points where the flag is 0 -- if the update
    were conditional, ratios would only ever appear on flag bars."""
    h, l, c = _realistic()
    out = macd_area_divergence(h, l, c)
    ratio_bars = out[DEFAULT_COLS[2]].notna()
    flag_bars = out[DEFAULT_COLS[0]] == 1
    assert (ratio_bars & ~flag_bars).sum() > 0


def test_ratio_columns_are_forward_filled_never_back_filled():
    h, l, c = _realistic()
    out = macd_area_divergence(h, l, c)
    for col in DEFAULT_COLS[2:]:
        s = out[col]
        first = s.first_valid_index()
        assert first is not None, f"{col} never populated on this fixture"
        # No value before the first structure point (a back-fill would
        # put one there), and no NaN after it (a forward fill leaves none).
        assert s.iloc[:first].isna().all()
        assert s.iloc[first:].notna().all()


def test_zero_previous_area_leaves_ratio_nan_not_inf():
    """A bull segment whose MACD histogram was never positive has an area
    of exactly 0; the NEXT bull structure point then divides by it. The
    ratio must be UNDEFINED (NaN), never inf.

    The two ratio families are written at the SAME structure bars, so the
    branch is directly observable as a bar where the PRICE ratio is
    populated but the AREA ratio is not. Seed 15 (found by scanning seeds
    0..3999) is such a case: the price ratio first appears at bar 22, the
    area ratio only at bar 29. This branch is not a synthetic curiosity
    -- on 89 BIST_100 daily frames / 405,312 bars at the defaults,
    MADIV_BULL_PX_R is populated on 358,423 bars against
    MADIV_BULL_AREA_R's 356,950, a 1,473-bar gap that is exactly this
    path."""
    rng = np.random.default_rng(15)
    c = pd.Series(100 * np.exp(np.cumsum(rng.normal(0, 0.02, 200))))
    out = macd_area_divergence(c * 1.003, c * 0.997, c, **P)
    assert out[BULL_PX].first_valid_index() == 22
    assert out[BULL_AREA].first_valid_index() == 29
    assert np.isnan(out[BULL_AREA].iloc[22]), "divide-by-zero must give NaN, not inf"
    assert not np.isinf(out.to_numpy(dtype=float)).any()
    # The flag is unaffected: `accum < 0 * shrink` is False for any
    # non-negative accum, so a zero previous area can never fire one.
    assert out[TOP].iloc[22] == 0


def test_no_event_before_the_ma_warmup_completes():
    """The gate mixes EMA and SMA at `slow_len`; both are NaN until index
    `slow_len - 1`, every comparison against NaN is False, so `trend`
    cannot leave 0 and no event can fire."""
    h, l, c = _realistic()
    out = macd_area_divergence(h, l, c)
    assert out[DEFAULT_COLS[0]].iloc[:119].sum() == 0
    assert out[DEFAULT_COLS[1]].iloc[:119].sum() == 0
    for col in DEFAULT_COLS[2:]:
        assert out[col].iloc[:119].isna().all()


# ---------------------------------------------------------------------------
# SCALE-FREE
# ---------------------------------------------------------------------------
# MACD is PRICE-SCALED, so a raw accumulated histogram area would not be
# shippable. Only ratios (and the flags) are shipped, and these two tests
# are the proof.

@pytest.mark.parametrize("factor", [8.0, 64.0, 0.125])
def test_scale_invariance_exact_power_of_two(factor):
    """Multiplying every input series by a POWER OF TWO is an exponent
    shift with no rounding, so the invariance is bit-exact -- both flags
    identical and both ratio families identical to the last bit."""
    h, l, c = _realistic()
    base = macd_area_divergence(h, l, c)
    scaled = macd_area_divergence(h * factor, l * factor, c * factor)
    for col in DEFAULT_COLS[:2]:
        assert (base[col].to_numpy() == scaled[col].to_numpy()).all()
    for col in DEFAULT_COLS[2:]:
        a, b = base[col].to_numpy(), scaled[col].to_numpy()
        assert (np.isnan(a) == np.isnan(b)).all()
        m = ~np.isnan(a)
        assert (a[m] == b[m]).all(), f"{col} not bit-identical under x{factor}"


@pytest.mark.parametrize("factor", [10.0, 0.1, 3.7])
def test_scale_invariance_arbitrary_factor(factor):
    """The same invariance at an arbitrary (non-power-of-two) factor,
    where binary rounding makes bit-equality unavailable: flags must
    still be EXACTLY equal, ratios equal to floating tolerance."""
    h, l, c = _realistic()
    base = macd_area_divergence(h, l, c)
    scaled = macd_area_divergence(h * factor, l * factor, c * factor)
    for col in DEFAULT_COLS[:2]:
        assert (base[col].to_numpy() == scaled[col].to_numpy()).all()
    for col in DEFAULT_COLS[2:]:
        pd.testing.assert_series_equal(base[col], scaled[col], rtol=1e-9, atol=0)


def test_scale_invariance_holds_on_the_firing_fixtures():
    """The invariance must hold where the interesting branches actually
    execute, not only on a fixture whose flags are mostly zero."""
    for builder, col in ((_top_scenario, TOP), (_bot_scenario, BOT)):
        h, l, c = builder()
        base = macd_area_divergence(h, l, c, **P)
        assert base[col].sum() > 0, "fixture stopped firing -- test has no power"
        scaled = macd_area_divergence(h * 8, l * 8, c * 8, **P)
        # x8 is an exponent shift, so demand BIT-equality here rather than a
        # tolerance. Fletcher NIT (round 1): the power-of-two test above runs
        # on `_realistic()`, where MADIV_BOT is identically zero -- so its
        # bit-identity assertion on the BOT column is vacuous, and "bit-
        # identical on all six columns" had never been asserted with a live
        # BOT flag until this line.
        pd.testing.assert_frame_equal(base, scaled, check_exact=True)


# ---------------------------------------------------------------------------
# CAUSALITY
# ---------------------------------------------------------------------------

def test_truncation_matches_prefix_of_full_series():
    """Prefix stability: necessary for causality, but NOT sufficient on
    its own to catch back-dating -- see
    `test_truncation_before_confirmation_catches_backdating_mutant`,
    which is the test that actually has that power."""
    h, l, c = _realistic()
    full = macd_area_divergence(h, l, c)
    for k in (600, 1200, 1777, 2300):
        part = macd_area_divergence(h.iloc[:k], l.iloc[:k], c.iloc[:k])
        pd.testing.assert_frame_equal(part, full.iloc[:k], check_exact=False)


def test_mutation_after_cutoff_does_not_change_earlier_output():
    h, l, c = _realistic()
    base = macd_area_divergence(h, l, c)
    k = 1600
    h2, l2, c2 = h.copy(), l.copy(), c.copy()
    for s in (h2, l2, c2):
        s.iloc[k:] = s.iloc[k:] * 3.0
    mutated = macd_area_divergence(h2, l2, c2)
    pd.testing.assert_frame_equal(mutated.iloc[:k], base.iloc[:k], check_exact=False)


def _load_backdating_mutant():
    """Load a MUTATED copy of the real module in which the two causality
    write-sites are back-dated to the segment's own extreme bar.

    The real module computes `top_write_idx = j` / `bot_write_idx = j`
    (the flip/confirmation bar) and writes the flag and both ratios
    there. The mutant rewrites those two assignments to
    `= bull_high_bar` / `= bear_low_bar` -- the source's own chart-LABEL
    anchor (`label.new(bullHighBar, ...)`, Pine L120 / L140), i.e.
    exactly the mistranslation the source invites, since the source DOES
    draw its marker back at the segment's extreme bar.

    Source is read from the real module's `__file__` via `importlib` and
    exec'd into an in-memory `types.ModuleType` (no filesystem
    footprint), never hand-reimplemented -- so the mutant is provably the
    real algorithm plus one changed index per side.
    """
    import importlib
    import types

    # The dotted `import_module` path gets the actual SUBMODULE (which
    # has a real `__file__`); the same name as an attribute of
    # `pandas_ta.momentum` resolves to the re-exported FUNCTION.
    real_module = importlib.import_module("pandas_ta.momentum.macd_area_divergence")
    with open(real_module.__file__, "r", encoding="utf-8") as fh:
        src = fh.read()

    m_top, m_bot = "top_write_idx = j", "bot_write_idx = j"
    assert src.count(m_top) == 1 and src.count(m_bot) == 1, \
        "write-site markers moved or duplicated -- update this mutant loader"
    mutated = src.replace(m_top, "top_write_idx = bull_high_bar", 1)
    mutated = mutated.replace(m_bot, "bot_write_idx = bear_low_bar", 1)
    assert mutated != src

    mod = types.ModuleType("macd_area_divergence_backdating_mutant")
    exec(compile(mutated, "<macd_area_divergence_backdating_mutant>", "exec"), mod.__dict__)
    return mod.macd_area_divergence


@pytest.mark.parametrize("builder,col,confirm,extreme", [
    (_top_scenario, TOP, 62, 50),
    (_bot_scenario, BOT, 139, 126),
])
def test_truncation_before_confirmation_catches_backdating_mutant(builder, col, confirm, extreme):
    """Truncate BEFORE the confirmation bar, so only the FULL run can
    ever reach the flip and write a back-dated flag at the segment's
    extreme bar. Proven two ways on the same fixture and cutoff:

    1. The REAL port writes 0 at `extreme` in BOTH runs -- no divergence
       between them, matching the module docstring's CAUSALITY claim.
    2. The MUTANT writes 1 at `extreme` in its FULL run (proving it is
       live, not a no-op) and 0 in its TRUNCATED run -- a genuine,
       detected divergence, which is what gives this cutoff its power.
       A cutoff placed AFTER the confirmation bar (as in
       `test_truncation_matches_prefix_of_full_series`) would let both
       runs reach the same event and back-date identically, detecting
       nothing at all.

    Parametrized over BOTH write-sites, since the mutant patches the top
    and bottom sides alike and asserting on only one would leave the
    other patched-but-unexercised.
    """
    h, l, c = builder()
    real = macd_area_divergence(h, l, c, **P)
    assert list(np.flatnonzero(real[col].to_numpy())) == [confirm]

    cut = confirm - 1                       # >= the fixtures' min_len of 8
    assert extreme < cut < confirm

    real_full = real
    real_trunc = macd_area_divergence(h.iloc[:cut], l.iloc[:cut], c.iloc[:cut], **P)
    assert real_full[col].iloc[extreme] == 0
    assert real_trunc[col].iloc[extreme] == 0

    mutant = _load_backdating_mutant()
    mut_full = mutant(h, l, c, **P)
    mut_trunc = mutant(h.iloc[:cut], l.iloc[:cut], c.iloc[:cut], **P)
    assert mut_full[col].iloc[extreme] == 1, "mutant is a no-op -- test has no power"
    assert mut_trunc[col].iloc[extreme] == 0
    assert mut_full[col].iloc[extreme] != mut_trunc[col].iloc[extreme]


def test_backdating_mutant_also_moves_the_ratio_columns():
    """The mutant patches the shared `*_write_idx` variable, so the two
    ratio columns move with the flag. Asserted so a future refactor that
    gave the ratios their own (still causal, or no longer causal) index
    cannot pass unnoticed."""
    h, l, c = _top_scenario()
    real = macd_area_divergence(h, l, c, **P)
    mutant = _load_backdating_mutant()
    mut = mutant(h, l, c, **P)
    # Real: nothing at the extreme bar (the ffill has not reached it either,
    # since this is the first bull structure point on this fixture).
    assert np.isnan(real[BULL_AREA].iloc[50])
    # Mutant: the ratio is written 12 bars early.
    assert not np.isnan(mut[BULL_AREA].iloc[50])


# ---------------------------------------------------------------------------
# Argument validation
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("kwargs", [
    {"fast_len": 0}, {"fast_len": -3}, {"fast_len": 3.5}, {"fast_len": float("nan")},
    {"fast_len": float("inf")}, {"fast_len": True}, {"fast_len": "abc"},
    {"mid_len": 0}, {"mid_len": -1}, {"mid_len": 2.5},
    {"slow_len": 0}, {"slow_len": -5}, {"slow_len": 1.5},
    {"macd_fast": 0}, {"macd_fast": 2.5}, {"macd_slow": 0}, {"macd_signal": 0},
    {"shrink": 0}, {"shrink": -0.5}, {"shrink": float("nan")},
    {"shrink": float("inf")}, {"shrink": True}, {"shrink": "abc"},
])
def test_bad_kwargs_raise(kwargs):
    h, l, c = _realistic(n=200)
    with pytest.raises(ValueError):
        macd_area_divergence(h, l, c, **kwargs)


def test_offset_shifts_every_column():
    h, l, c = _realistic()
    base = macd_area_divergence(h, l, c)
    shifted = macd_area_divergence(h, l, c, offset=2)
    for col in DEFAULT_COLS:
        pd.testing.assert_series_equal(
            shifted[col].iloc[2:].reset_index(drop=True),
            base[col].iloc[:-2].reset_index(drop=True),
            check_names=False, check_dtype=False,
        )


def test_dataframe_accessor_matches_direct_call():
    h, l, c = _realistic()
    df = pd.DataFrame({"open": c, "high": h, "low": l, "close": c, "volume": 1.0})
    direct = macd_area_divergence(h, l, c)
    via = df.ta.macd_area_divergence()
    pd.testing.assert_frame_equal(direct, via, check_exact=False)


def test_registered_in_category():
    import pandas_ta as ta
    assert "macd_area_divergence" in ta.Category["momentum"]
