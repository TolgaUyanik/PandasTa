# -*- coding: utf-8 -*-
"""Reproduce the numbers in docs/NmPriceDensity10Measured.md.

    python docs/measure_nm_price_density_10.py

Run from the repo root. Uses tests/test_nm_price_density_10.py's synthetic
frame and mutants; the real-data reachability count comes from the Gate E
run recorded in docs/gate_e_ledger.csv (run `is186-nm_price_density_10-dc9aa7c9`),
not from this script.
"""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.getcwd())
import tests.test_nm_price_density_10 as T  # noqa: E402

nm_price_density_10 = T.nm_price_density_10


def gate_a():
    print("== Gate A: hand-derived window (H=[10,12,11,9], L=[8,9,7,8], length=2) ==")
    high = T.pd.Series([10.0, 12.0, 11.0, 9.0])
    low = T.pd.Series([8.0, 9.0, 7.0, 8.0])
    out = nm_price_density_10(high, low, length=2)
    print(f"  bar1={float(out.iloc[1])!r} (expected 1.25)")
    print(f"  bar2={float(out.iloc[2])!r} (expected 1.4)")
    print(f"  bar3={float(out.iloc[3])!r} (expected 1.25)")

    print("== Gate A: counterexample, ratio below 1.0 (H=[5,1], L=[4,1], length=2) ==")
    out = nm_price_density_10(T.pd.Series([5.0, 1.0]), T.pd.Series([4.0, 1.0]), length=2)
    print(f"  bar1={float(out.iloc[1])!r} (expected 0.25)")

    print("== Gate A: independent scalar-loop cross-check (400 bars, length=50) ==")
    high, low = T.HIGH.iloc[:400], T.LOW.iloc[:400]
    length = 50
    port = nm_price_density_10(high, low, length=length)
    h = [float(v) for v in high.to_numpy()]
    l = [float(v) for v in low.to_numpy()]
    expected = [float("nan")] * len(h)
    for t in range(length - 1, len(h)):
        win_h = h[t - length + 1:t + 1]
        win_l = l[t - length + 1:t + 1]
        numerator = sum(hi - lo for hi, lo in zip(win_h, win_l))
        denom = max(win_h) - min(win_l)
        if denom == 0:
            continue
        expected[t] = numerator / denom
    oracle = T.pd.Series(expected, index=high.index)
    m = port.notna()
    max_diff = float((port[m] - oracle[m]).abs().max())
    print(f"  {int(m.sum())} defined bars of {len(port)}; "
          f"NaN masks equal {(port.isna() == oracle.isna()).all()}; "
          f"max |diff| vs independent loop: {max_diff:.3e}")


def min_length():
    print("== MIN_LENGTH: 1-bar window forced to {1.0}, 2-bar window informative ==")
    rng = np.random.default_rng(0)
    one = set()
    for _ in range(3000):
        low = rng.uniform(1.0, 100.0)
        high = low + rng.uniform(0.1, 50.0)
        one.add(round(T._density([high], [low]), 9))
    print(f"  length=1, 3000 draws: distinct values {sorted(one)}")
    rng = np.random.default_rng(1)
    two = set()
    for _ in range(3000):
        lows = rng.uniform(1.0, 100.0, 2)
        highs = lows + rng.uniform(0.1, 50.0, 2)
        val = T._density(list(highs), list(lows))
        if np.isfinite(val):
            two.add(round(val, 6))
    print(f"  length=2, 3000 draws: {len(two)} distinct values")


def reachability():
    print("== Gate C: reachability on a 1,500-bar synthetic frame (length=10) ==")
    s = T.base()
    fired = s.dropna()
    print(f"  fires {len(fired)} of {len(s)} (warm-up {len(s) - len(fired)}); "
          f"min {fired.min():.6f}, max {fired.max():.6f}, distinct values {fired.nunique()}")


def scale_tolerance():
    print("== Gate D: price-scale invariance (x8/x64 bit-identical, x10/x3.7 tolerance) ==")
    base = T.base()
    for k in (8.0, 64.0, 10.0, 3.7):
        scaled = nm_price_density_10(T.HIGH * k, T.LOW * k)
        m = base.notna()
        exact_mismatches = int((base[m] != scaled[m]).sum())
        diff = (base[m] - scaled[m]).abs()
        print(f"  x{k}: NaN masks equal {(base.isna() == scaled.isna()).all()}; "
              f"exact mismatches on {int(m.sum())} co-finite cells: {exact_mismatches}; "
              f"max abs diff {diff.max():.3e}")


def causality_sweep():
    print("== Gate B: future-splice sweep + mutants, 1,500-bar frame ==")
    real_leaks = T._leak_offsets(nm_price_density_10, T.HIGH, T.LOW)
    print(f"  swept {len(T.OFFSETS)} offsets, real module leaked at {len(real_leaks)}")
    for name in sorted(T.MUTANTS):
        mod = T._load_mutant(*T.MUTANTS[name])
        hits = T._leak_offsets(mod.nm_price_density_10, T.HIGH, T.LOW)
        print(f"    mutant {name}: leaked at {len(hits)} of {len(T.OFFSETS)}")


def module_sha1():
    import importlib.util
    spec = importlib.util.spec_from_file_location("gate_e_ledger", "docs/gate_e_ledger.py")
    gl = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gl)
    path = gl.module_path("pandas_ta.volatility.nm_price_density_10")
    print(f"== module_sha1 (LF-normalised, for docs/gate_e_ledger.csv) == {gl.lf_sha1(path)}")


if __name__ == "__main__":
    gate_a()
    min_length()
    reachability()
    scale_tolerance()
    causality_sweep()
    module_sha1()
    print("python", sys.version.split()[0], "pandas", pd.__version__, "numpy", np.__version__)
