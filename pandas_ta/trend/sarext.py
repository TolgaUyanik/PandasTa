# -*- coding: utf-8 -*-
"""Parabolic SAR - Extended. Port of TA-Lib's `SAREXT`.

TA-Lib is BSD-2-Clause, (c) 1999-2007 Mario Fortier. Reference implementation:
`ta-lib/src/ta_func/ta_SAREXT.c`. Nothing here imports `talib`; the recurrence
was pinned numerically against `talib` 0.7.1 -- max|diff| 0.0 over 29,168
daily bars from 20 BIST frames at the defaults, and 0.0 over 6,761 bars at a
deliberately non-default parameter set (offsetonreverse 0.05, long
0.03/0.03/0.30, short 0.01/0.01/0.15), which is what exercises the parameter
handling rather than only the happy path.

HOW IT DIFFERS FROM THE `psar` ALREADY IN THIS FORK

Three things, all of them in `SAREXT` and none of them in `psar`:

1. SEPARATE LONG AND SHORT ACCELERATION SCHEDULES -- init, step and maximum
   are six independent parameters, so an asymmetric stop is expressible.
2. `offsetonreverse` -- a proportional gap applied to the SAR at the instant
   of a reversal, so the new stop does not start exactly at the old extreme.
3. THE SIGN CARRIES THE DIRECTION -- one output series, negative while short.
   `psar` instead emits two mutually-NaN columns, `PSARl` and `PSARs`.

The initial direction is taken, as TA-Lib does, from a one-bar Minus-DM over
the first two bars, unless `startvalue` is non-zero, whose sign then sets it.

GATE D / GATE E -- ONE OF THE TWO CANDIDATE COLUMNS WAS DELETED

`SAREXT` is a signed PRICE LEVEL, so neither it nor anything derived from it
ships raw. Two scale-free candidates were built and measured against the
engine's full 485-column production output over 408,075 pooled daily BIST
bars:

* `SAREXTd` = `100*(close/|SAR| - 1)` -- **DELETED**. Spearman **+0.9850**
  against the engine's own `dist_to_psar_pct`. The engine already computes the
  distance from a Parabolic SAR; recomputing it from an EXTENDED SAR whose
  parameters sit at their symmetric defaults reproduces it almost exactly.
  This is the clearest revert of the batch and it was the predictable one.
* `SAREXTs` = `sign(SAR)` -- **DELETED**, and this one is the reason stage 4
  of the harness exists. Against the main grid it measured **+0.8393** (vs
  `dist_to_psar_pct`), inside the 0.76-0.90 disclose band, and it was about to
  ship on that number. But the engine's own SAR DIRECTION columns --
  `PSAR_Signal` (object: the literal strings "Bullish"/"Bearish") and
  `PSAR_Reversal` (bool) -- are NON-NUMERIC, so `select_dtypes(include=
  [np.number])` silently drops them and the main grid never sees the single
  closest analogue in the engine. Stage 4 re-runs the lane with those three
  coerced, and `SAREXTs` measures **+0.9598 against `PSAR_Signal`** over
  408,075 bars. That is a revert, not a disclosure. A "max rho" taken only
  over the numeric comparators would have been a measured number that was
  nonetheless wrong about the thing it was measuring.

  For the record, the widened stage 4 measured all fourteen candidates against
  those three coerced columns; `SAREXTs` is the ONLY one that breaches 0.90,
  and the eight columns that ship top out at 0.43 there.

THERE IS THEREFORE NO SHIPPED FEATURE HERE. `sarext` returns TA-Lib's signed
price level by default, is OUT of `Category`, and is in
`AnalysisIndicators.strategy`'s default exclusion list. It stays callable so
the port is not lost and Gate A stays reproducible (max|diff| 0.0 against
`talib.SAREXT` over 29,168 bars, at the defaults and off them).
`emit_dist=True` brings both deleted columns back for re-measurement, the way
`tvstop` keeps `TVS_DIST` reachable.
"""
import numpy as np
from pandas import DataFrame

from pandas_ta.utils import get_offset, verify_series


def sarext(high, low, close=None, startvalue=None, offsetonreverse=None,
           accelerationinitlong=None, accelerationlong=None,
           accelerationmaxlong=None, accelerationinitshort=None,
           accelerationshort=None, accelerationmaxshort=None, offset=None,
           **kwargs):
    """Indicator: Parabolic SAR - Extended (SAREXT)"""
    startvalue = float(startvalue) if startvalue is not None else 0.0
    offsetonreverse = float(offsetonreverse) if offsetonreverse is not None else 0.0
    ail = float(accelerationinitlong) if accelerationinitlong is not None else 0.02
    al = float(accelerationlong) if accelerationlong is not None else 0.02
    aml = float(accelerationmaxlong) if accelerationmaxlong is not None else 0.2
    ais = float(accelerationinitshort) if accelerationinitshort is not None else 0.02
    ash = float(accelerationshort) if accelerationshort is not None else 0.02
    ams = float(accelerationmaxshort) if accelerationmaxshort is not None else 0.2

    high = verify_series(high)
    low = verify_series(low)
    offset = get_offset(offset)
    if high is None or low is None: return
    if close is not None:
        close = verify_series(close)
    kwargs.pop("raw", None)
    emit_dist = bool(kwargs.pop("emit_dist", False))

    sar = _sarext_values(high.to_numpy(dtype=float), low.to_numpy(dtype=float),
                         startvalue, offsetonreverse, ail, al, aml, ais, ash, ams)

    suffix = f"{ail}_{aml}"
    # `raw` is accepted and ignored: the signed level is now the DEFAULT.
    data = {f"SAREXT_{suffix}": sar}
    if emit_dist:
        with np.errstate(divide="ignore", invalid="ignore"):
            level = np.abs(sar)
            level = np.where(level == 0.0, np.nan, level)
            ref = close.to_numpy(dtype=float) if close is not None \
                else 0.5 * (high.to_numpy(dtype=float) + low.to_numpy(dtype=float))
            data[f"SAREXTd_{suffix}"] = 100.0 * (ref / level - 1.0)
            data[f"SAREXTs_{suffix}"] = np.sign(sar)

    df = DataFrame(data, index=high.index)

    if offset != 0:
        df = df.shift(offset)

    if "fillna" in kwargs:
        df.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        df.fillna(method=kwargs["fill_method"], inplace=True)

    df.name = f"SAREXT_{suffix}"
    df.category = "trend"
    return df


