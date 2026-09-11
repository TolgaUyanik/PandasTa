# -*- coding: utf-8 -*-
"""Volatility Stop (VSTOP).

PINEBI-1b port of ``vStop`` from TradingView's ``ta`` library, publication
``RA2vGpkA``, lines 773-791.

    Mozilla Public License 2.0
    (c) TradingView

Gate A oracle, transcribed from the source::

    export vStop(series float source, simple int atrLength, series float atrFactor = 1) =>
        float src  = nz(source, close)
        float atrM = nz(ta.atr(atrLength) * atrFactor, ta.tr(true))
        var bool  trendUp = true
        var float max     = src
        var float min     = src
        var float stop    = 0.0
        max     := math.max(max, src)
        min     := math.min(min, src)
        stop    := nz(trendUp ? math.max(stop, max - atrM) : math.min(stop, min + atrM), src)
        trendUp := src - stop >= 0.0
        if trendUp != trendUp[1]
            max  := src
            min  := src
            stop := trendUp ? max - atrM : min + atrM
        [stop, trendUp]

WHAT MAKES THIS EASY TO GET WRONG
----------------------------------
* `max`/`min`/`stop`/`trendUp` are Pine `var`s: initialised ONCE and carried
  across bars. They are not rolling windows. A rolling `max` would make the
  stop ratchet back down, which is precisely what a trailing stop must not do.
* The reset block runs AFTER `trendUp` is recomputed and compares against
  `trendUp[1]`, the PREVIOUS bar's value. So on a flip the extremes reset to
  the current source and the stop is placed one ATR away immediately, rather
  than inheriting the old trend's extreme.
* `ta.atr` is Wilder smoothing, so the port uses `wilder_rma` over true range,
  not this fork's `rma` (`adjust=True`, a different filter — PINEBI-1c
  measured the divergence).

The stop itself is a PRICE LEVEL and therefore not an ML feature. The shipped
columns are the percent distance from close to the stop, and the trend flag,
which is already scale-free. `raw=True` returns the level for plotting.
"""
from numpy import bool_, isfinite, nan, zeros
from pandas import DataFrame
from pandas_ta.volatility.true_range import true_range
from pandas_ta.overlap.wilder_rma import wilder_rma
from pandas_ta.utils import get_offset, verify_series


def _run(src, atrm):
    """Pine's stateful loop, one bar at a time. Returns (stop, trend_up)."""
    n = len(src)
    stop_out = zeros(n)
    trend_out = zeros(n, dtype=bool_)
    trend_up = True
    mx = mn = nan
    stop = 0.0
    prev_trend = True
    for i in range(n):
        s, a = src[i], atrm[i]
        if not isfinite(s) or not isfinite(a):
            stop_out[i] = nan
            trend_out[i] = trend_up
            continue
        mx = s if not isfinite(mx) else max(mx, s)
        mn = s if not isfinite(mn) else min(mn, s)
        cand = max(stop, mx - a) if trend_up else min(stop, mn + a)
        stop = cand if isfinite(cand) else s
        trend_up = (s - stop) >= 0.0
        if trend_up != prev_trend:
            mx = mn = s
            stop = (mx - a) if trend_up else (mn + a)
        prev_trend = trend_up
        stop_out[i] = stop
        trend_out[i] = trend_up
    return stop_out, trend_out


def vstop(high, low, close, length=None, factor=None, offset=None, **kwargs):
    """Indicator: Volatility Stop (VSTOP)"""
    # Validate Arguments
    length = int(length) if length and length > 0 else 20
    factor = float(factor) if factor and factor > 0 else 1.0
    high = verify_series(high, length)
    low = verify_series(low, length)
    close = verify_series(close, length)
    offset = get_offset(offset)

    if high is None or low is None or close is None: return

    # Calculate Result
    tr = true_range(high=high, low=low, close=close)
    atr = wilder_rma(tr, length=length)
    if atr is None: return
    # Pine's nz(atr * factor, tr(true)): before the ATR has warmed up it falls
    # back to the bar's own true range rather than to 0.
    atrm = (atr * factor).fillna(tr)

    stop_arr, trend_arr = _run(close.to_numpy(dtype=float),
                               atrm.to_numpy(dtype=float))
    level = close.__class__(stop_arr, index=close.index)
    trend = close.__class__(trend_arr.astype(float), index=close.index)

    raw = kwargs.pop("raw", False)
    if raw:
        out = level
        out.name = f"VSTOP_{length}_{factor}"
        out.category = "trend"
        return out

    dist = 100.0 * (close - level) / level.where(level != 0)
    dist.name = f"VSTOP_DIST_PCT_{length}_{factor}"
    trend.name = f"VSTOP_TREND_{length}_{factor}"

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
    df.name = f"VSTOP_{length}_{factor}"
    df.category = "trend"
    return df


vstop.__doc__ = """Volatility Stop (VSTOP)

An ATR-distance trailing stop with a trend flag. In an uptrend the stop
ratchets up behind the running maximum and never falls; when price crosses it
the trend flips, the extremes reset, and the stop is re-placed one ATR the
other side.

DEFAULT OUTPUT IS THE PERCENT DISTANCE plus the trend flag — the stop level
itself is a price and therefore not an ML feature. `raw=True` returns the
level.

Sources:
    https://www.tradingview.com/script/RA2vGpkA/ (MPL-2.0, (c) TradingView)

Calculation:
    Default Inputs:
        length=20, factor=1.0

    atrM = wilder_rma(true_range, length) * factor
    (stateful; see the module docstring for the exact recursion)
    VSTOP_DIST_PCT = 100 * (close - stop) / stop
    VSTOP_TREND    = 1.0 while trending up, 0.0 otherwise

Args:
    high (pd.Series): Series of 'high's
    low (pd.Series): Series of 'low's
    close (pd.Series): Series of 'close's
    length (int): ATR period. Default: 20
    factor (float): ATR multiplier. Default: 1.0
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    raw (bool): Return the stop level instead. Default: False
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.DataFrame: VSTOP_DIST_PCT_{length}_{factor}, VSTOP_TREND_{length}_{factor}
"""
