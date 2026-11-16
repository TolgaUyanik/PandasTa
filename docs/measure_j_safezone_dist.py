# -*- coding: utf-8 -*-
"""J-SAFEZONE-DIST (PandasTa issue #121): every number in
`docs/JSafezoneDistMeasured.md`.

    python docs/measure_j_safezone_dist.py            # every section, in order
    python docs/measure_j_safezone_dist.py A1 D       # named sections only

One section per gate limb, printed and never derived: the repo's dominant
defect is "a claim written before it was measured", so this file is the only
place a figure in the receipt, the module docstring or
`tests/test_j_safezone_dist.py` may come from.

    pen[T]  = max(low[T-1] - low[T], 0)
    avg[T]  = sum(pen, 22) / count(pen > 0, 22)
    raw[T]  = low[T-1] - 2.5 * avg[T-1]
    stop[T] = max(raw[T-2], raw[T-1], raw[T])
    J_SAFEZONE_DIST[T] = (close[T] - stop[T]) / close[T]

⚠ The millisecond figures of §Z are this machine's and this run's. Nothing
else here is meant to depend on the machine, and
`docs/measure_j_safezone_dist_cpu.py` re-runs the sections under numpy's
reduced CPU dispatch to show which figures move.
"""
import importlib.util
import sys
import timeit
import tracemalloc
from pathlib import Path

import numpy as np
import pandas as pd
from pandas import Series, date_range

from pandas_ta.overlap.linreg_channel import linreg_channel
from pandas_ta.trend.adx import adx
from pandas_ta.trend.chop import chop
from pandas_ta.trend.j_safezone_dist import (LOOKBACK, MIN_BARS, MULT, PERIOD,
                                             j_safezone_dist)
from pandas_ta.trend.vhf import vhf
from pandas_ta.volatility.massi import massi
from pandas_ta.volatility.natr import natr
from pandas_ta.volatility.rvi import rvi

N = 1500
LEVEL = 100.0
#: The first bar that can fire, and so the warm-up on a frame with a
#: penetration in every window. `MIN_BARS` is that index plus one.
WARMUP = MIN_BARS - 1
FIRED = N - WARMUP
#: The blind causality sweep's perturbation points.
OFFSETS = list(range(N - 36, N))


# ------------------------------------------------------------------ frames
# The same builders and seeds as `tests/test_j_safezone_dist.py`, so a number
# in this file and a number in that one are the same measurement. `walk` ..
# `flat` are `docs/measure_j_damiani.py`'s, kept identical on purpose: two
# ports measured on the same frames can be compared. `rising` is new here,
# because this column has a NaN reading that `j_damiani` does not -- a window
# with no down-penetration at all -- and a one-way market is how a real frame
# reaches it without being flat.


def _ohlc(close, seed):
    """An OHLC frame around a close path, with `high >= close >= low`."""
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


def _rising(n=N, level=LEVEL, step=0.001):
    """Strictly rising lows: no down-penetration anywhere, ever.

    The degenerate frame this column has and `j_damiani` does not. It is
    not flat -- every bar moves, and every other indicator reads it -- so
    it separates "no movement" from "no DOWNSIDE movement".
    """
    idx = date_range("2020-01-01", periods=n, freq="h")
    lo = Series(level * (1.0 + step * np.arange(n)), index=idx)
    return lo * 1.004, lo, lo * 1.002


FRAMES = {
    "walk": _walk, "trend": _trend, "range-bound": _range_bound,
    "grid": _grid, "heavy-tailed": _heavy, "jump": _jump, "flat": _flat,
    "rising": _rising,
}
#: The frames with a down-penetration in every 22-bar window, i.e. the ones
#: that fire on `FIRED` bars. `flat` and `rising` fire nowhere.
VARYING = ["walk", "trend", "range-bound", "grid", "heavy-tailed", "jump"]


def _frame(name):
    _, low, close = FRAMES[name]()
    return low, close


def _col(name):
    return j_safezone_dist(*_frame(name))


# ----------------------------------------------------------------- oracles


def _oracle(low, close):
    """The issue's formula, bar by bar, sharing no code with the module.

    Its own penetration loop, its own window sums over plain Python
    slices, its own 3-bar max. `sum()` over a slice and pandas'
    `rolling.sum` are not the same arithmetic, so this is a 1e-12 check
    rather than a bit-equality one -- §A1 reports what it actually costs.
    """
    lo = low.to_numpy(dtype=float)
    cl = close.to_numpy(dtype=float)
    n = lo.size
    pen = np.full(n, np.nan)
    for i in range(1, n):
        pen[i] = max(lo[i - 1] - lo[i], 0.0)
    avg = np.full(n, np.nan)
    for i in range(PERIOD - 1, n):
        window = pen[i - PERIOD + 1:i + 1]
        if np.isnan(window).any():
            continue
        hits = [p for p in window if p > 0.0]
        if hits:
            avg[i] = sum(window) / len(hits)
    raw = np.full(n, np.nan)
    for i in range(1, n):
        raw[i] = lo[i - 1] - MULT * avg[i - 1]
    stop = np.full(n, np.nan)
    for i in range(LOOKBACK - 1, n):
        window = raw[i - LOOKBACK + 1:i + 1]
        if not np.isnan(window).any():
            stop[i] = max(window)
    return Series((cl - stop) / cl, index=close.index)


