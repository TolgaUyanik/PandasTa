# -*- coding: utf-8 -*-
import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from pandas import Series

from pandas_ta.utils import get_offset, verify_series

#: The feature's OWN increment parameter -- the `001` of
#: `DN_OutlierInclude_n_001_mdrmd` -- so it is a module constant and not a
#: function of `length`: the threshold sweep below steps from 0 to the
#: window's own z-scored maximum in units of 0.01 standard deviation.
INC = 0.01
#: Divisor convention of the z-score catch22/hctsa apply before every
#: feature. 1 is MATLAB `zscore`'s default, and hctsa is MATLAB.
ZSCORE_DDOF = 1
#: Fewest returns a window may hold. Not from the source -- the definition
#: states no structural floor -- chosen so the `k=0` threshold step (roughly
#: half the window, since it is z-scored) starts from a handful of points
#: rather than one or two. A smaller or missing `length` falls back to the
#: default.
MIN_LENGTH = 10
#: A window of returns whose standard deviation is at most NOISE_ULPS machine
#: epsilons does not vary: its z-score is the rounding of `c / c1 - 1` rather
#: than shape. NaN instead. The floor is an ABSOLUTE constant because what it
#: bounds is a dimensionless RETURN, the same habit this fork's other
#: catch22-on-returns ports use (`c22_dfa`, `c22_periodicity`,
#: `c22_low_freq_power`, `c22_median_freq`).
NOISE_ULPS = 4096
NOISE_FLOOR = NOISE_ULPS * np.finfo(float).eps  # 9.09e-13
#: Doubles of window to evaluate at once. Each chunk allocates a `(rows,
#: length)` z-scored slab and, per threshold step, a `(rows, length)` mask
#: and gap slab, so this budget keeps the peak off the product
#: `len(close) * length * (thresholds swept)`.
CHUNK_VALUES = 1 << 16


#: Trim threshold, in PERCENT of the row's non-negative count: the sweep is
#: cut after the last step that still includes more than this share (the
#: reference's `trimthr = 2`).
TRIM_PCT = 2.0


