# -*- coding: utf-8 -*-
from numpy import nan

from pandas_ta.utils import get_offset, verify_series


def gapm(open_, close, length=40, signal=20, offset=None, **kwargs):
    """Indicator: Gap Momentum (GAPM)"""
    length = int(length) if length and length > 0 else 40
    signal = int(signal) if signal and signal > 0 else 20
    open_ = verify_series(open_, length)
    close = verify_series(close, length)
    offset = get_offset(offset)

    if open_ is None or close is None: return

    gap = open_ - close.shift(1)
    up = gap.clip(lower=0)
    dn = (-gap).clip(lower=0)
    dn_sum = dn.rolling(length).sum()
    ratio = up.rolling(length).sum() / dn_sum.where(dn_sum > 0)  # no down gap: NaN, never inf

    # A NaN ratio is skipped by the EMA (neither a sample nor a decay step) and
    # is NaN in the output; the EMA needs `signal` valid ratios before it emits.
    gapm = ratio.ewm(span=signal, adjust=False, min_periods=signal, ignore_na=True).mean()
    gapm[ratio.isna()] = nan

    # Offset
    if offset != 0:
        gapm = gapm.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        gapm.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        method = kwargs["fill_method"]
        gapm = gapm.ffill() if method in ("ffill", "pad") else gapm.bfill()

    gapm.name = f"GAPM_{length}_{signal}"
    gapm.category = "momentum"

    return gapm


gapm.__doc__ = \
"""Gap Momentum (GAPM)

The ratio of the sum of up gaps to the sum of down gaps over `length` bars,
smoothed by an EMA of span `signal`. A gap is today's open minus yesterday's
close. Gaps are in price units, and the units cancel in the ratio, so the
column is scale-free. Above 1 means up gaps have outweighed down gaps.

Sources:
    Perry J. Kaufman, "Gap Momentum", Technical Analysis of Stocks &
    Commodities (TASC), January 2024. Cited from recollection; the article
    was NOT checked for this port.
    Reddit, r/algotrading post 1brndbe (2024-03-30),
    https://www.reddit.com/r/algotrading/comments/1brndbe/ (tier 4 crowd
    talk): "Measures the ratio of cumulative upward price gaps to downward
    price gaps over a specified period." The poster's claims (a predictive
    trend signal that works better in uptrends, tested on QQQ) are untested
    here.

This fork's choices, not the source's: the EMA smoothing; the defaults
(the thread gives no lengths); and a NaN ratio, never inf, when the window
holds no down gap. A "ratio = 1" rule for that case, which the owner's notes
attribute to Kaufman (as recalled, not checked), is not used. A NaN ratio is
skipped by the EMA and is NaN in the output. The ratio is floored at 0 and
unbounded above, so the tail is lopsided: on a synthetic walk where 80% of
bars open at the prior close, GAPM spans 0.176 to 26.385 around a median of
1.254.

Calculation:
    Default Inputs:
        length=40, signal=20
    gap = open - close[1]
    up = max(gap, 0);  dn = max(-gap, 0)
    ratio = SUM(up, length) / SUM(dn, length)
    ratio = NaN where the window holds no dn > 0
    GAPM = EMA(ratio, signal), with adjust=False and NaN ratios skipped;
           the first value is at the `signal`-th valid ratio,
           and GAPM is NaN wherever ratio is NaN

Args:
    open_ (pd.Series): Series of 'open's
    close (pd.Series): Series of 'close's
    length (int): Gap-sum window. Default: 40
    signal (int): EMA span of the ratio. Default: 20
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): 'ffill'/'pad' or 'bfill'/'backfill'

Returns:
    pd.Series: GAPM_{length}_{signal}
"""
