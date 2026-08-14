# -*- coding: utf-8 -*-
import math

import numpy as np
from pandas import DataFrame, Series

from pandas_ta.momentum.macd import macd as _macd
from pandas_ta.overlap.ema import ema
from pandas_ta.overlap.sma import sma
from pandas_ta.utils import get_offset, verify_series


def _validated_int(value, default, name, positive=True):
    """None -> default (a normal, documented default, not bad input).
    Anything else must be a genuine, finite, integral value, or raise.
    Duplicated verbatim from `inverse_fvg.py`'s/`bdi4kewl.py`'s helper of
    the same name (checks NaN/inf/non-integral explicitly before ever
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
    return value


def macd_area_divergence(high, low, close, fast_len=None, mid_len=None,
                         slow_len=None, macd_fast=None, macd_slow=None,
                         macd_signal=None, shrink=None, offset=None, **kwargs):
    """Indicator: MACD-Histogram-Area Segment Divergence (MADIV)"""
    fast_len = _validated_int(fast_len, 20, "fast_len")
    mid_len = _validated_int(mid_len, 60, "mid_len")
    slow_len = _validated_int(slow_len, 120, "slow_len")
    macd_fast = _validated_int(macd_fast, 12, "macd_fast")
    macd_slow = _validated_int(macd_slow, 26, "macd_slow")
    macd_signal = _validated_int(macd_signal, 9, "macd_signal")
    shrink = _validated_float(shrink, 0.95, "shrink")

    # Every one of the six MAs plus the MACD triple does its OWN
    # `verify_series(length)` check and returns None (not a NaN-filled
    # Series) on a too-short frame, which would crash `.to_numpy()` even
    # after a smaller local floor passed -- same reasoning as
    # `inverse_fvg.py`'s min_len comment.
    min_len = max(fast_len, mid_len, slow_len, macd_fast, macd_slow, macd_signal)
    high = verify_series(high, min_len)
    low = verify_series(low, min_len)
    close = verify_series(close, min_len)
    offset = get_offset(offset)

    if high is None or low is None or close is None:
        return

    # --- The MA-alignment regime gate (source L27-28, L31-37). Reduced to
    # a plain boolean gate: this port ships NO ribbon/alignment column of
    # its own (`ribbon_concordance` already scores MA rank ordering and
    # `amat` already ships an MA-alignment trend). The gate is internal
    # state only. ---
    ema_f = ema(close, length=fast_len)
    ema_m = ema(close, length=mid_len)
    ema_s = ema(close, length=slow_len)
    sma_f = sma(close, length=fast_len)
    sma_m = sma(close, length=mid_len)
    sma_s = sma(close, length=slow_len)

    # NaN handling is Pine-identical by construction: in Pine `na > na` is
    # false, and in pandas any comparison against NaN is False, so during
    # the MA warmup both gates are False and `trend` holds its `var int
    # trend = 0` initial value -- no event can fire. See the WARMUP
    # section of the docstring.
    trend_up = (ema_f > ema_m) & (ema_f > ema_s) & (sma_f > sma_s) & (sma_f > sma_m)
    trend_dn = (ema_f < ema_m) & (ema_f < ema_s) & (sma_f < sma_s) & (sma_f < sma_m)

    # --- MACD (source L82). Reuses this package's own `macd()`, which is
    # Pine-shaped: `ta.ema` seeds with an SMA of the first `length` bars
    # and this fork's `ema()` defaults to `sma=True`, the same seeding. ---
    macd_df = _macd(close, fast=macd_fast, slow=macd_slow, signal=macd_signal)
    if macd_df is None:
        return
    hist_cols = [c for c in macd_df.columns if c.startswith("MACDh")]
    # `macd()` swaps fast/slow when slow < fast, so its column suffix can
    # differ from the arguments passed in -- select by prefix, never by a
    # reconstructed name.
    hist = macd_df[hist_cols[0]]

    n = len(close)
    high_v = high.to_numpy(dtype=float)
    low_v = low.to_numpy(dtype=float)
    hist_v = hist.to_numpy(dtype=float)
    tu_v = trend_up.to_numpy(dtype=bool)
    td_v = trend_dn.to_numpy(dtype=bool)

    top_flag = np.zeros(n, dtype=int)
    bot_flag = np.zeros(n, dtype=int)
    bull_area_r = np.full(n, np.nan)
    bear_area_r = np.full(n, np.nan)
    bull_px_r = np.full(n, np.nan)
    bear_px_r = np.full(n, np.nan)

    trend = 0                       # source `var int trend = 0`
    bull_high = np.nan              # source `var float bullHigh = na`
    bear_low = np.nan               # source `var float bearLow = na`
    # `bull_high_bar` / `bear_low_bar` are the source's `bullHighBar`
    # (L58, latched L68) / `bearLowBar` (L62, latched L74). They are
    # tracked here for faithfulness and DELIBERATELY NEVER WRITTEN TO:
    # they are the chart-LABEL anchor (`label.new(bullHighBar, ...)`,
    # L120 / L140), i.e. exactly the index a repainting port would use to
    # back-date a divergence onto the segment's extreme bar. See the
    # CAUSALITY section of the docstring;
    # `tests/test_macd_area_divergence.py::test_truncation_before_
    # confirmation_catches_backdating_mutant` builds a mutant that swaps
    # the write index to precisely these two variables and shows the
    # mutant repaints while this module does not.
    bull_high_bar = -1
    bear_low_bar = -1
    prev_bull_high_price = np.nan   # source `var float prevBullHighPrice = na`
    prev_bull_area = np.nan         # source `var float prevBullMacdArea = na`
    prev_bear_low_price = np.nan    # source `var float prevBearLowPrice = na`
    prev_bear_area = np.nan         # source `var float prevBearMacdArea = na`
    bull_accum = 0.0                # source `var float bullMacdAccum = 0.0`
    bear_accum = 0.0                # source `var float bearMacdAccum = 0.0`

    # Single sequential pass, in the source's own top-to-bottom per-bar
    # order: prevTrend snapshot -> trend update -> extreme latch -> flip
    # detection -> histogram accumulation -> divergence tests -> reset.
    # The order matters and is NOT cosmetic; see the ORDER OF OPERATIONS
    # section of the docstring.
    for j in range(n):
        # --- 1. `prevTrend = trend` (L32) reads the PREVIOUS bar's state,
        # before this bar's update (L34-37). ---
        prev_trend = trend
        if tu_v[j]:
            trend = 1
        elif td_v[j]:
            trend = -1

        # --- 2. Segment extreme latch (L65-75), using the JUST-UPDATED
        # trend. Pine's `math.max(na, x)` / `math.max(x, na)` propagate
        # `na`, so a NaN High poisons `bullHigh` rather than being
        # skipped -- reproduced literally. `high == bullHigh` is then
        # False (NaN never equals itself), so the bar index is not
        # latched, matching Pine. ---
        if trend == 1:
            h = high_v[j]
            if bull_high != bull_high:          # currently na
                bull_high = h
            elif h != h:                        # na High poisons the latch
                bull_high = np.nan
            else:
                bull_high = h if h > bull_high else bull_high
            if h == bull_high:
                bull_high_bar = j
        if trend == -1:
            lo = low_v[j]
            if bear_low != bear_low:
                bear_low = lo
            elif lo != lo:
                bear_low = np.nan
            else:
                bear_low = lo if lo < bear_low else bear_low
            if lo == bear_low:
                bear_low_bar = j

        # --- 3. Flip detection (L78-79). `trend` is sticky (only ever
        # assigned on a live trendUp/trendDown), so a flip is the FIRST
        # bar on which the opposite alignment becomes true. ---
        bull_to_bear = (prev_trend == 1) and (trend == -1)
        bear_to_bull = (prev_trend == -1) and (trend == 1)

        # --- 4. Per-bar histogram-area accumulation (L96-102). Bull
        # segments accumulate `max(hist, 0)`, bear segments
        # `max(-hist, 0)` -- both are non-negative "momentum area" sums.
        # Pine's `math.max` propagates `na`, so a NaN histogram bar makes
        # the whole accumulator `na` until its next reset; reproduced.
        # (Unreachable at defaults: MACD warms at bar ~34, the 120-bar MA
        # gate cannot admit a non-zero trend before bar 119 -- measured,
        # see the docstring's WARMUP section.) ---
        hv = hist_v[j]
        if trend == 1:
            if hv != hv:
                bull_accum = np.nan
            else:
                bull_accum = bull_accum + (hv if hv > 0.0 else 0.0)
        if trend == -1:
            if hv != hv:
                bear_accum = np.nan
            else:
                bear_accum = bear_accum + (-hv if -hv > 0.0 else 0.0)

        # --- 5. TOP divergence (L104-123). Price made a HIGHER segment
        # high than the previous bull segment, but the bull segment's
        # accumulated histogram area SHRANK below `shrink` x the previous
        # one -> structural top. `prev*` are updated UNCONDITIONALLY on
        # every structure point, fired or not (L116-117). ---
        if bull_to_bear and (bull_high == bull_high):
            # CAUSALITY WRITE SITE. `j` is the flip (confirmation) bar --
            # the first bar on which this divergence is knowable. The
            # source's label goes at `bull_high_bar`, in the past; this
            # port does not.
            top_write_idx = j
            is_div = False
            if (prev_bull_area == prev_bull_area) and (prev_bull_high_price == prev_bull_high_price):
                if bull_high > prev_bull_high_price and bull_accum < prev_bull_area * shrink:
                    is_div = True
                # Scale-free ratio columns -- this port's OWN addition,
                # not source math. The source compares raw magnitudes;
                # raw MACD area is price-scaled and NOT shippable here.
                # `prev_bull_area == 0` (a bull segment whose histogram
                # was never positive) leaves the ratio NaN rather than
                # inf: undefined, not infinite. Note the flag is
                # unaffected -- `accum < 0 * shrink` is False for any
                # non-negative accum, matching Pine.
                if prev_bull_area > 0.0:
                    bull_area_r[top_write_idx] = bull_accum / prev_bull_area
                if prev_bull_high_price > 0.0:
                    bull_px_r[top_write_idx] = bull_high / prev_bull_high_price
            prev_bull_high_price = bull_high
            prev_bull_area = bull_accum
            if is_div:
                top_flag[top_write_idx] = 1

        # --- 6. BOTTOM divergence (L125-143), the exact mirror. ---
        if bear_to_bull and (bear_low == bear_low):
            bot_write_idx = j
            is_div = False
            if (prev_bear_area == prev_bear_area) and (prev_bear_low_price == prev_bear_low_price):
                if bear_low < prev_bear_low_price and bear_accum < prev_bear_area * shrink:
                    is_div = True
                if prev_bear_area > 0.0:
                    bear_area_r[bot_write_idx] = bear_accum / prev_bear_area
                if prev_bear_low_price > 0.0:
                    bear_px_r[bot_write_idx] = bear_low / prev_bear_low_price
            prev_bear_low_price = bear_low
            prev_bear_area = bear_accum
            if is_div:
                bot_flag[bot_write_idx] = 1

        # --- 7. Segment reset (L164-172). Note the asymmetry the source
        # itself has: the extreme goes back to `na`, the accumulator back
        # to `0.0` (not `na`). ---
        if bull_to_bear:
            bull_high = np.nan
            bull_high_bar = -1
            bull_accum = 0.0
        if bear_to_bull:
            bear_low = np.nan
            bear_low_bar = -1
            bear_accum = 0.0

    top_s = Series(top_flag, index=close.index)
    bot_s = Series(bot_flag, index=close.index)
    # The four ratios are written only on structure points; forward-fill
    # so each one reads "the most recent same-side structure reading".
    # Forward fill is strictly causal (it copies a past bar's value
    # forward, never a future bar's backward) and leaves the pre-first-
    # event prefix NaN.
    bull_area_s = Series(bull_area_r, index=close.index).ffill()
    bear_area_s = Series(bear_area_r, index=close.index).ffill()
    bull_px_s = Series(bull_px_r, index=close.index).ffill()
    bear_px_s = Series(bear_px_r, index=close.index).ffill()

    _all = (top_s, bot_s, bull_area_s, bear_area_s, bull_px_s, bear_px_s)

    if offset != 0:
        top_s = top_s.shift(offset)
        bot_s = bot_s.shift(offset)
        bull_area_s = bull_area_s.shift(offset)
        bear_area_s = bear_area_s.shift(offset)
        bull_px_s = bull_px_s.shift(offset)
        bear_px_s = bear_px_s.shift(offset)
        _all = (top_s, bot_s, bull_area_s, bear_area_s, bull_px_s, bear_px_s)

    if "fillna" in kwargs:
        for s in _all:
            s.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        for s in _all:
            s.fillna(method=kwargs["fill_method"], inplace=True)

    _props = f"_{fast_len}_{mid_len}_{slow_len}"
    top_s.name = f"MADIV_TOP{_props}"
    bot_s.name = f"MADIV_BOT{_props}"
    bull_area_s.name = f"MADIV_BULL_AREA_R{_props}"
    bear_area_s.name = f"MADIV_BEAR_AREA_R{_props}"
    bull_px_s.name = f"MADIV_BULL_PX_R{_props}"
    bear_px_s.name = f"MADIV_BEAR_PX_R{_props}"

    df = DataFrame({
        top_s.name: top_s,
        bot_s.name: bot_s,
        bull_area_s.name: bull_area_s,
        bear_area_s.name: bear_area_s,
        bull_px_s.name: bull_px_s,
        bear_px_s.name: bear_px_s,
    })
    df.name = f"MADIV{_props}"
    df.category = "momentum"

    return df


macd_area_divergence.__doc__ = \
"""MACD-Histogram-Area Segment Divergence (MADIV)

