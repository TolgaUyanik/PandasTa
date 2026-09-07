# -*- coding: utf-8 -*-
import numpy as np
from pandas import DataFrame
from pandas_ta.utils import get_offset, verify_series


def fvg(high, low, close, max_zones=None, offset=None, **kwargs):
    """Indicator: Fair Value Gap (FVG)"""
    # Validate Arguments
    max_zones = int(max_zones) if max_zones and max_zones > 0 else 10
    high = verify_series(high, 3)
    low = verify_series(low, 3)
    close = verify_series(close, 3)
    offset = get_offset(offset)

    if high is None or low is None or close is None: return

    n = len(close)
    fvg_bull_flag = np.zeros(n)
    fvg_bear_flag = np.zeros(n)
    in_fvg_bull = np.zeros(n)
    in_fvg_bear = np.zeros(n)

    # Spot FVG formations (3-bar pattern)
    for i in range(2, n):
        if low.iloc[i] > high.iloc[i - 2]:
            fvg_bull_flag[i] = 1
        if high.iloc[i] < low.iloc[i - 2]:
            fvg_bear_flag[i] = 1

    # Zones are (zone_low, zone_high) with zone_low < zone_high in BOTH lists.
    # The previous form stored the bear pair reversed and, in the same
    # iteration that created a zone, retained it only while `close <= zone_high`
    # (bull) / `close >= zone_low` (bear) -- conditions that read `close[i] <=
    # low[i]` and `close[i] >= high[i]`, true only on an exact tie. Every zone
    # was therefore evicted on the bar that created it and IN_FVG_* could never
    # fire: 0 in 12,000 probe bars. See FVGDEAD in TODO.md.
    bull_zones = []
    bear_zones = []

    for i in range(2, n):
        c = close.iloc[i]

        # Test membership against zones that already existed, BEFORE adding the
        # one this bar forms: a gap is not something price is "inside" on the
        # bar that opens it.
        active_bull = []
        for (zl, zh) in bull_zones:
            if zl <= c <= zh:
                in_fvg_bull[i] = 1
            # A bullish gap is filled once price closes back through its floor.
            if c > zl:
                active_bull.append((zl, zh))
        bull_zones = active_bull[-max_zones:]

        active_bear = []
        for (zl, zh) in bear_zones:
            if zl <= c <= zh:
                in_fvg_bear[i] = 1
            # A bearish gap is filled once price closes back through its ceiling.
            if c < zh:
                active_bear.append((zl, zh))
        bear_zones = active_bear[-max_zones:]

        if fvg_bull_flag[i]:
            bull_zones.append((high.iloc[i - 2], low.iloc[i]))
            bull_zones = bull_zones[-max_zones:]
        if fvg_bear_flag[i]:
            bear_zones.append((high.iloc[i], low.iloc[i - 2]))
            bear_zones = bear_zones[-max_zones:]

    df = DataFrame({
        "FVG_BULL":    fvg_bull_flag,
        "FVG_BEAR":    fvg_bear_flag,
        "IN_FVG_BULL": in_fvg_bull,
        "IN_FVG_BEAR": in_fvg_bear,
    }, index=close.index)

    df.name = "FVG"
    df.category = "trend"

    if offset != 0:
        df = df.shift(offset)

    if "fillna" in kwargs:
        df.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        df.fillna(method=kwargs["fill_method"], inplace=True)

    return df


