# -*- coding: utf-8 -*-
"""Reproduce the numbers in docs/RdDipDepth1025Measured.md.

    python docs/measure_rd_dip_depth_10_25.py

Run from the repo root. Uses tests/test_rd_dip_depth_10_25.py's synthetic
generators; no real-data cache is available in this worktree, so Gate C here
is synthetic-only -- the receipt session adds the Gate E run's real-data
reachability count.
"""
import os
import sys

import numpy as np
import pandas as pd
from numpy.lib.stride_tricks import sliding_window_view

sys.path.insert(0, os.getcwd())
import tests.test_rd_dip_depth_10_25 as T  # noqa: E402

rd_dip_depth_10_25 = T.rd_dip_depth_10_25


def gate_a():
    print("== Gate A: independent recompute (sliding_window_view max/mean), 400 bars ==")
    high, low, close = T._walk(400, seed=7)
    ref = T._oracle(high, low, close, 10, 25)
    out = rd_dip_depth_10_25(high, low, close, length=10, avg_length=25)
    nan_match = (np.isnan(ref) == out.isna().values).all()
    m = ~np.isnan(ref)
    max_diff = np.nanmax(np.abs(out.values[m] - ref[m]))
    print(f"  {int(m.sum())} compared bars; NaN masks match: {nan_match}; max|diff| = {max_diff:.3e}")

    print("== Gate A: hand-derived fixture (length=2, avg_length=4) ==")
    high2 = pd.Series([10.0] * 3 + [20.0] * 5)
    low2 = pd.Series([8.0] * 8)
    close2 = pd.Series([9.0] * 8)
    out2 = rd_dip_depth_10_25(high2, low2, close2, length=2, avg_length=4)
    print(f"  bar3 = {out2.iloc[3]:.6f} (expect {11.0 / 4.5:.6f}); "
          f"bar6 = {out2.iloc[6]:.6f} (expect {11.0 / 12.0:.6f})")


def reachability():
    print("== Gate C: reachability on a 1200-bar synthetic frame (seed 4) ==")
    high, low, close = T._walk(1200, seed=4)
    out = rd_dip_depth_10_25(high, low, close)
    fired = out.dropna()
    print(f"  fires {len(fired)} of {len(high)} (warm-up {len(high) - len(fired)}); "
          f"distinct values {fired.nunique()}; range [{fired.min():.6f}, {fired.max():.6f}]")

    print("== Gate C: reachability across 10 independent 600-bar seeds ==")
    for seed in range(10):
        high, low, close = T._walk(600, seed=seed + 100)
        out = rd_dip_depth_10_25(high, low, close)
        fired = out.dropna()
        print(f"  seed {seed + 100}: {len(fired)} non-NaN of {len(high)}, "
              f"{fired.nunique()} distinct values")


def scale_tolerance():
    print("== Gate D: price-scale invariance of high/low/close together (x8/x64/x10/x3.7) ==")
    high, low, close = T._walk(1200, seed=4)
    base = rd_dip_depth_10_25(high, low, close)
    for k in (8.0, 64.0, 10.0, 3.7):
        scaled = rd_dip_depth_10_25(high * k, low * k, close * k)
        m = base.notna()
        diff = (base[m] - scaled[m]).abs()
        rel = (diff / base[m].abs().replace(0, np.nan))
        print(f"  x{k}: NaN masks equal {(base.isna() == scaled.isna()).all()}; "
              f"exact mismatches {int((base[m].to_numpy() != scaled[m].to_numpy()).sum())} of {int(m.sum())}; "
              f"max|diff| {diff.max():.3e}; max relative diff {rel.max():.3e}")

    print("== Gate D: 0 < fires < n and non-constant ==")
    fired = base.dropna()
    print(f"  fires {len(fired)} of {len(high)}; distinct values {fired.nunique()}; "
          f"min {fired.min():.6f}; max {fired.max():.6f}")


def causality_sweep():
    print("== Gate B: future-splice sweep ==")
    ah, al, ac = T._walk(1200, seed=1)
    bh, bl, bc = T._walk(1200, seed=2)
    real_leaks = T._leaks(rd_dip_depth_10_25, ah, al, ac, bh, bl, bc)
    mod = T._load_mutant()
    mut = lambda h, l, c: mod.rd_dip_depth_10_25(h, l, c)  # noqa: E731
    mutant_leaks = T._leaks(mut, ah, al, ac, bh, bl, bc)
    print(f"  real module leaked at {real_leaks} of {len(T.OFFSETS)}; "
          f"mutant leaked at {mutant_leaks} of {len(T.OFFSETS)}")


def module_sha1():
    import importlib.util
    spec = importlib.util.spec_from_file_location("gate_e_ledger", "docs/gate_e_ledger.py")
    gl = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gl)
    path = gl.module_path("pandas_ta.momentum.rd_dip_depth_10_25")
    print(f"== module_sha1 (LF-normalised, for docs/gate_e_ledger.csv) == {gl.lf_sha1(path)}")


if __name__ == "__main__":
    gate_a()
    reachability()
    scale_tolerance()
    causality_sweep()
    module_sha1()
    print("python", sys.version.split()[0], "pandas", pd.__version__, "numpy", np.__version__)
