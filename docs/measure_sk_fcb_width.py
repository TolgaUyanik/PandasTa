# -*- coding: utf-8 -*-
"""SK-FCB-WIDTH (PandasTa issue #107): every number in
`docs/SkFcbWidthMeasured.md`.

    python docs/measure_sk_fcb_width.py          # every section, in order
    python docs/measure_sk_fcb_width.py A1 D     # named sections only

One section per gate limb, printed and never derived: the repo's dominant
defect is "a claim written before it was measured", so this file is the only
place a figure in the receipt, the module docstring or
`tests/test_sk_fcb_width.py` may come from.

    upper[T]       = level of the last CONFIRMED fractal high, held forward
    lower[T]       = level of the last CONFIRMED fractal low, held forward
    SK_FCB_WIDTH   = (upper - lower) / close

A fractal high is centred on a bar whose high beats all `SPAN` highs on each
side strictly, and it is confirmed `SPAN` bars later.

⚠ The millisecond figures of §Z are this machine's and this run's. Nothing
else here depends on the machine, and `docs/measure_sk_fcb_width_cpu.py`
re-runs the sections under numpy's reduced CPU dispatch to show which
figures move.
"""
import importlib.util
import sys
import timeit
import tracemalloc
from pathlib import Path

import numpy as np
import pandas as pd
from pandas import DataFrame, Series, date_range

from pandas_ta.trend.chop import chop
from pandas_ta.volatility.donchian import donchian
from pandas_ta.volatility.massi import massi
from pandas_ta.volatility.natr import natr
from pandas_ta.volatility.rvi import rvi
from pandas_ta.volatility.sk_fcb_width import (MIN_BARS, SPAN, _last_fractal,
                                               sk_fcb_width)
from pandas_ta.volatility.true_range import true_range

N = 1500
LEVEL = 100.0
#: The blind causality sweep's 36 perturbation points.
OFFSETS = list(range(N - 36, N))
#: Where §G plants a bad bar.
PLANT = 700


# ------------------------------------------------------------------ frames
# Same builders and seeds as `tests/test_sk_fcb_width.py`, so a number in
# this file and a number in that one are the same measurement. The first
# seven are `tests/test_j_acosc.py`'s, unchanged, so the frame set is shared
# across ports; `coarse` is the eighth and is this indicator's own (§C2).


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

    This frame exists for one reason, and it is this indicator's central
    risk rather than a decoration: the fractal predicate is STRICT, so a
    tie on either side of the centre bar destroys the fractal. On a
    continuous frame ties never happen; on a real tick grid they do, and
    FVGDEAD (see `CLAUDE.md`) is this repo's record of a column whose
    behaviour on synthetic continuous floats said nothing about its
    behaviour on rounded prices. §C2 measures what the rounding costs.
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


def _oracle(high, low, close, lag=SPAN):
    """The source formula by explicit loops, sharing no code with the
    module: `upper - lower` over close."""
    h = high.to_numpy(dtype=float)
    l = low.to_numpy(dtype=float)
    bear, bull = _fractals(h, l)
    up, lo = _carry(bear, bull, lag)
    return Series((up - lo) / close.to_numpy(dtype=float), index=close.index)


def _prototype(high, low, close):
    """`docs/issues/screen/ind_screen_r2.py`, candidate `sk_fcb_width`,
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

        @cand("sk_fcb_width", ...)
        def _(o, h, l, c, v):
            return (last_fractal(h, 2, True) - last_fractal(l, 2, False)) / c
    """
    def last_fractal(x, span, high):
        ref = x.shift(span)
        left = (x.shift(span + 1).rolling(span).max() if high
                else x.shift(span + 1).rolling(span).min())
        right = x.rolling(span).max() if high else x.rolling(span).min()
        is_f = ((ref > left) & (ref > right) if high
                else (ref < left) & (ref < right))
        return ref.where(is_f).ffill()
    return (last_fractal(high, 2, True) - last_fractal(low, 2, False)) / close


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
    return (last_fractal(high, 2, True) - last_fractal(low, 2, False)) / close


def _close_ends(high, low, close):
    """The reading NOT taken: `EndType.Close`, Skender's other option, which
    judges and returns the CLOSE instead of the high/low."""
    up = _last_fractal(close, SPAN, True)
    lo = _last_fractal(close, SPAN, False)
    return (up - lo) / close


# ----------------------------------------------------------------- mutants

SOURCE = Path(__file__).resolve().parents[1] / "pandas_ta" / "volatility" \
    / "sk_fcb_width.py"

#: (label, old text, new text). Edits to the SHIPPED source, read off disk.
CAUSALITY_MUTANTS = [
    # Skender's own index: the confirmed level moved back onto its centre
    # bar. §A3 builds the same reading independently, and
    # `tests/test_sk_fcb_width.py` asserts the two agree, so this mutant is
    # the documented alternative reading and not an invented edit.
    ("centre-read", "    return ref.where(is_fractal).ffill()",
     "    return ref.where(is_fractal).shift(-span).ffill()"),
    ("right-window-lead", "        right = x.rolling(span).max()",
     "        right = x.shift(-1).rolling(span).max()"),
    ("band-bfill", "    return ref.where(is_fractal).ffill()",
     "    return ref.where(is_fractal).bfill()"),
    ("output-early", "    width = (upper - lower) / c",
     "    width = ((upper - lower) / c).shift(-1)"),
    ("divisor-lead", "    width = (upper - lower) / c",
     "    width = (upper - lower) / c.shift(-1)"),
]
#: Not causality mutants: the guards, removed, to price what they buy.
CLOSE_GUARD_OFF = (
    "c = close.where(np.isfinite(close) & (close >= np.finfo(float).tiny))",
    "c = close")
HL_GUARD_OFF = ("    h = high.where(np.isfinite(high))\n"
                "    l = low.where(np.isfinite(low))",
                "    h = high\n    l = low")


