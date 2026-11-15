# -*- coding: utf-8 -*-
from pandas import DataFrame
from pandas_ta.overlap.ema import ema
from pandas_ta.utils import get_offset, verify_series

PAIRS = ((64, 256),)
# Gate E (issue #29, measured 2026-11-01, see docs/EwmacMeasured.md) STRUCK the
# other five Carver pairs -- (2,8) vs pgo 0.9739, (4,16) vs smi_SMI_5_20_5
# 0.9829, (8,32) vs tsi 0.9945, (16,64) vs ICHI_CHIKOU_VS_CLOUD 0.9175,
# (32,128) vs Dist_to_SMA_200_pct 0.9298, all pooled |rho| >= 0.90 on the 89
# BIST frames -- and they were removed. Only 64:256 survived, at DISCLOSE_GAP
# (0.8744 vs SMA_200_Slope_pct).


def ewmac(close, vol_length=None, offset=None, **kwargs):
    """Indicator: Exponentially Weighted Moving Average Crossover (EWMAC)"""
    # Validate Arguments
    vol_length = int(vol_length) if vol_length and vol_length > 0 else 35
    close = verify_series(close, PAIRS[-1][1] + 1)
    offset = get_offset(offset)

    if close is None: return

    # Calculate Result: EWMA-vol-normalised crossover, Carver's 64:256 pair
    # (the other five pairs were Gate E STRUCK and removed; see
    # docs/EwmacMeasured.md). sigma is Carver's own `robust_vol_calc` form,
    # not a window tied to the pair's own length -- the Gate A reasoning.
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
"standard deviation adjustment"), with `alpha = 2 / (L + 1)` for each leg
(`ema(..., sma=False)`, no SMA seed, matching Carver's own EWMA convention).

Carver gives six speed pairs: 2:8, 4:16, 8:32, 16:64, 32:128, 64:256. Gate E
(issue #29, measured 2026-11-01, `docs/EwmacMeasured.md`) STRUCK the first
five against existing engine columns (pooled |rho| 0.9175-0.9945 vs `pgo`,
`smi_SMI_5_20_5`, `tsi`, `ICHI_CHIKOU_VS_CLOUD`, `Dist_to_SMA_200_pct`) and
they were removed. Only **64:256** ships, at DISCLOSE_GAP (0.8744 vs
`SMA_200_Slope_pct`) -- the slow pair the issue itself flagged as having the
best chance of adding information, because the engine has no MACD-family
column that slow.

Ships the RAW ratio only -- no forecast scalar, no cap. The issue's own Gate
A note says a tree does not need the scalar; Carver's published scalars
(10.6 down to 1.87) and cap (|forecast| <= 20) are a position-sizing device
for his trading system, not a feature transform, and are not shipped here.

Gate A open question, decided here (no book/web access in this session; most
conservative reading per the issue-solver rules): `sigma` is Carver's EWMA
form, not a simple rolling window. This matches Carver's own
`robust_vol_calc` (one recent-volatility estimate reused by every
trading-rule variation of a given instrument) and is explicitly flagged here
as an ASSUMPTION rather than a page citation. `vol_length` (EWMA span for
`sigma`) defaults to 35, the span value Carver's own open-sourced
`pysystemtrade` uses for `robust_vol_calc`; this is recalled, not cited to a
page number, and is documented as a guess the same way `docs/PfeMeasured.md`
flags its own unsourced choices.

Calculation:
    Default Inputs:
        vol_length=35
    PAIRS = (64, 256)
    sigma = STDEV(DIFF(close, 1), vol_length)      EWMA form, span=vol_length
    EWMAC_{fast}_{slow}_{vol_length} = (EMA(close, fast) - EMA(close, slow)) / sigma

Args:
    close (pd.Series): Series of 'close's
    vol_length (int): EWMA span for the shared volatility estimate. Default: 35
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.DataFrame: one EWMAC_64_256_<vol_length> column, scale-free.
"""
