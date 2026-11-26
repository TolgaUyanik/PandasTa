# -*- coding: utf-8 -*-
"""Reproduce the numbers in docs/RdObvDev5Measured.md.

    python docs/measure_rd_obv_dev5.py

Run from the repo root. Uses tests/test_rd_obv_dev5.py's synthetic
generators; no real-data cache is available in this worktree, so Gate C here
is synthetic-only -- the receipt session adds the Gate E run's real-data
reachability count.
"""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.getcwd())
import tests.test_rd_obv_dev5 as T  # noqa: E402

rd_obv_dev5 = T.rd_obv_dev5
obv = T.obv


def gate_a():
    print("== Gate A: independent recompute (obv() + manual NumPy SMAs), 700 bars ==")
    close, volume = T._walk(700)
    length, vol_length = 5, 20
    obv_series = obv(close, volume).to_numpy()
    obv_sma = T._manual_sma(obv_series, length)
    avg_volume = T._manual_sma(volume.to_numpy(), vol_length)
    ref = (obv_series - obv_sma) / avg_volume

    out = rd_obv_dev5(close, volume, length=length, vol_length=vol_length)
    nan_match = (np.isnan(ref) == out.isna().values).all()
    m = ~np.isnan(ref)
    max_diff = np.nanmax(np.abs(out.values[m] - ref[m]))
    print(f"  {int(m.sum())} compared bars; NaN masks match: {nan_match}; max|diff| = {max_diff:.3e}")

    print("== Gate A: length=1 makes the numerator identically 0 ==")
    out1 = rd_obv_dev5(close, volume, length=1, vol_length=20)
    fired = out1.dropna()
    print(f"  {len(fired)} fired bars; all exactly 0.0: {bool((fired.to_numpy() == 0.0).all())}")


def reachability():
    print("== Gate C: reachability on a 900-bar synthetic frame (seed 11) ==")
    close, volume = T._walk(900)
    out = rd_obv_dev5(close, volume)
    fired = out.dropna()
    print(f"  fires {len(fired)} of {len(close)} (warm-up {len(close) - len(fired)}); "
          f"distinct values {fired.nunique()}; range [{fired.min():.6f}, {fired.max():.6f}]")

    print("== Gate C: reachability across 10 independent 900-bar seeds ==")
    for seed in range(10):
        close, volume = T._walk(900, seed=seed + 100)
        out = rd_obv_dev5(close, volume)
        fired = out.dropna()
        print(f"  seed {seed + 100}: {len(fired)} non-NaN of {len(close)}, "
              f"{fired.nunique()} distinct values")


def scale_tolerance():
    print("== Gate D: price-only rescale of close (x8/x64/x10/x3.7) ==")
    close, volume = T._walk(900)
    base = rd_obv_dev5(close, volume)
    for k in (8.0, 64.0, 10.0, 3.7):
        scaled = rd_obv_dev5(close * k, volume)
        m = base.notna()
        max_diff = (base[m] - scaled[m]).abs().max()
        print(f"  x{k}: NaN masks equal {(base.isna() == scaled.isna()).all()}; "
              f"max|diff| on {int(m.sum())} co-finite cells: {max_diff:.3e}")

    print("== Gate D: volume-only rescale (x8/x64/x10/x3.7) ==")
    for k in (8.0, 64.0, 10.0, 3.7):
        scaled = rd_obv_dev5(close, volume * k)
        m = base.notna()
        max_diff = (base[m] - scaled[m]).abs().max()
        print(f"  x{k}: NaN masks equal {(base.isna() == scaled.isna()).all()}; "
              f"max|diff| on {int(m.sum())} co-finite cells: {max_diff:.3e}")

    print("== Gate D: 0 < fires < n and non-constant ==")
    fired = base.dropna()
    print(f"  fires {len(fired)} of {len(close)}; distinct values {fired.nunique()}")


def causality_sweep():
    print("== Gate B: future-perturbation sweep, 9 offsets ==")
    real_leaks = T._leaks(rd_obv_dev5)
    mod = T._load_mutant()
    mutant_leaks = T._leaks(mod.rd_obv_dev5)
    print(f"  real module leaked at {real_leaks} of {len(T.OFFSETS)}; "
          f"mutant leaked at {mutant_leaks} of {len(T.OFFSETS)}")


def module_sha1():
    import importlib.util
    spec = importlib.util.spec_from_file_location("gate_e_ledger", "docs/gate_e_ledger.py")
    gl = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gl)
    path = gl.module_path("pandas_ta.volume.rd_obv_dev5")
    print(f"== module_sha1 (LF-normalised, for docs/gate_e_ledger.csv) == {gl.lf_sha1(path)}")


if __name__ == "__main__":
    gate_a()
    reachability()
    scale_tolerance()
    causality_sweep()
    module_sha1()
    print("python", sys.version.split()[0], "pandas", pd.__version__, "numpy", np.__version__)
