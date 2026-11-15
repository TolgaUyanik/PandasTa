# -*- coding: utf-8 -*-
"""Volume-low correlation plus mid-to-close gap -- Guotai Junan's (2017,
"GTJA191", internal quant report, read via the HKUDS/Vibe-Trading copy, MIT)
alpha `#191`, per issue #53. Source cited by the issue:

    #191: (CORR(MEAN(V,20), L, 5) + (H+L)/2) - C

**What this session could NOT do, disclosed up front:** `docs/pine/` and web
access are both unavailable in this worktree, so the issue's own named copy
-- HKUDS/Vibe-Trading (MIT) -- was never read. The formula below is derived
from the issue's own stated text (which is itself a quote of the GTJA191
report), per the issue's own instruction ("Gate A starts from the source
formula, not the prototype").

GATE A -- DERIVATION. Addition/subtraction associate freely, so the raw
formula's grouping is cosmetic:

    (CORR(MEAN(V,20), L, 5) + (H+L)/2) - C
        = CORR(MEAN(V,20), L, 5) + ((H+L)/2 - C)

`CORR(MEAN(V,20), L, 5)` is already unitless (a Pearson correlation), but
`(H+L)/2 - C` is a price difference -- not scale-free. The issue's own
candidate record (`docs/issues/screen/candidates.csv`, row `g191_191`) notes
the conversion applied before Gate E ever ran: `conv = "price terms
/close"`. The issue's own prototype (`docs/issues/screen/ind_screen.py:584`)
spells out the identical scale-free form directly:

    corr(mean(v, 20), l, 5) + ((h + l) / 2 - c) / c

so this port divides ONLY the price-difference term by `C`, leaving the
already-unitless correlation term untouched:

    G191_191 = CORR(MEAN(V,20), L, 5) + ((H+L)/2 - C) / C

OPERATORS, each read directly off the prototype's own (unambiguous) module
docstring, the same source g191_146 (issue #52) relied on for `SMA`/`MEAN`/
`ret` -- no disclosed ASSUMPTION needed:

* `MEAN(X, n)` = a trailing `n`-bar rolling mean, `X.rolling(n).mean()`.
  Matches the prototype's own `mean(x, n): return x.rolling(n).mean()`.
* `CORR(X, Y, n)` = a trailing `n`-bar rolling Pearson correlation,
  `X.rolling(n).corr(Y)`. Matches the prototype's own
  `corr(x, y, n): return _fin(x.rolling(n).corr(y))` (`_fin` replaces
  `[inf, -inf]` with `NaN`; this port applies the same replacement to its
  own division by `C`, for the symmetric reason: a near-zero `C` would
  otherwise produce `+-inf` rather than a defined number).
* `H`, `L`, `C`, `V` = high, low, close, volume.

CALCULATION, in the order computed below:
    mean_v    = MEAN(V, mean_length)                 # mean_length=20
    corr_term = CORR(mean_v, L, corr_length)          # corr_length=5
    gap_term  = ((H + L) / 2 - C) / C
    G191_191  = corr_term + gap_term, inf -> NaN

CAUSALITY. `mean_v[t]` is a trailing rolling mean of `V[t-mean_length+1..t]`,
reading no bar past `t`. `corr_term[t]` is a trailing rolling Pearson
correlation of `mean_v[t-corr_length+1..t]` against `L[t-corr_length+1..t]`,
again reading no bar past `t` -- by induction on `mean_v`, a function of
`V[0..t]` and `L[0..t]` only. `gap_term[t]` is pointwise in `H[t]`, `L[t]`,
`C[t]`. Nothing is shifted forward anywhere in the chain.
`tests/test_g191_191.py` proves this both by future-perturbation and by two
independent mutants (`importlib` source read, `exec`'d in memory), each
shown live (differs from the real module) and then caught at every offset
past the warm-up: shifting the final write index `corr_length` bars into the
future, and computing `MEAN(V, mean_length)` with `center=True` instead of
the causal trailing window -- the same look-ahead bug class CLAUDE.md
documents for `bos`'s `rolling(..., center=True)`.

SCALE-FREE. Pearson correlation is exactly invariant to a positive rescale
of either input: for any `k > 0`, `corr(k*X, Y) = corr(X, Y)` and
`corr(X, k*Y) = corr(X, Y)` algebraically (the `k` cancels between the
covariance and the standard-deviation terms). Rescaling `V` by `k` rescales
`mean_v` by the same `k` (linearity of the rolling mean), so `corr_term` is
untouched under ANY positive volume rescale. Rescaling `H`, `L`, `C` by `k`
leaves `corr_term` untouched (its inputs, `mean_v` and `L`, only `L` moves,
and correlation absorbs that) and leaves `gap_term` untouched too:
`((k*H + k*L)/2 - k*C) / (k*C) = ((H+L)/2 - C) / C`, the `k` cancels
algebraically. Measured on a synthetic frame: `x8`/`x64` land bit-identical
for BOTH price and volume rescales (power-of-two multiplication is exact in
IEEE754, so the algebraic cancellation is also exact in float64), while
`x10`/`x3.7` come out within float64 rounding tolerance of the unscaled
column. Measured in the test file and `docs/measure_g191_191.py`, not merely
asserted.
"""
import numpy as np
from pandas import Series

