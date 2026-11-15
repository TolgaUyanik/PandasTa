# -*- coding: utf-8 -*-
"""J-GATOR (PandasTa issue #104): every number in `docs/JGatorMeasured.md`.

    python docs/measure_j_gator.py            # every section, in order
    python docs/measure_j_gator.py A1 D       # named sections only

One section per gate limb, printed and never derived: the repo's dominant
defect is "a claim written before it was measured", so this file is the
only place a figure in the receipt, the module docstring or
`tests/test_j_gator.py` may come from.

    mid     = (high + low) / 2
    jaw     = SMMA(mid, 13) displaced 8 bars
    teeth   = SMMA(mid, 8)  displaced 5 bars
    lips    = SMMA(mid, 5)  displaced 3 bars
    J_GATOR = (|jaw - teeth| - |teeth - lips|) / close

⚠ The millisecond figures of §Z are this machine's and this run's. Nothing
else here depends on the machine, and `docs/measure_j_gator_cpu.py` re-runs
the sections under numpy's reduced CPU dispatch to show which figures move.
"""
import importlib.util
import sys
import timeit
import tracemalloc
from pathlib import Path

import numpy as np
import pandas as pd
from pandas import Series, date_range

from pandas_ta.momentum.ao import ao
from pandas_ta.momentum.j_gator import JAW, LIPS, MIN_BARS, TEETH, j_gator
from pandas_ta.momentum.qqe import qqe
from pandas_ta.overlap.ichimoku_ml import ichimoku_ml
from pandas_ta.overlap.rma import rma
from pandas_ta.trend.chop import chop
from pandas_ta.volatility.natr import natr

N = 1500
LEVEL = 100.0
#: Bars the column cannot fire on: the longest lag, and nothing else. The
#: EWMA is seeded at bar 0, so there is no `length - 1` warm-up here.
WARMUP = JAW[1]
FIRED = N - WARMUP


# ------------------------------------------------------------------ frames


def _ohlc(close, seed):
    """An OHLC frame around a close path, with `high >= close >= low`.

    The spread is random so that `mid = (high + low) / 2` is NOT the close:
    a frame where it is would hide any confusion between the two.
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
    """An Ornstein-Uhlenbeck path: the regime where the Alligator lines
    stay braided and the two spreads are of the same order."""
    rng = np.random.default_rng(seed)
    x = np.zeros(n)
    for i in range(1, n):
        x[i] = 0.9 * x[i - 1] + rng.normal(0.0, 0.02)
    return _ohlc(level * np.exp(x), seed)


def _grid(seed=17, n=N, level=LEVEL, tick=0.01):
    """A walk quantised to a tick grid, which is what real prices are."""
    h, l, c = _walk(seed, n, level)
    return (np.round(h / tick) * tick,
            np.round(l / tick) * tick,
            np.round(c / tick) * tick)


def _heavy(seed=19, n=N, level=LEVEL):
    rng = np.random.default_rng(seed)
    r = rng.standard_t(2.0, n) * 0.006
    return _ohlc(level * np.exp(np.cumsum(r)), seed)


def _jump(seed=23, n=N, level=LEVEL):
    """A walk with a single x1.5 gap at bar 700 -- the shape that opens the
    jaw-teeth spread far wider than the teeth-lips one."""
    h, l, c = _walk(seed, n, level)
    f = Series(np.where(np.arange(n) >= 700, 1.5, 1.0), index=c.index)
    return h * f, l * f, c * f


def _flat(n=N, level=LEVEL):
    """A constant price. Every SMMA equals the level, both spreads are
    exactly zero, and so is the column."""
    idx = date_range("2020-01-01", periods=n, freq="h")
    one = Series(np.full(n, level), index=idx)
    return one.copy(), one.copy(), one.copy()


FRAMES = {
    "walk": _walk,
    "trend": _trend,
    "range-bound": _range_bound,
    "grid": _grid,
    "heavy-tailed": _heavy,
    "jump": _jump,
    "flat": _flat,
}
#: Every frame but the flat one, whose column is identically 0.0.
VARYING = [n for n in FRAMES if n != "flat"]


def _scaled(frame, factor):
    h, l, c = frame
    return h * factor, l * factor, c * factor


def _agree(a, b):
    """(masks equal, shared bars, bit-equal bars, max |diff|, max |rel|)."""
    masks = bool((a.isna() == b.isna()).all())
    m = a.notna() & b.notna()
    if not int(m.sum()):
        return masks, 0, 0, float("nan"), float("nan")
    d = (a[m] - b[m]).abs()
    scale = b[m].abs().where(b[m].abs() > 0.0, np.nan)
    return (masks, int(m.sum()), int((a[m] == b[m]).sum()),
            float(d.max()), float((d / scale).max()))


def _spearman(a, b):
    m = a.notna() & b.notna()
    if int(m.sum()) < 3 or a[m].nunique() < 2 or b[m].nunique() < 2:
        return float("nan")
    return float(a[m].corr(b[m], method="spearman"))


# ----------------------------------------------------------------- oracles


def _smma_recursion(x, length, lag):
    """`SMMA(x, length)` by an explicit Python recursion, then displaced.

    Seeded at the first observation and spelled
    `(1 - a) * s[i-1] + a * x[i]`, which is what pandas' `ewm` with
    `adjust=False` computes up to the division by `(1 - a) + a` -- the
    reason §A1 is a relative bound and not bit-equality.
    """
    a = 1.0 / length
    s = np.empty(x.size)
    s[0] = x[0]
    for i in range(1, x.size):
        s[i] = (1.0 - a) * s[i - 1] + a * x[i]
    out = np.full(x.size, np.nan)
    out[lag:] = s[: x.size - lag]
    return out


def _oracle(high, low, close):
    """The issue's formula, sharing no code with the module: a hand-written
    recursion, hand-written lags, numpy's `abs`."""
    mid = (high.to_numpy(dtype=float) + low.to_numpy(dtype=float)) / 2
    jaw = _smma_recursion(mid, *JAW)
    teeth = _smma_recursion(mid, *TEETH)
    lips = _smma_recursion(mid, *LIPS)
    val = (np.abs(jaw - teeth) - np.abs(teeth - lips))
    return Series(val / close.to_numpy(dtype=float), index=close.index)


