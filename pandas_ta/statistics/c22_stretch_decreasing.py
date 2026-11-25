# -*- coding: utf-8 -*-
import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from pandas import Series

from pandas_ta.utils import get_offset, verify_series

# A window of one return has no diff to take, and a window of two returns
# has exactly one diff, whose sign is genuinely data-dependent (unlike
# `ts_strike_20`'s length=2, which is a forced constant). So the smallest
# window that can vary is already length=2; length=1 would be the forced
# constant 0 (no diff exists, so there is never a fall), which is why it is
# refused rather than kept.
MIN_LENGTH = 2
EXTRA_CLOSES = 1  # `length` returns need `length + 1` closes

# A window whose returns vary only at float-rounding level has no fall to
# read: an exactly geometric path has mathematically CONSTANT returns, but
# float64 accumulates tiny last-bit differences between them, and an
# unguarded reading would report a run read off that noise rather than the
# honest answer (0 -- no real decrease exists). Guarding on the window's own
# return SPAN, not on each diff individually, is this fork's existing habit
# on a dimensionless quantity (`ts_strike_20`, `ts_binent_20`, `ts_c3_20`,
# `lean_hurst_100`); the floor can be an absolute constant because what it
# bounds is the range of DIMENSIONLESS price ratios, which has no rolling
# scale of its own to keep causal.
NOISE_ULPS = 4096
NOISE_FLOOR = NOISE_ULPS * np.finfo(float).eps  # 9.09e-13


def c22_stretch_decreasing(close, length=None, offset=None, **kwargs):
    """Indicator: catch22/hctsa longest run of falling returns (C22STRETCHDEC)"""
    # Validate Arguments
    length = int(length) if length and int(length) >= MIN_LENGTH else 100
    close = verify_series(close, length + EXTRA_CLOSES)
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
    r = np.full(c.size, np.nan)
    with np.errstate(over="ignore"):
        r[1:] = c[1:] / c[:-1] - 1.0
    r = np.where(np.isfinite(r), r, np.nan)

    # (n - length + 1, length) causal windows of returns, oldest first. The
    # window ending at bar T holds r[T-length+1 .. T], so it reads closes
    # T - length .. T and the first full window sits at bar `length - 1`.
    windows = sliding_window_view(r, length)
    bad = np.isnan(windows).any(axis=1)
    span = windows.max(axis=1) - windows.min(axis=1)

    # The `length - 1` successive differences of the window's own returns.
    # Strictly negative is a FALL (the feature's own name, "falling returns");
    # zero (a flat or repeated return -- BIST tick rounding, the issue's own
    # worry) or positive BREAKS the run rather than extending it.
    diffs = windows[:, 1:] - windows[:, :-1]
    falling = diffs < 0.0

    # Longest run of consecutive True, read one column at a time so the
    # whole frame advances together: `current` is the run ending at this
    # column and `longest` the best seen so far.
    current = np.zeros(windows.shape[0])
    longest = np.zeros(windows.shape[0])
    for j in range(length - 1):
        current = np.where(falling[:, j], current + 1.0, 0.0)
        longest = np.maximum(longest, current)

    # A window whose returns are constant to rounding level has no real fall
    # to read: 0, the value a mathematically flat window gives, rather than a
    # run read off float64 noise.
    body = np.where(span > NOISE_FLOOR, longest, 0.0)

    out = np.full(c.size, np.nan)
    out[length - 1:] = np.where(bad, np.nan, body)
    result = Series(out, index=close.index)

    # Offset
    if offset != 0:
        result = result.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        result.fillna(kwargs["fillna"], inplace=True)

    # Name and Categorize it
    result.name = f"C22STRETCHDEC_{length}"
    result.category = "statistics"

    return result


