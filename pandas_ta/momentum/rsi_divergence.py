# -*- coding: utf-8 -*-
import numpy as np
from pandas import DataFrame, Series

from pandas_ta.momentum.rsi import rsi
from pandas_ta.utils import get_offset, verify_series


def _confirm_strict_pivots(series, left, right, is_high):
    """Causal pivot confirmation matching Pine's `ta.pivothigh`/
    `ta.pivotlow` (strict, unique extreme -- a tie confirms neither bar).
    Duplicated from `equal_highs_lows._confirm_strict_pivots` rather than
    cross-imported, matching this package's convention of self-contained
    indicator files.
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
    return Series(out, index=series.index)


def rsi_divergence(high, low, close, rsi_length=None, pivot_left=None, pivot_right=None,
                    min_lookback=None, max_lookback=None, rsi_oversold=None,
                    rsi_overbought=None, offset=None, **kwargs):
    """Indicator: RSI Divergence (RSIDIV)"""
    rsi_length = int(rsi_length) if rsi_length and rsi_length > 0 else 14
    pivot_left = int(pivot_left) if pivot_left and pivot_left > 0 else 4
    pivot_right = int(pivot_right) if pivot_right and pivot_right > 0 else 4
    min_lookback = int(min_lookback) if min_lookback and min_lookback > 0 else 10
    max_lookback = int(max_lookback) if max_lookback and max_lookback > 0 else 40
    rsi_oversold = float(rsi_oversold) if rsi_oversold and rsi_oversold > 0 else 45.0
    rsi_overbought = float(rsi_overbought) if rsi_overbought and rsi_overbought > 0 else 55.0
    high = verify_series(high, pivot_left + pivot_right + 1)
    low = verify_series(low, pivot_left + pivot_right + 1)
    close = verify_series(close, pivot_left + pivot_right + 1)
    offset = get_offset(offset)

    if high is None or low is None or close is None: return

    rsi_val = rsi(close, length=rsi_length)
    if rsi_val is None: return
    pivot_low = _confirm_strict_pivots(low, pivot_left, pivot_right, is_high=False)
    pivot_high = _confirm_strict_pivots(high, pivot_left, pivot_right, is_high=True)

    n = len(close)
    pl_vals = pivot_low.to_numpy(dtype=float)
    ph_vals = pivot_high.to_numpy(dtype=float)
    rsi_vals = rsi_val.to_numpy(dtype=float)

    bull_div = np.zeros(n, dtype=int)
    bear_div = np.zeros(n, dtype=int)

    # Stateful pairwise comparison: each new confirmed pivot is compared
    # only against the IMMEDIATELY PRECEDING pivot of the same type (not
    # a scan over many, matching the source's single `prev_*` variables,
    # updated unconditionally on every new pivot regardless of whether a
    # divergence fired). Bullish: price makes a LOWER low while RSI (read
    # at the pivot's own bar, `pivot_right` bars before the confirmation
    # bar) makes a HIGHER low, within [min_lookback, max_lookback] ACTUAL
    # PIVOT bars apart (not confirmation bars apart) and gated by an
    # RSI-oversold zone at the newer pivot. Bearish is the mirror.
    prev_pl_price = np.nan
    prev_pl_rsi = np.nan
    prev_pl_bar = -1
    prev_ph_price = np.nan
    prev_ph_rsi = np.nan
    prev_ph_bar = -1

    for j in range(n):
        if not np.isnan(pl_vals[j]):
            pivot_bar = j - pivot_right
            cur_rsi = rsi_vals[pivot_bar] if pivot_bar >= 0 else np.nan
            cur_price = pl_vals[j]
            if not np.isnan(prev_pl_price) and not np.isnan(cur_rsi):
                dist = pivot_bar - prev_pl_bar
                if (min_lookback <= dist <= max_lookback) and (cur_rsi <= rsi_oversold):
                    if (cur_price < prev_pl_price) and (cur_rsi > prev_pl_rsi):
                        bull_div[j] = 1
            prev_pl_price = cur_price
            prev_pl_rsi = cur_rsi
            prev_pl_bar = pivot_bar

        if not np.isnan(ph_vals[j]):
            pivot_bar = j - pivot_right
            cur_rsi = rsi_vals[pivot_bar] if pivot_bar >= 0 else np.nan
            cur_price = ph_vals[j]
            if not np.isnan(prev_ph_price) and not np.isnan(cur_rsi):
                dist = pivot_bar - prev_ph_bar
                if (min_lookback <= dist <= max_lookback) and (cur_rsi >= rsi_overbought):
                    if (cur_price > prev_ph_price) and (cur_rsi < prev_ph_rsi):
                        bear_div[j] = 1
            prev_ph_price = cur_price
            prev_ph_rsi = cur_rsi
            prev_ph_bar = pivot_bar

    bull_div = Series(bull_div, index=close.index)
    bear_div = Series(bear_div, index=close.index)

    # Offset
    if offset != 0:
        bull_div = bull_div.shift(offset)
        bear_div = bear_div.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        bull_div.fillna(kwargs["fillna"], inplace=True)
        bear_div.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        bull_div.fillna(method=kwargs["fill_method"], inplace=True)
        bear_div.fillna(method=kwargs["fill_method"], inplace=True)

    _props = f"_{rsi_length}_{pivot_left}_{pivot_right}"
    bull_div.name = f"RSIDIV_BULL{_props}"
    bear_div.name = f"RSIDIV_BEAR{_props}"

    df = DataFrame({bull_div.name: bull_div, bear_div.name: bear_div})
    df.name = f"RSIDIV{_props}"
    df.category = "momentum"

    return df


rsi_divergence.__doc__ = \
"""RSI Divergence (RSIDIV)

