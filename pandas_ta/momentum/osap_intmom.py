# -*- coding: utf-8 -*-
from pandas_ta.utils import get_offset, verify_series


def osap_intmom(close, near_length=None, far_length=None, offset=None, **kwargs):
    """Indicator: Intermediate Momentum (INTMOM)"""
    # Validate Arguments
    near_length = int(near_length) if near_length and near_length > 0 else 126
    far_length = int(far_length) if far_length and far_length > 0 else 252
    close = verify_series(close, far_length + 1)
    offset = get_offset(offset)

    if close is None or near_length >= far_length:
        return

    # INTMOM = Close[t-near_length] / Close[t-far_length] - 1. A cumulative
    # return compounded over a window of daily returns telescopes exactly to
    # the ratio of the window's two endpoint prices (prod(1+r_i) across the
    # window equals P_end / P_start, every interior price cancelling) -- the
    # same identity already used by this fork's own `osap_mrrev` #37 -- so
    # the formation-period return reduces to a single price ratio with no
    # month-by-month compounding step needed.
    intmom = close.shift(near_length) / close.shift(far_length) - 1

    # Offset
    if offset != 0:
        intmom = intmom.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        intmom.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        intmom.fillna(method=kwargs["fill_method"], inplace=True)

    # Name and Categorize it
    intmom.name = f"INTMOM_{near_length}_{far_length}"
    intmom.category = "momentum"

    return intmom


osap_intmom.__doc__ = \
"""Intermediate Momentum (INTMOM)

Intermediate momentum, as asked for by issue #40: the issue names it `IntMom`
in the Open Source Asset Pricing (OSAP) SignalDoc (Chen & Zimmermann)
catalogue (Novy-Marx 2012, OSAP t 5.79) and restates its formation window as
months t-12 through t-7 -- the most recent six months (t-6 through t-1) are
excluded entirely, leaving only the six months before that. That window
description is the issue's own restatement (and `docs/issues/screen/
candidates.csv`'s), not independently checked against the primary SignalDoc
text, which this worktree cannot reach -- see Gate A below.

Gate A. The primary OSAP SignalDoc text and the OSAP replication code
(GPL-2.0) are NOT consulted or available in this worktree (`docs/pine/` and
web access are unavailable); per the issue, this is ported from the paper's
definition of intermediate momentum, not from OSAP's code. The definition
used here rests on one textbook identity and one ASSUMPTION, both disclosed:

    1. IDENTITY, not an assumption: a cumulative return compounded over a
       window of daily returns telescopes exactly to the ratio of the
       window's two endpoint prices -- prod(1+r_i) for i in the window
       equals P_end / P_start, with every interior price cancelling. So the
       six-month cumulative-return window reduces to a single price ratio,
       `close.shift(near_length) / close.shift(far_length) - 1`, with no
       month-by-month return summation needed. Identical to the identity
       this fork's own `osap_mrrev` #37 already relies on.
    2. ASSUMPTION (the issue's own stated conversion, taken as given rather
       than independently re-derived from the primary OSAP SignalDoc, which
       this worktree cannot reach): month-to-trading-day conversion at 21
       trading days/month -- the number this repo's own `RATE
       ["DAYS_PER_MONTH"]` constant also uses, cited here only as narrative
       corroboration of the literal 21, not an active code dependency on
       that constant -- giving `near_length` = 6 * 21 = 126 (the "t-7"
       boundary, one month less than the window's literal month count) and
       `far_length` = 12 * 21 = 252 (the "t-12" boundary). This near/far
       split (far bound = the window's literal month count, near bound = one
       month less) is not a one-off invented for this port: `osap_mrrev`
       #37's own module docstring already derived this exact arithmetic as
       internal corroboration before this port existed --
       `docs/issues/screen/ind_screen.py`'s `osap_intmom` row,
       `delay(c,126)/delay(c,252)`, with 126/21=6=7-1 and 252/21=12 -- and a
       sibling row, `osap_lrrev` ("t-36..t-13" -> `delay(c,252)/delay(c,756)`,
       252/21=12=13-1, 756/21=36), follows the identical pattern. This is a
       real, checkable, internal cross-candidate pattern, not confirmation
       against the primary SignalDoc, which is unreachable here. This is the
       exact "126/252 bars" scale-free form stated in the issue and
       `docs/issues/screen/candidates.csv` (candidate `osap_intmom`), not a
       fresh reading, and it remains unconfirmed against the primary
       SignalDoc text itself.

If a future session gets access to the OSAP SignalDoc PDF/CSV, treat the
126/252 conversion as unverified against the primary source until re-checked
(it is currently verified only against the issue's own restatement of it).

Calculation:
    Default Inputs:
        near_length=126, far_length=252
    INTMOM = Close.shift(near_length) / Close.shift(far_length) - 1

Args:
    close (pd.Series): Series of 'close's
    near_length (int): Bars back to the end of the formation window (the
        "t-7" boundary). Default: 126
    far_length (int): Bars back to the start of the formation window (the
        "t-12" boundary). Default: 252
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.Series: INTMOM_{near_length}_{far_length}, a scale-free (dimensionless)
        cumulative-return ratio. NaN for the first `far_length` bars.
"""
