# -*- coding: utf-8 -*-
import math

import numpy as np
from pandas import DataFrame, Series

from pandas_ta.volatility.atr import atr
from pandas_ta.utils import get_offset, verify_series


def _validated_int(value, default, name, positive=True):
    """None -> default (a normal, documented default, not bad input).
    Anything else must be a genuine, finite, integral value, or raise.
    Duplicated verbatim from `bdi4kewl.py`'s/`rejection_blocks.py`'s/
    `sr_force.py`'s helper of the same name (checks NaN/inf/non-integral
    explicitly before ever calling `int()`, so every rejection path is the
    same ValueError, not a mix of ValueError/OverflowError/silent
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


def _validated_float(value, default, name, nonneg=True):
    """Same nan/inf discipline as `_validated_int`, float variant.
    Duplicated verbatim from `bdi4kewl.py`'s helper of the same name."""
    if value is None:
        return default
    if isinstance(value, bool):
        raise ValueError(f"{name} must be a{' non-negative' if nonneg else ''} float, got bool {value!r}")
    try:
        value = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{name} must be a{' non-negative' if nonneg else ''} float, got {value!r}")
    if value != value:
        raise ValueError(f"{name} must be finite, got NaN")
    if abs(value) == float("inf"):
        raise ValueError(f"{name} must be finite, got inf")
    if nonneg and value < 0:
        raise ValueError(f"{name} must be >= 0, got {value}")
    return value


class _Fvg:
    """One detected, not-yet-inverted Fair Value Gap. Mirrors the source's
    `type fvg` UDT minus nothing -- all four of its fields are real state
    (`top`, `bottom`, `startIndex`, `isBull`)."""
    __slots__ = ("top", "bottom", "start_index", "is_bull")

    def __init__(self, top, bottom, start_index, is_bull):
        self.top = top
        self.bottom = bottom
        self.start_index = start_index
        self.is_bull = is_bull


class _Ifvg:
    """One CONFIRMED inverse-FVG zone. Mirrors the source's `type ifvgObj`
    with its three drawing-object fields (`bx` box, `ln` centerline,
    `lbl` price label) dropped -- pure state, no chart I/O."""
    __slots__ = ("top", "bottom", "is_bull", "mitigated")

    def __init__(self, top, bottom, is_bull, mitigated=False):
        self.top = top
        self.bottom = bottom
        self.is_bull = is_bull
        self.mitigated = mitigated