def _prototype(low, close):
    """`docs/issues/screen/ind_screen_r2.py`, candidate `j_safezone_dist`,
    retyped (that file is gitignored, so it is on the owner's machine
    only). `sdiv` is inlined; everything else is the prototype's own.

        pen = (l.shift() - l).clip(lower=0)
        avg = sdiv(pen.rolling(22).sum(), (pen > 0).astype(float).rolling(22).sum())
        stop = (l.shift() - 2.5 * avg.shift()).rolling(3).max()
        return (c - stop) / c
    """
    pen = (low.shift() - low).clip(lower=0)
    avg = (pen.rolling(PERIOD).sum()
           / (pen > 0).astype(float).rolling(PERIOD).sum()
           ).replace([np.inf, -np.inf], np.nan)
    stop = (low.shift() - MULT * avg.shift()).rolling(LOOKBACK).max()
    return (close - stop) / close


def _mean_over_period(low, close):
    """The OTHER reading of "mean(down-penetrations, 22)": divide by 22
    rather than by the number of penetrations."""
    pen = (low.shift(1) - low).clip(lower=0.0)
    avg = pen.rolling(PERIOD, min_periods=PERIOD).mean()
    stop = (low.shift(1) - MULT * avg.shift(1)
            ).rolling(LOOKBACK, min_periods=LOOKBACK).max()
    return (close - stop) / close


# ----------------------------------------------------------------- helpers


def _bit_equal(a, b):
    """Same NaN mask, and every shared bar the same double."""
    if not bool((a.isna() == b.isna()).all()):
        return False
    m = a.notna() & b.notna()
    return bool((a[m].to_numpy() == b[m].to_numpy()).all())


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
    return float((a[m] - b[m]).abs().max()) if int(m.sum()) else float("nan")


def _spearman(a, b):
    m = a.notna() & b.notna()
    if int(m.sum()) < 3 or a[m].nunique() < 2 or b[m].nunique() < 2:
        return float("nan")
    return float(a[m].corr(b[m], method="spearman"))


def _scaled(frame, factor):
    low, close = frame
    return low * factor, close * factor


# ----------------------------------------------------------------- mutants

SOURCE = Path(__file__).resolve().parents[1] / "pandas_ta" / "trend" \
    / "j_safezone_dist.py"

#: (label, old text, new text). Edits to the SHIPPED source, read off disk.
#: Every one makes the OUTPUT read a bar later than T, so the blind suffix
#: sweep must catch every one.
#:
#: ⚠ THE SIZES ARE MEASURED, NOT CHOSEN FOR TIDINESS. The stop carries TWO
#: `shift(1)`s between a penetration and the output, so a `shift(-1)` early
#: in the chain is absorbed by them: it lands on bar T's OWN low rather
#: than a future one -- a defect, but not a look-ahead, and the sweep is
#: right not to catch it. `BLIND_SPOT_MUTANTS` holds those three, measured,
#: next to the two that drop a `shift(1)` outright.
CAUSALITY_MUTANTS = [
    ("pen-lead-2",
     "return (low.shift(1) - low).clip(lower=0.0)",
     "return (low.shift(-2) - low).clip(lower=0.0)"),
    ("avg-lead-2",
     "    total = pen.rolling(PERIOD, min_periods=PERIOD).sum()",
     "    total = pen.shift(-2).rolling(PERIOD, min_periods=PERIOD).sum()"),
    ("raw-lead",
     "    raw = lo.shift(1) - MULT * avg.shift(1)",
     "    raw = lo.shift(-1) - MULT * avg.shift(1)"),
    ("stop-lead-2",
     "    stop = raw.rolling(LOOKBACK, min_periods=LOOKBACK).max()",
     "    stop = raw.shift(-2).rolling(LOOKBACK, min_periods=LOOKBACK).max()"),
    ("close-lead",
     "    dist = (px - stop) / px",
     "    dist = (px.shift(-1) - stop) / px.shift(-1)"),
    ("output-early",
     "    dist = dist.where(np.isfinite(dist))",
     "    dist = dist.where(np.isfinite(dist)).shift(-1)"),
]

#: NOT causality mutants, and printing them is the point: each makes the
#: output read bar T's OWN low, which is wrong -- the stop a trader could
#: have had in the market is yesterday's -- but is not a read of any LATER
#: bar, so the suffix sweep is BLIND to all five. Gate A's oracle is not.
#: §B2 measures both halves of that, so Gate B's result is not read as more
#: than it is.
BLIND_SPOT_MUTANTS = [
    ("pen-lead-1", "return (low.shift(1) - low).clip(lower=0.0)",
     "return (low.shift(-1) - low).clip(lower=0.0)"),
    ("avg-lead-1", "    total = pen.rolling(PERIOD, min_periods=PERIOD).sum()",
     "    total = pen.shift(-1).rolling(PERIOD, min_periods=PERIOD).sum()"),
    ("stop-lead-1",
     "    stop = raw.rolling(LOOKBACK, min_periods=LOOKBACK).max()",
     "    stop = raw.shift(-1).rolling(LOOKBACK, min_periods=LOOKBACK).max()"),
    ("today-low", "    raw = lo.shift(1) - MULT * avg.shift(1)",
     "    raw = lo - MULT * avg.shift(1)"),
    ("today-avg", "    raw = lo.shift(1) - MULT * avg.shift(1)",
     "    raw = lo.shift(1) - MULT * avg"),
]

