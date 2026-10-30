# -*- coding: utf-8 -*-
import numpy as np

from pandas_ta.utils import get_offset, verify_series


def roll_spread(close, length=None, offset=None, **kwargs):
    """Indicator: Roll's Implied Bid-Ask Spread (ROLL)"""
    # Validate Arguments
    length = int(length) if length and length > 0 else 20
    close = verify_series(close, length + 2)
    offset = get_offset(offset)

    if close is None: return

    # Roll (1984): successive price changes are negatively autocorrelated
    # under a pure bid-ask bounce, and the spread is recovered from that
    # autocovariance.
    dp = close.diff()
    cov = dp.rolling(length).cov(dp.shift(1))

    # The model is only real when the rolling autocovariance is negative;
    # a positive (or zero) covariance is common (per the issue) and has no
    # spread reading under Roll's model -- NaN, not 0. 0 would read as "no
    # cost here", a claim the model does not support on these bars; NaN
    # correctly marks them as unmeasured, matching how this repo already
    # masks an undefined ratio (e.g. `maxvol_adv`'s NaN where ADV <= 0).
    # How often this happens is measured in docs/LiquidityMeasured.md, not
    # asserted here.
    neg_cov = cov.where(cov < 0)  # NaN for cov >= 0, so sqrt never sees a negative argument
    dollar = 2 * np.sqrt(-neg_cov)
    # Emitted as a percent of price (the issue's own phrasing) -- the
    # dollar-spread estimate divided by the bar's own close, times 100.
    roll = dollar / close * 100

    # Offset
    if offset != 0:
        roll = roll.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        roll.fillna(kwargs["fillna"], inplace=True)

    # Name and Categorize it
    roll.name = f"ROLL_{length}"
    roll.category = "volatility"

    return roll


roll_spread.__doc__ = \
"""Roll's Implied Bid-Ask Spread (ROLL)

Roll (1984)'s classic estimator: under a pure bid-ask bounce with no
information in the trade, consecutive price CHANGES are negatively
autocorrelated by exactly the spread, so the spread is recoverable from
-cov(dp_t, dp_t-1) alone -- no quote data needed. Emitted as a percent of
the bar's own close, per the issue's "emitted as a percent of price".

Source: Richard Roll, "A Simple Implicit Measure of the Effective Bid-Ask
Spread in an Efficient Market", Journal of Finance 39(4), 1984. Cited
alongside AFML ch. 19 (which derives Corwin-Schultz against the same
backdrop) and Chan, "Algorithmic Trading" (2013), ch. 3.

Decision made explicitly (the issue's own list): the rolling covariance is
positive on a trending or information-driven run -- common, per the issue --
and the estimator is undefined there (sqrt of a negative argument). This
emits NaN on those bars, not 0: see docs/LiquidityMeasured.md for how often
it happens and why NaN was chosen over 0.

Covariance is the pandas default sample covariance (ddof=1); the issue does
not specify a divisor and this is the ordinary statistical default, not a
Pine-ism (there is no `biased=true` convention to match here).

Calculation:
    Default Inputs:
        length=20
    dp = close.diff()
    cov = ROLLING_COV(dp, dp[1], length)                    (sample, ddof=1)
    dollar = 2*SQRT(-cov) if cov < 0 else NaN
    ROLL = 100 * dollar / close

Args:
    close (pd.Series): Series of 'close's
    length (int): Rolling covariance window. Default: 20
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)

Returns:
    pd.Series: ROLL_{length}, a spread as a percent of price, or NaN where
        the autocovariance is non-negative.
"""