def _mutant(old, new):
    src = SOURCE.read_text(encoding="utf-8")
    assert src.count(old) == 1, f"{old!r} occurs {src.count(old)} times"
    ns = {}
    exec(compile(src.replace(old, new), "<mutant>", "exec"), ns)
    return ns["sk_fcb_width"]


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
    once -- §B prints what each costs. The same factor multiplies high,
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


def _head(title):
    print()
    print("=" * 72)
    print(title)
    print("=" * 72)


# ---------------------------------------------------------------- sections


def section_A1():
    _head("A1 Gate A -- the source formula by explicit loops")
    print("Skender's `Fractal` double loop plus `Fcb`'s roll-forward,")
    print("transcribed and sharing no code with the module.")
    print()
    print(f"{'frame':>13} {'fired':>6} {'masks':>6} {'max |diff|':>12} "
          f"{'max |rel|':>12} {'bit-equal':>10}")
    for name in NAMES:
        frame = FRAMES[name]()
        col, orc = sk_fcb_width(*frame), _oracle(*frame)
        masks = bool((col.isna() == orc.isna()).all())
        print(f"{name:>13} {int(col.notna().sum()):>6} {str(masks):>6} "
              f"{_abs(col, orc):>12.3e} {_rel(col, orc):>12.3e} "
              f"{str(_bit_equal(col, orc)):>10}")


def section_A2():
    _head("A2 Gate A -- the screen prototype, bit for bit")
    print("The prototype the 2026-10-24 screen measured at Gate E, retyped.")
    print("It carries NO guards, so bit-equality is claimed on clean frames")
    print("only; §G shows where the guards make the two differ.")
    print()
    print(f"{'frame':>13} {'fired':>6} {'bit-equal':>10} {'max |diff|':>12}")
    for name in NAMES:
        frame = FRAMES[name]()
        col, proto = sk_fcb_width(*frame), _prototype(*frame)
        print(f"{name:>13} {int(col.notna().sum()):>6} "
              f"{str(_bit_equal(col, proto)):>10} {_abs(col, proto):>12.3e}")


def section_A3():
    _head("A3 The index Skender returns a fractal at, and the lag this port"
          " adds")
    print("Skender's `Fractal` puts the level ON the centre bar. Read there,")
    print("the band would be knowable SPAN bars before its right-hand bars")
    print("exist, so this port reads it SPAN bars later -- which is what the")
    print("screen prototype does, and the only reading that passes Gate B.")
    print("Both are measured here so the divergence is a number, not a")
    print("preference.")
    print()
    print(f"{'frame':>13} {'both fire':>10} {'differ':>7} {'share':>7} "
          f"{'spearman':>9} {'sweep':>6}")
    for name in FIRING:
        frame = FRAMES[name]()
        col, centre = sk_fcb_width(*frame), _centre_reading(*frame)
        m = col.notna() & centre.notna()
        n_both = int(m.sum())
        differ = int((col[m] != centre[m]).sum())
        share = n_both - differ
        print(f"{name:>13} {n_both:>10} {differ:>7} {share:>7} "
              f"{_spearman(col, centre):>9.4f} "
              f"{_sweep(_centre_reading, frame):>6}")
    print()
    print("`sweep` is §B's two-futures sweep run on the CENTRE reading, out")
    print("of 36. It is not 36 of 36 and cannot be: the look-ahead reaches")
    print("exactly SPAN bars and only shows when a fractal decision within")
    print("SPAN bars of the boundary flips, which is data-dependent. That")
    print("is why Gate B is the mutant comparison and not this sweep alone.")


def section_A4():
    _head("A4 The other readings not taken")
    print("Spearman of each against the shipped column, over the bars both")
    print("fire on, and the count of bars where they differ at all.")
    print()
    variants = {"non-strict (>=)": _non_strict, "EndType.Close": _close_ends}
    for label, fn in variants.items():
        print(f"-- {label}")
        print(f"{'frame':>13} {'col fires':>10} {'alt fires':>10} "
              f"{'differ':>7} {'spearman':>9}")
        for name in FIRING:
            frame = FRAMES[name]()
            col, alt = sk_fcb_width(*frame), fn(*frame)
            m = col.notna() & alt.notna()
            print(f"{name:>13} {int(col.notna().sum()):>10} "
                  f"{int(alt.notna().sum()):>10} "
                  f"{int((col[m] != alt[m]).sum()):>7} "
                  f"{_spearman(col, alt):>9.4f}")
        print()


def section_B():
    _head("B Gate B -- causality, two-futures sweep and read-off mutants")
    print(f"For each of the 36 offsets {OFFSETS[0]}..{OFFSETS[-1]} the frame")
    print("is split into one shared past and two wholly different futures")
    print("(see `_futures`), and the question is whether any bar < j moved.")
    print("Out of 36.")
    print()
    print(f"{'frame':>13} {'module':>7} "
          + " ".join(f"{label:>18}" for label, _, _ in CAUSALITY_MUTANTS))
    for name in NAMES:
        frame = FRAMES[name]()
        row = [f"{_sweep(sk_fcb_width, frame):>7}"]
        for _, old, new in CAUSALITY_MUTANTS:
            row.append(f"{_sweep(_mutant(old, new), frame):>18}")
        print(f"{name:>13} " + " ".join(row))
    print()
    print("⚠ A mutant's count is NOT 36 of 36 and cannot be, which is the")
    print("one thing to understand about Gate B here: three of these five")
    print("look ahead by exactly SPAN bars through a COMPARISON, so the")
    print("edit is invisible at an offset where the fractal decisions")
    print("within SPAN bars of the boundary happen to come out the same")
    print("either way. The gate is therefore the pair of statements below")
    print("-- the module at 0, and each mutant BOTH live against the module")
    print("and caught somewhere -- and not a 36 of 36 headline.")
    print()
    print("The module alone, swept over every bar but bar 0 of each frame")
    print("-- 1,499 of 1,500, where a split at bar 0 has no prefix -- not")
    print("36, because 0 from a weak detector would be weak evidence:")
    print()
    for name in NAMES:
        frame = FRAMES[name]()
        dense = list(range(1, frame[2].size))
        print(f"{name:>13} caught {_sweep(sk_fcb_width, frame, dense):>5} "
              f"of {len(dense):>5} offsets")
    print()
    print("Each mutant is live: how far it differs from the module on the")
    print("unperturbed `walk` frame.")
    print()
    frame = FRAMES["walk"]()
    base = sk_fcb_width(*frame)
    for label, old, new in CAUSALITY_MUTANTS:
        mut = _mutant(old, new)(*frame)
        m = base.notna() & mut.notna()
        same = int((base[m] == mut[m]).sum())
        moved = int((base[m] != mut[m]).sum())
        print(f"{label:>18} both fire {int(m.sum()):>5}  same {same:>5}  "
              f"moved {moved:>5}  max |rel| {_rel(base, mut):>10.3e}")


