# -*- coding: utf-8 -*-
"""J-DAMIANI (PandasTa issue #105): every number in `docs/JDamianiMeasured.md`.

    python docs/measure_j_damiani.py            # every section, in order
    python docs/measure_j_damiani.py A1 D       # named sections only

One section per gate limb, printed and never derived: the repo's dominant
defect is "a claim written before it was measured", so this file is the only
place a figure in the receipt, the module docstring or
`tests/test_j_damiani.py` may come from.

    TR           = max(high - low, |high - close[-1]|, |low - close[-1]|)
    ATR(n)       = TR.ewm(alpha=1/n, adjust=False).mean()
    base         = ATR(13) / ATR(40)
    J_DAMIANI[T] = base[T] + 0.5 * (J_DAMIANI[T-1] - J_DAMIANI[T-3])

⚠ The millisecond figures of §Z are this machine's and this run's. Nothing
else here depends on the machine, and `docs/measure_j_damiani_cpu.py` re-runs
the sections under numpy's reduced CPU dispatch to show which figures move.
"""
import importlib.util
import sys
import timeit
import tracemalloc
from pathlib import Path

import numpy as np
import pandas as pd
from pandas import Series, concat, date_range

from pandas_ta.overlap.rma import rma
from pandas_ta.overlap.wilder_rma import wilder_rma
from pandas_ta.trend.chop import chop
from pandas_ta.volatility.atr import atr
from pandas_ta.volatility.atr_ma_multiple import atr_ma_multiple
from pandas_ta.volatility.j_damiani import (FAR, FAST, LAG_S, MIN_BARS, NEAR,
                                            SLOW, _volatmeter, j_damiani)
from pandas_ta.volatility.massi import massi
from pandas_ta.volatility.natr import natr
from pandas_ta.volatility.rvi import rvi
from pandas_ta.volatility.true_range import true_range
from pandas_ta.volatility.volvol import volvol

N = 1500
LEVEL = 100.0
#: Bars the column cannot fire on, on a frame whose `base` never goes NaN:
#: the feedback loop's `vol[-3]`, and nothing else. Both EWMAs are seeded at
#: bar 0, so there is no `length - 1` warm-up here.
WARMUP = FAR
FIRED = N - WARMUP


# ------------------------------------------------------------------ frames
# The same builders and seeds as `tests/test_j_damiani.py`, so a number in
# this file and a number in that one are the same measurement. `walk` ..
# `flat` are `docs/measure_j_gator.py`'s seven, kept identical on purpose:
# two ports measured on the same frames can be compared. `flat-start` is new
# here, because this column -- unlike `j_gator`'s -- has a NaN reading and a
# frame that begins without movement is how a real one reaches it.


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


#: Bars of `_flat_start` with no movement at all. A newly listed BIST name
#: pinned at its limit for its first weeks is the real-data shape this
#: stands in for.
FLAT_PREFIX = 50


def _flat_start(seed=7, n=N, level=LEVEL):
    """A walk whose first `FLAT_PREFIX` bars have `high == low == close`."""
    h, l, c = _walk(seed, n, level)
    h, l, c = h.copy(), l.copy(), c.copy()
    for s in (h, l, c):
        s.iloc[:FLAT_PREFIX] = level
    return h, l, c


FRAMES = {
    "walk": _walk, "trend": _trend, "range-bound": _range_bound,
    "grid": _grid, "heavy-tailed": _heavy, "jump": _jump, "flat": _flat,
    "flat-start": _flat_start,
}
#: The frames whose `base` is finite from bar 0, i.e. the ones that fire on
#: `FIRED` bars. `flat` fires nowhere (0/0) and `flat-start` starts late.
VARYING = ["walk", "trend", "range-bound", "grid", "heavy-tailed", "jump"]


def _scaled(frame, factor):
    h, l, c = frame
    return h * factor, l * factor, c * factor


def _agree(a, b):
    """(masks equal, shared bars, bit-equal bars, max |diff|, max |rel|)."""
    masks = bool((a.isna() == b.isna()).all())
    m = a.notna() & b.notna()
    shared = int(m.sum())
    if not shared:
        return masks, 0, 0, float("nan"), float("nan")
    same = int((a[m] == b[m]).sum())
    d = float((a[m] - b[m]).abs().max())
    scale = b[m].abs().where(b[m].abs() > 0.0, np.nan)
    rel = float(((a[m] - b[m]).abs() / scale).max())
    return masks, shared, same, d, rel


def _spearman(a, b):
    m = a.notna() & b.notna()
    if int(m.sum()) < 3 or a[m].nunique() < 2 or b[m].nunique() < 2:
        return float("nan")
    return float(a[m].corr(b[m], method="spearman"))


# ----------------------------------------------------------------- oracles


def _tr_oracle(high, low, close):
    """The three-way max, written out bar by bar."""
    h = high.to_numpy(dtype=float)
    l = low.to_numpy(dtype=float)
    c = close.to_numpy(dtype=float)
    out = np.empty(h.size)
    out[0] = h[0] - l[0]
    for i in range(1, h.size):
        out[i] = max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1]))
    return out


def _wilder_oracle(x, length):
    """`s[0] = x[0]; s[i] = (1 - a) * s[i-1] + a * x[i]`, written out."""
    a = 1.0 / length
    s = np.empty(x.size)
    s[0] = x[0]
    for i in range(1, x.size):
        s[i] = (1.0 - a) * s[i - 1] + a * x[i]
    return s


def _oracle(high, low, close):
    """The issue's formula, sharing no code with the module."""
    tr = _tr_oracle(high, low, close)
    base = _wilder_oracle(tr, FAST) / _wilder_oracle(tr, SLOW)
    out = np.full(base.size, np.nan)
    for i in range(base.size):
        near = out[i - NEAR] if i >= NEAR else 0.0
        far = out[i - FAR] if i >= FAR else 0.0
        out[i] = base[i] + LAG_S * (near - far)
    out[:FAR] = np.nan
    return Series(out, index=close.index)


def _fin(x):
    """`ind_screen.py`'s `_fin`."""
    return x.replace([np.inf, -np.inf], np.nan)


def _prototype(high, low, close):
    """`docs/issues/screen/ind_screen.py`, candidate `j_damiani`, retyped
    (that file is gitignored, so it is on the owner's machine only).

    Its `atr_wilder` and `sdiv` are inlined; everything else, including the
    loop's `0.0` for a missing predecessor and the `shift(3)` mask, is the
    prototype's own.
    """
    def atr_wilder(h, l, c, n):
        tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()],
                       axis=1).max(axis=1)
        return tr.ewm(alpha=1 / n, adjust=False).mean()

    base = _fin(atr_wilder(high, low, close, 13)
                / atr_wilder(high, low, close, 40)).to_numpy()
    out = np.full(len(base), np.nan)
    for i in range(len(base)):
        if np.isnan(base[i]):
            continue
        p1 = out[i - 1] if i >= 1 and not np.isnan(out[i - 1]) else 0.0
        p3 = out[i - 3] if i >= 3 and not np.isnan(out[i - 3]) else 0.0
        out[i] = base[i] + 0.5 * (p1 - p3)
    return Series(out, index=close.index).where(
        Series(base, index=close.index).shift(3).notna())


def _volatmeter_numpy(base_values):
    """The feedback loop, spelled the obvious way: a numpy array and
    `np.isnan`. §Z times it against the shipped spelling and shows the
    outputs bit-identical; §A5 uses it as the loop's reference."""
    out = np.full(base_values.size, np.nan)
    for i in range(base_values.size):
        if np.isnan(base_values[i]):
            continue
        near = out[i - NEAR] if i >= NEAR and not np.isnan(out[i - NEAR]) \
            else 0.0
        far = out[i - FAR] if i >= FAR and not np.isnan(out[i - FAR]) else 0.0
        out[i] = base_values[i] + LAG_S * (near - far)
    return out


