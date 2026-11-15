# -*- coding: utf-8 -*-
import numpy as np
from pandas_ta.utils import get_offset, verify_series


def vol_sign_rev(close, volume, offset=None, **kwargs):
    """Indicator: Volume-Signed Reversal (VSR)"""
    # Validate Arguments
    close = verify_series(close, 2)  # min length 2: delta(.,1) needs 2 bars
    volume = verify_series(volume, 2)  # min length 2: delta(.,1) needs 2 bars
    offset = get_offset(offset)

    if close is None or volume is None:
        return

    # Alpha101 #12 (Kakushadze 2016): sign(delta(volume,1)) * -delta(close,1).
    # Scale-free form (issue #43 / docs/issues/screen/candidates.csv,
    # candidate a101_012): delta(close,1) -> one-bar return, so the price
    # term is close.pct_change(1) rather than the raw price difference.
    ret = close / close.shift(1) - 1
    vsr = np.sign(volume.diff(1)) * -ret

    # Offset
    if offset != 0:
        vsr = vsr.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        vsr.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        vsr.fillna(method=kwargs["fill_method"], inplace=True)

    # Name and Categorize it
    vsr.name = "VSR"
    vsr.category = "volume"

    return vsr


vol_sign_rev.__doc__ = \
"""Volume-Signed Reversal (VSR)

Alpha#12 of Kakushadze's "101 Formulaic Alphas" (2016, Wilmott; read from the
vnpy `alpha101` copy's restatement, cited by the issue and
`docs/issues/screen/candidates.csv` as `a101_012`, not from the paper or the
vnpy repository directly -- neither is reachable in this worktree, see Gate A
below): one bar's price return, sign-flipped whenever volume rose over the
same bar. A volume increase on an up bar reads as a reversal signal (negative
output); a volume increase on a down bar reads as the opposite.

Gate A. The Kakushadze (2016) paper text and the vnpy `alpha101` repository
are NOT consulted or available in this worktree (no web access, `docs/pine`
unavailable); this is ported from the issue's own restatement of Alpha#12 --
"sign(delta(volume,1)) * -delta(close,1)" -- which is also exactly the
expression the local Gate E screen prototype computes
(`docs/issues/screen/ind_screen.py:214`, `return np.sign(delta(v, 1)) *
-ret(c)`, where `ret(c) = c / c.shift(1) - 1`, `ind_screen.py:108`). Unlike
`osap_lrrev`/`osap_mrrev`/`osap_intmom`, no derivation or unit-conversion
assumption is needed here: both operators translate literally --
`delta(x, 1)` is `x.diff(1)`, `sign(x)` is `np.sign(x)` -- and the ONE
substitution is the scale-free conversion stated explicitly by the issue and
the candidates.csv row's own `conv` field: "delta(close,1) -> one-bar
return", i.e. the raw price difference `delta(close, 1)` is replaced by the
dimensionless return `close.pct_change(1)` so the column does not scale with
price level. This remains unconfirmed against the primary Kakushadze paper
text itself, which this worktree cannot reach.

Calculation:
    RET = Close / Close.shift(1) - 1
    VSR = sign(Volume.diff(1)) * -RET

Args:
    close (pd.Series): Series of 'close's
    volume (pd.Series): Series of 'volume's
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.Series: VSR, a scale-free (dimensionless) column taking values in
        [-1, 1] * |one-bar return| (it is a return magnitude multiplied by
        -1, 0 or 1). NaN for the first bar only.
"""