def inverse_fvg(high, low, close, atr_len=None, vol_mult=None, max_fvg_age=None,
                max_ifvg=None, offset=None, **kwargs):
    """Indicator: Inverse Fair Value Gap (IFVG)"""
    atr_len = _validated_int(atr_len, 14, "atr_len")
    vol_mult = _validated_float(vol_mult, 0.3, "vol_mult")
    max_fvg_age = _validated_int(max_fvg_age, 1000, "max_fvg_age")
    max_ifvg = _validated_int(max_ifvg, 10, "max_ifvg")

    # 3 bars for the gap pattern itself; atr_len because the `atr()` call
    # below does its OWN independent verify_series(atr_len) check and
    # returns None (not a NaN-filled Series) on a too-short frame, which
    # would crash `.to_numpy()` even after a smaller local floor passed --
    # same reasoning as `liquidity_sweep.py`'s min_len comment.
    min_len = max(3, atr_len)
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

    conf_bull = np.zeros(n, dtype=int)
    conf_bear = np.zeros(n, dtype=int)
    mit_bull = np.zeros(n, dtype=int)
    mit_bear = np.zeros(n, dtype=int)
    dist_sup = np.full(n, np.nan)
    dist_res = np.full(n, np.nan)

    active_fvgs = []   # list[_Fvg], source's `activeFvgs`; .push == append
    active_ifvgs = []  # list[_Ifvg], source's `activeIfvgs`; .unshift == insert(0, ..)

    for t in range(n):
        # --- 1. Detection of new FVGs (source lines 235-243). The
        # threshold is ATR(atr_len) at the CURRENT bar times vol_mult; a
        # NaN (unwarmed) ATR makes `gap > threshold` False, so no FVG is
        # detected during warmup -- matching Pine, where a na threshold
        # makes the `if` condition false. ---
        if t >= 2:
            threshold = atr_v[t] * vol_mult
            if low_v[t] > high_v[t - 2]:
                gap = low_v[t] - high_v[t - 2]
                if gap > threshold:
                    active_fvgs.append(_Fvg(low_v[t], high_v[t - 2], t - 2, True))
            if high_v[t] < low_v[t - 2]:
                gap = low_v[t - 2] - high_v[t]
                if gap > threshold:
                    active_fvgs.append(_Fvg(low_v[t - 2], high_v[t], t - 2, False))

        # --- 2. Process existing FVGs for INVERSION (source lines
        # 247-294). Descending iteration with in-place removal, exactly as
        # the source does (`for i = activeFvgs.size() - 1 to 0` +
        # `.remove(i)`), so index-based removal never disturbs a
        # not-yet-visited lower index. A newly detected FVG is visited on
        # its own detection bar, same as the source's single sequential
        # per-bar script execution -- but can never invert on that bar:
        # a bull FVG requires low[t] > high[t-2] == bottom, and close >=
        # low, so close > bottom; the mirror argument holds for bear. ---
        for i in range(len(active_fvgs) - 1, -1, -1):
            item = active_fvgs[i]
            confirmed = False

            if item.is_bull:
                if close_v[t] < item.bottom:
                    # Inversion confirmed -> BEARISH IFVG (resistance):
                    # a bullish gap that price closed back down through.
                    active_ifvgs.insert(0, _Ifvg(item.top, item.bottom, False))
                    conf_bear[t] = 1
                    confirmed = True
                elif high_v[t] < item.bottom:
                    # ⚠ PROVABLY UNREACHABLE in the source and here:
                    # close <= high always, so `high < bottom` implies
                    # `close < bottom` and the branch above already fired.
                    # Ported literally anyway rather than dropped as dead
                    # code -- a faithful translation of the source's own
                    # control flow, matching this fork's convention (see
                    # `bdi4kewl.py`'s `candidate_age >= pivot_right`
                    # guard, likewise always-true and likewise kept). It
                    # would only become live on malformed OHLC where
                    # close > high.
                    confirmed = True
            else:
                if close_v[t] > item.top:
                    # Inversion confirmed -> BULLISH IFVG (support):
                    # a bearish gap that price closed back up through.
                    active_ifvgs.insert(0, _Ifvg(item.top, item.bottom, True))
                    conf_bull[t] = 1
                    confirmed = True
                elif low_v[t] > item.top:
                    # Same provable unreachability, mirrored (low <= close).
                    confirmed = True

            if confirmed or (t - item.start_index) > max_fvg_age:
                active_fvgs.pop(i)

        # --- 3. Mitigation of confirmed IFVGs (source lines 298-319; the
        # box/line/label coordinate updates in that block are drawing-only
        # and are dropped). A just-confirmed IFVG is visited this same bar
        # but can never mitigate on it: a bull IFVG confirms on close >
        # top and mitigates on close < bottom < top. ---
        for ifv in active_ifvgs:
            if ifv.mitigated:
                continue
            if ifv.is_bull:
                if close_v[t] < ifv.bottom:
                    ifv.mitigated = True
                    mit_bull[t] = 1
            else:
                if close_v[t] > ifv.top:
                    ifv.mitigated = True
                    mit_bear[t] = 1

        # --- 4. Strict FIFO limiting (source lines 322-327): keep only
        # the `max_ifvg` most recently confirmed zones, newest at index 0,
        # dropping from the END (oldest). The source pops regardless of
        # mitigation state, as here. ---
        while len(active_ifvgs) > max_ifvg:
            active_ifvgs.pop()

        # --- 5. Scale-free distance columns (this port's OWN addition,
        # not source math -- see docstring). Nearest UNMITIGATED zone of
        # each polarity whose CENTERLINE sits on the correct side of
        # close; the centerline is the source's own emphasized level (it
        # draws and price-labels `midY = (top + bottom) / 2` for every
        # confirmed IFVG). Side-constrained before the argmin, following
        # `liquidity_sweep.py`'s Fletcher MAJOR fix, so both columns are
        # >= 0 whenever populated. ---
        c = close_v[t]
        sup_best = np.nan
        res_best = np.nan
        for ifv in active_ifvgs:
            if ifv.mitigated:
                continue
            mid = (ifv.top + ifv.bottom) / 2.0
            if ifv.is_bull:
                if mid < c and (np.isnan(sup_best) or (c - mid) < (c - sup_best)):
                    sup_best = mid
            else:
                if mid > c and (np.isnan(res_best) or (mid - c) < (res_best - c)):
                    res_best = mid
        if not np.isnan(sup_best) and c != 0:
            dist_sup[t] = (c - sup_best) / c * 100
        if not np.isnan(res_best) and c != 0:
            dist_res[t] = (res_best - c) / c * 100

    conf_bull_s = Series(conf_bull, index=close.index)
    conf_bear_s = Series(conf_bear, index=close.index)
    mit_bull_s = Series(mit_bull, index=close.index)
    mit_bear_s = Series(mit_bear, index=close.index)
    dist_sup_s = Series(dist_sup, index=close.index)
    dist_res_s = Series(dist_res, index=close.index)

    _all = (conf_bull_s, conf_bear_s, mit_bull_s, mit_bear_s, dist_sup_s, dist_res_s)

    if offset != 0:
        conf_bull_s = conf_bull_s.shift(offset)
        conf_bear_s = conf_bear_s.shift(offset)
        mit_bull_s = mit_bull_s.shift(offset)
        mit_bear_s = mit_bear_s.shift(offset)
        dist_sup_s = dist_sup_s.shift(offset)
        dist_res_s = dist_res_s.shift(offset)
        _all = (conf_bull_s, conf_bear_s, mit_bull_s, mit_bear_s, dist_sup_s, dist_res_s)

    if "fillna" in kwargs:
        for s in _all:
            s.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        for s in _all:
            s.fillna(method=kwargs["fill_method"], inplace=True)

    _props = f"_{atr_len}"
    conf_bull_s.name = f"IFVG_CONF_BULL{_props}"
    conf_bear_s.name = f"IFVG_CONF_BEAR{_props}"
    mit_bull_s.name = f"IFVG_MIT_BULL{_props}"
    mit_bear_s.name = f"IFVG_MIT_BEAR{_props}"
    dist_sup_s.name = f"IFVG_DIST_SUP{_props}"
    dist_res_s.name = f"IFVG_DIST_RES{_props}"

    df = DataFrame({
        conf_bull_s.name: conf_bull_s,
        conf_bear_s.name: conf_bear_s,
        mit_bull_s.name: mit_bull_s,
        mit_bear_s.name: mit_bear_s,
        dist_sup_s.name: dist_sup_s,
        dist_res_s.name: dist_res_s,
    })
    df.name = f"IFVG{_props}"
    df.category = "trend"

    return df


