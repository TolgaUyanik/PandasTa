# -*- coding: utf-8 -*-
"""Return-innovation momentum -- Guotai Junan's (2017, "GTJA191", internal
quant report, read via the HKUDS/Vibe-Trading copy, MIT) alpha `#146`, per
issue #52. Source cited by the issue:

    #146: MEAN(r - SMA(r,61,2), 20) * (r - SMA(r,61,2)) / SMA((r - SMA(r,61,2))^2, 60, 2)

**What this session could NOT do, disclosed up front:** `docs/pine/` and web
access are both unavailable in this worktree, so the issue's own named copy
-- HKUDS/Vibe-Trading (MIT) -- was never read. The formula below is derived
from the issue's own stated text (which is itself a quote of the GTJA191
report), per the issue's own instruction ("Gate A starts from the source
formula, not the prototype").

OPERATORS, each read directly off the formula string -- none needs a
disclosed ASSUMPTION, because the issue's own prototype
(`docs/issues/screen/ind_screen.py`) spells out GTJA's `SMA` convention
verbatim in its own docstring, and this port reuses that spelling, not an
independent guess:

* `r` = the daily simple return, `close / close.shift(1) - 1`. Matches the
  prototype's own `ret(c): c / c.shift(1) - 1`.
* `SMA(A, n, m)` is GTJA's own recursive smoother, NOT this fork's
  `pandas_ta.overlap.sma` (a plain simple moving average) -- a name
  collision the issue's source report shares with every other GTJA191
  alpha, and one the prototype's own docstring calls out explicitly:
  `Y[t] = (m*A[t] + (n-m)*Y[t-1]) / n`, an exponential moving average with
  `alpha = m/n`. Implemented here as `A.ewm(alpha=m/n, adjust=False,
  min_periods=n).mean()`: `adjust=False` reproduces the recursion exactly
  (pandas' default `adjust=True` instead computes a different,
  non-recursive weighted average over the whole history), and
  `min_periods=n` masks the first `n-1` bars, where the recursion has not
  yet seen enough of `A` to be anything other than dominated by its own
  seed value -- the same `min_periods=length` convention this fork's own
  `pandas_ta.overlap.rma`/`wilder_rma` already use for their own
  `ewm(alpha=...)` calls.
* `MEAN(x, d)` = a trailing `d`-bar rolling mean, `x.rolling(d).mean()`.
  Matches the prototype's own `mean(x, n): return x.rolling(n).mean()`.
* Division: a near-zero `SMA(e^2, 60, 2)` (near-constant `close`) makes the
  final ratio `+-inf`; mapped to `NaN`, matching the prototype's own
  `sdiv(a, b): return _fin(a / b)` (`_fin` replaces `[inf, -inf]` with
  `NaN`).

CALCULATION, in the order computed below:
    r   = close / close.shift(1) - 1
    s1  = SMA(r, smooth1_length, smooth1_weight)        # smooth1_length=61, smooth1_weight=2
    e   = r - s1
    m20 = MEAN(e, mean_length)                           # mean_length=20
    s2  = SMA(e**2, smooth2_length, smooth2_weight)      # smooth2_length=60, smooth2_weight=2
    G191_146 = (m20 * e) / s2, inf -> NaN

CAUSALITY. `r` reads `close[t]` and `close[t-1]`. `s1[t]` is GTJA's own
recursive EMA, `s1[t] = (m*r[t] + (n-m)*s1[t-1]) / n`: each step reads only
`r[t]` and its own PRIOR value `s1[t-1]`, so by induction `s1[t]` is a
function of `r[0..t]` only. `e[t] = r[t] - s1[t]` reads no bar past `t`.
`m20[t]` is a trailing rolling mean of `e[t-19..t]`. `s2[t]` is the same
GTJA recursion applied to `e[t]**2`, so by the same induction it is a
function of `e[0..t]**2` only. The final ratio is pointwise on three
already-backward-looking series. Nothing is shifted forward anywhere in the
chain. `tests/test_g191_146.py` proves this both by future-perturbation and
by two independent mutants (`importlib` source read, `exec`'d in memory),
each shown live (differs from the real module) and then caught at every
offset past the warm-up: shifting the final write index
`smooth2_length=60` bars into the future, and computing `MEAN(e,
mean_length)` with `center=True` instead of the causal trailing window --
the same look-ahead bug class CLAUDE.md documents for `bos`'s
`rolling(..., center=True)`.

SCALE-FREE. `r[t] = close[t]/close[t-1] - 1` is EXACTLY unchanged under a
positive rescale of `close` by any constant `k`: `(k*close[t])/(k*close[t-1])
- 1 = close[t]/close[t-1] - 1`, the `k` cancels algebraically. Since `r`
itself is untouched, every downstream term (`s1`, `e`, `m20`, `s2`, the
final ratio) is also untouched -- a mathematical certainty for ANY positive
`k`. Measured on a synthetic walk: `x8`/`x64` land bit-identical (power-of-
two multiplication is exact in IEEE754, so the cancellation is also exact in
floating point), while `x10`/`x3.7` come out within `~8e-15` of the
unscaled column -- float64 rounding in the division chain, not a scale
dependency (the two measured diffs are of the same order as machine
epsilon times the operand magnitudes). Measured in the test file and
`docs/measure_g191_146.py`, not merely asserted.
"""
import numpy as np
from pandas import Series

