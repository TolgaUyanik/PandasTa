# -*- coding: utf-8 -*-
import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from pandas import Series

from pandas_ta.utils import get_offset, verify_series

# Two bins are the fewest that can tell a concentrated window from a spread
# one: with one bin every sample lands in it and the value is 0 everywhere.
MIN_BINS = 2
# A window of two returns puts its minimum in the first bin and its maximum in
# the last, one sample each, so the value is the constant log 2 there; three
# returns is the smallest window whose value can vary.
MIN_LENGTH = 3
EXTRA_CLOSES = 1  # `length` returns need `length + 1` closes
# A window whose returns vary only at rounding level has no range to bin: the
# bin edges would be laid out across float64 noise and the entropy would be
# the entropy of that noise. The floor can be an absolute constant -- no
# rolling scale, so no second window to keep causal -- because what is floored
# is the range of DIMENSIONLESS price ratios. The same 4096 eps is this fork's
# existing habit on a dimensionless quantity: `statistics/ts_c3_20.py` and
# `statistics/lean_hurst_100.py` both use it.
NOISE_ULPS = 4096
NOISE_FLOOR = NOISE_ULPS * np.finfo(float).eps  # 9.09e-13


def ts_binent_20(close, length=None, bins=None, offset=None, **kwargs):
    """Indicator: binned entropy of returns (TS_BINENT)"""
    # Validate Arguments
    length = int(length) if length and int(length) >= MIN_LENGTH else 20
    bins = int(bins) if bins and int(bins) >= MIN_BINS else 5
    # One bin per sample is the saturation point and the loop below runs once
    # per bin, so an unclamped `bins` is unbounded work for no new shape. The
    # effective value is the one in the column name.
    bins = min(bins, length)
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
    # float error the ratio can still raise -- 1e-300 followed by 1e50 gives
    # an infinite return. Such a pair is bad data in the same way a NaN close
    # is (there is no return to take), so it is silenced here and emptied on
    # the next line rather than binned: an infinite end would make `width`
    # infinite, every finite sample would land in the first bin and the window
    # would report a plausible-looking value below the two-bin floor.
    with np.errstate(over="ignore"):
        r[1:] = c[1:] / c[:-1] - 1.0
    r = np.where(np.isfinite(r), r, np.nan)

    # (n - length + 1, length) causal windows of returns, oldest first. The
    # window ending at bar T holds r[T-length+1 .. T], so it reads closes
    # T - length .. T and the first full window sits at bar `length - 1` --
    # whose oldest return is r[0], which is NaN, so the first value is at bar
    # `length`.
    windows = sliding_window_view(r, length)
    low = windows.min(axis=1)
    high = windows.max(axis=1)
    # Emptying the range first means no zero and no rounding-level value ever
    # reaches the division, so there is nothing for an `errstate` to suppress
    # and no infinity to clean up afterwards. A window holding a NaN return
    # has NaN for both ends and lands here too.
    width = np.where(high - low > NOISE_FLOOR, high - low, np.nan)

    # `bins` equal-width bins spanning the window's own [min, max]. The
    # minimum sits at 0.0 and the maximum at exactly `bins`, which the clip
    # folds into the last bin -- the standard half-open layout with the top
    # edge inclusive.
    index = np.clip(np.floor((windows - low[:, None]) / width[:, None] * bins),
                    0, bins - 1)
    # Shannon entropy in nats of the bin shares. An empty bin contributes
    # exactly 0 (`p * log(1)`), which is why the inner `where` exists.
    h = np.zeros(windows.shape[0])
    for b in range(bins):
        p = (index == b).mean(axis=1)
        h -= np.where(p > 0, p * np.log(np.where(p > 0, p, 1.0)), 0.0)

    out = np.full(c.size, np.nan)
    out[length - 1:] = np.where(np.isnan(width), np.nan, h)
    binent = Series(out, index=close.index)

    # Offset
    if offset != 0:
        binent = binent.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        binent.fillna(kwargs["fillna"], inplace=True)

    # Name and Categorize it
    binent.name = f"TS_BINENT_{length}_{bins}"
    binent.category = "statistics"

    return binent


