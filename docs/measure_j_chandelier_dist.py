# -*- coding: utf-8 -*-
"""J-CHANDELIER-DIST-22 (PandasTa issue #122): the numbers in
`docs/JChandelierDistMeasured.md`, except the six that receipt names above
its §A1 (pytest's own counts, the tagged-column total, Gate E's universe
and the screen's figures, the web-access line, `CLAUDE.md`'s MAMA figure
and the asserted bounds).

    python docs/measure_j_chandelier_dist.py           # every section, in order
    python docs/measure_j_chandelier_dist.py A1 D      # named sections only

One section per gate limb, printed and never derived: the repo's dominant
defect is "a claim written before it was measured", so the RULE is that no
figure may enter the receipt, the module docstring or
`tests/test_j_chandelier_dist.py` except from a section here or from one of
the receipt's six named exceptions.

    tr[T]   = max(high - low, |high - close[T-1]|, |low - close[T-1]|)
    atr[T]  = Wilder(tr, 22), seeded with mean(tr[1..22])
    stop[T] = max(high[T-21..T]) - 3 * atr[T]
    J_CHANDELIER_DIST[T] = (close[T] - stop[T]) / close[T]

⚠ The millisecond figures of §Z are this machine's and this run's. Nothing
else here is meant to depend on the machine, and
`docs/measure_j_chandelier_dist_cpu.py` re-runs the sections under numpy's
reduced CPU dispatch to show which figures move.
"""
import importlib.util
import platform
import sys
import timeit
from pathlib import Path

import numpy as np
import pandas as pd
from pandas import DataFrame, Series, date_range

from pandas_ta.momentum.bias import bias
from pandas_ta.overlap.ichimoku_ml import ichimoku_ml
from pandas_ta.overlap.rma import rma
from pandas_ta.overlap.wilder_rma import wilder_rma
from pandas_ta.trend.chop import chop
from pandas_ta.trend.cksp import cksp
from pandas_ta.trend.j_chandelier_dist import (MIN_BARS, MULT, PERIOD,
                                               j_chandelier_dist)
from pandas_ta.trend.j_safezone_dist import j_safezone_dist
from pandas_ta.trend.vstop import vstop
from pandas_ta.volatility.natr import natr
from pandas_ta.volatility.true_range import true_range

N = 1500
LEVEL = 100.0
#: The first bar that can fire on a clean frame, and so the warm-up.
#: `MIN_BARS` is that index plus one.
WARMUP = MIN_BARS - 1
FIRED = N - WARMUP
#: The blind causality sweep's perturbation points.
OFFSETS = list(range(N - 36, N))


# ------------------------------------------------------------------ frames
# The same builders and seeds as `tests/test_j_chandelier_dist.py`, so a
# number in this file and a number in that one are the same measurement.
# `walk` .. `rising` are `docs/measure_j_safezone_dist.py`'s, kept identical
# on purpose: two ports measured on the same frames can be compared.


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
    """Tick-rounded prices, the shape real BIST bars have. ⚠ Measured (§A4):
    it has 0 bars with `high == low` at this tick and this seed, so it is
    NOT the frame that exercises `non_zero_range`'s epsilon -- `_tied` is.
    """
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
    """high == low == close on every bar: every true range is 0, so the ATR
    is 0, the stop IS the highest high, and the column is exactly 0.0."""
    idx = date_range("2020-01-01", periods=n, freq="h")
    one = Series(np.full(n, level), index=idx)
    return one.copy(), one.copy(), one.copy()


def _rising(n=N, level=LEVEL, step=0.001):
    """A one-way market: strictly rising lows, so the 22-bar high is always
    this bar's own."""
    idx = date_range("2020-01-01", periods=n, freq="h")
    lo = Series(level * (1.0 + step * np.arange(n)), index=idx)
    return lo * 1.004, lo, lo * 1.002


def _tied(seed=29, n=N, level=LEVEL, every=7):
    """A walk with a DOJI every `every` bars -- `high == low == close`, the
    bar `non_zero_range` exists for -- at whatever level is asked for.

    The epsilon it adds is ABSOLUTE, so what it costs depends on the price:
    at `LEVEL` = 100 the three epsilons vanish into the stop's last bits
    and §A4(e) measures the variant BIT-EQUAL to this module; at 1e-6 they
    do not, and the variant stops being scale-free. Both halves are
    measured rather than argued.
    """
    h, l, c = _walk(seed, n, level)
    doji = np.arange(n) % every == 0
    h = h.where(~doji, c)
    l = l.where(~doji, c)
    return h, l, c


FRAMES = {
    "walk": _walk, "trend": _trend, "range-bound": _range_bound,
    "grid": _grid, "heavy-tailed": _heavy, "jump": _jump, "flat": _flat,
    "rising": _rising, "tied": _tied,
}
#: The six frames whose prices vary in both directions. `flat` and `rising`
#: are degenerate and are reported on their own in §C2.
VARYING = ["walk", "trend", "range-bound", "grid", "heavy-tailed", "jump"]
#: Three of the six, for the sweeps: 6 mutants x 36 offsets x 2 calls each.
SWEPT = ["walk", "trend", "heavy-tailed"]


def _frame(name):
    return FRAMES[name]()


def _col(name):
    return j_chandelier_dist(*_frame(name))


def _scaled(frame, factor):
    high, low, close = frame
    return high * factor, low * factor, close * factor


# ----------------------------------------------------------------- oracles


def _oracle(high, low, close):
    """The issue's formula, bar by bar, sharing no code with the module.

    Its own true-range loop, its own SMA seed over a plain Python slice, its
    own Wilder recursion over Python floats, its own 22-bar running maximum.
    `sum(slice) / 22` and pandas' `.mean()` are not the same arithmetic, so
    this is a 1e-12 check rather than a bit-equality one -- §A1 reports what
    it actually costs.

    ⚠ This is TA-Lib's rule exactly: true range undefined at bar 0, the
    seed is the mean of true ranges 1 .. PERIOD, and a NaN anywhere
    poisons everything after it. The module's `wilder_rma` SLIDES its seed
    past an early NaN and CARRIES its state across a late one, which is a
    deliberate divergence of the helper; §G1 measures where the two part
    company. On a clean frame they cannot differ, which is why the oracle
    is run on clean frames only.
    """
    h = high.to_numpy(dtype=float)
    l = low.to_numpy(dtype=float)
    c = close.to_numpy(dtype=float)
    n = h.size
    nan = float("nan")

    tr = [nan] * n
    for i in range(1, n):
        tr[i] = max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1]))

    atr = [nan] * n
    if n > PERIOD:
        atr[PERIOD] = sum(tr[1:PERIOD + 1]) / PERIOD
        for i in range(PERIOD + 1, n):
            atr[i] = (tr[i] - atr[i - 1]) / PERIOD + atr[i - 1]

    hh = [nan] * n
    for i in range(PERIOD - 1, n):
        window = h[i - PERIOD + 1:i + 1]
        if not np.isnan(window).any():
            hh[i] = max(window)

    out = [nan] * n
    for i in range(n):
        if hh[i] == hh[i] and atr[i] == atr[i]:
            out[i] = (c[i] - (hh[i] - MULT * atr[i])) / c[i]
    return Series(out, index=close.index)