A SEGMENT-ACCUMULATION divergence detector, structurally different from
the classic pivot-pair kind.

A moving-average alignment gate cuts the series into alternating BULL and
BEAR segments. Inside each segment two things are latched: the segment's
price extreme (highest High in a bull segment, lowest Low in a bear one)
and the segment's "momentum area" -- the running sum of the POSITIVE MACD
histogram in a bull segment, of the absolute NEGATIVE histogram in a bear
one. When the gate flips, the just-closed segment is compared with the
previous segment of the same side:

    TOP divergence  (bull -> bear flip):
        segment high  >  previous bull segment high        AND
        segment area  <  previous bull segment area * 0.95

    BOTTOM divergence (bear -> bull flip):
        segment low   <  previous bear segment low         AND
        segment area  <  previous bear segment area * 0.95

i.e. price extended further but the trend spent LESS accumulated momentum
doing it.

Source: TradingView community indicator "趋势结构系统均线共振版" (Trend
Structure System, MA Resonance Edition), https://www.tradingview.com/
script/iOd2A4mw/ (ported into AwakenAnalytics/Backtesting TVPTA-6
candidate 15; MPL-2.0 per TradingView's open-source publication
convention). Pine v6, 173 lines.

WHAT IS NOT PORTED (all verified against the source, line by line):
  * The 6-MA ribbon itself (L9-14) and its six `plot()` calls (L16-21).
    The alignment condition (L27-28) is kept, but ONLY as an internal
    boolean gate -- no ribbon/alignment column is shipped. This package
    already has `trend/ribbon_concordance` (MA rank-ordering score) and
    `trend/amat` (MA-alignment trend), and a third alignment column
    would be a re-shipping of the same idea.
  * The ATR trend line (L24, L40-54): `trendLine` is a running max of
    `low - ATR(14)` in an uptrend / running min of `high + ATR(14)` in a
    downtrend, reset on flip -- that is a plain ATR trailing stop, which
    `overlap/supertrend` and `trend/halftrend` already cover.
  * Every `label.new` (L119-123, L139-143) and the structure-point
    connecting lines (L145-161), including the `bullHighTime` /
    `bearLowTime` / `lastPointTime` / `lastPointPrice` state that exists
    only to feed them. Drawing, not signal.
  * The two display toggles `showBullLabels` / `showBearLabels`
    (L5-6, gating L119 / L139): they gate drawing only, never the
    `isDivergence` computation, so they have no numeric effect.

