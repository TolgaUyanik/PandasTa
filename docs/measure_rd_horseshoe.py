# -*- coding: utf-8 -*-
"""Reproduce the numbers in docs/RdHorseshoeMeasured.md.

    python docs/measure_rd_horseshoe.py

Run from the repo root. Uses tests/test_rd_horseshoe.py's synthetic OHLC
generator; no real-data cache is available in this worktree, so Gate C here
is synthetic-only -- the receipt session adds the Gate E run's real-data
reachability count.
"""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.getcwd())
import tests.test_rd_horseshoe as T  # noqa: E402

rd_horseshoe = T.rd_horseshoe


def gate_a():
    print("== Gate A: hand-derived fixtures (bull, bear, outer-bound block, doji block) ==")
    for name, rows, fn in (
        ("bull", T._bull_rows(), None),
        ("bear", T._bear_rows(), None),
    ):
        df = T._ohlc(rows)
        out = rd_horseshoe(df.open, df.high, df.low, df.close)
        print(f"  {name} fixture: warm-up NaN bars {int(out.iloc[:3].isna().sum())}, "
              f"value at bar 3 = {out.iloc[3]}")


def reachability():
    print("== Gate C: reachability on a 2,000-bar synthetic frame (seed 4) ==")
    df = T._frame(n=2000, seed=4)
    out = rd_horseshoe(df.open, df.high, df.low, df.close)
    fired = out.dropna()
    bulls = int((fired == 1.0).sum())
    bears = int((fired == -1.0).sum())
    print(f"  fires {len(fired)} of 2000 (warm-up 3); bull {bulls}, bear {bears}, "
          f"zero {len(fired) - bulls - bears}")

    print("== Gate C: reachability across 10 independent 600-bar seeds ==")
    for seed in range(10):
        df = T._frame(n=600, seed=seed + 100)
        out = rd_horseshoe(df.open, df.high, df.low, df.close)
        fired = out.dropna()
        bulls = int((fired == 1.0).sum())
        bears = int((fired == -1.0).sum())
        print(f"  seed {seed + 100}: bull {bulls}, bear {bears}")


def scale_tolerance():
    print("== Gate D: price-scale invariance (x8/x64/x10/x3.7) ==")
    df = T._frame(seed=4)
    base = rd_horseshoe(df.open, df.high, df.low, df.close)
    for k in (8.0, 64.0, 10.0, 3.7):
        scaled = rd_horseshoe(df.open * k, df.high * k, df.low * k, df.close * k)
        m = base.notna()
        mismatches = int((base[m] != scaled[m]).sum())
        print(f"  x{k}: NaN masks equal {(base.isna() == scaled.isna()).all()}; "
              f"mismatches on {int(m.sum())} co-finite cells: {mismatches}")


def causality_sweep():
    print("== Gate B: future-perturbation sweep, 600-bar frame, J in range(10, 596, 2) ==")
    mod = T._load_mutant()
    a = T._frame(600, seed=1)
    b = T._frame(600, seed=2)
    mut_a_full = mod.rd_horseshoe(a.open, a.high, a.low, a.close)
    real_a_full = rd_horseshoe(a.open, a.high, a.low, a.close)
    js = list(range(10, 596, 2))
    real_leaks, mutant_leaks = 0, 0
    for j in js:
        spliced = a.copy()
        spliced.iloc[j:] = b.iloc[j:].to_numpy()
        real_b = rd_horseshoe(spliced.open, spliced.high, spliced.low, spliced.close)
        if not real_a_full.iloc[:j].equals(real_b.iloc[:j]):
            real_leaks += 1
        mut_b = mod.rd_horseshoe(spliced.open, spliced.high, spliced.low, spliced.close)
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
    path = gl.module_path("pandas_ta.candles.rd_horseshoe")
    print(f"== module_sha1 (LF-normalised, for docs/gate_e_ledger.csv) == {gl.lf_sha1(path)}")


if __name__ == "__main__":
    gate_a()
    reachability()
    scale_tolerance()
    causality_sweep()
    module_sha1()
    print("python", sys.version.split()[0], "pandas", pd.__version__, "numpy", np.__version__)