def _exposed_offsets(x, span=SPAN, lo=None, hi=None):
    """The offsets at which the `right-window-lead` mutant's extra bar is
    actually EXPOSED, worked out from the edit rather than guessed.

    That mutant reads `right = x.shift(-1).rolling(span).max()`, so for a
    centre bar `j` its right window is `{j+2, j+3}` instead of
    `{j+1, j+2}`, and the verdict is still written to bar `j + span`.
    Bar `T` therefore reads `x[T+1]` and nothing later, and it is the ONLY
    bar of the prefix a split at offset `j = T + 1` can reach.

    The verdict at that centre is
    `ref > max(left) and ref > max(x[j-1], x[j] * f)` for whatever factor
    `f` a future applies, so it can be True under SOME future only if
    `ref > max(left)` and `ref > x[j-1]` -- that is,
    `x[j-3] > max(x[j-5], x[j-4], x[j-1])`, the condition below. Where it
    fails the verdict is False under EVERY future, nothing flips, and no
    perturbation of bars >= j can be caught at that offset. Necessary by
    construction, and §B2 measures it: 0 catches outside this set. That
    is why the mutant's blind count is 4 .. 9 of 36 rather than 36 of 36.
    """
    v = x.to_numpy(dtype=float)
    lo = 5 if lo is None else lo
    hi = v.size if hi is None else hi
    return [j for j in range(lo, hi)
            if v[j - 3] > max(v[j - 5], v[j - 4], v[j - 1])]


def section_B2():
    _head("B2 The weakest mutant, swept where its edit is EXPOSED")
    print("`right-window-lead` is the thinnest limb of §B: one extra bar")
    print("of right-hand window, caught on 4 .. 9 of 36 blind offsets. A")
    print("margin of 4 is not evidence, so the edit is read and the sweep")
    print("is restricted to the offsets where it can possibly show (see")
    print("`_exposed_offsets`). Dense: every offset from 5 on, which is")
    print("1,495 of each frame's 1,500 -- the first five cannot be split")
    print("points, since the condition reads back to bar j - 5.")
    print()
    label, old, new = next(m for m in CAUSALITY_MUTANTS
                           if m[0] == "right-window-lead")
    mut = _mutant(old, new)
    print(f"{'frame':>13} {'offsets':>8} {'exposed':>8} "
          f"{'caught|exposed':>15} {'caught|not':>11}")
    # Pooled, printed rather than left to the reader's arithmetic: round 3
    # of the review caught a hand-added control total that was 13 short.
    pooled = {"offsets": 0, "exposed": 0, "hit_exp": 0, "hit_not": 0}
    for name in FIRING:
        frame = FRAMES[name]()
        h = frame[0]
        n = h.size
        every = list(range(5, n))
        exposed = set(_exposed_offsets(h, lo=5, hi=n))
        hit_exp = sum(_caught_at(mut, frame, j) for j in sorted(exposed))
        hit_not = sum(_caught_at(mut, frame, j)
                      for j in every if j not in exposed)
        pooled["offsets"] += len(every)
        pooled["exposed"] += len(exposed)
        pooled["hit_exp"] += hit_exp
        pooled["hit_not"] += hit_not
        print(f"{name:>13} {len(every):>8} {len(exposed):>8} "
              f"{hit_exp:>7} of {len(exposed):<5} {hit_not:>11}")
    print(f"{'POOLED':>13} {pooled['offsets']:>8} {pooled['exposed']:>8} "
          f"{pooled['hit_exp']:>7} of {pooled['exposed']:<5} "
          f"{pooled['hit_not']:>11}")
    print(f"{'unexposed':>13} {pooled['offsets'] - pooled['exposed']:>8}")
    print()
    print("`caught|not` is the control: an offset where the extra bar is")
    print("not exposed must be uncatchable, so any number but 0 there")
    print("would mean the condition above is wrong.")
    print()
    print("Exposure is NECESSARY, not sufficient, and the misses are")
    print("classified rather than waved at: at an exposed offset the")
    print("mutant writes `x[j-3]` as the upper band on bar j-1 under one")
    print("future and keeps the carried level under the other -- so it")
    print("goes unseen on three kinds of offset, all three counted here:")
    print("the two futures' verdicts AGREE anyway (the up factor is only")
    print("[1, 4], so it need not clear `ref`), the flipped level EQUALS")
    print("the level already carried, or the column has not started firing")
    print("by bar j-1.")
    print()

    def _verdict(x, c):
        """The mutant's upper-fractal verdict at centre `c`: left window
        `{c-2, c-1}`, right window `{c+2, c+3}`."""
        v = x.to_numpy(dtype=float)
        if c - 2 < 0 or c + 3 >= v.size:
            return None
        return bool(v[c] > max(v[c - 2], v[c - 1])
                    and v[c] > max(v[c + 2], v[c + 3]))

    print(f"{'frame':>13} {'missed':>7} {'verdicts agree':>15} "
          f"{'level equal':>12} {'not fired yet':>14} {'other':>6}")
    totals = {"missed": 0, "agree": 0, "equal": 0, "unfired": 0, "other": 0}
    for name in FIRING:
        frame = FRAMES[name]()
        h = frame[0]
        v = h.to_numpy(dtype=float)
        counts = {"agree": 0, "equal": 0, "unfired": 0, "other": 0}
        missed = 0
        for j in _exposed_offsets(h, lo=5, hi=h.size):
            if _caught_at(mut, frame, j):
                continue
            missed += 1
            frame_a, frame_b = _futures(frame, j)
            if _verdict(frame_a[0], j - 3) == _verdict(frame_b[0], j - 3):
                counts["agree"] += 1
                continue
            if np.isnan(mut(*frame_a).iloc[j - 1]):
                counts["unfired"] += 1
                continue
            carried = _last_fractal(frame_a[0], SPAN, True).iloc[j - 1]
            counts["equal" if carried == v[j - 3] else "other"] += 1
        print(f"{name:>13} {missed:>7} {counts['agree']:>15} "
              f"{counts['equal']:>12} {counts['unfired']:>14} "
              f"{counts['other']:>6}")
        totals["missed"] += missed
        for key in ("agree", "equal", "unfired", "other"):
            totals[key] += counts[key]
    print(f"{'POOLED':>13} {totals['missed']:>7} {totals['agree']:>15} "
          f"{totals['equal']:>12} {totals['unfired']:>14} "
          f"{totals['other']:>6}")


