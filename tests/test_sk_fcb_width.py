# -*- coding: utf-8 -*-
"""SK-FCB-WIDTH: `sk_fcb_width`, the Fractal Chaos Band width over close
(PandasTa issue #107, Skender Stock.Indicators' `Fcb`, Apache-2.0).

    SK_FCB_WIDTH_2 = (last confirmed fractal high
                      - last confirmed fractal low) / close

What this file pins, in order of how much it would hurt to lose:

1. **Gate A, the formula spelled two ways -- ONE of them independent.** A
   transcription of Skender's `Fractal` double loop plus `Fcb`'s
   roll-forward, sharing no code with the module, and the screen prototype
   that the 2026-10-24 catalog screen measured at Gate E. Both are
   asserted BIT-equal to the module, with identical NaN masks, on all
   eight synthetic frames (10,330 fired bars as measured here). Nothing is
   a tolerance: a band leg is a SELECTED price level, so the only
   arithmetic is one subtraction and one division.
   ⚠ The prototype limb is NOT a second derivation: `_prototype`'s
   `last_fractal` is the module's `_last_fractal` operation for operation,
   so its bit-equality on a clean frame is structural. What it buys is the
   TIE to the screen's Gate E figures and the guards priced at zero.
2. **The index divergence, named and measured.** Skender's `Fractal`
   returns a level ON its centre bar; this port reads it `SPAN` bars
   later, when the right-hand bars exist. The centre reading is built
   independently here, asserted to be a DIFFERENT column (46 .. 839 bars
   differ, Spearman 0.4638 .. 0.9643 as measured here), and asserted to
   be exactly what the `centre-read` mutant produces -- so the mutant is
   the documented alternative reading rather than an invented edit.
   ⚠ What is NOT pinned, because it cannot be: what `Fcb.Series.cs` does
   with that index. The file is unreadable from this worktree, which
   `test_the_source_library_is_not_readable_here` records.
3. **Gate B, causality.** A sweep that splits a frame into one shared past
   and two WHOLLY different futures catches the module on 0 of 36 offsets
   on each of the eight frames, and on 0 of 299 -- every bar but bar 0 --
   of a 300-bar walk, so the dense form of the claim has an assertion
   behind it and not only `docs/measure_sk_fcb_width.py` §B's 0 of 1,499
   (every bar but bar 0, of 1,500) on each of the eight. Five look-ahead
   mutants are read off the shipped source, edited and `exec`'d in memory;
   each is caught on each of the six frames other than `flat` and
   `coarse`.
   ⚠ A mutant is NOT caught on 36 of 36 and the test does not ask it to:
   three of the five look ahead through a COMPARISON, so the edit is
   invisible at an offset where the fractal decisions near the boundary
   come out the same either way. The weakest -- one extra bar of
   right-hand window -- was caught on 4 of 36 on `jump` when measured, so
   the assertion is "caught somewhere, on every one of those six frames",
   plus a separate assertion that each mutant is LIVE against the module,
   plus a MECHANISM-AWARE sweep for that weakest one: its exposure
   condition is derived from the edit, and the test asserts 0 catches
   outside it and 0 unexplained misses inside it.
4. **Gate D, scale.** x8/x64 bit-identical on every fired bar of all eight
   frames and at price levels 1e-6, 1e+6 and 1e+100, because a comparison
   is rescale-invariant and an exact binary factor cancels in
   `(a*f - b*f) / (c*f)`. x10/x3.7/x0.1/x1.0000001 within 1e-9 relative
   with matching NaN masks (measured max 1.229e-12), and -- the risk
   peculiar to this column -- 0 bars where an inexact rescale moved the
   fractal SELECTION, which would move the band by a whole price level.
5. **Gate C, reachability, and the three facts a consumer gets wrong.**
   The warm-up is DATA-DEPENDENT (first fire on bar 7 .. 89 across the
   frames here, and NEVER on a flat price, which fires 0 of 1,500); the
   column is NOT a non-negative width (negative on 5 .. 91 bars of each
   firing frame, plus exactly 0.0 on 85 bars of the 2.0-tick frame, which
   takes `<= 0` to 5 .. 105); and it is a STEP function over a moving
   divisor.
6. **The strict predicate against a tick grid.** `>` and not `>=`, so a
   tie destroys a fractal. The non-strict reading is bit-identical on the
   five continuous frames and a different column on a 2.0-tick frame
   (Spearman 0.0567 as measured here). This is the FVGDEAD lesson in
   `CLAUDE.md` applied in advance: synthetic continuous floats cannot see
   it, and 21.17% of real BIST daily bars close exactly at an extreme.
7. **The guards, and what each buys.** A bad close empties its own bar and
   no other (6 plants). A bad high or low makes no fractal instead, moves
   no EARLIER bar, and its forward reach is not bounded by a window. The
   high/low guard exists for infinities only: unguarded, a `+inf` high
   becomes a fractal and the band carries `inf`.
8. **Gate E is SHIP, and whose measurement the ledger row is.**
   `test_the_gate_e_row_is_this_ports_own_measurement` pins the row to run
   `is107-sk_fcb_width-8f25baf3` (2026-11-15, on THIS module): pooled
   **0.6104** against the engine's `natr` at n = 397,416, top-five
   per-frame max median **0.5846** over 89 frames, 687 comparators, no
   waiver. That is the SHIP band, pinned as the band's BOUND (pooled and
   per-frame both below 0.76) and not as digits. The screen's PROTOTYPE
   read the same digits on 2026-10-24, and item 1's §A2 limb asserts this
   module bit-equal to that prototype -- an expected agreement is the
   easiest kind of row to copy over by mistake, so the row's identity is
   pinned and not only its arithmetic.
   `test_the_gate_e_run_closes_gate_c_on_real_data` reads Gate C's real
   limb off the same row: 397,609 of 398,849 bars fire, the 1,240 empty
   ones are NOT a whole number of bars per frame (13.93 on average), which
   is item 5's data-dependent warm-up on real data, and 108 fired bars
   read exactly 0.0, which is item 5's tick-grid zero on real prices.
   ⚠ Not pinned, because the band does not read it: no single one of the
   89 frames reaches even 0.80 on any of the top five comparators (the
   worst is 0.6785, on the top one). ⚠ Not available at all: the row
   counts NaNs and zeros, not SIGNS, so item 5's negative readings stay a
   synthetic figure.

Every number above is printed by `python docs/measure_sk_fcb_width.py` on
this tree, and `python docs/measure_sk_fcb_width_cpu.py` re-runs this
module -- and any named section -- with numpy's `AVX512F`, `AVX512_SKX`,
`AVX2` and `FMA3` dispatch disabled. Counts and Spearman figures quoted in
this file's prose are THIS machine's; the assertions are bounds, bands and
structural relations, so a kernel that moves a price's last bits cannot
fail them.

⚠ The in-fork Spearman figures of `docs/SkFcbWidthMeasured.md` §F are
SYNTHETIC and are disclosures, not gates: the 687 engine comparators hold
no pandas_ta port, and against `natr` this file's seven firing frames read
0.0722 .. 0.3202 -- while the screen's OWN fork stage measured the
identical pair at 0.5873 on 12 REAL frames (per-frame max median 0.5772),
i.e. roughly 0.27 above these, and this port's OWN Gate E run read 0.6104
against the engine's `natr` on 89 real frames (item 8). The synthetic
frames understated it badly, so they were not evidence about Gate E either
way; §F also records that the obvious explanation for the gap was tested
and refuted, and §E3 that the fork's `natr:NATR_14` is not the engine's
`natr` -- this session did not read the engine.
"""
import csv
import importlib.util
from pathlib import Path

