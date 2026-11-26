# -*- coding: utf-8 -*-
"""WAVEPM-14-100 (PandasTa issue #261): every number in
`docs/WavepmMeasured.md`.

    python docs/measure_wavepm.py          # every section, in order
    python docs/measure_wavepm.py A1 D     # named sections only

One section per gate limb, printed and never derived: the repo's dominant
defect is "a claim written before it was measured", so this file is the only
place a figure in the receipt, the module docstring or
`tests/test_wavepm.py` may come from.

    r[T]   = std(close, n)[T] / sma(close, n)[T]      (ddof = 0)
    WAVEPM = tanh(r[T] / sqrt(mean(r[T-L+1 .. T] ** 2)))

⚠ The millisecond figures of §Z are this machine's and this run's.
"""
import sys
import timeit
import tracemalloc
from pathlib import Path

import numpy as np
import pandas as pd
from pandas import Series, date_range

from pandas_ta.trend.chop import chop
from pandas_ta.momentum.er import er
from pandas_ta.volatility.bbands import bbands
from pandas_ta.volatility.j_damiani import j_damiani
from pandas_ta.volatility.natr import natr
from pandas_ta.volatility.wavepm import wavepm

N = 1500
LEVEL = 100.0
LENGTH = 14
LOOKBACK = 100
#: The first fired bar: r needs LENGTH bars, its RMS LOOKBACK r's.
WARMUP = LENGTH + LOOKBACK - 2
#: The blind causality sweep's 36 perturbation points.
OFFSETS = list(range(N - 36, N))
#: Where §G plants a bad bar.
PLANT = 700


# ------------------------------------------------------------------ frames
# Same builders and seeds as `tests/test_wavepm.py`, which are
# `tests/test_inrange_count.py`'s, so the frame set is shared across ports.


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
    """A walk rounded to a tick coarser than its bar-to-bar move: many
    tied closes, and 14-bar windows with a single price (r = 0)."""
    h, l, c = _walk(seed, n, level)
    return (np.round(h / tick) * tick, np.round(l / tick) * tick,
            np.round(c / tick) * tick)


FRAMES = {
    "walk": _walk, "trend": _trend, "range-bound": _range_bound,
    "grid": _grid, "heavy-tailed": _heavy, "jump": _jump, "flat": _flat,
    "coarse": _coarse,
}
NAMES = list(FRAMES)
#: `flat` has rms = 0 on every bar, so the column is NaN throughout.
MOVING = [n for n in NAMES if n != "flat"]


def _c(frame):
    return frame[2]


def _scaled(frame, factor):
    return tuple(s * factor for s in frame)


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


def _maxdiff(a, b):
    m = a.notna() & b.notna()
    return float((a[m] - b[m]).abs().max()) if int(m.sum()) else float("nan")


# ----------------------------------------------------------------- oracles


def _oracle(close, length=LENGTH, lookback=LOOKBACK, ddof=0, by_mean=True):
    """Issue #261's finta form, transcribed as explicit loops and sharing no
    code with the module: each window summed bar by bar, no rolling."""
    x = close.to_numpy(dtype=float)
    n = x.size
    r = np.full(n, np.nan)
    for t in range(length - 1, n):
        w = x[t - length + 1:t + 1]
        s = 0.0
        for v in w:
            s += v
        mu = s / length
        ss = 0.0
        for v in w:
            ss += (v - mu) * (v - mu)
        sd = (ss / (length - ddof)) ** 0.5
        r[t] = sd / mu if by_mean else sd
    out = np.full(n, np.nan)
    for t in range(length + lookback - 2, n):
        q = 0.0
        for k in range(t - lookback + 1, t + 1):
            q += r[k] * r[k]
        rms = (q / lookback) ** 0.5
        out[t] = np.tanh(r[t] / rms) if rms > 0 else np.nan
    return Series(out, index=close.index)


# ----------------------------------------------------------------- mutants

SOURCE = Path(__file__).resolve().parents[1] / "pandas_ta" / "volatility" \
    / "wavepm.py"

#: (label, old text, new text). Edits to the SHIPPED source, read off disk.
CAUSALITY_MUTANTS = [
    ("mean-lead", "    mu = close.rolling(length).mean()",
     "    mu = close.rolling(length).mean().shift(-1)"),
    ("std-lead", "    sigma = close.rolling(length).std(ddof=0)",
     "    sigma = close.rolling(length).std(ddof=0).shift(-1)"),
    ("rms-lead", "    rms = np.sqrt((r * r).rolling(lookback).mean())",
     "    rms = np.sqrt((r * r).rolling(lookback).mean()).shift(-1)"),
    ("output-early", "    # Offset\n    if offset != 0:",
     "    wpm = wpm.shift(-1)\n    # Offset\n    if offset != 0:"),
]


