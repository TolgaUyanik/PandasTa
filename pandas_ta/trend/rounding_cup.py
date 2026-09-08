# -*- coding: utf-8 -*-
import numpy as np
from pandas import DataFrame, Series

from pandas_ta.trend._patternlib import _validated_float, _validated_int
from pandas_ta.utils import get_offset, verify_series


def rounding_cup(close, length=None, handle=None, curv_min=None,
                 sym_tol=None, min_depth=None, offset=None, **kwargs):
    """Indicator: Cup and Handle / Rounding Bottom / Rounding Top (CUP)"""
    length = _validated_int(length, 40, "length")
    if length < 4:
        raise ValueError(f"length must be >= 4, got {length}")
    handle = _validated_int(handle, 10, "handle")
    curv_min = _validated_float(curv_min, 0.6, "curv_min")
    sym_tol = _validated_float(sym_tol, 0.10, "sym_tol")
    min_depth = _validated_float(min_depth, 0.05, "min_depth")
    offset = get_offset(offset)

    close = verify_series(close, length + handle + 1)
    if close is None:
        return

    c = close.to_numpy(dtype=float)
    n = len(c)

    conf_bull = np.full(n, np.nan)
    conf_bear = np.full(n, np.nan)
    depth = np.full(n, np.nan)
    curv = np.full(n, np.nan)
    age = np.full(n, np.nan)

    # The cup window is `c[T - length - handle + 1 : T - handle + 1]`, so its
    # left edge reaches index 0 exactly at `T = length + handle - 1`. That bar
    # IS computable and is NOT part of the NaN prefix -- an earlier revision
    # used `length + handle` and threw away one genuinely computable bar,
    # which the hand-derived cup fixture in `tests/test_candle1_patterns.py`
    # caught because its confirmation lands on precisely that bar.
    warm = min(n, length + handle - 1)
    for _arr in (conf_bull, conf_bear, depth, curv, age):
        _arr[warm:] = 0.0
    age[warm:] = 1.0

    # Design matrix for the quadratic, built ONCE. `xn` is the standardised
    # bar index, so the leading coefficient is already unitless in time; the
    # price side is normalised per window by its own first bar, which is what
    # makes `CUP_CURV` scale-free in price.
    x = np.arange(length, dtype=float)
    xn = (x - x.mean()) / x.std()
    X = np.vstack([xn ** 2, xn, np.ones(length)]).T
    P = np.linalg.pinv(X)

    last_conf = -1
    for T in range(warm, n):
        w = c[T - length - handle + 1:T - handle + 1]
        if w[0] == 0.0 or not np.isfinite(w).all():
            if last_conf >= 0:
                age[T] = min((T - last_conf) / (length + handle), 1.0)
            continue
        wl = w / w[0]
        y = wl - wl.mean()
        beta = P @ y
        a = beta[0]
        resid = ((X @ beta - y) ** 2).sum()
        r2 = 1 - resid / max((y ** 2).sum(), 1e-12)

        if a > 0 and r2 > curv_min:
            # ROUNDING BOTTOM / CUP: rim is the higher of the two window
            # ends, the cup floor is the window minimum, and the event is the
            # first close back above the rim.
            rim = max(w[0], w[-1])
            lo = w.min()
            sym = abs(w[0] - w[-1]) / rim
            if (rim - lo) / rim >= min_depth and sym < sym_tol and \
                    c[T] > rim and c[T - 1] <= rim:
                conf_bull[T] = 1.0
                depth[T] = (rim - lo) / rim
                curv[T] = a
                last_conf = T
        elif a < 0 and r2 > curv_min:
            # ROUNDING TOP: the mirror. Rim is the LOWER of the two ends and
            # the event is the first close back below it.
            rim = min(w[0], w[-1])
            hi = w.max()
            sym = abs(w[0] - w[-1]) / max(w[0], w[-1])
            if (hi - rim) / hi >= min_depth and sym < sym_tol and \
                    c[T] < rim and c[T - 1] >= rim:
                conf_bear[T] = 1.0
                depth[T] = (hi - rim) / hi
                curv[T] = a
                last_conf = T

        if last_conf >= 0:
            age[T] = min((T - last_conf) / (length + handle), 1.0)

    idx = close.index
    out = [Series(arr, index=idx) for arr in
           (conf_bull, conf_bear, depth, curv, age)]

    if offset != 0:
        out = [s.shift(offset) for s in out]
    if "fillna" in kwargs:
        for s in out:
            s.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        for s in out:
            s.fillna(method=kwargs["fill_method"], inplace=True)

    _props = f"_{length}_{handle}_{curv_min}_{sym_tol}_{min_depth}"
    names = ["CUP_CONF_BULL", "CUP_CONF_BEAR", "CUP_DEPTH", "CUP_CURV",
             "CUP_AGE"]
    for s, nm in zip(out, names):
        s.name = nm + _props

    df = DataFrame({s.name: s for s in out})
    df.name = f"CUP{_props}"
    df.category = "trend"
    return df