def _outlier_timing_neg_rows(block, inc=INC, ddof=ZSCORE_DDOF):
    """The negative-outlier timing of each row of `block`.

    `block` is a `(rows, length)` slab of one-bar SIMPLE RETURNS, oldest
    first. Each row is z-scored (`ddof` = 1, MATLAB `zscore`) and NEGATED,
    so the window's most strongly negative returns become `y`'s largest
    values. `tot` is the row's count of `y >= 0`. Thresholds
    `j * inc` are swept for `j = 0 .. floor(max(y) / inc)`; at step `j` the
    qualifying positions are `r = {i : y[i] >= j * inc}`, 1-indexed (the
    MATLAB `find()` convention), and the step records:

    * `m1[j]` -- the mean gap between successive qualifying positions (NaN
      when fewer than two qualify; used only to cut the sweep);
    * `m3[j]` -- `(len(r) - 1) * 100 / tot`, the share of the row still
      included, in percent;
    * `m4[j]` -- `median(r) / (length / 2) - 1`, the qualifying set's median
      POSITION relative to the window's centre: 0 mid-window, -1 at the start,
      approaching +1 at the end.

    The sweep is cut at `min(mj, fbi)`, where `mj` is the LAST step with
    `m3 > TRIM_PCT` (2%) and `fbi` the FIRST step whose `m1` is NaN, and the
    row's value is the median of `m4[0 .. min(mj, fbi)]` -- hence `mdrmd`.
    This is catch22's `DN_OutlierInclude_n_001_mdrmd` step for step
    (Lubba et al. 2019); a measure-only comparison against pycatch22 0.4.5
    agrees on every window to 1e-12 (see the receipt).

    The per-threshold step is vectorised across rows by masking non-
    qualifying positions to NaN and taking `nanmedian`. Rows run past their
    own last step only up to the chunk's longest sweep; those extra steps are
    masked out before the cut.

    Comes back as NaN for a row holding a non-finite return and for a row
    whose standard deviation is at most `NOISE_FLOOR` or is not finite (where
    the reference returns 0.0 for an exactly constant window, this fork
    blanks, as its other catch22-on-returns ports do).
    """
    rows, n = block.shape
    bad = ~np.isfinite(block).all(axis=1)
    with np.errstate(invalid="ignore", over="ignore", divide="ignore"):
        sd = block.std(axis=1, ddof=ddof)
        bad |= ~(sd > NOISE_FLOOR) | ~np.isfinite(sd)
        z = (block - block.mean(axis=1, keepdims=True)) / sd[:, None]
    z = np.where(bad[:, None], 0.0, z)
    y = -z

    tot = (y >= 0.0).sum(axis=1).astype(float)
    max_y = y.max(axis=1)
    # Steps per row, as the reference counts them: int(max / inc) + 1.
    nth = np.where(bad, 1, (max_y / inc).astype(int) + 1)
    k_max = int(nth.max()) if rows else 0

    pos1 = np.arange(1, n + 1, dtype=float)[None, :]
    half = n / 2.0
    m1_nan = np.ones((rows, k_max), dtype=bool)
    m3 = np.zeros((rows, k_max))
    m4 = np.full((rows, k_max), np.nan)
    with np.errstate(invalid="ignore", divide="ignore"):
        for k in range(k_max):
            mask = y >= (k * inc)
            cnt = mask.sum(axis=1)
            m1_nan[:, k] = cnt < 2
            m3[:, k] = (cnt - 1) * 100.0 / tot
            has_any = cnt > 0
            if has_any.any():
                qualifying = np.where(mask[has_any], pos1, np.nan)
                m4[has_any, k] = np.nanmedian(qualifying, axis=1) / half - 1.0

    steps = np.arange(k_max)[None, :]
    live = steps < nth[:, None]
    # mj: last live step with m3 > TRIM_PCT (0 if none). fbi: first live step
    # with a NaN mean gap (the row's last step if none).
    over = live & (m3 > TRIM_PCT)
    mj = np.where(over.any(axis=1), k_max - 1 - np.argmax(over[:, ::-1], axis=1), 0)
    gapnan = live & m1_nan
    fbi = np.where(gapnan.any(axis=1), np.argmax(gapnan, axis=1), nth - 1)
    cut = np.minimum(mj, fbi)
    keep = steps <= cut[:, None]
    with np.errstate(invalid="ignore"):
        result = np.nanmedian(np.where(keep, m4, np.nan), axis=1) if k_max else np.full(rows, np.nan)
    return np.where(~bad, result, np.nan)


