# -*- coding: utf-8 -*-
"""Range Profile Oscillator (RPO) -- port of TradingView `atvJpWjW`.

Source: `docs/TradingView/pine/atvJpWjW-Range-Profile-Oscillator.pine`
(326 physical lines, `//@version=6`, MPL-2.0, (c) Uncle_the_shooter).

WHAT IS PORTED (source lines 80-203):

  * 80-110  the 50-bin RANGE-OCCUPANCY profile over a `lookback`-bar
            window. Every bar's [low, high] deposits weight into every
            bin it spans. NO volume field is read anywhere in the
            source (`grep -c '\\bvolume\\b'` on the source file returns
            0), which is exactly why this is a VOLATILITY column and
            not a Volume one -- it profiles where price SPENT RANGE,
            not where it traded size.
  * 112-121 the MODAL bin (heaviest bin, first-index tie-break) -> the
            midline price `mid_price`.
  * 123-146 the VALUE AREA: expand outward from the modal bin,
            alternating toward the heavier neighbour, until
            `ob_os_level`% of the total weight is enclosed ->
            `range_low` / `range_high`.
  * 148-150 the payoff, already scale-free:
            `osc = (close - mid_price) / half_range * ob_os_level`.
  * 202-203 `ta.crossover(osc, ob_os_level)` /
            `ta.crossunder(osc, -ob_os_level)` breakout flags.

WHAT IS NOT PORTED:

  * 152-200 plots, hlines, fills, gradients -- drawing only.
  * 215-225 background highlights, two `display.none` score plots and
            the BUY/SELL chart labels -- drawing only.
  * 227-326 the TP/SL block (the source's own `// TP/SL` comment is at
            line 227, its first statement `if (breakout_up or
            breakout_down) and showTargets` at 229). That block is a
            paper-trade simulator (entry line, ATR- or percent-sized
            stop, three RR targets, linefills), not a feature. It is
            declined in full; `atrPeriod`/`slAtrMult`/`rrTp1..3` are
            therefore not arguments here.
  * 205-213 the `sig_filter` alternation state (`var int
            last_signal_dir` at 205, the two gated assignments at
            207-208, the state update at 210-213) -- it blocks a second
            same-direction signal until an opposite one fires. That is
            a POSITION-STATE filter, i.e. the same "am I already long"
            bookkeeping this project's own backtester owns; emitting it
            as a feature would bake one entry policy into a column. The
            RAW `ta.crossover`/`ta.crossunder` are emitted instead,
            which is what `sig_filter = false` (the source's own
            default, line 15) produces.

DELIBERATE SUBSTITUTIONS (two, both documented as such):

  1. `syminfo.mintick` (source line 89, the ONLY `syminfo.`/`session.`/
     `timeframe.`/`request.security` reference in the whole file -- see
     the grep table in the porting notes) has no counterpart outside
     TradingView. The source's guard is `price_range > mintick * 5`:
     "the window is not degenerate". It is replaced by a RELATIVE
     guard, `price_range > min_range_pct * |maxH + minL| / 2`, so the
     port stays scale-free. `min_range_pct = 0.001` (0.1%) is the
     shipped default because at BIST-typical tick/price ratios
     `5 * mintick / price` lands in roughly 0.1%-1% (0.01 tick on a
     500 TL name -> 0.01%; 0.01 tick on a 5 TL name -> 1%), and 0.1% is
     the conservative end of that. `min_range_pct = 0.0` reproduces
     "any strictly positive range".

     HOW MUCH IT ACTUALLY GATES, measured (2026-08-26, over every
     cached BIST daily frame -- 577 frames / 2,133,141 rows /
     2,063,552 bars whose window range is strictly positive): the
     relative floor withdraws 203 further bars, 0.0098%, on 5 of the
     577 frames -- KGYO.IS 72, KSTUR.IS 57, SKYLP.IS 37, RUZYE.IS 20,
     YBTAS.IS 17. On those bars the profile is NOT rebuilt and the
     previous bar's midline and value area are carried forward, which
     is the source's own behaviour when its `mintick * 5` guard fails.
     Reproduce with
     `Backtesting/scripts/analysis/measure_rpo_window_support.py`.
  2. Pine's `add = candle_size * (bin_size / candle_size)` (source
     lines 104/107-110) is algebraically `bin_size` for every bar, so
     the profile is a pure OCCUPANCY COUNT scaled by a constant. Every
     downstream comparison -- the modal-bin argmax, `total * pct`, and
     the running `remaining` subtraction -- is homogeneous of degree 1
     in the weights, so the constant factor is dropped and the weights
     are carried as exact integer counts. This is algebraically
     identical and strictly BETTER conditioned than the source: Pine's
     multiply/divide round-trip leaves ~1 ulp of noise per bar, and
     both the modal-bin argmax and the `remaining > 0` stopping test
     are EXACT-TIE comparisons that this noise can flip.

     This is measured, not assumed. Three transliterations of the same
     source -- `add = candle_size * (bin_size/candle_size)` (literal),
     `add = bin_size` (algebraic), `add = 1` (this port's integer
     count) -- were run over 1,640 co-populated bars of four synthetic
     random-walk frames and DISAGREE WITH ONE ANOTHER:

         literal vs algebraic   77 / 1640 bars  (4.70%)
         literal vs count      100 / 1640       (6.10%)
         algebraic vs count     26 / 1640       (1.59%)

     literal vs count decomposes into a modal-bin flip on 29 bars and a
     value-area edge move on 61 (low) / 66 (high); the enclosed span
     changes by at most 1 bin on 55 of them, by 2 on one and by 4 on
     one. So the Pine answer is not recoverable FROM THE SOURCE TEXT.
     TradingView's own evaluation is deterministic -- it runs one
     definite float program and returns one definite answer -- but the
     text does not FIX that program at the exact-tie comparisons: it
     leaves the accumulation order of `candle_size * (bin_size /
     candle_size)` unpinned, and the three faithful readings above
     disagree on 26-100 of 1,640 bars because of it. There is therefore
     no reading of the text that can be certified bit-exact against
     TradingView without running TradingView. This port implements the
     exact-arithmetic form, which is deterministic AND
     reading-independent.
     `tests/test_range_profile.py::test_transliterations_of_the_source_disagree_with_each_other`
     re-derives those counts, and
     `::test_matches_an_integer_weight_transliteration_exactly` pins
     this module to the count form bar-for-bar.

INCOHERENT-BAR GUARD -- A DELIBERATE DEVIATION, NOT IN THE SOURCE.
A range-binning profile is structurally exposed to a single absurd
print: one bad High stretches `price_range`, and every real bar then
falls into one bucket. TradingView data does not have this problem;
this project's yfinance cache does, and DI-1 is blind to it because
the defect leaves no close-to-close jump.

Measured on `datastore/cache/MGROS_IS_1d.parquet` (5,678 daily bars):
index 159 (2004-12-29) carries `High = 12,235,458` and
`Low = 10,991,174` against `Open = Close = 11.61`, and 162 bars have
`High > 2 * Close` while ZERO bars fail the c2c test. Unguarded, the
oscillator's minimum on that frame is -835.11 and the value-area
width reaches 8,999.32% of price (70 bars above 1,000%) against a
clean-bar maximum of 167.66%. It is not always a visible blow-up:
around index 268-270 the column sits at -79.999, an apparently normal
"at the oversold edge" reading that is entirely an artifact.

The guard is definitional rather than heuristic: a bar failing
`low <= close <= high` is not an OHLC bar, so it is dropped from the
window -- from the extremes that set the bin edges AND from the
deposits -- rather than being allowed to define the profile's range.
On MGROS that catches 162 of 162 absurd bars and takes the minimum to
-391.70 and the width maximum to 167.66 with zero bars above 1,000%;
159 of 5,516 co-populated bars change, and the first 52 populated
bars are withdrawn because MGROS's indices 0-161 are ALL incoherent,
so those windows never had a valid profile to begin with.
`require_coherent_bars=False` restores the source's behaviour exactly.

THE COHERENCE FLOOR (`min_coherent_bars`), added 2026-08-26. The
sentence above covers the windows the guard WITHDRAWS. It does not
cover the windows it EMITS from almost nothing. Masking bars out of
the rolling extremes requires `min_periods=1`, and with no floor that
is taken literally: MGROS bar 162 (2005-01-03) emitted
`RPO_VA_WIDTH_PCT = 7.849436` and `RPO_OSC = 143.454530` from a
110-bar window containing EXACTLY ONE coherent bar -- a 50-bin
"profile" and a "value area" built from a single candle, and nothing
downstream could tell it apart from one backed by 110.

So a bar now needs `min_coherent_bars` surviving bars in its window or
it emits NaN. The default is `bins` (50, clamped to `lookback`): a
`bins`-bucket density is not estimable from fewer than `bins`
observations, which ties the floor to a parameter the caller already
sets rather than to a new magic number. NaN, not carry-forward, is
deliberate and is the OPPOSITE call from the `min_range_pct` guard
above -- that guard fires on a degenerate but REAL window, where the
last valid profile is the best available answer; this one fires on
MISSING DATA, where any emitted number is fabricated. The carried
`mid_price`/`range_*` state is not invalidated, it is simply not read
on such a bar. `min_coherent_bars=0` restores the pre-floor
behaviour. The floor is applied ONLY when `require_coherent_bars=True`
-- the guard-off branch's contract is to reproduce the source exactly,
and its `min_periods = lookback` already forces full support.

⚠ INTERACTION WITH `min_range_pct`, stated because it is latent
rather than live. Because a floored bar leaves the carried state
intact, a LATER bar that clears the floor but then trips the
`min_range_pct` guard would carry a PRE-GAP midline and value area
across the very hole the floor exists to suppress, and emit it as a
normal number. Measured 2026-08-26 over all 577 cached BIST daily
frames: incidence is ZERO -- the floored set {EPLAS.IS, MZHLD.IS,
MGROS.IS} and the range-gated set {KGYO.IS, KSTUR.IS, SKYLP.IS,
RUZYE.IS, YBTAS.IS} are DISJOINT, so no frame can currently exhibit
it. That disjointness is a property of this cache, NOT of the
algorithm -- re-check it after any cache refresh before relying on
this note.

BLAST RADIUS, measured 2026-08-26 over every cached BIST daily frame
(577 frames / 2,133,141 rows / 2,069,619 bars where a profile is
reachable at all): 19 bars sit on a window holding fewer than 20
coherent bars and 4 on fewer than 5 -- ALL 23 on MGROS.IS. At the
shipped floor of 50 the count is 295 bars on 3 frames (EPLAS.IS 163,
MZHLD.IS 83, MGROS.IS 49). Re-running the module on those 3 frames
before and after: every changed cell is a WITHDRAWAL, 0 values change
and 0 cells appear -- VA_WIDTH loses 49/163/83, each break flag
49/164/87 (the extra flag cells are the crossing pair's second
endpoint). Both figures are reproduced by
`Backtesting/scripts/analysis/measure_rpo_window_support.py` and
pinned by `test_min_coherent_bars_floors_the_profile_support`.

WHAT THE GUARD DOES NOT CATCH, measured and not hidden. THE COUNT
DEPENDS ON THE PREDICATE, so all three are published (re-measured
2026-08-26 on `ARCLK_IS_1d.parquet`, 6,729 bars; escalated to the
canonical register as row DI-5b -- see
`docs/knowledgebase/06-data-quality.md`):

    High / Low > 2.5                               784 bars
    High / Low > 2.5 AND coherent                  714
    High / Low > 2.5 AND coherent AND close == low 633

All three span the same era, 2000-05-10..2003-05-27, and the ratio on
the coherent set is tight (p1 2.996 / median 3.067 / p99 3.318 / max
3.430). An earlier revision of this block wrote "714 bars ... while
`close == low`", which is the count for the predicate WITHOUT the
`close == low` clause; with it the count is 633. Quote the predicate
beside whichever number is used. These bars are physically impossible
under BIST's +/-10% daily limit but perfectly COHERENT, so the guard
passes every one of them through. That is a whole-era
systematic defect in the High series affecting every High-consuming
indicator in this engine (ATR, natr, Donchian, BB), not a single-print
spike, and it is left as a data-integrity finding rather than patched
behind one indicator. No BIST-specific span filter is applied here:
this module has no way to know its bars come from a limit-banded
exchange.

  CORRECTION (2026-08-25). An earlier revision of this block claimed
  "every emitted column is byte-identical with the guard on and off
  for that frame". That is FALSE and was not measured before it was
  written: ARCLK also carries 103 SEPARATELY incoherent bars (indices
  70..4947), which the guard does fire on, moving 651 of 6,619
  `RPO_VA_WIDTH_PCT` cells, 7 `RPO_BREAK_UP` and 2 `RPO_BREAK_DN`.
  The true, narrow claim -- the one that is actually tested, in
  `test_guard_does_not_rescue_a_coherent_but_impossible_frame` -- is
  that a frame carrying ONLY the coherent-but-impossible shape comes
  back byte-identical with the guard on and off.

CONTAMINATION IS BOUNDED HERE, unlike a zone-lifecycle indicator: the
profile is a FIXED `lookback`-bar rolling window, so one bad print can
reach at most `lookback` subsequent bars. Measured on MGROS: 164
incoherent bars taint 381 of 5,568 populated bars (6.84%).

STATE CARRIED ACROSS BARS (faithful to the source, and a real
property of the column): `mid_price`, `range_high` and `range_low` are
Pine `var float`s (source lines 57-59). They are only reassigned inside
their guards, so on a bar where the range guard fails the PREVIOUS
bar's values persist and the oscillator is computed from them against
TODAY's close. There is one asymmetry, preserved on purpose:
`mid_price` is assigned before the `total > 0` check (line 121) while
`range_low`/`range_high` are assigned after it (lines 145-146), so a
window in which every bar has `high == low` (all weight zero -- a BIST
limit-lock streak is the realistic case) refreshes the midline while
leaving the value area stale.

WHAT WAS BUILT, MEASURED, AND THEN REMOVED (read before re-adding it).
The oscillator of source line 150 -- the source's own headline output,
`RPO_OSC_110_80` -- is COMPUTED here but NOT EMITTED. It was measured
against the COMPLETE 472-column numeric output of the consuming
engine's `IndicatorEngine(include_advanced=True).compute_all()`, pooled
over 89 BIST_100 daily frames / 405,312 bars (395,470 co-populated),
and scored:

    +0.858558  close_vs_qtr_mean_pct
    +0.855717  close_vs_qtr_median_pct
    +0.844715  ICHI_PRICE_VS_CLOUD
    +0.828585  ATRMAX_14_50

-- 8 cells at or above 0.80, and the shape is not one unlucky
comparator: the modal bin of a 110-bar range profile tracks that
window's central tendency closely, so `(close - mid) / half_width` is
close to a volatility-normalised "close versus its quarterly mean",
which this engine already ships. Dropping the two most contaminated
frames (MGROS.IS, ARCLK.IS) moves it to +0.859858, so the number is
not a data artifact either. The consuming project's precedent band is
"~0.9 revert / 0.76-0.80 ship with disclosure", and its own record
includes columns deleted at 0.859 and 0.845, so this one is deleted.
Full grid:
Backtesting/backtest_results/tvpta6/rpo_overlap_20260825.md

WHAT SURVIVED that measurement, and why it is not the same statistic:
the value-area WIDTH (max |rho| 0.548605 vs `sup_level_touches_120`;
0.537112 vs `natr`) and the two CROSSING EVENTS (0.173316 vs
`log_return`; 0.144673 vs `VELOCITY`). The width is the extent of the
DENSEST part of the window rather than the dispersion of all of it,
and a crossing is an event where the oscillator is a level -- neither
duplicates anything in the engine at the level the oscillator did.

SHARED KERNEL. `_profile_bins`, `_poc` and `_value_area` are module-
level and deliberately reusable. `K0SEi3Ct` (TL PbD Shape Pro) source
lines 186-198 run the SAME outward-expansion loop with the same
`vUp >= vDn` tie-break as this source's lines 133-144 -- verified by
reading both, see `_value_area`'s docstring for the line-by-line
correspondence -- and fills its bins with the `mode="overlap"` rule
(its lines 170-175). `Vrrujyso` (Delta Volume Profile) does NOT share
the expansion loop: `grep -c while` on its source returns 0 and it has
no value area at all; it needs only `mode="point"` binning and its own
balance-weighted modal-row score.
"""
import numpy as np
from pandas import DataFrame, Series

