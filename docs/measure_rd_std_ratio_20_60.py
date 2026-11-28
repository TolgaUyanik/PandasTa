# -*- coding: utf-8 -*-
"""Reproduce the numbers in docs/RdStdRatio2060Measured.md.

    python docs/measure_rd_std_ratio_20_60.py

Run from the repo root. Uses tests/test_rd_std_ratio_20_60.py's synthetic
walk generator; the real-data reachability count comes from the Gate E run
recorded in docs/gate_e_ledger.csv, not from this script.
"""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.getcwd())
import tests.test_rd_std_ratio_20_60 as T  # noqa: E402

rd_std_ratio_20_60 = T.rd_std_ratio_20_60


def gate_a():
    print("== Gate A: hand-derived fixture (length=2, avg_length=4) ==")
    close = pd.Series([10.0] * 5 + [20.0] * 3)
    out = rd_std_ratio_20_60(close, length=2, avg_length=4)
    print(f"  bar5 = {out.iloc[5]!r} (expected 4.0)")

    print("== Gate A: independent-loop cross-check (n=400, seed=7, length=20/avg=60) ==")
    c = T._walk(n=400, seed=7)
    out = rd_std_ratio_20_60(c, length=20, avg_length=60)
    ref = T._oracle(c, 20, 60)
    m = ~np.isnan(ref)
    diffs = np.abs(out.values[m] - ref[m])
    print(f"  {int(m.sum())} defined bars, NaN masks equal "
          f"{(np.isnan(ref) == out.isna().values).all()}, max |diff| {diffs.max():.3e}")


def reachability():
    print("== Gate C: reachability on a 1,200-bar synthetic walk (seed 4) ==")
    c = T._walk(seed=4)
    out = rd_std_ratio_20_60(c)
    fired = out.dropna()
    print(f"  fires {len(fired)} of {len(out)} (warm-up {len(out) - len(fired)}); "
          f"min {fired.min():.6f}, max {fired.max():.6f}, "
          f"distinct values {fired.nunique()}")

    print("== Gate C: reachability across 10 independent 600-bar seeds ==")
    for seed in range(10):
        c = T._walk(n=600, seed=seed + 100)
        out = rd_std_ratio_20_60(c)
        fired = out.dropna()
        print(f"  seed {seed + 100}: fires {len(fired)}, "
              f"min {fired.min():.6f}, max {fired.max():.6f}, "
              f"distinct {fired.nunique()}")


def scale_tolerance():
    print("== Gate D: price-scale invariance (x8/x64 bit-identical, x10/x3.7 tolerance) ==")
    c = T._walk(seed=4)
    base = rd_std_ratio_20_60(c)
    for k in (8.0, 64.0, 10.0, 3.7):
        scaled = rd_std_ratio_20_60(c * k)
        m = base.notna()
        exact_mismatches = int((base[m] != scaled[m]).sum())
        diff = (base[m] - scaled[m]).abs()
        rel = diff / base[m].abs().clip(lower=1e-12)
        print(f"  x{k}: NaN masks equal {(base.isna() == scaled.isna()).all()}; "
              f"exact mismatches on {int(m.sum())} co-finite cells: {exact_mismatches}; "
              f"max abs diff {diff.max():.3e}, max rel diff {rel.max():.3e}")


def causality_sweep():
    print("== Gate B: future-splice sweep, 1,200-bar walks (seeds 1 vs 2) ==")
    mod = T._load_mutant()
    ac = T._walk(1200, seed=1)
    bc = T._walk(1200, seed=2)
    real_leaks = T._leaks(rd_std_ratio_20_60, ac, bc)
    mut = lambda c: mod.rd_std_ratio_20_60(c)  # noqa: E731
    mutant_leaks = T._leaks(mut, ac, bc)
    print(f"  swept {len(T.OFFSETS)} J values: real module leaked at {real_leaks}, "
          f"mutant leaked at {mutant_leaks}")


def module_sha1():
    import importlib.util
    spec = importlib.util.spec_from_file_location("gate_e_ledger", "docs/gate_e_ledger.py")
    gl = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gl)
    path = gl.module_path("pandas_ta.volatility.rd_std_ratio_20_60")
    print(f"== module_sha1 (LF-normalised, for docs/gate_e_ledger.csv) == {gl.lf_sha1(path)}")


if __name__ == "__main__":
    gate_a()
    reachability()
    scale_tolerance()
    causality_sweep()
    module_sha1()
    print("python", sys.version.split()[0], "pandas", pd.__version__, "numpy", np.__version__)
