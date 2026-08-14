# -*- coding: utf-8 -*-
import math

import numpy as np
from pandas import DataFrame, Series

from pandas_ta.momentum.macd import macd
from pandas_ta.momentum.rsi import rsi
from pandas_ta.overlap.ema import ema
from pandas_ta.overlap.sma import sma
from pandas_ta.statistics.stdev import stdev
from pandas_ta.trend.adx import adx
from pandas_ta.volatility.atr import atr
from pandas_ta.utils import get_offset, verify_series


def _confirm_strict_pivots(series, left, right, is_high):
    """Causal pivot confirmation matching Pine's `ta.pivothigh`/
    `ta.pivotlow`: a bar at position i confirms (becomes visible at
    j=i+right) iff it is the STRICT, UNIQUE extreme of the window
    [i-left, i+right]. Duplicated from `sr_force.py`'s (and
    `rejection_blocks.py`'s / `liquidity_sweep.py`'s / `equal_highs_lows.py`'s
    / `sphinx_unicorn.py`'s / `volume_sr_zones.py`'s) identical helper
    rather than imported, matching this package's convention of
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


def _validated_int(value, default, name, positive=True):
    """None -> default (a normal, documented default, not bad input).
    Anything else must be a genuine, finite, integral value, or raise.
    Duplicated verbatim from `rejection_blocks.py`'s/`sr_force.py`'s
    helper of the same name (checks NaN/inf/non-integral explicitly
    before ever calling `int()`, so every rejection path is the same
    ValueError, not a mix of ValueError/OverflowError/silent truncation)."""
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
    Duplicated verbatim from `rejection_blocks.py`'s/`sr_force.py`'s
    helper of the same name. `nonneg=False` (used here for the RSI/BB
    threshold levels, which the source itself allows negative -- e.g.
    `longBbLevel` accepts -0.5..0.7) allows any finite value."""
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


def _validated_bool(value, default, name):
    """None -> default; a genuine bool passes through; anything else
    raises -- unlike Python's own truthiness, `1`/`0`/`"true"` are NOT
    silently accepted, matching `_validated_int`'s/`_validated_float`'s
    "wrong type raises, don't guess" discipline."""
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    raise ValueError(f"{name} must be a bool, got {value!r}")


class _Candidate:
    __slots__ = ("direction", "pivot_bar", "price", "atr", "score", "rescue")

    def __init__(self, direction, pivot_bar, price, atr_, score, rescue):
        self.direction = direction  # 1 = pending swing LOW (long candidate), -1 = pending swing HIGH (short)
        self.pivot_bar = pivot_bar  # the anchor (pivot) bar index, NOT the confirming bar
        self.price = price          # pivotLow / pivotHigh at the pivot bar
        self.atr = atr_             # ATR(14) at the pivot bar, frozen at candidate creation
        self.score = score          # 0-5 confluence score at creation
        self.rescue = rescue        # True iff admitted via the score==2 rescue branch


def _at(arr, idx):
    """arr[idx] if idx is a valid, non-negative, in-range index, else NaN.
    Python/numpy negative indices silently WRAP AROUND to the end of the
    array instead of raising -- which would corrupt every backward
    history reference this port makes (`close[pivotRight + contextBars]`,
    `macdHist[pivotRight + 1]`, ...) whenever that reference lands before
    bar 0. Pine's own out-of-range history-reference operator simply
    returns `na` in that case, which is what this reproduces; every
    comparison built on the result (`<`, `>`, `<=`, `>=`) then naturally
    evaluates to False against a NaN operand in numpy/Python, exactly
    matching Pine's "a boolean expression involving na is treated as
    false in an `if` condition" semantics -- no extra guarding needed at
    each call site."""
    if idx < 0 or idx >= len(arr):
        return np.nan
    return arr[idx]


