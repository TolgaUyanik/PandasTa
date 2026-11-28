# -*- coding: utf-8 -*-
import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from pandas import Series

from pandas_ta.utils import get_offset, verify_series

#: The feature's OWN lag -- the `1` of `CO_trev_1_num` -- so it is a module
#: constant and not a function of `length`. catch22 also ships a lag-2
#: sibling (not ported here).
LAG = 1
#: Divisor convention of the z-score catch22 applies before every feature. 1
#: is MATLAB `zscore`'s default, and hctsa is MATLAB. This fork's habit for
#: every other catch22-on-returns port (`c22_ami2`, `c22_mode_5`,
#: `c22_entropy_pairs`, ...).
ZSCORE_DDOF = 1
#: Fewest returns a window may hold: at least 2 so the single pairwise
#: difference the lag-1 asymmetry needs exists, plus 1 more so that mean is
#: itself an average of more than one term rather than a single cubed value.
#: A module choice, not from the source; a smaller or missing `length` falls
#: back to the default.
MIN_LENGTH = 3
#: A window of returns whose standard deviation is at most NOISE_ULPS machine
#: epsilons does not vary: its z-score is decided by the rounding of
#: `c / c1 - 1` rather than by shape. NaN instead. The floor is an ABSOLUTE
#: constant because what it bounds is a dimensionless RETURN, the same habit
#: this fork's other catch22-on-returns ports use (`c22_ami2`, `c22_mode_5`,
#: `c22_entropy_pairs`, `c22_dfa`, `c22_periodicity`).
NOISE_ULPS = 4096
NOISE_FLOOR = NOISE_ULPS * np.finfo(float).eps  # 9.09e-13
#: Doubles of window to evaluate at once. Each chunk allocates a `(rows,
#: length)` z-scored slab, so this budget is what keeps the peak off the
#: product `len(close) * length`.
CHUNK_VALUES = 1 << 19


def _trev_rows(block):
    """The time-reversal asymmetry of each row's own z-scored window.

    `block` is a `(rows, length)` slab of one-bar SIMPLE RETURNS, oldest
    first. Each row is z-scored; the mean CUBE of its consecutive
    (lag-1) differences is returned -- positive when rises are sharper than
    falls, negative when falls are sharper than rises.

    Comes back as NaN for a row holding a non-finite return and for a row
    whose standard deviation is at most `NOISE_FLOOR` or is not finite (no
    z-score to take).
    """
    bad = ~np.isfinite(block).all(axis=1)
    with np.errstate(invalid="ignore", over="ignore", divide="ignore"):
        sd = block.std(axis=1, ddof=ZSCORE_DDOF)
        z = (block - block.mean(axis=1, keepdims=True)) / sd[:, None]
        bad |= ~(sd > NOISE_FLOOR) | ~np.isfinite(sd)

        diffs = z[:, LAG:] - z[:, :-LAG]
        trev = (diffs ** 3).mean(axis=1)

    return np.where(~bad, trev, np.nan)


def c22_trev(close, length=None, offset=None, **kwargs):
    """Indicator: catch22 time-reversal asymmetry of returns at lag 1
    (C22TREV)"""
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
        # T - length + 1 .. T, which read closes T - length .. T: bar
        # `length` is the first that fires.
        win = sliding_window_view(r, length)
        rows = win.shape[0]
        step = max(1, CHUNK_VALUES // length)
        for a in range(0, rows, step):
            b = min(a + step, rows)
            out[length + a:length + b] = _trev_rows(win[a:b])

    result = Series(out, index=close.index)

    # Offset
    if offset != 0:
        result = result.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        result.fillna(kwargs["fillna"], inplace=True)

    # Name and Categorize it
    result.name = f"C22TREV_{length}"
    result.category = "statistics"

    return result


c22_trev.__doc__ = \
"""catch22 time-reversal asymmetry of returns at lag 1 (C22TREV)

Z-score the last `length` daily simple returns and report the mean CUBE of
the window's consecutive (lag-1) z-score differences -- positive when rises
are sharper than falls, negative when falls are sharper than rises, zero for
a time-symmetric process.

    Z      = (X - mean(X)) / sd(X, ddof=1)
    C22TREV = mean_{i=1..length-1}((Z[i+1] - Z[i])**3)

**Source: catch22 (Lubba, Sethi, Knaute, Schultz, Fulcher, Jones 2019, *Data
Mining and Knowledge Discovery* 33:1821, "catch22: CAnonical Time-series
CHaracteristics"), feature `CO_trev_1_num` of catch22 1.0 -- the
time-reversal asymmetry statistic at lag 1 -- applied by PandasTa issue #263
to the last 100 daily simple returns.** ⚠ catch22 is a subset selected for
TIME-SERIES CLASSIFICATION performance on 93 reference problems. That is not
return prediction, and nothing here tests it on BIST: its presence in this
fork is existence, not evidence.

The prototype that measured this candidate (`docs/issues/screen/ind_screen_
r3.py`, candidate `c22_trev`, 2026-10-24) used pycatch22 (GPL-3.0); this
module is written from the paper's own definition above -- a mean cubed
lag-1 difference of a z-scored return window -- never from that reference's
source. No shipped module imports it (a test asserts that over the whole
package); the one place it is run at all is `docs/measure_c22_trev.py`,
opt-in, measurement only, the same use the owner's own screen prototype
makes of it.

Calculation:
    Default Inputs:
        length=100, LAG=1, ZSCORE_DDOF=1
    r[t]    = close[t] / close[t-1] - 1
    X       = r[T-length+1 .. T]                (the window)
    Z       = (X - mean(X)) / sd(X, ddof=1)
    C22TREV = mean over i=1..length-1 of (Z[i+1] - Z[i])**3

**ONE blanking rule.** The window is NaN unless its return standard
deviation clears 9.09e-13 (4096 eps) -- the same floor this fork's other
catch22 ports on returns use -- so that this column reads SHAPE and not the
rounding of a flat window.

Causal: bar T reads closes T - length .. T. Measured by future-perturbation
sweep and by mutants read off this module's source, edited and exec'd in
memory (`docs/measure_c22_trev.py` section B; `tests/test_c22_trev.py`).

Scale-free: the price enters only as `close[t] / close[t-1]`, and `8a / 8b`
is the same double as `a / b`, so the RETURN series is unchanged by any
price rescale and the output is bit-identical under a x8/x64 price rescale.
Z-scoring then cancels any positive affine map of the return window itself
in exact real arithmetic (`Z(kX + d) = Z(X)` for `k > 0`), so the column is
also blind, up to floating-point noise, to an inexact rescale of the
returns (x10, x3.7) -- see `docs/measure_c22_trev.py` section D and
`tests/test_c22_trev.py`.

NaN on the first `length` bars; on every window holding a close that is NaN,
infinite, zero, negative or subnormal; on a window holding a close PAIR
whose ratio overflows to an infinite return; and under the blanking rule
above.

Args:
    close (pd.Series): Series of 'close's
    length (int): RETURNS per window, so `length + 1` closes. At least
        `MIN_LENGTH` = 3, and a smaller or missing value falls back to the
        default. Default: 100
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)

Returns:
    pd.Series: C22TREV_{length}, dimensionless (a mean cubed z-score
        difference), unbounded in principle but typically a small number
        close to zero for return-sized windows
"""
