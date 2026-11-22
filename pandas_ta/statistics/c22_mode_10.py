# -*- coding: utf-8 -*-
import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from pandas import Series

from pandas_ta.utils import get_offset, verify_series

#: The feature's OWN parameter -- the `10` of `DN_HistogramMode_10` -- so it
#: is a module constant and not a function of `length`. `DN_HistogramMode_5`
#: (this fork's `c22_mode_5`) is the same operation at 5 bins.
NUM_BINS = 10
#: Divisor convention of the z-score catch22 applies before every feature. 1
#: is MATLAB `zscore`'s default, and hctsa is MATLAB. Unlike this fork's
#: dimensionless catch22 ports (`c22_entropy_pairs`, `c22_dfa`), this
#: column's OUTPUT is itself a z-score value -- a histogram-bin centre, in
#: z-units -- so the divisor is not inert here: it sets the output's own
#: scale, not merely a cut point's position.
ZSCORE_DDOF = 1
#: Fewest returns a window may hold. Below `NUM_BINS`, several of the 10
#: bins could hold at most zero or one observation by pigeonhole alone,
#: before the data's own shape is read at all; a smaller or missing
#: `length` falls back to the default. A module choice, not from the source.
MIN_LENGTH = NUM_BINS
#: A window of returns whose standard deviation is at most NOISE_ULPS machine
#: epsilons does not vary: its z-score is decided by the rounding of
#: `c / c1 - 1` rather than by shape. NaN instead. The floor is an ABSOLUTE
#: constant because what it bounds is a dimensionless RETURN, the same habit
#: this fork's other catch22-on-returns ports use (`c22_entropy_pairs`,
#: `c22_ami2`, `c22_ami_timescale`, `c22_dfa`, `c22_periodicity`,
#: `c22_mode_5`).
NOISE_ULPS = 4096
NOISE_FLOOR = NOISE_ULPS * np.finfo(float).eps  # 9.09e-13
#: Doubles of window to evaluate at once. Each chunk allocates a `(rows,
#: length)` z-scored slab and a same-shaped bin-index slab, so this budget is
#: what keeps the peak off the product `len(close) * length`.
CHUNK_VALUES = 1 << 19


def _mode10_rows(block):
    """The histogram mode, in z-score units, of each row's own z-scored
    10-bin equal-width histogram.

    `block` is a `(rows, length)` slab of one-bar SIMPLE RETURNS, oldest
    first. Each row is z-scored; cut into `NUM_BINS` = 10 equal-width bins
    spanning its OWN [min, max]; and the output is the mean of the bin
    centre(s) of whichever bin(s) hold the most observations -- hctsa's
    `DN_HistogramMode` tie rule, which AVERAGES every tied bin's centre
    rather than picking one.

    Comes back as NaN for a row holding a non-finite return, for a row
    whose standard deviation is at most `NOISE_FLOOR` or is not finite (no
    z-score to take), and for the degenerate case the floor already rules
    out in practice -- a z-scored window whose own range is zero or not
    finite.
    """
    rows, n = block.shape

    bad = ~np.isfinite(block).all(axis=1)
    with np.errstate(invalid="ignore", over="ignore", divide="ignore"):
        sd = block.std(axis=1, ddof=ZSCORE_DDOF)
        z = (block - block.mean(axis=1, keepdims=True)) / sd[:, None]
        bad |= ~(sd > NOISE_FLOOR) | ~np.isfinite(sd)

        mn = z.min(axis=1)
        mx = z.max(axis=1)
        width = (mx - mn) / NUM_BINS
        bad |= ~(width > 0.0) | ~np.isfinite(width)

        # Bin index: how many whole bin-widths above the row's own minimum.
        # The maximum element lands at index `NUM_BINS` (its distance from
        # `mn` is exactly `NUM_BINS` widths), so it is clipped into the last
        # bin -- the same "last bin is closed on both ends" convention
        # MATLAB's `histcounts` and `numpy.histogram` both use.
        idx = np.floor((z - mn[:, None]) / width[:, None])
    # A `bad` row (flat sd, zero/non-finite width) can leave `idx` NaN or
    # infinite; its output is overwritten by NaN at the end regardless, but
    # `bincount` below needs a real non-negative integer to index with.
    idx = np.where(np.isfinite(idx), idx, 0.0)
    idx = np.clip(idx, 0.0, NUM_BINS - 1).astype(np.int64)

    code = idx + (np.arange(rows) * NUM_BINS)[:, None]
    counts = np.bincount(code.ravel(), minlength=rows * NUM_BINS)
    counts = counts.reshape(rows, NUM_BINS)

    max_count = counts.max(axis=1, keepdims=True)
    tied = counts == max_count
    centres = mn[:, None] + (np.arange(NUM_BINS)[None, :] + 0.5) * width[:, None]
    mode = (centres * tied).sum(axis=1) / tied.sum(axis=1)

    return np.where(~bad, mode, np.nan)


