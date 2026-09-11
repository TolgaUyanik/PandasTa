# -*- coding: utf-8 -*-
import numpy as np
from pandas import DataFrame, Series

from pandas_ta.trend._patternlib import (
    _line_at, _pivot_stream, _validated_int,
)
from pandas_ta.utils import get_offset, verify_series

#: A boundary whose per-bar slope, as a fraction of its own level, is under
#: this in absolute value counts as FLAT. CANDLE-0's probe used 0.0015 and
#: every fire rate in `docs/CandlePatternShortlist.md` §3 is at that value; it
#: is a module constant rather than a parameter so the shipped column names
#: cannot drift away from the measured ones.
_FLAT = 0.0015

#: Converging = the later boundary separation is under this fraction of the
#: earlier one. Also CANDLE-0's value.
_CONV = 0.8

#: A rectangle needs a body: two flat boundaries at least this far apart, as a
#: fraction of the upper boundary. CANDLE-0's value.
_RECT_MIN_WIDTH = 0.02


def _scan(high, low, close, left, right, max_wait, include_rect=False):
    """The whole matcher, once.

    Returns a dict of per-bar arrays. `triangle_wedge` publishes a SUBSET of
    them; `rect_up` / `rect_dn` are NOT shipped and exist so the measurement
    harness can ask which confirmations came from the RECTANGLE branch of the
    shape test.

    `include_rect` DEFAULTS TO FALSE, which is the shipped behaviour: the
    rectangle branch is REJECTED, so `rect_up` / `rect_dn` come back all-zero
    and no rectangle ever reaches a column. See the RECTANGLE section of this
    module's docstring for the pre-registered trigger that decided it.
    `include_rect=True` restores the branch and exists for exactly one caller,
    `measure_candle1_overlap_full.py`, so the measurement that FIRED the
    trigger stays reproducible after the trigger has been honoured. Honouring
    a decision must not delete its evidence.

    WHY THAT IS NOT A LUXURY. Round 1 of `docs/CandlePatternsMeasured.md` §6
    counted rectangles from the shipped columns, with the proxy mask
    `TRIW_CONF_* == 1 AND |TRIW_SLOPE_UP| < _FLAT AND |TRIW_SLOPE_DN| < _FLAT`.
    That mask is neither necessary nor sufficient, because `slope_up` /
    `slope_dn` are aggregated by max-|value| ACROSS EVERY pattern confirming on
    the bar: a genuine rectangle co-confirming with a steeper triangle is
    erased (false negative), and a converging pattern whose two per-bar slopes
    both happen to sit under `_FLAT` but which never passed `w1 >
    _RECT_MIN_WIDTH` is counted (false positive). The pre-registered rectangle
    decision rests on that population, so it has to be the real one. Extracting
    the loop, rather than re-implementing it in the harness, is what keeps the
    measured population and the shipped behaviour the same code.
    """
    n = len(close)
    c = close.to_numpy(dtype=float)
    piv = _pivot_stream(high, low, left, right)

    conf_bear = np.full(n, np.nan)
    conf_bull = np.full(n, np.nan)
    slope_up = np.full(n, np.nan)
    slope_dn = np.full(n, np.nan)
    width_c = np.full(n, np.nan)
    pend_col = np.full(n, np.nan)
    age = np.full(n, np.nan)
    rect_up = np.zeros(n)
    rect_dn = np.zeros(n)
    conv_c = np.zeros(n)

    warm = min(n, left + right + 3)
    for _arr in (conf_bear, conf_bull, slope_up, slope_dn, width_c,
                 pend_col, age):
        _arr[warm:] = 0.0
    age[warm:] = 1.0

    pend = []
    pi = 0
    last_conf = -1

    for T in range(n):
        while pi < len(piv) and piv[pi][0] <= T:
            seq = piv[:pi + 1]
            if len(seq) >= 4:
                s = seq[-4:]
                hs = [x for x in s if x[3] == 1]
                ls = [x for x in s if x[3] == -1]
                if len(hs) == 2 and len(ls) == 2:
                    hx1, hy1 = hs[0][1], hs[0][2]
                    hx2, hy2 = hs[1][1], hs[1][2]
                    lx1, ly1 = ls[0][1], ls[0][2]
                    lx2, ly2 = ls[1][1], ls[1][2]
                    if hx2 > hx1 and lx2 > lx1:
                        sh = (hy2 - hy1) / (hx2 - hx1) / max(hy1, 1e-9)
                        sl = (ly2 - ly1) / (lx2 - lx1) / max(ly1, 1e-9)
                        w1 = abs(hy1 - ly1) / max(hy1, 1e-9)
                        w2 = abs(hy2 - ly2) / max(hy2, 1e-9)
                        conv = w2 < w1 * _CONV
                        flat_h = abs(sh) < _FLAT
                        flat_l = abs(sl) < _FLAT
                        # The RECTANGLE branch of the shape test, named once
                        # so it can be both the acceptance rule and the thing
                        # the harness counts.
                        rect = flat_h and flat_l and w1 > _RECT_MIN_WIDTH
                        # Accept every CONVERGING shape (descending /
                        # ascending / symmetrical triangle, rising / falling
                        # wedge) plus the flat-flat RECTANGLE. Diverging
                        # boundaries -- broadening / megaphone -- are NOT
                        # accepted: CANDLE-0 measured that prototype at a
                        # 2.30% fire rate, ~3x the next-loosest shape, and
                        # DEFERRED it. Adding it here would ship the one
                        # candidate the shortlist declined.
                        ok = conv or rect
                        if rect and not include_rect:
                            # THE PRE-REGISTERED SKIP, and it rejects the
                            # pattern OUTRIGHT rather than falling back on the
                            # `conv` branch: a shape that is both converging
                            # and flat-flat is still a rectangle, and
                            # "skip the rectangle" has to mean the module
                            # emits none. Measured cost, 250 BIST tickers /
                            # 343,638 bars: 811 of 6,951 bull confirmations
                            # (11.7%) and 756 of 6,386 bear (11.8%) go away.
                            ok = False
                        if ok and w1 > 0:
                            pend.append({
                                "x1": hx1, "y1": hy1, "x2": hx2, "y2": hy2,
                                "lx1": lx1, "ly1": ly1, "lx2": lx2, "ly2": ly2,
                                "born": T, "sh": sh, "sl": sl, "rect": rect,
                                "conv": (w2 - w1) / w1,
                            })
            pi += 1

        keep = []
        for pt in pend:
            if T - pt["born"] > max_wait:
                continue
            up = _line_at(pt["x1"], pt["y1"], pt["x2"], pt["y2"], T)
            dn = _line_at(pt["lx1"], pt["ly1"], pt["lx2"], pt["ly2"], T)
            if c[T] > up:
                brk = 1
            elif c[T] < dn:
                brk = -1
            else:
                keep.append(pt)
                continue
            if brk == 1:
                conf_bull[T] = 1.0
                if pt["rect"]:
                    rect_up[T] = 1.0
            else:
                conf_bear[T] = 1.0
                if pt["rect"]:
                    rect_dn[T] = 1.0
            # measured move = the boundary separation AT THE BREAK BAR, as a
            # fraction of the break price. `abs` because a converging pair
            # can cross past its apex while the pattern is still inside its
            # bar budget; the separation is then negative and its MAGNITUDE
            # is still the honest measure of how far apart the lines were.
            w = abs(up - dn) / c[T] if c[T] else 0.0
            if w > width_c[T]:
                width_c[T] = w
            # These three keep the sign of the pattern that produced the
            # LARGEST |value| on the bar, so a shape is never averaged with a
            # different shape. Ties keep the first. NOTE this aggregation is
            # exactly why `rect_up` / `rect_dn` above are recorded here rather
            # than inferred later from the published slopes.
            if abs(pt["sh"]) > abs(slope_up[T]):
                slope_up[T] = pt["sh"]
            if abs(pt["sl"]) > abs(slope_dn[T]):
                slope_dn[T] = pt["sl"]
            # NOT SHIPPED -- `TRIW_CONV` was built, cleared Gate E and was
            # deleted on an internal rho of -0.8928 against `TRIW_WIDTH`. It is
            # still computed here so the harness can re-derive that number on
            # the SAME population the surviving columns are measured on. An
            # earlier revision recomputed it from a duplicated loop in the
            # harness that still accepted rectangles, while `TRIW_WIDTH` no
            # longer did, and the mismatch alone moved the pair from -0.8928
            # to -0.9415.
            if abs(pt["conv"]) > abs(conv_c[T]):
                conv_c[T] = pt["conv"]
            last_conf = T
        pend = keep

        if T >= warm:
            pend_col[T] = float(len(pend))
            if last_conf >= 0:
                age[T] = min((T - last_conf) / max_wait, 1.0)

    return {"conf_bear": conf_bear, "conf_bull": conf_bull,
            "slope_up": slope_up, "slope_dn": slope_dn, "width": width_c,
            "pend": pend_col, "age": age,
            "rect_up": rect_up, "rect_dn": rect_dn, "conv": conv_c}


