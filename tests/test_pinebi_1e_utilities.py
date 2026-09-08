# -*- coding: utf-8 -*-
"""PINEBI-1e — four ML utilities: `rolling_sum`, `normalize`, `covariance`, `pivot`.

These are **fork utilities, not Pine ports.** None of the four is called live
anywhere in `docs/pine/` — the corpus hits are comments and third-party library
methods, one of which literally reads *"Pine has no native ta.covariance"*. So
they carry no TradingView provenance and **no MPL attribution**, which would be
false. ⚠ The `ta.sum` half of that was WRONG and is corrected here: Pine v5 renamed
`ta.sum` to `math.sum`, and the corpus calls it **214 times across 88 files**,
45 of them MPL-licensed. The earlier claim that it is "never called live" was a
grep against the retired name. The no-attribution conclusion still holds, but
for the real reason: no source is copied — the implementation is pandas'
`Series.rolling().sum()`, not a transliteration of anything.

Pinned here, in order of how much it would hurt to lose:

1. **`normalize` is causal.** A whole-series min-max is the textbook look-ahead
   leak — it tells bar 5 what bar 900's maximum was. Proven with a mutant that
   is shown to be CAUGHT, not merely by truncating a prefix.
2. **`pivot` emits distances, never price levels.** The task's acceptance
   criterion, and the `PX` rule from `docs/MLCompanionContract.md`. Every one of
   the 11 columns must be scale-free; the test multiplies price by 8 and 64 and
   requires bit-identical output.
3. **`pivot` is not a duplicate of `pivot_point_levels`.** That function returns
   11 raw prices (`PP`, `R1`-`R5`, `S1`-`S5`), which are dead as features. This
   is its scale-free companion. If someone "simplifies" it back into the levels,
   `test_pivot_is_scale_free` fails.
4. **`rolling_sum` is named that, not `sum`**, so it cannot shadow the builtin
   for `from pandas_ta import *`. The emitted COLUMN is still `SUM_<length>`, so
   nothing a mined rule matches on changed.
5. **`covariance` inner-joins mismatched indices** rather than producing a
   plausible-looking number off misaligned bars.

Honest about what these are: `rolling_sum` and `covariance` are **not
scale-free** and are not model features on price input. They are shipped as
building blocks, and their docstrings say so rather than implying otherwise.
`normalize` and `pivot` ARE scale-free and are features.
"""
import numpy as np
import pytest
from pandas import DataFrame, Series, date_range

import pandas_ta as ta


def frame(n=400, seed=5):
    rng = np.random.default_rng(seed)
    close = 100 + np.cumsum(rng.normal(0, 1, n))
    idx = date_range("2024-01-01", periods=n, freq="D")
    return DataFrame({
        "open": close,
        "high": close + abs(rng.normal(0, 1, n)),
        "low": close - abs(rng.normal(0, 1, n)),
        "close": close,
        "volume": rng.integers(1e5, 1e6, n).astype(float),
    }, index=idx)


# ------------------------------------------------------------- rolling_sum

def test_rolling_sum_is_the_sliding_sum_and_keeps_the_SUM_column_name():
    df = frame()
    out = ta.rolling_sum(df["close"], length=10)
    assert out.name == "SUM_10"
    expected = df["close"].rolling(10, min_periods=10).sum()
    assert (out - expected).abs().max() == 0.0
    assert out.isna().sum() == 9


def test_rolling_sum_does_not_shadow_the_builtin():
    """The reason it is not called `sum`."""
    import pandas_ta
    assert not hasattr(pandas_ta, "sum") or pandas_ta.sum is sum, (
        "pandas_ta.sum would shadow the builtin for `from pandas_ta import *`"
    )
    assert hasattr(pandas_ta, "rolling_sum")


# --------------------------------------------------------------- normalize

def test_normalize_is_bounded_and_hits_both_ends():
    out = ta.normalize(frame()["close"], length=14)
    settled = out.dropna()
    assert settled.min() >= 0.0 and settled.max() <= 1.0
    assert settled.min() == pytest.approx(0.0, abs=1e-12)
    assert settled.max() == pytest.approx(1.0, abs=1e-12)
    assert 0 < settled.size < out.size, "must warm up, and must fire"


