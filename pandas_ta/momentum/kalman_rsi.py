# -*- coding: utf-8 -*-
import numpy as np
from pandas import Series

from pandas_ta.momentum.rsi import rsi
from pandas_ta.utils import get_offset, verify_series


def kalman_rsi(close, length=None, process_noise=None, measurement_noise=None,
                initial_error=None, offset=None, **kwargs):
    """Indicator: Kalman-Filtered RSI (KRSI)"""
    # Validate Arguments
    # MAJOR fix (Fletcher round 1): defaulted to pandas_ta's conventional
    # RSI length (14) without checking the SOURCE script's own default --
    # the Pine source (fU13VFoj-...pine:9) uses length=5. Matching the
    # source's default, not RSI's generic convention, since this indicator
    # is a specific port, not a fresh design.
    length = int(length) if length and length > 0 else 5
    process_noise = float(process_noise) if process_noise and process_noise > 0 else 0.01
    measurement_noise = float(measurement_noise) if measurement_noise and measurement_noise > 0 else 1.0
    initial_error = float(initial_error) if initial_error and initial_error > 0 else 1.0
    close = verify_series(close, length)
    offset = get_offset(offset)

    if close is None: return

    # A scalar Kalman filter (predict/update, no vectorized closed form
    # because the gain is state-dependent bar to bar) smooths `close`
    # BEFORE it feeds RSI -- this is the source's actual novel content;
    # ta.rsi alone is already ours (verified: TVPTA-2 flagged this
    # candidate `dedupe_hit=rsi`, but the dedupe was on the wrong
    # signal -- the file's ONE whitelisted call is ta.rsi, yet the real
    # computation is the Kalman recursion feeding it, exactly the "merely
    # uses ta.rsi inside new logic" case TVPTA-2's own text says is NOT a
    # dedupe hit).
    vals = close.to_numpy(dtype=float)
    n = len(vals)
    kalman_price = np.full(n, np.nan)
    price = vals[0] if n and not np.isnan(vals[0]) else np.nan
    error = initial_error
    for t in range(n):
        c = vals[t]
        if np.isnan(c):
            kalman_price[t] = price
            continue
        predicted_price = price if not np.isnan(price) else c
        predicted_error = error + process_noise
        gain = predicted_error / (predicted_error + measurement_noise)
        price = predicted_price + gain * (c - predicted_price)
        error = (1.0 - gain) * predicted_error
        kalman_price[t] = price

    kalman_price = Series(kalman_price, index=close.index)
    result = rsi(kalman_price, length=length)

    # Offset
    if offset != 0:
        result = result.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        result.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        result.fillna(method=kwargs["fill_method"], inplace=True)

    # Name and Categorize it
    result.name = f"KRSI_{length}"
    result.category = "momentum"

    return result


kalman_rsi.__doc__ = \
"""Kalman-Filtered RSI (KRSI)

RSI computed on a Kalman-filtered (smoothed) close instead of raw close.
The Kalman filter is a simple scalar predict/update recursion (not the
pivot/tie-break class of stateful logic elsewhere in this TVPTA-3 batch --
its gain is state-dependent but has no branching/tie-break ambiguity, so
it carries materially lower correctness risk). Still bounded 0-100 like
plain RSI, no additional scale-free work needed.

Source: TradingView community indicator "Kalman Filter-Optimized RSI" by
markchunwaipaul, https://www.tradingview.com/script/fU13VFoj-Kalman-Filter-Optimized-RSI/
(ported into AwakenAnalytics/Backtesting TVPTA-3, 2026-08-04; MPL-2.0 per
TradingView's open-source publication convention). The source script's
momentum-histogram/zone-fill display logic is not ported (chart styling
only, no additional math).

Calculation:
    Default Inputs:
        length=5, process_noise=0.01, measurement_noise=1.0, initial_error=1.0
    Kalman filter (per bar t):
        predicted_price = kalman_price[t-1]  (or close[t] on the first bar)
        predicted_error = kalman_error[t-1] + process_noise
        gain = predicted_error / (predicted_error + measurement_noise)
        kalman_price[t] = predicted_price + gain * (close[t] - predicted_price)
        kalman_error[t] = (1 - gain) * predicted_error
    KRSI = RSI(kalman_price, length)

Args:
    close (pd.Series): Series of 'close's
    length (int): RSI period. Default: 5 (matches the source Pine
        script's own default, NOT pandas_ta's conventional RSI default of
        14 -- this is a port of a specific published indicator, not a
        fresh design, so its default follows the source)
    process_noise (float): Kalman process noise. Default: 0.01
    measurement_noise (float): Kalman measurement noise. Default: 1.0
    initial_error (float): Kalman initial error estimate. Default: 1.0
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.Series: New feature generated.
"""
