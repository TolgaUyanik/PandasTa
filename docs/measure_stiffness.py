# -*- coding: utf-8 -*-
"""STIFFNESS-60 (PandasTa issue #259): the numbers in
`docs/StiffnessMeasured.md`, except the ones that receipt names as
exceptions (pytest's counts, the repo's wiring counts, the asserted bounds).

    python docs/measure_stiffness.py          # every section, in order
    python docs/measure_stiffness.py A1 D2    # named sections only

One section per gate limb, printed and never derived: no figure may enter
the receipt, the module docstring or `tests/test_stiffness.py` except from a
section here or from one of the receipt's named exceptions.

    MA[T]    = mean(close[T-99..T])                               SMA 100
    S[T]     = std(close[T-99..T], ddof=0)
    above[T] = 1 if close[T] > MA[T] + 0.2 * S[T] else 0
    STIFF[T] = 100 * (above[T-59] + ... + above[T]) / 60

⚠ The millisecond figures of §Z are this machine's and this run's.
"""
import importlib.util
import platform
import sys
import timeit
from pathlib import Path

import numpy as np
import pandas as pd
from pandas import Series, date_range

from pandas_ta.overlap.ma_disparity import ma_disparity
from pandas_ta.overlap.sma import sma
from pandas_ta.statistics.stdev import stdev
from pandas_ta.statistics.zscore import zscore
from pandas_ta.momentum.psl import psl
from pandas_ta.trend.stiffness import (LENGTH, MA_LENGTH, MIN_BARS, STD_MULT,
                                       stiffness)

N = 1500
LEVEL = 100.0
#: The first bar that can fire on a clean frame.
WARMUP = MIN_BARS - 1
FIRED = N - WARMUP
#: The blind causality sweep's perturbation points.
OFFSETS = list(range(N - 36, N))
#: One step of the column: a single `above` bit entering or leaving.
STEP = 100.0 / LENGTH


# ------------------------------------------------------------------ frames
# The same builders and seeds as `tests/test_stiffness.py`, and the close
# legs of `docs/measure_j_kaufmanstop_dist.py`'s, so two ports measured on
# the same frames can be compared.


def _idx(n):
    return date_range("2020-01-01", periods=n, freq="h")


def _walk(seed=7, n=N, level=LEVEL, sigma=0.01):
    rng = np.random.default_rng(seed)
    return Series(level * np.exp(np.cumsum(rng.normal(0.0, sigma, n))),
                  index=_idx(n))


def _trend(seed=11, n=N, level=LEVEL):
    rng = np.random.default_rng(seed)
    return Series(level * np.exp(np.cumsum(rng.normal(0.003, 0.008, n))),
                  index=_idx(n))


def _range_bound(seed=13, n=N, level=LEVEL):
    rng = np.random.default_rng(seed)
    x = np.zeros(n)
    for i in range(1, n):
        x[i] = 0.9 * x[i - 1] + rng.normal(0.0, 0.02)
    return Series(level * np.exp(x), index=_idx(n))


def _grid(seed=17, n=N, level=LEVEL, tick=0.01):
    return np.round(_walk(seed, n, level) / tick) * tick


def _coarse(seed=31, n=N, level=LEVEL, tick=0.5):
    """Tick-rounded to half a point on a level of 100, so long runs of
    exactly equal closes occur -- the tie case."""
    return np.round(_walk(seed, n, level) / tick) * tick


def _heavy(seed=19, n=N, level=LEVEL):
    rng = np.random.default_rng(seed)
    return Series(level * np.exp(np.cumsum(rng.standard_t(2.0, n) * 0.006)),
                  index=_idx(n))


def _jump(seed=23, n=N, level=LEVEL):
    c = _walk(seed, n, level)
    return c * Series(np.where(np.arange(n) >= 700, 1.5, 1.0), index=c.index)


def _flat(n=N, level=LEVEL):
    return Series(np.full(n, level), index=_idx(n))


def _rising(n=N, level=LEVEL, step=0.001):
    return Series(level * (1.0 + step * np.arange(n)), index=_idx(n))


FRAMES = {
    "walk": _walk, "trend": _trend, "range-bound": _range_bound,
    "grid": _grid, "coarse": _coarse, "heavy-tailed": _heavy, "jump": _jump,
    "flat": _flat, "rising": _rising,
}
NAMES = list(FRAMES)
#: The frames on which the column takes more than one value. ⚠ `trend`
#: (drift 0.003/bar) is NOT one: it reads exactly 100 on every fired bar,
#: like `rising` (§C1).
VARYING = ["walk", "range-bound", "grid", "coarse", "heavy-tailed", "jump"]
SWEPT = ["walk", "range-bound", "heavy-tailed"]


