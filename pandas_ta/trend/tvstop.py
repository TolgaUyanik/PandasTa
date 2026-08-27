# -*- coding: utf-8 -*-
"""Terminal Velocity Stop (TVS) -- port of TradingView `7YXrxMjV`.

Source: `docs/TradingView/pine/7YXrxMjV-Terminal-Velocity-Stop-Lyro-RS.pine`
in the AwakenAnalytics `Backtesting` repo.  `wc -l` = 116 and
`grep -c ''` = 116 (the file is newline-terminated, so 116 CONTENT
lines, no off-by-one); both counts measured 2026-08-27.  `//@version=6`,
MPL-2.0, (c) LyroRS.

THE MECHANISM -- A RATE LIMITER ON STOP TRAVEL

An ordinary ATR trailing stop (Supertrend, Chandelier, HalfTrend) is a
RATCHET: in an uptrend the stop is `max(previous stop, close - mult *
ATR)`, so after a vertical candle it TELEPORTS up to the new target and
the first pause knocks the position out.  This source keeps the ratchet
but caps how far the stop may travel in one bar, verbatim at L71/L74:

    L71: step = math.max(math.min(target - stop, vmax * atr), -vmax * atr)
    L74: stop := math.max(stop, stop + step)

`vmax` (default 0.3) is the "terminal velocity" in ATR per bar.  However
violent the move, the stop advances at most `vmax * ATR` per bar.

WHICH HALF OF THE L71 CLAMP IS DEAD, AND WHERE

L74 is `stop + max(0, step)` and its mirror L80 is `stop + min(0, step)`.
Fold each into the clamp, writing `x = target - stop` and `v = vmax*atr`
(`v >= 0` because ATR >= 0 and `vmax > 0`):

  * UPTREND (L74):   `max(0, max(min(x, v), -v))` == `max(0, min(x, v))`.
    The OUTER `math.max(..., -vmax * atr)` -- the LOWER clamp -- is DEAD
    here: the ratchet's own floor of 0 already dominates `-v`.  The
    `math.min(..., vmax * atr)` is the LIVE rate limiter in this branch.
  * DOWNTREND (L80): `min(0, max(min(x, v), -v))` == `min(0, max(x, -v))`.
    Mirror image: the `math.min(..., vmax * atr)` -- the UPPER clamp --
    is DEAD, and `math.max(..., -vmax * atr)` is the live rate limiter.

So each half is dead in exactly ONE branch and load-bearing in the
other; NEITHER is globally removable, and the shared `step` expression
is not reducible for the indicator as a whole.  This module reproduces
L71/L74/L80 LITERALLY -- the redundant clamp is computed on every bar in
both branches -- rather than substituting the two reduced forms, so that
the code reads against the source line for line.  Both directions are
pinned by `test_lower_clamp_is_dead_in_the_uptrend_branch` and
`test_upper_clamp_is_load_bearing_in_the_uptrend_branch`.

⚠ The brief this port was written against stated the opposite -- that
"L74 ... makes the `math.min` half of L71 dead in the uptrend branch".
That is the wrong half.  `max(0, x)` discards NEGATIVE steps, so it
subsumes the `-v` FLOOR, not the `+v` CEILING; deleting the `math.min`
in the uptrend branch removes the rate limit itself and lets the stop
teleport, which is the entire point of the indicator.  The tests above
demonstrate both claims on data rather than asserting them.

THE FLIP RESETS BYPASS THE RATE LIMIT

L78 and L84 assign `stop := close +/- multiplier * atr` outright.  A
direction flip therefore relocates the stop instantly; `vmax` governs
TRAVEL WITHIN a direction, not the reset.  This is the source's
behaviour and is reproduced.

WHAT IS EMITTED, AND WHAT IS DELIBERATELY NOT

The source's payload is `stop`, a raw PRICE LEVEL.  Under this project's
scale-free law (`docs/indicators/` INDOC: raw price-level indicators
earn nothing by design, because nominal drift decays them) a price is
not shippable, so the DISTANCE was built instead -- and then deleted on
its own measurement.  What ships is the pair of flip events:

    TVS_FLIP_BULL   L86 `flipUp`         0/1
    TVS_FLIP_BEAR   L87 `flipDown`       0/1
    TVS_DIST   (close - stop) / atr      signed, in ATR units
               -- NOT emitted by default; pass `emit_dist=True`.  It was
               built, wired, MEASURED and DELETED at Spearman 0.930462
               against the engine's `RSI`; see "WHAT WAS BUILT,
               MEASURED AND THEN DELETED" below.

Everything from here to that section describes `TVS_DIST`, which is
still COMPUTED (the flags are read off its state machine) and still
available under `emit_dist=True`.  It is kept because the deletion has
to stay reproducible and because the properties below are what a reader
needs in order to re-derive it -- not because the column ships.

`TVS_DIST` is not merely a rescaled Supertrend distance.  Its SIGN
carries the direction (see below) and its MAGNITUDE carries the thing
that is new.  In the uptrend branch that magnitude is an EXACT detector
of the rate limit: `TVS_DIST > mult` if and only if the clamp bound on
that bar.  Proof, all within `dir == 1`: `dist > mult` <=> `close -
stop > mult*atr` <=> `stop < target`; but an UNCLAMPED positive step is
exactly `target - stop`, which lands `stop` ON `target` (`dist ==
mult`), and a negative step is discarded by the ratchet leaving `stop >
target` (`dist < mult`).  So `stop` can only sit strictly below its
target if the step was cut down to `+vmax*atr` this bar.  An ordinary
ratchet stop -- Supertrend, HalfTrend, Chande-Kroll -- closes that gap
in one bar and therefore cannot express the quantity at all.  Pinned by
`test_dist_above_mult_is_exactly_the_clamp_binding`.

The sign recovers the direction: at the end of any bar with `dir == 1`
the source has either left `close >= stop` standing (L76 did not fire)
or flipped and reset to `close + multm*atr` with `dir == -1`;
symmetrically for `dir == -1` (L82/L84).  So a separate `dir` column
would be redundant and is NOT emitted.

⚠ ONE EXCEPTION, and it is reachable, not theoretical: `close == stop`
gives `TVS_DIST == 0`, whose sign identifies nothing.  A dead-flat
series does exactly this -- the ATR is at the `non_zero_range` epsilon
floor (see below), `target` rounds to `close`, the stop never moves and
EVERY bar reads 0.0 while `dir` is still 1.  Do not read `sign(dist)`
as the direction without handling 0.

WHAT WAS BUILT, MEASURED AND THEN DELETED

`TVS_DIST` was the port's headline column and it is not shipped.  It
duplicates an ENGINE column, and not marginally:

    Spearman(TVS_DIST, RSI) = +0.930462 over 404,066 pooled bars
    (89 BIST_100 daily frames, AwakenAnalytics `Backtesting`).

That is not a pooling artifact.  Measured on each frame SEPARATELY the
same cell reads mean +0.9321 / median +0.9329 / min +0.8126 / max
+0.9595 across all 89 -- a structural relationship, above the host
project's ~0.9 revert line on every basis available.  `cmo` scores
identically (+0.930462) because it is a monotone recode of RSI, and the
next comparators follow it down: `ATRMAX_14_50` 0.908, `QQE_RSIMA`
0.902, `zscore` 0.900.

The MECHANISM is clear in hindsight and is the reason the number is so
stable.  In an uptrend the stop may close its gap to the target at no
more than `vmax * ATR` per bar, so `close - stop` ACCUMULATES the recent
up-move in ATR units -- which is, to a monotone transform, the quantity
RSI reports.  The rate limiter turns the distance into a slow momentum
integrator.

⚠ It is worth being blunt about what that costs, because the honest
reading is that this port's headline idea did not survive contact with
the engine.  What survives is the pair of FLIP flags, whose maxima over
the same 478 comparators are +0.202650 (`TVS_FLIP_BULL` x
`IFVG_MIT_BEAR_14`) and +0.219132 (`TVS_FLIP_BEAR` x
`APUSH_BEAR_14_5_5`).

⚠ Do NOT re-add `TVS_DIST` on the argument that it is not a duplicate of
the engine's STOP lane.  That is true and irrelevant: measured over all
eleven stop-lane columns its maximum is +0.786164 against
`Supertrend_Direction`, which would only have put it in the
ship-with-disclosure band.  The deletion rests on RSI, a momentum
oscillator, not on the stop lane.

⚠ Nor on the argument that it is a distinct concept.  `FINDINGS.md`
records that RSI is never selected by any mined tree in level form, so a
column that tracks RSI at rho 0.93 is duplicating something that does
not earn.

The module still COMPUTES the column and emits it under
`emit_dist=True`, so the finding stays reproducible.

WHAT IS *NOT* SETTLED BY THAT MEASUREMENT.  The genuinely novel quantity
this indicator carries is the CLAMP BINDING, not the distance itself,
and the distance is only its proxy.  A binary clamp flag was PROBED
against the same 478 comparators on the same pool and came back
materially cleaner -- bull-side max +0.745392 against `ATR_BREAKOUT_UP`,
bear-side +0.678733 against `ATR_BREAKOUT_DN`, and the direction-free
union +0.516067 -- with fire rates of 15.62% / 10.56% / 26.17%.
⚠ THAT IS A PROBE, NOT A VERDICT, and it is deliberately NOT shipped
here: the probe column was reconstructed OUTSIDE
`IndicatorEngine.compute_all`, and its causality, scale-invariance and
contamination gates were never run.  Anyone picking it up owes it the
full gate stack.  Artifact:
`backtest_results/tvpta6/tvstop_clamp_probe_20260827.csv`.

NOT PORTED, and each is a distinct decline:

  * L27-51 -- the four-way colour palette (`ColMode` switch, custom
    palette inputs, `UpC`/`DnC`) and L89 `css`. Presentation only.
  * L94-97 -- the four `plot(..., plot.style_linebr)` stop lines. Two
    of them are the glow duplicates of the other two, and all four
    re-plot `stop`, which is a raw price.
  * L99-105 -- the `pStop`/`pPrice` anchor plots and the `fill(...)`
    trend cloud drawn between them. Drawing only.
  * L107-108 -- the flip-dot `plot.style_circles` (again `stop`) and
    the `plotcandle` bar recolour.
  * L113-114 -- the two `alertcondition` calls. Their payloads ARE
    `flipUp`/`flipDown`, which this module emits as columns; only the
    alert plumbing is dropped.
  * the raw `stop` LEVEL itself, per the scale-free law above. It is
    reachable from what IS emitted -- `stop == close - TVS_DIST * ATR`
    -- so nothing is lost that a caller with the OHLC frame cannot
    recover.

DIVIDING BY ATR: WHAT ACTUALLY HAPPENS, MEASURED

`TVS_DIST` divides by ATR, so the obvious worry is a zero ATR on a
suspended or dead-flat name.  MEASURED on this fork rather than
assumed: it does not arise.  `volatility/true_range.py` builds its
high-low leg with `utils.non_zero_range`, which adds `sflt.epsilon` to
the WHOLE series the moment any single bar has `high == low`, so on a
60-bar series of a constant 50.0 the ATR is pinned at
2.220446049250313e-16 -- floored, never 0 -- and `TVS_DIST` comes back
as exactly 0.0 on every bar, with no inf anywhere.  (Reasoned from
there: an exactly-zero ATR needs every true range in the window to be
zero, which needs `high == low` on those bars, which is precisely the
condition that triggers the epsilon.  So on well-formed OHLC input
`atr > 0` always.)  Both halves are pinned by
`test_flat_series_atr_is_epsilon_floored_and_dist_is_zero_not_inf`.

This module still guards with `if not (atr > 0)` -> NaN on all three
columns.  Be precise about what that guard is for: it covers a MISSING
ATR (the warm-up, and any NaN in the input propagating through) and a
pathological non-positive one; it is NOT what prevents an infinity on
flat data, because the epsilon floor gets there first.  The guard also
keeps the three NaN masks identical, which downstream overlap and
scale-invariance checks rely on.

⚠ THE REAL HAZARD IS THE OPPOSITE SHAPE, AND IT IS NOT GUARDED.  A
TINY-but-positive ATR is an amplifier: the ratio explodes without ever
reaching inf, so nothing NaNs out and nothing looks broken.  Measured
on a 60-bar fixture that sits flat at 50.0 and then steps once to 50.5,
`TVS_DIST` reads 12.98 on the step bar and climbs to 42.96 -- against a
`mult` of 3.0 -- purely because ATR had collapsed to the epsilon floor
and is only now recovering.  Those are LEGITIMATE readings of a real
quantity ("price is 43 ATR above a stop that may not chase"), not
corruption, and they are deliberately NOT clipped: a clip would invent
a threshold the source does not have.  But a consumer that assumes
`TVS_DIST` lives near +/-`mult` will be wrong, and a low-volatility
patch followed by ANY move is the shape that produces the tail.  Pinned
by `test_a_flat_patch_then_a_step_inflates_dist_far_beyond_mult`.

A NaN BAR IS SKIPPED, NOT CONSUMED -- AND THIS DIVERGES FROM PINE.  A
bar whose close or ATR is missing is stepped over: `stop` and `dir`
carry across it unchanged and all three columns read NaN there.  Pine
would instead propagate `na` through L71/L74, leave `stop` na, and then
re-enter the L68 `if na(stop)` branch on the next bar -- RESETTING the
stop and discarding the ratchet.  Skipping is the deliberate choice
here: a bar that did not trade is not evidence that the trend ended.
Pinned by `test_a_nan_bar_is_skipped_not_consumed`.

WARM-UP: `atr` uses this fork's `pandas_ta.volatility.atr`, whose RMA is
`ewm(alpha=1/length, min_periods=length).mean()` with pandas' default
`adjust=True`.  Pine's `ta.rma` instead seeds the recursion with an SMA
of the first `length` values.  The two agree in shape and converge
geometrically but are NOT bit-equal, so a bar-for-bar comparison
against a TradingView chart will differ slightly, most visibly early.
This is a PRE-EXISTING fork-wide property inherited by every ATR-based
indicator here (`cksp`, `supertrend`, `flag_breakout`), not a choice
made by this port; the transliteration test feeds ONE atr series to both
implementations so that it isolates the stop logic rather than the
moving-average flavour.

CONTAMINATION REACH.  `FINDINGS.md` records that an EMA/RMA stage makes
the stated `length` a decay constant rather than a window, so any
taint-reach number computed from `atr_length` is a FLOOR.  This
indicator adds a SECOND, longer-lived carrier: `stop` is a recursive
`var` that is only ever reset by a direction FLIP, so a contaminated
ATR does not wash out after `length` bars -- it perturbs the stop, and
that perturbation persists until the next flip.  In an uptrend the
self-correction is bounded BELOW by the rate limit itself (a stop left
too low closes the gap at no more than `vmax * ATR` per bar), while a
stop left too HIGH is removed immediately -- by a FABRICATED FLIP.
Measure the reach; do not read it off `atr_length`.
"""
import numpy as np
from pandas import DataFrame, Series