def _mutant(old, new):
    src = SOURCE.read_text(encoding="utf-8")
    assert src.count(old) == 1, f"{old!r} occurs {src.count(old)} times"
    ns = {}
    exec(compile(src.replace(old, new), "<mutant>", "exec"), ns)
    return ns["wavepm"]


def _futures(close, j, spread=3.0):
    """Three closes that agree BIT FOR BIT on bars < j: the series itself,
    and the series with every bar >= j scaled UP by a per-bar factor in
    [1.5, 4] or DOWN by its reciprocal."""
    n = close.size
    rng = np.random.default_rng(90_001 + j)
    f = np.ones(n)
    f[j:] = 1.5 + (spread - 0.5) * rng.random(n)[j:]
    up, dn = Series(f, index=close.index), Series(1.0 / f, index=close.index)
    return close, close * up, close * dn


def _caught_at(fn, close, j):
    base, *others = _futures(close, j)
    a = fn(base).iloc[:j]
    return any(not _bit_equal(a, fn(o).iloc[:j]) for o in others)


def _sweep(fn, close, offsets=None):
    return sum(_caught_at(fn, close, j) for j in (offsets or OFFSETS))


def _head(title):
    print()
    print("=" * 72)
    print(title)
    print("=" * 72)


# ---------------------------------------------------------------- sections


def section_A1():
    _head("A1 Gate A -- issue #261's finta form by explicit loops")
    print(f"{'frame':>13} {'fired':>6} {'masks':>6} {'max |diff|':>11} "
          f"{'bit-equal':>10}")
    pooled = 0
    for name in NAMES:
        c = _c(FRAMES[name]())
        col, orc = wavepm(c), _oracle(c)
        pooled += int(col.notna().sum())
        print(f"{name:>13} {int(col.notna().sum()):>6} "
              f"{str(bool((col.isna() == orc.isna()).all())):>6} "
              f"{_maxdiff(col, orc):>11.3e} {str(_bit_equal(col, orc)):>10}")
    print(f"{'POOLED':>13} {pooled:>6}")
    print()
    print("Other (length, lookback) on `walk` and `coarse`:")
    for length, lookback in ((5, 20), (20, 50), (30, 200)):
        for name in ("walk", "coarse"):
            c = _c(FRAMES[name]())
            col = wavepm(c, length=length, lookback=lookback)
            orc = _oracle(c, length, lookback)
            print(f"  {length:>3} {lookback:>4} {name:>8}: {col.name} masks "
                  f"{bool((col.isna() == orc.isna()).all())} "
                  f"max |diff| {_maxdiff(col, orc):.3e}")


def section_A4():
    _head("A4 The readings not taken")
    print("ddof=1 (sample std): rescales every r by one constant, which")
    print("cancels in r / rms. ProRealCode: std NOT divided by the mean.")
    print()
    print(f"{'frame':>13} {'ddof1 max|diff|':>16} {'no-mean spearman':>17} "
          f"{'no-mean max|diff|':>18}")
    for name in MOVING:
        c = _c(FRAMES[name]())
        col = wavepm(c)
        d0, d1 = _oracle(c), _oracle(c, ddof=1)
        nm = _oracle(c, by_mean=False)
        print(f"{name:>13} {_maxdiff(d0, d1):>16.3e} "
              f"{_spearman(col, nm):>17.4f} {_maxdiff(col, nm):>18.4f}")


def section_B():
    _head("B Gate B -- two-futures sweep and read-off mutants")
    print(f"Out of 36 offsets {OFFSETS[0]}..{OFFSETS[-1]}.")
    print()
    print(f"{'frame':>13} {'module':>7} "
          + " ".join(f"{label:>13}" for label, _, _ in CAUSALITY_MUTANTS))
    for name in NAMES:
        c = _c(FRAMES[name]())
        row = [f"{_sweep(wavepm, c):>7}"]
        for _, old, new in CAUSALITY_MUTANTS:
            row.append(f"{_sweep(_mutant(old, new), c):>13}")
        print(f"{name:>13} " + " ".join(row))
    print()
    print("The module alone, every bar but bar 0 as a split point:")
    for name in NAMES:
        c = _c(FRAMES[name]())
        dense = list(range(1, N))
        print(f"{name:>13} caught {_sweep(wavepm, c, dense):>5} "
              f"of {len(dense):>5}")
    print()
    print("Each mutant is live on unperturbed `walk`:")
    c = _c(FRAMES["walk"]())
    base = wavepm(c)
    for label, old, new in CAUSALITY_MUTANTS:
        mut = _mutant(old, new)(c)
        m = base.notna() & mut.notna()
        print(f"{label:>13} both fire {int(m.sum()):>5}  "
              f"moved {int((base[m] != mut[m]).sum()):>5}")


