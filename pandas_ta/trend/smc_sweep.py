# -*- coding: utf-8 -*-
"""Smart Money Concept Liquidity Sweep (SMC_SWEEP).

ALTPORT-2 port of ``pandas_ta_classic.momentum.smc_sweep`` from
https://github.com/xgboosted/pandas-ta-classic (MIT License, Copyright (c)
pandas-ta-classic contributors).  The upstream repository is NOT vendored here;
only the algorithm is reimplemented against this fork's helpers.

Category deviation, stated: upstream tags this `momentum`.  This fork files it
under `trend`, beside the SMC price-action family it belongs to (`bos`,
`choch`, `fvg`, `ob`, `liquidity_sweep`).  Only `Series.category` and the
`Category` bucket differ; the numbers do not.
"""
from numpy import where
from pandas import Series, concat

from pandas_ta.utils import get_offset, verify_series


def smc_sweep(open_, high, low, close, length=None, wick_mult=None, offset=None, **kwargs):
    """Indicator: Smart Money Concept Liquidity Sweep (SMC_SWEEP)"""
    # Validate Arguments
    length = int(length) if length and length > 0 else 15
    wick_mult = float(wick_mult) if wick_mult and wick_mult > 0 else 1.5
    open_ = verify_series(open_, length)
    high = verify_series(high, length)
    low = verify_series(low, length)
    close = verify_series(close, length)
    offset = get_offset(offset)

    if open_ is None or high is None or low is None or close is None: return

    # Calculate Result
    swing_low = low.rolling(window=length).min().shift(1)
    swing_high = high.rolling(window=length).max().shift(1)

    body = (close - open_).abs()
    oc = concat([open_, close], axis=1)
    lower_wick = oc.min(axis=1) - low
    upper_wick = high - oc.max(axis=1)

    bull_sweep = where(
        (low < swing_low) & (close > swing_low) & (close > open_)
        & (lower_wick > body * wick_mult), 1, 0)
    bear_sweep = where(
        (high > swing_high) & (close < swing_high) & (close < open_)
        & (upper_wick > body * wick_mult), -1, 0)

    smc_sweep = Series(bull_sweep + bear_sweep, index=close.index)

    # Offset
    if offset != 0:
        smc_sweep = smc_sweep.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        smc_sweep.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        smc_sweep.fillna(method=kwargs["fill_method"], inplace=True)

    # Name and Categorize it
    smc_sweep.name = f"SMC_SWEEP_{length}_{round(wick_mult, 4)}"
    smc_sweep.category = "trend"

    return smc_sweep


smc_sweep.__doc__ = \
"""Smart Money Concept Liquidity Sweep (SMC_SWEEP)

Price pokes through a rolling `length`-bar extreme, is rejected inside the same
bar leaving a wick longer than `wick_mult` x the body, and closes back on the
other side of the level in the opposite direction.  Nearer "a hammer at a
20-bar low" than a pool sweep.

Not a duplicate of the shipped `liquidity_sweep`, which sweeps CONFIRMED
PIVOTS from a level pool with an ATR tolerance and an explicit reclaim leg.
ALTPORT-1 measured the overlap against a chance baseline (200 per-frame
circular shifts, seed 20260910, 89 BIST daily frames): SMC_SWEEP lands within
+/-1 bar of ANY of the four `LSH_*` flags on **20.96%** of its events against a
null of **11.09 +/- 0.36%** -- **1.89x chance, z 27.4**, NOT the "79% disjoint"
an unbaselined count suggests.  The enrichment concentrates in the two SWEEP
flags (2.58x, 3.17x); the two RECLAIM flags are 1.23x / 1.13x, barely
distinguishable from chance.  The shared concept is the sweep leg.

SIGNED (+1 bull / -1 bear), and that is load-bearing.  An UNSIGNED magnitude
that is nonzero only on its own event's support correlates rho ~ 1.0000 with
any other such column -- the tied-zero trap that killed six CANDLE-1 columns.
Measured on 408,253 BIST daily bars: 6,474 events (1.586%), **2,335 +1 and
4,139 -1**.

Gate E (ALTPORT-1): max |Spearman rho| **0.161383** against `CCI`,
n = 406,562; per-frame median 0.166059, 0.0% of frames >= 0.90.  Rank
correlation against the `LSH_*` lane maxes at 0.078.  SHIP.

Sources:
    Smart Money Concept / ICT methodology.
    Ported from pandas-ta-classic (MIT),
    `pandas_ta_classic/momentum/smc_sweep.py`.

Calculation:
    Default Inputs:
        length=15, wick_mult=1.5
    swing_low  = low.rolling(length).min().shift(1)
    swing_high = high.rolling(length).max().shift(1)
    body       = |close - open|
    lower_wick = min(open, close) - low
    upper_wick = high - max(open, close)
    Bull (+1): low < swing_low  AND close > swing_low  AND close > open
               AND lower_wick > body * wick_mult
    Bear (-1): high > swing_high AND close < swing_high AND close < open
               AND upper_wick > body * wick_mult

Args:
    open_ (pd.Series): Series of 'open's
    high (pd.Series): Series of 'high's
    low (pd.Series): Series of 'low's
    close (pd.Series): Series of 'close's
    length (int): Swing high/low lookback. Default: 15
    wick_mult (float): Wick-to-body ratio multiplier. Default: 1.5
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.Series: New feature generated. 1 (bullish sweep), -1 (bearish), 0 (none).
"""
