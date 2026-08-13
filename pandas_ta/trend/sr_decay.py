# -*- coding: utf-8 -*-
import math

import numpy as np
from pandas import DataFrame, Series

from pandas_ta.utils import get_offset, verify_series
from pandas_ta.volatility import atr as _atr


def _confirm_strict_pivots(series, left, right, is_high):
    """Causal pivot confirmation matching Pine's `ta.pivothigh`/
    `ta.pivotlow` semantics: a bar at position i confirms (becomes visible
    at j=i+right) iff it is the STRICT, UNIQUE extreme of the window
    [i-left, i+right]. Duplicated verbatim from `sr_force.py` (and
    `liquidity_sweep.py`'s / `rejection_blocks.py`'s / `equal_highs_lows.
    py`'s / `sphinx_unicorn.py`'s identical helper) rather than imported,
    matching this package's convention of self-contained indicator files.
    """
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


class _Level:
    __slots__ = ("price", "atten", "swirl")

    def __init__(self, price, atten, swirl):
        self.price = price
        self.atten = atten
        self.swirl = swirl


def _validated_int(value, default, name, positive=True):
    """None -> default (a normal, documented default, not bad input).
    Anything else must be a genuine, finite, integral value, or raise.
    Duplicated verbatim from `sr_force.py`'s helper of the same name (that
    file's own docstring explains the NaN/inf/non-integral discipline this
    enforces vs. a bare `int(value)`)."""
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


def _attenuation(price, close_t, time_decay):
    """Port of the source's `calcAttenuation` (module 4.5, "减弱指数 /
    Attenuation Index"). `time_decay = min(bars_ago / 50, 1.0)` is passed
    in already-computed rather than recomputed per level: under THIS
    port's fixed `swing_len` (see module docstring), `barsAgo` at the
    confirming bar is ALWAYS exactly `swing_len` (never the source's
    `if barsAgo < 0: barsAgo := 0` clamp path -- a pivot's confirming bar
    is by construction `swing_len` bars after the pivot bar, never
    before), so `time_decay` is a single constant for an entire `sr_decay`
    call, not a per-level computation -- hoisting it out of the per-level
    loop is a performance simplification, not a behavior change; the
    per-level cost of literally recomputing `min(swing_len/50, 1.0)` on
    every confirmation would be identical every time.

    `price_change_pct = abs(close_t - price) / price * 100` mirrors the
    source's `priceChange = math.abs(currentPrice - price) / price * 100`
    exactly -- `currentPrice` in the source is simply `close` read on the
    bar the function executes on, which (module 6's calling site) is
    always the confirming bar, i.e. this function's own `close_t`.

    `price <= 0` (unreachable on real market data -- a confirmed swing
    pivot price is never zero or negative) returns NaN rather than
    raising ZeroDivisionError: the source has no equivalent guard (Pine
    division by zero is `na`, not an exception), and this fork's
    try/except-per-indicator wiring in `indicator_engine.py` would
    otherwise silently drop all 4 SRD_ columns on a single degenerate
    input row -- a defensive guard, not a behavior change for any real
    price series.
    """
    if price <= 0:
        return np.nan
    price_change_pct = abs(close_t - price) / price * 100.0
    price_decay = min(price_change_pct / 10.0, 1.0)
    attenuation = time_decay * 0.6 + price_decay * 0.4
    return min(attenuation, 1.0)