from pandas_ta.volatility.atr import atr as _atr
from pandas_ta.utils import get_offset, verify_series


def _validated_int(value, default, name, positive=True):
    """None -> default (a normal, documented default, not bad input).
    Anything else must be a genuine, finite, integral value, or raise.
    Same helper, same rejection paths, as `flag_breakout.py`."""
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


def _fmt(x):
    """`3.0 -> 3`, `0.3 -> 0.3` -- keeps column names short."""
    return int(x) if float(x).is_integer() else x


def tvstop(high, low, close, atr_length=None, mult=None, multm=None,
           vmax=None, mamode=None, emit_dist=False, offset=None, **kwargs):
    """Indicator: Terminal Velocity Stop (TVS)"""
    atr_length = _validated_int(atr_length, 14, "atr_length")
    mult = _validated_float(mult, 3.0, "mult")
    multm = _validated_float(multm, 3.0, "multm")
    vmax = _validated_float(vmax, 0.3, "vmax")
    # NOTE: the source's UI sliders additionally cap `vmax` at 2 and
    # floor `mult`/`multm` at 0.5 (L12-22).  Those are TradingView input
    # widget bounds, not algorithm preconditions, and -- as in
    # `flag_breakout` -- they are NOT re-enforced here.
    if mamode is not None and not isinstance(mamode, str):
        raise ValueError(f"mamode must be a str or None, got {mamode!r}")
    offset = get_offset(offset)

    high = verify_series(high, atr_length)
    low = verify_series(low, atr_length)
    close = verify_series(close, atr_length)
    if high is None or low is None or close is None:
        return

    atr_ = _atr(high=high, low=low, close=close, length=atr_length,
                mamode=mamode)
    if atr_ is None:
        return

    c = close.to_numpy(dtype=float)
    a = atr_.to_numpy(dtype=float)
    n = c.shape[0]

    dist = np.full(n, np.nan)
    flip_bull = np.full(n, np.nan)
    flip_bear = np.full(n, np.nan)

    # `var float stop = na` / `var int dir = 1`  (L63-64)
    stop = np.nan
    direction = 1
    prev_direction = None  # `dir[1]`; na before the first bar

    for t in range(n):
        a_t = a[t]
        c_t = c[t]
        # The port's own guard, not the source's -- see "DIVIDING BY ATR"
        # and "A NaN BAR" in the module docstring.  A missing/non-positive
        # ATR, or a missing close, leaves the state machine UNTOUCHED and
        # emits NaN on all three columns.  Do not relax this to lean on
        # Python's `max(x, nan) -> x` ordering accident: that happens to
        # preserve `stop` today, but it is unstated behaviour and it is
        # NOT what Pine does (there `na` propagates and the stop resets).
        if not (a_t > 0.0) or c_t != c_t:
            prev_direction = direction
            continue

        # L66
        target = c_t - mult * a_t if direction == 1 else c_t + multm * a_t

        if stop != stop:  # `if na(stop)` (L68)
            stop = target  # L69
        else:
            # L71, reproduced literally -- one half of this clamp is
            # redundant in each branch below, see the module docstring.
            step = max(min(target - stop, vmax * a_t), -vmax * a_t)
            if direction == 1:
                stop = max(stop, stop + step)      # L74
                if c_t < stop:                     # L76
                    direction = -1                 # L77
                    stop = c_t + multm * a_t       # L78
            else:
                stop = min(stop, stop + step)      # L80
                if c_t > stop:                     # L82
                    direction = 1                  # L83
                    stop = c_t - mult * a_t        # L84

        dist[t] = (c_t - stop) / a_t
        # L86-87.  `dir[1]` is na on the very first evaluated bar, and
        # `na == -1` is na in Pine, so no flip is claimed there.
        flip_bull[t] = 1.0 if (direction == 1 and prev_direction == -1) else 0.0
        flip_bear[t] = 1.0 if (direction == -1 and prev_direction == 1) else 0.0
        prev_direction = direction

    _props = f"_{atr_length}_{_fmt(mult)}_{_fmt(multm)}_{_fmt(vmax)}"
    # `dist` is COMPUTED unconditionally -- it IS the state machine's
    # output and the flags are read off its sign changes -- but emitted
    # only on request. See "WHAT WAS BUILT, MEASURED AND THEN DELETED".
    out = [Series(flip_bull, index=close.index, name=f"TVS_FLIP_BULL{_props}"),
           Series(flip_bear, index=close.index, name=f"TVS_FLIP_BEAR{_props}")]
    if emit_dist:
        out.insert(0, Series(dist, index=close.index,
                             name=f"TVS_DIST{_props}"))

    if offset != 0:
        names = [s.name for s in out]
        out = [s.shift(offset) for s in out]
        for s, nm in zip(out, names):
            s.name = nm

    if "fillna" in kwargs:
        for s in out:
            s.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        for s in out:
            s.fillna(method=kwargs["fill_method"], inplace=True)

    df = DataFrame({s.name: s for s in out})
    df.name = f"TVS{_props}"
    df.category = "trend"
    return df


