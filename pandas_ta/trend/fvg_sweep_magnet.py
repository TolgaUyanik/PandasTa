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
    `rejection_blocks.py`'s / `sr_force.py`'s / `sphinx_unicorn.py`'s /
    `equal_highs_lows.py`'s) identical helper rather than imported,
    matching this package's convention of self-contained indicator
    files."""
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
    __slots__ = ("top", "bot", "dir", "birth", "score", "live")

    def __init__(self, top, bot, dir_, birth):
        self.top = top
        self.bot = bot
        self.dir = dir_       # 1 = bullish FVG, -1 = bearish FVG
        self.birth = birth    # bar index the zone was created (confirming bar)
        self.score = None     # set on first MAINTAIN pass, same bar as birth
        self.live = True


def _validated_int(value, default, name, positive=True):
    """None -> default (a normal, documented default, not bad input).
    Anything else must be a genuine, finite, integral value, or raise.
    Duplicated verbatim from `sr_force.py`'s/`rejection_blocks.py`'s
    helper of the same name -- checks NaN/inf/non-integral explicitly
    before ever calling `int()`, so every rejection path raises the same
    ValueError (not a mix of ValueError/OverflowError/silent truncation,
    the shape `liquidity_sweep.py`'s original, now-superseded
    `_positive_int` had). `positive=False` allows 0 (used for
    `min_score`, where 0 legitimately means "no score floor -- every
    live, in-gap zone qualifies")."""
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
    Duplicated verbatim from `sr_force.py`/`rejection_blocks.py`."""
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


def _validated_bool(value, default, name):
    """None -> default. Must be an actual bool (or numpy bool_), not an
    int/str standing in for one -- same strict-typing discipline
    `_validated_int` already applies to `bool` (a distinct type from
    `int`, not silently accepted where an int is expected), applied here
    to the one param (`require_disp`) this port actually wants a plain
    boolean for. No prior TVPTA-6 port in this family has had a bool
    param to validate; this is this port's own addition to the shared
    `_validated_*` family, same nan/inf/type-strictness spirit."""
    if value is None:
        return default
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    raise ValueError(f"{name} must be a bool, got {type(value)!r}")


def _safe_div(a, b):
    """Port of the source's `f_safeDiv`: `b == 0.0 or na(b) ? 0.0 : a / b`.
    Returns 0.0 (not NaN) on a zero or NaN denominator -- literal
    translation, used only inside `_score` (the source's own scoring
    formula), never for this port's own `CE_DIST`/`CE_SCORE` additions
    (those propagate NaN on an invalid denominator instead, matching
    this family's `DIST`-column convention)."""
    if b == 0.0 or b != b:
        return 0.0
    return a / b


def _clamp(v, lo, hi):
    """Port of the source's `f_clamp`: `math.max(lo, math.min(hi, v))`."""
    return max(lo, min(hi, v))


def _score(gap_size, disp_body, age_bars, vol_ratio, atr_t):
    """Port of the source's `f_score(gapSize, dispBody, ageBars, volRatio)`
    (the global `atr` read inside it is this function's `atr_t`
    parameter). Returns an int in [0, 10].

    `math.round` in Pine v6 rounds ties up (checked against TradingView's
    own documentation, not assumed -- this port's own task explicitly
    flagged Pine-semantics assumptions as a past source of near-bad
    "fixes" elsewhere in this batch). Since `_clamp(..., 0.0, 10.0)`
    guarantees a non-negative input here, "round half up" and "round half
    away from zero" coincide, so `math.floor(x + 0.5)` is an exact,
    unambiguous translation regardless of which of the two the reference
    formally specifies."""
    gap_pts = _clamp(_safe_div(gap_size, atr_t) * 3.2, 0.0, 3.0)
    disp_pts = _clamp(_safe_div(disp_body, atr_t) * 2.0, 0.0, 3.0)
    age_pts = _clamp(3.0 - age_bars / 40.0, 0.0, 2.0)
    vol_pts = _clamp(vol_ratio * 1.2, 0.0, 2.0)
    total = _clamp(gap_pts + disp_pts + age_pts + vol_pts, 0.0, 10.0)
    return int(math.floor(total + 0.5))


def fvg_sweep_magnet(open_, high, low, close, volume, fvg_lookback=None, disp_atr_mult=None,
                      atr_len=None, min_gap_atr=None, require_disp=None, max_fvg_age=None,
                      pivot_len=None, liq_keep=None, sweep_wick_mult=None, sweep_confirm=None,
                      magnet_window=None, min_score=None, offset=None, **kwargs):
    """Indicator: FVG Sweep Magnet Engine (FSME)"""
    fvg_lookback = _validated_int(fvg_lookback, 10, "fvg_lookback")
    disp_atr_mult = _validated_float(disp_atr_mult, 1.25, "disp_atr_mult")
    atr_len = _validated_int(atr_len, 14, "atr_len")
    min_gap_atr = _validated_float(min_gap_atr, 0.25, "min_gap_atr")
    require_disp = _validated_bool(require_disp, True, "require_disp")
    max_fvg_age = _validated_int(max_fvg_age, 60, "max_fvg_age")
    pivot_len = _validated_int(pivot_len, 5, "pivot_len")
    liq_keep = _validated_int(liq_keep, 4, "liq_keep")
    sweep_wick_mult = _validated_float(sweep_wick_mult, 0.35, "sweep_wick_mult")
    sweep_confirm = _validated_int(sweep_confirm, 2, "sweep_confirm")
    magnet_window = _validated_int(magnet_window, 18, "magnet_window")
    min_score = _validated_int(min_score, 5, "min_score", positive=False)

    # atr_len is included in the length floor even though the per-bar gate
    # checks tolerate a NaN ATR gracefully (a NaN comparison is always
    # False, so an unwarmed ATR just blocks gap/sweep detection rather
    # than crashing) -- `atr()` does its OWN independent
    # verify_series(atr_len) check and returns None (not a NaN-filled
    # Series) on a too-short frame, which would otherwise crash
    # `.to_numpy()` on that None even after this function's own (smaller)
    # min_len check had passed. Mirrors `liquidity_sweep.py`/
    # `rejection_blocks.py`/`sr_force.py`.
    min_len = max(2 * pivot_len + 1, atr_len)
    open_ = verify_series(open_, min_len)
    high = verify_series(high, min_len)
    low = verify_series(low, min_len)
    close = verify_series(close, min_len)
    volume = verify_series(volume, min_len)
    offset = get_offset(offset)

    if open_ is None or high is None or low is None or close is None or volume is None:
        return

    n = len(close)
    open_v = open_.to_numpy(dtype=float)
    high_v = high.to_numpy(dtype=float)
    low_v = low.to_numpy(dtype=float)
    close_v = close.to_numpy(dtype=float)
    volume_v = volume.to_numpy(dtype=float)
    atr_v = atr(high, low, close, length=atr_len).to_numpy(dtype=float)
    # ta.sma(volume, 20) in the source -- a plain (non-recursive) rolling
    # mean, so hand-rolled here rather than routed through this fork's own
    # `sma()` (whose `verify_series` would return None, not a NaN-filled
    # Series, on a frame shorter than 20 bars -- a needless extra failure
    # mode for a one-line rolling mean; `atr()`'s recursive RMA above is
    # the one piece worth reusing the shared implementation for).
    vol_sma_v = volume.rolling(20, min_periods=20).mean().to_numpy(dtype=float)

    ph = _confirm_strict_pivots(high, pivot_len, pivot_len, is_high=True)  # confirmed swing highs -> BSL (bear-side) levels
    pl = _confirm_strict_pivots(low, pivot_len, pivot_len, is_high=False)  # confirmed swing lows  -> SSL (bull-side) levels

    mag_bull = np.zeros(n, dtype=int)
    mag_bear = np.zeros(n, dtype=int)
    ce_dist_bull = np.full(n, np.nan)
    ce_dist_bear = np.full(n, np.nan)
    ce_score_bull = np.full(n, np.nan)
    ce_score_bear = np.full(n, np.nan)

    bsl_pool = []  # pivot-high (BSL) prices, FIFO-capped at liq_keep -- swept by BEAR sweeps
    ssl_pool = []  # pivot-low  (SSL) prices, FIFO-capped at liq_keep -- swept by BULL sweeps
    zones = []     # SINGLE COMBINED pool for bull+bear FVGs, FIFO-capped at fvg_lookback --
    # matches the source's own `fvgBox`/`fvgTop`/... arrays, which are
    # shared by both directions and trimmed by `f_trimOldest` regardless
    # of a slot's `fvgLive` state (see module docstring's "combined pool,
    # dead zones linger" quirk).

    last_bull_sweep_bar = None
    last_bear_sweep_bar = None
    last_bull_sig_bar = None
    last_bear_sig_bar = None

    for t in range(n):
        atr_t = atr_v[t]
        atr_ok = not np.isnan(atr_t)
        bar_rng_t = high_v[t] - low_v[t]

        # --- 1. LIQUIDITY POOLS: new pivot(s) confirmed THIS bar enter the
        # pool before this same bar's sweep check -- matches the source's
        # script order (LIQUIDITY POOLS section runs before SWEEP
        # DETECTION). ---
        if not np.isnan(ph[t]):
            bsl_pool.append(ph[t])
            if len(bsl_pool) > liq_keep:
                bsl_pool.pop(0)
        if not np.isnan(pl[t]):
            ssl_pool.append(pl[t])
            if len(ssl_pool) > liq_keep:
                ssl_pool.pop(0)

        # --- 2. SWEEP DETECTION. Loop scans the WHOLE pool (oldest to
        # newest) without an early break, matching the source's `for`
        # loop -- only whether ANY level qualifies matters for the
        # boolean flags this port exposes (the source's own
        # `sweptBullLvl`/`sweptBearLvl`/`lastBull/BearSweepLvl` variables
        # are set but never read anywhere else in the script -- dead
        # state, not ported). ---
        bull_sweep = False
        bear_sweep = False
        if bar_rng_t > 0:
            wick_ok_high = (high_v[t] - max(open_v[t], close_v[t])) / bar_rng_t >= sweep_wick_mult
            wick_ok_low = (min(open_v[t], close_v[t]) - low_v[t]) / bar_rng_t >= sweep_wick_mult
        else:
            wick_ok_high = False
            wick_ok_low = False

        if len(ssl_pool) > 0 and wick_ok_low and atr_ok:
            for lvl in ssl_pool:
                if low_v[t] < lvl and close_v[t] > lvl and close_v[t] > open_v[t]:
                    bull_sweep = True
        if len(bsl_pool) > 0 and wick_ok_high and atr_ok:
            for lvl in bsl_pool:
                if high_v[t] > lvl and close_v[t] < lvl and close_v[t] < open_v[t]:
                    bear_sweep = True

        if bull_sweep:
            last_bull_sweep_bar = t
        if bear_sweep:
            last_bear_sweep_bar = t

        # --- 3. FVG STORAGE: displacement-qualified new gap creation.
        # Needs bars t-2 (the gap's far edge) and t-1 (the displacement/
        # middle candle) -- both automatically satisfied once t >= 2. ---
        if t >= 2 and atr_ok:
            bull_gap_raw = low_v[t] > high_v[t - 2]
            bear_gap_raw = high_v[t] < low_v[t - 2]
            mid_body = abs(close_v[t - 1] - open_v[t - 1])
            mid_bull = close_v[t - 1] > open_v[t - 1]
            mid_bear = close_v[t - 1] < open_v[t - 1]
            disp_ok_bull = (not require_disp) or (mid_bull and mid_body >= atr_t * disp_atr_mult)
            disp_ok_bear = (not require_disp) or (mid_bear and mid_body >= atr_t * disp_atr_mult)

            if bull_gap_raw:
                bull_gap_sz = low_v[t] - high_v[t - 2]
                if bull_gap_sz >= atr_t * min_gap_atr and disp_ok_bull:
                    zones.append(_Zone(low_v[t], high_v[t - 2], 1, t))
                    if len(zones) > fvg_lookback:
                        zones.pop(0)
            if bear_gap_raw:
                bear_gap_sz = low_v[t - 2] - high_v[t]
                if bear_gap_sz >= atr_t * min_gap_atr and disp_ok_bear:
                    zones.append(_Zone(low_v[t - 2], high_v[t], -1, t))
                    if len(zones) > fvg_lookback:
                        zones.pop(0)
            # bull_gap_raw and bear_gap_raw can never both hold (would
            # require high[t-2] < low[t] <= high[t] < low[t-2], impossible
            # given low <= high on every bar) -- at most one append/bar.

        # --- 4. MAINTAIN: every zone in the pool, INCLUDING one born this
        # very bar (it was already appended above, in step 3, which the
        # source's own FVG STORAGE section runs before MAINTAIN). A
        # brand-new zone can never be "filled" on its own creation bar
        # (Close >= Low[t] > High[t-2] = bot for a bull zone, by
        # bull_gap_raw's own definition; mirror for bear), so this is
        # purely a rescoring pass for it, not a same-bar kill. ---
        for z in zones:
            age = t - z.birth
            if z.live:
                filled = (close_v[t] < z.bot) if z.dir == 1 else (close_v[t] > z.top)
                expired = age > max_fvg_age
                if filled or expired:
                    z.live = False
            if z.live and atr_ok:
                gap_sz_now = z.top - z.bot
                vol_ratio_t = _safe_div(volume_v[t], vol_sma_v[t])
                # dispBody is passed as `atr_t` itself here (not the real
                # displacement body) -- a literal reproduction of the
                # source's own `f_score(gapSzNow, atr, float(age),
                # volRatio)` maintenance-pass call, see module docstring
                # "score quirk" for why the real displacement magnitude
                # never actually reaches any observable score.
                z.score = _score(gap_sz_now, atr_t, float(age), vol_ratio_t, atr_t)

        # --- 5. MAGNET SIGNALS + this port's own CE_DIST/CE_SCORE
        # addition, merged into one pass over the (post-MAINTAIN) live
        # zones -- both read the exact same `in_gap` test. ---
        bull_magnet = False
        bear_magnet = False
        best_bull_d, best_bull_s = None, None
        best_bear_d, best_bear_s = None, None

        bull_sweep_fresh = (last_bull_sweep_bar is not None
                             and sweep_confirm <= (t - last_bull_sweep_bar) <= magnet_window)
        bear_sweep_fresh = (last_bear_sweep_bar is not None
                             and sweep_confirm <= (t - last_bear_sweep_bar) <= magnet_window)

        if len(zones) > 0 and atr_ok:
            for z in zones:
                if not z.live:
                    continue
                # Source's own `inGap = low <= top and high >= bot` --
                # already INCLUSIVE in the .pine source itself (`<=`/`>=`,
                # not `<`/`>`), reused verbatim as the candidacy filter
                # for this port's own CE_DIST/CE_SCORE addition too (see
                # module docstring).
                in_gap = low_v[t] <= z.top and high_v[t] >= z.bot
                if not in_gap:
                    continue
                mid = (z.top + z.bot) * 0.5

                if z.dir == 1:
                    if bull_sweep_fresh and z.score >= min_score and close_v[t] > open_v[t]:
                        bull_magnet = True
                    if atr_t != 0.0:
                        d = abs(close_v[t] - mid) / atr_t
                        if best_bull_d is None or d < best_bull_d:
                            best_bull_d, best_bull_s = d, z.score
                else:
                    if bear_sweep_fresh and z.score >= min_score and close_v[t] < open_v[t]:
                        bear_magnet = True
                    if atr_t != 0.0:
                        d = abs(close_v[t] - mid) / atr_t
                        if best_bear_d is None or d < best_bear_d:
                            best_bear_d, best_bear_s = d, z.score

        bull_sig = bull_magnet and (last_bull_sig_bar is None or (t - last_bull_sig_bar) > magnet_window)
        bear_sig = bear_magnet and (last_bear_sig_bar is None or (t - last_bear_sig_bar) > magnet_window)
        if bull_sig:
            last_bull_sig_bar = t
        if bear_sig:
            last_bear_sig_bar = t

        mag_bull[t] = int(bull_sig)
        mag_bear[t] = int(bear_sig)
        if best_bull_d is not None:
            ce_dist_bull[t] = best_bull_d
            ce_score_bull[t] = float(best_bull_s)
        if best_bear_d is not None:
            ce_dist_bear[t] = best_bear_d
            ce_score_bear[t] = float(best_bear_s)

    mag_bull = Series(mag_bull, index=close.index)
    mag_bear = Series(mag_bear, index=close.index)
    ce_dist_bull = Series(ce_dist_bull, index=close.index)
    ce_dist_bear = Series(ce_dist_bear, index=close.index)
    ce_score_bull = Series(ce_score_bull, index=close.index)
    ce_score_bear = Series(ce_score_bear, index=close.index)

    if offset != 0:
        mag_bull = mag_bull.shift(offset)
        mag_bear = mag_bear.shift(offset)
        ce_dist_bull = ce_dist_bull.shift(offset)
        ce_dist_bear = ce_dist_bear.shift(offset)
        ce_score_bull = ce_score_bull.shift(offset)
        ce_score_bear = ce_score_bear.shift(offset)

    if "fillna" in kwargs:
        for s in (mag_bull, mag_bear, ce_dist_bull, ce_dist_bear, ce_score_bull, ce_score_bear):
            s.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        for s in (mag_bull, mag_bear, ce_dist_bull, ce_dist_bear, ce_score_bull, ce_score_bear):
            s.fillna(method=kwargs["fill_method"], inplace=True)

    _props = f"_{pivot_len}"
    mag_bull.name = f"FSME_MAG_BULL{_props}"
    mag_bear.name = f"FSME_MAG_BEAR{_props}"
    ce_dist_bull.name = f"FSME_CE_DIST_BULL{_props}"
    ce_dist_bear.name = f"FSME_CE_DIST_BEAR{_props}"
    ce_score_bull.name = f"FSME_CE_SCORE_BULL{_props}"
    ce_score_bear.name = f"FSME_CE_SCORE_BEAR{_props}"

    df = DataFrame({
        mag_bull.name: mag_bull,
        mag_bear.name: mag_bear,
        ce_dist_bull.name: ce_dist_bull,
        ce_dist_bear.name: ce_dist_bear,
        ce_score_bull.name: ce_score_bull,
        ce_score_bear.name: ce_score_bear,
    })
    df.name = f"FSME{_props}"
    df.category = "trend"

    return df


fvg_sweep_magnet.__doc__ = \
"""FVG Sweep Magnet Engine (FSME)

Two engines coupled into one signal: (1) displacement-validated Fair
Value Gaps (3-bar imbalances that also clear a minimum ATR-scaled size
AND, by default, a displacement-candle body filter) become scored,
tracked zones; (2) confirmed swing-pivot liquidity levels (buy-side above
swing highs, sell-side below swing lows), when swept by a wick-and-close
reversal, ARM a short window during which a live, sufficiently-scored,
currently-overlapping FVG zone firing in the sweep's direction becomes a
"magnet" signal.

Source: TradingView community indicator "FVG Sweep Magnet Engine
[PhenLabs]" by PhenLabs, https://www.tradingview.com/script/
1FFYDfSr-FVG-Sweep-Magnet-Engine-PhenLabs/ (ported into AwakenAnalytics/
Backtesting TVPTA-6, 2026-08-11; MPL-2.0 per TradingView's open-source
publication convention). Replaces the source's FVG-qualification gate
(`bullGapRaw`/`bearGapRaw` + the `sizeOk*`/`dispOk*` filters), its
liquidity-pool push/FIFO-cap maintenance (`f_pushLiq`), its sweep-
detection loops (the `bullSweep`/`bearSweep` `for` blocks), its FVG
lifecycle (`f_addFvg`/the MAINTAIN loop's fill/expire/rescore logic,
`f_score`), and its magnet-signal gate + cooldown (the MAGNET SIGNALS
section's `for` loop and `bullSig`/`bearSig` debounce) -- i.e. every line
of actual signal math in the source. NOT ported: all `box`/`line`/
`label`/`table` drawing (`f_armNeon`, the dashboard, `plotshape`,
`bgcolor`), the target-price extension (`targetExtAtr`/`bullTgt`/
`bearTgt`/the "TP" label -- a numeric-but-purely-visual output this port
does not surface), and the `alertcondition` wrappers (each fires on a
boolean this port already computes, or an OR of two).

⚠ Differentiated scope vs. this fork's two sibling FVG/liquidity ports
(explicit, since this session's own survey flagged the overlap risk):
`fvg.py` detects the SAME 3-bar gap pattern with NO displacement filter,
no ATR-scaled minimum size, and no scoring -- this port's underlying gap
gate is a strict SUBSET of `fvg.py`'s (every FSME zone would also be an
`fvg.py` FVG_BULL/BEAR event, not vice versa), and that qualifying-gap
event is deliberately NOT re-exposed here as its own `FSME_GAP_BULL/BEAR`
column -- doing so would read as a near-duplicate of `fvg.py`'s own
`FVG_BULL`/`FVG_BEAR` despite the different (stricter) gate underneath,
inviting exactly the confusion this port's own task was told to avoid.
The qualifying gate is ported (it is what makes a zone eligible to become
a magnet at all) but only surfaces through `MAG_*`/`CE_*`, never as a
standalone flag. `liquidity_sweep.py` (LSH) independently ports THIS
source's own sweep-of-pivot-level building block (wick sweep +
break-then-reclaim, a superset of the wick-only sweep used here) as its
own generic, reusable indicator -- this port's sweep detection is a
narrower, INLINE reimplementation (wick-only, no reclaim leg) kept local
because it feeds a state machine (sweep arms an FVG-overlap window) LSH
was never designed to expose, not because the underlying sweep math
itself is new. Neither `SWEEP_BULL`/`SWEEP_BEAR` events nor liquidity
levels are re-exposed as standalone columns here either, for the same
avoid-the-duplicate-column reason -- `LSH_SWEEP_BULL`/`LSH_SWEEP_BEAR`
already own that concept as a general-purpose column (on a swing_len the
caller controls independently of this indicator's `pivot_len`). This
port's actual value-add, and the only thing it outputs, is the COUPLING:
a displacement-qualified zone the sweep-armed window is currently
touching, distilled into `MAG_BULL`/`MAG_BEAR` (the fire event) and
`CE_DIST_BULL`/`CE_DIST_BEAR`/`CE_SCORE_BULL`/`CE_SCORE_BEAR` (an
always-on, non-sweep-gated proximity gauge to the nearest such zone's
midline).

⚠ `barstate.isconfirmed`-equivalent: like this fork's other event-
detection ports (`ob`, `fvg`, `sphinx_unicorn`, `liquidity_sweep`,
`rejection_blocks`), every row of a historical OHLCV frame is treated as
already-closed; the live caller (`indicator_engine.py`) is responsible
for not evaluating the final, still-forming bar, per this project's
`df.iloc[-3]` signal-bar law.

⚠ Score quirk, faithfully reproduced (not "fixed"): a zone's score is
computed ONCE at creation from the REAL displacement-candle body
(`f_score(gapSize, midBody, 0.0, volRatio[1])` in the source), but the
MAINTAIN pass that runs immediately afterward, in the SAME script
execution for that same bar (the source's MAINTAIN section runs strictly
after FVG STORAGE), unconditionally OVERWRITES it with
`f_score(gapSzNow, atr, float(age), volRatio)` -- note the second
argument is the bar's own ATR value, not the real displacement body. So
`dispPts = clamp(safeDiv(atr, atr) * 2.0, 0, 3.0)` is exactly 2.0
whenever ATR != 0 (a self-ratio), REGARDLESS of how large the qualifying
displacement candle actually was -- the creation-time score computed from
the real body is never actually observable in the source (or in this
port): it is overwritten before the bar's own script execution ends. This
port reproduces that by never computing a creation-time score at all --
a zone's `score` is only ever set by the MAINTAIN-pass formula, starting
on its own birth bar (see `_score`'s docstring). The real displacement
magnitude therefore matters ONLY as a creation GATE (`disp_ok_bull`/
`disp_ok_bear`), never as a scoring input.

⚠ Combined pool, dead zones linger (a distinct lifecycle from every
other level/zone pool in this family): the source's `fvgBox`/`fvgTop`/
`fvgBot`/... arrays hold BOTH bullish and bearish zones TOGETHER
(`fvg_lookback` bounds their combined count, same "one pool, both
directions" pattern `rejection_blocks.py` uses -- NOT the per-direction
pools `liquidity_sweep.py`/`sr_force.py` use), and a filled/expired zone
does NOT vacate its slot: `f_trimOldest` only runs when a NEW zone is
pushed, and it always evicts index 0 (oldest by insertion, REGARDLESS of
`fvgLive` state) once the pool exceeds `fvg_lookback`. So a dead
(filled/expired) zone occupies capacity indefinitely until a newer zone's
push happens to trim it away -- `fvg_lookback` bounds "zones tracked at
all" (live + not-yet-evicted-dead), not "zones currently live". Dedicated
regression test: `tests/test_fvg_sweep_magnet.py::
test_dead_zone_lingers_in_pool_until_fifo_evicted`.

⚠ `CE_DIST_BULL`/`CE_DIST_BEAR`/`CE_SCORE_BULL`/`CE_SCORE_BEAR` are this
port's own addition, in the `dist_to_res_level`/`SRF_DIST_*`/`LSH_DIST_*`/
`RB_DIST_*` tradition -- the source computes an analogous
`nearestMid`/`nearestDir`/`nearestDist` (plain, un-normalized, direction-
UNCONSTRAINED absolute price distance to literally the nearest live zone
of EITHER direction) but never reads it anywhere else in the script after
computing it: dead state in the source itself, not ported as-is. This
port's version differs deliberately in three ways: (1) ATR-normalized,
not raw price distance, matching this family's scale-free-distance
convention; (2) split BULL/BEAR (nearest live zone of THAT direction),
not a single direction-unconstrained nearest-of-either -- a more useful
per-direction read, and the natural shape given `MAG_BULL`/`MAG_BEAR` are
already split the same way; (3) candidacy is constrained to zones the
source's OWN `inGap = low <= top and high >= bot` test currently
overlaps -- i.e. the SAME zones eligible to fire a magnet signal (modulo
the sweep-freshness/score/candle-direction gates, which `CE_DIST`/
`CE_SCORE` deliberately do NOT apply -- they are an always-on proximity
gauge, not sweep-gated). Per this batch's now-established convention
(`sr_force.py`/`rejection_blocks.py`'s Fletcher-round findings on exactly
this boundary), any nearest-zone distance/score column must use an
INCLUSIVE side/candidacy test, not a strict one, with a dedicated
equality-boundary regression test -- unlike those two siblings, THIS
port needed no fix to get there: `inGap`'s `<=`/`>=` are already
inclusive in the ORIGINAL .pine source (not something this port
introduced), so Close (or the bar's High/Low) landing EXACTLY on a zone's
edge already counts as "in the gap" and reports a real distance, never
NaN, with no Fletcher-round history behind it. Dedicated regression
tests (still required by this batch's gate even without a prior-version
bug to regress against): `tests/test_fvg_sweep_magnet.py::
test_ce_dist_populated_not_nan_at_low_equals_top_boundary` (+ the
`high_equals_bot` mirror). `CE_SCORE_*` is NaN exactly when its paired
`CE_DIST_*` is NaN (no live, in-gap zone of that direction); `CE_DIST_*`
is NaN when no ATR is available, when ATR is exactly 0 (this port's own
division-by-zero guard, not present in the source, which never divides
by ATR for this purpose), or when no live zone of that direction
currently overlaps price.

Calculation:
    Default Inputs:
        fvg_lookback=10, disp_atr_mult=1.25, atr_len=14, min_gap_atr=0.25,
        require_disp=True, max_fvg_age=60, pivot_len=5, liq_keep=4,
        sweep_wick_mult=0.35, sweep_confirm=2, magnet_window=18, min_score=5
    Liquidity pools: confirmed pivot high/low via the strict-unique-extreme
        rule (`ta.pivothigh`/`ta.pivotlow` semantics, see
        `_confirm_strict_pivots`) at `pivot_len` bars either side -- a
        swing at bar i confirms at bar i + pivot_len. Pushed onto BSL
        (from highs) / SSL (from lows), each FIFO-capped INDEPENDENTLY at
        liq_keep.
    Sweep (bar t): wick_ok_high = (High[t] - max(Open[t],Close[t])) /
        (High[t]-Low[t]) >= sweep_wick_mult (0 if the bar has zero range);
        wick_ok_low mirrors on the low side. Bull sweep = wick_ok_low AND
        ATR defined AND ANY SSL level L with Low[t] < L < Close[t] AND
        Close[t] > Open[t]. Bear sweep mirrors on BSL with High[t] > L >
        Close[t] AND Close[t] < Open[t]. A sweep sets that direction's
        "last swept bar" to t.
    FVG creation (bar t, needs t >= 2 and ATR defined): bull gap raw =
        Low[t] > High[t-2]; bear gap raw = High[t] < Low[t-2]. Gap size
        (Low[t]-High[t-2] bull / Low[t-2]-High[t] bear) must be >=
        ATR(atr_len) * min_gap_atr. If require_disp: the MIDDLE bar (t-1)
        must close in the gap's own direction with body
        |Close[t-1]-Open[t-1]| >= ATR * disp_atr_mult. A qualifying zone
        (top, bot, dir, birth=t) is pushed onto the SINGLE COMBINED pool
        (bull+bear together), FIFO-capped at fvg_lookback (oldest slot
        evicted regardless of live/dead state).
    Maintenance (every bar, every zone in the pool including one born
        this bar): filled = Close[t] < bot (bull, STRICT) or Close[t] >
        top (bear, STRICT); expired = age > max_fvg_age; either kills the
        zone (permanently). While live: score = round(clamp(
        clamp(gap_size/ATR*3.2, 0,3) + clamp((ATR/ATR)*2.0, 0,3) +
        clamp(3-age/40, 0,2) + clamp(Volume[t]/SMA(Volume,20)[t]*1.2, 0,2),
        0, 10)) -- recomputed every live bar, see "score quirk" above.
    Magnet fire (bar t): bull-direction sweep must be "fresh"
        (sweep_confirm <= t - last_bull_swept_bar <= magnet_window); a
        live bull zone must have Low[t] <= top AND High[t] >= bot
        (inclusive overlap), score >= min_score, and Close[t] > Open[t].
        Bear mirrors. A cooldown suppresses a repeat fire of the same
        direction until more than magnet_window bars have passed since
        that direction's last fire.
    CE_DIST/CE_SCORE (bar t, this port's own addition): among the SAME
        live, in-gap-overlapping zones (NOT sweep/score/candle-direction
        gated), the one minimizing |Close[t] - (top+bot)/2| / ATR[t] per
        direction; its distance (>= 0 by construction, |.| never
        negative) and score are reported, NaN if none qualify.

Args:
    open_ (pd.Series): Series of 'open's
    high (pd.Series): Series of 'high's
    low (pd.Series): Series of 'low's
    close (pd.Series): Series of 'close's
    volume (pd.Series): Series of 'volume's
    fvg_lookback (int): Max combined (bull+bear) FVG zones tracked. Must
        be a positive int if given. Default: 10
    disp_atr_mult (float): Displacement-candle body must be >= ATR *
        this. Must be >= 0 if given. Default: 1.25
    atr_len (int): ATR lookback used throughout (gap size, displacement,
        scoring). Must be a positive int if given. Default: 14
    min_gap_atr (float): Minimum gap size, as a multiple of ATR. Must be
        >= 0 if given. Default: 0.25
    require_disp (bool): Require the displacement-candle body/direction
        filter. Must be a bool if given. Default: True
    max_fvg_age (int): Zones older than this (bars since creation) expire
        unresolved. Must be a positive int if given. Default: 60
    pivot_len (int): Bars either side required for a liquidity pivot.
        Must be a positive int if given. Default: 5
    liq_keep (int): Max liquidity levels tracked PER SIDE (BSL/SSL
        independently). Must be a positive int if given. Default: 4
    sweep_wick_mult (float): Minimum wick size as a fraction of the
        sweeping bar's own high-low range. Must be >= 0 if given.
        Default: 0.35
    sweep_confirm (int): Minimum bars after a sweep before the magnet
        window opens. Must be a positive int if given. Default: 2
    magnet_window (int): Bars after a sweep during which a magnet can
        fire; also the repeat-fire cooldown length. Must be a positive
        int if given. Default: 18
    min_score (int): Minimum zone score (0-10) required to fire a magnet
        signal. Must be a non-negative int if given (0 disables the score
        floor). Default: 5
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Raises:
    ValueError: `fvg_lookback`/`atr_len`/`max_fvg_age`/`pivot_len`/
        `liq_keep`/`sweep_confirm`/`magnet_window` given and not a
        positive, finite, integral value; `min_score` given and not a
        non-negative, finite, integral value; `disp_atr_mult`/
        `min_gap_atr`/`sweep_wick_mult` given and not a finite,
        non-negative value (NaN/+-inf/negative all raise; non-integral
        floats like 3.7 raise for int-typed params rather than silently
        truncating); `require_disp` given and not a bool. `None` (the
        actual default sentinel) still means "use the default," not an
        error.

Returns:
    pd.DataFrame: FSME_MAG_BULL, FSME_MAG_BEAR, FSME_CE_DIST_BULL,
        FSME_CE_DIST_BEAR, FSME_CE_SCORE_BULL, FSME_CE_SCORE_BEAR.
"""
