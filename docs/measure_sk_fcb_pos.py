# -*- coding: utf-8 -*-
"""SK-FCB-POS (PandasTa issue #108): every number in
`docs/SkFcbPosMeasured.md`.

    python docs/measure_sk_fcb_pos.py          # every section, in order
    python docs/measure_sk_fcb_pos.py A1 D     # named sections only

One section per gate limb, printed and never derived: the repo's dominant
defect is "a claim written before it was measured", so this file is the only
place a figure in the receipt, the module docstring or
`tests/test_sk_fcb_pos.py` may come from.

    upper[T]     = level of the last CONFIRMED fractal high, held forward
    lower[T]     = level of the last CONFIRMED fractal low, held forward
    SK_FCB_POS   = (close - lower) / (upper - lower)

A fractal high is centred on a bar whose high beats all `SPAN` highs on each
side STRICTLY, and it is confirmed `SPAN` bars later.

⚠ The frames, the seeds and the two band-leg helpers are issue #107's
(`docs/measure_sk_fcb_width.py`), so a figure about the BAND is the same
measurement in both receipts and only the figures about this column's
quotient are new. What is new and is this column's own risk is the
DENOMINATOR: `upper - lower` is not positive, so §C4 is the section to read
first.

⚠ The millisecond figures of §Z are this machine's and this run's. Nothing
else here depends on the machine, and `docs/measure_sk_fcb_pos_cpu.py`
re-runs the sections under numpy's reduced CPU dispatch to show which
figures move.
"""
import sys
import timeit
import tracemalloc
from pathlib import Path

import numpy as np
import pandas as pd
from pandas import DataFrame, Series, date_range

from pandas_ta.momentum.cci import cci
from pandas_ta.momentum.pgo import pgo
from pandas_ta.momentum.sk_fcb_pos import sk_fcb_pos
from pandas_ta.momentum.stoch import stoch
from pandas_ta.momentum.willr import willr
from pandas_ta.volatility.sk_fcb_width import (MIN_BARS, SPAN, _last_fractal,
                                               sk_fcb_width)

N = 1500
LEVEL = 100.0
#: The blind causality sweep's 36 perturbation points.
OFFSETS = list(range(N - 36, N))
#: Where §G plants a bad bar.
PLANT = 700


# ------------------------------------------------------------------ frames
# Same builders and seeds as `docs/measure_sk_fcb_width.py` and
# `tests/test_sk_fcb_pos.py`, so a number in any of the three is the same
# measurement. The first seven come from `tests/test_j_acosc.py` by way of
# issue #107; `coarse` is #107's eighth frame and is kept because this
# column's predicate is the same strict comparison.


def _ohlc(close, seed):
    """An OHLC frame around a close path, with `high >= close >= low`.

    The spread is random, so the highs and the lows are two different
    paths: a frame where `high - low` were constant would hide any
    confusion between the two band legs.
    """
    rng = np.random.default_rng(seed + 9_999)
    # Hourly, not daily: §Z runs 400,000 bars, and 400,000 DAYS from 2020
    # is past pandas' nanosecond datetime bound. Nothing here reads the
    # index, so the unit is free.
    idx = date_range("2020-01-01", periods=close.size, freq="h")
    return (Series(close * (1.0 + 0.004 * rng.random(close.size)), index=idx),
            Series(close * (1.0 - 0.004 * rng.random(close.size)), index=idx),
            Series(close, index=idx))


def _walk(seed=7, n=N, level=LEVEL, sigma=0.01):
    rng = np.random.default_rng(seed)
    return _ohlc(level * np.exp(np.cumsum(rng.normal(0.0, sigma, n))), seed)


def _trend(seed=11, n=N, level=LEVEL):
    rng = np.random.default_rng(seed)
    return _ohlc(level * np.exp(np.cumsum(rng.normal(0.003, 0.008, n))), seed)


def _range_bound(seed=13, n=N, level=LEVEL):
    rng = np.random.default_rng(seed)
    x = np.zeros(n)
    for i in range(1, n):
        x[i] = 0.9 * x[i - 1] + rng.normal(0.0, 0.02)
    return _ohlc(level * np.exp(x), seed)


def _grid(seed=17, n=N, level=LEVEL, tick=0.01):
    h, l, c = _walk(seed, n, level)
    return (np.round(h / tick) * tick, np.round(l / tick) * tick,
            np.round(c / tick) * tick)


def _heavy(seed=19, n=N, level=LEVEL):
    rng = np.random.default_rng(seed)
    return _ohlc(level * np.exp(np.cumsum(rng.standard_t(2.0, n) * 0.006)),
                 seed)


def _jump(seed=23, n=N, level=LEVEL):
    h, l, c = _walk(seed, n, level)
    f = Series(np.where(np.arange(n) >= 700, 1.5, 1.0), index=c.index)
    return h * f, l * f, c * f


def _flat(n=N, level=LEVEL):
    idx = date_range("2020-01-01", periods=n, freq="h")
    one = Series(np.full(n, level), index=idx)
    return one.copy(), one.copy(), one.copy()


def _coarse(seed=7, n=N, level=LEVEL, tick=2.0):
    """A walk rounded to a tick COARSER than its own bar-to-bar move.

    Issue #107's eighth frame, kept for the same reason and for one more of
    this column's own. The fractal predicate is STRICT, so a tie on either
    side of the centre bar destroys the fractal, and FVGDEAD (`CLAUDE.md`)
    is this repo's record of a column whose behaviour on synthetic
    continuous floats said nothing about its behaviour on rounded prices.
    The extra reason here is the DENOMINATOR: a coarse grid is where the
    two band legs land on the SAME tick, and `upper - lower == 0` is the
    one input that makes this column vanish rather than go wrong (§C4).
    """
    h, l, c = _walk(seed, n, level)
    return (np.round(h / tick) * tick, np.round(l / tick) * tick,
            np.round(c / tick) * tick)


FRAMES = {
    "walk": _walk, "trend": _trend, "range-bound": _range_bound,
    "grid": _grid, "heavy-tailed": _heavy, "jump": _jump, "flat": _flat,
    "coarse": _coarse,
}
NAMES = list(FRAMES)
#: `flat` carries no strict local extreme at all, so the column never fires
#: on it (§C). Every "every frame" claim about VALUES is over these seven.
FIRING = [n for n in NAMES if n != "flat"]


def _scaled(frame, factor):
    h, l, c = frame
    return h * factor, l * factor, c * factor


def _rel(a, b):
    """Max relative difference over the bars both fire on."""
    m = a.notna() & b.notna()
    if not int(m.sum()):
        return float("nan")
    d = (a[m] - b[m]).abs()
    scale = b[m].abs().where(b[m].abs() > 0.0, np.nan)
    rel = (d / scale).max()
    return 0.0 if np.isnan(rel) else float(rel)


def _abs(a, b):
    m = a.notna() & b.notna()
    if not int(m.sum()):
        return float("nan")
    return float((a[m] - b[m]).abs().max())


def _spearman(a, b):
    m = a.notna() & b.notna()
    if int(m.sum()) < 3 or a[m].nunique() < 2 or b[m].nunique() < 2:
        return float("nan")
    return float(a[m].corr(b[m], method="spearman"))


def _bit_equal(a, b):
    if not bool((a.isna() == b.isna()).all()):
        return False
    m = a.notna()
    return bool((a[m] == b[m]).all())


def _differs(a, b):
    """Bars where exactly one fires, or both fire and the values differ."""
    one = int((a.isna() != b.isna()).sum())
    m = a.notna() & b.notna()
    return one + int((a[m] != b[m]).sum())


# ----------------------------------------------------------------- oracles


def _fractals(h, l, span=SPAN):
    """Skender's `Fractal` with `leftSpan = rightSpan = span` and
    `EndType.HighLow`, transcribed as its own double loop.

        for (int p = i - leftSpan; p <= i + rightSpan; p++) {
            if (p == i) continue;
            if (evalHigh <= pHigh) isHigh = false;
            if (evalLow  >= pLow)  isLow  = false;
        }

    guarded by `if (i >= leftSpan && i < length - rightSpan)`. The level is
    returned ON the centre bar, which is where Skender puts it; what this
    port does with that index is §A3.
    """
    n = h.size
    bear, bull = np.full(n, np.nan), np.full(n, np.nan)
    for i in range(n):
        if not (span <= i < n - span):
            continue
        is_high = is_low = True
        for p in range(i - span, i + span + 1):
            if p == i:
                continue
            if not h[i] > h[p]:
                is_high = False
            if not l[i] < l[p]:
                is_low = False
        if is_high:
            bear[i] = h[i]
        if is_low:
            bull[i] = l[i]
    return bear, bull


def _carry(bear, bull, lag):
    """`Fcb`'s own roll-forward, with the fractal read `lag` bars after its
    centre: `upperLine = f.FractalBear ?? upperLine`."""
    n = bear.size
    up, lo = np.full(n, np.nan), np.full(n, np.nan)
    cur_up = cur_lo = np.nan
    for t in range(n):
        j = t - lag
        if j >= 0:
            if bear[j] == bear[j]:
                cur_up = bear[j]
            if bull[j] == bull[j]:
                cur_lo = bull[j]
        up[t], lo[t] = cur_up, cur_lo
    return up, lo


