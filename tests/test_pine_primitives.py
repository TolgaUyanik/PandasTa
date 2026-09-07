# -*- coding: utf-8 -*-
"""Tests for `pandas_ta.utils._pine` -- PINEBI-1a's 18 Pine primitives.

These are the vocabulary, not features: `ta.highest` or `ta.lowest` appear in 345
of the 2,211 scripts in `docs/pine/` (the union -- 332 and 306 individually), so
every later port is written in terms of them and a wrong primitive is a wrong
port, silently, everywhere.

What these tests pin, in order of how much it would hurt to lose:

* **The Pine semantics that differ from the obvious pandas one-liner.** Each has
  its own test with hand-computed expectations on a 10-bar series small enough to
  check by eye:
  - `barssince` / `valuewhen` return NaN before the first true, not 0 and not a
    back-fill (`test_barssince_is_na_before_the_first_true`);
  - `percentrank` ranks against the PREVIOUS `length` bars, excluding the current
    one -- including it would floor every result at `100/length`
    (`test_percentrank_excludes_the_current_bar`);
  - `*bars` return non-positive OFFSETS, not distances
    (`test_highestbars_returns_a_non_positive_offset`);
  - `cum` treats NaN as 0 rather than poisoning the tail (`test_cum_ignores_nan`).
* **`pivothigh`/`pivotlow` report on the CONFIRMATION bar**, `right` bars after
  the pivot, and nowhere else (`test_pivothigh_reports_on_the_confirmation_bar`).
  This is the primitive's causality cost and the thing most likely to be
  "simplified" into a lookahead.
* **Causality**, by mutant (`test_pivot_mutant_backdating_is_caught`): the module
  source is read, the pivot write is moved from `p + right` to `p`, the mutant is
  `exec`'d in memory, and the real module must differ. Prefix truncation cannot
  see back-dating; mutation can.
* **They are NOT registered as indicators** (`test_primitives_are_not_indicators`)
  -- absent from `Category`, absent from `df.ta`. A primitive that leaks into
  `df.ta.strategy()` becomes an unaudited feature column.

`pivot_point_levels` is checked against the Traditional formula recomputed in the
test, and for using only bars strictly before its anchor.
"""
import importlib.util
import io
import re

import numpy as np
import pandas as pd
import pytest

from .context import pandas_ta

# A 10-bar series with no ties, small enough to verify by hand.
S = pd.Series([1.0, 5.0, 3.0, 9.0, 2.0, 7.0, 4.0, 8.0, 6.0, 10.0])

PRIMITIVES = [
    "highest", "lowest", "highestbars", "lowestbars", "valuewhen", "barssince",
    "cum", "correlation", "percentrank", "percentile_nearest_rank",
    "percentile_linear_interpolation", "pivot_point_levels", "pivothigh",
    "pivotlow", "highest_since", "lowest_since", "alltime_max", "alltime_min",
]


def test_every_primitive_is_exported():
    missing = [n for n in PRIMITIVES if not callable(getattr(pandas_ta, n, None))]
    assert missing == [], missing


def test_primitives_are_not_indicators():
    """Vocabulary, not features: never in `Category`, never on `df.ta`.

    A primitive registered as an indicator would be swept into
    `df.ta.strategy()` and become a feature column nobody measured.
    """
    registered = {n for names in pandas_ta.Category.values() for n in names}
    leaked = sorted(set(PRIMITIVES) & registered)
    assert leaked == [], f"primitives registered as indicators: {leaked}"

    df = pd.DataFrame()
    exposed = [n for n in PRIMITIVES if hasattr(df.ta, n)]
    assert exposed == [], f"primitives exposed on df.ta: {exposed}"


def test_highest_and_lowest_include_the_current_bar():
    """Pine's window is inclusive: `highest(src, 3)` at bar i covers i-2..i."""
    assert pandas_ta.highest(S, 3).tolist()[2:5] == [5.0, 9.0, 9.0]
    assert pandas_ta.lowest(S, 3).tolist()[2:5] == [1.0, 3.0, 2.0]
    # NaN warm-up, not a partial window.
    assert pandas_ta.highest(S, 3).iloc[:2].isna().all()


