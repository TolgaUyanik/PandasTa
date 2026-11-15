# -*- coding: utf-8 -*-
from numpy import errstate, log
from pandas import DataFrame, Series

from pandas_ta.utils import get_offset, verify_series


def ovn_split(open_, close, length=None, offset=None, **kwargs):
    """Indicator: Overnight / Intraday Return Split (OVN)"""
    # Validate Arguments
    length = int(length) if length and length > 0 else 21
    open_ = verify_series(open_, length + 1)
    close = verify_series(close, length + 1)
    offset = get_offset(offset)

    if open_ is None or close is None: return

    # Calculate Result. Each bar's move is split into two legs: overnight
    # (yesterday's close to today's open) and intraday (today's open to
    # today's close). Log returns, not simple returns: their rolling SUM is
    # the log of the compounded return over the window, which is what a
    # "rolling sum of returns" means in the cited momentum literature.
    with errstate(divide="ignore", invalid="ignore"):
        overnight = log(open_.to_numpy(dtype=float) / close.shift(1).to_numpy(dtype=float))
        intraday = log(close.to_numpy(dtype=float) / open_.to_numpy(dtype=float))
    overnight = Series(overnight, index=close.index)
    intraday = Series(intraday, index=close.index)
    # Bar 0 has no prior close, so its overnight leg is undefined by
    # construction; blank its intraday leg to match, so OVNSUM and INTSUM
    # warm up together instead of INTSUM starting one bar earlier.
    intraday.iloc[0] = float("nan")

    ovn_sum = overnight.rolling(length).sum()
    int_sum = intraday.rolling(length).sum()
    diff = ovn_sum - int_sum

    df = DataFrame({
        f"OVNSUM_{length}": ovn_sum,
        f"INTSUM_{length}": int_sum,
        f"OVNINTDIFF_{length}": diff,
    }, index=close.index)

    # Offset
    if offset != 0:
        df = df.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        df.fillna(kwargs["fillna"], inplace=True)

    # Name and Categorize it
    df.name = f"OVN_{length}"
    df.category = "momentum"

    return df


ovn_split.__doc__ = \
"""Overnight / Intraday Return Split (OVN)

Splits each bar's move into two legs and sums each over a trailing window:
the OVERNIGHT leg (yesterday's close to today's open) and the INTRADAY leg
(today's open to today's close). PandasTa issue #14.

Sources:
    Alpha Architect, "Overnight Momentum vs. Intraday Momentum" and
    "Trading Costs Wipe Out the Overnight Return Anomaly" (describe the
    overnight/intraday return split; neither's specific tests are
    reproduced here).
    Quantpedia, "Dangers of Relying on OHLC Prices -- the Case of Overnight
    Drift in GDX" (the risk this port's docs/OvnSplitMeasured.md records:
    free OHLC data's `open` is sometimes wrong, which would corrupt the
    overnight leg specifically).

Decisions made here (the issue leaves them open, no human was available to
ask in this headless session):

* Log returns, not simple (arithmetic) returns. A rolling SUM of log
  returns equals the log of the bar-by-bar COMPOUNDED return over the
  window -- the identity "rolling sum of returns" invokes in the cited
  literature. A simple-return sum has no such identity.
* Window length 21 (one trading month), matching the monthly formation
  horizon the Alpha Architect sources use repeatedly for sorting on this
  split. Not tuned as a standalone feature window. ASSUMPTION.
* The difference column (OVNINTDIFF) is shipped: the issue offers it as
  optional, and the sources frame "overnight minus intraday" as the
  anomaly signal itself, not a derived extra.

This is NOT the one-day `GAP_PCT` / `OPEN_GAP_PCT` the parent repo's
`indicator_engine._calculate_gap_indicators` already computes (per the
issue's own overlap note): those are single-bar, this is a rolling sum
over `length` bars of the overnight leg alone, plus the matching intraday
leg and their difference.

Scale-free by construction: each leg is the log of a PRICE RATIO, so any
positive rescaling of `open`/`close` cancels inside the ratio before the
log. See docs/OvnSplitMeasured.md for the measured x8/x64/x10/x3.7 check.

Calculation:
    Default Inputs:
        length=21
    overnight = LOG(open / close[1])
    intraday  = LOG(close / open)
    OVNSUM_{length}      = SUM(overnight, length)
    INTSUM_{length}      = SUM(intraday, length)
    OVNINTDIFF_{length}  = OVNSUM_{length} - INTSUM_{length}

Args:
    open_ (pd.Series): Series of 'open's
    close (pd.Series): Series of 'close's
    length (int): Rolling window, in bars. Default: 21
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)

Returns:
    pd.DataFrame: OVNSUM_{length}, INTSUM_{length}, OVNINTDIFF_{length}
"""
