# -*- coding: utf-8 -*-
"""Volume-high rank correlation peak -- Kakushadze's (2016, Wilmott, "101
Formulaic Alphas") Alpha101 `#26`, per issue #44. Source cited by the issue:
Kakushadze (2016); vnpy's `vnpy/alpha101` module (MIT) is named by the issue
as the copy it read, but is NOT itself consulted in this session (`docs/pine/`
and web access are unavailable in this worktree) -- the formula used here is
the issue's own restatement, read as the source per the issue's own
instruction ("Gate A starts from the source formula, not the prototype").

Issue #44's stated formula:

    -ts_max(corr(ts_rank(volume, 5), ts_rank(high, 5), 5), 3)

No `IndNeutralize` wrapper and no `vwap` substitution are involved -- the
formula is already stated in terms of plain `volume` and `high`, which this
fork has directly; `low` and `close` are not read anywhere in it.

OPERATORS, each read from the issue's formula string:

* `ts_rank(x, d)` = the percentile rank of the current bar's value of `x`
  within its own trailing `d`-bar window: `count(x[t-d+1..t] <= x[t]) / d`.
  Same convention already shipped under this exact name by `a101_035`/
  `a101_058` and, underneath it, by `pandas_ta.statistics.rank`'s `RANK_d`
  (issue #34, a port of qlib's `Rank`). ASSUMPTION, disclosed, carried over
  unchanged from those two ports: Kakushadze's glossary names the operator
  but does not spell out tie handling or normalisation, so this fork's own
  existing convention is reused for internal consistency, not independently
  re-derived from vnpy.
* `corr(x, y, d)` = rolling Pearson correlation of `x` and `y` over a
  trailing `d`-bar window. Reused verbatim from `pandas_ta.utils._pine
  .correlation`, the same rolling-Pearson primitive `pvcorr` and `a101_058`
  already ship behind -- not a fresh implementation.
* `ts_max(x, d)` = the rolling maximum of `x` over its own trailing `d`-bar
  window, `max(x[t-d+1..t])`. Not previously named by any port in this fork,
  but there is nothing to assume: a trailing rolling maximum is `pandas`'
  own `Series.rolling(d).max()`, read off literally.

CALCULATION, in the order computed below:
    vol_rank  = TS_RANK(volume, vol_rank_length)         # vol_rank_length=5
    high_rank = TS_RANK(high, high_rank_length)          # high_rank_length=5
    corr_ser  = CORR(vol_rank, high_rank, corr_length)   # corr_length=5
    peak      = TS_MAX(corr_ser, max_length)             # max_length=3
    A101_026  = -peak

CAUSALITY. `TS_RANK` at bar `t` reads only its own trailing `length`-bar
window ending at `t` (see `_ts_rank` below, a `sliding_window_view` that never
indexes past its last element); `.rolling(length).corr()` and
`.rolling(length).max()` are both trailing by construction. Nothing anywhere
in the chain is shifted forward. `tests/test_a101_026.py` proves this both by
future-perturbation and by a mutant (`importlib` source read, `exec`'d in
memory) that shifts the final write index `max_length` bars into the future:
shown live (differs from the real module), then caught at every offset past
the warm-up.

SCALE-FREE. `TS_RANK` is an order statistic: for `k > 0`, a bar's value
within a window and the whole window are rescaled identically, so the `<=`
comparisons and hence every count/rank are mathematically unchanged --
`ts_rank` is invariant under any positive monotonic rescale of its input,
applied independently to `volume` or to `high`. `corr` is a correlation
coefficient, scale-invariant by definition in either argument, and here its
two arguments are themselves already scale-free ranks, so the invariance
holds twice over. `TS_MAX` of an already scale-free, bounded `[-1, 1]`
series inherits the bound, and negation preserves it. Power-of-two rescale
(x8/x64) is bit-identical as a mathematical certainty: IEEE754 multiplication
by a power of two is exact, so every intermediate value here is either
unchanged or exactly scaled, and the rank comparisons see no rounding at
all. x10/x3.7 are NOT powers of two, so exact cancellation is not guaranteed
by IEEE754 the same way -- `tests/test_a101_026.py` MEASURES these two cases
rather than assuming them.
"""
import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from pandas import Series

