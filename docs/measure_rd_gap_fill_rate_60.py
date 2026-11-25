# -*- coding: utf-8 -*-
"""Reproduce the numbers in docs/RdGapFillRate60Measured.md.

    python docs/measure_rd_gap_fill_rate_60.py

Run from the repo root. Uses tests/test_rd_gap_fill_rate_60.py's synthetic
OHLC generator; no real-data cache is available in this worktree, so Gate C
here is synthetic-only -- the receipt session adds the Gate E run's
real-data reachability count.
"""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.getcwd())
import tests.test_rd_gap_fill_rate_60 as T  # noqa: E402

rd_gap_fill_rate_60 = T.rd_gap_fill_rate_60


def gate_a():
    print("== Gate A: hand-derived fixture (length=3) ==")
    df = T._ohlc(T._hand_rows())
    out = rd_gap_fill_rate_60(df.open, df.high, df.low, df.close, length=3)
    print(f"  warm-up NaN bars {int(out.iloc[:2].isna().sum())}, "
          f"bar2 = {out.iloc[2]}, bar3 = {out.iloc[3]}")


def reachability():
    print("== Gate C: reachability on a 1,600-bar synthetic frame (seed 4) ==")
    df = T._frame(seed=4)
    out = rd_gap_fill_rate_60(df.open, df.high, df.low, df.close)
    fired = out.dropna()
    print(f"  fires {len(fired)} of {len(out)} (warm-up {len(out) - len(fired)}); "
          f"min {fired.min():.4f}, max {fired.max():.4f}, "
          f"distinct values {fired.nunique()}")

    print("== Gate C: reachability across 10 independent 600-bar seeds ==")
    for seed in range(10):
        df = T._frame(n=600, seed=seed + 100)
        out = rd_gap_fill_rate_60(df.open, df.high, df.low, df.close)
        fired = out.dropna()
        print(f"  seed {seed + 100}: fires {len(fired)}, "
              f"min {fired.min():.4f}, max {fired.max():.4f}")


def scale_tolerance():
    print("== Gate D: price-scale invariance (x8/x64/x10/x3.7) ==")
    df = T._frame(seed=4)
    base = rd_gap_fill_rate_60(df.open, df.high, df.low, df.close)
    for k in (8.0, 64.0, 10.0, 3.7):
        scaled = rd_gap_fill_rate_60(df.open * k, df.high * k, df.low * k, df.close * k)
        m = base.notna()
        mismatches = int((base[m] != scaled[m]).sum())
        print(f"  x{k}: NaN masks equal {(base.isna() == scaled.isna()).all()}; "
              f"mismatches on {int(m.sum())} co-finite cells: {mismatches}")


def causality_sweep():
    print("== Gate B: future-splice sweep, 1,600-bar frames (seeds 1 vs 2) ==")
    mod = T._load_mutant()
    a, b = T._frame(1600, seed=1), T._frame(1600, seed=2)
    real_leaks = T._leaks(rd_gap_fill_rate_60, a, b)
    mut = lambda o, h, l, c: mod.rd_gap_fill_rate_60(o, h, l, c)  # noqa: E731
    mutant_leaks = T._leaks(mut, a, b)
    print(f"  swept {len(T.OFFSETS)} J values: real module leaked at {real_leaks}, "
          f"mutant leaked at {mutant_leaks}")


def module_sha1():
    import importlib.util
    spec = importlib.util.spec_from_file_location("gate_e_ledger", "docs/gate_e_ledger.py")
    gl = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gl)
    path = gl.module_path("pandas_ta.statistics.rd_gap_fill_rate_60")
    print(f"== module_sha1 (LF-normalised, for docs/gate_e_ledger.csv) == {gl.lf_sha1(path)}")


if __name__ == "__main__":
    gate_a()
    reachability()
    scale_tolerance()
    causality_sweep()
    module_sha1()
    print("python", sys.version.split()[0], "pandas", pd.__version__, "numpy", np.__version__)
