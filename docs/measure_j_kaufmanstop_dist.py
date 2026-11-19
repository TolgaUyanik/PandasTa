# -*- coding: utf-8 -*-
"""J-KAUFMANSTOP-DIST (PandasTa issue #124): the numbers in
`docs/JKaufmanstopDistMeasured.md`, except the ones that receipt names above
its §A1 (pytest's own counts, the tagged-column total, Gate E's universe and
the screen's figures, the web-access line and the asserted bounds).

    python docs/measure_j_kaufmanstop_dist.py        # every section, in order
    python docs/measure_j_kaufmanstop_dist.py A1 D2  # named sections only

One section per gate limb, printed and never derived: the repo's dominant
defect is "a claim written before it was measured", so the RULE is that no
figure may enter the receipt, the module docstring or
`tests/test_j_kaufmanstop_dist.py` except from a section here or from one of
the receipt's named exceptions.

    rng[T]  = high[T] - low[T]
    avg[T]  = mean(rng[T-21..T])                                  SMA 22
    stop[T] = low[T] - 2 * avg[T]
    J_KAUFMANSTOP_DIST[T] = (close[T] - stop[T]) / close[T]

⚠ The millisecond figures of §Z are this machine's and this run's. Nothing
else here is meant to depend on the machine, and
`docs/measure_j_kaufmanstop_dist_cpu.py` re-runs the sections under numpy's
reduced CPU dispatch to show which figures move.
"""
import importlib.util
import platform
import sys
import timeit
from pathlib import Path

import numpy as np
import pandas as pd
from pandas import Series, date_range

from pandas_ta.overlap.sma import sma
from pandas_ta.trend.j_chandelier_dist import j_chandelier_dist
from pandas_ta.trend.j_kaufmanstop_dist import (MIN_BARS, MULT, PERIOD,
                                                j_kaufmanstop_dist)
from pandas_ta.trend.j_safezone_dist import j_safezone_dist
from pandas_ta.utils import non_zero_range
from pandas_ta.volatility.atr import atr
from pandas_ta.volatility.natr import natr
from pandas_ta.volatility.true_range import true_range

N = 1500
LEVEL = 100.0
#: The first bar that can fire on a clean frame, and so the warm-up.
#: ⚠ `MIN_BARS` is PERIOD here, not PERIOD + 1: the SMA's input `high - low`
#: is defined at bar 0, so there is no true-range bar to lose.
WARMUP = MIN_BARS - 1
FIRED = N - WARMUP
#: The blind causality sweep's perturbation points.
OFFSETS = list(range(N - 36, N))


# ------------------------------------------------------------------ frames
# The same builders and seeds as `tests/test_j_kaufmanstop_dist.py`, so a
# number in this file and a number in that one are the same measurement.
# They are `docs/measure_j_chandelier_dist.py`'s, kept identical on purpose:
# two ports measured on the same frames can be compared.


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
    """Tick-rounded prices, the shape real BIST bars have. ⚠ §A4 prints how
    many bars it has with `high == low` at this tick and this seed, because
    whether this frame exercises `non_zero_range`'s epsilon is a
    measurement, not an assumption -- `_tied` is the frame built to."""
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
    """high == low == close on every bar: every range is 0, so the average
    range is 0, the stop IS the low, and the column is exactly 0.0."""
    idx = date_range("2020-01-01", periods=n, freq="h")
    one = Series(np.full(n, level), index=idx)
    return one.copy(), one.copy(), one.copy()


def _rising(n=N, level=LEVEL, step=0.001):
    """A one-way market with no drawdown at all."""
    idx = date_range("2020-01-01", periods=n, freq="h")
    lo = Series(level * (1.0 + step * np.arange(n)), index=idx)
    return lo * 1.004, lo, lo * 1.002


def _tied(seed=29, n=N, level=LEVEL, every=7):
    """A walk with a doji every `every` bars -- `high == low == close`, the
    bar `non_zero_range` exists for and a legitimate zero-range bar here."""
    h, l, c = _walk(seed, n, level)
    doji = np.arange(n) % every == 0
    return h.where(~doji, c), l.where(~doji, c), c


FRAMES = {
    "walk": _walk, "trend": _trend, "range-bound": _range_bound,
    "grid": _grid, "heavy-tailed": _heavy, "jump": _jump, "flat": _flat,
    "rising": _rising, "tied": _tied,
}
NAMES = list(FRAMES)
#: The six frames whose prices vary in both directions.
VARYING = ["walk", "trend", "range-bound", "grid", "heavy-tailed", "jump"]
#: Three of the six, for the sweeps.
SWEPT = ["walk", "trend", "heavy-tailed"]


def _frame(name):
    return FRAMES[name]()


def _col(name):
    return j_kaufmanstop_dist(*_frame(name))


def _scaled(frame, factor):
    high, low, close = frame
    return high * factor, low * factor, close * factor


# ----------------------------------------------------------------- oracles


def _oracle(high, low, close):
    """The issue's formula bar by bar, over plain Python floats, sharing no
    code with the module: a naive 22-term window sum rather than pandas'
    compensated running one, which is the whole of the Gate A gap (§A1)."""
    h = high.to_numpy(dtype=float)
    l = low.to_numpy(dtype=float)
    c = close.to_numpy(dtype=float)
    n = h.size
    nan = float("nan")
    rng = [h[i] - l[i] for i in range(n)]
    out = [nan] * n
    for i in range(PERIOD - 1, n):
        window = rng[i - PERIOD + 1:i + 1]
        if any(x != x for x in window):
            continue
        avg = sum(window) / PERIOD
        stop = l[i] - MULT * avg
        if c[i] == c[i]:
            out[i] = (c[i] - stop) / c[i]
    return Series(out, index=close.index)


def _prototype(high, low, close):
    """`docs/issues/screen/ind_screen_r2.py`, candidate `j_kaufmanstop_dist`,
    retyped from the file this worktree carries a read-only copy of:

        (c - (l - 2 * mean(h - l, 22))) / c

    with `ind_screen.py`'s `mean(x, n) = x.rolling(n).mean()`.

    ⚠ This is the SHIPPED arithmetic, and §A3 measures that rather than
    taking it from the two quotes reading alike. `j_chandelier_dist`'s
    prototype was a different column; this one is not.
    """
    return (close - (low - 2 * (high - low).rolling(22).mean())) / close


def _alt_inline_mean(high, low, close):
    """The shipped column with `sma` replaced by the `rolling` call it
    makes, to price the import rather than trusting it (§A4(a))."""
    avg = (high - low).rolling(PERIOD, min_periods=PERIOD).mean()
    return (close - (low - MULT * avg)) / close