def section_C():
    _head("C Gate C -- reachability, on synthetic frames")
    print("Real-data counts are owed with the Gate E run; these are the")
    print("synthetic frames this file builds.")
    print()
    print(f"{'frame':>13} {'bars':>5} {'fired':>6} {'first':>6} "
          f"{'distinct':>9} {'min':>10} {'max':>10} {'< 0':>6} {'== 0':>6}")
    for name in NAMES:
        frame = FRAMES[name]()
        col = sk_fcb_width(*frame)
        v = col.dropna()
        first = int(np.flatnonzero(col.notna().to_numpy())[0]) if v.size \
            else -1
        print(f"{name:>13} {col.size:>5} {v.size:>6} {first:>6} "
              f"{v.nunique():>9} "
              f"{(v.min() if v.size else float('nan')):>10.4f} "
              f"{(v.max() if v.size else float('nan')):>10.4f} "
              f"{int((v < 0).sum()):>6} {int((v == 0).sum()):>6}")
    print()
    print("The band is a STEP function and the close is not, so the column")
    print("moves every bar while the band itself only moves when a fractal")
    print("confirms. Both counted, plus how stale each leg gets.")
    print()
    print(f"{'frame':>13} {'upper steps':>12} {'lower steps':>12} "
          f"{'max age up':>11} {'max age lo':>11} {'mean age':>9}")
    for name in FIRING:
        h, l, c = FRAMES[name]()
        up = _last_fractal(h.where(np.isfinite(h)), SPAN, True)
        lo = _last_fractal(l.where(np.isfinite(l)), SPAN, False)
        ages = []
        for leg in (up, lo):
            fired = leg.notna().to_numpy()
            changed = np.r_[False, leg.to_numpy()[1:] != leg.to_numpy()[:-1]]
            age = np.full(leg.size, np.nan)
            last = -1
            for t in range(leg.size):
                if changed[t] and fired[t]:
                    last = t
                if last >= 0:
                    age[t] = t - last
            ages.append(age)
        n_up = int(np.r_[False, (up.to_numpy()[1:] != up.to_numpy()[:-1])
                         & ~np.isnan(up.to_numpy()[1:])].sum())
        n_lo = int(np.r_[False, (lo.to_numpy()[1:] != lo.to_numpy()[:-1])
                         & ~np.isnan(lo.to_numpy()[1:])].sum())
        both = np.where(np.isnan(ages[0]) | np.isnan(ages[1]), np.nan,
                        np.maximum(ages[0], ages[1]))
        print(f"{name:>13} {n_up:>12} {n_lo:>12} "
              f"{np.nanmax(ages[0]):>11.0f} {np.nanmax(ages[1]):>11.0f} "
              f"{np.nanmean(both):>9.2f}")
    print()
    print("And the divisor's own contribution, counted rather than")
    print("reasoned: bars where NEITHER band leg moved and the column")
    print("moved anyway, which can only be the close.")
    print()
    print(f"{'frame':>13} {'band held':>10} {'of which col moved':>19} "
          f"{'col held too':>13}")
    for name in FIRING:
        h, l, c = FRAMES[name]()
        up = _last_fractal(h.where(np.isfinite(h)), SPAN, True)
        lo = _last_fractal(l.where(np.isfinite(l)), SPAN, False)
        col = sk_fcb_width(h, l, c)
        u, d, k = up.to_numpy(), lo.to_numpy(), col.to_numpy()
        held = (u[1:] == u[:-1]) & (d[1:] == d[:-1]) & ~np.isnan(k[1:]) \
            & ~np.isnan(k[:-1])
        moved = held & (k[1:] != k[:-1])
        print(f"{name:>13} {int(held.sum()):>10} {int(moved.sum()):>19} "
              f"{int(held.sum()) - int(moved.sum()):>13}")


def section_C2():
    _head("C2 The strict predicate against a tick grid")
    print("`>` and not `>=`, so a TIE on either side of the centre bar")
    print("destroys the fractal. Continuous floats never tie; rounded")
    print("prices do. Fractals found, per leg, on the same walk at four")
    print("tick sizes.")
    print()
    print(f"{'tick':>10} {'upper fractals':>15} {'lower fractals':>15} "
          f"{'fired':>6} {'first':>6}")
    for tick in (0.0, 0.01, 0.5, 2.0):
        h, l, c = (_walk() if tick == 0.0 else _coarse(tick=tick))
        col = sk_fcb_width(h, l, c)
        up = _last_fractal(h, SPAN, True)
        lo = _last_fractal(l, SPAN, False)
        n_up = int(np.r_[False, (up.to_numpy()[1:] != up.to_numpy()[:-1])
                         & ~np.isnan(up.to_numpy()[1:])].sum())
        n_lo = int(np.r_[False, (lo.to_numpy()[1:] != lo.to_numpy()[:-1])
                         & ~np.isnan(lo.to_numpy()[1:])].sum())
        v = col.dropna()
        first = int(np.flatnonzero(col.notna().to_numpy())[0]) if v.size \
            else -1
        label = "none" if tick == 0.0 else f"{tick}"
        print(f"{label:>10} {n_up:>15} {n_lo:>15} {v.size:>6} {first:>6}")
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


