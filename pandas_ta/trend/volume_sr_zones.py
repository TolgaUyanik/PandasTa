# -*- coding: utf-8 -*-
import numpy as np
from pandas import DataFrame, Series

from pandas_ta.overlap.sma import sma
from pandas_ta.volatility.atr import atr
from pandas_ta.utils import get_offset, verify_series


def _confirm_strict_pivots(series, left, right, is_high):
    """Causal pivot confirmation matching Pine's `ta.pivothigh`/
    `ta.pivotlow` (strict, unique extreme). Duplicated from
    `equal_highs_lows`/`rsi_divergence` rather than cross-imported,
    matching this package's convention of self-contained indicator files.
    """
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
    return Series(out, index=series.index)


def volume_sr_zones(high, low, close, volume, pivot_length=None, vol_length=None,
                     vol_mult=None, atr_length=None, zone_atr_mult=None,
                     max_levels=None, offset=None, **kwargs):
    """Indicator: Volume-Weighted Support & Resistance Zones (VOLSR)"""
    pivot_length = int(pivot_length) if pivot_length and pivot_length > 0 else 10
    vol_length = int(vol_length) if vol_length and vol_length > 0 else 20
    vol_mult = float(vol_mult) if vol_mult and vol_mult > 0 else 1.5
    atr_length = int(atr_length) if atr_length and atr_length > 0 else 14
    zone_atr_mult = float(zone_atr_mult) if zone_atr_mult and zone_atr_mult > 0 else 0.25
    max_levels = int(max_levels) if max_levels and max_levels > 0 else 8
    high = verify_series(high, 2 * pivot_length + 1)
    low = verify_series(low, 2 * pivot_length + 1)
    close = verify_series(close, 2 * pivot_length + 1)
    volume = verify_series(volume, 2 * pivot_length + 1)
    offset = get_offset(offset)

    if high is None or low is None or close is None or volume is None: return

    pivot_high = _confirm_strict_pivots(high, pivot_length, pivot_length, is_high=True)
    pivot_low = _confirm_strict_pivots(low, pivot_length, pivot_length, is_high=False)
    atr_val = atr(high, low, close, length=atr_length)
    vol_avg = sma(volume, length=vol_length)

    n = len(close)
    ph_vals = pivot_high.to_numpy(dtype=float)
    pl_vals = pivot_low.to_numpy(dtype=float)
    atr_vals = atr_val.to_numpy(dtype=float)
    vol_vals = volume.to_numpy(dtype=float)
    vol_avg_vals = vol_avg.to_numpy(dtype=float)
    close_vals = close.to_numpy(dtype=float)

    res_broken = np.zeros(n, dtype=int)
    sup_broken = np.zeros(n, dtype=int)
    res_dist = np.full(n, np.nan)
    sup_dist = np.full(n, np.nan)

    # A confirmed pivot only forms a zone if the volume AT THE PIVOT'S
    # OWN BAR exceeded its own rolling average by `vol_mult` (an
    # "institutional footprint" filter). Zones are held (a bounded FIFO
    # of up to `max_levels`) until price closes through them, then
    # dropped -- the nearest (highest resistance / lowest support) active
    # zone at each bar is exposed as a scale-free % distance, matching
    # this project's distance-form convention (`priorday_fib`,
    # `dist_to_res_level`).
    # Fletcher round 1 (TVPTA-3-composite): the source (TZLl2QBP.pine
    # lines 37-82) runs FORM-NEW-ZONE, THEN REMOVE-BROKEN-LEVELS, in that
    # order within a single bar's top-to-bottom pass -- a zone formed
    # THIS bar is immediately eligible to be broken by THIS bar's own
    # close (e.g. a pivot confirms with the price already past it). The
    # first attempt at this port ran break-check before formation, which
    # silently let a same-bar create-then-immediately-break zone survive
    # as a phantom, permanently-unbroken level -- reproduced concretely
    # and fixed by matching the source's actual order.
    res_levels = []  # each: [price_low, price_high] (zone_low..pivot_high)
    sup_levels = []
    for j in range(n):
        c = close_vals[j]

        if not np.isnan(ph_vals[j]):
            pivot_bar = j - pivot_length
            if pivot_bar >= 0 and not np.isnan(vol_vals[pivot_bar]) and not np.isnan(vol_avg_vals[pivot_bar]):
                if vol_vals[pivot_bar] > vol_avg_vals[pivot_bar] * vol_mult:
                    price = ph_vals[j]
                    zone_h = atr_vals[j] * zone_atr_mult if not np.isnan(atr_vals[j]) else 0.0
                    res_levels.append((price - zone_h, price))
                    if len(res_levels) > max_levels:
                        res_levels.pop(0)

        if not np.isnan(pl_vals[j]):
            pivot_bar = j - pivot_length
            if pivot_bar >= 0 and not np.isnan(vol_vals[pivot_bar]) and not np.isnan(vol_avg_vals[pivot_bar]):
                if vol_vals[pivot_bar] > vol_avg_vals[pivot_bar] * vol_mult:
                    price = pl_vals[j]
                    zone_h = atr_vals[j] * zone_atr_mult if not np.isnan(atr_vals[j]) else 0.0
                    sup_levels.append((price, price + zone_h))
                    if len(sup_levels) > max_levels:
                        sup_levels.pop(0)

        kept = []
        for lo, hi in res_levels:
            if c > hi:
                res_broken[j] = 1
            else:
                kept.append((lo, hi))
        res_levels = kept

        kept = []
        for lo, hi in sup_levels:
            if c < lo:
                sup_broken[j] = 1
            else:
                kept.append((lo, hi))
        sup_levels = kept

        if res_levels:
            nearest_res = min((hi for _, hi in res_levels if hi >= c), default=min(hi for _, hi in res_levels))
            res_dist[j] = (c - nearest_res) / c * 100
        if sup_levels:
            nearest_sup = max((lo for lo, _ in sup_levels if lo <= c), default=max(lo for lo, _ in sup_levels))
            sup_dist[j] = (c - nearest_sup) / c * 100

    res_broken = Series(res_broken, index=close.index)
    sup_broken = Series(sup_broken, index=close.index)
    res_dist = Series(res_dist, index=close.index)
    sup_dist = Series(sup_dist, index=close.index)

    # Offset
    if offset != 0:
        res_broken = res_broken.shift(offset)
        sup_broken = sup_broken.shift(offset)
        res_dist = res_dist.shift(offset)
        sup_dist = sup_dist.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        for s in (res_broken, sup_broken, res_dist, sup_dist):
            s.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        for s in (res_broken, sup_broken, res_dist, sup_dist):
            s.fillna(method=kwargs["fill_method"], inplace=True)

    _props = f"_{pivot_length}_{vol_length}"
    res_dist.name = f"VOLSR_RES_DIST{_props}"
    sup_dist.name = f"VOLSR_SUP_DIST{_props}"
    res_broken.name = f"VOLSR_RES_BROKEN{_props}"
    sup_broken.name = f"VOLSR_SUP_BROKEN{_props}"

    df = DataFrame({
        res_dist.name: res_dist,
        sup_dist.name: sup_dist,
        res_broken.name: res_broken,
        sup_broken.name: sup_broken,
    })
    df.name = f"VOLSR{_props}"
    df.category = "trend"

    return df


