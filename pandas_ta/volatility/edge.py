# -*- coding: utf-8 -*-
import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from pandas import Series

from pandas_ta.utils import get_offset, verify_series

TIE_RTOL = 1e-9


def _prices(s):
    """A price as float, NaN where it is not finite and positive: log(0) or
    log(negative) has no spread reading."""
    a = s.to_numpy(dtype=float)
    return np.where(np.isfinite(a) & (a > 0), a, np.nan)


def _differs(a, b):
    """`a != b` with a relative tolerance, NaN where either side is NaN.
    The tolerance is the prototype's: adjusted prices carry ulp noise, so an
    open that equals the high before adjustment can miss it by an ulp after."""
    with np.errstate(invalid="ignore"):
        out = (np.abs(a - b) > TIE_RTOL * np.maximum(np.abs(a), np.abs(b))).astype(float)
    return np.where(np.isnan(a) | np.isnan(b), np.nan, out)


def _pairs(o, h, l, c):
    """Per-pair inputs of eguidotti/bidask `edge()`; entry t-1 pairs bar t
    with bar t-1. The returns r1..r5 are the reference's log-price
    differences, each written as the log of a price RATIO so that a x2^k
    rescaling of every price leaves them bit-identical. Bar t-1's open and
    bar t's close are not read; the reference reads neither."""
    h1, l1, c1 = h[:-1], l[:-1], c[:-1]
    o, h, l = o[1:], h[1:], l[1:]
    with np.errstate(invalid="ignore"):
        r1 = 0.5 * (np.log(h / o) + np.log(l / o))       # m - o
        r2 = -0.5 * (np.log(h1 / o) + np.log(l1 / o))    # o - m1
        r3 = 0.5 * (np.log(h / c1) + np.log(l / c1))     # m - c1
        r4 = -0.5 * (np.log(h1 / c1) + np.log(l1 / c1))  # c1 - m1
        r5 = np.log(o / c1)                              # o - c1
    # tau: the bar traded at more than one price, (h != l) | (l != c1)
    hl, lc = _differs(h, l), _differs(l, c1)
    tau = np.where(np.isnan(hl) | np.isnan(lc), np.nan, np.maximum(hl, lc))
    po1 = tau * _differs(o, h)
    po2 = tau * _differs(o, l)
    pc1 = tau * _differs(c1, h1)
    pc2 = tau * _differs(c1, l1)
    return r1, r2, r3, r4, r5, tau, po1, po2, pc1, pc2


def _edge_rows(r1, r2, r3, r4, r5, tau, po1, po2, pc1, pc2):
    """Ardia, Guidotti & Kroencke (2024) eq. 15, transcribed from
    eguidotti/bidask `edge()`, one estimate per row (axis 1 is the window).
    Unsigned, sqrt(|s2|): the reference's default `sign=False`."""
    with np.errstate(divide="ignore", invalid="ignore"):
        pt = tau.mean(axis=1)
        po = po1.mean(axis=1) + po2.mean(axis=1)
        pc = pc1.mean(axis=1) + pc2.mean(axis=1)
        # the reference returns missing below two traded bars or with
        # po == 0 or pc == 0 (its divisors)
        ok = (tau.sum(axis=1) >= 2) & (po != 0) & (pc != 0)

        # de-meaned returns
        d1 = r1 - (r1.mean(axis=1) / pt)[:, None] * tau
        d3 = r3 - (r3.mean(axis=1) / pt)[:, None] * tau
        d5 = r5 - (r5.mean(axis=1) / pt)[:, None] * tau

        # the two moment conditions
        a1 = (-4.0 / po)[:, None]
        a2 = (-4.0 / pc)[:, None]
        x1 = a1 * d1 * r2 + a2 * d3 * r4
        x2 = a1 * d1 * r5 + a2 * d5 * r4

        e1 = x1.mean(axis=1)
        e2 = x2.mean(axis=1)
        v1 = (x1 ** 2).mean(axis=1) - e1 ** 2
        v2 = (x2 ** 2).mean(axis=1) - e2 ** 2

        # GMM weight: inverse-variance average, equal weights if the total
        # variance is not positive
        vt = v1 + v2
        s2 = np.where(vt > 0, (v2 * e1 + v1 * e2) / vt, (e1 + e2) / 2.0)
        return np.where(ok, np.sqrt(np.abs(s2)), np.nan)