def _fin(x):
    """The screen harness' `_fin` (`docs/issues/screen/ind_screen.py:37`),
    which is the only guard the prototype's `sdiv` applies."""
    return x.replace([np.inf, -np.inf], np.nan)


def _oracle(high, low, close, lag=SPAN):
    """The source formula by explicit loops, sharing no code with the
    module: close's position between the two band legs.

    ⚠ The `_fin` at the end is not decoration: `upper - lower` can be
    exactly 0, and without it the comparison against the module would be
    comparing `inf` with `NaN` rather than testing the formula (§C4).
    """
    h = high.to_numpy(dtype=float)
    l = low.to_numpy(dtype=float)
    bear, bull = _fractals(h, l)
    up, lo = _carry(bear, bull, lag)
    c = close.to_numpy(dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        raw = (c - lo) / (up - lo)
    return _fin(Series(raw, index=close.index))


def _prototype(high, low, close):
    """`docs/issues/screen/ind_screen_r2.py`, candidate `sk_fcb_pos`,
    retyped (that file is gitignored, so it is on the owner's machine
    only):

        def last_fractal(x, span, high):
            ref = x.shift(span)
            left = (x.shift(span + 1).rolling(span).max() if high
                    else x.shift(span + 1).rolling(span).min())
            right = (x.rolling(span).max() if high
                     else x.rolling(span).min())
            is_f = ((ref > left) & (ref > right) if high
                    else (ref < left) & (ref < right))
            return ref.where(is_f).ffill()

        def sdiv(a, b): return _fin(a / b)   # +-inf -> NaN

        @cand("sk_fcb_pos", ...)
        def _(o, h, l, c, v):
            up, lo = last_fractal(h, 2, True), last_fractal(l, 2, False)
            return sdiv(c - lo, up - lo)
    """
    def last_fractal(x, span, high_):
        ref = x.shift(span)
        left = (x.shift(span + 1).rolling(span).max() if high_
                else x.shift(span + 1).rolling(span).min())
        right = x.rolling(span).max() if high_ else x.rolling(span).min()
        is_f = ((ref > left) & (ref > right) if high_
                else (ref < left) & (ref < right))
        return ref.where(is_f).ffill()
    up = last_fractal(high, 2, True)
    lo = last_fractal(low, 2, False)
    return _fin((close - lo) / (up - lo))


def _centre_reading(high, low, close):
    """The reading NOT taken: the fractal used ON its centre bar, which is
    the index Skender's `Fractal` returns it at."""
    return _oracle(high, low, close, lag=0)


def _non_strict(high, low, close):
    """The reading NOT taken: `>=` / `<=` instead of strict, i.e. a tie on
    either side still makes a fractal."""
    def last_fractal(x, span, high_):
        ref = x.shift(span)
        left = (x.shift(span + 1).rolling(span).max() if high_
                else x.shift(span + 1).rolling(span).min())
        right = x.rolling(span).max() if high_ else x.rolling(span).min()
        is_f = ((ref >= left) & (ref >= right) if high_
                else (ref <= left) & (ref <= right))
        return ref.where(is_f).ffill()
    up = last_fractal(high, 2, True)
    lo = last_fractal(low, 2, False)
    return _fin((close - lo) / (up - lo))


def _close_ends(high, low, close):
    """The reading NOT taken: `EndType.Close`, Skender's other option, which
    judges and returns the CLOSE instead of the high/low."""
    up = _last_fractal(close, SPAN, True)
    lo = _last_fractal(close, SPAN, False)
    return _fin((close - lo) / (up - lo))


def _clipped(high, low, close):
    """The reading NOT taken, and the one a consumer is most likely to
    assume: the quotient with an INVERTED band (`upper < lower`) masked out
    instead of kept. §C4 prices the difference."""
    h = high.where(np.isfinite(high))
    l = low.where(np.isfinite(low))
    up = _last_fractal(h, SPAN, True)
    lo = _last_fractal(l, SPAN, False)
    width = (up - lo).where((up - lo) > 0.0)
    return _fin((close - lo) / width)


# ----------------------------------------------------------------- mutants

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "pandas_ta" / "momentum" / "sk_fcb_pos.py"
BAND_SOURCE = ROOT / "pandas_ta" / "volatility" / "sk_fcb_width.py"

#: (label, where, old text, new text). `where` is which SHIPPED file the
#: edit lands in -- "pos" is this port's own module, "band" is the
#: `_last_fractal` it imports. Both are read off disk and exec'd in memory,
#: so neither mutant can drift away from the source it claims to edit.
#: ⚠ Three of the six live in the IMPORTED helper, which is the point: this
#: module's causality is not decidable from this module's file alone, so
#: Gate B has to reach into the file it imports from.
CAUSALITY_MUTANTS = [
    # Skender's own index: the confirmed level moved back onto its centre
    # bar. §A3 builds the same reading independently and asserts the two
    # agree, so this is the documented alternative reading, not an
    # invented edit.
    ("centre-read", "band", "    return ref.where(is_fractal).ffill()",
     "    return ref.where(is_fractal).shift(-span).ffill()"),
    ("right-window-lead", "band", "        right = x.rolling(span).max()",
     "        right = x.shift(-1).rolling(span).max()"),
    ("band-bfill", "band", "    return ref.where(is_fractal).ffill()",
     "    return ref.where(is_fractal).bfill()"),
    ("upper-lead", "pos", "    upper = _last_fractal(h, SPAN, True)",
     "    upper = _last_fractal(h, SPAN, True).shift(-1)"),
    ("output-early", "pos", "    pos = (close - lower) / (upper - lower)",
     "    pos = ((close - lower) / (upper - lower)).shift(-1)"),
    ("numerator-lead", "pos", "    pos = (close - lower) / (upper - lower)",
     "    pos = (close.shift(-1) - lower) / (upper - lower)"),
]
#: Not a causality mutant: the high/low guard, removed, to price it.
HL_GUARD_OFF = ("    h = high.where(np.isfinite(high))\n"
                "    l = low.where(np.isfinite(low))",
                "    h = high\n    l = low")
#: Not a causality mutant either: the prototype's `sdiv`, removed, to price
#: what the `+-inf -> NaN` fold buys.
FIN_OFF = ("    pos = pos.replace([np.inf, -np.inf], np.nan)",
           "    pos = pos")


def _exec(text):
    ns = {}
    exec(compile(text, "<mutant>", "exec"), ns)
    return ns


def _edited(where, old, new):
    path = SOURCE if where == "pos" else BAND_SOURCE
    src = path.read_text(encoding="utf-8")
    assert src.count(old) == 1, \
        f"{old!r} occurs {src.count(old)} times in {path.name}"
    return src.replace(old, new)


def _mutant(where, old, new):
    """`sk_fcb_pos` with one edit applied to the shipped source.

    An edit in "band" is applied to `sk_fcb_width.py`, the mutated
    `_last_fractal` is lifted out of it, and it REPLACES the name in this
    module's own globals -- which works, and is why the band mutants are
    live at all, because `sk_fcb_pos` looks `_last_fractal` up in its
    globals on every call rather than binding it at import.
    `section_B1` asserts each of the six actually changes the output, so an
    edit that silently failed to take could not pass as a clean sweep.
    """
    if where == "pos":
        return _exec(_edited("pos", old, new))["sk_fcb_pos"]
    band = _exec(_edited("band", old, new))["_last_fractal"]
    ns = _exec(SOURCE.read_text(encoding="utf-8"))
    ns["_last_fractal"] = band
    return ns["sk_fcb_pos"]


def _futures(frame, j, spread=3.0):
    """Two frames that agree BIT FOR BIT on bars < j and differ wholly on
    bars >= j: one with every later bar scaled UP by a per-bar random
    factor in [1, 4], one with every later bar scaled DOWN by its
    reciprocal.

    ⚠ This is deliberately not the usual "multiply the tail by 1.03"
    sweep, and the reason is this column rather than a preference. The
    fractal predicate is a COMPARISON, so a look-ahead only becomes
    visible when a fractal decision within `SPAN` bars of the boundary
    actually flips; a 3% nudge leaves most decisions intact, and a weak
    detector returning 0 is weak evidence. Opposite large factors flip
    the right-hand side of the boundary decisions in both directions at
    once -- §B1 prints what each costs. The same factor multiplies high,
    low and close, so `high >= close >= low` survives, and bars < j are
    multiplied by exactly 1.0, which is exact in binary.
    """
    h, l, c = frame
    n = c.size
    rng = np.random.default_rng(90_001 + j)
    u = rng.random(n)
    up, dn = np.ones(n), np.ones(n)
    up[j:] = 1.0 + spread * u[j:]
    dn[j:] = 1.0 / (1.0 + spread * u[j:])
    fa = Series(up, index=c.index)
    fb = Series(dn, index=c.index)
    return (h * fa, l * fa, c * fa), (h * fb, l * fb, c * fb)


def _caught_at(fn, frame, j):
    """Does bar < j read bar >= j? Two wholly different futures, one
    shared past: a causal column is bit-identical on the shared part."""
    frame_a, frame_b = _futures(frame, j)
    a = fn(*frame_a).iloc[:j]
    b = fn(*frame_b).iloc[:j]
    if not bool((a.isna() == b.isna()).all()):
        return True
    m = a.notna() & b.notna()
    return not bool((a[m] == b[m]).all())


def _sweep(fn, frame, offsets=None):
    return sum(_caught_at(fn, frame, j) for j in (offsets or OFFSETS))


def _band_exposed_at(band_fn, frame, j):
    """Does the MUTATED band itself differ on the shared prefix?

    A necessary condition for a band mutant to be caught: if the two
    futures give the same `upper` and `lower` on every bar `< j`, no
    arithmetic downstream of them can differ there. Computed, not derived
    -- the mutated `_last_fractal` is run on both futures and the prefixes
    are compared.
    """
    (ha, la, _), (hb, lb, _) = _futures(frame, j)
    for x_a, x_b, upper in ((ha, hb, True), (la, lb, False)):
        a = band_fn(x_a.where(np.isfinite(x_a)), SPAN, upper).iloc[:j]
        b = band_fn(x_b.where(np.isfinite(x_b)), SPAN, upper).iloc[:j]
        if not bool((a.isna() == b.isna()).all()):
            return True
        m = a.notna() & b.notna()
        if not bool((a[m] == b[m]).all()):
            return True
    return False


def _same(a, b):
    return bool(a == b) or (np.isnan(a) and np.isnan(b))


def _moved_band_bars(label, band_fn, frame, j):
    """The prefix bars whose INPUT to the quotient the mutant moved.

    For `right-window-lead` that is every bar `< j` where the mutated band
    differs between the two futures. For `upper-lead` the shift can only
    reach bar `j - 1`, which is derived in `_upper_lead_exposed_at` and
    needs no search. Used by §B2 to say whether an exposed-but-uncaught
    offset was blocked by a NaN or by a coincidence.
    """
    if label != "right-window-lead":
        return [j - 1]
    (ha, la, _), (hb, lb, _) = _futures(frame, j)
    moved = set()
    for x_a, x_b, upper in ((ha, hb, True), (la, lb, False)):
        a = band_fn(x_a.where(np.isfinite(x_a)), SPAN, upper).iloc[:j]
        b = band_fn(x_b.where(np.isfinite(x_b)), SPAN, upper).iloc[:j]
        diff = (a.isna() != b.isna()) | ((a.notna() & b.notna()) & (a != b))
        moved.update(int(i) for i in np.flatnonzero(diff.to_numpy()))
    return sorted(moved)


def _upper_lead_exposed_at(frame, j):
    """The same necessary condition for `upper-lead`, whose channel is not
    the band but the SHIFT.

    `upper-lead` makes bar `t` read `upper[t + 1]`. For `t + 1 <= j - 1`
    that is still a prefix bar and is identical in both futures, so the
    ONLY prefix bar the edit can move is `t = j - 1`, which reads
    `upper[j]`. The condition is therefore `upper[j]` differing between the
    two futures, and it is computed here on the UNMUTATED band, which is
    what that mutant uses.
    """
    (ha, _, _), (hb, _, _) = _futures(frame, j)
    a = _last_fractal(ha.where(np.isfinite(ha)), SPAN, True).iloc[j]
    b = _last_fractal(hb.where(np.isfinite(hb)), SPAN, True).iloc[j]
    return not _same(a, b)


def _head(title):
    print()
    print("=" * 72)
    print(title)
    print("=" * 72)


def _census(frame):
    """The four populations §C4 is about, for one frame."""
    h, l, c = frame
    hh = h.where(np.isfinite(h))
    ll = l.where(np.isfinite(l))
    up = _last_fractal(hh, SPAN, True)
    lo = _last_fractal(ll, SPAN, False)
    den = up - lo
    ready = up.notna() & lo.notna() & c.notna()
    col = sk_fcb_pos(h, l, c)
    return {
        "col": col, "upper": up, "lower": lo, "den": den, "ready": ready,
        "ready_n": int(ready.sum()),
        "fired": int(col.notna().sum()),
        "den_pos": int((ready & (den > 0.0)).sum()),
        "den_zero": int((ready & (den == 0.0)).sum()),
        "den_neg": int((ready & (den < 0.0)).sum()),
    }


# ---------------------------------------------------------------- sections


def section_A1():
    _head("A1 Gate A -- the source formula by explicit loops")
    print("Skender's `Fractal` double loop plus `Fcb`'s roll-forward, then")
    print("close's position between the legs. The oracle shares no code with")
    print("the module: `_fractals` is a Python double loop over numpy and")
    print("`_carry` is a Python for-loop, where the module is four rolling")
    print("windows and an ffill.")
    print()
    print("Nothing here is a tolerance. The two band legs are SELECTED price")
    print("levels, so once the selection agrees the arithmetic is two")
    print("subtractions and one division on the same doubles -- it is either")
    print("bit-equal or the selection differs.")
    print()
    print(f"{'frame':>13} {'fired':>6} {'NaN masks':>10} {'max |diff|':>12} "
          f"{'bit-equal':>10}")
    total = 0
    for name in NAMES:
        frame = FRAMES[name]()
        col = sk_fcb_pos(*frame)
        orc = _oracle(*frame)
        total += int(col.notna().sum())
        print(f"{name:>13} {int(col.notna().sum()):>6} "
              f"{str(bool((col.isna() == orc.isna()).all())):>10} "
              f"{_abs(col, orc):>12.3e} {str(_bit_equal(col, orc)):>10}")
    print()
    print(f"fired bars over the eight frames: {total}")


def section_A2():
    _head("A2 Gate A -- the screen prototype, retyped")
    print("`docs/issues/screen/ind_screen_r2.py`, candidate `sk_fcb_pos`.")
    print("⚠ This is NOT a second derivation and is not offered as one: the")
    print("prototype's `last_fractal` is the module's `_last_fractal`")
    print("operation for operation, and its `sdiv` is the module's")
    print("`replace`. What bit-equality here buys is the TIE to the screen's")
    print("Gate E figure (0.8348 vs pgo), which was measured on this")
    print("expression, and the module's guards priced at zero on a clean")
    print("frame.")
    print()
    print(f"{'frame':>13} {'fired':>6} {'NaN masks':>10} {'bit-equal':>10}")
    for name in NAMES:
        frame = FRAMES[name]()
        col = sk_fcb_pos(*frame)
        pro = _prototype(*frame)
        print(f"{name:>13} {int(col.notna().sum()):>6} "
              f"{str(bool((col.isna() == pro.isna()).all())):>10} "
              f"{str(_bit_equal(col, pro)):>10}")


def section_A3():
    _head("A3 The divergence: Skender's index vs the confirmed index")
    print("Skender's `Fractal` returns a fractal ON its centre bar. This")
    print("port reads it SPAN bars later, when the right-hand bars exist.")
    print("That is a DIVERGENCE from the source rather than a")
    print("transcription, so both readings are measured here and the")
    print("centre reading is the `centre-read` mutant of §B1, which Gate B")
    print("catches.")
    print()
    print(f"{'frame':>13} {'both fire':>10} {'differ':>7} {'spearman':>9} "
          f"{'max |diff|':>12}")
    for name in FIRING:
        frame = FRAMES[name]()
        col = sk_fcb_pos(*frame)
        ctr = _centre_reading(*frame)
        m = col.notna() & ctr.notna()
        print(f"{name:>13} {int(m.sum()):>10} "
              f"{_differs(col, ctr):>7} {_spearman(col, ctr):>9.4f} "
              f"{_abs(col, ctr):>12.4f}")
    print()
    print("⚠ What `Fcb.Series.cs` itself does with that index is NOT")
    print("established here: the file is not readable from this worktree")
    print("(pinned by tests/test_sk_fcb_pos.py). The attribution is to the")
    print("issue's NAMING of the source.")


def section_A4():
    _head("A4 The strict predicate, and the EndType.Close reading")
    print("`>` and not `>=`. Skender's loop sets `isHigh = false` on")
    print("`evalHigh <= pHigh`, so a TIE on either side of the centre bar")
    print("destroys the fractal. On continuous floats ties never happen; on")
    print("a tick grid they do.")
    print()
    print(f"{'frame':>13} {'differ':>7} {'spearman':>9} {'max |diff|':>12}")
    for name in FIRING:
        frame = FRAMES[name]()
        col = sk_fcb_pos(*frame)
        ns = _non_strict(*frame)
        print(f"{name:>13} {_differs(col, ns):>7} "
              f"{_spearman(col, ns):>9.4f} {_abs(col, ns):>12.4f}")
    print()
    print("EndType.Close, Skender's other option: judge and return the")
    print("CLOSE instead of the high and the low. A different column, and")
    print("the issue names the high/low form.")
    print()
    print(f"{'frame':>13} {'differ':>7} {'spearman':>9} {'max |diff|':>12}")
    for name in FIRING:
        frame = FRAMES[name]()
        col = sk_fcb_pos(*frame)
        ce = _close_ends(*frame)
        print(f"{name:>13} {_differs(col, ce):>7} "
              f"{_spearman(col, ce):>9.4f} {_abs(col, ce):>12.4f}")


def section_B():
    _head("B Gate B -- the blind causality sweep")
    print("For each boundary j: two frames that agree bit for bit on bars")
    print("< j and differ wholly on bars >= j. A causal column is")
    print("bit-identical on the shared prefix. Every offset of every frame,")
    print("not a sample.")
    print()
    print(f"{'frame':>13} {'offsets':>8} {'caught':>7}")
    for name in NAMES:
        frame = FRAMES[name]()
        offsets = list(range(1, N))
        print(f"{name:>13} {len(offsets):>8} "
              f"{_sweep(sk_fcb_pos, frame, offsets):>7}")


def section_B1():
    _head("B1 Gate B -- six look-ahead mutants, read off the shipped source")
    print("Prefix truncation alone cannot see back-dating, so each mutant is")
    print("an edit to a SHIPPED file, exec'd in memory, and swept by the")
    print("same detector. Three edits land in this module; three land in the")
    print("`_last_fractal` it imports, which is the only way to test the")
    print("causality of code this module does not contain.")
    print()
    print("`live` is the number of the eight frames on which the mutant's")
    print("output differs from the module's at all: a mutant that is not")
    print("live is an edit that failed to take, and a clean sweep against it")
    print("would prove nothing.")
    print()
    header = f"{'mutant':>18} {'in':>5} {'live':>5} " + \
        " ".join(f"{n[:9]:>9}" for n in NAMES)
    print(header)
    for label, where, old, new in CAUSALITY_MUTANTS:
        fn = _mutant(where, old, new)
        live = 0
        caught = []
        for name in NAMES:
            frame = FRAMES[name]()
            live += int(_differs(sk_fcb_pos(*frame), fn(*frame)) > 0)
            caught.append(_sweep(fn, frame))
        print(f"{label:>18} {where:>5} {live:>5} " +
              " ".join(f"{c:>9}" for c in caught))
    print()
    print(f"each frame contributes {len(OFFSETS)} offsets "
          f"({OFFSETS[0]} .. {OFFSETS[-1]})")
    print()
    print("⚠ A 36-of-36 headline is NOT available for this indicator and is")
    print("not claimed. Three of the six look ahead THROUGH a strict")
    print("comparison, so they only show when a fractal decision within")
    print("SPAN bars of the boundary actually flips. §B2 takes the weakest")
    print("of them apart.")


def section_B2():
    _head("B2 Gate B -- the two weak mutants, swept densely")
    print("Two of the six are caught on single digits out of 36 in §B1, and")
    print("that is expected rather than reassuring: both look ahead THROUGH")
    print("something discrete. `right-window-lead` gives the right-hand")
    print("window one extra bar, so it changes the output only when that")
    print("bar flips a strict comparison; `upper-lead` shifts a STEP")
    print("function by one bar, so it changes the output only next to a")
    print("step. A single-digit catch count is therefore not evidence that")
    print("the module is clean, so each is given a necessary condition for")
    print("being catchable at all, and the catches are counted inside and")
    print("outside it over every offset of every firing frame.")
    print()
    print("Both conditions are COMPUTED, not derived: the relevant band is")
    print("run on both futures and compared. `outside` must be 0, or the")
    print("condition is wrong and the section proves nothing.")
    print()
    offsets = list(range(5, N))
    for label in ("right-window-lead", "upper-lead"):
        _, where, old, new = next(m for m in CAUSALITY_MUTANTS
                                  if m[0] == label)
        fn = _mutant(where, old, new)
        band = None
        if label == "right-window-lead":
            band = _exec(_edited(where, old, new))["_last_fractal"]
            def exposed_at(frame, j, _band=band):
                return _band_exposed_at(_band, frame, j)
            cond = ("the MUTATED band differs on some bar < j")
        else:
            exposed_at = _upper_lead_exposed_at
            cond = ("upper[j] differs between the two futures -- bar j - 1 "
                    "is the only prefix bar the shift can reach")
        print(f"{label}: exposed(j) = {cond}")
        print()
        print(f"{'frame':>13} {'offsets':>8} {'exposed':>8} {'caught':>7} "
              f"{'in exposed':>11} {'outside':>8} {'missed':>7}")
        tot_off = tot_exp = tot_caught = tot_out = 0
        missed = {}
        for name in FIRING:
            frame = FRAMES[name]()
            n_exp = n_caught = n_in = n_out = 0
            miss = []
            for j in offsets:
                exposed = exposed_at(frame, j)
                caught = _caught_at(fn, frame, j)
                n_exp += exposed
                n_caught += caught
                n_in += caught and exposed
                n_out += caught and not exposed
                if exposed and not caught:
                    miss.append(j)
            missed[name] = miss
            tot_off += len(offsets)
            tot_exp += n_exp
            tot_caught += n_caught
            tot_out += n_out
            print(f"{name:>13} {len(offsets):>8} {n_exp:>8} {n_caught:>7} "
                  f"{n_in:>11} {n_out:>8} {len(miss):>7}")
        print()
        n_missed = sum(len(v) for v in missed.values())
        print(f"control totals: {tot_off} offsets, {tot_exp} exposed, "
              f"{tot_caught} caught, {tot_out} caught outside the condition")
        print(f"                {tot_off - tot_exp} unexposed offsets, "
              f"{n_missed} exposed-but-missed "
              f"({tot_exp} - {tot_caught} = {tot_exp - tot_caught})")
        print()
        print("Every exposed-but-missed offset, classified rather than left")
        print("as a residue: `all-NaN` means every bar the band moved on")
        print("reads NaN in BOTH columns, so the move cannot reach the")
        print("output; `value-tie` means it reads a number and the two")
        print("quotients coincide anyway. On a coarse grid the column takes")
        print("27 distinct values on 1,326 fired bars (§C), which is where a")
        print("tie is cheap.")
        print()
        print(f"{'frame':>13} {'missed':>7} {'all-NaN':>8} {'value-tie':>10} "
              f"{'offsets':>24}")
        for name in FIRING:
            miss = missed[name]
            if not miss:
                continue
            frame = FRAMES[name]()
            n_nan = n_tie = 0
            for j in miss:
                frame_a, frame_b = _futures(frame, j)
                a = fn(*frame_a).iloc[:j]
                b = fn(*frame_b).iloc[:j]
                moved = _moved_band_bars(label, band, frame, j)
                if moved and all(np.isnan(a.iloc[i]) and np.isnan(b.iloc[i])
                                 for i in moved):
                    n_nan += 1
                else:
                    n_tie += 1
            shown = ", ".join(str(j) for j in miss[:6]) + \
                ("" if len(miss) <= 6 else ", ...")
            print(f"{name:>13} {len(miss):>7} {n_nan:>8} {n_tie:>10} "
                  f"{shown:>24}")
        print()
    print("The module itself over the same dense grid, for comparison: §B,")
    print("0 caught of 1,499 offsets on each of the eight frames.")


def section_C():
    _head("C Gate C -- reachability")
    print("Fired bars and the first fired bar, per frame. The column is NaN")
    print("until a fractal high AND a fractal low have both confirmed, so")
    print("THE WARM-UP IS DATA-DEPENDENT and there is no constant to quote.")
    print()
    print(f"{'frame':>13} {'bars':>6} {'fired':>6} {'first':>6} "
          f"{'distinct':>9} {'min':>10} {'max':>10}")
    for name in NAMES:
        frame = FRAMES[name]()
        col = sk_fcb_pos(*frame)
        v = col.dropna()
        first = int(np.flatnonzero(col.notna().to_numpy())[0]) if v.size \
            else -1
        if v.size:
            print(f"{name:>13} {col.size:>6} {v.size:>6} {first:>6} "
                  f"{v.nunique():>9} {v.min():>10.4f} {v.max():>10.4f}")
        else:
            print(f"{name:>13} {col.size:>6} {v.size:>6} {first:>6} "
                  f"{0:>9} {'--':>10} {'--':>10}")
    print()
    print("Gate D's constant-column guard, 0 < fires < n, read off the same")
    print("rows: `flat` fires 0 and is the one frame that fails it, which is")
    print("a reading about a constant price rather than a defect (§C3).")
    print()
    print("The earliest bar a fire is POSSIBLE on is 2 * SPAN = "
          f"{2 * SPAN}: a centre at bar SPAN confirmed SPAN bars later. It")
    print("needs one bar to be both the strict high and the strict low of")
    print("its window -- an outside bar. A hand frame that does it:")
    idx = date_range("2020-01-01", periods=7, freq="D")
    h = Series([10.0, 10.0, 12.0, 10.0, 10.0, 10.0, 10.0], index=idx)
    l = Series([9.0, 9.0, 7.0, 9.0, 9.0, 9.0, 9.0], index=idx)
    c = Series([9.5, 9.5, 9.5, 9.5, 11.0, 7.5, 9.5], index=idx)
    col = sk_fcb_pos(h, l, c)
    print()
    print(f"{'bar':>4} {'high':>7} {'low':>7} {'close':>7} {'SK_FCB_POS':>11}")
    for i in range(col.size):
        val = col.iloc[i]
        print(f"{i:>4} {h.iloc[i]:>7.2f} {l.iloc[i]:>7.2f} "
              f"{c.iloc[i]:>7.2f} "
              f"{'NaN' if np.isnan(val) else f'{val:>11.4f}':>11}")
    print()
    print(f"first fired bar: "
          f"{int(np.flatnonzero(col.notna().to_numpy())[0])}")
    print("Bar 4 closes above the upper leg and bar 5 below the lower leg,")
    print("so the hand frame also shows the column leaving [0, 1] (§C4).")


def section_C2():
    _head("C2 The strict predicate against a tick grid")
    print("Fractals found per leg on the same walk at four tick sizes, and")
    print("what the column does with them. Rounding starves the band, and a")
    print("starved band is this column's zero-denominator regime.")
    print()
    print(f"{'tick':>10} {'upper fr':>9} {'lower fr':>9} {'ready':>6} "
          f"{'fired':>6} {'den=0':>6} {'den<0':>6} {'distinct':>9}")
    for tick in (0.0, 0.01, 0.5, 2.0):
        frame = (_walk() if tick == 0.0 else _coarse(tick=tick))
        h, l, c = frame
        cen = _census(frame)
        up, lo = cen["upper"], cen["lower"]
        n_up = int(np.r_[False, (up.to_numpy()[1:] != up.to_numpy()[:-1])
                         & ~np.isnan(up.to_numpy()[1:])].sum())
        n_lo = int(np.r_[False, (lo.to_numpy()[1:] != lo.to_numpy()[:-1])
                         & ~np.isnan(lo.to_numpy()[1:])].sum())
        label = "none" if tick == 0.0 else f"{tick}"
        print(f"{label:>10} {n_up:>9} {n_lo:>9} {cen['ready_n']:>6} "
              f"{cen['fired']:>6} {cen['den_zero']:>6} {cen['den_neg']:>6} "
              f"{cen['col'].dropna().nunique():>9}")
    print()
    print("Ties, counted directly: bars whose high equals the high of a bar")
    print("within SPAN of it, which is where a fractal can be lost.")
    print()
    print(f"{'frame':>13} {'high ties':>10} {'low ties':>10}")
    for name in ("walk", "grid", "coarse"):
        h, l, _ = FRAMES[name]()
        hv, lv = h.to_numpy(), l.to_numpy()
        th = sum(int((hv[i] == hv[max(0, i - SPAN):i + SPAN + 1]).sum() > 1)
                 for i in range(hv.size))
        tl = sum(int((lv[i] == lv[max(0, i - SPAN):i + SPAN + 1]).sum() > 1)
                 for i in range(lv.size))
        print(f"{name:>13} {th:>10} {tl:>10}")
    print()
    print("⚠ Per CLAUDE.md (FVGDEAD), 86,415 of 408,253 real BIST daily bars")
    print("(21.17%) close exactly at an extreme, so the real-data regime is")
    print("the right-hand end of this table and the continuous frames")
    print("predict nothing about it.")


def section_C3():
    _head("C3 What the REST of the momentum bucket does on a flat price")
    print("§C says this column fires 0 of 1,500 bars on `flat`. Whether that")
    print("is unusual for the bucket is a claim about 85 other indicators, so")
    print("it is RUN here rather than asserted: every name in")
    print("Category['momentum'] on a flat OHLCV frame, through its `df.ta`")
    print("accessor at defaults, column by column.")
    print()
    import pandas_ta as ta
    h, l, c = _flat(n=600)
    df = DataFrame({"open": c, "high": h, "low": l, "close": c,
                    "volume": Series(np.full(c.size, 1e6), index=c.index)})
    buckets = {"all NaN": [], "all 0.0": [], "other": [], "raised": []}
    for name in sorted(ta.Category["momentum"]):
        try:
            out = getattr(df.ta, name)()
        except Exception as exc:                       # noqa: BLE001
            buckets["raised"].append(f"{name} ({type(exc).__name__})")
            continue
        if out is None:
            buckets["raised"].append(f"{name} (None)")
            continue
        frame = out.to_frame() if isinstance(out, Series) else out
        for col in frame.columns:
            s = frame[col]
            fired = int(s.notna().sum())
            zeros = int((s.dropna() == 0.0).sum())
            key = ("all NaN" if fired == 0 else
                   "all 0.0" if zeros == fired else "other")
            buckets[key].append(f"{name}:{col}")
    total = sum(len(v) for k, v in buckets.items() if k != "raised")
    print(f"columns probed: {total}; indicators that raised or returned "
          f"None: {len(buckets['raised'])}")
    print()
    for key in ("all NaN", "all 0.0", "other", "raised"):
        print(f"{key:>9}: {len(buckets[key])}")
    print()
    print(f"all NaN : {sorted(buckets['all NaN'])}")
    print()
    print(f"all 0.0 : {sorted(buckets['all 0.0'])}")
    print()
    print(f"raised  : {sorted(buckets['raised'])}")


def section_C4():
    _head("C4 THE DENOMINATOR -- the section to read first")
    print("`upper - lower` is NOT positive and is not guarded to be. The")
    print("legs are the last fractal HIGH and the last fractal LOW, taken")
    print("from DIFFERENT bars, so the band can be crossed (`upper < lower`)")
    print("or collapsed (`upper == lower`). Issue #107 measured the same")
    print("difference as a width; here it is a DIVISOR, which is a different")
    print("kind of exposure:")
    print()
    print("  den > 0  the column means what its name says")
    print("  den == 0 the quotient is +-inf and the `replace` empties the")
    print("           bar -- the column LOSES bars the width keeps")
    print("  den < 0  the bar is KEPT with the scale INVERTED: a close above")
    print("           both legs reads below 0 instead of above 1")
    print()
    print("`ready` is the bars where both legs and the close exist, i.e. the")
    print("bars the column could fire on.")
    print()
    print(f"{'frame':>13} {'ready':>6} {'fired':>6} {'den>0':>6} "
          f"{'den=0':>6} {'den<0':>6} {'lost':>5}")
    for name in NAMES:
        cen = _census(FRAMES[name]())
        print(f"{name:>13} {cen['ready_n']:>6} {cen['fired']:>6} "
              f"{cen['den_pos']:>6} {cen['den_zero']:>6} "
              f"{cen['den_neg']:>6} {cen['ready_n'] - cen['fired']:>5}")
    print()
    print("Where the VALUES land. [0, 1] is the band; outside it the close")
    print("is outside the band, which is ordinary. The `den < 0` rows are")
    print("the ones a consumer cannot read as a position.")
    print()
    print(f"{'frame':>13} {'<0':>6} {'[0,1]':>6} {'>1':>6} {'min':>11} "
          f"{'max':>11} {'min den<0':>11} {'max den<0':>11}")
    for name in FIRING:
        cen = _census(FRAMES[name]())
        col, den = cen["col"], cen["den"]
        v = col.dropna()
        neg = col[cen["ready"] & (den < 0.0)].dropna()
        print(f"{name:>13} {int((v < 0.0).sum()):>6} "
              f"{int(((v >= 0.0) & (v <= 1.0)).sum()):>6} "
              f"{int((v > 1.0).sum()):>6} {v.min():>11.4f} "
              f"{v.max():>11.4f} "
              f"{(neg.min() if neg.size else float('nan')):>11.4f} "
              f"{(neg.max() if neg.size else float('nan')):>11.4f}")
    print()
    print("The reading NOT taken, priced: mask the inverted band instead of")
    print("keeping it. The screen prototype keeps it, and the prototype is")
    print("what Gate E's 0.8348 was measured on, so keeping it is the choice")
    print("that ties this port to that figure -- but the cost is measured")
    print("rather than waved away.")
    print()
    print(f"{'frame':>13} {'differ':>7} {'spearman':>9} {'max |diff|':>12}")
    for name in FIRING:
        frame = FRAMES[name]()
        col = sk_fcb_pos(*frame)
        clp = _clipped(*frame)
        print(f"{name:>13} {_differs(col, clp):>7} "
              f"{_spearman(col, clp):>9.4f} {_abs(col, clp):>12.4f}")
    print()
    print("How long an inverted band lasts: the number of runs of")
    print("consecutive `den < 0` bars, and the longest of them.")
    print()
    print(f"{'frame':>13} {'den<0 runs':>11} {'longest run':>12}")
    for name in FIRING:
        cen = _census(FRAMES[name]())
        flag = (cen["ready"] & (cen["den"] < 0.0)).to_numpy()
        runs, longest, cur = 0, 0, 0
        for bit in flag:
            if bit:
                cur += 1
                longest = max(longest, cur)
            else:
                runs += int(cur > 0)
                cur = 0
        runs += int(cur > 0)
        print(f"{name:>13} {runs:>11} {longest:>12}")


def section_D():
    _head("D Gate D -- scale invariance")
    print("x8 and x64 are exact binary factors. The fractal SELECTION is")
    print("comparison-only, and (c*f - lo*f) / (up*f - lo*f) rounds to the")
    print("same double as (c - lo) / (up - lo) when f is exact, so")
    print("bit-identity is expected and is asserted rather than hoped for.")
    print("⚠ Unlike the sibling width, the factor cancels between NUMERATOR")
    print("and DENOMINATOR here, so this column is dimensionless twice over")
    print("-- and that is also why it does not need `close` as a divisor.")
    print()
    print(f"{'frame':>13} {'fired':>6} {'x8 bit-equal':>13} "
          f"{'x64 bit-equal':>14}")
    total = 0
    for name in NAMES:
        frame = FRAMES[name]()
        col = sk_fcb_pos(*frame)
        total += int(col.notna().sum())
        print(f"{name:>13} {int(col.notna().sum()):>6} "
              f"{str(_bit_equal(col, sk_fcb_pos(*_scaled(frame, 8)))):>13} "
              f"{str(_bit_equal(col, sk_fcb_pos(*_scaled(frame, 64)))):>14}")
    print()
    print(f"fired bars over the eight frames: {total}")
    print()
    print("Inexact factors. Two things can move: the last bits of the")
    print("division, and -- the risk peculiar to a comparison-selected band")
    print("-- the fractal SELECTION, if a rescale collapses two distinct")
    print("neighbouring prices onto one double and so destroys a strict")
    print("inequality. `sel flips` counts bars where the selected band level")
    print("changed RELATIVE to the rescale, which is the second failure mode.")
    print()
    print(f"{'frame':>13} {'factor':>10} {'masks':>6} {'max |rel|':>11} "
          f"{'sel flips':>10}")
    worst = 0.0
    flips_total = 0
    pairs = 0
    per_frame = {}
    for name in FIRING:
        frame = FRAMES[name]()
        base = sk_fcb_pos(*frame)
        h, l, _ = frame
        up0 = _last_fractal(h, SPAN, True)
        lo0 = _last_fractal(l, SPAN, False)
        per_frame[name] = 0.0
        for factor in (10.0, 3.7, 0.1, 1.0000001):
            other = sk_fcb_pos(*_scaled(frame, factor))
            masks = bool((base.isna() == other.isna()).all())
            up1 = _last_fractal(h * factor, SPAN, True) / factor
            lo1 = _last_fractal(l * factor, SPAN, False) / factor
            flips = int((~np.isclose(up0.to_numpy(), up1.to_numpy(),
                                     rtol=1e-9, atol=0.0,
                                     equal_nan=True)).sum()
                        + (~np.isclose(lo0.to_numpy(), lo1.to_numpy(),
                                       rtol=1e-9, atol=0.0,
                                       equal_nan=True)).sum())
            rel = _rel(base, other)
            worst = max(worst, rel)
            per_frame[name] = max(per_frame[name], rel)
            flips_total += flips
            pairs += 1
            print(f"{name:>13} {factor:>10} {str(masks):>6} "
                  f"{rel:>11.3e} {flips:>10}")
    print()
    print(f"worst relative difference over the {pairs} pairs: {worst:.3e}; "
          f"selection flips: {flips_total}")
    print()
    print("The same, per frame -- the worst of that frame's four factors, so")
    print("the receipt quotes a printed figure rather than a hand-picked row.")
    print()
    print(f"{'frame':>13} {'worst |rel|':>12}")
    for name in FIRING:
        print(f"{name:>13} {per_frame[name]:>12.3e}")
    print()
    print("The same x8/x64 run REPEATED at three price levels, so the")
    print("invariance is not an artefact of level 100.")
    print()
    print(f"{'level':>10} {'fired':>6} {'x8':>6} {'x64':>6} "
          f"{'max |value|':>22}")
    for level in (1e-6, 1e+6, 1e+100):
        frame = _walk(level=level)
        col = sk_fcb_pos(*frame)
        print(f"{level:>10.0e} {int(col.notna().sum()):>6} "
              f"{str(_bit_equal(col, sk_fcb_pos(*_scaled(frame, 8)))):>6} "
              f"{str(_bit_equal(col, sk_fcb_pos(*_scaled(frame, 64)))):>6} "
              f"{col.abs().max():>22.17g}")
    print()
    print("MORE than scale-free: a LEVEL SHIFT cancels too. `(c + s) -")
    print("(lo + s)` over `(up + s) - (lo + s)` is the same quotient, and")
    print("the fractal selection is comparison-only, so the column is")
    print("invariant under any increasing AFFINE map of price -- which the")
    print("sibling width, with its `/ close`, is not. Measured rather than")
    print("asserted, and it is NOT bit-identical: adding a constant")
    print("re-rounds every price, so the quotient moves in its last bits.")
    print("`differ` counts bars that moved AT ALL, which is why it is large")
    print("while `max |rel|` is tiny.")
    print()
    print(f"{'shift':>10} {'masks':>6} {'differ':>7} {'spearman':>9} "
          f"{'max |rel|':>11}")
    base_frame = _walk()
    base = sk_fcb_pos(*base_frame)
    for shift in (1.0, 50.0, 1e6):
        h, l, c = base_frame
        other = sk_fcb_pos(h + shift, l + shift, c + shift)
        print(f"{shift:>10.0f} "
              f"{str(bool((base.isna() == other.isna()).all())):>6} "
              f"{_differs(base, other):>7} "
              f"{_spearman(base, other):>9.4f} "
              f"{_rel(base, other):>11.3e}")


def section_F():
    _head("F Non-redundancy against the fork's own momentum columns")
    print("⚠ SYNTHETIC and a DISCLOSURE, not a gate: Gate E measures 687")
    print("engine comparators over 89 real BIST frames, and none of them is")
    print("a pandas_ta port. The screen put this prototype's nearest")
    print("comparators at pgo 0.8348, willr 0.8303, kdj_J_9_3 0.8256 on real")
    print("data -- DISCLOSE_GAP -- and its fork stage at cci:CCI_14_0.015")
    print("0.8556 on 12 real frames. Those are the numbers that matter; what")
    print("follows is this session's own frames, which are not a substitute.")
    print()
    comparators = [
        ("close", lambda h, l, c: c),
        ("willr_14", lambda h, l, c: willr(h, l, c, length=14)),
        ("pgo_14", lambda h, l, c: pgo(h, l, c, length=14)),
        ("cci_14", lambda h, l, c: cci(h, l, c, length=14)),
        ("stochk_14_3_3",
         lambda h, l, c: stoch(h, l, c).iloc[:, 0]),
        ("sk_fcb_width_2", lambda h, l, c: sk_fcb_width(h, l, c)),
        ("numerator", lambda h, l, c:
         c - _last_fractal(l.where(np.isfinite(l)), SPAN, False)),
        ("denominator", lambda h, l, c:
         _last_fractal(h.where(np.isfinite(h)), SPAN, True)
         - _last_fractal(l.where(np.isfinite(l)), SPAN, False)),
    ]
    rows = {}
    print(f"{'comparator':>16} " + " ".join(f"{n[:9]:>9}" for n in FIRING))
    for label, fn in comparators:
        vals = []
        for name in FIRING:
            frame = FRAMES[name]()
            vals.append(_spearman(sk_fcb_pos(*frame), fn(*frame)))
        rows[label] = vals
        print(f"{label:>16} " + " ".join(f"{v:>9.4f}" for v in vals))
    print()
    print("Ranked by the largest |rho| any frame gives, which is the figure")
    print("a redundancy argument would quote:")
    print()
    ranked = sorted(rows.items(),
                    key=lambda kv: -max(abs(v) for v in kv[1]))
    for label, vals in ranked:
        print(f"{label:>16} max |rho| {max(abs(v) for v in vals):>7.4f} "
              f"median {float(np.median(vals)):>8.4f}")
    print()
    print("Three rows are worth reading, and one of them refutes the")
    print("obvious story:")
    print()
    print("⚠ `numerator` -- `close - lower` alone, in price units -- is the")
    print("TOP row on this frame set. Most of what the column ranks is")
    print("already in the numerator, and the denominator contributes the")
    print("scale-freedom rather than the ranking. That is consistent with")
    print("the screen finding pgo, willr and cci (all close-position")
    print("measures) as the nearest real-data comparators.")
    print("⚠ `close` itself is NOT the story, and the guess that it would be")
    print("is REFUTED here: -0.0112 .. 0.5049. Between two confirmations the")
    print("column is affine in close, but the legs step and the slope's SIGN")
    print("flips with the denominator, so the pooled rank correlation is")
    print("low. §L measures the within-stretch figure, which is the one that")
    print("is +-1.")
    print("⚠ `sk_fcb_width_2`, the sibling built from the SAME two legs,")
    print("reads at most |0.2096| here: the two ports are not restatements")
    print("of each other on this frame set.")


def section_G():
    _head("G Guards, each priced")
    print("G1 A bad CLOSE, and this is a DIVERGENCE from the sibling worth")
    print("stating plainly. There, close is the divisor and a close that is")
    print("not finite and positive is masked out. Here close is in the")
    print("NUMERATOR, so there is no mask and there is no need for one for")
    print("the non-finite cases -- the quotient goes NaN or infinite and")
    print("the prototype's `+-inf -> NaN` fold empties the bar. ⚠ A ZERO,")
    print("NEGATIVE or subnormal close is NOT emptied and reads a large")
    print("finite number instead, which is arithmetically what `position")
    print("relative to a band` means for such a close and is NOT a defect,")
    print("but a consumer that treats a bad tick as a price gets a number")
    print("rather than a gap. `other` counts bars OTHER than the plant whose")
    print("value moved.")
    print()
    frame = _walk()
    base = sk_fcb_pos(*frame)
    h, l, c = frame
    print(f"{'plant':>12} {'fired':>6} {'plant bar':>14} {'other':>6}")
    for label, value in (("NaN", np.nan), ("+inf", np.inf),
                         ("-inf", -np.inf), ("0.0", 0.0), ("-1.0", -1.0),
                         ("1e-310", 1e-310), ("1e+300", 1e+300)):
        cc = c.copy()
        cc.iloc[PLANT] = value
        col = sk_fcb_pos(h, l, cc)
        moved = _differs(base.drop(base.index[PLANT]),
                         col.drop(col.index[PLANT]))
        val = col.iloc[PLANT]
        print(f"{label:>12} {int(col.notna().sum()):>6} "
              f"{('NaN' if np.isnan(val) else f'{val:.6g}'):>14} "
              f"{moved:>6}")
    print()
    print("Without the `+-inf -> NaN` fold, for the same plants -- what the")
    print("fold buys, measured rather than assumed. It is ONE bar, and the")
    print("`1e+300` row shows the fold is not a general magnitude guard:")
    print("that close stays finite and absurd either way.")
    print()
    unfolded = _exec(_edited("pos", *FIN_OFF))["sk_fcb_pos"]
    print(f"{'plant':>12} {'plant bar':>14} {'non-finite bars':>16}")
    for label, value in (("NaN", np.nan), ("+inf", np.inf),
                         ("0.0", 0.0), ("1e+300", 1e+300)):
        cc = c.copy()
        cc.iloc[PLANT] = value
        col = unfolded(h, l, cc)
        v = col.to_numpy()
        bad = int((~np.isfinite(v) & ~np.isnan(v)).sum())
        val = col.iloc[PLANT]
        print(f"{label:>12} "
              f"{('NaN' if np.isnan(val) else f'{val:.6g}'):>14} {bad:>16}")
    print()
    print("G2 A bad HIGH or LOW is ABSORBED: a comparison against NaN is")
    print("False, so the bar makes no fractal. The cost is that its reach is")
    print("NOT bounded by a window -- `ffill` carries the older leg until the")
    print("next fractal replaces it. `earlier` counts bars BEFORE the plant")
    print("that moved, which is the causality-relevant number.")
    print()
    print(f"{'leg':>6} {'plant':>8} {'fired':>6} {'later moved':>12} "
          f"{'earlier':>8}")
    for leg, series in (("high", "h"), ("low", "l")):
        for label, value in (("NaN", np.nan), ("+inf", np.inf),
                             ("-inf", -np.inf)):
            hh, ll = h.copy(), l.copy()
            if series == "h":
                hh.iloc[PLANT] = value
            else:
                ll.iloc[PLANT] = value
            col = sk_fcb_pos(hh, ll, c)
            later = _differs(base.iloc[PLANT:], col.iloc[PLANT:])
            earlier = _differs(base.iloc[:PLANT], col.iloc[:PLANT])
            print(f"{leg:>6} {label:>8} {int(col.notna().sum()):>6} "
                  f"{later:>12} {earlier:>8}")
    print()
    print("G3 What the high/low mask buys. `+inf > x` is True, so an")
    print("unguarded `+inf` high BECOMES a fractal and the band carries it.")
    print("With the mask, a NaN and an infinite price give identical columns")
    print("-- the `NaN == +inf` column below.")
    print()
    print("⚠ And the unguarded failure here is QUIETER than the sibling's.")
    print("There an `inf` leg makes the width read `inf`, which any check")
    print("catches. Here the `inf` lands in the DENOMINATOR, so the quotient")
    print("reads a plausible number instead. `first moved` is the earliest")
    print("bar whose value the mask changes, printed as guarded -> unguarded")
    print("so the plausibility is on the page rather than asserted.")
    print()
    unguarded = _exec(_edited("pos", *HL_GUARD_OFF))["sk_fcb_pos"]
    print(f"{'leg':>6} {'plant':>8} {'guarded fired':>14} "
          f"{'unguarded fired':>16} {'differ':>7} {'first moved':>26} "
          f"{'NaN == +-inf':>13}")
    for leg in ("high", "low"):
        for label, value in (("+inf", np.inf), ("-inf", -np.inf)):
            hh, ll = h.copy(), l.copy()
            hn, ln = h.copy(), l.copy()
            if leg == "high":
                hh.iloc[PLANT] = value
                hn.iloc[PLANT] = np.nan
            else:
                ll.iloc[PLANT] = value
                ln.iloc[PLANT] = np.nan
            g = sk_fcb_pos(hh, ll, c)
            u = unguarded(hh, ll, c)
            gn = sk_fcb_pos(hn, ln, c)
            # the first bar at or after the plant whose value moved
            m = (g.isna() != u.isna()) | ((g.notna() & u.notna())
                                          & (g != u))
            where = np.flatnonzero(m.to_numpy())
            if where.size:
                i = int(where[0])
                moved = (f"bar {i}: {g.iloc[i]:.6g} -> {u.iloc[i]:.6g}")
            else:
                moved = "--"
            print(f"{leg:>6} {label:>8} {int(g.notna().sum()):>14} "
                  f"{int(u.notna().sum()):>16} {_differs(g, u):>7} "
                  f"{moved:>26} {str(_bit_equal(g, gn)):>13}")
    print()
    print("G4 Degenerate frames raise nothing and a short frame is refused.")
    print()
    idx = date_range("2020-01-01", periods=40, freq="D")
    for label, maker in (
            ("all NaN", lambda: Series(np.full(40, np.nan), index=idx)),
            ("all zero", lambda: Series(np.zeros(40), index=idx)),
            ("all +inf", lambda: Series(np.full(40, np.inf), index=idx))):
        s = maker()
        col = sk_fcb_pos(s, s.copy(), s.copy())
        print(f"{label:>10}: fired {int(col.notna().sum())}, "
              f"name {col.name}")
    short = Series(np.arange(MIN_BARS - 1, dtype=float))
    print(f"{MIN_BARS - 1} bars (MIN_BARS - 1): "
          f"{sk_fcb_pos(short, short.copy(), short.copy())}")
    print()
    print("G5 NOT guarded, and stated rather than hidden: a frame whose")
    print("prices live hundreds of orders of magnitude apart. The quotient")
    print("has the factor cancel, so the cross-scale overflow the sibling")
    print("width has does NOT happen here -- measured, not assumed.")
    print()
    big = Series(np.full(60, 1e+300), index=date_range("2020-01-01",
                                                       periods=60, freq="D"))
    rng = np.random.default_rng(5)
    hb = big * (1.0 + 0.01 * rng.random(60))
    lb = big * (1.0 - 0.01 * rng.random(60))
    cb = Series(np.full(60, 1e-300), index=big.index)
    col = sk_fcb_pos(hb, lb, cb)
    v = col.to_numpy()
    print(f"high/low 1e+300, close 1e-300: fired {int(col.notna().sum())}, "
          f"non-finite {int((~np.isfinite(v) & ~np.isnan(v)).sum())}, "
          f"min {np.nanmin(v):.6g}, max {np.nanmax(v):.6g}")


def section_H():
    _head("H The hand frame: an INVERTED band, bar by bar")
    print("§C4 counts the `den < 0` bars; this is the mechanism. A high")
    print("fractal confirms early and a LOW fractal confirms later at a")
    print("level ABOVE it, so `upper - lower` goes negative and the")
    print("position scale flips.")
    print()
    idx = date_range("2020-01-01", periods=16, freq="D")
    high = Series([10.0, 10.5, 13.0, 10.4, 10.3,
                   20.0, 20.5, 21.0, 21.5, 22.0,
                   22.5, 23.0, 23.5, 24.0, 24.5, 25.0], index=idx)
    low = Series([9.0, 9.5, 9.4, 9.3, 9.2,
                  19.0, 19.5, 18.0, 19.6, 19.7,
                  19.8, 19.9, 20.0, 20.1, 20.2, 20.3], index=idx)
    close = Series([9.5, 10.0, 11.0, 10.0, 9.8,
                    19.5, 20.0, 19.0, 20.5, 21.0,
                    21.5, 22.0, 22.5, 23.0, 23.5, 24.0], index=idx)
    col = sk_fcb_pos(high, low, close)
    up = _last_fractal(high, SPAN, True)
    lo = _last_fractal(low, SPAN, False)
    print(f"{'bar':>4} {'high':>7} {'low':>7} {'close':>7} {'upper':>7} "
          f"{'lower':>7} {'den':>8} {'SK_FCB_POS':>12}")
    for i in range(col.size):
        val, u, d = col.iloc[i], up.iloc[i], lo.iloc[i]
        den = u - d
        print(f"{i:>4} {high.iloc[i]:>7.2f} {low.iloc[i]:>7.2f} "
              f"{close.iloc[i]:>7.2f} "
              f"{('NaN' if np.isnan(u) else f'{u:.2f}'):>7} "
              f"{('NaN' if np.isnan(d) else f'{d:.2f}'):>7} "
              f"{('NaN' if np.isnan(den) else f'{den:.2f}'):>8} "
              f"{('NaN' if np.isnan(val) else f'{val:.4f}'):>12}")
    print()
    print("A COLLAPSED band, for the other half of §C4: the fractal low")
    print("confirms at exactly the fractal high's level, so `den == 0`, the")
    print("quotient is +-inf and the bar is EMPTIED. The column stops firing")
    print("at bar 11 while the sibling width reads exactly 0.0 there -- the")
    print("difference between a divisor and a numerator, on one frame.")
    print()
    idx2 = date_range("2020-01-01", periods=16, freq="D")
    h2 = Series([10.0, 10.0, 12.0, 10.0, 10.0, 10.0, 10.0, 14.0,
                 14.0, 13.0, 14.0, 14.0, 10.0, 10.0, 10.0, 10.0], index=idx2)
    l2 = Series([9.0, 9.0, 9.0, 8.0, 9.0, 9.0, 9.0, 13.0,
                 13.0, 12.0, 13.0, 13.0, 9.0, 9.0, 9.0, 9.0], index=idx2)
    c2 = (h2 + l2) / 2.0
    col2 = sk_fcb_pos(h2, l2, c2)
    wid2 = sk_fcb_width(h2, l2, c2)
    up2 = _last_fractal(h2, SPAN, True)
    lo2 = _last_fractal(l2, SPAN, False)
    print(f"{'bar':>4} {'high':>7} {'low':>7} {'close':>7} {'upper':>7} "
          f"{'lower':>7} {'den':>8} {'SK_FCB_POS':>12} {'width':>8}")
    for i in range(col2.size):
        val, u, d = col2.iloc[i], up2.iloc[i], lo2.iloc[i]
        den = u - d
        w = wid2.iloc[i]
        print(f"{i:>4} {h2.iloc[i]:>7.2f} {l2.iloc[i]:>7.2f} "
              f"{c2.iloc[i]:>7.2f} "
              f"{('NaN' if np.isnan(u) else f'{u:.2f}'):>7} "
              f"{('NaN' if np.isnan(d) else f'{d:.2f}'):>7} "
              f"{('NaN' if np.isnan(den) else f'{den:.2f}'):>8} "
              f"{('NaN' if np.isnan(val) else f'{val:.4f}'):>12} "
              f"{('NaN' if np.isnan(w) else f'{w:.4f}'):>8}")


def section_L():
    _head("L The column is a STEP function's quotient, not a smooth one")
    print("Both legs change only when a fractal confirms, so between")
    print("confirmations the column moves only because `close` does, and it")
    print("moves AFFINELY in close. Steps per leg, and the longest stretch")
    print("one leg is held.")
    print()
    print(f"{'frame':>13} {'upper steps':>12} {'lower steps':>12} "
          f"{'longest upper':>14} {'longest lower':>14}")
    for name in NAMES:
        h, l, _ = FRAMES[name]()
        out = []
        for x, upper in ((h, True), (l, False)):
            leg = _last_fractal(x.where(np.isfinite(x)), SPAN,
                                upper).to_numpy()
            changed = np.r_[False, (leg[1:] != leg[:-1]) & ~np.isnan(leg[1:])]
            steps = int(changed.sum())
            longest, cur = 0, 0
            for i in range(leg.size):
                if changed[i]:
                    longest = max(longest, cur)
                    cur = 1
                elif not np.isnan(leg[i]):
                    cur += 1
            longest = max(longest, cur)
            out.append((steps, longest))
        print(f"{name:>13} {out[0][0]:>12} {out[1][0]:>12} "
              f"{out[0][1]:>14} {out[1][1]:>14}")
    print()
    print("Within one stretch the column is affine in close with slope")
    print("1 / den, so its rank correlation against close on that stretch is")
    print("exactly +1 when den > 0 and -1 when den < 0. Measured on the")
    print("longest `den > 0` stretch and the longest `den < 0` stretch of")
    print("each frame that has both:")
    print()
    print(f"{'frame':>13} {'stretch':>8} {'bars':>5} {'rho vs close':>13}")
    for name in FIRING:
        cen = _census(FRAMES[name]())
        _, _, c = FRAMES[name]()
        col, den, ready = cen["col"], cen["den"], cen["ready"]
        for sign, flag in (("den>0", ready & (den > 0.0)),
                           ("den<0", ready & (den < 0.0))):
            # the longest run of constant legs within the sign's bars
            key = (cen["upper"].astype(str) + "|"
                   + cen["lower"].astype(str)).where(flag)
            best, best_rho = 0, float("nan")
            for _, grp in key.dropna().groupby(key.dropna()):
                if grp.size > best:
                    sub = col.loc[grp.index]
                    rho = _spearman(sub, c.loc[grp.index])
                    if not np.isnan(rho):
                        best, best_rho = grp.size, rho
            if best:
                print(f"{name:>13} {sign:>8} {best:>5} {best_rho:>13.4f}")


def section_W():
    _head("W The five wiring touch points")
    import pandas_ta as ta
    frame = _walk(n=400)
    h, l, c = frame
    df = DataFrame({"open": c, "high": h, "low": l, "close": c,
                    "volume": Series(np.full(c.size, 1e6), index=c.index)})
    col = sk_fcb_pos(*frame)
    print(f"1 module       : pandas_ta/momentum/sk_fcb_pos.py")
    print(f"2 package      : {hasattr(ta.momentum, 'sk_fcb_pos')}")
    print(f"3 Category     : "
          f"{'sk_fcb_pos' in ta.Category['momentum']} "
          f"(momentum has {len(ta.Category['momentum'])})")
    print(f"4 accessor     : {hasattr(df.ta, 'sk_fcb_pos')}")
    print(f"5 tests        : tests/test_sk_fcb_pos.py")
    print()
    acc = df.ta.sk_fcb_pos()
    print(f"column name    : {col.name}")
    print(f"category tag   : {col.category}")
    print(f"accessor equal : {_bit_equal(col, acc)}")
    print(f"accessor name  : {acc.name}")
    print()
    print("`offset` and `fillna`, the two kwargs the signature carries:")
    off = sk_fcb_pos(*frame, offset=2)
    print(f"offset=2 shifts: "
          f"{_bit_equal(off.iloc[2:].reset_index(drop=True), col.iloc[:-2].reset_index(drop=True))}")
    filled = sk_fcb_pos(*frame, fillna=-9.0)
    print(f"fillna=-9.0    : {int((filled == -9.0).sum())} bars filled, "
          f"{int(col.isna().sum())} were NaN")
    print()
    print("The dictionary cut. `docs/gen_indicator_dictionary.py`'s `desc`")
    print("shows `d[:150].rsplit(' ', 1)[0]` of the docstring's first")
    print("paragraph, so a paragraph over 150 characters loses a WHOLE word.")
    print("The generator's own `desc` is lifted out of its source with `ast`")
    print("here rather than retyped, and the sentence is grown one character")
    print("at a time until it loses one, so the slack is measured.")
    print()
    import ast
    import re
    path = Path(__file__).resolve().with_name("gen_indicator_dictionary.py")
    tree = ast.parse(path.read_text(encoding="utf-8"))
    node = next(n for n in tree.body
                if isinstance(n, ast.FunctionDef) and n.name == "desc")
    ns = {"re": re}
    exec(compile(ast.Module(body=[node], type_ignores=[]),
                 "<gen_indicator_dictionary.desc>", "exec"), ns)
    desc = ns["desc"]
    body = []
    for line in sk_fcb_pos.__doc__.splitlines()[1:]:
        if line.strip():
            body.append(line.strip())
        elif body:
            break
    paragraph = " ".join(body)
    slack = 0
    while desc({"desc": paragraph + "x" * slack}) == paragraph + "x" * slack:
        slack += 1
        if slack > 400:
            break
    print(f"paragraph      : {len(paragraph)} characters")
    print(f"survives whole : {desc({'desc': paragraph}) == paragraph}")
    print(f"slack          : {slack - 1} more characters before a word goes")
    print(f"shown as       : {desc({'desc': paragraph})!r}")


def section_Z():
    _head("Z Cost")
    print("Four rolling passes, four shifts, two ffills, two subtractions,")
    print("one division and one replace -- no Python loop, so time and")
    print("memory are linear in bars.")
    print()
    print(f"{'bars':>10} {'peak MB':>10} {'peak MB (2nd)':>14} "
          f"{'ms':>8} {'ms (2nd)':>10}")
    for n in (100_000, 400_000):
        frame = _walk(n=n)
        peaks = []
        for _ in range(2):
            tracemalloc.start()
            sk_fcb_pos(*frame)
            peaks.append(tracemalloc.get_traced_memory()[1] / 1e6)
            tracemalloc.stop()
        times = [timeit.timeit(lambda: sk_fcb_pos(*frame), number=3) / 3 * 1e3
                 for _ in range(2)]
        print(f"{n:>10} {peaks[0]:>10.1f} {peaks[1]:>14.1f} "
              f"{times[0]:>8.1f} {times[1]:>10.1f}")
    print()
    print("⚠ The wall clock is DISCLOSED, not claimed: two invocations of")
    print("the same section already disagree, and both are printed above so")
    print("the spread is visible rather than averaged away.")


SECTIONS = {
    "A1": section_A1, "A2": section_A2, "A3": section_A3, "A4": section_A4,
    "B": section_B, "B1": section_B1, "B2": section_B2,
    "C": section_C, "C2": section_C2, "C3": section_C3, "C4": section_C4,
    "D": section_D, "F": section_F, "G": section_G, "H": section_H,
    "L": section_L, "W": section_W, "Z": section_Z,
}


if __name__ == "__main__":
    want = [a.upper() for a in sys.argv[1:]] or list(SECTIONS)
    for key in want:
        if key not in SECTIONS:
            raise SystemExit(f"unknown section {key!r};"
                             f" pick from {list(SECTIONS)}")
        SECTIONS[key]()
