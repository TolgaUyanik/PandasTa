# -*- coding: utf-8 -*-
"""Volume rank x price rank x return rank -- Kakushadze's (2016, Wilmott,
"101 Formulaic Alphas") Alpha101 `#35`, per issue #50. Source cited by the
issue: Kakushadze (2016); vnpy's `vnpy/alpha101` module (MIT) is named by the
issue as the copy it read, but is NOT itself consulted in this session
(`docs/pine/` and web access are unavailable in this worktree) -- the formula
used here is the issue's own restatement, read as the source per the issue's
own instruction ("Gate A starts from the source formula, not the prototype").

Issue #50's stated formula:

    ts_rank(volume, 32) * (1 - ts_rank(close + high - low, 16)) * (1 - ts_rank(returns, 32))

No `IndNeutralize` wrapper and no `vwap` substitution are involved -- unlike
`a101_048`/`a101_058`, this formula is already stated in terms of plain
OHLCV series this fork has.

OPERATORS, read directly off the formula string:

* `ts_rank(x, d)` = the percentile rank of the current bar's value of `x`
  within its own trailing `d`-bar window: `count(x[t-d+1..t] <= x[t]) / d`.
  Same convention already shipped under this exact name by `a101_058` (issue
  #42) and, underneath it, by `pandas_ta.statistics.rank`'s `RANK_d` (issue
  #34, a port of qlib's `Rank`). ASSUMPTION, disclosed, carried over
  unchanged from `a101_058`: Kakushadze's glossary names the operator but
  does not spell out tie handling or normalisation, so this fork's own
  existing convention is reused for internal consistency, not independently
  re-derived from vnpy.
* `returns` = the plain one-bar simple return `close[t] / close[t-1] - 1`,
  the same convention already used by `a101_048`'s `r = close.pct_change(
  fill_method=None)`.

CALCULATION, in the order computed below:
    returns  = close.pct_change(fill_method=None)      # close[t]/close[t-1] - 1
    vol_rank = TS_RANK(volume, vol_length)              # vol_length=32
    pr_rank  = TS_RANK(close + high - low, price_length)  # price_length=16
    ret_rank = TS_RANK(returns, return_length)          # return_length=32
    A101_035 = vol_rank * (1 - pr_rank) * (1 - ret_rank)

CAUSALITY. `TS_RANK` at bar `t` reads only its own trailing `length`-bar
window ending at `t` (see `_ts_rank` below, a `sliding_window_view` that never
indexes past its last element); `close + high - low` and `pct_change` are
both pointwise/one-bar-back combinations of the current and immediately
prior bar. Nothing anywhere in the chain is shifted forward.
`tests/test_a101_035.py` proves this both by future-perturbation and by a
mutant (`importlib` source read, `exec`'d in memory) that shifts the final
write index into the future: shown live (differs from the real module), then
caught at every offset past the warm-up.

SCALE-FREE. `TS_RANK` is an order statistic: for `k > 0`, a bar's value
within a window and the whole window are rescaled identically, so the
`<=` comparisons and hence every count/rank are mathematically unchanged --
`ts_rank` is invariant under any positive monotonic rescale of its input,
applied independently to `volume` or to `close`/`high`/`low` together.
`returns` is itself scale-free under a uniform price rescale in exact
arithmetic (`(k*c[t])/(k*c[t-1]) - 1 == c[t]/c[t-1] - 1`, the `k` cancels).
The whole product is a product of three already-bounded, dimensionless
ranks. Power-of-two rescale (x8/x64) is bit-identical as a mathematical
certainty: IEEE754 multiplication by a power of two is exact, so every
intermediate value here is either unchanged or exactly scaled, and the
rank comparisons see no rounding at all. x10/x3.7 are NOT powers of two, so
exact cancellation in `returns`' division is not guaranteed by IEEE754 the
same way -- `tests/test_a101_035.py` MEASURES these two cases rather than
assuming them, and finds them bit-identical too on the tested synthetic
frame (`docs/measure_a101_035.py`), because the only way a `1e-16`-scale
rounding difference changes `ts_rank`'s integer count is an exact tie at
the bit level, which this frame's continuous-valued synthetic data does not
produce. That is an empirical property of the tested data, not a proof that
no input can ever flip a tie.
"""
import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from pandas import Series

from pandas_ta.utils import get_offset, verify_series


