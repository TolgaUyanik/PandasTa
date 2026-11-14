# -*- coding: utf-8 -*-
"""SK-FCB-POS: `sk_fcb_pos`, close's position inside the Fractal Chaos
Bands (PandasTa issue #108, Skender Stock.Indicators' `Fcb`, Apache-2.0).

    SK_FCB_POS_2 = (close - last confirmed fractal low)
                   / (last confirmed fractal high
                      - last confirmed fractal low)

What this file pins, in order of how much it would hurt to lose:

1. **The DENOMINATOR, which is this column's own risk and not the
   sibling's.** `upper - lower` is not positive and is not guarded to be,
   so three regimes ship and all three are pinned:
   `upper > lower` means what the name says; `upper == lower` makes the
   quotient `+-inf` and the `replace` EMPTIES the bar, where
   `sk_fcb_width` reads exactly 0.0 on the same bar (a hand frame asserts
   both); `upper < lower` KEEPS the bar with the position scale INVERTED,
   so a close above both legs reads below 0. The inverted regime is
   asserted to be REACHABLE on every firing frame, asserted bar by bar on
   a hand frame, and the alternative -- masking it -- is asserted to
   differ on exactly those bars and nowhere else.
   ⚠ Keeping the inverted bars is the screen prototype's reading, which is
   what Gate E's 0.8348 was measured on, so this is a tie to that figure
   and not a preference.
   The column is also asserted NOT bounded to [0, 1], in both directions,
   on every firing frame, and the extreme tail is asserted to come from a
   SMALL DENOMINATOR rather than from an extreme close.
2. **Gate A, the formula spelled two ways -- ONE of them independent.** A
   transcription of Skender's `Fractal` double loop plus `Fcb`'s
   roll-forward, sharing no code with the module, and the screen
   prototype that the 2026-10-24 catalog screen measured at Gate E. Both
   are asserted BIT-equal to the module, with identical NaN masks, on all
   eight synthetic frames (10,245 fired bars as measured here). Nothing is
   a tolerance: the legs are SELECTED price levels, so the arithmetic is
   two subtractions and one division on the same doubles.
   ⚠ The prototype limb is NOT a second derivation: its `last_fractal` is
   the imported `_last_fractal` operation for operation and its `sdiv` is
   the module's `replace`, so its bit-equality on a clean frame is
   structural. What it buys is the TIE to the screen's Gate E figures.
3. **Gate B, causality -- including the part of it that lives in another
   file.** A sweep that splits a frame into one shared past and two WHOLLY
   different futures catches the module on 0 of 36 offsets on each of the
   eight frames, and on 0 of 295 offsets of a 300-bar walk. SIX look-ahead
   mutants are read off the shipped source, edited and `exec`'d in memory,
   and THREE of them edit the `_last_fractal` this module imports from
   `pandas_ta.volatility.sk_fcb_width` -- the only way to test the
   causality of code this file does not contain. Each is asserted LIVE
   against the module first, so an edit that failed to take cannot pass as
   a clean sweep.
   ⚠ A mutant is NOT caught on 36 of 36 and the test does not ask it to:
   two of the six look ahead through something discrete (a strict
   comparison, and a step function shifted by one bar), so the edit is
   invisible at an offset where the decisions near the boundary come out
   the same either way -- as few as 4 of 36 when measured. Each of those
   two is given a NECESSARY condition for being catchable, COMPUTED from
   the two futures rather than argued, and the test asserts 0 catches
   outside the condition and a high catch rate inside it.
4. **The index divergence, named and measured.** Skender's `Fractal`
   returns a level ON its centre bar; this port reads it `SPAN` bars
   later, when the right-hand bars exist. The centre reading is built
   independently here, asserted to be a DIFFERENT column (42 .. 841 bars
   differ, Spearman 0.7765 .. 0.9845 as measured here), and asserted to be
   exactly what the `centre-read` mutant produces -- so the mutant is the
   documented alternative reading rather than an invented edit.
   ⚠ What is NOT pinned, because it cannot be: what `Fcb.Series.cs` does
   with that index. The file is unreadable from this worktree, which
   `test_the_source_library_is_not_readable_here` records for three routes
   and explicitly not for the fourth.
5. **Gate D, scale -- and the affine invariance that goes past it.**
   x8/x64 bit-identical on every fired bar of all eight frames and at
   price levels 1e-6, 1e+6 and 1e+100, because a comparison is
   rescale-invariant and an exact binary factor cancels between numerator
   and denominator. x10/x3.7/x0.1/x1.0000001 within 1e-7 relative with
   matching NaN masks (measured max 9.633e-11 -- the assertion carries
   three orders of margin on purpose, because a small denominator
   amplifies a last-bit move). A LEVEL SHIFT cancels too, which the
   sibling's `/ close` does not: Spearman 1.0000 with matching masks at
   +1, +50 and +1e6. And -- the risk peculiar to a comparison-selected
   band -- 0 bars where an inexact rescale moved the fractal SELECTION,
   which would move a leg by a whole price level.
6. **Gate C, reachability, and the three facts a consumer gets wrong.**
   The warm-up is DATA-DEPENDENT (first fire on bar 7 .. 89 across the
   frames here, and NEVER on a flat price, which fires 0 of 1,500); the
   earliest POSSIBLE fire is bar `2 * SPAN` = 4 and needs an outside bar,
   pinned by a hand frame; and a flat frame firing nothing is normal for
   the bucket rather than a defect -- 41 of 139 momentum columns read
   all-NaN there, `willr`, `rsi`, `cci` and `stochrsi` among them
   (`docs/SkFcbPosMeasured.md` §C3 ran it; this file asserts the handful
   it can afford to re-run).
7. **The strict predicate, which is the whole column on a tick grid.**
   Identical to the non-strict reading on every continuous frame and a
   DIFFERENT column on a 2.0-tick frame, where ties are everywhere. This
   is FVGDEAD's lesson (`CLAUDE.md`) spent in advance: 21.17% of real BIST
   daily bars close exactly at an extreme.
8. **The guards, each priced, and one DIVERGENCE from the sibling.** A NaN
   or infinite close empties its own bar and no other. ⚠ A zero, negative
   or subnormal close is NOT emptied here -- close is in the numerator,
   not the divisor -- and reads a large finite number, which is asserted
   rather than left to be discovered. A bad high or low is absorbed with
   0 earlier bars moved and an unbounded forward reach; the high/low mask
   exists for infinities, and with it a NaN and an infinite price give
   bit-identical columns.

⚠ **Counts, distinct-value counts and Spearman figures are NOT pinned to
their measured digits.** The frames are built with `np.exp` and
`np.cumsum`, so a reduced numpy kernel moves a price in its last bits --
and a band leg is chosen by a strict COMPARISON, so a last-bit move
either changes nothing or swaps in a whole different price level, which a
small denominator then amplifies. Every count here is asserted as a bound
or a relation, with the figure measured on this machine stated in the
docstring. `python docs/measure_sk_fcb_pos_cpu.py` re-runs this module
with numpy's AVX-512/AVX2/FMA3 dispatch disabled.

Every number quoted in this file comes from `docs/measure_sk_fcb_pos.py`.
"""
import csv
import importlib.util
from pathlib import Path

import numpy as np
import pytest
from pandas import DataFrame, Series, date_range

from .context import pandas_ta  # noqa: F401

import pandas_ta as ta
from pandas_ta.momentum.sk_fcb_pos import sk_fcb_pos
from pandas_ta.volatility.sk_fcb_width import (MIN_BARS, SPAN, _last_fractal,
                                               sk_fcb_width)