def _oracle_wilder_longhand(high, low, close):
    """The same recursion written the OTHER way round --
    `alpha*tr + (1-alpha)*atr[-1]` instead of `atr[-1] + (tr - atr[-1])/n`.

    Algebraically identical, not bit-identical, and printed because
    `CLAUDE.md` records a TALIB-1 case where exactly this kind of
    re-association moved MAMA by 1.1e-2. §A1 reports the cost here.
    """
    h = high.to_numpy(dtype=float)
    l = low.to_numpy(dtype=float)
    c = close.to_numpy(dtype=float)
    n = h.size
    nan = float("nan")
    alpha = 1.0 / PERIOD
    tr = [nan] * n
    for i in range(1, n):
        tr[i] = max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1]))
    atr = [nan] * n
    if n > PERIOD:
        atr[PERIOD] = sum(tr[1:PERIOD + 1]) / PERIOD
        for i in range(PERIOD + 1, n):
            atr[i] = alpha * tr[i] + (1.0 - alpha) * atr[i - 1]
    hh = [nan] * n
    for i in range(PERIOD - 1, n):
        window = h[i - PERIOD + 1:i + 1]
        if not np.isnan(window).any():
            hh[i] = max(window)
    out = [nan] * n
    for i in range(n):
        if hh[i] == hh[i] and atr[i] == atr[i]:
            out[i] = (c[i] - (hh[i] - MULT * atr[i])) / c[i]
    return Series(out, index=close.index)


def _talib():
    """`talib` is a DEV-ONLY dependency (`setup.py`, `extras_require`) and
    TALIB-1's Gate A oracle. It is used here because `MAX` and `ATR` are
    TA-Lib's spelling of the issue's two operators and because a bare
    "ATR" conventionally means TA-Lib's Wilder ATR -- ⚠ NOT as a stand-in
    for jesse's code, which is not installed here and about which this
    file claims nothing. Returns None when talib is absent, and the caller
    says so out loud rather than passing silently."""
    if importlib.util.find_spec("talib") is None:
        return None
    import talib
    return talib


def _talib_column(high, low, close):
    lib = _talib()
    if lib is None:
        return None
    h = high.to_numpy(dtype=float)
    l = low.to_numpy(dtype=float)
    c = close.to_numpy(dtype=float)
    stop = lib.MAX(h, PERIOD) - MULT * lib.ATR(h, l, c, PERIOD)
    return Series((c - stop) / c, index=close.index)


def _prototype(high, low, close):
    """`docs/issues/screen/ind_screen_r2.py`, candidate
    `j_chandelier_dist_22`, retyped (that file is gitignored, so it is on
    the owner's machine only). `atr_wilder` and `tsmax` are
    `ind_screen.py`'s:

        def atr_wilder(h, l, c, n):
            tr = pd.concat([h - l, (h - c.shift()).abs(),
                            (l - c.shift()).abs()], axis=1).max(axis=1)
            return tr.ewm(alpha=1 / n, adjust=False).mean()
        def tsmax(x, n): return x.rolling(n).max()

        (c - (tsmax(h, 22) - 3 * atr_wilder(h, l, c, 22))) / c

    ⚠ This is NOT the shipped column. The prototype's ATR recurses from
    bar 0 with no SMA seed; the reading this port takes -- Wilder 1978, and
    what `talib.ATR` computes, both run in §A2 and §A5 -- is seeded with the
    mean of the first 22 true ranges. §A3 measures how far apart they are
    and for how long.
    """
    prev = close.shift()
    tr = pd.concat([high - low, (high - prev).abs(), (low - prev).abs()],
                   axis=1).max(axis=1)
    atr = tr.ewm(alpha=1.0 / PERIOD, adjust=False).mean()
    return (close - (high.rolling(PERIOD).max() - MULT * atr)) / close


def _alt_fork_rma(high, low, close):
    """This fork's `rma` -- pandas' `ewm(adjust=True, min_periods=22)` --
    over the same true range. The default `atr(mamode="rma")` uses it, and
    `pandas_ta/overlap/rma.py` says in its own docstring that it is NOT
    Wilder's."""
    tr = _module_true_range(high, low, close)
    return (close - (high.rolling(PERIOD, min_periods=PERIOD).max()
                     - MULT * rma(tr, length=PERIOD))) / close


def _alt_sma(high, low, close):
    """`SMA(tr, 22)` instead of Wilder's: `talib.ATR` is Wilder's (run in
    §A2 and §A5), but the book implementation of `cksp` uses an SMA, so the
    reading is not absurd."""
    tr = _module_true_range(high, low, close)
    return (close - (high.rolling(PERIOD, min_periods=PERIOD).max()
                     - MULT * tr.rolling(PERIOD, min_periods=PERIOD).mean())
            ) / close


def _alt_hh_close(high, low, close):
    """`HH22` over the CLOSE rather than the high.

    `HH` names the highest HIGH in every statement of the Chandelier Exit
    this session can read -- the issue's `HH22`, and the screen prototype's
    `tsmax(h, 22)`. ⚠ What jesse's and Skender's code pass is NOT checkable
    here and is not claimed. This row is what the other reading costs.
    """
    tr = _module_true_range(high, low, close)
    return (close - (close.rolling(PERIOD, min_periods=PERIOD).max()
                     - MULT * wilder_rma(tr, length=PERIOD))) / close


def _alt_fork_true_range(high, low, close):
    """The same column with `pandas_ta.volatility.true_range` in place of
    this module's own -- i.e. with `non_zero_range`'s epsilon.

    The one difference that matters is not the epsilon's size, it is that
    the epsilon is ABSOLUTE: `non_zero_range` adds `sys.float_info.epsilon`
    to EVERY bar of the `high - low` leg as soon as ONE bar has
    `high == low`, so the result no longer scales with the price. §A4(e)
    measures the divergence AND runs Gate D's x8/x64 cells on this
    variant.
    """
    tr = true_range(high=high, low=low, close=close)
    return (close - (high.rolling(PERIOD, min_periods=PERIOD).max()
                     - MULT * wilder_rma(tr, length=PERIOD))) / close


def _module_true_range(high, low, close):
    """The module's own true range, re-spelled here so the ATR variants
    above differ from the shipped column in their SMOOTHER alone."""
    prev = close.shift(1)
    tr = pd.concat([high - low, (high - prev).abs(), (low - prev).abs()],
                   axis=1).max(axis=1)
    tr.iloc[:1] = np.nan
    return tr


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


# ----------------------------------------------------------------- mutants

SOURCE = Path(__file__).resolve().parents[1] / "pandas_ta" / "trend" \
    / "j_chandelier_dist.py"

#: (label, old text, new text). Edits to the SHIPPED source, read off disk.
#: Every one makes the OUTPUT read a bar LATER than T, so the blind suffix
#: sweep must catch every one.
#:
#: ⚠ Unlike `j_safezone_dist`, this chain holds no forward `shift` at all
#: between a price and the output -- both legs read bar T -- so a one-bar
#: lead IS a look-ahead here and the mutants need no two-bar leads.
CAUSALITY_MUTANTS = [
    ("tr-high-lead",
     "    ranges = concat([high - low, (high - prev).abs(), (low - prev).abs()],",
     "    ranges = concat([high.shift(-1) - low, (high - prev).abs(), (low - prev).abs()],"),
    ("tr-prev-lead",
     "    prev = close.shift(1)",
     "    prev = close.shift(-1)"),
    ("atr-lead",
     "    atr = wilder_rma(tr, length=PERIOD)",
     "    atr = wilder_rma(tr.shift(-1), length=PERIOD)"),
    ("hh-lead",
     "    hh = hi.rolling(PERIOD, min_periods=PERIOD).max()",
     "    hh = hi.shift(-1).rolling(PERIOD, min_periods=PERIOD).max()"),
    ("close-lead",
     "    dist = (px - stop) / px",
     "    dist = (px.shift(-1) - stop) / px.shift(-1)"),
    ("output-early",
     "    dist = dist.where(np.isfinite(dist))",
     "    dist = dist.where(np.isfinite(dist)).shift(-1)"),
]

