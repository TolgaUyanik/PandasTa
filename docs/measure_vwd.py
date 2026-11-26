# -*- coding: utf-8 -*-
"""VWD (PandasTa issue #202): the numbers in `docs/VwdMeasured.md`, except
the ones that receipt names above its §A1 (pytest's own counts, the
before/after counts read off `README.md` and `docs/MLCompanionContract.md`,
and issue #202's screen figures).

    python docs/measure_vwd.py            # every section, in order
    python docs/measure_vwd.py A1 D1      # named sections only

One section per gate limb, printed and never derived: no figure may enter
the receipt, the module docstring or `tests/test_vwd.py` except from a
section here or from one of the receipt's named exceptions.

    madif[T] = (SMA(close, 14)[T] - EMA(close, 7)[T]) / EMA(close, 7)[T] * 100
    vp[T]    = (buy - sell) / (buy + sell), buy = V*(C-L)/(H-L), sell = V*(H-C)/(H-L)
    vs[T]    = SMA(|vp|, 14)[T]
    VWD[T]   = madif[T] * vp[T] * vs[T] * 10

⚠ The millisecond figures of §Z are this machine's and this run's.
"""
import importlib.util
import math
import platform
import sys
import timeit
import warnings
from pathlib import Path

#: Import THIS checkout's pandas_ta, not whichever one the environment
#: installed: the receipt describes this tree.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd
from pandas import DataFrame, Series, date_range

import pandas_ta  # noqa: E402
from pandas_ta.momentum.vwd import FAST, GAIN, MIN_BARS, PERCENT, SLOW, vwd

N = 1500
LEVEL = 100.0
#: The first bar that can fire on a clean frame, and so the warm-up.
WARMUP = MIN_BARS - 1
FIRED = N - WARMUP
#: The blind causality sweep's perturbation points.
OFFSETS = list(range(N - 36, N))


# ------------------------------------------------------------------ frames
# The same builders and seeds as `tests/test_vwd.py`, so a number in this
# file and a number in that one are the same measurement. The close sits
# strictly inside (low, high), so H > L on every bar of the six varying
# frames; `doji` plants H == L bars on purpose.


def _ohlcv(close, seed):
    rng = np.random.default_rng(seed + 9_999)
    idx = date_range("2020-01-01", periods=close.size, freq="h")
    return (Series(close * (1.0 + 0.004 * rng.random(close.size)), index=idx),
            Series(close * (1.0 - 0.004 * rng.random(close.size)), index=idx),
            Series(close, index=idx),
            Series(rng.integers(1_000, 100_000, close.size).astype(float),
                   index=idx))


def _walk(seed=7, n=N, level=LEVEL, sigma=0.01):
    rng = np.random.default_rng(seed)
    return _ohlcv(level * np.exp(np.cumsum(rng.normal(0.0, sigma, n))), seed)


def _trend(seed=11, n=N, level=LEVEL):
    rng = np.random.default_rng(seed)
    return _ohlcv(level * np.exp(np.cumsum(rng.normal(0.003, 0.008, n))), seed)


def _range_bound(seed=13, n=N, level=LEVEL):
    rng = np.random.default_rng(seed)
    x = np.zeros(n)
    for i in range(1, n):
        x[i] = 0.9 * x[i - 1] + rng.normal(0.0, 0.02)
    return _ohlcv(level * np.exp(x), seed)


def _grid(seed=17, n=N, level=LEVEL, tick=0.01):
    """Tick-rounded prices, the shape real BIST bars have."""
    h, l, c, v = _walk(seed, n, level)
    return (np.round(h / tick) * tick, np.round(l / tick) * tick,
            np.round(c / tick) * tick, v)


def _heavy(seed=19, n=N, level=LEVEL):
    rng = np.random.default_rng(seed)
    return _ohlcv(level * np.exp(np.cumsum(rng.standard_t(2.0, n) * 0.006)),
                  seed)


def _jump(seed=23, n=N, level=LEVEL):
    h, l, c, v = _walk(seed, n, level)
    f = Series(np.where(np.arange(n) >= 700, 1.5, 1.0), index=c.index)
    return h * f, l * f, c * f, v


def _doji(seed=29, n=N, level=LEVEL, every=100):
    """A `walk` with H == L == C on every `every`-th bar from bar 50: the
    source's vp is 0/0 there."""
    h, l, c, v = _walk(seed, n, level)
    h, l = h.copy(), l.copy()
    at = np.arange(50, n, every)
    h.iloc[at] = c.iloc[at]
    l.iloc[at] = c.iloc[at]
    return h, l, c, v