import numpy as np
import pytest
from pandas import DataFrame, Series, date_range

from .context import pandas_ta  # noqa: F401

import pandas_ta as ta
from pandas_ta.volatility.sk_fcb_width import (MIN_BARS, SPAN, _last_fractal,
                                               sk_fcb_width)

N = 1500
LEVEL = 100.0
COLUMN = "SK_FCB_WIDTH_2"
#: The causality sweep's 36 perturbation points.
OFFSETS = list(range(N - 36, N))
#: Where the guard sections plant a bad bar.
PLANT = 700


# ------------------------------------------------------------------ frames
# Same builders and seeds as `docs/measure_sk_fcb_width.py`, so a number in
# this file and a number in the receipt are the same measurement. The first
# seven are `tests/test_j_acosc.py`'s, unchanged; `coarse` is this
# indicator's own.


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
    """A walk rounded to a tick COARSER than its own bar-to-bar move, so
    that ties -- the thing the strict predicate is sensitive to -- are
    common instead of impossible."""
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
#: Continuous: no two prices within SPAN of each other can tie.
CONTINUOUS = ["walk", "trend", "range-bound", "heavy-tailed", "jump"]
#: The frames every mutant was caught on. `flat` never fires and `coarse`
#: barely moves its band, so neither can see every look-ahead; both are
#: measured in `docs/SkFcbWidthMeasured.md` §B rather than hidden here.
MUTANT_FRAMES = [n for n in NAMES if n not in ("flat", "coarse")]


def _scaled(frame, factor):
    h, l, c = frame
    return h * factor, l * factor, c * factor


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


def _bit_equal(a, b):
    if not bool((a.isna() == b.isna()).all()):
        return False
    m = a.notna()
    return bool((a[m] == b[m]).all())


def _steps(leg):
    """How many times a band leg changes level after it first fires."""
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
    it. ⚠ Transcribed from the formula issue #107 names, NOT from a reading
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


def _oracle(high, low, close, lag=SPAN):
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
    return (last_fractal(high, 2, True) - last_fractal(low, 2, False)) / close


def _close_ends(high, low, close):
    """The reading NOT taken: `EndType.Close`, Skender's other option,
    which judges and returns the CLOSE instead of the high and the low."""
    return ((_last_fractal(close, SPAN, True)
             - _last_fractal(close, SPAN, False)) / close)


def _negative_frame():
    """A 16-bar frame whose width goes NEGATIVE, by construction.

    Bars 0..4 make an early fractal high at 10.5 and an early fractal low
    at 9.5. The price then steps to ~100 and PLATEAUS, so no bar's high
    strictly beats both its neighbours and the rally gets no fractal high;
    the dip at bar 11 still makes a fractal low at 99.0, far above the
    stale upper band. Confirmed at bar 13, the width goes to -0.8868.
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
    """A frame whose bar `SPAN` is an OUTSIDE bar -- the strict high AND
    the strict low of the whole window -- so both band legs confirm on bar
    `2 * SPAN`, the earliest bar they can."""
    idx = date_range("2020-01-01", periods=n, freq="h")
    highs, lows, closes = (np.full(n, 10.0), np.full(n, 9.5),
                           np.full(n, 9.8))
    highs[SPAN], lows[SPAN] = 11.0, 9.0
    return (Series(highs, index=idx), Series(lows, index=idx),
            Series(closes, index=idx))


# ----------------------------------------------------------------- mutants

SOURCE = Path(__file__).resolve().parents[1] / "pandas_ta" / "volatility" \
    / "sk_fcb_width.py"

#: (label, old text, new text). Edits to the SHIPPED source, read off disk.
CAUSALITY_MUTANTS = [
    # Skender's own index: the confirmed level moved back onto its centre
    # bar. `test_the_centre_read_mutant_is_skenders_own_index` asserts this
    # equals `_centre_reading`, so it is the documented alternative reading
    # and not an invented edit.
    ("centre-read", "    return ref.where(is_fractal).ffill()",
     "    return ref.where(is_fractal).shift(-span).ffill()"),
    # One extra bar of right-hand window: the weakest of the five, and the
    # reason the sweep's count is reported rather than asserted at 36.
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
    bars >= j: one scaled UP by a per-bar random factor in [1, 4], one
    scaled DOWN by its reciprocal.

    ⚠ Deliberately not the usual "multiply the tail by 1.03", and the
    reason is this column: a fractal is a COMPARISON, so a look-ahead only
    becomes visible when a decision within `SPAN` bars of the boundary
    actually flips, and a 3% nudge leaves most decisions intact. Opposite
    large factors flip the right-hand side of those decisions in both
    directions at once. One factor multiplies high, low and close, so
    `high >= close >= low` survives; bars < j are multiplied by exactly
    1.0, which is exact in binary.
    """
    h, l, c = frame
    n = c.size
    rng = np.random.default_rng(90_001 + j)
    u = rng.random(n)
    up, dn = np.ones(n), np.ones(n)
    up[j:] = 1.0 + spread * u[j:]
    dn[j:] = 1.0 / (1.0 + spread * u[j:])
    fa, fb = Series(up, index=c.index), Series(dn, index=c.index)
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


