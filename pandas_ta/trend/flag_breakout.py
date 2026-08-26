# -*- coding: utf-8 -*-
"""Flag Pattern Breakout (FLAG) -- port of TradingView `tMHhzI6j`.

Source: `docs/TradingView/pine/tMHhzI6j-Flag-Pattern-Breakout-Dots3Red.pine`
(`wc -l` 398, `grep -c ''` 399 -- the final line `barcolor(C_BAR)` is
unterminated, so 399 CONTENT lines; both counts measured 2026-08-26).
`//@version=6`, MPL-2.0, (c) Dots3Red.

WHY `trend` AND NOT `volatility`.  `datastore/source/pine_candidates_
families.csv` files this slug under `family=volatility` because its
`primary_fn` is `atr`.  That is a reading of the SOURCE'S IMPORTS, not of
its OUTPUT, and this module deliberately disagrees with it:

  * every ATR reference in the source is a SCALE NORMALISER, never a
    measurement being emitted -- the staff height floor (L136), the
    minimum edge slope (L253/L293) and the breakout buffer (L259/L299)
    each divide a price quantity by ATR so that a threshold can be
    written as a dimensionless multiple.  Nothing this module emits is a
    dispersion statistic.
  * the PAYLOAD is a directional structure event: a straight-line
    impulse (R^2 of a linreg through closes, L100-119), a counter-sloped
    consolidation channel (L199-210), and a DIRECTIONAL close-break out
    of that channel (L259 bull / L299 bear).
  * every sibling chart-structure detector already in this fork sits
    under `trend` -- `dtdb`, `bos`, `choch`, `zigzag`, `zigzag_fib`,
    `sphinx_unicorn`, `swing_equilibrium`.  `volatility/range_profile.py`
    is under `volatility` because its payload IS a dispersion/occupancy
    statistic; this one is not the same kind of thing.

The CSV row is left with `family=volatility` (it records the survey's
call, and the survey is a historical document); the disagreement is
recorded in that row's `tvpta3_reason` note instead.

WHAT IS PORTED

  * L100-119 `f_window_r2` -- R^2 of an ordinary least-squares fit of
    `close` against bar ordinal over a `lookback+1`-bar window.  This is
    the "straightness" gate on the flagpole.
  * L121-150 `f_find_staff_rising` and L152-180 `f_find_staff_falling`
    -- the LONGEST-WINDOW-FIRST search for the pole.  For each
    `lookback` from `staff_max_bars` DOWN to `staff_min_bars`, a window
    qualifies when (a) its directional height clears `staff_min_atr *
    ATR` (L136 / L166), (b) at most `staff_max_opposite` bars inside it
    break the direction with a full non-overlap (L138-141 / L168-171),
    and (c) its R^2 clears `staff_min_r2` (L143 / L173).  The FIRST
    (longest) qualifying window wins and the search `break`s.
  * L195-196 `f_new_edge`, L199-210 `f_update_slope`, L212-220
    `f_update_extremes` -- the flag itself.  It is a PARALLEL channel
    whose single shared slope comes from INCREMENTAL least-squares sums
    (`n`, `sumX`, `sumY`, `sumXY`, `sumX2`) updated one bar at a time,
    with the upper rail pinned to the running highest high and the lower
    rail to the running lowest low.
  * L223-305 the two-sided state machine: seed on the staff's own end
    bar, extend, and then CONFIRM on an ATR-buffered close-break
    (L259 / L299), or ABANDON on width / age / slope-invalidity
    (L266 / L304).

WHAT IS NOT PORTED, and why (four distinct declines, not one block):

  1. L307-316 the `max_patterns` ring buffer.  It `array.shift`s the
     pattern array and deletes the shifted entry's lines and labels.
     TRACED, not assumed: `patterns` is WRITTEN only by the two
     `array.push` calls at L264/L302 and READ only by this shift block
     and by the visualisation loop at L349-398.  The DETECTION state is
     `tr_bull`/`st_bull`/`eg_bull` and their bear mirrors (L184-190),
     which the pattern array never feeds back into.  Dropping the array
     is therefore behaviour-neutral for everything this module emits,
     and `max_patterns` is not an argument here.
  2. L318-346 `f_get_envelope_bounds`.  It re-walks the confirmed
     pattern's bars to widen the two drawn rails to the pattern's actual
     high/low envelope.  It is called ONLY from the visualisation block
     (L367) and its outputs are only ever line endpoints.  It is also
     the one BACKWARD-LOOKING routine in the file, and its `up_start /
     up_end / lo_start / lo_end` are raw PRICES -- exactly the shape
     acceptance gate (d) forbids.  Declined in full.
  3. L349-398 the visualisation block -- `line.new`, `linefill.new`,
     `label.new`, the glow/fill colour triples, and `barcolor` at L399.
     Drawing only.  The label body at L380-385 is where the two
     descriptive quantities live (`staff.height / atr` in ATR units and
     `gap_final / atr`); the first of those IS emitted as a column, see
     `FLAG_POLE_ATR` below.  `gap_final` is NOT emitted: it is computed
     from `f_get_envelope_bounds` (declined at (2)) rather than from the
     tracked rails, so emitting it would require porting the declined
     routine.
  4. `zone_ext` (L61) -- a label x-offset in bars.  Drawing only.

RULE-5 (STATE IN DRAWING OBJECTS) -- TRACED, NOT GREPPED.  `line` and
`label` DO appear as type fields, at L93-96, but they are fields of
`FlagPattern`, which is constructed only at confirmation (L263/L301) and
read only by the visualisation loop.  The types that carry the DETECTION
state are `Staff` (L67-73: five `int`/`float` fields plus one `bool`,
`rising`) and `Edge` (L75-87: thirteen `int`/`float` fields), neither of
which has a drawing field.  Every predicate in the main loop
(L223-305) reads only `tr_*`, `st_*`, `eg_*`, `close`, `high`, `low` and
`atr_raw`.  No decision anywhere reads a `line` or `label`.  So the port
loses no state.  (Note the imprecision worth stating: `Staff` is not
purely `int`/`float` -- L73 is `bool rising`.  It is still not a drawing
field.)

NO BLOCKERS.  `grep -cE "request\\.security|input\\.session|timeframe\\.|
syminfo\\." <source>` returns **0** (re-run 2026-08-26).  There is no
higher-timeframe request, no session input, no symbol metadata: the port
needs no substitution of the kind `range_profile` needed for
`syminfo.mintick`.

`barstate.isconfirmed` (L222) gates the whole state machine.  On
historical bars in Pine every bar is confirmed, so on the bar series this
module is handed -- completed OHLCV rows -- it is a no-op.  It exists in
the source to stop the realtime, still-forming bar from mutating `var`
state; this module never sees a forming bar.

TWO ASYMMETRIES IN THE SOURCE, REPRODUCED DELIBERATELY.  These are not
typos this port silently "fixed"; a port that fixed them would not be
this indicator.

  a. THE WIDTH TEST DIFFERS BETWEEN THE TWO SIDES.  The bull side
     (L250) tests `too_wide_val = eg.hi_price - eg.lo_price`, the raw
     span between the tracked extremes, and the source carries the
     alternative `gap_now > ...` COMMENTED OUT on that same line.  The
     bear side (L288) tests `gap_now_b`, the span between the two
     SLOPE-PROJECTED rails at the current bar.  Those differ by
     `slope * (lo_bar - hi_bar)`, so the two sides are gated
     differently.  Reproduced exactly; `width_mode="source"` is the
     default.  `width_mode="raw"` / `"projected"` force one rule on both
     sides for anyone who wants the symmetric reading, and are NOT what
     the shipped columns use.
  b. THE BULL SIDE COMPUTES TWO DEAD LOCALS.  `edgeL` and `staffL`
     (L247-248) are assigned and never read; `gap_now` (L242) is
     computed and then only used by the commented-out branch.  They are
     simply absent here.

PINE-6 ARITHMETIC.  Nothing in the ported range does integer division:
the only `/` operators are `sumX * sumY / nf` and friends inside
`f_window_r2` (L115-118, all `float`), `edge_max_width_pct / 100.0`
(L250/L288, float literal), and `st.height / staff_bars` (L245/L283,
where `staff_bars` is explicitly `float(...)`).  So the v6 "`int / int`
yields a fractional value" rule never bites here and there is no v5
truncation to emulate either way.  `ta.stdev` does not appear in this
source at all (`grep -c 'ta\\.stdev'` -> 0), so the biased/unbiased
question does not arise.

FLOATING-POINT AND THE R^2 GATE.  `f_window_r2` accumulates five sums in
a Pine `for` loop, i.e. strictly sequentially.  This module computes the
same five sums with `numpy` over an explicit sliding window, whose
pairwise summation is a different associativity, so the two can differ by
~1 ulp.  That matters only if a window's R^2 lands within ~1e-16 of
`staff_min_r2`.  Unlike `range_profile`'s modal-bin argmax -- an EXACT-TIE
comparison, where the source text genuinely does not fix the answer --
this is a threshold comparison against a caller-chosen constant, and
`tests/test_flag_breakout.py::test_matches_a_literal_pine_order_
transliteration` runs a bar-for-bar sequential-accumulation reference
against the vectorised form and asserts the four emitted columns are
identical.  It is a pinned equality, not an assumption.

WHAT THIS EMITS (four columns; `_props` = `_{staff_max_bars}_
{staff_min_r2}_{breakout_atr_mult}`, e.g. `_12_0.85_0.15`):

  FLAG_CONF_BULL   1.0 on the bar a BULL flag breakout confirms (a rising
                   pole followed by a downward-sloped channel that the
                   close clears to the UPSIDE by `breakout_atr_mult *
                   ATR`), else 0.0.
  FLAG_CONF_BEAR   the mirror: falling pole, upward-sloped channel,
                   close breaks DOWN through the lower rail.
  FLAG_POLE_ATR    the pole's height divided by that bar's ATR, written
                   ON THE CONFIRMATION BAR ONLY, 0.0 elsewhere.  This is
                   the source's own `STAFF : x ATR` label quantity
                   (L382), and it is a dimensionless RATIO -- the pole's
                   two prices are never emitted.  It is >= `staff_min_atr`
                   wherever it is non-zero, by construction of the L136
                   gate, but not exactly equal to the label's value: the
                   label rounds to 1 decimal (`math.round(..., 1)`) and
                   divides by the ATR of the DRAWING bar, whereas this
                   divides by the ATR of the confirmation bar.
  FLAG_PEND        the live-tracking state AFTER bar `t` is processed:
                   +1 while a bull edge is being extended, -1 while a
                   bear edge is, 0 when neither, and their SUM (so 0)
                   when both.  This is the only DENSE column of the four
                   and the only one that answers "am I inside a
                   consolidation right now".

All four are NaN before the first bar at which ATR is finite (index 14
at the default `atr_length=14`, measured, because `atr` needs a prior
close for its first true range), and 0.0-or-event from there.

CAUSALITY.  A flag confirms AT THE BREAKOUT.  Every write in this module
lands on the bar being processed: `conf_*[t]`, `pole[t]` and `pend[t]`
are assigned inside the `t` iteration and no index other than `t` is ever
written.  Nothing is back-dated to the pole's bars or to the channel's
earlier bars -- which is precisely what the declined
`f_get_envelope_bounds` would have needed.  The staff search reads
`high`/`low`/`close` at `t - lookback .. t` only, and the edge update
reads bar `t` only.  The O(bars x window) longest-window-first loop is
therefore causal by construction, and
`tests/test_flag_breakout.py::test_truncating_the_frame_cannot_change_
earlier_bars` re-runs the module on every prefix of a synthetic frame and
asserts bar-for-bar equality on the overlap.

SCALE-FREEDOM.  No emitted column is a price.  Two are 0/1 event flags,
one is a small signed integer state, and `FLAG_POLE_ATR` is a
price/price ratio.  Every internal threshold is either dimensionless
(`staff_min_r2`, `edge_max_width_pct`, `max_edge_slope_ratio`) or an ATR
multiple.  The one place the source could have leaked scale --
`f_get_envelope_bounds`'s four raw price endpoints -- is declined.
`test_scale_invariance` multiplies the whole frame by 10 and by 8 (an
exact power of two, so the mantissa is untouched and the check is
bit-exact) and requires identical NaN masks, identical values, and
`0 < fires < n` on both flags.

DATA-INTEGRITY EXPOSURE (this engine's cache, not TradingView's feed).
This detector reads High and Low in three places -- the pole's height
(L133-135 / L163-165), the opposite-bar non-overlap count (L139/L169),
and the edge's tracked extremes (L212-220) -- while the R^2 straightness
gate reads CLOSE only.  So it is less High-exposed than a range or
profile detector but not immune.  Measured behaviour on the two frames
this project has escalated as contaminated is in the family page,
`docs/indicators/family-trend-overlay.md`; the headline is that the
column set is EVENT-SPARSE, so the realistic failure is a spurious
confirmation, not a blow-up in magnitude -- `FLAG_POLE_ATR` is bounded
below by `staff_min_atr` and above only by the data.

NO GUARD IS ADDED HERE.  `range_profile` added a `low <= close <= high`
coherence guard because a single absurd High could redefine an entire
50-bin profile's price range and thereby move EVERY emitted number on
that window.  This module has no such amplification: an absurd High
enters only additively, through one bar's height or one bar's tracked
extreme, and cannot rescale the other bars.  Adding a guard would also
change WHICH bars the pole search sees, i.e. change the pattern
inventory, which is a much larger deviation than the one it would fix.
The exposure is measured and published instead.
"""
import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from pandas import DataFrame, Series