def _alt_non_zero_range(high, low, close):
    """`H - L` through this fork's `non_zero_range`, i.e. with
    `sys.float_info.epsilon` added to EVERY bar of the leg as soon as ONE
    bar has `high == low`. The epsilon is ABSOLUTE, so the result stops
    scaling with the price -- §A4(c) runs Gate D's x8/x64 cells on it."""
    avg = sma(non_zero_range(high, low), length=PERIOD)
    return (close - (low - MULT * avg)) / close


def _alt_true_range(high, low, close):
    """`SMA22` over the TRUE range rather than over `high - low`. The issue
    quotes `SMA22(H - L)`, so this is what the other reading costs."""
    avg = sma(true_range(high=high, low=low, close=close), length=PERIOD)
    return (close - (low - MULT * avg)) / close


def _alt_ema(high, low, close):
    """`EMA22` in place of `SMA22`: the quote says SMA, and this is the
    distance to the nearest smoother a reader might substitute."""
    avg = (high - low).ewm(span=PERIOD, adjust=True,
                           min_periods=PERIOD).mean()
    return (close - (low - MULT * avg)) / close


def _alt_prev_low(high, low, close):
    """The stop off YESTERDAY's low. `L` carries no lag in the issue's
    quote, and this row is what lagging it costs -- it is also one of §B2's
    blind-spot mutants, because it reads no later bar."""
    avg = sma(high - low, length=PERIOD)
    return (close - (low.shift(1) - MULT * avg)) / close


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


def _differing_bars(a, b):
    """How many shared bars differ at all, and the last index that does."""
    m = a.notna() & b.notna()
    diff = a[m].to_numpy() != b[m].to_numpy()
    where = np.flatnonzero(diff)
    positions = np.flatnonzero(m.to_numpy())[where]
    return int(diff.sum()), (int(positions[-1]) if positions.size else -1)


def _talib():
    if importlib.util.find_spec("talib") is None:
        return None
    import talib
    return talib


# ----------------------------------------------------------------- mutants

SOURCE = Path(__file__).resolve().parents[1] / "pandas_ta" / "trend" \
    / "j_kaufmanstop_dist.py"

RNG_LINE = "    rng = hi - lo"
AVG_LINE = "    avg = sma(rng, length=PERIOD)"
STOP_LINE = "    stop = lo - MULT * avg"
DIST_LINE = "    dist = (px - stop) / px"
MASK_LINE = "    dist = dist.where(np.isfinite(dist))"

#: (label, old, new). Edits to the SHIPPED source that make the OUTPUT read
#: a bar LATER than T. ⚠ This chain holds no forward `shift` between a price
#: and the output, so a ONE-bar lead is already a look-ahead.
CAUSALITY_MUTANTS = [
    ("rng-high-lead", RNG_LINE, "    rng = hi.shift(-1) - lo"),
    ("rng-low-lead", RNG_LINE, "    rng = hi - lo.shift(-1)"),
    ("avg-lead", AVG_LINE, "    avg = sma(rng.shift(-1), length=PERIOD)"),
    ("stop-low-lead", STOP_LINE, "    stop = lo.shift(-1) - MULT * avg"),
    ("close-lead", DIST_LINE,
     "    dist = (px.shift(-1) - stop) / px.shift(-1)"),
    ("output-early", MASK_LINE,
     "    dist = dist.where(np.isfinite(dist)).shift(-1)"),
]

#: Edits that LAG a leg: wrong, but reading no bar later than T, so the
#: suffix sweep is blind to all three and Gate A's oracle is not.
BLIND_SPOT_MUTANTS = [
    ("rng-high-lag", RNG_LINE, "    rng = hi.shift(1) - lo"),
    ("avg-lag", AVG_LINE, "    avg = sma(rng, length=PERIOD).shift(1)"),
    ("stop-low-lag", STOP_LINE, "    stop = lo.shift(1) - MULT * avg"),
]

#: The five guards, each removable on its own, so each can be priced.
HI_GUARD_OFF = ("    hi = hi.where(np.isfinite(hi))", "    pass")
LO_GUARD_OFF = ("    lo = lo.where(np.isfinite(lo))", "    pass")
CL_GUARD_OFF = ("    cl = cl.where(np.isfinite(cl))", "    pass")
PX_GUARD_OFF = ("    px = cl.where(cl >= np.finfo(float).tiny)",
                "    px = cl")
FINITE_GUARD_OFF = (MASK_LINE, "    pass")
GUARDS = [("high is finite", HI_GUARD_OFF), ("low is finite", LO_GUARD_OFF),
          ("close is finite", CL_GUARD_OFF),
          ("close is positive+normal", PX_GUARD_OFF),
          ("output is finite", FINITE_GUARD_OFF)]


def _mutant(old, new):
    src = SOURCE.read_text(encoding="utf-8")
    assert src.count(old) == 1, f"{old!r} occurs {src.count(old)} times"
    ns = {}
    exec(compile(src.replace(old, new), "<mutant>", "exec"), ns)
    return ns["j_kaufmanstop_dist"]


def _caught_at(fn, frame, j, factor=1.03):
    """Did perturbing every bar >= j move any bar < j?

    ⚠ `factor` on all three legs is not a global rescale -- the column is
    invariant under one of those, which is Gate D -- it is a rescale of a
    SUFFIX, which moves the range and the low at bar j.
    """
    high, low, close = frame
    f = Series(np.where(np.arange(close.size) >= j, factor, 1.0),
               index=close.index)
    a = fn(high, low, close).iloc[:j]
    b = fn(high * f, low * f, close * f).iloc[:j]
    if not bool((a.isna() == b.isna()).all()):
        return True
    m = a.notna() & b.notna()
    return not bool((a[m].to_numpy() == b[m].to_numpy()).all())


def _sweep(fn, frame, offsets=None):
    return sum(_caught_at(fn, frame, j) for j in (offsets or OFFSETS))


def _first_catch_loudness(fn, frame, factor=1.03):
    """How far the FIRST caught offset moves the prefix. A catch of one bar
    by 1e-16 would be a rounding accident rather than a look-ahead, so the
    size is printed next to the count."""
    high, low, close = frame
    for j in OFFSETS:
        if not _caught_at(fn, frame, j):
            continue
        f = Series(np.where(np.arange(close.size) >= j, factor, 1.0),
                   index=close.index)
        return _abs(fn(high, low, close).iloc[:j],
                    fn(high * f, low * f, close * f).iloc[:j])
    return float("nan")


# ---------------------------------------------------------------- overflow