#: NOT causality mutants, and printing them is the point: each makes the
#: true range read bar T's OWN close where it should read yesterday's, or
#: lags a leg by a bar. None reads a LATER bar, so the suffix sweep is BLIND
#: to all of them. Gate A's oracle is not. §B2 measures both halves of that,
#: so Gate B's result is not read as more than it is.
BLIND_SPOT_MUTANTS = [
    ("tr-today-close", "    prev = close.shift(1)", "    prev = close"),
    ("tr-two-days-ago", "    prev = close.shift(1)", "    prev = close.shift(2)"),
    ("hh-lag",
     "    hh = hi.rolling(PERIOD, min_periods=PERIOD).max()",
     "    hh = hi.shift(1).rolling(PERIOD, min_periods=PERIOD).max()"),
]

#: The five guards, each removable on its own, so §G2 can price each one
#: instead of asserting that they are all needed.
HI_GUARD_OFF = ("    hi = hi.where(np.isfinite(hi))", "    pass")
LO_GUARD_OFF = ("    lo = lo.where(np.isfinite(lo))", "    pass")
CL_GUARD_OFF = ("    cl = cl.where(np.isfinite(cl))", "    pass")
PX_GUARD_OFF = ("    px = cl.where(cl >= np.finfo(float).tiny)",
                "    px = cl")
#: The final finite guard, removed, to price it.
FINITE_GUARD_OFF = ("    dist = dist.where(np.isfinite(dist))", "    pass")
GUARDS = [("high is finite", HI_GUARD_OFF), ("low is finite", LO_GUARD_OFF),
          ("close is finite", CL_GUARD_OFF),
          ("close is positive+normal", PX_GUARD_OFF),
          ("output is finite", FINITE_GUARD_OFF)]
#: Bar 0's true range restored, which is the prototype's reading and moves
#: the ATR seed back one bar.
BAR_ZERO_TR_ON = ("    tr.iloc[:1] = np.nan", "    pass")


def _mutant(old, new):
    src = SOURCE.read_text(encoding="utf-8")
    assert src.count(old) == 1, f"{old!r} occurs {src.count(old)} times"
    ns = {}
    exec(compile(src.replace(old, new), "<mutant>", "exec"), ns)
    return ns["j_chandelier_dist"]


def _caught_at(fn, frame, j, factor=1.03):
    """Did perturbing every bar >= j move any bar < j?

    ⚠ `factor` on all three legs is not a global rescale -- the column is
    invariant under one of those, which is Gate D -- it is a rescale of a
    SUFFIX, which moves the true range and the highest high at bar j.
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


# ------------------------------------------------------------- overflow


def _OVERFLOW_ROUTES():
    """The three ways a FINITE triple of inputs can still make an infinity,
    in the order they occur in the chain -- the true range's gap leg, the
    stop's subtraction, the final division. The labels carry the numbers so
    the table, the prose and the tests cannot drift onto three different
    numberings.

    ⚠ `j_safezone_dist` found that pandas' COMPENSATED `rolling.sum`
    absorbed two of its three routes. There is no rolling sum in this
    chain, so that absorption cannot happen here, and §G3 measures which
    routes reach the output rather than assuming either way.
    """
    idx = date_range("2020-01-01", periods=120, freq="h")
    rng = np.random.default_rng(5)
    big = np.finfo(float).max
    n = 120
    return [
        # 1. the true range's `high - prev close`: +DBL_MAX against
        #    -DBL_MAX. The finite guards do not demand an ordered bar.
        ("1. true range (+max high, -max close)",
         Series(np.full(n, big), index=idx),
         Series(np.full(n, -big), index=idx),
         Series(np.where(np.arange(n) % 2 == 0, -big, big), index=idx)),
        # 2. the stop's `hh - 3 * atr`: an ATR near DBL_MAX / 3.
        ("2. stop (3 x an ATR near DBL_MAX/3)",
         Series(np.full(n, big / 3.0), index=idx),
         Series(np.full(n, -big / 3.0), index=idx),
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
    """
    tr = _module_true_range(high, low, close)
    atr = wilder_rma(tr, length=PERIOD)
    hh = high.rolling(PERIOD, min_periods=PERIOD).max()
    stop = hh - MULT * atr
    parts = [high, low, close, tr, atr, hh, stop]
    return max(float(p.abs().max()) for p in parts if int(p.notna().sum()))


# ------------------------------------------------------------- neighbours


def _neighbours(high, low, close):
    """In-fork columns of the same shape, for §L.

    ⚠ A DISCLOSURE, not Gate E: six synthetic frames, not the 89 real ones,
    and these are fork columns rather than the engine's 687 comparators.
    But NOT "columns Gate E cannot see" -- THREE of them,
    `ICHI_PRICE_VS_KIJUN`, `bias` and `Range_Pos_20` (retyped from the rule
    here, since the manifest is unreadable from this worktree), carry the
    same names as comparators the screen's own Gate E run listed, and
    neither the engine's `compute_all` nor the `ml_features` manifest is
    readable from here, so whether those three are computed through this
    fork was not checked.
    """
    out = {}
    v = vstop(high=high, low=low, close=close)
    out["vstop:VSTOP_DIST_PCT_20_1.0"] = v.iloc[:, 0]
    ck = cksp(high=high, low=low, close=close)
    # `CKSPl` is a PRICE LEVEL and so ships as no feature at all; the
    # comparable quantity is its distance from the close, which is what
    # this column is. Same shape, different parameters: (10, 3, 20) --
    # `cksp`'s BOOK defaults, because `cksp.py` computes `x` and `q` before
    # `tvmode` is defaulted -- and smoothed with the fork's `rma` rather
    # than Wilder's. The column name is read off the returned frame rather
    # than typed, so a parameter change here cannot go unnoticed.
    long_stop = ck.columns[0]
    out[f"cksp:(close-{long_stop})/close"] = (close - ck[long_stop]) / close
    ichi = ichimoku_ml(high=high, low=low, close=close)
    out["ichimoku_ml:ICHI_PRICE_VS_KIJUN"] = ichi["ICHI_PRICE_VS_KIJUN"]
    out["j_safezone_dist:J_SAFEZONE_DIST_22_2.5_3"] = j_safezone_dist(
        low=low, close=close)
    out["natr:NATR_14"] = natr(high=high, low=low, close=close)
    out["chop:CHOP_14_1_100"] = chop(high=high, low=low, close=close)
    out["bias:BIAS_SMA_26"] = bias(close=close)
    # A RETYPED analogue of the screen's nearest Gate E comparator
    # (`Range_Pos_20`, 0.8606 on 89 real frames), not the manifest's own
    # column: the manifest is not in this repo. Labelled as such.
    hh20 = high.rolling(20, min_periods=20).max()
    ll20 = low.rolling(20, min_periods=20).min()
    out["(retyped analogue) Range_Pos_20"] = (close - ll20) / (hh20 - ll20)
    return out


# ---------------------------------------------------------------- sections


def _rule(title):
    print()
    print("=" * 78)
    print(title)
    print("=" * 78)


