# -*- coding: utf-8 -*-
import numpy as np
import pandas as pd
from pandas import DataFrame, Series

from pandas_ta.overlap.hlc3 import hlc3
from pandas_ta.utils import get_offset, is_datetime_ordered, verify_series


_VALID_ANCHORS = {"D": "D", "W": "W", "M": "M"}


def _validate_anchor(anchor):
    """None -> default 'W' (documented default, not bad input). Anything
    else must be one of 'D'/'W'/'M' (case-insensitive), or raise --
    matches this batch's established swallowed-bad-kwarg fix (see
    liquidity_sweep._validate_mode / rejection_blocks equivalents): the
    original scaffold pattern silently coerced an unrecognized value,
    this port raises instead."""
    if anchor is None:
        return "W"
    if not isinstance(anchor, str):
        raise ValueError(f"anchor must be a str ('D'/'W'/'M'), got {type(anchor).__name__}: {anchor!r}")
    key = anchor.upper()
    if key not in _VALID_ANCHORS:
        raise ValueError(f"anchor must be one of {sorted(_VALID_ANCHORS)}, got {anchor!r}")
    return _VALID_ANCHORS[key]


def _validate_min_samples(min_samples):
    """None -> disabled (documented default -- exact Pine-parity
    behavior, no extra masking beyond the stdev==0 guard). Anything else
    must be a finite, positive, INTEGRAL numeric value, or raise -- same
    swallowed-bad-kwarg shape this batch has fixed repeatedly elsewhere
    (bpress's `length`, liquidity_sweep's `swing_len`, etc.)."""
    if min_samples is None:
        return None
    if isinstance(min_samples, bool) or not isinstance(min_samples, (int, float, np.integer, np.floating)):
        raise ValueError(f"min_samples must be numeric, got {type(min_samples).__name__}: {min_samples!r}")
    if not np.isfinite(min_samples):
        raise ValueError(f"min_samples must be finite, got {min_samples}")
    if min_samples < 1:
        raise ValueError(f"min_samples must be >= 1, got {min_samples}")
    if float(min_samples) != int(min_samples):
        raise ValueError(f"min_samples must be integral, got {min_samples}")
    return int(min_samples)


