# -*- coding: utf-8 -*-
from pandas_ta import RATE
from pandas_ta.utils import get_offset, verify_series


def seas(close, length=None, years=None, offset=None, **kwargs):
    """Indicator: Annual-lag Seasonality (SEAS)"""
    # Validate Arguments
    length = int(length) if length and int(length) > 0 else 21
    years = int(years) if years and int(years) > 0 else 1
    year_bars = RATE["TRADING_DAYS_PER_YEAR"]
    if length > year_bars:
        raise ValueError(
            f"length ({length}) must be <= {year_bars}: at years=1 a longer "
            "window would read a bar after T"
        )
    close = verify_series(close, years * year_bars + 1)
    offset = get_offset(offset)

    if close is None: return

    # Calculate Result
    total = 0
    for y in range(1, years + 1):
        lag = y * year_bars
        total = total + (close.shift(lag - length) / close.shift(lag) - 1)
    seas = total / years

    # Offset
    if offset != 0:
        seas = seas.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        seas.fillna(kwargs["fillna"], inplace=True)

    # Name and Categorize it
    seas.name = f"SEAS_{length}_{years}"
    seas.category = "performance"

    return seas


seas.__doc__ = \
"""Annual-lag Seasonality (SEAS)

Heston-Sadka annual-lag seasonality: the return over the next `length` bars,
measured `years` ago, one trading year (252 bars) at a time, averaged.

Source: Quantpedia strategy 0125 "12 Month Cycle in Cross-Section of Stocks
Returns" (SSRN 687022): "grouped ... according to their performance in one
month one year ago". Flirting with Models, Otto van Hemert "Seasonality
Everywhere" reports lags up to 12 months predicting next-month returns with
a positive sign (T3 support). PandasTa issue #27.

Bar-count year, not a calendar one: `years=1` reads bar `T - 252` exactly,
never a date-matched trading day, so BIST holidays shift the window by a
handful of bars. A `DatetimeIndex`-anchored version is not built here
(smaller scope). `years` defaults to 1 (Quantpedia's own version); the
issue's `years=5` alternative is available as a parameter, not the default.

Causal: bar T reads close[T - 252*y + length] and close[T - 252*y], both
<= T whenever length <= 252*y; enforced for y=1 by rejecting
`length > 252`. Scale-free: each r_y is a price ratio minus one, so a
constant price factor cancels; bit-identical under x8 and x64. Warm-up is
exactly `252*years` bars: every r_y shares the same NaN region in its first
252 bars, and summing them propagates NaN, so SEAS is NaN until the last
(`years`-th) term clears its own warm-up.

Calculation:
    Default Inputs:
        length=21, years=1
    r_y = close[T - 252*y + length] / close[T - 252*y] - 1,  y = 1..years
    SEAS = mean(r_1, ..., r_years)

Args:
    close (pd.Series): Series of 'close's
    length (int): Bars in the forward window, h in the issue. Default: 21
    years (int): Number of annual lags to average, Y in the issue. Default: 1
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)

Returns:
    pd.Series: SEAS_{length}_{years}
"""