def section_C3():
    _head("C3 What the REST of the volatility bucket does on a flat price")
    print("§C says this column fires 0 of 1,500 bars on `flat`. Whether")
    print("that is unusual for the bucket is a claim about 36 other")
    print("indicators, so it is RUN here rather than asserted: every name")
    print("in Category['volatility'] on a flat OHLCV frame, through its")
    print("`df.ta` accessor at defaults, column by column.")
    print()
    import pandas_ta as ta
    h, l, c = _flat(n=600)
    df = pd.DataFrame({"open": c, "high": h, "low": l, "close": c,
                       "volume": Series(np.full(c.size, 1e6), index=c.index)})
    buckets = {"all NaN": [], "all 0.0": [], "other": [], "raised": []}
    print(f"{'indicator':>22} {'column':>34} {'fired':>6} {'zeros':>6}")
    for name in sorted(ta.Category["volatility"]):
        try:
            out = getattr(df.ta, name)()
        except Exception as exc:                       # noqa: BLE001
            buckets["raised"].append(f"{name} ({type(exc).__name__})")
            print(f"{name:>22} {'-- raised --':>34} "
                  f"{type(exc).__name__:>13}")
            continue
        frame = out.to_frame() if isinstance(out, Series) else out
        for col in frame.columns:
            s = frame[col]
            fired = int(s.notna().sum())
            zeros = int((s.dropna() == 0.0).sum())
            key = ("all NaN" if fired == 0 else
                   "all 0.0" if zeros == fired else "other")
            buckets[key].append(f"{name}:{col}")
            print(f"{name:>22} {col:>34} {fired:>6} {zeros:>6}")
    print()
    for key in ("all NaN", "all 0.0", "other", "raised"):
        print(f"{key:>9}: {len(buckets[key])}  {sorted(buckets[key])}")


def section_D():
    _head("D Gate D -- scale invariance")
    print("x8 and x64 are exact binary factors: the fractal SELECTION is")
    print("comparison-only, and (a*f - b*f) / (c*f) rounds to the same")
    print("double as (a - b) / c when f is exact, so bit-identity is")
    print("expected and is asserted rather than hoped for.")
    print()
    print(f"{'frame':>13} {'fired':>6} {'x8 bit-equal':>13} "
          f"{'x64 bit-equal':>14}")
    for name in NAMES:
        frame = FRAMES[name]()
        col = sk_fcb_width(*frame)
        print(f"{name:>13} {int(col.notna().sum()):>6} "
              f"{str(_bit_equal(col, sk_fcb_width(*_scaled(frame, 8)))):>13} "
              f"{str(_bit_equal(col, sk_fcb_width(*_scaled(frame, 64)))):>14}")
    print()
    print("Inexact factors. Two things can move: the last bits of the")
    print("division, and -- the risk peculiar to this column -- the fractal")
    print("SELECTION, if a rescale collapses two distinct neighbouring")
    print("prices onto one double and so destroys a strict inequality.")
    print("`sel flips` counts bars where the selected band level changed")
    print("RELATIVE to the rescale, which is the second failure mode.")
    print()
    print(f"{'frame':>13} {'factor':>10} {'masks':>6} {'max |rel|':>11} "
          f"{'sel flips':>10}")
    for name in FIRING:
        frame = FRAMES[name]()
        base = sk_fcb_width(*frame)
        h, l, _ = frame
        up0 = _last_fractal(h, SPAN, True)
        lo0 = _last_fractal(l, SPAN, False)
        for factor in (10.0, 3.7, 0.1, 1.0000001):
            other = sk_fcb_width(*_scaled(frame, factor))
            masks = bool((base.isna() == other.isna()).all())
            up1 = _last_fractal(h * factor, SPAN, True) / factor
            lo1 = _last_fractal(l * factor, SPAN, False) / factor
            flips = int((~np.isclose(up0.to_numpy(), up1.to_numpy(),
                                     rtol=1e-9, atol=0.0, equal_nan=True)).sum()
                        + (~np.isclose(lo0.to_numpy(), lo1.to_numpy(),
                                       rtol=1e-9, atol=0.0,
                                       equal_nan=True)).sum())
            print(f"{name:>13} {factor:>10} {str(masks):>6} "
                  f"{_rel(base, other):>11.3e} {flips:>10}")
    print()
    print("The same x8/x64 run REPEATED at three price levels, so the")
    print("invariance is not an artefact of level 100.")
    print()
    print(f"{'level':>10} {'fired':>6} {'x8':>6} {'x64':>6} {'max |value|':>14}")
    for level in (1e-6, 1e+6, 1e+100):
        frame = _walk(level=level)
        col = sk_fcb_width(*frame)
        print(f"{level:>10.0e} {int(col.notna().sum()):>6} "
              f"{str(_bit_equal(col, sk_fcb_width(*_scaled(frame, 8)))):>6} "
              f"{str(_bit_equal(col, sk_fcb_width(*_scaled(frame, 64)))):>6} "
              f"{col.abs().max():>14.17g}")
    print()
    print("0 < fires < n, the constant-column guard, per frame: see §C.")


