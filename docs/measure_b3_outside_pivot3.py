# -*- coding: utf-8 -*-
"""Reproduce the numbers in docs/B3OutsidePivot3Measured.md.

    python docs/measure_b3_outside_pivot3.py

Run from the repo root. Uses tests/test_b3_outside_pivot3.py's synthetic OHLC
generators; no real-data cache is available in this worktree, so Gate C here
is synthetic-only. Gate E is owed (run by the owner on the way to `main`).
"""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.getcwd())
import tests.test_b3_outside_pivot3 as T  # noqa: E402

b3_outside_pivot3 = T.b3_outside_pivot3


def gate_a():
    print("== Gate A: hand-derived fixtures (value at bar 2) ==")
    cases = {
        "fires": [(101.0, 99.0), (102.0, 98.0), (101.5, 98.5)],
        "swing_high_only": [(101.0, 99.0), (102.0, 98.0), (101.5, 97.0)],
        "swing_low_only": [(101.0, 99.0), (102.0, 98.0), (103.0, 98.5)],
        "left_high_tie": [(102.0, 99.0), (102.0, 98.0), (101.5, 98.5)],
        "left_low_tie": [(101.0, 98.0), (102.0, 98.0), (101.5, 98.5)],
        "right_high_tie": [(101.0, 99.0), (102.0, 98.0), (102.0, 98.5)],
        "right_low_tie": [(101.0, 99.0), (102.0, 98.0), (101.5, 98.0)],
    }
    for name, rows in cases.items():
        df = T._hl(rows)
        out = b3_outside_pivot3(df.high, df.low)
        print(f"  {name}: warm-up NaN bars {int(out.iloc[:2].isna().sum())}, "
              f"value at bar 2 = {out.iloc[2]}")

    print("== Gate A: independent bar loop, 12 tick-rounded frames x 1,500 bars (tick 1.0) ==")
    for seed in range(12):
        h, l = T._ticky(1500, seed)
        got = b3_outside_pivot3(h, l).to_numpy()
        ref = T._reference(h, l)
        mism = int((~((got == ref) | (np.isnan(got) & np.isnan(ref)))).sum())
        ties = int((h == h.shift(1)).sum() + (l == l.shift(1)).sum())
        print(f"  seed {seed}: ties {ties}, fires {int(np.nansum(got))}, mismatches {mism}")


def reachability():
    print("== Gate C: reachability on a 2,000-bar synthetic frame (seed 4) ==")
    df = T._frame(n=2000, seed=4)
    out = b3_outside_pivot3(df.high, df.low)
    fired = out.dropna()
    fires = int((fired == 1.0).sum())
    print(f"  settled {len(fired)} of 2000 (warm-up 2); pivots {fires}, "
          f"zero {len(fired) - fires}")

    print("== Gate C: reachability across 10 independent 600-bar seeds ==")
    for seed in range(10):
        df = T._frame(n=600, seed=seed + 100)
        out = b3_outside_pivot3(df.high, df.low)
        fired = out.dropna()
        print(f"  seed {seed + 100}: fires {int((fired == 1.0).sum())} of {len(fired)}")


def scale_tolerance():
    print("== Gate D: price-scale invariance (x8/x64/x10/x3.7), 2,000-bar seed-4 frame ==")
    df = T._frame(n=2000, seed=4)
    base = b3_outside_pivot3(df.high, df.low)
    for k in (8.0, 64.0, 10.0, 3.7):
        scaled = b3_outside_pivot3(df.high * k, df.low * k)
        m = base.notna()
        mismatches = int((base[m] != scaled[m]).sum())
        print(f"  x{k}: NaN masks equal {(base.isna() == scaled.isna()).all()}; "
              f"mismatches on {int(m.sum())} co-finite cells: {mismatches}")