fvg.__doc__ = \
"""Fair Value Gap (fvg)

Detects 3-bar Fair Value Gaps (imbalances) and tracks whether the
current bar is inside an active (unfilled) FVG zone.

Sources:
    AwakenAnalytics custom indicator (indicator_engine.py)
    ICT (Inner Circle Trader) concept

⚠ Membership and fill are both evaluated on CLOSE, not on the bar's low/high.
    This deliberately differs from the wick-based ICT mitigation convention: it
    keeps the column a close-based flag rather than an intrabar-touch flag,
    which is the form the rest of this fork's features take.

Calculation:
    FVG_BULL = 1 when low[i] > high[i-2]  (gap up, bullish imbalance)
    FVG_BEAR = 1 when high[i] < low[i-2]  (gap down, bearish imbalance)
    IN_FVG_BULL = 1 when close is inside an active bullish FVG zone
    IN_FVG_BEAR = 1 when close is inside an active bearish FVG zone

    A zone is [high[i-2], low[i]] for a bull gap and [high[i], low[i-2]] for a
    bear one. Membership is tested against zones that already existed, BEFORE
    the zone this bar forms is added -- a gap is not something price is
    "inside" on the bar that opens it. A bull zone expires once close falls
    back through its floor; a bear zone once close rises through its ceiling.

⚠ FVGDEAD (2026-09-07): before this, the zone was appended and then, in the
    SAME iteration, retained only while `close[i] <= low[i]` (bull) -- true on
    an exact tie only. So a zone survived its own formation bar ONLY when the
    bar closed exactly on its low (bear: exactly on its high).

    On synthetic continuous-float frames that never happens and both columns
    were constant zero (0 fires in 12,000 bars). On REAL data it happens often
    -- 86,415 of 408,253 BIST daily bars (21.17%) close exactly at their high
    or low -- so the old columns did fire, at 18,895 (bull) and 14,320 (bear),
    a 4.63% / 3.51% rate against the repaired 22.17% / 19.85%. Reproduce with
    Gate 0 of the measurement script; artifact `fvg_prerepair_counts.csv`.

    That is the reason for the repair, not merely the volume: which zones
    survived was decided by whether a close happened to tie the bar's extreme,
    i.e. by tick rounding, not by the structure the indicator names.

    Measured after the repair, on 89 BIST_100 frames / 408,253 daily bars
    (`Backtesting/scripts/analysis/measure_fvg_overlap_full.py`):

      Gate C  IN_FVG_BULL 90,506 fires (rate 0.2217), IN_FVG_BEAR 81,021
              (0.1985); 89/89 frames fire, 0 saturated. FVG_BULL/FVG_BEAR are
              unchanged by the repair (62,969 / 53,929).
      Gate D  dyadic scales x2/x8/x64/x1024 bit-identical (0 differing cells
              of 1,633,012). Non-dyadic x10 / x3.7 differ on 63 / 35 cells
              (0.004% / 0.002%) -- these columns are strict comparisons of
              price levels, so rounding can flip an exact tie.
      Gate E  max |Spearman rho| against all 361 other engine columns, measured
              on THIS module's output. At measurement time the engine still
              kept a private, unrepaired copy of the loop, so the pooled frame
              had to be overwritten with `ta.fvg` first -- scoring it as-is
              would have measured the column being replaced. The engine's two
              research copies now delegate here (FVGENG-0), so that overwrite
              is asserted rather than assumed; only the live container's copy
              still diverges:
                IN_FVG_BULL -0.6390 x FSME_CE_DIST_BULL_5, n = 30,667
                IN_FVG_BEAR -0.5962 x FSME_CE_DIST_BEAR_5, n = 22,824
              Both below the 0.76 ship line, and exactly one comparator each
              exceeds 0.5. ⚠ Those maxima ride a SPARSE comparator (7.5% of
              the pooled bars): against full-coverage comparators the maxima are
              0.3680 (DIST_PREV_LOW, n=408,164) and 0.3158 (DIST_PREV_HIGH,
              n=408,164). 361 is the total comparator count; 108 of them reach
              all 408,253 bars.
              Artifacts: `backtest_results/tvpta6/fvg_overlap_gridA_full.csv`,
              `fvg_gateC_reachability.csv`, `fvg_gateD_scale_mismatch.csv`,
              `fvg_prerepair_counts.csv`.

Args:
    high (pd.Series): Series of 'high's
    low (pd.Series): Series of 'low's
    close (pd.Series): Series of 'close's
    max_zones (int): Maximum number of active zones to track. Default: 10
    offset (int): Periods to offset. Default: 0

Returns:
    pd.DataFrame: FVG_BULL, FVG_BEAR, IN_FVG_BULL, IN_FVG_BEAR
"""