tvstop.__doc__ = """Terminal Velocity Stop (TVS)

A port of TradingView `7YXrxMjV` "Terminal Velocity Stop | Lyro RS"
(MPL-2.0, (c) LyroRS).  An ATR trailing stop whose PER-BAR TRAVEL is
hard-capped at `vmax` ATR, so however violent the candle the stop
cannot teleport under price and be taken out by the first pause.

The stop chases a target of `close - mult * ATR` in an uptrend and
`close + multm * ATR` in a downtrend, moving toward it by at most
`vmax * ATR` per bar and never backwards (a ratchet).  When the close
crosses its own stop the direction flips and the stop is reset to the
opposite side of price, bypassing the rate limit.

Emits the two DIRECTION-FLIP events.  The scale-free distance
`TVS_DIST = (close - stop) / ATR` -- the port's original headline
column -- is computed but NOT emitted by default: it measured Spearman
0.930462 against the engine's `RSI` and was deleted.  Pass
`emit_dist=True` to reproduce the finding.  See the module docstring.

Sources:
    https://www.tradingview.com/script/7YXrxMjV-Terminal-Velocity-Stop-Lyro-RS/

Calculation:
    See the module docstring for the source-line-by-source-line mapping,
    which half of the L71 clamp is dead in which branch and why, the
    four things deliberately NOT ported, and the NaN contract.

Args:
    high (pd.Series): Series of 'high's
    low (pd.Series): Series of 'low's
    close (pd.Series): Series of 'close's
    atr_length (int): ATR length, source `atrLen`. Default: 14
    mult (float): Stop distance from price in an UPTREND, in ATR,
        source `mult`. Default: 3.0
    multm (float): Stop distance from price in a DOWNTREND, in ATR,
        source `multm`. Default: 3.0
    vmax (float): Terminal velocity -- the maximum stop travel per bar,
        in ATR. Source `vmax`. Default: 0.3
    mamode (str): Moving average used by ATR. Default: None -> the
        fork's `atr` default, 'rma'
    emit_dist (bool): also emit `TVS_DIST`, `(close - stop) / ATR`.
        Default: False -- it measured Spearman 0.930462 against the
        engine's `RSI` over 404,066 bars (per-frame mean 0.9321 across
        89 frames) and was removed; see the module docstring.
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.DataFrame: TVS_FLIP_BULL, TVS_FLIP_BEAR columns (plus TVS_DIST,
    first, when `emit_dist=True`).
"""