Classic RSI/price divergence: a confirmed price pivot low that undercuts
the PRIOR pivot low (a lower low) while RSI at that same pivot bar sits
ABOVE the RSI reading at the prior pivot low (a higher low) -- price and
momentum disagreeing -- fires `RSIDIV_BULL`, gated by an RSI-oversold zone
at the newer pivot and a minimum/maximum bar-distance window between the
two pivots. `RSIDIV_BEAR` is the exact mirror (higher high in price, lower
high in RSI, RSI-overbought gate). Not a duplicate of `rsi` itself (which
this reuses) -- no divergence detector exists anywhere in the catalog.

Source: TradingView community indicator "RSI Divergence Engine v3 [30-40
Bar Window]" (see `datastore/source/pine_triage.csv` for the exact
attribution row) (ported into AwakenAnalytics/Backtesting TVPTA-3,
2026-08-04; MPL-2.0 per TradingView's open-source publication
convention). Only the divergence-detection logic is ported -- the
source's fixed reward:risk SL/TP line drawing and 200-EMA trend-filter
plot are position-management/display, not per-bar indicator math, and
are NOT replicated. ⚠ A second, independently-triaged composite-family
candidate (`IFO3JPL6-RSI-Smart-Divergence`) implements a MEANINGFULLY
DIFFERENT design for the same concept (pivots detected on the RSI series
itself, then the nearby PRICE extreme found via a small search radius
around that RSI pivot, vs. this port's design of pivots detected on PRICE
directly with RSI read at that bar) -- only this (price-pivot) design is
ported, as the more standard/conventional divergence-detector shape;
`IFO3JPL6` is recorded as superseded/dropped in
`datastore/source/pine_candidates_families.csv`, not implemented
separately.

Calculation:
    Default Inputs:
        rsi_length=14, pivot_left=4, pivot_right=4, min_lookback=10,
        max_lookback=40, rsi_oversold=45.0, rsi_overbought=55.0
    rsi = RSI(close, rsi_length)
    Confirmed pivot lows/highs on PRICE via the strict-unique-extreme rule
        (see `_confirm_strict_pivots`; same tie semantics as
        `equal_highs_lows`, deliberately different from
        `swing_equilibrium`'s rightmost-tie-wins rule used for a
        different source).
    On each new confirmed pivot low, compare against the immediately
        PRECEDING pivot low (unconditionally updated on every new pivot,
        not only when a divergence fires):
        dist = (bars between the two ACTUAL pivot bars, not confirmation
            bars)
        RSIDIV_BULL = 1 iff min_lookback <= dist <= max_lookback AND
            rsi_at_new_pivot <= rsi_oversold AND
            new_pivot_price < prev_pivot_price AND
            rsi_at_new_pivot > rsi_at_prev_pivot
    RSIDIV_BEAR mirrors this over pivot highs / rsi_overbought.

Args:
    high (pd.Series): Series of 'high's
    low (pd.Series): Series of 'low's
    close (pd.Series): Series of 'close's
    rsi_length (int): RSI period. Default: 14
    pivot_left (int): Bars before the candidate pivot. Default: 4
    pivot_right (int): Bars after the candidate pivot (confirmation lag).
        Default: 4
    min_lookback (int): Minimum bars between the two compared pivots.
        Default: 10
    max_lookback (int): Maximum bars between the two compared pivots.
        Default: 40
    rsi_oversold (float): RSI must be at/below this at the newer pivot low
        for a bullish divergence to qualify. Default: 45.0
    rsi_overbought (float): RSI must be at/above this at the newer pivot
        high for a bearish divergence to qualify. Default: 55.0
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.DataFrame: RSIDIV_BULL, RSIDIV_BEAR columns.
"""
