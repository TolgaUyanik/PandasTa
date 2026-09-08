# -*- coding: utf-8 -*-
"""PINEBI-1d — `up_and_down_volume` and `volume_delta`.

Ported from TradingView's `TradingView/ta`: `requestUpAndDownVolume()`
(`docs/pine/RA2vGpkA-ta.pine:439-442`), `requestVolumeDelta()` (`:474-489`) and
the `upAndDownVolumeCalc()` helper both wrap (`:381-404`).
**© TradingView, MPL-2.0.**

Pinned here, in order of how much it would hurt to lose:

1. **Neither function fetches data.** Pine calls `request.security()`; these
   take the lower-timeframe frame as an argument and RAISE when it is absent.
   The task's premise is that the data source is the blocker, not the code —
   so the code must not pretend the blocker away. Both the missing-frame and
   missing-anchor paths are pinned.
2. **The `var bool isBuyVolume` carry** (`:385`, `:393-397`). When a bar is
   flat on BOTH tests — `close == open` AND `close == close[1]` — Pine keeps
   the PREVIOUS bar's direction rather than defaulting either way. A port that
   drops the carry silently reclassifies every doji, and on tick-rounded BIST
   data those are common.
3. **`VD_HIGH >= VD_OPEN >= VD_LOW` is construction, not discovery.** Pine
   seeds `hiVol`/`loVol` at 0.0 and resets them per bar (`:387-392`,
   `:401-402`), so they are excursions FROM the open. A port that treated them
   as the running max/min of the delta would produce different — and more
   plausible-looking — numbers, which is exactly the kind of divergence this
   repo keeps finding late.
4. **The identity `UDV_POS - UDV_NEG == total volume`**, which fails the
   moment a bar's volume goes into neither bucket.
5. **Only the `_PCT` columns are features.** The rest scale with liquidity.

NOT claimed: these are not exercised on real intraday data anywhere, because
none exists in the cache — see `docs/LowerTimeframeData.md`. Every number here
is from a synthetic 1h-from-5m fixture.
"""
import numpy as np
import pytest
from pandas import DataFrame, Series, date_range

import pandas_ta as ta

BARS_PER_HOUR = 12
HOURS = 48


def lower_frame(hours=HOURS, seed=3):
    """A synthetic 1h-from-5m frame: 12 five-minute bars per hour."""
    n = BARS_PER_HOUR * hours
    rng = np.random.default_rng(seed)
    close = 100 + np.cumsum(rng.normal(0, 0.15, n))
    idx = date_range("2024-03-01 09:00", periods=n, freq="5min")
    return DataFrame({
        "open": close - rng.normal(0, 0.05, n),
        "high": close + abs(rng.normal(0, 0.1, n)),
        "low": close - abs(rng.normal(0, 0.1, n)),
        "close": close,
        "volume": rng.integers(1_000, 9_000, n).astype(float),
    }, index=idx)


# ------------------------------------------------------- 1. it does not fetch

@pytest.mark.parametrize("fn", [ta.up_and_down_volume, ta.volume_delta])
def test_it_raises_without_a_lower_timeframe_frame(fn):
    with pytest.raises(ValueError, match="REQUIRED"):
        fn()


@pytest.mark.parametrize("fn", [ta.up_and_down_volume, ta.volume_delta])
def test_it_raises_without_an_anchor_rather_than_guessing_a_period(fn):
    with pytest.raises(ValueError, match="anchor"):
        fn(lower_frame())


@pytest.mark.parametrize("fn", [ta.up_and_down_volume, ta.volume_delta])
def test_it_raises_on_an_unsorted_frame(fn):
    frame = lower_frame().iloc[::-1]
    with pytest.raises(ValueError, match="sorted"):
        fn(frame, anchor="1h")


@pytest.mark.parametrize("fn", [ta.up_and_down_volume, ta.volume_delta])
def test_it_names_the_columns_it_is_missing(fn):
    frame = lower_frame().drop(columns=["volume"])
    with pytest.raises(ValueError, match="volume"):
        fn(frame, anchor="1h")


def test_a_string_anchor_needs_a_datetime_index():
    frame = lower_frame().reset_index(drop=True)
    with pytest.raises(ValueError, match="DatetimeIndex"):
        ta.up_and_down_volume(frame, anchor="1h")


def test_a_series_anchor_must_share_the_index():
    frame = lower_frame()
    with pytest.raises(ValueError, match="index"):
        ta.up_and_down_volume(frame, anchor=Series([True] * 5))


# ------------------------------------------------------------ 2. the carry