def _flat(n=N, level=LEVEL):
    idx = date_range("2020-01-01", periods=n, freq="h")
    one = Series(np.full(n, level), index=idx)
    return one * 1.004, one * 0.996, one.copy(), Series(np.full(n, 1e4), index=idx)


FRAMES = {
    "walk": _walk, "trend": _trend, "range-bound": _range_bound,
    "grid": _grid, "heavy-tailed": _heavy, "jump": _jump, "doji": _doji,
    "flat": _flat,
}
NAMES = list(FRAMES)
VARYING = ["walk", "trend", "range-bound", "grid", "heavy-tailed", "jump"]
SWEPT = ["walk", "trend", "heavy-tailed"]


def _frame(name):
    return FRAMES[name]()


def _col(name, fn=None):
    h, l, c, _ = _frame(name)
    return (fn or vwd)(h, l, c)


# ---------------------------------------------------------------- oracles


def _oracle(high, low, close, volume, ema_seed="sma"):
    """The poster's formula bar by bar, sharing no code with the module:
    its own `math.fsum` SMAs, its own EMA recursion over Python floats, and
    vp in the LITERAL volume form, buy and sell each carrying V."""
    H = [float(x) for x in high.to_numpy(dtype=float)]
    L = [float(x) for x in low.to_numpy(dtype=float)]
    C = [float(x) for x in close.to_numpy(dtype=float)]
    V = [float(x) for x in volume.to_numpy(dtype=float)]
    n = len(C)
    nan = float("nan")
    alpha = 2.0 / (FAST + 1)
    e = [nan] * n
    if ema_seed == "sma":
        e[FAST - 1] = math.fsum(C[:FAST]) / FAST
        start = FAST
    else:                                  # bare recursion from bar 0
        e[0] = C[0]
        start = 1
    for i in range(start, n):
        e[i] = alpha * C[i] + (1.0 - alpha) * e[i - 1]
    vp = [nan] * n
    for i in range(n):
        if H[i] - L[i] > 0.0:
            buy = V[i] * (C[i] - L[i]) / (H[i] - L[i])
            sell = V[i] * (H[i] - C[i]) / (H[i] - L[i])
            if buy + sell != 0.0:
                vp[i] = (buy - sell) / (buy + sell)
    out = [nan] * n
    for i in range(SLOW - 1, n):
        win = [abs(x) for x in vp[i - SLOW + 1:i + 1]]
        if any(math.isnan(x) for x in win):
            continue
        s = math.fsum(C[i - SLOW + 1:i + 1]) / SLOW
        madif = (s - e[i]) / e[i] * PERCENT
        out[i] = madif * vp[i] * (math.fsum(win) / SLOW) * GAIN
    return Series(out, index=close.index)


def _bit_equal(a, b):
    if not bool((a.isna() == b.isna()).all()):
        return False
    m = a.notna() & b.notna()
    return bool((a[m].to_numpy() == b[m].to_numpy()).all())


def _abs(a, b):
    m = a.notna() & b.notna()
    return float((a[m] - b[m]).abs().max()) if int(m.sum()) else float("nan")


def _rel(a, b):
    m = a.notna() & b.notna() & (b.abs() > 0.0)
    return float(((a[m] - b[m]).abs() / b[m].abs()).max()) if int(m.sum()) else 0.0


def _spearman(a, b):
    m = a.notna() & b.notna()
    return float(a[m].corr(b[m], method="spearman"))


def _differing_bars(a, b):
    m = a.notna() & b.notna()
    return int((a[m].to_numpy() != b[m].to_numpy()).sum())


# ---------------------------------------------------------------- mutants

SOURCE = ROOT / "pandas_ta" / "momentum" / "vwd.py"

CAUSALITY_MUTANTS = [
    ("close-lead", "    c = close.astype(float)",
     "    c = close.astype(float).shift(-1)"),
    ("ema-lead", "    e = ema(c, length=FAST)",
     "    e = ema(c, length=FAST).shift(-1)"),
    ("sma-lead", "    madif = (sma(c, length=SLOW) - e) / e * PERCENT",
     "    madif = (sma(c, length=SLOW).shift(-1) - e) / e * PERCENT"),
    ("vp-lead", "    vp = ((c - l) - (h - c)) / rng.where(rng > 0.0)",
     "    vp = (((c - l) - (h - c)) / rng.where(rng > 0.0)).shift(-1)"),
    ("vs-lead", "    vs = sma(vp.abs(), length=SLOW)",
     "    vs = sma(vp.abs().shift(-1), length=SLOW)"),
    ("output-early", "    vwd = vwd.where(np.isfinite(vwd))",
     "    vwd = vwd.where(np.isfinite(vwd)).shift(-1)"),
]

