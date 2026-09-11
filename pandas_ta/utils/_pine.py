# -*- coding: utf-8 -*-
# r"""  <- the docstring is RAW: it quotes a grep whose `` and `\.` are not
# valid Python escapes. Harmless while the module is imported from a cached
# .pyc, but `tests/test_pinebi_1e_utilities.py::test_pivot_is_causal_with_a_mutant`
# exec()s this source fresh to build its mutant, and that emitted a
# DeprecationWarning on every run.
r"""PINEBI-1a: Pine Script's rolling primitives, transliterated.

These are NOT indicators and are deliberately absent from `Category`: they are
the vocabulary the Pine corpus is written in. `ta.highest` or `ta.lowest` appear
in **345 of the 2,211** scripts in `docs/pine/` (15.6%; `ta.highest` in 332,
`ta.lowest` in 306 -- the union, not the sum), so a port that lacks them has to
paraphrase every source it touches. Reproduce with::

    grep -rlE "\bta\.(highest|lowest)\b" docs/pine/ | wc -l

**Pine-exact, lag documented** (owner decision, 2026-09-07). Where Pine's
semantics differ from the obvious pandas one-liner, Pine wins and the difference
is stated in the docstring:

* windows are INCLUSIVE of the current bar, so `highest(src, 3)` at bar `i`
  covers `i-2 .. i`;
* `barssince` and `valuewhen` return `NaN` (Pine's `na`) before the condition
  has ever been true, rather than 0 or a back-fill;
* `pivothigh`/`pivotlow` return the pivot's PRICE on the bar that CONFIRMS it,
  `right` bars after the pivot itself, and `NaN` everywhere else. That lag is
  the causality cost of the primitive: at bar `i` you learn about a pivot at
  `i - right`. Nothing here reads a bar later than the one it writes.

The `*bars` variants return non-positive offsets, as Pine does: `0` when the
extreme is the current bar, `-2` when it is two bars back. ⚠ On a plateau they
report the NEAREST extreme (offset closest to 0), which is what Pine's backward
walk with strict improvement produces. That tie-break is this port's reading of
the backward walk and is pinned by `test_bars_offsets_break_ties_toward_the_
nearest_bar`; it was NOT confirmed against a live TradingView chart.

**NaN policy is not uniform, and the differences are deliberate:**

| behaviour | functions |
|---|---|
| propagate NaN | `highest` `lowest` `highestbars` `lowestbars` `correlation` `percentrank` and both percentiles -- a window containing NaN yields NaN |
| NaN is FALSE | every condition-shaped argument -- `barssince`, `valuewhen`, `highest_since`, `lowest_since` and `pivot_point_levels`'s `anchor` -- Pine's `na` condition never fires. This row is not hand-maintained: `test_the_na_false_row_names_every_condition_argument` discovers the callers of `_as_condition` from the source and fails if one is missing from it. |
| NaN absorbed as 0 | `cum` only, and that one is this port's choice rather than a verified Pine behaviour (see its docstring) |
| unverified against a live chart | FOUR: the `*bars` tie-break, `cum`'s na handling, `pivothigh`/`pivotlow`'s two-sided strictness, and `alltime_max`/`alltime_min`'s na handling (the row below) -- each marked ⚠ at its own definition. The previous version of this row said three and the row under it added a fourth. |
| NaN emitted, then ignored | `alltime_max` `alltime_min` -- `cummax`/`cummin` blank the gap bar and resume as if it were not there, so `[1, na, 3, 2, 5]` gives `[1, na, 3, 3, 5]`. Pine's behaviour on `na` inside `ta.max` is **unverified**; this is the port's. Pinned by `test_all_time_extremes_on_a_gap`. |

Sources: the Pine v6 reference for the core intrinsics; `highest_since` /
`lowest_since` follow `TradingView/ta` (MPL-2.0, (c) TradingView), whose source
is on disk at `docs/pine/RA2vGpkA-ta.pine`.
"""
import builtins

import numpy as np
from pandas import DataFrame, Series

from pandas_ta.utils._core import verify_series

# The controlled vocabulary, stated once. `from ._pine import *` would otherwise
# also re-export `np`, `DataFrame` and `Series` into the package namespace.
__all__ = [
    "highest", "lowest", "highestbars", "lowestbars", "cum", "barssince",
    "valuewhen", "correlation", "percentrank", "percentile_nearest_rank",
    "percentile_linear_interpolation", "pivothigh", "pivotlow",
    "highest_since", "lowest_since", "pivot_point_levels",
    "alltime_max", "alltime_min",
]