from pandas_ta.utils import get_offset, verify_series


def g191_146(close, smooth1_length=None, smooth1_weight=None, mean_length=None,
             smooth2_length=None, smooth2_weight=None, offset=None, **kwargs):
    """Indicator: Return-Innovation Momentum (G191_146)"""
    # Validate Arguments
    smooth1_length = int(smooth1_length) if smooth1_length and smooth1_length > 0 else 61
    smooth1_weight = int(smooth1_weight) if smooth1_weight and smooth1_weight > 0 else 2
    mean_length = int(mean_length) if mean_length and mean_length > 0 else 20
    smooth2_length = int(smooth2_length) if smooth2_length and smooth2_length > 0 else 60
    smooth2_weight = int(smooth2_weight) if smooth2_weight and smooth2_weight > 0 else 2
    min_length = smooth1_length + max(mean_length, smooth2_length)
    close = verify_series(close, min_length)
    offset = get_offset(offset)

    if close is None:
        return

    # Calculate Result
    r = close / close.shift(1) - 1.0
    s1 = r.ewm(alpha=smooth1_weight / smooth1_length, adjust=False,
               min_periods=smooth1_length).mean()
    e = r - s1
    m20 = e.rolling(mean_length).mean()
    s2 = (e ** 2).ewm(alpha=smooth2_weight / smooth2_length, adjust=False,
                       min_periods=smooth2_length).mean()

    result = (m20 * e / s2).replace([np.inf, -np.inf], np.nan)
    mask = e.notna() & m20.notna() & s2.notna()
    result = result.where(mask)

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
        f"G191_146_{smooth1_length}_{smooth1_weight}_{mean_length}_"
        f"{smooth2_length}_{smooth2_weight}"
    )
    result.category = "momentum"

    return result


g191_146.__doc__ = \
"""Return-Innovation Momentum (G191_146)

Guotai Junan's (2017, "GTJA191") alpha `#146`, per issue #52. The daily
return's deviation from its own slow GTJA-recursive average (the "return
innovation") is scaled by its own 20-bar mean and normalised by its slow
recursive variance -- a momentum-of-surprise signal: large and persistent
positive innovations push the column up, large and persistent negative
innovations push it down, and a small or inconsistent innovation keeps it
near zero regardless of its size relative to recent volatility. Full Gate A
derivation, causality and scale-free arguments are in the module source
above; see docs/G191146Measured.md for the measured numbers.

Calculation:
    Default Inputs:
        smooth1_length=61, smooth1_weight=2, mean_length=20,
        smooth2_length=60, smooth2_weight=2
    r   = close / close.shift(1) - 1
    s1  = SMA(r, smooth1_length, smooth1_weight)     # GTJA SMA, ewm(alpha=smooth1_weight/smooth1_length)
    e   = r - s1
    m20 = MEAN(e, mean_length)
    s2  = SMA(e**2, smooth2_length, smooth2_weight)  # GTJA SMA, ewm(alpha=smooth2_weight/smooth2_length)
    G191_146 = (m20 * e) / s2, inf -> NaN

Args:
    close (pd.Series): Series of 'close's
    smooth1_length (int): GTJA SMA length for the first (return) smoother. Default: 61
    smooth1_weight (int): GTJA SMA weight for the first smoother -- GTJA's own
        `m` is always a small positive integer, matching the prototype. Default: 2
    mean_length (int): Rolling window for the innovation's own mean. Default: 20
    smooth2_length (int): GTJA SMA length for the second (variance) smoother. Default: 60
    smooth2_weight (int): GTJA SMA weight for the second smoother. Default: 2
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.Series: G191_146_{smooth1_length}_{smooth1_weight}_{mean_length}_
        {smooth2_length}_{smooth2_weight}, a scale-free (dimensionless)
        column, unbounded in principle but concentrated near zero in
        practice (a ratio of an innovation's own mean and itself over its
        own smoothed variance). NaN for the first
        smooth1_length + max(mean_length, smooth2_length) - 1 bars.
"""