#: §A5 and §A3 read the loop through the obvious spelling on purpose: a
#: figure about the FILTER should not depend on the shipped loop's
#: micro-optimisation. §Z shows the two bit-identical.
_loop = _volatmeter_numpy


def _base(high, low, close, atr_fn=None):
    """`base` alone -- the bare ATR ratio, with no feedback loop.

    `atr_fn(tr, length) -> Series` swaps the smoother; the default is the
    module's.
    """
    prev = close.shift(1)
    tr = concat([high - low, (high - prev).abs(), (low - prev).abs()],
                axis=1).max(axis=1)
    if atr_fn is None:
        def atr_fn(x, n):
            return x.ewm(alpha=1.0 / n, adjust=False).mean()
    fast, slow = atr_fn(tr, FAST), atr_fn(tr, SLOW)
    return fast / slow.where(slow > 0.0)


def _column_from(base):
    """A `base` Series through the loop and the mask -- the module's tail."""
    out = Series(_loop(base.to_numpy(dtype=float)), index=base.index)
    return out.where(base.shift(FAR).notna())


def _variant(high, low, close, atr_fn):
    return _column_from(_base(high, low, close, atr_fn))


def _sma_seeded_atr(x, n):
    """Pine's `ta.rma` / this fork's `wilder_rma`: SMA-seeded Wilder."""
    return wilder_rma(x, length=n)


def _fork_rma_atr(x, n):
    """This fork's `rma`: pandas' DEFAULT `adjust=True`, min_periods=n."""
    return rma(x, length=n)


def _plain_ema_atr(x, n):
    """`alpha = 2/(n+1)` -- reading "ATR" as a plain EMA."""
    return x.ewm(span=n, adjust=False).mean()


def _fork_tr_column(high, low, close):
    """The whole column, but with this fork's `true_range` as its TR.

    Two divergences from the issue's TR in one: `non_zero_range` adds an
    epsilon to every bar once any bar has `high == low`, and bar 0 is NaN.
    """
    tr = true_range(high, low, close)
    fast = tr.ewm(alpha=1.0 / FAST, adjust=False).mean()
    slow = tr.ewm(alpha=1.0 / SLOW, adjust=False).mean()
    return _column_from(fast / slow.where(slow > 0.0))


def _fork_atr_column(high, low, close):
    """The whole column, but with this fork's `atr()` at its default
    `mamode="rma"` -- the nearest thing a reader would reach for."""
    fast = atr(high, low, close, length=FAST)
    slow = atr(high, low, close, length=SLOW)
    return _column_from(fast / slow.where(slow > 0.0))


# ----------------------------------------------------------------- mutants

SOURCE = Path(__file__).resolve().parents[1] / "pandas_ta" / "volatility" \
    / "j_damiani.py"

#: (label, what it does, old text, new text). Every one is an edit to the
#: SHIPPED source read off disk and exec'd in memory -- never a
#: re-implementation, which could differ from the module for reasons that
#: have nothing to do with causality.
MUTANTS = [
    ("tr-lead", "the true range gaps against TOMORROW's close",
     "prev = close.shift(1)", "prev = close.shift(-1)"),
    ("fast-atr-lead", "the fast ATR smooths a one-bar-early true range",
     "fast, slow = _atr(true_range, FAST), _atr(true_range, SLOW)",
     "fast, slow = _atr(true_range.shift(-1), FAST), _atr(true_range, SLOW)"),
    ("base-lead", "the loop reads tomorrow's ratio",
     "vol = Series(_volatmeter(base.to_numpy(dtype=float)), "
     "index=close.index)",
     "vol = Series(_volatmeter(base.shift(-1).to_numpy(dtype=float)), "
     "index=close.index)"),
    ("loop-lead", "the feedback term reads base[T+1] instead of vol[T-1]",
     "near = out[i - NEAR] if i >= NEAR else np.nan",
     "near = values[i + NEAR] if i + NEAR < len(values) else np.nan"),
    ("output-early", "the whole column shifted one bar earlier",
     "    vol = vol.where(base.shift(FAR).notna())",
     "    vol = vol.where(base.shift(FAR).notna()).shift(-1)"),
]

#: Not a causality mutant: the module's one guard, removed, to price what it
#: buys (§A2, §G3).
DIVISOR_GUARD_OFF = ("slow.where(slow > 0.0)", "slow")


def _mutant(old, new):
    src = SOURCE.read_text(encoding="utf-8")
    assert src.count(old) == 1, f"{old!r} occurs {src.count(old)} times"
    ns = {}
    exec(compile(src.replace(old, new), "<mutant>", "exec"), ns)
    return ns["j_damiani"]


#: The 36 perturbation points of the blind causality sweep: the last 36 bars
#: a future can start at. Each one is "change every bar >= J and see whether
#: any bar < J moves".
OFFSETS = list(range(N - 36, N))


def _future_sweep(fn, frame, offsets=None, factor=1.03):
    """How many of `offsets` the function is CAUGHT reading the future at."""
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
    print("A hand-written true range, a hand-written Wilder recursion and a")
    print("hand-written feedback loop, sharing no code with the module. An")
    print("independent spelling is NOT OBLIGED to round the same way --")
    print("pandas' `ewm` divides by `(1 - alpha) + alpha` -- so the test")
    print("asserts a bound rather than bit-equality.")
    print()
    print("⚠ The oracle has NO NaN handling: it is the formula as the issue")
    print("   writes it, so it is only comparable on frames whose `base`")
    print("   never goes NaN. `flat` and `flat-start` are measured against")
    print("   the prototype in A2 instead, and their masks in A3/C.")
    print()
    print(f"{'frame':<14} {'masks':>5} {'bars':>6} {'bit-eq':>7} "
          f"{'max |diff|':>12} {'max |rel|':>11}")
    worst = 0.0
    for name in VARYING:
        frame = FRAMES[name]()
        masks, shared, same, d, rel = _agree(j_damiani(*frame), _oracle(*frame))
        worst = max(worst, 0.0 if np.isnan(rel) else rel)
        print(f"{name:<14} {str(masks):>5} {shared:>6} {same:>7} "
              f"{d:>12.3e} {rel:>11.3e}")
    print()
    print(f"worst relative difference over the six frames: {worst:.3e}")
    print()
    print("the three legs on their own, on the walk (bit-equality of each):")
    h, l, c = FRAMES["walk"]()
    prev = c.shift(1)
    tr_mod = concat([h - l, (h - prev).abs(), (l - prev).abs()],
                    axis=1).max(axis=1)
    tr_or = Series(_tr_oracle(h, l, c), index=c.index)
    print(f"  true range            bit-equal on "
          f"{int((tr_mod == tr_or).sum())} of {tr_mod.size} bars")
    for length in (FAST, SLOW):
        a = tr_mod.ewm(alpha=1.0 / length, adjust=False).mean()
        b = Series(_wilder_oracle(tr_or.to_numpy(), length), index=c.index)
        print(f"  ATR({length:2d})               bit-equal on "
              f"{int((a == b).sum())} of {a.size} bars, max |diff| "
              f"{float((a - b).abs().max()):.3e}")
    for length in (FAST, SLOW):
        a = 1.0 / length
        print(f"  (1 - 1/{length:2d}) + 1/{length:2d} == 1.0 exactly: "
              f"{(1.0 - a) + a == 1.0}")


