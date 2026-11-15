# -*- coding: utf-8 -*-
"""MACD of the smoothed lagged 9-day ratio -- Guotai Junan's (2017, "GTJA191",
internal quant report, read via the HKUDS/Vibe-Trading copy, MIT) alpha
`#152`, per issue #66. Source cited by the issue:

    #152: SMA(MEAN(DELAY(SMA(DELAY(C/C9,1),9,1),1),12) - MEAN(same,26), 9, 1)

**What this session could NOT do, disclosed up front:** `docs/pine/` and web
access are both unavailable in this worktree, so the issue's own named copy
-- HKUDS/Vibe-Trading (MIT) -- was never read. The formula below is derived
from the issue's own stated text (itself a quote of the GTJA191 report), per
the issue's own instruction ("Gate A starts from the source formula, not the
prototype"), then cross-checked against the issue's own prototype
(`docs/issues/screen/ind_screen.py:510-514`):

    @cand("g191_152", "MACD of the smoothed lagged 9-day ratio", G,
          "#152: SMA(MEAN(DELAY(SMA(DELAY(C/C9,1),9,1),1),12) - MEAN(same,26), 9, 1)")
    def _(o, h, l, c, v):
        a = delay(sma(delay(c / delay(c, 9), 1), 9, 1), 1)
        return sma(mean(a, 12) - mean(a, 26), 9, 1)

No disclosed interpretation choice was needed -- the issue's own string and
the prototype agree exactly, including every window length. `C9` is read as
GTJA notation for `DELAY(C, 9)`, the same convention every other `g191_*`
port in this fork already relies on for `X1 = DELAY(X, 1)`-style names.

OPERATORS, each read directly off the prototype's own (unambiguous) module
source, the same source every other `g191_*` port in this fork relies on:

* `DELAY(X, n)` = `X.shift(n)` (`ind_screen.py:45`), a BACKWARD shift (bar
  `t` reads bar `t-n`), never a look-ahead.
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
  `ewm(alpha=...)` calls, and the same convention `g191_146` already ships
  for the identical GTJA `SMA` operator.
* `MEAN(x, d)` = a trailing `d`-bar rolling mean, `x.rolling(d).mean()`
  (`ind_screen.py:47`). Matches the prototype's own `mean(x, n): return
  x.rolling(n).mean()`.
* `C` = close. No other OHLCV field is read.

CALCULATION, in the order computed below (defaults
`delay_length=9, smooth1_length=9, smooth1_weight=1, fast_length=12,
slow_length=26, smooth2_length=9, smooth2_weight=1`):
    C9      = DELAY(C, delay_length)
    ratio   = C / C9
    r1      = DELAY(ratio, 1)
    s9      = SMA(r1, smooth1_length, smooth1_weight)
    s9_1    = DELAY(s9, 1)
    fast    = MEAN(s9_1, fast_length)
    slow    = MEAN(s9_1, slow_length)
    diff    = fast - slow
    G191_152 = SMA(diff, smooth2_length, smooth2_weight)

The structure mirrors a classic MACD (a fast-minus-slow moving-average
spread, itself smoothed into a signal line) applied not to price but to
`s9_1` -- a once-more-lagged, GTJA-recursively-smoothed version of the
9-day close ratio `C/C9`.

CAUSALITY. `C9[t] = C[t-delay_length]` reads only a past bar. `ratio[t] =
C[t]/C9[t]` reads bars `<= t`. `r1[t] = ratio[t-1]` reads bars `<= t-1`.
`s9[t]` is GTJA's own recursive EMA of `r1`: each step reads only `r1[t]`
and its own PRIOR value `s9[t-1]`, so by induction `s9[t]` is a function of
`r1[0..t]` only, hence of `C[0..t-1]` only. `s9_1[t] = s9[t-1]` reads bars
`<= t-1`. `fast[t]`/`slow[t]` are trailing rolling means of `s9_1`, each
reading a window ending at `t`, every index `<= t`. `diff[t] = fast[t] -
slow[t]` reads no bar past `t`. The final `G191_152[t]` is the same GTJA
recursion applied to `diff`, so by the same induction it is a function of
`diff[0..t]` only. Nothing in the chain is shifted forward anywhere.
`tests/test_g191_152.py` proves this both by future-perturbation (real
module: 0 of 34 offsets leak, over a synthetic walk) and by two independent
mutants (`importlib` source read, `exec`'d in memory), each shown live
(differs from the real module) and then caught at every one of the 34
offsets past the warm-up: shifting the final write index `smooth2_length`
bars into the future, and computing `fast` with `rolling(fast_length,
center=True)` instead of the causal trailing window -- the same `bos`
look-ahead bug class CLAUDE.md documents.

A THIRD construction was tried and discarded, recorded here because it
looks like a mutant and is not caught by this method -- not because it is
causal, but because the checked window cannot see it: shifting `r1 =
ratio.shift(1)` to `ratio.shift(-1)` (reading `ratio[t+1]` instead of
`ratio[t-1]`) IS a genuine one-bar look-ahead and is shown live-different
from the real module, but the pipeline's own two further `DELAY`s
(`s9_1 = DELAY(s9,1)`, then the rolling means) push its first visible
effect on the OUTPUT to index `j`, one bar past the last index
(`j-1`) the perturbation-at-`j` sweep checks (measured:
`docs/measure_g191_152.py`, 0 of 34 leaks). Prefix truncation alone proves
nothing (CLAUDE.md, Gate B) -- this is the same lesson from the other
direction: a sweep that only checks `[:j]` can also fail to see a REAL
look-ahead if the surrounding pipeline's own causal delays happen to push
its effect one bar later than the boundary being checked. The two mutants
actually used above are not subject to this: the write-shift mutant moves
the OUTPUT itself, and the centered-mean mutant's look-ahead lands inside
the checked window at the SAME index it corrupts (`fast[t]` at `t < j`
already reads `s9_1[t + (fast_length-1)//2]`, inside the window for every
`t` the sweep checks once `j` is past the warm-up).

WARM-UP. `ratio` is defined from `t >= delay_length`. `r1 = DELAY(ratio,1)`
is defined from `t >= delay_length + 1`. `s9`, GTJA's own recursion with
`min_periods=smooth1_length`, needs `smooth1_length` CONSECUTIVE valid `r1`
values, so it is defined from `t >= delay_length + smooth1_length`. `s9_1 =
DELAY(s9,1)` is defined from `t >= delay_length + smooth1_length + 1`.
`fast`/`slow`, trailing rolling means of `s9_1` over `fast_length` /
`slow_length` bars, are defined from `t >= delay_length + smooth1_length +
fast_length - 1` / `t >= delay_length + smooth1_length + slow_length - 1`
respectively; `diff` needs both, so from `t >= delay_length +
smooth1_length + max(fast_length, slow_length) - 1`. The final `SMA`, with
`min_periods=smooth2_length`, needs `smooth2_length` CONSECUTIVE valid
`diff` values, so `G191_152` is defined from `t >= delay_length +
smooth1_length + max(fast_length, slow_length) + smooth2_length - 1` --
`min_length = delay_length + smooth1_length + max(fast_length,
slow_length) + smooth2_length` bars of history (**53** at the shipped
defaults), enforced by `verify_series`.

SCALE-FREE. Let `k > 0` rescale price (`close -> k*close`). `C9 =
DELAY(C, delay_length)` is linear (a shift carries no arithmetic), so it
scales to `k*C9`. `ratio = C/C9` therefore scales to `(k*C)/(k*C9) = C/C9`
-- the `k` cancels EXACTLY, so `ratio` itself, and every downstream term
built only from `ratio` (`r1`, `s9`, `s9_1`, `fast`, `slow`, `diff`, the
final `SMA`), is untouched by the rescale, for ANY positive `k`. Measured
on a synthetic walk: `x8`/`x64` land bit-identical (power-of-two
multiplication is exact in IEEE754, so the cancellation is also exact in
floating point), while `x10`/`x3.7` come out within float64 rounding
tolerance of the unscaled column (the division and recursion arithmetic
itself rounds differently at a non-power-of-two multiplier, even though
the true mathematical ratio is identical). Measured in the test file and
`docs/measure_g191_152.py`, not merely asserted.
"""
from pandas_ta.utils import get_offset, verify_series


