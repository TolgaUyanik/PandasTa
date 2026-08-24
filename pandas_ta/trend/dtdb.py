# -*- coding: utf-8 -*-
import numpy as np
from pandas import DataFrame, Series

from pandas_ta.trend.zigzag_fib import _confirm_pivots
from pandas_ta.volatility.atr import atr
from pandas_ta.utils import get_offset, verify_series


def _validated_int(value, default, name, positive=True):
    """None -> default (a normal, documented default, not bad input).
    Anything else must be a genuine, finite, integral value, or raise.
    Same helper, same rejection paths, as `atr_push.py`/`sd_zone_pro.py`."""
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


def _validated_choice(value, default, name, allowed):
    if value is None:
        return default
    if not isinstance(value, str):
        raise ValueError(f"{name} must be one of {allowed}, got {value!r}")
    v = value.strip().lower()
    if v not in allowed:
        raise ValueError(f"{name} must be one of {allowed}, got {value!r}")
    return v


# Pine's f_crossBar caps its backward `low[o]`/`high[o]` reach at o <= 4990,
# one notch inside the script's own `max_bars_back = 5000` (source L2). Kept
# verbatim even though it is unreachable at these pivot spacings, because it
# is a real clause of the ported function and removing it silently would be
# an undocumented divergence.
_MAX_BARS_BACK = 4990


