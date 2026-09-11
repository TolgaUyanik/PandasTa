# -*- coding: utf-8 -*-
"""Wave Period Oscillator (WPO).

PINEBI-1b port of ``wpo`` from TradingView's ``ta`` library, publication
``RA2vGpkA``, lines 860-863.

    Mozilla Public License 2.0
    (c) TradingView

Gate A oracle, transcribed from the source::

    export wpo(simple int length) =>
        float tt     = 2 * math.pi / math.asin(close[1] / high)
        float ti     = math.sign(ta.change(close)) * tt
        float result = ta.ema(ti, length)

THE DOMAIN PROBLEM, MEASURED RATHER THAN ASSUMED
------------------------------------------------
``math.asin`` is defined only on [-1, 1].  The argument here is
``close[1] / high``, the PREVIOUS close over the CURRENT high, and that ratio
exceeds 1 on any bar whose high is below the prior close -- a gap down, which
is common.  Pine returns `na` for an out-of-domain `asin` and carries the na
through the EMA; numpy returns `nan` with a RuntimeWarning.

The port therefore masks the out-of-domain bars to NaN explicitly instead of
letting a warning decide, and the test module pins the share of bars affected
on real data so the number is on the record rather than a surprise. Clamping
the ratio into the domain was rejected: it would manufacture a period reading
for exactly the gap bars where the construction has no meaning.

``asin`` also approaches 0 as the ratio approaches 0, so ``tt`` diverges; that
cannot happen with real OHLC (a high is never far above the prior close in
ratio terms) but the guard is kept because a synthetic fixture can do it.
"""
from numpy import arcsin, inf, nan, pi, sign, where
from pandas_ta.overlap.ema import ema
from pandas_ta.utils import get_offset, verify_series


def wpo(high, close, length=None, offset=None, **kwargs):
    """Indicator: Wave Period Oscillator (WPO)"""
    # Validate Arguments
    length = int(length) if length and length > 0 else 14
    high = verify_series(high, length)
    close = verify_series(close, length)
    offset = get_offset(offset)

    if high is None or close is None: return

    # Calculate Result
    ratio = close.shift(1) / high
    # Out of asin's domain -> no reading for that bar, not a clamped one.
    in_domain = (ratio >= -1.0) & (ratio <= 1.0)
    safe = ratio.where(in_domain)
    denom = arcsin(safe)
    tt = (2.0 * pi) / denom.replace(0.0, nan)
    tt = tt.replace([inf, -inf], nan)
    ti = sign(close.diff()) * tt

    wpo = ema(ti, length=length)
    if wpo is None: return

    # Offset
    if offset != 0:
        wpo = wpo.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        wpo.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        wpo.fillna(method=kwargs["fill_method"], inplace=True)

    # Name and Categorize it
    wpo.name = f"WPO_{length}"
    wpo.category = "momentum"

    return wpo


wpo.__doc__ = """Wave Period Oscillator (WPO)

Reads an implied cycle period off how far the previous close sat inside the
current bar's high, via `2*pi / asin(close[1] / high)`, then signs it by the
bar's direction and smooths it. Long implied periods with a consistent sign
indicate a slow directional wave; sign flips indicate chop.

Scale-free: the only price term is the RATIO `close[1] / high`, so a scaling
of every price leaves the output bit-identical.

⚠ Undefined on bars where `close[1] > high` -- a gap down puts the ratio
outside `asin`'s domain. Those bars are NaN by design, not clamped; see the
module docstring.

Sources:
    https://www.tradingview.com/script/RA2vGpkA/ (MPL-2.0, (c) TradingView)

Calculation:
    Default Inputs:
        length=14

    tt  = 2 * pi / asin(close[1] / high)      # NaN where |ratio| > 1
    ti  = sign(change(close)) * tt
    WPO = ema(ti, length)

Args:
    high (pd.Series): Series of 'high's
    close (pd.Series): Series of 'close's
    length (int): The EMA smoothing period. Default: 14
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.Series: New feature generated.
"""