from pandas_ta.utils import get_offset, verify_series
from pandas_ta.utils._pine import correlation as _rolling_pearson


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


def a101_026(high, volume, vol_rank_length=None, high_rank_length=None,
             corr_length=None, max_length=None, offset=None, **kwargs):
    """Indicator: Volume-High Rank Correlation Peak (A101_026)"""
    # Validate Arguments
    vol_rank_length = int(vol_rank_length) if vol_rank_length and vol_rank_length > 1 else 5
    high_rank_length = int(high_rank_length) if high_rank_length and high_rank_length > 1 else 5
    corr_length = int(corr_length) if corr_length and corr_length > 1 else 5
    max_length = int(max_length) if max_length and max_length > 1 else 3
    # vol_rank/high_rank need their own (length-1)-bar warm-up before corr's
    # own window can start, and ts_max needs max_length valid corr values --
    # the binding term below.
    min_length = max(vol_rank_length, high_rank_length) + corr_length + max_length - 2
    high = verify_series(high, min_length)
    volume = verify_series(volume, min_length)
    offset = get_offset(offset)

    if high is None or volume is None:
        return

    if not high.index.equals(volume.index):
        raise ValueError(
            "a101_026: `high` and `volume` are indexed differently. A "
            "correlation read off misaligned series is a silent nonsense "
            "number."
        )

    # Calculate Result
    vol_rank = Series(_ts_rank(volume.to_numpy(dtype=float), vol_rank_length), index=volume.index)
    high_rank = Series(_ts_rank(high.to_numpy(dtype=float), high_rank_length), index=high.index)
    corr_series = _rolling_pearson(vol_rank, high_rank, corr_length)
    peak = corr_series.rolling(max_length, min_periods=max_length).max()
    result = -peak

    # Offset
    if offset != 0:
        result = result.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        result.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        result.fillna(method=kwargs["fill_method"], inplace=True)

    # Name & Category
    result.name = f"A101_026_{vol_rank_length}_{high_rank_length}_{corr_length}_{max_length}"
    result.category = "volume"

    return result


a101_026.__doc__ = \
"""Volume-High Rank Correlation Peak (A101_026)

Kakushadze's (2016, Wilmott, "101 Formulaic Alphas") Alpha101 `#26`, per
issue #44. Volume and high are each time-series ranked within their own
trailing window, the two rank series are rolling-correlated, and the
trailing peak of that correlation is negated -- high (very negative) when
volume and high have recently moved in lock-step at some point in the last
`max_length` bars. Full Gate A derivation, causality and scale-free
arguments are in the module source above; see docs/A101026Measured.md for
the measured numbers.

Calculation:
    Default Inputs:
        vol_rank_length=5, high_rank_length=5, corr_length=5, max_length=3
    VR       = TS_RANK(volume, vol_rank_length)        # count(<=current)/vol_rank_length
    HR       = TS_RANK(high, high_rank_length)
    C        = CORR(VR, HR, corr_length)               # rolling Pearson
    PEAK     = TS_MAX(C, max_length)                   # rolling max
    A101_026 = -PEAK

Args:
    high (pd.Series): Series of 'high's
    volume (pd.Series): Series of 'volume's
    vol_rank_length (int): Rolling window for the volume rank. Default: 5
    high_rank_length (int): Rolling window for the high rank. Default: 5
    corr_length (int): Rolling window for the rank correlation. Default: 5
    max_length (int): Rolling window for the trailing peak. Default: 3
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.Series: A101_026_{vol_rank_length}_{high_rank_length}_{corr_length}_
        {max_length}, a scale-free (dimensionless) negated rolling-max
        correlation, bounded on [-1, 1]. NaN for the first
        max(vol_rank_length, high_rank_length) + corr_length + max_length - 3
        bars.
"""