#: Wrong without reading any later bar: the sweep is blind, the oracle is not.
BLIND_SPOT_MUTANTS = [
    ("vs-lagged", "    vs = sma(vp.abs(), length=SLOW)",
     "    vs = sma(vp.abs(), length=SLOW).shift(1)"),
    ("ema-slow", "    e = ema(c, length=FAST)",
     "    e = ema(c, length=SLOW)"),
    ("over-sma", "    madif = (sma(c, length=SLOW) - e) / e * PERCENT",
     "    madif = (sma(c, length=SLOW) - e) / sma(c, length=SLOW) * PERCENT"),
]


def _mutant(old, new):
    src = SOURCE.read_text(encoding="utf-8")
    assert src.count(old) == 1, f"{old!r} occurs {src.count(old)} times"
    ns = {}
    exec(compile(src.replace(old, new), "<mutant>", "exec"), ns)
    return ns["vwd"]


#: (high, low, close) factors for the suffix. ⚠ Deliberately UNEQUAL: vp is
#: invariant under a common rescale (and a common shift) of one bar's H, L
#: and C, so a uniform suffix rescale would catch a `vp`- or `vs`-lead
#: mutant only through rounding (§B1U prints how little it moves them).
FACTORS = (1.02, 1.01, 1.03)


def _perturbed(frame, j):
    h, l, c, _ = frame
    at = np.arange(c.size) >= j
    fh, fl, fc = (Series(np.where(at, f, 1.0), index=c.index) for f in FACTORS)
    return h * fh, l * fl, c * fc


def _caught_at(fn, frame, j):
    """Did perturbing every high/low/close bar >= j move any bar < j?"""
    h, l, c, _ = frame
    a = fn(h, l, c).iloc[:j]
    b = fn(*_perturbed(frame, j)).iloc[:j]
    if not bool((a.isna() == b.isna()).all()):
        return True
    m = a.notna() & b.notna()
    return not bool((a[m].to_numpy() == b[m].to_numpy()).all())


def _sweep(fn, frame):
    return sum(_caught_at(fn, frame, j) for j in OFFSETS)


def _first_catch(fn, frame):
    h, l, c, _ = frame
    j = OFFSETS[0]
    return _abs(fn(h, l, c).iloc[:j], fn(*_perturbed(frame, j)).iloc[:j])


def _rule(title):
    print()
    print("=" * 78)
    print(title)
    print("=" * 78)


# ---------------------------------------------------------------- sections


def section_env():
    _rule("ENV")
    print(f"python {platform.python_version()}  pandas {pd.__version__}  "
          f"numpy {np.__version__}")
    print(f"talib installed: {importlib.util.find_spec('talib') is not None}")
    print(f"N={N} WARMUP={WARMUP} FIRED={FIRED} column={vwd(*_frame('walk')[:3]).name}")


def section_A1():
    _rule("A1 -- Gate A against a bar-by-bar oracle, vp in the literal V form")
    for name in VARYING:
        h, l, c, v = _frame(name)
        a, o = vwd(h, l, c), _oracle(h, l, c, v)
        print(f"{name:<13} fired {int(a.notna().sum()):>5}/{N}  masks equal "
              f"{bool((a.isna() == o.isna()).all())}  abs {_abs(a, o):.3e}  "
              f"rel {_rel(a, o):.3e}  rho {_spearman(a, o):.4f}")


def section_A2():
    _rule("A2 -- the EMA leg: this fork's `ema` against talib.EMA")
    from pandas_ta.overlap.ema import ema
    if importlib.util.find_spec("talib") is None:
        print("talib absent -- skipped")
        return
    import talib
    for name in VARYING:
        c = _frame(name)[2]
        a = ema(c, length=FAST)
        t = Series(talib.EMA(c.to_numpy(), FAST), index=c.index)
        first = int(np.flatnonzero(a.notna().to_numpy())[0])
        print(f"{name:<13} masks equal {bool((a.isna() == t.isna()).all())}  "
              f"abs {_abs(a, t):.3e}  first fire {first}")


