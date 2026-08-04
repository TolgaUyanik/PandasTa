# -*- coding: utf-8 -*-
from pandas import DataFrame

from pandas_ta.utils import get_offset, verify_series


def priorday_fib(high, low, close, offset=None, **kwargs):
    """Indicator: Prior-Day Fibonacci Zone Distance (PDFIB)"""
    high = verify_series(high, 2)
    low = verify_series(low, 2)
    close = verify_series(close, 2)
    offset = get_offset(offset)

    if high is None or low is None or close is None: return

    # On a DAILY bar series, "the prior session" IS the prior bar -- no
    # timezone-aware session-window replication needed (that machinery in
    # the source Pine script exists only because Pine usually runs on
    # intraday charts, where a session spans many bars). This is the
    # reformulation Fletcher round 2 pointed at directly: the original
    # defer reasoning quoted "a daily bar IS the whole session" as an
    # obstacle when it is actually the simplification that makes this a
    # trivial, low-risk port on this project's daily data.
    prior_high = high.shift(1)
    prior_low = low.shift(1)
    prior_mid = (prior_high + prior_low) / 2.0

    dist_high_pct = (close - prior_high) / close * 100
    dist_mid_pct = (close - prior_mid) / close * 100
    dist_low_pct = (close - prior_low) / close * 100

    # Offset
    if offset != 0:
        dist_high_pct = dist_high_pct.shift(offset)
        dist_mid_pct = dist_mid_pct.shift(offset)
        dist_low_pct = dist_low_pct.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        dist_high_pct.fillna(kwargs["fillna"], inplace=True)
        dist_mid_pct.fillna(kwargs["fillna"], inplace=True)
        dist_low_pct.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        dist_high_pct.fillna(method=kwargs["fill_method"], inplace=True)
        dist_mid_pct.fillna(method=kwargs["fill_method"], inplace=True)
        dist_low_pct.fillna(method=kwargs["fill_method"], inplace=True)

    dist_high_pct.name = "PDFIB_HIGH"
    dist_mid_pct.name = "PDFIB_MID"
    dist_low_pct.name = "PDFIB_LOW"

    df = DataFrame({
        dist_high_pct.name: dist_high_pct,
        dist_mid_pct.name: dist_mid_pct,
        dist_low_pct.name: dist_low_pct,
    })
    df.name = "PDFIB"
    df.category = "trend"

    return df


priorday_fib.__doc__ = \
"""Prior-Day Fibonacci Zone Distance (PDFIB)

Scale-free % distance from close to the prior bar's high, midpoint
("equilibrium"), and low -- the daily-bar reformulation of a prior-session
Fibonacci retracement zone tool. On DAILY data one bar already IS one
session, so "prior session high/low" collapses to `high.shift(1)`/
`low.shift(1)`; no timezone-aware session-window detection is needed (that
machinery exists in the source only because it targets intraday charts,
where a session spans many bars).

Source: TradingView community indicator "Fib Zone Lines" by (orphaned
metadata -- see `datastore/source/pine_triage.csv`),
https://www.tradingview.com/script/y2eyl03S-Fib-Zone-Lines/
(ported into AwakenAnalytics/Backtesting TVPTA-3, 2026-08-04; MPL-2.0 per
TradingView's open-source publication convention). Only the daily-bar
midpoint/high/low reformulation is ported here -- the source script's full
level set (-1.75 .. 1.75, an 11-level fan) and its intraday
timezone-aware session-boundary detection are NOT replicated; if intraday
fidelity to the exact Pine session window is wanted later, that is a
separate, genuinely scoped follow-up, not a blocker for this daily version.

Calculation:
    prior_high = high.shift(1); prior_low = low.shift(1)
    prior_mid  = (prior_high + prior_low) / 2
    PDFIB_HIGH = (close - prior_high) / close * 100
    PDFIB_MID  = (close - prior_mid)  / close * 100
    PDFIB_LOW  = (close - prior_low)  / close * 100

Args:
    high (pd.Series): Series of 'high's
    low (pd.Series): Series of 'low's
    close (pd.Series): Series of 'close's
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.DataFrame: PDFIB_HIGH, PDFIB_MID, PDFIB_LOW columns.
"""