from pandas_ta.utils import get_offset, verify_series


def g191_191(high, low, close, volume, mean_length=None, corr_length=None,
             offset=None, **kwargs):
    """Indicator: Volume-Low Correlation Plus Mid-to-Close Gap (G191_191)"""
    # Validate Arguments
    mean_length = int(mean_length) if mean_length and mean_length > 0 else 20
    corr_length = int(corr_length) if corr_length and corr_length > 1 else 5
    min_length = mean_length + corr_length - 1
    high = verify_series(high, min_length)
    low = verify_series(low, min_length)
    close = verify_series(close, min_length)
    volume = verify_series(volume, min_length)
    offset = get_offset(offset)

    if high is None or low is None or close is None or volume is None:
        return

    # Calculate Result
    mean_v = volume.rolling(mean_length).mean()
    corr_term = mean_v.rolling(corr_length, min_periods=corr_length).corr(low)
    gap_term = ((high + low) / 2.0 - close) / close

    result = corr_term + gap_term
    mask = corr_term.notna() & gap_term.notna()
    result = result.where(mask).replace([np.inf, -np.inf], np.nan)

    # Offset
    if offset != 0:
        result = result.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        result.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        result.fillna(method=kwargs["fill_method"], inplace=True)

    # Name & Category
    result.name = f"G191_191_{mean_length}_{corr_length}"
    result.category = "volume"

    return result


g191_191.__doc__ = \
"""Volume-Low Correlation Plus Mid-to-Close Gap (G191_191)

Guotai Junan's (2017, "GTJA191") alpha `#191`, per issue #53. A rolling
Pearson correlation between the 20-bar mean of volume and the low price,
added to the (scale-free) distance between the bar's own midpoint and its
close: a persistent positive correlation between participation and the low
means volume has been confirming new lows, pushed up or down by how far the
close sits from the bar's own midpoint. Full Gate A derivation, causality
and scale-free arguments are in the module source above; see
docs/G191191Measured.md for the measured numbers.

Calculation:
    Default Inputs:
        mean_length=20, corr_length=5
    mean_v    = MEAN(volume, mean_length)
    corr_term = CORR(mean_v, low, corr_length)
    gap_term  = ((high + low) / 2 - close) / close
    G191_191  = corr_term + gap_term, inf -> NaN

Args:
    high (pd.Series): Series of 'high's
    low (pd.Series): Series of 'low's
    close (pd.Series): Series of 'close's
    volume (pd.Series): Series of 'volume's
    mean_length (int): Rolling window for the volume mean. Default: 20
    corr_length (int): Rolling window for the correlation. Default: 5
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.Series: G191_191_{mean_length}_{corr_length}, a scale-free
        (dimensionless) column: a correlation in `[-1, 1]` plus a small
        price-relative gap term. NaN for the first
        mean_length + corr_length - 2 bars.
"""
