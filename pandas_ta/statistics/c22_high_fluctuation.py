# -*- coding: utf-8 -*-
import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from pandas import Series

from pandas_ta.utils import get_offset, verify_series

#: The feature's own threshold (the "40" of `MD_pNN_pnn40` is `0.04 * 1000`)
#: -- a module constant, not a function of `length`: the absolute z-score
#: gap a successive difference must clear to count as a "fluctuation".
THRESHOLD = 0.04
#: Divisor convention of the z-score catch22/hctsa apply before every
#: feature. 1 is MATLAB `zscore`'s default, and hctsa is MATLAB. Unlike
#: `c22_median_freq` (where the z-score is inert) or `c22_stretch_decreasing`
#: (where only its SIGN matters), this feature reads the z-scored SCALE
#: directly against an absolute threshold, so the divisor convention is
#: load-bearing here: changing it to ddof=0 rescales every z-score by
#: sqrt(length / (length - 1)), moving which diffs clear 0.04.
ZSCORE_DDOF = 1
#: A window of 2 returns has exactly 1 diff, and z-scoring 2 values always
#: places them at -1/sqrt(2) and +1/sqrt(2) (ddof=1): that diff is a FORCED
#: sqrt(2) ~= 1.4142 whenever the two returns differ at all, always far
#: above THRESHOLD, so every 2-return window reads a forced 1.0 regardless
#: of shape -- measured in `docs/measure_c22_high_fluctuation.py`
#: `min_length`. 3 is the smallest window whose value is genuinely
#: data-dependent (reaches both 0.5 and 1.0 on random triples, never forced
#: to one constant), so it is the floor rather than 2.
MIN_LENGTH = 3
EXTRA_CLOSES = 1  # `length` returns need `length + 1` closes
#: A window whose returns are constant to float-rounding level has a
#: standard deviation of (near) zero -- no z-score to take without dividing
#: by noise. This fork's existing habit on a dimensionless quantity
#: (`c22_median_freq`, `c22_mode_10`, `c22_stretch_decreasing`) guards on an
#: ABSOLUTE floor rather than a relative one, because what it bounds is the
#: standard deviation of dimensionless RETURNS, which has no rolling scale
#: of its own to keep causal.
NOISE_ULPS = 4096
NOISE_FLOOR = NOISE_ULPS * np.finfo(float).eps  # 9.09e-13


def c22_high_fluctuation(close, length=None, offset=None, **kwargs):
    """Indicator: catch22/hctsa share of successive return changes above
    0.04 sd (C22HIGHFLUCT)"""
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
    with np.errstate(invalid="ignore"):
        sd = windows.std(axis=1, ddof=ZSCORE_DDOF)
    bad |= ~(sd > NOISE_FLOOR) | ~np.isfinite(sd)

    # A `bad` row's own `sd` could be 0 or NaN; substitute a harmless 1.0 so
    # the division below never raises or spreads a NaN into a column this
    # row's output is about to be overwritten in anyway.
    safe_sd = np.where(bad, 1.0, sd)
    z = (windows - windows.mean(axis=1, keepdims=True)) / safe_sd[:, None]

    # The `length - 1` successive differences of the window's own z-scores,
    # and the SHARE of them whose absolute size clears THRESHOLD.
    d = z[:, 1:] - z[:, :-1]
    share = np.mean(np.abs(d) > THRESHOLD, axis=1)

    out = np.full(c.size, np.nan)
    out[length - 1:] = np.where(bad, np.nan, share)
    result = Series(out, index=close.index)

    # Offset
    if offset != 0:
        result = result.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        result.fillna(kwargs["fillna"], inplace=True)

    # Name and Categorize it
    result.name = f"C22HIGHFLUCT_{length}"
    result.category = "statistics"

    return result


