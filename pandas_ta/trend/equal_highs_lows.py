# -*- coding: utf-8 -*-
import numpy as np
from pandas import DataFrame, Series

from pandas_ta.volatility.atr import atr
from pandas_ta.utils import get_offset, verify_series


def _confirm_strict_pivots(series, left, right, is_high):
    """Causal pivot confirmation matching Pine's `ta.pivothigh`/
    `ta.pivotlow`: a bar at position i confirms (becomes visible at
    j=i+right) iff it is the STRICT, UNIQUE extreme of the window
    [i-left, i+right] -- unlike `swing_equilibrium`'s rightmost-tie-wins
    rule (a deliberate choice for that indicator's different source),
    Pine's built-in pivot functions register NO pivot at all on a tie
    (neither side of the tie qualifies). Duplicated as its own function
    here rather than reusing swing_equilibrium's `_confirm_pivots" --
    same causal-confirmation-lag shape, different tie semantics, matching
    this package's convention of self-contained indicator files.
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
        # Strict uniqueness: no OTHER bar in the window (left or right)
        # may also equal the extreme.
        rest = np.delete(w, i - (j - window + 1))
        if np.any(rest == extreme):
            continue
        out[j] = vals[i]
    return Series(out, index=series.index)


def equal_highs_lows(high, low, close, left=None, right=None, tol_mode=None,
                      atr_length=None, atr_mult=None, pct_tol=None,
                      lookback_pivots=None, offset=None, **kwargs):
    """Indicator: Equal Highs / Equal Lows (EQHL)"""
    left = int(left) if left and left > 0 else 5
    right = int(right) if right and right > 0 else 5
    tol_mode = tol_mode.lower() if tol_mode and isinstance(tol_mode, str) else "atr"
    atr_length = int(atr_length) if atr_length and atr_length > 0 else 14
    atr_mult = float(atr_mult) if atr_mult and atr_mult > 0 else 0.10
    pct_tol = float(pct_tol) if pct_tol and pct_tol > 0 else 0.05
    lookback_pivots = int(lookback_pivots) if lookback_pivots and lookback_pivots > 0 else 15
    high = verify_series(high, left + right + 1)
    low = verify_series(low, left + right + 1)
    close = verify_series(close, left + right + 1)
    offset = get_offset(offset)

    if high is None or low is None or close is None: return
    if tol_mode not in ("atr", "percent"): return

    pivot_high = _confirm_strict_pivots(high, left, right, is_high=True)
    pivot_low = _confirm_strict_pivots(low, left, right, is_high=False)

    if tol_mode == "atr":
        tolerance = atr(high, low, close, length=atr_length) * atr_mult
    else:
        tolerance = close * pct_tol / 100.0
    tol_vals = tolerance.to_numpy(dtype=float)

    ph_vals = pivot_high.to_numpy(dtype=float)
    pl_vals = pivot_low.to_numpy(dtype=float)
    n = len(close)

    eqh_flag = np.zeros(n, dtype=int)
    eqh_level_arr = np.full(n, np.nan)
    eqh_broken_arr = np.zeros(n, dtype=int)
    eql_flag = np.zeros(n, dtype=int)
    eql_level_arr = np.full(n, np.nan)
    eql_broken_arr = np.zeros(n, dtype=int)

    close_vals = close.to_numpy(dtype=float)
    active_eqh = np.nan
    active_eql = np.nan

    # Each new confirmed pivot is compared against a bounded, trailing
    # window of the last `lookback_pivots` PRIOR pivots of the same type
    # (independent of the other type -- highs never compared to lows).
    # On the first prior pivot found within tolerance, a level forms at
    # the max (for highs) / min (for lows) of the pair -- matching the
    # source's `break` after the first match, not an average.
    #
    # Fletcher round 1 (TVPTA-3-composite): the source (K3net9Kl-RLS.pine
    # -- "NEW PIVOT HIGH/LOW" at lines 59-98, THEN "REMOVE BROKEN LEVELS"
    # at lines 100-121) runs level FORMATION first, break-check SECOND,
    # within one bar's top-to-bottom pass -- a level formed THIS bar is
    # immediately eligible to be broken by THIS bar's own close. An
    # earlier version of this port ran break-check before formation
    # (and its comment here FALSELY claimed that order "match[ed] the
    # source's box-delete-then-recreate sequence" -- the source's actual
    # sequence is create-then-delete, not delete-then-recreate); fixed to
    # match the source's real order.
    prior_highs = []
    prior_lows = []
    for j in range(n):
        c = close_vals[j]

        if not np.isnan(ph_vals[j]):
            price = ph_vals[j]
            tol = tol_vals[j]
            for ref in reversed(prior_highs):
                if not np.isnan(tol) and abs(price - ref) <= tol:
                    eqh_flag[j] = 1
                    active_eqh = max(price, ref)
                    break
            prior_highs.append(price)
            if len(prior_highs) > lookback_pivots:
                prior_highs.pop(0)
        if not np.isnan(pl_vals[j]):
            price = pl_vals[j]
            tol = tol_vals[j]
            for ref in reversed(prior_lows):
                if not np.isnan(tol) and abs(price - ref) <= tol:
                    eql_flag[j] = 1
                    active_eql = min(price, ref)
                    break
            prior_lows.append(price)
            if len(prior_lows) > lookback_pivots:
                prior_lows.pop(0)

        if not np.isnan(active_eqh) and c > active_eqh:
            eqh_broken_arr[j] = 1
            active_eqh = np.nan
        if not np.isnan(active_eql) and c < active_eql:
            eql_broken_arr[j] = 1
            active_eql = np.nan

        eqh_level_arr[j] = active_eqh
        eql_level_arr[j] = active_eql

    eqh_flag = Series(eqh_flag, index=close.index)
    eql_flag = Series(eql_flag, index=close.index)
    eqh_broken = Series(eqh_broken_arr, index=close.index)
    eql_broken = Series(eql_broken_arr, index=close.index)
    eqh_level = Series(eqh_level_arr, index=close.index)
    eql_level = Series(eql_level_arr, index=close.index)

    dist_eqh_pct = (close - eqh_level) / close * 100
    dist_eql_pct = (close - eql_level) / close * 100

    # Offset
    if offset != 0:
        eqh_flag = eqh_flag.shift(offset)
        eql_flag = eql_flag.shift(offset)
        dist_eqh_pct = dist_eqh_pct.shift(offset)
        dist_eql_pct = dist_eql_pct.shift(offset)
        eqh_broken = eqh_broken.shift(offset)
        eql_broken = eql_broken.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        for s in (eqh_flag, eql_flag, dist_eqh_pct, dist_eql_pct, eqh_broken, eql_broken):
            s.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        for s in (eqh_flag, eql_flag, dist_eqh_pct, dist_eql_pct, eqh_broken, eql_broken):
            s.fillna(method=kwargs["fill_method"], inplace=True)

    _props = f"_{left}_{right}"
    eqh_flag.name = f"EQH{_props}"
    eql_flag.name = f"EQL{_props}"
    dist_eqh_pct.name = f"EQH_DIST{_props}"
    dist_eql_pct.name = f"EQL_DIST{_props}"
    eqh_broken.name = f"EQH_BROKEN{_props}"
    eql_broken.name = f"EQL_BROKEN{_props}"

    df = DataFrame({
        eqh_flag.name: eqh_flag,
        eql_flag.name: eql_flag,
        dist_eqh_pct.name: dist_eqh_pct,
        dist_eql_pct.name: dist_eql_pct,
        eqh_broken.name: eqh_broken,
        eql_broken.name: eql_broken,
    })
    df.name = f"EQHL{_props}"
    df.category = "trend"

    return df


equal_highs_lows.__doc__ = \
"""Equal Highs / Equal Lows (EQHL)

