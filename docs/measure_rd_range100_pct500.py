# -*- coding: utf-8 -*-
"""Reproduce the numbers in docs/RdRange100Pct500Measured.md.

    python docs/measure_rd_range100_pct500.py

Run from the repo root. Uses tests/test_rd_range100_pct500.py's synthetic
generators; no real-data cache is available in this worktree, so Gate C here
is synthetic-only -- the receipt session adds the Gate E run's real-data
reachability count.
"""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.getcwd())
import tests.test_rd_range100_pct500 as T  # noqa: E402

rd_range100_pct500 = T.rd_range100_pct500


def gate_a():
    print("== Gate A: independent per-window loop, 700 bars, length=100 pctlen=500 ==")
    high, low = T._walk(700)
    length, pctlen = 100, 500
    h, l = high.values, low.values

    r_ref = np.full(len(h), np.nan)
    for t in range(length - 1, len(h)):
        hh = h[t - length + 1:t + 1].max()
        ll = l[t - length + 1:t + 1].min()
        r_ref[t] = (hh - ll) / ll

    rank_ref = np.full(len(h), np.nan)
    for t in range(pctlen - 1, len(h)):
        window = r_ref[t - pctlen + 1:t + 1]
        if np.isnan(window).any():
            continue
        cur = window[-1]
        rank_ref[t] = (window <= cur).sum() / pctlen

    out = rd_range100_pct500(high, low, length=length, pctlen=pctlen)
    nan_match = (np.isnan(rank_ref) == out.isna().values).all()
    m = ~np.isnan(rank_ref)
    max_diff = np.nanmax(np.abs(out.values[m] - rank_ref[m]))
    print(f"  {int(m.sum())} compared bars; NaN masks match: {nan_match}; max|diff| = {max_diff:.3e}")

    print("== Gate A: constant-range frame reads exactly 1.0 (method='max' tie rule) ==")
    n = 650
    low_c = pd.Series(np.full(n, 100.0))
    high_c = pd.Series(np.full(n, 110.0))
    out_c = rd_range100_pct500(high_c, low_c, length=100, pctlen=500).dropna()
    print(f"  {len(out_c)} non-NaN bars, all == 1.0: {bool((out_c == 1.0).all())}")


def reachability():
    print("== Gate C: reachability on a 1,200-bar synthetic frame (seed 11/21) ==")
    high, low = T._walk(1200)
    out = rd_range100_pct500(high, low)
    fired = out.dropna()
    print(f"  fires {len(fired)} of {len(high)} (warm-up {len(high) - len(fired)}); "
          f"distinct values {fired.nunique()}; range [{fired.min():.6f}, {fired.max():.6f}]")

    print("== Gate C: reachability across 10 independent 1,200-bar seeds ==")
    for seed in range(10):
        high, low = T._walk(1200, seed=seed + 100)
        out = rd_range100_pct500(high, low)
        fired = out.dropna()
        print(f"  seed {seed + 100}: {len(fired)} non-NaN of {len(high)}, "
              f"{fired.nunique()} distinct values")


def scale_tolerance():
    print("== Gate D: price-scale invariance of high&low together (x8/x64/x10/x3.7) ==")
    high, low = T._walk(1200)
    base = rd_range100_pct500(high, low)
    for k in (8.0, 64.0, 10.0, 3.7):
        scaled = rd_range100_pct500(high * k, low * k)
        m = base.notna()
        max_diff = (base[m] - scaled[m]).abs().max()
        print(f"  x{k}: NaN masks equal {(base.isna() == scaled.isna()).all()}; "
              f"max|diff| on {int(m.sum())} co-finite cells: {max_diff:.3e}")

    print("== Gate D: 0 < fires < n and non-constant ==")
    fired = base.dropna()
    print(f"  fires {len(fired)} of {len(high)}; distinct values {fired.nunique()}")

    print("== Gate D: a zero low divides to NaN, not inf ==")
    low_z = low.copy()
    low_z.iloc[200] = 0.0
    out_z = rd_range100_pct500(high, low_z)
    n_inf = int(np.isinf(out_z.to_numpy(dtype=float)).sum())
    print(f"  infinities in output: {n_inf}")


def causality_sweep():
    print("== Gate B: future-perturbation sweep, 8 curated offsets ==")
    real_leaks = T._leaks(rd_range100_pct500)
    mod = T._load_mutant()
    mutant_leaks = T._leaks(mod.rd_range100_pct500)
    print(f"  real module leaked at {real_leaks} of {len(T.OFFSETS)}; "
          f"mutant leaked at {mutant_leaks} of {len(T.OFFSETS)}")


def module_sha1():
    import importlib.util
    spec = importlib.util.spec_from_file_location("gate_e_ledger", "docs/gate_e_ledger.py")
    gl = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gl)
    path = gl.module_path("pandas_ta.volatility.rd_range100_pct500")
    print(f"== module_sha1 (LF-normalised, for docs/gate_e_ledger.csv) == {gl.lf_sha1(path)}")


if __name__ == "__main__":
    gate_a()
    reachability()
    scale_tolerance()
    causality_sweep()
    module_sha1()
    print("python", sys.version.split()[0], "pandas", pd.__version__, "numpy", np.__version__)
