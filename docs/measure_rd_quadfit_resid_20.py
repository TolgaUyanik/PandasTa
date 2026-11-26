# -*- coding: utf-8 -*-
"""Reproduce the numbers in docs/RdQuadfitResid20Measured.md.

    python docs/measure_rd_quadfit_resid_20.py

Run from the repo root. Uses tests/test_rd_quadfit_resid_20.py's synthetic
walk generator; the real-data reachability count comes from the Gate E run
recorded in docs/gate_e_ledger.csv, not from this script.
"""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.getcwd())
import tests.test_rd_quadfit_resid_20 as T  # noqa: E402

rd_quadfit_resid_20 = T.rd_quadfit_resid_20


def gate_a():
    print("== Gate A: hand-derived fixture (length=4) ==")
    close = T._close(np.exp([0.0, 1 / 9, 4 / 9, 2.0]))
    out = rd_quadfit_resid_20(close, length=4)
    print(f"  warm-up NaN bars {int(out.iloc[:3].isna().sum())}, "
          f"bar3 = {out.iloc[3]!r} (expected 1/sqrt(5) = {1 / np.sqrt(5):.16f})")

    print("== Gate A: independent-loop cross-check (n=300, length=40) ==")
    close = T._walk(n=300, seed=7)
    out = rd_quadfit_resid_20(close, length=40)
    ref = T._oracle(np.log(close.to_numpy(dtype=float)), 40)
    m = ~np.isnan(ref)
    diffs = np.abs(out.values[m] - ref[m])
    print(f"  {int(m.sum())} defined bars, NaN masks equal "
          f"{(np.isnan(ref) == out.isna().values).all()}, max |diff| {diffs.max():.3e}")


def reachability():
    print("== Gate C: reachability on a 1,600-bar synthetic walk (seed 4) ==")
    close = T._walk(seed=4)
    out = rd_quadfit_resid_20(close)
    fired = out.dropna()
    print(f"  fires {len(fired)} of {len(out)} (warm-up {len(out) - len(fired)}); "
          f"min {fired.min():.4f}, max {fired.max():.4f}, "
          f"distinct values {fired.nunique()}")

    print("== Gate C: reachability across 10 independent 600-bar seeds ==")
    for seed in range(10):
        close = T._walk(n=600, seed=seed + 100)
        out = rd_quadfit_resid_20(close)
        fired = out.dropna()
        print(f"  seed {seed + 100}: fires {len(fired)}, "
              f"min {fired.min():.4f}, max {fired.max():.4f}, "
              f"distinct {fired.nunique()}")


def scale_tolerance():
    print("== Gate D: price-scale invariance (x8/x64 bit-identical, x10/x3.7 tolerance) ==")
    close = T._walk(seed=4)
    base = rd_quadfit_resid_20(close)
    for k in (8.0, 64.0, 10.0, 3.7):
        scaled = rd_quadfit_resid_20(close * k)
        m = base.notna()
        same = (base.isna() == scaled.isna()).all()
        diffs = np.abs(base[m].to_numpy() - scaled[m].to_numpy())
        exact_mismatches = int((diffs != 0).sum())
        print(f"  x{k}: NaN masks equal {same}; co-finite cells {int(m.sum())}; "
              f"exact mismatches {exact_mismatches}; max |diff| {diffs.max():.3e}; "
              f"max relative |diff| {np.nanmax(np.where(base[m] != 0, diffs / np.abs(base[m]), 0)):.3e}")


def causality_sweep():
    print("== Gate B: future-splice sweep, 1,600-bar walks (seeds 1 vs 2) ==")
    mod = T._load_mutant()
    a, b = T._walk(1600, seed=1), T._walk(1600, seed=2)
    real_leaks = T._leaks(rd_quadfit_resid_20, a, b)
    mut = lambda c: mod.rd_quadfit_resid_20(c)  # noqa: E731
    mutant_leaks = T._leaks(mut, a, b)
    print(f"  swept {len(T.OFFSETS)} J values: real module leaked at {real_leaks}, "
          f"mutant leaked at {mutant_leaks}")


def module_sha1():
    import importlib.util
    spec = importlib.util.spec_from_file_location("gate_e_ledger", "docs/gate_e_ledger.py")
    gl = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gl)
    path = gl.module_path("pandas_ta.statistics.rd_quadfit_resid_20")
    print(f"== module_sha1 (LF-normalised, for docs/gate_e_ledger.csv) == {gl.lf_sha1(path)}")


if __name__ == "__main__":
    gate_a()
    reachability()
    scale_tolerance()
    causality_sweep()
    module_sha1()
    print("python", sys.version.split()[0], "pandas", pd.__version__, "numpy", np.__version__)
