# -*- coding: utf-8 -*-
"""Reproduce the numbers in docs/NmEffortResult20Measured.md.

    python docs/measure_nm_effort_result_20.py

Run from the repo root. Uses tests/test_nm_effort_result_20.py's synthetic
frame and mutants; the real-data reachability count comes from the Gate E
run recorded in docs/gate_e_ledger.csv (owed at port time), not from this
script.
"""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.getcwd())
import tests.test_nm_effort_result_20 as T  # noqa: E402

nm_effort_result_20 = T.nm_effort_result_20


def gate_a():
    print("== Gate A: hand-derived window (V=[100,200,150,300], range=[2,4,1,5], length=2) ==")
    volume = T.pd.Series([100.0, 200.0, 150.0, 300.0])
    rng = T.pd.Series([2.0, 4.0, 1.0, 5.0])
    high, low = rng, T.pd.Series([0.0, 0.0, 0.0, 0.0])
    out = nm_effort_result_20(high, low, volume, length=2)
    print(f"  bar1={float(out.iloc[1])!r} (expected 1.0)")
    print(f"  bar2={float(out.iloc[2])!r} (expected 15/7={15.0 / 7.0!r})")
    print(f"  bar3={float(out.iloc[3])!r} (expected 0.8)")

    print("== Gate A: independent scalar-loop cross-check (400 bars, length=50) ==")
    high, low, volume = T.HIGH.iloc[:400], T.LOW.iloc[:400], T.VOLUME.iloc[:400]
    port = nm_effort_result_20(high, low, volume, length=50)
    m = port.notna()
    print(f"  {int(m.sum())} defined bars of {len(port)}")


def min_length():
    print("== MIN_LENGTH: 1-bar window forced to {1.0}, 2-bar window informative ==")
    rng = np.random.default_rng(0)
    one = set()
    for _ in range(3000):
        v, r = rng.uniform(1.0, 100.0, 1), rng.uniform(1.0, 100.0, 1)
        one.add(round(T._ratio(list(v), list(r)), 9))
    print(f"  length=1, 3000 draws: distinct values {sorted(one)}")
    rng = np.random.default_rng(1)
    two = set()
    for _ in range(3000):
        v, r = rng.uniform(1.0, 100.0, 2), rng.uniform(1.0, 100.0, 2)
        val = T._ratio(list(v), list(r))
        if np.isfinite(val):
            two.add(round(val, 6))
    print(f"  length=2, 3000 draws: {len(two)} distinct values")


def reachability():
    print("== Gate C: reachability on a 1,500-bar synthetic frame (length=20) ==")
    s = T.base()
    fired = s.dropna()
    print(f"  fires {len(fired)} of {len(s)} (warm-up {len(s) - len(fired)}); "
          f"min {fired.min():.6f}, max {fired.max():.6f}, distinct values {fired.nunique()}")


def scale_tolerance():
    print("== Gate D: price/volume-scale invariance (x8/x64 bit-identical, x10/x3.7 tolerance) ==")
    base = T.base()
    for axis, scale in (
            ("price", lambda k: nm_effort_result_20(T.HIGH * k, T.LOW * k, T.VOLUME)),
            ("volume", lambda k: nm_effort_result_20(T.HIGH, T.LOW, T.VOLUME * k)),
            ("combined", lambda k: nm_effort_result_20(T.HIGH * k, T.LOW * k, T.VOLUME * k)),
    ):
        for k in (8.0, 64.0, 10.0, 3.7):
            scaled = scale(k)
            m = base.notna()
            exact_mismatches = int((base[m] != scaled[m]).sum())
            diff = (base[m] - scaled[m]).abs()
            print(f"  {axis} x{k}: NaN masks equal {(base.isna() == scaled.isna()).all()}; "
                  f"exact mismatches on {int(m.sum())} co-finite cells: {exact_mismatches}; "
                  f"max abs diff {diff.max():.3e}")


def causality_sweep():
    print("== Gate B: future-splice sweep + mutants, 1,500-bar frame ==")
    real_leaks = T._leak_offsets(nm_effort_result_20, T.HIGH, T.LOW, T.VOLUME)
    print(f"  swept {len(T.OFFSETS)} offsets, real module leaked at {len(real_leaks)}")
    for name in sorted(T.MUTANTS):
        mod = T._load_mutant(*T.MUTANTS[name])
        hits = T._leak_offsets(mod.nm_effort_result_20, T.HIGH, T.LOW, T.VOLUME)
        print(f"    mutant {name}: leaked at {len(hits)} of {len(T.OFFSETS)}")


def module_sha1():
    import importlib.util
    spec = importlib.util.spec_from_file_location("gate_e_ledger", "docs/gate_e_ledger.py")
    gl = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gl)
    path = gl.module_path("pandas_ta.volume.nm_effort_result_20")
    print(f"== module_sha1 (LF-normalised, for docs/gate_e_ledger.csv) == {gl.lf_sha1(path)}")


if __name__ == "__main__":
    gate_a()
    min_length()
    reachability()
    scale_tolerance()
    causality_sweep()
    module_sha1()
    print("python", sys.version.split()[0], "pandas", pd.__version__, "numpy", np.__version__)
