# -*- coding: utf-8 -*-
"""TDI-20-2 (PandasTa issue #148): every number in `docs/TdiMeasured.md`.

    python docs/measure_tdi.py          # every section, in order
    python docs/measure_tdi.py A1 D     # named sections only

One section per gate limb, printed and never derived: the repo's dominant
defect is "a claim written before it was measured", so this file is the
only place a figure in the receipt, the module docstring or
`tests/test_tdi.py` may come from.

Source: R TTR (GPL-2.0), `TDI.R`:

    mom[T]     = price[T] - price[T - length]
    TDI_n_m[T] = (|sum_n mom| - (sum_2n |mom| - sum_n |mom|)) / price[T]

n = length, 2n = multiple * length. Ported from that published formula
(stated in issue #148), never read from the R source.
"""
import sys
import timeit
import tracemalloc
from pathlib import Path

import numpy as np
from pandas import Series, date_range

from pandas_ta.trend.tdi import tdi

N = 1500
LEVEL = 100.0
LENGTH = 20
MULTIPLE = 2
LONG_LENGTH = MULTIPLE * LENGTH
#: First bar that can carry a value: `length + multiple * length - 1`.
WARMUP = LENGTH + LONG_LENGTH - 1
OFFSETS = list(range(N - 36, N))
ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "pandas_ta" / "trend" / "tdi.py"


# ------------------------------------------------------------------ frames


def _index(n):
    return date_range("2020-01-01", periods=n, freq="h")


def _path(seed, n, mu=0.0, sigma=0.01, t=None):
    rng = np.random.default_rng(seed)
    r = rng.standard_t(t, n) * sigma * 0.6 if t else rng.normal(mu, sigma, n)
    return LEVEL * np.exp(np.cumsum(r))


def _series(values, tick=None):
    if tick:
        values = np.round(values / tick) * tick
    return Series(values, index=_index(len(values)))


def _walk(seed=7, n=N):
    return _series(_path(seed, n))


def _trend(seed=11, n=N):
    return _series(_path(seed, n, mu=0.003, sigma=0.008))


def _range_bound(seed=13, n=N):
    rng = np.random.default_rng(seed)
    x = np.zeros(n)
    for i in range(1, n):
        x[i] = 0.9 * x[i - 1] + rng.normal(0.0, 0.02)
    return _series(LEVEL * np.exp(x))


def _grid(seed=17, n=N):
    return _series(_path(seed, n), tick=0.01)


def _heavy(seed=19, n=N):
    return _series(_path(seed, n, t=2.0))


