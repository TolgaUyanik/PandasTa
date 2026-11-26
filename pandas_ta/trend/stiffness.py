# -*- coding: utf-8 -*-
import numpy as np

from pandas_ta.overlap.sma import sma
from pandas_ta.statistics.stdev import stdev
from pandas_ta.utils import get_offset, verify_series

#: The three numbers PandasTa issue #259 states: "ma_length = 100,
#: std_mult = 0.2, length = 60". Module constants rather than arguments, for
#: the same reason as `pandas_ta/trend/j_kaufmanstop_dist.py`'s: the Gate E
#: ledger refuses a run taken at non-default parameters
#: (`docs/gate_e_ledger.py`), so a `length=` surface would ship parameter
#: combinations nothing can measure. The column name carries `LENGTH`, as
#: the issue's `STIFF_60` does.
MA_LENGTH = 100
STD_MULT = 0.2
LENGTH = 60

#: Bars a frame must have before the function computes at all, and
#: `MIN_BARS - 1` is the index of the first bar that can fire: the band needs
#: MA_LENGTH closes, and the count then needs LENGTH bands, so the first
#: count closes at bar `MA_LENGTH - 1 + LENGTH - 1 = 158`. Pinned by
#: `tests/test_stiffness.py::test_a_frame_shorter_than_min_bars_is_refused`.
MIN_BARS = MA_LENGTH + LENGTH - 1


def stiffness(close, offset=None, **kwargs):
    """Indicator: Katsanos Stiffness (STIFF)"""
    # Validate Arguments
    close = verify_series(close, MIN_BARS)
    offset = get_offset(offset)

    if close is None: return

    # Calculate Result
    # An infinite close is made NaN before any window sees it. ⚠ This guard
    # is a MEASURED NO-OP, and the comment says so rather than claiming a
    # load it does not carry: §G1 of `docs/StiffnessMeasured.md` plants NaN,
    # +inf and -inf at four bars of a walk, and with this line removed the
    # column is bit-equal in all 12 cells. What absorbs an infinite close is
    # pandas' rolling window (an infinite observation makes the mean and SD
    # NaN, so the band is NaN at that bar and the `where` below blanks it).
    # Kept as defence in depth against that absorption changing.
    cl = close.astype(float)
    cl = cl.where(np.isfinite(cl))

    # The band, issue #259: "MA_t = SMA(close, 100)_t; S_t = std(close,
    # 100)_t with ddof = 0". `sma` and `stdev` are imported from their own
    # modules, never from the package (CLAUDE.md, "Known breaks"). ⚠ `ddof=0`
    # is the issue's, and it is NOT `stdev`'s default (1); §A3 measures the
    # ddof=1 reading as a different column.
    ma = sma(cl, length=MA_LENGTH)
    sd = stdev(cl, length=MA_LENGTH, ddof=0)
    band = ma + STD_MULT * sd

    # "above_t = 1 if close_t > MA_t + 0.2 * S_t, else 0. Each bar is
    # compared with its own band." ⚠ STRICT `>`: a close exactly ON the band
    # is not above it. On a flat frame the band is the close itself
    # (SD 0), so the strict reading gives 0 and `>=` would give 100 -- §C2
    # measures both. A bar whose close or band is NaN is NaN, not 0, so it
    # empties its windows rather than counting as "not above".
    above = (cl > band).astype(float).where(band.notna() & cl.notna())

    # "STIFF_t = 100 * (above_{t-59} + ... + above_t) / 60, current bar
    # included." A rolling SUM of 0/1 floats is an exact integer, so the
    # issue's arithmetic is spelled in the issue's order.
    count = above.rolling(LENGTH, min_periods=LENGTH).sum()
    stiff = 100.0 * count / LENGTH

    # Offset
    if offset != 0:
        stiff = stiff.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        stiff.fillna(kwargs["fillna"], inplace=True)

    # Name and Categorize it
    stiff.name = f"STIFF_{LENGTH}"
    stiff.category = "trend"

    return stiff