def test_a_doubly_flat_bar_carries_the_previous_direction():
    """Pine's `var bool isBuyVolume`, the detail a port silently loses."""
    from pandas_ta.volume.up_and_down_volume import _classify_intrabar

    idx = date_range("2024-03-01 09:00", periods=5, freq="5min")
    # bar 1 is decisively DOWN; bars 2 and 3 are flat on both tests
    frame = DataFrame({
        "open": [10.0, 11.0, 10.0, 10.0, 9.0],
        "close": [10.0, 10.0, 10.0, 10.0, 10.0],
    }, index=idx)
    direction = _classify_intrabar(frame)
    assert direction.iloc[1] == -1.0, "close < open must be a down bar"
    assert direction.iloc[2] == -1.0, "flat bar must CARRY the -1, not reset"
    assert direction.iloc[3] == -1.0, "and keep carrying it"
    assert direction.iloc[4] == 1.0, "close > open flips it back up"


def test_a_leading_flat_run_takes_pines_initial_true():
    from pandas_ta.volume.up_and_down_volume import _classify_intrabar

    idx = date_range("2024-03-01 09:00", periods=3, freq="5min")
    frame = DataFrame({"open": [10.0, 10.0, 10.0],
                       "close": [10.0, 10.0, 10.0]}, index=idx)
    assert (_classify_intrabar(frame) == 1.0).all(), (
        "`var bool isBuyVolume = true` (RA2vGpkA-ta.pine:385)"
    )


def test_the_second_test_is_close_against_the_previous_bar():
    """`close > close[1]` is the LOWER-timeframe previous bar, and it is not
    reset at a main-bar boundary -- only the accumulators are (`:387-392`)."""
    from pandas_ta.volume.up_and_down_volume import _classify_intrabar

    idx = date_range("2024-03-01 09:00", periods=3, freq="5min")
    frame = DataFrame({"open": [10.0, 11.0, 11.0],
                       "close": [10.0, 11.0, 12.0]}, index=idx)
    direction = _classify_intrabar(frame)
    assert direction.iloc[2] == 1.0, "close == open, but close > close[1]"


# ---------------------------------------------------------- 3./4. identities

def test_up_and_down_volume_identities():
    frame = lower_frame()
    udv = ta.up_and_down_volume(frame, anchor="1h")
    total = frame["volume"].groupby(frame.index.floor("1h")).sum()

    assert list(udv.columns) == ["UDV_POS", "UDV_NEG", "UDV_DELTA",
                                 "UDV_DELTA_PCT"]
    assert udv.shape[0] == HOURS
    assert ((udv["UDV_POS"] - udv["UDV_NEG"]) - total).abs().max() < 1e-9, (
        "every bar's volume must land in exactly one bucket"
    )
    assert (udv["UDV_DELTA"]
            - (udv["UDV_POS"] + udv["UDV_NEG"])).abs().max() < 1e-9
    assert (udv["UDV_POS"] >= 0).all() and (udv["UDV_NEG"] <= 0).all(), (
        "Pine returns down volume as a NEGATIVE quantity (`:399`)"
    )
    assert udv["UDV_DELTA_PCT"].between(-1.0, 1.0).all()


def test_volume_delta_excursions_bracket_the_open_by_construction():
    frame = lower_frame()
    vd = ta.volume_delta(frame, anchor="1h")
    assert list(vd.columns) == ["VD_OPEN", "VD_HIGH", "VD_LOW", "VD_LAST",
                                "VD_DELTA_PCT"]
    assert (vd["VD_HIGH"] >= vd["VD_OPEN"]).all()
    assert (vd["VD_OPEN"] >= vd["VD_LOW"]).all()


def test_without_a_cumulative_period_it_is_the_plain_delta():
    """Pine treats an empty period string the same way (`:483-485`)."""
    frame = lower_frame()
    udv = ta.up_and_down_volume(frame, anchor="1h")
    vd = ta.volume_delta(frame, anchor="1h")
    assert (vd["VD_OPEN"].abs() < 1e-12).all()
    assert (vd["VD_LAST"] - udv["UDV_DELTA"]).abs().max() < 1e-9


def test_a_cumulative_period_accumulates_and_resets():
    frame = lower_frame()
    plain = ta.volume_delta(frame, anchor="1h")
    cvd = ta.volume_delta(frame, anchor="1h", cumulative_period="1D")

    first_of_day = cvd["VD_OPEN"].groupby(cvd.index.floor("1D")).first()
    assert (first_of_day.abs() < 1e-12).all(), "each period must open at 0.0"
    assert (cvd["VD_LAST"] - plain["VD_LAST"]).abs().max() > 0, (
        "a CVD that equals the plain delta is not accumulating"
    )
    # and it really is a running sum within the day
    for _day, block in cvd.groupby(cvd.index.floor("1D")):
        deltas = plain["VD_LAST"].loc[block.index]
        assert (block["VD_LAST"] - deltas.cumsum()).abs().max() < 1e-9