from pandas_ta.volatility.atr import atr
from pandas_ta.utils import get_offset, verify_series


def _validated_int(value, default, name, positive=True):
    """None -> default (a normal, documented default, not bad input).
    Anything else must be a genuine, finite, integral value, or raise.
    Same helper, same rejection paths, as `dtdb.py`/`range_profile.py`."""
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
    v = str(value).lower()
    if v not in allowed:
        raise ValueError(f"{name} must be one of {allowed}, got {value!r}")
    return v


def _fmt(x):
    """`2.0 -> 2`, `0.85 -> 0.85` -- keeps column names short."""
    return int(x) if float(x).is_integer() else x


def _window_r2_grid(c, lookbacks):
    """R^2 of `close` against bar ordinal, for every (lookback, bar) pair.

    Pine `f_window_r2`, source L100-119, evaluated for all bars at once.
    Returns a dict `lookback -> np.ndarray of length n`, where entry `t`
    is the R^2 over `close[t-lookback .. t]` (so `lookback+1` points,
    x = 0..lookback) and entries with `t < lookback` are NaN.

    The five sums are taken over an EXPLICIT sliding window rather than
    from a long cumulative sum: `sumY2 - sumY*sumY/nf` is a cancelling
    difference, and differencing a cumsum that has run over thousands of
    bars would lose far more precision than the source's own 13-term
    loop does.  `sumX` and `sumX2` are closed forms of the same integer
    series Pine accumulates.
    """
    n = c.shape[0]
    out = {}
    for L in lookbacks:
        m = L + 1
        r2 = np.full(n, np.nan)
        if n < m:
            out[L] = r2
            continue
        win = sliding_window_view(c, m)            # (n-m+1, m)
        x = np.arange(m, dtype=float)
        nf = float(m)
        sumX = x.sum()
        sumX2 = (x * x).sum()
        sumY = win.sum(axis=1)
        sumY2 = (win * win).sum(axis=1)
        sumXY = (win * x).sum(axis=1)
        sxy = sumXY - sumX * sumY / nf
        sxx = sumX2 - sumX * sumX / nf
        syy = sumY2 - sumY * sumY / nf
        with np.errstate(invalid="ignore", divide="ignore"):
            v = np.where((sxx > 0.0) & (syy > 0.0), (sxy * sxy) / (sxx * syy), 0.0)
        # a window containing a NaN close yields NaN in Pine too (every
        # comparison against it is then false), so it is not forced to 0.
        v = np.where(np.isfinite(win).all(axis=1), v, np.nan)
        r2[L:] = v
        out[L] = r2
    return out