def _overflow_routes():
    """The three ways a FINITE triple of inputs can still make an infinity,
    in the order they occur in the chain -- the range's subtraction, the
    stop's subtraction, the final division. The labels carry the numbers so
    the table, the prose and the tests cannot drift onto three numberings.

    ⚠ `j_safezone_dist` found that pandas' COMPENSATED `rolling.sum`
    absorbed two of its three routes. There IS a rolling mean in this chain,
    so §G3 measures which routes reach the output rather than assuming
    either way.
    """
    idx = date_range("2020-01-01", periods=120, freq="h")
    rng = np.random.default_rng(5)
    big = float(np.finfo(float).max)
    n = 120
    return [
        # 1. `high - low`: +DBL_MAX against -DBL_MAX. The finite guards do
        #    not demand an ordered bar.
        ("1. range (+max high, -max low)",
         Series(np.full(n, big), index=idx),
         Series(np.full(n, -big), index=idx),
         Series(np.full(n, 1.0), index=idx)),
        # 2. the stop's `lo - 2 * avg`: an average range near DBL_MAX / 2.
        ("2. stop (2 x an average range near DBL_MAX/2)",
         Series(np.full(n, big / 2.0), index=idx),
         Series(np.full(n, -big / 2.0), index=idx),
         Series(np.full(n, 1.0), index=idx)),
        # 3. the DIVISION: a huge stop over a tiny close.
        ("3. division (1e300 / 1e-300)",
         Series(1e300 * (1.0 + 0.01 * rng.random(n)), index=idx),
         Series(-1e300 * (1.0 + 0.01 * rng.random(n)), index=idx),
         Series(np.full(n, 1e-300), index=idx)),
    ]


def _largest_intermediate(high, low, close):
    """The biggest magnitude anywhere in the chain, for a headroom check.

    Printed rather than reasoned about: `j_safezone_dist`'s §D3 margin was
    once a typed "four orders" and was wrong by 202 of them.

    ⚠ EVERY value the chain computes, and the set took two rounds of review
    to close: round 3 found `MULT * avg` and `dist` missing, round 4 found
    the division's numerator `px - stop` and the guarded divisor `px` still
    missing. The ten now here are the three inputs, `rng`, `avg`,
    `MULT * avg`, `stop`, `px`, `px - stop` and `dist` -- which is the whole
    chain, so the universal in §D3's prose is one.
    """
    rng = high - low
    avg = sma(rng, length=PERIOD)
    scaled = MULT * avg
    stop = low - scaled
    px = close.where(close >= np.finfo(float).tiny)
    numerator = px - stop
    dist = numerator / px
    parts = [high, low, close, rng, avg, scaled, stop, px, numerator, dist]
    return max(float(p.abs().max()) for p in parts if int(p.notna().sum()))


# -------------------------------------------------------------- neighbours


def _neighbours(high, low, close):
    """In-fork columns of the same shape, for §L.

    ⚠ A DISCLOSURE, not Gate E: six synthetic frames, not the 89 real ones,
    and these are fork columns (or rules retyped here) rather than the
    engine's 687 comparators. And NOT "columns Gate E cannot see": `natr` is
    the screen's own top comparator, and `Stop_2ATR_pct` and
    `Swing_Range_pct` are named in issue #124's comparator list. Neither the
    engine's `compute_all` nor the `ml_features` manifest is readable from
    this worktree, so what the engine actually computes under those names,
    and whether it routes through this fork, was NOT checked here.
    """
    out = {}
    out["natr:NATR_14"] = natr(high=high, low=low, close=close)
    # RETYPED from the name alone: issue #124 lists `Stop_2ATR_pct` as a
    # comparator at the same 0.8776 as `natr`, and the obvious reading of
    # the name is two ATRs as a percentage of the close -- which is this
    # column's own second term with a Wilder ATR in place of the mean range.
    # ⚠ The engine's definition is not readable here, so this row prices the
    # READING, not the engine's column.
    out["Stop_2ATR_pct (retyped)"] = (
        100.0 * MULT * atr(high=high, low=low, close=close, length=14) / close)
    # RETYPED from `docs/issues/screen/ind_screen_r2.py`'s own candidate
    # `lean_avgrange_14` (`AverageRange.cs: SMA(H - L)`, "/close"), which
    # the 2026-10-24 screen measured against this one at |rho| 0.8646
    # (`cand_pairs_r2.csv`). It is NOT in this fork.
    out["lean_avgrange_14 (retyped)"] = (high - low).rolling(14).mean() / close
    # RETYPED from the name: issue #124's third comparator, at 0.7305.
    out["Swing_Range_pct (retyped)"] = (
        (high.rolling(20).max() - low.rolling(20).min()) / close)
    out["true_range/close (retyped)"] = (
        true_range(high=high, low=low, close=close) / close)
    out["j_chandelier_dist:J_CHANDELIER_DIST_22_3.0"] = j_chandelier_dist(
        high=high, low=low, close=close)
    out["j_safezone_dist:J_SAFEZONE_DIST_22_2.5_3"] = j_safezone_dist(
        low=low, close=close)
    return out


# ------------------------------------------------------------------ output


def _table(rows, head):
    widths = [max(len(str(r[i])) for r in [head] + rows)
              for i in range(len(head))]
    line = "  ".join(str(h).ljust(w) for h, w in zip(head, widths))
    print(line)
    print("  ".join("-" * w for w in widths))
    for row in rows:
        print("  ".join(str(cell).ljust(w) for cell, w in zip(row, widths)))


def _header(key, title):
    print()
    print(f"=== {key}. {title}")


# ----------------------------------------------------------------- sections


def section_env():
    _header("ENV", "environment")
    print(f"python {platform.python_version()} on {platform.platform()}")
    print(f"numpy {np.__version__}, pandas {pd.__version__}")
    talib = _talib()
    print(f"talib {talib.__version__ if talib else 'NOT INSTALLED'}")
    print(f"jesse installed: {importlib.util.find_spec('jesse') is not None}")
    print(f"PERIOD={PERIOD} MULT={MULT} MIN_BARS={MIN_BARS} "
          f"WARMUP={WARMUP} FIRED={FIRED} N={N}")


def section_A1():
    _header("A1", "Gate A -- the issue's formula, spelled independently")
    rows = []
    for name in VARYING:
        frame = _frame(name)
        got, want = j_kaufmanstop_dist(*frame), _oracle(*frame)
        rows.append([name, int(got.notna().sum()),
                     bool((got.isna() == want.isna()).all()),
                     _bit_equal(got, want),
                     f"{_abs(got, want):.3e}", f"{_rel(got, want):.3e}",
                     f"{_spearman(got, want):.6f}"])
    _table(rows, ["frame", "fired", "same NaN mask", "bit-equal",
                  "max |abs|", "max |rel|", "spearman"])
    print()
    print("The gap is pandas' compensated running sum against the oracle's")
    print("naive 22-term one. Measured directly, on the `walk` frame:")
    high, low, close = _frame("walk")
    rng = (high - low).to_numpy(dtype=float)
    pandas_avg = sma(high - low, length=PERIOD)
    naive = np.full(rng.size, np.nan)
    for i in range(PERIOD - 1, rng.size):
        naive[i] = sum(rng[i - PERIOD + 1:i + 1].tolist()) / PERIOD
    naive = Series(naive, index=close.index)
    print(f"  SMA bit-equal to a naive window sum: "
          f"{_bit_equal(pandas_avg, naive)}")
    print(f"  max |abs| between the two means:     "
          f"{_abs(pandas_avg, naive):.3e}")
    print(f"  bars of {int(pandas_avg.notna().sum())} that differ:          "
          f"{_differing_bars(pandas_avg, naive)[0]}")


