# -*- coding: utf-8 -*-
"""Reproduce the numbers in docs/LevelShiftSizeMeasured.md.

    python docs/measure_level_shift_size.py

Run from the repo root. Uses tests/test_level_shift_size.py's generators and
its independent (plain-Python-loop) transcription of Kats'
`get_level_shift_features` max.
"""
import os
import platform
import sys
import time
import tracemalloc

import numpy as np
import pandas as pd

sys.path.insert(0, os.getcwd())
import tests.test_level_shift_size as T  # noqa: E402

FRAMES = (
    ("GARCH(.10,.85), 1500", lambda: T._garch(1500, 1)),
    ("iid normal, 1500", lambda: pd.Series(100 * np.cumprod(1 + np.random.default_rng(2).normal(0, 0.02, 1500)))),
    ("step at 750 (x1.5), 1500", lambda: T._step_series(1500, 3, 750, 1.5)[1]),
    ("tick-rounded near 5, 1500", lambda: _ticky(1500, 4)),
)


def _ticky(n, seed):
    rng = np.random.default_rng(seed)
    c = 100 * np.cumprod(1 + rng.normal(0, 0.02, n))
    c = 5 + (c - c[0]) * 0.01
    return pd.Series(np.round(c / 0.01) * 0.01)


def gate_a():
    """The oracle is Kats' max-of-diffs, transcribed independently (a plain
    Python loop over sliding window_size-bar means on raw log(close), not
    the module's cumsum-on-ratio vectorisation), compared against the
    module at every bar of several frames and lengths."""
    print("== Gate A: vs Kats get_level_shift_features max (independent loop), every bar ==")
    for name, mk in FRAMES:
        close = mk()
        for L in (T.MIN_LENGTH, 50, 100):
            if L + 5 > close.size:
                continue
            ours = T.level_shift_size(close, length=L).to_numpy()
            ref = T._oracle(close, L)
            m = ~np.isnan(ours) & ~np.isnan(ref)
            max_diff = np.max(np.abs(ours[m] - ref[m])) if m.any() else float("nan")
            print(f"  {name} length {L}: NaN masks equal {np.array_equal(np.isnan(ours), np.isnan(ref))}; "
                  f"max abs diff {max_diff:.3e} over {int(m.sum())} bars")


def semantics():
    """A single, deterministic persistent step inside an otherwise flat
    100-bar window (the closed-form construction in
    test_level_shift_size.py::test_closed_form_single_level_shift,
    generalised over the step's log size V): LEVELSHIFTSIZE scales
    linearly with V, confirming "size of the jump"."""
    print("== semantics: LEVELSHIFTSIZE_100 scales with the step's log size ==")
    for v in (0.02, 0.05, 0.10, 0.20):
        close = pd.Series(np.where(np.arange(100) < 50, 1.0, np.exp(v)))
        out = T.level_shift_size(close, length=100)
        print(f"  step log-size {v}: LEVELSHIFTSIZE_100[99] = {out.iloc[99]:.6f} (V/20 = {v / T.WINDOW_SIZE:.6f})")


def reachability():
    print("== Gate C: reachability on a 600-bar GARCH frame, length 100 ==")
    out = T.level_shift_size(T._garch(600, seed=4))
    print(f"  fires {out.notna().sum()} of 600 (warm-up {T._garch().size - out.notna().sum()}); "
          f"distinct values {out.dropna().nunique()}; range [{out.min():.6f}, {out.max():.6f}]")


def scale_tolerance():
    print("== Gate D: price-scale tolerance (x10/x3.7, not powers of two) ==")
    close = T._garch(seed=4)
    for k in (10.0, 3.7):
        base, scaled = T.level_shift_size(close), T.level_shift_size(close * k)
        d = (base - scaled).abs()
        print(f"  x{k}: max abs diff {d.max():.3e}, NaN masks equal {(base.isna() == scaled.isna()).all()}")


def tie_robustness():
    print("== robustness: flat and one-ulp-jitter prices ==")
    flat = pd.Series([10.0] * 150)
    out = T.level_shift_size(flat)
    print(f"  exactly flat, 150 bars: fires {out.notna().sum()}, all zero {(out.dropna() == 0.0).all()}")
    rng = np.random.default_rng(0)
    c = np.full(150, 10.0)
    c[rng.random(150) < 0.5] = np.nextafter(10.0, 20.0)
    out = T.level_shift_size(pd.Series(c))
    print(f"  one-ulp jitter, 150 bars: fires {out.notna().sum()}, max value {out.dropna().max():.3e}")


def cost():
    print("== cost (machine-dependent; " + (platform.processor() or platform.machine()) + ") ==")
    for n in (5000, 20000, 200000):
        close = pd.Series(100 * np.cumprod(1 + np.random.default_rng(5).normal(0, 0.02, n)))
        for L in (100, 252):
            runs = [_timed(close, L) for _ in range(5)]  # tracemalloc off
            tracemalloc.start()
            T.level_shift_size(close, length=L)
            peak = tracemalloc.get_traced_memory()[1]
            tracemalloc.stop()
            print(f"  n={n} length={L}: 5 runs {min(runs):.3f} .. {max(runs):.3f} s; "
                  f"peak {peak / 2 ** 20:.0f} MiB (tracemalloc, separate run)")


def _timed(close, length):
    t0 = time.perf_counter()
    T.level_shift_size(close, length=length)
    return time.perf_counter() - t0


if __name__ == "__main__":
    gate_a()
    semantics()
    reachability()
    scale_tolerance()
    tie_robustness()
    cost()
    print("python", sys.version.split()[0], "pandas", pd.__version__, "numpy", np.__version__)
