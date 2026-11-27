# -*- coding: utf-8 -*-
"""Reproduce the numbers in docs/NmMmi250Measured.md.

    python docs/measure_nm_mmi_250.py

Run from the repo root. Uses tests/test_nm_mmi_250.py's synthetic frame
generators and mutants; the real-data reachability count comes from the
Gate E run recorded in docs/gate_e_ledger.csv (owed at port time), not from
this script.
"""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.getcwd())
import tests.test_nm_mmi_250 as T  # noqa: E402

nm_mmi_250 = T.nm_mmi_250


def gate_a():
    print("== Gate A: hand-derived window ([1, 2, 3, 4], length=4) ==")
    out = nm_mmi_250(T._closes_from_returns([1.0, 2.0, 3.0, 4.0]), length=4)
    print(f"  bar4 = {float(out.iloc[4])!r} (expected 200/3 = {200.0 / 3.0!r})")

    print("== Gate A: independent scalar-loop cross-check (400 bars, seed=5, length=50) ==")
    close = T._walk(400, seed=5)
    port, oracle = nm_mmi_250(close, length=50), T._oracle_series(close, length=50)
    m = port.notna()
    diffs = (port[m] - oracle[m]).abs()
    print(f"  {int(m.sum())} defined bars, NaN masks equal "
          f"{(port.isna() == oracle.isna()).all()}, max |diff| {diffs.max():.3e}")


def min_length():
    print("== MIN_LENGTH: 2-return window forced constant, 3-return informative ==")
    rng = np.random.default_rng(0)
    two = {T._reversal_fraction(rng.normal(0.0, 1.0, 2)) for _ in range(3000)}
    print(f"  length=2, 3000 draws: distinct values {sorted(two)}")
    rng = np.random.default_rng(1)
    three = {T._reversal_fraction(rng.normal(0.0, 1.0, 3)) for _ in range(30000)}
    print(f"  length=3, 30000 draws: distinct values {sorted(three)}")


def reachability():
    print("== Gate C: reachability on three 1,500-bar synthetic frames (length=250) ==")
    for name in sorted(T.FRAMES):
        s = T.base(name)
        fired = s.dropna()
        print(f"  {name}: fires {len(fired)} of {len(s)} (warm-up {len(s) - len(fired)}); "
              f"min {fired.min():.6f}, max {fired.max():.6f}, "
              f"distinct values {fired.nunique()}")


def scale_tolerance():
    print("== Gate D: price-scale invariance (x8/x64 bit-identical, x10/x3.7 tolerance) ==")
    for name in sorted(T.FRAMES):
        f = T.FRAMES[name]
        base = nm_mmi_250(f)
        for k in (8.0, 64.0, 10.0, 3.7):
            scaled = nm_mmi_250(f * k)
            m = base.notna()
            exact_mismatches = int((base[m] != scaled[m]).sum())
            diff = (base[m] - scaled[m]).abs()
            print(f"  {name} x{k}: NaN masks equal {(base.isna() == scaled.isna()).all()}; "
                  f"exact mismatches on {int(m.sum())} co-finite cells: {exact_mismatches}; "
                  f"max abs diff {diff.max():.3e}")


def causality_sweep():
    print("== Gate B: future-splice sweep + mutants, three 1,500-bar frames ==")
    for frame in sorted(T.FRAMES_B):
        close = T.FRAMES_B[frame]
        real_leaks = T._leak_offsets(nm_mmi_250, close)
        print(f"  {frame}: swept {len(T.OFFSETS)} offsets, real module leaked at "
              f"{len(real_leaks)}")
        for name in sorted(T.MUTANTS):
            mod = T._load_mutant(*T.MUTANTS[name])
            hits = T._leak_offsets(mod.nm_mmi_250, close)
            print(f"    mutant {name}: leaked at {len(hits)} of {len(T.OFFSETS)}")


def module_sha1():
    import importlib.util
    spec = importlib.util.spec_from_file_location("gate_e_ledger", "docs/gate_e_ledger.py")
    gl = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gl)
    path = gl.module_path("pandas_ta.statistics.nm_mmi_250")
    print(f"== module_sha1 (LF-normalised, for docs/gate_e_ledger.csv) == {gl.lf_sha1(path)}")


if __name__ == "__main__":
    gate_a()
    min_length()
    reachability()
    scale_tolerance()
    causality_sweep()
    module_sha1()
    print("python", sys.version.split()[0], "pandas", pd.__version__, "numpy", np.__version__)
