# -*- coding: utf-8 -*-
"""Up-day volatility EMA -- Guotai Junan's (2017, "GTJA191", internal quant
report, read via the HKUDS/Vibe-Trading copy, MIT) alpha `#174`, per issue
#74. Source cited by the issue:

    #174: SMA(C>C1 ? STD(C,20) : 0, 20, 1)

**What this session could NOT do, disclosed up front:** `docs/pine/` and web
access are both unavailable in this worktree, so the issue's own named copy
-- HKUDS/Vibe-Trading (MIT) -- was never read. The formula below is taken
directly from the issue's own stated text, per the issue's own instruction
("Gate A starts from the source formula, not the prototype"), then
cross-checked against the issue's own prototype
(`docs/issues/screen/ind_screen.py:544-547`):

    @cand("g191_174", "up-day volatility EMA", G,
          "#174: SMA(C>C1 ? STD(C,20) : 0, 20, 1)", "/close")
    def _(o, h, l, c, v):
        s = std(c, 20)
        return sma(s.where(c > delay(c, 1), 0.0).where(s.notna()), 20, 1) / c

No disclosed interpretation choice was needed -- the issue's own string and
the prototype agree exactly, including the window lengths. Unlike `g191_023`
(issue #73), this alpha is NOT a ratio of two same-unit accumulators: it is
the single up-day accumulator alone, which carries the unit of `STD(C,20)`
-- a price-scale quantity. The prototype's own `conv` field records this
directly (`docs/issues/screen/candidates.csv`'s `g191_174` row: `/close`),
and this port applies that division, matching the issue's own candidate
line, "(scale-free form: /close)".

OPERATORS, each read directly off the prototype's own (unambiguous) module
source, the same source every other `g191_*` port in this fork relies on:

* `C1` denotes `C` delayed one bar, `DELAY(C, 1) = C.shift(1)`
  (`ind_screen.py:45`), a BACKWARD shift (bar `t` reads bar `t-1`), never a
  look-ahead.
* `STD(X, n)` = a trailing `n`-bar rolling sample standard deviation,
  `X.rolling(n).std()` -- pandas default `ddof=1` (`ind_screen.py:48`), the
  same convention `g191_076` (issue #54), `g191_160` (issue #67) and
  `g191_023` (issue #73) already established for the identical GTJA `STD`
  operator.
* `C>C1 ? STD(C,20) : 0` is a per-bar ternary: it keeps the rolling std on
  an up day (`close[t] > close[t-1]`) and forces `0.0` on a down-or-flat day
  (`close[t] <= close[t-1]`). The prototype's own `s.where(c > delay(c, 1),
  0.0)` is this ternary read literally -- `Series.where(cond, other)` keeps
  the original value where `cond` is True and substitutes `other` where it
  is False. The prototype's own trailing `.where(s.notna())` re-masks the
  result to `NaN` wherever `STD(C,20)` itself is undefined (the first
  `std_length-1` bars) -- without it, `s.where(cond, 0.0)` would silently
  turn those leading `NaN`s into `0.0` on down-or-flat bars there, which is
  not what the formula states (the ternary chooses between `STD(C,20)` and
  `0`, not between "whatever `STD` happens to be, `NaN` included" and `0`).
* `SMA(A, n, m)` is GTJA's own recursive smoother, NOT this fork's
  `pandas_ta.overlap.sma` (a plain simple moving average) -- a name
  collision the issue's source report shares with every other GTJA191
  alpha, called out explicitly in the prototype's own docstring
  (`ind_screen.py:57-59`): `Y[t] = (m*A[t] + (n-m)*Y[t-1]) / n`, an
  exponential moving average with `alpha = m/n`. Implemented here as
  `A.ewm(alpha=m/n, adjust=False, min_periods=n).mean()`, the same
  implementation and the same `min_periods=length` masking convention
  `g191_160` and `g191_023` already ship for the identical GTJA `SMA`
  operator.
* `C` = close. No other OHLCV field is read.

CALCULATION, in the order computed below (defaults
`std_length=20, smooth_length=20, smooth_weight=1`):
    C1       = DELAY(C, 1)
    std_c    = STD(C, std_length)
    up_vol   = std_c.where(C > C1, 0.0).where(std_c.notna())
    u        = SMA(up_vol, smooth_length, smooth_weight)
    G191_174 = u / C

CAUSALITY. `C1[t] = C[t-1]` reads only a past bar. `std_c[t]` is a trailing
rolling statistic of `C[t-std_length+1..t]`, reading no bar past `t`.
`up_vol[t]` is pointwise in `std_c[t]` and the pointwise comparison `C[t] >
C1[t]`, reading no bar past `t`. The `SMA`'s recursion reads only its own
input at `t` and its own PRIOR value at each step, so by induction `u[t]`
is a function of `up_vol[0..t]` only, hence of `C[0..t]` only. The final
division by `C[t]` reads only bar `t`. Nothing in the chain is shifted
forward anywhere. `tests/test_g191_174.py` proves this both by
future-perturbation (real module: 0 leaks over a synthetic walk, swept past
the warm-up) and by two independent mutants (`importlib` source read,
`exec`'d in memory), each shown live (differs from the real module) and
then caught at every offset past the warm-up: shifting the final write
index `smooth_length` bars into the future, and computing `std_c` with
`rolling(std_length, center=True)` instead of the causal trailing window --
the same `bos` look-ahead bug class CLAUDE.md documents.

WARM-UP. `std_c` needs `std_length` CONSECUTIVE bars of `C`, so it is
defined from `t >= std_length - 1`. `up_vol` inherits that same mask
exactly (the trailing `.where(std_c.notna())` is what enforces this --
`up_vol` is defined for precisely the same `t` as `std_c`, no earlier and
no later). The GTJA `SMA`, with `min_periods=smooth_length`, needs
`smooth_length` CONSECUTIVE valid `up_vol` values, so `u` (hence the
result) is defined from `t >= (std_length - 1) + (smooth_length - 1)` --
`min_length = std_length + smooth_length - 1` bars of history (**39** at
the shipped defaults), enforced by `verify_series`.

SCALE-FREE. Let `k > 0` rescale price (`close -> k*close`). The comparison
`C > C1` is invariant under a positive rescale (`k*C > k*C1` iff `C > C1`
for `k > 0`), so the ternary's BRANCH CHOICE at every bar is unchanged.
`STD(k*C, n) = k * STD(C, n)` (standard deviation is linear in a positive
scalar multiple of its input), so `std_c` scales to `k*std_c`. On the kept
branch, `up_vol` therefore scales to `k*up_vol`; on the forced-zero branch
it stays exactly `0.0 = k*0.0` for any `k`. So `up_vol` scales to
`k*up_vol` at every bar, and the GTJA `SMA`'s recursion is itself linear in
its input, so `u -> k*u`. Unlike `g191_023`'s ratio (where the `k` cancels
between numerator and denominator with no final division needed), `u`
ALONE carries the price unit, so the final `u/C` division is what makes
the column scale-free: `(k*u)/(k*C) = u/C` -- the `k` cancels EXACTLY, for
ANY positive `k`. Measured on a synthetic walk: `x8`/`x64` land
bit-identical (power-of-two multiplication is exact in IEEE754, so the
cancellation is also exact in floating point), while `x10`/`x3.7` come out
within float64 rounding tolerance of the unscaled column (the comparison
and recursion arithmetic itself rounds differently at a non-power-of-two
multiplier, even though the true mathematical ratio is identical).
Measured in the test file and `docs/measure_g191_174.py`, not merely
asserted.
"""
from pandas_ta.utils import get_offset, verify_series


