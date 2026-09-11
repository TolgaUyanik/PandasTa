# -*- coding: utf-8 -*-
"""Bill Williams' Market Facilitation Index, in scale-free form (MFI_BW_SF).

ALTPORT-2 port of the *question* asked by
``tti.indicators.MarketFacilitationIndex`` from
https://github.com/vsaveris/trading-technical-indicators (MIT License,
Copyright (c) 2020 Vasileios Saveris).  The upstream repository is NOT vendored
here.

⚠ tti is NOT the Gate A oracle for the shipped column.  tti returns
``(high - low) / volume`` and rounds it to 10 decimals; the shipped form
multiplies volume straight back out, so the only upstream contribution is
``high - low``, which is raw OHLC.  ALTPORT-1 measured the upstream call
decorative (tti `mfi` vs a local `(h-l)/volume`: max |d| 4.99908e-11, the
`.round(10)` half-ulp floor).  Gate A therefore goes to Bill Williams'
definition directly, and `raw=True` exposes it for that check.

Name collision, deliberate: `pandas_ta.mfi` is the Money Flow Index, an
entirely different indicator.  This function is `bw_mfi` and its column is
`MFI_BW_SF_<length>`.
"""
from pandas_ta.overlap.sma import sma
from pandas_ta.utils import get_offset, verify_series


def bw_mfi(high, low, close, volume, length=None, raw=False, offset=None, **kwargs):
    """Indicator: Bill Williams Market Facilitation Index, scale-free (MFI_BW_SF)"""
    # Validate Arguments
    length = int(length) if length and length > 0 else 20
    high = verify_series(high, length)
    low = verify_series(low, length)
    close = verify_series(close, length)
    volume = verify_series(volume, length)
    offset = get_offset(offset)

    if high is None or low is None or close is None or volume is None: return

    # Calculate Result
    if raw:
        # Bill Williams' definition verbatim -- a PRICE PER SHARE, not a
        # feature.  Registered nowhere; here so Gate A has an oracle.
        result = (high - low) / volume
        result.name = f"MFI_BW_RAW_{length}"
    else:
        avg_volume = sma(volume, length=length)
        rel_volume = volume / avg_volume
        result = ((high - low) / close) / rel_volume
        result.name = f"MFI_BW_SF_{length}"

    # Offset
    if offset != 0:
        result = result.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        result.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        result.fillna(method=kwargs["fill_method"], inplace=True)

    result.category = "volume"

    return result


bw_mfi.__doc__ = \
"""Bill Williams' Market Facilitation Index, scale-free (MFI_BW_SF)

How much price movement does one unit of volume buy?  Price impact, or
liquidity efficiency.  `eom` is the nearest shipped idea but is directional and
ships as a price level; `cmf` measures accumulation, not efficiency.

Bill Williams' raw index is `(high - low) / volume`, which is neither
price-scale-free nor volume-scale-free -- it is TL per share, and it doubles
when the share count halves.  The shipped column is the double ratio

    MFI_BW_SF = ((high - low) / close) / (volume / SMA(volume, length))

-- today's range as a fraction of price, per unit of RELATIVE volume.  Both
divisions are the pre-engineered relations the ML feature contract asks for: a
tree cannot form `a / b` on its own.

Scale-free: Gate D measured bit-identical (max |delta| == 0.0) under
OHLC x8 and x64, and unchanged under volume x8/x64 (the volume ratio cancels).

Gate E (ALTPORT-1, 89 BIST daily frames): max |Spearman rho| **0.536816**
against `vol_at_low_ratio`, n = 394,399; per-frame median 0.537448, 0.0% of
frames >= 0.90.  Disclosed: recomputed on prices x1e5 (dropping tti's
fixed-decimal floor) the same pair reads -0.573380 -- the largest quantisation
move of the nine ALTPORT-1 candidates.  Still SHIP.

Sources:
    Bill Williams, "Trading Chaos".
    Question sourced from trading-technical-indicators (MIT),
    `tti/indicators/_market_facilitation_index.py`.

Calculation:
    Default Inputs:
        length=20
    SMA = Simple Moving Average
    raw=True :  MFI_BW_RAW = (high - low) / volume          <- a price level
    default  :  MFI_BW_SF  = ((high - low) / close)
                             / (volume / SMA(volume, length))

Args:
    high (pd.Series): Series of 'high's
    low (pd.Series): Series of 'low's
    close (pd.Series): Series of 'close's
    volume (pd.Series): Series of 'volume's
    length (int): The relative-volume average period. Default: 20
    raw (bool): Return Bill Williams' unscaled (high-low)/volume. Default: False
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.Series: New feature generated.
"""
