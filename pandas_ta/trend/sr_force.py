# -*- coding: utf-8 -*-
import math

import numpy as np
from pandas import DataFrame, Series

from pandas_ta.utils import get_offset, verify_series


def _confirm_strict_pivots(series, left, right, is_high):
    """Causal pivot confirmation matching Pine's `ta.pivothigh`/
    `ta.pivotlow`: a bar at position i confirms (becomes visible at
    j=i+right) iff it is the STRICT, UNIQUE extreme of the window
    [i-left, i+right]. Duplicated from `liquidity_sweep.py`'s (and
    `rejection_blocks.py`'s / `equal_highs_lows.py`'s / `sphinx_unicorn.py`'s)
    identical helper rather than imported, matching this package's
    convention of self-contained indicator files."""
    window = left + right + 1
    n = len(series)
    vals = series.to_numpy(dtype=float)
    out = np.full(n, np.nan)
    for j in range(window - 1, n):
        i = j - right
        w = vals[j - window + 1: j + 1]
        if np.isnan(vals[i]):
            continue
        extreme = np.nanmax(w) if is_high else np.nanmin(w)
        if vals[i] != extreme:
            continue
        rest = np.delete(w, i - (j - window + 1))
        if np.any(rest == extreme):
            continue
        out[j] = vals[i]
    return out


class _Level:
    __slots__ = ("price", "score")

    def __init__(self, price, score):
        self.price = price
        self.score = score


def _validated_int(value, default, name, positive=True):
    """None -> default (a normal, documented default, not bad input).
    Anything else must be a genuine, finite, integral value, or raise.
    Duplicated verbatim from `rejection_blocks.py`'s helper of the same
    name (that file's own docstring explains why: `liquidity_sweep.py`'s
    original `_positive_int` did a bare `int(value)`, which lets
    `int(float('nan'))` raise ValueError only by luck and lets
    `int(3.7)` silently truncate rather than reject a non-integral
    float -- this version checks NaN/inf/non-integral explicitly before
    ever calling `int()`, so every rejection path is the same
    ValueError, not a mix of ValueError/OverflowError/silent truncation).
    `positive=False` allows 0 (used for `debounce_bars`, where 0
    legitimately means "no debounce, count every touch")."""
    if value is None:
        return default
    if isinstance(value, bool):
        raise ValueError(f"{name} must be a{'n' if not positive else ' positive'} int, got bool {value!r}")
    if isinstance(value, float):
        if value != value:  # NaN != NaN
            raise ValueError(f"{name} must be a finite int, got NaN")
        if math.isinf(value):
            raise ValueError(f"{name} must be a finite int, got inf")
        if not value.is_integer():
            raise ValueError(f"{name} must be an integral value, got non-integral float {value}")
    try:
        value = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{name} must be a{'n' if not positive else ' positive'} int, got {value!r}")
    if positive and value <= 0:
        raise ValueError(f"{name} must be a positive int, got {value}")
    if not positive and value < 0:
        raise ValueError(f"{name} must be a non-negative int, got {value}")
    return value


def _validated_float(value, default, name, nonneg=True):
    """Same nan/inf discipline as `_validated_int`, float variant.
    Duplicated verbatim from `rejection_blocks.py`."""
    if value is None:
        return default
    if isinstance(value, bool):
        raise ValueError(f"{name} must be a non-negative float, got bool {value!r}")
    try:
        value = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{name} must be a non-negative float, got {value!r}")
    if value != value:
        raise ValueError(f"{name} must be finite, got NaN")
    if abs(value) == float("inf"):
        raise ValueError(f"{name} must be finite, got inf")
    if nonneg and value < 0:
        raise ValueError(f"{name} must be >= 0, got {value}")
    return value