def triangle_wedge(high, low, close, left=None, right=None, max_wait=None,
                   offset=None, **kwargs):
    """Indicator: Triangle / Wedge boundary break (TRIW)"""
    left = _validated_int(left, 5, "left")
    right = _validated_int(right, 5, "right")
    max_wait = _validated_int(max_wait, 60, "max_wait")
    offset = get_offset(offset)

    min_len = left + right + 1
    high = verify_series(high, min_len)
    low = verify_series(low, min_len)
    close = verify_series(close, min_len)
    if high is None or low is None or close is None:
        return

    r = _scan(high, low, close, left, right, max_wait)
    conf_bear, conf_bull = r["conf_bear"], r["conf_bull"]
    slope_up, slope_dn = r["slope_up"], r["slope_dn"]
    width_c, pend_col, age = r["width"], r["pend"], r["age"]

    idx = close.index
    out = [Series(a, index=idx) for a in
           (conf_bear, conf_bull, slope_up, slope_dn, width_c,
            pend_col, age)]

    if offset != 0:
        out = [s.shift(offset) for s in out]
    if "fillna" in kwargs:
        for s in out:
            s.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        for s in out:
            s.fillna(method=kwargs["fill_method"], inplace=True)

    _props = f"_{left}_{right}_{max_wait}"
    names = ["TRIW_CONF_BEAR", "TRIW_CONF_BULL", "TRIW_SLOPE_UP",
             "TRIW_SLOPE_DN", "TRIW_WIDTH", "TRIW_PEND", "TRIW_AGE"]
    for s, nm in zip(out, names):
        s.name = nm + _props

    df = DataFrame({s.name: s for s in out})
    df.name = f"TRIW{_props}"
    df.category = "trend"
    return df