def section_env():
    _rule("§0  environment")
    print(f"python  {sys.version.split()[0]}  ({platform.machine()})")
    print(f"numpy   {np.__version__}")
    print(f"pandas  {pd.__version__}")
    dispatch = getattr(np.core._multiarray_umath, "__cpu_dispatch__", [])
    enabled = [f for f in dispatch
               if np.core._multiarray_umath.__cpu_features__.get(f)]
    print(f"dispatchable features enabled: {enabled}")
    for name in ("talib", "jesse", "stock_indicators"):
        print(f"{name:>18} installed: "
              f"{importlib.util.find_spec(name) is not None}")
    print(f"PERIOD={PERIOD}  MULT={MULT}  MIN_BARS={MIN_BARS}  "
          f"WARMUP={WARMUP}  N={N}  FIRED={FIRED}")


def section_A1():
    _rule("§A1  Gate A -- the module against a bar-by-bar oracle")
    print(f"{'frame':<14}{'fired':>7}{'nan-mask':>10}{'bit-equal':>11}"
          f"{'max |abs|':>13}{'max |rel|':>13}")
    for name in VARYING:
        frame = _frame(name)
        got, want = j_chandelier_dist(*frame), _oracle(*frame)
        print(f"{name:<14}{int(got.notna().sum()):>7}"
              f"{str(bool((got.isna() == want.isna()).all())):>10}"
              f"{str(_bit_equal(got, want)):>11}"
              f"{_abs(got, want):>13.3e}{_rel(got, want):>13.3e}")
    print()
    print("the same oracle with the Wilder step re-associated as "
          "alpha*tr + (1-alpha)*atr[-1]:")
    print(f"{'frame':<14}{'bit-equal':>11}{'max |abs|':>13}{'max |rel|':>13}")
    for name in VARYING:
        frame = _frame(name)
        a, b = _oracle(*frame), _oracle_wilder_longhand(*frame)
        print(f"{name:<14}{str(_bit_equal(a, b)):>11}"
              f"{_abs(a, b):>13.3e}{_rel(a, b):>13.3e}")


def section_A2():
    _rule("§A2  Gate A -- the module against talib's MAX and ATR")
    lib = _talib()
    if lib is None:
        print("talib is NOT installed in this worktree, so this limb did "
              "not run.")
        print("It is the issue's two operators as TA-Lib spells them, and a "
              "bare 'ATR'")
        print("conventionally means TA-Lib's Wilder ATR. The test skips "
              "rather than passing.")
        return
    print(f"talib {lib.__version__}")
    print(f"{'frame':<14}{'shared':>8}{'nan-mask':>10}{'bit-equal':>11}"
          f"{'max |abs|':>13}{'max |rel|':>13}{'rho':>9}")
    for name in VARYING:
        frame = _frame(name)
        got, want = j_chandelier_dist(*frame), _talib_column(*frame)
        m = got.notna() & want.notna()
        print(f"{name:<14}{int(m.sum()):>8}"
              f"{str(bool((got.isna() == want.isna()).all())):>10}"
              f"{str(_bit_equal(got, want)):>11}"
              f"{_abs(got, want):>13.3e}{_rel(got, want):>13.3e}"
              f"{_spearman(got, want):>9.4f}")


def section_A3():
    _rule("§A3  the SCREEN PROTOTYPE is a different column on the warm-up")
    print("The prototype's ATR is `tr.ewm(alpha=1/22, adjust=False)` seeded "
          "at bar 0 with")
    print("bar 0's own high-low range; the source formula's is seeded with "
          "the mean of true")
    print("ranges 1..22. Same recursion, different seed, so they converge "
          "at (21/22)^k.")
    print()
    print(f"{'frame':<14}{'shared':>8}{'differ':>8}{'last differ':>12}"
          f"{'max |abs|':>12}{'max |rel|':>12}{'rho':>9}")
    for name in VARYING:
        frame = _frame(name)
        got, proto = j_chandelier_dist(*frame), _prototype(*frame)
        m = got.notna() & proto.notna()
        differ, last = _differing_bars(got, proto)
        print(f"{name:<14}{int(m.sum()):>8}{differ:>8}{last:>12}"
              f"{_abs(got, proto):>12.3e}{_rel(got, proto):>12.3e}"
              f"{_spearman(got, proto):>9.4f}")
    print()
    print("where the two STOP differing, bar by bar, on `walk`:")
    frame = _frame("walk")
    got, proto = j_chandelier_dist(*frame), _prototype(*frame)
    d = (got - proto).abs()
    for bar in (22, 50, 100, 200, 400, 600, 800, 1000, 1499):
        print(f"  bar {bar:>5}: |difference| = {float(d.iloc[bar]):.6e}")
    print()
    print("prototype fires on bars the module does not (its ATR needs no "
          "seed window):")
    for name in VARYING:
        frame = _frame(name)
        got, proto = j_chandelier_dist(*frame), _prototype(*frame)
        only = int((proto.notna() & got.isna()).sum())
        print(f"  {name:<14} prototype-only bars: {only}")


def section_A4():
    _rule("§A4  the other readings, priced")
    alts = [
        ("(a) prototype ewm(alpha,adjust=False) from bar 0", _prototype),
        ("(b) this fork's rma (adjust=True)", _alt_fork_rma),
        ("(c) SMA(tr, 22) instead of Wilder", _alt_sma),
        ("(d) HH22 over the CLOSE, not the high", _alt_hh_close),
        ("(e) the fork's true_range (non_zero_range epsilon)",
         _alt_fork_true_range),
    ]
    for label, fn in alts:
        print()
        print(label)
        print(f"  {'frame':<14}{'shared':>8}{'differ':>8}{'max |abs|':>12}"
              f"{'max |rel|':>12}{'rho':>9}")
        for name in VARYING + ["tied"]:
            frame = _frame(name)
            got, alt = j_chandelier_dist(*frame), fn(*frame)
            m = got.notna() & alt.notna()
            differ, _ = _differing_bars(got, alt)
            print(f"  {name:<14}{int(m.sum()):>8}{differ:>8}"
                  f"{_abs(got, alt):>12.3e}{_rel(got, alt):>12.3e}"
                  f"{_spearman(got, alt):>9.4f}")
    print()
    print("(e) WHERE THE EPSILON BITES, measured on both sides rather than "
          "assumed.")
    print("`non_zero_range` adds `sys.float_info.epsilon` "
          f"({np.finfo(float).eps:.3e}) to EVERY bar of")
    print("the `high - low` leg as soon as ONE bar has `high == low`. It is "
          "an ABSOLUTE")
    print("quantity, so whether it survives depends on the price LEVEL, "
          "and Gate D runs at")
    print("1e-6 as well as at 100.")
    print()
    print(f"{'frame':<10}{'level':>9}{'ties':>7}{'differ':>8}"
          f"{'max |abs|':>12}{'module x8':>11}{'variant x8':>12}"
          f"{'variant x64':>13}")
    for name in ("walk", "grid", "flat", "tied"):
        for level in (LEVEL, 1e-6):
            high, low, close = _frame(name)
            # ⚠ at LEVEL the frame is used UNTOUCHED: `h / 100 * 100` is
            # not the identity in binary floating point, and an earlier
            # draft of this table read its own rounding as 4 extra
            # disagreeing bars.
            frame = ((high, low, close) if level == LEVEL else
                     (high / LEVEL * level, low / LEVEL * level,
                      close / LEVEL * level))
            ties = int((frame[0].to_numpy() == frame[1].to_numpy()).sum())
            mine, theirs = j_chandelier_dist(*frame), _alt_fork_true_range(
                *frame)
            differ, _ = _differing_bars(mine, theirs)
            print(f"{name:<10}{level:>9.0e}{ties:>7}{differ:>8}"
                  f"{_abs(mine, theirs):>12.3e}"
                  f"{str(_bit_equal(mine, j_chandelier_dist(*_scaled(frame, 8.0)))):>11}"
                  f"{str(_bit_equal(theirs, _alt_fork_true_range(*_scaled(frame, 8.0)))):>12}"
                  f"{str(_bit_equal(theirs, _alt_fork_true_range(*_scaled(frame, 64.0)))):>13}")