def section_C():
    _head("C Gate C -- reachability, on synthetic frames")
    print(f"{'frame':>13} {'bars':>5} {'fired':>6} {'first':>6} "
          f"{'distinct':>9} {'== 0':>6} {'> 0.5':>6} {'> 0.9':>6} "
          f"{'min':>7} {'max':>7} {'mean':>7}")
    for name in NAMES:
        col = wavepm(_c(FRAMES[name]()))
        v = col.dropna()
        fired = col.notna().to_numpy()
        first = int(np.flatnonzero(fired)[0]) if fired.any() else -1
        if v.size == 0:
            print(f"{name:>13} {col.size:>5} {0:>6} {first:>6}")
            continue
        print(f"{name:>13} {col.size:>5} {v.size:>6} {first:>6} "
              f"{v.nunique():>9} {int((v == 0).sum()):>6} "
              f"{int((v > 0.5).sum()):>6} {int((v > 0.9).sum()):>6} "
              f"{v.min():>7.4f} {v.max():>7.4f} {v.mean():>7.4f}  "
              f"max < tanh(10): {bool(v.max() < np.tanh(10.0))}")


def section_D():
    _head("D Gate D -- scale invariance")
    print(f"{'frame':>13} {'x8':>6} {'x64':>6} {'x10 max|diff|':>14} "
          f"{'x3.7 max|diff|':>15} {'masks x10/x3.7':>15}")
    for name in NAMES:
        frame = FRAMES[name]()
        base = wavepm(_c(frame))
        b8 = _bit_equal(base, wavepm(_c(_scaled(frame, 8))))
        b64 = _bit_equal(base, wavepm(_c(_scaled(frame, 64))))
        a10 = wavepm(_c(_scaled(frame, 10.0)))
        a37 = wavepm(_c(_scaled(frame, 3.7)))
        masks = bool((base.isna() == a10.isna()).all()
                     and (base.isna() == a37.isna()).all())
        print(f"{name:>13} {str(b8):>6} {str(b64):>6} "
              f"{_maxdiff(base, a10):>14.3e} {_maxdiff(base, a37):>15.3e} "
              f"{str(masks):>15}")
    print()
    print("At other price levels, x8 and x64, and against level 100:")
    ref = wavepm(_c(_walk()))
    for level in (1e-6, 1e+6, 1e+100):
        frame = _walk(level=level)
        base = wavepm(_c(frame))
        print(f"  {level:>8.0e}: fired {int(base.notna().sum())}  "
              f"x8 {_bit_equal(base, wavepm(_c(_scaled(frame, 8))))}  "
              f"x64 {_bit_equal(base, wavepm(_c(_scaled(frame, 64))))}  "
              f"vs level 100 max|diff| {_maxdiff(base, ref):.3e}")


def section_F():
    _head("F Non-redundancy against fork columns (SYNTHETIC, a disclosure)")
    cols = {}
    for name in MOVING:
        h, l, c = FRAMES[name]()
        col = wavepm(c)
        others = {
            "chop:CHOP_14_1_100": chop(h, l, c),
            "j_damiani:J_DAMIANI_13_40": j_damiani(h, l, c),
            "er:ER_10": er(c),
            "bbands:BBB_5_2.0": bbands(c)["BBB_5_2.0"],
            "natr:NATR_14": natr(h, l, c),
            "raw r (std14/sma14)": c.rolling(14).std(ddof=0)
            / c.rolling(14).mean(),
        }
        for label, other in others.items():
            if isinstance(other, pd.DataFrame):
                other = other.iloc[:, 0]
            cols.setdefault(label, []).append(_spearman(col, other))
    print(f"{'comparator':>28} {'median |rho|':>12} {'max |rho|':>9} "
          + " ".join(f"{n[:9]:>9}" for n in MOVING))
    for label, v in sorted(cols.items(),
                           key=lambda kv: -np.nanmedian(np.abs(kv[1]))):
        print(f"{label:>28} {np.nanmedian(np.abs(v)):>12.4f} "
              f"{np.nanmax(np.abs(v)):>9.4f} "
              + " ".join(f"{x:>9.4f}" for x in v))


