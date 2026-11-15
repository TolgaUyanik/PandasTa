# -*- coding: utf-8 -*-
"""Decayed low-volume correlation rank + VWAP momentum rank -- Guotai
Junan's (2017, "GTJA191", internal quant report, read via the
HKUDS/Vibe-Trading copy, MIT) alpha `#44`, per issue #60. Source cited by
the issue:

    #44: TSRANK(DECAYLINEAR(CORR(LOW,MEAN(V,10),7),6),4)
         + TSRANK(DECAYLINEAR(DELTA(VWAP,3),10),15)

**What this session could NOT do, disclosed up front:** `docs/pine/` and
web access are both unavailable in this worktree, so the issue's own named
copy -- HKUDS/Vibe-Trading (MIT) -- was never read. The formula below is
derived from the issue's own stated text (itself a quote of the GTJA191
report), per the issue's own instruction ("Gate A starts from the source
formula, not the prototype").

GATE A -- DERIVATION. The formula sums two independently-computed TSRANK
terms. The first reads a 7-bar rolling Pearson correlation between `LOW`
and a 10-bar volume average, smooths that correlation series with a
6-bar linearly-decaying weighted average, then takes its 4-bar
time-series rank -- "how unusually high has the (smoothed) low/low-volume
correlation been, lately". The second reads the 3-bar change in `VWAP`,
smooths it with a 10-bar linearly-decaying weighted average, then takes
its 15-bar time-series rank -- "how unusually strong has the (smoothed)
VWAP momentum been, lately". `VWAP` has no traded-value field in daily
OHLCV; the issue's own parenthetical states the scale-free conversion
("VWAP -> (H+L+C)/3"), matching the issue's own prototype
(`docs/issues/screen/ind_screen.py:362-366`), candidate `g191_044`:

    @cand("g191_044", "decayed low-volume correlation rank + VWAP momentum
          rank", G, "#44: TSRANK(DECAYLINEAR(CORR(LOW,MEAN(V,10),7),6),4) +
          TSRANK(DECAYLINEAR(DELTA(VWAP,3),10),15)", "VWAP -> (H+L+C)/3")
    def _(o, h, l, c, v):
        return (tsrank(decaylinear(corr(l, mean(v, 10), 7), 6), 4)
                + tsrank(decaylinear(delta(tp(h, l, c), 3), 10), 15))

No disclosed interpretation choice was needed for the formula itself -- the
issue's own string and the prototype agree exactly, including every
window length.

OPERATORS, each read directly off the prototype's own (unambiguous) module
source, the same source every other `g191_*` port in this fork relies on:

* `MEAN(X, n)` = `X.rolling(n).mean()` (`ind_screen.py:47`).
* `CORR(X, Y, n)` = a trailing `n`-bar rolling Pearson correlation,
  `X.rolling(n).corr(Y)`, `inf -> NaN` (`ind_screen.py:53`,
  `corr(x, y, n): return _fin(x.rolling(n).corr(y))`).
* `DELTA(X, n)` = `X - X.shift(n)` (`ind_screen.py:46`), a BACKWARD
  difference (bar `t` reads bar `t-n`), never a look-ahead.
* `DECAYLINEAR(X, d)` = a trailing `d`-bar weighted average with weights
  `1, 2, ..., d` (oldest bar in the window weighted `1`, the CURRENT bar
  weighted `d`), normalised to sum to 1 (`ind_screen.py:79-81`:
  `w = np.arange(1, d+1); return win_dot(x, w / w.sum())`, where `win_dot`
  dots each trailing `d`-bar window, oldest-first, against `w`).
* `TSRANK(X, n)` = the percentile rank of the CURRENT bar's value of `X`
  within its own trailing `n`-bar window (`ind_screen.py:52`,
  `tsrank(x, n): return x.rolling(n).rank(pct=True)` -- pandas' own
  rolling percentile rank, average-rank tie-break, requiring a full
  `n`-bar window of non-NaN values or the result is `NaN`).
* `H`, `L`, `C`, `V` = high, low, close, volume. `VWAP` has no traded-value
  field in daily OHLCV, so this port uses the typical price `(H+L+C)/3`,
  matching the prototype's own `tp(h, l, c): return (h + l + c) / 3`
  (`ind_screen.py:109`).

CALCULATION, in the order computed below (`mean_v_length=10,
corr_length=7, decay1_length=6, tsrank1_length=4, delta_length=3,
decay2_length=10, tsrank2_length=15`):
    tp       = (H + L + C) / 3
    mean_v   = MEAN(V, mean_v_length)
    corr1    = CORR(L, mean_v, corr_length)
    decay1   = DECAYLINEAR(corr1, decay1_length)
    term1    = TSRANK(decay1, tsrank1_length)
    delta_tp = DELTA(tp, delta_length)
    decay2   = DECAYLINEAR(delta_tp, decay2_length)
    term2    = TSRANK(decay2, tsrank2_length)
    G191_044 = term1 + term2

CAUSALITY. `mean_v[t]` is a trailing `mean_v_length`-bar mean, reading only
`V[t-mean_v_length+1..t]`. `corr1[t]` is a trailing `corr_length`-bar
Pearson correlation of `L` against `mean_v`, each already backward-looking,
reading no bar newer than `t`. `decay1[t]` dots the trailing
`decay1_length`-bar window of `corr1` ending at `t` against fixed weights
-- every window index `<= t`. `term1[t] = TSRANK(decay1, tsrank1_length)`
reads only `decay1[t-tsrank1_length+1..t]`. The second branch is identical
in shape: `delta_tp[t] = tp[t] - tp[t-delta_length]` reads only `t` and
`t-delta_length`; `decay2[t]` and `term2[t]` chain the same two backward
operators. The final sum combines only `term1[t]` and `term2[t]` -- nothing
in either branch reads a bar newer than `t`. `tests/test_g191_044.py`
proves this both by future-perturbation (real module: 0 of 34 offsets
leak) and by two independent mutants (`importlib` source read, `exec`'d
in memory), each shown live (differs from the real module): shifting the
final write index `tsrank2_length` bars forward is caught at EVERY
offset (34 of 34); replacing the backward `DELTA`
(`tp.shift(delta_length)`) with a FORWARD shift (`tp.shift(-delta_length)`)
is caught at 30 of 34 -- the remaining 4 are a MEASURED, understood
property of `TSRANK`, not a causality gap: at those 4 offsets `term2`
itself (isolated from the mutant's full output) sits at the rank ceiling
`1.0` in BOTH the unperturbed and the perturbed run, at every one of the
12 affected bars (`python docs/measure_g191_044.py`) -- `TSRANK` is a
`[0, 1]`-bounded order statistic, so replacing an already-maximal value
with an even larger future-leaked outlier still ranks `1.0`, making the
corruption provably invisible to a rank-only comparison at exactly those
bars.

WARM-UP. `mean_v` is valid from `mean_v_length` bars of history.
`corr1` needs `corr_length` CONSECUTIVE bars where `mean_v` is already
valid, so it is valid from `mean_v_length + corr_length - 1` bars.
`decay1` needs `decay1_length` consecutive valid `corr1` bars (the
`win_dot` dot-product propagates a `NaN` the moment any bar in its window
is `NaN`, via ordinary float arithmetic -- no explicit mask needed), valid
from `mean_v_length + corr_length + decay1_length - 2` bars. `term1` needs
`tsrank1_length` consecutive valid `decay1` bars (pandas' `.rolling().rank()`
defaults `min_periods` to the full window, so a window touching even one
`NaN` is itself `NaN`), valid from `mean_v_length + corr_length +
decay1_length + tsrank1_length - 3` bars -- **24** at the shipped
defaults. `delta_tp` is valid from `delta_length + 1` bars. `decay2` is
valid from `delta_length + decay2_length` bars. `term2` is valid from
`delta_length + decay2_length + tsrank2_length - 1` bars -- **27** at the
shipped defaults. The two branches are PARALLEL, not chained, so the true
warm-up is the max of the two: `min_length = max(mean_v_length +
corr_length + decay1_length + tsrank1_length - 3, delta_length +
decay2_length + tsrank2_length - 1)` -- **27** at the shipped defaults,
enforced by `verify_series`.

SCALE-FREE. Let `k > 0` rescale price (`high, low, close -> k*(...)`, or
`volume -> k*volume`, independently). Pearson correlation is exactly
invariant to a positive rescale of EITHER input (the `k` cancels between
the covariance and the standard-deviation terms), so `corr1` is unchanged
by a price rescale of `L` alone or a volume rescale of `V` alone (`mean_v`
is linear/positively homogeneous in `V`, so rescaling `V` by `k` rescales
`mean_v` by the same `k`, and correlation is invariant to that too).
`decay1` is a fixed-weight linear combination of `corr1`, which is itself
a bounded `[-1, 1]` quantity untouched by either rescale -- `decay1` is
therefore untouched too, EXACTLY (not merely algebraically, after some
cancellation -- the input to the weighted sum never changes). `term1 =
TSRANK(decay1, ...)` is an order statistic (a rolling percentile rank),
invariant to ANY strictly-increasing transform of its input, and `decay1`
being completely untouched is a (trivial) strictly-increasing transform of
itself -- so `term1` is unchanged under either rescale. For the second
branch: `delta_tp = tp - tp.shift(delta_length)` scales by the SAME `k` as
a price rescale (a plain difference is linear/positively homogeneous in
price; `V` never enters this branch, so a volume rescale leaves it fully
untouched), `decay2` (a fixed-weight linear combination) scales by the
same `k` too, and `term2 = TSRANK(decay2, ...)` is again an order
statistic -- invariant to ANY positive rescale of its input, since
multiplying by `k > 0` is a strictly-increasing transform that preserves
every pairwise ordering inside the rolling window. So `term2` is
UNCHANGED under a price rescale (not merely scaled by `k`), and fully
untouched by a volume rescale. The whole column, `term1 + term2`, is
therefore scale-free BY CONSTRUCTION for a positive rescale of price and
volume INDEPENDENTLY -- built entirely from a bounded correlation and two
rank order statistics, never from a raw price or volume level. Measured
on a synthetic frame: PRICE x8/x64 and VOLUME x8/x64 all land
bit-identical (power-of-two multiplication is exact in IEEE754, and
`TSRANK`'s rank ordering is untouched by it regardless), while x10/x3.7 on
either axis come out within float64 rounding tolerance (the correlation
and weighted-sum arithmetic itself rounds; the rank ordering does not
change at all, so the residual tolerance gap is from `corr1`/`decay2`'s
own floating-point rounding, not from any rank instability). Measured in
the test file and `docs/measure_g191_044.py`, not merely asserted.
"""
import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from pandas import Series

