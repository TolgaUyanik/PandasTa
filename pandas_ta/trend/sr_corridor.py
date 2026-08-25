# -*- coding: utf-8 -*-
import numpy as np
from pandas import DataFrame, Series

from pandas_ta.volatility.atr import atr
from pandas_ta.utils import get_offset, verify_series


def _validated_int(value, default, name, positive=True):
    """None -> default (a normal, documented default, not bad input).
    Anything else must be a genuine, finite, integral value, or raise.
    Same helper, same rejection paths, as `dtdb.py`/`atr_push.py`."""
    if value is None:
        return default
    if isinstance(value, bool):
        raise ValueError(f"{name} must be an int, got bool {value!r}")
    if isinstance(value, float):
        if value != value:
            raise ValueError(f"{name} must be a finite int, got NaN")
        if np.isinf(value):
            raise ValueError(f"{name} must be a finite int, got inf")
        if not value.is_integer():
            raise ValueError(f"{name} must be an integral value, got {value}")
    try:
        value = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{name} must be an int, got {value!r}")
    if positive and value <= 0:
        raise ValueError(f"{name} must be a positive int, got {value}")
    if not positive and value < 0:
        raise ValueError(f"{name} must be a non-negative int, got {value}")
    return value


def _validated_float(value, default, name, positive=True):
    """Same nan/inf discipline as `_validated_int`, float variant."""
    if value is None:
        return default
    if isinstance(value, bool):
        raise ValueError(f"{name} must be a float, got bool {value!r}")
    try:
        value = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{name} must be a float, got {value!r}")
    if value != value:
        raise ValueError(f"{name} must be finite, got NaN")
    if np.isinf(value):
        raise ValueError(f"{name} must be finite, got inf")
    if positive and value <= 0:
        raise ValueError(f"{name} must be > 0, got {value}")
    if not positive and value < 0:
        raise ValueError(f"{name} must be >= 0, got {value}")
    return value


