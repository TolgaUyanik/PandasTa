# -*- coding: utf-8 -*-
"""MACD of the smoothed lagged one-day change -- Guotai Junan's (2017,
"GTJA191", internal quant report, read via the HKUDS/Vibe-Trading copy,
MIT) alpha `#169`, per issue #72. Source cited by the issue:

    #169: SMA(MEAN(DELAY(SMA(C-C1,9,1),1),12) - MEAN(same,26), 10, 1)

**What this session could NOT do, disclosed up front:** `docs/pine/` and
web access are both unavailable in this worktree, so the issue's own named
copy -- HKUDS/Vibe-Trading (MIT) -- was never read. The formula below is
derived from the issue's own stated text (itself a quote of the GTJA191
report), per the issue's own instruction ("Gate A starts from the source
formula, not the prototype"), then cross-checked against the issue's own
prototype (`docs/issues/screen/ind_screen.py:537-541`):

    @cand("g191_169", "MACD of the smoothed lagged one-day change", G,
          "#169: SMA(MEAN(DELAY(SMA(C-C1,9,1),1),12) - MEAN(same,26), 10, 1)", "/close")
    def _(o, h, l, c, v):
        a = delay(sma(delta(c, 1), 9, 1), 1)
        return sma(mean(a, 12) - mean(a, 26), 10, 1) / c

No disclosed interpretation choice was needed -- the issue's own string and
the prototype agree exactly, including every window length and the
issue's own scale-free conversion ("/close"). `C1` denotes `C` delayed one
bar, the same convention every other `g191_*` port in this fork relies on
for `X1 = DELAY(X, 1)`-style names; `C-C1` is therefore the plain one-day
price change, read directly off the prototype's own `delta(c, 1)`
(`ind_screen.py:delta`, `x.diff(n)`).

OPERATORS, each read directly off the prototype's own (unambiguous) module
source, the same source every other `g191_*` port in this fork relies on:

* `DELAY(X, n)` = `X.shift(n)` (`ind_screen.py:45`), a BACKWARD shift (bar
  `t` reads bar `t-n`), never a look-ahead.
* `C - C1` = `delta(c, 1)` = `c.diff(1)` -- the one-bar price change, `NaN`
  at bar 0 where `C1` is undefined.
* `SMA(A, n, m)` is GTJA's own recursive smoother, NOT this fork's
  `pandas_ta.overlap.sma` (a plain simple moving average) -- a name
  collision the issue's source report shares with every other GTJA191
  alpha, called out explicitly in the prototype's own docstring
  (`ind_screen.py:55-57`): `Y[t] = (m*A[t] + (n-m)*Y[t-1]) / n`, an
  exponential moving average with `alpha = m/n`. Implemented here as
  `A.ewm(alpha=m/n, adjust=False, min_periods=n).mean()`: `adjust=False`
  reproduces the recursion exactly (pandas' default `adjust=True` instead
  computes a different, non-recursive weighted average over the whole
  history), and `min_periods=n` masks the recursion until it has seen `n`
  of its own valid inputs -- the same `min_periods=length` convention this
  fork's own `pandas_ta.overlap.rma`/`wilder_rma` already use for their own
  `ewm(alpha=...)` calls, and the same convention `g191_146`/`g191_152`
  already ship for the identical GTJA `SMA` operator.
* `MEAN(x, d)` = a trailing `d`-bar rolling mean, `x.rolling(d).mean()`
  (`ind_screen.py:47`). Matches the prototype's own `mean(x, n): return
  x.rolling(n).mean()`.
* `C` = close. No other OHLCV field is read.

CALCULATION, in the order computed below (defaults
`smooth1_length=9, smooth1_weight=1, fast_length=12, slow_length=26,
smooth2_length=10, smooth2_weight=1`):
    delta_c  = C - DELAY(C, 1)             # NaN at bar 0
    s9       = SMA(delta_c, smooth1_length, smooth1_weight)
    a        = DELAY(s9, 1)
    fast     = MEAN(a, fast_length)
    slow     = MEAN(a, slow_length)
    diff     = fast - slow
    G191_169 = SMA(diff, smooth2_length, smooth2_weight) / C

The structure mirrors a classic MACD (a fast-minus-slow moving-average
spread, itself smoothed into a signal line) applied not to price but to
`a` -- a once-lagged, GTJA-recursively-smoothed version of the one-day
price change `C - C1` -- then divided by close for a scale-free result.
Unlike `g191_152` (whose inner quantity is already the dimensionless
ratio `C/C9`, so no final division is needed), `delta_c` here is a
price-unit term, so the issue's own prototype divides the final `SMA` by
`C`, matching the same `/close` conversion `g191_167`/`g191_151` already
ship for their own price-unit GTJA191 alphas.

CAUSALITY. `delta_c[t] = C[t] - C[t-1]` reads only bars `<= t`. `s9[t]` is
GTJA's own recursive EMA of `delta_c`: each step reads only `delta_c[t]`
and its own PRIOR value `s9[t-1]`, so by induction `s9[t]` is a function
of `delta_c[0..t]` only, hence of `C[0..t]` only. `a[t] = s9[t-1]` reads
bars `<= t-1`. `fast[t]`/`slow[t]` are trailing rolling means of `a`, each
reading a window ending at `t`, every index `<= t`. `diff[t] = fast[t] -
slow[t]` reads no bar past `t`. The final GTJA `SMA` applied to `diff` is
the same recursion, so by the same induction it is a function of
`diff[0..t]` only, hence of `C[0..t]` only. The last division by `C[t]`
reads only bar `t`. Nothing in the chain is shifted forward anywhere.
`tests/test_g191_169.py` proves this both by future-perturbation (real
module: 0 of N offsets leak, over a synthetic walk) and by two independent
mutants (`importlib` source read, `exec`'d in memory), each shown live
(differs from the real module) and then caught at every offset past the
warm-up: shifting the final write index `smooth2_length` bars into the
future, and computing `fast` with `rolling(fast_length, center=True)`
instead of the causal trailing window -- the same `bos` look-ahead bug
class CLAUDE.md documents.

WARM-UP. `delta_c` is defined from `t >= 1` (bar 0 has no prior close).
`s9`, GTJA's own recursion with `min_periods=smooth1_length`, needs
`smooth1_length` CONSECUTIVE valid `delta_c` values, so it is defined from
`t >= smooth1_length` (the first valid `delta_c` is at `t=1`, so the
`smooth1_length`-th one lands at `t = smooth1_length`). `a = DELAY(s9, 1)`
is defined from `t >= smooth1_length + 1`. `fast`/`slow`, trailing rolling
means of `a` over `fast_length` / `slow_length` bars, are defined from
`t >= smooth1_length + fast_length` / `t >= smooth1_length + slow_length`
respectively; `diff` needs both, so from `t >= smooth1_length +
max(fast_length, slow_length)`. The final `SMA`, with
`min_periods=smooth2_length`, needs `smooth2_length` CONSECUTIVE valid
`diff` values, so `G191_169` is defined from `t >= smooth1_length +
max(fast_length, slow_length) + smooth2_length - 1` -- `min_length =
smooth1_length + max(fast_length, slow_length) + smooth2_length` bars of
history (**45** at the shipped defaults), enforced by `verify_series`.

SCALE-FREE. Let `k > 0` rescale price (`close -> k*close`). `delta_c = C -
DELAY(C, 1)` scales to `k*delta_c` (subtraction of two linearly scaled
terms). `s9`, a linear recursion (a weighted sum of `delta_c` values),
scales to `k*s9`; `a = DELAY(s9, 1)` likewise scales to `k*a`; `fast`,
`slow` and `diff`, all linear in `a`, scale to `k*fast`, `k*slow`,
`k*diff`; the final `SMA`, again linear, scales to `k*SMA(diff, ...)`. The
last division by `C -> k*C` therefore gives `(k*SMA(diff,...))/(k*C) =
SMA(diff,...)/C` -- the `k` cancels EXACTLY, for ANY positive `k`.
Measured on a synthetic walk: `x8`/`x64` land bit-identical (power-of-two
multiplication is exact in IEEE754, so the cancellation is also exact in
floating point), while `x10`/`x3.7` come out within float64 rounding
tolerance of the unscaled column (the subtraction, recursion and rolling
arithmetic itself rounds differently at a non-power-of-two multiplier,
even though the true mathematical ratio is identical). Measured in the
test file and `docs/measure_g191_169.py`, not merely asserted.
"""
from pandas_ta.utils import get_offset, verify_series


