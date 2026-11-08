# -*- coding: utf-8 -*-
"""Relative-volume rank x 7-day reversal rank -- Kakushadze's (2016, Wilmott,
"101 Formulaic Alphas") Alpha101 `#43`, per issue #46. Source cited by the
issue: Kakushadze (2016); vnpy's `vnpy/alpha101` module (MIT) is named by the
issue as the copy it read, but is NOT itself consulted in this session
(`docs/pine/` and web access are unavailable in this worktree) -- the formula
used here is the issue's own restatement of Kakushadze's published text, read
as the source per the issue's own instruction ("Gate A starts from the source
formula, not the prototype").

Issue #46's stated formula:

    ts_rank(volume/adv20, 20) * ts_rank(-delta(close, 7), 8)

OPERATORS, each read from Kakushadze's published glossary as restated by the
issue, not re-derived from vnpy:

* `adv(d)` = a trailing `d`-bar rolling mean of `volume`. **ASSUMPTION,
  disclosed:** Kakushadze's glossary defines `adv(d)` as the average DAILY
  DOLLAR volume (price times volume), not plain share volume. This fork
  already resolved the same ambiguity for `a101_021` (issue #45) by reading
  `adv(d)` as a plain volume rolling mean, because the issue's own prototype
  (`docs/issues/screen/ind_screen.py`'s `relv(v, n=20): return sdiv(v, mean(v,
  n))`) and its own disclosed "unchanged under price x8" invariant both
  require a volume-only `adv` -- a dollar-volume `adv` would carry a price
  term and break that invariant. The same reasoning applies verbatim here:
  `volume/adv20` must stay unchanged under a pure price rescale for the whole
  expression to be scale-free in `close` (see SCALE-FREE below), which only
  holds if `adv20` carries no price term. Reused for internal consistency
  with `a101_021`, not independently re-derived from vnpy.
* `delta(x, d)` = `x - x.shift(d)`, the plain `d`-bar difference.
* `ts_rank(x, d)` = the percentile rank of the current bar's value of `x`
  within its own trailing `d`-bar window: `count(x[t-d+1..t] <= x[t]) / d`.
  **ASSUMPTION, disclosed:** Kakushadze's glossary names the operator but
  does not spell out tie handling or the exact normalisation; this fork
  already ships two operators under this exact convention --
  `pandas_ta.statistics.rank`'s `RANK_d` for qlib's `Rank`, and
  `pandas_ta.volume.a101_058`'s own `_ts_rank` for Alpha101 `#58` (issue
  #42) -- so the same convention is reused here for internal consistency,
  not independently re-derived from vnpy. Duplicated locally rather than
  imported, matching `a101_058`'s own choice (CLAUDE.md: import a helper
  from its own module, never from another module or the package).

CALCULATION, in the order computed below:
    adv      = MEAN(volume, adv_length)                    # adv_length=20
    relvol   = volume / adv
    vrank    = TS_RANK(relvol, vol_rank_length)             # vol_rank_length=20
    d7       = DELTA(close, delta_length)                   # delta_length=7
    revrank  = TS_RANK(-d7, rev_rank_length)                 # rev_rank_length=8
    A101_043 = vrank * revrank

CAUSALITY. `adv` is a trailing rolling mean reading only `[t-adv_length+1
.. t]`; `relvol` is pointwise on `adv` and the current bar's `volume`;
`vrank` (the `sliding_window_view` in `_ts_rank` below) reads only
`relvol[t-vol_rank_length+1 .. t]`. `d7 = close - close.shift(delta_length)`
reads only `t` and `t-delta_length`; `revrank` reads only
`(-d7)[t-rev_rank_length+1 .. t]`. Nothing is shifted forward anywhere in the
chain. `tests/test_a101_043.py` proves this both by future-perturbation and
by a mutant (`importlib` source read, `exec`'d in memory) that shifts the
final write index `rev_rank_length` bars into the future: shown live (differs
from the real module), then caught at every offset past the warm-up.

SCALE-FREE. `relvol = volume / adv` is the ratio of two quantities that scale
identically under a positive rescale of `volume` (`adv` is linear/positively
homogeneous in `volume`), so `relvol` -- and hence `vrank`, an order
statistic of `relvol` -- is unchanged under a `volume` rescale; `close` does
not appear in this half at all. `d7 = close - close.shift(delta_length)`
scales by the same positive factor `k` as `close` under a `close` rescale, so
`-d7` does too, and `ts_rank` is an order statistic, invariant to any
monotonic (in particular any positive-linear) rescale of its input -- so
`revrank` is unchanged under a `close` rescale; `volume` does not appear in
this half at all. The product of the two is therefore scale-free under a
positive rescale of EITHER `close` OR `volume` independently. Measured in
the test file, not merely asserted.
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


def a101_043(close, volume, adv_length=None, vol_rank_length=None,
             delta_length=None, rev_rank_length=None, offset=None, **kwargs):
    """Indicator: Relative-Volume Rank x 7-Day Reversal Rank (A101_043)"""
    # Validate Arguments
    adv_length = int(adv_length) if adv_length and adv_length > 0 else 20
    vol_rank_length = int(vol_rank_length) if vol_rank_length and vol_rank_length > 0 else 20
    delta_length = int(delta_length) if delta_length and delta_length > 0 else 7
    rev_rank_length = int(rev_rank_length) if rev_rank_length and rev_rank_length > 0 else 8
    min_length = max(
        adv_length + vol_rank_length - 1,
        delta_length + rev_rank_length,
    )
    close = verify_series(close, min_length)
    volume = verify_series(volume, min_length)
    offset = get_offset(offset)

    if close is None or volume is None:
        return

    if not close.index.equals(volume.index):
        raise ValueError(
            "a101_043: `close` and `volume` are indexed differently. A "
            "ranked ratio read off misaligned series is a silent nonsense "
            "number."
        )

    # Calculate Result
    adv = volume.rolling(adv_length).mean()
    relvol = (volume / adv).replace([np.inf, -np.inf], np.nan)
    vrank = Series(_ts_rank(relvol.to_numpy(dtype=float), vol_rank_length), index=close.index)

    d7 = close.diff(delta_length)
    revrank = Series(_ts_rank((-d7).to_numpy(dtype=float), rev_rank_length), index=close.index)

    result = vrank * revrank

    # Offset
    if offset != 0:
        result = result.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        result.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        result.fillna(method=kwargs["fill_method"], inplace=True)

    # Name & Category
    result.name = f"A101_043_{adv_length}_{vol_rank_length}_{delta_length}_{rev_rank_length}"
    result.category = "momentum"

    return result


a101_043.__doc__ = \
"""Relative-Volume Rank x 7-Day Reversal Rank (A101_043)

