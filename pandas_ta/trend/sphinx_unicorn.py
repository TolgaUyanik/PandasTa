# -*- coding: utf-8 -*-
import numpy as np
from pandas import DataFrame, Series

from pandas_ta.utils import get_offset, verify_series


def _confirm_strict_pivots(series, left, right, is_high):
    """Causal pivot confirmation matching Pine's `ta.pivothigh`/
    `ta.pivotlow`: a bar at position i confirms (becomes visible at
    j=i+right) iff it is the STRICT, UNIQUE extreme of the window
    [i-left, i+right]. Duplicated from `equal_highs_lows.py`'s identical
    helper rather than imported, matching this package's convention of
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


def _find_nested_fvg(high_v, low_v, swing_bar, probe, radius, strict, is_bull_setup):
    """Search backward from `swing_bar` (inclusive) for the nearest 3-bar
    FVG whose price range the swing price (`probe`) sits inside, and that
    is still OPEN (unfilled) as of the swing bar. Returns (top, bot) or
    (nan, nan). Absolute bar-index arithmetic -- see the module docstring
    for the derivation from the source's Pine relative-offset form.

    Bullish FVG (BISI): high[gap_start] < low[gap_end], range (bot=high[
    gap_start], top=low[gap_end]). Bearish FVG (SIBI): low[gap_start] >
    high[gap_end], range (bot=high[gap_end], top=low[gap_start])."""
    for d in range(0, radius + 1):
        gap_end = swing_bar - d
        gap_start = swing_bar - d - 2
        if gap_start < 0:
            break
        if is_bull_setup:
            t, b = low_v[gap_end], high_v[gap_start]
            valid = b < t
        else:
            t, b = low_v[gap_start], high_v[gap_end]
            valid = b < t
        if np.isnan(t) or np.isnan(b) or not valid:
            continue
        hit = (probe > b and probe < t) if strict else (probe >= b and probe <= t)
        if not hit:
            continue
        # Filled check: has price already traded back through the gap
        # between its formation and the swing bar (exclusive of the
        # formation bar itself, inclusive of the swing bar)?
        #
        # Fletcher CRITICAL catch: an earlier version of this line read
        # `lo = gap_end - d + 1`, which is `swing_bar - 2*d + 1` -- an
        # extra `-d` that drags the scan back INTO the gap's own bars
        # (gap_start..gap_end) for any d >= 3, where the gap's own low
        # is (almost always) below its own high, so the gap declares
        # itself filled. Net effect: only gaps ending within ~2 bars of
        # the swing could ever match; fvg_look behaved like fvg_look=2
        # regardless of the actual parameter. Re-derived from the Pine
        # source directly: `for k = off0 to i-1` in Pine-relative terms
        # maps to the absolute range [swing_bar-d+1, swing_bar] --
        # exactly `gap_end+1` to `swing_bar` (gap_end = swing_bar-d), no
        # second `d` term.
        filled = False
        lo = gap_end + 1
        hi = swing_bar
        for k in range(max(lo, 0), hi + 1):
            ref = low_v[k] if is_bull_setup else high_v[k]
            if np.isnan(ref):
                continue
            if (is_bull_setup and ref < b) or (not is_bull_setup and ref > t):
                filled = True
                break
        if not filled:
            return t, b
    return np.nan, np.nan


def _find_disp_fvg(high_v, low_v, t_bar, is_bull_setup, nz_t, nz_b, lookback, min_sz, ratio):
    """Balanced Price Range check: does a same-direction gap, formed in
    the `lookback` bars up to and including `t_bar`, overlap the nesting
    FVG [nz_b, nz_t] by at least a hair and clear the size floor? True/
    False. Absolute bar-index form of the source's `find_disp_fvg`.

    The overlap test is `overlap > 0` (strictly positive), not Pine's
    `ov >= syminfo.mintick` -- a second, independent `mintick`
    substitution alongside `disp_min_pct` (the module docstring's mintick
    paragraph covers `disp_min_pct` only, not this one), admitting a
    fractional-float overlap Pine's one-tick floor would reject.
    Deliberately not tied to `min_sz`/`disp_min_pct`
    (which floors the gap's own SIZE, a different quantity from how much
    it overlaps the nesting zone) -- left as `> 0` rather than inventing
    a second undocumented threshold."""
    nest_sz = nz_t - nz_b
    need_sz = max(min_sz, ratio * nest_sz)
    for d in range(0, lookback + 1):
        gap_end = t_bar - d
        gap_start = t_bar - d - 2
        if gap_start < 0:
            break
        if is_bull_setup:
            t, b = low_v[gap_end], high_v[gap_start]
            valid = b < t
        else:
            t, b = low_v[gap_start], high_v[gap_end]
            valid = b < t
        if np.isnan(t) or np.isnan(b) or not valid:
            continue
        overlap = min(t, nz_t) - max(b, nz_b)
        gap = t - b
        if overlap > 0 and gap >= need_sz:
            return True
    return False


def sphinx_unicorn(high, low, close, swing=None, fvg_look=None, strict=None,
                    need_disp=None, need_bpr=None, bpr_look=None,
                    disp_min_pct=None, disp_ratio=None, offset=None, **kwargs):
    """Indicator: Sphinx Unicorn FVG Breaker/BPR Nesting Model"""
    swing = int(swing) if swing and swing > 0 else 2
    fvg_look = int(fvg_look) if fvg_look and fvg_look > 0 else 20
    strict = bool(strict) if strict is not None else True
    need_disp = bool(need_disp) if need_disp is not None else True
    need_bpr = bool(need_bpr) if need_bpr is not None else True
    bpr_look = int(bpr_look) if bpr_look and bpr_look > 0 else 6
    disp_min_pct = float(disp_min_pct) if disp_min_pct and disp_min_pct > 0 else 0.01
    disp_ratio = float(disp_ratio) if disp_ratio and disp_ratio > 0 else 0.75

    min_len = 2 * swing + fvg_look + 5
    high = verify_series(high, min_len)
    low = verify_series(low, min_len)
    close = verify_series(close, min_len)
    offset = get_offset(offset)

    if high is None or low is None or close is None: return

    n = len(close)
    high_v = high.to_numpy(dtype=float)
    low_v = low.to_numpy(dtype=float)
    close_v = close.to_numpy(dtype=float)

    ph = _confirm_strict_pivots(high, swing, swing, is_high=True)
    pl = _confirm_strict_pivots(low, swing, swing, is_high=False)

    arm_bull = np.zeros(n, dtype=int)
    arm_bear = np.zeros(n, dtype=int)
    fire_bull = np.zeros(n, dtype=int)
    fire_bear = np.zeros(n, dtype=int)
    dist_bull = np.full(n, np.nan)
    dist_bear = np.full(n, np.nan)

    # Simplified vs. source: the source keeps an 8-zone ring buffer per
    # direction and clusters new swings against BOTH LEVEL (demoted) and
    # ARMED zones -- this port tracks only the single CURRENTLY ARMED
    # zone per direction (matching equal_highs_lows's precedent: "track
    # only the MOST RECENTLY FORMED level" rather than the source's
    # unbounded/ring-buffered array). See the module docstring for the
    # measured consequence and why this follows the source's own stated
    # design intent rather than a probable bug in its actual code.
    armed_top = [np.nan, np.nan]     # [bear, bull] -- NOTE: opposite of the source's z_armed slot order (source: 0=bull via _arm(0)/z_armed[0], 1=bear via _arm(1)/z_armed[1]); this port's [0]=bear/[1]=bull is internal-only, never compared against the source's array
    armed_bot = [np.nan, np.nan]
    armed_swing = [np.nan, np.nan]

    for t in range(n):
        swing_bar = t - swing

        # --- BEARISH setup: swing LOW nested in a bullish FVG (BISI) ---
        if swing_bar >= 0 and not np.isnan(pl[t]):
            top, bot = _find_nested_fvg(high_v, low_v, swing_bar, pl[t], fvg_look, strict, is_bull_setup=True)
            if not np.isnan(top):
                cur_top, cur_bot = armed_top[0], armed_bot[0]
                clustered = (not np.isnan(cur_top)) and (min(cur_top, top) - max(cur_bot, bot) > 0)
                if not clustered:
                    armed_top[0], armed_bot[0], armed_swing[0] = top, bot, pl[t]
                    arm_bear[t] = 1
                else:
                    cur_span = cur_top - cur_bot
                    new_span = top - bot
                    if new_span > cur_span:
                        armed_top[0], armed_bot[0] = top, bot
                    armed_swing[0] = pl[t]

        # --- BULLISH setup: swing HIGH nested in a bearish FVG (SIBI) ---
        if swing_bar >= 0 and not np.isnan(ph[t]):
            top, bot = _find_nested_fvg(high_v, low_v, swing_bar, ph[t], fvg_look, strict, is_bull_setup=False)
            if not np.isnan(top):
                cur_top, cur_bot = armed_top[1], armed_bot[1]
                clustered = (not np.isnan(cur_top)) and (min(cur_top, top) - max(cur_bot, bot) > 0)
                if not clustered:
                    armed_top[1], armed_bot[1], armed_swing[1] = top, bot, ph[t]
                    arm_bull[t] = 1
                else:
                    cur_span = cur_top - cur_bot
                    new_span = top - bot
                    if new_span > cur_span:
                        armed_top[1], armed_bot[1] = top, bot
                    armed_swing[1] = ph[t]

        # --- ACTIVATION ---
        if not np.isnan(armed_top[0]):
            swp, zt, zb = armed_swing[0], armed_top[0], armed_bot[0]
            need = min(swp, zb) if need_disp else swp
            dist_bear[t] = (close_v[t] - need) / close_v[t] * 100
            go = close_v[t] < need
            bpr = True
            if go and need_bpr:
                bpr = _find_disp_fvg(high_v, low_v, t, False, zt, zb, bpr_look, disp_min_pct / 100.0 * close_v[t], disp_ratio)
            if go and bpr:
                fire_bear[t] = 1
                armed_top[0] = armed_bot[0] = armed_swing[0] = np.nan

        if not np.isnan(armed_top[1]):
            swp, zt, zb = armed_swing[1], armed_top[1], armed_bot[1]
            need = max(swp, zt) if need_disp else swp
            dist_bull[t] = (close_v[t] - need) / close_v[t] * 100
            go = close_v[t] > need
            bpr = True
            if go and need_bpr:
                bpr = _find_disp_fvg(high_v, low_v, t, True, zt, zb, bpr_look, disp_min_pct / 100.0 * close_v[t], disp_ratio)
            if go and bpr:
                fire_bull[t] = 1
                armed_top[1] = armed_bot[1] = armed_swing[1] = np.nan

    arm_bull = Series(arm_bull, index=close.index)
    arm_bear = Series(arm_bear, index=close.index)
    fire_bull = Series(fire_bull, index=close.index)
    fire_bear = Series(fire_bear, index=close.index)
    dist_bull = Series(dist_bull, index=close.index)
    dist_bear = Series(dist_bear, index=close.index)

    if offset != 0:
        arm_bull = arm_bull.shift(offset)
        arm_bear = arm_bear.shift(offset)
        fire_bull = fire_bull.shift(offset)
        fire_bear = fire_bear.shift(offset)
        dist_bull = dist_bull.shift(offset)
        dist_bear = dist_bear.shift(offset)

    if "fillna" in kwargs:
        for s in (arm_bull, arm_bear, fire_bull, fire_bear, dist_bull, dist_bear):
            s.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        for s in (arm_bull, arm_bear, fire_bull, fire_bear, dist_bull, dist_bear):
            s.fillna(method=kwargs["fill_method"], inplace=True)

    _props = f"_{swing}"
    arm_bull.name = f"SPHINX_ARM_BULL{_props}"
    arm_bear.name = f"SPHINX_ARM_BEAR{_props}"
    fire_bull.name = f"SPHINX_FIRE_BULL{_props}"
    fire_bear.name = f"SPHINX_FIRE_BEAR{_props}"
    dist_bull.name = f"SPHINX_DIST_BULL{_props}"
    dist_bear.name = f"SPHINX_DIST_BEAR{_props}"

    df = DataFrame({
        arm_bull.name: arm_bull,
        arm_bear.name: arm_bear,
        fire_bull.name: fire_bull,
        fire_bear.name: fire_bear,
        dist_bull.name: dist_bull,
        dist_bear.name: dist_bear,
    })
    df.name = f"SPHINX{_props}"
    df.category = "trend"

    return df


sphinx_unicorn.__doc__ = \
"""Sphinx Unicorn FVG Breaker/BPR Nesting Model