def _generator_desc():
    """`docs/gen_indicator_dictionary.py`'s own `desc`, lifted out of its
    source with `ast` and compiled alone.

    Importing that module runs its whole indicator probe, which is far too
    slow for a unit test -- and re-typing the cut here would pin a COPY of
    the rule rather than the rule."""
    import ast
    import re
    path = Path(__file__).resolve().parents[1] / "docs" \
        / "gen_indicator_dictionary.py"
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
    assert "sk_fcb_width" in ta.Category["volatility"]
    frame = _walk()
    col = sk_fcb_width(*frame)
    assert col.name == COLUMN == f"SK_FCB_WIDTH_{SPAN}"
    assert col.category == "volatility"

    h, l, c = frame
    df = DataFrame({"high": h, "low": l, "close": c})
    assert hasattr(df.ta, "sk_fcb_width")
    via_accessor = df.ta.sk_fcb_width()
    assert via_accessor.name == COLUMN
    assert bool((via_accessor.dropna() == col.dropna()).all())


def test_the_source_library_is_not_readable_here():
    """Gate A is the formula issue #107 NAMES, spelled two ways -- not a
    run or a reading of Skender's C#. Three routes to that source are
    pinned shut here, so the claim cannot rot into "checked against
    Skender" if one of them ever opens.

    `docs/pine/` is the Pine corpus `CLAUDE.md` describes as untracked apart
    from one tracked file (#8, TradingView's `ta` library); it holds Pine,
    not C#, but it is the only vendored-source directory this repo has ever
    had, and the absence of any vendored source beyond that file is half of
    why this port cites the issue's naming of `Fcb.Series.cs` instead of its
    lines.

    ⚠ A FOURTH route, web access, was unavailable in the session that
    wrote this and is NOT pinned here: a test cannot see it. Said in the
    module docstring and in `docs/SkFcbWidthMeasured.md`'s "What this port
    does NOT establish" too, so "all routes are pinned" is nowhere."""
    assert importlib.util.find_spec("stock_indicators") is None
    repo = Path(__file__).resolve().parents[1]
    # `docs/pine/` holds only the one tracked file (#8): TradingView's `ta`
    # library, which the Pine audit cites. Anything more is a vendored corpus.
    pine = repo / "docs" / "pine"
    assert not pine.exists() or {x.name for x in pine.iterdir()} <= {"RA2vGpkA-ta.pine"}
    assert not list(repo.rglob("Fcb.Series.cs"))


def test_the_signature_is_the_three_prices_and_an_offset():
    """No `span=`: 2 is a module constant, because span 2 is the only span
    anything -- the issue's title, the screen prototype, the Gate E
    figures -- has measured. A keyword here would ship spans nothing has
    looked at."""
    import inspect
    assert list(inspect.signature(sk_fcb_width).parameters) == \
        ["high", "low", "close", "offset", "kwargs"]
    assert (SPAN, MIN_BARS) == (2, 5)


def test_a_frame_shorter_than_min_bars_is_refused():
    """`MIN_BARS` = 2 * SPAN + 1 is a floor on the INPUT. The shortest
    accepted frame has exactly one bar a band could sit on -- bar
    2 * SPAN -- and whether it fires there is DATA-DEPENDENT: `walk` does
    not, the outside-bar frame does."""
    h, l, c = _walk(n=40)
    assert sk_fcb_width(h.iloc[:MIN_BARS - 1], l.iloc[:MIN_BARS - 1],
                        c.iloc[:MIN_BARS - 1]) is None
    short = sk_fcb_width(h.iloc[:MIN_BARS], l.iloc[:MIN_BARS],
                         c.iloc[:MIN_BARS])
    assert short is not None and short.size == MIN_BARS
    assert int(short.notna().sum()) == 0

    out = sk_fcb_width(*_outside_bar_frame())
    assert int(out.notna().sum()) == 1
    assert out.notna().to_numpy()[2 * SPAN]


def test_offset_and_fillna_do_what_the_kwargs_say():
    base = sk_fcb_width(*_walk())
    moved = sk_fcb_width(*_walk(), offset=2)
    m = base.notna() & base.shift(2).notna()
    assert bool((moved[m] == base.shift(2)[m]).all())
    filled = sk_fcb_width(*_walk(), fillna=0.0)
    assert int(filled.isna().sum()) == 0


# ------------------------------------------------------------------ Gate A


@pytest.mark.parametrize("name", NAMES)
def test_gate_a_matches_the_source_formula_by_explicit_loops(name):
    """Limb 1: Skender's `Fractal` double loop plus `Fcb`'s roll-forward,
    transcribed and sharing no code with the module. BIT-equal, not within
    a tolerance: a band leg is a selected price level, so the whole
    computation is one subtraction and one division.

    Measured here: 1,491 / 1,479 / 1,491 / 1,477 / 1,493 / 1,488 / 0 /
    1,411 fired bars, 10,330 pooled. The assertion is bit-equality and
    identical masks, not those counts."""
    frame = FRAMES[name]()
    col, orc = sk_fcb_width(*frame), _oracle(*frame)
    assert bool((col.isna() == orc.isna()).all())
    assert _bit_equal(col, orc)


@pytest.mark.parametrize("name", NAMES)
def test_gate_a_matches_the_screen_prototype_bit_for_bit(name):
    """Limb 2: the prototype the 2026-10-24 catalog screen measured at
    Gate E (max |rho| 0.6104 vs `natr`, n = 397,416), retyped from
    `docs/issues/screen/ind_screen_r2.py`.

    This is the limb that ties this port to those figures. It is BIT-equal
    on a clean frame, which also prices the module's guards at zero there:
    the prototype has none."""
    frame = FRAMES[name]()
    assert _bit_equal(sk_fcb_width(*frame), _prototype(*frame))


