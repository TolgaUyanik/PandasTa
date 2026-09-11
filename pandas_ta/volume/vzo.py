# -*- coding: utf-8 -*-
"""Volume Zone Oscillator (VZO).

PINEBI-1b port of ``vzo`` from TradingView's ``ta`` library, publication
``RA2vGpkA``, lines 820-821.

    Mozilla Public License 2.0
    (c) TradingView

Gate A oracle, transcribed from the source::

    export vzo(simple int length) =>
        float result = zone(volume, length)

    zone(series float source, simple int length) =>
        float result = 100 * nz(ta.ema(math.sign(ta.change(close)) * source, length) / ta.ema(source, length))

THE TRAP THAT MAKES THIS A DIFFERENT INDICATOR IF YOU MISS IT: the sign term
reads **`close`**, not `source`.  `vzo` is volume signed by the PRICE
direction -- "how much of the recent volume traded on up bars" -- not volume
signed by its own change.  Reading `sign(change(volume))` gives a plausible
looking series that answers a different question, and no test on shape or
range would catch it.  The shared helper in ``momentum/_zone.py`` takes
`close` and `source` as separate arguments precisely so this cannot be
transcribed away.
"""
from pandas_ta.momentum._zone import zone
from pandas_ta.utils import get_offset, verify_series


def vzo(close, volume, length=None, offset=None, **kwargs):
    """Indicator: Volume Zone Oscillator (VZO)"""
    # Validate Arguments
    length = int(length) if length and length > 0 else 14
    close = verify_series(close, length)
    volume = verify_series(volume, length)
    offset = get_offset(offset)

    if close is None or volume is None: return

    # Calculate Result
    vzo = zone(close, volume, length)
    if vzo is None: return

    # Offset
    if offset != 0:
        vzo = vzo.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        vzo.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        vzo.fillna(method=kwargs["fill_method"], inplace=True)

    # Name and Categorize it
    vzo.name = f"VZO_{length}"
    vzo.category = "volume"

    return vzo


vzo.__doc__ = """Volume Zone Oscillator (VZO)

The share of recent volume that traded on up bars, as a percentage in roughly
[-100, 100].  +100 means every bar in the window closed up; -100 means every
bar closed down.

Scale-free in BOTH inputs, which is unusual and worth stating: the volume
units cancel in the ratio, so the reading is invariant to a share split or a
lot-size change as well as to a price scaling.  That makes it comparable
across tickers in a way raw volume columns are not.

Sources:
    https://www.tradingview.com/script/RA2vGpkA/ (MPL-2.0, (c) TradingView)

Calculation:
    Default Inputs:
        length=14

    VZO = 100 * ema(sign(change(close)) * volume, length) / ema(volume, length)

Args:
    close (pd.Series): Series of 'close's
    volume (pd.Series): Series of 'volume's
    length (int): The smoothing period. Default: 14
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.Series: New feature generated.
"""