def section_A2():
    _head("A2 Gate A -- the screen prototype, bit for bit")
    print("The prototype shares the module's spelling of ATR (pandas' `ewm`)")
    print("and its loop, so this limb is EXACT, and it is the limb that ties")
    print("this port to the 2026-10-24 screen's Gate E figures. Run on all")
    print("eight frames, INCLUDING the two whose `base` goes NaN -- the")
    print("guards are what has to agree there, and they are the module's own")
    print("spelling rather than the prototype's `_fin`.")
    print()
    print(f"{'frame':<14} {'masks':>5} {'bars':>6} {'bit-eq':>7} "
          f"{'max |diff|':>12}")
    for name in FRAMES:
        frame = FRAMES[name]()
        masks, shared, same, d, _ = _agree(j_damiani(*frame),
                                           _prototype(*frame))
        print(f"{name:<14} {str(masks):>5} {shared:>6} {same:>7} {d:>12.3e}")
    print()
    print("and the guards, which are the only place the two spellings")
    print("differ at all. `divisor-off` is the module with")
    print("`slow.where(slow > 0.0)` removed, i.e. the prototype's bare")
    print("division; it must agree with the module everywhere:")
    unguarded = _mutant(*DIVISOR_GUARD_OFF)
    for name in FRAMES:
        frame = FRAMES[name]()
        masks, shared, same, d, _ = _agree(j_damiani(*frame),
                                           unguarded(*frame))
        print(f"  {name:<14} masks {str(masks):<5} bit-equal {same} of "
              f"{shared}, max |diff| {d:.3e}")


def section_A3():
    _head("A3 the warm-up is the LOOP's, and bar 0's ratio is exactly 1")
    print("Both EWMAs are seeded at the first true range, so `base` is")
    print("defined from bar 0 and base[0] = TR[0]/TR[0] = 1 exactly. The")
    print("column's NaNs on a clean frame are the loop's `vol[-3]` and")
    print("nothing else.")
    print()
    for name in VARYING + ["flat-start"]:
        h, l, c = FRAMES[name]()
        base = _base(h, l, c)
        col = j_damiani(h, l, c)
        first = int(col.notna().to_numpy().argmax())
        print(f"  {name:<14} base[0] {base.iloc[0]!r:<22} "
              f"base NaN {int(base.isna().sum()):>3}  "
              f"column first fired bar {first:>3}, NaN "
              f"{int(col.isna().sum()):>3}, fired {int(col.notna().sum()):>5}"
              f" of {col.size}")
    print()
    print("the three masked bars are COMPUTED and then dropped -- they are")
    print("what bar 3 recurses from. Bar 3 of the walk, three ways:")
    h, l, c = FRAMES["walk"]()
    base = _base(h, l, c)
    raw = Series(_loop(base.to_numpy()), index=c.index)
    col = j_damiani(h, l, c)
    for i in range(5):
        print(f"  bar {i}: base {base.iloc[i]:.9f}  loop {raw.iloc[i]:.9f}  "
              f"column {col.iloc[i]}")
    print(f"  bar 3 == base[3] + 0.5*(loop[2] - loop[0]): "
          f"{col.iloc[3] == base.iloc[3] + LAG_S * (raw.iloc[2] - raw.iloc[0])}")
    print()
    print(f"MIN_BARS = {MIN_BARS} = SLOW + FAR, a floor on the INPUT:")
    short = j_damiani(h.iloc[:MIN_BARS - 1], l.iloc[:MIN_BARS - 1],
                      c.iloc[:MIN_BARS - 1])
    print(f"  a {MIN_BARS - 1}-bar frame returns {short}")
    ok = j_damiani(h.iloc[:MIN_BARS], l.iloc[:MIN_BARS], c.iloc[:MIN_BARS])
    print(f"  a {MIN_BARS}-bar frame fires on {int(ok.notna().sum())} bars")
    print(f"  and its values match the full frame's first {MIN_BARS} bars: "
          f"{bool((ok.dropna() == col.iloc[:MIN_BARS].dropna()).all())}")


def section_A4():
    _head("A4 WHICH ATR -- the smoother and the true range, priced")
    print("The issue says ATR13/ATR40 and the prototype spells it")
    print("`ewm(alpha=1/n, adjust=False)` over the plain three-way max,")
    print("seeded at bar 0. FOUR other readings are in reach, three of them")
    print("inside this fork, and this section is what choosing one costs.")
    print("⚠ jesse's own code is NOT read here -- jesse is not installed and")
    print("web access is unavailable -- so none of this is evidence about")
    print("what jesse computes.")
    print()
    for label, text, fn in (
        ("(a) SMA-seeded (wilder_rma / Pine ta.rma)",
         "same recursion, seeded with SMA(TR[:n]) at bar n-1",
         lambda h, l, c: _variant(h, l, c, _sma_seeded_atr)),
        ("(b) this fork's `rma`",
         "pandas' DEFAULT adjust=True, min_periods=n",
         lambda h, l, c: _variant(h, l, c, _fork_rma_atr)),
        ("(c) a PLAIN EMA",
         "alpha = 2/(n+1) -- reading 'ATR' as 'EMA of TR'",
         lambda h, l, c: _variant(h, l, c, _plain_ema_atr)),
        ("(d) this fork's `true_range`",
         "non_zero_range epsilon + bar 0 NaN, same smoother",
         _fork_tr_column),
        ("(e) this fork's `atr()` at its defaults",
         "mamode='rma' over the fork's true_range: both at once",
         _fork_atr_column),
    ):
        print(f"{label}")
        print(f"    {text}")
        print(f"{'frame':<14} {'masks':>5} {'shared':>7} {'bit-eq':>7} "
              f"{'max |diff|':>12} {'rho':>8}")
        for name in VARYING:
            frame = FRAMES[name]()
            base, other = j_damiani(*frame), fn(*frame)
            masks, shared, same, d, _ = _agree(base, other)
            print(f"{name:<14} {str(masks):>5} {shared:>7} {same:>7} "
                  f"{d:>12.3e} {_spearman(base, other):>8.4f}")
        print()
    print("(a) and (d) again, as convergences: a SEED difference is a")
    print("    WARM-UP difference and has to die. max |diff| over bars >= k")
    print("    on the walk and on range-bound, which are the best and the")
    print("    worst rho above:")
    for label, fn in (("(a) SMA-seeded",
                       lambda h, l, c: _variant(h, l, c, _sma_seeded_atr)),
                      ("(d) fork true_range", _fork_tr_column)):
        for name in ("walk", "range-bound"):
            frame = FRAMES[name]()
            base = j_damiani(*frame)
            other = fn(*frame)
            m = base.notna() & other.notna()
            diff = (base[m] - other[m]).abs().to_numpy()
            bars = np.arange(base.size)[m.to_numpy()]
            cells = []
            for k in (FAR, 50, 100, 200, 400, 800):
                tail = diff[bars >= k]
                cells.append(f"{k}: {tail.max():.1e}" if tail.size else "-")
            print(f"      {label:<20} {name:<12} " + "  ".join(cells))
            print(f"      {'':<20} {'':<12} against the column's own max "
                  f"|value| over those {int(m.sum())} shared bars: "
                  f"{base[m].abs().max():.4f}")
    print()
    print("(d) where the fork's true_range differs, exactly: how many bars")
    print("    of TR itself move, and whether any bar has high == low:")
    for name in FRAMES:
        h, l, c = FRAMES[name]()
        prev = c.shift(1)
        mine = concat([h - l, (h - prev).abs(), (l - prev).abs()],
                      axis=1).max(axis=1)
        theirs = true_range(h, l, c)
        m = mine.notna() & theirs.notna()
        print(f"  {name:<14} high == low on {int((h == l).sum()):>5} bars; "
              f"TR bit-equal on {int((mine[m] == theirs[m]).sum()):>5} of "
              f"{int(m.sum()):>5} shared, NaN masks equal "
              f"{bool((mine.isna() == theirs.isna()).all())}; "
              f"fired: module {int(j_damiani(h, l, c).notna().sum()):>5}, "
              f"fork TR {int(_fork_tr_column(h, l, c).notna().sum()):>5}")