rounding_cup.__doc__ = """Cup and Handle / Rounding Bottom / Rounding Top (CUP)

The one member of this fork's chart-pattern family that is a CURVATURE
statement rather than a pivot-sequence statement, which is exactly why
`docs/CandlePatternShortlist.md` shortlisted it: `head_shoulders`,
`triple_top_bottom`, `triangle_wedge` and `dtdb` all consume the same
confirmed-pivot stream and can only ever see what that stream encodes. This
one fits a quadratic to a fixed window of closes and reads its leading
coefficient. CANDLE-0 measured its prototype among the lowest overlaps of the
whole set (max |rho| 0.0598 / 0.0597 over 112 shipped columns).

A cup is the `length` closes ending `handle` bars ago; the handle is the gap
between the cup's right rim and the break, and is not itself shape-tested. The
event is the first close back through the rim.

Columns (props suffix = `_{length}_{handle}_{curv_min}_{sym_tol}_{min_depth}`,
default `_40_10_0.6_0.1_0.05`):

`min_depth` is in that suffix because it CHANGES THE OUTPUT. An earlier
revision left it out, and the omission was not cosmetic: measured on an
800-bar seed-11 walk, `min_depth=0.05` fires `CUP_CONF_BULL` 4 times and
`min_depth=0.30` fires it 0 times, and both emitted the SAME column name.
Naming is API here -- the parent repo matches mined-strategy rules on these
strings -- so two different features under one name is a silent collision in
someone else's backtest, not a tidiness issue.

  CUP_CONF_BULL   0/1 on the bar a ROUNDING BOTTOM / cup closes back above
                  its rim. 0.0 elsewhere; NaN for the first
                  `length + handle - 1` bars.
  CUP_CONF_BEAR   0/1, the ROUNDING TOP mirror -- first close back below the
                  rim.
  CUP_DEPTH       `(rim - floor) / rim` for a cup, `(ceiling - rim) / ceiling`
                  for a top, on a confirmation bar, 0.0 elsewhere. This is
                  the "measured move as a fraction of price"; it is UNSIGNED
                  and at least `min_depth` when nonzero.
  CUP_CURV        the fitted quadratic's leading coefficient, on a
                  confirmation bar. SIGNED -- positive is a cup, negative a
                  rounding top -- and this is the one signed magnitude in the
                  family. It is not a duplicate of the flags: it says how
                  SHARP the curve is, and its sign is already implied by
                  which flag fired, so a miner reading `CURV > x` gets a
                  strictly stronger condition than `CONF_BULL == 1`. Unitless:
                  the window is normalised by its own first close and the bar
                  index is standardised, so the value is invariant to price
                  scale AND to price level.
  CUP_AGE         bars since the last confirmation divided by
                  `length + handle`, clipped to 1.0; 1.0 when nothing has
                  confirmed. NOTE the divisor differs from the pivot
                  matchers' `max_wait` -- this module has no bar budget,
                  because a rounding pattern is not carried forward: it is
                  re-tested from scratch on every bar. The window span is the
                  only natural time scale here, and using it keeps the column
                  in the same [0, 1] range as `HS_AGE` / `TRPL_AGE` /
                  `TRIW_AGE` without pretending the two are the same clock.

=== TWO COLUMNS THAT WERE BUILT, MEASURED AND REMOVED ================

`CUP_R2` (the fit's coefficient of determination) and `CUP_SYM` (rim
asymmetry) were built, taken through the full 485-column Gate E, and DELETED
on the INTERNAL overlap:

    CUP_DEPTH x CUP_R2     spearman rho = 1.0000    n = 88,747
    CUP_DEPTH x CUP_SYM    spearman rho = 0.9986    n = 88,747
    CUP_R2    x CUP_SYM    spearman rho = 0.9986    n = 88,747

measured on 50 BIST tickers / 91,197 daily bars
(`../Backtesting/scripts/analysis/measure_candle1_overlap_full.py`). All three
magnitudes are nonzero on the same ~718 bars and 0.0 on the other ~88,000, and
that shared support pins the rank correlation near 1 whatever they measure.

`CUP_CURV` SURVIVED THE SAME SUPPORT, and the contrast is the useful part:

    CUP_DEPTH x CUP_CURV   spearman rho = 0.1307    n = 88,747

because `CUP_CURV` is SIGNED -- positive on the 406 cup bars, negative on the
312 rounding-top bars -- so it splits the support into three rank blocks
instead of two and stops being a description of the support alone. That is the
measured escape route from the shared-support trap, and it is why this module
keeps two magnitudes where `head_shoulders` and `triple_top_bottom` keep one.

WHAT IS LOST: `CUP_R2` was the only quality-of-fit number, so a miner can no
longer ask for "a clean bowl" specifically; the `curv_min` threshold still
enforces a floor of 0.6 on every emitted pattern. `CUP_SYM` was the only rim
balance number, likewise floored by `sym_tol`.

WHY THERE IS NO `CUP_PEND`: the three sibling matchers carry a matched
candidate forward until it breaks, voids or times out, so "how many are live"
is a real state. This one has no candidate list -- every bar's window is fit
independently -- so a pending count would have nothing to count.

CAUSALITY: bar `T` reads `c[T - length - handle + 1 : T - handle + 1]` for the
fit and `c[T-1]`, `c[T]` for the break. Nothing after `T`. Pinned by a
future-perturbation mutant in `tests/test_candle1_patterns.py`.

GATE D and why the window normalisation is by DIVISION: `w / w[0]` is
bit-identical under an exact power-of-two rescale, because `(8a) / (8b)` and
`a / b` have the same IEEE-754 result when 8 is a power of two. Subtracting a
mean first would not have been -- and Gate D in this repo is `== 0.0`, not a
tolerance.
"""
