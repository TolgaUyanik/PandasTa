# -*- coding: utf-8 -*-
import math

import numpy as np
from pandas import DataFrame, Series

from pandas_ta.overlap.sma import sma
from pandas_ta.volatility.atr import atr
from pandas_ta.utils import get_offset, verify_series


def _validated_int(value, default, name, positive=True):
    """None -> default (a normal, documented default, not bad input).
    Anything else must be a genuine, finite, integral value, or raise.
    Duplicated verbatim from `inverse_fvg.py`/`macd_area_divergence.py`'s
    helper of the same name (checks NaN/inf/non-integral explicitly
    before ever calling `int()`, so every rejection path is the same
    ValueError, not a mix of ValueError/OverflowError/silent
    truncation)."""
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
    if abs(value) == float("inf"):
        raise ValueError(f"{name} must be finite, got inf")
    if positive and value <= 0:
        raise ValueError(f"{name} must be > 0, got {value}")
    if not positive and value < 0:
        raise ValueError(f"{name} must be >= 0, got {value}")
    return value


def _confirm_strict_pivots(series, left, right, is_high):
    """Causal pivot confirmation matching Pine's `ta.pivothigh`/
    `ta.pivotlow` (strict, unique extreme). Duplicated from
    `volume_sr_zones`/`sr_force` rather than cross-imported, matching
    this package's convention of self-contained indicator files.
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


class _Zone(object):
    """One drawn rectangle of the source, reduced to the four scalars the
    source's own merge tests actually read.

    The source stores five PARALLEL arrays per side (Pine L88-98):
    `closed*ClusterBoxes` (box[]) alongside `closed*ClusterTops`,
    `closed*ClusterBottoms`, `closed*ClusterVols` (float[]) and
    `closed*ClusterLabels`. Every merge test reads the FLOAT arrays
    (L175-177, L194-196, L327-329, L346-348); the box array is read at
    only three kinds of site, NONE of which carries state:
    `box.set_right` (L419-425), `box.delete` on FIFO eviction (L224/L376),
    and `array.get` in the cross-side merge (L203/L355) purely to recolour
    the survivor (`box.set_bgcolor`/`set_border_color`, not ported). Its
    `array.size` (L172/L191/L324/L343) is only a loop bound over the
    parallel float arrays. So the zone state is NOT locked inside drawing
    objects and this class is a faithful stand-in, not an approximation.
    (An earlier revision of this paragraph said the box array was "only
    ever iterated" for the first two -- literally false, since L203/L355
    do `array.get` it. The conclusion is unchanged; the sentence was not.)

    `opened_at` / `closed_at` are BAR INDICES in the port's own
    (causality-critical) sense: the bar on which the zone became visible
    and the bar on which it stopped being visible. `mass_events` is an
    append-only [(bar_index, mass)] timeline, because a zone's volume is
    mutated in place by later merges (L183, L202, L335, L354).
    """

    __slots__ = ("zid", "side", "top", "bottom", "opened_at", "closed_at", "mass_events")

    def __init__(self, zid, side, top, bottom, opened_at, mass):
        self.zid = zid                # stable identity for PASS 2's mass table
        self.side = side              # "demand" (low cluster) or "supply" (high cluster)
        self.top = top
        self.bottom = bottom
        self.opened_at = opened_at
        self.closed_at = None         # None == still on chart at the last bar
        self.mass_events = [(opened_at, mass)]

    def add_mass(self, at, delta):
        self.mass_events.append((at, self.mass_events[-1][1] + delta))

    @property
    def mass(self):
        return self.mass_events[-1][1]


def _zone_distance(price, zone):
    """Distance from `price` to the interval [zone.bottom, zone.top];
    0.0 when the price sits inside the zone."""
    return max(zone.bottom - price, price - zone.top, 0.0)


def sd_zone_pro(high, low, close, volume, pivot_length=None, group=None,
                max_bar_dist=None, merge_tol_mult=None, atr_length=None,
                box_atr_mult=None, max_boxes=None, vol_length=None,
                merge_cross_side=None, offset=None, **kwargs):
    """Indicator: SD Zone Pro -- zone mass imbalance (SDZ)"""
    pivot_length = _validated_int(pivot_length, 5, "pivot_length")
    group = _validated_int(group, 3, "group")
    max_bar_dist = _validated_int(max_bar_dist, 10, "max_bar_dist")
    merge_tol_mult = _validated_float(merge_tol_mult, 1.5, "merge_tol_mult", positive=False)
    atr_length = _validated_int(atr_length, 14, "atr_length")
    box_atr_mult = _validated_float(box_atr_mult, 0.5, "box_atr_mult", positive=False)
    # Pine's `maxBoxCount` documents 0 as "unlimited", so 0 is a legal value.
    max_boxes = _validated_int(max_boxes, 15, "max_boxes", positive=False)
    vol_length = _validated_int(vol_length, 20, "vol_length")
    if merge_cross_side is None:
        merge_cross_side = True
    if not isinstance(merge_cross_side, (bool, np.bool_)):
        raise ValueError(f"merge_cross_side must be a bool, got {merge_cross_side!r}")
    merge_cross_side = bool(merge_cross_side)

    min_len = 2 * pivot_length + 1
    high = verify_series(high, min_len)
    low = verify_series(low, min_len)
    close = verify_series(close, min_len)
    volume = verify_series(volume, min_len)
    offset = get_offset(offset)

    if high is None or low is None or close is None or volume is None: return

    pivot_high = _confirm_strict_pivots(high, pivot_length, pivot_length, is_high=True)
    pivot_low = _confirm_strict_pivots(low, pivot_length, pivot_length, is_high=False)
    atr_val = atr(high, low, close, length=atr_length)
    vol_avg = sma(volume, length=vol_length)

    n = len(close)
    ph_vals = pivot_high.to_numpy(dtype=float)
    pl_vals = pivot_low.to_numpy(dtype=float)
    atr_vals = atr_val.to_numpy(dtype=float) if atr_val is not None else np.full(n, np.nan)
    vol_vals = volume.to_numpy(dtype=float)
    vol_avg_vals = vol_avg.to_numpy(dtype=float) if vol_avg is not None else np.full(n, np.nan)
    close_vals = close.to_numpy(dtype=float)

    # ---------------------------------------------------------------
    # PASS 1 -- the source's clustering state machine.
    #
    # Produces a list of `_Zone`s, each carrying the bar on which it
    # became visible / stopped being visible and its mass timeline.
    # NOTHING is read out of the pool here; the read is PASS 2. Keeping
    # them apart is what makes the causality contract checkable at all
    # (a single fused forward loop cannot distinguish "visible from the
    # confirmation bar" from "visible from the pivot's own bar", because
    # in a forward loop both are trivially in the past).
    # ---------------------------------------------------------------
    # Pine L34-40: pivot value / bar / volume arrays, `array.unshift`ed
    # (most recent at index 0) and capped at 2520 entries (L47/L54).
    pl_v, pl_b, pl_vol = [], [], []
    ph_v, ph_b, ph_vol = [], [], []

    zones = []
    active = {"demand": None, "supply": None}   # Pine's `lastLowClusterBox` / `lastHighClusterBox`
    anchor_bar = {"demand": None, "supply": None}   # `lastLowClusterBar` / `lastHighClusterBar`
    anchor_price = {"demand": np.nan, "supply": np.nan}  # `lastLowClusterPrice` / `lastHighClusterPrice`
    anchor_vol = {"demand": 0.0, "supply": 0.0}     # `lastLowClusterVol` / `lastHighClusterVol`
    closed = {"demand": [], "supply": []}       # `closedLowCluster*` / `closedHighCluster*`

    for j in range(n):
        # CAUSALITY WRITE-SITE. Every zone-state change below (open,
        # close, mass merge) is stamped with this index. `j` is the
        # CONFIRMATION bar; the pivot that triggered the batch sits at
        # `j - pivot_length`. Back-dating this to the pivot's own bar is
        # exactly the mistranslation the source invites -- it draws its
        # box `left = minBarIdx` (L242-250), i.e. anchored at the pivot,
        # even though the box cannot exist until the pivot confirms.
        # `tests/test_sd_zone_pro.py::_load_backdating_mutant` patches
        # this one line and proves the difference is detected.
        zone_state_idx = j

        margin = atr_vals[j] * box_atr_mult if not np.isnan(atr_vals[j]) else 0.0
        merge_tol = atr_vals[j] * merge_tol_mult if not np.isnan(atr_vals[j]) else 0.0

        # Pine L43-55: record the confirmed pivot BEFORE the clustering
        # block reads `array.size(...)`. `volume[pLowLen]` is the volume
        # at the pivot's OWN bar, which is `j - pivot_length`.
        pivot_bar = j - pivot_length
        low_fired = not np.isnan(pl_vals[j])
        high_fired = not np.isnan(ph_vals[j])
        if low_fired:
            pl_v.insert(0, pl_vals[j])
            pl_b.insert(0, pivot_bar)
            pl_vol.insert(0, vol_vals[pivot_bar])
            if len(pl_v) > 2520:
                pl_v.pop(); pl_b.pop(); pl_vol.pop()
        if high_fired:
            ph_v.insert(0, ph_vals[j])
            ph_b.insert(0, pivot_bar)
            ph_vol.insert(0, vol_vals[pivot_bar])
            if len(ph_v) > 2520:
                ph_v.pop(); ph_b.pop(); ph_vol.pop()

        for side, fired, vals, bars, vols in (
            ("demand", low_fired, pl_v, pl_b, pl_vol),
            ("supply", high_fired, ph_v, ph_b, ph_vol),
        ):
            if not fired:
                continue
            # Pine L110-112 / L262-264: the batch trigger is a GLOBAL
            # MODULAR COUNTER over the all-time pivot count (itself
            # capped at 2520), NOT tidy consecutive bucketing.
            total = len(vals)
            if not (total >= group and total % group == 0):
                continue

            # Pine L117-126 / L269-278: scan the `group` MOST RECENT
            # pivots (indices 0..group-1 of an unshift-to-front array).
            # The comparison is STRICT (`<` / `>`), so on a tie the
            # lowest index -- the MOST RECENT pivot -- keeps the anchor.
            group_vol = 0.0
            ext_val = None
            ext_idx = -1
            for i in range(group):
                v = vals[i]
                group_vol += vols[i]
                if ext_val is None or (v < ext_val if side == "demand" else v > ext_val):
                    ext_val = v
                    ext_idx = i
            ext_bar = bars[ext_idx]

            # Pine L129 / L281: proximity check against the ACTIVE
            # cluster's anchor bar.
            if anchor_bar[side] is not None and (ext_bar - anchor_bar[side]) <= max_bar_dist:
                # ---- absorb into the active cluster (L130-164 / L282-316)
                combined = anchor_vol[side] + group_vol
                if side == "demand":
                    take_new = ext_val < anchor_price[side]
                    final_price = min(ext_val, anchor_price[side])
                else:
                    take_new = ext_val > anchor_price[side]
                    final_price = max(ext_val, anchor_price[side])
                final_bar = ext_bar if take_new else anchor_bar[side]

                # The source DELETES the old box and creates a new one
                # (same bar), so the active zone's geometry -- including
                # its ATR margin -- is refreshed at THIS bar's ATR.
                if active[side] is not None:
                    active[side].closed_at = zone_state_idx
                top, bottom = ((final_price + margin, final_price) if side == "demand"
                               else (final_price, final_price - margin))
                z = _Zone(len(zones), side, top, bottom, zone_state_idx, combined)
                zones.append(z)
                active[side] = z
                anchor_bar[side] = final_bar
                anchor_price[side] = final_price
                anchor_vol[side] = combined
            else:
                # ---- finalize the previous cluster (L167-228 / L319-380)
                prev = active[side]
                if prev is not None:
                    # `box.get_top`/`box.get_bottom` (L168-169 / L320-321)
                    # are the ONLY four reads out of a drawing object in
                    # the whole source, and they are exactly the values
                    # written at the box's two creation sites -- so the
                    # zone object carries them directly.
                    prev_top, prev_bottom = prev.top, prev.bottom
                    other = "supply" if side == "demand" else "demand"

                    target = None
                    for z in closed[side]:
                        if (prev_top + merge_tol) >= z.bottom and (z.top + merge_tol) >= prev_bottom:
                            target = z
                            break
                    if target is None and merge_cross_side:
                        # CROSS-SIDE MERGE (L189-213 / L341-365): a demand
                        # cluster's volume is added into a SUPPLY zone's
                        # `Vols` entry and the survivor keeps its own
                        # side's geometry. Faithful, and deliberately not
                        # "fixed" -- see the module docstring.
                        for z in closed[other]:
                            if (prev_top + merge_tol) >= z.bottom and (z.top + merge_tol) >= prev_bottom:
                                target = z
                                break

                    if target is not None:
                        target.add_mass(zone_state_idx, anchor_vol[side])
                        prev.closed_at = zone_state_idx       # `box.delete`
                    else:
                        # Stored as a new closed box -- the SAME object is
                        # pushed (L216 / L368), so it keeps its identity,
                        # geometry and mass; it just stops being "active".
                        closed[side].append(prev)
                        if max_boxes > 0 and len(closed[side]) > max_boxes:
                            evicted = closed[side].pop(0)
                            evicted.closed_at = zone_state_idx

                # ---- open a fresh cluster (L242-256 / L394-408)
                top, bottom = ((ext_val + margin, ext_val) if side == "demand"
                               else (ext_val, ext_val - margin))
                z = _Zone(len(zones), side, top, bottom, zone_state_idx, group_vol)
                zones.append(z)
                active[side] = z
                anchor_bar[side] = ext_bar
                anchor_price[side] = ext_val
                anchor_vol[side] = group_vol

    # ---------------------------------------------------------------
    # PASS 2 -- read the pool.
    # ---------------------------------------------------------------
    opens = [[] for _ in range(n)]
    closes = [[] for _ in range(n)]
    mass_at = [[] for _ in range(n)]
    for z in zones:
        # A zone whose close lands on (or before) its own open was never
        # visible on any bar -- registering it would leak it into `live`
        # permanently, since PASS 2 applies closes before opens.
        if z.closed_at is not None and z.closed_at <= z.opened_at:
            continue
        if 0 <= z.opened_at < n:
            opens[z.opened_at].append(z)
        if z.closed_at is not None and 0 <= z.closed_at < n:
            closes[z.closed_at].append(z)
        for at, m in z.mass_events[1:]:
            if 0 <= at < n:
                mass_at[at].append((z, m))

    imbalance = np.full(n, np.nan)
    near_mass = np.full(n, np.nan)
    live = {"demand": [], "supply": []}
    cur_mass = {}          # zid -> mass as of the current bar

    for j in range(n):
        for z in closes[j]:
            if z in live[z.side]:
                live[z.side].remove(z)
        for z in opens[j]:
            live[z.side].append(z)
            cur_mass[z.zid] = z.mass_events[0][1]
        for z, m in mass_at[j]:
            cur_mass[z.zid] = m

        c = close_vals[j]
        if np.isnan(c):
            continue

        best = {}
        for side in ("demand", "supply"):
            pool = live[side]
            if not pool:
                continue
            bz = pool[0]
            bd = _zone_distance(c, bz)
            for z in pool[1:]:
                d = _zone_distance(c, z)
                if d < bd:
                    bz, bd = z, d
            best[side] = (bz, bd)

        if "demand" in best and "supply" in best:
            dm = cur_mass[best["demand"][0].zid]
            sm = cur_mass[best["supply"][0].zid]
            tot = sm + dm
            if tot > 0:
                imbalance[j] = (sm - dm) / tot

        if best:
            # Nearest zone on EITHER side; on an exact tie demand wins
            # (dict insertion order below is demand-then-supply and the
            # comparison is strict).
            near = None
            for side in ("demand", "supply"):
                if side not in best:
                    continue
                z, d = best[side]
                if near is None or d < near[1]:
                    near = (z, d)
            va = vol_avg_vals[j]
            if not np.isnan(va) and va > 0:
                near_mass[j] = cur_mass[near[0].zid] / va

    imbalance = Series(imbalance, index=close.index)
    near_mass = Series(near_mass, index=close.index)

    # Offset
    if offset != 0:
        imbalance = imbalance.shift(offset)
        near_mass = near_mass.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        for s in (imbalance, near_mass):
            s.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        for s in (imbalance, near_mass):
            s.fillna(method=kwargs["fill_method"], inplace=True)

    _props = f"_{pivot_length}_{group}"
    imbalance.name = f"SDZ_MASS_IMBALANCE{_props}"
    near_mass.name = f"SDZ_NEAR_MASS{_props}"

    df = DataFrame({
        imbalance.name: imbalance,
        near_mass.name: near_mass,
    })
    df.name = f"SDZ{_props}"
    df.category = "trend"

    return df


sd_zone_pro.__doc__ = \
"""SD Zone Pro -- supply/demand zone MASS imbalance (SDZ)