def bdi4kewl(open_, high, low, close, volume, pivot_left=None, pivot_right=None,
             impulse_lookback=None, min_impulse_atr=None, min_reversal_atr=None,
             max_confirmation_bars=None, min_swing_separation_atr=None,
             context_bars=None, long_rsi_level=None, short_rsi_level=None,
             long_bb_level=None, short_bb_level=None, activity_volume_ratio=None,
             activity_range_atr=None, rejection_wick_ratio=None, min_score=None,
             enable_rescue_branch=None, offset=None, **kwargs):
    """Indicator: 4-Hour Swing Turn (STURN) -- ATR-confirmed swing-turn signal"""
    pivot_left = _validated_int(pivot_left, 3, "pivot_left")
    pivot_right = _validated_int(pivot_right, 2, "pivot_right")
    impulse_lookback = _validated_int(impulse_lookback, 12, "impulse_lookback")
    min_impulse_atr = _validated_float(min_impulse_atr, 2.00, "min_impulse_atr")
    min_reversal_atr = _validated_float(min_reversal_atr, 1.20, "min_reversal_atr")
    max_confirmation_bars = _validated_int(max_confirmation_bars, 12, "max_confirmation_bars")
    min_swing_separation_atr = _validated_float(min_swing_separation_atr, 1.50, "min_swing_separation_atr")
    context_bars = _validated_int(context_bars, 6, "context_bars")
    long_rsi_level = _validated_float(long_rsi_level, 48.0, "long_rsi_level", nonneg=False)
    short_rsi_level = _validated_float(short_rsi_level, 52.0, "short_rsi_level", nonneg=False)
    long_bb_level = _validated_float(long_bb_level, 0.35, "long_bb_level", nonneg=False)
    short_bb_level = _validated_float(short_bb_level, 0.65, "short_bb_level", nonneg=False)
    activity_volume_ratio = _validated_float(activity_volume_ratio, 1.15, "activity_volume_ratio")
    activity_range_atr = _validated_float(activity_range_atr, 1.10, "activity_range_atr")
    rejection_wick_ratio = _validated_float(rejection_wick_ratio, 0.25, "rejection_wick_ratio")
    min_score = _validated_int(min_score, 3, "min_score")
    enable_rescue_branch = _validated_bool(enable_rescue_branch, True, "enable_rescue_branch")

    # Length floor: the pivot-confirmation window (_confirm_strict_pivots'
    # own left+right+1 requirement), the impulse lookback, and the longest
    # warmup among the borrowed primitives (EMA21, MACD's slow+signal=35)
    # -- ATR/RSI/ADX(14) and SMA/STDEV(20) are all shorter and so never
    # bind here.
    min_len = max(2 * pivot_left + 1, 2 * pivot_right + 1, impulse_lookback, 21, 35)
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

    atr_v = atr(high, low, close, length=14).to_numpy(dtype=float)
    rsi_v = rsi(close, length=14).to_numpy(dtype=float)
    ema21_v = ema(close, length=21).to_numpy(dtype=float)
    bb_basis = sma(close, length=20)
    # ddof=0 (population stdev), NOT this package's own `stdev()` default
    # of ddof=1 (sample) -- Pine's `ta.stdev(source, length, biased)`
    # defaults `biased=true`, i.e. the POPULATION estimator, which is
    # exactly why this same package's `bbands()` hard-defaults `ddof=0`
    # (`pandas_ta/volatility/bbands.py`) rather than trusting `stdev()`'s
    # own default. Fletcher-caught (round 1): the original version of this
    # line used the bare `stdev()` default (ddof=1), inflating the
    # deviation by sqrt(20/19) (~2.6%) and pulling `bbPosition` toward
    # 0.5 -- measured to flip the 0.35/0.65 threshold on 0.766% of bars
    # (529/69,063) on a real-data sample, changing 4 flag-bars and 5
    # SCORE values across 25,085 signals over 367,417 bars. Small, but a
    # genuine mistranslation of Pine's default, not a warmup/seeding
    # convention difference (unlike the "borrowed primitives" caveat
    # elsewhere in this docstring, which is about warmup, not defaults).
    bb_dev = stdev(close, length=20, ddof=0) * 2.0
    bb_upper_v = (bb_basis + bb_dev).to_numpy(dtype=float)
    bb_lower_v = (bb_basis - bb_dev).to_numpy(dtype=float)
    bb_denom_v = bb_upper_v - bb_lower_v
    # Pine: `bbUpper != bbLower ? (close-bbLower)/(bbUpper-bbLower) : 0.5`.
    # During SMA(20)/STDEV(20) warmup (bars 0-18) bbUpper/bbLower are BOTH
    # na -- and Pine treats a na-valued condition as false in a ternary,
    # so the ELSE branch (0.5) fires. Python/numpy's `!=` operator does
    # NOT share that semantics: `nan != nan` is True (unlike `<`/`>`/
    # `<=`/`>=`, which are all False against a NaN operand) -- a naive
    # `bb_upper_v != bb_lower_v` would therefore select the DIVISION
    # branch on NaN inputs and (harmlessly, since NaN propagates) still
    # end up NaN, not Pine's 0.5. `~np.isnan(...)` is required explicitly
    # to reproduce the else-branch-on-na Pine behavior for the ~5-bar
    # window (14-18, between ATR's warmup and BB's) where this port's
    # main loop is otherwise already active.
    diff_ok = (bb_upper_v != bb_lower_v) & ~np.isnan(bb_upper_v) & ~np.isnan(bb_lower_v)
    with np.errstate(invalid="ignore", divide="ignore"):
        bb_position_v = np.where(
            diff_ok,
            (close_v - bb_lower_v) / np.where(bb_denom_v == 0, np.nan, bb_denom_v),
            0.5,
        )

    adx_df = adx(high, low, close, length=14)
    plus_di_v = adx_df["DMP_14"].to_numpy(dtype=float)
    minus_di_v = adx_df["DMN_14"].to_numpy(dtype=float)
    macd_hist_v = macd(close, fast=12, slow=26, signal=9)["MACDh_12_26_9"].to_numpy(dtype=float)
    avg_volume_v = sma(volume, length=20).to_numpy(dtype=float)
    with np.errstate(invalid="ignore", divide="ignore"):
        volume_ratio_v = np.where(avg_volume_v > 0, volume_v / avg_volume_v, 0.0)

    # Pine `ta.highest(high, impulseLookback)` / `ta.lowest(low, ...)`:
    # rolling extreme over the trailing window INCLUDING the current bar,
    # gracefully using however much history exists early on (never na
    # purely for insufficient warmup) -- `min_periods=1` matches that.
    impulse_highest_v = high.rolling(window=impulse_lookback, min_periods=1).max().to_numpy(dtype=float)
    impulse_lowest_v = low.rolling(window=impulse_lookback, min_periods=1).min().to_numpy(dtype=float)

    pivot_low_v = _confirm_strict_pivots(low, pivot_left, pivot_right, is_high=False)
    pivot_high_v = _confirm_strict_pivots(high, pivot_left, pivot_right, is_high=True)

    out_long = np.zeros(n, dtype=int)
    out_short = np.zeros(n, dtype=int)
    out_score = np.full(n, np.nan)
    out_rescue = np.full(n, np.nan)

    pending = []  # list[_Candidate], processed in insertion order each bar --
    # mirrors the source's `pendingDirection`/`pendingPivotBar`/`pendingPrice`/
    # `pendingAtr`/`pendingScore`/`pendingRescue` parallel arrays as one list
    # of objects instead (this package's usual style for multi-field pooled
    # state, see `_Zone` in `rejection_blocks.py`/`sr_force.py`).

    last_signal_direction = 0  # 0 = none yet (never equals +-1, so the first
    # accepted signal always clears the alternation check, same as the
    # source's `var int lastSignalDirection = 0`)
    last_signal_price = np.nan
    last_signal_atr = np.nan

    for t in range(n):
        anchor_bar = t - pivot_right
        if anchor_bar < 0:
            continue
        anchor_atr = atr_v[anchor_bar]
        if np.isnan(anchor_atr):
            # Matches Pine's `not na(atr[pivotRight])` gate -- the ENTIRE
            # per-bar block (both new-candidate creation AND existing-
            # candidate confirmation/expiry checking) is skipped this bar
            # when the anchor bar's own ATR hasn't warmed up yet, exactly
            # like the source. Only matters in the first ~14 bars, when
            # `pending` is provably still empty (no candidate could have
            # been added without having already passed this same gate on
            # an earlier bar).
            continue

        open_a = open_v[anchor_bar]
        close_a = close_v[anchor_bar]
        high_a = high_v[anchor_bar]
        low_a = low_v[anchor_bar]
        anchor_range = high_a - low_a
        if anchor_range > 0:
            anchor_lower_wick = (min(open_a, close_a) - low_a) / anchor_range
            anchor_upper_wick = (high_a - max(open_a, close_a)) / anchor_range
        else:
            anchor_lower_wick = 0.0
            anchor_upper_wick = 0.0
        anchor_range_atr = anchor_range / anchor_atr if anchor_atr > 0 else 0.0
        anchor_active = (volume_ratio_v[anchor_bar] >= activity_volume_ratio) or (anchor_range_atr >= activity_range_atr)

        # --- new LONG (swing-low) candidate ---
        pl = pivot_low_v[t]
        if not np.isnan(pl):
            prior_close = _at(close_v, anchor_bar - context_bars)
            prior_move_pass = close_a < prior_close
            bb_a = bb_position_v[anchor_bar]
            location_pass = (bb_a <= long_bb_level) or (close_a < ema21_v[anchor_bar])
            rsi_a = rsi_v[anchor_bar]
            momentum_pass = (rsi_a <= long_rsi_level) or (minus_di_v[anchor_bar] > plus_di_v[anchor_bar])
            macd_prev = _at(macd_hist_v, anchor_bar - 1)
            rejection_pass = (anchor_lower_wick >= rejection_wick_ratio) or (close_a > open_a) or (macd_hist_v[anchor_bar] > macd_prev)
            score = int(prior_move_pass) + int(location_pass) + int(momentum_pass) + int(anchor_active) + int(rejection_pass)
            preceding_high = impulse_highest_v[anchor_bar]
            impulse_pass = (preceding_high - pl) >= min_impulse_atr * anchor_atr
            rescue_pass = bool(enable_rescue_branch and score == 2 and anchor_active and rejection_pass)
            if impulse_pass and (score >= min_score or rescue_pass):
                # Keep only the single MOST EXTREME (lowest-price) pending
                # long candidate: any existing long candidate whose price
                # is dominated (>= the new, more-extreme low) is dropped;
                # if any surviving candidate is itself MORE extreme than
                # the new one, the new one is not added. Scanning backward
                # so index-based removal never disturbs not-yet-visited
                # (lower-index) entries.
                add_candidate = True
                idx = len(pending) - 1
                while idx >= 0:
                    c = pending[idx]
                    if c.direction == 1:
                        if pl <= c.price:
                            pending.pop(idx)
                        else:
                            add_candidate = False
                    idx -= 1
                if add_candidate:
                    pending.append(_Candidate(1, anchor_bar, pl, anchor_atr, score, rescue_pass))

        # --- new SHORT (swing-high) candidate, mirror of the above ---
        ph = pivot_high_v[t]
        if not np.isnan(ph):
            prior_close = _at(close_v, anchor_bar - context_bars)
            prior_move_pass = close_a > prior_close
            bb_a = bb_position_v[anchor_bar]
            location_pass = (bb_a >= short_bb_level) or (close_a > ema21_v[anchor_bar])
            rsi_a = rsi_v[anchor_bar]
            momentum_pass = (rsi_a >= short_rsi_level) or (plus_di_v[anchor_bar] > minus_di_v[anchor_bar])
            macd_prev = _at(macd_hist_v, anchor_bar - 1)
            rejection_pass = (anchor_upper_wick >= rejection_wick_ratio) or (close_a < open_a) or (macd_hist_v[anchor_bar] < macd_prev)
            score = int(prior_move_pass) + int(location_pass) + int(momentum_pass) + int(anchor_active) + int(rejection_pass)
            preceding_low = impulse_lowest_v[anchor_bar]
            impulse_pass = (ph - preceding_low) >= min_impulse_atr * anchor_atr
            rescue_pass = bool(enable_rescue_branch and score == 2 and anchor_active and rejection_pass)
            if impulse_pass and (score >= min_score or rescue_pass):
                add_candidate = True
                idx = len(pending) - 1
                while idx >= 0:
                    c = pending[idx]
                    if c.direction == -1:
                        if ph >= c.price:
                            pending.pop(idx)
                        else:
                            add_candidate = False
                    idx -= 1
                if add_candidate:
                    pending.append(_Candidate(-1, anchor_bar, ph, anchor_atr, score, rescue_pass))

        # --- confirmation / expiry: every pending candidate (both
        # directions, in insertion order, INCLUDING ones just added this
        # same bar above -- matches the source's single sequential script
        # execution per bar) is checked once. A candidate leaves the pool
        # this bar either way (accepted, blocked-but-reversal-confirmed,
        # or aged out past max_confirmation_bars); only a genuinely still-
        # pending candidate survives to the next bar. ---
        idx = 0
        signal_accepted_this_bar = False
        while idx < len(pending):
            c = pending[idx]
            candidate_age = t - c.pivot_bar
            expired = candidate_age > max_confirmation_bars
            if c.direction == 1:
                reversal_confirmed = (candidate_age >= pivot_right) and (close_v[t] - c.price >= min_reversal_atr * c.atr)
            else:
                reversal_confirmed = (candidate_age >= pivot_right) and (c.price - close_v[t] >= min_reversal_atr * c.atr)

            if expired or reversal_confirmed:
                if reversal_confirmed:
                    alternation_pass = last_signal_direction != c.direction
                    comparison_atr = c.atr if np.isnan(last_signal_atr) else max(c.atr, last_signal_atr)
                    separation_pass = np.isnan(last_signal_price) or (abs(c.price - last_signal_price) >= min_swing_separation_atr * comparison_atr)
                    if not signal_accepted_this_bar and alternation_pass and separation_pass:
                        # THE CAUSALITY POINT: the flag is written at `t`,
                        # the CONFIRMATION bar -- never at `c.pivot_bar`.
                        # The source's own tooltip says the same thing
                        # ("该枢轴已在 ... 的4小时收盘确认", "this pivot was
                        # confirmed at the ... 4h close") even though its
                        # LABEL is drawn back at the pivot bar for display;
                        # this port ships only the confirmation-bar flag,
                        # never the back-dated marker (see module docstring
                        # CAUSALITY section).
                        if c.direction == 1:
                            out_long[t] = 1
                        else:
                            out_short[t] = 1
                        out_score[t] = float(c.score)
                        out_rescue[t] = 1.0 if (c.rescue or c.score < min_score) else 0.0
                        last_signal_direction = c.direction
                        last_signal_price = c.price
                        last_signal_atr = c.atr
                        signal_accepted_this_bar = True
                pending.pop(idx)
            else:
                idx += 1

    long_s = Series(out_long, index=close.index)
    short_s = Series(out_short, index=close.index)
    score_s = Series(out_score, index=close.index)
    rescue_s = Series(out_rescue, index=close.index)

    if offset != 0:
        long_s = long_s.shift(offset)
        short_s = short_s.shift(offset)
        score_s = score_s.shift(offset)
        rescue_s = rescue_s.shift(offset)

    if "fillna" in kwargs:
        for s in (long_s, short_s, score_s, rescue_s):
            s.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        for s in (long_s, short_s, score_s, rescue_s):
            s.fillna(method=kwargs["fill_method"], inplace=True)

    _props = f"_{pivot_left}_{pivot_right}"
    long_s.name = f"STURN_LONG{_props}"
    short_s.name = f"STURN_SHORT{_props}"
    score_s.name = f"STURN_SCORE{_props}"
    rescue_s.name = f"STURN_RESCUE{_props}"

    df = DataFrame({
        long_s.name: long_s,
        short_s.name: short_s,
        score_s.name: score_s,
        rescue_s.name: rescue_s,
    })
    df.name = f"STURN{_props}"
    df.category = "trend"

    return df


