# -*- coding: utf-8 -*-
import numpy as np
from pandas import DataFrame, Series

from pandas_ta.volatility.atr import atr
from pandas_ta.utils import get_offset, verify_series


def _confirm_strict_pivots(series, left, right, is_high):
    """Causal pivot confirmation matching Pine's `ta.pivothigh`/
    `ta.pivotlow`: a bar at position i confirms (becomes visible at
    j=i+right) iff it is the STRICT, UNIQUE extreme of the window
    [i-left, i+right]. Duplicated from `equal_highs_lows.py`'s (and
    `sphinx_unicorn.py`'s) identical helper rather than imported, matching
    this package's convention of self-contained indicator files."""
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
    __slots__ = ("price", "lvl_bar", "broken")

    def __init__(self, price, lvl_bar, broken=False):
        self.price = price
        self.lvl_bar = lvl_bar
        self.broken = broken


def _process_side(levels, t, extreme_v, close_v, atr_v, atr_mult, max_age,
                   mode_wick, mode_reclaim, is_bear):
    """Advance one side's level pool (bear=BSL/swing-highs, bull=SSL/
    swing-lows) by one bar. Returns (new_levels, did_sweep, did_reclaim).
    `extreme_v` is `high_v` for the bear side, `low_v` for the bull side --
    the price the wick must pierce through."""
    new_levels = []
    did_sweep = False
    did_reclaim = False
    for lvl in levels:
        if t - lvl.lvl_bar > max_age:
            continue  # aged out, no event -- matches Pine's maxAge branch

        if is_bear:
            pen_ok = (atr_mult == 0.0) or (extreme_v[t] - lvl.price >= atr_v[t] * atr_mult)
            is_sweep = mode_wick and (not lvl.broken) and (extreme_v[t] > lvl.price) and (close_v[t] < lvl.price) and pen_ok
        else:
            pen_ok = (atr_mult == 0.0) or (lvl.price - extreme_v[t] >= atr_v[t] * atr_mult)
            is_sweep = mode_wick and (not lvl.broken) and (extreme_v[t] < lvl.price) and (close_v[t] > lvl.price) and pen_ok

        reclaim = False
        broken = lvl.broken
        if mode_reclaim:
            if is_bear:
                if (not broken) and (close_v[t] > lvl.price) and pen_ok:
                    broken = True
                elif broken and (close_v[t] < lvl.price):
                    reclaim = True
            else:
                if (not broken) and (close_v[t] < lvl.price) and pen_ok:
                    broken = True
                elif broken and (close_v[t] > lvl.price):
                    reclaim = True

        if is_sweep or reclaim:
            did_sweep = did_sweep or is_sweep
            did_reclaim = did_reclaim or reclaim
            continue  # resolved -- level leaves the pool, mirrors Pine's .remove(i)

        new_levels.append(_Level(lvl.price, lvl.lvl_bar, broken))

    return new_levels, did_sweep, did_reclaim


