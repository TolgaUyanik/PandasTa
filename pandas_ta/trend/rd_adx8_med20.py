# -*- coding: utf-8 -*-
"""Rolling median of ADX(8) over 20 bars -- Reddit, tier 4 (ResearchIntel
kb/reddit.db), per issue #178: r/quant rd:quant:1gc3o70 (2024-10-25),
https://www.reddit.com/r/quant/comments/1gc3o70/ -- "Use ADX with 3, 5, 8
periods. And then create the median of each of these for past 10 and 20
data points respectively." The issue names six combinations (3 ADX
lengths x 2 median windows); this port ships exactly the one issue #178
names in its title and "What": ADX(8), median window 20.

POSTER'S WORDS (tier 4, untested by the poster), quoted above. Claimed use:
extra ML features, poster claims a big gain -- NOT independently tested
here. This port ships existence (causal, scale-free, reachable on real
data), not evidence that it helps a model.

GATE A -- the source formula, read bar-by-bar (the issue's own instruction:
"Gate A starts from the source formula, not the prototype"):

    ADX8            = adx(high, low, close, length=8)
    RD_ADX8_MED20    = ADX8.rolling(20).median()

`adx()` is Wilder's Average Directional Index -- this fork's own existing,
already-ported, already-tested formula, `pandas_ta/trend/adx.py` lines
22-39: true range smoothed with Wilder's RMA, directional movement masked
to its positive-only component and smoothed the same way, DX =
100*|DMP-DMN|/(DMP+DMN), ADX = RMA(DX, length). This port RE-USES that
function rather than re-deriving ADX from scratch -- `adx.py`'s own
docstring cites its source (the TradingView "DMI ADX TREND 2.0" script).
The rolling median is a plain trailing-window median, INCLUSIVE of the
current bar, identical in form to `pandas_ta.statistics.median`'s own
`close.rolling(length).median()` -- the only novel arithmetic this port
adds is that one `.rolling(20).median()` call on top of an already-shipped
column. Siblings: issue #171 shipped `rd_adx3_med10` (ADX(3), median 10)
on this fork's own already-existing pattern; this port is that same
pattern at the issue's other named length pair.

Neither "8" nor "20" carries a zero-guard beyond pandas' own
`rolling().median()` NaN propagation (a window containing a NaN input bar
reads NaN for the median call). The one edge case this port DOES diverge
on is the minimum-input-length guard: ADX's own warm-up needs
`2 * adx_length` bars before its first non-NaN value (the convention this
fork's `adxr.py` already uses), not `adx_length` bars alone -- an earlier
draft under-counted this and would have returned an all-NaN Series instead
of `None` for a handful of too-short inputs; `min_bars` below is written
against the corrected threshold, and
`tests/test_rd_adx8_med20.py::test_min_bars_boundary` pins it.

CAUSALITY. ADX8 is already causal by construction (established by
`pandas_ta.trend.adx`): its value at bar T reads only `high/low/close[.. T]`.
The rolling median at bar T then reads only `ADX8[T-19 .. T]` -- the
trailing 20-bar window ending AT T, never a future bar.
`tests/test_rd_adx8_med20.py` proves this with a future-perturbation probe
(bars before a perturbation point J stay bit-identical regardless of what
the frame's tail past J is changed to) and a look-ahead mutant
(`importlib`-read source, the median's input shifted one bar toward the
future with `.shift(-1)` before the rolling call, `exec`'d in memory --
never a hand-written copy): the real module leaks 0 bars at every swept
offset; the mutant is live (differs from the real module) and leaks at a
MAJORITY of the same offsets -- a median is robust to a single extreme
input, so a minority of offsets land the perturbed value on the same side
of the window's existing median and do not move it; see the test module's
own docstring for the measured count.

SCALE-FREE. ADX is already bounded on [0, 100] and invariant to a positive
rescale of price -- `pandas_ta/trend/adx.py`'s own formula divides every
directional-movement term by `atr_` (itself linear in price scale), so a
joint rescale of high/low/close by a positive constant cancels exactly in
that ratio. Measured in `tests/test_rd_adx8_med20.py`: `ADX_8` itself and
`RD_ADX8_MED20` are both bit-identical under a power-of-two rescale
(x8/x64) and within a small float tolerance under a non-power-of-two one
(x10/x3.7). A rolling MEDIAN of an unchanged series is itself unchanged
(no further error enters at the median step beyond what ADX8 already
carries) -- no `/close` or similar additional division is needed, unlike a
price-level column.
"""
from pandas_ta.trend.adx import adx
from pandas_ta.utils import get_offset, verify_series