@pytest.mark.parametrize("name", FIRING)
def test_the_centre_reading_is_a_different_column(name):
    """⚠ The divergence this port owns. Skender's `Fractal` returns a level
    ON its centre bar; read there, the band would be knowable before its
    right-hand bars existed. This port reads it `SPAN` bars later.

    The two are a REAL choice, not a rounding: measured here they differ on
    46 .. 839 of the bars both fire on, at Spearman 0.4638 .. 0.9643. The
    band is asserted rather than the numbers, so a kernel that moves a
    price's last bits cannot fail it -- but "they differ somewhere" and
    "they are not the same column" are both asserted on every frame."""
    frame = FRAMES[name]()
    col, centre = sk_fcb_width(*frame), _centre_reading(*frame)
    m = col.notna() & centre.notna()
    assert int(m.sum()) > 0
    assert int((col[m] != centre[m]).sum()) > 0
    rho = _spearman(col, centre)
    assert 0.40 <= rho <= 0.99, rho


def test_the_centre_read_mutant_is_skenders_own_index():
    """The `centre-read` mutant is not an invented edit: it is exactly the
    alternative reading the test above measures, built here by editing the
    shipped source and there by an independent loop."""
    label, old, new = CAUSALITY_MUTANTS[0]
    assert label == "centre-read"
    frame = _walk()
    assert _bit_equal(_mutant(old, new)(*frame), _centre_reading(*frame))


@pytest.mark.parametrize("name", CONTINUOUS)
def test_the_strict_predicate_costs_nothing_on_continuous_prices(name):
    """⚠ Half of the FVGDEAD lesson, stated as an assertion. On continuous
    floats no two prices within `SPAN` of each other tie, so `>` and `>=`
    are the SAME column -- bit-identical. A test suite built only on
    frames like these would therefore report nothing at all about the
    choice, which is why the two rounded frames below exist."""
    frame = FRAMES[name]()
    assert _bit_equal(sk_fcb_width(*frame), _non_strict(*frame))


@pytest.mark.parametrize("name,rho_max", [("grid", 0.99), ("coarse", 0.50)])
def test_the_strict_predicate_is_the_whole_column_on_a_tick_grid(name,
                                                                rho_max):
    """⚠ The other half. A tie destroys a fractal, so on rounded prices the
    strict reading is a DIFFERENT column: measured here, 43 bars differ on
    the 0.01-tick frame (Spearman 0.9556) and 1,235 on the 2.0-tick frame
    (0.0567).

    Real BIST daily bars close exactly at an extreme on 21.17% of bars
    (`CLAUDE.md`, FVGDEAD), so this is the regime Gate E's real frames sit
    in and the continuous frames say nothing about it."""
    frame = FRAMES[name]()
    col, alt = sk_fcb_width(*frame), _non_strict(*frame)
    m = col.notna() & alt.notna()
    assert int((col[m] != alt[m]).sum()) > 0
    assert _spearman(col, alt) < rho_max


@pytest.mark.parametrize("name", FIRING)
def test_endtype_close_is_a_different_column(name):
    """Skender's `Fractal` takes an `EndType`, and `Fcb` uses `HighLow`.
    The `Close` reading is a near neighbour and not a restatement:
    measured Spearman 0.1857 .. 0.9132 across these frames, asserted below
    0.95 so that a future session cannot quietly swap the two."""
    frame = FRAMES[name]()
    rho = _spearman(sk_fcb_width(*frame), _close_ends(*frame))
    assert rho < 0.95, rho


# ------------------------------------------------------------------ Gate B


@pytest.mark.parametrize("name", NAMES)
def test_gate_b_mutant_the_module_reads_no_future_bar(name):
    """The gate: one shared past, two wholly different futures, 36 offsets,
    and not one earlier bar may move. 0 of 36 on every frame.

    `docs/measure_sk_fcb_width.py` §B runs the same detector over every
    bar but bar 0 of each frame -- 0 of 1,499 on all eight -- which is the
    strong form of this claim and too slow to keep here at 1,500 bars; the
    300-bar version of it is the test below."""
    assert _sweep(sk_fcb_width, FRAMES[name]()) == 0


def test_gate_b_mutant_the_module_reads_no_future_bar_at_any_offset():
    """The dense form of the gate, kept in the suite rather than only in
    the measure script: every bar but bar 0 of a 300-bar walk is a split
    point -- 299 of 300 -- and not one earlier bar may move. (Bar 0 is
    excluded because a split there leaves no prefix to compare.)

    ⚠ This exists because the 36-offset test above only guards the tail of
    a frame, so a look-ahead that bit earlier -- near the warm-up, say --
    would be reported by `docs/measure_sk_fcb_width.py` §B, which runs
    1,499 of 1,500 offsets on each of the eight frames, and by nothing the
    suite runs. 300 bars rather than 1,500 keeps this under a second."""
    frame = _walk(n=300)
    offsets = list(range(1, 300))
    assert _sweep(sk_fcb_width, frame, offsets) == 0


@pytest.mark.parametrize("name", MUTANT_FRAMES)
def test_gate_b_mutant_every_lookahead_edit_is_caught(name):
    """Five look-ahead mutants, read off the shipped file, edited and
    `exec`'d in memory. Each is caught on each of these six frames.

    ⚠ NOT 36 of 36, and the test does not pretend otherwise: three of the
    five look ahead through a COMPARISON, so an offset where the fractal
    decisions near the boundary agree either way sees nothing. Measured
    here, `centre-read` is caught on 33 .. 35 of 36 and
    `right-window-lead` on 4 .. 9; `flat` and `coarse` are excluded
    because they catch only 1 and 3 of the 5 -- `flat` never fires, so
    only `band-bfill` reaches it, and `coarse`'s two band legs move 15 and
    12 times in 1,500 bars. Both frames are in
    `docs/SkFcbWidthMeasured.md` §B rather than dropped."""
    frame = FRAMES[name]()
    caught = {label: _sweep(_mutant(old, new), frame)
              for label, old, new in CAUSALITY_MUTANTS}
    assert all(v > 0 for v in caught.values()), caught


def _exposed_offsets(x, lo, hi):
    """The offsets at which `right-window-lead`'s extra bar can possibly
    be seen, derived from the edit rather than guessed.

    That mutant's right window for centre `c` is `{c+2, c+3}` instead of
    `{c+1, c+2}`, and the verdict is still written to bar `c + SPAN`. So
    bar `T` reads `x[T+1]` and nothing later, and bar `j - 1` is the only
    prefix bar a split at `j` can reach. Its verdict there is
    `ref > max(left) and ref > max(x[j-1], x[j] * f)` for whichever factor
    `f` a future applies, so it can be True under SOME future only when
    `x[j-3] > max(x[j-5], x[j-4], x[j-1])`. Where that fails the verdict
    is False under EVERY future and no perturbation of bars >= j can be
    caught -- necessary by construction, and asserted below."""
    v = x.to_numpy(dtype=float)
    return [j for j in range(lo, hi)
            if v[j - 3] > max(v[j - 5], v[j - 4], v[j - 1])]