def test_highestbars_returns_a_non_positive_offset():
    """0 = the current bar is the extreme; -2 = two bars back. Not a distance."""
    hb = pandas_ta.highestbars(S, 3)
    assert hb.tolist()[2:6] == [-1.0, 0.0, -1.0, -2.0]
    assert (hb.dropna() <= 0).all(), "offsets must be non-positive"
    lb = pandas_ta.lowestbars(S, 3)
    assert (lb.dropna() <= 0).all()


def test_bars_offsets_break_ties_toward_the_nearest_bar():
    """On a plateau Pine reports the NEAREST extreme, offset 0 -- not the oldest.

    `np.argmax` returns the first maximum, which inverts this. The main fixture
    is deliberately tie-free, so ties need their own frame: 21.17% of real BIST
    bars close exactly at an extreme (CLAUDE.md), making this the common case.
    """
    plateau = pd.Series([5.0, 5.0, 5.0, 1.0])
    assert pandas_ta.highestbars(plateau, 3).iloc[2] == 0.0
    assert pandas_ta.highestbars(plateau, 3).iloc[3] == -1.0

    trough = pd.Series([1.0, 1.0, 1.0, 5.0])
    assert pandas_ta.lowestbars(trough, 3).iloc[2] == 0.0
    assert pandas_ta.lowestbars(trough, 3).iloc[3] == -1.0


def test_barssince_is_na_before_the_first_true():
    """NaN, not 0 -- 0 would claim the condition fired on that bar."""
    bs = pandas_ta.barssince(S > 6)
    assert bs.iloc[:3].isna().all(), "condition never true yet -> na"
    assert bs.iloc[3] == 0, "true on this bar -> 0"
    assert bs.iloc[4] == 1
    assert bs.iloc[5] == 0


def test_valuewhen_walks_back_by_occurrence():
    v0 = pandas_ta.valuewhen(S > 6, S, 0)
    v1 = pandas_ta.valuewhen(S > 6, S, 1)
    assert v0.iloc[:3].isna().all()
    assert v0.iloc[3] == 9.0 and v0.iloc[4] == 9.0 and v0.iloc[5] == 7.0
    # One occurrence back needs two occurrences to have happened.
    assert v1.iloc[:5].isna().all()
    assert v1.iloc[5] == 9.0


def test_percentrank_excludes_the_current_bar():
    """The current value is ranked AGAINST the window, not counted inside it.

    Bar 4 is 2.0 against [1, 5, 3, 9]: one value <= 2, so 25%. Including the
    current bar would make 2/5 = 40% and would floor every result at 100/length.
    """
    pr = pandas_ta.percentrank(S, 4)
    assert pr.iloc[:4].isna().all()
    assert pr.iloc[4] == 25.0
    assert pr.iloc[9] == 100.0          # 10.0 is above all of [7, 4, 8, 6]
    # NOT `(pr > 0).all()`: a percentrank of 0 is legitimate whenever the
    # current value is below every one of the previous `length` values, and on a
    # falling series correct code produces it on every bar. The 25.0 assertion
    # above is what actually discriminates exclusive (25.0) from inclusive (40.0).
    falling = pd.Series([9.0, 8.0, 7.0, 6.0, 5.0, 4.0])
    assert pandas_ta.percentrank(falling, 4).iloc[4] == 0.0, (
        "a strictly falling series must be able to reach 0"
    )


def test_cum_ignores_nan():
    s = pd.Series([1.0, np.nan, 2.0, 3.0])
    assert pandas_ta.cum(s).tolist() == [1.0, 1.0, 3.0, 6.0]