def liquidity_sweep(high, low, close, swing_len=None, atr_len=None, atr_mult=None,
                     max_levels=None, max_age=None, mode=None, offset=None, **kwargs):
    """Indicator: Liquidity Sweep Hunter (LSH)"""
    swing_len = int(swing_len) if swing_len and swing_len > 0 else 10
    atr_len = int(atr_len) if atr_len and atr_len > 0 else 14
    atr_mult = float(atr_mult) if atr_mult is not None and atr_mult >= 0 else 0.1
    max_levels = int(max_levels) if max_levels and max_levels > 0 else 10
    max_age = int(max_age) if max_age and max_age > 0 else 300
    mode = mode.lower() if mode and isinstance(mode, str) else "both"
    if mode not in ("wick", "reclaim", "both"):
        mode = "both"
    mode_wick = mode in ("wick", "both")
    mode_reclaim = mode in ("reclaim", "both")

    # atr_len is included in the length floor even though `_process_side`
    # tolerates NaN ATR gracefully (NaN comparisons are False, so an
    # unwarmed ATR just blocks penetration rather than crashing) -- the
    # `atr()` call below does its OWN independent verify_series(atr_len)
    # check and returns None (not a NaN-filled Series) on a too-short
    # frame, which would otherwise crash `.to_numpy()` on that None even
    # after this function's own (smaller) min_len check had passed.
    min_len = max(2 * swing_len + 1, atr_len)
    high = verify_series(high, min_len)
    low = verify_series(low, min_len)
    close = verify_series(close, min_len)
    offset = get_offset(offset)

    if high is None or low is None or close is None: return

    n = len(close)
    high_v = high.to_numpy(dtype=float)
    low_v = low.to_numpy(dtype=float)
    close_v = close.to_numpy(dtype=float)
    atr_v = atr(high, low, close, length=atr_len).to_numpy(dtype=float)

    ph = _confirm_strict_pivots(high, swing_len, swing_len, is_high=True)   # swing highs -> BSL (bear levels)
    pl = _confirm_strict_pivots(low, swing_len, swing_len, is_high=False)   # swing lows  -> SSL (bull levels)

    sweep_bull = np.zeros(n, dtype=int)
    sweep_bear = np.zeros(n, dtype=int)
    reclaim_bull = np.zeros(n, dtype=int)
    reclaim_bear = np.zeros(n, dtype=int)
    dist_res = np.full(n, np.nan)   # % distance to nearest unswept BSL (resistance, above)
    dist_sup = np.full(n, np.nan)   # % distance to nearest unswept SSL (support, below)

    bear_levels = []  # BSL pool, from confirmed swing HIGHS
    bull_levels = []  # SSL pool, from confirmed swing LOWS

    for t in range(n):
        # --- pivot detection: new levels enter the pool THIS bar, before
        # the same bar's event check -- matches Pine's script order (the
        # pivot-detection `if` blocks run before the event-detection
        # block, both gated by the same `barstate.isconfirmed` bar) ---
        if not np.isnan(ph[t]):
            bear_levels.append(_Level(ph[t], t - swing_len))
            if len(bear_levels) > max_levels:
                bear_levels.pop(0)  # FIFO cap, mirrors Pine's `.shift()` on overflow

        if not np.isnan(pl[t]):
            bull_levels.append(_Level(pl[t], t - swing_len))
            if len(bull_levels) > max_levels:
                bull_levels.pop(0)

        # --- event detection over the (possibly just-grown) pools ---
        bear_levels, did_sweep_bear, did_reclaim_bear = _process_side(
            bear_levels, t, high_v, close_v, atr_v, atr_mult, max_age,
            mode_wick, mode_reclaim, is_bear=True)
        bull_levels, did_sweep_bull, did_reclaim_bull = _process_side(
            bull_levels, t, low_v, close_v, atr_v, atr_mult, max_age,
            mode_wick, mode_reclaim, is_bear=False)

        sweep_bear[t] = int(did_sweep_bear)
        reclaim_bear[t] = int(did_reclaim_bear)
        sweep_bull[t] = int(did_sweep_bull)
        reclaim_bull[t] = int(did_reclaim_bull)

        if bear_levels:
            nearest = min(bear_levels, key=lambda lv: abs(lv.price - close_v[t]))
            dist_res[t] = (nearest.price - close_v[t]) / close_v[t] * 100
        if bull_levels:
            nearest = min(bull_levels, key=lambda lv: abs(lv.price - close_v[t]))
            dist_sup[t] = (close_v[t] - nearest.price) / close_v[t] * 100

    sweep_bull = Series(sweep_bull, index=close.index)
    sweep_bear = Series(sweep_bear, index=close.index)
    reclaim_bull = Series(reclaim_bull, index=close.index)
    reclaim_bear = Series(reclaim_bear, index=close.index)
    dist_res = Series(dist_res, index=close.index)
    dist_sup = Series(dist_sup, index=close.index)

    if offset != 0:
        sweep_bull = sweep_bull.shift(offset)
        sweep_bear = sweep_bear.shift(offset)
        reclaim_bull = reclaim_bull.shift(offset)
        reclaim_bear = reclaim_bear.shift(offset)
        dist_res = dist_res.shift(offset)
        dist_sup = dist_sup.shift(offset)

    if "fillna" in kwargs:
        for s in (sweep_bull, sweep_bear, reclaim_bull, reclaim_bear, dist_res, dist_sup):
            s.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        for s in (sweep_bull, sweep_bear, reclaim_bull, reclaim_bear, dist_res, dist_sup):
            s.fillna(method=kwargs["fill_method"], inplace=True)

    _props = f"_{swing_len}"
    sweep_bull.name = f"LSH_SWEEP_BULL{_props}"
    sweep_bear.name = f"LSH_SWEEP_BEAR{_props}"
    reclaim_bull.name = f"LSH_RECLAIM_BULL{_props}"
    reclaim_bear.name = f"LSH_RECLAIM_BEAR{_props}"
    dist_res.name = f"LSH_DIST_RES{_props}"
    dist_sup.name = f"LSH_DIST_SUP{_props}"

    df = DataFrame({
        sweep_bull.name: sweep_bull,
        sweep_bear.name: sweep_bear,
        reclaim_bull.name: reclaim_bull,
        reclaim_bear.name: reclaim_bear,
        dist_res.name: dist_res,
        dist_sup.name: dist_sup,
    })
    df.name = f"LSH{_props}"
    df.category = "trend"

    return df


