# -*- coding: utf-8 -*-
"""Volume x close-location oscillator -- Guotai Junan's (2017, "GTJA191",
internal quant report, read via the HKUDS/Vibe-Trading copy, MIT) alpha
`#111`, per issue #71. Source cited by the issue:

    #111: SMA(V*CLV,11,2) - SMA(V*CLV,4,2)

**What this session could NOT do, disclosed up front:** `docs/pine/` and web
access are both unavailable in this worktree, so the issue's own named copy
-- HKUDS/Vibe-Trading (MIT) -- was never read. The formula below is derived
from the issue's own stated text (which is itself a quote of the GTJA191
report), per the issue's own instruction ("Gate A starts from the source
formula, not the prototype"), then cross-checked against the issue's own
prototype (`docs/issues/screen/ind_screen.py:466-470`, `clv` itself at
`ind_screen.py:110`):

    @cand("g191_111", "volume x close-location oscillator", G,
          "#111: SMA(V*CLV,11,2) - SMA(V*CLV,4,2)", "/mean(V,20)")
    def _(o, h, l, c, v):
        x = v * clv(h, l, c)
        return sdiv(sma(x, 11, 2) - sma(x, 4, 2), mean(v, 20))

    def clv(h, l, c): return sdiv((c - l) - (h - c), h - l)

No disclosed interpretation choice was needed -- the issue's own string and
the prototype agree exactly, including both window lengths/weights and the
`/mean(V,20)` scale-free conversion the issue's own candidate line states.

OPERATORS, each read directly off the prototype's own (unambiguous) module
source, the same source every other `g191_*` port in this fork relies on:

* `CLV` (close-location value) = `((C-L)-(H-C)) / (H-L) = (2C-H-L)/(H-L)`,
  the standard Accumulation/Distribution per-bar term, in `[-1, 1]` whenever
  `H > L`. The prototype's own `sdiv` (`ind_screen.py:40`,
  `_fin(a / b)`) replaces `+-inf` with `NaN`; structurally this never
  actually fires here, because `H == L` forces `C == H == L` (the close
  cannot sit outside `[L, H]`), making the numerator `2C-H-L` exactly `0`
  at the same bar the denominator is `0` -- so pandas' own float division
  already returns `NaN` (`0.0/0.0`) without the explicit replacement. This
  port keeps the replacement anyway, matching the prototype's own `sdiv` and
  every sibling port's defensive convention, in case of a non-degenerate
  `inf` from a future caller that violates `L <= C <= H`.
* `V` = volume. `H`, `L`, `C` = high, low, close.
* `SMA(A, n, m)` is GTJA's own recursive smoother, NOT this fork's
  `pandas_ta.overlap.sma` (a plain simple moving average) -- a name
  collision the issue's source report shares with every other GTJA191
  alpha, called out explicitly in the prototype's own docstring
  (`ind_screen.py:57-58`): `Y[t] = (m*A[t] + (n-m)*Y[t-1]) / n`, an
  exponential moving average with `alpha = m/n`. Implemented here as
  `A.ewm(alpha=m/n, adjust=False, min_periods=n).mean()`, the same
  implementation and `min_periods=length` masking convention `g191_152`,
  `g191_146` and `g191_160` already ship for the identical GTJA `SMA`
  operator -- applied TWICE here, at two different `(n, m)` pairs over the
  SAME series `x = V*CLV`.
* `MEAN(X, n)` = a trailing `n`-bar rolling mean, `X.rolling(n).mean()`.
  Matches the prototype's own `mean(x, n): return x.rolling(n).mean()`.

CALCULATION, in the order computed below (defaults `smooth1_length=11,
smooth1_weight=2, smooth2_length=4, smooth2_weight=2, mean_length=20`):
    clv   = ((C - L) - (H - C)) / (H - L), inf -> NaN
    x     = V * clv
    sma1  = SMA(x, smooth1_length, smooth1_weight)
    sma2  = SMA(x, smooth2_length, smooth2_weight)
    mean_v = MEAN(V, mean_length)
    G191_111 = (sma1 - sma2) / mean_v, inf -> NaN

CAUSALITY. `clv[t]` is pointwise in `H[t]`, `L[t]`, `C[t]`, reading no bar
past `t`. `x[t]` is pointwise in `V[t]` and `clv[t]`. Each GTJA `SMA`'s
recursion reads only `x[t]` and its own PRIOR value at each step, so by
induction `sma1[t]` and `sma2[t]` are each a function of `x[0..t]` only.
`mean_v[t]` is a trailing rolling mean of `V[t-mean_length+1..t]`, again
reading no bar past `t`. The final ratio is pointwise on three
already-backward-looking series. Nothing in the chain is shifted forward
anywhere. `tests/test_g191_111.py` proves this both by future-perturbation
(real module: 0 leaks over a synthetic walk, swept past the warm-up) and by
two independent mutants (`importlib` source read, `exec`'d in memory), each
shown live (differs from the real module) and then caught at every offset
past the warm-up: shifting the final write index `mean_length` bars into
the future, and computing `mean_v` with `rolling(mean_length,
center=True)` instead of the causal trailing window -- the same `bos`
look-ahead bug class CLAUDE.md documents.

WARM-UP. `sma1` needs `smooth1_length` valid `x` values (`min_periods=11`,
counted over however many bars it takes to SEE 11 non-NaN `x`s -- an `H==L`
tie just delays the count by one), `sma2` needs `smooth2_length`
(`min_periods=4`), and `mean_v` needs `mean_length` CONSECUTIVE bars of `V`
(`min_periods=20`, a plain `.rolling()`, which, unlike `.ewm()`, requires
the window itself to be `mean_length` bars wide and never reads `x`, so a
tie cannot delay it at all). At the shipped defaults, `mean_v`'s
`mean_length=20` is the binding constraint, so `G191_111` is defined from
`t >= mean_length - 1 = 19` UNLESS more than `mean_length - 1 -
smooth1_length = 8` of bars `0..18` are `H==L` ties (the only way `sma1`'s
11-observation count can fail to clear by bar 18) -- measured in
`docs/measure_g191_111.py`: a single tie injected at bar 5 of a 1500-bar
synthetic walk (no other ties) leaves the first valid index at 19, exactly
unchanged from the no-tie case. `min_length = max(smooth1_length,
smooth2_length, mean_length)` = **20** bars at the shipped defaults,
enforced by `verify_series` -- NECESSARY (fewer bars cannot possibly
satisfy `mean_v`'s `min_periods=20`) and, per the measured single-tie case
above, SUFFICIENT for anything short of a tie-heavy opening stretch.

SCALE-FREE. Let `k > 0` rescale price (`H, L, C -> k*H, k*L, k*C`) and
`j > 0` rescale volume (`V -> j*V`), independently or together. `clv` is
EXACTLY invariant under a positive price rescale: `((k*C-k*L)-(k*H-k*C)) /
(k*H-k*L) = (2*k*C-k*H-k*L) / (k*(H-L)) = (2C-H-L)/(H-L)`, the `k` cancels
algebraically; `clv` does not involve `V` at all, so a volume rescale
leaves it untouched too. `x = V*clv` therefore scales to `j*x` under ANY
positive volume rescale and is untouched by a price rescale alone. Both
GTJA `SMA` applications are linear in a positive scalar multiple of their
input (the recursion `Y[t] = (m*A[t] + (n-m)*Y[t-1])/n` is linear in `A`),
so `sma1 -> j*sma1` and `sma2 -> j*sma2` under a volume rescale, untouched
under a price-only rescale. `mean_v = MEAN(V, mean_length) -> j*mean_v`
under a volume rescale (linearity of the rolling mean), untouched under a
price-only rescale. The final ratio `(sma1-sma2)/mean_v` therefore has the
`j` cancel EXACTLY under ANY positive volume rescale, and is untouched
algebraically under ANY positive price rescale (neither numerator nor
denominator depends on price beyond the already-invariant `clv`).
Measured on a synthetic walk: PRICE x8/x64 and VOLUME x8/x64 (independently
and combined) land bit-identical (power-of-two multiplication is exact in
IEEE754, so the algebraic cancellation/invariance is also exact in float64),
while x10/x3.7 come out within float64 rounding tolerance of the unscaled
column. Measured in the test file and `docs/measure_g191_111.py`, not
merely asserted.
"""
import numpy as np