from pandas_ta.utils import get_offset, verify_series


def _validated_int(value, default, name, positive=True):
    """None -> default (a normal, documented default, not bad input).
    Anything else must be a genuine, finite, integral value, or raise.
    Same helper, same rejection paths, as `sr_corridor.py`/`dtdb.py`."""
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


# ---------------------------------------------------------------------
# SHARED PROFILE KERNEL
#
# Three functions, all independent of this indicator's parameters, so
# the two remaining profile candidates can import them instead of
# re-implementing:
#
#   K0SEi3Ct  ->  _profile_bins(mode="overlap") + _poc + _value_area
#   Vrrujyso  ->  _profile_bins(mode="point") only (it has no value
#                 area; its modal row uses a delta-BALANCE score, not a
#                 raw max, so it must not call `_poc`)
# ---------------------------------------------------------------------
def _profile_bins(win_high, win_low, lo_edge, bin_size, bins,
                  mode="span", weight=None, price=None):
    """Bin one window of bars into `bins` equal price buckets.

    Returns a float array of length `bins`. `lo_edge` is the price of
    the bottom of bin 0 and `bin_size` the bucket height, so bin `b`
    covers `[lo_edge + b*bin_size, lo_edge + (b+1)*bin_size)`.

    mode="span"      every bin the bar's [low, high] SPANS receives the
                     bar's full weight. Bin indices come from
                     `floor((price - lo_edge) / bin_size)` clamped to
                     `[0, bins-1]`, matching `atvJpWjW` lines 100-101.
                     Bars with `high == low` are SKIPPED, matching that
                     source's `if candle_size > 0` (line 98) -- which
                     means a limit-locked BIST bar contributes nothing.
    mode="overlap"   every bin receives `weight * overlap / (high-low)`,
                     the volume-profile rule of `K0SEi3Ct` lines
                     170-175. Bars with `high <= low` deposit their
                     whole weight into the single bin holding `high`
                     (that source's own `if h <= l` branch, lines
                     166-168), so a locked bar is NOT dropped here.
    mode="point"     the bar's whole weight goes into the one bin
                     holding `price[i]` (`Vrrujyso` lines 126-129 use
                     hlc3). Requires `price`.

    `weight=None` means 1.0 per bar, which is what `atvJpWjW` reduces
    to (see the module docstring, substitution 2).
    """
    win_high = np.asarray(win_high, dtype=float)
    win_low = np.asarray(win_low, dtype=float)
    m = win_high.shape[0]
    if weight is None:
        w = np.ones(m, dtype=float)
    else:
        w = np.asarray(weight, dtype=float)
        if w.shape[0] != m:
            raise ValueError("weight length must match the window length")
    out = np.zeros(bins, dtype=float)
    if bin_size <= 0 or m == 0:
        return out

    if mode == "point":
        if price is None:
            raise ValueError("mode='point' requires `price`")
        p = np.asarray(price, dtype=float)
        idx = np.clip(np.floor((p - lo_edge) / bin_size), 0, bins - 1)
        ok = np.isfinite(p) & np.isfinite(w)
        np.add.at(out, idx[ok].astype(np.int64), w[ok])
        return out

    b1 = np.clip(np.floor((win_low - lo_edge) / bin_size), 0, bins - 1)
    b2 = np.clip(np.floor((win_high - lo_edge) / bin_size), 0, bins - 1)
    finite = np.isfinite(win_high) & np.isfinite(win_low) & np.isfinite(w)

    if mode == "span":
        ok = finite & ((win_high - win_low) > 0)
        if not ok.any():
            return out
        # difference-array accumulation: O(window + bins) instead of the
        # source's nested `for b = b1 to b2` loop, same result.
        diff = np.zeros(bins + 1, dtype=float)
        lo_i = b1[ok].astype(np.int64)
        hi_i = b2[ok].astype(np.int64)
        np.add.at(diff, lo_i, w[ok])
        np.add.at(diff, hi_i + 1, -w[ok])
        return np.cumsum(diff)[:bins]

    if mode == "overlap":
        rng = win_high - win_low
        flat = finite & (rng <= 0)
        if flat.any():
            np.add.at(out, b2[flat].astype(np.int64), w[flat])
        real = finite & (rng > 0)
        for i in np.flatnonzero(real):
            lo_b = int(b1[i])
            hi_b = int(b2[i])
            for b in range(lo_b, hi_b + 1):
                b_bot = lo_edge + b * bin_size
                ov = min(win_high[i], b_bot + bin_size) - max(win_low[i], b_bot)
                if ov > 0:
                    out[b] += w[i] * ov / rng[i]
        return out

    raise ValueError(f"unknown mode {mode!r}")


