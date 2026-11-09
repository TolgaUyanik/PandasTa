# -*- coding: utf-8 -*-
"""Seven-day mean gap plus 230-day VWAP/lagged-close correlation -- Guotai
Junan's (2017, "GTJA191", internal quant report, read via the
HKUDS/Vibe-Trading copy, MIT) alpha `#26`, per issue #56. Source cited by
the issue:

    #26: (SUM(C,7)/7 - C) + CORR(VWAP, DELAY(C,5), 230)

**What this session could NOT do, disclosed up front:** `docs/pine/` and web
access are both unavailable in this worktree, so the issue's own named copy
-- HKUDS/Vibe-Trading (MIT) -- was never read. The formula below is derived
from the issue's own stated text, per the issue's own instruction ("Gate A
starts from the source formula, not the prototype").

GATE A -- DERIVATION. `SUM(C,7)/7` is a 7-bar trailing mean of `close`
(`SUM` is a trailing rolling sum, so `SUM(C,7)/7 = MEAN(C,7)`), so the first
term is a price-unit mean-reversion gap: how far the close sits BELOW its
own trailing 7-bar average. The second term is a 230-bar trailing Pearson
correlation between the daily VWAP and the close lagged 5 bars. The issue's
own parenthetical states the scale-free conversion applied before Gate E
ever ran: "first term /close; VWAP -> (H+L+C)/3". The issue's own prototype
(`docs/issues/screen/ind_screen.py:339`) spells out the identical scale-free
form directly:

    (mean(c, 7) - c) / c + corr(tp(h, l, c), delay(c, 5), 230)

so this port divides ONLY the price-unit gap term by `C`, leaving the
already-unitless correlation term untouched, and uses the typical price
`(H+L+C)/3` as the VWAP proxy (no traded-value field in daily OHLCV):

    G191_026 = (MEAN(C, 7) - C) / C + CORR(TP, DELAY(C, 5), 230)

OPERATORS, each read directly off the prototype's own (unambiguous) module
docstring, the same source g191_191 (issue #53) relied on for `MEAN`/`CORR`:

* `MEAN(X, n)` = a trailing `n`-bar rolling mean, `X.rolling(n).mean()`.
  Matches the prototype's own `mean(x, n): return x.rolling(n).mean()`.
* `DELAY(X, n)` = `X.shift(n)`, matching the prototype's own
  `delay(x, n): return x.shift(n)` -- a BACKWARD-looking shift (bar `t`
  reads bar `t-n`), never a look-ahead.
* `CORR(X, Y, n)` = a trailing `n`-bar rolling Pearson correlation,
  `X.rolling(n).corr(Y)`. Matches the prototype's own
  `corr(x, y, n): return _fin(x.rolling(n).corr(y))` (`_fin` replaces
  `[inf, -inf]` with `NaN`; this port applies the same replacement to its
  own division by `C`, for the symmetric reason: a near-zero `C` would
  otherwise produce `+-inf` rather than a defined number).
* `H`, `L`, `C` = high, low, close. `VWAP` has no traded-value field in
  daily OHLCV, so this port uses the typical price `(H+L+C)/3`, matching
  the prototype's own `tp(h, l, c): return (h + l + c) / 3`.

CALCULATION, in the order computed below (`mean_length=7`, `lag=5`,
`corr_length=230`):
    tp         = (H + L + C) / 3
    gap_term   = (MEAN(C, mean_length) - C) / C
    lagged_c   = DELAY(C, lag)
    corr_term  = CORR(tp, lagged_c, corr_length)
    G191_026   = gap_term + corr_term, inf -> NaN

CAUSALITY. `gap_term[t]` is a trailing rolling mean of `C[t-mean_length+1..t]`
minus `C[t]`, divided by `C[t]` -- reads no bar past `t`. `lagged_c[t] =
C[t-lag]`, strictly BEFORE `t` for `lag > 0` -- never a look-ahead.
`corr_term[t]` is a trailing rolling Pearson correlation of
`tp[t-corr_length+1..t]` against `lagged_c[t-corr_length+1..t]` =
`C[t-corr_length+1-lag..t-lag]`, the oldest bar read being
`t-corr_length+1-lag`, strictly in the past. Nothing is shifted forward
anywhere in the chain. `tests/test_g191_026.py` proves this both by
future-perturbation and by two independent mutants (`importlib` source
read, `exec`'d in memory), each shown live (differs from the real module)
and then caught at every offset past the warm-up: shifting the final write
index `corr_length` bars into the future, and replacing the backward
`DELAY` (`close.shift(lag)`) with a FORWARD shift
(`close.shift(-lag)`) -- turning the lag term into a look-ahead.

SCALE-FREE. Pearson correlation is exactly invariant to a positive rescale
of either input: for any `k > 0`, `corr(k*X, Y) = corr(X, Y)` algebraically
(the `k` cancels between the covariance and the standard-deviation terms).
Rescaling `H`, `L`, `C` by `k` rescales `tp` by the same `k` (linearity) and
`lagged_c` by the same `k` (a shift commutes with a scalar multiply), so
`corr_term` is untouched under ANY positive price rescale. `gap_term` is
likewise untouched: `(MEAN(k*C, mean_length) - k*C) / (k*C) =
(MEAN(C, mean_length) - C) / C`, the `k` cancels algebraically. Measured on
a synthetic frame: `x8`/`x64` land bit-identical (power-of-two
multiplication is exact in IEEE754, so the algebraic cancellation is also
exact in float64), while `x10`/`x3.7` come out within float64 rounding
tolerance of the unscaled column. Measured in the test file and
`docs/measure_g191_026.py`, not merely asserted.
"""
import numpy as np