def dtdb(high, low, close, pivots=None, tol_atr=None, buf_atr=None,
         void_atr=None, max_wait=None, track_bars=None, max_keep=None,
         atr_length=None, mode=None, dbl_mode=None, offset=None, **kwargs):
    """Indicator: Double Top / Double Bottom (DTDB)"""
    pivots = _validated_int(pivots, 8, "pivots")
    if pivots < 3:
        raise ValueError(f"pivots must be >= 3, got {pivots}")
    atr_length = _validated_int(atr_length, 14, "atr_length")
    max_wait = _validated_int(max_wait, 60, "max_wait")
    track_bars = _validated_int(track_bars, 120, "track_bars")
    max_keep = _validated_int(max_keep, 12, "max_keep")
    tol_atr = _validated_float(tol_atr, 0.5, "tol_atr")
    buf_atr = _validated_float(buf_atr, 0.15, "buf_atr", positive=False)
    void_atr = _validated_float(void_atr, 0.0, "void_atr", positive=False)
    mode = _validated_choice(mode, "close", "mode", ("close", "wick"))
    dbl_mode = _validated_choice(dbl_mode, "any", "dbl_mode", ("any", "weaker"))
    offset = get_offset(offset)

    min_len = 2 * pivots + 1
    high = verify_series(high, min_len)
    low = verify_series(low, min_len)
    close = verify_series(close, min_len)
    if high is None or low is None or close is None:
        return

    n = len(close)
    atr_s = atr(high, low, close, length=atr_length)

    # Pine: ph = ta.pivothigh(pivLen, pivLen); pl = ta.pivotlow(pivLen, pivLen)
    # (source L75-76). `_confirm_pivots` is IMPORTED from `zigzag_fib` rather
    # than copied a third time -- see the DIVERGENCES section of the module
    # docstring for why that deliberately breaks this package's
    # self-contained-module convention.
    ph_s, _ = _confirm_pivots(high, pivots, pivots)
    _, pl_s = _confirm_pivots(low, pivots, pivots)

    h = high.to_numpy(dtype=float)
    l = low.to_numpy(dtype=float)
    c = close.to_numpy(dtype=float)
    a = atr_s.to_numpy(dtype=float)
    ph = ph_s.to_numpy(dtype=float)
    pl = pl_s.to_numpy(dtype=float)

    conf_bear = np.full(n, np.nan)
    conf_bull = np.full(n, np.nan)
    tgt = np.full(n, np.nan)
    pend = np.full(n, np.nan)
    res = np.full(n, np.nan)
    warm = min(n, 2 * pivots)
    for _arr in (conf_bear, conf_bull, tgt, pend, res):
        _arr[warm:] = 0.0

    # zigzag state -- Pine's zzB / zzP / zzD (source L65-67), capped at 20.
    zz_b, zz_p, zz_d = [], [], []
    pats = []

    def _zz_push(b, pr, d):
        """Pine f_zzPush, source L88-112. Returns True only when a genuinely
        NEW pivot is appended; a same-direction, more-extreme pivot EXTENDS
        the last entry in place and returns False (so no re-match fires)."""
        m = len(zz_d)
        appended = False
        if m == 0:
            zz_b.append(b); zz_p.append(pr); zz_d.append(d)
            appended = True
        else:
            li = m - 1
            if zz_d[li] == d:
                lp = zz_p[li]
                if (d == 1 and pr > lp) or (d == -1 and pr < lp):
                    zz_p[li] = pr
                    zz_b[li] = b
            else:
                zz_b.append(b); zz_p.append(pr); zz_d.append(d)
                appended = True
        while len(zz_d) > 20:
            zz_b.pop(0); zz_p.pop(0); zz_d.pop(0)
        return appended

    def _region_taken(s, e):
        """Pine f_regionTaken, source L139-153. Rejects a new span that
        overlaps an existing pattern's span by more than 15% of the shorter
        of the two. Pine guards `m >= 2` on the point array; every DT/DB
        pattern here carries 3 or 4 points, so that guard is always true and
        is not re-expressed."""
        sp = e - s
        for p in pats:
            ps = p["start_bar"]
            pe = p["last_bar"]
            ov = min(e, pe) - max(s, ps)
            if ov > 0.15 * min(sp, pe - ps):
                return True
        return False

    def _cross_bar(j, from_bar, to_bar, level, bear, max_back):
        """Pine f_crossBar, source L156-166, with `slp` fixed at 0.0.

        Walks BACKWARD from `from_bar - 1` and returns the FIRST bar whose
        low (bear) / high (bull) reaches `level`, or -1. Pine addresses those
        bars as `low[o]` with `o = bar_index - fromBar + k`, i.e. bar
        `from_bar - k`; that indirection is what this rewrite removes."""
        lim = max(1, min(max_back, from_bar - to_bar))
        for k in range(1, lim + 1):
            b = from_bar - k
            o = j - b
            # Pine reads na for an out-of-range history offset, and every
            # comparison against na is false -- so both guards are `continue`.
            if b < 0 or o < 0 or o > _MAX_BARS_BACK:
                continue
            if (bear and l[b] <= level) or ((not bear) and h[b] >= level):
                return b
        return -1

    def _cross_fwd(j, p):
        """Pine f_crossFwd, source L276-289, with the neckline constant.

        First bar AFTER the pattern's last point at which price actually
        touched the neckline; defaults to the confirmation bar. Called only
        at confirmation, where `bar_index == p.confBar`, so the scan never
        reads beyond bar `j`."""
        last_b = p["last_bar"]
        conf_bar = p["conf_bar"]
        lim = max(1, conf_bar - last_b)
        for k in range(1, lim + 1):
            b = last_b + k
            if j - b < 0:
                continue
            if (p["dir"] == -1 and l[b] <= p["neck"]) or \
               (p["dir"] == 1 and h[b] >= p["neck"]):
                return b
        return conf_bar

    def _new_pat(kind, direction, neck, apex, apex_bar, invalid, ext,
                 born_bar, start_bar, last_bar):
        """Pine f_newPat, source L114-132, minus every drawing handle and
        minus `neckSlope`/`neckX` (constant-neckline collapse, see the
        module docstring). `start_bar`/`last_bar` stand in for Pine's
        `p.px[0]` / `p.px[m-1]`, the only two points `f_regionTaken` and
        `f_crossFwd` ever read."""
        pats.append({
            "kind": kind, "dir": direction, "neck": neck, "apex": apex,
            "apex_bar": apex_bar, "invalid": invalid, "ext": ext,
            "born_bar": born_bar, "start_bar": start_bar,
            "last_bar": last_bar, "conf_bar": -1, "target": np.nan,
            "confirmed": False, "result": 0,
        })

    def _match_high(j, tol):
        """Pine f_matchHigh, source L169-221 -- DOUBLE TOP branch ONLY
        (L200-221). The H&S branch (L172-199) is NOT ported; see the module
        docstring, this is NOT behaviour-neutral."""
        m = len(zz_d)
        if m < 3:
            return
        h1, l1, h2 = zz_p[m - 3], zz_p[m - 2], zz_p[m - 1]
        h1_bar = zz_b[m - 3]
        # Pine v6: `int / int` is a FLOAT division; `int()` truncates toward
        # zero. `int(x / 2)`, not `x // 2` -- they differ for negative x.
        leg_w = max(3, int((zz_b[m - 1] - h1_bar) / 2))
        to_bar = zz_b[max(0, m - 4)]
        cross_b = _cross_bar(j, h1_bar, to_bar, l1, True, 2 * leg_w)
        if cross_b >= 0:
            start_b = cross_b
        elif m >= 4:
            start_b = zz_b[m - 4]
        else:
            start_b = h1_bar
        trail_bar = zz_b[m - 1] + leg_w
        if not (abs(h1 - h2) <= tol):
            return
        if not (dbl_mode == "any" or h2 <= h1 + tol * 0.25):
            return
        if not (min(h1, h2) - l1 > 1.5 * tol):
            return
        if _region_taken(start_b, trail_bar):
            return
        ex = max(h1, h2)
        _new_pat(1, -1, l1, (h1 + h2) / 2.0, zz_b[m - 1], ex, ex,
                 j, start_b, zz_b[m - 1])

    def _match_low(j, tol):
        """Pine f_matchLow, source L222-273 -- DOUBLE BOTTOM branch ONLY
        (L253-273). The inverse-H&S branch (L225-252) is NOT ported."""
        m = len(zz_d)
        if m < 3:
            return
        l1, h1, l2 = zz_p[m - 3], zz_p[m - 2], zz_p[m - 1]
        l1_bar = zz_b[m - 3]
        leg_w = max(3, int((zz_b[m - 1] - l1_bar) / 2))
        to_bar = zz_b[max(0, m - 4)]
        cross_b = _cross_bar(j, l1_bar, to_bar, h1, False, 2 * leg_w)
        if cross_b >= 0:
            start_b = cross_b
        elif m >= 4:
            start_b = zz_b[m - 4]
        else:
            start_b = l1_bar
        trail_bar = zz_b[m - 1] + leg_w
        if not (abs(l1 - l2) <= tol):
            return
        if not (dbl_mode == "any" or l2 >= l1 - tol * 0.25):
            return
        if not (h1 - max(l1, l2) > 1.5 * tol):
            return
        if _region_taken(start_b, trail_bar):
            return
        ex = min(l1, l2)
        _new_pat(2, 1, h1, (l1 + l2) / 2.0, zz_b[m - 1], ex, ex,
                 j, start_b, zz_b[m - 1])

    # --- engine, Pine L323-416. Pine gates the whole block on
    # `barstate.isconfirmed`; every bar of a historical frame is confirmed,
    # so the gate is the identity here.
    for j in range(n):
        atr_j = a[j]
        tol = atr_j * tol_atr
        buf = atr_j * buf_atr
        vtol = tol + atr_j * void_atr

        # Pine L330-335: the HIGH pivot is pushed and matched BEFORE the low
        # pivot on a bar that confirms both. Order is load-bearing (it
        # decides which of the two claims the region first).
        if ph[j] == ph[j]:
            if _zz_push(j - pivots, ph[j], 1):
                _match_high(j, tol)
        if pl[j] == pl[j]:
            if _zz_push(j - pivots, pl[j], -1):
                _match_low(j, tol)

        i = 0
        while i < len(pats):
            p = pats[i]
            gone = False
            if not p["confirmed"]:
                neck_now = p["neck"]          # f_neckAt collapses: slope == 0
                if p["dir"] == -1:
                    if h[j] > p["ext"] + vtol:
                        gone = True
                    elif (l[j] if mode == "wick" else c[j]) < neck_now - buf:
                        p["confirmed"] = True
                else:
                    if l[j] < p["ext"] - vtol:
                        gone = True
                    elif (h[j] if mode == "wick" else c[j]) > neck_now + buf:
                        p["confirmed"] = True
                if not gone and not p["confirmed"] and \
                        j - p["born_bar"] > max_wait:
                    gone = True
                if p["confirmed"]:
                    p["conf_bar"] = j
                    neck_c = p["neck"]
                    if p["dir"] == -1:
                        height = p["apex"] - neck_c
                        p["target"] = neck_c - height
                    else:
                        height = neck_c - p["apex"]
                        p["target"] = neck_c + height
                    # f_draw is NOT ported, but its two STATE mutations
                    # (Pine L294-295) are: the forward-cross point is
                    # appended to p.px, which moves p.px[m-1] and therefore
                    # changes what `f_regionTaken` blocks afterwards.
                    p["last_bar"] = _cross_fwd(j, p)
                    if p["dir"] == -1:
                        conf_bear[j] = 1.0
                    else:
                        conf_bull[j] = 1.0
                    # UNSIGNED magnitude: direction lives in the two flags,
                    # so this column carries only "how far the measured
                    # target sits from the break price". On the (rare) bar
                    # where two patterns confirm, the LARGER distance wins --
                    # deterministic and independent of pattern birth order.
                    if c[j] != 0.0 and c[j] == c[j]:
                        _d = abs((p["target"] - c[j]) / c[j])
                        if _d > tgt[j]:
                            tgt[j] = _d
            elif p["result"] == 0:
                if p["dir"] == -1:
                    if l[j] <= p["target"]:
                        p["result"] = 1
                    elif c[j] >= p["invalid"]:
                        p["result"] = 2
                else:
                    if h[j] >= p["target"]:
                        p["result"] = 1
                    elif c[j] <= p["invalid"]:
                        p["result"] = 2
                if p["result"] == 0 and j - p["conf_bar"] > track_bars:
                    p["result"] = 3
                # Pine L381/L383 also bumps the per-run res/hits counters
                # here. Those are aggregates over the whole run, not per-bar
                # features, and are NOT ported.
                if p["result"] == 1:
                    res[j] += 1.0
                elif p["result"] == 2:
                    res[j] -= 1.0
                # result == 3 (timeout) is a NON-event for the feature and
                # emits nothing; the state machine still records it, which
                # is what stops the pattern being tracked further.
            if gone:
                pats.pop(i)
            else:
                i += 1

        # Pine L400-416: cap CONFIRMED patterns, oldest first.
        cnt = 0
        for p in pats:
            if p["confirmed"]:
                cnt += 1
        while cnt > max_keep:
            idx = -1
            for k, p in enumerate(pats):
                if p["confirmed"]:
                    idx = k
                    break
            if idx >= 0:
                pats.pop(idx)
            cnt -= 1

        if j >= warm:
            npend = 0.0
            for p in pats:
                if not p["confirmed"]:
                    npend += p["dir"]
            pend[j] = npend

    conf_bear = Series(conf_bear, index=close.index)
    conf_bull = Series(conf_bull, index=close.index)
    tgt = Series(tgt, index=close.index)
    pend = Series(pend, index=close.index)
    res = Series(res, index=close.index)
    out = [conf_bear, conf_bull, tgt, pend, res]

    if offset != 0:
        out = [s.shift(offset) for s in out]

    if "fillna" in kwargs:
        for s in out:
            s.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        for s in out:
            s.fillna(method=kwargs["fill_method"], inplace=True)

    conf_bear, conf_bull, tgt, pend, res = out
    _props = f"_{pivots}_{tol_atr}_{buf_atr}"
    conf_bear.name = f"DTDB_CONF_BEAR{_props}"
    conf_bull.name = f"DTDB_CONF_BULL{_props}"
    tgt.name = f"DTDB_TGT_PCT{_props}"
    pend.name = f"DTDB_PEND{_props}"
    res.name = f"DTDB_RES{_props}"

    df = DataFrame({s.name: s for s in
                    (conf_bear, conf_bull, tgt, pend, res)})
    df.name = f"DTDB{_props}"
    df.category = "trend"
    return df


