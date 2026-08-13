# -*- coding: utf-8 -*-
import numpy as np
import pandas as pd
from pandas import Series
from pandas_ta.momentum.er import er
from pandas_ta.overlap import ema
from pandas_ta.volatility import atr as _atr
from pandas_ta.utils import get_offset, verify_series

# TVPTA-6 acceptance gates (a)-(f) -- all six required before this port is done:
# (a) Causality: no look-ahead. This indicator is IIR/recursive (balance/
#     drift/pressureMemory each carry forward state), so "causal" means
#     mutating bar T changes bar T and every bar AFTER it, and NEVER a bar
#     before T -- verified by test, not assumed from the loop's shape.
# (b) Pine->pandas semantics verified against the FORK's source, not memory
#     -- two real gotchas found and verified here: `ta.ema`'s Pine seeding
#     (first value = raw src, not an SMA seed) only matches this fork's own
#     `ema(..., sma=False)`, NOT the `sma=True` default (see module
#     docstring "EMA SEEDING" section); and `ta.atr`'s SMA-seeded Wilder
#     smoothing differs from this fork's `atr()` (ewm-based RMA, `iloc[:1]
#     = NaN` on true_range) by a measured, bounded, decaying amount during
#     warmup (see "ATR SEEDING" section).
# (c) Reachable via df.ta.pressure_pulse() -- core.py registration required.
# (d) Numeric correctness spot-checked against the source .pine's own math
#     (docs/TradingView/pine/5BLfGp6I-Trend-Pulse.pine, L344-657), not just
#     "runs without crashing".
# (e) Docstring names source URL + author.
# (f) Test asserts real behavior (bounded range VERIFIED BY FUZZING -- the
#     scoping survey's "bounded +-1" claim is WRONG, see module docstring),
#     known input->output, and a source edge case -- not just "returns a
#     Series".
#
# This is a partial port of "MSL Trend Pulse" (5BLfGp6I). Only the
# Pressure Pulse module (L517-657) is ported, plus the Predictive Balance
# alpha-beta filter (L344-516) it depends on as an internal (NOT exposed as
# its own top-level indicator -- see module docstring "OVERLAP CHECK").
# NOT ported: the flip-band regime state machine (L464-516, drives the
# `regime`/`upFlipMark`/`dnFlipMark` plots), the Wave Memory module
# (impulse/wave-force tracker, L659-915), the ~700 lines of glow-layer
# drawing code, and the dashboard table. See the module docstring below for
# the full list and rationale.