def _retest_score(high_v, low_v, close_v, t, price, retest_lookback, touch_tol_pct, debounce_bars):
    """Port of the source's `calculateResistanceBehavior`/
    `calculateSupportBehavior` -- the two functions are BYTE-IDENTICAL in
    the source (only their names differ; neither ever reads its own
    `swingIdx` parameter), so this is one shared implementation used for
    both sides, matching that fact rather than duplicating it into two
    near-identical functions.

    Scans `i = 1..retest_lookback` bars back from `t` -- the CONFIRMING
    bar (the bar on which the pivot's strict-unique-extreme window
    closes and the level enters the pool), NOT the pivot bar itself
    (`t - swing_len`). This is a faithful reproduction of a source quirk,
    not a design choice of this port: `calculateResistanceBehavior(price,
    swingIdx)` never references `swingIdx` in its body -- `high[i]`/
    `low[i]`/`close[i]` are Pine history-referencing operators relative
    to whatever bar the function executes on, which is the bar making the
    `array.push(...)` call (i.e. `bar_index`, the confirming bar), not
    `swingIdx`. Since `swing_len` (the source's `autoBars`, 3-10) is
    always < `retest_lookback` (50 by default), the pivot bar itself
    always falls inside this scan window regardless.

    A second faithful-not-fixed quirk: `cnt` is capped to 5 (`if cnt > 5:
    cnt := 5`) AFTER `weightScore` has already accumulated every
    debounced touch found (which can exceed 5 over a 50-bar window with
    only a 2-bar debounce -- up to ~25 are possible), but BEFORE
    `avgWeight = weightScore / cnt` divides by the now-capped count. So a
    level with, say, 8 real touches has its `weightScore` sum (~8 terms)
    divided by 5, not 8 -- `avgWeight` (and therefore `finalScore`) is
    systematically inflated versus a genuine 5-touch level. Reproduced
    exactly: `cnt_raw` (uncapped, used only for the final int the
    function's caller-visible touch count) vs `cnt` (capped, used for
    both the division and the `countFactor` step function) are kept as
    two separate values below, mirroring the source's own two-stage
    `cnt`/`avgWeight` computation order. NOTE: `final_score = cnt *
    avg_weight * count_factor` is algebraically just `weight_score *
    count_factor` -- the capped `cnt` in `avg_weight`'s denominator
    cancels against the `cnt` multiplied back in for `final_score`. Kept
    as the three-factor form below (not simplified) because that is the
    literal shape of the source's own `finalScore = cnt * avgWeight *
    countFactor` line -- a port mirrors the source's arithmetic, not an
    algebraically-reduced equivalent of it.

    Touch-scan NaN guard: only `high`/`low` are checked for NaN before a
    bar is skipped (`if np.isnan(h) or np.isnan(l): continue`), matching
    the source's own guard (`not na(high[i]) and not na(low[i])` --
    `close[i]` is NOT part of that guard). A NaN `close` is NOT special-
    cased here; it simply fails its own `lower <= c <= upper` comparison
    (a NaN comparison is always False in both Pine and Python, not an
    error), exactly like the source: a bar with a valid high/low but a
    NaN close can still register a touch via its high or low. An earlier
    version of this port guarded on all three of high/low/close, which
    silently dropped touches the source would have counted, shifting
    `last_touch_bar` (and therefore every later touch's debounce
    decision) for the rest of the scan -- Fletcher-caught, fixed here.

    `time_weight = 1.0 - (i / retest_lookback) * 0.5`: `i` and
    `retest_lookback` are both Python `int`, so `i / retest_lookback` is
    genuine float (true) division here regardless. The source's own
    `timeWeight = 1.0 - (i / 50) * 0.5` (both `i` and `50` are Pine
    `int`) is ALSO genuine float division, not integer-truncating --
    checked directly against TradingView's Pine v6 migration guide,
    which states int/int division with a non-evenly-divisible result
    always yields a fractional value in v6 (this is a v5-only behavior,
    removed in v6), and this source is `//@version=6` (line 1 of
    `1BcGW1Og.pine`). Recorded here since this exact question was raised
    and independently verified during this port's own review.
    """
    upper = price * (1.0 + touch_tol_pct)
    lower = price * (1.0 - touch_tol_pct)
    cnt_raw = 0
    weight_score = 0.0
    last_touch_bar = 0
    for i in range(1, retest_lookback + 1):
        j = t - i
        if j < 0:
            continue  # matches Pine's `not na(high[i])` guard at the start of history
        h, l, c = high_v[j], low_v[j], close_v[j]
        if np.isnan(h) or np.isnan(l):
            continue  # matches Pine's `not na(high[i]) and not na(low[i])` guard
            # exactly -- close is deliberately NOT part of this guard, see the
            # "Touch-scan NaN guard" paragraph above.
        touched = (lower <= h <= upper) or (lower <= l <= upper) or (lower <= c <= upper)
        if touched and (i - last_touch_bar) >= debounce_bars:
            cnt_raw += 1
            last_touch_bar = i
            time_weight = 1.0 - (i / retest_lookback) * 0.5
            weight_score += time_weight

    cnt = min(cnt_raw, 5)
    avg_weight = (weight_score / cnt) if cnt > 0 else 0.0

    if cnt >= 5:
        count_factor = 1.5
    elif cnt >= 3:
        count_factor = 1.0
    elif cnt >= 2:
        count_factor = 0.6
    else:
        count_factor = 0.3

    final_score = cnt * avg_weight * count_factor
    if final_score > 5.0:
        final_score = 5.0
    return final_score


