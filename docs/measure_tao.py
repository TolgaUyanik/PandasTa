# -*- coding: utf-8 -*-
"""TAO-10-5 (PandasTa issue #266): every number in `docs/TaoMeasured.md`.

    python docs/measure_tao.py          # every section, in order
    python docs/measure_tao.py A1 D     # named sections only

One section per gate limb, printed and never derived: the repo's dominant
defect is "a claim written before it was measured", so this file is the only
place a figure in the receipt, the module docstring or `tests/test_tao.py`
may come from.

    O[T]     = 100 * (close[T] - LL10[T]) / (HH10[T] - LL10[T])  (NaN if HH == LL)
    MAO[T]   = mean(O[T - 4 .. T])
    TAO_10_5 = O[T] - (MAO[T] - 50)

⚠ The millisecond figures of §Z are this machine's and this run's.
"""
import sys
import timeit
import tracemalloc
from pathlib import Path

import numpy as np
from pandas import DataFrame, Series, date_range

from pandas_ta.momentum.tao import tao

N = 1500
LEVEL = 100.0
LENGTH = 10
MA_LENGTH = 5
MIDPOINT = 50.0
#: First bar that can carry a value: `length + ma_length - 2`.
WARMUP = LENGTH + MA_LENGTH - 2
OFFSETS = list(range(N - 36, N))
ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "pandas_ta" / "momentum" / "tao.py"


# ------------------------------------------------------------------ frames
# OHLC, because the stochastic reads the high and the low. Every frame is
# built from a close path, an open one bar behind it, and a high / low that
# sit outside both by a random non-negative spread -- zero on ~20% of bars,
# so the close is often EXACTLY the bar's (and the window's) extreme.


def _index(n):
    # Hourly: §Z runs 400,000 bars, past pandas' datetime bound as days.
    return date_range("2020-01-01", periods=n, freq="h")


def _ohlc(close, seed, tick=None):
    rng = np.random.default_rng(seed + 1000)
    n = close.size
    c = np.asarray(close, dtype=float)
    o = np.r_[c[0], c[:-1]] * (1 + rng.normal(0.0, 0.002, n))
    up = np.abs(rng.normal(0.0, 0.006, n)) * c * (rng.random(n) > 0.2)
    dn = np.abs(rng.normal(0.0, 0.006, n)) * c * (rng.random(n) > 0.2)
    h = np.maximum(o, c) + up
    lo = np.minimum(o, c) - dn
    if tick:
        o, h, lo, c = (np.round(x / tick) * tick for x in (o, h, lo, c))
        h = np.maximum.reduce([h, o, c])
        lo = np.minimum.reduce([lo, o, c])
    idx = _index(n)
    return DataFrame({"open": o, "high": h, "low": lo, "close": c}, index=idx)


def _path(seed, n, mu=0.0, sigma=0.01, t=None):
    rng = np.random.default_rng(seed)
    r = rng.standard_t(t, n) * sigma * 0.6 if t else rng.normal(mu, sigma, n)
    return LEVEL * np.exp(np.cumsum(r))


def _walk(seed=7, n=N):
    return _ohlc(_path(seed, n), seed)


def _trend(seed=11, n=N):
    return _ohlc(_path(seed, n, mu=0.003, sigma=0.008), seed)


def _range_bound(seed=13, n=N):
    rng = np.random.default_rng(seed)
    x = np.zeros(n)
    for i in range(1, n):
        x[i] = 0.9 * x[i - 1] + rng.normal(0.0, 0.02)
    return _ohlc(LEVEL * np.exp(x), seed)


def _grid(seed=17, n=N):
    return _ohlc(_path(seed, n), seed, tick=0.01)


def _heavy(seed=19, n=N):
    return _ohlc(_path(seed, n, t=2.0), seed)