def _gtja_sma(series, n, m):
    """GTJA SMA(A,n,m): Y = (m*A + (n-m)*Y[-1]) / n, an EMA with alpha m/n."""
    return series.ewm(alpha=m / n, adjust=False, min_periods=n).mean()


def g191_174(close, std_length=None, smooth_length=None, smooth_weight=None,
             offset=None, **kwargs):
    """Indicator: Up-Day Volatility EMA (G191_174)"""
    # Validate Arguments
    std_length = int(std_length) if std_length and std_length > 1 else 20
    smooth_length = int(smooth_length) if smooth_length and smooth_length > 0 else 20
    smooth_weight = int(smooth_weight) if smooth_weight and smooth_weight > 0 else 1
    min_length = std_length + smooth_length - 1
    close = verify_series(close, min_length)
    offset = get_offset(offset)

    if close is None:
        return

    # Calculate Result
    std_c = close.rolling(std_length).std()
    up = close > close.shift(1)
    up_vol = std_c.where(up, 0.0).where(std_c.notna())
    u = _gtja_sma(up_vol, smooth_length, smooth_weight)
    result = u / close

    # Offset
    if offset != 0:
        result = result.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        result.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        result.fillna(method=kwargs["fill_method"], inplace=True)

    # Name & Category
    result.name = f"G191_174_{std_length}_{smooth_length}_{smooth_weight}"
    result.category = "volatility"

    return result


g191_174.__doc__ = \
"""Up-Day Volatility EMA (G191_174)

Guotai Junan's (2017, "GTJA191") alpha `#174`, per issue #74. On each day the
trailing `std_length`-bar rolling standard deviation of close is routed to an
accumulator only if the day closed up (`close > close.shift(1)`), else
contributes zero, smoothed with GTJA's own recursive `SMA`, then divided by
close to make the column scale-free. The single-accumulator (non-ratio)
counterpart of `g191_023` (issue #73, up-day share) and `g191_160` (issue
#67, down-day share). Full Gate A derivation, causality and scale-free
arguments are in the module source above; see docs/G191174Measured.md for
the measured numbers.

Calculation:
    Default Inputs:
        std_length=20, smooth_length=20, smooth_weight=1
    C1       = DELAY(close, 1)
    std_c    = STDEV(close, std_length)                  # ddof=1, pandas default
    up_vol   = std_c where close > C1, else 0.0; NaN where std_c is NaN
    u        = SMA(up_vol, smooth_length, smooth_weight) # GTJA SMA, ewm(alpha=smooth_weight/smooth_length)
    G191_174 = u / close

Args:
    close (pd.Series): Series of 'close's
    std_length (int): Rolling window for the per-day standard deviation. Default: 20
    smooth_length (int): GTJA SMA length for the recursive smoother. Default: 20
    smooth_weight (int): GTJA SMA weight for the recursive smoother -- GTJA's own
        `m` is always a small positive integer, matching the prototype. Default: 1
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.Series: G191_174_{std_length}_{smooth_length}_{smooth_weight}, a
        scale-free (dimensionless) column, non-negative (a smoothed,
        close-normalised up-day volatility). NaN for the first
        std_length + smooth_length - 2 bars (38 at the shipped defaults).
"""