def _swirl(atr_v, hl_sma_v, high_v, low_v, t, bars_ago):
    """Port of the source's `calcSwirl` (module 4.6, "漩涡指标 / Swirl
    Index"). Called once per confirming level, at bar `t` (the confirming
    bar), with `bars_ago = swing_len` -- see `_attenuation`'s docstring
    for why this is always exactly `swing_len`, never the source's
    negative-clamp path, under this port's fixed-`swing_len` scheme.

    Two DIFFERENT volatility measures are combined here, faithfully
    reproducing a real distinction in the source, not an inconsistency
    introduced by this port: `atr_v` is `ta.atr(14)` (Wilder/RMA-smoothed
    TRUE range, gap-inclusive -- `pandas_ta.volatility.atr`'s own default
    `mamode="rma"` matches Pine's `ta.atr` FORMULA exactly), used for
    `volatility_change = atr_current / atr_near`; `hl_sma_v` is a plain
    14-bar SIMPLE moving average of `high - low` (bar range, NOT true
    range -- no gap component), used as each scanned bar's own
    normalizer inside the swirl sum. The source's `ta.atr(14)` and
    `ta.sma(high - low, 14)` genuinely are two different series; this
    port keeps them separate rather than collapsing to one for tidiness.

    ⚠ ONE REAL DIVERGENCE from the source, not merely a formula match: in
    the .pine source, both `ta.atr(14)` (inside `calcSwirl`, itself only
    called from the `if not na(swingHigh)`/`if not na(swingLow)` blocks,
    module 6, lines 367-372/392-397) and `ta.sma(high - low, 14)` (inside
    `calcSwirl`'s own `for i = 0 to 10` loop) are call sites that Pine
    only advances on the bars where they actually EXECUTE -- i.e. only on
    confirming bars, not every bar. This port instead computes `atr_v`/
    `hl_sma_v` as ordinary EVERY-BAR series (via this fork's own `atr()`
    and a plain `.rolling(14).mean()`) and indexes into them at the
    bars the source's sparse calls would have landed on. The two are NOT
    proven identical series -- Pine's own conditional-call-site semantics
    for `ta.*` functions are a known subtlety this port does not attempt
    to replicate bar-for-bar. The every-bar interpretation is the
    deliberate, reasonable choice here (an every-bar ATR/SMA series is
    the only practical way to look up "the ATR value at the pivot bar,
    however many bars ago that was" without re-deriving a sparse-call
    warm-up state machine), not an oversight; flagged explicitly because
    every OTHER quirk in this file (the /10 divisor, the barsAgo clamp,
    the atrNear fallback) is reproduced to the digit, and this is the one
    place that is not.

    `atrNear = ta.atr(14)[barsAgo]` reads the ATR value AT THE PIVOT BAR
    itself (`t - bars_ago`, which under this port's construction is
    exactly the pivot's own bar index -- see `_confirm_strict_pivots`),
    with a fallback to `atrCurrent` if that value is NaN or <= 0 (matches
    the source's `if na(atrAtIdx) or atrAtIdx <= 0: atrAtIdx :=
    ta.atr(14)` guard). If the fallback ALSO fails to produce a usable
    (finite, positive) value -- both possible only in very early history,
    before ATR(14) has warmed up -- this returns NaN rather than raising
    or dividing by zero; the source has no equivalent second guard
    because Pine's own na propagation makes `atrCurrent / na` silently
    `na`, which is exactly what this early return reproduces.

    `swirlSum` scans `i = 0..10` (11 bars, INCLUSIVE of the confirming
    bar itself at i=0) but `swirlAvg = swirlSum / 10` divides by 10, not
    11 -- reproduced exactly as an off-by-one quirk in the source, not
    "fixed" here, same translate-the-math-as-computed discipline as
    `sr_force.py`'s `_retest_score` (whose own module docstring documents
    an analogous capped-count/uncapped-sum quirk). A scanned bar is
    skipped (contributes 0, not counted toward a different denominator)
    when its own high/low is NaN, when the scan runs off the start of
    history (`j = t - i < 0`), or when that bar's own 14-bar SMA(high-low)
    normalizer is NaN or <= 0 -- matching the source's `if not na(high[i])
    and not na(low[i])` and `if not na(avgRange) and avgRange > 0` guards.
    """
    pivot_idx = t - bars_ago
    atr_near = atr_v[pivot_idx] if pivot_idx >= 0 else np.nan
    if np.isnan(atr_near) or atr_near <= 0:
        atr_near = atr_v[t]
    if np.isnan(atr_near) or atr_near <= 0:
        return np.nan
    atr_current = atr_v[t]
    volatility_change = atr_current / atr_near  # NaN propagates naturally if atr_current is NaN

    swirl_sum = 0.0
    for i in range(0, 11):
        j = t - i
        if j < 0:
            continue  # matches Pine's `not na(high[i])` guard at the start of history
        h, l = high_v[j], low_v[j]
        if np.isnan(h) or np.isnan(l):
            continue
        avg_range = hl_sma_v[j]
        if np.isnan(avg_range) or avg_range <= 0:
            continue
        swirl_sum += (h - l) / avg_range

    swirl_avg = swirl_sum / 10.0  # deliberately 10, not 11 -- see docstring
    if np.isnan(volatility_change):
        return np.nan
    return min(swirl_avg * volatility_change, 5.0)