def section_A3():
    _rule("A3 -- readings NOT taken, priced: bare ewm(span=7) from bar 0")
    for name in VARYING:
        h, l, c, v = _frame(name)
        a = vwd(h, l, c)
        b = _oracle(h, l, c, v, ema_seed="bare")
        m = a.notna() & b.notna()
        diff = np.flatnonzero(np.abs(a[m].to_numpy() - b[m].to_numpy()) > 1e-9)
        last = int(np.flatnonzero(m.to_numpy())[diff[-1]]) if diff.size else -1
        print(f"{name:<13} bars differing > 1e-9: {diff.size:>5}/{int(m.sum())}  "
              f"max abs {_abs(a, b):.3e}  last differing bar {last}  "
              f"rho {_spearman(a, b):.6f}")


def section_A4():
    _rule("A4 -- V == 0 or NaN on one bar: the literal form is blank, the module is not")
    for bad in (0.0, float("nan")):
        h, l, c, v = _frame("walk")
        v = v.copy()
        v.iloc[700] = bad
        a, o = vwd(h, l, c), _oracle(h, l, c, v)
        gone = np.flatnonzero((a.notna() & o.isna()).to_numpy())
        print(f"V={bad}: module fired {int(a.notna().sum())}  literal fired "
              f"{int(o.notna().sum())}  literal-only blanks {int(gone[0])}..{int(gone[-1])}")


def section_B1():
    _rule("B1 -- Gate B: the blind future sweep and six look-ahead mutants")
    for name in VARYING:
        print(f"{name:<13} module caught {_sweep(vwd, _frame(name))}/{len(OFFSETS)}")
    for label, old, new in CAUSALITY_MUTANTS:
        fn = _mutant(old, new)
        caught = [_sweep(fn, _frame(n)) for n in SWEPT]
        loud = min(_first_catch(fn, _frame(n)) for n in SWEPT)
        print(f"{label:<13} caught {caught} of {len(OFFSETS)}  "
              f"smallest first-catch move {loud:.3e}")


def section_B1U():
    _rule("B1U -- why FACTORS are unequal: a UNIFORM x1.03 suffix at OFFSETS[0] "
          "against the vp-lead and vs-lead mutants")
    j = OFFSETS[0]
    for label, old, new in CAUSALITY_MUTANTS[3:5]:
        fn = _mutant(old, new)
        moves = []
        for name in SWEPT:
            h, l, c, _ = _frame(name)
            f = Series(np.where(np.arange(c.size) >= j, 1.03, 1.0), index=c.index)
            moves.append(_abs(fn(h, l, c).iloc[:j], fn(h * f, l * f, c * f).iloc[:j]))
        print(f"{label:<8} prefix move per frame {SWEPT}: "
              + "  ".join(f"{m:.3e}" for m in moves))


def section_B2():
    _rule("B2 -- the sweep's blind spot, and the oracle covering it")
    fr = _frame("walk")
    o = _oracle(*fr)
    for label, old, new in BLIND_SPOT_MUTANTS:
        fn = _mutant(old, new)
        print(f"{label:<13} sweep {_sweep(fn, fr)}/{len(OFFSETS)}  "
              f"miss vs oracle {_abs(fn(*fr[:3]), o):.3e}")


def section_C1():
    _rule("C1 -- Gate C reachability on the six varying frames (SYNTHETIC)")
    pooled = []
    for name in VARYING:
        col = _col(name)
        d = col.dropna()
        pooled.append(d)
        first = int(np.flatnonzero(col.notna().to_numpy())[0])
        print(f"{name:<13} fired {d.size}/{N}  first {first}  distinct "
              f"{d.nunique()}  zero {int((d == 0).sum())}  "
              f"min {d.min():.4e}  max {d.max():.4e}")
    p = pd.concat(pooled)
    print(f"pooled {p.size}: min {p.min():.4e} max {p.max():.4e} negative "
          f"{int((p < 0).sum())} zero {int((p == 0).sum())} "
          f"|v|<=1 {int((p.abs() <= 1).sum())}")


def section_C2():
    _rule("C2 -- H == L bars: each blanks SLOW bars; a flat frame")
    col = _col("doji")
    h, l, c, _ = _frame("doji")
    print(f"doji: {int((h == l).sum())} H==L bars, fired {int(col.notna().sum())}/{N}, "
          f"blank after warm-up {int(col.iloc[WARMUP:].isna().sum())}")
    col = _col("flat")
    print(f"flat (H>L, constant close): fired {int(col.notna().sum())}  "
          f"max |v| {float(col.abs().max()):.3e}")


