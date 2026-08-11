# -*- coding: utf-8 -*-
import math

import numpy as np
from pandas import DataFrame, Series

from pandas_ta.volatility.atr import atr
from pandas_ta.utils import get_offset, verify_series


def _confirm_strict_pivots(series, left, right, is_high):
    """Causal pivot confirmation matching Pine's `ta.pivothigh`/
    `ta.pivotlow`: a bar at position i confirms (becomes visible at
    j=i+right) iff it is the STRICT, UNIQUE extreme of the window
    [i-left, i+right]. Duplicated from `liquidity_sweep.py`'s (and
    `equal_highs_lows.py`'s / `sphinx_unicorn.py`'s) identical helper
    rather than imported, matching this package's convention of
    self-contained indicator files."""
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


class _Zone:
    __slots__ = ("top", "bot", "dir", "tapped")

    def __init__(self, top, bot, dir_, tapped=False):
        self.top = top
        self.bot = bot
        self.dir = dir_  # -1 = bearish RB (resistance, born at a swing high), 1 = bullish RB (support, born at a swing low)
        self.tapped = tapped


def _validated_int(value, default, name, positive=True):
    """None -> default (a normal, documented default, not bad input).
    Anything else must be a genuine, finite, integral value, or raise --
    fixes the gap this session's `liquidity_sweep` port shipped with
    (Fletcher round 1 there added ValueError-on-invalid-input, but its
    `_positive_int` still does a bare `int(value)`: `int(float('nan'))`
    raises ValueError by luck, but `int(float('inf'))` raises
    OverflowError -- a different exception type a caller catching
    ValueError would miss -- and `int(3.7)` silently truncates to 3
    rather than rejecting the non-integral float). This helper checks
    NaN/inf/non-integral explicitly before ever calling `int()`, so
    every rejection path raises the same `ValueError`."""
    if value is None:
        return default
    if isinstance(value, bool):
        raise ValueError(f"{name} must be a positive int, got bool {value!r}")
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
        raise ValueError(f"{name} must be a positive int, got {value!r}")
    if positive and value <= 0:
        raise ValueError(f"{name} must be a positive int, got {value}")
    return value


def _validated_float(value, default, name, nonneg=True):
    """Same nan/inf discipline as `_validated_int`, float variant. `value
    == value` is False for NaN (no `math.isnan` import needed twice) and
    `abs(value) != float('inf')` catches both signs of infinity."""
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


