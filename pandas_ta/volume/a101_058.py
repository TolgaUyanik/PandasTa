# -*- coding: utf-8 -*-
"""Decayed price-volume correlation rank -- Kakushadze's (2016, Wilmott, "101
Formulaic Alphas") Alpha101 `#58`, without its cross-sectional `IndNeutralize`
wrapper (this fork has no sector/industry classification to neutralise
against), per issue #42. Source cited by the issue: Kakushadze (2016); vnpy's
`vnpy/alpha101` module (MIT) is named by the issue as the copy it read, but
is NOT itself consulted in this session (`docs/pine/` and web access are
unavailable in this worktree) -- the formula used here is the issue's own
restatement of Kakushadze's published text, read as the source per the
issue's own instruction ("Gate A starts from the source formula, not the
prototype").

Issue #42's stated formula (`IndNeutralize` dropped):

    -ts_rank(decay_linear(corr(vwap, volume, 4), 8), 6)

with the issue's own scale-free substitution for `vwap` -- "vwap ->
(H+L+C)/3" -- since this fork's `vwap` is a volume-weighted price level, not
the scale-free proxy the issue asks for here.

OPERATORS, each read from Kakushadze's published glossary as restated by the
issue, not re-derived from vnpy:

* `corr(x, y, d)` = rolling Pearson correlation of `x` and `y` over a
  trailing `d`-bar window. Reused verbatim from `pvcorr`'s own helper
  (`pandas_ta.utils._pine.correlation`), a rolling-Pearson primitive already
  shared by one other port -- not a fresh implementation.
* `decay_linear(x, d)` = a `d`-bar weighted moving average of `x` with
  linearly increasing weights, the heaviest weight on the most recent bar:
  weight `i` bars back (0-indexed from the current bar) is `d - i`, divided
  by `sum(1..d)`. This is EXACTLY `pandas_ta.overlap.wma`'s own definition at
  `asc=True` (ascending weights `[1, 2, ..., d]` dotted against a rolling
  window whose last element is the current bar, i.e. the current bar gets
  weight `d`, the oldest gets weight `1`) -- reused, not reimplemented.
* `ts_rank(x, d)` = the percentile rank of the current bar's value of `x`
  within its own trailing `d`-bar window: `count(x[t-d+1..t] <= x[t]) / d`.
  ASSUMPTION, disclosed: Kakushadze's glossary names the operator but does
  not spell out tie handling or the exact normalisation; this fork already
  ships one operator under this exact name and convention --
  `pandas_ta.statistics.rank`'s `RANK_d[t] = count(close[t-d+1..t] <=
  close[t]) / d` for qlib's `Rank` -- so the same convention is used here for
  internal consistency, not independently re-derived from vnpy. See
  docs/A101058Measured.md.

CALCULATION, in the order computed below:
    typical = (high + low + close) / 3                        # vwap proxy, issue's own substitution
    corr_series = CORR(typical, volume, corr_length)           # rolling Pearson
    decayed = WMA(corr_series, decay_length, asc=True)         # decay_linear
    ranked = TS_RANK(decayed, rank_length)                     # count(<=current)/rank_length, in (0, 1]
    A101_058 = -ranked

CAUSALITY. Every step is a trailing rolling window (`corr`, `wma`, the
`sliding_window_view` in `_ts_rank` below) reading only `[t-d+1 .. t]`;
nothing is shifted forward. `tests/test_a101_058.py` proves this both by
future-perturbation and by a mutant that shifts the final write index
`rank_length` bars into the future (the negated-ranked assignment gains a
`.shift()` by `-rank_length` positions). A single-bar lookahead inside the
correlation step was tried first and rejected as the mutant: `ts_rank`'s
6-bucket output sometimes absorbs a 1-bar perturbation without changing
bucket (11/15 offsets caught), a quantisation artefact of the final rank
step rather than a causality gap -- see the test module's docstring.

SCALE-FREE. `corr` is a correlation coefficient (scale-invariant by
definition, for both inputs independently); `decay_linear` is a weighted
average of an already scale-free, bounded [-1, 1] series, so it inherits the
bound; `ts_rank` is an order statistic, invariant to any monotonic rescale of
its input. The whole chain is scale-free by construction (not by an added
normalisation step), for a positive rescale of EITHER `high`/`low`/`close` OR
`volume` independently. Measured in the test file, not merely asserted.
"""
import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from pandas import Series

from pandas_ta.overlap.wma import wma
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


def a101_058(high, low, close, volume, corr_length=None, decay_length=None,
             rank_length=None, offset=None, **kwargs):
    """Indicator: Decayed Price-Volume Correlation Rank (A101_058)"""
    # Validate Arguments
    corr_length = int(corr_length) if corr_length and corr_length > 1 else 4
    decay_length = int(decay_length) if decay_length and decay_length > 0 else 8
    rank_length = int(rank_length) if rank_length and rank_length > 0 else 6
    min_length = corr_length + decay_length + rank_length - 2
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
            "a101_058: `high`, `low`, `close` and `volume` are indexed "
            "differently. A correlation read off misaligned series is a "
            "silent nonsense number."
        )

    # Calculate Result
    typical = (high + low + close) / 3  # vwap proxy, per the issue's own scale-free substitution
    corr_series = _rolling_pearson(typical, volume, corr_length)
    decayed = wma(corr_series, length=decay_length, asc=True)
    ranked = Series(_ts_rank(decayed.to_numpy(dtype=float), rank_length), index=decayed.index)
    result = -ranked

    # Offset
    if offset != 0:
        result = result.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        result.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        result.fillna(method=kwargs["fill_method"], inplace=True)

    # Name & Category
    result.name = f"A101_058_{corr_length}_{decay_length}_{rank_length}"
    result.category = "volume"

    return result


a101_058.__doc__ = \
"""Decayed Price-Volume Correlation Rank (A101_058)

Kakushadze's (2016, Wilmott, "101 Formulaic Alphas") Alpha101 `#58`, without
its cross-sectional `IndNeutralize` wrapper (this fork has no sector/industry
classification), per issue #42. A rolling price-volume correlation is
decay-weighted toward its most recent value, then time-series ranked within
its own trailing window, negated. Full Gate A derivation, causality and
scale-free arguments are in the module source above; see
docs/A101058Measured.md for the measured numbers.

Calculation:
    Default Inputs:
        corr_length=4, decay_length=8, rank_length=6
    typical = (high + low + close) / 3                   # vwap proxy (issue's own substitution)
    C       = CORR(typical, volume, corr_length)          # rolling Pearson
    D       = WMA(C, decay_length, asc=True)              # decay_linear: heaviest weight on the newest bar
    R       = TS_RANK(D, rank_length)                     # count(D[t-rank_length+1..t] <= D[t]) / rank_length
    A101_058 = -R

Args:
    high (pd.Series): Series of 'high's
    low (pd.Series): Series of 'low's
    close (pd.Series): Series of 'close's
    volume (pd.Series): Series of 'volume's
    corr_length (int): Rolling window for the price-volume correlation. Default: 4
    decay_length (int): Rolling window for the linear-decay weighting. Default: 8
    rank_length (int): Rolling window for the time-series rank. Default: 6
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.Series: A101_058_{corr_length}_{decay_length}_{rank_length}, a
        scale-free (dimensionless) negated percentile rank, bounded on
        [-1, -1/rank_length]. NaN for the first
        corr_length + decay_length + rank_length - 3 bars.
"""