def avwap_z(high, low, close, volume, anchor=None, min_samples=None, offset=None, **kwargs):
    """Indicator: Anchored VWAP Z-Score (AVWAP_Z)"""
    # Validate Arguments
    anchor = _validate_anchor(anchor)
    min_samples = _validate_min_samples(min_samples)
    high = verify_series(high)
    low = verify_series(low)
    close = verify_series(close)
    volume = verify_series(volume)
    offset = get_offset(offset)
    if high is None or low is None or close is None or volume is None:
        return

    # The reset boundary is a pandas Period, derived from each bar's own
    # timestamp (`index.to_period(anchor)`) -- this is the SAME technique
    # `pandas_ta.overlap.vwap` already uses for its own anchor resets
    # (`wp.groupby(wp.index.to_period(anchor)).cumsum()`), deliberately
    # reused rather than reinvented so both anchored-VWAP forms in this
    # fork share one reset convention. It requires only a DatetimeIndex
    # timestamp per bar -- no sub-hourly session-open detection -- which
    # is why this candidate is portable at all (see the file-level
    # docstring's Anchor Portability section below): unlike a candidate
    # needing e.g. an intraday 09:30 session-open time, "did the
    # day/week/month change since the previous bar" is answerable from a
    # single daily OR hourly bar timestamp alone.
    if not isinstance(close.index, pd.DatetimeIndex):
        raise ValueError(
            "avwap_z requires a DatetimeIndex (needed for the anchor-period "
            f"reset via .to_period({anchor!r})); got index type "
            f"{type(close.index).__name__}. `pandas_ta.overlap.vwap` only "
            "warns and then crashes later on this same gap -- this port "
            "raises explicitly instead, per this batch's swallowed-bad-"
            "input convention (see docstring in bpress.py / liquidity_sweep.py)."
        )
    # ORDERING, not just typing (Fletcher round 1, MAJOR): a DatetimeIndex
    # that is present but NOT sorted ascending passes the isinstance check
    # above yet silently breaks causality below -- `groupby(periods).
    # cumsum()`/`.transform("first")` both follow ROW order, not TIME
    # order, so an out-of-order frame lets a bar's output incorporate a
    # LATER-timestamped row that merely appears earlier in the frame.
    # `pandas_ta.overlap.vwap` calls this exact same `is_datetime_ordered`
    # check but only WARNS and continues; this port raises instead, per
    # its own stated convention of raising rather than silently degrading
    # (matches the type check just above, which already claimed to be
    # stricter than vwap.py here -- prior to this check that claim was
    # only true for TYPE, not ORDER; it is genuinely true for both now).
    if not is_datetime_ordered(close):
        raise ValueError(
            "avwap_z requires a time-ordered (ascending) DatetimeIndex; "
            "groupby(periods).cumsum() and groupby(periods).transform('first') "
            "both follow ROW order, not TIME order, so unsorted input silently "
            "produces non-causal results (a bar's output can incorporate a "
            "later-timestamped row that appears earlier in the frame). Sort "
            "the input by its index before calling."
        )

    # Calculate Result
    #
    # Pine (module 1 of the source, the only module this port translates --
    # see the __doc__ "NOT ported" section for module 2):
    #   src = hlc3
    #   if anchor: cumPV := 0; cumV := 0; cumPV2 := 0
    #   cumPV  += src * volume
    #   cumV   += volume
    #   cumPV2 += volume * src^2
    #   vwapVal  = cumV > 0 ? cumPV / cumV : na
    #   variance = cumV > 0 ? max(cumPV2/cumV - vwapVal^2, 0) : na
    #   stdev    = sqrt(variance)
    #
    # This is the textbook volume-weighted plug-in (population, NOT
    # Bessel-corrected) variance: Var_w[X] = E_w[X^2] - E_w[X]^2, weighted
    # by `volume` rather than by an observation count. There is no
    # separate "ddof" convention to reconcile here (unlike e.g.
    # `ta.stdev()`, which does carry an explicit ddof kwarg) -- Pine's
    # formula IS the biased/population estimator by construction (no
    # `-1`/`N-1` term appears anywhere in cumPV2/cumV - vwapVal^2), so
    # this port's TARGET result reproduces it exactly. It is NOT, however,
    # computed via Pine's own literal cumPV2/cumV - vwapVal^2 subtraction
    # -- see the numerical-stability note just below.
    #
    # NUMERICAL STABILITY (a deliberate, verified deviation from Pine's
    # literal formula, not a semantic one): Pine's `cumPV2/cumV -
    # vwapVal^2` subtracts two large near-equal numbers (both ~price^2)
    # whenever a period's TRUE variance is small relative to price^2 --
    # classic catastrophic cancellation. Measured directly on this file's
    # own test fixture (tests/test_avwap_z.py::_random_ohlcv(), n=120,
    # seed=11), comparing the naive `cumPV2/cumV - vwapVal^2` formula
    # against this reformulation, both evaluated on the fixture as-is and
    # on the SAME fixture with high/low/close scaled by k=1000 (volume
    # unchanged) -- mathematically required to leave Z unchanged (see the
    # docstring's Scale-invariance section), so any difference is pure
    # floating-point error:
    #   naive formula:  max |Z(1x) - Z(1000x)| = 2.96e-09
    #                    max relative stdev error = 1.0 (i.e. a stdev
    #                    that should be ~0 came out finite at one scale
    #                    and exactly 0.0 at the other -- a full sign/
    #                    magnitude flip, not just noise)
    #                    NaN mask (stdev==0 positions): scale-DEPENDENT
    #                    (differs between the 1x and 1000x runs)
    #   this reformulation: max |Z(1x) - Z(1000x)| = 2.87e-13  (~10,300x tighter)
    #                    max relative stdev error = 3.72e-14
    #                    NaN mask: scale-INVARIANT (identical both runs)
    # The fix -- computing the sum of squares as a deviation from a fixed
    # per-period REFERENCE value (here, each period's own first
    # typical_price) rather than from the (much larger) raw price -- is
    # algebraically IDENTICAL to Pine's formula (Var(X) = Var(X - ref) for
    # any constant `ref`). It reduces, but does not eliminate, the
    # boundary flip-flop at any finite precision, so `stdev > 0` below is
    # a description of intent, not a bulletproof guarantee at the
    # sub-epsilon boundary. Re-measure against `_random_ohlcv()` (same
    # method as above) if this formula changes again.
    typical_price = hlc3(high=high, low=low, close=close)
    periods = close.index.to_period(anchor)

    ref = typical_price.groupby(periods).transform("first")
    deviation = typical_price - ref
    wpd = deviation * volume
    wpd2 = (deviation ** 2) * volume

    cum_v = volume.groupby(periods).cumsum()
    cum_pvd = wpd.groupby(periods).cumsum()
    cum_pvd2 = wpd2.groupby(periods).cumsum()

    with np.errstate(invalid="ignore", divide="ignore"):
        # `.where(cum_v > 0)`, not `.replace(0.0, np.nan)`: Pine's guard is
        # `cumV > 0 ? ... : na`, which also maps a NEGATIVE cumV to na (not
        # reachable with a real OHLCV feed -- volume is never negative --
        # but `.replace(0.0, ...)` would let a negative cumV survive as
        # finite garbage instead of na, a real divergence from Pine even
        # though it costs nothing to close given volume is never negative
        # in practice).
        cum_v_safe = cum_v.where(cum_v > 0)
        mean_deviation = cum_pvd / cum_v_safe
        vwap_val = ref + mean_deviation
        variance = (cum_pvd2 / cum_v_safe) - mean_deviation ** 2
    variance = variance.clip(lower=0.0)  # matches Pine's `math.max(variance, 0)` -- guards tiny float negatives
    stdev = np.sqrt(variance)

    # Z-SCORE: (close - vwap) / stdev, in sigma units. This is this port's
    # OWN addition -- the source .pine never computes a z-score, only
    # plots the raw vwapVal/upper/lower band price LEVELS (see __doc__
    # "NOT ported" for why those raw levels are deliberately excluded
    # here). stdev==0 happens deterministically on the FIRST bar of every
    # anchor period (n=1 sample -> cumPV2/cumV == vwapVal^2 exactly) and,
    # more rarely, on any bar where every sample in the period so far has
    # had an identical typical_price. Pine's own bands would plot a
    # degenerate (zero-width) band there; dividing (close - vwap_val) by
    # a zero stdev would instead blow up to +/-inf here (close != vwap_val
    # in general, since vwap_val is built from hlc3, not close) -- an inf
    # is a worse ML feature than a NaN (poisons any downstream scaling/
    # comparison silently), so this port maps stdev==0 to NaN explicitly,
    # a deliberate deviation the source's own math doesn't have to make
    # since it never divides by stdev at all.
    with np.errstate(invalid="ignore", divide="ignore"):
        z = (close - vwap_val) / stdev
    z = z.where(stdev > 0)

    # THE n=2 CASE (Fletcher round 1, MAJOR): the n=1 guard just above
    # only prevents a divide-by-EXACTLY-zero; it does NOT bound Z once a
    # period has 2+ samples. Solving the n=2 case in closed form (2
    # samples, volumes v1/v2, typical prices p1/p2): vwap = (p1*v1 +
    # p2*v2)/(v1+v2) (the ordinary 2-point VWAP), stdev = |p1-p2| *
    # sqrt(v1*v2)/(v1+v2), and therefore
    #     Z(2nd bar) = (p2 - vwap) / stdev = sign(p2-p1) * sqrt(v1/v2)
    # -- i.e. on a period's SECOND bar, Z depends on NOTHING but the
    # ratio of the first two bars' VOLUMES, is completely UNBOUNDED (a
    # 100:1 volume ratio between consecutive bars, unremarkable on a
    # thin BIST name, gives |Z|=10 from price action alone), and is
    # heavy-tailed rather than merely "occasionally large": measured
    # directly on this file's own `_random_ohlcv()` test fixture (n=2000,
    # seed=11, anchor="W") AVWAP_Z_W ranges -857.22..106.31 over the full
    # series; 0.75% of ALL rows have |Z|>5, 0.35% have |Z|>10; every one
    # of those extreme values sits on a period's 2nd-or-early bar (see
    # tests/test_avwap_z.py::test_second_bar_of_period_z_is_unbounded_by_
    # volume_ratio for the exact closed-form pin, and the module
    # docstring's "THE n=2 CASE" section for the full derivation +
    # measurement). This is a REAL property of the ported formula, not a
    # bug to silently paper over -- Pine's own bands are exactly as
    # degenerate there (a near-zero-width band around 2 points is exactly
    # as volume-ratio-driven as this Z is), this port just makes the
    # degeneracy visible as a number instead of an invisible pixel-width
    # band on a chart.
    #
    # `min_samples` (opt-in, default None/disabled -- Pine parity):
    # forces Z to NaN for any bar where fewer than `min_samples` samples
    # have accumulated in the current anchor period so far, INCLUDING the
    # n=2 case above (n=1 is already NaN via the stdev==0 guard
    # regardless of this parameter). This is a PORT DEVIATION, not
    # something the source does or needs (the source never computes a
    # ratio, only plots bands, so it has no analogous "too few samples"
    # failure mode) -- purely a downstream-ML-safety knob a caller can
    # opt into. Deliberately NOT applied to DIST_PCT: that column is a
    # price ratio, not a stdev ratio, and has no comparable degeneracy at
    # small n -- a 2-sample VWAP is a noisier ESTIMATE of the eventual
    # within-period VWAP, not a numerically unbounded quantity, so
    # masking it would throw away well-behaved information for no
    # numerical-safety reason. Deliberately NOT folded into the column
    # NAME (unlike `anchor`, a structural parameter that changes which
    # formula/reset-boundary applies): `min_samples` only ever REMOVES
    # values from the SAME Z definition, the same relationship every
    # other optional masking knob in this file (`offset`, `fillna`) has
    # to its own column name.
    if min_samples is not None:
        bar_count = typical_price.groupby(periods).cumcount() + 1
        z = z.where(bar_count >= min_samples)

    # DIST_PCT: signed % distance from the anchored VWAP itself, scaled by
    # price rather than by stdev -- the SAME "raw level -> scale-free
    # distance" transform this project's `dist_to_res_level` established
    # as precedent (CLAUDE.md Indicator Book: "raw price-LEVEL indicators
    # ... earn nothing by design -- only their scale-free DISTANCE forms
    # do"). Deliberately a DIFFERENT normalization from the Z column
    # above (divides by `close`, not by the anchor-period's evolving
    # stdev), so the two columns are not redundant: DIST_PCT is a pure
    # price-relative measure (comparable in magnitude to e.g.
    # dist_to_res_level's own % form), while Z additionally accounts for
    # how much the anchor period has dispersed so far. Sign convention
    # matches liquidity_sweep's DIST_RES/DIST_SUP -- positive means price
    # is above the reference level.
    dist_pct = (close - vwap_val) / close * 100.0

    z.name = f"AVWAP_Z_{anchor}"
    dist_pct.name = f"AVWAP_DIST_PCT_{anchor}"

    if offset != 0:
        z = z.shift(offset)
        dist_pct = dist_pct.shift(offset)

    if "fillna" in kwargs:
        z.fillna(kwargs["fillna"], inplace=True)
        dist_pct.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        z.fillna(method=kwargs["fill_method"], inplace=True)
        dist_pct.fillna(method=kwargs["fill_method"], inplace=True)

    # Category is "volume" (volume-weighted inputs -- consistent with
    # every sibling in this directory), which disagrees on its face with
    # the ML-register/family-doc placement of AVWAP_Z_*/AVWAP_DIST_PCT_*
    # under "Band / channel" (center-line +/- sigma-envelope SHAPE, see
    # docs/indicators/family-band-channel.md Sec 2.8 in the Backtesting
    # repo) -- both are correct, they're just two different axes
    # (pandas_ta Category = what the inputs are; ML-register family =
    # what the output SHAPE is), the same split NWE (Sec 2.7 on the same
    # page) already lives with.
    df = DataFrame({z.name: z, dist_pct.name: dist_pct})
    df.name = f"AVWAP_Z_{anchor}"
    df.category = "volume"

    return df