def _confirm_strict_pivots(series, left, right, is_high):
    """Causal pivot confirmation matching Pine's `ta.pivothigh`/
    `ta.pivotlow` (strict, unique extreme). A bar at position `i`
    confirms at `j = i + right` iff it is the unique extreme of the
    window `[i - left, i + right]`.

    Duplicated from `volume_sr_zones.py` rather than cross-imported,
    matching this package's convention of self-contained indicator
    files. The duplication is DELIBERATE and load-bearing for this
    module in particular: `volume_sr_zones` (VOLSR) is the closest
    existing port, and using the same pivot rule keeps the difference
    between the two modules in the zone LIFECYCLE and the emitted
    feature, where it actually is, rather than manufacturing a
    difference out of a helper choice.

    Unlike VOLSR, `left` and `right` are genuinely independent here --
    the Pine source runs an ASYMMETRIC `pivotLeft = 8, pivotRight = 5`
    (source lines 82-96), and VOLSR's signature cannot express that
    (it takes a single `pivot_length` used on both sides).
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


_ZONE_RESISTANCE = 1
_ZONE_SUPPORT = -1


def sr_corridor(high, low, close, pivot_left=None, pivot_right=None,
                atr_length=None, zone_atr=None, invalidation_atr=None,
                max_zones=None, max_edge_atr=None, offset=None, **kwargs):
    """Indicator: Support/Resistance Corridor Width (SRCOR)"""
    pivot_left = _validated_int(pivot_left, 8, "pivot_left")
    pivot_right = _validated_int(pivot_right, 5, "pivot_right")
    atr_length = _validated_int(atr_length, 14, "atr_length")
    max_zones = _validated_int(max_zones, 40, "max_zones")
    zone_atr = _validated_float(zone_atr, 0.60, "zone_atr")
    invalidation_atr = _validated_float(invalidation_atr, 0.10,
                                        "invalidation_atr", positive=False)
    # `max_edge_atr` is the ONE knob with no counterpart in the Pine
    # source (see the DELIBERATE DEVIATION block below). A positive
    # infinity explicitly disables it and reproduces the source's
    # unbounded behaviour bit-for-bit, which is how the deviation is
    # tested; every other value goes through the same validation as the
    # ported parameters.
    if max_edge_atr is None:
        max_edge_atr = 50.0
    elif isinstance(max_edge_atr, float) and np.isposinf(max_edge_atr):
        pass
    else:
        max_edge_atr = _validated_float(max_edge_atr, 50.0, "max_edge_atr")

    min_len = pivot_left + pivot_right + 1
    high = verify_series(high, min_len)
    low = verify_series(low, min_len)
    close = verify_series(close, min_len)
    offset = get_offset(offset)

    if high is None or low is None or close is None: return

    pivot_high = _confirm_strict_pivots(high, pivot_left, pivot_right, is_high=True)
    pivot_low = _confirm_strict_pivots(low, pivot_left, pivot_right, is_high=False)
    atr_val = atr(high, low, close, length=atr_length)

    n = len(close)
    ph_vals = pivot_high.to_numpy(dtype=float)
    pl_vals = pivot_low.to_numpy(dtype=float)
    atr_vals = atr_val.to_numpy(dtype=float)
    close_vals = close.to_numpy(dtype=float)

    width_atr = np.full(n, np.nan)

    # ------------------------------------------------------------------
    # The ported slice is the Pine source's ZONE ENGINE + COMPRESSED AREA
    # block (source lines 321-590), and NOTHING else. Bar order inside
    # the loop reproduces the source's own top-to-bottom order:
    #
    #   1. CREATE ZONES            (source lines 337-391)
    #   2. REMOVE INVALIDATED      (source lines 394-441)
    #   3. FIND NEAREST S AND R    (source lines 444-495)
    #   4. COMPRESSED AREA         (source lines 571-590)
    #
    # so a zone created on THIS bar is immediately eligible to be
    # invalidated by THIS bar's close, and immediately eligible to be
    # the nearest zone -- the same same-bar ordering hazard that was
    # found and fixed in `volume_sr_zones.py`.
    #
    # WHAT MAKES THIS NOT VOLSR. Five differences, all from the source:
    #   (i)   NO volume filter at formation. VOLSR only forms a zone
    #         when volume at the pivot's own bar beat its own SMA by
    #         `vol_mult`; this source forms one on EVERY confirmed
    #         pivot, so `volume` is not an argument here at all.
    #   (ii)  ASYMMETRIC pivots (8 left / 5 right, source lines 82-96).
    #   (iii) An ATR INVALIDATION BUFFER (source line 400): a zone dies
    #         only on `close > top + atr * invalidation_atr` (or
    #         `close < bottom - ...`), not on a bare close through the
    #         level as in VOLSR.
    #   (iv)  The CORRIDOR itself (source lines 575-590) -- a TWO-SIDED
    #         measurement VOLSR has no analogue for, and the only thing
    #         this module emits.
    #   (v)   Nearest-zone SELECTION by price-unit distance with a
    #         ZERO-CLAMP inside the zone (source lines 464-495), rather
    #         than VOLSR's percent distance. Used here only to pick
    #         WHICH zones bound the corridor; never emitted.
    #
    # Two further divergences from VOLSR that are not in that list but
    # are real: the FIFO cap is SHARED across both zone types (source
    # line 383, `MAX_STORED_ZONES = 40` over one set of arrays), where
    # VOLSR caps each side separately at `max_levels`; and the zone
    # DEPTH is scaled by `atr[pivotRight]` -- the ATR as of the pivot's
    # OWN bar (source lines 349, 369) -- where VOLSR uses the ATR of the
    # confirmation bar.
    #
    # DELIBERATELY NOT PORTED: the daily VWAP and the UTC opening range
    # (source lines 252-320), the market-context/observation state
    # machine (source lines 595-885), and the dashboard/visual/alert
    # block (source lines 886-1489). Verified before cutting: source
    # lines 321-594 contain no reference to `openingRange`, `dailyVWAP`,
    # `newUtcDay`, `utcMinuteOfDay` or `insideOpeningRange`; the first
    # such reference after the zone block is `dailyVWAP` at line 601.
    # Every `box`/`line`/`label`/`table` call inside the zone block is
    # dropped, as is the per-zone `zoneEvaluated` bookkeeping, which
    # exists only to stop the state machine re-reporting a zone.
    #
    # DELIBERATE DEVIATION FROM THE SOURCE -- `max_edge_atr`. This is the
    # ONE rule in this module that the Pine source does not contain, and
    # it is stated here rather than buried because every other line above
    # is a faithfulness note.
    #
    #   THE SOURCE LINE THAT DOES NOT EXIST. The source's zone lifecycle
    #   is exactly three rules: born on a confirmed pivot (L337-391),
    #   evicted oldest-first past `MAX_STORED_ZONES = 40` (L148 declares
    #   it; L383-391 is the eviction loop), and killed by a close beyond
    #   its edge plus `atr * invalidationBufferATR` (L398-441). Grep the
    #   zone LIFECYCLE (L337-441) for a bound on how FAR a zone may sit
    #   from price, or on how OLD it may get: there is none. (The only
    #   age term that could touch a ZONE is `math.max(zoneCreatedBar,
    #   bar_index - 5000)` at L1097/L1211 -- it clamps the DRAWN box's
    #   left edge in the un-ported visual block and never touches the
    #   zone arrays. The file's other age term, `watchAge` at L690/L773,
    #   ages a reaction WATCH, not a zone, and is likewise un-ported.) `L400` is
    #   the only distance test in the zone block and it is the
    #   invalidation buffer, not a sanity bound.
    #
    #   WHY THAT IS A DEFECT ON THIS DATA, MEASURED. `MGROS.IS` carries a
    #   pre-2005 lira-redenomination residual: `High`/`Low` are in OLD
    #   lira while `Open`/`Close` are in NEW lira, so `High` peaks at
    #   12,235,458 at index 159 against a `Close` of 11.61, and 162 bars
    #   carry `High > 2*Close`. DI-1's c2c test passes on ALL of them
    #   (0 failures) because `Close` itself is clean, so nothing upstream
    #   catches it. Under the source's three rules that produces two
    #   immortal populations: seven resistance zones born at index 57-164
    #   with tops of 8.3e6-1.2e7, which `close > top + buf` can never
    #   reach again; and one support zone born at index 224 whose BOTTOM
    #   is a legitimate 9.228 but whose TOP is 87,970, because its depth
    #   was scaled by a contaminated `atr[pivotRight]` of ~1.46e5. None
    #   of them is ever evicted either -- eviction fires only when the
    #   LIVE count exceeds 40, and ordinary zones die fast enough that it
    #   never does. The support zone then wins the nearest-support race
    #   on every subsequent bar for free, because the source's zero-clamp
    #   (L473-480) scores any zone price sits INSIDE at distance 0.
    #   Result, measured: 5,410 of that frame's 5,485 populated bars
    #   (98.6%), contiguous from index 268 to 5677, carry |value| > 1000,
    #   median |numerator| 87,953 against a median `Close` of 20.02
    #   (4,393x price). The ATR divisor on those bars is NORMAL --
    #   median 0.6113 against 0.6391 over the whole frame -- so this is
    #   a numerator defect, not a divisor collapse.
    #
    #   THE RULE ADDED. A zone is eligible to BOUND the corridor only if
    #   the edge that would bound it lies within `max_edge_atr * atr` of
    #   the current close -- the TOP for a support zone, the BOTTOM for a
    #   resistance zone, i.e. exactly the number that enters the emitted
    #   arithmetic. It is applied ONLY to eligibility in step 3. Zones
    #   are still born, evicted and invalidated exactly as the source
    #   does, and the bound is REVERSIBLE: a far zone becomes eligible
    #   again if price travels back to it, which a removal rule could not
    #   express. Because both surviving edges are then within
    #   `max_edge_atr` of the same close, the emitted column is bounded
    #   by construction to +/- 2 * max_edge_atr.
    #
    #   WHY 50.0. It is a SANITY bound placed in clear air between two
    #   populations, not a percentile fitted to one. Measured over the
    #   same 89 BIST_100 daily frames / 367,669 populated bars: on the 87
    #   clean frames the winning zone's edge distance has median 3.73 ATR,
    #   q0.999 29.31 and a MAXIMUM of 124.29, and only 63 of 357,840 bars
    #   (0.0176%) have a winner beyond 50 ATR; the contaminated winners
    #   sit near 1.4e5 ATR, about 2,800x the bound. Three orders of
    #   magnitude separate them.
    #
    #   WHAT IT DOES NOT DO, so it is not oversold: it does NOT make a
    #   contaminated frame correct. During the contaminated era itself
    #   both the levels and the ATR are garbage together and the ratio
    #   stays small, so nothing here detects that; DI-5 does. What it
    #   stops is one bad print poisoning the column for the REST of the
    #   series after prices return to a normal scale. The immortal zones
    #   also still occupy FIFO slots (8 of 40 on `MGROS.IS`), which this
    #   rule does not reclaim.
    # ------------------------------------------------------------------
    zone_top = []
    zone_bottom = []
    zone_type = []
    for j in range(n):
        c = close_vals[j]
        a = atr_vals[j]
        pivot_bar = j - pivot_right
        a_pivot = atr_vals[pivot_bar] if pivot_bar >= 0 else np.nan

        # 1. CREATE ZONES (source lines 337-391)
        if not np.isnan(ph_vals[j]) and not np.isnan(a_pivot):
            top = ph_vals[j]
            zone_top.append(top)
            zone_bottom.append(top - a_pivot * zone_atr)
            zone_type.append(_ZONE_RESISTANCE)
        if not np.isnan(pl_vals[j]) and not np.isnan(a_pivot):
            bottom = pl_vals[j]
            zone_top.append(bottom + a_pivot * zone_atr)
            zone_bottom.append(bottom)
            zone_type.append(_ZONE_SUPPORT)
        # `while array.size(zoneIds) > MAX_STORED_ZONES` + `array.shift`
        # (source lines 383-391): oldest-first eviction, ONE shared cap.
        while len(zone_type) > max_zones:
            zone_top.pop(0)
            zone_bottom.pop(0)
            zone_type.pop(0)

        # 2. REMOVE INVALIDATED ZONES (source lines 394-441).
        # Pine guards the whole block on `array.size(zoneIds) > 0`, and
        # its `close < zoneBottom - buffer` comparison yields `na` (which
        # an `if` treats as false) whenever `atr` is still `na`, so a
        # NaN ATR removes nothing. Replicated rather than "cleaned up".
        if zone_type and not np.isnan(a):
            buf = a * invalidation_atr
            keep_t, keep_b, keep_y = [], [], []
            for t, b, y in zip(zone_top, zone_bottom, zone_type):
                dead = ((y == _ZONE_SUPPORT and c < b - buf)
                        or (y == _ZONE_RESISTANCE and c > t + buf))
                if not dead:
                    keep_t.append(t)
                    keep_b.append(b)
                    keep_y.append(y)
            zone_top, zone_bottom, zone_type = keep_t, keep_b, keep_y

        # 3. FIND NEAREST SUPPORT AND RESISTANCE (source lines 444-495).
        # Scanned oldest-first with a strictly-less-than update, exactly
        # as the source's `for index = 0 to array.size(zoneIds) - 1`
        # loop does, so ties resolve to the OLDER zone.
        best_sup = np.nan
        best_res = np.nan
        sup_top = np.nan
        res_bottom = np.nan
        # The DELIBERATE DEVIATION, and the only line in this loop the
        # source does not have. When the ATR is unusable there is nothing
        # to measure the bound in, so no bound is applied -- and the
        # emit below is NaN on those bars anyway.
        edge_cap = a * max_edge_atr if (not np.isnan(a) and a > 0) else np.inf
        for t, b, y in zip(zone_top, zone_bottom, zone_type):
            if y == _ZONE_SUPPORT and c >= b:
                if abs(c - t) > edge_cap:
                    continue
                d = c - t if c > t else 0.0
                if np.isnan(best_sup) or d < best_sup:
                    best_sup = d
                    sup_top = t
            elif y == _ZONE_RESISTANCE and c <= t:
                if abs(c - b) > edge_cap:
                    continue
                d = b - c if c < b else 0.0
                if np.isnan(best_res) or d < best_res:
                    best_res = d
                    res_bottom = b

        # 4. COMPRESSED AREA (source lines 575-590).
        # `distanceBetweenZones = nearestResistanceBottom -
        # nearestSupportTop` is a SIGNED price-unit gap (negative when
        # the two zones overlap). It is a price LEVEL difference, so it
        # is published ONLY divided by ATR -- see the module docstring.
        if not np.isnan(sup_top) and not np.isnan(res_bottom) \
                and not np.isnan(a) and a > 0:
            width_atr[j] = (res_bottom - sup_top) / a

    width = Series(width_atr, index=close.index)

    # Offset
    if offset != 0:
        width = width.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        width.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        width.fillna(method=kwargs["fill_method"], inplace=True)

    _props = f"_{pivot_left}_{pivot_right}_{zone_atr}"
    width.name = f"SRCOR_WIDTH_ATR{_props}"

    df = DataFrame({width.name: width})
    df.name = f"SRCOR{_props}"
    df.category = "trend"

    return df


sr_corridor.__doc__ = \
"""Support/Resistance Corridor Width (SRCOR)

