# -*- coding: utf-8 -*-
"""B3-INRANGE-COUNT-20 (PandasTa issue #203): every number in
`docs/InrangeCountMeasured.md`.

    python docs/measure_inrange_count.py          # every section, in order
    python docs/measure_inrange_count.py A1 D     # named sections only

One section per gate limb, printed and never derived: the repo's dominant
defect is "a claim written before it was measured", so this file is the only
place a figure in the receipt, the module docstring or
`tests/test_inrange_count.py` may come from.

    cnt[T] = min(cnt[T-1] + 1, n)  if high[T] < highest(high, n)[T-1]
                                   and low[T] > lowest(low, n)[T-1]
             max(cnt[T-1] - 2, 0)  otherwise
    INRC_n = cnt / n

⚠ The millisecond figures of §Z are this machine's and this run's.
"""
import sys
import timeit
import tracemalloc
from pathlib import Path

import numpy as np
import pandas as pd
from pandas import DataFrame, Series, date_range

from pandas_ta.momentum.squeeze import squeeze
from pandas_ta.trend.adx import adx
from pandas_ta.trend.chop import chop
from pandas_ta.trend.vhf import vhf
from pandas_ta.volatility.inrange_count import inrange_count
from pandas_ta.volatility.range_compress_run import range_compress_run

N = 1500
LEVEL = 100.0
LENGTH = 20
#: The blind causality sweep's 36 perturbation points.
OFFSETS = list(range(N - 36, N))
#: Where §G plants a bad bar.
PLANT = 700


# ------------------------------------------------------------------ frames
# Same builders and seeds as `tests/test_inrange_count.py`, which are
# `tests/test_sk_fcb_width.py`'s, so the frame set is shared across ports.


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
    """A walk rounded to a tick coarser than its bar-to-bar move, so a bar
    TYING the prior range's extreme -- outside, under the strict rule -- is
    common instead of impossible."""
    h, l, c = _walk(seed, n, level)
    return (np.round(h / tick) * tick, np.round(l / tick) * tick,
            np.round(c / tick) * tick)


FRAMES = {
    "walk": _walk, "trend": _trend, "range-bound": _range_bound,
    "grid": _grid, "heavy-tailed": _heavy, "jump": _jump, "flat": _flat,
    "coarse": _coarse,
}
NAMES = list(FRAMES)
#: `flat` ties its own range on every bar, so the column is constant 0.0.
MOVING = [n for n in NAMES if n != "flat"]


def _hl(frame):
    return frame[0], frame[1]


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


# ----------------------------------------------------------------- oracles


def _oracle(high, low, length=LENGTH, strict=True):
    """The poster's Pine, transcribed as explicit loops and sharing no code
    with the module: the envelope is re-scanned bar by bar over the
    `length` bars before T, no rolling window, no shift."""
    h = high.to_numpy(dtype=float)
    l = low.to_numpy(dtype=float)
    out = np.full(h.size, np.nan)
    cnt = 0
    for t in range(length, h.size):
        hi, lo = -np.inf, np.inf
        for k in range(t - length, t):
            if h[k] > hi:
                hi = h[k]
            if l[k] < lo:
                lo = l[k]
        inside = (h[t] < hi and l[t] > lo) if strict else \
            (h[t] <= hi and l[t] >= lo)
        cnt = min(cnt + 1, length) if inside else max(cnt - 2, 0)
        out[t] = cnt / length
    return Series(out, index=high.index)


def _non_strict(high, low):
    """The reading NOT taken: `<=` / `>=`, so a tie with the prior range's
    extreme counts as inside."""
    return _oracle(high, low, strict=False)


# ----------------------------------------------------------------- mutants

SOURCE = Path(__file__).resolve().parents[1] / "pandas_ta" / "volatility" \
    / "inrange_count.py"