def rejection_blocks(open_, high, low, close, swing_len=None, min_wick_ratio=None,
                      min_wick_atr=None, atr_len=None, max_zones=None, offset=None,
                      **kwargs):
    """Indicator: Kale Rejection Blocks (RB)"""
    swing_len = _validated_int(swing_len, 3, "swing_len")
    min_wick_ratio = _validated_float(min_wick_ratio, 0.35, "min_wick_ratio")
    min_wick_atr = _validated_float(min_wick_atr, 0.30, "min_wick_atr")
    atr_len = _validated_int(atr_len, 14, "atr_len")
    max_zones = _validated_int(max_zones, 12, "max_zones")

    # atr_len is included in the length floor even though the per-bar
    # threshold check below tolerates NaN ATR gracefully (a NaN
    # comparison is always False, so an unwarmed ATR just blocks
    # qualification rather than crashing) -- `atr()` does its OWN
    # independent verify_series(atr_len) check and returns None (not a
    # NaN-filled Series) on a too-short frame, which would otherwise
    # crash `.to_numpy()` on that None even after this function's own
    # (smaller) min_len check had passed. Mirrors `liquidity_sweep.py`.
    min_len = max(2 * swing_len + 1, atr_len)
    open_ = verify_series(open_, min_len)
    high = verify_series(high, min_len)
    low = verify_series(low, min_len)
    close = verify_series(close, min_len)
    offset = get_offset(offset)

    if open_ is None or high is None or low is None or close is None: return

    n = len(close)
    open_v = open_.to_numpy(dtype=float)
    high_v = high.to_numpy(dtype=float)
    low_v = low.to_numpy(dtype=float)
    close_v = close.to_numpy(dtype=float)
    atr_v = atr(high, low, close, length=atr_len).to_numpy(dtype=float)

    ph = _confirm_strict_pivots(high, swing_len, swing_len, is_high=True)  # confirmed swing highs -> bearish RB candidates
    pl = _confirm_strict_pivots(low, swing_len, swing_len, is_high=False)  # confirmed swing lows  -> bullish RB candidates

    tap_bull = np.zeros(n, dtype=int)
    tap_bear = np.zeros(n, dtype=int)
    spent_bull = np.zeros(n, dtype=int)
    spent_bear = np.zeros(n, dtype=int)
    dist_res = np.full(n, np.nan)  # % distance to nearest ACTIVE bearish (resistance) zone strictly above close
    dist_sup = np.full(n, np.nan)  # % distance to nearest ACTIVE bullish (support) zone strictly below close

    zones = []  # single combined pool -- the source's `bxs` array holds BOTH
    # directions together and caps the TOTAL count at `keepN`/`max_zones`,
    # not per side. Kept as one list here to match that exactly (a
    # per-side-capped pool, as `liquidity_sweep.py` uses, would silently
    # change the eviction behavior whenever bull and bear candidates
    # compete for the same slot).

    def _new_zone(dir_, t):
        """Pine's `newRB(dir)`: the pivot candle is `swing_len` bars back
        from the confirming bar `t`. `wick`/`rng` reference ONLY the pivot
        bar's own OHLC; the ATR threshold reads `atr_v[t]` (today's ATR,
        NOT the pivot bar's ATR) -- this asymmetry is in the source
        (`atr = ta.atr(14)` evaluated at the current bar, compared against
        a wick measured `swing_len` bars in the past) and is reproduced
        here deliberately, not a bug."""
        pivot_bar = t - swing_len
        o, c, h, l = open_v[pivot_bar], close_v[pivot_bar], high_v[pivot_bar], low_v[pivot_bar]
        if np.isnan(o) or np.isnan(c) or np.isnan(h) or np.isnan(l):
            return None
        body_top = max(o, c)
        body_bot = min(o, c)
        rng = max(h - l, 1e-9)  # syminfo.mintick has no headless-OHLCV equivalent; an
        # epsilon floor prevents a zero-range bar from making `rng` zero and
        # dividing-by-zero-shaped comparisons degenerate, same role the
        # source's `math.max(h - l, syminfo.mintick)` plays.
        if dir_ == -1:
            wick = h - body_top
            top, bot = h, body_top
        else:
            wick = body_bot - l
            top, bot = body_bot, l
        atr_now = atr_v[t]
        if np.isnan(atr_now):
            return None
        ok = (wick >= min_wick_ratio * rng) and (wick >= min_wick_atr * atr_now)
        if not ok:
            return None
        return _Zone(top, bot, dir_)

    for t in range(n):
        # --- 1. new-zone detection: bearish (from a confirmed swing HIGH)
        # then bullish (from a confirmed swing LOW), matching the source's
        # `if not na(ph)` block before its `if not na(pl)` block, both
        # BEFORE this same bar's lifecycle loop below. ---
        if not np.isnan(ph[t]):
            z = _new_zone(-1, t)
            if z is not None:
                zones.append(z)
                if len(zones) > max_zones:
                    zones.pop(0)  # FIFO cap on the COMBINED pool, mirrors `array.shift(bxs)`
        if not np.isnan(pl[t]):
            z = _new_zone(1, t)
            if z is not None:
                zones.append(z)
                if len(zones) > max_zones:
                    zones.pop(0)

        # --- 2. lifecycle: spent (mitigated, body closes through the far
        # edge) removes the zone; tapped (price re-enters the zone) sets a
        # sticky flag once. Checked against THIS bar's own high/low/close,
        # including a zone born on this very bar (matches the source: the
        # lifecycle `for` loop runs over `bxs` AFTER both addRB calls, in
        # the same script execution for bar `t`). Spent is checked before
        # tapped, and a spent zone never also reports tapped this bar --
        # exactly the source's `if spent: ... continue`. ---
        survivors = []
        for z in zones:
            if z.dir == -1:
                spent = close_v[t] > z.top
            else:
                spent = close_v[t] < z.bot
            if spent:
                if z.dir == -1:
                    spent_bear[t] = 1
                else:
                    spent_bull[t] = 1
                continue  # removed from the pool, matches `array.remove(bxs, i)`

            if z.dir == -1:
                in_zone = high_v[t] >= z.bot
            else:
                in_zone = low_v[t] <= z.top
            if in_zone and not z.tapped:
                z.tapped = True
                if z.dir == -1:
                    tap_bear[t] = 1
                else:
                    tap_bull[t] = 1
            survivors.append(z)
        zones = survivors

        # --- 3. distance to nearest ACTIVE zone on the correct side of
        # price -- constrained to zones price hasn't already moved fully
        # PAST (the far edge), same discipline as `liquidity_sweep.py`'s
        # Fletcher-MAJOR-fixed DIST_RES/DIST_SUP (an unconstrained
        # nearest-by-absolute-distance argmin could otherwise pick a zone
        # on the wrong side of price). "Active" includes a
        # tapped-but-not-yet-spent zone -- it is still tracked and still
        # resolvable, only a spent zone leaves the pool.
        #
        # Fletcher MINOR (this port's own round 1, distinct from
        # liquidity_sweep's MAJOR): the first version of this block
        # required the NEAR edge strictly ahead of price (`bot > c` /
        # `top < c`), so a zone price had already TAPPED INTO (price
        # inside [bot, top], the exact TAP moment RB_TAP_BEAR/BULL fires)
        # reported NaN instead of the geometrically obvious answer -- you
        # are AT that resistance/support right now, distance 0. Fixed by
        # widening the candidate filter to the FAR edge (`top >= c` /
        # `bot <= c` -- the spent check already guarantees an active
        # bearish zone always has `top >= c`/an active bullish zone always
        # has `bot <= c`, so this filter is a no-op safety net, not a
        # behavior change, for the "genuinely ahead" case) and clamping
        # the reported distance to >= 0 so a contained zone reports 0
        # rather than a negative value; the raw (unclamped) argmin key is
        # kept so a zone price is INSIDE always wins over a merely-nearby
        # zone price hasn't reached yet (a more negative raw `bot - c` /
        # `c - top` beats a smaller positive one, matching "you're already
        # there beats you're almost there").
        c = close_v[t]
        res_cands = [z for z in zones if z.dir == -1 and z.top >= c]
        if res_cands:
            nearest = min(res_cands, key=lambda z: z.bot - c)
            dist_res[t] = max(nearest.bot - c, 0.0) / c * 100
        sup_cands = [z for z in zones if z.dir == 1 and z.bot <= c]
        if sup_cands:
            nearest = min(sup_cands, key=lambda z: c - z.top)
            dist_sup[t] = max(c - nearest.top, 0.0) / c * 100

    tap_bull = Series(tap_bull, index=close.index)
    tap_bear = Series(tap_bear, index=close.index)
    spent_bull = Series(spent_bull, index=close.index)
    spent_bear = Series(spent_bear, index=close.index)
    dist_res = Series(dist_res, index=close.index)
    dist_sup = Series(dist_sup, index=close.index)

    if offset != 0:
        tap_bull = tap_bull.shift(offset)
        tap_bear = tap_bear.shift(offset)
        spent_bull = spent_bull.shift(offset)
        spent_bear = spent_bear.shift(offset)
        dist_res = dist_res.shift(offset)
        dist_sup = dist_sup.shift(offset)

    if "fillna" in kwargs:
        for s in (tap_bull, tap_bear, spent_bull, spent_bear, dist_res, dist_sup):
            s.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        for s in (tap_bull, tap_bear, spent_bull, spent_bear, dist_res, dist_sup):
            s.fillna(method=kwargs["fill_method"], inplace=True)

    _props = f"_{swing_len}"
    tap_bull.name = f"RB_TAP_BULL{_props}"
    tap_bear.name = f"RB_TAP_BEAR{_props}"
    spent_bull.name = f"RB_SPENT_BULL{_props}"
    spent_bear.name = f"RB_SPENT_BEAR{_props}"
    dist_res.name = f"RB_DIST_RES{_props}"
    dist_sup.name = f"RB_DIST_SUP{_props}"

    df = DataFrame({
        tap_bull.name: tap_bull,
        tap_bear.name: tap_bear,
        spent_bull.name: spent_bull,
        spent_bear.name: spent_bear,
        dist_res.name: dist_res,
        dist_sup.name: dist_sup,
    })
    df.name = f"RB{_props}"
    df.category = "trend"

    return df