def sr_decay(high, low, close, swing_len=None, max_levels=None, offset=None, **kwargs):
    """Indicator: S/R Decay Metrics (SRD) -- level staleness + local range turbulence"""
    swing_len = _validated_int(swing_len, 5, "swing_len")
    max_levels = _validated_int(max_levels, 20, "max_levels")

    min_len = 2 * swing_len + 1
    high = verify_series(high, min_len)
    low = verify_series(low, min_len)
    close = verify_series(close, min_len)
    offset = get_offset(offset)

    if high is None or low is None or close is None: return

    n = len(close)
    high_v = high.to_numpy(dtype=float)
    low_v = low.to_numpy(dtype=float)
    close_v = close.to_numpy(dtype=float)

    atr_v = _atr(high, low, close, length=14).to_numpy(dtype=float)
    hl_sma_v = (high - low).rolling(14).mean().to_numpy(dtype=float)

    ph = _confirm_strict_pivots(high, swing_len, swing_len, is_high=True)  # confirmed swing highs -> resistance candidates
    pl = _confirm_strict_pivots(low, swing_len, swing_len, is_high=False)  # confirmed swing lows  -> support candidates

    atten_res = np.full(n, np.nan)
    atten_sup = np.full(n, np.nan)
    swirl_res = np.full(n, np.nan)
    swirl_sup = np.full(n, np.nan)

    # time_decay is a CONSTANT for the whole call under this port's fixed
    # swing_len -- see _attenuation's docstring.
    time_decay = min(swing_len / 50.0, 1.0)

    res_levels = []  # resistance pool, from confirmed swing HIGHS -- FIFO-capped at max_levels
    sup_levels = []  # support pool,    from confirmed swing LOWS  -- FIFO-capped at max_levels

    for t in range(n):
        # --- level creation: atten/swirl are computed ONCE, at
        # confirmation, exactly matching the source's script order (the
        # `array.push` call happens immediately after `calcAttenuation`/
        # `calcSwirl` return, both evaluated on the confirming bar). The
        # source never re-scores a level after it enters the pool -- same
        # frozen-at-creation discipline as sr_force.py's retest score. ---
        if not np.isnan(ph[t]):
            price = ph[t]
            atten = _attenuation(price, close_v[t], time_decay)
            swirl = _swirl(atr_v, hl_sma_v, high_v, low_v, t, swing_len)
            res_levels.append(_Level(price, atten, swirl))
            if len(res_levels) > max_levels:
                res_levels.pop(0)  # FIFO cap, mirrors the source's `array.remove(..., 0)` on overflow
        if not np.isnan(pl[t]):
            price = pl[t]
            atten = _attenuation(price, close_v[t], time_decay)
            swirl = _swirl(atr_v, hl_sma_v, high_v, low_v, t, swing_len)
            sup_levels.append(_Level(price, atten, swirl))
            if len(sup_levels) > max_levels:
                sup_levels.pop(0)

        # --- nearest-active-level lookup, side-constrained, inclusive
        # >=/<= -- same discipline as sr_force.py's DIST/SCORE columns
        # (Fletcher-MAJOR precedent there): a level exactly AT Close still
        # qualifies (reports that level's atten/swirl, not NaN); a level
        # on the wrong side of price (price has since traded through it)
        # is excluded even though it never leaves the pool except via the
        # FIFO cap. Uses the SAME pivot pool construction (same
        # swing_len/max_levels defaults) as sr_force -- calling both with
        # matching params reports on the SAME underlying levels. ---
        c = close_v[t]
        res_cands = [lv for lv in res_levels if lv.price >= c]
        if res_cands:
            nearest = min(res_cands, key=lambda lv: lv.price - c)
            atten_res[t] = nearest.atten
            swirl_res[t] = nearest.swirl
        sup_cands = [lv for lv in sup_levels if lv.price <= c]
        if sup_cands:
            nearest = min(sup_cands, key=lambda lv: c - lv.price)
            atten_sup[t] = nearest.atten
            swirl_sup[t] = nearest.swirl

    atten_res = Series(atten_res, index=close.index)
    atten_sup = Series(atten_sup, index=close.index)
    swirl_res = Series(swirl_res, index=close.index)
    swirl_sup = Series(swirl_sup, index=close.index)

    if offset != 0:
        atten_res = atten_res.shift(offset)
        atten_sup = atten_sup.shift(offset)
        swirl_res = swirl_res.shift(offset)
        swirl_sup = swirl_sup.shift(offset)

    if "fillna" in kwargs:
        for s in (atten_res, atten_sup, swirl_res, swirl_sup):
            s.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        for s in (atten_res, atten_sup, swirl_res, swirl_sup):
            s.fillna(method=kwargs["fill_method"], inplace=True)

    _props = f"_{swing_len}"
    atten_res.name = f"SRD_ATTEN_RES{_props}"
    atten_sup.name = f"SRD_ATTEN_SUP{_props}"
    swirl_res.name = f"SRD_SWIRL_RES{_props}"
    swirl_sup.name = f"SRD_SWIRL_SUP{_props}"

    df = DataFrame({
        atten_res.name: atten_res,
        atten_sup.name: atten_sup,
        swirl_res.name: swirl_res,
        swirl_sup.name: swirl_sup,
    })
    df.name = f"SRD{_props}"
    df.category = "trend"

    return df