def _frame(name):
    return FRAMES[name]()


def _col(name):
    return stiffness(_frame(name))


# ---------------------------------------------------------------- helpers


def _bit_equal(a, b):
    if not bool((a.isna() == b.isna()).all()):
        return False
    m = a.notna() & b.notna()
    return bool((a[m].to_numpy() == b[m].to_numpy()).all())


def _abs(a, b):
    m = a.notna() & b.notna()
    return float((a[m] - b[m]).abs().max()) if int(m.sum()) else float("nan")


def _spearman(a, b):
    m = a.notna() & b.notna()
    if int(m.sum()) < 3 or a[m].nunique() < 2 or b[m].nunique() < 2:
        return float("nan")
    return float(a[m].corr(b[m], method="spearman"))


def _differing_bars(a, b):
    m = a.notna() & b.notna()
    return int((a[m].to_numpy() != b[m].to_numpy()).sum())


# ---------------------------------------------------------------- oracles


def _oracle(close):
    """The issue's formula bar by bar over plain Python floats, sharing no
    code with the module: a naive 100-term mean, a two-pass population
    variance, and a 60-term count."""
    c = close.to_numpy(dtype=float).tolist()
    n = len(c)
    nan = float("nan")
    above = [nan] * n
    for i in range(MA_LENGTH - 1, n):
        w = c[i - MA_LENGTH + 1:i + 1]
        if any(x != x for x in w):
            continue
        m = sum(w) / MA_LENGTH
        s = (sum((x - m) ** 2 for x in w) / MA_LENGTH) ** 0.5
        above[i] = 1.0 if c[i] > m + STD_MULT * s else 0.0
    out = [nan] * n
    for i in range(LENGTH - 1, n):
        w = above[i - LENGTH + 1:i + 1]
        if any(x != x for x in w):
            continue
        out[i] = 100.0 * sum(w) / LENGTH
    return Series(out, index=close.index)


def _talib():
    if importlib.util.find_spec("talib") is None:
        return None
    import talib
    return talib


def _via_talib(talib, close):
    x = close.to_numpy(dtype=float)
    band = Series(talib.SMA(x, timeperiod=MA_LENGTH)
                  + STD_MULT * talib.STDDEV(x, timeperiod=MA_LENGTH, nbdev=1),
                  index=close.index)
    above = (close > band).astype(float).where(band.notna())
    return 100.0 * above.rolling(LENGTH).sum() / LENGTH


def _alt(close, ddof=0, op="gt", sign=1.0, ema3=False):
    band = sma(close, MA_LENGTH) + sign * STD_MULT * stdev(close, MA_LENGTH,
                                                           ddof=ddof)
    hit = (close > band) if op == "gt" else (close >= band)
    above = hit.astype(float).where(band.notna())
    out = 100.0 * above.rolling(LENGTH).sum() / LENGTH
    return out.ewm(span=3, adjust=False).mean() if ema3 else out


ALTERNATIVES = [
    ("std ddof=1", lambda c: _alt(c, ddof=1)),
    ("close >= band", lambda c: _alt(c, op="ge")),
    ("jesse lower band SMA - 0.2*std", lambda c: _alt(c, sign=-1.0)),
    ("jesse lower band + EMA(3)", lambda c: _alt(c, sign=-1.0, ema3=True)),
]


# ---------------------------------------------------------------- mutants

SOURCE = Path(__file__).resolve().parents[1] / "pandas_ta" / "trend" \
    / "stiffness.py"

MA_LINE = "    ma = sma(cl, length=MA_LENGTH)"
SD_LINE = "    sd = stdev(cl, length=MA_LENGTH, ddof=0)"
ABOVE_LINE = "    above = (cl > band).astype(float).where(band.notna() & cl.notna())"
COUNT_LINE = "    count = above.rolling(LENGTH, min_periods=LENGTH).sum()"
OUT_LINE = "    stiff = 100.0 * count / LENGTH"
GUARD_LINE = "    cl = cl.where(np.isfinite(cl))"

#: One-bar leads of the band's two legs. ⚠ Printed, NOT used as the gate's
#: mutants: one close in 100 moves the mean and SD so little that the
#: comparison rarely flips, so `sd-lead` is identical to the module on two
#: of the three swept frames before any perturbation, and the sweep catches
#: neither on `heavy-tailed` (§B1).
WEAK_MUTANTS = [
    ("ma-lead", MA_LINE, "    ma = sma(cl.shift(-1), length=MA_LENGTH)"),
    ("sd-lead", SD_LINE, "    sd = stdev(cl.shift(-1), length=MA_LENGTH, ddof=0)"),
]

