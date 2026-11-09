# -*- coding: utf-8 -*-
"""100-Day Trend-Gated Drawdown / 3-Day Reversal -- Guotai Junan's (2017,
"GTJA191", internal quant report, read via the HKUDS/Vibe-Trading copy,
MIT) alpha `#98`, per issue #58. Source cited by the issue:

    #98: DELTA(MEAN(C,100),100)/DELAY(C,100) <= 0.05 ? -(C-TSMIN(C,100)) : -DELTA(C,3)

**What this session could NOT do, disclosed up front:** `docs/pine/` and web
access are both unavailable in this worktree, so the issue's own named copy
-- HKUDS/Vibe-Trading (MIT) -- was never read. The formula below is derived
from the issue's own stated text (which is itself a quote of the GTJA191
report), per the issue's own instruction ("Gate A starts from the source
formula, not the prototype").

GATE A -- DERIVATION. The formula is a ternary gated by how much the
100-bar moving average of `close` has itself moved over the last 100 bars,
relative to the close 100 bars ago:

    trend_mean = MEAN(C, 100)
    gate       = DELTA(trend_mean, 100) / DELAY(C, 100)
    G191_098   = gate <= 0.05 ? -(C - TSMIN(C, 100)) : -DELTA(C, 3)

`gate <= 0.05` reads "the 100-bar average has drifted by at most 5% of the
close 100 bars ago" -- a flat-or-declining-trend gate (a strongly rising
100-bar average pushes `gate` above 0.05 and routes to the OTHER branch).
When the gate fires (flat/declining trend), the alpha reports
`-(C - TSMIN(C,100))` = `TSMIN(C,100) - C`, a non-positive distance: zero
exactly at the 100-bar low, more negative the further price sits above it
-- a DRAWDOWN read, hence "100-day trend-gated drawdown". Otherwise (a
strongly rising 100-bar average), it reports `-DELTA(C,3)` =
`-(C - DELAY(C,3))`, the negated 3-bar price change -- a REVERSAL read:
a strong 3-bar advance makes this strongly negative. Operators, each read
directly off the issue's own named prototype's unambiguous module
docstring (`docs/issues/screen/ind_screen.py`, the same source
`g191_144` (issue #57) and `g191_165` (issue #55) relied on for the same
operator family):

* `DELAY(X, n)` = `X.shift(n)` (`ind_screen.py:45`), a BACKWARD shift
  (bar `t` reads bar `t-n`), never a look-ahead.
* `DELTA(X, n)` = `X - X.shift(n)` (`ind_screen.py:46`), the `n`-bar
  backward difference.
* `MEAN(X, n)` = `X.rolling(n).mean()` (`ind_screen.py:47`), a trailing
  `n`-bar rolling mean.
* `TSMIN(X, n)` = `X.rolling(n).min()` (`ind_screen.py:51`), a trailing
  `n`-bar rolling minimum.
* `C` = close. The formula uses no other OHLCV field.

The issue's own prototype (`docs/issues/screen/ind_screen.py:445-449`)
spells out the identical ternary directly, already in its scale-free
("/close") form:

    g = delta(mean(c, 100), 100) / delay(c, 100)
    (pd.Series(np.where(g <= 0.05, -(c - tsmin(c, 100)), -delta(c, 3)),
               index=c.index) / c).where(g.notna())

so this port ships that same scale-free ratio: `G191_098 = raw / close`,
where `raw` is the ternary above, and the final column is masked to `NaN`
wherever `gate` itself is undefined or non-finite -- not merely wherever
the SELECTED branch happens to be undefined, matching the prototype's own
`.where(g.notna())` (the branch not taken is still computed, by
construction of `np.where`, but is discarded by this mask).

One disclosed hardening beyond the prototype's literal `np.where(g <= ...)`:
`gate`'s denominator is `DELAY(C, 100)`, a price, never structurally zero on
real data but not provably nonzero either; this port explicitly replaces
`+-inf` in `gate` with `NaN` before the comparison (the prototype's `g`
would instead carry a `+-inf <= 0.05` comparison through to `False`, i.e.
silently route an ill-defined gate to the reversal branch). `NaN` is not
`<=` anything in pandas/numpy (the comparison itself evaluates to `False`,
matching ordinary float semantics), so an inf-gate row is masked out by
the final `g.notna()`-style check either way; the explicit inf replacement
only makes that masking ALSO catch the (currently unobserved) inf case
rather than relying on `NaN != inf`.

CALCULATION, in the order computed below (`length=100`,
`reversal_length=3`, `threshold=0.05`):
    trend_mean   = MEAN(close, length)
    gate         = DELTA(trend_mean, length) / DELAY(close, length), +-inf -> NaN
    drawdown     = -(close - TSMIN(close, length))       # = TSMIN(close,length) - close, <= 0
    reversal     = -DELTA(close, reversal_length)
    raw          = gate <= threshold ? drawdown : reversal
    G191_098     = (raw / close), NaN wherever gate is NaN

WARM-UP. `trend_mean[t]` needs `length` bars, valid from `t >= length - 1`
(0-indexed). `DELTA(trend_mean, length)[t]` needs BOTH `trend_mean[t]` and
`trend_mean[t-length]` valid, i.e. `t - length >= length - 1`, i.e.
`t >= 2*length - 1` -- the binding constraint (looser than `DELAY(close,
length)`, which only needs `t >= length`, and looser than `TSMIN`/`DELTA(C,
reversal_length)`, both needing far fewer bars at the shipped defaults). So
`gate`, and therefore the whole column, is NaN for strictly fewer than
`2 * length` bars of history; `min_length = max(2 * length, reversal_length
+ 1)`, enforced by `verify_series`.

CAUSALITY. `trend_mean[t]` is a trailing rolling mean of `close[t-length+1
.. t]`, reading no bar past `t`. `gate[t]` combines `trend_mean[t]`,
`trend_mean[t-length]` and `close[t-length]` -- by induction, bars no newer
than `t` and no older than `t - 2*length + 1`. `drawdown[t]` is a trailing
rolling min of `close[t-length+1..t]` minus `close[t]` itself; `reversal[t]`
reads `close[t]` and `close[t-reversal_length]`. Every term is a function of
`close` at `t` or earlier; the ternary SELECTS between two already-causal
branches without reading anything new, and the final division by `close[t]`
reads only bar `t`. Nothing in the chain is shifted forward.
`tests/test_g191_098.py` proves this both by future-perturbation and by two
independent mutants (`importlib` source read, `exec`'d in memory), each
shown live (differs from the real module) and then caught at every offset
past the warm-up: shifting the final write index `length` bars into the
future, and replacing the backward `DELAY` (`close.shift(length)`) with a
FORWARD shift (`close.shift(-length)`) in the gate's denominator.

SCALE-FREE. Let `k > 0` rescale price (`close -> k*close`). `trend_mean ->
k*trend_mean` (linearity of a rolling mean), so `DELTA(trend_mean, length)
-> k*DELTA(trend_mean, length)` (linearity of a backward difference), and
`DELAY(close, length) -> k*DELAY(close, length)`. Therefore `gate` is
EXACTLY invariant under any positive price rescale -- the `k` cancels
before the `<= threshold` comparison even runs, so the BRANCH TAKEN at
every bar is identical pre- and post-rescale (this is why the ternary
itself needs no separate scale-free argument: it is a selector over an
invariant condition). `TSMIN(close, length) -> k*TSMIN(close, length)`
(rolling min commutes with a positive scale), so `drawdown -> k*drawdown`;
`DELTA(close, reversal_length) -> k*DELTA(close, reversal_length)`, so
`reversal -> k*reversal`. Either way, `raw -> k*raw`. The final division
`raw / close -> (k*raw) / (k*close) = raw / close` exactly. Measured on a
synthetic frame: `x8`/`x64` land bit-identical (power-of-two multiplication
is exact in IEEE754, so the algebraic cancellation is also exact in
float64), while `x10`/`x3.7` come out within float64 rounding tolerance.
Measured in the test file and `docs/measure_g191_098.py`, not merely
asserted.
"""
import numpy as np
import pandas as pd