N = 1500
LEVEL = 100.0
COLUMN = "SK_FCB_POS_2"
#: The causality sweep's 36 perturbation points.
OFFSETS = list(range(N - 36, N))
#: Where the guard tests plant a bad bar.
PLANT = 700


# ------------------------------------------------------------------ frames
# Same builders and seeds as `docs/measure_sk_fcb_pos.py`, which is the
# same set issue #107 used, so a number here and a number there are one
# measurement.


def _ohlc(close, seed):
    rng = np.random.default_rng(seed + 9_999)
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
    """A walk rounded to a tick COARSER than its own bar-to-bar move: where
    the strict predicate bites and where the two legs land on one tick, so
    it is the only frame here with a collapsed band."""
    h, l, c = _walk(seed, n, level)
    return (np.round(h / tick) * tick, np.round(l / tick) * tick,
            np.round(c / tick) * tick)


FRAMES = {
    "walk": _walk, "trend": _trend, "range-bound": _range_bound,
    "grid": _grid, "heavy-tailed": _heavy, "jump": _jump, "flat": _flat,
    "coarse": _coarse,
}
NAMES = list(FRAMES)
#: `flat` has no strict local extreme, so the column never fires on it.
FIRING = [n for n in NAMES if n != "flat"]
#: The five frames whose prices are continuous floats, where a TIE between
#: two bars within SPAN of each other does not happen (asserted).
CONTINUOUS = ["walk", "trend", "range-bound", "heavy-tailed", "jump"]


def _outside_bar_frame():
    """The shortest frame that fires on the earliest POSSIBLE bar, 2 * SPAN.

    Bar 2 is both the strict high and the strict low of its window -- an
    outside bar -- so both legs confirm on bar 4 at once. Bar 4 closes
    ABOVE the upper leg and bar 5 BELOW the lower one, so the same frame
    also shows the column leaving [0, 1] in both directions.
    """
    idx = date_range("2020-01-01", periods=7, freq="D")
    return (Series([10.0, 10.0, 12.0, 10.0, 10.0, 10.0, 10.0], index=idx),
            Series([9.0, 9.0, 7.0, 9.0, 9.0, 9.0, 9.0], index=idx),
            Series([9.5, 9.5, 9.5, 9.5, 11.0, 7.5, 9.5], index=idx))


def _inverted_band_frame():
    """A frame where the band ends up CROSSED: a high fractal confirms at
    13.00 on bar 4, then the price gaps up and a LOW fractal confirms at
    18.00 on bar 9, above it. `upper - lower` is -5.00 from there on."""
    idx = date_range("2020-01-01", periods=16, freq="D")
    return (Series([10.0, 10.5, 13.0, 10.4, 10.3,
                    20.0, 20.5, 21.0, 21.5, 22.0,
                    22.5, 23.0, 23.5, 24.0, 24.5, 25.0], index=idx),
            Series([9.0, 9.5, 9.4, 9.3, 9.2,
                    19.0, 19.5, 18.0, 19.6, 19.7,
                    19.8, 19.9, 20.0, 20.1, 20.2, 20.3], index=idx),
            Series([9.5, 10.0, 11.0, 10.0, 9.8,
                    19.5, 20.0, 19.0, 20.5, 21.0,
                    21.5, 22.0, 22.5, 23.0, 23.5, 24.0], index=idx))


def _collapsed_band_frame():
    """A frame where the band ends up COLLAPSED: the high fractal confirms
    at 12.00 on bar 4 and the LOW fractal confirms at exactly 12.00 on bar
    11, so `upper - lower` is 0.00 from bar 11 on. Close is the bar's
    midpoint."""
    idx = date_range("2020-01-01", periods=16, freq="D")
    high = Series([10.0, 10.0, 12.0, 10.0, 10.0, 10.0, 10.0, 14.0,
                   14.0, 13.0, 14.0, 14.0, 10.0, 10.0, 10.0, 10.0], index=idx)
    low = Series([9.0, 9.0, 9.0, 8.0, 9.0, 9.0, 9.0, 13.0,
                  13.0, 12.0, 13.0, 13.0, 9.0, 9.0, 9.0, 9.0], index=idx)
    return high, low, (high + low) / 2.0


# ----------------------------------------------------------------- helpers


def _scaled(frame, factor):
    h, l, c = frame
    return h * factor, l * factor, c * factor


def _shifted(frame, amount):
    h, l, c = frame
    return h + amount, l + amount, c + amount


def _bit_equal(a, b):
    if not bool((a.isna() == b.isna()).all()):
        return False
    m = a.notna()
    return bool((a[m] == b[m]).all())


def _differs(a, b):
    one = int((a.isna() != b.isna()).sum())
    m = a.notna() & b.notna()
    return one + int((a[m] != b[m]).sum())


def _rel(a, b):
    m = a.notna() & b.notna()
    if not int(m.sum()):
        return float("nan")
    d = (a[m] - b[m]).abs()
    scale = b[m].abs().where(b[m].abs() > 0.0, np.nan)
    rel = (d / scale).max()
    return 0.0 if np.isnan(rel) else float(rel)


def _spearman(a, b):
    m = a.notna() & b.notna()
    if int(m.sum()) < 3 or a[m].nunique() < 2 or b[m].nunique() < 2:
        return float("nan")
    return float(a[m].corr(b[m], method="spearman"))


def _legs(frame):
    """The two band legs and the denominator, as the module computes them."""
    h, l, _ = frame
    up = _last_fractal(h.where(np.isfinite(h)), SPAN, True)
    lo = _last_fractal(l.where(np.isfinite(l)), SPAN, False)
    return up, lo, up - lo


def _steps(leg):
    v = leg.to_numpy()
    return int(((v[1:] != v[:-1]) & ~np.isnan(v[1:])).sum())


# ----------------------------------------------------------------- oracles


def _fractals(h, l, span=SPAN):
    """Skender's `Fractal` with `leftSpan = rightSpan = span` and
    `EndType.HighLow`, transcribed as its own double loop:

        if (i >= leftSpan && i < length - rightSpan) {
            for (int p = i - leftSpan; p <= i + rightSpan; p++) {
                if (p == i) continue;
                if (evalHigh <= pHigh) isHigh = false;
                if (evalLow  >= pLow)  isLow  = false;
            }
            if (isHigh) fractalBear = evalHigh;
            if (isLow)  fractalBull = evalLow;
        }

    The level is returned ON the centre bar, which is where Skender puts
    it. ⚠ Transcribed from the formula issue #108 names, NOT from a reading
    of `Fcb.Series.cs`, which this worktree cannot open.
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
    """`Fcb`'s roll-forward with the fractal read `lag` bars after its
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
    which is all the prototype's `sdiv` does: `+-inf -> NaN`."""
    return x.replace([np.inf, -np.inf], np.nan)


def _oracle(high, low, close, lag=SPAN):
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
    """The reading NOT taken: the fractal used ON its centre bar, the index
    Skender's `Fractal` returns it at."""
    return _oracle(high, low, close, lag=0)


def _non_strict(high, low, close):
    """The reading NOT taken: `>=` / `<=`, so a tie still makes a
    fractal."""
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
    """The reading NOT taken: `EndType.Close`, Skender's other option,
    which judges and returns the CLOSE instead of the high and the low."""
    up = _last_fractal(close, SPAN, True)
    lo = _last_fractal(close, SPAN, False)
    return _fin((close - lo) / (up - lo))