def _gtja_sma(series, n, m):
    """GTJA SMA(A,n,m): Y = (m*A + (n-m)*Y[-1]) / n, an EMA with alpha m/n."""
    return series.ewm(alpha=m / n, adjust=False, min_periods=n).mean()


def g191_169(close, smooth1_length=None, smooth1_weight=None, fast_length=None,
             slow_length=None, smooth2_length=None, smooth2_weight=None,
             offset=None, **kwargs):
    """Indicator: MACD Of The Smoothed Lagged One-Day Change (G191_169)"""
    # Validate Arguments
    smooth1_length = int(smooth1_length) if smooth1_length and smooth1_length > 0 else 9
    smooth1_weight = int(smooth1_weight) if smooth1_weight and smooth1_weight > 0 else 1
    fast_length = int(fast_length) if fast_length and fast_length > 0 else 12
    slow_length = int(slow_length) if slow_length and slow_length > 0 else 26
    smooth2_length = int(smooth2_length) if smooth2_length and smooth2_length > 0 else 10
    smooth2_weight = int(smooth2_weight) if smooth2_weight and smooth2_weight > 0 else 1
    min_length = smooth1_length + max(fast_length, slow_length) + smooth2_length
    close = verify_series(close, min_length)
    offset = get_offset(offset)

    if close is None:
        return

    # Calculate Result
    delta_c = close.diff()
    s9 = _gtja_sma(delta_c, smooth1_length, smooth1_weight)
    a = s9.shift(1)
    fast = a.rolling(fast_length).mean()
    slow = a.rolling(slow_length).mean()
    diff = fast - slow
    result = _gtja_sma(diff, smooth2_length, smooth2_weight) / close

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
        f"G191_169_{smooth1_length}_{smooth1_weight}_{fast_length}_"
        f"{slow_length}_{smooth2_length}_{smooth2_weight}"
    )
    result.category = "momentum"

    return result


