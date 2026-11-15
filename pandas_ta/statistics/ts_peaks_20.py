# -*- coding: utf-8 -*-
import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from pandas import Series

from pandas_ta.utils import get_offset, verify_series

# The support: how many closes on EACH side of a candidate must be strictly
# below it. The issue fixes it -- `number_peaks(x, n=2) on 20 closes; a peak
# counts once confirmed 2 bars later` -- so it is not a parameter here, and it
# is in the column name so a later support cannot quietly reuse it.
#
# `n = 2` means BOTH distances 1 and 2 on BOTH sides, which is the source's
# loop `for i in range(1, n + 1)` and not just "the close two bars later": a
# peak at bar P needs P above P-1, P-2, P+1 AND P+2. The screen prototype
# spells the same four comparisons (`docs/issues/screen/ind_screen.py`,
# candidate `ts_peaks_20`), and this module is bit-equal to it on every clean
# frame measured (docs/TsPeaks20Measured.md, Gate A2).
SUPPORT = 2
# The comparison is STRICT (`>`), so a plateau is not a peak and a window of
# identical closes counts 0. That is the source's `>`; `>=` is a different
# column and is priced in docs/TsPeaks20Measured.md, Gate A5.
#
# `length` closes hold `length - 2 * SUPPORT` candidates, so the smallest
# window with a candidate at all is `2 * SUPPORT + 1` = 5 closes, where the
# column takes only 0 and 1 (measured).
MIN_LENGTH = 2 * SUPPORT + 1


def ts_peaks_20(close, length=None, offset=None, **kwargs):
    """Indicator: confirmed local peaks of close (TS_PEAKS)"""
    # Validate Arguments
    length = int(length) if length and int(length) >= MIN_LENGTH else 20
    close = verify_series(close, length)
    offset = get_offset(offset)

    if close is None: return

    # Calculate Result
    c = close.to_numpy(dtype=float)
    n = c.size

    # The candidate bars: every close that has SUPPORT closes on each side
    # inside the series. `core[j]` is close `j + SUPPORT`.
    core = c[SUPPORT:n - SUPPORT]
    # A close that is not finite cannot be ordered against its neighbours:
    # every comparison against a NaN is False, which would silently read as
    # "not a peak" and UNDERCOUNT rather than refuse. It is masked out below.
    ok = np.isfinite(c)
    peak = np.ones(core.size, dtype=bool)
    valid = ok[SUPPORT:n - SUPPORT].copy()
    for i in range(1, SUPPORT + 1):
        left, right = c[SUPPORT - i:n - SUPPORT - i], c[SUPPORT + i:n - SUPPORT + i]
        peak &= (core > left) & (core > right)
        valid &= ok[SUPPORT - i:n - SUPPORT - i] & ok[SUPPORT + i:n - SUPPORT + i]
    # Only comparisons are read: no difference, no ratio, no sum. That is
    # what makes the column invariant to any strictly increasing transform of
    # price and not merely to a multiplication.
    flags = np.where(valid, peak.astype(np.int8), np.int8(-1))

    # The window ending at bar T is closes T - length + 1 .. T, and a
    # candidate needs SUPPORT closes of its own on each side inside it, so the
    # window holds `length - 2 * SUPPORT` candidates: bars T - length + 1 +
    # SUPPORT .. T - SUPPORT. The newest one is T - SUPPORT, which is the
    # issue's "confirmed 2 bars later", and the first full window sits at bar
    # `length - 1`.
    candidates = length - 2 * SUPPORT
    windows = sliding_window_view(flags, candidates)
    counts = windows.sum(axis=1, dtype=np.int64)
    # One masked candidate empties its whole window: a count over fewer than
    # `candidates` candidates is a different statistic, not a smaller sample
    # of this one. `min(axis=1) < 0` rather than `(windows < 0).any(axis=1)`:
    # the two are equivalent (`min < 0` iff some element is < 0), but the
    # `any` form materialises a `(rows, candidates)` bool array first --
    # traced at a 6.8 MB peak at `length` 20 and 98.7 MB at `length` 250,
    # against 0.8 MB for this form on the same windows -- while `min` is a
    # strided reduction straight to `(rows,)`. `tests/test_ts_peaks_20.py`
    # pins this spelling, because the two are behaviourally identical and
    # only the memory differs (docs/TsPeaks20Measured.md, Cost).
    bad = windows.min(axis=1) < 0

    out = np.full(n, np.nan)
    out[length - 1:] = np.where(bad, np.nan, counts)
    peaks = Series(out, index=close.index)

    # Offset
    if offset != 0:
        peaks = peaks.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        peaks.fillna(kwargs["fillna"], inplace=True)

    # Name and Categorize it
    peaks.name = f"TS_PEAKS_{length}_{SUPPORT}"
    peaks.category = "statistics"

    return peaks