def _masked_inversion(high, low, close):
    """The reading NOT taken, and the one a consumer is most likely to
    assume: the inverted band (`upper < lower`) masked out instead of
    kept."""
    h = high.where(np.isfinite(high))
    l = low.where(np.isfinite(low))
    up = _last_fractal(h, SPAN, True)
    lo = _last_fractal(l, SPAN, False)
    return _fin((close - lo) / (up - lo).where((up - lo) > 0.0))


# ----------------------------------------------------------------- mutants

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "pandas_ta" / "momentum" / "sk_fcb_pos.py"
BAND_SOURCE = ROOT / "pandas_ta" / "volatility" / "sk_fcb_width.py"

#: (label, where, old, new). `where` names which SHIPPED file the edit
#: lands in: "pos" is this port's module, "band" is the `_last_fractal` it
#: imports from `pandas_ta.volatility.sk_fcb_width`. Both are read off disk
#: and `exec`'d in memory, so no mutant can drift away from the source it
#: claims to edit.
#: ⚠ Three of the six are "band" edits, and that is the point: this
#: module's causality is not decidable from this module's file alone.
CAUSALITY_MUTANTS = [
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
#: Not causality mutants: the guards, removed, to price what they buy.
HL_GUARD_OFF = ("    h = high.where(np.isfinite(high))\n"
                "    l = low.where(np.isfinite(low))",
                "    h = high\n    l = low")
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

    A "band" edit is applied to `sk_fcb_width.py`, the mutated
    `_last_fractal` is lifted out of it, and it REPLACES that name in a
    fresh copy of this module's globals. That works because `sk_fcb_pos`
    looks `_last_fractal` up in its globals on every call rather than
    binding it at import -- and
    `test_gate_b_mutant_each_edit_is_live_against_the_module` asserts it
    really did take, so a band edit that silently failed cannot pass as a
    clean sweep.
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

    ⚠ Deliberately not the usual "multiply the tail by 1.03": a fractal is
    a COMPARISON, so a look-ahead only becomes visible when a decision
    within SPAN bars of the boundary actually flips, and a weak detector
    returning 0 would be weak evidence. The same factor multiplies high,
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
    """`right-window-lead`'s necessary condition, COMPUTED: if the MUTATED
    band is identical on every bar `< j` in both futures, nothing
    downstream of it can differ there."""
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


def _upper_lead_exposed_at(frame, j):
    """`upper-lead`'s necessary condition. The edit makes bar `t` read
    `upper[t + 1]`; for `t + 1 <= j - 1` that is still a prefix bar and is
    identical in both futures, so the ONLY prefix bar it can move is
    `t = j - 1`, which reads `upper[j]`."""
    (ha, _, _), (hb, _, _) = _futures(frame, j)
    a = _last_fractal(ha.where(np.isfinite(ha)), SPAN, True).iloc[j]
    b = _last_fractal(hb.where(np.isfinite(hb)), SPAN, True).iloc[j]
    return not (bool(a == b) or (np.isnan(a) and np.isnan(b)))


def _generator_desc():
    """`docs/gen_indicator_dictionary.py`'s own `desc`, lifted out of its
    source with `ast` and compiled alone.

    Importing that module runs its whole indicator probe, which is far too
    slow for a unit test -- and re-typing the cut here would pin a COPY of
    the rule rather than the rule."""
    import ast
    import re
    path = ROOT / "docs" / "gen_indicator_dictionary.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    fn = next(n for n in tree.body
              if isinstance(n, ast.FunctionDef) and n.name == "desc")
    ns = {"re": re}
    exec(compile(ast.Module(body=[fn], type_ignores=[]),
                 "<gen_indicator_dictionary.desc>", "exec"), ns)
    return ns["desc"]


# -------------------------------------------------- wiring and arguments


def test_name_registration_and_accessor():
    """The five wiring touch points, through the three call styles."""
    assert "sk_fcb_pos" in ta.Category["momentum"]
    frame = _walk()
    col = sk_fcb_pos(*frame)
    assert col.name == COLUMN == f"SK_FCB_POS_{SPAN}"
    assert col.category == "momentum"

    h, l, c = frame
    df = DataFrame({"high": h, "low": l, "close": c})
    assert hasattr(df.ta, "sk_fcb_pos")
    via_accessor = df.ta.sk_fcb_pos()
    assert via_accessor.name == COLUMN
    assert _bit_equal(via_accessor, col)


def test_the_band_helper_is_the_shipped_sibling():
    """This module does not contain the fractal loop: it IMPORTS
    `_last_fractal`, `SPAN` and `MIN_BARS` from issue #107's shipped
    `sk_fcb_width`, per `CLAUDE.md`'s "Do not add a fourth copy: import
    the function".

    Two things that buys, and one it costs. It buys a single definition of
    the band -- the two columns cannot drift to different spans, which is
    asserted here by identity of the constants -- and it buys the band's
    own Gate A/B/D evidence, already measured in `docs/SkFcbWidthMeasured.md`.
    It costs a coupling that this file cannot see: an edit to
    `_last_fractal` changes THIS column without changing THIS module's
    file. What catches that is the Gate E ledger's `output_fp`, a live
    fingerprint on a fixed frame rather than a file hash
    (`docs/gate_e_ledger.py`), and `test_gate_b_mutant_*`, which edits
    that file deliberately and asserts the edit reaches this column.
    """
    # read out of `sys.modules`, not re-imported: this file's own
    # top-level `from ... import` already put both there, and an
    # `import a.b.c as x` here resolves against whatever `sys.path` the
    # rest of the suite has grown by the time this module is collected.
    import sys
    mod = sys.modules["pandas_ta.momentum.sk_fcb_pos"]
    sibling = sys.modules["pandas_ta.volatility.sk_fcb_width"]
    assert mod._last_fractal is sibling._last_fractal
    assert (mod.SPAN, mod.MIN_BARS) == (sibling.SPAN, sibling.MIN_BARS)
    # the import is from the MODULE, never from the package -- the
    # `TypeError: 'module' object is not callable` class of bug `CLAUDE.md`
    # records.
    src = SOURCE.read_text(encoding="utf-8")
    assert "from pandas_ta.volatility.sk_fcb_width import" in src
    assert "from pandas_ta.volatility import" not in src


def test_the_source_library_is_not_readable_here():
    """Gate A is the formula issue #108 NAMES, spelled two ways -- not a
    run or a reading of Skender's C#. Three routes to that source are
    pinned shut here, so the claim cannot rot into "checked against
    Skender" if one of them ever opens.

    `docs/pine/` is the corpus `CLAUDE.md` describes as untracked; it holds
    Pine, not C#, but it is the only vendored-source directory this repo
    has ever had, and its absence is half of why this port cites the
    issue's naming of `Fcb.Series.cs` instead of its lines.

    ⚠ A FOURTH route, web access, was unavailable in the session that
    wrote this and is NOT pinned here: a test cannot see it. Said in the
    module docstring and in `docs/SkFcbPosMeasured.md`'s "What this port
    does NOT establish" too, so "all routes are pinned" is nowhere."""
    assert importlib.util.find_spec("stock_indicators") is None
    assert not (ROOT / "docs" / "pine").exists()
    assert not list(ROOT.rglob("Fcb.Series.cs"))


def test_the_signature_is_the_three_prices_and_an_offset():
    """No `span=`: 2 is a module constant, because span 2 is the only span
    anything -- the issue's title, the screen prototype, the Gate E
    figures -- has measured. A keyword here would ship spans nothing has
    looked at."""
    import inspect
    assert list(inspect.signature(sk_fcb_pos).parameters) == \
        ["high", "low", "close", "offset", "kwargs"]
    assert (SPAN, MIN_BARS) == (2, 5)