def _sarext_values(h, l, startvalue, offsetonreverse, ail, al, aml, ais, ash, ams):
    """TA-Lib's `ta_SAREXT.c` recurrence. Signed: negative while short."""
    n = h.size
    out = np.full(n, np.nan)
    if n < 2:
        return out

    af_long, af_short = ail, ais
    if af_long > aml:
        af_long = ail = aml
    if al > aml:
        al = aml
    if af_short > ams:
        af_short = ais = ams
    if ash > ams:
        ash = ams

    start = 1
    if startvalue == 0.0:
        # TA-Lib's one-bar Minus-DM over the first two bars decides the side.
        diff_m = l[start - 1] - l[start]
        diff_p = h[start] - h[start - 1]
        minus_dm = diff_m if (diff_m > 0.0 and diff_m > diff_p) else 0.0
        is_long = 0 if minus_dm > 0.0 else 1
    else:
        is_long = 1 if startvalue > 0.0 else 0

    new_high, new_low = h[start - 1], l[start - 1]
    if startvalue == 0.0:
        ep, sar = (h[start], new_low) if is_long else (l[start], new_high)
    else:
        ep = h[start] if is_long else l[start]
        sar = abs(startvalue)
    # TA-Lib's own comment: "cheat on the newLow and newHigh for the first
    # iteration". Removing it shifts every subsequent bar.
    new_low, new_high = l[start], h[start]

    for t in range(start, n):
        prev_low, prev_high = new_low, new_high
        new_low, new_high = l[t], h[t]

        if is_long:
            if new_low <= sar:
                is_long = 0
                sar = ep
                if sar < prev_high: sar = prev_high
                if sar < new_high: sar = new_high
                if offsetonreverse != 0.0: sar += sar * offsetonreverse
                out[t] = -sar
                af_short = ais
                ep = new_low
                sar = sar + af_short * (ep - sar)
                if sar < prev_high: sar = prev_high
                if sar < new_high: sar = new_high
            else:
                out[t] = sar
                if new_high > ep:
                    ep = new_high
                    af_long += al
                    if af_long > aml: af_long = aml
                sar = sar + af_long * (ep - sar)
                if sar > prev_low: sar = prev_low
                if sar > new_low: sar = new_low
        else:
            if new_high >= sar:
                is_long = 1
                sar = ep
                if sar > prev_low: sar = prev_low
                if sar > new_low: sar = new_low
                if offsetonreverse != 0.0: sar -= sar * offsetonreverse
                out[t] = sar
                af_long = ail
                ep = new_high
                sar = sar + af_long * (ep - sar)
                if sar > prev_low: sar = prev_low
                if sar > new_low: sar = new_low
            else:
                out[t] = -sar
                if new_low < ep:
                    ep = new_low
                    af_short += ash
                    if af_short > ams: af_short = ams
                sar = sar + af_short * (ep - sar)
                if sar < prev_high: sar = prev_high
                if sar < new_high: sar = new_high

    return out


sarext.__doc__ = \
"""Parabolic SAR - Extended (SAREXT)

Sources:
    TA-Lib `ta_SAREXT.c` (BSD-2-Clause)
    J. Welles Wilder, New Concepts in Technical Trading Systems (1978)

Calculation:
    Default Inputs:
        startvalue=0, offsetonreverse=0,
        accelerationinitlong=0.02, accelerationlong=0.02, accelerationmaxlong=0.2,
        accelerationinitshort=0.02, accelerationshort=0.02, accelerationmaxshort=0.2
    SAREXTd = 100 * (close / abs(SAR) - 1)   -- DELETED on Gate E, see above
    SAREXTs = sign(SAR): +1 long, -1 short   -- DELETED on Gate E, see above

Args:
    high (pd.Series): Series of 'high's
    low (pd.Series): Series of 'low's
    close (pd.Series): Series of 'close's, used only for the distance column.
        Falls back to (high+low)/2 when absent.
    startvalue (float): 0 lets a one-bar Minus-DM choose the side; >0 forces
        long from that SAR, <0 forces short from its absolute value.
    offsetonreverse (float): Proportional gap added to the SAR on a reversal.
    accelerationinitlong/long/maxlong (float): Long acceleration schedule.
    accelerationinitshort/short/maxshort (float): Short acceleration schedule.
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    emit_dist (bool): Bring back the DELETED `SAREXTd_*` / `SAREXTs_*`
        columns, for re-measurement only. They failed Gate E at rho +0.9850
        (vs `dist_to_psar_pct`) and +0.9598 (vs the non-numeric `PSAR_Signal`)
        and must not be fed to a model. Default: False
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.DataFrame: SAREXT_* -- a signed PRICE LEVEL, not an ML feature, and
        deliberately outside `Category`. Plus SAREXTd_* and SAREXTs_* when
        emit_dist=True.
"""