def _prototype(high, low, close):
    """The screen prototype, retyped from `docs/issues/screen/ind_screen.py`
    candidate `j_gator` (that file is gitignored, so it exists only on the
    owner's machine):

        mid = (h + l) / 2
        sm = lambda n: mid.ewm(alpha=1 / n, adjust=False).mean()
        jaw, teeth, lips = sm(13).shift(8), sm(8).shift(5), sm(5).shift(3)
        return ((jaw - teeth).abs() - (teeth - lips).abs()) / c
    """
    mid = (high + low) / 2
    sm = lambda n: mid.ewm(alpha=1 / n, adjust=False).mean()  # noqa: E731
    jaw, teeth, lips = sm(13).shift(8), sm(8).shift(5), sm(5).shift(3)
    return ((jaw - teeth).abs() - (teeth - lips).abs()) / close


def _sma_seeded(x, length, lag):
    """The OTHER SMMA: seeded with `SMA(x[:length])` at bar `length - 1`,
    NaN before it. TradingView's `ta.rma` and most "smoothed moving
    average" descriptions mean this one."""
    a = 1.0 / length
    s = np.full(x.size, np.nan)
    s[length - 1] = x[:length].mean()
    for i in range(length, x.size):
        s[i] = (1.0 - a) * s[i - 1] + a * x[i]
    out = np.full(x.size, np.nan)
    out[lag:] = s[: x.size - lag]
    return out


def _sma_seeded_column(high, low, close):
    mid = (high.to_numpy(dtype=float) + low.to_numpy(dtype=float)) / 2
    jaw = _sma_seeded(mid, *JAW)
    teeth = _sma_seeded(mid, *TEETH)
    lips = _sma_seeded(mid, *LIPS)
    val = np.abs(jaw - teeth) - np.abs(teeth - lips)
    return Series(val / close.to_numpy(dtype=float), index=close.index)


def _rma_column(high, low, close):
    """The same formula over this fork's `rma`, i.e. pandas' `ewm` at its
    DEFAULT `adjust=True` with `min_periods=length`."""
    mid = (high + low) / 2
    jaw = rma(mid, JAW[0]).shift(JAW[1])
    teeth = rma(mid, TEETH[0]).shift(TEETH[1])
    lips = rma(mid, LIPS[0]).shift(LIPS[1])
    return ((jaw - teeth).abs() - (teeth - lips).abs()) / close


def _ema_column(high, low, close):
    """The same formula over a PLAIN EMA -- `alpha = 2 / (n + 1)`, i.e.
    `ewm(span=n, adjust=False)` -- which is the other thing "a moving
    average of period n" can mean. Wilder's smoothing (`alpha = 1/n`) is
    the reading the issue's "SMMA" and the prototype carry; this is the
    reading that would follow from mis-reading SMMA as EMA, and §A4(c)
    prices it.

    `adjust=False` is held FIXED here on purpose: it is the axis §A4(b)
    isolates, so leaving it alone makes the alpha the only difference
    from the shipped column."""
    mid = (high + low) / 2

    def line(length, lag):
        return mid.ewm(span=length, adjust=False).mean().shift(lag)

    jaw, teeth, lips = line(*JAW), line(*TEETH), line(*LIPS)
    return ((jaw - teeth).abs() - (teeth - lips).abs()) / close


# ----------------------------------------------------------------- mutants

SOURCE = Path(__file__).resolve().parents[1] / "pandas_ta" / "momentum" \
    / "j_gator.py"

#: Each entry is (label, what it does, old text, new text). Every one is an
#: edit to the SHIPPED source read off disk, exec'd in memory -- never a
#: re-implementation, which could differ from the module for reasons that
#: have nothing to do with causality.
MUTANTS = [
    ("jaw-lead", "the jaw reads 8 bars AHEAD instead of 8 behind",
     "JAW = (13, 8)", "JAW = (13, -8)"),
    ("teeth-lead", "the teeth read 5 bars ahead",
     "TEETH = (8, 5)", "TEETH = (8, -5)"),
    ("lips-lead", "the lips read 3 bars ahead",
     "LIPS = (5, 3)", "LIPS = (5, -3)"),
    ("output-early", "the whole column is written one bar early",
     "    gator = ((jaw - teeth).abs() - (teeth - lips).abs()) / c",
     "    gator = (((jaw - teeth).abs() - (teeth - lips).abs())"
     " / c).shift(-1)"),
    ("divisor-lead", "the scale-free divisor is tomorrow's close",
     ".abs()) / c", ".abs()) / c.shift(-1)"),
    ("close-guard-off", "the close guard is removed (NOT a causality"
                        " mutant: §G1's justification for the guard)",
     "c = close.where(np.isfinite(close) & (close >= np.finfo(float).tiny))",
     "c = close"),
]