Kakushadze's (2016, Wilmott, "101 Formulaic Alphas") Alpha101 `#43`, per
issue #46. Today's volume relative to its 20-bar average is time-series
ranked over the trailing 20 bars; the 7-bar price reversal (negated 7-bar
delta) is time-series ranked over the trailing 8 bars; the two ranks are
multiplied. High when volume is unusually elevated relative to its own
recent history AND the 7-bar price change has unusually reversed. Full Gate A
derivation, causality and scale-free arguments are in the module source
above; see docs/A101043Measured.md for the measured numbers.

Calculation:
    Default Inputs:
        adv_length=20, vol_rank_length=20, delta_length=7, rev_rank_length=8
    adv      = MEAN(volume, adv_length)
    relvol   = volume / adv
    vrank    = TS_RANK(relvol, vol_rank_length)   # count(relvol[t-19..t] <= relvol[t]) / 20
    d7       = DELTA(close, delta_length)         # close - close[7]
    revrank  = TS_RANK(-d7, rev_rank_length)       # count(-d7[t-7..t] <= -d7[t]) / 8
    A101_043 = vrank * revrank

Args:
    close (pd.Series): Series of 'close's
    volume (pd.Series): Series of 'volume's
    adv_length (int): Rolling window for the volume average. Default: 20
    vol_rank_length (int): Rolling window for the relative-volume rank. Default: 20
    delta_length (int): Lookback for the price delta. Default: 7
    rev_rank_length (int): Rolling window for the reversal rank. Default: 8
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.Series: A101_043_{adv_length}_{vol_rank_length}_{delta_length}_{rev_rank_length},
        a scale-free (dimensionless) product of two percentile ranks, on
        [1 / (vol_rank_length * rev_rank_length), 1] (each rank is itself on
        [1/d, 1]). NaN for the first
        max(adv_length + vol_rank_length - 2, delta_length + rev_rank_length - 1) bars.
"""
