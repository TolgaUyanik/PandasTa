# -*- coding: utf-8 -*-
"""Up-day volatility share (Dorsey RVI form) -- Guotai Junan's (2017,
"GTJA191", internal quant report, read via the HKUDS/Vibe-Trading copy, MIT)
alpha `#23`, per issue #73. Source cited by the issue:

    #23: SMA(C>C1 ? STD(C,20) : 0, 20, 1) / (that + SMA(C<=C1 ? STD(C,20) : 0, 20, 1)) * 100

**What this session could NOT do, disclosed up front:** `docs/pine/` and web
access are both unavailable in this worktree, so the issue's own named copy
-- HKUDS/Vibe-Trading (MIT) -- was never read. The formula below is taken
directly from the issue's own stated text, per the issue's own instruction
("Gate A starts from the source formula, not the prototype"), then
cross-checked against the issue's own prototype
(`docs/issues/screen/ind_screen.py:324-330`):

    @cand("g191_023", "up-day volatility share (Dorsey RVI form)", G,
          "#23: SMA(C>C1 ? STD(C,20) : 0, 20, 1) / (that + SMA(C<=C1 ? STD(C,20) : 0, 20, 1)) * 100")
    def _(o, h, l, c, v):
        s, up = std(c, 20), c > delay(c, 1)
        u = sma(s.where(up, 0.0).where(s.notna()), 20, 1)
        d = sma(s.where(~up, 0.0).where(s.notna()), 20, 1)
        return 100 * sdiv(u, u + d)

No disclosed interpretation choice was needed -- the issue's own string and
the prototype agree exactly, including both window lengths. Unlike `g191_160`
(the down-day counterpart, issue #67), this alpha carries NO `conv` field in
the issue's own prototype registry (`docs/issues/screen/candidates.csv`'s
`g191_023` row leaves the conversion column blank): the ratio of two
same-unit (price-std) quantities is already scale-free by construction, so no
`/close` division is applied here, matching the issue's own candidate line.

OPERATORS, each read directly off the prototype's own (unambiguous) module
source, the same source every other `g191_*` port in this fork relies on:

* `C1` denotes `C` delayed one bar, `DELAY(C, 1) = C.shift(1)`
  (`ind_screen.py:45`), a BACKWARD shift (bar `t` reads bar `t-1`), never a
  look-ahead.
* `STD(X, n)` = a trailing `n`-bar rolling sample standard deviation,
  `X.rolling(n).std()` -- pandas default `ddof=1` (`ind_screen.py:48`), the
  same convention `g191_076` (issue #54) and `g191_160` (issue #67) already
  established for the identical GTJA `STD` operator.
* `C>C1 ? STD(C,20) : 0` and `C<=C1 ? STD(C,20) : 0` are a complementary pair
  of per-bar ternaries, partitioning EVERY bar into exactly one of the two
  branches (an up day, `close[t] > close[t-1]`, or a down-or-flat day,
  `close[t] <= close[t-1]`): one keeps the rolling std on an up day and
  forces `0.0` on a down-or-flat day, the other does the opposite. The
  prototype's own `s.where(up, 0.0)` / `s.where(~up, 0.0)` is this pair read
  literally -- `Series.where(cond, other)` keeps the original value where
  `cond` is True and substitutes `other` where it is False. The prototype's
  own trailing `.where(s.notna())` on each branch re-masks the result to
  `NaN` wherever `STD(C,20)` itself is undefined (the first `std_length-1`
  bars) -- without it, `s.where(cond, 0.0)` would silently turn those
  leading `NaN`s into `0.0` on whichever branch's condition is False there,
  which is not what the formula states (the ternary chooses between
  `STD(C,20)` and `0`, not between "whatever `STD` happens to be, `NaN`
  included" and `0`).
* `SMA(A, n, m)` is GTJA's own recursive smoother, NOT this fork's
  `pandas_ta.overlap.sma` (a plain simple moving average) -- a name
  collision the issue's source report shares with every other GTJA191
  alpha, called out explicitly in the prototype's own docstring
  (`ind_screen.py:57-59`): `Y[t] = (m*A[t] + (n-m)*Y[t-1]) / n`, an
  exponential moving average with `alpha = m/n`. Implemented here as
  `A.ewm(alpha=m/n, adjust=False, min_periods=n).mean()`, the same
  implementation and the same `min_periods=length` masking convention
  `g191_160` already ships for the identical GTJA `SMA` operator.
* `C` = close. No other OHLCV field is read.
* The issue's own final `* 100` scales the ratio to a 0-100 percentage, the
  Dorsey Relative Volatility Index's own convention (this fork's own `rvi`
  module, upstream `RVI`, uses the identical 0-100 scale for the structurally
  analogous up/down-vs-STD ratio).

CALCULATION, in the order computed below (defaults
`std_length=20, smooth_length=20, smooth_weight=1`):
    C1     = DELAY(C, 1)
    std_c  = STD(C, std_length)
    up_vol = std_c.where(C > C1, 0.0).where(std_c.notna())
    dn_vol = std_c.where(C <= C1, 0.0).where(std_c.notna())
    u      = SMA(up_vol, smooth_length, smooth_weight)
    d      = SMA(dn_vol, smooth_length, smooth_weight)
    G191_023 = 100 * u / (u + d)

CAUSALITY. `C1[t] = C[t-1]` reads only a past bar. `std_c[t]` is a trailing
rolling statistic of `C[t-std_length+1..t]`, reading no bar past `t`.
`up_vol[t]`/`dn_vol[t]` are pointwise in `std_c[t]` and the pointwise
comparison `C[t] > C1[t]` (equivalently `C[t] <= C1[t]`), reading no bar past
`t`. Each `SMA`'s recursion reads only its own input at `t` and its own PRIOR
value at each step, so by induction `u[t]` and `d[t]` are functions of
`up_vol[0..t]` / `dn_vol[0..t]` only, hence of `C[0..t]` only. The final
ratio `100 * u[t] / (u[t] + d[t])` reads no bar past `t` either. Nothing in
the chain is shifted forward anywhere. `tests/test_g191_023.py` proves this
both by future-perturbation (real module: 0 leaks over a synthetic walk,
swept past the warm-up) and by two independent mutants (`importlib` source
read, `exec`'d in memory), each shown live (differs from the real module)
and then caught at every offset past the warm-up: shifting the final write
index `smooth_length` bars into the future, and computing `std_c` with
`rolling(std_length, center=True)` instead of the causal trailing window --
the same `bos` look-ahead bug class CLAUDE.md documents.

WARM-UP. `std_c` needs `std_length` CONSECUTIVE bars of `C`, so it is defined
from `t >= std_length - 1`. `up_vol`/`dn_vol` inherit that same mask exactly
(the trailing `.where(std_c.notna())` is what enforces this -- each is
defined for precisely the same `t` as `std_c`, no earlier and no later). The
GTJA `SMA`, with `min_periods=smooth_length`, needs `smooth_length`
CONSECUTIVE valid `up_vol`/`dn_vol` values, so `u` and `d` (hence the ratio)
are defined from `t >= (std_length - 1) + (smooth_length - 1)` --
`min_length = std_length + smooth_length - 1` bars of history (**39** at the
shipped defaults), enforced by `verify_series`.

SCALE-FREE. Let `k > 0` rescale price (`close -> k*close`). The comparison
`C > C1` (and its complement) is invariant under a positive rescale (`k*C >
k*C1` iff `C > C1` for `k > 0`), so each ternary's BRANCH CHOICE at every bar
is unchanged. `STD(k*C, n) = k * STD(C, n)` (standard deviation is linear in
a positive scalar multiple of its input), so `std_c` scales to `k*std_c`. On
the kept branch, `up_vol`/`dn_vol` therefore scale to `k*up_vol` / `k*dn_vol`;
on the forced-zero branch each stays exactly `0.0 = k*0.0` for any `k`. So
`up_vol`/`dn_vol` scale to `k*up_vol` / `k*dn_vol` at every bar, and the GTJA
`SMA`'s recursion is itself linear in its input, so `u -> k*u` and
`d -> k*d`. The ratio `100 * (k*u) / (k*u + k*d) = 100 * u / (u + d)` -- the
`k` cancels EXACTLY, for ANY positive `k`, with no final division needed (the
column is self-normalising, unlike `g191_160`'s `/close`). Measured on a
synthetic walk: `x8`/`x64` land bit-identical (power-of-two multiplication is
exact in IEEE754, so the cancellation is also exact in floating point), while
`x10`/`x3.7` come out within float64 rounding tolerance of the unscaled
column (the comparison and recursion arithmetic itself rounds differently at
a non-power-of-two multiplier, even though the true mathematical ratio is
identical). Measured in the test file and `docs/measure_g191_023.py`, not
merely asserted.
"""
import numpy as np

