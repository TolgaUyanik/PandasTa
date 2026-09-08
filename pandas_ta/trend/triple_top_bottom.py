# -*- coding: utf-8 -*-
import numpy as np
from pandas import DataFrame, Series

from pandas_ta.trend._patternlib import (
    _line_at, _pivot_stream, _validated_float, _validated_int,
)
from pandas_ta.utils import get_offset, verify_series


def triple_top_bottom(high, low, close, left=None, right=None, tol=None,
                      max_wait=None, offset=None, **kwargs):
    """Indicator: Triple Top / Triple Bottom (TRPL)"""
    left = _validated_int(left, 5, "left")
    right = _validated_int(right, 5, "right")
    tol = _validated_float(tol, 0.03, "tol")
    max_wait = _validated_int(max_wait, 60, "max_wait")
    offset = get_offset(offset)

    min_len = left + right + 1
    high = verify_series(high, min_len)
    low = verify_series(low, min_len)
    close = verify_series(close, min_len)
    if high is None or low is None or close is None:
        return

    n = len(close)
    c = close.to_numpy(dtype=float)
    piv = _pivot_stream(high, low, left, right)

    conf_bear = np.full(n, np.nan)
    conf_bull = np.full(n, np.nan)
    tgt = np.full(n, np.nan)
    pend_col = np.full(n, np.nan)
    age = np.full(n, np.nan)

    warm = min(n, left + right + 4)
    for _arr in (conf_bear, conf_bull, tgt, pend_col, age):
        _arr[warm:] = 0.0
    age[warm:] = 1.0

    pend = []
    pi = 0
    last_conf = -1

    for T in range(n):
        while pi < len(piv) and piv[pi][0] <= T:
            seq = piv[:pi + 1]
            if len(seq) >= 5:
                s = seq[-5:]
                hs = [x for x in s if x[3] == 1]
                ls = [x for x in s if x[3] == -1]
                # TRIPLE TOP: three level peaks, two intervening troughs.
                # The neckline is the line through the two troughs.
                if len(hs) == 3 and len(ls) == 2:
                    tops = [x[2] for x in hs]
                    if max(tops) / min(tops) - 1 <= tol:
                        pend.append({
                            "dir": -1, "x1": ls[0][1], "y1": ls[0][2],
                            "x2": ls[1][1], "y2": ls[1][2], "born": T,
                            "ref": max(tops),
                        })
                if len(ls) == 3 and len(hs) == 2:
                    bots = [x[2] for x in ls]
                    if max(bots) / min(bots) - 1 <= tol:
                        pend.append({
                            "dir": 1, "x1": hs[0][1], "y1": hs[0][2],
                            "x2": hs[1][1], "y2": hs[1][2], "born": T,
                            "ref": min(bots),
                        })
            pi += 1

        keep = []
        for pt in pend:
            if T - pt["born"] > max_wait:
                continue
            neck = _line_at(pt["x1"], pt["y1"], pt["x2"], pt["y2"], T)
            hit = (pt["dir"] == -1 and c[T] < neck) or \
                  (pt["dir"] == 1 and c[T] > neck)
            if not hit:
                keep.append(pt)
                continue
            height = abs(pt["ref"] - neck)
            target = neck - height if pt["dir"] == -1 else neck + height
            if pt["dir"] == -1:
                conf_bear[T] = 1.0
            else:
                conf_bull[T] = 1.0
            if c[T] != 0.0 and c[T] == c[T]:
                d = abs((target - c[T]) / c[T])
                if d > tgt[T]:
                    tgt[T] = d
            last_conf = T
        pend = keep

        if T >= warm:
            pend_col[T] = float(sum(pt["dir"] for pt in pend))
            if last_conf >= 0:
                age[T] = min((T - last_conf) / max_wait, 1.0)

    idx = close.index
    out = [Series(a, index=idx) for a in
           (conf_bear, conf_bull, tgt, pend_col, age)]

    if offset != 0:
        out = [s.shift(offset) for s in out]
    if "fillna" in kwargs:
        for s in out:
            s.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        for s in out:
            s.fillna(method=kwargs["fill_method"], inplace=True)

    _props = f"_{left}_{right}_{tol}_{max_wait}"
    names = ["TRPL_CONF_BEAR", "TRPL_CONF_BULL", "TRPL_TGT_PCT",
             "TRPL_PEND", "TRPL_AGE"]
    for s, nm in zip(out, names):
        s.name = nm + _props

    df = DataFrame({s.name: s for s in out})
    df.name = f"TRPL{_props}"
    df.category = "trend"
    return df