RELATIONSHIP TO WHAT THIS PACKAGE ALREADY SHIPS (grepped, not assumed):
  * `momentum/rsi_divergence` is this package's only other divergence
    detector. It is PIVOT-PAIR based (`_confirm_strict_pivots` with
    `pivot_left`/`pivot_right`, then a `min_lookback`/`max_lookback`
    window between two confirmed pivots of the same type) and compares a
    LEVEL (RSI read at the pivot bar). MADIV compares an AREA accumulated
    over a variable-length regime segment, and its segmentation comes
    from an MA gate, not from pivots. Different mechanism, different
    event timing.
  * `volume/weis_wave` is the closest MECHANISM neighbour in the package
    -- it, too, accumulates a per-bar quantity over variable-length
    price-structure segments and resets on a direction flip. Three
    differences: it accumulates VOLUME (or True Range), not MACD
    histogram; its segmentation is a Renko box reversal, not an MA
    alignment gate; and it carries NO cross-segment memory at all, so it
    cannot express a divergence (there is no previous-segment
    comparison in it).
  * A grep for a MACD-histogram area/accumulator across `momentum/` and
    `trend/` (`hist.*(area|accum|cumsum|segment)` and the reverse)
    returned ZERO hits.

COLUMNS
  MADIV_TOP_{fast}_{mid}_{slow}
      0/1. 1 on the bull->bear flip bar where a TOP divergence confirmed.
      Dense (0 elsewhere, including the warmup).
  MADIV_BOT_{fast}_{mid}_{slow}
      0/1 mirror, on the bear->bull flip bar.
  MADIV_BULL_AREA_R_{fast}_{mid}_{slow}
      The just-closed bull segment's histogram area divided by the
      PREVIOUS bull segment's. Written on the flip bar and forward-filled
      until the next bull structure point. < `shrink` (0.95) is the
      momentum leg of a top divergence. NaN before the second bull
      structure point (nothing to compare with), and NaN when the
      previous area was exactly 0.
  MADIV_BEAR_AREA_R_{fast}_{mid}_{slow}
      Mirror, on bear segments.
  MADIV_BULL_PX_R_{fast}_{mid}_{slow}
      The just-closed bull segment's high divided by the previous bull
      segment's high; forward-filled the same way. > 1 is the price leg
      of a top divergence.
  MADIV_BEAR_PX_R_{fast}_{mid}_{slow}
      Mirror: segment low / previous bear segment low. < 1 is the price
      leg of a bottom divergence.

