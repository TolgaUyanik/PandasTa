# -*- coding: utf-8 -*-
"""Market Meanness Index of daily returns -- issue #184 (NM-MMI-250).

SOURCE (not Reddit -- the Reddit thread only NAMED this indicator, tier 4,
rd:algotrading:hr30er; the definition is read from the article itself):
Johann Christian Lotter, "The Market Meanness Index", financial-hacker.com.
The issue restates the article's own formula, in Zorro's own array order
(`Data[0]` the MOST RECENT bar, higher index further BACK in time):

    MMI = 100 * (nl + nh) / (n - 1)
    for i = 1 .. n - 1:
        if Data[i] > median and Data[i] > Data[i-1]: nh += 1
        if Data[i] < median and Data[i] < Data[i-1]: nl += 1

GATE A -- the issue's own formula (not the screen prototype
`docs/issues/screen/ind_screen_r7.py`'s `nm_mmi_250`; the issue's
instruction is "Gate A starts from the source formula, not the prototype"),
translated out of Zorro order into this fork's forward-chronological one.
In Zorro order `Data[i]` is further BACK in time than `Data[i-1]` (lower
index = more recent), so stepping `i-1 -> i` steps BACKWARD through time.
Writing the window oldest-first as `w[0 .. n-1]` (forward-chronological,
this module's own convention), `Data[i]` is `w[k]` and `Data[i-1]` is
`w[k+1]` for `k = 0 .. n-2` -- `Data[i]` the OLDER element of each
compared pair, `Data[i-1]` the one step NEWER. So for `k = 0 .. n-2`:

    if w[k] > median and w[k] > w[k+1]: nh += 1   # above median, falling back toward it
    if w[k] < median and w[k] < w[k+1]: nl += 1   # below median, rising back toward it
    MMI = 100 * (nl + nh) / (n - 1)

`Data` is the article's own series of daily (simple) returns, not price
levels -- the issue's own "Prototype" line: "on daily returns (the article:
about 75 for random changes)". `n = 250` is the article's own test period,
kept here as the `length` parameter's default rather than hard-coded, this
fork's standing convention for every other rolling-window port.

CAUSALITY. `r[t] = close[t]/close[t-1] - 1` is backward-looking by
construction, and `w = r[T-length+1 .. T]` (`sliding_window_view`, no
`center`) reads only returns at or before `T` -- so bar `T` of
`NM_MMI_{length}` reads only `close[T-length .. T]`. Every comparison inside
the window (`median`, `>`, `<`) is a pure function of that window's own
values, with no separate rolling state carried across windows.
`tests/test_nm_mmi_250.py` proves this with a future-splice probe (bars
before a perturbation point J stay bit-identical whether or not the frame's
tail is replaced) and three one-bar-shift mutants (the final write placed
one bar earlier, the computed MMI array rolled forward one row, and the
return's own write index shifted forward one bar): the real module leaks 0
bars at every swept J on every frame; each mutant is live and leaks at a
measured, frame-specific, strictly positive count of the swept offsets
(24/31 on `ar1`, 19/31 on `tick-rounded`, 20/31 on `walk` --
`docs/measure_nm_mmi_250.py`), never zero.

SCALE-FREE. `r[t] = close[t]/close[t-1] - 1` is a price RATIO minus one:
`(k*a)/(k*b)` is the identical double to `a/b` whenever `k` is an exactly
representable power of two (the multiply introduces no rounding, so
numerator and denominator are both scaled by the same exact factor and the
quotient is bit-for-bit unchanged) -- the same argument `c22_high_fluctuation`
and `rd_range_contraction` already rely on. Since every comparison downstream
(`median`, `>`, `<`) is a pure function of the bit-identical return array,
`NM_MMI_{length}` is BIT-IDENTICAL under a x8/x64 price rescale. A
non-power-of-two rescale (x10, x3.7) is not exact at the multiply step, so
each return picks up independent last-bit rounding noise; the column stays
within a tiny tolerance except on the rare window where two returns sit
close enough together that the rounding noise flips a `>`/`<` comparison,
which moves that one window's count by a whole `100 / (length - 1)` step.
Measured in `docs/measure_nm_mmi_250.py` (see docs/NmMmi250Measured.md for
the counted numbers).
"""
import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from pandas import Series

from pandas_ta.utils import get_offset, verify_series

#: `length` returns need `length + 1` closes (the extra one gives `r[0]` a
#: predecessor -- which is still NaN, since there is no close before bar 0).
EXTRA_CLOSES = 1
#: Below 3, the output is forced to (near-)one value rather than being
#: data-dependent. At `length = 2` there is exactly one pair (a, b) and the
#: median is their mean, so `a > m` and `a > b` always agree in sign (and
#: likewise for `<`): MMI is a forced 100 unless the pair ties exactly, in
#: which case it is a forced 0 -- never anything else. At `length = 3`, hand
#: enumeration of the 6 orderings of 3 distinct values gives MMI in
#: {50, 100} (2 of 6 orderings have BOTH pairs reverse, MMI=100; the other 4
#: have exactly ONE pair reverse, MMI=50) -- still not a single forced
#: constant, so 3 is the floor rather than 2.
MIN_LENGTH = 3