def c22_mode_10(close, length=None, offset=None, **kwargs):
    """Indicator: catch22 mode of a 10-bin histogram of the z-scored return
    window (C22MODE10)"""
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
            out[length + a:length + b] = _mode10_rows(win[a:b])

    result = Series(out, index=close.index)

    # Offset
    if offset != 0:
        result = result.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        result.fillna(kwargs["fillna"], inplace=True)

    # Name and Categorize it
    result.name = f"C22MODE10_{length}"
    result.category = "statistics"

    return result


c22_mode_10.__doc__ = \
"""catch22 mode of a 10-bin histogram of the z-scored return window (C22MODE10)

Z-score the last `length` daily returns, cut the z-scored window into
`NUM_BINS` = 10 equal-width bins spanning its OWN [min, max], and report the
mean of the bin centre(s) of whichever bin(s) hold the most observations.
hctsa's tie rule: when two or more bins are tied for the most observations,
average ALL of their centres rather than pick one arbitrarily.

    Z   = (X - mean(X)) / sd(X, ddof=1)
    C22MODE10 = mean of bin-centre(s) of the mode bin(s) of a 10-bin
                equal-width histogram of Z over [min(Z), max(Z)]

**Source: catch22 (Lubba, Sethi, Knaute, Schultz, Fulcher, Jones 2019, *Data
Mining and Knowledge Discovery* 33:1821, "catch22: CAnonical Time-series
CHaracteristics"), feature `DN_HistogramMode_10` of catch22 1.0 -- hctsa's
`DN_HistogramMode(y, 10)` -- applied by PandasTa issue #136 to the last 100
daily simple returns.** ⚠ catch22 is a subset selected for TIME-SERIES
CLASSIFICATION performance on 93 reference problems. That is not return
prediction, and nothing here tests it on BIST: its presence in this fork is
existence, not evidence.

The reference implementation (pycatch22 1.0.2) is **GPL-3.0** and this fork
is MIT: this module was written from the paper's description of the feature
family (the mode of a z-scored equal-width histogram) and from hctsa's
published operation name and parameter (`DN_HistogramMode`, bin count 10),
never from the reference's source. No shipped module imports it (a test
asserts that over the whole package); the one place it is run at all is
`docs/measure_c22_mode_10.py`, opt-in, measurement only, the same use the
owner's own screen prototype makes of it.

**Unlike this fork's other catch22-on-returns ports, z-scoring here is NOT
inert**, the same caveat `c22_mode_5` (this module's 5-bin sibling)
carries. `c22_entropy_pairs` and `c22_dfa` read only the ORDER or the
quantile-relative POSITION of z-scored values, which an affine map cannot
move; this column's output is a bin CENTRE position in z-units, which an
affine map of the input DOES move, by the same affine map. The issue's own
name for this candidate -- "the z-scored 10-bin return histogram" -- is read
as applying literally: the shipped value is in z-score units, not raw return
units.

**The bin-edge convention matches `numpy.histogram`'s and MATLAB
`histcounts`' own equal-width default**: `NUM_BINS` bins of equal width over
`[min, max]`, each closed on the left and open on the right except the last,
which is closed on BOTH ends (so the maximum element is never lost to a
would-be eleventh bin).

Calculation:
    Default Inputs:
        length=100, NUM_BINS=10, ZSCORE_DDOF=1
    r[t]    = close[t] / close[t-1] - 1
    X       = r[T-length+1 .. T]                (the window)
    Z       = (X - mean(X)) / sd(X, ddof=1)
    edges   = linspace(min(Z), max(Z), NUM_BINS + 1)
    counts  = histogram of Z over edges (last bin closed on both ends)
    M       = {{i : counts[i] = max(counts)}}
    C22MODE10 = mean over i in M of (edges[i] + edges[i+1]) / 2

**ONE blanking rule.** The window is NaN unless its return standard
deviation clears 9.09e-13 (4096 eps) -- the same floor this fork's other
catch22 ports on returns use -- so that this column reads SHAPE and not the
rounding of a flat window.

Causal: bar T reads closes T - length .. T. Measured by future-perturbation
sweep and by mutants read off this module's source, edited and exec'd in
memory (`docs/measure_c22_mode_10.py` section B).

Scale-free: z-scoring removes any affine dependence on the RAW return scale
-- `Z' = (kX + d - mean(kX + d)) / sd(kX + d, ddof=1) = Z` for any `k > 0`
and any shift `d`, exactly, in real arithmetic -- so the shipped column is
dimensionless by construction. In floating point this is bit-identical under
a x8/x64 price rescale (the price enters only as `c[t] / c[t-1]`, and
`8a / 8b` is the double `a / b`) and measured within a small tolerance under
an inexact return rescale (x10, x3.7) -- see `docs/measure_c22_mode_10.py`
section D and `tests/test_c22_mode_10.py`.

NaN on the first `length` bars; on every window holding a close that is NaN,
infinite, zero, negative or subnormal; on a window holding a close PAIR whose
ratio overflows to an infinite return; and under the blanking rule above.

Args:
    close (pd.Series): Series of 'close's
    length (int): RETURNS per window, so `length + 1` closes. At least
        `NUM_BINS` = 10, and a smaller or missing value falls back to the
        default. Default: 100
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)

Returns:
    pd.Series: C22MODE10_{length}, a z-score value, typically inside roughly
        [-3, 3] for a return-sized window but not hard-bounded
"""
