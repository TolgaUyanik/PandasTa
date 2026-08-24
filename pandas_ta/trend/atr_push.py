# -*- coding: utf-8 -*-
import math

import numpy as np
from pandas import DataFrame, Series

from pandas_ta.volatility.atr import atr
from pandas_ta.utils import get_offset, verify_series


def _validated_int(value, default, name, positive=True):
    """None -> default (a normal, documented default, not bad input).
    Anything else must be a genuine, finite, integral value, or raise.
    Duplicated verbatim from `sd_zone_pro.py`/`inverse_fvg.py`'s helper
    of the same name (checks NaN/inf/non-integral explicitly before ever
    calling `int()`, so every rejection path is the same ValueError, not
    a mix of ValueError/OverflowError/silent truncation)."""
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


def atr_push(open_, high, low, close, atr_length=None, breakout_lookback=None,
             push_window=None, min_push_atr=None, max_push_candles=None,
             offset=None, **kwargs):
    """Indicator: ATR-Normalized Push Detection (APUSH)"""
    # Validate Arguments
    atr_length = _validated_int(atr_length, 14, "atr_length")
    breakout_lookback = _validated_int(breakout_lookback, 5, "breakout_lookback")
    push_window = _validated_int(push_window, 5, "push_window")
    min_push_atr = _validated_float(min_push_atr, 1.0, "min_push_atr")
    max_push_candles = _validated_int(max_push_candles, 5, "max_push_candles")
    offset = get_offset(offset)

    _min = max(atr_length, breakout_lookback + 1, push_window)
    open_ = verify_series(open_, _min)
    high = verify_series(high, _min)
    low = verify_series(low, _min)
    close = verify_series(close, _min)

    if open_ is None or high is None or low is None or close is None:
        return

    n = len(close)

    # --- Pine L336-347 -----------------------------------------------
    # `ta.atr(atrLength)` == RMA of True Range; pandas_ta's `atr`
    # defaults to mamode="rma", so this is the same recursion.
    atr_v = atr(high=high, low=low, close=close, length=atr_length)

    # 🔴 CAUSALITY, the one thing that is easy to get wrong here.
    # `ta.highest(high[1], breakoutLookback)` reads the series ALREADY
    # SHIFTED BY ONE BAR, so the window is bars t-1 .. t-breakoutLookback
    # and the CURRENT bar's own high is EXCLUDED. Dropping the `.shift(1)`
    # would let the current high enter its own breakout test. That is not
    # merely a weaker test, it is UNSATISFIABLE for valid OHLC: it asks
    # for `close > max(High over a window containing High[t])`, and
    # `close <= High[t]` always. The column goes silently DEAD -- it does
    # not degrade, it stops firing entirely (measured: 0 fires vs 41).
    # A mistranslation here yields a dead column, not a leak. `tests/test_atr_push.py` proves the difference with an
    # in-memory MUTANT of this module, not with an assertion.
    #
    # `min_periods` is left at the rolling default (== window), which
    # reproduces Pine's `ta.highest`/`ta.lowest` returning `na` during
    # warmup; NaN comparisons are False in pandas exactly as `na`
    # comparisons are false in Pine.
    prev_structure_high = high.shift(1).rolling(breakout_lookback).max()
    prev_structure_low = low.shift(1).rolling(breakout_lookback).min()

    # `ta.lowest(low, pushWindow)` / `ta.highest(high, pushWindow)` are
    # NOT shifted -- the impulse leg is measured from the push window's
    # extreme UP TO AND INCLUDING the current bar. That asymmetry is the
    # source's, and it is deliberate: the breakout leg asks "did this
    # close exceed prior structure", the push leg asks "how far has this
    # leg travelled by now".
    recent_push_low = low.rolling(push_window).min()
    recent_push_high = high.rolling(push_window).max()

    # --- Pine L349-386 -----------------------------------------------
    bullish_candle = close > open_
    bearish_candle = close < open_
    bullish_breakout = close > prev_structure_high
    bearish_breakout = close < prev_structure_low

    bull_leg = close - recent_push_low
    bear_leg = recent_push_high - close

    sufficient_bullish_push = bull_leg >= atr_v * min_push_atr
    sufficient_bearish_push = bear_leg >= atr_v * min_push_atr

    # `bar_index > math.max(breakoutLookback + 1, maximumPushCandles + 2)`.
    # `maximumPushCandles` is a ZONE-CANDLE input (Pine L58) whose only
    # other use is the declined zone-origin search (L582/L705); it enters
    # the ported half solely through this warmup gate, so it is kept as a
    # parameter rather than silently hard-coded.
    enough_history = Series(
        np.arange(n) > max(breakout_lookback + 1, max_push_candles + 2),
        index=close.index,
    )

    # `barstate.isconfirmed` is TRUE on every historical bar and only
    # false on the still-forming realtime bar. This port consumes
    # completed bars, so it is a no-op here. It is NOT a strictly-prior
    # guarantee -- the current bar's own open/high/low/close are used, by
    # design (see the push-window note above).
    bull_flag = (enough_history & bullish_candle & bullish_breakout
                 & sufficient_bullish_push)
    bear_flag = (enough_history & bearish_candle & bearish_breakout
                 & sufficient_bearish_push)

    # NaN-propagate the warmup instead of publishing a hard 0: before
    # `atr_v`/the rolling extremes exist the answer is "unknown", not
    # "no push". `strategy_miner`-style consumers treat the two very
    # differently.
    warm = atr_v.notna() & prev_structure_high.notna() & recent_push_low.notna()
    bull = bull_flag.astype(float).where(warm)
    bear = bear_flag.astype(float).where(warm)

    # NOTE: `bull_leg` / `bear_leg` are used ONLY inside the threshold
    # comparisons above. A continuous `leg / atr` form WAS built here and
    # was REMOVED after measurement -- see "THE CONTINUOUS STRENGTH FORM"
    # in the docstring below. Do not re-add it without re-measuring.

    # Offset
    if offset != 0:
        bull = bull.shift(offset)
        bear = bear.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        for s in (bull, bear):
            s.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        for s in (bull, bear):
            s.fillna(method=kwargs["fill_method"], inplace=True)

    _props = f"_{atr_length}_{breakout_lookback}_{push_window}"
    bull.name = f"APUSH_BULL{_props}"
    bear.name = f"APUSH_BEAR{_props}"

    df = DataFrame({
        bull.name: bull,
        bear.name: bear,
    })
    df.name = f"APUSH{_props}"
    df.category = "trend"
    return df