def edge(open_, high, low, close, length=None, offset=None, **kwargs):
    """Indicator: EDGE Bid-Ask Spread Estimator (EDGE)"""
    # Validate Arguments
    length = int(length) if length and int(length) > 2 else 21
    open_ = verify_series(open_, length)
    high = verify_series(high, length)
    low = verify_series(low, length)
    close = verify_series(close, length)
    offset = get_offset(offset)

    if open_ is None or high is None or low is None or close is None: return

    # Calculate Result: each bar's estimate is the reference's `edge()` run
    # on that bar's own `length` bars (length - 1 consecutive pairs),
    # computed window by window rather than from rolling sums, so no value
    # depends on bars that have left the window. A window with any missing
    # input is NaN, as the reference's `edge_rolling` makes it.
    cols = _pairs(_prices(open_), _prices(high), _prices(low), _prices(close))
    w = length - 1
    windows = [sliding_window_view(x, w) for x in cols]
    complete = ~np.any([np.isnan(x).any(axis=1) for x in windows], axis=0)
    values = np.full(open_.size, np.nan)
    values[length - 1:] = np.where(complete, _edge_rows(*windows), np.nan)

    spread = Series(values, index=open_.index)

    # Offset
    if offset != 0:
        spread = spread.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        spread.fillna(kwargs["fillna"], inplace=True)

    # Name and Categorize it
    spread.name = f"EDGE_{length}"
    spread.category = "volatility"

    return spread


edge.__doc__ = \
"""EDGE Bid-Ask Spread Estimator (EDGE)

Estimates the bid-ask spread, as a fraction of price (0.01 = 1%), from open,
high, low and close prices alone. EDGE combines two moment conditions on
log returns between the bar's midrange, its open and the prior close, each
an unbiased estimator of the squared spread, and weights them by their
inverse variances (a GMM average). Unlike Corwin-Schultz (`corwin_schultz`,
high and low) and Roll (`roll_spread`, close) it uses all four prices, and
it corrects for infrequent trading: a bar that traded at a single price
(h == l == prior close) is weighted out through tau.

Sources: Ardia, Guidotti & Kroencke (2024), "Efficient estimation of
bid-ask spreads from open, high, low, and close prices", Journal of
Financial Economics 161, 103916, eq. 15. Transcribed from the authors'
reference implementation, eguidotti/bidask (MIT), `python/bidask/edge.py`
at commit 1caba55; its published test value is reproduced in
tests/test_edge.py.

Decisions made explicitly:
- Unsigned, sqrt(|s2|), the reference's default (`sign=False`). A negative
  squared-spread estimate reads as its magnitude.
- Each bar reads its own `length` bars (length - 1 consecutive pairs), as
  the reference's `edge_rolling(window=length)` does. The open of the
  window's first bar and the close of the current bar are not read.
- Price ties (the indicator variables, e.g. open == high) are tested on raw
  prices with a relative tolerance of 1e-9 instead of the reference's exact
  test on logs: adjusted prices carry ulp noise that exact equality reads
  as "no tie". On unadjusted tick data the two agree.
- A window with a missing, zero or negative price is NaN, as
  `edge_rolling`'s default `min_periods` makes it; the reference's
  single-sample `edge()` instead skips missing values.
- Computed window by window, not from rolling sums: every value depends on
  its own window only, so a bad tick stops affecting the estimate as soon
  as it leaves the window.

Scale-free: every return is a log price ratio and every tie test is
relative, so a x8/x64 rescaling is bit-identical. See docs/EdgeMeasured.md.

Calculation:
    Default Inputs:
        length=21
    o, h, l, c = LN(open), LN(high), LN(low), LN(close);  m = (h + l) / 2
    per pair (t, t-1):  r1 = m - o, r2 = o - m1, r3 = m - c1,
                        r4 = c1 - m1, r5 = o - c1
    tau = (h != l) | (l != c1)
    po = MEAN(tau * (o != h)) + MEAN(tau * (o != l))
    pc = MEAN(tau * (c1 != h1)) + MEAN(tau * (c1 != l1))
    pt = MEAN(tau)
    dK = rK - MEAN(rK) / pt * tau                 for K = 1, 3, 5
    x1 = -4/po * d1 * r2 - 4/pc * d3 * r4
    x2 = -4/po * d1 * r5 - 4/pc * d5 * r4
    e = MEAN(x),  v = MEAN(x^2) - e^2             for x1, x2
    s2 = (v2*e1 + v1*e2) / (v1 + v2)  if v1 + v2 > 0  else  (e1 + e2) / 2
    EDGE = SQRT(ABS(s2))
    NaN if SUM(tau) < 2, po == 0 or pc == 0
    (means over the window's length - 1 pairs)

Args:
    open_ (pd.Series): Series of 'open's
    high (pd.Series): Series of 'high's
    low (pd.Series): Series of 'low's
    close (pd.Series): Series of 'close's
    length (int): Bars per estimate, > 2. Default: 21
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)

Returns:
    pd.Series: EDGE_{length}, a spread as a fraction of price, >= 0.
"""