from pandas_ta.utils import get_offset, verify_series


def _decaylinear(values: np.ndarray, d: int) -> np.ndarray:
    """Trailing `d`-bar weighted average with weights `1, 2, ..., d`
    (oldest bar in the window weighted `1`, the current bar weighted `d`),
    normalised to sum to 1. A `NaN` anywhere in a window propagates to
    that window's output through ordinary float arithmetic -- no explicit
    mask needed. Reads only the window ending at the current bar."""
    n = len(values)
    out = np.full(n, np.nan)
    if d > n:
        return out
    w = np.arange(1, d + 1, dtype=float)
    w = w / w.sum()
    windows = sliding_window_view(values, d)  # (n-d+1, d), oldest-first
    out[d - 1:] = windows @ w
    return out


def g191_044(high, low, close, volume, mean_v_length=None, corr_length=None,
             decay1_length=None, tsrank1_length=None, delta_length=None,
             decay2_length=None, tsrank2_length=None, offset=None, **kwargs):
    """Indicator: Decayed Low-Volume Correlation Rank + VWAP Momentum Rank (G191_044)"""
    # Validate Arguments
    mean_v_length = int(mean_v_length) if mean_v_length and mean_v_length > 1 else 10
    corr_length = int(corr_length) if corr_length and corr_length > 1 else 7
    decay1_length = int(decay1_length) if decay1_length and decay1_length > 1 else 6
    tsrank1_length = int(tsrank1_length) if tsrank1_length and tsrank1_length > 1 else 4
    delta_length = int(delta_length) if delta_length and delta_length > 0 else 3
    decay2_length = int(decay2_length) if decay2_length and decay2_length > 1 else 10
    tsrank2_length = int(tsrank2_length) if tsrank2_length and tsrank2_length > 1 else 15

    min_len_1 = mean_v_length + corr_length + decay1_length + tsrank1_length - 3
    min_len_2 = delta_length + decay2_length + tsrank2_length - 1
    min_length = max(min_len_1, min_len_2)
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
            "g191_044: high/low/close/volume are indexed differently. A "
            "cross-series correlation read off misaligned series is a "
            "silent nonsense number."
        )

    # Calculate Result
    tp = (high + low + close) / 3.0
    mean_v = volume.rolling(mean_v_length).mean()
    corr1 = low.rolling(corr_length, min_periods=corr_length).corr(mean_v)
    corr1 = corr1.replace([np.inf, -np.inf], np.nan)
    decay1 = Series(_decaylinear(corr1.to_numpy(dtype=float), decay1_length), index=close.index)
    term1 = decay1.rolling(tsrank1_length).rank(pct=True)

    delta_tp = tp - tp.shift(delta_length)
    decay2 = Series(_decaylinear(delta_tp.to_numpy(dtype=float), decay2_length), index=close.index)
    term2 = decay2.rolling(tsrank2_length).rank(pct=True)

    result = term1 + term2

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
        f"G191_044_{mean_v_length}_{corr_length}_{decay1_length}_"
        f"{tsrank1_length}_{delta_length}_{decay2_length}_{tsrank2_length}"
    )
    result.category = "statistics"

    return result