from pandas_ta.utils import get_offset, verify_series


def _gtja_sma(series, n, m):
    """GTJA SMA(A,n,m): Y = (m*A + (n-m)*Y[-1]) / n, an EMA with alpha m/n."""
    return series.ewm(alpha=m / n, adjust=False, min_periods=n).mean()


def g191_111(high, low, close, volume, smooth1_length=None, smooth1_weight=None,
             smooth2_length=None, smooth2_weight=None, mean_length=None,
             offset=None, **kwargs):
    """Indicator: Volume x Close-Location Oscillator (G191_111)"""
    # Validate Arguments
    smooth1_length = int(smooth1_length) if smooth1_length and smooth1_length > 0 else 11
    smooth1_weight = int(smooth1_weight) if smooth1_weight and smooth1_weight > 0 else 2
    smooth2_length = int(smooth2_length) if smooth2_length and smooth2_length > 0 else 4
    smooth2_weight = int(smooth2_weight) if smooth2_weight and smooth2_weight > 0 else 2
    mean_length = int(mean_length) if mean_length and mean_length > 0 else 20
    min_length = max(smooth1_length, smooth2_length, mean_length)
    high = verify_series(high, min_length)
    low = verify_series(low, min_length)
    close = verify_series(close, min_length)
    volume = verify_series(volume, min_length)
    offset = get_offset(offset)

    if high is None or low is None or close is None or volume is None:
        return

    # Calculate Result
    clv = ((close - low) - (high - close)) / (high - low)
    clv = clv.replace([np.inf, -np.inf], np.nan)
    x = volume * clv
    sma1 = _gtja_sma(x, smooth1_length, smooth1_weight)
    sma2 = _gtja_sma(x, smooth2_length, smooth2_weight)
    mean_v = volume.rolling(mean_length).mean()

    result = ((sma1 - sma2) / mean_v).replace([np.inf, -np.inf], np.nan)

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
        f"G191_111_{smooth1_length}_{smooth1_weight}_{smooth2_length}_"
        f"{smooth2_weight}_{mean_length}"
    )
    result.category = "volume"

    return result