from pandas_ta.utils import get_offset, verify_series


def _gtja_sma(series, n, m):
    """GTJA SMA(A,n,m): Y = (m*A + (n-m)*Y[-1]) / n, an EMA with alpha m/n."""
    return series.ewm(alpha=m / n, adjust=False, min_periods=n).mean()


def g191_023(close, std_length=None, smooth_length=None, smooth_weight=None,
             offset=None, **kwargs):
    """Indicator: Up-Day Volatility Share, Dorsey RVI form (G191_023)"""
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
    dn_vol = std_c.where(~up, 0.0).where(std_c.notna())
    u = _gtja_sma(up_vol, smooth_length, smooth_weight)
    d = _gtja_sma(dn_vol, smooth_length, smooth_weight)
    with np.errstate(invalid="ignore"):
        result = 100.0 * u / (u + d)

    # Offset
    if offset != 0:
        result = result.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        result.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        result.fillna(method=kwargs["fill_method"], inplace=True)

    # Name & Category
    result.name = f"G191_023_{std_length}_{smooth_length}_{smooth_weight}"
    result.category = "volatility"

    return result


g191_023.__doc__ = \
"""Up-Day Volatility Share, Dorsey RVI form (G191_023)

Guotai Junan's (2017, "GTJA191") alpha `#23`, per issue #73. The down-day
counterpart of `g191_160` (issue #67): on each day the trailing
`std_length`-bar rolling standard deviation of close is routed to one of two
accumulators depending on whether the day closed up (`close >
close.shift(1)`) or down-or-flat, each smoothed with GTJA's own recursive
`SMA`; the result is the up-accumulator's share of the two accumulators'
sum, scaled to 0-100 -- the Dorsey Relative Volatility Index form. Full Gate
A derivation, causality and scale-free arguments are in the module source
above; see docs/G191023Measured.md for the measured numbers.

Calculation:
    Default Inputs:
        std_length=20, smooth_length=20, smooth_weight=1
    C1     = DELAY(close, 1)
    std_c  = STDEV(close, std_length)                      # ddof=1, pandas default
    up_vol = std_c where close > C1, else 0.0; NaN where std_c is NaN
    dn_vol = std_c where close <= C1, else 0.0; NaN where std_c is NaN
    u      = SMA(up_vol, smooth_length, smooth_weight)     # GTJA SMA, ewm(alpha=smooth_weight/smooth_length)
    d      = SMA(dn_vol, smooth_length, smooth_weight)
    G191_023 = 100 * u / (u + d)

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
    pd.Series: G191_023_{std_length}_{smooth_length}_{smooth_weight}, a
        scale-free (dimensionless) column bounded in [0, 100] (an up-day
        volatility share of total smoothed volatility). NaN for the first
        std_length + smooth_length - 2 bars (38 at the shipped defaults).
"""