def _as_series(x, name=None):
    return x if isinstance(x, Series) else Series(x, name=name)


def _length(length, minimum=1, default=None):
    """Pine raises on a non-positive length; coercing one to 1 hides a typo.

    The docstring above promised that and the body then called `int()`, which
    truncates: `highest(src, 2.7)` returned a 2-bar window under the name
    `HIGHEST_2`. A rejected typo is loud; a truncated one is a wrong feature
    column with a plausible name, which is the harder bug of the two.
    """
    if length is None:
        return default if default is not None else minimum
    try:
        as_int = int(length)
    except (TypeError, ValueError):
        raise TypeError(f"length must be an integer, got {length!r}")
    if as_int != length:
        raise ValueError(
            f"length must be a whole number, got {length!r} -- `int()` would "
            f"have truncated it to {as_int}"
        )
    if as_int < minimum:
        raise ValueError(f"length must be >= {minimum}, got {as_int}")
    return as_int


def _as_condition(x):
    """Pine's `na` condition is FALSE, not true.

    `Series.astype(bool)` maps NaN to True, which would fire every
    condition on its own warm-up bars -- and a condition built on any
    rolling source (`sma(close, 20) > close`) is NaN for its first N bars,
    so that is the normal case, not a corner.
    """
    # NOT `.fillna(False)`: on an object-dtype condition that emits pandas 2.3's
    # "Downcasting object dtype arrays on .fillna" FutureWarning -- an error
    # under `-W error`, a hard failure in pandas 3 -- and `.infer_objects()`
    # afterwards cannot retract a warning already raised. Mask first instead.
    s = _as_series(x)
    values = np.where(s.isna().to_numpy(), False, s.to_numpy())
    return Series(values.astype(bool), index=s.index)


def highest(source, length=None):
    """Pine `ta.highest`: highest value of the last `length` bars, inclusive.

    Returns NaN until `length` bars exist, matching Pine's `na` warm-up.
    """
    source = verify_series(_as_series(source))
    length = _length(length)
    out = source.rolling(length, min_periods=length).max()
    out.name = f"HIGHEST_{length}"
    return out


def lowest(source, length=None):
    """Pine `ta.lowest`: lowest value of the last `length` bars, inclusive."""
    source = verify_series(_as_series(source))
    length = _length(length)
    out = source.rolling(length, min_periods=length).min()
    out.name = f"LOWEST_{length}"
    return out


def highestbars(source, length=None):
    """Pine `ta.highestbars`: offset to the highest bar, as a non-positive int.

    `0` means the current bar is the highest of the window; `-2` means two bars
    back. Pine returns the offset, not the distance, which is why the sign is
    kept.
    """
    source = verify_series(_as_series(source))
    length = _length(length)
    # Pine walks BACK from the current bar keeping strict improvements, so on a
    # plateau it reports the NEAREST extreme (offset closest to 0). `np.argmax`
    # returns the oldest, which inverts the tie-break -- and ties are the common
    # case, not a corner: 21.17% of real BIST bars close exactly at an extreme.
    out = source.rolling(length, min_periods=length).apply(
        lambda w: -float(np.argmax(w[::-1])) + 0.0, raw=True)
    out.name = f"HIGHESTBARS_{length}"
    return out


def lowestbars(source, length=None):
    """Pine `ta.lowestbars`: offset to the lowest bar, as a non-positive int."""
    source = verify_series(_as_series(source))
    length = _length(length)
    out = source.rolling(length, min_periods=length).apply(
        lambda w: -float(np.argmin(w[::-1])) + 0.0, raw=True)
    out.name = f"LOWESTBARS_{length}"
    return out


def cum(source):
    """Pine `ta.cum`: running total from the first bar.

    ⚠ **na policy, unverified against TradingView.** This port treats `na` as 0
    so a single gap does not poison the whole tail. Pine's documented behaviour
    on `na` inside `ta.cum` was NOT confirmed against a live chart, so this is
    THIS PORT's choice, not a transliteration -- unlike `highest_since`, which
    quotes its source. See the na-policy table in the module docstring.
    """
    source = verify_series(_as_series(source))
    out = source.fillna(0).cumsum()
    out.name = "CUM"
    return out


