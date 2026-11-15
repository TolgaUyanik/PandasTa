# -*- coding: utf-8 -*-
"""Volume-gated 7-day move rank -- Kakushadze's (2016, Wilmott, "101
Formulaic Alphas") Alpha101 `#7`, per issue #51. Source cited by the issue:
Kakushadze (2016); vnpy's `vnpy/alpha101` module (MIT) is named by the issue
as the copy it read, but is NOT itself consulted in this session
(`docs/pine/` and web access are unavailable in this worktree) -- the formula
used here is the issue's own restatement of Kakushadze's published text, read
as the source per the issue's own instruction ("Gate A starts from the source
formula, not the prototype").

Issue #51's stated formula:

    adv20<volume ? -ts_rank(|delta(close,7)|,60)*sign(delta(close,7)) : -1

OPERATORS, each read from Kakushadze's published glossary as restated by the
issue, not re-derived from vnpy:

* `adv(d)` = a trailing `d`-bar rolling mean of `volume`. **ASSUMPTION,
  disclosed:** Kakushadze's glossary defines `adv(d)` as the average DAILY
  DOLLAR volume (price times volume), not plain share volume. This fork
  already resolved the identical ambiguity for `a101_021` (issue #45) and
  `a101_043` (issue #46) by reading `adv(d)` as a plain volume rolling mean,
  because the issue's own prototype (`docs/issues/screen/ind_screen.py`'s
  `relv(v, n=20): return sdiv(v, mean(v, n))`) and its own disclosed
  "unchanged under price x8" invariant both require a volume-only `adv` -- a
  dollar-volume `adv` would carry a price term and break that invariant for
  any formula that also compares `adv` against plain `volume` or a price
  series. The same reasoning applies here: for the `adv20<volume` gate to stay
  unchanged under a pure price rescale (see SCALE-FREE below), `adv20` must
  carry no price term at all. Reused for internal consistency with
  `a101_021`/`a101_043`, not independently re-derived from vnpy.
* `delta(x, d)` = `x - x.shift(d)`, the plain `d`-bar difference.
* `ts_rank(x, d)` = the percentile rank of the current bar's value of `x`
  within its own trailing `d`-bar window: `count(x[t-d+1..t] <= x[t]) / d`.
  **ASSUMPTION, disclosed:** Kakushadze's glossary names the operator but
  does not spell out tie handling or the exact normalisation; this fork
  already ships this exact convention under the same name in
  `pandas_ta.statistics.rank`'s `RANK_d`, `pandas_ta.volume.a101_058`'s
  `_ts_rank` and `pandas_ta.momentum.a101_043`'s `_ts_rank` -- so the same
  convention is reused here for internal consistency, not independently
  re-derived from vnpy. Duplicated locally rather than imported, matching
  those ports' own choice (CLAUDE.md: import a helper from its own module,
  never from another module or the package).
* `sign(x)` = `numpy.sign`: `+1` for `x > 0`, `-1` for `x < 0`, `0` for
  `x == 0`. Read directly off the formula string, no ambiguity to disclose.

CALCULATION, in the order computed below:
    adv      = MEAN(volume, adv_length)                 # adv_length=20
    d7       = DELTA(close, delta_length)                # delta_length=7
    tsrank   = TS_RANK(|d7|, ts_rank_length)              # ts_rank_length=60
    gated    = -tsrank * SIGN(d7)
    A101_007 = (volume > adv) ? gated : -1.0

CAUSALITY. `adv` is a trailing rolling mean reading only `[t-adv_length+1 ..
t]`. `d7 = close - close.shift(delta_length)` reads only `t` and
`t-delta_length`. `tsrank` (the `sliding_window_view` in `_ts_rank` below)
reads only `|d7|[t-ts_rank_length+1 .. t]`, each of which itself reads no
later than `t`. `sign(d7)` and the final branch selection are pointwise on
already-backward-looking series. Nothing is shifted forward anywhere in the
chain. `tests/test_a101_007.py` proves this both by future-perturbation and
by a mutant (`importlib` source read, `exec`'d in memory) that shifts the
final write index `ts_rank_length` bars into the future: shown live (differs
from the real module), then caught at every offset past the warm-up.

SCALE-FREE. Scaling `close` by a positive constant `k` scales `d7` by the
same `k` (a plain difference is linear/positively homogeneous in `close`), so
`|d7|` scales by `k` too (`k > 0`), and `ts_rank` is an order statistic,
invariant to any positive rescale of its own input -- `tsrank` is therefore
unchanged. `sign(d7)` is also unchanged under a positive rescale (sign is
invariant to any positive multiplier). `volume` and `adv` never read `close`,
so the gate `volume > adv` is untouched by a price rescale. The whole chain
is therefore unchanged -- not merely linearly rescaled -- by a positive
rescale of `close`. Scaling `volume` by a positive constant `k` scales
`volume` and `adv` identically (`adv` is linear/positively homogeneous in
`volume`), so the strict inequality `volume > adv` keeps the same truth value
at every bar (`k > 0` preserves strict ordering and ties alike); `close`
never appears in the `tsrank`/`sign` half, so that half is untouched by a
volume rescale. The whole chain is therefore scale-free by construction, for
a positive rescale of EITHER `close` OR `volume` independently. Measured in
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


def a101_007(close, volume, adv_length=None, delta_length=None,
             ts_rank_length=None, offset=None, **kwargs):
    """Indicator: Volume-Gated 7-Day Move Rank (A101_007)"""
    # Validate Arguments
    adv_length = int(adv_length) if adv_length and adv_length > 0 else 20
    delta_length = int(delta_length) if delta_length and delta_length > 0 else 7
    ts_rank_length = int(ts_rank_length) if ts_rank_length and ts_rank_length > 0 else 60
    min_length = max(adv_length, delta_length + ts_rank_length)
    close = verify_series(close, min_length)
    volume = verify_series(volume, min_length)
    offset = get_offset(offset)

    if close is None or volume is None:
        return

    if not close.index.equals(volume.index):
        raise ValueError(
            "a101_007: `close` and `volume` are indexed differently. A "
            "volume-gated rank read off misaligned series is a silent "
            "nonsense number."
        )

    # Calculate Result
    adv = volume.rolling(adv_length).mean()
    d7 = close.diff(delta_length)
    tsrank = Series(_ts_rank(d7.abs().to_numpy(dtype=float), ts_rank_length), index=close.index)
    sign_d7 = Series(np.sign(d7.to_numpy(dtype=float)), index=close.index)
    gated = -tsrank * sign_d7

    result = Series(np.where(volume > adv, gated, -1.0), index=close.index)
    mask = adv.notna() & tsrank.notna()
    result = result.where(mask)

    # Offset
    if offset != 0:
        result = result.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        result.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        result.fillna(method=kwargs["fill_method"], inplace=True)

    # Name & Category
    result.name = f"A101_007_{adv_length}_{delta_length}_{ts_rank_length}"
    result.category = "momentum"

    return result


a101_007.__doc__ = \
"""Volume-Gated 7-Day Move Rank (A101_007)