c22_stretch_decreasing.__doc__ = \
"""catch22/hctsa longest run of falling returns (C22STRETCHDEC)

How long the recent returns kept falling, one after another: take the
`length` trailing simple returns, mark every bar whose return is STRICTLY
below the one before it, and report the length of the longest unbroken run
of marks.

    C22STRETCHDEC = longest run of consecutive (r[i] < r[i-1]) in the window

**Source: catch22's `SB_BinaryStats_diff_longstretch0`** (Lubba, Sethi,
Knaute, Schultz, Fulcher, Jones 2019, *Data Mining and Knowledge Discovery*
33:1821, "catch22: CAnonical Time-series CHaracteristics"; reference code
pycatch22 1.0.2, GPL-3.0), as screened by PandasTa issue #140, applied to the
last 100 daily simple returns. catch22's own published one-line description
of the feature is "longest period of successive decreases". ⚠ catch22 is a
subset selected for TIME-SERIES CLASSIFICATION performance on 93 reference
problems. That is not return prediction, and nothing here tests it on BIST:
its presence in this fork is existence, not evidence.

The reference implementations (pycatch22, hctsa) are **GPL-3.0** and this
fork is MIT: this module was written from the feature's published
definition -- binarize the first difference of the input by its SIGN and
report the longest run of the "did not increase" state -- never from the
references' source. No shipped module imports either.

**Two choices the definition does not pin, decided and priced here:**
* The hctsa operation family (`SB_BinaryStats`) binarizes a diffed series by
  sign and reports `longstretch0`, the longest run of the ZERO state. Which
  sign that state is (`diff < 0` vs `diff <= 0`) is not spelled out by the
  feature's own one-line name. This module reads "falling" as STRICT: a diff
  of exactly zero (two equal, or two repeated-zero, returns -- the issue's
  own BIST tick-rounding worry) is FLAT, not falling, and breaks the run
  rather than extending it. The `<=` reading would instead fold a repeated
  return into "not increasing", counting it as a continued fall; that
  reading is NOT what this module ships.
* catch22's own pipeline z-scores every window before every feature. Z-scoring
  is `(x - mean(x)) / sd(x)`, an affine map with a POSITIVE slope (for
  `sd(x) > 0`): `diff(a*x + b) = a * diff(x)` for a constant `b`, and
  multiplying by a positive `a` cannot flip a sign. So the z-score is INERT
  for this feature by construction -- it changes no diff's sign and hence no
  run -- and this module skips it rather than computing and discarding it.

**One blanking-to-zero rule**, the same habit this fork's other return-based
statistics ports use on a dimensionless quantity (`ts_strike_20`,
`ts_binent_20`, `ts_c3_20`, `lean_hurst_100`): a window whose `length`
returns vary only at float-rounding level (span `<= 9.09e-13`, 4096 eps) has
no real fall to read -- its mathematical answer is 0, since constant returns
never decrease -- but float64 arithmetic gives such a window tiny non-zero
diffs, so without the guard it would report a run read off that noise rather
than the honest 0.

Calculation:
    Default Inputs:
        length=100
    r[t]           = close[t] / close[t-1] - 1
    d[i]           = r[i] - r[i-1],  i = T-length+2 .. T  (length - 1 diffs)
    C22STRETCHDEC  = longest run of consecutive (d[i] < 0), or 0 when the
                     window's own return span is <= 9.09e-13

Causal: bar T reads closes T - length .. T. Measured by future-perturbation
sweep and by mutants read off this module's source, edited and exec'd in
memory (`docs/measure_c22_stretch_decreasing.py` section B).

Scale-free: every diff compares two dimensionless simple returns, and
`8a / 8b` is the same double as `a / b`, so the column is bit-identical
under a x8/x64 price rescale (the price enters only as `c[t] / c[t-1]`).
Because the statistic depends only on the SIGN of each diff, and a positive
affine map of the returns cannot flip that sign, it is ALSO bit-identical
under a positive affine rescale of the returns themselves (x10, x3.7) --
stronger than the usual "measured under tolerance" most of this fork's
return-based catch22 ports carry, and measured directly in
`tests/test_c22_stretch_decreasing.py`.

NaN on the first `length` bars (the window ending at bar `length - 1` still
reads back to the undefined first return, so it is NaN too -- the same
warm-up ts_strike_20 and c22_median_freq both have); on every window holding
a close that is NaN, infinite, zero, negative or subnormal; and on a window
holding a close PAIR whose ratio overflows to an infinite return.

Args:
    close (pd.Series): Series of 'close's
    length (int): RETURNS per window, so `length + 1` closes. At least
        `MIN_LENGTH` = 2 -- a 1-return window has no diff to take and is a
        forced constant 0 -- and a smaller or missing value falls back to
        the default. Default: 100
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)

Returns:
    pd.Series: C22STRETCHDEC_{length}, an integer-valued count of bars in
        `{0 .. length - 1}`
"""
