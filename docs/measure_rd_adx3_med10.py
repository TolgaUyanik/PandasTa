# -*- coding: utf-8 -*-
"""Reproduce the numbers in docs/RdAdx3Med10Measured.md.

    python docs/measure_rd_adx3_med10.py

Run from the repo root. Uses tests/test_rd_adx3_med10.py's synthetic
generators; no real-data cache is available in this worktree, so Gate C here
is synthetic-only -- the receipt session adds the Gate E run's real-data
reachability count.
"""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.getcwd())
import tests.test_rd_adx3_med10 as T  # noqa: E402

rd_adx3_med10 = T.rd_adx3_med10
adx = T.adx


def gate_a():
    print("== Gate A: independent recompute (adx() + numpy.median), 700 bars ==")
    high, low, close = T._walk(700)
    length = 10
    adx3 = adx(high=high, low=low, close=close, length=3)["ADX_3"].to_numpy()

    ref = np.full(len(adx3), np.nan)
    for t in range(length - 1, len(adx3)):
        window = adx3[t - length + 1:t + 1]
        if np.isnan(window).any():
            continue
        ref[t] = np.median(window)

    out = rd_adx3_med10(high, low, close, adx_length=3, length=length)
    nan_match = (np.isnan(ref) == out.isna().values).all()
    m = ~np.isnan(ref)
    max_diff = np.nanmax(np.abs(out.values[m] - ref[m]))
    print(f"  {int(m.sum())} compared bars; NaN masks match: {nan_match}; max|diff| = {max_diff:.3e}")

    print("== Gate A: length=1 is the identity on ADX3 ==")
    out1 = rd_adx3_med10(high, low, close, adx_length=3, length=1)
    adx3_s = adx(high=high, low=low, close=close, length=3)["ADX_3"]
    mm = out1.notna() & adx3_s.notna()
    print(f"  {int(mm.sum())} compared bars; all equal: {bool((out1[mm].to_numpy() == adx3_s[mm].to_numpy()).all())}")


def reachability():
    print("== Gate C: reachability on a 900-bar synthetic frame (seed 11) ==")
    high, low, close = T._walk(900)
    out = rd_adx3_med10(high, low, close)
    fired = out.dropna()
    print(f"  fires {len(fired)} of {len(high)} (warm-up {len(high) - len(fired)}); "
          f"distinct values {fired.nunique()}; range [{fired.min():.6f}, {fired.max():.6f}]")

    print("== Gate C: reachability across 10 independent 900-bar seeds ==")
    for seed in range(10):
        high, low, close = T._walk(900, seed=seed + 100)
        out = rd_adx3_med10(high, low, close)
        fired = out.dropna()
        print(f"  seed {seed + 100}: {len(fired)} non-NaN of {len(high)}, "
              f"{fired.nunique()} distinct values")


def scale_tolerance():
    print("== Gate D: price-scale invariance of high/low/close together (x8/x64/x10/x3.7) ==")
    high, low, close = T._walk(900)
    base = rd_adx3_med10(high, low, close)
    base_adx3 = adx(high=high, low=low, close=close, length=3)["ADX_3"]
    for k in (8.0, 64.0, 10.0, 3.7):
        scaled = rd_adx3_med10(high * k, low * k, close * k)
        scaled_adx3 = adx(high=high * k, low=low * k, close=close * k, length=3)["ADX_3"]
        m = base.notna()
        max_diff = (base[m] - scaled[m]).abs().max()
        ma = base_adx3.notna()
        max_diff_adx3 = (base_adx3[ma] - scaled_adx3[ma]).abs().max()
        print(f"  x{k}: NaN masks equal {(base.isna() == scaled.isna()).all()}; "
              f"RD_ADX3_MED10 max|diff| on {int(m.sum())} co-finite cells: {max_diff:.3e}; "
              f"ADX_3 max|diff|: {max_diff_adx3:.3e}")

    print("== Gate D: 0 < fires < n and non-constant ==")
    fired = base.dropna()
    print(f"  fires {len(fired)} of {len(high)}; distinct values {fired.nunique()}")


def causality_sweep():
    print("== Gate B: future-perturbation sweep, 9 offsets ==")
    real_leaks = T._leaks(rd_adx3_med10)
    mod = T._load_mutant()
    mutant_leaks = T._leaks(mod.rd_adx3_med10)
    print(f"  real module leaked at {real_leaks} of {len(T.OFFSETS)}; "
          f"mutant leaked at {mutant_leaks} of {len(T.OFFSETS)}")


def module_sha1():
    import importlib.util
    spec = importlib.util.spec_from_file_location("gate_e_ledger", "docs/gate_e_ledger.py")
    gl = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gl)
    path = gl.module_path("pandas_ta.trend.rd_adx3_med10")
    print(f"== module_sha1 (LF-normalised, for docs/gate_e_ledger.csv) == {gl.lf_sha1(path)}")


if __name__ == "__main__":
    gate_a()
    reachability()
    scale_tolerance()
    causality_sweep()
    module_sha1()
    print("python", sys.version.split()[0], "pandas", pd.__version__, "numpy", np.__version__)