def _poc(weights):
    """(modal bin index, total weight).

    Strict `>` scan from bin 0 upward, so the LOWEST index wins a tie --
    identical tie-break in `atvJpWjW` lines 115-119 (`if total_bin >
    max_total`) and `K0SEi3Ct` lines 179-184 (`if vv > pocV`).
    `np.argmax` has the same first-maximum rule.
    """
    weights = np.asarray(weights, dtype=float)
    if weights.size == 0:
        return 0, 0.0
    return int(np.argmax(weights)), float(weights.sum())


def _value_area(weights, poc_idx, total, frac):
    """Value area around `poc_idx`, as INCLUSIVE bin indices (lo, hi).

    Expand outward one bin at a time, always toward the heavier
    neighbour, until `frac * total` of the weight is enclosed.

    THE SHARED LOOP. `atvJpWjW` lines 133-144 and `K0SEi3Ct` lines
    189-197 are the same loop written two ways; the correspondence,
    read off both sources:

      atvJpWjW                          K0SEi3Ct
      remaining = total*pct - mid_total vaVol = pocV          (same start:
                                                 the modal bin is
                                                 pre-counted)
      while remaining > 0               while vaVol < total*vaP/100
        and (lowB > 0 or highB < N-1)     and (up < nB or dn >= 0)
      upper = w[highB+1] else -1        vUp = vols[up] else -1.0
      lower = w[lowB-1]  else -1        vDn = vols[dn] else -1.0
      if upper >= lower and upper >= 0  if vUp >= vDn
        highB += 1; remaining -= upper    vaVol += vUp; up += 1
      else if lower >= 0                else
        lowB -= 1;  remaining -= lower    vaVol += vDn; dn -= 1
      -> lowB, highB (last included)    -> dn+1, up-1 (last included)

    The tie-break is `>=` toward the UPPER side in both. atvJpWjW's
    extra `>= 0` guards and its `else: break` are unreachable given the
    while condition (both neighbours can only be -1 when the profile is
    already fully enclosed, which ends the loop), so the two loops are
    behaviourally the same; the guards are kept here because they are
    in the source being ported.

    `frac` is a FRACTION (0.8), not a percent -- the callers do their
    own `/100`, as both sources do.
    """
    weights = np.asarray(weights, dtype=float)
    n_bins = weights.shape[0]
    lo_b = hi_b = int(poc_idx)
    if n_bins == 0 or total <= 0:
        return lo_b, hi_b
    remaining = total * frac - weights[lo_b]
    while remaining > 0 and (lo_b > 0 or hi_b < n_bins - 1):
        upper = weights[hi_b + 1] if hi_b < n_bins - 1 else -1.0
        lower = weights[lo_b - 1] if lo_b > 0 else -1.0
        if upper >= lower and upper >= 0:
            hi_b += 1
            remaining -= upper
        elif lower >= 0:
            lo_b -= 1
            remaining -= lower
        else:
            break
    return lo_b, hi_b


