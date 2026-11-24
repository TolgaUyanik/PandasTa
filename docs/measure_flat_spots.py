# -*- coding: utf-8 -*-
"""Reproduce the numbers in docs/FlatSpotsMeasured.md.

    python docs/measure_flat_spots.py

Run from the repo root. Uses tests/test_flat_spots.py's generators and its
verbatim transcription of the prototype's `_flat_spots`.
"""
import os
import sys
import time
import tracemalloc

import numpy as np
import pandas as pd

sys.path.insert(0, os.getcwd())
import tests.test_flat_spots as T  # noqa: E402


def gate_a():
    print("== Gate A: vs the prototype's _flat_spots (verbatim), every bar ==")
    for name, mk in (("continuous, 300", lambda: T._continuous(300, 1)),
                      ("ticky, 300", lambda: T._ticky(300, 2)),
                      ("ticky, 300 seed 3", lambda: T._ticky(300, 3))):
        close = mk()
        for L in (20, 30, 100):
            ours = T.flat_spots(close, length=L).to_numpy()
            ref = T._oracle(close, L)
            m = ~np.isnan(ours) & ~np.isnan(ref)
            same = np.array_equal(ours[m], ref[m])
            masks_eq = np.array_equal(np.isnan(ours), np.isnan(ref))
            print(f"  {name} length {L}: bit-identical to oracle {same}; NaN masks equal {masks_eq}; "
                  f"{m.sum()} bars compared")


def semantics():
    print("== semantics: FLATSPOTS_100, 10 paths x 600 bars (500 values each) ==")
    rows = (("continuous", lambda s: T._continuous(600, s)), ("ticky (0.01 tick near 5)", lambda s: T._ticky(600, s)))
    print("| closes | pooled median | pooled mean | p90 | distinct values |")
    for name, mk in rows:
        v = np.concatenate([T.flat_spots(mk(500 + s)).dropna().to_numpy() for s in range(10)])
        print(f"| {name} | {np.median(v):.2f} | {v.mean():.3f} | {np.quantile(v, .9):.2f} | {len(np.unique(v))} |")


def scale_tolerance():
    print("== Gate D: price-scale tolerance (x10/x3.7, not powers of two) ==")
    close = T._ticky(seed=4)
    for k in (10.0, 3.7):
        base, scaled = T.flat_spots(close), T.flat_spots(close * k)
        d = (base - scaled).abs()
        print(f"  x{k}: max abs diff {d.max():.3e}, NaN masks equal {(base.isna() == scaled.isna()).all()}")


def reachability():
    print("== Gate C: synthetic reachability ==")
    out = T.flat_spots(T._ticky(seed=4))
    print(f"  600 bars, 100 warm-up: {out.notna().sum()} fire, {out.dropna().nunique()} distinct values, "
          f"range [{out.min():.0f}, {out.max():.0f}]")


def cost():
    print("== cost (machine-dependent) ==")
    for n in (5000, 20000, 200000):
        close = T._ticky(n, 5)
        for L in (100, 252):
            runs = [_timed(close, L) for _ in range(5)]  # tracemalloc off
            tracemalloc.start()
            T.flat_spots(close, length=L)
            peak = tracemalloc.get_traced_memory()[1]
            tracemalloc.stop()
            print(f"  n={n} length={L}: 5 runs {min(runs):.3f} .. {max(runs):.3f} s; "
                  f"peak {peak / 2 ** 20:.0f} MiB (tracemalloc, separate run)")


def _timed(close, length):
    t0 = time.perf_counter()
    T.flat_spots(close, length=length)
    return time.perf_counter() - t0


if __name__ == "__main__":
    gate_a()
    semantics()
    scale_tolerance()
    reachability()
    cost()
    print("python", sys.version.split()[0], "pandas", pd.__version__, "numpy", np.__version__)