def section_A5():
    _head("A5 the feedback loop IS the column -- a stable resonator")
    print("`vol[T] = base[T] + 0.5*(vol[T-1] - vol[T-3])` is an IIR filter")
    print("with transfer function 1 / (1 - 0.5 z^-1 + 0.5 z^-3). Five")
    print("things about it, measured rather than argued, because they are")
    print("what makes this column something other than an ATR ratio.")
    print()
    print("(a) STABILITY -- the characteristic roots of")
    print("    z^3 - 0.5 z^2 + 0.5 = 0:")
    roots = np.roots([1.0, -LAG_S, 0.0, LAG_S])
    for r in roots:
        print(f"      {r:+.6f}   |z| = {abs(r):.6f}")
    print(f"    largest |z| = {max(abs(r) for r in roots):.6f} "
          f"(< 1 means an impulse decays)")
    print()
    print("(b) GAIN -- |H(e^-iw)| over the frequency grid, and where it")
    print("    peaks. The DC gain is what says the loop leaves the mean")
    print("    level of the ratio alone:")
    w = np.linspace(1e-9, np.pi, 2_000_001)
    z = np.exp(-1j * w)
    gain = 1.0 / np.abs(1.0 - LAG_S * z + LAG_S * z ** 3)
    k = int(np.argmax(gain))
    print(f"      H(DC)      = {1.0 / abs(1.0 - LAG_S + LAG_S):.6f}")
    print(f"      peak |H|   = {gain[k]:.6f} at period "
          f"{2 * np.pi / w[k]:.4f} bars")
    print(f"      H(Nyquist) = {gain[-1]:.6f}")
    print()
    print("(c) the IMPULSE RESPONSE, run through the module's own loop, and")
    print("    how fast it dies:")
    imp = np.zeros(400)
    imp[0] = 1.0
    h_imp = _loop(imp)
    print("      k:      " + "  ".join(f"{v:>7.4f}" for v in h_imp[:8]))
    for k in (0, 10, 50, 100, 200, 300):
        print(f"      max |h| over k >= {k:>3}: {np.abs(h_imp[k:]).max():.3e}")
    print(f"      sum |h| = {np.abs(h_imp).sum():.6f}")
    print()
    print("(d) and what DROPPING the loop would cost: the bare ATR ratio")
    print("    against the shipped column. This is the loop's whole")
    print("    contribution to the column's identity -- and it is a")
    print("    RESHAPING rather than a re-ranking, which is a disclosure")
    print("    and not a defence.")
    print(f"{'frame':<14} {'shared':>7} {'bit-eq':>7} {'max |diff|':>12} "
          f"{'rho':>8}")
    for name in VARYING:
        frame = FRAMES[name]()
        col = j_damiani(*frame)
        bare = _base(*frame).where(col.notna())
        _, shared, same, d, _ = _agree(col, bare)
        print(f"{name:<14} {shared:>7} {same:>7} {d:>12.3e} "
              f"{_spearman(col, bare):>8.4f}")
    print()
    print("(e) so the column IS bounded, and here is the envelope. `base`")
    print("    is a ratio of two weighted means of the SAME true ranges")
    print("    whose weights each sum to 1, so it cannot exceed the largest")
    print("    ratio of those weights -- which is at lag 0, SLOW/FAST:")
    pos = float(h_imp[h_imp > 0].sum())
    neg = float(h_imp[h_imp < 0].sum())
    bound = SLOW / FAST
    print(f"      sup base            = SLOW/FAST = {bound:.6f}")
    print(f"      sum h+ = {pos:.6f}, sum h- = {neg:.6f}")
    print(f"      so J_DAMIANI in ({bound * neg:.4f}, {bound * pos:.4f})")
    print("    the supremum of `base` is ATTAINED, not approached: on a")
    print("    frame that is flat and then moves, the first moving bar is")
    print("    the only non-zero true range, so every weight but lag 0 hits")
    print("    a zero and the ratio is SLOW/FAST -- to within a rounding of")
    print("    the division, which is the honest form of that sentence:")
    h, l, c = FRAMES["flat-start"]()
    base = _base(h, l, c)
    hit = float(base.iloc[FLAT_PREFIX])
    print(f"      flat-start base[{FLAT_PREFIX}] = {hit!r}")
    print(f"      SLOW/FAST              = {bound!r}")
    print(f"      bit-equal {hit == bound}, relative difference "
          f"{abs(hit - bound) / bound:.3e}, i.e. "
          f"{round(abs(hit - bound) / np.spacing(bound))} ulp")
    print(f"      max base over all eight frames: "
          f"{max(float(_base(*FRAMES[n]()).max()) for n in FRAMES if n != 'flat'):.6f}")
    print("    and what the frames actually reach, against that envelope:")
    allv = pd.concat([j_damiani(*FRAMES[n]()).dropna() for n in FRAMES
                      if n != "flat"])
    print(f"      {allv.size} bars, min {allv.min():.6f}, "
          f"max {allv.max():.6f}  (envelope {bound * neg:.4f} .. "
          f"{bound * pos:.4f})")


def section_B():
    _head("B Gate B -- the mutants, and the blind sweep")
    print(f"{len(OFFSETS)} perturbation points (bars {OFFSETS[0]}..{OFFSETS[-1]}),")
    print("every bar >= J multiplied by 1.03. Caught = some bar < J moved.")
    print()
    print("⚠ 1.03 on high, low AND close is not a global rescale -- the")
    print("   column is invariant under one of those (that is Gate D) -- it")
    print("   is a rescale of a SUFFIX, which moves the true range at bar J")
    print("   and so is visible to a column that reads ahead.")
    print()
    frames = {n: FRAMES[n]() for n in VARYING}
    print("the SHIPPED module, which must be caught nowhere:")
    for name, frame in frames.items():
        print(f"  {name:<14} caught {_future_sweep(j_damiani, frame):>2} of "
              f"{len(OFFSETS)}")
    print()
    for label, what, old, new in MUTANTS:
        fn = _mutant(old, new)
        print(f"{label} -- {what}")
        for name, frame in frames.items():
            base, mut = j_damiani(*frame), fn(*frame)
            m = base.notna() & mut.notna()
            moved = int((base[m] != mut[m]).sum())
            live = moved > 0 or not bool((base.isna() == mut.isna()).all())
            caught = _future_sweep(fn, frame)
            print(f"  {name:<14} live {str(live):<5} moved {moved:>5} of "
                  f"{int(m.sum()):>5}  caught {caught:>2} of {len(OFFSETS)}")
        print()
    print("B1 and at ONE offset, how much the blind sweep actually sees --")
    print("   bars < J that move, and by how much, for each mutant on the")
    print("   walk. A mutant caught at 36 of 36 is not necessarily caught")
    print("   LOUDLY, and a quiet one is a thing to know:")
    frame = frames["walk"]
    h, l, c = frame
    for label, _, old, new in MUTANTS:
        fn = _mutant(old, new)
        base = fn(h, l, c)
        for j in (OFFSETS[0], OFFSETS[-1]):
            f = Series(np.where(np.arange(c.size) >= j, 1.03, 1.0),
                       index=c.index)
            out = fn(h * f, l * f, c * f)
            a, b = base.iloc[:j], out.iloc[:j]
            m = a.notna() & b.notna()
            moved = int((a[m] != b[m]).sum())
            d = float((a[m] - b[m]).abs().max())
            print(f"   {label:<14} J={j} moved {moved:>3} bar(s) of "
                  f"{int(m.sum())}, max |diff| {d:.3e}")