def _jump(seed=23, n=N):
    p = _path(seed, n)
    return _series(p * np.where(np.arange(n) >= n // 2, 1.5, 1.0))


def _flat(n=N):
    return _series(np.full(n, LEVEL))


def _coarse(seed=7, n=N):
    """A walk rounded to a 0.5 tick -- flat runs happen by rounding."""
    return _series(_path(seed, n, sigma=0.002), tick=0.5)


FRAMES = {
    "walk": _walk, "trend": _trend, "range-bound": _range_bound,
    "grid": _grid, "heavy-tailed": _heavy, "jump": _jump, "flat": _flat,
    "coarse": _coarse,
}
NAMES = list(FRAMES)
FIRING = [n for n in NAMES if n != "flat"]


def _run(close, fn=None, **kw):
    return (fn or tdi)(close, **kw)


# ----------------------------------------------------------------- helpers


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


# ----------------------------------------------------------------- oracle


def _oracle(close, length=LENGTH, multiple=MULTIPLE):
    """The issue's formula by explicit scalar loops: a fresh n-bar sum of
    signed momentum and fresh n-bar / 2n-bar sums of absolute momentum, no
    pandas operation, no fillna."""
    c = close.to_numpy(float)
    n = c.size
    long_length = multiple * length
    mom = np.full(n, np.nan)
    for i in range(length, n):
        mom[i] = c[i] - c[i - length]
    out = np.full(n, np.nan)
    for i in range(length + long_length - 1, n):
        short_w = mom[i - length + 1:i + 1]
        long_w = mom[i - long_length + 1:i + 1]
        if np.isnan(short_w).any() or np.isnan(long_w).any():
            continue
        short_sum = 0.0
        short_abs = 0.0
        for x in short_w:
            short_sum += x
            short_abs += abs(x)
        long_abs = 0.0
        for x in long_w:
            long_abs += abs(x)
        out[i] = (abs(short_sum) - (long_abs - short_abs)) / c[i]
    return Series(out, index=close.index)


# ----------------------------------------------------------------- mutants

MOM_LINE = "    mom = close - close.shift(length)"
SHORT_SUM_LINE = "    short_sum = mom.rolling(length).sum()"
SHORT_ABS_LINE = "    short_abs_sum = abs_mom.rolling(length).sum()"
LONG_ABS_LINE = "    long_abs_sum = abs_mom.rolling(long_length).sum()"
OUT_LINE = "    tdi = (short_sum.abs() - (long_abs_sum - short_abs_sum)) / close"

CAUSALITY_MUTANTS = [
    ("mom-lead", MOM_LINE, "    mom = close.shift(-length) - close"),
    ("short-sum-centred", SHORT_SUM_LINE,
     "    short_sum = mom.rolling(length, center=True).sum()"),
    ("short-abs-centred", SHORT_ABS_LINE,
     "    short_abs_sum = abs_mom.rolling(length, center=True).sum()"),
    ("long-abs-centred", LONG_ABS_LINE,
     "    long_abs_sum = abs_mom.rolling(long_length, center=True).sum()"),
    ("output-early", OUT_LINE,
     "    tdi = ((short_sum.abs() - (long_abs_sum - short_abs_sum))"
     " / close).shift(-1)"),
]


def _mutant(old, new):
    src = SOURCE.read_text(encoding="utf-8")
    assert src.count(old) == 1, f"{old!r} occurs {src.count(old)} times"
    ns = {}
    exec(compile(src.replace(old, new), "<mutant>", "exec"), ns)
    return ns["tdi"]


def _futures(close, j, spread=3.0):
    """Two series that agree BIT FOR BIT on bars < j (multiplied by exactly
    1.0) and differ wholly on bars >= j: every price from j on is scaled by
    one per-bar factor, up in one future and down in the other."""
    n = len(close)
    rng = np.random.default_rng(90_001 + j)
    u = rng.random(n)
    up, dn = np.ones(n), np.ones(n)
    up[j:] = 1.0 + spread * u[j:]
    dn[j:] = 1.0 / (1.0 + spread * u[j:])
    return close * up, close * dn


def _caught_at(fn, close, j):
    a, b = (_run(c, fn).iloc[:j] for c in _futures(close, j))
    return not _bit_equal(a, b)


def _sweep(fn, close, offsets=None):
    return sum(_caught_at(fn, close, j) for j in (offsets or OFFSETS))


# ---------------------------------------------------------------- sections


def section_A1():
    _head("A1 Gate A -- the issue's formula by explicit scalar loops")
    print(f"{'frame':>13} {'fired':>6} {'bit-equal':>10} {'masks':>6} "
          f"{'differ':>7} {'max abs':>11} {'spearman':>9}")
    for name in NAMES:
        close = FRAMES[name]()
        col, orc = _run(close), _oracle(close)
        print(f"{name:>13} {int(col.notna().sum()):>6} "
              f"{str(_bit_equal(col, orc)):>10} "
              f"{str(bool((col.isna() == orc.isna()).all())):>6} "
              f"{_differs(col, orc):>7} {_abs(col, orc):>11.3e} "
              f"{_spearman(col, orc):>9.4f}")
    print()
    print("`max abs` is in the ratio's own units (close-divided). A")
    print("non-zero value is pandas' online rolling sum against a fresh")
    print("per-window sum.")


def section_A1T():
    _head("A1T Gate A on the TEST module's own 400-bar frames")
    print("`tests/test_tdi.py` uses the same builders and seeds at N=400")
    print("bars, not 1,500 -- a shorter series changes which bars round")
    print("differently, so this is measured separately rather than reusing")
    print("A1's number.")
    print()
    print(f"{'frame':>13} {'fired':>6} {'max abs':>11}")
    worst_name, worst_val = None, -1.0
    for name in NAMES:
        close = FRAMES[name](n=400)
        col, orc = _run(close), _oracle(close)
        val = _abs(col, orc)
        print(f"{name:>13} {int(col.notna().sum()):>6} {val:>11.3e}")
        if val > worst_val:
            worst_name, worst_val = name, val
    print()
    print(f"worst: {worst_name} {worst_val:.3e}")
    print("(this happens to equal section D's x10 figure on `jump` -- a")
    print("coincidence of this run, not a leftover copy: §A1T and §D compare")
    print("different things -- the oracle loop vs. a price rescale -- on the")
    print("same frame.)")


def section_B():
    _head("B Gate B -- the blind causality sweep, every offset")
    print(f"{'frame':>13} {'offsets':>8} {'caught':>7}")
    offsets = list(range(1, N))
    for name in NAMES:
        print(f"{name:>13} {len(offsets):>8} "
              f"{_sweep(tdi, FRAMES[name](), offsets):>7}")


def section_B1():
    _head("B1 Gate B -- five look-ahead mutants, read off the shipped source")
    print(f"{'mutant':>18} {'live':>5} " +
          " ".join(f"{n[:9]:>9}" for n in NAMES))
    for label, old, new in CAUSALITY_MUTANTS:
        fn = _mutant(old, new)
        live, caught = 0, []
        for name in NAMES:
            close = FRAMES[name]()
            live += int(_differs(_run(close), _run(close, fn)) > 0)
            caught.append(_sweep(fn, close))
        print(f"{label:>18} {live:>5} " + " ".join(f"{c:>9}" for c in caught))
    print()
    print(f"each frame contributes {len(OFFSETS)} offsets "
          f"({OFFSETS[0]} .. {OFFSETS[-1]})")


def section_C():
    _head("C Gate C -- reachability")
    print(f"{'frame':>13} {'bars':>6} {'fired':>6} {'first':>6} "
          f"{'distinct':>9} {'min':>11} {'max':>11}")
    for name in NAMES:
        close = FRAMES[name]()
        col = _run(close)
        v = col.dropna()
        if v.size:
            first = int(np.flatnonzero(col.notna().to_numpy())[0])
            print(f"{name:>13} {col.size:>6} {v.size:>6} {first:>6} "
                  f"{v.nunique():>9} {v.min():>11.6f} {v.max():>11.6f}")
        else:
            print(f"{name:>13} {col.size:>6} {0:>6} {-1:>6} {0:>9} "
                  f"{'--':>11} {'--':>11}")
    print()
    print(f"expected constant warm-up: {WARMUP} leading NaN bars, "
          f"first value at bar {WARMUP}.")


def section_C2():
    _head("C2 Flat runs: what empties the column")
    print("A planted run of L identical bars, ending at bar 800 of a walk.")
    print("`mom` is 0 (not NaN) wherever both ends of its window are inside")
    print("the flat run, so TDI reads a real (non-NaN) value there, often 0.")
    print()
    print(f"{'patch':>6} {'bars 0 in window':>18} {'emptied':>8}")
    base = _walk()
    ref = _run(base)
    for patch in (5, 20, 40, 59, 60, 65):
        close = base.copy()
        v = float(base.iloc[800 - patch + 1])
        close.iloc[800 - patch + 1:801] = v
        col = _run(close)
        zero_mom = int((col.iloc[800 - LENGTH + 1:801] == 0).sum())
        print(f"{patch:>6} {zero_mom:>18} "
              f"{int((col.isna() & ref.notna()).sum()):>8}")


def section_D():
    _head("D Gate D -- scale invariance")
    print(f"{'frame':>13} {'factor':>11} {'bit-equal':>10} {'masks':>6} "
          f"{'max abs':>11} {'spearman':>9}")
    for name in FIRING:
        close = FRAMES[name]()
        col = _run(close)
        for factor in (8.0, 64.0, 2.0 ** -20, 2.0 ** 300, 10.0, 3.7, 0.1):
            other = _run(close * factor)
            print(f"{name:>13} {factor:>11.4g} "
                  f"{str(_bit_equal(col, other)):>10} "
                  f"{str(bool((col.isna() == other.isna()).all())):>6} "
                  f"{_abs(col, other):>11.3e} {_spearman(col, other):>9.4f}")
    print()
    print("A LEVEL SHIFT is NOT expected to be invariant: `mom` and both")
    print("rolling sums cancel an additive constant exactly, but `close`")
    print("itself (the divisor) does not.")
    print()
    print(f"{'shift':>8} {'bit-equal':>10} {'masks':>6} {'max abs':>11}")
    close = _walk()
    col = _run(close)
    for shift in (1.0, 50.0, 1e6):
        other = _run(close + shift)
        print(f"{shift:>8g} {str(_bit_equal(col, other)):>10} "
              f"{str(bool((col.isna() == other.isna()).all())):>6} "
              f"{_abs(col, other):>11.3e}")
    print()
    print(f"{'frame':>13} {'fires':>6} {'n':>6} {'distinct':>9}")
    for name in FIRING:
        col = _run(FRAMES[name]())
        print(f"{name:>13} {int(col.notna().sum()):>6} {col.size:>6} "
              f"{col.dropna().nunique():>9}")


def section_F():
    _head("F Non-redundancy against the fork's own columns (SYNTHETIC)")
    from pandas_ta.momentum.cfo import cfo
    from pandas_ta.momentum.roc import roc
    from pandas_ta.trend.vhf import vhf
    others = {
        "VHF_28": lambda c: vhf(c),
        "CFO_9": lambda c: cfo(c),
        "ROC_10": lambda c: roc(c, 10),
        "ROC_20": lambda c: roc(c, 20),
    }
    print(f"{'frame':>13} " + " ".join(f"{k:>14}" for k in others))
    for name in FIRING:
        close = FRAMES[name]()
        col = _run(close)
        print(f"{name:>13} " + " ".join(
            f"{_spearman(col, fn(close)):>14.4f}" for fn in others.values()))


def section_W():
    _head("W The five wiring touch points")
    import pandas_ta as ta
    close = _walk(n=400)
    col = _run(close)
    df = close.to_frame("close")
    print("1 module       : pandas_ta/trend/tdi.py")
    print(f"2 package      : {hasattr(ta.trend, 'tdi')}")
    print(f"3 Category     : {'tdi' in ta.Category['trend']} "
          f"(trend has {len(ta.Category['trend'])})")
    print(f"4 accessor     : {hasattr(df.ta, 'tdi')}")
    print("5 tests        : tests/test_tdi.py")
    print(f"column name    : {col.name}")
    print(f"accessor equal : {_bit_equal(col, df.ta.tdi())}")
    print(f"Category total : {sum(len(v) for v in ta.Category.values())}")
    body = []
    for line in tdi.__doc__.splitlines()[1:]:
        if line.strip():
            body.append(line.strip())
        elif body:
            break
    paragraph = " ".join(body)
    print(f"paragraph      : {len(paragraph)} characters")


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
        close = _walk(n=n)
        tracemalloc.start()
        _run(close)
        peak = tracemalloc.get_traced_memory()[1] / 1e6
        tracemalloc.stop()
        times = [timeit.timeit(lambda: _run(close), number=3) / 3 * 1e3
                 for _ in range(2)]
        print(f"{n:>10} {peak:>10.1f} {times[0]:>8.1f} {times[1]:>10.1f}")


SECTIONS = {
    "A1": section_A1, "A1T": section_A1T, "B": section_B, "B1": section_B1, "C": section_C,
    "C2": section_C2, "D": section_D, "F": section_F, "W": section_W,
    "W2": section_W2, "Z": section_Z,
}


if __name__ == "__main__":
    want = [a.upper() for a in sys.argv[1:]] or list(SECTIONS)
    for key in want:
        if key not in SECTIONS:
            raise SystemExit(f"unknown section {key!r}; pick from {list(SECTIONS)}")
        SECTIONS[key]()