Detects "equal highs"/"equal lows" -- a widely-used SMC/ICT liquidity-pool
concept: a confirmed swing pivot that lands within a small tolerance
(ATR-scaled or %-of-price) of an earlier pivot of the same type forms a
level, interpreted as resting liquidity the market is likely to sweep.
`EQH`/`EQL` are 1 on the bar a new level forms; `EQH_DIST`/`EQL_DIST` are
the scale-free % distance from close to the currently active level (held
constant from formation until broken); `EQH_BROKEN`/`EQL_BROKEN` fire when
close crosses through it. Not a duplicate of `zigzag`/`swing_equilibrium`
(neither does tolerance-based level CLUSTERING across separate pivots).

Source: TradingView community indicator "Equal Highs & Equal Lows" (see
`datastore/source/pine_triage.csv` for the exact attribution row) (ported
into AwakenAnalytics/Backtesting TVPTA-3, 2026-08-04; MPL-2.0 per
TradingView's open-source publication convention). Pivot confirmation
uses Pine's actual `ta.pivothigh`/`ta.pivotlow` tie semantics (strict,
unique extreme -- a genuine tie confirms NEITHER bar), deliberately
DIFFERENT from `swing_equilibrium`'s rightmost-tie-wins rule (that was a
choice specific to `swing_equilibrium`'s own different source). ⚠
Simplified versus the source: the source tracks an unbounded array of
live (unbroken) EQH/EQL levels simultaneously; this port tracks only the
MOST RECENTLY FORMED level of each type at any time (a new level replaces
the previous one in the DataFrame's single EQH_DIST/EQL_DIST column even
if the prior level hasn't broken yet) -- a scoped-down, single-column
form matching this project's "distance to nearest/most relevant level"
convention (`priorday_fib`, `dist_to_res_level`) rather than the source's
full multi-level array, which would need a variable-width output.

Calculation:
    Default Inputs:
        left=5, right=5, tol_mode="atr", atr_length=14, atr_mult=0.10,
        pct_tol=0.05, lookback_pivots=15
    Confirmed pivot highs/lows via strict-unique-extreme rule (see
        `_confirm_strict_pivots`).
    tolerance = ATR(atr_length)*atr_mult, or close*pct_tol/100
    On each new confirmed pivot, scan the last `lookback_pivots` prior
        pivots of the SAME type (most recent first); the first one found
        within `tolerance` forms a level at max/min(new, prior).
    EQH/EQL = 1 on the formation bar
    EQH_DIST/EQL_DIST = (close - level) / close * 100, held until broken
    EQH_BROKEN/EQL_BROKEN = 1 on the bar close first crosses the level

Args:
    high (pd.Series): Series of 'high's
    low (pd.Series): Series of 'low's
    close (pd.Series): Series of 'close's
    left (int): Bars before the candidate pivot. Default: 5
    right (int): Bars after the candidate pivot (confirmation lag).
        Default: 5
    tol_mode (str): "atr" or "percent". Default: "atr"
    atr_length (int): ATR period (tol_mode="atr"). Default: 14
    atr_mult (float): ATR multiplier (tol_mode="atr"). Default: 0.10
    pct_tol (float): % tolerance (tol_mode="percent"). Default: 0.05
    lookback_pivots (int): Prior pivots of each type kept for comparison.
        Default: 15
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.DataFrame: EQH, EQL, EQH_DIST, EQL_DIST, EQH_BROKEN, EQL_BROKEN.
"""