def section_F():
    _head("F Non-redundancy against the fork's own volatility columns")
    print("⚠ SYNTHETIC and a disclosure, not a gate: Gate E measures 687")
    print("engine comparators over 89 real BIST frames, and none of them is")
    print("a pandas_ta port. The screen put this prototype's nearest")
    print("comparator at natr, 0.6104 pooled.")
    print()
    cols = {}
    for name in FIRING:
        h, l, c = FRAMES[name]()
        col = sk_fcb_width(h, l, c)
        don = donchian(h, l)
        others = {
            "natr:NATR_14": natr(h, l, c),
            "massi:MASSI_9_25": massi(h, l),
            "chop:CHOP_14_1_100": chop(h, l, c),
            "rvi:RVI_14": rvi(c, h, l),
            "true_range/close (invented)": true_range(h, l, c) / c,
            "donchian width/close (invented)":
                (don.iloc[:, 2] - don.iloc[:, 0]) / c,
        }
        for label, other in others.items():
            cols.setdefault(label, []).append(_spearman(col, other))
    print("⚠ SEVEN frames, not eight: `flat` never fires, so it has no")
    print("Spearman at all. Ordered by max |rho|, worst first -- the metric")
    print("the screen, the issue and the other receipts use.")
    print()
    print(f"{'comparator':>33} {'max |rho|':>9} "
          + " ".join(f"{n[:9]:>9}" for n in FIRING))
    for label, values in sorted(cols.items(),
                                key=lambda kv: -np.nanmax(np.abs(kv[1]))):
        print(f"{label:>33} {np.nanmax(np.abs(values)):>9.4f} "
              + " ".join(f"{v:>9.4f}" for v in values))
    print()
    print("The SIGNED maximum, which is NOT the metric above and which an")
    print("earlier draft of this section sorted by. Printed rather than")
    print("described, so the two orderings can be compared without anyone")
    print("retyping either:")
    print()
    print(f"{'comparator':>33} {'max rho':>9}")
    for label, values in sorted(cols.items(),
                                key=lambda kv: -np.nanmax(kv[1])):
        print(f"{label:>33} {np.nanmax(values):>9.4f}")
    print()
    print("Why the synthetic figures above are so far under the screen's")
    print("0.6104 is NOT explained by this file, and the obvious guess is")
    print("tested here and REFUTED: 'on a continuous frame the band is")
    print("re-drawn every few bars, so the close in the divisor carries")
    print("the column'. Spearman against 1/close and against the band")
    print("width in PRICE units (upper - lower) says the opposite -- the")
    print("numerator dominates on every frame.")
    print()
    print(f"{'frame':>13} {'vs 1/close':>11} {'vs upper-lower':>15} "
          f"{'band steps':>11}")
    for name in FIRING:
        h, l, c = FRAMES[name]()
        col = sk_fcb_width(h, l, c)
        up = _last_fractal(h.where(np.isfinite(h)), SPAN, True)
        lo = _last_fractal(l.where(np.isfinite(l)), SPAN, False)
        raw = up - lo
        steps = int(np.r_[False, (raw.to_numpy()[1:] != raw.to_numpy()[:-1])
                          & ~np.isnan(raw.to_numpy()[1:])].sum())
        print(f"{name:>13} {_spearman(col, 1.0 / c):>11.4f} "
              f"{_spearman(col, raw):>15.4f} {steps:>11}")


def section_G():
    _head("G Guards, and what each one buys")
    print("G1 -- the close guard. A bad close empties its own bar; the count")
    print("of OTHER bars moved is the claim that matters.")
    print()
    frame = _walk()
    base = sk_fcb_width(*frame)
    h, l, c = frame
    unguarded = _mutant(*CLOSE_GUARD_OFF)
    print(f"{'close[700]':>12} {'fired':>6} {'emptied':>8} {'others':>7} "
          f"{'unguarded reads':>18}")
    for label, value in (("nan", np.nan), ("0.0", 0.0), ("-1.0", -1.0),
                         ("+inf", np.inf), ("-inf", -np.inf),
                         ("1e-310", 1e-310)):
        c2 = c.copy()
        c2.iloc[PLANT] = value
        out = sk_fcb_width(h, l, c2)
        emptied = int((base.notna() & out.isna()).sum())
        m = base.notna() & out.notna()
        others = int((base[m] != out[m]).sum())
        raw = unguarded(h, l, c2).iloc[PLANT]
        print(f"{label:>12} {int(out.notna().sum()):>6} {emptied:>8} "
              f"{others:>7} {raw:>18.6f}")
    print()
    print("G2 -- a bad HIGH or LOW. It produces no NaN, because a comparison")
    print("against a NaN is False: the bar simply makes no fractal. ⚠ The")
    print("cost is that its reach is NOT bounded by a window the way a")
    print("rolling mean's is -- a fractal the frame would have had is")
    print("missed, and `ffill` carries the older level until the NEXT")
    print("fractal replaces it, however long that takes. The counts below")
    print("are this plant on this frame and not a bound. No bar BEFORE the")
    print("plant may move, and that is the causal half.")
    print()
    print(f"{'leg':>6} {'value':>8} {'fired':>6} {'emptied':>8} "
          f"{'moved':>6} {'first moved':>12} {'last moved':>11} "
          f"{'max |rel|':>11}")
    for leg in ("high", "low"):
        for label, value in (("nan", np.nan), ("+inf", np.inf),
                             ("-inf", -np.inf)):
            parts = {"high": h.copy(), "low": l.copy()}
            parts[leg].iloc[PLANT] = value
            out = sk_fcb_width(parts["high"], parts["low"], c)
            emptied = int((base.notna() & out.isna()).sum())
            m = base.notna() & out.notna()
            idx = np.flatnonzero(m.to_numpy())[(base[m] != out[m]).to_numpy()]
            print(f"{leg:>6} {label:>8} {int(out.notna().sum()):>6} "
                  f"{emptied:>8} {idx.size:>6} "
                  f"{(idx.min() if idx.size else -1):>12} "
                  f"{(idx.max() if idx.size else -1):>11} "
                  f"{_rel(base, out):>11.3e}")
    print()
    print("G3 -- the SAME plants with the high/low guard removed, which is")
    print("what the guard buys: an infinity passes `ref > left`, becomes a")
    print("fractal, and `ffill` carries `inf` as the band until the next")
    print("fractal replaces it. A `-inf` HIGH and a `+inf` LOW cost nothing")
    print("-- an infinity on the wrong side of the comparison is never an")
    print("extreme -- and a NaN never made a fractal in the first place, so")
    print("FOUR of the six plants below are already clean unguarded and the")
    print("guard buys the other two.")
    print()
    hl_off = _mutant(*HL_GUARD_OFF)
    print(f"{'leg':>6} {'value':>8} {'fired':>6} {'non-finite':>11} "
          f"{'first non-finite':>17}")
    for leg in ("high", "low"):
        for label, value in (("nan", np.nan), ("+inf", np.inf),
                             ("-inf", -np.inf)):
            parts = {"high": h.copy(), "low": l.copy()}
            parts[leg].iloc[PLANT] = value
            out = hl_off(parts["high"], parts["low"], c)
            v = out.dropna().to_numpy()
            bad = ~np.isfinite(v)
            first = int(np.flatnonzero(
                ~np.isfinite(out.to_numpy()) & out.notna().to_numpy())[0]) \
                if bad.any() else -1
            print(f"{leg:>6} {label:>8} {v.size:>6} {int(bad.sum()):>11} "
                  f"{first:>17}")