def test_a_series_anchor_matches_the_equivalent_string_anchor():
    frame = lower_frame()
    by_string = ta.up_and_down_volume(frame, anchor="1h")
    by_series = ta.up_and_down_volume(
        frame, anchor=Series(frame.index.floor("1h"), index=frame.index))
    assert by_string.shape == by_series.shape
    assert (by_string.to_numpy() - by_series.to_numpy() == 0).all()


# ------------------------------------------------------------- 5. ML contract

def test_only_the_pct_columns_are_scale_free_in_volume():
    """Multiplying VOLUME by 8 must leave the ratios untouched and move the
    raw sums -- that is the whole reason the `_PCT` columns exist."""
    frame = lower_frame()
    scaled = frame.copy()
    scaled["volume"] = scaled["volume"] * 8

    base = ta.up_and_down_volume(frame, anchor="1h")
    other = ta.up_and_down_volume(scaled, anchor="1h")
    assert (base["UDV_DELTA_PCT"]
            - other["UDV_DELTA_PCT"]).abs().max() == 0.0
    assert (base["UDV_DELTA"] - other["UDV_DELTA"]).abs().max() > 0.0, (
        "the raw delta is liquidity-scaled and must move; if it does not, the "
        "fixture is not exercising what this test claims"
    )


def test_reachability_on_the_fixture():
    """Gate C, with the counts stated."""
    frame = lower_frame()
    udv = ta.up_and_down_volume(frame, anchor="1h")
    vd = ta.volume_delta(frame, anchor="1h", cumulative_period="1D")
    for out in (udv, vd):
        for column in out.columns:
            assert out[column].notna().all(), f"{column} has gaps"
            assert out[column].nunique() > 1, f"{column} is CONSTANT"


# ---------------------------------------------------------------- wiring

@pytest.mark.parametrize("name", ["up_and_down_volume", "volume_delta"])
def test_they_are_callable_but_deliberately_OUTSIDE_Category(name):
    """The exclusion is the point, and it is pinned rather than assumed.

    These REQUIRE a second (lower-timeframe) frame. `df.ta.strategy()` cannot
    supply one, so registering them in `Category` took the entire
    multiprocessing sweep down with `ValueError: the lower-timeframe frame is
    REQUIRED` — three red tests in `test_wiring_accessors.py`, including the
    two that exist as a monument to WIRING-1. This is that regression in
    reverse: WIRING-1 was a `Category` name with no accessor; this was an
    accessor that cannot be called with what a sweep passes.

    They stay module- and accessor-callable, alongside `drawdown`/`ma`/`vp`.
    """
    assert hasattr(ta, name), "must stay callable at module level"
    assert hasattr(DataFrame().ta, name), "and on the df.ta accessor"
    assert name not in ta.Category["volume"], (
        f"{name} is back in Category -- df.ta.strategy() will raise on it"
    )


def test_the_strategy_sweep_still_runs():
    """The regression this exclusion exists to prevent, caught here too rather
    than only in `test_wiring_accessors.py`."""
    import numpy as np

    rng = np.random.default_rng(1)
    n = 120
    close = 100 + np.cumsum(rng.normal(0, 1, n))
    df = DataFrame({
        "open": close, "high": close + 1, "low": close - 1, "close": close,
        "volume": rng.integers(1e5, 1e6, n).astype(float),
    }, index=date_range("2024-01-01", periods=n, freq="D"))
    # BOTH paths. The category sweep passed even while the bug was live; it
    # was `strategy("all")` -- which enumerates ACCESSOR methods, not just
    # `Category` -- that took the multiprocessing pool down. Removing the two
    # from `Category` was necessary and NOT sufficient.
    df.ta.strategy("volume", verbose=False, timed=False, cores=0)
    df.ta.strategy(verbose=False, timed=False, cores=0)


def test_both_are_in_the_default_strategy_exclusion_list():
    """Pinned by name, because `Category` removal alone did not stop the sweep.

    `vp` sits in the same list for the same class of reason: it needs
    something a bulk sweep cannot hand it.
    """
    import inspect

    from pandas_ta.core import AnalysisIndicators

    source = inspect.getsource(AnalysisIndicators.strategy)
    for name in ("up_and_down_volume", "volume_delta"):
        assert f'"{name}"' in source, (
            f"{name} left the default exclusion list -- df.ta.strategy() will "
            f"raise on it again"
        )