def _mutant(old, new):
    """The shipped module, read off disk, one substring replaced, exec'd in
    memory. Refuses an anchor that is not unique, so a mutation cannot
    silently hit a different line after an edit."""
    src = SOURCE.read_text(encoding="utf-8")
    assert src.count(old) == 1, f"{old!r} occurs {src.count(old)} times"
    ns = {}
    exec(compile(src.replace(old, new), "<mutant>", "exec"), ns)
    return ns["j_gator"]


#: The 36 perturbation points of the blind causality sweep: the last 36
#: bars a future can start at. Each one is "change every bar >= J and see
#: whether any bar < J moves".
OFFSETS = list(range(N - 36, N))


def _future_sweep(fn, frame, offsets=None, factor=1.03):
    """How many of `offsets` the function is CAUGHT reading the future at.

    Caught means: perturbing high, low and close at every bar >= J moved at
    least one bar < J. A causal column cannot be caught at any J.
    """
    h, l, c = frame
    base = fn(h, l, c)
    caught = 0
    for j in offsets or OFFSETS:
        f = Series(np.where(np.arange(c.size) >= j, factor, 1.0), index=c.index)
        out = fn(h * f, l * f, c * f)
        a, b = base.iloc[:j], out.iloc[:j]
        if not (a.isna() == b.isna()).all() or \
                not bool((a.dropna() == b.dropna()).all()):
            caught += 1
    return caught


# ---------------------------------------------------------------- sections


def _head(title):
    print()
    print("=" * 72)
    print(title)
    print("=" * 72)


def section_A1():
    _head("A1 Gate A -- the issue's formula, spelled independently")
    print("A hand-written recursion + hand-written lags vs the module, per")
    print("frame. An independent spelling is NOT OBLIGED to round the same")
    print("way -- pandas' `ewm` divides by `(1 - alpha) + alpha`, which is")
    print("not 1.0 for every alpha -- so the test asserts a bound. Measured")
    print("0.000e+00 here, because that sum IS exactly 1.0 for alpha = 1/13,")
    print("1/8 and 1/5 on this machine.")
    print()
    print(f"{'frame':<14} {'masks':>5} {'bars':>6} {'bit-eq':>7} "
          f"{'max |diff|':>12} {'max |rel|':>11}")
    worst = 0.0
    for name in FRAMES:
        frame = FRAMES[name]()
        masks, shared, same, d, rel = _agree(j_gator(*frame), _oracle(*frame))
        worst = max(worst, 0.0 if np.isnan(rel) else rel)
        print(f"{name:<14} {str(masks):>5} {shared:>6} {same:>7} "
              f"{d:>12.3e} {rel:>11.3e}")
    print()
    print(f"worst relative difference over all frames: {worst:.3e}")


def section_A2():
    _head("A2 Gate A -- the screen prototype, bit for bit")
    print("The prototype shares the module's spelling of SMMA (pandas'")
    print("`ewm`), so this limb is EXACT, and it is the limb that ties this")
    print("port to the 2026-10-24 Gate E figures.")
    print()
    print(f"{'frame':<14} {'masks':>5} {'bars':>6} {'bit-eq':>7} "
          f"{'max |diff|':>12}")
    for name in FRAMES:
        frame = FRAMES[name]()
        masks, shared, same, d, _ = _agree(j_gator(*frame), _prototype(*frame))
        print(f"{name:<14} {str(masks):>5} {shared:>6} {same:>7} {d:>12.3e}")
    print()
    print("Same, with the prototype's own `(h + l) / 2` vs the module's:")
    h, l, c = FRAMES["walk"]()
    mid_a = (h + l) / 2
    mid_b = 0.5 * (h + l)
    print(f"  (h + l) / 2 == 0.5 * (h + l) on all bars: "
          f"{bool((mid_a == mid_b).all())}")


def section_A3():
    _head("A3 the lag is a BACKWARD read, and the column's reach")
    print("`shift(lag)` with lag > 0 means bar T reads the smoothed value")
    print("of bar T - lag. Pinned against an explicit index walk, and the")
    print("first fired bar is the longest lag.")
    print()
    h, l, c = FRAMES["walk"]()
    mid = (h + l) / 2
    for length, lag in (JAW, TEETH, LIPS):
        line = mid.ewm(alpha=1.0 / length, adjust=False).mean()
        shifted = line.shift(lag)
        same = all(shifted.iloc[t] == line.iloc[t - lag]
                   for t in range(lag, mid.size))
        print(f"  SMMA({length:2d}) lag {lag}: shifted[T] == line[T - lag] "
              f"on all {mid.size - lag} bars: {same}; "
              f"NaN on the first {int(shifted.isna().sum())}")
    col = j_gator(h, l, c)
    first = int(col.notna().to_numpy().argmax())
    print()
    print(f"  column: first fired bar {first}, NaN bars "
          f"{int(col.isna().sum())}, fired {int(col.notna().sum())} of "
          f"{col.size}")
    print(f"  MIN_BARS = {MIN_BARS}; a {MIN_BARS - 1}-bar frame returns "
          f"{j_gator(h.iloc[:MIN_BARS - 1], l.iloc[:MIN_BARS - 1], c.iloc[:MIN_BARS - 1])}")
    short = j_gator(h.iloc[:MIN_BARS], l.iloc[:MIN_BARS], c.iloc[:MIN_BARS])
    print(f"  a {MIN_BARS}-bar frame fires on {int(short.notna().sum())} bars")


