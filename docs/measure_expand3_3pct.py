# -*- coding: utf-8 -*-
"""EXPAND3-3PCT (PandasTa issue #201): every number in `docs/Expand33PctMeasured.md`.

    python docs/measure_expand3_3pct.py          # every section, in order
    python docs/measure_expand3_3pct.py A1 D     # named sections only

One section per gate limb, printed and never derived: the repo's dominant
defect is "a claim written before it was measured", so this file is the
only place a figure in the receipt, the module docstring or
`tests/test_expand3_3pct.py` may come from.

Source: Reddit r/TradingView 1jlvqer (2025-03-28), tier 4:

    highSignal = high[2]*1.03 <= high[1] and high[1]*1.03 <= high
    lowSignal  = the mirror with lows 3% lower
    EXPAND3_3.0 = highSignal - lowSignal
"""
import sys
import timeit
import tracemalloc
from pathlib import Path

import numpy as np
from pandas import DataFrame, Series, date_range

from pandas_ta.trend.expand3_3pct import expand3_3pct

N = 1500
LEVEL = 100.0
PCT = 3.0
#: First bar that can carry a value.
WARMUP = 2
OFFSETS = list(range(N - 36, N))
ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "pandas_ta" / "trend" / "expand3_3pct.py"


# ------------------------------------------------------------------ frames


def _index(n):
    return date_range("2020-01-01", periods=n, freq="min")


def _ohlc(close, seed, wick, tick=None):
    """Open = previous close; high / low = the body widened by a half-normal
    wick, so high >= max(open, close) and low <= min(open, close)."""
    rng = np.random.default_rng(seed + 1_000)
    n = close.size
    open_ = np.r_[close[0], close[:-1]]
    high = np.maximum(open_, close) * (1.0 + np.abs(rng.normal(0.0, wick, n)))
    low = np.minimum(open_, close) * (1.0 - np.abs(rng.normal(0.0, wick, n)))
    if tick:
        high, low = (np.round(x / tick) * tick for x in (high, low))
    idx = _index(n)
    return DataFrame({"high": high, "low": low}, index=idx)


def _path(seed, n, mu=0.0, sigma=0.02, t=None):
    rng = np.random.default_rng(seed)
    r = rng.standard_t(t, n) * sigma * 0.6 if t else rng.normal(mu, sigma, n)
    return LEVEL * np.exp(np.cumsum(r))


def _walk(seed=7, n=N):
    return _ohlc(_path(seed, n), seed, 0.01)


def _trend(seed=11, n=N):
    return _ohlc(_path(seed, n, mu=0.01, sigma=0.02), seed, 0.01)


def _range_bound(seed=13, n=N):
    rng = np.random.default_rng(seed)
    x = np.zeros(n)
    for i in range(1, n):
        x[i] = 0.9 * x[i - 1] + rng.normal(0.0, 0.03)
    return _ohlc(LEVEL * np.exp(x), seed, 0.01)


def _grid(seed=17, n=N):
    return _ohlc(_path(seed, n), seed, 0.01, tick=0.01)


def _heavy(seed=19, n=N):
    return _ohlc(_path(seed, n, t=2.0), seed, 0.01)


