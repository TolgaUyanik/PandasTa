# -*- coding: utf-8 -*-
from numpy import abs as npabs
from pandas_ta.volatility.atr import atr
from pandas_ta.utils import get_offset, verify_series


def ttr_snr_20(high, low, close, length=None, offset=None, **kwargs):
    """Indicator: Signal-to-Noise Ratio (TTR SNR)"""
    # Validate Arguments
    length = int(length) if length and length > 0 else 20
    high = verify_series(high, length + 1)
    low = verify_series(low, length + 1)
    close = verify_series(close, length + 1)
    offset = get_offset(offset)

    if high is None or low is None or close is None: return

    # Calculate Result
    # TTR's own ATR() default smooths with Wilder's recursion (`wilder=TRUE`
    # passed to its internal EMA); this fork's own atr() default is "rma",
    # explicitly NOT Wilder's smoothing (see atr.py's docstring). mamode=
    # "wrma" is this fork's name for Wilder's smoothing, so it is passed
    # explicitly here to match the SOURCE formula's ATR(n), not this
    # package's own ATR default.
    atr_val = atr(high=high, low=low, close=close, length=length, mamode="wrma")
    # Both the numerator (a price difference) and the denominator (built
    # from price differences) are price-scale quantities, so the ratio is
    # scale-free as written -- no extra normalization needed.
    move = npabs(close - close.shift(length))
    snr = move / atr_val

    # Offset
    if offset != 0:
        snr = snr.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        snr.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        snr.fillna(method=kwargs["fill_method"], inplace=True)

    # Name and Categorize it
    snr.name = f"TTR_SNR_{length}"
    snr.category = "volatility"

    return snr


ttr_snr_20.__doc__ = \
"""Signal-to-Noise Ratio (TTR SNR)

The size of the net `length`-bar move, in units of that window's own Average
True Range: a scale-free measure of how much of a window's volatility went
into trend rather than noise.

Source: R TTR (GPL-2.0), `SNR.R`:

    SNR <- function(HLC, n = 10, ...) {
      ATR <- ATR(HLC, n = n, ...)[, "atr"]
      Cl  <- Cl(HLC)
      SNR <- abs(Cl - lag(Cl, n)) / ATR
      ...
    }

Per CLAUDE.md ("Library code (R TTR, GPL-2.0): existence, not evidence"),
TTR is not installed, vendored or run as an oracle here -- `SNR.R`'s own
source is NOT in this worktree, and the formula above is recalled from the
issue text, not read off TTR's code. Gate A is checked against an
independent loop written from that formula text. TTR's own default `n` is
10; PandasTa issue #149 fixes `n = 20` ("TTR has no default"), hence the
module name.

Unlike most of this fork's ports, the source formula is already scale-free
as written: both the numerator (a price difference) and the denominator (an
Average True Range, itself built from price differences) carry one power of
price, so their ratio is dimensionless. No log-return or percent conversion
is needed, unlike e.g. `pfe` or `tf_median_absdiff_20`.

Calculation:
    Default Inputs:
        length=20
    ATR  = Average True Range(high, low, close, length, mamode="wrma")
           (Wilder's smoothing -- TTR's own ATR() default; NOT this
           package's own atr() default, which is "rma")
    move = ABS(close - close[length])
    SNR  = move / ATR

A window whose True Range is zero on every bar (a name frozen at its price
limit for `length` consecutive sessions from bar 0) also has a zero `move`,
since the close cannot have changed either -- this is NOT a `0 / 0` NaN,
because `true_range`'s own `non_zero_range` helper already adds a float
epsilon to a degenerate zero high-low range (existing behaviour of this
fork's `true_range`, not something this port adds), so a totally flat
series reads a clean 0.0 here, not NaN. Measured: `docs/measure_ttr_snr_20.py`.
No ternary/guard is in the source formula, so none is added in this module;
the zero-safety comes from a dependency this module already calls.

Args:
    high (pd.Series): Series of 'high's
    low (pd.Series): Series of 'low's
    close (pd.Series): Series of 'close's
    length (int): It's period. Default: 20
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.Series: TTR_SNR_{length}, non-negative. A totally flat input series
        reads exactly 0.0 after warm-up, not NaN (see the frozen-window
        note above).
"""