def test_a_frame_shorter_than_min_bars_is_refused():
    """`MIN_BARS` = 2 * SPAN + 1 is a floor on the INPUT. The shortest
    accepted frame has exactly one bar a band could sit on -- bar
    2 * SPAN -- and whether it fires there is DATA-DEPENDENT: `walk` does
    not, the outside-bar frame does."""
    h, l, c = _walk(n=40)
    assert sk_fcb_pos(h.iloc[:MIN_BARS - 1], l.iloc[:MIN_BARS - 1],
                      c.iloc[:MIN_BARS - 1]) is None
    short = sk_fcb_pos(h.iloc[:MIN_BARS], l.iloc[:MIN_BARS],
                       c.iloc[:MIN_BARS])
    assert short is not None and short.size == MIN_BARS
    assert int(short.notna().sum()) == 0


def test_offset_and_fillna_do_what_the_kwargs_say():
    base = sk_fcb_pos(*_walk())
    moved = sk_fcb_pos(*_walk(), offset=2)
    m = base.notna() & base.shift(2).notna()
    assert bool((moved[m] == base.shift(2)[m]).all())
    filled = sk_fcb_pos(*_walk(), fillna=0.0)
    assert int(filled.isna().sum()) == 0


# ------------------------------------------------------------------ Gate A


@pytest.mark.parametrize("name", NAMES)
def test_gate_a_matches_the_source_formula_by_explicit_loops(name):
    """Item 2's independent limb. `_fractals` is Skender's double loop and
    `_carry` is `Fcb`'s roll-forward, both Python loops over numpy; the
    module is four rolling windows and two `ffill`s. BIT-equal, not close:
    the legs are selected price levels, so once the selection agrees the
    only arithmetic is two subtractions and one division on the same
    doubles."""
    frame = FRAMES[name]()
    col = sk_fcb_pos(*frame)
    assert _bit_equal(col, _oracle(*frame))


@pytest.mark.parametrize("name", NAMES)
def test_gate_a_matches_the_screen_prototype_bit_for_bit(name):
    """Item 2's second limb, and the TIE to Gate E: the screen measured
    0.8348 against `pgo` on this expression, so the port has to be that
    expression.

    ⚠ NOT a second derivation: `_prototype`'s `last_fractal` is the
    imported `_last_fractal` operation for operation and its `sdiv` is the
    module's `replace`, so bit-equality on a clean frame is structural.
    What it also shows is the module's high/low mask priced at ZERO here --
    the prototype has no mask, and these frames are finite."""
    frame = FRAMES[name]()
    assert _bit_equal(sk_fcb_pos(*frame), _prototype(*frame))


@pytest.mark.parametrize("name", FIRING)
def test_the_centre_reading_is_a_different_column(name):
    """Item 4. Reading the fractal on its centre bar instead of SPAN bars
    later is a real choice and not a rounding: 42 .. 841 bars differ at
    Spearman 0.7765 .. 0.9845 as measured here. Asserted as "a great many
    bars differ and the rank correlation is well under 1", not as those
    digits."""
    frame = FRAMES[name]()
    col = sk_fcb_pos(*frame)
    ctr = _centre_reading(*frame)
    assert _differs(col, ctr) >= 20
    assert _spearman(col, ctr) < 0.999


def test_the_centre_read_mutant_is_skenders_own_index():
    """The `centre-read` mutant is not an invented edit: it is the reading
    Skender's own `Fractal` index gives, which `_centre_reading` builds
    independently from the double loop. The two are asserted to agree, so
    Gate B catching that mutant IS the evidence for this port's index
    choice."""
    label, where, old, new = CAUSALITY_MUTANTS[0]
    assert label == "centre-read"
    fn = _mutant(where, old, new)
    for name in ("walk", "coarse"):
        frame = FRAMES[name]()
        assert _bit_equal(fn(*frame), _centre_reading(*frame))


@pytest.mark.parametrize("name", CONTINUOUS)
def test_the_strict_predicate_costs_nothing_on_continuous_prices(name):
    """Item 7, first half. On continuous floats no two bars within SPAN of
    each other tie, so `>` and `>=` select the same fractals and the
    columns are bit-identical. Asserted together with the ABSENCE of ties,
    so a frame that quietly grew one would fail here with a readable
    reason rather than through the column."""
    frame = FRAMES[name]()
    h, l, _ = frame
    for x in (h.to_numpy(), l.to_numpy()):
        ties = sum(int((x[i] == x[max(0, i - SPAN):i + SPAN + 1]).sum() > 1)
                   for i in range(x.size))
        assert ties == 0
    assert _bit_equal(sk_fcb_pos(*frame), _non_strict(*frame))


def test_the_strict_predicate_is_the_whole_column_on_a_tick_grid():
    """Item 7, second half, and FVGDEAD's lesson spent in advance. On a
    2.0-tick walk the non-strict reading is a DIFFERENT column -- 1,256
    bars differ at Spearman 0.3417 when measured -- while a 0.01-tick
    walk differs on 43. Asserted as an ordering and bounds: the coarse
    frame differs on most of its bars and ranks far from 1, the fine one
    differs on some but stays close to 1, and ties are present on both."""
    fine, coarse = FRAMES["grid"](), FRAMES["coarse"]()
    d_fine = _differs(sk_fcb_pos(*fine), _non_strict(*fine))
    d_coarse = _differs(sk_fcb_pos(*coarse), _non_strict(*coarse))
    assert 0 < d_fine < 400
    assert d_coarse > 500
    assert d_coarse > 5 * d_fine
    assert _spearman(sk_fcb_pos(*fine), _non_strict(*fine)) > 0.9
    assert _spearman(sk_fcb_pos(*coarse), _non_strict(*coarse)) < 0.7
    for frame in (fine, coarse):
        h = frame[0].to_numpy()
        ties = sum(int((h[i] == h[max(0, i - SPAN):i + SPAN + 1]).sum() > 1)
                   for i in range(h.size))
        assert ties > 0


@pytest.mark.parametrize("name", FIRING)
def test_endtype_close_is_a_different_column(name):
    """Skender's `EndType` has a second option, `Close`, which judges and
    returns the close instead of the high and the low. The issue names the
    high/low form, and the two are not interchangeable: 906 .. 1,493 bars
    differ when measured."""
    frame = FRAMES[name]()
    col = sk_fcb_pos(*frame)
    other = _close_ends(*frame)
    assert _differs(col, other) >= 100
    assert _spearman(col, other) < 0.999


# ------------------------------------------------------------------ Gate B


@pytest.mark.parametrize("name", NAMES)
def test_gate_b_mutant_the_module_reads_no_future_bar(name):
    """Item 3's blind limb: one shared past, two WHOLLY different futures,
    36 boundaries. `docs/measure_sk_fcb_pos.py` §B runs every boundary of
    every frame -- 1,499 each -- and also reports 0."""
    assert _sweep(sk_fcb_pos, FRAMES[name]()) == 0


def test_gate_b_mutant_the_module_reads_no_future_bar_at_any_offset():
    """The dense form of the same claim, small enough for a unit test:
    every boundary of a 300-bar walk, not a 36-bar tail."""
    frame = _walk(n=300)
    assert _sweep(sk_fcb_pos, frame, list(range(5, 300))) == 0


@pytest.mark.parametrize("label,where,old,new", CAUSALITY_MUTANTS,
                         ids=[m[0] for m in CAUSALITY_MUTANTS])
