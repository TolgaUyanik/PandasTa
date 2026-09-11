# -*- coding: utf-8 -*-
"""`ema2` -- the dynamic-alpha EMA of the TradingView `ta` library.

Source: `docs/pine/RA2vGpkA-ta.pine` (untracked; see CLAUDE.md), the
TradingView/`ta` Pine v5 library, **MPL-2.0, (c) TradingView**.
`export ema2` is at L158-160 and the private `ewma` helper it rides on is
at L75-77.  Verbatim:

    L75  ewma(series float source, series float alpha) =>
    L76      float result = na
    L77      result := alpha * source + (1.0 - alpha) * nz(result[1], source)

    L158 export ema2(series float source, series float length) =>
    L159     float alpha  = 2.0 / (math.max(1.0, length) + 1.0)
    L160     float result = ewma(source, alpha)

TWO DIFFERENCES FROM `ema`, BOTH MEASURED (docs/PineAlternatesMeasured.md)

1. WARM-UP.  `pandas_ta.ema` seeds with an SMA -- it NaNs `close[:length-1]`
   and writes `mean(close[0:length])` at `length-1` -- so its first finite
   value is at index `length - 1`.  `ewma`'s `nz(result[1], source)` seeds
   with the source itself, so bar 0 is finite.  Measured on GRID_S (the
   400-bar seeded walk of `tests/test_pinebi_1c_alternates.py`) and on all
   40 Grid A tickers at length=10: first-stable index 9 vs 0, i.e.
   **9 bars saved**, identical on every ticker.

   HOW MUCH THAT IS WORTH TO THE CONSUMER TODAY: ZERO USABLE ROWS, measured.
   Receipt: `pine_alternates_warmup_materiality.csv`, emitted by
   `run_materiality()` in `../Backtesting/scripts/analysis/measure_pine_alternates.py`.
   Config, because it changes the answer: `IndicatorEngine(include_advanced
   =False).compute_all` on the cached `*_1d.parquet` with its **DatetimeIndex
   left alone**, 365 numeric columns.

     ticker     bars  range              median  p90  max   slowest column
     ACSEL.IS    753  2023-08 - 2026-08       9   88   499  HARPARK_1_5_22_500
     AKBNK.IS  5,748  2004-03 - 2026-08      13  123  2779  tom_pos

   A usable ROW is gated by the SLOWEST column, so shaving 9 bars off one
   column moves the frame's usable start by nothing.  AKBNK's ceiling is a
   CALENDAR feature (`tom_pos`, with `sessions_to_holiday`, `ramazan_day`
   and `days_to_bayram` beside it), not an indicator; drop the five calendar
   columns and the ceiling is still 623 (`MADIV_BEAR_AREA_R_20_60_120`).
   Either way it is hundreds to thousands of bars against 9.

   TWO WRONG VERSIONS OF THIS PARAGRAPH HAVE NOW SHIPPED, and the second is
   the more instructive.  Round 1 asserted materiality with no measurement.
   Round 2 measured -- but under `.reset_index(drop=True)`, which turns the
   parquet's DatetimeIndex into a RangeIndex and SILENTLY DROPS the 17
   calendar/period columns that need `.to_period()`; that run saw 348
   columns and reported p90 93/200 and a max of 1763.  Five of its six
   figures did not reproduce.  The conclusion was unharmed -- the real
   ceiling is worse -- but the numbers were not the ones claimed, which is
   why they now come from a committed CSV and name their index type.

2. PARAMETER REACH.  `pandas_ta.ema` does `length = int(length)`, so the
   length is a scalar integer for the whole series.  Here `length` may be a
   per-bar Series (Pine's `series float`), which is what `frama` and the
   adaptive filters in the same library need.  A fractional scalar is also
   reachable and is NOT truncated.

The recursion is the same filter, so Spearman rho against `EMA_10` is
~1.0 by construction.  The PINEBI-1c acceptance test is warm-up and
parameter reach, not overlap; see docs/PineAlternatesMeasured.md.
"""
import hashlib

import numpy as np
from pandas import Series

from pandas_ta.utils import get_offset, verify_series


def dynamic_ewma(source, alpha):
    """Pine `ewma(source, alpha)` -- L75-77 of RA2vGpkA-ta.pine.

    `alpha` is a per-bar array of the same length as `source`.  The filter is
    seeded with `source` itself (`nz(result[1], source)`), so the first bar is
    finite; a NaN source or alpha emits NaN and re-seeds on the next finite
    bar, which is what Pine's `na` propagation does.
    """
    src = np.asarray(source, dtype=float)
    a = np.asarray(alpha, dtype=float)
    n = src.size
    out = np.full(n, np.nan)
    prev = np.nan
    for i in range(n):
        s, ai = src[i], a[i]
        if np.isnan(s) or np.isnan(ai):
            prev = np.nan
            continue
        base = s if np.isnan(prev) else prev
        prev = ai * s + (1.0 - ai) * base
        out[i] = prev
    return out