def section_A4():
    _head("A4 WHICH SMMA -- the seed and the alpha, priced")
    print("The issue says SMMA and the prototype spells it")
    print("`ewm(alpha=1/n, adjust=False)`, seeded at the FIRST value.")
    print("THREE other readings of that name exist, and this section is what")
    print("choosing one costs. ⚠ jesse's own smoother is NOT read here --")
    print("jesse is not installed and web access is unavailable -- so none")
    print("of this is evidence about what jesse computes.")
    print()
    print("(a) SMA-seeded SMMA (TradingView's `ta.rma`): same recursion,")
    print("    seeded with SMA(x[:length]) at bar length - 1.")
    print(f"{'frame':<14} {'shared':>7} {'bit-eq':>7} {'max |diff|':>12} "
          f"{'rho':>8}")
    for name in VARYING:
        frame = FRAMES[name]()
        base, other = j_gator(*frame), _sma_seeded_column(*frame)
        _, shared, same, d, _ = _agree(base, other)
        print(f"{name:<14} {shared:>7} {same:>7} {d:>12.3e} "
              f"{_spearman(base, other):>8.4f}")
    print()
    print("    and how fast the two converge on the walk -- max |diff| over")
    print("    bars >= k, which is monotone by construction:")
    frame = FRAMES["walk"]()
    base, other = j_gator(*frame), _sma_seeded_column(*frame)
    m = base.notna() & other.notna()
    diff = (base[m] - other[m]).abs().to_numpy()
    bars = np.arange(base.size)[m.to_numpy()]
    for k in (8, 20, 50, 100, 200, 400):
        tail = diff[bars >= k]
        print(f"      bars >= {k:>4}: max |diff| {tail.max():.3e}  "
              f"(column max |value| {base[m].abs().max():.3e})")
    print()
    print("(b) this fork's `rma` (pandas' DEFAULT adjust=True, "
          "min_periods=length):")
    print(f"{'frame':<14} {'shared':>7} {'bit-eq':>7} {'max |diff|':>12} "
          f"{'rho':>8}")
    for name in VARYING:
        frame = FRAMES[name]()
        base, other = j_gator(*frame), _rma_column(*frame)
        _, shared, same, d, _ = _agree(base, other)
        print(f"{name:<14} {shared:>7} {same:>7} {d:>12.3e} "
              f"{_spearman(base, other):>8.4f}")
    print()
    print("(c) a PLAIN EMA -- alpha = 2/(n+1), `ewm(span=n, adjust=False)`")
    print("    -- which is what reading 'SMMA' as 'EMA' would give. This is")
    print("    the reading the issue's wording excludes, and the ONLY one")
    print("    that changes the smoother's memory rather than its warm-up.")
    print("    `adjust=False` is held fixed, so the alpha is the only")
    print("    difference from the shipped column:")
    print(f"{'frame':<14} {'shared':>7} {'bit-eq':>7} {'max |diff|':>12} "
          f"{'rho':>8}")
    for name in VARYING:
        frame = FRAMES[name]()
        base, other = j_gator(*frame), _ema_column(*frame)
        _, shared, same, d, _ = _agree(base, other)
        print(f"{name:<14} {shared:>7} {same:>7} {d:>12.3e} "
              f"{_spearman(base, other):>8.4f}")


