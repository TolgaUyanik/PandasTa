# -*- coding: utf-8 -*-
"""Mean absolute close location -- Reddit (tier 4, ResearchIntel
kb/reddit.db), per issue #200: r/TradingView rd:TradingView:1gofmli
(2024-11-11, https://www.reddit.com/r/TradingView/comments/1gofmli/). The
issue cites the formula and one Pine line, not a whole script, so there is no
source line number -- Gate A reads the formula from the issue's own statement
(its own instruction: "Gate A starts from the source formula, not the
prototype"), not from the screen prototype
(`docs/issues/screen/ind_screen_r9.py`'s `b3_clv_abs_14`).

POSTER'S WORDS (tier 4, untested by the poster): "float volume_strength =
ta.sma(math.abs(volume_pressure), length_sma)". Claimed use: scales the
momentum signal by how one-sided volume pressure has been -- NOT
independently tested here. This port ships existence (the column is causal,
scale-free and not constant), not evidence that it predicts anything.

GATE A -- the issue's formula, bar T the current bar:
    buy  = close[T] - low[T]
    sell = high[T] - close[T]
    vp   = (buy - sell) / (buy + sell)          (= 2 * CLV - 1)
    CLVABS = SMA_length(|vp|)                    (length = 14)
Despite the poster's "volume" naming, the formula reads no volume: buy/sell
are the close's distances from the bar's low and high. `buy + sell` is
`high - low`, so a zero-range bar (`high == low`) is 0 / 0: NaN here, `na`
in Pine.

NA RULE OF `ta.sma` (issue #200 review round 1). The Pine v5/v6 reference
for `ta.sma` says, in its Remarks: "`na` values in the `source` series are
ignored; the function calculates on the `length` quantity of non-`na`
values." UNVERIFIED in this session: the reviewer and the porter both
recalled that sentence, but the page could not be fetched here (WebFetch was
refused), so the owner should confirm it against
https://www.tradingview.com/pine-script-reference/v6/#fun_ta.sma. This port
follows that sentence: the mean is over the last `length` NON-NaN `|vp|`
values (`dropna().rolling(length).mean()`). A NaN bar (a zero-range bar, or
a missing input) therefore contributes nothing, and its output equals the
prior bar's (forward-filled back onto the original index). The window can
reach back past the NaN bars. A round-0 draft that let one flat bar blank
`length` outputs (25% of the bars on a 2%-flat synthetic frame) was a guess,
not the source's behaviour.

CAUSALITY. Bar T's output reads high/low/close at bars <= T only: the last
`length` non-NaN bars up to T (a trailing window, nothing shifted toward the
future).
`tests/test_clv_abs.py` proves this with a future-perturbation probe and a
mutant that shifts the `|vp|` write one bar earlier (`.shift(-1)`).

SCALE-FREE. `vp` is a ratio of two differences of like-for-like prices, so
a positive price rescale cancels in it: bit-identical under x8/x64 (exact
power-of-two scaling), within float rounding under x10/x3.7.
"""
from pandas_ta.utils import get_offset, verify_series


def clv_abs(high, low, close, length=None, offset=None, **kwargs):
    """Indicator: Mean Absolute Close Location (CLVABS)"""
    # Validate Arguments
    length = int(length) if length and length > 0 else 14
    high = verify_series(high, length)
    low = verify_series(low, length)
    close = verify_series(close, length)
    offset = get_offset(offset)

    if high is None or low is None or close is None:
        return

    # Calculate Result
    buy = close - low
    sell = high - close
    vp = (buy - sell) / (buy + sell)
    vp = vp.where(buy + sell != 0)  # 0/0 is NaN already; this also NaNs +-x/0 when close sits outside a zero range
    vp_abs = vp.abs()
    # ta.sma skips na: mean of the last `length` non-NaN values, carried over NaN bars
    clvabs = vp_abs.dropna().rolling(length, min_periods=length).mean()
    clvabs = clvabs.reindex(vp_abs.index).ffill()

    # Offset
    if offset != 0:
        clvabs = clvabs.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        clvabs.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        clvabs.fillna(method=kwargs["fill_method"], inplace=True)

    # Name & Category
    clvabs.name = f"CLVABS_{length}"
    clvabs.category = "candles"

    return clvabs


clv_abs.__doc__ = \
"""Mean Absolute Close Location (CLVABS)

The trailing simple mean of the absolute close location value: how far,
on average, each bar's close sat from the middle of its own range, ignoring
which side. 0 = closes at mid-range, 1 = closes at an extreme. From a Reddit
post (tier 4, untested by the poster), who calls it "volume strength" and
uses it to scale a momentum signal by how one-sided pressure has been. See
the module source above for the full source citation, Gate A derivation and
the causality/scale-free argument; docs/ClvAbsMeasured.md has the measured
numbers.

Sources:
    Reddit, tier 4 (ResearchIntel kb/reddit.db): rd:TradingView:1gofmli
    (2024-11-11) https://www.reddit.com/r/TradingView/comments/1gofmli/

Calculation:
    Default Inputs:
        length=14
    buy = close - low
    sell = high - close
    vp = (buy - sell) / (buy + sell), NaN when high == low
    CLVABS = SMA(|vp|, length) over the last length non-NaN |vp| values
             (Pine ta.sma's na-skipping rule), carried over NaN bars

Args:
    high (pd.Series): Series of 'high's
    low (pd.Series): Series of 'low's
    close (pd.Series): Series of 'close's
    length (int): The mean's period. Default: 14
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.Series: CLVABS_{length}, scale-free, in [0, 1] when
        low <= close <= high (a close outside the bar's range gives |vp| > 1).
        NaN until `length` non-NaN |vp| values have been seen.
"""
