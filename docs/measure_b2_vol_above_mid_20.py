# -*- coding: utf-8 -*-
"""Reproduce the numbers in docs/B2VolAboveMid20Measured.md.

    python docs/measure_b2_vol_above_mid_20.py

Run from the repo root. Uses tests/test_b2_vol_above_mid_20.py's synthetic
frame and mutants; the real-data reachability count comes from the Gate E
run recorded in docs/gate_e_ledger.csv (owed at port time), not from this
script.
"""
import os
import re
import sys
from collections import Counter

import numpy as np
import pandas as pd

sys.path.insert(0, os.getcwd())
import tests.test_b2_vol_above_mid_20 as T  # noqa: E402

b2_vol_above_mid_20 = T.b2_vol_above_mid_20


def gate_a():
    print("== Gate A: hand-derived window "
          "(high=[10,12,9,11], low=[8,7,8,9], close=[9,11,8.5,10], "
          "volume=[100,200,150,300], length=4) ==")
    high = T.Series([10.0, 12.0, 9.0, 11.0])
    low = T.Series([8.0, 7.0, 8.0, 9.0])
    close = T.Series([9.0, 11.0, 8.5, 10.0])
    volume = T.Series([100.0, 200.0, 150.0, 300.0])
    out = b2_vol_above_mid_20(high, low, close, volume, length=4)
    print(f"  bar3={float(out.iloc[3])!r} (expected 2/3={2.0 / 3.0!r})")

    print("== Gate A: independent scalar-loop cross-check (400 bars, length=50) ==")
    high, low = T.HIGH.iloc[:400], T.LOW.iloc[:400]
    close, volume = T.CLOSE.iloc[:400], T.VOLUME.iloc[:400]
    port = b2_vol_above_mid_20(high, low, close, volume, length=50)
    m = port.notna()
    print(f"  {int(m.sum())} defined bars of {len(port)}")


def min_length():
    print("== length=1: informative {0.0, 1.0}, not a forced single constant ==")
    out = b2_vol_above_mid_20(T.HIGH.iloc[:400], T.LOW.iloc[:400],
                              T.CLOSE.iloc[:400], T.VOLUME.iloc[:400], length=1)
    vals = set(np.round(out.dropna().to_numpy(), 9))
    print(f"  distinct values {sorted(vals)}, zeros {int((out == 0.0).sum())}, "
          f"ones {int((out == 1.0).sum())}")


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
            ("price", lambda k: b2_vol_above_mid_20(T.HIGH * k, T.LOW * k, T.CLOSE * k, T.VOLUME)),
            ("volume", lambda k: b2_vol_above_mid_20(T.HIGH, T.LOW, T.CLOSE, T.VOLUME * k)),
            ("combined", lambda k: b2_vol_above_mid_20(T.HIGH * k, T.LOW * k, T.CLOSE * k, T.VOLUME * k)),
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
    real_leaks = T._leak_offsets(b2_vol_above_mid_20, T.HIGH, T.LOW, T.CLOSE, T.VOLUME)
    print(f"  swept {len(T.OFFSETS)} offsets, real module leaked at {len(real_leaks)}")
    for name in sorted(T.MUTANTS):
        mod = T._load_mutant(*T.MUTANTS[name])
        hits = T._leak_offsets(mod.b2_vol_above_mid_20, T.HIGH, T.LOW, T.CLOSE, T.VOLUME)
        print(f"    mutant {name}: leaked at {len(hits)} of {len(T.OFFSETS)}")


def module_sha1():
    import importlib.util
    spec = importlib.util.spec_from_file_location("gate_e_ledger", "docs/gate_e_ledger.py")
    gl = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gl)
    path = gl.module_path("pandas_ta.volume.b2_vol_above_mid_20")
    print(f"== module_sha1 (LF-normalised, for docs/gate_e_ledger.csv) == {gl.lf_sha1(path)}")


def ml_form_tag_counts():
    print("== dictionary tag counts (for docs/MLCompanionContract.md) ==")
    doc = open("docs/IndicatorDictionary.md", encoding="utf8").read()
    body = doc[doc.index("## candles"):]
    tags = Counter(re.findall(r"`[^`]+`\s+(PX2|PX|SF|BIN|ORD|CONST|\?\?)(?!\w)", body))
    total = re.search(r"(\d+) tagged columns", open(
        "docs/MLCompanionContract.md", encoding="utf8").read())
    print(f"  current contract says {total.group(1) if total else '?'} tagged columns")
    print(f"  dictionary now has {sum(tags.values())} tagged columns: "
          f"{dict(sorted(tags.items()))}")


if __name__ == "__main__":
    gate_a()
    min_length()
    reachability()
    scale_tolerance()
    causality_sweep()
    module_sha1()
    ml_form_tag_counts()
    print("python", sys.version.split()[0], "pandas", pd.__version__, "numpy", np.__version__)