bdi4kewl.__doc__ = \
"""4-Hour Swing Turn (STURN) -- ATR-confirmed swing-turn signal

A confirmed fractal pivot (`ta.pivotlow`/`ta.pivothigh` strict-extreme
semantics, left/right bars either side) is scored on 5 independent
confluence factors -- prior directional context, BB-position/EMA21
location, RSI/DMI momentum, bar "activity" (volume ratio OR range-vs-ATR),
and wick-rejection/MACD-histogram turn -- and only becomes a PENDING
candidate if it also clears a minimum preceding-impulse size (>= 2.0 ATR
by default) AND scores >= `min_score` (3 of 5 by default) on those 5
factors, OR qualifies via a narrower "rescue" branch (score exactly 2,
but BOTH the activity and rejection factors independently pass). A
pending candidate is held -- at most one per direction, the most price-
extreme survives, see the pruning comment in the code -- until price
reverses far enough from the pivot price (>= 1.2 ATR by default) within
`max_confirmation_bars` (12 by default), at which point it either fires
(subject to two book-keeping gates: ALTERNATION -- the new signal's
direction must differ from the last accepted signal's, and SEPARATION --
its pivot price must be >= 1.5 ATR, using the larger of the two
candidates' own ATR, from the last accepted signal's price) or is dropped
unfired once it expires.

Source: TradingView community indicator "4-Hour Swing Turn V2.0"
("4小时波段转折 V2.0") by AIsangbiao, https://www.tradingview.com/script/
BDi4kEWL/ (ported into AwakenAnalytics/Backtesting TVPTA-6 candidate 13,
2026-08-14; MPL-2.0 per TradingView's open-source publication
convention). Replaces the entire signal state machine (lines ~76-194 of
the source): the 5-item confluence score (both the swing-low and the
mirrored swing-high branch), the impulse-size gate, the rescue branch,
the same-direction pending-candidate pruning (`addCandidate`/the
backward-scanning `while pruneIndex >= 0` loop), and the confirmation/
expiry loop (`reversalConfirmed`/`expired`, the alternation + separation
gates on acceptance).

⚠ CAUSALITY -- the source is exemplary here, and this port preserves
that property exactly: every score/gate/threshold check reads bars at or
before `[pivotRight]` (the anchor/pivot bar) or the current confirming
bar; nothing ever looks forward. The source's own visible LABEL is
back-dated to the pivot bar for display (`label.new(x = candidateBar,
...)`, i.e. drawn several bars in the PAST relative to where it was
actually created) -- but its own code comment says this explicitly
("针尖标记只会在实时确认完成后创建，再锚定到已经确认的枢轴价位；提醒时间仍是
确认K线，绝不冒充提前预知" -- "the pin marker is only ever CREATED after
live confirmation completes, then anchored back to the already-confirmed
pivot price; the alert time is still the CONFIRMING bar, never
pretending to know in advance") and its `alertcondition`/tooltip both
fire strictly on the confirming bar. This port ships ONLY that
confirmation-bar flag (`STURN_LONG`/`STURN_SHORT` are 1 on the bar the
reversal is confirmed, never back-dated to the pivot bar) -- the
back-dated pivot-bar marker is a DISPLAY convenience with no place in a
column-oriented, non-repainting feature.

⚠ `validChart` DROPPED: the source hard-gates all of the above behind
`timeframe.isintraday and timeframe.multiplier == 240 and
chart.is_standard` (i.e. it only runs on standard 4-hour intraday
charts). This fork's engine runs on daily and hourly OHLCV frames, not
TradingView's live chart timeframe state, so there is no `validChart`
equivalent to check -- the gate is dropped entirely, not translated. The
signal math itself is timeframe-agnostic (every threshold is expressed
in ATR units or bar counts, not clock time), so this is a scope
reduction (the caller may run it on ANY bar interval), not a
mistranslation.

⚠ Every borrowed primitive (`atr`, `rsi`, `ema`, `sma`/`stdev` for the
Bollinger midline/deviation, `adx` for `+DI`/`-DI`, `macd` for the
histogram) is this fork's OWN implementation, not Pine's `ta.*` -- their
warmup/seeding conventions (SMA- or RMA-seeded, per each module's own
docstring) can differ from Pine's own recursive seeding in the first
`length` bars of a series. This is a pre-existing, project-wide caveat
shared by every other TVPTA port that composes these same primitives,
not something new here.

⚠ NOT PORTED (display/alerting only, no signal math): the `validChart`
gate (see above, a scope decision, not merely "not ported"); all
`label.new`/`plotshape` drawing (including the back-dated pivot-bar
marker itself, per the CAUSALITY section above); the 3 `alertcondition`
calls; `showLongSignals`/`showShortSignals`/`showPivotTipLabels`/
`showConfirmationMarks` (display-only toggles with no effect on which
bars fire); the tooltip time-format string
(`str.format_time(time, "yyyy-MM-dd HH:mm")`).

⚠ The `candidateAge >= pivotRight` reversal-confirmation guard is, by
construction, ALWAYS true for the reasons below -- ported literally
anyway (a faithful translation of the source's own math, not an
algebraically-reduced equivalent of it, matching this fork's convention
-- see `sr_force.py`'s `_retest_score` docstring for the precedent of
keeping a source's own not-simplified arithmetic shape). A candidate is
only ever appended to `pending` at the SAME bar `t = anchor_bar +
pivot_right` where its creation gate (`impulse_pass and (score >=
min_score or rescue_pass)`) is checked, and is immediately visited by
the SAME bar's confirmation loop afterward (this is a structural fact of
the control flow above, not a sampled/measured claim): at that first
visit, `candidate_age = t - c.pivot_bar = pivot_right` exactly, and
`candidate_age` only grows on every later bar the (still-pending)
candidate is revisited (`c.pivot_bar` is fixed, `t` increases). So the
guard can never observe `candidate_age < pivot_right`.

Calculation:
    Default Inputs:
        pivot_left=3, pivot_right=2, impulse_lookback=12,
        min_impulse_atr=2.00, min_reversal_atr=1.20,
        max_confirmation_bars=12, min_swing_separation_atr=1.50,
        context_bars=6, long_rsi_level=48.0, short_rsi_level=52.0,
        long_bb_level=0.35, short_bb_level=0.65,
        activity_volume_ratio=1.15, activity_range_atr=1.10,
        rejection_wick_ratio=0.25, min_score=3, enable_rescue_branch=True
    ATR(14), RSI(14), EMA(21) on close; Bollinger basis=SMA(20),
        deviation=STDEV(20, ddof=0)*2 (POPULATION stdev, matching Pine's
        `ta.stdev(..., biased=true)` default -- NOT this package's own
        `stdev()` default of ddof=1/sample), bbPosition=(close-lower)/
        (upper-lower) (0.5 if upper==lower or either is na); +DI/-DI via ADX(14);
        MACD(12,26,9) histogram; volumeRatio=volume/SMA(volume,20)
        (0.0 if the average is not > 0).
    A confirmed pivot low/high at anchor bar p (visible `pivot_right`
        bars later, at bar p+pivot_right) is scored on 5 factors (each 0
        or 1) -- for the LOW/long side:
            priorMove:  close[p] < close[p - context_bars]
            location:   bbPosition[p] <= long_bb_level OR close[p] < EMA21[p]
            momentum:   RSI[p] <= long_rsi_level OR -DI[p] > +DI[p]
            active:     volumeRatio[p] >= activity_volume_ratio
                            OR range[p]/ATR[p] >= activity_range_atr
            rejection:  lowerWick[p] >= rejection_wick_ratio
                            OR close[p] > open[p]
                            OR MACDh[p] > MACDh[p-1]
        (HIGH/short side mirrors every comparison direction.)
        impulse = (rolling `impulse_lookback`-bar high highest up to p)
            - pivotLow >= min_impulse_atr * ATR[p]   (mirrored for highs)
        admitted if impulse passes AND (score >= min_score OR
            (enable_rescue_branch AND score == 2 AND active AND rejection))
        Same-direction pending candidates: only the most price-extreme
            (lowest low / highest high) survives.
    Each bar, every pending candidate is checked: EXPIRED if its age
        (bars since its own anchor bar) exceeds max_confirmation_bars;
        REVERSAL-CONFIRMED if close has moved >= min_reversal_atr * (that
        candidate's own ATR) away from its pivot price, in its favor.
        A reversal-confirmed candidate fires (STURN_LONG/STURN_SHORT = 1
        at the CURRENT bar) only if no other candidate already fired this
        same bar, its direction differs from the last accepted signal's
        (ALTERNATION), and its pivot price is >= min_swing_separation_atr
        * max(its own ATR, the last accepted signal's ATR) away from the
        last accepted signal's price (SEPARATION). Either way (fired or
        not), an expired-or-reversal-confirmed candidate leaves the pool.
    STURN_SCORE / STURN_RESCUE are NaN except on a bar where STURN_LONG
        or STURN_SHORT is 1, where they carry that accepted candidate's
        own 0-5 score and whether it was admitted via the rescue branch
        (1.0) or the normal score >= min_score path (0.0).

Args:
    open_ (pd.Series): Series of 'open's
    high (pd.Series): Series of 'high's
    low (pd.Series): Series of 'low's
    close (pd.Series): Series of 'close's
    volume (pd.Series): Series of 'volume's
    pivot_left (int): Bars before the candidate pivot. Must be a
        positive int if given. Default: 3
    pivot_right (int): Bars after the candidate pivot required to
        confirm it (also the causal confirmation lag). Must be a
        positive int if given. Default: 2
    impulse_lookback (int): Rolling window (bars) for the preceding-
        impulse extreme. Must be a positive int if given. Default: 12
    min_impulse_atr (float): Minimum preceding impulse size, in ATR
        multiples. Must be >= 0 if given. Default: 2.00
    min_reversal_atr (float): Minimum reversal-from-pivot distance, in
        ATR multiples, to confirm a candidate. Must be >= 0 if given.
        Default: 1.20
    max_confirmation_bars (int): Max bars a candidate may remain pending
        before it expires unfired. Must be a positive int if given.
        Default: 12
    min_swing_separation_atr (float): Minimum distance, in ATR
        multiples, between an accepted signal's pivot price and the
        previous accepted signal's. Must be >= 0 if given. Default: 1.50
    context_bars (int): Bars back for the prior-direction context check.
        Must be a positive int if given. Default: 6
    long_rsi_level (float): RSI upper reference for a swing-low. Any
        finite value. Default: 48.0
    short_rsi_level (float): RSI lower reference for a swing-high. Any
        finite value. Default: 52.0
    long_bb_level (float): Bollinger-position upper reference for a
        swing-low. Any finite value. Default: 0.35
    short_bb_level (float): Bollinger-position lower reference for a
        swing-high. Any finite value. Default: 0.65
    activity_volume_ratio (float): Minimum volume/SMA(volume) ratio for
        an "active" bar. Must be >= 0 if given. Default: 1.15
    activity_range_atr (float): Minimum bar range, in ATR multiples, for
        an "active" bar. Must be >= 0 if given. Default: 1.10
    rejection_wick_ratio (float): Minimum rejection-wick fraction of the
        bar's own range. Must be >= 0 if given. Default: 0.25
    min_score (int): Minimum 5-factor score to admit a candidate outside
        the rescue branch. Must be a positive int if given. Default: 3
    enable_rescue_branch (bool): Allow a score==2 candidate through when
        both activity and rejection independently pass. Must be a bool
        if given. Default: True
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Raises:
    ValueError: any of the int-typed params given and not a positive
        (or, for `min_reversal_atr`'s sibling ints -- none are
        non-negative-only here) finite, integral value (NaN, +-inf, and
        non-integral floats like 3.7 all raise); any of the float-typed
        threshold/multiple params given and not a finite value (the
        ATR-multiple/ratio params additionally require >= 0; the RSI/BB
        level params do not, matching the source's own signed input
        range); `enable_rescue_branch` given and not a genuine bool.
        `None` (the actual default sentinel) still means "use the
        default," not an error.

Returns:
    pd.DataFrame: STURN_LONG, STURN_SHORT (0/1 event flags), STURN_SCORE
        (0-5, NaN unless a flag fired that bar), STURN_RESCUE (0.0/1.0,
        NaN unless a flag fired that bar).
"""