def section_D1():
    _rule("D1 -- Gate D x8 / x64 bit-identical")
    for name in VARYING + ["doji"]:
        h, l, c, _ = _frame(name)
        base = vwd(h, l, c)
        print(f"{name:<13} " + "  ".join(
            f"x{f:g} {_bit_equal(base, vwd(h * f, l * f, c * f))}"
            for f in (8.0, 64.0)))


def section_D2():
    _rule("D2 -- inexact factors: masks, absolute and relative")
    worst_abs = worst_rel = 0.0
    masks = True
    for name in VARYING:
        h, l, c, _ = _frame(name)
        base = vwd(h, l, c)
        for f in (10.0, 3.7, 0.1, 1.0000001):
            other = vwd(h * f, l * f, c * f)
            masks &= bool((base.isna() == other.isna()).all())
            worst_abs = max(worst_abs, _abs(base, other))
            big = base.abs() >= 1e-3
            worst_rel = max(worst_rel, _rel(other[big], base[big]))
    print(f"24 cells: masks all equal {masks}  worst abs {worst_abs:.3e}  "
          f"worst rel (|v| >= 1e-3) {worst_rel:.3e}")


def section_D3():
    _rule("D3 -- non-vacuity: a +10 level shift DOES move the column")
    for name in VARYING:
        h, l, c, _ = _frame(name)
        base, other = vwd(h, l, c), vwd(h + 10, l + 10, c + 10)
        print(f"{name:<13} bars moved {_differing_bars(base, other)}/{FIRED}  "
              f"max {_abs(base, other):.3e}")


def section_D4():
    _rule("D4 -- 0 < fires < n")
    for name in VARYING:
        print(f"{name:<13} fires {int(_col(name).notna().sum())} of {N}")


def section_L():
    _rule("L -- in-fork overlap: every Category column at defaults, per-frame "
          "median |rho| (a DISCLOSURE, not Gate E)")
    warnings.filterwarnings("ignore")
    names = [n for v in pandas_ta.Category.values() for n in v]
    res = {}
    for name in VARYING:
        h, l, c, v = _frame(name)
        df = DataFrame({"open": c.shift(1).fillna(c.iloc[0]).to_numpy(),
                        "high": h.to_numpy(), "low": l.to_numpy(),
                        "close": c.to_numpy(), "volume": v.to_numpy()},
                       index=c.index)
        df["high"] = df[["open", "high"]].max(axis=1)
        df["low"] = df[["open", "low"]].min(axis=1)
        y = df.ta.vwd()
        for ind in names:
            if ind == "vwd":
                continue
            try:
                out = getattr(df.ta, ind)()
            except Exception:
                continue
            if isinstance(out, tuple):
                out = out[0]
            if isinstance(out, Series):
                out = out.to_frame()
            if not isinstance(out, DataFrame):
                continue
            for col in out.columns:
                x = pd.to_numeric(out[col], errors="coerce")
                m = x.notna() & y.notna()
                if int(m.sum()) < 200 or x[m].nunique() < 3:
                    continue
                res.setdefault(f"{ind}:{col}", []).append(
                    abs(float(x[m].corr(y[m], method="spearman"))))
    med = {k: float(np.median(v)) for k, v in res.items() if len(v) == len(VARYING)}
    print(f"{len(med)} columns scored on all {len(VARYING)} frames")
    for k, v in sorted(med.items(), key=lambda kv: -kv[1])[:5]:
        print(f"  {v:.4f}  {k}")


def section_Z():
    _rule("Z -- cost (THIS machine, THIS run; nothing else cites these)")
    h, l, c, v = _frame("walk")
    for label, fn in (("vwd", lambda: vwd(h, l, c)),
                      ("the oracle", lambda: _oracle(h, l, c, v))):
        best = min(timeit.repeat(fn, number=10, repeat=3)) / 10 * 1e3
        print(f"{label:<14}{best:>9.3f} ms per call on {N} bars")


SECTIONS = {
    "ENV": section_env, "A1": section_A1, "A2": section_A2, "A3": section_A3,
    "A4": section_A4, "B1": section_B1, "B1U": section_B1U, "B2": section_B2, "C1": section_C1,
    "C2": section_C2, "D1": section_D1, "D2": section_D2, "D3": section_D3,
    "D4": section_D4, "L": section_L, "Z": section_Z,
}


if __name__ == "__main__":
    want = [a.upper() for a in sys.argv[1:]] or list(SECTIONS)
    for key in want:
        if key not in SECTIONS:
            raise SystemExit(f"unknown section {key!r}; "
                             f"pick from {list(SECTIONS)}")
        SECTIONS[key]()
