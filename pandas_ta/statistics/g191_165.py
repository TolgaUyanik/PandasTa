# -*- coding: utf-8 -*-
"""Rescaled range R/S (48) -- Guotai Junan's (2017, "GTJA191", internal
quant report, read via the HKUDS/Vibe-Trading copy, MIT) alpha `#165`, per
issue #55. Source cited by the issue:

    #165: MAX(SUMAC(C-MEAN(C,48))) - MIN(SUMAC(C-MEAN(C,48))) / STD(C,48)

**What this session could NOT do, disclosed up front:** `docs/pine/` and web
access are both unavailable in this worktree, so the issue's own named copy
-- HKUDS/Vibe-Trading (MIT) -- was never read. The formula below is derived
from the issue's own stated text, per the issue's own instruction ("Gate A
starts from the source formula, not the prototype").

GATE A -- DERIVATION. The issue's own parenthetical already flags the
formula's precedence as ambiguous and tells the reader how to resolve it:
"scale-free form: read as (MAX-MIN)/STD, the R/S statistic; the literal
precedence is price-unit". Reading it that way names the quantity exactly:
the classical rescaled-range (R/S) statistic (Hurst 1951) over a trailing
`length`-bar window --

    m   = mean(window)
    d_i = window_i - m,            i = 0..length-1
    Z_i = cumsum(d)_i               (running sum WITHIN the window, reset
                                      at every window boundary -- the window
                                      is the unit the statistic is defined
                                      over, matching the issue's own "R/S
                                      statistic" naming, not a running sum
                                      over the whole history)
    R   = max(Z) - min(Z)
    S   = std(window)
    G191_165 = R / S

Two sub-choices the literal text leaves open, each resolved below with its
reasoning (not a silent guess):

1. **Is `SUMAC` window-local or global?** The issue's own parenthetical names
   the target as "the R/S statistic" -- a term with one standard textbook
   definition, and that definition resets the cumulative sum at the start of
   EACH window (`Z_0 = d_0`, not carried over from the previous window). A
   global, never-reset cumsum would not be "the R/S statistic" by that name;
   it would be an unbounded running quantity with no textbook name in this
   context. The issue's own prototype (`docs/issues/screen/ind_screen.py:159-
   163`, `w_rescaled_range`) independently reaches the same reading: it
   windows the series first (`roll(c, 48, w_rescaled_range)`,
   `ind_screen.py:530`) and cumsum's only inside each window
   (`Z = np.cumsum(W - W.mean(1, keepdims=True), 1)`). Two independent reads
   of the same ambiguous text agree, so this port uses the window-local
   reading.
2. **`STD`'s ddof.** The sibling GTJA191 port that actually invokes a `STD`
   operator in its own formula, `g191_076` (`STD(|C/C1-1|/V,20) /
   MEAN(|C/C1-1|/V,20)`), cites the prototype's own GENERIC `std` operator,
   `ind_screen.py:48` (`def std(x, n): return x.rolling(n).std()`, pandas'
   default `ddof=1`, a SAMPLE standard deviation), as the GTJA `STD(...)`
   spelling -- that is the operator the issue's formula string itself
   invokes by name (`STD(C,48)`). (`g191_146` and `g191_191`'s own formulas
   never invoke `STD` at all, so they are silent on this question, not
   corroborating witnesses -- this is a one-port precedent, not a fork-wide
   one.) The prototype's `w_rescaled_range` helper does NOT call that
   generic operator for its own denominator; it recomputes the window's std
   inline with plain numpy (`W.std(1)`, numpy's default `ddof=0`, a
   POPULATION standard deviation) -- a vectorisation shortcut local to that
   one screening function's implementation, never restated anywhere as what
   GTJA's `STD` means. Per the issue's own instruction ("Gate A starts from
   the source formula, not the prototype"), this port uses the operator the
   FORMULA names (`ddof=1`, matching `g191_076`'s own `STD`), not the one
   the screening helper happened to take a numeric shortcut with. The two
   conventions differ only by the factor `sqrt((length-1)/length)`
   (measured `sqrt(47/48) = 0.989529` at the shipped default) -- a small,
   constant rescale, not a shape change; see `docs/G191165Measured.md` for
   the measured size of this choice.

CALCULATION, in the order computed below (`length=48`):
    for each window of `length` consecutive closes ending at bar `t`:
        m        = mean(window)
        Z        = cumsum(window - m)              # window-local, resets each window
        R        = max(Z) - min(Z)
        S        = std(window, ddof=1)              # pandas-default sample std, matching STD(C,48)
        G191_165[t] = R / S, 0/0 -> NaN (a constant window makes both R and S zero)

CAUSALITY. Each window ending at `t` reads only `close[t-length+1 .. t]`;
`m`, `Z`, `R`, `S` are all pure functions of that window's own values, and the
result is written to the window's OWN last bar, `t`. Nothing is shifted
forward anywhere in the chain. `tests/test_g191_165.py` proves this both by
future-perturbation and by two independent mutants (`importlib` source read,
`exec`'d in memory), each shown live (differs from the real module) and then
caught at every offset past the warm-up: shifting the whole write index
`length` bars into the future, and writing each window's result to its
CENTER bar (`(length-1)//2` bars in from the window start) instead of its
last bar -- the same look-ahead bug class CLAUDE.md documents for `bos`'s
`rolling(..., center=True)`, expressed here as a write-index shift because
this module does not use pandas' `rolling(center=True)` at all.

SCALE-FREE. Under a positive rescale of `close` by any constant `k`: every
window value scales by `k`, so its mean scales by `k`, every deviation
`d_i = window_i - m` scales by `k` (the `k` is linear and distributes over
the subtraction), every partial sum `Z_i` scales by `k` (cumsum is linear),
so `R = max(Z) - min(Z)` scales by `k`. `S = std(window, ddof=1)` is also
exactly linear in a positive scalar multiple of its input
(`std(k*X) = k * std(X)` for `k > 0`). The ratio `R / S` therefore has the
`k` cancel algebraically, for ANY `k > 0` -- not a coincidence of this
formula's shape, a mathematical certainty. Measured on a synthetic walk:
`x8`/`x64` land bit-identical (power-of-two multiplication is exact in
IEEE754, so the algebraic cancellation is also exact in float64), while
`x10`/`x3.7` come out within float64 rounding tolerance of the unscaled
column. Measured in the test file and `docs/measure_g191_165.py`, not merely
asserted.
"""
import numpy as np
import pandas as pd
from numpy.lib.stride_tricks import sliding_window_view