An SMC/ICT "unicorn" setup detector: a confirmed swing pivot nested inside
an OPPOSING-polarity Fair Value Gap (a swing LOW inside a bullish FVG for a
bearish setup, a swing HIGH inside a bearish FVG for a bullish setup) arms
a watched breaker level. It activates (fires) when price closes beyond
both the swing and the FVG's far edge, optionally gated by a Balanced
Price Range check (the breaking leg must itself leave a comparably-sized
same-direction gap overlapping the level it reclaims).

Source: TradingView community indicator "Sphinx Unicorn - FVG Breaker
Nesting Model" by TheHermeticTrader, https://www.tradingview.com/script/
IJ4sFGcU-Sphinx-Unicorn-FVG-Breaker-Nesting-Model/ (ported into
AwakenAnalytics/Backtesting TVPTA-6, 2026-08-10; MPL-2.0 per TradingView's
open-source publication convention).

⚠ Simplified versus the source, deliberately: the source keeps an 8-slot
ring buffer of zones per direction (states LEVEL/ARMED/ACTIVE/SPENT) and
clusters each new qualifying swing against every LEVEL-or-ARMED zone still
in the buffer, not just the current ARMED one. This port tracks only the
single currently-ARMED zone per direction -- matching this package's
`equal_highs_lows` precedent ("track only the MOST RECENTLY FORMED level"
rather than an unbounded/ring-buffered array). Practical consequence: a
new swing that would have re-clustered into an old DEMOTED (LEVEL) zone
in the source instead arms a fresh zone here.