atr_push.__doc__ = """ATR-Normalized Push Detection (APUSH)

A structural breakout AND an ATR-scaled impulse leg, required together.
A bar qualifies as a bullish push when it closes green, closes above the
highest high of the `breakout_lookback` bars BEFORE it, and has travelled
at least `min_push_atr` x ATR up from the lowest low of the trailing
`push_window` bars (that window includes the current bar). Bearish is the
mirror.

Ported from the TradingView Pine v6 source "Buy and Sell Zones"
(`LStt7FmQ-Buy-and-Sell-Zones.pine`, `wc -l` = 1513; the file has no
trailing newline, so 1514 content lines). The push detector itself is
Pine L336-386. `enoughHistory` also reads `maximumPushCandles` (L58).

=== THE CONTINUOUS STRENGTH FORM: BUILT, MEASURED, REMOVED ============

Two further columns were built here and REMOVED before this landed:
`APUSH_STR_BULL` / `APUSH_STR_BEAR`, the impulse leg published raw in ATR
units -- `(close - lowest(low, push_window)) / atr` and its mirror. The
motivation was sound (a sparse 0/1 flag is hard for a tree miner to place
inside a conjunction), but they are near-duplicates of columns the
consuming engine already ships, and the measurement says so:

  APUSH_STR_BULL x dist_low_5        rho = +0.858779   n = 404,066
  APUSH_STR_BEAR x dist_from_high_5  rho = -0.845240   n = 404,066

That overlap is MEASURED, not an arithmetic identity. An earlier
revision of this docstring asserted the numerator and window were
IDENTICAL and only the divisor differed. That was written from memory,
not from the engine, and it is WRONG. The engine computes, verbatim
(`backtesting_engine/indicator_engine.py:1320-1324` in the consuming
repo):

        for n in (5, 21, 63):
            roll_low = low.shift(1).rolling(n, min_periods=max(1, n // 2)).min()
            df[f'dist_low_{n}'] = ((close - roll_low) / close.clip(lower=eps)).clip(lower=0.0)
            roll_high = high.shift(1).rolling(n, min_periods=max(1, n // 2)).max()

`APUSH_STR_BULL` was `(close - low.rolling(5).min()) / atr`: the same
STYLE of numerator over a ONE-BAR-OFFSET window, differing in FOUR ways,
not one.

  1. `.shift(1)`       -- the engine's window is t-5..t-1; ours was
                          t-4..t, and so INCLUDED the current bar.
  2. `min_periods`     -- the engine uses max(1, 5 // 2) = 2; ours was 5.
  3. `.clip(lower=0.0)`-- the engine cannot go negative; ours could.
  4. the divisor       -- `close` vs `atr`.

They are different series, and measurably so: the engine's real
`dist_low_5` correlates 0.915898 with the misquoted unshifted/unclipped
form (n=404,956), and `APUSH_STR_BULL` measures 0.858779 against the
engine-ACTUAL column (n=404,066) versus 0.92096 against the misquoted
one. The 0.858779 is NOT a separate number -- it IS the published grid
maximum for this pair, measured by the harness against the engine's real
column. Bear mirror: -0.845240 engine-actual vs -0.913926 misquoted.
(Fletcher round 2, MAJOR: an earlier revision gave 0.908 / 0.848 / 0.916,
which were a 25-frame subset reported as if full-universe. Re-measured
over all 89 cached BIST_100 daily frames.)

Difference 3 is load-bearing inside this very docstring: the DI-5
finding below depends on `APUSH_STR_BULL` being unshifted AND unclipped
-- that is the only reason it reached a pooled minimum of -1.01925,
while `dist_low_5` cannot go below 0. The identity claim and that
finding could never both have been true.

So 0.858779 is the MEASURED consequence of a NEAR-OVERLAPPING window
(4 of 5 bars shared) plus a slowly-varying divisor -- dividing by a
slowly-varying divisor is close to a monotone rescaling, so a rank
correlation barely moves. It is the same failure mode that got
`TOD_RVOL_REL`/`TOD_VVOL_REL` removed at 0.934/0.999, but it is an
empirical result, not a derivation.

THE REMOVAL IS CORRECT ON THE MEASUREMENT ALONE. 0.858779 was genuinely
measured over 404,066 pooled bars and sits above the project's 0.76-0.80
ship-with-disclosure band, near its ~0.9 revert precedent. That decision
stands on its own and never needed an identity argument.

The two 0/1 FLAGS were kept because the CONJUNCTION is what is actually
new here -- neither leg alone is novel, the requirement that both hold on
the same bar is. They measure far lower: max |rho| 0.508954
(APUSH_BULL x PPIVOT_VOLRATIO_10_10, n=329,922) and 0.488968
(APUSH_BEAR x BOS_BEAR, n=404,066), with 1 of 924 measured flag cells at
or above 0.5 and none at or above 0.6. Full grid:
`backtest_results/tvpta6/atr_push_overlap_20260815.md` in the consuming
repo.

⚠ A continuous form is NOT prohibited by the above, and the earlier
claim that any such form "must be of the CONJUNCTION" does not follow
from a single measured overlap. What the 0.858779 rules out is THIS
column -- an unshifted, unclipped, `min_periods=5`, ATR-divided bull leg
-- against THESE comparators on THIS universe. A form that shifts the
window, clips, or normalises differently is a DIFFERENT column and must
be MEASURED on its own rather than ruled out by inheritance. A form of
the conjunction remains the most likely to clear the band, because the
conjunction is not shipped anywhere, but that is a prior, not a rule.
Any such attempt must also carry a RELATIVE degenerate-ATR guard. Measured while the
removed columns existed: a bare `atr > 0` mask does NOT protect the
division, because on a perfectly flat frame `pandas_ta.atr` returns
2.22e-16 rather than 0.0; a frame whose push window reaches outside the
flat stretch then produced 4.50e+16. A floor of `1e-12 * |close|` handled
it. Recorded so the next attempt does not rediscover it.

=== WHAT THIS PORT DELIBERATELY DOES NOT SHIP =========================

The source's ZONE LIFECYCLE (Pine L390-1476) is NOT ported: the parallel
zone-state arrays (L394-449), zone creation (L575-951), and the
management / departure / retest / reaction / invalidation machine
(L952-1450).

The reason is OVERLAP AND EFFORT, not portability. It is roughly 500
logical lines whose concepts already have three modules in this fork --
`trend/ob.py` (order blocks), `trend/rejection_blocks.py` (wick-rejection
zones with a tap/spent lifecycle), and `trend/fvg.py` / `trend/
inverse_fvg.py` (gap zones with a mitigation lifecycle); see also
`trend/liquidity_compression_box.py`. Re-porting a fourth zone-pool
lifecycle would buy a fourth near-sibling of columns this fork already
measures.

⚠ It is explicitly NOT declined for being "held in drawing objects". A
prior survey of this file recorded that, and it is WRONG: L394-449
declare genuine `array<float>` / `array<int>` / `array<bool>` state
(`buyTops`, `buyBottoms`, `buyOriginBars`, `buyCreationBars`,
`buyTouchBars`, `buyDeparted`, `buyTouched`, `buyValidated`,
`buyInvalidated`, and the sell mirrors), with `array<box> buyBoxes`
(L394) / `array<box> sellBoxes` (L428) as a DISPLAY MIRROR of that state.
A grep for `box.|label.|line.|color.|bgcolor|border` matches 60 of the
file's 1514 content lines (`wc -l` reports 1513 only because the final
line is unterminated; `grep` counts it, and so must this ratio -- see
the `wc -l` note above, which had it right). The lifecycle is
portable; it is simply not worth its cost here.

⚠ RE-OPENABLE, genuinely unported second-tier concept: the source's
DEPARTURE -> RETEST -> REACTION ladder is NOT covered by any existing
module in this fork and is not claimed to be. A zone must first be
DEPARTED (`close >= top + atr * departureATR`, Pine L995-1010), then
RETESTED no sooner than `minimumRetestDelay` bars later, then produce a
REACTION of at least `reactionATR` within `reactionTimeLimit` bars, and
only then is it VALIDATED. `trend/band_cross_retest.py` is the closest
analogue this fork ships, but it is anchored on moving-band crosses, not
on zones, and has no departure precondition and no reaction deadline.
That ladder is a legitimate, separate future candidate.

Also NOT ported, as having no analogue or no value here: the pip
machinery (L317-330 -- `syminfo.mintick` / forex tick-size logic, no fork
equivalent), every colour input (L241-312), every `box.*` / `label.*`
call, the validation markers (L1451-1476) and the alerts (L1477+).

=== NOT A DUPLICATE ===================================================

`trend/bos.py` also detects a "break of structure", but against the LAST
CONFIRMED SWING high/low (`high.rolling(swing_length, center=True).max()`
-> a running `last_swing_high`), not against an N-bar
`highest(high[1], N)` window, and it carries NO ATR push-magnitude leg at
all. `trend/bdi4kewl.py` uses `ta.highest(high, impulseLookback)` but
INCLUDING the current bar, as one term of a pivot-anchored confluence
score. `trend/ob.py`'s "impulse close" compares against the single prior
bar's high. None of the three requires a prior-N-bar breakout AND an
ATR-scaled leg together, which is this indicator's whole content.

⚠ FORK-HYGIENE NOTE ON `trend/bos.py`, BLAST RADIUS ZERO. Its
`rolling(swing_length, center=True)` is genuinely NON-CAUSAL -- it reads
`swing_length // 2` bars into the future. The defect is real and worth a
low-priority fix. It is NOT, however, a live-book issue, and must not be
filed as one: `bos.py` is a DORMANT, UNREFERENCED module here. The
consuming repo's `IndicatorEngine` never imports it (`grep -c "bos"
backtesting_engine/indicator_engine.py` -> 0, and `bos` is absent from
its `pandas_ta.trend` import list); the engine computes `BOS_BULL` /
`BOS_BEAR` itself and CAUSALLY at `indicator_engine.py:549-552`, via
`_sh_vals.shift(2).ffill()` (mirrored at `speedy_indicators.py:412`).
The two `StrategyMaster.csv` rows mentioning `BOS_BULL` therefore use the
engine's causal column, not this one, and are NOT compromised by it.

Calculation:
    Default Inputs:
        atr_length=14, breakout_lookback=5, push_window=5,
        min_push_atr=1.0, max_push_candles=5
    atr_v         = ATR(atr_length)                  [RMA, == Pine ta.atr]
    prev_hi       = high.shift(1).rolling(breakout_lookback).max()
    prev_lo       = low.shift(1).rolling(breakout_lookback).min()
    push_lo       = low.rolling(push_window).min()   [includes this bar]
    push_hi       = high.rolling(push_window).max()  [includes this bar]
    enough        = bar_index > max(breakout_lookback + 1,
                                    max_push_candles + 2)
    APUSH_BULL    = enough and close > open and close > prev_hi
                    and (close - push_lo) >= atr_v * min_push_atr
    APUSH_BEAR    = enough and close < open and close < prev_lo
                    and (push_hi - close) >= atr_v * min_push_atr

    Both columns are NaN through warmup rather than 0 -- "unknown",
    not "no push".

Scale-freedom: both columns are invariant to a positive rescale of all
four price series -- the flags compare two price-scaled quantities
(`close - push_lo` vs `atr_v * min_push_atr`) against each other. Volume
is not read at all.

Args:
    open_ (pd.Series): Series of 'open's
    high (pd.Series): Series of 'high's
    low (pd.Series): Series of 'low's
    close (pd.Series): Series of 'close's
    atr_length (int): ATR period. Default: 14
    breakout_lookback (int): How many bars BEFORE the current bar the
        breakout reference high/low spans. Default: 5
    push_window (int): Trailing window, INCLUDING the current bar, whose
        extreme the impulse leg is measured from. Default: 5
    min_push_atr (float): Minimum impulse leg in ATR units. Default: 1.0
    max_push_candles (int): Source's zone-candle search depth; here it
        only widens the `enough_history` warmup gate. Default: 5
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.DataFrame: APUSH_BULL, APUSH_BEAR
"""
