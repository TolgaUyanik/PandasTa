# -*- coding: utf-8 -*-
from pandas_ta.utils import get_offset, verify_series


def osap_mrrev(close, near_length=None, far_length=None, offset=None, **kwargs):
    """Indicator: Medium-Run Reversal (MRREV)"""
    # Validate Arguments
    near_length = int(near_length) if near_length and near_length > 0 else 252
    far_length = int(far_length) if far_length and far_length > 0 else 378
    close = verify_series(close, far_length + 1)
    offset = get_offset(offset)

    if close is None or near_length >= far_length:
        return

    # MRREV = Close[t-near_length] / Close[t-far_length] - 1. A cumulative
    # return over a price series telescopes to the ratio of its two endpoints
    # (the product of (1+r_i) across the window equals P_end / P_start), so
    # this is the exact formation-period return from far_length bars ago to
    # near_length bars ago -- no month-by-month compounding step needed.
    mrrev = close.shift(near_length) / close.shift(far_length) - 1

    # Offset
    if offset != 0:
        mrrev = mrrev.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        mrrev.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        mrrev.fillna(method=kwargs["fill_method"], inplace=True)

    # Name and Categorize it
    mrrev.name = f"MRREV_{near_length}_{far_length}"
    mrrev.category = "momentum"

    return mrrev


osap_mrrev.__doc__ = \
"""Medium-Run Reversal (MRREV)

A medium-run reversal effect, as asked for by issue #37: the issue names it
`MRreversal` in the Open Source Asset Pricing (OSAP) SignalDoc (Chen &
Zimmermann) catalogue (t-stat not given, per the issue's own measurement)
and restates its formation window as months t-18 through t-13 -- a 6-month
window ending 12 months before the current month, so the most recent year
is excluded from the reversal signal entirely. That window description is
the issue's own restatement, not independently checked against the primary
SignalDoc text, which this worktree cannot reach -- see the Gate A
disclosure below.

Gate A. The OSAP SignalDoc text itself and the OSAP replication code (GPL-2.0)
are NOT consulted or available in this worktree; per the issue, this is ported
from the public finance-literature definition of a medium-run reversal
effect, not from OSAP's code. The definition used here rests on one
textbook identity and one ASSUMPTION, both disclosed:

    1. IDENTITY, not an assumption: a cumulative return compounded over a
       window of daily returns telescopes exactly to the ratio of the
       window's two endpoint prices -- prod(1+r_i) for i in the window
       equals P_end / P_start, with every interior price cancelling. So the
       6-month cumulative-return window reduces to a single price ratio,
       `close.shift(near_length) / close.shift(far_length) - 1`, with no
       month-by-month return summation needed.
    2. ASSUMPTION (the issue's own stated conversion, taken as given rather
       than independently re-derived from the primary OSAP SignalDoc, which
       this worktree cannot reach): month-to-trading-day conversion at 21
       trading days/month -- the number this repo's own `RATE
       ["DAYS_PER_MONTH"]` constant also uses, cited here only as narrative
       corroboration of the literal 21, not an active code dependency on
       that constant -- giving `near_length` = 12 * 21 = 252 and
       `far_length` = 18 * 21 = 378. The near/far split (far bound = the
       window's literal month count, near bound = one month less) is not a
       one-off either: the same prototype file carries two sibling `@cand`
       rows matching the identical arithmetic -- `osap_intmom` ("t-12..t-7"
       -> `delay(c,126)/delay(c,252)`, 126/21=6=7-1, 252/21=12) and
       `osap_lrrev` ("t-36..t-13" -> `delay(c,252)/delay(c,756)`,
       252/21=12=13-1, 756/21=36). Two further rows, `osap_mom12_1`
       (`delay(c,21)/delay(c,252)`) and `osap_mom6_1`
       (`delay(c,21)/delay(c,126)`), follow a related but distinct
       convention (Jegadeesh-Titman "skip the last month": near bound fixed
       at 21 = 1 month, not one-less-than-the-window) -- they corroborate the
       prototype's consistent use of 21-trading-days/month, not that every
       row shares this one's exact near/far arithmetic. This is a real,
       checkable, internal cross-candidate pattern, not confirmation against
       the primary SignalDoc, which is unreachable here. This is the exact
       "252/378 bars" scale-free form stated in the issue and
       `docs/issues/screen/candidates.csv` (candidate `osap_mrrev`), not a
       fresh reading, and it remains unconfirmed against the primary
       SignalDoc text itself.

Calculation:
    Default Inputs:
        near_length=252, far_length=378
    MRREV = Close.shift(near_length) / Close.shift(far_length) - 1

Args:
    close (pd.Series): Series of 'close's
    near_length (int): Bars back to the end of the formation window (the
        "t-13" boundary). Default: 252
    far_length (int): Bars back to the start of the formation window (the
        "t-18" boundary). Default: 378
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.Series: MRREV_{near_length}_{far_length}, a scale-free (dimensionless)
        cumulative-return ratio. NaN for the first `far_length` bars.
"""
