# -*- coding: utf-8 -*-
"""Kaufman's price density (10) -- issue #186 (NM-PRICE-DENSITY-10). Source:
Kaufman 2013, Trading Systems and Methods, 5th ed., ch. 1 "Other
Measurements of Noise" (ResearchIntel book chunk); named, undefined, in two
Reddit threads (tier 4): rd:algotrading:15xt5xt, rd:algotrading:1nrkjby. The
chapter's own formula, restated in the issue's "What" line:

    sum_n(High_i - Low_i) / (max_n(High) - min_n(Low)), n = 10 (Kaufman's own example period)

GATE A. There is no second source to cross-check against -- the issue
names exactly one (Kaufman 2013), and the screen prototype's own
formalisation (`docs/issues/screen/ind_screen_r7.py`'s `nm_price_density_10`:
`sdiv((h - l).rolling(10).sum(), tsmax(h, 10) - tsmin(l, 10))`) is a direct
transcription of that same chapter formula, not a second, independent
reading. Reading the formula with `H`/`L` each bar's own high/low and a
trailing window of `length` bars ENDING at and including the current bar
(this fork's standing rolling convention, matching every other port here):

    range[t]       = H[t] - L[t]
    numerator[t]   = SUM(range, length)[t]  = sum(range[t-length+1 .. t])
    hh[t]          = MAX(H, length)[t]      = max(H[t-length+1 .. t])
    ll[t]          = MIN(L, length)[t]      = min(L[t-length+1 .. t])
    denominator[t] = hh[t] - ll[t]
    NM_PRICE_DENSITY[t] = numerator[t] / denominator[t]         (inf -> NaN)

The single division is masked the same way the prototype's `sdiv` masks it
(`sdiv(a, b) = (a / b).replace([inf, -inf], nan)`). On OHLC-CONSISTENT
input (`H[t] >= L[t]` on every bar -- NOT validated by this function, the
same unstated precondition `har_park`/`corwin_schultz` rely on),
`denominator[t] == 0` forces `numerator[t] == 0` too (see READING below),
so the masked case is always `0/0`, never a genuine `nonzero/0`. On a
malformed bar (`L[t] > H[t]` somewhere in the window) this no longer
holds -- `numerator` can be negative while `denominator` is still 0 (e.g.
`H=[5,2]`, `L=[5,8]`, `length=2`: `numerator=-6`, `denominator=0`) -- but
the result is still masked, because that case divides to `-inf`, which
`.replace([inf, -inf], nan)` catches the same as `+inf`.

READING. Kaufman's own claim (not independently tested here -- existence,
not evidence, per the issue's own closing line): price density reads how
much of a window's total high-low range comes from "wasted motion" --
individual bars retracing over ground the window's own net high-low span
already covers -- versus net directional progress. A value of 1.0 is the
tightest possible reading: every bar's own range stacks edge-to-edge inside
the window's own high-low span with no overlap at all (e.g. a single bar,
or a strictly one-directional walk where each bar's range is disjoint from
every other bar's). Values above 1.0 mean the bars overlapped (chop:
up-down-up motion re-covering the same price band); Kaufman reads higher
values as noisier. Unlike a ratio of two same-direction sums, this one is
NOT bounded below by 1.0: a window spanning a gap (one bar's range fully
disjoint from the window's low-volatility remainder) can push
`numerator[t] < denominator[t]`, because `denominator` is anchored to the
window's extreme HIGH and extreme LOW regardless of which bars set them or
how far apart those two bars sit -- measured counterexample constructed by
hand: `H = [5, 1]`, `L = [4, 1]` gives `numerator = 1 + 0 = 1`,
`denominator = 5 - 1 = 4`, ratio `0.25`.

CAUSALITY. `range[t]` is pointwise in `H[t]`/`L[t]`; `numerator[t]`,
`hh[t]` and `ll[t]` are each trailing rolling reductions over
`[t-length+1, t]` (`.rolling(length, min_periods=length)`, no
`center=True` anywhere); the final ratio is pointwise in those three. By
induction, `NM_PRICE_DENSITY[t]` reads no bar after `t`, and no bar before
`t-length+1`. `tests/test_nm_price_density_10.py` proves this both by
future-perturbation (every H/L bar from `J` onward replaced by an
independent synthetic path, bars `< J` required bit-identical with
matching NaN masks, swept over many `J` past the warm-up) and by two
mutants, each `importlib`-read and `exec`'d in memory, shown live (differs
from the real module) and then caught at every swept offset: the final
write shifted `length` bars into the future (`result.shift(-length)`), and
`hh` built from a FORWARD-looking window (`.shift(-length)` appended after
the trailing rolling max, so bar `t`'s "window high" actually reads
`H[t+1 .. t+length]`, none of which overlaps the trailing window the real
module reads).

SCALE-FREE. Let `k > 0` rescale price (`H, L -> k*H, k*L`). `range -> k*range`
(linear), so `numerator -> k*numerator`; `hh -> k*hh` and `ll -> k*ll`
(a positive scalar multiply preserves argmax/argmin), so
`denominator -> k*denominator`. `NM_PRICE_DENSITY = numerator / denominator`
is therefore invariant under ANY positive price rescale -- algebraically
exact. In float64 this cancellation is exact (bit-identical) only when `k`
is a power of two (the multiply introduces no rounding, so every scaled
quantity is exactly `k` times the original double); a non-power-of-two
factor (`x10`, `x3.7`) rounds `H*k`/`L*k` independently before `range`'s
own subtraction and the rolling reductions run on already-rounded inputs,
so the cancellation holds only to within float64 tolerance. Measured in
`docs/measure_nm_price_density_10.py` (see
`docs/NmPriceDensity10Measured.md`): `x8`/`x64` (bit-identical) and
`x10`/`x3.7` (tolerance).

`MIN_LENGTH = 2`: at `length = 1`, `numerator[t] = SUM(range, 1)[t] =
range[t]` and `hh[t] - ll[t] = H[t] - L[t] = range[t]` (a 1-bar rolling
max/min/sum is each the identity), so the ratio is FORCED to
`range[t] / range[t]`: `1.0` on every bar where `range[t] != 0`, and
`0/0 = NaN` where it is zero -- never anything else. `2` is the smallest
window where `hh[t]`/`ll[t]` can read a DIFFERENT bar than the one setting
`numerator[t]`'s own two addends, so the ratio is no longer pinned to one
value by construction -- confirmed in `tests/test_nm_price_density_10.py`
by a random-draw probe at each length.
"""
import numpy as np

