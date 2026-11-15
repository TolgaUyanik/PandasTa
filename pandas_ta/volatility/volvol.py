# -*- coding: utf-8 -*-
from .natr import natr
from pandas_ta.utils import get_offset, verify_series


def volvol(high, low, close, length=None, natr_length=None, mamode=None, offset=None, **kwargs):
    """Indicator: Volatility of Volatility (VOLVOL)"""
    # Validate Arguments
    length = int(length) if length and length > 0 else 20
    natr_length = int(natr_length) if natr_length and natr_length > 0 else 14
    mamode = mamode if isinstance(mamode, str) else "ema"
    high = verify_series(high, length + natr_length)
    low = verify_series(low, length + natr_length)
    close = verify_series(close, length + natr_length)
    offset = get_offset(offset)

    if high is None or low is None or close is None: return

    # Calculate Result
    # NATR is already scale-free (100 * ATR / close), so a plain rolling stdev
    # of it stays scale-free too -- no division is needed the way a
    # coefficient-of-variation form would need one, which would read NaN on a
    # flat-price window where NATR's own mean is 0.
    vol = natr(high=high, low=low, close=close, length=natr_length, mamode=mamode)
    volvol = vol.rolling(length).std()

    # Offset
    if offset != 0:
        volvol = volvol.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        volvol.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        volvol.fillna(method=kwargs["fill_method"], inplace=True)

    # Name and Categorize it
    volvol.name = f"VOLVOL_{length}_{natr_length}"
    volvol.category = "volatility"

    return volvol


volvol.__doc__ = \
"""Volatility of Volatility (VOLVOL)

The rolling standard deviation of a rolling volatility series -- the
vol-of-vol a trader means when a position's own risk is itself unstable.
The volatility series fed into the outer stdev is `natr` (Normalized Average
True Range), already a scale-free (price-ratio) measure of realised
volatility, so VOLVOL inherits scale-freeness without needing the
coefficient-of-variation form the sources mention as an alternative.

Sources:
    Alpha Architect, "Volatility Anomalies: IVOL and Vol-of-Vol"
    Kaufman, Perry J. (2013). "Trading Systems and Methods", 5th ed., ch. 18
    ("Volatility Measurements and Position Sizing") -- defines vol-of-vol as
    the standard deviation of a rolling volatility estimator over a window.
    IVOL itself needs a benchmark regression (same treatment as `beta`) and
    is out of scope.

Calculation:
    Default Inputs:
        length=20, natr_length=14
    NATR = Normalized Average True Range(high, low, close, natr_length)
    VOLVOL = STDEV(NATR, length)  (trailing rolling sample stdev, ddof=1)

Args:
    high (pd.Series): Series of 'high's
    low (pd.Series): Series of 'low's
    close (pd.Series): Series of 'close's
    length (int): The vol-of-vol window. Default: 20
    natr_length (int): The inner NATR window. Default: 14
    mamode (str): NATR's moving average mode. Default: 'ema'
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.Series: New feature, VOLVOL_{length}_{natr_length}, non-negative.
"""