sr_decay.__doc__ = \
"""S/R Decay Metrics (SRD) -- level staleness + local range turbulence

Companion port to `sr_force.py` (same source, same confirmed-swing-pivot
level pool construction, same `_confirm_strict_pivots`/fixed-`swing_len`
scheme) -- computes the source's TWO OTHER per-level scalars,
`calcAttenuation` and `calcSwirl`, that `sr_force.py` deliberately did NOT
port (see that file's module docstring). Confirmed swing pivots become
resting S/R levels -- resistance above from swing highs, support below
from swing lows -- held in a bounded, per-side FIFO pool (`max_levels`, no
other eviction). Each level's Attenuation (a 0..1 "how stale is this
level" index: 60% time-since-confirmation + 40% how far price has already
moved away from it) and Swirl (a 0..5 "how turbulent has recent trading
range been, relative to the level's own birth volatility" index) are
computed ONCE, at confirmation, exactly like `sr_force.py`'s re-test
score -- never re-scored as the level ages in the pool.

Source: TradingView community indicator "ATK/DEF Support Resistance S/R
Channel Rating Engine" by ATTDEFS, https://www.tradingview.com/script/2wGxbRZP/
(ported into AwakenAnalytics/Backtesting TVPTA continuation, 2026-08-13;
MPL-2.0 per TradingView's open-source publication convention). This
source is a documented SUPERSET of `1BcGW1Og` ("ATK/DEF Support
Resistance SR Force Matrix", already ported as `sr_force.py`) -- same
`calcHistoricalPower`/`calculateResistanceBehavior`/
`calculateSupportBehavior` touch-behavior engine, PLUS `calcAttenuation`
(module 4.5) and `calcSwirl` (module 4.6). This port implements ONLY the
two new scalars; the shared touch-behavior/re-test-score base is NOT
re-ported here -- see `sr_force.py` for that (calling `sr_force()` and
`sr_decay()` with matching `swing_len`/`max_levels` reports on the SAME
underlying level pool, so `SRF_SCORE_RES`/`SRF_DIST_RES` and
`SRD_ATTEN_RES`/`SRD_SWIRL_RES` describe the SAME nearest resistance
level at a given bar -- they are meant to be read together).

NOT ported (out of scope for both this file and `sr_force.py`):
`calcHistoricalPower` (a THIRD separate per-level metric -- ATR-normalized
price shock x volume multiple x recency weight; still deferred, see
`datastore/source/pine_candidates_families.csv`'s `1BcGW1Og`/`2wGxbRZP`
rows), the auto-timeframe multiplier (`getTimeFrameMultiplier`, only ever
feeds `calcHistoricalPower`), candle pressure (module 5), the channel-line
drawing through consecutive same-side pivots (module 9.5, `line.new` only
-- no scalar output), and all label/table drawing (modules 7, 10, 11, 12).

⚠ `swing_len` is a FIXED parameter here, not the source's adaptive
`autoBars` -- IDENTICAL deviation to `sr_force.py` (same default,
`swing_len=5`), see that file's module docstring for the full account of
why (the honest reason is portability/simplicity: no sibling port in this
fork's `trend/` package reproduces a bar-varying pivot window). One
CONSEQUENCE specific to this port's two new scalars, not shared with
`sr_force.py`: because `swing_len` is fixed (not the source's
per-bar-varying `autoBars`), `barsAgo` at a level's confirming bar is
ALWAYS exactly `swing_len` (never the source's `if barsAgo < 0: barsAgo :=
0` clamp path), which collapses `calcAttenuation`'s `timeDecay` term to a
SINGLE CONSTANT for an entire `sr_decay()` call (`min(swing_len / 50,
1.0)` -- 0.1 at the default `swing_len=5`) rather than a genuinely
per-level computation as in the source (where a bar-varying `autoBars`
would make `timeDecay` vary level-to-level). Only the `priceDecay` term
(and therefore final `attenuation`) still varies per level.

⚠ `calcSwirl`'s `swirlSum` scans `i = 0..10` (11 bars) but `swirlAvg =
swirlSum / 10` divides by 10, not 11 -- reproduced exactly as a
translate-the-math-as-computed choice, not "fixed" here (same discipline
`sr_force.py`'s `_retest_score` docstring uses for its own analogous
capped-count/uncapped-sum quirk). `calcSwirl` also combines TWO different
volatility measures faithfully kept distinct: `ta.atr(14)` (Wilder/RMA
true range, gap-inclusive) for the `atrNear`/`atrCurrent` ratio, vs. a
plain 14-bar SMA of `high - low` (bar range, no gap) as each scanned bar's
own normalizer inside the sum -- see `_swirl`'s docstring for the full
account.

⚠ `SRD_ATTEN_RES`/`SRD_ATTEN_SUP`/`SRD_SWIRL_RES`/`SRD_SWIRL_SUP`'s
"nearest active level" framing is this port's own addition (the source
only ever draws ALL qualifying levels as chart labels, filtered by the
separate, not-ported `calcHistoricalPower >= powerThreshold`) --
IDENTICAL side-constrained (inclusive `>=`/`<=`, not strict `>`/`<`)
nearest-level argmin as `sr_force.py`'s `SRF_DIST_RES`/`SRF_DIST_SUP`,
applying that file's own Fletcher-MAJOR lesson from the start here rather
than re-discovering it: a resistance candidate's price must be AT OR
ABOVE Close, a support candidate's AT OR BELOW, BEFORE ranking by
distance -- required because a level here never resolves on a break, only
FIFO eviction, so a stale wrong-side level can sit in the pool
indefinitely. Regression test:
`tests/test_sr_decay.py::test_atten_and_swirl_report_real_values_not_nan_when_close_equals_level_price`
(+ support-side mirror) assert real (non-NaN) `ATTEN`/`SWIRL` values, not
NaN, at the exact equality boundary. `SRD_ATTEN_RES`/`SRD_ATTEN_SUP` are
in [0, 1] whenever populated (the source's own `attenuation` cap);
`SRD_SWIRL_RES`/`SRD_SWIRL_SUP` are in [0, 5] whenever populated (the
source's own `swirlScore` cap, matching `sr_force.py`'s `SRF_SCORE_*`
range). ⚠ The NaN-pairing between `ATTEN`/`SWIRL` is ONE-DIRECTIONAL, NOT
the two-way pairing `sr_force.py`'s `SRF_SCORE_*`/`SRF_DIST_*` have:
`ATTEN.isna()` implies `SWIRL.isna()` (no side-valid level at all -> both
NaN, same "no candidate" gate), but NOT the reverse -- `_attenuation`
never itself returns NaN for a positively-priced level confirmed on a bar
with a non-NaN Close (it has no ATR dependency -- see the two exceptions
in family-structure-smc.md §2h; neither is observed in this project's
datastore), while `_swirl` CAN return NaN for a level confirmed
before `ATR(14)` had ANY valid history yet (very early bars only), and
that NaN is then frozen on the level like every other per-level scalar
here. So a level from early history can report a real `ATTEN` alongside a
permanently-NaN `SWIRL`; a level with no candidate at all reports NaN on
both. Verified: `tests/test_sr_decay.py::
test_atten_swirl_bounded_and_atten_isna_implies_swirl_isna` (the bound,
across a random-walk fixture) and, end-to-end, `tests/test_sr_decay.py::
test_atten_real_swirl_permanently_nan_for_early_history_level` (a
constructed level that actually exhibits real-ATTEN/NaN-SWIRL, proving
the positive case the bound alone cannot -- Fletcher MAJOR round 1: an
earlier version of the first test asserted the LOGICAL INVERSE of this
paragraph, `atten.notna() => swirl.notna()`, and passed only because its
fixture had no early-history level to catch it; fixed, and the missing
positive test added, same round). This port intentionally does not
re-expose its own DIST column -- combine with `sr_force()`'s
`SRF_DIST_RES`/`SRF_DIST_SUP` for distance.

Calculation:
    Default Inputs:
        swing_len=5, max_levels=20
    Confirmed pivot high/low via strict-unique-extreme rule (`ta.pivothigh`/
        `ta.pivotlow` semantics, see `_confirm_strict_pivots`) -- a swing at
        bar i confirms at bar i + swing_len. IDENTICAL pool construction to
        `sr_force()` -- same levels, if called with matching params.
    On confirmation at bar t, for pivot price P:
        time_decay = min(swing_len / 50, 1.0)                      (constant per call)
        price_change_pct = abs(Close[t] - P) / P * 100
        price_decay = min(price_change_pct / 10, 1.0)
        attenuation = min(time_decay * 0.6 + price_decay * 0.4, 1.0)

        atr_near = ATR(14)[t - swing_len]  (fallback to ATR(14)[t] if NaN/<=0)
        volatility_change = ATR(14)[t] / atr_near
        swirl_sum = sum_{i=0..10} (High[t-i] - Low[t-i]) / SMA(High-Low, 14)[t-i]
            (each term skipped if its own bar or normalizer is NaN/<=0)
        swirl = min((swirl_sum / 10) * volatility_change, 5.0)
        level (price=P, atten=attenuation, swirl=swirl) pushed onto that
        side's pool; if pool size > max_levels, the OLDEST level is
        dropped (FIFO).
    SRD_ATTEN_RES / SRD_SWIRL_RES = the nearest ACTIVE resistance level's
        (price >= Close) attenuation / swirl; NaN if none qualify.
    SRD_ATTEN_SUP / SRD_SWIRL_SUP: mirror on the support side (price <= Close).

Args:
    high (pd.Series): Series of 'high's
    low (pd.Series): Series of 'low's
    close (pd.Series): Series of 'close's
    swing_len (int): Bars either side required for a pivot. Must be a
        positive int if given. Default: 5
    max_levels (int): Max active levels tracked PER SIDE. Must be a
        positive int if given. Default: 20
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Raises:
    ValueError: `swing_len`/`max_levels` given and not a positive, finite,
        integral value (NaN/+-inf/negative/non-integral-float all raise).
        `None` (the actual default sentinel) still means "use the
        default," not an error.

Returns:
    pd.DataFrame: SRD_ATTEN_RES, SRD_ATTEN_SUP, SRD_SWIRL_RES, SRD_SWIRL_SUP.
"""
