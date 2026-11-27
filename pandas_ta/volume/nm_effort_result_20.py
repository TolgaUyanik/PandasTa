# -*- coding: utf-8 -*-
"""Effort vs result: relative volume over relative range (20) -- issue #185
(NM-EFFORT-RESULT-20). Named in two Reddit threads only, tier 4, evidence of
nothing: Wyckoff's "effort vs result" (volume vs price response) as
described in rd:Daytrading:1k9oyhh, and "Volume Range Events" (volume
change vs candle range change) in a round-6 thread. Neither thread states a
formula; the issue's own "What" line states the one actually shipped,
identical to the screen prototype's own formalisation
(`docs/issues/screen/ind_screen_r7.py`'s `nm_effort_result_20`):

    (V / SMA20(V)) / ((H - L) / SMA20(H - L))

GATE A. There is no second, independent "source formula" to derive this
from and no published formula to check it against -- the issue's own text
discloses that explicitly ("this prototype's formalisation: no published
formula was found"). Unlike `nm_mmi_250` (issue #184), where the issue
restated an article's own equation, here the issue's stated formula AND the
prototype's formalisation are the identical expression above; Gate A is
therefore a faithful translation of that one expression, not a derivation
from a second source. Reading the formula with `V` the bar's own volume,
`H`/`L` its own high/low, and `SMA20` this fork's standing rolling-mean
convention (a trailing window of `length` bars ENDING at and including the
current bar, the same convention `mean()` in the prototype and `SMA` in
every other port here use):

    range[t]        = H[t] - L[t]
    mean_volume[t]  = SMA(V, length)[t]           = mean(V[t-length+1 .. t])
    mean_range[t]   = SMA(range, length)[t]       = mean(range[t-length+1 .. t])
    rel_volume[t]   = V[t] / mean_volume[t]                        (inf -> NaN)
    rel_range[t]    = range[t] / mean_range[t]                     (inf -> NaN)
    NM_EFFORT_RESULT[t] = rel_volume[t] / rel_range[t]              (inf -> NaN)

Each of the three divisions is masked independently, matching the
prototype's own nested `sdiv` calls
(`sdiv(sdiv(v, mean(v, 20)), sdiv(h - l, mean(h - l, 20)))`, where
`sdiv(a, b) = (a / b).replace([inf, -inf], nan)`) rather than only the
final one -- a zero `mean_range` (a flat trailing window) blanks
`rel_range` on its own before it ever reaches the outer division.

READING. Wyckoff's own claim (not independently tested here -- existence,
not evidence, per the issue's own closing line): volume ("effort") should
move price range ("result") in proportion. `rel_volume` and `rel_range`
each read "today vs this series' own recent average" for volume and range
respectively, so their ratio reads "is today's effort over- or
under-represented relative to today's result, both against their own
20-bar baselines" -- near 1.0 when effort and result move together,
above 1.0 when volume runs ahead of the range it produced (effort without
proportional result -- Wyckoff's own "no demand" / "no supply" reading),
below 1.0 when the range outruns its volume (an outsized move on
comparatively thin participation).

CAUSALITY. `range[t]` is pointwise in `H[t]`/`L[t]`; `mean_volume[t]` and
`mean_range[t]` are trailing rolling means over `[t-length+1, t]`
(`.rolling(length, min_periods=length).mean()`, pandas' own causal
convention -- no `center=True` anywhere); `rel_volume[t]` and `rel_range[t]`
are pointwise ratios of two quantities already shown causal at `t`; the
final ratio is pointwise in those. By induction, `NM_EFFORT_RESULT[t]`
reads no bar after `t`, and no bar before `t-length+1`.
`tests/test_nm_effort_result_20.py` proves this both by future-perturbation
(every OHLCV bar from `J` onward replaced by an independent synthetic path,
bars `< J` required bit-identical with matching NaN masks, swept over many
`J` past the warm-up) and by two mutants, each `importlib`-read and `exec`'d
in memory, shown live (differs from the real module) and then caught at
every swept offset: the final write shifted `length` bars into the future
(`result.shift(-length)`), and `mean_volume` built from a FORWARD-looking
window (`.shift(-length)` appended after the trailing rolling mean, so bar
`t`'s "mean volume" actually reads `V[t+1 .. t+length]`, none of which
overlaps the trailing window the real module reads).

SCALE-FREE, on two independent axes. Let `k > 0` rescale price
(`H, L -> k*H, k*L`) and `j > 0` rescale volume (`V -> j*V`), independently
or together. `range -> k*range` (linear), so `mean_range -> k*mean_range`
and `rel_range = range/mean_range` is UNCHANGED by a price rescale and does
not involve `V` at all, so a volume rescale leaves it untouched too.
Symmetrically, `mean_volume -> j*mean_volume` and `rel_volume = V/mean_volume`
is unchanged by a volume rescale and does not involve price at all.
`NM_EFFORT_RESULT = rel_volume / rel_range` is therefore invariant under ANY
positive price rescale, ANY positive volume rescale, or both together --
algebraically exact. In float64 this cancellation is exact (bit-identical)
only when the rescale factor is a power of two (the multiply introduces no
rounding, so every scaled quantity is exactly `factor` times the original
double); a non-power-of-two factor (`x10`, `x3.7`) rounds `H*k`/`L*k`/`V*j`
independently before `range`'s own subtraction and the rolling sums run on
already-rounded inputs, so the cancellation holds only to within float64
tolerance. Measured in `docs/measure_nm_effort_result_20.py` (see
`docs/NmEffortResult20Measured.md`): price-only, volume-only, and both
together, at `x8`/`x64` (bit-identical) and `x10`/`x3.7` (tolerance).

`MIN_LENGTH = 2`: at `length = 1`, `mean_volume[t] = SMA(V, 1)[t] = V[t]`
(a 1-bar rolling mean is the identity), so `rel_volume[t] = V[t]/V[t]` is a
FORCED `1.0` on every bar where `V[t] != 0` (and `0/0 = NaN` where it is
zero) -- never anything else. The same collapse hits `rel_range` at
`length = 1` (`range[t]/range[t] `). The ratio of two forced-constant
series is itself forced to `1.0` (or `NaN`), a non-informative column; `2`
is the smallest window where `mean_volume[t]` and `mean_range[t]` read a
DIFFERENT bar (`t-1`) as well as `t`, so the ratios are no longer pinned to
one value by construction -- confirmed in
`tests/test_nm_effort_result_20.py` by a random-draw probe at each length.
"""
import numpy as np
from pandas import Series