#: The divisor guard inside `_mean_penetration`, removed, to price it.
HITS_GUARD_OFF = ("return total / hits.where(hits > 0.0)",
                  "return total / hits")
#: The final finite guard, removed, to price it.
FINITE_GUARD_OFF = ("    dist = dist.where(np.isfinite(dist))", "    pass")


def _ROLLING_SUM_PROBES():
    """pandas' compensated `rolling.sum`, probed for what it does to an
    overflow -- the behaviour §G3's routes 1 and 2 rely on.

    81 bars with the bad value in the MIDDLE, so the contamination is
    separable from `min_periods`' own `PERIOD - 1` warm-up. A 31-bar
    probe with the bad value at index 0 cannot do that, and an earlier
    draft read its 22 NaNs as 22 contaminated windows when 21 of them
    were the warm-up. Shared with `tests/test_j_safezone_dist.py`.
    """
    big = np.finfo(float).max
    return [
        ("one +inf at bar 40", [1.0] * 40 + [np.inf] + [1.0] * 40),
        ("two DBL_MAX at bars 40, 41", [1.0] * 40 + [big] * 2 + [1.0] * 39),
    ]


def _largest_intermediate(low, close):
    """The biggest magnitude anywhere in the chain, for a headroom check.

    Printed rather than reasoned about: §D3's margin against DBL_MAX used
    to be a typed "four orders" and was wrong by 202 of them.
    """
    lo = low.where(np.isfinite(low))
    pen = (lo.shift(1) - lo).clip(lower=0.0)
    total = pen.rolling(PERIOD, min_periods=PERIOD).sum()
    hits = (pen > 0.0).astype(float).rolling(PERIOD, min_periods=PERIOD).sum()
    avg = total / hits.where(hits > 0.0)
    stop = (lo.shift(1) - MULT * avg.shift(1)
            ).rolling(LOOKBACK, min_periods=LOOKBACK).max()
    parts = [lo, close, pen, total, avg, stop]
    return max(float(p.abs().max()) for p in parts if int(p.notna().sum()))


#: The three ways a FINITE pair of inputs can still make an infinity, in
#: the order they occur in the chain -- subtraction, rolling sum, division.
#: The labels carry the numbers so the table, the prose and the tests
#: cannot drift onto three different numberings, which they did once.
#: Shared in shape with `tests/test_j_safezone_dist.py::_overflow_frame`.
#: ⚠ An earlier draft of the module docstring said the final division was
#: the only route; it is not, and these are the frames that say so.
def _OVERFLOW_ROUTES():
    idx = date_range("2020-01-01", periods=120, freq="h")
    rng = np.random.default_rng(5)
    big = np.finfo(float).max
    routes = [
        # 1. the SUBTRACTION itself, which needs a NEGATIVE low -- legal
        #    here, because `low` is guarded for finiteness only.
        ("1. subtraction (+max to -max)",
         Series(np.where(np.arange(120) % 2 == 0, big, -big), index=idx),
         Series(np.full(120, 100.0), index=idx)),
        # 2. the ROLLING SUM: eleven penetrations near DBL_MAX in one
        #    22-bar window add to more than DBL_MAX.
        ("2. rolling sum (alternating max)",
         Series(np.where(np.arange(120) % 2 == 0, big, 1.0), index=idx),
         Series(np.full(120, 100.0), index=idx)),
        # 3. the DIVISION: a huge stop over a tiny close.
        ("3. division (1e300 / 1e-300)",
         Series(1e300 * (1.0 + 0.01 * rng.random(120)), index=idx),
         Series(np.full(120, 1e-300), index=idx)),
    ]
    return routes


def _mutant(old, new):
    src = SOURCE.read_text(encoding="utf-8")
    assert src.count(old) == 1, f"{old!r} occurs {src.count(old)} times"
    ns = {}
    exec(compile(src.replace(old, new), "<mutant>", "exec"), ns)
    return ns["j_safezone_dist"]


def _caught_at(fn, frame, j, factor=1.03):
    """Did perturbing every bar >= j move any bar < j?

    ⚠ `factor` on low AND close is not a global rescale -- the column is
    invariant under one of those, which is Gate D -- it is a rescale of a
    SUFFIX, which moves the penetration at bar j.
    """
    low, close = frame
    f = Series(np.where(np.arange(close.size) >= j, factor, 1.0),
               index=close.index)
    a = fn(low, close).iloc[:j]
    b = fn(low * f, close * f).iloc[:j]
    if not bool((a.isna() == b.isna()).all()):
        return True
    m = a.notna() & b.notna()
    return not bool((a[m].to_numpy() == b[m].to_numpy()).all())