def section_G():
    _head("G Guards")
    print("A bad close at bar 700 of `walk`: bars before it moved, the NaN")
    print("hole after it, and whether +-inf is bit-identical to NaN. There is")
    print("no mask: pandas' rolling windows already return NaN over an inf.")
    print()
    c = _c(_walk())
    base = wavepm(c)
    nan_c = c.copy()
    nan_c.iloc[PLANT] = np.nan
    nan_out = wavepm(nan_c)
    print(f"{'value':>6} {'before':>7} {'NaN bars from 700':>18} "
          f"{'== NaN plant':>13} {'fired after hole':>17}")
    for label, value in (("nan", np.nan), ("+inf", np.inf),
                         ("-inf", -np.inf)):
        x = c.copy()
        x.iloc[PLANT] = value
        out = wavepm(x)
        b, o = base.to_numpy(), out.to_numpy()
        before = int((~((b[:PLANT] == o[:PLANT])
                        | (np.isnan(b[:PLANT]) & np.isnan(o[:PLANT])))).sum())
        hole = int(np.isnan(o[PLANT:]).sum())
        after = int(np.isfinite(o[PLANT + hole:]).sum())
        print(f"{label:>6} {before:>7} {hole:>18} "
              f"{str(_bit_equal(out, nan_out)):>13} {after:>17}")


def section_L():
    _head("L Short and degenerate frames")
    c = _c(_walk(n=200))
    for n in (WARMUP, WARMUP + 1, WARMUP + 5):
        out = wavepm(c.iloc[:n])
        print(f"  bars {n:>3}: "
              f"{'None' if out is None else str(int(out.notna().sum())) + ' fired'}")
    idx = date_range("2020-01-01", periods=300, freq="h")
    for label, value in (("all NaN", np.nan), ("all 0.0", 0.0),
                         ("all -5.0", -5.0), ("all 100.0", 100.0)):
        s = Series(np.full(300, value), index=idx)
        with np.errstate(all="ignore"):
            out = wavepm(s)
        print(f"  {label:>10}: {int(out.notna().sum())} fired")
    neg = wavepm(-_c(_walk()))
    v = neg.dropna()
    print(f"  negated walk: {v.size} fired, min {v.min():.4f}, "
          f"max {v.max():.4f}")


def section_M():
    _head("M The wiring counts, read back from the package")
    import re
    from collections import Counter

    import pandas_ta as ta
    print(f"registered in Category: {sum(len(v) for v in ta.Category.values())}")
    print(f"volatility bucket: {len(ta.Category['volatility'])}")
    doc = (Path(__file__).resolve().with_name("IndicatorDictionary.md")
           .read_text(encoding="utf-8"))
    body = doc[doc.index("## candles"):]
    tags = Counter(re.findall(
        r"`[^`]+`\s+(PX2|PX|SF|BIN|ORD|CONST|\?\?)(?!\w)", body))
    print(f"dictionary tagged columns: {sum(tags.values())}  {dict(tags)}")
    for line in doc.splitlines():
        if line.startswith("| `wavepm`"):
            print(f"  {line}")


def _generator_desc():
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


def section_W():
    _head("W The docstring's first paragraph against the dictionary's cut")
    body = []
    for line in wavepm.__doc__.splitlines()[1:]:
        if line.strip():
            body.append(line.strip())
        elif body:
            break
    paragraph = " ".join(body)
    desc = _generator_desc()
    print(f"paragraph ({len(paragraph)} chars): {paragraph}")
    print(f"desc() returns it whole: {desc({'desc': paragraph}) == paragraph}")


def section_Z():
    _head("Z Cost (machine- and run-dependent)")
    for n in (100_000, 400_000):
        c = _c(_walk(n=n))
        times = [min(timeit.repeat(lambda: wavepm(c), number=1,
                                   repeat=3)) * 1e3 for _ in range(2)]
        tracemalloc.start()
        wavepm(c)
        peak = tracemalloc.get_traced_memory()[1] / 1e6
        tracemalloc.stop()
        print(f"{n:>8} bars: {min(times):.0f} .. {max(times):.0f} ms, "
              f"peak {peak:.1f} MB")


SECTIONS = {
    "A1": section_A1, "A4": section_A4, "B": section_B, "C": section_C,
    "D": section_D, "F": section_F, "G": section_G, "L": section_L,
    "M": section_M, "W": section_W, "Z": section_Z,
}


if __name__ == "__main__":
    print(f"pandas {pd.__version__}, numpy {np.__version__}")
    want = [a.upper() for a in sys.argv[1:]] or list(SECTIONS)
    for key in want:
        if key not in SECTIONS:
            raise SystemExit(f"unknown section {key!r}; pick from {list(SECTIONS)}")
        SECTIONS[key]()
