# -*- coding: utf-8 -*-
"""Variability of return-per-volume -- Guotai Junan's (2017, "GTJA191",
internal quant report, read via the HKUDS/Vibe-Trading copy, MIT) alpha
`#76`, per issue #54. Source cited by the issue:

    #76: STD(|C/C1-1|/V,20) / MEAN(|C/C1-1|/V,20)

**What this session could NOT do, disclosed up front:** `docs/pine/` and web
access are both unavailable in this worktree, so the issue's own named copy
-- HKUDS/Vibe-Trading (MIT) -- was never read. The formula below is taken
directly from the issue's own stated text, per the issue's own instruction
("Gate A starts from the source formula, not the prototype").

GATE A -- DERIVATION. The formula is already a single ratio -- a rolling
coefficient of variation of `X = |C/C1-1| / V` -- so there is no grouping to
resolve, unlike `g191_191`'s `+`/`-` chain. `C1` denotes `C` delayed one bar
(`close.shift(1)`), the issue's own GTJA notation, matching the prototype's
own `delay(x, n) = x.shift(n)` and `ret(c) = c / c.shift(1) - 1`.

OPERATORS, each read directly off the prototype's own (unambiguous) module
code (`docs/issues/screen/ind_screen.py`), the same source `g191_146` and
`g191_191` relied on for `MEAN`/`STD`/`ret` -- no disclosed ASSUMPTION
needed:

* `ret(c)` = `c / c.shift(1) - 1`, the one-bar simple return
  (`ind_screen.py:108`).
* `STD(X, n)` = a trailing `n`-bar rolling sample standard deviation,
  `X.rolling(n).std()` -- pandas default `ddof=1` (`ind_screen.py:48`,
  `def std(x, n): return x.rolling(n).std()`).
* `MEAN(X, n)` = a trailing `n`-bar rolling mean, `X.rolling(n).mean()`
  (`ind_screen.py:47`).
* `sdiv(a, b)` = `(a / b).replace([inf, -inf], nan)` (`ind_screen.py:41-42`).
  The prototype's own candidate function (`ind_screen.py:419-423`,
  `cand("g191_076", ...)`) wraps BOTH divisions in the formula with `sdiv`,
  not bare `/`: `x = sdiv(ret(c).abs(), v)` then
  `return sdiv(std(x, 20), mean(x, 20))`. This port reuses that guard at
  both divisions for the identical reason -- a zero-volume bar would
  otherwise make `X` `+-inf` rather than a defined number, and a
  zero-variance-free window (`MEAN(X, n) == 0`) would otherwise make the
  output `+-inf` too -- not a guess, read directly off the prototype's own
  function body, which is plain code, not prose open to interpretation.

CALCULATION, in the order computed below:
    ret_c  = C / C1 - 1, C1 = C.shift(1)
    x      = |ret_c| / V, inf -> NaN
    std_x  = STD(x, length)       # length=20
    mean_x = MEAN(x, length)
    G191_076 = std_x / mean_x, inf -> NaN

CAUSALITY. `ret_c[t]` reads `C[t]` and `C[t-1]` only. `x[t]` is pointwise in
`ret_c[t]` and `V[t]`. `std_x[t]` and `mean_x[t]` are trailing rolling
statistics of `x[t-length+1..t]`, reading no bar past `t` -- by induction on
`x`, a function of `C[0..t]` and `V[0..t]` only. Nothing is shifted forward
anywhere in the chain. `tests/test_g191_076.py` proves this both by
future-perturbation and by two independent mutants (`importlib` source read,
`exec`'d in memory), each shown live (differs from the real module) and then
caught at every offset past the warm-up: shifting the final write index
`length` bars into the future, and computing `STD`/`MEAN` with
`center=True` instead of the causal trailing window -- the same look-ahead
bug class CLAUDE.md documents for `bos`'s `rolling(..., center=True)`.

SCALE-FREE. `ret_c` is exactly scale-free under a positive rescale of
`close`: `(k*C)/(k*C1) - 1 = C/C1 - 1` algebraically, the `k` cancels inside
the division itself (the price scale never reaches `std_x`/`mean_x` at all).
`x = |ret_c| / V` scales by `1/k` under a positive volume rescale `V -> k*V`
(`ret_c` is untouched by a volume rescale); `std_x` and `mean_x` are both
linear in a positive scalar multiple of their input (`STD(k*X, n) = k *
STD(X, n)`, `MEAN(k*X, n) = k * MEAN(X, n)` for `k > 0`), so the ratio
`std_x / mean_x` is exactly invariant: the `1/k` cancels between numerator
and denominator algebraically, for ANY `k > 0`, not merely a coincidence of
this particular formula's shape. Measured on a synthetic frame: `x8`/`x64`
land bit-identical for BOTH price and volume rescales (power-of-two
multiplication is exact in IEEE754, so the algebraic cancellation is also
exact in float64), while `x10`/`x3.7` come out within float64 rounding
tolerance of the unscaled column. Measured in the test file and
`docs/measure_g191_076.py`, not merely asserted.
"""
import numpy as np

from pandas_ta.utils import get_offset, verify_series


def g191_076(close, volume, length=None, offset=None, **kwargs):
    """Indicator: Variability of Return-Per-Volume (G191_076)"""
    # Validate Arguments
    length = int(length) if length and length > 1 else 20
    min_length = length + 1
    close = verify_series(close, min_length)
    volume = verify_series(volume, min_length)
    offset = get_offset(offset)

    if close is None or volume is None:
        return

    # Calculate Result
    ret_c = close / close.shift(1) - 1.0
    x = (ret_c.abs() / volume).replace([np.inf, -np.inf], np.nan)
    std_x = x.rolling(length).std()
    mean_x = x.rolling(length).mean()
    result = (std_x / mean_x).replace([np.inf, -np.inf], np.nan)

    # Offset
    if offset != 0:
        result = result.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        result.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        result.fillna(method=kwargs["fill_method"], inplace=True)

    # Name & Category
    result.name = f"G191_076_{length}"
    result.category = "volume"

    return result


g191_076.__doc__ = \
"""Variability of Return-Per-Volume (G191_076)

Guotai Junan's (2017, "GTJA191") alpha `#76`, per issue #54. The rolling
coefficient of variation (STD / MEAN) of the absolute one-bar return divided
by volume: how erratic the "price impact per unit of volume" has been over
the last `length` bars, as opposed to its average level. Full Gate A
derivation, causality and scale-free arguments are in the module source
above; see docs/G191076Measured.md for the measured numbers.

Calculation:
    Default Inputs:
        length=20
    ret_c    = close / close.shift(1) - 1
    x        = |ret_c| / volume, inf -> NaN
    std_x    = STDEV(x, length)   # ddof=1, pandas default
    mean_x   = SMA(x, length)
    G191_076 = std_x / mean_x, inf -> NaN

Args:
    close (pd.Series): Series of 'close's
    volume (pd.Series): Series of 'volume's
    length (int): Rolling window for both STD and MEAN. Default: 20
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.Series: G191_076_{length}, a scale-free (dimensionless) column: a
        coefficient of variation, non-negative. NaN for the first `length`
        bars.
"""