def section_A2():
    _header("A2", "Gate A -- TA-Lib as the third speller")
    talib = _talib()
    if talib is None:
        print("talib is an optional dev dependency and is NOT installed; "
              "this section is a skip, not a pass")
        return
    rows = []
    for name in VARYING:
        high, low, close = _frame(name)
        want = (close - (low - MULT * Series(
            talib.SMA((high - low).to_numpy(dtype=float), timeperiod=PERIOD),
            index=close.index))) / close
        got = j_kaufmanstop_dist(high, low, close)
        rows.append([name, int(got.notna().sum()), int(want.notna().sum()),
                     bool((got.isna() == want.isna()).all()),
                     _bit_equal(got, want), f"{_abs(got, want):.3e}",
                     f"{_spearman(got, want):.6f}"])
    _table(rows, ["frame", "fired", "talib fired", "same NaN mask",
                  "bit-equal", "max |abs|", "spearman"])
    print()
    high, low, close = _frame("walk")
    ts = Series(talib.SMA((high - low).to_numpy(dtype=float),
                          timeperiod=PERIOD), index=close.index)
    print(f"talib.SMA(high - low, 22) first fires at index "
          f"{int(ts.notna().to_numpy().argmax())}; this module's `sma` at "
          f"{int(sma(high - low, length=PERIOD).notna().to_numpy().argmax())};"
          f" the column at "
          f"{int(j_kaufmanstop_dist(high, low, close).notna().to_numpy().argmax())}")


def section_A3():
    _header("A3", "Gate A -- the screen prototype IS this arithmetic")
    rows = []
    for name in NAMES:
        frame = _frame(name)
        got, proto = j_kaufmanstop_dist(*frame), _prototype(*frame)
        rows.append([name, int(got.notna().sum()), int(proto.notna().sum()),
                     _bit_equal(got, proto), f"{_abs(got, proto):.3e}",
                     f"{_spearman(got, proto):.6f}"])
    _table(rows, ["frame", "fired", "prototype fired", "bit-equal",
                  "max |abs|", "spearman"])
    print()
    print("⚠ Measured, not inferred from the two quotes reading alike. The")
    print("prototype is `docs/issues/screen/ind_screen_r2.py`'s candidate")
    print("`j_kaufmanstop_dist`, and `ind_screen.py`'s `mean(x, n)` is")
    print("`x.rolling(n).mean()` -- the same call `sma` makes. UNLIKE")
    print("`j_chandelier_dist`, whose prototype used an unseeded ATR.")


def section_A4():
    _header("A4", "Gate A -- the other readings are other columns")
    print("(a) the `sma` import against the `rolling` call it makes")
    rows = []
    for name in NAMES:
        frame = _frame(name)
        rows.append([name, _bit_equal(j_kaufmanstop_dist(*frame),
                                      _alt_inline_mean(*frame))])
    _table(rows, ["frame", "bit-equal"])

    print()
    print("(b) the smoother and the series it smooths")
    rows = []
    for label, fn in (("SMA22 over the TRUE range", _alt_true_range),
                      ("EMA22 over high - low", _alt_ema),
                      ("stop off YESTERDAY's low", _alt_prev_low)):
        for name in VARYING:
            frame = _frame(name)
            got, alt = j_kaufmanstop_dist(*frame), fn(*frame)
            differ, last = _differing_bars(got, alt)
            rows.append([label, name, int(got.notna().sum()),
                         int(alt.notna().sum()), differ, last,
                         f"{_abs(got, alt):.3e}",
                         f"{_spearman(got, alt):.6f}"])
    _table(rows, ["reading", "frame", "fired", "alt fired", "differ",
                  "last", "max |abs|", "spearman"])

    print()
    print("(c) `high - low` through `non_zero_range`: the epsilon is")
    print("ABSOLUTE, so the variant stops scaling with the price.")
    rows = []
    for name in NAMES:
        high, low, close = _frame(name)
        rows.append([name, int((high.to_numpy() == low.to_numpy()).sum()),
                     _bit_equal(j_kaufmanstop_dist(high, low, close),
                                _alt_non_zero_range(high, low, close))])
    _table(rows, ["frame", "high == low bars", "bit-equal to the module"])
    print()
    rows = []
    for level in (LEVEL, 1e-6):
        high, low, close = _tied()
        frame = (high, low, close) if level == LEVEL else (
            high / LEVEL * level, low / LEVEL * level, close / LEVEL * level)
        for factor in (8.0, 64.0):
            rows.append([f"tied @ {level:g}", factor,
                         _bit_equal(j_kaufmanstop_dist(*frame),
                                    j_kaufmanstop_dist(*_scaled(frame,
                                                                factor))),
                         _bit_equal(_alt_non_zero_range(*frame),
                                    _alt_non_zero_range(*_scaled(frame,
                                                                 factor)))])
    _table(rows, ["frame", "x", "module bit-identical",
                  "non_zero_range variant bit-identical"])


def section_A5():
    _header("A5", "Gate A -- the warm-up is the SMA window and nothing else")
    high, low, close = _frame("walk")
    col = j_kaufmanstop_dist(high, low, close)
    print(f"first fired index: {int(col.notna().to_numpy().argmax())} "
          f"(WARMUP = {WARMUP} = PERIOD - 1)")
    print(f"MIN_BARS = {MIN_BARS} = PERIOD "
          f"(j_chandelier_dist's is PERIOD + 1: it reads a previous close)")
    rows = []
    for n in (PERIOD - 1, PERIOD, PERIOD + 1, 60):
        frame = (high.iloc[:n], low.iloc[:n], close.iloc[:n])
        out = j_kaufmanstop_dist(*frame)
        rows.append([n, "None" if out is None else int(out.notna().sum()),
                     "None" if out is None else
                     (int(out.notna().to_numpy().argmax())
                      if int(out.notna().sum()) else "-")])
    _table(rows, ["bars", "fired", "first fired index"])
    print()
    print("Nothing in the chain reads a bar before T - 21, so a prefix")
    print("truncation at bar k leaves every bar >= k + 21 untouched:")
    base = j_kaufmanstop_dist(high, low, close)
    cut = j_kaufmanstop_dist(high.iloc[500:], low.iloc[500:],
                             close.iloc[500:])
    tail = base.iloc[500 + WARMUP:]
    print(f"  bars compared: {int(tail.notna().sum())}, bit-equal: "
          f"{_bit_equal(tail, cut.iloc[WARMUP:])}")