def flag_breakout(high, low, close, staff_min_atr=None, staff_min_bars=None,
                  staff_max_bars=None, staff_max_opposite=None,
                  staff_min_r2=None, edge_min_bars=None, edge_max_bars=None,
                  edge_max_width_pct=None, max_edge_slope_ratio=None,
                  min_slope_atr=None, breakout_atr_mult=None,
                  atr_length=None, width_mode=None, offset=None, **kwargs):
    """Indicator: Flag Pattern Breakout (FLAG)"""
    staff_min_atr = _validated_float(staff_min_atr, 2.0, "staff_min_atr")
    staff_min_bars = _validated_int(staff_min_bars, 2, "staff_min_bars")
    staff_max_bars = _validated_int(staff_max_bars, 12, "staff_max_bars")
    staff_max_opposite = _validated_int(staff_max_opposite, 1,
                                        "staff_max_opposite", positive=False)
    staff_min_r2 = _validated_float(staff_min_r2, 0.85, "staff_min_r2")
    edge_min_bars = _validated_int(edge_min_bars, 3, "edge_min_bars")
    edge_max_bars = _validated_int(edge_max_bars, 30, "edge_max_bars")
    edge_max_width_pct = _validated_float(edge_max_width_pct, 60.0,
                                          "edge_max_width_pct")
    max_edge_slope_ratio = _validated_float(max_edge_slope_ratio, 0.6,
                                            "max_edge_slope_ratio")
    min_slope_atr = _validated_float(min_slope_atr, 0.02, "min_slope_atr",
                                     positive=False)
    breakout_atr_mult = _validated_float(breakout_atr_mult, 0.15,
                                         "breakout_atr_mult", positive=False)
    atr_length = _validated_int(atr_length, 14, "atr_length")
    width_mode = _validated_choice(width_mode, "source", "width_mode",
                                   ("source", "raw", "projected"))
    offset = get_offset(offset)

    if staff_max_bars < staff_min_bars:
        raise ValueError("staff_max_bars must be >= staff_min_bars, got "
                         f"{staff_max_bars} < {staff_min_bars}")
    if edge_min_bars < 2:
        raise ValueError(f"edge_min_bars must be >= 2, got {edge_min_bars}")

    min_len = staff_max_bars + 2
    high = verify_series(high, min_len)
    low = verify_series(low, min_len)
    close = verify_series(close, min_len)
    if high is None or low is None or close is None:
        return

    n = len(close)
    h = high.to_numpy(dtype=float)
    l = low.to_numpy(dtype=float)
    c = close.to_numpy(dtype=float)
    a = atr(high, low, close, length=atr_length).to_numpy(dtype=float)

    lookbacks = list(range(staff_max_bars, staff_min_bars - 1, -1))

    # ---- staff predicates, vectorised -------------------------------
    # Pine's `high[k] <= low[k+1]` (L139) reads the LATER bar's high
    # against the EARLIER bar's low, i.e. the later bar sits entirely
    # below the earlier one -- a full downward non-overlap, which is the
    # "opposite" direction for a RISING staff.  L169 is its mirror.
    d_rise = np.zeros(n, dtype=np.int64)
    d_fall = np.zeros(n, dtype=np.int64)
    if n > 1:
        d_rise[1:] = (h[1:] <= l[:-1]).astype(np.int64)
        d_fall[1:] = (l[1:] >= h[:-1]).astype(np.int64)
    cum_rise = np.concatenate(([0], np.cumsum(d_rise)))
    cum_fall = np.concatenate(([0], np.cumsum(d_fall)))

    r2_grid = _window_r2_grid(c, lookbacks)

    idx = np.arange(n)
    rise_ok, fall_ok = {}, {}
    for L in lookbacks:
        ok_r = np.zeros(n, dtype=bool)
        ok_f = np.zeros(n, dtype=bool)
        if n > L:
            t = idx[L:]
            floor_ = a[t] * staff_min_atr
            # opposite count over bars t-L+1 .. t  (k = 0..L-1)
            opp_r = cum_rise[t + 1] - cum_rise[t - L + 1]
            opp_f = cum_fall[t + 1] - cum_fall[t - L + 1]
            r2 = r2_grid[L][t]
            with np.errstate(invalid="ignore"):
                ok_r[t] = ((h[t] - l[t - L]) >= floor_) & \
                          (opp_r <= staff_max_opposite) & (r2 >= staff_min_r2)
                ok_f[t] = ((h[t - L] - l[t]) >= floor_) & \
                          (opp_f <= staff_max_opposite) & (r2 >= staff_min_r2)
        rise_ok[L] = ok_r
        fall_ok[L] = ok_f

    conf_bull = np.full(n, np.nan)
    conf_bear = np.full(n, np.nan)
    pole = np.full(n, np.nan)
    pend = np.full(n, np.nan)
    finite_atr = np.flatnonzero(np.isfinite(a))
    warm = int(finite_atr[0]) if finite_atr.size else n
    for _arr in (conf_bull, conf_bear, pole, pend):
        _arr[warm:] = 0.0

    # ---- state (Pine L184-190) --------------------------------------
    # `Edge` is carried as a plain list so the incremental sums are
    # mutated in place exactly as Pine mutates the UDT's fields.
    # [start_bar, n, sumX, sumY, sumXY, sumX2, slope, hi_price, hi_bar,
    #  lo_price, lo_bar]
    S, N, SX, SY, SXY, SX2, SL, HP, HB, LP, LB = range(11)

    def _new_edge(s):
        return [s, 0, 0.0, 0.0, 0.0, 0.0, np.nan,
                np.nan, -1, np.nan, -1]

    def _update_slope(eg, bar_idx, y_val):
        """Pine `f_update_slope`, L199-210.  `slope` is only reassigned
        once `n >= 2` AND the normal-equation denominator is non-zero;
        otherwise the PREVIOUS slope survives, NaN included."""
        x = float(bar_idx - eg[S])
        eg[N] += 1
        eg[SX] += x
        eg[SY] += y_val
        eg[SXY] += x * y_val
        eg[SX2] += x * x
        if eg[N] >= 2:
            denom = eg[N] * eg[SX2] - eg[SX] * eg[SX]
            if denom != 0.0:
                eg[SL] = (eg[N] * eg[SXY] - eg[SX] * eg[SY]) / denom

    def _update_extremes(eg, bar_idx, hi_val, lo_val):
        """Pine `f_update_extremes`, L212-220.  `na(x) or v > x` keeps
        the FIRST bar's value when the tracked extreme is still unset."""
        if not np.isfinite(eg[HP]) or hi_val > eg[HP]:
            eg[HP] = hi_val
            eg[HB] = bar_idx
        if not np.isfinite(eg[LP]) or lo_val < eg[LP]:
            eg[LP] = lo_val
            eg[LB] = bar_idx

    tr_bull = False
    tr_bear = False
    eg_bull = None
    eg_bear = None
    st_bull_h = 0.0     # staff height
    st_bull_bars = 0.0  # end_bar - start_bar
    st_bear_h = 0.0
    st_bear_bars = 0.0

    for t in range(n):
        atr_t = a[t]

        # ── BULL SIDE (Pine L225-267) ────────────────────────────────
        if not tr_bull:
            for L in lookbacks:
                if t - L < 0:
                    continue
                if rise_ok[L][t]:
                    lo_p = l[t - L]
                    hi_p = h[t]
                    tr_bull = True
                    st_bull_h = hi_p - lo_p
                    st_bull_bars = float(L)
                    eg_bull = _new_edge(t)
                    _update_slope(eg_bull, t, hi_p)
                    _update_extremes(eg_bull, t, hi_p, hi_p)
                    break
        else:
            eg = eg_bull
            _update_slope(eg, t, h[t])
            _update_extremes(eg, t, h[t], l[t])

            upper_now = eg[HP] + eg[SL] * float(t - eg[HB])
            staff_slope = st_bull_h / st_bull_bars if st_bull_bars > 0 else 0.0

            # L250: the bull side tests the RAW extreme span.  The
            # projected form is on that same source line, commented out.
            if width_mode == "projected":
                span = (eg[HP] - eg[LP]) + eg[SL] * (eg[LB] - eg[HB])
            else:
                span = eg[HP] - eg[LP]
            too_wide = span > (edge_max_width_pct / 100.0) * st_bull_h
            too_old = (t - eg[S]) > edge_max_bars
            eligible = eg[N] >= edge_min_bars
            slope_negative = eg[SL] < -(min_slope_atr * atr_t)
            slope_shallow = abs(eg[SL]) <= max_edge_slope_ratio * staff_slope
            valid_slope = bool(slope_negative and slope_shallow)

            if eligible and valid_slope and \
                    c[t] > upper_now + breakout_atr_mult * atr_t:
                conf_bull[t] = 1.0
                pole[t] = st_bull_h / atr_t
                tr_bull = False
            elif too_wide or too_old or (eligible and not valid_slope):
                tr_bull = False

        # ── BEAR SIDE (Pine L269-305) ────────────────────────────────
        if not tr_bear:
            for L in lookbacks:
                if t - L < 0:
                    continue
                if fall_ok[L][t]:
                    hi_p = h[t - L]
                    lo_p = l[t]
                    tr_bear = True
                    st_bear_h = hi_p - lo_p
                    st_bear_bars = float(L)
                    eg_bear = _new_edge(t)
                    _update_slope(eg_bear, t, lo_p)
                    _update_extremes(eg_bear, t, lo_p, lo_p)
                    break
        else:
            eg = eg_bear
            _update_slope(eg, t, l[t])
            _update_extremes(eg, t, h[t], l[t])

            upper_now_b = eg[HP] + eg[SL] * float(t - eg[HB])
            lower_now_b = eg[LP] + eg[SL] * float(t - eg[LB])
            staff_slope = st_bear_h / st_bear_bars if st_bear_bars > 0 else 0.0

            # L288: the bear side tests the PROJECTED gap.  Asymmetry (a).
            if width_mode == "raw":
                span_b = eg[HP] - eg[LP]
            else:
                span_b = upper_now_b - lower_now_b
            too_wide_b = span_b > (edge_max_width_pct / 100.0) * st_bear_h
            too_old_b = (t - eg[S]) > edge_max_bars
            eligible_b = eg[N] >= edge_min_bars
            slope_positive = eg[SL] > (min_slope_atr * atr_t)
            slope_shallow_b = abs(eg[SL]) <= max_edge_slope_ratio * staff_slope
            valid_slope_b = bool(slope_positive and slope_shallow_b)

            if eligible_b and valid_slope_b and \
                    c[t] < lower_now_b - breakout_atr_mult * atr_t:
                conf_bear[t] = 1.0
                pole[t] = st_bear_h / atr_t
                tr_bear = False
            elif too_wide_b or too_old_b or (eligible_b and not valid_slope_b):
                tr_bear = False

        if t >= warm:
            pend[t] = (1.0 if tr_bull else 0.0) - (1.0 if tr_bear else 0.0)

    conf_bull = Series(conf_bull, index=close.index)
    conf_bear = Series(conf_bear, index=close.index)
    pole = Series(pole, index=close.index)
    pend = Series(pend, index=close.index)
    out = [conf_bull, conf_bear, pole, pend]

    if offset != 0:
        out = [s.shift(offset) for s in out]

    if "fillna" in kwargs:
        for s in out:
            s.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        for s in out:
            s.fillna(method=kwargs["fill_method"], inplace=True)

    conf_bull, conf_bear, pole, pend = out
    _props = (f"_{staff_max_bars}_{_fmt(staff_min_r2)}"
              f"_{_fmt(breakout_atr_mult)}")
    conf_bull.name = f"FLAG_CONF_BULL{_props}"
    conf_bear.name = f"FLAG_CONF_BEAR{_props}"
    pole.name = f"FLAG_POLE_ATR{_props}"
    pend.name = f"FLAG_PEND{_props}"

    df = DataFrame({s.name: s for s in (conf_bull, conf_bear, pole, pend)})
    df.name = f"FLAG{_props}"
    df.category = "trend"
    return df


