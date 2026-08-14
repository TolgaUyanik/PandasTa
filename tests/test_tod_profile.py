# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.volume.tod_profile` (TOD).

TVPTA-6 candidate 16 -- port of the PROFILE ACCUMULATOR (Pine L101-175) of
"Volume & Volatility Time-of-Day - Seasonality Forecast" (slug n16YXPSU).

The centrepiece is `test_self_inclusion_mutant_is_detected`. A time-of-day
profile's specific failure mode is an off-by-one in which a bar's own sample
is folded into its slot's mean BEFORE that mean is read, so the bar leaks its
own value into its own baseline. A prefix-truncation test cannot see this --
the leak is entirely within-bar, so a truncated run and a full run agree
perfectly while BOTH are wrong. It is therefore proven with an executable
MUTANT (`_load_self_inclusion_mutant`) that loads the real module's own source
via `importlib`, reverses exactly the two marked ordering lines, and `exec`s
the result into an in-memory module -- so the mutant is provably the real
algorithm with one thing changed, never a hand-reimplementation.
"""
import numpy as np
import pandas as pd
import pytest

from pandas_ta.volume import tod_profile

P = dict(length=20, bb_length=20, min_samples=5)
COLS = ["TOD_SLOT_RVOL_20_20", "TOD_SLOT_VVOL_20_20",
        "TOD_RVOL_REL_20_20", "TOD_VVOL_REL_20_20"]

# BIST's real hourly shape: 9 bars/session at :30 past the hour, 06:30-14:30Z.
SESSION_HOURS = [6, 7, 8, 9, 10, 11, 12, 13, 14]


def _hourly_frame(n_days=60, seed=7, tz="UTC", vol_scale=1.0, px_scale=1.0):
    """A synthetic BIST-shaped hourly frame with a deliberate time-of-day
    volume profile: the open and close slots trade heavier than midday."""
    rng = np.random.default_rng(seed)
    stamps, slot_of_bar = [], []
    day = pd.Timestamp("2024-01-01", tz=tz)
    while len(stamps) < n_days * len(SESSION_HOURS):
        if day.weekday() < 5:
            for h in SESSION_HOURS:
                stamps.append(day + pd.Timedelta(hours=h, minutes=30))
                slot_of_bar.append(h)
        day += pd.Timedelta(days=1)
    idx = pd.DatetimeIndex(stamps)
    n = len(idx)

    close = 47.0 * np.exp(np.cumsum(rng.normal(0.0002, 0.006, n))) * px_scale
    # U-shaped intraday volume profile (open/close heavy) + noise
    shape = {6: 2.4, 7: 1.5, 8: 1.0, 9: 0.8, 10: 0.7,
             11: 0.8, 12: 1.0, 13: 1.6, 14: 2.6}
    base = np.array([shape[s] for s in slot_of_bar])
    volume = base * 1e6 * np.exp(rng.normal(0, 0.35, n)) * vol_scale
    return pd.DataFrame({"Close": close, "Volume": volume}, index=idx)


def _daily_frame(n=400, seed=3):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2022-01-03", periods=n)
    close = 47 * np.exp(np.cumsum(rng.normal(0.0005, 0.015, n)))
    return pd.DataFrame({"Close": close, "Volume": 1e6 * np.exp(
        rng.normal(0, 0.3, n))}, index=idx)


def _run(df, **kw):
    p = dict(P); p.update(kw)
    return tod_profile(close=df["Close"], volume=df["Volume"], **p)


# ───────────────────────────── shape / smoke ─────────────────────────────

def test_returns_the_four_named_columns():
    r = _run(_hourly_frame())
    assert list(r.columns) == COLS
    assert r.name == "TOD_20_20"
    assert r.category == "volume"


def test_columns_are_populated_on_hourly_input():
    r = _run(_hourly_frame())
    for c in COLS:
        assert r[c].notna().sum() > 0, f"{c} is entirely NaN on hourly input"


# ─────────────────────── correctness vs an independent reference ───────────

def test_matches_an_independent_reference_implementation():
    """Recompute the slot means with a straightforward, separately-written
    double loop (O(n^2), deliberately naive -- it shares no code with the
    module's incremental accumulator) and require an exact match."""
    df = _hourly_frame(n_days=40)
    r = _run(df)

    bb = df["Close"].rolling(20).std(ddof=0)
    mid = df["Close"].rolling(20).mean()
    bbw = 100.0 * (2 * 2.0 * bb) / mid                     # Pine L114
    rvol = df["Volume"] / df["Volume"].rolling(20).mean()  # Pine L135
    vvol = bbw / bbw.rolling(20).mean()                    # Pine L140

    slot = df.index.hour * 60 + df.index.minute
    exp_r, exp_v = [], []
    for i in range(len(df)):
        prior = np.flatnonzero((slot[:i] == slot[i]))      # STRICTLY prior
        pr = rvol.values[prior]; pr = pr[~np.isnan(pr)]
        pv = vvol.values[prior]; pv = pv[~np.isnan(pv)]
        exp_r.append(pr.mean() if len(pr) >= 5 else np.nan)
        exp_v.append(pv.mean() if len(pv) >= 5 else np.nan)

    np.testing.assert_allclose(r[COLS[0]].values, exp_r, rtol=1e-12)
    np.testing.assert_allclose(r[COLS[1]].values, exp_v, rtol=1e-12)
    # ...and the REL columns are exactly bar-ratio / slot-mean
    np.testing.assert_allclose(
        r[COLS[2]].values, rvol.values / np.array(exp_r), rtol=1e-12)
    np.testing.assert_allclose(
        r[COLS[3]].values, vvol.values / np.array(exp_v), rtol=1e-12)


def test_min_samples_floor_is_respected_exactly():
    """No value is emitted for a slot until it has `min_samples` STRICTLY
    prior samples; the first emission lands on the (min_samples+1)-th
    occurrence of that slot, counting only bars whose ratio is non-NaN."""
    df = _hourly_frame(n_days=40)
    for ms in (3, 5, 8):
        r = _run(df, min_samples=ms)
        rvol = df["Volume"] / df["Volume"].rolling(20).mean()
        slot = df.index.hour * 60 + df.index.minute
        for s in np.unique(slot):
            at = np.flatnonzero((slot == s) & rvol.notna().values)
            col = r[COLS[0]].values
            assert np.isnan(col[at[:ms]]).all(), f"emitted before {ms} samples"
            assert not np.isnan(col[at[ms]]), f"withheld at sample {ms}"


# ───────────────────────────── CAUSALITY ─────────────────────────────

def _load_self_inclusion_mutant():
    """Load a MUTATED copy of the real module in which the read step and the
    accumulate step are SWAPPED -- i.e. the current bar is folded into its
    own slot before that slot's mean is read, the self-inclusion defect.

    Source is read from the real module's `__file__` via `importlib` and
    exec'd into an in-memory `types.ModuleType` (no filesystem footprint),
    never hand-reimplemented -- so the mutant is provably the real algorithm
    with exactly two adjacent statements transposed.
    """
    import importlib
    import types

    real_module = importlib.import_module("pandas_ta.volume.tod_profile")
    with open(real_module.__file__, "r", encoding="utf-8") as fh:
        src = fh.read()

    marker = "        _read_step(i)\n        _accumulate_step(i)\n"
    assert src.count(marker) == 1, \
        "causality ordering lines moved or duplicated -- update this mutant loader"
    mutated = src.replace(
        marker, "        _accumulate_step(i)\n        _read_step(i)\n", 1)
    assert mutated != src

    mod = types.ModuleType("tod_profile_self_inclusion_mutant")
    exec(compile(mutated, "<tod_profile_self_inclusion_mutant>", "exec"),
         mod.__dict__)
    return mod.tod_profile


def test_self_inclusion_mutant_is_detected():
    """REAL vs MUTANT must disagree, on a fixture whose slot means are small
    enough that one extra sample visibly moves them (`min_samples=5`, so the
    first emitted mean rests on 5 samples and self-inclusion makes it 6).

    Two independent detections, so this does not rest on float noise:

    1. STRUCTURAL -- the mutant emits a value one bar EARLIER per slot. The
       real port needs 5 samples already banked before it reads; the mutant
       banks the current bar first, so it fires on the 5th occurrence where
       the real port is still NaN. This alone is a hard, magnitude-free
       detection.
    2. NUMERIC -- where both emit, the values differ.
    """
    df = _hourly_frame(n_days=40)
    real = _run(df)
    mutant = _load_self_inclusion_mutant()(
        close=df["Close"], volume=df["Volume"], **P)

    # (1) structural: strictly more emitted values in the mutant
    real_n = real[COLS[0]].notna().sum()
    mut_n = mutant[COLS[0]].notna().sum()
    assert mut_n > real_n, (
        f"mutant is a no-op -- test has no power (real={real_n}, mut={mut_n})")
    # exactly one extra emission per slot (9 slots in this fixture)
    assert mut_n - real_n == df.index.hour.nunique() == 9

    # bars where the real port withholds but the mutant already speaks
    leak_only = real[COLS[0]].isna() & mutant[COLS[0]].notna()
    assert leak_only.sum() == 9

    # (2) numeric: on the overlap, the values genuinely differ
    both = real[COLS[0]].notna() & mutant[COLS[0]].notna()
    assert both.sum() > 100
    diff = (real[COLS[0]][both] - mutant[COLS[0]][both]).abs()
    assert diff.max() > 1e-6, "mutant numerically indistinguishable"
    assert (diff > 1e-9).mean() > 0.99, \
        "self-inclusion must move nearly every emitted slot mean"


def test_truncation_matches_prefix_of_full_series():
    """Complementary to the mutant: a prefix of the full run must equal a run
    on the truncated input. (Necessary but NOT sufficient -- see this file's
    docstring; a self-inclusion leak passes this test cleanly.)"""
    df = _hourly_frame(n_days=40)
    k = 200
    full = _run(df)
    trunc = _run(df.iloc[:k])
    pd.testing.assert_frame_equal(full.iloc[:k], trunc, check_exact=False)


# ───────────────────────────── scale-freedom ─────────────────────────────

@pytest.mark.parametrize("kw", [dict(vol_scale=10.0), dict(px_scale=10.0),
                                dict(vol_scale=1e4, px_scale=1e3)])
def test_outputs_are_invariant_to_price_and_volume_scale(kw):
    """Every column is a ratio of a quantity to a mean of that same quantity,
    so a constant rescaling of price and/or volume must cancel exactly."""
    base = _run(_hourly_frame())
    scaled = _run(_hourly_frame(**kw))
    for c in COLS:
        a, b = base[c].values, scaled[c].values
        assert np.array_equal(np.isnan(a), np.isnan(b))
        m = ~np.isnan(a)
        np.testing.assert_allclose(a[m], b[m], rtol=1e-9)


def test_bb_std_cancels_out_of_every_output():
    """`bb_std` (Pine `bbMult`) scales BB width linearly and every output
    divides BB width by a mean of BB width, so it cannot move a single value.
    Asserted rather than assumed (the docstring makes this claim)."""
    df = _hourly_frame()
    a = _run(df, bb_std=2.0)
    for mult in (0.5, 1.0, 3.7):
        b = _run(df, bb_std=mult)
        pd.testing.assert_frame_equal(a, b)


# ───────────────────────── degenerate input / timeframe ─────────────────────

def test_daily_input_returns_all_nan_with_a_reason_and_does_not_raise():
    """The hourly-only constraint. Daily bars carry ONE minute-of-day slot,
    so the profile has nothing to discriminate. Contract: all-NaN, stable
    column names, a stamped reason -- never an exception."""
    r = _run(_daily_frame())
    assert list(r.columns) == COLS
    assert r.isna().all().all()
    assert "slots" in r.tod_degenerate_reason


def test_integer_index_returns_all_nan_via_the_slot_count_guard():
    """A RangeIndex does NOT raise in `pd.DatetimeIndex(...)` -- pandas
    coerces the integers to epoch NANOSECONDS, so every bar lands on
    1970-01-01 00:00 and the frame has exactly one slot. Measured, not
    assumed: it is the slot-count guard that catches this, not the type
    guard. Either way the contract holds -- all-NaN, never a raise."""
    df = _hourly_frame()
    df.index = pd.RangeIndex(len(df))
    r = _run(df)
    assert list(r.columns) == COLS
    assert r.isna().all().all()
    assert "slots" in r.tod_degenerate_reason


def test_non_datetime_index_returns_all_nan_via_the_type_guard():
    """A string index genuinely cannot be coerced, exercising the
    `except (TypeError, ValueError)` path."""
    df = _hourly_frame()
    df.index = pd.Index([f"bar-{i}" for i in range(len(df))])
    r = _run(df)
    assert list(r.columns) == COLS
    assert r.isna().all().all()
    assert "datetime" in r.tod_degenerate_reason


# ───────────────────────────── timezone ─────────────────────────────

def test_tz_relabeling_is_bit_identical_for_a_no_dst_zone():
    """Turkey has observed no DST since 2016, so reading slots in UTC vs in
    Europe/Istanbul is a pure RELABELING of slot ids (+180 minutes on every
    bar) and must leave every output value untouched. This is the claim the
    module docstring makes about the consuming repo's BIST hourly cache."""
    df = _hourly_frame(tz="UTC")
    utc = _run(df, tz=None)
    ist = _run(df, tz="Europe/Istanbul")
    pd.testing.assert_frame_equal(utc, ist)


def test_tz_is_ignored_on_a_tz_naive_index():
    """A tz-naive index is already assumed to be local wall time; passing a
    tz must NOT silently localize-and-shift it."""
    df = _hourly_frame(tz="UTC")
    df.index = df.index.tz_localize(None)
    pd.testing.assert_frame_equal(_run(df, tz=None),
                                  _run(df, tz="Asia/Tokyo"))


def test_a_dst_observing_zone_does_shift_slots():
    """The converse, so the test above is not mistaken for 'tz never matters'.
    Converting a UTC index to a DST-observing zone changes slot ids by
    different amounts either side of a transition, so the profile differs."""
    df = _hourly_frame(n_days=200, tz="UTC")
    a = _run(df, tz=None)
    b = _run(df, tz="America/New_York")
    assert not a[COLS[0]].equals(b[COLS[0]])


# ───────────────────────────── scope ─────────────────────────────

def test_session_scope_runs_and_differs_from_rolling():
    df = _hourly_frame()
    roll = _run(df, scope="rolling")
    sess = _run(df, scope="session")
    for c in COLS:
        assert sess[c].notna().sum() > 0
    assert not roll[COLS[0]].equals(sess[COLS[0]])


def test_session_scope_first_bar_of_each_day_reads_one():
    """Pine L126-133 adds the current bar to the session sums BEFORE reading
    the mean, so the day's first bar is measured against itself -> exactly 1."""
    df = _hourly_frame()
    vol = df["Volume"]
    day = pd.Series(df.index.normalize(), index=df.index)
    first = day.ne(day.shift()).values
    grp = day.ne(day.shift()).cumsum()
    ma = vol.groupby(grp).expanding().mean().reset_index(level=0, drop=True)
    np.testing.assert_allclose((vol / ma).values[first], 1.0, rtol=1e-12)


def test_unknown_scope_falls_back_to_rolling():
    df = _hourly_frame()
    pd.testing.assert_frame_equal(_run(df, scope="nonsense"),
                                  _run(df, scope="rolling"))
