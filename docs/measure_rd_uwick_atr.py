# -*- coding: utf-8 -*-
"""Reproduce the numbers in docs/RdUwickAtrMeasured.md.

    python docs/measure_rd_uwick_atr.py

Run from the repo root. Uses tests/test_rd_uwick_atr.py's synthetic OHLC
generator; no real-data cache is available in this worktree, so Gate C here
is synthetic-only -- the receipt session adds the Gate E run's real-data
reachability count.
"""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.getcwd())
import tests.test_rd_uwick_atr as T  # noqa: E402

rd_uwick_atr = T.rd_uwick_atr


def gate_a():
    print("== Gate A: hand-derived fixture (length=2) ==")
    df = T._ohlc(T._hand_rows())
    out = rd_uwick_atr(df.open, df.high, df.low, df.close, length=2)
    print(f"  warm-up NaN bars {int(out.iloc[:2].isna().sum())}, bar2 = {out.iloc[2]}")

    print("== Gate A: independent per-bar loop (TR + Wilder recursion), 1,600 bars, length 5 ==")
    df = T._frame()
    length = 5
    o, h, l, c = (df[k].to_numpy(dtype=float) for k in ("open", "high", "low", "close"))
    n = len(c)
    upper_wick = h - np.maximum(o, c)
    atr_ref = T._independent_atr5(h, l, c, length=length)
    ref = np.full(n, np.nan)
    m = ~np.isnan(atr_ref) & (atr_ref != 0)
    ref[m] = upper_wick[m] / atr_ref[m]
    out = rd_uwick_atr(df.open, df.high, df.low, df.close, length=length)
    nan_match = (np.isnan(ref) == out.isna().values).all()
    mm = ~np.isnan(ref)
    max_diff = np.max(np.abs(out.values[mm] - ref[mm]))
    print(f"  NaN masks match: {nan_match}; {int(mm.sum())} compared bars, "
          f"max|diff| = {max_diff:.3e}")


def reachability():
    print("== Gate C: reachability on a 1,600-bar synthetic frame (seed 4) ==")
    df = T._frame(seed=4)
    out = rd_uwick_atr(df.open, df.high, df.low, df.close)
    fired = out.dropna()
    print(f"  fires {len(fired)} of {len(out)} (warm-up {len(out) - len(fired)}); "
          f"min {fired.min():.4f}, max {fired.max():.4f}, "
          f"distinct values {fired.nunique()}")

    print("== Gate C: reachability across 10 independent 600-bar seeds ==")
    for seed in range(10):
        df = T._frame(n=600, seed=seed + 100)
        out = rd_uwick_atr(df.open, df.high, df.low, df.close)
        fired = out.dropna()
        print(f"  seed {seed + 100}: fires {len(fired)}, "
              f"min {fired.min():.4f}, max {fired.max():.4f}")

    print("== Gate C: flat run reads 0.0, not NaN, past warm-up ==")
    rows = [(100.0, 100.0, 100.0, 100.0)] * 8
    flat = T._ohlc(rows)
    out = rd_uwick_atr(flat.open, flat.high, flat.low, flat.close, length=3)
    print(f"  warm-up NaN bars {int(out.iloc[:3].isna().sum())}, "
          f"values past warm-up: {out.iloc[3:].tolist()}")


def scale_tolerance():
    print("== Gate D: price-scale invariance (x8/x64/x10/x3.7) ==")
    df = T._frame(seed=4)
    base = rd_uwick_atr(df.open, df.high, df.low, df.close)
    for k in (8.0, 64.0, 10.0, 3.7):
        scaled = rd_uwick_atr(df.open * k, df.high * k, df.low * k, df.close * k)
        m = base.notna()
        max_diff = (base[m] - scaled[m]).abs().max()
        mismatches = int((base[m] != scaled[m]).sum())
        print(f"  x{k}: NaN masks equal {(base.isna() == scaled.isna()).all()}; "
              f"mismatches on {int(m.sum())} co-finite cells: {mismatches}; "
              f"max|diff| = {max_diff:.3e}")


def causality_sweep():
    print("== Gate B: future-splice sweep, 1,600-bar frames (seeds 1 vs 2) ==")
    mod = T._load_mutant()
    a, b = T._frame(1600, seed=1), T._frame(1600, seed=2)
    real_leaks = T._leaks(rd_uwick_atr, a, b)
    mut = lambda o, h, l, c: mod.rd_uwick_atr(o, h, l, c)  # noqa: E731
    mutant_leaks = T._leaks(mut, a, b)
    print(f"  swept {len(T.OFFSETS)} J values: real module leaked at {real_leaks}, "
          f"mutant leaked at {mutant_leaks}")


def module_sha1():
    import importlib.util
    spec = importlib.util.spec_from_file_location("gate_e_ledger", "docs/gate_e_ledger.py")
    gl = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gl)
    path = gl.module_path("pandas_ta.candles.rd_uwick_atr")
    print(f"== module_sha1 (LF-normalised, for docs/gate_e_ledger.csv) == {gl.lf_sha1(path)}")


if __name__ == "__main__":
    gate_a()
    reachability()
    scale_tolerance()
    causality_sweep()
    module_sha1()
    print("python", sys.version.split()[0], "pandas", pd.__version__, "numpy", np.__version__)