def alltime_max(source):
    """Pine `ta.max`: the ALL-TIME high of a series, from the first bar.

    ⚠ **Named `alltime_max`, not `max`.** Pine's name would shadow the builtin
    across the whole package: `_pine`'s `__all__` feeds `pandas_ta.utils`, which
    `core.py` star-imports, so `max(...)` in any module -- and in any user file
    doing `from pandas_ta import *` -- would silently become this function and
    return a Series where a scalar was meant. The output column has always been
    `ALLTIME_MAX`; the callable now matches it.

    Not a rolling window -- `ta.max(high)` is the running maximum over every bar
    so far, which is why it takes no length. The corpus uses it exactly that way:
    `docs/pine/c1pPR2kI.pine:137-139` reads `// All Time High and Low` /
    `ATH = ta.max(HIGH_)` / `ATL = ta.min(LOW_)`.

    """
    source = verify_series(_as_series(source))
    out = source.cummax()
    out.name = "ALLTIME_MAX"
    return out


def alltime_min(source):
    """Pine `ta.min`: the ALL-TIME low of a series, from the first bar.

    Named `alltime_min` for the reason given in `alltime_max`.
    """
    source = verify_series(_as_series(source))
    out = source.cummin()
    out.name = "ALLTIME_MIN"
    return out


def barssince(condition):
    """Pine `ta.barssince`: bars elapsed since `condition` was last true.

    `0` on a bar where the condition is true. **NaN, not 0, before the first
    true** -- Pine returns `na` there, and collapsing that to 0 would claim the
    condition just fired.
    """
    cond = _as_condition(condition).to_numpy()
    out = np.full(len(cond), np.nan)
    last = -1
    for i, flag in enumerate(cond):
        if flag:
            last = i
        if last >= 0:
            out[i] = i - last
    result = Series(out, index=_as_series(condition).index, name="BARSSINCE")
    return result


def valuewhen(condition, source, occurrence=0):
    """Pine `ta.valuewhen`: `source` when `condition` was true, N occurrences back.

    `occurrence=0` is the most recent true bar (including the current one).
    NaN until that many occurrences have happened.
    """
    cond = _as_condition(condition).to_numpy()
    src = verify_series(_as_series(source)).to_numpy(dtype=float)
    if occurrence is not None and int(occurrence) < 0:
        raise ValueError("occurrence must be >= 0")
    occurrence = int(occurrence) if occurrence else 0

    out = np.full(len(cond), np.nan)
    hits = []
    for i, flag in enumerate(cond):
        if flag:
            hits.append(i)
        if len(hits) > occurrence:
            out[i] = src[hits[-1 - occurrence]]
    return Series(out, index=_as_series(condition).index,
                  name=f"VALUEWHEN_{occurrence}")


def correlation(source_a, source_b, length=None):
    """Pine `ta.correlation`: rolling Pearson correlation over `length` bars.

    ⚠ Deviation: `length=1` RAISES here, where Pine returns `na` -- a
    single-bar correlation has no meaning and a typo'd length should not return
    a column of NaN that looks like a warm-up.
    """
    a = verify_series(_as_series(source_a))
    b = verify_series(_as_series(source_b))
    length = _length(length, minimum=2)
    out = a.rolling(length, min_periods=length).corr(b)
    out.name = f"CORRELATION_{length}"
    return out


def percentrank(source, length=None):
    """Pine `ta.percentrank`: % of the PREVIOUS `length` values at or below now.

    Pine's window is the `length` bars BEFORE the current one; the current value
    is the thing being ranked, not part of the population. Ranking a value
    against a window containing itself would floor the result at `100/length`.
    """
    source = verify_series(_as_series(source))
    length = _length(length)
    values = source.to_numpy(dtype=float)
    out = np.full(len(values), np.nan)
    for i in range(length, len(values)):
        window = values[i - length:i]
        if np.isnan(values[i]) or np.isnan(window).any():
            continue
        out[i] = 100.0 * np.count_nonzero(window <= values[i]) / length
    return Series(out, index=source.index, name=f"PERCENTRANK_{length}")


def percentile_nearest_rank(source, length=None, percentage=50.0):
    """Pine `ta.percentile_nearest_rank`: nearest-rank percentile, inclusive window.

    Nearest rank picks an OBSERVED value -- `ceil(P/100 * N)`-th smallest -- so
    the result is always a value that actually occurred, unlike the interpolated
    form below.
    """
    source = verify_series(_as_series(source))
    length = _length(length)
    percentage = float(percentage)
    if not 0.0 <= percentage <= 100.0:
        raise ValueError(f"percentage must be in [0, 100], got {percentage}")

    def _rank(window):
        ordered = np.sort(window)
        idx = int(np.ceil(percentage / 100.0 * len(ordered))) - 1
        return float(ordered[builtins.max(0, builtins.min(idx, len(ordered) - 1))])

    out = source.rolling(length, min_periods=length).apply(_rank, raw=True)
    out.name = f"PCTNR_{length}_{percentage:g}"
    return out


