# -*- coding: utf-8 -*-
"""Reproduce the numbers in docs/RdVwio10Measured.md.

    python docs/measure_rd_vwio_10.py

Run from the repo root. Uses tests/test_rd_vwio_10.py's synthetic
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
import tests.test_rd_vwio_10 as T  # noqa: E402

rd_vwio_10 = T.rd_vwio_10


def gate_a():
    print("== Gate A: all-buy bars reads +1.0 ==")
    n = 60
    close = Series(100.0 + np.arange(n, dtype=float))
    open_ = close - 1.0
    volume = Series(np.full(n, 500.0))
    out = rd_vwio_10(open_, close, volume, length=10).dropna()
    print(f"  {len(out)} non-NaN bars, max|ratio - 1| = {(out - 1.0).abs().max():.3e}")

    print("== Gate A: all-sell bars reads -1.0 ==")
    open_ = close + 1.0
    out = rd_vwio_10(open_, close, volume, length=10).dropna()
    print(f"  {len(out)} non-NaN bars, max|ratio + 1| = {(out + 1.0).abs().max():.3e}")

    print("== Gate A: independent per-bar loop, 400 bars, length 10 ==")
    open_, close, volume = T._frame(400)
    n = 10
    o, c, v = open_.values, close.values, volume.values

    def ema_ref(x, length):
        out = np.full(len(x), np.nan)
        out[length - 1] = np.mean(x[:length])
        alpha = 2.0 / (length + 1.0)
        for i in range(length, len(x)):
            out[i] = alpha * x[i] + (1 - alpha) * out[i - 1]
        return out

    imbalance = np.where(c > o, v, np.where(c < o, -v, 0.0))
    ref = ema_ref(imbalance, n) / ema_ref(v, n)
    out = rd_vwio_10(open_, close, volume, length=n)
    nan_match = (np.isnan(ref) == out.isna().values).all()
    max_diff = np.nanmax(np.abs(out.values - ref))
    print(f"  NaN masks match: {nan_match}; max|diff| = {max_diff:.3e}")

    print("== Gate A: screen prototype's plain ewm reading, after bar 100 ==")
    open_, close, volume = T._frame(500)
    buys = volume.where(close > open_, 0.0)
    sells = volume.where(close < open_, 0.0)
    prototype = ((buys - sells).ewm(span=n, adjust=False).mean()
                 / volume.ewm(span=n, adjust=False).mean())
    out = rd_vwio_10(open_, close, volume, length=n)
    tail = (out.index >= 100) & out.notna() & prototype.notna()
    diff = (out[tail] - prototype[tail]).abs()
    print(f"  {int(tail.sum())} compared bars, max|diff| = {diff.max():.3e}")


def reachability():
    print("== Gate C: reachability on a 1,200-bar synthetic frame (seeds 11/31/21) ==")
    open_, close, volume = T._frame()
    out = rd_vwio_10(open_, close, volume)
    fired = out.dropna()
    print(f"  fires {len(fired)} of {len(close)} (warm-up {len(close) - len(fired)}); "
          f"non-zero {int((fired != 0).sum())}; distinct values {fired.nunique()}")

    print("== Gate C: reachability across 10 independent 600-bar seeds ==")
    for seed in range(10):
        open_, close, volume = T._frame(600, cseed=seed + 100, oseed=seed + 300, vseed=seed + 200)
        out = rd_vwio_10(open_, close, volume)
        fired = out.dropna()
        print(f"  seed {seed + 100}: {len(fired)} non-NaN of {len(close)}, "
              f"{fired.nunique()} distinct values")


def scale_tolerance():
    print("== Gate D: price-scale invariance (x8/x64/x10/x3.7), open+close together ==")
    open_, close, volume = T._frame()
    base = rd_vwio_10(open_, close, volume)
    for k in (8.0, 64.0, 10.0, 3.7):
        scaled = rd_vwio_10(open_ * k, close * k, volume)
        m = base.notna()
        max_diff = (base[m] - scaled[m]).abs().max()
        print(f"  price x{k}: NaN masks equal {(base.isna() == scaled.isna()).all()}; "
              f"max|diff| on {int(m.sum())} co-finite cells: {max_diff:.3e}")

    print("== Gate D: volume-scale invariance (x8/x64/x10/x3.7) ==")
    for k in (8.0, 64.0, 10.0, 3.7):
        scaled = rd_vwio_10(open_, close, volume * k)
        m = base.notna()
        max_diff = (base[m] - scaled[m]).abs().max()
        print(f"  volume x{k}: NaN masks equal {(base.isna() == scaled.isna()).all()}; "
              f"max|diff| on {int(m.sum())} co-finite cells: {max_diff:.3e}")


def causality_sweep():
    print("== Gate B: future-perturbation sweep, 16 offsets ==")
    real_leaks = T._leaks(rd_vwio_10)
    mod = T._load_mutant()
    mutant_leaks = T._leaks(mod.rd_vwio_10)
    print(f"  real module leaked at {real_leaks} of {len(T.OFFSETS)}; "
          f"mutant leaked at {mutant_leaks} of {len(T.OFFSETS)}")


def module_sha1():
    import importlib.util
    spec = importlib.util.spec_from_file_location("gate_e_ledger", "docs/gate_e_ledger.py")
    gl = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gl)
    path = gl.module_path("pandas_ta.volume.rd_vwio_10")
    print(f"== module_sha1 (LF-normalised, for docs/gate_e_ledger.csv) == {gl.lf_sha1(path)}")


if __name__ == "__main__":
    gate_a()
    reachability()
    scale_tolerance()
    causality_sweep()
    module_sha1()
    print("python", sys.version.split()[0], "pandas", pd.__version__, "numpy", np.__version__)