dtdb.__doc__ = """Double Top / Double Bottom (DTDB)

The first CHART-PATTERN SHAPE MATCHER in this fork. A confirmed pivot
zigzag is matched against the two-peak / two-trough template, and the
resulting candidate is then carried FORWARD, bar by bar, until one of
three things happens: price breaks the neckline by an ATR buffer (the
pattern CONFIRMS), price runs past the pattern's own extreme by a
tolerance (the pattern is VOIDED), or a bar budget expires (the pattern
TIMES OUT). Nothing is emitted at the pattern's own pivots -- the
confirmation event is written on the neckline-break bar and nowhere else.

Ported from the TradingView Pine v6 source "Chart Patterns [FEELS]"
(`docs/TradingView/pine/z8Jv04Q7-Chart-Patterns-FEELS.pine` in the
consuming repo; `wc -l` = 438, file IS newline-terminated, so 438 content
lines -- both counts verified by reading the file, not assumed).

Columns (props suffix = `_{pivots}_{tol_atr}_{buf_atr}`, default
`_8_0.5_0.15`):

  DTDB_CONF_BEAR  0/1, set on the bar a DOUBLE TOP breaks its neckline.
                  0.0 on every other bar; NaN for the first `2 * pivots`
                  bars, where no pivot can have confirmed yet.
  DTDB_CONF_BULL  0/1, the DOUBLE BOTTOM mirror.
  DTDB_TGT_PCT    the MEASURED TARGET published as a SCALE-FREE, UNSIGNED
                  distance: `|target - close| / close` on a confirmation
                  bar, 0.0 elsewhere. The target PRICE is never emitted.
                  Direction is NOT duplicated here -- it lives in the two
                  flags above.
  DTDB_PEND       net PENDING (matched, not yet confirmed, not yet
                  voided) pattern count at the close of the bar: `+1` per
                  live Double Bottom, `-1` per live Double Top.
  DTDB_RES        outcome of a CONFIRMED pattern, written on the bar it
                  resolves: +1 measured target reached, -1 invalidated,
                  summed over patterns resolving that bar. 0.0 elsewhere.

AGGREGATION on a bar where more than one pattern fires: the two CONF
flags are 0/1 and SATURATE (two simultaneous double tops still read 1.0);
`TGT_PCT` takes the LARGEST distance, which is order-independent; `RES`
SUMS, so a bar on which one pattern hit its target and another was
invalidated nets to 0.0. `f_regionTaken` makes simultaneity uncommon but
NOT impossible -- two patterns in non-overlapping regions can resolve on
the same bar. MEASURED by instrumenting this module over 40 BIST daily
frames / 155,745 bars: 593 confirmations landed on 591 distinct bars (2
bars carried two), and 544 resolutions landed on 537 distinct bars (7
carried more than one). So the `RES` net-to-zero case is possible and
was not observed to dominate; it is disclosed, not assumed away.

=== THE COLUMN THAT WAS BUILT, MEASURED AND REMOVED ==================

An earlier revision of this module shipped `DTDB_CONF` as a single
SIGNED column (-1 double top / +1 double bottom) alongside a SIGNED
`DTDB_TGT` = `(target - close) / close`. Measured on 12 BIST daily
frames / 44,917 pooled bars, that pair correlated

    DTDB_CONF x DTDB_TGT    spearman rho = +0.9380    n = 44,725

which is above this project's revert precedent (`iama` reverted at 0.95;
candidate 16 self-reverted two columns at 0.934/0.999). The redundancy
was structural: a signed magnitude is nonzero exactly where its own
signed flag is, and carries the same sign almost everywhere.

The fix was to DECOMPOSE rather than delete: direction moved into two 0/1
flags (the convention every sibling module in this fork already uses --
`APUSH_BULL`/`APUSH_BEAR`, `IFVG_CONF_BULL`/`_BEAR`), and the magnitude
became UNSIGNED. Re-measured on 40 frames / 155,745 bars, the worst
internal pair is now

    DTDB_CONF_BULL x DTDB_TGT_PCT   rho = +0.7829
    DTDB_CONF_BEAR x DTDB_TGT_PCT   rho = +0.6207

with every other internal pair under |0.006|. The remaining 0.78 is
IRREDUCIBLE and is disclosed rather than engineered away: `TGT_PCT` is
nonzero on exactly the union of the two flags' fire bars, so a rank
correlation of that order is what a magnitude column paired with its own
event flag MUST produce. It sits inside this project's
ship-with-disclosure band (`PRESSURE_PULSE` 0.8045, `TRI_DIR_PRESSURE`
0.760), and the magnitude is genuinely incremental -- it lets a miner
write `TGT_PCT > x` as a strictly stronger condition than the bare flag.

⚠ ONE THING WAS LOST in that decomposition, and it is not nothing. With
a signed target the sign DISAGREED with the pattern direction on 22 of
591 confirmation bars (3.7%) across those 40 frames: a break bar that
gaps straight through the neckline AND past the measured target has
`target - close` pointing the OTHER way. That "already overshot its own
target on the break bar" state is no longer recoverable from
`TGT_PCT`.

=== WHAT IS NOT PORTED, AND WHERE THAT IS NOT NEUTRAL ================

1. HEAD & SHOULDERS / INVERSE H&S ARE NOT PORTED, AND DROPPING THEM
   CHANGES THE DOUBLE-TOP OUTPUT. This is a DELIBERATE, DOCUMENTED
   DIVERGENCE. Do not "fix" it into equivalence.

   The source matches H&S FIRST and lets it SUPPRESS the double top on
   the same pivot window (L200: `if n >= 3 and showDT and not matched5`;
   the mirror is L253 for the double bottom). With the H&S branch gone,
   `matched5` is permanently false, the guard is vacuous, and a 5-pivot
   window the source would have consumed as an H&S is instead tested as
   a double top on its last three pivots. MORE double tops fire here
   than the source produces.

   Second, independent mechanism: `f_regionTaken` (L139-153) scans the
   `pats` array across ALL pattern kinds, not just its own. With no H&S
   or inverse-H&S patterns ever entering that pool, the occupied-region
   set is strictly smaller, so DT/DB candidates the source would have
   rejected as overlapping are admitted here. That AGAIN admits more
   double tops.

   Net: this module reproduces the source ONLY under
   `showHS = false, showIHS = false`. It is NOT equivalent to the
   source's SHIPPED configuration, whose defaults are `showHS = true`
   and `showIHS = true` (L18-19).

2. THE SLOPED NECKLINE IS DELETED OUTRIGHT -- and this is the real
   structural win from the DT/DB-only split, not the ~58 lines of shape
   test. The sloped neckline exists ONLY for H&S: the double top passes
   `f_newPat(1, -1, l1, 0.0, ...)` (L211) and the double bottom passes
   `0.0` (L264), and both call `f_crossBar` with `slp = 0.0` (L206,
   L259). So `neckSlope` and `neckX` are dead fields for DT/DB, and
   `f_neckAt` (L84-85) -- `p.neck + p.neckSlope * (b - p.neckX)` --
   collapses to the constant `p.neck`. Removing them removes an entire
   class of bar-index off-by-one arithmetic from the two functions where
   this port's risk is concentrated (`f_crossBar`, `f_crossFwd`).

3. `f_draw` (L291-311) is NOT ported -- EXCEPT ITS TWO STATE MUTATIONS,
   which are. This is the subtle one. `f_draw` is nominally a drawing
   routine, but L294-295 mutate engine state that later matching reads:

       f_addPt(p, tb, f_neckAt(p, tb))
       p.trailB := math.max(p.trailB, tb)

   The first appends the forward neckline-cross bar to the pattern's
   point array, which MOVES `p.px[m - 1]` forward from the last pivot
   bar to that cross bar -- and `p.px[m - 1]` is exactly what
   `f_regionTaken` reads as `pe`. Confirming a pattern therefore ENLARGES
   the region it blocks. That mutation IS ported (`p["last_bar"] =
   _cross_fwd(...)`), and `f_crossFwd` (L276-289) is ported with it,
   solely because of this. The second, `p.trailB`, is read only by the
   `line.new` at L307 and is genuinely drawing-only; it is dropped.

4. NOT PORTED, no behavioural consequence: `f_delete` (L313-321, pure
   drawing-handle cleanup -- the `array.remove(pats, ...)` beside every
   call IS ported), every `line.new` / `box` / `label.new`, the hit-rate
   table (L418-433), and the four `alertcondition` calls (L435-438).

5. THE RUNNING HIT-RATE COUNTERS `res` / `hits` (L381, L383) ARE NOT
   PORTED. They are per-RUN aggregates, not per-bar features: emitting a
   running hit rate as a column would leak the outcome distribution of
   the whole series backward into every bar. Dropped on purpose.

6. Pine's outcome tri-state `1 = target / 2 = invalidated / 3 = timeout`
   (L366-378) IS implemented in the state machine -- the timeout branch
   is what stops a stale confirmed pattern being tracked. But `1/2/3` is
   a CATEGORICAL code, not an ordinal quantity, so it is not published
   raw. `DTDB_RES` publishes the ordered part of it (+1 target / -1
   invalidated) and emits 0 for a timeout, which is a non-event.

7. `maxKeep` (L400-416) IS ported. It evicts the oldest CONFIRMED
   pattern once more than `max_keep` are held, which shrinks the
   region-occupancy set and therefore admits later patterns -- state,
   not display, despite the input's "keep the chart clean" tooltip.

=== CAUSALITY =========================================================

A pattern is BORN on the bar its third pivot CONFIRMS -- that is
`bar_index` in `f_newPat` (L125), i.e. `pivots` bars after the pivot
itself. It CONFIRMS on a later bar still, and RESOLVES later than that.
Every write in this module is at the index of the bar carrying the
information, never back-dated to the pattern's pivots or apex. The
source's own drawings ARE back-dated (`line.new` from `p.coreS`,
`label.new` at `p.apexBar`) -- that display back-dating is precisely
what this port does not ship.

`tests/test_dtdb.py` proves this with a REAL-vs-MUTANT prefix-truncation
table rather than an assertion: an `importlib` + `exec` copy of this
module with the write site moved from `j` to `p["apex_bar"]` diverges
from its own truncated run, on co-populated bars, while the real module
does not.

=== SCALE-FREE ========================================================

No column carries a price level. `DTDB_CONF_BULL`, `DTDB_CONF_BEAR`,
`DTDB_PEND` and `DTDB_RES`
are counts; `DTDB_TGT_PCT` is the measured target as a fraction of the
confirming close. Every threshold inside the matcher is ATR-scaled
(`tol = atr * tol_atr`, `buf = atr * buf_atr`, `vtol = tol + atr *
voidTol`), exactly as in the source, so the whole pipeline is invariant
to multiplying all prices by a constant. Pinned by
`test_scale_free_under_price_rescale`, which also asserts the columns are
non-degenerate so invariance cannot be bought with a constant column.

`DTDB_TGT_PCT` guards `close == 0` (and NaN close) before dividing; the
source never divides by price at all, since it plots a target LEVEL.

=== TIMEFRAME SENSITIVITY (not a bug) =================================

`max_wait` (60) and `track_bars` (120) are BAR COUNTS, not durations, and
so is `pivots` (8). On an hourly frame 60 bars is roughly a week of
sessions; on a daily frame it is roughly three months. Pattern yield,
and the mix of confirmed / voided / timed-out, therefore differ
materially between 1d and 1h feeds of the same instrument. That is
inherited from the source, which is likewise bar-indexed, and is a
parameterization to set per timeframe -- not a defect.

=== PIVOT RULE AND ATR PROVENANCE =====================================

`_confirm_pivots` is IMPORTED from `pandas_ta.trend.zigzag_fib` rather
than copied. That deliberately breaks this package's self-contained-
module convention, and the reason is in that helper's own docstring: the
rule is RIGHTMOST-TIE-WINS, chosen because requiring strict uniqueness
"over-suppresses genuine ties like double-tops" -- which is this
module's entire subject. Two implementations of that rule already exist
(`zigzag_fib` and `swing_equilibrium`, verified equivalent in logic,
different in shape); a third copy would be a third thing to keep in sync
on a rule that has already been through three rounds of regression fixes.
It is NOT identical to Pine's `ta.pivothigh` / `ta.pivotlow`, whose
tie-breaking is unspecified in the Pine reference.

`atr` here is this fork's `pandas_ta.volatility.atr` (`ewm(alpha=1/n,
adjust=True)`), not Pine's recursive Wilder `ta.atr`. They differ during
warm-up and converge; `tests/test_atr_push.py::
test_atr_smoothing_deviates_from_pine_only_during_warmup` pins the
measured gap. Following the fork's ATR is deliberate -- every sibling
module in this package reads the same one.

Sources:
    https://www.tradingview.com/script/z8Jv04Q7/
    Local: docs/TradingView/pine/z8Jv04Q7-Chart-Patterns-FEELS.pine

Calculation:
    Default Inputs:
        pivots=8, tol_atr=0.5, buf_atr=0.15, void_atr=0.0, max_wait=60,
        track_bars=120, max_keep=12, atr_length=14, mode="close",
        dbl_mode="any"

    atr  = ATR(atr_length)
    tol  = atr * tol_atr        # "two tops are equal" tolerance
    buf  = atr * buf_atr        # neckline break buffer
    vtol = tol + atr * void_atr # how far past the extreme voids it

    Zigzag: confirmed pivot highs/lows pushed with alternation; a
    same-direction, more-extreme pivot EXTENDS the last leg in place and
    does NOT re-trigger matching (Pine f_zzPush, L88-112).

    Double Top on the last three pivots (h1, l1, h2):
        |h1 - h2| <= tol
        and (dbl_mode == "any" or h2 <= h1 + tol * 0.25)
        and min(h1, h2) - l1 > 1.5 * tol
        and not region_taken(start_bar, trail_bar)
      neck  = l1 ; apex = (h1 + h2) / 2 ; ext = invalid = max(h1, h2)

    Double Bottom mirrors it on (l1, h1, l2).

    Each bar thereafter, for each unconfirmed pattern:
        void    if high > ext + vtol            (bear; mirror for bull)
        confirm if close < neck - buf           (mode="wick": low)
        void    if bar - born_bar > max_wait
      On confirmation: target = neck -+ (apex - neck), i.e. the measured
      move projected from the neckline.

    Each bar thereafter, for each confirmed, unresolved pattern:
        result 1 if low  <= target       (bear; mirror for bull)
        result 2 if close >= invalid
        result 3 if bar - conf_bar > track_bars

Args:
    high (pd.Series): Series of 'high's
    low (pd.Series): Series of 'low's
    close (pd.Series): Series of 'close's
    pivots (int): Pivot width on each side (Pine `pivLen`). Must be >= 3.
        Default: 8
    tol_atr (float): "Two tops are equal" tolerance in ATR (Pine `tolIn`).
        Default: 0.5
    buf_atr (float): Neckline break buffer in ATR (Pine `bufIn`).
        Default: 0.15
    void_atr (float): Extra room past the extreme before a forming
        pattern is discarded, in ATR (Pine `voidTol`). Default: 0.0
    max_wait (int): Bars a forming pattern may wait for its neckline
        break. Default: 60
    track_bars (int): Bars a confirmed pattern is followed for its
        outcome. Default: 120
    max_keep (int): Confirmed patterns retained before the oldest is
        evicted. Default: 12
    atr_length (int): ATR length. Default: 14
    mode (str): "close" (bar must CLOSE beyond the neckline) or "wick"
        (an intrabar pierce confirms). Default: "close"
    dbl_mode (str): "any", or "weaker" for the classic momentum-failure
        form only (second peak not higher than the first). Default: "any"
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.DataFrame: DTDB_CONF_BULL, DTDB_CONF_BEAR, DTDB_PEND, DTDB_RES,
        DTDB_TGT_PCT columns (five).
"""