def _sweep(fn, frame, offsets=None):
    return sum(_caught_at(fn, frame, j) for j in (offsets or OFFSETS))


# ---------------------------------------------------------------- sections


def section_A1():
    print("\n§A1 Gate A -- the issue's formula, spelled independently\n")
    print(f"  {'frame':<14} {'fired':>6} {'oracle':>7} {'bit-eq':>7} "
          f"{'max |rel|':>11} {'max |abs|':>11}")
    for name in VARYING:
        low, close = _frame(name)
        got, want = j_safezone_dist(low, close), _oracle(low, close)
        print(f"  {name:<14} {int(got.notna().sum()):>6} "
              f"{int(want.notna().sum()):>7} {str(_bit_equal(got, want)):>7} "
              f"{_rel(got, want):>11.3e} {_abs(got, want):>11.3e}")
    print("\n  and on the two degenerate frames, where both are all-NaN:")
    for name in ("flat", "rising"):
        low, close = _frame(name)
        got, want = j_safezone_dist(low, close), _oracle(low, close)
        print(f"  {name:<14} {int(got.notna().sum()):>6} "
              f"{int(want.notna().sum()):>7} {str(_bit_equal(got, want)):>7}")


def section_A2():
    print("\n§A2 Gate A -- the screen prototype, bit for bit\n")
    print(f"  {'frame':<14} {'fired':>6} {'proto':>6} {'bit-equal':>10}")
    for name in FRAMES:
        low, close = _frame(name)
        got, want = j_safezone_dist(low, close), _prototype(low, close)
        print(f"  {name:<14} {int(got.notna().sum()):>6} "
              f"{int(want.notna().sum()):>6} {str(_bit_equal(got, want)):>10}")
    print("\n  The module adds two guards the prototype has not (the input")
    print("  sanitation and the final finite mask). On a clean frame both")
    print("  are no-ops, which is what this table says; §G measures what")
    print("  they buy on a frame that is not clean.")


def section_A3():
    print("\n§A3 the warm-up, bar by bar\n")
    low, close = _frame("walk")
    pen = (low.shift(1) - low).clip(lower=0.0)
    total = pen.rolling(PERIOD, min_periods=PERIOD).sum()
    hits = (pen > 0.0).astype(float).rolling(PERIOD, min_periods=PERIOD).sum()
    avg = total / hits.where(hits > 0.0)
    raw = low.shift(1) - MULT * avg.shift(1)
    stop = raw.rolling(LOOKBACK, min_periods=LOOKBACK).max()
    col = j_safezone_dist(low, close)
    for label, s in (("pen", pen), ("avg", avg), ("raw", raw),
                     ("stop", stop), ("column", col)):
        first = int(s.notna().to_numpy().argmax())
        print(f"  {label:<8} first defined at index {first:>3}")
    print(f"\n  MIN_BARS = {MIN_BARS} = PERIOD {PERIOD} + LOOKBACK "
          f"{LOOKBACK} + 1, and the first fired index is {MIN_BARS - 1}.")
    short = j_safezone_dist(low.iloc[:MIN_BARS - 1], close.iloc[:MIN_BARS - 1])
    exact = j_safezone_dist(low.iloc[:MIN_BARS], close.iloc[:MIN_BARS])
    print(f"  on {MIN_BARS - 1} bars: {short!r}")
    print(f"  on {MIN_BARS} bars: fires on "
          f"{0 if exact is None else int(exact.notna().sum())} bar(s)")


def section_A4():
    print("\n§A4 WHICH MEAN -- sum/count, not sum/22\n")
    print(f"  {'frame':<14} {'shipped':>8} {'per-22':>8} {'shared':>7} "
          f"{'rho':>8} {'max |abs|':>11} {'ship>alt':>9}")
    for name in VARYING + ["rising"]:
        low, close = _frame(name)
        a, b = j_safezone_dist(low, close), _mean_over_period(low, close)
        m = a.notna() & b.notna()
        bigger = int((a[m] > b[m]).sum())
        print(f"  {name:<14} {int(a.notna().sum()):>8} "
              f"{int(b.notna().sum()):>8} {int(m.sum()):>7} "
              f"{_spearman(a, b):>8.4f} {_abs(a, b):>11.3e} {bigger:>9}")
    print("\n  Averaging over 22 instead of over the hits is a SMALLER mean")
    print("  on any window with a quiet bar, so a HIGHER stop and a SMALLER")
    print("  distance -- `ship>alt` counts the shared bars where the shipped")
    print("  column is the larger of the two. The per-22 reading also never")
    print("  goes NaN, which is why `rising` is in this table.")