def _mutant_right_verdict(x, c):
    """`right-window-lead`'s upper-fractal verdict at centre `c`."""
    v = x.to_numpy(dtype=float)
    if c - 2 < 0 or c + 3 >= v.size:
        return None
    return bool(v[c] > max(v[c - 2], v[c - 1])
                and v[c] > max(v[c + 2], v[c + 3]))


@pytest.mark.parametrize("name", ["walk", "coarse"])
def test_gate_b_mutant_the_weakest_edit_is_swept_where_it_is_exposed(name):
    """⚠ The thinnest limb of Gate B, carried by a mechanism-aware sweep
    instead of by a 4-of-36 blind margin.

    `right-window-lead` adds ONE bar of right-hand window, so the blind
    sweep sees it on only 4 .. 9 of 36 offsets -- a margin too small to be
    evidence. The edit is therefore read (`_exposed_offsets`) and two
    things are asserted densely, over every offset from 5 on of a 300-bar
    frame -- 295 of 300, since the condition reads back to bar `j - 5`:

    1. **Necessity.** Outside the exposed set the mutant is caught 0
       times. Any other number would mean the derivation is wrong.
    2. **Sufficiency, up to three named exceptions.** Inside it, every
       miss is one of: the two futures' verdicts agree anyway (the up
       factor is only [1, 4], so it need not clear `ref`); the flipped
       level equals the level already carried; or the column has not
       started firing by bar `j - 1`. Nothing is left over.

    Measured on the 1,500-bar frames by `docs/measure_sk_fcb_width.py`
    §B2, whose pooled row it prints rather than leaves to be added up:
    1,692 of 1,722 exposed offsets caught and 0 of 8,743 unexposed ones
    over the seven firing frames (270 of 272 and 0 of 1,223 on `walk`; 24
    of 36 and 0 of 1,459 on `coarse`), and all 30 misses fall in those
    three buckets -- 17 verdict-agreement, 9 level-equality and 4
    not-yet-fired, with the 9 and 3 of the 4 contributed by `coarse`,
    where ties make equal levels common."""
    _, old, new = next(m for m in CAUSALITY_MUTANTS
                       if m[0] == "right-window-lead")
    mut = _mutant(old, new)
    frame = _walk(n=300) if name == "walk" else _coarse(n=300)
    h = frame[0]
    exposed = set(_exposed_offsets(h, 5, h.size))
    assert len(exposed) > 0

    unexposed = [j for j in range(5, h.size) if j not in exposed]
    assert sum(_caught_at(mut, frame, j) for j in unexposed) == 0

    caught = unexplained = 0
    for j in sorted(exposed):
        if _caught_at(mut, frame, j):
            caught += 1
            continue
        frame_a, frame_b = _futures(frame, j)
        if _mutant_right_verdict(frame_a[0], j - 3) == \
                _mutant_right_verdict(frame_b[0], j - 3):
            continue
        if np.isnan(mut(*frame_a).iloc[j - 1]):
            continue
        carried = _last_fractal(frame_a[0], SPAN, True).iloc[j - 1]
        if carried != h.to_numpy(dtype=float)[j - 3]:
            unexplained += 1
    assert caught > 0
    assert unexplained == 0, unexplained


@pytest.mark.parametrize("label,old,new", CAUSALITY_MUTANTS,
                         ids=[m[0] for m in CAUSALITY_MUTANTS])
def test_gate_b_mutant_each_edit_is_live_against_the_module(label, old, new):
    """The other half of the pair. A mutant caught on few offsets would
    prove nothing if the edit were inert, so each one is also shown to
    MOVE the column: measured on `walk`, 783 bars for `centre-read`, 217
    for `right-window-lead` and all 1,490 shared bars for the other
    three."""
    frame = _walk()
    base, mut = sk_fcb_width(*frame), _mutant(old, new)(*frame)
    m = base.notna() & mut.notna()
    assert int(m.sum()) > 0
    assert int((base[m] != mut[m]).sum()) > 0


# ------------------------------------------------------------------ Gate C


@pytest.mark.parametrize("name", FIRING)
def test_gate_c_the_column_fires_and_is_not_constant(name):
    """`0 < fires < n` and more than one distinct value, per frame.
    Measured here: 1,411 .. 1,493 fired of 1,500, taking 60 .. 1,493
    distinct values -- the 60 is the 2.0-tick frame, where the band moves
    27 times in all."""
    col = sk_fcb_width(*FRAMES[name]())
    fired = int(col.notna().sum())
    assert 0 < fired < col.size
    assert col.dropna().nunique() > 1


def test_the_warmup_is_data_dependent():
    """⚠ The number this column does not have. There is no constant
    warm-up: the first fire waits for a fractal high AND a fractal low to
    confirm, which is bar 7 on one frame here and bar 89 on another, and
    the NaNs are a leading prefix on all of them.

    `MIN_BARS` is a floor on the input and the dictionary's warm-up
    column shows one probe frame's figure, not a constant."""
    firsts = {}
    for name in FIRING:
        col = sk_fcb_width(*FRAMES[name]())
        idx = np.flatnonzero(col.notna().to_numpy())
        firsts[name] = int(idx[0])
        # A leading prefix, not scattered holes.
        assert bool(col.iloc[idx[0]:].notna().all())
        assert idx[0] >= 2 * SPAN
    assert len(set(firsts.values())) > 1, firsts
    assert max(firsts.values()) > 4 * min(firsts.values()), firsts


def test_a_flat_price_never_fires_and_that_is_a_reading():
    """A constant price has no STRICT local extreme, so no fractal ever
    confirms and the column is all-NaN on all 1,500 bars -- a statement
    about the instrument, not missing data.

    ⚠ Whether that is unusual for this category is a claim about 36 other
    indicators, so `docs/measure_sk_fcb_width.py` §C3 RUNS them instead:
    13 of the volatility bucket's 63 columns read all-NaN on a flat frame,
    `j_damiani` among them, and 26 read exactly 0.0. So the NaN is not a
    divergence; only the reason for it is particular to this column. An
    earlier draft of this docstring asserted the opposite without running
    anything, and round 1 of the review caught it."""
    col = sk_fcb_width(*_flat())
    assert int(col.notna().sum()) == 0
    assert col.size == N


