# -*- coding: utf-8 -*-
"""Range EMA over its own EMA (single mass-index ratio) -- Guotai Junan's
(2017, "GTJA191", internal quant report, read via the HKUDS/Vibe-Trading
copy, MIT) alpha `#109`, per issue #76. Source cited by the issue:

    #109: SMA(H-L,10,2) / SMA(SMA(H-L,10,2),10,2)

**What this session could NOT do, disclosed up front:** `docs/pine/` and web
access are both unavailable in this worktree, so the issue's own named copy
-- HKUDS/Vibe-Trading (MIT) -- was never read. The formula below is taken
directly from the issue's own stated text, per the issue's own instruction
("Gate A starts from the source formula, not the prototype"), then
cross-checked against the issue's own prototype
(`docs/issues/screen/ind_screen.py:452-456`):

    @cand("g191_109", "range EMA over its own EMA (single mass-index ratio)", G,
          "#109: SMA(H-L,10,2) / SMA(SMA(H-L,10,2),10,2)")
    def _(o, h, l, c, v):
        e = sma(h - l, 10, 2)
        return sdiv(e, sma(e, 10, 2))

No disclosed interpretation choice was needed -- the issue's own string and
the prototype agree exactly, including both window lengths/weights. Unlike
every other ratio-form `g191_*` port in this fork (`g191_023`, `g191_111`,
...), this candidate's own `candidates.csv` row carries NO `conv` field (an
empty cell, `docs/issues/screen/candidates.csv:46`) -- there is no extra
scale-free conversion to apply, because the ratio of a quantity to its OWN
recursive smoothing is already scale-free by construction (derived below).

OPERATORS, each read directly off the prototype's own (unambiguous) module
source, the same source every other `g191_*` port in this fork relies on:

* `H`, `L` = high, low. No other OHLCV field is read.
* `SMA(A, n, m)` is GTJA's own recursive smoother, NOT this fork's
  `pandas_ta.overlap.sma` (a plain simple moving average) -- a name
  collision the issue's source report shares with every other GTJA191
  alpha, called out explicitly in the prototype's own docstring
  (`ind_screen.py:57-59`): `Y[t] = (m*A[t] + (n-m)*Y[t-1]) / n`, an
  exponential moving average with `alpha = m/n`. Implemented here as
  `A.ewm(alpha=m/n, adjust=False, min_periods=n).mean()`, the same
  implementation and `min_periods=length` masking convention every sibling
  `g191_*` port ships for the identical GTJA `SMA` operator -- applied
  TWICE here, the SECOND time on the OUTPUT of the first (CHAINED, unlike
  `g191_111`'s two `SMA`s applied in PARALLEL to the same input).
* The prototype's own `sdiv` (`ind_screen.py:41-42`, `_fin(a / b)`)
  replaces `+-inf` with `NaN` on the final division.

CALCULATION, in the order computed below (defaults
`smooth1_length=10, smooth1_weight=2, smooth2_length=10, smooth2_weight=2`):
    e        = SMA(H - L, smooth1_length, smooth1_weight)
    s        = SMA(e, smooth2_length, smooth2_weight)
    G191_109 = e / s, inf -> NaN

CAUSALITY. `H[t] - L[t]` is pointwise, reading no bar past `t`. Each GTJA
`SMA`'s recursion reads only its own input at `t` and its own PRIOR value at
each step, so by induction `e[t]` is a function of `(H-L)[0..t]` only, and
`s[t]` (an SMA OF `e`) is in turn a function of `e[0..t]`, hence of
`(H-L)[0..t]` only. The final ratio is pointwise on two already-backward-
looking series. Nothing in the chain is shifted forward anywhere.
`tests/test_g191_109.py` proves this both by future-perturbation (real
module: 0 leaks over a synthetic walk, swept past the warm-up) and by two
independent mutants (`importlib` source read, `exec`'d in memory), each
shown live (differs from the real module) and then caught at every offset
past the warm-up: shifting the final write index `smooth2_length` bars into
the future, and computing `e` from `H.shift(-1) - L.shift(-1)` (one bar of
look-ahead folded into the range BEFORE smoothing) -- the same `bos`
look-ahead bug class CLAUDE.md documents.

WARM-UP. `e` needs `smooth1_length` valid `(H-L)` values (`min_periods=10`
on the GTJA `SMA`'s underlying `.ewm()`; an `H==L` tie does not create a
NaN here, since `H-L=0` is a perfectly valid float, so for ordinary OHLC
data `e` is defined from `t >= smooth1_length - 1`). `s` is an SMA OF `e`
itself, so it needs `smooth2_length` valid `e` values AFTER `e` starts,
hence `s` (and the result) is defined from `t >= (smooth1_length - 1) +
(smooth2_length - 1)` -- `min_length = smooth1_length + smooth2_length - 1`
= **19** bars at the shipped defaults, enforced by `verify_series`, the
same chained-smoother warm-up arithmetic `g191_174` uses for its
STD-then-SMA chain.

SCALE-FREE. Let `k > 0` rescale price (`H, L -> k*H, k*L`). `H - L -> k*(H
- L)` (linear in a positive scalar). The GTJA `SMA` recursion is linear in
a positive scalar multiple of its input, so `e -> k*e`; applying the SAME
linear recursion to `e` gives `s -> k*s`. The final ratio `e/s -> (k*e) /
(k*s) = e/s` for ANY `k > 0` -- the `k` cancels EXACTLY, with no extra
division needed, because both numerator and denominator are built from the
SAME underlying series by the SAME linear operator at two different speeds
(this is why the prototype's own `candidates.csv` row carries no `conv`
field). Measured on a synthetic walk: PRICE x8/x64 land bit-identical
(power-of-two multiplication is exact in IEEE754, so the algebraic
cancellation is also exact in float64), while x10/x3.7 come out within
float64 rounding tolerance of the unscaled column. Measured in the test
file and `docs/measure_g191_109.py`, not merely asserted.
"""
import numpy as np