def section_B1():
    _header("B1", "Gate B -- the blind future sweep and its mutants")
    rows = [[name, _sweep(j_kaufmanstop_dist, _frame(name)), len(OFFSETS)]
            for name in VARYING]
    _table(rows, ["frame", "module caught at", "offsets"])
    print()
    rows = []
    for label, old, new in CAUSALITY_MUTANTS:
        fn = _mutant(old, new)
        for name in SWEPT:
            frame = _frame(name)
            a, b = j_kaufmanstop_dist(*frame), fn(*frame)
            m = a.notna() & b.notna()
            live = int(m.sum()) > 0 and not bool(
                (a[m].to_numpy() == b[m].to_numpy()).all())
            rows.append([label, name, live, _sweep(fn, frame), len(OFFSETS),
                         f"{_first_catch_loudness(fn, frame):.3e}"])
    _table(rows, ["mutant", "frame", "live", "caught at", "offsets",
                  "first catch moves by"])


def section_B2():
    _header("B2", "Gate B -- the sweep's blind spot, and the oracle on it")
    rows = []
    for label, old, new in BLIND_SPOT_MUTANTS:
        fn = _mutant(old, new)
        for name in ("walk", "heavy-tailed"):
            frame = _frame(name)
            rows.append([label, name, _sweep(fn, frame), len(OFFSETS),
                         _bit_equal(fn(*frame), _oracle(*frame)),
                         f"{_abs(fn(*frame), _oracle(*frame)):.3e}"])
    _table(rows, ["mutant", "frame", "caught by sweep", "offsets",
                  "bit-equal to oracle", "oracle rejects by"])
    print()
    print("All three read only bars <= T, so the SUFFIX sweep cannot see")
    print("them. That is why Gate B here is the sweep AND the oracle.")


def section_C1():
    _header("C1", "Gate C -- reachability on the varying frames")
    rows = []
    pooled = []
    for name in VARYING:
        col = _col(name)
        clean = col.dropna()
        pooled.append(clean.to_numpy())
        rows.append([name, int(col.notna().sum()), N, int(clean.nunique()),
                     f"{float(clean.min()):.6f}", f"{float(clean.max()):.6f}",
                     int((clean < 0.0).sum()), int((clean == 0.0).sum())])
    _table(rows, ["frame", "fired", "bars", "distinct", "min", "max",
                  "< 0", "== 0"])
    allv = np.concatenate(pooled)
    print()
    print(f"pooled over the six: {allv.size} bars, "
          f"{float(allv.min()):.6f} .. {float(allv.max()):.6f}, "
          f"{int((allv < 0).sum())} negative, {int((allv == 0).sum())} "
          f"exactly zero, {int((allv > 0).sum())} positive")
    print("⚠ The column does not change sign on well-formed OHLC:")
    print("`(close - stop)/close = (close - low)/close + 2*avg/close`.")


def section_C2():
    _header("C2", "Gate C -- the frames that are not ordinary")
    rows = []
    for name in ("flat", "rising", "tied"):
        col = _col(name)
        clean = col.dropna()
        rows.append([name, int(col.notna().sum()), int(clean.nunique()),
                     f"{float(clean.min()):.6f}", f"{float(clean.max()):.6f}",
                     int((clean == 0.0).sum())])
    _table(rows, ["frame", "fired", "distinct", "min", "max", "== 0"])
    print()
    print("`flat` is the exception to \"not a constant column\": every range")
    print("is 0, so the stop IS the low and the low IS the close.")


def section_D1():
    _header("D1", "Gate D -- x8 / x64 bit-identical")
    rows = []
    for name in NAMES:
        frame = _frame(name)
        base = j_kaufmanstop_dist(*frame)
        rows.append([name, int(base.notna().sum())]
                    + [_bit_equal(base,
                                  j_kaufmanstop_dist(*_scaled(frame, f)))
                       for f in (8.0, 64.0)])
    _table(rows, ["frame", "fired", "x8", "x64"])


def section_D2():
    _header("D2", "Gate D -- inexact factors, a tolerance")
    rows = []
    worst = 0.0
    for name in VARYING:
        frame = _frame(name)
        base = j_kaufmanstop_dist(*frame)
        row = [name]
        for factor in (10.0, 3.7, 0.1, 1.0000001):
            moved = j_kaufmanstop_dist(*_scaled(frame, factor))
            same_mask = bool((base.isna() == moved.isna()).all())
            rel = _rel(moved, base)
            worst = max(worst, rel)
            row.append(f"{rel:.3e}{'' if same_mask else ' MASK MOVED'}")
        rows.append(row)
    _table(rows, ["frame", "x10", "x3.7", "x0.1", "x1.0000001"])
    print()
    print(f"worst of the {len(VARYING) * 4} cells: {worst:.3e} "
          f"(the test asserts 1e-9)")


def section_D3():
    _header("D3", "Gate D -- extreme price levels, and the headroom")
    print("⚠ EVERY frame at EVERY level, not one frame: round 1 of the")
    print("review found the prose reading 'nine frames at three levels'")
    print("over a table that had run one frame. 9 x 3 x 2 = 54 cells.")
    rows = []
    for name in NAMES:
        high, low, close = _frame(name)
        for level in (1e-6, 1e6, 1e100):
            frame = (high / LEVEL * level, low / LEVEL * level,
                     close / LEVEL * level)
            base = j_kaufmanstop_dist(*frame)
            rows.append([name, f"{level:g}", int(base.notna().sum()),
                         _bit_equal(base,
                                    j_kaufmanstop_dist(*_scaled(frame, 8.0))),
                         _bit_equal(base,
                                    j_kaufmanstop_dist(*_scaled(frame, 64.0))),
                         f"{_largest_intermediate(*frame):.3e}"])
    _table(rows, ["frame", "level", "fired", "x8", "x64",
                  "largest value the chain computes"])
    big = float(np.finfo(float).max)
    print()
    worst = 0.0
    for name in NAMES:
        high, low, close = _frame(name)
        frame = (high / LEVEL * 1e100, low / LEVEL * 1e100,
                 close / LEVEL * 1e100)
        worst = max(worst, _largest_intermediate(*frame))
    print(f"DBL_MAX = {big:.3e}; largest value the chain computes, over all")
    print(f"nine frames at 1e100 = {worst:.3e}, so the headroom is "
          f"{big / worst:.3e}x")
    print("⚠ At a level of 1e-6 the largest value in the chain is the")
    print("dimensionless OUTPUT, ~1.4e-02, because `dist` is a ratio and")
    print("does not shrink with the price; `flat` is the exception, whose")
    print("output is exactly 0.0.")