#: (label, old text, new text). Edits to the SHIPPED source, read off disk.
CAUSALITY_MUTANTS = [
    # The envelope taken one bar AHEAD instead of one bar behind.
    ("high-envelope-lead",
     "    hh = h.rolling(length, min_periods=1).max().shift(1)",
     "    hh = h.rolling(length, min_periods=1).max().shift(-1)"),
    ("low-envelope-lead",
     "    ll = l.rolling(length, min_periods=1).min().shift(1)",
     "    ll = l.rolling(length, min_periods=1).min().shift(-1)"),
    # Tomorrow's high judged against today's envelope.
    ("high-lead",
     "    inrc = Series(_count(h.to_numpy(dtype=float),",
     "    inrc = Series(_count(h.shift(-1).to_numpy(dtype=float),"),
    ("output-early", "    # Offset\n    if offset != 0:",
     "    inrc = inrc.shift(-1)\n    # Offset\n    if offset != 0:"),
]
#: Not a causality mutant: the infinity guard, removed, to price it.
GUARD_OFF = ("    h = high.where(np.isfinite(high))\n"
             "    l = low.where(np.isfinite(low))",
             "    h = high\n    l = low")


def _mutant(old, new):
    src = SOURCE.read_text(encoding="utf-8")
    assert src.count(old) == 1, f"{old!r} occurs {src.count(old)} times"
    ns = {}
    exec(compile(src.replace(old, new), "<mutant>", "exec"), ns)
    return ns["inrange_count"]


def _futures(frame, j, spread=3.0):
    """Three frames that agree BIT FOR BIT on bars < j: the frame itself,
    and the frame with every bar >= j scaled UP by a per-bar factor in
    [1.5, 4] or DOWN by its reciprocal.

    ⚠ Not "scaled up vs scaled down" alone: that pair sends bar j OUTSIDE
    the prior range under BOTH futures, so a mutant that reads bar j's
    verdict (`output-early`) sees the same thing either way -- measured 0
    of 36 on `walk` with that pair. The untouched tail keeps bar j inside
    wherever the frame has it inside. The up tail moves the HIGH envelope
    and the down tail the LOW one, which the two envelope mutants each
    need."""
    h, l, c = frame
    n = c.size
    rng = np.random.default_rng(90_001 + j)
    f = np.ones(n)
    f[j:] = 1.5 + (spread - 0.5) * rng.random(n)[j:]
    up, dn = Series(f, index=c.index), Series(1.0 / f, index=c.index)
    return (h, l, c), (h * up, l * up, c * up), (h * dn, l * dn, c * dn)


def _caught_at(fn, frame, j):
    base, *others = _futures(frame, j)
    a = fn(*_hl(base)).iloc[:j]
    for other in others:
        b = fn(*_hl(other)).iloc[:j]
        if not bool((a.isna() == b.isna()).all()):
            return True
        m = a.notna()
        if not bool((a[m] == b[m]).all()):
            return True
    return False


def _sweep(fn, frame, offsets=None):
    return sum(_caught_at(fn, frame, j) for j in (offsets or OFFSETS))


def _head(title):
    print()
    print("=" * 72)
    print(title)
    print("=" * 72)


# ---------------------------------------------------------------- sections


def section_A1():
    _head("A1 Gate A -- the poster's Pine by explicit loops")
    print(f"{'frame':>13} {'fired':>6} {'masks':>6} {'differ':>7} "
          f"{'bit-equal':>10}")
    pooled = 0
    for name in NAMES:
        frame = FRAMES[name]()
        col, orc = inrange_count(*_hl(frame)), _oracle(*_hl(frame))
        m = col.notna() & orc.notna()
        pooled += int(col.notna().sum())
        print(f"{name:>13} {int(col.notna().sum()):>6} "
              f"{str(bool((col.isna() == orc.isna()).all())):>6} "
              f"{int((col[m] != orc[m]).sum()):>7} "
              f"{str(_bit_equal(col, orc)):>10}")
    print(f"{'POOLED':>13} {pooled:>6}")
    print()
    print("Other lengths on `walk` and `coarse`, bit-equal:")
    for length in (5, 10, 50):
        for name in ("walk", "coarse"):
            frame = FRAMES[name]()
            ok = _bit_equal(inrange_count(*_hl(frame), length=length),
                            _oracle(*_hl(frame), length=length))
            print(f"  length {length:>3} {name:>8}: {ok}")