def rd_adx8_med20(high, low, close, adx_length=None, length=None, mamode=None, offset=None, **kwargs):
    """Indicator: Rolling Median of ADX(8) (RD_ADX8_MED20)"""
    # Validate Arguments
    adx_length = int(adx_length) if adx_length and adx_length > 0 else 8
    length = int(length) if length and length > 0 else 20
    mamode = mamode if isinstance(mamode, str) else "rma"
    min_periods = int(kwargs["min_periods"]) if "min_periods" in kwargs and kwargs["min_periods"] is not None else length
    # ADX itself needs 2*adx_length bars before its own first non-NaN value
    # (adxr.py's own house convention, `verify_series(high, 2 * length)`) --
    # adx_length alone under-counts that warm-up and lets through an input
    # too short to ever produce a non-NaN median, returning an all-NaN
    # Series instead of None.
    min_bars = 2 * adx_length + max(length, min_periods)
    high = verify_series(high, min_bars)
    low = verify_series(low, min_bars)
    close = verify_series(close, min_bars)
    offset = get_offset(offset)

    if high is None or low is None or close is None: return

    # Calculate Result
    adx_df = adx(high=high, low=low, close=close, length=adx_length, mamode=mamode)
    if adx_df is None: return
    adx8 = adx_df[f"ADX_{adx_length}"]
    result = adx8.rolling(length, min_periods=min_periods).median()

    # Offset
    if offset != 0:
        result = result.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        result.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        result.fillna(method=kwargs["fill_method"], inplace=True)

    # Name & Category
    result.name = f"RD_ADX8_MED20_{adx_length}_{length}"
    result.category = "trend"

    return result


rd_adx8_med20.__doc__ = \
"""Rolling Median of ADX(8) (RD_ADX8_MED20)

The rolling 20-bar median of an 8-period Average Directional Index. From a
Reddit post (tier 4, untested by the poster), issue #178: "Use ADX with 3,
5, 8 periods. And then create the median of each of these for past 10 and
20 data points respectively." Claimed use: extra ML features, poster
claims a big gain -- NOT independently tested here. This port ships
existence (causal, scale-free, reachable on real data), not evidence that
it helps a model.

See the module source above for the full source citation and the Gate A
derivation. docs/RdAdx8Med20Measured.md has the measured numbers.

Sources:
    Reddit, tier 4 (ResearchIntel kb/reddit.db): rd:quant:1gc3o70
    (2024-10-25) https://www.reddit.com/r/quant/comments/1gc3o70/

Calculation:
    Default Inputs:
        adx_length=8, length=20
    ADX8            = adx(high, low, close, length=adx_length)["ADX_8"]
    RD_ADX8_MED20    = ADX8.rolling(length).median()

Args:
    high (pd.Series): Series of 'high's
    low (pd.Series): Series of 'low's
    close (pd.Series): Series of 'close's
    adx_length (int): The ADX smoothing length. Default: 8
    length (int): The rolling median window. Default: 20
    mamode (str): ADX's moving-average mode, forwarded to `adx()`. Default: "rma"
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    min_periods (int, optional): Minimum bars for the rolling median window. Default: length
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.Series: RD_ADX8_MED20_{adx_length}_{length}, bounded on [0, 100] --
        scale-free by construction (inherited from `adx()`'s own invariance
        to a positive price rescale) -- see docs/RdAdx8Med20Measured.md.
"""
