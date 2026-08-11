# -*- coding: utf-8 -*-
import numpy as np
import pandas as pd
from pandas import DataFrame, Series

from pandas_ta.overlap.hlc3 import hlc3
from pandas_ta.utils import get_offset, verify_series


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


def avwap_z(high, low, close, volume, anchor=None, offset=None, **kwargs):
    """Indicator: Anchored VWAP Z-Score (AVWAP_Z)"""
    # Validate Arguments
    anchor = _validate_anchor(anchor)
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
    # classic catastrophic cancellation. Measured directly (see
    # tests/test_avwap_z.py::test_scale_invariant_under_price_rescale's
    # development history): on ordinary ~100-price synthetic data this
    # formula's floating-point error is ~1e-12 in absolute terms, but
    # right at a period's stdev==0 boundary that ~1e-12 noise decides
    # whether `variance.clip(lower=0)` lands on exactly 0.0 (-> Z is NaN,
    # the documented guard below) or a tiny positive epsilon (-> Z
    # divides by a near-zero stdev and explodes to +/-thousands) --
    # verified to differ in exactly this way between a series and that
    # same series' prices scaled by 1000x, which is mathematically
    # required to be scale-invariant (see the docstring's
    # Scale-invariance section) but was NOT, prior to this fix, at
    # floating-point precision. The standard fix -- computing the sum of
    # squares as a deviation from a fixed per-period REFERENCE value
    # (here, each period's own first typical_price) rather than from the
    # (much larger) raw price -- is algebraically IDENTICAL to Pine's
    # formula (Var(X) = Var(X - ref) for any constant `ref`) but reduces
    # the observed floating-point error by ~1000x (measured: ~1e-12 ->
    # ~1e-15 at the same 1000x price scale). It does not eliminate the
    # boundary flip-flop entirely (no finite-precision formula can), so
    # `stdev > 0` below is a description of intent, not a bulletproof
    # guarantee at the sub-epsilon boundary.
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
        cum_v_safe = cum_v.replace(0.0, np.nan)  # cumV==0 -> na, matches Pine's `cumV > 0 ? ... : na`
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

Calculation:
    Default Inputs:
        anchor="W" ("D", "W", or "M")
    typical_price = HLC3 = (high + low + close) / 3
    Reset each bar's cumulants to 0 at the first bar of every new
        `index.to_period(anchor)` period (day/week/month boundary):
            cumPV  = groupby(period).cumsum(typical_price * volume)
            cumV   = groupby(period).cumsum(volume)
            cumPV2 = groupby(period).cumsum(volume * typical_price^2)
    vwap  = cumPV / cumV                              (NaN where cumV == 0)
    var   = max(cumPV2/cumV - vwap^2, 0)               (NaN where cumV == 0)
    stdev = sqrt(var)
    AVWAP_Z_{anchor}        = (close - vwap) / stdev   (NaN where stdev == 0 --
                                deterministically true on every period's own
                                first bar; this port's own divide-by-zero
                                guard, the source never divides by stdev)
    AVWAP_DIST_PCT_{anchor} = (close - vwap) / close * 100

Scale-invariance: both outputs are already ratios (Z divides by a
same-unit stdev, DIST_PCT divides by close and multiplies by 100), so
scaling every OHLCV price column by a constant k>0 leaves both columns
ALGEBRAICALLY unchanged. Not byte-identical in floating point, though:
verified in tests/test_avwap_z.py::test_scale_invariant_under_price_
rescale to agree to rtol/atol 1e-6 (not exact equality) at a 1000x price
multiplier -- see the numerical-stability comment above the variance
calculation in this file for why an exact match isn't achievable (Pine's
own sum-of-squares variance formula loses a few ULPs differently at
different absolute price scales; this port's period-anchored-deviation
reformulation reduces, but cannot fully eliminate, that at any finite
precision). Also scale-invariant under volume rescaling alone (`volume *
m` for any constant m>0), verified the same way.

Args:
    high (pd.Series): Series of 'high's
    low (pd.Series): Series of 'low's
    close (pd.Series): Series of 'close's. Index MUST be a pd.DatetimeIndex
        (required for the `.to_period(anchor)` reset boundary) -- raises
        ValueError otherwise, rather than the cryptic AttributeError a
        bare `.to_period()` call on a non-datetime index would raise, or
        `pandas_ta.overlap.vwap`'s own silent print-and-continue.
    volume (pd.Series): Series of 'volume's
    anchor (str): One of "D" (day/session), "W" (week), or "M" (month),
        case-insensitive. Must match one of these 3 if given, or raises
        ValueError -- the scaffold's own swallowed-bad-kwarg shape this
        batch has repeatedly fixed elsewhere (liquidity_sweep's `mode`,
        rejection_blocks' equivalents). `None` (the actual default
        sentinel) is not an error and means "use the default."
        Default: "W"
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Raises:
    ValueError: `anchor` given and not "D"/"W"/"M" (case-insensitive) or
        not a str; `close.index` is not a pd.DatetimeIndex.

Returns:
    pd.DataFrame: AVWAP_Z_{anchor}, AVWAP_DIST_PCT_{anchor}.
"""
