# -*- coding: utf-8 -*-
import numpy as np
from pandas import Series

from pandas_ta.utils import get_offset, verify_series


def _valid_bar(high: Series, low: Series) -> Series:
    """A bar is usable if both high and low are positive and high >= low."""
    return (high > 0) & (low > 0) & (high >= low)


def _hl2(high: Series, low: Series, valid: Series) -> Series:
    """Per-bar squared log high/low range, NaN on a malformed bar so a bad
    tick does not poison the rolling sums with a -inf from log(0) or a NaN
    from log(negative). Split out so Gate A can be checked against a single
    hand-computed bar in isolation."""
    return Series(np.where(valid, np.log(high / low) ** 2, np.nan), index=high.index)


def corwin_schultz(high, low, length=None, offset=None, **kwargs):
    """Indicator: Corwin-Schultz Bid-Ask Spread Estimator (CS)"""
    # Validate Arguments
    length = int(length) if length and length > 0 else 1
    high = verify_series(high, length + 1)
    low = verify_series(low, length + 1)
    offset = get_offset(offset)

    if high is None or low is None: return

    # beta: AFML 19.1's getBeta -- the 2-bar sum of the per-bar squared log
    # HL range, averaged over `length` (length=1, AFML's own default `sl`,
    # disables the averaging).
    valid = _valid_bar(high, low)
    hl2 = _hl2(high, low, valid)
    beta = hl2.rolling(2).sum().rolling(length).mean()

    # gamma: AFML 19.1's getGamma -- the 2-bar HIGH/LOW range itself (today
    # and yesterday), squared-log. NaN unless both bars are individually
    # valid, so a bad tick does not leak a -inf into gamma even though
    # high/low.rolling(2) alone would not catch it.
    valid2 = valid.rolling(2).sum() == 2
    h2 = high.rolling(2).max()
    l2 = low.rolling(2).min()
    gamma = Series(np.where(valid2, np.log(h2 / l2) ** 2, np.nan), index=high.index)

    den = 3 - 2 * np.sqrt(2.0)
    alpha = (np.sqrt(2.0) - 1) * np.sqrt(beta) / den - np.sqrt(gamma / den)
    # AFML 19.1's getAlpha clips a negative alpha to 0 before exponentiating,
    # which is this estimator's own fix for exactly the failure the issue
    # names: BIST tick rounding (a flat or near-flat HL range on consecutive
    # bars) drives alpha, and so the raw spread, negative on many bars. Kept
    # as AFML defines it -- NOT reverted to let negatives through -- because
    # a negative "spread" has no reading as a cost FEATURE (unlike
    # `costs.py`'s cost-MODEL use of the same formula, where a negative
    # value nets against a later positive one in a backtest P&L; a feature
    # column is read bar-by-bar with no such netting). How often this clip
    # engages is measured in docs/LiquidityMeasured.md, not asserted here.
    alpha = alpha.clip(lower=0.0)
    cs = 2 * (np.exp(alpha) - 1) / (1 + np.exp(alpha))

    # Offset
    if offset != 0:
        cs = cs.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        cs.fillna(kwargs["fillna"], inplace=True)

    # Name and Categorize it
    cs.name = f"CS_{length}"
    cs.category = "volatility"

    return cs


corwin_schultz.__doc__ = \
"""Corwin-Schultz Bid-Ask Spread Estimator (CS)

Estimates the bid-ask spread, as a fraction of price, from two-day high/low
ranges alone -- no trade or quote data. Corwin & Lipson Schultz derive it from
the idea that a bar's HIGH/LOW ratio reflects both true volatility and the
spread, while a 2-bar HIGH/LOW ratio reflects the same volatility over twice
the horizon but the SAME spread (an informed trader's quote does not widen
just because the measurement window got longer) -- the two equations solve
for the spread alone.

Source: Lopez de Prado, "Advances in Financial Machine Learning" (2018),
ch. 19 "Microstructural Features", snippet 19.1 (`getBeta` / `getGamma` /
`getAlpha` / `corwinSchultz`), itself implementing Corwin & Schultz (2012),
"A Simple Way to Estimate Bid-Ask Spreads from Daily High and Low Prices",
Journal of Finance 67(2). Cross-check: the parent repo's
`backtesting_engine/costs.py:49` `corwin_schultz()`, a COST MODEL, not a
feature -- it keeps negative spreads for P&L netting; this clips them (see
below) because a feature column has no such netting to rely on.

Already scale-free: every term is a ratio of highs to lows, so an ×8/×64
price rescaling is bit-identical and an ×10/×3.7 rescaling only differs by
floating-point rounding. See docs/LiquidityMeasured.md.

Decisions made explicitly (the issue's own list):
- Negative alpha (and so the bars this would make the raw spread negative)
  is clipped to 0, matching AFML's own `getAlpha`. `length=1` is AFML's own
  default (`sl=1`, i.e. no averaging of beta).
- `length` smooths beta the way AFML's `sl` parameter does; it does not
  change gamma, which is always the raw 2-bar range.

Calculation:
    Default Inputs:
        length=1
    hl2 = LN(high / low)^2                               (NaN if high<=0, low<=0 or high<low)
    beta = SMA(SUM(hl2, 2), length)
    gamma = LN(MAX(high, 2) / MIN(low, 2))^2
    den = 3 - 2*SQRT(2)
    alpha = MAX(0, (SQRT(2)-1) * SQRT(beta) / den - SQRT(gamma / den))
    CS = 2 * (EXP(alpha) - 1) / (1 + EXP(alpha))

Args:
    high (pd.Series): Series of 'high's
    low (pd.Series): Series of 'low's
    length (int): Bars to average beta over. Default: 1
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)

Returns:
    pd.Series: CS_{length}, a spread as a fraction of price, >= 0.
"""