c22_high_fluctuation.__doc__ = \
"""catch22/hctsa share of successive return changes above 0.04 sd (C22HIGHFLUCT)

How often the recent returns jumped by more than a small fixed amount, bar
to bar: z-score the `length` trailing simple returns, take the successive
differences of the z-scores, and report the SHARE of those differences
whose absolute size exceeds 0.04.

    C22HIGHFLUCT = share of |diff(Z)| > 0.04, Z = z-score of the window

**Source: catch22's `MD_pNN_pnn40`** (Lubba, Sethi, Knaute, Schultz,
Fulcher, Jones 2019, *Data Mining and Knowledge Discovery* 33:1821,
"catch22: CAnonical Time-series CHaracteristics"; reference code pycatch22
1.0.2, GPL-3.0), as screened by PandasTa issue #144 alongside the rest of
catch22, applied to the last 100 daily simple returns. catch22's published
family of `MD_pNNx` measures generalises the heart-rate-variability pNN50
statistic (the share of successive RR-interval changes exceeding 50ms) to
an arbitrary series: z-score it first, then count successive changes past
a fixed absolute threshold; `pnn40` is the member at threshold 0.04. ⚠
catch22 is a subset selected for TIME-SERIES CLASSIFICATION performance on
93 reference problems. That is not return prediction, and nothing here
tests it on BIST: its presence in this fork is existence, not evidence.

The reference implementations (pycatch22, hctsa) are **GPL-3.0** and this
fork is MIT: this module was written from the feature's published
definition -- z-score the series, difference it, and report the share of
differences exceeding a fixed absolute threshold -- never from the
references' source. No shipped module imports either.

**Unlike this fork's other return-based catch22 ports, the z-score here is
NOT inert.** `c22_median_freq` divides the z-score's divisor out of a power
ratio, and `c22_stretch_decreasing` reads only each diff's SIGN, which a
positive affine map cannot flip; this feature compares the z-scored diff's
MAGNITUDE against an absolute constant, so the divisor convention
(`ZSCORE_DDOF`) genuinely moves the output, and a NEGATIVE rescale of the
returns (which flips every diff's sign but not its magnitude) leaves this
column's value UNCHANGED -- the opposite of `c22_stretch_decreasing`'s own
negative-rescale behaviour, priced and measured in both modules' test
suites.

**One blanking rule.** The window is NaN unless its return standard
deviation clears `NOISE_FLOOR` (9.09e-13, 4096 eps) -- the same floor this
fork's other catch22-on-returns ports use -- so that a window whose returns
are constant to rounding level is NaN (no z-score to take) rather than a
share read off the sign of float64 noise.

Calculation:
    Default Inputs:
        length=100, THRESHOLD=0.04, ZSCORE_DDOF=1
    r[t]           = close[t] / close[t-1] - 1
    X              = r[T-length+1 .. T]                (the window)
    Z              = (X - mean(X)) / sd(X, ddof=1)
    d[i]           = Z[i] - Z[i-1],  i = 2 .. length    (length - 1 diffs)
    C22HIGHFLUCT   = count(|d[i]| > 0.04) / (length - 1)

Causal: bar T reads closes T - length .. T. Measured by future-perturbation
sweep and by mutants read off this module's source, edited and exec'd in
memory (`docs/measure_c22_high_fluctuation.py` section `gate_b`).

Scale-free: the output is a share on `[0, 1]`, dimensionless by
construction. The price enters only as `c[t] / c[t-1]`, so `8a / 8b` being
the same double as `a / b` makes the column bit-identical under a x8/x64
price rescale, and measured bit-identical under a x10/x3.7/x0.1 price
rescale too (`docs/measure_c22_high_fluctuation.py` section `gate_c_d`,
`tests/test_c22_high_fluctuation.py`). Mathematically, the z-score cancels
any affine map `a*r + b` of the returns themselves exactly in real
arithmetic (`a > 0`: `Z' = Z`; `a < 0`: `Z' = -Z`, and the share reads only
`|diff(Z)|`, so it is unchanged either way) -- but that is an identity in
REAL arithmetic, not a float64 proof like the price-ratio argument above,
since `mean`/`std`/division each round independently on the rescaled
array. Measured bit-identical on one frame (`walk`) under x10/x3.7/x0.1/x2.5 and
a +0.01 shift, and under a x-1 negation, because this statistic is a
COUNT over a fixed grid (`k / (length - 1)`) that only moves when a diff
crosses the 0.04 boundary, and none did on these frames -- see
`docs/measure_c22_high_fluctuation.py` section `gate_c_d`.

NaN on the first `length` bars; on every window holding a close that is NaN,
infinite, zero, negative or subnormal; on a window holding a close PAIR
whose ratio overflows to an infinite return; and under the blanking rule
above.

Args:
    close (pd.Series): Series of 'close's
    length (int): RETURNS per window, so `length + 1` closes. At least
        `MIN_LENGTH` = 3 -- a 2-return window has exactly 1 diff whose
        magnitude is a FORCED sqrt(2), always above THRESHOLD, so its
        output is a forced constant 1.0 rather than data-dependent -- and a
        smaller or missing value falls back to the default. Default: 100
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)

Returns:
    pd.Series: C22HIGHFLUCT_{length}, a share on [0, 1] in steps of
        1 / (length - 1)
"""