def section_D4():
    _header("D4", "Gate D -- 0 < fires < n, and a level shift moves it")
    rows = []
    for name in NAMES:
        high, low, close = _frame(name)
        base = j_kaufmanstop_dist(high, low, close)
        moved = j_kaufmanstop_dist(high + 10.0, low + 10.0, close + 10.0)
        m = base.notna() & moved.notna()
        rows.append([name, int(base.notna().sum()), len(base),
                     0 < int(base.notna().sum()) < len(base),
                     int(m.sum()), int((base[m] != moved[m]).sum())])
    _table(rows, ["frame", "fired", "n", "0 < fires < n", "shared",
                  "moved by +10"])


def section_E():
    _header("E", "Gate E -- pending, and what the screen measured")
    print("Gate E: pending, run by issue-solver after this session.")
    print()
    print("The 2026-10-24 screen, round 2, measured the PROTOTYPE -- which")
    print("§A3 measures BIT-EQUAL to this module on all nine frames, so")
    print("these are this arithmetic's figures on data this worktree cannot")
    print("read. Quoted from `docs/issues/screen/candidates_r2.csv` and")
    print("`fork_overlap_r2.csv` (both gitignored, owner's machine):")
    print("  gate_e_max_rho   0.8776182137043917 vs natr (compute_all)")
    print("  gate_e_n         396980")
    print("  gate_e_perframe  0.8600682984579084")
    print("  gate_e_verdict   DISCLOSE_GAP")
    print("  fork_max_rho     0.8611 vs natr:NATR_14 (per-frame 0.8547)")
    print("  cand_pairs_r2    0.8646 vs lean_avgrange_14 (another candidate)")
    print("  sanity_r2        finite_min 0.9750593824228029, nunique_min 821,")
    print("                   causal 0.0, px8 0.0, vx8 0.0 (6 frames)")
    print()
    print("No ledger row exists yet; the receipt session records it.")


def section_G1():
    _header("G1", "the guards are no-ops on an ordinary frame")
    rows = []
    for label, edit in GUARDS:
        fn = _mutant(*edit)
        rows.append([label] + [_bit_equal(j_kaufmanstop_dist(*_frame(n)),
                                          fn(*_frame(n))) for n in NAMES])
    _table(rows, ["guard off"] + NAMES)


def section_G2():
    _header("G2", "each guard priced on a frame built to reach it")
    high, low, close = _frame("walk")
    rows = []
    for leg, label, edit in (("high", "high is finite", HI_GUARD_OFF),
                             ("low", "low is finite", LO_GUARD_OFF),
                             ("close", "close is finite", CL_GUARD_OFF)):
        bare = _mutant(*edit)
        for value in (np.inf, -np.inf, np.nan):
            h, l, c = high.copy(), low.copy(), close.copy()
            {"high": h, "low": l, "close": c}[leg].iloc[700] = value
            with np.errstate(all="ignore"):
                ship, naked = j_kaufmanstop_dist(h, l, c), bare(h, l, c)
            differ, last = _differing_bars(ship, naked)
            rows.append([label, f"{value}", int(ship.notna().sum()),
                         int(naked.notna().sum()),
                         int(np.isinf(ship).sum()),
                         int(np.isinf(naked).sum()),
                         _bit_equal(ship, naked), differ,
                         f"{_abs(ship, naked):.3e}"])
    _table(rows, ["guard", "planted", "fired", "fired w/o", "inf",
                  "inf w/o", "bit-equal", "differ", "max |abs|"])
    print(f"(frame length {len(close)}, fired on a clean frame {FIRED})")

    print()
    print("the close-is-positive-and-normal guard, planted at bar 700:")
    rows = []
    bare = _mutant(*PX_GUARD_OFF)
    base = j_kaufmanstop_dist(high, low, close)
    for bad in (0.0, -50.0, 5e-310):
        cl = close.copy()
        cl.iloc[700] = bad
        with np.errstate(all="ignore"):
            ship, naked = j_kaufmanstop_dist(high, low, cl), bare(high, low, cl)
        gone = np.flatnonzero((base.notna() & ship.isna()).to_numpy())
        rows.append([f"{bad:g}", gone.tolist(), int(ship.notna().sum()),
                     int(naked.notna().sum()),
                     "-" if ship.notna().iloc[700] else
                     (f"{float(naked.iloc[700]):.3e}"
                      if bool(naked.notna().iloc[700]) else "NaN"),
                     int(np.isinf(naked).sum())])
    _table(rows, ["close", "bars blanked", "fired", "fired w/o",
                  "value w/o the guard at 700", "inf w/o"])


def section_G3():
    _header("G3", "three routes to an infinity on FINITE inputs")
    rows = []
    bare = _mutant(*FINITE_GUARD_OFF)
    for label, h, l, c in _overflow_routes():
        with np.errstate(all="ignore"):
            ship, naked = j_kaufmanstop_dist(h, l, c), bare(h, l, c)
        rows.append([label, len(c), int(ship.notna().sum()),
                     int(np.isinf(ship).sum()), int(naked.notna().sum()),
                     int(np.isinf(naked).sum())])
    _table(rows, ["route", "bars", "fired", "inf", "fired w/o the mask",
                  "inf w/o the mask"])
    print()
    print("what a pandas rolling mean does with one +inf observation")
    print("(81 bars of 1.0 with a +inf at bar 40):")
    with np.errstate(all="ignore"):
        inf_in = sma(Series([1.0] * 40 + [np.inf] + [1.0] * 40),
                     length=PERIOD)
        big_in = sma(Series([1.0] * 40 + [float(np.finfo(float).max)]
                            + [1.0] * 40), length=PERIOD)
    print(f"  +inf:    fired {int(inf_in.notna().sum())}, "
          f"inf {int(np.isinf(inf_in).sum())}, "
          f"bar 40 = {float(inf_in.iloc[40])}, "
          f"bar 61 = {float(inf_in.iloc[61])}")
    print(f"  DBL_MAX: fired {int(big_in.notna().sum())}, "
          f"inf {int(np.isinf(big_in).sum())}, "
          f"bar 40 = {float(big_in.iloc[40]):.3e}")