CAUSALITY_MUTANTS = [
    ("ma-lead-10", MA_LINE, "    ma = sma(cl.shift(-10), length=MA_LENGTH)"),
    ("sd-lead-10", SD_LINE, "    sd = stdev(cl.shift(-10), length=MA_LENGTH, ddof=0)"),
    ("close-lead", ABOVE_LINE,
     "    above = (cl.shift(-1) > band).astype(float).where(band.notna() & cl.notna())"),
    ("above-lead", COUNT_LINE,
     "    count = above.shift(-1).rolling(LENGTH, min_periods=LENGTH).sum()"),
    ("output-early", OUT_LINE, "    stiff = (100.0 * count / LENGTH).shift(-1)"),
]

BLIND_SPOT_MUTANTS = [
    ("close-lag", ABOVE_LINE,
     "    above = (cl.shift(1) > band).astype(float).where(band.notna() & cl.notna())"),
    ("band-lag", ABOVE_LINE,
     "    above = (cl > band.shift(1)).astype(float).where(band.notna() & cl.notna())"),
]


def _mutant(old, new):
    src = SOURCE.read_text(encoding="utf-8")
    assert src.count(old) == 1, f"{old!r} occurs {src.count(old)} times"
    ns = {}
    exec(compile(src.replace(old, new), "<mutant>", "exec"), ns)
    return ns["stiffness"]


#: The suffix factor. ⚠ Not the 1.03 `j_kaufmanstop_dist`'s sweep uses: this
#: column is a COUNT, so a look-ahead shows only when the perturbation flips
#: a comparison, and a 3% suffix moves a 100-bar mean by ~0.03%. §B1 prints
#: the catches at this factor.
SWEEP_FACTOR = 10.0


def _caught_at(fn, close, j, factor=SWEEP_FACTOR):
    """Did rescaling every bar >= j move any bar < j? A rescale of a SUFFIX,
    not a global one -- the column is invariant under that (Gate D)."""
    f = Series(np.where(np.arange(close.size) >= j, factor, 1.0),
               index=close.index)
    a = fn(close).iloc[:j]
    b = fn(close * f).iloc[:j]
    return not _bit_equal(a, b)


def _sweep(fn, close, offsets=None):
    return sum(_caught_at(fn, close, j) for j in (offsets or OFFSETS))


def _first_catch_gap(fn, close, factor=SWEEP_FACTOR):
    for j in OFFSETS:
        if _caught_at(fn, close, j, factor):
            f = Series(np.where(np.arange(close.size) >= j, factor, 1.0),
                       index=close.index)
            return j, _abs(fn(close).iloc[:j], fn(close * f).iloc[:j])
    return None, float("nan")


# ------------------------------------------------------------------ print


def _table(rows, head):
    widths = [max(len(str(r[i])) for r in [head] + rows)
              for i in range(len(head))]
    print("  ".join(str(h).ljust(w) for h, w in zip(head, widths)))
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
    print(f"MA_LENGTH={MA_LENGTH} STD_MULT={STD_MULT} LENGTH={LENGTH} "
          f"MIN_BARS={MIN_BARS} WARMUP={WARMUP} FIRED={FIRED} N={N}")


def section_A1():
    _header("A1", "Gate A -- the issue's formula, spelled independently")
    rows = []
    for name in NAMES:
        close = _frame(name)
        got, want = stiffness(close), _oracle(close)
        rows.append([name, int(got.notna().sum()),
                     bool((got.isna() == want.isna()).all()),
                     _bit_equal(got, want), _differing_bars(got, want),
                     f"{_abs(got, want):.3e}"])
    _table(rows, ["frame", "fired", "same NaN mask", "bit-equal",
                  "bars differing", "max |abs|"])


def section_A2():
    _header("A2", "Gate A -- TA-Lib SMA + STDDEV as the third speller")
    talib = _talib()
    if talib is None:
        print("talib is NOT installed; this section is a skip, not a pass")
        return
    rows = []
    for name in NAMES:
        close = _frame(name)
        got, want = stiffness(close), _via_talib(talib, close)
        rows.append([name, bool((got.isna() == want.isna()).all()),
                     _bit_equal(got, want), _differing_bars(got, want),
                     f"{_abs(got, want):.3e}",
                     int(want.notna().to_numpy().argmax())])
    _table(rows, ["frame", "same NaN mask", "bit-equal", "bars differing",
                  "max |abs|", "first fired bar"])