avwap_z.__doc__ = \
"""Anchored VWAP Z-Score (AVWAP_Z)

Ports ONLY Module 1 ("MODULO 1: VWAP Anclado (automatico)") of the
TradingView community indicator "MAEM - Volume Suite" by MAEmisary,
https://www.tradingview.com/script/wbrAnavm/ (ported into AwakenAnalytics/
Backtesting TVPTA continuation, 2026-08-11).

pandas_ta Category: "volume" (volume-weighted inputs, consistent with
every sibling in this directory). ML-register family (downstream, in
the Backtesting repo): "Band / channel" (center-line +/- sigma-envelope
SHAPE), see docs/indicators/family-band-channel.md Sec 2.8 -- both are
correct at once, they classify along different axes (inputs vs. output
shape); nothing else in this docstring cross-references that split, so
it's stated here explicitly.

Anchor portability (why this candidate is portable at all, unlike the
immediately preceding declined candidate W74Algwa-...-v6, which needed a
sub-hourly 04:00-09:30 pre-market session WINDOW this fork's daily/hourly
OHLCV pipeline cannot construct): the source offers 4 anchor options via
`input.string(..., options=['Sesion','Semana','Mes','Fecha fija'])`,
detected each bar as `ta.change(time('D'|'W'|'M')) != 0` (or, for
'Fecha fija', a one-time `time >= fixedDate and time[1] < fixedDate`
crossing). Every one of these is a DAY/WEEK/MONTH BOUNDARY check against
the bar's own timestamp -- not an intraday clock-time window -- so it
needs only "did the calendar day/week/month change since the previous
bar," answerable from a single daily-bar OR hourly-bar timestamp alone.
This is exactly the reset convention `pandas_ta.overlap.vwap` already
implements via `index.to_period(anchor)`; this port reuses it rather
than reinventing it.

3 of the 4 Pine anchor options are ported (mapped 1:1 to pandas period
aliases): 'Sesion' -> "D", 'Semana' -> "W", 'Mes' -> "M". 'Fecha fija'
(fixed date) is deliberately NOT ported: it is a one-off, single
arbitrary cutoff timestamp (`input.time`, defaulting to a specific
2026-01-01 in the source) rather than a periodic, repeating boundary --
it does not generalize into a systematic per-bar ML feature the way the
3 periodic anchors do, and every other anchored-VWAP precedent in this
fork (`pandas_ta.overlap.vwap`) is periodic-only too.

Default anchor is "W" (week), NOT "D" like `pandas_ta.overlap.vwap`'s own
default -- a deliberate deviation, not an oversight. "D" degenerates on
this fork's DAILY-bar data: every bar starts its own new anchor period
(n=1), so cumPV2/cumV == vwapVal^2 exactly and every single Z value comes
out NaN (stdev==0, see below) -- structurally useless as a daily-bar
default. "D" is still fully supported and meaningful for this fork's
HOURLY bars (multiple bars per trading day), just not the safer default.

Deliberately LEFT OUT, and why:
    - Module 2 ("MODULO 2: Perfil de Volumen (aproximado) -- POC / VAH /
      VAL"), the entire approximate Volume Profile block, gated by
      `if enableVolProfile and barstate.islast`. This computes a
      histogram over the trailing `vpLookback` bars ONCE, on the final
      bar only (`barstate.islast`) -- a single non-series snapshot for
      drawing boxes/lines, not a per-bar causal feature a walk-forward
      backtest or live signal loop can evaluate on every row. It also
      duplicates this fork's own `pandas_ta.volume.vp` (Volume Profile),
      already ported. Per the CSV triage note (`pine_candidates_
      families.csv`, slug `wbrAnavm`), this was flagged as "real,
      non-duplicate market-structure math, but ... disproportionate work
      for this pass" -- the disproportion argument stands for a
      dedicated future pass; the barstate.islast / non-series argument
      is the harder, structural reason it is out of scope for THIS port
      regardless of effort.
    - Module 1's own raw price-LEVEL outputs: `vwapVal`
      (plot('AVWAP', ...)) and the 4 fixed-multiple bands `upper1/lower1/
      upper2/lower2` (vwapVal +/- mult1*stdev, vwapVal +/- mult2*stdev).
      Per this project's Indicator Book law (CLAUDE.md: "raw price-LEVEL
      indicators (MAs, bands, pivots, prior levels) earn nothing by
      design (nominal-drift decay) -- only their scale-free DISTANCE
      forms do"), none of these 5 raw levels is ported as a column. The
      2 columns this port DOES produce are that "scale-free distance
      form": AVWAP_Z (distance in the anchor period's own sigma units)
      and AVWAP_DIST_PCT (distance as % of current price). A separate
      "distance to the mult1/mult2 bands" column was considered and
      rejected as REDUNDANT, not merely simplified away: since the bands
      are `vwap +/- mult*stdev` with mult a caller-supplied CONSTANT,
      "distance from Z to band mult1" is exactly `mult1 - Z` -- a pure
      affine (additive-constant) transform of the Z column already
      produced, carrying zero information an ML model's own bias term
      couldn't already absorb from Z alone. `mult1`/`mult2` are therefore
      not even accepted as parameters here (no plotted quantity depends
      on them once the raw levels are dropped).

THE n=2 CASE -- Z is unbounded and heavy-tailed on each anchor period's
2nd bar, driven purely by the intra-period volume ratio (Fletcher round
1, MAJOR -- this was previously undocumented; only the n=1 case above
was). Solving the n=2 case in closed form (2 samples, volumes v1/v2,
typical prices p1/p2): vwap = (p1*v1 + p2*v2)/(v1+v2) (the ordinary
2-point VWAP), stdev = |p1-p2| * sqrt(v1*v2)/(v1+v2), therefore:
    Z(2nd bar) = (p2 - vwap) / stdev = sign(p2-p1) * sqrt(v1/v2)
This depends on NOTHING but the ratio of the first two bars' volumes --
a 100:1 volume ratio between consecutive bars (unremarkable on a thin
BIST name) gives |Z|=10 from price action alone, regardless of how
small the actual price move was. Measured directly on this file's own
`_random_ohlcv()` test fixture (n=2000, seed=11, anchor="W"):
AVWAP_Z_W ranges -857.22..106.31 over the full 2000-bar series; 0.75%
of ALL rows have |Z|>5, 0.35% have |Z|>10 -- these are not rare
one-off outliers, every extreme sits on a period's 2nd-or-early bar,
by construction. This is a REAL property of the ported formula, not a
bug silently papered over: Pine's own fixed-multiple bands are exactly
as degenerate at n=2 (a near-zero-width band spanning 2 points is just
as volume-ratio-driven), this port merely turns that same degeneracy
into a visible number instead of an invisible pixel-width band on a
chart. See `min_samples` below for an opt-in mitigation, and
tests/test_avwap_z.py::test_second_bar_of_period_z_is_unbounded_by_
volume_ratio for the closed-form pin (volumes [10000, 100] -> exactly
sqrt(100) = 10.0).

⚠ Register caveat: `docs/knowledgebase/IndicatorMLRegister.md`'s
auto-measured range for `AVWAP_Z_W` is NOT trustworthy evidence against
the above -- `scripts/utils/gen_indicator_register.py`'s synthetic
fixture hardcodes `Volume=1e6` (a CONSTANT), which forces v1==v2==1e6
on every 2-sample period and pins that register row's measured Z to
exactly +/-1.0 on its own fixture. Real (non-constant) volume is what
produces the blowup measured above; the register's narrow range is an
artifact of its own generator, not a property of this indicator.

Calculation:
    Default Inputs:
        anchor="W" ("D", "W", or "M"), min_samples=None (disabled)
    typical_price = HLC3 = (high + low + close) / 3
    Reset each bar's cumulants to 0 at the first bar of every new
        `index.to_period(anchor)` period (day/week/month boundary):
            cumPV  = groupby(period).cumsum(typical_price * volume)
            cumV   = groupby(period).cumsum(volume)
            cumPV2 = groupby(period).cumsum(volume * typical_price^2)
    vwap  = cumPV / cumV                              (NaN where cumV <= 0)
    var   = max(cumPV2/cumV - vwap^2, 0)               (NaN where cumV <= 0)
    stdev = sqrt(var)
    AVWAP_Z_{anchor}        = (close - vwap) / stdev   (NaN where stdev == 0 --
                                deterministically true on every period's own
                                first bar; this port's own divide-by-zero
                                guard, the source never divides by stdev.
                                UNBOUNDED, heavy-tailed on the period's 2nd
                                bar and not fully tamed for several bars
                                after -- see "THE n=2 CASE" above. If
                                `min_samples` is given, ALSO NaN wherever
                                fewer than `min_samples` samples have
                                accumulated in the current period so far.)
    AVWAP_DIST_PCT_{anchor} = (close - vwap) / close * 100  (never masked
                                by `min_samples` -- see Args below)

Scale-invariance: both outputs are already ratios (Z divides by a
same-unit stdev, DIST_PCT divides by close and multiplies by 100), so
scaling every OHLCV price column by a constant k>0 leaves both columns
ALGEBRAICALLY unchanged. Not byte-identical in floating point, though:
measured directly on `_random_ohlcv()` (n=120, seed=11) at k=1000 --
max |Z(1x) - Z(1000x)| = 2.87e-13, max relative stdev error = 3.72e-14,
NaN mask (stdev==0 positions) scale-INVARIANT (identical both scales;
the pre-fix naive formula was NOT: 2.96e-09 max |Z| error, relative
stdev error up to 1.0, and a scale-DEPENDENT NaN mask -- see the
numerical-stability comment above the variance calculation in this file
for the full before/after). tests/test_avwap_z.py::test_scale_invariant_
under_price_rescale/_volume_rescale assert to rtol=1e-9/atol=1e-11 (not
exact equality, and not the older/looser 1e-6 this test used before
Fletcher round 1 tightened it to something that actually has teeth
against the measured 2.87e-13 error). Also scale-invariant under volume
rescaling alone (`volume * m` for any constant m>0), verified the same
way.

Args:
    high (pd.Series): Series of 'high's
    low (pd.Series): Series of 'low's
    close (pd.Series): Series of 'close's. Index MUST be a pd.DatetimeIndex,
        SORTED ASCENDING (required for the `.to_period(anchor)` reset
        boundary AND for `groupby(periods).cumsum()`/`.transform("first")`
        to follow chronological rather than merely row order) -- raises
        ValueError on either gap: a non-DatetimeIndex (rather than the
        cryptic AttributeError a bare `.to_period()` call would raise), or
        a DatetimeIndex that is present but not ascending-ordered (rather
        than the silent non-causal-but-doesn't-crash result an unordered
        groupby produces). `pandas_ta.overlap.vwap` checks this exact same
        ordering condition (`is_datetime_ordered`) but only WARNS and
        continues; this port raises on both checks instead, consistent
        with its own stated convention elsewhere (`anchor`/`min_samples`
        validation below) of raising rather than silently degrading.
    volume (pd.Series): Series of 'volume's
    anchor (str): One of "D" (day/session), "W" (week), or "M" (month),
        case-insensitive. Must match one of these 3 if given, or raises
        ValueError -- the scaffold's own swallowed-bad-kwarg shape this
        batch has repeatedly fixed elsewhere (liquidity_sweep's `mode`,
        rejection_blocks' equivalents). `None` (the actual default
        sentinel) is not an error and means "use the default."
        Default: "W"
    min_samples (int): Opt-in port deviation, OFF by default (Pine
        parity): if given, forces AVWAP_Z_{anchor} to NaN for every bar
        where fewer than `min_samples` samples have accumulated in the
        current anchor period so far -- a mitigation for "THE n=2 CASE"
        above (an n=1 bar is already NaN regardless, via the stdev==0
        guard). Does NOT affect AVWAP_DIST_PCT_{anchor}, which has no
        comparable small-n numerical degeneracy (see the Calculation
        section). Must be a finite, positive, integral numeric value if
        given, or raises ValueError (same swallowed-bad-kwarg shape as
        `anchor`). `None` (the default) means "disabled," not an error.
        Default: None
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Raises:
    ValueError: `anchor` given and not "D"/"W"/"M" (case-insensitive) or
        not a str; `min_samples` given and not a finite, positive,
        integral numeric value; `close.index` is not a pd.DatetimeIndex,
        or is a pd.DatetimeIndex that is not sorted ascending.

Returns:
    pd.DataFrame: AVWAP_Z_{anchor}, AVWAP_DIST_PCT_{anchor}.
"""