def section_A4():
    _head("A4 The reading not taken: non-strict `<=` / `>=`")
    print(f"{'frame':>13} {'ties':>6} {'differ':>7} {'spearman':>9}")
    for name in MOVING:
        frame = FRAMES[name]()
        h, l = _hl(frame)
        hh = h.rolling(LENGTH).max().shift(1)
        ll = l.rolling(LENGTH).min().shift(1)
        ties = int(((h == hh) | (l == ll)).sum())
        col, alt = inrange_count(h, l), _non_strict(h, l)
        m = col.notna() & alt.notna()
        print(f"{name:>13} {ties:>6} {int((col[m] != alt[m]).sum()):>7} "
              f"{_spearman(col, alt):>9.4f}")


def section_B():
    _head("B Gate B -- two-futures sweep and read-off mutants")
    print(f"Out of 36 offsets {OFFSETS[0]}..{OFFSETS[-1]}.")
    print()
    print(f"{'frame':>13} {'module':>7} "
          + " ".join(f"{label:>19}" for label, _, _ in CAUSALITY_MUTANTS))
    for name in NAMES:
        frame = FRAMES[name]()
        row = [f"{_sweep(inrange_count, frame):>7}"]
        for _, old, new in CAUSALITY_MUTANTS:
            row.append(f"{_sweep(_mutant(old, new), frame):>19}")
        print(f"{name:>13} " + " ".join(row))
    print()
    print("The module alone, every bar but bar 0 as a split point:")
    for name in NAMES:
        frame = FRAMES[name]()
        dense = list(range(1, N))
        print(f"{name:>13} caught {_sweep(inrange_count, frame, dense):>5} "
              f"of {len(dense):>5}")
    print()
    print("Each mutant is live on unperturbed `walk`:")
    frame = FRAMES["walk"]()
    base = inrange_count(*_hl(frame))
    for label, old, new in CAUSALITY_MUTANTS:
        mut = _mutant(old, new)(*_hl(frame))
        m = base.notna() & mut.notna()
        print(f"{label:>19} both fire {int(m.sum()):>5}  "
              f"moved {int((base[m] != mut[m]).sum()):>5}")


def section_C():
    _head("C Gate C -- reachability, on synthetic frames")
    print(f"{'frame':>13} {'bars':>5} {'fired':>6} {'first':>6} "
          f"{'distinct':>9} {'== 0':>6} {'== 1':>6} {'mean':>7}")
    for name in NAMES:
        col = inrange_count(*_hl(FRAMES[name]()))
        v = col.dropna()
        first = int(np.flatnonzero(col.notna().to_numpy())[0])
        print(f"{name:>13} {col.size:>5} {v.size:>6} {first:>6} "
              f"{v.nunique():>9} {int((v == 0).sum()):>6} "
              f"{int((v == 1).sum()):>6} {v.mean():>7.4f}")
    print()
    print("Steps taken, on `walk`: +1 bars, -2 bars, and how many of the")
    print("-2 bars were clipped at 0.")
    col = inrange_count(*_hl(_walk())).to_numpy() * LENGTH
    d = np.diff(col[LENGTH:])
    print(f"  +1 {int((d == 1).sum())}  -2 {int((d == -2).sum())}  "
          f"-1 (2 -> ... clipped) {int((d == -1).sum())}  "
          f"0 {int((d == 0).sum())}")