liquidity_sweep.__doc__ = \
"""Liquidity Sweep Hunter (LSH)

Confirmed swing pivots become resting liquidity levels -- buy-side
liquidity (BSL) above swing highs, sell-side liquidity (SSL) below swing
lows -- held in a bounded, aging pool per side. Each active level resolves
one of two ways: a WICK SWEEP (price pierces through on an intrabar wick
and closes back inside, same bar) or a BREAK-THEN-RECLAIM (a later bar
closes through the level, flagging it "broken"; a subsequent bar's close
crosses back reclaims it). An ATR-scaled minimum-penetration filter gates
both event types; levels older than `max_age` bars expire unresolved.

Source: TradingView community indicator "Liquidity Sweep Hunter |
AlphaScript" by AlphaScript, https://www.tradingview.com/script/
PqkIPsgl-Liquidity-Sweep-Hunter-AlphaScript/ (ported into AwakenAnalytics/
Backtesting TVPTA-6, 2026-08-11; MPL-2.0 per TradingView's open-source
publication convention). Replaces the source's pivot-detection block
(`ta.pivothigh`/`ta.pivotlow` under `barstate.isconfirmed`), its per-side
level-pool maintenance (push/shift array with `maxLevels`/`maxAge`), and
its event-resolution loop (the `isSweep`/`reclaim` logic inside the
`bearLevels`/`bullLevels` `for` loops) -- i.e. every line of actual
signal math in the source. NOT ported: all line/label/table drawing,
the dashboard, `plotshape`, and the `alertcondition` wrappers (each
alert condition is a boolean this port already computes as a column, or
an OR of two already-computed columns).

⚠ Naming note: the source's `bearLevels` array holds levels born from
swing HIGHS (tagged "BSL" on the source's chart labels, buy-side
liquidity resting ABOVE price -- where short-sellers' stops and long
take-profits sit), resolved by the source's own `bearSweep`/`bearReclaim`
booleans; `bullLevels` holds levels born from swing LOWS (tagged "SSL"),
resolved by `bullSweep`/`bullReclaim`. So "bear" already means "the BSL/
swing-high side" in the source itself, not an inversion this port
introduces -- `LSH_SWEEP_BEAR`/`LSH_RECLAIM_BEAR` mirror the source's own
`bearSweep`/`bearReclaim` directly (swing-high levels, checked against
`high`), and `_BULL` mirrors `bullSweep`/`bullReclaim` (swing-low levels,
checked against `low`). Worth stating explicitly only because "BSL"
sounds like it should pair with "bull" at a skim.

⚠ `barstate.isconfirmed` gating: the source only detects pivots and
events on confirmed (closed) bars, guarding against the currently-forming
bar repainting. Every row of a historical OHLCV frame passed to this
function is, by construction, already a closed bar -- so this port
processes every row as the source would process a confirmed one; it does
not special-case a final "still forming" row (same convention as this
fork's other event-detection ports, e.g. `ob`, `fvg`, `sphinx_unicorn` --
the live caller (`indicator_engine.py`) is responsible for not evaluating
the last, still-forming bar, per this project's `df.iloc[-3]` signal-bar
law, not this function).

⚠ Simplified vs. the source in two ways, both deliberate: (1) the
source's per-level `line`/`label` drawing objects are dropped entirely --
pure state, no chart I/O. (2) "nearest unswept level" for the two `DIST`
columns is defined here as nearest-by-absolute-price-distance across the
WHOLE active pool for that side, a natural reading the source itself
never needed (it never asks "how far to the nearest level," only "did
THIS level's price get hit") -- this is this port's own addition to
satisfy the project's scale-free-distance convention (see `docs/
indicators/family-structure-smc.md` header / `dist_to_res_level`
precedent), not a translation of existing Pine math.

Calculation:
    Default Inputs:
        swing_len=10, atr_len=14, atr_mult=0.1, max_levels=10, max_age=300,
        mode="both" ("wick", "reclaim", or "both")
    Confirmed pivot high/low via strict-unique-extreme rule (`ta.pivothigh`/
        `ta.pivotlow` semantics, see `_confirm_strict_pivots`) -- a swing at
        bar i confirms at bar i+swing_len.
    On confirmation, push a new level (price=pivot, lvl_bar=i) onto that
        side's pool; if the pool exceeds `max_levels`, drop the OLDEST
        (FIFO), matching the source's push/shift array.
    Each bar, for every active level of a side not yet aged out
        (`bar - lvl_bar <= max_age`):
            pen_ok = atr_mult==0 or (penetration >= ATR(atr_len) * atr_mult)
            WICK SWEEP (mode in wick/both): wick pierces through AND close
                closes back on the origin side of the level AND pen_ok AND
                level not already broken.
            BREAK-THEN-RECLAIM (mode in reclaim/both): if not yet broken
                and close crosses through with pen_ok, mark broken (no
                event fires); if already broken and a later close crosses
                back, fire reclaim.
            Either event resolves (removes) the level; sweep and reclaim
                are mutually exclusive for a given level on a given bar
                (their close-side conditions are complements).
    DIST_RES = (nearest active BSL/bear-level price - close) / close * 100
        (NaN if no active BSL level); DIST_SUP = (close - nearest active
        SSL/bull-level price) / close * 100 (NaN if no active SSL level).

Args:
    high (pd.Series): Series of 'high's
    low (pd.Series): Series of 'low's
    close (pd.Series): Series of 'close's
    swing_len (int): Bars either side required for a pivot. Default: 10
    atr_len (int): ATR lookback for the penetration filter. Default: 14
    atr_mult (float): Minimum penetration, as a multiple of ATR. 0 disables
        the filter. Default: 0.1
    max_levels (int): Max active levels tracked per side. Default: 10
    max_age (int): Levels older than this (bars since confirmation) expire
        unresolved. Default: 300
    mode (str): "wick", "reclaim", or "both". Default: "both"
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.DataFrame: LSH_SWEEP_BULL, LSH_SWEEP_BEAR, LSH_RECLAIM_BULL,
        LSH_RECLAIM_BEAR, LSH_DIST_RES, LSH_DIST_SUP.
"""