g191_044.__doc__ = \
"""Decayed Low-Volume Correlation Rank + VWAP Momentum Rank (G191_044)

Guotai Junan's (2017, "GTJA191") alpha `#44`, per issue #60. Sums two
time-series percentile ranks: how unusually high the (6-bar
decay-smoothed) 7-bar correlation between `low` and its own 10-bar volume
average has been over the last 4 bars, plus how unusually strong the
(10-bar decay-smoothed) 3-bar change in typical price has been over the
last 15 bars. Full Gate A derivation, causality and scale-free arguments
are in the module source above; see docs/G191044Measured.md for the
measured numbers.

Calculation:
    Default Inputs:
        mean_v_length=10, corr_length=7, decay1_length=6, tsrank1_length=4,
        delta_length=3, decay2_length=10, tsrank2_length=15
    tp       = (high + low + close) / 3           # VWAP proxy
    mean_v   = MEAN(volume, mean_v_length)
    corr1    = CORR(low, mean_v, corr_length)
    decay1   = DECAYLINEAR(corr1, decay1_length)   # weights 1..decay1_length
    term1    = TSRANK(decay1, tsrank1_length)
    delta_tp = DELTA(tp, delta_length)             # tp - tp.shift(delta_length)
    decay2   = DECAYLINEAR(delta_tp, decay2_length)
    term2    = TSRANK(decay2, tsrank2_length)
    G191_044 = term1 + term2

Args:
    high (pd.Series): Series of 'high's
    low (pd.Series): Series of 'low's
    close (pd.Series): Series of 'close's
    volume (pd.Series): Series of 'volume's
    mean_v_length (int): Rolling window for the volume average. Default: 10
    corr_length (int): Rolling window for the low/volume correlation. Default: 7
    decay1_length (int): Linear-decay window smoothing the correlation. Default: 6
    tsrank1_length (int): Time-series rank window for the correlation branch. Default: 4
    delta_length (int): Lookback for the typical-price change. Default: 3
    decay2_length (int): Linear-decay window smoothing the price change. Default: 10
    tsrank2_length (int): Time-series rank window for the momentum branch. Default: 15
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.Series: G191_044_{mean_v_length}_{corr_length}_{decay1_length}_
        {tsrank1_length}_{delta_length}_{decay2_length}_{tsrank2_length}, a
        scale-free (dimensionless) column: a sum of two rolling percentile
        ranks, each in `[0, 1]`, so the column lies in `[0, 2]`. NaN for the
        first `max(mean_v_length + corr_length + decay1_length +
        tsrank1_length - 3, delta_length + decay2_length + tsrank2_length -
        1) - 1` bars (27 - 1 = 26 at the shipped defaults).
"""
