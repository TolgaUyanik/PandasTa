# -*- coding: utf-8 -*-
"""Reproduce the numbers in docs/RdOutsideBarMeasured.md.

    python docs/measure_rd_outside_bar.py

Run from the repo root. Uses tests/test_rd_outside_bar.py's synthetic OHLC
generator; no real-data cache is available in this worktree, so Gate C here
is synthetic-only. The real-data reachability count comes from the launcher's
Gate E run (see docs/RdOutsideBarMeasured.md).
"""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.getcwd())
import tests.test_rd_outside_bar as T  # noqa: E402

rd_outside_bar = T.rd_outside_bar


def gate_a():
    print("== Gate A: hand-derived fixtures (fire, high-only, low-only, tie) ==")
    cases = {
        "fires": [(101.0, 99.0), (102.0, 98.0)],
        "high_only": [(101.0, 99.0), (102.0, 99.5)],
        "low_only": [(101.0, 99.0), (100.5, 98.0)],
        "tie": [(101.0, 99.0), (101.0, 99.0)],
    }
    for name, rows in cases.items():
        df = T._hl(rows)
        out = rd_outside_bar(df.high, df.low)
        print(f"  {name}: warm-up NaN bars {int(out.iloc[:1].isna().sum())}, "
              f"value at bar 1 = {out.iloc[1]}")


def reachability():
    print("== Gate C: reachability on a 2,000-bar synthetic frame (seed 4) ==")
    df = T._frame(n=2000, seed=4)
    out = rd_outside_bar(df.high, df.low)
    fired = out.dropna()
    fires = int((fired == 1.0).sum())
    print(f"  fires {len(fired)} of 2000 (warm-up 1); outside-bar {fires}, "
          f"zero {len(fired) - fires}")

    print("== Gate C: reachability across 10 independent 600-bar seeds ==")
    for seed in range(10):
        df = T._frame(n=600, seed=seed + 100)
        out = rd_outside_bar(df.high, df.low)
        fired = out.dropna()
        fires = int((fired == 1.0).sum())
        print(f"  seed {seed + 100}: fires {fires} of {len(fired)}")


def scale_tolerance():
    print("== Gate D: price-scale invariance (x8/x64/x10/x3.7) ==")
    df = T._frame(seed=4)
    base = rd_outside_bar(df.high, df.low)
    for k in (8.0, 64.0, 10.0, 3.7):
        scaled = rd_outside_bar(df.high * k, df.low * k)
        m = base.notna()
        mismatches = int((base[m] != scaled[m]).sum())
        print(f"  x{k}: NaN masks equal {(base.isna() == scaled.isna()).all()}; "
              f"mismatches on {int(m.sum())} co-finite cells: {mismatches}")


def causality_sweep():
    print("== Gate B: future-perturbation sweep, 600-bar frame, J in range(10, 596, 2) ==")
    mod = T._load_mutant()
    a = T._frame(600, seed=1)
    b = T._frame(600, seed=2)
    mut_a_full = mod.rd_outside_bar(a.high, a.low)
    real_a_full = rd_outside_bar(a.high, a.low)
    js = list(range(10, 596, 2))
    real_leaks, mutant_leaks = 0, 0
    for j in js:
        spliced = a.copy()
        spliced.iloc[j:] = b.iloc[j:].to_numpy()
        real_b = rd_outside_bar(spliced.high, spliced.low)
        if not real_a_full.iloc[:j].equals(real_b.iloc[:j]):
            real_leaks += 1
        mut_b = mod.rd_outside_bar(spliced.high, spliced.low)
        av, bv = mut_a_full.iloc[j - 1], mut_b.iloc[j - 1]
        both_nan = pd.isna(av) and pd.isna(bv)
        if not (av == bv or both_nan):
            mutant_leaks += 1
    print(f"  swept {len(js)} J values: real module leaked at {real_leaks}, "
          f"mutant leaked at {mutant_leaks}")


def module_sha1():
    import importlib.util
    spec = importlib.util.spec_from_file_location("gate_e_ledger", "docs/gate_e_ledger.py")
    gl = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gl)
    path = gl.module_path("pandas_ta.candles.rd_outside_bar")
    print(f"== module_sha1 (LF-normalised, for docs/gate_e_ledger.csv) == {gl.lf_sha1(path)}")


if __name__ == "__main__":
    gate_a()
    reachability()
    scale_tolerance()
    causality_sweep()
    module_sha1()
    print("python", sys.version.split()[0], "pandas", pd.__version__, "numpy", np.__version__)
