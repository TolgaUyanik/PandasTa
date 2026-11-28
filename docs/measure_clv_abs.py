# -*- coding: utf-8 -*-
"""Reproduce the numbers in docs/ClvAbsMeasured.md.

    python docs/measure_clv_abs.py

Run from the repo root. Uses tests/test_clv_abs.py's synthetic tick-rounded
OHLC generator and its independent loop reference; no real-data cache is
available in this worktree, so Gate C here is synthetic-only.
"""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.getcwd())
import tests.test_clv_abs as T  # noqa: E402

clv_abs = T.clv_abs


def gate_a():
    print("== Gate A: hand-derived fixtures (length 4) ==")
    cases = {
        "close_at_extreme": T._hlc([(102.0, 98.0, 102.0), (101.0, 99.0, 99.0)] * 2),
        "mid_range": T._hlc([(102.0, 98.0, 100.0)] * 4),
        "mixed": T._hlc([(102.0, 98.0, 101.0), (102.0, 98.0, 100.0),
                         (102.0, 98.0, 98.0), (102.0, 98.0, 99.0)]),
    }
    for name, df in cases.items():
        out = clv_abs(df.high, df.low, df.close, length=4)
        print(f"  {name}: warm-up NaN {int(out.iloc[:3].isna().sum())}, value at bar 3 = {out.iloc[3]}")
    rows = [(102.0, 98.0, 101.0), (102.0, 98.0, 100.0), (102.0, 98.0, 98.0),
            (102.0, 98.0, 99.0), (102.0, 98.0, 102.0), (100.0, 100.0, 100.0),
            (102.0, 98.0, 98.0)]
    df = T._hlc(rows)
    out = clv_abs(df.high, df.low, df.close, length=4)
    print(f"  zero_range at bar 5 (|vp| 0.5, 0, 1, 0.5, 1, flat, 1): bars 3..6 = {list(out.iloc[3:])} "
          "(skip na -> bar 6 0.875; propagate na -> NaN; flat as 0 -> 0.625)")

    print("== Gate A: module vs independent loop reference, 2,000-bar frames ==")
    for seed in (1, 2, 3):
        for length in (5, 14):
            df = T._frame(n=2000, seed=seed)
            out = clv_abs(df.high, df.low, df.close, length=length)
            ref = T._reference(df.high, df.low, df.close, length=length)
            m = out.notna()
            print(f"  seed {seed} length {length}: NaN masks equal {(out.isna() == ref.isna()).all()}, "
                  f"settled {int(m.sum())}, max abs diff {np.max(np.abs(out[m] - ref[m])):.3g}, "
                  f"zero-range bars {int((df.high == df.low).sum())}")


def causality_sweep():
    print("== Gate B: future-perturbation sweep, 600-bar frame, J in range(10, 596, 2) ==")
    mod = T._load_mutant()
    a, b = T._frame(600, seed=1, flat=0.0), T._frame(600, seed=2, flat=0.0)
    print(f"  no flat bars: swept {len(T.JS)} J values: real module leaked at {T._sweep(clv_abs, a, b, T.JS)}, "
          f"mutant leaked at {T._sweep(mod.clv_abs, a, b, T.JS)}")
    a, b = T._frame(600, seed=1), T._frame(600, seed=2)
    print(f"  2% flat bars: swept {len(T.JS)} J values: real module leaked at {T._sweep(clv_abs, a, b, T.JS)}")


def _overlap_frame(seed, n=1500):
    """The pre-port equivalence-check generator: Student-t(4) returns with a
    volatility random walk, ticks 0.01/0.05/0.1, about 2% flat bars."""
    r = np.random.default_rng(seed)
    tick = [0.01, 0.05, 0.1][seed % 3]
    vol = 0.01 * np.exp(np.cumsum(r.normal(0, 0.05, n)))
    c = 50 * np.exp(np.cumsum(r.standard_t(4, n) * vol * 0.5))
    o = np.r_[c[0], c[:-1]] * (1 + r.normal(0, 0.002, n))
    h = np.maximum(o, c) * (1 + np.abs(r.normal(0, vol * 0.6)))
    l = np.minimum(o, c) * (1 - np.abs(r.normal(0, vol * 0.6)))
    rd = lambda x: np.round(x / tick) * tick
    o, h, l, c = rd(o), rd(h), rd(l), rd(c)
    flat = r.random(n) < 0.02
    h[flat] = l[flat] = o[flat] = c[flat]
    h = np.maximum.reduce([h, o, c]); l = np.minimum.reduce([l, o, c])
    v = np.round(r.lognormal(12, 0.6, n))
    return pd.DataFrame(dict(open=o, high=h, low=l, close=c, volume=v))