volume_sr_zones.__doc__ = \
"""Volume-Weighted Support & Resistance Zones (VOLSR)

Confirmed swing pivots that formed on ABOVE-AVERAGE volume (volume at the
pivot's own bar > its own `vol_length`-bar SMA * `vol_mult`) become
ATR-sized support/resistance zones, held until price closes through them.
The volume-confirmation gate is what distinguishes this from a plain
pivot/zigzag level -- an ordinary swing extreme reached on THIN volume is
not treated as meaningful resting supply/demand. Outputs the scale-free %
distance from close to the nearest active resistance/support zone (a
bounded FIFO of up to `max_levels` zones per side), plus break flags.

Source: TradingView community indicator "Volume-Weighted Support &
Resistance" (see `datastore/source/pine_triage.csv` for the exact
attribution row) (ported into AwakenAnalytics/Backtesting TVPTA-3,
2026-08-04; MPL-2.0 per TradingView's open-source publication
convention). Ported in full -- the source's entire substance is this
detection+zone-lifecycle logic; only the box-drawing/fade-on-break visual
styling is not replicated.

Calculation:
    Default Inputs:
        pivot_length=10, vol_length=20, vol_mult=1.5, atr_length=14,
        zone_atr_mult=0.25, max_levels=8
    Confirmed pivot highs/lows via the strict-unique-extreme rule (see
        `_confirm_strict_pivots`).
    vol_ok = volume[pivot_bar] > SMA(volume, vol_length)[pivot_bar] * vol_mult
    On vol_ok, a zone forms: resistance = [pivot_high - ATR*zone_atr_mult,
        pivot_high]; support = [pivot_low, pivot_low + ATR*zone_atr_mult]
    Zone dropped when close crosses fully through it (close > zone top
        for resistance, close < zone bottom for support)
    VOLSR_RES_DIST/VOLSR_SUP_DIST = (close - nearest active zone edge) /
        close * 100
    VOLSR_RES_BROKEN/VOLSR_SUP_BROKEN = 1 on the break bar

Args:
    high (pd.Series): Series of 'high's
    low (pd.Series): Series of 'low's
    close (pd.Series): Series of 'close's
    volume (pd.Series): Series of 'volume's
    pivot_length (int): Bars each side of the candidate pivot. Default: 10
    vol_length (int): Volume SMA period for the confirmation gate.
        Default: 20
    vol_mult (float): Volume must exceed its SMA by this multiple.
        Default: 1.5
    atr_length (int): ATR period for zone sizing. Default: 14
    zone_atr_mult (float): Zone height as an ATR multiple. Default: 0.25
    max_levels (int): Maximum tracked zones per side (FIFO). Default: 8
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.DataFrame: VOLSR_RES_DIST, VOLSR_SUP_DIST, VOLSR_RES_BROKEN,
        VOLSR_SUP_BROKEN columns.
"""