def section_A3():
    _header("A3", "Gate A -- the other readings are other columns")
    rows = []
    for label, fn in ALTERNATIVES:
        for name in VARYING:
            close = _frame(name)
            got, alt = stiffness(close), fn(close)
            rows.append([label, name, _differing_bars(got, alt),
                         f"{_abs(got, alt):.3f}", f"{_spearman(got, alt):.4f}"])
    _table(rows, ["reading", "frame", "bars differing", "max |abs|",
                  "spearman"])
    print()
    flat = _frame("flat")
    print(f"flat frame: module {sorted(stiffness(flat).dropna().unique())}, "
          f"'>=' reading {sorted(_alt(flat, op='ge').dropna().unique())}")


def section_A4():
    _header("A4", "Gate A -- nothing reads before T-158 (prefix truncation)")
    rows = []
    for name in NAMES:
        close = _frame(name)
        base = stiffness(close)
        cut = stiffness(close.iloc[500:])
        tail = base.iloc[500 + WARMUP:]
        rows.append([name, int(tail.notna().sum()),
                     _bit_equal(tail, cut.iloc[WARMUP:])])
    _table(rows, ["frame", "bars from 658 on", "bit-equal"])


def section_B1():
    _header("B1", "Gate B -- future sweep, module and look-ahead mutants")
    rows = [["MODULE", name, _sweep(stiffness, _frame(name)), "", ""]
            for name in VARYING]
    for label, old, new in CAUSALITY_MUTANTS + WEAK_MUTANTS:
        fn = _mutant(old, new)
        for name in SWEPT:
            close = _frame(name)
            live = _differing_bars(stiffness(close), fn(close))
            j, gap = _first_catch_gap(fn, close)
            rows.append([label, name, _sweep(fn, close), live,
                         f"{gap:.4f} at {j}"])
    _table(rows, ["edit", "frame", "caught of 36", "bars live",
                  "first catch gap"])


def section_B2():
    _header("B2", "Gate B -- the sweep's blind spot, and the oracle covers it")
    rows = []
    for label, old, new in BLIND_SPOT_MUTANTS:
        fn = _mutant(old, new)
        for name in SWEPT:
            close = _frame(name)
            out, want = fn(close), _oracle(close)
            rows.append([label, name, _sweep(fn, close),
                         _differing_bars(out, want), f"{_abs(out, want):.4f}"])
    _table(rows, ["edit", "frame", "caught of 36", "bars off the oracle",
                  "max |abs|"])


def section_C1():
    _header("C1", "Gate C -- reachability on synthetic frames")
    rows = []
    for name in NAMES:
        col = _col(name).dropna()
        rows.append([name, len(col), col.nunique(), int((col == 0).sum()),
                     int((col == 100).sum()), f"{col.min():.4f}",
                     f"{col.max():.4f}",
                     bool(np.allclose(col / STEP, np.round(col / STEP)))])
    _table(rows, ["frame", "fired", "distinct", "== 0", "== 100", "min",
                  "max", "multiples of 100/60"])
    pooled = pd.concat([_col(n).dropna() for n in VARYING])
    print()
    print(f"pooled over the {len(VARYING)} varying frames: {len(pooled)} "
          f"fired bars, {int((pooled == 0).sum())} at 0, "
          f"{int((pooled == 100).sum())} at 100, "
          f"{int(((pooled > 0) & (pooled < 100)).sum())} strictly between")


def section_C2():
    _header("C2", "Gate C -- the tie: a close exactly ON its band")
    flat = _frame("flat")
    band = sma(flat, MA_LENGTH) + STD_MULT * stdev(flat, MA_LENGTH, ddof=0)
    print(f"flat frame: band == close on "
          f"{int((band.dropna() == flat[band.notna()]).sum())} of "
          f"{int(band.notna().sum())} bars; SD exactly 0 on "
          f"{int((stdev(flat, MA_LENGTH, ddof=0).dropna() == 0).sum())}")
    print(f"module reads {sorted(stiffness(flat).dropna().unique())} "
          f"(strict >), '>=' reads "
          f"{sorted(_alt(flat, op='ge').dropna().unique())}")
    coarse = _frame("coarse")
    print(f"coarse frame: {int((coarse.diff() == 0).sum())} of {N} closes "
          f"equal their predecessor")