def section_C():
    _head("C Gate C -- reachability on synthetic frames")
    print("Real-data counts are owed with the Gate E run (the launcher's).")
    print()
    print(f"{'frame':<14} {'fired':>6} {'of':>6} {'distinct':>9} "
          f"{'>1':>6} {'<1':>6} {'min':>11} {'max':>11} {'median':>9}")
    for name in FRAMES:
        col = j_damiani(*FRAMES[name]())
        v = col.dropna()
        if not v.size:
            print(f"{name:<14} {v.size:>6} {col.size:>6} "
                  f"{'-':>9} {'-':>6} {'-':>6} {'-':>11} {'-':>11} {'-':>9}")
            continue
        print(f"{name:<14} {v.size:>6} {col.size:>6} {v.nunique():>9} "
              f"{int((v > 1).sum()):>6} {int((v < 1).sum()):>6} "
              f"{v.min():>11.4f} {v.max():>11.4f} {v.median():>9.4f}")
    print()
    print("the flat frame reads NOTHING, and that is the honest answer:")
    h, l, c = FRAMES["flat"]()
    base = _base(h, l, c)
    print(f"  TR == 0 on all {int((_tr_oracle(h, l, c) == 0.0).sum())} bars, "
          f"so ATR(13) == ATR(40) == 0 and the ratio is 0/0")
    print(f"  base NaN on {int(base.isna().sum())} of {base.size} bars; "
          f"column fired {int(j_damiani(h, l, c).notna().sum())}")
    print()
    print("the flat-START frame fires late, by the same mechanism:")
    h, l, c = FRAMES["flat-start"]()
    col = j_damiani(h, l, c)
    base = _base(h, l, c)
    print(f"  first {FLAT_PREFIX} bars flat -> base NaN on "
          f"{int(base.isna().sum())} bars, first defined bar "
          f"{int(base.notna().to_numpy().argmax())}")
    print(f"  column first fired bar {int(col.notna().to_numpy().argmax())}, "
          f"fired {int(col.notna().sum())} of {col.size}")
    print()
    print("what the frames actually REACH, which is much narrower than the")
    print("envelope §A5(e) derives -- (-5.5360, 8.6129) there, and this")
    print("here. Neither is a bounded oscillator's [0, 100]:")
    allv = pd.concat([j_damiani(*FRAMES[n]()).dropna() for n in VARYING])
    print(f"  pooled {allv.size} bars over the six varying frames, "
          f"min {allv.min():.6f}, max {allv.max():.6f}, "
          f"mean {allv.mean():.6f}")
    for lo, hi in ((0.25, 2.5), (0.5, 2.0), (0.0, 1e9)):
        print(f"  inside {lo} .. {hi}: "
              f"{int(((allv >= lo) & (allv <= hi)).sum())} of {allv.size}")
    print(f"  negative readings: {int((allv < 0).sum())} of {allv.size}")


def section_D():
    _head("D Gate D -- scale-free")
    print("D1 x8 / x64, which are EXACT in binary and must be bit-identical:")
    print(f"{'frame':<14} {'factor':>7} {'masks':>5} {'bars':>6} "
          f"{'bit-eq':>7} {'max |diff|':>12}")
    for name in FRAMES:
        frame = FRAMES[name]()
        base = j_damiani(*frame)
        for factor in (8.0, 64.0):
            masks, shared, same, d, _ = _agree(
                base, j_damiani(*_scaled(frame, factor)))
            print(f"{name:<14} {factor:>7.0f} {str(masks):>5} {shared:>6} "
                  f"{same:>7} {d:>12.3e}")
    print()
    print("D2 x10 / x3.7 / x0.1 / x1.0000001, which are NOT exact:")
    print(f"{'frame':<14} {'factor':>10} {'masks':>5} {'bit-eq':>7} "
          f"{'of':>6} {'max |rel|':>11}")
    worst = 0.0
    for name in VARYING:
        frame = FRAMES[name]()
        base = j_damiani(*frame)
        for factor in (10.0, 3.7, 0.1, 1.0000001):
            masks, shared, same, _, rel = _agree(
                base, j_damiani(*_scaled(frame, factor)))
            worst = max(worst, 0.0 if np.isnan(rel) else rel)
            print(f"{name:<14} {factor:>10.7f} {str(masks):>5} {same:>7} "
                  f"{shared:>6} {rel:>11.3e}")
    print()
    print(f"worst relative difference: {worst:.3e}")
    print()
    print("D3 the same at extreme price LEVELS, x8 / x64 again. `finite`")
    print("    counts the fired bars that are not inf -- §G5 cites it, and")
    print("    `fired` alone cannot carry that claim because an infinity is")
    print("    not NaN:")
    for level in (1e-6, 1e+6, 1e+100):
        frame = _walk(level=level)
        base = j_damiani(*frame)
        row = []
        for factor in (8.0, 64.0):
            _, shared, same, _, _ = _agree(base,
                                           j_damiani(*_scaled(frame, factor)))
            row.append(f"x{factor:.0f}: {same} of {shared}")
        fired = base.dropna().to_numpy()
        print(f"  level {level:>8.0e}  " + "   ".join(row)
              + f"   fired {fired.size}"
              + f"   finite {int(np.isfinite(fired).sum())}")
    print()
    print("D4 0 < fires < n, so a constant cannot pass Gate D by being")
    print("    invariant. ⚠ The FLAT frame fires nowhere -- 0/0 -- so this")
    print("    is a claim about the six varying frames and the flat-start")
    print("    one, and the flat frame is §C's separate pin:")
    for name in FRAMES:
        col = j_damiani(*FRAMES[name]())
        fires = int(col.notna().sum())
        print(f"  {name:<14} 0 < {fires:>5} < {col.size}: "
              f"{0 < fires < col.size}")


#: Bars a planted bad price is dropped at, in §G1/§G2. Several, because ONE
#: is luck: a NaN high removes two of the true range's three legs, and
#: whether that moves the bar at all depends on which leg was the max there.
PLANTS = (100, 400, 700, 1000, 1200)