from pandas_ta.utils import get_offset, verify_series


def g191_098(close, length=None, reversal_length=None, threshold=None,
             offset=None, **kwargs):
    """Indicator: 100-Day Trend-Gated Drawdown / 3-Day Reversal (G191_098)"""
    # Validate Arguments
    length = int(length) if length and length > 1 else 100
    reversal_length = int(reversal_length) if reversal_length and reversal_length >= 1 else 3
    threshold = float(threshold) if threshold is not None else 0.05
    min_length = max(2 * length, reversal_length + 1)
    close = verify_series(close, min_length)
    offset = get_offset(offset)

    if close is None:
        return

    # Calculate Result
    trend_mean = close.rolling(length, min_periods=length).mean()
    gate = (trend_mean - trend_mean.shift(length)) / close.shift(length)
    gate = gate.replace([np.inf, -np.inf], np.nan)

    drawdown = -(close - close.rolling(length, min_periods=length).min())
    reversal = -(close - close.shift(reversal_length))

    raw = pd.Series(
        np.where(gate <= threshold, drawdown, reversal), index=close.index
    )
    result = (raw / close).where(gate.notna())

    # Offset
    if offset != 0:
        result = result.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        result.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        result.fillna(method=kwargs["fill_method"], inplace=True)

    # Name & Category
    result.name = f"G191_098_{length}_{reversal_length}_{threshold}"
    result.category = "trend"

    return result