def section_H():
    _head("H The column is NOT a non-negative width")
    print("`upper` and `lower` are the last fractal HIGH and the last")
    print("fractal LOW, and they come from DIFFERENT bars -- so nothing")
    print("makes the difference positive. A hand frame proves it, and the")
    print("mechanism is the tie of §C2: a plateau denies the rally its own")
    print("fractal high, while the dip after it still makes a fractal low")
    print("ABOVE the old high.")
    print()
    h, l, c = _negative_frame()
    col = sk_fcb_width(h, l, c)
    up = _last_fractal(h, SPAN, True)
    lo = _last_fractal(l, SPAN, False)
    print(f"{'bar':>4} {'high':>8} {'low':>8} {'close':>8} {'upper':>8} "
          f"{'lower':>8} {'width':>10}")
    for t in range(h.size):
        print(f"{t:>4} {h.iloc[t]:>8.2f} {l.iloc[t]:>8.2f} "
              f"{c.iloc[t]:>8.2f} {up.iloc[t]:>8.2f} {lo.iloc[t]:>8.2f} "
              f"{col.iloc[t]:>10.4f}")
    v = col.dropna()
    print()
    print(f"fired {v.size}, negative {int((v < 0).sum())}, min {v.min():.4f}")
    print()
    print("On the eight random frames of §C the count of readings <= 0 is in")
    print("that section's last column; this frame is the existence proof the")
    print("random ones do not give.")


def _negative_frame():
    """A 16-bar frame whose width goes NEGATIVE, by construction.

    Bars 0..4 make an early fractal high at 10.5 and an early fractal low
    at 9.5. Then the price steps to ~100 and PLATEAUS, so no bar's high
    strictly beats both neighbours; the dip at bars 11..12 then gives a
    fractal low at 99.0, which is far above the stale upper band.
    """
    highs = [10.0, 10.2, 10.5, 10.1, 9.9,
             100.0, 100.0, 100.0, 100.0, 100.0, 100.0,
             99.5, 100.0, 100.0, 100.0, 100.0]
    lows = [9.8, 9.7, 9.6, 9.5, 9.7,
            99.5, 99.5, 99.5, 99.5, 99.5, 99.5,
            99.0, 99.5, 99.5, 99.5, 99.5]
    closes = [9.9, 10.0, 10.1, 9.8, 9.8,
              99.8, 99.8, 99.8, 99.8, 99.8, 99.8,
              99.2, 99.8, 99.8, 99.8, 99.8]
    idx = date_range("2020-01-01", periods=len(highs), freq="h")
    return (Series(highs, index=idx, dtype=float),
            Series(lows, index=idx, dtype=float),
            Series(closes, index=idx, dtype=float))


def _outside_bar_frame(n=MIN_BARS):
    """A frame whose bar `SPAN` is an OUTSIDE bar: the strict high AND the
    strict low of the whole window, so both band legs confirm on bar
    `2 * SPAN`, the earliest bar they can."""
    idx = date_range("2020-01-01", periods=n, freq="h")
    highs = np.full(n, 10.0)
    lows = np.full(n, 9.5)
    closes = np.full(n, 9.8)
    highs[SPAN] = 11.0
    lows[SPAN] = 9.0
    return (Series(highs, index=idx), Series(lows, index=idx),
            Series(closes, index=idx))


def section_L():
    _head("L Degenerate frames, and the shortest accepted frame")
    print("A frame shorter than MIN_BARS returns None. MIN_BARS itself has")
    print("exactly one bar a band COULD sit on -- bar 2 * SPAN -- and")
    print("whether it does is data-dependent, which is the whole of the")
    print("warm-up here. On `walk` it does not.")
    print()
    h, l, c = _walk(n=40)
    for n in (MIN_BARS - 1, MIN_BARS, 2 * SPAN + 6):
        out = sk_fcb_width(h.iloc[:n], l.iloc[:n], c.iloc[:n])
        got = "None" if out is None else f"{int(out.notna().sum())} fired"
        print(f"  bars {n:>3}: {got}")
    print()
    print("That bar 2 * SPAN is REACHABLE needs a frame where one bar is")
    print("both the strict high and the strict low of its window -- an")
    print("outside bar -- so that both legs confirm at once:")
    print()
    oh, ol, oc = _outside_bar_frame()
    out = sk_fcb_width(oh, ol, oc)
    first = np.flatnonzero(out.notna().to_numpy())
    print(f"  outside bar at index {SPAN}: {int(out.notna().sum())} fired, "
          f"first at bar {int(first[0]) if first.size else -1} "
          f"(2 * SPAN = {2 * SPAN}), value {out.iloc[2 * SPAN]:.6f}")
    print()
    print("Constant / zero / negative / NaN frames, under")
    print("errstate(all='raise'):")
    print()
    idx = date_range("2020-01-01", periods=60, freq="h")
    for label, value in (("all NaN", np.nan), ("all 0.0", 0.0),
                         ("all -5.0", -5.0), ("all 100.0", 100.0)):
        s = Series(np.full(60, value), index=idx)
        with np.errstate(all="raise"):
            out = sk_fcb_width(s.copy(), s.copy(), s.copy())
        print(f"  {label:>10}: {int(out.notna().sum())} fired")
    print()
    print("A frame whose high/low and close live hundreds of orders apart:")
    h2, l2, _ = _walk(n=60, level=1e+300)
    tiny = Series(np.full(60, 1e-300), index=h2.index)
    out = sk_fcb_width(h2, l2, tiny)
    v = out.dropna().to_numpy()
    print(f"  high/low 1e+300, close 1e-300: {v.size} fired, "
          f"{int(np.isinf(v).sum())} infinite")