@pytest.mark.parametrize("name", FIRING)
def test_the_width_is_not_bounded_below_by_zero(name):
    """⚠ Despite the name. `upper` and `lower` are the last fractal high
    and the last fractal low, read from DIFFERENT bars, so nothing makes
    the difference positive: measured 5 .. 91 negative readings on each of
    these frames, down to -0.1294, plus 85 readings of exactly 0.0 on the
    2.0-tick frame, where both legs land on one tick -- which takes the
    `<= 0` count, a different figure, to 5 .. 105.

    A consumer clipping at zero, or taking a log, is discarding a real
    reading. The mechanism is in `_negative_frame`."""
    v = sk_fcb_width(*FRAMES[name]()).dropna()
    assert int((v < 0).sum()) > 0


def test_the_hand_frame_shows_how_the_width_goes_negative():
    """The existence proof the random frames do not give, bar by bar: a
    plateau denies the rally its own fractal high while the dip after it
    still makes a fractal low ABOVE the stale high. -0.8868 from bar 13."""
    frame = _negative_frame()
    col = sk_fcb_width(*frame)
    h, l, _ = frame
    assert _last_fractal(h, SPAN, True).iloc[-1] == 10.5
    assert _last_fractal(l, SPAN, False).iloc[-1] == 99.0
    v = col.dropna()
    assert int((v < 0).sum()) == 3
    assert v.min() == pytest.approx((10.5 - 99.0) / 99.8, rel=1e-12)


@pytest.mark.parametrize("name", FIRING)
def test_the_band_is_a_step_function_over_a_moving_divisor(name):
    """The band changes only when a fractal confirms -- measured 172 .. 230
    steps per leg over 1,500 bars on the six frames other than `flat` and
    `coarse`, and 15 and 12 on the 2.0-tick one, where one leg is held for
    up to 428 bars -- so between confirmations the column moves only
    because `close` does.

    Asserted as the mechanism itself, not a proxy for it: far fewer band
    steps than fired bars, AND at least one bar where NEITHER leg moved
    and the column moved anyway -- which can only be the close. Measured
    here, 271 .. 1,131 such bars per frame: 1,071 of 1,071 band-held bars
    on `walk` and all of them on the other four continuous frames, 1,050
    of 1,054 on the 0.01-tick frame, and only 271 of 1,387 on the 2.0-tick
    one, where the rounded close repeats as well."""
    h, l, c = FRAMES[name]()
    up = _last_fractal(h.where(np.isfinite(h)), SPAN, True)
    lo = _last_fractal(l.where(np.isfinite(l)), SPAN, False)
    col = sk_fcb_width(h, l, c)
    fired = int(col.notna().sum())
    steps = _steps(up) + _steps(lo)
    assert 0 < steps < fired / 2

    u, d, k = up.to_numpy(), lo.to_numpy(), col.to_numpy()
    held = ((u[1:] == u[:-1]) & (d[1:] == d[:-1])
            & ~np.isnan(k[1:]) & ~np.isnan(k[:-1]))
    assert int(held.sum()) > 0
    assert int((held & (k[1:] != k[:-1])).sum()) > 0


def test_a_tick_grid_starves_the_band():
    """Rounding costs fractals, monotonically in the tick and on BOTH
    legs: measured 216 / 212 / 71 / 15 upper fractals and 205 / 199 / 82 /
    12 lower ones at no rounding, 0.01, 0.5 and 2.0 on one walk.

    Asserted as the ORDERING per leg plus "the coarse tick loses most of
    them", which is the shape that would survive a different seed."""
    for leg, upper in ((0, True), (1, False)):
        counts = []
        for tick in (None, 0.01, 0.5, 2.0):
            frame = _walk() if tick is None else _coarse(tick=tick)
            counts.append(_steps(_last_fractal(frame[leg], SPAN, upper)))
        assert counts == sorted(counts, reverse=True), (upper, counts)
        assert counts[-1] < counts[0] / 5, (upper, counts)


# ------------------------------------------------------------------ Gate D


@pytest.mark.parametrize("name", NAMES)
@pytest.mark.parametrize("factor", [8, 64])
def test_gate_d_scale_is_bit_identical_under_exact_factors(name, factor):
    """x8 and x64 are exact in binary, and the band legs are SELECTED by
    comparisons, which no positive rescale changes. `(a*f - b*f) / (c*f)`
    then has the same real quotient as `(a - b) / c` and rounds once, so
    bit-identity is structural and is asserted as such."""
    frame = FRAMES[name]()
    base = sk_fcb_width(*frame)
    assert _bit_equal(base, sk_fcb_width(*_scaled(frame, factor)))


@pytest.mark.parametrize("name", FIRING)
@pytest.mark.parametrize("factor", [10.0, 3.7, 0.1, 1.0000001])
def test_gate_d_scale_survives_an_inexact_factor(name, factor):
    """Inexact factors: NaN masks must match exactly and the values within
    1e-9 relative (measured max 1.229e-12 over the 28 pairs).

    ⚠ The risk peculiar to this column is not that last bit. A rescale
    that collapsed two distinct neighbouring prices onto one double would
    destroy a strict inequality and move a band leg by a WHOLE price
    level, which is what the second assertion looks for: 0 bars where the
    selected level moved by more than 1e-9 relative to the rescale. 0 is a
    measurement over these 28 pairs, not a proof that it cannot happen."""
    frame = FRAMES[name]()
    base = sk_fcb_width(*frame)
    other = sk_fcb_width(*_scaled(frame, factor))
    assert bool((base.isna() == other.isna()).all())
    assert _rel(base, other) <= 1e-9, _rel(base, other)

    h, l, _ = frame
    for leg, upper in ((h, True), (l, False)):
        a = _last_fractal(leg, SPAN, upper).to_numpy()
        b = (_last_fractal(leg * factor, SPAN, upper) / factor).to_numpy()
        flips = int((~np.isclose(a, b, rtol=1e-9, atol=0.0,
                                 equal_nan=True)).sum())
        assert flips == 0, flips


