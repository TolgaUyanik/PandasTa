# -*- coding: utf-8 -*-
import numpy as np
import pandas as pd
from pandas import Series
from pandas_ta.volatility import atr as _atr
from pandas_ta.utils import get_offset, verify_series

# TVPTA-6 acceptance gates (a)-(f) -- all six required before this port is done:
# (a) Causality: no look-ahead. This is an IIR recursion (`ima[t]` depends
#     on `ima[t-1]`), so "causal" means mutating bar T changes bar T and
#     every bar AFTER it, and NEVER a bar before T -- verified by test
#     (test_mutation_only_changes_current_and_later_bars), not inferred
#     from the loop's shape.
# (b) Pine->pandas semantics verified against the FORK's source, not
#     memory -- see "OVERLAP CHECK" below for the kama()/vidya() diff.
# (c) Reachable via df.ta.iama() -- core.py registration required.
# (d) Numeric correctness spot-checked against the source .pine's own math
#     (docs/TradingView/pine/6SVLw0kE-Institutional-Moving-Averages.pine
#     L122-133), not just "runs without crashing" -- see
#     test_correctness_vs_independent_reference_default_params /
#     _custom_params (an independently-derived per-bar reference
#     implementation, not a copy of this file's vectorized code) and
#     test_bar_zero_is_closed_form (the trivial out[0]==close[0] identity).
# (e) Docstring names source URL + author.
# (f) Test asserts real behavior (hand-computed fixture, causality by
#     mutation AND truncation, canary-guarded fixture, scale-free
#     verified by execution) -- not just "returns a Series".
#
# This is a partial port of "Institutional Moving Averages" (6SVLw0kE).
# Only `f_ima` (L122-133 of the .pine) is ported -- the adaptive-MA engine
# itself. NOT ported: the 5-length MA stack that calls f_ima five times
# with chained inputs (`maFast`/`maMed`/`maSlow`/`maPri`/`maSec`, L156-165),
# the composite 0-100 trend-strength score (L173-199), the bull/bear regime
# state machine (L202-209), the 3-tier buy/sell signal engine with
# cooldowns (L258-307), the adaptive ribbon / dashboard / drawing code
# (L228-416), and the dynamic S/R envelope (L167-170). Each of those is a
# separate, stateful sub-system built ON TOP of f_ima's output, not part
# of the adaptive-MA formula itself -- porting them is out of scope for
# this candidate (see the TVPTA-3 CSV row's own "disproportionate to port
# as one function" reasoning).


def _validate_length(value, name, default, minval, maxval=None):
    if value is None:
        return default
    if isinstance(value, bool) or not isinstance(value, (int, float, np.integer, np.floating)):
        raise ValueError(f"{name} must be numeric, got {type(value).__name__}: {value!r}")
    if not np.isfinite(value):
        raise ValueError(f"{name} must be finite, got {value}")
    if float(value) != int(value):
        raise ValueError(f"{name} must be integral, got {value}")
    value = int(value)
    if value < minval or (maxval is not None and value > maxval):
        bound = f">= {minval}" if maxval is None else f"in [{minval}, {maxval}]"
        raise ValueError(f"{name} must be {bound} (Pine source's own input bounds), got {value}")
    return value


def _validate_float(value, name, default, minval, maxval):
    if value is None:
        return default
    if isinstance(value, bool) or not isinstance(value, (int, float, np.integer, np.floating)):
        raise ValueError(f"{name} must be numeric, got {type(value).__name__}: {value!r}")
    value = float(value)
    if not np.isfinite(value):
        raise ValueError(f"{name} must be finite, got {value}")
    if not (minval <= value <= maxval):
        raise ValueError(f"{name} must be in [{minval}, {maxval}] (Pine source's own input bounds), got {value}")
    return value


def _validate_positive_float(value, name, default):
    if value is None:
        return default
    if isinstance(value, bool) or not isinstance(value, (int, float, np.integer, np.floating)):
        raise ValueError(f"{name} must be numeric, got {type(value).__name__}: {value!r}")
    value = float(value)
    if not np.isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be finite and positive, got {value}")
    return value