from pandas_ta.utils import get_offset, verify_series


def g191_026(high, low, close, mean_length=None, corr_length=None, lag=None,
             offset=None, **kwargs):
    """Indicator: Seven-Day Mean Gap Plus VWAP/Lagged-Close Correlation (G191_026)"""
    # Validate Arguments
    mean_length = int(mean_length) if mean_length and mean_length > 1 else 7
    corr_length = int(corr_length) if corr_length and corr_length > 1 else 230
    lag = int(lag) if lag and lag > 0 else 5
    min_length = max(mean_length, lag + corr_length)
    high = verify_series(high, min_length)
    low = verify_series(low, min_length)
    close = verify_series(close, min_length)
    offset = get_offset(offset)

    if high is None or low is None or close is None:
        return

    # Calculate Result
    tp = (high + low + close) / 3.0
    gap_term = (close.rolling(mean_length).mean() - close) / close
    lagged_close = close.shift(lag)
    corr_term = tp.rolling(corr_length, min_periods=corr_length).corr(lagged_close)

    # NaN from either term already propagates through float addition; no
    # explicit mask needed before the inf -> NaN replacement.
    result = (gap_term + corr_term).replace([np.inf, -np.inf], np.nan)

    # Offset
    if offset != 0:
        result = result.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        result.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        result.fillna(method=kwargs["fill_method"], inplace=True)

    # Name & Category
    result.name = f"G191_026_{mean_length}_{corr_length}_{lag}"
    result.category = "statistics"

    return result


g191_026.__doc__ = \
"""Seven-Day Mean Gap Plus VWAP/Lagged-Close Correlation (G191_026)

Guotai Junan's (2017, "GTJA191") alpha `#26`, per issue #56. A mean-reversion
gap (how far the close sits below its own trailing 7-bar average, as a
fraction of the close) added to a long-horizon (230-bar) Pearson correlation
between the daily typical price and the close lagged 5 bars: a persistent
positive correlation there means the typical price has been tracking where
the close was 5 bars ago, i.e. slow-moving trend-following. Full Gate A
derivation, causality and scale-free arguments are in the module source
above; see docs/G191026Measured.md for the measured numbers.

Calculation:
    Default Inputs:
        mean_length=7, corr_length=230, lag=5
    tp         = (high + low + close) / 3
    gap_term   = (MEAN(close, mean_length) - close) / close
    lagged_c   = DELAY(close, lag)
    corr_term  = CORR(tp, lagged_c, corr_length)
    G191_026   = gap_term + corr_term, inf -> NaN

Args:
    high (pd.Series): Series of 'high's
    low (pd.Series): Series of 'low's
    close (pd.Series): Series of 'close's
    mean_length (int): Rolling window for the mean-reversion gap. Default: 7
    corr_length (int): Rolling window for the correlation. Default: 230
    lag (int): Backward shift applied to close before the correlation. Default: 5
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.Series: G191_026_{mean_length}_{corr_length}_{lag}, a scale-free
        (dimensionless) column: a small price-relative gap plus a
        correlation in `[-1, 1]`. The gap and correlation terms are
        computed in PARALLEL (neither feeds the other), so the warm-up is
        whichever term is slower: NaN for the first
        max(mean_length, lag + corr_length) - 1 bars.
"""
