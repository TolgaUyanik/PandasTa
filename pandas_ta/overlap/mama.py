# -*- coding: utf-8 -*-
"""MESA Adaptive Moving Average. Port of TA-Lib's `MAMA`.

TA-Lib is BSD-2-Clause, (c) 1999-2007 Mario Fortier; algorithm by John Ehlers
(*Rocket Science for Traders*, Wiley 2001). Reference implementation:
`ta-lib/src/ta_func/ta_MAMA.c`. Shared Hilbert machinery, the 12-bar warm-up
and the numeric pins: `pandas_ta/cycles/_hilbert.py`. Nothing imports `talib`.

MAMA is an EMA whose alpha is `fastlimit / (rate of change of the Hilbert
phase)`, clamped to `[slowlimit, fastlimit]`: it runs fast when the phase is
turning slowly (a trend) and slow when the phase is racing (a cycle). FAMA is
the same recursion on MAMA at half that alpha.

GATE D / GATE E -- THIS INDICATOR SHIPS NO FEATURE. READ THIS FIRST.

Both MAMA and FAMA are moving averages, so both scale with `close` and neither
is an ML feature on its own. The two scale-free companions were BUILT, WIRED,
MEASURED AND DELETED:

* `MAMAd` (`100*(close/MAMA - 1)`): Spearman **+0.9148** against the engine's
  `NWE_MID_200_8.0_8.0` over 390,453 pooled daily BIST bars.
* `MAMAf` (`100*(MAMA/FAMA - 1)`): Spearman **+0.9408** against `QQE_RSIMA`
  over 405,405 bars.

Both are reverts by the Gate E rule (>= 0.90). This is the outcome the task
brief predicted, for the stated reason: TA-Lib and pandas_ta share heritage,
and "distance from a smoother" is a shape the engine already carries several
times over. An adaptive alpha does not make the distance a new signal.

What is left is the RAW PAIR, which this function now returns by default.
Consequences, all deliberate:

* `mama` is NOT in `Category`, so `df.ta.strategy()` never sweeps it into the
  feature set, and it is in `AnalysisIndicators.strategy`'s default exclusion
  list so that `strategy("all")` -- which enumerates ACCESSORS -- does not run
  it either.
* `df.ta.mama()` still works and the port stays pinned against `talib.MAMA`,
  so the measurement is reproducible.
* `emit_dist=True` brings the two deleted columns back for re-measurement, the
  way `tvstop` keeps its deleted `TVS_DIST` reachable.

GATE A -- WHERE THE PORT IS NOT EXACT, AND WHY

Max|diff| against `talib` over 20 daily BIST frames / 28,548 bars is 2.7e-6
(MAMA) and 2.7e-4 (FAMA), against <= 3.2e-13 for every other read-out of the
same state machine. All of it comes from ONE bar of one frame
(`ISMEN_IS_1d` bar 2327) where our detrender rounds to exactly 0.0 and
TA-Lib's does not. Alpha is a CLAMPED reciprocal of a phase difference, so a
1-ulp difference in `atan(Q1/I1)` becomes 0.05 vs 0.5 and the recursion
carries it. See the long comment in `_hilbert.ht_state`.
"""
import numpy as np
from pandas import DataFrame

from pandas_ta.cycles._hilbert import LOOKBACK_32, _WARMUP_32, blank_lookback, ht_state
from pandas_ta.utils import get_offset, verify_series


def mama(close, fastlimit=None, slowlimit=None, offset=None, **kwargs):
    """Indicator: MESA Adaptive Moving Average (MAMA)"""
    fastlimit = float(fastlimit) if fastlimit is not None else 0.5
    slowlimit = float(slowlimit) if slowlimit is not None else 0.05
    close = verify_series(close)
    offset = get_offset(offset)
    if close is None: return
    # `raw` is accepted and ignored: the raw levels are now the DEFAULT output.
    kwargs.pop("raw", None)
    emit_dist = bool(kwargs.pop("emit_dist", False))

    px = close.to_numpy(dtype=float)
    state = ht_state(px, _WARMUP_32, fastlimit=fastlimit, slowlimit=slowlimit)
    m = blank_lookback(state["mama"], LOOKBACK_32)
    f = blank_lookback(state["fama"], LOOKBACK_32)

    suffix = f"{fastlimit}_{slowlimit}"
    data = {f"MAMA_{suffix}": m, f"FAMA_{suffix}": f}
    if emit_dist:
        with np.errstate(divide="ignore", invalid="ignore"):
            m_safe = np.where(m == 0.0, np.nan, m)
            f_safe = np.where(f == 0.0, np.nan, f)
            data[f"MAMAd_{suffix}"] = 100.0 * (px / m_safe - 1.0)
            data[f"MAMAf_{suffix}"] = 100.0 * (m / f_safe - 1.0)

    df = DataFrame(data, index=close.index)

    if offset != 0:
        df = df.shift(offset)

    if "fillna" in kwargs:
        df.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        df.fillna(method=kwargs["fill_method"], inplace=True)

    df.name = f"MAMA_{suffix}"
    df.category = "overlap"
    return df


mama.__doc__ = \
"""MESA Adaptive Moving Average (MAMA)

Sources:
    TA-Lib `ta_MAMA.c` (BSD-2-Clause)
    John Ehlers, Rocket Science for Traders (Wiley, 2001)

Calculation:
    Default Inputs:
        fastlimit=0.5, slowlimit=0.05
    alpha  = clamp(fastlimit / max(1, prev_phase - phase), slowlimit, fastlimit)
    MAMA   = alpha * close + (1 - alpha) * MAMA[-1]
    FAMA   = 0.5*alpha * MAMA + (1 - 0.5*alpha) * FAMA[-1]
    MAMAd  = 100 * (close / MAMA - 1)   -- DELETED on Gate E, see above
    MAMAf  = 100 * (MAMA / FAMA - 1)    -- DELETED on Gate E, see above
    Warm-up 12 bars, TA-Lib lookback 32.

Args:
    close (pd.Series): Series of 'close's
    fastlimit (float): Upper alpha clamp. Default: 0.5
    slowlimit (float): Lower alpha clamp. Default: 0.05
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    emit_dist (bool): Bring back the DELETED `MAMAd_*` / `MAMAf_*` columns,
        for re-measurement only. They failed Gate E at rho +0.9148 and +0.9408
        and must not be fed to a model. Default: False
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.DataFrame: MAMA_* and FAMA_* -- PRICE LEVELS, not ML features, and
        deliberately outside `Category`. Plus MAMAd_* / MAMAf_* when
        emit_dist=True.
"""
