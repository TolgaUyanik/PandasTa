# -*- coding: utf-8 -*-
"""`t3_tv` -- the dynamic-length Tillson T3 of the TradingView `ta` library.

Source: `docs/pine/RA2vGpkA-ta.pine` (untracked; see CLAUDE.md), the
TradingView/`ta` Pine v5 library, **MPL-2.0, (c) TradingView**.
Pine names this export `t3Alt`; it is at L661-662 over the private `gd2`
at L651-652:

    L651 gd2(series float source, series float length, simple float vf) =>
    L652     float result = ema2(source, length) * (1 + vf)
    L652                    - ema2(ema2(source, length), length) * vf

    L661 export t3Alt(series float source, series float length, simple float vf = 0.7) =>
    L662     float result = gd2(gd2(gd2(source, length, vf), length, vf), length, vf)

The module ships as `t3_tv` rather than `t3alt` so the name matches the
`<name>2` / `<name>_tv` convention PINEBI-1c requires of survivors, and so
the column `T3tv_10_0.7` cannot be mistaken for `T3_10_0.7`.

THE DIFFERENCES FROM `t3`, MEASURED (docs/PineAlternatesMeasured.md)

The two are the same filter written two ways: `pandas_ta.t3` expands the
triple generalised-DEMA into the `c1*e6 + c2*e5 + c3*e4 + c4*e3` polynomial
over six chained EMAs, which is algebraically identical to
`gd(gd(gd(...)))`.  What differs:

1. WARM-UP.  `t3`'s deepest term is `e6`, six SMA-seeded `ema` calls deep.
   The arithmetic guess `6 * (length - 1)` is WRONG and was measured: each
   nested `ema` re-seeds from a window holding one finite value, so the
   stack still settles at `length - 1`.  Measured at length=10: first-stable
   index 9 vs 0, **9 bars saved**, on GRID_S and on all 40 Grid A tickers.
2. PARAMETER REACH -- TWO, not one:
   a. `t3` does `length = int(length)`; `t3_tv` takes a per-bar Series.
   b. THE VOLUME FACTOR.  `t3` validates `a = float(a) if a and a > 0 and
      a < 1 else 0.7`, so any `vf >= 1` silently becomes 0.7 -- the caller
      gets a column named `T3_10_0.7` and never learns.  Pine's `vf` is an
      unrestricted `simple float`, so `t3_tv` clamps it NOWHERE -- 0 and
      negatives pass through -- and the column name always carries the value
      actually used.  Round 1 of this module rejected anything outside
      (0, 1] back to 0.7, i.e. committed the same fault it is indicting;
      `tests/test_pinebi_1c_alternates.py` now pins `T3tv_10_0.0` and
      asserts `vf=0` equals the plain triple-EMA chain.
"""
from pandas_ta.overlap.ema2 import ema2, _length_array
from pandas_ta.utils import get_offset, verify_series


def _gd2(source, length, vf):
    """Pine `gd2` -- generalised DEMA over the dynamic-length `ema2`."""
    e1 = ema2(close=source, length=length)
    e2 = ema2(close=e1, length=length)
    return e1 * (1 + vf) - e2 * vf


def t3_tv(close, length=None, vf=None, offset=None, **kwargs):
    """Indicator: Dynamic-Length Tillson T3 (T3tv)"""
    close = verify_series(close)
    offset = get_offset(offset)
    if close is None: return

    _, token = _length_array(length, close.index, 10)
    # NO CLAMP. L661 declares `simple float vf = 0.7` and puts no bound on it,
    # so `vf=0` (which collapses gd() to a plain EMA chain) and a negative vf
    # are legal configurations and are passed through. Round 1 of this module
    # rejected anything outside (0, 1] back to 0.7 while naming the column
    # `T3tv_10_0.7` -- the exact `t3(a=1.5) -> T3_10_0.7` defect this port was
    # written to indict.
    vf = 0.7 if vf is None else float(vf)

    out = _gd2(_gd2(_gd2(close, length, vf), length, vf), length, vf)

    if offset != 0:
        out = out.shift(offset)
    if "fillna" in kwargs:
        out.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        out.fillna(method=kwargs["fill_method"], inplace=True)

    out.name = f"T3tv_{token}_{vf}"
    out.category = "overlap"
    return out


t3_tv.__doc__ = \
"""Dynamic-Length Tillson T3 (T3tv)

TradingView `ta.t3Alt()` -- the triple generalised DEMA built on the
source-seeded, per-bar-length `ema2`.  Finite from bar 0 where `t3` needs
`length - 1` bars (measured 9 at length=10), and unlike `t3` it does not
clamp the volume factor at all -- `t3` rewrites anything outside (0, 1) to
0.7 and still names the column `T3_10_0.7`.

Sources:
    TradingView `ta` library (RA2vGpkA), L651-652 and L661-662. MPL-2.0,
    (c) TradingView.

Calculation:
    Default Inputs:
        length=10, vf=0.7
    gd(x)  = EMA2(x, length) * (1 + vf) - EMA2(EMA2(x, length), length) * vf
    T3tv   = gd(gd(gd(close)))

Args:
    close (pd.Series): Series of 'close's
    length (int | float | pd.Series): It's period; a Series gives a per-bar
        length. Default: 10
    vf (float): Volume factor. NOT clamped -- L661 declares it a bare
        `simple float`, so 0 (which collapses gd() to a plain EMA chain)
        and negatives pass through and are encoded in the column name,
        unlike `t3`, which silently rewrites anything outside (0, 1) to
        0.7 while still naming the column `T3_10_0.7`. Default: 0.7
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.Series: New feature generated.
"""