from pandas_ta.utils import get_offset, verify_series

#: Below this, `mean_volume`/`mean_range` collapse to the identity window
#: and the whole ratio is forced to a single constant -- see the module
#: docstring's closing paragraph.
MIN_LENGTH = 2


def nm_effort_result_20(high, low, volume, length=None, offset=None, **kwargs):
    """Indicator: Effort vs Result -- relative volume over relative range (NM_EFFORT_RESULT)"""
    # Validate Arguments
    length = int(length) if length and int(length) >= MIN_LENGTH else 20
    high = verify_series(high, length)
    low = verify_series(low, length)
    volume = verify_series(volume, length)
    offset = get_offset(offset)

    if high is None or low is None or volume is None: return

    # Calculate Result
    rng = high - low
    mean_volume = volume.rolling(length, min_periods=length).mean()
    mean_range = rng.rolling(length, min_periods=length).mean()

    rel_volume = (volume / mean_volume).replace([np.inf, -np.inf], np.nan)
    rel_range = (rng / mean_range).replace([np.inf, -np.inf], np.nan)
    result = (rel_volume / rel_range).replace([np.inf, -np.inf], np.nan)

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
    result.name = f"NM_EFFORT_RESULT_{length}"
    result.category = "volume"

    return result


nm_effort_result_20.__doc__ = \
"""Effort vs Result -- relative volume over relative range (NM_EFFORT_RESULT)

Wyckoff's "effort" (volume) vs "result" (price-range response), each read
relative to its OWN trailing 20-bar average rather than in raw units:
`rel_volume = V / SMA20(V)`, `rel_range = (H-L) / SMA20(H-L)`,
`NM_EFFORT_RESULT = rel_volume / rel_range`. Near 1.0 when volume and range
move together against their own baselines; above 1.0 when volume runs
ahead of the range it produced (effort without proportional result); below
1.0 when the range outruns its own volume (an outsized move on
comparatively thin participation). Named in two Reddit threads only (tier
4) -- Wyckoff's own "effort vs result" idea and a separate "Volume Range
Events" thread -- neither states a formula; this is the issue's own stated
formalisation (also the screen prototype's), not an independently
published one. Existence, not evidence: nothing here tests Wyckoff's own
claim on real data. See the module source above and
docs/NmEffortResult20Measured.md for what was actually measured.

Source:
    Wyckoff's "effort vs result" (volume vs price response), as described
    in rd:Daytrading:1k9oyhh; "Volume Range Events" (volume change vs
    candle range change) in a round-6 Reddit thread (tier 4)

Calculation:
    Default Inputs:
        length=20
    range       = high - low
    mean_volume = SMA(volume, length)
    mean_range  = SMA(range, length)
    rel_volume  = volume / mean_volume, inf -> NaN
    rel_range   = range / mean_range, inf -> NaN
    NM_EFFORT_RESULT = rel_volume / rel_range, inf -> NaN

Args:
    high (pd.Series): Series of 'high's
    low (pd.Series): Series of 'low's
    volume (pd.Series): Series of 'volume's
    length (int): Rolling window for both SMAs, at least `MIN_LENGTH` = 2; a
        smaller or missing value falls back to the default. Default: 20
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): 'ffill'/'pad' or 'bfill'/'backfill'

Returns:
    pd.Series: NM_EFFORT_RESULT_{length}. NaN for the first `length - 1`
        bars, and on any later bar whose own `mean_volume` or `mean_range`
        is zero (a flat trailing window) or whose `rel_range` is zero (a
        doji bar inside an otherwise non-flat window) -- each such bar
        divides by zero and is masked rather than left as +-inf.
"""