def section_B():
    print("\n§B Gate B -- causality\n")
    print("  the shipped module, against the blind suffix sweep:")
    for name in VARYING:
        caught = _sweep(j_safezone_dist, _frame(name))
        print(f"    {name:<14} caught {caught:>2} of {len(OFFSETS)}")
    print("\n  six look-ahead mutants, read off the shipped source:")
    print(f"  {'mutant':<14} {'frame':<14} {'live':>6} {'caught':>8}")
    worst = len(OFFSETS)
    for label, old, new in CAUSALITY_MUTANTS:
        fn = _mutant(old, new)
        for name in VARYING:
            frame = _frame(name)
            a, b = j_safezone_dist(*frame), fn(*frame)
            m = a.notna() & b.notna()
            live = (int(m.sum()) > 0
                    and not bool((a[m].to_numpy() == b[m].to_numpy()).all()))
            caught = _sweep(fn, frame)
            worst = min(worst, caught)
            print(f"  {label:<14} {name:<14} {str(live):>6} "
                  f"{caught:>5} of {len(OFFSETS)}")
    print("\n  Every mutant is LIVE on every frame and caught on at least")
    print(f"  {worst} of the {len(OFFSETS)} offsets, where the module is caught on 0.")
    print("  ⚠ A count below 36 is a property of the FORMULA, not a gap in")
    print("  the mutant: `clip(lower=0)`, the mean over the hits and the")
    print("  `rolling(3).max()` all discard information, so raising the")
    print("  suffix by 3% moves the output only at the offsets where the")
    print("  perturbed bar is the one those three operators select.")


def section_B1():
    print("\n§B1 how LOUD each catch is\n")
    print("  At the first caught offset: how many bars before it move, and")
    print("  by how much. A catch of one bar by 1e-16 would be a rounding")
    print("  accident; these are not.")
    print(f"  {'mutant':<14} {'frame':<14} {'j':>5} {'moved':>6} "
          f"{'max |diff|':>12}")
    for label, old, new in CAUSALITY_MUTANTS:
        fn = _mutant(old, new)
        for name in ("walk", "heavy-tailed"):
            low, close = _frame(name)
            for j in OFFSETS:
                f = Series(np.where(np.arange(close.size) >= j, 1.03, 1.0),
                           index=close.index)
                a = fn(low, close).iloc[:j]
                b = fn(low * f, close * f).iloc[:j]
                m = a.notna() & b.notna()
                moved = int((a[m] != b[m]).sum()) + int(
                    (a.isna() != b.isna()).sum())
                if moved:
                    print(f"  {label:<14} {name:<14} {j:>5} {moved:>6} "
                          f"{_abs(a, b):>12.3e}")
                    break


def section_B2():
    print("\n§B2 the sweep's BLIND SPOT, measured rather than left open\n")
    print("  Five edits that make the output read bar T's OWN low. None")
    print("  reads a LATER bar -- the stop's two `shift(1)`s absorb a")
    print("  one-bar lead -- so the suffix sweep cannot catch any of them,")
    print("  and Gate A's oracle catches all five. `vs oracle` False is a")
    print("  catch, not a failure: it is the oracle rejecting the mutant.")
    print(f"  {'mutant':<12} {'frame':<14} {'swept':>10} {'vs oracle':>10} "
          f"{'rho':>8} {'max |abs|':>11}")
    for label, old, new in BLIND_SPOT_MUTANTS:
        fn = _mutant(old, new)
        for name in ("walk", "heavy-tailed"):
            frame = _frame(name)
            got, want = fn(*frame), _oracle(*frame)
            print(f"  {label:<12} {name:<14} "
                  f"{_sweep(fn, frame):>3} of {len(OFFSETS)} "
                  f"{str(_bit_equal(got, want)):>10} "
                  f"{_spearman(got, want):>8.4f} {_abs(got, want):>11.3e}")


def section_C():
    print("\n§C1 Gate C -- reachability, synthetic\n")
    print(f"  {'frame':<14} {'fired':>6} {'of':>5} {'distinct':>9} "
          f"{'min':>10} {'max':>10} {'<0':>6} {'==0':>5}")
    for name in FRAMES:
        col = _col(name)
        v = col.dropna()
        lo = f"{v.min():.4f}" if v.size else "-"
        hi = f"{v.max():.4f}" if v.size else "-"
        print(f"  {name:<14} {int(col.notna().sum()):>6} {len(col):>5} "
              f"{int(v.nunique()):>9} {lo:>10} {hi:>10} "
              f"{int((v < 0).sum()):>6} {int((v == 0).sum()):>5}")
    print("\n  `flat` and `rising` fire NOWHERE, and that is the column's")
    print("  own shape rather than a defect: `avg` is the mean over bars")
    print("  WITH a down-penetration, and neither frame has one.")
    print("\n  §C2 real data: OWED. Gate E is run by issue-solver after this")
    print("  session, and its 89 BIST frames are where the real-data counts")
    print("  come from.")


