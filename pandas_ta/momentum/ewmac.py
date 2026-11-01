# -*- coding: utf-8 -*-
from pandas import DataFrame
from pandas_ta.overlap.ema import ema
from pandas_ta.utils import get_offset, verify_series

PAIRS = ((2, 8), (4, 16), (8, 32), (16, 64), (32, 128), (64, 256))


def ewmac(close, vol_length=None, offset=None, **kwargs):
    """Indicator: Exponentially Weighted Moving Average Crossover (EWMAC)"""
    # Validate Arguments
    vol_length = int(vol_length) if vol_length and vol_length > 0 else 35
    close = verify_series(close, PAIRS[-1][1] + 1)
    offset = get_offset(offset)

    if close is None: return

    # Calculate Result: one EWMA-vol-normalised crossover per Carver pair.
    # sigma is ONE shared estimate (not re-derived per pair): Carver's own
    # trading-rule family normalises every speed by the same recent
    # volatility of price changes, not by a window tied to each pair's own
    # length. See docs/EwmacMeasured.md for the Gate A reasoning.
    sigma = close.diff().ewm(span=vol_length, adjust=False).std()

    data = {}
    for fast, slow in PAIRS:
        fastma = ema(close, length=fast, sma=False)
        slowma = ema(close, length=slow, sma=False)
        col = (fastma - slowma) / sigma
        col.name = f"EWMAC_{fast}_{slow}_{vol_length}"
        data[col.name] = col

    df = DataFrame(data)

    # Offset
    if offset != 0:
        df = df.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        df.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        df.fillna(method=kwargs["fill_method"], inplace=True)

    # Name and Categorize it
    df.name = f"EWMAC_{vol_length}"
    df.category = "momentum"

    return df


ewmac.__doc__ = \
"""Exponentially Weighted Moving Average Crossover (EWMAC)

Carver's volatility-normalised EMA crossover (Carver 2015, *Systematic
Trading*, Appendix B *Trading Rules*): the difference of a fast and a slow
EMA of `close`, divided by the recent standard deviation of daily price
changes (in price points, not percentage points -- the appendix's own
"standard deviation adjustment"). One column per Carver speed pair: 2:8,
4:16, 8:32, 16:64, 32:128, 64:256, with `alpha = 2 / (L + 1)` for each leg
(`ema(..., sma=False)`, no SMA seed, matching Carver's own EWMA convention).

Ships the RAW ratio only -- no forecast scalar, no cap. The issue's own Gate
A note says a tree does not need the scalar; Carver's published scalars
(10.6 down to 1.87) and cap (|forecast| <= 20) are a position-sizing device
for his trading system, not a feature transform, and are not shipped here.

Gate A open question, decided here (no book/web access in this session; most
conservative reading per the issue-solver rules): `sigma` is Carver's EWMA
form, not a simple rolling window, and it is computed ONCE per bar and
shared across all six columns -- not re-derived per pair at the pair's own
span. This matches Carver's own `robust_vol_calc` (one recent-volatility
estimate reused by every trading-rule variation of a given instrument), is
simpler than six separate vol estimates, and is explicitly flagged here as
an ASSUMPTION rather than a page citation. `vol_length` (EWMA span for
`sigma`) defaults to 35, the span value Carver's own open-sourced
`pysystemtrade` uses for `robust_vol_calc`; this is recalled, not cited to a
page number, and is documented as a guess the same way `docs/PfeMeasured.md`
flags its own unsourced choices.

Calculation:
    Default Inputs:
        vol_length=35
    PAIRS = (2,8), (4,16), (8,32), (16,64), (32,128), (64,256)
    sigma = STDEV(DIFF(close, 1), vol_length)      EWMA form, span=vol_length
    For each (fast, slow) in PAIRS:
        EWMAC_{fast}_{slow}_{vol_length} = (EMA(close, fast) - EMA(close, slow)) / sigma

Args:
    close (pd.Series): Series of 'close's
    vol_length (int): EWMA span for the shared volatility estimate. Default: 35
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.DataFrame: six EWMAC_<fast>_<slow>_<vol_length> columns, scale-free.
"""
