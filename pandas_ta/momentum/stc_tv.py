# -*- coding: utf-8 -*-
"""Schaff Trend Cycle, the TradingView library form (STCTV).

PINEBI-1b port of ``stc`` from TradingView's ``ta`` library, publication
``RA2vGpkA``, lines 527-533.

    Mozilla Public License 2.0
    (c) TradingView

⚠ **NAMED `stc_tv`, NOT `stc`.** This fork already ships an `stc`, and round 7
established that it is NOT this calculation. Following the `t3` / `t3_tv`
precedent PINEBI-1c set for exactly this situation.

Gate A oracle, transcribed from the source::

    export stc(series float source, simple int fast, simple int slow, simple int cycle, simple int d1, simple int d2) =>
        float macd   = ta.ema(source, fast) - ta.ema(source, slow)
        float k      = nz(fixnan(ta.stoch(macd, macd, macd, cycle)))
        float d      = ta.ema(k, d1)
        float kd     = nz(fixnan(ta.stoch(d, d, d, cycle)))
        float stc    = ta.ema(kd, d2)
        float result = math.max(math.min(stc, 100), 0)

THREE MEASURED DIFFERENCES FROM THE SHIPPED `stc`, from the round-7 review
---------------------------------------------------------------------------
1. **`d1` and `d2` are parameters here and do not exist on `pandas_ta.stc`**,
   which substitutes a fixed-alpha recursion. Two of the five smoothing
   stages are therefore not reachable on the shipped function.
2. **This clamps to [0, 100]; `pandas_ta.stc` does not.**
3. **`pandas_ta.stc:195` guards with `if lowest_xmacd.iloc[i] > 0`**, which
   freezes the first stochastic whenever the rolling MACD minimum is <= 0 --
   the NORMAL case for a zero-centred oscillator, not an edge case.

`ta.stoch(x, x, x, cycle)` with one series in all three price slots is the
plain rolling rescale `100 * (x - min(x)) / (max(x) - min(x))`, which is what
is implemented. Pine's `nz(fixnan(...))` carries the last valid value through
a flat window rather than emitting NaN; that is reproduced with a forward
fill, because a flat window here means "no new information", not "no reading".
"""
from pandas_ta.overlap.ema import ema
from pandas_ta.utils import get_offset, verify_series


def _stoch_self(x, length):
    """Pine's `ta.stoch(x, x, x, length)` — a plain rolling rescale."""
    lo = x.rolling(length).min()
    hi = x.rolling(length).max()
    rng = hi - lo
    out = 100.0 * (x - lo) / rng.where(rng != 0)
    # `fixnan` holds the previous valid value across a flat window.
    return out.ffill()


def stc_tv(close, fast=None, slow=None, cycle=None, d1=None, d2=None,
           offset=None, **kwargs):
    """Indicator: Schaff Trend Cycle, TradingView form (STCTV)"""
    # Validate Arguments
    fast = int(fast) if fast and fast > 0 else 23
    slow = int(slow) if slow and slow > 0 else 50
    cycle = int(cycle) if cycle and cycle > 0 else 10
    d1 = int(d1) if d1 and d1 > 0 else 3
    d2 = int(d2) if d2 and d2 > 0 else 3
    close = verify_series(close, slow + cycle)
    offset = get_offset(offset)

    if close is None: return

    # Calculate Result
    ef, es = ema(close, length=fast), ema(close, length=slow)
    if ef is None or es is None: return
    macd = ef - es
    k = _stoch_self(macd, cycle)
    d = ema(k, length=d1)
    if d is None: return
    kd = _stoch_self(d, cycle)
    st = ema(kd, length=d2)
    if st is None: return
    stc_tv = st.clip(lower=0.0, upper=100.0)

    # Offset
    if offset != 0:
        stc_tv = stc_tv.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        stc_tv.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        stc_tv.fillna(method=kwargs["fill_method"], inplace=True)

    # Name and Categorize it
    stc_tv.name = f"STCTV_{fast}_{slow}_{cycle}_{d1}_{d2}"
    stc_tv.category = "momentum"

    return stc_tv


stc_tv.__doc__ = """Schaff Trend Cycle — TradingView library form (STCTV)

A MACD put through two stochastic rescales with an EMA between them, clamped
to [0, 100]. The double rescale is what makes it snap between extremes rather
than drift like the MACD it is built from.

⚠ NOT the same calculation as this fork's `stc`. That one has no `d1`/`d2`,
does not clamp, and carries a guard that freezes its first stochastic whenever
the rolling MACD minimum is <= 0 — which is the normal case for a zero-centred
oscillator. See the module docstring for the three measured differences.

Scale-free: every stage after the MACD is a rescale or a bounded smoothing, so
a price scaling leaves the output bit-identical.

Sources:
    https://www.tradingview.com/script/RA2vGpkA/ (MPL-2.0, (c) TradingView)

Calculation:
    Default Inputs:
        fast=23, slow=50, cycle=10, d1=3, d2=3

    macd = ema(close, fast) - ema(close, slow)
    k    = stoch_self(macd, cycle)
    d    = ema(k, d1)
    kd   = stoch_self(d, cycle)
    STCTV = clip(ema(kd, d2), 0, 100)

Args:
    close (pd.Series): Series of 'close's
    fast (int): Fast EMA period. Default: 23
    slow (int): Slow EMA period. Default: 50
    cycle (int): Stochastic window. Default: 10
    d1 (int): First smoothing period. Default: 3
    d2 (int): Second smoothing period. Default: 3
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.Series: New feature generated.
"""