def test_normalize_is_scale_free():
    """Gate D: invariant under multiplication, because it is a position in a range."""
    close = frame()["close"]
    base = ta.normalize(close, length=14)
    for factor in (8, 64):
        scaled = ta.normalize(close * factor, length=14)
        both = ~(base.isna() | scaled.isna())
        assert (base[both] - scaled[both]).abs().max() == 0.0, (
            f"not scale-free at x{factor} -- CLAUDE.md Gate D requires "
            f"bit-identical, and it measures 0.0 today"
        )
    # a shift is NOT expected to be invariant -- min-max is affine-equivariant
    # in scale but the window range moves with an offset only if the offset is
    # constant, which it is; so this one IS invariant too. Assert it rather
    # than assuming it.
    shifted = ta.normalize(close + 1000, length=14)
    both = ~(base.isna() | shifted.isna())
    assert (base[both] - shifted[both]).abs().max() < 1e-9


def test_normalize_returns_nan_on_a_flat_window():
    """0.5 was tried and removed on measurement, not taste."""
    flat = Series([5.0] * 50)
    out = ta.normalize(flat, length=14)
    assert out.notna().sum() == 0, (
        "a flat window has no position within its range -- emitting 0.5 plants "
        "a synthetic reading at the centre of the feature's distribution"
    )


def test_the_flat_fraction_that_killed_the_0_5_midpoint():
    """The measurement behind the choice, pinned so it cannot be reverted on
    taste: on a tick-rounded walk, 0.5 would have been fabricated on 17.7% of
    settled bars."""
    rng = np.random.default_rng(4)
    close = Series(np.round(100 + np.cumsum(rng.normal(0, 0.02, 2000)), 1))
    window = close.rolling(14, min_periods=14)
    flat = (window.max() - window.min()) == 0
    settled = window.min().notna()
    fraction = float((flat & settled).sum()) / float(settled.sum())
    assert fraction == pytest.approx(0.1772, abs=0.002), (
        f"flat fraction moved to {fraction:.4f}"
    )


def test_normalize_is_causal_with_a_mutant():
    """Real module clean; a whole-series (leaking) mutant caught."""
    import importlib.util

    close = frame()["close"]
    cut = 250

    full = ta.normalize(close, length=14)
    prefix = ta.normalize(close.iloc[:cut], length=14)
    both = ~(full.iloc[:cut].isna() | prefix.isna())
    assert both.sum() > 100
    assert (full.iloc[:cut][both] - prefix[both]).abs().max() == 0.0

    spec = importlib.util.find_spec("pandas_ta.statistics.normalize")
    source = open(spec.origin, encoding="utf8").read()
    # The leak must stay Series-shaped: substituting bare scalars
    # (`close.min()`) makes the module raise AttributeError on `.where`, which
    # is a crash, not a demonstration that the leak is detectable. An expanding
    # window that has been handed the whole series is the honest mutant -- it
    # is what a careless "just use the full history" edit actually looks like.
    mutated = source.replace(
        "    lowest, highest = window.min(), window.max()",
        "    lowest, highest = (close * 0 + close.min(),"
        " close * 0 + close.max())")
    assert mutated != source, "the mutation did not apply -- the test is blind"

    namespace = {}
    exec(compile(mutated, "<mutant>", "exec"), namespace)
    m_full = namespace["normalize"](close, length=14)
    m_prefix = namespace["normalize"](close.iloc[:cut], length=14)
    both = ~(m_full.iloc[:cut].isna() | m_prefix.isna())
    assert (m_full.iloc[:cut][both] - m_prefix[both]).abs().max() > 1e-9, (
        "the whole-series mutant was NOT caught, so this cannot certify causality"
    )


# -------------------------------------------------------------- covariance

def test_covariance_matches_pandas_and_names_its_ddof():
    df = frame()
    out = ta.covariance(df["close"], df["volume"], length=30)
    assert out.name == "COV_30_1"
    expected = df["close"].rolling(30, min_periods=30).cov(df["volume"], ddof=1)
    assert (out - expected).abs().max() == 0.0
    assert ta.covariance(df["close"], df["volume"], length=30, ddof=0).name \
        == "COV_30_0"


def test_covariance_inner_joins_a_mismatched_index():
    """Misaligned inputs must not silently produce a plausible number."""
    df = frame()
    other = df["volume"].iloc[5:].copy()
    out = ta.covariance(df["close"], other, length=30)
    assert out is not None
    assert out.index.equals(df.index.intersection(other.index))
    assert out.notna().sum() > 0