@pytest.mark.parametrize("percentage,expected", [
    (1, 1.0), (25, 1.0), (50, 2.0), (75, 3.0), (100, 4.0),
])
def test_percentile_nearest_rank_pins_the_ceil_formula(percentage, expected):
    """`ceil(P/100 * N)`-th smallest -- these cases separate it from floor/round.

    Asserting only "the result is one of the observed values" would pass on any
    of the four and leave the index formula unpinned.
    """
    window = pd.Series([1.0, 2.0, 3.0, 4.0])
    got = pandas_ta.percentile_nearest_rank(window, 4, percentage).iloc[-1]
    assert got == expected


def test_percentile_variants_differ_the_way_pine_says():
    """Nearest-rank returns an OBSERVED value; interpolation need not."""
    window = pd.Series([1.0, 2.0, 3.0, 4.0])
    nr = pandas_ta.percentile_nearest_rank(window, 4, 50).iloc[-1]
    li = pandas_ta.percentile_linear_interpolation(window, 4, 50).iloc[-1]
    assert nr == 2.0 and nr in set(window.tolist())
    assert li == 2.5, "linear interpolation sits between the neighbours"
    assert nr != li


def test_correlation_hits_the_hand_computed_values():
    """Hand-computed, not compared to a copy of the implementation's own body.

    Pine's `ta.correlation` is `cov / (stdev * stdev)` at `biased=true`
    (ddof=0); the ddof cancels in the ratio, so the Pearson value is the same
    either way -- which this test demonstrates rather than assumes.
    """
    a = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
    assert pandas_ta.correlation(a, a * 3 + 1, 5).iloc[-1] == pytest.approx(1.0)
    assert pandas_ta.correlation(a, -a, 5).iloc[-1] == pytest.approx(-1.0)

    b = pd.Series([2.0, 1.0, 4.0, 3.0, 5.0])
    x, y = a.to_numpy(), b.to_numpy()
    cov = np.mean((x - x.mean()) * (y - y.mean()))          # ddof=0, as Pine
    expected = cov / (x.std(ddof=0) * y.std(ddof=0))
    assert pandas_ta.correlation(a, b, 5).iloc[-1] == pytest.approx(expected)
    # By hand: mean(a)=mean(b)=3; deviations a=(-2,-1,0,1,2), b=(-1,-2,1,0,2);
    # products sum to 8, /5 = 1.6 covariance; both stdevs are sqrt(2), so
    # 1.6 / 2 = 0.8.
    assert expected == pytest.approx(0.8)


def test_pivothigh_reports_on_the_confirmation_bar():
    """The pivot's PRICE lands `right` bars after the pivot, NaN elsewhere.

    With left=right=1, bar 1 (5.0) is a pivot high (5 > 1 and 5 > 3), and Pine
    reports it at bar 2. Reporting it at bar 1 would be a one-bar lookahead.
    """
    ph = pandas_ta.pivothigh(S, 1, 1)
    assert np.isnan(ph.iloc[1]), "pivot must not be reported on its own bar"
    assert ph.iloc[2] == 5.0
    assert ph.iloc[4] == 9.0
    assert ph.notna().sum() < len(S), "a pivot on every bar is not a pivot"

    pl = pandas_ta.pivotlow(S, 1, 1)
    assert pl.iloc[3] == 3.0            # bar 2 (3.0) confirmed at bar 3
    assert np.isnan(pl.iloc[2])


def test_pivothigh_right_lag_scales_with_the_parameter():
    """right=2 moves the report two bars out -- the documented causality cost."""
    ph1 = pandas_ta.pivothigh(S, 1, 1)
    ph2 = pandas_ta.pivothigh(S, 1, 2)
    first1 = int(ph1.notna().to_numpy().argmax())
    first2 = int(ph2.notna().to_numpy().argmax())
    assert first2 > first1