def section_G4():
    _header("G4", "which bars a bad price empties, leg by leg")
    high, low, close = _frame("walk")
    base = j_kaufmanstop_dist(high, low, close)
    rows = []
    print("⚠ Plant points 5 and 1495 are here because")
    print("'blanks exactly bars T .. T+21' has TWO boundaries: a bar inside")
    print("the warm-up was never fired, and T + 21 past the last bar cannot")
    print("be blanked. Round 1 of the review found the claim stated without")
    print("the right edge; round 2 found the left edge still missing. The")
    print(f"rule is max(T, {WARMUP}) .. min(T+{PERIOD - 1}, n-1).")
    for leg in ("high", "low", "close"):
        for value in (np.nan, np.inf, -np.inf):
            for j in (5, 100, 700, 1100, 1495):
                h, l, c = high.copy(), low.copy(), close.copy()
                {"high": h, "low": l, "close": c}[leg].iloc[j] = value
                with np.errstate(all="ignore"):
                    col = j_kaufmanstop_dist(h, l, c)
                gone = np.flatnonzero((base.notna() & col.isna()).to_numpy())
                differ, last = _differing_bars(base.iloc[j + 1:],
                                               col.iloc[j + 1:])
                rows.append([leg, f"{value}", j, len(gone),
                             (f"{gone[0]} .. {gone[-1]}" if gone.size
                              else "-"),
                             _bit_equal(base.iloc[:j], col.iloc[:j]),
                             len(base) - j - 1, differ])
    _table(rows, ["leg", "planted", "at", "blanked", "range",
                  "prefix bit-equal", "later bars", "later bars moved"])
    print()
    print(f"(frame length {len(close)}; PERIOD = {PERIOD})")


def section_G5():
    _header("G5", "would the input guards bite if pandas STOPPED absorbing?")
    print("Round 1 of the review refuted a claim this section replaces. The")
    print("claim was that the §G2 bit-equality pins pandas' absorption in")
    print("both directions -- that an upgrade propagating an infinite")
    print("observation instead of NaN-ing the window would fail there too.")
    print("It would not, and the reason is the FINAL MASK, so the question")
    print("is run here instead of argued.")
    print()
    print("`sma` is rebound, by editing the import line of the shipped")
    print("source, to a mean that PROPAGATES an infinity -- a numpy window")
    print("mean with no `rolling` in it, for the reason the premise table")
    print("below prints -- and each input guard is then removed on top of")
    print("that. One bad value at bar 700 of a `walk`.")
    # ⚠ NOT `rolling(...).apply(np.mean, raw=True)`, which is what round 2
    # of the review proposed and what an earlier draft of this section used.
    # That does NOT propagate, and the premise table below prints that
    # rather than asserting it: the three `rolling` aggregations it measures
    # all read NaN at a planted `+inf` where a numpy window mean reads
    # `inf`, which places the conversion before the aggregation. So the way
    # to model a pandas that stopped absorbing is to leave `rolling` out,
    # which is what this does. pandas' source is outside this worktree and
    # is not read, so the mechanism is not named here.
    propagating = (
        "from pandas_ta.overlap.sma import sma",
        "def sma(close, length=None, **kwargs):\n"
        "    import numpy as _np\n"
        "    from pandas import Series as _S\n"
        "    _a = close.to_numpy(dtype=float)\n"
        "    _o = _np.full(_a.size, _np.nan)\n"
        "    for _i in range(length - 1, _a.size):\n"
        "        _o[_i] = _a[_i - length + 1:_i + 1].mean()\n"
        "    return _S(_o, index=close.index)")
    print()
    # The rebinding on its own: does the propagating mean even change the
    # shipped column on a clean frame, and does it still blank a bad bar?
    rows = []
    for name in ("walk", "tied"):
        frame = _frame(name)
        with np.errstate(all="ignore"):
            ship, prop = (j_kaufmanstop_dist(*frame),
                          _mutant(*propagating)(*frame))
        rows.append([f"{name} (clean)", int(ship.notna().sum()),
                     int(prop.notna().sum()), _bit_equal(ship, prop),
                     f"{_abs(ship, prop):.3e}"])
    _table(rows, ["frame", "fired", "fired w/ propagating mean", "bit-equal",
                  "max |abs|"])
    print()
    rows = []
    src = SOURCE.read_text(encoding="utf-8")
    high, low, close = _frame("walk")
    for leg, label, edit in (("high", "high is finite", HI_GUARD_OFF),
                             ("low", "low is finite", LO_GUARD_OFF),
                             ("close", "close is finite", CL_GUARD_OFF)):
        for value in (np.inf, -np.inf):
            h, l, c = high.copy(), low.copy(), close.copy()
            {"high": h, "low": l, "close": c}[leg].iloc[700] = value
            ns_on, ns_off = {}, {}
            on = src.replace(*propagating)
            assert on != src
            off = on.replace(*edit)
            assert off != on
            exec(compile(on, "<prop>", "exec"), ns_on)
            exec(compile(off, "<prop+guard-off>", "exec"), ns_off)
            with np.errstate(all="ignore"):
                a = ns_on["j_kaufmanstop_dist"](h, l, c)
                b = ns_off["j_kaufmanstop_dist"](h, l, c)
            rows.append([label, f"{value}", int(a.notna().sum()),
                         int(b.notna().sum()), int(np.isinf(a).sum()),
                         int(np.isinf(b).sum()), _bit_equal(a, b),
                         _differing_bars(a, b)[0]])
    _table(rows, ["guard", "planted", "fired", "fired w/o the guard", "inf",
                  "inf w/o", "bit-equal", "differ"])
    print()
    print("So the §G2 bit-equality does NOT pin pandas' absorption: the")
    print("final mask converts the propagated infinity to a NaN at exactly")
    print("the bars the guard already blanks.")
    print()
    print("⚠ THE PREMISE OF THIS SECTION, PRINTED RATHER THAN ASSUMED.")
    print("Round 2 of the review pointed out that the six cells above read")
    print("the same whether the rebound mean propagates or absorbs, so they")
    print("cannot establish that it propagates. It also proposed")
    print("`rolling(...).apply(np.mean, raw=True)` as the propagating mean,")
    print("and THAT IS REFUTED HERE. ⚠ What is measured is the BEHAVIOUR of")
    print("three aggregations, not pandas' source, which this worktree")
    print("cannot read: all three read NaN where a numpy window mean reads")
    print("inf, which puts the conversion before the window function rather")
    print("than in the mean. On the `walk` with a +inf high planted at bar")
    print("700 and the high guard removed:")
    rows = []
    h, l, c = high.copy(), low.copy(), close.copy()
    h.iloc[700] = np.inf
    ns_tmp = {}
    exec(compile(SOURCE.read_text(encoding="utf-8").replace(*propagating)
                 .split("def j_kaufmanstop_dist")[0], "<means>", "exec"),
         ns_tmp)
    means = (
        ("shipped `sma` (rolling)", lambda s: sma(s, length=PERIOD)),
        ("rolling(...).apply(np.mean)",
         lambda s: s.rolling(PERIOD, min_periods=PERIOD)
         .apply(np.mean, raw=True)),
        ("rolling(...).max()",
         lambda s: s.rolling(PERIOD, min_periods=PERIOD).max()),
        ("§G5's numpy window mean", lambda s: ns_tmp["sma"](s, PERIOD)),
    )
    for label, fn in means:
        with np.errstate(all="ignore"):
            avg = fn(h - l)
        rows.append([label, f"{float(avg.iloc[700])}",
                     int(np.isinf(avg).sum()), int(avg.notna().sum())])
    _table(rows, ["mean over high - low", "value at bar 700", "inf bars",
                  "fired"])
    print()
    print("Only the window mean that leaves `rolling` out propagates, so")
    print("that is what the tables above and below are built on.")
    print()
    print("⚠ AND WHICH TESTS SUCH AN UPGRADE WOULD FAIL -- two, not one,")
    print("which is round 2's MAJOR. §G3's route 1 ships 0 infinities")
    print("WITHOUT the final mask today, and that zero is the absorption")
    print("rather than anything this module does. The three routes under")
    print("the rebinding:")
    rows = []
    src_prop = SOURCE.read_text(encoding="utf-8").replace(*propagating)
    ns_prop, ns_prop_bare = {}, {}
    exec(compile(src_prop, "<prop>", "exec"), ns_prop)
    exec(compile(src_prop.replace(*FINITE_GUARD_OFF), "<prop-nomask>", "exec"),
         ns_prop_bare)
    for label, hh, ll, cc in _overflow_routes():
        with np.errstate(all="ignore"):
            ship = ns_prop["j_kaufmanstop_dist"](hh, ll, cc)
            bare = ns_prop_bare["j_kaufmanstop_dist"](hh, ll, cc)
        rows.append([label, len(cc), int(ship.notna().sum()),
                     int(np.isinf(ship).sum()), int(bare.notna().sum()),
                     int(np.isinf(bare).sum())])
    _table(rows, ["route (propagating mean)", "bars", "fired", "inf",
                  "fired w/o the mask", "inf w/o the mask"])
    print()
    print("So `test_route_1_never_reaches_the_output`, which asserts 0")
    print("infinities without the mask, would fail too -- and §G3's route-1")
    print("row would move. The final mask still holds the output clean in")
    print("all three routes, which is the thing that matters for a shipped")
    print("column.")