def _fmt(x):
    """`80.0` -> `80`, `0.5` -> `0.5`, for column suffixes."""
    return int(x) if float(x).is_integer() else x


def range_profile(high, low, close, lookback=None, ob_os_level=None,
                  bins=None, min_range_pct=None, require_coherent_bars=True,
                  min_coherent_bars=None, emit_osc=False, offset=None,
                  **kwargs):
    """Indicator: Range Profile Oscillator (RPO)"""
    lookback = _validated_int(lookback, 110, "lookback")
    bins = _validated_int(bins, 50, "bins")
    ob_os_level = _validated_float(ob_os_level, 80.0, "ob_os_level")
    min_range_pct = _validated_float(min_range_pct, 0.001, "min_range_pct",
                                     positive=False)
    if lookback < 2:
        raise ValueError(f"lookback must be >= 2, got {lookback}")
    if bins < 2:
        raise ValueError(f"bins must be >= 2, got {bins}")
    # THE COHERENCE FLOOR (see the module docstring). Default `bins`:
    # a `bins`-bucket density is not estimable from fewer than `bins`
    # observations. Clamped to `lookback` so a `bins > lookback`
    # configuration cannot floor every bar out of existence.
    min_coherent_bars = _validated_int(
        min_coherent_bars, bins if bins <= lookback else lookback,
        "min_coherent_bars", positive=False)
    if min_coherent_bars > lookback:
        raise ValueError(
            f"min_coherent_bars must be <= lookback ({lookback}), "
            f"got {min_coherent_bars}")

    high = verify_series(high, lookback + 1)
    low = verify_series(low, lookback + 1)
    close = verify_series(close, lookback + 1)
    offset = get_offset(offset)
    if high is None or low is None or close is None: return

    n = len(close)
    h_v = high.to_numpy(dtype=float).copy()
    l_v = low.to_numpy(dtype=float)
    c_v = close.to_numpy(dtype=float)

    # DELIBERATE DEVIATION -- NOT IN THE PINE SOURCE. See the module
    # docstring's INCOHERENT-BAR GUARD block. A bar that does not
    # satisfy `low <= close <= high` is not an OHLC bar; it is dropped
    # from the window entirely (both from the min/max that set the bin
    # edges and from the deposits), instead of being allowed to set the
    # profile's range. `require_coherent_bars=False` reproduces the
    # source's unguarded behaviour exactly.
    if require_coherent_bars:
        coherent = (np.isfinite(h_v) & np.isfinite(l_v) & np.isfinite(c_v)
                    & (l_v <= c_v) & (c_v <= h_v))
        h_v = np.where(coherent, h_v, np.nan)
        l_v = np.where(coherent, l_v, np.nan)
        masked_high = Series(h_v, index=high.index)
        masked_low = Series(l_v, index=low.index)
        # `min_periods = 1` is NOT a statement that one bar is enough.
        # It differs from the guard-off branch's `lookback` because the
        # mask can legitimately empty most of a window while the bars
        # that DO have support must still get their rolling extremes.
        # The actual support requirement is `min_coherent_bars`,
        # enforced per bar in the loop below; without it this branch
        # would rebuild a full `bins`-bin profile from a single
        # surviving bar (measured on MGROS.IS -- module docstring).
        min_periods = 1
        support_mask = coherent
    else:
        l_v = l_v.copy()
        masked_high, masked_low = high, low
        min_periods = lookback
        support_mask = np.isfinite(h_v) & np.isfinite(l_v)

    # Source line 82-87: min(low) / max(high) over the SAME window the
    # profile is built from -- bar `t` back through `t - lookback + 1`.
    roll_min = masked_low.rolling(lookback, min_periods=min_periods) \
        .min().to_numpy(dtype=float)
    roll_max = masked_high.rolling(lookback, min_periods=min_periods) \
        .max().to_numpy(dtype=float)
    # Bars surviving into the window `[t - lookback + 1, t]`.
    support = Series(support_mask.astype(float)) \
        .rolling(lookback, min_periods=1).sum().to_numpy(dtype=float)

    osc = np.full(n, np.nan)
    va_width = np.full(n, np.nan)

    mid_price = np.nan
    range_low = np.nan
    range_high = np.nan
    frac = ob_os_level / 100.0

    # Source line 81: `if bar_index >= lookback`. bar_index is 0-based,
    # so the FIRST computed bar is index `lookback` and its window is
    # `[1, lookback]` -- index 0 is never read even though a full
    # window already exists at index `lookback - 1`. That one-bar
    # conservatism is the source's, and is kept.
    for t in range(lookback, n):
        # DELIBERATE DEVIATION -- THE COHERENCE FLOOR, not in the Pine
        # source. Fewer than `min_coherent_bars` surviving bars is
        # MISSING DATA, not the degenerate-but-real window the range
        # guard below handles, so the bar emits NaN instead of a
        # profile built from a handful of bars OR a carried-forward
        # one. The carried state is deliberately left untouched: it is
        # not invalidated, it is simply not read on this bar. Applied
        # only when the coherence guard is on -- `require_coherent_bars
        # =False` must reproduce the source exactly, and there
        # `min_periods = lookback` already forces full support.
        if require_coherent_bars and support[t] < min_coherent_bars:
            continue
        min_l = roll_min[t]
        max_h = roll_max[t]
        if np.isfinite(min_l) and np.isfinite(max_h):
            price_range = max_h - min_l
            # DELIBERATE SUBSTITUTION 1 (see module docstring):
            # `price_range > syminfo.mintick * 5` -> relative floor.
            floor = min_range_pct * abs(max_h + min_l) / 2.0
            if price_range > floor and price_range > 0:
                bin_size = price_range / bins
                w = _profile_bins(h_v[t - lookback + 1:t + 1],
                                  l_v[t - lookback + 1:t + 1],
                                  min_l, bin_size, bins, mode="span")
                mid_bin, total = _poc(w)
                mid_price = min_l + bin_size * (mid_bin + 0.5)
                if total > 0:
                    lo_b, hi_b = _value_area(w, mid_bin, total, frac)
                    range_low = min_l + lo_b * bin_size
                    range_high = min_l + (hi_b + 1) * bin_size

        # Source lines 149-150. Uses whatever `mid_price` / `range_*`
        # currently hold -- refreshed this bar, or carried forward.
        if np.isfinite(range_high) and np.isfinite(range_low) \
                and np.isfinite(mid_price):
            half_range = (range_high - range_low) / 2.0
            if half_range > 0 and np.isfinite(c_v[t]):
                osc[t] = (c_v[t] - mid_price) / half_range * ob_os_level
                if mid_price > 0:
                    va_width[t] = (range_high - range_low) / mid_price * 100.0

    # Source lines 202-203: `ta.crossover` / `ta.crossunder`. NaN
    # wherever either endpoint of the pair is NaN, so warm-up is never
    # reported as "no breakout".
    prev = np.concatenate(([np.nan], osc[:-1]))
    pair_ok = np.isfinite(osc) & np.isfinite(prev)
    break_up = np.where(pair_ok,
                        ((osc > ob_os_level) & (prev <= ob_os_level)).astype(float),
                        np.nan)
    break_dn = np.where(pair_ok,
                        ((osc < -ob_os_level) & (prev >= -ob_os_level)).astype(float),
                        np.nan)

    tag = f"_{lookback}_{_fmt(ob_os_level)}"
    osc_s = Series(osc, index=close.index, name=f"RPO_OSC{tag}")
    vaw_s = Series(va_width, index=close.index, name=f"RPO_VA_WIDTH_PCT{tag}")
    up_s = Series(break_up, index=close.index, name=f"RPO_BREAK_UP{tag}")
    dn_s = Series(break_dn, index=close.index, name=f"RPO_BREAK_DN{tag}")

    if offset != 0:
        osc_s = osc_s.shift(offset)
        vaw_s = vaw_s.shift(offset)
        up_s = up_s.shift(offset)
        dn_s = dn_s.shift(offset)

    if "fillna" in kwargs:
        for s in (osc_s, vaw_s, up_s, dn_s):
            s.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        for s in (osc_s, vaw_s, up_s, dn_s):
            s.fillna(method=kwargs["fill_method"], inplace=True)

    # `RPO_OSC` IS NOT SHIPPED. See "WHAT WAS BUILT, MEASURED, AND THEN
    # REMOVED" in the module docstring: it measured Spearman +0.858558
    # against the consuming engine's `close_vs_qtr_mean_pct` over
    # 395,470 pooled bars. `emit_osc=True` is NOT a feature switch and
    # nothing in production sets it -- it exists so the port's
    # correctness, causality and scale-invariance can still be asserted
    # directly against the quantity every shipped column is derived
    # from. Do not wire it into an engine.
    out = ((osc_s,) if emit_osc else ()) + (vaw_s, up_s, dn_s)
    df = DataFrame({s.name: s for s in out})
    df.name = f"RPO{tag}"
    df.category = "volatility"
    return df