from pandas_ta.utils import get_offset, verify_series


def g191_165(close, length=None, offset=None, **kwargs):
    """Indicator: Rescaled Range R/S (G191_165)"""
    # Validate Arguments
    length = int(length) if length and length > 1 else 48
    close = verify_series(close, length)
    offset = get_offset(offset)

    if close is None:
        return

    # Calculate Result
    a = close.to_numpy(dtype=float)
    n = len(a)
    out = np.full(n, np.nan)
    if n >= length:
        W = sliding_window_view(a, length)  # (n-length+1, length) causal windows, oldest first
        dev = W - W.mean(axis=1, keepdims=True)
        z = np.cumsum(dev, axis=1)
        rs_range = z.max(axis=1) - z.min(axis=1)
        std_w = W.std(axis=1, ddof=1)
        with np.errstate(invalid="ignore", divide="ignore"):
            rs = rs_range / std_w
        out[length - 1:] = rs

    result = pd.Series(out, index=close.index)

    # Offset
    if offset != 0:
        result = result.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        result.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        result.fillna(method=kwargs["fill_method"], inplace=True)

    # Name & Category
    result.name = f"G191_165_{length}"
    result.category = "statistics"

    return result


g191_165.__doc__ = \
"""Rescaled Range R/S (G191_165)

Guotai Junan's (2017, "GTJA191") alpha `#165`, per issue #55. The classical
rescaled-range (R/S) statistic (Hurst 1951) over a trailing window: the
range of the window's own running sum of deviations from its own mean,
divided by the window's own standard deviation -- a scale-free read on how
far a window's cumulative drift wanders relative to its own dispersion,
the seed statistic behind Hurst-exponent estimation. Full Gate A derivation
(including the two disclosed interpretation choices this issue's own
ambiguous formula text requires), causality and scale-free arguments are in
the module source above; see docs/G191165Measured.md for the measured
numbers.

Calculation:
    Default Inputs:
        length=48
    for each trailing window W of `length` closes ending at bar t:
        m  = mean(W)
        Z  = cumsum(W - m)            # resets at each window
        R  = max(Z) - min(Z)
        S  = STDEV(W)                 # ddof=1, pandas default
        G191_165[t] = R / S, 0/0 -> NaN

Args:
    close (pd.Series): Series of 'close's
    length (int): Rolling window for the R/S statistic. Default: 48
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.Series: G191_165_{length}, a scale-free (dimensionless) column,
        non-negative (a ratio of a range to a standard deviation). NaN for
        the first `length - 1` bars.
"""