SCALE-FREE
⚠ MACD is PRICE-SCALED (this project's own `Backtesting/CLAUDE.md` says
so explicitly, in contrast to RSI/CCI/ADX which are format-clean), so a
RAW accumulated histogram area is NOT scale-free and is deliberately NOT
shipped. What is shipped are RATIOS of two areas (and of two prices) on
the same instrument, in which the price scale cancels, plus the two
boolean flags. Multiplying every input series by a constant leaves all
six columns unchanged; with a power-of-two constant the invariance is
BIT-EXACT (an exponent shift introduces no rounding), which is what
`tests/test_macd_area_divergence.py::test_scale_invariance_exact_power_
of_two` asserts. A x10 variant asserts the same to floating tolerance.

⚠ Being scale-free is NOT an endorsement of MACD as a feature. In this
project the MACD/PPO cluster has a grep-verified mining track record of
ZERO -- no mined rule has ever selected a MACD or PPO column. The
hypothesis under test here is a DIVERGENCE STRUCTURE (a cross-segment
area comparison), not a MACD level; it inherits none of that record's
support.

CAUSALITY
Everything a bar's output depends on is known at that bar's close. The
one real back-dating risk is structural, not arithmetic: a divergence is
only KNOWABLE at the flip bar, but the source draws its label at
`bullHighBar` / `bearLowBar` -- the segment's extreme bar, which is in
the past. Writing the flag there would back-date a fact by the whole
length of the segment. This port writes at the flip bar. `bull_high_bar`
/ `bear_low_bar` are tracked but never written to, and the test suite
builds a MUTANT of this module (source read via `importlib`, the two
write-site indices textually swapped to those two variables, exec'd into
an in-memory module) and truncates the input BEFORE confirmation: the
mutant then disagrees with itself between the full and truncated runs,
while this module does not. A prefix-truncation test alone cannot detect
back-dating -- both runs reach the same event and back-date identically.