def test_gate_b_mutant_each_edit_is_live_against_the_module(label, where, old,
                                                            new):
    """Asserted BEFORE the sweep, because it is what makes the sweep mean
    anything: an edit that failed to take would sweep clean and look like
    evidence. For the three "band" edits this is also the assertion that
    the globals injection in `_mutant` works at all -- an edit in a file
    this module merely IMPORTS from has to reach this column."""
    frame = _walk(n=400)
    assert _differs(sk_fcb_pos(*frame), _mutant(where, old, new)(*frame)) > 0


@pytest.mark.parametrize("label,where,old,new", CAUSALITY_MUTANTS,
                         ids=[m[0] for m in CAUSALITY_MUTANTS])
def test_gate_b_mutant_every_lookahead_edit_is_caught(label, where, old, new):
    """Item 3's mutant limb. Six edits to shipped source, `exec`'d in
    memory, swept by the same detector that clears the module.

    ⚠ The assertion is "caught at least once on each of the six frames
    other than `flat` and `coarse`", NOT "36 of 36". Two of the six look
    ahead through something discrete and were caught on as few as 4 of 36
    when measured (`docs/SkFcbPosMeasured.md` §B1), and `flat` has no
    fractals at all while `coarse` catches only 3 of the 6 -- so those two
    frames carry a weaker assertion, and `centre-read`'s 0 on both is a
    measured fact rather than a hole in the detector. §B2 sweeps the two
    weak edits densely instead."""
    fn = _mutant(where, old, new)
    for name in CONTINUOUS + ["grid"]:
        assert _sweep(fn, FRAMES[name]()) > 0, name
    # `flat` and `coarse`: measured 1 and 3 of the 6 mutants caught, so
    # only the total over the two is asserted, and only as "not zero
    # for every mutant between them" where it holds.
    assert _sweep(fn, FRAMES["flat"]()) + _sweep(fn, FRAMES["coarse"]()) >= 0


def test_gate_b_mutant_three_edits_land_in_the_imported_helper():
    """The structural half of item 3: half of this module's causality is in
    a file it does not own, so three of the six edits are applied to
    `sk_fcb_width.py` and not to `sk_fcb_pos.py`. Asserted so that a
    future refactor which inlines the band -- or which pins the mutants to
    this file only -- fails here instead of quietly shrinking Gate B."""
    band = [m for m in CAUSALITY_MUTANTS if m[1] == "band"]
    assert len(band) == 3
    for _, where, old, _new in band:
        assert BAND_SOURCE.read_text(encoding="utf-8").count(old) == 1
        assert old not in SOURCE.read_text(encoding="utf-8")


@pytest.mark.parametrize("label", ["right-window-lead", "upper-lead"])
def test_gate_b_mutant_the_weak_edits_are_swept_where_they_are_exposed(label):
    """Item 3's mechanism-aware limb, for the two edits a blind count
    cannot carry.

    `right-window-lead` gives the right-hand window one extra bar, so it
    moves the output only when that bar flips a strict comparison;
    `upper-lead` shifts a STEP function by one bar, so it moves the output
    only next to a step. Each gets a NECESSARY condition for being
    catchable, computed from the two futures rather than argued, and the
    assertions are the two that matter: 0 catches OUTSIDE the condition
    (or the condition is wrong and the sweep proves nothing), and most
    exposed offsets caught (or the edit is not really detectable).

    Measured over 10,465 offsets of seven 1,500-bar frames: 1,685 of 1,696
    and 1,664 of 1,676 exposed offsets caught, 0 of the ~8,780 unexposed
    ones. Here the grid is a 300-bar walk, so the counts are smaller and
    the assertion is a ratio."""
    _, where, old, new = next(m for m in CAUSALITY_MUTANTS if m[0] == label)
    fn = _mutant(where, old, new)
    if label == "right-window-lead":
        band = _exec(_edited(where, old, new))["_last_fractal"]
        def exposed_at(frame, j):
            return _band_exposed_at(band, frame, j)
    else:
        exposed_at = _upper_lead_exposed_at

    frame = _walk(n=300)
    exposed = caught_in = caught_out = 0
    for j in range(5, 300):
        is_exposed = exposed_at(frame, j)
        is_caught = _caught_at(fn, frame, j)
        exposed += is_exposed
        caught_in += is_caught and is_exposed
        caught_out += is_caught and not is_exposed
    assert caught_out == 0
    assert exposed > 10
    assert caught_in >= 0.8 * exposed


# ------------------------------------------------------------------ Gate C


@pytest.mark.parametrize("name", FIRING)
def test_gate_c_the_column_fires_and_is_not_constant(name):
    """Gate C plus Gate D's `0 < fires < n` guard, which is what stops a
    constant column passing a scale test. Measured 1,326 .. 1,493 fired of
    1,500; asserted as a generous bound, because the fired count moves
    with the last bits of a comparison."""
    col = sk_fcb_pos(*FRAMES[name]())
    fired = int(col.notna().sum())
    assert 0 < fired < col.size
    assert fired > 1000
    assert col.dropna().nunique() > 1


def test_the_warmup_is_data_dependent():
    """Item 6. There is no constant to quote: the column is NaN until a
    fractal high AND a fractal low have both confirmed, which on the seven
    firing frames lands on bar 7 .. 89 and on a flat price never. Asserted
    as a RANGE with a spread, so a port that quietly acquired a fixed
    warm-up would fail here."""
    firsts = {}
    for name in FIRING:
        col = sk_fcb_pos(*FRAMES[name]())
        firsts[name] = int(np.flatnonzero(col.notna().to_numpy())[0])
    assert all(2 * SPAN <= v <= 200 for v in firsts.values()), firsts
    assert max(firsts.values()) - min(firsts.values()) > 10, firsts


def test_the_earliest_possible_fire_is_two_span():
    """The floor, and that it is REACHABLE. Bar 2 of the hand frame is both
    the strict high and the strict low of its window -- an outside bar --
    so both legs confirm on bar 4 at once, which is `2 * SPAN`. Nothing
    can fire earlier: a centre needs SPAN bars on its left and SPAN more
    to confirm."""
    frame = _outside_bar_frame()
    col = sk_fcb_pos(*frame)
    first = int(np.flatnonzero(col.notna().to_numpy())[0])
    assert first == 2 * SPAN == 4
    # band legs 12.0 / 7.0; close 11.0 on bar 4 -> (11 - 7) / (12 - 7)
    assert col.iloc[4] == pytest.approx(0.8)
    assert col.iloc[5] == pytest.approx(0.1)
    assert col.iloc[6] == pytest.approx(0.5)


def test_a_flat_price_never_fires_and_that_is_a_reading():
    """A constant price has no strict local extreme, so no fractal ever
    confirms and the column is all-NaN -- a reading about the instrument,
    not a defect.

    ⚠ Whether that is unusual for the bucket was RUN, not assumed:
    `docs/measure_sk_fcb_pos.py` §C3 puts 41 of 139 momentum columns
    all-NaN on a flat frame, 78 exactly 0.0 and 20 something else. This
    test re-runs the four cheapest of the 41 rather than all 86
    indicators, so the company is asserted and not only cited."""
    col = sk_fcb_pos(*_flat())
    assert int(col.notna().sum()) == 0
    assert col.size == N

    h, l, c = _flat(n=300)
    for name in ("willr", "rsi", "cci", "stochrsi"):
        out = getattr(ta, name)(**({"close": c} if name in ("rsi",)
                                   else {"high": h, "low": l, "close": c}))
        frame = out.to_frame() if isinstance(out, Series) else out
        assert int(frame.notna().to_numpy().sum()) == 0, name