def test_pivot_mutant_backdating_is_caught():
    """Gate B: move the write from `p + right` to `p` and the output must change."""
    spec = importlib.util.find_spec("pandas_ta.utils._pine")
    src = open(spec.origin, encoding="utf8").read()
    mutated, count = re.subn(r"out\[p \+ right\] = values\[p\]",
                             "out[p] = values[p]", src)
    assert count == 2, f"expected two pivot write sites, patched {count}"

    ns = {"__name__": "pine_mutant"}
    exec(compile(mutated, "<pine_mutant>", "exec"), ns)

    # BOTH patched sites are compared. The previous version patched two and
    # checked `pivothigh` only, so `pivotlow` could have lost its confirmation
    # lag with the mutant test still green -- a guard that half-covers the
    # thing it mutates.
    unguarded = []
    for fn in ("pivothigh", "pivotlow"):
        real = getattr(pandas_ta, fn)(S, 1, 1).to_numpy()
        mutant = ns[fn](S, 1, 1).to_numpy()
        if np.array_equal(real, mutant, equal_nan=True):
            unguarded.append(fn)
    assert unguarded == [], (
        f"back-dating the pivot write changed nothing for {unguarded} -- the "
        f"confirmation lag is not actually being applied there"
    )


def test_highest_since_and_lowest_since_track_from_bar_zero():
    """Transliterated from `docs/pine/RA2vGpkA-ta.pine:236-240`, not from intuition.

    The library's `math.max(nz(source, result), nz(result, source))` line runs
    UNCONDITIONALLY, so the run is seeded on the first defined bar and the
    series is never `na` afterwards -- it does not wait for the first true
    condition. A true condition RESETS the run to that bar's own value. The
    intuitive reading (NaN until the first true) is what this port shipped
    first, and it was wrong.
    """
    hs = pandas_ta.highest_since(S > 6, S)
    ls = pandas_ta.lowest_since(S > 6, S)

    # Bars 0-2: no trigger yet, but tracking has already started.
    assert hs.iloc[0] == 1.0
    assert hs.iloc[1] == 5.0
    assert hs.iloc[2] == 5.0, "running max, not the current bar"
    assert ls.iloc[2] == 1.0

    assert hs.iloc[3] == 9.0            # trigger: run resets to this bar
    assert hs.iloc[4] == 9.0
    assert hs.iloc[5] == 7.0            # new trigger, new run
    assert ls.iloc[4] == 2.0


def test_conditions_treat_nan_as_false():
    """Pine's `na` condition is FALSE. `Series.astype(bool)` maps NaN to True.

    A condition built on any rolling source is NaN for its warm-up bars, so
    getting this wrong fires every condition at the head of every series.
    """
    cond = pd.Series([np.nan, np.nan, 1.0, 0.0, 1.0])
    src = pd.Series([10.0, 20.0, 30.0, 40.0, 50.0])

    bs = pandas_ta.barssince(cond)
    assert bs.iloc[:2].isna().all(), "NaN condition must not count as a trigger"
    assert bs.iloc[2] == 0 and bs.iloc[3] == 1

    vw = pandas_ta.valuewhen(cond, src, 0)
    assert vw.iloc[:2].isna().all()
    assert vw.iloc[2] == 30.0


def test_pivot_point_levels_match_the_traditional_formula():
    idx = pd.date_range("2024-01-01", periods=90, freq="D")
    rng = np.random.default_rng(4)
    close = pd.Series(100 + np.cumsum(rng.normal(0, 1, 90)), index=idx)
    high = close + 1.0
    low = close - 1.0

    levels = pandas_ta.pivot_point_levels(high, low, close)
    assert list(levels.columns) == [
        "PP", "R1", "S1", "R2", "S2", "R3", "S3", "R4", "S4", "R5", "S5"
    ], "Pine's Traditional set is eleven levels, not seven"

    # January is the first period: nothing completed before it, so no levels.
    assert levels.loc["2024-01-31"].isna().all()

    # February's levels come from January's completed high/low/close.
    jan = slice("2024-01-01", "2024-01-31")
    pp = (high[jan].max() + low[jan].min() + close[jan].iloc[-1]) / 3.0
    feb = levels.loc["2024-02-05"]
    assert abs(feb["PP"] - pp) < 1e-9
    assert abs(feb["R1"] - (2 * pp - low[jan].min())) < 1e-9
    assert abs(feb["S1"] - (2 * pp - high[jan].max())) < 1e-9