def causality_sweep():
    print("== Gate B: future-perturbation sweep, 600-bar frame, J in range(10, 596, 2) ==")
    mod = T._load_mutant()
    a = T._frame(600, seed=1)
    b = T._frame(600, seed=2)
    mut_a_full = mod.b3_outside_pivot3(a.high, a.low)
    real_a_full = b3_outside_pivot3(a.high, a.low)
    js = list(range(10, 596, 2))
    real_leaks, mutant_leaks = 0, 0
    for j in js:
        spliced = a.copy()
        spliced.iloc[j:] = b.iloc[j:].to_numpy()
        real_b = b3_outside_pivot3(spliced.high, spliced.low)
        if not real_a_full.iloc[:j].equals(real_b.iloc[:j]):
            real_leaks += 1
        mut_b = mod.b3_outside_pivot3(spliced.high, spliced.low)
        av, bv = mut_a_full.iloc[j - 1], mut_b.iloc[j - 1]
        both_nan = pd.isna(av) and pd.isna(bv)
        if not (av == bv or both_nan):
            mutant_leaks += 1
    print(f"  swept {len(js)} J values: real module leaked at {real_leaks}, "
          f"mutant leaked at {mutant_leaks}")


def _ohlc(seed, n=2000):
    """Tick-rounded OHLC walk (ticks 0.01/0.05/0.1, Student-t(4) returns,
    volatility regimes every 400 bars) -- the pre-port equivalence frames."""
    rng = np.random.default_rng(seed)
    tick = [0.01, 0.05, 0.1][seed % 3]
    c = 100 * np.exp(np.cumsum(rng.standard_t(4, n) * 0.01 * (1 + (np.arange(n) // 400) % 2)))
    o = np.r_[c[0], c[:-1]] * (1 + rng.normal(0, .002, n))
    h = np.maximum(o, c) * (1 + np.abs(rng.normal(0, .005, n)))
    l = np.minimum(o, c) * (1 - np.abs(rng.normal(0, .005, n)))
    r = lambda x: pd.Series(np.round(x / tick) * tick)
    return r(o), r(h), r(l), r(c)


def decomposition():
    print("== Decision 4: decomposition and overlap, 14 tick-rounded OHLC frames x 2,000 bars ==")
    import pandas_ta as ta
    from scipy.stats import spearmanr
    rho = {"CDL_INSIDE": [], "RD_OUTSIDE_BAR": []}
    rows, mism_total, ties_total = 0, 0, 0
    for seed in range(14):
        o, h, l, c = _ohlc(seed)
        cand = b3_outside_pivot3(h, l)
        alt = ((ta.rd_outside_bar(h, l).shift(1) == 1)
               & (ta.cdl_inside(o, h, l, c, asbool=True) == 1)).astype(float)
        mism = int((alt != cand).iloc[2:].sum())
        mism_total += mism
        ties_total += int((h == h.shift(1)).sum() + (l == l.shift(1)).sum())
        cols = {"CDL_INSIDE": ta.cdl_inside(o, h, l, c, asbool=True).astype(float),
                "RD_OUTSIDE_BAR": ta.rd_outside_bar(h, l)}
        line = []
        for k, s in cols.items():
            d = pd.concat([cand, s], axis=1).iloc[100:].dropna()
            r = spearmanr(d.iloc[:, 0], d.iloc[:, 1])[0]
            rho[k].append(r)
            line.append(f"{k} {r:.4f}")
        rows += len(cand) - 100
        print(f"  seed {seed}: fires {int(cand.sum())}, decomposition mismatches {mism}, "
              + ", ".join(line))
    print(f"  rows after 100-bar burn-in {rows}; ties {ties_total}; mismatches {mism_total}")
    for k, x in rho.items():
        print(f"  {k}: per-frame median rho {np.median(x):.4f} "
              f"(min {np.min(x):.4f}, max {np.max(x):.4f})")


def module_sha1():
    import importlib.util
    spec = importlib.util.spec_from_file_location("gate_e_ledger", "docs/gate_e_ledger.py")
    gl = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gl)
    path = gl.module_path("pandas_ta.candles.b3_outside_pivot3")
    print(f"== module_sha1 (LF-normalised, for docs/gate_e_ledger.csv) == {gl.lf_sha1(path)}")


if __name__ == "__main__":
    gate_a()
    reachability()
    scale_tolerance()
    causality_sweep()
    decomposition()
    module_sha1()
    print("python", sys.version.split()[0], "pandas", pd.__version__, "numpy", np.__version__)