def section_G():
    _head("G guards -- bad prices, the bound, and what the one guard buys")
    frame = FRAMES["walk"]()
    h, l, c = frame
    base = j_damiani(*frame)
    print("G1 a bad price EMPTIES NO BAR, and that is the first surprise.")
    print("    A NaN in one leg does not NaN the true range: the three-way")
    print("    max skips it and the surviving legs still answer (bar 0 is")
    print("    the exception -- there is no previous close, so high or low")
    print("    alone decides it). And `ewm` skips a NaN observation rather")
    print("    than poisoning the tail. So a bad price perturbs the column")
    print("    instead of holing it -- recursively, because all three legs")
    print("    are inside the two EWMAs, which makes the claim two-sided:")
    print("    bars BEFORE it are bit-identical, and the contamination")
    print("    decays with the slow filter's memory.")
    print()
    print(f"    planted at bars {list(PLANTS)}; `moved` counts the bars that")
    print("    change at all, and the k columns are max |rel change| over")
    print("    bars >= J + k, worst over those five plants:")
    print()
    print(f"{'leg':<7} {'planted':>9} {'pre bit-eq':>11} {'emptied':>8} "
          f"{'moved':>12} {'k=0':>10} {'k=50':>10} {'k=100':>10} {'k=300':>10}")
    for leg, bad in (("high", np.nan), ("high", np.inf), ("low", np.nan),
                     ("low", -np.inf), ("close", np.nan), ("close", np.inf)):
        pre_ok, emptied, moved, tops = True, 0, [], [0.0, 0.0, 0.0, 0.0]
        for j in PLANTS:
            h2, l2, c2 = h.copy(), l.copy(), c.copy()
            {"high": h2, "low": l2, "close": c2}[leg].iloc[j] = bad
            out = j_damiani(h2, l2, c2)
            pre, pre_out = base.iloc[:j], out.iloc[:j]
            m0 = pre.notna() & pre_out.notna()
            pre_ok &= bool((pre[m0] == pre_out[m0]).all())
            emptied = max(emptied, int((base.notna() & out.isna()).sum()))
            m = base.notna() & out.notna()
            moved.append(int((base[m] != out[m]).sum()))
            rel = ((base[m] - out[m]).abs()
                   / base[m].abs().where(base[m].abs() > 0, np.nan)).to_numpy()
            bars = np.arange(base.size)[m.to_numpy()]
            for i, k in enumerate((0, 50, 100, 300)):
                if (bars >= j + k).any():
                    tops[i] = max(tops[i], float(np.nanmax(rel[bars >= j + k])))
        print(f"{leg:<7} {bad!r:>9} {str(pre_ok):>11} {emptied:>8} "
              f"{min(moved):>5}..{max(moved):<6} "
              + " ".join(f"{t:>10.3e}" for t in tops))
    print()
    print("G2 an INFINITE price never reaches the output, and this is what")
    print("    says so rather than an argument: `high - low` at an infinite")
    print("    high IS `inf`, so the true range at that bar is infinite --")
    print("    and pandas converts an infinity to NaN before the `ewm`")
    print("    kernel, which then SKIPS it, carrying the previous smoothed")
    print("    value. ⚠ This is a pandas BEHAVIOUR the module relies on, so")
    print("    a test pins it: without it the column would ship `inf`.")
    print()
    print("    ⚠ It is NOT the same as planting a NaN, and the naive claim")
    print("    that it is would have been wrong: a NaN leaves the surviving")
    print("    legs of the max intact, an infinity wins the max. `vs NaN`")
    print("    is how far apart the two readings are.")
    print()
    print(f"{'leg':<7} {'planted':>9} {'fired':>7} {'finite':>7} "
          f"{'infinite':>9} {'vs NaN max |diff|':>18}")
    for leg in ("high", "low", "close"):
        for bad in (np.inf, -np.inf):
            for j in (PLANTS[2],):
                cols = []
                for value in (bad, np.nan):
                    h2, l2, c2 = h.copy(), l.copy(), c.copy()
                    {"high": h2, "low": l2, "close": c2}[leg].iloc[j] = value
                    cols.append(j_damiani(h2, l2, c2))
                _, shared, _, d, _ = _agree(*cols)
                v = cols[0].dropna().to_numpy()
                print(f"{leg:<7} {bad!r:>9} {v.size:>7} "
                      f"{int(np.isfinite(v).sum()):>7} "
                      f"{int(np.isinf(v).sum()):>9} {d:>18.3e}")
    print()
    print("    and the true range itself, at the planted bar:")
    for leg in ("high", "low", "close"):
        h2, l2, c2 = h.copy(), l.copy(), c.copy()
        {"high": h2, "low": l2, "close": c2}[leg].iloc[PLANTS[2]] = np.inf
        prev = c2.shift(1)
        tr = concat([h2 - l2, (h2 - prev).abs(), (l2 - prev).abs()],
                    axis=1).max(axis=1)
        atr_f = tr.ewm(alpha=1.0 / FAST, adjust=False).mean()
        print(f"      inf {leg:<6}: TR infinite on "
              f"{int(np.isinf(tr.to_numpy()).sum())} bar(s), NaN on "
              f"{int(tr.isna().sum())}; ATR({FAST}) infinite on "
              f"{int(np.isinf(atr_f.to_numpy()).sum())}, NaN on "
              f"{int(atr_f.isna().sum())}")
    print()
    print("G3 the one guard, `slow.where(slow > 0.0)`. It changes no reading")
    print("    ON THESE EIGHT FRAMES -- §A2 measures it bit-equal to the")
    print("    bare division on all of them; (d) below is the regime where")
    print("    removing it ships an `inf`, so this is not dead code --")
    print("    so what it buys HERE has to be stated exactly:")
    print("    the 0/0 of a frame with no movement is decided HERE rather")
    print("    than inside pandas. Measured below: today's pandas evaluates")
    print("    that division and suppresses numpy's invalid-operation flag")
    print("    itself, so the unguarded form survives too. The guard is what")
    print("    makes that independent of a pandas internal:")
    unguarded = _mutant(*DIVISOR_GUARD_OFF)
    for label, fn in (("module   ", j_damiani), ("unguarded", unguarded)):
        for name in ("flat", "walk"):
            fr = FRAMES[name]()
            try:
                with np.errstate(all="raise"):
                    out = fn(*fr)
                said = f"fired {int(out.notna().sum())}, raised nothing"
            except Exception as exc:                      # noqa: BLE001
                said = f"{type(exc).__name__}: {exc}"
            print(f"    {label} on {name:<11} {said}")
    print("    the bare ratio, under the same errstate, to show WHICH")
    print("    operation the flag would come from:")
    hf, lf, cf = FRAMES["flat"]()
    prev = cf.shift(1)
    trf = concat([hf - lf, (hf - prev).abs(), (lf - prev).abs()],
                 axis=1).max(axis=1)
    a, b = (trf.ewm(alpha=1.0 / FAST, adjust=False).mean(),
            trf.ewm(alpha=1.0 / SLOW, adjust=False).mean())
    try:
        with np.errstate(all="raise"):
            r = a / b
        said = f"NaN on {int(r.isna().sum())} of {r.size}, raised nothing"
    except Exception as exc:                              # noqa: BLE001
        said = f"{type(exc).__name__}: {exc}"
    print(f"    pandas  `fast / slow` on flat: {said}")
    try:
        with np.errstate(all="raise"):
            r = a.to_numpy() / b.to_numpy()
        said = f"NaN on {int(np.isnan(r).sum())} of {r.size}, raised nothing"
    except Exception as exc:                              # noqa: BLE001
        said = f"{type(exc).__name__}: {exc}"
    print(f"    numpy   `fast / slow` on flat: {said}")
    print()
    print("G4 degenerate frames -- all-NaN, all-zero, all-negative, and a")
    print("    frame of one repeated price. Every bar NaN, nothing raised:")
    idx = date_range("2020-01-01", periods=60, freq="h")
    for value in (np.nan, 0.0, -5.0, 100.0):
        s = Series(np.full(60, value), index=idx)
        try:
            with np.errstate(all="raise"):
                out = j_damiani(s.copy(), s.copy(), s.copy())
            said = (f"fired {int(out.notna().sum())} of {out.size}, "
                    f"finite {int(np.isfinite(out.dropna().to_numpy()).sum())}")
        except Exception as exc:                          # noqa: BLE001
            said = f"{type(exc).__name__}: {exc}"
        print(f"    all {value!r:<6} -> {said}")
    print()
    print("G5 NO guard on the division's RESULT, and why. §A5(e) bounds the")
    print("    ratio by SLOW/FAST in EXACT arithmetic; these four")
    print("    adversarial frames are what that is worth. (a) .. (c) find no")
    print("    overflow; (d) finds both the bound's real exception and the")
    print("    one infinity the DIVISOR guard already removes:")
    print()
    print("    (a) a first bar whose high - low OVERFLOWS to inf, then a")
    print("        normal walk. The infinite true range is skipped, so the")
    print("        column is finite:")
    n = 600
    hw, lw, cw = _walk(n=n)
    h2, l2 = hw.copy(), lw.copy()
    h2.iloc[0], l2.iloc[0] = 1e+308, -1e+308
    out = j_damiani(h2, l2, cw)
    v = out.dropna().to_numpy()
    with np.errstate(over="ignore"):
        tr0 = float(h2.iloc[0] - l2.iloc[0])
    print(f"        TR[0] = {tr0}; fired {v.size} "
          f"of {n}, finite {int(np.isfinite(v).sum())}, max "
          f"{v.max() if v.size else float('nan'):.6f}")
    print("    (b) the cross-scale frame: high/low at 1e+300 against a close")
    print("        at 1e-300. The close only enters through the gap legs, so")
    print("        the ratio does not care about its scale:")
    h3, l3, _ = _walk(n=60, level=1e+300)
    tinyc = Series(np.full(60, 1e-300), index=h3.index)
    out = j_damiani(h3, l3, tinyc)
    v = out.dropna().to_numpy()
    print(f"        fired {v.size} of 60, finite "
          f"{int(np.isfinite(v).sum())}, max "
          f"{v.max() if v.size else float('nan'):.6f}")
    print("    (c) a huge bar followed by nothing at all, which is where a")
    print("        divisor could UNDERFLOW while its numerator had not. It")
    print("        is the numerator that underflows first -- the fast ATR")
    print("        forgets faster -- so the ratio falls to 0 and then to")
    print("        0/0, never to inf:")
    n2 = 32_000
    idx2 = date_range("2020-01-01", periods=n2, freq="h")
    hi = np.full(n2, 1.0)
    hi[0] = 1e+16
    hh = Series(hi, index=idx2)
    ll = Series(np.full(n2, 1.0), index=idx2)
    cc = Series(np.full(n2, 1.0), index=idx2)
    prev = cc.shift(1)
    tr2 = concat([hh - ll, (hh - prev).abs(), (ll - prev).abs()],
                 axis=1).max(axis=1)
    f2 = tr2.ewm(alpha=1.0 / FAST, adjust=False).mean()
    s2 = tr2.ewm(alpha=1.0 / SLOW, adjust=False).mean()
    col2 = j_damiani(hh, ll, cc)
    print(f"{'bar':>7} {'ATR(13)':>12} {'ATR(40)':>12} {'base':>12} "
          f"{'column':>12}")
    for bar in (1, 1_000, 5_000, 10_000, 20_000, 29_000, 31_999):
        bv = f2.iloc[bar] / s2.iloc[bar] if s2.iloc[bar] > 0 else float("nan")
        print(f"{bar:>7} {f2.iloc[bar]:>12.3e} {s2.iloc[bar]:>12.3e} "
              f"{bv:>12.3e} {col2.iloc[bar]:>12.3e}")
    nz = np.flatnonzero((f2.to_numpy() == 0.0))
    nzs = np.flatnonzero((s2.to_numpy() == 0.0))
    print(f"        ATR(13) reaches exactly 0 at bar "
          f"{int(nz[0]) if nz.size else None}, ATR(40) at bar "
          f"{int(nzs[0]) if nzs.size else None} -- neither does: a")
    print("        subnormal times 0.975 rounds back to itself, so both")
    print("        STALL just above zero instead of reaching it.")
    b2 = f2 / s2.where(s2 > 0.0)
    print(f"        max base on this frame {float(b2.max()):.6f} "
          f"(SLOW/FAST = {SLOW / FAST:.6f}); exceeds it: "
          f"{bool(float(b2.max()) > SLOW / FAST)}")
    print("        ⚠ The stall is the OBVIOUS candidate for breaking the")
    print("        exact-arithmetic bound of §A5(e) -- a numerator stuck at")
    print("        the subnormal floor over a denominator still falling --")
    print("        and on this frame it does not: the numerator is pinned")
    print("        at the 2.964e-323 printed above while the denominator")
    print("        falls from 9.750e+15 to the 9.387e-323 printed above, so")
    print("        the ratio stays under 1.2 throughout. (d) is where the")
    print("        bound actually breaks:")
    print(f"        column: fired {int(col2.notna().sum())} of {n2}, "
          f"infinite {int(np.isinf(col2.to_numpy()).sum())}, "
          f"max {float(col2.max()):.6f}, min {float(col2.min()):.3e}")
    print()
    print("    (d) where the weight bound DOES break, and it is not the stall")
    print("        above: a true range of a few ULPS. Subnormal")
    print("        multiplication rounds ABSOLUTELY, so `1/13 * k` and")
    print("        `1/40 * k` both round to a whole number of ulps and their")
    print("        ratio is whatever those two integers say. A frame flat for")
    print("        a while and then moving by k ulps:")
    print()
    print(f"{'k (ulps)':>9} {'ATR(13)/ulp':>12} {'ATR(40)/ulp':>12} "
          f"{'base':>10} {'> SLOW/FAST':>12} {'column max':>11} "
          f"{'UNGUARDED base':>15}")
    ulp = np.nextafter(0.0, 1.0)
    n3 = 200
    idx3 = date_range("2020-01-01", periods=n3, freq="h")
    worst = 0.0
    infs = 0
    for k in (1, 3, 7, 13, 40, 59, 100, 1000):
        hi3 = np.zeros(n3)
        hi3[FLAT_PREFIX] = k * ulp
        hh3 = Series(hi3, index=idx3)
        zz3 = Series(np.zeros(n3), index=idx3)
        prev3 = zz3.shift(1)
        tr3 = concat([hh3 - zz3, (hh3 - prev3).abs(), (zz3 - prev3).abs()],
                     axis=1).max(axis=1)
        f3 = tr3.ewm(alpha=1.0 / FAST, adjust=False).mean()
        s3 = tr3.ewm(alpha=1.0 / SLOW, adjust=False).mean()
        b3 = f3 / s3.where(s3 > 0.0)
        with np.errstate(divide="ignore", invalid="ignore"):
            raw3 = f3.to_numpy() / s3.to_numpy()
        col3 = j_damiani(hh3, zz3, zz3)
        top = float(b3.max())
        worst = max(worst, 0.0 if np.isnan(top) else top)
        rawtop = (float(np.nanmax(raw3)) if np.isfinite(raw3).any()
                  or np.isinf(raw3).any() else float("nan"))
        infs += int(np.isinf(raw3).sum())
        print(f"{k:>9} {f3.iloc[FLAT_PREFIX] / ulp:>12.1f} "
              f"{s3.iloc[FLAT_PREFIX] / ulp:>12.1f} {top:>10.4f} "
              f"{str(top > SLOW / FAST):>12} "
              f"{float(col3.max()) if int(col3.notna().sum()) else float('nan'):>11.4f} "
              f"{rawtop:>15.4f}")
    print(f"        worst `base` over those: {worst:.6f} against "
          f"SLOW/FAST = {SLOW / FAST:.6f}")
    print("        ⚠ TWO findings here, and both correct a claim this")
    print("        receipt made before measuring it.")
    print("        1. The weight bound of §A5(e) is EXACT-ARITHMETIC, and")
    print("           THIS is where floating point breaks it -- not the")
    print("           stall of (c). Subnormal multiplication rounds")
    print("           ABSOLUTELY, so 1/13 and 1/40 of k ulps both round to")
    print("           whole ulps and the ratio is whatever those two")
    print("           integers say: 5/1 at k = 59.")
    print("        2. The divisor guard is NOT a no-op after all. At k <= 13")
    print("           the slow ATR rounds to ZERO while the fast one does")
    print(f"           not, and the UNGUARDED column reads `inf` ({infs} bars")
    print("           over these eight frames). The guard turns that into")
    print("           NaN, which is why no overflow guard is needed.")
    print()
    print("G6 so WHERE can `base` be NaN at all? Only on a LEADING run of")
    print("    bars -- while the SLOW ATR is still exactly 0, which means")
    print("    either nothing has moved yet or (G5(d)) everything that has")
    print("    moved rounded to zero at subnormal scale. A Wilder EWMA of")
    print("    non-negative observations that is positive once stays")
    print("    positive -- §G5(c) measures the one thing that could end")
    print("    that, an underflow, STALLING above zero rather than reaching")
    print("    it -- so there are no mid-series holes and the column's NaNs")
    print("    are always a prefix:")
    for name in FRAMES:
        col = j_damiani(*FRAMES[name]())
        nan_bars = np.flatnonzero(col.isna().to_numpy())
        contiguous = (nan_bars.size == 0
                      or bool((nan_bars == np.arange(nan_bars.size)).all()))
        print(f"    {name:<14} NaN on {nan_bars.size:>4} bars, a leading "
              f"prefix: {contiguous}")
    print(f"    and on the {n2}-bar underflow frame of (c): NaN on "
          f"{int(col2.isna().sum())} bars, a leading prefix: "
          f"{bool((np.flatnonzero(col2.isna().to_numpy()) == np.arange(int(col2.isna().sum()))).all())}")
    print("    and on the adversarial frame for the sentence above -- 7 ulps")
    print("    of movement at bar 50 (which rounds the slow ATR to zero),")
    print("    then a normal move at bar 100, so that the NaN run has to")
    print("    END somewhere in the middle of the frame:")
    hi5 = np.zeros(200)
    hi5[50] = 7 * np.nextafter(0.0, 1.0)
    hi5[100] = 1.0
    idx5 = date_range("2020-01-01", periods=200, freq="h")
    hh5 = Series(hi5, index=idx5)
    zz5 = Series(np.zeros(200), index=idx5)
    col5 = j_damiani(hh5, zz5, zz5)
    nan5 = np.flatnonzero(col5.isna().to_numpy())
    print(f"      NaN on {nan5.size} bars, a leading prefix: "
          f"{bool((nan5 == np.arange(nan5.size)).all())}; first fired bar "
          f"{int(col5.notna().to_numpy().argmax())}, fired "
          f"{int(col5.notna().sum())} of {col5.size}, infinite "
          f"{int(np.isinf(col5.to_numpy()).sum())}")
    print()
    print("    and the nearest thing to a mid-series hole a caller can")
    print("    reach: a bar whose high AND low are both NaN, which leaves")
    print("    the true range with no surviving leg at all. `ewm` skips")
    print("    that observation and the ATRs carry, so `base` still does")
    print("    not go NaN and the column still does not lose a bar:")
    h4, l4 = h.copy(), l.copy()
    h4.iloc[700], l4.iloc[700] = np.nan, np.nan
    b4 = _base(h4, l4, c)
    o4 = j_damiani(h4, l4, c)
    print(f"      base NaN on {int(b4.isna().sum())} bars; column fired "
          f"{int(o4.notna().sum())} of {o4.size}, max |rel change| vs clean "
          f"{_agree(base, o4)[4]:.3e}")