def c22_outlier_timing_neg(close, length=None, offset=None, **kwargs):
    """Indicator: catch22 timing of negative return outliers (C22OUTLIERNEG)"""
    # Validate Arguments
    length = int(length) if length and int(length) >= MIN_LENGTH else 100
    close = verify_series(close, length + 1)
    offset = get_offset(offset)

    if close is None: return

    # Calculate Result
    c = close.to_numpy(dtype=float)
    # A close that is not a finite, normal, positive float (NaN, inf, zero,
    # negative, or subnormal such as 1e-310) is bad data: it has no return to
    # take, so it is missing.
    c = np.where(np.isfinite(c) & (c >= np.finfo(float).tiny), c, np.nan)

    # The one-bar simple return, spelled as a price RATIO minus one: `8a / 8b`
    # is the same double as `a / b`, so a x2**k rescale of the price cancels
    # EXACTLY here and nothing downstream can see it.
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        r = c[1:] / c[:-1] - 1.0
    r = np.where(np.isfinite(r), r, np.nan)

    n = c.size
    out = np.full(n, np.nan)
    if n >= length + 1:
        # The window ending at bar T holds the `length` returns of bars
        # T - length + 1 .. T, which read closes T - length .. T: bar `length`
        # is the first that fires.
        win = sliding_window_view(r, length)
        rows = win.shape[0]
        step = max(1, CHUNK_VALUES // length)
        for a in range(0, rows, step):
            b = min(a + step, rows)
            out[length + a:length + b] = _outlier_timing_neg_rows(win[a:b])

    result = Series(out, index=close.index)

    # Offset
    if offset != 0:
        result = result.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        result.fillna(kwargs["fillna"], inplace=True)

    # Name and Categorize it
    result.name = f"C22OUTLIERNEG_{length}"
    result.category = "statistics"

    return result


c22_outlier_timing_neg.__doc__ = \
"""catch22 timing of negative return outliers (C22OUTLIERNEG)

Z-score the last `length` daily returns and negate the z-score, so the
window's most strongly NEGATIVE returns read as `y`'s largest values. Sweep
a threshold `thr` from 0 to `max(y)` in steps of `INC` = 0.01 standard
deviation; at each step, among the positions where `y >= thr` (1-indexed),
take the MEDIAN POSITION of the qualifying set and normalise it to the
window's own half-length (`median(idx) / (length/2) - 1`, 0 at mid-window,
-1 crowded to the start, +1 crowded to the end). The sweep is cut at the
earlier of two steps: the LAST step whose qualifying set, less one, is
still more than 2% of the window's `y >= 0` count, and the FIRST step with
fewer than two qualifying points. The column is the MEDIAN, over the steps
up to that cut, of those per-step normalised median positions -- `mdrmd`: the outer MeDian, across the sweep, of each step's own
median-Rank reading, MeDian-reduced -- reading how early or late in the
window the net's progressively more extreme negative outliers sit, not how
far apart they are.

    Z   = (X - mean(X)) / sd(X, ddof=1)
    Y   = -Z
    tot = count(Y >= 0)
    for j = 0 .. floor(max(Y) / INC):
        idx(j)   = 1-indexed positions i with Y[i] >= j * INC
        rank(j)  = median(idx(j)) / (length/2) - 1
        share(j) = (len(idx(j)) - 1) * 100 / tot
    mj  = last j with share(j) > TRIM_PCT (2)       (0 if none)
    fbi = first j with len(idx(j)) < 2              (last j if none)
    C22OUTLIERNEG = median(rank(0 .. min(mj, fbi)))

**Source: catch22 (Lubba, Sethi, Knaute, Schultz, Fulcher, Jones 2019, *Data
Mining and Knowledge Discovery* 33:1821, "catch22: CAnonical Time-series
CHaracteristics"), feature `DN_OutlierInclude_n_001_mdrmd` -- hctsa's
`DN_OutlierInclude(y, 'n', 0.01)` operation, whose output table names its
`md`-suffixed outputs by the per-threshold statistic (`mdr`, the normalised
median RANK of the qualifying set) and the outer reduction (`md`, median
across the trimmed sweep) -- applied by PandasTa issue #142 to the last 100
daily simple returns.** ⚠ catch22 is a subset selected for TIME-SERIES
CLASSIFICATION performance on 93 reference problems. That is not return
prediction, and nothing here tests it on BIST: its presence in this fork is
existence, not evidence. Shape features of z-scored returns can pick up
BIST tick rounding (many zero or repeated returns on low-priced stocks); see
Gate C and Gate E for whether a price level or `Volume` tops the
attribution comparators.

The reference implementation (pycatch22) is **GPL-3.0** and this fork
is MIT: this module was written from the feature's published description
above, never from the reference's source, and no shipped module imports it
(a test asserts that over the whole package).

**Checked against the reference's OUTPUT, measure-only.** pycatch22 0.4.5
(GPL-3.0) was installed in a separate scratch environment, never in this
package's, and run as a black box on every full window of six synthetic
1,500-bar frames at lengths 100, 10 and 37: 26,118 windows, and this column
agrees with it on every one to 1e-12 (measured 2026-11-24, owner). No code
was read from it, and no shipped module imports it (a test asserts that
over the whole package). Gate A also keeps an independent SECOND SPELLING of
the kernel (plain Python, `statistics.median`, no numpy, no shared code with
the vectorised kernel above). Two earlier versions of this port did not agree. Round 1 (commit
`11ebc10`) read `mdrmd` as a nested median of inter-event GAPS. Round 2 kept
the median position but cut the sweep at a fixed 2% of the window rather
than at the reference's rule, which moved 116 of 600 windows of a test
frame (median absolute difference 0.03, largest 0.26). Round 3, this
version, uses the reference's cut, step for step.

**The z-score's divisor convention is NOT inert here**, unlike in several of
this fork's other catch22 ports: `ddof` rescales every `y[i]` by the same
positive factor (`sqrt((n - ddof) / n)` of each other), which preserves the
RANKING of positions but not which ones clear a fixed ABSOLUTE threshold
`k * INC` -- a threshold sweep in absolute units is exactly the one
operation an overall rescale is not blind to. Measured small but nonzero:
`tests/test_c22_outlier_timing_neg.py` finds 1 of 9 sampled `ar1` windows
moved between `ddof` 0 and 1. `ZSCORE_DDOF` = 1 is kept at MATLAB
`zscore`'s default (hctsa's own convention) for the same reason every
sibling port uses it, not because this feature happens to be blind to it.

Calculation:
    Default Inputs:
        length=100, INC=0.01, ZSCORE_DDOF=1, TRIM_PCT=2
    r[t] = close[t] / close[t-1] - 1
    X    = r[T-length+1 .. T]                   (the window)
    Z    = (X - mean(X)) / sd(X, ddof=1)
    Y    = -Z
    C22OUTLIERNEG = the median-of-median-positions described above, UNITLESS

**ONE blanking rule.** The window is NaN unless its return standard
deviation clears 9.09e-13 (4096 eps) -- the same floor this fork's other
catch22 ports use -- so that this column reads the TIMING of the window's
own extremes and not the rounding of a flat window.

Causal: bar T reads closes T - length .. T. Measured by future-perturbation
sweep and by mutants read off this module's source, edited and exec'd in
memory (`docs/measure_c22_outlier_timing_neg.py` section B).

Scale-free: the output is a normalised MEDIAN POSITION bounded in roughly
[-1, 1] (a median of per-threshold median ranks, each itself normalised by
the window's own half-length), dimensionless with respect to price by
construction -- the price enters only as `c[t] / c[t-1]`, which is exact
under a power-of-two rescale, and the whole computation past that point is
a function of the Z-SCORE alone, invariant under `a * r + b` for any
`a > 0` (NOT `a < 0`: a sign flip of the returns swaps which tail is
"negative"). Measured bit-identical under a x8/x64 price rescale and under
an inexact x10/x3.7 price or return rescale -- see
`docs/measure_c22_outlier_timing_neg.py` section D and
`tests/test_c22_outlier_timing_neg.py`. It IS dimensionless with respect to
`length` too, unlike this fork's integer/count catch22 outputs
(`c22_dfa`, `c22_periodicity`): the `/(length/2)` term in the per-threshold
reduction is exactly what makes a median POSITION comparable across window
sizes, where a median GAP (bars) would not be.

NaN on the first `length` bars; on every window holding a close that is NaN,
infinite, zero, negative or subnormal; on a window holding a close PAIR
whose ratio overflows to an infinite return; and under the blanking rule
above.

Cost: the windows are walked in chunks, so the peak is set by `CHUNK_VALUES`
and not by `len(close) * length * (thresholds swept)`; measured cost is in
`docs/C22OutlierTimingNegMeasured.md`.

Args:
    close (pd.Series): Series of 'close's
    length (int): RETURNS per window, so `length + 1` closes. At least
        `MIN_LENGTH` = 10, and a smaller or missing value falls back to the
        default. Default: 100
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)

Returns:
    pd.Series: C22OUTLIERNEG_{length}, a normalised median event position
        bounded in roughly [-1, 1]
"""