def _jump(seed=23, n=N):
    p = _path(seed, n)
    return _ohlc(p * np.where(np.arange(n) >= n // 2, 1.5, 1.0), seed)


def _flat(n=N):
    one = np.full(n, LEVEL)
    return DataFrame({"open": one, "high": one, "low": one, "close": one},
                     index=_index(n))


def _coarse(seed=7, n=N):
    """A walk rounded to a 0.5 tick, coarser than the bar's spread: flat
    10-bar windows and closes AT the window's extreme happen by rounding."""
    return _ohlc(_path(seed, n, sigma=0.002), seed, tick=0.5)


FRAMES = {
    "walk": _walk, "trend": _trend, "range-bound": _range_bound,
    "grid": _grid, "heavy-tailed": _heavy, "jump": _jump, "flat": _flat,
    "coarse": _coarse,
}
NAMES = list(FRAMES)
FIRING = [n for n in NAMES if n != "flat"]


def _run(df, fn=None, **kw):
    return (fn or tao)(df["high"], df["low"], df["close"], **kw)


# ----------------------------------------------------------------- helpers


def _rel(a, b):
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


def _bit_equal(a, b):
    if not bool((a.isna() == b.isna()).all()):
        return False
    m = a.notna()
    return bool((a[m] == b[m]).all())


def _differs(a, b):
    one = int((a.isna() != b.isna()).sum())
    m = a.notna() & b.notna()
    return one + int((a[m] != b[m]).sum())


def _head(title):
    print()
    print("=" * 72)
    print(title)
    print("=" * 72)


# ----------------------------------------------------------------- oracles


def _oracle(df, length=LENGTH, ma_length=MA_LENGTH, midpoint=MIDPOINT):
    """The issue's formula by explicit scalar loops: a fresh min / max over
    each 10-bar window, a fresh five-term mean, no pandas operation."""
    h = df["high"].to_numpy(float)
    lo = df["low"].to_numpy(float)
    c = df["close"].to_numpy(float)
    n = c.size
    o = np.full(n, np.nan)
    out = np.full(n, np.nan)
    for i in range(length - 1, n):
        hh = max(h[i - length + 1:i + 1])
        ll = min(lo[i - length + 1:i + 1])
        if hh != ll:
            o[i] = 100.0 * (c[i] - ll) / (hh - ll)
    for i in range(length + ma_length - 2, n):
        w = o[i - ma_length + 1:i + 1]
        if not np.isnan(w).any():
            total = 0.0
            for x in w:
                total += x
            out[i] = o[i] - (total / ma_length - midpoint)
    return Series(out, index=df.index)


def _via_stoch(df):
    """The same construction on the shipped `stoch`'s raw %K
    (`smooth_k=1`), which divides by `non_zero_range` (adds an epsilon on a
    flat window) instead of leaving it NaN."""
    from pandas_ta.momentum.stoch import stoch
    k = stoch(df["high"], df["low"], df["close"], k=LENGTH, d=1,
              smooth_k=1).iloc[:, 0]
    return k - (k.rolling(MA_LENGTH).mean() - MIDPOINT)


# ----------------------------------------------------------------- mutants

LL_LINE = "    lowest_low = low.rolling(length).min()"
HH_LINE = "    highest_high = high.rolling(length).max()"
OSC_LINE = "    osc = 100 * (close - lowest_low) / rng.where(rng != 0)"
MAO_LINE = "    mao = osc.rolling(ma_length).mean()"
OUT_LINE = "    tao = osc - (mao - midpoint)"

CAUSALITY_MUTANTS = [
    ("ll-centred", LL_LINE,
     "    lowest_low = low.rolling(length, center=True).min()"),
    ("hh-lead", HH_LINE,
     "    highest_high = high.rolling(length).max().shift(-1)"),
    ("close-lead", OSC_LINE,
     "    osc = 100 * (close.shift(-1) - lowest_low) / rng.where(rng != 0)"),
    ("mao-centred", MAO_LINE,
     "    mao = osc.rolling(ma_length, center=True).mean()"),
    ("output-early", OUT_LINE, "    tao = (osc - (mao - midpoint)).shift(-1)"),
]


def _mutant(old, new):
    src = SOURCE.read_text(encoding="utf-8")
    assert src.count(old) == 1, f"{old!r} occurs {src.count(old)} times"
    ns = {}
    exec(compile(src.replace(old, new), "<mutant>", "exec"), ns)
    return ns["tao"]


def _futures(df, j, spread=3.0):
    """Two frames that agree BIT FOR BIT on bars < j (multiplied by exactly
    1.0) and differ wholly on bars >= j: every price of a later bar scaled
    by one per-bar factor, up in one and down in the other, so each bar
    stays a valid OHLC bar."""
    n = len(df)
    rng = np.random.default_rng(90_001 + j)
    u = rng.random(n)
    up, dn = np.ones(n), np.ones(n)
    up[j:] = 1.0 + spread * u[j:]
    dn[j:] = 1.0 / (1.0 + spread * u[j:])
    return df.mul(up, axis=0), df.mul(dn, axis=0)


def _caught_at(fn, df, j):
    a, b = (_run(f, fn).iloc[:j] for f in _futures(df, j))
    return not _bit_equal(a, b)


def _sweep(fn, df, offsets=None):
    return sum(_caught_at(fn, df, j) for j in (offsets or OFFSETS))


# ---------------------------------------------------------------- sections


def section_A1():
    _head("A1 Gate A -- the issue's formula by explicit scalar loops")
    print(f"{'frame':>13} {'fired':>6} {'bit-equal':>10} {'masks':>6} "
          f"{'differ':>7} {'max abs':>11} {'spearman':>9}")
    for name in NAMES:
        df = FRAMES[name]()
        col, orc = _run(df), _oracle(df)
        print(f"{name:>13} {int(col.notna().sum()):>6} "
              f"{str(_bit_equal(col, orc)):>10} "
              f"{str(bool((col.isna() == orc.isna()).all())):>6} "
              f"{_differs(col, orc):>7} {_abs(col, orc):>11.3e} "
              f"{_spearman(col, orc):>9.4f}")
    print()
    print("`max abs` is in oscillator points (0 .. 100 scale). A non-zero")
    print("value is pandas' online rolling mean against a fresh five-term sum.")


def section_A2():
    _head("A2 The identity TAO = 50 + (O - MAO), and the oscillator's own form")
    print(f"{'frame':>13} {'max |TAO - (50 + O - MAO)|':>28}")
    for name in FIRING:
        df = FRAMES[name]()
        ll = df["low"].rolling(LENGTH).min()
        hh = df["high"].rolling(LENGTH).max()
        rng = hh - ll
        o = 100 * (df["close"] - ll) / rng.where(rng != 0)
        alt = 50 + (o - o.rolling(MA_LENGTH).mean())
        print(f"{name:>13} {_abs(_run(df), alt):>28.3e}")


def section_A3():
    _head("A3 The reading NOT taken: the shipped `stoch`'s raw %K")
    print("`stoch` divides by `non_zero_range`, which adds an epsilon on a")
    print("zero range, so a flat 10-bar window reads O = 0 instead of NaN.")
    print()
    print(f"{'frame':>13} {'differ':>7} {'mask diff':>10} {'max abs':>11} "
          f"{'spearman':>9}")
    for name in NAMES:
        df = FRAMES[name]()
        col, via = _run(df), _via_stoch(df)
        print(f"{name:>13} {_differs(col, via):>7} "
              f"{int((col.isna() != via.isna()).sum()):>10} "
              f"{_abs(col, via):>11.3e} {_spearman(col, via):>9.4f}")


def section_B():
    _head("B Gate B -- the blind causality sweep, every offset")
    print(f"{'frame':>13} {'offsets':>8} {'caught':>7}")
    offsets = list(range(1, N))
    for name in NAMES:
        print(f"{name:>13} {len(offsets):>8} "
              f"{_sweep(tao, FRAMES[name](), offsets):>7}")


def section_B1():
    _head("B1 Gate B -- five look-ahead mutants, read off the shipped source")
    print(f"{'mutant':>14} {'live':>5} " +
          " ".join(f"{n[:9]:>9}" for n in NAMES))
    for label, old, new in CAUSALITY_MUTANTS:
        fn = _mutant(old, new)
        live, caught = 0, []
        for name in NAMES:
            df = FRAMES[name]()
            live += int(_differs(_run(df), _run(df, fn)) > 0)
            caught.append(_sweep(fn, df))
        print(f"{label:>14} {live:>5} " + " ".join(f"{c:>9}" for c in caught))
    print()
    print(f"each frame contributes {len(OFFSETS)} offsets "
          f"({OFFSETS[0]} .. {OFFSETS[-1]})")


def section_C():
    _head("C Gate C -- reachability, and the bound [-30, 130]")
    print(f"{'frame':>13} {'bars':>6} {'fired':>6} {'first':>6} "
          f"{'distinct':>9} {'min':>9} {'max':>9} {'<0':>5} {'>100':>5} "
          f"{'flatHL':>7}")
    for name in NAMES:
        df = FRAMES[name]()
        col = _run(df)
        v = col.dropna()
        rng = df["high"].rolling(LENGTH).max() - df["low"].rolling(LENGTH).min()
        flat = int((rng == 0).sum())
        if v.size:
            first = int(np.flatnonzero(col.notna().to_numpy())[0])
            print(f"{name:>13} {col.size:>6} {v.size:>6} {first:>6} "
                  f"{v.nunique():>9} {v.min():>9.4f} {v.max():>9.4f} "
                  f"{int((v < 0).sum()):>5} {int((v > 100).sum()):>5} "
                  f"{flat:>7}")
        else:
            print(f"{name:>13} {col.size:>6} {0:>6} {-1:>6} {0:>9} "
                  f"{'--':>9} {'--':>9} {0:>5} {0:>5} {flat:>7}")
    print()
    print("`flatHL` counts bars whose 10-bar range is exactly 0.")
    print()
    print("The bound attained, on a hand frame: 9 bars on a 0 .. 100 range,")
    print("four closes at the low, then one at the high (and the mirror):")
    for last, rest in ((100.0, 0.0), (0.0, 100.0)):
        c = np.array([50.0] * 9 + [rest] * 4 + [last])
        df = DataFrame({"high": np.full(c.size, 100.0),
                        "low": np.full(c.size, 0.0), "close": c},
                       index=_index(c.size))
        print(f"  four at {rest:>5}, then {last:>5}: "
              f"{float(_run(df).iloc[-1])!r}")


def section_C2():
    _head("C2 Flat windows: what empties the column")
    print("A planted run of L identical bars (high == low == close) in the")
    print("walk, ending at bar 800. O is NaN once the window is all flat,")
    print("which needs L >= 10, and each NaN O empties 5 TAO bars.")
    print()
    print(f"{'patch':>6} {'O NaN':>6} {'emptied':>8}")
    base = _walk()
    ref = _run(base)
    for patch in (5, 9, 10, 11, 15):
        df = base.copy()
        v = float(base["close"].iloc[800 - patch + 1])
        df.iloc[800 - patch + 1:801] = v
        rng = df["high"].rolling(LENGTH).max() - df["low"].rolling(LENGTH).min()
        col = _run(df)
        print(f"{patch:>6} {int((rng == 0).sum()):>6} "
              f"{int((col.isna() & ref.notna()).sum()):>8}")


def section_D():
    _head("D Gate D -- scale invariance")
    print(f"{'frame':>13} {'factor':>11} {'bit-equal':>10} {'masks':>6} "
          f"{'max abs':>11} {'spearman':>9}")
    for name in FIRING:
        df = FRAMES[name]()
        col = _run(df)
        for factor in (8.0, 64.0, 2.0 ** -20, 2.0 ** 300, 10.0, 3.7, 0.1):
            other = _run(df * factor)
            print(f"{name:>13} {factor:>11.4g} "
                  f"{str(_bit_equal(col, other)):>10} "
                  f"{str(bool((col.isna() == other.isna()).all())):>6} "
                  f"{_abs(col, other):>11.3e} {_spearman(col, other):>9.4f}")
    print()
    print("A LEVEL SHIFT: the formula is differences over a difference, so it")
    print("cancels in exact arithmetic -- but not bit for bit.")
    print()
    print(f"{'shift':>8} {'bit-equal':>10} {'masks':>6} {'max abs':>11}")
    df = _walk()
    col = _run(df)
    for shift in (1.0, 50.0, 1e6):
        other = _run(df + shift)
        print(f"{shift:>8g} {str(_bit_equal(col, other)):>10} "
              f"{str(bool((col.isna() == other.isna()).all())):>6} "
              f"{_abs(col, other):>11.3e}")


def section_F():
    _head("F Non-redundancy against the fork's own columns (SYNTHETIC)")
    from pandas_ta.momentum.cfo import cfo
    from pandas_ta.momentum.stoch import stoch
    from pandas_ta.momentum.willr import willr
    from pandas_ta.statistics.rank import rank
    others = {
        "WILLR_10": lambda d: willr(d["high"], d["low"], d["close"], 10),
        "STOCHk_10_3_3": lambda d: stoch(d["high"], d["low"], d["close"],
                                         k=10).iloc[:, 0],
        "STOCHk_14_3_3": lambda d: stoch(d["high"], d["low"],
                                         d["close"]).iloc[:, 0],
        "CFO_9": lambda d: cfo(d["close"]),
        "RANK_5": lambda d: rank(d["close"])["RANK_5"],
    }
    print(f"{'frame':>13} " + " ".join(f"{k:>14}" for k in others))
    for name in FIRING:
        df = FRAMES[name]()
        col = _run(df)
        print(f"{name:>13} " + " ".join(
            f"{_spearman(col, fn(df)):>14.4f}" for fn in others.values()))


def section_W():
    _head("W The five wiring touch points")
    import pandas_ta as ta
    df = _walk(n=400)
    col = _run(df)
    print("1 module       : pandas_ta/momentum/tao.py")
    print(f"2 package      : {hasattr(ta.momentum, 'tao')}")
    print(f"3 Category     : {'tao' in ta.Category['momentum']} "
          f"(momentum has {len(ta.Category['momentum'])})")
    print(f"4 accessor     : {hasattr(df.ta, 'tao')}")
    print("5 tests        : tests/test_tao.py")
    print(f"column name    : {col.name}")
    print(f"accessor equal : {_bit_equal(col, df.ta.tao())}")
    print(f"Category total : {sum(len(v) for v in ta.Category.values())}")
    import ast
    import re
    path = Path(__file__).resolve().with_name("gen_indicator_dictionary.py")
    tree = ast.parse(path.read_text(encoding="utf-8"))
    node = next(n for n in tree.body
                if isinstance(n, ast.FunctionDef) and n.name == "desc")
    ns = {"re": re}
    exec(compile(ast.Module(body=[node], type_ignores=[]), "<desc>", "exec"),
         ns)
    body = []
    for line in tao.__doc__.splitlines()[1:]:
        if line.strip():
            body.append(line.strip())
        elif body:
            break
    paragraph = " ".join(body)
    print(f"paragraph      : {len(paragraph)} characters, survives the "
          f"dictionary cut whole: {ns['desc']({'desc': paragraph}) == paragraph}")


def section_W2():
    _head("W2 The dictionary's ML-form tags, counted")
    path = ROOT / "docs" / "IndicatorDictionary.md"
    tags = ["PX2", "PX", "SF", "BIN", "ORD", "CONST", "??"]
    counts = {t: 0 for t in tags}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("| `"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 5:
            continue
        for token in cells[3].replace("<br>", " ").split():
            if token in counts:
                counts[token] += 1
    print(f"tagged columns : {sum(counts.values())}")
    for t in tags:
        print(f"{t:>15}: {counts[t]}")


def section_Z():
    _head("Z Cost")
    print(f"{'bars':>10} {'peak MB':>10} {'ms':>8} {'ms (2nd)':>10}")
    for n in (100_000, 400_000):
        df = _walk(n=n)
        tracemalloc.start()
        _run(df)
        peak = tracemalloc.get_traced_memory()[1] / 1e6
        tracemalloc.stop()
        times = [timeit.timeit(lambda: _run(df), number=3) / 3 * 1e3
                 for _ in range(2)]
        print(f"{n:>10} {peak:>10.1f} {times[0]:>8.1f} {times[1]:>10.1f}")


SECTIONS = {
    "A1": section_A1, "A2": section_A2, "A3": section_A3,
    "B": section_B, "B1": section_B1, "C": section_C, "C2": section_C2,
    "D": section_D, "F": section_F, "W": section_W, "W2": section_W2,
    "Z": section_Z,
}


if __name__ == "__main__":
    want = [a.upper() for a in sys.argv[1:]] or list(SECTIONS)
    for key in want:
        if key not in SECTIONS:
            raise SystemExit(f"unknown section {key!r}; pick from {list(SECTIONS)}")
        SECTIONS[key]()