def section_D():
    _head("D Gate D -- scale invariance")
    print(f"{'frame':>13} {'x8':>6} {'x64':>6} {'x10':>6} {'x3.7':>6} "
          f"{'x0.1':>6}")
    for name in NAMES:
        frame = FRAMES[name]()
        base = inrange_count(*_hl(frame))
        row = [str(_bit_equal(base, inrange_count(*_hl(_scaled(frame, f)))))
               for f in (8, 64, 10.0, 3.7, 0.1)]
        print(f"{name:>13} " + " ".join(f"{r:>6}" for r in row))
    print()
    print("At other price levels, x8 and x64:")
    for level in (1e-6, 1e+6, 1e+100):
        frame = _walk(level=level)
        base = inrange_count(*_hl(frame))
        print(f"  {level:>8.0e}: fired {int(base.notna().sum())}  "
              f"x8 {_bit_equal(base, inrange_count(*_hl(_scaled(frame, 8))))}"
              f"  x64 "
              f"{_bit_equal(base, inrange_count(*_hl(_scaled(frame, 64))))}")


def section_F():
    _head("F Non-redundancy against fork columns (SYNTHETIC, a disclosure)")
    cols = {}
    for name in MOVING:
        h, l, c = FRAMES[name]()
        col = inrange_count(h, l)
        sq = squeeze(h, l, c)
        others = {
            "vhf:VHF_28": vhf(c),
            "adx:ADX_14": adx(h, l, c).iloc[:, 0],
            "chop:CHOP_14_1_100": chop(h, l, c),
            "range_compress_run:RCR_100": range_compress_run(h, l),
            "squeeze:SQZ_ON": sq["SQZ_ON"],
        }
        for label, other in others.items():
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
    print("A bad high or low at bar 700 of `walk`: the bar's own reading,")
    print("bars before it moved, and bars after it moved.")
    print()
    h, l, c = _walk()
    base = inrange_count(h, l)
    off = _mutant(*GUARD_OFF)
    print(f"{'leg':>5} {'value':>6} {'own NaN':>8} {'before':>7} "
          f"{'after':>6} {'unguarded after':>16}")
    for leg in ("high", "low"):
        for label, value in (("nan", np.nan), ("+inf", np.inf),
                             ("-inf", -np.inf)):
            parts = {"high": h.copy(), "low": l.copy()}
            parts[leg].iloc[PLANT] = value
            out = inrange_count(parts["high"], parts["low"])
            raw = off(parts["high"], parts["low"])
            b, o, r = base.to_numpy(), out.to_numpy(), raw.to_numpy()

            def moved(x, y):  # NaN == NaN counts as unmoved
                return int((~((x == y) | (np.isnan(x) & np.isnan(y)))).sum())
            before = moved(b[:PLANT], o[:PLANT])
            after = moved(b[PLANT + 1:], o[PLANT + 1:])
            ua = moved(b[PLANT + 1:], r[PLANT + 1:])
            print(f"{leg:>5} {label:>6} {str(np.isnan(o[PLANT])):>8} "
                  f"{before:>7} {after:>6} {ua:>16}")


def section_L():
    _head("L Short and degenerate frames")
    h, l, _ = _walk(n=40)
    for n in (LENGTH, LENGTH + 1, LENGTH + 5):
        out = inrange_count(h.iloc[:n], l.iloc[:n])
        print(f"  bars {n:>3}: "
              f"{'None' if out is None else str(int(out.notna().sum())) + ' fired'}")
    idx = date_range("2020-01-01", periods=60, freq="h")
    for label, value in (("all NaN", np.nan), ("all 0.0", 0.0),
                         ("all -5.0", -5.0), ("all 100.0", 100.0)):
        s = Series(np.full(60, value), index=idx)
        with np.errstate(all="raise"):
            out = inrange_count(s.copy(), s.copy())
        v = out.dropna()
        print(f"  {label:>10}: {v.size} fired, values {sorted(set(v))}")


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
        if line.startswith("| `inrange_count`"):
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
    for line in inrange_count.__doc__.splitlines()[1:]:
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
        h, l, _ = _walk(n=n)
        times = [min(timeit.repeat(lambda: inrange_count(h, l), number=1,
                                   repeat=3)) * 1e3 for _ in range(2)]
        tracemalloc.start()
        inrange_count(h, l)
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