def fork_overlap():
    """Not Gate E: per-frame Spearman |rho| of CLVABS_14 against every column
    of every other `Category` indicator at defaults, 14 synthetic frames,
    first 100 bars dropped. Slow (a few minutes)."""
    import warnings
    import pandas_ta as ta
    print("== Fork overlap (not Gate E): 14 synthetic 1,500-bar frames, every Category output at defaults ==")
    names = [n for cat in ta.Category.values() for n in cat if n != "clv_abs"]
    res, ties, rows = {}, 0, 0
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for s in range(14):
            df = _overlap_frame(s)
            ties += int((df.high == df.low).sum())
            y = clv_abs(df.high, df.low, df.close)
            rows += int(y.iloc[100:].notna().sum())
            for n in names:
                try:
                    out = getattr(df.ta, n)()
                except Exception:
                    continue
                if isinstance(out, pd.Series):
                    out = out.to_frame()
                if not isinstance(out, pd.DataFrame):
                    continue
                for col in out.columns:
                    x = pd.to_numeric(out[col], errors="coerce")
                    if len(x) != len(y):
                        continue
                    m = x.notna() & y.notna() & np.isfinite(x)
                    m.iloc[:100] = False
                    if m.sum() < 200 or x[m].nunique() < 3:
                        continue
                    res.setdefault(f"{n}:{col}", []).append(x[m].rank().corr(y[m].rank()))
    tab = sorted(((abs(np.median(v)), np.median(v), len(v), k)
                  for k, v in res.items() if len(v) >= 12), reverse=True)
    print(f"  {ties} zero-range bars, {rows} candidate rows after bar 100; {len(tab)} comparator columns")
    for t in tab[:5]:
        print("  |median| %.4f (median %.4f, %d frames) %s" % t)


def reachability():
    print("== Gate C: reachability on a 2,000-bar synthetic frame (seed 4) ==")
    df = T._frame(n=2000, seed=4)
    out = clv_abs(df.high, df.low, df.close)
    s = out.dropna()
    print(f"  settled {len(s)} of 2000 (zero-range bars {int((df.high == df.low).sum())}); "
          f"non-zero {int((s != 0).sum())}; distinct values {s.nunique()}; "
          f"min {s.min():.4f} median {s.median():.4f} max {s.max():.4f}")
    print("== Gate C: across 10 independent 600-bar seeds (100-109) ==")
    for seed in range(100, 110):
        df = T._frame(n=600, seed=seed)
        s = clv_abs(df.high, df.low, df.close).dropna()
        print(f"  seed {seed}: settled {len(s)} of 600, distinct {s.nunique()}, "
              f"min {s.min():.4f} max {s.max():.4f}")


def scale_tolerance():
    print("== Gate D: price-scale invariance, 2,000-bar frame (seed 4) ==")
    df = T._frame(n=2000, seed=4)
    base = clv_abs(df.high, df.low, df.close)
    m = base.notna()
    for k in (8.0, 64.0, 10.0, 3.7):
        scaled = clv_abs(df.high * k, df.low * k, df.close * k)
        print(f"  x{k}: NaN masks equal {(base.isna() == scaled.isna()).all()}; "
              f"mismatches on {int(m.sum())} co-finite cells {int((base[m] != scaled[m]).sum())}; "
              f"max abs diff {np.max(np.abs(base[m] - scaled[m])):.3g}")


def module_sha1():
    import importlib.util
    spec = importlib.util.spec_from_file_location("gate_e_ledger", "docs/gate_e_ledger.py")
    gl = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gl)
    path = gl.module_path("pandas_ta.candles.clv_abs")
    print(f"== module_sha1 (LF-normalised, for docs/gate_e_ledger.csv) == {gl.lf_sha1(path)}")


if __name__ == "__main__":
    gate_a()
    causality_sweep()
    reachability()
    scale_tolerance()
    fork_overlap()
    module_sha1()
    print("python", sys.version.split()[0], "pandas", pd.__version__, "numpy", np.__version__)
