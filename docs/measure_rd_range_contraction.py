# -*- coding: utf-8 -*-
"""Reproduce the numbers in docs/RdRangeContractionMeasured.md.

    python docs/measure_rd_range_contraction.py

Run from the repo root. Uses tests/test_rd_range_contraction.py's synthetic
walk generator; the real-data reachability count comes from the Gate E run
recorded in docs/gate_e_ledger.csv, not from this script.
"""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.getcwd())
import tests.test_rd_range_contraction as T  # noqa: E402

rd_range_contraction = T.rd_range_contraction


def gate_a():
    print("== Gate A: hand-derived fixture (n=2, short=2, long=4) ==")
    high = pd.Series([11.0] * 5 + [21.0] * 3)
    low = pd.Series([9.0] * 5 + [9.0] * 3)
    out = rd_range_contraction(high, low, n=2, short=2, long=4)
    print(f"  bar7 = {out.iloc[7]!r} (expected 12.0/9.5 = {12.0 / 9.5!r})")

    print("== Gate A: independent-loop cross-check (n=400, seed=7, n=5/10/50) ==")
    h, l = T._walk(n=400, seed=7)
    out = rd_range_contraction(h, l, n=5, short=10, long=50)
    ref = T._oracle(h, l, 5, 10, 50)
    m = ~np.isnan(ref)
    diffs = np.abs(out.values[m] - ref[m])
    print(f"  {int(m.sum())} defined bars, NaN masks equal "
          f"{(np.isnan(ref) == out.isna().values).all()}, max |diff| {diffs.max():.3e}")


def reachability():
    print("== Gate C: reachability on a 1,200-bar synthetic walk (seed 4) ==")
    h, l = T._walk(seed=4)
    out = rd_range_contraction(h, l)
    fired = out.dropna()
    print(f"  fires {len(fired)} of {len(out)} (warm-up {len(out) - len(fired)}); "
          f"min {fired.min():.6f}, max {fired.max():.6f}, "
          f"distinct values {fired.nunique()}")

    print("== Gate C: reachability across 10 independent 600-bar seeds ==")
    for seed in range(10):
        h, l = T._walk(n=600, seed=seed + 100)
        out = rd_range_contraction(h, l)
        fired = out.dropna()
        print(f"  seed {seed + 100}: fires {len(fired)}, "
              f"min {fired.min():.6f}, max {fired.max():.6f}, "
              f"distinct {fired.nunique()}")


def scale_tolerance():
    print("== Gate D: price-scale invariance (x8/x64 bit-identical, x10/x3.7 tolerance) ==")
    h, l = T._walk(seed=4)
    base = rd_range_contraction(h, l)
    for k in (8.0, 64.0, 10.0, 3.7):
        scaled = rd_range_contraction(h * k, l * k)
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
    ah, al = T._walk(1200, seed=1)
    bh, bl = T._walk(1200, seed=2)
    real_leaks = T._leaks(rd_range_contraction, ah, al, bh, bl)
    mut = lambda h, l: mod.rd_range_contraction(h, l)  # noqa: E731
    mutant_leaks = T._leaks(mut, ah, al, bh, bl)
    print(f"  swept {len(T.OFFSETS)} J values: real module leaked at {real_leaks}, "
          f"mutant leaked at {mutant_leaks}")


def module_sha1():
    import importlib.util
    spec = importlib.util.spec_from_file_location("gate_e_ledger", "docs/gate_e_ledger.py")
    gl = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gl)
    path = gl.module_path("pandas_ta.volatility.rd_range_contraction")
    print(f"== module_sha1 (LF-normalised, for docs/gate_e_ledger.csv) == {gl.lf_sha1(path)}")


if __name__ == "__main__":
    gate_a()
    reachability()
    scale_tolerance()
    causality_sweep()
    module_sha1()
    print("python", sys.version.split()[0], "pandas", pd.__version__, "numpy", np.__version__)