@pytest.mark.parametrize("level", [1e-6, 1e+6, 1e+100])
def test_gate_d_scale_at_extreme_price_levels(level):
    """The same x8/x64 run repeated three orders of magnitude apart and
    then 94 more, so the invariance is not an artefact of level 100."""
    frame = _walk(level=level)
    base = sk_fcb_width(*frame)
    assert int(base.notna().sum()) > 0
    assert _bit_equal(base, sk_fcb_width(*_scaled(frame, 8)))
    assert _bit_equal(base, sk_fcb_width(*_scaled(frame, 64)))


# ------------------------------------------------------- guards and edges


@pytest.mark.parametrize("value", [np.nan, 0.0, -1.0, np.inf, -np.inf,
                                   1e-310])
def test_a_bad_close_empties_its_own_bar_and_no_other(value):
    """The divisor guard, priced. Each of these six closes empties exactly
    its own bar and moves 0 others.

    What it buys is measured rather than argued: unguarded, a zero or
    subnormal close reads `inf`, a NEGATIVE close reads a
    plausible-looking -1.503724, and an infinite close reads a
    plausible-looking 0.000000 -- a feature value no consumer would
    question."""
    h, l, c = _walk()
    base = sk_fcb_width(h, l, c)
    c2 = c.copy()
    c2.iloc[PLANT] = value
    out = sk_fcb_width(h, l, c2)

    emptied = np.flatnonzero((base.notna() & out.isna()).to_numpy())
    assert emptied.tolist() == [PLANT]
    m = base.notna() & out.notna()
    assert int((base[m] != out[m]).sum()) == 0

    raw = _mutant(*CLOSE_GUARD_OFF)(h, l, c2).iloc[PLANT]
    assert not (np.isfinite(raw) and raw == base.iloc[PLANT])


@pytest.mark.parametrize("leg", ["high", "low"])
@pytest.mark.parametrize("value", [np.nan, np.inf, -np.inf])
def test_a_bad_high_or_low_makes_no_fractal_and_moves_no_earlier_bar(leg,
                                                                    value):
    """⚠ A bad high or low is absorbed rather than emptied: a comparison
    against a NaN is False, so the bar makes no fractal and no reading
    goes missing. With the guard on, an infinity behaves exactly like a
    NaN -- asserted bit-equal below.

    The causal half is the assertion that matters: NO bar before the plant
    moves. ⚠ The disclosure is that the forward reach is NOT bounded by a
    window the way a rolling mean's is -- `ffill` carries the older level
    until the next fractal replaces it, measured 10 bars for a high and 4
    for a low at bar 700 of `walk`, and a frame with sparser fractals
    would carry it further."""
    h, l, c = _walk()
    base = sk_fcb_width(h, l, c)
    parts = {"high": h.copy(), "low": l.copy()}
    parts[leg].iloc[PLANT] = value
    out = sk_fcb_width(parts["high"], parts["low"], c)

    assert bool((base.isna() == out.isna()).all())
    assert int((~np.isfinite(out.dropna().to_numpy())).sum()) == 0

    m = base.notna() & out.notna()
    idx = np.flatnonzero(m.to_numpy())[(base[m] != out[m]).to_numpy()]
    assert idx.size > 0
    assert int((idx < PLANT).sum()) == 0

    nan_parts = {"high": h.copy(), "low": l.copy()}
    nan_parts[leg].iloc[PLANT] = np.nan
    assert _bit_equal(out, sk_fcb_width(nan_parts["high"],
                                        nan_parts["low"], c))


@pytest.mark.parametrize("leg,value,infinite", [("high", np.inf, True),
                                                ("low", -np.inf, True),
                                                ("high", -np.inf, False),
                                                ("low", np.inf, False)])
def test_the_high_low_guard_is_what_keeps_an_infinity_out(leg, value,
                                                          infinite):
    """What that guard buys, measured: `+inf > x` is True, so an unguarded
    `+inf` high BECOMES a fractal and the band carries `inf` until the
    next fractal replaces it -- 9 infinite readings for this plant, and 5
    for a `-inf` low.

    ⚠ And the two plants it buys nothing for, stated rather than implied:
    a `-inf` HIGH and a `+inf` LOW are never extremes, so they cost
    nothing even unguarded. The guard is for infinities only; a NaN
    already declined to make a fractal."""
    h, l, c = _walk()
    parts = {"high": h.copy(), "low": l.copy()}
    parts[leg].iloc[PLANT] = value
    unguarded = _mutant(*HL_GUARD_OFF)(parts["high"], parts["low"], c)
    bad = int((~np.isfinite(unguarded.dropna().to_numpy())).sum())
    assert (bad > 0) is infinite, bad

    guarded = sk_fcb_width(parts["high"], parts["low"], c)
    assert int((~np.isfinite(guarded.dropna().to_numpy())).sum()) == 0


@pytest.mark.parametrize("value", [np.nan, 0.0, -5.0, 100.0])
def test_a_degenerate_frame_raises_nothing(value):
    """All-NaN, all-zero, all-negative and all-one-price frames: no float
    error is reachable under `errstate(all="raise")`, and all four fire
    nowhere.

    The last of them is the one that matters -- a repeated price is a
    halted instrument, not a pathological input -- and it fires nowhere
    for a structural reason rather than a guard: no strict local
    extreme."""
    idx = date_range("2020-01-01", periods=60, freq="h")
    s = Series(np.full(60, value), index=idx)
    with np.errstate(all="raise"):
        out = sk_fcb_width(s.copy(), s.copy(), s.copy())
    assert int(out.notna().sum()) == 0


def test_the_cross_scale_overflow_is_disclosed_and_unguarded():
    """The one non-finite reading this module can produce, pinned so the
    disclosure cannot rot into silence: a frame whose high and low sit at
    1e+300 while the close sits at 1e-300 overflows the division and reads
    `inf` on every bar it fires.

    That is bad data rather than a price -- the same walk at ONE scale
    fires finite at 1e-6, 1e+6 and 1e+100, which is
    `test_gate_d_scale_at_extreme_price_levels`."""
    h, l, _ = _walk(n=60, level=1e+300)
    tiny = Series(np.full(60, 1e-300), index=h.index)
    v = sk_fcb_width(h, l, tiny).dropna().to_numpy()
    assert v.size > 0
    assert int(np.isinf(v).sum()) == v.size


# ------------------------------------------------------- docs and the ledger