def section_D1():
    _header("D1", "Gate D -- x8 / x64 bit-identity, at four price levels")
    rows = []
    for level in (LEVEL, 1e-6, 1e6, 1e100):
        for name in NAMES:
            close = _frame(name) / LEVEL * level
            base = stiffness(close)
            rows.append([f"{level:g}", name, int(base.notna().sum()),
                         _bit_equal(base, stiffness(close * 8.0)),
                         _bit_equal(base, stiffness(close * 64.0))])
    _table(rows, ["level", "frame", "fired", "x8 bit-equal", "x64 bit-equal"])
    print(f"cells bit-equal: {sum(r[3] and r[4] for r in rows)} of "
          f"{len(rows)} (frame x level), each covering both factors")


def section_D2():
    _header("D2", "Gate D -- inexact factors x10 / x3.7 / x0.1 / x1.0000001")
    rows = []
    for factor in (10.0, 3.7, 0.1, 1.0000001):
        for name in NAMES:
            close = _frame(name)
            base, moved = stiffness(close), stiffness(close * factor)
            rows.append([factor, name,
                         bool((base.isna() == moved.isna()).all()),
                         _differing_bars(base, moved),
                         f"{_abs(base, moved):.3e}"])
    _table(rows, ["factor", "frame", "same NaN mask", "bars differing",
                  "max |abs|"])
    print(f"worst cell: {max(float(r[4]) for r in rows):.3e}; cells with any "
          f"differing bar: {sum(r[3] > 0 for r in rows)} of {len(rows)}")


def section_D3():
    _header("D3", "Gate D -- what moves the column, so D1 is not vacuous")
    rows = []
    for name in NAMES:
        close = _frame(name)
        base = stiffness(close)
        rows.append([name, int(base.notna().sum()),
                     _differing_bars(base, stiffness(close + 10.0)),
                     _differing_bars(base, stiffness(close ** 2)),
                     _differing_bars(base, stiffness(np.log(close)))])
    _table(rows, ["frame", "fired", "moved by +10", "moved by close**2",
                  "moved by log(close)"])


def section_G1():
    _header("G1", "guards -- one bad close empties a bounded window")
    rows = []
    src = SOURCE.read_text(encoding="utf-8")
    ns = {}
    exec(compile(src.replace(GUARD_LINE, "    pass"), "<guard-off>", "exec"),
         ns)
    unguarded = ns["stiffness"]
    for value in (np.nan, np.inf, -np.inf):
        for j in (5, 100, 700, 1495):
            close = _frame("walk")
            bad = close.copy()
            bad.iloc[j] = value
            base, out = stiffness(close), stiffness(bad)
            blank = base.notna() & out.isna()
            moved = base.notna() & out.notna() & (base != out)
            off = unguarded(bad)
            rows.append([value, j, int(blank.sum()), int(moved.sum()),
                         int(np.isinf(out).sum()),
                         _differing_bars(out, off),
                         int((out.isna() != off.isna()).sum())])
    _table(rows, ["value", "bar", "blanked", "moved", "inf in output",
                  "guard-off bars differing", "guard-off NaN-mask diff"])


def section_L():
    _header("L", "in-fork overlap on synthetic frames -- a disclosure, not "
                 "Gate E")
    comps = {
        "MADISP_200_SMA": lambda c: ma_disparity(c).iloc[:, 0],
        "Z_30": lambda c: zscore(c),
        "PSL_12": lambda c: psl(c),
        "zscore(close, 100) [non-default]": lambda c: zscore(c, 100),
        "60-bar mean of zscore(close, 100) [not shipped]":
            lambda c: zscore(c, 100).rolling(60).mean(),
    }
    rows = []
    for label, fn in comps.items():
        rhos = [_spearman(_col(n), fn(_frame(n))) for n in VARYING]
        rows.append([label, f"{np.median(np.abs(rhos)):.4f}",
                     f"{min(rhos):+.4f}", f"{max(rhos):+.4f}", len(rhos)])
    _table(rows, ["comparator", "median |rho|", "min", "max", "frames"])


def section_Z():
    _header("Z", "cost -- THIS MACHINE AND THIS RUN ONLY")
    close = _frame("walk")
    t = timeit.timeit(lambda: stiffness(close), number=50) / 50
    print(f"stiffness {1000 * t:7.3f} ms per call on {N} bars")


SECTIONS = {
    "ENV": section_env,
    "A1": section_A1, "A2": section_A2, "A3": section_A3, "A4": section_A4,
    "B1": section_B1, "B2": section_B2,
    "C1": section_C1, "C2": section_C2,
    "D1": section_D1, "D2": section_D2, "D3": section_D3,
    "G1": section_G1,
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