def section_A5():
    _rule("§A5  the warm-up is the chain, not the number 22")
    high, low, close = _frame("walk")
    tr = _module_true_range(high, low, close)
    atr = wilder_rma(tr, length=PERIOD)
    hh = high.rolling(PERIOD, min_periods=PERIOD).max()
    col = j_chandelier_dist(high, low, close)

    def first(s):
        return int(s.notna().to_numpy().argmax())

    for label, s in (("true range", tr), ("wilder atr", atr),
                     ("highest high", hh), ("column", col)):
        print(f"  first non-NaN of {label:<13} = {first(s)}")
    print(f"  MIN_BARS = {MIN_BARS}; a frame of exactly MIN_BARS bars fires "
          f"on "
          f"{int(j_chandelier_dist(high.iloc[:MIN_BARS], low.iloc[:MIN_BARS], close.iloc[:MIN_BARS]).notna().sum())}")
    print(f"  a frame of MIN_BARS - 1 bars returns "
          f"{j_chandelier_dist(high.iloc[:MIN_BARS - 1], low.iloc[:MIN_BARS - 1], close.iloc[:MIN_BARS - 1])!r}")
    lib = _talib()
    if lib is None:
        print("  talib is NOT installed, so the TRANGE/ATR limb below did "
              "not run.")
    else:
        ref_tr = Series(lib.TRANGE(high.to_numpy(dtype=float),
                                   low.to_numpy(dtype=float),
                                   close.to_numpy(dtype=float)),
                        index=close.index)
        ref_atr = Series(lib.ATR(high.to_numpy(dtype=float),
                                 low.to_numpy(dtype=float),
                                 close.to_numpy(dtype=float), PERIOD),
                         index=close.index)
        print(f"  talib.TRANGE first non-NaN = {first(ref_tr)}, "
              f"bit-equal to this module's true range: "
              f"{_bit_equal(tr, ref_tr)}")
        print(f"  talib.ATR({PERIOD}) first non-NaN = {first(ref_atr)}, "
              f"max |abs| vs wilder_rma(tr, {PERIOD}) = "
              f"{_abs(atr, ref_atr):.3e}, "
              f"on an ATR of magnitude {float(ref_atr.abs().median()):.4f} "
              f"(median)")
    print()
    print("  bar 0's true range, restored (the prototype's reading), moves "
          "the seed:")
    fn = _mutant(*BAR_ZERO_TR_ON)
    moved = fn(high, low, close)
    print(f"    first non-NaN = {first(moved)}, "
          f"differing bars vs the module = {_differing_bars(col, moved)[0]}, "
          f"max |abs| = {_abs(col, moved):.3e}")


def section_B1():
    _rule("§B1  Gate B -- the blind future sweep")
    print(f"36 offsets ({OFFSETS[0]} .. {OFFSETS[-1]}), each rescaling every "
          f"bar >= j by 1.03.")
    print()
    print(f"{'frame':<14}{'module caught':>15}")
    for name in VARYING:
        print(f"{name:<14}{_sweep(j_chandelier_dist, _frame(name)):>15}")
    print()
    print("mutants read off the shipped source, each a read of a LATER bar:")
    print(f"{'mutant':<16}{'frame':<14}{'live':>6}{'caught/36':>11}"
          f"{'first catch |abs|':>19}")
    for label, old, new in CAUSALITY_MUTANTS:
        fn = _mutant(old, new)
        for name in SWEPT:
            frame = _frame(name)
            a, b = j_chandelier_dist(*frame), fn(*frame)
            m = a.notna() & b.notna()
            live = bool(int(m.sum())) and not bool(
                (a[m].to_numpy() == b[m].to_numpy()).all())
            caught = _sweep(fn, frame)
            loud = _first_catch_loudness(fn, frame)
            print(f"{label:<16}{name:<14}{str(live):>6}{caught:>11}"
                  f"{loud:>19.3e}")


def section_B2():
    _rule("§B2  Gate B -- the sweep's blind spot, and the oracle covering it")
    print("Each edit below makes the true range read the WRONG close, or "
          "lags a leg, without")
    print("reading any LATER bar. The sweep is blind to all of them; Gate "
          "A's oracle is not.")
    print()
    print(f"{'mutant':<16}{'frame':<14}{'caught/36':>11}"
          f"{'vs oracle bit-equal':>21}{'max |abs| vs oracle':>21}")
    for label, old, new in BLIND_SPOT_MUTANTS:
        fn = _mutant(old, new)
        for name in ("walk", "heavy-tailed"):
            frame = _frame(name)
            print(f"{label:<16}{name:<14}{_sweep(fn, frame):>11}"
                  f"{str(_bit_equal(fn(*frame), _oracle(*frame))):>21}"
                  f"{_abs(fn(*frame), _oracle(*frame)):>21.3e}")


def section_C1():
    _rule("§C1  Gate C -- reachability on the six varying frames")
    print(f"{'frame':<14}{'fired':>7}{'of':>6}{'distinct':>10}{'min':>12}"
          f"{'max':>12}{'<0':>7}{'==0':>7}")
    pooled = []
    for name in VARYING:
        col = _col(name)
        values = col.dropna()
        pooled.append(values)
        print(f"{name:<14}{int(col.notna().sum()):>7}{len(col):>6}"
              f"{int(values.nunique()):>10}{float(values.min()):>12.6f}"
              f"{float(values.max()):>12.6f}"
              f"{int((values < 0).sum()):>7}{int((values == 0).sum()):>7}")
    allv = pd.concat(pooled)
    print(f"{'POOLED':<14}{len(allv):>7}{'':>6}{int(allv.nunique()):>10}"
          f"{float(allv.min()):>12.6f}{float(allv.max()):>12.6f}"
          f"{int((allv < 0).sum()):>7}{int((allv == 0).sum()):>7}")
    print()
    print("⚠ Gate C's REAL-DATA limb is owed: everything above is "
          "synthetic. The launcher's")
    print("Gate E run reports the non-NaN count over the 89 BIST frames "
          "and a receipt session")
    print("writes it into §C of docs/JChandelierDistMeasured.md.")


def section_C2():
    _rule("§C2  the two degenerate frames")
    for name in ("flat", "rising"):
        col = _col(name)
        values = col.dropna()
        print(f"{name:<10} fired {int(col.notna().sum()):>5} of {len(col)}, "
              f"distinct {int(values.nunique())}, "
              f"min {float(values.min()):.6f}, max {float(values.max()):.6f}")
    print()
    print("`flat` is the sharp one: high == low == close on every bar, so "
          "every true range is")
    print("0, the ATR is 0, the stop IS the highest high and the column is "
          "exactly 0.0. It")
    print("fires, so `0 < fires < n` holds, and it is CONSTANT, which is "
          "why Gate D's")
    print("'not a constant column' limb is asserted on the varying frames "
          "instead.")


def section_D1():
    _rule("§D1  Gate D -- x8 / x64 are bit-identical")
    print(f"{'frame':<14}{'x8':>8}{'x64':>8}{'fired':>8}")
    for name in VARYING:
        frame = _frame(name)
        base = j_chandelier_dist(*frame)
        print(f"{name:<14}"
              f"{str(_bit_equal(base, j_chandelier_dist(*_scaled(frame, 8.0)))):>8}"
              f"{str(_bit_equal(base, j_chandelier_dist(*_scaled(frame, 64.0)))):>8}"
              f"{int(base.notna().sum()):>8}")