ts_peaks_20.__doc__ = \
"""Confirmed local peaks of close (TS_PEAKS)

How many closes of the window are a local maximum with support 2: strictly
above the two closes before AND the two closes after them.

    peak[P]  = c[P] > c[P-1] and c[P] > c[P-2]
               and c[P] > c[P+1] and c[P] > c[P+2]
    TS_PEAKS = count of peaks among the window's `length - 4` candidates

An integer, 0 .. 6 at length 20 -- not a continuous feature. Two peaks must
be at least 3 bars apart (a peak is above the close two bars on either side,
so neither of two bars 2 apart can be above the other), and the 20-close
window holds 16 candidates at bars T-17 .. T-2, so at most 6 of them can
fire: exhaustive over all 65,536 subsets of the 16 candidate positions, the
largest pairwise-3-apart subset has 6 members, and a 20-close window that
attains 6 is pinned in `tests/test_ts_peaks_20.py`.

⚠ **The freshest bar it can COUNT is T-2, by construction.** Bar T's own
close IS read -- as the confirmation of older candidates -- but it can never
be counted itself: a peak at bar P is only countable once closes P+1 and P+2
exist, which is the issue's "a peak counts once confirmed 2 bars later". So
the newest two closes of the window enter ONLY as confirmation, and the
column cannot react to a high made today: planting a spike at the LAST bar of
a frame leaves the column bit-identical (measured). Dropping the confirmation -- counting a
candidate that merely tops its two predecessors -- is a different column
(Spearman 0.000035 on a walk, docs/TsPeaks20Measured.md, Gate A5).

⚠ **It is magnitude-blind.** A peak that stands 0.01% above its neighbours
counts exactly as much as one that stands 30% above them: planting a +10, a
+50 and a +1000 sigma return at the same bar of a 1,500-bar walk gives a
BIT-IDENTICAL column (16 fired bars move in each of the three cases). It is
not a volatility, trend-strength or outlier feature.

⚠ **A flat window and a monotone window BOTH read 0.** The comparison is
strict, so a plateau is not a peak: a flat, a strictly rising, a strictly
falling and a 100/101 zigzag 1,500-bar frame all read exactly 0.0 on all
1,481 fired bars (measured). A dead stock and a trending one are
indistinguishable here, and a strongly trending frame reads 0.0 on 1,465 of
its 1,481 bars.

⚠ **Peaks only, no troughs.** The source counts maxima of the series it is
given, so the column is asymmetric in sign: the same path mirrored
(`-close`) is a different column, Spearman 0.2886 on a walk (measured).

Source: tsfresh feature_calculators (MIT), `number_peaks`, as the formula is
stated by PandasTa issue #92: `number_peaks(x, n=2) on 20 closes; a peak
counts once confirmed 2 bars later`.
⚠ tsfresh is NOT installed in this worktree and web access is unavailable, so
the formula under test is the issue's line plus the published `number_peaks`
definition (support `n` on both sides, strict `>`), not a read of tsfresh's
own code; anything tsfresh does that the line does not say (how it treats a
series shorter than `2n + 1`, whether it drops NaNs rather than refusing) is
unverified here. What IS checked is that two independent spellings of that
definition -- an `np.roll`-per-window oracle and a plain-Python scalar loop
-- are bit-equal to this module, and that the issue's own screen prototype
(`docs/issues/screen/ind_screen.py`, candidate `ts_peaks_20`) is bit-equal to
it too on every clean frame measured. Unlike issue #91's `ts_perment_20`,
this port and the screened prototype are the SAME column
(docs/TsPeaks20Measured.md, Gate A2) -- which still does not transfer the
screen's Gate E numbers, because those were taken by a different harness run
on a prototype; the launcher's Gate E run on this module is the number that
decides ship/revert.

Four readings the wording leaves open, decided and priced in
docs/TsPeaks20Measured.md (A5) rather than assumed:
* Support on BOTH sides at distances 1 AND 2, the source's `for i in
  range(1, n + 1)`. Rejected: comparing only against the closes 2 away
  (Spearman 0.7674 on a walk, 0.7510 tick-rounded, 0.6070 on a coarse grid),
  and the immediate neighbours only, i.e. `n = 1` (0.1159 / 0.3485 / 0.4562).
* The comparison is STRICT. Rejected: `>=`, which makes a plateau a peak --
  free on a continuous walk (bit-equal on 1,481 of 1,481 bars) and decisive
  on a coarse grid (Spearman -0.0984, where 51.74% of candidates tie with a
  neighbour).
* The window is 20 CLOSES, so 16 candidates, and the first value lands at bar
  19. Rejected: 20 CANDIDATES, which needs 24 closes (Spearman 0.7916 /
  0.8021 / 0.8756).
* The output is the raw COUNT, the source's `np.sum`. Dividing by the 16
  candidates is an exact rescaling (Spearman 1.000000), so it is the one
  choice here a rank miner cannot see.

Discrete and heavily tied: 7 possible values at length 20, so a rank
statistic over this column carries many tied ranks by construction. Measured
over 1,481 bars of a walk: 6 distinct values, histogram
{0: 5, 1: 266, 2: 702, 3: 439, 4: 68, 5: 1}, and the ceiling 6 is reached by
none of the seven synthetic frames.

Causal: bar T reads closes T - length + 1 .. T, measured by a
future-perturbation sweep -- 0 of 37 offsets in each of the six
configurations run (three frames at the default, plus `length` 10, 60 and 5
on the walk).
Scale-free: stronger than a scale. The column reads only comparisons, so a
strictly increasing transform of price leaves it bit-identical -- x8, x64,
x1024, x10, x3.7 and x0.1 on 1,481 of 1,481 bars of each of seven frames, and
`log`, `sqrt`, `x**3` and `+1000` on the walk. That invariance holds up to a
float64 COLLAPSE: a transform that rounds two distinct closes onto the same
double can DESTROY a peak, because the comparison is strict -- none of the
scalings tested creates a new adjacent tie on any of the seven frames, which
is a measurement and not a guarantee (docs/TsPeaks20Measured.md, Gate D). A
DRIFT is not such a transform and does move the column (Spearman 0.4066
under +0.004 of log drift a bar), and neither is ROUNDING to a coarser grid
(0.5667 against the unrounded path), so price granularity is an input here.
NaN on the first `length - 1` bars, and on any window holding a close that is
NaN or infinite: such a close cannot be ordered, so it invalidates the
`2 * SUPPORT + 1` = 5 candidates it sits in, and since a window holds
`length - 4` candidates an INTERIOR such close -- bar `length - 1` through
`n - length` -- empties exactly `length` = 20 bars at the default (measured at
bar 200 of a 400-bar frame). Nearer either end fewer bars are emptied,
because the warm-up or the end of the frame swallows part of the span
(measured on the same frame: 1 bar for a NaN at bar 0 or at the last bar, 3 at
bar 2, 6 at bar 5). A zero, negative or subnormal close is NOT rejected: this
column takes no ratio and no logarithm, so such a close still compares.

Cost: the windows are a numpy view and both row reductions write straight to
`(rows,)`, so the traced peak does NOT grow with `length` -- measured 11.7 MB
at n = 400,000 for each of `length` 20, 60 and 250, against 22-24 / 30-35 /
65-66 ms (best of three, banded over four runs on one machine). That is the
reason `bad` is spelled `min(axis=1) < 0`: the equivalent
`(windows < 0).any(axis=1)` materialises a
`(rows, length - 4)` bool array, measured at a 6.8 MB peak at `length` 20 and
98.7 MB at `length` 250 against 0.8 MB for the `min` form, on the same
windows -- a flag array carrying all three reachable values -- and agreeing
with it on every one of them (docs/TsPeaks20Measured.md, Cost).
The O(n * length) work is the two row reductions themselves.

Calculation:
    Default Inputs:
        length=20   (support 2, fixed by issue #92)
    peak[P] = c[P] > c[P-1] and c[P] > c[P-2]
              and c[P] > c[P+1] and c[P] > c[P+2]
    TS_PEAKS[T] = sum of peak[P] for P in T-length+1+2 .. T-2

Args:
    close (pd.Series): Series of 'close's
    length (int): Closes per window. At least 5 -- a four-close window holds
        no candidate at all -- so a smaller or missing value falls back to
        the default. At 5 the column takes exactly the two values 0 and 1
        (measured). Default: 20
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)

Returns:
    pd.Series: TS_PEAKS_{length}_2, an integer-valued float count from 0.0 up
        to 6.0 at length 20
"""