⚠ This simplification follows the source's DOCUMENTED intent, not its
literal code: the source's own header comment states "Promotion is
one-way ... A demoted LEVEL never re-arms" -- but `_cluster_of` (the
clustering test) checks LEVEL-or-ARMED zones together, and the "existing
cluster" branch DOES re-promote a matched LEVEL zone back to ARMED
(`if array.get(z_st, cl) == 0: array.set(z_st, cl, 1)`), directly
contradicting that comment. This looks like an unintended behavior in the
source rather than the author's actual design, and chasing bug-for-bug
fidelity to it would require reproducing the full ring buffer for
uncertain benefit -- this port follows the stated design ("never
re-arms") instead.

Two concrete consequences of this divergence, so "arms a fresh zone
here" isn't read as behavioral equivalence: (1) in the source, that
re-promotion ALSO raises `arm_bull`/`arm_bear` for the re-clustered
swing -- this port emits no arm signal on the bars where the source's
literal code would. (2) The source's re-promotion repoints `z_armed` at
the OLD zone's (already-established) top/bot, not the new swing's own
range -- so its subsequent `need` threshold is computed from a different
price range than the freshly-armed zone this port creates, and the
OLD zone in the source is left stranded in state ARMED but no longer
tracked by anything, permanently unable to fire (itself further evidence
the source's behavior is unintended, not designed). This divergence is
untestable in this port by construction -- there is no ring buffer here
to exhibit the source's literal behavior against.

⚠ `min_ticks`/`syminfo.mintick` (a secondary floor under the source's real
gate, its own comment: "The ratio is the real gate") has no equivalent in
a headless OHLCV frame -- BIST's actual tick table isn't available here.
Replaced with `disp_min_pct` (default 0.01%), a price-relative floor
serving the same "don't let a near-zero-size gap qualify" role.

⚠ `syminfo`/REACH (550): verified NOT reachable for this script's actual
call pattern -- `off0` in `find_bisi`/`find_sibi` is always exactly
`swing` (bounded 1-15 by the source's own input range), never close to
REACH, so the REACH-clamp branch is dead code here and not ported.

Not a duplicate of this fork's existing `fvg()` (also in `pandas_ta/trend/`):
that indicator tracks which currently-open gaps price sits inside RIGHT
NOW; this one asks a different, backward-looking question per swing --
"was a specific historical gap still open AT THE TIME a given swing
formed, and does the swing nest inside it" -- so its internals (`_find_
nested_fvg`/`_find_disp_fvg`) are not interchangeable with `fvg()`'s.

NOT ported: the state-machine's ACTIVE->SPENT mitigation tracking (chart
color only, ACTIVE/SPENT zones never participate in future clustering
per the source's own `_cluster_of`, so dropping them changes nothing
observable), all box/label/line rendering, the diagnostic table, and the
alert wrappers (`alertcondition` calls carry no additional math beyond the
arm/fire booleans this port already computes).

Calculation:
    Default Inputs:
        swing=2, fvg_look=20, strict=True, need_disp=True, need_bpr=True,
        bpr_look=6, disp_min_pct=0.01, disp_ratio=0.75
    Confirmed pivot high/low via strict-unique-extreme rule (`ta.pivothigh`/
        `ta.pivotlow` semantics, see `_confirm_strict_pivots`).
    On each new confirmed swing, search backward up to `fvg_look` bars for
        the nearest still-open (unfilled) opposing-polarity FVG containing
        the swing price (`_find_nested_fvg`). If found and it does not
        overlap the currently-armed zone in that direction: demote the old
        zone (if any) and arm the new one. If it overlaps: keep the larger
        span seen, update the watched swing to the newest.
    Each bar with an armed zone: need = swing price, or swing-vs-FVG-edge
        combined if need_disp. DIST = (close - need) / close * 100.
        FIRE (and clear the armed slot) when close crosses need AND
        (if need_bpr) a same-direction displacement gap overlapping the
        zone, at least disp_ratio x its size, formed within bpr_look bars.

Args:
    high (pd.Series): Series of 'high's
    low (pd.Series): Series of 'low's
    close (pd.Series): Series of 'close's
    swing (int): Bars either side required for a pivot. Default: 2
    fvg_look (int): How far back from a swing to search for its nesting
        FVG. Default: 20
    strict (bool): Swing must sit strictly inside the FVG (not touching
        an edge). Default: True
    need_disp (bool): Activation needs a close beyond the FVG's far edge
        too, not just the swing. Default: True
    need_bpr (bool): Require the Balanced Price Range displacement-gap
        check. Default: True
    bpr_look (int): BPR displacement search window, bars. Default: 6
    disp_min_pct (float): Minimum displacement gap size, % of price (this
        port's stand-in for the source's tick-based floor). Default: 0.01
    disp_ratio (float): Displacement gap size, as a multiple of the
        nesting gap it inverts. Default: 0.75
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.DataFrame: SPHINX_ARM_BULL, SPHINX_ARM_BEAR, SPHINX_FIRE_BULL,
        SPHINX_FIRE_BEAR, SPHINX_DIST_BULL, SPHINX_DIST_BEAR.
"""