def section_L():
    _header("L", "in-fork overlap -- A DISCLOSURE, NOT GATE E")
    print("Six SYNTHETIC frames, fork columns and retyped rules; Gate E is")
    print("89 real BIST frames against 687 engine comparators. ⚠ `natr` is")
    print("the screen's own top comparator, so this section previews the")
    print("gate rather than being blind to it.")
    print()
    cols = {}
    for name in VARYING:
        frame = _frame(name)
        mine = j_kaufmanstop_dist(*frame)
        for label, other in _neighbours(*frame).items():
            cols.setdefault(label, []).append(abs(_spearman(mine, other)))
    rows = []
    for label, vals in cols.items():
        arr = np.array([v for v in vals if v == v])
        rows.append([label, len(arr), f"{float(np.median(arr)):.4f}",
                     f"{float(arr.min()):.4f}", f"{float(arr.max()):.4f}"])
    rows.sort(key=lambda r: -float(r[2]))
    _table(rows, ["in-fork column", "frames", "per-frame median |rho|",
                  "min", "max"])
    print()
    print("The screen's own fork figure for `natr:NATR_14` was 0.8611")
    print("(per-frame max median 0.8547) on 12 real frames; the synthetic")
    print("figure above is the number to compare it with, and it is far")
    print("LOWER rather than higher -- the reverse of what")
    print("`j_chandelier_dist` found, where synthetic read 0.0575 HIGH.")
    print("The table below is what this section can say about why, and it")
    print("is a measurement of the SYNTHETIC side only: the column is")
    print("`(close - low)/close + 2*avg/close`, and on these frames the")
    print("wick term carries more of it than the range term does -- the")
    print("two standard deviations are within a factor of 0.51 .. 0.70 and")
    print("the column's own |rho| is 0.857 .. 0.920 against the wick")
    print("against 0.572 .. 0.620 against the range term -- because")
    print("`_ohlc` draws the relative range i.i.d. per bar, so its 22-bar")
    print("mean is far smoother than real volatility. ⚠ That real ranges")
    print("vary more is NOT measured here: no real frame is readable from")
    print("this worktree. What is measured is that these six frames cannot")
    print("stand in for Gate E in either direction, and the port's own run")
    print("is the only thing that decides the band.")
    print()
    rows = []
    for name in VARYING + ["tied"]:
        high, low, close = _frame(name)
        mine = j_kaufmanstop_dist(high, low, close)
        wick = (close - low) / close
        rngterm = MULT * sma(high - low, length=PERIOD) / close
        rows.append([name,
                     f"{float(wick.dropna().std()):.3e}",
                     f"{float(rngterm.dropna().std()):.3e}",
                     f"{float(rngterm.dropna().std() / wick.dropna().std()):.4f}",
                     f"{abs(_spearman(mine, wick)):.4f}",
                     f"{abs(_spearman(mine, rngterm)):.4f}"])
    _table(rows, ["frame", "std (close-low)/close", "std 2*avg/close",
                  "ratio", "|rho| vs wick", "|rho| vs range term"])


def section_Z():
    _header("Z", "cost -- THIS MACHINE AND THIS RUN ONLY")
    high, low, close = _frame("walk")
    for label, fn in (("j_kaufmanstop_dist", j_kaufmanstop_dist),
                      ("j_chandelier_dist", j_chandelier_dist)):
        t = timeit.timeit(lambda: fn(high, low, close), number=50) / 50
        print(f"{label:<22} {1000 * t:7.3f} ms per call on {N} bars")


SECTIONS = {
    "ENV": section_env,
    "A1": section_A1, "A2": section_A2, "A3": section_A3, "A4": section_A4,
    "A5": section_A5,
    "B1": section_B1, "B2": section_B2,
    "C1": section_C1, "C2": section_C2,
    "D1": section_D1, "D2": section_D2, "D3": section_D3, "D4": section_D4,
    "E": section_E,
    "G1": section_G1, "G2": section_G2, "G3": section_G3, "G4": section_G4,
    "G5": section_G5,
    "L": section_L,
    "Z": section_Z,
}


if __name__ == "__main__":
    want = [a.upper() for a in sys.argv[1:]] or list(SECTIONS)
    for key in want:
        if key not in SECTIONS:
            raise SystemExit(f"unknown section {key!r}; "
                             f"pick from {list(SECTIONS)}")
    for key in want:
        SECTIONS[key]()
