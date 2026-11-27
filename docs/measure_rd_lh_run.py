# -*- coding: utf-8 -*-
"""Reproduce the numbers in docs/RdLhRunMeasured.md.

    python docs/measure_rd_lh_run.py

Run from the repo root. Uses tests/test_rd_lh_run.py's synthetic generator;
no real-data cache is available in this worktree, so Gate C here is
synthetic-only -- the receipt session adds the Gate E run's real-data
reachability count.
"""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.getcwd())
import tests.test_rd_lh_run as T  # noqa: E402

rd_lh_run = T.rd_lh_run


def gate_a():
    print("== Gate A: independent recompute (plain Python loop), 800 bars ==")
    high = T._walk(800, seed=7)
    hv = high.to_numpy(dtype=float)
    ref = np.zeros(len(hv))
    for t in range(1, len(hv)):
        ref[t] = ref[t - 1] + 1 if hv[t] < hv[t - 1] else 0.0
    out = rd_lh_run(high)
    print(f"  {len(hv)} bars; exact match: {bool((out.to_numpy() == ref).all())}")

    print("== Gate A: hand-computed sequence ==")
    high2 = pd.Series([10.0, 9.0, 8.0, 8.0, 11.0, 10.0, 10.0])
    out2 = rd_lh_run(high2)
    print(f"  {out2.tolist()} (expect [0.0, 1.0, 2.0, 0.0, 0.0, 1.0, 0.0])")


def reachability():
    print("== Gate C: reachability on a 1200-bar synthetic frame (seed 4) ==")
    high = T._walk(1200, seed=4)
    out = rd_lh_run(high)
    nonzero = out[out > 0]
    print(f"  {len(out) - int((out == 0).sum())} of {len(out)} bars nonzero; "
          f"distinct values {out.nunique()}; max run {int(out.max())}")

    print("== Gate C: reachability across 10 independent 600-bar seeds ==")
    for seed in range(10):
        high = T._walk(600, seed=seed + 100)
        out = rd_lh_run(high)
        print(f"  seed {seed + 100}: {int((out > 0).sum())} nonzero of {len(high)}, "
              f"{out.nunique()} distinct values, max run {int(out.max())}")


def tie_check_and_scale():
    print("== Gate D: exact consecutive ties in `high` (seed-4 walk) ==")
    high = T._walk(1200, seed=4)
    hv = high.to_numpy(dtype=float)
    ties = int((hv[1:] == hv[:-1]).sum())
    print(f"  {ties} exact ties among 1199 consecutive pairs")

    print("== Gate D: price-scale invariance (x8/x64/x10/x3.7) ==")
    base = rd_lh_run(high)
    for k in (8.0, 64.0, 10.0, 3.7):
        scaled = rd_lh_run(high * k)
        mism = int((base.to_numpy() != scaled.to_numpy()).sum())
        print(f"  x{k}: mismatches {mism} of {len(base)}")


def causality_sweep():
    print("== Gate B: future-splice sweep ==")
    ah, bh = T._walk(1200, seed=1), T._walk(1200, seed=2)
    real_leaks = T._leaks(rd_lh_run, ah, bh)
    mod = T._load_mutant()
    mut = lambda h: mod.rd_lh_run(h)  # noqa: E731
    mutant_leaks = T._leaks(mut, ah, bh)
    print(f"  real module leaked at {real_leaks} of {len(T.OFFSETS)}; "
          f"mutant leaked at {mutant_leaks} of {len(T.OFFSETS)}")


def module_sha1():
    import importlib.util
    spec = importlib.util.spec_from_file_location("gate_e_ledger", "docs/gate_e_ledger.py")
    gl = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gl)
    path = gl.module_path("pandas_ta.trend.rd_lh_run")
    print(f"== module_sha1 (LF-normalised, for docs/gate_e_ledger.csv) == {gl.lf_sha1(path)}")


if __name__ == "__main__":
    gate_a()
    reachability()
    tie_check_and_scale()
    causality_sweep()
    module_sha1()
    print("python", sys.version.split()[0], "pandas", pd.__version__, "numpy", np.__version__)