def pressure_pulse(open_, high, low, close,
                    balance_length=None, min_gain=None, max_gain=None,
                    drift_gain=None, drift_damping=None, atr_length=None,
                    pulse_norm_length=None, pulse_smooth_length=None,
                    memory_min=None, memory_max=None, min_tick=None,
                    offset=None, **kwargs):
    """Indicator: Pressure Pulse (PRESSURE_PULSE)

    Ports ONLY the source's Pressure Pulse module (`rawPressure` through
    `pulse`, Pine L517-657) plus the Predictive Balance alpha-beta filter
    (L344-516) it depends on as an internal helper. See the module
    docstring for the full calculation and what was NOT ported.
    """
    # Validate Arguments
    open_ = verify_series(open_)
    high = verify_series(high)
    low = verify_series(low)
    close = verify_series(close)
    offset = get_offset(offset)
    if any(s is None for s in (open_, high, low, close)):
        return

    for name, s in (("open_", open_), ("high", high), ("low", low), ("close", close)):
        if not pd.api.types.is_numeric_dtype(s):
            raise ValueError(f"{name} must be numeric, got dtype {s.dtype}")
        arr = s.to_numpy(dtype="float64", copy=False)
        if not np.isfinite(arr).all():
            raise ValueError(
                f"{name} contains non-finite values (nan/inf) -- pressure_pulse is a "
                "recursive (IIR) indicator: balance/drift/pressureMemory each carry "
                "forward state, so a single NaN/inf would poison every subsequent bar's "
                "output, not just a `length`-bar window (verified: see "
                "tests/test_pressure_pulse.py::test_single_nan_poisons_all_subsequent_bars). "
                "Unlike bpress's deliberate NaN-passthrough (a rolling-window indicator, "
                "where a gap only nulls `length` bars), that behavior is not acceptable here."
            )

    n = len(close)
    if not (len(open_) == len(high) == len(low) == n):
        raise ValueError(
            f"open_/high/low/close must be the same length, got "
            f"{len(open_)}/{len(high)}/{len(low)}/{n}"
        )

    def _validate_length(value, name, default, minval):
        if value is None:
            return default
        if isinstance(value, bool) or not isinstance(value, (int, float, np.integer, np.floating)):
            raise ValueError(f"{name} must be numeric, got {type(value).__name__}: {value!r}")
        if not np.isfinite(value):
            raise ValueError(f"{name} must be finite, got {value}")
        if float(value) != int(value):
            raise ValueError(f"{name} must be integral, got {value}")
        value = int(value)
        if value < minval:
            raise ValueError(f"{name} must be >= {minval} (Pine source's own minval), got {value}")
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
            raise ValueError(
                f"{name} must be in [{minval}, {maxval}] (Pine source's own input bounds), got {value}"
            )
        return value

    # Length-type params. Minvals mirror the Pine source's own input.int
    # `minval=` declarations exactly (L21-167 of the .pine).
    balance_length = _validate_length(balance_length, "balance_length", 20, minval=3)
    atr_length = _validate_length(atr_length, "atr_length", 14, minval=1)
    pulse_norm_length = _validate_length(pulse_norm_length, "pulse_norm_length", 50, minval=5)
    pulse_smooth_length = _validate_length(pulse_smooth_length, "pulse_smooth_length", 5, minval=1)

    # Float-type params. min/maxvals mirror the Pine source's own input.float
    # `minval=`/`maxval=` declarations exactly. driftDamping's Pine maxval of
    # 0.99 (never 1.0) and memoryMin/memoryMax's maxvals of 0.98/0.99 are not
    # arbitrary here -- they are the reason the balance/drift/pressureMemory
    # IIR recursions cannot diverge (see module docstring "BOUNDEDNESS").
    min_gain = _validate_float(min_gain, "min_gain", 0.05, minval=0.01, maxval=0.50)
    max_gain = _validate_float(max_gain, "max_gain", 0.40, minval=0.05, maxval=1.00)
    drift_gain = _validate_float(drift_gain, "drift_gain", 0.12, minval=0.00, maxval=1.00)
    drift_damping = _validate_float(drift_damping, "drift_damping", 0.80, minval=0.00, maxval=0.99)
    memory_min = _validate_float(memory_min, "memory_min", 0.60, minval=0.00, maxval=0.98)
    memory_max = _validate_float(memory_max, "memory_max", 0.88, minval=0.00, maxval=0.99)

    # min_tick: the source's `syminfo.mintick` (exchange-declared minimum
    # price increment) has no equivalent on a bare OHLC Series -- there is
    # no symbol/exchange context. Substituted with a fixed epsilon floor,
    # a deliberate deviation from the source, not a silent one (see module
    # docstring "MINTICK SUBSTITUTION").
    if min_tick is None:
        min_tick = 1e-8
    else:
        if isinstance(min_tick, bool) or not isinstance(min_tick, (int, float, np.integer, np.floating)):
            raise ValueError(f"min_tick must be numeric, got {type(min_tick).__name__}: {min_tick!r}")
        min_tick = float(min_tick)
        if not np.isfinite(min_tick) or min_tick <= 0:
            raise ValueError(f"min_tick must be finite and positive, got {min_tick}")

    # Insufficient-history guard: `er()` (path_quality), `atr()` (safeAtr's
    # primary term) and `ema()` (pressureScale, pulse) all internally call
    # `verify_series(series, min_length=window)` and return None -- not a
    # partial/NaN-heavy Series -- whenever `len(series) < window`. Rather
    # than special-case each of those None returns individually, mirror
    # the SAME "return None on insufficient history" convention used
    # throughout this fork (e.g. bpress) at this function's own boundary:
    # a single upfront length check against every window parameter this
    # function uses, one place, same semantics as every window it calls
    # into.
    min_required = max(balance_length, atr_length, pulse_norm_length, pulse_smooth_length)
    if n < min_required:
        return

    # Calculate Result
    idx = close.index
    o = open_.to_numpy(dtype="float64", copy=False)
    h = high.to_numpy(dtype="float64", copy=False)
    lo = low.to_numpy(dtype="float64", copy=False)
    c = close.to_numpy(dtype="float64", copy=False)

    # --- Predictive Balance (Pine L344-462) ---
    # basisSource = (H + L + 2*C) / 4
    basis = (h + lo + 2.0 * c) / 4.0
    basis_s = Series(basis, index=idx)

    # pathQuality = clamp(safeDiv(directionalMove, pathLength, 0.0), 0, 1),
    # where directionalMove = |basis - basis[balanceLen]| (nz-fallback to
    # basis itself when history is short) and pathLength = SMA(sourceStep,
    # balanceLen) * balanceLen = the rolling SUM of |1-bar diffs|. This is
    # EXACTLY this fork's own `er()` (Kaufman Efficiency Ratio) applied to
    # `basis` with length=balanceLen, drift=1 -- see module docstring
    # "PATH QUALITY == KAUFMAN'S EFFICIENCY RATIO". `er()`'s own NaN
    # (insufficient-history OR 0/0) cases coincide exactly with Pine's
    # safeDiv fallback triggers, so a single `.fillna(0.0).clip(0, 1)`
    # reproduces `pathQuality` bar-for-bar (verified in
    # tests/test_pressure_pulse.py::test_path_quality_matches_er).
    path_quality = er(basis_s, length=balance_length, drift=1).fillna(0.0).clip(0.0, 1.0).to_numpy()

    reaction_floor = min(min_gain, max_gain)
    reaction_ceiling = max(min_gain, max_gain)
    reaction = reaction_floor + (reaction_ceiling - reaction_floor) * path_quality

    balance = np.empty(n, dtype="float64")
    drift = np.empty(n, dtype="float64")
    prev_balance = np.empty(n, dtype="float64")  # state carried INTO bar t, before its update

    balance[0] = basis[0]
    drift[0] = 0.0
    prev_balance[0] = basis[0]
    for t in range(1, n):
        pb = balance[t - 1]
        pd_ = drift[t - 1]
        prev_balance[t] = pb
        prediction = pb + pd_
        error = basis[t] - prediction
        r = reaction[t]
        balance[t] = prediction + r * error
        drift[t] = drift_damping * pd_ + drift_gain * r * error

    # --- Pressure Pulse (Pine L517-657) ---
    atr_series = _atr(high, low, close, length=atr_length, mamode="rma")
    atr_arr = atr_series.to_numpy(dtype="float64", copy=False) if atr_series is not None else np.full(n, np.nan)
    safe_atr = np.where(np.isfinite(atr_arr), atr_arr, h - lo)
    safe_atr = np.maximum(safe_atr, min_tick)

    candle_range = np.maximum(h - lo, min_tick)

    with np.errstate(invalid="ignore"):
        body_pressure = np.clip((c - o) / safe_atr, -1.0, 1.0)
        close_pressure = np.clip((2.0 * c - h - lo) / candle_range, -1.0, 1.0)
        trend_pressure = np.clip((balance - prev_balance) / safe_atr, -2.0, 2.0) / 2.0
        stretch_pressure = np.clip((c - balance) / safe_atr, -2.0, 2.0) / 2.0

    raw_pressure = (
        0.35 * body_pressure
        + 0.25 * close_pressure
        + 0.25 * trend_pressure
        + 0.15 * stretch_pressure
    )

    memory_floor = min(memory_min, memory_max)
    memory_ceiling = max(memory_min, memory_max)
    memory_factor = memory_floor + (memory_ceiling - memory_floor) * path_quality

    pressure_memory = np.empty(n, dtype="float64")
    pressure_memory[0] = raw_pressure[0]  # memoryFactor[0] * nz(pressureMemory[-1], 0.0) + rawPressure[0]
    for t in range(1, n):
        pressure_memory[t] = memory_factor[t] * pressure_memory[t - 1] + raw_pressure[t]

    # pressureScale = ta.ema(|pressureMemory|, pulseNormLen). Pine's ta.ema
    # seeds bar 0 with the raw source value, NOT an SMA -- `sma=False` is
    # required to match (see module docstring "EMA SEEDING").
    pressure_scale = ema(
        Series(np.abs(pressure_memory), index=idx), length=pulse_norm_length, sma=False
    ).to_numpy(dtype="float64", copy=False)

    # relativePressure = safeDiv(pressureMemory, pressureScale, 0.0):
    # fallback to 0.0 whenever the scale is undefined, zero, or non-finite
    # (the last case cannot arise from a finite-input, stable-parameter run
    # -- see "BOUNDEDNESS" -- but is guarded defensively all the same).
    valid_scale = np.isfinite(pressure_scale) & (pressure_scale != 0.0)
    relative_pressure = np.where(valid_scale, np.divide(pressure_memory, pressure_scale, where=valid_scale), 0.0)

    compressed_pressure = 2.0 * relative_pressure / (1.5 + np.abs(relative_pressure))

    pulse = ema(
        Series(compressed_pressure, index=idx), length=pulse_smooth_length, sma=False
    )

    result = pulse
    result.name = f"PRESSURE_PULSE_{balance_length}_{atr_length}_{pulse_norm_length}_{pulse_smooth_length}"
    result.category = "momentum"

    # Offset
    if offset != 0:
        result = result.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        result.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        result.fillna(method=kwargs["fill_method"], inplace=True)

    return result