def test_the_docstrings_first_paragraph_survives_the_dictionary_cut():
    """`docs/gen_indicator_dictionary.py` shows `d[:150].rsplit(' ', 1)[0]`
    of the docstring's first paragraph, which drops the trailing word
    WHOLE. The cut only runs when the paragraph EXCEEDS 150 characters, so
    the budget is 150 and the penalty for passing it is a whole word.
    The paragraph is 121 characters, i.e. 29 to spare -- measured by
    `python docs/measure_sk_fcb_width.py W`, which calls the generator's
    own `desc()` and grows the sentence until it loses a word.

    This test runs the generator's OWN `desc`, lifted out of its source by
    `ast`, so the assertion fails if the generator's cut changes and not
    only if this sentence grows."""
    body = []
    for line in sk_fcb_width.__doc__.splitlines()[1:]:
        if line.strip():
            body.append(line.strip())
        elif body:
            break
    paragraph = " ".join(body)
    assert len(paragraph) == 121, len(paragraph)

    desc = _generator_desc()
    assert desc({"desc": paragraph}) == paragraph
    # One character past the 150 budget, i.e. one past §W's measured slack
    # of 29, and the generator takes a whole word.
    longer = paragraph[:-1] + "x" * 30 + paragraph[-1:]
    assert len(longer) == 151
    assert desc({"desc": longer}) != longer


def _sk_fcb_width_ledger_row():
    ledger = Path(__file__).resolve().parents[1] / "docs" / "gate_e_ledger.csv"
    rows = list(csv.DictReader(ledger.open(encoding="utf-8")))
    assert rows, "the ledger should not be empty"
    rows = [r for r in rows if r["indicator"] == "sk_fcb_width"]
    assert len(rows) == 1, rows
    return rows[0]


def test_the_gate_e_row_is_this_ports_own_measurement():
    """The ledger row for `sk_fcb_width` must come from the run on THIS
    module, `is107-sk_fcb_width-8f25baf3` (measured 2026-11-15), and NOT
    from the catalog screen of 2026-10-24, which measured the PROTOTYPE.
    The two agree to every digit issue #107 printed -- pooled 0.6104
    against `compute_all`'s `natr` at n = 397,416, top-five per-frame max
    median 0.5846 over 89 frames, runners-up `Stop_2ATR_pct` 0.6104 and
    `Swing_Range_pct` 0.5530 -- which is exactly why the row's identity
    needs pinning: `tests/test_gate_e_ledger.py` re-derives a row's
    `module_sha1` and output fingerprint from the tree and checks its
    verdict arithmetic, but it cannot see WHOSE measurement a row came
    from. The §A2 limb of item 1 asserts this module bit-equal to the
    retyped prototype on all eight frames, so the agreement is expected.

    The verdict is **SHIP**, the `< 0.76` band of `r3-perframe-0.90`: the
    column stays and the row needs no waiver (only STRUCK needs one).
    Both limbs are asserted as BOUNDS and not as digits -- pooled below
    0.76 and the top-five per-frame max median below 0.76 -- so a
    re-recorded row that moved within the band still has to stay in it.

    This test replaced `test_the_gate_e_row_is_owed`, which asserted the
    row was ABSENT and so failed the moment the receipt session recorded
    it. `docs/SkFcbWidthMeasured.md` §E .. §E3 carries the result in full,
    including the part the band does not read: no single one of the 89
    frames reaches even 0.80 on ANY of the top five comparators."""
    row = _sk_fcb_width_ledger_row()
    assert row["module"] == "pandas_ta.volatility.sk_fcb_width"
    assert row["column"] == COLUMN
    assert row["run"] == "is107-sk_fcb_width-8f25baf3"
    assert row["verdict"] == "SHIP"
    assert row["verdict_schema"] == "r3-perframe-0.90"
    assert row["waiver"] == ""
    assert row["against"] == "natr"
    assert row["against_set"] == "compute_all"
    assert row["perframe_max_against"] == "natr"
    assert (int(row["n_frames"]), int(row["n_comparators"])) == (89, 687)
    # SHIP is pooled |rho| < 0.76 with no top-5 comparator's per-frame
    # median >= 0.90; this row clears the stricter of the two lines on
    # both limbs.
    assert float(row["max_abs_rho"]) < 0.76
    assert float(row["perframe_max_median_abs_rho"]) < 0.76


def test_the_gate_e_run_closes_gate_c_on_real_data():
    """Gate C's real-data limb, read off the SAME ledger row rather than
    retyped: the column fires on 397,609 of the run's 398,849 pooled bars
    over 89 real BIST frames, so `0 < fires < n` holds there and not only
    on the synthetic frames of item 5.

    The 1,240 empty bars are NOT a constant warm-up, and that is the
    real-data form of item 5's finding: 1,240 is not a whole number of
    bars per frame (13.93 on average), so no per-frame constant can
    produce it, while the floor `2 * SPAN` per frame is 356 of the 1,240.
    Asserted as those two relations -- not a whole multiple of
    `n_frames`, and at least `2 * SPAN * n_frames` -- rather than as
    1,240. ⚠ 13.93 is EMPTY BARS per frame and not a mean first-fire bar:
    the two coincide only if the real NaNs are a leading prefix, which
    this row cannot show, because a bad close empties its own bar wherever
    it sits (`test_a_bad_close_empties_its_own_bar_and_no_other`).

    `non_zero` is 108 SHORT of `non_nan`, i.e. 108 fired real bars read
    exactly 0.0. Item 5's exact zeros were measured on a 2.0-tick
    synthetic frame, and this is the same reading on real prices, where
    21.17% of BIST daily bars close exactly at an extreme: both band legs
    land on one tick. Asserted as `0 < non_zero < non_nan`, the
    structural fact, with 108 the figure measured by that run.

    ⚠ The row carries no count of NEGATIVE readings -- it reports NaN and
    zero only -- so item 5's 5 .. 91 negatives per frame stay a SYNTHETIC
    figure and nothing here pins them on real data."""
    row = _sk_fcb_width_ledger_row()
    pooled = int(row["pooled_bars"])
    fires = int(row["non_nan"])
    frames = int(row["n_frames"])
    empty = pooled - fires
    assert 0 < fires < pooled
    assert empty % frames != 0, empty
    assert empty >= 2 * SPAN * frames
    # 108 bars read exactly 0.0 in this run; pinned as the relation.
    assert 0 < int(row["non_zero"]) < fires