Kakushadze's (2016, Wilmott, "101 Formulaic Alphas") Alpha101 `#7`, per issue
#51. When today's volume exceeds its 20-bar average, the column is the
negated time-series rank of the 7-bar absolute price move, signed by the
direction of that move; otherwise the column is a flat `-1`. Full Gate A
derivation, causality and scale-free arguments are in the module source
above; see docs/A101007Measured.md for the measured numbers.

Calculation:
    Default Inputs:
        adv_length=20, delta_length=7, ts_rank_length=60
    adv      = MEAN(volume, adv_length)
    d7       = DELTA(close, delta_length)          # close - close[7]
    tsrank   = TS_RANK(|d7|, ts_rank_length)        # count(|d7|[t-59..t] <= |d7|[t]) / 60
    gated    = -tsrank * SIGN(d7)
    A101_007 = (volume > adv) ? gated : -1.0

Args:
    close (pd.Series): Series of 'close's
    volume (pd.Series): Series of 'volume's
    adv_length (int): Rolling window for the volume average. Default: 20
    delta_length (int): Lookback for the price delta. Default: 7
    ts_rank_length (int): Rolling window for the time-series rank. Default: 60
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.Series: A101_007_{adv_length}_{delta_length}_{ts_rank_length}, a
        scale-free (dimensionless) column on [-1, 1]: either a flat -1.0
        (volume at or below its adv_length-bar average) or a signed
        percentile rank magnitude in [-1, -1/ts_rank_length] union
        {0} union [1/ts_rank_length, 1] (volume above its average). NaN for
        the first max(adv_length, delta_length + ts_rank_length) - 1 bars.
"""