def section_L():
    _head("L in-fork overlap -- SYNTHETIC, a disclosure and not Gate E")
    print("Spearman |rho| against shipped fork columns on the six varying")
    print("frames. ⚠ This is NOT Gate E: Gate E is 687 ENGINE comparators")
    print("over 89 real BIST frames and the launcher runs it. These are")
    print("synthetic frames and a handful of neighbours, chosen as the")
    print("nearest questions this fork already answers.")
    print()
    print("⚠ What the 2026-10-24 screen measured on the PROTOTYPE, for")
    print("   contrast: max |rho| 0.7621 vs the engine's `ATR_Ratio_5_20`")
    print("   (n = 397,069), then `natr_percentile` 0.7302 and `natr_Pctl`")
    print("   0.7294 -- the DISCLOSE band. Its fork-overlap stage 2 put the")
    print("   nearest fork column at 0.7023 (`massi:MASSI_9_25`, 12 frames).")
    print()
    comparators = {
        "natr:NATR_14": lambda h, l, c: natr(h, l, c),
        "massi:MASSI_9_25": lambda h, l, c: massi(h, l),
        "chop:CHOP_14_1_100": lambda h, l, c: chop(h, l, c),
        "volvol": lambda h, l, c: volvol(h, l, c).iloc[:, 0]
        if hasattr(volvol(h, l, c), "columns") else volvol(h, l, c),
        "rvi:RVI_14": lambda h, l, c: rvi(c, h, l),
        "atr_ma_multiple:ATRMAX_14_50": atr_ma_multiple,
        "bare ATR(13)/ATR(40)": _base,
    }
    rows = {}
    for label, fn in comparators.items():
        rows[label] = []
        for name in VARYING:
            frame = FRAMES[name]()
            try:
                other = fn(*frame)
            except Exception as exc:                      # noqa: BLE001
                rows[label].append(float("nan"))
                print(f"  {label}: {type(exc).__name__}: {exc}")
                continue
            if isinstance(other, pd.DataFrame):
                other = other.iloc[:, 0]
            rows[label].append(abs(_spearman(j_damiani(*frame), other)))
    print(f"{'comparator':<30} " + " ".join(f"{n[:9]:>9}" for n in VARYING)
          + f" {'max':>8}")
    for label, vals in rows.items():
        print(f"{label:<30} " + " ".join(f"{v:>9.4f}" for v in vals)
              + f" {max(vals):>8.4f}")
    print()
    print("the two ratios this column is nearest to, by construction:")
    print("  `natr` is ATR/close -- a LEVEL of volatility, not a ratio of")
    print("  two horizons; `massi` sums EMA(range)/EMA(EMA(range)), which")
    print("  is the same fast-over-slow shape and is the screen's nearest")
    print("  fork column. The bare ratio row is §A5(d)'s, repeated here")
    print("  because the loop is what separates this column from it.")