def test_pivot_point_levels_needs_an_anchor_without_a_datetime_index():
    with pytest.raises(ValueError, match="anchor"):
        pandas_ta.pivot_point_levels(S + 1, S - 1, S)


@pytest.mark.parametrize("scale", [2.0, 8.0, 64.0])
def test_price_primitives_are_scale_equivariant(scale):
    """Scaling prices scales the price-valued outputs by the same factor.

    `percentrank` and the `*bars` offsets are scale-INVARIANT instead, which is
    the other half of the same property.
    """
    for fn in (pandas_ta.highest, pandas_ta.lowest):
        base = fn(S, 3).to_numpy()
        scaled = fn(S * scale, 3).to_numpy()
        assert np.allclose(base * scale, scaled, equal_nan=True), fn.__name__

    assert np.array_equal(pandas_ta.highestbars(S, 3).to_numpy(),
                          pandas_ta.highestbars(S * scale, 3).to_numpy(),
                          equal_nan=True)
    assert np.array_equal(pandas_ta.percentrank(S, 4).to_numpy(),
                          pandas_ta.percentrank(S * scale, 4).to_numpy(),
                          equal_nan=True)


def test_pivot_point_levels_rejects_unimplemented_types():
    """Pine defines six types; only Traditional is implemented, and it says so.

    The parameter is `kind=`, not Pine's `type=`, to avoid shadowing the
    builtin -- the docstring records the rename alongside the other signature
    divergences.
    """
    idx = pd.date_range("2024-01-01", periods=70, freq="D")
    close = pd.Series(np.linspace(100, 120, 70), index=idx)
    with pytest.raises(ValueError, match="Traditional"):
        pandas_ta.pivot_point_levels(close + 1, close - 1, close, kind="Fibonacci")


def test_pivot_point_levels_r4_and_r5_extend_the_ladder():
    """R4/R5 were missing entirely in the first version of this port."""
    idx = pd.date_range("2024-01-01", periods=90, freq="D")
    rng = np.random.default_rng(4)
    close = pd.Series(100 + np.cumsum(rng.normal(0, 1, 90)), index=idx)
    levels = pandas_ta.pivot_point_levels(close + 1.0, close - 1.0, close)
    row = levels.loc["2024-02-05"]
    assert row["R3"] < row["R4"] < row["R5"]
    assert row["S3"] > row["S4"] > row["S5"]


@pytest.mark.parametrize("fn", [
    "highest", "lowest", "highestbars", "lowestbars", "percentrank",
    "percentile_nearest_rank", "percentile_linear_interpolation",
])
@pytest.mark.parametrize("bad", [0, -5])
def test_non_positive_lengths_raise(fn, bad):
    """Pine raises; coercing a typo'd length to 1 hands back plausible garbage."""
    with pytest.raises(ValueError, match="length"):
        getattr(pandas_ta, fn)(S, bad)


@pytest.mark.parametrize("bad", [0, -5])
def test_pivot_left_and_right_also_validate(bad):
    """`left`/`right` were still silently coerced five functions below `_length`."""
    with pytest.raises(ValueError, match="length"):
        pandas_ta.pivothigh(S, bad, 1)
    with pytest.raises(ValueError, match="length"):
        pandas_ta.pivotlow(S, 1, bad)


def test_occurrence_and_percentage_validate():
    with pytest.raises(ValueError, match="occurrence"):
        pandas_ta.valuewhen(S > 6, S, -1)
    for bad in (-20, 150):
        with pytest.raises(ValueError, match="percentage"):
            pandas_ta.percentile_nearest_rank(S, 4, bad)
        with pytest.raises(ValueError, match="percentage"):
            pandas_ta.percentile_linear_interpolation(S, 4, bad)