def section_D():
    print("\n§D1 Gate D -- x8 / x64, bit-identical\n")
    print(f"  {'frame':<14} {'fired':>6} {'x8':>10} {'x64':>10}")
    for name in VARYING:
        frame = _frame(name)
        base = j_safezone_dist(*frame)
        row = [str(_bit_equal(base, j_safezone_dist(*_scaled(frame, f))))
               for f in (8.0, 64.0)]
        print(f"  {name:<14} {int(base.notna().sum()):>6} "
              f"{row[0]:>10} {row[1]:>10}")
    print("\n§D2 x10 / x3.7 / x0.1 / x1.0000001, a tolerance\n")
    print(f"  {'frame':<14} {'x10':>11} {'x3.7':>11} {'x0.1':>11} "
          f"{'x1.0000001':>11}")
    worst = 0.0
    for name in VARYING:
        frame = _frame(name)
        base = j_safezone_dist(*frame)
        cells = []
        for f in (10.0, 3.7, 0.1, 1.0000001):
            r = _rel(j_safezone_dist(*_scaled(frame, f)), base)
            worst = max(worst, r)
            cells.append(f"{r:.3e}")
        print(f"  {name:<14} {cells[0]:>11} {cells[1]:>11} {cells[2]:>11} "
              f"{cells[3]:>11}")
    print(f"\n  worst cell: {worst:.3e}   (the tests assert 1e-9)")
    print("\n§D3 extreme price levels\n")
    print(f"  {'level':>8} {'fired':>6} {'x8':>8} {'x64':>8} "
          f"{'interm, x8':>13} {'interm, x64':>13}")
    worst_interm = 0.0
    for level in (1e-6, 1e6, 1e100):
        frame = _frame("walk")
        frame = (frame[0] / LEVEL * level, frame[1] / LEVEL * level)
        base = j_safezone_dist(*frame)
        cells, interms = [], []
        for f in (8.0, 64.0):
            scaled = _scaled(frame, f)
            cells.append(str(_bit_equal(base, j_safezone_dist(*scaled))))
            interms.append(_largest_intermediate(*scaled))
            worst_interm = max(worst_interm, interms[-1])
        print(f"  {level:>8.0e} {int(base.notna().sum()):>6} "
              f"{cells[0]:>8} {cells[1]:>8} {interms[0]:>13.3e} "
              f"{interms[1]:>13.3e}")
    print("\n  ⚠ The margin is PRINTED, not reasoned. The largest")
    print("  intermediate anywhere in the chain over all SIX cells is")
    print(f"  {worst_interm:.3e}, against DBL_MAX {np.finfo(float).max:.3e}"
          f" -- a factor of")
    print(f"  {np.finfo(float).max / worst_interm:.3e}, so the rescale does "
          f"not come near")
    print("  overflowing and the bit-identity is the same claim as §D1's.")
    print("  An earlier draft asserted the x64 cells on four prose surfaces")
    print("  while only x8 had been run, then asserted this margin as")
    print("  \"four orders\" when it is over two hundred, then quoted it")
    print("  over six cells when only the three x64 ones had been walked.")
    print("\n§D4 `0 < fires < n`, and a level SHIFT is not invariant\n")
    print(f"  {'frame':<14} {'fires':>6} {'n':>5} {'0<f<n':>7} "
          f"{'shift +10 moves':>16}")
    for name in VARYING:
        low, close = _frame(name)
        base = j_safezone_dist(low, close)
        moved = j_safezone_dist(low + 10.0, close + 10.0)
        m = base.notna() & moved.notna()
        n_moved = int((base[m] != moved[m]).sum())
        fires = int(base.notna().sum())
        print(f"  {name:<14} {fires:>6} {len(base):>5} "
              f"{str(0 < fires < len(base)):>7} "
              f"{n_moved:>7} of {int(m.sum())}")


