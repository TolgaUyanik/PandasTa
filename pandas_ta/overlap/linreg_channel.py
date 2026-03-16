# -*- coding: utf-8 -*-
import numpy as np
from pandas import DataFrame
from pandas_ta.utils import get_offset, verify_series


def linreg_channel(close, length=None, offset=None, **kwargs):
    """Indicator: Linear Regression Channel"""
    # Validate Arguments
    length = int(length) if length and length > 0 else 20
    close = verify_series(close, length)
    offset = get_offset(offset)

    if close is None: return

    # Calculate Result
    def _linreg_stats(arr):
        n = len(arr)
        x = np.arange(n, dtype=float)
        if np.isnan(arr).any():
            return np.nan, np.nan, np.nan
        x_mean = x.mean()
        a_mean = arr.mean()
        ss_xx = ((x - x_mean) ** 2).sum()
        ss_xy = ((x - x_mean) * (arr - a_mean)).sum()
        slope = ss_xy / ss_xx if ss_xx != 0 else 0.0
        intercept = a_mean - slope * x_mean
        fitted = intercept + slope * x
        residuals = arr - fitted
        std_err = np.sqrt((residuals ** 2).sum() / max(n - 1, 1))
        return slope, fitted[-1], std_err

    close_arr = close.to_numpy(dtype=float)
    slopes, values, devs = [], [], []
    for i in range(len(close_arr)):
        if i < length - 1:
            slopes.append(np.nan)
            values.append(np.nan)
            devs.append(np.nan)
        else:
            s, v, d = _linreg_stats(close_arr[i - length + 1: i + 1])
            slopes.append(s)
            values.append(v)
            devs.append(d)

    slopes = np.array(slopes)
    values = np.array(values)
    devs = np.array(devs)

    linreg_slope = np.where(close_arr != 0, slopes / close_arr * 100, np.nan)

    # Prepare DataFrame
    df = DataFrame({
        "LINREG_SLOPE":   linreg_slope,
        "LINREG_VALUE":   values,
        "LINREG_DEV":     devs,
        "LINREG_UPPER_1": values + devs,
        "LINREG_LOWER_1": values - devs,
        "LINREG_UPPER_2": values + 2 * devs,
        "LINREG_LOWER_2": values - 2 * devs,
    }, index=close.index)

    df.name = f"LINREGCH_{length}"
    df.category = "overlap"

    if offset != 0:
        df = df.shift(offset)

    if "fillna" in kwargs:
        df.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        df.fillna(method=kwargs["fill_method"], inplace=True)

    return df


linreg_channel.__doc__ = \
"""Linear Regression Channel (linreg_channel)

Computes a rolling linear regression over `length` bars and returns the
fitted value at the last bar together with ±1 and ±2 standard-deviation
bands.  Also returns the normalised slope (% of close per bar).

Sources:
    AwakenAnalytics custom indicator (indicator_engine.py)

Calculation:
    Default Inputs:
        length=20
    For each window of `length` bars:
        Fit OLS: close ~ x  (x = 0,1,...,n-1)
        LINREG_VALUE   = fitted value at bar n-1
        LINREG_DEV     = std(residuals)
        LINREG_SLOPE   = slope / close * 100  (normalised %)
        LINREG_UPPER_1 = LINREG_VALUE + LINREG_DEV
        LINREG_LOWER_1 = LINREG_VALUE - LINREG_DEV
        LINREG_UPPER_2 = LINREG_VALUE + 2*LINREG_DEV
        LINREG_LOWER_2 = LINREG_VALUE - 2*LINREG_DEV

Args:
    close (pd.Series): Series of 'close's
    length (int): Rolling window. Default: 20
    offset (int): Periods to offset the result. Default: 0

Returns:
    pd.DataFrame: LINREG_SLOPE, LINREG_VALUE, LINREG_DEV,
                  LINREG_UPPER_1, LINREG_LOWER_1,
                  LINREG_UPPER_2, LINREG_LOWER_2
"""