def test_pivots_are_strict_on_a_plateau():
    """A plateau is NOT a pivot -- `>` on both sides, not `>=`.

    Mutating `>` to `>=` in both functions leaves every other test in this file
    green, because the main fixture is tie-free by construction. This is the
    same blind spot that hid the `highestbars` tie-break bug, so it gets its own
    frame: on `[1, 5, 5, 1, 2]` a non-strict comparison reports pivots at bars 2
    and 3 that a strict one does not.
    """
    assert pandas_ta.pivothigh(pd.Series([1.0, 5.0, 5.0, 1.0, 2.0]), 1, 1).isna().all()
    assert pandas_ta.pivotlow(pd.Series([5.0, 1.0, 1.0, 5.0, 4.0]), 1, 1).isna().all()
    # ...while a strict extreme in the same shape IS reported.
    assert pandas_ta.pivothigh(pd.Series([1.0, 5.0, 6.0, 1.0, 2.0]), 1, 1).iloc[3] == 6.0


def test_pivot_strictness_mutant_is_caught():
    """Gate B for the comparison itself: `>` -> `>=` must change the output."""
    spec = importlib.util.find_spec("pandas_ta.utils._pine")
    src = open(spec.origin, encoding="utf8").read()
    mutated, count = re.subn(r"\(values\[p\] > window_", "(values[p] >= window_", src)
    assert count == 2, f"expected two strict comparisons in pivothigh, got {count}"
    mutated, low_count = re.subn(r"\(values\[p\] < window_",
                                 "(values[p] <= window_", mutated)
    assert low_count == 2, f"expected two in pivotlow, got {low_count}"

    ns = {"__name__": "pine_strict_mutant"}
    exec(compile(mutated, "<pine_strict_mutant>", "exec"), ns)

    plateau = pd.Series([1.0, 5.0, 5.0, 1.0, 2.0])
    assert not np.array_equal(
        pandas_ta.pivothigh(plateau, 1, 1).to_numpy(),
        ns["pivothigh"](plateau, 1, 1).to_numpy(), equal_nan=True), (
        "loosening the pivothigh comparison changed nothing"
    )
    trough = pd.Series([5.0, 1.0, 1.0, 5.0, 4.0])
    assert not np.array_equal(
        pandas_ta.pivotlow(trough, 1, 1).to_numpy(),
        ns["pivotlow"](trough, 1, 1).to_numpy(), equal_nan=True), (
        "loosening the pivotlow comparison changed nothing"
    )


def test_all_time_extremes_on_a_gap():
    """NaN is emitted on the gap bar and then ignored -- the fourth na policy.

    `cummax` blanks the gap and resumes as if it were not there. Pine's
    behaviour on `na` inside `ta.max` is unverified, so this pins the PORT's
    choice deliberately rather than leaving it an accident of the pandas call.
    """
    gapped = pd.Series([1.0, np.nan, 3.0, 2.0, 5.0])
    got = pandas_ta.alltime_max(gapped).tolist()
    assert got[0] == 1.0 and np.isnan(got[1])
    assert got[2:] == [3.0, 3.0, 5.0]

    lows = pandas_ta.alltime_min(gapped).tolist()
    assert lows[0] == 1.0 and np.isnan(lows[1])
    assert lows[2:] == [1.0, 1.0, 1.0]


def test_the_builtins_are_not_shadowed():
    """`from pandas_ta import *` must not replace Python's `max`/`min`.

    `_pine.__all__` feeds `pandas_ta.utils`, which `core.py` star-imports, so a
    primitive named `max` would become `pandas_ta.max` AND land in any user
    namespace doing a star import -- returning a Series where a scalar was
    meant, with no error.
    """
    # The package must not define these names at all. (`pandas_ta.max is
    # builtins.max` would be the wrong check -- a module does not expose
    # builtins as attributes, so it is False either way.)
    for name in ("max", "min"):
        assert not hasattr(pandas_ta, name), (
            f"pandas_ta.{name} exists; a star import would put it on the "
            f"name {name!r} in the caller's namespace"
        )

    # And the thing a user actually gets bitten by.
    namespace = {}
    exec("from pandas_ta import *", namespace)
    for name in ("max", "min"):
        assert name not in namespace, f"`from pandas_ta import *` bound {name!r}"

    assert callable(pandas_ta.alltime_max) and callable(pandas_ta.alltime_min)