def section_D2():
    _rule("§D2  Gate D -- inexact factors, max relative move")
    factors = [10.0, 3.7, 0.1, 1.0000001]
    print(f"{'frame':<14}" + "".join(f"{f'x{f:g}':>14}" for f in factors)
          + f"{'nan masks':>12}")
    worst = 0.0
    for name in VARYING:
        frame = _frame(name)
        base = j_chandelier_dist(*frame)
        cells, masks = [], True
        for factor in factors:
            moved = j_chandelier_dist(*_scaled(frame, factor))
            masks = masks and bool((base.isna() == moved.isna()).all())
            cell = _rel(moved, base)
            worst = max(worst, cell)
            cells.append(cell)
        print(f"{name:<14}" + "".join(f"{c:>14.3e}" for c in cells)
              + f"{str(masks):>12}")
    print(f"\nworst cell over the {len(VARYING) * len(factors)} cells: "
          f"{worst:.6e}")
    print("⚠ this figure moves between numpy CPU dispatches, so the test "
          "asserts 1e-9.")


def section_D3():
    _rule("§D3  Gate D -- extreme price levels, and the headroom printed")
    high, low, close = _frame("walk")
    print(f"{'level':>10}{'fired':>8}{'x8':>8}{'x64':>8}"
          f"{'largest intermediate':>24}{'DBL_MAX / it':>16}")
    big = float(np.finfo(float).max)
    for level in (1e-6, 1e6, 1e100):
        frame = (high / LEVEL * level, low / LEVEL * level,
                 close / LEVEL * level)
        base = j_chandelier_dist(*frame)
        worst = max(_largest_intermediate(*_scaled(frame, f))
                    for f in (1.0, 8.0, 64.0))
        print(f"{level:>10.0e}{int(base.notna().sum()):>8}"
              f"{str(_bit_equal(base, j_chandelier_dist(*_scaled(frame, 8.0)))):>8}"
              f"{str(_bit_equal(base, j_chandelier_dist(*_scaled(frame, 64.0)))):>8}"
              f"{worst:>24.3e}{big / worst:>16.3e}")
    print("\nthe largest intermediate is taken over high, low, close, tr, "
          "atr, hh and stop,")
    print("at x1, x8 and x64 of each level -- walked, not reasoned about.")


def section_D4():
    _rule("§D4  Gate D -- a level SHIFT moves every fired bar")
    print("The check that keeps the x8 bit-identity from being vacuous.")
    print(f"{'frame':<14}{'fired':>8}{'moved by +10':>14}")
    for name in VARYING:
        high, low, close = _frame(name)
        base = j_chandelier_dist(high, low, close)
        moved = j_chandelier_dist(high + 10.0, low + 10.0, close + 10.0)
        m = base.notna() & moved.notna()
        print(f"{name:<14}{int(m.sum()):>8}"
              f"{int((base[m] != moved[m]).sum()):>14}")


def section_E():
    _rule("§E  Gate E")
    print("Gate E: pending, run by issue-solver after this session.")
    print()
    print("The screen measured the PROTOTYPE (2026-10-24, run "
          "screen_r2_20261024):")
    print("  max |rho| 0.8606 vs Range_Pos_20 (manifest, n = 396,980)")
    print("  top-5 per-frame max median 0.8759  ->  DISCLOSE_GAP")
    print("  next: ICHI_PRICE_VS_KIJUN 0.8485, bias 0.8438")
    print("⚠ and that was the prototype's ATR, not this module's -- §A3 "
          "prices the gap.")
    print("The port's own run decides its band; this session does not run "
          "Gate E.")


def section_G1():
    _rule("§G1  one bad price, and exactly which bars it empties")
    high, low, close = _frame("walk")
    base = j_chandelier_dist(high, low, close)
    print(f"{'leg':<7}{'value':>8}{'bar':>7}{'bars emptied':>14}"
          f"{'first':>8}{'last':>8}{'prefix bit-equal':>18}"
          f"{'bars MOVED after j':>20}{'last moved':>12}")
    for leg in ("high", "low", "close"):
        for value in (np.nan, np.inf, -np.inf):
            for j in (100, 700, 1100):
                h, l, c = high.copy(), low.copy(), close.copy()
                {"high": h, "low": l, "close": c}[leg].iloc[j] = value
                with np.errstate(all="ignore"):
                    col = j_chandelier_dist(h, l, c)
                gone = np.flatnonzero(
                    (base.notna() & col.isna()).to_numpy())
                moved, last_moved = _differing_bars(base.iloc[j:],
                                                    col.iloc[j:])
                print(f"{leg:<7}{value:>8.3g}{j:>7}{gone.size:>14}"
                      f"{(int(gone[0]) - j if gone.size else 0):>+8}"
                      f"{(int(gone[-1]) - j if gone.size else 0):>+8}"
                      f"{str(_bit_equal(base.iloc[:j], col.iloc[:j])):>18}"
                      f"{moved:>20}{last_moved:>12}")
    print("\n(first/last are OFFSETS from the planted bar j; 'bars MOVED'"
          " counts bars at or")
    print("after j that still FIRE but read a different number, and 'last "
          "moved' is the last")
    print("such bar as an offset from j -- -1 when there is none.)")
    print()
    print("⚠ WHY A BAD HIGH MOVES NOTHING AT BARS 100 AND 700 AND MOVES "
          "EVERYTHING AT 1100.")
    print("Dropping the high blanks the two true-range legs that use it "
          "and leaves")
    print("`|low - prev close|`, and `max(axis=1)` SKIPS the NaNs rather "
          "than propagating")
    print("them -- so the true range changes only when a high leg was the "
          "winning one,")
    print("which is what an UP bar has. Measured, rather than inferred "
          "from the counts:")
    tr_full = _module_true_range(high, low, close)
    for j in (100, 700, 1100):
        legs = {"high - low": float(high.iloc[j] - low.iloc[j]),
                "|high - prev close|": abs(float(high.iloc[j]
                                                 - close.iloc[j - 1])),
                "|low - prev close|": abs(float(low.iloc[j]
                                                - close.iloc[j - 1]))}
        winner = max(legs, key=legs.get)
        direction = ("up" if close.iloc[j] > close.iloc[j - 1] else "down")
        print(f"  bar {j:>5}: {direction}-bar, true range "
              f"{float(tr_full.iloc[j]):.6f} set by {winner!r}; "
              f"without the high legs it would be "
              f"{legs['|low - prev close|']:.6f}")
    print()
    print("⚠ A bad LOW empties NOTHING and is still not harmless: it is "
          "the row where the")
    print("two columns separate. `low` reaches the output only through the "
          "true range, and")
    print("`wilder_rma` SKIPS a NaN observation rather than blanking it, "
          "so the ATR carries")
    print("and a BOUNDED RUN of later bars reads a slightly different "
          "number with no NaN to")
    print("flag it -- read the `bars MOVED` and `last moved` columns: NOT "
          "every later bar.")
    print("At a plant of bar 100 there are 1,400 later bars and 658 of "
          "them move; the")
    print("recursion forgets the perturbation at (21/22)^k, the same decay "
          "§A3 prints bar")
    print("by bar, so the column is bit-identical again from bar 809 "
          "onward. The run is")
    print("only unbounded where the FRAME ends first, which is the 1100 "
          "plant.")
    print()
    print("⚠ the helper's NaN semantics, stated rather than assumed: "
          "`wilder_rma` CARRIES its")
    print("state across a NaN observation instead of poisoning the rest of "
          "the series. So a")
    print("mid-series hole costs a bounded run of bars here, and the "
          "oracle -- which is")
    print("TA-Lib's rule, where a NaN poisons everything after it -- is "
          "run on clean frames.")
    print("Bars after the hole, module vs oracle, on a frame with a NaN "
          "high at bar 700:")
    h = high.copy()
    h.iloc[700] = np.nan
    module_hole = j_chandelier_dist(h, low, close)
    oracle_hole = _oracle(h, low, close)
    tail = slice(760, None)
    print(f"  module fires on {int(module_hole.iloc[tail].notna().sum())} "
          f"bars after 760; oracle on "
          f"{int(oracle_hole.iloc[tail].notna().sum())}")