stiffness.__doc__ = \
"""Katsanos Stiffness (STIFF)

The share of the last 60 closes, in percent, that closed above their own
100-bar SMA plus 0.2 of the 100-bar standard deviation.

    MA[T]    = mean(close[T-99..T])                               SMA 100
    S[T]     = std(close[T-99..T], ddof=0)
    above[T] = 1 if close[T] > MA[T] + 0.2 * S[T] else 0
    STIFF[T] = 100 * (above[T-59] + ... + above[T]) / 60

Source: Markos Katsanos, "Stiffness", Technical Analysis of Stocks &
Commodities, November 2018, as PandasTa issue #259 states it from the
ProRealCode port (https://www.prorealcode.com/prorealtime-indicators/
stiffness-indicator/) and the thinkorswim Stiffness reference, both of
which cite Katsanos. ⚠ The article itself was not readable when the issue
was written and was not read here; what Gate A checks is the issue's
formula, spelled independently and by TA-Lib. jesse (MIT) counts closes
above SMA - 0.2 * std and smooths with EMA(3); the owner chose the
upper-band, unsmoothed version, and that is the one shipped. The issue
says of the source: "existence, not evidence".

Gate A: a bar-by-bar oracle over plain Python floats (its own 100-term
mean, two-pass population variance and 60-term count, sharing no code with
the module) is BIT-EQUAL on 1,342 of 1,342 fired bars of each of nine test
frames, and so is `talib.SMA` + `talib.STDDEV(nbdev=1)` -- TA-Lib's STDDEV
is the population one -- first firing at the same bar 158 (talib 0.7.1;
`docs/StiffnessMeasured.md` §A1, §A2). The readings a reader might
substitute are other columns, though not always on every frame: SD with
ddof=1 differs on 60 bars of two of six varying frames (`coarse`, `jump`)
and on none of the other four; `>=` differs only where a close sits exactly
on its band, which is the flat frame (0 here, 100 there); jesse's lower
band differs on 943 .. 1,342 bars of each of the six (§A3).

Causal: bar T reads closes T-158 .. T and nothing earlier or later.
Truncating a 1,500-bar frame at bar 500 leaves all 842 bars from 658 on
bit-equal (§A4); a 36-offset x10 suffix-perturbation sweep catches the
module at 0 of 36 on each of six frames, and five look-ahead mutants of this
file are each caught at 5 .. 36 of 36 on each of three (§B1). ⚠ The sweep
is blind to LAGS, which read no later bar; Gate A's oracle rejects both lag
mutants on all three frames (§B2).

Scale-free by construction, and translation-free too: `close`, `MA` and
`0.2 * S` all move together under `a * close + b` with `a > 0`, so every
`above` bit is unchanged. Measured: x8/x64 bit-identical on all nine frames
at price levels 1e-6, 100, 1e6 and 1e100 (36 cells, §D1); x10/x3.7/x0.1/
x1.0000001 move 0 bars in all 36 cells (§D2); a +10 shift moves 0 bars of
all nine. What does move it is a NON-affine transform: `close**2` moves
180 .. 372 bars and `log(close)` 43 .. 489 of each of the six varying frames
(§D3), so the bit-identity is not vacuous.

Bounded to [0, 100] in steps of 100/60. Over the six varying frames' 8,052
fired bars: 1,244 at 0, 605 at 100, 6,203 strictly between (§C1). A flat
frame reads exactly 0 on every fired bar (the close sits ON its band, SD
exactly 0, and the comparison is strict); a steadily rising frame, and the
`trend` frame (drift 0.003/bar), read exactly 100 on every one (§C1, §C2).
One NaN or infinite close blanks a bounded run -- 159 bars when planted at
bar 700 -- and moves no other bar (§G1).

⚠ In-fork overlap, on synthetic frames and NOT Gate E: the nearest shipped
column is `ma_disparity`'s `MADISP_200_SMA`, per-frame median |rho| 0.8099
over the six varying frames (0.3375 .. 0.8447). Gate E on real data:
DISCLOSE_GAP, 0.8728 vs `SMA_50_200_Spread_pct` (§E).

Calculation:
    Default Inputs:
        ma_length=100, std_mult=0.2, length=60  -- module constants
    band  = sma(close, 100) + 0.2 * stdev(close, 100, ddof=0)
    above = close > band
    STIFF = 100 * sum(above, 60) / 60

Args:
    close (pd.Series): Series of 'close's
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)

Returns:
    pd.Series: STIFF_60, a percentage in [0, 100]
"""
