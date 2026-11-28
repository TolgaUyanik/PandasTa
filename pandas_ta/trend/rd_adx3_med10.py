# -*- coding: utf-8 -*-
"""Rolling median of ADX(3) over 10 bars -- Reddit, tier 4 (ResearchIntel
kb/reddit.db), per issue #171: r/quant rd:quant:1gc3o70 (2024-10-25),
https://www.reddit.com/r/quant/comments/1gc3o70/ -- "Use ADX with 3, 5, 8
periods. And then create the median of each of these for past 10 and 20
data points respectively." The issue names six combinations (3 ADX
lengths x 2 median windows); this port ships exactly the one issue #171
names in its title and "What": ADX(3), median window 10.

POSTER'S WORDS (tier 4, untested by the poster), quoted above. Claimed use:
extra ML features, poster claims a big gain -- NOT independently tested
here. This port ships existence (causal, scale-free, reachable on real
data), not evidence that it helps a model.

GATE A -- the source formula, read bar-by-bar (the issue's own instruction:
"Gate A starts from the source formula, not the prototype"):

    ADX3            = adx(high, low, close, length=3)
    RD_ADX3_MED10    = ADX3.rolling(10).median()

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
adds is that one `.rolling(10).median()` call on top of an already-shipped
column.

Neither "3" nor "10" carries a zero-guard or edge case beyond pandas' own
`rolling().median()` NaN propagation (a window containing a NaN input bar
reads NaN for the median call) -- there is nothing else in the poster's
words to diverge from.

CAUSALITY. ADX3 is already causal by construction (established by
`pandas_ta.trend.adx`): its value at bar T reads only `high/low/close[.. T]`.
The rolling median at bar T then reads only `ADX3[T-9 .. T]` -- the
trailing 10-bar window ending AT T, never a future bar.
`tests/test_rd_adx3_med10.py` proves this with a future-perturbation probe
(bars before a perturbation point J stay bit-identical regardless of what
the frame's tail past J is changed to) and a look-ahead mutant
(`importlib`-read source, the median's input shifted one bar toward the
future with `.shift(-1)` before the rolling call, `exec`'d in memory --
never a hand-written copy): the real module leaks 0 bars at every swept
offset; the mutant is live (differs from the real module) and leaks at a
MAJORITY of the same offsets (measured 5 of 9) -- a median is robust to a
single extreme input, so a minority of offsets land the perturbed value on
the same side of the window's existing median and do not move it; see the
test module's own docstring for that argument.

SCALE-FREE. ADX is already bounded on [0, 100] and invariant to a positive
rescale of price -- `pandas_ta/trend/adx.py`'s own formula divides every
directional-movement term by `atr_` (itself linear in price scale), so a
joint rescale of high/low/close by a positive constant cancels exactly in
that ratio. Measured in `tests/test_rd_adx3_med10.py`: `ADX_3` itself and
`RD_ADX3_MED10` are both bit-identical under a power-of-two rescale
(x8/x64) and within a small float tolerance under a non-power-of-two one
(x10/x3.7). A rolling MEDIAN of an unchanged series is itself unchanged
(no further error enters at the median step beyond what ADX3 already
carries) -- no `/close` or similar additional division is needed, unlike a
price-level column.
"""
from pandas_ta.trend.adx import adx
from pandas_ta.utils import get_offset, verify_series


def rd_adx3_med10(high, low, close, adx_length=None, length=None, mamode=None, offset=None, **kwargs):
    """Indicator: Rolling Median of ADX(3) (RD_ADX3_MED10)"""
    # Validate Arguments
    adx_length = int(adx_length) if adx_length and adx_length > 0 else 3
    length = int(length) if length and length > 0 else 10
    mamode = mamode if isinstance(mamode, str) else "rma"
    min_periods = int(kwargs["min_periods"]) if "min_periods" in kwargs and kwargs["min_periods"] is not None else length
    min_bars = adx_length + max(length, min_periods)
    high = verify_series(high, min_bars)
    low = verify_series(low, min_bars)
    close = verify_series(close, min_bars)
    offset = get_offset(offset)

    if high is None or low is None or close is None: return

    # Calculate Result
    adx_df = adx(high=high, low=low, close=close, length=adx_length, mamode=mamode)
    if adx_df is None: return
    adx3 = adx_df[f"ADX_{adx_length}"]
    result = adx3.rolling(length, min_periods=min_periods).median()

    # Offset
    if offset != 0:
        result = result.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        result.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        result.fillna(method=kwargs["fill_method"], inplace=True)

    # Name & Category
    result.name = f"RD_ADX3_MED10_{adx_length}_{length}"
    result.category = "trend"

    return result


rd_adx3_med10.__doc__ = \
"""Rolling Median of ADX(3) (RD_ADX3_MED10)

The rolling 10-bar median of a 3-period Average Directional Index. From a
Reddit post (tier 4, untested by the poster), issue #171: "Use ADX with 3,
5, 8 periods. And then create the median of each of these for past 10 and
20 data points respectively." Claimed use: extra ML features, poster
claims a big gain -- NOT independently tested here. This port ships
existence (causal, scale-free, reachable on real data), not evidence that
it helps a model.

See the module source above for the full source citation and the Gate A
derivation. docs/RdAdx3Med10Measured.md has the measured numbers.

Sources:
    Reddit, tier 4 (ResearchIntel kb/reddit.db): rd:quant:1gc3o70
    (2024-10-25) https://www.reddit.com/r/quant/comments/1gc3o70/

Calculation:
    Default Inputs:
        adx_length=3, length=10
    ADX3            = adx(high, low, close, length=adx_length)["ADX_3"]
    RD_ADX3_MED10    = ADX3.rolling(length).median()

Args:
    high (pd.Series): Series of 'high's
    low (pd.Series): Series of 'low's
    close (pd.Series): Series of 'close's
    adx_length (int): The ADX smoothing length. Default: 3
    length (int): The rolling median window. Default: 10
    mamode (str): ADX's moving-average mode, forwarded to `adx()`. Default: "rma"
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    min_periods (int, optional): Minimum bars for the rolling median window. Default: length
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.Series: RD_ADX3_MED10_{adx_length}_{length}, bounded on [0, 100] --
        scale-free by construction (inherited from `adx()`'s own invariance
        to a positive price rescale) -- see docs/RdAdx3Med10Measured.md.
"""