range_profile.__doc__ = """Range Profile Oscillator (RPO)

Ports the calculation half of the TradingView indicator `atvJpWjW`
("Range Profile Oscillator", (c) Uncle_the_shooter, MPL-2.0). Over a
rolling `lookback`-bar window the bar RANGES (not volume -- the source
reads no volume field at all) are binned into `bins` equal price
buckets. The heaviest bucket is the midline; the value area is grown
outward from it, always toward the heavier neighbour, until
`ob_os_level`% of the profile weight is enclosed. The oscillator is
the current close's distance from the midline in units of half the
value-area width, rescaled by `ob_os_level` so that +/-`ob_os_level`
marks the value-area edges.

Filed under `volatility` because it measures how price RANGE is
distributed, and because the porting register
(`datastore/source/pine_candidates_families.csv`, slug
`atvJpWjW-Range-Profile-Oscillator`) records `family=volatility` for
this candidate.

Sources:
    docs/TradingView/pine/atvJpWjW-Range-Profile-Oscillator.pine

Calculation:
    minL      = min(low,  lookback)          # window = [t-lookback+1, t]
    maxH      = max(high, lookback)
    bin_size  = (maxH - minL) / bins
    w[b]      = number of window bars whose [low, high] spans bin b
                (bars with high == low contribute nothing)
    mid_bin   = argmax(w)                    # first maximum wins ties
    mid_price = minL + bin_size * (mid_bin + 0.5)
    lo, hi    = expand outward from mid_bin toward the heavier
                neighbour until ob_os_level% of sum(w) is enclosed
    range_low  = minL + lo * bin_size
    range_high = minL + (hi + 1) * bin_size
    half_range = (range_high - range_low) / 2

    osc              = (close - mid_price) / half_range * ob_os_level
                       (computed, NOT emitted -- see the module docstring)
    (a bar whose window holds fewer than `min_coherent_bars`
     coherent bars is skipped entirely and emits NaN)

    RPO_VA_WIDTH_PCT = (range_high - range_low) / mid_price * 100
    RPO_BREAK_UP     = crossover(osc,  ob_os_level)
    RPO_BREAK_DN     = crossunder(osc, -ob_os_level)

Args:
    high (pd.Series): Series of 'high's
    low (pd.Series): Series of 'low's
    close (pd.Series): Series of 'close's
    lookback (int): Profile window in bars. Default: 110
    ob_os_level (float): Value-area coverage in PERCENT, and the level
        the oscillator's breakout flags fire at. Default: 80.0
    bins (int): Number of price buckets. Default: 50
    emit_osc (bool): NOT A FEATURE SWITCH. `RPO_OSC` is deleted, not
        optional -- see "WHAT WAS BUILT, MEASURED, AND THEN REMOVED"
        above. True adds it back so the port's properties can be
        asserted against it in tests. Default: False
    require_coherent_bars (bool): NOT IN THE SOURCE. Drop any window
        bar failing `low <= close <= high` from both the window
        extremes and the profile deposits. False reproduces the
        source. Default: True
    min_coherent_bars (int): NOT IN THE SOURCE, and the other half of
        the guard above -- the minimum number of surviving bars a
        window must hold before the profile is rebuilt at all. Below
        it the bar emits NaN (it does NOT carry the previous profile
        forward: too few bars is missing data, not a degenerate-but-
        real window). Default: `bins`, clamped to `lookback` -- a
        `bins`-bucket density is not estimable from fewer than `bins`
        observations. 0 disables the floor. Ignored when
        `require_coherent_bars=False`, whose contract is to reproduce
        the source exactly. Default: None (-> `bins`)
    min_range_pct (float): Relative substitute for the source's
        `syminfo.mintick * 5` degeneracy guard -- the window's range
        must exceed this fraction of the window's mid price for the
        profile to be rebuilt (otherwise the previous bar's midline and
        value area are carried forward, as in the source). 0.0 means
        "any strictly positive range". Default: 0.001
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.DataFrame: RPO_VA_WIDTH_PCT, RPO_BREAK_UP, RPO_BREAK_DN columns
        (and RPO_OSC only when `emit_osc=True`, which is a test hook,
        not a production setting).
"""