triple_top_bottom.__doc__ = """Triple Top / Triple Bottom (TRPL)

Three level touches of one boundary, two intervening counter-pivots, and an
event written on the bar the neckline breaks. Same family and same event shape
as `dtdb` and `head_shoulders`: match on confirmed pivots, carry the candidate
forward, emit on the break bar only.

WHY THIS IS NOT `dtdb` WITH A PARAMETER. `dtdb`'s `dbl_mode` is
`("any", "weaker")`; reading `pandas_ta/trend/dtdb.py`, `_match_high` and
`_match_low` read `zz_p[m-3:m]` -- exactly three zigzag points, two of them
same-side. There is NO three-touch option and no parameter that creates one.
Measured by CANDLE-0 over 50 BIST tickers / 91,197 daily bars: the triple-top
prototype fired 187 times and co-fired with `DTDB_CONF_BEAR` on ONE bar; at a
+/-3-bar window `dtdb` covers 0.112 of triple tops, so 89% of them are
invisible to it.

Columns (props suffix = `_{left}_{right}_{tol}_{max_wait}`, default
`_5_5_0.03_60`):

  TRPL_CONF_BEAR  0/1 on the bar a TRIPLE TOP closes below its neckline.
                  NaN for the first `left + right + 4` bars.
  TRPL_CONF_BULL  0/1, the TRIPLE BOTTOM mirror.
  TRPL_TGT_PCT    `|target - close| / close` on a confirmation bar, 0.0
                  elsewhere. UNSIGNED; direction is in the flags.
  TRPL_PEND       net matched-but-unconfirmed count: `+1` bottom, `-1` top.
  TRPL_AGE        bars since the last confirmation / `max_wait`, clipped to
                  1.0; 1.0 when nothing has confirmed.

=== A COLUMN THAT WAS BUILT, MEASURED AND REMOVED ====================

`TRPL_SPREAD` -- touch dispersion `(max touch - min touch) / max touch` -- was
built, taken through the full 485-column Gate E, and DELETED on the internal
overlap:

    TRPL_TGT_PCT x TRPL_SPREAD    spearman rho = 1.0000    n = 90,497

measured on 50 BIST tickers / 91,197 daily bars
(`../Backtesting/scripts/analysis/measure_candle1_overlap_full.py`). Both are
nonzero on exactly the same 406 bars and 0.0 on the other 90,091, and against
that support the rank correlation is 1.0000 to four places regardless of what
either column measures inside it. See `head_shoulders`'s docstring for the
mechanism and for the one escape route measured to work (a SIGNED magnitude).

=== A COLUMN THAT WAS PROPOSED AND NOT BUILT =========================

`docs/CandlePatternShortlist.md` §4 proposed `TRPL_TOUCHES` as an ordinal
touch count. It is not shipped: this matcher only ever accepts a five-pivot
window with three same-side touches, so the column would be 3.0 on every
confirmation bar and 0.0 everywhere else -- a rescaled copy of
`TRPL_CONF_BEAR + TRPL_CONF_BULL`, and a constant on its own support. Gate D
requires `0 < fires < n` for a reason; a column that cannot vary is not a
feature. Shipping it would have been a Gate E failure discovered late instead
of a design decision made early, and it is recorded here so the shortlist's
proposal is answered rather than quietly dropped.

CAUSALITY: pivots are consumed no earlier than `pivot_bar + right`; the
neckline is evaluated only at the current bar. Pinned by a future-perturbation
mutant in `tests/test_candle1_patterns.py`.
"""
