# -*- coding: utf-8 -*-
"""Reproduce the numbers in docs/RdCorrCObv20Measured.md.

    python docs/measure_rd_corr_c_obv_20.py

Run from the repo root. Uses tests/test_rd_corr_c_obv_20.py's synthetic
generators; no real-data cache is available in this worktree, so Gate C here
is synthetic-only -- the receipt session adds the Gate E run's real-data
reachability count.
"""
import os
import sys

import numpy as np
import pandas as pd
from pandas import Series

sys.path.insert(0, os.getcwd())
import tests.test_rd_corr_c_obv_20 as T  # noqa: E402

rd_corr_c_obv_20 = T.rd_corr_c_obv_20
obv = T.obv


def gate_a():
    print("== Gate A: monotone close + constant volume reads +1.0 ==")
    n = 60
    close = Series(100.0 + np.arange(n, dtype=float))
    volume = Series(np.full(n, 500.0))
    out = rd_corr_c_obv_20(close, volume, length=10).dropna()
    print(f"  {len(out)} non-NaN bars, max|corr - 1| = {(out - 1.0).abs().max():.3e}")

    print("== Gate A: independent np.corrcoef loop, 400 bars, length 20 ==")
    close = T._walk(400)
    volume = T._vol(400)
    n = 20
    c, v = close.values, volume.values
    signed_vol = np.empty(len(c))
    signed_vol[0] = v[0]
    for i in range(1, len(c)):
        signed_vol[i] = v[i] if c[i] >= c[i - 1] else -v[i]
    obv_ref = np.cumsum(signed_vol)
    ref = np.full(len(c), np.nan)
    for t in range(n - 1, len(c)):
        ref[t] = np.corrcoef(c[t - n + 1:t + 1], obv_ref[t - n + 1:t + 1])[0, 1]
    out = rd_corr_c_obv_20(close, volume, length=n)
    nan_match = (np.isnan(ref) == out.isna().values).all()
    max_diff = np.nanmax(np.abs(out.values - ref))
    print(f"  NaN masks match: {nan_match}; max|diff| = {max_diff:.3e}")

    print("== Gate A: z-score equivalence (issue's own parenthetical) ==")
    close = T._walk(300)
    volume = T._vol(300)
    obv_series = obv(close, volume)
    z_close = (close - close.mean()) / close.std()
    z_obv = (obv_series - obv_series.mean()) / obv_series.std()
    zscored_corr = z_close.rolling(n, min_periods=n).corr(z_obv)
    out = rd_corr_c_obv_20(close, volume, length=n)
    diff = (out - zscored_corr).dropna()
    print(f"  {len(diff)} compared bars, max|diff| = {diff.abs().max():.3e}")


def reachability():
    print("== Gate C: reachability on a 1,200-bar synthetic frame (seed 11/21) ==")
    close, volume = T._walk(), T._vol()
    out = rd_corr_c_obv_20(close, volume)
    fired = out.dropna()
    print(f"  fires {len(fired)} of {len(close)} (warm-up {len(close) - len(fired)}); "
          f"non-zero {int((fired != 0).sum())}; distinct values {fired.nunique()}")

    print("== Gate C: reachability across 10 independent 600-bar seeds ==")
    for seed in range(10):
        close = T._walk(600, seed=seed + 100)
        volume = T._vol(600, seed=seed + 200)
        out = rd_corr_c_obv_20(close, volume)
        fired = out.dropna()
        print(f"  seed {seed + 100}: {len(fired)} non-NaN of {len(close)}, "
              f"{fired.nunique()} distinct values")


def scale_tolerance():
    print("== Gate D: price-scale invariance (x8/x64/x10/x3.7) ==")
    close, volume = T._walk(), T._vol()
    base = rd_corr_c_obv_20(close, volume)
    for k in (8.0, 64.0, 10.0, 3.7):
        scaled = rd_corr_c_obv_20(close * k, volume)
        m = base.notna()
        max_diff = (base[m] - scaled[m]).abs().max()
        print(f"  price x{k}: NaN masks equal {(base.isna() == scaled.isna()).all()}; "
              f"max|diff| on {int(m.sum())} co-finite cells: {max_diff:.3e}")

    print("== Gate D: volume-scale invariance (x8/x64/x10/x3.7) ==")
    for k in (8.0, 64.0, 10.0, 3.7):
        scaled = rd_corr_c_obv_20(close, volume * k)
        m = base.notna()
        max_diff = (base[m] - scaled[m]).abs().max()
        print(f"  volume x{k}: NaN masks equal {(base.isna() == scaled.isna()).all()}; "
              f"max|diff| on {int(m.sum())} co-finite cells: {max_diff:.3e}")


def causality_sweep():
    print("== Gate B: future-perturbation sweep, 16 offsets ==")
    real_leaks = T._leaks(rd_corr_c_obv_20)
    mod = T._load_mutant()
    mutant_leaks = T._leaks(mod.rd_corr_c_obv_20)
    print(f"  real module leaked at {real_leaks} of {len(T.OFFSETS)}; "
          f"mutant leaked at {mutant_leaks} of {len(T.OFFSETS)}")


def module_sha1():
    import importlib.util
    spec = importlib.util.spec_from_file_location("gate_e_ledger", "docs/gate_e_ledger.py")
    gl = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gl)
    path = gl.module_path("pandas_ta.volume.rd_corr_c_obv_20")
    print(f"== module_sha1 (LF-normalised, for docs/gate_e_ledger.csv) == {gl.lf_sha1(path)}")


if __name__ == "__main__":
    gate_a()
    reachability()
    scale_tolerance()
    causality_sweep()
    module_sha1()
    print("python", sys.version.split()[0], "pandas", pd.__version__, "numpy", np.__version__)