def sr_force(high, low, close, swing_len=None, retest_lookback=None, touch_tol_pct=None,
             debounce_bars=None, max_levels=None, offset=None, **kwargs):
    """Indicator: S/R Force Matrix (SRF) -- level re-test strength"""
    swing_len = _validated_int(swing_len, 5, "swing_len")
    retest_lookback = _validated_int(retest_lookback, 50, "retest_lookback")
    touch_tol_pct = _validated_float(touch_tol_pct, 0.003, "touch_tol_pct")
    debounce_bars = _validated_int(debounce_bars, 2, "debounce_bars", positive=False)
    max_levels = _validated_int(max_levels, 20, "max_levels")

    min_len = 2 * swing_len + 1
    high = verify_series(high, min_len)
    low = verify_series(low, min_len)
    close = verify_series(close, min_len)
    offset = get_offset(offset)

    if high is None or low is None or close is None: return

    n = len(close)
    high_v = high.to_numpy(dtype=float)
    low_v = low.to_numpy(dtype=float)
    close_v = close.to_numpy(dtype=float)

    ph = _confirm_strict_pivots(high, swing_len, swing_len, is_high=True)  # confirmed swing highs -> resistance candidates
    pl = _confirm_strict_pivots(low, swing_len, swing_len, is_high=False)  # confirmed swing lows  -> support candidates

    score_res = np.full(n, np.nan)
    score_sup = np.full(n, np.nan)
    dist_res = np.full(n, np.nan)
    dist_sup = np.full(n, np.nan)

    res_levels = []  # resistance pool, from confirmed swing HIGHS -- FIFO-capped at max_levels
    sup_levels = []  # support pool,    from confirmed swing LOWS  -- FIFO-capped at max_levels

    for t in range(n):
        # --- level creation: a level's retest score is computed ONCE, at
        # confirmation, scanning the retest_lookback bars leading up to
        # (and including) this same confirming bar -- matches the
        # source's script order (the `array.push` call happens
        # immediately after `calculateResistanceBehavior`/
        # `calculateSupportBehavior` return, both on the confirming
        # bar). The source never re-scores a level after it enters the
        # pool. ---
        if not np.isnan(ph[t]):
            score = _retest_score(high_v, low_v, close_v, t, ph[t], retest_lookback, touch_tol_pct, debounce_bars)
            res_levels.append(_Level(ph[t], score))
            if len(res_levels) > max_levels:
                res_levels.pop(0)  # FIFO cap, mirrors the source's `array.remove(..., 0)` on overflow
        if not np.isnan(pl[t]):
            score = _retest_score(high_v, low_v, close_v, t, pl[t], retest_lookback, touch_tol_pct, debounce_bars)
            sup_levels.append(_Level(pl[t], score))
            if len(sup_levels) > max_levels:
                sup_levels.pop(0)

        # --- nearest-active-level lookup, side-constrained -- the
        # source itself never asks "what is the nearest level," only
        # tracks all of them for display (Fletcher-MAJOR lesson from
        # `liquidity_sweep.py`: an unconstrained nearest-by-absolute-
        # distance argmin can pick a level on the WRONG side of price,
        # e.g. a resistance level price has since traded through,
        # reporting a negative "distance to resistance". A level here
        # never leaves the pool except via the FIFO cap (no
        # sweep/break/reclaim lifecycle, unlike liquidity_sweep.py/
        # rejection_blocks.py), so a stale wrong-side level can persist
        # in the pool indefinitely -- constraining the candidate set to
        # the correct side of price before the argmin is REQUIRED here,
        # not just a nice-to-have.
        #
        # Fletcher MAJOR (this port's own round 1): the filters use
        # >=/<= (a level AT close price qualifies), not strict >/<,
        # clamped to a non-negative distance (`max(..., 0.0)`) --
        # matching `rejection_blocks.py`'s post-Fletcher-round-1 pattern
        # (the "tap" moment there). An earlier version of this port used
        # strict inequality, which meant Close landing EXACTLY on a
        # heavily re-tested level -- the single most informative bar --
        # reported NaN on both SCORE and DIST instead of the obvious
        # answer: you are AT that level right now, distance 0. ---
        c = close_v[t]
        res_cands = [lv for lv in res_levels if lv.price >= c]
        if res_cands:
            nearest = min(res_cands, key=lambda lv: lv.price - c)
            dist_res[t] = max(nearest.price - c, 0.0) / c * 100
            score_res[t] = nearest.score
        sup_cands = [lv for lv in sup_levels if lv.price <= c]
        if sup_cands:
            nearest = min(sup_cands, key=lambda lv: c - lv.price)
            dist_sup[t] = max(c - nearest.price, 0.0) / c * 100
            score_sup[t] = nearest.score

    score_res = Series(score_res, index=close.index)
    score_sup = Series(score_sup, index=close.index)
    dist_res = Series(dist_res, index=close.index)
    dist_sup = Series(dist_sup, index=close.index)

    if offset != 0:
        score_res = score_res.shift(offset)
        score_sup = score_sup.shift(offset)
        dist_res = dist_res.shift(offset)
        dist_sup = dist_sup.shift(offset)

    if "fillna" in kwargs:
        for s in (score_res, score_sup, dist_res, dist_sup):
            s.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        for s in (score_res, score_sup, dist_res, dist_sup):
            s.fillna(method=kwargs["fill_method"], inplace=True)

    _props = f"_{swing_len}"
    score_res.name = f"SRF_SCORE_RES{_props}"
    score_sup.name = f"SRF_SCORE_SUP{_props}"
    dist_res.name = f"SRF_DIST_RES{_props}"
    dist_sup.name = f"SRF_DIST_SUP{_props}"

    df = DataFrame({
        score_res.name: score_res,
        score_sup.name: score_sup,
        dist_res.name: dist_res,
        dist_sup.name: dist_sup,
    })
    df.name = f"SRF{_props}"
    df.category = "trend"

    return df