def iama(high, low, close, length=None, k=None, atr_length=None,
         norm_length=None, min_tick=None, rel_floor=None, offset=None,
         **kwargs):
    """Indicator: Institutional Adaptive MA distance (IAMA_DIST)

    Ports ONLY `f_ima` (Pine L122-133) -- an efficiency-ratio- and
    volatility-adaptive moving average. Returns the scale-free PERCENT
    DISTANCE of price from that adaptive line, `(close - ima) / ima * 100`,
    NOT the raw line itself -- see the module docstring "SCALE-FREE OUTPUT"
    for why.
    """
    # Validate Arguments
    high = verify_series(high)
    low = verify_series(low)
    close = verify_series(close)
    offset = get_offset(offset)
    if any(s is None for s in (high, low, close)):
        return

    for name, s in (("high", high), ("low", low), ("close", close)):
        if not pd.api.types.is_numeric_dtype(s):
            raise ValueError(f"{name} must be numeric, got dtype {s.dtype}")
        arr = s.to_numpy(dtype="float64", copy=False)
        if not np.isfinite(arr).all():
            raise ValueError(
                f"{name} contains non-finite values (nan/inf) -- iama is a recursive "
                "(IIR) indicator: ima[t] depends on ima[t-1], so an un-vetted NaN/inf "
                "could poison every subsequent bar's output, not just a `length`-bar "
                "window (the self-heal branch below only resets on a NaN it computed "
                "itself, not on NaN handed in from outside), so it is rejected here at "
                "the API boundary instead -- see tests/test_iama.py::test_single_nan_close_raises."
            )

    n = len(close)
    if not (len(high) == len(low) == n):
        raise ValueError(f"high/low/close must be the same length, got {len(high)}/{len(low)}/{n}")

    # Length-type params. Minvals/maxvals mirror the Pine source's own
    # input.int declarations exactly: lenFast/lenMed/lenSlow/lenPri/lenSec
    # all share `minval=2` (L42-46) -- f_ima's `len` argument is used
    # generically across all five roles, so 2 is the honest floor here,
    # not the specific default (9) any one of them happens to use.
    # atrLen: input.int(14, minval=2, maxval=200, L36). normLen:
    # input.int(50, minval=10, maxval=300, L38).
    length = _validate_length(length, "length", 9, minval=2)
    atr_length = _validate_length(atr_length, "atr_length", 14, minval=2, maxval=200)
    norm_length = _validate_length(norm_length, "norm_length", 50, minval=10, maxval=300)

    # k mirrors Pine's `sens` input.float(1.0, minval=0.1, maxval=3.0, L35).
    k = _validate_float(k, "k", 1.0, minval=0.1, maxval=3.0)

    # min_tick / rel_floor: the source's `syminfo.mintick` (L124, used only
    # as a divide-by-zero floor under the slope term) has no equivalent on
    # a bare OHLC Series -- no symbol/exchange context. Unlike
    # pressure_pulse's floor (feeding a *linear* clip, where an
    # under-floored ratio can blow through the clip and flip sign), this
    # floor feeds `f_squash(x) = x/(1+|x|)`, which is bounded in [0, 1) for
    # any non-negative x regardless of magnitude -- a huge or
    # floor-inflated ratio just saturates squash toward 1, it cannot flip
    # sign (the numerator |close - close.shift(k)| is never negative). So
    # this floor is numerical hygiene (avoid an explicit 0/0 -> nan or
    # x/0 -> inf on a genuinely flat ATR run), not a correctness fix in
    # the pressure_pulse sense -- see test_flat_price_eff_and_slope_are_zero
    # (a flat-OHLC fixture that exercises this exact path without raising
    # or producing a divide warning).
    if min_tick is None:
        min_tick = 1e-8
    else:
        min_tick = _validate_positive_float(min_tick, "min_tick", 1e-8)
    if rel_floor is None:
        rel_floor = 2.5e-3
    else:
        rel_floor = _validate_positive_float(rel_floor, "rel_floor", 2.5e-3)

    min_required = max(length + 1, atr_length, norm_length)
    if n < min_required:
        return

    # Calculate Result
    idx = close.index
    h = high.to_numpy(dtype="float64", copy=False)
    lo = low.to_numpy(dtype="float64", copy=False)
    c = close.to_numpy(dtype="float64", copy=False)

    # --- f_efficiency(s, len) (Pine L103-106) ---
    # dir = |s - s[len]|, pth = SUM(|s - s[1]|, len) (a trailing len-bar
    # rolling sum), eff = pth>0 ? min(dir/pth, 1) : 0. Both dir and pth are
    # only defined once `length` bars of history exist (Pine's own
    # historical-reference-return-na semantics on `s[len]`/`math.sum` with
    # insufficient bars) -- reproduced here for free: `close.diff(length)`
    # and a `length`-window `.rolling().sum()` are both NaN for the first
    # `length` rows, and NaN propagates through the division naturally, no
    # explicit masking needed. Only the genuine pth==0 (flat-price window,
    # full history) case needs an explicit 0.0 substitution, since 0/0 is
    # NaN in Pine too but Pine's ternary explicitly routes it to 0.0, not na.
    dir_ = (close - close.shift(length)).abs().to_numpy(dtype="float64", copy=False)
    step = close.diff(1).abs()
    pth = step.rolling(length).sum().to_numpy(dtype="float64", copy=False)
    with np.errstate(divide="ignore", invalid="ignore"):
        ratio = dir_ / pth
    eff = np.minimum(ratio, 1.0)
    zero_pth = np.isfinite(pth) & (pth == 0.0)
    eff = np.where(zero_pth, 0.0, eff)

    # --- ATR + volRatio (Pine L138-140, computed once and reused) ---
    atr_series = _atr(high, low, close, length=atr_length, mamode="rma")
    atr_arr = atr_series.to_numpy(dtype="float64", copy=False) if atr_series is not None else np.full(n, np.nan)
    atr_avg_arr = pd.Series(atr_arr, index=idx).rolling(norm_length).mean().to_numpy(dtype="float64", copy=False)
    with np.errstate(divide="ignore", invalid="ignore"):
        vol_ratio_raw = atr_arr / atr_avg_arr
    vol_ratio = np.where(np.isfinite(atr_avg_arr) & (atr_avg_arr > 0), vol_ratio_raw, 1.0)

    # --- slope (Pine L124) ---
    # slope_len = max(1, round(len/3.0)); slope = |s - s[slope_len]| /
    # max(atr, mintick). NOTE: unlike pressure_pulse's atr substitution
    # (which falls back to High-Low when ta.atr() is undefined), no such
    # fallback is applied here -- during ATR's own warmup (`atr_arr` is
    # NaN), the floor `np.maximum(nan, tick_floor)` stays NaN (numpy's
    # `maximum`, not `fmax`, propagates NaN), so slope/drive/alpha/ima are
    # all NaN for those bars too, then the recursion's own na(out[1])
    # self-heal (see below) resets back to `close` on the following bar.
    # This is a judgment call: Pine's own na-propagation rules for
    # `math.max(na, x)` were not independently verified against the live
    # TradingView runtime (no such runtime available here) -- the
    # NaN-propagating choice was made because it matches this fork's
    # general convention (kama.py/vidya.py both leave warmup NaN rather
    # than substituting a proxy) and is the more conservative of the two
    # readings, not because Pine's exact na-arg behavior was confirmed.
    # round-half-up (`floor(x+0.5)`) vs Python's banker's-rounding `round()`
    # would only diverge on an exact .5 tie -- provably UNREACHABLE here,
    # not merely untested at the shipped default: for integer `length`,
    # `length/3.0 mod 1` is always in {0, 1/3, 2/3}, never 0.5 (`length`
    # would need to be an odd multiple of 1.5, impossible for an integer).
    # Verified by brute force over length in [2, 2000] during the TVPTA-6
    # candidate-12 Fletcher review, 2026-08-14 -- the rounding-mode choice
    # is a dead branch, not a live judgment call.
    slope_len = max(1, int(np.floor(length / 3.0 + 0.5)))
    slope_num = (close - close.shift(slope_len)).abs().to_numpy(dtype="float64", copy=False)
    tick_floor = np.maximum(min_tick, rel_floor * np.abs(c))
    safe_atr_slope = np.maximum(atr_arr, tick_floor)
    with np.errstate(divide="ignore", invalid="ignore"):
        slope = slope_num / safe_atr_slope

    # --- drive, vAdj, fastA/slowA, alpha (Pine L125-130) ---
    squash_slope = slope / (1.0 + np.abs(slope))
    drive = np.minimum(1.0, 0.65 * eff + 0.35 * squash_slope)
    v_adj = np.clip(vol_ratio, 0.6, 1.5)
    fast_a = 2.0 / (max(2.0, length / (2.0 + k)) + 1.0)
    slow_a = 2.0 / (length * (1.0 + k * 0.5) + 1.0)
    alpha = np.power(slow_a + drive * (fast_a - slow_a), 2.0) * v_adj
    alpha = np.clip(alpha, 0.001, 1.0)

    # --- out (Pine L131-133) ---
    # out := na(out[1]) ? s : out[1] + alpha*(s - out[1]). Bar 0's out[1]
    # doesn't exist (na) -> out[0] = close[0]. From bar 1 on, if the
    # PREVIOUS bar's out is na (e.g. because that bar's alpha was na
    # during warmup), the current bar resets to close[t] rather than
    # propagating na forever -- a self-healing recursion, not a one-shot
    # seed. Reproduced with an explicit loop (an IIR recursion with a
    # conditional reset is not vectorizable) -- same approach as
    # kama.py/pressure_pulse.py's own hand-rolled loops in this fork.
    ima = np.empty(n, dtype="float64")
    for t in range(n):
        prev = ima[t - 1] if t > 0 else np.nan
        if np.isnan(prev):
            ima[t] = c[t]
        else:
            ima[t] = prev + alpha[t] * (c[t] - prev)

    # --- SCALE-FREE OUTPUT ---
    # ima itself is a price LEVEL (drifts with the instrument's nominal
    # price, does not generalize across tickers/time -- the exact reason
    # this project's register excludes raw MA columns, see
    # docs/indicators/family-moving-avg-smoother.md and the ma_disparity
    # precedent, pandas_ta/overlap/ma_disparity.py). Only the PERCENT
    # DISTANCE of price from the line is returned.
    with np.errstate(divide="ignore", invalid="ignore"):
        dist_pct = (c - ima) / ima * 100.0

    result = Series(dist_pct, index=idx)

    # Offset
    if offset != 0:
        result = result.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        result.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        result.fillna(method=kwargs["fill_method"], inplace=True)

    # Name & Category
    result.name = f"IAMA_DIST_{length}_{k}_{atr_length}_{norm_length}"
    result.category = "overlap"

    return result


