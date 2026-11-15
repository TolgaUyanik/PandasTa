# -*- coding: utf-8 -*-
import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from pandas import Series

from pandas_ta.utils import get_offset, verify_series

# A window of one return is its own mean, so nothing is ever strictly above it
# and the column is 0 everywhere; a window of two returns puts exactly one of
# them above the mean (or neither, when they are equal), so it is the constant
# 1. Three returns is the smallest window whose value can vary.
MIN_LENGTH = 3
EXTRA_CLOSES = 1  # `length` returns need `length + 1` closes
# A window whose returns vary only at rounding level has no strike to read:
# which samples land above the mean is then decided by float64 noise, and the
# run length it produces is an ORDINARY-LOOKING integer rather than an obvious
# absurdity. Such a window is reported as 0 -- the value exactly constant
# returns give, since no sample can be strictly above their mean. The floor can
# be an absolute constant -- no rolling scale, so no second window to keep
# causal -- because what is floored is the range of DIMENSIONLESS price ratios.
# The same 4096 eps is this fork's existing habit on a dimensionless quantity:
# `statistics/ts_binent_20.py` floors the same window return range with it, and
# `statistics/ts_c3_20.py` and `statistics/lean_hurst_100.py` floor a return
# standard deviation and a log price ratio.
NOISE_ULPS = 4096
NOISE_FLOOR = NOISE_ULPS * np.finfo(float).eps  # 9.09e-13


def ts_strike_20(close, length=None, offset=None, **kwargs):
    """Indicator: longest strike of returns above their mean (TS_STRIKE)"""
    # Validate Arguments
    length = int(length) if length and int(length) >= MIN_LENGTH else 20
    close = verify_series(close, length + EXTRA_CLOSES)
    offset = get_offset(offset)

    if close is None: return

    # Calculate Result
    c = close.to_numpy(dtype=float)
    # A close that is not a finite, normal, positive float (NaN, inf, zero,
    # negative, or subnormal such as 1e-310) is bad data: it has no return to
    # take, so it is missing.
    c = np.where(np.isfinite(c) & (c >= np.finfo(float).tiny), c, np.nan)

    # The simple return, spelled as a price RATIO minus one: `8a / 8b` is the
    # same double as `a / b`, so a x2^k rescale cancels exactly rather than to
    # rounding.
    r = np.full(c.size, np.nan)
    # Both ends are finite, positive and normal by now, so OVERFLOW is the one
    # float error the ratio can still raise -- 1e-300 followed by 1e50 gives an
    # infinite return. Such a pair is bad data in the same way a NaN close is
    # (there is no return to take), so it is silenced here and emptied on the
    # next line rather than compared: an infinite return would be above any
    # finite mean and would plant a strike of its own.
    with np.errstate(over="ignore"):
        r[1:] = c[1:] / c[:-1] - 1.0
    r = np.where(np.isfinite(r), r, np.nan)

    # (n - length + 1, length) causal windows of returns, oldest first. The
    # window ending at bar T holds r[T-length+1 .. T], so it reads closes
    # T - length .. T and the first full window sits at bar `length - 1` --
    # whose oldest return is r[0], which is NaN, so the first value is at bar
    # `length`.
    windows = sliding_window_view(r, length)
    mean = windows.mean(axis=1)
    span = windows.max(axis=1) - windows.min(axis=1)

    # Strictly above, the comparison the issue's line and the screen prototype
    # both use: a sample sitting exactly ON the mean does not extend a strike.
    # A NaN return makes the whole window's mean
    # NaN, and every comparison against NaN is False, so such a window scores 0
    # here and is emptied below.
    above = windows > mean[:, None]
    # Longest run of consecutive True, read one column at a time so the whole
    # frame advances together: `current` is the run ending at this column and
    # `longest` the best seen so far.
    current = np.zeros(windows.shape[0])
    longest = np.zeros(windows.shape[0])
    for j in range(length):
        current = np.where(above[:, j], current + 1.0, 0.0)
        longest = np.maximum(longest, current)

    out = np.full(c.size, np.nan)
    out[length - 1:] = np.where(np.isnan(mean), np.nan,
                                np.where(span > NOISE_FLOOR, longest, 0.0))
    strike = Series(out, index=close.index)

    # Offset
    if offset != 0:
        strike = strike.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        strike.fillna(kwargs["fillna"], inplace=True)

    # Name and Categorize it
    strike.name = f"TS_STRIKE_{length}"
    strike.category = "statistics"

    return strike