def section_B():
    _head("B Gate B -- the mutants, and the blind sweep")
    print(f"{len(OFFSETS)} perturbation points (bars {OFFSETS[0]}..{OFFSETS[-1]}),")
    print("every bar >= J multiplied by 1.03. Caught = some bar < J moved.")
    print()
    frames = {n: FRAMES[n]() for n in VARYING}
    print("the SHIPPED module, which must be caught nowhere:")
    for name, frame in frames.items():
        print(f"  {name:<14} caught {_future_sweep(j_gator, frame):>2} of "
              f"{len(OFFSETS)}")
    print()
    for label, what, old, new in MUTANTS:
        fn = _mutant(old, new)
        print(f"{label} -- {what}")
        for name, frame in frames.items():
            base, mut = j_gator(*frame), fn(*frame)
            m = base.notna() & mut.notna()
            moved = int((base[m] != mut[m]).sum())
            live = moved > 0 or not bool((base.isna() == mut.isna()).all())
            caught = _future_sweep(fn, frame)
            print(f"  {name:<14} live {str(live):<5} moved {moved:>5} of "
                  f"{int(m.sum()):>5}  caught {caught:>2} of {len(OFFSETS)}")
        print()
    print("B2 what the blind sweep sees at ONE offset, for the mutant it")
    print("   catches least often -- how many bars < J move, and by how")
    print("   much, on each frame:")
    fn = _mutant(MUTANTS[1][2], MUTANTS[1][3])
    for name, frame in frames.items():
        h, l, c = frame
        base = fn(h, l, c)
        for j in (OFFSETS[0], OFFSETS[18], OFFSETS[-1]):
            f = Series(np.where(np.arange(c.size) >= j, 1.03, 1.0),
                       index=c.index)
            out = fn(h * f, l * f, c * f)
            a, b = base.iloc[:j], out.iloc[:j]
            m = a.notna() & b.notna()
            moved = int((a[m] != b[m]).sum())
            d = float((a[m] - b[m]).abs().max())
            print(f"   {name:<14} J={j} moved {moved:>2} bar(s) of "
                  f"{int(m.sum())}, max |diff| {d:.3e}")
    print()
    print("B3 WHY, and it is a fact about the COLUMN rather than about the")
    print("   mutant: whenever the teeth line is the OUTER one of the three,")
    print("   it CANCELS out of `|jaw-teeth| - |teeth-lips|` -- the column")
    print("   is then the signed jaw-lips spread and reads the teeth not at")
    print("   all. A mutant whose teeth read the future is outer far more")
    print("   often, so there is nothing for the blind sweep to see.")
    print()
    print("   `outer` is the share of fired bars on which the teeth cancel,")
    print("   `max |id. diff|` the agreement with the jaw-lips spread there,")
    print("   and `sweep` the teeth mutant's catches of 36. The MUTANT's own")
    print("   share is the one that predicts the sweep, so both are printed.")
    print()
    print(f"{'frame':<14} {'outer':>7} {'of':>6} {'share':>7} "
          f"{'max |id. diff|':>14} {'mut. outer':>11} {'sweep':>6}")
    fn = _mutant(MUTANTS[1][2], MUTANTS[1][3])
    for name, frame in frames.items():
        h, l, c = frame
        mid = (h + l) / 2

        def lines(teeth_lag):
            return (mid.ewm(alpha=1 / JAW[0], adjust=False).mean().shift(JAW[1]),
                    mid.ewm(alpha=1 / TEETH[0], adjust=False).mean().shift(teeth_lag),
                    mid.ewm(alpha=1 / LIPS[0], adjust=False).mean().shift(LIPS[1]))

        def outer_mask(jaw, teeth, lips):
            pair = pd.concat([jaw, lips], axis=1)
            hi, lo = pair.max(axis=1), pair.min(axis=1)
            return (teeth >= hi), (teeth <= lo)

        jaw, teeth, lips = lines(TEETH[1])
        col = j_gator(h, l, c)
        m = col.notna()
        up, dn = outer_mask(jaw, teeth, lips)
        outer = (up | dn) & m
        ident = Series(np.where(up, 1.0, -1.0), index=col.index) \
            * (lips - jaw) / c
        d = float((col[outer] - ident[outer]).abs().max())
        mjaw, mteeth, mlips = lines(-TEETH[1])
        mup, mdn = outer_mask(mjaw, mteeth, mlips)
        mcol = fn(h, l, c)
        mm = mcol.notna()
        mouter = (mup | mdn) & mm
        print(f"{name:<14} {int(outer.sum()):>7} {int(m.sum()):>6} "
              f"{int(outer.sum()) / int(m.sum()):>7.4f} {d:>14.3e} "
              f"{int(mouter.sum()) / int(mm.sum()):>11.4f} "
              f"{_future_sweep(fn, frame):>6}")
    print()
    print("B4 the same mutant, swept only where the mechanism lets it show.")
    print("   An offset J can only be caught if the mutant's teeth are")
    print("   INTERIOR on at least one of bars J-5 .. J-1 -- that is where")
    print("   its look-ahead reaches -- OR if the perturbation itself flips")
    print("   which line is outer there. `catchable` counts the offsets the")
    print("   UNPERTURBED mutant already exposes, `caught` the sweep's")
    print("   catches among them, and `elsewhere` its catches among the")
    print("   rest, which are the flips and are not a surprise.")
    print()
    print(f"{'frame':<14} {'catchable':>10} {'caught':>7} {'elsewhere':>10} "
          f"{'of':>4}")
    for name, frame in frames.items():
        h, l, c = frame
        mid = (h + l) / 2
        mjaw = mid.ewm(alpha=1 / JAW[0], adjust=False).mean().shift(JAW[1])
        mteeth = mid.ewm(alpha=1 / TEETH[0], adjust=False).mean().shift(-TEETH[1])
        mlips = mid.ewm(alpha=1 / LIPS[0], adjust=False).mean().shift(LIPS[1])
        pair = pd.concat([mjaw, mlips], axis=1)
        interior = ((mteeth < pair.max(axis=1)) & (mteeth > pair.min(axis=1))
                    & fn(h, l, c).notna()).to_numpy()
        hit = miss = catchable = 0
        for j in OFFSETS:
            reach = interior[max(0, j - TEETH[1]):j].any()
            caught = _future_sweep(fn, frame, offsets=[j]) == 1
            catchable += int(bool(reach))
            if reach:
                hit += int(caught)
            else:
                miss += int(caught)
        print(f"{name:<14} {catchable:>10} {hit:>7} {miss:>10} "
              f"{len(OFFSETS):>4}")