def test_all_time_extremes_are_not_rolling():
    """`ta.max`/`ta.min` take no length: they are the all-time extremes.

    Mislabelled "not a Pine built-in" in the first coverage pass and queued into
    PINEBI-1e as ROLLING fork utilities. The corpus says otherwise --
    `docs/pine/c1pPR2kI.pine:137-139` comments `// All Time High and Low`
    directly over `ta.max(HIGH_)` / `ta.min(LOW_)`.
    """
    assert pandas_ta.alltime_max(S).tolist() == [1, 5, 5, 9, 9, 9, 9, 9, 9, 10]
    assert pandas_ta.alltime_min(S).tolist() == [1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
    # A running extreme never retreats.
    assert pandas_ta.alltime_max(S).is_monotonic_increasing
    assert pandas_ta.alltime_min(S).is_monotonic_decreasing


def test_the_na_false_row_names_every_condition_argument():
    """MINOR (round 9): the na-policy table is discovered, not maintained.

    The module docstring's "NaN is FALSE" row listed four functions while five
    route an argument through `_as_condition` -- `pivot_point_levels`'s `anchor`
    was missing. Correcting the row would fix the instance; this closes the
    class, so a sixth condition-taking primitive added tomorrow fails here until
    it is documented AND until it actually treats `na` as false.
    """
    import importlib.util

    spec = importlib.util.find_spec("pandas_ta.utils._pine")
    src = io.open(spec.origin, encoding="utf8").read()

    # Discover from the source: every top-level def whose body calls
    # `_as_condition`. Not a hand list -- that is the defect being closed.
    callers = set()
    current = None
    for line in src.splitlines():
        match = re.match(r"^def ([a-z_][a-z0-9_]*)\(", line)
        if match:
            current = match.group(1)
        elif current and not current.startswith("_") and "_as_condition(" in line:
            callers.add(current)

    assert len(callers) >= 5, (
        f"expected at least the five known condition-taking primitives, "
        f"discovered {sorted(callers)} -- the scan is broken, not the module"
    )

    from pandas_ta.utils import _pine

    doc = _pine.__doc__
    row = [ln for ln in doc.splitlines() if "NaN is FALSE" in ln]
    assert len(row) == 1, "expected exactly one `NaN is FALSE` table row"
    undocumented = sorted(n for n in callers if f"`{n}`" not in row[0])
    assert undocumented == [], (
        f"these route an argument through `_as_condition` but are absent from "
        f"the module docstring's `NaN is FALSE` row: {undocumented}"
    )

    # And the row must be true, not merely complete: a NaN condition must not
    # fire. Each caller takes its condition first, so a NaN-only condition is
    # enough to separate "never fires" from "always fires".
    never = pd.Series([np.nan] * len(S), index=S.index)
    assert pandas_ta.barssince(never).isna().all(), "NaN condition fired"
    assert pandas_ta.valuewhen(never, S).isna().all(), "NaN condition fired"


@pytest.mark.parametrize("bad", [2.7, 3.5, -0.5])
def test_a_non_integral_length_is_rejected_not_truncated(bad):
    """MINOR (round 9): `_length`'s docstring promised a typo would raise.

    Its body called `int()`, so `highest(S, 2.7)` silently produced a 2-bar
    window named `HIGHEST_2` -- a wrong feature column under a plausible name,
    which survives review better than a crash does.
    """
    with pytest.raises((ValueError, TypeError)):
        pandas_ta.highest(S, bad)

    # Whole-number floats still work: `length=3.0` is not a typo, and callers
    # pass numpy integers.
    assert pandas_ta.highest(S, 3.0).equals(pandas_ta.highest(S, 3))
    assert pandas_ta.highest(S, np.int64(3)).equals(pandas_ta.highest(S, 3))