pressure_pulse.__doc__ = \
"""Pressure Pulse (PRESSURE_PULSE)

Source: TradingView community indicator "MSL Trend Pulse" by
MarketStructureLab,
https://www.tradingview.com/script/5BLfGp6I-Trend-Pulse/
(ported into AwakenAnalytics/Backtesting TVPTA continuation, TVPTA-6
candidate 11)

Pine functions/sections replaced: the Pressure Pulse module (`rawPressure`
through `pulse`, `docs/TradingView/pine/5BLfGp6I-Trend-Pulse.pine` L517-657)
and the Predictive Balance alpha-beta filter (`balance`/`drift`, L344-462)
it depends on as an internal (not exposed as its own indicator -- see
"OVERLAP CHECK" below). Nothing else from this 1,672-line, 3-module source
is ported.

Deliberately NOT ported, and why:
    - The flip-band regime state machine (`flipBand`/`upperFlipBand`/
      `lowerFlipBand`/`bullBreak`/`bearBreak`/`regime`/`upFlipMark`/
      `dnFlipMark`, L464-516): a discrete BUY/SELL-flip classifier built on
      top of Predictive Balance, using two more inputs (`bandBase`,
      `bandNoise`) that Pressure Pulse itself never reads. A separate
      indicator, not part of the oscillator.
    - Wave Memory (L659-915, ~257 lines): a stateful impulse/wave-force
      tracker keyed off `pulseGrowing`/`pressurePresent` (which need the
      `deadband` input, also never read by Pressure Pulse itself) --
      genuinely its own multi-state system, not a sub-component of the
      oscillator.
    - ~700 lines of glow-layer plotting (adaptive-alpha gradient fills)
      and the dashboard table (L1104-1650): pure visualization, no numeric
      output.

Calculation:
    Default Inputs:
        balance_length=20, min_gain=0.05, max_gain=0.40, drift_gain=0.12,
        drift_damping=0.80, atr_length=14, pulse_norm_length=50,
        pulse_smooth_length=5, memory_min=0.60, memory_max=0.88

    -- Predictive Balance (an efficiency-adaptive Holt/alpha-beta filter) --
    basis[t]        = (High[t] + Low[t] + 2*Close[t]) / 4
    pathQuality[t]  = clip(ER(basis, balance_length)[t], 0, 1)   -- see
                      "PATH QUALITY == KAUFMAN'S EFFICIENCY RATIO" below
    reaction[t]     = min(min_gain,max_gain)
                      + (max(min_gain,max_gain) - min(min_gain,max_gain)) * pathQuality[t]
    prediction[t]   = balance[t-1] + drift[t-1]      (bar 0: balance[0]=basis[0], drift[0]=0)
    error[t]        = basis[t] - prediction[t]
    balance[t]      = prediction[t] + reaction[t] * error[t]
    drift[t]        = drift_damping * drift[t-1] + drift_gain * reaction[t] * error[t]

    -- Pressure Pulse --
    safeATR[t]        = max(ATR(atr_length)[t] if finite else High[t]-Low[t], min_tick)
    candleRange[t]    = max(High[t]-Low[t], min_tick)
    bodyPressure[t]   = clip((Close[t]-Open[t]) / safeATR[t], -1, 1)
    closePressure[t]  = clip((2*Close[t]-High[t]-Low[t]) / candleRange[t], -1, 1)
    trendPressure[t]  = clip((balance[t]-balance[t-1]) / safeATR[t], -2, 2) / 2
    stretchPressure[t]= clip((Close[t]-balance[t]) / safeATR[t], -2, 2) / 2
    rawPressure[t]    = 0.35*bodyPressure[t] + 0.25*closePressure[t]
                        + 0.25*trendPressure[t] + 0.15*stretchPressure[t]     -- in [-1, 1]

    memoryFactor[t]   = min(memory_min,memory_max)
                        + (max(memory_min,memory_max) - min(memory_min,memory_max)) * pathQuality[t]
    pressureMemory[t] = memoryFactor[t] * pressureMemory[t-1] + rawPressure[t]   (t=0: = rawPressure[0])
                        -- an UN-normalized IIR accumulator (no *(1-factor)
                        term), stable because memoryFactor in [0, 0.98] by
                        the Pine source's own input bounds (see
                        "BOUNDEDNESS")
    pressureScale[t]  = EMA(|pressureMemory|, pulse_norm_length)[t]
    relativePressure[t] = pressureMemory[t]/pressureScale[t] if pressureScale[t] not in {0, undefined} else 0
    compressedPressure[t] = 2*relativePressure[t] / (1.5 + |relativePressure[t]|)
    PRESSURE_PULSE[t] = EMA(compressedPressure, pulse_smooth_length)[t]

PATH QUALITY == KAUFMAN'S EFFICIENCY RATIO (verified, not merely
asserted): Pine's `directionalMove = |basis - basis[balanceLen]|` (nz-
fallback to `basis` when history is short) is exactly this fork's own
`er()`'s `abs_diff = close.diff(length).abs()` term, and Pine's
`pathLength = ta.sma(sourceStep, balanceLen) * balanceLen` (a rolling SUM
of |1-bar diffs|, since SMA*N == sum) is exactly `er()`'s own
`abs_volatility.rolling(length).sum()` term -- i.e. `pathQuality` IS
Kaufman's Efficiency Ratio (the same quantity `kama()` uses to drive its
adaptive smoothing constant) applied to `basis` instead of `close`, then
clipped to [0, 1]. `er()`'s NaN cases (insufficient history for either
term, or a 0/0 flat-price window) coincide exactly with when Pine's
`safeDiv(..., fallback=0.0)` fires, so `er(basis, balance_length, drift=1)
.fillna(0.0).clip(0, 1)` reproduces `pathQuality` bar-for-bar -- this
function reuses `er()` directly rather than re-deriving the same rolling
sum/diff, see tests/test_pressure_pulse.py::test_path_quality_matches_er.

OVERLAP CHECK (Predictive Balance vs `kama`/`vidya`/this fork's own
`bpress`): Predictive Balance shares `kama`'s core idea -- an Efficiency-
Ratio-driven adaptive gain -- but is NOT a re-skin of KAMA. `kama` is a
SINGLE exponential filter with a SQUARED ER-derived smoothing constant
(`sc = (er*(fast_w-slow_w)+slow_w)**2`, blending directly against the raw
close). Predictive Balance is a Holt/alpha-beta DOUBLE filter carrying two
independent states (`balance` AND `drift`), using ER LINEARLY (not
squared) to set a correction gain on a PREDICTION error
(`balance[t] = (balance[t-1]+drift[t-1]) + reaction*error`, not a
`sc*src + (1-sc)*prev` blend) -- the trend/drift state and the
predict-then-correct structure have no KAMA analog. It is filed under
`momentum/` (not alongside `kama`/`vidya` in `overlap/`) BECAUSE it is not
itself exposed as a standalone indicator here -- it is an internal helper
feeding a bounded oscillator, matching the placement rationale that this
fork's own `bpress` used for a different reason (proximity to `linreg`) but
applied to "proximity to the oscillator that consumes it" instead. The
`PRESSURE_PULSE` output itself was measured against the fork's closest
existing scale-free "distance from an adaptive/regression line" siblings
(`bpress` and `willr`) on real BIST_100 daily data (40 tickers, 160,880
joint bars) -- see
backtest_results/tvpta6/pressure_pulse_overlap_20260813.md (Backtesting
repo) for the full measurement. Result, not hidden: LOW correlation vs
`bpress` (Pearson 0.303 / Spearman 0.309) and vs the deployed book's own
`cfo` (Pearson -0.051 / Spearman -0.054), but HIGH vs `willr` (Pearson
0.799 / Spearman 0.805) -- MORE rank-correlated than this batch's own
`tri_dir_pressure` vs `VOL_DELTA_APPROX` (0.760), which that measurement
already treats as a genuine collinearity concern. Not a duplicate (willr
is a 14-bar rolling extremum position; PRESSURE_PULSE's analogous
`closePressure` sub-term is single-bar and contributes only 25% of the
composite's weight), but a real overlap a feature-selection pass across
this family should account for, not assume away because the formulas
differ structurally.

EMA SEEDING (Pine `ta.ema` vs this fork's `ema()` -- gotcha, verified):
Pine's `ta.ema` seeds bar 0 directly with the source value and recurses
from there (`sum := na(sum[1]) ? src : alpha*src + (1-alpha)*nz(sum[1])`,
alpha=2/(length+1)) -- it does NOT SMA-seed. This fork's own `ema()`
DEFAULTS to `sma=True` (SMA-seeded over the first `length` bars, NaN
before that) -- calling `ema(x, length)` with no kwarg would silently ship
a systematically different (NaN-delayed, differently-valued) series.
`ema(x, length, sma=False)` was verified byte-for-byte (max abs diff 0.0
over 50 bars, seed=1) against a from-scratch implementation of Pine's own
recursive formula -- this is the ONLY kwarg combination that reproduces
`ta.ema`, used for BOTH `pressureScale` and the final `pulse` smoothing.
Same class of gotcha as bpress's `linreg(..., tsf=True)` requirement.

ATR SEEDING (Pine `ta.atr` vs this fork's `atr()` -- measured divergence,
documented not hidden): Pine's `ta.atr` uses an SMA-seeded Wilder
recursion (first ATR = SMA of the first `length` true ranges, every prior
bar undefined). This fork's `atr()` composes `true_range()` (which
explicitly NaNs the very first bar, `iloc[:drift] = NaN`, since there is
no previous close) with `rma()` (an `ewm(alpha=1/length, min_periods=
length)`, i.e. src-seeded not SMA-seeded) -- so `atr()`'s first non-NaN
bar lands ONE BAR LATER than Pine's own (idx `atr_length` vs
`atr_length - 1`, 0-indexed), and its early post-warmup values differ from
a true SMA-seeded Wilder ATR by a measured, geometrically-decaying amount:
0.134 at the seed+1 bar, 0.0224 fourteen bars later, 6.3e-5 by bar 100,
6.6e-11 by bar 299 (length=14, seed=0 synthetic OHLC; see
tests/test_pressure_pulse.py for the reproducible check). This divergence
is bounded to the warmup window and immaterial to `PRESSURE_PULSE` in
practice because `safeAtr` already falls back to `High-Low` whenever ATR
is undefined (matching the source's own `nz(atrValue, high-low)` design)
-- the 1-bar shift only changes WHICH side of that fallback a single bar
lands on, not whether the fallback pattern exists. Not claimed to be an
exact match; the divergence is measured and bounded, not hand-waved away.

MINTICK SUBSTITUTION: Pine's `syminfo.mintick` (the listed instrument's
minimum price increment, from TradingView's own exchange metadata) has no
equivalent for a bare OHLC Series with no symbol/exchange context. A fixed
`min_tick` parameter (default 1e-8) is substituted everywhere the source
used `syminfo.mintick` -- both `safeAtr`'s and `candleRange`'s zero-range
floor. This is a genuine, acknowledged deviation from the source (not a
silent one): on an instrument whose real tick size is coarser than 1e-8,
a High==Low bar's `candleRange` floor here is far smaller than Pine's
would be, so `closePressure` on such a bar would clip to +-1 more readily
here than on the original chart. Callers with a known tick size should
pass it explicitly via `min_tick=`.

BOUNDEDNESS (verified by fuzzing, NOT the scoping survey's "+-1" claim --
that claim is WRONG): `compressedPressure = 2*r / (1.5 + |r|)` is bounded
to the OPEN interval (-2, 2) for ANY finite r (the limit as |r| -> infinity
is exactly 2, never reached) -- this holds regardless of parameter choice,
by construction, independent of whatever `pressureMemory`/`balance` do
upstream. `PRESSURE_PULSE` (an EMA, i.e. a convex combination of past
`compressedPressure` values with weights summing to 1) inherits the same
strict (-2, 2) bound. The Pine source's own input `maxval`s on
`drift_damping` (0.99) and `memory_min`/`memory_max` (0.98/0.99) --
mirrored here as hard ValueError bounds, see Args -- additionally
guarantee the `drift`/`pressureMemory` recursions themselves cannot
diverge to +-inf (which would otherwise risk an inf-inf -> NaN through the
`clip()` calls). Verified two ways, both truthfully reported (not the
same run, do not average them): the SHIPPED regression test,
tests/test_pressure_pulse.py::test_bounded_by_fuzzing, runs 400 draws of
random-walk OHLC with randomized valid parameter combinations every time
the suite runs (worst |PRESSURE_PULSE| observed there printed to stdout,
always < 2.0, typically ~1.7-1.9); a separate, larger, NOT-shipped
one-off exploration during development ran 3,000 draws (worst observed
1.861) to build confidence before committing to the 400-draw regression
count -- 3,000 was not kept in the suite because it costs ~7x the
runtime (~20s vs ~3s) for the same qualitative conclusion.

Causality: `balance`/`drift`/`pressureMemory` are true IIR recursions (each
bar's value depends on the PREVIOUS bar's `balance`/`drift`/
`pressureMemory`, never a future one) -- mutating bar T changes bar T and
every bar strictly after it, and must leave every bar before T
bit-identical; verified directly (mutation + prefix-truncation tests), not
assumed from the loop's shape, since a subtly wrong index off-by-one in a
recursive implementation could silently leak information backward via a
mis-aligned `.shift()`/lookup that a pure "no `.shift(-1)` in the code"
read would not catch.

Args:
    open_ (pd.Series): Series of 'open's
    high (pd.Series): Series of 'high's
    low (pd.Series): Series of 'low's
    close (pd.Series): Series of 'close's. All four must be fully finite
        (no NaN/inf) -- unlike a rolling-window indicator, a single gap
        would poison every subsequent bar once it enters the recursive
        state; raises ValueError instead of silently propagating.
    balance_length (int): Predictive Balance efficiency-ratio window
        (Pine "Direction Window"). Default: 20. Must be a finite positive
        integral value >= 3 (the Pine source's own minval).
    min_gain (float): Predictive Balance reaction floor (Pine "Minimum
        Reaction"). Default: 0.05. Must be in [0.01, 0.50].
    max_gain (float): Predictive Balance reaction ceiling (Pine "Maximum
        Reaction"). Default: 0.40. Must be in [0.05, 1.00]. Used as
        min(min_gain,max_gain)/max(min_gain,max_gain) regardless of which
        argument is numerically larger, matching the source.
    drift_gain (float): Drift-state learning rate (Pine "Drift Learning").
        Default: 0.12. Must be in [0.00, 1.00].
    drift_damping (float): Drift-state damping (Pine "Drift Damping").
        Default: 0.80. Must be in [0.00, 0.99] -- the < 1 bound is what
        keeps the drift recursion from diverging, see "BOUNDEDNESS".
    atr_length (int): ATR window feeding safeATR (Pine "Volatility
        Length"). Default: 14. Must be a finite positive integral value
        >= 1.
    pulse_norm_length (int): EMA window normalizing |pressureMemory| into
        pressureScale (Pine "Normalisation Length"). Default: 50. Must be
        a finite positive integral value >= 5.
    pulse_smooth_length (int): Final EMA smoothing window (Pine "Pulse
        Smoothing"). Default: 5. Must be a finite positive integral
        value >= 1.
    memory_min (float): pressureMemoryFactor floor (Pine "Minimum
        Memory"). Default: 0.60. Must be in [0.00, 0.98].
    memory_max (float): pressureMemoryFactor ceiling (Pine "Maximum
        Memory"). Default: 0.88. Must be in [0.00, 0.99] -- the < 1 bound
        is what keeps pressureMemory from diverging, see "BOUNDEDNESS".
    min_tick (float): Substitute for Pine's `syminfo.mintick` (no
        exchange context on a bare Series) -- see "MINTICK SUBSTITUTION".
        Default: 1e-8. Must be finite and positive.
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.Series: PRESSURE_PULSE_{balance_length}_{atr_length}_
        {pulse_norm_length}_{pulse_smooth_length}, strictly bounded to
        (-2, 2) by construction (see "BOUNDEDNESS") -- NOT (-1, 1) as the
        scoping survey's paraphrase claimed. Returns `None` (pandas_ta
        convention, matching every window-based indicator this function
        calls into -- `er`/`atr`/`ema` each do the same) when
        `len(close) < max(balance_length, atr_length, pulse_norm_length,
        pulse_smooth_length)`.
"""