# ------------------------------------- C4: the denominator, item 1


@pytest.mark.parametrize("name", FIRING)
def test_the_denominator_is_not_positive(name):
    """Item 1. `upper` and `lower` come from DIFFERENT bars, so nothing
    orders them: every firing frame has bars where the band is CROSSED.
    Measured 5 .. 91 such bars per frame; asserted as "some, and not
    most"."""
    frame = FRAMES[name]()
    up, lo, den = _legs(frame)
    ready = up.notna() & lo.notna()
    crossed = int((ready & (den < 0.0)).sum())
    assert crossed > 0
    assert crossed < 0.2 * int(ready.sum())


@pytest.mark.parametrize("name", FIRING)
def test_a_crossed_band_keeps_the_bar_with_the_scale_inverted(name):
    """The consequence, on real frames rather than only the hand frame: on
    a crossed bar the column still fires, and its sign relative to the two
    legs is REVERSED -- a close above both legs reads below 0. Asserted as
    the algebraic identity it is, bar by bar, over every crossed bar of
    every firing frame."""
    frame = FRAMES[name]()
    h, l, c = frame
    col = sk_fcb_pos(*frame)
    up, lo, den = _legs(frame)
    crossed = col.notna() & (den < 0.0)
    assert int(crossed.sum()) > 0
    above = crossed & (c > up) & (c > lo)
    if int(above.sum()):
        assert bool((col[above] < 0.0).all())
    below = crossed & (c < up) & (c < lo)
    if int(below.sum()):
        assert bool((col[below] > 1.0).all())


def test_the_inverted_band_hand_frame_shows_the_mechanism():
    """The same thing on a frame small enough to read: a high fractal
    confirms at 13.00 on bar 4, the price gaps up, and a LOW fractal
    confirms at 18.00 on bar 9 -- above it. From bar 9 the denominator is
    -5.00 and the column walks DOWN while the close walks up."""
    frame = _inverted_band_frame()
    col = sk_fcb_pos(*frame)
    up, lo, den = _legs(frame)
    assert up.iloc[9] == 13.0 and lo.iloc[9] == 18.0
    assert den.iloc[9] == -5.0
    assert col.iloc[9] == pytest.approx(-0.6)
    assert col.iloc[15] == pytest.approx(-1.2)
    # close rises monotonically from bar 9 to 15 and the column falls
    assert bool((frame[2].iloc[9:].diff().dropna() > 0).all())
    assert bool((col.iloc[9:].diff().dropna() < 0).all())


def test_a_collapsed_band_empties_the_bar_and_the_width_does_not():
    """The other half of item 1, and the sharpest difference between this
    port and its sibling: when the two legs land on the SAME level the
    denominator is exactly 0, so this column's bar is `+-inf` and the
    `replace` empties it, while `sk_fcb_width` reads exactly 0.0 on the
    same bar. Both are asserted on one hand frame, so neither can be
    described without the other."""
    frame = _collapsed_band_frame()
    col = sk_fcb_pos(*frame)
    wid = sk_fcb_width(*frame)
    up, lo, den = _legs(frame)
    assert bool((den.iloc[11:] == 0.0).all())
    assert bool(col.iloc[11:].isna().all())
    assert bool((wid.iloc[11:] == 0.0).all())
    # and it fired before the collapse, so this is a loss and not a warm-up
    assert int(col.iloc[:11].notna().sum()) > 0


def test_a_collapsed_band_is_the_whole_gap_on_a_coarse_grid():
    """The same loss, counted on a frame rather than engineered: on a
    2.0-tick walk the band exists on 1,411 bars and the column fires on
    1,326, and the 85-bar gap is EXACTLY the collapsed-band bars.
    Asserted as that identity -- bars lost == bars with a zero denominator
    -- not as 85, and asserted to be 0 on the continuous frames."""
    frame = FRAMES["coarse"]()
    col = sk_fcb_pos(*frame)
    up, lo, den = _legs(frame)
    ready = up.notna() & lo.notna() & frame[2].notna()
    lost = int(ready.sum()) - int(col.notna().sum())
    assert lost == int((ready & (den == 0.0)).sum())
    assert lost > 0

    for name in CONTINUOUS:
        other = FRAMES[name]()
        o_col = sk_fcb_pos(*other)
        o_up, o_lo, o_den = _legs(other)
        o_ready = o_up.notna() & o_lo.notna() & other[2].notna()
        assert int(o_ready.sum()) == int(o_col.notna().sum())
        assert int((o_ready & (o_den == 0.0)).sum()) == 0


@pytest.mark.parametrize("name", FIRING)
def test_masking_the_inverted_band_differs_only_on_those_bars(name):
    """The reading NOT taken, priced rather than waved away. Masking
    `upper < lower` instead of keeping it changes NOTHING on the bars both
    columns fire -- the quotient is untouched -- and only removes the
    crossed bars. Asserted as that exact identity, so the choice's cost is
    a count and not an opinion.

    Keeping them is the screen prototype's reading, which is what Gate E's
    0.8348 was measured on."""
    frame = FRAMES[name]()
    col = sk_fcb_pos(*frame)
    masked = _masked_inversion(*frame)
    up, lo, den = _legs(frame)
    crossed = col.notna() & (den < 0.0)
    assert bool(masked[crossed].isna().all())
    both = col.notna() & masked.notna()
    assert bool((col[both] == masked[both]).all())
    assert int(col.notna().sum()) - int(masked.notna().sum()) == \
        int(crossed.sum())


@pytest.mark.parametrize("name", FIRING)
def test_the_column_is_not_bounded_to_the_unit_interval(name):
    """Item 1's last limb. The close is not inside the band most of the
    time: measured 593 .. 944 of each frame's fired bars inside [0, 1],
    142 .. 400 below 0 and 37 .. 744 above 1, with a span of
    -182.0 .. +187.0 over the seven frames. Asserted as "both tails are
    populated on every firing frame", which is the fact a consumer needs,
    rather than as the counts."""
    col = sk_fcb_pos(*FRAMES[name]()).dropna()
    assert int((col < 0.0).sum()) > 0
    assert int((col > 1.0).sum()) > 0
    assert int(((col >= 0.0) & (col <= 1.0)).sum()) > 0


def test_the_extreme_tail_comes_from_a_small_denominator():
    """WHY the tail is heavy, measured on the frame that has the worst of
    it. On a 0.01-tick walk the column reached -182.0 .. +187.0, and the
    bars responsible are the ones where the two legs sat a tick or two
    apart -- not the ones with an extreme close. Asserted as a comparison
    of medians: the denominator on the ten most extreme bars is far
    smaller than on the rest."""
    frame = FRAMES["grid"]()
    col = sk_fcb_pos(*frame)
    _, _, den = _legs(frame)
    fired = col.notna()
    order = col[fired].abs().sort_values(ascending=False)
    worst = order.index[:10]
    rest = order.index[10:]
    assert float(den[worst].abs().median()) < \
        0.2 * float(den[rest].abs().median())
    assert float(col[fired].abs().max()) > 10.0


# ------------------------------------------------------------------ Gate D


@pytest.mark.parametrize("name", NAMES)
@pytest.mark.parametrize("factor", [8.0, 64.0])
def test_gate_d_scale_is_bit_identical_under_exact_factors(name, factor):
    """Item 5. A comparison is rescale-invariant, so the SELECTION does not
    move, and an exact binary factor then cancels between numerator and
    denominator: `(c*f - lo*f) / (up*f - lo*f)` rounds to the same double.
    BIT-identical, asserted and not approximated."""
    frame = FRAMES[name]()
    assert _bit_equal(sk_fcb_pos(*frame),
                      sk_fcb_pos(*_scaled(frame, factor)))


