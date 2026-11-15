# -*- coding: utf-8 -*-
from pandas_ta.utils import get_offset, verify_series


def demand(high, low, close, volume, length=None, vol_length=None, offset=None, **kwargs):
    """Indicator: Demand Index / Demand Oscillator (DEMAND)"""
    # Validate Arguments
    length = int(length) if length and length > 0 else 10
    vol_length = int(vol_length) if vol_length and vol_length > 0 else 10
    min_len = max(length, vol_length) + 2
    high = verify_series(high, min_len)
    low = verify_series(low, min_len)
    close = verify_series(close, min_len)
    volume = verify_series(volume, min_len)
    offset = get_offset(offset)

    if high is None or low is None or close is None or volume is None:
        return

    # K = 3 * close / SMA(length)(rolling 2-bar max of the daily high-low
    # range). A ratio of two price-scale quantities -- scale-free, and
    # bit-identical under a uniform price rescale (see test_demand.py).
    day_range = high - low
    two_bar_range = day_range.rolling(2).max()
    range_sma = two_bar_range.rolling(length).mean()
    k = 3.0 * close / range_sma.where(range_sma > 0)

    # ASSUMPTION (Gate A, undocumented in the source corpus -- see module
    # docstring "WHAT IS ASSUMED"): ΔC/C is the plain 1-bar percent change,
    # close.pct_change().
    pct_chg = close.pct_change()
    denom = k * pct_chg

    rising = pct_chg > 0
    falling = pct_chg < 0
    # flat (pct_chg == 0, exact on tick-rounded data): neither branch fires,
    # BP and SP both default to volume below -- this IS the ΔC-near-zero
    # guard the issue asks for, not a special case bolted on afterward.

    safe_denom = denom.where(denom != 0)
    sp = volume.where(~rising, volume / safe_denom)
    bp = volume.where(~falling, volume / safe_denom.abs())

    raw = bp - sp
    # `pct_chg > 0` and `< 0` are both False on a NaN pct_chg (no prior bar)
    # AND on a NaN `k` (range_sma not yet full), both of which would
    # otherwise fall into the flat branch above and read a false 0.0 instead
    # of "undefined" -- mask both back to NaN explicitly. `length` and
    # `vol_length` warm up at different rates (`range_sma`'s is 1 bar longer
    # than a plain `rolling(length)`, from the leading `rolling(2).max()`),
    # so when `vol_length < length + 1` there is a real window where
    # `avg_vol` below is already defined but `k` is not -- a flat bar inside
    # that window must still read NaN, not 0.0, since BP/SP depend on BOTH
    # the volume floor AND the volatility scale being defined. A genuinely
    # flat bar outside that window (pct_chg == 0.0, k defined) is unaffected.
    raw = raw.where(pct_chg.notna() & k.notna())

    # Scale-free w.r.t. volume: the issue's own choice ("ship it divided by
    # volume, or by SMA(V, n)"). `raw` is linear in `volume` on every branch
    # (rising: V - V/denom = V*(1-1/denom); falling: V/|denom| - V =
    # V*(1/|denom|-1); flat: 0), so this ratio is bit-identical under a
    # uniform volume rescale.
    avg_vol = volume.rolling(vol_length).mean()
    out = raw / avg_vol.where(avg_vol > 0)

    # Offset
    if offset != 0:
        out = out.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        out.fillna(kwargs["fillna"], inplace=True)

    # Name and Categorize it
    out.name = f"DEMAND_{length}_{vol_length}"
    out.category = "volume"

    return out


demand.__doc__ = \
"""Demand Index / Demand Oscillator (DEMAND)

Sibbet's Demand Index, in Aspray's "Demand Oscillator" form as cited by
Kaufman (2013), ch. 12 "Volume, Open Interest, and Breadth". Splits each
bar's volume into a buying-pressure (BP) and selling-pressure (SP) share,
scaled by a volatility factor K, and reports BP - SP, normalised by a
trailing average volume to stay scale-free.

WHAT IS ASSUMED (Gate A risk, disclosed per the issue -- read before trusting
this column). This repo's copy of the source is Kaufman's prose plus a
formula the issue's own text calls "a reading of garbled PDF text... as far
as the PDF text can be read" -- the book page images and Aspray's original
TASC articles (June 1986, September 1989) are not in this worktree. Three
things the formula as given leaves unstated, decided here and NOT verified
against the primary source:

    1. "max 2-day high-low range" is read as `rolling(2).max()` of the daily
       `high - low` range, i.e. the larger of today's and yesterday's range --
       not a 2-bar high minus a 2-bar low.
    2. "ΔC/C" is read as the plain 1-bar percent change, `close.pct_change()`
       (today's close vs yesterday's), not a different base.
    3. The source gives no behaviour for an unchanged close. Here, ΔC == 0
       is treated as neutral: BP = SP = volume, so the oscillator reads
       exactly 0 -- this doubles as the ΔC-near-zero guard the issue calls
       for, since on tick-rounded data ΔC == 0 is the common failure mode,
       not a rare floating-point coincidence.

If a future session gets access to the book page or Aspray's article, treat
this module as unverified against the primary source until re-checked.

Scale-free (the issue's own decision point, resolved here): raw BP - SP is
linear in `volume` (see the module source), so dividing by a trailing SMA of
volume cancels any uniform volume rescale exactly, and the price side (K is a
close/range ratio, ΔC/C is a ratio) cancels any uniform price rescale exactly
-- both measured bit-identical under x8/x64 in tests/test_demand.py, not
merely asserted.

Calculation:
    Default Inputs:
        length=10, vol_length=10

    range        = High - Low
    range2       = ROLLING_MAX(range, 2)
    K            = 3 * Close / SMA(range2, length)
    pct_chg      = Close.pct_change()
    rising:  BP = Volume,                    SP = Volume / (K * pct_chg)
    falling: BP = Volume / (K * |pct_chg|),  SP = Volume
    flat:    BP = Volume,                    SP = Volume
    raw          = BP - SP
    DEMAND       = raw / SMA(Volume, vol_length)

Args:
    high (pd.Series): Series of 'high's
    low (pd.Series): Series of 'low's
    close (pd.Series): Series of 'close's
    volume (pd.Series): Series of 'volume's
    length (int): SMA window for the volatility-scaling range. Default: 10
    vol_length (int): SMA window for the volume normaliser. Default: 10
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)

Returns:
    pd.Series: DEMAND_{length}_{vol_length}, a volume-normalised oscillator.
        NaN wherever `range_sma` or `avg_vol` is not yet defined or is zero.
"""
