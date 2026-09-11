# -*- coding: utf-8 -*-
import numpy as np
from pandas import DataFrame, Series

from pandas_ta.trend._patternlib import (
    _line_at, _pivot_stream, _validated_float, _validated_int,
)
from pandas_ta.utils import get_offset, verify_series


def head_shoulders(high, low, close, left=None, right=None, tol=None,
                   max_wait=None, offset=None, **kwargs):
    """Indicator: Head and Shoulders / Inverse Head and Shoulders (HS)"""
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

    # Earliest bar at which FIVE alternating pivots could have confirmed: the
    # first confirms at `left + right`, and each further pivot needs at least
    # one more bar. This is a LOWER BOUND on the warm-up, not the typical one
    # -- on real data the fifth pivot confirms far later. It is stated as a
    # bound so the NaN prefix can never hide a bar on which the pattern was
    # genuinely computable.
    warm = min(n, left + right + 4)
    for _arr in (conf_bear, conf_bull, tgt, pend_col, age):
        _arr[warm:] = 0.0
    age[warm:] = 1.0

    pend = []
    pi = 0
    last_conf = -1

    for T in range(n):
        # Consume every pivot whose CONFIRMATION bar has arrived. `piv` is
        # sorted by confirm bar, so this prefix is exactly what a bar-T
        # observer knows.
        while pi < len(piv) and piv[pi][0] <= T:
            seq = piv[:pi + 1]
            if len(seq) >= 5:
                s = seq[-5:]
                k = [x[3] for x in s]
                p = [x[2] for x in s]
                b = [x[1] for x in s]
                # BEAR: peak - trough - PEAK - trough - peak, middle peak
                # dominant by at least tol/2 over BOTH shoulders, shoulders
                # level within tol. Neckline = the line through the two
                # troughs.
                if k == [1, -1, 1, -1, 1] and \
                        p[2] > p[0] * (1 + tol / 2) and \
                        p[2] > p[4] * (1 + tol / 2) and \
                        abs(p[0] - p[4]) / max(p[0], p[4]) <= tol:
                    pend.append({
                        "dir": -1, "x1": b[1], "y1": p[1], "x2": b[3],
                        "y2": p[3], "born": T, "head": p[2],
                        "ls": p[0], "rs": p[4],
                    })
                # BULL: the mirror.
                if k == [-1, 1, -1, 1, -1] and \
                        p[2] < p[0] * (1 - tol / 2) and \
                        p[2] < p[4] * (1 - tol / 2) and \
                        abs(p[0] - p[4]) / max(p[0], p[4]) <= tol:
                    pend.append({
                        "dir": 1, "x1": b[1], "y1": p[1], "x2": b[3],
                        "y2": p[3], "born": T, "head": p[2],
                        "ls": p[0], "rs": p[4],
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
            # measured target: project the head-to-neckline height through
            # the neckline, then publish it as an UNSIGNED fraction of the
            # break price. The target PRICE never leaves this function.
            height = abs(pt["head"] - neck)
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
    names = ["HS_CONF_BEAR", "HS_CONF_BULL", "HS_TGT_PCT", "HS_PEND",
             "HS_AGE"]
    for s, nm in zip(out, names):
        s.name = nm + _props

    df = DataFrame({s.name: s for s in out})
    df.name = f"HS{_props}"
    df.category = "trend"
    return df


head_shoulders.__doc__ = """Head and Shoulders / Inverse Head and Shoulders (HS)

A five-pivot chart-pattern shape matcher, in the family `dtdb` opened: a
confirmed-pivot stream is matched against a template, the candidate is carried
FORWARD bar by bar, and the event is written on the NECKLINE-BREAK bar and
nowhere else. Nothing is emitted at the pattern's own pivots.

Not a port. The template, tolerances and defaults are the ones CANDLE-0
measured -- `docs/CandlePatternShortlist.md` §3 and its harness
`../Backtesting/scripts/analysis/measure_chart_patterns_overlap_full.py`
(`proto_pivot_patterns`) -- reproduced here rather than re-derived, so the
shipped module fires where the document that authorised it said it would.

Columns (props suffix = `_{left}_{right}_{tol}_{max_wait}`, default
`_5_5_0.03_60`):

  HS_CONF_BEAR   0/1 on the bar a HEAD AND SHOULDERS (peak-trough-PEAK-
                 trough-peak) closes below its neckline. 0.0 elsewhere;
                 NaN for the first `left + right + 4` bars, the earliest
                 bar at which five alternating pivots could have confirmed.
  HS_CONF_BULL   0/1, the INVERSE head-and-shoulders mirror.
  HS_TGT_PCT     the measured target as a SCALE-FREE, UNSIGNED distance:
                 `|target - close| / close` on a confirmation bar, 0.0
                 elsewhere. Direction lives in the two flags -- `dtdb`
                 measured a signed magnitude beside a signed flag at
                 rho = 0.938 and reverted it.
  HS_PEND        net matched-but-unconfirmed pattern count at the close:
                 `+1` per live inverse H&S, `-1` per live H&S.
  HS_AGE         bars since the most recent confirmation, divided by
                 `max_wait` and clipped to 1.0. 1.0 when nothing has yet
                 confirmed -- so "long ago" and "never" are the same value,
                 which is deliberate: both mean "no recent pattern", and a
                 sentinel would need a scale the column does not have.

AGGREGATION on a bar where more than one pattern confirms: the flags are 0/1
and SATURATE; `TGT_PCT` takes the LARGEST value, which is order-independent.

=== TWO COLUMNS THAT WERE BUILT, MEASURED AND REMOVED ================

`docs/CandlePatternShortlist.md` §4 proposed two pattern-specific magnitudes
alongside the target, and both were built, shipped through a full 485-column
Gate E, and then DELETED on the INTERNAL overlap:

    HS_TGT_PCT x HS_HEAD_EXC   spearman rho = 1.0000   n = 90,497
    HS_TGT_PCT x HS_SYM        spearman rho = 0.9902   n = 90,497
    HS_SYM     x HS_HEAD_EXC   spearman rho = 0.9902   n = 90,497

measured on 50 BIST tickers / 91,197 daily bars
(`../Backtesting/scripts/analysis/measure_candle1_overlap_full.py`). All three
are above this repo's 0.9 revert line, and 1.0000 is not a near-miss.

THE MECHANISM, because it generalises to every module in this family and is
worth stating once. A magnitude that is nonzero on exactly its own event's
support and 0.0 everywhere else is, to a rank correlation, almost entirely a
DESCRIPTION OF THAT SUPPORT: 90,137 tied zeros against 360 nonzero values, so
the zero/nonzero split dominates and the within-support ordering barely moves
the coefficient. Two such columns on the SAME support are therefore
near-perfectly rank-correlated whatever they measure. `HS_SYM` and
`HS_HEAD_EXC` are genuinely different quantities -- one is shoulder
asymmetry, the other head dominance -- and it did not save them.

What DOES escape it, measured on the sibling module: a SIGNED magnitude.
`CUP_CURV` is positive for a cup and negative for a rounding top, and its
correlation with `CUP_DEPTH` on the identical support is 0.1307, not 1.0. So
the escape route, if these two columns are ever wanted back, is to give them
a sign or to publish them CONTINUOUSLY over the pending window rather than
only on the break bar. Both are redesigns, not fixes, and neither was
attempted here.

WHAT IS LOST: `HS_TGT_PCT` alone cannot say whether a confirmed H&S had level
shoulders or lopsided ones. The shape test still ENFORCES `|ls - rs| / max <=
tol`, so the pattern is still symmetric within 3%; what is gone is where
inside that budget it sat.

WHY THIS IS NOT A RESTATEMENT of anything shipped: measured by CANDLE-0 over
50 BIST tickers / 91,197 daily bars against 112 shipped columns, the bear
prototype's max |Spearman rho| was 0.0650 (vs `EQH_5_5`) and it co-fired with
`DTDB_CONF_BEAR` on 1 bar out of 180/140. The full 485-column Gate E is in
`docs/CandlePatternsMeasured.md`.

CAUSALITY: a pivot at bar `i` is consumed no earlier than bar `i + right`, and
a pattern's boundary is only ever evaluated at the CURRENT bar. Pinned by a
future-perturbation mutant in `tests/test_candle1_patterns.py`, not by prefix
truncation -- per `CLAUDE.md` Gate B, prefix truncation cannot see back-dating.

WHAT IS DELIBERATELY NOT EMITTED: the neckline price, the head price, the
target price, the pattern's width in points, and any raw bar index. All four
are forbidden by `docs/CandlePatternShortlist.md` §4 -- they scale with price
or with the frame, and a tree cannot compare them to anything.
"""