def section_G2():
    _rule("§G2  the five guards, each priced on its own")
    print("A guard that changes nothing anywhere is decoration. Each row "
          "removes ONE guard")
    print("from the shipped source and reports what moves.")
    print()
    print("(i) on the nine ordinary frames, every guard must be a no-op:")
    print(f"  {'guard':<26}" + "".join(f"{n[:9]:>11}" for n in FRAMES))
    for label, (old, new) in GUARDS:
        bare = _mutant(old, new)
        cells = []
        for name in FRAMES:
            frame = _frame(name)
            cells.append(str(_bit_equal(j_chandelier_dist(*frame),
                                        bare(*frame))))
        print(f"  {label:<26}" + "".join(f"{c:>11}" for c in cells))
    print()
    print("(ii) on frames built to reach them -- `fired` and `inf` are the "
          "column's, with")
    print("the guard removed, against the shipped module's in brackets:")
    high, low, close = _frame("walk")
    probes = []
    for leg, value in (("high", np.inf), ("low", -np.inf),
                       ("close", np.inf)):
        h, l, c = high.copy(), low.copy(), close.copy()
        {"high": h, "low": l, "close": c}[leg].iloc[700] = value
        probes.append((f"{leg} = {value:+.0f} at bar 700", (h, l, c)))
    cl0 = close.copy()
    cl0.iloc[700] = 0.0
    probes.append(("close = 0 at bar 700", (high, low, cl0)))
    clneg = close.copy()
    clneg.iloc[700] = -50.0
    probes.append(("close = -50 at bar 700", (high, low, clneg)))
    probes.append(("1e300 stop over a 1e-300 close",
                   tuple(_OVERFLOW_ROUTES()[2][1:])))
    print(f"  {'probe':<32}{'guard':<26}{'fired':>14}{'inf':>10}"
          f"{'differ':>8}{'max |abs|':>12}")
    for probe_label, frame in probes:
        with np.errstate(all="ignore"):
            ship = j_chandelier_dist(*frame)
        for label, (old, new) in GUARDS:
            bare = _mutant(old, new)
            with np.errstate(all="ignore"):
                col = bare(*frame)
            if _bit_equal(ship, col):
                continue
            differ, _ = _differing_bars(ship, col)
            print(f"  {probe_label:<32}{label:<26}"
                  f"{f'{int(col.notna().sum())} ({int(ship.notna().sum())})':>14}"
                  f"{f'{int(np.isinf(col).sum())} ({int(np.isinf(ship).sum())})':>10}"
                  f"{differ:>8}{_abs(ship, col):>12.3e}")
    print()
    print("⚠ A GUARD WITH A ROW HERE IS LOAD-BEARING, and the two columns "
          "`fired` and `inf`")
    print("are blind to three of them -- which is why `differ` and "
          "`max |abs|` are printed")
    print("beside them. An earlier draft of this section read the equal "
          "`fired`/`inf` cells")
    print("as 'the three input guards move nothing' and said so in the "
          "receipt, the shipped")
    print("docstring and the test header. The row exists at all only "
          "because removing the")
    print("guard changed the column; the loop above skips a guard that is "
          "bit-equal.")
    print()
    print()
    print("⚠ `differ` and `max |abs|` are DISPATCH-DEPENDENT, which is why "
          "they are quoted")
    print("with their reduced-CPU values everywhere they appear: "
          "`docs/measure_j_chandelier_")
    print("dist_cpu.py G2` prints 634 / 662 / 664 for the three input "
          "guards against the")
    print("636 / 664 / 663 above. The assertions that rest on them are "
          "shapes (`> 300`")
    print("bars, `> 1e-5`), not these counts.")
    print()
    print("The mechanism, and it is NOT 'pandas blanks it anyway': with "
          "the guard, the bad")
    print("leg is NaN and `max(axis=1)` SKIPS it, so the true range is the "
          "largest SURVIVING")
    print("leg and the ATR takes it; without the guard the leg is "
          "infinite, the true range")
    print("is infinite, and a pandas window DROPS that observation "
          "entirely (§G3). Two")
    print("different ATRs from bar T onward -- with identical NaN masks "
          "and identical")
    print("counts, which is exactly why `fired` and `inf` cannot see it.")


def section_G3():
    _rule("§G3  three routes to an infinity on FINITE inputs")
    bare = _mutant(*FINITE_GUARD_OFF)
    print(f"{'route':<40}{'bars':>6}{'inf guarded':>13}{'inf bare':>10}"
          f"{'fired guarded':>15}")
    for label, high, low, close in _OVERFLOW_ROUTES():
        with np.errstate(all="ignore"):
            guarded = j_chandelier_dist(high, low, close)
            unguarded = bare(high, low, close)
        # The frame length is PRINTED rather than left in this file's
        # source: the receipt quotes "97 of 120" and the denominator has to
        # come from the run like the numerator does (§G4 prints its 60 for
        # the same reason).
        print(f"{label:<40}{len(close):>6}{int(np.isinf(guarded).sum()):>13}"
              f"{int(np.isinf(unguarded).sum()):>10}"
              f"{int(guarded.notna().sum()):>15}")
    print()
    print("⚠ `j_safezone_dist` found pandas' COMPENSATED `rolling.sum` "
          "absorbing two of its")
    print("three routes. There is no rolling sum in this chain -- and route "
          "1 is absorbed")
    print("anyway, by a DIFFERENT pandas behaviour, measured here rather "
          "than assumed:")
    print("a pandas WINDOW operation replaces an infinite observation with "
          "NaN before it")
    print("smooths. So an infinite true range leaves the ATR carrying its "
          "previous state")
    print("rather than going infinite, and the probes below show the "
          "infinity LEAVING NO")
    print("TRACE while a merely huge DBL_MAX flows straight through:")
    for label, values in (
            ("one +inf at bar 40 of 81", [1.0] * 40 + [np.inf] + [1.0] * 40),
            ("one DBL_MAX at bar 40 of 81",
             [1.0] * 40 + [float(np.finfo(float).max)] + [1.0] * 40)):
        probe = Series(values)
        with np.errstate(all="ignore"):
            smoothed = probe.ewm(alpha=1.0 / PERIOD, adjust=False).mean()
        print(f"  {label} -> {int(np.isinf(smoothed).sum())} infinite, "
              f"{int(smoothed.isna().sum())} NaN; bars 40..44 read "
              + ", ".join(f"{v:.3e}" for v in smoothed.iloc[40:45]))
    print()
    print("  and the same two through `wilder_rma`, which is what the "
          "module calls:")
    for label, values in (
            ("one +inf at bar 40 of 81", [1.0] * 40 + [np.inf] + [1.0] * 40),
            ("one DBL_MAX at bar 40 of 81",
             [1.0] * 40 + [float(np.finfo(float).max)] + [1.0] * 40)):
        probe = Series(values)
        with np.errstate(all="ignore"):
            smoothed = wilder_rma(probe, length=PERIOD)
        print(f"  {label} -> {int(np.isinf(smoothed).sum())} infinite, "
              f"{int(smoothed.isna().sum())} NaN; bars 40..44 read "
              + ", ".join(f"{v:.3e}" for v in smoothed.iloc[40:45]))
    print("  (pinned on its own in the test file, so an upgrade that moves "
          "it fails there")
    print("  rather than shipping an infinite feature.)")