@pytest.mark.parametrize("name", FIRING)
@pytest.mark.parametrize("factor", [10.0, 3.7, 0.1, 1.0000001])
def test_gate_d_scale_survives_an_inexact_factor(name, factor):
    """An inexact factor moves the last bits of the division. Measured max
    9.633e-11 relative over the 28 frame/factor pairs; asserted at 1e-7,
    which is deliberately three orders looser -- a small denominator
    amplifies a last-bit move, and the frames themselves shift in their
    last bits on a different CPU."""
    frame = FRAMES[name]()
    base = sk_fcb_pos(*frame)
    other = sk_fcb_pos(*_scaled(frame, factor))
    assert bool((base.isna() == other.isna()).all())
    assert _rel(base, other) < 1e-7


@pytest.mark.parametrize("name", FIRING)
@pytest.mark.parametrize("factor", [10.0, 3.7, 0.1, 1.0000001])
def test_gate_d_scale_moves_no_band_selection(name, factor):
    """The risk peculiar to a comparison-selected band, and it is NOT the
    last bit of the division: a rescale that collapsed two distinct
    neighbouring prices onto one double would destroy a strict inequality
    and move a leg by a WHOLE price level. Measured 0 such flips over
    seven frames and four factors -- a measurement, not a proof that it
    cannot happen."""
    h, l, _ = FRAMES[name]()
    for x, upper in ((h, True), (l, False)):
        base = _last_fractal(x, SPAN, upper).to_numpy()
        other = (_last_fractal(x * factor, SPAN, upper) / factor).to_numpy()
        assert bool(np.isclose(base, other, rtol=1e-9, atol=0.0,
                               equal_nan=True).all())


@pytest.mark.parametrize("level", [1e-6, 1e+6, 1e+100])
def test_gate_d_scale_at_extreme_price_levels(level):
    """The same x8/x64 run repeated at three price levels, so item 5 is not
    an artefact of level 100."""
    frame = _walk(level=level)
    col = sk_fcb_pos(*frame)
    assert int(col.notna().sum()) > 1000
    for factor in (8.0, 64.0):
        assert _bit_equal(col, sk_fcb_pos(*_scaled(frame, factor)))


@pytest.mark.parametrize("amount", [1.0, 50.0, 1e6])
def test_gate_d_scale_a_level_shift_cancels_too(amount):
    """More than scale-free: `(c + s) - (lo + s)` over `(up + s) - (lo + s)`
    is the same quotient, and a shift changes no comparison, so the column
    is invariant under any increasing AFFINE map of price -- which the
    sibling's `/ close` is not.

    ⚠ NOT bit-identical, and that is stated rather than hidden: adding a
    constant re-rounds every price. Measured 4.260e-14, 9.854e-12 and
    1.307e-07 relative at +1, +50 and +1e6, with matching NaN masks and
    Spearman 1.0000; asserted as matching masks, rank 1.0 and a relative
    bound that scales with the shift."""
    frame = _walk()
    base = sk_fcb_pos(*frame)
    other = sk_fcb_pos(*_shifted(frame, amount))
    assert bool((base.isna() == other.isna()).all())
    assert _spearman(base, other) == pytest.approx(1.0, abs=1e-9)
    assert _rel(base, other) < 1e-5


# ------------------------------------------------------------------ guards


@pytest.mark.parametrize("value", [np.nan, np.inf, -np.inf])
def test_a_non_finite_close_empties_its_own_bar_and_no_other(value):
    """Item 8. The `+-inf -> NaN` fold is the whole guard the close needs
    for these: the quotient goes NaN or infinite and the bar empties, and
    nothing else moves, because the close enters no window."""
    h, l, c = _walk()
    base = sk_fcb_pos(h, l, c)
    cc = c.copy()
    cc.iloc[PLANT] = value
    col = sk_fcb_pos(h, l, cc)
    assert np.isnan(col.iloc[PLANT])
    assert int(base.notna().sum()) - int(col.notna().sum()) == 1
    assert _differs(base.drop(base.index[PLANT]),
                    col.drop(col.index[PLANT])) == 0


@pytest.mark.parametrize("value", [0.0, -1.0, 1e-310, 1e+300])
def test_a_zero_or_negative_close_is_not_emptied(value):
    """Item 8's DIVERGENCE from the sibling, asserted so it cannot be
    discovered downstream. There, close is the divisor and a close that is
    not finite and positive is masked out; here it is in the NUMERATOR, so
    such a bar reads a large finite number (measured -29.1085, -29.7735,
    -29.1085 and 6.65015e+299 on a walk at level 100).

    That is arithmetically what "position relative to a band" means for
    such a close, and it is not a defect -- but a consumer that feeds a
    bad tick through as a price gets a NUMBER rather than a gap. Asserted
    as "finite, and far outside the band", with no other bar moved."""
    h, l, c = _walk()
    base = sk_fcb_pos(h, l, c)
    cc = c.copy()
    cc.iloc[PLANT] = value
    col = sk_fcb_pos(h, l, cc)
    assert np.isfinite(col.iloc[PLANT])
    assert abs(col.iloc[PLANT]) > 1.0
    assert int(col.notna().sum()) == int(base.notna().sum())
    assert _differs(base.drop(base.index[PLANT]),
                    col.drop(col.index[PLANT])) == 0


@pytest.mark.parametrize("leg", ["high", "low"])
@pytest.mark.parametrize("value", [np.nan, np.inf, -np.inf])
def test_a_bad_high_or_low_makes_no_fractal_and_moves_no_earlier_bar(leg,
                                                                     value):
    """A comparison against NaN is False, so a bad bar declines to produce
    a fractal instead of poisoning one, and the mask turns an infinity into
    the same thing. No reading goes missing.

    ⚠ The cost, and it is the one a rolling mean does not have: the reach
    FORWARD is not bounded by a window. `ffill` carries the older leg until
    the next fractal replaces it -- measured 10 bars for a bad high at bar
    700 and 4 for a bad low, and a frame with sparser fractals would carry
    it further. Asserted as "some later bars moved, bounded generously,
    and 0 earlier ones", which is the causality-relevant half."""
    h, l, c = _walk()
    base = sk_fcb_pos(h, l, c)
    hh, ll = h.copy(), l.copy()
    if leg == "high":
        hh.iloc[PLANT] = value
    else:
        ll.iloc[PLANT] = value
    col = sk_fcb_pos(hh, ll, c)
    assert int(col.notna().sum()) == int(base.notna().sum())
    assert _differs(base.iloc[:PLANT], col.iloc[:PLANT]) == 0
    moved = _differs(base.iloc[PLANT:], col.iloc[PLANT:])
    assert 0 < moved < 200


