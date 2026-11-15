# -*- coding: utf-8 -*-
from pandas_ta.utils import get_offset, verify_series


def amihud(close, volume, length=None, offset=None, **kwargs):
    """Indicator: Amihud Illiquidity Ratio (AMIHUD)"""
    # Validate Arguments
    length = int(length) if length and length > 0 else 21
    close = verify_series(close, length + 1)
    volume = verify_series(volume, length + 1)
    offset = get_offset(offset)

    if close is None or volume is None: return

    # Amihud (2002): price impact per currency traded -- a big move on thin
    # dollar volume is illiquid; a big move on heavy dollar volume is not.
    ret = close.pct_change()
    dvol = close * volume
    illiq = (ret.abs() / dvol.where(dvol > 0)).rolling(length).mean()

    # NOT scale-free on its own: it scales with currency x volume (the
    # issue's own flag). Normalised here as a ratio to its OWN trailing
    # history -- an expanding median, causal, no second window parameter --
    # the same cancellation this repo already uses for `maxvol_adv`'s
    # peak/ADV ratio, and chosen over the issue's other two options for a
    # concrete reason: `log` does not cancel a volume-only rescaling
    # (log(x*k) = log(x) + log(k), not invariant), and a rolling-RANK
    # normalisation is scale-free too but throws away magnitude ("twice as
    # illiquid as usual" becomes indistinguishable from "a little more").
    # The ratio keeps that magnitude while cancelling scale exactly. 1.0
    # reads "typical illiquidity for this series' own history"; 2.0 reads
    # "twice its own usual illiquidity". See docs/LiquidityMeasured.md.
    baseline = illiq.expanding(min_periods=1).median()
    out = illiq / baseline.where(baseline > 0)

    # Offset
    if offset != 0:
        out = out.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        out.fillna(kwargs["fillna"], inplace=True)

    # Name and Categorize it
    out.name = f"AMIHUD_{length}"
    out.category = "volume"

    return out


amihud.__doc__ = \
"""Amihud Illiquidity Ratio (AMIHUD)

Amihud (2002)'s illiquidity measure: the average absolute return per unit of
dollar volume over a trailing window -- a large price move on thin turnover
reads as illiquid, the same move on heavy turnover does not. Normalised
against its own trailing history (see below) so the column is scale-free.

Source: Yakov Amihud, "Illiquidity and Stock Returns: Cross-Section and
Time-Series Effects", Journal of Financial Markets 5(1), 2002. Cited
alongside Chan, "Algorithmic Trading" (2013), ch. 3, and Aldridge,
"High-Frequency Trading" (2010), ch. 4/10/11/17.

Decision made explicitly (the issue's own list): raw Amihud scales with
currency x volume, so two tickers (or one ticker after a split) are not
comparable and an x8 volume rescaling would not be scale-free. This ships
the ratio of the raw illiquidity to its own trailing (expanding) median,
not the raw value, and not `log` or a rolling rank -- see the module source
for why.

Calculation:
    Default Inputs:
        length=21
    ret = PCT_CHANGE(close)
    dvol = close * volume                                  (NaN where <= 0)
    illiq = SMA(ABS(ret) / dvol, length)
    baseline = EXPANDING_MEDIAN(illiq)                      (causal, from inception)
    AMIHUD = illiq / baseline

Args:
    close (pd.Series): Series of 'close's
    volume (pd.Series): Series of 'volume's
    length (int): Rolling illiquidity window. Default: 21
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)

Returns:
    pd.Series: AMIHUD_{length}, a ratio to the series' own trailing median
        illiquidity.
"""