def _gtja_sma(series, n, m):
    """GTJA SMA(A,n,m): Y = (m*A + (n-m)*Y[-1]) / n, an EMA with alpha m/n."""
    return series.ewm(alpha=m / n, adjust=False, min_periods=n).mean()


def g191_152(close, delay_length=None, smooth1_length=None, smooth1_weight=None,
              fast_length=None, slow_length=None, smooth2_length=None,
              smooth2_weight=None, offset=None, **kwargs):
    """Indicator: MACD Of The Smoothed Lagged 9-Day Ratio (G191_152)"""
    # Validate Arguments
    delay_length = int(delay_length) if delay_length and delay_length > 0 else 9
    smooth1_length = int(smooth1_length) if smooth1_length and smooth1_length > 0 else 9
    smooth1_weight = int(smooth1_weight) if smooth1_weight and smooth1_weight > 0 else 1
    fast_length = int(fast_length) if fast_length and fast_length > 0 else 12
    slow_length = int(slow_length) if slow_length and slow_length > 0 else 26
    smooth2_length = int(smooth2_length) if smooth2_length and smooth2_length > 0 else 9
    smooth2_weight = int(smooth2_weight) if smooth2_weight and smooth2_weight > 0 else 1
    min_length = (
        delay_length + smooth1_length + max(fast_length, slow_length) + smooth2_length
    )
    close = verify_series(close, min_length)
    offset = get_offset(offset)

    if close is None:
        return

    # Calculate Result
    ratio = close / close.shift(delay_length)
    r1 = ratio.shift(1)
    s9 = _gtja_sma(r1, smooth1_length, smooth1_weight)
    s9_1 = s9.shift(1)
    fast = s9_1.rolling(fast_length).mean()
    slow = s9_1.rolling(slow_length).mean()
    diff = fast - slow
    result = _gtja_sma(diff, smooth2_length, smooth2_weight)

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
        f"G191_152_{delay_length}_{smooth1_length}_{smooth1_weight}_{fast_length}_"
        f"{slow_length}_{smooth2_length}_{smooth2_weight}"
    )
    result.category = "momentum"

    return result