def section_G():
    print("\n§G1 a bad price EMPTIES BARS -- unlike `j_damiani`\n")
    print(f"  {'leg':<6} {'value':>6} {'plant':>6} {'fired':>6} "
          f"{'emptied':>8} {'first':>6} {'last':>6} {'contiguous':>11}")
    low, close = _frame("walk")
    base = j_safezone_dist(low, close)
    for leg in ("low", "close"):
        for value in (np.nan, np.inf, -np.inf):
            for j in (100, 400, 700, 1100, 1499):
                lo, cl = low.copy(), close.copy()
                (lo if leg == "low" else cl).iloc[j] = value
                col = j_safezone_dist(lo, cl)
                gone = base.notna() & col.isna()
                idx = np.flatnonzero(gone.to_numpy())
                first = idx[0] if idx.size else -1
                last = idx[-1] if idx.size else -1
                contiguous = bool(idx.size
                                  and idx.size == last - first + 1)
                print(f"  {leg:<6} {value:>6.0f} {j:>6} "
                      f"{int(col.notna().sum()):>6} {int(gone.sum()):>8} "
                      f"{first:>6} {last:>6} {str(contiguous):>11}")
    print(f"\n  A plant at the LAST bar is the one that cannot empty "
          f"{PERIOD + LOOKBACK} bars,")
    print("  because the frame ends first. Everything before the first")
    print("  emptied bar is bit-identical:")
    for j in (100, 700):
        lo = low.copy()
        lo.iloc[j] = np.nan
        col = j_safezone_dist(lo, close)
        head = slice(0, j)
        print(f"    low=NaN at {j:>5}: bars < {j} bit-identical: "
              f"{_bit_equal(base.iloc[head], col.iloc[head])}")
    print("\n§G2 the `hits` guard, and what it buys\n")
    bare = _mutant(*HITS_GUARD_OFF)
    print(f"  {'frame':<14} {'guarded':>8} {'bare':>6} {'bit-equal':>10}")
    for name in FRAMES:
        frame = _frame(name)
        a, b = j_safezone_dist(*frame), bare(*frame)
        print(f"  {name:<14} {int(a.notna().sum()):>8} "
              f"{int(b.notna().sum()):>6} {str(_bit_equal(a, b)):>10}")
    print("\n  `total > 0` implies `hits > 0` -- a counted penetration is")
    print("  positive -- so the bare form's only division by zero is 0/0,")
    print("  which is NaN either way. The guard buys the DECISION, here,")
    print("  rather than a different number.")
    print("\n§G3 the final finite guard is NOT a no-op\n")
    unguarded = _mutant(*FINITE_GUARD_OFF)
    print(f"  {'frame':<14} {'bit-equal':>10}")
    for name in FRAMES:
        frame = _frame(name)
        print(f"  {name:<14} "
              f"{str(_bit_equal(j_safezone_dist(*frame), unguarded(*frame))):>10}")
    print("\n  THREE arithmetic routes to an infinity exist on FINITE")
    print("  inputs, not one -- an earlier draft of the module docstring")
    print("  said the final division was the only one. All three are run")
    print("  here, with the intermediates, because only one of the three")
    print("  reaches the output and that is a measurement rather than an")
    print("  argument.")
    print(f"\n  {'route':<33} {'pen max':>10} {'sum(22)':>10} {'stop':>10} "
          f"{'guarded':>20} {'unguarded':>20}")
    for label, lo, cl in _OVERFLOW_ROUTES():
        with np.errstate(over="ignore", invalid="ignore"):
            pen = (lo.where(np.isfinite(lo)).shift(1)
                   - lo.where(np.isfinite(lo))).clip(lower=0.0)
            total = pen.rolling(PERIOD, min_periods=PERIOD).sum()
            hits = (pen > 0.0).astype(float).rolling(
                PERIOD, min_periods=PERIOD).sum()
            avg = total / hits.where(hits > 0.0)
            stop = (lo.shift(1) - MULT * avg.shift(1)
                    ).rolling(LOOKBACK, min_periods=LOOKBACK).max()
            guarded, bare_fin = j_safezone_dist(lo, cl), unguarded(lo, cl)

        def _tag(s):
            if int(np.isinf(s).sum()):
                return "inf"
            if int(s.notna().sum()) == 0:
                return "all NaN"
            return f"{float(s.dropna().abs().max()):.2e}"

        print(f"  {label:<33} {_tag(pen):>10} {_tag(total):>10} "
              f"{_tag(stop):>10} "
              f"{f'inf {int(np.isinf(guarded).sum())} nan {int(guarded.isna().sum())}':>20} "
              f"{f'inf {int(np.isinf(bare_fin).sum())} nan {int(bare_fin.isna().sum())}':>20}")
    print("\n  ⚠ Read the `sum(22)` column: on routes 1 and 2 it is all")
    print("  NaN, so neither route reaches the output and the final mask")
    print("  is not what stops them -- pandas' `rolling.sum` is")
    print("  COMPENSATED (Kahan), and once the compensation term goes NaN")
    print("  every later window does too.")
    print("\n  ⚠ That is NOT a guarantee, and the probes below are what")
    print("  say so rather than a reassuring sentence. They are 81 bars")
    print("  with the bad value in the MIDDLE, because a 31-bar probe with")
    print("  it at bar 0 cannot tell the contamination from `min_periods`'")
    print("  own warm-up (PERIOD - 1 = 21 windows of ANY frame) -- an")
    print("  earlier draft read 22 NaNs as 22 contaminated windows when 21")
    print("  of them were warm-up.")
    print(f"\n  {'probe':<30} {'inf':>5} {'warm-up':>8} {'extra':>6} "
          f"{'blanked bars':>16}")
    for label, values in _ROLLING_SUM_PROBES():
        with np.errstate(over="ignore", invalid="ignore"):
            rolled = Series(values).rolling(PERIOD, min_periods=PERIOD).sum()
        nan_idx = np.flatnonzero(rolled.isna().to_numpy())
        extra = nan_idx[nan_idx >= PERIOD - 1]
        span = (f"{extra[0]} .. {extra[-1]}" if extra.size else "-")
        print(f"  {label:<30} {int(np.isinf(rolled).sum()):>5} "
              f"{PERIOD - 1:>8} {extra.size:>6} {span:>16}")
    print("\n  ⚠ The `inf` column is the finding. An input `+inf` blanks")
    print("  all 22 windows that hold it and ships no infinity; TWO")
    print("  DBL_MAX summands do not -- the window in which the overflow")
    print("  first happens reads +inf, and only the 21 after it are NaN.")
    print("  So \"the compensated sum absorbs an overflow\" is true of")
    print("  routes 1 and 2's frames and is NOT a rule. That is why the")
    print("  final mask stays, and why the assertion that matters is on")
    print("  this MODULE's output rather than on a pandas internal.")
    print("\n§G4 degenerate frames raise nothing\n")
    for label, value in (("zeros", 0.0), ("negative", -100.0),
                         ("subnormal", 5e-310), ("huge", 1e308)):
        idx2 = date_range("2020-01-01", periods=60, freq="h")
        s = Series(np.full(60, value), index=idx2)
        with np.errstate(all="ignore"):
            col = j_safezone_dist(s, s)
        print(f"  {label:<10} fired {int(col.notna().sum()):>3} of 60, "
              f"infinite {int(np.isinf(col).sum()):>3}")
    print("\n§G5 frames below MIN_BARS, and a constant-NaN frame\n")
    for n in (0, 1, 5):
        empty = Series(np.full(n, 100.0),
                       index=date_range("2020-01-01", periods=n, freq="h"))
        print(f"  {n} bars (< MIN_BARS {MIN_BARS}): "
              f"{j_safezone_dist(empty, empty)!r}")
    allnan = Series(np.full(100, np.nan), index=date_range(
        "2020-01-01", periods=100, freq="h"))
    col = j_safezone_dist(allnan, allnan)
    print(f"  100 all-NaN bars: fired "
          f"{0 if col is None else int(col.notna().sum())}")


