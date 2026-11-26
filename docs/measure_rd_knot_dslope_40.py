# -*- coding: utf-8 -*-
"""Reproduce the numbers in docs/RdKnotDslope40Measured.md.

    python docs/measure_rd_knot_dslope_40.py

Run from the repo root. Uses tests/test_rd_knot_dslope_40.py's synthetic
walk generator; the real-data reachability count comes from the Gate E run
recorded in docs/gate_e_ledger.csv, not from this script.
"""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.getcwd())
import tests.test_rd_knot_dslope_40 as T  # noqa: E402

rd_knot_dslope_40 = T.rd_knot_dslope_40


def gate_a():
    print("== Gate A: hand-derived fixture (length=10, knot_margin=2) ==")
    t = np.arange(10, dtype=float)
    y = np.where(t <= 5, t, 5 + 3 * (t - 5))
    close = T._close(np.exp(y))
    out = rd_knot_dslope_40(close, length=10, knot_margin=2)
    print(f"  warm-up NaN bars {int(out.iloc[:9].isna().sum())}, "
          f"bar9 = {out.iloc[9]!r} (expected slope change 3 - 1 = 2.0)")

    print("== Gate A: independent-loop cross-check (n=300, length=40, knot_margin=5) ==")
    close = T._walk(n=300, seed=7)
    out = rd_knot_dslope_40(close, length=40, knot_margin=5)
    ref = T._oracle(np.log(close.to_numpy(dtype=float)), 40, 5)
    m = ~np.isnan(ref)
    diffs = np.abs(out.values[m] - ref[m])
    print(f"  {int(m.sum())} defined bars, NaN masks equal "
          f"{(np.isnan(ref) == out.isna().values).all()}, max |diff| {diffs.max():.3e}")


def reachability():
    print("== Gate C: reachability on a 1,600-bar synthetic walk (seed 4) ==")
    close = T._walk(seed=4)
    out = rd_knot_dslope_40(close)
    fired = out.dropna()
    print(f"  fires {len(fired)} of {len(out)} (warm-up {len(out) - len(fired)}); "
          f"min {fired.min():.6f}, max {fired.max():.6f}, "
          f"distinct values {fired.nunique()}")

    print("== Gate C: reachability across 10 independent 600-bar seeds ==")
    for seed in range(10):
        close = T._walk(n=600, seed=seed + 100)
        out = rd_knot_dslope_40(close)
        fired = out.dropna()
        print(f"  seed {seed + 100}: fires {len(fired)}, "
              f"min {fired.min():.6f}, max {fired.max():.6f}, "
              f"distinct {fired.nunique()}")


def scale_tolerance():
    print("== Gate D: price-scale invariance (x8/x64/x10/x3.7) ==")
    close = T._walk(seed=4)
    base = rd_knot_dslope_40(close)
    for k in (8.0, 64.0, 10.0, 3.7):
        scaled = rd_knot_dslope_40(close * k)
        m = base.notna()
        exact_mismatches = int((base[m] != scaled[m]).sum())
        diff = (base[m] - scaled[m]).abs()
        rel = diff / base[m].abs().clip(lower=1e-12)
        print(f"  x{k}: NaN masks equal {(base.isna() == scaled.isna()).all()}; "
              f"exact mismatches on {int(m.sum())} co-finite cells: {exact_mismatches}; "
              f"max abs diff {diff.max():.3e}, max rel diff {rel.max():.3e}")


def causality_sweep():
    print("== Gate B: future-splice sweep, 1,600-bar walks (seeds 1 vs 2) ==")
    mod = T._load_mutant()
    a, b = T._walk(1600, seed=1), T._walk(1600, seed=2)
    real_leaks = T._leaks(rd_knot_dslope_40, a, b)
    mut = lambda c: mod.rd_knot_dslope_40(c)  # noqa: E731
    mutant_leaks = T._leaks(mut, a, b)
    print(f"  swept {len(T.OFFSETS)} J values: real module leaked at {real_leaks}, "
          f"mutant leaked at {mutant_leaks}")


def module_sha1():
    import importlib.util
    spec = importlib.util.spec_from_file_location("gate_e_ledger", "docs/gate_e_ledger.py")
    gl = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gl)
    path = gl.module_path("pandas_ta.statistics.rd_knot_dslope_40")
    print(f"== module_sha1 (LF-normalised, for docs/gate_e_ledger.csv) == {gl.lf_sha1(path)}")


if __name__ == "__main__":
    gate_a()
    reachability()
    scale_tolerance()
    causality_sweep()
    module_sha1()
    print("python", sys.version.split()[0], "pandas", pd.__version__, "numpy", np.__version__)