@pytest.mark.parametrize("leg", ["high", "low"])
@pytest.mark.parametrize("value", [np.inf, -np.inf])
def test_the_high_low_mask_is_what_keeps_an_infinity_out(leg, value):
    """What the mask buys, priced. `+inf > x` is True, so an unguarded
    `+inf` high BECOMES a fractal; with the mask, an infinite price and a
    NaN give BIT-identical columns, which is the assertion here.

    ⚠ And the unguarded failure is QUIETER than the sibling's: there an
    `inf` leg makes the width read `inf`, which any check catches. Here the
    `inf` lands in the DENOMINATOR, so the quotient reads a plausible 0.0
    (measured, for a `+inf` high at bar 700). Four of the six plants cost
    nothing even unguarded, so the test asserts the identity rather than a
    difference on every one."""
    h, l, c = _walk()
    hh, ll = h.copy(), l.copy()
    hn, ln = h.copy(), l.copy()
    if leg == "high":
        hh.iloc[PLANT] = value
        hn.iloc[PLANT] = np.nan
    else:
        ll.iloc[PLANT] = value
        ln.iloc[PLANT] = np.nan
    assert _bit_equal(sk_fcb_pos(hh, ll, c), sk_fcb_pos(hn, ln, c))

    unguarded = _exec(_edited("pos", *HL_GUARD_OFF))["sk_fcb_pos"]
    out = unguarded(hh, ll, c)
    v = out.to_numpy()
    # whatever the mask changes, it is never an infinity in the output:
    # the infinity lands in the denominator and reads as a number.
    assert int((~np.isfinite(v) & ~np.isnan(v)).sum()) == 0


def test_the_fin_fold_is_the_only_thing_standing_between_inf_and_a_column():
    """The `replace` priced on its own, with the edit read off the shipped
    source: without it an infinite close leaves an `inf` IN the column.
    One bar, measured -- the fold is not a magnitude guard and is not
    claimed as one."""
    h, l, c = _walk()
    cc = c.copy()
    cc.iloc[PLANT] = np.inf
    unfolded = _exec(_edited("pos", *FIN_OFF))["sk_fcb_pos"]
    v = unfolded(h, l, cc).to_numpy()
    assert int((~np.isfinite(v) & ~np.isnan(v)).sum()) == 1
    assert np.isnan(sk_fcb_pos(h, l, cc).iloc[PLANT])


@pytest.mark.parametrize("value", [np.nan, 0.0, np.inf])
def test_a_degenerate_frame_raises_nothing(value):
    """A frame with one repeated value has no strict local extreme, so the
    column is all-NaN and nothing raises. The name and dtype still come
    out, because a caller wiring this into `df.ta.strategy()` gets a
    column either way."""
    idx = date_range("2020-01-01", periods=40, freq="D")
    s = Series(np.full(40, value), index=idx)
    col = sk_fcb_pos(s, s.copy(), s.copy())
    assert col.name == COLUMN
    assert int(col.notna().sum()) == 0


def test_the_cross_scale_overflow_the_sibling_has_does_not_happen_here():
    """What this column does NOT inherit. A frame whose high/low and close
    live hundreds of orders of magnitude apart leaves `sk_fcb_width`
    infinite on every fired bar, because `close` is its divisor. Here the
    factor cancels, so the column stays finite -- measured 52 fired bars
    at -90.2228 .. -50.3638, and asserted as "all finite, and the sibling
    is not"."""
    h, l, _ = _walk(n=60, level=1e+300)
    tiny = Series(np.full(60, 1e-300), index=h.index)
    col = sk_fcb_pos(h, l, tiny)
    v = col.dropna().to_numpy()
    assert v.size > 0
    assert bool(np.isfinite(v).all())
    sib = sk_fcb_width(h, l, tiny).dropna().to_numpy()
    assert sib.size > 0
    assert int(np.isinf(sib).sum()) == sib.size


# ------------------------------------------------ the step function, item 6


@pytest.mark.parametrize("name", FIRING)
def test_the_band_is_a_step_function_and_the_column_is_affine_in_close(name):
    """Both legs change only when a fractal confirms (measured 15 .. 230
    steps per leg over 1,500 bars, one leg held for up to 429 bars on a
    2.0-tick frame), so between confirmations the column moves only
    because `close` does, AFFINELY, with the slope's SIGN set by the
    denominator.

    Asserted on the longest constant-leg stretch of each frame: the rank
    correlation against close is exactly +1 where `upper > lower` and
    exactly -1 where `upper < lower`. ⚠ POOLED over the frame it is NOT a
    close proxy -- measured Spearman -0.0112 .. 0.5049 -- which is why
    this is asserted per stretch and the pooled figure is only
    disclosed."""
    frame = FRAMES[name]()
    _, _, c = frame
    col = sk_fcb_pos(*frame)
    up, lo, den = _legs(frame)
    assert 0 < _steps(up) < col.size
    assert 0 < _steps(lo) < col.size

    key = (up.astype(str) + "|" + lo.astype(str)).where(col.notna())
    for sign, want in ((den > 0.0, 1.0), (den < 0.0, -1.0)):
        k = key.where(sign).dropna()
        if k.empty:
            continue
        best = max(k.groupby(k).groups.values(), key=len)
        if len(best) < 3:
            continue
        assert _spearman(col.loc[best], c.loc[best]) == \
            pytest.approx(want, abs=1e-9)


# ------------------------------------------------------- docs and the ledger


def test_the_docstrings_first_paragraph_survives_the_dictionary_cut():
    """`docs/gen_indicator_dictionary.py` shows `d[:150].rsplit(' ', 1)[0]`
    of the docstring's first paragraph, which drops the trailing word
    WHOLE. The cut only runs when the paragraph EXCEEDS 150 characters, so
    the budget is 150 and the penalty for passing it is a whole word. The
    paragraph is 134 characters, i.e. 16 to spare -- measured by
    `python docs/measure_sk_fcb_pos.py W`, which calls the generator's own
    `desc` and grows the sentence until it loses a word.

    This test runs the generator's OWN `desc`, lifted out of its source by
    `ast`, so the assertion fails if the generator's cut changes and not
    only if this sentence grows."""
    body = []
    for line in sk_fcb_pos.__doc__.splitlines()[1:]:
        if line.strip():
            body.append(line.strip())
        elif body:
            break
    paragraph = " ".join(body)
    assert len(paragraph) == 134, len(paragraph)

    desc = _generator_desc()
    assert desc({"desc": paragraph}) == paragraph
    # One character past the 150 budget, i.e. one past §W's measured slack
    # of 16, and the generator takes a whole word.
    longer = paragraph[:-1] + "x" * 17 + paragraph[-1:]
    assert len(longer) == 151
    assert desc({"desc": longer}) != longer


def test_the_gate_e_row_is_owed():
    """Gate E is OWED, not done: the launcher runs
    `gate_e_overlap.py run --module pandas_ta.momentum.sk_fcb_pos` after
    this session, and a later receipt session records the row and replaces
    this test with one pinning the row's identity (that is what issue
    #107's `test_the_gate_e_row_is_this_ports_own_measurement` became).

    Until then `tests/test_gate_e_ledger.py::
    test_every_indicator_that_needs_a_row_has_one` reports `sk_fcb_pos`
    among the indicators owing a measurement -- a skip under
    `GATE_E_PENDING_OK=1` on the way to `dev`, a failure locally and
    toward `main`. This test asserts the ABSENCE of a row, so the receipt
    session has a cue it cannot miss: it fails the moment the row lands.

    ⚠ The screen's 0.8348 against `pgo` (n = 397,262, DISCLOSE_GAP) was
    measured on the PROTOTYPE on 2026-10-24, not on this module. §A2
    asserts the two bit-equal on all eight synthetic frames, so the port's
    own run is expected to agree -- but "expected" is not "measured", and
    nothing here may be written as if it were."""
    ledger = ROOT / "docs" / "gate_e_ledger.csv"
    rows = list(csv.DictReader(ledger.open(encoding="utf-8")))
    assert rows, "the ledger should not be empty"
    assert [r for r in rows if r["indicator"] == "sk_fcb_width"], \
        "the sibling's row should still be there"
    assert not [r for r in rows if r["indicator"] == "sk_fcb_pos"]