def section_L():
    print("\n§L what the column reads -- in-fork overlap, SYNTHETIC\n")
    print("  SEVEN neighbours, chosen as the nearest questions this fork")
    print("  already answers -- NOT a sweep of the 356 registered")
    print("  indicators. Scale-free, at their defaults, Spearman against")
    print("  the shipped column, over the six varying frames. ⚠ This is a")
    print("  DISCLOSURE and not Gate E: the 687 engine comparators hold no")
    print("  pandas_ta port, and the screen's own fork-overlap stage ran on")
    print("  12 REAL frames and put `LINREG_LOWER_2_DIST_PCT` nearest at")
    print("  0.7578.")
    names = []
    rows = {}
    for name in VARYING:
        high, low, close = FRAMES[name]()
        col = j_safezone_dist(low, close)
        others = {}
        others["NATR_14"] = natr(high, low, close)
        others["CHOP_14_1_100"] = chop(high, low, close)
        others["VHF_28"] = vhf(close)
        others["RVI_14"] = rvi(close, high, low)
        adx_df = adx(high, low, close)
        others["ADX_14"] = adx_df.iloc[:, 0]
        others["MASSI_9_9"] = massi(high, low)
        lrc = linreg_channel(close)
        others["LINREG_LOWER_2_DIST_PCT"] = lrc["LINREG_LOWER_2_DIST_PCT"]
        for key, other in others.items():
            rows.setdefault(key, {})[name] = _spearman(col, other)
        names.append(name)
    print(f"\n  {'comparator':<26} " + " ".join(f"{n[:9]:>9}" for n in names)
          + f" {'max |rho|':>10}")
    for key in sorted(rows, key=lambda k: -max(
            abs(v) for v in rows[k].values() if v == v)):
        cells = " ".join(f"{rows[key][n]:>9.4f}" for n in names)
        best = max(abs(v) for v in rows[key].values() if v == v)
        print(f"  {key:<26} {cells} {best:>10.4f}")


def section_W():
    print("\n§W the dictionary's 150-character cut\n")
    import ast
    import re
    path = Path(__file__).resolve().with_name("gen_indicator_dictionary.py")
    tree = ast.parse(path.read_text(encoding="utf-8"))
    fn = next(n for n in tree.body
              if isinstance(n, ast.FunctionDef) and n.name == "desc")
    ns = {"re": re}
    exec(compile(ast.Module(body=[fn], type_ignores=[]), "<desc>", "exec"), ns)
    doc = j_safezone_dist.__doc__.splitlines()
    body = []
    for line in doc[1:]:
        s = line.strip()
        if s:
            body.append(s)
        elif body:
            break
    full = " ".join(body)
    cut = ns["desc"]({"desc": full})
    print(f"  first paragraph ({len(full)} chars):\n    {full}")
    print(f"\n  after the cut ({len(cut)} chars):\n    {cut}")
    print(f"\n  survives whole: {'…' not in cut}")


def section_Z():
    print("\n§Z cost\n")
    print("  ⚠ one machine, one run. Nothing else in this file depends on")
    print("  either, and no claim anywhere divides by these numbers.")
    for n in (1_500, 50_000, 400_000):
        frame = (_walk(n=n)[1], _walk(n=n)[2])
        tracemalloc.start()
        j_safezone_dist(*frame)
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        best = min(timeit.repeat(lambda: j_safezone_dist(*frame), number=1,
                                 repeat=3))
        print(f"  {n:>8,} bars: {best * 1e3:>8.2f} ms   "
              f"{best / n * 1e6:>7.3f} us/bar   peak {peak / 2 ** 20:>6.1f} MB")


SECTIONS = {
    "A1": section_A1, "A2": section_A2, "A3": section_A3, "A4": section_A4,
    "B": section_B, "B1": section_B1, "B2": section_B2, "C": section_C,
    "D": section_D, "G": section_G, "L": section_L, "W": section_W,
    "Z": section_Z,
}


if __name__ == "__main__":
    print(f"pandas {pd.__version__}, numpy {np.__version__}")
    print(f"jesse installed: {importlib.util.find_spec('jesse') is not None}")
    wanted = sys.argv[1:] or list(SECTIONS)
    for key in wanted:
        if key not in SECTIONS:
            raise SystemExit(f"unknown section {key!r}; "
                             f"have {', '.join(SECTIONS)}")
        SECTIONS[key]()