g191_111.__doc__ = \
"""Volume x Close-Location Oscillator (G191_111)

Guotai Junan's (2017, "GTJA191") alpha `#111`, per issue #71. The per-bar
close-location value (`CLV`, `[-1, 1]`, how close the bar closed to its own
high vs. its own low) weighted by volume, smoothed with two GTJA recursive
`SMA`s at different speeds (lengths 11 and 4), the difference of which is a
MACD-style spread of volume-weighted close location; dividing by the
trailing 20-bar mean volume makes the result scale-free. Full Gate A
derivation, causality and scale-free arguments are in the module source
above; see docs/G191111Measured.md for the measured numbers.

Calculation:
    Default Inputs:
        smooth1_length=11, smooth1_weight=2, smooth2_length=4,
        smooth2_weight=2, mean_length=20
    clv      = ((close - low) - (high - close)) / (high - low), inf -> NaN
    x        = volume * clv
    sma1     = SMA(x, smooth1_length, smooth1_weight)   # GTJA SMA, ewm(alpha=smooth1_weight/smooth1_length)
    sma2     = SMA(x, smooth2_length, smooth2_weight)   # GTJA SMA, ewm(alpha=smooth2_weight/smooth2_length)
    mean_v   = MEAN(volume, mean_length)
    G191_111 = (sma1 - sma2) / mean_v, inf -> NaN

Args:
    high (pd.Series): Series of 'high's
    low (pd.Series): Series of 'low's
    close (pd.Series): Series of 'close's
    volume (pd.Series): Series of 'volume's
    smooth1_length (int): GTJA SMA length for the slow smoother. Default: 11
    smooth1_weight (int): GTJA SMA weight for the slow smoother -- GTJA's own
        `m` is always a small positive integer, matching the prototype. Default: 2
    smooth2_length (int): GTJA SMA length for the fast smoother. Default: 4
    smooth2_weight (int): GTJA SMA weight for the fast smoother. Default: 2
    mean_length (int): Rolling window for the volume mean. Default: 20
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.Series: G191_111_{smooth1_length}_{smooth1_weight}_{smooth2_length}_
        {smooth2_weight}_{mean_length}, a scale-free (dimensionless) column.
        NaN for at least the first `max(smooth1_length, smooth2_length,
        mean_length) - 1` bars (19 at the shipped defaults), longer if an
        `H == L` tie bar falls inside the warm-up window.
"""