def test_covariance_of_a_series_with_itself_is_its_variance():
    df = frame()
    cov = ta.covariance(df["close"], df["close"], length=30)
    var = df["close"].rolling(30, min_periods=30).var(ddof=1)
    assert (cov - var).abs().max() < 1e-9


# ------------------------------------------------------------------- pivot

def test_pivot_emits_eleven_distance_columns_and_no_price_levels():
    df = frame()
    out = ta.pivot(df["high"], df["low"], df["close"])
    assert isinstance(out, DataFrame)
    assert out.shape[1] == 11
    assert all(c.startswith("PIVOT_") and c.endswith("_DIST_PCT")
               for c in out.columns), list(out.columns)
    for level in ("PP", "R1", "R2", "R3", "R4", "R5",
                  "S1", "S2", "S3", "S4", "S5"):
        assert f"PIVOT_{level}_DIST_PCT" in out.columns
    # no column may be a raw price: prices here are ~100, distances are ~0
    assert out.abs().max().max() < 1.0, (
        "a column with price-sized magnitude means levels leaked out raw"
    )


def test_pivot_is_scale_free():
    """Gate D. This is the whole reason `pivot` exists next to `pivot_point_levels`."""
    df = frame()
    base = ta.pivot(df["high"], df["low"], df["close"])
    for factor in (8, 64):
        scaled = ta.pivot(df["high"] * factor, df["low"] * factor,
                          df["close"] * factor)
        both = ~(base.isna() | scaled.isna())
        diff = (base[both] - scaled[both]).abs().max().max()
        assert diff == 0.0, (
            f"not scale-free at x{factor}: {diff} -- Gate D requires "
            f"bit-identical, and it measures 0.0 today"
        )


def test_pivot_is_not_a_restatement_of_pivot_point_levels():
    """The levels are PX and dead as features; these are distances and are not."""
    from pandas_ta.utils._pine import pivot_point_levels

    df = frame()
    levels = pivot_point_levels(df["high"], df["low"], df["close"])
    dist = ta.pivot(df["high"], df["low"], df["close"])
    assert levels.abs().max().max() > 10, "levels really are price-sized"
    assert dist.abs().max().max() < 1.0, "distances really are not"
    # and the relation is exactly the documented one
    both = ~(levels["PP"].isna() | dist["PIVOT_PP_DIST_PCT"].isna())
    expected = (df["close"] - levels["PP"]) / df["close"]
    assert (dist["PIVOT_PP_DIST_PCT"][both]
            - expected[both]).abs().max() < 1e-15


def test_pivot_fires_on_real_shaped_data():
    """Gate C: reachability, with the count stated."""
    df = frame()
    out = ta.pivot(df["high"], df["low"], df["close"])
    settled = out.dropna()
    assert settled.shape[0] == 369, (
        f"expected 369 settled rows on the 400-bar fixture, got "
        f"{settled.shape[0]}"
    )
    for column in out.columns:
        fires = out[column].notna().sum()
        assert 0 < fires < out.shape[0], f"{column} never fires"
        assert out[column].nunique() > 1, (
            f"{column} is CONSTANT -- `notna()` alone cannot see that, which "
            f"is what the old message wrongly claimed to check"
        )


def test_pivot_raises_on_a_non_datetime_index_rather_than_guessing():
    df = frame().reset_index(drop=True)
    with pytest.raises(Exception):
        ta.pivot(df["high"], df["low"], df["close"])


# ---------------------------------------------------------------- wiring

@pytest.mark.parametrize("name,category", [
    ("rolling_sum", "statistics"),
    ("normalize", "statistics"),
    ("covariance", "statistics"),
    ("pivot", "trend"),
])
def test_all_five_wiring_touch_points(name, category):
    df = frame()
    assert hasattr(ta, name), f"{name} missing at module level"
    assert name in ta.Category[category], f"{name} missing from Category"
    assert hasattr(df.ta, name), f"df.ta.{name} missing"


def test_the_corrupted_neighbours_are_intact():
    """Wiring `rolling_sum`/`pivot` once concatenated them onto their
    neighbours (`"zscore" "rolling_sum"` -> `zscorerolling_sum`) because a
    comma was missing. Both names silently vanished from `Category`."""
    assert "zscore" in ta.Category["statistics"]
    assert "zigzag_fib" in ta.Category["trend"]
    joined = [n for names in ta.Category.values() for n in names]
    assert "zscorerolling_sum" not in joined
    assert "zigzag_fibpivot" not in joined