ts_binent_20.__doc__ = \
"""Binned entropy of returns (TS_BINENT)

How evenly the recent returns fill their own range: lay `bins` equal-width
bins across the window's [min, max], count how many of the `length` returns
fall in each, and take the Shannon entropy of those shares in nats.

    TS_BINENT = -sum over bins of p * log(p),   p = count / length

The bins are anchored on the window's OWN minimum and maximum, which is what
makes the column scale-free and also what it reads: a window whose returns
are spread evenly across their range scores near `log(bins)`, and a window
with one large move and nineteen small ones scores near the floor, because
the one move stretches the range and the other nineteen collapse into the
first bin. It is a concentration / outlier-dominance reading, not a
volatility reading.

At the defaults the value lives in a narrow, DISCRETE set: 1.609438 at the
top (four returns in each of the five bins -- in float64 exactly
1.6094379124341005, which is ONE ULP ABOVE `math.log(5)`, because the five
terms are accumulated one bin at a time) and 0.198515 at the bottom
(nineteen in one bin, one in another, which is the least a non-degenerate
20-return window can score). The entropy FUNCTION takes **182** distinct
values over the 7,315 count vectors a 20-return window can produce -- that
count is of values ROUNDED to 1e-12, and in float64 the module emits more
than 182, because the terms are accumulated in bin order and two count
vectors that are permutations of each other land on different last bits
(measured: 154 distinct values on a 1,500-bar walk, 136 on a tick-rounded
walk and 193 on a student-t path, collapsing to 104 / 85 / 137 at 1e-12).
Either way the column ties heavily -- 1,480 bars over 136-193 distinct
float64 values (104-137 of them distinct at 1e-12) -- so a rank statistic
over it carries many tied ranks by construction
(docs/TsBinent20Measured.md).

⚠ It is INVARIANT to the amplitude of the returns, not just to the price
level. Every bin edge is a fraction of the window's own range, so
`r -> a*r + b` for `a > 0` leaves every count unchanged: the column is
bit-identical under a x0.5 and a x3 rescale of the returns themselves
(1,480 of 1,480 bars each) and under +0.004 of log drift a bar (1,480 of
1,480). Do NOT read it as a volatility or a trend feature; the same shape at
any amplitude reads the same number.

What it orders, measured as medians of 1,500-bar paths whose returns differ
in SHAPE: uniform 1.5260, gaussian 1.4737, laplace 1.3748, student-t(2)
1.2348, two-point (+-sigma) 0.6881. One planted outlier is enough to move
it: a single +50-sigma return reads exactly the 19/1 floor 0.198515 on all
20 windows that hold it, and a +10-sigma one takes those windows to a median
of 0.8557 against the frame's 1.4989.

Source: tsfresh feature_calculators (MIT), `binned_entropy`, as the formula
is stated by PandasTa issue #89: `binned_entropy(max_bins=5) on 20 returns`,
in the form of the screen prototype `docs/issues/screen/ind_screen.py`
candidate `ts_binent_20` (local to the owner's machine),
`roll(ret(c), 20, w_binned_entropy)`.
⚠ tsfresh is NOT installed in this worktree and web access is unavailable,
so the formula under test is the issue's line and the prototype, not a read
of tsfresh's own code; anything tsfresh does that the line does not say (how
it treats a series shorter than `max_bins`, whether it drops NaNs rather
than returning NaN) is unverified here. The 20 and the 5 bins are the
issue's own parameters. What IS independently checked is the DEFINITION of
equal-width binning: numpy's own `np.histogram` spelled window by window is
bit-equal to this module on 1,480 of 1,480 bars of a walk and of a
tick-rounded walk (docs/TsBinent20Measured.md, Gate A3).

Five readings the wording leaves open, decided and priced in
docs/TsBinent20Measured.md rather than assumed (the first four priced on the
same 1,500-bar walk, port against variant -- receipt §Gate A, A5; the fifth,
the degenerate window, on a flat 300-close frame -- §Gate A, A6):
* The bins are EQUAL-WIDTH, the prototype's and `np.histogram`'s. The
  equal-frequency (quantile) reading is not a different column, it is a
  CONSTANT one: 5 bins of 4 samples give `p = 1/5` every bar, so it reads
  exactly `log(5)` on 1,480 of 1,480 bars and carries no information.
* `bins=5`, the issue's. 3 bins is Spearman 0.651029 against it and 10 bins
  0.724187: the bin count is a real choice, not a formatting detail.
* The entropy is in NATS and unnormalised, the standard `binned_entropy`
  form. Dividing by `log(bins)` is a strict rescaling (`port / log(5)`
  reproduces it exactly, Spearman 1.000000), so it changes nothing a rank
  miner sees.
* The returns are simple (`close/close.shift(1) - 1`), the prototype's
  `ret`. Log returns are a different column: max |difference| 0.2502,
  Spearman 0.944970 -- a monotone but NON-affine transform of the returns
  moves samples across bin edges, which is why this one matters more here
  than for a moment-based column.
* A window with no range to bin is NaN, not 0. A literal `np.histogram`
  reading returns exactly 0 there, because numpy widens a zero-width range
  to `[v - 0.5, v + 0.5]` and puts every sample in one bin; measured, that
  reading fires on 280 of 300 bars of a flat frame where this column fires
  on none, all 280 of them exactly 0.0. NaN is the prototype's reading and
  the one issue #89's Gate E numbers were screened with.

The guard is `max - min > 9.09e-13` rather than `!= 0`, and here that
matters MORE than it did for `ts_c3_20`: the returns of an exactly geometric
path are mathematically constant but vary at rounding level in float64, and
an unguarded reading then bins that rounding noise into a value that looks
ORDINARY. Measured: a 1%-a-bar ladder fires 0 of 300 bars guarded and 280
unguarded, the unguarded values spanning [0.6474, 1.5114] -- inside the live
range of a real walk ([0.9262, 1.6094] on a 1,500-bar frame), so nothing
downstream could have spotted them. On a walk and on a tick-rounded walk the
floor changes neither a NaN flag nor a value (280 of 300 bars fire on each).

Causal: bar T reads closes T - length .. T, measured by a
future-perturbation sweep -- 0 of 37 offsets in each of the six
configurations run (three frames at the defaults, plus `(20, 10)`, `(60, 5)`
and `(5, 5)` on the walk).
Scale-free: every input is a price ratio, and `8a / 8b` is the same double as
`a / b`, so the column is bit-identical under a x8/x64 rescale (1,480 of
1,480 fired bars on each of a walk, a tick-rounded walk and a student-t
path; also at `bins=10` (1,480 of 1,480), `length=60` (1,440) and `length=5`
(1,495)). On these frames x10 and x3.7 are bit-identical too, which the
arithmetic does NOT guarantee: the value is a function of discrete bin
counts, so a last-bit change in a return moves it only when a sample crosses
a bin edge, and on these frames none did.
NaN on the first `length` bars; on any window holding a close that is NaN,
infinite, zero, negative or subnormal (a bad close empties the 21 windows it
sits in, because it spoils two returns); on any window holding a close pair
whose ratio OVERFLOWS (one spoiled return, so 20 windows); and on any window
whose `length` returns differ from each other by 9.09e-13 or less. That last one has three reachable
causes: `length + 1` identical closes (measured: a flat run planted in a walk
empties 0 bars at 20 identical closes and 1 at 21); an exactly geometric
path, whose closes are all DISTINCT (a 1%-a-bar ladder fires 0 of 300); and a
near-monotone fine-tick path at a high price, whose closes are distinct and
not geometric (measured: price 1e6 with a 0.001 tick, one tick a bar, has a
return range of 2.2e-16 and fires 0 of 300).

Cost: the module materialises one `(n - length + 1, length)` array of bin
indices and holds two same-shape float64 temporaries while computing it, so
memory is O(n * length), not O(n). At n = 400,000: 244 ms and a traced peak
of **144.1 MB** (measured with tracemalloc), of which 64.0 MB is the index
array itself (arithmetic from its shape).

Calculation:
    Default Inputs:
        length=20, bins=5
    r[t]    = close[t] / close[t-1] - 1
    lo, hi  = min, max of r over the trailing `length` returns
    width   = hi - lo (NaN where width <= 9.09e-13)
    k[i]    = min(floor((r[i] - lo) / width * bins), bins - 1)
    p[b]    = count of k == b, over `length`
    TS_BINENT = -sum(p * log(p)) over the occupied bins

Args:
    close (pd.Series): Series of 'close's
    length (int): Returns per window. At least 3 -- a 2-return window is the
        constant `log 2` (measured) -- a smaller or missing value falls back
        to the default. Default: 20
    bins (int): Equal-width bins across the window's range. At least 2, and
        clamped to `length`: a histogram with more bins than samples resolves
        nothing the sample supports, and it reads mostly the number of exact
        ties (measured on a 400-bar walk at length 20: 45 distinct values
        over 380 fired bars at `bins=20` against 91 at `bins=5`, and an
        unclamped `bins=100` is Spearman 0.263965 against the clamp). The
        effective value is the one in the column name. Default: 5
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)

Returns:
    pd.Series: TS_BINENT_{length}_{bins}, in nats, from the two-bin floor up
        to the even split -- 1.6094379124341005 at the defaults, one ulp
        above `math.log(5)`
"""