from pandas_ta.utils import get_offset, verify_series


def _gtja_sma(series, n, m):
    """GTJA SMA(A,n,m): Y = (m*A + (n-m)*Y[-1]) / n, an EMA with alpha m/n."""
    return series.ewm(alpha=m / n, adjust=False, min_periods=n).mean()


def g191_109(high, low, smooth1_length=None, smooth1_weight=None,
             smooth2_length=None, smooth2_weight=None, offset=None, **kwargs):
    """Indicator: Range EMA over its own EMA (G191_109)"""
    # Validate Arguments
    smooth1_length = int(smooth1_length) if smooth1_length and smooth1_length > 0 else 10
    smooth1_weight = int(smooth1_weight) if smooth1_weight and smooth1_weight > 0 else 2
    smooth2_length = int(smooth2_length) if smooth2_length and smooth2_length > 0 else 10
    smooth2_weight = int(smooth2_weight) if smooth2_weight and smooth2_weight > 0 else 2
    min_length = smooth1_length + smooth2_length - 1
    high = verify_series(high, min_length)
    low = verify_series(low, min_length)
    offset = get_offset(offset)

    if high is None or low is None:
        return

    # Calculate Result
    e = _gtja_sma(high - low, smooth1_length, smooth1_weight)
    s = _gtja_sma(e, smooth2_length, smooth2_weight)
    result = (e / s).replace([np.inf, -np.inf], np.nan)

    # Offset
    if offset != 0:
        result = result.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        result.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        result.fillna(method=kwargs["fill_method"], inplace=True)

    # Name & Category
    result.name = (
        f"G191_109_{smooth1_length}_{smooth1_weight}_{smooth2_length}_{smooth2_weight}"
    )
    result.category = "volatility"

    return result


g191_109.__doc__ = \
"""Range EMA over its own EMA (G191_109)

Guotai Junan's (2017, "GTJA191") alpha `#109`, per issue #76. The trailing
daily range (`high - low`) smoothed with GTJA's own recursive `SMA`, divided
by a SECOND application of the same recursive `SMA` to that smoothed range
-- a single mass-index-style ratio of a quantity to its own further-smoothed
self. Full Gate A derivation, causality and scale-free arguments are in the
module source above; see docs/G191109Measured.md for the measured numbers.

Calculation:
    Default Inputs:
        smooth1_length=10, smooth1_weight=2, smooth2_length=10, smooth2_weight=2
    e        = SMA(high - low, smooth1_length, smooth1_weight)  # GTJA SMA, ewm(alpha=smooth1_weight/smooth1_length)
    s        = SMA(e, smooth2_length, smooth2_weight)           # GTJA SMA, ewm(alpha=smooth2_weight/smooth2_length)
    G191_109 = e / s, inf -> NaN

Args:
    high (pd.Series): Series of 'high's
    low (pd.Series): Series of 'low's
    smooth1_length (int): GTJA SMA length for the first (range) smoother. Default: 10
    smooth1_weight (int): GTJA SMA weight for the first smoother -- GTJA's own
        `m` is always a small positive integer, matching the prototype. Default: 2
    smooth2_length (int): GTJA SMA length for the second (EMA-of-EMA) smoother. Default: 10
    smooth2_weight (int): GTJA SMA weight for the second smoother. Default: 2
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.Series: G191_109_{smooth1_length}_{smooth1_weight}_{smooth2_length}_
        {smooth2_weight}, a scale-free (dimensionless) column. NaN for at
        least the first `smooth1_length + smooth2_length - 2` bars (18 at
        the shipped defaults).
"""