The signed gap between the nearest active resistance zone's BOTTOM edge
and the nearest active support zone's TOP edge, expressed in ATR units.
Positive means price sits in an open corridor that many ATRs wide;
values near zero mean support and resistance have closed in on each
other (the source's "compressed area"); negative means the two zones
overlap.

This is a TWO-SIDED structural measurement, and that is the whole point
of the port. This package already ships `volume_sr_zones` (VOLSR), whose
pivot detection, ATR-scaled zone band, bounded FIFO and nearest-zone
search are ~85% the same machinery, and which already publishes
one-sided DISTANCE columns (`VOLSR_RES_DIST`, `VOLSR_SUP_DIST`) plus
break flags. SRCOR deliberately publishes NEITHER a distance NOR a break
flag -- only the corridor, which VOLSR has no analogue for.

WHY THE FLAG IS NOT A COLUMN. The source's boolean `zonesCloseTogether`
(source lines 588-590) is `distanceBetweenZones <= atr *
minimumZoneGapATR`. Dividing both sides by `atr` (> 0 wherever this
column is populated) makes that EXACTLY `SRCOR_WIDTH_ATR <=
minimumZoneGapATR`, i.e. a fixed threshold on the column above, at the
source's default 0.25. Shipping it as well would be a second column
recoverable in full from the first by any threshold-splitting consumer,
so only the continuous form is emitted. `tests/test_sr_corridor.py`
asserts that identity rather than leaving it as a claim.

WHY IT IS DIVIDED BY ATR. `distanceBetweenZones` is a difference of two
price levels and therefore carries price units; emitting it raw would be
a price level by another name, which this project's indicator
conventions rule out (nominal-drift decay). Dividing by the same bar's
ATR makes it invariant to a rescaling of the whole price series, which
`tests/test_sr_corridor.py` checks bit-exactly at power-of-two factors.

ONE DELIBERATE DEVIATION FROM THE SOURCE: `max_edge_atr`. The source's
zone lifecycle has no bound on how far from price a zone may sit and no
bound on its age, so a zone born off a corrupted High can neither be
invalidated nor evicted and bounds the corridor forever. Measured on
`MGROS.IS` (a pre-2005 lira-redenomination residual that DI-1's c2c test
passes): 5,410 of 5,485 populated bars, 98.6% of the frame, contiguous
over twenty-one years. `max_edge_atr` makes a zone eligible to bound the
corridor only while the edge that would bound it is within that many ATR
of the current close. Default 50.0; pass `float('inf')` to reproduce the
source exactly. Full argument, measurements and residuals: the DELIBERATE
DEVIATION block in the function body.

Source: TradingView community indicator, Pine v6, published script
`yQdPgJ6s` ("Crypto Intraday Engine"), 1,489 content lines (ported into
AwakenAnalytics/Backtesting TVPTA-6, 2026-08-25; MPL-2.0 per
TradingView's open-source publication convention). ONLY the zone engine
and compressed-area blocks (source lines 321-594) are ported. The daily
VWAP and UTC opening range (lines 252-320), the market-context and
observation state machine (lines 595-885) and the dashboard, visual
objects and alerts (lines 886-1489) are NOT ported.

Calculation:
    Default Inputs:
        pivot_left=8, pivot_right=5, atr_length=14, zone_atr=0.60,
        invalidation_atr=0.10, max_zones=40
    Confirmed pivot highs/lows via the strict-unique-extreme rule (see
        `_confirm_strict_pivots`), asymmetric left/right.
    On a confirmed pivot high: resistance zone
        [pivot_high - ATR[pivot_bar] * zone_atr, pivot_high]
    On a confirmed pivot low: support zone
        [pivot_low, pivot_low + ATR[pivot_bar] * zone_atr]
    where ATR[pivot_bar] is the ATR as of the pivot's OWN bar.
    Zones are held in ONE shared oldest-first FIFO capped at
        `max_zones`, and die on
        close > top + ATR * invalidation_atr        (resistance)
        close < bottom - ATR * invalidation_atr     (support)
    Nearest support = the eligible (close >= bottom, AND
        `|close - top| <= ATR * max_edge_atr`) support zone minimising
        `close - top` clamped at 0 inside the zone; resistance mirrors it
        on its BOTTOM edge. Ties go to the older zone.
    SRCOR_WIDTH_ATR = (nearest_resistance_bottom - nearest_support_top)
        / ATR, and NaN unless BOTH sides have an eligible zone.

Args:
    high (pd.Series): Series of 'high's
    low (pd.Series): Series of 'low's
    close (pd.Series): Series of 'close's
    pivot_left (int): Bars to the LEFT of a candidate pivot. Default: 8
    pivot_right (int): Bars to the RIGHT of a candidate pivot; also the
        confirmation lag. Default: 5
    atr_length (int): ATR period. Default: 14
    zone_atr (float): Zone depth as an ATR multiple. Default: 0.60
    invalidation_atr (float): Extra ATR multiple price must close beyond
        a zone before it dies. 0 reproduces a bare break. Default: 0.10
    max_zones (int): Shared FIFO cap across both zone types. Default: 40
    max_edge_atr (float): NOT IN THE SOURCE -- sanity bound on zone
        eligibility. A zone may bound the corridor only while the edge
        that would bound it (a support's TOP, a resistance's BOTTOM) is
        within this many ATR of the current close. Bounds the emitted
        column to +/- 2 * max_edge_atr by construction.
        `float('inf')` disables it and reproduces the source. Default: 50.0
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.DataFrame: SRCOR_WIDTH_ATR column.
"""