g191_169.__doc__ = \
"""MACD Of The Smoothed Lagged One-Day Change (G191_169)

Guotai Junan's (2017, "GTJA191") alpha `#169`, per issue #72. The one-day
price change `C - C1` is smoothed with GTJA's own recursive `SMA`; that
smoothed series is lagged by a bar and fed into a classic MACD structure
(a 12-bar mean minus a 26-bar mean of the same series), the resulting
spread is smoothed once more with the same recursive `SMA`, and the
result is divided by close for a scale-free column -- a MACD taken not of
price, but of a once-lagged, once-smoothed version of the one-day price
change. Full Gate A derivation, causality and scale-free arguments are in
the module source above; see docs/G191169Measured.md for the measured
numbers.

Calculation:
    Default Inputs:
        smooth1_length=9, smooth1_weight=1, fast_length=12, slow_length=26,
        smooth2_length=10, smooth2_weight=1
    delta_c  = close - DELAY(close, 1)
    s9       = SMA(delta_c, smooth1_length, smooth1_weight)  # GTJA SMA, ewm(alpha=smooth1_weight/smooth1_length)
    a        = DELAY(s9, 1)
    fast     = MEAN(a, fast_length)
    slow     = MEAN(a, slow_length)
    diff     = fast - slow
    G191_169 = SMA(diff, smooth2_length, smooth2_weight) / close  # GTJA SMA, ewm(alpha=smooth2_weight/smooth2_length)

Args:
    close (pd.Series): Series of 'close's
    smooth1_length (int): GTJA SMA length for the first (change) smoother. Default: 9
    smooth1_weight (int): GTJA SMA weight for the first smoother -- GTJA's own
        `m` is always a small positive integer, matching the prototype. Default: 1
    fast_length (int): Rolling window for the fast mean of the smoothed change. Default: 12
    slow_length (int): Rolling window for the slow mean of the smoothed change. Default: 26
    smooth2_length (int): GTJA SMA length for the second (signal) smoother. Default: 10
    smooth2_weight (int): GTJA SMA weight for the second smoother. Default: 1
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.Series: G191_169_{smooth1_length}_{smooth1_weight}_{fast_length}_
        {slow_length}_{smooth2_length}_{smooth2_weight}, a scale-free
        (dimensionless) column, unbounded in principle but concentrated
        near zero in practice (a MACD-style spread of two rolling means of
        a smoothed price change, divided by close). NaN for the first
        smooth1_length + max(fast_length, slow_length) + smooth2_length - 1
        bars (44 at the shipped defaults).
"""