def section_C():
    _head("C Gate C -- reachability on synthetic frames")
    print("Real-data counts are owed with the Gate E run (the launcher's).")
    print()
    print(f"{'frame':<14} {'fired':>6} {'of':>6} {'distinct':>9} "
          f"{'>0':>6} {'<0':>6} {'==0':>6} {'min':>11} {'max':>11}")
    for name in FRAMES:
        col = j_gator(*FRAMES[name]())
        v = col.dropna()
        print(f"{name:<14} {v.size:>6} {col.size:>6} {v.nunique():>9} "
              f"{int((v > 0).sum()):>6} {int((v < 0).sum()):>6} "
              f"{int((v == 0).sum()):>6} {v.min():>11.3e} {v.max():>11.3e}")
    print()
    print("the flat frame, exactly:")
    flat = j_gator(*FRAMES["flat"]()).dropna()
    print(f"  all bars exactly 0.0: {bool((flat == 0.0).all())} "
          f"({flat.size} bars)")
    print()
    print("a two-sided bound nobody should assume: the column is NOT")
    print("bounded in [-1, 1] by construction -- it is a spread difference")
    print("over a price -- so here is what the frames reach:")
    allv = pd.concat([j_gator(*FRAMES[n]()).dropna() for n in FRAMES])
    print(f"  pooled {allv.size} bars, min {allv.min():.6e}, "
          f"max {allv.max():.6e}, mean {allv.mean():.6e}")
    print(f"  |value| <= 0.1 on {int((allv.abs() <= 0.1).sum())} of "
          f"{allv.size}")


def section_D():
    _head("D Gate D -- scale-free")
    print("(a) x8 / x64, which are EXACT in binary and must be bit-identical:")
    print(f"{'frame':<14} {'factor':>7} {'masks':>5} {'bars':>6} "
          f"{'bit-eq':>7} {'max |diff|':>12}")
    for name in FRAMES:
        frame = FRAMES[name]()
        base = j_gator(*frame)
        for factor in (8.0, 64.0):
            masks, shared, same, d, _ = _agree(
                base, j_gator(*_scaled(frame, factor)))
            print(f"{name:<14} {factor:>7.0f} {str(masks):>5} {shared:>6} "
                  f"{same:>7} {d:>12.3e}")
    print()
    print("(b) x10 / x3.7 / x0.1 / x1.0000001, which are NOT exact:")
    print(f"{'frame':<14} {'factor':>10} {'masks':>5} {'bit-eq':>7} "
          f"{'of':>6} {'max |rel|':>11}")
    worst = 0.0
    for name in VARYING:
        frame = FRAMES[name]()
        base = j_gator(*frame)
        for factor in (10.0, 3.7, 0.1, 1.0000001):
            masks, shared, same, _, rel = _agree(
                base, j_gator(*_scaled(frame, factor)))
            worst = max(worst, 0.0 if np.isnan(rel) else rel)
            print(f"{name:<14} {factor:>10.7f} {str(masks):>5} {same:>7} "
                  f"{shared:>6} {rel:>11.3e}")
    print()
    print(f"worst relative difference: {worst:.3e}")
    print()
    print("(c) the same at extreme price LEVELS, x8 / x64 again. `finite`")
    print("    counts the fired bars that are not inf -- §G5 cites it, and")
    print("    `fired` alone cannot carry that claim because an infinity is")
    print("    not NaN:")
    for level in (1e-6, 1e+6, 1e+100):
        frame = _walk(level=level)
        base = j_gator(*frame)
        row = []
        for factor in (8.0, 64.0):
            _, shared, same, _, _ = _agree(base, j_gator(*_scaled(frame, factor)))
            row.append(f"x{factor:.0f}: {same} of {shared}")
        fired = base.dropna().to_numpy()
        print(f"  level {level:>8.0e}  " + "   ".join(row)
              + f"   fired {fired.size}"
              + f"   finite {int(np.isfinite(fired).sum())}")
    print()
    print("(d) 0 < fires < n on every frame, so a constant cannot pass:")
    for name in FRAMES:
        col = j_gator(*FRAMES[name]())
        fires = int(col.notna().sum())
        print(f"  {name:<14} 0 < {fires} < {col.size}: "
              f"{0 < fires < col.size}")