def section_W():
    _head("W the dictionary's 150-character cut")
    print("`docs/gen_indicator_dictionary.py`'s `desc()` shows")
    print("`d[:150].rsplit(' ', 1)[0]` of the docstring's first paragraph,")
    print("and only when it EXCEEDS 150 characters -- so the budget is 150")
    print("and the penalty for passing it is a whole WORD.")
    print()
    import ast
    import re
    path = Path(__file__).resolve().parent / "gen_indicator_dictionary.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    fn = next(n for n in tree.body
              if isinstance(n, ast.FunctionDef) and n.name == "desc")
    ns = {"re": re}
    exec(compile(ast.Module(body=[fn], type_ignores=[]), "<desc>", "exec"), ns)
    desc = ns["desc"]
    body = []
    for line in j_damiani.__doc__.splitlines()[1:]:
        if line.strip():
            body.append(line.strip())
        elif body:
            break
    paragraph = " ".join(body)
    print(f"  paragraph: {paragraph!r}")
    print(f"  length {len(paragraph)}; survives whole: "
          f"{desc({'desc': paragraph}) == paragraph}")
    grown = paragraph
    for extra in range(0, 12):
        candidate = paragraph[:-1] + "x" * extra + paragraph[-1:]
        if desc({"desc": candidate}) != candidate:
            print(f"  loses a word at {len(candidate)} characters, i.e. "
                  f"{extra - 1} to spare")
            break
        grown = candidate
    else:
        print(f"  still whole at {len(grown)} characters")


def section_Z():
    _head("Z cost")
    print("⚠ Milliseconds are THIS machine's and this run's. best-of-5, and")
    print("   the point is the shape -- linear in bars, with a Python loop")
    print("   over them -- not the digits. ⚠ That covers everything DERIVED")
    print("   from them too: the loop's share below, the us/bar figures and")
    print("   the two-spelling ratio are quotients of timings that move, so")
    print("   the only numbers worth pinning here are the traced peak, the")
    print("   linear shape, the ordering, and the bit-identical output.")
    print()
    for n in (1_000, 10_000, 100_000, 400_000):
        frame = _walk(n=n)
        best = min(timeit.repeat(lambda: j_damiani(*frame), number=1,
                                 repeat=5))
        bare = min(timeit.repeat(lambda: _base(*frame), number=1, repeat=5))
        tracemalloc.start()
        j_damiani(*frame)
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        print(f"  {n:>7} bars: {best * 1e3:>8.2f} ms   "
              f"ratio only {bare * 1e3:>7.2f} ms   "
              f"loop {100 * (1 - bare / best):>5.1f}% of it   "
              f"peak {peak / 2 ** 20:>6.1f} MB")
    print()
    frame = _walk(n=400_000)
    per_bar = min(timeit.repeat(lambda: j_damiani(*frame), number=1,
                                repeat=3)) / 400_000 * 1e6
    print(f"  per bar, at 400,000 bars: {per_bar:.3f} us")
    print()
    print("  and what the loop's SPELLING costs, since it is half the run.")
    print("  `_volatmeter` works on Python floats and tests NaN with")
    print("  `x != x`; the obvious spelling keeps the numpy array and calls")
    print("  `np.isnan`. Both outputs, bit-for-bit, and both timings:")
    base = _base(*frame).to_numpy(dtype=float)
    a = _volatmeter(base)
    b = _volatmeter_numpy(base)
    same = bool((np.isnan(a) == np.isnan(b)).all()
                and (a[~np.isnan(a)] == b[~np.isnan(b)]).all())
    ta = min(timeit.repeat(lambda: _volatmeter(base), number=1, repeat=5))
    tb = min(timeit.repeat(lambda: _volatmeter_numpy(base), number=1,
                           repeat=5))
    print(f"    shipped: {ta * 1e3:>8.2f} ms   {ta / 400_000 * 1e6:.3f} us/bar")
    print(f"    np.isnan:{tb * 1e3:>8.2f} ms   {tb / 400_000 * 1e6:.3f} us/bar")
    print(f"    bit-identical outputs: {same}")


SECTIONS = {
    "A1": section_A1, "A2": section_A2, "A3": section_A3, "A4": section_A4,
    "A5": section_A5, "B": section_B, "C": section_C, "D": section_D,
    "G": section_G, "L": section_L, "W": section_W, "Z": section_Z,
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