triangle_wedge.__doc__ = """Triangle / Wedge boundary break (TRIW)

FOUR named chart patterns in ONE module, deliberately, and this is the design
decision most worth understanding before reading the columns.

Ascending triangle, descending triangle, symmetrical triangle, rising wedge and
falling wedge differ only in the SIGNS of two boundary slopes.

=== THE RECTANGLE IS NOT MATCHED, ON A PRE-REGISTERED TRIGGER ========

`docs/CandlePatternShortlist.md` §5 item 5 wrote the trigger BEFORE this module
existed: *"if the real module's +/-3-bar recall against `LCB_BREAKOUT_*` stays
at or above ~0.69 at production parameters, rectangle becomes SKIP -- covered,
whatever rho says."* Measured on 250 BIST tickers / 343,638 daily bars, with
the rectangle population read out of `_scan` itself rather than reconstructed
from the published columns:

    RECT_UP vs LCB_BREAKOUT_UP_5   811 events   recall 0.7102 +/- 0.0159
    RECT_DN vs LCB_BREAKOUT_DN_5   756 events   recall 0.6958 +/- 0.0167

Both are above 0.69 on the point estimate, and 0.69 sits BELOW the 1-SE band in
both directions. The trigger fires on the literal reading and on the noise-aware
one, so the rectangle branch is rejected and this module emits none.

Round 1 of `docs/CandlePatternsMeasured.md` reported 0.6869 / 0.6881 on 50
tickers and shipped the rectangle. Both errors pushed the same way: the sample
was small (SE ~0.033, so 0.69 was inside the band and the answer was undecided),
and the population was wrong -- it used the proxy mask
`TRIW_CONF_* == 1 AND |SLOPE_UP| < _FLAT AND |SLOPE_DN| < _FLAT`, which erases
a rectangle that co-confirms with a steeper triangle, and those crowded bars are
exactly where an LCB breakout is most likely.

MEASURED COST of honouring it, 250 tickers / 343,638 bars: 811 of 6,951 bull
confirmations (11.7%) and 756 of 6,386 bear (11.8%) are no longer emitted.

`_scan(..., include_rect=True)` restores the branch for the harness alone, so
the evidence survives the decision.

=== NO ONE-HOT SHAPE FLAGS ===========================================

`docs/CandlePatternShortlist.md` §4 records the call: ship the MEASUREMENTS --
the two boundary slopes and the width -- and let the miner derive the taxonomy,
rather than ship one-hot flags that are a deterministic function of three
numbers and would each restate them. Ascending / descending / symmetrical /
rising-wedge / falling-wedge is the sign pair of `TRIW_SLOPE_UP` and
`TRIW_SLOPE_DN`, which a tree reaches in two splits.

⚠ AND THAT DERIVATION IS AN APPROXIMATION, which is worth knowing because a
worse version of it cost this module a round. `TRIW_SLOPE_UP` / `TRIW_SLOPE_DN`
are aggregated by max-|value| across EVERY pattern confirming on the bar, so on
a bar carrying two patterns the published slope pair describes whichever one
was steeper -- not necessarily the one whose width or flag a reader is looking
at. `tests/test_candle1_patterns.py`'s descending-triangle fixture pins exactly
that: `SLOPE_UP` comes from one pattern and `WIDTH` from another on bar 29.
Round 1 built the rectangle count on a slope-derived mask and measured the
wrong population; anything that needs the EXACT shape of a specific pattern has
to read `_scan`, not the columns.

Columns (props suffix = `_{left}_{right}_{max_wait}`, default `_5_5_60`):

=== A PARAMETER THAT WAS ADVERTISED AND DID NOTHING ==================

An earlier revision of this module took a `tol` argument and put it in the
column name, "for signature and suffix parity with the sibling matchers". It
was never read: `tol=0.03` and `tol=0.99` produced BIT-IDENTICAL output under
two different column names. Naming is API in this fork -- the parent repo
matches mined rules on these strings -- so a name that varies while the values
do not is a false promise, and the fix was to delete the parameter rather than
to invent work for it. The boundaries here are FITTED LINES, not level touches,
so there is genuinely no tolerance to spend; `_FLAT`, `_CONV` and
`_RECT_MIN_WIDTH` above are the shape thresholds and they are module constants
on purpose, so the shipped names cannot drift away from the measured ones.

  TRIW_CONF_BEAR  0/1 on the bar price closes BELOW the lower boundary of a
                  live triangle or wedge -- NOT a rectangle, which this
                  module does not match at all (see THE RECTANGLE IS NOT
                  MATCHED above). NaN for the first
                  `left + right + 3` bars -- the earliest bar at which four
                  alternating pivots could have confirmed.
  TRIW_CONF_BULL  0/1, the upper-boundary break.
  TRIW_SLOPE_UP   upper boundary's per-bar slope as a fraction of its own
                  level, on a confirmation bar, 0.0 elsewhere. Scale-free by
                  construction: a price and its 8x copy give the same number.
  TRIW_SLOPE_DN   the same for the lower boundary.
  TRIW_WIDTH      boundary separation at the break bar, divided by the break
                  price. This is the "measured move as a fraction of price"
                  the task asks for; it is UNSIGNED, direction being in the
                  two flags.
  TRIW_PEND       count of matched-but-unbroken patterns at the close. This
                  one is UNSIGNED, unlike `HS_PEND` / `TRPL_PEND`: a pending
                  triangle has no direction until it breaks, so there is no
                  sign to carry, and inventing one would misrepresent the
                  state.
  TRIW_AGE        bars since the last confirmation / `max_wait`, clipped to
                  1.0; 1.0 when nothing has confirmed.

AMBIGUOUS ZERO, disclosed rather than engineered away: `TRIW_SLOPE_UP` and
`TRIW_SLOPE_DN` are 0.0 both on a non-confirmation bar and
on a confirmation bar whose boundary is exactly horizontal. The second case is
what a perfect rectangle looks like. Reading them WITH a `CONF` flag removes
the ambiguity; reading them alone does not. The alternative -- NaN off-event --
was rejected because it makes the columns unusable to a tree that cannot split
on NaN, which is the same reason `dtdb` writes 0.0 off-event.

=== A COLUMN THAT WAS BUILT, MEASURED AND REMOVED ====================

`TRIW_CONV` -- the convergence rate
`(width_at_second_pivot_pair - width_at_first) / width_at_first` -- was built,
taken through the full 485-column Gate E (max |rho| 0.1071 vs `CHOP`, a clear
SHIP), and then DELETED on the INTERNAL overlap:

    TRIW_CONV x TRIW_WIDTH    spearman rho = -0.8928    n = 90,547

measured on 50 BIST tickers / 91,197 daily bars
(`../Backtesting/scripts/analysis/measure_candle1_overlap_full.py`). This
repo's bands are "0.76-0.80 ship with disclosure, rho ~ 0.9 revert"; 0.8928 is
~0.9, and it was treated as a revert rather than argued into the disclosure
band.

WHICH ONE WENT, and why that is not arbitrary: `TRIW_WIDTH` is the measured
move as a fraction of price, which CANDLE-1's brief requires every pattern to
emit. `TRIW_CONV`'s job was to say whether the boundaries were converging --
but this matcher REJECTS diverging shapes outright (see below), so every
non-rectangle pattern it emits is converging BY CONSTRUCTION, and the two
slope columns already separate rectangle from triangle from wedge. `CONV`
was carrying almost no taxonomy the survivors do not carry.

WHAT IS LOST: the RATE of convergence. `SLOPE_UP` and `SLOPE_DN` give the two
boundary slopes and `WIDTH` gives the separation at the break, so a miner can
reconstruct a convergence rate up to the difference between "measured at the
pivots" and "measured at the break". That is not nothing, and it is disclosed
rather than claimed to be free.

=== WHAT IS NOT HERE, AND WHY ========================================

BROADENING / MEGAPHONE is not matched. The diverging branch is explicitly
rejected in the shape test above. CANDLE-0 measured its prototype at 2,093
firings (2.30% of bars) against 0.20-0.77% for every other shape, from the one
template with no constraint beyond "the boundaries diverged", and DEFERRED it
on specificity. Its overlap was fine (max |rho| 0.0984); this is not an
overlap rejection and it is reversible the moment there is predictive
evidence.

CAUSALITY: pivots are consumed no earlier than `pivot_bar + right`, and both
boundary lines are evaluated only at the current bar. Pinned by a
future-perturbation mutant in `tests/test_candle1_patterns.py`.
"""