def _jump(seed=23, n=N):
    p = _path(seed, n) * np.where(np.arange(n) >= n // 2, 1.5, 1.0)
    return _ohlc(p, seed, 0.01)


def _calm(seed=29, n=N):
    """0.5% bars: a 3% step is ~6 sigma, so the column almost never fires."""
    return _ohlc(_path(seed, n, sigma=0.005), seed, 0.002)


def _coarse(seed=31, n=N):
    """A walk rounded to a 1.0 tick at level 100 -- many exact high / low
    ties, and steps that land exactly on 3 ticks = 3%."""
    return _ohlc(_path(seed, n), seed, 0.01, tick=1.0)


def _flat(n=N):
    v = np.full(n, LEVEL)
    return DataFrame({"high": v, "low": v}, index=_index(n))


FRAMES = {
    "walk": _walk, "trend": _trend, "range-bound": _range_bound,
    "grid": _grid, "heavy-tailed": _heavy, "jump": _jump, "calm": _calm,
    "coarse": _coarse, "flat": _flat,
}
NAMES = list(FRAMES)
FIRING = [n for n in NAMES if n != "flat"]


def _run(df, fn=None, **kw):
    return (fn or expand3_3pct)(df["high"], df["low"], **kw)


# ----------------------------------------------------------------- helpers


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


# ----------------------------------------------------------------- oracle


def _oracle(df, up_k=1.03, dn_k=0.97, low_reciprocal=False):
    """The source's expression by scalar loops with the float LITERALS 1.03
    and 0.97, no pandas operation. `low_reciprocal=True` reads the low leg
    the other way: `low[1] * 1.03 <= low[2] and low * 1.03 <= low[1]`."""
    h = df["high"].to_numpy(float)
    lo = df["low"].to_numpy(float)
    n = h.size
    out = np.full(n, np.nan)
    for i in range(2, n):
        w = (h[i - 2], h[i - 1], h[i], lo[i - 2], lo[i - 1], lo[i])
        if any(np.isnan(x) for x in w):
            continue
        up = h[i - 2] * up_k <= h[i - 1] and h[i - 1] * up_k <= h[i]
        if low_reciprocal:
            dn = lo[i - 1] * up_k <= lo[i - 2] and lo[i] * up_k <= lo[i - 1]
        else:
            dn = lo[i - 2] * dn_k >= lo[i - 1] and lo[i - 1] * dn_k >= lo[i]
        out[i] = float(up) - float(dn)
    return Series(out, index=df.index)


# ----------------------------------------------------------------- mutants

H1_LINE = "    h1 = high.shift(1)"
H2_LINE = "    h2 = high.shift(2)"
L1_LINE = "    l1 = low.shift(1)"
L2_LINE = "    l2 = low.shift(2)"
UP_LINE = "    up = (h2 * up_k <= h1) & (h1 * up_k <= high)"
DN_LINE = "    dn = (l2 * dn_k >= l1) & (l1 * dn_k >= low)"
OUT_LINE = "    expand = (up.astype(float) - dn.astype(float)).where(valid)"

#: The five the tests pin: each reads bar T+1 for bar T and is caught.
CAUSALITY_MUTANTS = [
    ("h2-lead", H2_LINE, "    h2 = high.shift(-1)"),
    ("l2-lead", L2_LINE, "    l2 = low.shift(-1)"),
    ("up-early", UP_LINE,
     "    up = ((h2 * up_k <= h1) & (h1 * up_k <= high)).shift(-1, fill_value=False)"),
    ("dn-early", DN_LINE,
     "    dn = ((l2 * dn_k >= l1) & (l1 * dn_k >= low)).shift(-1, fill_value=False)"),
    ("output-early", OUT_LINE,
     "    expand = (up.astype(float) - dn.astype(float)).where(valid).shift(-1)"),
]
#: Disclosed, NOT pinned: live, but a random future almost never lands
#: bar T+1 inside the narrow window `[high[T-2]*1.03, high[T]/1.03]` the
#: mutated comparison needs, so a blind sweep barely sees them (section B1).
WEAK_MUTANTS = [
    ("h1-lead", H1_LINE, "    h1 = high.shift(-1)"),
    ("l1-lead", L1_LINE, "    l1 = low.shift(-1)"),
]


def _mutant(old, new):
    src = SOURCE.read_text(encoding="utf-8")
    assert src.count(old) == 1, f"{old!r} occurs {src.count(old)} times"
    ns = {}
    exec(compile(src.replace(old, new), "<mutant>", "exec"), ns)
    return ns["expand3_3pct"]


def _futures(df, j, spread=3.0):
    """Two frames that agree BIT FOR BIT on bars < j (multiplied by exactly
    1.0) and differ wholly on bars >= j: every high and low from j on is
    scaled by one per-bar factor, up in one future and down in the other."""
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
    _head("A1 Gate A -- the source's expression by scalar loops, float literals")
    print(f"{'frame':>13} {'non-NaN':>8} {'bit-equal':>10} {'differ':>7}")
    for name in NAMES:
        df = FRAMES[name]()
        col, orc = _run(df), _oracle(df)
        print(f"{name:>13} {int(col.notna().sum()):>8} "
              f"{str(_bit_equal(col, orc)):>10} {_differs(col, orc):>7}")


def section_A2():
    _head("A2 The low leg read the other way (`low[1] * 1.03 <= low[2]`)")
    print("bars where the reciprocal reading of the low leg differs from the")
    print("shipped `low[2] * 0.97 >= low[1]` reading")
    print(f"{'frame':>13} {'-1 shipped':>11} {'-1 recip':>9} {'differ':>7}")
    for name in NAMES:
        df = FRAMES[name]()
        col, alt = _run(df), _oracle(df, low_reciprocal=True)
        print(f"{name:>13} {int((col == -1).sum()):>11} "
              f"{int((alt == -1).sum()):>9} {_differs(col, alt):>7}")


def section_A3():
    _head("A3 Ties -- a step exactly on 3% fires")
    h = Series([100.0, 103.0, 106.09, 106.09, 109.2727])
    lo = Series([100.0, 97.0, 94.09, 94.09, 91.2673])
    df = DataFrame({"high": h, "low": lo})
    print(f"100 * 1.03   == 103.0   : {100.0 * 1.03 == 103.0}")
    print(f"103 * 1.03   == 106.09  : {103.0 * 1.03 == 106.09}")
    print(f"106.09*1.03  == 109.2727: {106.09 * 1.03 == 109.2727}")
    print(f"100 * 0.97   == 97.0    : {100.0 * 0.97 == 97.0}")
    print(f"97 * 0.97    == 94.09   : {97.0 * 0.97 == 94.09}")
    print(f"94.09 * 0.97 == 91.2673 : {94.09 * 0.97 == 91.2673}")
    print(f"highs only   : {list(_run(DataFrame({'high': h, 'low': h})))}")
    print(f"lows only    : {list(_run(DataFrame({'high': lo * 0 + 1, 'low': lo})))}")
    print(f"both legs    : {list(_run(df))}")
    print()
    print("exact-boundary bars per frame (any of the four comparisons an")
    print("exact float equality):")
    print(f"{'frame':>13} {'boundary':>9}")
    for name in NAMES:
        d = FRAMES[name]()
        hh, ll = d["high"], d["low"]
        h1, h2, l1, l2 = hh.shift(1), hh.shift(2), ll.shift(1), ll.shift(2)
        eq = ((h2 * 1.03 == h1) | (h1 * 1.03 == hh)
              | (l2 * 0.97 == l1) | (l1 * 0.97 == ll))
        print(f"{name:>13} {int(eq.sum()):>9}")


def section_B():
    _head("B Gate B -- the blind causality sweep, every offset")
    print(f"{'frame':>13} {'offsets':>8} {'caught':>7}")
    offsets = list(range(1, N))
    for name in NAMES:
        print(f"{name:>13} {len(offsets):>8} "
              f"{_sweep(expand3_3pct, FRAMES[name](), offsets):>7}")


def section_B1():
    _head("B1 Gate B -- look-ahead mutants, read off the shipped source")
    print(f"{'mutant':>13} " + " ".join(f"{n[:7]:>7}" for n in NAMES))
    print("live (bars differing from the real module on the frame):")
    for label, old, new in CAUSALITY_MUTANTS + WEAK_MUTANTS:
        fn = _mutant(old, new)
        print(f"{label:>13} " + " ".join(
            f"{_differs(_run(FRAMES[n]()), _run(FRAMES[n](), fn)):>7}"
            for n in NAMES))
    for n_bars in (400, N):
        offs = list(range(1, n_bars))
        print(f"caught (of {len(offs)} offsets, every bar, {n_bars}-bar frames):")
        for label, old, new in CAUSALITY_MUTANTS + WEAK_MUTANTS:
            fn = _mutant(old, new)
            print(f"{label:>13} " + " ".join(
                f"{_sweep(fn, FRAMES[n](n=n_bars), offs):>7}" for n in NAMES),
                flush=True)


def section_C():
    _head("C Gate C -- reachability")
    print(f"{'frame':>13} {'bars':>5} {'NaN':>4} {'+1':>4} {'-1':>4} "
          f"{'0':>5} {'both':>5} {'first fire':>10}")
    for name in NAMES:
        df = FRAMES[name]()
        col = _run(df)
        h, lo = df["high"], df["low"]
        up = (h.shift(2) * 1.03 <= h.shift(1)) & (h.shift(1) * 1.03 <= h)
        dn = (lo.shift(2) * 0.97 >= lo.shift(1)) & (lo.shift(1) * 0.97 >= lo)
        fired = np.flatnonzero((col.fillna(0) != 0).to_numpy())
        print(f"{name:>13} {col.size:>5} {int(col.isna().sum()):>4} "
              f"{int((col == 1).sum()):>4} {int((col == -1).sum()):>4} "
              f"{int((col == 0).sum()):>5} {int((up & dn).sum()):>5} "
              f"{(int(fired[0]) if fired.size else -1):>10}")
    print()
    print("`both` = bars where both legs fire and the column nets to 0.")


def section_CT():
    _head("CT Gate A / C on the TEST module's own 400-bar frames")
    print("`tests/test_expand3_3pct.py` uses the same builders and seeds at")
    print("N=400 bars; a shorter series fires on different bars, so it is")
    print("measured separately rather than reusing A1 / C's numbers.")
    print()
    print(f"{'frame':>13} {'bit-equal':>10} {'+1':>4} {'-1':>4} {'0':>5} {'NaN':>4}")
    for name in NAMES:
        df = FRAMES[name](n=400)
        col = _run(df)
        print(f"{name:>13} {str(_bit_equal(col, _oracle(df))):>10} "
              f"{int((col == 1).sum()):>4} {int((col == -1).sum()):>4} "
              f"{int((col == 0).sum()):>5} {int(col.isna().sum()):>4}")


def section_D():
    _head("D Gate D -- scale")
    print(f"{'frame':>13} " + " ".join(f"{f:>7}" for f in
          ("x8", "x64", "x2^-20", "x2^300", "x10", "x3.7", "x0.1", "+1")))
    print("cells: bars that differ from the unscaled column (0 = identical,"
          " NaN masks included)")
    for name in NAMES:
        df = FRAMES[name]()
        col = _run(df)
        cells = [_differs(col, _run(df * f)) for f in
                 (8.0, 64.0, 2.0 ** -20, 2.0 ** 300, 10.0, 3.7, 0.1)]
        cells.append(_differs(col, _run(df + 1.0)))
        print(f"{name:>13} " + " ".join(f"{c:>7}" for c in cells))
    print()
    print("x10 / x3.7 / x0.1 NaN masks identical on every frame: " + str(all(
        bool((_run(FRAMES[n]()).isna() == _run(FRAMES[n]() * f).isna()).all())
        for n in NAMES for f in (10.0, 3.7, 0.1))))
    print("nonzero bars (0 < fires < n):")
    for name in NAMES:
        col = _run(FRAMES[name]())
        print(f"{name:>13} {int((col.fillna(0) != 0).sum()):>5} of {col.size}")


def section_W():
    import pandas_ta as ta
    _head("W Wiring")
    df = _walk()
    col = _run(df)
    print(f"2 package      : {hasattr(ta.trend, 'expand3_3pct')}")
    print(f"3 Category     : {'expand3_3pct' in ta.Category['trend']} "
          f"(trend has {len(ta.Category['trend'])})")
    print(f"4 accessor     : {hasattr(df.ta, 'expand3_3pct')}")
    print("5 tests        : tests/test_expand3_3pct.py")
    print(f"column name    : {col.name}")
    print(f"accessor equal : {_bit_equal(col, df.ta.expand3_3pct())}")
    print(f"Category total : {sum(len(v) for v in ta.Category.values())}")


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
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("| `expand3_3pct`"):
            print(line[:160])


def _e0_frame(seed, n=1500):
    """The pre-port equivalence screen's frames: a lognormal close at 1% /
    3% / 5% per-bar vol (seed % 3), wick half-normal at half the vol,
    rounded to a 0.05 (odd seed) or 0.01 (even seed) tick."""
    rng = np.random.default_rng(seed)
    vol = [0.01, 0.03, 0.05][seed % 3]
    c = 100 * np.exp(np.cumsum(rng.normal(0, vol, n)))
    o = np.r_[c[0], c[:-1]]
    h = np.maximum(o, c) * (1 + np.abs(rng.normal(0, vol / 2, n)))
    lo = np.minimum(o, c) * (1 - np.abs(rng.normal(0, vol / 2, n)))
    tick = 0.05 if seed % 2 else 0.01
    rd = lambda x: np.round(x / tick) * tick  # noqa: E731
    return DataFrame({"high": rd(h), "low": rd(lo), "close": rd(c)})


def section_E0():
    import pandas_ta as ta
    _head("E0 Pre-port equivalence screen -- NOT Gate E")
    print("12 synthetic tick-rounded frames x 1,500 bars; per-frame Spearman")
    print("rho of EXPAND3_3.0 vs the nearest shipped columns, bars >= 60.")
    print("A frame where the column never fires gives NaN and is left out")
    print("of the median.")
    comps = {
        "ROC_2": lambda d: ta.roc(d["close"], 2),
        "INC_2": lambda d: ta.increasing(d["close"], 2),
        "HIGHER_HIGH-LOWER_LOW": lambda d: (lambda b: b.iloc[:, 2] - b.iloc[:, 3])(
            ta.bos(d["high"], d["low"], d["close"])),
    }
    rows = {k: [] for k in comps}
    fires, ties = [], []
    for seed in range(12):
        d = _e0_frame(seed)
        x = _run(d)
        fires.append(int((x.fillna(0) != 0).sum()))
        ties.append(int((d["high"] == d["high"].shift(1)).sum()))
        for k, f in comps.items():
            v = f(d)
            m = x.notna() & v.notna() & (d.index >= 60)
            xs, vs = x[m], v[m]
            rows[k].append(float("nan") if xs.nunique() < 2 or vs.nunique() < 2
                           else float(xs.corr(vs, method="spearman")))
    print(f"fires per frame      : {fires}")
    print(f"exact high ties      : {ties}")
    for k, v in rows.items():
        a = np.array(v)
        ok = a[~np.isnan(a)]
        print(f"{k:>22}: median {np.median(ok):.4f} over {ok.size} frames, "
              f"range [{ok.min():.4f}, {ok.max():.4f}]")


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
    "A1": section_A1, "A2": section_A2, "A3": section_A3, "B": section_B,
    "B1": section_B1, "C": section_C, "CT": section_CT, "D": section_D, "E0": section_E0, "W": section_W,
    "W2": section_W2, "Z": section_Z,
}


if __name__ == "__main__":
    want = [a.upper() for a in sys.argv[1:]] or list(SECTIONS)
    for key in want:
        if key not in SECTIONS:
            raise SystemExit(f"unknown section {key!r}; pick from {list(SECTIONS)}")
        SECTIONS[key]()