def percentile_linear_interpolation(source, length=None, percentage=50.0):
    """Pine `ta.percentile_linear_interpolation`: interpolated percentile.

    Interpolates between the two neighbouring ranks, so the result need not be a
    value that occurred.
    """
    source = verify_series(_as_series(source))
    length = _length(length)
    percentage = float(percentage)
    if not 0.0 <= percentage <= 100.0:
        raise ValueError(f"percentage must be in [0, 100], got {percentage}")
    out = source.rolling(length, min_periods=length).apply(
        lambda w: float(np.percentile(w, percentage, method="linear")), raw=True)
    out.name = f"PCTLI_{length}_{percentage:g}"
    return out


def pivothigh(source, left=None, right=None, high=None):
    """Pine `ta.pivothigh`: the pivot's PRICE on the bar that confirms it.

    A bar `p` is a pivot high when its value is strictly greater than the `left`
    bars before it and the `right` bars after it. Pine reports the pivot on bar
    `p + right` -- not on `p` -- and `na` on every other bar.

    ⚠ **Two-sided STRICTNESS is this port's reading, not a verified Pine
    behaviour** -- the same status as the `*bars` tie-break and `cum`'s na
    policy, and it matters on the same axis: 21.17% of real BIST bars close
    exactly at an extreme, so plateaus are the common case. A non-strict
    comparison would report a pivot on every bar of a flat top. Pinned by
    `test_pivots_are_strict_on_a_plateau` and by a `>`/`<` mutation test.

    ⚠ **That `right`-bar lag IS the causality cost.** The value is written at
    `p + right`, using only bars up to `p + right`, so it is causal; but a
    strategy reading it at bar `i` is learning about a pivot at `i - right`.
    Every port built on this primitive inherits the lag, and should say so.

    `ta.pivothigh(left, right)` (no source) defaults to `high`; pass either
    `source` positionally or `high=` for that form.
    """
    if source is None:
        source = high
    source = verify_series(_as_series(source))
    left = _length(left)
    right = _length(right)

    values = source.to_numpy(dtype=float)
    out = np.full(len(values), np.nan)
    for p in range(left, len(values) - right):
        window_l = values[p - left:p]
        window_r = values[p + 1:p + 1 + right]
        if np.isnan(values[p]) or np.isnan(window_l).any() or np.isnan(window_r).any():
            continue
        # STRICTLY greater on both sides: a plateau is not a pivot. Pinned by
        # `test_pivots_are_strict_on_a_plateau`, because a `>` -> `>=` mutation
        # is invisible on any fixture without ties.
        if (values[p] > window_l).all() and (values[p] > window_r).all():
            out[p + right] = values[p]
    return Series(out, index=source.index, name=f"PIVOTHIGH_{left}_{right}")


def pivotlow(source, left=None, right=None, low=None):
    """Pine `ta.pivotlow`: mirror of `pivothigh`, same `right`-bar lag."""
    if source is None:
        source = low
    source = verify_series(_as_series(source))
    left = _length(left)
    right = _length(right)

    values = source.to_numpy(dtype=float)
    out = np.full(len(values), np.nan)
    for p in range(left, len(values) - right):
        window_l = values[p - left:p]
        window_r = values[p + 1:p + 1 + right]
        if np.isnan(values[p]) or np.isnan(window_l).any() or np.isnan(window_r).any():
            continue
        # Strictly less on both sides -- see the note in `pivothigh`.
        if (values[p] < window_l).all() and (values[p] < window_r).all():
            out[p + right] = values[p]
    return Series(out, index=source.index, name=f"PIVOTLOW_{left}_{right}")


def highest_since(condition, source):
    """`TradingView/ta.highestSince`: running max since `condition` last fired.

    Transliterated from `docs/pine/RA2vGpkA-ta.pine:236-240` (MPL-2.0,
    (c) TradingView)::

        export highestSince(series bool cond, series float source = high) =>
            var float result = na
            if cond
                result := source
            result := math.max(nz(source, result), nz(result, source))

    ⚠ The `math.max` line runs UNCONDITIONALLY, so tracking starts at bar 0 and
    the series is never `na` after the first non-NaN source value -- it does NOT
    wait for the first true condition. A true condition RESETS the run to that
    bar's own value. An earlier version of this port returned NaN until the
    first true, which is the intuitive reading and not what the source does.
    """
    cond = _as_condition(condition).to_numpy()
    src = verify_series(_as_series(source)).to_numpy(dtype=float)
    out = np.full(len(cond), np.nan)
    running = np.nan
    for i, flag in enumerate(cond):
        if flag:
            running = src[i]
        # nz(source, result) / nz(result, source): whichever is defined wins,
        # so the first defined bar seeds the run regardless of `cond`.
        if np.isnan(running):
            running = src[i]
        elif not np.isnan(src[i]):
            running = builtins.max(running, src[i])
        out[i] = running
    return Series(out, index=_as_series(condition).index, name="HIGHEST_SINCE")