flag_breakout.__doc__ = """Flag Pattern Breakout (FLAG)

A port of TradingView `tMHhzI6j` "Flag Pattern Breakout [Dots3Red]"
(MPL-2.0, (c) Dots3Red).  It detects the classic flag: a steep, straight
IMPULSE ("staff" / flagpole), then a shallow counter-sloped parallel
CHANNEL ("edge" / flag), then a close-break out of that channel in the
pole's direction.

The pole is found by searching windows from `staff_max_bars` down to
`staff_min_bars` and taking the LONGEST one that clears three gates: a
height of at least `staff_min_atr` ATR, at most `staff_max_opposite`
fully non-overlapping counter-direction bars, and an R-squared of at
least `staff_min_r2` for an OLS fit of close against bar ordinal.  The
channel is then tracked with INCREMENTAL least-squares sums, one bar at
a time, its two rails sharing a single slope and pinned to the running
highest high and lowest low.  It confirms when the close clears the
relevant rail by `breakout_atr_mult` ATR, and is abandoned when it grows
wider than `edge_max_width_pct` of the pole's height, outlives
`edge_max_bars`, or becomes eligible while its slope is not both
counter-directional (by at least `min_slope_atr` ATR per bar) and
shallower than `max_edge_slope_ratio` times the pole's slope.

Sources:
    https://www.tradingview.com/script/tMHhzI6j-Flag-Pattern-Breakout-Dots3Red/

Calculation:
    See the module docstring for the source-line-by-source-line mapping,
    the four things deliberately NOT ported, and the two asymmetries in
    the source that are reproduced rather than fixed.

Args:
    high (pd.Series): Series of 'high's
    low (pd.Series): Series of 'low's
    close (pd.Series): Series of 'close's
    staff_min_atr (float): Minimum pole height in ATR. Default: 2.0
    staff_min_bars (int): Shortest pole window. Default: 2
    staff_max_bars (int): Longest pole window, searched first. Default: 12
    staff_max_opposite (int): Counter-direction bars tolerated in the
        pole. Default: 1
    staff_min_r2 (float): Minimum R-squared straightness. Default: 0.85
    edge_min_bars (int): Bars the channel must run before a breakout can
        confirm. Default: 3
    edge_max_bars (int): Channel age cap. Default: 30
    edge_max_width_pct (float): Channel width cap, as a percent of the
        pole's height. Default: 60.0
    max_edge_slope_ratio (float): Channel slope cap, as a multiple of the
        pole's slope. Default: 0.6
    min_slope_atr (float): Minimum |channel slope| in ATR per bar.
        Default: 0.02
    breakout_atr_mult (float): ATR buffer the close must clear.
        Default: 0.15
    atr_length (int): ATR length. Default: 14
    width_mode (str): 'source' reproduces the source's two DIFFERENT
        width tests (raw extreme span on the bull side, slope-projected
        gap on the bear side); 'raw' and 'projected' force one rule on
        both sides. Default: 'source'
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.DataFrame: FLAG_CONF_BULL, FLAG_CONF_BEAR, FLAG_POLE_ATR,
    FLAG_PEND columns.
"""