def test_covariance_requires_other_and_refuses_a_duplicated_index():
    df = frame()
    with pytest.raises(ValueError, match="required"):
        ta.covariance(df["close"], length=30)

    dup = df["close"].copy()
    dup.index = dup.index[:200].repeat(2)
    other = dup.iloc[:-3]
    with pytest.raises(ValueError, match="duplicated index"):
        ta.covariance(dup, other, length=30)


def test_covariance_returns_none_when_the_join_is_too_short():
    df = frame()
    other = df["volume"].iloc[-5:]
    assert ta.covariance(df["close"], other, length=30) is None


def test_the_default_sweep_does_not_emit_price_against_share_count():
    """`df.ta.strategy("statistics")` used to emit COV of price vs volume --
    magnitude ~2.8e5, unusable, from a function whose docstring says it is not
    a feature. The accessor now defaults both sides to returns."""
    df = frame()
    out = df.ta.covariance(length=30)
    assert out is not None
    assert out.abs().max() < 1.0, (
        f"the default covariance is still price-scaled: {out.abs().max()}"
    )


def test_normalize_rejects_a_degenerate_length():
    with pytest.raises(ValueError, match="length must be"):
        ta.normalize(frame()["close"], length=1)


def test_pivot_is_causal_with_a_mutant():
    """The claim `pivot.py` makes, actually pinned — by PERTURBING THE FUTURE.

    An earlier docstring cited `tests/test_pivot.py`, a file that does not
    exist, for a mutant nobody had written. Writing it turned up something
    worth recording: neither prefix truncation NOR an endpoint rescan can
    certify this function. Levels publish only at anchors, so a one-bar
    look-ahead inside a period never surfaces before the next anchor, and both
    mutants below score 0.0 under either method. `CLAUDE.md` already warns that
    "prefix truncation alone proves nothing"; for anchor-sparse output it
    proves even less.

    What does work is perturbing every bar from J onward and asserting nothing
    before J moves. Measured: the real module leaks 0.0, a back-dated write
    leaks 50.0 (to float noise) — the exact size of the injected shift.
    """
    import importlib.util

    n = 200
    rng = np.random.default_rng(5)
    close = 100 + np.cumsum(rng.normal(0, 1, n))
    idx = date_range("2024-01-01", periods=n, freq="D")
    high = Series(close + abs(rng.normal(0, 1, n)), index=idx)
    low = Series(close - abs(rng.normal(0, 1, n)), index=idx)
    close = Series(close, index=idx)
    # a dense anchor: the default monthly one publishes so rarely that a leak
    # has nowhere to show itself inside a test-sized frame
    anchor = Series((np.arange(n) % 20) == 0, index=idx)
    J = 120

    def leak(fn):
        base = fn(high, low, close, anchor=anchor)
        shifted = fn(high + 50 * (np.arange(n) >= J),
                     low + 50 * (np.arange(n) >= J),
                     close + 50 * (np.arange(n) >= J), anchor=anchor)
        a, b = base.iloc[:J], shifted.iloc[:J]
        mask = ~(a.isna() | b.isna())
        assert mask.to_numpy().sum() > 300, "nothing settled to compare"
        return float((a[mask] - b[mask]).abs().max().max())

    from pandas_ta.utils._pine import pivot_point_levels

    assert leak(pivot_point_levels) == 0.0, "the real module leaks the future"

    spec = importlib.util.find_spec("pandas_ta.utils._pine")
    source = open(spec.origin, encoding="utf8").read()
    mutated = source.replace(
        "                out[name][i] = levels[name]",
        "                out[name][max(i - 25, 0)] = levels[name]")
    assert mutated != source, "the mutation did not apply -- the test is blind"

    namespace = {}
    exec(compile(mutated, "<mutant>", "exec"), namespace)
    assert leak(namespace["pivot_point_levels"]) == pytest.approx(50.0, abs=1e-9), (
        "the back-dated mutant was NOT caught, so this cannot certify causality"
    )

    # and `pivot` itself is a pure elementwise transform of those levels, so it
    # inherits the property -- asserted, not assumed
    df = frame()
    cut = 250
    full = ta.pivot(df["high"], df["low"], df["close"])
    prefix = ta.pivot(df["high"].iloc[:cut], df["low"].iloc[:cut],
                      df["close"].iloc[:cut])
    both = ~(full.iloc[:cut].isna() | prefix.isna())
    assert (full.iloc[:cut][both] - prefix[both]).abs().max().max() == 0.0