sr_force.__doc__ = \
"""S/R Force Matrix (SRF) -- level re-test strength

Confirmed swing pivots become resting S/R levels -- resistance above from
swing highs, support below from swing lows -- held in a bounded, per-side
FIFO pool (`max_levels`, no other eviction: unlike this fork's other
level-pool ports (`liquidity_sweep`, `rejection_blocks`), the source
never removes a level on a break or a sweep, only on FIFO overflow). Each
level's "re-test strength" score is computed ONCE, at confirmation: a
50-bar (default) backward scan counts how many times price touched
within a tight tolerance band around the level's price (a 2-bar debounce
prevents one touch from being counted many times), weights each counted
touch by recency, and combines count + average recency-weight + a
touch-count step function into a single 0..5 score.

Source: TradingView community indicator "ATK/DEF Support Resistance SR
Force Matrix" by ATTDEFS, https://www.tradingview.com/script/1BcGW1Og/
(ported into AwakenAnalytics/Backtesting TVPTA-6, 2026-08-11; MPL-2.0 per
TradingView's open-source publication convention). Replaces the source's
`calculateResistanceBehavior`/`calculateSupportBehavior` (the two
functions are byte-identical in the source save for their names -- this
port implements them once, as `_retest_score`) and the per-side
push/FIFO-cap level-pool maintenance (`array.push`/`array.remove(...,
0)` on `resistancePrices`/`supportPrices` and their parallel arrays)
that stores each level's score. NOT ported: `calcHistoricalPower` (a
SEPARATE per-level metric -- ATR-normalized price shock x volume
multiple x recency weight -- out of scope for this port, see
`datastore/source/pine_candidates_families.csv`'s `1BcGW1Og` row and its
functional-subset sibling `kPQxBN1q`), the auto-timeframe multiplier
(`getTimeFrameMultiplier`, only ever feeds `calcHistoricalPower`), candle
pressure (module 5), the liquidity-flow table block (module 11, volume-
ratio-vs-VWAP status text), and all label/table drawing.

⚠ `swing_len` is a FIXED parameter here, not the source's adaptive
`autoBars` (`round(ATR(14) / SMA(TrueRange, 50) * 5)`, clamped to
[3, 10], recomputed every bar and fed as BOTH the left and right window
to `ta.pivothigh`/`ta.pivotlow`). Each individual pivot under the
source's scheme DOES have a well-defined confirmation lag -- its own
bar's `autoBars` value, known at that bar -- so "no single confirmation
lag exists" is not the honest reason for fixing it; the honest reason is
portability/simplicity: no sibling port in this fork's `trend/` package
reproduces a bar-varying pivot window (`ta.pivothigh`/`ta.pivotlow` with
a per-bar-changing left/right argument has no established translation
pattern here yet), and a single fixed `swing_len` keeps this port
consistent with `_confirm_strict_pivots`'s existing fixed-window
contract, shared verbatim with `liquidity_sweep.py`/`rejection_blocks.py`.
`swing_len=5` (this port's default) is the value `autoBars` converges to
when ATR(14) roughly equals the 50-bar mean True Range (a common regime,
not an edge case) -- a reasonable representative constant, not a
derivation of the source's exact per-bar behavior. Pass `swing_len`
explicitly to match a specific market's typical `autoBars` value if that
matters downstream.

⚠ The retest-score scan window is anchored to the CONFIRMING bar, not
the pivot bar -- see `_retest_score`'s docstring for the full account of
why (the source's `swingIdx` parameter is never read in
`calculateResistanceBehavior`/`calculateSupportBehavior`'s body). This
is a faithful reproduction of what the source actually computes, not a
simplification this port introduces.

⚠ `avgWeight`'s denominator uses the CAPPED touch count (max 5) while
its numerator (`weightScore`) sums EVERY debounced touch found (which
can exceed 5) -- see `_retest_score`'s docstring. A level with more than
5 real touches has its score systematically inflated versus a genuine
5-touch level. Reproduced exactly; not corrected, per this port's
mandate to translate the math as computed.

⚠ `SRF_DIST_RES`/`SRF_DIST_SUP`/the "nearest level" framing for
`SRF_SCORE_RES`/`SRF_SCORE_SUP` are this port's own addition, in the
`dist_to_res_level`/`LSH_DIST_*`/`RB_DIST_*` tradition (the source only
ever draws ALL qualifying levels as labels, filtered by the separate,
not-ported `calcHistoricalPower` >= `powerThreshold`; it never asks "how
far to the nearest level" or "what is ITS score"). "Nearest" is
side-constrained (a resistance level's price must be AT OR ABOVE Close,
a support level's price AT OR BELOW) before the argmin, same discipline
as `liquidity_sweep.py`'s Fletcher-MAJOR fix and `rejection_blocks.py`'s
zone-edge version of it -- REQUIRED here (not just good practice)
because a level in this indicator's pool never resolves on a break, only
on FIFO eviction, so a stale wrong-side level can sit in the pool
indefinitely, unlike the sweep/break-then-reclaim lifecycles that
structurally bound `liquidity_sweep`'s/`rejection_blocks`'s wrong-side
exposure. The boundary uses `>=`/`<=`, not strict `>`/`<`, with the
reported distance clamped to `max(..., 0.0)` -- Fletcher MAJOR (this
port's own round 1): an earlier strict-inequality version reported NaN
on BOTH `SCORE` and `DIST` the moment Close landed EXACTLY on a level's
price (the single most informative bar -- price sitting exactly on a
heavily re-tested level) instead of the obvious answer, 0 -- the same
class of gap `rejection_blocks.py`'s own Fletcher round 1 fixed for its
zone edges (see that module's docstring for the mirror account).
Regression test: `tests/test_sr_force.py::
test_dist_and_score_report_zero_not_nan_when_close_equals_level_price`
(+ support-side mirror) assert `DIST == 0.0` and `SCORE` equal to that
exact level's own score, not NaN, at the exact equality boundary.
`SRF_DIST_RES`/`SRF_DIST_SUP` are >= 0 whenever populated, by
construction; `SRF_SCORE_RES`/`SRF_SCORE_SUP` are NaN exactly when their
paired `DIST` column is NaN (no level on the correct side of price, per
the `>=`/`<=` rule above), and in [0, 5] whenever populated (the
source's own `finalScore` cap).

Calculation:
    Default Inputs:
        swing_len=5, retest_lookback=50, touch_tol_pct=0.003,
        debounce_bars=2, max_levels=20
    Confirmed pivot high/low via strict-unique-extreme rule (`ta.pivothigh`/
        `ta.pivotlow` semantics, see `_confirm_strict_pivots`) -- a swing at
        bar i confirms at bar i + swing_len.
    On confirmation at bar t, for pivot price P:
        upper = P * (1 + touch_tol_pct); lower = P * (1 - touch_tol_pct)
        for i = 1..retest_lookback (bars back from t, the CONFIRMING bar):
            touched = high[t-i] in [lower,upper] or low[t-i] in [lower,upper]
                or close[t-i] in [lower,upper]
            if touched and (i - last_touch_bar) >= debounce_bars:
                cnt_raw += 1; last_touch_bar = i
                weight_score += 1.0 - (i / retest_lookback) * 0.5
        cnt = min(cnt_raw, 5)
        avg_weight = weight_score / cnt if cnt > 0 else 0
        count_factor = 1.5 if cnt>=5 else 1.0 if cnt>=3 else 0.6 if cnt>=2 else 0.3
        score = min(cnt * avg_weight * count_factor, 5.0)
        level (price=P, score=score) pushed onto that side's pool; if pool
        size > max_levels, the OLDEST level is dropped (FIFO).
    SRF_DIST_RES = max(nearest active resistance level's price - Close, 0.0)
        / Close * 100, restricted to resistance levels with price >= Close
        (NaN if none qualify -- 0.0, not NaN, when Close sits exactly on the
        nearest qualifying level's price); SRF_SCORE_RES = that nearest
        level's score (NaN exactly when SRF_DIST_RES is NaN).
    SRF_DIST_SUP / SRF_SCORE_SUP: mirror on the support side (price <= Close).

Args:
    high (pd.Series): Series of 'high's
    low (pd.Series): Series of 'low's
    close (pd.Series): Series of 'close's
    swing_len (int): Bars either side required for a pivot. Must be a
        positive int if given. Default: 5
    retest_lookback (int): Bars scanned backward from the confirming bar
        when scoring a level's re-test strength. Must be a positive int
        if given. Default: 50
    touch_tol_pct (float): Half-width of the touch tolerance band, as a
        fraction of the level price (e.g. 0.003 = +-0.3%). Must be >= 0
        if given. Default: 0.003
    debounce_bars (int): Minimum bar gap between two counted touches.
        Must be a non-negative int if given (0 disables debouncing --
        every touching bar counts). Default: 2
    max_levels (int): Max active levels tracked PER SIDE. Must be a
        positive int if given. Default: 20
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Raises:
    ValueError: `swing_len`/`retest_lookback`/`max_levels` given and not
        a positive, finite, integral value; `debounce_bars` given and
        not a non-negative, finite, integral value; `touch_tol_pct`
        given and not a finite, non-negative value (NaN/+-inf/negative
        all raise for all of these; non-integral floats like 3.7 raise
        for the int-typed params rather than silently truncating).
        `None` (the actual default sentinel) still means "use the
        default," not an error.

Returns:
    pd.DataFrame: SRF_SCORE_RES, SRF_SCORE_SUP, SRF_DIST_RES, SRF_DIST_SUP.
"""