Confirmed swing pivots are batched `group` at a time; each batch's
summed volume is attached to a price shelf anchored at the batch's
extreme pivot. Nearby batches are absorbed into the running ("active")
cluster; a batch that arrives too far away finalizes the active cluster,
which either MERGES its volume into an already-resting zone whose price
range it overlaps (within an ATR tolerance) or becomes a resting zone
itself. What accumulates is VOLUME: merging never widens a zone, it only
adds mass to the older survivor.

Outputs the scale-free imbalance between the mass resting at the nearest
supply shelf and the nearest demand shelf, plus (optionally) the nearest
shelf's mass expressed in average-bars-of-volume.

Source: TradingView community indicator "SD Zone Pro"
(`docs/TradingView/pine/gIs5tbMW.pine`, Pine v6, 440 lines; see
`datastore/source/pine_candidates_families.csv` for the attribution row)
(ported into AwakenAnalytics/Backtesting TVPTA-6, 2026-08-15; MPL-2.0
per TradingView's open-source publication convention).

WHY THIS IS NOT A `volume_sr_zones` RE-PORT
    `volume_sr_zones` (VOLSR) uses volume exactly ONCE, as a boolean
    admission test (`vol_vals[pivot_bar] > vol_avg_vals[pivot_bar] *
    vol_mult`), and then discards it -- its zone tuple is `(lo, hi)`,
    price only. NO zone in this fork carries a volume WEIGHT. Both
    `sr_force.py` and `sr_decay.py` explicitly record
    `calcHistoricalPower` -- "ATR-normalized price shock x volume
    multiple x recency weight" -- as NOT ported and still deferred. This
    port fills that documented hole from a different source: here the
    volume IS the zone's state, mutated by every later merge.
    Accordingly this port deliberately ships NO `*_DIST` and NO
    `*_BROKEN` column: that lane already holds `VOLSR_RES_DIST`/
    `VOLSR_SUP_DIST`, `SRF_DIST_RES`/`SRF_DIST_SUP`, `IFVG_DIST_SUP`/
    `IFVG_DIST_RES`, `LCB_HIGH_DIST`/`LCB_LOW_DIST` and the engine's own
    `dist_to_res_level`/`dist_to_sup_level`, and a distance column from
    this source would be VOLSR with different knobs. Raw cumulative
    volume is not shipped either -- volume regimes drift the way nominal
    price levels do, so a mass only leaves this module as a RATIO.

THREE FAITHFULNESS TRAPS (each reproduced literally, not tidied)
 1. THE BATCH TRIGGER IS A GLOBAL MODULAR COUNTER, NOT A SLIDING WINDOW.
    Pine L112/L264: `totalLowPivots >= xGroupLow and (totalLowPivots %
    xGroupLow == 0)`, where `totalLowPivots = array.size(pLowVals)` is
    the ALL-TIME pivot count, itself capped at 2520 (L47/L54). A batch
    fires on every N-th pivot EVER SEEN, and the loop then reads the N
    MOST RECENT pivots (indices 0..N-1 of an unshift-to-front array) --
    which is NOT the same set as "the N pivots since the last batch"
    once the cap starts biting. Consequence, reproduced here: once the
    array saturates at 2520 and `2520 % group == 0` (true for every
    `group` in 1..10, and for 12/14/15/18/20/21/...), the trigger fires
    on EVERY subsequent pivot. Do not "fix" this into consecutive
    bucketing.
 2. THE SOURCE'S OWN DEFAULTS MAKE THE HEADLINE FEATURE A NO-OP.
    `xGroupLow = xGroupHigh = 1` (L15-16) means no grouping at all, and
    `pLowLen = pHighLen = 1` (L9-10) means 1-bar noise pivots. This port
    DEVIATES DELIBERATELY: `pivot_length=5, group=3`. Precedent for
    disclosing a defaults deviation rather than inheriting a degenerate
    one: `sr_force.py`'s fixed-`swing_len` note. Pass `pivot_length=1,
    group=1` to reproduce the source's shipped configuration exactly.
 3. CROSS-SIDE MERGE CONTAMINATES MASS BY DESIGN.
    Pine L199-213 / L351-365: when a finalized DEMAND cluster overlaps a
    resting SUPPLY zone (and `mergeCrossSide` is on, the source's
    default), the demand volume is added to that SUPPLY zone's `Vols`
    entry and the survivor keeps its own side's geometry. So
    `SDZ_MASS_IMBALANCE` is NOT a clean bull/bear split; it is "mass
    resting at the nearest shelf above vs at the nearest shelf below",
    where a shelf may have been built from both sides. That is the
    source's actual semantics and it is not silently repaired here --
    pass `merge_cross_side=False` to switch it off.

ALSO WORTH KNOWING: THESE ZONES NEVER DIE ON A BREAK. There is no
close-through eviction anywhere in the source; the only removal is FIFO
overflow at `maxBoxCount` per side (L223-228 / L375-380). Combined with
the absence of any volume gate at formation (VOLSR has one), the zone
population here is materially different from VOLSR's -- these shelves
persist through price, VOLSR's do not.

STATE IS NOT LOCKED IN DRAWING OBJECTS. The source declares five
PARALLEL arrays per side (L88-98): `closed*ClusterBoxes` (box[]) beside
`closed*ClusterTops`/`Bottoms`/`Vols` (float[]) and `*Labels`. Every
merge test reads the FLOAT arrays (L175-177, L194-196, L327-329,
L346-348); the box array is only iterated for `box.set_right` (L419-425)
and `box.delete` on eviction. The only four reads out of a drawing
object in the whole file are `box.get_top`/`box.get_bottom` at L168-169
and L320-321, and they are reconstructible: the active demand box is
built at exactly two sites (L150-158, L242-250) with its `bottom`
written straight into the scalar `lastLowClusterPrice` on the next line
(L161/L253), so `prevBottom == lastLowClusterPrice` identically and
`prevTop == lastLowClusterPrice + boxMargin-as-of-the-creating-bar`.
Supply mirrors (L302-310, L394-402). This port carries `top`/`bottom` on
the `_Zone` object itself, written at exactly those two sites, so the
`box.get_*` calls disappear with no loss.

CAUSALITY. A pivot is only known `pivot_length` bars after it prints, so
every zone-state change (open, close, mass merge) is stamped with the
CONFIRMATION bar `j`, never with the pivot's own bar `j - pivot_length`
and never with the cluster's anchor bar. The source itself invites the
mistranslation -- it draws the box with `left = minBarIdx`, back at the
pivot -- which is why the port separates PASS 1 (state machine, emits a
timestamped zone timeline) from PASS 2 (reads the pool bar by bar): a
single fused forward loop cannot tell the two apart, so it cannot be
tested. `tests/test_sd_zone_pro.py` patches the single write-site (the
lone `zone_state_idx` assignment at the top of PASS 1's bar loop) into a
back-dating mutant and shows the difference is detected.

NOT PORTED (drawing / cosmetics only): `formatVol` (L60-70), every
`label.new`/`label.set_*` site (L138-148, L230-240, L290-300, L382-392,
L427-440), every `box.new`/`box.set_right`/`box.set_bgcolor` site
(L150-158, L242-250, L302-310, L394-402, L410-425), the
`useMergedColor`/`mergedColor` recolour inputs (L22-23), the
`showDemandLabels`/`showSupplyLabels` toggles (L12-13) and
`displayMode`/`showDemand`/`showSupply` (L25-27, both sides are always
computed here -- the imbalance needs both).

Calculation:
    Default Inputs:
        pivot_length=5, group=3, max_bar_dist=10, merge_tol_mult=1.5,
        atr_length=14, box_atr_mult=0.5, max_boxes=15, vol_length=20,
        merge_cross_side=True
    Confirmed pivot highs/lows via the strict-unique-extreme rule (see
        `_confirm_strict_pivots`), recorded with the volume at the
        PIVOT'S OWN BAR (Pine `volume[pLowLen]`).
    margin       = ATR(atr_length) * box_atr_mult        (current bar)
    merge_tol    = ATR(atr_length) * merge_tol_mult      (current bar)
    On every `group`-th pivot ever seen (per side): take the `group`
        most recent pivots, sum their volumes, take their extreme price.
    If (extreme_bar - active_anchor_bar) <= max_bar_dist: absorb into the
        active cluster -- mass adds, the anchor moves to the more
        extreme price, geometry is rebuilt at the current bar's margin.
    Else: finalize the active cluster. If its [bottom, top] overlaps a
        resting SAME-side zone within merge_tol, its mass is added there
        and it is discarded; else, if merge_cross_side, the same test is
        run against resting OTHER-side zones; else it becomes a resting
        zone (FIFO, per side, capped at max_boxes). Then a fresh active
        cluster opens at the batch extreme.
    Demand zone = [price, price + margin]; supply = [price - margin, price]
    nearest_*    = the live zone of that side minimising the distance to
        close (0 inside the zone)
    SDZ_MASS_IMBALANCE = (nearest_supply_mass - nearest_demand_mass) /
        (nearest_supply_mass + nearest_demand_mass),  in [-1, +1]
    SDZ_NEAR_MASS      = mass of the nearest live zone on EITHER side /
        SMA(volume, vol_length)

Args:
    high (pd.Series): Series of 'high's
    low (pd.Series): Series of 'low's
    close (pd.Series): Series of 'close's
    volume (pd.Series): Series of 'volume's
    pivot_length (int): Bars each side of the candidate pivot. Default: 5
        (the source ships 1 -- see faithfulness trap 2)
    group (int): Pivots per batch. Default: 3 (the source ships 1)
    max_bar_dist (int): Max bar gap for absorbing a batch into the
        active cluster. Default: 10
    merge_tol_mult (float): Zone-overlap tolerance as an ATR multiple.
        Default: 1.5
    atr_length (int): ATR period. Default: 14
    box_atr_mult (float): Zone height as an ATR multiple. Default: 0.5
    max_boxes (int): Resting zones kept per side (FIFO); 0 = unlimited,
        matching the source's own documented sentinel. Default: 15
    vol_length (int): Volume SMA period for SDZ_NEAR_MASS. Default: 20
    merge_cross_side (bool): Allow a finalized cluster to merge its mass
        into the OTHER side's resting zone. Default: True (the source's
        own default -- see faithfulness trap 3)
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.DataFrame: SDZ_MASS_IMBALANCE, SDZ_NEAR_MASS columns.
"""