inverse_fvg.__doc__ = \
"""Inverse Fair Value Gap (IFVG)

A Fair Value Gap (3-bar imbalance) that price later closes back THROUGH
flips polarity: the gap that failed as continuation becomes a zone of the
OPPOSITE bias. A bullish FVG whose lower edge is closed below becomes a
BEARISH IFVG (overhead resistance); a bearish FVG whose upper edge is
closed above becomes a BULLISH IFVG (support). Each confirmed IFVG is
then tracked until MITIGATION -- a close back through its far edge, i.e.
the inversion itself failing.

Only gaps larger than `ATR(atr_len) * vol_mult` are admitted, so the
detector ignores micro-imbalances and keys on displacement-sized ones.

Source: TradingView community indicator "Liquidity Sweeps & Inverse FVGs
[LuxAlgo]" by LuxAlgo, https://www.tradingview.com/script/GC3Vxs8n/
(ported into AwakenAnalytics/Backtesting TVPTA-6 candidate 14,
2026-08-14; MPL-2.0, per the source file's own header). Ports the
source's INVERSE-FVG half in full: the volatility-filtered FVG detection
block, the inversion state machine that promotes a detected FVG to a
confirmed IFVG zone (both polarities), the post-confirmation mitigation
check, and the FIFO cap on tracked zones.

⚠ THE LIQUIDITY-SWEEP HALF WAS DELIBERATELY NOT PORTED -- scope decision,
not an oversight. The source is a dual system: an `piv`-object liquidity-
sweep tracker (arrays of pivot objects flagged broken/mitigated/wicked,
source lines ~131-224) alongside the IFVG tracker (lines ~231-327). The
sweep half is a near-duplicate of this fork's already-shipped
`trend/liquidity_sweep.py` (`LSH_SWEEP_BULL/BEAR`,
`LSH_RECLAIM_BULL/BEAR`, `LSH_DIST_RES/SUP`): both take `ta.pivothigh`/
`ta.pivotlow` swings into a per-side pool of level objects; both resolve a
level either as a WICK SWEEP (`high > level and close < level` on the
swing-high side -- the source's `get.wic := true` branch, LSH's
`is_sweep`) or as a BREAK-THEN-RECLAIM (`close` through the level flags
`brk`/`broken`, a later opposite close resolves it -- the source's
`get.tak := true` branch, LSH's `reclaim`); both age levels out
(source: `n - get.bix > 2000`, LSH: `max_age`) and remove a level from the
pool once resolved. The differences are parameterization, not mechanism
(the source hard-codes its age cap and has no ATR-penetration filter,
where LSH exposes `max_age`/`atr_mult`, and the source's three-way `opt`
input toggles wick-only / reclaim-only / both, which LSH exposes as
`mode`). Re-porting it would ship a second, slightly-worse copy of six
columns that already exist. Only the IFVG half is genuinely new here.

⚠ NOT PORTED (display/alerting only, no signal math): every `box.new`/
`line.new`/`label.new` call and their per-bar coordinate updates
(`set_right`/`set_x2`/`set_x`), including the centerline and its
mintick-formatted price label; the `showIfvg` toggle (an unconditional
display gate -- this port always computes); the `.delete()` calls in the
FIFO trim (this port drops the object, there is nothing to erase); the
two `alert()` calls (each is a boolean this port already ships as a
column -- `IFVG_CONF_BULL`/`IFVG_CONF_BEAR`); all color inputs.

⚠ `maxIfvgDisplay` -> `max_ifvg`, default RAISED from the source's 1 to
10. The source's own tooltip calls it a display limit ("Limits the number
of active IFVGs shown on the chart to keep it clean"), and it caps ONE
combined array across both polarities -- at its default of 1 the script
tracks a single zone at a time regardless of direction, which would make
both distance columns here alternate between polarities and sit NaN most
of the time. Ported as a state-pool cap instead; `max_ifvg=1` reproduces
the source's own behaviour exactly. Everything else (the 1000-bar FVG age
cap, the 0.3 ATR multiplier, ATR(14)) is at the source's literal default.

⚠ Two `else if` branches in the source are PROVABLY UNREACHABLE and are
ported literally anyway (see the inline comments): `else if high <
item.bottom` on the bull-FVG side can only be reached when `close >=
bottom`, but `close <= high < bottom` contradicts that; the bear-side
mirror (`else if low > item.top`) is the same argument with `low <=
close`. They can only ever fire on malformed OHLC where close sits
outside [low, high]. Kept as a faithful translation of the source's
control flow rather than an algebraically-reduced equivalent, matching
this fork's convention (see `bdi4kewl.py`'s always-true
`candidate_age >= pivot_right` guard).

⚠ CAUSALITY: an IFVG's flag is written at the bar its inversion is
CONFIRMED, never back-dated to the gap bar. The source's own `box.new(
item.startIndex, ...)` draws the zone back to the gap's origin bar for
display -- that back-dated rectangle is exactly what this port does NOT
ship. `item.start_index` is used here only for the age cap, never to
write a value into a past row. Everything read on bar `t` is `high[t]`,
`low[t]`, `close[t]`, `high[t-2]`, `low[t-2]`, `ATR[t]`, plus state
accumulated from strictly earlier bars.

⚠ The `atr()` primitive is this fork's own implementation (RMA-based, the
`mamode` default matching Pine's `ta.atr`), not Pine's `ta.atr`; their
warmup/seeding conventions can differ over the first `atr_len` bars. This
is the same project-wide caveat every other TVPTA port composing a
borrowed primitive carries.

⚠ Relationship to this fork's existing `fvg()` and `fvg_sweep_magnet()`:
`fvg()` detects plain 3-bar gaps and reports whether price sits INSIDE an
unfilled one (no volatility filter, no polarity flip). `fvg_sweep_magnet()`
gates FVGs on displacement and arms them as magnet targets after a
liquidity sweep. Neither implements INVERSION -- the promotion of a failed
gap into an opposite-polarity zone -- which is what this module adds. This
port deliberately does not re-detect gaps in a new way: its detection
block is the source's own, differing from `fvg()`'s mainly by the
ATR-scaled size filter.

Calculation:
    Default Inputs:
        atr_len=14, vol_mult=0.3, max_fvg_age=1000, max_ifvg=10
    Each bar t (t >= 2), threshold = ATR(atr_len)[t] * vol_mult:
        BULLISH FVG if low[t] > high[t-2] and (low[t] - high[t-2]) >
            threshold -> zone (bottom=high[t-2], top=low[t]).
        BEARISH FVG if high[t] < low[t-2] and (low[t-2] - high[t]) >
            threshold -> zone (bottom=high[t], top=low[t-2]).
    Every tracked, not-yet-inverted FVG is then checked (newest first):
        a BULLISH FVG with close[t] < its bottom INVERTS -> a BEARISH IFVG
            zone (same top/bottom), IFVG_CONF_BEAR = 1 at t.
        a BEARISH FVG with close[t] > its top INVERTS -> a BULLISH IFVG
            zone (same top/bottom), IFVG_CONF_BULL = 1 at t.
        an inverted FVG leaves the FVG pool; so does one older than
            max_fvg_age bars (measured from its gap-origin bar, t-2 at
            detection).
    Every confirmed, not-yet-mitigated IFVG is then checked:
        a BULLISH IFVG (support) with close[t] < its bottom is MITIGATED,
            IFVG_MIT_BULL = 1 at t.
        a BEARISH IFVG (resistance) with close[t] > its top is MITIGATED,
            IFVG_MIT_BEAR = 1 at t.
        Mitigated zones stay in the pool (frozen, matching the source)
            but never contribute to the distance columns again.
    The IFVG pool is then FIFO-trimmed to the `max_ifvg` most recently
        confirmed zones.
    IFVG_DIST_SUP = (close - m) / close * 100 where m is the centerline
        ((top+bottom)/2) of the nearest unmitigated BULLISH IFVG with
        m < close; NaN if none qualifies. IFVG_DIST_RES = (m - close) /
        close * 100 over unmitigated BEARISH IFVGs with m > close; NaN if
        none qualifies. Both >= 0 whenever populated, by construction.

Args:
    high (pd.Series): Series of 'high's
    low (pd.Series): Series of 'low's
    close (pd.Series): Series of 'close's
    atr_len (int): ATR lookback for the gap-size filter. Must be a
        positive int if given. Default: 14
    vol_mult (float): Minimum gap size as a multiple of ATR. 0 admits
        every gap. Must be >= 0 if given. Default: 0.3
    max_fvg_age (int): Bars a detected-but-not-yet-inverted FVG is kept
        before expiring. Must be a positive int if given. Default: 1000
    max_ifvg (int): Max confirmed IFVG zones tracked (FIFO, newest kept).
        Must be a positive int if given. Default: 10 (the source's own
        default is 1, a display limit -- see above)
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Raises:
    ValueError: `atr_len`/`max_fvg_age`/`max_ifvg` given and not a
        positive, finite, integral value (NaN, +-inf, non-integral floats
        and bools all raise); `vol_mult` given and not a finite value
        >= 0. `None` (the default sentinel) still means "use the
        default," not an error.

Returns:
    pd.DataFrame: IFVG_CONF_BULL, IFVG_CONF_BEAR (0/1, written on the
        inversion-confirmation bar), IFVG_MIT_BULL, IFVG_MIT_BEAR (0/1,
        written on the mitigation bar), IFVG_DIST_SUP, IFVG_DIST_RES
        (percent distance to the nearest active zone centerline on that
        side, NaN when none qualifies), each suffixed `_{atr_len}`.
"""
