# -*- coding: utf-8 -*-
"""Volatility Stop, dynamic-length alternate (VSTOP2).

PINEBI-1b port of ``vStop2`` from TradingView's ``ta`` library, publication
``RA2vGpkA``, lines 799-817.

    Mozilla Public License 2.0
    (c) TradingView

Gate A oracle: identical to ``vStop`` except for ONE line, which is the entire
reason the library ships both::

    export vStop (series float source, simple int   atrLength, series float atrFactor = 1) =>
        float atrM = nz(ta.atr(atrLength) * atrFactor, ta.tr(true))
    export vStop2(series float source, series float atrLength, series float atrFactor = 1) =>
        float atrM = nz(atr2(atrLength) * atrFactor, ta.tr(true))

`vStop`'s `atrLength` is `simple int` -- fixed for the life of the script.
`vStop2`'s is `series float` -- it can change every bar, and it reaches that
through `atr2`, the library's own dynamic-length ATR, which this fork already
ships (PINEBI-1c).

That is the same axis PINEBI-1c measured across its seven kept alternates: the
sibling raises `ValueError: The truth value of a Series is ambiguous` on a
per-bar length, and the alternate takes it.  The stateful recursion itself is
NOT duplicated here -- it is imported from ``vstop`` -- because two
transcriptions of one stateful loop drift, which is the FVGENG rule.

The column name carries a `dyn` token when the length is per-bar, matching the
convention PINEBI-1c set for `ema2`/`atr2`/`supertrend2`, so a mined rule can
tell a fixed-length stop from a dynamic one by the string alone.
"""
from numpy import asarray, isfinite, nan
from pandas import DataFrame, Series
from pandas_ta.trend.vstop import _run
from pandas_ta.volatility.true_range import true_range
from pandas_ta.utils import get_offset, verify_series


def _dynamic_wilder(tr, lengths):
    """Wilder's RMA with a per-bar length: r[i] = r[i-1] + (tr[i] - r[i-1])/n."""
    x = tr.to_numpy(dtype=float)
    n = asarray(lengths, dtype=float)
    out = [nan] * len(x)
    prev = nan
    for i in range(len(x)):
        ni = n[i]
        if not isfinite(x[i]) or not isfinite(ni) or ni < 1:
            out[i] = prev
            continue
        prev = x[i] if not isfinite(prev) else prev + (x[i] - prev) / ni
        out[i] = prev
    return Series(out, index=tr.index)


def vstop2(high, low, close, length=None, factor=None, offset=None, **kwargs):
    """Indicator: Volatility Stop, dynamic length (VSTOP2)"""
    # Validate Arguments
    factor = float(factor) if factor and factor > 0 else 1.0
    high = verify_series(high)
    low = verify_series(low)
    close = verify_series(close)
    offset = get_offset(offset)

    if high is None or low is None or close is None: return

    if isinstance(length, Series):
        lengths = length.reindex(close.index).to_numpy(dtype=float)
        finite = lengths[isfinite(lengths)]
        if finite.size == 0: return
        token = "dyn%d-%d" % (int(finite.min()), int(finite.max()))
    else:
        n = int(length) if length and length > 0 else 20
        lengths = [float(n)] * len(close)
        token = str(n)

    # Calculate Result
    tr = true_range(high=high, low=low, close=close)
    atr = _dynamic_wilder(tr, lengths)
    atrm = (atr * factor).fillna(tr)

    stop_arr, trend_arr = _run(close.to_numpy(dtype=float),
                               atrm.to_numpy(dtype=float))
    level = Series(stop_arr, index=close.index)
    trend = Series(trend_arr.astype(float), index=close.index)

    raw = kwargs.pop("raw", False)
    if raw:
        out = level
        out.name = f"VSTOP2_{token}_{factor}"
        out.category = "trend"
        return out

    dist = 100.0 * (close - level) / level.where(level != 0)
    dist.name = f"VSTOP2_DIST_PCT_{token}_{factor}"
    trend.name = f"VSTOP2_TREND_{token}_{factor}"

    # Offset
    if offset != 0:
        dist = dist.shift(offset)
        trend = trend.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        dist.fillna(kwargs["fillna"], inplace=True)
        trend.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        dist.fillna(method=kwargs["fill_method"], inplace=True)
        trend.fillna(method=kwargs["fill_method"], inplace=True)

    dist.category = trend.category = "trend"
    df = DataFrame({dist.name: dist, trend.name: trend})
    df.name = f"VSTOP2_{token}_{factor}"
    df.category = "trend"
    return df


vstop2.__doc__ = """Volatility Stop, dynamic length (VSTOP2)

`vstop` with a per-bar ATR length. Hand it a Series and the stop's ATR window
changes bar by bar — useful when the window is itself driven by a regime or
volatility measure. Hand it an int and it behaves like `vstop`.

The sibling `vstop` raises `ValueError: The truth value of a Series is
ambiguous` on a per-bar length; this is the alternate that takes it, the same
relationship `ema2`/`atr2`/`supertrend2` have with their siblings.

The column name carries a `dyn{min}-{max}` token when the length is per-bar,
so a fixed-length stop and a dynamic one are distinguishable by name.

Sources:
    https://www.tradingview.com/script/RA2vGpkA/ (MPL-2.0, (c) TradingView)

Args:
    high (pd.Series): Series of 'high's
    low (pd.Series): Series of 'low's
    close (pd.Series): Series of 'close's
    length (int | pd.Series): ATR period, fixed or per-bar. Default: 20
    factor (float): ATR multiplier. Default: 1.0
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    raw (bool): Return the stop level instead. Default: False
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.DataFrame: VSTOP2_DIST_PCT_{token}_{factor}, VSTOP2_TREND_{token}_{factor}
"""