from pandas_ta.utils import get_offset, verify_series

#: Below this, `numerator`/`denominator` collapse to the identity window
#: and the ratio is forced to a single constant -- see the module
#: docstring's closing paragraph.
MIN_LENGTH = 2


def nm_price_density_10(high, low, length=None, offset=None, **kwargs):
    """Indicator: Kaufman's Price Density (NM_PRICE_DENSITY)"""
    # Validate Arguments
    length = int(length) if length and int(length) >= MIN_LENGTH else 10
    high = verify_series(high, length)
    low = verify_series(low, length)
    offset = get_offset(offset)

    if high is None or low is None: return

    # Calculate Result
    rng = high - low
    numerator = rng.rolling(length, min_periods=length).sum()
    hh = high.rolling(length, min_periods=length).max()
    ll = low.rolling(length, min_periods=length).min()
    denominator = hh - ll

    result = (numerator / denominator).replace([np.inf, -np.inf], np.nan)

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
    result.name = f"NM_PRICE_DENSITY_{length}"
    result.category = "volatility"

    return result


nm_price_density_10.__doc__ = \
"""Kaufman's Price Density (NM_PRICE_DENSITY)

The sum of each bar's own high-low range over a trailing window, divided by
that same window's own high-low span (its highest high minus its lowest
low): `NM_PRICE_DENSITY = SUM(H-L, length) / (MAX(H, length) - MIN(L, length))`.
A value of 1.0 is the tightest possible reading (no bar's range overlaps
another's inside the window's own span); values above 1.0 mean bars
retraced over ground the window already covered (Kaufman reads this as
noise). Named, undefined, in two Reddit threads only (tier 4) --
rd:algotrading:15xt5xt and rd:algotrading:1nrkjby -- neither states a
formula; this is Kaufman's own published chapter formula (2013, ch. 1,
"Other Measurements of Noise"), not an independently derived one.
Existence, not evidence: nothing here tests Kaufman's own claim on real
data. See the module source above and docs/NmPriceDensity10Measured.md for
what was actually measured.

Source:
    Kaufman, Perry J. (2013). Trading Systems and Methods, 5th ed., ch. 1
    "Other Measurements of Noise". Named in rd:algotrading:15xt5xt,
    rd:algotrading:1nrkjby (Reddit, tier 4).

Calculation:
    Default Inputs:
        length=10
    range       = high - low
    numerator   = SUM(range, length)
    hh          = MAX(high, length)
    ll          = MIN(low, length)
    NM_PRICE_DENSITY = numerator / (hh - ll), inf -> NaN

Args:
    high (pd.Series): Series of 'high's
    low (pd.Series): Series of 'low's
    length (int): Rolling window, at least `MIN_LENGTH` = 2; a smaller or
        missing value falls back to the default. Default: 10
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): 'ffill'/'pad' or 'bfill'/'backfill'

Returns:
    pd.Series: NM_PRICE_DENSITY_{length}. NaN for the first `length - 1`
        bars, and on any later bar whose window high equals its window low
        (every H and L identical across the whole window) -- that bar
        divides by zero and is masked rather than left as +-inf. Not
        bounded below by 1.0 in general: a window spanning a price gap can
        read below 1.0 (see READING in the module docstring).
"""