iama.__doc__ = \
"""Institutional Adaptive MA distance (IAMA_DIST)

Source: TradingView community indicator "Institutional Moving Averages" by
Michael_Fx_Trader,
https://www.tradingview.com/script/6SVLw0kE-Institutional-Moving-Averages/
(ported into AwakenAnalytics/Backtesting TVPTA continuation, TVPTA-6
candidate 12)

Pine function replaced: `f_ima` only (`docs/TradingView/pine/
6SVLw0kE-Institutional-Moving-Averages.pine` L122-133), the source's
adaptive-MA engine. NOT ported: the 5-length MA stack that calls f_ima
five times with chained inputs (maFast/maMed/maSlow/maPri/maSec, L156-165),
the 0-100 trend-strength composite (L173-199), the bull/bear regime state
machine (L202-209), the 3-tier signal engine with cooldowns (L258-307),
the dynamic S/R envelope (L167-170), and all ribbon/dashboard/drawing code
(L228-416). Each is a separate stateful system built on TOP of f_ima's
output -- porting the engine alone matches the CSV row's own "large
multi-stage original system, disproportionate to port as one function;
f_ima alone could be a scoped future candidate" call.

OVERLAP CHECK (mandatory before this port was written, per TVPTA-6):
f_ima is structurally closest to `kama()` (pandas_ta/overlap/kama.py) --
both are IIR adaptive-EMA recursions gated by an EFFICIENCY RATIO
(`dir/pth`, Kaufman's own formula, identical math to f_ima's `eff`
sub-term: kama.py's `er = abs_diff / peer_diff_sum` uses the same
`|close-close.shift(len)| / rolling(len).sum(|diff|)` construction as
f_ima's `f_efficiency`). Where they diverge, verified by reading both
source files line-by-line:
  1. kama's smoothing constant (`sc = (er*(fr-sr)+sr)**2`) is driven by
     `er` ALONE; f_ima's `drive = min(1, 0.65*eff + 0.35*squash(slope))`
     blends the SAME efficiency ratio with a second, independent
     structural-slope term (`|close-close.shift(len/3)| / ATR`, squashed)
     that kama has no equivalent of at all.
  2. f_ima's alpha additionally multiplies by a volatility-regime term
     (`vAdj = clip(ATR/SMA(ATR,normLen), 0.6, 1.5)`) that kama does not
     have -- kama's `sc` depends only on `er`, never on ATR/volatility.
  3. f_ima's fast/slow EMA bounds (`fastA`/`slowA`) are parameterized by
     `k` (sensitivity) via `len/(2+k)` and `len*(1+k*0.5)`, a different
     shape than kama's fixed `2/(fast+1)`/`2/(slow+1)` bound pair.
`vidya()` (pandas_ta/overlap/vidya.py) is a more distant sibling: its
adaptive term is `|CMO(length)|` (Chande Momentum Oscillator, a SIGNED
sum-of-gains-vs-losses ratio), not an efficiency ratio at all -- a
different volatility-adaption mechanism, not compared numerically here
since kama is the closer analog by construction.

MEASURED OVERLAP IS HIGH -- read before treating this as a novel feature.
This section went through TWO rounds of Fletcher review (TVPTA-6
candidate 12, 2026-08-14), each catching a different flavor of the same
mistake -- publishing a number without executing the exact thing it was
labeled as. Round 1: the first version measured `IAMA_DIST` against
`dist_to_kama`, a HYPOTHETICAL feature nobody had built, and argued that
made the overlap tolerable ("not an existing shipped column") -- wrong,
because it never checked the Backtesting project's OWN mineable feature
set. Round 2: the fix for round 1 introduced a NEW error -- a
`mkt_kama_pos` row computed as `close/kama(10,2,30)-1` on each TICKER's
own close and labeled "the project's own already-shipped kama distance
feature", when the REAL `mkt_kama_pos` (`indicator_engine.py:376`, inside
`compute_market_trend`) is computed on the XU100.IS INDEX's close and
broadcast to every ticker -- a different, much less correlated signal.
Round 2 also found the "every OK-verdict column" claim was never checked
against `NWE_MID_200_8.0_8.0`, which turns out to overlap MORE than
`bias`.

**Verified, current numbers** (40 BIST_100 tickers, `datastore/cache/
*_1d.parquet`, shipped `iama` defaults, all four comparator columns
pulled from the SAME `IndicatorEngine(include_advanced=False).
compute_all()` frame `IAMA_DIST` was computed against -- not a
hand-reconstruction; see the module docstring below and
`backtest_results/tvpta6/iama_overlap_20260814.md` for the full method
and the two corrections in detail):

  - `NWE_MID_200_8.0_8.0` (Band/channel, `(close-nw_mid)/close*100`):
    Spearman 0.9498 pooled / 0.9507 per-ticker median / 0.9053 per-ticker
    minimum -- the HIGHEST of the enumerated set measured (NOT claimed as
    the maximum over the register's full 212 `OK`-verdict columns; a full
    programmatic sweep was started but not completed).
  - `bias` (Oscillator/momentum, `(close-SMA20)/SMA20`,
    `indicator_engine.py:1146`): Spearman 0.9361 / 0.9370 / 0.9138.
  - `RSI`: Spearman 0.9276 / 0.9308 / 0.9097.
  - `ATR_POSITION` (register verdict NORMALIZE, not OK): Spearman
    0.9216 / 0.9265 / 0.8638.
  - REAL `mkt_kama_pos` (index-derived, broadcast, `indicator_engine.py:
    376`): Spearman 0.5020 pooled / 0.4933 median / 0.1696 minimum --
    materially LOWER than the other four; this is the number that
    corrects round 2's error, not a corroboration of anything.

Ranking convention: by SIGNED Spearman, since every comparator measured
here came out positive -- stated explicitly because a strongly negative
correlation would be equally redundant for a DecisionTree split, which
does not care about sign, only ordering.

Mechanically expected either way: `f_efficiency`'s `dir/pth` IS the same
Kaufman efficiency-ratio formula as kama's own `er`, and f_ima's two
additional terms (squashed slope, volatility multiplier) modulate rather
than replace that shared driver -- apparently not enough to move the RANK
ordering far from other `(close-X)/X`-shaped distances from a smoother.

**Ship call: this pandas_ta port is KEPT (code correct, tested, cheap to
hold) but the Backtesting-side wiring was REVERTED** the same session --
at 0.92-0.95 against multiple columns ALREADY in the mining pool, "flag
it and let mining decide" (this batch's own `pressure_pulse`/
`tri_dir_pressure` precedent, ~0.76-0.80 against THEIR shipped siblings)
is not a real option; mining would just weigh the same ordering twice.
Re-wiring requires an actual mining A/B run (with vs without `IAMA_DIST`
in the pool) showing it earns something the existing columns don't, not
another correlation measurement. See `datastore/source/
pine_candidates_families.csv` (slug 6SVLw0kE-Institutional-Moving-
Averages, status back to `defer`) for the standing decision -- do not
re-derive the numbers from this docstring, read the artifact.

SCALE-FREE OUTPUT: `ima` itself (the adaptive line) is a price level and
is NOT returned -- only `(close - ima) / ima * 100`, the same distance-form
choice as `ma_disparity` (pandas_ta/overlap/ma_disparity.py) and for the
identical reason: a raw MA level drifts with an instrument's nominal price
and is excluded by this project's mining register (see
docs/indicators/family-moving-avg-smoother.md).

Calculation:
    Default Inputs:
        length=9, k=1.0, atr_length=14, norm_length=50

    eff[t]   = f_efficiency(close, length)[t]
             = pth[t]>0 ? min(|close[t]-close[t-length]|/pth[t], 1) : 0
               where pth[t] = SUM(|close-close.shift(1)|, length)[t]
    atr[t]   = ATR(atr_length)[t]  (Wilder/RMA)
    atrAvg[t]= SMA(atr, norm_length)[t]
    volRatio[t] = atrAvg[t]>0 ? atr[t]/atrAvg[t] : 1.0
    slopeLen = max(1, round(length/3.0))
    slope[t] = |close[t]-close[t-slopeLen]| / max(atr[t], max(min_tick, rel_floor*|close[t]|))
    drive[t] = min(1, 0.65*eff[t] + 0.35*(slope[t]/(1+slope[t])))
    vAdj[t]  = clip(volRatio[t], 0.6, 1.5)
    fastA    = 2 / (max(2, length/(2+k)) + 1)
    slowA    = 2 / (length*(1+k*0.5) + 1)
    alpha[t] = clip((slowA + drive[t]*(fastA-slowA))**2 * vAdj[t], 0.001, 1)
    ima[t]   = close[t]                          if ima[t-1] is NaN (incl. t=0)
             = ima[t-1] + alpha[t]*(close[t]-ima[t-1])   otherwise
    IAMA_DIST[t] = (close[t] - ima[t]) / ima[t] * 100

Args:
    high (pd.Series): Series of 'high's
    low (pd.Series): Series of 'low's
    close (pd.Series): Series of 'close's
    length (int): f_ima's `len`. Default: 9
    k (float): f_ima's `k` (Pine's `sens`, adaptive sensitivity). Default: 1.0
    atr_length (int): ATR window (Pine `atrLen`). Default: 14
    norm_length (int): volRatio's ATR-averaging window (Pine `normLen`). Default: 50
    min_tick (float): absolute divide-by-zero floor (Pine `syminfo.mintick`
        has no equivalent on a bare Series). Default: 1e-8
    rel_floor (float): price-scale-aware divide-by-zero floor, as a
        fraction of |close|. Default: 2.5e-3
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.Series: IAMA_DIST_{length}_{k}_{atr_length}_{norm_length}
"""
