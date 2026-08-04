# -*- coding: utf-8 -*-
import numpy as np
from pandas import DataFrame, Series

from pandas_ta.volatility.atr import atr
from pandas_ta.utils import get_offset, verify_series


def nadaraya_watson_envelope(high, low, close, lookback=None, h=None, r=None,
                              atr_length=None, atr_mult=None, offset=None, **kwargs):
    """Indicator: Nadaraya-Watson Rational-Quadratic Kernel Envelope (NWE)"""
    lookback = int(lookback) if lookback and lookback > 0 else 200
    h = float(h) if h and h > 0 else 8.0
    r = float(r) if r and r > 0 else 8.0
    atr_length = int(atr_length) if atr_length and atr_length > 0 else 14
    atr_mult = float(atr_mult) if atr_mult and atr_mult > 0 else 2.0
    high = verify_series(high, lookback + 1)
    low = verify_series(low, lookback + 1)
    close = verify_series(close, lookback + 1)
    offset = get_offset(offset)

    if high is None or low is None or close is None: return

    # Rational-quadratic kernel weight for a bar `i` positions back from
    # "now": w_i = (1 + i^2 / (2*h^2*r))^-r. This is a WEIGHTED MOVING
    # AVERAGE with a specific, well-known kernel shape (heavier tails than
    # a Gaussian, controlled by r) -- non-repainting because the weights
    # only ever look backward (i=0..lookback, all bars at or before the
    # current one). `w[::-1]` reorders the (i=0..lookback) weights to
    # match a chronological rolling window (oldest first, current last).
    i = np.arange(lookback + 1, dtype=float)
    weights = (1.0 + (i ** 2) / (2.0 * h * h * r)) ** (-r)
    weights_chrono = weights[::-1]
    weight_sum = weights.sum()

    window = lookback + 1
    values = close.to_numpy(dtype=float)
    n = len(values)
    nw_mid = np.full(n, np.nan)
    for end in range(window - 1, n):
        segment = values[end - window + 1: end + 1]
        nw_mid[end] = np.dot(segment, weights_chrono) / weight_sum

    nw_mid = Series(nw_mid, index=close.index)
    atr_val = atr(high, low, close, length=atr_length)

    dist_mid_pct = (close - nw_mid) / close * 100
    dist_upper_pct = (close - (nw_mid + atr_val * atr_mult)) / close * 100
    dist_lower_pct = (close - (nw_mid - atr_val * atr_mult)) / close * 100
    slope = nw_mid.diff()

    # Offset
    if offset != 0:
        dist_mid_pct = dist_mid_pct.shift(offset)
        dist_upper_pct = dist_upper_pct.shift(offset)
        dist_lower_pct = dist_lower_pct.shift(offset)
        slope = slope.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        dist_mid_pct.fillna(kwargs["fillna"], inplace=True)
        dist_upper_pct.fillna(kwargs["fillna"], inplace=True)
        dist_lower_pct.fillna(kwargs["fillna"], inplace=True)
        slope.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        dist_mid_pct.fillna(method=kwargs["fill_method"], inplace=True)
        dist_upper_pct.fillna(method=kwargs["fill_method"], inplace=True)
        dist_lower_pct.fillna(method=kwargs["fill_method"], inplace=True)
        slope.fillna(method=kwargs["fill_method"], inplace=True)

    _props = f"_{lookback}_{h}_{r}"
    dist_mid_pct.name = f"NWE_MID{_props}"
    dist_upper_pct.name = f"NWE_UPPER{_props}"
    dist_lower_pct.name = f"NWE_LOWER{_props}"
    slope.name = f"NWE_SLOPE{_props}"

    df = DataFrame({
        dist_mid_pct.name: dist_mid_pct,
        dist_upper_pct.name: dist_upper_pct,
        dist_lower_pct.name: dist_lower_pct,
        slope.name: slope,
    })
    df.name = f"NWE{_props}"
    df.category = "overlap"

    return df


nadaraya_watson_envelope.__doc__ = \
"""Nadaraya-Watson Rational-Quadratic Kernel Envelope (NWE)

A non-repainting Nadaraya-Watson kernel regression: each bar's estimate is
a WEIGHTED average of itself and the `lookback` bars before it, using a
rational-quadratic kernel weight `w_i = (1 + i^2/(2*h^2*r))^-r` for a bar
`i` positions back -- heavier-tailed than a Gaussian kernel, with `r`
controlling how quickly the tail decays. Distinct from every existing MA
in the catalog (`sma`/`ema`/`hma`/`kama`/...): none of them use this
specific kernel weighting. ATR-scaled upper/lower bands around it form an
envelope. All outputs are scale-free % distance from close (raw levels
are not exposed, matching this project's distance-form convention).

Source: TradingView community indicator "ConfluX" (Nadaraya-Watson +
Money Flow Index confluence scorer) (see `datastore/source/pine_triage.csv`
for the exact attribution row) (ported into AwakenAnalytics/Backtesting
TVPTA-3, 2026-08-04; MPL-2.0 per TradingView's open-source publication
convention). Only the kernel-regression envelope itself is ported -- the
source's MFI confluence scoring (duplicate of the existing `mfi`), volume-
spike detection (duplicate of `zscore` applied to volume), and the info-
table/marker UI are NOT replicated. The same kernel technique was also
found independently reimplemented (as `gaussMA`) in another composite-
family candidate this batch, corroborating it as a genuinely wanted,
non-duplicate primitive.

Calculation:
    Default Inputs:
        lookback=200, h=8.0 (bandwidth), r=8.0 (relative weighting),
        atr_length=14, atr_mult=2.0
    w_i = (1 + i^2 / (2*h^2*r))^-r, for i = 0..lookback (0 = current bar)
    nw_mid = sum(close[i] * w_i for i in 0..lookback) / sum(w_i)
    NWE_MID   = (close - nw_mid) / close * 100
    NWE_UPPER = (close - (nw_mid + ATR(atr_length)*atr_mult)) / close * 100
    NWE_LOWER = (close - (nw_mid - ATR(atr_length)*atr_mult)) / close * 100
    NWE_SLOPE = nw_mid.diff()  (raw, NOT scale-free -- a bar-over-bar
        change in a price-scale quantity; consumers wanting a scale-free
        slope should divide by close themselves)

Args:
    high (pd.Series): Series of 'high's
    low (pd.Series): Series of 'low's
    close (pd.Series): Series of 'close's
    lookback (int): Bars each side of the kernel window (weights computed
        for the current bar plus this many prior bars). Default: 200
    h (float): Kernel bandwidth -- higher is smoother. Default: 8.0
    r (float): Relative weighting factor -- higher tightens the fit.
        Default: 8.0
    atr_length (int): ATR period for the envelope bands. Default: 14
    atr_mult (float): ATR multiple for the envelope bands. Default: 2.0
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.DataFrame: NWE_MID, NWE_UPPER, NWE_LOWER, NWE_SLOPE columns.
"""
