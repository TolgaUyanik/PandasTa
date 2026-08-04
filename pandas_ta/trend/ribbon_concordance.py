# -*- coding: utf-8 -*-
from pandas import Series

from pandas_ta.overlap.ma import ma
from pandas_ta.overlap.ema import ema
from pandas_ta.utils import get_offset, verify_series


def ribbon_concordance(close, ma_type=None, base_length=None, spacing=None,
                        ribbon_size=None, smooth_length=None, offset=None, **kwargs):
    """Indicator: Ribbon Rank Concordance (RIBBONCONC)"""
    ma_type = ma_type.lower() if ma_type and isinstance(ma_type, str) else "ema"
    base_length = int(base_length) if base_length and base_length > 0 else 5
    spacing = int(spacing) if spacing and spacing > 0 else 5
    ribbon_size = int(ribbon_size) if ribbon_size and ribbon_size >= 2 else 8
    ribbon_size = min(ribbon_size, 10)
    smooth_length = int(smooth_length) if smooth_length and smooth_length > 0 else 3
    close = verify_series(close, base_length + (ribbon_size - 1) * spacing)
    offset = get_offset(offset)

    if close is None: return

    # A ribbon of `ribbon_size` MAs at increasing periods; for every pair
    # (i, j) with period[i] < period[j], +1 if the shorter-period MA sits
    # above the longer-period one (bullish-consistent ordering), -1 if
    # reversed, 0 if tied -- summed and normalized to [-100, 100] by the
    # number of pairs actually compared.
    lengths = [base_length + i * spacing for i in range(ribbon_size)]
    ribbon = [ma(ma_type, close, length=length) for length in lengths]

    concordance_sum = Series(0.0, index=close.index)
    pair_count = Series(0.0, index=close.index)
    for i in range(ribbon_size - 1):
        for j in range(i + 1, ribbon_size):
            vi, vj = ribbon[i], ribbon[j]
            both_valid = vi.notna() & vj.notna()
            sign = Series(0.0, index=close.index)
            sign[both_valid & (vi > vj)] = 1.0
            sign[both_valid & (vi < vj)] = -1.0
            concordance_sum += sign
            pair_count += both_valid.astype(float)

    raw_concordance = (concordance_sum / pair_count.replace(0, float("nan"))) * 100.0

    # Smooth the ALWAYS-LIVE raw signal first (matching the source:
    # `smoothedConcordance = ta.ema(rawConcordance, postSmoothLen)` runs
    # on the ungated raw score, which is valid from the moment any two
    # ribbon MAs are both non-na -- far earlier than the full ribbon's
    # warmup). Fletcher round 2 (TVPTA-3-composite) caught round 1's
    # warmup-gate fix applying the mask to raw_concordance BEFORE
    # smoothing: that forces the EMA to restart cold exactly when the
    # gate opens, discarding all the pre-warmup smoothing history Pine's
    # EMA had already accumulated -- verified live to disagree with a
    # Pine-faithful recompute by tens of points (on the bounded
    # [-100,100] scale) for several bars after every warmup event, using
    # the indicator's own default smooth_length=3.
    smoothed = ema(raw_concordance, length=smooth_length) if smooth_length > 1 else raw_concordance

    # Fletcher round 1 (TVPTA-3-composite): the source (r25Zyal3.pine
    # ~lines 148-152) gates its DISPLAYED output (`dispConcordance :=
    # warmedUp ? smoothedConcordance : na`) behind `warmedUp = bar_index
    # >= longestPeriod` -- it suppresses the value shown, including
    # partial-ribbon values from just the 2-3 shortest MAs, until the
    # FULL ribbon (including the longest-period MA) has warmed up, but
    # the EMA feeding that display was never gated itself. Applied to the
    # SMOOTHED series here, not the raw one, to match that order.
    # ⚠ Known approximation (Fletcher round 2, not fully resolved): gating
    # on `ribbon[-1].notna()` matches Pine's `bar_index >= longestPeriod`
    # to within one bar for the length-based ma_types (sma/ema/rma/wma/
    # dema/tema -- verified empirically, `.notna()` starts one bar earlier
    # than Pine's literal `bar_index == longestPeriod`), and is NOT
    # equivalent for ma_type="hma" (HMA needs ~sqrt(length) MORE bars to
    # warm up than its nominal length -- Pine's own literal gate does not
    # account for this and would itself leak a partial-ribbon score for
    # HMA ribbons at bar_index==longestPeriod; this port's gate instead
    # waits for HMA's true readiness, arguably more correct but not a
    # literal match to Pine).
    result = smoothed.where(ribbon[-1].notna())

    # Offset
    if offset != 0:
        result = result.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        result.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        result.fillna(method=kwargs["fill_method"], inplace=True)

    _props = f"_{ma_type.upper()}_{base_length}_{spacing}_{ribbon_size}"
    result.name = f"RIBBONCONC{_props}"
    result.category = "trend"

    return result


ribbon_concordance.__doc__ = \
"""Ribbon Rank Concordance (RIBBONCONC)

Builds a ribbon of `ribbon_size` moving averages at increasing periods
(`base_length + i*spacing`), then for every pair of MAs counts whether the
shorter-period one sits above the longer-period one (+1, bullish-
consistent ordering), below it (-1), or tied (0). Summed over all pairs
and normalized to [-100, 100] by the pair count -- +100 means every
shorter MA sits above every longer MA (full bullish alignment), -100 the
mirror. Distinct from a plain MA-ribbon plot (which just draws N lines):
this collapses the ribbon's ORDERING into one scale-free number, and
distinct from `adx`/`vhf` (which measure trend STRENGTH from price
directly, not ribbon self-consistency).

Source: TradingView community indicator "Ribbon Concordance [RC Tools]"
(see `datastore/source/pine_triage.csv` for the exact attribution row)
(ported into AwakenAnalytics/Backtesting TVPTA-3, 2026-08-04; MPL-2.0 per
TradingView's open-source publication convention). Ported in full -- the
pairwise concordance formula is the entire substance of the source; its
color-zone bucketing and background-painting are decorative and not
replicated.

Calculation:
    Default Inputs:
        ma_type="ema", base_length=5, spacing=5, ribbon_size=8, smooth_length=3
    lengths = [base_length + i*spacing for i in range(ribbon_size)]
    ribbon  = [MA(close, length) for length in lengths]
    For every pair (i, j), i < j (i.e. shorter period than j):
        +1 if ribbon[i] > ribbon[j], -1 if <, 0 if ==
    raw = 100 * sum(pair scores) / (number of pairs with both MAs valid)
    smoothed = EMA(raw, smooth_length)  (on the ALWAYS-LIVE raw series --
        matches the source computing its EMA before gating the display)
    RIBBONCONC = smoothed, masked NaN until the FULL ribbon has warmed up
        (the longest-period MA is valid) -- approximates the source's
        `warmedUp` display gate to within one bar for length-based
        ma_types; NOT a literal match for ma_type="hma" (see the
        in-code comment on this)

Args:
    close (pd.Series): Series of 'close's
    ma_type (str): "sma", "ema", "wma", "rma", "hma", "dema", or "tema".
        Default: "ema"
    base_length (int): Shortest MA period. Default: 5
    spacing (int): Period increment between consecutive ribbon MAs.
        Default: 5
    ribbon_size (int): Number of MAs in the ribbon, 2-10. Default: 8
    smooth_length (int): EMA smoothing period applied to the raw score.
        Default: 3
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.Series: RIBBONCONC_{MA_TYPE}_{base_length}_{spacing}_{ribbon_size}
"""