rejection_blocks.__doc__ = \
"""Kale Rejection Blocks (RB)

At a confirmed swing HIGH, the pivot candle's upper-wick zone (body-top
to high) becomes a bearish "rejection block" -- a resistance zone price
returns to and gets rejected from again. At a confirmed swing LOW, the
lower-wick zone (body-bottom to low) becomes a bullish rejection block
(support). A candidate pivot candle only qualifies if its wick is large
relative to BOTH its own bar range and the current ATR. Each active zone
resolves through a two-stage lifecycle: TAPPED (a sticky flag, set once
price first re-enters the zone -- the TP/entry moment the source's author
uses this indicator for) and SPENT/mitigated (the zone is removed once a
later bar's body closes fully through the zone's far edge).

Source: TradingView community indicator "Kale Rejection Blocks - John
3:16" by lezama03, https://www.tradingview.com/script/
QjOFE86I-Kale-Rejection-Blocks-John-3-16/ (ported into AwakenAnalytics/
Backtesting TVPTA-6, 2026-08-11; MPL-2.0 per TradingView's open-source
publication convention). Replaces the source's `newRB()` (pivot-candle
wick qualification), `addRB()`'s array push/FIFO-cap logic (drawing calls
themselves dropped), and the "relevance lifecycle" `for` loop (the
`spent`/`inZone` boolean logic) -- i.e. every line of actual signal math
in the source. NOT ported: all `box`/`label`/`line`/`table` drawing, the
watermark table, `alertcondition`, and the optional ZigZag structure line
(`showZig`) -- that feature only ever draws a line between successive
confirmed pivots with no state or threshold of its own; it emits no
signal beyond the swing-pivot confirmation `ph`/`pl` already consumed
above, so there is no additional math to port.

⚠ Combined pool, not per-side: the source's `bxs` array holds BOTH bullish
and bearish zones together and caps the TOTAL count at `keepN`
(`max_zones` here), evicting the OLDEST zone (FIFO) regardless of
direction once the cap is exceeded. This is reproduced exactly -- a
per-direction cap (as `liquidity_sweep.py` uses for its BSL/SSL pools)
would silently change which zones survive whenever bull and bear
candidates compete for the same slot.

⚠ ATR/wick asymmetry is IN THE SOURCE, not a bug this port introduces:
`newRB()`'s `wick`/`rng` are measured on the PIVOT bar (`swing_len` bars
in the past), but the ATR threshold multiplies TODAY'S `ta.atr(14)`
(the confirming bar `t`, not the pivot bar `t - swing_len`). Reproduced
verbatim (`atr_v[t]` in `_new_zone`, called from bar `t`).

⚠ `barstate.isconfirmed`-equivalent: like this fork's other event-
detection ports (`ob`, `fvg`, `sphinx_unicorn`, `liquidity_sweep`), every
row of a historical OHLCV frame is treated as already-closed; the live
caller (`indicator_engine.py`) is responsible for not evaluating the
final, still-forming bar, per this project's `df.iloc[-3]` signal-bar law.

⚠ `DIST_RES`/`DIST_SUP` are this port's own addition, not a translation
of existing Pine math (the source only ever asks "did THIS zone get
tapped," never "how far to the nearest zone") -- added in the family's
`dist_to_res_level`/`LSH_DIST_RES`/`SPHINX_DIST_*` tradition for a
scale-free distance feature. "Nearest" is nearest-by-(possibly negative)
raw distance to the zone's NEAR (tap-triggering) edge -- `bot` for a
bearish/resistance zone, `top` for a bullish/support zone -- among zones
NOT YET fully passed (`z.top >= close` for DIST_RES, `z.bot <= close` for
DIST_SUP), with the reported distance clamped to >= 0. This is the same
side-discipline `liquidity_sweep.py`'s Fletcher-MAJOR fix established
(never let an unconstrained argmin pick a zone the wrong side of price),
shipped here from the start rather than needing a follow-up round --
but see the next paragraph for a related, DISTINCT hole this port's own
Fletcher round 1 found and fixed in the clamping itself.

⚠ Fletcher MINOR (round 1): the first version of this port's DIST
columns required the near edge STRICTLY ahead of price (`bot > close` /
`top < close`, no clamping), so a zone price had already TAPPED INTO
(price sitting inside `[bot, top]` -- precisely the moment `RB_TAP_BEAR`/
`RB_TAP_BULL` fires) reported NaN instead of the geometrically obvious
answer: you are AT that resistance/support right now, distance 0. This
is NOT the same failure mode as the Fletcher-MAJOR side-constraint bug
above -- it is a *within-side* boundary/containment gap, not a
wrong-side pick, and it is specific to this indicator's ZONE (not point)
levels: `SPENT` fires the moment `close` crosses the FAR edge, so an
active bearish zone provably always has `top >= close` and an active
bullish zone always has `bot <= close` (if it didn't, it would already
be spent and gone) -- meaning the "restricted to the correct side" test
alone can never exclude a genuinely wrong-side active zone here the way
it does for `liquidity_sweep.py`'s point levels; the real gap was purely
the missing 0-clamp for the contained case. Fixed by widening the
candidate filter to the far edge (a no-op for the "genuinely ahead" case,
given the invariant above) and reporting `max(nearest_edge_distance, 0)`.
Dedicated regression tests: `tests/test_rejection_blocks.py::
test_dist_res_zero_not_nan_while_price_inside_zone` (and its DIST_SUP
mirror) assert 0.0, not NaN, both strictly inside a zone and at the exact
near-edge boundary; `test_dist_res_prefers_zone_containing_price_over_
farther_zone` (and its mirror) assert a contained zone's distance-0
correctly outranks a merely-nearby zone's smaller-but-still-positive
distance.

"Active" includes a tapped-but-not-yet-spent zone (still tracked, still
resolvable); only a spent zone leaves the pool and stops contributing to
either DIST column.

Calculation:
    Default Inputs:
        swing_len=3, min_wick_ratio=0.35, min_wick_atr=0.30, atr_len=14,
        max_zones=12
    Confirmed pivot high/low via strict-unique-extreme rule (`ta.pivothigh`/
        `ta.pivotlow` semantics, see `_confirm_strict_pivots`) -- a swing at
        bar i confirms at bar i + swing_len.
    On confirmation at bar t, for the pivot bar p = t - swing_len:
        body_top = max(open[p], close[p]); body_bot = min(open[p], close[p])
        rng = max(high[p] - low[p], epsilon)
        bearish (from a swing high): wick = high[p] - body_top,
            zone = [body_top, high[p]]
        bullish (from a swing low):  wick = body_bot - low[p],
            zone = [low[p], body_bot]
        qualifies iff wick >= min_wick_ratio * rng
            AND wick >= min_wick_atr * ATR(atr_len)[t]  (today's ATR)
        qualifying zone pushed onto the COMBINED pool; if pool size >
            max_zones, the oldest zone (either direction) is dropped (FIFO).
    Each bar t, for every zone currently in the pool (including one born
        this bar):
            SPENT (mitigated): close[t] > zone.top (bearish) or
                close[t] < zone.bot (bullish) -- zone removed, no TAP fires
                this bar for it.
            TAPPED (sticky, fires once): high[t] >= zone.bot (bearish) or
                low[t] <= zone.top (bullish), and not already tapped.
    DIST_RES = max(nearest active bearish zone's `bot` - close, 0) / close
        * 100, among zones with `top >= close` (NaN only if the pool has
        no active bearish zone at all).
    DIST_SUP = max(close - nearest active bullish zone's `top`, 0) / close
        * 100, among zones with `bot <= close` (NaN only if the pool has
        no active bullish zone at all).
        Both are >= 0 whenever populated, by construction; 0 exactly
        while price sits inside the nearest zone (the TAP window).

Args:
    open_ (pd.Series): Series of 'open's
    high (pd.Series): Series of 'high's
    low (pd.Series): Series of 'low's
    close (pd.Series): Series of 'close's
    swing_len (int): Bars either side required for a pivot. Must be a
        positive int if given. Default: 3
    min_wick_ratio (float): Minimum wick size as a fraction of the pivot
        bar's own high-low range. Must be >= 0 if given. Default: 0.35
    min_wick_atr (float): Minimum wick size as a multiple of ATR(atr_len)
        measured at the CONFIRMING bar (not the pivot bar). Must be >= 0
        if given. Default: 0.30
    atr_len (int): ATR lookback for the wick-size filter. Must be a
        positive int if given. Default: 14
    max_zones (int): Max active zones tracked in the COMBINED (both
        directions) pool. Must be a positive int if given. Default: 12
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Raises:
    ValueError: any of `swing_len`/`atr_len`/`max_zones` given and not a
        positive, finite, integral value (NaN, +-inf, and non-integral
        floats like 3.7 all raise -- they do not silently truncate or
        fall back to the default); `min_wick_ratio`/`min_wick_atr` given
        and not a finite, non-negative value (NaN/+-inf/negative all
        raise). `None` (the actual default sentinel) still means "use the
        default," not an error.

Returns:
    pd.DataFrame: RB_TAP_BULL, RB_TAP_BEAR, RB_SPENT_BULL, RB_SPENT_BEAR,
        RB_DIST_RES, RB_DIST_SUP.
"""