g191_152.__doc__ = \
"""MACD Of The Smoothed Lagged 9-Day Ratio (G191_152)

Guotai Junan's (2017, "GTJA191") alpha `#152`, per issue #66. The 9-day
close ratio `C/C9` is lagged by a bar and smoothed with GTJA's own
recursive `SMA`; that smoothed series is itself lagged by a bar and fed
into a classic MACD structure (a 12-bar mean minus a 26-bar mean of the
same series), and the resulting spread is smoothed once more with the same
recursive `SMA` -- a MACD taken not of price, but of a once-lagged,
once-smoothed version of the 9-day close ratio. Full Gate A derivation,
causality and scale-free arguments are in the module source above; see
docs/G191152Measured.md for the measured numbers.

Calculation:
    Default Inputs:
        delay_length=9, smooth1_length=9, smooth1_weight=1, fast_length=12,
        slow_length=26, smooth2_length=9, smooth2_weight=1
    C9    = DELAY(close, delay_length)
    ratio = close / C9
    r1    = DELAY(ratio, 1)
    s9    = SMA(r1, smooth1_length, smooth1_weight)      # GTJA SMA, ewm(alpha=smooth1_weight/smooth1_length)
    s9_1  = DELAY(s9, 1)
    fast  = MEAN(s9_1, fast_length)
    slow  = MEAN(s9_1, slow_length)
    diff  = fast - slow
    G191_152 = SMA(diff, smooth2_length, smooth2_weight)  # GTJA SMA, ewm(alpha=smooth2_weight/smooth2_length)

Args:
    close (pd.Series): Series of 'close's
    delay_length (int): Lag for the close ratio's own denominator (`C9`). Default: 9
    smooth1_length (int): GTJA SMA length for the first (ratio) smoother. Default: 9
    smooth1_weight (int): GTJA SMA weight for the first smoother -- GTJA's own
        `m` is always a small positive integer, matching the prototype. Default: 1
    fast_length (int): Rolling window for the fast mean of the smoothed ratio. Default: 12
    slow_length (int): Rolling window for the slow mean of the smoothed ratio. Default: 26
    smooth2_length (int): GTJA SMA length for the second (signal) smoother. Default: 9
    smooth2_weight (int): GTJA SMA weight for the second smoother. Default: 1
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.Series: G191_152_{delay_length}_{smooth1_length}_{smooth1_weight}_
        {fast_length}_{slow_length}_{smooth2_length}_{smooth2_weight}, a
        scale-free (dimensionless) column, unbounded in principle but
        concentrated near zero in practice (a MACD-style spread of two
        rolling means of a smoothed near-1 ratio). NaN for the first
        delay_length + smooth1_length + max(fast_length, slow_length) +
        smooth2_length - 1 bars (52 at the shipped defaults).
"""