g191_098.__doc__ = \
"""100-Day Trend-Gated Drawdown / 3-Day Reversal (G191_098)

Guotai Junan's (2017, "GTJA191") alpha `#98`, per issue #58. A ternary gated
by how much a 100-bar moving average of `close` has itself drifted over the
last 100 bars, scaled by the close 100 bars ago: when that drift is small or
negative (a flat-or-declining trend), the column reports the negative
distance from the trailing 100-bar low (a drawdown read, zero at the low);
when the drift is large and positive (a strongly rising trend), it instead
reports the negated 3-bar price change (a short-horizon reversal read).
Full Gate A derivation, causality and scale-free arguments are in the
module source above; see docs/G191098Measured.md for the measured numbers.

Calculation:
    Default Inputs:
        length=100, reversal_length=3, threshold=0.05
    trend_mean = MEAN(close, length)
    gate       = DELTA(trend_mean, length) / DELAY(close, length), inf -> NaN
    drawdown   = -(close - TSMIN(close, length))
    reversal   = -DELTA(close, reversal_length)
    raw        = gate <= threshold ? drawdown : reversal
    G191_098   = raw / close, NaN wherever gate is NaN

Args:
    close (pd.Series): Series of 'close's
    length (int): Rolling window for the trend-mean gate and the drawdown
        low. Default: 100
    reversal_length (int): Backward difference window for the reversal
        branch. Default: 3
    threshold (float): Gate cutoff on the trend-mean's own relative drift.
        Default: 0.05
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.Series: G191_098_{length}_{reversal_length}_{threshold}, a scale-free
        (dimensionless) column. NaN for the first `2 * length - 1` bars
        (the gate's own warm-up, which dominates every other term's at the
        shipped defaults). `threshold` is embedded in the name via plain
        `str()` -- a non-default value with float repr noise (e.g.
        `0.3 - 0.2`) or far from 1 (scientific notation) renders as-is;
        pass a clean literal, matching every other float-tunable in this
        fork (`ffd`, `kalman_trend`).
"""