ts_strike_20.__doc__ = \
"""Longest strike of returns above their mean (TS_STRIKE)

How long the recent returns kept beating their own average: take the
`length` trailing simple returns, mark the ones STRICTLY above that window's
mean, and report the length of the longest unbroken run of marks.

    TS_STRIKE = longest run of consecutive (r[i] > mean(r)) in the window

The output is a small INTEGER, not a continuous statistic. Its attainable
set is `{0} + {1 .. length - 1}`: every k from 1 to 19 is reachable at the
defaults (constructed, k consecutive +1 returns among zeros --
docs/TsStrike20Measured.md §Gate A, A4), `length` itself is NOT, because at
least one sample of a window is always at or below that window's own mean,
and 0 means the window's `length` returns are all EQUAL -- or equal to
rounding level, see the floor below -- since otherwise the maximum is
strictly above the mean. On real-shaped frames only a handful of
those values show up: 9 distinct values over 1,480 fired bars of a
1,500-bar walk (1 to 9, median 3, mean 3.6912) and 11 on an AR(1) path.
The column therefore TIES heavily by construction, and a rank statistic over
it carries many tied ranks.

⚠ It is INVARIANT to any affine map of the returns, not just to the price
level. Every sample is compared with the mean of its own window, so
`r -> a*r + b` for `a > 0` leaves every comparison unchanged: the column is
bit-identical under a x0.5 and a x3 rescale of the returns themselves and
under +0.004 of log drift a bar (1,480 of 1,480 bars each). Two
consequences worth stating plainly:
* it is NOT a volatility feature -- the same pattern at any amplitude reads
  the same integer;
* it is NOT a trend feature -- a pure geometric trend has CONSTANT returns,
  so it reads 0 (measured: 0.0 on all 280 fired bars of a 1%-a-bar ladder),
  while a path alternating up and down every bar reads a constant 1 (1,480
  of 1,480). What it reads is the CLUSTERING of above-average returns.
That clustering is the ordering it claims, measured on AR(1) log-return
paths at phi = +0.8 / +0.6 / +0.3 / 0 / -0.3 / -0.6 / -0.8: mean 6.5392 /
5.5128 / 4.3872 / 3.6520 / 3.1297 / 2.7081 / 2.3223 (medians 6 / 5 / 4 / 3 /
3 / 3 / 2 -- the means separate the cases the medians tie). One outlier
SHORTENS it rather than lengthening it, because the outlier drags the mean
above the ordinary returns: a single +50% return reads 1 or 2 on the 20
windows holding it where the same bars read 2 or 3 without it, against a
frame mean of 3.6912.

Source: tsfresh feature_calculators (MIT), `longest_strike_above_mean`, as
the formula is stated by PandasTa issue #90:
`longest_strike_above_mean on 20 returns`, in the form of the screen
prototype `docs/issues/screen/ind_screen.py` candidate `ts_strike_20`
(local to the owner's machine), `roll(ret(c), 20, w_longest_strike_above_mean)`.
⚠ tsfresh is NOT installed in this worktree and web access is unavailable,
so the formula under test is the issue's line and the prototype, not a read
of tsfresh's own code. NOTHING in this module's documentation describes
tsfresh's source text: how it spells the comparison, how it counts runs, what
it does with an empty series or with NaNs is UNVERIFIED here, and the
attribution is to the feature NAME the issue gives. The 20 is the issue's own
parameter. What IS independently checked is the RUN counting: an
`itertools.groupby` run-length spelling over `x > x.mean()` -- chosen because
it shares no array machinery with the module, not because tsfresh is known to
spell it that way -- applied window by window in a plain Python loop, is
bit-equal to this module on 1,480 of 1,480 bars of a walk, of a tick-rounded
walk and of an AR(1) path (§Gate A, A3).

Five readings the wording leaves open, decided and priced in
docs/TsStrike20Measured.md rather than assumed:
* The comparison is STRICT (`>`), which is what the issue's line and the
  prototype's `W > W.mean(1, keepdims=True)` give. The `>=` reading is NOT a
  cosmetic difference even though it is bit-equal on 1,480 of 1,480 bars of
  a walk -- it differs only on an exact tie with the mean, of which a walk
  and a tick-rounded walk have 0 in 29,600 samples -- because on a window of
  EQUAL returns it reads `length` (20, the top of the scale) where this
  column reads 0 (the bottom): the two readings disagree maximally on
  exactly the case that is reachable on real data.
* The returns are simple (`close/close.shift(1) - 1`), the prototype's
  `ret`. Log returns are a different column: bit-equal on 1,455 of 1,480
  bars, max |difference| 3 runs, Spearman 0.988879 -- a monotone but
  NON-affine transform changes the window MEAN, which is what the
  comparison is against.
* Above the mean, not below: the mirror the screen listed as a separate
  candidate (`skipped.py`, "ts_longest_strike_below_mean -- read: mirror of
  ts_strike_20") is a genuinely different column -- bit-equal on 346 of
  1,480 bars, Spearman 0.109170.
* The count is RAW, not divided by `length`: the issue's line names the
  feature and the prototype returns the run length itself, while the screen's
  neighbouring candidate `ts_above_mean_20` spells its own division out
  (`count_above_mean / n`). Normalising is a strict rescaling (`port / 20`
  reproduces it on 1,480 of 1,480 bars, Spearman 1.000000), so it changes
  nothing a rank miner sees.
* A window whose returns are constant to rounding level reads 0 rather than
  a run read off float64 noise. See the floor below.

The floor is `max(r) - min(r) > 9.09e-13` and it matters because the
unguarded failure here is INVISIBLE rather than absurd: the returns of an
exactly geometric path are mathematically constant, so the answer is 0, but
in float64 they differ in their last bits and an unguarded reading then
reports a run length of that noise -- measured, a 1%-a-bar ladder reads 1,
2, 3 or 4 on all 280 of its fired bars (counts 85 / 64 / 80 / 51 on this
machine; being rounding noise they move with numpy's kernels, 87 / 75 / 73 /
45 under `NPY_DISABLE_CPU_FEATURES="AVX512F AVX512_SKX AVX2 FMA3"`) and an
exact x1.5 ladder reads 1, 2, 3, 5 or 8, every one of those values inside the
live range of a real walk (1 to 9). On a walk and on a tick-rounded walk the
floor changes neither a value nor a NaN flag (280 of 300 bars fire on each,
bit-equal to the unguarded form). What it COSTS is stated rather than
hidden: on a monotone one-tick-per-bar path the returns genuinely decrease
(the tick is a shrinking fraction of a rising price), so the mathematical
answer is not 0 -- at price 50 with a 0.01 tick the window's return span is
6.8e-07, above the floor, and the column reads 10; at price 1e6 with a 0.001
tick the span is 2.2e-16 and it reads 0, where the unguarded form spreads
over every value from 0 to 19; at price 1e6 with a 0.01 tick the span is
2.0e-15 and it reads 0, where the unguarded form reads 8 to 11. The floor is
an absolute constant -- no rolling scale, so no second window to keep causal
-- because what it bounds is the range of DIMENSIONLESS price ratios.

Causal: bar T reads closes T - length .. T, measured by a
future-perturbation sweep -- 0 of 37 offsets in each of the six
configurations run (a walk, a tick-rounded walk and an AR(1) path at the
default, `length=5` and `length=60` on the walk, and a walk carrying 21
identical closes at each offset, where the guard fires). Five mutants are
caught on 33 to 37 of those 37 offsets; a cell under 37 is the discreteness
of an integer column rather than an excuse, and §Gate B measures the
mechanism (a one-bar look-ahead can move exactly ONE bar of the prefix,
J - 1, so a miss is an offset where that one integer did not change). A sixth
mutant covers `span`, the windowed quantity the guard reads, on the
flat-planted frame -- 37 of 37.
Scale-free: every input is a price ratio, and `8a / 8b` is the same double as
`a / b`, so the column is bit-identical under a x8/x64 rescale (1,480 of
1,480 fired bars on each of three frames; 1,495 of 1,495 at `length=5` and
1,440 of 1,440 at `length=60`). x10 and x3.7 come out bit-identical too,
which the arithmetic does not promise on its own -- the output is an integer
decided by a float comparison, so a last-bit change in the mean can in
principle flip a near-tie. What makes it hold here is measured: the smallest
margin any sample has to its own window's mean is 1.2e-06 on the walk and
5.2e-08 on the AR(1) path (2.5e-05 and 1.3e-06 of the window's return span),
with 0 exact ties in 29,600 samples -- several orders of magnitude from a
rounding decision.
NaN on the first `length` bars; on any window holding a close that is NaN,
infinite, zero, negative or subnormal (a bad close empties the 21 windows it
sits in, because it spoils two returns); and on any window holding a close
pair whose ratio OVERFLOWS (one spoiled return, so 20 windows). A window
that is merely degenerate is NOT NaN: `length + 1` identical closes read 0
(measured: a flat run planted in a walk makes 0 bars read 0 at 20 identical
closes, 1 at 21 and 5 at 25).

Cost: the module materialises one `(n - length + 1, length)` BOOLEAN array
and reduces over views of the returns, so memory is O(n * length) but a
byte a cell rather than a double. At n = 400,000 the traced peak is 37.2 MB
(tracemalloc, reproduced on every run made), of which 8.0 MB is the boolean
array itself (arithmetic from its shape). Wall clock is a tenth of a second
in that size, and is NOT quoted as a band because it does not reproduce:
measured runs on one machine span 116-165 ms.

Calculation:
    Default Inputs:
        length=20
    r[t]      = close[t] / close[t-1] - 1
    mu        = mean of r over the trailing `length` returns
    span      = max(r) - min(r) over the same window
    TS_STRIKE = longest run of consecutive (r[i] > mu), or 0 when
                span <= 9.09e-13

Args:
    close (pd.Series): Series of 'close's
    length (int): Returns per window. At least 3 -- a 1-return window is its
        own mean and a 2-return window puts exactly one sample above it, so
        both are constant (measured on a 400-bar walk: 0 on all 399 fired
        bars at `length=1`, 1 on all 398 at `length=2`, and {1, 2} at
        `length=3`) -- and a smaller or missing value falls back to the
        default. Default: 20
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)

Returns:
    pd.Series: TS_STRIKE_{length}, an integer-valued count of bars in
        `{0} + {1 .. length - 1}`
"""