def nm_mmi_250(close, length=None, offset=None, **kwargs):
    """Indicator: Market Meanness Index of daily returns (NM_MMI)"""
    # Validate Arguments
    length = int(length) if length and int(length) >= MIN_LENGTH else 250
    close = verify_series(close, length + EXTRA_CLOSES)
    offset = get_offset(offset)

    if close is None: return

    # Calculate Result
    c = close.to_numpy(dtype=float)
    # A close that is not a finite, normal, positive float (NaN, inf, zero,
    # negative, or subnormal such as 1e-310) is bad data: it has no return to
    # take, so it is missing.
    c = np.where(np.isfinite(c) & (c >= np.finfo(float).tiny), c, np.nan)

    # The one-bar simple return, spelled as a price RATIO minus one so that a
    # x2**k price rescale cancels exactly (see SCALE-FREE above).
    r = np.full(c.size, np.nan)
    with np.errstate(over="ignore"):
        r[1:] = c[1:] / c[:-1] - 1.0
    r = np.where(np.isfinite(r), r, np.nan)

    # (n - length + 1, length) causal windows of returns, oldest first. The
    # window ending at bar T holds r[T-length+1 .. T], so it reads closes
    # T - length .. T.
    windows = sliding_window_view(r, length)
    bad = np.isnan(windows).any(axis=1)
    # A `bad` row's own entries could hold NaN; substitute a harmless 0.0 so
    # `median`/the comparisons below never raise or warn on a row this
    # module's output is about to blank out anyway.
    safe = np.where(bad[:, None], 0.0, windows)

    m = np.median(safe, axis=1, keepdims=True)
    older, newer = safe[:, :-1], safe[:, 1:]              # w[k] vs w[k+1]
    reversal = ((older > m) & (older > newer)) | ((older < m) & (older < newer))
    mmi = 100.0 * reversal.sum(axis=1) / (length - 1)

    out = np.full(c.size, np.nan)
    out[length - 1:] = np.where(bad, np.nan, mmi)
    result = Series(out, index=close.index)

    # Offset
    if offset != 0:
        result = result.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        result.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        method = kwargs["fill_method"]
        if method in ("ffill", "pad"):
            result = result.ffill()
        elif method in ("bfill", "backfill"):
            result = result.bfill()
        else:  # a silent bfill on a typo would be a look-ahead
            raise ValueError(f"fill_method must be ffill/pad or bfill/backfill, not {method!r}")

    # Name & Category
    result.name = f"NM_MMI_{length}"
    result.category = "statistics"

    return result


nm_mmi_250.__doc__ = \
"""Market Meanness Index of daily returns (NM_MMI)

The share of a 250-return window's own moves that fall BACK toward the
window's median rather than away from it: inside the window, for every pair
of adjacent returns (older, newer), count it as a "reversal" if the older
one sits above the median and falls toward it, or below the median and
rises toward it, then report that count as a percentage of the window's
`length - 1` pairs. A trending series keeps pushing away from its own
median (few reversals, MMI low); a choppy, mean-reverting one keeps
snapping back (many reversals, MMI high) -- the article's own calibration
point is "about 75 for random changes" on this fork's daily-return input, a
claim NOT independently re-tested here (existence, not evidence; see the
module source above and docs/NmMmi250Measured.md).

Named in a Reddit thread only (tier 4, rd:algotrading:hr30er) -- the
definition itself comes from the article, not the thread:

Source:
    Johann Christian Lotter, "The Market Meanness Index", financial-hacker.com

Calculation:
    Default Inputs:
        length=250
    r[t]    = close[t] / close[t-1] - 1
    w        = r[T-length+1 .. T], oldest first
    m        = median(w)
    for k = 0 .. length-2 (older = w[k], newer = w[k+1]):
        reversal[k] = (older > m and older > newer) or (older < m and older < newer)
    NM_MMI = 100 * count(reversal) / (length - 1)

Args:
    close (pd.Series): Series of 'close's
    length (int): Returns per window, so `length + 1` closes. At least
        `MIN_LENGTH` = 3; a smaller or missing value falls back to the
        default. Default: 250
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): 'ffill'/'pad' or 'bfill'/'backfill'

Returns:
    pd.Series: NM_MMI_{length}, a percentage on [0, 100] in steps of
        100 / (length - 1). NaN for the first `length` bars, on every window
        holding a close that is NaN, infinite, zero, negative or subnormal,
        and on a window holding a close PAIR whose ratio overflows to an
        infinite return.
"""