def section_W():
    _head("W The docstring's first paragraph against the dictionary's cut")
    print("`docs/gen_indicator_dictionary.py`'s `desc()` shows")
    print("`d[:150].rsplit(' ', 1)[0]` of the first paragraph, dropping the")
    print("trailing word WHOLE -- and only when the paragraph exceeds 150")
    print("characters.")
    print()
    desc = _generator_desc()
    body = []
    for line in sk_fcb_width.__doc__.splitlines()[1:]:
        if line.strip():
            body.append(line.strip())
        elif body:
            break
    paragraph = " ".join(body)
    print(f"paragraph ({len(paragraph)} chars): {paragraph}")
    print(f"desc() returns it whole: {desc({'desc': paragraph}) == paragraph}")
    slack = 0
    while desc({"desc": paragraph[:-1] + "x" * (slack + 1) + paragraph[-1:]}) \
            == paragraph[:-1] + "x" * (slack + 1) + paragraph[-1:]:
        slack += 1
        if slack > 200:
            break
    print(f"characters of slack before a word is lost: {slack}")


def _generator_desc():
    """`docs/gen_indicator_dictionary.py`'s own `desc`, lifted out with
    `ast` -- importing that module runs its whole indicator probe."""
    import ast
    import re
    path = Path(__file__).resolve().with_name("gen_indicator_dictionary.py")
    tree = ast.parse(path.read_text(encoding="utf-8"))
    fn = next(n for n in tree.body
              if isinstance(n, ast.FunctionDef) and n.name == "desc")
    ns = {"re": re}
    exec(compile(ast.Module(body=[fn], type_ignores=[]),
                 "<gen_indicator_dictionary.desc>", "exec"), ns)
    return ns["desc"]


def section_M():
    _head("M The wiring counts, re-derived rather than incremented")
    print("`docs/IndicatorDictionary.md` is generated from a live probe, so")
    print("these are read back out of it and out of the live package --")
    print("`README.md` and `docs/MLCompanionContract.md` quote them, and")
    print("`tests/test_readme_counts.py` and")
    print("`tests/test_ml_companions.py` re-derive them independently.")
    print()
    import re
    from collections import Counter

    import pandas_ta as ta
    registered = sum(len(v) for v in ta.Category.values())
    print(f"registered in Category: {registered}")
    print(f"'sk_fcb_width' in Category['volatility']: "
          f"{'sk_fcb_width' in ta.Category['volatility']}")
    print(f"volatility bucket: {len(ta.Category['volatility'])}")

    path = Path(__file__).resolve().with_name("IndicatorDictionary.md")
    doc = path.read_text(encoding="utf-8")
    body = doc[doc.index("## candles"):]
    tags = Counter(re.findall(
        r"`[^`]+`\s+(PX2|PX|SF|BIN|ORD|CONST|\?\?)(?!\w)", body))
    print(f"dictionary tagged columns: {sum(tags.values())}")
    for tag in ("PX", "SF", "BIN", "PX2", "ORD", "CONST", "??"):
        print(f"  {tag:>5}: {tags[tag]}")
    probed = re.search(r"\*\*(\d+) indicators\*\* probed", doc)
    print(f"dictionary probed: {probed.group(1)}")
    for label in ("registered in `Category`",
                  "callable as `df.ta.<name>()`"):
        row = re.search(re.escape(label) + r" \| \*\*(\d+)\*\*", doc)
        print(f"dictionary table, {label}: {row.group(1)}")
    print()
    print("The SK_FCB_WIDTH_2 row the generator wrote:")
    for line in doc.splitlines():
        if line.startswith("| `sk_fcb_width`"):
            print(f"  {line}")


def section_Z():
    _head("Z Cost")
    print("⚠ Machine- and run-dependent. Best of 5, printed as a range over")
    print("two repeats so the spread is visible rather than hidden.")
    print()
    print(f"{'bars':>8} {'ms (best of 5, two runs)':>28} {'peak MB':>9}")
    for n in (100_000, 400_000):
        frame = _walk(n=n)
        times = [min(timeit.repeat(lambda: sk_fcb_width(*frame), number=1,
                                   repeat=5)) * 1e3 for _ in range(2)]
        tracemalloc.start()
        sk_fcb_width(*frame)
        peak = tracemalloc.get_traced_memory()[1] / 1e6
        tracemalloc.stop()
        print(f"{n:>8} {min(times):>13.1f} .. {max(times):<13.1f} "
              f"{peak:>9.1f}")


SECTIONS = {
    "A1": section_A1, "A2": section_A2, "A3": section_A3, "A4": section_A4,
    "B": section_B, "B2": section_B2, "C": section_C, "C2": section_C2,
    "C3": section_C3,
    "D": section_D,
    "F": section_F, "G": section_G, "H": section_H, "L": section_L,
    "M": section_M, "W": section_W, "Z": section_Z,
}


if __name__ == "__main__":
    print(f"pandas {pd.__version__}, numpy {np.__version__}")
    print("Stock.Indicators (the C# source) is NOT readable from this "
          "worktree: "
          f"{importlib.util.find_spec('stock_indicators') is None}")
    want = [a.upper() for a in sys.argv[1:]] or list(SECTIONS)
    for key in want:
        if key not in SECTIONS:
            raise SystemExit(f"unknown section {key!r};"
                             f" pick from {list(SECTIONS)}")
        SECTIONS[key]()