def section_G():
    _head("G guards -- bad prices, and what the one guard buys")
    print("G1 a bad CLOSE empties its own bar and no other. The close is")
    print("    only the divisor, so this is not a recursive effect.")
    print()
    j = 700
    frame = FRAMES["walk"]()
    base = j_gator(*frame)
    print("    `unguarded` is the same module with the guard removed, which")
    print("    is what the guard buys: a reading of +-inf or a sign flip.")
    print()
    unguarded = _mutant(MUTANTS[-1][2], MUTANTS[-1][3])
    for bad in (np.nan, 0.0, -1.0, np.inf, -np.inf, 1e-310):
        h, l, c = frame
        c2 = c.copy()
        c2.iloc[j] = bad
        out = j_gator(h, l, c2)
        raw = unguarded(h, l, c2)
        emptied = int((base.notna() & out.isna()).sum())
        elsewhere = int((base.notna() & out.notna()
                         & (base != out)).sum())
        v = raw.iloc[j]
        print(f"    close[{j}] = {bad!r:<9} emptied {emptied} bar(s) "
              f"(bar {j} itself: {bool(out.isna().iloc[j])}), "
              f"other bars moved {elsewhere}; unguarded reads "
              f"{v if not np.isfinite(v) else round(float(v), 9)}")
    print()
    print("G2 a bad MID is recursive, and the contamination DECAYS. Bars")
    print("    before it are bit-identical; after it, max |rel change| over")
    print("    bars >= J + k (monotone by construction). Run on BOTH legs:")
    print("    `mid` is (high + low) / 2, so a bad low has to behave like a")
    print("    bad high, and that is measured rather than argued:")
    for leg, bad in (("high", np.nan), ("high", np.inf),
                     ("low", np.nan), ("low", np.inf)):
        h, l, c = frame
        if leg == "high":
            h2, l2 = h.copy(), l
            h2.iloc[j] = bad
        else:
            h2, l2 = h, l.copy()
            l2.iloc[j] = bad
        out = j_gator(h2, l2, c)
        pre = base.iloc[:j]
        pre_out = out.iloc[:j]
        m = pre.notna() & pre_out.notna()
        print(f"    {leg}[{j}] = {bad!r}: bars < {j} bit-identical "
              f"{bool((pre[m] == pre_out[m]).all())} ({int(m.sum())} bars), "
              f"emptied {int((base.notna() & out.isna()).sum())}")
        mm = base.notna() & out.notna()
        rel = ((base[mm] - out[mm]).abs()
               / base[mm].abs().where(base[mm].abs() > 0, np.nan))
        bars = np.arange(base.size)[mm.to_numpy()]
        for k in (0, 1, 13, 50, 100, 300):
            tail = rel.to_numpy()[bars >= j + k]
            top = np.nanmax(tail) if tail.size else float("nan")
            print(f"      bars >= {j} + {k:>3}: max |rel| {top:.3e}")
    print()
    print("G3 an infinite HIGH or LOW needs no guard in this module, and")
    print("    that is measured, not assumed: pandas' `_prep_values` turns")
    print("    an inf into a NaN before the `ewm` kernel runs, and `ewm`")
    print("    SKIPS a NaN observation. So an inf bar and a NaN bar are the")
    print("    same column; the only non-finite reading this module can")
    print("    produce is §G5's cross-scale division overflow.")
    print()
    h, l, c = frame

    def _planted(leg, value):
        """The frame with `value` at bar j of `leg`, the other leg intact."""
        if leg == "high":
            x = h.copy()
            x.iloc[j] = value
            return x, l
        x = l.copy()
        x.iloc[j] = value
        return h, x

    for leg in ("high", "low"):
        ref = j_gator(*_planted(leg, np.nan), close=c)
        for label, bad in (("+inf", np.inf), ("-inf", -np.inf)):
            out = j_gator(*_planted(leg, bad), close=c)
            masks, shared, same, d, _ = _agree(out, ref)
            nonfin = int((~np.isfinite(out.to_numpy())).sum())
            print(f"    {leg}[{j}] = {label}: fired "
                  f"{int(out.notna().sum())}, "
                  f"non-finite readings {nonfin - int(out.isna().sum())}, "
                  f"NaN {int(out.isna().sum())}")
            print(f"      vs the same bar as NaN: masks {masks}, bit-equal "
                  f"{same} of {shared}, max |diff| {d:.3e}")
    print()
    print("G4 an all-NaN, an all-zero and an all-negative frame raise")
    print("   nothing:")
    idx = date_range("2020-01-01", periods=60, freq="D")
    for label, value in (("all-NaN", np.nan), ("all-zero", 0.0),
                         ("all-negative", -5.0)):
        s = Series(np.full(60, value), index=idx)
        with np.errstate(all="raise"):
            out = j_gator(s.copy(), s.copy(), s.copy())
        print(f"    {label:<13} fired {int(out.notna().sum())} of 60")
    print()
    print("G5 the one case NOTHING here guards, stated rather than hidden:")
    print("    a frame whose high/low and close live hundreds of orders of")
    print("    magnitude apart is a division that can overflow. It is bad")
    print("    data rather than a price, and the module reports it:")
    h, l, c = _walk(n=60, level=1e+300)
    tiny_close = Series(np.full(60, 1e-300), index=h.index)
    out = j_gator(h, l, tiny_close)
    v = out.to_numpy()
    print(f"    high/low ~1e+300 with close 1e-300: fired "
          f"{int(out.notna().sum())} of 60, of which infinite "
          f"{int(np.isinf(v).sum())}, finite {int(np.isfinite(v).sum())}")
    print("    (the same frame at ONE scale is fine, and §D(c)'s `finite`")
    print("     column is where that is counted: the walk at 1e-6, 1e+6")
    print("     and 1e+100 fires 1,492 bars, all finite.)")