def lowest_since(condition, source):
    """`TradingView/ta.lowestSince`: running min since `condition` last fired.

    Same shape as `highest_since`, from `RA2vGpkA-ta.pine` -- tracking starts at
    bar 0, a true condition resets the run.
    """
    cond = _as_condition(condition).to_numpy()
    src = verify_series(_as_series(source)).to_numpy(dtype=float)
    out = np.full(len(cond), np.nan)
    running = np.nan
    for i, flag in enumerate(cond):
        if flag:
            running = src[i]
        if np.isnan(running):
            running = src[i]
        elif not np.isnan(src[i]):
            running = builtins.min(running, src[i])
        out[i] = running
    return Series(out, index=_as_series(condition).index, name="LOWEST_SINCE")


def pivot_point_levels(high, low, close, anchor=None, kind="Traditional"):
    """Pine `ta.pivot_point_levels`, "Traditional": P and R1-R5 / S1-S5.

    Pine's signature is `ta.pivot_point_levels(type, anchor, developing)` and it
    returns an 11-element array: P, R1, S1, R2, S2, R3, S3, R4, S4, R5, S5. This
    returns the same eleven as named DataFrame columns, priced from the
    COMPLETED previous period.

    ⚠ Differences from the built-in, stated rather than hidden:
      * only `type="Traditional"` is implemented; the others (Fibonacci,
        Woodie, Classic, DM, Camarilla) raise instead of silently substituting;
      * `developing` is not implemented -- levels update once per period, at the
        anchor, never intrabar;
      * the arguments are `(high, low, close, anchor)` rather than Pine's
        `(type, anchor, developing)`, because this function is handed series
        instead of reading the chart.

    `anchor` is a boolean Series marking the first bar of each new period. The
    default anchors on a change of calendar month when the index is a
    DatetimeIndex, and raises otherwise rather than guessing.

    Levels for the period starting at an anchor bar use only bars strictly
    BEFORE that anchor, so nothing here reads forward.
    """
    if kind != "Traditional":
        raise ValueError(
            f"pivot_point_levels: only kind='Traditional' is implemented, got "
            f"{kind!r}. Pine also defines Fibonacci, Woodie, Classic, DM and "
            f"Camarilla; add one deliberately rather than substituting. "
            f"(Pine calls this parameter `type`; renamed to avoid shadowing "
            f"the builtin.)")

    high = verify_series(_as_series(high))
    low = verify_series(_as_series(low))
    close = verify_series(_as_series(close))

    if anchor is None:
        if not hasattr(high.index, "month"):
            raise ValueError(
                "pivot_point_levels needs an `anchor` boolean Series when the "
                "index is not a DatetimeIndex")
        month = Series(high.index.month, index=high.index)
        anchor = month != month.shift(1)
    anchor = _as_condition(anchor)

    names = ["PP", "R1", "S1", "R2", "S2", "R3", "S3", "R4", "S4", "R5", "S5"]
    out = {name: np.full(len(close), np.nan) for name in names}

    period_high = period_low = period_close = np.nan
    levels = None
    for i in range(len(close)):
        if anchor.iloc[i] and not np.isnan(period_high):
            pp = (period_high + period_low + period_close) / 3.0
            span = period_high - period_low
            up, down = pp - period_low, period_high - pp
            levels = {
                "PP": pp,
                "R1": 2 * pp - period_low,
                "S1": 2 * pp - period_high,
                "R2": pp + span,
                "S2": pp - span,
                "R3": period_high + 2 * up,
                "S3": period_low - 2 * down,
                "R4": period_high + 3 * up,
                "S4": period_low - 3 * down,
                "R5": period_high + 4 * up,
                "S5": period_low - 4 * down,
            }
        if anchor.iloc[i]:
            period_high, period_low, period_close = (
                high.iloc[i], low.iloc[i], close.iloc[i])
        else:
            period_high = np.nanmax([period_high, high.iloc[i]])
            period_low = np.nanmin([period_low, low.iloc[i]])
            period_close = close.iloc[i]
        if levels is not None:
            for name in names:
                out[name][i] = levels[name]

    frame = DataFrame(out, index=close.index)
    frame.name = "PIVOTPOINTS"
    return frame