def _scalar_token(value, as_float=False):
    """`10.0 -> 10`, `12.5 -> 12.5`: the name carries no false precision.

    `as_float=True` keeps the trailing `.0` for parameters whose SIBLING
    already spells them as floats -- `SUPERT_7_3.0`, `T3_10_0.7`.  Naming is
    API, so `supertrend2`'s multiplier must read `3.0` beside `supertrend`'s,
    not `3`.
    """
    if as_float:
        return float(value)
    return int(value) if float(value).is_integer() else float(value)


def _series_token(values, prefix="dyn", as_float=False):
    """A name token for a per-bar parameter that two different Series cannot share.

    `dyn` alone was a COLLISION: `df.ta.ema2(length=slow)` after
    `df.ta.ema2(length=fast)` produced `EMA2_dyn` twice and, with
    `append=True`, the second silently overwrote the first -- in the one call
    shape this module exists to make possible.  The token is now the observed
    range plus a deterministic digest of the float64 bytes, so it is readable
    (`dyn5-20-3f9c1b7e`) and reproducible across runs and processes
    (`blake2b` of the raw buffer, not Python's salted `hash()`).

    THE DIGEST IS 4 BYTES, NOT 2, AND THE REASON IS A BIRTHDAY BOUND.  A
    2-byte digest is 65,536 codes, which puts a 50% collision at roughly 300
    distinct per-bar Series in one frame -- and the span prefix does not save
    it in the same-span case this module's own test pins (5->20 against
    20->5).  A collision here is not a cosmetic clash: it is the silent
    `append=True` overwrite the token exists to prevent.  32 bits moves the
    50% point to ~77,000 Series.  This is still a bound, not a guarantee, and
    the docstring says bound.
    """
    finite = values[np.isfinite(values)]
    if finite.size == 0:
        span = "na"
    else:
        span = (f"{_scalar_token(finite.min(), as_float)}"
                f"-{_scalar_token(finite.max(), as_float)}")
    digest = hashlib.blake2b(np.ascontiguousarray(values, dtype=float).tobytes(),
                             digest_size=4).hexdigest()
    return f"{prefix}{span}-{digest}"


def _param_array(value, index, default, floor=None, as_float=False):
    """Normalise a scalar-or-Series parameter into an array plus a name token.

    Returns `(values, token)`.  Two rules, both of which this module got wrong
    in round 1 and both of which are exactly what it indicts `t3` for:

    * THE CLAMP IS PINE'S, NOT AN INVENTION.  `floor` is `math.max(1.0, x)`
      from L103/L159/L497 and nothing else.  Round 1 sent a non-positive
      scalar back to the DEFAULT (`ema2(close, -5)` == `length=10`) while the
      Series path clamped to 1 inside the caller -- two paths of one argument
      disagreeing, and neither matching the cited Pine line.  Parameters Pine
      does NOT clamp (`vf`, `factor`) pass `floor=None` and are passed
      through, including 0 and negatives.
    * THE NAME CARRIES THE EFFECTIVE VALUE.  `ema2(close, -5)` is `EMA2_1`,
      not `EMA2_10`.  A column named for a parameter the call did not use is
      the `T3_10_0.7`-for-`a=1.5` defect, and naming is API here.
    """
    if isinstance(value, Series):
        vals = value.reindex(index).astype(float).to_numpy()
        if floor is not None:
            vals = np.maximum(floor, vals)
        return vals, _series_token(vals, as_float=as_float)
    if value is None:
        value = default
    value = float(value)
    if floor is not None:
        value = max(float(floor), value)
    return np.full(len(index), value), _scalar_token(value, as_float)


def _length_array(length, index, default):
    """`_param_array` under Pine's `math.max(1.0, length)` floor."""
    return _param_array(length, index, default, floor=1.0)


def ema2(close, length=None, offset=None, **kwargs):
    """Indicator: Dynamic-Length Exponential Moving Average (EMA2)"""
    close = verify_series(close)
    offset = get_offset(offset)
    if close is None: return

    lengths, token = _length_array(length, close.index, 10)
    # L159 `2.0 / (math.max(1.0, length) + 1.0)`; the max() is _length_array's floor
    alpha = 2.0 / (lengths + 1.0)
    out = Series(dynamic_ewma(close, alpha), index=close.index)

    if offset != 0:
        out = out.shift(offset)
    if "fillna" in kwargs:
        out.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        out.fillna(method=kwargs["fill_method"], inplace=True)

    out.name = f"EMA2_{token}"
    out.category = "overlap"
    return out


ema2.__doc__ = \
"""Dynamic-Length Exponential Moving Average (EMA2)

TradingView `ta.ema2()` -- an EMA whose `length` may vary bar by bar and
whose recursion is seeded with the source rather than with an SMA, so it
returns a finite value on the first bar instead of `NaN` for `length - 1`
bars.  Both differences from `ema` are measured in
`docs/PineAlternatesMeasured.md`.

Sources:
    TradingView `ta` library (RA2vGpkA), L75-77 and L158-160. MPL-2.0,
    (c) TradingView.

Calculation:
    Default Inputs:
        length=10
    alpha = 2 / (max(1, length) + 1)
    EMA2[0] = close[0]
    EMA2[i] = alpha * close[i] + (1 - alpha) * EMA2[i-1]

Args:
    close (pd.Series): Series of 'close's
    length (int | float | pd.Series): It's period; a Series gives a per-bar
        length. Default: 10
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.Series: New feature generated.
"""