def _ts_rank(values: np.ndarray, length: int) -> np.ndarray:
    """Percentile rank of the LAST bar of each trailing `length`-bar window:
    count(window <= last) / length. Reads only the window ending at the
    current bar -- no bar past `t` is ever touched."""
    n = len(values)
    out = np.full(n, np.nan)
    if length > n:
        return out
    windows = sliding_window_view(values, length)
    last = windows[:, -1]
    valid = np.all(np.isfinite(windows), axis=1)
    counts = np.sum(windows <= last[:, None], axis=1)
    out[length - 1:] = np.where(valid, counts / length, np.nan)
    return out


def a101_035(high, low, close, volume, vol_length=None, price_length=None,
             return_length=None, offset=None, **kwargs):
    """Indicator: Volume Rank x Price Rank x Return Rank (A101_035)"""
    # Validate Arguments
    vol_length = int(vol_length) if vol_length and vol_length > 1 else 32
    price_length = int(price_length) if price_length and price_length > 1 else 16
    return_length = int(return_length) if return_length and return_length > 1 else 32
    # returns has 1 leading NaN (pct_change), so its own window needs
    # return_length bars AFTER that NaN -- the binding term below.
    min_length = max(vol_length - 1, price_length - 1, return_length) + 1
    high = verify_series(high, min_length)
    low = verify_series(low, min_length)
    close = verify_series(close, min_length)
    volume = verify_series(volume, min_length)
    offset = get_offset(offset)

    if high is None or low is None or close is None or volume is None:
        return

    if not (high.index.equals(low.index) and high.index.equals(close.index)
            and high.index.equals(volume.index)):
        raise ValueError(
            "a101_035: `high`, `low`, `close` and `volume` are indexed "
            "differently. Ranking misaligned series is a silent nonsense "
            "number."
        )

    # Calculate Result
    returns = close.pct_change(fill_method=None)
    price_term = close + high - low
    vol_rank = Series(_ts_rank(volume.to_numpy(dtype=float), vol_length), index=volume.index)
    pr_rank = Series(_ts_rank(price_term.to_numpy(dtype=float), price_length), index=price_term.index)
    ret_rank = Series(_ts_rank(returns.to_numpy(dtype=float), return_length), index=returns.index)
    result = vol_rank * (1 - pr_rank) * (1 - ret_rank)

    # Offset
    if offset != 0:
        result = result.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        result.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        result.fillna(method=kwargs["fill_method"], inplace=True)

    # Name & Category
    result.name = f"A101_035_{vol_length}_{price_length}_{return_length}"
    result.category = "volume"

    return result


a101_035.__doc__ = \
"""Volume Rank x Price Rank x Return Rank (A101_035)

Kakushadze's (2016, Wilmott, "101 Formulaic Alphas") Alpha101 `#35`, per
issue #50. Three trailing-window percentile ranks multiplied together: how
high today's volume sits in its own recent history, how LOW today's
`close + high - low` sits in its own recent history (via `1 - rank`), and how
LOW today's 1-bar return sits in its own recent history (via `1 - rank`) --
high when volume is unusually heavy while price range and returns have been
unusually weak. Full Gate A derivation, causality and scale-free arguments
are in the module source above; see docs/A101035Measured.md for the measured
numbers.

Calculation:
    Default Inputs:
        vol_length=32, price_length=16, return_length=32
    returns  = close.pct_change()                         # close[t]/close[t-1] - 1
    VR       = TS_RANK(volume, vol_length)                 # count(<=current)/vol_length
    PR       = TS_RANK(close + high - low, price_length)
    RR       = TS_RANK(returns, return_length)
    A101_035 = VR * (1 - PR) * (1 - RR)

Args:
    high (pd.Series): Series of 'high's
    low (pd.Series): Series of 'low's
    close (pd.Series): Series of 'close's
    volume (pd.Series): Series of 'volume's
    vol_length (int): Rolling window for the volume rank. Default: 32
    price_length (int): Rolling window for the price-range rank. Default: 16
    return_length (int): Rolling window for the return rank. Default: 32
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.Series: A101_035_{vol_length}_{price_length}_{return_length}, a
        scale-free (dimensionless) product of three ranks, bounded on
        [0, 1). NaN for the first
        max(vol_length - 1, price_length - 1, return_length) bars.
"""