def section_G4():
    _rule("§G4  degenerate and hostile frames raise nothing")
    bars = 60
    idx = date_range("2020-01-01", periods=bars, freq="h")
    for value in (0.0, -100.0, 5e-310, 1e308, np.nan):
        s = Series(np.full(bars, value), index=idx)
        with np.errstate(all="ignore"):
            col = j_chandelier_dist(s, s, s)
        fired = col.dropna()
        span = (f"min {float(fired.min()):.1f} max {float(fired.max()):.1f}"
                if len(fired) else "min -- max --")
        print(f"  constant {value:>10.3g}: fired "
              f"{int(col.notna().sum()):>3} of {bars}, infinite "
              f"{int(np.isinf(col).sum()):>3}, "
              f"distinct {int(fired.nunique())}, {span}")
    print()
    for n in (0, 1, 5, MIN_BARS - 1, MIN_BARS):
        s = Series(np.full(n, 100.0),
                   index=date_range("2020-01-01", periods=n, freq="h"))
        out = j_chandelier_dist(s, s, s)
        print(f"  a {n:>3}-bar frame -> "
              f"{'None' if out is None else f'{int(out.notna().sum())} fired'}")
    print()
    high, low, close = _frame("walk")
    for bad in (0.0, -50.0):
        cl = close.copy()
        cl.iloc[700] = bad
        col = j_chandelier_dist(high, low, cl)
        base = j_chandelier_dist(high, low, close)
        gone = np.flatnonzero((base.notna() & col.isna()).to_numpy())
        print(f"  a close of {bad:>6} at bar 700 empties bars "
              f"{gone.tolist()}")


def section_L():
    _rule("§L  in-fork overlap -- a DISCLOSURE, not Gate E")
    names = None
    rows = {}
    for frame_name in VARYING:
        frame = _frame(frame_name)
        col = j_chandelier_dist(*frame)
        nb = _neighbours(*frame)
        names = list(nb)
        for key in names:
            rows.setdefault(key, []).append(abs(_spearman(col, nb[key])))
    print(f"{'neighbour':<46}" + "".join(f"{n[:9]:>11}" for n in VARYING)
          + f"{'median':>9}")
    for key in sorted(names, key=lambda k: -float(np.median(rows[k]))):
        cells = rows[key]
        print(f"{key:<46}" + "".join(f"{c:>11.4f}" for c in cells)
              + f"{float(np.median(cells)):>9.4f}")
    print()
    print(f"⚠ SIX SYNTHETIC frames and {len(names)} chosen neighbours, not "
          f"a sweep of the fork and")
    print("not Gate E, whose 687 comparators are the engine's `compute_all` "
          "and the")
    print("`ml_features` manifest -- neither readable from this worktree.")
    print("⚠ But NOT 'columns Gate E cannot see': THREE of the rows above "
          "carry names from")
    print("the comparator list the screen's own Gate E run produced -- "
          "ICHI_PRICE_VS_KIJUN")
    print("(0.8485), bias (0.8438) and Range_Pos_20 (0.8606, the figure "
          "that decided the")
    print("prototype's band, retyped from the rule here because the "
          "manifest is unreadable")
    print("from this worktree). Whether the engine computes any of the "
          "three through this")
    print("fork was NOT checked in this session, so those three may preview "
          "the gate")
    print("rather than being invisible to it. The other five have no "
          "counterpart in that")
    print("list.")
    print()
    print("For the one fork-wide REAL-DATA figure that exists, quoted from "
          "issue #122 and")
    print("not measured here: the screen's stage 2 (scale-free Category "
          "outputs at")
    print("defaults, 12 frames) put ichimoku_ml:ICHI_PRICE_VS_KIJUN "
          "nearest at 0.8603 with a")
    print("per-frame max median of 0.8656 -- against the PROTOTYPE's "
          "column, not this one.")
    print()
    print("⚠ AND THESE FIGURES RUN HIGH, which is the reason the retyped "
          "`Range_Pos_20`")
    print("analogue is in the table at all. It is the ONE comparator with "
          "both a synthetic")
    print("number here and a real one from the screen "
          "(0.8606 over 89 BIST frames,")
    print("n = 396,980). The median above is higher than that, so a "
          "neighbour's figure in")
    print("this table is an UPPER-ish reading and not a Gate E result: six "
          "synthetic frames")
    print("of 1,500 bars share more structure than 89 real ones do.")
    gap = float(np.median(rows["(retyped analogue) Range_Pos_20"]))
    print(f"   synthetic median {gap:.4f} vs the screen's real 0.8606 -> "
          f"{gap - 0.8606:+.4f}")
    print()
    print("⚠ THE NEAREST NEIGHBOUR IS THE ONE TO READ FIRST. "
          "`cksp` is the Chande Kroll")
    print("Stop and its long leg is `HH(10) - 3*ATR(10)` run through a "
          "second 20-bar")
    print("maximum -- the same family as the Chandelier Exit. What `cksp` "
          "SHIPS is the")
    print("price LEVEL (`CKSPl_10_3_20`), which the ML contract does not "
          "treat as a feature")
    print("at all; the row above is that level turned into a distance by "
          "this file, which")
    print("the fork does not ship. So the overlap is between this column "
          "and a column that")
    print("does not exist, and it still belongs in the receipt because a "
          "consumer could")
    print("build it in one line.")


def section_Z():
    _rule("§Z  cost -- THIS machine, THIS run")
    high, low, close = _walk(seed=7, n=400_000)
    runs = 3
    seconds = timeit.repeat(
        lambda: j_chandelier_dist(high, low, close), number=1, repeat=runs)
    print(f"400,000 bars, {runs} runs: "
          + ", ".join(f"{s * 1e3:.1f} ms" for s in seconds))
    small = _frame("walk")
    seconds = timeit.repeat(lambda: j_chandelier_dist(*small), number=10,
                            repeat=runs)
    print(f"1,500 bars x 10, {runs} runs: "
          + ", ".join(f"{s * 1e2:.2f} ms/call" for s in seconds))
    print("⚠ one machine, one run, and these digits DO NOT REPRODUCE: the "
          "round-3 review's")
    print("own run of this section read 133.8 / 107.8 / 108.8 ms at 400,000 "
          "bars against")
    print("89.0 / 77.4 / 81.2 ms here, under different machine load. The "
          "receipt quotes a")
    print("per-bar order of magnitude and the LINEARITY, not these "
          "numbers; nothing else in")
    print("this file is meant to depend on either.")


SECTIONS = {
    "ENV": section_env,
    "A1": section_A1, "A2": section_A2, "A3": section_A3, "A4": section_A4,
    "A5": section_A5,
    "B1": section_B1, "B2": section_B2,
    "C1": section_C1, "C2": section_C2,
    "D1": section_D1, "D2": section_D2, "D3": section_D3, "D4": section_D4,
    "E": section_E,
    "G1": section_G1, "G2": section_G2, "G3": section_G3, "G4": section_G4,
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