ORDER OF OPERATIONS (load-bearing, matches the source's single
top-to-bottom per-bar execution)
On a bull->bear flip bar, `trend` is already -1 by the time the extreme
latch runs, so: the BEAR segment's low and histogram area already include
that bar, while the top-divergence test sees the bull segment WITHOUT it.
The bull reset then runs last. Reordering any of these changes results.

WARMUP
The gate mixes EMA and SMA at 20/60/120 by default. This fork's `ema()`
seeds with an SMA of the first `length` bars (`sma=True`), so `ema(120)`
and `sma(120)` are both NaN until bar index 119. Every comparison against
NaN is False, so `trend` cannot leave its initial 0 and NO event can fire
before index `slow_len - 1`; the flags are a legitimate 0 there (no event
occurred) and the four ratios are NaN. `verify_series` additionally
refuses a frame shorter than `max(fast_len, mid_len, slow_len, macd_fast,
macd_slow, macd_signal)`. MACD (26+9) warms far earlier than the 120-bar
gate, which is why the NaN-histogram accumulator branch is unreachable at
default parameters.

Args:
    high (pd.Series): Series of 'high's
    low (pd.Series): Series of 'low's
    close (pd.Series): Series of 'close's
    fast_len (int): Short MA length for the alignment gate. Default: 20
    mid_len (int): Middle MA length. Default: 60
    slow_len (int): Long MA length. Default: 120
    macd_fast (int): MACD fast EMA length. Default: 12
    macd_slow (int): MACD slow EMA length. Default: 26
    macd_signal (int): MACD signal EMA length. Default: 9
    shrink (float): Area-shrink factor a segment must fall under to
        qualify as a divergence. Default: 0.95
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.DataFrame: MADIV_TOP, MADIV_BOT, MADIV_BULL_AREA_R,
        MADIV_BEAR_AREA_R, MADIV_BULL_PX_R, MADIV_BEAR_PX_R columns.
"""