def section_L():
    _head("L what the column READS -- in-fork overlap, synthetic")
    print("Spearman against scale-free fork columns, per frame. These are")
    print("SYNTHETIC and they are not Gate E, whose 687 comparators are the")
    print("engine's. The screen's top comparator `TK_Cross_Age` is one of")
    print("those; its runner-up `ICHI_TK_CROSS_AGE` IS a shipped column of")
    print("this fork (`ichimoku_ml`), so it is measured here -- with")
    print("`ICHI_TK_DIST`, the same Tenkan/Kijun pair as a distance.")
    print()
    print(f"{'frame':<14} {'ao/close':>9} {'natr':>8} {'chop':>8} "
          f"{'QQEs':>8} {'ICHI_AGE':>9} {'ICHI_DIST':>10} {'|gator|':>8}")
    for name in VARYING:
        h, l, c = FRAMES[name]()
        col = j_gator(h, l, c)
        a = ao(h, l) / c
        nt = natr(h, l, c)
        ch = chop(h, l, c)
        q = qqe(c)
        qs = q[[x for x in q.columns if x.startswith("QQEs")][0]]
        ichi = ichimoku_ml(h, l, c)
        print(f"{name:<14} {_spearman(col, a):>9.4f} "
              f"{_spearman(col, nt):>8.4f} {_spearman(col, ch):>8.4f} "
              f"{_spearman(col, qs):>8.4f} "
              f"{_spearman(col, ichi['ICHI_TK_CROSS_AGE']):>9.4f} "
              f"{_spearman(col, ichi['ICHI_TK_DIST']):>10.4f} "
              f"{_spearman(col.abs(), nt):>8.4f}")
    print()
    print("the two spreads the formula is built from, against the shipped")
    print("difference -- what the single column costs. ⚠ Whether the source")
    print("library also returns them apart is NOT visible from this")
    print("worktree; the issue quotes one difference and that is what ships.")
    for name in VARYING:
        h, l, c = FRAMES[name]()
        mid = (h + l) / 2
        jaw = mid.ewm(alpha=1 / JAW[0], adjust=False).mean().shift(JAW[1])
        teeth = mid.ewm(alpha=1 / TEETH[0], adjust=False).mean().shift(TEETH[1])
        lips = mid.ewm(alpha=1 / LIPS[0], adjust=False).mean().shift(LIPS[1])
        jaw_teeth = (jaw - teeth).abs() / c
        teeth_lips = (teeth - lips).abs() / c
        col = j_gator(h, l, c)
        print(f"  {name:<14} rho(col, |jaw-teeth|) "
              f"{_spearman(col, jaw_teeth):>7.4f}  "
              f"rho(col, |teeth-lips|) {_spearman(col, teeth_lips):>7.4f}  "
              f"rho(spread, spread) "
              f"{_spearman(jaw_teeth, teeth_lips):>7.4f}")


def section_W():
    _head("W the dictionary's 150-character cut")
    print("`docs/gen_indicator_dictionary.py`'s `desc()` cuts the docstring's")
    print("first paragraph at 150 characters -- but as")
    print("`d[:150].rsplit(' ', 1)[0]`, which drops the trailing word whole.")
    print("This grows the sentence until that function loses a word, so the")
    print("slack is measured and not counted by hand.")
    print()
    path = Path(__file__).resolve().with_name("gen_indicator_dictionary.py")
    spec = importlib.util.spec_from_file_location("_gendict", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_gendict"] = mod
    try:
        spec.loader.exec_module(mod)
    except SystemExit:
        pass
    title, body = mod.summary(j_gator)
    print(f"  title: {title!r}")
    print(f"  paragraph ({len(body)} chars): {body!r}")
    shown = mod.desc({"desc": body})
    print(f"  as shown ({len(shown)} chars): {shown!r}")
    print(f"  survives whole: {shown == body}")
    slack = 0
    while True:
        probe = body[:-1] + "x" * (slack + 1) + body[-1:]
        if mod.desc({"desc": probe}) != probe:
            break
        slack += 1
        if slack > 300:
            break
    print(f"  characters of slack before the cut bites: {slack}")


def section_Z():
    _head("Z cost -- machine-specific, best of 5")
    print("⚠ The milliseconds are this machine's and this run's. The claims")
    print("are the SHAPE (three `ewm` passes, no window, so linear in bars)")
    print("and the traced peak.")
    print()
    for n in (100_000, 400_000):
        h, l, c = _walk(n=n)
        best = min(timeit.repeat(lambda: j_gator(h, l, c), repeat=5, number=1))
        tracemalloc.start()
        j_gator(h, l, c)
        peak = tracemalloc.get_traced_memory()[1]
        tracemalloc.stop()
        print(f"  {n:>7} bars: best of 5 {best * 1e3:8.2f} ms, "
              f"traced peak {peak / 1e6:6.1f} MB")
    print()
    h, l, c = _walk(n=100_000)
    best_oracle = min(timeit.repeat(lambda: _oracle(h, l, c),
                                    repeat=3, number=1))
    best_mod = min(timeit.repeat(lambda: j_gator(h, l, c),
                                 repeat=3, number=1))
    print(f"  100,000 bars: the Python-recursion oracle costs "
          f"{best_oracle / best_mod:.0f}x the module "
          f"({best_oracle * 1e3:.0f} ms vs {best_mod * 1e3:.1f} ms), which")
    print("  is why §A1's oracle lives here and not in the test module's")
    print("  long frames.")


SECTIONS = {
    "A1": section_A1, "A2": section_A2, "A3": section_A3, "A4": section_A4,
    "B": section_B, "C": section_C, "D": section_D, "G": section_G,
    "L": section_L, "W": section_W, "Z": section_Z,
}


if __name__ == "__main__":
    print(f"pandas {pd.__version__}, numpy {np.__version__}")
    print(f"frames: {N} bars each, level {LEVEL}; column fires on {FIRED} "
          f"(warm-up {WARMUP} = the longest lag)")
    want = [a.upper() for a in sys.argv[1:]] or list(SECTIONS)
    for key in want:
        if key not in SECTIONS:
            raise SystemExit(f"unknown section {key!r}; "
                             f"pick from {list(SECTIONS)}")
        SECTIONS[key]()
